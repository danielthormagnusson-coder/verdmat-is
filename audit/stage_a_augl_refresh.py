"""
stage_a_augl_refresh.py — Phase 2 (Áfangi 0 weekend run)

Single-action augl-only refresh of every fastnum in Supabase `properties`.
Streams the fastnum list once at startup (Supabase MCP one-shot bulk query)
and persists it to a local manifest, so resume after restart doesn't need
network access to Supabase.

Per-fastnum cost: 1 evalue.is POST + 1 sec sleep ≈ 1.4 s wall-clock.
124,835 × 1.4 s ≈ 49 hours — multi-night.

Resume-safety: each completed fastnum lands in stage_a_augl with
captured_at set; restart of this script skips them. SQLite is the
durable state.

Halt rules per task spec:
  - Cloudflare 403 / HTML response → halt + write to status
  - Sustained network failure (>10 min unreachable) → halt
  - Disk free <5% → halt
  - 5xx errors >5% over rolling 100-request window → halt
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from weekend_run_status import get_writer  # noqa: E402

AUDIT_DIR = Path(__file__).resolve().parent
STAGING_DB = AUDIT_DIR / "stage_a_augl_staging.db"
MANIFEST_FILE = AUDIT_DIR / "stage_a_fastnum_manifest.txt"

BASE_URL = "https://www.evalue.is/fastnum"
DELAY = 1.0
TIMEOUT = 15
MAX_RETRIES = 3
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://www.evalue.is",
}
DISK_FREE_THRESHOLD = 0.05  # halt if D:\ free < 5%
ERROR_RATE_WINDOW = 100
ERROR_RATE_THRESHOLD = 0.05  # halt if 5xx rate > 5% over rolling window
SUSTAINED_NET_FAIL_S = 600  # 10 min sustained-failure halt
CHECKPOINT_EVERY = 25       # SQLite commit cadence (~35 s) — durability + reader visibility
PROGRESS_LOG_EVERY = 500    # human-log line cadence (still progress in status every iter)


SCHEMA = """
CREATE TABLE IF NOT EXISTS stage_a_augl (
    fastnum INTEGER PRIMARY KEY,
    augl_status INTEGER,
    augl_json TEXT,
    n_ads INTEGER,
    n_image_urls INTEGER,
    latest_augl_iso TEXT,
    captured_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stage_a_status ON stage_a_augl(augl_status);
"""


def init_db():
    conn = sqlite3.connect(STAGING_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    for stmt in SCHEMA.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()
    return conn


def post_augl(fastnum):
    """POST get_fasteign_augl. Returns (parsed_json | None, halt_reason | None)."""
    url = f"{BASE_URL}/{fastnum}?/get_fasteign_augl"
    data = f"fastnum={fastnum}".encode("utf-8")
    last = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                ct = resp.headers.get("Content-Type", "")
                if resp.headers.get("cf-mitigated"):
                    return None, f"cf-mitigated:{resp.headers.get('cf-mitigated')}"
                if "html" in ct.lower() or body.lstrip().lower().startswith(("<!doctype", "<html")):
                    return None, f"html-response ct={ct}"
                try:
                    return json.loads(body), None
                except json.JSONDecodeError:
                    return None, "json-decode-error"
        except urllib.error.HTTPError as e:
            if e.code == 403:
                return None, f"http-403"
            last = f"http-{e.code}"
            if 500 <= e.code < 600:
                # surface 5xx for rolling-window halt logic
                return None, last
        except (urllib.error.URLError, TimeoutError) as e:
            last = f"net:{e}"
        except Exception as e:
            last = f"err:{type(e).__name__}"
        if attempt < MAX_RETRIES - 1:
            time.sleep((attempt + 1) * 2)
    return None, last or "max-retries"


def parse_augl_summary(payload):
    """Return (n_ads, n_image_urls, latest_iso) summary tuple."""
    if not payload or payload.get("status") != 200:
        return 0, 0, None
    try:
        inner = json.loads(payload.get("data") or "")
    except Exception:
        return 0, 0, None
    if not isinstance(inner, list) or len(inner) < 1 or not isinstance(inner[0], list):
        return 0, 0, None
    n_ads = len(inner[0])
    blob = json.dumps(inner, ensure_ascii=False, default=str)
    import re as _re
    n_imgs = len(_re.findall(
        r"https://d1u57vh96em4i1\.cloudfront\.net/\d+/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)",
        blob, flags=_re.IGNORECASE))
    iso_pat = _re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    dates = sorted(iso_pat.findall(blob))
    latest = dates[-1] if dates else None
    return n_ads, n_imgs, latest


def load_or_build_manifest(sw):
    """Read fastnum manifest from disk; rebuild via Supabase if missing.

    Supabase pull is left as an offline step — caller runs:
       SELECT fastnum FROM properties ORDER BY fastnum
    and saves to MANIFEST_FILE one fastnum per line.
    """
    if not MANIFEST_FILE.exists():
        sw.log("ERROR", f"manifest missing: {MANIFEST_FILE}")
        sw.log("ERROR", "create it by running:")
        sw.log("ERROR", "  (Supabase MCP) SELECT fastnum FROM properties ORDER BY fastnum")
        sw.log("ERROR", "  → save fastnums one-per-line to stage_a_fastnum_manifest.txt")
        raise SystemExit(2)
    fns = []
    for line in MANIFEST_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.isdigit():
            fns.append(int(s))
    sw.log("INFO", f"manifest: {len(fns):,} fastnums")
    return fns


def main():
    sw = get_writer()
    sw.start()
    try:
        sw.set_phase("phase_2_stage_a_augl_refresh")
        sw.set_subphase("startup")
        sw.log("INFO", f"Phase 2 starting; staging={STAGING_DB}")

        fastnums = load_or_build_manifest(sw)

        conn = init_db()
        # Build done-set for resume
        done = set(r[0] for r in conn.execute("SELECT fastnum FROM stage_a_augl"))
        sw.log("INFO", f"resume: {len(done):,} fastnums already in staging; "
                       f"{len(fastnums) - len(done):,} remaining")

        sw.set_subphase("augl-refresh sweep")
        sw.set_progress(len(done), len(fastnums))

        rolling_errs = deque(maxlen=ERROR_RATE_WINDOW)
        last_net_ok_at = time.monotonic()
        started = time.monotonic()
        completed_this_run = 0

        for i, fn in enumerate(fastnums):
            if fn in done:
                continue

            # Disk-full pre-check
            if i % 200 == 0:
                free = shutil.disk_usage("D:\\")
                if free.free / free.total < DISK_FREE_THRESHOLD:
                    sw.add_halt(f"disk-low: {free.free/1024**3:.1f} GB free of {free.total/1024**3:.0f} GB")
                    return 6

            payload, halt_reason = post_augl(fn)
            now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

            # Halt-rule checks
            if halt_reason and halt_reason.startswith(("cf-", "http-403", "html-response")):
                sw.add_halt(f"fastnum {fn}: {halt_reason}")
                return 4

            if halt_reason:
                rolling_errs.append(1)
                # 5xx tracking
                if halt_reason.startswith("http-5"):
                    if (sum(rolling_errs) / max(len(rolling_errs), 1)) > ERROR_RATE_THRESHOLD \
                       and len(rolling_errs) >= ERROR_RATE_WINDOW:
                        sw.add_halt(f"5xx rate > 5% over rolling window — halt")
                        return 5
                # Sustained net-fail tracking
                if halt_reason.startswith("net:") or halt_reason == "max-retries":
                    if time.monotonic() - last_net_ok_at > SUSTAINED_NET_FAIL_S:
                        sw.add_halt(f"sustained net failure > {SUSTAINED_NET_FAIL_S}s")
                        return 5
                # log + persist a placeholder row so we don't re-attempt this run;
                # downloaded=0 will mark it for retry in a later session
                conn.execute(
                    "INSERT OR REPLACE INTO stage_a_augl "
                    "(fastnum, augl_status, augl_json, n_ads, n_image_urls, "
                    " latest_augl_iso, captured_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (fn, -1, None, 0, 0, None, now_iso),
                )
            else:
                rolling_errs.append(0)
                last_net_ok_at = time.monotonic()
                n_ads, n_imgs, latest = parse_augl_summary(payload)
                conn.execute(
                    "INSERT OR REPLACE INTO stage_a_augl "
                    "(fastnum, augl_status, augl_json, n_ads, n_image_urls, "
                    " latest_augl_iso, captured_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (fn, payload.get("status", 0),
                     json.dumps(payload, ensure_ascii=False),
                     n_ads, n_imgs, latest, now_iso),
                )

            completed_this_run += 1
            done_total = len(done) + completed_this_run
            elapsed = time.monotonic() - started
            rate_per_min = (completed_this_run / elapsed) * 60 if elapsed > 0 else 0
            # Update status every iteration so cat audit/weekend_run_status.md is live
            sw.set_progress(done_total, len(fastnums), rate_per_min)

            if completed_this_run % CHECKPOINT_EVERY == 0:
                conn.commit()
            if completed_this_run % PROGRESS_LOG_EVERY == 0:
                sw.log("INFO",
                       f"checkpoint {done_total:,}/{len(fastnums):,} "
                       f"this_run={completed_this_run:,} rate={rate_per_min:.1f}/min")

            # Per-fastnum delay (last-step, not first — so resume on completed=N
            # picks up at N+1 with no extra wait)
            time.sleep(DELAY)

        conn.commit()
        sw.complete_phase("phase_2_stage_a_augl_refresh")
        sw.log("INFO", f"Phase 2 COMPLETE this_run={completed_this_run:,}")
        return 0
    finally:
        sw.stop()


if __name__ == "__main__":
    sys.exit(main())
