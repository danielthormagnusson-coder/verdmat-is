# Áfangi 0 Stage 1 — backfill pilot report v2 (three-probe extension)

**Date**: 2026-05-07
**Reference**: `audit/backfill_pilot_plan.md`, `audit/backfill_pilot_report.md` (v1, committed)
**Scraper**: `audit/backfill_evalue_range.py` + `audit/backfill_evalue_probes.py`
**Output DB**: `audit/backfill_pilot.db` (now 405 rows: 5 positive control + 100 pilot sweep + 300 across three probes)
**Run log**: `audit/backfill_pilot_run.log`
**Status**: probes complete, **PAUSED** for Danni decision. No scaling, no Supabase writes, no commits.

---

## Headline

| Probe | Range | Hits | Hit rate | Diagnosis |
|---|---|---:|---:|---|
| Pilot v1 | 2,450,000–2,450,099 | 0/100 | 0.0 % | mid-2.4M bucket: empty |
| Probe 1 | 2,400,000–2,400,099 | 0/100 | 0.0 % | start of 2.4M bucket: empty |
| Probe 2 | 2,499,900–2,499,999 | 0/100 | 0.0 % | end of 2.4M bucket: empty |
| Probe 3 | 2,541,715–2,541,814 | **2/100** | **2.0 %** | trailing range: sparse but real |

- **2.4M bucket: 0 / 400 across four independent slices spanning the full 100K span.** Hypothesis confirmed — HMS does not issue fastnums in `2,400,000–2,499,999`. The bucket is administratively unused, not "Danni's prior sweep skipped it". **The missing 25K is NOT in this bucket.**
- **Trailing range above current MAX (2,541,714): live new rows.** Two confirmed new properties — `2541716` Borgarbraut 2B in Búðardalur (Parhús, 63.2 m², fasteignamat 21,150 thús kr) and `2541748` Hánefsstaðir 1 in Seyðisfjörður (Íbúð í húð, 256 m², fasteignamat 43,600 thús kr). Both verified absent from Supabase `properties` (independent SELECT).
- **No Cloudflare events**, **no halts**, **no errors** across all 900 HTTP requests in the three probes (300 fastnums × 3 actions). Total elapsed 996.6 s (~16 min 36 s).
- **All three probes added cleanly to `backfill_pilot.db`** with stage tags `probe_2400000`, `probe_2499900`, `probe_2541715`. The original v1 pilot rows are untouched (still queryable as `stage='positive_control'` and `stage='pilot_sweep'`).

---

## Cross-checked against live `properties` distribution

Re-pulled bucket-density 2026-05-07 to ground the diagnosis:

| Bucket | Supabase rows | MIN | MAX | Span density (rows / [MAX-MIN]) |
|---|---:|---:|---:|---:|
| 2,000,000 – 2,099,999 | 43,837 | 2,000,044 | 2,096,697 | **45.4 %** |
| 2,100,000 – 2,199,999 | 18,228 | 2,100,005 | 2,199,998 | 18.2 % |
| 2,200,000 – 2,299,999 | 28,897 | 2,200,002 | 2,299,998 | 28.9 % |
| 2,300,000 – 2,399,999 | 16,198 | 2,300,000 | **2,377,983** | 20.8 % (over actual span) — but ~22K integers in `[2,377,984, 2,399,999]` un-probed |
| **2,400,000 – 2,499,999** | **0** | — | — | **0 %** — bucket truly empty (confirmed by 4 probes) |
| 2,500,000 – 2,599,999 | 17,675 | 2,500,015 | 2,541,714 | 42.4 % (over actual span) |

Two observations:

1. **HMS allocation density is heterogeneous (18–45 %) across active buckets**, so "expect 20-30 % density in 2.4M" was always an over-confident prior in the original plan. The probes still rule out anything close to "active": even 5 % density would have given ~5 hits per 100, yet we got 0/400.
2. **The sparse 2.5M bucket already extends only to MAX=2,541,714.** Probe 3 found 2 hits in `[2,541,715, 2,541,814]`. So new HMS issuances are happening in this range — exactly the trailing-50–200/month estimate from `SCRAPER_SPEC v1` §7.4.

---

## Diagnosis — where the missing fastnums likely are

Updated probability ranking, given the four-probe evidence:

1. **Trailing range above 2,541,714** — confirmed live (2 new rows in 100 candidates immediately above MAX). New issuances accumulating since Danni's last sweep. Magnitude: probably 50–500 rows depending on the actual top of the trailing range (probably somewhere in 2,545,000–2,560,000). High-confidence target.
2. **`2,378,000–2,399,999` sub-gap** — 2.3M bucket truncates at 2,377,983, but the bucket nominally extends to 2,399,999. ~22K candidates in this slice were never probed by Danni's prior sweeps. Density: unknown. Plausible at neighboring 2.3M bucket density (~21%) → ~4,500 rows. **Highest-volume single target if density holds.**
3. **Sparse intra-bucket gaps within already-populated buckets** — the 2.0M / 2.1M / 2.2M / 2.3M / 2.5M buckets each have 50K-80K integers that sit between actual rows. Most are HMS-not-issued (consistent with 18–45 % density). Some are genuinely-issued-but-Danni-missed. Discoverability: only via integer-space walk per-bucket. Magnitude: unknown, probably 5–20K rows in aggregate.
4. **2.4M bucket** — REJECTED. 0/400 hits is statistically conclusive. Do not scale here.
5. **2.6M+ buckets** — not yet probed; would be follow-on work after the trailing target is exhausted.

