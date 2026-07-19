# LEIGUMAT — ÞREP + NaN-RETRAIN (cc30)

> **Lota:** cc30, hófst 2026-07-18T2318Z · þetta blað 2026-07-19T0003Z
> **Umboð:** `LEIGUMAT_FORKONNUN_AKVORDUNARBLAD_2026-07-17T1759Z.md` (cc13-dómur, GO á promotion með 4 skilyrðum) · `RENT_MODEL_CARD.md` · `RENT_IMPUTATION_DECISION.md`
> **Staða:** Fasi 1 (þrep + endurþjálfun). **Live `predictions_rent` = 0 alla lotuna.** Flip ekki framkvæmt.
> **Klukka:** tvíhliða staðfest — vélin á Greenwich Standard Time (UTC+0), staðartími == UTC.

---

## 0. Það sem lotan fann og hvers vegna hún beygði

Fyrirmælin gerðu ráð fyrir að staging væri flipp-hæft og að lotan þyrfti aðeins að bæta við þrepi og merkingu. **Það reyndist rangt.** Staging bar ólagaða `fj_herbergi`-fallback-meinsemd sem hefði sent ~13% of lág leigumöt á 2/3 universins undir merkingunni „kvarðað". Lotan tók því á sig endurþjálfun (armur OB) áður en nokkuð var byggt ofan á.

Þrjú frávik frá fyrirmælum, öll staðfest af eiganda áður en þau voru framkvæmd:

| # | Fyrirmæli | Raunveruleiki | Úrlausn |
|---|---|---|---|
| 1 | „RENT_MODEL_CARD skjalfestir NaN-bias (+0,123)" | Talan er **+0,1282** og er í `RENT_IMPUTATION_DECISION.md`, ekki í model-cardinu | Rétt tala notuð; sjá §1 |
| 2 | „T5-þrep … sömu evidence-tier hugsun og salan" | Sölu-þrep er afurð comps-vélarinnar; leigan hefur **enga comps-vél** | Þrepið skilgreint upp á nýtt á leigu-ásum; sjá §2 |
| 3 | Skilyrði 4 „anchor ≤ 2 mán" | Akkerið er 2026-05 (~2,5 mán) | Stenst á A2-endurskilgreiningu cc19 („nýjasta BIRTA útgáfa + hörð ≤4 mán vörn"), staðfest af eiganda; sjá §5 |

---

## 1. fj_herbergi — meinsemdin, sönnunin og lagfæringin

### 1.1 Meinsemdin

`rent_v1` var þjálfað þar sem `fj_herbergi` var til staðar í **99,25%** raða, en er borið fram á universe þar sem **66,6% (105.496 af 158.314) vantar það**. NaN-default-stefna trésins var því aldrei þjálfuð á þeirri dreifingu sem hún mætir í rekstri.

Mælt í `RENT_IMPUTATION_DECISION.md` (02.07.2026, stýrð tilraun — sömu OOF-raðir, aðeins feature-tiltækileika breytt):

| armur | MAPE% | bias(log) | cov80 | cov95 |
|---|---:|---:|---:|---:|
| A0 grunnlína (raun-fjherb) | 12,967 | −0,0013 | 81,5 | 95,4 |
| **A1 fullur fallback** | 17,716 | **+0,1282** | **57,7** | 90,3 |
| (a) OA impute | 13,532 | −0,0012 | 80,3 | 95,1 |
| **(b) OB NaN-retrain** | **13,434** | **+0,0043** | **80,5** | **95,4** |
| (c) OC tvö-módel | 13,459 | +0,0040 | 80,5 | 95,3 |

### 1.2 Sjálfstæð sönnun á staging (cc30, ný)

Skjalið mældi meinsemdina á OOF-gögnum. cc30 mældi hana **á staging-tölunum sjálfum** — sama segment, þröngt stærðarband 60–100 m², meðal-fermetraverð eftir því hvort `fjherb` er til staðar:

| segment | m/herb | án herb | mismunur |
|---|---:|---:|---:|
| ROW_HOUSE·Country | 2.987 | 2.399 | **−19,7%** |
| APT_ATTIC·RVK_core | 4.183 | 3.430 | **−18,0%** |
| APT_BASEMENT·RVK_core | 3.952 | 3.327 | **−15,8%** |
| APT_FLOOR·RVK_core | 3.967 | 3.367 | **−15,1%** |
| APT_STANDARD·RVK_core | 3.961 | 3.416 | **−13,7%** |
| APT_FLOOR·Country | 2.942 | 2.560 | **−13,0%** |
| APT_STANDARD·Country | 3.134 | 2.735 | **−12,8%** |
| APT_FLOOR·Capital_sub | 3.709 | 3.254 | **−12,3%** |
| APT_STANDARD·Capital_sub | 3.844 | 3.370 | **−12,3%** |

**Níu segment af níu, sama átt.** e^0,1282 − 1 = +13,7% — stærðin stemmir við mælda biasið. Þetta er ekki raunmunur á eignunum (stýrða tilraunin í §1.1 notaði sömu raðir), heldur módel-meinsemd.

**Afleiðing ef flippað hefði verið óbreytt:** 105.496 leigumöt ~13% of lág, og 80%-bilið þeirra þekur í raun ~58% en ekki 80,55%. Viðmiðið „cov80 80,55%" er held-set-tala þar sem `fj_herbergi` VAR til staðar — hún lýsir ekki þeim röðum sem færu live.

### 1.3 Af hverju þreplækkun ein dugði ekki

Eigandi valdi upphaflega þreplækkun fram yfir bilvíkkun, með réttum rökstuðningi: *breiðara ókvarðað bil = ómæld tala = bannað.* En þrep leiðréttir hvorki 13% bias né endurheimtir þekju — það merkir aðeins. Skilyrðið „bilið helst KVARÐAÐ" var einmitt **ekki uppfyllt** á þessum 2/3. Lagfæringin varð því að vera á módelinu, ekki merkingunni. Þreplækkunin stendur áfram sem sjálfstæð regla (§2), nú ofan á rétt kvarðað bil.

### 1.4 Framkvæmd (OB)

`train_rent_v1.py`: nýtt `make_X_train()` sem setur `fj_herbergi = NaN` á 66,6% þjálfunarraða (deterministic, `default_rng(4242)`). **Aðeins fyrir þjálfun** — við skorun er raun-missingness þegar til staðar og tilbúin ofan á væri tvítalning. Kallstaðir uppfærðir í `rent_recalibration.py`, `rent_conformal.py`, `score_rent_universe.py`; spá-frame alls staðar áfram raun-frame.

Mælt eftir endurþjálfun:

- **OOF MAPE 13,0% / medAPE 7,8%** (raun-frame) — engin hnignun frá A0 12,97%.
- **Akkeri:** HFAC óbreytt (kemur úr birtri leiguverðsjá HMS, ekki úr módelinu — eins og vera ber). `k_global` 1,103054 → **1,108152** (+0,46%).
- **Conformal endurkvarðað:** cov80 **80,8%** · cov95 **95,0%** (held n=21.787), á móti 80,55/94,99 áður. Einbýli-ásinn heldur (73,0 → 82,5 eftir viðbót).

Útgáfustimplar: `model_version = rent_v1_nan`, `calibration_version = rent_anchor_v2_herbergi_fm+conformal_v2_tegund_nan`.

Afturköllun: `rent_calibration_config_pre_nanretrain_20260718T2318Z.json` + `rent_conformal_corrections_pre_nanretrain_20260718T2318Z.json` (báðar staðfestar á diski).

---

## 2. Leigu-þrepið — ný skilgreining, ekki portun

### 2.1 Af hverju ekki portun

Sölu-þrep T1–T5 er **afurð comps-vélarinnar** (`build_comps_v2.py` → `valuation_tiers`, 167.503 raðir): þrepið mælir hve djúpt comps-kaskadinn þurfti að fara áður en nógu margar sambærilegar sölur fundust. **Leigan hefur enga comps-vél og enga þrepatöflu** — `predictions_rent_staging` bar hvorki þrep né flokk. Þrepið varð því að skilgreinast upp á nýtt.

### 2.2 Mæling sem breytti hönnuninni

Fyrsta tilgáta var að nota conformal-fallback-stigið sem þéttleika-ás. **Það reyndist rangt, tvisvar:**

