-- 20261031140000_cc286_fasteignasala_rh_jafntefli_gotur — cc286 (ákvarðanir Danna 31.10). Additíft + endurgerð eins MV. Beitt með psycopg2 (lock_timeout 10 s),
-- rollback skrifað og sannað á undan (D:\_audit\cc286_markadur\scripts/beita_migration_cc286.py --prof).
--
-- (a) R-H: heildarkaup fjölbýlishúss (Fjölbýli, samningsflötur > 500 m²) utan röðunar — talið í nefnurum.
-- (b) Jafntefli innan dags: samningur sameiginlegur öllum stofum jafnteflisins (eignun.stofur, n_stofu_sameiginl).
-- (c) semantic.v_street_prices: miðgildi/fjórðungar götu síuð með SKYNSEMISMÖRKUM 50.000–2.500.000 kr/m² (nafnverð)
--     í stað landsvísu 1.–99. hundraðshlutamarks (_sales_base.is_ppm2_outlier), sem felldi heilar götur (Bryggjugata:
--     allar 19 sölur, miðgildi NULL). Mælt 31.10 í 5 ára glugganum (47.404 sölur): landssían felldi 960, mörkin fella 46
--     (45 undir 50 þ., 1 yfir 2,5 M: 13 m² flatarmálsvilla); hæsta raunsala 1,86 M kr/m². Annað í MV-inu óbreytt.
--     Einkvæmi vísirinn (REFRESH CONCURRENTLY í daily_sales_refresh) og réttindi anon/authenticated endurgerð.

ALTER TABLE scraper.fasteignasala_eignun
  ADD COLUMN stofur text[],
  ADD COLUMN utan_rodunar text;
COMMENT ON COLUMN scraper.fasteignasala_eignun.stofur IS 'cc286: allar stofur sem fá samninginn (jafntefli innan dags → fleiri en ein); NULL = reiknað fyrir cc286-v1';
COMMENT ON COLUMN scraper.fasteignasala_eignun.utan_rodunar IS 'cc286: ástæða þess að samningur er utan röðunar (heildarkaup_fjolbylishuss) eða NULL';

ALTER TABLE semantic.fasteignasala_nefnarar
  ADD COLUMN n_utan_rodunar integer NOT NULL DEFAULT 0,
  ADD COLUMN velta_utan_rodunar bigint NOT NULL DEFAULT 0,
  ADD COLUMN utan_rodunar_astaeda text,
  ADD COLUMN n_stofu_sameiginl integer NOT NULL DEFAULT 0;
ALTER TABLE semantic.fasteignasala_nyb_stadir
  ADD COLUMN n_utan_rodunar integer NOT NULL DEFAULT 0,
  ADD COLUMN n_stofu_sameiginl integer NOT NULL DEFAULT 0;

DROP MATERIALIZED VIEW semantic.v_street_prices;
CREATE MATERIALIZED VIEW semantic.v_street_prices AS
 WITH win AS (
         SELECT max(sales_history.thinglystdags) AS data_through,
            (max(sales_history.thinglystdags) - '5 years'::interval)::date AS window_start
           FROM sales_history
        )
 SELECT b.street,
    b.sveitarfelag,
        CASE
            WHEN GROUPING(b.prop_type) = 1 THEN 'allt'::text
            ELSE b.prop_type
        END AS prop_type,
    count(*) AS n_sales,
    count(*) FILTER (WHERE b.is_newbuild) AS n_newbuild,
    count(*) FILTER (WHERE NOT b.is_newbuild) AS n_existing,
    round(avg(b.is_newbuild::integer), 3) AS newbuild_share,
    percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.kaupverd_nominal::double precision)) AS median_kaupverd_nominal,
    percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_nominal::double precision)) FILTER (WHERE b.ppm2_nominal >= 50000::numeric AND b.ppm2_nominal <= 2500000::numeric) AS median_ppm2_nominal,
    percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_real::double precision)) FILTER (WHERE b.ppm2_nominal >= 50000::numeric AND b.ppm2_nominal <= 2500000::numeric) AS median_ppm2_real,
    percentile_cont(0.25::double precision) WITHIN GROUP (ORDER BY (b.ppm2_nominal::double precision)) FILTER (WHERE b.ppm2_nominal >= 50000::numeric AND b.ppm2_nominal <= 2500000::numeric) AS p25_ppm2_nominal,
    percentile_cont(0.75::double precision) WITHIN GROUP (ORDER BY (b.ppm2_nominal::double precision)) FILTER (WHERE b.ppm2_nominal >= 50000::numeric AND b.ppm2_nominal <= 2500000::numeric) AS p75_ppm2_nominal,
        CASE
            WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_real::double precision)) FILTER (WHERE NOT b.is_newbuild AND b.ppm2_nominal >= 50000::numeric AND b.ppm2_nominal <= 2500000::numeric)
            ELSE NULL::double precision
        END AS median_ppm2_real_existing,
        CASE
            WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_nominal::double precision)) FILTER (WHERE NOT b.is_newbuild AND b.ppm2_nominal >= 50000::numeric AND b.ppm2_nominal <= 2500000::numeric)
            ELSE NULL::double precision
        END AS median_ppm2_nominal_existing,
        CASE
            WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.kaupverd_nominal::double precision)) FILTER (WHERE NOT b.is_newbuild)
            ELSE NULL::double precision
        END AS median_kaupverd_nominal_existing,
        CASE
            WHEN count(*) FILTER (WHERE b.is_newbuild) >= 5 THEN percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_real::double precision)) FILTER (WHERE b.is_newbuild AND b.ppm2_nominal >= 50000::numeric AND b.ppm2_nominal <= 2500000::numeric)
            ELSE NULL::double precision
        END AS median_ppm2_real_newbuild,
    percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.einflm_at_sale::double precision)) AS median_einflm,
    max(b.thinglystdags) AS last_sale_date,
        CASE
            WHEN count(*) >= 100 THEN 'high'::text
            WHEN count(*) >= 30 THEN 'medium'::text
            WHEN count(*) >= 10 THEN 'low'::text
            ELSE 'thin'::text
        END AS data_quality,
    min(w.window_start) AS window_start,
    min(w.data_through) AS data_through
   FROM semantic._sales_base b
     CROSS JOIN win w
  WHERE b.onothaefur = 0 AND b.is_residential AND b.street IS NOT NULL AND b.sveitarfelag IS NOT NULL AND b.thinglystdags >= w.window_start
  GROUP BY GROUPING SETS ((b.street, b.sveitarfelag, b.prop_type), (b.street, b.sveitarfelag))
 HAVING count(*) >= 5;
CREATE UNIQUE INDEX uq_mv_street_prices ON semantic.v_street_prices USING btree (street, sveitarfelag, prop_type);
GRANT SELECT ON semantic.v_street_prices TO anon, authenticated;
COMMENT ON MATERIALIZED VIEW semantic.v_street_prices IS 'cc286: miðgildi síuð með skynsemismörkum 50.000–2.500.000 kr/m² (nafnverð), ekki landsvísu-hundraðshluta';
