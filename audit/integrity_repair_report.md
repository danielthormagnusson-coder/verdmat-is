# Phase 1.3 — Integrity repair report

**Date**: 2026-05-08T12:43:24+00:00
**Source DB**: D:\Gagnapakkar\image_index.db

## Repair pass

- rows checked (downloaded=1 at start): 879,904
- verified existing on disk (last_verified_at + file_size_bytes set): 879,904
- flipped to downloaded=0 (file missing): 0
- repair rate: 0.00% missing

## image_index.db post-state

- total rows: 1,153,063
- downloaded=1 rows (verified, with file_size_bytes set): 879,904
- distinct fastnums with ≥1 verified image: 38,342
- total verified disk bytes: 207,863,285,463 (193.59 GB)

## Missing-on-disk samples (first 50)

_(none)_

## Notes

These rows are now `downloaded=0` and will be re-fetched from `original_url`
during Phase 3 (Stage B image bootstrap). The collator already did this
check inline at import; this script re-verifies and catches drift between
collation and now (typically zero, occasionally one or two if filesystem
activity happens mid-run).
