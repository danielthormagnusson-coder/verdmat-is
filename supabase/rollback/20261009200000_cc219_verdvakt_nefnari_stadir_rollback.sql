-- cc219 fasi 3 rollback — fellir nefnara per stað. v1 og v2 Verðvaktarinnar ósnert.
-- Framendinn les MV-ið: revert verdmat-ai (fasi 3) FYRST, annars fellur gagnalag /verdvaktin á stöðumerki.
BEGIN;
SET TRANSACTION READ WRITE;
DROP MATERIALIZED VIEW IF EXISTS semantic.v_verdvakt_nefnarar_stadir_v2;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20261009200000';
COMMIT;
