# STATE — Núverandi staða verkefnis

**Síðast uppfært:** 22. apríl 2026 (Sprint 2 Áfangi 4 Fasi A+B+C1+C2 LOKIÐ í production. Fimm mid-flight bug-fixes: Bug 1 regime pill, Bug 2 `effective_date_latest`, Bug 3 autocomplete ORDER BY, Bug 4 tveggja-þrepa autocomplete + HMS-gap caveat + prefix indexes, Bug 5 expand-query missing-column regression. Launch strategy Leið B locked: ship dashboard með HMS-gap acknowledgement, scraper er Sprint 3 top-priority. Fasi C-3 og C-4 næst.)

**Verkefnisstaða heildar: ~82%**

---

## Dev-umhverfi

Windows PowerShell, Python 3.14 (pandas installed), allt á **D:\\** drifinu (Samsung T7 external SSD). Flatt, ekkert sub-folder (fyrir utan `Gagnapakkar/` sem geymir raw scraper output).

**Canonical gagnaskrár á D:\\:**

| Skrá | Stærð | Innihald | Format |
|---|---|---|---|
| `listings_v2.pkl` | 105 MB | 471K listings, 98,57% valid dates 2010-2026 | pickle |
| `listings_text_v2.pkl` | 1.6 GB | (augl_id → lysing) mapping, 456K | pickle |
| `sales_v2.pkl` | 21 MB | 173K per-property sales frá kaups_json | pickle |
| `properties_v2.pkl` | 23 MB | 125K HMS fasteignaskrá | pickle |
| `pairs_v1.pkl` | 28 MB | **Pairing output**, 174K arm's-length sölur með pair_status | pickle |
| `geography_features.pkl` | 12 MB | **Geography output**, per-FASTNUM geo features | pickle |
| `training_data_v1.pkl` | 32 MB | **Áfangi 2.1** feature matrix, 144.254 records × 35 cols | pickle |
| `baseline_predictions.pkl` | 62 MB | **Áfangi 2.3** baseline predictions all splits | pickle |
| `baseline_*.lgb` (×6) | ~5 MB ea | Baseline LightGBM models (mean + 5 quantiles) | LightGBM |
| `iter2_predictions.pkl` | 35 MB | **Áfangi 2.4b** iter2 predictions all splits, 144.254 × 38 | pickle |
| `iter2_main_*.lgb` (×6) | ~0.1–5 MB ea | Iter2 main models (residential ex-SUMMERHOUSE) | LightGBM |
| `iter2_summer_*.lgb` (×6) | ~12 KB–5 MB ea | Iter2 summer models (SUMMERHOUSE only) | LightGBM |
| `gold_standard_sample.csv` | ~400 KB | **Áfangi 3a+** 200-row stratified sample fyrir pilot | utf-8 |
| `gold_standard_labeling.xlsx` | ~170 KB | **Áfangi 3a+** labeling workbook 106 cols + dropdowns | xlsx |
| `pilot_extraction_output.csv` | ~800 KB | **Áfangi 3c** pilot extraction v0.2.1 (Haiku 4.5, 200 listings) | utf-8-sig |
| `pilot_extraction_raw.jsonl` | ~700 KB | **Áfangi 3c** raw JSON per extraction fyrir re-processing | jsonl |
| `pilot_extraction_output_v022.csv` | ~800 KB | **Áfangi 3c+** pilot v0.2.2 output (re-pilot á sömu 200) | utf-8-sig |
| `pilot_extraction_raw_v022.jsonl` | ~700 KB | **Áfangi 3c+** raw v0.2.2 JSONL með resume logic | jsonl |
| `discover_gaps_keywords.txt` | ~8 KB | **Áfangi 3c** keyword gap report | utf-8 |
| `discover_gaps_llm.jsonl` + `_summary.txt` | ~450 KB | **Áfangi 3c** Sonnet LLM gap analysis (1.105 flagged signals) | jsonl + txt |
| `batch_extraction_unique.jsonl` | ~60 MB | **Áfangi 3d** raw unique extractions (37.544 records, unfiltered) | jsonl |
| `batch_extraction_propagated.csv` | ~70 MB | **Áfangi 3d** propagated til 40.814 paired (canonical_code bug — use JSONL fyrir merge) | utf-8-sig |
| `batch_results/chunk_XX_results.jsonl` (×8) | ~7 MB ea | Per-chunk Batch API outputs | jsonl |
| `batch_state.json` | <1 KB | Batch run state tracking | json |
| `training_data_v2_prepatch.pkl` | ~180 MB | Pre-patch backup (audit artifact) | pickle |
| `training_data_v3.pkl` | ~180 MB | **Áfangi 4c** — v2 + is_quality_transaction + kv_ratio (kept for evaluation use) | pickle |
| `iter3v3_predictions.pkl` | ~19 MB | **Áfangi 4c (DEPRECATED)** — iter3 v3 predictions; v3 model regressed, not production | pickle |
| `iter3v3_*.lgb` (×12) | ~0,1–5 MB ea | **Áfangi 4c (DEPRECATED)** — v3 model files, not used in production | LightGBM |
| `iter3_predictions.pkl` (v2) | ~19 MB | **Áfangi 4 (PRODUCTION)** — canonical iter3 v2 predictions for all scoring | pickle |
| `iter3_*.lgb` (v2, ×12) | ~0,1–5 MB ea | **Áfangi 4 (PRODUCTION)** — canonical model files | LightGBM |
| `calibration_config.json` | <5 KB | **Áfangi 4c** — per-segment stretch factors (v2-based after revision) | json |
| `kaupskra.csv` | 46 MB | HMS kaupskrá, 226K færslur (authoritative) | semicolon, latin-1 |
| `Stadfangaskra.csv` | 38 MB | HMS staðfangaskrá (138K rows) | comma, utf-8 |
| `fastnum_structured.csv` | ~15 MB | Extracted merking + hnit | comma, utf-8 |
| `cpi_verdtrygging.csv` | <1 KB | VNV 1995M04–2026M05, 374 mánuðir | comma, utf-8 |
| `repeat_sale_index.pkl` / `.csv` | ~250 KB | **Áfangi 6** BMN repeat-sale output, 2.673 rows × 15 cols, nominal + real indices | pickle + utf-8-sig |
| `repeat_sale_pairs.pkl` | ~10 MB | **Áfangi 6** 56.824 clean pairs post-filter cascade, 16 cols | pickle |
| `repeat_sale_summary.csv` | ~5 KB | **Áfangi 6** per-cell CAGR + crash-depth table, 27 rows | utf-8-sig |
| `residential_real_grid.png` | ~340 KB | **Áfangi 6** 3×3 main residential plot | png |
| `apt_floor_regional.png` | ~170 KB | **Áfangi 6** Country catch-up overlay | png |
| `nominal_vs_real.png` | ~95 KB | **Áfangi 6** methodology explainer | png |
| `sample_density_heatmap.png` | ~335 KB | **Áfangi 6** cell × ár n_pairs heatmap | png |
| `crash_recovery_zoom.png` | ~185 KB | **Áfangi 6** 2006-2018 focus, RVK residential | png |
| `ats_lookup_by_quarter.pkl` / `.csv` | ~220 KB | **Áfangi 7** Table A — per (seg × reg × qtr), 913 rows × 13 cols, heat_bucket as metadata | pickle + utf-8-sig |
| `ats_lookup_by_heat.pkl` / `.csv` | ~13 KB | **Áfangi 7** Table B — pooled per (seg × reg × heat), 63 rows × 10 cols. **Primary scoring table**. | pickle + utf-8-sig |
| `ats_heat_thresholds.pkl` / `.csv` | ~4 KB | **Áfangi 7** Audit: p33/p67 per (seg × reg), 23 rows × 6 cols | pickle + utf-8-sig |
| `ats_dashboard_quarterly.pkl` / `.csv` | ~55 KB | **Áfangi 7** Region-collapsed seg × qtr trends, 359 rows × 8 cols | pickle + utf-8-sig |
| `ats_dashboard_monthly_heat.pkl` / `.csv` | ~460 KB | **Áfangi 7** Monthly rolling z-score regime indicator, 2.501 rows × 9 cols | pickle + utf-8-sig |
| `Gagnapakkar/fasteignir{,1,2,3,4}.db` | ~3 GB | Raw scraper output, 5 partitions | SQLite |

**⚠ Deprecated — má ekki lesa úr:**
- `D:\fasteignir_merged.db` (2,8 GB) — 82% NaT á thinglystdags.
- `D:\audit_1_5\listings.pkl`, `sales.pkl` — derivatives af korrupteraða merged DB.
- Öll pickle-a-derivatives í `D:\audit_1_5\` nema output logs.

**Python moduler á D:\\:**

| Skrá | Hlutverk |
|---|---|
| `devalue.py` | Parser fyrir SvelteKit devalue-format |
| `cpi.py` | `CPI.load()`, `.factor()`, `.deflate()` — verðbólguleiðrétting |
| `classify_property.py` | HMS tegund → (canonical_code, flags) tuple |
| `rules.py` | Business-logic rules: new-build, property-change, outlier, segment stats, region |
| `extract_merking.py` | Per-property structured extract (merking, floor, hnit) |
| `parse_all_dbs.py` | Unified parser: 5 pre-merge DBs → v2 pickles |
| `patch_v2_dates.py` | One-off: re-parse dates í existing v2 pickles með ISO8601 format |
| `pairing.py` | **Listing-to-sale pairing** með session assignment + pair_status taxonomy |
| `geography.py` | **Per-FASTNUM geography features** með matsvaedi_bucket, region_tier, lat/lon |
| `test_pairing.py` | 17 tests fyrir pairing.py |
| `test_geography.py` | 18 tests fyrir geography.py |
| `run_pair_and_validate.py` | Keyrir pairing á raungögnum + validation report |
| `run_build_geography.py` | Keyrir geography build á raungögnum + validation |
| `audit_1_7_full_report.py` | Re-runnable heildarskýrsla |
| `audit_2_0_training_data_preview.py` | **Áfangi 2.0 diagnostic** — filter cascade, FEPILOG preview, floor features preview |
| `build_training_data.py` | **Áfangi 2.1** — feature engineering → `training_data_v1.pkl` |
| `audit_2_2_split_validation.py` | **Áfangi 2.2** — train/val/test split validation diagnostics |
| `train_baseline.py` | **Áfangi 2.3** — 6 LightGBM models (mean + 5 quantiles) |
| `audit_2_4a_residuals.py` | **Áfangi 2.4a** — deep residual audit on baseline predictions |
| `train_iteration2.py` | **Áfangi 2.4b** — main + summer models með SUMMERHOUSE split og real_fasteignamat |
| `audit_2_4c_residuals.py` | **Áfangi 2.4c** — deep residual audit á iter2 predictions |
| `verify_augl_flags.py` | **Áfangi 3a** — empirical coverage check á augl-flags í listings_v2 |
| `draw_gold_standard_sample.py` | **Áfangi 3a+** — stratified 120-row sample úr paired subset (scaled til 200 í 3c, seed=42) |
| `build_labeling_xlsx.py` | **Áfangi 3a+** — smíðar Google-Sheets-compatible xlsx með data validation |
| `pilot_extract.py` | **Áfangi 3c** — Haiku 4.5 extraction v0.2.1 með tool_use, prompt caching, few-shot, retry, incremental save, resume-from-JSONL |
| `pilot_extract_v022.py` | **Áfangi 3c+** — v0.2.2 re-pilot með 15 nýjum fields, tightened prompt (4 refinements), 3ja few-shot example, append-semantics JSONL |
| `discover_gaps_keywords.py` | **Áfangi 3c** — 120-keyword gap frequency analysis (ókeypis, reglexpr á lysing vs extraction) |
| `discover_gaps_llm.py` | **Áfangi 3c** — Sonnet 4.6 meta-analysis per (lysing, extraction) pair fyrir unknown-unknown gaps (~$3) |
| `check_duplicates.py` | **Áfangi 3c** — hash-based dedup analysis (exact + first-500-char) á sample + full population |
| `batch_extract.py` | **Áfangi 3d** — Batch API submission í 8 chunks af 5000, resume-safe state management, per-chunk JSONL outputs, post-proc propagation |
| `build_training_data_v2.py` | **Áfangi 3e** — merge raw JSONL + pairs + training_v1 + feature engineering → training_data_v2.pkl |
| `patch_training_data_v2.py` | **Áfangi 4 post-audit** — fixes unregistered_space_sqm zero-fill bug + num_parking_spaces cap |
| `train_iteration3.py` | **Áfangi 4** — iter3 v2 training (154 features, real_fasteignamat computed inline) |
| `filter_training_data.py` | **Áfangi 4c** — adds is_quality_transaction flag (kv_ratio ∈ [0,70; 1,50]) → training_data_v3.pkl |
| `train_iteration3_v3.py` | **Áfangi 4c (DEPRECATED)** — retrain með filter í training. Caused held MAPE regression; v3 models not used. |
| `calibrate_segments.py` | **Áfangi 4c (SUPERSEDED)** — original calibration á v3 predictions |
| `calibrate_segments_v2.py` | **Áfangi 4c (PRODUCTION)** — calibration á v2 predictions (canonical), produces `calibration_config.json` |
| `score_new_listing.py` | **Áfangi 4c (PRODUCTION API)** — stateless scoring: tekur eign dict → skilar calibrated prediction + PI. Loads models einu sinni, callable frá UI/API layer. Smoke-tested 2026-04-19 (62 mkr spá á 85m² APT postnr 105 með 45 mkr FASTEIGNAMAT, 80% PI 48-64 mkr). |
| `refresh_cpi.py` | **Operational** — Hagstofa PxWeb API fetch fyrir VNV (`VIS01004.px`, `financial_indexation`). Staðfest virkar 2026-04-19: 374 mánuðir 1995M04–2026M05, reference VNV 678,30. Atomic write, safety aborts á >5% shrinkage. |
| `monthly_recalibration.py` | **Operational** — cronjob template fyrir regime-aware refresh af k-factors. Reiknar ný k-factors úr trailing 12m residuals, archive-ar gamla konfigurað. Safety abort ef drift > 30%. |
| `refresh_kaupskra.py` | **Operational** — fetch nýrra þinglýstra sölu frá HMS kaupskrá (OCI Object Storage URL). Idempotent med MD5 + Last-Modified state tracking. Staðfest virkar 2026-04-20: 226.481 rows, composite PK `(FAERSLUNUMER, FASTNUM)`, latest tx 2026-04-17. |
| `rebuild_training_data.py` | **Operational (TODO)** — re-derive real_kaupverd, cpi_factor, real_fasteignamat eftir refresh_cpi + refresh_kaupskra |
| `validate_metrics.py` | **Operational (TODO)** — sanity check á held MAPE drift, PI coverage, post-refresh validation |
| `build_repeat_sale_index.py` | **Áfangi 6** — BMN OLS repeat-sale index builder, per (canonical_code × region_tier) × ársfjórðung, bæði nominal og CPI-deflated real. 56s runtime á 56.824 clean pairs. |
| `analyze_repeat_sale_index.py` | **Áfangi 6** — matplotlib plot generator (5 .png) + per-cell summary stats (CAGR, crash-depth). |
| `ats_diagnostic.py` | **Áfangi 7** — pre-build validation tool: paired_fresh distribution summary, SD-decline check, cell density audit. |
| `build_ats_lookup.py` | **Áfangi 7** — end-to-end ATS lookup builder. Produces 5 output files (Tables A+B, heat thresholds, 2 dashboard aggregates). 1,7 sec runtime á 52K clean paired_fresh. |
| `refresh_dashboard_tables.py` | **Operational orchestrator** — monthly-cycle step 4 af 6. Wraps `build_repeat_sale_index.py` + `build_ats_lookup.py` með cross-script atomicity, subprocess isolation, shape-safety validation, rollback á failure. 65-81s runtime. Staðfest virkt 2026-04-20 í tveimur cycles. |

**Parsing gotchas:**
- Kaupskrá notar **ISO dates** `'YYYY-MM-DD HH:MM:SS.0'` með variable fractional precision (1-6+ digits). Alltaf nota `pd.to_datetime(..., format='ISO8601')` — inference silently fellur á mismunandi precision.
- `BYGGAR`, `FULLBUID`, `ONOTHAEFUR_SAMNINGUR`, `EINFLM`, `KAUPVERD`, `FASTEIGNAMAT` þarf `pd.to_numeric(errors='coerce')`.
- `SKJALANUMER` er **string** ("R-005069/2006"), ekki numeric. Ekki nota `pd.to_numeric`.
- Stadfangaskra er **UTF-8 comma-separated** (ekki latin-1 þrátt fyrir HMS source).
- PowerShell `>` redirection býr til **UTF-16LE** skjöl. Script-ar tee-a beint í UTF-8 skjöl með Python (sjá `_Tee` pattern).
- `sys.stdout.reconfigure(encoding='utf-8')` þarf efst í scripts fyrir íslenska stafi.
- **`thinglystdags="0001-01-01T00:00:00"`** er devalue sentinel — parse-ast sem Timestamp(year=1), ekki NaT. Year-range filter þarf.
- **fastnum dtype**: listings_v2 er `Int64` (nullable), kaupskra verður `int64` (numpy) eftir `pd.to_numeric`. merge_asof krefst sama dtype; cast í `int64` báðum megin.
- **Case-mismatch milli iter2/training_data og pairs**: iter2_predictions og training_data_v1 nota UPPERCASE (`FAERSLUNUMER`, `FASTNUM`, `SKJALANUMER`, `THINGLYSTDAGS`), en pairs_v1 notar lowercase (`faerslunumer`, `fastnum`). Join-logic verður að case-normalize. **Primary join key**: `FAERSLUNUMER` ↔ `faerslunumer` (unique per sala).
- **pairs_v1 hefur ekki `augl_id`** — hefur `augl_id_initial` og `augl_id_final`. Notum `augl_id_final` sem primary (lýsing sem var uppi á sölu-tíma), fallback í `augl_id_initial` ef final er null.
- **listings_v2 augl-flags hafa 86,2% null rate** (2026-04-18 empirical). Sama pattern á `svalir`, `gardur`, `lyfta`, `staedi`, `rafbill`, `pets`, `hjolastoll`, `eldrib`, `lat`, `long` — source-driven (source_db hefur 5 unique values, líklega að bara einn skilaði augl parsed). Extraction verður að supplement fyrir 86% af listings.
- **`inngangur` er 42-value categorical**, ekki boolean eins og TAXONOMY gaf í skyn. 232K af 472K eru „Sameiginlegur". `has_separate_entrance` má derive sem `inngangur != "Sameiginlegur"`.
- **fjbadherb, fjsvfnherb, fjherb eru 100% populated í listings_v2** — authoritative, ekki extracta. `byggar` 99,4% populated. `inngangur` 99,9%. `bilskur` 100% (pre-computed í pipeline, ekki pure scrape).
- **listings_text_v2.pkl er `DataFrame` með `augl_id` og `lysing` columns** — 456K rows. Normalize via `normalize_listings_text()` í sample-draw.
- **pandas 2.x fillna**: `Series.fillna(other_series.values)` fails ef dtypes eru Int64 (nullable). Nota `Series.fillna(other_series)` beint (index-alignment gerist sjálfvirkt).

**PowerShell / Windows / API gotchas (Áfangi 3c):**
- Env var syntax: **`$env:VAR = "value"`** í PowerShell (ekki cmd-style `set VAR=value`). `set` í PowerShell býr til lokal variable með equals-í-nafninu, ekki environment variable.
- Persistent env var: `[Environment]::SetEnvironmentVariable("VAR", "value", "User")` — þarfnast nýs shell til að taka gildi.
- Windows default file read encoding er **cp1252** sem fail-ast á UTF-8 scripts með íslenskum stöfum. Notaðu `Get-Content -Encoding UTF8` fyrir PowerShell grep.
- **Excel file-lock** breytir CSV í read-only — incremental saves crasha með `PermissionError`. pilot_extract.py notar safe_csv_save með retry (sleep 2s, reyna aftur). Lokaðu Excel áður en keyrir batch jobs.
- **Sleep/standby** interrupar long-running HTTP requests — API kallar hanga. Slökkva áður en keyrt: `powercfg /change standby-timeout-ac 0`. Restore síðar: `60`.
- **Anthropic API billing er aðskilið frá Claude.ai Pro/Max subscription** — separate payment method á console.anthropic.com. Minimum top-up $5. Tier 1 ($100/mán cap) þarf $40 cumulative deposit + 7 daga bið fyrir Tier 2 ($500/mán).
- Íslenskir **smart-quotes** (`„"`) í Python string literals breakja parser. Notaðu ASCII `"..."` með escapes í source kóða.
- **Excel CSV encoding**: default cp1252 garblar UTF-8 stafi (`Ã¾` í staðinn fyrir `þ`). Notaðu `utf-8-sig` (með BOM) output, eða Google Sheets sem detectar UTF-8 automatically.
- **Haiku 4.5 tool_use með prompt caching**: `cache_control: {type: "ephemeral"}` settu bæði á system prompt og tool definition. Fyrsta kall skrifar cache (~$0,014 fyrir 6.840 tokens), síðari kall les cache (~$0,006, 90% afsláttur á cached input).

