# Áfangi 0 — weekend run status

**Updated:** 2026-05-15T21:46:57+00:00  |  monitor with `cat audit/weekend_run_status.md`
**Run started:** 2026-05-13T09:15:07+00:00  |  **total elapsed:** 2d 12h 31m

## Phase state

- ✓ **phase_1_storage_build** — completed
- ✓ **phase_2_stage_a_augl_refresh** — completed
- ✓ **phase_3_stage_b_image_bootstrap** — completed
- · **phase_4_commit_push** — pending

## Current activity

- **Phase:** phase_3_stage_b_image_bootstrap
- **Subphase:** 4-way parallel fetch (4 workers)
- **Phase elapsed:** 1d 23h 12m
- **Items:** 1,746,397 / 1,751,416 (99.7%)
- **Throughput:** 619.6 items/min
- **ETA (current subphase):** 8 min (0 h 8 min)

## Disk

- `D:\Gagnapakkar\images\` size: 352.53 GB
- D:\ free: 354.1 GB free

## Halts

- (none)

## Recent log (last 30 lines)

```
[2026-05-13T22:35:14+00:00] INFO    url-discovery: scanned 36,000 stage-A rows, inserted 792,733 new image_index rows
[2026-05-13T22:35:16+00:00] INFO    url-discovery: scanned 37,000 stage-A rows, inserted 818,249 new image_index rows
[2026-05-13T22:35:18+00:00] INFO    url-discovery: scanned 38,000 stage-A rows, inserted 847,802 new image_index rows
[2026-05-13T22:35:20+00:00] INFO    url-discovery: scanned 39,000 stage-A rows, inserted 875,471 new image_index rows
[2026-05-13T22:35:23+00:00] INFO    url-discovery: scanned 40,000 stage-A rows, inserted 906,899 new image_index rows
[2026-05-13T22:35:25+00:00] INFO    url-discovery: scanned 41,000 stage-A rows, inserted 938,222 new image_index rows
[2026-05-13T22:35:27+00:00] INFO    url-discovery: scanned 42,000 stage-A rows, inserted 969,463 new image_index rows
[2026-05-13T22:35:29+00:00] INFO    url-discovery: scanned 43,000 stage-A rows, inserted 996,645 new image_index rows
[2026-05-13T22:35:32+00:00] INFO    url-discovery: scanned 44,000 stage-A rows, inserted 1,026,639 new image_index rows
[2026-05-13T22:35:34+00:00] INFO    url-discovery: scanned 45,000 stage-A rows, inserted 1,054,333 new image_index rows
[2026-05-13T22:35:37+00:00] INFO    url-discovery: scanned 46,000 stage-A rows, inserted 1,083,358 new image_index rows
[2026-05-13T22:35:40+00:00] INFO    url-discovery: scanned 47,000 stage-A rows, inserted 1,114,943 new image_index rows
[2026-05-13T22:35:42+00:00] INFO    url-discovery: scanned 48,000 stage-A rows, inserted 1,140,904 new image_index rows
[2026-05-13T22:35:45+00:00] INFO    url-discovery: scanned 49,000 stage-A rows, inserted 1,174,538 new image_index rows
[2026-05-13T22:35:49+00:00] INFO    url-discovery: scanned 50,000 stage-A rows, inserted 1,206,861 new image_index rows
[2026-05-13T22:35:53+00:00] INFO    url-discovery: scanned 51,000 stage-A rows, inserted 1,241,859 new image_index rows
[2026-05-13T22:35:57+00:00] INFO    url-discovery: scanned 52,000 stage-A rows, inserted 1,273,175 new image_index rows
[2026-05-13T22:36:01+00:00] INFO    url-discovery: scanned 53,000 stage-A rows, inserted 1,300,543 new image_index rows
[2026-05-13T22:36:05+00:00] INFO    url-discovery: scanned 54,000 stage-A rows, inserted 1,328,000 new image_index rows
[2026-05-13T22:36:11+00:00] INFO    url-discovery: scanned 55,000 stage-A rows, inserted 1,356,389 new image_index rows
[2026-05-13T22:36:18+00:00] INFO    url-discovery: scanned 56,000 stage-A rows, inserted 1,380,383 new image_index rows
[2026-05-13T22:36:25+00:00] INFO    url-discovery: scanned 57,000 stage-A rows, inserted 1,410,875 new image_index rows
[2026-05-13T22:36:32+00:00] INFO    url-discovery: scanned 58,000 stage-A rows, inserted 1,445,259 new image_index rows
[2026-05-13T22:36:35+00:00] INFO    url-discovery: scanned 59,000 stage-A rows, inserted 1,477,898 new image_index rows
[2026-05-13T22:36:36+00:00] INFO  discovered 1,478,257 new image_index rows from Stage A
[2026-05-13T22:36:39+00:00] INFO  queued 1,751,416 downloaded=0 rows for fetch
[2026-05-15T21:46:17+00:00] INFO  Phase 3 COMPLETE downloaded=1,751,358 failed=58 bytes=378,371,477,854
[2026-05-15T21:46:57+00:00] INFO  status writer stopped
[2026-05-15T21:46:57+00:00] INFO  orchestrator: phase 3 stage-b image bootstrap returned 0
[2026-05-15T21:46:57+00:00] INFO  === orchestrator: phases 1-3 complete; commit/push (phase 4) is manual ===
```

