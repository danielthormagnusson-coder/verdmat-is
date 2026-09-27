-- cc213 fasi 1 rollback — fellir allar sex töflur gagnalags fasteignasölu-röðunar.
-- Afritaðu vörumerkjakortið og salakortið fyrst ef handvirkar staðfestingar eiga að lifa:
--   \copy (select * from scraper.fasteignasala_vorumerki order by sala_id) to 'vorumerki_backup.csv' csv header
--   \copy (select * from semantic.sali_kort order by sali_id) to 'sali_kort_backup.csv' csv header
BEGIN;
SET TRANSACTION READ WRITE;
DROP TABLE IF EXISTS semantic.fasteignasala_manudur;
DROP TABLE IF EXISTS semantic.fasteignasala_nefnarar;
DROP TABLE IF EXISTS scraper.fasteignasala_eignun;
DROP TABLE IF EXISTS semantic.sali_samheiti;
DROP TABLE IF EXISTS semantic.sali_kort;
DROP TABLE IF EXISTS scraper.fasteignasala_vorumerki;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260927180000';
COMMIT;
