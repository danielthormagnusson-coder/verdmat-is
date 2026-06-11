-- T5 semantic layer — FASI 1.5: materialization + composition-bias fix
-- (spec: D:\verdmat-is\T5_SEMANTIC_VIEWS_v1_draft.md §5-uppfærsla + §6 #8)
-- Output-viewin fjögur verða MATERIALIZED (mæld latency 25,5s sem venjuleg
-- views; storage 1.003 MB / 8 GB budget). _sales_base helst venjulegt view.
-- Composition-bias fix (innsýn Danna 2026-06-11): verð-viewin þrjú fá
-- n_existing + *_existing medians + median_ppm2_real_newbuild, NULL undir
-- 5-sölu þunn-sellu vörn — median á nýbyggingaþungri einingu er nýbyggingaverð,
-- ekki verðmæti eldri stofnsins.
-- MV-in eru sköpuð WITH NO DATA; fyrsta REFRESH er sér operational skref
-- strax á eftir apply (sjá REFRESH-blokk í spec §4). UNIQUE index á natural
-- key hvers MV gerir REFRESH ... CONCURRENTLY mögulegt síðar.
-- Applied via MCP apply_migration 2026-06-11; version 20260611155653 skráð
-- sjálfkrafa í supabase_migrations.schema_migrations.

DROP VIEW IF EXISTS semantic.v_street_directory;
DROP VIEW IF EXISTS semantic.v_matsvaedi_prices_yearly;
DROP VIEW IF EXISTS semantic.v_street_prices;
DROP VIEW IF EXISTS semantic.v_postnr_prices_yearly;

-- ============================================================================
-- 2.1 semantic.v_street_directory — MV (óbreytt skilgreining frá fasa 1)
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_street_directory AS
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

-- ============================================================================
-- 2.2 semantic.v_matsvaedi_prices_yearly — MV + composition-bias dálkar
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_matsvaedi_prices_yearly AS
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

-- ============================================================================
-- 2.3 semantic.v_street_prices — MV + composition-bias dálkar
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_street_prices AS
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
HAVING count(*) >= 5
WITH NO DATA;

CREATE UNIQUE INDEX uq_mv_street_prices
  ON semantic.v_street_prices (street, sveitarfelag, prop_type);

-- ============================================================================
-- 2.4 semantic.v_postnr_prices_yearly — MV + composition-bias dálkar
-- ============================================================================
CREATE MATERIALIZED VIEW semantic.v_postnr_prices_yearly AS
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
