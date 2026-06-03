"""fetch_myigloo — Step 1c Phase 3 myigloo raw fetcher (hybrid index + detail).

SCRAPER_SPEC_v2 §2.1 raw layer for myigloo. Index-walk enumerates listing ids
(page_size=100, order_by=-published_at, newest-first); detail-walk fetches the
rich ~80-key payload per id. Every fetch lands in raw_myigloo.db as a content-
addressable blob + an append-only ledger row, with content-hash idempotency
(unchanged body -> changed=0 / skipped_unchanged / blob reused). content_hash is
computed on a CANONICALIZED body (§2.1.1: per-source volatile JSON paths nulled —
e.g. myigloo's request-stamped *.verification.as_of) so per-request server
timestamps cannot defeat dedup; blob_gz stores the body verbatim.

NO parsing, NO Supabase, NO canonical promotion — that is Step 1d+.

CLI:
    python fetch_myigloo.py             # FULL run (~9 pages + ~874 details)
    python fetch_myigloo.py --dry-run   # 1 page + first 10 details (warm-up)

Timestamp convention (binding, §2.1): every ISO8601 string comes from
datetime.now(timezone.utc).isoformat() at the Python call-site and is passed
into the INSERT. Never SQL datetime()/CURRENT_TIMESTAMP.

stdlib only.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path  # noqa: E402

API_BASE = "https://rent-api.myigloo.is/api/listings/"
PAGE_SIZE = 100
HEADERS = {"User-Agent": "verdmat-is/0.1 (research)", "Accept": "application/json"}
TIMEOUT_S = 30
BACKOFF = (1, 2, 4)          # exponential backoff between retry attempts
MAX_ATTEMPTS = 3
POLITE_DELAY_S = 1.0
OUTAGE_THRESHOLD = 5         # consecutive 5xx -> abort

# §2.1.1 — per-source volatile JSON paths nulled before hashing. These are
# server-stamped per-request timestamps; left in, they make every fetch's body
# unique and defeat content-hash idempotency. Additive list as discovered.
MYIGLOO_VOLATILE_PATHS = (
    "organization.verification.as_of",
    "owner.verification.as_of",
)


# ─────────────────────────────────────────────────────────────── data types
@dataclass
class FetchResult:
    kind: str
    source_listing_id: "str | None"
    status: "int | None"
    hash: "str | None"
    byte_len: int
    byte_len_gz: int
    changed: int
    retries: int
    elapsed_ms: float
    new_blob: bool = False
    body: "bytes | None" = None


@dataclass
class RunStats:
    pages_fetched: int = 0
    details_fetched: int = 0
    new_blobs: int = 0
    changed_1_count: int = 0
    changed_0_count: int = 0
    http_errors_4xx: int = 0
    http_errors_5xx: int = 0
    total_uncompressed_bytes: int = 0
    total_compressed_bytes: int = 0
    total_elapsed_sec: float = 0.0


class OutageAbort(RuntimeError):
    pass


class OutageDetector:
    """Counts consecutive 5xx responses; trips at threshold. 2xx resets."""
    def __init__(self, threshold: int = OUTAGE_THRESHOLD):
        self.threshold = threshold
        self.consecutive = 0
        self.tripped = False

    def record(self, status: "int | None") -> bool:
        if status is not None and 500 <= status <= 599:
            self.consecutive += 1
        elif status is not None and 200 <= status < 300:
            self.consecutive = 0
        if self.consecutive >= self.threshold:
            self.tripped = True
        return self.tripped


# ───────────────────────────────────────────────────────────── pure helpers
def should_retry(status: "int | None" = None, exc: "BaseException | None" = None) -> bool:
    """Retry on 5xx, 429, and transient network errors; not on other 4xx."""
    if isinstance(exc, urllib.error.HTTPError):   # HTTPError IS-A URLError; judge by code
        status, exc = exc.code, None
    if exc is not None:
        return isinstance(exc, (urllib.error.URLError, ConnectionError, TimeoutError))
    if status is None:
        return False
    return status == 429 or 500 <= status <= 599


def _nullify_path(obj, path):
    """Walk a dotted path and set the leaf to None. No-op if the path is missing."""
    keys = path.split(".")
    cur = obj
    for k in keys[:-1]:
        if not isinstance(cur, dict) or k not in cur:
            return
        cur = cur[k]
    if isinstance(cur, dict) and keys[-1] in cur:
        cur[keys[-1]] = None


def _canonical_hash(body: bytes, content_type: str) -> str:
    """sha256 of the body with per-source volatile fields nulled (§2.1.1).
    JSON only; falls back to raw-body sha256 on parse failure (defensive)."""
    if content_type.startswith("application/json"):
        try:
            payload = json.loads(body)
            for path in MYIGLOO_VOLATILE_PATHS:
                _nullify_path(payload, path)
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                   ensure_ascii=False).encode("utf-8")
            return hashlib.sha256(canonical).hexdigest()
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass  # fall through to raw hash
    return hashlib.sha256(body).hexdigest()


def compute_changed(conn, kind, source_listing_id, url, new_hash):
    """(changed, parse_status) by comparing to the most-recent prior fetch of
    the same logical target (per-id for detail, per-url for api_page)."""
    if source_listing_id is not None:
        row = conn.execute(
            "SELECT content_hash FROM raw_fetches WHERE source='myigloo' AND fetch_kind=? "
            "AND source_listing_id=? ORDER BY fetched_at DESC, raw_id DESC LIMIT 1",
            (kind, source_listing_id)).fetchone()
    else:
        row = conn.execute(
            "SELECT content_hash FROM raw_fetches WHERE source='myigloo' AND fetch_kind=? "
            "AND source_listing_id IS NULL AND url=? ORDER BY fetched_at DESC, raw_id DESC LIMIT 1",
            (kind, url)).fetchone()
    prev = row[0] if row else None
    if prev is not None and prev == new_hash:
        return 0, "skipped_unchanged"
    return 1, "pending"


# ──────────────────────────────────────────────────────────────── DB writes
def record_success(conn, kind, source_listing_id, url, fetched_at, status, retries,
                   body, content_type="application/json", elapsed_ms=0.0) -> FetchResult:
    h = _canonical_hash(body, content_type)
    body_gz = gzip.compress(body)
    byte_len = len(body)
    changed, parse_status = compute_changed(conn, kind, source_listing_id, url, h)
    new_blob = conn.execute("SELECT 1 FROM raw_blobs WHERE content_hash=?", (h,)).fetchone() is None
    conn.execute(
        "INSERT OR IGNORE INTO raw_blobs(content_hash, blob_gz, content_type, byte_len, first_stored) "
        "VALUES(?,?,?,?,?)", (h, body_gz, content_type, byte_len, fetched_at))
    conn.execute(
        "INSERT INTO raw_fetches(source, source_listing_id, url, fetch_kind, fetched_at, "
        "http_status, content_hash, changed, retry_count, parse_status) VALUES('myigloo',?,?,?,?,?,?,?,?,?)",
        (source_listing_id, url, kind, fetched_at, status, h, changed, retries, parse_status))
    conn.commit()
    return FetchResult(kind, source_listing_id, status, h, byte_len, len(body_gz),
                       changed, retries, elapsed_ms, new_blob, body)


def record_failure(conn, kind, source_listing_id, url, fetched_at, status, retries, elapsed_ms=0.0) -> FetchResult:
    # parse_error is reserved for parser failures (Step 1d), not HTTP — leave NULL.
    conn.execute(
        "INSERT INTO raw_fetches(source, source_listing_id, url, fetch_kind, fetched_at, "
        "http_status, content_hash, changed, retry_count, parse_status) VALUES('myigloo',?,?,?,?,?,NULL,0,?,'pending')",
        (source_listing_id, url, kind, fetched_at, status, retries))
    conn.commit()
    return FetchResult(kind, source_listing_id, status, None, 0, 0, 0, retries, elapsed_ms, False, None)


# ───────────────────────────────────────────────────────────── HTTP + write
def fetch_one(url, kind, source_listing_id, conn, sleep_fn=time.sleep) -> FetchResult:
    status = None
    body = None
    content_type = "application/json"
    elapsed_ms = 0.0
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        attempts += 1
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                body = resp.read()
                status = resp.status
                content_type = (resp.headers.get("content-type") or "application/json").split(";")[0].strip()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            break  # 2xx
        except urllib.error.HTTPError as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            status, body = e.code, None
            if should_retry(status=status) and attempts < MAX_ATTEMPTS:
                sleep_fn(BACKOFF[attempts - 1]); continue
            break  # non-retryable 4xx, or 5xx/429 after final attempt
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            status, body = None, None
            if attempts < MAX_ATTEMPTS:
                sleep_fn(BACKOFF[attempts - 1]); continue
            break  # network failure after final attempt

    retries = attempts - 1
    fetched_at = datetime.now(timezone.utc).isoformat()
    if status is not None and 200 <= status < 300 and body is not None:
        result = record_success(conn, kind, source_listing_id, url, fetched_at, status, retries,
                                body, content_type, elapsed_ms)
    else:
        result = record_failure(conn, kind, source_listing_id, url, fetched_at, status, retries, elapsed_ms)
    sleep_fn(POLITE_DELAY_S)  # politeness, after the logical fetch (outside retry-backoff)
    return result


# ──────────────────────────────────────────────────────────────────── log
def _log_fetch(res: FetchResult, log):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    idv = res.source_listing_id if res.source_listing_id is not None else "NULL"
    hsh = (res.hash[:8] + "...") if res.hash else "-"
    log("[%s] kind=%-8s id=%-7s status=%s changed=%s hash=%s bytes=%s (gzip %s) elapsed=%.0fms retries=%s"
        % (ts, res.kind, idv, res.status, res.changed, hsh, res.byte_len, res.byte_len_gz,
           res.elapsed_ms, res.retries))


def _tally(stats: RunStats, res: FetchResult):
    if res.new_blob:
        stats.new_blobs += 1
    if res.status is not None and 200 <= res.status < 300:
        if res.changed == 1:
            stats.changed_1_count += 1
        else:
            stats.changed_0_count += 1
    if res.status is not None and 400 <= res.status < 500:
        stats.http_errors_4xx += 1
    if res.status is not None and 500 <= res.status < 600:
        stats.http_errors_5xx += 1
    stats.total_uncompressed_bytes += res.byte_len
    stats.total_compressed_bytes += res.byte_len_gz


# ────────────────────────────────────────────────────────────────────── run
def _page_url(page, use_order_by):
    base = "%s?page=%d&page_size=%d" % (API_BASE, page, PAGE_SIZE)
    return base + "&order_by=-published_at" if use_order_by else base


def run(dry_run: bool, conn, log=print) -> RunStats:
    stats = RunStats()
    outage = OutageDetector()
    t_start = time.perf_counter()
    ids: list = []
    use_order_by = True
    order_by_verdict = "untested"
    page = 1

    log("=== myigloo fetch: %s ===" % ("DRY-RUN (1 page + 10 details)" if dry_run else "FULL RUN"))
    log("--- Phase 1: index-walk (page_size=%d, order_by=-published_at) ---" % PAGE_SIZE)
    while True:
        res = fetch_one(_page_url(page, use_order_by), "api_page", None, conn)
        _log_fetch(res, log)
        # order_by fallback only on the first page
        if page == 1 and use_order_by and res.status in (400, 404):
            log("  WARNING: order_by=-published_at returned %s — falling back to no order_by." % res.status)
            use_order_by = False
            order_by_verdict = "rejected (%s) -> fell back" % res.status
            res = fetch_one(_page_url(1, False), "api_page", None, conn)
            _log_fetch(res, log)
        stats.pages_fetched += 1
        _tally(stats, res)
        if outage.record(res.status):
            raise OutageAbort("aborted: %d consecutive 5xx responses" % outage.consecutive)

        next_url = None
        if res.status == 200 and res.body:
            data = json.loads(res.body)
            items = data.get("items", [])
            ids.extend(it["id"] for it in items if "id" in it)
            next_url = data.get("next")
            if page == 1:
                log("  page=1 returned %d items; count=%s; next=%s"
                    % (len(items), data.get("count"), bool(next_url)))
                # empirical order_by confirmation
                first3 = [(it.get("id"), it.get("published_at")) for it in items[:3]]
                pubs = [it.get("published_at") for it in items if it.get("published_at")]
                desc = all(pubs[i] >= pubs[i + 1] for i in range(len(pubs) - 1)) if len(pubs) > 1 else None
                log("  first 3 (id, published_at): %s" % first3)
                if use_order_by:
                    order_by_verdict = ("HONORED (published_at descending)" if desc
                                        else "IGNORED (200 but not newest-first; data still valid)")
                log("  order_by verdict: %s" % order_by_verdict)
        else:
            log("  page=%d non-200 (status=%s) — no ids extracted" % (page, res.status))

        if dry_run or not next_url:
            break
        page += 1

    log("--- Phase 2: detail-walk (%d ids%s) ---"
        % (min(10, len(ids)) if dry_run else len(ids), ", dry-run first 10" if dry_run else ""))
    detail_ids = ids[:10] if dry_run else ids
    for lid in detail_ids:
        res = fetch_one("%s%s/" % (API_BASE, lid), "detail", str(lid), conn)
        _log_fetch(res, log)
        stats.details_fetched += 1
        _tally(stats, res)
        if outage.record(res.status):
            raise OutageAbort("aborted: %d consecutive 5xx responses" % outage.consecutive)

    stats.total_elapsed_sec = time.perf_counter() - t_start
    _print_summary(stats, order_by_verdict, log)
    return stats


def _print_summary(stats: RunStats, order_by_verdict: str, log):
    ratio = (stats.total_compressed_bytes / stats.total_uncompressed_bytes
             if stats.total_uncompressed_bytes else 0.0)
    log("\n=== END-OF-RUN SUMMARY ===")
    log("  pages_fetched            : %d" % stats.pages_fetched)
    log("  details_fetched          : %d" % stats.details_fetched)
    log("  new_blobs                : %d" % stats.new_blobs)
    log("  changed=1 (new/changed)  : %d" % stats.changed_1_count)
    log("  changed=0 (unchanged)    : %d" % stats.changed_0_count)
    log("  http_errors_4xx          : %d" % stats.http_errors_4xx)
    log("  http_errors_5xx          : %d" % stats.http_errors_5xx)
    log("  total_uncompressed_bytes : %d" % stats.total_uncompressed_bytes)
    log("  total_compressed_bytes   : %d" % stats.total_compressed_bytes)
    log("  compression_ratio        : %.3f (gzip/raw)" % ratio)
    log("  total_elapsed_sec        : %.1f" % stats.total_elapsed_sec)
    log("  order_by=-published_at    : %s" % order_by_verdict)


def main():
    ap = argparse.ArgumentParser(description="myigloo raw fetcher (hybrid index + detail)")
    ap.add_argument("--dry-run", action="store_true", help="1 page + first 10 details (warm-up)")
    args = ap.parse_args()

    db_path = get_raw_db_path("myigloo")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    print("DB: %s" % db_path)
    try:
        run(args.dry_run, conn)
    except OutageAbort as e:
        print("OUTAGE ABORT: %s" % e)
        sys.exit(2)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
