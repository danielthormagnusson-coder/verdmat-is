# cc28 — Staging-hreinsun: `predictions_staging` + júlí-parið DROPPUÐ

**Dags:** 2026-07-18 · **Migration:** `20260718210603_cc28_drop_dead_staging`
**Niðurstaða:** 3 töflur droppaðar (1.010.036 raðir alls), 2 skildar eftir á mældu lífi.

---

## 0. Samantekt

DECISIONS.md ákvað 2026-07-03 að `public.predictions_staging` skyldi **droppað**, ekki
varið með RLS-policy. cc9-migrationin `20260714214317` setti RLS á sem bráðabirgða-plástur
meðan ákvörðunin beið. cc28 framkvæmdi ákvörðunina eftir herta sannreynslu og tók
júlí-parið með á sömu mælingu.

| Tafla | Raðir | Afdrif |
|---|---:|---|
| `public.predictions_staging` | 167.503 | **DROPPUÐ** |
| `public.predictions_july_staging` | 167.503 | **DROPPUÐ** |
| `public.feature_attributions_july_staging` | 1.675.030 | **DROPPUÐ** |
| `public.predictions_rent_staging` | 158.314 | **STENDUR** — líf mælt |
| `public.feature_attributions_rent_staging` | 1.583.140 | **STENDUR** — líf mælt |

Pláss losað: 28 + 23 + 118 = **169 MB**.

---

## 1. Hert sannreynsla (liður 1 í cc28-prompti)

### 1a. Kyrrstöðugreining — 9 vísanir, engin þeirra keyrandi kóði

