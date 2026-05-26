# Áfangi 0 Stage 1 — backfill pilot report

**Date**: 2026-05-07
**Plan reference**: `audit/backfill_pilot_plan.md` (committed `56c6134`)
**Scraper**: `audit/backfill_evalue_range.py` (variant 6 of evalue.is family)
**Output DB**: `audit/backfill_pilot.db` (105 rows + run-event log)
**Run log**: `audit/backfill_pilot_run.log`
**Status**: pilot complete, halted-as-planned for review. **No scaling, no Supabase writes, no commit yet** — awaiting Danni decision.

---

## Headline

- **Positive control**: **5 / 5 PASS** — evalue.is API still works, schema unchanged, no Cloudflare interception.
- **Pilot sweep (2,450,000–2,450,099)**: **0 / 100 hits**. All 100 returned `status: 204` (No Content). No 403s, no 404s, no challenges, no errors.
- **No Cloudflare event** at any point. No halt fired.
- **Total elapsed**: 354.3 s (5 min 54 s) for 105 fastnums × 3 actions = 315 HTTP requests.
- **Strategic finding (most important):** the 2.4M-bucket "Danni skipped this range" hypothesis from the plan **does not hold for the mid-bucket slice we probed.** A 0% hit rate at 2,450,000–2,450,099 means either HMS literally doesn't issue fastnums in this slice, or the entire 2.4M bucket is administratively unused. Either way, scaling the planned 100K-candidate sweep would mostly be 204s. **The gap-fill strategy needs a Phase-2 decision before we proceed to full backfill.**

---

## Audit trail — fastnums probed

**Positive controls** (random sample from `properties WHERE fastnum BETWEEN 2500015 AND 2541714`, captured 2026-05-07T12:18 UTC):

| # | fastnum | result |
|---|---|---|
| 1 | 2503270 | OK (status 200, address: Árskógar 3A, Reykjavík) |
| 2 | 2506715 | OK (status 200, address: Holtabraut 20) |
| 3 | 2512191 | OK |
| 4 | 2526172 | OK (status 200, address: Klappahraun 9A, Mývatn) |
| 5 | 2528893 | OK |

**Pilot sweep**: 100 sequential integers `2,450,000–2,450,099` inclusive. All 100 returned `status: 204`.

---

## Step-by-step results

### Step 1 — positive control (5 fastnums, ~20 s)

```
2026-05-07T12:18:38  stage_start positive_control count=5
2026-05-07T12:18:58  stage_end   positive_control elapsed=20.0s ok=5 not_found=0 error=0 other=0
2026-05-07T12:18:58  control_pass — proceeding to pilot sweep
```

All 5 returned `{"type":"success","status":200,"data":"<stringified JSON>"}`. Schema and field shape match what existing `properties` rows expect.

### Step 2 — pilot sweep (100 fastnums, ~334 s)

```
2026-05-07T12:18:58  stage_start pilot_sweep count=100
... progress 10/100 ... 100/100 (all 'other')
2026-05-07T12:24:33  stage_end   pilot_sweep elapsed=334.3s ok=0 not_found=0 error=0 other=100
```

The "other" status in the run log corresponds entirely to **`data_status_204`** in SQLite — i.e., evalue.is responded successfully (`type:success`), but with HTTP-style status code `204` (No Content) and `data: "[null]"`. This is **not a 404, not a Cloudflare challenge, not a server error.** It is the API's way of saying "valid request, no record".

### Step 3 — Cloudflare contingency

**Not triggered.** No `cf-mitigated` headers, no HTML responses, no 403s, no 429s observed across all 315 requests. No retry/halt logic fired. Scraper exited cleanly with exit code 0.

---

## Schema sample — for Phase 2 mapping shim

### Live `get_fasteign_data` response (positive control, fastnum 2503270)

Outer envelope:
```json
{"type": "success", "status": 200, "data": "<inner stringified JSON>"}
```

Inner `data` field is itself a JSON-encoded array. **First element is a header map (field name → 1-based position)**, subsequent elements are the values at those positions.

