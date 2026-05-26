# Phase 1.5 — Storage policy validation report

**Date**: 2026-05-08T12:54:05+00:00
**Result**: **PASS**
**Fresh controls**: [2503338, 2511365, 2512279, 2525474, 2534360]
**Scrape counts**: {'ok': 5, 'not_found': 0, 'error': 0, 'other': 0}
**Elapsed**: 126.1 s

## Per-property image counts

| fastnum | own (source=self) | cross-property | image_index rows | files on disk | check |
|---|---:|---:|---:|---:|---|
| 2503338 | 150 | 59 | 209 | 209 | ✓ |
| 2511365 | 48 | 0 | 48 | 48 | ✓ |
| 2512279 | 22 | 0 | 22 | 22 | ✓ |
| 2525474 | 0 | 0 | 0 | 0 | ✓ |
| 2534360 | 0 | 0 | 0 | 0 | ✓ |

## image_index.db deltas

- new rows added: 0
- newly downloaded=1: 0
- new cross_property_refs rows: 0
- total files on disk after run (across all 5 fastnums): 279

## Storage policy posture

- Layout: `D:\Gagnapakkar\images\<source_fastnum>\<n>.jpg`
- Cross-property URLs land in `<source_fastnum>` not `<referencing_fastnum>`,
  recorded as a `cross_property_refs` row.
- Idempotent skip via `image_index.original_url` lookup; pre-existing
  downloads are reused without a re-fetch.
- Pass criteria: per-property `image_index_rows` count must match
  `files_on_disk` count. Mismatch => silent loss => Phase 1.5 fails =>
  weekend run halts.
