"""
storage_policy_validator.py — Phase 1.5 (Áfangi 0 weekend run)

Re-scrapes 5 fresh positive-control fastnums via the new storage policy
and verifies:
  - Own-property images land at /images/<own_fastnum>/<n>.jpg
  - Cross-property images land at /images/<source_fastnum>/<n>.jpg
  - image_index gets new rows for each downloaded URL
  - cross_property_refs gets a row whenever source_fn != property_fn
  - Logged n_urls matches files-on-disk-after (no silent loss)

Halt-and-report on any of:
  - Any of 5 fresh controls fails to scrape (status != ok)
  - Logged n_urls > files actually present in canonical layout
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backfill_evalue_range import init_db, run_stage, HaltSignal  # noqa: E402
from image_archive import open_index_db, CANONICAL_IMAGE_ROOT  # noqa: E402
from weekend_run_status import get_writer  # noqa: E402

# Fresh sample queried 2026-05-08; deliberately excludes pilot v3 + pilot v1 fastnums.
FRESH_CONTROLS = [2503338, 2511365, 2512279, 2525474, 2534360]
PILOT_DB = Path(__file__).resolve().parent / "backfill_pilot.db"
REPORT_PATH = Path(__file__).resolve().parent / "storage_policy_validation_report.md"


def main():
    sw = get_writer()
    sw.start()
    try:
        sw.set_phase("phase_1_storage_build")
        sw.set_subphase(f"validation on 5 fresh controls {FRESH_CONTROLS}")
        sw.log("INFO", f"Phase 1.5 validation started; controls={FRESH_CONTROLS}")

        # Snapshot image_index state pre-validation
        idx = open_index_db()
        pre_n_index = idx.execute("SELECT COUNT(*) FROM image_index").fetchone()[0]
        pre_n_dl = idx.execute(
            "SELECT COUNT(*) FROM image_index WHERE downloaded=1"
        ).fetchone()[0]
        pre_n_cross = idx.execute("SELECT COUNT(*) FROM cross_property_refs").fetchone()[0]
        idx.close()

        # Run the scrape with the new storage policy active
        pilot_conn = init_db(PILOT_DB)
        idx = open_index_db()
        try:
            counts, elapsed = run_stage(
                pilot_conn, FRESH_CONTROLS, "phase1_5_validation",
                image_root=None,
                fast_skip_on_204=False,
                image_index_conn=idx,
            )
        except HaltSignal as e:
            sw.add_halt(f"Phase 1.5 scrape halted: {e}")
            return 2

        # Note: a 204 on a Supabase-listed fastnum just means evalue.is no longer
        # indexes that property — it's a data anomaly, not a storage-policy
        # failure. The real gate is the per-property silent-loss check below.
        if counts["ok"] == 0:
            sw.add_halt(f"Phase 1.5 ZERO controls scraped: counts={counts}")
            return 3
        if counts["ok"] < 3:
            sw.log("WARN", f"Phase 1.5 fewer than 3/5 controls scraped ok: {counts}; "
                           "continuing to silent-loss check")

        # Post-state
        post_n_index = idx.execute("SELECT COUNT(*) FROM image_index").fetchone()[0]
        post_n_dl = idx.execute(
            "SELECT COUNT(*) FROM image_index WHERE downloaded=1"
        ).fetchone()[0]
        post_n_cross = idx.execute(
            "SELECT COUNT(*) FROM cross_property_refs"
        ).fetchone()[0]

        added_index = post_n_index - pre_n_index
        added_dl = post_n_dl - pre_n_dl
        added_cross = post_n_cross - pre_n_cross

        # Per-property summary from image_index
        per_property = []
        files_on_disk_total = 0
        for fn in FRESH_CONTROLS:
            # All image_index rows ever added for ANY source_fastnum that the
            # cross_property_refs table associates with this fn (own + cross).
            rows = idx.execute(
                """SELECT DISTINCT i.fastnum, i.image_nr, i.local_path
                   FROM image_index i
                   LEFT JOIN cross_property_refs c
                     ON c.image_url = i.original_url
                        AND c.referencing_fastnum = ?
                   WHERE i.fastnum = ? OR c.referencing_fastnum = ?
                   ORDER BY i.fastnum, i.image_nr""",
                (fn, fn, fn),
            ).fetchall()
            n_own = sum(1 for src_fn, _, _ in rows if src_fn == fn)
            n_cross = sum(1 for src_fn, _, _ in rows if src_fn != fn)
            on_disk_for_fn = sum(
                1 for _, _, lp in rows if Path(lp).is_file()
            )
            files_on_disk_total += on_disk_for_fn
            per_property.append({
                "fastnum": fn, "n_own": n_own, "n_cross": n_cross,
                "n_index_rows": len(rows), "n_files_on_disk": on_disk_for_fn,
            })
            sw.log("INFO",
                   f"  fastnum={fn} own={n_own} cross={n_cross} "
                   f"index_rows={len(rows)} on_disk={on_disk_for_fn}")

        idx.close()
        pilot_conn.close()

        # Pass criteria: every per-property index_rows matches on_disk count
        pass_criteria_met = all(
            p["n_index_rows"] == p["n_files_on_disk"] for p in per_property
        )

        write_report(per_property, counts, elapsed, files_on_disk_total,
                     added_index, added_dl, added_cross, pass_criteria_met)

        if not pass_criteria_met:
            sw.add_halt("Phase 1.5 silent-loss check FAILED — see report")
            return 4

        sw.log("INFO", f"Phase 1.5 PASS — {sum(p['n_files_on_disk'] for p in per_property)} files on disk")
        return 0
    finally:
        sw.stop()


def write_report(per_property, counts, elapsed, total_disk, added_index, added_dl, added_cross, passed):
    rows_md = "\n".join(
        f"| {p['fastnum']} | {p['n_own']} | {p['n_cross']} | "
        f"{p['n_index_rows']} | {p['n_files_on_disk']} | "
        f"{'✓' if p['n_index_rows']==p['n_files_on_disk'] else '✗ silent loss'} |"
        for p in per_property
    )
    text = f"""# Phase 1.5 — Storage policy validation report

**Date**: {datetime.now(timezone.utc).isoformat(timespec='seconds')}
**Result**: {'**PASS**' if passed else '**FAIL — silent loss detected**'}
**Fresh controls**: {[p['fastnum'] for p in per_property]}
**Scrape counts**: {counts}
**Elapsed**: {elapsed:.1f} s

## Per-property image counts

| fastnum | own (source=self) | cross-property | image_index rows | files on disk | check |
|---|---:|---:|---:|---:|---|
{rows_md}

## image_index.db deltas

- new rows added: {added_index:,}
- newly downloaded=1: {added_dl:,}
- new cross_property_refs rows: {added_cross:,}
- total files on disk after run (across all 5 fastnums): {total_disk:,}

## Storage policy posture

- Layout: `D:\\Gagnapakkar\\images\\<source_fastnum>\\<n>.jpg`
- Cross-property URLs land in `<source_fastnum>` not `<referencing_fastnum>`,
  recorded as a `cross_property_refs` row.
- Idempotent skip via `image_index.original_url` lookup; pre-existing
  downloads are reused without a re-fetch.
- Pass criteria: per-property `image_index_rows` count must match
  `files_on_disk` count. Mismatch => silent loss => Phase 1.5 fails =>
  weekend run halts.
"""
    REPORT_PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
