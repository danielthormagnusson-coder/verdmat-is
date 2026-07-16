# verdmat.is — MODEL CARD (iter4, production) — Fable-prep

> **Purpose.** Dense, numeric ground-truth of the *current* production valuation stack so a frontier model can reason without re-deriving. Read-only capture from `origin/main` + on-disk artifacts. **This file is untracked scratch under `docs/fable_prep/` — not a canonical doc.**
> **Captured:** 2026-07-01. **Authoritative sources:** `origin/main` (both repos in sync, 0/0 ahead/behind) + `D:\` artifacts + live Supabase (read-only).
> **Do not trust the Project-Files panel** (shows stale iter3). Everything below reconciles against the model's actual feature list and artifacts.

---

## 0. TL;DR — what is live right now

| Fact | Value | Source |
|---|---|---|
| **Production sale model** | `iter4_final_v1` (LightGBM, **no fasteignamat**) | `predictions.model_version` (live), `rebuild_predictions_iter4.py:52` |
| Live prediction rows | **167,503** (1 cohort, `predicted_at=2026-07-01`) | Supabase `public.predictions` |
| Boosters | `iter4a_*.lgb` — 12 files (main+summer × {mean,q025,q100,q500,q900,q975}) | `D:\iter4a_*.lgb`, 2026-04-21 |
| Held MAPE (main, N=2,084) | **8.19%** (medAPE 5.54%, bias(log) +0.013) | `iter4a_training_log.txt` |
| Calibration in prod | `iter4_segcal_v1` (per-segment empirical **stretch** on native quantiles) | `rebuild_predictions_iter4.py:287-333` |
| CPI real-anchor | frozen `MODEL_ANCHOR_YM=2026-05`; `cpi_factor_valuation=cpi[2026-05]/cpi[2026-07]=0.991232` | `rebuild_predictions_iter4.py:50,107-111` |
| **Rent model** | `rent_v1` — scored to **staging only**, **NOT promoted** | Supabase: `predictions_rent`=0, `predictions_rent_staging`=**158,314** |
| ATS (ask-to-sale) | lookup tables, not a model — Table B `public.ats_lookup` (65 rows) primary | `ats_lookup.csv`, DECISIONS 2026-04-20 |

**Model is frozen until iter5** (real-scale anchor pinned; valuation-month moves independently of the frozen anchor).

---

## 1. iter3 → iter4 reconciliation — the FASTEIGNAMAT drop (design choice, documented cost)

**iter4 removes fasteignamat entirely.** Confirmed independently in three places:

1. `iter4a_training_log.txt` header: *"iter4a — standalone training (NO FASTEIGNAMAT)"* · *"skipping real_fasteignamat computation (fastmat removal)"* · *"Features: 154 (iter3v2 had 156; iter4a drops FASTEIGNAMAT + no real_fasteignamat)"*.
2. `iter4a_feature_importance.csv` — no fasteignamat feature present at all. Top gain now: `EINFLM` 34.5%, `sale_year` 19.6%, `matsvaediNUMER` 17.6%, `matsvaedi_bucket` 14.2%, `BYGGAR` 4.5%.
3. `rebuild_predictions_iter4.py:237` (prod inference): *"No FASTEIGNAMAT, no real_fasteignamat."*

**Why (DECISIONS 2026-04-21):** HMS fasteignamat is *itself* a hedonic regression on kaupskrá → using it as input is circular and makes the prediction pre-determined by HMS. Annual HMS updates (every June) cause **5–10% overnight prediction jumps with zero registered transactions** — fatal for bank / pro-user use cases where stability outranks 1–2 pp MAPE. Fasteignamat still shown on UI as *"reference only"*, never as input.

**Cost, documented (DECISIONS 2026-04-21):** held MAPE **8.19%** (iter4a) vs **7.97%** (iter3v2) = **+0.22 pp** for full fasteignamat independence. iter4b (`init_model` fine-tune) abandoned as technically infeasible (feature-drop breaks the `init_model` feature-compatibility contract). iter4a is the winner by default.

**Memory correction:** iter3 did not put ~65% importance on a single fasteignamat feature; it was **~77.9% combined** on `real_fasteignamat` + `FASTEIGNAMAT` (iter1: real 63% + nominal 13%). DECISIONS notes that gain was largely **collinear** with size/location/age/time — LightGBM re-learns the signal from `EINFLM + matsvaedi_bucket + matsvaediNUMER + sale_year + BYGGAR` without the fastmat mediator.

**Link to the hard segments (§4/§8):** fasteignamat carried ~78% gain and encoded hard-to-model location/quality signal; **its removal bites hardest exactly where the structured primitives are weakest — SFH_DETACHED and Country tier** (see §4 held table: SFH_DETACHED|Country 22.2% MAPE vs RVK_core APT 6–7%).

---

## 2. Pipeline

**Target:** `log_real_kaupverd` = log of CPI-deflated sale price. LightGBM L2 (mean) + 5 pinball-quantile models (α = 0.025, 0.10, 0.50, 0.90, 0.975).

**Split — SINGLE temporal train/val/test/held (NOT k-fold):**

| Split | Role | Main N | Notes |
|---|---|---|---|
| train_ext | train + val(2024) folded in | 129,769 | includes ≤2023 + 2024 |
| test | early-stopping / conformal calib | 8,575 | (2025) |
| held | **primary eval** — pure holdout | 2,084 | (2026, OOS) |

- Training data: `D:\training_data_v2.pkl` (146,038 × 170; main 140,428 / summer 3,826). OOS cutoff = **2026-04-20** (`.lgb` mtime); `predicted_at` is a stamp, not a cutoff.
- **`onothaefur=0` (non-market-sale) filter is MANDATORY on OOS eval** — without it MAPE 56%/bias −37%; with it 16%/−0.8% (DECISIONS line 209).

**CPI real-adjustment + anchor:**
- `real_kaupverd = KAUPVERD × cpi_factor`; target trained in real log-space.
- Prod re-scales log-space (real @ `MODEL_ANCHOR_YM=2026-05`) → nominal @ valuation via `cpi_factor_valuation = cpi[2026-05]/cpi[2026-07] = 0.991232`, read from `cpi_verdtrygging.csv` (verðtryggingarvísitala, published 2 months forward, final).
- **Model anchor frozen at 2026-05 until iter5**; `valuation_month` is separate → changing valuation month does NOT move the frozen anchor (parity-verified).

**Segmentation:**
- **Model split:** `main` (residential, ex-summerhouse) vs `summer` (SUMMERHOUSE) — separate boosters (`min_data_in_leaf` 40 vs 15).
- **Calibration segmentation:** `canonical_code` (segcal) and `canonical_code × region_tier` (conformal Mondrian). region_tier ∈ {RVK_core, Capital_sub, Country}.

---

## 3. Feature set

**154 features**, categoricals = `['canonical_code','matsvaedi_bucket','region_tier','unit_category']`. NaN-native (missing features stay NaN at inference).

**Top-20 gain (main mean model, `iter4a_feature_importance.csv`):**

| # | feature | gain % | # | feature | gain % |
|---|---|---|---|---|---|
| 1 | EINFLM (size m²) | 34.52 | 11 | landnum | 0.46 |
| 2 | sale_year | 19.59 | 12 | merking_floor | 0.41 |
| 3 | matsvaediNUMER | 17.62 | 13 | lon | 0.37 |
| 4 | matsvaedi_bucket | 14.24 | 14 | unit_category | 0.35 |
| 5 | BYGGAR (build year) | 4.51 | 15 | sale_month | 0.32 |
| 6 | postnr | 1.67 | 16 | canonical_code | 0.27 |
| 7 | building_max_floor | 1.54 | 17 | floor_fraction | 0.18 |
| 8 | age_at_sale | 1.29 | 18 | needs_immediate_work_flag | 0.17 |
| 9 | LOD_FLM (lot m²) | 0.88 | 19 | region_tier | 0.14 |
| 10 | lat | 0.62 | 20 | listing_elaboration_ord | 0.12 |

Top-5 primitives (size/time/geography/age) = **~90% of gain**. The tail (~135 features) is condition/status/issue/amenity flags each <0.2%.

**Extraction / LLM features (~95 engineered cols from a ~$375 Haiku extraction run):** condition scores, status ordinals, issue flags, amenity flags, `listing_elaboration_ord`, etc. **Combined contribution ≈ 1% of gain** (DECISIONS line 3520; the last feature `has_extraction_data` has gain 0.0). Documented reason: condition correlates with price but residual correlation after structured features is only −0.20 on held; LightGBM captures the same variance via dense confounders (is_new_build, age_at_sale, matsvaedi_bucket) at 24% extraction coverage.

---

## 4. Held metrics per segment (iter4, computed from artifacts)

> **Method (per instruction, reconciles with audit CC-lota B):** `iter4a_predictions.pkl ⨝ training_data_v2.pkl` on `FAERSLUNUMER` → held split. residual = log(actual) − log(pred); MAPE on **real scale**; coverage from native quantiles (q100/q900 = 80%, q025/q975 = 95%). Recomputed table reconciles with `iter4a_training_log.txt` (APT_STANDARD 6.37%, SFH_DETACHED 16.29%, summer 175% — match).
>
> **⚠ SPLIT CAVEAT:** all figures come from **one temporal split** (not k-fold CV). Held-n is small on weak segments. **Cells marked ⚠ have n<60 → thin statistical power.**
> **⚠ COVERAGE CAVEAT:** cov80/cov95 below are **RAW native-quantile** (pre-calibration). Production applies `iter4_segcal_v1` stretch (§5); the split-conformal artifact reaches target (§5).

**Held total (main+summer, N=2,131):** MAPE 11.87% · medAPE 5.64% · bias(log) +0.01 · cov80 66.5% · cov95 89.2%
**Held main only (N=2,084):** MAPE 8.19% · medAPE 5.54% · bias(log) +0.013

**Per canonical_code (held):**

| canonical_code | N | MAPE% | medAPE% | bias_log | cov80% | cov95% |
|---|---:|---:|---:|---:|---:|---:|
| APT_STANDARD | 740 | 6.37 | 4.82 | 0.00 | 65.1 | 89.3 |
| ROW_HOUSE | 100 | 7.24 | 5.16 | 0.01 | 78.0 | 93.0 |
| APT_FLOOR | 1,019 | 8.55 | 5.86 | 0.02 | 66.1 | 88.9 |
| APT_ATTIC ⚠ | 17 | 9.06 | 4.32 | −0.02 | 82.4 | 94.1 |
| SEMI_DETACHED ⚠ | 48 | 9.48 | 5.96 | 0.00 | 54.2 | 83.3 |
| APT_BASEMENT ⚠ | 51 | 10.90 | 7.01 | 0.02 | 66.7 | 92.2 |
| SFH_DETACHED | 106 | 16.29 | 10.10 | 0.03 | 67.0 | 85.9 |
| APT_UNAPPROVED ⚠ | 3 | 9.08 | 4.14 | 0.09 | 66.7 | 100.0 |
| SUMMERHOUSE ⚠ | 47 | 175.13 | 22.11 | −0.17 | 74.5 | 91.5 |

**Per region_tier (held):**

| region_tier | N | MAPE% | medAPE% | cov80% | cov95% |
|---|---:|---:|---:|---:|---:|
| RVK_core | 803 | 6.84 | 4.94 | 70.4 | 92.0 |
| Capital_sub | 798 | 12.32 | 5.01 | 64.4 | 87.0 |
| Country | 473 | 17.32 | 9.63 | 64.9 | 89.0 |

**Per region_tier × canonical_code (held) — cells with n≥30 shown; ⚠ = n<60:**

| region_tier | canonical | N | MAPE% | medAPE% | cov80% | cov95% |
|---|---|---:|---:|---:|---:|---:|
| RVK_core | APT_STANDARD | 379 | 6.00 | 4.69 | 68.1 | 90.5 |
| RVK_core | APT_FLOOR | 345 | 7.28 | 5.40 | 72.2 | 93.0 |
| RVK_core | APT_BASEMENT ⚠ | 36 | 11.43 | 7.41 | 61.1 | 91.7 |
| Capital_sub | APT_STANDARD | 265 | 5.81 | 4.30 | 64.9 | 89.4 |
| Capital_sub | APT_FLOOR | 416 | 7.19 | 5.19 | 61.8 | 84.6 |
| Capital_sub | ROW_HOUSE ⚠ | 47 | 4.67 | 4.27 | 83.0 | 93.6 |
| Capital_sub | SFH_DETACHED ⚠ | 33 | 8.13 | 6.16 | 69.7 | 90.9 |
| Capital_sub | SUMMERHOUSE ⚠ | 9 | 512.33 | 29.67 | 66.7 | 77.8 |
| Country | APT_FLOOR | 233 | 10.68 | 8.06 | 67.4 | 91.9 |
| Country | APT_STANDARD | 78 | 9.80 | 7.68 | 53.8 | 85.9 |
| Country | **SFH_DETACHED** | 61 | **22.15** | 13.80 | 63.9 | 82.0 |
| Country | ROW_HOUSE ⚠ | 38 | 10.24 | 9.39 | 71.1 | 89.5 |
| Country | SUMMERHOUSE ⚠ | 37 | 76.16 | 19.93 | 78.4 | 94.6 |
| Country | SEMI_DETACHED ⚠ | 21 | 14.24 | 12.04 | 42.9 | 76.2 |

**Reading:** accuracy floor is RVK_core apartments (~6–7% MAPE). The stress axis is **Country × SFH/summer** — exactly where fasteignamat's dropped location signal was doing the most work.

---

## 5. Uncertainty

**Two artifacts exist; know which is live.**

**(A) Production — `iter4_segcal_v1` (`iter4_calibration_config.json`, 2026-04-21).** Per-segment empirical **stretch** of the native LightGBM quantiles around the mean:
```
lo80 = mean − k80·(mean − q100);  hi80 = mean + k80·(q900 − mean)
lo95 = mean − k95·(mean − q025);  hi95 = mean + k95·(q975 − mean)
```
k-factors are per-`canonical_code`, near 1.0 (APT_FLOOR k80=1.05, APT_STANDARD k80=1.07, SFH k80=1.00, `_global_fallback` k80=1.05, k95=1.03). Calibrated on the **quality-filtered val+test pool** (`is_quality_transaction`, drops `KAUPVERD/FASTEIGNAMAT ∉ [0.70,1.50]`). **This is what `rebuild_predictions_iter4.py` writes to the live `real_pred_lo80/hi80/lo95/hi95` columns.**

> **⚠ Coverage gap worth flagging:** because segcal was fit on the *quality-filtered* pool (where native quantiles ≈ target, hence k≈1.0), on the *unfiltered* held set the same intervals cover only **66.5% (80% PI) / 89.2% (95% PI)** — i.e. the live 80% PI likely under-covers. Artifact (B) is the fix but is **not wired into the prod rebuild**.
>
> **[LEIÐRÉTT 2026-07-15 cc4 — línan að ofan er STALE]** Artifact (B) VAR tengt og flippað LIVE **2026-07-02** (sjá DECISIONS „Conformal PI (iter4_conformal_v1) + width-based A/B/C/D confidence-grade FLIPPAÐ LIVE"). Lifandi `predictions` er 100% `calibration_version='iter4_conformal_v1+segcal_fb'`; segcal (A) lifir aðeins sem fallback fyrir SUMMERHOUSE + kóða utan artifacts. Sama stale-fullyrðing rataði í fable-audit F.3 (VERDMAT_FLIPI_2_2026-07-15T1127Z.md) — leiðrétting þar bíður cc2-push (prod-repo lás).

**(B) Verified alternative — `iter4_conformal_v1` (`iter4_conformal_corrections.json`, 2026-04-21).** Split-conformal, symmetric, **log-space**; nonconformity = `|log_real − pred_mean_log|`; half-widths = empirical 80th/95th `|resid|` quantiles; **Mondrian cascade** `canonical_code×region_tier → canonical_code → global` (MIN_N via cell presence), calibrated on the test split (n=8,575). **Verified held coverage: 80% → 79.1%, 95% → 94.6%** (per-canonical held cov80 77–88%). `rent_conformal.py` calls this *"the sale-side LIVE conformal layer"* and mirrors it — so treat (B) as the intended conformal method, but confirm wiring before quoting its coverage as live.

---

## 6. Ask-to-sale (ATS) gap — lookup, not a model (Áfangi 7, DECISIONS 2026-04-20)

Built by `build_ats_lookup.py` from `pairs_v1.pkl` paired_fresh subset (~52K clean ask↔sale pairs, 1.7s runtime). Dual-table:

- **Table A — `ats_lookup_by_quarter`** (913 rows): per `canonical_code × region_tier × quarter` + heat_bucket + data_quality. Historical fidelity.
- **Table B — `ats_lookup` (= `ats_lookup_by_heat`, 63–65 rows): PRIMARY scoring table.** Pooled per `canonical_code × region_tier × heat_bucket`. Columns: `n_pairs, median_log_ratio, dispersion_sd, dispersion_mad, above_list_rate, p33, p67, data_quality`.

**Scoring:** `pi_80 = list_price × exp(median_log_ratio ± 1.28 × dispersion_mad)`; dispersion = `MAD × 1.4826` (robust, self-consistent with median center).

**SD-collapse argument (why pool into Table B):** per-quarter dispersion **collapses / is unstable in thin cells**, and the newest quarter is *always* thin (þinglýsing lag) → cold-start. Pooling by heat_bucket yields robust MAD dispersion in thin cells and removes the cold-start hole (0 insufficient cells in B post-pooling). Fallback: B first, A latest-row only if B insufficient (rare). Quality floors: Table B `n<10` insufficient; high = n≥20 ∧ sd<0.05.

---

## 7. Rent model (`rent_v1`) — scored, calibrated, NOT promoted

**Status (Supabase, live):** `predictions_rent` = **0** · `predictions_rent_staging` = **158,314** · `feature_attributions_rent_staging` = **1,583,140**. Conformal artifact says *"promotion: NONE — Supabase write is a future single transaction."* → **pipeline is scored into staging and conformal-calibrated, but the live rent path is not yet switched on.**

**Model (`train_rent_v1.py`):** LightGBM, target = `log1p(HEILDARVERD)` (total rent). **Fasi 1 = time-as-feature, no deflator (gate G2); fasteignamat NOT in features (gate G4).** Features (18) = 12 numeric (`staerd, einflm_canonical, byggar, fj_herbergi, lod_flm, lat, lng, contract_year, contract_month, t_cont, age, otimabundid`) + 6 categorical (`canonical_code, matsvaedi_bucket, region_tier, unit_category, tegund, sveitarfelag`). Data: `leiga_train.parquet` (2011–2023).

**CV scheme:** (a) **GroupKFold grouped-by-fastnum, 5 folds** (each fastnum wholly in one fold) → OOF MAPE/medAPE; (b) **2023-temporal holdout** (train ≤2022, test 2023), total + per-segment (sveitarfélag / herbergi / tegund).

**OOF point-metrics:** ⚠ **`train_rent_v1.py` writes nothing to disk (reports to stdout only) and no run log is persisted → clean OOF total MAPE PENDING (do not quote).** Documented per-tegund figures from `rent_conformal.py` provenance (Stage-4 temporal): **Einbýli 18.9% MAPE, Fjölbýli 12.1% MAPE**.

**Anchor layer (`rent_recalibration.py`, Skref 7, v2 herbergi-resolved):** level-anchor via leiguverðsjá `MEDAL_FERMETRAVERD` (per-m², composition-clean) with a **herbergi gradient** (leiguverðsjá 2024→2026 movement is room-count-varying: +20.5% for 1-herb vs +10.4% for 6+, span 10pp — real segment inflation, not artifact). `anchored = model_fm × STAERD × HFAC(h) = model_total × HFAC(h)`. T_ref = 2023 (data edge; forward extrapolation absorbed into k). HFAC (herbergi factors) 1→1.156 … 6+→0.769.

**Conformal (`rent_conformal.py`, Fasi 3, `rent_conformal_v2_tegund`):** split-conformal, symmetric, log-space — mirror of sale `iter4_conformal_v1` **plus one surgical Mondrian axis: `tegund`, EINBÝLI-ONLY.** Cascade: `if tegund==Einbýli: cc|region|tegund → cc|region → cc → global; else: cc|region → cc → global` (MIN_N=30). Rationale: rent has neither fasteignamat anchor nor dense data, so Einbýli systematically under-covers (80%→73%) under cc×region; the extra axis fires only for Einbýli (purely additive — widens Einbýli, byte-identical elsewhere).
**Verified held coverage (artifact `rent_conformal_corrections.json`):** **80% → 80.55%, 95% → 94.99%** (held n=21,787; calib n=22,622); median PI width 38.2% (80%) / 77.1% (95%). Cells: 6 cc×reg×tegund, 22 cc×reg, 10 cc.

**Scorer (`score_rent_universe.py`, Lota 3):** frozen model + Stage-7 herbergi anchor + conformal v2; reads canonical features direct from `public.properties` (`.strip()` on CHAR-padded `sveitarfelag`); `predicted_at=2026-05-01`; `model_version='rent_v1'`, `calib='rent_anchor_v2_herbergi_fm+conformal_v2_tegund'`. DB read-only, writes CSVs → staging tables.

---

## 8. Known limitations (documented)

| Limitation | Evidence |
|---|---|
| **SFH_DETACHED weak, esp. Country** | held MAPE 16.3% overall; Country×SFH **22.2%** (n=61). Structured features under-discriminate where fasteignamat's location signal was doing the work. |
| **SUMMERHOUSE effectively unmodeled** | held MAPE 175% (n=47); train N=3,826. Market dominated by land-value/amenity/waterfront/condition that structured features don't capture (DECISIONS line 3891). Separate booster, but signal-starved. |
| **Live 80% PI under-covers** | ~~segcal fit on quality-filtered pool → raw held cov80 66.5% (§5). Conformal artifact (79.1%) exists but not wired to prod rebuild.~~ **[LEIÐRÉTT 2026-07-15 cc4]** Conformal LIVE síðan 2026-07-02 (DECISIONS-færsla; sjá §5-leiðréttingu). Eftirstæð spurning er hvort 2025-kvörðunin heldur 80% á eftir-cutoff sölum — mælt í CONFORMAL_RECAL cc4-lotu. |
| **Extraction/LLM features ≈ 1% gain** | near-saturated hedonic signal from size+age+matsvæði; `has_extraction_data` gain 0.0 (§3). |
| **Single split, thin weak-segment n** | no k-fold; SFH n=106, summer n=47, several cells n<60 (§4). |
| **Model frozen until iter5** | real-anchor pinned 2026-05; per-prediction anchor inferred not stored — iter5 must write `model_pred_anchor_ym` per rebuild (DECISIONS line 263). |
| **Rent not live** | staged (158,314), OOF total unpersisted, promotion is a future single txn (§7). |
| **Quality filter tension** | `kv_ratio ∉ [0.70,1.50]` drop excludes ~11K genuine new-builds from train (kept in held) — historical trade-off (DECISIONS line 3446). |

---

## 9. File index (where each artifact lives)

**Repos (both `origin/main`, in sync):** app `D:\verdmat-is\app` (`6eb43bc`); precompute `D:\verdmat-is\precompute` (`090de2c`).

**Sale model / calibration (`D:\` root, 2026-04-21):**
| Artifact | Path |
|---|---|
| Boosters (12) | `D:\iter4a_{main,summer}_{mean,q025,q100,q500,q900,q975}.lgb` |
| Predictions (train-time) | `D:\iter4a_predictions.pkl` (144,254 × 19) |
| Feature importance | `D:\iter4a_feature_importance.csv` |
| Training log (metrics) | `D:\iter4a_training_log.txt` |
| Segcal (LIVE calibration) | `D:\iter4_calibration_config.json` (`iter4_segcal_v1`) |
| Conformal (verified alt) | `D:\iter4_conformal_corrections.json` (`iter4_conformal_v1`) |
| Training data | `D:\training_data_v2.pkl` (146,038 × 170, 2026-06-28) |
| CPI | `D:\cpi_verdtrygging.csv` |
| Training script | `D:\verdmat-is\models\train_iter4a.py`; calib `calibrate_iter4.py`, `conformal_calibration.py` |

**Prod inference / precompute:**
| Artifact | Path |
|---|---|
| Rebuild scorer | `D:\verdmat-is\precompute\rebuild_predictions_iter4.py` |
| Predictions export | `D:\verdmat-is\precompute\exports\predictions_iter4.csv` (167,503, 2026-06-30) |
| SHAP export | `…\exports\feature_attributions_iter4.csv` (1,675,030 rows) |
| Live tables | Supabase `public.predictions` (167,503, iter4_final_v1), `feature_attributions` |

**ATS:** `…\exports\ats_lookup.csv` (Table B) · `ats_lookup_by_quarter.csv` (Table A) · Supabase `public.ats_lookup` (65), `v_ats_lookup_by_quarter` (913).

**Rent (`D:\verdmat-is\precompute`):**
| Artifact | Path |
|---|---|
| Train | `train_rent_v1.py` · Anchor `rent_recalibration.py` · Conformal `rent_conformal.py` · Scorer `score_rent_universe.py` |
| Training data | `data\processed\leiga_train.parquet` (2011–2023) · repeat index `leiga_repeat_index.parquet` |
| Calib configs | `data\processed\rent_calibration_config.json` (anchor) · `rent_conformal_corrections.json` (conformal v2_tegund) |
| Exports | `exports\predictions_rent.csv` (2026-07-01) · `exports\feature_attributions_rent.csv` |
| Live tables | Supabase `predictions_rent` (0), `predictions_rent_staging` (158,314), `feature_attributions_rent_staging` (1,583,140) |

**Canonical docs (`D:\verdmat-is\app\docs`):** `STATE.md` (217KB), `DECISIONS.md` (414KB) — both 2026-06-30. Key entries: iter4 standalone 2026-04-21; ATS Áfangi 7 2026-04-20; extraction ≈1% gain line 3520; OOS methodology line 209.
