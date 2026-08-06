# ROLLBACK_RUNBOOK_CC78 — ágúst-endurþjálfunin (regla R)

> **Staða: LESIN OG STAÐFEST AF ARKITEKT 2026-08-03.** Sjá §10 — allir sex
> staðfestingarreitir fylltir, með þremur sérstökum staðfestingum bókuðum.
> **Fasi 2 má hefjast** að uppfylltu einu útistandandi skilyrði: æfingarstig 1
> (§5, read-only) skal keyrt ÁÐUR en fyrsta þjálfunarkeyrsla hefst.
>
> Krafan sem þessi staða uppfyllir: runbókin varð að vera **lesin og staðfest**
> áður en fyrsta þjálfunarkeyrsla hæfist — ekki bara skrifuð. Þjálfun sem hefst án
> staðfestingar er keyrð án útgönguleiðar.

**Ritað:** cc78, 2026-08-03 · **Sameinar:** fasa 0 §5 (áætlun) + fasa 1D §8 (hörð
skilyrði) · **Leysir hvorugt af sem heimild um mælingar**, en er EINA
framkvæmdarskjalið. Ef þessi runbók og eldri skjöl stangast á, gildir þessi.

**Umfang:** ágúst-flipp cc78 (regla R + notkunar-mapping). Á EKKI við um leigu-brautina
(`predictions_rent*`) sem er ósnert.

---

## §0 HVAÐ ER ÖÐRUVÍSI VIÐ ÞETTA FLIPP

Fyrri flipp (`flip_iter4r.py`, júlí) snertu **aðeins spár**. cc78 snertir þrennt:

| # | hlutur | fyrri flipp | cc78 |
|---|---|---|---|
| 1 | `public.predictions` | já | já |
| 2 | `public.feature_attributions` | já | já |
| 3 | **`public.properties.canonical_code`** | **ALDREI** | **JÁ** |

Liður 3 er nýr og hefur þrjár afleiðingar sem eldri runbók nær ekki yfir:

- **R3-akkerið er nýtt og ófrávíkjanlegt** — án þess er engin leið til baka í gömlu
  flokkunina.
- **MV-listinn er ófullnægjandi.** `flip_iter4r.py` endurnýjar einn MV. Fjórir aðrir
  lesa `properties`/`canonical_code` (§7).
- **`/eign/*/stilla` brotnar fyrir 28.063 eignir** sem skipta um bílskúrs-fjölskyldu
  (fasi 0 §4.6) — `app/api/adjust-valuation/route.js` skilar **HTTP 400**.

---

## §1 FORSENDUR — R1–R9. EKKERT MÁ HEFJAST FYRR EN ÞÆR ERU ALLAR GRÆNAR

### R1 — frosnar spár  ⚠ HART SKILYRÐI

```sql
CREATE TABLE public.predictions_2026_08_pre_cc78 AS
  SELECT * FROM public.predictions;
ALTER TABLE public.predictions_2026_08_pre_cc78 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.predictions_2026_08_pre_cc78 FROM anon, authenticated;
```

> **R1 SKAL STAÐFEST ÁÐUR EN FLIPPI ER HRUNDIÐ AF STAÐ — ALDREI EFTIR.**
>
> `cc78_frozen_cohort_v1.pkl` og `predictions_pre_cc51` bera einu eftirlifandi
> eintökin af `iter4r_20260716`-spám utan `public.predictions` sjálfrar. Yfirskrifi
> flipp töfluna án staðfestrar R1 er **samanburðargrunnurinn horfinn og rollback
> ómöguleg**. Þetta er skilyrði, ekki ábending.

**Sannreyning — öll þrjú skrefin, í þessari röð:**

```sql
-- (a) rowcount
SELECT count(*) FROM public.predictions_2026_08_pre_cc78;   -- KRAFA: 167503

-- (b) model_version á ÖLLUM röðum
SELECT model_version, calibration_version, count(*)
FROM public.predictions_2026_08_pre_cc78 GROUP BY 1,2;
-- KRAFA: model_version = 'iter4r_20260716' á 167503 röðum, 2 calibration_versions
--        (…_conformal_serving_v1 og …_conformal_v1+segcal_fb)

-- (c) engin NULL í spádálkunum
SELECT count(*) FROM public.predictions_2026_08_pre_cc78
WHERE real_pred_mean IS NULL OR real_pred_lo80 IS NULL
   OR real_pred_hi80 IS NULL OR confidence_grade IS NULL;   -- KRAFA: 0
```

**(d) handahófsúrtak gegn frosna kohortnum — ófrávíkjanlegt:**

```python
# python, read-only
import pandas as pd, psycopg2
C = pd.read_pickle(r"D:\cc78_frozen_cohort_v1.pkl")          # sha c0e548cfddc4b1ff
s = C.sample(100, random_state=20260803)                      # fastur seed
conn = psycopg2.connect(open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig")
                        .read().strip()); conn.set_session(readonly=True)
fn = ",".join(str(int(x)) for x in s["fastnum"].unique())
db = pd.read_sql(f"""SELECT fastnum, real_pred_mean, real_pred_lo80, real_pred_hi80,
                            real_pred_lo95, real_pred_hi95, confidence_grade
                     FROM public.predictions_2026_08_pre_cc78
                     WHERE fastnum IN ({fn})""", conn)
m = s.merge(db, on="fastnum", suffixes=("_kohort", "_snap"))
for c in ["real_pred_mean", "real_pred_lo80", "real_pred_hi80",
          "real_pred_lo95", "real_pred_hi95"]:
    d = (m[f"{c}_kohort"].astype(float) - m[f"{c}_snap"].astype(float)).abs().max()
    print(f"{c}: max |Δ| = {d}")        # KRAFA: 0.0 á ÖLLUM fimm
```

