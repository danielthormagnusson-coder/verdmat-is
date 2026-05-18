# Áfangi 0 Stage 1 — weekend run summary

Generated 2026-05-18 as part of the Phase 4 handoff. See `weekend_run_inventory.md` for raw numbers.

## What ran

Two coordinated autonomous runs over the weekend, both finished clean:

1. **Orchestrator (`weekend_run_orchestrator.py`)** — built canonical image index, refreshed augl payloads for every Supabase property, and bootstrapped the image archive.
2. **HMS full-scrape (`hms_full_scrape.py`)** — sequential **Phase A → B → C** against `https://hms.is/api/fasteignaskra/fasteign/{nr}` to bring fasteignaskrá fields into local archive.

The HMS scrape is the strategic centrepiece of this commit; the orchestrator's completion is the operational supporting win.

## Run timeline

| When (UTC) | Event |
|---|---|
| 2026-05-08T12:35 | Orchestrator started (Phase 1.2 storage build) |
| 2026-05-12 05:07 | Windows Update reboot #1 — orchestrator Phase 2 killed at row 56,500 |
| 2026-05-13 04:51 | Windows Update reboot #2 — orchestrator Phase 2 killed again at row 97,800 (KB5089549 May Patch Tuesday) |
| 2026-05-13 09:15 | Orchestrator resumed (manual relaunch); WU paused via elevated registry write through 2026-05-20 |
| 2026-05-15 14:09 | HMS full-scrape A→B→C launched in parallel |
| **2026-05-15 21:46** | **Orchestrator Phase 3 image bootstrap COMPLETE** — clean exit, returned 0 |
| **2026-05-18 00:29** | **HMS full-scrape COMPLETE** — Phase C closed, clean exit |

HMS scrape total elapsed: **58h 20m**. Zero resumes (WU paused), zero WAF halts.

## HMS scrape — A / B / C metrics

The orchestrator's `stage_a` naming created a name collision, so HMS phases were independently labelled A / B / C. The three target sets are disjoint by construction:

| Phase | Target set | Requests | Hits (HTTP 200) | Empty (HTTP 500) | Hit-rate |
|:--|:--|---:|---:|---:|---:|
| A | `kaupskra \ properties` ∪ mid-size-gap ints (200–1000 wide) | 8,897 | **2,059** | 6,838 | 23.1% |
| B | every existing `properties.fastnum` | 124,835 | **124,738** | 97 | **99.92%** |
| C | full span `[2,000,044..2,547,000]` minus A ∪ B | 413,225 | **28,134** | 385,091 | 6.81% |
| **Total** | | **546,957** | **154,931** | 392,026 | 28.3% |

Stored in `audit/hms_archive_staging.db.hms_fasteign` (391 MB, gitignored).

## Three big findings

### 1. ~30,193 new properties discovered (HMS-only, never in Supabase)

- **2,059 from Phase A** — the 8,897 Phase A target was constructed from `kaupskra \ properties` (1,527 fastnums) plus integers inside 200–1000-wide gaps (~7,370). Of these, 23.1% existed in HMS.
- **28,134 from Phase C** — the "fill the rest" sweep. These are HMS-registered properties that never sold in any kaupskra record AND never appeared in evalue.is augl data. They were structurally invisible to every existing data source.
- Examples seen: countryside cultivated land plots (Ræktað land), unsold new-build apartments at the end of a numbered series (Stakkahlíð 5), regional health clinics, sheep barns, hay barns, horse stables, fishing rights.

### 2. 124,738 existing Supabase rows now have full HMS schema

Every property except 97 (see below) was refreshed with the new HMS fields:

- `lhlmat` (land share of fasteignamat — decomposes value into land + structure)
- `brunabotamat` (fire insurance / rebuild-cost valuation, independent of market)
- `fasteignamat_naesta_ar` (next-year assessment forecast)
- `notkunareiningar[].matseiningar[]` array — sub-unit breakdown, each with own `einflm`, `byggingarar`, `byggingarstig` (B0–B4), `gerd` (HMS internal class), `matsstig`, `skodags`, `texti` (subtype), independent `brunabotamat` and `fasteignamat`.
- `landeign_nr` and `tengd_stadfang_nr[]` (lot/staðfang cross-references for building-density features).

