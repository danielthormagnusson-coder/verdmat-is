-- cc219 fasi 2 rollback — fellir v2-lag Verðvaktarinnar. v1 (v_verdvakt_breytingar/_afsala/_nefnarar) ósnert.
-- Bakfyllingartaflan er endurgeranleg úr raw_mbl.db (scripts/cc219_bakfylla_hra_athuganir.py).
BEGIN;
SET TRANSACTION READ WRITE;
DROP MATERIALIZED VIEW IF EXISTS semantic.v_verdvakt_nefnarar_v2;
DROP MATERIALIZED VIEW IF EXISTS semantic.v_verdvakt_breytingar_v2;
DROP TABLE IF EXISTS scraper.verdvakt_hra_athugun;
COMMENT ON MATERIALIZED VIEW semantic.v_verdvakt_breytingar IS NULL;
COMMENT ON MATERIALIZED VIEW semantic.v_verdvakt_nefnarar IS NULL;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260930200000';
COMMIT;