> **KRAFA: nákvæmlega 0,0 á öllum fimm dálkum.** Þetta eru sömu raðir; hvert frávik
> þýðir að snapshotið er ekki af því sem kohorturinn mældi og **flipp má ekki hefjast**.

### R2 — feature_attributions

```sql
CREATE TABLE public.feature_attributions_2026_08_pre_cc78 AS
  SELECT * FROM public.feature_attributions;
ALTER TABLE public.feature_attributions_2026_08_pre_cc78 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.feature_attributions_2026_08_pre_cc78 FROM anon, authenticated;
```
**Sannreyning:** `count(*)` = **1.675.030** · engir munaðarleysingjar:
```sql
SELECT count(*) FROM public.feature_attributions_2026_08_pre_cc78 f
WHERE NOT EXISTS (SELECT 1 FROM public.predictions_2026_08_pre_cc78 p
                  WHERE p.fastnum = f.fastnum);            -- KRAFA: 0
```

### R3 — flokkun eignaþýðisins  ⚠ NÝTT, HART SKILYRÐI

```sql
CREATE TABLE public.properties_canonical_pre_cc78 AS
  SELECT fastnum, canonical_code, unit_family, is_residential, is_summerhouse
  FROM public.properties;
ALTER TABLE public.properties_canonical_pre_cc78 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.properties_canonical_pre_cc78 FROM anon, authenticated;
CREATE UNIQUE INDEX ON public.properties_canonical_pre_cc78 (fastnum);
```

**Sannreyning — nákvæm dreifing, ekki bara rowcount:**

```sql
SELECT count(*) FROM public.properties_canonical_pre_cc78;   -- KRAFA: 232887
SELECT canonical_code, count(*) FROM public.properties_canonical_pre_cc78
GROUP BY 1 ORDER BY 2 DESC;
```

| canonical_code | KRAFA n |
|---|---:|
| APT_FLOOR | 91.197 |
| EXCLUDE | 56.958 |
| APT_STANDARD | 33.614 |
| SFH_DETACHED | 19.610 |
| SUMMERHOUSE | 13.924 |
| ROW_HOUSE | 7.728 |
| SEMI_DETACHED | 4.335 |
| APT_BASEMENT | 3.592 |
| APT_ATTIC | 1.397 |
| APT_UNAPPROVED | 216 |
| APT_ROOM | 118 |
| APT_HOTEL | 104 |
| APT_SENIOR | 89 |
| APT_MIXED | 5 |
| **alls** | **232.887** |

```sql
SELECT count(*) FILTER (WHERE is_residential)  AS resi,       -- KRAFA: 162005
       count(*) FILTER (WHERE is_summerhouse)  AS summer,     -- KRAFA: 13924
       count(DISTINCT unit_family)             AS uf_distinct,-- KRAFA: 4
       count(*) FILTER (WHERE unit_family IS NULL) AS uf_null -- KRAFA: 42439
FROM public.properties_canonical_pre_cc78;
```

### R4–R9 — diskur og bókhald

