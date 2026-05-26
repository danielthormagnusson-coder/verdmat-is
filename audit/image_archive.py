"""
image_archive.py — shared image-download + image_index helper module.

Centralizes the new (post-pilot-v3) storage policy:
  - Layout: D:\\Gagnapakkar\\images\\<source_fastnum>\\<n>.jpg (sequential, legacy convention)
  - source_fastnum is the path component of the CloudFront URL, not the property
    that referenced it (handles the cross-property bug from pilot v3).
  - image_nr is sequential per source_fastnum, computed from MAX(image_nr)+1.
    Single-threaded callers; for parallel Stage B see stage_b_image_bootstrap.
  - All downloads write a row to image_index.db with PRIMARY KEY (fastnum, image_nr).
  - When the property scraping context references a source_fastnum != itself,
    a row is also written to cross_property_refs.

Used by:
  - backfill_evalue_range.py (single-property scraping)
  - storage_policy_validator.py (Phase 1.5)
  - stage_b_image_bootstrap.py (parallel re-fetch of downloaded=0 rows)
"""

from __future__ import annotations

import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CANONICAL_IMAGE_ROOT = Path(r"D:\Gagnapakkar\images")
INDEX_DB_PATH = Path(r"D:\Gagnapakkar\image_index.db")

# Cloudfront URL pattern; group 1 = source_fastnum, group 2 = original basename
CF_RE = re.compile(
    r"https://d1u57vh96em4i1\.cloudfront\.net/(\d+)/([A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp))",
    re.IGNORECASE,
)
IMG_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
IMAGE_TIMEOUT = 30


def open_index_db():
    INDEX_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(INDEX_DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def parse_cf_urls(text):
    """Extract (source_fastnum:int, basename:str, full_url:str) tuples
    in first-occurrence order from a JSON-string-or-blob.
    """
    seen = set()
    out = []
    for source_fn, basename in CF_RE.findall(text):
        url = f"https://d1u57vh96em4i1.cloudfront.net/{source_fn}/{basename}"
        if url in seen:
            continue
        seen.add(url)
        out.append((int(source_fn), basename, url))
    return out


def download_image_to_disk(url, dest_path):
    """Single-image fetch with atomic-rename. Returns (ok, bytes, info)."""
    if dest_path.exists():
        try:
            return True, dest_path.stat().st_size, "skip-exists"
        except OSError:
            pass
    try:
        req = urllib.request.Request(url, headers=IMG_UA)
        with urllib.request.urlopen(req, timeout=IMAGE_TIMEOUT) as resp:
            body = resp.read()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest_path.with_suffix(dest_path.suffix + ".partial")
        tmp.write_bytes(body)
        tmp.replace(dest_path)
        return True, len(body), "downloaded"
    except urllib.error.HTTPError as e:
        return False, 0, f"http-{e.code}"
    except (urllib.error.URLError, TimeoutError) as e:
        return False, 0, f"net:{e}"
    except Exception as e:
        return False, 0, f"err:{type(e).__name__}:{e}"


def fetch_or_skip_image(idx_conn, source_fn, url, augl_capture_iso=None):
    """Idempotent ensure-downloaded-and-indexed for one URL.

    Looks up the URL in image_index. If already downloaded=1 + file exists,
    no-op and return ('cached', existing_path, 0). Otherwise fetches from CDN,
    writes to canonical layout, updates index. Returns
    (status, local_path, bytes_written) where status is one of:
      'cached'     — already on disk, no work
      'downloaded' — fresh fetch succeeded
      'failed'     — fetch failed (HTTP/network/etc.); image_index NOT updated
    """
    cur = idx_conn.cursor()
    row = cur.execute(
        "SELECT image_nr, local_path, downloaded FROM image_index WHERE original_url=?",
        (url,),
    ).fetchone()
    if row:
        nr, lp, dl = row
        if dl == 1 and Path(lp).exists():
            return "cached", lp, 0
        # row exists but file missing — re-download to canonical layout
    else:
        nr = None  # need to compute

    if nr is None:
        nr = (cur.execute(
            "SELECT COALESCE(MAX(image_nr), 0) + 1 FROM image_index WHERE fastnum=?",
            (source_fn,),
        ).fetchone()[0])

    local_path = CANONICAL_IMAGE_ROOT / str(source_fn) / f"{nr}.jpg"
    ok, nbytes, info = download_image_to_disk(url, local_path)
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if ok:
        if row:
            cur.execute(
                "UPDATE image_index SET local_path=?, downloaded=1, "
                "last_verified_at=?, file_size_bytes=? WHERE original_url=?",
                (str(local_path), now_iso, nbytes, url),
            )
        else:
            cur.execute(
                """INSERT OR IGNORE INTO image_index
                   (fastnum, image_nr, original_url, local_path, downloaded,
                    source_db, first_seen_at, last_verified_at, file_size_bytes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (source_fn, nr, url, str(local_path), 1,
                 "fresh_scrape", now_iso, now_iso, nbytes),
            )
        idx_conn.commit()
        return "downloaded", str(local_path), nbytes
    else:
        return "failed", None, 0


def record_cross_property_ref(idx_conn, referencing_fn, referenced_fn,
                              image_url, augl_id="—", capture_iso=None):
    """Note that property `referencing_fn`'s augl referenced an image that
    physically lives in `referenced_fn`'s CloudFront folder. Idempotent.
    """
    if referencing_fn == referenced_fn:
        return  # not a cross-ref
    capture_iso = capture_iso or datetime.now(timezone.utc).isoformat(timespec="seconds")
    idx_conn.execute(
        """INSERT OR IGNORE INTO cross_property_refs
           (referencing_fastnum, referenced_fastnum, image_url, augl_id, augl_capture_at)
           VALUES (?, ?, ?, ?, ?)""",
        (referencing_fn, referenced_fn, image_url, augl_id, capture_iso),
    )
    idx_conn.commit()


def download_property_images_v2(idx_conn, property_fastnum, augl_payload):
    """Download every CloudFront image referenced by this property's augl.

    Honors the new storage policy:
      - Each image lives at /images/<source_fastnum>/<n>.jpg
      - Cross-property URLs (source != property) recorded in cross_property_refs
      - Idempotent skip-if-already-downloaded via image_index lookup

    Returns dict with summary counts.
    """
    if not augl_payload or augl_payload.get("status") != 200:
        return {"n_urls": 0, "downloaded": 0, "cached": 0, "failed": 0,
                "bytes": 0, "cross_refs": 0}

    import json
    data_str = augl_payload.get("data") or ""
    try:
        inner = json.loads(data_str)
    except (json.JSONDecodeError, TypeError):
        return {"n_urls": 0, "downloaded": 0, "cached": 0, "failed": 0,
                "bytes": 0, "cross_refs": 0}

    blob = json.dumps(inner, ensure_ascii=False, default=str)
    triples = parse_cf_urls(blob)
    counts = {"n_urls": len(triples), "downloaded": 0, "cached": 0,
              "failed": 0, "bytes": 0, "cross_refs": 0}
    for source_fn, basename, url in triples:
        if source_fn != property_fastnum:
            record_cross_property_ref(idx_conn, property_fastnum, source_fn, url)
            counts["cross_refs"] += 1
        status, _, nbytes = fetch_or_skip_image(idx_conn, source_fn, url)
        counts[status] = counts.get(status, 0) + 1
        counts["bytes"] += nbytes
        time.sleep(0.5)  # polite to CloudFront
    return counts