| Skrá | Lína | Eðli |
|---|---|---|
| `app/supabase/migrations/20260714214317_cc9_rls_fix_snapshot_staging.sql` | 12, 23, 40 | cc9-DDL (bráðabirgða-RLS) |
| `app/supabase/rollback/20260714214317_..._rollback.sql` | 7 | rollback-par |
| `app/docs/RLS_FIX_20260714T214739Z.md` | 21, 47, 66 | skjal |
| `app/docs/DECISIONS.md` | 125, 127 | ákvörðunin sjálf |
| `app/docs/STATE.md` | 15, 27 | skjal |
| `app/docs/fable_prep/audit/RETRAIN_ITER4R_2026-07-16.md` | 124 | skjal |
| `precompute/load_comps_v2.py` | 9 | **athugasemd** — vísar í töfluna sem *fordæmi* („predictions_staging lexían"), snertir hana ekki |

**Þekja leitarinnar:** öll þrjú repo (`app`, `precompute`, `verdmat-ai`) · **D:-rót, 77 .py-skriptur → 0 hits** ·
**precompute að meðtöldum ó-committuðum skriptum → 1 hit (athugasemdin)** ·
**Task Scheduler, 7 verdmat-verk export'uð með `schtasks /query /fo LIST /v` → 0 hits.**

Verkin sjö sem keyra: `lifecycle_sweep_mbl`, `daily_sales_refresh.py`, `run_backup.ps1`,
`nightly_delta_chain.sh`, `myigloo_nightly_chain.sh`, `monthly_cpi_reanchor.py`,
`model_quality_eval.py`. Ekkert þeirra snertir töflurnar.

### 1b. Hreyfigreining — kyrrstæðar síðan 1. júlí

`pg_stat_user_tables` + raðastimplar:

| Tafla | `n_tup_ins` | `n_tup_upd` | `n_tup_del` | `idx_scan` | síðasti lestur | `predicted_at` | `model_version` |
|---|---:|---:|---:|---|---|---|---|
| `predictions_staging` | 167.503 | **0** | **0** | **NULL** | 2026-07-14 21:44Z | 2026-07-01 (min=max) | `iter4_final_v1` |
| `predictions_july_staging` | 167.503 | **0** | **0** | **NULL** | 2026-06-30 19:11Z | 2026-07-01 (min=max) | `iter4_final_v1` |
| `feature_attributions_july_staging` | 1.675.030 | **0** | **0** | **NULL** | 2026-06-30 19:11Z | — | — |

**Lykilatriði:** síðasti lestur á `predictions_staging` (2026-07-14 21:44:38Z) er *cc9-RLS-úttektin
sjálf* — skjalið `RLS_FIX_20260714T214739Z.md` er stimplað 21:47:39Z, þremur mínútum síðar.
Síðasta snerting var sem sagt úttektin, ekki rekstur. `idx_scan = NULL` þýðir að ekkert
forrit hefur nokkurn tímann flett upp í töflunni.

**Kynslóðabil:** allar bera `iter4_final_v1` meðan lifandi `predictions` keyrir á
`iter4r_20260716` — tvær líkanakynslóðir á eftir.

**DB-háðir:** 0 views · 0 matviews · 0 föll (`pg_proc.prosrc ILIKE`) · 0 `pg_depend`-tengsl.

### 1c. Flipp-skriptan — notar þær EKKI

`precompute/flip_iter4r.py` línur 39 + 107–110:

```python
STG_P, STG_F = "predictions_iter4r_staging", "feature_attributions_iter4r_staging"
...
log(f"  ATH: {stg} er til — DROP og endursmíð (staging er einnota)")
```

Skriptan býr til **sínar eigin** töflur með viðskeyti, DROPpar og endursmíðar þær í hverri
keyrslu, og hefur **enga vísun** í þessar þrjár. Það par var droppað í cc14. Líklegasti
lifandi neytandinn var þar með útilokaður **með mælingu, ekki ályktun**.

### 1d. Dómur

Öll þrjú skilyrðin uppfyllt → grænt á DROP.

---

## 2. Afrit (belti og axlabönd)

`pg_dump` 17.6 (= server-útgáfa), `--schema=public --table=... --no-owner --no-privileges`.
DSN lesinn úr `D:\verdmat-is\.dbconfig` í pípu — aldrei prentaður.

| Skrá (í `D:\_rollback_backup\`) | Stærð |
|---|---:|
| `cc28_predictions_staging_20260718T210603Z.sql` | 24,7 MB |
| `cc28_predictions_july_staging_20260718T210603Z.sql` | 19,5 MB |
| `cc28_feature_attributions_july_staging_20260718T210603Z.sql` | 72,0 MB |

**Sannreynt INNI Í dumpunum** (talning `COPY ... FROM stdin;`-blokka, ekki bara skráarstærð):

```
predictions_staging                dump=   167503  vaent=   167503  PASS
predictions_july_staging           dump=   167503  vaent=   167503  PASS
feature_attributions_july_staging  dump=  1675030  vaent=  1675030  PASS
```

3/3 PASS. `predictions_staging` 24,7 MB á móti 28 MB töflustærð — mismunurinn er
tafluyfirbygging (page overhead), ekki gagnatap; raðatalningin sannar það.

`pre_iter4r`-snapshotið stendur óháð þessu og er önnur, sjálfstæð endurreisnarleið.

---

## 3. Framkvæmd

- **Migration:** `app/supabase/migrations/20260718210603_cc28_drop_dead_staging.sql`
  (ber alla sannreynsluna sem athugasemd + rowcount + afritsslóðir)
- **Rollback:** `app/supabase/rollback/20260718210603_cc28_drop_dead_staging_rollback.sql`
  — tvíþætt: skema (CREATE TABLE ×3 + **ENABLE ROW LEVEL SECURITY ×3**) + gögn úr dumpunum.
  Gildra skjalfest í skránni: dumparnir bera **ekki** RLS-stöðuna, svo þeir skilja
  töflurnar eftir OPNAR ef þeir eru keyrðir beint. RLS-línurnar eru skylda.

---

## 4. Eftirtékk

**Töflustaða eftir DROP** — aðeins leigu-parið eftir:

```
feature_attributions_rent_staging   rls=true   161 MB
predictions_rent_staging            rls=true    30 MB
```

**Advisors endurkeyrðir** (`security`): `predictions_staging`,
`predictions_july_staging` og `feature_attributions_july_staging` eru **horfnar** úr
`rls_enabled_no_policy`. Flöggunin sem cc9 plástraði er farin við rótina.

**`spatial_ref_sys` skilin eftir sem known-accepted:** ERROR `rls_disabled_in_public` stendur.
Þetta er PostGIS-kerfistafla; `ALTER TABLE` þar strandar á ownership hvort eð er. Ekki galli,
ekki verkefni.

---

## 5. HALT — leigu-parið stendur (liður 3)

`predictions_rent_staging` + `feature_attributions_rent_staging` voru mæld á **sömu**
sannreynslu og féllu á henni — **líf sést**:

| Merki | Mæling |
|---|---|
| Kóðavísun | `precompute/load_rent_staging.py` **SKRIFAR** í þær (TRUNCATE + COPY, línur 51–56) |
| Lestur | `idx_scan` = 437 / 2 · `last_idx_scan` **2026-07-18 09:46Z** (í dag) |
| Staða | `RENT_MODEL_CARD.md`: „scored to staging only, **NOT promoted**", `predictions_rent` (live) = 0 |
| Ákvörðun | cc13 skráði promotion sem **opna** — lota #1 áætluð ~22.07 |
| Kynslóð | `rent_v1`, `predicted_at` 2026-05-01 — núverandi, ekki úrelt |

Þær eru **ekki** dauðir artifacts heldur óflippað líkan sem bíður ákvörðunar. Ekki snert.

**Athugasemd um flöggun þeirra:** þær standa áfram í `rls_enabled_no_policy` (INFO). Þrátt
fyrir að bera 14 `anon`/`authenticated` grants eru þær **lokaðar** — RLS á + 0 policies
neitar öllu. Grantarnir eru gagnslausir en meinlausir. Rétta afgreiðslan er að láta þetta
fylgja leigu-flippinu (lota #3), ekki plástra sérstaklega.

---

## 6. Lærdómur

**Bráðabirgða-RLS-plástur á dauða töflu felur ákvörðun í stað þess að framkvæma hana.**
cc9 setti RLS á `predictions_staging` af því að advisors flaggaði hana — en ákvörðunin um
DROP lá þá þegar fyrir (DECISIONS.md, 11 dögum fyrr). Plásturinn slökkti á viðvöruninni og
þar með á áminningunni. Taflan lifði fjórum lotum lengur en hún átti.

**Reglan:** þegar advisors flaggar töflu, spurðu fyrst hvort hún eigi að vera til. RLS-plástur
er rétt svar fyrir töflu sem á að lifa; fyrir dauðan artifact er hann frestun sem lítur út
eins og lausn.

**Aðferðin sem skar úr:** `idx_scan = NULL` + `n_tup_upd = 0` + tímastimpill síðasta lesturs
sem rakinn er til *úttektarinnar sjálfrar* er sterkari sönnun en grep eitt og sér — grep
finnur ekki lesanda sem er ekki í repo-inu. Öfugt sannaði `last_idx_scan` í dag að leigu-parið
lifir, þótt sami grep hefði getað verið lesinn sem „bara skjöl".
