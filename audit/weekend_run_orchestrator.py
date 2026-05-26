"""
weekend_run_orchestrator.py — top-level entry for the Áfangi 0 weekend run.

Runs Phase 1.2 → 1.3 → 1.5 → 2 → 3 in sequence. Each phase is idempotent /
resume-safe; if a phase has already completed (per its durable state) the
orchestrator skips it. If a phase halts, the orchestrator exits non-zero;
re-running the orchestrator picks up from the halt point.

Phase 4 (final commit + push) is NOT done by this script — that step
happens in a Claude session at the end of the run, since it requires
human-style git commit message composition + repo-level coordination.

Usage:
    python audit/weekend_run_orchestrator.py

Status: monitor `audit/weekend_run_status.md` from any terminal. Halt
reasons are also written there.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from weekend_run_status import get_writer  # noqa: E402

INDEX_DB_PATH = Path(r"D:\Gagnapakkar\image_index.db")
STAGE_A_DB = Path(__file__).resolve().parent / "stage_a_augl_staging.db"


def phase_1_done():
    """Phase 1 is durably complete if image_index.db exists with 1M+ rows."""
    if not INDEX_DB_PATH.exists():
        return False
    try:
        c = sqlite3.connect(INDEX_DB_PATH, timeout=5)
        n = c.execute("SELECT COUNT(*) FROM image_index").fetchone()[0]
        c.close()
        return n > 1_000_000
    except Exception:
        return False


def phase_2_done():
    """Phase 2 is done if stage_a DB has rows for ≥99% of 124,835 fastnums."""
    if not STAGE_A_DB.exists():
        return False
    try:
        c = sqlite3.connect(STAGE_A_DB, timeout=5)
        n = c.execute("SELECT COUNT(*) FROM stage_a_augl").fetchone()[0]
        c.close()
        return n >= 124_000  # tolerate small slop
    except Exception:
        return False


def phase_3_done():
    """Phase 3 done if image_index has zero downloaded=0 rows whose URL was discovered."""
    if not INDEX_DB_PATH.exists():
        return False
    try:
        c = sqlite3.connect(INDEX_DB_PATH, timeout=5)
        # Note: downloaded=0 rows WILL exist for URLs that 404'd. So we can't
        # use 0 as the gate. Instead: phase 3 is "done" if it ran to completion
        # at least once and no halts. A simpler heuristic: phase 4 will check
        # this via a sentinel file written by phase 3.
        sentinel = Path(__file__).resolve().parent / "phase_3_complete.flag"
        c.close()
        return sentinel.exists()
    except Exception:
        return False


def run_module(module_name, phase_label):
    """Import + invoke .main() of a phase module. Returns exit code."""
    sw = get_writer()
    sw.log("INFO", f"orchestrator: starting {phase_label} ({module_name})")
    mod = importlib.import_module(module_name)
    rc = mod.main() or 0
    sw.log("INFO", f"orchestrator: {phase_label} returned {rc}")
    return rc


def main():
    sw = get_writer()
    sw.start()
    try:
        sw.log("INFO", "=== weekend run orchestrator started ===")

        # Phase 1
        if phase_1_done():
            sw.log("INFO", "Phase 1: already done (image_index.db has >1M rows), skipping")
            sw.complete_phase("phase_1_storage_build")
        else:
            for mod, label in [
                ("legacy_myndir_collator", "phase 1.2 collator"),
                ("integrity_repair", "phase 1.3 integrity repair"),
                ("storage_policy_validator", "phase 1.5 validator"),
            ]:
                rc = run_module(mod, label)
                if rc != 0:
                    sw.add_halt(f"orchestrator: {label} returned {rc}")
                    return rc
            sw.complete_phase("phase_1_storage_build")

        # Phase 2
        if phase_2_done():
            sw.log("INFO", "Phase 2: already done, skipping")
            sw.complete_phase("phase_2_stage_a_augl_refresh")
        else:
            rc = run_module("stage_a_augl_refresh", "phase 2 stage-a augl-refresh")
            if rc != 0:
                sw.add_halt(f"orchestrator: phase 2 returned {rc}")
                return rc

        # Phase 3
        if phase_3_done():
            sw.log("INFO", "Phase 3: already done, skipping")
            sw.complete_phase("phase_3_stage_b_image_bootstrap")
        else:
            rc = run_module("stage_b_image_bootstrap", "phase 3 stage-b image bootstrap")
            if rc != 0:
                sw.add_halt(f"orchestrator: phase 3 returned {rc}")
                return rc
            # write sentinel
            (Path(__file__).resolve().parent / "phase_3_complete.flag").write_text(
                "Phase 3 completed", encoding="utf-8"
            )

        sw.log("INFO", "=== orchestrator: phases 1-3 complete; commit/push (phase 4) is manual ===")
        return 0
    finally:
        sw.stop()


if __name__ == "__main__":
    sys.exit(main())