1. **Kaskadinn er ekki einhalla með áreiðanleika.** Stig 0 (dýpsta sellan, `cc|region|tegund`) hefur **breiðustu bilin** (p50 65,4%) af því að það stig er frátekið fyrir Einbýli — versta segmentið. „Dýpra = betra" hefði raðað Einbýli í T1.
2. **Kaskadinn FELUR þynnkuna.** MIN_N=30 þvingar fallback upp á við, svo engin röð situr nokkurn tíma á þunnri conformal-sellu. Global-fallback fær meira að segja **þröngt** bil (38,8%) úr samlagðri kvantílu sem hún hefur ekki unnið fyrir.

Raunveruleg þynnka sést aðeins á fínni kvarða. Mælt á leiguskrá 2021–2023 (n=21.099 samningar), `postnr × canonical_code`: **348 af 441 sellum (78,9%) hafa <30 samninga, miðgildi 6.** Það er ásinn sem ber merkingu — og hann speglar 211/286-töluna úr forkönnunarblaðinu á annarri kornastærð.

### 2.3 Skilgreiningin

**Aðal-ás: staðbundinn þéttleiki** `n_local` = samningar 2021–2023 í `postnr × canonical_code`.

| n_local | grunnþrep |
|---|---|
| ≥ 100 | T1 |
| 30–99 | T2 |
| 10–29 | T3 |
| 5–9 | T4 |

**Þreplækkanir** (+1 hvor, gólf í T4 — hvorug ein og sér gerir mat óbirtanlegt):
- `fj_herbergi` vantar
- conformal-fallback á stig 2 (canonical-only, engin svæðis-vitneskja)

**T5 — engin tala birt** ef eitthvað af eftirfarandi:
- `canonical_code ∈ {APT_UNAPPROVED, APT_ROOM, EXCLUDE}` — leiguverðið ræðst af ósýnilegum leigukjörum (húsgögn, hiti innifalinn, óformlegt samkomulag), OOF MAPE 18,8–21,4%
- conformal-fallback á stig 3 (global — engin segment-vitneskja)
- `n_local < 5` — engin staðbundin leigu-vitneskja

**Flokkur A–D** = conformal-breidd, **sömu þröskuldar og salan** (rel80 < 0,20 = A · < 0,36 = B · annars C; D = útilokaður eignaflokkur). Bókstafurinn verður að þýða það sama í leigu og sölu.

### 2.4 Sannreynd heilindi ásanna

- **Join hreinn:** 0 raðir með `postnr` null, 0 með `canonical_code` null.
- **5.846 raðir með `n_local = 0` eru raunverulegar, ekki join-gallar:** 4.473 eru í postnúmerum sem KOMA FYRIR í leiguskránni en með engum skráðum samningi fyrir þá eignagerð; 1.373 eru í postnúmerum án nokkurs skráðs leigusamnings. T5 á þeim er rétt.
- **Krossgát:** `fj_herbergi`-vöntun mældist 105.496 = **66,6%**, nákvæmlega tala model-cardsins → joinið stemmir.

*(Þrepatafla og flokkadreifing á endanlegum OB-tölum: §3, fyllt eftir endurskorun.)*

---

## 3. Mælingar á endurskoruðu universi

Endurskorun keyrð 19.07 00:01–00:13Z. `predictions_rent_staging` + `feature_attributions_rent_staging` endurhlaðin: **158.314 / 1.583.140** raðir (væntar tölur, nákvæm samsvörun). **Live `predictions_rent` = 0 allan tímann**, staðfest í hverju skrefi.

### 3.1 Áhrif OB á universið

| hópur | n | meðalbreyting | miðgildisbreyting |
|---|---:|---:|---:|
| `fj_herbergi` til staðar | 52.818 | +0,03% | **−0,01%** |
| `fj_herbergi` vantar | 105.496 | +21,94% | **+20,14%** |

Rétt hegðun: raðirnar sem virkuðu hreyfðust ekki (endurþjálfunin raskaði engu að óþörfu), og fallback-raðirnar leiðréttust upp á við. +20% samsvarar leiðréttingu á ~−16,7% vanmati, innan mælda bilsins −12,3% til −19,7% úr §1.2.

### 3.2 Gapið lokað (sama mæling og §1.2, á OB-tölum)