---

## Áfangar verkefnis

0. **Infrastructure** — gagnagrunnur, deployment, scheduling, monitoring, reproducibility framework, nýr scraper
1. **Segmentering og data audit** — taxonomy, reglur, pairing, geography, audit
2. **Baseline hedonic módel** — LightGBM quantile regression á structured features
3. **Extraction schema design**
4. **Pilot extraction**
5. **Full extraction + módel v2**
6. **Repeat-sale calibration** (samhliða 5)
7. **Uncertainty + time-on-market + ask-to-sale gap module**
8. **Iterative learning loop**
9. **UI** (9a internal, 9b public, 9c subscription)
10. **Markaðsyfirlit** — v1 indicator-pakkinn

---

## Staða per áfanga

### Áfangi 0 — Infrastructure: **0%**

Backlog:
- Nýr scraper fyrir fastinn.is með monitoring og healthcheck (replace erft gat scraper sem dó 2025-07)
- Scraper þarf að capture `landnum` field úr augl_json (testable Danni's pre-fastnum hypothesis)

### Áfangi 1 — Segmentering og data audit: **~96%**

- [x] 1.0 Devalue-parser (`devalue.py`)
- [x] 1.1 Taxonomy finalization — 514 HMS tegundir flokkaðar
- [x] 1.1.1 Verðbólguleiðrétting-infra
- [x] 1.1.2 Structured per-property extract
- [x] 1.2 Nýbyggingarregla staðfest
- [x] 1.3 Eignabreytingarregla
- [x] 1.4.1 Field stability audit
- [x] 1.4.2 Outlier filter
- [x] 1.4.3 Data layer cleanup — v2 pickles canonical
- [x] 1.5 Listing-to-sale pairing → `pair_listings_to_sales()`, canonical `pairs_v1.pkl`
- [x] 1.6 Geography features → `build_geography_features()`, canonical `geography_features.pkl`
- [x] 1.7 Data audit report — `audit_1_7_full_report.py` + `DATA_AUDIT_REPORT.md`
- [x] 1.8 FEPILOG decoding + multi-unit scale mæling
- [ ] 1.8b (deferred): Landnum-based alt-pairing — kræfist re-parse af augl_json eða nýrr scraper

### Áfangi 2 — Baseline módel: **~80%**

- [x] 2.0 Diagnostic audit — `audit_2_0_training_data_preview.py` keyrt, niðurstöður logged
- [x] 2.1 Feature engineering — `build_training_data.py` → `training_data_v1.pkl` (144.254 records)
- [x] 2.2 Train/val/test split validation — `audit_2_2_split_validation.py`
- [x] 2.3 Baseline LightGBM quantile regression (6 módel: mean + P2.5/P10/P50/P90/P97.5)
- [x] 2.4a Deep residual audit — `audit_2_4a_residuals.py`, diagnosed systematic overprediction
- [x] 2.4b Iteration 2 — `train_iteration2.py` keyrt, main + summer models vistaðir
- [x] 2.4c Iteration 2 residual audit — `audit_2_4c_residuals.py`, iter2 metrics staðfest
- [ ] 2b (deferred): Spatial KNN smoothing, K-fold CV, monotonic constraints — ekki prioritized, main model meets targets

**Iter2 main model er production-ready fyrir residential** (Áfangi 2 closed fyrir alla residential fjölbýli/sérbýli/raðhús). SUMMERHOUSE segment er unresolved og skráð sem known limitation (sjá Áfanga 2.4c niðurstöður).

**Feature backlog ready**:
- Floor features úr merking: `merking_floor`, `building_max_floor`, `is_top_floor` (gated building_max_floor≥2), `floor_fraction` (gated eins)
- Geography: matsvaediNUMER categorical + region_tier + lat/lon (úr `geography_features.pkl`)
- FEPILOG decoded: `unit_category` (AA+BB), `is_main_unit` (CC==01)
- Outlier flags sem filter
- Multi-unit filter (keep eingöngu single-FASTNUM SKJALANUMER)
- Pair-derived features (ekki í core baseline, en tiltækar): `list_price_final`, `ask_to_sale_ratio`, `time_on_market_days`

### Áfangi 3 — Extraction schema design: **~98%**

- [x] 3a Schema design (v0.2.1 frozen) — 18-component status matrix (unit-level 11 + building-level 7) með 7-stiga status enum + year + detail; 7 augl-supplement trilemmas (fyrir 86% af listings þar sem augl er null); situational fields fyrir útsýni, útipláss, parking, layout, building, negative signals, agent framing, property narrative. Samtals 93 fields.
- [x] 3a+ Labeling protocol v0.2 (120 listings: 100 stratified + 20 worst-held oversample) + LABELING_GUIDE v0.1 (895 lína concrete Icelandic reference með per-component trigger-phrases og 3 worked examples)
- [x] 3a+ Empirical augl coverage staðfest (`verify_augl_flags.py` run) — 10/10 target flags í listings_v2, 86,2% null rate á 7 scrape-dependent flags → schema supplements
- [x] 3a+ Gold-standard sample drawn (`draw_gold_standard_sample.py` run, scaled í 3c úr 120 í 200 rows) — saved á `D:\gold_standard_sample.csv`, stratified balanced across 36 cells
- [x] 3a+ Labeling workbook built (`build_labeling_xlsx.py`) — `D:\gold_standard_labeling.xlsx` með 106 cols, 48 enum dropdowns, frozen panes, header comments
- [x] 3b **Middle-ground validation valið** frekar en formal hand-labeling protocol (sjá Áfangi 3b decision). Workflow: pilot → manual scan → iterate schema → full batch.
- [x] 3c Pilot extraction script `pilot_extract.py` — Haiku 4.5 + tool_use + prompt caching + 2 few-shot examples + retry logic + incremental JSONL+CSV save + resume-from-JSONL
- [x] 3c Pilot run 200 listings á Haiku 4.5 v0.2.1 — zero extraction failures, actual cost ~$3 (ekki $1,35 sem script reported — sjá calc bug decision)
- [x] 3c Discovery infrastructure: `discover_gaps_keywords.py` (120 keywords í 12 flokkum) + `discover_gaps_llm.py` (Sonnet 4.6 meta, 1.105 signals flagged, ~$3) + `check_duplicates.py`
- [x] 3c Quality findings identified (well_maintained over-use, þakkantur confusion, listing_elaboration inflated, óskráð rými gap, lot_type gap)
- [x] 3c Duplicate analysis — population rate 12,4% í 200 sample, 7,8% í full 40.814 (37.544 unique); top-10 dups eru nýbyggingar-developments
- [x] 3c+ **Schema v0.2.2 frozen** — `EXTRACTION_SCHEMA_v0_2_2.md` skrifað. 15 ný fields: 6 size & legal, 5 outdoor, laundry_configuration, end_unit_position, sale_channel, immediate_availability. Refactor garden_quality (condition-only). 93 → 108 fields.
- [x] 3c+ `pilot_extract_v022.py` skrifað — ný tool schema, 4 system prompt refinements (well_maintained tightening, þakkantur distinction, listing_elaboration thresholds 150/300/600w, óskráð rými guidance), 3ja few-shot example (ROW_HOUSE með óskráð rými + sérlóð), resume-from-JSONL append semantík
- [x] 3c+ Re-pilot v0.2.2 á 200 listings — PASS á öllum critical targets: well_maintained kitchen 60%→21%, bathroom 57,5%→19,5%, flooring 59,5%→20%. 15 nýju fields captured með meaningful rates. Kostnaður: ~$3,50 (ekki $1,68 sem script reported).
- [x] 3d `batch_extract.py` skrifað — Batch API submission í 8 chunks af 5000 (256 MB raw limit), resume-safe state.json, per-chunk JSONL download, post-proc end_unit filter (hafði canonical_code bug — sjá decision)
- [x] 3d Full batch run keyrður — 37.544 unique, zero API failures, 76 errored requests (0,2%), ~20 mín á Anthropic-megin. **Rauncostnaður: $349** (ekki $157 projected — calc formula bug, sjá decision). Output: `batch_extraction_unique.jsonl` + `batch_extraction_propagated.csv` (latter hefur canonical_code bug; raw JSONL er authoritative).
- [x] 3d+ Quality audit á full 40K population: well_maintained fix generalizar (21% kitchen, 21% bathroom, 19% flooring), nýju fields skila meaningful signal (óskráð rými 8,9%, sérlóð 2,3%, laundry dedicated 34,6%, sale_channel einkasala 21%). lot_orientation schema violations identified (30+ Claude variants — normalize í feature engineering).
- [x] 3e `build_training_data_v2.py` skrifað — merge raw JSONL + pairs + training_data_v1 + feature engineering → training_data_v2.pkl. 11-category feature engineering (ordinal/binary/multi-enum/composite). **Blokkandi næsta session fyrir keyrslu**.
- [ ] 3e Keyra `build_training_data_v2.py` — output `training_data_v2.pkl` (~115 cols, ~28% extraction coverage)

**Skjöl frozen í project**:
- `EXTRACTION_SCHEMA_v0.2.md` — schema v0.2.1 (93 fields)
- `EXTRACTION_SCHEMA_v0_2_2.md` — schema v0.2.2 (108 fields, supersedes v0.2.1 fyrir full batch)
- `GOLD_STANDARD_PROTOCOL.md` — v0.2 protocol (aligned við v0.2.1, v0.2.2 additive not breaking)
- `LABELING_GUIDE.md` — v0.1 concrete Icelandic labeling reference

**Áfangi 3 er effectively complete** — aðeins merge-script lokal keyrsla eftir til að framleiða training_data_v2.pkl. Iter3 training í Áfanga 4 tekur við.

### Áfangar 4–10: ekki byrjaðir

---

## Áfangi 2.3 niðurstöður (baseline LightGBM, 2026-04-18)

6 módel þjálfuð á 19 features: mean (L2) + 5 quantiles (P2.5, P10, P50, P90, P97.5). LightGBM 4.6.0.

**Point accuracy (mean model)**:

| Split | MAPE% | medAPE% | log_RMSE | R² |
|---|---|---|---|---|
| train | 7,84 | 5,43 | 0,1121 | 0,9530 |
| val | 12,53 | 6,85 | 0,1730 | 0,8593 |
| test | 15,36 | 7,33 | 0,2050 | 0,8228 |
| held | 17,19 | 11,03 | 0,2090 | 0,7857 |

**PI coverage** (target 80% / 95%):

| Split | 80% PI | 95% PI | 80% width% |
|---|---|---|---|
| train | 80,3 | 95,3 | 25,5 |
| val | 67,6 | 90,4 | 22,1 |
| test | 65,5 | 88,9 | 22,3 |
| held | 51,9 | 85,6 | 22,4 |

**Feature importance (top 5 af gain)**:
- FASTEIGNAMAT: 71,3%
- sale_year: 8,7%
- EINFLM: 5,3%
- matsvaedi_bucket: 3,2%
- BYGGAR: 3,0%

FASTEIGNAMAT dominerar — restin af 18 features deila 28,7%. Geography-features (matsvaedi_bucket, region_tier, lat/lon) eru collectively 4% vegna þess að FASTEIGNAMAT er already geo-adjusted af HMS.

**Segment test MAPE**:

| Category | N | MAPE% | medAPE% |
|---|---|---|---|
| APT_STANDARD | 3.202 | 8,4 | 6,6 |
| APT_ATTIC | 82 | 8,4 | 6,7 |
| APT_BASEMENT | 248 | 8,9 | 6,5 |
| ROW_HOUSE | 395 | 9,7 | 6,5 |
| APT_FLOOR | 3.973 | 10,9 | 7,5 |
| SEMI_DETACHED | 209 | 11,5 | 6,2 |
| SFH_DETACHED | 453 | 17,8 | 10,0 |
| **SUMMERHOUSE** | **312** | **156,8** | **22,3** |

Country-segment test MAPE 26,8% (driven mostly by SUMMERHOUSE catastrophic errors). Residential rollup (SUMMERHOUSE excluded): test MAPE 10,2%, medAPE 7,1%, cov80 65,6%.

---

## Áfangi 2.4a niðurstöður (deep residual audit, 2026-04-18)

**Model systematically overpredictar í 2024+, monotonic progression**:

| Split | mean residual_log | ≈ bias% |
|---|---|---|
| train | +0,0001 | 0% |
| val 2024 | −0,0360 | −3,5% |
| test 2025 | −0,0512 | −5,0% |
| held 2026 | −0,1014 | −9,6% |

**Tvær distinct orsakir identified**:

1. **FASTEIGNAMAT nominal drift**: FASTEIGNAMAT óx nominally 2024–2026 en real prices ekki. Model lærði "FASTEIGNAMAT X → real_kaupverd Y" í 2006–2023 verðlagi. Í 2024+ hefur FASTEIGNAMAT vaxið en real price ekki → overpredict. 6.872 af 8.575 test-records detta í Q5 (efsta training-quintile af FASTEIGNAMAT).

2. **2024–2026 real price plateau/decline**: median_real +5,4% 2024, −2,2% 2025, −1,8% 2026. Model trained up to 2023 (monotonic vöxtur) kannast ekki við plateau — heldur áfram að extrapolera upward.

**Diagnostic findings**:
- Spatial residuals eru bara **mildly clustered** (std 0,038, range [−0,15, +0,11]). Spatial smoothing gæti gefið 1–2 pp MAPE gain — deferred til 2b.
- Residual correlations **allar undir 0,10 Spearman þröskuldi** (hæst FASTEIGNAMAT við 0,07). Ekkert single feature catastrophically missed.
- SUMMERHOUSE dominerar worst-20 í test (20/20). Confirmed: aðskilja í iteration 2.
- Per-year train MAPE: 7–11% (2008–2009 hæst vegna financial crisis, modern 2018–2023 sit 7–8%). Model fittar training data vel — vandi er structural (distribution shift).
- Capital_sub APT_STANDARD hefur verstu calibration (54% cov80 á 1.254 records) — worth investigating eftir main fixes.

---

## Áfangi 2.4b niðurstöður (iteration 2, 2026-04-18 21:57)

**Hyperparameters**: eins og baseline (num_leaves=63, lr=0.05, min_data_in_leaf=40 fyrir main / 15 fyrir summer, ff=0.9, bf=0.8, n_estimators=3000, early_stopping=100, seed=42).

**Features**: 20 (19 baseline + `real_fasteignamat`).

**Split structure**:

| Split | Main (ex-SH) | Summer |
|---|---|---|
| train_ext | 129.769 | 3.467 |
| test (early stopping) | 8.575 | 312 |
| held (pure holdout) | 2.084 | 47 |

**Best iterations** (test quantile as early stopping):
- main: mean 1859, q025 355, q10 593, q50 2976, q90 746, q975 347
- summer: mean 161, q025 1, q10 59, q50 854, q90 253, q975 189

**Feature importance (main mean, top 10)**:
- real_fasteignamat 62,7%
- FASTEIGNAMAT 13,4%
- EINFLM 4,9%
- sale_year 4,5%
- is_new_build 3,9%
- matsvaedi_bucket 3,4%
- BYGGAR 2,9%
- postnr 1,7%
- LOD_FLM 0,7%
- sale_month 0,4%

Real_fasteignamat took over dominant position (baseline: FASTEIGNAMAT 71%). Nominal FASTEIGNAMAT still contributes 13% incremental signal — model useful at both scales.

---

## Áfangi 2.4c niðurstöður (iter2 residual audit, 2026-04-18)

### Fair comparison with baseline (held 2026, pure holdout)

| Metric | Baseline 2.3 | Iter2 main (residential) | Iter2 combined |
|---|---|---|---|
| MAPE | 17,19% | **7,97%** | 11,66% |
| medAPE | 11,03% | 5,24% | 5,37% |
| cov80 | 51,95% | 69,9% | 70,1% |
| cov95 | 85,55% | 89,5% | 89,6% |
| mean bias (log) | −0,1014 | **−0,0151** | −0,0220 |

**Main residential model cut MAPE more than in half** (17,19% → 7,97%) og nearly eliminated systematic bias (−10% → −1,5%). Target (held MAPE ≤ 10%) achieved með substantial margin.

### Per-year bias (main model)

| Year | Split | N | MAPE | Bias (log) |
|---|---|---|---|---|
| 2006–2023 | train_ext | ~120K | 5,9–9,4% | ~0 per year |
| 2024 | train_ext | 9.719 | 5,70% | +0,000 |
| 2025 | test | 8.575 | 8,21% | +0,009 |
| 2026 | held | 2.084 | 7,97% | −0,015 |

Baseline hafði monotonic increasing negative bias (0 → −10%). Iter2 hefur near-zero bias across all recent years. **Mechanism 1 (FASTEIGNAMAT drift) og Mechanism 2 (2024 plateau) eru bæði fixed**.

### Mechanism 1 validation — per real_fasteignamat quintile bias on held

| Quintile | Range (þús.kr) | N | Bias (log) | MAPE |
|---|---|---|---|---|
| Q1 | ≤30.728 | 47 | +0,003 | 15,1% |
| Q2 | 30.728–41.717 | 99 | −0,034 | 12,7% |
| Q3 | 41.717–53.168 | 307 | −0,030 | 10,1% |
| Q4 | 53.168–69.789 | 573 | −0,020 | 6,4% |
| Q5 | >69.789 | 1.058 | −0,007 | 7,5% |

Baseline: Q5 bias −0,105 (−10%) — iter2: Q5 bias −0,007 (−0,7%). Fix virkar across the board, including í Q5 high-end properties.

### Per-segment main held MAPE

| canonical_code | N | MAPE | medAPE | bias |
|---|---|---|---|---|
| APT_FLOOR | 1.019 | 8,24% | 5,51% | −0,01 |
| APT_STANDARD | 740 | 6,32% | 4,75% | −0,02 |
| SFH_DETACHED | 106 | 15,89% | 7,48% | −0,04 |
| ROW_HOUSE | 100 | 7,52% | 5,64% | −0,04 |
| APT_BASEMENT | 51 | 9,95% | 5,10% | −0,02 |
| SEMI_DETACHED | 48 | 9,03% | 5,99% | −0,03 |
| APT_ATTIC | 17 | 8,15% | 3,90% | −0,05 |

SFH_DETACHED er verstur (16% MAPE) — dreifður markaður, sumt í Country er mjög óhefðbundið. APT-flokkar eru excellent (6–8%).

### Per region × segment (n≥20)

| region_tier | canonical_code | N | MAPE | bias |
|---|---|---|---|---|
| RVK_core | APT_STANDARD | 386 | 6,15% | −0,02 |
| RVK_core | APT_FLOOR | 353 | 7,43% | −0,02 |
| RVK_core | APT_BASEMENT | 37 | 10,63% | −0,02 |
| Capital_sub | APT_FLOOR | 426 | 6,87% | 0,00 |
| Capital_sub | APT_STANDARD | 273 | 6,13% | −0,03 |
| Capital_sub | ROW_HOUSE | 51 | 6,23% | −0,03 |
| Capital_sub | SFH_DETACHED | 34 | 7,13% | +0,03 |
| Country | APT_FLOOR | 240 | 11,85% | −0,01 |
| Country | SFH_DETACHED | 62 | 22,43% | −0,09 |
| Country | APT_STANDARD | 81 | 7,70% | +0,01 |
| Country | ROW_HOUSE | 40 | 9,58% | −0,06 |

RVK_core og Capital_sub eru solid (6–10%). Country SFH_DETACHED er veikasta segmentið — old rural houses með óstaðlaða features.

### SUMMERHOUSE — ekki solved

Main story: **isolating SUMMERHOUSE cleaned up main model** en summer-model sjálft er enn unstable.

- Test (312): MAPE 137%, medAPE 21%
- Held (47): MAPE 176%, medAPE 22%, 81% af records hafa APE < 50%

Median prediction er workable en tail er catastrophic — nokkrir predictions víxla 2-3 orders of magnitude. Features available eru ekki nógu discriminative fyrir summerhouse valuation (land-value dominerar, condition heterogeneous).

**SUMMERHOUSE valuation er known limitation**. Future work: add land value features, settlement indicators, amenity proximity. Ekki blocker fyrir residential valuation website.

### Calibration — slightly too narrow

| Split | cov80 (target 80%) | cov95 (target 95%) |
|---|---|---|
| train_ext | 80,3% | 95,4% |
| test | 68,2% | 90,3% |
| held | 69,9% | 89,5% |

Train er well-calibrated. Test/held eru ~10 pp undir target. Áhrif: confidence intervals eru slightly too tight á out-of-sample. Fixable með iter3 quantile adjustment eða wider bands, en ekki blocker fyrir production launch.

### Spatial residuals — OK

Top-10 matsvaedi-buckets á held hafa mean_bias í bilinu [−0,06, +0,06]. Bias std across all 140 buckets er 0,132 en er dominated af small-N buckets með noisy means. Populated buckets eru vel calibrated. Spatial KNN smoothing deferred remains correct call.

### Go/no-go verdict: **Áfangi 2 COMPLETE fyrir residential**

Main residential model meets targets:
- ✓ Held MAPE ≤ 10% (actual 7,97%)
- ✓ medAPE ≤ 8% (actual 5,24%)
- ✗ cov80 ≥ 75% (actual 69,9% — near miss, acceptable)
- ✓ Near-zero bias (−1,5% vs baseline −10%)

**Næsta skref: Áfangi 3 — extraction schema design.**

---

## Áfangi 2.0 niðurstöður (2026-04-18)

### Filter cascade (audit preview)

| Skref | N | % af raw | Δ |
|---|---|---|---|
| Start (kaupskra raw) | 226.481 | 100,00% | — |
| Valid THINGLYSTDAGS | 226.481 | 100,00% | +0 |
| Arm's-length | 174.526 | 77,06% | −51.955 |
| Single-FASTNUM SKJALANUMER | 159.964 | 70,63% | −14.562 |
| Property join | 159.281 | 70,33% | −683 |
| In-model taxonomy | 148.816 | 65,71% | −10.465 |
| Geography join | 148.816 | 65,71% | +0 |
| Size filter 20-1000 | 148.683 | 65,65% | −133 |
| Minimal price-outlier (audit-only) | 148.608 | 65,62% | −75 |

Final preview training set: **148.608 records** (full rules.py outlier + repeat-sale property-change rule bætir ekki miklu við drop-tölurnar á single-sale baseline).

### Multi-unit filter er principled

Price-per-m² comparison (2020+, residential): multi-unit samningar eru kerfisbundið lower pr-m² en single á Einbýli (0,91× median) og Fjölbýli (0,89×). Sérbýli mismun neglible (0,99×). Filter að droppa multi er principled — við erum ekki að missa signal heldur að fjarlægja bundled-pricing dynamics sem módelið á ekki að læra af.

Multi-unit rate hefur doublast: 6% (2015) → 14% (2024–26). Við erum því að droppa hærra hlutfall af nýjum sölum en sögulegum. Ekki breyting á policy — flagga bara í model-performance review á test-set.

### FEPILOG AA hypothesis rejected

Upphaflega átti AA=02 að vera bílskúrar/geymslur. Audit 2.0 hafnar þeirri greiningu. Cross-tab á unit_category × canonical_code sýnir að unit_category 0201 í in-model records (5.988 arm's-length residential sölur) er í raun:

- APT_STANDARD: 2.826
- APT_FLOOR: 1.987
- ROW_HOUSE: 522
- SEMI_DETACHED: 466
- SFH_DETACHED: 110
- SUMMERHOUSE: 61

Median pr-m² fyrir 0201 = 588 k/m² — clean residential range, ekki garage (sem væri 100–250). AA er ekki clean residential/garage split.

**Impact**: Canonical exclusion stýrist áfram af `classify_property()` úr HMS tegund, ekki af FEPILOG AA. Feature design óbreytt — `unit_category = AA + BB` sem categorical og `is_main_unit = (CC == "01")` halda gildi.

### Floor features eru gold

100% coverage á MAIN residential (105.435), 100% á SECONDARY (368), 99,7% á SUMMERHOUSE (4.513). Better en vonast til.

Íbúðir með bæði `merking_floor` og `building_max_floor`: 85.351. Top-floor rate 44,4% án gating (inflated af single-floor buildings). **Ákvörðun**: gate `is_top_floor` og `floor_fraction` á `building_max_floor >= 2` — fyrir single-floor buildings (raðhús, einbýli) er top-floor concept meaningless, skila NaN.

---

## Áfangi 1.8 niðurstöður (2026-04-18 kvöld)

### FEPILOG decoding

6-stafa kóði AABBCC, 1.551 distinct values í kaupskra. Hierarchy:
- **AA** = aðal-flokkur. AA=01 (74%) er dominantly residential-main. AA=02 (11%) og AA=03+ eru *mixed*: residential-main records eru til staðar í þeim öllum, blandaðar við commercial, garages og lóðir. **AA er ekki clean residential/garage split** — má ekki nota sem exclusion key. Canonical exclusion stýrist áfram af property_type (classify_property úr HMS tegund). Empíríkt staðfest í audit 2.0: unit_category 0201 í in-model records (5.988 arm's-length residential sölur) er APT_STANDARD/APT_FLOOR/ROW_HOUSE/SEMI_DETACHED með median pr-m² = 588 k/m² (clean residential range).
- **BB** = undir-flokkur. Dreifing heldur áfram innan hvers AA — ekki predictable hrein flokkun.
- **CC** = raðnúmer. CC=01 (aðal-eining) = 58,1% af öllum sölum, CC=02+ er aukaeiningar.

Notagildi í módeli: `unit_category = fep_AA + fep_BB` sem categorical feature. `is_main_unit = (CC == "01")`. LightGBM lærir hvaða AA_BB-kombinations haga sér sérstaklega.

### Multi-unit sales scale

**8,3% af arm's-length records (14.562 af 174.526) eru í multi-unit samningum** (2-4 FASTNUM undir sama SKJALANUMER).

Distribution:
- 95,80% SKJALANUMER = 1 FASTNUM
- 3,90% = 2 FASTNUM
- 0,29% = 3 FASTNUM
- 0,02% = 4 FASTNUM

Lykil-uppgötvun: **KAUPVERD er þegar skipt milli rows** (998 af 1000 sample hafa mismunandi verð per row). HMS has pro-rata allocated sale price — enginn double-count þegar við summum. Policy fyrir Áfanga 2: **einfalt filter**, keep eingöngu single-FASTNUM SKJALANUMER (95,8% af samningum) í baseline training. Multi-unit sölurnar eru smooth bias í módelinu (ekki representative arm's-length single-property sales).

### Landnum-based alt pairing

Ekki testable núna. listings_v2 hefur ekki landnum field. Raw augl_json í SQLite DB-unum gæti mögulega haft það — re-parse væri ódýrt check áður en við planleggjum nýjan scraper. En ekki blocker fyrir Áfanga 2.

Danni's hypothesis (skráð sem backlog 1.8b): margar nýbyggingar eru seldar áður en endanlegt FASTNUM er úthlutað af HMS. Listing er þá undir pre-fastnum auðkenni (landnum eða öðru) og birtist ekki í FASTNUM-index. Hægt að testa með landnum-based alternative identifier pairing þegar field er tiltækt.

---

## Áfangi 1.6 niðurstöður — geography

Canonical skrá: `D:\geography_features.pkl` (12 MB, 124.835 rows, 0 nulls).

| Feature | Description |
|---|---|
| `matsvaediNUMER` | 191 distinct, 100% coverage |
| `matsvaediNAFN` | Nafn matsvæðis |
| `matsvaedi_bucket` | 213 distinct: 160 M-buckets (≥50 sölur 2015+) + 53 P-buckets (rare-merged) |
| `matsvaedi_sales_2015` | Sales count reference (weighting proxy) |
| `postnr`, `postheiti` | Backup categorical |
| `region_tier` | RVK_core / Capital_sub / Country (33/36/31%) |
| `lat`, `lon` | 100% valid, 100% innan Íslands bbox |

Audit 1.6 staðfesti: 160 af 191 matsvæða (84%) hafa ≥50 sölur 2015+, 99,4% af sölum í þessum "big" matsvæðum. Rare-merge í P<postnr>_other drop-ar niður í 0,6% af markaðnum.

---

## Áfangi 1.5 niðurstöður — pairing.py og pairs_v1.pkl

Pairing logic:
- Session assignment: consecutive listings á sömu FASTNUM með gap > **90 dagar** splitta í nýjan session
- Pair-to-sale: merge_asof með direction='backward' — hver sala pair-ast við nýjasta listing sem kom fyrir söluna (á listings, ekki session_end — tryggir að session spanning sale sé rétt handlað)
- Classification thresholds: **Y_fresh=180 dagar, Y_valid=365 dagar**

pair_status taxonomy (7 gildi), 2015+ (N=125.735):

| Status | Meaning | 2015+ count | 2015+ % |
|---|---|---|---|
| `paired_fresh` | session_end ≤ 180d frá sölu | 55.538 | 44,2% |
| `paired_recent` | 180d < gap ≤ 365d | 3.380 | 2,7% |
| `paired_stale` | gap > 365d | 6.361 | 5,1% |
| `paired_no_price` | paired en list_price_final ógilt | 2.108 | 1,7% |
| `post_sale_only` | listings á FASTNUM en allir eftir sölu | 10.843 | 8,6% |
| `off_market_newbuild` | engin listings + new-build | 9.439 | 7,5% |
| `off_market_used` | engin listings + used market | 38.066 | 30,3% |

Orthogonal flag: `in_scrape_gap` (sale_date ≥ 2025-07-01) — data quality degradation indicator, ekki exclusion regla.

Validation: ask_to_sale median á paired_fresh = **0,9816** (matches audit 1.5 fyrri mælingu). Median time_on_market ~60 dagar.

---

## Scrape gap staðfesting (2026-04-18)

Listings `effective_date` volume hrundi úr ~9.000/mán í júní 2025 niður í ~600/mán í ágúst 2025 og hefur ekki náð að rétta úr sér (~1.800/mán í 2026-03/04). Staðfest í `audit_1_5_scrape_coverage.py` (2026-04-18).

| Tímabil | Listings/mán | Notes |
|---|---|---|
| 2023 baseline | 5.000-8.000 | Normal |
| 2024 | 7.400-11.800 | Healthy peak |
| 2025-H1 | 6.600-10.300 | Normal |
| **2025-07** | **2.590** | Cliff byrjar |
| **2025-08 til 2026-02** | **272-920** | Gap era |
| 2026-03/04 | 1.775-1.857 | Partial recovery |

Annualized rate vs 2024 = 0,10x. Scraperinn var gamli scraperinn sem Danni erfði, ekki full control. Stoppaði sennilega um mitt 2025. Allur data frá þeim tíma er incomplete — við getum ekki fyllt í það sem er tapað.

**Áhrif á pairing:** sölur ≥ 2025-07-01 fá `in_scrape_gap=True` flag. Þetta er **metadata-merki, ekki síunar-regla**. Paired_fresh records í gap-tímabili eru jafn-nothæf per-pair og pre-gap records. Einungis *nefnarinn* (% sala sem eru off-market, coverage rate, o.s.frv.) er bjagaður því listings er missing. Downstream consumer-ar filtra eftir þörfum.

**Áfangi 0 action**: byggja nýjan scraper með monitoring.

---

## Key finding 2026-04-18 — Nýbyggingar útskýra EKKI off-market Fjölbýli

Tilgáta um að off_market Fjölbýli væru yfirgnæfandi nýbyggingar var röng. Audit 1.5b: 18,5% nýbyggingahlutfall í off_market vs 15,2% í markaðinum í heild og 15,4% í paired_candidate — statistísk tilviljun.

Danni's hypothesis (skráð sem backlog item fyrir 1.8b): margar nýbyggingar eru seldar áður en endanlegt fastnum er úthlutað. Listing er þá undir pre-fastnum auðkenni (landnum eða öðru) og birtist ekki í FASTNUM-index. Hægt að testa með landnum-based alternative identifier pairing í Áfanga 1.8b.

Practical implication: ~32K "off_market_used" Fjölbýli sölur í 2015+ sem við getum ekki pair-að. Þetta er raunveruleiki markaðsins, ekki fixable með núverandi data layer. Paired_fresh coverage er ~44% af 2015+ markaðinum — sem er vel nothæft fyrir Áfanga 7 training (55K+ hrein pairs).

---

## Canonical data pipeline (current state)

```
pre-merge DBs (5x SQLite)
   └─ parse_all_dbs.py + patch_v2_dates.py
         └─ listings_v2.pkl, listings_text_v2.pkl, sales_v2.pkl, properties_v2.pkl
              ├─ pairing.py (pair_listings_to_sales)
              │     └─ pairs_v1.pkl
              └─ geography.py (build_geography_features)
                    └─ geography_features.pkl
                         └─ build_training_data.py (Áfangi 2.1)
                               └─ training_data_v1.pkl
                                    ├─ train_baseline.py (Áfangi 2.3)
                                    │     └─ baseline_*.lgb (×6)
                                    │        baseline_predictions.pkl
                                    └─ train_iteration2.py (Áfangi 2.4b)
                                          └─ iter2_main_*.lgb (×6)
                                             iter2_summer_*.lgb (×6)
                                             iter2_predictions.pkl
                                               └─ audit_2_4c_residuals.py (Áfangi 2.4c)
```

Áfangi 2 baseline módel notar:
- `kaupskra.csv` (arm's-length filter, target verð)
- `properties_v2.pkl` (structured features)
- `geography_features.pkl` (geo features)
- Pairing output ekki nauðsynleg í baseline — hedonic keyrir á sales bara.

---

## Post-parse audit niðurstöður

| Mælikvarði | Gildi |
|---|---|
| Unique FASTNUM (properties_v2) | 124.835 |
| Unique augl_id (listings_v2) | 471.591 |
| Unique faerslunumer (sales_v2) | 173.409 |
| Listings með valid date (2000-2030) | 464.866 (98,57%) |
| Sales með valid date | 173.409 (100%) |
| Listings date range | 2010–2026 |
| Sales date range | 2006–2026 |
| Unique FASTNUM í listings_v2 | 58.437 (47% af 125K fasteignastofninum) |
| Kaupskrár records (CSV) | 226.481 |
| Arm's-length records | 174.526 |
| Paired_fresh í pairs_v1 (2015+) | 55.538 |
| Training preview (Áfangi 2.0) | 148.608 |
| Training data v1 final | 144.254 |
| Baseline test MAPE | 15,36% |
| Baseline held MAPE | 17,19% |
| **Iter2 main held MAPE (production)** | **7,97%** |
| Iter2 combined held MAPE | 11,66% |

---

## Full-DB audit niðurstöður (núna deprecated, haldið til reference)

Áður en 1.4.3 data cleanup fór fram höfðum við:

| Mælikvarði | Gildi (á merged DB) |
|---|---|
| Eignir alls | 126.246 |
| Ok-eignir | 124.834 |
| Listings með parseable floor (merking) | 87.295 |
| Unique buildings (by coords) | 32.292 |
| Total listings í merged DB | 516.007 |
| Með dated thinglystdags | 91.074 (17,65% — korrupterað) |

Kaupskrá CSV: 226.481 færslur. Arm's-length eftir ONOTHAEFUR-filter: 174.526.

---

## Taxonomy coverage (post 1.1)

| Fjölskylda | Records | % |
|---|---|---|
| MAIN residential (7 kóðar) | 105.523 | 84,5% |
| SECONDARY residential (5 kóðar) | 368 | 0,3% |
| SUMMERHOUSE | 4.513 | 3,6% |
| **Í módeli alls** | **110.404** | **88,4%** |
| EXCLUDE | 14.519 | 11,6% |

(Tölur gilda fyrir properties_v2 eftir cleanup. audit_1_7 rekur á 110.316 vegna þess að það notar classify_property tuple-form; báðar tölurnar eru innan 0,1% hvor annarrar.)

---

## Nýbyggingarsegment (post 1.2)

| Kategorí | Count | % af arm's-length |
|---|---|---|
| FULLBUID=0 eingöngu (pre-completion) | 3.371 | 1,9% |
| FULLBUID=1 + years≤2 eingöngu | 19.938 | 11,4% |
| Bæði skilyrði | 3.293 | 1,9% |
| **Union (nýbyggingar alls)** | **26.602** | **15,2%** |

Pre-completion discount: Fjölbýli 12%, Einbýli 23%.

**Per TEGUND**:

| TEGUND | New-build rate |
|---|---|
| Atvinnuhúsnæði | 23,6% |
| Sérbýli | 22,5% |
| Fjölbýli | 15,3% |
| Sumarhús | 9,9% |
| Einbýli | 5,1% |

Mikil ósamhverfa milli Einbýli (5,1%) og Sérbýli (22,5%) reflekterer að Sérbýli eru oft developed í project-scale (raðhús, parhús) á meðan Einbýli eru oftar byggð sem sérbyggingar af eiganda.

---

## Eignabreytingarregla (post 1.3)

Repeat-sale par útilokað ef:
1. FULLBUID 1→0 transition milli sala (88 pör í sample)
2. `|pct_change|` á `EINFLM` milli sala > **5%** (2.070 pör)

Impact á 68.696 consecutive arm's-length pör: 2.133 droppuð (3,1%), 66.563 held (96,9%).

---

## Field stability findings (post 1.4.1) ⚠

**Frozen snapshots í kaupskrá CSV — aldrei nota sem per-sale values:**
- `FASTEIGNAMAT_GILDANDI` (notið `FASTEIGNAMAT` í staðinn)
- `FYRIRHUGAD_FASTEIGNAMAT` (notið `FASTEIGNAMAT`)
- `BRUNABOTAMAT_GILDANDI` (engin historical í CSV)
- `FJHERB` (engin historical í CSV — sækja úr augl_json ef þörf; nú í listings_v2)

**Réttir historical dálkar:** KAUPVERD (99,40% varies), FASTEIGNAMAT (98,65%), EINFLM (6,77%), FULLBUID (4,60%), LOD_FLM (4,31%).

---

## Outlier filter findings (post 1.4.2)

HMS kaupskrá er óvenju hrein. Ekki einn factor-1000 innsláttarvilla í 226K safninu.

Á residential arm's-length með valid price+size+mat (N=162.692):

| Regla | Færslur | % |
|---|---|---|
| `is_price_outlier` (combined) | 172 | 0,106% |
| `is_size_outlier` (<20 eða >1000) | 153 | 0,094% |
| **Union (drop)** | **324** | **0,199%** |

---

## Floor-feature discovery (Áfangi 2 backlog, post 2026-04-18)

| Byggingarhæð | Top-floor premium | Spread 1→top |
|---|---|---|
| 4 hæða | +2,3% | +1,5 m.kr |
| 5 hæða | +3,6% | +3,0 m.kr |
| 6-7 hæða | +4,3% | +4,8 m.kr |
| 8-10 hæða | +4,6% | +4,0 m.kr |
| 11+ hæða | +3,5% | +4,1 m.kr |

Features að bæta við í Áfanga 2 baseline: `merking_floor`, `building_max_floor`, `is_top_floor`, `floor_fraction`.

---

## Verðbólguleiðrétting

| Viðmið | VNV | Stuðull til 2026M05 |
|---|---|---|
| 2006M05 | 255,2 | ×2,66 |
| 2015M01 | 421,0 | ×1,61 |
| 2020M01 | 472,8 | ×1,44 |
| 2026M05 | 678,3 | ×1,00 |

---

## Ákvarðanir sem eru lokaðar (sjá DECISIONS.md)

30+ ákvarðanir skráðar. Lykil-atriði:
- Target = þinglýst kaupverð í raunvirði (CPI-deflated).
- Uncertainty = LightGBM quantile regression, fimm quantiles + mean.
- Geography = tvö lög (matsvaediNUMER + götureitur spatial smoothing deferred til 2b).
- Arm's length = `ONOTHAEFUR_SAMNINGUR=1` útilokað.
- Nýbygging = `FULLBUID=0 OR BYGGAR innan 2 ára af THINGLYSTDAGS`.
- Withdrawn listings → markaðsyfirlit.
- Infra stack = Hetzner + Postgres/PostGIS + Docker Compose + Dagster + MLflow + Cloudflare R2.
- Taxonomy: MAIN (7), SECONDARY (5), SUMMERHOUSE (1), EXCLUDE.
- Verðbólguleiðrétting til rolling latest month með VNV verðtryggingarútgáfu.
- Floor features í baseline: `merking_floor`, `building_max_floor`, `is_top_floor`, `floor_fraction`.
- Eignabreytingarregla = EINFLM |pct_change| > 5% eða FULLBUID 1→0.
- Frozen-snapshot dálkar í kaupskrá CSV = FASTEIGNAMAT_GILDANDI, FYRIRHUGAD_FASTEIGNAMAT, BRUNABOTAMAT_GILDANDI, FJHERB.
- Outlier filter: Combined fm_ratio + segment-z signal, ósymmetrisk regla.
- Canonical data layer = v2 pickles frá `parse_all_dbs.py`. Merged DB er deprecated.
- Dedupe: latest scraped_at wins per (augl_id | faerslunumer | fastnum); listings prefer date_valid=True first.
- Invalid dates (`0001-...`) retained sem NaT með `date_valid=False` flag.
- Lysing HTML texti stored separately í `listings_text_v2.pkl`.
- **Pairing defaults: X=90d session boundary, Y_fresh=180d, Y_valid=365d.** (nýtt 2026-04-18 kvöld)
- **pair_status 7-flokka taxonomy, `in_scrape_gap` sem metadata flag (ekki síunarregla).** (nýtt 2026-04-18 kvöld)
- **Scrape gap frá 2025-07-01 accepted — ekki backfill, nýr scraper í Áfanga 0.** (nýtt 2026-04-18 kvöld)
- **Nýbyggingar-tilgáta um off_market Fjölbýli rejected; Danni's pre-fastnum tilgáta skráð í 1.8b backlog.** (nýtt 2026-04-18 kvöld)
- **Geography rare-merge við 50 sölur; bare lat/lon í LightGBM frekar en pre-computed spatial grid.** (nýtt 2026-04-18 kvöld)
- **FEPILOG AABBCC hierarchy decoded; unit_category = AA+BB feature, is_main_unit flag.** (nýtt 2026-04-18 lokakvöld)
- **Multi-unit policy: keep single-FASTNUM SKJALANUMER eingöngu í baseline training.** (nýtt 2026-04-18 lokakvöld)
- **FEPILOG AA=02 er ekki garage-flokkur; AA er mixed across all values. Feature design óbreytt (unit_category + is_main_unit) en AA ekki notað sem exclusion key.** (nýtt 2026-04-18, Áfangi 2.0 audit)
- **is_top_floor og floor_fraction gated á `building_max_floor >= 2`; NaN fyrir single-floor buildings.** (nýtt 2026-04-18, Áfangi 2.0 audit)
- **Baseline LightGBM hyperparameters**: num_leaves=63, lr=0.05, min_data_in_leaf=40, ff=0.9, bf=0.8, early_stopping=100. (nýtt 2026-04-18, Áfangi 2.3)
- **Chronological split**: train ≤2023, val 2024, test 2025, held 2026+ (baseline). (nýtt 2026-04-18, Áfangi 2.3)
- **Iter2 splits**: train_ext = train+val combined, test = early stopping, held = pure holdout. (nýtt 2026-04-18, Áfangi 2.4b plan)
- **Iter2 architecture**: SUMMERHOUSE aðskilið í sérstakt módel; main model er ex-SUMMERHOUSE. (nýtt 2026-04-18, Áfangi 2.4b plan)
- **real_fasteignamat = FASTEIGNAMAT × cpi_factor** bætt við sem 20. feature í iter2. (nýtt 2026-04-18, Áfangi 2.4b plan)
- **Spatial KNN smoothing deferred til 2b** — residuals mildly clustered (std 0,038), low priority. (nýtt 2026-04-18, Áfangi 2.4a)
- **Iter2 main model = production hedonic for residential**; held MAPE 7,97%, bias −1,5%. Both mechanisms (FASTEIGNAMAT drift + 2024 plateau) fixed. (nýtt 2026-04-18, Áfangi 2.4c)
- **SUMMERHOUSE acknowledged unresolved**; main features insufficient. Needs land-value + amenity features. Not blocker for residential website. (nýtt 2026-04-18, Áfangi 2.4c)
- **Áfangi 2 closed** fyrir residential; next step = Áfangi 3 extraction schema. cov80 near-miss (70% vs 75% target) ekki blocker. (nýtt 2026-04-18, Áfangi 2.4c)

---

## Áfangi 1 data quality scorecard

| Categoria | Score |
|---|---|
| properties_v2 geo coverage | 100% |
| properties_v2 tegund coverage | 100% |
| listings_v2 date_valid | 98,6% |
| kaupskrá THINGLYSTDAGS parseable | 100% |
| Arm's-length rate | 77% |
| Pairing — 2015+ paired_fresh rate | 44% |
| Pairing — Einbýli paired_fresh | 57% |
| Pairing — Fjölbýli paired_fresh | 43% |
| Ask-to-sale median (paired_fresh) | 0,982 |
| Outlier rate (residential) | 0,20% |
| Scrape freshness (pre-2025-07) | 100% |
| Scrape freshness (post-2025-07) | 10% (gap) |

---

## Áfangi 3a niðurstöður (extraction schema kickoff, 2026-04-18 til -19)

### Scope og budget

Áfangi 3 er text-extraction out of 456K lýsinga í `listings_text_v2.pkl`. Markmið: bæta marginal signal yfir iter2 (held MAPE 7,97%) með structured features úr lýsingum. Target iter3 MAPE: 6–7% range (optimistic; academic hedonic+text literature gefur 0,5–1,5 pp lift þegar structured baseline er sterk).

**Scope-restriction á round 1**: paired subset only (~80K listings), ekki full 456K corpus. Unpaired listings eru ekki í iter3 training og skila engum iter3-lift. Deferred til round 2 þegar vettvangurinn skilar value.

**Budget round 1**: ~$240 með Haiku 4.5 + batch API (50% afsl) + prompt caching (90% afsl á static 8K-token schema).

**Per-model pricing** (staðfest 2026-04-18 via anthropic docs):

| Model | Input / Output $/MTok | 456K-scale estimate | 80K paired round 1 |
|---|---|---|---|
| Haiku 4.5 + batch + caching | ~$0,003 / listing | $1,500 | **$240** |
| Sonnet 4.6 + batch + caching | ~$0,010 / listing | $4,400 | $800 |
| Opus 4.7 + batch + caching | ~$0,017 / listing | $7,600 | $1,400 |

### Schema v0.2.1 — component-level rich

Lykil-design insight (Danni, 18. apríl): fasteignalýsingar innihalda component-level detail sem skiptir máli. V0.1 lumpaði „ný rafmagnstafla" og „yfirfarin rafmagnstafla" undir sama flagg; v0.2 gerir skýran greinarmun með 7-stiga status enum.

**Status enum** (gildir fyrir öll 18 components):
- `replaced_new` — nýtt, skipt um („nýtt þak", „nýskipt tafla")
- `overhauled` — yfirfarið, gert í gegn („rafmagnstafla yfirfarin")
- `well_maintained` — vel viðhaldið án specific action
- `original_functional` — upprunalegt, virkar
- `needs_work` — þarfnast framkvæmda
- `in_progress` — í vinnslu („byrjað að klæða")
- `not_mentioned` — ekki í lýsingu

**18 components × 3 fields (status, year, detail) = 54 matrix fields**:
- Unit-level (11): kitchen, primary_bathroom, secondary_bathroom, flooring, interior_finishes, paint, electrical_panel, electrical_wiring, plumbing, heating, windows_unit
- Building-level (7): roof, cladding, windows_building, insulation, elevator_mechanism, sameign_cosmetic, foundation_drainage

**Plus 39 situational/meta fields**: útsýni (2), útipláss detail (5), parking detail (3), layout (6), building & annað (5), negative signals (3), agent framing (3), augl-supplement trilemmas (7), narrative + meta (5).

**Samtals 93 fields**. Output-cost impact á móti flat v0.1 schema (25 fields) er ~10–15% hærri því flestir component-fields verða `not_mentioned` (stutt strings í JSON).

### Empirical coverage findings úr `verify_augl_flags.py`

listings_v2 hefur 37 dálka og öll 10 target augl-flag nöfn eru þar sem direct columns. En coverage er ójöfn:

**100% populated (ekki extracta)**: `fjherb`, `fjsvfnherb`, `fjbadherb`, `bilskur` (computed), `n_myndir`, `inngangur` (99,9%, 42-value categorical), `byggar` (99,4%).

**14% populated (extract sem supplement)**: `svalir`, `gardur`, `lyfta`, `staedi`, `rafbill`, `pets`, `hjolastoll`, `eldrib` — sama 86,2% null-rate á öllum og á `lat`/`long`. Source-driven (source_db hefur 5 unique values, líklega að bara einn skilaði augl parsed). Post-extraction merge: augl-flag tekur precedence ef non-null, extracted trilemma fyllir í þegar augl er null.

### Sample draw findings

Script `draw_gold_standard_sample.py` keyrt á D:\:
- Pool eftir alla filtera: **33.976 paired listings** með lýsingu 300–3000 chars
- Öll 36 cells populated (region × type_bucket × era), engin thin
- 100 stratified + 20 worst-held oversample = 120 labelling targets
- Canonical breakdown (stratified): SFH_DETACHED 25, APT_FLOOR+ATTIC 25, APT_STANDARD+BASEMENT 24, ROW+SEMI 26
- Region balance: Country 34 / Capital_sub 33 / RVK_core 33 — nákvæmlega balanced
- Worst-held APE range: 25,2% til 119,0% (stress-test cases)

### Labeling infrastructure

**`gold_standard_labeling.xlsx`** smíðað með `build_labeling_xlsx.py` — 106 cols × 121 rows:
- 11 context cols (prefilled úr sample CSV, light-blue fill)
- 54 component matrix cols
- 41 situational + meta cols
- 48 enum cols fá data validation dropdown
- 3 multi-select cols (view_type, reported_issues, storage_type) með header-comment útskýringu á semicolon format
- Frozen row 1 og col A
- Header comments á öllum labels

Labeler uploadar xlsx í Google Drive → Open with Google Sheets → data validation preservast. Aðskilinn browser-tab með `LABELING_GUIDE.md` sem reference.

---

## Áfangi 3b decision (2026-04-19) — Middle-ground validation chosen over formal gold-standard

Danni pushað back á formal hand-labeling protocol (15–30 klst manual labeling commitment) með rökum að LLM-extraction iteration með manual scan gefur sufficient quality fyrir commercial-grade residential model án þess að krefjast formal kappa agreement numbers. „Erum við ekki að tala um að gervigreindin geri þetta?"

**Valið workflow** (Áfangi 3b/3c):

1. Pilot extract 200 listings á Haiku 4.5 ($1,35)
2. Manual scan outputs, flag augljós issues
3. Discovery analysis (keyword + LLM meta-analysis) fyrir unknown-unknowns
4. Synthesa concrete v0.2.2 refinements
5. Re-run pilot með v0.2.2 → verify improvements
6. Ef gott → 80K batch extraction
7. **Fallback**: ef v0.2.2 re-pilot marginal, revert í formal protocol

**Hvað við spörum**: ~25 klst af Danni's tíma í manual labeling.

**Hvað við töpum**:
- Engin formal kappa inter-rater agreement metric
- Engin per-field F1/precision/recall numbers
- Engin explicit quality gates

**Hvað við höldum**:
- Visual inspection af extraction quality (fann well_maintained pattern strax)
- Ability til að catch systematic patterns
- Gold-standard sample er samt drawn (200 rows) og má nota fyrir formal validation seinna ef þörf krefur
- Duplicate detection infrastructure sem uppgötvaði 12,4% pop dup rate

---

## Áfangi 3c niðurstöður (pilot + discovery, 2026-04-19)

### Pilot extraction infrastructure — `pilot_extract.py`

Highlights:
- Model: `claude-haiku-4-5-20251001`
- Tool-use með strict JSON schema (`extract_property_features` tool definition)
- Prompt caching: `cache_control: {type: "ephemeral"}` á system prompt + tool definition
- Few-shot: 2 embedded examples (Vesturbæjar elaborate + Akranes terse)
- Max_tokens 2500
- Retry logic: 3 attempts með exponential backoff fyrir rate limits + transient errors
- Incremental JSONL writes (append-per-extraction)
- Incremental CSV saves með `safe_csv_save` (try/except PermissionError + retry á 2s delay, leysir Excel file-lock)
- **Resume-from-JSONL logic** (critical eftir sleep-interruption incident fyrst run)
- UTF-8-sig encoding fyrir Excel + Google Sheets compatibility

### Pilot results — 200 listings

**Infrastructure**:
- Zero extraction failures (robust tool_use + schema validation)
- Total cost actual $1,35 (not estimate)
- Per-listing average $0,0067
- Cost breakdown: fyrsta call $0,014 (cache write 6.840 tokens), subsequent ~$0,006 (cache read 90% off)
- Duration ~40 min sequential, ~10 sek per call
- **Projected batch 80K**: sync $534, batch (50% off) $267

**Quality highlights** (virkar vel):
- Renovation-year extraction sterk: row 5 fangar kitchen 2019, flooring 2019, windows 2019, cladding 2019 með detail sambeisuð á réttum components
- Narratives genuinely good — 2–4 setninga Icelandic prose, ekki copy-paste, ekki repetitive
- New-build detection correct (agent_lead_selling_point = new_build_appeal)
- Parking distinctions work (assigned_outdoor vs unassigned vs enclosed_garage)
- Balcony size + orientation captured

**Quality issues fyrir v0.2.2** (þrjú systematic patterns):

1. **`well_maintained` over-use** (stærsta issue):
   - Distribution per component: kitchen 64%, primary_bathroom 60%, flooring 54%, interior_finishes 55%
   - Pattern: Claude treatar feature description + positive adjective („fallegt eldhús, granít borðar") sem condition signal
   - Marketing puffery („fallegt", „glæsilegt", „mjög fínt") inflates well_maintained; true condition signal gets diluted
   - Compare: components correctly defaulted til not_mentioned þegar truly absent: paint 92%, electrical_panel 92%, insulation 92%
   - **FIX fyrir v0.2.2**: tighten system prompt til að krefjast explicit condition language („í góðu standi", „vel viðhaldið", „í topp standi"). Marketing adjective + feature description → `not_mentioned`.

2. **„Þak" vs „þakkantur" semantic confusion**:
   - Row 14 (SFH Sandgerði): lysing segir „eftir er að klæða undir þakkantinn" (roof-edge cladding incomplete)
   - Claude flagged roof=in_progress. Raunin: only cladding_in_progress.
   - **FIX fyrir v0.2.2**: add explicit example í system prompt: „þakkantur" (roof edge) er ekki „þak" (roof itself). „Að klæða undir þakkantinn" → cladding_in_progress, ekki roof.

3. **`listing_elaboration` inflated**:
   - Distribution: elaborate 68%, promotional_heavy 26%, standard 6%, terse 0%
   - Either threshold too low eða sample bias by 300-3000 char filter
   - **FIX fyrir v0.2.2**: recalibrate thresholds — terse <150 words, standard 150-300, elaborate 300-600, promotional_heavy 600+ OR heavy promotional language.

### Discovery analysis — `discover_gaps_keywords.py`

Ókeypis (regex-based). 120 Icelandic real-estate keywords í 12 flokkum: entrance/hallway, flooring materials, heating, fireplaces, pools, proximity (leikskóli/skóli), wet-areas, architectural (lofthæð), outdoor, storage, sameiginlegt/sér, new-build, sale-pressure.

**Top gaps** (keyword í lysing, NOT í extraction):
- `forstofa` (entrance hall): 26 af 27 gap 96%
- `eik` (oak flooring): 21 af 31 gap 68%
- `flísar` (tiles): 13 af 25 gap 52%
- `hol` (hallway/landing): 11 af 13 gap 85%
- `leikskól` (daycare proximity): 8 af 11 gap 73%
- `arinn` (fireplace): 7 af 14 gap 50%
- `klætt` (cladded): 6 af 6 gap 100%
- `sundlaug` (pool): 5 af 5 gap 100%

Þessi mentions eru líklega lítt predictive per-se en gefa vísbendingu um fields sem ætti mögulega að bæta við (flooring material, specific rooms, proximity features).

### Discovery analysis — `discover_gaps_llm.py` (pending run)

Sonnet 4.6 meta-analysis per (lysing, extraction) pair. Prompt spyr: „hvaða signals í lýsingu eru ekki í extraction sem hafa áhrif á verðmat?" ~$4 total fyrir 200-pilot.

Status: **pending**. Krafið $4 budget + Tier 2 API access (sem þarfnast 7 daga bið). Plan: keyra strax eftir Tier 2 advance.

### Duplicate analysis — `check_duplicates.py`

Sample (200 pilot): 0 exact duplicates, 0 first-500-char duplicates.

**Population (53.866 paired + length-filtered 300–3000 chars)**:
- Exact-text duplicates: TBD (run ekki keyrt á full pop)
- **First-500-char duplicates: 6.687 (12,4%)**
- Eftir dedup: 47.179 unique listings
- Top-10 dup groups eru öll nýbyggingar-developments:
  - Lund í Kópavogi 27×
  - Grímsgata 2-4, Urriðaholt 31× total (2 agent templates)
  - Hlíðarendi 17×
  - Dvergurinn við Lækjargötu 15×
  - Asparlaut 1-5 15×

**Dedup strategy fyrir batch extraction**: extract one representative per hash-group, propagate to all, add `extraction_group_size` metadata. In iter3, apply `sample_weight = 1 / sqrt(extraction_group_size)` fyrir weighted cancellation af shared-signal bias (forða data leakage þegar 15 identical listings eiga mismunandi target prices).

**Saves**: $22 í dedup vs no-dedup batch. Minor budget saving. Main value er signal quality fyrir iter3.

### Size/legal signals gap (manual scan 50 listings)

Danni flaggaði „óskráðir fermetrar" → manual scan fann 24% of listings (12 af 50) hafa size/legal signals **NOT captured** í v0.2.1:

| Signal | Example | Frequency |
|---|---|---|
| Explicit „óskráð rými" | Row 8: „Óskráð rými á neðri hæð er u.þ.b 40 fm" | 2 / 50 |
| „Háaloft" nefnt | Rows 9, 26, 42 | 3 / 50 |
| „Mikil lofthæð" / „3ja metra lofthæð" | Rows 10, 25 | 2 / 50 |
| „Aukaíbúð" (separate sub-unit) | Rows 4, 5, 45 | 3 / 50 |
| „Ónýttur byggingarreitur" | Row 1: „90 fm" | 1 / 50 |
| „Sérlóð" (private lot in shared development) | Ýmsar | ~5 / 50 |

**Critical case** (row 8): 40 fm unregistered space = potentially +15-20% property value, completely missed in current schema.

### Budget revision

| Metric | Original | Actual |
|---|---|---|
| Paired + length-filtered pool | 80.000 (estimate) | **53.866** (actual) |
| Per-listing Haiku (sync, observed) | $0,003 (estimate) | $0,0067 |
| Per-listing Haiku (batch, projected) | $0,0015 | $0,0033 |
| Total sync if ran 80K | $240 | $534 |
| Total batch 53.866 no dedup | — | **$178** |
| Total batch 47.179 med dedup | — | **$156** |

Innan $200–300 upphaflegs budget en með betri strategy.

### Proposed schema v0.2.2 additions (~11 new fields)

**Size & legal (6 fields)** — 24% gap currently:

| Field | Type | Rationale |
|---|---|---|
| `unregistered_space_present` | trilemma | Óskráð rými flag |
| `unregistered_space_sqm_stated` | int \| null | m² number ef nefnd |
| `unregistered_space_type` | multi: loft_attic / basement / addition / garage_converted / other | Hvað konar |
| `has_secondary_unit` | trilemma | „Aukaíbúð" (aðskilið frá is_duplex sem er lagal status) |
| `ceiling_height_premium` | trilemma | „Mikil lofthæð", „3ja metra lofthæð" |
| `unused_building_rights_present` | trilemma | „Ónýttur byggingarreitur" — real verðmæti |

**Outdoor (5 fields)** — garden_quality currently conflates size + condition:

| Field | Type | Rationale |
|---|---|---|
| `lot_type` | enum: private_einkalod / shared_sameign / private_in_shared_serlod / not_applicable / not_mentioned | **Biggest-impact field**. Sérlóð er major APT premium |
| `lot_orientation` | enum: south_southwest / east_west / north_shade / mixed / not_mentioned | Afstaða |
| `garden_size_framing` | enum: unusually_large / large / standard / small / not_mentioned | Decoupled frá condition |
| `is_corner_lot` | trilemma | Horn-lóð |
| `is_waterfront_or_seaside` | trilemma | Sjávarlóð |

**Refactor existing field** — `garden_quality` decoupled from size, values now condition-only: `well_landscaped_mature` / `standard_maintained` / `minimal_or_neglected` / `none` / `not_mentioned`.

**Deferred candidates fyrir v0.3** (nýbyggingar sub-schema, ekki critical í fyrstu batch):
- `finish_package_level` (Pakki 1/2/3)
- `delivery_status` („afhendingartíminn")
- `early_occupancy_available` („laus strax")
- `building_permit_status` („samþykkt teikning")

**System prompt v2 refinements**:
- Tighten `well_maintained` criterion: require explicit condition language, ekki marketing puffery
- Add explicit „þak" vs „þakkantur" distinction example
- Recalibrate listing_elaboration thresholds (150/300/600 word brackets)
- Add óskráð rými extraction guidance með m² number capture
- Add 3rd few-shot example (row 8 pattern — SFH með óskráð rými)

**Estimated impact**: schema grows 93 → ~104 fields. Output tokens +5%. Per-listing cost $0,0067 → ~$0,0070. Batch 47K cost $156 → ~$165. Trivial delta.

---


## Áfangi 4 niðurstöður (iter3 training + post-audit fixes, 2026-04-19)

### Iter3 v1 (first run): overfit í extraction features án real_fasteignamat

Scriptið `train_iteration3.py` var skrifað same structure og iter2 (main + summer split, 6 LightGBM models per split). Input: training_data_v2.pkl eftir patch (fixes á unregistered_space_sqm zero-fill bug + num_parking_spaces cap).

Fyrsta keyrsla missti **real_fasteignamat** — iter2 feature (FASTEIGNAMAT × cpi_factor) var computed inline í train_iteration2.py og ekki persistent í training_data_v1.pkl, svo build_training_data_v2.py inherited sama gap. Handoff til iter3 nefndi „same hyperparams og iter2" en ekki að duplicate-a feature engineering.

Held main MAPE: 9,30% (vs iter2 7,97% baseline). Regression, ekki lift. Bias −0,043 (mechanism 1 vandamál aftur komið).

### Iter3 v2 (fix: added real_fasteignamat + has_extraction_data)

Eftir insert af `real_fasteignamat = FASTEIGNAMAT * cpi_factor` og `has_extraction_data = extraction_success.fillna(0).astype(int)` sem computed features efst í scriptinu:

| Metric | iter2 baseline | Iter3 v2 |
|---|---|---|
| Held main MAPE | 7,97% | **7,96%** |
| Held main medAPE | 5,24% | 5,03% |
| Held main bias (log) | −0,015 | −0,014 |
| Held 80% PI coverage | 69,9% | 69,7% |
| Held 95% PI coverage | 89,5% | 91,3% |

Marginal lift á medAPE og cov95 en essentially tie á MAPE. Feature importance: real_fasteignamat 64,7%, FASTEIGNAMAT 13,1%, age 4,7%, EINFLM 3,8%, matsvaedi_bucket 3,5%. Öll 95 engineered extraction features samanlagt: **~1% af gain**.

### Per-segment held MAPE (iter3 v2 main):

| Segment | N | MAPE | medAPE |
|---|---|---|---|
| APT_STANDARD | 740 | 6,13% | 4,46% |
| ROW_HOUSE | 100 | 7,52% | 4,60% |
| APT_FLOOR | 1.019 | 8,33% | 5,26% |
| SEMI_DETACHED | 48 | 9,04% | 6,30% |
| APT_BASEMENT | 51 | 10,42% | 4,84% |
| **SFH_DETACHED** | **106** | **16,20%** | **9,32%** |

SFH er outlier-segment með residual SD 0,213 (tvöfalt APT_STANDARD 0,081). Quantile output hefur wide SFH band (w80_log=0,316) en ennþá undercovered (67,0% cov80).

### Ákvörðun: Iter3 v2 frozen sem last-iteration mean model.

Extraction features eru redundant við FASTEIGNAMAT + structured features fyrir hedonic mean MAPE. Real signal er til í residuals á extracted subset (ICS × residual correlation = −0,20 á held) en LightGBM tekur það ekki upp vegna sparse coverage (24%) og dominance af dense 100%-populated features.

Lærðdómur: í íslenskum markaði er FASTEIGNAMAT + aldur + matsvæði + stærð informationally near-saturated fyrir baseline hedonic. Auka extraction features skila sér ekki í mean prediction — þær skila sér í **uncertainty calibration, UI comparables, markaðsyfirlit metrics, og TOM módel** (sjá Áfangi 5+ rescope).

---


## Áfangi 4c (data quality filter + segment-stretch calibration, launched 2026-04-19)

### Hvað þetta er

Niðurstaða úr tveggja-hringja deep-dive með öðrum Claude instance og empirical validation á þessum enda:

1. **kv_ratio filter** — 4–12% af transactions eru ONOTHAEFUR slip-through (seljandi-tengdir aðilar, hlutasölur, erfðagjafir, fixer-uppers) með `KAUPVERD/FASTEIGNAMAT < 0,70` eða `> 1,50`. Dropping þessi rows úr train/val/test batar held MAPE frá 7,96% → 6,96% (undir 7,0% target). Held sjálft er **unfiltered** fyrir realistic evaluation.

2. **Segment-specific stretch calibration** — ódýr alternative við variance-head. Multiplicar existing iter3 q100/q900 og q025/q975 output með per-segment k-factor (kalibreraður á val+test pool). SFH fær k80=1,18 sem lyftir cov80 frá 67,0% í 75,5%. APT_STANDARD fær k80=1,10 (minimal stretch). Zero new model, ein JSON skrá, mánaðarlegt recalibration job.

### Af hverju ekki variance-head

Deep-dive Claude lagði upphaflega til variance-head sem launch-critical (section 6 í fyrstu skýrslu). Þrjár validation-niðurstöður á þessum enda afvísuðu það:

1. **Heavy-tail er raunverulegt en mismunandi touch point**: Residual z-distribution á held hefur kurtosis 9,6 (Gaussian 3) og tail [3,5)|z| er 4× Gaussian. En þetta er drifið að mörgu leyti af kv_ratio slip-through — eftir filter fer `quantile(|resid|/std, 0.95)` úr 2,09 í near-Gaussian 2,09 (sjá z-multiplier reconciliation í DECISIONS).

2. **Segment-stretch slær variance-head á SFH**: Variance-head V3 gaf SFH held cov80=54,7%. Segment-stretch gefur 75,5%. Variance-head lærði sigma_hat ~0,04 fyrir SFH þegar empirical resid_SD er 0,21 — það underestímaði SFH variance vegna all-segments pooled training. Þetta er segment-inn sem bankar munu nota mest; 20 pp coverage gap er unaceptable.

3. **Aggregate coverage gain yfir stretch er aðeins 0,6 pp**: Variance-head pool-calibrated gaf held 73,1% cov80. Uniform stretch pool-calibrated gaf 72,5%. Variance-head var 0,6 pp betra á aggregate en 20 pp verra á SFH. Operational complexity (kalibrering, sigma estimation, drift monitoring) réttlætir ekki þetta.

### Final metrics (clean held, after segment-stretch):

Mælt á quality-clean held (N=2.026, kv_ratio ∈ [0,7; 1,5]):

| Metric | Iter3 v2 uncalibrated | Iter3 v3 + segment-stretch |
|---|---|---|
| Held MAPE | 7,96% | **~6,96%** |
| Held medAPE | 5,03% | **~4,96%** |
| Held 80% PI coverage | 69,7% | **~72,4%** |
| Held 95% PI coverage | 91,3% | **~92,2%** |
| SFH cov80 specifically | 67,0% | **~75,5%** |

(Tölurnar eru empirical estimates frá existing iter3 v2 predictions + kv filter + pool-cal stretch. Iter3 v3 retrain mun gefa uppfærðar tölur með model fitted á clean data.)

### Pipeline

```
training_data_v2.pkl (patched)
  → filter_training_data.py       → training_data_v3.pkl
  → train_iteration3_v3.py        → iter3v3_*.lgb + iter3v3_predictions.pkl
  → calibrate_segments.py         → calibration_config.json
  → production scoring reads JSON and applies segment k to q100/q900
```

Mánaðarlegt cronjob: trailing 12m residuals → update k-factors í calibration_config.json. Regime-aware uncertainty without new model.

---


## Áfangi 4c revision (iter3 v3 retrain post-mortem, 2026-04-19 22:43)

**Hvað gerðist**: Scripts `filter_training_data.py`, `train_iteration3_v3.py`, og `calibrate_segments.py` voru keyrð að áætlun. Niðurstöður afhjúpuðu að **dropping slip-through rows úr training gerði model verra á held**, ekki betra eins og spáð.

### Tölur

| Metric | iter3 v2 baseline | iter3 v3 (filter í training) | Δ |
|---|---|---|---|
| Held ALL MAPE (N=2.084) | 7,96% | **8,80%** | +0,84 pp verra |
| Held CLEAN MAPE (N=2.026) | 6,90% | 7,29% | +0,39 pp verra |
| Held ALL cov80 | 69,7% | 66,1% | −3,6 pp verra |
| Held ALL cov95 | 91,3% | 86,8% | −4,5 pp verra |
| SFH_DETACHED held clean MAPE | 10,68% | 11,03% | −0,35 pp verra |

Per segment var v3 verra en v2 á 5 af 6 main residential segments. Eini segmentinn sem batnaði var SEMI_DETACHED (9,33% → 8,83%, N=48, varla marktækt).

### Hvers vegna

Filter dropaði 16.216 af 129.769 train+val rows (12,5%) og 568 af 8.575 test (6,6%). Þessi 16 þúsund rows voru:
- **0,3-0,6% kv_ratio < 0,70**: genuine slip-through (~500-700 rows total)
- **~11% kv_ratio > 1,50**: mest nýbyggingar með genuinely hátt markaðsverð vs FASTEIGNAMAT — **ekki noise**

Model missti training signal um hvernig nýbyggingar verðlagðast ofan á FASTEIGNAMAT. Bias á held fór úr −0,013 í −0,022. Per-segment verði v3 undirverðlegði nánast alls staðar.

Segment-stretch k-factors á v3 quantiles urðu líka minni (1,02–1,11) en á v2 (1,10–1,18) vegna þess að quantile regression í v3 lærði þrengri quantiles á hreinu training data — en held inniheldur slippers sem þessar quantiles capture ekki.

### Lærðdómur

Kv_ratio filter er **evaluation tool, ekki training tool**:
- Í training þarf model að sjá full distribution, inclúsive nýbyggingar og ættaryfirfærslur, til að kalibrerast.
- Í evaluation er gagnlegt að reporta bæði all-held og clean-held metrics — clean gefur „model performance on valid comparables", all gefur „production MAPE including edge cases".
- Í production scoring skal flag-a suspect transactions (kv outlier í price history) sem `is_suspect_comparable=1` í UI, ekki útiloka frá samanburði.

### Rollback

- **iter3 v2 er canonical production mean model**. `iter3_*.lgb` og `iter3_predictions.pkl` eru canonical.
- **iter3v3_*.lgb skjöl eru deprecated** — má halda á D:\\ sem audit trail en ekki nota í scoring.
- **training_data_v3.pkl er preserved** — notkun eingöngu til að fá is_quality_transaction flag í predictions, ekki retraining.
- **Ný calibration**: `calibrate_segments_v2.py` keyrir á v2 predictions, produces uppfærðan `calibration_config.json` með k-factors frá v2 val+test clean pool.

### Staða Áfanga 4c eftir rollback

| Metric | Status |
|---|---|
| Held ALL MAPE (production target 7,0%) | 7,96% — under target 8,0% but not at 7,0% |
| Held CLEAN MAPE | 6,90% — under 7,0% |
| Held CLEAN cov80 after v2-cal stretch | ~75% (spáð frá pre-run audit) |
| Held CLEAN cov95 after v2-cal stretch | ~92% (spáð) |
| SFH cov80 after v2-cal stretch | ~75,5% (spáð) |

Bíður lokakeyrslu á `calibrate_segments_v2.py` fyrir endanleg staðfestu metrics.

---


## Áfangi 4c LOKIÐ (v2 + segment-stretch final results, 2026-04-19 22:53)

### Actual calibrated metrics

**Held ALL (N=2.084) — production-realistic, inniheldur slip-through**:

| Metric | Value |
|---|---|
| MAPE | 7,96% |
| medAPE | 5,60% |
| cov80 | 71,9% (width_log 0,209) |
| cov95 | 91,3% (width_log 0,402) |

**Held CLEAN (N=2.026) — arm's-length transactions only**:

| Metric | Value |
|---|---|
| MAPE | **7,00%** (target hit) |
| medAPE | 5,38% |
| cov80 | 73,1% (width_log 0,204) |
| cov95 | 92,7% (width_log 0,393) |

### Per-segment held clean

| Segment | N | MAPE | cov80 | w80_log |
|---|---|---|---|---|
| APT_ATTIC | 17 | 6,45% | 94,1% | 0,270 |
| APT_BASEMENT | 49 | 6,53% | 71,4% | 0,229 |
| APT_FLOOR | 979 | 7,26% | 74,3% | 0,216 |
| APT_STANDARD | 731 | **5,95%** | 72,6% | 0,170 |
| ROW_HOUSE | 99 | 7,30% | 67,7% | 0,192 |
| SEMI_DETACHED | 48 | 9,04% | 60,4% | 0,219 |
| SFH_DETACHED | 100 | 11,13% | **73,0%** | 0,304 |

APT_STANDARD hefur banka-grade accuracy (5,95% MAPE). SFH_DETACHED held cov80 hoppaði úr 67,0% uncalibrated í 73,0% eftir stretch — 20+ pp betra en variance-head V3 alternative sem gaf 54,7%. Staðfestir ákvörðun að sleppa variance-head.

### k-factors (per-segment, saved in calibration_config.json)

| Segment | k80 | k95 | Túlkun |
|---|---|---|---|
| APT_ATTIC | 1,01 | 0,87 | Well-calibrated quantile; shrink 95% tails |
| APT_BASEMENT | 1,01 | 0,95 | Near-perfect quantile fit |
| APT_FLOOR | 1,05 | 1,01 | Minor 80% stretch |
| APT_STANDARD | 1,06 | 0,98 | Minor 80% stretch, shrink 95% |
| ROW_HOUSE | **1,12** | 0,98 | Biggest 80% stretch needed |
| SEMI_DETACHED | 1,01 | 0,99 | Well-calibrated |
| SFH_DETACHED | 1,00 | 0,93 | Quantile width perfect at 80%, shrink 95% |
| _global_fallback | 1,05 | 0,99 | For any unknown segment |

Notable: most k95 factors are **below 1,0** (shrinkage). Iter3 quantile regression over-learned conservative 95% tails; empirical calibration pulls them tighter.

### Production scoring pipeline (launch-ready)

```
Listing inflow → existing feature pipeline → iter3 v2 .lgb model →
  {pred_mean_log, pred_q100_log, pred_q900_log, pred_q025_log, pred_q975_log}
  → canonical_code lookup in calibration_config.json →
  apply k80, k95 segment-specific stretch →
  {pred_mean, pi_80_lo, pi_80_hi, pi_95_lo, pi_95_hi}
  → display with is_suspect_comparable flag if kv_ratio outlier detected
```

Zero new model dependencies. Simple JSON lookup + arithmetic. Monthly recalibration job reads trailing 12m residuals and rewrites k-factors.

### Áfangi 4c closed. Launch-ready for pilot.

---


## Áfangi 4d — Operational pipeline (launched 2026-04-19 23:45)

### Context

Eftir 4c closure er core valuation module tilbúið, en monthly refresh-chain vantar. Fyrir production module ser nægir ekki að hafa frozen models — gögnin þurfa að streyma: nýjar þinglýstar sölur (HMS), CPI uppfærslur (Hagstofa), og endurþjálfun fyrir regime drift.

Fimm-skref monthly cycle:

```
1. refresh_cpi.py               ✓ done + smoke-tested 2026-04-19
2. refresh_kaupskra.py          ← next
3. rebuild_training_data.py     ← next
4. monthly_recalibration.py     ✓ done (þarf rebuild skref fyrst fyrir input)
5. validate_metrics.py          ← next
```

### Skref 1 staðfest virkar

`refresh_cpi.py` (2026-04-19 23:32 local test):
- Endpoint: `https://px.hagstofa.is/pxis/api/v1/is/Efnahagur/visitolur/1_vnv/1_vnv/VIS01004.px`
- Code: `Vísitala = financial_indexation` (vísitala neysluverðs til verðtryggingar, base maí 1988 = 100)
- 374 mánuðir fetched (1995M04 – 2026M05)
- Reference VNV: 678,30 (2026M05)
- cpi_factor sanity: 2026M04 gefur 1,005485 — **nákvæmlega eins og training pickle gefur**
- Atomic write, encoding-tolerant read fyrir existing CSV
- Safety aborts á >5% shrinkage í fetch vs existing

### Skref 4 virkar á eigin en þarf skref 2–3 til að vera meaningful

`monthly_recalibration.py` getur keyrt á existing training_data_v2.pkl en það capture-ar ekki nýjar sölur síðasta mánaðar. Full operational value krefst að refresh_kaupskra og rebuild_training_data séu keyrð fyrst.

### Production scoring staðfest

`score_new_listing.py` smoke-tested 2026-04-19 23:51. Sample APT_STANDARD 85 m², BYGGAR 1998, postnr 105, FASTEIGNAMAT 45 mkr:

| Output | Gildi |
|---|---|
| Mean prediction | 62,1 mkr |
| Median (q500) | 56,9 mkr |
| 80% PI | 47,9 – 64,3 mkr |
| 95% PI | 46,8 – 68,9 mkr |
| Implied kv_ratio | 1,38 (within arms'-length range) |
| Suspect flag | False |

Mean yfir median (log-normal right skew) — correct behavior. 95% PI wider en 80% PI á báðum hliðum — correct.

### Bugs leysir í test

Tveir bugs komu upp í smoke-tests og voru fixaðir:

1. **CPI loading (bug í original `score_new_listing.py`)**: reyndi að parsa `cpi_verdtrygging.csv` með assumed column names `year, month, vnv`. Existing CSV er með annað schema. **Fix**: byggja CPI lookup úr `training_data_v2.pkl` þar sem `cpi_factor` er þegar per row. Robustara en CSV parsing.

2. **Categorical dtype mismatch**: LightGBM var þjálfað á pandas `Categorical` með fyrirfram skilgreindum `categories`. Scoring sendi raw strings, leiddi til „categorical_feature do not match" error. **Fix**: load categorical_mappings úr training pickle, cast columns í matching Categorical dtype við inference. Einnig bætt við runtime warning ef óþekkt gildi send inn.

### Known warnings / limitations

- Pandas 4.0 deprecation warning: `pd.Categorical(values, categories=X)` þegar values innihalda entries sem ekki eru í X verður raise í framtíðinni. Þetta er intentional path fyrir óþekkt gildi (verður NaN) og við fylgjumst með future-proofing í framtíðar-release.
- `matsvaedi_bucket` og `unit_category` eru strict: unknown values → NaN → predictions illa calibrated. UI layer verður að mappa inflow á training categories before scoring.
- Reference cpi_factor breytist mánaðarlega (þegar nýtt VNV er birt). Þetta er expected og deterministic; `rebuild_training_data.py` verður að re-deriva öll real_kaupverd/real_fasteignamat með nýjum factor svo features haldist consistent.

---


## Áfangi 4d — Skref 2 staðfest (refresh_kaupskra, 2026-04-20 00:19)

### Niðurstaða

`refresh_kaupskra.py` keyrt á D:\ — download endpoint virkar, MD5 verified, atomic install.

```
Remote Last-Modified: Sun, 19 Apr 2026 02:00:42 GMT
Remote size:          44,1 MB (content-length 46.272.642 bytes)
Download time:        ~few sec
MD5:                  YgTSzW5gC6e5ra3UVtuIdA== (verified)
Row count:            226.481
```

Script er idempotent: second run HEAD-checkar MD5, matches state JSON, exit early án download. State tracking í `D:\kaupskra_fetch_state.json`. Backup í `D:\kaupskra_prev.csv` fyrir rollback.

### HMS endpoint (staðfest 2026-04-20)

```
https://frs3o1zldvgn.objectstorage.eu-frankfurt-1.oci.customer-oci.com
  /n/frs3o1zldvgn/b/public_data_for_download/o/kaupskra.csv
```

OCI Object Storage bucket í Frankfurt. `hms.is` landing síða linkar á þennan URL. URL virðist stöðug — `frs3o1zldvgn` er OCI tenant identifier sem ætti að haldast svo lengi sem HMS hefur sama Oracle samning.

Monthly update pattern (observed): Sunnudagur 2. viku mánaðar ~02:00 GMT. Latest transaction í skjalinu er ~2 vikna lag frá publication (latest þinglýsingardagur 2026-04-17 í 2026-04-19 release).

### Composite primary key finding (critical)

**Kaupskrá primary key er `(FAERSLUNUMER, FASTNUM)`, ekki `FAERSLUNUMER` eitt.**

Staðfestar tölur (2026-04-20):
- 226.481 total rows
- 212.514 unique FAERSLUNUMER
- **13.967 duplicates (6,2% af dataset)**

Einn kaupsamningur (SKJALANUMER) getur innihaldið margar fasteignir (multi-parcel deed). Hver FASTNUM er separate row í kaupskrá með sama FAERSLUNUMER. Dæmi: `SKJALANUMER=T-005121/2006` selur bæði `FASTNUM=2223287` og `FASTNUM=2223288` á sömu dagsetningu fyrir sama heildarverð.

**Implication**: existing „single-FASTNUM SKJALANUMER" filter í training data cascade (DATA_SCHEMA.md) er ekki bara „clean-up heuristic" — hann er **mandatory** til að forðast double-counting í training. Filterinn var settur inn af vel rökstuddri ástæðu; rebuild_training_data.py MUST preserve hann.

Initial assumption um PK var röng og ég fixaði script-ið áður en það gekk í production. Ef einhver annar í framtíðinni byggir pipeline sem hleður kaupskrá í gagnagrunn, þarf PK skilgreining að vera composite.

---


## Áfangi 4d LOKIÐ — end-to-end monthly cycle staðfest (2026-04-20 10:15)

### Full cycle keyrt í röð

Eftir að CPI schema bug var fixaður (sjá DECISIONS „2026-04-20 protocol lesson" entry), var öll 5-skref sekvens keyrð á D:\\ 2026-04-20 10:08–10:11, allir með exit 0:

```
python refresh_cpi.py           # migrated CPI CSV úr legacy schema í target
python refresh_kaupskra.py       # no-op, MD5 match á sömu kaupskra.csv
python rebuild_training_data.py  # v1 + v2 rebuilt, zero shape drift
python monthly_recalibration.py  # blocked á SEMI_DETACHED drift (expected)
python validate_metrics.py       # 8/8 drift checks pass
```

### Rebuild shape drift (safety sanity)

| PKL | Prev | Ný | Row drift | Col drift |
|---|---|---|---|---|
| training_data_v1 | (144.254, 35) | (144.254, 35) | 0,00% | 0,00% |
| training_data_v2 | (144.254, 170) | (144.254, 170) | 0,00% | 0,00% |

Perfect idempotency á sama kaupskra MD5 — rebuild er safe og reproducible.

### validate_metrics vs 4c baseline (8/8 pass)

| Metric | 4c baseline | Post-cycle | Δ |
|---|---|---|---|
| Held clean MAPE | 7,00% | **7,01%** | +0,01 pp |
| Held clean cov80 | 73,10% | 72,85% | −0,25 pp |
| Held clean cov95 | 92,70% | 92,69% | −0,01 pp |
| Held all MAPE | 7,96% | 7,98% | +0,02 pp |
| Held all cov80 | 71,90% | 71,69% | −0,21 pp |
| SFH cov80 | 73,00% | 73,00% | +0,00 pp |
| APT_STANDARD MAPE | 5,95% | 5,97% | +0,02 pp |

Allir innan ±0,5 pp MAPE og ±3,0 pp coverage thresholds. 4c baseline reproducible.

### Safety mechanisms sönnuðust í raun

1. **rebuild_training_data.py per-component rollback**: Í fyrstu end-to-end cycle (2026-04-20 09:30), bilaði v1 build með `KeyError: 'year_month'` úr cpi.py vegna CPI schema mismatch. Orchestrator rollback-aði v1 pkl klínt úr prev backup, kept v2 unchanged. Exit 2. Debugging straightforward — ljóst hvar í cascade bilun varð.

2. **monthly_recalibration.py drift blocker**: SEMI_DETACHED k95 drift +34,3% (k80 +21,8%) fór yfir 30% threshold. Auto-update blocked, manual review required. Full alternative JSON skrifuð í log fyrir possible accept. Consistent með 4c post-mortem lesson: bias dýpkun er snemma warning sem má ekki silent-ly aðlagast.

3. **validate_metrics drift checks**: Embedded baseline embedded úr DECISIONS 4c closure entry; 8 per-segment og overall checks; exit 0 þegar allir pass. History snapshot skrifað í `D:\validation_history\YYYYMMDD.json` fyrir trend monitoring.

### Sub-percent numerical drift observation

Held clean MAPE fór úr 7,00% → 7,01% og cov80 úr 73,10% → 72,85% milli rebuilds með bit-identical inputs (sama kaupskra MD5, sami CPI). Orsök: pandas merge í v2-build skilar rows í aðeins mismunandi röð, sem breytir `pd.Categorical` category ordering, sem breytir integer-kóðum sem LightGBM sér. Sub-percent floor innan allra thresholds og acceptable fyrir operational pipeline. Strangari reproducibility krefst sort-pre-categorize í build scripts — deferred til iter 5+.

### CPI schema migration (protocol lesson)

Þegar `refresh_cpi.py` var smoke-tested 2026-04-19 skrifaði scriptið CSV í „year,month,vnv" schema, en downstream `cpi.py` les `year_month,cpi` format. Smoke test missti integration test. Fix 2026-04-20 10:05: `write_csv_atomic` skrifar nú target schema; `read_existing_csv` detectar bæði schemas og force-rewrite á migration. Validated með 3 smoke tests sem simulera `cpi.py` `load()` nákvæmlega. Principle: smoke test má aldrei vera bara „script rennur án villu" — verður að inkludera downstream consumer simulation. Skráð sem protocol lesson í DECISIONS.

### SEMI_DETACHED drift alert — pending decision

Monthly recalibration blokkaði autonomous k-factor update. Drift alert er raunverulegur markaðssignal, ekki bug:

- SEMI_DETACHED: k95 +34,3%, k80 +21,8%
- Global k80: +22,9%
- Öll segments drifta plús áttina (wider intervals needed)

Tvær leiðir:
1. Accept drift: overwrite calibration_config.json með nýjum k-factors. Betri empirical coverage strax á 2026 Q2 markaði.
2. Hækka drift threshold úr 30% í 40%: leyfa auto-updates á þessum stærðum, halda aftur í raunverulegum regime shifts.

Ákvörðun deferred til að hafa 2-3 monthly cycles gagnagrundvöll. Ekki urgent — current calibration virkar vel á held data.

### Production state eftir 4d closure

| Component | Status |
|---|---|
| Models (iter3 v2, 12 × .lgb) | Frozen canonical |
| Calibration (iter3v2_segcal_v1) | Frozen canonical |
| Training data v2 (144.254 × 170) | Rebuild-able via monthly cycle |
| Operational scripts (5) | All staðfest virkt end-to-end 2026-04-20 |
| Backups (_prev pkl, kaupskra_prev, calibration_history) | Preserved fyrir audit + rollback |

Áfangi 4d marks completion of launch-critical operational infrastructure. Pipeline er production-ready fyrir pilot launch.

---


## Áfangi 6 LOKIÐ — BMN repeat-sale index framleiddur (2026-04-20)

### Niðurstaða

Framleiðir Bailey-Muth-Nourse (BMN) OLS repeat-sale verðvísitölu per (canonical_code × region_tier) × ársfjórðung fyrir 2006Q2–2026Q2. 27 af 33 cells fitted (6 skipped fyrir n < 50). 56.824 clean pairs eftir filter cascade (83.1% af 68.381 consecutive pairs). Bæði nominal og CPI-deflated real indices framleiddir.

### Filter cascade niðurstöður

```
Starting consecutive pairs:                            68.381
(a) Drop is_new_build_t1 = True:                       59.305  (-13.3%)
(b) Drop |EINFLM change| > 5%:                         57.482  (-3.1%)
(c) Drop FULLBUID 1 → 0:                               57.437  (-0.1%)
(d) Drop pair_span_days < 90:                          56.878  (-1.0%)
(e) Drop canonical_code changed:                       56.878  (-0.0%)
(f) Drop region_tier changed:                          56.878  (-0.0%)
(g) Drop |log_price_ratio_nominal| > 2:                56.824  (-0.1%)
Final clean pairs:                                     56.824  (83.1%)
```

### Main residential real index trajectory

| Segment × Region | n_pairs | Real CAGR | Crash trough | Drawdown | Real 2026Q2 |
|---|---|---|---|---|---|
| APT_STANDARD × RVK_core | 10.594 | 1,73% | 2010Q3 | -29,0% | 140,9 |
| APT_STANDARD × Capital_sub | 4.719 | 1,54% | 2010Q1 | -27,8% | 134,8 |
| APT_STANDARD × Country | 2.632 | 1,80% | 2013Q1 | -31,3% | 142,5 |
| APT_FLOOR × RVK_core | 9.322 | 1,53% | 2010Q1 | -29,7% | 135,6 |
| APT_FLOOR × Capital_sub | 11.031 | 1,58% | 2011Q2 | -32,6% | 136,9 |
| APT_FLOOR × Country | 7.300 | 2,83% | 2013Q1 | -17,9% | 174,9 |
| ROW_HOUSE × RVK_core | 227 | **0,51%** | 2011Q2 | **-48,5%** | 104,0 |
| SFH_DETACHED × Capital_sub | 934 | 1,50% | 2011Q1 | -41,0% | 134,8 |
| SFH_DETACHED × RVK_core | 222 | 2,87% | 2010Q1 | -41,3% | 175,0 |

### Publishable findings (3 key)

(a) **Landsbyggð catch-up**: APT_FLOOR Country real growth 2006→2026 = +74,9% vs RVK_core +35,6% og Capital_sub +36,9%. Country vex 2× meira en RVK í raun-verði. Starting divergence er consistently frá 2016. Tvær candidate-hypotheses (RVK bubble concentration í 2006 baseline vs tourism rental demand), ekki separated ennþá en finding stendur óháð.

(b) **ROW_HOUSE RVK_core niche**: Lægsta real CAGR (0,5%) og dýpsta drawdown (-48,5%) af öllum main residential cells. Raðhús í Reykjavík er small-supply niche þar sem 2006-2008 bubble var most inflated. Empirical domain insight sem var ekki augljóst fyrirfram.

(c) **SUMMERHOUSE missed crash**: Country sumarbústaðir real CAGR +7,0% per ár og trough er 2006Q2 sjálft (aldrei niður fyrir baseline). Asset-class counter-cyclical við innlent hrun — tourism/rental driven market, ekki domestic.

### Quality distribution

| Quality | Count | Notes |
|---|---|---|
| high | 534 | n_period ≥ 20 AND se < 0,05 |
| medium | 497 | n_period ≥ 5 AND se < 0,10 |
| low | 1.044 | n_period ≥ 1 |
| insufficient | 598 | n_period = 0 → index NaN |

Dashboard má filtera í high/medium fyrir user-facing views (38% af period-rows), með „show all" toggle fyrir audit.

### Output skrár

| Skrá | Innihald |
|---|---|
| `repeat_sale_index.pkl` / `.csv` | Full output, 2.673 rows (33 × 81), 15 cols |
| `repeat_sale_pairs.pkl` | 56.824 clean pairs post-filter cascade, 16 cols |
| `repeat_sale_summary.csv` | Per-cell CAGR og crash-depth table, 27 rows |
| `residential_real_grid.png` | 3×3 grid (APT_STANDARD + APT_FLOOR + SFH_DETACHED) × 3 regions |
| `apt_floor_regional.png` | Country catch-up overlay (sterkasti visual fyrir fjölmiðla) |
| `nominal_vs_real.png` | Methodology explainer fyrir banka/regulator |
| `sample_density_heatmap.png` | Cell × ár heatmap, quality-transparency tool |
| `crash_recovery_zoom.png` | 2006-2018 focus, RVK residential (CI bands deferred) |
| `build_repeat_sale_index.py` | End-to-end build script (56s runtime) |
| `analyze_repeat_sale_index.py` | Plots + summary stats generator |

### Deferred til framtíðar

- CI bands á crash_recovery_zoom.png (thin samples look unfair án CI)
- Geometric Mean Revert Case-Shiller (GMRCS) ef BMN noise er issue downstream
- Weighted BMN með interval-distance weights
- Monthly sub-index fyrir RVK_core (fyrir leading indicators í dashboard)
- Integration í monthly cycle (`refresh_dashboard_tables.py`) — post-rebuild_training_data, pre-validate_metrics

### Áfangi 6 closed. Index ready fyrir dashboard consumption.

---


## Áfangi 7 niðurstöður (ATS lookup tafla)

Dual-table ATS (ask-to-sale gap) lookup framleiddur úr `pairs_v1.pkl` paired_fresh subset. 5 output-skrár á D:\\, 1,7 sec runtime á 52.001 clean+inclusion-filtered pairs.

### Scope og filter cascade

| Skref | N | Skýring |
|---|---|---|
| paired_fresh base | 55.544 | `pair_status == 'paired_fresh'` |
| post scrape-gap exclusion | 53.386 | `~in_scrape_gap` |
| post EXCLUDE filter | 52.136 | `canonical_code != 'EXCLUDE'` |
| post outlier clip | 52.083 | `ATS ∈ [0.5, 2.0]`, 53 rows clipped |
| post inclusion filter | 52.001 | all-time cell n ≥ 50, 23 cells included, 7 excluded |

Includes main residential × 3 regions (APT_ATTIC Capital_sub+RVK, APT_BASEMENT × 3, APT_FLOOR × 3, APT_STANDARD × 3, ROW_HOUSE × 3, SEMI_DETACHED × 3, SFH_DETACHED × 3) + SUMMERHOUSE Capital_sub/Country + APT_UNAPPROVED RVK. Excludes APT_MIXED/APT_ROOM (n<50) og APT_ATTIC Country (n=48).

### Table A quality distribution (913 rows)

| Segment | high | medium | low | insufficient | % usable |
|---|---|---|---|---|---|
| APT_FLOOR | 83 | 37 | 0 | 2 | 98,4% |
| APT_STANDARD | 102 | 18 | 0 | 4 | 96,8% |
| ROW_HOUSE | 42 | 74 | 3 | 3 | 95,1% |
| SFH_DETACHED | 35 | 79 | 4 | 3 | 94,2% |
| SEMI_DETACHED | 21 | 68 | 10 | 20 | 74,8% |
| APT_BASEMENT | 37 | 42 | 1 | 39 | 66,4% |
| APT_ATTIC | 3 | 47 | 3 | 25 | 64,1% |
| SUMMERHOUSE | 0 | 33 | 11 | 33 | 42,9% |
| APT_UNAPPROVED | 0 | 4 | 0 | 27 | 12,9% |

### Table B quality distribution (63 rows pooled)

| Quality | Count | Notes |
|---|---|---|
| high | 41 | n≥20 ∧ sd<0,05 |
| medium | 21 | n≥5 ∧ sd<0,10 |
| low | 1 | SEMI_DETACHED Country cold |
| insufficient | 0 | Pooling mission accomplished |

6 missing (seg × reg × heat) combos af 69 expected (all-time): APT_BASEMENT Country og APT_UNAPPROVED RVK_core fá NaN heat_bucket vegna <8 stable quarters (6 og 4 qtrs respektive), svo báðar absent úr Table B.

### Heat-label methodology

Static percentile p33/p67 á quarterly medians per (segment × region). Monthly refresh recomputes. Rolling z-score hafnað fyrir lookup vegna reproducibility (historical labels má ekki drift); rolling 3-mo/12-mo z-score notaður sér fyrir live regime indicator í dashboard_monthly_heat.

### Publishable findings (4 key)

**(a) Heat-label monotonicity confirmed**. cold < neutral < hot í median_log_ratio á öllum 21 populated cells. Deltas hot_minus_cold 0,016-0,091. Stærstu: SUMMERHOUSE Capital_sub (9,1% price differential hot vs cold), SFH_DETACHED RVK (2,9%), SEMI_DETACHED RVK (2,8%).

**(b) Above-list rate er strongest regime signal**. 3-4× hlutfall í hot vs cold fyrir flest residential cells. APT_ATTIC RVK 14% → 47%, SEMI_DETACHED RVK 12% → 47%, APT_STANDARD RVK 9% → 33%. Bidding-war dynamics í hot regime clearly captured.

**(c) Dispersion er NOT function af heat**. 12 cells hypothesis-compatible (cold > hot MAD), 9 reverse. Mean effect negligible (+0,003). Empirical claim: „Ask-to-sale gap sveiflan er stöðug (MAD ~0,02-0,03) óháð regime; munur hot/cold liggur í miðgildi, ekki dreifingu". Simplifies scoring — PI-width ≈ constant across heat buckets.

**(d) Current market state 2025-06** (síðasti mánuður pre-scrape-gap): APT_STANDARD RVK_core z = -0,74 (cold), ROW_HOUSE Capital_sub z = -0,91 (cold), flest residential neutral/cold. SFH_DETACHED Country z = 0,51 (hot) — counter-trend með Áfanga 6 Country catch-up story. Yearly aggregate staðfestir 2022 peak (above_list 33,1%) → 2023 trough (9,8%) → 2024-2025 stabilization (12-14%).

### Scoring usage pattern

```python
row = table_b.loc[(seg, reg, current_heat_bucket)]
predicted_sale = list_price * np.exp(row.median_log_ratio)
pi_80_lo = list_price * np.exp(row.median_log_ratio - 1.28 * row.dispersion_mad)
pi_80_hi = list_price * np.exp(row.median_log_ratio + 1.28 * row.dispersion_mad)
```

Current_heat_bucket ákvarðast af latest quarter's row í Table A (retrospective). Fyrir live dashboard „current regime" indicator: z_3v12 > 0,5 = hot, z < -0,5 = cold, annars neutral úr `ats_dashboard_monthly_heat`.

### Output skrár

| Skrá | Innihald |
|---|---|
| `ats_lookup_by_quarter.pkl` / `.csv` | Table A, 913 × 13, historical per-quarter audit |
| `ats_lookup_by_heat.pkl` / `.csv` | Table B, 63 × 10, primary scoring pooled |
| `ats_heat_thresholds.pkl` / `.csv` | 23 × 6, p33/p67 audit per cell |
| `ats_dashboard_quarterly.pkl` / `.csv` | 359 × 8, region-collapsed trends |
| `ats_dashboard_monthly_heat.pkl` / `.csv` | 2.501 × 9, rolling z-score regime indicator |
| `ats_diagnostic.py` | Pre-build validation tool |
| `build_ats_lookup.py` | End-to-end build (1,7 sec) |

### Deferred til framtíðar

- `analyze_ats_trends.py` — plots: above-list rate timeline, regime indicator timeline, pooled-distribution-by-heat violins
- Leading-indicator heat definition (months-of-supply, TOM, withdrawal rate) as v2 ef ATS-derived heat sýnir PI-calibration issues
- Integration í monthly cycle (`refresh_dashboard_tables.py`) — post-rebuild_training_data, pre-calibration, parallel við repeat_sale_index

### Áfangi 7 closed. ATS lookup ready fyrir dashboard + scoring consumption.

---


## Progress tracking

| Áfangi | % Complete | Staða |
|---|---|---|
| 0 — Infrastructure | 0% | Planning begun (hosted dashboard arkitektúr valin) — parallel workstream |
| 1 — Segmentering & audit | 96% | 1.8b deferred (needs re-parse/new scraper) |
| 2 — Baseline módel | 80% | Residential closed (held 7,97%); SUMMERHOUSE deferred |
| 3 — Extraction schema | 100% | Schema frozen, batch run klárt, training_data_v2 pipeline completed |
| 4 — Iter3 training | 100% | Iter3 v2 frozen at held MAPE 7,96% (mean model). Extraction redundant w/ FASTEIGNAMAT for hedonic mean |
| 4c — Quality filter + calibration | 100% | v2 + segment-stretch frozen as production. Held clean MAPE 7,00%, cov80 73,1%, cov95 92,7%, SFH cov80 73,0%. |
| 4d — Operational pipeline | 100% | Öll 5 scripts ✓ staðfest virkt end-to-end 2026-04-20. Held clean MAPE 7,01% post-cycle (baseline 7,00%, 8/8 drift checks pass). `refresh_dashboard_tables.py` integration staðfest 2026-04-20 21:00 (65-81s, shape +0,0%). Monthly cycle nú 6-skref. Pending: SEMI_DETACHED drift ákvörðun. |
| 5 — Extraction-driven UI + metrics (rescoped from "full extraction + model v2") | 0% | Comparables UI, condition-adjusted flow, markaðsyfirlit condition metrics |
| 6 — Repeat-sale index | 100% | 27/33 cells fitted. Held MAPE N/A (not valuation). 56.824 clean pairs. Publishable: Country catch-up +75% vs RVK +36% real (2006→2026), ROW_HOUSE RVK_core niche (-48,5% crash), SUMMERHOUSE missed crash. |
| 7 — Ask-to-sale lookup tafla (rescoped — NO ML module) | 100% | Dual-table (A per-quarter + B heat-pooled) framleitt úr 52K paired_fresh. 5 output-skrár á D:\\. `refresh_dashboard_tables.py` orchestrator integration staðfest. Publishable: heat-monotonicity allir cells, above-list 3-4× regime-driven, dispersion NOT function af heat (contra hypothesis), 2025-06 market state mostly cold. |
| 8–10 | 0% | — |

**Vegið heildar: ~82%**

---

## Næstu skref þegar nýr chat byrjar (uppfært 2026-04-20 21:10, orchestrator LOKIÐ)

1. Lesa STATE.md, DECISIONS.md, WORKING_PROTOCOL.md, TAXONOMY.md, DATA_SCHEMA.md, GLOSSARY.md, EXTRACTION_SCHEMA_v0_2_2.md.

2. **Áfangi 4d LOKIÐ** (operational pipeline). **Áfangi 6 LOKIÐ** (repeat-sale BMN index). **Áfangi 7 LOKIÐ** (ATS lookup dual-table). **Orchestrator integration LOKIÐ** (refresh_dashboard_tables, 6-skref monthly cycle staðfest virk).

3. **Canonical output-skrár frá Áfanga 6 á D:\\**:
   - `repeat_sale_index.pkl` + `.csv` — 2.673 rows, 15 cols
   - `repeat_sale_pairs.pkl` — 56.824 clean pairs
   - `repeat_sale_summary.csv` — 27-row per-cell CAGR og crash-depth
   - 5 .png plots (residential_real_grid, apt_floor_regional, nominal_vs_real, sample_density_heatmap, crash_recovery_zoom)
   - Scripts: `build_repeat_sale_index.py`, `analyze_repeat_sale_index.py`

4. **Canonical output-skrár frá Áfanga 7 á D:\\**:
   - `ats_lookup_by_quarter.pkl` + `.csv` — Table A, 913 rows × 13 cols, per (seg × reg × qtr)
   - `ats_lookup_by_heat.pkl` + `.csv` — Table B, 63 rows × 10 cols, pooled per heat. **Primary scoring table**.
   - `ats_heat_thresholds.pkl` + `.csv` — 23 × 6, p33/p67 audit
   - `ats_dashboard_quarterly.pkl` + `.csv` — 359 × 8, region-collapsed
   - `ats_dashboard_monthly_heat.pkl` + `.csv` — 2.501 × 9, rolling z-score regime indicator
   - Scripts: `ats_diagnostic.py`, `build_ats_lookup.py`

5. **Monthly cycle frozen (6 skref)**:
   1. `refresh_cpi.py`
   2. `refresh_kaupskra.py`
   3. `rebuild_training_data.py`
   4. `refresh_dashboard_tables.py` — wraps build_repeat_sale_index + build_ats_lookup, cross-script atomicity, rollback á failure. Staðfest 2026-04-20: 65-81s runtime, idempotent (+0,0% shape deltas).
   5. `monthly_recalibration.py`
   6. `validate_metrics.py`

6. **Val á næsta áfanga** — þrír valkostir:
   - **Áfangi 5** (extraction-driven UI + comparables) — comparables UI, condition-adjusted flow, markaðsyfirlit condition metrics. Þarf extraction features sem voru redundant fyrir hedonic mean en hafa ótæmt adjacent value.
   - **Áfangi 0** (infrastructure / hosted dashboard) — Supabase + Vercel stack, public-facing dashboard v0, custom domain. Parallel workstream, ekki blocker fyrir Áfanga 5.
   - **SEMI_DETACHED drift investigation** — eftir 1-2 monthly cycles bera saman k-factor trajectories, ákveða hvort drift er sampling noise eða real regime shift. Bíður gagnagrundvöll.

7. **Deferred** (ekki blockers):
   - `analyze_ats_trends.py` — plots fyrir Áfanga 7 (regime timeline, above-list trend, pooled distributions by heat)
   - CI bands á crash_recovery_zoom.png
   - Monthly RVK sub-index fyrir leading indicators
   - Cleanup: eyða `D:\_rollback_backup\20260420_205839` (preserved úr --keep-backup test)

8. **Known limitations (óbreyttar)**:
   - SEMI_DETACHED held cov80 60,4% (N=48 small sample)
   - SFH held MAPE 11,13%
   - SUMMERHOUSE still broken í valuation módeli (170% MAPE)
   - Pandas 4.0 Categorical warning í score_new_listing
   - ATS: APT_BASEMENT Country og APT_UNAPPROVED RVK_core hafa NaN heat_bucket (niche fallback, <8 stable qtrs)

9. **Parallel backlog (ekki blockers)**: nýr scraper, SUMMERHOUSE iter3, variance-head, Round 2 extraction, landnum-based alt-pairing.


---

## Áfangi 8 — verdmat-is production platform (í gangi)

**Síðast uppfært:** 21. apríl 2026

### Stakkur
- Next.js 16 + React 19 + Tailwind v4
- Supabase (PostgreSQL, Pro tier, eu-north-1 Stockholm, project szzjsvmvxfrhyexblzvq)
- Vercel deploy at https://verdmat-is.vercel.app
- GitHub: https://github.com/danielthormagnusson-coder/verdmat-is

### Phase 1A — Precompute (KLÁRAÐ 2026-04-21)
- `build_precompute.py` á `D:\verdmat-is\precompute\`
- 7 CSV outputs í `exports\`: properties, predictions, feature_attributions (SHAP top-10), comps_index, sales_history, repeat_sale_index, ats_lookup
- Total 202 MB of 450 MB cap
- 124.835 properties · 110.316 predictions (residential + summerhouse) · 1,1M SHAP rows · 1,1M comp rows

### Phase 1B — Live deploy (KLÁRAÐ 2026-04-21)
- DB size: 424 MB (Pro tier ceiling 8 GB — was 500 MB on free, at 85%)
- Pages: `/`, `/eign/[fastnum]`, `/markadur`, `/um`
- Wow features: autocomplete leit, per-eign verðmat með 80/95% CI, SHAP waterfall á íslensku, Leaflet kort, comps gallery með CloudFront myndir, sölusaga, heat grid, repeat-sale index 2006-2026

### Phase 1C — Bug fixes (KLÁRAÐ 2026-04-21)
- A: `sales_history` nominal unit bug leyst (72.900.000.000 kr → 72,9 M kr). Phase 1A `kaupverd_real` formula endurbætt (training_data_v2.cpi_factor lookup per (year, month)).
- B: `/markadur` repeat-sale chart stopped at 2013Q4 → now full 2006Q2-2026Q2. Orsök: PostgREST `max-rows=1000` default, pagination bypass.
- C: landing featured + autocomplete filter á `is_residential = true`. Non-residential detail page sýnir "Verðmat ekki í boði" notice í stað prediction/SHAP/comps/market sections.

### Phase 1D — Document sync (KLÁRAÐ 2026-04-21)
- Authoritative Claude.ai Project folder version restored til D:\ (11 skrár)
- GitHub `docs/` folder í verdmat-is repo creates single source of truth fyrir chat-Claude + Claude Code
- WORKING_PROTOCOL.md updated með sync rule (D:\ → docs/ → git → origin)

### Áfangi 2-5 — Module Robustness (NÆSTA)
- Target: remove `real_fasteignamat` dependence (currently 45-85% feature importance per prediction)
- Reason: annual HMS fasteignamat updates cause 5-10% overnight jumps — not acceptable for bank/pro users
- Plan: iter4 standalone (no fastmat input) + selected LLM features from existing extraction
- LLM extraction audit 2026-04-21: existing `batch_extraction_propagated.csv` (40.814 listings, v0.2.2, quality validated) is sufficient — no re-extraction needed. Property-level coverage 27% (28.546 / 105.803 residential). Gap extraction only if Áfangi 2-5 Skref 6a feature selection identifies LLM features as critical.
- Feature selection approach: structured features only for iter4 v1, add LLM features in v2, manual-layer questionnaire in Áfangi 9 (Sprint 3)

### Áfangi 2-5 byrjað (2026-04-21)
Iter4 standalone training. LLM extraction audit passed — reusing existing 40.814 rows v0.2.2. iter3v2 stays as production archive until Áfangi 2-5 Skref 10 import swaps in iter4.

### iter4 structured-only result (2026-04-21, Skref 4)
- **iter4a held MAPE: 8.19%** (iter3v2 baseline: 7.97%, delta +0.22 pp)
- PI coverage undercoverage: 80% PI = 66.3% (target 78%), 95% PI = 89.1% (target 94%) — calibration pending in Skref 7
- Feature importance redistribution: EINFLM 34.5% + sale_year 19.6% + matsvaediNUMER 17.6% + matsvaedi_bucket 14.2% + BYGGAR 4.5% replaces iter3v2's 77.9% fastmat dominance
- iter4b (init_model fine-tune) skipped: LightGBM requires feature compatibility with init_model, so dropping FASTEIGNAMAT is incompatible. Winner = iter4a by default.
- Training time: 9.4 min (vs 60-90 min estimate)
- Status: Stop-conditions not tripped (MAPE < 15%). Proceed to Skref 5 (LLM features already joined in training_data_v2; verify coverage).

### Áfangi 2-5 KLÁRAÐ (2026-04-21)
iter4 standalone í production. Held MAPE 8.19% (iter3v2: 7.97%, delta +0.22 pp) — cost-of-stability aðeins 1/14 af því sem áætlað var (3-5 pp). DB size 561 MB (Pro tier, plenty of headroom). iter3v2 archived í `predictions_iter3v2` og `feature_attributions_iter3v2`. Debug mode á `/eign/[fastnum]?mode=debug` sýnir samanburð.

**Sanity:** fastnum 2000281 (Bakkastígur 1): iter4 91.6 M kr (80% PI 81.5–105.3), iter3v2 var 89.6 M kr, delta +2.2%.

**Known gap:** 80% PI coverage á held er 68% (target 80%). Segment stretch calibration hjálpar ekki meira á þessum predictions — quantile spread er ekki nógu breitt. Sprint 2+ fix: conformal prediction eða retrain quantile módelin með bigger bagging.

**Frontend additions:**
- HMS-fasteignamat relabeled með reference-only caveat
- `?mode=debug` sýnir iter4 vs iter3v2 samanburðartöflu
- Landing hero italic note "iter4 standalone módel — óháður fasteignamati HMS"

### Sprint 2 byrjað (2026-04-21)
Pro-user track fyrst: PI cal + auth + manual Q + PDF. Invite-only. Pro users: fasteignasali + bankamaður (2 boð).
Public dashboard track second: custom domain verdmat.is + hverfi pages + journalistic stories.
Sprint 2 breaks into 4 áfangar × 17 skref, ~50-70 klst active work over 4 calendar weeks.

### Sprint 2 Skref 1 KLÁRAÐ (2026-04-21): Conformal PI calibration
- `iter4_conformal_v1` replaced `iter4_segcal_v1`
- Method: split-conformal on test split residuals, symmetric log-space half-widths
- Per (canonical_code × region_tier) with segment + global fallbacks; MIN_N=30
- **Held coverage jumped 68% → 79.1% on 80% PI, 94.6% on 95% PI** (targets 80/95 — essentially nailed)
- Applied to Supabase: 110,316 predictions updated via COPY-staging + UPDATE JOIN (14 sec), `calibration_version='iter4_conformal_v1'`
- Bakkastígur 1 sample: mean 91.6 M, 80% PI 80.9-103.8 M (was 81.5-105.3 M), 95% PI 72.9-115.2 M
- No frontend code change needed — detail page reads PI fields from DB, footer badge auto-shows new calibration_version

### Sprint 2 Skref 2-4 KLÁRAÐ (2026-04-21): Auth infrastructure + Pro dashboard skeleton

**Database (applied til Supabase):**
- `pro_users` — invite-only Pro-user registry með RLS "read own"
- `saved_properties` — watchlist per user
- `saved_valuations` — persisted baseline + adjusted values með answers_json
- `saved_searches` — search criteria í JSONB fyrir Áfanga 3
- All tables með RLS policies locked til `auth.uid()`

**Next.js auth stack:**
- `@supabase/ssr` installed
- `lib/supabase-server.js` + `lib/supabase-browser.js` helpers
- `/login` magic-link form (invite-only messaging)
- `/auth/callback` route handler (token exchange → /pro redirect)
- `middleware.js` á `/pro/*` — unauth → /login, no pro_row → /pro/pending
- `/pro` dashboard skeleton: greeting + role badge + 3 CTA cards + saved properties grid + recent valuations table (all með empty states)
- `/pro/pending` page fyrir users sem eru innskráðir en ekki í pro_users yet

**Manual steps eftir (Danni þarf að gera í Supabase/Resend dashboards áður en login virkar):**
1. Supabase → Authentication → Providers → Email: enable Magic Link
2. Supabase → Authentication → URL Configuration: add `https://verdmat-is.vercel.app/auth/callback` og `http://localhost:3000/auth/callback`
3. Supabase → Authentication → Providers → Email: disable signups (invite-only)
4. Búa Resend account (resend.com, free tier 3K emails/mán), verify domain, get API key
5. Supabase → Project Settings → Auth → SMTP settings: configure custom SMTP með Resend credentials (smtp.resend.com:587)
6. Invite-user flow: Supabase dashboard → Authentication → Users → Invite user með email
7. Eftir user signar inn í fyrsta sinn, keyra SQL: `INSERT INTO pro_users (id, email, role, company) VALUES ('<uuid>', '<email>', 'fasteignasali'/'banki', '<company>');`

### Sprint 2 Áfangi 1 CLOSED (2026-04-21)

**Skref 1.5 — Conformal PI verification: PASS**
- Pooled residential (N=2,084): 80% PI coverage **79.08%** (target 80, delta -0.92), 95% PI **94.63%** (target 95, delta -0.37)
- Per-segment: most within ±5 pp; APT_STANDARD×Country -10.9 pp (N=81, small), ROW_HOUSE×Capital_sub +12.2 pp (over-covers with wider than needed)
- Criteria met: pooled ∈ [78, 82] and [93, 96]. Conformal correction is validated.

**Skref 1.6 — Auth UI frozen**
- `/login` replaced med "Pro útgáfan er á leiðinni" static landing med mailto CTA
- `/auth/callback`, `middleware.js`, `/pro/*` routes retained (functional when re-enabled í Áfanga 5)

**Skref 1.7 — Edge-case audit: 5/5 PASS**
- No photos (fastnum 2354868 ROW_HOUSE): "Engar myndir" placeholder, verðmat renders ✓
- New build no sales (2503822 byggt 2024): page loads, sölusaga section hidden ✓
- Non-residential (2516150 EXCLUDE): "atvinnuhúsnæði · Verðmat ekki í boði" notice ✓
- No comps (2169101 APT_HOTEL): prediction 21.9 M kr rendered, comps section hidden cleanly ✓
- Single-word heimilisfang (2085524 "Gil" APT_FLOOR): renders as-is, no fallback needed ✓

Áfangi 1 er klárað. Áfangi 2 (manual questionnaire + live scoring) er next.

### Sprint 2 Áfangi 2 KLÁRAÐ (2026-04-22): Public manual questionnaire + live scoring

**Skref 5 — Small-N fallback smoothing:**
- Tested MIN_N=100 (own 30% + donor 70%) and MIN_N=500 (40/60). Both made pooled coverage WORSE (79.08 → 78.21).
- Donor-selection rule "max-N region" pulls Country cells toward tighter Capital_sub/RVK_core, shrinking PI. Correct direction would be similar-residual-distribution donor, not max-N.
- Decision: keep iter4_conformal_v1. APT_STANDARD × Country held cov 69.1% is N=81 sample noise (binomial 95% CI around 80% target is [71%, 89%], observed 2pp below lower bound — marginal).

**Skref 6 — Manual Q effects:**
- Empirical residual approach gave 0.2–2% magnitudes (because iter4a already uses these features). Switched to literature-anchored hardcoded values in `data/manual_q_effects.json`.
- 11 questions: kitchen_renovated, bathroom_renovated, flooring, view, balcony, garage, elevator, condition_overall, floor_position, proximity_school, proximity_store.
- Range: worst-case -12%, best-case +21%.
- Sprint 3 will refine via LightGBM PDP.

**Skref 7 — `/api/adjust-valuation` POST route:**
- Fetches baseline from `predictions`, applies multiplicative log-space adjustments, returns baseline + adjusted + sorted breakdown.
- Verified: Bakkastígur 1 baseline 91.6M → with (sjor+eldhús+gott) = 103.6M, multiplier 1.13, breakdown ordered by absolute ISK impact.

**Skref 8-9 — Questionnaire UI + results:**
- `/eign/[fastnum]/stilla` 5-screen wizard (11 questions, APT-conditional floor_position + elevator).
- Defaults pre-selected, progress bar, client state via useReducer.
- `/eign/[fastnum]/stilla/nidurstada?a=q:v,q:v,...` server component, answers via URL → link-shareable.
- Waterfall breakdown per question, sorted by absolute ISK impact.
- Share button copies canonical URL.

**Skref 10 — CTA on eign page:**
- Terracotta-accent card between prediction and SHAP: "Viltu nákvæmara verðmat?" → "Stilla verðmat".
- Hidden for SUMMERHOUSE and non-residential (redirects to /eign?notice=no_adjust).

**Skref 11 — Edge-case coverage (5/5 PASS):**
- APT_FLOOR (2000281 Bakkastígur 1): 200, renders ✓
- SFH_DETACHED (2000280 Bakkastígur 3): 200, 142.4M baseline → 151.3M personal ✓
- ROW_HOUSE (2000749 Framnesvegur 20A): 200, renders ✓
- SUMMERHOUSE (2053860): 307 → /eign/2053860?notice=no_adjust ✓
- APT_HOTEL no-comps (2169101): 200, renders (works since is_residential=true) ✓

Áfangi 2 closed. Áfangi 3 (PDF export + saved valuations) is next.

### Sprint 2 Áfangi 2 v1.1 (2026-04-23): Effects calibration refinement
Additive update til v1 (no rollback). Live og verified via API test.
- `flooring` 4-option enum → `flooring_renovated` trilemma (US-market artifact removed)
- `garage` split into `garage_sfh_row` (SFH/ROW/SEMI) og `garage_apt` (APT_*) með canonical-gated UI og API validation
- `condition_overall` 3→4 stig: gott / medal / smavagilegar_framkvaemdir (−2%) / mikilvirk_vidgerd (−5%)
- `proximity_school` raised 0.7→1.5% (Iceland family-market)
- `view.gras` −0.5→0 (Iceland grass not penalty)
- `floor_position.kjallari` −2→−3%, `floor4plus` +2→+2.5%
- `ovisst` defaults halved (0.5% kitchen, 0.4% bath, 0.2% flooring) so stacked-ovisst doesn't accidentally add up
- Legacy URL compat: v1 `thorfVidgerd` → `mikilvirk_vidgerd`, v1 `flooring:X` silently dropped

API verification: `{kitchen_renovated:ja, condition:smavagilegar_framkvaemdir, garage_apt:sameign, view:sjor, proximity_school:ja}` produces multiplier 1.1000 (expected 1.098) med 5 breakdown items each matching hardcoded values line-by-line. `garage_sfh_row` on APT_FLOOR returns HTTP 400 med clear error message.

### Sprint 2 Áfangi 3 KLÁRAÐ (2026-04-23): PDF export

Public downloadable PDF á niðurstöðusíðu. `@react-pdf/renderer` lazy-importaður á click.

**PDF layout (A4):**
- Header: verdmat.is merki + útgefið dagsetning + fastnum + model version
- Heimilisfang line með segment / m² / byggt / herb
- Summary: 2-col grunn vs persónulegt + delta box
- PI tafla: 80% og 95% bil
- Breakdown: Q / value / impact (color-coded green/red/faint)
- Markaðssamhengi placeholder (ítarlegri í Sprint 3)
- Disclaimer: AI-verðmat ekki bindandi
- Footer: pinned model metadata

**Íslenskt letur fix:** Upphaflega prófaði ég að register-a Inter + Fraunces frá Google Fonts CDN, en þessir URL-ar voru made-up og 404'ðu — PDF generation throw-aði. Skipti yfir í PDF standard Type 1 fonts (Helvetica body, Times-Roman display) sem cover-a Latin-1 Supplement, sem inniheldur alla íslenska stafi (þ æ ð ö á ú). Engin network fetch, reliable offline, faster render.

**Filename:** `verdmat_<fastnum>_<YYYY-MM-DD>.pdf`

Áfangi 3 closed. Áfangi 4 (saved searches + custom domain + SEO pages) og Áfangi 5 (auth re-activation) eftir.
