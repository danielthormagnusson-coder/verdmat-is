-- cc213b rollback — fellir staðfestingardálka semantic.sali_kort (handvirk útilokun glatast: virkt stendur).
BEGIN;
SET TRANSACTION READ WRITE;
ALTER TABLE semantic.sali_kort DROP COLUMN IF EXISTS athugasemd, DROP COLUMN IF EXISTS stadfest_dags, DROP COLUMN IF EXISTS stadfest_af;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260929100000';
COMMIT;
