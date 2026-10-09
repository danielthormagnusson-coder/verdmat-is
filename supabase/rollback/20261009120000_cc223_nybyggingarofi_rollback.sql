-- Rollback cc223 nýbyggingarofi. Framendinn verður fyrst að lesa FS_REGLA = 'cc213-v2' (eldri röð).
BEGIN;
SET TRANSACTION READ WRITE;
DELETE FROM semantic.fasteignasala_nefnarar WHERE regla_version = 'cc223-v1';   -- cascade: manudur + nyb_stadir
DELETE FROM scraper.fasteignasala_eignun WHERE regla_version = 'cc223-v1';
DROP POLICY fasteignasala_manudur_les ON semantic.fasteignasala_manudur;
CREATE POLICY fasteignasala_manudur_les ON semantic.fasteignasala_manudur FOR SELECT TO anon, authenticated
  USING (adili_tegund = 'stofa'
         OR EXISTS (SELECT 1 FROM semantic.fasteignasala_nefnarar n
                     WHERE n.timabil_fra = fasteignasala_manudur.timabil_fra AND n.timabil_til = fasteignasala_manudur.timabil_til
                       AND n.gluggi = fasteignasala_manudur.gluggi AND n.regla_version = fasteignasala_manudur.regla_version
                       AND n.stada_sali IN ('bradabirgda','endanlegt')));
DROP TABLE semantic.fasteignasala_nyb_stadir;
ALTER TABLE semantic.fasteignasala_manudur DROP CONSTRAINT fasteignasala_manudur_pkey;
ALTER TABLE semantic.fasteignasala_manudur ADD PRIMARY KEY
  (timabil_fra, timabil_til, gluggi, regla_version, adili_tegund, maelikvardi, med_nybyggingum, adili_lykill);
ALTER TABLE semantic.fasteignasala_manudur DROP CONSTRAINT manudur_nybyggingar_chk;
ALTER TABLE semantic.fasteignasala_manudur DROP COLUMN nybyggingar;
COMMIT;