| segment | fyrir | eftir |
|---|---:|---:|
| APT_FLOOR·Capital_sub | −12,3% | **0,0%** |
| APT_STANDARD·RVK_core | −13,7% | **−2,0%** |
| APT_STANDARD·Country | −12,8% | **−2,0%** |
| APT_FLOOR·Country | −13,0% | **−2,0%** |
| APT_FLOOR·RVK_core | −15,1% | **−3,0%** |
| APT_BASEMENT·RVK_core | −15,8% | **−3,0%** |
| APT_ATTIC·RVK_core | −18,0% | **−3,0%** |
| ROW_HOUSE·Country | −19,7% | **−9,0%** |

Eftirstæð −2 til −3% er heiðarleg: eignir án skráðs herbergjafjölda eru að einhverju marki raunverulega frábrugðnar, og módelið má ekki lengur ofreiða sig á feature-ið. **ROW_HOUSE·Country (−9%) fer á vaktlista** sem versta eftirstæða sneiðin.

### 3.3 Þrepadreifing (endanleg, á OB-tölum)

| Þrep | n | % | þar af herb vantar | n_local miðgildi | PI80 miðgildi |
|---|---:|---:|---:|---:|---:|
| T1 | 35.110 | 22,18 | 0 | 309 | 39,1% |
| T2 | 74.193 | 46,86 | 67.347 | 331 | 39,1% |
| T3 | 18.318 | 11,57 | 13.748 | 43 | 46,8% |
| T4 | 15.288 | 9,66 | 12.975 | 11 | 46,8% |
| **T5 — engin tala** | **15.405** | **9,73** | 11.426 | 1 | 47,8% |

**T5-ástæður** (deterministic, forgangsraðað): `of_fair_samningar` 14.896 · `eignaflokkur` 314 · `engin_svaedisgogn` 195. Sannreynt: **hver einasta T5-röð ber ástæðu, engin önnur röð ber ástæðu.**

**Lestur T2:** 67.347 af 74.193 T2-röðum eru T1-raðir lækkaðar vegna `fj_herbergi`-vöntunar (n_local miðgildi T2 er 331 — HÆRRA en T1). T2 þýðir í reynd „þéttur gagnagrunnur en herbergjafjöldi óskráður". Það er rétt framsetning: gögnin eru til, en ein lykilbreyta vantar.

**Samanburður við söluna:** leigu-T5 er 9,73% á móti sölu-T5 2,03% (3.407/167.503). Leigan neitar **4,8× oftar**. Það er satt og á að vera þannig — staðbundin leigugögn eru miklu þynnri en sölugögn.

### 3.4 Flokkadreifing

| Flokkur | n | % |
|---|---:|---:|
| A | **0** | 0,00 |
| B | 48.189 | 30,44 |
| C | 109.811 | 69,36 |
| D | 314 | 0,20 |

**Flokkur A er óaðgengilegur leigunni.** Þrengsta conformal-sellan (`APT_FLOOR|Capital_sub`, q80_log 0,149) gefur ~30% breidd; 20%-þröskuldur sölunnar næst aldrei. Tveir kostir voru mögulegir:

1. Endurkvarða bókstafina að leigu-dreifingunni → „B" myndi þýða sitt hvað eftir vörum. **Hafnað** — bókstafur sem þýðir ekki það sama lýgur.
2. Halda þröskuldunum og láta leiguna sýna B/C → **valið**. Niðurstaðan segir satt: leigumat er einfaldlega óvissara en sölumat.

Afleiðing: flokkurinn aðgreinir lítið INNAN leigunnar (30/69 skipting). Það er í lagi — **þrepið er aðgreinandinn**, flokkurinn er þvervöru-yfirlýsing um breidd.

### 3.5 Öryggisstaða nýju töflunnar

`valuation_tiers_rent_staging`: RLS **á**, **0 stefnur**, `anon`/`authenticated` SELECT = **false** (default-deny). Rétt fyrir staging-töflu skv. CLAUDE.md-reglunni. **Við flip þarf hún `public_read` SELECT-stefnu** — bókað í flip-planinu.

---

## 4. Vaktarrásirnar þrjár — skriflegar skilgreiningar (skilyrði 3)

Skilyrði 3 í cc13-dómnum krefst þess að vaktarrásirnar séu **skilgreindar FYRIR flip**. Þær eru skilgreindar hér. **Bygging pípunnar er lota #4** og er ekki launch-blocker — skilyrðið snýr að skilgreiningunni, ekki útfærslunni.

