# GOLD_STANDARD_PROTOCOL — Hand-labeling protocol v0.2

**Útgáfa**: v0.2 (2026-04-18)
**Supersedes**: v0.1 (aligned við flatt v0.1 schema, retired)
**Alignment**: EXTRACTION_SCHEMA v0.2.1 (93 fields, 18-component matrix) + LABELING_GUIDE v0.1 (concrete field-by-field íslenskar instructions)
**Deliverable**: `gold_standard_v1.csv` með 100 hand-labeled listings úr paired subset + 20 worst-held oversample.

---

## Tilgangur

Skapa ground-truth benchmark fyrir LLM-extraction sem keyrist í Áfanga 3c. Tvö hlutverk:

1. **Accuracy-mæling**: reikna per-field precision/recall/kappa á Haiku/Sonnet/Opus extractions vs hand-labels á sömu 100 listings. Án þess erum við að fljúga blindur á ~80K-record batch-keyrslu.
2. **Schema-validation**: uppgötva schema-issues (ambiguous enums, missing fields, redundant fields) áður en við frystjum v0.3. Hand-labeling er fyrsta raunveruleiki-test á hvort 18-component matrix + 35+ situational fields er construct-anlegt á raun-lýsingum.

Protocol-ið byggir á því að öll concrete field-specific leiðbeiningar eru í LABELING_GUIDE.md (895 línu skjal með per-component reference, status-enum decision tree, og 3 worked examples). Þetta skjal skilgreinir eingöngu sampling, process, og quality metrics — ekki hvernig á að labela individual fields.

---

## Sample design

### Population

Sample dregst úr **paired subset** af listings_v2 (≈80K records) — nákvæmlega það subset sem fer í iter3 training og full extraction (~$240 budget). Sampling út fyrir paired subset myndi skila gold-standard sem matchar ekki extraction-target.

Filter-reglur fyrir population:
- `pair_status ∈ {paired_fresh, paired_valid}` úr `pairs_v1.pkl`
- `augl_id` hefur non-null `lysing` í `listings_text_v2.pkl`
- `canonical_code ∈ {APT_STANDARD, APT_FLOOR, APT_BASEMENT, APT_ATTIC, SFH_DETACHED, SEMI_DETACHED, ROW_HOUSE}` (in-model taxonomy)
- `300 ≤ len(lysing) ≤ 3000` chars (útiloka dead-text og ekstrem-long outliers)

Áætlað að ~70K records standist öll þessi skilyrði.

### Stratification

100 listings skiptast í 36-cell grid plús oversample fyrir hard cases. Stratification fangar þrjár helstu víddir sem iter2 performar mismunandi yfir:

- **Region tier**: RVK_core / Capital_sub / Country (3)
- **Property type**: APT_STANDARD / APT_FLOOR / SFH_DETACHED / ROW_HOUSE (4)
  - APT_BASEMENT, APT_ATTIC, SEMI_DETACHED rolled inn í nearest-sibling fyrir sampling (too rare fyrir eigin cell). V0.3 schema-refinement getur splittað aftur ef data supportar.
- **Sölu-era**: 2015–2019 / 2020–2023 / 2024–2026 (3)

Markmið: 3 samples per cell × 36 = 108. Trimmað niður í 100 með því að sleppa 8 thinnest-populated cells (líklega Country APT pre-2020 outliers).

**Oversample (viðbót við 100 primary)**: 20 listings sem eru worst-predicted á iter2 held (`ape ≥ 20%`). Stress-test — ef extraction bætir ekki þessi cases er augljós ceiling-limitation.

Total labeled: **120 listings** (100 stratified + 20 worst-held oversample).

### Sampling procedure

Aðskilinn Python script `draw_gold_standard_sample.py` (skrifað næst):

1. Load paired subset (paired_fresh + paired_valid) úr `pairs_v1.pkl`.
2. Filter sem lýst er ofan.
3. Stratify í 36 cells.
4. Random sample innan hvers cell, `seed=42`.
5. Nearest-cell fallback ef cell hefur < 3 records available.
6. Add worst-held oversample (top 20 ape frá `iter2_predictions.pkl` þar sem `iter2_split=='held'`).
7. Save sem `gold_standard_sample.csv` á D:\.

