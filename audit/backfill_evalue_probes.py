"""
backfill_evalue_probes.py — three additional probe sweeps after pilot v1

Reuses scraper plumbing from `backfill_evalue_range`. Each probe is its own
stage label so the existing pilot rows in `backfill_pilot.db` are untouched.

Probes (per Danni 2026-05-07 follow-up directive):
  1. probe_2400000  → 2,400,000-2,400,099 (start of 2.4M bucket)
  2. probe_2499900  → 2,499,900-2,499,999 (end of 2.4M bucket; upper boundary)
  3. probe_2541715  → 2,541,715-2,541,814 (trailing range above current MAX)

Same 3-action POST mechanic, same 1-req/sec throttle, same halt-on-Cloudflare
contract. Run sequentially in order. Total expected wall-clock ~17 min.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Reuse the pilot scraper module verbatim
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backfill_evalue_range import (  # noqa: E402
    AUDIT_DIR,
    DB_PATH,
    HaltSignal,
    init_db,
    log_event,
    run_stage,
)


PROBES = [
    ("probe_2400000", range(2_400_000, 2_400_100)),
    ("probe_2499900", range(2_499_900, 2_500_000)),
    ("probe_2541715", range(2_541_715, 2_541_815)),
]


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    conn = init_db(DB_PATH)
    overall_started = time.monotonic()
    log_event(conn, "INFO", "init", None, "probes_run_start",
              f"db={DB_PATH} probes={[p[0] for p in PROBES]}")

    summary = {}
    for stage_label, rng in PROBES:
        fastnums = list(rng)
        try:
            counts, elapsed = run_stage(conn, fastnums, stage_label)
        except HaltSignal as e:
            log_event(conn, "HALT", stage_label, None, "probe_aborted", str(e))
            log_event(conn, "INFO", "run", None, "probes_run_end",
                      f"aborted_in_{stage_label} elapsed_s={time.monotonic()-overall_started:.1f}")
            return 2
        summary[stage_label] = {"counts": counts, "elapsed_s": round(elapsed, 1)}

    overall_elapsed = time.monotonic() - overall_started
    log_event(conn, "INFO", "run", None, "probes_run_end",
              f"all_probes_ok elapsed_s={overall_elapsed:.1f} summary={summary}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
