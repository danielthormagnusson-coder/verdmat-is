# EXTRACTION-BACKFILL — FORKÖNNUN OG ÁKVÖRÐUNARBLAÐ (cc20)

**Dags:** 2026-07-18 · **Lota:** cc20 · **Staða:** HALT — bíður kostnaðar-go frá Danna
**Umfang lotu:** 100% read-only. Engin extraction-köll framkvæmd. Engin skrif í DB.
**Tilefni:** forsenda þess að ástands-/eigindaupplýsingar komist inn í líkanið sjálft
(iter5-samanburðarkeyrslan, PLANNING_BACKLOG úr cc12).

---

## 0. SAMANTEKT — þrennt sem breytir spurningunni

Forkönnunin svarar spurningunni sem var spurð, en þrjú atriði komu í ljós sem
verða að liggja fyrir áður en kostnaðar-go er tekið:

1. **Nefnarinn í verkefnislýsingunni var rangur.** Kafli 10 skilgreinir
   *skýrslu-nefnara*, ekki þjálfunarþýði. Réttur nefnari er **146.499 samningar**
   (§1).
2. **Kostnaður er ekki bindandi þröskuldur.** Fullur backfill á (b)-hópinn kostar
   **$210–867** eftir útfærslu (§3). Intro-verðlok 31.08 spara ~$100–200 í
   krónum talið — það er raunverulegt en veikt tímasetningarrök (§3.3).
3. **Bindandi þröskuldurinn er annars staðar.** Fullur backfill hækkar
   eigindaþekju þjálfunarþýðisins úr 23,8% í **39,7% — ekki hærra** (§2).
   60,3% þýðisins á engan auglýsingatexta og extraction getur ekki lagað það.

Og eitt til viðbótar sem er **stopp-atriði fyrir útfærsluna eins og hún var
tilgreind**: eigindalagið sem beðið var um að skrifa í nær ekki inn í líkanið (§4).

---

## 1. NEFNARI — leiðrétting

Verkefnislýsingin sagði „metanlegir samningar skv. skilgreiningu kafla 10".
Þau eru tvö aðskilin mengi:

| | Kafli 10 (skýrslu-nefnari) | Þjálfunarþýði líkansins |
|---|---|---|
| Grunnur | `public.sales_history` (Postgres) | `kaupskra.csv` → `training_data_v2.pkl` |
| Sía | kaupverð>0, `onothaefur=0`, `is_suspect_comparable=false` | 9-þrepa keðja (`build_training_data.py:166-228`) |
| Auka-hlið | — | skjalanúmer 1:1, flokkun `IN_MODEL`, landfræði-join, 20–1000 m², útlagasía |
| **N** | 609 íbúðasamningar í júní 2026 | **146.499 samningar** |

Heimild: `FASTEIGNASKYRSLA_2026-06_20260715T2358Z.md:144`;
`D:\rebuild_training_data_log_20260716.txt` (9-þrepa fallkeðja 229.783 → 146.499);
`iter4r_20260716_manifest.json` (`data_shape: [146499, 172]`).

Allar tölur hér eftir eru á **146.499-nefnaranum**.

---

## 2. UMFANG — a/b/c með nefnurum

Tengikeðjan sem ræður öllu:
`FAERSLUNUMER` → `pairs_v1.pkl` → `augl_id` → `lysing` → `lysing_hash` → extraction.

| | Flokkur | N | % |
|---|---|---:|---:|
| **(a)** | Þegar extractað | 34.842 | 23,8% |
| **(b)** | Texti til, óextractað | 23.310 | 15,9% |
| **(c)** | Engin pörun / enginn texti | 88.347 | 60,3% |
| | *þar af (b) m/ raunverulegum texta >0 stafir* | *22.875* | |

**Þakið á fullum backfill er 39,7% þekja.** (c)-hópurinn er ekki
extraction-vandamál heldur pörunar-/skröpunarvandamál: `pairs_v1.pkl` parar
aðeins 67.407 færslur alls, og 58.152 þeirra lenda í þjálfunarþýðinu.

### 2.1 Hvar batnar þekjan mest — canonical × svæði

Núverandi þekja (a) og hvað vantar, 6 stærstu götin:

