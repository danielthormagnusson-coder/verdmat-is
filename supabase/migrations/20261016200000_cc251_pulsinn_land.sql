-- =====================================================================
-- cc251 f.1 — Púlsinn, leið (a) (Danni 16.10): landssumma kaupsamninga telur ALLAR nothæfar íbúðasölur,
-- líka þær sem eiga sér ekkert matsvæði (369 í nýja glugganum, 289 nýbyggingar; 2 í þeim fyrri — cc249 m3).
-- Hverfaraðirnar eru ÓBREYTTAR (sömu 10 dálkar, sama röð, sömu gildi; sannað með md5 í --prof).
-- Viðbót: tveir aftastir dálkar n_12mo_land / n_prev12mo_land (sama gildi á hverri röð, sami gluggi og sami
-- þinglýsingarás og n_12mo/n_prev12mo, aðeins án síunnar matsvaedi_numer IS NOT NULL).
-- Framendinn (lib/markadur-puls.js) les nýju dálkana; lifandi www breytist því ekki fyrr en framendinn er pushaður.
-- Rollback (skrifuð á undan, orðrétt úr pg_get_viewdef): supabase/rollback/20261016200000_cc251_pulsinn_land_rollback.sql
-- Skil: D:\_audit\cc251_manadarsala\SKIL_CC251.md · grunnur D:\_audit\cc249_manadarsala\SKIL_CC249.md
-- =====================================================================
BEGIN;
SET TRANSACTION READ WRITE;
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
        ), land AS (
         SELECT count(*) FILTER (WHERE b.thinglystdags >= (w.data_through - '1 year'::interval)) AS n_12mo_land,
            count(*) FILTER (WHERE b.thinglystdags < (w.data_through - '1 year'::interval)) AS n_prev12mo_land
           FROM semantic._sales_base b
             CROSS JOIN win w
          WHERE b.onothaefur = 0 AND b.is_residential AND b.thinglystdags >= (w.data_through - '2 years'::interval)
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
    agg.data_through,
    land.n_12mo_land,
    land.n_prev12mo_land
   FROM agg
     CROSS JOIN land;
CREATE UNIQUE INDEX uq_mv_hood_heat ON semantic.v_hood_heat USING btree (matsvaedi_numer);
ALTER MATERIALIZED VIEW semantic.v_hood_heat OWNER TO postgres;
REVOKE ALL ON semantic.v_hood_heat FROM PUBLIC, anon, authenticated;
GRANT SELECT ON semantic.v_hood_heat TO anon, authenticated;
COMMENT ON COLUMN semantic.v_hood_heat.n_12mo_land IS
  'cc251: nothæfar íbúðasölur (onothaefur=0, is_residential) síðustu 12 mán á þinglýsingardegi, ALLT landið, líka án matsvæðis. Sama gildi á hverri röð — EKKI leggja saman yfir raðir.';
COMMENT ON COLUMN semantic.v_hood_heat.n_prev12mo_land IS
  'cc251: sama og n_12mo_land fyrir 12 mánuðina á undan.';
NOTIFY pgrst, 'reload schema';
COMMIT;