Output columns: `augl_id`, `fastnum`, `canonical_code`, `region_tier`, `sale_year`, `lysing` (full text, ekki preview), `sample_cell`, `sample_source ∈ {stratified, worst_held}`, `sample_order` (1–120, random).

`sample_order` er random integer fyrir labeling-röð — forðar drift þar sem labeler verður „þreyttur" í lok á einhverju subset.

### Seed og reproducibility

`seed=42` fyrir sample-draw. Skráð í DECISIONS.md eftir v0.3 freeze. Ef við viljum expand sample í v2 (fleiri listings), drögum við nýja með `seed=43` og sameinum.

---

## Labeling-ferli

### Tool

**Google Sheet** með tveimur tabs:

**Tab 1 `labeling`** — einn row per listing, ~95 columns:

- **Context** (6 cols): sample_order, augl_id, canonical_code, region_tier, sale_year, lysing (full text í cell — Google Sheets limit er 50K chars per cell, og lýsingar eru < 3K).
- **Component matrix** (54 cols): fyrir hvert af 18 components → 3 cells (`status_<component>`, `year_<component>`, `detail_<component>`).
- **Augl-supplement trilemmas** (7 cols): `has_balcony`, `has_garden`, `has_elevator_available`, `has_assigned_parking`, `has_ev_charging`, `is_accessible`, `is_senior_marketed`.
- **Situational fields** (~25 cols): view_type (multi-select), view_quality, balcony details, garden, parking, layout, building & annað.
- **Negative signals** (3 cols): reported_issues (multi-select), needs_immediate_work, sold_as_is.
- **Agent framing** (3 cols): agent_lead_selling_point, urgency_signals, listing_elaboration.
- **Narrative & meta** (7 cols): property_narrative, extraction_notes, listing_lang_is_icelandic, listing_minimally_informative, labeler_id, labeled_at, confidence_notes.

Notum **data validation dropdowns** á öll enum columns. Blokkar typos og tryggir consistent value names. Fyrir multi-select fields (view_type, reported_issues, storage_type): notað semicolon-separated string í cell — „sea;mountain" er parsed sem list í post-processing.

**Tab 2 `guide`** — link eða copy af LABELING_GUIDE.md sem quick reference meðan labeling stendur yfir.

### Labeling-röð

120 listings í random sample_order. Mæli með 20-stafla blokkum með pásum.

**Ekki nota LLM-extraction sem prior**. Labeler sér aldrei hvað Claude væri að segja áður en hand-label er sett. Spillir independence — labeler myndi líklega sammælast Claude oftar en hann myndi ef hann kom blindur að textunum.

### Staged review pattern (mikilvægt fyrir schema quality)

Þetta er lykil-breyting frá v0.1 protocol-i sem leggur áherslu á iterative refinement:

1. **Label fyrstu 20 listings** í quick pass (~3 klst).
2. **Pause og self-review**: skoða own labels, flagga ambiguities, skrifa í `confidence_notes` hvað var óljóst.
3. **Schema/guide refinement**: ég update-a LABELING_GUIDE og mögulega schema v0.2.1 → v0.2.2 byggt á findings. Labeler gerir re-label á fyrstu 20 ef needed.
4. **Continue 80 á refined-guide**: labeler klárar 80 sem eftir eru með tuned instructions.
5. **Final 20 worst-held oversample**: labeled síðast til að sjá hvort extraction/schema standast edge cases.

Þessi staging forðar að 100 listings séu labelaðir á buggy-schema og þurfi re-label. Cost: pausing forces tuned consistency.

---

## Inter-rater setup

### Primary labeler

**Danni** labelar öll 120 listings.

### Secondary labeler

Sótt síðar — ideal: fasteignasali eða einhver með mikla reynslu í að lesa fasteignalýsingar. Secondary labelar 30 af 100 stratified (ekki úr oversample-partinu, því þær eru stress-test aðskildar) í **blindu setup** — annað Google Sheet án aðgangs að Danni-labels.

Fallback ef secondary er ekki í boði: Danni labelar sömu 30 aftur með 1+ vikna gapi. Intra-rater agreement er weaker ceiling en inter-rater, en betra en ekkert.

