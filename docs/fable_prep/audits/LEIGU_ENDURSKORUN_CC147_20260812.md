# LEIGU-ENDURSJÓNUN — ÞREP 2 AF 4 (ENDURSKORUN)

**cc147 · 2026-08-12 · STAGING ONLY · HALT fyrir flipp**

Mælikóði: `precompute/cc147_endurskorun.py` (explicit paths, ein keyrsla + `--stage-only`).
Mælitöflur + keyrslulog: `D:\_audit\cc147_leigu_endurskorun\`.
Artifact: `precompute/data/processed/rent_conformal_corrections_reglaR_20260812.json`.
Manifest: `precompute/data/processed/rent_v1_reglaR_20260812_manifest.json`.
Staging: `public.predictions_rent_cc147_staging` (158.314 raðir, RLS virk, 0 policies).
Frestur umferðarinnar: **01.09**.

**Bann virt upp á rað:** `predictions_rent` LIFANDI ósnert (`rent_v1_nan`,
Σ`pred_mean` = 48.454.595.294 óbreytt eftir keyrslu) · `valuation_tiers_rent` ósnert
(þrepavélin er ÞREP 3 og var **ekki** endurkeyrð) · `leiga_train.parquet` ósnert á
diski (mtime 2026-06-29 23:49; öll endurmerking gerist í minni) · þröskuldar óbreyttir
(`MIN_N`=30, `MIN_LOCAL`=5, `THRESHOLDS`, `GRADE_A/B`, `SEED`=42, `SPLIT`=60/20/20) ·
enginn framendi snertur · ekkert flippað.

---

## 0. MÆLITÆKIÐ SANNAÐ FYRST (fjögur hlið, öll í kóðanum, öll fella keyrsluna)

| hlið | hvað er endurgert | niðurstaða |
|---|---|---|
| **G1** | `rent_conformal_corrections.json` úr parquet + `grouped_split(seed=42)` | 38 sellur (6 srt / 22 sr / 10 cc), **0 mismunur** á `n_calibration`; calib n = 22.622 |
| **G2** | `predictions_rent.segment` úr PRE-cc78 `canonical_code` + frosnu sellunum | **0 mismunur á 158.314 röðum** |
| **G3** | **NÝTT:** `pi80` = `e^q80 − e^−q80` gegn lifandi `(hi80−lo80)/mean` | max\|frávik\| = **8,33·10⁻⁶**, 0 raðir yfir 1e−5 |
| **G3b** | `valuation_tiers_rent.pi80_pct` gegn útreiknuðu | max\|frávik\| = **0,0050 pp** |
| **G4** | **STERKASTA:** full endurskorun á FROSINNI merkingu í dag (skorun **B**) gegn lifandi töflu | **max\|Δ\| = 0 kr. á öllum 158.314 röðum og öllum fimm spádálkum** |

G3 var nauðsynlegt af því afurð þessarar lotu ER bilið: án þess gats væri
pi80-mælingin ósönnuð. G3 sannar líka **að `pi80` er hreint fall af `q80` sellunnar
og því ÓHÁÐ level-akkerinu** — hvorki `k_global` né `HFAC` geta hreyft dómskilyrðið.

**G4 er það sem gerir alla lotuna læsilega.** Endurskorunarvélin endurgerir lifandi
töfluna BIT FYRIR BIT þegar hún fær frosnu merkinguna. Þar með er **allt** sem mælist
milli B og C endurmerkingin sjálf — ekkert rek í `properties`, engin mæliskekkja,
engin ólíkindi í LightGBM-fitti. Sundurliðunin rek-vs-endursjónun er því ekki mat
heldur bókhald: rekið er **núll**.

---

## 1. HVAÐ VAR GERT

`rent_v1` er **óbreytt í arkitektúr** — sömu `FEATURES`, sömu `PARAMS`, sama
`N_ROUNDS`=800, sami `HERB_DROPOUT`, sami kaskadi. Aðeins **merkingin** breytist:
`canonical_code` er lesið lifandi úr `public.properties` **báðum megin** joinsins
(S2, cc135/cc146-aðferðin). S1 (frosin merking þjálfunarmegin, lifandi
skorunarmegin) er BÖNNUÐ — hún gefur þynnku sem er ekki til.

- Leigusamningar 2011–2023: **32.438 af 111.818 (29,01 %)** bera annað
  `canonical_code`; 10 fastnúmer finnast ekki í `properties` og halda parquet-merkingu.
- Rek á öðrum ásum (bókað, EKKI hluti S2): `unit_category` 21 samningar,
  `region_tier` 10 samningar. S2 snertir aðeins `canonical_code`.
- Conformal-sellur: **38 → 31** (srt 6→3, sr 22→19, cc 10→9), `global` q80
  0,1950 → 0,1972.

Þrjár skoranir svo rek og endursjónun aðskildust:

| | merking | conformal-artifact | hlutverk |
|---|---|---|---|
| **A** | lifandi `predictions_rent` (skorað 2026-05-01) | frosið | FYRIR |
| **B** | `properties_canonical_pre_cc78`, skorað í dag | frosið | REK-einangrun |
| **C** | S2 (lifandi cc báðum megin), skorað í dag | **nýtt** | EFTIR |

**A → B: 0 kr. frávik, 0 segment-frávik, 0 fallback-frávik.**
**B → C er endursjónunin, hrein.**

---

## 2. FORSPÁRPRÓFIN a–c, DÆMD

### a. `fallback_lvl` — **STENDUR**

| fallback_lvl | | fyrir | eftir | breyting |
|---|---|---:|---:|---:|
| 0 | `cc\|region\|tegund` | 17.654 | 36.098 | **+18.444** |
| 1 | `cc\|region` | 139.890 | 121.392 | −18.498 |
| 2 | `cc` | 575 | 573 | −2 |
| 3 | `global` | 195 | 251 | **+56** |

Spá cc146: **1→0 á ~18.446** → raun **18.446**. **1→3 á ~56** → raun **56**.
Báðar upp á rað. Að auki: 0→1 á **2 röðum** (2104432, 2161075 — `SFH_DETACHED|Country|Einbýli`
→ `ROW_HOUSE|Country` / `APT_FLOOR|Country`) og 2→1 á 3 röðum; hvorugt var spáð
en hvorugt stangast á við spána (hún var sett fram um tvö tilteknu hólfin).

### b. Þrep — **STENDUR**

| þrep | lifandi | eftir | breyting |
|---|---:|---:|---:|
| T1 | 32.526 | 32.526 | 0 |
| T2 | 71.560 | 71.560 | 0 |
| T3 | 20.972 | 20.973 | **+1** |
| T4 | 19.161 | 19.160 | −1 |
| **T5** | **14.095** | **14.095** | **0** |

Spá cc146: ~1 víxl, T5 ~14.095 → raun **1 víxl, T5 = 14.095**. Víxlið er
**fastnum 2297138** — nákvæmlega sú röð sem cc146 nafngreindi, T4→T3
(`SEMI_DETACHED` → `ROW_HOUSE|RVK_core`, fb 2→1, n_local 40).
Spáin lenti á RÖÐINNI, ekki bara á tölunni.

Ástæðufærslan lenti líka: `of_fair_samningar` 13.586 → **13.530** (−56),
`engin_svaedisgogn` 195 → **251** (+56), `eignaflokkur` 314 óbreytt.
Þetta er bókað sem **færsla**, ekki lagfæring: raðirnar 56 voru þegar í T5
vegna þéttleika og eru það áfram — það sem breytist er hvað kerfið segir að
sé að.

**Þetta er staðfesting, ekki vonbrigði.** Dómskilyrðið var bókað fyrirfram.

### c. pi80-BREIDDARDREIFINGIN — afurð lotunnar

Nefnari alls staðar talinn. Öll gildi í %; `d_p50` í prósentustigum.

| hópur | n | p10 fyrir | **p50 fyrir** | p90 fyrir | p10 eftir | **p50 eftir** | p90 eftir | Δp50 | Δmeðaltal | þrengist | víkkar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **ALLT ÞÝÐIÐ** | **158.314** | 29,65 | **39,11** | 58,74 | 26,87 | **38,54** | 61,34 | **−0,57** | **+1,65** | 105.460 | 52.854 |
| fjölskylda = FJÖLBÝLI | 101.867 | 24,88 | 39,11 | 46,76 | 26,87 | 38,54 | 41,98 | −0,57 | −1,23 | 82.544 | 19.323 |
| fjölskylda = SÉRBÝLI | 56.447 | 29,65 | 46,76 | 62,84 | 36,14 | **57,76** | 61,34 | **+11,01** | **+6,86** | 22.916 | 33.531 |
| fb fyrir = 0 | 17.654 | 58,74 | 62,13 | 62,84 | 57,75 | 61,34 | 61,34 | −0,80 | −2,36 | 17.654 | 0 |
| fb fyrir = 1 | 139.890 | 29,65 | 39,11 | 46,76 | 26,87 | 38,54 | 61,34 | −0,57 | +2,16 | 87.806 | 52.084 |
| fb fyrir = 2 | 575 | 41,11 | 41,11 | 41,11 | 42,27 | 42,27 | 42,27 | +1,16 | +1,52 | 0 | 575 |
| fb fyrir = 3 | 195 | 39,25 | 39,25 | 39,25 | 39,69 | 39,69 | 39,69 | +0,44 | +0,44 | 0 | 195 |
| fb eftir = 0 | 36.098 | 29,65 | 46,76 | 62,84 | 57,75 | **61,34** | 61,34 | **+14,58** | **+8,55** | 17.652 | 18.446 |
| fb eftir = 1 | 121.392 | 29,65 | 39,11 | 46,76 | 26,87 | 38,54 | 46,89 | −0,57 | −0,39 | 87.767 | 33.625 |
| víxla segmenti | 57.473 | 24,88 | 41,36 | 46,76 | 26,87 | 38,54 | 61,34 | −2,83 | **+7,83** | 18.363 | 39.110 |
| víxla EKKI segmenti | 100.841 | 29,65 | 39,11 | 62,13 | 26,87 | 38,54 | 61,34 | −0,57 | −1,87 | 87.097 | 13.744 |

**Miðgildið og meðaltalið segja andstæða sögu og bæði eru rétt.** Miðgildið fer
niður um 0,57 pp (fjölbýlis-massinn þrengist lítillega á endurreiknuðum leifum);
meðaltalið fer UPP um 1,65 pp af því 18.446 raðir stökkva úr ~39 % í ~61 %
þegar þær ná loks í sína eigin Einbýli-sellu. **Engin röð stendur kyrr**
(óskert = 0) — endurskorunin snertir bilið á öllum 158.314 röðum.

Efnislega niðurstaðan er á SÉRBÝLI: miðgildisbreidd **46,76 % → 57,76 %
(+11,01 pp)** á 56.447 eignum. Það er ekki afturför heldur mælingin sem
cc146 gat ekki gert: sérbýli var að lesa fjölbýlis-sellu og bar of þröngt bil.

### Sundurliðun breiddarinnar — hólfun gegn leifum

| leið | pi80 miðgildi | pi80 meðaltal |
|---|---:|---:|
| A/B frosið (hólfun frosin, leifar frosnar) | 39,11 | 41,09 |
| aðeins NÝ HÓLFUN (leifar frosnar) | 39,31 | **43,15** |
| aðeins NÝJAR LEIFAR (hólfun frosin) | 39,01 | 42,87 |
| **C = báðar (staðið)** | **38,54** | **42,74** |

Ásarnir tveir eru **ekki samleggjandi**: hvor um sig gefur breiðara meðaltal en
báðir saman. Ný hólfun ber meira af hreyfingunni en nýjar leifar, en hvorug
skýrir hana ein.

### Flokkur A–D

| flokkur | fyrir | eftir | breyting |
|---|---:|---:|---:|
| A (≤20 %) | 0 | 0 | 0 |
| B (20–36 %) | 48.189 | 34.584 | **−13.605** |
| C (>36 %) | 109.811 | 123.416 | **+13.605** |
| D (útilokaður flokkur) | 314 | 314 | 0 |

Crosstab: B→C á 13.608, C→B á **3** (2062322, 2088137, 2094181 — allar
`APT_ATTIC`/`APT_BASEMENT` → `APT_FLOOR|Capital_sub`, pi80 41–55 % → 26,9 %).
Flokkur A er áfram tómur — leigan nær aldrei ≤20 %, sbr. cc30.

**Þetta er kostnaðurinn sem borðið verður að taka afstöðu til:** 13.605 eignir
fá VERRI bókstaf án þess að nokkur tala versni. Bókstafurinn mælir breidd
bilsins, og bilið breikkaði af því það var of þröngt áður.

---

## 3. VAKTAREIGNIRNAR SEX

| | fastnum | eign | cc fyrir → eftir | segment fyrir → eftir | n_conf | fb | **pi80** | flokkur | þrep | pred_mean |
|---|---|---|---|---|---|---|---|---|---|---|
| **A** | 2031935 | Hvassaleiti 69, 103 | `APT_ATTIC`→`ROW_HOUSE` | `APT_ATTIC\|RVK_core` → `ROW_HOUSE\|RVK_core` | 256→344 | 1→1 | 55,03→**61,69** (+6,66) | C→C | 4→4 | 313.665→341.617 (+8,91 %) |
| **B** | 2023957 | Skeljagrandi 9, 107 | `APT_FLOOR`→`SFH_DETACHED` | `APT_FLOOR\|RVK_core` → `SFH_DETACHED\|RVK_core\|Einbýli` | 6490→553 | 1→**0** | 39,11→**57,75** (+18,64) | C→C | 5→5 | 342.536→330.586 (−3,49 %) |
| **C** | 2270320 | Grænlandsleið 1, 113 | `SEMI_DETACHED`→`ROW_HOUSE` | `SEMI_DETACHED` → `ROW_HOUSE\|RVK_core` | 194→344 | 2→**1** | 41,11→**61,69** (+20,58) | C→C | 5→5 | 380.126→372.634 (−1,97 %) |
| **D** | 2000426 | Vesturgata 30, 101 | `APT_STANDARD` (óbr.) | `APT_STANDARD\|RVK_core` → **`global`** | 2722→22622 | 1→**3** | 41,36→39,69 (−1,67) | C→C | 5→5 | 232.020→237.610 (+2,41 %) |
| **E** | 2033138 | Sléttuvegur 11, 103 | `APT_FLOOR` (óbr.) | `APT_FLOOR\|RVK_core` (óbr.) | 6490→8432 | 1→1 | 39,11→38,54 (−0,57) | C→C | 2→2 | 292.884→307.648 (+5,04 %) |
| **F** | 2000189 | Mýrargata 24, 101 | `SFH_DETACHED` (óbr.) | `SFH_DETACHED\|RVK_core\|Einbýli` (óbr.) | 180→**553** | 0→0 | 58,74→57,75 (**−0,99**) | C→C | 2→2 | 319.524→308.595 (−3,42 %) |

`t5_astaeda`: D færist `of_fair_samningar` → `engin_svaedisgogn` (ein af 56).
A/E/F hafa enga (ekki í T5). B/C halda `of_fair_samningar`.
Rek A→B er **+0,00 %** á öllum sex (G4).

**F — VIÐMIÐIÐ — hreyfðist minnst og HALT-frávikið kom ekki fram.** Lykillinn
stendur kyrr (`SFH_DETACHED|RVK_core|Einbýli`), fb 0→0, þrep 2→2, flokkur C→C,
og bilið hreyfðist um **−0,99 pp** — minnsta hreyfing allra sex á pi80.
`n_conformal` 180→553 er samt raunveruleg breyting: sellan hennar ÞYKKNAÐI
þrefalt þótt nafnið standi. pred_mean −3,42 % er í línu við dreifinguna
(p05 −4,74 %, p95 +5,58 %) og telst ekki efnisleg hreyfing.

---

## 4. PARITY (staging)

| mæling | gildi | krafa | dómur |
|---|---|---|---|
| raðir í staging | 158.314 | 158.314 | PASS |
| raðir í lifandi | 158.314 | 158.314 | PASS |
| fastnúm-mengis-mismunur (FULL JOIN) | 0 | 0 | PASS |
| **segment vs `properties.canonical_code`** | **0** | 0 | **PASS** |
| munaðarleysingjar | 0 | 0 | PASS |
| bilaröð brotin (lo95≤lo80≤mean≤hi80≤hi95) | 0 | 0 | PASS |
| RLS virk | true | true | PASS |
| grants á anon/authenticated | 0 | 0 | PASS |
| NULL-mynstur, allir 12 dálkar | lifandi = staging (allt 0) | eins | PASS |
| **LIFANDI segment vs properties** | **57.417** | — | bókað |

Síðasta línan er innistæðan: **57.417 raðir bera ósamræmi í lifandi töflunni,
0 í staging.** Það er lokunin sem cc135 bókaði ÓLEYST.

Raðafjöldi krafðist engrar skýringar — skorunarþýðið
(`is_residential AND einflm BETWEEN 20 AND 1000`) er nákvæmlega sama
158.314-fastnúma mengi og lifandi taflan, 0 frávik í báðar áttir. Engin sella
sem hvarf felldi röð: allar 158.314 fengu segment, þar af 251 `global`.

Fæðingarreglan virt: `CREATE TABLE` + `ENABLE ROW LEVEL SECURITY` +
`REVOKE ALL … FROM anon, authenticated` í **einni og sömu DDL-stæðu**, innan
sömu txn og `COPY` og parity-hliðin (rollback ef eitthvað fellur).
Taflan ber 0 policies = innri/læst.

---

## 5. KOHORT

| kohort | allt þýðið | sýnilegt þýði |
|---|---:|---:|
| FÁ birt mat (T5 → <5) | **0** | **0** |
| MISSA birt mat (<5 → T5) | **0** | **0** |
| þrepsvíxl alls | 1 | 1 |
| flokkur breytist | 13.611 | 13.597 |
| pi80 þrengist | 105.460 | 105.298 |
| pi80 víkkar | 52.854 | 52.819 |
| pi80 óskert | 0 | 0 |

Fjöleiningar-vörnin (`v_fjoleining_fastnum`) telur **301 fastnúm** núna (193 þann
12.08 að morgni, 301 nú — sýnin er tímaháð, sbr. cc135/cc146); 197 þeirra eru í
leiguþýðinu, sýnilegt þýði 158.117.

**Enginn fær og enginn missir birt mat.** Endurskorunin er hrein bils-aðgerð á
spá-hliðinni. Þrepin sjálf endurbyggjast í ÞREPI 3 og þar getur talan hreyfst —
þessi lota keyrði þrepavélina EKKI, aðeins regluna hennar á óbreyttu `n_local`.

---

## 6. ÁKVÖRÐUNARLIÐIR FYRIR BORÐIÐ (HALT)

1. **`k_global` — mælt, ekki hreyft.** CFG ber 1,108152; endurmælt á S2-grunni
   **1,107372** (−0,070 %). Staðið artifact ber FROSNA gildið af því CFG-lyklarnir
   (`sveitarfélagsflokkun × herbergi`) eru ósnertir af S2. Frávikið er
   level-frávik og getur ekki hreyft pi80 (G3). Borðið á að segja hvort þrep 3
   flytji k eða haldi því.
2. **Flokkur B→C á 13.605 eignum** er sýnileg afturför í bókstaf án þess að nokkur
   tala versni. Þarf ákvörðun um birtingu áður en flippað er.
3. **`feature_attributions_rent` er TÓM (0 raðir)** og hvergi lesin af framenda
   (aðeins í migrations). Endurskorunin framleiddi ENGIN attributions — bókað
   sem meðvitað úrfelling, ekki gleymska.
4. **101 raðir bera `canonical_code` sem er ekki til í leigu-þjálfuninni** (jafn
   margar fyrir og eftir) og fá NaN-flokk í LightGBM. Fyrirliggjandi hegðun
   framleiðsluskorarans, óbreytt hér, ómælt áður.
5. **pi95 hreyfist í ÖFUGA átt við pi80 á miðgildinu** (`pred_lo95` +1,40 %,
   `pred_hi95` −1,25 % að miðgildi). Enginn flötur les 95 %-bilið í dag; bókað
   sem óskoðað horn.

**Flipp bíður go.** Þrep 3 (þrepavélin endurbyggð á nýju spánni) og þrep 4
(flipp + framendi) eru sér lotur.
