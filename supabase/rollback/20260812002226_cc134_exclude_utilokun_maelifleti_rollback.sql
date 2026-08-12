-- ROLLBACK · cc134 KOSTUR (c) — EXCLUDE UNDANSKILIÐ Á MÆLIFLÖTUNUM
-- ============================================================================
-- Endurheimtir ástandið eins og það var 12.08.2026, þ.e. útgáfurnar úr
--   supabase/migrations/20260627211837_extraction_layer.sql   (v_expected_vs_real)
--   supabase/migrations/20260628093000_ops_scraper_signals.sql (ops_scraper_signals)
-- báðar afritaðar hér ÚR LIFANDI DB (`pg_get_viewdef` / `pg_get_functiondef`,
-- 12.08), ekki endursagðar eftir minni.
--
-- ENGIN GÖGN ERU Í HÚFI. cc134 (c) snertir enga töflu og enga röð — hún breytir
-- aðeins tveimur sýnum og einu falli. Kostur (b) (eyðing 2.372 raða) var FELLDUR,
-- svo það er ekkert að endurheimta úr afriti.
--
-- ATH. RÖÐIN. `v_expected_vs_real` verður að fara AFTUR Á TÖFLUNA áður en
-- `v_expected_vs_real_all` er sleppt — annars fellur DROP á dependency.
-- ============================================================================

-- ── 1. mæliflöturinn aftur beint á töfluna (34 dálkar -> 33) ────────────────
-- CREATE OR REPLACE getur ekki FJARLÆGT dálk, svo hér þarf DROP + CREATE.
-- Það er skaðlaust: mælt cc134 12.08 — ekkert object er skilgreint ofan á
-- sýninni (pg_depend/pg_rewrite: aðeins hún sjálf) og engin grants nema eiganda.
DROP VIEW IF EXISTS scraper.v_expected_vs_real;

CREATE VIEW scraper.v_expected_vs_real AS
SELECT
  val.valuation_id,
  val.fastnum,
  val.source_listing_id,
  val.lysing_hash,
  val.expected_base,
  val.expected_extraction,
  (val.expected_extraction - val.expected_base)                        AS extraction_gap,
  val.extraction_applied,
  val.model_version,
  val.valued_at,
  l.unit_key, l.category, l.tenure, l.sub_type, l.size_sqm, l.byggar, l.addr_text,
  l.price_amount                                                       AS asking_price,
  ext.extraction, ext.extraction_schema_version, ext.extraction_model,
  u.n_relistings, u.days_on_market, u.first_listed_at, u.last_seen_at,
  s.kaupverd_nominal                                                   AS real_price,
  s.thinglystdags                                                      AS sold_at,
  (s.fastnum IS NOT NULL)                                              AS sold,
  CASE WHEN s.kaupverd_nominal > 0 AND val.expected_base IS NOT NULL
       THEN (val.expected_base - s.kaupverd_nominal)::numeric / s.kaupverd_nominal END
                                                                       AS base_pct_error,
  CASE WHEN s.kaupverd_nominal > 0 AND val.expected_extraction IS NOT NULL
       THEN (val.expected_extraction - s.kaupverd_nominal)::numeric / s.kaupverd_nominal END
                                                                       AS extraction_pct_error,
  to_char(s.thinglystdags, 'YYYY-MM')                                  AS sale_ym,
  ci.cpi                                                               AS cpi_at_sale,
  ph.price_trajectory
FROM scraper.listing_valuations val
LEFT JOIN scraper.listings l
       ON l.source = 'mbl' AND l.source_listing_id = val.source_listing_id
LEFT JOIN scraper.listing_extractions ext ON ext.lysing_hash = val.lysing_hash
LEFT JOIN scraper.v_units u ON u.unit_key = l.unit_key
LEFT JOIN LATERAL (
  SELECT s2.fastnum, s2.kaupverd_nominal, s2.thinglystdags
  FROM public.sales_history s2
  WHERE s2.fastnum = val.fastnum
    AND s2.onothaefur = 0
    AND s2.thinglystdags >= val.valued_at::date
  ORDER BY s2.thinglystdags ASC
  LIMIT 1
) s ON true
LEFT JOIN public.cpi_index ci ON ci.year_month = to_char(s.thinglystdags, 'YYYY-MM')
LEFT JOIN LATERAL (
  SELECT jsonb_agg(jsonb_build_object('observed_at', p.observed_at,
                                      'price', p.price_amount)
                   ORDER BY p.observed_at) AS price_trajectory
  FROM scraper.listing_price_history p
  JOIN scraper.listings l3 ON l3.source = p.source
                          AND l3.source_listing_id = p.source_listing_id
  WHERE l3.unit_key = l.unit_key
) ph ON true;

