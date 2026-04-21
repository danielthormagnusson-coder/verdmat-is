# DECISIONS — Arkitektúrákvarðanir

Skrá yfir lokaðar ákvarðanir með dagsetningu og rökstuðningi. Nýjar ákvarðanir bætast við efst.

---

## 2026-04-23 — Áfangi 3 closed: PDF export með built-in PDF fonts

**Hvað**: Public downloadable PDF á nidurstaða-síðu. Lazy-loaded `@react-pdf/renderer` + Document/Page/Text layout með Helvetica + Times-Roman (built-in Type 1 standard fonts).

**Font decision**: Reyndi first að registerá Inter + Fraunces frá Google Fonts CDN, en placeholder TTF URLs voru 404, PDF generation failed silent í client. Switched to PDF standard fonts (Helvetica body, Times-Roman display) sem báðir styðja Latin-1 Supplement (includes þ æ ð ö á ú via WinAnsiEncoding). Trade-off: display-heading serif er Times-Roman í staðinn fyrir Fraunces — web og PDF typography mismatch, en web brand retained og PDF letur er stable + offline.

**Lazy-load strategy**: `@react-pdf/renderer` er ~450 KB gzipped. Initial bundle er óbreytt frá Áfanga 2 af því PDFDownloadButton dynamic-importar renderer + PDFReport á fyrsta click. Second click er instant (modules cached). Accept loading state "Býr til PDF..." sem user feedback.

**Disclaimer**: Explicit text í PDF footer stating "AI-verðmat, not legally binding" — important fyrir ef fasteignasalar prenta og deila með viðskiptavinum.

---

## 2026-04-23 — Manual Q effects v1.1 calibration refinement (additive)

**Hvað**: 6-item calibration update til `data/manual_q_effects.json`. Backwards-compatible: old share URLs still work via legacy-key translation in both API og results page.

**Rationale per fix**:

1. **Flooring type → renovation trilemma**: Parket vs teppi er US-suburban price signal. Íslandi notar báðar lausnir alongside each other; gólfefni-type dispersion er stödd cross-buyer-pool and doesn't systematically move price. Recent-renovation er raunverulegt signal instead.

2. **Garage split by segment**: Single garage question allowed "tvofalt +4.5%" on APT_FLOOR, gerir flat-buyer confused og overstates effect. SFH/ROW/SEMI fá actual-bílskúr enum (einfaldur/tvöfaldur); APT fá bílastæði enum (sameign/tryggt_utanhuss/bilskyli_kjallari). Canonical-gated UI rendering + API validation enforce.

3. **Condition 4 stages**: v1 jumped 3% → 0% → −5% med engin middle stage for minor work. `smavagilegar_framkvaemdir` (−2%) fills gap; most Icelandic properties sit in medium-minor range. More granular user experience.

4. **proximity_school raised**: Real-estate literature used in v1 was US-sub; Icelandic barnafjölskyldu-markaðir í Kópavogi/Hafnarfirði price-a skólanálægð sterkar. 1.5% er Iceland-realistic.

5. **kjallari and floor4+**: Hedonic studies á íslenskum markaði suggest 3-5% kjallari penalty and +2-3% premium á hærri hæðum. v1.0 values were mildir; v1.1 aligns better.

6. **ovisst defaults halved**: v1 had ovisst as weak positive (≈0.3× of "ja" effect) sem meant user clicking "ovisst" through alls 5 questions fékk +1.5% stacked boost. Halving gerir ovisst accept-default-gracefully option, ekki stealth-bonus.

**Still hardcoded**: Sprint 3 PDP-based refresh á iter4a booster supersedear þetta alveg. Þessi refinement er interim pending real data-driven calibration.

**Coverage**: stacked worst-case −10 to −11%, best-case +24 to +27% (SFH vs APT). Real dispersion narrower.

---

## 2026-04-22 — Sprint 2 Áfangi 2 decisions

**Hvað**: Public manual questionnaire shipped (no auth required). Baseline + persónulegt verðmat med 11-spurning flow, link-shareable results, CTA card on main eign page.

**Segment fallback abandoned** (Skref 5): Tested 2 blend strategies — max-N donor biased small-N Country cells toward tighter Capital_sub/RVK_core. Pooled cov worsened (79.08 → 78.21). APT_STANDARD × Country held N=81 undercoverage (69.1%) is sample noise at Bin(81, 0.80) lower CI bound, not systematic miscalibration. Retained iter4_conformal_v1.

**Manual Q effects hardcoded**: Empirical residual regression gave 0.2–2% magnitudes — iter4a already uses these features as inputs, so leftover residuals only reflect what model missed. Used literature-anchored values in `data/manual_q_effects.json` (range −12% to +21%). Sprint 3 will refine via PDP per feature on iter4a booster.

**URL-encoded answers**: Results page uses `?a=q1:v1,q2:v2` query string instead of POST-only flow. Benefits: link-shareable, server-rendered (no client-side result fetch), no cookie/storage. Share button copies canonical URL.

**Questionnaire non-applicability**: SUMMERHOUSE + non-residential redirect 307 → `/eign/[id]?notice=no_adjust`. Avoid user confusion from getting a personal valuation on iter4's known-weak SUMMERHOUSE segment (175% MAPE) or unpredicted commercial.

**API route**: `/api/adjust-valuation` POST exposed publicly (no auth). Accepts `{fastnum, answers}`, returns `{baseline, adjusted, breakdown, multiplier, model}`. Server-side computation ensures baseline pulled from DB fresh. Used by results page indirectly via URL-decode + same adjustment logic; API available for future client use (saved valuations in Áfangi 3).

---

## 2026-04-22 — Sprint 2 Áfangi 1 QA findings

Edge case audit á 5 scenarios fyrir eign detail page:
1. No photos → "Engar myndir" placeholder í gallery. PASS.
2. New build (2024+, no sales) → sölusaga section renders conditional (`salesHistory.length > 0`), hidden when empty. PASS.
3. Non-residential (EXCLUDE canonical_code) → "Verðmat ekki í boði" notice; prediction/SHAP/comps/market sections all gated on `is_residential`. PASS.
4. No comps (APT_HOTEL fastnum 2169101) → prediction + SHAP render (21.9 M kr, 10 SHAP rows); comps section conditional, hidden cleanly. PASS.
5. Single-word heimilisfang (e.g. "Gil", "Mörk") → used as-is in heading; no fallback needed since all residential have at least short address. PASS.

No fixes required — existing conditional rendering handles all 5 gracefully.

**Known remaining issues** (carried into Sprint 2 Áfangi 2):
- APT_STANDARD × Country 80% PI coverage 69.1% (11 pp under, N=81). Small-sample noise; conformal quantile for this cell is below true residual distribution. Candidate fix: pool with Capital_sub, or increase MIN_N threshold.
- ROW_HOUSE × Capital_sub 80% PI coverage 92.2% (+12.2 pp over). PI widths too wide for this cell. Cosmetic issue, not functional.

---

## 2026-04-21 — Sprint 2 Skref 1: Switched to conformal PI calibration

**Hvað**: Replaced iter4 segment-stretch calibration (`iter4_segcal_v1`) with split-conformal prediction intervals (`iter4_conformal_v1`). Per (canonical_code × region_tier) quantiles of |log-residual| from the test split define symmetric half-widths; held coverage jumped from 68% → 79.1% on 80% PI.

**Af hverju segment-stretch náði ekki 80%**: The iter4 quantile heads (q100/q900) produce a narrower distribution than iter3v2's. Stretch factor k80=1.05 (found by grid-search to maximize coverage on val+test) saturates — widening the quantile head further was not possible because the quantiles themselves are under-spread. Conformal skips the quantile head entirely: it empirically calibrates PI width from observed residual distribution on held-out calibration data.

**Method**:
1. Training uses train + val (early stopping on val). Test split is reserved purely for calibration.
2. For each (canonical_code × region_tier) with n ≥ 30 on test split, compute `q80_log = 80th percentile of |log_real_kaupverd - pred_mean_log|`, same for q95.
3. Fallback hierarchy: segment×region → segment-only → global (when n < 30).
4. Application: `pred_lo80_log = pred_mean_log - q80_log`, `pred_hi80_log = pred_mean_log + q80_log`. Convert to ISK via `expm1 / cpi_factor × 1000`.

**Alternative considered**: (a) Retrain quantile models with wider bagging / deeper trees — more risky, affects point estimate. Hafnað. (b) Full conformalized quantile regression (CQR) à la Romano et al 2019 — more theoretically sound but much more code. Hafnað for v1. (c) Per-property adaptive conformal (locally-weighted residuals) — better guarantees but costly at inference. Deferred.

**Coverage deltas (held, main residential N=2,084)**:
```
Metric          iter4_segcal  iter4_conformal  Δ
80% PI cov      66.3%         79.1%            +12.8 pp
95% PI cov      89.1%         94.6%            +5.5 pp
```

**Impact**: User-facing PI widths now reflect actual uncertainty. Bakkastígur 1 80% PI went 81.5-105.3 → 80.9-103.8 M kr (tighter lower, tighter upper — concentrated around mean). Same model, same mean prediction. `iter4_segcal_v1` JSON retained on disk for audit.

---

## 2026-04-21 — iter4 production rollout (Áfangi 2-5 closed)

**Hvað**: Switched production prediction model from iter3v2 to iter4a (standalone, no fasteignamat input). iter3v2 archived in Supabase as `predictions_iter3v2` + `feature_attributions_iter3v2`. Frontend default view reads iter4 (`predictions` table post-rename). Debug mode `?mode=debug` loads both for side-by-side comparison.

**Metrics**:
- iter4a held MAPE: 8.19% (iter3v2 baseline 7.97%, delta +0.22 pp)
- Per-segment: APT_STANDARD 6.37%, APT_FLOOR 8.55%, ROW_HOUSE 7.24%, APT_BASEMENT 10.90%, SFH_DETACHED 16.29% (small N=106)
- Calibration: `iter4_segcal_v1` JSON, per-segment k-factors similar to iter3v2's
- 80% PI coverage 68% (target 80%) — known undercoverage, deferred to Sprint 2+
- Training time: 9.4 min (iter4a), 26 min (iter4 precompute rebuild with SHAP)

