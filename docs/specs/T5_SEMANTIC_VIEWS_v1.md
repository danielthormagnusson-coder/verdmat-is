# T5 — SEMANTIC VIEWS v1 (DRAFT, un-tracked)

**Staða**: HÖNNUNARDRÖG — ekkert af þessu hefur verið keyrt gegn Supabase.
Creation er aðskilið gated skref með `apply_migration` eftir yfirferð Danna.

**Dagsetning**: 2026-06-11
**Grunnur**: T5 könnunarfasi sama dag (read-only, Supabase MCP). Allar tölur
hér að neðan eru empírískar úr þeirri könnun, ekki forsendur.
**Hlutverk skjalsins**: (a) implementation-spec fyrir creation-skrefið,
(b) fyrsti hluti knowledge-pakka expert-agentsins — caveats-blokkirnar eru
first-class deliverable og eiga að flytjast beint í SKILL.md agentsins síðar.

---

## 0. Empírískur grunnur (samantekt könnunar)

| Staðreynd | Gildi | Afleiðing í hönnun |
|---|---|---|
| `sales_history` | 173.867 raðir, 2006-05-09 → 2026-04-17, verð í HEILUM kr | data_through-stimpill; ekki þús.kr eins og hrá kaupskrá |
| ONOTHAEFUR-leki | 420 raðir með onothaefur=1 (þar af 170 í 2025, 120 í 2026) | hörð `onothaefur = 0` sía í hverju viewi |
| Join sales↔properties | 100% á fastnum; matsvæði 99,89%, postnr 99,98% | properties er eina geo-uppsprettan, engin önnur þörf |
| Götur | 17.805 distinct; 2.619 nöfn í >1 sveitarfélagi | lykill = gata × sveitarfélag (24.322 pör) |
| Heimilisfang-kynslóðir | D3-recovery raðir með `"Gata 28   (Gata)"`-form + trailing whitespace í sveitarfelag | sviga-strip + btrim í normaliseringu |
| Þéttleiki gata (2020+, resid, clean) | 4.052 sellur, median 6; 86% sala á götum ≥10 | götu-views aðeins pooled fjölára + n-gat ≥5 |
| Þéttleiki matsvæða | 184 sellur, median 140/4,5 ár; ~80 með ≥30/ár | árstrend ber ~helming, ársfjórðungar bara topp |
| Þéttleiki póstnr | 153 sellur, median 44 | fallback-lag |
| Blöndun fjölbýli/sérbýli | 677/1.455 götur ≥10 blanda; 253 ≥20% minnihluti | per-tegund grouping sets í verð-views |
| Nýbyggingar | 17,2% sala 2020+ (byggar ≥ söluár−2) | is_newbuild flag alls staðar; útilokanlegt af consumer |
| Sumarhús | is_residential=false, eigin flagg; 2.320 sölur 2020+ | eingöngu í v_summerhouse_market |
| Verð/m² halar | p01 130þ., p99 1.104þ. kr/m² (2020+) | per-árs percentile-trim flagg í grunnviewi |
| Tvítekningar | 76 af 173.447 (fastnum, dags) | hverfandi; engin dedup-meðhöndlun |
| predictions (iter4) | 167.503; 96,2% þekja á íbúðareignum | v_model_vs_sold_by_hood gerlegt |

