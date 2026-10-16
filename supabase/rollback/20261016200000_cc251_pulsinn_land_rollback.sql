-- cc251 ROLLBACK fyrir 20261016200000_cc251_pulsinn_land — endurreisir semantic.v_hood_heat ORÐRÉTT eins og hún var
-- 16.10.2026 fyrir cc251 (pg_get_viewdef, ekki handskrifað). Eigandi postgres; ACL {postgres=arwdDxtm/postgres,anon=r/postgres,authenticated=r/postgres}; 179 raðir, md5 raða 145898b34f7b82da2c2fccacd3b21734.
BEGIN;
SET TRANSACTION READ WRITE;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '300s';
DROP MATERIALIZED VIEW semantic.v_hood_heat;
CREATE MATERIALIZED VIEW semantic.v_hood_heat AS
 WITH win AS (
         SELECT max(sales_history.thinglystdags) AS data_through
           FROM sales_history
        ), s AS (
         SELECT b.fastnum,
            b.thinglystdags,
            b.sale_year,
            b.sale_quarter,
            b.kaupverd_nominal,
            b.kaupverd_real,
            b.einflm_at_sale,
            b.byggar_at_sale,
            b.onothaefur,
            b.is_newbuild,
            b.ppm2_nominal,
            b.ppm2_real,
            b.street,
            b.sveitarfelag,
            b.postnr,
            b.postheiti,
            b.matsvaedi_numer,
            b.matsvaedi_nafn,
            b.region_tier,
            b.canonical_code,
            b.prop_type,
            b.is_residential,
            b.is_summerhouse,
            b.lat,
            b.lng,
            b.is_ppm2_outlier,
            w.data_through
           FROM (semantic._sales_base b
             CROSS JOIN win w)
          WHERE ((b.onothaefur = 0) AND b.is_residential AND (b.matsvaedi_numer IS NOT NULL) AND (b.thinglystdags >= (w.data_through - '2 years'::interval)))
        ), agg AS (
         SELECT s.matsvaedi_numer,
            mode() WITHIN GROUP (ORDER BY s.matsvaedi_nafn) AS matsvaedi_nafn,
            min(s.data_through) AS data_through,
            count(*) FILTER (WHERE (s.thinglystdags >= (s.data_through - '1 year'::interval))) AS n_12mo,
            count(*) FILTER (WHERE (s.thinglystdags < (s.data_through - '1 year'::interval))) AS n_prev12mo,
            percentile_cont((0.5)::double precision) WITHIN GROUP (ORDER BY ((s.ppm2_real)::double precision)) FILTER (WHERE ((NOT s.is_ppm2_outlier) AND (NOT s.is_newbuild) AND (s.thinglystdags >= (s.data_through - '1 year'::interval)))) AS median_ppm2_real_12mo,
            percentile_cont((0.5)::double precision) WITHIN GROUP (ORDER BY ((s.ppm2_real)::double precision)) FILTER (WHERE ((NOT s.is_ppm2_outlier) AND (NOT s.is_newbuild) AND (s.thinglystdags < (s.data_through - '1 year'::interval)))) AS median_ppm2_real_prev12mo
           FROM s
          GROUP BY s.matsvaedi_numer
        )
 SELECT matsvaedi_numer,
    matsvaedi_nafn,
    n_12mo,
    n_prev12mo,
    round((((n_12mo)::numeric / (NULLIF(n_prev12mo, 0))::numeric) - (1)::numeric), 3) AS volume_change,
    median_ppm2_real_12mo,
    median_ppm2_real_prev12mo,
    round((((median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, (0)::double precision)) - (1)::double precision))::numeric, 3) AS ppm2_real_change,
        CASE
            WHEN ((n_12mo < 10) OR (n_prev12mo < 10)) THEN 'insufficient'::text
            WHEN (((median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, (0)::double precision)) - (1)::double precision) >= (0.05)::double precision) THEN 'hot'::text
            WHEN ((((median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, (0)::double precision)) - (1)::double precision) >= (0.02)::double precision) AND ((((n_12mo)::numeric / (NULLIF(n_prev12mo, 0))::numeric) - (1)::numeric) >= 0.15)) THEN 'hot'::text
            WHEN (((median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, (0)::double precision)) - (1)::double precision) <= ('-0.05'::numeric)::double precision) THEN 'cold'::text
            WHEN ((((median_ppm2_real_12mo / NULLIF(median_ppm2_real_prev12mo, (0)::double precision)) - (1)::double precision) <= ('-0.02'::numeric)::double precision) AND ((((n_12mo)::numeric / (NULLIF(n_prev12mo, 0))::numeric) - (1)::numeric) <= '-0.15'::numeric)) THEN 'cold'::text
            ELSE 'neutral'::text
        END AS heat_bucket,
    data_through
   FROM agg;
CREATE UNIQUE INDEX uq_mv_hood_heat ON semantic.v_hood_heat USING btree (matsvaedi_numer);
ALTER MATERIALIZED VIEW semantic.v_hood_heat OWNER TO postgres;
REVOKE ALL ON semantic.v_hood_heat FROM PUBLIC, anon, authenticated;
GRANT SELECT ON semantic.v_hood_heat TO anon, authenticated;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20261016200000';
NOTIFY pgrst, 'reload schema';
COMMIT;
