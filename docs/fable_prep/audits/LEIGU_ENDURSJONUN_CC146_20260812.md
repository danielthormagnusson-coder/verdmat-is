# LEIGU-ENDURSJÓNUN — ÞREP 1 AF 4 (FORPRÓF)

**cc146 · 2026-08-12 · READ-ONLY · HALT eftir skil**

Mælikóði: `precompute/cc146_forprof.py` (explicit paths, ein keyrsla).
Mælitöflur + keyrslulog: `D:\_audit\cc146_leigu_endursjonun\`.
Frestur umferðarinnar: **01.09**.

**Bann virt upp á rað:** engin DB-skrif (allar tengingar `set_session(readonly=True)`),
`leiga_train.parquet` lesin en ALDREI skrifuð — öll endurmerking gerist í minni,
`predictions_rent` / `valuation_tiers_rent` aðeins lesnar, engin módelbreyting,
ekkert skorað.

---

## 0. MÆLITÆKIÐ SANNAÐ FYRST (tvö hörð hlið)

Engin tala í þessu skjali er birt fyrr en tækið endurgerir hvort tveggja frosnu
artifactin sem hún hvílir á. Bæði hlið eru í kóðanum og fella keyrsluna (`SystemExit`).

| hlið | hvað er endurgert | niðurstaða |
|---|---|---|
| **G1** | `rent_conformal_corrections.json` úr `leiga_train.parquet` + `grouped_split(seed=42)` | 38 sellur, **0 mismunur** á `n_calibration`; calib n = 22.622 = artifactið |
| **G2** | `predictions_rent.segment` úr PRE-cc78 `canonical_code` + frosnu sellunum | **0 mismunur á öllum 158.314 röðum** |

Auk þess: `fallback_lvl` úr `segment` gegn `valuation_tiers_rent.fallback_lvl` = 0 mismunur;
endurgerð LIFANDI þreps úr `(n_local, herb_vantar, fb_old, cc_live)` = 0 mismunur.

Þetta er sama sönnunarröð og cc135 (S0 endurgerði lifandi töfluna EXAKT). Aðferðin
er þar með flutt af sölu-hliðinni yfir á segment-ásinn: **ef ég get endurgert
frosna ástandið upp á rað, þá er breytingin sem ég mæli breytingin sjálf, ekki
mæliskekkja.**

---

## 1. SKORINGARÞÝÐIÐ ENDURMERKT S2

Aðferð cc135 (S1 BÖNNUÐ): lifandi `canonical_code` úr `public.properties` á
**báðum** hliðum — bæði á eigninni sem er skoruð og á leigusamningunum sem
kvarða conformal-sellurnar. `region_tier` og `tegund` eru ósnert af reglu R
(R er eignaflokkun); rek á `region_tier` mælist á 10 samningum af 111.818 og er
ekki hluti S2.

Leigusamningar 2011–2023 (conformal-glugginn): **32.438 af 111.818 (29,01 %)**
bera annað `canonical_code` undir reglu R. 10 fastnúmer finnast ekki í
`properties` og halda parquet-merkingu.

### 1a. Raðir sem víxla segmenti — nefnari 158.314

| mæling | n | % af þýði |
|---|---:|---:|
| **víxla segment-lykli** | **57.473** | **36,30 %** |
| þar af cc-víxl (`cc_pre != cc_live`) | 57.417 | 36,27 % |
| segment-strengur óbreyttur þrátt fyrir cc-víxl | 0 | 0,00 % |

Mismunurinn 57.473 − 57.417 = **56** eru raðir sem víxla lykli án þess að
`canonical_code` breytist: þær falla úr `APT_STANDARD|RVK_core` í `global`
af því sellan sjálf hverfur (sjá 1c).

### 1b. Sundurliðun eftir gömlu × nýju fjölskyldu (aðeins víxlarar)

| gömul fjölskylda | ný fjölskylda | n | % af þýði |
|---|---|---:|---:|
| FJOLBYLI | FJOLBYLI | 30.710 | 19,40 % |
| **FJOLBYLI** | **SERBYLI** | **26.748** | **16,90 %** |
| SERBYLI | SERBYLI | 13 | 0,01 % |
| SERBYLI | FJOLBYLI | 2 | 0,00 % |

Stærstu canonical-víxl: `APT_STANDARD→APT_FLOOR` 30.179 · `APT_FLOOR→SFH_DETACHED`
18.178 · `APT_FLOOR→ROW_HOUSE` 5.519 · `APT_STANDARD→ROW_HOUSE` 2.758.
Full tafla: `01_segment_vixl_eftir_fjolskyldu.csv`, lyklar `01_segment_vixl_lyklar.csv`,
raðgögn `01_skoringarthydi_S2_radir.csv`.

Fjölbýli↔sérbýli-hólfið (26.750 eignir í cc135) helst nánast óbreytt hér: 26.748
þeirra víxla líka conformal-segmenti. **Ásarnir tveir hreyfast á sama hólfinu** —
það er ástæðan fyrir að þeir verða að lagast saman.

### 1c. Þynnka og þykknun conformal-sellanna

Þröskuldurinn er **`MIN_N = 30`**, lesinn úr `rent_conformal.py:45` (ekki giskað).
Sella er til ef og aðeins ef hún ber ≥ 30 kvörðunarsamninga; annars fellur kaskadinn
upp á við.

| stig | halda | **ÞYNNAST ÚT** | ÞYKKNA INN |
|---|---:|---:|---:|
| `cc\|region\|tegund` (Einbýli) | 3 | **3** | 0 |
| `cc\|region` | 19 | **3** | 0 |
| `cc` | 9 | **1** | 0 |
| **alls** | **31** | **7** | **0** |

Sellur alls: **38 → 31**. Af þeim 31 sem halda **vex n á 22, minnkar á 0, stendur á 9**.

Sellurnar sem þynnast út — allar sjö:

| stig | lykill | n fyrir | n eftir |
|---|---|---:|---:|
| cc\|region\|tegund | `APT_FLOOR\|Capital_sub\|Einbýli` | 332 | 19 |
| cc\|region\|tegund | `APT_FLOOR\|Country\|Einbýli` | 474 | 12 |
| cc\|region\|tegund | `APT_FLOOR\|RVK_core\|Einbýli` | 350 | 6 |
| cc | `APT_STANDARD` | 5.401 | 1 |
| cc\|region | `APT_STANDARD\|RVK_core` | 2.722 | 1 |
| cc\|region | `APT_STANDARD\|Capital_sub` | 1.833 | 0 |
| cc\|region | `APT_STANDARD\|Country` | 846 | 0 |

**Þetta er ekki gagnatap — þetta er mótsagnahreinsun.** Sellurnar sem hverfa eru
nákvæmlega þær sem gátu ekki verið til: `APT_FLOOR|*|Einbýli` = samningur skráður
sem Einbýli í leiguskrá á eign sem `properties` kallaði íbúðarhæð; regla R gerir
eignina að `SFH_DETACHED`/`ROW_HOUSE` og mótsögnin gufar upp. `APT_STANDARD`
leysist upp eins og cc143 mældi á sölu-hliðinni (57 eignir eftir í öllu landinu).
Enginn samningur glatast: hann færist í sellu sem er þykkari fyrir.

---

## 2. ÞÉTTLEIKA-ÁSINN (`postnr × canonical_code`)

`leiga_train.parquet` ÓSNERT á diski — endurmerkt í minni. Samningar ≥ 2021:
**7.167 af 21.097 (33,97 %)** endurmerkjast. Talan endurgerir cc135 upp á rað
(bókað þar: 7.167/21.099).

Sellur: **441 → 414** (sameinaður nefnari 486). `n_local` breytist á **327** sellum.

### 2a. Sellur sem skipta þéttleikaflokki: **214 af 486 (44,03 %)**

| fyrir \ eftir | 0 | 1–4 | 5–9 | 10–29 | 30–99 | ≥100 |
|---|---:|---:|---:|---:|---:|---:|
| **0** | 0 | 35 | 5 | 4 | 1 | 0 |
| **1–4** | 30 | 134 | 22 | 7 | 2 | 1 |
| **5–9** | 11 | 11 | 32 | 16 | 3 | 0 |
| **10–29** | 5 | 0 | 8 | 52 | 13 | 1 |
| **30–99** | 6 | 0 | 0 | 3 | 25 | 7 |
| **≥100** | 20 | 2 | 0 | 0 | 1 | 29 |

Á T5-þröskuldinum (`MIN_LOCAL = 5`): **42 sellur fara YFIR** hann (staðbundin
leiguvitneskja verður til) og **55 falla UNDIR** hann.

Eignavegið, nefnari 158.314: **35.261 eignir** sitja á sellu sem skiptir
þéttleikaflokki. 4.465 eignir sitja á (postnr × cc) sem ber engan samning í
hvorugri merkingu.

Skráin: `02_sellur_thettleiki.csv`, `02_thettleikaflokkar_crosstab.csv`.

---

## 3. FALLBACK-DREIFINGIN SEM SPÁ (deterministic, engin skorun)

Kaskada-valið er hreint fall af TALNINGU (`n ≥ MIN_N`), ekki af leifum. Þess vegna
má endurgera það á endurmerktum grunni án þess að skora. Þetta er forspáin sem
þrep 2 mælist gegn — skrifuð **fyrst**, mæld **svo** (7.10-mynstrið).

### 3a. `fallback_lvl` — nefnari 158.314

| lvl | lýsing | fyrir | eftir | breyting | fyrir % | eftir % |
|---:|---|---:|---:|---:|---:|---:|
| 0 | `cc\|region\|tegund` | 17.654 | **36.098** | **+18.444** | 11,15 | 22,80 |
| 1 | `cc\|region` | 139.890 | **121.392** | **−18.498** | 88,36 | 76,68 |
| 2 | `cc` | 575 | 573 | −2 | 0,36 | 0,36 |
| 3 | `global` | 195 | **251** | **+56** | 0,12 | 0,16 |

Raðir sem færast milli stiga: **18.508**. Krossinn (`03_fallback_crosstab.csv`):
1→0 **18.446** · 0→1 2 · 1→2 1 · 1→3 **56** · 2→1 3.

Aðal-hreyfingin er **dýpkun**: 18.446 raðir fá sína eigin `cc|region|tegund`-sellu
þar sem þær sátu áður á grófari `cc|region`. Það er beinlínis það sem
Einbýli-ásinn í `rent_conformal.py` var hannaður til að gera og gat ekki gert
meðan merkingin var röng.

### 3b. Þrep-forspá — nefnari 158.314

| þrep | lifandi | **forspá eftir endurskorun** | breyting |
|---:|---:|---:|---:|
| T1 | 32.526 | 32.526 | 0 |
| T2 | 71.560 | 71.560 | 0 |
| T3 | 20.972 | **20.973** | **+1** |
| T4 | 19.161 | **19.160** | **−1** |
| T5 | 14.095 | 14.095 | 0 |

**Ein einasta röð víxlar þrepi. 0 fá birt mat, 0 missa það.** Þetta er
óþægilegasta og mikilvægasta talan í lotunni og hún er ekki mistök: þrepið les
`fallback_lvl` aðeins á tveimur stöðum (`== 2` gefur +1 þrep, `== 3` gefur T5),
og hreyfingin 1→0 fer framhjá báðum. Röðin sem víxlar er `2297138` (fb 2→1, T4→T3).

### 3c. T5-ástæðurnar færast þótt talan standi

| ástæða | lifandi | forspá | breyting |
|---|---:|---:|---:|
| `of_fair_samningar` | 13.586 | 13.530 | **−56** |
| `engin_svaedisgogn` | 195 | **251** | **+56** |
| `eignaflokkur` | 314 | 314 | 0 |

Allar 56 raðirnar sem falla í `global` eru ÞEGAR í T5 vegna þéttleika — heildin
stendur, ástæðan færist. Sú tilfærsla er sjálf spá sem þrep 2 getur fellt.

### 3d. Það sem er ÓSPÁANLEGT hér — sagt berum orðum

`pi80` og flokkur A–D ráðast af q-gildunum, sem endurreiknast af leifum líkansins
við endurskorun. **Þau eru EKKI forspáanleg án skorunar** og eru þess vegna
mæling þreps 2, ekki spá þessarar lotu. Umfang óvissunnar er þó mælt:

* raðir sem lesa AÐRA conformal-sellu: **57.473 (36,30 %)**
* raðir þar sem `n_conformal` breytist: **153.367**
* `n_conformal` miðgildi: 3.082 → 6.124

Dæmi um stærðargráðuna (`03_nconformal_fyrir_eftir.csv`): `APT_FLOOR|Country`
→ `SFH_DETACHED|Country|Einbýli` færir 10.096 raðir úr sellu með 3.082
kvörðunarsamninga í sellu með 791. Bilið mun hreyfast; í hvora átt og hve mikið
er ómælt hér.

**Forsendur forspárinnar, svo þrep 2 geti fellt hana:** sama `leiga_train.parquet`
(engin ný leiguskrá), sami `SEED=42`-klofningur, `MIN_N=30` óbreytt, `THRESHOLDS`
og `MIN_LOCAL` óbreytt, þéttleiki fastur á cc135-gildunum. Breytist eitthvað af
þessu er forspáin ógild sem viðmið — ekki röng.

---

## 4. PAR-LAGS-KÖNNUN — KORTLAGT, EKKI ÚTFÆRT

Spurningin: getur þéttleika-/sellu-ásinn lesið cc143-artifactið í stað eigin hólfunar?

| viðmið | leiga (cc146) | par-lag (cc143) |
|---|---|---|
| hólfun | `postnr × canonical_code` | `canonical_code × region_tier` |
| fjöldi sella | 414 | 29 |
| landfr. upplausn | **175 póstnúmer** | **3 region_tier** (RVK_core 15 pnr, Capital_sub 27, Country 138) |
| eining sem er talin | leigusamningar ≥ 2021 | endurteknar sölur (pör) 2006Q2–2026Q3 |
| lágmarksþröskuldur | `MIN_LOCAL = 5` (T5-hlið) | `MIN_PAIRS_FOR_REGRESSION = 50`, þunn sería < 500 |
| tímaás | enginn — flatur fjöldi | fjórðungsgrind með vísitölustigi |
| tilgangur | **ÞREP** (birtanleiki mats) | **VÍSITALA** (verðlagsfærsla) |
| miðgildi n á sellu | 6 | 285 |
| sellur undir eigin þröskuldi | 182 af 414 | 8 af 29 |

**Úrskurður: munurinn er EFNISLEGUR.** Sellurnar mæla ólíka hluti. cc143-sellan
þarf n til að meta VERÐBREYTINGU yfir tíma; leigu-sellan þarf n til að svara
hvort staðbundin leiguvitneskja sé yfirleitt til. Læsi leigan cc143-hólfunina
færi hún úr 175 póstnúmerum í 3 svæði: **331 af 414 sellum (80,0 %) bera nú
< 30 samninga, en í cc143-hólfun væru það 10 af 30** — nákvæmlega sá þynnku-ás
sem cc30 byggði þrepið á hyrfi úr sjónmáli. Þetta er sama gildran og cc30 bókaði
um conformal-sellurnar: *kaskadinn felur þynnkuna með því að falla upp á við.*

**BÓKAÐ OG SLEPPT.** Samræming er iter-verk eftir 01.09.
Skrár: `04_parlag_kortlagning.csv`, `04_leiga_i_cc143_holfun.csv`.

---

## 5. FASTNÚM-LAUSI FJÓRÐUNGURINN — MÆLD TALA MEÐ NEFNARA

Talan „~24,4 %“ á sér enga heimild í kóðanum. Mælt upp á rað í lifandi lindunum:

| lind | raðir | auglýsingar | m/fastnum | **án fastnums** | **%** | fastnum sem joinast í `properties` | ferskleiki |
|---|---:|---:|---:|---:|---:|---:|---|
| mbl (`parsed_mbl_rent`) | 3.516 | 3.516 | 0 | **3.516** | **100,00** | 0 | 2026-06-09 .. **2026-08-12** |
| myigloo (`parsed_myigloo`) | 5.973 | 1.809 | 1.642 | 167 | 9,23 | 1.642 | 2026-06-03 .. **2026-08-12** |
| ↳ þar af residential | — | 1.628 | 1.524 | 104 | 6,39 | 1.524 | *(undirmengi)* |
| visir (`parsed_visir`, rent) | 183 | 183 | 159 | 24 | 13,11 | **130** | 01.06 .. 08.06 (STÖÐNUÐ) |
| **SAMTALS** | **9.672** | **5.508** | 1.801 | **3.707** | **67,30** | 1.772 | |

**Tvær tölur, ekki ein — borðið verður að velja þýðið:**

* **67,30 %** ef nefnarinn er allar leiguauglýsingar í lifandi lindunum. Talan er
  borin uppi af mbl: `parsed_mbl_rent` hefur **engan fastnum-dálk í skemanu**,
  aðeins heimilisfang + póstnúmer. Þetta er ekki þekjugat í gögnunum heldur
  vantandi reit í parsernum.
* **9,59 %** (191 af 1.992) ef mbl er tekið út — þ.e. meðal linda sem yfirleitt
  reyna að bera fastnum.

Hvorug er ~24,4 %. Tvö atriði til viðbótar sem breyta þýðinu:

* **visir-fastnúmer joinast ekki**: 159 auglýsingar bera fastnum en aðeins 130
  finnast í `public.properties` → raunverulegt ónothæfi visir er **28,96 %**, ekki
  13,11 %. Fastnum sem joinast ekki er jafn-ónothæfur og fastnum sem vantar.
* **visir-lindin er stöðnuð** (síðasta auglýsing 08.06) — sbr.
  `reference_visir_ip_throttle`. Hún er í nefnaranum en skilar engu nýju.
* Tölurnar eru **uppsafnaðar** í lindunum, ekki „í birtingu núna“.

Til samanburðar ber þjálfunarlindin `leiguskra.csv` (FROSIN 29.06) **0 raðir án
fastnums af 120.558 (0,00 %)** og aðeins **13 fastnúmer (0,01 %)** sem finnast
ekki í `properties`. Fastnúm-vandinn er því **alfarið á auglýsingahliðinni**, ekki
á samningahliðinni sem líkanið er þjálfað á.

Skrá: `05_fastnum_thekja_per_lind.csv`.

---

## 6. VAKTAREIGNIR — NAFNGREIND PRÓFDÆMI UMFERÐARINNAR

### 6a. cc135-tölurnar gerðar upp fyrst

| mæling | allar 158.314 | sýnilegar (158.117) | BÓKAÐ í cc135 |
|---|---:|---:|---:|
| FÁ birt mat | 4.166 | **4.164** | **4.164** ✓ |
| MISSA birt mat | 2.856 | **2.855** | **2.855** ✓ |
| þrepsvíxl | 34.484 | 34.455 | 34.456 (−1) |

FÁ/MISSA endurgerast upp á rað undir sýnileika-síunni (fjöleiningar-vörnin).
Þrepsvíxlin skeika um 1 af því að `v_fjoleining_fastnum` er **tímaháð sýn**:
193 fastnúmer 12.08, **301 núna**. Sbr. `feedback_single_deed_sian_er_timahad`
— sama gerð af galla, önnur tafla.

### 6b. Valdar eignir (lægsta fastnúmer í hverju hólfi = endurvalanlegt)

| # | fastnum | heimilisfang | hólf (n í hólfi) | cc víxl | segment | fb | n_conf | þrep pre-cc135 → lifandi → **FORSPÁ** |
|---|---|---|---|---|---|---|---|---|
| **A** | 2031935 | Hvassaleiti 69, 103 | fjölb↔sérb **FÉKK** mat (410) | `APT_ATTIC→ROW_HOUSE` | `APT_ATTIC\|RVK_core` → `ROW_HOUSE\|RVK_core` | 1→1 | 256→344 | 5 → 4 → **4** |
| **B** | 2023957 | Skeljagrandi 9, 107 | fjölb↔sérb **MISSTI** mat (2.423) | `APT_FLOOR→SFH_DETACHED` | `APT_FLOOR\|RVK_core` → `SFH_DETACHED\|RVK_core\|Einbýli` | **1→0** | 6490→**553** | 2 → 5 → **5** |
| **C** | 2270320 | Grænlandsleið 1, 113 | fallback dýpkar 2→1 (3) | `SEMI_DETACHED→ROW_HOUSE` | `SEMI_DETACHED` → `ROW_HOUSE\|RVK_core` | **2→1** | 194→344 | 4 → 5 → **5** |
| **D** | 2000426 | Vesturgata 30, 101 | fellur í **global** (56) | `APT_STANDARD→APT_STANDARD` | `APT_STANDARD\|RVK_core` → **`global`** | **1→3** | 2722→**22622** | 2 → 5 → **5** |
| **E** | 2297138 | Sogavegur 130, 108 | **eina þrep-víxlið** (1) | `SEMI_DETACHED→ROW_HOUSE` | `SEMI_DETACHED` → `ROW_HOUSE\|RVK_core` | **2→1** | 194→344 | 5 → 4 → **3** |
| **F** | 2000189 | Mýrargata 24, 101 | **viðmið**, segment óbreytt (91.031) | ekkert | `SFH_DETACHED\|RVK_core\|Einbýli` óbreytt | 0→0 | 180→553 | 3 → 2 → **2** |

Eignirnar spanna víxl-hólfin sem beðið var um: A og B eru fjölbýli↔sérbýli sem
FÉKK og MISSTI mat í cc135; C og E sýna dýpkun kaskadans; D er eina hólfið sem
FELLUR í global (og sýnir að T5-ástæðan færist án þess að talan hreyfist); F er
viðmiðið — segment óbreytt, en `n_conformal` fer samt 180→553 af því að sellan
hennar ÞYKKNAR. **F er prófdæmið sem sýnir að bilið hreyfist líka þar sem
lykillinn stendur kyrr.**

Skrá: `06_vaktareignir.csv`.

---

## 7. HVAÐ ÞETTA FORPRÓF SEGIR ÞREPI 2

1. **Ásinn er raunverulegur og stór:** 36,30 % skoringarþýðisins les aðra
   conformal-sellu eftir endurmerkingu, og 26.748 eignir færast milli fjölbýlis
   og sérbýlis.
2. **En hann bítur EKKI á þrepinu.** Forspáin er 1 röð. Endurskorun réttlætist
   ekki á þrepstölunni — hún réttlætist á BILINU, sem er ómælanlegt án hennar.
   Sá rökstuðningur verður að standa berum orðum í ákvörðun þreps 2; talan
   „14.095 → 14.095“ má ekki koma borðinu á óvart eftir á.
3. **Þynnkan sem regla R veldur er mótsagnahreinsun, ekki gagnatap:** 7 sellur
   hverfa, allar sjö annaðhvort `APT_FLOOR|*|Einbýli` (ómöguleg samsetning) eða
   `APT_STANDARD|*` (flokkur sem er nánast horfinn). 22 sellur þykkna, engin
   þynnist sem heldur velli. **0 nýjar sellur ná MIN_N.**
4. **Óspáanlegi hlutinn er nefndur:** `pi80` og flokkur A–D. Þrep 2 verður að
   mæla þau, ekki spá þeim.

---

## 8. BÓKAÐ ÓLEYST (ekki afgangur — sér mál)

* **`parsed_mbl_rent` ber engan fastnum-reit.** 3.516 leiguauglýsingar með
  heimilisfang + póstnúmer en engan lykil í `properties`. Þetta er parser-verk,
  ekki gagnaverk.
* **visir-leigulindin er stöðnuð frá 08.06** og 29 af 159 fastnúmerum hennar
  joinast ekki í `properties`.
* **`v_fjoleining_fastnum` er tímaháð sýn** (193 → 301 á þremur mánuðum). Sérhver
  bókuð tala sem síast í gegnum hana er tímastimpluð hvort sem hún segir það eða
  ekki.
* **Þéttleika-ásinn og conformal-ásinn hólfa sömu eignirnar á ólíkan hátt**
  (postnr × cc gegn cc × region_tier) og hvorugur les cc143-hólfunina. Þrjú
  ólík sellukerfi lifa nú samhliða í kerfinu.

---

**HALT.** Þrep 2 fær sér forskrift eftir þessi skil.
