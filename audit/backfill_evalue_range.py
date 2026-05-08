"""
backfill_evalue_range.py — Áfangi 0 Stage 1 pilot scraper

Variant 6 of the evalue.is scraper family. Differs from the legacy variants
only in fastnum source: takes an explicit list (positive controls + integer
range) on the command line instead of reading kaupskra.csv. Same POST
mechanic, same SQLite schema, same 1-req/sec delay.

Hard halt rules per locked plan (audit/backfill_pilot_plan.md):
  - HTTP 403 → halt immediately, no retry
  - HTML response (Cloudflare interactive challenge) → halt immediately
  - Network error after MAX_RETRIES → halt
  Retry-with-delay trains anti-bot detection, so we do NOT recover.

Three actions per fastnum (data + kaups + augl), per existing scraper
template. Output rows are stage-tagged so positive-control vs pilot-sweep
can be separated in reporting.

Image downloads are SKIPPED for the pilot — image URLs are still recorded
to the myndir table for later, but no bytes are pulled. Pilot is about
API liveness + schema, not bulk-fetching media.

Usage:
    python audit/backfill_evalue_range.py
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "audit"
DB_PATH = AUDIT_DIR / "backfill_pilot.db"
LOG_PATH = AUDIT_DIR / "backfill_pilot_run.log"
IMAGE_ROOT = Path(r"D:\Gagnapakkar\images")  # per Áfangi 0.y Amendment 4 (image-ownership policy)

BASE_URL = "https://www.evalue.is/fastnum"
DELAY = 1.0
REQUEST_DELAY = 0.3
IMAGE_DELAY = 0.5  # polite to CloudFront between image GETs (separate host from evalue.is)
TIMEOUT = 15
IMAGE_TIMEOUT = 30  # images are larger; allow more headroom
MAX_RETRIES = 3

IMG_RE = re.compile(
    r"https://d1u57vh96em4i1\.cloudfront\.net/\d+/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)",
    re.IGNORECASE,
)
IMG_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.evalue.is",
}

ACTIONS = ("get_fasteign_data", "get_fasteign_kaups", "get_fasteign_augl")

POSITIVE_CONTROLS = [2526172, 2528893, 2512191, 2503270, 2506715]
PILOT_RANGE_START = 2_450_000
PILOT_RANGE_END = 2_450_099  # inclusive


class HaltSignal(Exception):
    """Raised when a hard-halt condition fires."""


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fasteignir (
            fastnum TEXT PRIMARY KEY,
            stage TEXT,
            data_json TEXT,
            kaups_json TEXT,
            augl_json TEXT,
            scraped_at TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'ok'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            level TEXT,
            stage TEXT,
            fastnum TEXT,
            event TEXT,
            detail TEXT
        )
        """
    )
    conn.commit()
    return conn


def log_event(conn, level, stage, fastnum, event, detail=""):
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO run_events (ts, level, stage, fastnum, event, detail) VALUES (?,?,?,?,?,?)",
        (ts, level, stage, str(fastnum) if fastnum is not None else None, event, detail),
    )
    conn.commit()
    line = f"[{ts}] {level:5} stage={stage} fastnum={fastnum} {event} {detail}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def post_evalue(fastnum, action):
    """POST to evalue.is. Returns (parsed_json_or_None, halt_reason_or_None).

    halt_reason set => caller MUST halt; do not interpret the JSON.
    """
    url = f"{BASE_URL}/{fastnum}?/{action}"
    data = f"fastnum={fastnum}".encode("utf-8")

    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body_bytes = resp.read()
                ct = resp.headers.get("Content-Type", "")
                body = body_bytes.decode("utf-8", errors="replace")

                # Cloudflare challenge surface: HTML body or cf-mitigated header
                cf_mitigated = resp.headers.get("cf-mitigated")
                if cf_mitigated:
                    return None, f"cloudflare-mitigated:{cf_mitigated}"

                if "html" in ct.lower() or body.lstrip().lower().startswith("<!doctype html") or body.lstrip().startswith("<html"):
                    snippet = body[:300].replace("\n", " ")
                    return None, f"html-response ct={ct} body[:300]={snippet!r}"

                try:
                    return json.loads(body), None
                except json.JSONDecodeError as e:
                    snippet = body[:300].replace("\n", " ")
                    return None, f"json-decode-error: {e} body[:300]={snippet!r}"

        except urllib.error.HTTPError as e:
            # 403 == hard halt. Do not retry.
            if e.code == 403:
                return None, f"http-403 reason={e.reason}"
            if e.code == 429:
                return None, f"http-429 rate-limited reason={e.reason}"
            last_err = f"HTTP {e.code} {e.reason}"
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = f"net error: {e}"
        except Exception as e:
            last_err = f"unexpected: {type(e).__name__}: {e}"

        # transient: limited retry with backoff
        if attempt < MAX_RETRIES - 1:
            wait = (attempt + 1) * 2
            time.sleep(wait)

    return None, f"max-retries-exhausted last_err={last_err}"