| canonical | svæði | N | m/ext | vantar | þekja |
|---|---|---:|---:|---:|---:|
| APT_FLOOR | Capital_sub | 29.030 | 6.449 | 22.581 | 22,2% |
| APT_STANDARD | RVK_core | 26.674 | 5.455 | 21.219 | 20,5% |
| APT_FLOOR | RVK_core | 23.730 | 5.170 | 18.560 | 21,8% |
| APT_FLOOR | Country | 17.457 | 4.977 | 12.480 | 28,5% |
| APT_STANDARD | Capital_sub | 14.951 | 2.814 | 12.137 | 18,8% |
| APT_BASEMENT | RVK_core | 3.845 | 1.365 | 2.480 | 35,5% |

Þekjan er merkilega **flöt** (18,8–41,6%) — engin ein eignategund eða svæði er
kerfisbundið verr sett. Það þýðir að backfill bætir þekju nokkuð jafnt og býr
ekki til nýja bjagaða undirhópa, en það þýðir líka að **enginn markviss
hlutabackfill nær miklu meiru en flatur** (mótrök gegn því að byrja á einu
svæði).

### 2.2 Þekja eftir ári — rekið er í nýlegum gögnum

| ár | 2016 | 2018 | 2020 | 2022 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|
| þekja | 45,0% | 44,4% | 33,0% | 32,2% | 27,9% | 29,5% | **12,8%** |

Þetta er sjálfstætt vaktaratriði: þekjan **fellur** eftir því sem nær dregur,
og 2026 er á 12,8%. Ef eigindin fara inn í líkanið án þess að þetta sé lagað
verður featurið kerfisbundið þynnra á nýjustu gögnunum — þ.e. veikast þar sem
líkanið er mest notað.

---

## 3. KOSTNAÐUR

### 3.1 Mældur tokengrunnur (ekki áætlaður)

40 raunveruleg v2-köll í `eigindi_extraction_runs` gefa aðhvarf með R²=0,996:

```
input_tokens = 3.854 + 0,5334 × stafir      (R² = 0,996, n = 40)
output_tokens: meðaltal 1.294, miðgildi 1.228, bil 519–2.718
```

Tvennt sem þetta afhjúpar:
- **1,87 stafir/token** í íslenskum texta (mun óhagstæðara en enska ~4).
- **Fastur forskeyti = 3.854 tokens** (system-prompt + json-skema). Á
  miðgildistexta (b)-hópsins er það ~65% af innslættinum — endursent
  ócache-að í hverju einasta kalli. **Kerfi B cache-ar ekki; kerfi A gerir það.**

(b)-hópurinn: miðgildi 3.931 stafir, meðaltal 4.327, p90 5.845, alls 99,0 M stafir
→ 141,0 Mtok inn / 29,6 Mtok út.

### 3.2 Heildarkostnaður (b) = 22.875 köll

| Útfærsla | Intro (til 31.08) | Listaverð (frá 01.09) |
|---|---:|---:|
| sonnet-5 ber | **$578** (2,53¢) | **$867** (3,79¢) |
| sonnet-5 + prompt-cache | $419 (1,83¢) | $629 (2,75¢) |
| sonnet-5 + Batch API | $289 (1,26¢) | $433 (1,89¢) |
| **sonnet-5 + cache + batch** | **$210** (0,92¢) | **$314** (1,37¢) |
| haiku-4-5 (kerfi A, m/cache) | $162 | $162 |
| haiku-4-5 + batch | **$81** | **$81** |

cc5-forsendan (2–4,3¢/kall) **heldur** — ber sonnet-5 lendir á 2,53¢/3,79¢.
En hún á aðeins við um ócache-að, óbatchað on-demand-kall; hún er ekki rétt
forsenda fyrir lotukeyrslu.

### 3.3 Um tímasetningarrökin

Intro-verð rennur út **2026-08-31**; listaverð er +50% á báðum hliðum
(staðfest: $2/$10 → $3/$15 per Mtok). Í hlutfalli er það stórt, í krónum
**$104 (cache+batch) til $289 (ber)**. Það er of lítið til að réttlæta að
flýta keyrslu á kostnað §4-úrlausnarinnar. Ef backfill fer fram á annað borð
er þó ódýrara að gera það fyrir 31.08 — bara ekki að *forgangsraða* því þess vegna.

---

## 4. STOPP-ATRIÐI — eigindalagið nær ekki inn í líkanið

Verkefnislýsingin sagði „engin ný töfluhönnun — skrifast í sama eigindalag"
(þ.e. `public.property_attributes` + `eigindi_extraction_runs`, kerfi B).

