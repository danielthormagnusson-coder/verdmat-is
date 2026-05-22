# POST_HMS_RECOVERY_PLAN

Runnable specification for the work that becomes possible once `audit/hms_full_recovery.py` completes and the canonical recovered-fastnum set is locked. Parametrized on `N_RECOVERED` — expected ~71,800 fastnums, computed as 392,026 probed × 18.5% point-estimate recovery rate (Wilson 95% CI 16.2%–21.0%, per the 2026-05-21 spike report).

This document does not authorize execution. It is the source-of-truth checklist; running anything here requires both gates below to be green and an explicit Danni "halt áfram" per step.

---

## 0. Gates — both must be green before any step below

- [ ] **G1: HMS recovery complete.** `audit/hms_full_recovery.py` has finished. `audit/hms_recovery_report.md` has been updated with the final breakdown: total probed (392,026), genuine-500 count, recovered-200 count (= `N_RECOVERED`), per-dead-zone-window distribution. The set of recovered fastnums has been materialized into a stable artifact — propose `audit/recovered_fastnums_locked.txt` (one fastnum per line) so every step below reads from the same canonical input.
- [ ] **G2: Production-template hardening landed.** Per `docs/PLANNING_BACKLOG.md` item 5 (2026-05-22). Specifically:
  - `audit/hms_full_scrape.py` retro-fitted with outage detection (sliding-window pause + alert on <1% hit-rate) and 500-aware backoff (sustained 5xx triggers backoff, not just WAF status codes).
  - `audit/stage_a_augl_refresh.py` resume done-set changed from `SELECT fastnum FROM stage_a_augl` to `SELECT fastnum FROM stage_a_augl WHERE augl_status IN (200, 204)` so error-rows (`augl_status=-1`) get retried on resume.
  - Canonical scraper template (the shape both will conform to) is documented somewhere persistent (proposed: `docs/SCRAPER_SPEC_v1.md` §canonical-template section).

If either gate is red, do not run any step below. The point of the gates is that running this plan against an unstable input set or a not-yet-hardened template would risk re-creating the exact silent-loss class of bug this plan exists to recover from.

---

## 1. Step 0 — Magnitude confirmation + recovered-set partition (cheap, ~1 min)

The recovered set is NOT homogeneous. The dead-zone (2026-05-16/17) sat inside Phase C of the original scrape but caught **some** Phase B fastnums that happened to be probed during that window. Per DECISIONS 2026-05-18, the original scrape flagged 97 such Phase B fastnums as "deregistered ghosts" (HTTP 500, assumed gone). The recovery now re-probes them; whichever subset returns 200 was never a ghost — it was a dead-zone false-negative on an already-known fastnum.

Partition the recovered set into two subsets before any further work:

- **(a) already-in-base** = empirically `recovered ∩ properties.WHERE deregistered=true` — the recovered fastnums currently flagged as ghosts in Supabase (D2 soft-flagged ~97 Phase B HMS-500s as `deregistered=true` per DECISIONS 2026-05-18). Expected ≈ 97 (cross-checks against `recovered ∩ stage_a_augl_staging.fastnum` since the 97 Phase B ghosts were in the evalue input set). These need **HMS-metadata refresh + `deregistered = false` flip only** — NO insert, NO evalue re-scrape (their evalue payload is already in staging from 2026-05-08→13), NO kaupskrá lookup (their `sales_history` is already loaded). **The apply path uses the empirical set materialised by Step 0, not a hard-coded 97.**
- **(b) net-new Phase C** = `recovered \ already-in-base`. Genuinely new fastnums that returned 500 during the dead-zone Phase C sweep. Expected ≈ 71,700 (= `N_RECOVERED − |already-in-base|`). These need the **full pass** (Steps 1-4 below).

