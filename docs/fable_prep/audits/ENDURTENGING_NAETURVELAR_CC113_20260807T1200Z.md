# cc113 — ENDURTENGING NÆTUR-VÉLARINNAR VIÐ iter4r

**Dags:** 2026-08-07 · **Umfang:** liður (i) af PLANNING_BACKLOG viðauka cc112 — ENDURTENGING EIN.
Endurreikningur 953 raðanna (liður ii) er ÓSNERTUR og fær sitt eigið go.

## 0. Vandinn sem var leystur

cc112 setti útgáfuhlið á skrifleið nætur-verðmatsins af því adapterinn skoraði úr öðrum
heimi en framleiðslan: `D:\iter4a_*.lgb` (154 eiginleikar, óhreyfðir frá 21.04, stimpill
`iter4_final_v1`) meðan `pipeline_config.model_version` bar `iter4r_20260805_reglaR_strukt`
(156). Hliðið stöðvaði blæðinguna en tengdi ekkert; keðjan hefur ritað
`CHAIN FAIL (extraction)` hverja nótt síðan, sem ætlað var.

## 1. KORTLAGNING — munurinn lið fyrir lið

Fyrirmyndin er `D:\verdmat-is\precompute\rebuild_predictions_iter4.py`, vélin sem
skrifaði lifandi `public.predictions` við flippið (cc104/cc101).

| # | Þáttur | Adapter FYRIR (`phase_d3_score_extract`) | Framleiðsla (`rebuild_predictions_iter4`) |
|---|---|---|---|
| 1 | boosterar | `D:\iter4a_{main,summer}_{6}.lgb`, harðkóðuð mappa | `--artifact-dir D:\model_artifacts\<ver>`, skrár `<ver>_{grp}_{suffix}.lgb` |
| 2 | eiginleikar | **154** | **156** |
| 3 | nýju featurnar | engar | `n_ibudareininga` + `flm_hlutfall`, innspýtt úr `hms_classification_v1.pkl` (sha-hliðað) |
| 4 | conformal | `D:\iter4_conformal_corrections.json`, kaskadi seg_reg→seg→**global** | `<ver>_conformal.json`, kaskadi seg_reg→seg→**segcal** |
| 5 | framreiðslulag | ekkert | **3.3 ósamhverft** `<ver>_conformal_serving_v1.json`, `bil = mean_kr · exp(offset)`, punktmat ÓSNERT; D-flokkar aldrei gegnum lagið |
| 6 | kvantílar | aðeins `mean` + `q500` | allir sex (`q025/q100/q900/q975` bera segcal-fallbackið) |
| 7 | `model_version` | **harðkóðað** `iter4_final_v1` | `--model-version` = nafn artifact-möppu |
| 8 | `calibration_version` | harðkóðað `iter4_conformal_v1` | per röð: serving-útgáfa eða `<ver>_conformal_v1+segcal_fb` |
| 9 | verðmats-mánuður | **2026-04** (sale_year/sale_month eru EIGINLEIKAR) | **2026-07** |
| 10 | cpi-stuðull | `freeze_cpi_factor` = cpi[2026-09]/cpi[2026-07] | `CPI.factor('2026-07', to_ym='2026-09')` — **stóðst þegar á, 1,013006** |
| 11 | `confidence_grade` | ekki reiknaður | reiknaður af RÚNNUÐU bilunum, þröskuldar 0,240/0,443 |
| 12 | `region_tier` / `matsvaedi_bucket` | **lesnir af `public.properties`** | **AFLEIDDIR** úr `matsvaediNUMER` (rt_map úr þjálfunarramma, fallback `Country`) |

Liður 12 fannst ekki við kortlagningu heldur við mælingu — sjá §3.

## 2. TENGINGIN

- **Artifact:** `D:\model_artifacts\iter4r_20260805_reglaR_strukt` — VALIÐ út frá
  `pipeline_config.model_version`, ekkert harðkóðað. Fylgir næsta flippi sjálfkrafa.
- **Serving-lag:** `iter4r_20260805_reglaR_strukt_conformal_serving_v1.json`
  sha256[:16] = **`6e736a47b82d9130`** (staðfest gegn GO-inu).
- **hms-lind:** `D:\hms_classification_v1.pkl` sha256[:16] = **`16d78e39d57cfcad`**
  (sama hlið og rebuild-vélin ber; manifest `flip_status` bókar sama sha).