**Net read**: Stage 1 effort should redirect entirely away from 2.4M and toward (1) trailing + (2) `2,378K–2,400K` sub-gap, in that order.

---

## Schema variability finding (Phase 2 mapping shim)

Fastnum **2541716** returned a schema map with **position collisions**:

```
{"fastnum":1, "landnum":2, "heinum":3, "heimilisfang":4, "merking":5,
 "tegund":6, "flatarmal":7, "fasteignamat":8,
 "fasteignamaT_NAESTA":9, "brunabotamat":9,    ← collision at 9
 "postnr":10, "hnitWGS84_N":11, "hnitWGS84_E":12,
 "matsvaediNUMER":13,
 "matsvaediNAFN":14, "postheiti":14}            ← collision at 14
```

vs. the canonical 16-position schema seen in positive controls and 2541748 (which has all 16 positions distinct). **HMS evidently emits a compressed schema for properties with fewer distinct field values** — last-key-wins semantics in the dict mean `fasteignamaT_NAESTA` and `matsvaediNAFN` are silently dropped from the response.

**Mapping shim contract update for Phase 2:**
- Parse the schema map fresh per row (don't cache schema across the dataset).
- Treat position collisions as "the colliding field is absent" and write `NULL` to the corresponding `properties` column.
- Validate value-array length: when shorter than 16, the omitted high-position fields are absent and must be `NULL`.
- Verified empirically — both row shapes appear in `audit/backfill_pilot.db`, so the shim's schema parser can be unit-tested against real data.

This was **not visible** in the v1 pilot's 5 positive-control rows. The Phase 2 mapping shim would have shipped without handling it. Probe 3 surfaced it specifically because it captured properties from a sparser, lower-fidelity HMS allocation cohort.

---

## Updated scaling recommendation (priority order)

### 1. **First scaling target: trailing range walk.**

Walk `2,541,715` → some `discovered_max`. Stopping rule: stop when 200 consecutive 204s observed (definitive end of HMS issuances). Expected discovery: top probably in `2,545,000–2,560,000` based on 50–200/month × 6 months since last scrape. At observed 2 % hit rate, walking 5,000 candidates yields ~100 new rows. At 1 req/sec single-action (per `backfill_pilot_plan.md` §111 locked decision), 5,000 fastnums = ~85 min. Worth doing in a single session, no multi-night staging needed.

### 2. **Second scaling target: `2,378,000–2,399,999` sub-gap.**

Walk this 22K-candidate slice. Hit rate unknown — propose a 100-candidate spot-probe at `2,388,000–2,388,099` (mid-gap) first (~6 min). If hit rate ≥ 5 %, full sweep estimated ~6 hours single-action; if < 5 %, treat like 2.4M and skip.

### 3. **Third scaling target: intra-bucket sparse-gap audit.**

Run a Supabase query to find the largest integer-gaps within each populated bucket, probe each gap with a 100-candidate sample, sweep gaps with non-zero hit rate. This is structurally identical to (2) but applied across already-populated buckets. Probably yields ~5–20 K rows total over multiple sub-gap sweeps.

### 4. **Skip 2.4M entirely.**

400/400 = 0 hits is a definitive empty-bucket signal. ~40 hours of single-action scraping for likely zero new rows.

### 5. **Phase 2 mapping shim work** can run **in parallel** with any of (1)-(3).

Schema is empirically grounded, including the position-collision variant. Shim implementation cost is independent of which fastnums end up in the final scrape. Build the shim against the 7 OK rows already in `backfill_pilot.db` (5 positive controls + 2 trailing-probe hits), unit-test against both schema variants, then point at any future scrape DB with the same shape.

---

## Operational notes

- **Throttle posture remains 1 req/sec, three actions per fastnum in the probes; no rate-limit signals observed.** Same posture should be safe for the trailing-range walk. Single-action posture for production scaling per locked plan §111.
- **`fasteignamaT_NAESTA` is HMS's typo** (capital T mid-word). Matches the original positive-control schema. Mapping shim will need a snake_case-rename rule for this column (probably `fasteignamat_naesta`); confirm against actual `properties` column names during shim build.
- **No commits yet** for either the v1 pilot scraper, the probe runner, or this report. All artifacts staged in `audit/` for Danni review.

---

## Artifacts on disk

- `audit/backfill_pilot.db` — 405 rows in `fasteignir` (5 ok + 100 + 100 + 100 + 98×204 + 2 ok), 28 events in `run_events`.
- `audit/backfill_pilot_run.log` — append-only human log spanning v1 pilot + 3 probes.
- `audit/backfill_evalue_range.py` — pilot scraper (variant 6, integer-range walker).
- `audit/backfill_evalue_probes.py` — three-probe driver, imports from `backfill_evalue_range`.
- `audit/backfill_pilot_report.md` — v1 report (pre-three-probe).
- `audit/backfill_pilot_report_v2.md` — this document.

**No Supabase writes, no schema changes, no commits made. PAUSED for Danni review.**

PLANNING_BACKLOG.md Áfangi 0.y entry was updated in this session with **Amendment 4** (image-ownership policy: all scrapers download to `D:\Gagnapakkar\images\` in addition to structured-JSON capture; storage convention + refresh policy locked next session using the positive-control `augl_json` payloads in `backfill_pilot.db` for sizing).
