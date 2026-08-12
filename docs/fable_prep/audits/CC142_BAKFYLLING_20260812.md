# cc142 — VERÐMATS-BAKFYLLINGIN. EIN MÖNNUÐ KEYRSLA. LOKIÐ 12.08.2026.

Heimild: afstaða borðsins — ein keyrsla = **ein hrein frávikadreifing á sama akkeri**.
Forsendan (cc140, mean-öldin) lent: allar nýjar raðir fæðast á `real_pred_mean`.

Rás: `psycopg2` gegnum `run_extraction.py` (transaction pooler). Read-only tenging fyrir
lestur, `SET TRANSACTION READ WRITE` fyrir skrif. **Engin MCP-stæða.**

---

## 0 — ÞURRKEYRSLAN (7.10-reglan: talan mæld NÚNA, ekki lesin úr drögum)

Mælt **11:58 UTC**, gegnum **raunfallið** `extraction_engine.fetch_extracted_listings_to_value`
(`limit=None`, cc134-sían virk) — ekki gegnum spegil af fyrirspurninni.

| | |
|---|---|
| **BIÐRÖÐIN** | **19.022 raðir** |
| eignir (distinct `fastnum`) | 4.013 |
| distinct `source_listing_id` | 19.022 (= raðir; `DISTINCT ON` heldur) |
| **EXCLUDE + NULL `canonical_code`** | **0** |
| adapter-stimpill af diski | `iter4r_20260805_reglaR_strukt` |
| `pipeline_config.model_version` | `iter4r_20260805_reglaR_strukt` (jafnt — útgáfuhliðið opið) |

Talan er **ekki** 18.734 (cc121) né 18.177 (cc134-spá) né 28.703 (cc136). Hún var mæld
og hún er viðmið keyrslunnar.

**cc140-checksumman endurgerð fyrst.** Tjáningin var ekki bókuð sem SQL, aðeins sem
„md5 yfir (id : base : extraction)". Hún var **endurleituð og hitt upp á bæti** — 100
frambjóðendur, 2 treff (jafngild afmörkun sama mengis):

```sql
SELECT md5(string_agg(valuation_id::text||':'||expected_base::text||':'
                      ||expected_extraction::text, ',' ORDER BY valuation_id))
FROM scraper.listing_valuations WHERE valuation_id <= 24562;   -- = 91089f71233ca1d240350c01d3258ecf
```

---

## 1 — KEYRSLAN

```
python -u -m scripts.run_extraction --value-seeded --confirm
```

Án `--skip-valuation`, án `--value-limit` (falsy-gildran er lokuð í cc128, en 0 er samt
aldrei rétt gildi hér), án `--forward` → **enginn `anthropic`-klient er smíðaður**,
án `--bridge` → brúin ósnert (`bridge: SLEPPT` í logginu).

Logg: `keyrsla_cc142.log`. Útgáfuhliðið (cc112) heimilaði skrif:
`adapter == lifandi`. Skorað: `X: (4013, 156)` tvisvar (base + full), serving-lag 3.3 á
3.755 af 3.757 main-röðum, fallback á 256 summer-röðum.

```
value: 19022 extracted listings without a valuation
  valued 19022 listings (skipped 0 unscored); 4013 distinct fastnum scored
```

**`skipped 0`** — engin röð féll úr skoruninni.

---

## 2 — SÖNNUN

### Rowcount-jafnan

| | fyrir | eftir | Δ |
|---|---|---|---|
| raðir alls | 23.610 | **42.632** | **+19.022** |
| hæsta `valuation_id` | 24.567 | 43.589 | — |
| raðir á lifandi `model_version` | 2.968 | 21.990 | +19.022 |

**+19.022 = þurrkeyrslutalan upp á röð.** Id-bilið `24568..43589` er **SAMFELLT**
(43.589 − 24.568 + 1 = 19.022) — engin `ON CONFLICT DO NOTHING`-sleppa, engin endurtekning.

### Checksum gamla mengisins — ÓBREYTT