**Það skilar sér ekki inn í iter5.** Staðfest:

- `D:\verdmat-is\precompute` (retrain-leiðslan) nefnir `property_attributes` **hvergi**.
- `build_training_data_v2.py` les eingöngu: `batch_extraction_unique.jsonl`,
  `pairs_v1.pkl`, `listings_text_v2.pkl`, `training_data_v1.pkl`.
- 16 extraction-featurin sem þegar eru í `training_data_v2.pkl`
  (`has_balcony_flag`, `extraction_success`, …) koma öll úr **kerfi A**.

Kerfin tvö eru aðskilin frá grunni:

| | Kerfi A (fæðir líkanið) | Kerfi B (eigindalagið) |
|---|---|---|
| Skema | v0.2.2, **108 reitir** | `SKEMA_UTGAFA=2`, **13 eigindi** |
| Módel | `claude-haiku-4-5` | `claude-sonnet-5` |
| Geymsla | `scraper.listing_extractions` (jsonb) | `property_attributes` (röð per eigind) |
| Idempotens | efnis-hash `md5(lysing)[:12]` | runs-tafla `(fastnum, augl_id, skema_utgafa)` |
| Prompt-cache | **já** (system + tool-skema) | **nei** |
| Mældur kostn. | 0,71¢ | 2,53–3,79¢ |
| Kemst í iter5 | **já** | **nei** |

Backfill í kerfi B krefst þess að ný samrunakóði verði skrifaður
(`property_attributes` → `FAERSLUNUMER` → training matrix). Það er ekki ný
tafla, en það er ný leiðsla — og það rekst á sama „engin ný hönnun"-skilyrðið,
bara á öðrum stað. Auk þess eru eigindin 13 í stað 108, þ.e. þrengra
featureset en cc12-eigindaeffektinn var mældur á.

**Þetta er ákvörðun sem Danni á að taka, ekki ég** — sjá valkosti í §6.

---

## 5. LOTUÁÆTLUN (á við hvora leið sem valin verður)

### 5.1 Aðferð
**Message Batches API**, ekki raðkeyrsla. Rök: mæld svörun on-demand er
11–38 sek/kall → 22.875 köll raðkeyrð = **6,6 sólarhringar**; með samhliðni 5
(eins og `gata_eigindi`) = 1,3 sólarhringar. Batch API skilar 50% afslætti og
flestar lotur klárast innan klukkustundar (þak 24 klst).

### 5.2 Lotustærðir
- `CHUNK_SIZE = 5.000` (sama og `batch_extract.py:97`, heldur undir 256 MB þakinu)
- 22.875 köll → **5 lotur**
- Áætlaður keyrslutími: 5 × ≤1–3 klst raðbundið, þ.e. **innan eins vinnudags**;
  versta tilfelli (24 klst/lota) = 5 sólarhringar
- Endurræsanleiki: `batch_state.json`-mynstrið er þegar til (`batch_extract.py`)

### 5.3 Idempotens
Fer eftir leið:

- **Kerfi A:** engin ný vinna. Efnis-hash `md5(lysing)[:12]` er PK og innsetning
  er `ON CONFLICT DO NOTHING`. Endurkeyrsla er sjálfkrafa örugg og
  endur-auglýsingar með sama texta deila einu extraction.
- **Kerfi B:** sama mynstur og on-demand — SELECT á
  `(fastnum, augl_id, skema_utgafa)` fyrir hvert kall.
  **Aðvörun:** runs-taflan hefur **enga unique-þvingun**; idempotens er
  eingöngu í forritskóða. Í lotukeyrslu með samhliðni er það kappaksturs-hætta
  sem on-demand-leiðin (eitt kall í einu) fékk aldrei á sig. Fyrir backfill
  þyrfti annaðhvort unique-index eða raðbundna forskoðun.

### 5.4 Girðingar sem þarf að taka afstöðu til
- `EIGINDI_DAGSTHAK` = 200 köll/dag → 114 dagar á (b)-hópinn. Backfill verður
  að fara framhjá þakinu; það má ekki gerast óvart í sömu kóðaleið og
  notendakvótinn.
- Kostnaðargirðing kerfis A (`--daily-cap-usd 10.0`, `PER_CALL_USD=0.0071`)
  þarf hækkun eða sérstillingu fyrir lotuna.

---

## 6. ÁKVÖRÐUNARLIÐIR — bíða go

