-- 20260601122916_scraper_schema_init.sql
-- SCRAPER_SPEC_v2 §2.3 (canonical) + §2.4 (views) + §2.5 (fastnum resolution columns)
--
-- Net-new, additive. ZERO impact on existing public.* tables/views.
-- Home: new `scraper` schema inside the existing verdmat-is Supabase (spec §2.3, LOCKED (b)).
-- Public read: column-allowlisted security_invoker views (spec §2.4-B; Group B least-privilege).
-- Writes: service-role only (staging-then-sync, spec #2B). anon/authenticated get SELECT on
--   the allowlisted columns + the v_* views only.
--
-- Rollback: no paired file (repo convention is transactional apply, not paired rollbacks).
--   To undo later, write a NEW timestamped forward migration: DROP SCHEMA scraper CASCADE.
--
-- PRE-APPLY NOTES (see session report):
--   * scraper schema must be added to the PostgREST exposed-schemas config for the v_* views
--     to be reachable via the REST API (dashboard/config, not DDL).
--   * residential views join public.v_properties (security_invoker; respects the Group B view
--     layer) — its byggar/einflm/matsvaedi_nafn are anon-readable (verified FIX 3, 2026-06-01).
--   * fastnum FK is ON DELETE NO ACTION (FIX 2): matches the properties soft-delete discipline
--     (deregistered flag, not row delete) and avoids the ck_fastnum_resolution conflict.

BEGIN;

-- ── extensions (idempotent; included for fresh-project safety) ──
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS postgis;    -- geography(Point) for ix_lc_geo (spec §2.3-E geo note)

-- ── schema ──
CREATE SCHEMA IF NOT EXISTS scraper;

-- ── enum axes (spec §2.3-A, §2.5-B) ──
CREATE TYPE scraper.category_enum    AS ENUM ('residential','commercial','plot','other');
CREATE TYPE scraper.tenure_enum      AS ENUM ('sale','rent');
CREATE TYPE scraper.lease_term_enum  AS ENUM ('short_term','long_term','unspecified');
CREATE TYPE scraper.fastnum_res_enum AS ENUM
  ('source_supplied','address_match','geo_match','manual','unresolvable_by_design');

-- ── canonical table (spec §2.3-B + §2.5-B) ──
CREATE TABLE scraper.listings_canonical (
  -- identity
  canonical_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  -- source provenance (current owner; churns across re-dedup)
  source               text NOT NULL,
  source_listing_id    text NOT NULL,
  url                  text NOT NULL,
  secondary_source_ids text[] NOT NULL DEFAULT '{}',
  -- lifecycle
  first_seen_at        timestamptz NOT NULL,
  last_seen_at         timestamptz NOT NULL,
  withdrawn_at         timestamptz,
  is_active            boolean NOT NULL DEFAULT true,   -- maintained by nightly promotion (spec §2.3-B)
  -- pricing
  price_amount         numeric NOT NULL,
  price_currency       text NOT NULL DEFAULT 'ISK',
  -- descriptive
  listing_title        text,
  lysing               text,                            -- raw description, for LLM extraction
  -- taxonomy (TAXONOMY_v2)
  category             scraper.category_enum NOT NULL,
  tenure               scraper.tenure_enum   NOT NULL,
  sub_type             text NOT NULL,
  tegund_raw           text NOT NULL,
  lease_term_class     scraper.lease_term_enum,         -- NULL when tenure='sale'
  -- geo + size
  fastnum              bigint REFERENCES public.properties(fastnum) ON DELETE NO ACTION,
  lat                  numeric,
  lng                  numeric,
  geog                 geography(Point,4326) GENERATED ALWAYS AS (
                         CASE WHEN lat IS NOT NULL AND lng IS NOT NULL
                              THEN ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography
                              ELSE NULL END
                       ) STORED,
  area_sqm             numeric,
  rooms                numeric,
  bedrooms             numeric,
  bathrooms            numeric,
  addr_text            text,
  addr_municipality    text,
  addr_postcode        text,
  -- rent-specific
  deposit_isk          numeric,
  available_from       date,
  -- photos (URLs only; byte archival = §5 #5, deferred)
  photos_json          jsonb NOT NULL DEFAULT '[]'::jsonb,
  -- audit / dedup provenance
  canonical_version          integer NOT NULL DEFAULT 1,
  last_promoted_at           timestamptz NOT NULL,
  surviving_parse_id         bigint,                    -- opaque local parsed_* id (across sync boundary)
  surviving_source_priority  integer NOT NULL,          -- snapshot at promotion (not a live lookup)
  -- fastnum resolution (spec §2.5-B)
  fastnum_resolution_method     scraper.fastnum_res_enum, -- NULL=not-yet-attempted; 'unresolvable_by_design'=permanent NULL
  fastnum_resolution_confidence numeric,                  -- 0..1; NULL for unresolved + unresolvable_by_design
  fastnum_resolution_at         timestamptz,

  CONSTRAINT uq_source_listing UNIQUE (source, source_listing_id),
  CONSTRAINT ck_rent_lease  CHECK (tenure = 'sale' OR lease_term_class IS NOT NULL),
  CONSTRAINT ck_plot_area   CHECK (category <> 'plot' OR area_sqm IS NOT NULL),
  CONSTRAINT ck_price_pos   CHECK (price_amount > 0),
  CONSTRAINT ck_fastnum_pos CHECK (fastnum IS NULL OR fastnum > 0),
  CONSTRAINT ck_fastnum_resolution CHECK (
        (fastnum IS NULL
           AND (fastnum_resolution_method IS NULL
                OR fastnum_resolution_method = 'unresolvable_by_design'))
     OR (fastnum IS NOT NULL
           AND fastnum_resolution_method IN ('source_supplied','address_match','geo_match','manual')
           AND fastnum_resolution_confidence BETWEEN 0 AND 1)
  )
);

-- ── indexes (spec §2.3-E) ──
CREATE INDEX ix_lc_fastnum      ON scraper.listings_canonical (fastnum) WHERE fastnum IS NOT NULL;
CREATE INDEX ix_lc_segment      ON scraper.listings_canonical (category, tenure, sub_type);
CREATE INDEX ix_lc_active       ON scraper.listings_canonical (is_active, last_seen_at);
CREATE INDEX ix_lc_price_active ON scraper.listings_canonical (price_amount) WHERE is_active;
CREATE INDEX ix_lc_geo          ON scraper.listings_canonical USING gist (geog);

-- ── RLS + column-allowlist grants (spec §2.4-B; Group B posture) ──
ALTER TABLE scraper.listings_canonical ENABLE ROW LEVEL SECURITY;
CREATE POLICY public_read ON scraper.listings_canonical
  FOR SELECT TO anon, authenticated USING (true);   -- rows pass; columns gated by GRANT below
REVOKE ALL ON scraper.listings_canonical FROM anon, authenticated;
GRANT USAGE ON SCHEMA scraper TO anon, authenticated;
GRANT SELECT (canonical_id, source, url, first_seen_at, last_seen_at, withdrawn_at,
              is_active, price_amount, price_currency, listing_title, lysing,
              category, tenure, sub_type, tegund_raw, lease_term_class,
              fastnum, lat, lng, area_sqm, rooms, bedrooms, bathrooms,
              addr_text, addr_municipality, addr_postcode,
              deposit_isk, available_from, photos_json)
  ON scraper.listings_canonical TO anon, authenticated;
-- operational/provenance columns intentionally NOT granted:
--   source_listing_id, secondary_source_ids, geog, canonical_version, last_promoted_at,
--   surviving_parse_id, surviving_source_priority, fastnum_resolution_* (spec §2.4-B)
-- service_role retains full access (bypasses RLS) for the sync hop.

-- ── public views (spec §2.4-A; security_invoker — cannot widen anon's column grants) ──
CREATE VIEW scraper.v_residential_sale_listings WITH (security_invoker = true) AS
SELECT lc.canonical_id, lc.source, lc.url,
       lc.first_seen_at, lc.last_seen_at, lc.withdrawn_at, lc.is_active,
       lc.price_amount, lc.price_currency, lc.listing_title, lc.lysing,
       lc.category, lc.tenure, lc.sub_type, lc.tegund_raw,
       lc.fastnum, lc.lat, lc.lng, lc.area_sqm, lc.rooms, lc.bedrooms, lc.bathrooms,
       lc.addr_text, lc.addr_municipality, lc.addr_postcode, lc.photos_json,
       p.byggar, p.einflm, p.matsvaedi_nafn
FROM scraper.listings_canonical lc
LEFT JOIN public.v_properties p USING (fastnum)   -- v_properties (security_invoker) respects Group B abstraction
WHERE lc.category = 'residential' AND lc.tenure = 'sale';

CREATE VIEW scraper.v_residential_rent_listings WITH (security_invoker = true) AS
SELECT lc.canonical_id, lc.source, lc.url,
       lc.first_seen_at, lc.last_seen_at, lc.withdrawn_at, lc.is_active,
       lc.price_amount, lc.price_currency, lc.listing_title, lc.lysing,
       lc.category, lc.tenure, lc.sub_type, lc.tegund_raw, lc.lease_term_class,
       lc.fastnum, lc.lat, lc.lng, lc.area_sqm, lc.rooms, lc.bedrooms, lc.bathrooms,
       lc.addr_text, lc.addr_municipality, lc.addr_postcode, lc.photos_json,
       lc.deposit_isk, lc.available_from,
       p.byggar, p.einflm, p.matsvaedi_nafn
FROM scraper.listings_canonical lc
LEFT JOIN public.v_properties p USING (fastnum)   -- v_properties (security_invoker) respects Group B abstraction
WHERE lc.category = 'residential' AND lc.tenure = 'rent';

CREATE VIEW scraper.v_commercial_listings WITH (security_invoker = true) AS
SELECT lc.canonical_id, lc.source, lc.url,
       lc.first_seen_at, lc.last_seen_at, lc.withdrawn_at, lc.is_active,
       lc.price_amount, lc.price_currency, lc.listing_title, lc.lysing,
       lc.category, lc.tenure, lc.sub_type, lc.tegund_raw, lc.lease_term_class,
       lc.fastnum, lc.lat, lc.lng, lc.area_sqm,
       lc.addr_text, lc.addr_municipality, lc.addr_postcode, lc.photos_json
FROM scraper.listings_canonical lc
WHERE lc.category = 'commercial';

CREATE VIEW scraper.v_plot_listings WITH (security_invoker = true) AS
SELECT lc.canonical_id, lc.source, lc.url,
       lc.first_seen_at, lc.last_seen_at, lc.withdrawn_at, lc.is_active,
       lc.price_amount, lc.price_currency, lc.listing_title, lc.lysing,
       lc.category, lc.tenure, lc.sub_type, lc.tegund_raw,
       lc.fastnum, lc.lat, lc.lng, lc.area_sqm,
       lc.addr_text, lc.addr_municipality, lc.addr_postcode, lc.photos_json
FROM scraper.listings_canonical lc
WHERE lc.category = 'plot';

CREATE VIEW scraper.v_listings_combined WITH (security_invoker = true) AS
SELECT lc.canonical_id, lc.source, lc.url,
       lc.first_seen_at, lc.last_seen_at, lc.withdrawn_at, lc.is_active,
       lc.price_amount, lc.price_currency, lc.listing_title,
       lc.category, lc.tenure, lc.sub_type, lc.tegund_raw, lc.lease_term_class,
       lc.fastnum, lc.lat, lc.lng, lc.area_sqm, lc.rooms, lc.bedrooms, lc.bathrooms,
       lc.addr_text, lc.addr_municipality, lc.addr_postcode,
       lc.deposit_isk, lc.available_from, lc.photos_json
FROM scraper.listings_canonical lc;

GRANT SELECT ON scraper.v_residential_sale_listings,
                scraper.v_residential_rent_listings,
                scraper.v_commercial_listings,
                scraper.v_plot_listings,
                scraper.v_listings_combined
  TO anon, authenticated;

COMMIT;
