-- =====================================================================
-- cc276 — SÓTTKVÍ SEM TAFLA: falda mengið (scraper.v_tvitok_falin) geymt í scraper.tvitok_falin
-- Rollback: supabase/rollback/20261026090000_cc276_tvitok_falin_tafla_rollback.sql
--
-- Rót (cc272): lesfletirnir tveir síuðu v_tvitok_falin, CTE yfir alla tvítakaklasa sem var endurmetin
-- í HVERRI lesningu (~200 ms á sitemap-hólf á móti ~10 ms án hennar; 57014 undir byggingarálagi).
--
-- Nú: reglan sjálf er ÓBREYTT í scraper.v_tvitok_falin (cc267 ákvörðun 2: í hverjum klasa birtist elsta
-- LIFANDI eintakið). Hún er lesin aðeins af scraper.endurreikna_tvitok_falin(), sem samstillir töfluna
-- (DELETE það sem fellur út, INSERT það sem bætist við, ein færsla, raðlæst með advisory-lás).
-- Lesfletirnir lesa töfluna (PK-uppfletting). Endurreiknað:
--   * í lok scripts/promote_listings_append.py (á eftir tvítakamerkingu; skrifar status, listed_at, listing_tvitok)
--   * í lok scripts/lifecycle_sweep_mbl.py (skrifar withdrawn_confirmed / confirmed_absent_1 + status)
--   * í þessari migration (upphafsfylling)
-- Þetta eru einu skrifararnir á inntök reglunnar (cc276 §1). Milli keyrslna getur taflan verið á eftir
-- reglunni; frávikið er mælanlegt hvenær sem er: endurreikna_tvitok_falin() skilar baett/eytt.
--
-- Skilgreiningar lesflatanna að öðru leyti ORÐRÉTTAR úr pg_get_viewdef 25.10.2026 (lifandi gerð cc267).
-- Heimildir: taflan og fallið fá ENGAR heimildir anon/authenticated/service_role (lesfletir eru definer-
-- views í eigu postgres); CREATE OR REPLACE VIEW heldur ACL lesflatanna óbreyttum.
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan

CREATE TABLE scraper.tvitok_falin (
  listing_id  bigint  PRIMARY KEY REFERENCES scraper.listings (listing_id) ON DELETE CASCADE
);
COMMENT ON TABLE scraper.tvitok_falin IS
  'cc276: efnisgert mengi scraper.v_tvitok_falin (faldar auglýsingar vegna tvítaka). Aðeins scraper.endurreikna_tvitok_falin() skrifar.';
ALTER TABLE scraper.tvitok_falin ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE scraper.tvitok_falin FROM PUBLIC, anon, authenticated, service_role;

CREATE FUNCTION scraper.endurreikna_tvitok_falin(OUT baett integer, OUT eytt integer, OUT alls integer)
LANGUAGE plpgsql
SET search_path = pg_catalog, scraper
AS $fn$
DECLARE
  n_tafla integer;
BEGIN
  -- tveir samtímis endurreikningar (promote / sóp) raðast í stað þess að rekast á ON CONFLICT
  PERFORM pg_advisory_xact_lock(hashtext('scraper.tvitok_falin'));
  WITH ny AS MATERIALIZED (SELECT listing_id FROM scraper.v_tvitok_falin),
       d AS (DELETE FROM scraper.tvitok_falin t
              WHERE NOT EXISTS (SELECT 1 FROM ny WHERE ny.listing_id = t.listing_id)
             RETURNING 1),
       i AS (INSERT INTO scraper.tvitok_falin (listing_id)
             SELECT listing_id FROM ny
             ON CONFLICT (listing_id) DO NOTHING
             RETURNING 1)
  SELECT (SELECT count(*) FROM i), (SELECT count(*) FROM d), (SELECT count(*) FROM ny)
    INTO baett, eytt, alls;
  SELECT count(*) INTO n_tafla FROM scraper.tvitok_falin;
  IF n_tafla <> alls THEN
    RAISE EXCEPTION 'tvitok_falin: % raðir í töflu eftir endurreikning, reglan gefur %', n_tafla, alls;
  END IF;
END
$fn$;
COMMENT ON FUNCTION scraper.endurreikna_tvitok_falin() IS
  'cc276: samstillir scraper.tvitok_falin við regluna scraper.v_tvitok_falin. baett/eytt = frávik frá síðasta endurreikningi.';
REVOKE ALL ON FUNCTION scraper.endurreikna_tvitok_falin() FROM PUBLIC, anon, authenticated, service_role;

SELECT * FROM scraper.endurreikna_tvitok_falin();
ANALYZE scraper.tvitok_falin;

COMMENT ON VIEW scraper.v_tvitok_falin IS
  'cc267/cc276: REGLAN — allir klasameðlimir nema elsta LIFANDI eintak klasans. Lesfletir lesa efnisgerðu töfluna scraper.tvitok_falin.';

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
           FROM scraper.tvitok_falin tf
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
           FROM scraper.tvitok_falin tf
          WHERE tf.listing_id = l.listing_id));

COMMIT;
