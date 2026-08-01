# cc47 — LÆKNUN B fullnaðuð + AKKERIS-VÖRÐUR

> **Lota cc47, klukka tvíhliða: staðvær 2026-07-26 08:11:35 (+00:00) · UTC
> 2026-07-26T08:11:35Z · TZ „Greenwich Standard Time", offset 0 → staðvær = UTC.**
> Ótracked lotuskýrsla. Arkitekt flytur §5 (DATA_SCHEMA-viðaukann) í tracked docs
> í bókunarlotu.

---

## 0. Staða í einni setningu

Vikuvélin `model_quality_eval` hafði **ekki mælt neitt síðan 13.07** og bókaði það sem
`success`. Hún er nú endurstillt á lifandi líkanið, mælir tvöfalda OOS-skilgreiningu,
og **aðaltalan fellur á dómsreglunni: cov80 = 68,0 % á n=847 (< 80 %)**. HALT til
arkitekts. Engin skrif í `model_metrics` framkvæmd — bíður sér-go.

---

## 1. Þöglu núllvegunin — hvað var raunverulega að

`pipeline_runs` #76 (2026-07-20 05:00, 6,2 s):

```json
{"dryrun": false, "oos_pairs": 0, "overall": null, "rows_written": 0,
 "exit_status": "success",
 "paired_summary": {"paired_error": "RuntimeError: cpi_index missing model_pred_anchor_ym=2026-08"}}
```

**Tvær óháðar orsakir lágu ofan á hvor annarri:**

1. **Harðkóðað `MODEL_VERSION = "iter4_final_v1"`.** iter4r-flippið 16.07 skipti út öllum
   167.503 röðum í `public.predictions`. Fastinn lifði flippið af og mældi árgang sem er
   ekki lengur til. Sannreynt í dag:

   | `p.model_version` | raðir sem `fetch_oos` finnur |
   |---|---:|
   | `iter4_final_v1` (harðkóðaði fastinn) | **0** |
   | `iter4r_20260716` (lifandi) | 2.105 |

2. **`CROSS JOIN anchor` á tómt akkeri.** 20.07 vantaði `2026-08` í `cpi_index`, svo
   akkeris-CTE-ið skilaði núll röðum og krossjoinið tortímdi öllu í hljóði — sama mynstur
   og cc41. Sú orsök er sjálfkrafa horfin (vísitölu-vélin bætti 08 og 09 við síðan), en
   *aðferðin* var eftir. Nú er akkerið leyst upp á undan og gefið inn sem breyta; ekkert
   krossjoin lengur.

**Hvorug orsökin gaf merki.** `exit 0`, `success` í `pipeline_runs`, og engin lína í
`D:\model_quality_eval.log` sem stakk í augun. Fjarvera mælingar leit út eins og kyrrð.

---

## 2. Rótarfixin (bæði)

### 2.1 `model_version` lesið úr `pipeline_config`

Lykillinn **var þegar til** — `flip_iter4r.py:205` skrifar bæði `model_pred_anchor_ym`
og `model_version` inni í flipp-txn-inu. Enginn nýr lykill þurfti; vélin var einfaldlega
ekki að lesa hann.

```
pipeline_config: model_version = 'iter4r_20260716'
                 model_pred_anchor_ym = '2026-08'
                 sales_history_anchor_ym = '2026-09'
```

`read_model_version()` kastar `MeasurementFailure` ef lykillinn vantar — **engin
harðkóðuð varaleið**. Flipp-hefðin stendur óbreytt framvegis.

### 2.2 Núll raðir = fall, ekki niðurstaða

Ný `MeasurementFailure` + `loud()` (78 upphrópunarmerki, ómissanleg í 40 KB logg) og
`exit 1` þegar:

- `holdout30` finnur < 200 pör (gólf; 30 % af raunverulegum kvörðunarglugga er aldrei svo lítið)
- `fresh_edge` finnur 0 pör (þá er sölu-leiðslan stopp — það er niðurstaða, ekki tómleiki)
- `overall`-sneiðin er tóm (engin íbúðarhúsnæði → engin aðaltala til að dæma)
- skrifin lenda á 0 röðum úr ótómum farmi (rúllað til baka)
- sviðin tvö skarast (þá er annar glugginn rangmerktur og báðar tölurnar grunsamlegar)

---

## 3. Rauðsönnun (2/2 — bæði stig vörnarinnar)