```python
# scripts/post_recovery_step0_partition.py (to write at execution time)
import psycopg2, sqlite3
RECOVERED = set(int(x) for x in open("audit/recovered_fastnums_locked.txt"))
# Canonical source of subset (a): Supabase's current ghost set, intersected with recovered.
conn = psycopg2.connect(open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read().strip())
cur = conn.cursor()
cur.execute(
    "SELECT fastnum FROM properties WHERE deregistered = true AND fastnum = ANY(%s)",
    (list(RECOVERED),),
)
already_in_base = set(r[0] for r in cur.fetchall())                 # empirical subset (a)
net_new         = RECOVERED - already_in_base                       # subset (b)

# Sanity cross-check: subset (a) should be ⊆ recovered ∩ Phase-B (= evalue staging),
# because every D2 ghost was in Supabase at the evalue scrape time.
sq = sqlite3.connect(r"file:D:\verdmat-is\app\audit\stage_a_augl_staging.db?mode=ro", uri=True)
PHASE_B = set(r[0] for r in sq.execute("SELECT fastnum FROM stage_a_augl"))
assert already_in_base.issubset(RECOVERED & PHASE_B), \
    "subset (a) leaked outside Phase-B input set — investigate before apply"

print(f"N_RECOVERED               = {len(RECOVERED):,}")
print(f"|already-in-base| (a)     = {len(already_in_base):,}  (expected ~97)")
print(f"|net-new Phase C| (b)     = {len(net_new):,}  (expected ~71,700)")
open("audit/recovered_already_in_base.txt", "w").write("\n".join(str(x) for x in sorted(already_in_base)))
open("audit/recovered_net_new.txt",         "w").write("\n".join(str(x) for x in sorted(net_new)))
```

**Decision branches** on `|already-in-base|`:
- **0 ≤ |already-in-base| ≤ ~120** (default): proceed. The 97 figure is the original D2 ghost count; the recovered subset is whatever empirically intersects current `deregistered=true`, and may shift by ±a few dozen.
- **|already-in-base| ≫ ~120**: STOP and investigate. Either the `deregistered=true` set has grown beyond D2 (separate question), or the dead-zone overlapped Phase B more aggressively than the spike report suggested.
- **|already-in-base| = 0**: also worth a sanity check — D2's 97 ghosts SHOULD have been in the 392K recovery pool. If none recovered, that supports the original D2 conclusion that they are genuinely deregistered (cross-check against the recovery output's per-window distribution).

After this partition lands, Steps 1-3 operate exclusively on subset (b). Subset (a) is handled in §4c's UPDATE path within the same D3-extended apply migration.

---

## 2. Step 1 — Evalue augl pass for the net-new subset

Operates on `audit/recovered_net_new.txt` (subset (b) from Step 0; expected ~71,700 fastnums).

Re-use the *shape* of `audit/stage_a_augl_refresh.py` (POST `evalue.is/fastnum/<fn>?/get_fasteign_augl`, polite 1.0 s delay, 5xx rolling-5% halt, 1-strike halt on `cf-mitigated`/HTML/403, 10-min sustained-net halt) but with the hardened template from gate G2 (retry-on-resume for `augl_status NOT IN (200, 204)`).

**Own staging table** — do not write into `stage_a_augl_staging.db` (which is the Phase B set, canonical and unchanged). Propose new DB `audit/stage_a_augl_recovered.db` with identical schema. This keeps the two populations cleanly separable for audit and lets the original 124,835-row baseline stay frozen. Subset (a) "already-in-base" is NOT re-scraped here — their evalue data already lives in `stage_a_augl_staging.db`.

**Rate / capacity**: `|net-new| × 1.4 s ≈ 71,700 × 1.4 / 3600 ≈ 28 hours` single-worker. If a higher concurrency is desired, decide after Step 0 results — for ~72K rows, single-worker 28h is fine.

**Resume-safety**: same as existing refresher (SQLite WAL, checkpoint every 25 rows). With the hardened template, error rows persist as `augl_status=-1` and are picked up on the next resume.

**Halt rules** — unchanged from `stage_a_augl_refresh.py`:
- HTTP 403 / Cloudflare-mitigated / HTML response → 1-strike halt.
- Rolling >5% 5xx over 100-request window → halt.
- Sustained net failure >10 min → halt.
- Disk free <5% → halt.

**Output**: per-fastnum row with `augl_status`, `augl_json`, `n_ads`, `n_image_urls`, `latest_augl_iso`, `captured_at`. Of the ~72K, expect ~30-50% to have listings (similar baseline to Phase B), the rest n_ads=0.