- **Manifest:** `iter4r_20260805_reglaR_strukt_manifest.json` sha256[:16] = `f0bb1e01eac9119b`,
  `n_features=156`, `train_end=2026-01-15`, `data_end=2026-07-31`.
- **3.1-conformal:** `iter4r_20260805_reglaR_strukt_conformal.json` sha256[:16] = `6dca5e405edee1bd`.

**Kvörðunar-kaskadinn er EKKI afritaður.** `_conformal_halfwidths`, `_serving_offsets`,
`_confidence_grade` og flokkaþröskuldarnir eru FLUTTIR INN úr `rebuild_predictions_iter4`.
Það var lexía cc112: tvö afrit sem drifu í sundur, og hlið sem varði aðeins annað þeirra.

### Hvers vegna hliðið hefur enn tennur

`MODEL_VERSION` er nú BINDING, ekki fasti. **VALIÐ** á artifacti kemur úr `pipeline_config`;
**STIMPILLINN** kemur úr `<ver>_manifest.json` Á DISKI. Læsi hliðið báðar hliðar úr sömu
töflu væri samanburðurinn sjálfgefið sannur og hliðið dautt. Nú ber það saman
*það-sem-var-hlaðið* gegn *því-sem-framleiðslan-segist-keyra*, og bítur á: möppunafn ≠
manifest, artifact sem vantar, og hverja pinnun sem fer fram hjá `pipeline_config`.
Sjálfgefna gildið er áfram `iter4_final_v1` — sé artifactið aldrei hlaðið FELLUR hliðið.

Þrjár hliðanir til viðbótar, allar mældar á undan fyrstu röð: feature-fjöldi ==
`manifest.n_features`; hms-sha; og **`FREEZE_ANCHOR_YM` == `pipeline_config.model_pred_anchor_ym`**
(flipp sem færir akkerið án þess að færa fastann myndi annars skala hverja einustu spá hljóðlaust).

**Hliðinu sjálfu (`assert_write_world_matches_live`) var ekki breytt — fallið er ekki í diffinu.**

## 3. SANNPRÓFUN 3(a)(b)(c)

### 3(a) feature-fjöldi
```
feature count            : 156
'n_ibudareininga' í lista: True
'flm_hlutfall' í lista   : True
```
Beinn samanburður boosteranna: 154 → 156, **bættist við** `['n_ibudareininga','flm_hlutfall']`,
**horfið** `[]`, röð óbreytt. `summer` ber sama 156-lista og `main`.

### 3(b) samanburður við LIFANDI `public.predictions`

Krafa: ≥100 eignir, frávik >0,5% á miðgildi ⇒ HALT.

**Breið sópun — hver 8. röð yfir allan alheiminn, n = 20.937:**

| reitur | max\|Δ\| kr | med \|Δ%\| | p95 \|Δ%\| | n≠ |
|---|---|---|---|---|
| real_pred_mean | **0** | 0,0000 | 0,0000 | **0** |
| real_pred_median | **0** | 0,0000 | 0,0000 | **0** |
| real_pred_lo80 | **0** | 0,0000 | 0,0000 | **0** |
| real_pred_hi80 | **0** | 0,0000 | 0,0000 | **0** |
| real_pred_lo95 | **0** | 0,0000 | 0,0000 | **0** |
| real_pred_hi95 | **0** | 0,0000 | 0,0000 | **0** |

`confidence_grade` 20.937/20.937 · `calibration_source` 20.937/20.937 ·
`calibration_version` 20.937/20.937 · `segment` 20.937/20.937.

**BÆTI FYRIR BÆTI, ekki „innan bils".** Þakið 0,5% var aldrei reynt á.

Lagskipt sópun (60 raðir í hverja sellu `calibration_source × confidence_grade`, n=420) þekur
allar fjórar kvörðunarleiðirnar — `serving_seg_reg` / `serving_seg` / `serving_global` /
`segcal_fallback` — og 12 segment, öll með max\|Δ\| = 0.

#### Frávikið sem mældist og var lagað (liður 12 í töflunni)

Fyrsta keyrsla gaf 22 af 800 SUMMERHOUSE-röðum með ólíkt `real_pred_mean`, max\|Δ\| 14,2 M kr.
Rakning: **allir tölulegir eiginleikar stemmdu nákvæmlega** (`einflm`, `matsvaedi_numer`,
`postnr`, `lat`, `lng`: 0/800 ólíkar gegn `properties_v2.pkl`). Frávikið var `region_tier`:
adapterinn las hann af `public.properties` en framleiðslan LEIÐIR hann af `matsvaediNUMER`.

