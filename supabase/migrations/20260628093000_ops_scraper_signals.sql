-- /ops operator dashboard: aggregate-only scraper signals.
--
-- scraper.* is NOT exposed to PostgREST (the app + nightly scripts read it via a
-- direct psycopg2 connection, never REST). The /ops dashboard reads via supabase-js
-- (REST) with the service-role key, so it cannot reach scraper.* directly
-- ("Invalid schema: scraper"). Rather than expose the whole scraper schema to the
-- API (LEIÐ 1), we keep scraper internal and surface ONLY aggregates through this
-- SECURITY DEFINER function (LEIÐ 2, DECISIONS 2026-06-28).
--
-- Safety: SECURITY DEFINER runs with owner privileges, so it must NEVER return raw
-- rows or any single property — only counts + timestamps. search_path='' + fully
-- qualified names harden it against search-path injection. EXECUTE granted to
-- service_role only (the /ops server component's client), NOT anon.

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

REVOKE ALL ON FUNCTION public.ops_scraper_signals() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.ops_scraper_signals() TO service_role;

NOTIFY pgrst, 'reload schema';
