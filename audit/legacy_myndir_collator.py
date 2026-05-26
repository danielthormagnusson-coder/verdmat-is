"""
legacy_myndir_collator.py — Phase 1.2 (Áfangi 0 weekend run)

Builds D:\\Gagnapakkar\\image_index.db with the LOCKED schema (per task spec)
by collating the 5 legacy `myndir` tables in D:\\Gagnapakkar\\fasteignir*.db.

For each legacy myndir row (fastnum, nr, url, local_path, downloaded):
  - Resolve absolute disk location by trying every known archive root
  - INSERT into image_index with first-seen-at = now, last_verified_at = NULL
  - Track source_db so we can attribute provenance later

Schema variations across legacy DBs are documented in
audit/legacy_myndir_schema.md (sister script output).

Idempotent: re-runnable. Existing image_index rows preserved
(INSERT OR IGNORE on (fastnum, image_nr) primary key).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from weekend_run_status import get_writer  # noqa: E402

INDEX_DB = Path(r"D:\Gagnapakkar\image_index.db")
LEGACY_DBS = [
    Path(r"D:\Gagnapakkar\fasteignir.db"),
    Path(r"D:\Gagnapakkar\fasteignir1.db"),
    Path(r"D:\Gagnapakkar\fasteignir2.db"),
    Path(r"D:\Gagnapakkar\fasteignir3.db"),
    Path(r"D:\Gagnapakkar\fasteignir4.db"),
]
ARCHIVE_ROOTS = [
    # Order matters — first existing match wins per (fastnum, nr).
    # Most-populated roots first to minimize stat() probe count.
    Path(r"D:\Gagnapakki 3 - fasteignir\myndir"),
    Path(r"D:\Gagnapakki 4 - fasteignir\myndir"),
    Path(r"D:\Gagnapakki 5 - fasteignir\myndir"),
    Path(r"D:\Gagnapakki 1"),  # flat layout, no `myndir/` subdir
    Path(r"D:\Gagnapakki 2 - fasteignir\myndir"),
    Path(r"D:\Leiguskra - scrape\Gagnasafn\myndir"),
    Path(r"D:\Gagnapakkar\images"),  # pilot v3 + new canonical
]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS image_index (
    fastnum INTEGER NOT NULL,
    image_nr INTEGER NOT NULL,
    original_url TEXT NOT NULL,
    local_path TEXT NOT NULL,
    downloaded INTEGER NOT NULL DEFAULT 0,
    source_db TEXT,
    first_seen_at TEXT NOT NULL,
    last_verified_at TEXT,
    file_size_bytes INTEGER,
    PRIMARY KEY (fastnum, image_nr)
);
CREATE INDEX IF NOT EXISTS idx_image_index_url ON image_index(original_url);
CREATE INDEX IF NOT EXISTS idx_image_index_downloaded ON image_index(downloaded);

CREATE TABLE IF NOT EXISTS cross_property_refs (
    referencing_fastnum INTEGER NOT NULL,
    referenced_fastnum INTEGER NOT NULL,
    image_url TEXT NOT NULL,
    augl_id TEXT,
    augl_capture_at TEXT NOT NULL,
    PRIMARY KEY (referencing_fastnum, image_url, augl_id)
);
CREATE INDEX IF NOT EXISTS idx_cross_refs_referenced ON cross_property_refs(referenced_fastnum);

CREATE TABLE IF NOT EXISTS collation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    source_db TEXT,
    rows_read INTEGER,
    rows_inserted INTEGER,
    rows_skipped_dup INTEGER,
    notes TEXT
);
"""


