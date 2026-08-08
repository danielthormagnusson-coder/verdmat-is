# cc116 — ENDURREIKNINGUR 953 RAÐANNA

**Dags:** 2026-08-07 · **Umfang:** liður (ii) af PLANNING_BACKLOG viðauka cc112, V2-fordæmi
cc94 B2. Liður (i) (endurtenging) var forsenda og er lokið í cc113 (`ed2d6d5`).
**Engin pipeline-breyting, hliðinu ekki breytt, engin Haiku-köll, engin önnur röð snert.**

## 0. Vandinn

953 raðir í `scraper.listing_valuations` báru `model_version = 'iter4_final_v1'` en voru
frystar **eftir** flipp-committið `2026-08-06T12:24:26Z`, þ.e. úr 154-eiginleika heiminum
sem framleiðslan var þá farin frá. Þær voru einu raðirnar í töflunni sem voru rangar miðað
við lifandi framleiðslu. Eldri raðir (fyrir flipp) voru frystar þegar `iter4_final_v1` VAR
framleiðslan, eru sögulega réttar á sínum tíma og eru **ekki snertar**.

## 1. AFMÖRKUN (mæld fyrst, read-only)

| mæling | gildi | krafa |
|---|---:|---:|
| `iter4_final_v1` ∧ `valued_at >= flip` | **953** | 953 ✔ |
| ↳ einkvæm `source_listing_id` | 953 | — |
| ↳ einkvæm `fastnum` | 507 | — |
| ↳ `valued_at` span | 2026-08-07 00:41:11Z … 04:13:25Z | allar ≥ flipp ✔ |
| `iter4_final_v1` ∧ `valued_at < flip` (sögulegar) | 20.642 | ósnertar |
| 20.642 + 953 == `iter4_final_v1` alls (21.595) | TRUE | ✔ |
| raðir með `valued_at IS NULL` | 0 | engin röð fellur milli skilgreininga ✔ |
| tvítök á `source_listing_id` innan mengisins | 0 | ✔ |
| mengis-`source_listing_id` sem bar ÞEGAR nýja stimpilinn | **0** | ⇒ insert-first óhætt ✔ |
| raðir mengisins með útdrátt til í `listing_extractions` | **953 / 953** | engin Haiku-köll ✔ |
| mengis-raðir sem uppfylla skilyrði lifandi biðraðar | **953 / 953** | allt mengið endurreiknanlegt ✔ |
| `lysing_hash` frystu raðarinnar vs lifandi biðröð | **953 eins / 0 rek** | sami útdráttartexti ✔ |

**Sögulega bandið er varið af tvennu, ekki einu:** afmörkunin er `>= flipp`, og eyðingin
neðar er á **`valuation_id`-lista**, ekki á skilyrði. Skilyrði sem misritast eyðir öðru
mengi en það sem var mælt; auðkennalisti getur það ekki.

## 2. VARÐVEISLA FYRIR AÐGERÐ

Full röð, allir níu dálkar, allar 953 — ekki úrtak. **Utan git** (raðgögn úr prod-DB fara
aldrei í git):

| skrá | raðir | sha256[:16] | bæti |
|---|---:|---|---:|
| `D:\_audit\cc116_endurreikningur\listing_valuations_pre_cc116_20260807T2100Z.csv` | **953** | `576c7d2e6d319d36` | 102.606 |
| `D:\_audit\cc116_endurreikningur\listing_valuations_pre_cc116_20260807T2100Z.jsonl` | **953** | `d73e4e419ea7225f` | 267.346 |

Rowcount er **talinn af disknum eftir skrif**, ekki af því sem ætlað var að skrifa
(953 == 953 == 953). Grunnlínusummur: `expected_base` 79.948.413.919 ·
`expected_extraction` 80.902.159.922.

Ólíkt cc94 B2 var **engin afritstafla búin til í DB** — diskur var það sem beðið var um, og
`_pre_cc94b`/`_pre_cc94b2` bíða þegar dropps á backlog. Ný afritstafla hefði bætt þriðju
töflunni í þann hala.