| mengi | fyrir | eftir |
|---|---|---|
| cc140-mengið (`valuation_id ≤ 24562`, 23.605 raðir) | `91089f71233ca1d240350c01d3258ecf` | **`91089f71233ca1d240350c01d3258ecf`** |
| `sum(expected_base)` sama mengis | 2.012.081.631.136 | **2.012.081.631.136** |
| alt for-keyrslu-mengið (`≤ 24567`, 23.610 raðir) | `0ebcde1c200530aa6f45e9457bf916c3` | **`0ebcde1c200530aa6f45e9457bf916c3`** |

Víðara mengið er mælt LÍKA svo cc140-raðirnar fimm séu inni í vörninni — ekki bara
þær 23.605 sem cc140 bókaði. **Engin gömul röð hreyfðist.**

### Stikkprufa — `expected_base = real_pred_mean` upp á krónu

Ekki 10 raðir heldur **allar sem hafa spátöflu-join: 16.174 af 16.174 (100,0000 %)**,
Δ = 0 kr. `expected_base <> real_pred_mean`: **0**. `expected_base = real_pred_median`:
**0** — svo jafnan er ekki tilviljun tveggja jafnra talna.

**Nefnarinn sagður:** 2.848 raðir (543 eignir) eiga **enga röð í `public.predictions`** og
eru því ósannreynanlegar gegn spátöflunni. Það er þekja spátöflunnar, ekki frávik í
keyrslunni — biðraðar-skilgreiningin krafðist aldrei spátöflu-raðar. Sjá þó §3, þar sem
þessi sami hópur ber langstærsta `extraction_gap`-ið.

### Hin þrjú hliðin

| krafa | mæling |
|---|---|
| `model_version` á nýju röðunum | `iter4r_20260805_reglaR_strukt` × 19.022, **ein og aðeins ein útgáfa** |
| EXCLUDE skrifað | **0** (líka 0 NULL `canonical_code`) |
| `midsaekni_old` á nýju röðunum | `mean` × 19.022, **0 median** |

### Kostnaður

`day_total` 2026-08-12: **$3,9684 → $3,9684.** Óhreyfður. Verðmats-þrepið gerir engin
Haiku-köll og keyrslan snerti ekki `extraction_cost_state.json`. Talan sem stendur eftir
er næturkeðjan frá 01:00, ekki þessi keyrsla.

---

## 3 — FRÁVIKADREIFINGIN (afurðin)

Full sundurliðun með nefnurum: **`SONNUN_OG_DREIFING_CC142.md`** í þessari möppu.
Allt sem hér fer á eftir er **mean-öldin ein** — `GROUP BY midsaekni_old` er sjálfkrafa
hreint á þessu mengi því allt nýtt er `mean`.

### `base_pct_error` — NEFNARINN ER NÚLL, OG ÞAÐ ER RÉTTA STAÐAN

| raðir | seldar (þinglýst ≥ `valued_at`) | með `base_pct_error` |
|---|---|---|
| 19.022 | **0** | **0** |

Þetta er **ekki gat heldur skilgreining**: `v_expected_vs_real_all` tengir sölu með
`s2.thinglystdags >= val.valued_at::date`, og raðirnar voru verðmetnar í dag. **Fyrsta
mean-alda `base_pct_error`-mælingin verður til við fyrstu sölu eftir 12.08.** Hún má
**aldrei** fyllt með median-aldar tölum — `base_pct_error` er ósamfelld tímaröð yfir
aldamörkin (cc140 §5).

Til samanburðar, aldrei til samlagningar:

| öld | raðir | seldar | bjagi | MAPE |
|---|---|---|---|---|
| `mean` | 19.027 | **0** | — | — |
| `median` | 23.605 | 259 | +8,67 % | 14,93 % |

### `extraction_gap` — HEILDIN

| n | gap = 0 | gap > 0 | gap < 0 | meðaltal | miðgildi | min | max |
|---|---|---|---|---|---|---|---|
| 19.022 | 45 (0,24 %) | 11.947 (62,8 %) | 7.030 (37,0 %) | **+1.207.579 kr** | +792.218 kr | −57.867.788 | +31.428.230 |

Sem hlutfall af `expected_base`: **meðaltal +2,3103 %**, miðgildi **+1,0088 %**.
Útdrátturinn **hækkar matið oftar en hann lækkar það** (62,8 % á móti 37,0 %) og
meðaltalið er tvöfalt miðgildið — dreifingin er **hægri-skekkt**, fáar stórar hækkanir
draga meðaltalið.

