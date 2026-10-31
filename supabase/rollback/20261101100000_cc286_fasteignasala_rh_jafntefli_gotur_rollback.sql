-- ROLLBACK 20261101100000_cc286_fasteignasala_rh_jafntefli_gotur
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
    percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_nominal::double precision)) FILTER (WHERE NOT b.is_ppm2_outlier) AS median_ppm2_nominal,
    percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_real::double precision)) FILTER (WHERE NOT b.is_ppm2_outlier) AS median_ppm2_real,
    percentile_cont(0.25::double precision) WITHIN GROUP (ORDER BY (b.ppm2_nominal::double precision)) FILTER (WHERE NOT b.is_ppm2_outlier) AS p25_ppm2_nominal,
    percentile_cont(0.75::double precision) WITHIN GROUP (ORDER BY (b.ppm2_nominal::double precision)) FILTER (WHERE NOT b.is_ppm2_outlier) AS p75_ppm2_nominal,
        CASE
            WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_real::double precision)) FILTER (WHERE NOT b.is_newbuild AND NOT b.is_ppm2_outlier)
            ELSE NULL::double precision
        END AS median_ppm2_real_existing,
        CASE
            WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_nominal::double precision)) FILTER (WHERE NOT b.is_newbuild AND NOT b.is_ppm2_outlier)
            ELSE NULL::double precision
        END AS median_ppm2_nominal_existing,
        CASE
            WHEN count(*) FILTER (WHERE NOT b.is_newbuild) >= 5 THEN percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.kaupverd_nominal::double precision)) FILTER (WHERE NOT b.is_newbuild)
            ELSE NULL::double precision
        END AS median_kaupverd_nominal_existing,
        CASE
            WHEN count(*) FILTER (WHERE b.is_newbuild) >= 5 THEN percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (b.ppm2_real::double precision)) FILTER (WHERE b.is_newbuild AND NOT b.is_ppm2_outlier)
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

ALTER TABLE semantic.fasteignasala_nyb_stadir DROP COLUMN n_stofu_sameiginl, DROP COLUMN n_utan_rodunar;
ALTER TABLE semantic.fasteignasala_nefnarar DROP COLUMN n_stofu_sameiginl, DROP COLUMN utan_rodunar_astaeda,
  DROP COLUMN velta_utan_rodunar, DROP COLUMN n_utan_rodunar;
ALTER TABLE scraper.fasteignasala_eignun DROP COLUMN utan_rodunar, DROP COLUMN stofur;