## 3. ENDURREIKNINGURINN

Skrifta: `D:\_audit\cc116_endurreikningur\cc116_endurreikningur.py` (`--write` þarf; án hans
hrein mæling). **Leiðin er sama leið og cc113-raunprófunin fór — engin afrit af
pipeline-rökum:**

```
E.load_serving_models(ro)                 # bindur MODEL_VERSION við artifact-manifest á DISKI
E.assert_write_world_matches_live(ro)     # cc112-hliðið, óbreytt
E.fetch_extracted_listings_to_value(ro)   # ÓBREYTT fall, öll biðröðin (21.372), síuð í Python
E.value_listings(rw, models, rows)        # ber hliðið aftur sem fyrstu stæðu, skrifar
```

Mengið var **síað í Python út úr óbreyttri biðröð**, ekki sótt með afritaðri SQL-fyrirspurn
(cc94 B2 afritaði fyrirspurnina). Afrit af fyrirspurn getur rekið frá nóttinni; sama fall
getur það ekki. Sjá [[feedback-hlid-a-maelingu-en-ekki-a-skrifleid]].

**Hliðið hleypti í gegn af réttri ástæðu**, ekki af því það var þaggað:
```
model_version: 'iter4r_20260805_reglaR_strukt' (pipeline_config.model_version)
manifest: train_end=2026-01-15 data_end=2026-07-31 n_features=156
hms-lind sha OK (16d78e39d57cfcad) · feature count: 156
cpi_factor @ 2026-07: 1.0130 (freeze[2026-09/2026-07] = 1.013006)
útgáfuhlið: adapter 'iter4r_...' == lifandi 'iter4r_...' — skrif heimiluð
```

### Röðin: INSERT-FIRST, ekki DELETE-FIRST — meðvitað frávik frá cc94 B2

cc94 varð að eyða fyrst því stimpillinn var **sá sami** og einkvæmnislykillinn
`(source_listing_id, model_version)` hefði rekist á. Hér ber nýja röðin **annan** stimpil,
skörunin var mæld **0**, svo insert-first er bæði löglegt og strangt öruggara:

- **SKREF A** — 953 nýjar raðir skrifaðar undir `iter4r_20260805_reglaR_strukt`,
  staðfest 953/953 í töflu. Hefði það brugðist væri engu eytt.
- **SKREF B** — 953 gömlu raðirnar eyddar á `valuation_id = ANY(...)`, `rowcount = 953`.

Ekkert augnablik er til þar sem auglýsing mengisins á ekkert verðmat. Glugginn þar sem hún
átti **tvö** (sitt undir hvorum stimpli) var sekúndubrot; `scraper.v_expected_vs_real` ber
`model_version` per röð og aggregerar ekki, og engin notendasíða les töfluna.

**Kostnaður: $0,00.** `anthropic` er hvergi flutt inn og enginn client smíðaður;
`scraper_data/extraction_cost_state.json` var lesin fyrir og eftir og er **bæti fyrir bæti
óbreytt** (2026-08-07 stendur í $1,7821 — cc113-raunprófunin, ekki þessi keyrsla).

## 4. SÖNNUN

Mæld af **sjálfstæðri read-only skriftu** (`cc116_sonnun.py`) sem les varðveisluskrána
**af diski** og ber gegn lifandi töflu — ekki af minni aðgerðarskriftunnar.

| `model_version` | fyrir | eftir |
|---|---:|---:|
| `iter4_final_v1` (alls) | 21.595 | **20.642** |
| ↳ þar af mengið (≥ flipp) | **953** | **0** |
| ↳ þar af sögulegar (< flipp) | 20.642 | **20.642** (ÓBREYTT) |
| `iter4r_20260805_reglaR_strukt` | 10 | **963** |
| **ALLS** | **21.605** | **21.605** (ÓBREYTT) |

- **Engin röð týnd:** 953 varðveittar `source_listing_id` → 953 raðir / 953 einkvæmar undir
  nýja stimplinum. 0 þeirra enn undir gamla stimplinum.