| # | hlutur | aðgerð | sannreyning |
|---|---|---|---|
| R4 | `pipeline_config` | bóka orðrétt í flipp-audit | `model_version=iter4r_20260716` · `model_pred_anchor_ym=2026-08` · `sales_history_anchor_ym=2026-09` (3 lyklar) |
| R5 | `D:\model_artifacts\iter4r_20260716\` | ÓSNERT (skriftur neita að yfirskrifa) | `_manifest.json` les `data_sha256_16=aa2e191e750fd513` |
| R6 | `D:\training_data_v2.pkl` | afrit → `training_data_v2_pre_cc78.pkl` | sha bókað ÁÐUR en endurbyggt |
| R7 | `D:\properties_v2.pkl` | afrit → `properties_v2_pre_cc78.pkl` | mtime 2026-07-06 22:49, 49.248.213 bæti |
| R8 | kóði á `D:\` | afrit m/ tímastimpli | `classify_property.py.pre_cc78_20260803T112828Z` **er þegar til** (md5 `35c1cad66538eec64ab9d8f3a49825f2`); bæta við `build_training_data.py`, `rebuild_training_data.py` |
| R9 | `D:\cc78_frozen_cohort_v1.pkl` | **er rollback-eign, ekki bara mæling** — taka með í næturafrit | sha `c0e548cfddc4b1ff` |

> **`D:\` er EKKI git-repo.** R8 er sjálfstæð krafa; `git revert` nær ekki til
> `classify_property.py`, `build_training_data.py` né `rebuild_training_data.py`.

### Akkeri sem MÁ ALDREI HENDA (eldri, óskyld cc78)

`predictions_2026_07_pre_iter4r` · `predictions_pre_cc51` · `predictions_2026_04` ·
`predictions_iter3v2` · `feature_attributions_2026_07_pre_iter4r` ·
`feature_attributions_2026_04` · `feature_attributions_iter3v2` ·
`predictions_staging_cc51` · `postheiti_snapshot_pre_d3fix_20260706`

Þau bera `segment` með **gömlu** gildunum. Eftir R er sá dálkur ekki lengur
samanburðarhæfur við lifandi `properties.canonical_code` — **þekkt, ekki lagað**
(fasi 0 §4.5). Hver fyrirspurn sem joinar þau við `properties` á segmenti er röng.

---

## §2 FLIPP-RÖÐIN — hvað gerist og í hvaða röð

**Ekkert hér má keyra fyrr en §1 er allt grænt og arkitekt hefur gefið sér-GO.**

| # | þrep | tafla/hlutur | æft? |
|---|---|---|---|
| 0 | **R1–R9 staðfest** (§1) | — | — |
| 1 | universe-rebuild úr kandídat-artifacti → CSV í `precompute/exports/` | disk | **ÆFT** (júlí) |
| 2 | staging-töflur + COPY + hlið (rowcount, universe, checksum, bil-röðun, corr) | `predictions_cc78_staging`, `feature_attributions_cc78_staging` | **ÆFT** |
| 3 | **atómísk txn:** `SET TRANSACTION READ WRITE` → `session_replication_role='replica'` → `UPDATE predictions FROM staging` → `TRUNCATE+INSERT feature_attributions` | 2 töflur | **ÆFT** |
| 4 | **í SÖMU txn:** `pipeline_config` → `model_version`, `model_pred_anchor_ym` | 1 tafla | **ÆFT** |
| 5 | **í SÖMU txn:** `UPDATE properties SET canonical_code, unit_family, is_residential, is_summerhouse` | `public.properties` | **ÓÆFT** ⚠ §5 |
| 6 | **í SÖMU txn:** in-txn recheck FYRIR commit (§4) | — | **ÆFT** (án liðar 5) |
| 7 | COMMIT | — | — |
| 8 | **MV-refresh — FIMM, ekki einn** (§7) | semantic | **ÓÆFT** fyrir 4 af 5 ⚠ |
| 9 | kóðafastar: `model_quality_eval.py` (§6) | disk | **ÓÆFT** |
| 10 | app-hliðar: `/stilla`-fjölskyldur, `/markadur/modelstada` prósa (§6) | Vercel | **ÓÆFT** |

> **Þrep 3–6 verða að vera EIN transaction.** Ef `properties.canonical_code` og
> `predictions.segment` fara í sitt hvora txn er tímabil þar sem
> `v_properties.canonical_code` og `v_current_predictions.segment` stangast á —
> og `adjust-valuation` skilar 400 fyrir eignir sem eru í hvorugu ástandinu.

---

## §3 ROLLBACK-RÖÐIN — nákvæm, í þessari röð

Aldrei sjálfvirk. **Bóka ástæðu ÁÐUR en keyrt er.**

```
 0. HALT — ákvörðun eiganda. Bóka ástæðu í flipp-audit ÁÐUR en skref 1 hefst.

 1. psycopg2 á transaction pooler (port 6543).
    FYRSTA setning hverrar txn:  SET TRANSACTION READ WRITE

 2. SET LOCAL statement_timeout = '300s'
    SET LOCAL session_replication_role = 'replica'      -- FK-triggerar af

 3. TRUNCATE public.predictions;
    INSERT INTO public.predictions
      SELECT * FROM public.predictions_2026_08_pre_cc78;

 4. TRUNCATE public.feature_attributions;
    INSERT INTO public.feature_attributions
      SELECT * FROM public.feature_attributions_2026_08_pre_cc78;

 5. UPDATE public.properties p                          -- ⚠ ÓÆFT ÞREP, sjá §5
       SET canonical_code = s.canonical_code,
           unit_family    = s.unit_family,
           is_residential = s.is_residential,
           is_summerhouse = s.is_summerhouse
       FROM public.properties_canonical_pre_cc78 s
      WHERE s.fastnum = p.fastnum
        AND (p.canonical_code IS DISTINCT FROM s.canonical_code
          OR p.unit_family    IS DISTINCT FROM s.unit_family
          OR p.is_residential IS DISTINCT FROM s.is_residential
          OR p.is_summerhouse IS DISTINCT FROM s.is_summerhouse);

 6. pipeline_config UPSERT:
       model_version        = 'iter4r_20260716'
       model_pred_anchor_ym = '2026-08'
    (sales_history_anchor_ym er EKKI okkar — snerta hana ALDREI hér)

 7. IN-TXN RECHECK FYRIR COMMIT  — §4. Falli eitthvað: conn.rollback().

 8. COMMIT

 9. MV-refresh — FIMM (§7). Skylda, ekki valfrjálst.

10. Kóði á diski (R8):
       Copy-Item D:\classify_property.py.pre_cc78_20260803T112828Z `
                 -Destination D:\classify_property.py -Force
       python D:\classify_property.py          # 40 próf, exit 0
    + build_training_data.py, rebuild_training_data.py úr sínum afritum.

11. model_quality_eval.py fastar aftur í R4-bókuðu gildin (§6).

12. SANNPRÓFUN — mæld, ekki treyst (§8).

13. UI-sannprófun á prod (§8).
```

---

## §4 IN-TXN RECHECK — fyrir commit, í BÁÐAR áttir

Sama fyrirspurn gildir fyrir flipp (þrep 6) og rollback (þrep 7); aðeins vænt gildi
snúast við.

```sql
SELECT
  (SELECT count(*) FROM public.predictions)                                  AS n_pred,
  (SELECT count(*) FROM public.predictions WHERE model_version = %(mv)s)     AS n_mv,
  (SELECT count(*) FROM public.feature_attributions)                         AS n_fa,
  (SELECT count(*) FROM public.feature_attributions f
     WHERE NOT EXISTS (SELECT 1 FROM public.predictions p
                       WHERE p.fastnum = f.fastnum))                         AS n_orph,
  (SELECT count(*) FROM public.properties)                                   AS n_props,
  (SELECT count(*) FROM public.properties WHERE canonical_code='APT_STANDARD') AS n_apt_std,
  (SELECT count(*) FROM public.properties WHERE is_summerhouse)              AS n_summer,
  (SELECT count(*) FROM public.properties p
     JOIN public.properties_canonical_pre_cc78 s USING (fastnum)
    WHERE p.canonical_code IS DISTINCT FROM s.canonical_code)                AS n_frav;
```

