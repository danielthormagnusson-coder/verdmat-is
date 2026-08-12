# PRIOR-MERKIÐ OG V2-FLÖTURINN — cc152

**Dags:** 2026-08-13 · **Lota:** cc152 · **Staða:** LIÐIR 0–3 FRAMKVÆMDIR, **HALT B** (push=deploy)
**Heimild:** cc151 (`PRIOR_FLAG_CC151_20260812.md`, `D:\_audit\cc151_prior_flag\`), cc145
**Mælikeyrslur:** `precompute/cc152_iter3v2.py`, `cc152_thynnka_rot.py`,
`cc152_thynnka_vaenting.py`, `cc152_thynnka_parity.py`, `cc152_k8_grunnur.py`
— allar `set_session(readonly=True)` · flipp: `cc152_prep_snapshot.py`,
`cc152_flip.py`, `cc152_revoke_iter3v2.py` (sjá VIÐAUKA aftast)
**Hrágögn:** `D:\_audit\cc152_prior_merki_v2\` · **Staging:** `D:\cc152\prior_fix.{csv,parquet}`

---

## NIÐURSTAÐA Í ÞREMUR SETNINGUM

1. `predictions_iter3v2` er **frosin tafla** (gamla `predictions`, endurnefnd við
   iter4-innflutning), 100 % ósamhljóða vélinni — **en enginn notendaflötur les hana**,
   svo birtingaratvikið sem liður 0 leitaði að er **ekki til**.
2. Þynnkuflaggið var **borið á ásinn eftir fallhliðið sem tryggir þröskuldinn**: valdar
   sellur bera ≥ 670 pör, felldar ≤ 485, þröskuldur 500 — sönnuð rót, rótarfix keyrt
   gegnum staging með **parity PASS á öllum 15 öðrum dálkum**, 2.966 raðir breytast.
3. **K8 stenst dómsskilyrðið** (2,53 % af akkeruðum, innan 2–15 %) og er þar með
   aðalkosturinn — og hann logar **einhalla eftir gagnagæðum**, öfugt við K0.

**Og eitt til: forsenda liðar 3 er röng.** Lifandi `/eign` (verdmat.ai) er **þegar
V2-eingöngu** og hefur verið síðan 2026-07-05. cc151 §5 mældi **frosna app-repóið**.
Sjá §5.

---

## 0. HVAÐ ER `predictions_iter3v2`?

### 0.1 (a) Tafla eða view — `pg_class`

| nspname | relname | relkind | tegund | est_rows |
|---|---|---|---|---:|
| public | `predictions` | `r` | **tafla** | 167.503 |
| public | `predictions_iter3v2` | `r` | **TAFLA** | 110.316 |
| public | `v_current_predictions` | `v` | view | — |

`v_current_predictions` er `SELECT DISTINCT ON (fastnum) … FROM predictions ORDER BY
fastnum, predicted_at DESC`. `predictions_iter3v2` er **ekki** view og **ekki** samheiti
— hún er sjálfstæð, frosin tafla.

**Uppruni hennar er í skrifleiðinni, orðrétt:**

```python
# precompute/import_iter4.py:31,39
DROP TABLE IF EXISTS predictions_iter3v2 CASCADE;
...
ALTER TABLE predictions RENAME TO predictions_iter3v2;
```

Hún **er** gamla `predictions`-taflan, endurnefnd þegar iter4 var flutt inn. Og eldri
migration bókar tilganginn berum orðum:

```sql
-- app/supabase/_legacy_migrations/20260506_rls_baseline_audit.sql:57
-- predictions_iter3v2 (~110K rows, 18 MB) — debug-mode comparison surface
```

### 0.2 (b) `model_version` og `predicted_at`

| tafla | raðir | einkvæm fastnum | model_version | predicted_at |
|---|---:|---:|---|---|
| `predictions_iter3v2` | 110.316 | 110.316 | `iter3v2` (110.316/110.316) | **2026-04-01**, 1 dagur |
| `v_current_predictions` | 167.503 | 167.503 | `iter4r_20260805_reglaR_strukt` | **2026-07-01**, 1 dagur |

Ein útgáfa hvor, einn dagur hvor. Fjögurra mánaða og heillar líkanakynslóðar munur.

### 0.3 (c) |Δ| gegn `v_current_predictions`

Samanburðardálkur `real_pred_mean` báðum megin. Join á `fastnum`:

| stærð | tala |
|---|---:|
| fastnum í `predictions_iter3v2` | 110.316 |
| fastnum í `v_current_predictions` | 167.503 |
| **sameiginlegir** | **110.316** (iter3v2 ⊂ v_current) |
| aðeins í `v_current` | 57.187 |
| nothæfar raðir (bæði > 0) | 110.316 |

| þröskuldur | teljari | af 110.316 |
|---|---:|---:|
| \|Δ\| > 0,00 % | 110.316 | **100,0000 %** |
| \|Δ\| > 0,50 % | 104.111 | 94,3752 % |
| \|Δ\| > 1,00 % | 98.010 | 88,8448 % |
| \|Δ\| > 2,00 % | 85.876 | 77,8455 % |
| \|Δ\| > 5,00 % | 54.649 | 49,5386 % |
| \|Δ\| > 10,00 % | 25.469 | 23,0873 % |

**\|Δ\| dreifing:** p50 **4,94 %** · p75 9,42 % · **p90 20,49 %** · p95 35,76 % ·
p99 80,07 % · max 1.014,93 % · meðaltal 9,50 %.
**Formerkt Δ:** p05 −9,75 % · p25 −3,77 % · p50 +0,72 % · p75 +6,83 % · p95 +34,81 %.

**Nákvæmlega sama tala: 0 af 110.316. Önnur tala en vélin framleiðir: 110.316 = 100,00 %.**

### 0.4 GO-DÓMUR

Verkbeiðnin setti tvö HALT-mörk: **stöðnuð spá á > 1 % eigna** eða **\|Δ\| p90 > 2 %**.
Á töflunni eru bæði rofin margfalt (100 % og 20,49 %).

**En skilyrðið er orðað „Beri FLÖTURINN stöðnuð spá" — og flöturinn ber hana ekki.**
Grep á `predictions_iter3v2` yfir öll þrjú repó:

| repó | hit á notendafleti |
|---|---|
| `verdmat-ai` (LIFANDI, www.verdmat.ai) | **ENGIN — núll tilvísun í öllu repóinu** |
| `app` (frosið) | ein, `app/eign/[fastnum]/page.js:82` — **inni í `if (showDebug)`** |
| `precompute` | skrifleið + mælingar |

Í frosna repóinu er sóknin sjálf skilyrt:

```js
// app/eign/[fastnum]/page.js:55,79-88,95
const showDebug = sp.mode === "debug";
...
if (showDebug) {
  queries.push(supabase.from("predictions_iter3v2").select("*").eq("fastnum", fnum).maybeSingle());
}
...
const iter3Prediction = showDebug ? results[5]?.data : null;
```

og öll þrjú birtingarstöðin (línur 510, 538, 543) liggja inni í `{showDebug && …}`. Þar
er talan birt **hlið við hlið við iter4-töluna, merkt sem gamla líkanið** — sem er
nákvæmlega það sem taflan er til fyrir.

> **DÓMUR: GO.** Taflan er stöðnuð að fullu, en hún er **debug-artefakt á bak við
> `?mode=debug`**, ekki birtingarflötur. Ekkert birtingaratvik. Björgun á ekki við;
> merkjavinnan heldur áfram.
>
> **Bókað sem áhætta, ekki atvik:** taflan er `anon`-læs (`public_read`, `GRANT SELECT
> TO anon`), svo hver sem er getur sótt 110.316 fjögurra mánaða gamlar spár um
> PostgREST. Það er ekki flötur, en það er opið yfirborð. Tillaga í §6.

---

## 1. ÞYNNKUFLAGGIÐ — RÓTIN

### 1.1 Skilgreiningin eins og hún stóð (orðrétt úr skrifleiðinni)

```python
# precompute/cc143_prior.py:179  (fyrir cc152)
own["prior_series_thin_flag"] = own.prior_serie_n_pairs.fillna(0) < SERIES_THIN_N
```

`build_comps_v2.py` ber **ekkert** þynnkuflagg — grep finnur það aðeins í
`cc143_prior.py`. Það er cc143-viðbót og lifir á einum stað.

Hvaðan `prior_serie_n_pairs` kemur — orðrétt:

```python
# precompute/cc143_prior.py:126-132
def _serie_stats(g):
    li = g.sort_values("q").log_index_nominal.to_numpy(float)
    d = np.diff(li[~np.isnan(li)])
    return {"pairs": dict(zip(g["q"], g["n_pairs_in_period"])),
            "n": float(g.cell_n_pairs.iloc[0]),        # <-- prior_serie_n_pairs
            "sd": float(np.std(d, ddof=1)) if len(d) > 1 else np.nan}

# cc143_prior.py:155,162,165 — st er sótt á ÞAÐ LAG SEM RESOLVER-INN VALDI
f, level, aq, prov, _v = resolver.resolve_many(c, rg, pers, AT_Q)
st = serie_of(level, c, rg)
g["prior_serie_n_pairs"] = st["n"] if st else np.nan
```

### 1.2 Hliðið sem tryggir þröskuldinn (orðrétt)

```python
# precompute/index_resolution.py:124-133  (_pick_layer)
ok = s["val"].index[(s["val"].index <= at_q)
                    & (s["pairs"].reindex(s["val"].index).fillna(0) >= MIN_ANCHOR_PAIRS)
                    & s["raw_ok"].reindex(s["val"].index).fillna(False)]
if len(ok) == 0:
    continue                       # <-- sellan fellur niður um lag
aq = ok.max()
if (at_q - aq).n > STALE_Q:
    continue                       # <-- og hér líka
```

`MIN_ANCHOR_PAIRS = 10`, `STALE_Q = 2`.

### 1.3 MÆLINGIN — hliðið tryggir 500-þröskuldinn

Á cc143-artifactinu `D:\cc143\rs_live_kaupskra_v2.pkl` (3.116 raðir, 29 sellur):

| hópur | n sellur | `cell_n_pairs` min | max | þar af < 500 |
|---|---:|---:|---:|---:|
| **VALDAR** á `level='cell'` | **12** | **670** | 18.908 | **0 af 12** |
| **FELLDAR** niður um lag | **17** | 1 | **485** | **17 af 17** |

> **485 < 500 ≤ 670.** Þröskuldurinn liggur í **tómu bili** milli felldu og völdu
> sellnanna. Hvert einasta gildi sem flaggið gat lesið var, að byggingu, yfir
> þröskuldinum. **0/77.484 var ekki mæling — það var óhjákvæmileiki.**

Sama sést á lesnu töflunni sjálfri: lægsta `prior_serie_n_pairs` yfir allar 77.484
akkeraðar eignir er **670** (cell 670 · family 1.731 · national 56.387).

### 1.4 SD-hnykkjan sem 500 var valið úr — hún stendur, en á HINUM ásnum

cc143-athugasemdin fullyrti `n < 500 → SD 0,13–0,56`. Endurmælt á artifactinu:

| dýptarbil | n seríur | SD-bil | miðgildi |
|---|---:|---|---:|
| 0–200 pör | 15 | 0,134–0,561 | 0,283 |
| 200–500 | 3 | 0,082–0,169 | 0,149 |
| 500–1.000 | 4 | 0,055–0,158 | 0,077 |
| 1.000–5.000 | 8 | 0,033–0,063 | 0,053 |
| 5.000–20.000 | 5 | 0,024–0,045 | 0,042 |
| 20.000+ | 2 | 0,021–0,023 | 0,022 |

**Mælingin var rétt.** `APT_ATTIC|Country` (71 pör) ber SD 0,561, `SUMMERHOUSE|Capital_sub`
(85) 0,417, `APT_UNAPPROVED|RVK_core` (73) 0,283 — allt sellur með <500 pör.

**En það eru nákvæmlega þær 17 sellur sem falla niður um lag.** SD-ferillinn var
mældur á sellu-seríunum **FYRIR fall**; þröskuldurinn var svo borinn á seríuna **EFTIR
fall**. Mælingin og beitingin lágu á sitt hvorri kornastærðinni.

### 1.5 SVAR VIÐ SPURNINGUNNI

Ekki (a) óvíraður — línan keyrir og skilar `False` á öllum 77.484 röðum.
Ekki (c) skilgreiningin dauð í merkingu — SD-hnykkurinn er raunverulegur og mældur.
**(b) borinn á rangan ás** — og nákvæmlega í þriðja sinn sama mynstrið:
`MIN_ANCHOR_PAIRS` tryggði akkerisfjórðunginn (cc139), cc143 færði flaggið upp á
seríudýpt — **en las hana áfram niðri fyrir sama hlið.**

### 1.6 RÓTARFIXIÐ

Ásinn sem hliðið les **ekki** er dýpt **eigin sellu eignarinnar**, óháð því hvaða lag
akkerið endaði á.

```python
# cc143_prior.py:162-171  (NÝTT)
leaf = series.get(("cell", c, rg))
g["prior_leaf_n_pairs"] = leaf["n"] if leaf else np.nan

# cc143_prior.py:190  (NÝTT — full rót-athugasemd í kóðanum sjálfum)
own["prior_series_thin_flag"] = own.prior_leaf_n_pairs.fillna(0) < SERIES_THIN_N
```

`SCRIPT_VERSION` → `cc152_prior_2026-08-13`. `SERIES_THIN_N` **óbreytt í 500** — hnykkurinn
sem það var valið úr stendur (§1.4). `prior_serie_n_pairs` **óbreytt að merkingu** (dýpt
seríunnar sem raunverulega var notuð) svo ekkert annað hreyfist.

### 1.7 STAGING + PARITY

Keyrt með **sömu rökum og lifandi flippið** (`--now 2026-08-12`, `AT_Q 2026Q3`, sama
artifact og family-map) → `D:\cc152\prior_fix.{csv,parquet}`, 77.484 raðir.

**Parity gegn lifandi `valuation_tiers`** (`01g_parity.txt`):

| dálkur | ósamræmi | staða |
|---|---:|---|
| `prior_date` · `prior_price_kr` · `prior_adj_kr` · `prior_idx_factor` · `prior_idx_level` | 0 | PASS |
| `prior_anchor_q` · `prior_anchor_pairs` · `prior_serie_n_pairs` · `prior_serie_sd_dlog` | 0 | PASS |
| `prior_age_years` · `prior_suspect` · `prior_old_anchor_flag` | 0 | PASS |
| `prior_anchor_lag_q` · `prior_anchor_stale_flag` · `prior_level_fallback_flag` | 0 | PASS |
| **`prior_series_thin_flag`** | **2.966** | MÁ BREYTAST |

Raðamengi eins (77.484/77.484, 0 hvorum megin). **15 af 15 öðrum dálkum bæti-identískir.**

**Teljari á breyttum röðum gegn vænting** (mæld **fyrir** fix í `01e_vaenting.txt`):

| | teljari | tíðni af akkeruðum |
|---|---:|---:|
| áður `true` | 0 | 0,00 % |
| **eftir `true`** | **2.966** | **3,83 %** |
| `false → true` | 2.966 | |
| `true → false` | **0** | |
| **vænting mæld fyrirfram** | **2.966 / 3,83 %** | **STENDUR** |

Ásinn staðfestur á röðunum sjálfum: hámark `leaf_n` á kviknuðum röðum **485**, lágmark á
slökktum **670**, 8 raðir bera `NaN` (sella ekki til í artifactinu → telst þunn).

**Hvar logar það** — einhalla eftir gagnagæðum, öfugt við K0:

| flokkur | teljari | nefnari | tíðni | | þrep | teljari | nefnari | tíðni |
|---|---:|---:|---:|---|---|---:|---:|---:|
| A | 0 | 44.363 | **0,00 %** | | T1 | 2.008 | 70.563 | 2,85 % |
| B | 966 | 18.669 | 5,17 % | | T2 | 135 | 3.472 | 3,89 % |
| C | 1.674 | 11.505 | **14,55 %** | | T3 | 731 | 2.929 | 24,96 % |
| D | 326 | 2.947 | 11,06 % | | T5 | 56 | 140 | **40,00 %** |

### 1.8 TVENNT SEM BORÐIÐ VERÐUR AÐ SJÁ

**(i) Lagaða flaggið er bæti-identískt `prior_level_fallback_flag` á öllum 77.484 röðum.**
Krosstaflan er fullkomlega hornalæg (74.518 / 0 / 0 / 2.966). Á artifactinu í dag gildir
`eigin sella < 500 pör ⟺ sellan féll niður um lag`.

Þau eru **ekki sama skilgreining**: „fallback" segir *hvaðan vísitalan kom*, „þunn" segir
*hve djúpt mitt eigið markaðsþrep er*. Samfallið er **aðstæðubundið, ekki byggingarlegt**
— ung sella með ≥10 pör í líðandi fjórðungi en <500 alls væri þunn án falls. Í dag er
það mengi tómt. Munurinn á þessu og gamla ástandinu er efnislegur: áður var flaggið
**ómögulegt**, nú er það **satt en tvítekið**.

**(ii) Þröskuldurinn 500 er ónæmur á bilinu (485, 670].** Hvert gildi þar gefur sömu
2.966 raðir. Talan gerir enga fínvinnu á núverandi artifacti.

---

## 2. KOSTADÓMUR MERKISINS — K8

### 2.1 Grunnurinn fyrst (skilyrði áður en dæmt er)

cc151 mældi alla kostina á `valuation_tiers.pred_mean_at_build_kr`, en `/eign` birtir
`v_current_predictions.real_pred_mean`. Merki sem segir „bilið er > 25 pp" verður að
reiknast á tölunni sem stendur á skjánum. Mælt á báðum grunnum:

**`real_pred_mean` og `pred_mean_at_build_kr` eru nákvæmlega eins á 77.484 af 77.484
akkeruðum röðum** (|Δ| p90 = 0,0000 %). Spurningin fellur niður; allar tíðnitölur cc151
standa óbreyttar á birta grunninum.

| kostur | teljari (build) | teljari (BIRT) | tíðni |
|---|---:|---:|---:|
| K0 `age > 8` | 27.877 | 27.877 | 35,98 % |
| K1 `age > 12` | 13.518 | 13.518 | 17,45 % |
| K6 `\|bil\| > 25 pp` | 6.316 | 6.316 | 8,15 % |
| K7 `age > 8` OG `\|bil\| > 25 pp` | 3.237 | 3.237 | 4,18 % |
| **K8 `age > 12` OG `\|bil\| > 25 pp`** | **1.957** | **1.957** | **2,53 %** |

### 2.2 DÓMURINN

Skilyrði (a): **K8 er aðalkostur ef tíðni hans liggur á 2–15 % akkeraðra.**

| | |
|---|---:|
| skilgreining | `prior_age_years > 12` **OG** `\|prior_adj_kr − real_pred_mean\| / real_pred_mean > 25 pp` |
| **teljari** | **1.957** |
| **nefnari (akkeraðar eignir — kortið birtist ekki án akkeris)** | **77.484** |
| **tíðni** | **2,53 %** |
| á öllum 167.503 röðum `valuation_tiers` | 1,17 % |

**2,00 % ≤ 2,53 % ≤ 15,00 % → K8 stenst. VALINN KOSTUR: K8.** Skilyrði (b) og (c) falla
ekki til.

### 2.3 Hvers vegna K8 er raunverulegt merki en K0 ekki

| | K0 (lifandi í dag) | **K8 (valinn)** |
|---|---:|---:|
| tíðni | 35,98 % | **2,53 %** |
| miðgildi \|bil\| innan | 8,00 pp | **36,15 pp** (gegn 6,40 utan) |
| miðaldur akkeris innan | 11,86 ár | **16,17 ár** (gegn 5,72 utan) |
| tíðni á flokki A (bestu gögnin) | 34,00 % | **1,05 %** |
| tíðni á flokki D | 34,88 % | **11,23 %** |
| tíðni á T5 | 48,57 % | **20,00 %** |
| hlutur flöggunar á flokki A | **54,11 %** | 23,86 % |

K0 span A–D var 5,11 pp og ekki einhalla. **K8 er einhalla A → D (1,05 → 11,23 %)** og
vex í þrepi (T1 1,93 % → T5 20,00 %). Merkið logar þar sem gögnin eru rýrust.

### 2.4 25 pp — BÓKAÐ BERUM ORÐUM

> **25 pp er VALIÐ SÝNIGILDI, ekki mældur hnykkur.** cc151 §4 bókaði það þannig og cc152
> hefur **ekki** mælt hnykk á þeim ási. Ekkert í mælingunum staðfestir að 25 sé betri
> staður en 20 eða 30. Aldursþátturinn (`> 12 ár`) hvílir hins vegar á mældri brekku
> (cc151 §3.4: hlutfall > 25 pp fer 6,59 % → 8,37 % → **12,43 %** við 12–15 ár).
>
> **Endurskoðunarskilyrði:** 25 pp skal endurmælt að hnykk þegar annaðhvort gerist —
> (1) yield-akkeraða leigan hreyfir akkerisbilin, eða (2) næsta líkanaumferð er skoruð.
> Þar til er talan skreyting á þröskuldi, ekki niðurstaða.

### 2.5 Formerkið — textinn má ekki gefa átt

Innan K8: akkerið liggur **yfir** matinu á 1.015 eignum (51,87 %) og **undir** á 942
(48,13 %). Nánast jafnt. Textinn segir því að **bilið sé stórt**, ekki í hvora áttina
það hallar.

---

## 3. STAÐA LIÐAR 3 — FORSENDAN ER RÖNG (V2-TENGINGIN ER ÞEGAR LIFANDI)

cc151 §5 bókaði að `/eign` læsi `comps_index` (gömlu) og `predictions_iter3v2`, og að
hvorki `valuation_tiers` né `comps_index_v2` væri lesið af nokkrum framendafleti.
**Sú talning var gerð á `app/eign/[fastnum]/page.js` — í FROSNA app-repóinu**
(`D:\verdmat-is\app`, millisíðan á `verdmat-is.vercel.app`).

**Lifandi vefurinn er `www.verdmat.ai` úr `D:\verdmat-is\verdmat-ai`**, og þar er
`/eign/[fastnum]/page.tsx` (34 línur) → `components/eign/EignSidaEfni.tsx` →
`lib/eign-queries.js`. Grep á öllu því repói:

| tafla | staða á lifandi fleti |
|---|---|
| `v_current_predictions` | LESIN (`lib/eign-queries.js:194`) |
| **`valuation_tiers`** | **LESIN** (`lib/eign-queries.js:202`) |
| **`comps_index_v2`** | **LESIN**, `set_role='comp'` hörð sía (`:217`) |
| **`comps_t5_basis`** | **LESIN** (`:670`) |
| **`comps_index` (gamla)** | **ENGIN TILVÍSUN** — bönnuð í haus skrárinnar |
| **`predictions_iter3v2`** | **ENGIN TILVÍSUN** |

Skráin bókar bannið sjálf:

```js
// lib/eign-queries.js:2-4
// v_current_predictions (mat/bil/flokkur), valuation_tiers (þrep/prior/
// flögg), comps_index_v2 (comps, set_role-sía HÖRÐ), comps_t5_basis (T5).
// Gamla comps_index-taflan er BÖNNUÐ hér (sjá README, flip-brot varúð).
```

> **„V2 eingöngu" er þegar ástand á lifandi fletinum, ekki stefna.** Það var klárað í
> Skref 2 þann 2026-07-05. Liður 3 hefur því **enga tengingarvinnu** — hann hefur
> merkjavinnu eina.

### 3.1 En það gerir merkjavinnuna brýnni, ekki minni

`components/eign/Akkeri.tsx` **birtir K0 í dag, lifandi, sem pillu**:

```tsx
{tiers.prior_old_anchor_flag && (
  <span className="vm-flagg-pilla">eldri en {AKKERI_ALDURSMORK_AR} ára</span>
)}
```

Sá borði logar á **35,98 % akkeraðra eigna**, oftast á flokki A, og cc151 sýndi að hann
aðgreinir ekkert (AUC 0,500 innan sellu). **Hann er nú þegar veggfóður fyrir framan
notendur.** K8 kemur því ekki ofan á auðan flöt — hann **leysir K0 af**.

`lib/eign-queries.js:202` sækir í dag aðeins `prior_old_anchor_flag` og `prior_suspect`
af flöggunum fimm; `prior_series_thin_flag`, `prior_anchor_stale_flag` og
`prior_level_fallback_flag` eru **ekki í `select`-listanum**.

### 3.2 Snertiflötur við BANN-listann — hreinn

`Akkeri` er rendrað í `EignSidaEfni.tsx:252`, inni í **else-grein** `{erLeiga ? … : …}`
(lína 176). `/leiguverd/[fastnum]` rendrar sama komponent með `ham="leiga"` og fer í
**hina greinina** — Akkeri-kortið birtist þar **ekki**. Breyting á `Akkeri.tsx` snertir
því engan leigu-flöt.

---

## 4. HVAÐ ER GERT OG HVAÐ EKKI

**Gert (allt read-only nema staging á disk):**

1. `predictions_iter3v2` fullmæld — tafla, frosin 2026-04-01, 100 % ósamhljóða vélinni,
   **enginn notendaflötur les hana**. GO.
2. Rót þynnkuflaggsins sönnuð með tölum: 485 < 500 ≤ 670, hliðið tryggði þröskuldinn.
3. Rótarfix skrifað í `cc143_prior.py` (ás færður á eigin sellu), staging keyrt,
   **parity PASS á 15/15 öðrum dálkum**, teljari 2.966 stendur við fyrirfram mælda
   vænting.
4. K8 dæmdur valinn kostur — 1.957 / 77.484 = 2,53 %, innan 2–15 %.
5. Forsenda liðar 3 leiðrétt og mæld.

**Ekki gert:**

* **Ekkert skrifað í DB.** Flippið á `prior_series_thin_flag` bíður go (HALT A).
* Framendi ósnertur — engin lína í `verdmat-ai` breytt.
* 25 pp ómælt að hnykk (§2.4).
* `prior_leaf_n_pairs` er í staging-CSV en **ekki** lagt til í `valuation_tiers` — það
  krefðist migration og verkbeiðnin bókar „aðeins flaggið má breytast". Tillaga í §6.
* `predictions_rent*` / `valuation_tiers_rent*` / leigu-fletir ósnertir. Engin
  Haiku-köll. Sölu-spáin sjálf ósnert.

---

## 5. ÁKVÖRÐUNARFLÖTUR — HALT A

### Á1 — flipp á `prior_series_thin_flag` (2.966 raðir)

Staging er grænt og teljarinn stendur. Flippið yrði `UPDATE … WHERE flag IS DISTINCT
FROM` innan einnar txn með checksum-hliði á hina dálkana
(sbr. [[feedback_truncate_insert_endurhledur_alla_dalka]]).

**Vandinn sem borðið verður að taka afstöðu til:** lagaða flaggið er bæti-identískt
`prior_level_fallback_flag` (§1.8-i).

* **A1a — FLIPPA** (tillaga mín). Dálkurinn hættir að vera ómögulegur og verður satt
  mælitæki; samfallið við fallback er aðstæðubundið og getur rofnað. Kostnaður: núll á
  öðrum dálkum, sannað.
* **A1b — LEGGJA DÁLKINN NIÐUR** og nota `prior_level_fallback_flag` á fletinum.
  Hreinni skema, en hendir mælitæki sem verður sjálfstætt um leið og ein ung sella
  kviknar.

### Á2 — umfang liðar 3 eftir leiðréttinguna

Tengingarvinnan er þegar til. Það sem stendur eftir:

1. Víkka `select` í `lib/eign-queries.js:202` með `prior_series_thin_flag`,
   `prior_anchor_stale_flag`, `prior_level_fallback_flag` (+ `prior_adj_kr`,
   `prior_age_years` eru þegar sótt).
2. **Taka K0-pilluna „eldri en 8 ára" út** úr `Akkeri.tsx` og setja K8-merkið í staðinn.
3. Textinn hógvær, hlutlaus, engin tala án mælingar að baki, engin átt gefin (§2.5).

**Spurningin sem ég ræð ekki:** á K0-pillan að hverfa alveg, eða standa áfram sem hrein
staðreyndarlína („fyrri sala er 14 ára") án hógværðarmerkingar? Þær eru ólíkir hlutir —
aldur akkeris er staðreynd sem á heima á kortinu; **hógværðarmerki** á hann er það sem
cc151 formælti.

---

## 6. TILLÖGUR SEM ÞESSI LOTA GERIR EKKI

1. **`predictions_iter3v2` er `anon`-læs.** 110.316 fjögurra mánaða gamlar spár eru
   sækjanlegar um PostgREST án auðkenningar. Hún þjónar `?mode=debug` á frosnu síðunni
   einni. Tillaga: `REVOKE SELECT … FROM anon, authenticated` (debug-flöturinn notar
   sama anon-lykil, svo það slekkur á honum — sem er líklega rétt).
2. **`prior_leaf_n_pairs` inn í `valuation_tiers`** svo rökin séu endurskoðanleg á
   röðinni sjálfri (sbr. [[feedback_flagg_a_throskuldi_sem_hlid_tryggir]]). Krefst
   migration — utan heimildar þessarar lotu.
3. **Hnykkmæling á 25 pp** áður en talan festist í UI-texta (§2.4).

**HALT A — bíð go á Á1 (flipp) og afstöðu til Á2 (umfang liðar 3).**

---

# VIÐAUKI — FRAMKVÆMDIN (go borðsins 2026-08-13)

## A1 · FLIPP Á `prior_series_thin_flag` — PASS

**Undanfari, í réttri röð.** Rollback-SQL og snapshot skrifuð **fyrir** hvert
skrif (`03_prep.txt`):

* `D:\cc152\rollback_cc152_flagg.sql` — UPDATE úr snapshot, með **báðum**
  checksum-hliðum inni í `do`-blokk (fall → `raise exception` → rollback)
* `D:\cc152\rollback_cc152_iter3v2_acl.sql` — GRANT + policy endurreist, með
  `relacl` fyrir-stöðunni límdri orðrétt í hausinn
* `public.valuation_tiers_thinflag_pre_cc152` — 167.503 raðir, PK á `fastnum`,
  RLS on, engin policy; ósamræmi gegn lifandi töflu **0**
* `D:\cc152\prior_snapshot_pre_cc152.parquet`

**Checksums fyrir flipp:** `CHK_ADRIR15 = dd39a15d601a2fb2fcc9cdfabd410f96` ·
`CHK_FLAGG = 414bb097f5462ea4224a59c647af1e1e`.

**Flippið** (`04_flipp.txt`) — `UPDATE` á einum dálki úr temp-töflu, `set
transaction read write` fyrsta stæðan, öll hlið **innan** txn:

| hlið | mælt | vænting | |
|---|---:|---:|---|
| G1 raðamengi lindar ↔ akkeraðar raðir | 0 / 0 vantandi | 0 / 0 | PASS |
| G2 `CHK_ADRIR15` **eftir** skrif | `dd39a15d…f96` | óbreytt | PASS |
| G3 flaggið | 0 → **2.966** | 0 → 2.966 | PASS |
| G4 `true → false` | **0** | 0 | PASS |
| G5 raðafjöldi `valuation_tiers` | 167.503 | 167.503 | PASS |
| G6 akkeraðar eignir | 77.484 | 77.484 | PASS |
| G7 raðir án akkeris m/ ekki-NULL flagg | 0 | 0 | PASS |

`UPDATE` snerti nákvæmlega **2.966** raðir. **Postverify í sérstakri read-only
session** endurmældi raðafjölda, akkeraðar, teljara og `CHK_ADRIR15` — allt PASS.

**Tíðni eftir flipp, m/ nefnara** (bókun):

| flokkur | teljari | nefnari | tíðni | | þrep | teljari | nefnari | tíðni |
|---|---:|---:|---:|---|---|---:|---:|---:|
| A | 0 | 44.363 | 0,00 % | | T1 | 2.008 | 70.563 | 2,85 % |
| B | 966 | 18.669 | 5,17 % | | T2 | 135 | 3.472 | 3,89 % |
| C | 1.674 | 11.505 | 14,55 % | | T3 | 731 | 2.929 | 24,96 % |
| D | 326 | 2.947 | 11,06 % | | T4 | 36 | 380 | 9,47 % |
| | | | | | T5 | 56 | 140 | 40,00 % |

Vöktunarliðurinn (bæti-samsemd við `prior_level_fallback_flag`) er bókaður í
DECISIONS §5D-12 §3 og var mældur inni í flippinu sjálfu sem
`thin & ekki fallback = 0` — skráður sem **vöktun, ekki hlið**.

## A1b · `predictions_iter3v2` LOKUÐ FYRIR ANON — PASS

`05_revoke.txt`. Ein txn: `drop policy public_read` · `revoke select from anon` ·
`revoke select from authenticated` · `enable row level security` (idempotent),
með hliði innan txn á RLS, policy-fjölda og `relacl`.

| | fyrir | eftir |
|---|---|---|
| `relacl` | `{postgres=…,service_role=…,anon=r/postgres,authenticated=r/postgres}` | `{postgres=…,service_role=…}` |
| policies | `public_read` (r, {authenticated,anon}) | **engar** |
| `relrowsecurity` | true | true |

**Mótpróf:**

| próf | niðurstaða |
|---|---|
| `set role anon` → `select count(*)` | **42501 permission denied** |
| `set role authenticated` → sama | **42501 permission denied** |
| sem eigandi | 110.316 — **taflan stendur, ekki droppuð** |
| PostgREST anon `/rest/v1/predictions_iter3v2` | **HTTP 401**, `{"code":"42501"}` |
| PostgREST anon `/rest/v1/v_current_predictions` | HTTP 200 (viðmið) |
| PostgREST anon `valuation_tiers?prior_series_thin_flag=is.true` | HTTP 200, flaggið les rétt |
| www.verdmat.ai `/eign/{2018566,2058042,2000189,2061458}` | **4/4 HTTP 200**, akkeriskort til staðar, engin villa |

## 3 · FRAMENDINN (`verdmat-ai`, LIFANDI REPÓIÐ)

**Engin gagnasókn breyttist.** K8 les `prior_age_years` og `prior_adj_kr` úr
`valuation_tiers` og `real_pred_mean` úr `v_current_predictions` — allt þegar í
`select`-listanum (`lib/eign-queries.js:194,202`). Ekkert nýtt í flutningi.

**`config/skyringar.ts`** — `AKKERI_ALDURSMORK_AR` 8 → **12** (mælda brekkan),
nýtt `AKKERI_BILSMORK_PP = 25` með 25 pp-bókuninni og endurskoðunarskilyrðinu
orðréttum í kóðanum, og **`veikurAkkerisStudningur()`** — ein skilgreining á K8
fyrir alla fleti. Skilar `false` þegar aldur, akkeri eða mat vantar: merkið
logar aldrei á ómældri röð.

**`components/eign/Akkeri.tsx`** — K0-pillan „eldri en 8 ára" **fjarlægð**.
Aldurinn kominn sem staðreyndarlína í línublokkina („Aldur fyrri sölu · 18 ár"),
engin pilla, enginn viðvörunarlitur, engin fyrirvara-orðun. K8-textinn bætist
neðan við innan/utan-setninguna, stefnulaus.

**`lib/agent-tools.js`** — `gamalt_akkeri: prior_old_anchor_flag` **vék** fyrir
`veikur_studningur`, lesið úr **sama falli** og kortið. Þetta var ekki valfrjálst:
FEST REGLA (forskrift A) í haus skrárinnar bókar að hver tala sem agentinn ber
fram komi úr sama deterministic kalli og síðan — hefði K0 staðið þar hefði
agentinn sagt „gamalt akkeri" um þriðju hverja eign eftir að kortið hætti því.
`aldur_ara` stendur óbreytt sem hrá staðreynd. `erT5 || fjoleining` kæfa merkið
af sömu ástæðu og þau kæfa `verdmat`: það ber samanburð við mat sem sá flötur
neitar að nefna.

**Snertiflötur við BANN-listann — hreinn.** `Akkeri` rendrast í else-grein
`{erLeiga ? … : erT5 ? … : (…)}` (`EignSidaEfni.tsx:176,190`): `/leiguverd` fer í
fyrstu greinina og T5 í aðra — akkeriskortið birtist á hvorugum. Engin
leigu-skrá snert.

### Diff-yfirlit

| skrá | eðli breytingar |
|---|---|
| `config/skyringar.ts` | aldursmörk 8→12 · `AKKERI_BILSMORK_PP` · `veikurAkkerisStudningur()` · bókun 25 pp |
| `components/eign/Akkeri.tsx` | K0-pilla → staðreyndarlína · K8-merki · stefnulaus texti |
| `lib/agent-tools.js` | `gamalt_akkeri` → `veikur_studningur` úr sama falli · T5/fjöleiningar-kæfing |

`npx tsc --noEmit` hreint · `next build` grænt (18/18 síður).

## RAUNPRÓFUN (localhost á `next build`-útgáfunni, fyrir push)

Eignirnar valdar úr `06_k8_eignir.csv` — sú skrá ber **1.957 raðir og stendur því
við teljarann** sem dæmdur var.

| fastnum | heimilisfang | þrep/flokkur | aldur | bil | akkeriskort | aldurslína | **K8-merki** | K0-leif |
|---|---|---|---:|---:|---|---|---|---|
| 2000473 | Vesturgata 28 | T1/B | 18,32 ár | 52,33 pp | já | „18 ár" | **JÁ** | 0 |
| 2000506 | Tryggvagata 4 | T1/A | 18,30 ár | 30,27 pp | já | „18 ár" | **JÁ** | 0 |
| **2018566** | **Skipasund 35** (viðmið) | T1/B | 0,96 ár | 13,54 pp | já | „innan við ár" | nei | 0 |
| 2058042 | — (þynnkuflagg **true**) | — | 2 ár | — | já | „2 ár" | nei | 0 |
| 2005255 | Laugavegur 71 | **T5** | — | — | **ekkert kort** (T5-grein) | — | nei | 0 |

**Strengurinn „eldri en" finnst hvergi á neinni síðu — 0/5.** Og 2058042 sýnir
að merkið les **ekki** lagaða þynnkuflaggið: sú eign ber `thin_flag = true` en
ekkert merki, eins og borðið ákvað.

Rendraður texti, orðréttur af skjá (`m_2000473.html`):

> Akkeri — fyrri sala · Þinglýst sala · apríl 2008 · 6,5 M kr · Framreiknað til
> dagsins · 18,4 M kr · **Aldur fyrri sölu · 18 ár** · Framreiknaða akkerið er
> **utan** 80% vissubilsins. · **Fyrri salan er meira en 12 ára og framreiknað
> verð hennar liggur langt frá matinu. Akkerið styður matið því veikt hér.**

og viðmiðið (`m_2018566.html`):

> … Framreiknað til dagsins · 147,4 M kr · **Aldur fyrri sölu · innan við ár** ·
> Framreiknaða akkerið er **innan** 80% vissubilsins.

**Textinn er stefnulaus:** „liggur langt frá matinu", aldrei „yfir" eða „undir" —
rétt, því formerkið skiptist 51,87 / 48,13 innan K8. **25 pp stendur hvergi í
texta**, aðeins mældu aldursmörkin 12.

**Eitt lagað í prófuninni:** `Math.floor(0,96) = 0` gaf „Aldur fyrri sölu · 0 ár"
á Skipasundi 35 — satt en les rangt. Orðast nú „innan við ár" undir einu ári
(p05 aldurs er 0,60 ár, svo tilfellin eru raunveruleg). Endurbyggt og
endurprófað.

**Þrep 5 — athugasemd:** akkeriskortið rendrast **alls ekki** á T5 (eigin grein í
`EignSidaEfni.tsx:190`). T5-eignin er því próf á að merkið **leki ekki** þangað,
ekki próf á merkinu sjálfu. Það er fyrirliggjandi hönnun (T5 tölulaus), ekki
breyting þessarar lotu.

---

**HALT B — bíð go á push = deploy.** Raunprófun á production endurtekst eftir
deploy á sömu fimm eignum.