| # | Ákvörðun | Valkostir | Mín ábending |
|---|---|---|---|
| **A1** | **Leið** | (i) kerfi A, haiku, 108 reitir, fæðir iter5 beint — $81–162 · (ii) kerfi B, sonnet, 13 eigindi + ný samrunaleiðsla — $210–867 · (iii) hvorugt núna | **(i)** — ódýrari, breiðari featureset, engin ný leiðsla, og er sannanlega sú leið sem cc12-eigindaeffektinn var mældur á |
| **A2** | **Umfang** | (i) allur (b) = 22.875 · (ii) aðeins 2020+ = ~15.900 · (iii) prufulota 2.000 fyrst | **(iii) → (i)** — prufulota staðfestir tokenlíkanið og idempotens áður en full lota fer af stað |
| **A3** | **Tímasetning** | (i) fyrir 31.08 (intro) · (ii) eftir override-lotu 20.–21.07 · (iii) með iter5-hringnum | **(ii)** — sparnaðurinn ($104–289) réttlætir ekki að trufla override-sameininguna sem hefur deadline 26.07 |
| **A4** | **(c)-hópurinn (60,3%)** | (i) sérlota um pörunarþekju · (ii) á backlog · (iii) sætta sig við 39,7% þak | **(i) á backlog** — þetta er stærri lyftistöng en backfillið sjálft en er annað verkefni |
| **A5** | **Prompt-cache í kerfi B** | lagfæra óháð backfill (fastur 3.854-token forskeyti) | **já** — 28% sparnaður á öllum on-demand-köllum framvegis, óháð A1 |

---

## 7. HVAÐ VAR EKKI GERT Í ÞESSARI LOTU

- **Engin extraction-köll.** Engin API-köll af neinu tagi.
- **Engin skrif** í Postgres, SQLite eða pickle-skrár. Allur DB-aðgangur um
  transaction-pooler (6543), sem er sjálfgefið read-only.
- **Ekkert committað eða pushað.**
- Ekki sannreynt: hvort 108-reita skema v0.2.2 keyri hreint á 2024–2026 textum
  (batch-keyrslan var á eldra safni) — ætti að vera hluti af prufulotu í A2(iii).
- Ekki mælt: hversu mikið af (c)-hópnum ætti texta í SQLite-söfnunum
  (~36.100 sölutextar á diski) sem `pairs_v1` nær ekki til. Það er inntak í A4.

---

## 8. HEIMILDIR

| Skrá | Hlutverk |
|---|---|
| `FASTEIGNASKYRSLA_2026-06_20260715T2358Z.md:144` | kafli 10, skýrslu-nefnari |
| `D:\build_training_data.py:166-228` | 9-þrepa þjálfunarsía |
| `D:\rebuild_training_data_log_20260716.txt` | fallkeðja 229.783 → 146.499 |
| `D:\build_training_data_v2.py` | samruni extraction → training matrix |
| `D:\pairs_v1.pkl` | augl_id ↔ faerslunumer pörun (67.407) |
| `D:\training_data_v2.pkl` | 146.499 × 170, 16 extraction-feature |
| `public.eigindi_extraction_runs` | 40 v2-köll = tokengrunnur §3.1 |
| `verdmat-ai\lib\eigindi-extraction.js` | kerfi B: prompt, skema v2, cache-leysi |
| `D:\pilot_extract_v022.py`, `D:\batch_extract.py` | kerfi A: cache + Batch API mynstur |
| `ONDEMAND_EXTRACTION_2026-07-13T2229Z.md:124-139` | cc5 kostnaðarmæling (2–4,3¢) |

---

**HALT.** Bíður svara við A1–A5. Engin aðgerð fyrr en go liggur fyrir.

---

## 9. DÓMUR A1–A5 (Danni, 2026-07-18) + LEIÐRÉTTING Á A5

### 9.1 Dómur

| # | Ákvörðun | Staða |
|---|---|---|
| **A1** | **KERFI A** (`batch_extraction`-ættin, 108 reitir). Kerfi B er notendalag, ekki þjálfunarleið. | ÚRSKURÐAÐ |
| **BACKFILL** | (b)-hópur 23.310 m/ Batch API, lotuskipt á nætur, gluggi **eftir 26.07 og fyrir 31.08**. | **SKILYRT — bíður go með tölu** |
| **(c) pörunargat** | 88.347 (60,3%) → sér-liður á PLANNING_BACKLOG m/ ársþekju-tölum. | SKRÁÐ (§10) |
| **A5** | `cache_control` á fasta forskeytið í kerfi B. | **KEYRT — sjá leiðréttingu 9.2** |