### `extraction_gap` eftir `canonical_code`

| `canonical_code` | raðir | eignir | gap=0 | meðal-gap kr | miðgildi kr | meðal % | miðgildi % | meðal `expected_base` |
|---|---|---|---|---|---|---|---|---|
| APT_FLOOR | 13.620 | 2.799 | 0 | 1.155.623 | 729.765 | 2,102 | 0,870 | 84.670.438 |
| ROW_HOUSE | 1.776 | 324 | 0 | 2.179.680 | 1.173.562 | 3,073 | 1,446 | 106.058.114 |
| SFH_DETACHED | 1.607 | 437 | 0 | 847.569 | 1.417.229 | 2,639 | 1,181 | 124.189.813 |
| SUMMERHOUSE | 1.048 | 256 | **45** | 1.213.501 | 783.956 | 4,079 | 2,518 | 42.290.985 |
| APT_BASEMENT | 550 | 96 | 0 | 416.650 | 744.554 | 0,879 | 1,813 | 56.928.621 |
| SEMI_DETACHED | 344 | 80 | 0 | 1.195.380 | 969.244 | 2,186 | 0,837 | 96.179.845 |
| APT_ATTIC | 55 | 16 | 0 | 1.186.137 | 1.888.765 | 1,746 | 2,029 | 72.384.077 |
| APT_UNAPPROVED | 10 | 3 | 0 | 18.018 | −20.178 | 0,070 | −0,044 | 40.716.109 |
| APT_MIXED | 8 | **1** | 0 | 3.517.372 | 3.517.372 | 4,286 | 4,286 | 82.062.292 |
| APT_ROOM | 4 | **1** | 0 | −1.962.151 | −1.962.151 | −7,226 | −7,226 | 27.153.710 |

**0 EXCLUDE** — cc134-sían heldur alla leið í töfluna.
**Neðstu tvær línurnar bera EINA EIGN hvor** og eru ekki dreifingar; þær eru
punktar og mega ekki lesast sem flokkseinkenni.
**SFH_DETACHED er eina línan þar sem miðgildið er hærra en meðaltalið** — vinstri-skekkt,
þ.e. fáar stórar LÆKKANIR draga meðaltalið niður, öfugt við allt annað safnið.

### `extraction_gap` eftir flokki A–D (`predictions.confidence_grade`)

| flokkur | raðir | eignir | gap=0 | meðal-gap kr | miðgildi kr | meðal % | miðgildi % | meðal `expected_base` |
|---|---|---|---|---|---|---|---|---|
| A | 10.488 | 2.112 | 0 | 488.980 | 378.305 | **0,807** | 0,464 | 91.048.984 |
| B | 3.577 | 776 | 0 | 579.799 | 428.549 | **0,972** | 0,531 | 103.080.293 |
| C | 1.178 | 356 | 0 | 1.635.444 | 1.203.004 | **4,541** | 2,038 | 79.102.522 |
| D | 931 | 226 | 27 | 1.387.080 | 1.087.094 | **4,409** | 2,777 | 44.428.842 |
| **`<NULL>`** | **2.848** | **543** | 18 | **4.406.697** | 3.758.090 | **7,919** | 6,811 | 69.111.158 |

**EINHALLINN ER SKÝR OG HANN ER RÉTTUR VEGINN:** því lakari sem vissa líkansins er,
því meira hreyfir útdrátturinn matið — A 0,81 % → C/D ~4,5 % → engin einkunn 7,92 %.
Útdrátturinn leggur mest til þar sem grunnlíkanið veit minnst. Það er sú hegðun sem
maður vill sjá og hún var **ekki** hönnuð inn.

**`<NULL>`-línan er stærsta einstaka niðurstaða þessarar dreifingar** og hún er ekki
flokkur heldur **fjarvera**: 2.848 raðir (543 eignir, 15,0 % mengisins) eiga enga röð í
`public.predictions`. Þær bera **fimmfalt** meðal-gap A-flokks og þær eru einmitt
raðirnar sem stikkprufan í §2 gat ekki sannreynt. **Það er ómælt mengi, ekki mælt, og
fer á backlog** — ekki í þessa færslu sem fullyrðing um orsök.

---

## 4 — PÁSAN AFLÉTT (skilyrt GO uppfyllt)