| stærð | eftir ROLLBACK | eftir FLIPPI |
|---|---:|---:|
| `n_pred` | 167.503 | 167.503 |
| `n_mv` (`iter4r_20260716` / ný útgáfa) | 167.503 | 167.503 |
| `n_fa` | 1.675.030 | = CSV-rowcount |
| `n_orph` | 0 | 0 |
| `n_props` | 232.887 | 232.887 |
| **`n_apt_std`** | **33.614** | **≈ 206** (cc76 T17) |
| `n_summer` | 13.924 | **13.924** (óbreytt — sértaxonómíu-vörn) |
| **`n_frav`** | **0** | **≈ 58.500** (fasi 0 §2, cc76 T17: 58.561) |

> `n_apt_std` og `n_frav` eru skýrustu merkin um hvorum megin kerfið stendur.
> `n_summer` **verður** að vera óbreytt í báðar áttir — hreyfist hún er
> sértaxonómíu-vörnin brotin (fasi 1B §3).

---

## §5 ÆFT vs ÓÆFT — og hvað er hægt að æfa án þess að snerta prod

### Staðan

| þrep | æft | heimild |
|---|---|---|
| snapshot / staging / COPY / hlið | **JÁ** | `flip_iter4r.py` júlí, `phase_snapshot`+`phase_staging` |
| atómísk txn á `predictions` + `feature_attributions` | **JÁ** | `flip_iter4r.phase_flip` |
| `pipeline_config` í sömu txn | **JÁ** | sama |
| rollback á þeim tveimur töflum | **JÁ** | `flip_iter4r.rollback()`, bókað „æfð aðgerð" |
| **`UPDATE properties.canonical_code` (þrep 5)** | **NEI** | **aldrei framkvæmt í neinu flippi** |
| **MV-refresh á fjórum properties-MV** | **NEI** | aðeins `v_model_vs_sold_by_hood` hefur verið endurnýjaður í flippi |

### Er æfing möguleg án þess að snerta prod?

**Svarið er blandað og fer eftir því hversu langt á að ganga.**

**Stig 1 — FULLKOMLEGA READ-ONLY, engin skrif, engin lásar-áhætta.**
Rollback-UPDATE-ið hefur nákvæma SELECT-hliðstæðu. Hún sannreynir join-cardinality,
fjölda snertra raða og að engin röð týnist — allt án þess að skrifa:

```sql
-- (a) join er 1:1 og nær yfir allt þýðið
SELECT (SELECT count(*) FROM public.properties)                       AS n_props,
       (SELECT count(*) FROM public.properties_canonical_pre_cc78)    AS n_snap,
       (SELECT count(*) FROM public.properties p
          JOIN public.properties_canonical_pre_cc78 s USING (fastnum)) AS n_join;
-- KRAFA: allar þrjár == 232887

-- (b) hve margar raðir MYNDI UPDATE-ið snerta
SELECT count(*) FROM public.properties p
  JOIN public.properties_canonical_pre_cc78 s USING (fastnum)
 WHERE p.canonical_code IS DISTINCT FROM s.canonical_code
    OR p.unit_family    IS DISTINCT FROM s.unit_family
    OR p.is_residential IS DISTINCT FROM s.is_residential
    OR p.is_summerhouse IS DISTINCT FROM s.is_summerhouse;
-- fyrir flipp: 0    ·    eftir flipp: ≈ 58.500

-- (c) niðurstaðan sem UPDATE-ið myndi skilja eftir
SELECT s.canonical_code, count(*) FROM public.properties p
  JOIN public.properties_canonical_pre_cc78 s USING (fastnum) GROUP BY 1 ORDER BY 2 DESC;
-- KRAFA: nákvæmlega taflan í §1/R3
```

> **Stig 1 er ekki bara mögulegt heldur SKYLDA** — það sannar allt nema skrifleiðina
> sjálfa, kostar ekkert og má keyra hvenær sem er.

**Stig 2 — æfing á skrifleiðinni í einangruðu skema (skrifar í prod-DB, en snertir
ekki `public.properties`).**

```sql
CREATE SCHEMA IF NOT EXISTS cc78_rehearsal;
REVOKE ALL ON SCHEMA cc78_rehearsal FROM anon, authenticated;
CREATE TABLE cc78_rehearsal.properties (LIKE public.properties INCLUDING ALL);
INSERT INTO cc78_rehearsal.properties SELECT * FROM public.properties;
-- keyra ÞREP 5 orðrétt gegn cc78_rehearsal.properties, mæla rowcount fyrir/eftir
DROP SCHEMA cc78_rehearsal CASCADE;   -- eftir æfingu
```
`cc78_rehearsal` er **ekki exposed schema**, svo PostgREST birtir hana ekki. Bætum
`REVOKE` við samt (CLAUDE.md-reglan í anda, þótt hún nefni `public`).
Kostur: núll áhætta á `public.properties`. Galli: minna trútt (aðrir lásar, önnur
tölfræði, engir sömu triggerar nema `INCLUDING ALL` nái þeim).

**Stig 3 — æfing gegn RAUNTÖFLUNNI með þvinguðu ROLLBACK.** Trúasta prófið: réttir
lásar, réttar vísitölur, réttur rowcount. Skrifar WAL en skilur ekkert eftir.

```python
conn.autocommit = False
cur.execute("SET TRANSACTION READ WRITE")
cur.execute("SET LOCAL statement_timeout = '120s'")
cur.execute("SET LOCAL idle_in_transaction_session_timeout = '60s'")
cur.execute(UPDATE_ÞREP_5)
print("snertar raðir:", cur.rowcount)          # KRAFA: 0 fyrir flipp
cur.execute(RECHECK_SQL); print(cur.fetchone())
conn.rollback()                                 # ENGIN commit-leið í skriftunni
```
**Skilyrði:** skriftan má ekki innihalda `conn.commit()` yfirleitt · keyrt utan
háannatíma · `idle_in_transaction_session_timeout` sett svo dautt session losi lásinn.

### Ákvörðun — STAÐFEST AF ARKITEKT 2026-08-03