---

## 3. Step 2 — Kaupskrá lookup for the net-new subset

Operates on `audit/recovered_net_new.txt` (subset (b) from Step 0). Subset (a) already-in-base is NOT looked up here — their sales history is already loaded in Supabase `sales_history`.

`D:\kaupskra.csv` (HMS thinglýsing dump) is the canonical sales source. **Refresh it first** via `D:\refresh_kaupskra.py` (per CLAUDE.md operational scripts) so the slice is current as of run time, not 2026-04-20.

Then filter to the net-new subset:

```python
# scripts/post_recovery_step2_kaupskra.py (to write at execution time)
import pandas as pd
NET_NEW = set(int(x) for x in open("audit/recovered_net_new.txt"))
kp = pd.read_csv(r"D:\kaupskra.csv", sep=";", encoding="latin-1")
kp["FASTNUM"] = pd.to_numeric(kp["FASTNUM"], errors="coerce").astype("Int64")
# Exclude unenforceable contracts (per pairs_v1 + Áfangi 1.5 rules)
kp = kp[kp["ONOTHAEFUR_SAMNINGUR"].astype(str).str.strip() != "1"]
# Apply nýbygging rule (per rules.py is_new_build) at training-data time;
# kaupskrá is sales source-of-truth, do NOT pre-filter new-builds here.
sales_for_net_new = kp[kp["FASTNUM"].isin(NET_NEW)]
sales_for_net_new.to_csv("audit/net_new_sales_history.csv", index=False, encoding="utf-8-sig")
print(f"|net-new|              = {len(NET_NEW):,}")
print(f"net-new with sales     = {sales_for_net_new['FASTNUM'].nunique():,}")
print(f"total sales rows       = {len(sales_for_net_new):,}")
```

