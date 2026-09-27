-- cc210 C1 rollback — fellir scraper.thekjuprof (mælitafla; engin önnur tafla vísar í hana).
-- Afritaðu raðirnar fyrst ef mælisagan á að lifa:
--   \copy (select * from scraper.thekjuprof order by id) to 'thekjuprof_backup.csv' csv header
BEGIN;
SET TRANSACTION READ WRITE;
DROP TABLE IF EXISTS scraper.thekjuprof;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260927085656';
COMMIT;