### Disagreement resolution (eftir secondary-labeling)

1. Reikna per-field agreement á shared 30 listings.
2. Fyrir hvert field með < 70% agreement: labelers skoða saman, ráða rót (oftast ambiguous instruction í LABELING_GUIDE, ekki labeler-error).
3. Update LABELING_GUIDE eða mögulega schema v0.2.x → v0.3. Re-label disputed cells með refined instruction.
4. Genuine ambiguity (< 70% agreement eftir re-label) → accept sem known limitation og skrá í DECISIONS.md. Field gæti orðið candidate fyrir merge eða drop í v0.3.

---

## Quality metrics

### Per-field accuracy

Reiknað sjálfvirkt á shared 30-listing subset (primary + secondary labels). Metrics per field-type:

| Field-type | Metric | Threshold fyrir „nothæft" |
|---|---|---|
| Trilemma (yes/no/not_mentioned) | Per-class F1 | F1 ≥ 0,85 á `yes` og `no` classes |
| Status-enum (7 ordered values) | Cohen's quadratic-weighted kappa | κ ≥ 0,70 |
| Categorical nominal (agent_lead_selling_point, parking_type, view_quality, heating_type) | Cohen's unweighted kappa + per-class F1 | κ ≥ 0,65, F1 ≥ 0,80 fyrir common classes |
| Numeric (year fields) | Exact-match + ±1 year tolerance, MAE | Tolerance-match ≥ 0,80 |
| Multi-select enum (view_type, reported_issues, storage_type) | Mean Jaccard similarity per listing | Jaccard ≥ 0,70 |
| Free-text (property_narrative) | Qualitative review of 20 samples | Subjective pass/fail |

Threshold-in eru lower-bound fyrir fieldið til að vera tekið inn í iter3 training. Lower F1 er acceptable á status-enum (7-class) en á trilemma (3-class) vegna intrinsic difficulty.

Output: `gold_standard_agreement_report.md` með per-field kappa-töflu og agreement-breakdown.

### Coverage metrics

Aðskilið frá accuracy — mælir hve oft fieldið er extract-able í fyrsta lagi. Reiknað á full 100-listing primary-labeled sample (ekki bara shared 30).

**`not_mentioned` rate per field**. Ef > 70% á component status → fieldið er svo sjaldgæft-nefnt að það bætir ekki signal. Component er samt extracted (kostar ekki meir), en `not_mentioned` er encoded sem sér category í LightGBM features frekar en dropped.

**Distribution balance per enum**. Ef > 90% af values fara í eitt enum-value → fieldið er degenerate og bætir ekki discriminative signal. Candidate fyrir v0.3 drop ef mega mega skinny.

### Pilot-level signal check

Þegar 120 pilot-extracted JSON eru til (Haiku + Sonnet + Opus keyrt á sömu 120 í 3c):

Reikna Pearson correlation milli key extracted features (interior_condition_score, roof_status_ordinal, view_quality_ordinal, þ.m.t. composite scores) og `residual_log_iter2` (per-listing bias frá iter2 hedonic).

Fields sem **ekki correlate-a** á 120-listing sample eru unlikely að gefa lift í 144K training — en small-N er ekki conclusive. Fields sem **correlate strongly með residuals** eru high-confidence candidates fyrir iter3 feature set.

---

## Deliverable format

Vistað á D:\ fyrir reproducibility:

**`gold_standard_v1.csv`** (120 rows × ~95 columns):
- Context + labels + meta (eins og Google Sheet tab 1 layout)
- Exported úr Google Sheet með File → Download → CSV
- Nota UTF-8 encoding (ekki UTF-16LE sem Google gerir default stundum)

**`gold_standard_agreement_report.md`** (generated eftir secondary labeling):
- Per-field agreement tafla
- Coverage per field tafla
- Top-5 systematic disagreements með dæmum
- Schema-refinement recommendations fyrir v0.3

**`labeling_iteration_log.md`** (evolving document, editable á meðan labeling er í gangi):
- Log af hvaða breytingar var gerðar á LABELING_GUIDE á milli 20-listing batches
- Listar yfir ambiguous phrase-decisions sem voru nagla-ðar niður
- Tricky-cases log (spesifíkar lýsingar og hvernig þeim var handled)