-- ── 2. heimildarsýnin burt ──────────────────────────────────────────────────
DROP VIEW IF EXISTS scraper.v_expected_vs_real_all;

-- ── 3. /ops teljararnir í fyrra horf (ósíaðir) ─────────────────────────────
CREATE OR REPLACE FUNCTION public.ops_scraper_signals()
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT jsonb_build_object(
    'chain', jsonb_build_object(
      'mbl_last_seen',           (SELECT max(last_seen_at) FROM scraper.listings WHERE source::text = 'mbl'),
      'myigloo_last_seen',       (SELECT max(last_seen_at) FROM scraper.listings WHERE source::text = 'myigloo'),
      'canonical_last_promoted', (SELECT max(last_promoted_at) FROM scraper.listings_canonical),
      'price_history_max',       (SELECT max(observed_at) FROM scraper.listing_price_history),
      'extraction_max',          (SELECT max(extracted_at) FROM scraper.listing_extractions),
      'valuation_max',           (SELECT max(valued_at) FROM scraper.listing_valuations)
    ),
    'extraction', (
      SELECT jsonb_build_object(
        'count_latest_day', (
          SELECT count(*) FROM scraper.listing_extractions
          WHERE extracted_at >= date_trunc('day', (SELECT max(extracted_at) FROM scraper.listing_extractions))),
        'val_count_latest_day', (
          SELECT count(*) FROM scraper.listing_valuations
          WHERE valued_at >= date_trunc('day', (SELECT max(valued_at) FROM scraper.listing_valuations))),
        'model',             e.extraction_model,
        'schema_version',    e.extraction_schema_version,
        'total_extractions', (SELECT count(*) FROM scraper.listing_extractions),
        'total_valuations',  (SELECT count(*) FROM scraper.listing_valuations)
      )
      FROM scraper.listing_extractions e
      ORDER BY e.extracted_at DESC NULLS LAST
      LIMIT 1
    ),
    'backlog', jsonb_build_object(
      'live_res_sale', (
        SELECT count(*) FROM scraper.listings_canonical c
        WHERE c.category::text = 'residential' AND c.tenure::text = 'sale' AND c.withdrawn_at IS NULL),
      'live_res_sale_valued', (
        SELECT count(DISTINCT c.canonical_id)
        FROM scraper.listings_canonical c
        JOIN scraper.listing_valuations v ON v.source_listing_id = c.source_listing_id
        WHERE c.category::text = 'residential' AND c.tenure::text = 'sale' AND c.withdrawn_at IS NULL),
      'unprocessed', (
        SELECT count(*) FROM scraper.listings_canonical c
        WHERE c.category::text = 'residential' AND c.tenure::text = 'sale' AND c.withdrawn_at IS NULL
          AND NOT EXISTS (SELECT 1 FROM scraper.listing_valuations v WHERE v.source_listing_id = c.source_listing_id))
    ),
    'sources', jsonb_build_object(
      'mbl',            (SELECT count(*) FROM scraper.listings_canonical WHERE source::text = 'mbl'),
      'myigloo',        (SELECT count(*) FROM scraper.listings_canonical WHERE source::text = 'myigloo'),
      'visir',          (SELECT count(*) FROM scraper.listings_canonical WHERE source::text = 'visir'),
      'live',           (SELECT count(*) FROM scraper.listings_canonical WHERE withdrawn_at IS NULL),
      'withdrawn',      (SELECT count(*) FROM scraper.listings_canonical WHERE withdrawn_at IS NOT NULL),
      'total',          (SELECT count(*) FROM scraper.listings_canonical),
      'fastnum_filled', (SELECT count(*) FROM scraper.listings_canonical WHERE fastnum IS NOT NULL)
    ),
    'generated_at', now()
  );
$$;

REVOKE ALL ON FUNCTION public.ops_scraper_signals() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ops_scraper_signals() TO service_role;

-- ── 4. Python-síunni (kostur a) er EKKI rúllað til baka hér ─────────────────
-- Hún býr í scripts/extraction_engine.py og er sjálfstæð ákvörðun borðsins.
-- Sé henni líka rúllað til baka verður `/ops` `unprocessed` að bera 109-gólfið
-- aftur — það er samhengið, ekki villa. Bakfærsla á (a) er git revert á þeirri
-- einu línu, ekki SQL.