### 9.2 LEIÐRÉTTING: A5-ávinningurinn er ~14%, ekki 28%

Talan 28% sem gefin var í cc20-samantektinni **var of há**. Hún gerði ráð
fyrir að allt fasta forskeytið (3.854 tok) væri cache-hæft. Það er það ekki:

| Hluti forskeytis | Tokens (mat) | Cache-hæft? |
|---|---:|---|
| `EXTRACTION_PROMPT` (system, 4.084 stafir íslenska) | ~2.184 | **já** |
| `EXTRACTION_SCHEMA` (um `output_config.format`) + kerfisyfirbygging | ~1.670 | **nei** |

`cache_control` má aðeins setja á `system`-, `tools`- eða skeytablokkir.
`output_config.format` tekur það ekki — skemað verður endursent fullu verði
í hverju kalli.

**Umferðarmynstur (mælt, 41 bil milli 42 kalla):** 83% kalla koma innan
5 mín frá því síðasta, miðgildisbil 6 sek. Köllin koma í hviðum (prófanir
og `gata_eigindi` í öldum) — cache hittir því oftast, sem er forsenda þess
að þetta borgi sig yfirleitt.

**Endurreiknaður ávinningur** (83% lestur á 0,1×, 17% skrif á 1,25×):
- sparast ~1.539 tok/kall af ~4.900 innslætti
- **≈14% af heildarkostnaði kalls** (intro og listaverð svipað)

**Tvennt sem dregur enn úr:**
1. **Lágmarksþröskuldur.** Cache-hæfi hlutinn er ~2.184 tok og lágmarkið
   fyrir sonnet-tier er 2.048. Það er ~7% borð. Fari system-promptið undir
   þröskuldinn **þegir cache-ið án villu** (`cache_creation_input_tokens: 0`).
   Sérhver stytting á promptinu framvegis getur slökkt á þessu hljóðlaust.
2. **`gata_eigindi` keyrir 5 samhliða.** Samhliða köll geta ekki lesið cache
   hvert annars — í öldu af 5 skrifar eitt og hin fjögur missa.

### 9.3 Sannreyning A5 — aðferð

Beiðnin sagði „eitt on-demand-kall fyrir/eftir, input_tokens fellur ~65%".
Hvorugt stemmir alveg:

- **Tvö köll þarf eftir breytingu, ekki eitt fyrir og eitt eftir.** Fyrsta
  kallið *skrifar* cache (`cache_creation_input_tokens` ≈ 2.184, `input_tokens`
  óbreytt). Annað kallið innan 5 mín *les* (`cache_read_input_tokens` ≈ 2.184).
  Merkið sést aðeins á kalli #2.
- **Fallið verður ~43%, ekki 65%.** `input_tokens` sem skráð er í
  `eigindi_extraction_runs` er ócache-aða talan. Grunnlína er meðaltal
  **5.032**; á cache-lestri á að sjást **~2.850**.

Engin migration þarf — mælingin sést í núverandi runs-töflu:

```sql
select created_at, input_tokens, output_tokens
  from public.eigindi_extraction_runs
 where skema_utgafa = 2
 order by created_at desc limit 5;
```

**Fellur input_tokens ekki í ~2.850 á öðru kalli innan 5 mín er cache-ið
óvirkt** — líklegasta orsök er lágmarksþröskuldurinn (9.2, liður 1).

**Kóðabreyting:** `verdmat-ai/lib/eigindi-extraction.js` — `system` fer úr
streng í `[{type:"text", text, cache_control:{type:"ephemeral"}}]`.
Módúll hleðst hreint. **Ekkert kall keyrt í þessari lotu.**

---

## 10. KEYRSLUÁÆTLUN BACKFILL — tilbúin, bíður go með tölu

**Leið: kerfi A.** Engin ný töfluhönnun, engin ný samrunaleiðsla, engin ný
idempotens — allt mynstrið er þegar til í `D:\batch_extract.py` og
`D:\pilot_extract_v022.py`.

### 10.1 Umfang og kostnaður