Inner array (decoded, fastnum 2503270):
```json
[
  {"fastnum":1,"landnum":2,"heinum":3,"heimilisfang":4,"merking":5,"tegund":6,
   "flatarmal":7,"fasteignamat":8,"fasteignamaT_NAESTA":9,"brunabotamat":10,
   "postnr":11,"hnitWGS84_N":12,"hnitWGS84_E":13,"matsvaediNUMER":14,
   "matsvaediNAFN":15,"postheiti":16},
  2503270,           // fastnum
  224212,            // landnum
  1164636,           // heinum
  "Árskógar 3A",     // heimilisfang
  "020503",          // merking
  "Íbúð",            // tegund   (verified UTF-8 stored correctly; terminal mojibake only)
  118.1,             // flatarmal
  79800,             // fasteignamat (in thousands of ISK, per existing properties row pattern)
  null,              // fasteignamaT_NAESTA
  78800,             // brunabotamat
  109,               // postnr
  64.10501909,       // hnitWGS84_N
  -21.84648308,      // hnitWGS84_E
  150,               // matsvaediNUMER
  "Seljahverfi",     // matsvaediNAFN
  "Reykjavík"        // postheiti
]
```

**Mapping-shim contract (preliminary, for Phase 2):**
1. Parse outer JSON; extract `data` (string).
2. JSON-parse the `data` string → array.
3. `array[0]` is the header map; positions are 1-based.
4. For each `column_name → position` in the header, read `array[position]`.
5. The 16 columns above map directly onto Supabase `properties` columns of the same name (need to confirm column-name parity vs. snake_case during shim build — `fasteignamaT_NAESTA` looks like a typo and may actually be `fasteignamat_naesta` in Supabase).

### Live `get_fasteign_kaups` (positive control, fastnum 2526172)

```json
{"type":"success","status":200,"data":"[[]]"}
```

Empty for this property. Same encoding pattern: outer envelope, inner data is stringified JSON. Empty array means no kaupskrá records — confirms the plan's expectation that never-sold properties have empty `kaups_json`.

### Live `get_fasteign_augl` (positive control, fastnum 2526172, listings/ads payload)

```json
{"type":"success","status":200,"data":"[[1,103],{\"id\":2,\"heimilisfang\":3,\"postnr\":4,\"kaupverd\":5,\"thinglystdags\":6,\"fjherb\":7,\"fjsvfnherb\":8,\"fjbadherb\":9,\"tegund\":10,\"einflm\":11,\"lysing\":12,\"fastnum\":13,\"fasteignamat\":14,\"brunabotamat\":15,\"ahvilandi\":15,\"byggar\":16,\"inngangur\":17,\"lyfta\":18,\"bilskur\":18,\"long\":19,\"lat\":20,\"staedi\":18,\"rafbill\":18,...
```

Different inner shape — first element is a slot-index array `[1, 103]` (ad-boundary indices), second element is the column-position map for ad records. **augl payload structure differs from data payload** — the mapping shim needs a separate parser for it. Since augl is not in scope for the registry-completion goal (per locked-plan §111), this is informational only; we don't have to ship an augl mapper as part of Phase 2.

### Live `get_fasteign_data` 204 response (pilot sweep, fastnum 2450000)

```json
{"type":"success","status":204,"data":"[null]"}
```

All 100 pilot rows look identical to this. `kaups_json` and `augl_json` for the same fastnums are `{"type":"success","status":200,"data":"[[]]"}` — i.e., the kaups/augl actions return success-empty rather than 204, because they're queries-by-key rather than registry-lookups, and an empty result on a non-existent fastnum is structurally still "no records found".

---

## What this tells us about the 2.4M bucket

The plan (§Empirical gap analysis) predicted: *if this bucket is normal-density (~20K–30K like its neighbors), it accounts for most or all of the missing 25K by itself.*

Observed: **0/100 in mid-bucket.** Even at the low end of neighboring-bucket density (~15% sparsest), we'd expect ~15 hits in 100 candidates. Zero hits across a 100-integer span is statistically inconsistent with a normal-density bucket.

Three competing hypotheses, none yet confirmed:

1. **Bucket-empty by HMS administrative reservation.** HMS may simply not issue fastnums in `2,400,000–2,499,999` for some allocation-policy reason. Consistent with the bucket having 0 rows in `properties`.
2. **2,450,000–2,450,099 is a 100-integer dead zone within an otherwise-populated bucket.** Possible but improbable — would require us to be unlucky with our pilot slice. Probabilistically much less likely than (1).
3. **evalue.is doesn't carry data for this bucket even when HMS does.** evalue.is is a derivative source, not authoritative — could have its own indexing gaps. The positive controls confirm evalue.is *can* serve 2.5M data, so this would mean "evalue.is indexed 2.5M but not 2.4M". Possible but no obvious reason.

A 3-probe sanity check (3 × 100 candidates from different sub-ranges of the 2.4M bucket) would distinguish (1) from (2) at low cost (~15 min wall-clock). **Recommend doing that before scaling, not after.**

---

## Full-backfill projection (revised from plan)

**Pilot timing**: 354.3 s for 105 fastnums × 3 actions = 1.12 s/HTTP request (incl. 0.3 s inter-request delay), or ~3.37 s/fastnum end-to-end.

**Plan's estimate** (28 h for 100K fastnums) assumed `get_fasteign_data` only at 1 req/sec. My pilot runs all 3 actions for safety, so my measured per-fastnum cost is 3.37 s, not 1 s.

| Scope | Per-fastnum | 100K candidates | 25K (target backfill) |
|---|---|---|---|
| Pilot pattern (3 actions) | 3.37 s | ~94 h | ~23 h |
| Plan-spec pattern (1 action only) | ~1.4 s | ~39 h | ~10 h |

But — these are wall-clock costs **assuming we actually want to scrape every candidate**. If the 2.4M bucket is mostly 204s, the per-fastnum-with-data cost is unbounded. **Cost per actual gap-filled row is the metric that matters, and we don't know it yet.**

---

## Recommendations (for Danni decision; no autonomous follow-up)

1. **Sanity-probe two more sub-ranges in the 2.4M bucket before any scaling decision.** Suggested: `2,400,000–2,400,099`, `2,499,900–2,499,999`. Two more 100-fastnum probes; ~10 min wall-clock total. Distinguishes "bucket truly empty" from "we picked a bad slice".
2. **If those two probes also yield 0%**, redirect Stage 1 effort to:
   - **`2,378,000–2,399,999` sub-gap probe** (the in-bucket gap noted in plan §Empirical gap analysis, max=2,377,983 in a bucket extending to 2,399,999) — different structural reason to expect hits.
   - **`2,541,715+` trailing range** (post-Danni-last-sweep newly-issued fastnums; magnitude unknown but small).
   - **Sparse-gap audit within populated buckets** — query `properties` for largest integer-gaps within each populated bucket, probe those.
3. **If at least one of the two new sub-range probes yields hits** (>5% hit rate), proceed to scaling-decision conversation: full 2.4M sweep at 1 req/sec single-action pattern (~30–40 h wall-clock, multi-night staging).
4. **Mapping-shim work can begin in parallel** — schema is now empirically grounded (positive-control response shape above is the input contract), and the shim's cost (1–2 h) is independent of which fastnums we end up scraping. Building the shim against the captured positive-control rows in `audit/backfill_pilot.db` is a clean, decoupled piece of work.
5. **Cloudflare posture remains unchanged** — no signal that evalue.is has tightened bot management since Danni's last sweep, so the existing 1 req/sec pattern remains operationally viable.

---

## Artifacts on disk

- `audit/backfill_pilot.db` — 105 rows in `fasteignir` (5 ok positive controls + 100 data_status_204 sweep rows), plus full `run_events` audit log (12 events).
- `audit/backfill_pilot_run.log` — newline-delimited human-readable log (also stored as `run_events` rows).
- `audit/backfill_evalue_range.py` — pilot scraper (variant 6, integer-range walker; not committed, awaiting decision).

No Supabase writes, no schema changes, no commits made. **PAUSED for Danni review.**
