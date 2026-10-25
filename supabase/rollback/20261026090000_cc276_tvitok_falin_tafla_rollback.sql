-- Rollback 20261026090000_cc276_tvitok_falin_tafla: lesfletirnir aftur á endurmat við lestur (scraper.v_tvitok_falin, gerð cc267,
-- pg_get_viewdef 25.10.2026 orðrétt), fall og tafla felld. Reglan v_tvitok_falin stendur.
BEGIN;
SET TRANSACTION READ WRITE;

CREATE OR REPLACE VIEW scraper.v_eign_virk_auglysing AS
 SELECT l.listing_id,
    l.source,
    l.fastnum,
    l.tenure,
    l.category,
    l.price_amount,
    l.is_price_on_request,
    ph.asett_verd_dags,
    l.listed_at,
    l.first_seen_at,
    l.last_seen_at,
    l.er_atvinnuhusnaedi,
    l.lysing,
    l.agency_name,
    l.agency_phone,
    l.agency_email,
    l.agency_addr,
    l.agency_postcode,
    l.agency_url
   FROM scraper.listings l
     LEFT JOIN LATERAL ( SELECT max(ph2.observed_at) AS asett_verd_dags
           FROM scraper.listing_price_history ph2
          WHERE ph2.source = l.source AND ph2.source_listing_id = l.source_listing_id) ph ON true
  WHERE l.status = 'active'::text AND NOT (EXISTS ( SELECT 1
           FROM scraper.listing_lifecycle_events e
          WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id AND e.event_type = 'withdrawn_confirmed'::scraper.lifecycle_event_enum)) AND NOT (EXISTS ( SELECT 1
           FROM scraper.listing_lifecycle_events ea
          WHERE ea.source = l.source AND ea.source_listing_id = l.source_listing_id AND ea.event_type = 'confirmed_absent_1'::scraper.lifecycle_event_enum)) AND (l.addr_text IS NULL OR l.addr_text !~* '(\yseld\y|\yseldar\y|\yseldur\y|\ysold\y|\yfrátekin\y|\yfrátekið\y)'::text) AND NOT (EXISTS ( SELECT 1
           FROM scraper.v_tvitok_falin tf
          WHERE tf.listing_id = l.listing_id));

CREATE OR REPLACE VIEW scraper.v_leit_listings AS
 SELECT l.listing_id,
    l.source,
    l.source_listing_id,
    l.fastnum,
    l.tenure,
    l.category,
    l.sub_type,
    l.tegund_raw,
    l.price_amount,
    l.is_price_on_request,
    ph.asett_verd_dags,
    l.size_sqm,
    l.rooms,
    l.bedrooms,
    l.bathrooms,
    COALESCE(l.byggar::numeric, p.byggar) AS byggar,
    l.addr_text,
    l.addr_postcode,
    btrim(COALESCE(p.sveitarfelag, l.addr_municipality, pn.sveitarfelag)) AS sveitarfelag,
    btrim(p.matsvaedi_nafn) AS hverfi,
    p.matsvaedi_numer,
    COALESCE(l.lat::double precision, p.lat) AS lat,
    COALESCE(l.lng::double precision, p.lng) AS lng,
    l.photos_json,
    p.first_photo_url,
    l.listed_at,
    l.first_seen_at,
    l.last_seen_at,
    l.br_dags,
    (EXISTS ( SELECT 1
           FROM scraper.listing_lifecycle_events ea
          WHERE ea.source = l.source AND ea.source_listing_id = l.source_listing_id AND ea.event_type = 'confirmed_absent_1'::scraper.lifecycle_event_enum)) AS er_fjarveru_flaggad,
    (EXISTS ( SELECT 1
           FROM predictions pr
          WHERE pr.fastnum = l.fastnum AND pr.real_pred_mean IS NOT NULL)) AS er_metanleg,
        CASE
            WHEN l.is_price_on_request OR l.price_amount IS NULL OR l.size_sqm IS NULL OR l.size_sqm <= 0::numeric THEN NULL::numeric
            ELSE round(l.price_amount::numeric / l.size_sqm)
        END AS fermetraverd_kr,
    l.mublad,
    p.is_new_build,
    l.er_atvinnuhusnaedi,
    row_number() OVER (PARTITION BY l.tenure, l.category, (COALESCE(l.fastnum::text, 'addr:'::text || lower(btrim(l.addr_text)))), l.price_amount, l.size_sqm ORDER BY l.listed_at DESC NULLS LAST, l.listing_id DESC) = 1 AS er_nyjasta_birting,
    l.addr_text ~* '(\yseld\y|\yseldar\y|\yseldur\y|\ysold\y|\yfrátekin\y|\yfrátekið\y)'::text AS er_auglyst_seld,
    l.price_amount IS NOT NULL AND (EXISTS ( SELECT 1
           FROM scraper.listing_price_history ph3
          WHERE ph3.source = l.source AND ph3.source_listing_id = l.source_listing_id AND ph3.price_amount > l.price_amount)) AS verd_laekkad,
        CASE
            WHEN l.tenure = 'rent'::text THEN c.available_from
            ELSE NULL::date
        END AS laus_fra,
        CASE
            WHEN l.tenure = 'rent'::text THEN c.lease_term_class::text
            ELSE NULL::text
        END AS leigutimi,
        CASE
            WHEN l.tenure = 'rent'::text THEN c.deposit_isk
            ELSE NULL::numeric
        END AS trygging_isk
   FROM scraper.listings l
     LEFT JOIN v_properties p USING (fastnum)
     LEFT JOIN scraper.listings_canonical c ON c.source = l.source AND c.source_listing_id = l.source_listing_id
     LEFT JOIN LATERAL ( SELECT pp.sveitarfelag
           FROM properties pp
          WHERE l.addr_postcode ~ '^[0-9]+$'::text AND pp.postnr = l.addr_postcode::integer AND pp.sveitarfelag IS NOT NULL
         LIMIT 1) pn ON true
     LEFT JOIN LATERAL ( SELECT max(ph2.observed_at) AS asett_verd_dags
           FROM scraper.listing_price_history ph2
          WHERE ph2.source = l.source AND ph2.source_listing_id = l.source_listing_id) ph ON true
  WHERE l.status = 'active'::text AND NOT (EXISTS ( SELECT 1
           FROM scraper.listing_lifecycle_events e
          WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id AND e.event_type = 'withdrawn_confirmed'::scraper.lifecycle_event_enum)) AND NOT (EXISTS ( SELECT 1
           FROM scraper.v_tvitok_falin tf
          WHERE tf.listing_id = l.listing_id));

COMMENT ON VIEW scraper.v_tvitok_falin IS
  'cc267: auglýsingar faldar vegna tvítaka — allir klasameðlimir nema elsta LIFANDI eintak klasans.';

DROP FUNCTION scraper.endurreikna_tvitok_falin();
DROP TABLE scraper.tvitok_falin;

COMMIT;
