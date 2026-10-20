-- =====================================================================
-- cc267 f.2 — SÓTTKVÍ mbl-tvítaka (merking, ekki eyðing)
-- Rollback: supabase/rollback/20261021090000_cc267_tvitok_sottkvi_rollback.sql
--
-- scraper.listing_tvitok: ein röð per tvítak (listing_id) með frumriti klasans (frumrit_listing_id =
-- klasalykill: elsta röð klasans skv. scripts/tvitak_regla.py; regla_version skráð per röð).
-- Raðirnar í scraper.listings standa óbreyttar.
--
-- scraper.v_tvitok_falin (cc267 ákvörðun 2, Danni 20.10): ENDURMAT við hverja lesningu — í hverjum
-- klasa (frumrit + tvítök) BIRTIST elsta LIFANDI eintakið (status active, hvorki withdrawn_confirmed
-- né confirmed_absent_1), öll hin eru falin. Taki mbl frumritið niður en tvítak lifir, birtist elsta
-- lifandi tvítakið, svo eign hverfur aldrei úr „Á sölu" meðan eitthvert eintak lifir. Ekkert lifandi ->
-- frumritið er „sýnt" (grunnsíur sýnanna fella það hvort eð er).
--
-- Lesfletirnir tveir sem allt lifandi les sía út v_tvitok_falin:
--   scraper.v_eign_virk_auglysing  (/eign „Á sölu", svæði, verðvakt-nefnari, nybygging virk, agent)
--   scraper.v_leit_listings        (/leit, Púlsinn „Framboð núna", leiga, agent frambodsleit)
-- Sían er í WHERE, svo er_nyjasta_birting (row_number) reiknast eftir síun.
-- Skilgreiningar að öðru leyti ORÐRÉTTAR úr pg_get_viewdef 20.10.2026 (lifandi gerð; v_leit_listings
-- á uppruna í verdmat-ai/supabase/migrations — þessi migration tekur við henni).
--
-- Tóm tafla = engin breyting á lifandi tölu. Merking: D:\_audit\cc267_tvitok\merkja_tvitok.py --beita,
-- síðan scripts/promote_listings_append.py (vörnin virkjast þegar taflan er til).
-- Ekki app-lesin beint: RLS á töflu, engar heimildir anon/authenticated (lesfletir eru definer-views).
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan

CREATE TABLE scraper.listing_tvitok (
  listing_id          bigint      PRIMARY KEY REFERENCES scraper.listings (listing_id) ON DELETE CASCADE,
  frumrit_listing_id  bigint      NOT NULL REFERENCES scraper.listings (listing_id) ON DELETE CASCADE,
  regla_version       text        NOT NULL,
  merkt_at            timestamptz NOT NULL DEFAULT now(),
  merkt_af            text        NOT NULL,
  CONSTRAINT listing_tvitok_ekki_sjalft_chk CHECK (listing_id <> frumrit_listing_id)
);
CREATE INDEX listing_tvitok_frumrit_idx ON scraper.listing_tvitok (frumrit_listing_id);

COMMENT ON TABLE scraper.listing_tvitok IS
  'cc267: sóttkví mbl-tvítaka (sama efni innan 10 mín, scripts/tvitak_regla.py). Lesfletir sía út scraper.v_tvitok_falin.';

ALTER TABLE scraper.listing_tvitok ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE scraper.listing_tvitok FROM PUBLIC, anon, authenticated;

CREATE VIEW scraper.v_tvitok_falin AS
WITH klasi AS (
         SELECT t.frumrit_listing_id AS klasi_id, t.frumrit_listing_id AS listing_id
           FROM scraper.listing_tvitok t
          GROUP BY t.frumrit_listing_id
        UNION ALL
         SELECT t.frumrit_listing_id, t.listing_id
           FROM scraper.listing_tvitok t
        ), medlimir AS (
         SELECT k.klasi_id, k.listing_id, l.listed_at,
            (l.status = 'active'::text AND NOT (EXISTS ( SELECT 1
                   FROM scraper.listing_lifecycle_events e
                  WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id
                    AND (e.event_type = ANY (ARRAY['withdrawn_confirmed'::scraper.lifecycle_event_enum,
                                                   'confirmed_absent_1'::scraper.lifecycle_event_enum]))))) AS lifandi
           FROM klasi k
             JOIN scraper.listings l ON l.listing_id = k.listing_id
        ), synt AS (
         SELECT DISTINCT ON (m.klasi_id) m.klasi_id, m.listing_id
           FROM medlimir m
          ORDER BY m.klasi_id, m.lifandi DESC, m.listed_at, m.listing_id
        )
 SELECT DISTINCT m.listing_id
   FROM medlimir m
  WHERE NOT (EXISTS ( SELECT 1 FROM synt s WHERE s.klasi_id = m.klasi_id AND s.listing_id = m.listing_id));

COMMENT ON VIEW scraper.v_tvitok_falin IS
  'cc267: auglýsingar faldar vegna tvítaka — allir klasameðlimir nema elsta LIFANDI eintak klasans.';
REVOKE ALL ON TABLE scraper.v_tvitok_falin FROM PUBLIC, anon, authenticated;

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

COMMIT;