| stig | staða | tímasetning |
|---|---|---|
| **1 — read-only SELECT-hliðstæða** | **SKYLDA** | **fyrir fyrstu þjálfunarkeyrslu** (§10.1 iii) |
| 2 — einangrað `cc78_rehearsal`-skema | valkvætt, **þarf sitt GO** | fyrir flipp |
| 3 — þvingað ROLLBACK gegn rauntöflunni | **trúasta æfingin á þrepi 5**, þarf sitt GO | fyrir flipp |

Stig 1 skrifar ekkert, tekur enga lása og kostar ekkert — en það **krefst þess að R3
sé þegar til** (fyrirspurnirnar joina gegn `properties_canonical_pre_cc78`). Röðin er
því **R3 → stig 1 → fyrsta þjálfunarkeyrsla**.

Stig 2 og 3 eru **DB-skrif og þurfa sitt eigið GO** — þau voru ekki hluti af fasa 1
og eru það ekki heldur sjálfkrafa hluti af fasa 2.

---

## §6 KÓÐAFASTAR SEM LIFA FLIPP AF — og verða að snúast við í rollback

| skrá | fasti | gildi í dag (rollback-mark) |
|---|---|---|
| `scripts/model_quality_eval.py:123` | `FREEZE_ANCHOR_YM` | `"2026-08"` |
| `:124` | `PRED_VALUATION_YM` | `"2026-07"` |
| `:166` | `BASELINE` | `{"mape":7.00,"cov80":73.1,"cov95":92.7}` |
| `:131` | `ADAPTER_MODEL_VERSION` | `"iter4_final_v1"` (pöruð braut þegar dauð) |
| `app/api/adjust-valuation/route.js:8-9` | `APT_CODES` / `SFH_CODES` | óbreyttar — **en fjölskyldan sem eign lendir í breytist** |
| `app/markadur/modelstada/page.js:212` | harðkóðuð prósa | „81,2 % ±2,7 pp (n=848)", „næsta þekju-mæling ágúst 2026" |
| `app/um/page.js` | `/um#adferdafraedi` | **ÞEGAR ÚRELT** (iter3v2) — fyrirliggjandi, ekki cc78 |

`model_version` og OOS-gluggar eru **rétt gerðir** (lesnir úr `pipeline_config` +
manifest af diski, cc47-rótarfix). Aðeins akkeris- og viðmiðunarfastarnir eru
harðkóðaðir.

> **`/stilla`-áhrifin eru ekki kóðafasti heldur gagnaáhrif.** 28.063 eignir skipta um
> bílskúrs-fjölskyldu; deildar slóðir með `garage_apt` skila **HTTP 400**
> (`route.js:44-47`). Rollback þreps 5 lagar það sjálfkrafa. **Ef flipp er látið
> standa þarf sér-ákvörðun um hvað gerist við þessar slóðir** — það er
> vöruákvörðun, ekki rollback-atriði.

---

## §7 MV-REFRESH — FIMM, EKKI EINN  ⚠ GAT Í ELDRI ÁÆTLUN

`flip_iter4r.py:252` endurnýjar **aðeins** `semantic.v_model_vs_sold_by_hood`. Það
var rétt þegar flipp snerti aðeins spár. cc78 breytir `properties.canonical_code`
og þá bætast fjórir við (mælt með `pg_get_viewdef` yfir öll 13 MV):

| MV | les | skylda eftir cc78 |
|---|---|---|
| `semantic.v_model_vs_sold_by_hood` | `predictions` | **JÁ** (var þegar) |
| `semantic.v_hood_heat` | `canonical_code`, `is_summerhouse` | **JÁ — NÝTT** |
| `semantic.v_street_directory` | `properties`, `canonical_code`, `is_summerhouse` | **JÁ — NÝTT** |
| `semantic.v_street_activity` | `properties` | **JÁ — NÝTT** |
| `semantic.v_sveitarfelag_lookup` | `properties` | **JÁ — NÝTT** |
| `semantic.v_summerhouse_market` | `is_summerhouse` | mælt óbreytt (sértaxonómíu-vörn) — endurnýja samt |
| hin sjö | `sales_history` o.fl. | nei |

```sql
SET default_transaction_read_only = off;
SET work_mem = '64MB';
SET statement_timeout = '600s';
REFRESH MATERIALIZED VIEW CONCURRENTLY semantic.v_model_vs_sold_by_hood;
REFRESH MATERIALIZED VIEW CONCURRENTLY semantic.v_hood_heat;
REFRESH MATERIALIZED VIEW CONCURRENTLY semantic.v_street_directory;
REFRESH MATERIALIZED VIEW CONCURRENTLY semantic.v_street_activity;
REFRESH MATERIALIZED VIEW CONCURRENTLY semantic.v_sveitarfelag_lookup;
REFRESH MATERIALIZED VIEW CONCURRENTLY semantic.v_summerhouse_market;
```

> **`CONCURRENTLY` krefst UNIQUE index á hverjum MV.** Aðeins
> `v_model_vs_sold_by_hood` er sannreyndur með slíkan. **Athuga hina fimm ÁÐUR en
> flipp hefst** — annars fellur skipunin og MV situr stöðnuð:
> ```sql
> SELECT c.relname, count(i.indexrelid) FILTER (WHERE ix.indisunique) AS uniq_idx
> FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
> LEFT JOIN pg_index ix ON ix.indrelid=c.oid
> LEFT JOIN pg_class i ON i.oid=ix.indexrelid
> WHERE n.nspname='semantic' AND c.relkind='m' GROUP BY 1 ORDER BY 1;
> ```
> Án unique index: sleppa `CONCURRENTLY` (læsir MV meðan á stendur) — meðvituð
> ákvörðun, ekki þögul.

`semantic._sales_base` er **view, ekki MV** — engin refresh, en agentar mega aldrei
lesa hana beint.