def extract_image_urls(augl_payload):
    """Return all distinct CloudFront image URLs across every ad in this property's augl payload.

    `augl_payload` is the parsed outer envelope ({type, status, data}) — the inner `data`
    field is itself a stringified JSON. Order-preserving dedupe so first-occurrence wins.
    """
    if not augl_payload or augl_payload.get("status") != 200:
        return []
    data_str = augl_payload.get("data") or ""
    try:
        inner = json.loads(data_str)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(inner, list) or len(inner) == 0:
        return []
    urls = IMG_RE.findall(json.dumps(inner, ensure_ascii=False, default=str))
    seen = set()
    return [u for u in urls if not (u in seen or seen.add(u))]


def download_image(url, dest_path):
    """Single-image download. Returns (ok: bool, bytes_written: int, info: str).

    Idempotent: if dest already exists, treat as success without re-downloading.
    Errors return ok=False; caller logs and continues (do NOT halt the stage on a
    single CloudFront 404 — image URLs can rot independently of registry data).
    """
    if dest_path.exists():
        try:
            return True, dest_path.stat().st_size, "skip-exists"
        except OSError:
            pass  # fall through to re-download

    try:
        req = urllib.request.Request(url, headers=IMG_UA)
        with urllib.request.urlopen(req, timeout=IMAGE_TIMEOUT) as resp:
            body = resp.read()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to .partial, rename — avoids half-file on interrupt
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


def download_property_images(conn, fastnum, augl_payload, image_root, stage):
    """Download every CloudFront image referenced by this property's augl payload.

    Layout: image_root / <fastnum> / <basename>.jpg
    Single failure logs WARN and continues; the stage does not abort.
    Returns (n_ok, n_fail, total_bytes, n_urls).
    """
    urls = extract_image_urls(augl_payload)
    if not urls:
        return 0, 0, 0, 0

    fn_dir = image_root / str(fastnum)
    n_ok = 0
    n_fail = 0
    total_bytes = 0
    for i, url in enumerate(urls):
        basename = url.rsplit("/", 1)[-1].split("?")[0]
        dest = fn_dir / basename
        ok, nbytes, info = download_image(url, dest)
        if ok:
            n_ok += 1
            total_bytes += nbytes
        else:
            n_fail += 1
            log_event(conn, "WARN", stage, fastnum, "img_fail",
                      f"url={url} info={info}")
        if i + 1 < len(urls):
            time.sleep(IMAGE_DELAY)
    return n_ok, n_fail, total_bytes, len(urls)


def scrape_property(conn, fastnum, stage, image_root=None, fast_skip_on_204=False):
    """Scrape one fastnum's three actions; optionally download its images.

    Returns ('ok' | 'not_found' | f'data_status_<n>' | 'error', payloads_dict).

    `fast_skip_on_204=True`: if the first (data) action returns status 204, persist
    the row immediately and skip the remaining 2 POSTs. Cuts non-hit cost by ~67%
    on bucket walks where most fastnums are unassigned.

    `image_root` (Path | None): if set, on each `ok` row download every CloudFront
    image referenced by the augl payload to image_root/<fastnum>/<basename>. Image
    failures do not abort the stage.
    """
    payloads = {"get_fasteign_data": None, "get_fasteign_kaups": None, "get_fasteign_augl": None}

    # Action 1: data (always)
    data, halt_reason = post_evalue(fastnum, "get_fasteign_data")
    if halt_reason is not None:
        log_event(conn, "HALT", stage, fastnum, "get_fasteign_data", halt_reason)
        raise HaltSignal(f"get_fasteign_data on {fastnum}: {halt_reason}")
    payloads["get_fasteign_data"] = data

    # Fast-skip: if the registry says "no record", don't waste calls on kaups/augl
    if fast_skip_on_204 and data is not None and data.get("status") == 204:
        status = "data_status_204"
        conn.execute(
            """
            INSERT OR REPLACE INTO fasteignir (fastnum, stage, data_json, kaups_json, augl_json, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(fastnum), stage, json.dumps(data, ensure_ascii=False), None, None, status),
        )
        conn.commit()
        return status, payloads

    time.sleep(REQUEST_DELAY)

    # Actions 2-3: kaups + augl
    kaups, halt_reason = post_evalue(fastnum, "get_fasteign_kaups")
    if halt_reason is not None:
        log_event(conn, "HALT", stage, fastnum, "get_fasteign_kaups", halt_reason)
        raise HaltSignal(f"get_fasteign_kaups on {fastnum}: {halt_reason}")
    payloads["get_fasteign_kaups"] = kaups
    time.sleep(REQUEST_DELAY)

    augl, halt_reason = post_evalue(fastnum, "get_fasteign_augl")
    if halt_reason is not None:
        log_event(conn, "HALT", stage, fastnum, "get_fasteign_augl", halt_reason)
        raise HaltSignal(f"get_fasteign_augl on {fastnum}: {halt_reason}")
    payloads["get_fasteign_augl"] = augl

    if data is None and kaups is None and augl is None:
        status = "error"
    elif data and data.get("status") == 404:
        status = "not_found"
    elif data and data.get("status") not in (200,):
        status = f"data_status_{data.get('status')}"
    else:
        status = "ok"

    conn.execute(
        """
        INSERT OR REPLACE INTO fasteignir (fastnum, stage, data_json, kaups_json, augl_json, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(fastnum),
            stage,
            json.dumps(data, ensure_ascii=False) if data is not None else None,
            json.dumps(kaups, ensure_ascii=False) if kaups is not None else None,
            json.dumps(augl, ensure_ascii=False) if augl is not None else None,
            status,
        ),
    )
    conn.commit()

    if image_root is not None and status == "ok" and augl is not None:
        n_ok, n_fail, total_bytes, n_urls = download_property_images(
            conn, fastnum, augl, image_root, stage
        )
        if n_urls > 0:
            log_event(conn, "INFO", stage, fastnum, "img_summary",
                      f"n_urls={n_urls} ok={n_ok} fail={n_fail} bytes={total_bytes}")

    return status, payloads