def init_index_db():
    INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(INDEX_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    for stmt in SCHEMA_SQL.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()
    return conn


def resolve_absolute_path(legacy_local_path, fastnum_str, image_nr):
    """Find the actual file on disk for a given legacy myndir row.

    Legacy local_path is relative (e.g., 'myndir\\2294894\\1.jpg' or
    '2294894\\1.jpg' depending on which legacy variant wrote it).

    Try each known archive root + the file part of legacy_local_path.
    Also handle the flat-layout case (Gagnapakki 1) where the legacy path
    might just be '<fastnum>\\<n>.jpg' without a 'myndir' prefix.
    """
    # Normalize legacy path to forward slashes
    rel = legacy_local_path.replace("\\", "/").lstrip("/")
    # Strip any leading 'myndir/' since it's a stable prefix in some roots
    rel_stripped = rel
    if rel_stripped.startswith("myndir/"):
        rel_stripped = rel_stripped[len("myndir/"):]

    # Candidate file basenames to try at each root
    fastnum_subdir = fastnum_str
    file_basename = rel.rsplit("/", 1)[-1]  # e.g. "1.jpg"

    for root in ARCHIVE_ROOTS:
        candidate = root / fastnum_subdir / file_basename
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def collate_one(conn, legacy_db_path, sw):
    sw.set_subphase(f"collating {legacy_db_path.name}")
    legacy = sqlite3.connect(legacy_db_path)
    rows_read = 0
    rows_inserted = 0
    rows_skipped_dup = 0
    rows_no_disk = 0
    cur_in = legacy.cursor()
    # Stream rows from legacy myndir
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    BATCH = 5000
    last_progress = 0
    total = legacy.execute("SELECT COUNT(*) FROM myndir").fetchone()[0]
    sw.set_progress(0, total)

    cur_out = conn.cursor()
    for chunk_offset in range(0, total, BATCH):
        rows = cur_in.execute(
            "SELECT fastnum, nr, url, local_path, downloaded "
            "FROM myndir ORDER BY id LIMIT ? OFFSET ?",
            (BATCH, chunk_offset),
        ).fetchall()
        for fastnum_str, nr, url, local_path, downloaded in rows:
            rows_read += 1
            try:
                fn_int = int(fastnum_str)
                nr_int = int(nr)
            except (ValueError, TypeError):
                continue
            # Resolve absolute path (only if downloaded=1; else placeholder)
            abs_path = None
            file_size = None
            verified_at = None
            if downloaded == 1:
                abs_path = resolve_absolute_path(local_path or "", fastnum_str, nr_int)
                if abs_path is not None:
                    try:
                        st = abs_path.stat()
                        file_size = st.st_size
                        verified_at = now_iso
                    except OSError:
                        abs_path = None
                if abs_path is None:
                    rows_no_disk += 1
                    # File missing on disk — record URL but mark downloaded=0
                    # so Phase 3 will re-fetch it.
                    downloaded = 0
            local_path_canonical = (
                str(abs_path) if abs_path
                else str(Path(r"D:\Gagnapakkar\images") / fastnum_str / f"{nr_int}.jpg")
            )
            try:
                cur_out.execute(
                    """
                    INSERT INTO image_index
                      (fastnum, image_nr, original_url, local_path, downloaded,
                       source_db, first_seen_at, last_verified_at, file_size_bytes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (fn_int, nr_int, url, local_path_canonical, downloaded,
                     legacy_db_path.name, now_iso, verified_at, file_size),
                )
                rows_inserted += 1
            except sqlite3.IntegrityError:
                rows_skipped_dup += 1
        conn.commit()
        # progress: rows_read / total
        sw.set_progress(rows_read, total)
        if rows_read - last_progress >= 50_000:
            sw.log("INFO", f"  {legacy_db_path.name}: {rows_read:,}/{total:,} read; "
                           f"inserted={rows_inserted:,} dup={rows_skipped_dup:,} "
                           f"no_disk={rows_no_disk:,}")
            last_progress = rows_read

    legacy.close()
    cur_out.execute(
        """INSERT INTO collation_log (ts, source_db, rows_read, rows_inserted,
                                       rows_skipped_dup, notes) VALUES (?, ?, ?, ?, ?, ?)""",
        (now_iso, legacy_db_path.name, rows_read, rows_inserted, rows_skipped_dup,
         f"no_disk={rows_no_disk}"),
    )
    conn.commit()
    sw.log("INFO", f"  {legacy_db_path.name}: complete. read={rows_read:,} "
                   f"inserted={rows_inserted:,} dup={rows_skipped_dup:,} "
                   f"no_disk={rows_no_disk:,}")
    return {"rows_read": rows_read, "rows_inserted": rows_inserted,
            "rows_skipped_dup": rows_skipped_dup, "no_disk": rows_no_disk}


def main():
    sw = get_writer()
    sw.start()
    try:
        sw.set_phase("phase_1_storage_build")
        sw.set_subphase("init image_index.db")
        sw.log("INFO", f"Phase 1.2 collator started; index_db={INDEX_DB}")
        conn = init_index_db()

        totals = {"rows_read": 0, "rows_inserted": 0,
                  "rows_skipped_dup": 0, "no_disk": 0}
        for db in LEGACY_DBS:
            if not db.exists():
                sw.log("WARN", f"legacy DB missing: {db}")
                continue
            r = collate_one(conn, db, sw)
            for k in totals:
                totals[k] += r[k]

        sw.log("INFO", f"COLLATION TOTALS: {totals}")
        # Final image_index stats
        n_rows = conn.execute("SELECT COUNT(*) FROM image_index").fetchone()[0]
        n_dl = conn.execute(
            "SELECT COUNT(*) FROM image_index WHERE downloaded=1"
        ).fetchone()[0]
        n_dist_fn = conn.execute(
            "SELECT COUNT(DISTINCT fastnum) FROM image_index"
        ).fetchone()[0]
        sw.log("INFO", f"image_index.db: rows={n_rows:,} downloaded={n_dl:,} "
                       f"distinct_fastnums={n_dist_fn:,}")
        conn.close()

        # Write the schema-doc + collation-log markdowns
        write_schema_doc(totals, n_rows, n_dl, n_dist_fn)
    finally:
        sw.stop()


def write_schema_doc(totals, n_rows, n_dl, n_dist_fn):
    AUDIT_DIR = Path(__file__).resolve().parent
    doc = AUDIT_DIR / "legacy_myndir_collation_log.md"
    text = f"""# Legacy myndir → image_index.db collation log

**Date**: {datetime.now(timezone.utc).isoformat(timespec='seconds')}
**Source**: D:\\Gagnapakkar\\fasteignir{{,1,2,3,4}}.db (5 legacy myndir tables)
**Target**: D:\\Gagnapakkar\\image_index.db (canonical image index, locked schema)

## Totals

- rows read: {totals['rows_read']:,}
- rows inserted into image_index: {totals['rows_inserted']:,}
- rows skipped (duplicate (fastnum, image_nr)): {totals['rows_skipped_dup']:,}
- rows where downloaded=1 but file not on disk: {totals['no_disk']:,}

## Final image_index.db state

- total rows: {n_rows:,}
- downloaded=1 (verified on disk): {n_dl:,}
- downloaded=0 (URL captured, file missing or never fetched): {n_rows - n_dl:,}
- distinct fastnums covered: {n_dist_fn:,}

## Schema variations across legacy DBs

All 5 legacy DBs (`fasteignir.db`, `fasteignir1.db`, `fasteignir2.db`,
`fasteignir3.db`, `fasteignir4.db`) share the identical `myndir` schema:

```sql
CREATE TABLE myndir (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fastnum TEXT,
    nr INTEGER,
    url TEXT,
    local_path TEXT,
    downloaded INTEGER DEFAULT 0,
    UNIQUE(fastnum, nr)
);
```

`local_path` is RELATIVE (e.g. `myndir\\2294894\\1.jpg` or `2294894\\1.jpg`)
and the absolute archive root is implicit (the working directory where the
legacy scraper variant ran). Resolved during collation by probing
`ARCHIVE_ROOTS` order: `Gagnapakki 3 → 4 → 5 → 1 → 2 → Leiguskra → Gagnapakkar/images`
and taking the first match.

## Notes

- Some `(fastnum, image_nr)` keys appear in multiple legacy DBs; first-write
  wins, subsequent inserts skip via PRIMARY KEY constraint and increment
  `rows_skipped_dup`. The `source_db` column reflects which legacy DB the
  first occurrence came from; later DBs' identical rows are not retained.
- `last_verified_at` is set to collation time only for `downloaded=1` rows
  whose file was located on disk. `downloaded=0` rows are placeholders
  awaiting Phase 3 fetch.
- `local_path` for `downloaded=0` rows is set to the canonical
  `D:\\Gagnapakkar\\images\\<fastnum>\\<image_nr>.jpg` (where the file
  WILL land on download), not a legacy archive path.
"""
    doc.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
