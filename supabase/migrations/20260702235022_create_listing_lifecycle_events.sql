-- Phase A · lifecycle pipe · migration 1 (additive, reversible).
-- Append-only event log for mbl (and later multi-source) listing lifecycle.
-- Internal table: RLS on, no policy, table grants revoked from anon/authenticated;
-- service_role (the sweep script) bypasses RLS. Not exposed via PostgREST (scraper schema).
--
-- Rollback: app/scripts/lifecycle_events_rollback.sql

CREATE TYPE scraper.lifecycle_event_enum AS ENUM (
  'discovered',
  'price_changed',
  'confirmed_absent_1',
  'withdrawn_confirmed',
  'sale_matched'
);

CREATE TABLE scraper.listing_lifecycle_events (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source            text        NOT NULL,
  source_listing_id text        NOT NULL,
  fastnum           bigint,
  event_type        scraper.lifecycle_event_enum NOT NULL,
  event_at          timestamptz NOT NULL,
  evidence          jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_lle_source_listing_event_at
  ON scraper.listing_lifecycle_events (source, source_listing_id, event_at);

CREATE INDEX idx_lle_event_type_event_at
  ON scraper.listing_lifecycle_events (event_type, event_at);

ALTER TABLE scraper.listing_lifecycle_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON scraper.listing_lifecycle_events FROM anon, authenticated;