def run_stage(conn, fastnums, stage_label, image_root=None, fast_skip_on_204=False):
    log_event(conn, "INFO", stage_label, None, "stage_start",
              f"count={len(fastnums)} fast_skip={fast_skip_on_204} images={'on' if image_root else 'off'}")
    started = time.monotonic()
    counts = {"ok": 0, "not_found": 0, "error": 0, "other": 0}
    for i, fn in enumerate(fastnums, 1):
        try:
            status, _ = scrape_property(
                conn, fn, stage_label,
                image_root=image_root, fast_skip_on_204=fast_skip_on_204,
            )
        except HaltSignal as e:
            log_event(conn, "HALT", stage_label, fn, "halt_signal", str(e))
            raise
        if status == "ok":
            counts["ok"] += 1
        elif status == "not_found":
            counts["not_found"] += 1
        elif status == "error":
            counts["error"] += 1
        else:
            counts["other"] += 1
        if i % 50 == 0 or i == len(fastnums):
            log_event(
                conn, "INFO", stage_label, None, "progress",
                f"{i}/{len(fastnums)} ok={counts['ok']} not_found={counts['not_found']} error={counts['error']} other={counts['other']}"
            )
        if i < len(fastnums):
            time.sleep(DELAY)
    elapsed = time.monotonic() - started
    log_event(
        conn, "INFO", stage_label, None, "stage_end",
        f"elapsed_s={elapsed:.1f} counts={counts}"
    )
    return counts, elapsed


def main():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    conn = init_db(DB_PATH)
    log_event(conn, "INFO", "init", None, "run_start",
              f"db={DB_PATH} positives={POSITIVE_CONTROLS} pilot={PILOT_RANGE_START}-{PILOT_RANGE_END}")

    overall_started = time.monotonic()

    # Stage A: positive controls
    try:
        pc_counts, pc_elapsed = run_stage(conn, POSITIVE_CONTROLS, "positive_control")
    except HaltSignal as e:
        log_event(conn, "HALT", "positive_control", None, "stage_aborted", str(e))
        log_event(conn, "INFO", "run", None, "run_end", f"aborted_in_positive_control elapsed_s={time.monotonic()-overall_started:.1f}")
        return 2

    if pc_counts["ok"] != len(POSITIVE_CONTROLS):
        log_event(
            conn, "HALT", "positive_control", None, "control_not_all_ok",
            f"ok={pc_counts['ok']}/{len(POSITIVE_CONTROLS)}; halting before pilot sweep"
        )
        log_event(conn, "INFO", "run", None, "run_end", f"halted_after_positive_control elapsed_s={time.monotonic()-overall_started:.1f}")
        return 3

    log_event(conn, "INFO", "positive_control", None, "control_pass",
              f"all {len(POSITIVE_CONTROLS)} OK; proceeding to pilot sweep")

    # Stage B: pilot sweep
    pilot_fastnums = list(range(PILOT_RANGE_START, PILOT_RANGE_END + 1))
    try:
        sweep_counts, sweep_elapsed = run_stage(conn, pilot_fastnums, "pilot_sweep")
    except HaltSignal as e:
        log_event(conn, "HALT", "pilot_sweep", None, "stage_aborted", str(e))
        log_event(conn, "INFO", "run", None, "run_end", f"aborted_in_pilot_sweep elapsed_s={time.monotonic()-overall_started:.1f}")
        return 4

    overall_elapsed = time.monotonic() - overall_started
    log_event(
        conn, "INFO", "run", None, "run_end",
        f"all_stages_ok elapsed_s={overall_elapsed:.1f} pc={pc_counts} sweep={sweep_counts}"
    )
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