| # | Keyrsla | Vænt | Fékkst |
|---|---|---|---|
| 1 | `--force-model-version ekki_til_v999` | exit≠0 | **exit 1**, `MÆLING SKILAÐI ENGU: manifest not found: D:\model_artifacts\ekki_til_v999\...` |
| 2 | `--force-model-version cc47_rautt_prof` (gilt manifest+holdout afritað, heiti ekki í `predictions`) | exit≠0 | **exit 1**, `scope 'holdout30' returned 0 pairs (floor 200) ... version is not in public.predictions` |

Rauðsönnun 1 ein hefði **ekki** sannað núll-vörnina — hún stöðvast á manifestinu áður en
nokkur fyrirspurn er gerð. Þess vegna var #2 sviðsett: gilt manifest, gild
holdout-aðild, heiti sem er ekki til í `predictions` → nákvæmlega ástandið sem gaf
þögult núll 20.07. Sviðsetta mappan `D:\model_artifacts\cc47_rautt_prof\` var eydd
strax á eftir (`Test-Path` → False).

`--force-model-version` er merkt RAUÐSÖNNUN ONLY í hjálpartexta og prentar að
`pipeline_config` sé sniðgengið.

---

## 4. Mælingin — báðar tölur með nefnurum

**Keyrsla: `--dryrun` (engin skrif í `model_metrics`).** Lifandi líkan
`iter4r_20260716`, de-akkeri `cpi[2026-08] = 690,700`.

Manifest af diski (`iter4r_20260716_manifest.json`): `train_end=2026-01-15`,
`data_end=2026-07-15`, `holdout_frac=0.3`, `holdout_seed=20260716`, `n_features=154`.

| | sample_scope | oos_cutoff | **n** | MAPE | medAPE | bias | **cov80** | cov95 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| **(a) AÐALTALA** — 30 % holdout, seed 20260716 | `holdout30` | 2026-01-15 (train_end) | **847** | 9,96 % | 7,66 % | −2,56 % | **68,0 %** | 90,4 % |
| **(b) HLIÐARTALA** — ferskur jaðar | `fresh_edge` | 2026-07-15 (data_end) | **191** | 12,38 % | 10,33 % | −3,18 % | **62,3 %** | 90,1 % |

**Nefnarabókhald.**
(a) 848 FAERSLUNUMER í `iter4r_20260716_holdout_rows.csv` (allar `calib_role='holdout'`,
`model_group='main'`, `onothaefur=0`, `is_suspect_comparable=False`) → 848 finnast í
`sales_history` → **847** para sig við `predictions` með CPI (1 eign án lifandi spár) →
847 eru allar íbúðarhúsnæði, svo `overall` = 847.
(b) 316 sölur þinglýstar > 2026-07-15 → 230 eftir `onothaefur=0` + verð > 0 → **198** para
sig við `predictions`+`properties` (allar með CPI) → **191** eftir að sumarhús/annað
utan íbúðarhúsnæðis fellur út.
Skörun sviðanna tveggja: **0 faerslunumer** (staðfest í kóða, ekki gefið sér).

**Aðgreiningin í `model_metrics`:** hvor talan fær sitt `sample_scope` OG sitt
`oos_cutoff`. `extra` á báðum `overall`-röðum ber `scope_role` („AÐALTALA" / „HLIÐARTALA")
og `never_sum_with`, svo lesandi einnar raðar sér samstundis að þær megi ekki leggja saman.

### 4.1 Hvers vegna 68,0 % en ekki 81,2 %

Holdout-skýrslan frá þjálfun (16.07) segir cov80 = 81,2 % á sömu 848 röðunum. Ég
endurreiknaði `c_in80` beint úr `holdout_rows.csv`: **81,25 %** — skýrslan stemmir. Munurinn
er **ekki** ólík sneið og **ekki** ólík bilbreidd:

| | med rel80 | cov80 |
|---|---:|---:|
| kandídat, þjálfunarbraut (`c_in80`, real/real, hver sala í eigin tímasamhengi) | 0,219 | 81,25 % |
| lifandi artifakt, útgáfubraut (spá skoruð einu sinni @ 2026-07, CPI-bakfærð á sölumánuð) | 0,219 | 68,0 % |

Bilin eru **nákvæmlega jafnbreið** (0,219 í báðum, og 0,219 í hverjum einasta sölumánuði).
Það er punktspáin sem færist. Sundurliðun eftir sölumánuði sýnir að þetta er **ekki**
CPI-bakfærslurek sem vex með fjarlægð frá verðmats-mánuðinum:

| sölumánuður | 01 | 02 | 03 | 04 | 05 | 06 | 07 |
|---|---:|---:|---:|---:|---:|---:|---:|
| n | 46 | 95 | 202 | 131 | 121 | 163 | 89 |
| cov80 | 73,9 | 67,4 | 72,8 | 68,7 | 60,3 | 68,1 | 64,0 |

Fjærsti mánuðurinn (janúar) er **bestur**, ekki verstur. Og ferski jaðarinn — sem liggur
1–9 daga frá verðmats-mánuðinum og hefur því nánast enga bakfærslu — er **lægstur allra
(62,3 %)**. Skekkjan liggur ekki í de-akkerinu.

**Þetta er fyrsta VAKTARmælingin.** RETRAIN_ITER4R §5 merkti 81,2 % beinlínis sem
„kandídatsmæling við þjálfun, ekki vaktarmæling" og bannaði nýja tracking-röð fyrr en
vaktarmæling lægi fyrir. Hún liggur nú fyrir og er 13,2 pp lægri.

### 4.2 DÓMSREGLA

```
cov80(aðaltala) = 68,0 % < 80 %   →   HALT
```

Vélin prentar háværa línu, bókar `domsregla` í `pipeline_runs.summary` OG í `extra` á
báðum `overall`-röðum, og endar á **exit 2** (nýr kóði: mælt og skrifað, en dómsreglan
féll). Mælingin er skrifuð **áður en** exit 2 gerist — HALT má ekki eyða eigin sönnun.

Afleiðingarnar tvær (`/adferdafraedi` stöðumerking skv. grunnreglu 13; flýtt endurþjálfun
skv. yfirlýstri reglu síðunnar) eru **ekki** gerðar sjálfkrafa og **ekki** gerðar í þessari
lotu. Þær eru arkitektsins.

### 4.3 Þriðja þögla talan sem fannst á leiðinni

E2/paired-brautin skorar í gegnum `phase_d3_score_extract`, sem hleður `D:\iter4a_*.lgb`
og stimplar `iter4_final_v1`. Eftir flippið er það **annað líkan** en það sem situr í
`predictions`. „Extraction-gapið" hefði því verið fjarlægðin milli TVEGGJA LÍKANA með
extraction-miða á sér. Blokkin neitar nú að keyra þegar `ADAPTER_MODEL_VERSION !=
model_version` — hávært og bókað (`paired_skipped: adapter_model_mismatch`), aldrei þögult.
Aðaltalan er ósnortin af því (E1-vörnin heldur).

---

## 5. VIÐAUKI TIL DATA_SCHEMA.md — akkeris-invariantinn

> Arkitekt flytur þennan kafla í `docs/DATA_SCHEMA.md` í bókunarlotu.

### Akkeris-invariantinn

Í `pipeline_config` eru **tvö óháð CPI-akkeri** sem hreyfast á sitt hvorum hraða:

| lykill | hvað situr á því | hver hreyfir |
|---|---|---|
| `sales_history_anchor_ym` | `sales_history.kaupverd_real` | `monthly_cpi_reanchor.py`, mánaðarlega |
| `model_pred_anchor_ym` | `predictions.real_pred_*` | **aðeins líkans-flipp** (`flip_iter4r.py`) |

**INVARIANT.** `kaupverd_real` og `real_pred_*` eru **ekki á sama kvarða** nema akkerin
tvö séu jöfn. Þegar þau eru það ekki ber hver beinn REAL-á-REAL samanburður falinn
margfaldara:

```
skekkja = cpi[sales_history_anchor_ym] / cpi[model_pred_anchor_ym]
```

**Staðan í dag (2026-07-26):** `sales=2026-09` (cpi 693,2), `model=2026-08` (cpi 690,7) →
**+0,3620 %**. Empírískt staðfest: miðgildi
`kaupverd_real / (kaupverd_nominal × cpi[2026-09]/cpi[söluM])` = **1,000000** á n=5.658
sölum frá 2026-01 — þ.e. `kaupverd_real` situr sannanlega á sölu-akkerinu.

**Ónæmi.** NOMINAL/NOMINAL samanburður er ónæmur, því hann snertir `kaupverd_real` aldrei:

```
nominal_pred = real_pred_mean × cpi[söluM] / cpi[model_pred_anchor_ym]
   borið saman við   kaupverd_nominal