| | |
|---|---|
| Þýði | (b)-hópur, 23.310 samningar — 22.875 m/ texta >0 stafir |
| Módel | `claude-haiku-4-5`, skema v0.2.2 (108 reitir) |
| Aðferð | Message Batches API, 50% afsláttur |
| Prompt-cache | já — system + tool-skema (kerfi A gerir þetta þegar) |
| **Kostnaðarmat** | **$81** (batch) — $162 án batch |
| Mælt einingaverð | 0,71¢/kall (`PER_CALL_USD`, staðfest í `pilot_extract_v022.log`) |

Verðlok 31.08 hafa **engin áhrif á þessa leið** — haiku-verð breytist ekki.
Tímaglugginn eftir 26.07 stendur samt sem óskað var.

### 10.2 Lotuskipting (nætur)

| | |
|---|---|
| `CHUNK_SIZE` | 5.000 (þegar í `batch_extract.py:97`, undir 256 MB þaki) |
| Fjöldi lota | **5** (4 × 5.000 + 1 × 2.875) |
| Ein lota per nótt | 5 nætur → gluggi 27.07–31.07, gott borð fram að 31.08 |
| Pollun | 300 sek, 36 klst þak per lotu (`batch_extract.py:98-99`) |
| Endurræsing | `D:\batch_state.json` — þegar til |

### 10.3 Idempotens (óbreytt mynstur)

- Lykill: `lysing_hash = md5(lysing)[:12]`, PK í `scraper.listing_extractions`
- Innsetning: `ON CONFLICT (lysing_hash) DO NOTHING`
- Endurkeyrsla lotu er því sjálfkrafa örugg; endur-auglýsingar með sama texta
  deila einu extraction
- Innsláttarsía: `MIN_LYSING_LEN=300`, `MAX_LYSING_LEN=3000`
  (`batch_extract.py:93-94`) — **ATH:** miðgildi (b)-hópsins er 3.931 stafir,
  þ.e. **meirihluti hópsins fellur á efri þakinu**. Þakið þarf hækkun eða
  röksemd áður en keyrt er (sjá 10.5).

### 10.4 Girðingar sem þarf að losa vísvitandi

- `run_extraction.py --daily-cap-usd 10.0` → dugir ($81 alls) en lotan má ekki
  fara um sömu kóðaleið og næturkeyrslan svo hún éti ekki kvótann hennar
- `EIGINDI_DAGSTHAK` (200/dag) á **ekki** við — það er kerfi B

### 10.5 Óleyst fyrir go

1. **`MAX_LYSING_LEN=3000` sker meirihluta (b)-hópsins.** Miðgildi 3.931,
   p90 5.845. Þarf annaðhvort hækkun þaksins eða meðvitaða ákvörðun um að
   klippa. Þetta breytir bæði þekju og kostnaði og er **ekki mitt að ákveða**.
2. **Skema v0.2.2 er ósannreynt á 2024–2026 textum** (batch-keyrslan var á
   eldra safni). Prufulota 2.000 áður en fullar 5 lotur fara af stað.
3. Kostnaðartalan sem go-ið á að bera.

---

## 11. PLANNING_BACKLOG-LIÐUR — pörunargatið (c)

**Titill:** Pörunarþekja `pairs_v1` — stærsta lyftistöngin á eigindaþekju

**Vandi:** 88.347 af 146.499 samningum þjálfunarþýðisins (60,3%) eiga enga
pörun við auglýsingu og þar með engan texta. Extraction getur ekki lagað þetta.
Fullur extraction-backfill lyftir þekju úr 23,8% í 39,7% og **ekki hærra**.

**Ársþekja — rekið er í nýlegum gögnum:**

| ár | 2016 | 2018 | 2020 | 2022 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|
| þekja | 45,0% | 44,4% | 33,0% | 32,2% | **27,9%** | 29,5% | **12,8%** |

Þekjan fellur eftir því sem nær dregur. Fari eigindin inn í líkanið án þess að
þetta sé lagað verður featurið kerfisbundið þynnst á nýjustu gögnunum — þ.e.
veikast þar sem líkanið er mest notað.

**Sér-probe (ekki mælt í cc20):** ~36.100 sölutextar liggja í SQLite á diski
(32.376 mbl + 3.291 myigloo + 418 visir) sem `pairs_v1` nær ekki til.
Óvitað hve stór skörun þeirra við (c)-hópinn er. Það er fyrsta mælingin.

**Þekjan er flöt eftir eignategund/svæði** (18,8–41,6%) — engin undirtegund
er kerfisbundið verr sett, svo markviss hlutabackfill vinnur lítið umfram flatan.
