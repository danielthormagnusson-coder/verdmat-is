# cc145 — COMPS-ENDURBYGGING Á cc143-VÍSITÖLUNNI

**Staða: BYGGT + STAGED + MÆLT — HALT FYRIR FLIPP.**
Dagsetning 2026-08-12. Artifacts `D:\cc145\`, mælitöflur `D:\_audit\cc145_comps\`.
Frysting `*_pre_cc145` ×4 stendur, staging ×4 hlaðið, parity PASS.
Ekkert flippað. `predictions` ósnert, `prior_*` ósnert, leiga ósnert.

---

## 0. Hliðið

cc145 mátti ekki fara af stað fyrr en cc143-flippið væri committað og skilað.
Við upphaf lotu var flippið **lifandi í DB en óbókað í git** (keyrt 17:33, git bar
ekkert cc143). Lotan stöðvaðist á því hliði. cc143 bókaði svo og pushaði:
`app adfcbb9` + `precompute 2417034` — bæði sha staðfest með `git fetch`/`git log`
áður en haldið var áfram. Einn DB-skrifari alla leið; `pg_stat_activity` bar engar
aðrar virkar skriftir.

---

## 1. Ómælda joinið (`build_comps_v2.py:152`) — MÆLT, ÓEFNISLEGT

cc143 bókaði að comp-poolinn sé merktur úr `training_data_v2.pkl` en subjects úr
lifandi universi, og að umfangið væri ómælt. Mælt hér, NOW=2026-08-12, sömu hörðu
síur og buildið notar:

| Ás | Hlið | Nefnari | Teljari | % |
|---|---|---|---|---|
| `canonical_code` | subjects | 167.503 | **0** | **0,0000 %** |
| `canonical_code` | comp-pool | 25.953 raðir | **0** | **0,0000 %** |
| `region_tier` | subjects | 167.503 | 185 | 0,1104 % |
| `region_tier` | comp-pool | 25.953 raðir | 44 | 0,1695 % |

89.237 subjects (53,27 %) bera merkingu í `training_data_v2`; **engin þeirra ólíka**.
78.266 (46,73 %) bera enga — þær seljast ekki í glugganum og berast aldrei í poolinn.
4 comp-raðir (0,02 %) eiga fastnum utan universis.

Ástæðan er mælanleg: `training_data_v2.pkl` endurbyggt 04.08 á reglu R og
`canon_universe.parquet` sótt 12.08 13:37 úr lifandi DB — báðar hliðar á reglu R.

**Báðir ásar undir 1 %-þröskuldinum ⇒ engin HALT-spurning af þessum lið.** Byggt
án breytingar á joininu.

### Afleiddur fundur — `geography_features.pkl` er staðnaður (BACKLOG, ekki lagað hér)

Region-ásinn er ekki sami join og cc143 bókaði. Subjects taka `region_tier` úr
lifandi universi, poolinn úr `geography_features.pkl` **frá 28.05**. Þaðan koma
185 subjects / 44 pool-raðir. Sex sellur hreyfast, stærst `APT_FLOOR×RVK_core`
+34 / `APT_FLOOR×Capital_sub` −34 (0,4 % / 0,5 % af sellunni); sellufjöldi
óbreyttur 28↔28. Skiptingin: 137 RVK_core→Capital_sub, 41 RVK_core→Country,
7 hina leiðina.

**Bókast sem sjálfstæður 7.8-stöðnunarliður á backlog.** ATH: cc131 bókaði
„region_tier-mismunur við valuation_tiers = 0" — það var mælt á ÖÐRUM fleti
(vt gegn geo, báðar hliðar úr sama staðnaða lagi). Mælt gegn LIFANDI universi
er mismunurinn 185. Sama gildra og
[[feedback_hlid_sem_les_badar_hlidar_ur_somu_heimild_er_daudt]].

---

## 2. Vírun og parity-hóla á sjálfri skriftinni

`build_comps_v2.py:75` bar `AT_Q = pd.Period("2026Q2")` harðkóðað og resolverinn
las sjálfgefna `D:\repeat_sale_index_v2.pkl` (03.07). Það er sama tvöfalda
frystingin og cc143 fann á par-laginu: **endapunktur OG lind**. Bætt við
`--index`, `--family-map`, `--at-q`; án `--at-q` er AT_Q **líðandi fjórðungur af
`--now`** (nákvæmlega eins og `cc143_prior.py`). Allt stimplað í
`_comps_v2_build_stamp.json` (7.8).

**Parity-hólan:** sama skrift með GÖMLU inntökunum (`--now 2026-08-11 --at-q
2026Q2`, sjálfgefið artifact) gegn lifandi artifactinu:

| Mæling | Niðurstaða |
|---|---|
| `price_adj_kr`, 1.094.658 raðir m/sama comp | **0 ólíkar**, max\|Δ\| = 0 |
| `idx_anchor_q` / `idx_level_used`, 1.098.038 raðir | **0 ólíkar** |
| `canonical_code` / `region_tier`, subjects | **0 ólíkar** |
| `km` / `similarity` | ≤0,69 m / ≤7·10⁻⁶ (fleytitölusuð) |
| `n_comps` breytt á 5.517 eignum | **allar í 3 sellum breyttu salnanna, 0 utan** |

Mismunurinn er **7 kaupskrár-færslur** sem bárust milli builda (4 nýjar 10.08,
3 horfnar); `kaupskra.csv` sha `4b5eb1af…`→`1b74c1f1…`. Eina Δ=+18 útlagan er
fastnum **2145072** — sama eignin og missti prior-akkerið í cc143 vegna tímaháðu
`single_deed`-síunnar. Sama regla, tvö lög.
**Patchið er sannanlega óvirkt.**

---

## 3. Buildið

```
build_comps_v2.py --support support --pred support/predictions_current.csv \
  --now 2026-08-12 --index D:\cc143\rs_live_kaupskra_v2.pkl \
  --family-map D:\cc143\rs_live_kaupskra_family_map.csv
