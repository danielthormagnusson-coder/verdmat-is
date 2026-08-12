# cc134 — EXCLUDE Í VERÐMATSLEIÐINNI: VÉLARNAR TVÆR ÓSAMMÁLA

**Mælt 12.08.2026 · READ-ONLY · engin síun, engin eyðing, engin breyting á vélum.**
Allar DB-tengingar `psycopg2` með `set_session(readonly=True)`. Ekkert var skrifað.
Líkanskeyrslur hér að neðan eru **skorun í minni** — ekkert fór í
`scraper.listing_valuations`.

Heimild: cc130 §5c (nýr liður úr lið #5 í útdráttar-biðraðarmælingunni).

---

## 0. NIÐURSTAÐA Í EINNI MÁLSGREIN

Skorunin er **ekki bara óbirt — hún er utan skilgreiningarsviðs líkansins.**
`training_data_v2.pkl` (sha `32f9a1242b212d11`, sama skrá og þjálfaði lifandi
artefaktið) ber **0 EXCLUDE-raðir af 146.841**, og `canonical_code` er *pandas
Categorical* með **12 flokkum sem EXCLUDE er ekki í**. Við skorun varpast
`'EXCLUDE'` því í `-1 → NaN` og fer niður sjálfgefnu greinina á eiginleika sem
ber 2,87 % gain. Talan sem frýs er ekki mat á atvinnuhúsnæði; hún er **„íbúð af
þessari stærð í þessu matsvæði"**, mæld: að þvinga flokkinn í `APT_FLOOR` færir
hana um aðeins **3,10 % að meðaltali**. Og hún mengar: **6 seldar EXCLUDE-raðir
af 206 (2,9 %) færa `base_pct_error`-bjagann úr +6,06 % í +8,22 %** og
`extraction_gap`-meðaltalið — sjálfa mælinguna á því hvað útdrátturinn skilar —
**úr +0,4927 M kr í +0,2721 M kr, þ.e. 45 % niður**.

---

## 1. ER SKORUNIN MERKINGARLAUS? — ÞJÁLFUNARÞEKJAN

### 1.1 Nefnarinn er sannreyndur

`iter4r_20260805_reglaR_strukt_manifest.json` segir
`data_path = D:\training_data_v2.pkl`, `data_sha256_16 = 32f9a1242b212d11`.
**Endurmælt á diski í dag: `32f9a1242b212d11`.** Skráin sem þjálfaði lifandi
líkanið er bæti fyrir bæti sú sem mælt er hér.

### 1.2 n raðir per `canonical_code` — allt safnið, n = 146.841

| `canonical_code` | train | val | test | held | **alls** |
|---|---|---|---|---|---|
| APT_FLOOR | 82.088 | 6.765 | 6.223 | 3.182 | **98.258** |
| SFH_DETACHED | 17.743 | 1.204 | 1.032 | 506 | **20.485** |
| ROW_HOUSE | 11.130 | 873 | 753 | 352 | **13.108** |
| APT_BASEMENT | 4.964 | 291 | 281 | 118 | **5.654** |
| SUMMERHOUSE | 3.200 | 272 | 313 | 143 | **3.928** |
| SEMI_DETACHED | 2.592 | 233 | 211 | 97 | **3.133** |
| APT_ATTIC | 1.742 | 84 | 86 | 39 | **1.951** |
| APT_UNAPPROVED | 188 | 12 | 9 | 5 | **214** |
| APT_ROOM | 50 | 3 | 1 | 1 | **55** |
| APT_STANDARD | 26 | 1 | 4 | 1 | **32** |
| APT_MIXED | 16 | 0 | 1 | 0 | **17** |
| APT_HOTEL | 4 | 0 | 2 | 0 | **6** |
| **EXCLUDE** | **0** | **0** | **0** | **0** | **0** |

Summan er nákvæmlega 146.841 — **engin `NaN`-röð heldur**. Líkanið hefur því
hvorki séð `EXCLUDE` **né vantandi** `canonical_code` í þjálfun.

### 1.3 Hvað gerist í raun við skorun

`phase_d3_score_extract.build_X_matrix:263`:

```python
X[cat] = pd.Categorical(vals, categories=cat_map[cat])
```

`cat_map["canonical_code"]` er lesið beint úr þjálfunarrammanum
(`phase_d3_score_extract.py:167-170`) og ber **12 flokka**. Mælt:

```
pd.Categorical(['EXCLUDE','APT_FLOOR','SFH_DETACHED'], categories=<12>)
  -> codes [-1, 2, 10]   ->  [nan, 'APT_FLOOR', 'SFH_DETACHED']
```

**`EXCLUDE` er ekki flokkur við skorun. Hann er `NULL`.** Eiginleikinn sem ber
7. hæsta gain í líkaninu (2,87 %) er einfaldlega fjarverandi, og röðin fer niður
sjálfgefnu greinina — grein sem **engin þjálfunarröð þjálfaði**.

### 1.4 SANNPRÓFUN: talan er „íbúð af þessari stærð", ekki mat á flokknum

410 EXCLUDE-eignirnar sem bera frystingu voru skoraðar í minni með lifandi
artefaktinu, fjórum sinnum, aðeins `canonical_code` breytt.

**Parity fyrst** (annars mælir prófið ekki vélina): 201 EXCLUDE-eignir undir
lifandi stimplinum, adapter gegn frystu töflunni — **max |Δ| = 0 kr, 201/201**.
Prófið keyrir sömu vél og nóttin.

| skorað sem | meðaltal | miðgildi | meðal Δ gegn EXCLUDE | **meðal &#124;Δ&#124;** | hámark &#124;Δ&#124; |
|---|---|---|---|---|---|
| **EXCLUDE (eins og er → NaN)** | 64,93 M | 55,45 M | — | — | — |
| þvingað `APT_FLOOR` | 65,41 M | 55,89 M | +0,27 % | **3,10 %** | 7,9 % |
| þvingað `ROW_HOUSE` | 68,00 M | 57,28 M | +4,25 % | 4,33 % | 10,2 % |
| þvingað `SFH_DETACHED` | 70,66 M | 58,12 M | +7,85 % | 7,86 % | 18,7 % |

**Flokkurinn skiptir nánast engu máli.** Talan er afurð `EINFLM` (30,17 % gain),
`matsvaediNUMER` (16,66 %) og `matsvaedi_bucket` (13,47 %) — vélin svarar
spurningunni „hvað kostar íbúðarhúsnæði af þessari stærð hér", óháð því að
eignin er iðnaðarhús.

### 1.5 Það versta: 82 eignir sem hafa ekkert byggingarflatarmál

Af 410 eignum bera **82 (20,0 %) `einflm` NULL eða 0**, 134 (32,7 %) ekkert
`byggar`, 73 (17,8 %) ekkert `matsvaedi_numer`. Frystu tölurnar á þessum 82:

| `tegund_raw` | n | meðal-mat | miðgildi | hámark |
|---|---|---|---|---|
| **Sumarbústaðaland** | 52 | **19,94 M kr** | 20,29 M | 31,08 M |
| **Íbúðarhúsalóð** | 15 | **26,82 M kr** | 25,94 M | 38,63 M |
| Annað land | 7 | 25,05 M | 27,18 M | 30,57 M |
| Hesthús | 1 | 39,68 M | — | — |
| Eyðijörð, nytjað | 1 | 23,64 M | — | — |
| Fjós / Gripahús / Ræktun / Snyrting / Skemma / iðnaðarlóð | 6 | 16,9–31,6 M | — | — |
| **samtals** | **82** | **22,12 M kr** | | **1,81 ma. kr bókfært** |

**Sumarbústaðaland með engri byggingu ber 19,94 M kr „verðmat" að meðaltali.**
Það er ekki vanmat eða ofmat — það er úttak vélar sem fékk `EINFLM = NaN`.

### 1.6 SANNPRÓFUN GEGN MARKAÐI

Frysta matið deilt með **ásettu verði** á sömu auglýsingu (sölu-auglýsingar með
verði):

| `canonical_code` | n | meðal mat/ásett | **MdAPE gegn ásettu** | MAPE |
|---|---|---|---|---|
| APT_ATTIC | 61 | 0,967 | **4,4 %** | 7,4 % |
| APT_FLOOR | 15.486 | 1,107 | **7,7 %** | 28,3 % |
| APT_BASEMENT | 564 | 0,936 | 8,7 % | 10,4 % |
| ROW_HOUSE | 1.871 | 0,907 | 10,8 % | 12,7 % |
| SFH_DETACHED | 1.681 | 1,067 | 14,2 % | 38,3 % |
| SEMI_DETACHED | 381 | 0,911 | 16,3 % | 18,3 % |
| SUMMERHOUSE | 1.147 | 1,187 | 18,6 % | 50,4 % |
| **EXCLUDE** | **2.330** | **3,822** | **60,2 %** | **319,4 %** |

**Dómur á lið 1: talan er ekki „óbirt mat". Hún er úttak líkans á flokki sem
það var aldrei þjálfað á, reiknað úr eiginleikum sem eru að þriðjungi tómir,
og hún hittir markaðinn 4–8× verr en nokkur íbúðarflokkur.**

### 1.7 HLIÐARFUNDUR — SAMA BILUN ER ÞEGAR KOMIN Á BIRTINGARLEIÐINA

`public.properties` ber **14** `canonical_code`-gildi; þjálfunin ber **12**.
Umframgildin eru `EXCLUDE` (56.958 eignir, engin spá — ásetningur) og
**`APT_SENIOR` (89 eignir)**. `APT_SENIOR` er **ekki í þjálfunargögnunum og ekki
í flokkakortinu** — og **allar 89 bera BIRTA spá í `public.predictions`**
(meðaltal 57,20 M kr).

Sannprófað, ekki ályktað: adapterinn skoraði þessar 89 eignir og var borinn
saman við birtu töfluna — **max |Δ| = 0 kr, 89/89**. Birtu spárnar voru því
raunverulega reiknaðar með `canonical_code = NaN`.

**Þetta er utan verksviðs cc134 og er hér bókað sem sjálfstæður liður, ekki
lagað.** Það fellir jafnframt einföldunina „birtingarleiðin útilokar það sem
líkanið kann ekki": hún útilokar `EXCLUDE`, en ekki `APT_SENIOR`.

---

## 2. MENGAR HÚN EITTHVAÐ? — NEYTENDALISTINN

### 2.1 Neytendur `scraper.listing_valuations` — TÆMANDI

Mælt í `pg_depend`/`pg_rewrite` (allt sem er skilgreint ofan á töfluna),
`pg_proc.prosrc` (öll föll), `information_schema.role_table_grants` (hver má
lesa), og grepi yfir bæði repó.

| # | Neytandi | Tegund | Les EXCLUDE-raðirnar? | Flötur |
|---|---|---|---|---|
| 1 | `scraper.v_expected_vs_real` | VIEW (eina objectið ofan á töflunni) | **JÁ — engin sía** | greiningarlotur (cc120, cc123) |
| 2 | `public.ops_scraper_signals()` | SECURITY DEFINER fall | **JÁ — í 4 teljurum** | `/ops` |
| 3 | `extraction_engine.fetch_extracted_listings_to_value` | anti-join við sjálfa sig | JÁ (verkefnaskrá) | nætur-vélin |
| 4 | `app/ops/page.js:243` | ferskleikalína (`max(valued_at)`) | hlutlaus | `/ops` |

**Grants: aðeins `postgres`.** `anon`, `authenticated` og `service_role` bera
**engin** grants á hvorugt objectið. Eina leiðin að vefnum er
`ops_scraper_signals()` (EXECUTE: `postgres`, `service_role`).

**EKKI neytendur — sannreynt:**
`scripts/model_quality_eval.py` **nefnir töfluna 0 sinnum** — vikulega
gæðamælingin (`/adferdafraedi`) er algerlega óháð. Það er í samræmi við
DECISIONS §5D: *„`listing_valuations`-mengið var VÍSVITANDI ekki notað"*.
`verdmat-ai`-repóið les hvorugt (cc130-grep, endurstaðfest).
Engin matview, engin RLS-stefna, ekkert `semantic.*`.

### 2.2 NEYTANDI 1 — `v_expected_vs_real`: mæld áhrif

Nefnari: 23.605 raðir, **206 seldar** (allar með `base_pct_error`).
EXCLUDE-hlutur: **2.372 raðir (10,05 %), 6 seldar (2,9 %)**.

#### `base_pct_error` — **AUGLÝSINGASTIG** (nefnari eins og hann er, n = 206)

| mengi | n | bjagi | MAPE | MdAPE | innan ±10 % |
|---|---|---|---|---|---|
| **ALLT (eins og er)** | 206 | **+8,22 %** | **15,50 %** | 8,48 % | 109 |
| **ÁN EXCLUDE** | 200 | **+6,06 %** | **13,56 %** | 7,93 % | 109 |
| aðeins EXCLUDE | 6 | +80,41 % | 80,41 % | 91,09 % | **0** |
| | | **Δ = 2,16 pp** | **Δ = 1,94 pp** | Δ = 0,55 pp | Δ = 0 |

#### Sama mæling á **EIGNASTIGI** (nefnarinn er á auglýsingu — 5,25 raðir/eign)

| mengi | n eignir | bjagi | MAPE | MdAPE |
|---|---|---|---|---|
| ALLT | 82 | **+5,46 %** | **13,96 %** | 8,31 % |
| ÁN EXCLUDE | 79 | **+3,16 %** | **11,98 %** | 7,72 % |
| aðeins EXCLUDE | 3 | +66,08 % | 66,08 % | 80,17 % |
| | | **Δ = 2,30 pp** | **Δ = 1,98 pp** | Δ = 0,59 pp |

**3 eignir af 82 (3,7 %) bera 2,3 prósentustig af bjaganum.** Áhrifin standa á
báðum nefnurum — þetta er ekki tvítalningar-tálsýn.

#### Raðirnar sex, allar

| fastnum | `tegund_raw` | einflm | mat | raunverð | villa | seldist |
|---|---|---|---|---|---|---|
| 2503743 (×3) | Iðnaður | 206,5 | 163,4 M | 80,9 M | **+102,0 %** | 27.07.2026 |
| 2530691 (×2) | Iðnaður | 82,2 | 78,4 M | 43,5 M | **+80,2 %** | 30.07.2026 |
| 2185718 | Verslun | 136,6 | 63,8 M | 55,0 M | +16,0 % | 04.08.2026 |

Bugðufljót 9 birtist **þrisvar** og Brúarfljót 3 **tvisvar** — fimm af sex röðum
eru tvær eignir.

#### `extraction_pct_error`

| mengi | n | bjagi | MAPE |
|---|---|---|---|
| ALLT | 206 | +7,81 % | 14,50 % |
| ÁN EXCLUDE | 200 | **+6,00 %** | **12,89 %** |
| aðeins EXCLUDE | 6 | +67,98 % | 67,98 % |

#### `extraction_gap` — **STÆRSTA MENGUNIN**

Þetta er mælingin á því hvað útdrátturinn (Haiku-kostnaðurinn) skilar. Hér er
nefnarinn **allar 23.605 raðirnar**, ekki bara seldar — svo EXCLUDE er 10,05 %
af honum, ekki 2,9 %.

| mengi | n | meðal-gap | miðgildi |
|---|---|---|---|
| **ALLT (eins og er)** | 23.605 | **+0,2721 M kr** | +0,1507 M kr |
| **ÁN EXCLUDE** | 21.233 | **+0,4927 M kr** | +0,2105 M kr |
| aðeins EXCLUDE | 2.372 | **−1,7025 M kr** | −0,3679 M kr |

**10 % af röðunum lækka mælt útdráttar-framlag um 45 %** (0,4927 → 0,2721).
EXCLUDE-raðirnar draga í **ÖFUGA átt** við alla aðra flokka (−1,70 M kr gegn
+0,49 M kr). Orsökin er ekki mæld hér — það sem er mælt er að báðar hliðar
gapsins, grunnurinn og yfirlagið, eru reiknaðar á röð þar sem `canonical_code`
er `NaN` í líkaninu. (`build_extraction_features` tekur `canonical_code` líka
sem inntak — `ROW_HOUSE`/`SEMI_DETACHED`-greinin á línu 301 — svo `EXCLUDE`
fellur þar í `else`-greinina á `end_unit_flag`.)

### 2.3 NEYTANDI 2 — `/ops` · `ops_scraper_signals()`: mæld áhrif

| teljari | eins og er | EXCLUDE-hlutur | % |
|---|---|---|---|
| `total_valuations` | 23.605 | **2.372** | 10,05 % |
| `val_count_latest_day` | 2.000 | **179** | 8,95 % |
| `live_res_sale_valued` | 4.199 | **43** | 1,02 % |
| `backlog.unprocessed` | 7.745 | **109** | 1,41 % |

Athugið **ósamræmi í lyklun**: `/ops`-backlogið síar á
`listings_canonical.category = 'residential'` (**auglýsingaflokkur**) meðan
verðmatið ræðst af `properties.canonical_code` (**eignaflokkur**). Þess vegna
eru aðeins 109 EXCLUDE-raðir í backloginu en 2.093 í verðmats-biðröðinni:
**tvær ólíkar skilgreiningar á „íbúð" á sama spjaldi.**
`unprocessed` ber amber-þröskuld við 5.000 (`app/ops/page.js:337`).

---

## 3. SÍUHÖNNUN — Á `value_listings` AÐ BERA SÖMU ÚTILOKUN?

### 3.1 RÓTIN: sían er til, en í RÖNGU FALLI

`phase_d3_score_extract.main()` ber þriggja hliða trekt (línur 451-464):

```python
is_scorable  = ins["is_residential"] | ins["is_summerhouse"]     # EXCLUDE-hliðið
has_byggar   = ins["byggar"].notna()
is_confident = ins["matsvaedi_confident"].fillna(False)
scor = ins[is_scorable & has_byggar & is_confident]
```

`value_listings` kallar **`score()` beint** gegnum `_score_iter4`, ekki `main()`.
**Trektin er í keyrslu-drifinu, ekki í skorunarfallinu** — svo nætur-vélin
endurnýtir vélina og sleppir öllum þremur hliðum. Þetta er sama gerð og cc112
(hlið á mælingu en ekki á skrifleið) og cc94 (`flatten_row`-skynjarinn sem bjó
í falli sem keðjan kallaði aldrei).

### 3.2 Hvernig sían liti út

`fetch_extracted_listings_to_value` (`extraction_engine.py:193-230`) hefur
`public.properties pr` **þegar í JOIN-inu**, svo sían er ein WHERE-lína — engin
ný tenging, engin ný tafla:

```sql
      WHERE l.source = 'mbl' AND l.fastnum IS NOT NULL AND l.lysing IS NOT NULL
        AND v.valuation_id IS NULL
        AND (e.validation_status IS NULL OR e.validation_status NOT LIKE 'rejected:%%')
+       -- cc134: skorunarhliðið úr phase_d3_score_extract.main() sem score() ber ekki.
+       AND (pr.is_residential OR pr.is_summerhouse)
```

### 3.3 Hvað fjarlægir hver kostur — mælt á biðröðinni (n = 20.270 / 4.312 eignir)

| sía | eftir | **burt** | eignir eftir |
|---|---|---|---|
| engin (eins og er) | 20.270 | 0 | 4.312 |
| **S1** `canonical_code <> 'EXCLUDE'` | 18.177 | **2.093 (10,33 %)** | 3.897 |
| **S2** `is_residential OR is_summerhouse` | 18.177 | **2.093** | 3.897 |
| **S3** S2 + `byggar IS NOT NULL` | 16.293 | 3.977 (19,62 %) | 3.535 |
| **S4** `EXISTS (public.predictions)` | 15.461 | 4.809 (23,72 %) | 3.366 |

**S1 ≡ S2 nákvæmlega.** Krossmælt á öllu safninu (232.887 eignir):
`canonical_code = 'EXCLUDE'` og `NOT (is_residential OR is_summerhouse)` eru
**sama mengi, 56.958 eignir, núll frávik í hvoruga átt**. Orðalagið skiptir því
engu; **S2 er samt réttara orðalagið** af því að það er *sama tjáningin og
birtingarleiðin notar* — sían og hliðið verða þá læsileg sem sama regla.

### 3.4 S4 er strangasta lesningin á spurningunni — og hún er stærri

Sé spurningin lesin bókstaflega („sömu útilokun og birtingarleiðin") er svarið
S4: **verðmeta ekkert sem birtingarleiðin ber ekki spá á.** Hún fjarlægir
2.093 EXCLUDE **auk 2.716 raða á 531 eign sem eru íbúðarhæfar en bera samt enga
spá** — halinn í §1.7-töflunni (SUMMERHOUSE 16,18 % án spár, SFH_DETACHED
8,33 %, APT_FLOOR 2,47 %).

**S4 er hins vegar ekki lögð til hér.** Hún er hlið á *afurð annarrar vélar*
(`public.predictions` er endurbyggð per flipp), svo hún myndi láta biðröðina
hreyfast við hverja endurbyggingu spátöflunnar — og sá halinn er sjálfstætt
mál sem er ekki mælt í þessari lotu. **S2 er sían sem þessi mæling ber.**
Halinn (2.716 raðir / 531 eign) er bókaður sem opinn liður.

### 3.5 Hvað verður um þær 2.372 sem þegar eru til

Sían er á **verkefnaskránni**, ekki á töflunni. Hún snertir engar núverandi
raðir. Skiptingin sem valkostirnir í §4 þurfa:

| stimpill | raðir | eignir | seldar (í `base_pct_error`) |
|---|---|---|---|
| `iter4_final_v1` (sögulegt) | 2.126 | 406 | **6** |
| `iter4r_20260805_reglaR_strukt` (lifandi) | 246 | 201 | 0 |
| **alls** | **2.372** | **410** | **6** |

**Öll mengunin í §2.2 situr í sögulega stimplinum.** Lifandi stimpillinn ber
enga selda EXCLUDE-röð — enn.

---

## 4. AFSTÖÐUKOSTIR

Sameiginlegt öllum: **kostnaður er $0,00 í allar áttir.** Verðmats-þrepið gerir
engin Haiku-köll; útdrættirnir eru þegar keyptir og bókaðir. Þetta er ekki
sparnaðarákvörðun. Sömuleiðis: verðmats-þrepið er í **pásu frá 09.08**
(`EXTRACT_VALUE_LIMIT=0` → `--skip-valuation`, cc121), svo ekkert af þessu
blæðir í nótt — glugginn er opinn.

### KOSTUR (a) — sía framvegis, láta gömlu standa

| | |
|---|---|
| **Breyting** | ein WHERE-lína í `fetch_extracted_listings_to_value` (§3.2) |
| **Hvað hverfur** | 2.093 raðir / 415 eignir úr biðröðinni; **0 raðir í töflunni** |
| **Hver finnur fyrir** | `/ops`: `unprocessed` fær **varanlegt gólf 109** (aldrei tæmt); `backlog`-nefnarinn og verðmats-nefnarinn hætta að stemma |
| **Hvað brotnar** | Ekkert í kóða. `v_expected_vs_real` **ber áfram alla mengunina í §2.2** — bjaginn stendur +8,22 % og `extraction_gap` +0,2721 M kr |
| **Áhætta** | **Talan sem lítur út fyrir að vera löguð er það ekki.** Sá sem les töfluna eftir (a) sér óbreytta mengun og heldur að hún sé hrein — nákvæmlega gerðin *„færsla sem lýsir viðgerð er ekki viðgerð"* |

### KOSTUR (b) — sía **og** hreinsa gamlar

| | |
|---|---|
| **Breyting** | (a) + `DELETE` á 2.372 röðum á `valuation_id = ANY(listi)` |
| **Hvað hverfur** | `total_valuations` 23.605 → **21.233**; `live_res_sale_valued` 4.199 → **4.156**; sex seldu raðirnar |
| **Mælingar á eftir** | bjagi **+6,06 %**, MAPE **13,56 %**, `extraction_gap` **+0,4927 M kr** — hreint, ekki með fyrirvara |
| **Hvað brotnar** | Ekkert í kóða (engin FK vísar inn). **En:** 2.126 raðir eru **sögulegt verðmat undir dauðum stimpli** — cc131 bókaði þann flokk sérstaklega sem *„ekki endurbyggingarefni"*. Eyðing er þá **eyðing á sögu**, ekki hreinsun á rusli |
| **Skilyrði ef valið** | CSV+JSONL-varðveisla með sha á undan (cc116-mynstrið), `DELETE` á lista af `valuation_id`, aldrei á skilyrði — regla `feedback_insert_first_thegar_lykillinn_greinir` |
| **Áhætta** | Óafturkræft án varðveislunnar. Hún kostar ekkert; sleppa henni er eina raunverulega áhættan |

### KOSTUR (c) — láta standa, undanskilja í mælingum

| | |
|---|---|
| **Breyting** | Sía inni í `scraper.v_expected_vs_real` (`CREATE OR REPLACE VIEW` + `JOIN public.properties`) — **eða** í hverri mælingu fyrir sig |
| **Hvað hverfur** | Ekkert af diski. Raðirnar standa, mælingin verður hrein |
| **Hver finnur fyrir** | `/ops`-teljarar standa óbreyttir (10,05 % EXCLUDE) — **misræmi milli spjalds og sýnar** verður varanlegt |
| **Hvað brotnar** | Ekkert. En **vélin heldur áfram að skrifa** ~2.093 nýjar merkingarlausar raðir þegar pásan er tekin af, og sían þarf að standa að eilífu |
| **Áhætta** | Meðhöndlar einkennið. Þegar hún er í sýninni er hún **ein sía á einum stað sem allir framtíðar-nefnarar erfa** — það er skárra en per-mæling, en það lagar hvorki skrifin né `/ops` |

### KOSTUR (d) — láta standa óbreytt og bóka

| | |
|---|---|
| **Breyting** | Engin nema DECISIONS-færsla |
| **Hvað hverfur** | Ekkert |
| **Hvað brotnar** | Ekkert **í dag**. Á morgun: hver framtíðarlota sem les `base_pct_error` eða `extraction_gap` beint úr sýninni fær mengaða tölu og verður að muna eftir færslunni |
| **Áhætta** | Hæst. Bókun sem verður að vera lesin til að tala sé rétt er sama gerð og `feedback_bokun_um_vidgerd_er_ekki_vidgerd`: rétta talan í skjalinu, ranga talan í gagninu |

**MÆLT — MENGUNIN HEFUR EKKI ENN KOMIST Í BIRTA TÖLU, FYRIR TILVILJUN.**
cc120 §3.2 birti **+7,84 %** á n = 180. Sá nefnari krafðist tengingar við
`public.predictions_2026_04` (til að endurheimta samfrysta meðaltalið) — og
**apríl-árgangurinn ber 0 EXCLUDE-eignir**, eins og allar spátöflur. Mælt á
206 seldu röðunum í dag:

| | tengist apríl-árgangi | tengist ekki |
|---|---|---|
| annað | 186 | 14 |
| **EXCLUDE** | **0** | **6** |

**Öll sex EXCLUDE-röðin féllu út úr cc120-nefnaranum af sjálfu sér.** cc120-talan
var því hrein — en hún var hrein **fyrir tilviljun**, af því að tengingin sem
mælingin þurfti í öðrum tilgangi virkaði óvart sem EXCLUDE-sía. Sá sem spyr
sýnina beint (`select avg(base_pct_error) from scraper.v_expected_vs_real`,
augljósasta leiðin) fær **+8,22 %**. Þetta er því hlaðin byssa, ekki afhleypt:
kostur (d) skilur hana hlaðna.

### Samanburður í einni töflu

| | vélin hættir | mælingin hrein | `/ops` réttur | saga varðveitt | óafturkræft |
|---|---|---|---|---|---|
| **(a)** | ✅ | ❌ | ⚠ gólf 109 | ✅ | nei |
| **(b)** | ✅ | ✅ | ✅ | ❌ | **já** |
| **(c)** | ❌ | ✅ | ❌ | ✅ | nei |
| **(d)** | ❌ | ❌ | ❌ | ✅ | nei |

**(a) + (c) saman** gefur ✅ á fyrstu þremur og ✅ á fjórða — vélin hættir, sýnin
verður hrein, `/ops`-gólfið er eina bókaða frávikið, og engin saga tapast. Sá
samsetti kostur er **ekki** í upphaflega listanum og er lagður fram hér sem
mælingarniðurstaða, ekki sem ákvörðun.

---

## 5. ÓLEYSTIR LIÐIR SEM MÆLINGIN FANN (ekki hluti af ákvörðuninni)

1. **`APT_SENIOR` — 89 BIRTAR spár á óþjálfuðum flokki** (§1.7). Sama bilun,
   en á birtingarleiðinni. Sannprófað 89/89 max |Δ| = 0 kr.
2. **531 eign / 2.716 raðir í biðröðinni sem eru íbúðarhæfar en bera samt enga
   spá** (§3.4) — SUMMERHOUSE 16,18 % af flokknum, SFH_DETACHED 8,33 %.
3. **`/ops` lyklar backlog á `listings_canonical.category` en verðmatið á
   `properties.canonical_code`** (§2.3) — 109 gegn 2.093.
4. **`v_expected_vs_real` telur á auglýsingu, ekki eign** (5,25 raðir/eign);
   Bugðufljót 9 vegur þrefalt í sex-raða menginu.

---

## 6. AÐFERÐ OG SANNPRÓFUN

| | |
|---|---|
| DB | `psycopg2`, `set_session(readonly=True)`, transaction pooler 6543 |
| Skrif | **engin** — hvorki DB, artefökt né vélar snertar |
| Haiku-köll | **0** ($0,00) |
| Líkan | `iter4r_20260805_reglaR_strukt` úr `pipeline_config.model_version`, artefakt af diski, manifest-stimpill |
| Þjálfunargögn | `D:\training_data_v2.pkl`, sha256[:16] **endurmælt** `32f9a1242b212d11` = manifest |
| Parity-sönnun 1 | 201 EXCLUDE-eignir undir lifandi stimpli: adapter gegn frystingu, **max &#124;Δ&#124; = 0 kr, 201/201** |
| Parity-sönnun 2 | 89 APT_SENIOR: adapter gegn `public.predictions`, **max &#124;Δ&#124; = 0 kr, 89/89** |
| Neytendaleit | `pg_depend`+`pg_rewrite` (objects), `pg_proc.prosrc` (föll), `role_table_grants` (grants), grep bæði repó |
| Skriftur | `…\scratchpad\cc134_{db,m1,m3,m4,m5,m6,m7,probe,probe2}.py` |

**HALT.** Engin sía sett, engu eytt, engri vél breytt. Kostirnir fjórir (+ samsetti
(a)+(c)) bíða ákvörðunar borðsins.

---

## 7. VIÐAUKI 12.08 kl. 10:07Z — KOSTUR (c) APPLÝJAÐUR

**Þessi kafli er viðbót eftir á. §0–§6 hér að ofan standa ÓBREYTT eins og þau
voru skrifuð fyrir apply** — þar á meðal setningin í §4 um að migration væri
óapplýjuð. Sú lesning var rétt þegar hún var skrifuð og er leiðrétt hér að
neðan, ekki þurrkuð út (sama regla og cc105 fylgdi).

### 7.1 RÁSIN VAR PSYCOPG2, EKKI SUPABASE MCP — OG JAFNGILDIÐ VAR SMÍÐAÐ

`apply_migration` var **ótengt í lotunni**. Staðfest með þremur ToolSearch-leitum
(`+supabase apply_migration`, `select:mcp__supabase__apply_migration,…`,
berum `apply_migration`) — engin niðurstaða; aðeins `claude-in-chrome`,
`context7` og `financial-analysis` voru til staðar. Borðið heimilaði psycopg2 á
transaction pooler gegn **þremur skilyrðum**, sem öll voru uppfyllt:

| # | skilyrði | hvernig það var uppfyllt | sannprófun |
|---|---|---|---|
| 1 | `schema_migrations` handvirkt, **í sömu txn og stæðan** | `INSERT` í `supabase_migrations.schema_migrations` er inni í sama txn og DDL-ið; fall veltur báðum til baka | 8 færslur, `20260812002226`–`002233`, `n_stmt = 1` hver |
| 2 | **hvert statement sér** (cc86), `SET TRANSACTION READ WRITE` fyrst, fall á n stöðvar n+1 | átta aðskildar txn-ir; `SET TRANSACTION READ WRITE` er fyrsta stæðan í hverri; `raise` eftir `rollback()` stöðvar lykkjuna | 8/8 keyrðar, engin féll |
| 3 | **spegill úr töflunni**, ekki úr drögunum | `supabase/migrations/20260812002226_…sql` endurskrifuð úr `schema_migrations.statements` | sjá §7.4 |

`created_by` ber rásina (`… (psycopg2, cc134 — MCP ótengt)`) svo hún sjáist **í
töflunni sjálfri**, ekki aðeins í þessu skjali. Næsta lota sem les
`schema_migrations` sér því strax að þessar átta færslur komu ekki frá MCP.

**Af hverju þetta var ekki hljóðlát rásaskipti:** MCP-leiðin gerir tvennt
sjálfkrafa sem psycopg2 gerir ekki — hún skráir migrationina og hún bindur
skráninguna við keyrsluna. Skilyrðin þrjú eru nákvæmlega þessi tvö atriði
handsmíðuð, plús krafan um að spegillinn sanni hvað var keyrt. **Jafngildið var
því smíðað, ekki gefið sér.**

### 7.2 EFTIRMÆLING — NEFNARARNIR HREYFÐUST, OG ÞAÐ ER SJÁLFSTÆÐ NIÐURSTAÐA

Milli mælingarinnar kl. 00:06 og apply kl. ~10:00 **breyttust lifandi gögnin**:
49 nýjar virkar auglýsingar og **53 nýjar seldar raðir** úr `daily_sales_refresh`
(206 → 259 raðir með `base_pct_error`). **Töflurnar í DECISIONS §5D-2 §4 eru því
ekki lengur beinn samanburður** — þær mældu annan nefnara.

Þess vegna var **forspá reiknuð á FERSKUM gögnum rétt fyrir apply**, svo
sannprófunin yrði forspárpróf en ekki eftiráskýring. Teljararnir voru síðan
lesnir eftir apply með því að **kalla `ops_scraper_signals()`** — sömu leið og
`/ops` fer — ekki með endurrituðu SQL.

| teljari | fyrir | forspá | **MÆLT** | |
|---|---|---|---|---|
| `total_valuations` | 23.605 | 21.233 | **21.233** | ✓ |
| `val_count_latest_day` | 2.000 | 1.821 | **1.821** | ✓ |
| `backlog.live_res_sale` | 11.993 | 11.840 | **11.840** | ✓ |
| `backlog.live_res_sale_valued` | 4.199 | 4.156 | **4.156** | ✓ |
| `backlog.unprocessed` | 7.794 | 7.684 | **7.684** | ✓ |
| `v_expected_vs_real` raðir | 23.605 | 21.233 | **21.233** | ✓ |
| `base_pct_error` bjagi | +8,67 % | +5,55 % | **+5,55 %** | ✓ |
| MAPE | 14,93 % | 11,98 % | **11,98 %** | ✓ |
| n seldar | 259 | 252 | **252** | ✓ |

**Öll níu gildin lentu á forspánni upp á tölu.** Samlagningin heldur:
**11.840 = 4.156 + 7.684**. Ferskleikalínan (`valuation_max`) er **ósíuð** eins og
til stóð — hún svarar „keyrði vélin", ekki „hvað skrifaði hún".

**Gólfið 109 er farið.** `unprocessed` féll um 110 (109 EXCLUDE + 1 sem varð
verðmetin/afskráð í millitíðinni), og (a)+(c) eru þar með báðar inni.

**Um 8,22 → 6,06 úr GO-inu:** sú tala var rétt á 00:06-nefnaranum (n=206). Á
10:07-nefnaranum (n=259) er hún **8,67 → 5,55**. Áttin og stærðin standa
(≈3,1 pp), en **talan sjálf er nefnaraháð og má ekki vitna í hana án dagsetningar.**

### 7.3 SKILYRÐI GO-INS: `canonical_code`-DÁLKURINN

`scraper.v_expected_vs_real_all` ber **`canonical_code` í sæti 34**. Báðar sýnir
bera 34 dálka (33 upprunalegir + nýi aftast), sem er skilyrði
`CREATE OR REPLACE VIEW`. Þetta er dálkurinn sem vantaði í cc120 og er ástæðan
fyrir að EXCLUDE-halinn sást ekki þá.

### 7.4 SPEGILLINN — OG ÞVERSÖGNIN SEM MÁTTI EKKI „LAGAST"

Statements voru lesin **orðrétt úr `schema_migrations.statements`** og skráin
endurskrifuð af þeim lestri. Lesturinn var borinn saman við drögin: **0 frávik af
8 — drögin voru keyrð óbreytt.**

Samanburðurinn er festur við **git-útgáfu draganna (`581e092`)**, ekki við skrána
á diski. Fyrsta útgáfa speglunar-skriptsins las drögin af diski og gaf því
`0 frávik` í fyrstu keyrslu en `8 frávik` í annarri — af því að það var þá farið
að bera töfluna saman við spegilinn sem það hafði sjálft skrifað. **Sannprófun
sem skiptir um merkingu við aðra keyrslu er ekki sannprófun**; hún er nú
idempotent (sama sha, sama dómur, endurtekið).

**Þversögn sem stendur af ásettu ráði:** stæða 01 ber innbyggðan haus draganna,
þar á meðal línuna *„ÓAPPLÝJUÐ … hefur EKKI verið keyrð"* og for-apply tölurnar
(11.944 → 11.792). Sá texti **var hluti af því sem var keyrt** og stendur því
óbreyttur — að snyrta hann væri að falsa spegilinn. Skráarhausinn ber viðvörun um
að hann gildi þar sem þeim ber á milli.

| skrá | sha256[:16] |
|---|---|
| drögin sem voru keyrð (`581e092`) | `870a25195041f3ff` |
| **spegillinn úr töflunni** | **`efd673ceed639ed9`** |
| rollback (ósnertur) | `cc09761ba588d2fd` |

### 7.5 RÉTTINDI — MÆLD Á `relacl`/`proacl`, EKKI `information_schema`

cc105-reglan: grantor og `PUBLIC`-grants sjást hvergi í `information_schema`.

| object | ACL |
|---|---|
| `scraper.v_expected_vs_real_all` | `{postgres=arwdDxtm/postgres}` |
| `scraper.v_expected_vs_real` | `<engin skráð — erfir eiganda>` |
| `public.ops_scraper_signals()` | `{postgres=X/postgres,service_role=X/postgres}` |

`aclexplode` á nýju sýninni: **`anon`, `authenticated` og `PUBLIC` bera EKKERT.**
Nýja sýnin er því jafn lokuð og sú sem fyrir var, sagt berum orðum í migrationinni
frekar en látið ráðast af default privileges.

### 7.6 HVAÐ STENDUR EFTIR

Óbreytt frá §5: fjórir opnir liðir á `PLANNING_BACKLOG` (`APT_SENIOR` fremst).
Verðmats-þrepið er **áfram í pásu** (`EXTRACT_VALUE_LIMIT=0`) — cc134 breytti því
ekki og átti ekki að gera það. Rollback er óbreyttur og gildur; hann skilar
`v_expected_vs_real` beint á töfluna, sleppir `_all` og setur teljarana sjö í
fyrra horf.
