-- Rollback cc224: fellir fjórar töflur /nybyggingar (gögn endurreiknanleg með scripts/cc224_nybygging_verkefni.py,
-- NEMA semantic.nybygging_slodir — taka afrit af henni fyrst ef hún er ekki tóm).
BEGIN;
SET TRANSACTION READ WRITE;
DROP TABLE semantic.nybygging_einingar;
DROP TABLE semantic.nybygging_verkefni;
DROP TABLE semantic.nybygging_slodir;
DROP TABLE semantic.nybygging_keyrslur;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20261009230000';
COMMIT;
