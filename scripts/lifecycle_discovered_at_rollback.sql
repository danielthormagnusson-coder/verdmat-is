-- Rollback for Phase A migration 2: scraper.listings.discovered_at
-- Written BEFORE apply (lifecycle-pipe Phase A mandate).
-- Reverses <version>_add_discovered_at_to_listings.
-- Additive column, no data derived from it elsewhere; dropping it is lossless
-- beyond the discovery stamps themselves.
--
-- Apply via Supabase MCP execute_sql, or psycopg2 on the 6543 pooler
-- (in which case SET TRANSACTION READ WRITE must be the FIRST statement).

BEGIN;
ALTER TABLE scraper.listings DROP COLUMN IF EXISTS discovered_at;
COMMIT;
