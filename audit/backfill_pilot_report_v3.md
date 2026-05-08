# Áfangi 0 Stage 1 — backfill pilot report v3

**Date**: 2026-05-07 → 2026-05-08 (run spanned UTC midnight)
**Reference**: `audit/backfill_pilot_report.md` (v1), `audit/backfill_pilot_report_v2.md`, `audit/scrape_gap_diagnostic_report.md`, `audit/kaupskra_staleness_check.md`, `audit/image_storage_policy.md`, `docs/PLANNING_BACKLOG.md` Áfangi 0.y Amendment 4.
**Scrapers**: `audit/backfill_evalue_range.py` (extended with image-download module + `fast_skip_on_204`), `audit/backfill_evalue_v3.py` (phases 2-4 runner).
**DBs**: `audit/backfill_pilot.db` extended with three new stages (`phase2_validation`, `phase3_trailing`, `phase4_subgap`); `D:\Gagnapakkar\images\<fastnum>\` archive directories.
**Status**: pilot v3 complete, **PAUSED** for review. No commits, no Supabase writes.

---

## Headline

- **Phase 2 (5 fresh positive controls): 5/5 OK.** Full 3-action scrape + image download path validated. **621 image successes logged, 505 files on disk** — discrepancy explained by an empirical finding that re-shapes the image-storage policy (see §Image archive observations below).
- **Phase 3 (trailing walk, 2,541,715–2,546,714): 2/5,000 hits = 0.04% density.** Exactly the same 2 fastnums (`2541716`, `2541748`) found in pilot v2's first-100 probe. **No new hits in the next 4,900 candidates.** New-issuance density above the current Supabase MAX collapses to near-zero almost immediately.
- **Phase 4 (sub-gap, 2,389,000–2,389,099): 0/100 hits.** The candidate `2,378,000–2,399,999` sub-gap (2.3M bucket truncates at 2,377,983) is empty in this slice. Combined with the pilot v2 evidence on the 2.4M bucket, the previously-attractive registry-completion targets are now mostly ruled out.
- **No Cloudflare events, no halts, no errors** across all v3 phases. ~7,965 s elapsed (132.8 min wall-clock).
- **Big strategic shift:** the "missing ~25K" registry-completion hypothesis is now in serious doubt. The next session's high-value work is **NOT** more registry-completion sweeps — it's the listings-currency + image-archive multi-night sweep on the existing 124,835 fastnums.

---

## Phase-by-phase results

### Phase 2 — image-download validation (5 fresh controls)

Fresh sample queried from Supabase: `2501932, 2511402, 2527607, 2528464, 2534391` (random from `2,500,015 ≤ fastnum ≤ 2,541,714`). All 5 returned `status: 200` cleanly. Per-fastnum image-download summary:

| fastnum | log n_urls | disk count | disk MB | heimilisfang sample |
|---|---:|---:|---:|---|
| 2501932 | 78  | 78  | 8.26 | Sunnusmári 16, Kópavogur |
| 2511402 | 44  | 44  | 10.44 | (residential, 2.5M range) |
| 2527607 | 244 | 244 | 66.17 | (residential, 2.5M range) |
| 2528464 | 96  | **54** | 17.19 | (residential, 2.5M range) |
| 2534391 | 159 | **85** | 17.24 | (residential, 2.5M range) |
| **Total** | **621** | **505** | **119.31** | |

Image-download mechanism itself is robust: zero HTTP errors against CloudFront, atomic-rename writes, idempotent skip-if-exists, polite 0.5 s delay between fetches.

### Phase 3 — trailing range walk (5,000 candidates)

| metric | value |
|---|---|
| range | `2,541,715 – 2,546,714` (5,000 candidates) |
| hits (`status:200`) | **2** (`2541716`, `2541748`) — both already discovered in pilot v2's first-100 probe |
| non-hits (`status:204`) | 4,998 |
| net new fastnums above MAX | 0 (the 2 hits sit at MAX+2 and MAX+34, well within the first 100 above MAX that v2 already probed) |
| hit density | 0.04 % overall, 2 % in the first 100, 0 % in the next 4,900 |
| Cloudflare events | 0 |
| elapsed | 7,353 s (123 min) |

Both Phase 3 hits had `n_ads=0` (no listings on file), so no images downloaded. The two confirmed new properties:
- `2541716` Borgarbraut 2B, Búðardalur (Parhús, 63.2 m², fasteignamat 21,150 thús kr)
- `2541748` Hánefsstaðir 1, Seyðisfjörður (Íbúð í húð, 256 m², fasteignamat 43,600 thús kr)

The user task spec asked for "a sample of 10 new properties" — only 2 exist to sample. The trailing range above MAX yielded fewer than half a percent of the expected scaling-target volume.

### Phase 4 — sub-gap probe (100 candidates)

| metric | value |
|---|---|
| range | `2,389,000 – 2,389,099` (100 candidates, mid the `2,378,000–2,399,999` sub-gap above 2.3M MAX 2,377,983) |
| hits | **0** |
| non-hits | 100 |
| Cloudflare events | 0 |
| elapsed | 145.8 s (2.4 min) |

The sub-gap appears empty in this slice. Could probe more sub-ranges to be conclusive (`2,380,000–2,380,099`, `2,395,000–2,395,099`), but given the trailing-range result also collapsed, my read is the registry-completion gap-fill thesis is broadly weak — not just at one location.

---

## Image archive observations (storage-policy-relevant)

### Disk vs. log discrepancy → multi-CloudFront-folder finding

The log claims 621 successful image downloads in Phase 2; the disk shows 505 unique JPG files. The discrepancy (116 missing files) was investigated:

**Root cause:** properties' `augl_json` payloads reference image URLs from **multiple CloudFront folders**, some belonging to OTHER properties. For fastnum `2528464`, the augl payload contained 96 unique CloudFront URLs:
- 34 in `/2528464/...` (the property's own ad images)
- 62 in other CloudFront paths like `/25204686/...`, `/25204687/...`, `/25284654/...`

Looking at the `/<digits>/` prefixes more carefully:
- `25204686 = 2520468 + 6` — this is **fastnum 2520468 plus an ad-index 6**, i.e., an image from a *different* property's listing
- `25284654 = 2528465 + 4` — different property again
- `25343911 = 2534391 + 1` — same property's ad #1 (own-property cross-references)

So the augl payload mixes (a) the subject property's own ad images and (b) "comparable listings" cross-property images — likely evalue.is showing similar nearby properties or recent comparable sales for context.

**Bug in the pilot's storage scheme:** my `download_property_images` writes everything to `image_root/<property_fastnum>/<basename>`, flattening all 96 URLs into one folder. When a cross-property reference happens to share a basename with an own-property image (or with another cross-property reference), the second download hits `dest.exists()` early-return and returns `ok=True info="skip-exists"` — the log records a "successful download" even though no file was written. 116 such collisions explain the 96→54 and 159→85 drops on the two affected fastnums.

**This is a storage-policy correction that needs to land before any production multi-night sweep**, not a critical pilot blocker. The bug is conservative (it under-archives cross-property images, never over-archives or corrupts), so the pilot's 505 own-property images are correct. But for the production archive we need a layout that preserves CloudFront-folder origin.

### Recommended storage-policy correction (for next-session lock)

Three options ordered by my preference:

1. **Layout by CloudFront origin** (recommended): write to `image_root/<cf_path_segment>/<basename>` exactly as the URL specifies. Side-table `image_property_map (property_fastnum, image_url, local_path, role)` records which property's augl referenced each image and what its role was (own-ad / cross-comparable). Preserves natural CloudFront addressing, avoids collisions, supports many-to-many property-to-image.

2. **Origin-prefixed filenames**: keep `image_root/<property_fastnum>/` layout but prefix filenames with origin path: `image_root/2528464/25204686__sph3_F3h.jpg`. Avoids collisions, keeps property grouping, sacrifices direct CloudFront-mirror nicety.

3. **Content-addressable**: hash URL → filename. Fully collision-free but loses every bit of human-meaningful metadata in the filename.

(1) is also the most natural for a future "expose images via static-file path that mirrors CloudFront" serving pattern.

### Disk size empirics (Phase 2)

| metric | value |
|---|---|
| total properties | 5 |
| total unique on-disk images | 505 |
| total disk size | 119.31 MB |
| avg images per property | 101 |
| avg KB per image | 242 |
| max images per property | 244 (fastnum 2527607) |
| min images per property | 44 |

These 5 properties were random-sampled from the 2.5M range. All 5 had ≥1 ad-with-images — which doesn't match the population baseline (only 38.9 % of 124,835 fastnums have any photos per Supabase `n_photos`). So the per-fastnum image counts above are biased toward "active" properties.

---

## Refined full-backfill scope estimate (uses today's empirical data)

### Population breakdown (Supabase `properties` 2026-05-08 query)

```
total_rows                    124,835
rows with no photos            76,240   (61.1 %)
rows with photos               48,595   (38.9 %)
avg photos (when nonzero)        23.47   ← legacy scraper capped at 50
median                           23
p90                              38
max                              50      ← cap artifact, true count likely higher
```

The legacy scraper extracted images from the *first ad only* (`newest_only=True`) and topped out at 50. Phase 2's freshly-scraped images count from-all-ads up to 244 — a **~5× per-property growth** vs. the legacy Supabase n_photos column for ad-having properties.

### Augl-refresh time (single-action `get_fasteign_augl` only)

```
124,835 fastnums × ~1.4 s/fastnum (1 POST + 1 s delay) = ~49 hours of HTTP work
```

Single-action posture per locked plan §111. Resume-safe via `INSERT OR REPLACE` keyed on `(fastnum, stage)`. Multi-night staging works cleanly.

### Image-archive bootstrap cost (CloudFront fetches)

Naive serial at 0.5 s delay:
```
48,595 fastnums-with-images × ~100 imgs avg × 0.5 s/img = ~675 hours = 28 days  ← too slow
```

This is an unworkable cost at the pilot's serial-with-0.5s-delay posture. Fix options:
- Drop image delay to 0.1 s: 28 days → ~5.6 days
- Add 4-way parallelism (CloudFront tolerates this): 5.6 days → ~34 hours = 1.4 nights
- Both: ~28 hours = 1.2 nights

**Practical target: ~30 hours wall-clock for the full image bootstrap**, with image fetches at 0.1 s delay and 4-way parallelism. The augl-refresh side runs at the original 1 req/sec (no parallelism on evalue.is).

### Storage size

```
48,595 properties × ~80–120 images avg × ~250 KB = 0.97 – 1.46 TB
```

Phase 2 saw ~24 MB per ad-having property. If that's representative: 48,595 × 24 MB = ~1.17 TB midpoint. Allow ±25 % for distribution variance. **Assume ~1 TB target archive size** for sizing decisions; provision ≥1.5 TB free space on `D:\Gagnapakkar\` before kickoff.

### Bundled vs. split — recommendation

**Recommendation: split.** Two stages, run on separate nights:

#### Stage A — augl-only refresh of 124,835 existing fastnums (~49 h, 2 nights)
- Single-action `get_fasteign_augl` only; data + kaups untouched (data is stable, kaups is empty for un-sold properties anyway).
- No image downloads in this stage. Just refresh the JSON payloads.
- Output: refreshed `augl_json` per fastnum in a new SQLite table, plus a derived "n_images" column from the URL count for sizing the next stage.
- Closes the listings-currency gap (`scrape_gap_diagnostic` Hypothesis B) on its own.

#### Stage B — image archive bootstrap (~30 h with parallelism, 1-2 nights)
- Reads Stage A's refreshed augl payloads.
- Downloads images per the corrected storage policy (next-session lock).
- 4-way parallel CloudFront fetches at 0.1 s sleep.
- Output: `~1 TB` archive at `D:\Gagnapakkar\images\` per locked layout.

**Why split, not bundle:**
1. Stage A has standalone value (listings currency); doesn't need to wait on storage-policy lock or image bootstrap finishing.
2. Stage A's output gives us empirical n_images-per-fastnum data to right-size Stage B before we commit to the multi-day fetch.
3. If anything weird surfaces in Stage A's payloads (schema drift, new fields, etc.), we can adjust before pulling 1+ TB.
4. Storage policy correction can land between A and B — it touches B but not A.

### Skipping the registry-completion sweep

Given pilot v3:
- Trailing 5K walk: 2 hits = essentially nothing
- Sub-gap probe: 0 hits = empty
- 2.4M bucket: 0/400 = empty (pilot v2)

**The previously-planned multi-night registry-completion sweep is no longer worth the wall-clock budget.** The known and probed gap-fill targets have been near-exhaustively measured. The remaining theoretical gap (intra-bucket sparse holes within already-populated buckets) lacks evidence of meaningful population, and probing it would require a new search strategy (per-bucket integer-gap detection) before any sweep.

If the user still wants registry-completion coverage, the only remaining moves are:
- Probe **higher buckets** (2.6M, 2.7M, 2.8M) — completely un-probed; could reveal a recent issuance range
- Probe **a few sparse-gap holes** within populated buckets (e.g., the largest integer gap inside 2.0M, 2.1M, etc.) before committing to a sweep

These are 30-60 minute probes, cheap. Out of scope for this session.

---

## What's resolved this session

- ✅ Image-download capability built and integrated into `backfill_evalue_range.py` with `image_root` parameter on `scrape_property` and `run_stage`.
- ✅ Storage policy v0 documented at `audit/image_storage_policy.md`, with empirically-discovered correction needed before production sweep.
- ✅ Phase 2 validation passed cleanly (5/5 OK, 505 images, 119 MB, 0 errors).
- ✅ Phase 3 trailing walk completed with definitive low-density signal.
- ✅ Phase 4 sub-gap probe completed (empty).
- ✅ Refined full-backfill scope: ~49 h augl-refresh + ~30 h image bootstrap, ~1 TB archive size, split into two stages.
- ✅ Storage-policy bug (cross-property URL collision) discovered and characterized; fix proposal documented for next-session lock.
- ✅ Strategic re-direction: drop registry-completion full-sweep; focus on listings-currency + image-archive bootstrap.

## Out-of-scope (next-session candidates)

- Storage policy lock (decide between `cf_path_origin / origin_prefix / hash` filename layouts).
- Mapping shim build (uses Phase 2 + diag scrape as schema sample, including the `fasteignamaT_NAESTA`-typo and the position-collision schema variant from pilot v2).
- Stage A — augl-only refresh of 124,835 fastnums (~49 h, 2 nights).
- Stage B — image-archive bootstrap (~30 h with parallelism, after storage-policy lock).
- Recurring-scrape redesign (drop `status='ok'` skip on `get_fasteign_augl` per `kaupskra_staleness_check.md` finding).
- (Optional, low priority) Probe higher buckets `2,600,000+` to rule out missing fastnums in unprobed regions.

---

## Artifacts

- `audit/backfill_pilot.db` — now 5,510 rows (105 v1+v2 + 5,205 v3 + 200 v3) tagged across 7 stages (`positive_control`, `pilot_sweep`, `probe_2400000`, `probe_2499900`, `probe_2541715`, `phase2_validation`, `phase3_trailing`, `phase4_subgap`). Also contains all run-event audit logs.
- `audit/backfill_evalue_range.py` — extended with `extract_image_urls`, `download_image`, `download_property_images`; `scrape_property` now takes `image_root=` and `fast_skip_on_204=`; `run_stage` likewise.
- `audit/backfill_evalue_v3.py` — phases 2-4 runner, halt-on-failure between phases.
- `audit/image_storage_policy.md` — v0 storage policy + open questions for next-session lock.
- `audit/backfill_pilot_report_v3.md` — this document.
- `D:\Gagnapakkar\images\` — 5 fastnum subdirs, 505 images, 119.31 MB on disk.

No commits, no Supabase writes. **Paused for Danni review.**