```

Þetta er formið sem `model_quality_eval.py` og `semantic.v_model_vs_sold_by_hood` nota,
og það er **skyldan** fyrir hvern nýjan mælipunkt.

**Þögnin er vandinn, ekki frávikið.** Framtíðarvísitala er lögmæt og sölu-akkerið MÁ fara
fram úr líkans-akkerinu — það gerist í hvert sinn sem ný VNV-mánuður kemur á milli flippa.
Það sem má ekki er að það gerist án merkis. Akkeris-vörður (cc47) í
`monthly_cpi_reanchor.py` skref 2b gefur háværa WARN-línu og bókar
`summary.anchor_guard = {sales_anchor_new, model_anchor, verdict}` í `pipeline_runs`.
Verdict-gildi: `OK` · `SALES_ANCHOR_AHEAD` · `MODEL_ANCHOR_MISSING`. **Vörðurinn abortar
ekki** — að stöðva lögmætan vísitölumánuð til að vernda ópinnaðan lesanda væri röng stöng.

**Sögulegt tilefni.** `pipeline_runs` #85 (2026-07-26 04:00) færði sölu-akkerið
`2026-07 → 2026-09` — **stökk yfir 2026-08 og fram úr líkans-akkerinu í sömu aðgerð** —
og bókaði `exit_status: success` án þess að nefna yfirskotið einu orði. 228.875 raðir
uppfærðar. Það er nákvæmlega yfirskotið sem vörðurinn merkir héðan í frá.

---

## 6. Kallaralistinn (yfirskots-frágangur, liður a)

`rg --no-ignore --hidden` yfir öll þrjú repóin (`app`, `precompute`, `verdmat-ai`),
sniðmengi skráa sem nefna BÆÐI `kaupverd_real` OG `real_pred_*`, að viðbættum
`v_model_vs_sold`-lesendum. Dómur per stað:

### PINNAR (nominal/nominal eða skýrt akkeri)

| Staður | Hvað það gerir |
|---|---|
| `app/scripts/model_quality_eval.py` | `kaupverd_nominal` vs `real_pred_× × cpi[söluM]/cpi[model_pred_anchor_ym]`. Akkerið leyst upp á undan og gefið inn sem breyta — ekkert `CROSS JOIN` sem getur tortímt í hljóði (cc47) |
| `semantic.v_model_vs_sold_by_hood` (LIFANDI skilgreining, staðfest með `pg_get_viewdef`) | `kaupverd_nominal / (real_pred_median × cs.cpi/a.anchor_cpi)`, akkeri úr `pipeline_config`. **Athuga:** notar enn `CROSS JOIN anchor` → sama tortímingarhætta og cc41; pinningin sjálf er rétt. Á BACKLOG, utan cc47-umfangs |
| `verdmat-ai/lib/markadur-queries.js:773`, `markadur-lykiltolur.js:223`, `components/markadur/flipar/Likan.tsx` | lesa MV-ið beint (`sold_to_pred_ratio`), reikna ekkert sjálf → **erfa pinninguna** |

### SKEKKIST (ber saman real-á-real án sjálfstæðrar akkerispinnu)

| Staður | Línur | Hvað gerist |
|---|---|---|
| **`precompute/holdout_eval.py`** | 148–156 | `ratio = median(real_pred_mean/kaupverd_real)`; `scale = 1000 if 300<ratio<3000 else 1`; `sala_kr = kaupverd_real × scale`. Þetta er **einingaskynjari, ekki akkerispinna** — hann greinir þús.kr vs kr og lætur akkeris-frávikið óáreitt. `l_ape`/`l_in80`/`l_in95` (M2-„live"-dálkurinn í holdout-skýrslunni) bera því +0,362 % skekk í dag. **Fer vaxandi eftir því sem lengra líður frá flippi.** — Athuga: þetta er sama skriptan og býr til `holdout_rows.csv`, sem cc47 les til að skilgreina aðild `holdout30`. **Aðildin er ósnortin** af gallanum (`FAERSLUNUMER`, `calib_role`, síurnar) — gallinn snertir aðeins `l_*`-dálkana. Ný cc47-mæling reiknar sínar eigin tölur nominal/nominal og notar CSV-ið eingöngu sem aðildarlista |
| `app/docs/fable_prep/prototypes/conformal_recal_holdout.py` | 59–85 | sama `scale`-mynstur, sama skekk. Frumgerð, ekki í rekstri |
| `app/docs/fable_prep/prototypes/conformal_recal_extra.py` | 38–40 | `kaupverd_real` borið **beint** við `real_pred_lo80/hi80` — engin skölun, engin pinna. Frumgerð, ekki í rekstri |

### SÖGULEGT — villir þann sem les migrations sem sannleik

| Staður | Lína | Athugasemd |
|---|---|---|
| `app/supabase/migrations/20260612091832_t5_semantic_phase2.sql` | 230 | `b.kaupverd_real / NULLIF(pr.real_pred_median,0) AS sold_to_pred_ratio` — upprunalega, ópinnaða skilgreining `v_model_vs_sold_by_hood`. **Lifandi sýnin er lagfærð** (nominal + akkeri), svo þetta skekkir ekkert í rekstri. Skráin er hins vegar ósamhljóða DB-inu og migration-skrár eru lesnar sem heimild |

### Á EKKI VIÐ

`app/scripts/phase_d3_apply.py` (INSERT-hleðsla, enginn samanburður) ·
`precompute/build_precompute.py` (**býr til** `kaupverd_real` úr `cpi_factor` í
`training_data_v2`; ber ekki saman við spár) · `app/scripts/daily_sales_refresh.py` +
`monthly_cpi_reanchor.py` (hreyfa/lesa `kaupverd_real`, snerta aldrei `predictions`) ·
`app/components/SalesHistoryTable.js` + `verdmat-ai/components/SalesHistoryTable.js`
(birta söluverð, engin spá í sömu tölu) · `baseline.sql` og
`_legacy_migrations/20260421_initial_schema.sql` (dálkaskilgreiningar) · skjöl
(`DECISIONS.md`, `PLANNING_BACKLOG.md`, `T5_SEMANTIC_VIEWS_v1.md`, `CPI_REBUILD_*`,
`CONFORMAL_RECAL_*`).

**`verdmat-ai`-repóið: núll staðir** í flokkunum SKEKKIST/PINNAR-með-eigin-reikningi.
Öll líkans-vs-sala framsetning þar fer gegnum MV-ið.

**Ekkert lagað í þessari lotu.** Listinn er dómur, ekki viðgerð — `holdout_eval.py` er
eina rekstrarlega tilfellið og viðgerð þar er sér-ákvörðun (hún breytir tölum í
þjálfunarskýrslum aftur í tímann).

---

## 7. Það sem var EKKI gert

- **Engin skrif í `model_metrics`.** Bíður sér-go innan lotu (liður 2 í fyrirmælum).
  Tölurnar í §4 eru úr `--dryrun`.
- **`/adferdafraedi` ósnert** — stöðumerking skv. grunnreglu 13 er arkitektsins.
- **Engin endurþjálfun ræst.**
- **Ekkert commit.** Þrjár skrár breyttar í vinnutré `app` (87 skrár óhreinar alls →
  explicit paths skylda).
- **`sales_history_real_backup_20260726_0400` (228.875 raðir) STENDUR** — ósnert, bíður
  ágúst-vaktar eins og hin borðin.
- `v_model_vs_sold_by_hood` `CROSS JOIN anchor`-hættan: greind, bókuð, **ekki lagfærð**
  (utan umfangs).

---

## 8. Breyttar skrár

| Skrá | +/− |
|---|---|
| `app/scripts/model_quality_eval.py` | 506 breyttar línur (fastarnir fjórir, tvöföld OOS, bæði rótarfixin, dómsreglan, adapter-vörður) |
| `app/scripts/monthly_cpi_reanchor.py` | +55 (akkeris-vörður skref 2b + bókun í 3 `finish_run`) |
| `app/scripts/anchor_config.py` | +17 (`read_model_anchor`, viljandi ekki fatal) |

`python -m py_compile` grænt á öllum þremur.

— cc47, 2026-07-26T08:11Z

---

## VIÐAUKI A (bætt við 2026-07-28) — exit≠0 kviknar engri tilkynningu

`verdmat-weekly-model-quality` keyrir `C:\Python314\python.exe` beint; **enginn wrapper,
enginn `OnFailure`-trigger, engin tilkynningarrás.** Nýju exit-kóðarnir (1 = mæling
skilaði engu, 2 = dómsreglan féll) skila sér því aðeins í `LastTaskResult` í Task
Scheduler og í `pipeline_runs.exit_status` — **ekkert lætur vita af sjálfu sér.**

Þetta er raunveruleg takmörkun á lækningunni, ekki formsatriði: cc47 lagaði það að vélin
*mæli* og að hún *segi frá í logg og DB*, en ekki að **einhver frétti af því án þess að
fletta upp**. Fyrir mælingu sem á að vaka yfir líkaninu milli lota er það eftirstandandi
gat.

Til samanburðar: `LastTaskResult` var `0` þann 20.07 þegar ekkert var mælt. Héðan í frá
verður hann `2` eða `1` — sem er framför, en aðeins fyrir þann sem lítur.

**Staða: sér-liður á BACKLOG, EKKI útfærður nú.** Ákvörðun um rás (t.d. Resend-póstur
gegnum sömu leið og ábendingakerfið, `OnFailure`-trigger, eða morgunúttektin les
`pipeline_runs.exit_status`) er sér-go.

— cc47 viðauki, 2026-07-28
