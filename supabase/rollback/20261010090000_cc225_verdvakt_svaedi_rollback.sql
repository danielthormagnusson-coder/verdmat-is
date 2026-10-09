-- cc225 rollback — fellir svæðissíu Verðvaktarinnar (9-hólfa nefnara + póstnúmeratöflu). v1, v2 og
-- v_verdvakt_nefnarar_stadir_v2 ósnert. Framendinn les hvort tveggja: revert verdmat-ai (cc225) FYRST.
BEGIN;
SET TRANSACTION READ WRITE;
DROP MATERIALIZED VIEW IF EXISTS semantic.v_verdvakt_nefnarar_svaedi_v2;
DROP TABLE IF EXISTS semantic.verdvakt_hbs_postnr;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20261010090000';
COMMIT;