**Mikilvægasta semantíska staðreyndin**: `sales_history` er AFLEIDD undirmengi
(pairs-leidd, arm's-length, single-fastnum) — ekki ófiltruð kaupskrá. Full
kaupskrá (~228K m. 23% ONOTHAEFUR) er eingöngu local á `D:\kaupskra.csv`.
Fyrir verð- og veltugreiningar á markaðsverði er undirmengið einmitt rétta
mengið; fyrir „heildarfjölda þinglýsinga" spurningar er það EKKI rétta mengið.

---

## 1. Arkitektúr

### 1.1 Schema: `semantic` (SAMÞYKKT tillaga Danna — með einni útfærslunótu)

Ég er sammála dedicated schema, og rökin eru sterkari en bara snyrtimennska:

1. **Grant-mörk fyrir agent-role**: framtíðar read-only role expert-agentsins
   fær `USAGE ON SCHEMA semantic` + `SELECT` á view-in — og EKKERT á public.
   Einn GRANT-flötur, default-deny á allt annað, sama heimspeki og Group B
   column-lockout.
2. **PostgREST-einangrun**: `semantic` er ekki í exposed-schemas config →
   view-in leka ekki sjálfkrafa út um REST-lagið. Ef mælaborðið á síðar að
   lesa eitthvert þeirra er það meðvituð ákvörðun (bæta schema í config eða
   spegla valin views í public), ekki sjálfgefin hegðun.
3. **Nafnrýmis-hreinlæti**: agentinn á að geta sagt „allt sem þú mátt snerta
   er í semantic.*" — ekkert táknrænt rugl við 23 töflur í public.

**Útfærslunóta (frávik frá Group B mynstri, meðvitað)**: Group B views í
public eru `security_invoker = true` af því neytandinn er anon í gegnum
PostgREST og RLS á að gilda. Hér legg ég til **venjuleg owner-rights views**
(security_invoker = false, default). Ástæða: þá þarf agent-role-ið aðeins
SELECT á view-unum sjálfum en ekki á undirliggjandi public-töflunum — sem er
nákvæmlega aðgangslíkanið sem við viljum (agentinn sér aggregates, ekki
hráar töflur, nema það sé sérstaklega veitt). Trade-off: view-eigandinn
(postgres) bypassar RLS á base-töflunum — það er í lagi því öll base-gögnin
hér eru þegar public-read hvort eð er. **Opin spurning #1 staðfestir þetta.**

### 1.2 Eitt innra grunnview + harðkóðun í hverju viewi

Götunormaliseringin (tvöfalt regexp + btrim + NULLIF) og per-árs
percentile-trim eru of flókin til að copy-peista í 12 views — það væri
viðhaldsgildra (sama rök og root-fix-reglan: ein skilgreining, einn staður).
Þess vegna:

- **`semantic._sales_base`** (undirstrik-prefix = internal plumbing) á
  normaliseringuna, tegundaflokkunina, nýbyggingar-flaggið og outlier-flaggið
  — skilgreint EINU SINNI.
- Hörðu reglurnar standa SAMT bókstaflega í hverju downstream-viewi:
  `onothaefur = 0` er síað í base OG endurtekið í hverju viewi (dálkurinn
  flýtur í gegn til þess), `is_residential` er alltaf explicit downstream.
  Redundant — viljandi: SQL-textinn í hverju viewi er sjálfskjalandi fyrir
  agentinn og þolir breytingar á base.

### 1.3 Þverlægir staðlar

- **data_quality stigar** (samræmt yfir öll verð-views):
  `high` n≥100 · `medium` n≥30 · `low` n≥10 · `thin` n≥5 · `insufficient` <5.
  Götu-verð-views EMITTA EKKI raðir undir n=5 (HAVING-gat) — öryggisnet svo
  agentinn geti ekki vitnað í 2-sölu „meðalverð götu". Svæðis-views emitta
  allt með flaggi (svæði eru nógu aggregeruð til að n=6 median sé staðreynd,
  bara hávaðasöm).
- **Percentile-trim**: `is_ppm2_outlier` = ppm2_real utan [p01, p99] síns
  söluárs (reiknað yfir íbúðarsölur). Verð/m²-tölfræði í öllum views síar
  `NOT is_ppm2_outlier`. Heildarverðs-medianar eru EKKI trimmaðir (median er
  robust og trimmið er hugsað gegn gagnavillum í m², ekki verði).
- **Nýbyggingar-proxy**: `is_newbuild` = `byggar_at_sale ≥ söluár − 2`
  (17,2% sala 2020+; canonical nýbyggingarregla verkefnisins — samræmi við
  `is_new_build = FULLBUID=0 OR age_at_sale ≤ 2` í training-pipeline).
  FULLBUID er ekki í sales_history; þetta er proxy-ið sem til er. Views bera
  newbuild_share dálk; trend-views þar sem samsetningarbjögun skiptir mestu
  (quarterly, hood_heat) ÚTILOKA nýbyggingar úr verð-tölfræði en telja þær í
  veltu. (Spurning #3 SVARAÐ: −2.)
- **data_through**: hvert view ber `data_through` = max(thinglystdags) —
  uncorrelated scalar subquery, keyrir einu sinni per query (InitPlan).
- **Verðeiningar**: nominal = heilar kr á söludegi; real = CPI-leiðrétt á
  nýjasta CPI-mánuð precompute-keðjunnar. Þróunar-samanburður notar ALLTAF
  real; „hvað kostar" svör nota nominal.

---

## 2. View-skilgreiningar

### 2.0 `semantic._sales_base` — internal grunnview (smíðast fyrst)

**Tilgangur**: Eitt sameiginlegt sölu-grain lag: sales_history ⋈ properties
með götunormaliseringu, tegundaflokkun, nýbyggingar- og outlier-flöggum.
Internal plumbing — agentinn notar það ekki beint í v1 (opin spurning #5).

**Grain**: ein röð per arm's-length sala. **Lykill**: (fastnum, thinglystdags) — 76 þekkt tvítök, hverfandi.

```sql
CREATE OR REPLACE VIEW semantic._sales_base AS
WITH joined AS (
  SELECT
    sh.fastnum,
    sh.thinglystdags,
    EXTRACT(YEAR FROM sh.thinglystdags)::int                    AS sale_year,
    to_char(sh.thinglystdags, 'YYYY"Q"Q')                       AS sale_quarter,
    sh.kaupverd_nominal,
    sh.kaupverd_real,
    sh.einflm_at_sale,
    sh.byggar_at_sale,
    sh.onothaefur,
    (sh.byggar_at_sale IS NOT NULL
     AND sh.byggar_at_sale >= EXTRACT(YEAR FROM sh.thinglystdags) - 2)
                                                                AS is_newbuild,
    sh.kaupverd_nominal / NULLIF(sh.einflm_at_sale, 0)          AS ppm2_nominal,
    sh.kaupverd_real    / NULLIF(sh.einflm_at_sale, 0)          AS ppm2_real,
    -- Götunormalisering (T5 könnun §2): sviga-viðskeyti burt, svo allt frá
    -- fyrsta " <tölustaf>", svo btrim; tóm strengur → NULL.
    NULLIF(btrim(regexp_replace(regexp_replace(p.heimilisfang,
        '\s*\(.*\)\s*$', ''), '\s+\d.*$', '')), '')             AS street,
    NULLIF(btrim(p.sveitarfelag), '')                           AS sveitarfelag,
    p.postnr,
    p.postheiti,
    p.matsvaedi_numer,
    p.matsvaedi_nafn,
    p.region_tier,
    p.canonical_code,
    CASE
      WHEN p.canonical_code LIKE 'APT%'                                  THEN 'fjolbyli'
      WHEN p.canonical_code IN ('SFH_DETACHED','ROW_HOUSE','SEMI_DETACHED') THEN 'serbyli'
      ELSE 'annad'
    END                                                         AS prop_type,
    p.is_residential,
    p.is_summerhouse,
    p.lat,
    p.lng
  FROM public.sales_history sh
  JOIN public.properties p ON p.fastnum = sh.fastnum   -- 100% match (T5 §3)
  WHERE sh.onothaefur = 0                              -- HÖRÐ REGLA (420 lekar)
),
bounds AS (
  -- Per-árs trim-mörk á real verð/m², reiknuð YFIR ÍBÚÐARSÖLUR eingöngu.
  SELECT sale_year,
         percentile_cont(0.01) WITHIN GROUP (ORDER BY ppm2_real) AS ppm2_real_p01,
         percentile_cont(0.99) WITHIN GROUP (ORDER BY ppm2_real) AS ppm2_real_p99
  FROM joined
  WHERE is_residential AND ppm2_real IS NOT NULL
  GROUP BY sale_year
)
SELECT j.*,
       COALESCE(j.is_residential AND j.ppm2_real IS NOT NULL
                AND (j.ppm2_real < b.ppm2_real_p01
                     OR j.ppm2_real > b.ppm2_real_p99), false) AS is_ppm2_outlier
FROM joined j
LEFT JOIN bounds b USING (sale_year);
```

**Caveats**:
- Undirmengi-eðlið erfist: þetta er pairs-leidd arm's-length kaupskrá, ekki
  full þinglýsingaskrá. „Hve margar sölur" svör eru neðra mat á heildarveltu.
- `onothaefur` dálkurinn flýtur í gegn svo downstream-views geti endurtekið
  síuna sýnilega; hann er alltaf 0 hér.
- `prop_type='annad'` innan is_residential er nær tómt mengi (APT_UNAPPROVED
  o.fl. secondary-kóðar) — downstream views sleppa því ekki, það fellur í
  'allt'-rollup en fær ekki eigin línu í per-tegund grouping.
- Outlier-mörkin eru reiknuð per söluár yfir landið allt — EKKI per svæði.
  Dýrt hverfi nálægt p99 fær fleiri trimmaðar sölur en miðjusvæði; við
  medianskoðun er áhrifið hverfandi en p90+ percentilar í dýrustu svæðum
  geta verið örlítið vanmetnir.
- Trailing-whitespace og D3-recovery formattið er normaliserað hér; engin
  önnur lína í kerfinu þarf að vita af tveimur heimilisfang-kynslóðum.

---

## FASI 1 — router + verðlag

### 2.1 `semantic.v_street_directory`

**Tilgangur**: Uppflettilag götu → svæðis-stigveldi: hvar er gatan, hvað býr
á henni og hvernig blandast hún. Þetta er „router"-viewið sem agentinn (og
fallback-logík) notar til að velja rétt granularitet áður en verð-view er
spurt. Byggt á properties (öllum eignum), ekki sölum.

**Grain**: gata × sveitarfélag (~24.300 raðir). **Lykill**: (street, sveitarfelag).

```sql
CREATE MATERIALIZED VIEW semantic.v_street_directory AS  -- MV frá fasa 1.5
WITH props AS (
  SELECT
    NULLIF(btrim(regexp_replace(regexp_replace(heimilisfang,
        '\s*\(.*\)\s*$', ''), '\s+\d.*$', '')), '') AS street,
    NULLIF(btrim(sveitarfelag), '')                 AS sveitarfelag,
    postnr, matsvaedi_numer, matsvaedi_nafn, region_tier,
    is_residential, is_summerhouse,
    CASE
      WHEN canonical_code LIKE 'APT%'                                  THEN 'fjolbyli'
      WHEN canonical_code IN ('SFH_DETACHED','ROW_HOUSE','SEMI_DETACHED') THEN 'serbyli'
      ELSE 'annad'
    END AS prop_type,
    lat, lng
  FROM public.properties
  WHERE heimilisfang IS NOT NULL AND sveitarfelag IS NOT NULL
)
SELECT
  street,
  sveitarfelag,
  count(*)                                                    AS n_properties,
  count(*) FILTER (WHERE is_residential)                      AS n_residential,
  count(*) FILTER (WHERE is_summerhouse)                      AS n_summerhouse,
  count(*) FILTER (WHERE prop_type = 'fjolbyli' AND is_residential) AS n_fjolbyli,
  count(*) FILTER (WHERE prop_type = 'serbyli'  AND is_residential) AS n_serbyli,
  round((count(*) FILTER (WHERE prop_type = 'fjolbyli' AND is_residential))::numeric
        / NULLIF(count(*) FILTER (WHERE prop_type IN ('fjolbyli','serbyli')
                                  AND is_residential), 0), 3) AS fjolbyli_share,
  mode() WITHIN GROUP (ORDER BY postnr)                       AS postnr_mode,
  count(DISTINCT postnr)                                      AS n_postnr,
  mode() WITHIN GROUP (ORDER BY matsvaedi_numer)              AS matsvaedi_numer_mode,
  mode() WITHIN GROUP (ORDER BY matsvaedi_nafn)               AS matsvaedi_nafn_mode,
  count(DISTINCT matsvaedi_numer)                             AS n_matsvaedi,
  mode() WITHIN GROUP (ORDER BY region_tier)                  AS region_tier_mode,
  avg(lat)                                                    AS lat_centroid,
  avg(lng)                                                    AS lng_centroid,
  (SELECT max(thinglystdags) FROM public.sales_history)       AS data_through
FROM props
WHERE street IS NOT NULL
GROUP BY street, sveitarfelag
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_street_directory
  ON semantic.v_street_directory (street, sveitarfelag);
```

**Caveats**:
- Gata getur legið yfir fleiri en eitt matsvæði/póstnúmer (langar götur,
  Laugavegur-tilvik): `*_mode` er algengasta gildið, `n_matsvaedi`/`n_postnr`
  segja hvort gatan er klofin. Agent-regla: ef n_matsvaedi > 1 á að svara á
  matsvæðis-stigi með fyrirvara, ekki láta mode ráða þegjandi.
- „Götur" án húsnúmera (22.040 eignaraðir; dreifbýlis-bæjanöfn eins og
  „Hólar") og lóðaauðkenni með tölustöfum („Reyðarvatn S12") eru gildar raðir
  hér — directory er líka bæjarnafnaskrá dreifbýlis. n_residential greinir
  íbúðargötur frá lóðasvæðum.
- Sami götustrengur í tveimur sveitarfélögum er TVÆR raðir — það er kjarni
  lykilsins. Agent má aldrei fletta upp á street eingöngu.
- Centroid er meðaltal eignahnita — á klofnum götum getur það lent „milli"
  hluta götunnar.

### 2.2 `semantic.v_matsvaedi_prices_yearly`

**Tilgangur**: Kjarna-verðþróunarlag verkefnisins: verð og verð/m² per
matsvæði per ár, sundurliðað fjölbýli/sérbýli + 'allt'-rollup. Sterkasta
granularitetið (184 svæði, ~80 bera ≥30 sölur/ár).

**Grain**: matsvæði × ár × prop_type ('fjolbyli' | 'serbyli' | 'allt').
**Lykill**: (matsvaedi_numer, sale_year, prop_type).

```sql
CREATE MATERIALIZED VIEW semantic.v_matsvaedi_prices_yearly AS  -- MV frá fasa 1.5
SELECT
  b.matsvaedi_numer,
  mode() WITHIN GROUP (ORDER BY b.matsvaedi_nafn)             AS matsvaedi_nafn,
  mode() WITHIN GROUP (ORDER BY b.region_tier)                AS region_tier,
  b.sale_year,
  CASE WHEN GROUPING(b.prop_type) = 1 THEN 'allt' ELSE b.prop_type END AS prop_type,
  count(*)                                                    AS n_sales,
  count(*) FILTER (WHERE b.is_newbuild)                       AS n_newbuild,
  count(*) FILTER (WHERE NOT b.is_newbuild)                   AS n_existing,
  round(avg(b.is_newbuild::int), 3)                           AS newbuild_share,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_nominal)  AS median_kaupverd_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_real)     AS median_kaupverd_real,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_real,
  percentile_cont(0.25) WITHIN GROUP (ORDER BY b.ppm2_real)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS p25_ppm2_real,
  percentile_cont(0.75) WITHIN GROUP (ORDER BY b.ppm2_real)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS p75_ppm2_real,
  -- Composition-bias fix (§6 #8): NULL ef undirmengi < 5 sölur.
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
      FILTER (WHERE NOT b.is_newbuild AND NOT b.is_ppm2_outlier) END
                                                              AS median_ppm2_real_existing,
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
      FILTER (WHERE NOT b.is_newbuild AND NOT b.is_ppm2_outlier) END
                                                              AS median_ppm2_nominal_existing,
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_nominal)
      FILTER (WHERE NOT b.is_newbuild) END
                                                              AS median_kaupverd_nominal_existing,
  CASE WHEN count(*) FILTER (WHERE b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
      FILTER (WHERE b.is_newbuild AND NOT b.is_ppm2_outlier) END
                                                              AS median_ppm2_real_newbuild,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.einflm_at_sale)    AS median_einflm,
  CASE WHEN count(*) >= 100 THEN 'high'
       WHEN count(*) >= 30  THEN 'medium'
       WHEN count(*) >= 10  THEN 'low'
       WHEN count(*) >= 5   THEN 'thin'
       ELSE 'insufficient' END                                AS data_quality,
  (SELECT max(thinglystdags) FROM public.sales_history)       AS data_through
FROM semantic._sales_base b
WHERE b.onothaefur = 0              -- hörð regla, endurtekin sýnilega
  AND b.is_residential              -- sumarhús/atvinnuhúsn. EKKI hér
  AND b.matsvaedi_numer IS NOT NULL
GROUP BY GROUPING SETS (
  (b.matsvaedi_numer, b.sale_year, b.prop_type),
  (b.matsvaedi_numer, b.sale_year)
)
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_matsvaedi_prices_yearly
  ON semantic.v_matsvaedi_prices_yearly (matsvaedi_numer, sale_year, prop_type);
```

**Caveats**:
- 'allt'-raðir innihalda líka prop_type='annad' (örfáar secondary-sölur) —
  þess vegna getur n_sales('allt') > n('fjolbyli') + n('serbyli') um örfáar.
- Aðal-medianarnir lýsa því sem SELDIST (nýbyggingar inni). Á einingum með
  newbuild_share yfir ~0,3 er `median_*_existing` rétti samanburðurinn fyrir
  verðmat eldri eigna (§6 #8 composition-bias fix); `*_existing`/`*_newbuild`
  dálkarnir eru NULL þegar viðkomandi undirmengi er <5 sölur — agentinn má
  ekki vitna í 3-sölu eldri-stofns-median. Empírísk nóta (fasa-1.5 tékk):
  fixið bítur þar sem GAMALL stofn blandast nýbyggingu (Ánanaust: 'allt'
  1.066þ. vs existing 839þ. real-kr/m²); á alnýjum götum þar sem „eldri
  stofninn" er sjálfur nýlegar endursölur (Sunnusmári) er bilið eðlilega ~0.
- Ár 2006 og 2026 eru hlutaár (maí-start, apríl-cutoff) — n_sales þeirra er
  ekki samanburðarhæft við heil ár; data_through segir til um 2026-skurðinn.
- 2008–2010 eru grunn ár (hrunið, 1.8–2.7K sölur á landinu) — flest svæði
  detta í 'thin'/'insufficient' þar; það er sagan, ekki gagnagalli.
- Verðþróunarsamanburður milli ára á að nota *_real dálkana; nominal er fyrir
  „hvað kostaði" svör.

### 2.3 `semantic.v_street_prices`

**Tilgangur**: Verðlag götu — pooled rúllandi 5 ára gluggi, per tegund, með
hörðu n-gati. Flaggskips-efni mælaborðsins („hvað kostar fermetrinn í götunni
minni") og fínasta granularitet semantic-lagsins.

**Grain**: gata × sveitarfélag × prop_type ('fjolbyli' | 'serbyli' | 'allt'),
aðeins sellur með n ≥ 5 í glugganum. **Lykill**: (street, sveitarfelag, prop_type).

```sql
CREATE MATERIALIZED VIEW semantic.v_street_prices AS  -- MV frá fasa 1.5
WITH win AS (
  SELECT max(thinglystdags)                                AS data_through,
         (max(thinglystdags) - interval '5 years')::date   AS window_start
  FROM public.sales_history
)
SELECT
  b.street,
  b.sveitarfelag,
  CASE WHEN GROUPING(b.prop_type) = 1 THEN 'allt' ELSE b.prop_type END AS prop_type,
  count(*)                                                    AS n_sales,
  count(*) FILTER (WHERE b.is_newbuild)                       AS n_newbuild,
  count(*) FILTER (WHERE NOT b.is_newbuild)                   AS n_existing,
  round(avg(b.is_newbuild::int), 3)                           AS newbuild_share,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_nominal)  AS median_kaupverd_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_real,
  percentile_cont(0.25) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS p25_ppm2_nominal,
  percentile_cont(0.75) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS p75_ppm2_nominal,
  -- Composition-bias fix (§6 #8): NULL ef undirmengi < 5 sölur.
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
      FILTER (WHERE NOT b.is_newbuild AND NOT b.is_ppm2_outlier) END
                                                              AS median_ppm2_real_existing,
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
      FILTER (WHERE NOT b.is_newbuild AND NOT b.is_ppm2_outlier) END
                                                              AS median_ppm2_nominal_existing,
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_nominal)
      FILTER (WHERE NOT b.is_newbuild) END
                                                              AS median_kaupverd_nominal_existing,
  CASE WHEN count(*) FILTER (WHERE b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
      FILTER (WHERE b.is_newbuild AND NOT b.is_ppm2_outlier) END
                                                              AS median_ppm2_real_newbuild,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.einflm_at_sale)    AS median_einflm,
  max(b.thinglystdags)                                        AS last_sale_date,
  CASE WHEN count(*) >= 100 THEN 'high'
       WHEN count(*) >= 30  THEN 'medium'
       WHEN count(*) >= 10  THEN 'low'
       ELSE 'thin' END                                        AS data_quality,
  min(w.window_start)                                         AS window_start,
  min(w.data_through)                                         AS data_through
FROM semantic._sales_base b
CROSS JOIN win w
WHERE b.onothaefur = 0
  AND b.is_residential
  AND b.street IS NOT NULL
  AND b.sveitarfelag IS NOT NULL
  AND b.thinglystdags >= w.window_start
GROUP BY GROUPING SETS (
  (b.street, b.sveitarfelag, b.prop_type),
  (b.street, b.sveitarfelag)
)
HAVING count(*) >= 5     -- n-gat: raðir undir 5 sölum eru EKKI birtar
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_street_prices
  ON semantic.v_street_prices (street, sveitarfelag, prop_type);
```

**Caveats**:
- HAVING-gatið þýðir að fjarvera götu úr viewinu er upplýsing („of fá
  viðskipti sl. 5 ár") en ekki „gatan er ekki til" — directory-viewið sker úr.
  Agent-regla: miss hér → fallback á matsvæði götunnar úr v_street_directory.
- 5 ára pooled gluggi BLANDAR verðlagi tímabilsins; median_ppm2_real er rétti
  dálkurinn fyrir samanburð gatna (CPI-leiðréttur), nominal-tölurnar eru
  „blandað verðlag 2021–2026" og eiga ekki að lesast sem verð dagsins.
- 'allt'-línan á blönduðum götum (677 af 1.455 ≥10-götum blanda tegundum) er
  samsetningarháð — fjölbýlis/sérbýlis-línurnar eru alltaf réttari samanburður.
- Tvær götur í sitthvoru sveitarfélagi með sama nafn eru aðskildar raðir;
  UI/agent verður að bera sveitarfélag fram í svari.
- Composition-bias regla (§6 #8): á götum með newbuild_share yfir ~0,3 er
  `median_*_existing` rétti viðmiðunardálkurinn fyrir verðmat eldri eignar —
  aðal-medianinn er nýbyggingadrifinn þar. `*_existing`/`*_newbuild` eru NULL
  undir 5-sölu undirmengi (þunn-sellu vörn, sama prinsipp og n-gatið).

### 2.4 `semantic.v_postnr_prices_yearly`

**Tilgangur**: Póstnúmera-útgáfa verðþróunarlagsins — fallback þegar
matsvæði er of þunnt eða spurningin er á póstnúmera-máli („verð í 101").

**Grain**: póstnúmer × ár × prop_type. **Lykill**: (postnr, sale_year, prop_type).

```sql
CREATE MATERIALIZED VIEW semantic.v_postnr_prices_yearly AS  -- MV frá fasa 1.5
SELECT
  b.postnr,
  mode() WITHIN GROUP (ORDER BY b.postheiti)                  AS postheiti_mode,
  mode() WITHIN GROUP (ORDER BY b.region_tier)                AS region_tier,
  b.sale_year,
  CASE WHEN GROUPING(b.prop_type) = 1 THEN 'allt' ELSE b.prop_type END AS prop_type,
  count(*)                                                    AS n_sales,
  count(*) FILTER (WHERE b.is_newbuild)                       AS n_newbuild,
  count(*) FILTER (WHERE NOT b.is_newbuild)                   AS n_existing,
  round(avg(b.is_newbuild::int), 3)                           AS newbuild_share,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_nominal)  AS median_kaupverd_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_real)     AS median_kaupverd_real,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_real,
  -- Composition-bias fix (§6 #8): NULL ef undirmengi < 5 sölur.
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
      FILTER (WHERE NOT b.is_newbuild AND NOT b.is_ppm2_outlier) END
                                                              AS median_ppm2_real_existing,
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
      FILTER (WHERE NOT b.is_newbuild AND NOT b.is_ppm2_outlier) END
                                                              AS median_ppm2_nominal_existing,
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_nominal)
      FILTER (WHERE NOT b.is_newbuild) END
                                                              AS median_kaupverd_nominal_existing,
  CASE WHEN count(*) FILTER (WHERE b.is_newbuild) >= 5 THEN
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
      FILTER (WHERE b.is_newbuild AND NOT b.is_ppm2_outlier) END
                                                              AS median_ppm2_real_newbuild,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.einflm_at_sale)    AS median_einflm,
  CASE WHEN count(*) >= 100 THEN 'high'
       WHEN count(*) >= 30  THEN 'medium'
       WHEN count(*) >= 10  THEN 'low'
       WHEN count(*) >= 5   THEN 'thin'
       ELSE 'insufficient' END                                AS data_quality,
  (SELECT max(thinglystdags) FROM public.sales_history)       AS data_through
FROM semantic._sales_base b
WHERE b.onothaefur = 0
  AND b.is_residential
  AND b.postnr IS NOT NULL
GROUP BY GROUPING SETS (
  (b.postnr, b.sale_year, b.prop_type),
  (b.postnr, b.sale_year)
)
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_postnr_prices_yearly
  ON semantic.v_postnr_prices_yearly (postnr, sale_year, prop_type);
```

**Caveats**:
- `postheiti_mode` ber D3-recovery mengunina (götuheiti í postheiti á ~hluta
  raða) — mode yfir sölumengið ætti nær alltaf að gefa rétt byggðarlag, en
  dálkurinn er display-hint, ekki sannleikur. Póstnúmerið sjálft er hreint.
- Stór póstnúmer (t.d. 101, 200) spanna mörg matsvæði með ólíku verðlagi —
  matsvæðis-viewið er alltaf fínni sannleikur þegar það ber gögnin.
- Sömu hlutaárs-/hrunárs-fyrirvarar og í 2.2.
- Composition-bias regla (§6 #8): sama og í 2.2/2.3 — newbuild_share yfir
  ~0,3 → nota `median_*_existing`; NULL undir 5-sölu undirmengi.

---

## FASI 2 — virkni, þróun, sérgreiningar

### 2.5 `semantic.v_street_activity`

**Tilgangur**: Veltusaga götu: hve mikið selst, hve mikið af því er
nýbygging, hvenær seldist síðast. Verðlaust (engin verð-tölfræði) svo ekkert
n-gat þarf — talningar eru staðreyndir á hvaða n sem er.

**Grain**: gata × sveitarfélag × ár. **Lykill**: (street, sveitarfelag, sale_year).

```sql
CREATE MATERIALIZED VIEW semantic.v_street_activity AS  -- MV frá fasa 2
SELECT
  b.street,
  b.sveitarfelag,
  b.sale_year,
  count(*)                                              AS n_sales,
  count(*) FILTER (WHERE b.is_newbuild)                 AS n_newbuild,
  count(*) FILTER (WHERE b.prop_type = 'fjolbyli')      AS n_fjolbyli,
  count(*) FILTER (WHERE b.prop_type = 'serbyli')       AS n_serbyli,
  count(DISTINCT b.fastnum)                             AS n_distinct_properties,
  max(b.thinglystdags)                                  AS last_sale_in_year,
  (SELECT max(thinglystdags) FROM public.sales_history) AS data_through
FROM semantic._sales_base b
WHERE b.onothaefur = 0
  AND b.is_residential
  AND b.street IS NOT NULL
  AND b.sveitarfelag IS NOT NULL
GROUP BY b.street, b.sveitarfelag, b.sale_year
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_street_activity
  ON semantic.v_street_activity (street, sveitarfelag, sale_year);
```

**Caveats**:
- Veltu-hlutfall (turnover rate) þarf nefnara: joinið við
  v_street_directory.n_residential til að fá „% eigna götunnar sem skipti um
  hendur" — viljandi ekki innbakað hér (directory-nefnari er nútíma-stock en
  árin hér ná til 2006; hlutfallið væri tímaskekkt fyrir gömul ár).
- n_distinct_properties < n_sales innan árs = sama eign seld oftar en einu
  sinni (flipp-signal).
- Undirmengi-fyrirvarinn (arm's-length only) bítur mest hér: heildarveltan á
  götu er vanmetin um ONOTHAEFUR-hlutann (~23% á landsvísu).

### 2.6 `semantic.v_sveitarfelag_market`

**Tilgangur**: Sveitarfélagsyfirlit per ár: velta, verðlag, nýbyggingar- og
fjölbýlishlutdeild. Grófasta granularitetið og öruggasti fallbackurinn.

**Grain**: sveitarfélag × ár. **Lykill**: (sveitarfelag, sale_year).

```sql
CREATE MATERIALIZED VIEW semantic.v_sveitarfelag_market AS  -- MV frá fasa 2
SELECT
  b.sveitarfelag,
  mode() WITHIN GROUP (ORDER BY b.region_tier)                AS region_tier,
  b.sale_year,
  count(*)                                                    AS n_sales,
  sum(b.kaupverd_nominal)                                     AS velta_nominal,
  count(*) FILTER (WHERE b.is_newbuild)                       AS n_newbuild,
  round(avg(b.is_newbuild::int), 3)                           AS newbuild_share,
  round(avg((b.prop_type = 'fjolbyli')::int), 3)              AS fjolbyli_share,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_nominal)  AS median_kaupverd_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_real)     AS median_kaupverd_real,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_real,
  CASE WHEN count(*) >= 100 THEN 'high'
       WHEN count(*) >= 30  THEN 'medium'
       WHEN count(*) >= 10  THEN 'low'
       WHEN count(*) >= 5   THEN 'thin'
       ELSE 'insufficient' END                                AS data_quality,
  (SELECT max(thinglystdags) FROM public.sales_history)       AS data_through
FROM semantic._sales_base b
WHERE b.onothaefur = 0
  AND b.is_residential
  AND b.sveitarfelag IS NOT NULL
GROUP BY b.sveitarfelag, b.sale_year
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_sveitarfelag_market
  ON semantic.v_sveitarfelag_market (sveitarfelag, sale_year);
```

**Caveats**:
- `velta_nominal` er summa arm's-length íbúðarsala — EKKI heildarvelta
  fasteignamarkaðar sveitarfélagsins (vantar ONOTHAEFUR, atvinnuhúsnæði,
  fjöleigna-samninga). Nota sem þróunar-signal, ekki hagtölu.
- Sveitarfélaganöfn eru eins og HMS skrifar þau („Reykjavíkurborg", ekki
  „Reykjavík") — agentinn þarf nafnamöppun í knowledge-pakka (notendur segja
  „Kópavogur", gögnin segja „Kópavogsbær").
- Sameiningar sveitarfélaga yfir 20 ára gluggann geta valdið nafnabrotum í
  tímaröðum (sama land, tvö nöfn) — þekkt takmörkun v1.

### 2.7 `semantic.v_matsvaedi_trend_quarterly`

**Tilgangur**: Ársfjórðungsupplausn verðþróunar fyrir matsvæðin sem bera
hana. Nýbyggingar ÚTILOKAÐAR úr verðtölfræði (samsetningarbjögun er verst á
fjórðungs-skala) en taldar sér.

**Grain**: matsvæði × ársfjórðungur (2015+). **Lykill**: (matsvaedi_numer, sale_quarter).

```sql
CREATE MATERIALIZED VIEW semantic.v_matsvaedi_trend_quarterly AS  -- MV frá fasa 2
SELECT
  b.matsvaedi_numer,
  mode() WITHIN GROUP (ORDER BY b.matsvaedi_nafn)             AS matsvaedi_nafn,
  b.sale_quarter,
  count(*)                                                    AS n_sales,
  count(*) FILTER (WHERE b.is_newbuild)                       AS n_newbuild,
  count(*) FILTER (WHERE NOT b.is_newbuild)                   AS n_existing,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
    FILTER (WHERE NOT b.is_ppm2_outlier AND NOT b.is_newbuild)
                                                              AS median_ppm2_real_existing,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier AND NOT b.is_newbuild)
                                                              AS median_ppm2_nominal_existing,
  (count(*) FILTER (WHERE NOT b.is_newbuild)) < 10            AS insufficient_sample,
  CASE WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 30 THEN 'high'
       WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 10 THEN 'medium'
       WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5  THEN 'low'
       ELSE 'insufficient' END                                AS data_quality,
  (SELECT max(thinglystdags) FROM public.sales_history)       AS data_through
FROM semantic._sales_base b
WHERE b.onothaefur = 0
  AND b.is_residential
  AND b.matsvaedi_numer IS NOT NULL
  AND b.sale_year >= 2015
GROUP BY b.matsvaedi_numer, b.sale_quarter
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_matsvaedi_trend_quarterly
  ON semantic.v_matsvaedi_trend_quarterly (matsvaedi_numer, sale_quarter);
```

**Caveats**:
- Könnunin sýndi að aðeins ~30–45 matsvæði bera ≥100 sölur/ár → fjórðungs-n
  er oftast 5–35; `insufficient_sample`-flaggið (mynstur úr repeat_sale_index)
  er ekki skraut heldur skylda í allri framsetningu.
- Median per fjórðung er HÁVAÐASAMUR punktur — fyrir alvöru vísitölulestur
  vísar agentinn á `repeat_sale_index` (BMN, composition-controlled); þetta
  view er „hvað er að gerast NÚNA í hverfinu" lag, ekki vísitala.
- Nýjasti fjórðungurinn er alltaf hlutafjórðungur upp að data_through (apríl
  2026 cutoff núna) OG þinglýsingar berast með töf — síðasti punktur á alltaf
  eftir að hækka í n. Aldrei draga ályktun af falli í nýjasta fjórðungi.

### 2.8 `semantic.v_hood_heat`

**Tilgangur**: Markaðs-momentum per matsvæði: síðustu 12 mánuðir vs 12
mánuðirnir þar á undan — velta og verð/m², með heat-bucket flokkun.
Mælaborðs-efni („heitustu hverfin núna").

**Grain**: matsvæði (ein röð hvert). **Lykill**: matsvaedi_numer.

```sql
CREATE MATERIALIZED VIEW semantic.v_hood_heat AS  -- MV frá fasa 2
WITH win AS (
  SELECT max(thinglystdags) AS data_through FROM public.sales_history
),
s AS (
  SELECT b.*, w.data_through
  FROM semantic._sales_base b
  CROSS JOIN win w
  WHERE b.onothaefur = 0
    AND b.is_residential
    AND b.matsvaedi_numer IS NOT NULL
    AND b.thinglystdags >= (w.data_through - interval '24 months')
),
agg AS (
  SELECT
    matsvaedi_numer,
    mode() WITHIN GROUP (ORDER BY matsvaedi_nafn)  AS matsvaedi_nafn,
    min(data_through)                              AS data_through,
    count(*) FILTER (WHERE thinglystdags >= data_through - interval '12 months')
                                                   AS n_12mo,
    count(*) FILTER (WHERE thinglystdags <  data_through - interval '12 months')
                                                   AS n_prev12mo,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY ppm2_real)
      FILTER (WHERE NOT is_ppm2_outlier AND NOT is_newbuild
              AND thinglystdags >= data_through - interval '12 months')
                                                   AS median_ppm2_real_12mo,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY ppm2_real)
      FILTER (WHERE NOT is_ppm2_outlier AND NOT is_newbuild
              AND thinglystdags < data_through - interval '12 months')
                                                   AS median_ppm2_real_prev12mo
  FROM s
  GROUP BY matsvaedi_numer
)
SELECT
  matsvaedi_numer,
  matsvaedi_nafn,
  n_12mo,
  n_prev12mo,
  round((n_12mo::numeric / NULLIF(n_prev12mo, 0)) - 1, 3)     AS volume_change,
  median_ppm2_real_12mo,
  median_ppm2_real_prev12mo,
  round(((median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, 0)) - 1)::numeric, 3)
                                                              AS ppm2_real_change,
  CASE
    WHEN n_12mo < 10 OR n_prev12mo < 10 THEN 'insufficient'
    WHEN (median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, 0)) - 1 >= 0.05
      THEN 'hot'
    WHEN (median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, 0)) - 1 >= 0.02
     AND (n_12mo::numeric / NULLIF(n_prev12mo, 0)) - 1 >= 0.15
      THEN 'hot'
    WHEN (median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, 0)) - 1 <= -0.05
      THEN 'cold'
    WHEN (median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, 0)) - 1 <= -0.02
     AND (n_12mo::numeric / NULLIF(n_prev12mo, 0)) - 1 <= -0.15
      THEN 'cold'
    ELSE 'neutral'
  END                                                         AS heat_bucket,
  data_through
FROM agg
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_hood_heat
  ON semantic.v_hood_heat (matsvaedi_numer);
```

**Caveats**:
- Heat-þröskuldarnir (±5% verð, ±2%+±15% velta) eru v1-HEURISTIK, ekki
  kalibruð töl — opin spurning #4. ats_dashboard_monthly_heat notar
  z-skor-aðferð (3mo vs 12mo rolling) á ask-to-sale; þessi notar einfaldari
  YoY-medianspörun á söluverði. Tvö ólík „heat"-hugtök — agentinn verður að
  greina á milli (þetta = söluverðs-momentum; ats = tilboðsspennu-momentum).
- Þinglýsingatöfin bítur líka hér: nýjustu vikurnar eru vantaldar í n_12mo —
  volume_change hefur kerfisbundna neikvæða bjögun nálægt data_through.
  Verðhlutföllin (median) eru ónæmari.
- Nýbyggingar útilokaðar úr verðmedian (sömu rök og 2.7) en taldar í veltu.

### 2.9 `semantic.v_newbuild_share`

**Tilgangur**: Nýbyggingavelta og -verðálag per matsvæði per ár: hlutdeild
nýbygginga og verð/m²-premía þeirra yfir eldri eignir sama svæðis.

**Grain**: matsvæði × ár. **Lykill**: (matsvaedi_numer, sale_year).

```sql
CREATE MATERIALIZED VIEW semantic.v_newbuild_share AS  -- MV frá fasa 2
SELECT
  b.matsvaedi_numer,
  mode() WITHIN GROUP (ORDER BY b.matsvaedi_nafn)             AS matsvaedi_nafn,
  b.sale_year,
  count(*)                                                    AS n_sales,
  count(*) FILTER (WHERE b.is_newbuild)                       AS n_newbuild,
  round(avg(b.is_newbuild::int), 3)                           AS newbuild_share,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier AND b.is_newbuild)    AS median_ppm2_newbuild,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier AND NOT b.is_newbuild) AS median_ppm2_existing,
  round((
    percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
      FILTER (WHERE NOT b.is_ppm2_outlier AND b.is_newbuild)
    / NULLIF(percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
      FILTER (WHERE NOT b.is_ppm2_outlier AND NOT b.is_newbuild), 0)
    - 1)::numeric, 3)                                         AS newbuild_premium,
  CASE WHEN count(*) FILTER (WHERE b.is_newbuild) >= 30
        AND count(*) FILTER (WHERE NOT b.is_newbuild) >= 30 THEN 'high'
       WHEN count(*) FILTER (WHERE b.is_newbuild) >= 10
        AND count(*) FILTER (WHERE NOT b.is_newbuild) >= 10 THEN 'medium'
       WHEN count(*) FILTER (WHERE b.is_newbuild) >= 5
        AND count(*) FILTER (WHERE NOT b.is_newbuild) >= 5  THEN 'low'
       ELSE 'insufficient' END                                AS data_quality,
  (SELECT max(thinglystdags) FROM public.sales_history)       AS data_through
FROM semantic._sales_base b
WHERE b.onothaefur = 0
  AND b.is_residential
  AND b.matsvaedi_numer IS NOT NULL
GROUP BY b.matsvaedi_numer, b.sale_year
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_newbuild_share
  ON semantic.v_newbuild_share (matsvaedi_numer, sale_year);
```

**Caveats**:
- `newbuild_premium` ber EKKI saman sambærilegar eignir — nýbyggingar eru
  kerfisbundið öðruvísi (stærð, tegund, staðsetning innan svæðis). Þetta er
  lýsandi munur, ekki kausal premía; data_quality krefst beggja hliða.
- byggar-proxyið flokkar gagngert endurbyggt húsnæði (nýtt byggingarár á
  gömlu fastnum) sem nýbyggingu — fátítt en til.
- ONOTHAEFUR-undirmengið vanmetur nýbyggingaveltu sérstaklega þar sem
  verktakasölur til tengdra aðila eru flaggaðar — share hér er markaðshlutdeild
  í arm's-length sölum, ekki byggingartölfræði.

### 2.10 `semantic.v_model_vs_sold_by_hood`

**Tilgangur**: Raunsölur síðustu 12 mánaða bornar saman við gildandi
iter4-spár sömu eigna per matsvæði: hvar selst yfir/undir mati módelsins.
Brú yfir í T6 (fasteignamats-frávik) og fyrsta self-monitoring lag agentsins.

**Grain**: matsvæði. **Lykill**: matsvaedi_numer.

```sql
CREATE MATERIALIZED VIEW semantic.v_model_vs_sold_by_hood AS  -- MV frá fasa 2
WITH win AS (
  SELECT max(thinglystdags) AS data_through FROM public.sales_history
),
pairs AS (
  SELECT
    b.matsvaedi_numer,
    b.matsvaedi_nafn,
    w.data_through,
    b.kaupverd_real / NULLIF(pr.real_pred_median, 0)::numeric AS sold_to_pred_ratio
  FROM semantic._sales_base b
  JOIN public.predictions pr ON pr.fastnum = b.fastnum
  CROSS JOIN win w
  WHERE b.onothaefur = 0
    AND b.is_residential
    AND b.matsvaedi_numer IS NOT NULL
    AND NOT b.is_ppm2_outlier
    AND b.thinglystdags >= (w.data_through - interval '12 months')
    AND pr.real_pred_median > 0
)
SELECT
  matsvaedi_numer,
  mode() WITHIN GROUP (ORDER BY matsvaedi_nafn)               AS matsvaedi_nafn,
  count(*)                                                    AS n_pairs,
  percentile_cont(0.5)  WITHIN GROUP (ORDER BY sold_to_pred_ratio) AS median_ratio,
  percentile_cont(0.25) WITHIN GROUP (ORDER BY sold_to_pred_ratio) AS p25_ratio,
  percentile_cont(0.75) WITHIN GROUP (ORDER BY sold_to_pred_ratio) AS p75_ratio,
  CASE WHEN count(*) >= 100 THEN 'high'
       WHEN count(*) >= 30  THEN 'medium'
       WHEN count(*) >= 10  THEN 'low'
       WHEN count(*) >= 5   THEN 'thin'
       ELSE 'insufficient' END                                AS data_quality,
  min(data_through)                                           AS data_through
FROM pairs
GROUP BY matsvaedi_numer
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_model_vs_sold_by_hood
  ON semantic.v_model_vs_sold_by_hood (matsvaedi_numer);
```

**Caveats**:
- **CIRCULARITY**: sölurnar í glugganum geta verið í þjálfunar-/kalibrunar-
  gögnum iter4 (eftir retrain-cycle) — median_ratio nálægt 1,00 er þá að
  hluta sjálfspeglun. Þetta er stefnu-vísir („hverfi X selst kerfisbundið 6%
  yfir mati"), ALDREI formleg módel-validering — hún á heima í
  validate_metrics keðjunni með held-out aga.
- **EININGA-VALIDERING SKYLDA VIÐ CREATION**: kaupverd_real er í heilum kr;
  einingar `predictions.real_pred_median` (bigint) eru óstaðfestar í þessari
  könnun. Sanity-tékk við creation: `SELECT percentile_cont(0.5)...` á
  ratio-inu — vænt ~1,0; ef ~1.000 er þús.kr-mismatch og viewið þarf ×1000
  leiðréttingu. Sjá creation-gátlista §4. **STAÐFEST 2026-06-12 við fasa-2
  creation: median ratio 1,0042 (IQR 0,944–1,082, n=9.500) — einingar passa.**
- predictions er current-snapshot (predicted_at), ekki spá-á-söludegi —
  12 mánaða glugginn heldur tímaskekkjunni innan markaðshreyfingar ársins,
  en í hröðum markaði bjagast ratio-ið í átt hreyfingarinnar.
- 8.426 held-fastnums (D3 honesty-gate) eiga enga spá → detta sjálfkrafa úr
  join-inu; svæði með háa held-hlutdeild (Country) fá lægra n_pairs.

### 2.11 `semantic.v_summerhouse_market`

**Tilgangur**: Sumarhúsamarkaðurinn per sveitarfélag per ár — EINA viewið
þar sem sumarhús eiga heima; alls staðar annars staðar eru þau síuð burt
með is_residential.

**Grain**: sveitarfélag × ár. **Lykill**: (sveitarfelag, sale_year).

```sql
CREATE MATERIALIZED VIEW semantic.v_summerhouse_market AS  -- MV frá fasa 2; ppm2 ótrimmaður meðvitað (sjá caveats)
SELECT
  b.sveitarfelag,
  b.sale_year,
  count(*)                                                    AS n_sales,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_nominal)  AS median_kaupverd_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_real)     AS median_kaupverd_real,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.einflm_at_sale)    AS median_einflm,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)      AS median_ppm2_nominal,
  CASE WHEN count(*) >= 30 THEN 'high'
       WHEN count(*) >= 10 THEN 'medium'
       WHEN count(*) >= 5  THEN 'low'
       ELSE 'insufficient' END                                AS data_quality,
  (SELECT max(thinglystdags) FROM public.sales_history)       AS data_through
FROM semantic._sales_base b
WHERE b.onothaefur = 0
  AND b.is_summerhouse          -- EKKI is_residential — sér-mengi
  AND b.sveitarfelag IS NOT NULL
GROUP BY b.sveitarfelag, b.sale_year
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_summerhouse_market
  ON semantic.v_summerhouse_market (sveitarfelag, sale_year);
```

**Caveats**:
- `is_ppm2_outlier` flaggið er reiknað yfir íbúðarsölur og er false/ógilt
  hér — ppm2-medianinn er ÓTRIMMAÐUR (median er robust; sumarhúsa-m² er
  hvort eð er veik stærð því lóð/hlunnindi bera stóran hluta verðsins).
- Verð/m² er almennt veikari mælikvarði á sumarhús en heildarverð — agentinn
  á að leiða svör með median_kaupverd, ekki ppm2.
- Lægri data_quality-þröskuldar (30/10/5) en í íbúðar-views — sumarhúsamengið
  er lítið (2.320 sölur 2020+ á landsvísu) og dreift; jafnvel stærstu
  sveitarfélögin (Grímsnes- og Grafningshreppur, Bláskógabyggð) ná fáum
  hundruðum á ári.

### 2.12 `semantic.v_price_distribution_by_hood`

**Tilgangur**: Full verðdreifing (p10–p90) per matsvæði, pooled síðustu 3 ár
— fyrir „hvað fæst fyrir X milljónir í hverfi Y" spurningar og
dreifingar-myndir, þar sem median einn dugar ekki.

**Grain**: matsvæði × prop_type. **Lykill**: (matsvaedi_numer, prop_type).

```sql
CREATE MATERIALIZED VIEW semantic.v_price_distribution_by_hood AS  -- MV frá fasa 2
WITH win AS (
  SELECT max(thinglystdags)                              AS data_through,
         (max(thinglystdags) - interval '3 years')::date AS window_start
  FROM public.sales_history
)
SELECT
  b.matsvaedi_numer,
  mode() WITHIN GROUP (ORDER BY b.matsvaedi_nafn)             AS matsvaedi_nafn,
  CASE WHEN GROUPING(b.prop_type) = 1 THEN 'allt' ELSE b.prop_type END AS prop_type,
  count(*)                                                    AS n_sales,
  percentile_cont(0.10) WITHIN GROUP (ORDER BY b.kaupverd_nominal) AS p10_kaupverd,
  percentile_cont(0.25) WITHIN GROUP (ORDER BY b.kaupverd_nominal) AS p25_kaupverd,
  percentile_cont(0.50) WITHIN GROUP (ORDER BY b.kaupverd_nominal) AS p50_kaupverd,
  percentile_cont(0.75) WITHIN GROUP (ORDER BY b.kaupverd_nominal) AS p75_kaupverd,
  percentile_cont(0.90) WITHIN GROUP (ORDER BY b.kaupverd_nominal) AS p90_kaupverd,
  percentile_cont(0.10) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS p10_ppm2,
  percentile_cont(0.50) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS p50_ppm2,
  percentile_cont(0.90) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS p90_ppm2,
  CASE WHEN count(*) >= 100 THEN 'high'
       WHEN count(*) >= 30  THEN 'medium'
       WHEN count(*) >= 10  THEN 'low'
       ELSE 'thin' END                                        AS data_quality,
  min(w.window_start)                                         AS window_start,
  min(w.data_through)                                         AS data_through
FROM semantic._sales_base b
CROSS JOIN win w
WHERE b.onothaefur = 0
  AND b.is_residential
  AND b.matsvaedi_numer IS NOT NULL
  AND b.thinglystdags >= w.window_start
GROUP BY GROUPING SETS (
  (b.matsvaedi_numer, b.prop_type),
  (b.matsvaedi_numer)
)
HAVING count(*) >= 10    -- dreifingar-percentilar þurfa hærra gat en median
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_price_distribution_by_hood
  ON semantic.v_price_distribution_by_hood (matsvaedi_numer, prop_type);
```

**Caveats**:
- p10/p90 á n=10–30 sellum eru í raun min/max-nágrannar — data_quality
  'thin'/'low' raðir eiga aðeins að nota p25–p75. HAVING ≥10 er gólfið;
  agentinn á að herða kröfuna eftir því hvaða percentil hann vitnar í.
- 3 ára pooled gluggi blandar verðlagi (sami fyrirvari og 2.3) — nominal
  tölur lesast „verðlag tímabilsins", ekki dagsins.
- Halar dreifingar bera samsetningu (penthouse vs kjallari, götumunur innan
  svæðis) — ekki „sama eign ódýr/dýr".

---

### 2.13 `semantic.v_sveitarfelag_lookup` — statískt nafna-lookup (fasi 2, §6 #7)

**Tilgangur**: Möppun HMS-sveitarfélaganafna („Kópavogsbær") á notendamál
(„Kópavogur") fyrir agent og UI. Canonical-layer reglan: knowledge-pakki
agentsins VÍSAR í þetta view en á ekki möppunina sjálfur.

**Grain**: sveitarfélag (64 raðir). **Lykill**: sveitarfelag.

```sql
CREATE MATERIALIZED VIEW semantic.v_sveitarfelag_lookup AS  -- MV frá fasa 2
WITH base AS (
  SELECT DISTINCT NULLIF(btrim(sveitarfelag), '') AS sveitarfelag
  FROM public.properties
  WHERE sveitarfelag IS NOT NULL
),
manual(sveitarfelag, common_name) AS (VALUES
  ('Reykjavíkurborg',            'Reykjavík'),
  ('Kópavogsbær',                'Kópavogur'),
  ('Hafnarfjarðarkaupstaður',    'Hafnarfjörður'),
  ('Seltjarnarnesbær',           'Seltjarnarnes'),
  ('Akureyrarbær',               'Akureyri'),
  ('Akraneskaupstaður',          'Akranes'),
  ('Vestmannaeyjabær',           'Vestmannaeyjar'),
  ('Ísafjarðarbær',              'Ísafjörður'),
  ('Grindavíkurbær',             'Grindavík'),
  ('Hveragerðisbær',             'Hveragerði'),
  ('Stykkishólmsbær',            'Stykkishólmur'),
  ('Grundarfjarðarbær',          'Grundarfjörður'),
  ('Bolungarvíkurkaupstaður',    'Bolungarvík'),
  ('Blönduósbær',                'Blönduós'),
  ('Seyðisfjarðarkaupstaður',    'Seyðisfjörður'),
  ('Sveitarfélagið Árborg',      'Árborg'),
  ('Sveitarfélagið Hornafjörður','Hornafjörður'),
  ('Sveitarfélagið Skagafjörður','Skagafjörður'),
  ('Sveitarfélagið Ölfus',       'Ölfus'),
  ('Sveitarfélagið Vogar',       'Vogar')
)
SELECT b.sveitarfelag,
       COALESCE(m.common_name, b.sveitarfelag) AS common_name,
       (m.common_name IS NOT NULL)             AS has_alias
FROM base b
LEFT JOIN manual m USING (sveitarfelag)
WHERE b.sveitarfelag IS NOT NULL
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_sveitarfelag_lookup
  ON semantic.v_sveitarfelag_lookup (sveitarfelag);
```

**Caveats**:
- Aliasarnir eru ÍHALDSSAMIR: aðeins suffix-afleiðingar (-bær/-kaupstaður/
  -borg) og „Sveitarfélagið X"-strip — ENGAR bæjarnafna-giskanir (Árborg er
  „Árborg", ekki „Selfoss"; Fjallabyggð er „Fjallabyggð", ekki „Siglufjörður").
  Bæjarnafn↔sveitarfélags-tenging fyrir notendaspurningar („verð á Selfossi")
  er knowledge-pakka verkefni, ekki SQL.
- common_name fellur á sveitarfelag óbreytt þegar enginn alias er til
  (has_alias=false) — view-ið skilar alltaf öllum 64 röðum.
- Sameiningar sveitarfélaga breyta base-mengi við REFRESH; manual-listinn
  þarf þá yfirferð (lágtíðni viðhald).

## 3. Dependency-röð fyrir creation

```
1. CREATE SCHEMA semantic;
2. semantic._sales_base                    (þarf: public.sales_history, public.properties)
3. FASI 1:
   a. v_street_directory                   (þarf: public.properties — óháð base)
   b. v_matsvaedi_prices_yearly            (þarf: _sales_base)
   c. v_street_prices                      (þarf: _sales_base)
   d. v_postnr_prices_yearly               (þarf: _sales_base)
4. FASI 2 (öll óháð innbyrðis, hvaða röð sem er):
   v_street_activity, v_sveitarfelag_market, v_matsvaedi_trend_quarterly,
   v_hood_heat, v_newbuild_share, v_summerhouse_market,
   v_price_distribution_by_hood            (öll þarf: _sales_base)
   v_model_vs_sold_by_hood                 (þarf: _sales_base + public.predictions
                                            + EININGA-VALIDERING fyrst, sjá §4)
   v_sveitarfelag_lookup                   (statískt; þarf: public.properties)
5. GRANTs (sér gated skref með agent-role hönnun — EKKI í creation-migration)
```

Engin view vísar í annað downstream-view — flatt tré með _sales_base sem
einu sameiginlegu rót. v_street_directory er eina viewið án base-dependency.

## 4. Creation-gátlisti (fyrir apply_migration skrefið, til glöggvunar)

1. `EXPLAIN ANALYZE` á _sales_base og þyngsta downstream (v_street_prices) —
   vænting <1–2s; ef verulega yfir, sjá materialization-plan.
2. Sanity per view: row count innan ±10% af könnunar-spá (sjá §5 töflu),
   spot-check 2–3 þekktar götur/matsvæði gegn handreikningi.
3. v_model_vs_sold_by_hood EININGA-TÉKK (sjá 2.10) ÁÐUR en viewið er skapað.
4. Staðfesta að `semantic` sé EKKI í PostgREST exposed-schemas eftir á.
5. (Fasa 2) v_hood_heat kalibrerunartékk gegn ats_dashboard_monthly_heat
   sögunni ÁÐUR en heat-þröskuldarnir læsast (§6 svar #4).

### §4.1 REFRESH-ábyrgð MV-anna (fasi 1.5)

Öll 13 output-MV eru MATERIALIZED (4 frá fasa 1.5, 9 frá fasa 2 — þ.m.t.
v_sveitarfelag_lookup); `_sales_base` er eina venjulega viewið. REFRESH-ábyrgð:
**hooked í run_monthly post-push þegar þar að kemur; þangað til er REFRESH
handvirkt gated skref eftir HVERJA sales_history-uppfærslu** (annars sýna
MV-in stale data_through og stale tölur). Copy-paste blokk:

```sql
REFRESH MATERIALIZED VIEW semantic.v_street_directory;
REFRESH MATERIALIZED VIEW semantic.v_matsvaedi_prices_yearly;
REFRESH MATERIALIZED VIEW semantic.v_street_prices;
REFRESH MATERIALIZED VIEW semantic.v_postnr_prices_yearly;
REFRESH MATERIALIZED VIEW semantic.v_street_activity;
REFRESH MATERIALIZED VIEW semantic.v_sveitarfelag_market;
REFRESH MATERIALIZED VIEW semantic.v_matsvaedi_trend_quarterly;
REFRESH MATERIALIZED VIEW semantic.v_hood_heat;
REFRESH MATERIALIZED VIEW semantic.v_newbuild_share;
REFRESH MATERIALIZED VIEW semantic.v_model_vs_sold_by_hood;
REFRESH MATERIALIZED VIEW semantic.v_summerhouse_market;
REFRESH MATERIALIZED VIEW semantic.v_price_distribution_by_hood;
REFRESH MATERIALIZED VIEW semantic.v_sveitarfelag_lookup;
```

Keyra EITT í einu (ekki samhliða — IO-samkeppni á litla instance-inu,
mælt í fasa 1). Hvert tekur ~10–30s. `REFRESH ... CONCURRENTLY` er
mögulegt eftir fyrsta populate (unique indexar `uq_mv_*` til staðar á
öllum 13) — aðeins þörf ef lesendur mega ekki blokkast meðan refresh
keyrir; plain REFRESH dugar í v1.

## 5. Materialized vs venjuleg — mat

**UPPFÆRSLA 2026-06-11 (fasi 1.5, eftir mælingar — SNÝR v1-TILLÖGUNNI VIÐ):**
v1-tillagan hér að neðan féll á creation-gátlistanum: mæld warm-latency
`_sales_base` var **25,5s** (properties_pkey full-index-scan 23,1s — random
heap-IO yfir 232K breiðar raðir), og storage-rökin reyndust byggð á úreltri
minnisfærslu (mælt 1.003 MB / 8 GB Pro-budget, ekki 424/500 MB).
**ÁKVÖRÐUN (migration `20260611155653_t5_semantic_phase1_5`):** output-viewin
fjögur eru MATERIALIZED með UNIQUE index á natural key; `_sales_base` helst
venjulegt view undir þeim. Mæld MV-latency eftir populate: **0,1–116 ms**.
Composition-bias fixið (§6 #8) fór inn í sama pass. REFRESH-ábyrgð: §4.1.

**Upprunalega v1-tillagan (haldið til sögu, FALLIN): ÖLL views venjuleg
(ekki materialized).** Rökstuðningur:

- **Storage er skorinn auðlind**: gagnagrunnurinn stendur í 424/500 MB.
  Materialized `_sales_base` (173K raðir × ~25 dálkar) væri gróft ~40–60 MB —
  10% af eftirstandandi plássi fyrir hreina afleiðu. Nei.
- **Reiknikostnaður er viðráðanlegur**: þyngsta mynstrið er hash-join 173K×233K
  + aggregate — sekúndubrot á þessari stærðargráðu, og neytendur (mælaborð,
  agent) eru low-QPS. Engin frammistöðuþörf réttlætir refresh-flækju á degi 1.
- **Ferskleiki ókeypis**: venjuleg views endurspegla sales_history-push
  samstundis; materialized þyrftu REFRESH-hooks í run_monthly — ný
  orchestration-skuld sem ekkert kallar á enn.

**Undantekningarstígur ef frammistaða bítur síðar** (mælt, ekki giskað):
materialisera AFLEIÐSLURNAR, aldrei base-ið — output-stærðirnar eru hverfandi:

| View | ~raðir (könnunarmat) | Mat-stærð |
|---|---|---|
| v_street_directory | ~24.300 | ~2–3 MB |
| v_matsvaedi_prices_yearly | 184×21×3 ≈ 9–11K | ~1 MB |
| v_street_prices | ≤4.052×3, post-gat ~3–5K | <1 MB |
| v_postnr_prices_yearly | 153×21×3 ≈ 8–9K | ~1 MB |
| FASI 2 samtals | ~30–40K | ~3–5 MB |

Þ.e. AÐ materialisera öll 12 output-in kostar ~10 MB — en það er ákvörðun
fyrir mælda þörf, með REFRESH-step í run_monthly post-push, ekki v1.

## 6. Opnar spurningar — SVÖR DANNA SKRÁÐ (2026-06-11)

1. **Grant-líkan semantic-views** — SVARAÐ: SAMÞYKKT. Owner-rights
   (security_invoker=false); agent-role fær schema-USAGE + view-SELECT í
   sér gated GRANT-skrefi síðar.
2. **PostgREST-exposure** — SVARAÐ: NEI í v1. semantic er agent/SQL-lag;
   mælaborðs-aðgangur yrði meðvituð síðari ákvörðun (exposed-schemas
   breyting eða public-spegill).
3. **Nýbyggingar-skilgreining** — SVARAÐ: byggar ≥ söluár−2 (17,2% sala
   2020+) per canonical nýbyggingarreglu verkefnisins (samræmi við
   `is_new_build = FULLBUID=0 OR age_at_sale ≤ 2` í training-pipeline).
   Innleitt í _sales_base hér að ofan.
4. **Heat-þröskuldar** — SVARAÐ: standa sem v1-heuristik, MEÐ
   skyldu-kalibrerunartékki gegn ats_dashboard_monthly_heat sögunni við
   fasa-2 creation (bætt í §4 gátlistann sem liður 5). **KALIBRERAÐ
   2026-06-12**: hot 21 / neutral 65 / cold 18 / insufficient 75 á 179
   matsvæðum (hot-median +8,1%, cold −5,1%) — heilbrigð dreifing með
   raunverulegum aðskilnaði; íhaldssamara en ats-þriðjungarnir en ats mælir
   annað signal (ask-to-sale z-skor); þröskuldar standa óbreyttir.
5. **Agent-aðgangur að _sales_base** — SVARAÐ: NEI í v1; agent-role fær
   aggregate-views eingöngu.
6. **ONOTHAEFUR-lekinn upstream** — SVARAÐ: JÁ á backlog sem sér
   verkefnislýsing (root-fix í sales_history-append ferlinu, 420 raðir,
   290 frá 2025–26).
7. **Sveitarfélaganafna-möppun** — SVARAÐ: verður STATÍSKT LOOKUP-VIEW í
   fasa 2 (13. viewið, t.d. v_sveitarfelag_lookup) per canonical-layer
   reglunni — knowledge-pakki agentsins vísar í það en á það ekki.
   **INNLEITT í fasa 2** (v_sveitarfelag_lookup, 64 raðir, 20 íhaldssamir
   aliasar — sjá §2.13).
8. **Composition-bias fix á verð-views** — VIÐBÓT DANNA 2026-06-11 (domain-
   innsýn): median á einingu með háa nýbyggingahlutdeild er nýbyggingaverð,
   ekki verðmæti eldri stofnsins — sá sem verðmetur eldri eign fær of háa
   viðmiðun. Öll þrjú verð-views fengu `n_existing`,
   `median_ppm2_real_existing`, `median_ppm2_nominal_existing`,
   `median_kaupverd_nominal_existing` og `median_ppm2_real_newbuild`
   (samhverfan), öll með 5-sölu þunn-sellu NULL-vörn. Innleitt í fasa-1.5
   migration (20260611155653). Empírískt sannreynt: bítur á
   blönduðum einingum (Ánanaust 227þ. kr/m² bias, Sólbakki Fjarðabyggð
   460þ.), ~0 á alnýjum götum (Sunnusmári) og rótgrónum (Hraunbær) —
   eins og vænta mátti.

---

*Skjalið er un-tracked draft per verklagsreglur (spec-drafts utan repo).
Næsta gated skref: yfirferð Danna → apply_migration creation-lota (FASI 1
fyrst) með gátlistanum í §4.*
