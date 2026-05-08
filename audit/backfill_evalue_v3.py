"""
backfill_evalue_v3.py — Stage 1 phases 2-4 with image-download enabled.

Phase 2 — fresh 5 positive controls (queried from Supabase 2026-05-07T14:xx UTC),
          full 3-action scrape + image downloads. HARD HALT if any !=ok or
          if image-download fails on a property that should have images.

Phase 3 — trailing range walk 2,541,715-2,546,714 (5,000 candidates above
          current Supabase MAX). fast_skip_on_204 enabled — non-hits cost
          one POST instead of three. Image download enabled for hits.

Phase 4 — sub-gap probe 2,389,000-2,389,099 (100 candidates mid-2.3M-bucket
          tail-gap). Same pattern as Phase 3.

Halt-on-failure: if any phase raises HaltSignal (Cloudflare, 403, HTML, etc.)
the runner exits non-zero immediately. Phase ordering is sequential — a halt
in Phase 2 prevents Phase 3 from starting, etc.

Output: appended to audit/backfill_pilot.db with new stage labels:
  - phase2_validation
  - phase3_trailing
  - phase4_subgap

Image archive: D:\\Gagnapakkar\\images\\<fastnum>\\<basename>.<ext>
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backfill_evalue_range import (  # noqa: E402
    AUDIT_DIR,
    DB_PATH,
    HaltSignal,
    IMAGE_ROOT,
    init_db,
    log_event,
    run_stage,
)


# Fresh Supabase sample queried 2026-05-07; range 2,500,015-2,541,714 (the
# 2.5M dense-bucket fastnums Danni already has data for, used as positive
# controls for re-scrape correctness on top of the image-download path).
PHASE2_POSITIVE_CONTROLS = [2501932, 2511402, 2527607, 2528464, 2534391]

PHASE3_RANGE = range(2_541_715, 2_546_715)  # 5,000 candidates inclusive of start exclusive of end
PHASE4_RANGE = range(2_389_000, 2_389_100)  # 100 candidates


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)

    conn = init_db(DB_PATH)
    log_event(conn, "INFO", "init", None, "v3_run_start",
              f"db={DB_PATH} image_root={IMAGE_ROOT} "
              f"phase2={PHASE2_POSITIVE_CONTROLS} "
              f"phase3=[{PHASE3_RANGE.start}-{PHASE3_RANGE.stop - 1}] "
              f"phase4=[{PHASE4_RANGE.start}-{PHASE4_RANGE.stop - 1}]")

    overall_started = time.monotonic()

    # --- Phase 2 ---
    try:
        p2_counts, p2_elapsed = run_stage(
            conn, PHASE2_POSITIVE_CONTROLS, "phase2_validation",
            image_root=IMAGE_ROOT, fast_skip_on_204=False,
        )
    except HaltSignal as e:
        log_event(conn, "HALT", "phase2_validation", None, "stage_aborted", str(e))
        log_event(conn, "INFO", "run", None, "v3_run_end",
                  f"aborted_in_phase2 elapsed_s={time.monotonic()-overall_started:.1f}")
        return 2

    if p2_counts["ok"] != len(PHASE2_POSITIVE_CONTROLS):
        log_event(conn, "HALT", "phase2_validation", None, "p2_not_all_ok",
                  f"counts={p2_counts}; halting before phase 3")
        return 3

    log_event(conn, "INFO", "phase2_validation", None, "p2_pass",
              "image-download path validated; proceeding to trailing walk")

    # --- Phase 3 ---
    try:
        p3_counts, p3_elapsed = run_stage(
            conn, list(PHASE3_RANGE), "phase3_trailing",
            image_root=IMAGE_ROOT, fast_skip_on_204=True,
        )
    except HaltSignal as e:
        log_event(conn, "HALT", "phase3_trailing", None, "stage_aborted", str(e))
        log_event(conn, "INFO", "run", None, "v3_run_end",
                  f"aborted_in_phase3 elapsed_s={time.monotonic()-overall_started:.1f}")
        return 4

    log_event(conn, "INFO", "phase3_trailing", None, "p3_done",
              f"counts={p3_counts} elapsed_s={p3_elapsed:.1f}")

    # --- Phase 4 ---
    try:
        p4_counts, p4_elapsed = run_stage(
            conn, list(PHASE4_RANGE), "phase4_subgap",
            image_root=IMAGE_ROOT, fast_skip_on_204=True,
        )
    except HaltSignal as e:
        log_event(conn, "HALT", "phase4_subgap", None, "stage_aborted", str(e))
        log_event(conn, "INFO", "run", None, "v3_run_end",
                  f"aborted_in_phase4 elapsed_s={time.monotonic()-overall_started:.1f}")
        return 5

    overall_elapsed = time.monotonic() - overall_started
    log_event(conn, "INFO", "run", None, "v3_run_end",
              f"all_phases_ok elapsed_s={overall_elapsed:.1f} "
              f"p2={p2_counts} p3={p3_counts} p4={p4_counts}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
