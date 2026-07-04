-- comps_v2_load_rollback.sql
-- Rollback fyrir COMP-FLIP skref 3 (loader). Skrifad FYRIR framkvaemd.
-- Tvo adskilin tilvik - keyrid ADEINS thann hluta sem a vid:
--
-- A) STAGING-rollback (eftir phase staging/copy, adur en flip-txn keyrir):
--    fellir stagingu; loka-toflurnar fjorar eru enn tomar og migration stendur.
BEGIN;
SET TRANSACTION READ WRITE;
DROP TABLE IF EXISTS public.comps_index_v2_staging;
DROP TABLE IF EXISTS public.valuation_tiers_staging;
DROP TABLE IF EXISTS public.comps_drift_diagnostics_staging;
DROP TABLE IF EXISTS public.comps_t5_basis_staging;
COMMIT;

-- B) FLIP-rollback (eftir committada flip-txn):
--    taemir loka-toflurnar fjorar (aftur i skref-1 stodu) + fjarlaegir
--    pipeline_runs faersluna. Live comps_index OSNERT af bade.
-- BEGIN;
-- SET TRANSACTION READ WRITE;
-- TRUNCATE public.comps_index_v2, public.valuation_tiers,
--          public.comps_drift_diagnostics, public.comps_t5_basis;
-- DELETE FROM public.pipeline_runs WHERE run_type = 'comps_v2_flip_load';
-- COMMIT;
