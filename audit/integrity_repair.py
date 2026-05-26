"""
integrity_repair.py — Phase 1.3 (Áfangi 0 weekend run)

Re-verifies every image_index row with downloaded=1: checks file exists
at local_path, updates file_size_bytes + last_verified_at if so, marks
downloaded=0 if missing. Idempotent.

The legacy collator already did this check inline as it imported each
legacy myndir row. This script catches anything that drifted between
collation and now (e.g., file deletion mid-run), and produces the
audit/integrity_repair_report.md the spec requires.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from weekend_run_status import get_writer  # noqa: E402

INDEX_DB = Path(r"D:\Gagnapakkar\image_index.db")
REPORT_PATH = Path(__file__).resolve().parent / "integrity_repair_report.md"


def main():
    sw = get_writer()
    sw.start()
    try:
        sw.set_phase("phase_1_storage_build")
        sw.set_subphase("integrity repair")
        sw.log("INFO", f"Phase 1.3 integrity repair started; index_db={INDEX_DB}")

        conn = sqlite3.connect(INDEX_DB)
        conn.execute("PRAGMA journal_mode=WAL")

        # Pre-stats
        n_total = conn.execute("SELECT COUNT(*) FROM image_index").fetchone()[0]
        n_dl_pre = conn.execute(
            "SELECT COUNT(*) FROM image_index WHERE downloaded=1"
        ).fetchone()[0]
        sw.log("INFO", f"image_index.db: {n_total:,} rows, {n_dl_pre:,} marked downloaded=1")
        sw.set_progress(0, n_dl_pre)

        # Stream downloaded=1 rows, check existence
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        BATCH = 5000
        checked = 0
        verified = 0
        flipped = 0
        missing_paths = []  # capture first 50 for the report
        cur = conn.cursor()
        cur.execute(
            "SELECT fastnum, image_nr, local_path FROM image_index WHERE downloaded=1"
        )
        updates_verify = []
        updates_flip = []
        while True:
            rows = cur.fetchmany(BATCH)
            if not rows:
                break
            for fn, nr, lp in rows:
                checked += 1
                p = Path(lp)
                try:
                    st = p.stat()
                    updates_verify.append((now_iso, st.st_size, fn, nr))
                    verified += 1
                except OSError:
                    updates_flip.append((fn, nr))
                    flipped += 1
                    if len(missing_paths) < 50:
                        missing_paths.append(lp)
            # apply in batch
            if updates_verify:
                conn.executemany(
                    "UPDATE image_index SET last_verified_at=?, file_size_bytes=? "
                    "WHERE fastnum=? AND image_nr=?",
                    updates_verify,
                )
                updates_verify.clear()
            if updates_flip:
                conn.executemany(
                    "UPDATE image_index SET downloaded=0 WHERE fastnum=? AND image_nr=?",
                    updates_flip,
                )
                updates_flip.clear()
            conn.commit()
            sw.set_progress(checked, n_dl_pre)
            if checked % 100_000 == 0:
                sw.log("INFO", f"  verified {verified:,}, flipped {flipped:,} of {checked:,}/{n_dl_pre:,}")

        sw.log("INFO", f"COMPLETE checked={checked:,} verified={verified:,} flipped={flipped:,}")

        # Post-stats
        n_dl_post = conn.execute(
            "SELECT COUNT(*) FROM image_index WHERE downloaded=1"
        ).fetchone()[0]
        n_dist_dl = conn.execute(
            "SELECT COUNT(DISTINCT fastnum) FROM image_index WHERE downloaded=1"
        ).fetchone()[0]
        total_bytes = conn.execute(
            "SELECT SUM(file_size_bytes) FROM image_index WHERE downloaded=1"
        ).fetchone()[0] or 0

        write_report(checked, verified, flipped, missing_paths,
                     n_total, n_dl_pre, n_dl_post, n_dist_dl, total_bytes)
        conn.close()
        sw.log("INFO", f"integrity_repair_report.md written")
    finally:
        sw.stop()


def write_report(checked, verified, flipped, missing_paths,
                 n_total, n_dl_pre, n_dl_post, n_dist_dl, total_bytes):
    text = f"""# Phase 1.3 — Integrity repair report

**Date**: {datetime.now(timezone.utc).isoformat(timespec='seconds')}
**Source DB**: D:\\Gagnapakkar\\image_index.db

## Repair pass

- rows checked (downloaded=1 at start): {checked:,}
- verified existing on disk (last_verified_at + file_size_bytes set): {verified:,}
- flipped to downloaded=0 (file missing): {flipped:,}
- repair rate: {(flipped/checked*100 if checked else 0):.2f}% missing

## image_index.db post-state

- total rows: {n_total:,}
- downloaded=1 rows (verified, with file_size_bytes set): {n_dl_post:,}
- distinct fastnums with ≥1 verified image: {n_dist_dl:,}
- total verified disk bytes: {total_bytes:,} ({total_bytes/1024/1024/1024:.2f} GB)

## Missing-on-disk samples (first 50)

{chr(10).join('- ' + p for p in missing_paths) if missing_paths else '_(none)_'}

## Notes

These rows are now `downloaded=0` and will be re-fetched from `original_url`
during Phase 3 (Stage B image bootstrap). The collator already did this
check inline at import; this script re-verifies and catches drift between
collation and now (typically zero, occasionally one or two if filesystem
activity happens mid-run).
"""
    REPORT_PATH.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