Sameiginlegt: leigan hefur **enga per-eign truth eftir 2024-03** (þinglýsing leigusamninga lagðist af). Allar þrjár rásirnar eru því **aggregat**, og það verður að segjast hreint út: leigu-vaktin er strúktúrelt veikari en sölu-vaktin.

### Rás 1 — Leiguverðsjá (level-drift)

| | |
|---|---|
| **Heimild** | HMS leiguverðsjá, `Gogn_til_nidurhals_leiguverdsja.csv` (prismic-CDN) |
| **Taktur** | Mánaðarlega; hash-vöktun á skránni (cc19 bókaði að niðurhalshlekkur hvarf af hms.is en skráin lifir á óbreytanlegri slóð) |
| **Mæling** | Miðgildi módel-leigumats vs LVS-sella, per svæði × herbergjafjölda |
| **Þröskuldur** | Frávik > ±5% á sellu með n ≥ 100 samningum, tvo mánuði í röð |
| **Aðgerð** | Endurskoða akkeri (`k_global` + HFAC); við > ±10% → HALT á birtingu og endurkvörðun |

### Rás 2 — Leiguvísitala (akkeris-taktur)

| | |
|---|---|
| **Heimild** | `leiguvisitala.csv`, sama OCI-fata og kaupskráin — **lifandi** (Last-Modified 15.07.2026) |
| **Taktur** | Mánaðarlega |
| **Mæling** | Uppsöfnuð vísitöluhreyfing frá akkeris-glugga (nú 2026-05) |
| **Þröskuldur** | Hreyfing > 3% frá akkeri, EÐA akkeri eldra en nýjasta birta LVS-útgáfa, EÐA hörð 4-mánaða vörn (skilyrði 4, §5) |
| **Aðgerð** | Anchor-refresh + endurskorun |

### Rás 3 — Eigið ask vs módel (flæðis-vísir)

| | |
|---|---|
| **Heimild** | `scraper.listings`, `tenure='rent'` (mbl + myigloo, ~1.401 nothæf) |
| **Taktur** | Vikulega |
| **Mæling** | Miðgildi auglýsts leiguverðs ÷ miðgildi módelmats, sama sneið |
| **Þröskuldur** | Hlutfall utan bandsins **1,15–1,20** (mælt í forkönnun: RVK 1/2/3 herb 1,16/1,17/1,19; Capital_sub 2/3 herb 1,20/1,15) |
| **Aðgerð** | Rannsaka hvort ask-premían hefur hreyfst eða módelið rekið |
| **⚠ Hörð regla** | Ask-leiga og samningsmat mega **ALDREI blandast** í birtingu. Ask er nýtt flæði; matið er samningsmat. Rásin er greiningartæki, ekki kvörðunar-heimild |

---

## 5. Skilyrði cc13-dómsins — staða

| # | Skilyrði | Staða |
|---|---|---|
| 1 | T5-lag inn | ✅ Skilgreint og smíðað (§2) |
| 2 | Loud labeling „MÓDELSPÁ — ekki mæld leiga" | ⏳ Fasi 2 |
| 3 | Vaktarrásirnar þrjár skilgreindar FYRIR flip | ✅ §4 (skriflegar; pípa = lota #4) |
| 4 | Anchor aldrei eldri en 2 mánuðir | ✅ á A2-endurskilgreiningu cc19 |

**Skilyrði 4 — nánar.** Akkerið er 2026-05 (~2,5 mán 19.07). Á orðalagi cc13-blaðsins („≤ 2 mánuðir") fellur það. cc19 (`LEIGU_ANCHOR_REFRESH_CC19_2026-07-18T0909Z.md`) endurskilgreindi skilyrðið í **„aldrei eldra en nýjasta BIRTA útgáfa + hörð ≤4 mán vörn"** eftir að hafa mælt að nýjasta leiguverðsjá (útg. 10.06, gögn 2026-05) væri **bæti-identísk** þeirri sem akkerið hvílir á — það er engin ferskari útgáfa til að sækja, svo „≤2 mán" er óuppfyllanlegt skilyrði í reynd, ekki merki um rek. Eigandi staðfesti þessa skilgreiningu í cc30. GO-dómurinn heldur.

---

*Skrifað af cc30 (Claude Opus 4.8). Live `predictions_rent` = 0 við ritun þessa blaðs.*