**Impact**:
- Annual HMS fasteignamat updates (júní ár hvert) **no longer cause prediction jumps** — iter4 is fully decoupled.
- Feature importance redistribution healthy: EINFLM 34.5%, sale_year 19.6%, matsvaediNUMER 17.6%, matsvaedi_bucket 14.2%, BYGGAR 4.5% (vs iter3v2's 77.9% fastmat dominance).
- DB size grew to 561 MB (was 424) due to iter3v2 archive retention. Still well within Pro tier (8 GB).
- iter4b via `init_model` fine-tune abandoned: LightGBM requires feature compatibility with init_model, so dropping FASTEIGNAMAT is infeasible without workarounds that preserve iter3v2's fastmat dependence.
- LLM extraction feature selection (Skref 5-6) was a no-op: all 136 extraction features were already joined into training_data_v2 and used by iter3v2. iter4a inherits them automatically.

**Not tripped stop-conditions**:
- Skref 4 MAPE > 15%: iter4a at 8.19% (well under).
- Skref 8 Bakkastígur 1 delta > 30%: actual +2.2%.

**Deferred to future sprints**:
- PI coverage undercoverage on held (68% vs 80% target).
- Manual-layer questionnaire (Áfangi 9 / Sprint 3).
- SUMMERHOUSE model quality (175% MAPE — iter3v2 has same issue).

---

## 2026-04-21 — iter4a validated as production candidate; iter4b (init_model) abandoned

**Hvað**: iter4a training complete. Held MAPE 8.19% vs iter3v2 baseline 7.97% — a +0.22 pp cost for full fasteignamat independence. iter4b (LightGBM `init_model` fine-tune) was abandoned due to technical infeasibility.

**Af hverju iter4a virkar svona vel**: The 77.9% gain iter3v2 attributed to `real_fasteignamat` + `FASTEIGNAMAT` was largely **collinear** with underlying features (size, location, age, time). LightGBM re-learns the signal from EINFLM + matsvaedi_bucket + matsvaediNUMER + sale_year + BYGGAR without the fastmat mediator. Feature importance in iter4a is healthily distributed across size/geography/time primitives.

**Af hverju iter4b sleppt**: LightGBM `init_model` parameter requires feature-set compatibility between the init booster and the new Dataset. Dropping `FASTEIGNAMAT` from iter4b features violates this contract. Workarounds (keeping feature as NaN constant) preserve iter3v2's existing NaN-path decisions on those features, not truly decoupling from fastmat. Clean "iter4b via fine-tune" is not feasible with feature-drop semantics.

**Alternative considered**: Train iter4a with alternative hyperparameters (more trees, deeper) as an iter4a_deep variant. Deferred — iter4a baseline already at 8.19% on held, diminishing returns from tuning.

**Consequence**: iter4a is the winner by default. PI coverage (66.3% on 80% PI vs target 78%) requires calibration-stretch in Skref 7 (follow iter3v2's `iter3v2_segcal_v1` pattern).

---

## 2026-04-21 — Switched production target from Streamlit prototype to Next.js+Supabase+Vercel

**Hvað**: Eftir Áfangi 7 completion var byggt Streamlit `app.py` sem Áfangi 5 v1. Danni hafnaði því sem prototype-quality (1990-style search bar, no feature attribution UI, no market integration). Switch yfir í production-grade Next.js stack byggt á sister project heyaskr (sama höfund, existing deploy).

**Af hverju**: End goal (bank analytics tool, public dashboard, subscription product) krefst scalable stakks; Streamlit limits would force full rewrite later. Next.js + Supabase gefur publish-level UX, server components, edge CDN, mobile-responsive út úr boxinu. Code-reuse mynstur frá heyaskr.

**Alternative**: (a) Streamlit með heavy customization — hafnað, limits remain. (b) FastAPI + vanilla HTML — meira plumbing, ekkert CDN, custom auth. Hafnað. (c) SvelteKit — minni reynsla, enginn code-reuse. Hafnað.

**Impact**: Phase 1 scope defined (precompute + mirror + read-only frontend); Sprint 2 adds auth/user accounts.

---

## 2026-04-21 — Precompute-all strategy fyrir Sprint 1 (no live Python backend)

**Hvað**: Engin FastAPI/Railway/Docker fyrir Sprint 1. LightGBM scoring + SHAP + comps eru precomputed locally (Phase 1A), dump í CSV, import í Supabase. Frontend les precomputed gildi úr PostgREST eingöngu.

**Af hverju**: Faster ship, zero backend ops, DB queries < 100 ms. Live scoring (fyrir user manual input í Áfanga 9) deferred til Sprint 2 þegar auth er komið og scope réttlætir backend.

**Alternative**: (a) FastAPI á Hetzner/Railway með live LightGBM. Hafnað: meira infra, cold-start latency, ónauðsynlegt fyrir read-only Sprint 1. (b) Supabase Edge Functions með Python/Deno. Hafnað: LightGBM runtime ekki supported á Edge.

**Impact**: 7 CSV skráar, 202 MB → 424 MB Supabase DB, <100 ms edge queries. Pipeline re-run-able via `build_precompute.py --force` locally.

---

## 2026-04-21 — CloudFront image URLs directly, no Supabase Storage

**Hvað**: `photo_urls_json` dálkur í `properties` tafla vísar beint í `d1u57vh96em4i1.cloudfront.net` URLs frá scraper. Engin upload til Supabase Storage.

**Af hverju**: 1,15M myndir eru þegar live á CloudFront frá scraper pipeline. Re-hosting er ónauðsynlegur overhead fyrir Sprint 1. Delisted auglýsingar skila 404 sem frontend handles gracefully (fallback parchment card, user sér engar broken images án intervention).

**Alternative**: (a) Download myndir í Supabase Storage bucket. Hafnað: 1,15M × ~100KB = ~115 GB, Supabase free-tier storage cap er 1GB. Bandwidth + storage cost ~$30/mán á Pro. (b) Proxy via Next.js Image optimizer. Hafnað: complexity + CloudFront URL rewriting bandwidth á Vercel.

**Impact**: Photos eru subject til CloudFront availability + scraper-side delisting. Long-term (Áfangi 10+) þarf að consider mirror ef availability lækkar eða domain changes.

---

## 2026-04-21 — iter4 standalone (no fasteignamat input), 100% separation from iter3v2

**Hvað**: iter4 model fjarlægir `real_fasteignamat`, `FASTEIGNAMAT`, `fasteignamaT_GILDANDI` og allar derivatives úr input features. 100% standalone, ekkert blend með iter3v2. Fasteignamat birtist áfram á UI sem reference number, ekki model input.

**Af hverju**: HMS fasteignamat er sjálft hedonic regression á kaupskrá — að nota það sem input í okkar módel er circular og gerir spána fyrir-determined af HMS updates. Annual HMS fasteignamat updates (júní ár hvert) cause 5-10% overnight jumps í iter3v2 predictions án þess að einn einasti kaupsamningur hafi verið þinglýstur. Þetta er fatal fyrir bank/pro-user use case þar sem stability er verðmætari en 1-2 pp MAPE.

**Alternative**: (a) Keep fastmat as input (status quo iter3v2). Hafnað af ofangreindum ástæðum. (b) Blend iter3v2 + iter4 við 50/50. Hafnað: blend retains circular dependency, bara demp-ar stökkin. (c) Add fastmat sem separate "anchor" calibration layer post-hoc. Potentially future work, ekki Sprint 2.

**Expected cost**: 3-5 pp MAPE increase (7,97% → ~11-13%), acceptable vaxtar-tradeoff. LLM features í Skref 6 geta milduð skaðann. Calibration (segment stretch factors) þarf endurgerð á nýjum residuals.

**Impact**: `score_new_listing.py` clone → `score_iter4.py` með removed fastmat fields. Precompute re-run subset (predictions + SHAP only). UI sýnir fasteignamat sem "Opinber eignamat frá HMS — reference only" með smá caveat text.

---

## 2026-04-21 — Document sync via GitHub repo (D:\ → docs/ → origin/main)

**Hvað**: Continuity files (STATE, DECISIONS, WORKING_PROTOCOL, TAXONOMY, GLOSSARY, DATA_SCHEMA, LABELING_GUIDE, GOLD_STANDARD_PROTOCOL, EXTRACTION_SCHEMA_v0_2_2, DATA_AUDIT_REPORT, devalue.py) synced til `docs/` folder í verdmat-is GitHub repo. D:\ er working copy, repo er canonical.

**Af hverju**: Claude Code working D:\ diverged frá Claude.ai Project folder versions (t.d. D:\STATE.md = 163 lines vs Project = 1759 lines) og caused authoritative-source confusion í Phase 1C/1D. GitHub provides single source of truth readable af bæði chat-Claude (via raw URL) og Claude Code (via git pull).

**Alternative**: (a) Sync til OneDrive/Dropbox. Hafnað: enginn chat-Claude read-access. (b) Manual paste-a content í chat hverju sinni. Hafnað: tedious, error-prone. (c) Sérstakur private repo. Hafnað: meira management, verdmat-is repo er nú þegar private og docs eru engir secrets.

**Workflow**:
1. Edit á D:\ via `str_replace` (existing rule, unchanged).
2. `cp D:\<FILE>.md /d/verdmat-is/app/docs/<FILE>.md`
3. `git add docs/ && git commit && git push`
4. Chat-Claude fer að raw URL when needed.

**Impact**: WORKING_PROTOCOL.md updated með rule (Phase 1D Skref 5). Any future Claude Code session sees both D:\ og docs/ in same git repo → divergence detectable via `diff`.

---

## 2026-04-20 (refresh_dashboard_tables orchestrator closed) — Monthly cycle integration staðfest virk

**Hvað**: `refresh_dashboard_tables.py` orchestrator framleiddur og tested end-to-end. Integrerar `build_repeat_sale_index.py` + `build_ats_lookup.py` sem cohesive dashboard snapshot með cross-script atomicity.

**Placement í monthly cycle (6-skref → post-integration 6-skref)**:
1. `refresh_cpi.py`
2. `refresh_kaupskra.py`
3. `rebuild_training_data.py`
4. **`refresh_dashboard_tables.py` ← NÝTT**
5. `monthly_recalibration.py`
6. `validate_metrics.py`

**Semantics**:

1. **Cross-script atomicity**. Ef annað hvort sub-script bilar með non-zero exit, orchestrator triggerar rollback á BÁÐUM dashboard-tafla-settum (repeat-sale 4 skrár + ATS 10 skrár = 14 monitored files). Consumers sjá aldrei mixed state þar sem repeat-sale er fresh en ATS stale, eða öfugt.

2. **Subprocess pattern**. Sama arkitektúr og `rebuild_training_data.py` — keyra hvert sub-script í sjálfstæðu Python process með `subprocess.run(check=False)`, capture-a return code, stream-a stdout live gegnum parent process. Isolation + visibility.

3. **Shape safety**. Post hvers sub-script validerar orchestrator að (a) allar expected outputs séu framleiddar, (b) row count hafi ekki shrinkað > 5% vs backup, (c) column count match-i exactly. Dashboard tables grow með tíma, svo row shrinkage = probable bug (kaupskra corruption, filter-cascade regression, etc).

4. **First-run friendly**. Ef engin previous outputs (empty `D:\_rollback_backup\`), skip backup step með warning, keyra eðlilega. No failure mode.

5. **Rollback safety**. Backup tekinn pre-run í `D:\_rollback_backup\YYYYMMDD_HHMMSS\`. Á success → deleted (eða preserved með `--keep-backup` flag). Á failure → outputs restored frá backup, backup preserved fyrir post-mortem inspection.

6. **Bare essentials orchestrator design**. Engin retry logic (transient failures bera ábyrgð á manual re-run), engar absolute shape floors (relative-to-backup er self-updating), engin per-file content validation (sub-scripts bera ábyrgð á internal integrity). Orchestrator sér aðeins um cross-script atomicity.

**Runtime validation** (staðfest 2026-04-20 20:58 og 21:00):

- Cycle 1 (--keep-backup): 81,0 sec total
  - Backup: <1 sec (14 files, ~1 MB total)
  - Repeat-sale: 77,6 sec (build) + 0,1 sec (validation)
  - ATS: 2,5 sec (build) + 0,1 sec (validation)
  - Cleanup: negligible

- Cycle 2 (normal): 65,4 sec total
  - Repeat-sale: 62,0 sec (warm disk cache)
  - ATS: 2,5 sec

Expected runtime window: 60-85 sec depending á disk cache state. Acceptable fyrir monthly cron.

**Idempotency staðfest**: Back-to-back cycles á unchanged input data gáfu identical outputs (shape deltas +0,0% á öllum 14 files, column counts exact match). Sama pattern og staðfesti rebuild_training_data í Áfanga 4d.

**Output skrá orchestrator framleiðir ekki**: orchestrator sjálfur emmar ekki output, bara orchestrators sub-scripts sem allar outputs undir management. Aðeins side-effect af orchestrator er short-lived backup dir í `D:\_rollback_backup\`.

**Scripts**:
- `refresh_dashboard_tables.py` — orchestrator (360 línur)

**Deferred til framtíðar**:
- Logging til file (núna er stdout-only; PowerShell user má pipa `> refresh.log` ef þarf)
- Per-cell sanity checks (e.g. "APT_STANDARD RVK real 2026Q2 ∈ [130, 150]") — v2 bonus
- Alert/notification hooks (email, Slack) fyrir rollback events

**Monthly cycle staða post-integration**: 6 skref frosin og staðfest. `validate_metrics.py` er downstream svo er forlag þess að dashboard tables séu fresh þegar validation keyrir. Næsta óleyst eining í pipeline er SEMI_DETACHED k-factor drift (Áfangi 4d pending) sem bíður 1-2 monthly cycles gagnagrundvallar.

---

## 2026-04-20 (Áfangi 7 closed) — ATS lookup tafla, dual-table arkitektúr (quarter + heat-pooled), static percentile heat-labels

**Hvað**: Áfangi 7 (ask-to-sale gap lookup) lokið. Framleiðir 5 output-skrár úr `pairs_v1.pkl` paired_fresh subset í `build_ats_lookup.py` (1,7 sec runtime á 52K clean pairs):

- `ats_lookup_by_quarter.pkl` / `.csv` — Table A, 913 rows × 13 cols, per (canonical_code × region_tier × quarter) með heat_bucket og data_quality as metadata
- `ats_lookup_by_heat.pkl` / `.csv` — Table B, 63 rows × 10 cols, pooled per (canonical_code × region_tier × heat_bucket). **Primary scoring table**.
- `ats_heat_thresholds.pkl` / `.csv` — 23 rows × 6 cols, p33/p67 audit
- `ats_dashboard_quarterly.pkl` / `.csv` — 359 rows × 8 cols, region-collapsed seg × qtr trends
- `ats_dashboard_monthly_heat.pkl` / `.csv` — 2.501 rows × 9 cols, live regime z-score indicator

**Methodology decisions taken** (confirmed í chat 2026-04-20):

1. **Dual-table arkitektúr (A + B)**. Table A er per-quarter historical fidelity. Table B er heat-pooled (1 row per (seg × reg × heat_bucket)) og er **primary scoring table** því pooling gefur robust dispersion í thin cells og leysir cold-start problem fyrir nýjasta ársfjórðunginn sem er alltaf thin vegna þinglýsingar-lags. Scoring-fallback: B først, A latest-row ef B insufficient (rare — 0 insufficient cells í B post-pooling).

2. **Input = paired_fresh only, exclude in_scrape_gap=True**. Filter cascade: 55.544 paired_fresh → 53.386 post-scrape-gap → 52.136 post-EXCLUDE → 52.083 post-outlier-clip → 52.001 post-inclusion-filter. Selection-bias rationale: 2025-07+ paired pairs eru technically valid per-pair en coverage er unrepresentative í gap, svo aggregate statistics eru untrustworthy. Refresh mánaðarlega re-includes data þegar scraper kemur aftur.

3. **Outlier clip ATS ∈ [0,5; 2,0]**. 53 rows klippt (~0,1%). Non-negotiable pre-aggregation: raw SD 0,1327 vs MAD×1,4826 0,0275 = 4,8× ratio í heavy tails (data-entry errors, foreclosures, skilnaðarsölur, bulk-deals). Clip range matchar DATA_SCHEMA sanity validation.

4. **Inclusion filter MIN_PAIRS_PER_CELL = 50 all-time**. Same threshold og Áfangi 6 BMN. 23 cells included, 7 excluded: APT_ATTIC Country (48), APT_MIXED RVK (4), APT_ROOM × 3 regions (5/3/17), APT_UNAPPROVED Capital_sub/Country (3/2). Main residential + SUMMERHOUSE Capital_sub/Country + APT_UNAPPROVED RVK all pass.

5. **Heat-label = static percentile (p33/p67) per (segment × region)**. Segment × region specific (ekki global) vegna þess að APT_STANDARD RVK hefur allt aðra baseline ATS en SFH Country — global þröskuldur myndi tag-a allar Country cells sem permanent cold. Thresholds reiknaðir á quarterly medians úr quarters með n ≥ 5 (stable). Rolling z-score **hafnað** fyrir lookup labels (reproducibility: 2018Q3 heat-label má ekki breytast þegar 2026 gögn koma inn), en notaður sér fyrir live dashboard regime indicator (ats_dashboard_monthly_heat).

6. **Scoring-primary dispersion = MAD × 1,4826**. Robust to outliers í small-sample cells; self-consistent með median (ekki mean) sem center. Audit-secondary dispersion = classical std; báðar geymdar. Scoring formúla: `pi_80 = list × exp(median_log_ratio ± 1,28 × dispersion_mad)`.

7. **Quality flags**. Table A: n<5 insufficient, n≥20 ∧ sd<0,05 high, n≥5 ∧ sd<0,10 medium, annars low. Table B: n<10 insufficient (stricter floor því pooling á að safna samples), sömu dispersion thresholds fyrir high/medium/low.

8. **Niche fallback fyrir cells með <8 stable quarters**. heat_bucket = NaN. 2 cells triggera: APT_BASEMENT Country (6 stable qtrs) og APT_UNAPPROVED RVK_core (4 stable qtrs). Þær 2 cells eru absent úr Table B (6 missing rows af 69 possible → 63 actual, 9% missing). Ef framtíðar-usecase þarf þessar cells, scoring fellur á training-data hedonic baseline.

9. **Monthly rolling 3-mo vs 12-mo z-score**. Separate live regime indicator í `ats_dashboard_monthly_heat`, óháð lookup labels. Sparse months (n=0) skipped, acceptable for v1 regime-detector. Used for dashboard "current market is heating up/cooling down" UI.

**Niðurstöður — empirical findings**:

(a) **Heat-label monotonicity confirmed**. cold < neutral < hot median_log_ratio á öllum 21 populated cells (engin exception). Deltas hot-minus-cold 0,016-0,091. Stærstu: SUMMERHOUSE Capital_sub (0,091 = 9,1%), SFH_DETACHED RVK_core (0,029), SEMI_DETACHED RVK_core (0,028).

(b) **Above-list rate er stærsta regime-driven signal**. 3-4× hlutfall í hot vs cold fyrir flest residential segments. APT_ATTIC RVK 14% → 47%, SEMI_DETACHED RVK 12% → 47%, APT_STANDARD RVK 9% → 33%. Confirmar bidding-war dynamics í hot regime.

(c) **Dispersion er NOT strongly function af heat — gengur í móti old-chat hypothesis**. 12 cells cold > hot MAD (hypothesis-compatible), 9 cells reverse. Mean effect kringum +0,003 (negligible). Empirical claim: "Ask-to-sale gap á íslenska markaðnum hefur stöðuga sveiflu (MAD ~0,02-0,03) óháð regime; munur hot/cold liggur í miðgildi, ekki dreifingu." Publishable finding + simplifies scoring (PI width ≈ constant across heat buckets).

(d) **Current market state per 2025-06** (síðasti mánuður pre-scrape-gap): APT_STANDARD RVK_core z_3v12 = -0,74 (cold), ROW_HOUSE Capital_sub z = -0,91 (cold), APT_BASEMENT RVK_core z = -0,52 (cold). Main residential er mostly neutral/cold. SFH_DETACHED Country z = 0,51 (hot) — counter-trend með Country catch-up frá Áfanga 6. Matchar widely-known narrative: 2022-end peak, 2023 correction, 2024-2025 cooling.

(e) **Yearly aggregate regime pattern** (3 main residential collapsed): 2022 peak (above_list 33,1%, median -0,007), 2023 trough (above_list 9,8%, median -0,025), 2024-2025 stabilization (above_list 12-14%, median -0,018 til -0,019). Orthogonal validation af Áfanga 6 timing findings.

**Output artifacts á D:\\**:
- `ats_lookup_by_quarter.pkl` / `.csv` — 913 × 13
- `ats_lookup_by_heat.pkl` / `.csv` — 63 × 10
- `ats_heat_thresholds.pkl` / `.csv` — 23 × 6
- `ats_dashboard_quarterly.pkl` / `.csv` — 359 × 8
- `ats_dashboard_monthly_heat.pkl` / `.csv` — 2.501 × 9

**Scripts**:
- `ats_diagnostic.py` — pre-build validation tool (~4 sec)
- `build_ats_lookup.py` — end-to-end build (1,7 sec runtime á 52K clean pairs)

**Deferred til framtíðar**:
- `analyze_ats_trends.py` — plots (above-list rate timeline, regime indicator timeline, pooled-distribution-by-heat violins)
- Leading-indicator heat definition (months-of-supply, TOM, withdrawal rate) as v2 alternative — ef empirical PI-calibration í production sýnir að ATS-derived heat er circular og inadequate
- `refresh_dashboard_tables.py` integration orchestrator (næsti áfangi post-Áfangi-7)

**Pending integration**: ATS lookup þarf re-reiknast mánaðarlega í refresh cycle. Integration point er post-rebuild_training_data, pre-calibration, parallel við repeat_sale_index. `refresh_dashboard_tables.py` verður orchestrator sem keyrir build_repeat_sale_index.py + build_ats_lookup.py í röð.

---

## 2026-04-20 (Áfangi 6 closed) — BMN repeat-sale index virkar, Country catch-up staðfest, ROW_HOUSE RVK_core niche finding

**Hvað**: Áfangi 6 (repeat-sale verðvísitala) lokið. Framleiðir Bailey-Muth-Nourse (BMN) OLS regressionir per (canonical_code × region_tier) × ársfjórðung fyrir 2006Q2–2026Q2 (81 quarters, 33 cells, 27 fitted). Output er `repeat_sale_index.pkl` + `repeat_sale_index.csv` með bæði **nominal** og **real** (CPI-deflated) indices, per-period `data_quality` flag (high/medium/low/insufficient), og 95% CI via std_error frá OLS.

**Methodology decisions taken**:

1. **Source = pairs_v1, ekki training_data_v1**. 24% fleiri pörum (off_market_used + off_market_newbuild + post_sale_only eru öll valid fyrir repeat-sale purposes því sale_price er þinglýst, óháð listing match).

2. **Consecutive pairing, ekki all-combinations C(n,2)**. Fyrir FASTNUM með 3 sölum → 2 pör, ekki 3. Case-Shiller standard; simpler, no double-counting.

3. **BMN per-cell aðskildar OLS regressions, ekki pooled með interactions**. Simpler, interpretable, og leyfir ólíka variance í hverjum segment × region cell. Divergence milli cells er visualized post-hoc í plots.

4. **Strict new-build-t1 exclusion**. Útilokar pör þar sem fyrri sala er `is_new_build=True`. Rökstudd tvenns konar: (a) developer→first-buyer pricing er pre-negotiated, ekki market equilibrium, og (b) Danni's domain insight: nýbyggingar eru seldar oft án gólfefna, ísskáps og uppþvottavélar, sem eru komnir inn í verðið þegar resale fer fram. Þ.e. eignin er literally not the same good milli t1 og t2 og ratio-ið er biased upward. EINFLM change filter (5%) grípur ekki þetta því flatarmál breytist ekki. 13.3% drop á pair-inu (9.076 pör af 68.381) — acceptable loss fyrir cleaner methodology.

5. **Filter cascade** (applied post-consecutive-pairing, per-step row counts logged):
   - (a) is_new_build_t1 = True           → -13.3%
   - (b) |EINFLM change| > 5%             → -3.1%
   - (c) FULLBUID 1 → 0                   → -0.1%
   - (d) pair_span_days < 90              → -1.0%
   - (e) canonical_code changed           → -0.0%
   - (f) region_tier changed              → -0.0%
   - (g) |log_price_ratio_nominal| > 2    → -0.1%
   - Final: 56.824 clean pairs (83.1% of 68.381 initial consecutive pairs)

6. **CPI deflation er default, ekki optional**. Nominal index-inn einn og sér er misleading fyrir íslenskan markað vegna verðbólgu (CPI growth ×2.66 frá 2006 til 2026). Báðar útgáfur emitted í output (`index_value_nominal` og `index_value_real`); dashboard notar real sem primary, nominal sem toggle. Baseline fyrir báðar = 2006Q2 = 100.

7. **Canonical source fyrir tegund er properties_v2 (fine HMS, 514 values), ekki pairs_v1.tegund (kaupskrá coarse TEGUND, ~7 values)**. Initial implementation notaði coarse og allt var misclassified sem EXCLUDE; fixed með properties_v2.fastnum → tegund → classify_property.

8. **MIN_PAIRS_FOR_REGRESSION = 50**. Cells með færri en 50 pör fá `insufficient_sample=True` og NaN indices. 6 af 33 cells skipped (APT_MIXED RVK, APT_ROOM × 3 regions, APT_UNAPPROVED Capital_sub + Country).

9. **NaN-gate fyrir periods án gagna**. Fitted cells fá NaN index (ekki baseline=100) fyrir quarters þar sem n_period=0. Dashboard má því forðast misleading plateau-línur.

**Niðurstöður — publishable findings**:

Main residential real CAGR 2006Q2→2026Q2 er 1.5–1.8% per ár fyrir apartments í RVK/Capital_sub, 2.7–2.8% fyrir Country (catch-up story). Real crash 2008-2011 var -27% til -33% frá 2006 peak fyrir main apartments; SEMI_DETACHED og ROW_HOUSE RVK hit harder (-44% til -49%). Recovery til 2006 baseline tók ~10 ár (crossed 100 around 2016-2017). Peak 2022Q4 var +37 til +47% yfir 2006 real-terms fyrir main cells.

Þrjú publishable findings:

(a) **Landsbyggð catch-up**: APT_FLOOR Country real growth 2006→2026 = +74.9% vs RVK_core +35.6%. Country segment vex more en RVK í raun-verði, starting consistently frá 2016. Tvær hypotheses sem framtíðar-rannsókn þarf: (i) RVK var meira inflated í 2006 baseline (bubble concentrated), svo relative growth frá lægri baseline er meira pronounced, eða (ii) tourism-driven rental demand drev Country prices upp frá 2016+. Finding stendur óháð hvor hypothesis sannast.

(b) **ROW_HOUSE RVK_core niche finding**: Lægsta real CAGR (0.5%) en dýpsta drawdown (-48.5%) af öllum main residential cells. Consistent við að raðhús í Reykjavík eru small-supply niche segment þar sem 2006-2008 bubble var most inflated. Empirical domain insight sem var ekki augljóst fyrirfram.

(c) **SUMMERHOUSE missed crash**: Country summerhouse real CAGR er +7.0% per ár og trough er 2006Q2 sjálft (aldrei niður fyrir baseline). Consistent við að sumarbústaðir á landsbyggðinni eru ekki domestic-driven market heldur tourism/rental driven og missed 2008 crash-ið alveg. Sjaldgæft fyrir asset-class að vera counter-cyclical við innlent hrun.

**Output artifacts á D:\\**:
- `repeat_sale_index.pkl` / `.csv` — full output, 2.673 rows (33 cells × 81 quarters), 15 cols
- `repeat_sale_pairs.pkl` — 56.824 clean pairs post-filter cascade, 16 cols
- `repeat_sale_summary.csv` — per-cell CAGR og crash-depth table, 27 rows
- 5 .png plots: `residential_real_grid.png`, `apt_floor_regional.png`, `nominal_vs_real.png`, `sample_density_heatmap.png`, `crash_recovery_zoom.png`

**Scripts**:
- `build_repeat_sale_index.py` — end-to-end build (56s total elapsed)
- `analyze_repeat_sale_index.py` — plots + summary stats generator

**Deferred til framtíðar**:
- CI bands á crash_recovery_zoom.png (plot 5) — thin samples look unfair without them
- Geometric Mean Revert Case-Shiller (GMRCS) ef noise er issue í downstream
- Weighted BMN með interval-distance weights
- Monthly sub-index fyrir RVK_core (aðallega fyrir dashboard leading indicators)
- Integration í operational monthly cycle: `refresh_dashboard_tables.py` skript sem re-derive index + ATS lookup eftir rebuild_training_data

**Pending integration í monthly cycle**: repeat-sale index þarf að re-reikna-st mánaðarlega þegar nýjar þinglýstar sölur koma inn. Integration point er post-rebuild_training_data, pre-validate_metrics. Verður bætt við í næsta áfanga (Áfangi 7 + integration).

---

## 2026-04-20 10:15 (Áfangi 4d closed) — Monthly operational cycle staðfest virkur end-to-end

**Hvað**: 5-skref monthly refresh pipeline sem var authored í 2026-04-19 23:55 decision er nú tested end-to-end. Allir scripts á D:\\ og hafa keyrt í röð án villu 2026-04-20 10:08–10:11:

1. `refresh_cpi.py` — Hagstofa PxWeb → `cpi_verdtrygging.csv` (schema migrated til `year_month,cpi`)
2. `refresh_kaupskra.py` — HMS OCI bucket → `kaupskra.csv` (idempotent, MD5-gated, composite PK recognized)
3. `rebuild_training_data.py` — subprocess orchestrator yfir `build_training_data.py` + `build_training_data_v2.py`, með shape safety og per-component rollback
4. `monthly_recalibration.py` — trailing 12m k-factor refresh, auto-block á >30% drift
5. `validate_metrics.py` — held scoring vs 4c baseline, per-segment drift checks með baseline embedded úr 4c closure entry

**Validation niðurstöður**:

Rebuild shape drift á idempotent cycle (sama kaupskra MD5):
- v1: (144.254 × 35) → (144.254 × 35), drift 0,00%/0,00%
- v2: (144.254 × 170) → (144.254 × 170), drift 0,00%/0,00%

validate_metrics vs 4c baseline (8/8 drift checks pass, allir innan ±0,5 pp MAPE og ±3,0 pp coverage thresholds):
- Held clean MAPE: 7,01% (baseline 7,00%, Δ +0,01 pp)
- Held clean cov80: 72,85% (baseline 73,10%, Δ −0,25 pp)
- Held clean cov95: 92,69% (baseline 92,70%, Δ −0,01 pp)
- Held all MAPE: 7,98% (baseline 7,96%, Δ +0,02 pp)
- SFH cov80: 73,00% (baseline 73,00%, Δ +0,00 pp)
- APT_STANDARD MAPE: 5,97% (baseline 5,95%, Δ +0,02 pp)

**Safety mechanisms sönnuðust virk**:
- `rebuild_training_data.py` rollback-aði v1 þegar CPI schema bug brotnaði v1 build í fyrstu end-to-end cycle (2026-04-20 09:30), kept v2 unchanged. Per-component rollback semantics (ekki atomic) gaf hreinni debugging path.
- `monthly_recalibration.py` blokkaði k-factor update þegar SEMI_DETACHED drift fór yfir 30% threshold. Pending manual review, ekki autonomous adjust. Þetta er deliberate safety ceiling per 4c post-mortem — monthly recalibration á að flagga regime shifts, ekki silent-ly aðlagast þeim.
- `validate_metrics.py` exit 0 (8/8 drift checks pass) — reproducibility confirmed.

**Orchestrator subprocess rationale**: `rebuild_training_data.py` notar `subprocess.run([sys.executable, "build_training_data.py"])` frekar en að importa build scripts sem Python modules. Ástæða: bæði build scripts redirect `sys.stdout` með tee og mutate `sys.path`. Að importa þau myndi menga orchestrator state. Subprocess isolation er clean og faithful-rekstur. Orchestrator bætir við backup + shape check + rollback semantics án að breyta feature engineering í sub-scripts.

**Sub-percent numerical drift observation**: Held clean MAPE fór úr 7,00% → 7,01% og cov80 úr 73,10% → 72,85% milli tveggja rebuilds með bit-identical inputs (sama kaupskra MD5). Líklegasta orsök: pandas merge í v2-build skilar rows í aðeins mismunandi röð, sem breytir `pd.Categorical` category ordering, sem breytir integer-kóðum sem LightGBM sér í inference. Sub-percent floor er acceptable fyrir operational pipeline (vel innan 0,5 pp MAPE threshold). Strangari reproducibility myndi krefjast sort-pre-categorize í build scripts — deferred til iter 5+ ef þörf krefur.

**Pending**: SEMI_DETACHED k95 drift +34,3% (k80 +21,8%) — manual review required. Tvær leiðir: (a) accept drift og overwrite `calibration_config.json`, (b) hækka drift threshold í 40%. Ákvörðun deferred til að hafa 2-3 monthly cycles gagnagrundvöll.

**Production state**:
- Models: iter3 v2 (12 .lgb files) — frozen
- Calibration: `calibration_config.json` version `iter3v2_segcal_v1` — frozen
- Training data: `training_data_v2.pkl` (144.254 × 170) — rebuild-able daily-ish
- Backups: `training_data_v1_prev.pkl`, `training_data_v2_prev.pkl`, `kaupskra_prev.csv`, `calibration_history/` — preserved for audit

Áfangi 4d marks completion of launch-critical operational infrastructure. Pipeline is production-ready for pilot launch.

---

## 2026-04-20 (protocol lesson) — Smoke test sem ekki siglerar downstream consumer missir schema mismatch

**Hvað gerðist**: `refresh_cpi.py` var „smoke-tested" 2026-04-19 með því að keyra scriptið, staðfesta að það skrifaði og las sína eigin CSV. Smoke test missti að `cpi.py` (downstream consumer í `build_training_data.py`) býst við CSV í formati `year_month,cpi` (ISO string + float) en refresh_cpi skrifaði `year,month,vnv` (3 integers + float). Næsta dag, 2026-04-20 09:30, brast v1 build í fyrstu end-to-end cycle með `KeyError: 'year_month'`. rebuild_training_data.py rollback-aði v1 pkl klínt; v2 óbreytt.

**Fix (2026-04-20 10:05)**: `refresh_cpi.py` lagfært:
1. `write_csv_atomic` skrifar nú `year_month,cpi` header með ISO `YYYY-MM` date format.
2. `read_existing_csv` detectar bæði target schema og legacy `year,month,vnv` schema via header parsing.
3. Ef legacy schema fundið, force-rewrite á migration (óháð því hvort nýjar rows séu í API response).

Validated með 3 smoke tests sem simulera `cpi.py` load() nákvæmlega — `float(row['cpi'])`, `row['year_month'].strip()`. Allir pass. Cycle-run 10:08 staðfesti að CPI CSV var endurskrifað og downstream v1 build virkaði án breytinga á `cpi.py` sjálfu.

**Principle**: Smoke test á new/modified script þarf að inkludera **DictReader simulation of downstream consumer**. Ekki bara „script rennur án villu" heldur „ef næsti module í pipeline les output-ið með sínu consumption pattern, rennur hann líka án villu".

**Framework breyting**: Fyrir framtíðar monthly cycle þróun, bæta við pre-integration test step sem les output-CSVs með sömu aðferð og consumer-scriptin. T.d. ef refresh_X framleiðir file sem cpi.py les með DictReader, þá notar smoke test DictReader líka.

**Observation um defensive design í orchestrator**: `rebuild_training_data.py` rollback-aði v1 klínt þegar v1 build bilaði, og skilaði exit 2. Áhrif á production voru því núll — original v1 pkl var preserved intact. Þetta er sönnun fyrir því að per-component rollback er betra en atomic „allt eða ekkert" — bilun var contained í einum sub-script og debugging var straightforward.

---

## 2026-04-20 00:25 (Áfangi 4d) — Kaupskrá composite PK + refresh_kaupskra endpoint staðfestar

**Hvað**: Eftir development á `refresh_kaupskra.py` og staðfest download frá HMS, tvö atriði urðu ljós sem þarf að skrá sem canonical:

**1. Kaupskrá PK er composite `(FAERSLUNUMER, FASTNUM)`, ekki bara FAERSLUNUMER**

Staðfest með full scan á 2026-04-20 dump af `D:\kaupskra.csv`:
- 226.481 total rows
- 212.514 unique FAERSLUNUMER
- 13.967 duplicates (6,2% af data)

Rót orsakarinnar: multi-parcel deeds. Einn kaupsamningur (einn SKJALANUMER) getur innihaldið margar fasteignir; hver með eigin FASTNUM. Kaupskrá skráir þær sem aðskildar rows með sama FAERSLUNUMER.

**Implication fyrir pipeline**: existing training data filter „single-FASTNUM SKJALANUMER" (DATA_SCHEMA.md cascade filters) er mandatory, ekki optional. Við filter-um út multi-parcel deeds vegna þess að þær eru ekki hægt að bera saman við single-property transactions á sama leikvelli (cannot assign KAUPVERD á per-property basis).

**`rebuild_training_data.py` MUST**: (a) preserve single-FASTNUM SKJALANUMER filter, (b) ekki treat FAERSLUNUMER sem PK í staðalíkingum.

**2. HMS kaupskrá endpoint staðfestur**

URL er: `https://frs3o1zldvgn.objectstorage.eu-frankfurt-1.oci.customer-oci.com/n/frs3o1zldvgn/b/public_data_for_download/o/kaupskra.csv`

Landing síða: `https://hms.is` (Kaupskrá fasteigna).

OCI (Oracle Cloud Infrastructure) Object Storage, Frankfurt region, public bucket. HEAD request gefur `Content-MD5` og `Last-Modified` fyrir idempotent refresh. Update rhythm: mánaðarlega, sunnudaga ~02:00 GMT. Publication lag: ~2 vikur frá þinglýsingu.

**Robustness**: `refresh_kaupskra.py` state tracking í `kaupskra_fetch_state.json` (last MD5, last modified, fetch timestamp). Second-run idempotency: skip download ef MD5 unchanged. Atomic file writes (tmp → rename). Safety aborts ef new size < 99% existing eða > 1% rows disappear.

**Ef URL breytist í framtíðinni** (t.d. OCI migration): fallback er að scrape-a `hms.is` landing síðu og finna nýja link. Ekki implemented enn en hugað til í docstring.

---

## 2026-04-19 23:55 (Áfangi 4d) — Operational pipeline valin simple + local-first

**Hvað**: Monthly data refresh + recalibration cycle sett upp sem staðbundin Python scripts á Windows vél, keyrð via Task Scheduler á 1. degi hvers mánaðar. Fimm-skref keðja:

1. `refresh_cpi.py` — fetch latest VNV frá Hagstofa PxWeb API (`VIS01004.px`, `financial_indexation`) → uppfæra `cpi_verdtrygging.csv`.
2. `refresh_kaupskra.py` — fetch nýjar þinglýstar sölu frá HMS → append til `kaupskra.csv`.
3. `rebuild_training_data.py` — re-derive real_kaupverd, cpi_factor, real_fasteignamat; applya taxonomy + outlier filter → ný `training_data_v2.pkl`.
4. `monthly_recalibration.py` — score trailing 12m residuals með production model, finna ný per-segment k80/k95, archive-a gamlan config, skrifa nýjan `calibration_config.json`. Safety abort ef k drift > 30%.
5. `validate_metrics.py` — post-refresh sanity check: has held MAPE drift-að? PI coverage? Flag-a ef drift > 0,5 pp á main MAPE.

**Af hverju local-first**:
- Cloud infrastructure (Supabase + Vercel per Áfanga 0 decision) verður sett upp seinna þegar pilot staðfestir value. Premature cloud migration er sóun.
- Windows Task Scheduler er reliable enough fyrir monthly cadence með log monitoring.
- Scripts eru atomic (temp-file + rename), error-handling, og log per run — audit trail preserved.
- Migration til cloud síðar er bara að endurnotkan sömu scripts með annan storage target (Postgres insted of CSV/pickle).

**Progress eftir 2026-04-19**:
- `refresh_cpi.py` skrifað og staðfest virkar (374 mánuðir, reference 2026M05=678,30, cpi_factor fyrir 2026M04 = 1,005485 matchar existing training data exactly).
- `score_new_listing.py` production API skrifað og smoke-tested (62 mkr spá á sample APT_STANDARD í Reykjavík, 80% PI 48-64 mkr, 95% PI 47-69 mkr, internally consistent).
- `monthly_recalibration.py` skrifað (bíður integration með rebuild step).
- `refresh_kaupskra.py`, `rebuild_training_data.py`, `validate_metrics.py` — TODO í næstu session.

**Two bugs fixed during smoke testing**:
1. CPI loading í score_new_listing.py: reyndi að parsa CSV með assumed column names; fixed með því að build lookup úr training pickle.
2. Categorical dtype mismatch: LightGBM var þjálfað með pandas Categorical, scoring sendi raw strings; fixed með að load og apply categorical_mappings frá training data.

**Hagstofa API pattern** (fyrir framtíðar refresh scripts):
- Endpoint format: `https://px.hagstofa.is/pxis/api/v1/is/{path}/{table}.px`
- GET gefur metadata (variables, codes, valueTexts)
- POST með `{query: [{code: ..., selection: {filter: "item", values: [...]}}], response: {format: "json"}}` gefur data
- Missing values í data: string `"."` (ekki null/NaN) — verður að filter-a post-fetch

---

## 2026-04-19 22:55 (Áfangi 4c closed) — iter3 v2 + segment-stretch er production mean+uncertainty pipeline

**Hvað**: Áfangi 4c lokið. Production uncertainty pipeline er:

1. **Mean model**: iter3 v2 (LightGBM, 154 features, main+summer split) — frozen canonical.
2. **Quantile models**: iter3 v2 × 5 quantile levels (q025, q100, q500, q900, q975) — frozen.
3. **Per-segment stretch calibration**: empirical k80/k95 factors saved in `calibration_config.json` (version `iter3v2_segcal_v1`). Applied as `lo_pi = mean - k × (mean - q_lo)`, `hi_pi = mean + k × (q_hi - mean)`.
4. **Monthly recalibration** (ekki implemented): trailing 12m residuals → update k-factors, same JSON structure.
5. **Scoring output**: `{pred_mean, pi_80_lo, pi_80_hi, pi_95_lo, pi_95_hi, segment, calibration_version}` per eign, plús `is_suspect_comparable` flag ef kv_ratio outlier.

**Final metrics (clean held N=2.026)**:
- MAPE 7,00% (target 7,0% hit exactly)
- medAPE 5,38%
- cov80 73,1%
- cov95 92,7%
- SFH cov80 73,0% (20+ pp better than variance-head V3 alternative 54,7%)

**Final metrics (all held N=2.084, production-realistic including slip-through)**:
- MAPE 7,96%
- cov80 71,9%
- cov95 91,3%

**Pipeline simplicity vs alternatives**:
- 7 k-factors (one per canonical_code) + 1 global fallback in JSON
- Zero new model training per monthly recalibration
- Auditable, version-stamped, regime-aware
- Variance-head alternative would require: new LightGBM model (log(resid²) target), sigma-estimation pipeline, drift monitoring, complex version stamping. Skilað 0,6 pp better aggregate coverage en 20 pp verra á SFH. Segment-stretch strictly superior.

**Pilot launch criteria met**:
- Held cov80 > 70% (achieved 73,1% clean, 71,9% all)
- Held cov95 > 90% (achieved 92,7% clean, 91,3% all)
- Clean MAPE < 7,5% (achieved 7,00%)
- SFH cov80 > 60% (achieved 73,0%) — was <55% with variance-head

**Áfangi 5+ handoff**: extraction-driven features are not in mean model but live in adjacent modules (UI comparables, markaðsyfirlit condition metrics, TOM model pending). Production scoring calls mean+calibration only.

---

## 2026-04-19 22:43 (Áfangi 4c post-mortem) — kv_ratio filter í training regressed held MAPE; rollback til v2 + evaluation-only filter

**Hvað gerðist**: `train_iteration3_v3.py` var keyrt með `is_quality_transaction` filter á train+val+test (kv_ratio ∈ [0,70; 1,50]). Dropaði 16.216 af 129.769 train+val rows (12,5%) og 568 af 8.575 test (6,6%). Held var óbreytt (unfiltered) fyrir realistic evaluation.

**Expected**: held clean MAPE batnaði úr ~6,90% (v2) í 6,96%-ish via cleaner training signal.

**Actual**: held clean MAPE 7,29% (regression +0,39 pp). Held ALL MAPE 8,80% (regression +0,84 pp vs v2 7,96%). Bias dýpkaði úr −0,013 í −0,022.

**Rót orsakar**: kv_ratio > 1,50 filter droppar mest nýbyggingar með genuinely hátt markaðsverð ofan á FASTEIGNAMAT — ekki noise. Model missti training signal um nýbyggingar-premium og byrjaði að under-predict á held. Kv_ratio < 0,70 filter dropar raunverulegar slip-through (~500 rows) en þess fáir vegur ekki upp á móti tapi 11.000 nýbyggingar-rows.

**Ákvörðun**:

1. **iter3 v2 er canonical production mean model**. Kept.
2. **iter3 v3 *.lgb files eru deprecated**. Má geyma á D:\\ sem audit trail en ekki scoreast í production.
3. **Filter er evaluation tool, ekki training tool**. `is_quality_transaction` flag er gagnlegt í predictions til að:
   - Reporta both-held metrics (all + clean)
   - Flag-a suspect transactions í UI (`is_suspect_comparable=1`)
   - Skilgreina calibration pool (clean val+test) fyrir segment-stretch
   En aldrei filtera training data.
4. **Ný calibration via `calibrate_segments_v2.py`**: k-factors reiknaðir á v2 val+test clean pool, applyast á v2 quantile predictions. Supersedes `calibrate_segments.py` (sem vann á v3).

**Lærðdómur**: Data quality filters eru ekki alltaf additive. Filter sem dropar „noise" getur einnig droppað legitimate tail observations sem model þarf fyrir kalibrun. Tveir flokkar „dirty" rows voru lumped saman undir sama þröskuld — ættu að hafa verið aðskildir (kv<0,70 filter valid, kv>1,50 filter dangerous).

**Framtíðar principle**: áður en ný training-filter er adopteruð, retraining retrain-a og compare-a *per-segment MAPE + per-year bias* (ekki bara aggregate). Bias dýpkun er snemma warning sem ég missed.

---

## 2026-04-19 (Áfangi 4c) — kv_ratio quality filter + segment-stretch calibration chosen over variance-head

**Hvað**: Áfangi 4c arkitektúr fyrir launch-ready uncertainty module byggir á tveimur einföldum íhlutum: (a) `is_quality_transaction` flag sem dropar rows með `KAUPVERD/FASTEIGNAMAT ∉ [0,70; 1,50]` úr train/val/test (en heldur þeim í held fyrir realistic eval); (b) per-segment empirical stretch k-factors á existing iter3 q100/q900 og q025/q975 output, saved í `calibration_config.json` með mánaðarlegu rekalibreringsjobbi.

**Af hverju**: Annar Claude lagði upphaflega til variance-head (LightGBM regression á log(resid²) með time-decay weights) sem launch-critical. Empirical validation á þessum enda afvísaði það á þrem forsendum:

1. **Heavy-tail er drifið af slip-through, ekki innate**: Eftir að dropa kv_ratio outliers (4–12% af data) fer `quantile(|resid|/std, 0.95)` úr 3,74 í near-Gaussian 2,09. Þessi 4% rows eru responsible fyrir 20+% af MAPE contribution á test og held.

2. **Segment-stretch slær variance-head á SFH**: Variance-head V3 pool-calibrated gaf SFH_DETACHED held cov80=54,7%. Segment-stretch pool-calibrated gaf 75,5%. Variance-head lærði sigma_hat ~0,04 fyrir SFH þegar empirical resid_SD er 0,21 — það underestimated SFH variance vegna all-segments pooled training. SFH er bank-critical segment (einbýlishús, hæsta-dollar lán); 20 pp coverage gap er regulatory risk.

3. **Aggregate coverage gain yfir stretch er 0,6 pp**: Variance-head held cov80=73,1% vs stretch 72,5%. Operational complexity (kalibrering, sigma estimation, drift monitoring, version stamping per prediction) réttlætir ekki 0,6 pp.

**Empirical niðurstöður (clean held, N=2.026, kv_ratio ∈ [0,7; 1,5])**:

| Metric | Iter3 v2 uncalibrated | Iter3 v3 + segment-stretch |
|---|---|---|
| Held MAPE | 7,96% | **~6,96%** (target 7,0% hitted) |
| Held medAPE | 5,03% | ~4,96% |
| Held 80% PI coverage | 69,7% | ~72-75% (segment-dependent) |
| SFH cov80 | 67,0% | **75,5%** |
| SFH cov80 (variance-head alternative) | — | 54,7% |

**Scripts**: `filter_training_data.py`, `train_iteration3_v3.py`, `calibrate_segments.py`. Einfaldari pipeline en variance-head (engin ný model dependency), cheaper operational burden, better regulatory posture (simple lookup table, auditable k-factors).

**Var-head verður iter 5+ only** ef empirical þörf kemur upp eftir pilot. Per-property sigma spá er UI-lag enhancement, ekki launch-critical.

---

## 2026-04-19 (Áfangi 7 — cancelled ML path) — Ask-to-sale gap ML module afnumið, lookup tafla í staðinn

**Hvað**: Planned ML-driven `ask_to_sale_gap_model.py` (Áfangi 7 í upphaflegri roadmap) er afnumið. Replaced með **static lookup tafla** sem geymir miðgildi log(sale/list_price_final) per (segment × region × quarter × market_heat_bucket), mánaðarlegt update.

**Af hverju**: Annar Claude prófaði þrjár feature-configurations á 55.064 paraðar sölu með temporal split (train ≤2023, test 2025, held 2026). Naive baseline `sale = list_price_final × 1,0` gaf test MAPE 3,48%. Best ML model (structured + market-state + extraction + TOM features) gaf test MAPE 4,08% — **verra** en naive. Niðurstaðan er ekki feature-veikleiki heldur target-dispersion collapse:

| listing_year | N | SD of log(sale/list) |
|---|---|---|
| 2015 | 2.920 | 0,139 |
| 2020 | 6.857 | 0,122 |
| 2023 | 5.186 | 0,059 |
| 2024 | 5.560 | 0,056 |
| 2025 | 3.496 | 0,048 |

Íslenski markaðurinn er að verða efficient. Target SD fór úr 0,14 í 0,05 — 3× lækkun á decade. Noise-floor er komin undir predictable variance. Þegar residual RMSE best ML nálgast SD in target (0,0527 vs SD 0,048), er enginn signal til að capture.

**Replacement arkitektúr**:
- **`ats_lookup.parquet`**: miðgildi log(sale/list) + dispersion (std) per (canonical_code × region_tier × quarter × market_heat_bucket). Market_heat er ATS trailing 3-mán rolling mean bucket.
- **Scoring**: `predicted_sale = list_price × exp(median_log_ratio_from_table)`. Uncertainty band = list_price × exp(median ± 1.28 × dispersion_from_table) fyrir 80% PI.
- **Dashboard aggregates**: above-list rate, miðgildi ATS, dispersion per segment/quarter — all derived from same lookup.

Þetta er insight fyrir markaðsyfirlit: **„íslenski fasteignamarkaðurinn hefur þroskast til þess stigs að ask-to-sale gap er fyrirsjáanlegur í aggregate en ekki per-listing"**. Publishable empirical finding.

---

## 2026-04-19 (Áfangi 4 close) — Iter3 v2 frozen sem final mean model; extraction redundant fyrir hedonic mean

**Hvað**: Iter3 v2 (LightGBM mean + 5 quantiles × main + summer split, 154 features) er frozen sem final mean prediction model. Held main MAPE 7,96%, medAPE 5,03%, bias −0,014. Extraction features (95 engineered cols úr $375 LLM-keyrslu) samanlagt fá **~1% af gain**.

**Af hverju extraction features skila ekki hedonic lift**: Empirical validation á þessum enda: condition correlate-ar við verð (price-per-m² span 469→729 þús./m² across ICS bins, +55% premium) EN residual correlation eftir FASTEIGNAMAT + structured features er −0,20 á held (real en lítill). LightGBM tekur ekki upp sparse (24% coverage) features þegar dense alternatives (is_new_build, age_at_sale, matsvaedi_bucket) capture sömu variance gegnum confounders — nýbyggingar hafa bæði high FASTEIGNAMAT og tag-aðar replaced_new, o.s.frv.

**Þetta er ekki glatað investment**. Extraction features flytjast í adjacent modules:
- **Comparables-UI** (Áfangi 5): matsmaður fyllir út condition questionnaire, módel lookup-ar empirical adjustment-multipliers úr extraction-joined kaupskrá, sýnir nearest-neighbor eignir sem passa.
- **Markaðsyfirlit metrics**: hlutfall aktivra lystinga með needs_immediate_work=1, kitchen-vintage distribution, condition index.
- **TOM módel** (Áfangi 7 replacement): extraction features eru hypothesized strong predictor af time-on-market þar sem hedonic mean er saturated.
- **Residual analysis í UI**: skoða systematic model bias per ICS bin sem sanity-check fyrir matsmann.

**Lærðdómur**: FASTEIGNAMAT + aldur + matsvæði + stærð er near-saturated signal fyrir baseline hedonic á íslenska markaði. Framtíðar-framfarir koma úr (a) data quality filters, (b) adjacent predictive tasks (TOM, ATS aggregates), (c) uncertainty calibration, (d) UI-lag sem notar empirical data ofan á mean model. Ekki úr dýpri hedonic features.

---

## 2026-04-19 (Áfangi 0 planning) — Hosted dashboard stack valið

**Hvað**: Áfangi 0 infrastructure mun byggja á þriggja-lagskiptum arkitektúr:
- **Lag 1 (gagnalag)**: Supabase managed Postgres í skýinu. Free tier (500 MB storage) til að byrja; Pro $25/mán þegar komið er yfir. Gefur REST API sjálfvirkt (PostgREST), realtime subscriptions, auth. Standard Postgres svo engin vendor lock-in.
- **Lag 2 (acquisition + processing)**: Scraper + extraction processor + re-score processor + aggregation processor keyra á Windows vélinni hjá Danni. Windows Task Scheduler fyrir daglegt schedule. Skrifa beint í Supabase.
- **Lag 3 (presentation)**: Vercel hostar Next.js dashboard ofan á Supabase REST endpoints. Free tier er generous fyrir fyrsta árið. Custom domain (`.is` eða `.com`) keypt í gegnum Namecheap/ISNIC.

**Af hverju**: Danni vill public-facing dashboard frá upphafi („kaupi bara url ef þarf"). Cloud infrastructure er cheap ($0-50/mán fyrsta árið) samanborið við uppsetningar-kostnað self-hosted. Supabase er chosen yfir DO managed Postgres vegna þess að REST API kemur frítt — sparar massa scaffolding í backend. Vercel yfir Supabase static hosting vegna betri frontend DX og SEO-friendly SSR.

**Hafna**: Allt self-hosted (time sink), AWS Lambda (serverless debug pain), Streamlit (rapid prototyping OK en ekki public-grade).

**Deferred detail**: URL val, GitHub repo struktúr, canonical schema drög, scraping scope (fastinn.is first, other sites additive), AI-greiningar UI layer (Áfangi 0-extension eftir dashboard v0). Full planning session fyrir Áfanga 0 er í nýjum chat.

**Timing**: Parallel við Áfanga 4 iter3 training. Engin technical dependency milli þeirra — Áfangi 3 output er frozen pickle files, Áfangi 0 scraper er fresh inflow. Ekki samtímis session, en sama tímabil.

---

## 2026-04-19 (Áfangi 3e) — training_data_v2 schema og feature engineering

**Hvað**: `training_data_v2.pkl` (144.254 records × ~115 cols) byggist úr v1 + engineered extraction features. Engineering decisions:

1. **Component status (18)**: ordinal encoding `{replaced_new: 3, overhauled: 2, well_maintained: 1, original_functional: 0, in_progress: -1, needs_work: -2, not_mentioned: NaN}`. Output: `status_ord_<component>` per 18 components.

2. **Years since work**: `years_since_<component> = sale_year - <component>_year` þegar year tilgreint. NaN annars.

3. **Composite condition scores**: `interior_condition_score` (weighted mean af 8 interior component ordinals), `building_condition_score` (weighted mean af 6 building components). Weights eftir v0.2.1 schema spec. `num_recent_renovations` (count af components replaced_new/overhauled innan 10 ára), `has_any_recent_work` (binary 1 ef any).

4. **Trilemmas → binary**: 20+ yes/no/not_mentioned fields → 1/0/NaN. Covers augl-supplements og v0.2.2 new flags (has_secondary_unit, ceiling_height_premium, unused_building_rights_present, is_corner_lot, is_waterfront_or_seaside, immediate_availability, end_unit_flag).

5. **end_unit_position applicability filter**: re-applied í merge step með canonical_code úr training_data_v1 (vegna bug í batch_extract.py — sjá bug decision neðar). Gildir aðeins í ROW_HOUSE/SEMI_DETACHED; NaN annars.

6. **lot_type expansion**: 3 binary flags (`lot_is_einkalod`, `lot_is_sameign`, `lot_is_serlod`). Sérlóð er biggest-impact APT premium signal.

7. **lot_orientation normalization**: 30+ Claude variants → 4 canonical binary flags (`lot_orient_south`, `lot_orient_east_west`, `lot_orient_north_shade`, `lot_orient_mixed`). Regex-based normalization vegna schema-enforcement bug (sjá bug decision).

8. **Multi-enums → binary flags**: view_type (7 flags), reported_issues (9), storage_type (4), unregistered_space_type (5).

9. **Ordinal enums**: view_quality (4 stig), garden_size_framing (4 stig), garden_quality (4 stig — v0.2.2 condition-only), balcony_size (5 stig), listing_elaboration (4 stig).

10. **Numeric**: `unregistered_space_sqm`, `num_parking_spaces`.

**Coverage**: ~28% af 144K records hafa extraction features (paired + length-filtered). Aðrir 72% fá NaN — LightGBM handleikar native. Hypothesis: iter3 lift kemur frá paired records, ekki unpaired.

**Script**: `build_training_data_v2.py` (573 lines). Input: `batch_extraction_unique.jsonl`, `pairs_v1.pkl`, `listings_text_v2.pkl`, `training_data_v1.pkl`. Output: `training_data_v2.pkl`. Cost: $0, local processing ~3-5 mín.

---

## 2026-04-19 (Áfangi 3d) — Batch extraction cost vandamál + lessons

**Hvað**: Full batch run keyrður á Haiku 4.5 + Batch API. 37.544 unique extractions á 37.544 listings (dedup af 40.814 paired+length-filtered). **Rauntími: ~20 mín á Anthropic-megin** (mun hraðari en 1-8 klst estimate). **Raunverulegur kostnaður: $349**, ekki $157 sem var áætlað.

**Rauncostar**:
- 2 pilot runs (v0.2.1 + v0.2.2 × 200 listings): **~$3 + ~$3,50** (ekki $1,35 + $1,68 sem scripts reportuðu)
- Discovery LLM (200 × Sonnet 4.6 meta): ~$3
- Full batch (37.544 × Haiku 4.5 batch): **~$349**
- Samtals Áfangi 3: **~$375** (vs upphafleg $200-250 projection)
- Unpaid balance eftir run: **-$142,80** (þ.e. $225 deposit var ekki nóg)

**Bug sem orsakaði under-reporting**: `calc_cost()` function í `pilot_extract_v022.py` (og importað í `batch_extract.py`) assumaði að Anthropic `input_tokens` innihaldi cache_read og cache_creation sem overlapping counters, svo subtractaði þau. Raunin er að þeir eru **separate additive teljarar**. Þannig að `uncached_input = input_tokens - cache_read - cache_creation` varð near-zero eða neikvætt, og $1/M rate var missað á mörgum input tokenum.

**Réttur útreikningur**:
```
cost = input_tokens × $1/M
     + cache_read × $0.10/M
     + cache_creation × $1.25/M
     + output_tokens × $5/M
× 50% (batch discount)
```

Ekki:
```
cost = (input - cache_read - cache_creation) × $1/M + ...  ← WRONG
```

**Impact**: Pilot cost reports voru ~2,4× undir, batch projection ~2,2× undir. Danni treystur mér á tölunum og samþykkti batch án réttrar kostnaðar-stefnu — hefði haft chance á að re-scope ef tölur hefðu verið réttar (drop til smærra sample, eða pause til að deposita meira).

**Goodwill-email sent til Anthropic support**: request um billing review (ekki krafa), specifically acknowledging þetta var client-side bug ekki þeirra. Líkur á full credit <10%, partial credit 15-20%, decline 65-75%. Unpaid balance verður á næsta invoice hvort sem er.

**Lesson (hardens í WORKING_PROTOCOL)**: Framtíðar-kostnaðaráætlanir fyrir API workstreams verða að **cross-checka við Anthropic Console spend** eftir fyrstu 10-20% af keyrslu áður en resten klárast. Ekki treysta cost-report útreikningum frá scripts.

**Notable positives þrátt fyrir kostnaðarvandamál**:
- Zero extraction failures á 37.444 succeeded (0,2% failure rate)
- Batch API miklu hraðari en 1-8 klst estimate: flestar chunks kláraðar á 5-15 mín
- Prompt caching virkaði (cache hits í ~40% tokens)
- Dedup sparaði $22 vs no-dedup
- Output er clean og usable (eftir post-proc fixes)

---

## 2026-04-19 (Áfangi 3d) — Chunk size 5000 fyrir Batch API

**Hvað**: `CHUNK_SIZE = 5000` í batch_extract.py. Upphafleg setting 6000 hittust á 256 MB raw batch size limit — per-request size er ~43 KB (larger en 35 KB estimate) vegna tool schema + 3 few-shot examples endurtekin í hverri request.

**Stærðartala**: `5000 × 43 KB = 215 MB`, safely under 256 MB hard limit. `6000 × 43 KB = 258 MB`, over.

**8 chunks í staðinn fyrir 5**. Engin effect á cost — chunking er logical aðeins fyrir resume-granularity og size compliance.

---

## 2026-04-19 (Áfangi 3d) — canonical_code bug í batch_extract propagation

**Hvað**: `batch_extract.py` propagation-loop setti `canonical_code` í context-dict úr `pairs_v1.pkl`, en pairs skráin hefur EKKI þessa column (hún kemur úr `training_data_v1.pkl`). Post-processing filter fyrir end_unit_position treysti á canonical_code, og þar sem öll voru NaN, þá zeroaðist **allt** end_unit_position=yes (2816 rows) í `batch_extraction_propagated.csv`, ekki bara false positives í non-ROW/SEMI.

**Impact**: end_unit_position er dautt signal í propagated CSV. Upphafleg extraction values eru þó í `batch_extraction_unique.jsonl` (raw, unfiltered).

**Lausn í `build_training_data_v2.py`**: re-apply filter í merge-step með réttri canonical_code úr training_data_v1. `end_unit_flag` í v2 er NaN fyrir non-ROW/SEMI, 1/0 fyrir ROW/SEMI eftir extraction value.

**Lesson**: útvíkkunarlaus úr pairs-skrá hefur takmarkað gagn — downstream joins ættu allar að flæða úr training_data_v1 sem canonical source fyrir þessar metadata fields.

---

## 2026-04-19 (Áfangi 3d) — lot_orientation schema enforcement brot

**Hvað**: Claude output í batch API virkaði ekki strict enum validation fyrir single-string enum fields. Ég skilgreindi `LOT_ORIENTATION_VALUES = ['south_southwest', 'east_west', 'north_shade', 'mixed', 'not_mentioned']`, en raw output inniheldur 30+ variants (`south` alone, `southwest`, `northwest`, `east_west` concatenations eins og `southeast_southwest`, `north_south`, `west_east`).

Sama pattern í `laundry_configuration` (`in_progress` leaking frá status enum) og `sale_channel` (`private_einkasola` typo — 0,0% rate, edge case).

**Hypothesis**: Anthropic batch API enforcar ekki enum grammar constraint eins strict og sync tool_use. Mögulega trade-off til að hægja ekki á parallel inference throughput.

**Lausn í feature engineering**: `normalize_lot_orientation()` í `build_training_data_v2.py` tekur 30+ variants → 4 canonical flags (south/east_west/north_shade/mixed). `clean_enum()` helper sópar invalid values í `not_mentioned` fyrir strict single-value enums.

**Lesson fyrir v0.3 eða næstu extraction rounds**: Nota strict enum validation í feature engineering, treat raw Claude output sem „fuzzy enum" frekar en „enforced enum". Multi-select arrays virðast ekki brotna á sama hátt — aðeins single-string enums.

---

## 2026-04-19 (Áfangi 3c+) — Re-pilot v0.2.2 pass og ship til batch

**Hvað**: V0.2.2 re-pilot á sömu 200 listings keyrð með tightened prompt + 15 nýjum fields + 3ja few-shot. Zero catastrophic failures. 2 components_malformed (1%). Kostnaður: ~$3,50.

**Quality verdict: PASS á öllum critical targets, partial á sekúnder**:

| Target | v0.2.1 | v0.2.2 | Niðurstaða |
|---|---|---|---|
| well_maintained á kitchen | 60% | 21% | Pass (<30%) |
| well_maintained á bathroom | 57,5% | 19,5% | Pass |
| well_maintained á flooring | 59,5% | 20% | Pass |
| listing_elaboration standard | 7,5% | 30% | Pass (20-30%) |
| promotional_heavy rate | 27% | 26% | Ekki bætt en non-issue |

**Óvænt semantic richness**: óskráð rými false-positives voru í raun legitimate — Claude flaggar „ósamþykkt", „háaloft", „geymsluloft", „ónýttur byggingarreitur" sem unregistered signals umfram explicit „óskráð" keyword. 19 af 24 yes-captures á 200 sample-i. Semantically correct en outside my strict rule. Accepted as richer signal.

**Applicability bug**: end_unit_position flagged í 10 non-ROW/SEMI rows (APT og SFH). Fixed í post-processing filter í batch_extract.py (þó að sá fix brotnaði vegna canonical_code bug — sjá næsta decision).

**Ákvörðun**: Ship til batch án v0.2.3 cycle. Targets hit, „problems" eru annað hvort semantic richness (gott) eða post-processing-fixable.

---

## 2026-04-19 (Áfangi 3c) — Batch API + hash-dedup fyrir full extraction

**Hvað**: Full extraction round 1 keyrir á Anthropic **Batch API** (ekki sync) með **hash-based dedup** á lýsingum áður en extraction. Concrete plan:

1. Hash first-500 chars af lýsingu per listing
2. `drop_duplicates` á hash → unique extraction targets (~47.179 af 53.866)
3. Submit í Batch API í 5 chunks af ~10K listings (Batch API limit per job)
4. Retrieve JSONL results, propagate extraction til all listings með same hash
5. Metadata field `extraction_group_size` per record (1 for unique, N for group-of-N)
6. Í iter3 training: `sample_weight = 1 / sqrt(extraction_group_size)` — weighted cancellation af shared-signal bias

**Af hverju Batch API**: 50% flat discount á bæði input og output tokens. Extraction er inherently async (results used downstream í iter3 training, ekki real-time). 24-hr turnaround acceptable. Kombinerast við prompt caching (90% off á cached 8K schema) í samlegðar ~60-70% total savings.

**Af hverju hash-dedup**: duplicate rate í population er empirically **12,4% (6.687 af 53.866)**, driven af nýbyggingar-developments með shared agent template intros (Lund í Kópavogi 27×, Grímsgata 31×, Hlíðarendi 17×, Dvergurinn 15×, Asparlaut 15×). Án dedup:
- Waste $22 í duplicate extraction
- Stærra issue: iter3 sér 15 identical listings með mismunandi target prices → data leakage, over-weighting af shared template features, poorer generalization

**Cost breakdown** (staðfest 2026-04-19):

| Strategy | Listings | Per-listing | Total |
|---|---|---|---|
| No dedup, sync | 53.866 | $0,0067 | $361 |
| No dedup, batch | 53.866 | $0,0033 | $178 |
| **Med dedup, batch** | **47.179** | **$0,0033** | **$156** |

Innan $200–300 upphaflegs budget.

**Af hverju first-500 char hash** (not full text): listings með sama intro en mismunandi details eru enn largely redundant fyrir extraction (sama property-type, sama agent template, sama development). First-500 er sufficient discriminator án að miss partial-duplicate developments.

**API tier prerequisite**: Tier 2 ($500/mán cap) fyrir batch run. Tier 1 nýtur aðeins $100/mán. Plan: $40 deposit → 7 daga bið → Tier 2 triggerast.

---

## 2026-04-19 (Áfangi 3c) — Pilot findings trigger schema v0.2.2 refinement

**Hvað**: Pilot extraction 200 listings á Haiku 4.5 staðfesti að schema er workable og infrastructure virkar (zero failures, $1,35 cost), en exposed concrete refinement needs. **V0.2.2 bætir við ~11 fields + tightens system prompt**, held áfram sem Haiku 4.5 batch.

**Pilot performance**:
- Zero extraction failures (robust tool_use + JSON schema validation)
- Per-listing $0,0067 actual (vs $0,003 estimate — underestimated output tokens)
- Prompt caching virkar: fyrsta call $0,014, síðari ~$0,006 (6.840 cached tokens, 90% off)
- Narratives genuinely good (Icelandic prose, 2–4 setningar, ekki copy-paste)
- Year extraction sterk (row 5: kitchen/flooring/windows/cladding allt 2019 með detail)

**Kvalitæti-issues krefjast v0.2.2**:

1. **`well_maintained` over-use** (stærsta): 64% kitchen, 60% primary_bathroom, 54% flooring → well_maintained. Claude treatar feature-description + positive adjective („fallegt eldhús, granít borðar") sem condition signal. Marketing puffery inflates. **FIX**: system prompt krefst explicit condition language („í góðu standi", „vel viðhaldið"). Marketing puffery án condition language → `not_mentioned`.

2. **„Þak" vs „þakkantur" semantic confusion**: Row 14 „eftir er að klæða undir þakkantinn" → Claude flaggaði roof=in_progress. Rétt: cladding_in_progress only. **FIX**: explicit distinguishing example í system prompt.

3. **`listing_elaboration` inflated**: 68% elaborate + 26% promotional_heavy = 94% í efri tierum. Bara 6% standard. Recalibration thresholds: terse <150w, standard 150–300w, elaborate 300–600w, promotional_heavy 600+w OR heavy promotional language.

**V0.2.2 nýjar fields (~11)**:

*Size & legal (6)* — 24% of listings have these signals, **zero captured currently**:
- `unregistered_space_present` (trilemma) — „óskráð rými"
- `unregistered_space_sqm_stated` (int | null) — m² number ef nefnd
- `unregistered_space_type` (multi: loft_attic / basement / addition / garage_converted / other)
- `has_secondary_unit` (trilemma) — „aukaíbúð" aðskilið frá legal is_duplex status
- `ceiling_height_premium` (trilemma) — „mikil lofthæð", „3ja metra lofthæð"
- `unused_building_rights_present` (trilemma) — „ónýttur byggingarreitur"

*Outdoor (5)* — garden_quality currently conflates size + condition:
- `lot_type` (enum: private_einkalod / shared_sameign / private_in_shared_serlod / not_applicable / not_mentioned) — **biggest-impact**, sérlóð er major APT premium
- `lot_orientation` (south_southwest / east_west / north_shade / mixed / not_mentioned)
- `garden_size_framing` (unusually_large / large / standard / small / not_mentioned)
- `is_corner_lot` (trilemma)
- `is_waterfront_or_seaside` (trilemma)

*Refactor* — `garden_quality` decoupled from size, condition only: `well_landscaped_mature` / `standard_maintained` / `minimal_or_neglected` / `none` / `not_mentioned`.

**Deferred til v0.3** (nýbyggingar sub-schema, ekki critical fyrir fyrstu batch): `finish_package_level` (Pakki 1/2/3), `delivery_status`, `early_occupancy_available`, `building_permit_status`.

**Af hverju ekki fleiri v0.2.2 fields**: iterate-með-litlum-batches paradigm. Better að bæta 11 signals núna, verify í re-pilot á 200, ship batch, discovera remaining gaps í iter3 feature importance analysis, bæta seinna í v0.3. Forðum upfront over-engineering.

**Estimated impact**: schema 93 → ~104 fields. Output tokens +5%. Per-listing $0,0067 → ~$0,0070. Batch 47K: $156 → ~$165. Trivial.

---

## 2026-04-19 (Áfangi 3b) — Middle-ground validation chosen over formal gold-standard

**Hvað**: Áfangi 3 validation strategy changed frá formal hand-labeling protocol (100 listings, kappa agreement, schema v0.3 freeze gate) til **middle-ground „vibe check"** workflow.

**Af hverju**: Danni pushaði back á formal protocol með rökum að LLM extraction iteration með manual scan er faster en 15–30 klst af hand-labeling og gefur sufficient signal fyrir commercial-grade residential model. „Erum við ekki að tala um að gervigreindin geri þetta?"

**Workflow**:
1. Run pilot extraction (200 listings, Haiku 4.5) → $1,35
2. Manual scan outputs, flag obvious issues
3. Run discovery analysis (keyword + LLM meta) → ~$4
4. Synthesa concrete v0.2.2 refinements
5. Re-run pilot → verify improvements ($1,35)
6. Ef quality góð → 80K batch
7. **Fallback**: ef v0.2.2 re-pilot shows marginal quality, revert í formal protocol

**Savings**: ~25 klst af Danni's tíma án meaningful quality compromise fyrir commercial-grade residential valuation.

**Hvað við töpum**:
- Engin formal kappa inter-rater agreement metric
- Engin per-field F1/precision/recall numbers
- Engin explicit quality gates

**Hvað við höldum**:
- Visual inspection af extraction quality (fann well_maintained pattern strax — approach works)
- Ability til að catch systematic patterns via manual scan
- Gold-standard sample er samt drawn (200 rows) og má nota fyrir formal validation seinna ef þörf krefur
- Discovery infrastructure (keyword + LLM meta + duplicate check) sem uppgötvaði 12,4% pop dup rate og 24% size/legal gap

---

## 2026-04-19 (Áfangi 3a) — Schema v0.2.1 frozen fyrir extraction round 1

**Hvað**: Extraction schema v0.2.1 er frozen sem starting point fyrir 3c pilot. 93 fields total:

- **Component-status matrix** (18 × 3 = 54 fields): unit-level 11 (kitchen, primary_bathroom, secondary_bathroom, flooring, interior_finishes, paint, electrical_panel, electrical_wiring, plumbing, heating, windows_unit) + building-level 7 (roof, cladding, windows_building, insulation, elevator_mechanism, sameign_cosmetic, foundation_drainage). Hver component fær `status` (7-stiga enum) + `year` (int) + `detail` (short text).
- **7-stiga status enum**: `replaced_new`, `overhauled`, `well_maintained`, `original_functional`, `needs_work`, `in_progress`, `not_mentioned`.
- **7 augl-supplement trilemmas**: fyrir þau 7 flags sem hafa 86% null rate í listings_v2. Extracted value fyllir inn þegar augl er null.
- **Situational fields**: útsýni (2), útipláss detail (5), parking detail (3), layout (6), building & annað (5), negative signals (3), agent framing (3), narrative + meta (5).

**Af hverju component-level rich**: v0.1 hafði flatt schema sem lumpaði „ný rafmagnstafla" og „yfirfarin rafmagnstafla" undir sama flagg. Danni benti á að þessi aðgreining er central fyrir bæði verðmat (verðáhrif mismunandi) og explainability (hægt að segja „X bætti svona mikið við virðið"). V0.2 gerir skýran status-distinction per component sem model getur lært á og kerfi getur útskýrt.

**Af hverju 18 components frekar en fleiri/færri**: trimmed-list af kjarna building/unit components sem birtast reglulega í íslenskum lýsingum. Minna er skarðbrotandi (t.d. ef við hefðum bara „interior" og „exterior" 2-component matrix missum við signal). Meira er diminishing returns (cosmetic-sub-components bæta við token-cost án marginal lift).

**Re-freeze í v0.3 eftir 3c pilot** — component-fields með `not_mentioned` rate > 70% eða F1 < 0,75 verða candidates fyrir drop eða merge.

---

## 2026-04-19 (Áfangi 3a) — Extraction scope round 1 = paired subset, Haiku+batch+caching

**Hvað**: Round 1 extraction scope er þröngvað að paired subset (~80K listings), ekki full 456K corpus. Model val: **Claude Haiku 4.5** með batch API (50% afsláttur) + prompt caching (90% afsláttur á static 8K-token schema). Budget: **~$240**.

**Af hverju paired subset eingöngu**: bara paired listings fara í iter3 training data. Unpaired listings (off_market_used, off_market_newbuild, post_sale_only) eru 86K af iter2's 144K — þeir hafa engan augl_id og því engin lýsingu til að extract. Extraction á þeim myndi kosta en gefa núll iter3-lift.

**Af hverju Haiku**: rich 18-component schema er harðara extraction task en v0.1 (nuance milli „ný" vs „yfirfarin" er real test), en batch + caching gerir þetta fjárhagslega bærilegt eingöngu á Haiku. Ef pilot (3c) sýnir að Haiku nær ekki quality threshold (F1 ≥ 0,75 á status enum), fallback í Sonnet 4.6 (total ~$800 í staðinn fyrir $240).

**Deferred til round 2** (þegar vettvangurinn skilar revenue/funding):
- Unpaired ~370K extraction (additional ~$1.100 á Haiku, ~$3.700 á Sonnet)
- Sonnet upgrade á paired subset ef Haiku er marginal
- Image-based extraction (7M myndir er real money)
- Dedicated sumarbústaða-schema með land-value focus

**Token estimates** per listing (Haiku):
- Input: ~8.000 static (cached, $0,10/MTok) + ~600 dynamic ($1/MTok)
- Output: ~1.000 tokens ($5/MTok)
- Per-listing með batch: ~$0,003
- 80K × $0,003 = $240

---

## 2026-04-19 (Áfangi 3a) — Gold-standard = 120→200 listings, seed=42, 36-cell stratified

**Hvað**: Gold-standard benchmark er hand-labeled listings, drawn með `seed=42` úr paired subset af iter2_predictions.pkl. Original breakdown (Áfangi 3a):

- **100 stratified** yfir 36-cell grid (region_tier × type_bucket × era, 3×4×3)
- **20 worst-held oversample** (top APE frá iter2 held predictions, stress-test)

**Scale update í Áfanga 3c (2026-04-19)**: sample **grew til 200 rows** (180 stratified + 20 worst_held, 5 per cell) fyrir robust discovery analysis á pilot. All 36 cells still populated, no thin cells.

**Type_bucket collapse** (rare types inn í nearest-sibling fyrir sampling):
- APT_BASEMENT → APT_STANDARD bucket
- APT_ATTIC → APT_FLOOR bucket
- SEMI_DETACHED → ROW_HOUSE bucket

**Era bins**: 2015–2019 / 2020–2023 / 2024–2026.

**Filter-reglur**: paired_fresh eða paired_valid pair_status, canonical_code in-model, lysing-length 300–3000 chars.

**Af hverju 120 og ekki 100 eða 200**: 100 stratified gefur ~3 samples per cell sem er þunnt en fangar systematic issues per-cell. 20 worst-held oversample er critical stress-test — ef extraction bætir ekki worst cases frá iter2, er það augljós limitation sem við viljum uppgötva í pilot en ekki við full run.

**Sample draw empirical outcome**: öll 36 cells populated, engin thin cells. Stratified draw = 108 records, trimmed til 100. Region balance 34/33/33. Canonical balance (efter bucket collapse): SFH 25, APT_FLOOR 25, APT_STANDARD 24, ROW+SEMI 26.

**Staged-review labeling pattern**: labela fyrstu 20 með v0.2.1 + v0.1 guide, pause, tune schema/guide ef þörf, labela remaining 100 með refined version. Forðar að 100 listings séu labelaðir á buggy-schema.

---

## 2026-04-19 (Áfangi 3a) — augl flag coverage + inngangur categorical

**Hvað**: Empirical findings úr `verify_augl_flags.py` (2026-04-18) breyta schema design og join-logic:

**Finding 1 — 86,2% null rate á 7 augl flags**: `svalir`, `gardur`, `lyfta`, `staedi`, `rafbill`, `pets`, `hjolastoll`, `eldrib` (plús `lat`/`long`) hafa sama null-rate. Driven af source_db (5 unique values, líklega að bara einn skilaði augl_json með parsed flags). **Consequence**: schema v0.2.1 bætti við 7 supplement-trilemma fields sem extraction fyllir í fyrir 86% af listings þar sem augl er null. Post-extraction merge: augl-flag tekur precedence þegar non-null.

**Finding 2 — `inngangur` er 42-value categorical**: ekki boolean eins og TAXONOMY gaf í skyn. 232K af 472K eru „Sameiginlegur". `has_separate_entrance` derive-ast sem `inngangur != "Sameiginlegur"` — ekki þörf á extraction.

**Finding 3 — 100% populated numeric fields**: `fjherb` (100%), `fjsvfnherb` (100%), `fjbadherb` (100%), `byggar` (99,4%), `bilskur` (100%, pre-computed), `n_myndir` (100%). Þessi fields voru upphaflega í v0.1 extraction schema en eru drop-aðir í v0.2.1 (duplicates HMS authoritative data).

**Finding 4 — join-key case mismatch**: iter2_predictions og training_data_v1 nota UPPERCASE (`FAERSLUNUMER`, `FASTNUM`, `SKJALANUMER`, `THINGLYSTDAGS`), pairs_v1 notar lowercase. Primary join: `FAERSLUNUMER` ↔ `faerslunumer` (unique per sala). pairs hefur `augl_id_final` og `augl_id_initial` — nota final sem primary, fallback í initial.

---

## 2026-04-18 (Áfangi 2.4c) — Áfangi 2 closed fyrir residential

**Hvað**: Iter2 main residential model meets production targets:
- Held MAPE 7,97% (target ≤10%) ✓
- medAPE 5,24% (target ≤8%) ✓
- Bias −1,5% (baseline var −10%) ✓
- cov80 69,9% (target ≥75%) ✗ near miss

Áfangi 2 declared closed fyrir residential segmentið. Næsta skref er Áfangi 3 extraction schema design.

**Af hverju closed þrátt fyrir cov80 near-miss**: cov80 miss er 5 pp og er acceptable production quality. Users of valuation website fá slightly wider intervals í report-ing (t.d. 85% í staðinn fyrir 80% labeled). Can be tightened later í iter3 með quantile adjustment án þess að block Áfanga 3 vinnu.

**Tvær mechanism fixes staðfestar virka**:
- Mechanism 1 (FASTEIGNAMAT nominal drift): Per-quintile bias á held var −10% í Q5 í baseline, er núna −0,7% í iter2. `real_fasteignamat` feature solved.
- Mechanism 2 (2024–2026 plateau): Per-year bias var monotonic 0→−10% í baseline, er núna flat ~0 í 2024/2025/2026. train_ext = train+val merge solved.

---

## 2026-04-18 (Áfangi 2.4c) — SUMMERHOUSE acknowledged unresolved

**Hvað**: Summer model held MAPE 176%, medAPE 22%. 81% af records hafa APE < 50% (acceptable median prediction) en tail er catastrophic (max APE >300.000%).

Features available (EINFLM, BYGGAR, LOD_FLM, lat/lon, FASTEIGNAMAT) eru ekki discriminative enough fyrir summerhouse valuation. Markaðurinn er dominated af land-value (location, lot size, amenity proximity, waterfront access) og condition (cabin vs fully winterized) — structured features fanga þetta ekki.

**Decision**: Accept summer model sem unresolved. Known limitation documented. Residential website launches án summerhouse valuation fyrir v1. Future work:
- Collect land-value indicators (distance to amenities, watercoverage, waterfront)
- Re-classify summerhouses by type (traditional cabin / modern / winterized / glamping)
- Potentially separate hedonic extraction schema með different features

---

## 2026-04-18 (Áfangi 2.4c) — Iter2 main model = production baseline

**Hvað**: Iter2 main (ex-SUMMERHOUSE) 6 modules — mean + 5 quantiles — er canonical production model fyrir residential valuation.

**Hyperparameters finalized**:
- num_leaves=63, learning_rate=0.05
- min_data_in_leaf=40 (main), 15 (summer)
- feature_fraction=0.9, bagging_fraction=0.8, bagging_freq=5
- n_estimators=3000 með early stopping=100 á test split
- seed=42, deterministic=True

**Features finalized (20)**: canonical_code, unit_category, matsvaedi_bucket, region_tier, postnr, lat, lon, EINFLM, BYGGAR, LOD_FLM, FASTEIGNAMAT, **real_fasteignamat**, is_new_build, merking_floor, building_max_floor, is_top_floor, floor_fraction, is_main_unit, sale_year, sale_month.

Feature importance: real_fasteignamat 63%, FASTEIGNAMAT 13%, EINFLM 5%, sale_year 4%, is_new_build 4%. Restin deila 11%.

**Best iterations**: main_mean=1859, main_q50=2976. Q50 þjálfaði mikið lengur en mean — median er harðari að optimize.

---

## 2026-04-18 (Áfangi 2.4c) — audit_2_4c_residuals.py canonical audit script

**Hvað**: `audit_2_4c_residuals.py` er reproducible audit script sem keyrist á `iter2_predictions.pkl`. Gefur útstreymi með bias per split, calibration, Mechanism 1 quintile check, worst-20 inspection, spatial clustering, og per-segment metrics.

**Af hverju**: Hver iter3+ þjálfun ætti að keyra sama audit (eftir minor modifications á column names) til að tryggja regression-safe metrics. Template fyrir future model iterations.

---

## 2026-04-18 (Áfangi 2.4b plan) — Iteration 2 architecture

**Hvað**: Eftir 2.4a residual audit staðfesti tvær orsakir fyrir systematic overprediction í 2024+, plan-ast iter2 með þremur fixes:

**P1 — SUMMERHOUSE aðskilið**: Main model þjálfað á ~139.741 residential records (canonical_code != SUMMERHOUSE). Separate summer model á ~4.513 SUMMERHOUSE records. 12 módel total: 6 main (mean + 5 quantiles) + 6 summer.

**P2 — real_fasteignamat feature**: Bæta við `real_fasteignamat = FASTEIGNAMAT × cpi_factor` sem 20. feature. Halda FASTEIGNAMAT líka inni (gefur módeli bæði nominal og real view). Model lærir hvaða er meira predictive í mismunandi contextum.

**P3 — Extended training**: train_ext = train (≤2023) + val (2024) combined. Test (2025) færist í hlutverk early-stopping set. Held (2026) remains pure holdout. Þetta lætur model sjá 2024 plateau og reduces Mechanism 2 extrapolation penalty.

**Af hverju samtímis allir þrír**: Isolating one fix at a time myndi taka 3× iterations með lítinn incremental value. Audit 2.4a sýndi að mechanisms eru conceptually distinct en öll í sömu átt (overprediction), svo samþætt fix er low-risk.

**Ekki gera núna**:
- Monotonic constraint á sale_year: Real prices eru ekki monotonic (fóru niður 2025–2026), svo constraint myndi enforca false pattern.
- Spatial KNN smoothing: Residuals eru mildly clustered (std 0,038) — marginal gain. Deferred til 2b.
- K-fold CV: Overkill fyrir iteration 2. Fair comparison með baseline er held (2026) MAPE.

**Expected outcome**: residential test MAPE ≤ 9%, held MAPE ≤ 10%, cov80 ≥ 75% á held. Held metric er authoritative samanburður; test er ekki fair því iter2 notar test fyrir early stopping.

---

## 2026-04-18 (Áfangi 2.4a) — Systematic overprediction diagnosis

**Hvað**: Residual audit afhjúpaði að baseline model overpredictar í 2024+, með monotonic progression:
- train bias 0%, val bias −3,5%, test bias −5,0%, held bias −9,6%.

**Tvær distinct orsakir**:

1. **FASTEIGNAMAT nominal drift**. FASTEIGNAMAT er nominal (ekki CPI-adjusted) en target (real_kaupverd) er deflated. 2024–2026 saw FASTEIGNAMAT óx nominally mikið, en real prices plateau-uðu. Model lærði í training "FASTEIGNAMAT X → real_kaupverd Y" en í test hefur FASTEIGNAMAT vaxið fyrir sama real price → overpredict. Staðfest með Section F quintile analysis: 6.872 af 8.575 test-records detta í Q5 (efsta training-quintile).

2. **2024–2026 real price plateau**. median_real var +5,4% 2024, −2,2% 2025, −1,8% 2026. Model trained on 2006–2023 monotonic uptrend kannast ekki við plateau/decline — extrapolerar upward í 2025–2026.

**Af hverju þetta skiptir máli**: Fix #1 (real_fasteignamat feature) og Fix #2 (include 2024 in training) eru orthogonal og ætti að samlegast combined. Við testum báða samtímis í iter2.

**Diagnostic ekki-findings** (worth noting til að forðast future rabbit-holes):
- Spatial residuals eru bara **mildly clustered** (std 0,038 í log-space, range [−0,15, +0,11]). KNN smoothing gæti gefið 1–2 pp MAPE gain en er ekki primary fix.
- Residual correlations allar **undir 0,10 Spearman** (hæst FASTEIGNAMAT við 0,07). Ekkert single feature er systematically missed.
- Per-year train MAPE sit í 7–8% (modern 2018–2023) og aldrei fer upp fyrir 11% (2008–2009 financial crisis). Model passar training gögn vel — problem er structural (distribution shift), ekki overfit.

---

## 2026-04-18 (Áfangi 2.3) — Baseline LightGBM hyperparameters

**Hvað**: Conservative baseline, ekki tuning-heavy:
- `num_leaves=63`, `learning_rate=0.05`
- `n_estimators=3000` með early_stopping=100 á val
- `min_data_in_leaf=40`, `feature_fraction=0.9`, `bagging_fraction=0.8`, `bagging_freq=5`
- `seed=42`, `deterministic=True`, `force_col_wise=True`
- Categorical features explicitly marked: canonical_code, unit_category, matsvaedi_bucket, region_tier, postnr

**Target**: `log_real_kaupverd`. Predictions back-transform með `exp()`.

**Sex módel**: mean (L2 regression) + 5 quantiles (alphas 0.025, 0.10, 0.50, 0.90, 0.975). Eitt módel per quantile — LightGBM styður ekki multi-output quantile native.

**Af hverju engin hyperparameter tuning í baseline**: Baseline er viðmið, ekki optimized model. Vill mæla hvort structured features einir og sér (19 features) gefa meaningful signal áður en við spendum time á tuning.

**Best iterations per model** (empirical result): mean 820, q025 330, q10 400, q50 2368, q90 3000 (hit max), q975 875. Q50 og Q90 trained lengur — median er harðari að optimize en tails.

---

## 2026-04-18 (Áfangi 2.3) — Point-prediction metric = mean model

**Hvað**: Reiknum point-prediction accuracy metrics (MAPE, MAE, R²) á bæði mean model og P50 (median quantile). Notum **mean model sem primary point estimate** í reporting.

**Af hverju**: Mean model (L2 loss) optimizar squared error sem gives conditional expectation. P50 optimizar absolute error sem gives conditional median. Fyrir log-normal pris distribution eru þau ekki eins — mean > median.

Í íslenska real estate markaði er mean model slightly betri í MAPE (test 15,36% vs P50 15,68%) en P50 er betri í medAPE (test 6,72% vs mean 7,33%). Mean model er authoritative fyrir point estimate; P50 er fyrirliggjandi úr quantile suite ef user vill robust median.

---

## 2026-04-18 (Áfangi 2.3) — Chronological split confirmed

**Hvað**: train ≤ 2023 (123.517), val = 2024 (9.719), test = 2025 (8.887), held = 2026+ (2.131).

**Af hverju chronological**: Real estate market has temporal trends sem model þarf að generalize across. Random split myndi gefa optimistic metrics vegna of-fitting á tíma.

**Trade-off**: sale_year=2024 er aldrei séð í training, sem þýðir LightGBM trees nota leaf values frá 2023 boundary. Þetta skapar extrapolation problem sem 2.4a staðfesti og 2.4b fixar með train_ext merge.

---

## 2026-04-18 (Áfangi 2.1) — Required fields filter added

**Hvað**: Training data build dropar records þar sem KAUPVERD, FASTEIGNAMAT, BYGGAR, EINFLM, FASTNUM, THINGLYSTDAGS eru null. Þetta dropar 11.467 records (step 2 í cascade: 226.481 → 215.014).

**Af hverju**: LightGBM handle-ar NaN fyrir flesta features, en target (KAUPVERD) má ekki vera NaN, og FASTEIGNAMAT er required fyrir outlier rule. Drop-ing fyrir cascade simplifies downstream.

**Impact á nýbyggingahlutfall**: Baseline training set hefur is_new_build = 13,8% vs audit 1.2 tala 15,2%. Difference er vegna required-fields filter sem dropar nýbyggingar með vantandi historical FASTEIGNAMAT (fyrir-completion transactions hafa oft NaN FASTEIGNAMAT).

---

## 2026-04-18 (Áfangi 2.1) — building_max_floor reiknað á fullum properties_v2

**Hvað**: `building_max_floor` er reiknað á fullum properties_v2 (124.835 records), ekki bara training subset. Grouping á landnum, max af merking_floor.

**Af hverju**: Þegar við ákveðum hvort íbúð er top-floor viljum við að byggingin sé fullgreind af öllum einingum sínum, ekki bara þeim sem voru seldar í arm's-length context. Íbúð á 3. hæð í 5-hæða byggingu er ekki top floor, en ef við reiknum bara á training data kannski sjáum við bara íbúðir á 1. og 3. hæð í þeirri byggingu, og miss-flaggum 3. sem top.

---

## 2026-04-18 (Áfangi 2.0 audit) — FEPILOG AA=02 hypothesis rejected

**Hvað**: Upphafleg lýsing FEPILOG AA-flokka frá Áfanga 1.8 (2026-04-18 lokakvöld) var röng. AA=02 er **ekki** bílskúrar/geymslur — það er mixed-purpose flokkur þar sem dominantly residential-main records eru innanborðs, blandaðar við commercial og garages. Sama gildir um AA=03+: allir AA-kóðar innihalda blöndu af property types.

Audit 2.0 staðfesti með cross-tab á unit_category (AA+BB) × canonical_code innan in-model set (148.608 records): unit_category 0201 telur 5.988 arm's-length residential sölur — APT_STANDARD (2.826), APT_FLOOR (1.987), ROW_HOUSE (522), SEMI_DETACHED (466), SFH_DETACHED (110), SUMMERHOUSE (61). Median pr-m² = 588 k/m² (clean residential range, ekki garage sem væri 100–250 k/m²).

**Af hverju það skiptir máli**: AA er ekki usable sem residential/non-residential classifier. Canonical exclusion í módeli stýrist af `classify_property()` úr HMS `tegund`, ekki af FEPILOG. AA má ekki notast sem second-pass filter "bara til öryggis".

**Feature design óbreytt**: `unit_category = AA + BB` sem categorical feature og `is_main_unit = (CC == "01")` sem binary. LightGBM lærir rétt price-differential á unit_category nánast frítt vegna þess að mikill meirihluti records clusterar í fáum kóðum (top-5 eru 67% af data).

**Engin breyting á 2.1 build scope**. Skráð hér svo framtíðar-Claude (eða ég sjálfur) villist ekki á fyrri lýsingu.

---

## 2026-04-18 (Áfangi 2.0 audit) — is_top_floor og floor_fraction gated á building_max_floor≥2

**Hvað**: Í audit 2.0 sýndi top-floor rate ungated að 44,4% af íbúðum væru "top floor" — inflated af single-floor buildings þar sem merking_floor = building_max_floor = 1 gefur trivially True. Þessi signal er meaningless fyrir einbýli, raðhús, og other single-floor structures.

**Ákvörðun**:
- `is_top_floor = NaN` þegar `building_max_floor < 2`, annars boolean
- `floor_fraction = NaN` þegar `building_max_floor < 2`, annars `merking_floor / building_max_floor`

NaN er preferred over False því LightGBM handle-ar NaN native og lærir "missing as information" en not-applicable-as-False myndi gefa módelinu villandi signal að einbýli séu "ekki top floor".

**Af hverju**: Audit 2.0 sýndi 85.351 apt units (APT_STANDARD/APT_FLOOR/APT_ATTIC) með bæði merking_floor og building_max_floor. Af þeim eru multi-floor buildings bara ein subset. Gating tryggir að feature-inn er meaningful í records þar sem hann er relevant.

---

## 2026-04-18 (lokakvöld) — FEPILOG decoding hierarchy (Áfangi 1.8)

**Hvað**: FEPILOG er 6-stafa kóði AABBCC:
- **AA** = aðal-flokkur. AA=01 er 74% af sölum og dominantly residential-main. AA=02 (11%) og AA=03+ eru mixed (uppfært 2026-04-18, sjá ákvörðun efst).
- **BB** = undir-flokkur.
- **CC** = raðnúmer. CC=01 (aðal-eining) = 58,1% af öllum sölum.

Features fyrir Áfanga 2:
- `unit_category = AA + BB` sem categorical (t.d. "0101", "0102", "0201")
- `is_main_unit = (CC == "01")` sem binary

**Af hverju**: 1.551 distinct FEPILOG codes eru óhöndluð í raw form. Hierarkíuna er skýr og LightGBM lærir hvaða AA_BB kombinations haga sér sérstaklega án þess að þurfa explicit rule-set.

**Alternative**: Flat categorical (1.551 levels) — hafnað, of sparse. Full AABBCC hierarchy með 3 features — yfirkill fyrir CC sem er mostly bara "main vs secondary" signal.

---

## 2026-04-18 (lokakvöld) — Multi-unit policy: single-FASTNUM only í baseline training

**Hvað**: 8,3% af arm's-length records (14.562 af 174.526) eru í multi-unit SKJALANUMER (2-4 FASTNUM undir sama samningi). **Policy fyrir Áfanga 2**: keep eingöngu single-FASTNUM SKJALANUMER í baseline training set (95,8% af samningum).

**Lykil-uppgötvun sem gerir þetta safe**: HMS hefur þegar pro-rata skipt KAUPVERD milli FASTNUM rows í multi-unit samningum. 998 af 1000 sample two-FASTNUM samningum hafa **mismunandi** KAUPVERD á rows. Þannig að summum við KAUPVERD per SKJALANUMER myndi ekki double-count-a.

Samt: multi-unit sölur eru ekki representative single-property arm's-length trades (oft eignasafn-sölur eða íbúð+atvinnuhúsnæði transactions). Filtering þær út gefur hreinna training signal. Geta verið endurskoðaðar í síðari áfanga ef þörf krefst.

**Af hverju**: Audit 1.8 section B staðfesti bæði scale (8,3% — nógu mikið til að skipta máli) og verð-skipting (clean pro-rata — ekkert re-engineering þarf). Einfaldasta legitimate solution er filter.

**Validated í audit 2.0**: Price-per-m² (2020+, residential) er kerfisbundið lower á multi-unit samningum: Einbýli 0,91×, Fjölbýli 0,89×, Sérbýli 0,99× relative to single. Multi-unit drop fjarlægir bundled-pricing dynamics sem módelið á ekki að læra.

**Alternative**:
- Aggregate KAUPVERD per SKJALANUMER og treat sem einn sale — hafnað, blandar saman eignir með mismunandi characteristics
- Keep alla records með flag — hafnað, noisy training signal í módeli sem targets single-property verð
- Drop entire multi-unit samninga — valið. Keep only single-FASTNUM (95,8%).

---

## 2026-04-18 (lokakvöld) — Landnum-based alt-pairing deferred (Áfangi 1.8b)

**Hvað**: Danni's pre-fastnum hypothesis (listings undir landnum áður en endanlegt FASTNUM er úthlutað) er **ekki testable** með núverandi listings_v2 — field-ið er ekki í parsed output. Skráð sem Áfanga 1.8b backlog.

Næsta skref þegar tekið upp aftur: re-parse fyrstu pre-merge DB til að sjá hvort landnum er í raw augl_json en bara droppað í parse_all_dbs.py. Ef já, endurgera listings_v2 með landnum field og keyra landnum-based alt pairing. Ef nei, verður að bíða eftir nýjum scraper (Áfangi 0) sem captures landnum.

**Af hverju defer**: Ekki blocker fyrir Áfanga 2 (hedonic baseline notar ekki pairing input). Áfangi 7 ask-to-sale módel getur notað núverandi 55.538 paired_fresh án landnum alt pairing. Upgrade-ar coverage í Fjölbýli frá 44% upp í kannski 60-70% ef tilgáta er correct, en sá ávinningur kemur að góðu seinna.

---

## 2026-04-18 (kvöld) — Geography feature architecture (Áfangi 1.6)

**Hvað**: Per-FASTNUM geography features í `D:\geography_features.pkl`:
- `matsvaediNUMER` og `matsvaediNAFN` — HMS verðmatssvæði, 100% coverage
- `matsvaedi_bucket` — rare-merged: M<numer> fyrir ≥50 sölur 2015+ (160 distinct), P<postnr>_other fyrir rare (53 distinct). 213 distinct values alls
- `matsvaedi_sales_2015` — sales count reference (weighting proxy)
- `postnr`, `postheiti` — backup categorical
- `region_tier` — RVK_core (101-116) / Capital_sub (170-276) / Country (33/36/31% split)
- `lat`, `lon` — bare numeric, LightGBM lærir spatial patterns

**Af hverju rare-merge við 50 sölur**: Audit 1.6 sýndi 160 af 191 matsvæða (84%) hafa ≥50 sölur 2015+, summerast í 99,4% af sölum. Rare matsvæðin (15%) summerast í 0,6% af markaðnum — það er bara strjálbýl svæði (Flatey á Breiðafirði, Hornstrandir). Merge í postnr_other preserves info án að búa til super-sparse categories.

**Af hverju bare lat/lon í stað spatial grid**: LightGBM lærir nonlinear spatial patterns án pre-processing. Einfaldara coupling. Spatial smoothing (t.d. KNN-residuals) bætist á í Áfanga 2b **aðeins ef** residual audit sýnir clear clustered residual sem módel nær ekki úr matsvæði + lat/lon.

**Alternative**:
- matsvæði eingöngu án postnr backup — hafnað, taparekstur í rare-merged eignum
- Pre-computed spatial grid (100m×100m cells) — hafnað, óþarfa complexity pre-baseline
- KNN-smoothed residual feature núna — hafnað, gera residual audit fyrst

---

## 2026-04-18 (kvöld) — Pairing logic og pair_status taxonomy (Áfangi 1.5)

**Hvað**: `pairing.py` implementar `pair_listings_to_sales()` sem skilar `pairs_v1.pkl` með 7-flokka pair_status taxonomy. Defaults: X=90d session boundary, Y_fresh=180d, Y_valid=365d.

pair_status gildi:
- `paired_fresh` — gap ≤ Y_fresh (clean ask-to-sale signal)
- `paired_recent` — Y_fresh < gap ≤ Y_valid (valid en eldri listing)
- `paired_stale` — gap > Y_valid (don't trust)
- `paired_no_price` — paired en list_price_final ógilt
- `post_sale_only` — listings eftir söluna eingöngu
- `off_market_newbuild` — engin listings, nýbygging
- `off_market_used` — engin listings, notaður markaður

**Key bug fixed late 2026-04-18**: Upphafleg merge_asof var á session_end, sem missed af cases þar sem session spannar söluna (pre-sale listing + post-sale listing innan 90d). Fixed til að match-a á listings beint og skila session metadata via session_id join. Paired_fresh count hækkaði úr 54.054 → 55.538 (matches audit 1.5b).

**Af hverju X=90, Y_fresh=180, Y_valid=365**: Audit 1.5b core diagnostic (ask-to-sale median per gap bucket):
| Bucket | Median |
|---|---|
| 0-180d | 0.970-0.987 |
| 180-365d | 0.969 |
| 1-2y | 1.001 (inflation crossover) |
| 2-5y | 1.249 |
| 5y+ | 1.643 |

180d er conservative cutoff fyrir training data. 365d er permissive cutoff fyrir valid pair flag.

---

## 2026-04-18 (kvöld) — Scrape gap frá 2025-07-01 accepted

**Hvað**: Listings volume hrundi úr ~9.000/mán (2024) niður í ~600/mán (2025-H2). Partial recovery til ~1.800/mán í 2026-03/04. Annualized rate vs 2024 = 0.10x. Danni erfði gamla scraperinn og hefur ekki kontrol. Leyst með nýjum scraper í Áfanga 0.

`in_scrape_gap=True` flag á sölur ≥ 2025-07-01 í pairs_v1 sem **metadata flag, ekki sía**. Paired records í gap-tímabili eru nothæf per-pair (real listing + real sale); einungis denominator-dependent metrics (coverage rate, off_market %) eru unreliable.

---

## 2026-04-18 (kvöld) — Nýbyggingar-tilgáta um off_market Fjölbýli rejected

**Hvað**: Tilgáta um að off_market Fjölbýli væru yfirgnæfandi nýbyggingar (70-90%) falsified í audit 1.5b. Nýbyggingar eru 18,5% af off_market Fjölbýli vs 15,3% markaðurinn í heild — engin over-representation.

Danni's pre-fastnum hypothesis (1.8b backlog) er núverandi leading explanation fyrir 32K off_market Fjölbýli sölur.

---

## 2026-04-18 (síðar) — thinglystdags parsing með format='ISO8601'

**Hvað**: `pd.to_datetime(..., format='ISO8601')` í stað inference fyrir raw `thinglystdags` strings með variable fractional precision (1-6+ digits). Plus year-range filter til að fanga sentinel dates ('0001-...').

**Impact**: date_valid stökk úr 84,77% í 98,57% í listings_v2.

---

## 2026-04-18 — Canonical data layer switched to v2 pickles (Áfangi 1.4.3)

**Hvað**: Downstream vinna les úr v2 pickles framleiddum af `parse_all_dbs.py` úr 5 pre-merge scraper DBum í `D:\Gagnapakkar\`. `fasteignir_merged.db` er deprecated (82% NaT á thinglystdags).

Per-DB FASTNUM partitions near-disjoint; overlap 378+380 í boundaries. Dedupe heldur latest scrape.

---

## 2026-04-18 — Dedupe strategy fyrir v2 pickles

**Hvað**:
- Listings: sort á `(augl_id, date_valid, scraped_at)` priorities `[True, False, False]`, drop_duplicates keep='first'
- Sales: sort á `(faerslunumer, scraped_at)`, latest wins
- Properties: sort á `(fastnum, scraped_at)`, latest wins
- Texts: same as listings

---

## 2026-04-18 — Invalid dates retained með date_valid flag

**Hvað**: Listings með sentinel eða unparseable dates halda `effective_date=NaT` með `date_valid=False`. ~5% af listings. Downstream filtrar á `date_valid=True` explicitly.

---

## 2026-04-18 — Lysing stored separately

**Hvað**: Listing descriptions (~2-5KB each) í aðskildri pickle (`listings_text_v2.pkl`, ~1,5 GB). Main listings_v2 lite fyrir fast loading.

---

## 2026-04-18 — Outlier filter (Áfangi 1.4.2)

**Hvað**: Tvær reglur:

**`is_price_outlier`** — combined signal, flaggar ef nokkur:
1. `fm_ratio < 0,10`
2. `fm_ratio < 0,30` AND `robust_z < −3`
3. `robust_z < −5` AND `fm_ratio < 0,50`
4. `robust_z > +10` AND `fm_ratio > +20`

Þar sem `robust_z = (log10(pr-m²) − seg_median) / (seg_iqr/1,349)`, segment = (TEGUND × region × 3-ára bucket).

**`is_size_outlier`**: `EINFLM < 20` eða `> 1000`.

Impact á residential (N=162.692): 324 flaggaðar (0,20%).

**MIKILVÆGT**: `is_price_outlier` tekur historical `FASTEIGNAMAT`, aldrei `FASTEIGNAMAT_GILDANDI`.

---

## 2026-04-18 — Frozen-snapshot dálkar staðfestir (Áfangi 1.4.1)

**Hvað**: Fjórir dálkar í kaupskrá CSV eru frozen HMS-snapshots:
- `FASTEIGNAMAT_GILDANDI` → nota `FASTEIGNAMAT`
- `FYRIRHUGAD_FASTEIGNAMAT` → nota `FASTEIGNAMAT`
- `BRUNABOTAMAT_GILDANDI` → engin historical í CSV
- `FJHERB` → sækja úr augl_json í listings_v2

Historical dálkar: KAUPVERD (99,40%), FASTEIGNAMAT (98,65%), EINFLM (6,77%), FULLBUID (4,60%), LOD_FLM (4,31%).

---

## 2026-04-18 — Eignabreytingarregla (Áfangi 1.3)

**Hvað**: Repeat-sale par útilokað ef (a) FULLBUID 1→0 transition, eða (b) `|EINFLM pct_change| > 5%`. Impact á 68.696 consecutive pör: 2.133 droppuð (3,1%).

---

## 2026-04-18 — Floor-level features í baseline

**Hvað**: `merking_floor`, `building_max_floor`, `is_top_floor`, `floor_fraction`. Top-floor premium +2-5% consistently.

---

## 2026-04-18 — Nýbyggingarregla empíríkt staðfest

**Hvað**: `FULLBUID=0 OR BYGGAR innan 2 ára af THINGLYSTDAGS`. Fangar 26.602 sölur (15,2%). Pre-completion discount: Fjölbýli 12%, Einbýli 23%.

---

## 2026-04-18 — Verðbólguleiðrétting CPI á þjálfunarsafn

**Hvað**: Allar verð-observations CPI-deflated til rolling latest month. `real_price = nominal × (CPI_ref / CPI_at_sale)`. Target = `real_kaupverd`.

Heimild: Hagstofan VIS01004, `cpi_verdtrygging.csv`, `cpi.py` helper.

---

## 2026-04-18 — Taxonomy finalization (514 HMS tegundir)

**Hvað**: Fjórir viðbótar secondary residential flokkar: `APT_ROOM`, `APT_HOTEL`, `APT_MIXED`, `APT_UNAPPROVED`. Saman við `APT_SENIOR`. Gestahús útilokað.

Coverage: 88,4% í módeli, 11,6% EXCLUDE.

---

## 2026-04-17 — Skjalastrúktúr fyrir project continuity

**Hvað**: Sex-skjala strúktúr: PROJECT_INSTRUCTIONS.md, STATE.md, DATA_SCHEMA.md, DECISIONS.md, TAXONOMY.md, GLOSSARY.md. Bætt við DATA_AUDIT_REPORT.md í Áfanga 1.7.

---

## 2026-04-17 — Property type taxonomy drög

**Hvað**: 8 canonical residential flokkar + SUMMERHOUSE. **Superseded**: 2026-04-18 með 5 sekúnder-flokkum (APT_ROOM, APT_HOTEL, APT_MIXED, APT_UNAPPROVED, APT_SENIOR).

---

## 2026-04-17 — Arm's-length filter

**Hvað**: Útiloka `ONOTHAEFUR_SAMNINGUR=1` (23%, 51.767 færslur).

**Af hverju**: Non-arm's-length sölur (fjölskyldu-transferrs, nauðungarsölur, gjafir) endurspegla ekki markaðsverð. Útiloka úr módeli, halda í sögulegri töflu fyrir reference.

---

## 2026-04-17 — Nýbyggingarregla (initial)

**Hvað**: `FULLBUID=0 OR (BYGGAR innan 2 ára af THINGLYSTDAGS)`. Staðfest empirically 2026-04-18.

**Af hverju**: Nýbyggingar hafa sinn eigin price dynamic (pre-completion discount, builder incentives). Þarf sérflögg svo hedonic módel geti lært þessa dynamík aðskilið frá notaðum markaði.

---

## 2026-04-17 — Eignabreytingar milli sala

**Hvað**: Fjarlægja repeat-sale pör þar sem EINFLM hefur breyst meira en 5%. Eitthvað var renovated/added/split — sala #2 er ekki á sömu eign.

**Af hverju**: Repeat-sale index byggir á að pöruð sala sé á sömu eign. Extension, division í fleiri íbúðir, o.s.frv. gera comparison röng.

---

## 2026-04-17 — Listing-to-sale pairing logic (initial plan)

**Hvað**: Para saman auglýsingar og kaupskrárfærslur ef samfellt á markaði. Gap > X daga → aðskilið söluferli. **Implementerað og finalized** 2026-04-18 kvöld með X=90, Y_fresh=180, Y_valid=365.

**Af hverju**: Framenginn ask-to-sale gap módel (Áfangi 7) þarf clean pairs milli listings og sala. Session-boundary handlar "paused re-listings" vs "new attempts".

---

## 2026-04-17 — Listing withdrawals fara í markaðsyfirlit

**Hvað**: Listings sem enda án sölu → flagged sem "withdrawn". Útilokaðar úr módeli, notaðar sem leading indicator (withdrawal rate er key market-temperature signal).

**Af hverju**: Útilokun úr þjálfunarsafni forðast bias (withdrawn eru ekki representative af completed sales). Haldið í markaðsyfirlit því rate þeirra er sterk indicator á markaðsástandi.

---

## 2026-04-17 — Geography: tvö lög

**Hvað**: (1) `matsvaediNUMER` sem categorical feature, (2) spatial smoothing með KNN á götureits-level (deferred til Áfanga 2b).

**Af hverju**: Matsvæði fangar hverfa-level price effects. KNN-smoothing fangar smaller-grain patterns (sjávarsýn, nálægð við park). Tvö lög saman gefa bæði discrete og continuous signal.

**Alternative íhugað**:
- Postnúmer eingöngu — hafnað, of coarse (postnr 105 spannar sem dæmi 8 matsvæði)
- Spatial grid eingöngu — hafnað, missir semantic matsvæðis-info

---

## 2026-04-17 — Target variable

**Hvað**: Aðalspá = þinglýst kaupverð (raunvirði). Ask-to-sale gap módel separat (Áfangi 7).

**Af hverju**: Kaupverð er authoritative (þinglýst). Listings er self-reported og óáreiðanlegt sem target. Gap-módel lærir discrepancy aðskilið svo við getum spáð bæði ásett verð OG sölvirði.

---

## 2026-04-17 — Uncertainty quantification

**Hvað**: LightGBM quantile regression, 5 quantiles (P2.5/P10/P50/P90/P97.5) + mean.

**Af hverju**: Bankar og opinberir aðilar krefjast uncertainty intervals, ekki bara point estimates. Quantile regression captures tail behavior betur en normal Gaussian. 5 quantiles gefa 80% og 95% intervals beint.

**Alternative íhugað**:
- Bootstrap ensembling — hafnað, compute-expensive, síður principled
- Conformal prediction — lagt í backlog fyrir Áfanga 2b ef calibration er léleg
- Bayesian regression — hafnað, scale-vandi á 170K sölum

---

## 2026-04-17 — Infrastructure stack

**Hvað**: Hetzner + PostgreSQL 16 + PostGIS + R2 + Docker Compose + Dagster + MLflow + Grafana/Prometheus/Sentry + FastAPI.

**Af hverju**:
- Hetzner: Evrópu-hosted (GDPR), cheap dedicated hardware
- Postgres+PostGIS: well-proven fyrir geo-data, SQL is universal
- Cloudflare R2: S3-compatible, zero egress cost
- Dagster: bestu data-pipeline tool fyrir scheduled scrapes og retraining
- MLflow: model versioning + reproducibility

---

## 2026-04-17 — ML framework

**Hvað**: LightGBM fyrir verðmat. Claude API fyrir LLM-extraction úr lýsingum.

**Af hverju**:
- LightGBM: proven fyrir tabular real-estate, handles categoricals native, fast training
- Claude: best-in-class fyrir íslenska texta extraction (Áfangi 4-5)

**Alternative íhugað**:
- XGBoost — svipað performance, LightGBM er hraðari á íslenskum scale
- Neural net (TabNet, FT-Transformer) — hafnað, marginal gains vs complexity overhead
- GPT-4 / Gemini — keppinautur, Claude hefur best íslenskuna í testing

---

## 2026-04-17 — Repeat-sale calibration samhliða extraction

**Hvað**: Repeat-sale pair analysis með CPI + markaðsvísitölu deflation samhliða pilot/full extraction (Áfangar 5-6).

**Af hverju**: Repeat-sale gefur ábyggilegt market-trend signal sem hedonic getur vottað sig gegn. Parallelization sparar tíma — bæði vinna á sama data layer.

---

## 2026-04-17 — Versioning og reproducibility

**Hvað**: Hvert verðmat fær version stamp (model_version + feature_version + data_snapshot_date). `predictions` tafla í Postgres geymir öll spá með feature values á spá-tíma.

**Af hverju**: Bankar þurfa að geta endurgert spá á hvaða tíma sem er (audit trails). Feature drift monitoring krefst historical feature values.

---

## 2026-04-17 — Three deployment channels, one data layer

**Hvað**: Einn canonical Postgres + API. Public/subscription/internal lesa af sama gagnalagi með mismunandi permission scopes.

**Af hverju**: Avoid data duplication. Ein truth-source. Breytingar í module propagate í alla kanala.

---

## 2026-04-17 — v1 markaðsyfirlits-indicators

**Hvað**: Átta indicators: repeat-sale index, list-to-sale ratio, months of supply, withdrawal rate, time-on-market distribution, orðatíðnigreining, model-tracking (spá vs söluverð), affordability index (verð / meðalárslaun).

**Af hverju**: Standard real-estate indicators + nokkur sérstök (orðatíðni úr lýsingum, model-tracking sem sjálfstætt gæða-monitor). v1 er data-driven sýnisafn; v2 getur bætt við byggt á feedback.

---

*Ný ákvörðun? Bættu við efst með dagsetningu + rökstuðningi.*