---

## §8 SANNPRÓFUN EFTIR ROLLBACK — mæld, ekki treyst

```bash
python D:\verdmat-is\app\scripts\model_quality_eval.py --dryrun
```

| stærð | KRAFA |
|---|---|
| `sample_scope='holdout30'` n | **847** |
| cov80 | **81,1098 %** |
| MAPE | **9,9552 %** |
| bias | **−2,5598 %** |
| `sample_scope='fresh_edge'` | n vex með tíma — bera við bókaða línu í fasa 1D §1, **ekki fast gildi** |

```bash
python D:\build_frozen_cohort_cc78.py --verify-only
# KRAFA: öll 14 hlið græn (kohorturinn er sjálfstæð sannprófun á spánum)
```

**DB:**
```sql
SELECT canonical_code, count(*) FROM public.properties GROUP BY 1 ORDER BY 2 DESC;
-- KRAFA: nákvæmlega taflan í §1/R3
SELECT key, value FROM public.pipeline_config ORDER BY key;
-- KRAFA: model_version=iter4r_20260716 · model_pred_anchor_ym=2026-08
```

**UI á prod:**

| próf | KRAFA |
|---|---|
| `/eign/2013952` (Álftamýri 39) | ber `APT_STANDARD`, ekki `ROW_HOUSE` |
| `/eign/2013952/stilla` með `garage_apt` | **HTTP 200**, ekki 400 |
| `/markadur/modelstada` | hleðst, þekjulína óbreytt |
| `/leit` | flokkarnir svara |

---

## §9 HVAÐ ROLLBACK NÆR EKKI TIL

| hlutur | af hverju | viðbragð |
|---|---|---|
| `model_metrics`-raðir frá cc78-líkani | vélin skrifar SÖGU, ekki ástand | láta standa — þær bera sinn `model_version` og aðgreinast sjálfar |
| `pipeline_runs` / `steps` | sama | láta standa |
| MV-innihald milli skrefa 8 og 9 | MV stöðnuð þar til refresh | skref 9 er **skylda** |
| `predictions_rent*` | leigu-brautin ósnert af cc78 | engin aðgerð |
| Vercel-útgáfur | UI fer sér | sér-revert ef UI var snert |
| Deildar `/stilla`-slóðir sem skiluðu 400 meðan flipp stóð | notandaupplifun þegar orðin | ekkert tæknilegt; vöruákvörðun |

---

## §10 STAÐFESTING ARKITEKTS — SKILYRÐI FYRIR ÞJÁLFUN

> **Þessi runbók skal lesin og staðfest af arkitekt ÁÐUR en fyrsta þjálfunarkeyrsla
> fasa 2 hefst.** Ekki nóg að hún sé skrifuð.
>
> Rökin: fyrsta þjálfunarkeyrslan er sjálf skaðlaus (hún skrifar aðeins í nýja
> artifact-möppu), en hún er upphaf keðju sem endar í flippi. Verði forsendurnar í
> §1 ekki teknar **áður**, er hætt við að R1/R2/R3 séu tekin eftir að
> `public.predictions` hefur þegar verið snert — og þá er þetta skjal gagnslaust.
>
> **Staðfestingarreitur — FYLLTUR.**
>
> | liður | staðfest | dags |
> |---|---|---|
> | §1 R1–R9 forsendur, þ.m.t. handahófsúrtakið gegn kohortnum | ☑ **JÁ** | 2026-08-03 |
> | §2 flipp-röðin, þ.m.t. að þrep 3–6 séu EIN txn | ☑ **JÁ** | 2026-08-03 |
> | §3 rollback-röðin | ☑ **JÁ** | 2026-08-03 |
> | §5 að þrep 5 sé óæft, og hvaða æfingarstig verður keyrt | ☑ **JÁ** | 2026-08-03 |
> | §7 að MV-listinn sé fimm/sex, ekki einn | ☑ **JÁ** | 2026-08-03 |
> | §10 að þjálfun megi hefjast | ☑ **JÁ**, að uppfylltu skilyrði (iii) | 2026-08-03 |
>
> **Staðfest af arkitekt 2026-08-03.**

### §10.1 ÞRJÁR SÉRSTAKAR STAÐFESTINGAR — orðréttar

**(i) MV-fundurinn er réttur og mikilvægur.**
> Fimm MV lesa `properties`; `flip_iter4r.py` endurnýjar aðeins einn. Það var rétt
> áður, þegar flipp snerti aðeins spár — **en cc78 snertir `properties`.**

Afleiðing: §7 er bindandi hluti flipp-raðarinnar (þrep 8), ekki eftiráhugsun.
Eftirtékkið á UNIQUE index (§7) skal keyrt **áður** en flipp hefst, svo
`CONCURRENTLY` falli ekki og skilji MV eftir stöðnuð.

**(ii) Þrep 3–6 í EINNI transaction er SKILYRÐI, ekki ábending.**
> Tímabil þar sem `canonical_code` og `predictions.segment` eru í sitt hvora
> transaction er ástand sem `adjust-valuation` getur ekki þjónað.

Afleiðing: falli eitthvert þrepanna fjögurra skal **öll** transactionin rúlla til
baka. Það er engin ásættanleg millistaða. `flip_iter4r.phase_flip`-mynstrið
(in-txn recheck FYRIR commit) gildir óbreytt og nær nú líka yfir þrep 5.

**(iii) Æfingarstig 1 er SKYLDA fyrir fyrstu þjálfunarkeyrslu.**
> Read-only SELECT-hliðstæðan (§5, stig 1) skal keyrð áður en fyrsta
> þjálfunarkeyrsla hefst. **Stig 2 og 3 þurfa sitt eigið GO og eru ekki hluti af
> fasa 1.**