This is the dataset that the valuation model upgrade depends on.

### 3. 97 "ghost" properties in Supabase no longer recognised by HMS

Phase B HTTP 500 results — properties whose fastnums returned `{"error":"Internal server error"}` from HMS. These are de-registered / merged / renumbered properties that still occupy a row in `properties` but no longer have a backing record at the source. They need a Phase D handling decision (mark `deregistered=true`, soft-delete, or hard-delete).

## Phase C surprise — pilot v3 thesis revised

Pilot v3 (2026-05-07/08) had run small-sample probes against three target ranges and reported:

- Trailing range 2,541,715..2,546,714 (5,000 candidates): **2 hits**
- Sub-gap 2,389,000..2,389,099 (100 candidates): **0 hits**
- 2.4M bucket (400 across four slices): **0 hits**

The conclusion at the time (`project_registry_completion_thesis_collapsed.md`) was: "the missing 25K hypothesis no longer has a credible target range" and "session-after-next should NOT plan a multi-night registry-completion sweep". Phase C of this weekend's full-coverage sweep refutes that conclusion:

- 28,134 hits across 413,225 candidates = **6.81% aggregate**
- Excluding the confirmed-empty 2.4M bucket (100K integers, ~0 hits): **~9.0%** hit-rate across the rest
- Pilot v3's probe locations were unrepresentative — they happened to hit administratively-empty stretches while completely missing the intra-bucket sparse-hole population structure.

**Lesson:** small-sample probes are insufficient to scope full registry-completion work. Even though three probes returned 0–2 hits each, the broader population structure was 1–2 orders of magnitude denser. Full-coverage sweeps remain necessary before concluding "scope is small" for any backfill-style operation against authoritative external registries.

## Orchestrator companion deliverables

(All running and completed during the same weekend window, fully separate from the HMS scrape:)

- **`stage_a_augl_staging.db`** — 124,835 augl payloads, all `augl_status=200`. 65,811 (52.7%) were `[[]]` empty-history, 57,649 (46.2%) were multi-ad history responses. Bridges the "listings currency" gap.
- **`image_index.db`** — 2,631,485 rows total, 2,631,427 (99.998%) downloaded successfully, 58 failed. By source: 1,478,257 newly discovered from Phase 2 augl payloads + 1,152,898 collated from legacy `fasteignir{,1,2,3,4}.db` + 165 from pilot v3 residual.
- **`D:\Gagnapakkar\images\`** — 1,752,028 image files, 352.53 GB. Phase 3 fetched ~378 GB of new images (legacy archive started at ~196 GB → now 352 GB on disk; bytes accounting in log = 378.4 GB which includes overwrites of placeholder rows).
- **`cross_property_refs`** table — 134,635 cross-property image references catalogued (the "augl payload references images from OTHER properties' CloudFront folders" finding from pilot v3 phase-2). Top-referenced fastnum prefix `0` (47,722 refs) is a placeholder/normalisation artifact worth one diagnostic look later.

## Phase D readiness

All scraped data sits in `audit/hms_archive_staging.db`. Three decisions are pending before Supabase write-back:

1. **Schema:** new `hms_data` table (1:1 with `properties.fastnum` plus `matseiningar` denormalised) or widen `properties` in place? Separate table is cleaner for HMS-refresh re-runs without touching the prediction-eldsneyti columns; widening is simpler for queries.
2. **30,193 new property insertion:** they need full pipeline (coordinates from staðfangaskrá, matsvaedi assignment, region_tier, canonical_code etc.) before joining `properties` — or land in an HMS-only staging table first and graduate over time.
3. **97 ghost handling:** mark `deregistered=true` + retain history, soft-delete, or hard-delete? Implications for `sales_history`, `predictions`, model training filters.

Out-of-scope for this commit. Will be planned in a fresh strategic chat session.

## Carried items not addressed this run

- Stage B image-fetch observability gap (`feedback_stage_b_observability_gap.md`) — the orchestrator's status file went silent during the 4-worker fetch phase. Real-time progress had to be queried directly from `image_index.db`. Worth a fix before the next long parallel-fetch run.
- SCRAPER_SPEC v1.1 amendments (carried from before this weekend) — still pending.
- Schema variant unit tests (carried) — still pending.