**Expected**: a meaningful fraction of recovered fastnums will have ZERO sales history (since they're new HMS-only properties that may never have been thinglýstir). Those go to Supabase `properties` with whatever HMS metadata + empty `sales_history`. Properties with sales get rows in `sales_history`.

**Output**: `audit/recovered_sales_history.csv` — staging artifact, not yet promoted.

---

## 4. Step 3 — Supabase promotion (D3-extended)

This step extends the existing Phase D execution pattern (per CLAUDE.md and `scripts/phase_d1_*.py` family): three scripts, explicit halt between dryrun and apply.

### 4a. D3-reconciliation — additive (LOCKED 2026-05-22)

**The question**: Phase D3 was originally specced as "30K insert" (the ~30,193 net-new HMS-only fastnums discovered during Phase A+C of the 2026-05-15→18 full-scrape — per DECISIONS 2026-05-18). The recovery now adds ~71,700 *additional* net-new fastnums (subset (b) from Step 0 partition). **The 30K and the recovery net-new are ADDITIVE**, by the following argument:

- The 30,193 counts HMS-recognized fastnums (HTTP 200) found during Phase A+C that were *not* in Supabase `properties` at scrape time. They returned HMS-200 in the original 2026-05-15→18 sequential scrape.
- The ~71,700 (subset (b)) counts fastnums that returned HTTP 500 during the dead-zone (and were not in Supabase at scrape time, per Step 0 partition) and are now reclassified to 200 by `hms_full_recovery.py`.
- A given fastnum was probed **exactly once** in the 2026-05-15→18 scrape, so it landed in either the "200" bucket (counted in 30K) OR the "500" bucket (recovery candidate). It cannot be in both.
- Therefore D3-extended scope ≈ `30,193 + |net-new (b)| ≈ ~30,193 + ~71,700 ≈ ~101,900 ≈ ~102K net-new fastnums`. Universe expands from 124,835 (current `properties` row count) to ~**227K** post-D3-extended.

**Empirical disjointness check** (cheap, ~10 sec post-recovery) — this is the *disjointness test* of the additive claim, distinct from the Step 0 partition which compared against `Supabase_at_scrape_time`:

```python
# scripts/post_recovery_d3_reconciliation_check.py (to write at execution time)
import sqlite3
NET_NEW = set(int(x) for x in open("audit/recovered_net_new.txt"))
SUPABASE_AT_SCRAPE = set(int(x) for x in open("audit/stage_a_fastnum_manifest.txt") if x.strip().isdigit())
conn = sqlite3.connect(r"file:D:\verdmat-is\app\audit\hms_archive_staging.db?mode=ro", uri=True)
ORIGINAL_30K_SET = set(
    r[0] for r in conn.execute("SELECT fastnum FROM hms_archive WHERE http_status = 200")
) - SUPABASE_AT_SCRAPE
overlap = NET_NEW & ORIGINAL_30K_SET
print(f"|original_30K_set|        = {len(ORIGINAL_30K_SET):,}  (expected ~30,193)")
print(f"|net-new (b)|             = {len(NET_NEW):,}    (expected ~71,700)")
print(f"|overlap|                 = {len(overlap):,}  (expected 0 by single-probe argument)")
print(f"D3-extended scope         = {len(ORIGINAL_30K_SET | NET_NEW):,}  (expected ~101,900)")
```

**Decision branch** on `|overlap|`:
- `|overlap| = 0` (default expected by the single-probe argument): D3-extended is one additive batch of ~102K. One run of extract → dryrun → apply on the union.
- `0 < |overlap| ≤ 10`: stragglers (e.g., fastnums probed in a Phase A retry that then landed in a Phase C dead-zone window — edge case at phase boundary). Fold into the union; document.
- `|overlap| > 10`: STOP. The single-probe argument is wrong; understand the scrape mechanic before promoting.

### 4b. D3-extended execution pattern (additive ~102K + ~97 refresh)

Three scripts in `scripts/`, mirroring `phase_d1_*.py`:

- `scripts/phase_d3_extract.py` — local-only. Reads:
  - `audit/hms_archive_staging.db` (Phase A+C 200s — the original ~30,193)
  - `audit/hms_recovery_extension.db` (the recovery output, name TBD by recovery session)
  - `audit/net_new_sales_history.csv` (Step 2 output)
  - `audit/recovered_already_in_base.txt` (subset (a) — for the refresh path)
  - `audit/recovered_net_new.txt` (subset (b) — for the insert path)
  
  Builds two candidate sets, both sized empirically from Step 0 outputs (not hard-coded):
  - **Insert candidates** (`|subset (b)| + |original 30K|` ≈ 102K rows): subset (b) ∪ original 30K. Computes derived columns (`canonical_code`, `region_tier`, `matsvaedi_bucket`, `is_residential`, `is_summerhouse`, `is_new_build`, `is_main_unit`, lat/lng from `Stadfangaskra.csv`) via `classify_property.py` + `rules.py`. Output: `D:\phase_d3_insert_rows.parquet`.
  - **Refresh candidates** (size = `|audit/recovered_already_in_base.txt|`, expected ≈ 97): subset (a), read directly from the Step 0 output file. Updates existing `properties` rows with: refreshed HMS metadata (`brunabotamat`, `lhlmat`, etc. from the recovery payload) + `deregistered = false` (un-ghost). Output: `D:\phase_d3_refresh_rows.parquet`.
- `scripts/phase_d3_dryrun.py` — reads both parquets + queries Supabase for current state. Reports: (i) insert: net-new fastnums vs unexpected collisions, (ii) refresh: confirm every fastnum in `recovered_already_in_base.txt` currently has `deregistered=true` in Supabase (sanity — if any has `deregistered=false`, surface and ask before un-ghost-ing nothing), (iii) coverage of derived columns (% with valid lat/lng, % with canonical_code resolved, % with HMS metadata), (iv) generates `D:\phase_d3_rollback.sql` (DROP inserted rows + restore `deregistered=true` on the empirical refresh set). Writes nothing to Supabase.
- `scripts/phase_d3_apply.py` — only runs after explicit Danni "halt áfram" on the dryrun report. Two atomic blocks:
  - INSERT into `properties` from `phase_d3_insert_rows.parquet` — idempotent via `ON CONFLICT (fastnum) DO NOTHING`.
  - UPDATE existing `properties` rows from `phase_d3_refresh_rows.parquet` — `SET <HMS columns> = …, deregistered = false WHERE fastnum = ANY(<empirical subset (a)>)`. Empirical set, never hard-coded.
  - INSERT into `sales_history` from `audit/net_new_sales_history.csv` — composite-key idempotency.

### 4c. Promotion order within D3-extended

1. `properties` INSERT (~102K net-new from subset (b) ∪ original 30K).
2. `properties` UPDATE (refresh + un-ghost for the empirical subset (a) from `audit/recovered_already_in_base.txt`; expected ≈ 97). Apply path reads the file at run time; never hard-codes the count.
3. `sales_history` INSERT joined on FASTNUM. Any sales row whose FASTNUM is not in `properties` post-insert is dropped + logged (should be empty if Step 0/2/3 are clean).

After this point, `properties` is at its new universe size. Predictions follow in Step 4.

---

## 5. Step 4 — Score net-new with iter4 → populate `predictions`

`iter4_final_v1` is the production model and is **HMS-feature-driven** — it deliberately uses no FASTEIGNAMAT (circularity removed in Áfangi 4) and listing-derived LLM features contribute ~nothing to the point prediction for the iter4 spec (their measured importance is dominated by structural features `einflm`, `byggar`, `canonical_code`, geography, `lod_flm`). Net-new fastnums have full HMS coverage (since recovery confirmed they're HMS-200 with payload), so they are scorable now — predictions are NOT deferred to the next training cycle.

Use the existing stateless scoring API:

```python
# scripts/post_recovery_step4_score.py (to write at execution time)
import sys
sys.path.insert(0, r"D:\\")
import score_new_listing  # loads iter4 models once
import pandas as pd
import psycopg2

# Pull the ~102K net-new fastnums' Supabase row (now that D3-extended INSERT landed)
conn = psycopg2.connect(open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read().strip())
NET_NEW = set(int(x) for x in open("audit/recovered_net_new.txt"))
ORIGINAL_30K = set(int(x) for x in open("audit/recovered_original_30k.txt"))
TO_SCORE = NET_NEW | ORIGINAL_30K  # ~102K
# Fetch the rows in chunks; score; collect into a DataFrame
# (concrete chunked SELECT + score loop omitted for spec — see Áfangi 4c
#  score_new_listing API contract: takes dict, returns calibrated mean + PI)
# Output: D:\phase_d3_predictions.parquet
```

Then `scripts/phase_d3_predictions_apply.py` inserts the rows into `predictions` (composite-key idempotency via `(fastnum, model_version, calibration_version)` ON CONFLICT). After this step, `v_current_predictions` count grows from 110,316 to ~212,000.

**Excluded from Step 4** (defer to next precompute cycle):
- `feature_attributions` — SHAP attributions are model-internal and the existing precompute pipeline (`train_iteration3.py` / iter4 successor) emits them as part of training output. Re-emitting per-fastnum requires the saved booster + the inline-derived `real_fasteignamat` — feasible but adds complexity beyond this plan's scope.
- `comps_index` — comp-finding requires recomputing nearest neighbours across the expanded universe, not a per-fastnum operation. Defer to next precompute cycle of `build_precompute.py`.

UI impact (post Step 4): `/eign/<recovered_fastnum>` will render the hero address, ByggingarstigBadge, LhlmatBar, ValuationStrip, **PredictionCard** (with iter4 point + 80%/95% PI). The AttributionWaterfall section will show empty state ("nákvæmari greining bíður næstu líkanaþjálfunar"), and CompsGrid will be empty ("sambærilegar eignir bíða næstu líkanaþjálfunar").

---

## 6. Verification + new universe size

After Steps 3 + 4 land:

- `SELECT count(*) FROM properties` → expected ~**227,000** (= 124,835 base + ~101,900 net-new from D3-extended; subset (a)'s ~97 are UPDATE not INSERT). Locked at run time as `N_NEW_UNIVERSE`.
- `SELECT count(*) FROM properties WHERE deregistered IS NOT TRUE` (i.e., `v_properties` count) → expected ~**227,000** (the 97 ghosts are now un-ghosted by subset (a)'s refresh; any subset of the original 97 that didn't recover remains `deregistered=true`).
- `SELECT count(*) FROM predictions` → expected ~**212,000** (= 110,316 base + ~101,900 new from Step 4).
- `SELECT count(DISTINCT fastnum) FROM v_current_predictions` → matches predictions distinct fastnum count.
- `SELECT count(DISTINCT FASTNUM) FROM sales_history` → grew by however many net-new fastnums had sales history in kaupskrá.

### Downstream impact analysis

The new universe is a coverage expansion + on-demand scoring, not a full precompute recompute. Specifically:

- **`v_properties`** — automatic coverage expansion. No code change needed. Frontend's `/eign/<fastnum>` returns new fastnums; search autocomplete surfaces them.
- **`v_current_predictions`** — grows by ~102K rows. New fastnums get iter4 predictions immediately. `DISTINCT ON (fastnum)` semantics unchanged.
- **`repeat_sale_index` / `v_repeat_sale_index`** — sales-based, computed from `pairs_v1` matches. Net-new fastnums with sales contribute pairs only after `rebuild_training_data.py` + `build_repeat_sale_index.py` are re-run. Until then the index is unchanged — the BMN index integrates over the full historical sales surface; adding more pairs only refines existing-cell estimates within their CIs.
- **`ats_lookup` / `v_ats_lookup_by_heat`** — precompute-driven, refreshed via `refresh_dashboard_tables.py`. No immediate change.
- **`comps_index`** — precompute-driven. Net-new fastnums won't appear as comps and won't have comps until the next `build_precompute.py` cycle.
- **`feature_attributions`** — precompute-driven, predictions-coupled. Empty for net-new fastnums until next training-cycle output is loaded (gap shown explicitly in UI: AttributionWaterfall empty state).
- **Search autocomplete (`search_properties_grouped` RPC)** — automatic — the RPC queries `properties` directly. Net-new fastnums searchable immediately post-D3-extended.

**Sanity checks to run post-apply**:
- [ ] `/eign/<one_net_new_fastnum>` renders 200, hero displays heimilisfang/postnr, ByggingarstigBadge + LhlmatBar conditional on the new HMS fields working, PredictionCard renders iter4 point + 80%/95% PI, AttributionWaterfall + CompsGrid show "bíður næstu þjálfunar" empty state.
- [ ] `/eign/<one_un_ghosted_fastnum>` (one of the recovered subset (a) rows) renders 200, previously deregistered, now visible.
- [ ] Search autocomplete `?q=<known_heimilisfang_from_net_new>` returns the new row.
- [ ] `/markadur` and all `/markadur/*` sub-pages render unchanged (they read from precompute-derived tables that haven't moved).
- [ ] No PostgREST 42501 / 42703 errors on any page.

---

## 7. Runnable checklist (one-page)

```
GATES (both must be ✓ before anything below)
[ ] G1  hms_full_recovery.py complete; audit/recovered_fastnums_locked.txt materialized
[ ] G2  production-template hardening landed (PLANNING_BACKLOG item 5)

STEP 0  Magnitude confirmation + recovered-set partition
[ ] write & run scripts/post_recovery_step0_partition.py
[ ] |already-in-base (a)| ≤ ~120 confirmed (expected ~97); STOP if much higher
[ ] outputs: audit/recovered_already_in_base.txt, audit/recovered_net_new.txt

STEP 1  Evalue augl pass for net-new subset (b)
[ ] new staging DB: audit/stage_a_augl_recovered.db (do NOT touch stage_a_augl_staging.db)
[ ] run hardened-template refresher on subset (b) only; ~28h single-worker
[ ] HALT and report: N_net_new_with_listings, ghost count, error count

STEP 2  Kaupskrá lookup for net-new subset (b)
[ ] refresh D:\kaupskra.csv via refresh_kaupskra.py (idempotent)
[ ] write & run scripts/post_recovery_step2_kaupskra.py
[ ] output: audit/net_new_sales_history.csv
[ ] HALT and report: N_net_new_with_sales, total_sales_rows

STEP 3  Supabase promotion (D3-extended)
[ ] D3-reconciliation: write & run scripts/post_recovery_d3_reconciliation_check.py
[ ] confirm |overlap| = 0 (additive locked) OR halt-and-investigate if > 10
[ ] write scripts/phase_d3_extract.py → D:\phase_d3_insert_rows.parquet + refresh_rows.parquet
[ ] write scripts/phase_d3_dryrun.py → halt for Danni's "halt áfram"
[ ] (after halt áfram) write scripts/phase_d3_apply.py → execute (INSERT then UPDATE then sales_history)

STEP 4  Score net-new with iter4 → populate predictions
[ ] write scripts/post_recovery_step4_score.py (uses D:\score_new_listing.py API)
[ ] output: D:\phase_d3_predictions.parquet
[ ] write scripts/phase_d3_predictions_apply.py → insert into predictions
[ ] post-apply: 5 sanity checks per §6

CLOSE
[ ] DECISIONS.md additive entry: D3-extended applied + Step 4 scored, N_new_universe,
    counts of insert/update/refresh, coverage stats
[ ] STATE.md additive Roadmap update: Phase D3 ✅
[ ] PLANNING_BACKLOG: mark item 6 closed; note follow-ups: next-training-cycle for
    feature_attributions / repeat-sale / comps_index refresh on the net-new fastnums
[ ] git commit (explicit paths) + git push
```

---

## 8. What this plan does NOT cover (handed off to other lanes / future sessions)

- **D4 (cross_property_refs)** — the HMS recovery v2 captures `stadfangData.fasteignir[]` (systur-fastnums on the same staðfang) in the `full_response` column. D4 will use that to populate a `cross_property_refs` table. Out of scope; gated on D4 spec.
- **D5 (photo_urls_json)** — backfill the `photo_urls_json` column for net-new fastnums from the existing image archive at `D:\Gagnapakkar\images\` if any are already mirrored, or fetch fresh via the augl payloads from Step 1. Out of scope; gated on D5 spec.
- **iter5 retraining** — once D3-extended + Step 4 land + D4/D5 follow, `rebuild_training_data.py` needs the Supabase HMS export step (PLANNING_BACKLOG item 1, 2026-05-20) and then iter5 can train on the expanded universe with the new HMS features. Separate session.
- **`feature_attributions` + `comps_index` refresh** — predictions-coupled / nearest-neighbour-coupled; defer to next `build_precompute.py` cycle. UI shows empty state for net-new fastnums in the meantime.
- **Phase X Group B column-grant lockout** — the deployed-frontend confirmation step from the 2026-05-21 DECISIONS entry. **Independent of this plan** — neither blocks the other. Column-grant lockout is the *next focused session* (scheduled first per user priority, gates on deployed-frontend prod confirmation). This plan runs on its own gated track (proceeds when G1 + G2 are green, on its own schedule). Phase X Group C runs after the column-grant lockout completes.

---

## 9. Open decision points

| # | Question | Position | Locked? |
|---|---|---|---|
| 1 | Are the original 30K and the recovery net-new additive or overlapping? | Additive (~30K + ~71.7K ≈ ~102K) | **YES** — locked 2026-05-22 (Danni review). Disjointness empirically confirmed via §4a check before Step 3 apply. |
| 2 | Step 0 partition threshold for "investigate" | `|already-in-base| > ~120` triggers investigate; `= 0` triggers sanity-check | YES (proposed) |
| 3 | Step 1 own staging DB name | `audit/stage_a_augl_recovered.db`, schema mirror of `stage_a_augl_staging.db` | YES (proposed) |
| 4 | Step 3 promotion order | INSERT properties → UPDATE properties (refresh subset (a)) → INSERT sales_history | YES (proposed) |
| 5 | Step 4 scoring scope | Score all ~102K net-new with iter4 (HMS-feature-driven; listing features ~zero contribution to point pred). feature_attributions + comps_index deferred to next precompute cycle. | YES (proposed) |
| 6 | Concurrency for Step 1 (~71.7K rows × 1.4 s) | Single-worker, ~28h, polite to evalue.is | YES (proposed) |
| 7 | What about D2 ghost members that do NOT recover under `hms_full_recovery.py`? | Stay `deregistered=true`. With the outage-aware hardened template (gate G2), a non-recovering re-probe is HMS-confirmed real deregistration — no further action needed. | **YES — LOCKED 2026-05-22.** |
