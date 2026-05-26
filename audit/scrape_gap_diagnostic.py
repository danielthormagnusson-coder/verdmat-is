"""
scrape_gap_diagnostic.py — Áfangi 0 Stage 1 listings-volume gap diagnostic

Re-scrapes a single fastnum (default: 2004765, Laugavegur 39) using the same
POST mechanic as `backfill_evalue_range.py`, but outputs to a separate DB
(`audit/scrape_gap_diagnostic.db`) so the pilot DB stays untouched.

Halt-on-failure: if the scrape returns anything other than `status='ok'`,
exit with non-zero. Same Cloudflare/HTML/403 contract.

Goal: verify whether the existing scraper format still captures recent
listings data on a fastnum that we have empirical-screenshot evidence for
(3 listings dated 2026-05-05, 2026-04-17, 2024-11-13 per Danni's
2026-05-07 screenshot).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backfill_evalue_range import (  # noqa: E402
    AUDIT_DIR,
    HaltSignal,
    init_db,
    log_event,
    run_stage,
)

DIAG_DB = AUDIT_DIR / "scrape_gap_diagnostic.db"
TARGET_FASTNUM = 2004765


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    conn = init_db(DIAG_DB)
    log_event(conn, "INFO", "init", None, "diag_run_start",
              f"db={DIAG_DB} target={TARGET_FASTNUM}")
    started = time.monotonic()

    try:
        counts, elapsed = run_stage(conn, [TARGET_FASTNUM], "diag_2004765")
    except HaltSignal as e:
        log_event(conn, "HALT", "diag_2004765", None, "stage_aborted", str(e))
        return 2

    if counts.get("ok", 0) != 1:
        log_event(conn, "HALT", "diag_2004765", None, "scrape_not_ok",
                  f"counts={counts}; halt — Laugavegur 39 must scrape ok for diagnostic to be meaningful")
        return 3

    log_event(conn, "INFO", "run", None, "diag_run_end",
              f"ok elapsed_s={time.monotonic()-started:.1f}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
