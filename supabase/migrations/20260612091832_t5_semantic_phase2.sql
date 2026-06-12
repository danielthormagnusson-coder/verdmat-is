-- T5 semantic layer — FASI 2: 8 views + v_sveitarfelag_lookup = 13 objektar alls
-- (spec: D:\verdmat-is\T5_SEMANTIC_VIEWS_v1_draft.md §2.5–2.13)
-- Öll MATERIALIZED m. sama mynstri og fasi 1.5 (WITH NO DATA + UNIQUE index á
-- natural key) — lesa öll _sales_base og myndu erfa 25s-latency annars.
-- FORTÉKK staðfest fyrir apply: (1) predictions-einingar median ratio 1,0042
-- (n=9.500) → v_model_vs_sold_by_hood má skapast; (2) heat-kalibrering:
-- hot 21 / neutral 65 / cold 18 / insufficient 75 á 179 matsvæðum →
-- ±5%/±2%+±15% þröskuldar standa óbreyttir.
-- v_summerhouse_market: ppm2 ÓTRIMMAÐUR meðvitað — _sales_base outlier-flagg
-- nær aðeins yfir íbúðarsölur; median er robust og ppm2 er hvort eð er veikur
-- mælikvarði á sumarhús (lóð/hlunnindi bera verðið); leading stat er kaupverd.
-- Applied via MCP apply_migration 2026-06-12; version 20260612091832 skráð
-- sjálfkrafa í supabase_migrations.schema_migrations.

-- ============================================================================
-- 2.5 semantic.v_street_activity — veltusaga götu (engin verð-tölfræði)
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_street_activity AS
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

-- ============================================================================
-- 2.6 semantic.v_sveitarfelag_market — sveitarfélagsyfirlit per ár
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_sveitarfelag_market AS
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

-- ============================================================================
-- 2.7 semantic.v_matsvaedi_trend_quarterly — nýbyggingar ÚR verðtölfræði
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_matsvaedi_trend_quarterly AS
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

-- ============================================================================
-- 2.8 semantic.v_hood_heat — 12mo vs prev-12mo momentum
-- Þröskuldar ±5% / ±2%+±15% staðfestir m. kalibreringartékki (sjá header).
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_hood_heat AS
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

-- ============================================================================
-- 2.9 semantic.v_newbuild_share — nýbyggingahlutdeild + premía per matsvæði/ár
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_newbuild_share AS
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

-- ============================================================================
-- 2.10 semantic.v_model_vs_sold_by_hood — raunsölur 12mo vs iter4 spár
-- EININGA-TÉKK staðfest fyrir apply: median ratio 1,0042 (n=9.500).
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_model_vs_sold_by_hood AS
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

-- ============================================================================
-- 2.11 semantic.v_summerhouse_market — sumarhús per sveitarfélag/ár
-- ppm2 ótrimmaður meðvitað (sjá header-nótu).
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_summerhouse_market AS
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

-- ============================================================================
-- 2.12 semantic.v_price_distribution_by_hood — p10–p90, pooled 3 ár
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_price_distribution_by_hood AS
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
HAVING count(*) >= 10
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_price_distribution_by_hood
  ON semantic.v_price_distribution_by_hood (matsvaedi_numer, prop_type);

-- ============================================================================
-- 2.13 semantic.v_sveitarfelag_lookup — statískt nafna-lookup (§6 #7)
-- Aliasar ÍHALDSSAMIR: aðeins suffix-afleiðingar og "Sveitarfélagið X"-strip,
-- ENGAR bæjarnafna-giskanir (Árborg er Árborg, ekki "Selfoss").
-- Knowledge-pakki agentsins vísar í þetta view, á það ekki.
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_sveitarfelag_lookup AS
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