- **Sögulega bandið ósnert:** 20.642 raðir, `min(valued_at)` 2026-06-27 22:13:04Z,
  `max(valued_at)` 2026-08-06 09:20:26Z — óbreytt frá mælingu liðar 1.
- **cc113-raðirnar tíu ósnertar:** 10 raðir undir nýja stimplinum frá 07.08 11:50Z standa.
- **Nýju auðkennin:** `valuation_id` 21610–22562, `valued_at` 2026-08-07 23:39:33Z.
  Auðkennin breytast — óhjákvæmilegt við V2 og bókað; gömlu lifa í varðveisluskránni.
- **PARITY við lifandi framleiðslu:** `expected_base` nýju raðanna vs
  `public.predictions.real_pred_median`: **645/645 eins, max|Δ| = 0 kr.** 308 raðir
  (123 eignir) eiga ekkert `fastnum` í `predictions` og eru utan nefnarans — það er
  join-nefnari, ekki frávik.

### Stikkprufa (3 raðir, gamalt vs nýtt)

| `source_listing_id` | fastnum | id | base fyrir | base eftir | Δ base | ext fyrir | ext eftir | Δ ext |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| 1484008 | 2200016 | 20856→21610 | 62.682.201 | **67.303.212** | +4.621.011 (+7,37%) | 69.580.344 | **75.385.083** | +5.804.739 (+8,34%) |
| 1496905 | 2153416 | 20857→21611 | 30.754.990 | **31.119.200** | +364.210 (+1,18%) | 37.342.443 | **38.957.046** | +1.614.603 (+4,32%) |
| 1566394 | 2209957 | 20858→21612 | 81.867.233 | **83.221.405** | +1.354.172 (+1,65%) | 83.956.494 | **86.399.933** | +2.443.439 (+2,91%) |

## 5. FRÁVIKADREIFINGIN — hvað flippið hreyfði á þessum fleti

Þetta er ekki aukaafurð heldur mæling í sjálfu sér: 953 raðir sem voru skoraðar í báðum
heimum á **sama akkeri, sama útdráttartexta og sama degi** — hreinn munur á líkanaheimunum.

| | `expected_base` | `expected_extraction` |
|---|---:|---:|
| raðir | 953 | 953 |
| **óbreyttar** | **0** | **0** |
| miðgildi Δ | −441.244 kr (−0,615%) | −410.391 kr (−0,514%) |
| miðgildi \|Δ\| | 2.771.136 kr (**3,70%**) | 2.552.707 kr (**3,74%**) |
| p95 \|Δ\| | 22.181.188 kr (**25,72%**) | 26.034.672 kr (**28,71%**) |
| min / max Δ | −38.328.395 / +18.198.662 | −43.423.629 / +14.987.517 |
| upp / niður | 434 / 519 | 440 / 513 |
| **summa** | 79,95 → **77,99 ma.kr (−2,45%)** | 80,90 → **78,83 ma.kr (−2,56%)** |

**Engin einasta röð stóð í stað.** Miðgildið er lítið (−0,6%) en dreifingin er breið:
fjórða hver króna hreyfðist um meira en 25% á efstu 5%. Nýi heimurinn er ekki „gamli
heimurinn plús leiðrétting" — hann er annar heimur, sem er nákvæmlega það sem cc112-hliðið
hélt fram og cc113 sannreyndi á öðrum fleti.

### Lagskipt — regla R skýrir ekki dreifinguna

| hópur | raðir | eignir | miðgildi Δbase | miðgildi \|Δ\| | p95 \|Δ\| | max \|Δ\| |
|---|---:|---:|---:|---:|---:|---:|
| **endurflokkað af reglu R** | 179 | 107 | **+1,57%** | 2,39% | 12,11% | 15,96% |
| **óbreytt flokkun** | 774 | 400 | **−0,90%** | 4,02% | 27,68% | 37,95% |

Öfugt við það sem búast mátti við: endurflokkuðu eignirnar hreyfðust **minna og upp á við**,
óbreyttu flokkarnir meira og niður. Endurflokkunin er því **ekki** meginskýring frávikanna —
strúktúr-endurþjálfunin sjálf (156 eiginleikar + serving-lagið) er það.

