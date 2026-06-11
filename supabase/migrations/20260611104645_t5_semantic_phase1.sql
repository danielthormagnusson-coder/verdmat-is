-- T5 semantic layer — FASI 1 (spec: D:\verdmat-is\T5_SEMANTIC_VIEWS_v1_draft.md)
-- semantic schema + _sales_base + v_street_directory + v_matsvaedi_prices_yearly
--   + v_street_prices + v_postnr_prices_yearly
-- Owner-rights views (EKKI security_invoker) per §6 svar #1.
-- ENGIN GRANT-skref hér — agent-role er sér gated skref síðar.
-- Schema er EKKI í PostgREST exposed-schemas (per §6 svar #2).
-- Applied via MCP apply_migration 2026-06-11; version 20260611104645 skráð
-- sjálfkrafa í supabase_migrations.schema_migrations (ekkert repair þarf).

CREATE SCHEMA IF NOT EXISTS semantic;

-- ============================================================================
-- 2.0 semantic._sales_base — internal grunnview
-- ============================================================================
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

-- ============================================================================
-- 2.1 semantic.v_street_directory — router-view (gata × sveitarfélag)
-- ============================================================================
CREATE OR REPLACE VIEW semantic.v_street_directory AS
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
GROUP BY street, sveitarfelag;

-- ============================================================================
-- 2.2 semantic.v_matsvaedi_prices_yearly
-- ============================================================================
CREATE OR REPLACE VIEW semantic.v_matsvaedi_prices_yearly AS
SELECT
  b.matsvaedi_numer,
  mode() WITHIN GROUP (ORDER BY b.matsvaedi_nafn)             AS matsvaedi_nafn,
  mode() WITHIN GROUP (ORDER BY b.region_tier)                AS region_tier,
  b.sale_year,
  CASE WHEN GROUPING(b.prop_type) = 1 THEN 'allt' ELSE b.prop_type END AS prop_type,
  count(*)                                                    AS n_sales,
  count(*) FILTER (WHERE b.is_newbuild)                       AS n_newbuild,
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
);

-- ============================================================================
-- 2.3 semantic.v_street_prices — pooled 5 ára gluggi, n-gat ≥5
-- ============================================================================
CREATE OR REPLACE VIEW semantic.v_street_prices AS
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
HAVING count(*) >= 5;     -- n-gat: raðir undir 5 sölum eru EKKI birtar

-- ============================================================================
-- 2.4 semantic.v_postnr_prices_yearly
-- ============================================================================
CREATE OR REPLACE VIEW semantic.v_postnr_prices_yearly AS
SELECT
  b.postnr,
  mode() WITHIN GROUP (ORDER BY b.postheiti)                  AS postheiti_mode,
  mode() WITHIN GROUP (ORDER BY b.region_tier)                AS region_tier,
  b.sale_year,
  CASE WHEN GROUPING(b.prop_type) = 1 THEN 'allt' ELSE b.prop_type END AS prop_type,
  count(*)                                                    AS n_sales,
  count(*) FILTER (WHERE b.is_newbuild)                       AS n_newbuild,
  round(avg(b.is_newbuild::int), 3)                           AS newbuild_share,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_nominal)  AS median_kaupverd_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.kaupverd_real)     AS median_kaupverd_real,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_nominal)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_nominal,
  percentile_cont(0.5) WITHIN GROUP (ORDER BY b.ppm2_real)
    FILTER (WHERE NOT b.is_ppm2_outlier)                      AS median_ppm2_real,
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
);