```

AT_Q=**2026Q3**, resolver-stimpill `…|2026-08-12T13:34:06Z|…` (cc143-artifactið),
116 s. 167.503 subjects, **1.098.103** comp-raðir, pool 25.953/23.972, t5 35.379,
drift 23 sellur. Þrep T1 70.660 (42,18 %) / T2 82.725 / T3 2.949 / T4 8.198 /
T5 2.971.

Vísitölulagið færðist: pool-sellur `{cell 14, family 13, national 1}` →
`{family 15, cell 12, national 1}` — tvær sellur falla úr cell í family af því
2026Q3 er of þunn til að bera akkeri. Akkerisreglan virkar.

---

## 4. BLOKKER SEM FANNST: loaderinn hefði brotið prior-bannið

`load_comps_v2.py` flippaði `valuation_tiers` með **TRUNCATE + INSERT** og
dálkalistinn ber tíu `prior_*`-dálka. Óbreyttur hefði hann:

1. **yfirskrifað cc143-flippuðu `prior_*`-dálkana** með prior-útreikningi
   `build_comps_v2` (önnur skrift, aðrar reglur en `cc143_prior.py`), og
2. **þaggað nýju sjö cc143-flöggin í NULL** — þau eru ekki í dálkalistanum, svo
   INSERT skilur þau eftir tóm, þögult.

Hvort tveggja brýtur bannið „prior_*-dálkarnir (nýflippaðir) ósnertir".

**Lagfæring (þrjú lög):**
- `valuation_tiers` fær `flip_mode="update"`: UPDATE á comp-dálkunum einum,
  `PRIOR_FROZEN` (10+7 dálkar) aldrei í SET-lista. Hinar þrjár töflurnar halda
  TRUNCATE+INSERT.
- **Hlið á SKRIFLEIÐINNI**: prior-checksum borin saman við `*_pre_cc145` í SÖMU
  txn — brot rúllar flippinu til baka í stað þess að mælast eftir á.
  Mengja-jafnræði (lifandi ↔ staging, hvorug hlið með aukaröð) er hart skilyrði
  á undan UPDATE-inu.
- Postverify undanskilur `prior_*` fyrir `valuation_tiers` — annars væri það
  falskt fall (lifandi ber cc143-gildin, CSV-ið ber sín eigin).

Auk þess: `SCRATCH` benti á scratchpad cc131-lotunnar, **dauða slóð milli lota**
(sama gildra og cc129 lenti í). Fært á `D:\_audit\cc145_comps`.

---

## 5. Frysting + staging + parity

**Frysting** (`cc145_freeze.py`, neitar að yfirskrifa):

| Tafla | Raðir | Checksum lifandi = snapshot |
|---|---|---|
| `valuation_tiers_pre_cc145` | 167.503 | Σwmedian 12.682.744.128.387 · Σn_comps 57.219.444 · T1 70.641 ✓ |
| `comps_index_v2_pre_cc145` | 1.098.087 | Σprice_adj 91.569.359.575.043 ✓ |
| `comps_t5_basis_pre_cc145` | 35.435 | Σprice 2.219.975.100.000 ✓ |
| `comps_drift_diagnostics_pre_cc145` | 23 | Σn_d 153.366 ✓ |

**prior_*-checksum við frystingu: `4b6edaf9f772276ba6d4da9d830a193d`** — talan sem
flippið verður að skila óbreyttri. Rollback: `app/scripts/comps_v2_rollback_cc145.sql`.

**Staging → parity: PASS 4/4** — rowcount jafn á öllum fjórum, 500-sýnin
(lægstu 250 + hæstu 250 eftir PK) **0 frumur ólíkar**, munaðarlausar 0,
universe 167.503 distinct, sentinel-varpanir allar á væntu gildi
(wmedian_null 14.118, similarity_null 7.561, prior_null 90.019),
Σprice_adj staging 91.371.393.818.131.

---

## 6. 0,3 %-JAFNAN — LOKAST

Bilið var að prior-hliðin læsi cc143-artifactið á 2026Q3 en comp-hliðin gamla
artifactið á 2026Q2. Mælt beint sem **hlutfall eigna þar sem hliðarnar bera sama
verðlags-akkeri**:

| | nefnari | prior_anchor_q = idx_anchor_q |
|---|---|---|
| FYRIR | 77.484 | 2.367 — **3,05 %** |
| EFTIR | 77.484 | 77.484 — **100,00 %** |

Báðar hliðar lesa nú `D:\cc143\rs_live_kaupskra_v2.pkl` @ AT_Q=2026Q3.
**Jafnan berum orðum: bilið milli prior- og comp-hliðar er 0 — ekki lítið, heldur
núll, af því hliðarnar deila artifacti og fjórðungi.**

Stærð bilsins sem lokaðist, á landsvísitölunni:
gamalt artifact 2026Q2 = 382,2479 → cc143 2026Q3 = 378,1401 = **−1,074 %**, þar af
−0,807 % endurmat á 2026Q2 (frosni endapunkturinn var þunnkusaður) og
**−0,270 % þrepið 2026Q2→2026Q3** — það er „0,3 %-bilið" eins og það mælist.

Akkeri comp-hliðarinnar: 2026Q2 98.610 / 2026Q1 62.575 / 2025Q4 6.318 →
**2026Q3 151.641** / 2026Q2 10.604 / 2026Q1 5.258. Engin eign situr eftir á 2025Q4.

---

## 7. SKAMMTASVÖRUN — VÆNTINGIN STÓÐST EKKI

Sama hólfun og cc131 (gamla taflan gegn reglu R), sama SQL fyrir og eftir,
mælistærð median(comp_wmedian / lifandi spá):

| hólf | n | fyrir | eftir |
|---|---|---|---|
| óbreytt | 109.794 | 0,9921 | 0,9878 |
| breytt innan fjölskyldu | 30.658 | 0,9848 | 0,9884 |
| víxlað fjölbýli→sérbýli | 27.036 | 0,9863 | 0,9769 |
| önnur víxl | 15 | 1,0251 | 1,0229 |

„Fyrir"-dálkurinn endurgerir cc131-mælinguna upp á fjóra aukastafi
(0,9921 / 0,9848 / 0,9863) — sama-við-sama er tryggt.

**Mengunarbilið fór úr 0,58 p.p. í 1,09 p.p. Væntingin var ≤0,6 p.p. eða batni.
Hún stóðst EKKI.**

**Sundurgreining (bil innan sellu, hólfin borin saman í SÖMU sellu):**

| sella | fyrir | eftir | |
|---|---|---|---|
| ROW_HOUSE×Capital_sub | 0,30 | 0,06 | þrengist |
| ROW_HOUSE×Country | 1,30 | 0,74 | þrengist |
| SFH_DETACHED×Capital_sub | 0,34 | 0,21 | þrengist |
| SFH_DETACHED×RVK_core | 0,94 | 0,42 | þrengist |
| ROW_HOUSE×RVK_core | 1,17 | **2,52** | breikkar |
| SFH_DETACHED×Country | 2,09 | **2,34** | breikkar |

Fjórar af sex sellum þrengjast innan sellu; heildarbreikkunin er að stærstum hluta
**sellu-samsetning**, ekki mengun — hólfin eru orðin staðgengill fyrir sellu-aðild
því cc145 hreyfir enga flokkun (canonical 0 ólíkar). En tvær sellur breikka
raunverulega, og önnur þeirra (`SFH_DETACHED×Country`) er einmitt sella sem
akkerast á þunnu 2026Q3. **Ég afskrifa ekki fallna væntingu — hún fellur, og
sundurgreiningin fylgir með.**

**Heildarkvörðun versnar lítillega:** median(comp_wmedian/spá) 0,9895 → 0,9867
(frávik frá 1: −1,05 % → −1,33 %, n=153.361).

---

## 8. NÝ ÁHÆTTA SEM MÆLDIST: hálfkláraður fjórðungur sem akkeri

2026Q3 er **hálfkláraður** — 1.7.–11.8. = 6 vikur af 13. Pör í Q3 eru ~45 % af Q2
alls staðar. `MIN_ANCHOR_PAIRS=10` hleypir seríu með 10 pörum í gegn sem akkeri.

**90,5 % universis (151.641 eign) akkerast nú á 2026Q3.** Þar af liggja
**33.634 eignir (20,1 % universis) á lagi með færri en 30 pör í fjórðungnum**:

| sella | lag | eignir | pör í 2026Q3 |
|---|---|---|---|
| SFH_DETACHED×Capital_sub | cell | 11.391 | 16 |
| SUMMERHOUSE×Country | cell | 10.577 | 13 |
| ROW_HOUSE×Country | cell | 6.218 | 18 |
| APT_BASEMENT×RVK_core | cell | 2.851 | 17 |
| SEMI_DETACHED×Capital_sub | family | 2.077 | 27 |
| SEMI_DETACHED×RVK_core | family | 520 | 13 |

Til samanburðar bera stærstu sellurnar nóg: APT_FLOOR×RVK_core 159 pör (43.987
eignir), ×Capital_sub 128 (33.784), APT_FLOOR×Country 65, SFH_DETACHED×Country 36.

Sellu-þrepin 2026Q2→2026Q3 eru samsvarandi óstöðug þar sem þunnt er:
APT_BASEMENT×Country +91,8 % (1 par), ×Capital_sub −28,7 % (1 par),
SEMI_DETACHED×Country +10,9 % (2 pör) — **akkerisreglan sigtar sex af átta villtum
sellum burt**, en tvær sleppa: `SFH_DETACHED×Country` (−5,54 %, n=36, 19.397 eignir)
og `ROW_HOUSE×Country` (−7,46 %, n=18, 6.218 eignir).

Þetta er sama ættin og [[feedback_flagg_a_throskuldi_sem_hlid_tryggir]]: þröskuldur
sem hlið ofar tryggir. Hér er þröskuldurinn 10 og hann bítur ekki á hálfum fjórðungi.

---

## 9. Prófdæmin

### Skipasund 35 (2018566) — GAPIÐ BREIKKAR

| | fyrir | eftir |
|---|---|---|
| þrep / n_comps | T1 / 80 | T1 / 81 |
| comp_wmedian | 124.115.601 | **121.718.273** |
| d_log | −0,0449 | −0,0644 |
| akkeri / lag | 2026Q1 / family | 2026Q1 / **cell** |
| gap comps−spá | −4,39 % | **−6,24 %** |
| gap prior−comps | +18,75 % | +21,09 % |

Akkerið situr áfram í 2026Q1 — sellan `SFH_DETACHED×RVK_core` ber 7 pör í Q3 og
9 í Q2, hvort tveggja undir 10. Það sem vinnst er að lagið fer úr fjölskyldu í
sellu (serían ber 670 pör). Comp-listinn er allur úr sérbýlisætt ≤1,92 km.
prior_adj 147,4 M gegn comp-miðgildi 121,7 M og spá 129,8 M — **þessi eign er
áfram ósamræmd á öllum þremur mælingum og versnar**.

### Álftamýri 39 (2013952) — VÆNTINGIN GEKK EFTIR

Fastnúmerið er **2013952** (forskriftin bar 2103763 — leiðrétt; 2103763 er ekki til
í universinu, geo né training_data).

| | fyrir | eftir |
|---|---|---|
| þrep / n_comps | T1 / 94 | T1 / 94 |
| comp_wmedian | 145.270.512 | **135.600.929** |
| d_log | +0,0511 | −0,0178 |
| akkeri / lag | **2025Q4** / cell | **2026Q2** / cell |
| gap comps−spá | +5,24 % | **−1,76 %** |
| gap prior−comps | −4,14 % | +2,70 % |

Bókaða væntingin — „comp-akkerið færist af 2025Q4 á ferskan fjórðung" — **gekk
eftir**. Gapið gegn spá minnkar úr 5,24 % í 1,76 % að tölugildi og gegn prior úr
4,14 % í 2,70 %. Comp-listinn er 8 raðir, allar `2026Q2`-akkeraðar, 0,30–1,96 km.

---

## 10. Staðan og hvað bíður

**Í DB núna:** `*_pre_cc145` ×4 (frysting), `*_staging` ×4 (nýja buildið),
lifandi töflur ÓBREYTTAR. Ekkert flippað.

**Til flipps vantar go.** Flipp-röðin: `load_comps_v2.py --phase flip` (atómísk
txn, UPDATE á comp-dálkum `valuation_tiers` + TRUNCATE/INSERT ×3, orphan-recheck,
**prior-checksum-hlið**, `pipeline_runs`) → `--phase parity` (final) → `--phase
cleanup` → eftirmæling á lifandi.

**Bókað til næstu lotu:**
1. `geography_features.pkl` (28.05) — staðnaði region-ásinn, 185 subjects /
   44 pool-raðir. 7.8-ættin.
2. Þröskuldurinn `MIN_ANCHOR_PAIRS=10` gegn hálfkláruðum fjórðungi — 20,1 %
   universis á lagi með <30 pör.
3. `build_comps_v2` reiknar sinn eigin `prior_*` sem er nú aldrei skrifaður.
   Tvær óháðar prior-útfærslur á sama artifacti — samanburður þeirra er ómældur.
