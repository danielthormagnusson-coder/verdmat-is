# Legacy myndir → image_index.db collation log

**Date**: 2026-05-08T12:40:47+00:00
**Source**: D:\Gagnapakkar\fasteignir{,1,2,3,4}.db (5 legacy myndir tables)
**Target**: D:\Gagnapakkar\image_index.db (canonical image index, locked schema)

## Totals

- rows read: 1,156,588
- rows inserted into image_index: 1,153,063
- rows skipped (duplicate (fastnum, image_nr)): 3,525
- rows where downloaded=1 but file not on disk: 273,088

## Final image_index.db state

- total rows: 1,153,063
- downloaded=1 (verified on disk): 879,904
- downloaded=0 (URL captured, file missing or never fetched): 273,159
- distinct fastnums covered: 48,691

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

`local_path` is RELATIVE (e.g. `myndir\2294894\1.jpg` or `2294894\1.jpg`)
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
  `D:\Gagnapakkar\images\<fastnum>\<image_nr>.jpg` (where the file
  WILL land on download), not a legacy archive path.
