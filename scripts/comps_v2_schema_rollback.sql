-- comps_v2_schema_rollback.sql
-- Rollback fyrir COMP-FLIP skref 1 (migration create_comps_v2_tables).
-- Skrifad FYRIR apply (WORKING_PROTOCOL / Phase-D mynstur).
-- Fellir adeins NYJU tofurnar fjorar; live public.comps_index er OSNERT af bade
-- migration og rollbacki. Policies, indexar og FK falla med toflunum.
-- Keyrsla: psql/pooler med SET TRANSACTION READ WRITE, eda MCP execute_sql.

BEGIN;
SET TRANSACTION READ WRITE;

DROP TABLE IF EXISTS public.comps_index_v2;
DROP TABLE IF EXISTS public.valuation_tiers;
DROP TABLE IF EXISTS public.comps_drift_diagnostics;
DROP TABLE IF EXISTS public.comps_t5_basis;

DELETE FROM supabase_migrations.schema_migrations
 WHERE name = 'create_comps_v2_tables';

COMMIT;
