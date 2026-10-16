-- cc251 ROLLBACK fyrir 20261016210000_cc251_manadarsala_yoy — taflan var ný (ekkert las hana fyrir cc251), svo
-- rollback = DROP. Skrifuð Á UNDAN migration-inni. Framendinn (MarkadurManadarsala) fellur þá í „ekki tiltækt".
BEGIN;
SET TRANSACTION READ WRITE;
SET LOCAL lock_timeout = '10s';
DROP TABLE IF EXISTS semantic.manadarsala_yoy;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20261016210000';
NOTIFY pgrst, 'reload schema';
COMMIT;
