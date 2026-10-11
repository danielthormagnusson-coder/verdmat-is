-- cc231 rollback: fjarlægir scraper.listings.sidast_fundin_at.
-- Á UNDAN: setja lifecycle_sweep_mbl.py aftur á útgáfu fyrir cc231 (annars hrynur næsta sópun á
-- óþekktum dálki). rollback()-lagfæringin (ActiveSqlTransaction) má standa óháð þessu.
-- Gögn dálksins tapast; afrit fyrir DROP: D:\_audit\cc231_sopun\afrit_sidast_fundin_<ts>.csv (b2 --beita skrifar).
BEGIN;
SET TRANSACTION READ WRITE;

ALTER TABLE scraper.listings DROP COLUMN IF EXISTS sidast_fundin_at;

DELETE FROM supabase_migrations.schema_migrations WHERE version = '20261011210000';

COMMIT;