Mælt á öllum alheiminum (n = 167.503): `region_tier` greinir á um **171** raðir,
`matsvaedi_bucket` um **1.158**. Hvort tveggja eru kategórískir LÍKANS-eiginleikar OG
`region_tier` er lykill kvörðunar-kaskadans, svo þetta var annar heimur — sama tegund
bilunar og cc112 stöðvaði, bara minni. Adapterinn leiðir þá nú eins og framleiðslan
(`mirror_derived_dims`). Eftir lagfæringu: SUMMERHOUSE 0/800 á öllum sex reitum.

### 3(c) cc112-útgáfuhliðið
```
útgáfuhlið: adapter 'iter4r_20260805_reglaR_strukt' == lifandi
            'iter4r_20260805_reglaR_strukt' — skrif heimiluð
```
Prófað á sömu tengingargerð og skrifleiðin notar (`autocommit=False`), og aftur í
raunkeyrslunni sjálfri. Hliðinu var ekki breytt.

### Aukamæling — E2-yfirlagið (útdráttarleiðin)
`has_extraction_data` = 0 á grunnlínu, 1 á full-leið; `n_ibudareininga`/`flm_hlutfall`
**eins í báðum eiginleikavigrum** (þeir voru settir í `_structural`-mengið — annars hefðu
þeir talist extraction-featurur og útdráttar-gapið mælst núll í hljóði). Grunnlína ==
lifandi `real_pred_median` á 116/116; gap ≠ 0 á 120/120, miðgildi −327.732 kr.

## 4. RAUNPRÓFUN (07.08 ~11:50Z)

`python scripts/run_extraction.py --forward 10 --confirm --value-limit 10`

| mæling | fyrir | eftir |
|---|---|---|
| `scraper.listing_valuations` alls | 21.595 | **21.605** (+10) |
| ↳ `iter4_final_v1` | 21.595 | **21.595** (ÓBREYTT) |
| ↳ `iter4r_20260805_reglaR_strukt` | 0 | **10** |
| raðir eftir 06.08T12:24:26Z (953-mengið) | 953 | **953** (ÓSNERT) |
| `scraper.listing_extractions` | 5.725 | **5.735** (+10) |

Haiku 10/10 ok, 0 hafnaðar, kostnaður **$0,071**.

**Stikkprufa (valuation_id 21600, fastnum 2184634):** `model_version` =
`iter4r_20260805_reglaR_strukt` ✓ · `expected_base` = 85.363.751 == lifandi
`predictions.real_pred_median` 85.363.751 ✓ · `expected_extraction` = 89.521.504
(gap +4.157.753). Sama mynd á 21601 og 21602.

**Um „nýju bilin/flokkinn":** `scraper.listing_valuations` BER ENGA bil-dálka og engan
flokk — taflan hefur aðeins `expected_base` / `expected_extraction` (bæði `real_pred_median`),
`extraction_applied`, `model_version`, `valued_at`. Bilin og flokkurinn lifa í
`public.predictions` (sýnd hér að ofan um join). Að láta frystu verðmötin bera þau er
migration og því SÉR ÁKVÖRÐUN, ekki hluti af endurtengingu.

## 4b. ÞAK Á NÓTTINA — GO 07.08 (viðbót eftir HALT)

Ákvörðun eigandans: keðjan keyrir í nótt **með `--value-limit 2000`**, ekki ~21.344 í einni
ómannaðri hrinu. Rök: tengingin hefur keyrt 10 raðir í raun; fyrsta stóra hrinan á að vera
VALIN en ekki afleiðing af fullri biðröð; enginn notendaflötur les töfluna svo ekkert liggur á.

**Hvar þakið var sett — þar sem keðjan les það, ekki handvirkt:**
`scripts/nightly_delta_chain.sh`, fasti `EXTRACT_VALUE_LIMIT=2000` við hlið
`DELTA_MAX_PAGES` / `NIGHT_BUDGET`, ásamt `EXTRACT_FORWARD=200`.

