# Weekend run — factual inventory (2026-05-18)

Numbers only. No interpretation. See `weekend_run_summary.md` for narrative.

## Timeline

| When (UTC) | Event |
|---|---|
| 2026-05-08T12:35:22 | Orchestrator started — Phase 1.2 collator first run |
| 2026-05-12 morning | Resume after initial WU reboot (per memory; not in this log range) |
| 2026-05-13T04:51 | Windows Update auto-restart killed orchestrator mid Phase 2 (row 97,800/124,835) |
| 2026-05-13T09:15:07 | Orchestrator resumed; finished Phase 2 |
| 2026-05-13T22:36:39 | Phase 3 (image bootstrap) URL-discovery complete: 1,478,257 new image_index rows; 1,751,416 queued for fetch |
| 2026-05-15T14:09:27 | HMS full-scrape (A→B→C) launched |
| 2026-05-15T21:46:17 | Phase 3 image bootstrap COMPLETE: 1,751,358 downloaded, 58 failed, 378,371,477,854 bytes |
| 2026-05-15T21:46:57 | Orchestrator returned 0; phases 1-3 complete |
| 2026-05-18T00:29:23 | HMS full-scrape COMPLETE |

## Orchestrator final phase state (from `weekend_run_status.md`)

- ✓ phase_1_storage_build (canonical image_index built from 5 legacy DBs)
- ✓ phase_2_stage_a_augl_refresh (124,835 fastnums)
- ✓ phase_3_stage_b_image_bootstrap (1.75M image fetches)
- phase_4_commit_push — pending (this task)

Halts during run: none after the 2026-05-13 WU recovery.

## `audit/stage_a_augl_staging.db` — Phase 2 output

- Size: 2,678,317,056 bytes (2.55 GB)
- Schema: `stage_a_augl(fastnum, augl_status, augl_json, n_ads, n_image_urls, latest_augl_iso, captured_at)`
- Rows: **124,835**
- All `augl_status=200` (zero failures across the whole Supabase manifest)
- `augl_json` length distribution:
  - ≤60 chars (empty `[[]]` response — no ad history): **65,811** (52.7%)
  - 61–2,000 chars: **1,375** (1.1%)
  - >2,000 chars (multi-ad history): **57,649** (46.2%)

## `D:\Gagnapakkar\image_index.db` — canonical index

- Size: 829,300,736 bytes (790.9 MB)
- Tables: `image_index`, `cross_property_refs`, `collation_log`, `sqlite_sequence`
- `image_index` schema: `(fastnum, image_nr, original_url, local_path, downloaded, source_db, first_seen_at, last_verified_at, file_size_bytes)`
- `image_index` rows: **2,631,485**
  - downloaded=1: **2,631,427** (99.998%)
  - downloaded=0: **58** (failed fetches; final residual)
- By `source_db`:
  | source_db | rows |
  |---|---:|
  | stage_a_discovery (NEW from Phase 2 augl payloads) | 1,478,257 |
  | fasteignir1.db (legacy myndir) | 437,212 |
  | fasteignir3.db (legacy myndir) | 278,516 |
  | fasteignir.db (legacy myndir) | 218,020 |
  | fasteignir4.db (legacy myndir) | 208,059 |
  | fasteignir2.db (legacy myndir) | 11,256 |
  | fresh_scrape (pilot v3 residual) | 165 |
- `cross_property_refs` rows: **134,635** (cross-property image refs identified in Phase 2 payloads)

## `D:\Gagnapakkar\images\` — final archive

- Files: **1,752,028**
- Bytes: **378,522,529,500** (352.53 GB)
- Matches `weekend_run.log` Phase 3 completion: downloaded=1,751,358 + 58 failed = 1,751,416 queued. The extra 612 files on disk represent the pre-existing legacy archive entries that were re-verified during Phase 1.5 storage policy validation.

## `audit/hms_archive_staging.db` — HMS full-scrape A/B/C

- Size: 410,259,456 bytes (391.3 MB)
- Schema: `hms_fasteign(fastnum, http_status, fasteign_data, fetched_at, phase, exists_in_hms)`
- Rows: **546,957**
- `fetched_at` range: 2026-05-15T14:03:00Z .. 2026-05-18T00:29:23Z (58h 26m wall-clock incl. smoke-test rows)
- By (phase, http_status):
  | phase | http | count | notes |
  |---|---:|---:|---|
  | A | 200 | **2,059** | backfill hits |
  | A | 500 | 6,838 | non-existent |
  | B | 200 | **124,738** | enrichment hits (99.92% of Supabase manifest) |
  | B | 500 | **97** | "ghost" Supabase rows HMS no longer recognises |
  | C | 200 | **28,134** | sparse-gap hits (6.81%) |
  | C | 500 | 385,091 | confirmed empty |
- By `exists_in_hms`:
  - 1: **154,931** (total real HMS records pulled)
  - 0: 392,026

## `audit/backfill_pilot.db` — pilot v1/v2/v3 record

- Size: 2,854,912 bytes (2.7 MB)
- `fasteignir`: 5,415 rows
- `run_events`: 185 events
- (Untouched by this weekend's runs; retained for historical reference.)

## Disk

- D:\ free: 354.1 GB (post-Phase-3, per status file)