Afleiðing: eina útistandandi skilyrðið fyrir fasa 2. Stig 1 skrifar ekkert, tekur
enga lása og má keyra hvenær sem er — en niðurstaðan skal bókuð:

| fyrirspurn (§5, stig 1) | KRAFA fyrir flipp |
|---|---|
| (a) `n_props` = `n_snap` = `n_join` | allar þrjár **232.887** |
| (b) raðir sem UPDATE myndi snerta | **0** |
| (c) `canonical_code`-dreifing gegnum joinið | nákvæmlega taflan í §1/R3 |

> ⚠ **(a) og (b) krefjast þess að R3 sé þegar til.** Röðin er því:
> **R3 → æfingarstig 1 → fyrsta þjálfunarkeyrsla.** R3 er `CREATE TABLE AS` (DB-skrif)
> og þarf sitt GO sem hluti af fasa 2.

### §10.2 STAÐA — hvað má og hvað má ekki

| | staða |
|---|---|
| Runbók lesin og staðfest | ✅ 2026-08-03 |
| Fasi 2 heimill í grundvallaratriðum | ✅ |
| **Útistandandi fyrir fyrstu þjálfunarkeyrslu** | **R3 (m/ GO) → æfingarstig 1 → bóka (a)(b)(c)** |
| Æfingarstig 2 og 3 | ⛔ þurfa sitt eigið GO |
| Flipp | ⛔ þarf sitt eigið GO, eftir að R1–R9 eru öll græn |

**Ekkert í fasa 2 hefst fyrr en eigandi er við borðið.**

### §10.3 FRAMKVÆMDARBÓKUN — R3 og æfingarstig 1  *(append 2026-08-03, cc78 fasi 2 skref 1)*

> Bókun skv. §10.1 (iii). **Append — engum fyrri texta breytt.**

#### R3 keyrt — `public.properties_canonical_pre_cc78`

`2026-08-03 20:32:42Z` · logg `D:\cc78_r3_create.log` · **232.887 raðir, COMMIT**

`SET TRANSACTION READ WRITE` fyrst · RLS + `REVOKE` + unique index í **sömu aðgerð**
og taflan varð til · in-txn rowcount-tékk **fyrir** commit · `public.properties`
aðeins LESIN. Ellefu hlið, öll PASS:

| hlið | mælt |
|---|---|
| rowcount == 232.887 | 232.887 ✔ |
| `canonical_code`-dreifing == §1/R3 | 14 gildi, summa 232.887 ✔ |
| `is_residential` == 162.005 | 162.005 ✔ |
| `is_summerhouse` == 13.924 | 13.924 ✔ |
| `unit_family` distinct == 4 · NULL == 42.439 | 4 · 42.439 ✔ |
| `fastnum` einkvæmt, engin NULL | 0 null, 232.887 distinct ✔ |
| **afrit == lifandi tafla, röð fyrir röð** | **frávik 0** ✔ |
| RLS virkt | `relrowsecurity=true` ✔ |
| **réttindi `anon`/`authenticated`** | **engin** ✔ (mælt gegnum `role_table_grants`, ekki treyst á `REVOKE`-eintakið — cc52) |

#### Æfingarstig 1 keyrt — read-only

`2026-08-03 21:19:58Z` · logg `D:\cc78_stig1_rehearsal.log` ·
`set_session(readonly=True)` · **engin skrif, engir lásar**

| # | fyrirspurn | KRAFA | **MÆLT** |
|---|---|---|---|
| **(a)** | `n_props` = `n_snap` = `n_join` | allar þrjár 232.887 | **232.887 / 232.887 / 232.887** ✔ |
| (a+) | munaðarleysingjar í báðar áttir + tvítök í snapshot | 0 | **0 / 0 / 0** ✔ |
| **(b)** | raðir sem rollback-UPDATE myndi snerta | **0** | **0** ✔ |
| (b+) | sundurliðað per dálk (`canonical_code` / `unit_family` / `is_residential` / `is_summerhouse`) | 0 hvert | **0 / 0 / 0 / 0** ✔ |
| **(c)** | `canonical_code`-dreifing gegnum joinið | nákvæmlega §1/R3 | **14 gildi, summa 232.887** ✔ |

(a+) og (b+) eru viðbætur umfram §5: join-fjöldi einn dylur 1:N-samband, og samtala
núll dylur að einn dálkur víki á móti öðrum. Bæði voru mæld sér.

#### Aukamæling — keyrsluáætlun rollback-UPDATE-sins (`EXPLAIN`, ekki keyrt)

```
Update on properties p  (cost=8560.96..77519.34 rows=0 width=0)
  ->  Hash Join  (cost=8560.96..77519.34 rows=218635 width=29)
        Hash Cond: (p.fastnum = s.fastnum)
        Join Filter: (canonical_code / unit_family / is_residential / is_summerhouse
                      IS DISTINCT FROM …)
        ->  Seq Scan on properties p                       (rows=233375)
        ->  Hash -> Seq Scan on properties_canonical_pre_cc78 s (rows=232887)
```

Tvennt til að vita fyrir flippið:

1. **Áætlunin er hash join með seq scan báðum megin.** Unique index á snapshotinu er
   ekki notaður — það er rétt val fyrir fullt töflu-join og þarf ekki lagfæringar.
   Kostnaður er hóflegur; UPDATE-ið er ekki langvarandi lás.
2. **Áætlaðar raðir gegnum `Join Filter` eru 218.635 en raunfjöldi er 0.** Postgres
   getur ekki áætlað fylgni `IS DISTINCT FROM` yfir tvær töflur. Þetta er
   **tölfræðiskekkja í áætlun, ekki villa** — en hún þýðir að kostnaðartölur
   `EXPLAIN` eru stórlega ofmetnar fyrir rollback-áttina (0 raðir) og nokkurn veginn
   réttar fyrir flipp-áttina (≈58.500 raðir). Ekki nota `EXPLAIN`-kostnað sem
   tímamat á rollback.