---

## Schema-refinement loop

Hand-labeling er ekki einnota — það er feedback loop inn í schema v0.3.

1. Label fyrstu 20 listings með v0.2.1 schema og v0.1 guide.
2. Review. Hvaða fields hafa labeler trouble? Hvaða fields eru consistently `not_mentioned`? Hvar er guide ambiguous?
3. Revise LABELING_GUIDE og, ef þörf, schema v0.2.1 → v0.2.2.
4. Re-label first 20 með refined guide til að sjá hvort disagreements leysast.
5. Label remaining 80 með v0.2.2.
6. Secondary labels 30 (blindur).
7. Agreement report genererast. Schema v0.3 skrifað með final field set.
8. Label 20 worst-held oversample.
9. **DECISIONS.md entry**: „Schema v0.3 frosið með eftirfarandi changes frá v0.2.x: ..."

Þessi loop forðar trap af því að label 100 listings á buggy schema og uppgötva fyrst eftir að schema þarf að breyta — sem myndi kosta re-labeling.

---

## Verkefnis-áætlun

Röð, ekki dagatal:

1. **Schema v0.2.1 frozen** ✓ og **Labeling guide frozen** ✓ → **Gold-standard sample draw** (næsta skref — ég skrifa `draw_gold_standard_sample.py`).
2. **Google Sheet setup** — ég get gefið template með column-specs, eða þú smíðar út frá 95-column lista. Dropdown data validation á öll enum columns.
3. **Label 20** með v0.2.1 + guide v0.1.
4. **Review + schema/guide tune** (ef þörf).
5. **Label remaining 80**.
6. **Secondary labels 30** þegar Danni hefur fundið fasteignasala.
7. **Agreement report** → schema v0.3 freeze → DECISIONS entry.
8. **Label 20 worst-held oversample**.
9. **Pilot extraction (3c)**: Haiku + Sonnet + Opus á sömu 120 listings → comparison við gold.
10. **Go/no-go decision** fyrir full-scale extraction (3d): ~80K paired, Haiku + batch, ~$240.

---

## Hvenær er gold-standard „nóg"?

120 listings eru empirically nóg fyrir:
- Per-field kappa með ~0,08–0,10 confidence interval á agreement estimate
- Detection á systematic failures í component-status matrix (18 components × 7 statuses)
- Coverage estimation með ±8 pp precision á ~70% `not_mentioned` threshold
- Identification á schema-level bugs (redundant fields, ambiguous enums, missing fields)

120 eru **ekki** nóg fyrir:
- Per-region per-type breakdown af accuracy (sample er thin per cell — 2–3 samples per stratification cell)
- Catching 1-in-1000 edge cases (t.d. flood-damaged listings eða historical-designation premium)
- Per-component accuracy með high precision fyrir **alla 18** components — sumir verða aldrei labelaðir ef 95% af listings segja „not_mentioned" um t.d. `foundation_drainage`

Það sem 120 gefa okkur er **green-light með measured expectations** fyrir að keyra full batch. Ef Claude performar > 85% F1 á Tier 1 components (kitchen, primary_bathroom, flooring, electrical_panel, roof, cladding) á 100-sample, er líklegt að það haldi á 80K með well-calibrated uncertainty.

---

## Takmarkanir og afsakanir

Þetta gold-standard er **íslensk-málssérfræði** labeling. Núverandi primary labeler er tæknimaður (Danni), ekki fasteignasali. Secondary (fasteignasali) sótt síðar — þangað til eru primary labels authoritative. Danni er reyndur nóg til að dæma flest components sannfærandi, en edge-case sérfræði (t.d. dæma sameign-quality í hverfa-samhengi, eða read-between-lines á agent-framing) gæti vantað.

Gæti valdið:
- Over-reliance á explicit language í lýsingu (Danni labelar það sem hann sér; reyndur fasteignasali myndi infera meira úr subtle cues).
- Lower recall á negative signals sem fasteignasali myndi lesa á milli línanna.
- Mögulegt bias í `agent_lead_selling_point` — tæknimaður getur túlkað lead-ið öðruvísi en fasteignasali.

V0.3 refinement eftir secondary-labeler review lagar þetta.