Biðröðin mæld gegnum **raunfallið** eftir keyrslu: **0 raðir.**

`scripts/nightly_delta_chain.sh`: `EXTRACT_VALUE_LIMIT` **0 → 2000**.
Það er nákvæmlega endurræsingin sem cc121 bókaði („ÞESSI EINA TALA") og hún fjarlægir
`--skip-valuation` úr raunkallinu:

```
fyrir:  run_extraction --forward 200 --confirm --skip-valuation
eftir:  run_extraction --forward 200 --confirm --value-limit 2000
```

`bash -n` hreint. Rofinn sannreyndur með því að **keyra sömu greiningu og skelin ber**
(`-gt 0`), ekki með lestri.

**Þakið 2000 er hlutlaust í venjulegri nótt** (biðröð vex ~300/nótt < 2000) — keðjan tekur
sína ~300. Það stendur eftir sem vörn gegn EINNI þekktri bilun: næsta **líkanaskipti**
opnar allar 42.632 raðirnar í einu vetfangi (biðröðin er skilgreind á `model_version`;
cc113 mældi 3 → 21.354 við tenginguna). Sú hrina á að vera valin eins og þessi var.

---

## 5 — BANNIÐ HELT

| bann | mæling |
|---|---|
| extraction-þrepið ósnert | ekkert `--forward`; enginn `anthropic`-klient smíðaður; `day_total` $3,9684 óhreyfður |
| `predictions` ósnert | aðeins lesin (`JOIN` í sönnun); skrifleiðin snertir eina töflu |
| engin gömul röð endurrituð | tvær checksummur óbreyttar; `ON CONFLICT ... DO NOTHING` getur ekki uppfært |
| brúin ósnert | `bridge: SLEPPT (opt-in)` í logginu |

## 6 — ÚT AF STENDUR (ekki gert í cc142, ekki í umfangi)

1. **`<NULL>`-flokkurinn** — 2.848 raðir / 543 eignir án `predictions`-raðar, með
   fimmfalt gap. Ómælt.
2. **cc140-checksum-tjáningin var ekki bókuð sem SQL** og varð að endurleitast. SQL-ið
   er bókað hér að ofan svo næsta lota þurfi þess ekki.
3. **Fyrsta mean-alda `base_pct_error`** verður til við fyrstu sölu eftir 12.08.
4. **Parity-hliðið vaktar enn `median`-höfuðið eitt** (cc140 §6, backlog) — óbreytt af cc142.
5. **Bókun í DECISIONS/STATE + commit** er ógerð; skráarbreytingin er á diski (þar sem
   Task Scheduler les hana) en ekki í git.

---

## VIÐAUKI (cc144, 12.08) — ÞETTA ER GIT-AFRITIÐ, OG ÞAÐ ER EKKI HEILD MÖPPUNNAR

Þessi viðauki er **eina viðbót cc144** við skjalið; engri línu að ofan var hreyft.
Frumritið liggur á `D:\_audit\cc142_verdmats_bakfylling\` og var **ekki** snert.

**Liður 5 í §6 er afgreiddur:** `scripts/nightly_delta_chain.sh` (`EXTRACT_VALUE_LIMIT`
0 → 2000) og þetta skjal eru committuð í `verdmat-is/app` af cc144, og DECISIONS ber
færsluna **§5D-5**. STATE.md var **ekki** uppfært — cc144 hafði umboð til viðbóta í
DECISIONS eingöngu, og það stendur út af.

**`SONNUN_OG_DREIFING_CC142.md` fylgir EKKI í git.** §3 hér að ofan vísar á hana „í
þessari möppu" og sú tilvísun á við **diskmöppuna**, ekki `docs/fable_prep/audits/`.
Ástæðan er bókuð regla, ekki nísku: skráin ber **12 raða stikkprufu á eignastigi**
(`fastnum` × `expected_base` × `real_pred_mean`/`_median`), þ.e. per-eign spár
líkansins, og **app-repoið er opið og deploy-tengt**. Raðgagnaútflutningur úr prod fer
ekki þangað; aggregat gerir það. Allar tölur §2–§3 sem cc142 byggir á eru **aggregat og
eru hér inni** — sundurliðunin sem vantar er nefnaramynd, ekki sönnun, og hún er
endurskapanleg af disknum.
