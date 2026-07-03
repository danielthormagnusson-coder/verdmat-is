-- Rollback for Phase A migration 1: scraper.listing_lifecycle_events
-- Written at apply time (lifecycle-pipe Phase A mandate; scratchpad-rescued
-- out of ephemeral Temp into the repo). Commits with the migration mirror
-- on commit-go.
--
-- Reverses <version>_create_listing_lifecycle_events.
-- Fully reversible: table is an append-only event log, no FKs point INTO it,
-- so dropping it orphans nothing. Enum is dropped after the table that uses it.
--
-- Apply via Supabase MCP execute_sql, or psycopg2 on the 6543 pooler
-- (in which case SET TRANSACTION READ WRITE must be the FIRST statement).

BEGIN;
DROP TABLE IF EXISTS scraper.listing_lifecycle_events;
DROP TYPE  IF EXISTS scraper.lifecycle_event_enum;
COMMIT;