### Halinn situr á `EXCLUDE`

| hópur | eignir | raðir | miðgildi Δ | miðgildi \|Δ\| | p95 \|Δ\| | max \|Δ\| |
|---|---:|---:|---:|---:|---:|---:|
| `canonical_code = EXCLUDE` | 47 | 67 | −3,57% | 4,86% | **33,76%** | **37,95%** |
| íbúðarhúsnæði | 460 | 886 | −0,40% | 3,60% | 25,46% | 31,39% |

Fimm stærstu frávikin eru öll á `EXCLUDE`-eignum (mest −37,95%). Það er í sjálfu sér
væntanlegt — `EXCLUDE` er utan taxonomíunnar sem líkanið er akkerað á — en það þýðir að
p95-talan í heildardreifingunni er dregin upp af flokki sem á minnstan rétt á að vera þar.
Mengið skiptist: `APT_FLOOR` 698 · `EXCLUDE` 67 · `SFH_DETACHED` 66 · `ROW_HOUSE` 59 ·
`SUMMERHOUSE` 33 · `SEMI_DETACHED` 19 · `APT_BASEMENT` 10 · `APT_ATTIC` 1.

## 6. FRÁVIK FRÁ FORSENDUM VERKBEIÐNINNAR (mæld, ekki gefin)

Verkbeiðnin bar töluna „**103 af 478 eignum (21,5%)**" úr cc110-morgunvaktinni. Endurmælt í
dag gegn `public.properties_canonical_pre_cc78` (R3-rollback-akkerið):

**107 af 507 eignum (21,1%).** Hlutfallið stenst; nefnarinn er annar. Rowcount-krafan (953)
stóðst nákvæmlega, svo þetta felldi ekki hliðið í lið 1 — en það er bókað hér svo tölurnar
tvær reki ekki áfram hlið við hlið. Sundurliðun endurflokkunarinnar:
`APT_STANDARD→APT_FLOOR` 75 · `APT_FLOOR→SFH_DETACHED` 15 · `APT_FLOOR→ROW_HOUSE` 9 ·
`APT_STANDARD→ROW_HOUSE` 6 · `APT_BASEMENT→SFH_DETACHED` 1 · `APT_STANDARD→SFH_DETACHED` 1.

## 7. ÓSNERT

- **20.642 sögulegar raðir** undir `iter4_final_v1` — mælt óbreyttar að fjölda og
  `valued_at`-bandi. Hvort þær eigi líka að endurreiknast er **ótekin ákvörðun** og stendur
  áfram á backlog (þær voru réttar á sínum tíma; endurreikningur þeirra væri ekki viðgerð
  heldur endursögn).
- **Pipeline, hliðið, nætur-keðjan** — ekkert breytt, ekkert committað í `scripts/`.
- **Biðröð nætur-keðjunnar** fór úr 21.372 í **20.419** (mengið er nú verðmetið undir
  lifandi stimpli). Þakið `EXTRACT_VALUE_LIMIT=2000` bítur áfram; ~10 nætur standa eftir.
  Nóttin 08.08 sér mengið ekki lengur.

## 8. SKRÁR

| skrá | hlutverk |
|---|---|
| `D:\_audit\cc116_endurreikningur\cc116_endurreikningur.py` | aðgerðin (`--write`) |
| `D:\_audit\cc116_endurreikningur\cc116_sonnun.py` | sjálfstæð sönnun, read-only |
| `…\listing_valuations_pre_cc116_20260807T2100Z.{csv,jsonl}` | varðveisla, 953 raðir |
| `…\nidurstada_20260807T233934Z.json` | rowcount fyrir/eftir + dreifing |
| `…\fyrir_eftir_rows_20260807T233934Z.jsonl` | 953 raðir, gamalt vs nýtt, per röð |

Aðgerðarskriftan er **idempotent af sjálfu sér**: önnur keyrsla með `--write` mældi mengið
0 og stöðvaði áður en nokkuð var snert (`HALT: mengið er ekki 953 raðir. Ekkert snert.`).