#### Staða eftir bókun

| | staða |
|---|---|
| R3 | ✅ til, sannreynt, RLS + engin anon-réttindi |
| Æfingarstig 1 | ✅ grænt — **(a)(b)(c) bókuð hér að ofan** |
| **Skilyrði §10.1 (iii)** | ✅ **UPPFYLLT** |
| **Fyrsta þjálfunarkeyrsla** | ✅ **heimil** (þarf samt sér-GO eiganda) |
| Æfingarstig 2 og 3 | ⛔ sitt eigið GO |
| R1, R2, R4–R9 | ⛔ ógerð — **skilyrði fyrir flipp, ekki fyrir þjálfun** |
| Flipp | ⛔ sitt eigið GO, eftir að R1–R9 eru öll græn |

> **Það sem stig 1 sannar EKKI:** skrifleiðina sjálfa. `UPDATE`-setningin hefur aldrei
> verið keyrð gegn neinni töflu. Stig 2 (einangrað skema) og stig 3 (þvingað
> `ROLLBACK` gegn rauntöflunni) standa óhreyfð og þurfa sitt eigið GO áður en flipp
> er heimilað.

### §10.4 FLIPP-UNDIRBÚNINGSBÓKUN cc98 — kandídat útnefndur  *(append 2026-08-05, cc98; BÓKAÐ, EKKI FRAMKVÆMT)*

> Append skv. GO arkitekts 05.08.2026 (sam-rýni eftir skref 3.0/A/B/D1/D2).
> **Engum fyrri texta breytt.**

**Flipp-kandídat: `iter4r_20260805_reglaR_strukt`** (D2, 156 features; manifest
merkt `flip_status`, sha `f0bb1e01eac9119b`). `iter4r_20260804_reglaR` (154f)
**fær aldrei flipp** — merkt í manifesti (sha `010c25f1d0954314`).

Viðbótarskilyrði við flipp-röðina (§2), framkvæmast VIÐ flipp og ekki fyrr:

1. **Trainer-skráin færist í D2-ástand og committast VIÐ flipp:**
   `precompute/retrain_sales_model.py` — `n_ibudareininga` + `flm_hlutfall` úr
   EXCLUDE, `EXPECTED_N_FEATURES = 156`, Int32→float64 vörpunin. Nákvæmt diff
   er varðveitt sem munur afritanna `.cc98_R154_20260805T093342Z` (154-ástandið,
   sha `3a35a13dc847b01b`, situr á diski NÚNA) og keyrslunnar sem þjálfaði
   kandídatinn. Þar til flippað er stendur skráin í 154-ástandinu.
2. **Alheims-skorunin (`rebuild_predictions_iter4.py`) fær hms-lags-innspýtingu:**
   `n_ibudareininga` + `flm_hlutfall` per fastnúmer úr `hms_classification_v1.pkl`
   (sha-hliðað `16d78e39d57cfcad`) inn í X — annars train/serve-skekkja á nýju
   featurunum tveimur. Sannreynt í cc98-mati (D2-eval sprautaði nákvæmlega svona).
3. Öll fyrri skilyrði runbókarinnar standa ÓBREYTT: R1-frysting FYRIR flipp
   (§1, hart skilyrði), þrep 3–6 í EINNI transaction (§2/§10.1 ii), fimm/sex
   MV (§7), raunprófun eftir á (§8).

Level-fyrirvarinn sem GO-bréf skrefs 4 skal bera BERUM ORÐUM (krafa arkitekts):
holdout30-heildarbias kandídatsins er **+2,46 % (vanmat)** — dæmt ásættanlegt
verð í sam-rýni (|2,45| < |3,39| gamla ofmatsins á (b), jaðar-rek nær leyst) —
og cov80-myndin í framreiðsluramma ber miss↑ 2,3× miss↓ (cc98 3.1-audit).
**Eigandi kvittar þetta sérstaklega í GO-bréfinu.**

### §10.5 LEIÐRÉTTING Á §3 ÞREPI 6 — þriðji pipeline_config-lykillinn  *(append 2026-08-06, cc104, fundur æfingarstigs 3)*

> **Append — engum fyrri texta breytt.** Flippið skrifar ÞRJÁ lykla í
> `pipeline_config`: `model_version`, `model_pred_anchor_ym` og **NÝJAN lykil
> `calibration_version`** (GO-bréf cc98 §6 þrep 3–6). §3 þrep 6 telur aðeins
> fyrri tvo. Rollback verður því einnig að keyra:
>
> ```sql
> DELETE FROM public.pipeline_config WHERE key = 'calibration_version';
> ```
>
> annars situr serving_v1-merkið eftir á iter4r_20260716-ástandinu og lýgur til
> um kvörðun spánna. Fullbúið rollback-SQL m/þessari leiðréttingu:
> `D:\cc104_flip_rollback.sql` (skrifað FYRIR flipp). Æfingarstig 3 keyrt grænt
> gegn rauntöflunum 2026-08-06T12:11Z (`D:\cc104_stage3_rehearsal.log`) —
> endurheimt sannreynd m/checksum == R1/R2 og lifandi ástand óbreytt eftir æfingu.

---

## §11 HEIMILDIR

`docs/fable_prep/audits/AGUST_ENDURTHJALFUN_FASI0_CC78_20260803T110155Z.md` §5 ·
`…FASI1A…112828Z.md` · `…FASI1B…120051Z.md` · `…FASI1C…121052Z.md` §9 ·
`…FASI1D…121822Z.md` §8 · `docs/RETRAIN_RUNBOOK.md` §5 ·
`precompute/flip_iter4r.py` · `HMS_MOTSOGN_CC76_20260803T104446Z.md` T17