**TVÖ AÐSKILIN ÞÖK, ekki eitt.** `EXTRACT_FORWARD` þakar HAIKU-hrinuna (kostnað);
`EXTRACT_VALUE_LIMIT` þakar VERÐMATS-hrinuna (skrif). Þau eru ótengd: verðmats-biðröðin er
allt safnið sem á ekki verðmat undir lifandi `model_version` — ekki bara það sem var
útdregið í nótt — svo Haiku-þakið ver hana ekki. Það var einmitt gildran.

**Rökin eru byggð EINU SINNI og notuð af BÁÐUM greinum** (`local xargs=(...)`). Áður var
þurrkeyrslu-línan handskrifaður strengur við hliðina á raunkallinu og gat sagt eitt meðan
nóttin gerði annað. Þurrkeyrsla sem sannar ekki raunkallið sannar ekki neitt.

**Þurrkeyrsla (`bash scripts/nightly_delta_chain.sh --dry-run`, exit 0):**
```
[dry-run] would run: run_extraction --forward 200 --confirm --value-limit 2000
                     (max-n 500, daily-cap $10)
```

**Að talan BÍTI er sér mæling** — að flaggið sé sent sannar ekki að það klippi. Mælt um
sama fall og keðjan kallar (`fetch_extracted_listings_to_value`), read-only:

| | raðir |
|---|---|
| biðröð ÁN þaks | **21.372** |
| biðröð MEÐ þaki | **2.000** |
| klippt af nóttinni | **19.372** |

⇒ þakið bítur. Eftir nóttina standa ~19.372 eftir, ~10 nætur í viðbót á sama þaki.
Þegar biðröðin er tæmd verður þakið hlutlaust (biðröð < þak) og má hækka eða fjarlægja.
`bash -n` hreint.

**Dómur morgunvaktar 08.08:** n raðir skrifaðar (≤2.000), **allar** á
`iter4r_20260805_reglaR_strukt`, **0** á gamla stimplinum, og hliðið hleypti í gegn með
læsilegri log-línu í `scraper_data/logs/extraction_<TS>.log`
(`útgáfuhlið: adapter … == lifandi … — skrif heimiluð`; stderr er utf-8 frá cc112, svo
línan lendir ekki sem cp1252-hakk). Keðjulínan ber `valued N listings` gegnum
`summary`-grepið sem fyrir var.

**Liður (ii) er ÓSNERTUR af þessu og getur ekki lent í hrinunni:** 953-mengið ber gamla
stimpilinn `iter4_final_v1` og biðröðin síar á lifandi `model_version`, svo þær raðir
komast aldrei í þetta fetch.

## 5. ÓTEKIN ÁKVÖRÐUN SEM ERFÐIST AF TENGINGUNNI (staðan fyrir GO-ið að ofan)

Biðröðin er skilgreind sem „auglýsingar án verðmats **fyrir þetta `model_version`**".
Mælt 07.08: **3** undir gamla stimplinum → **21.354** undir þeim nýja. Nætur-keðjan keyrir
`run_extraction --forward 200 --confirm` án þaks, svo **næsta nótt frystir ~21.344 nýjar
raðir** undir nýja stimplinum. Það er ekki bilun heldur skilgreiningin, og það er ekki
liður (ii) (gömlu raðirnar standa óhreyfðar) — en það er hrina sem á að vera VALIN.

`--value-limit` var bætt við sem rofa (sjálfgefið ótakmarkað = óbreytt hegðun).
Neytandi töflunnar er `scraper.v_expected_vs_real` + ferskleikalínan á `/ops`; **engin
notendasíða les hana**, svo bakfyllingin er greiningarlag, ekki framleiðsluflötur.

**LEYST í §4b:** þakið sett á 2.000 í keðjunni sjálfri, þurrkeyrt og mælt að það bíti.

## 6. BREYTTAR SKRÁR

- `scripts/phase_d3_score_extract.py` — artifact-hamur (boosterar/conformal/serving/hms,
  allir sex kvantílar, ósamhverfu bilin, flokkur, afleiddu víddirnar tvær). Án
  `artifact_dir` er hegðunin óbreytt bæti fyrir bæti.
- `scripts/model_quality_eval.py` — `load_models_live_artifact()` + fjórar hliðanir;
  `ADAPTER_MODEL_VERSION` er nú sjálfgefið gildi, ekki eina gildið.
- `scripts/extraction_engine.py` — `load_serving_models()` bindur `MODEL_VERSION` við
  stimpil artifactsins af diski. **Hliðið sjálft ósnert.**
- `scripts/run_extraction.py` — kallar nýja hleðslarann; `--value-limit`.
