-- =====================================================================
-- cc223 — Nýbyggingarofi þrístaða (Allt / Án nýbygginga / Aðeins nýbyggingar) í fasteignasölu-röðuninni
-- Skrifað af scripts/cc213_fasteignasala_manudur.py (regla_version cc223-v1; cc213-v2 skrifuð samhliða
-- þar til framendinn flippar FS_REGLA).
-- Rollback: supabase/rollback/20261009120000_cc223_nybyggingarofi_rollback.sql
-- Skil: D:\_audit\cc223_nybyggingarofi\SKIL_CC223.md
--
-- 1. semantic.fasteignasala_manudur.nybyggingar ∈ {med, an, adeins} — sjálfstæð röðunarlína per stað
--    (ekki afleidd í framenda). Eldri raðir fá med/an úr med_nybyggingum. PK ber nú nybyggingar
--    (med og adeins bera bæði med_nybyggingum = true).
-- 2. semantic.fasteignasala_nyb_stadir — nefnarar + stöðumerki PER STAÐ: „aðeins nýbyggingar" ber eigið
--    eignunar- og sala-gólf (júlí 2026: 96/138 = 69,6 % eignað < 70 % → ohaeft).
-- 3. RLS manudur: raðir með stað-röð gáttaðar á stöðu staðarins (stofa: ≠ ohaeft; sali: bradabirgda/endanlegt);
--    raðir án stað-raðar (cc213-v1/v2) halda óbreyttri reglu.
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;

-- 1. röðunarlína per stað
ALTER TABLE semantic.fasteignasala_manudur ADD COLUMN nybyggingar text;
UPDATE semantic.fasteignasala_manudur SET nybyggingar = CASE WHEN med_nybyggingum THEN 'med' ELSE 'an' END;
ALTER TABLE semantic.fasteignasala_manudur ALTER COLUMN nybyggingar SET NOT NULL;
ALTER TABLE semantic.fasteignasala_manudur ADD CONSTRAINT manudur_nybyggingar_chk CHECK (
      nybyggingar IN ('med','an','adeins')
  AND (nybyggingar = 'an') = (NOT med_nybyggingum)
  AND (nybyggingar <> 'adeins' OR nyb_fjoldi = fjoldi));
ALTER TABLE semantic.fasteignasala_manudur DROP CONSTRAINT fasteignasala_manudur_pkey;
ALTER TABLE semantic.fasteignasala_manudur ADD PRIMARY KEY
  (timabil_fra, timabil_til, gluggi, regla_version, adili_tegund, maelikvardi, nybyggingar, adili_lykill);
COMMENT ON COLUMN semantic.fasteignasala_manudur.nybyggingar IS
  'cc223: med = allar sölur; an = nýbyggingar út; adeins = aðeins nýbyggingar (regla 5: FULLBUID=0 ∨ BYGGAR ≥ ár(UTGDAG)−2).';

-- 2. nefnarar + stöðumerki per stað
CREATE TABLE semantic.fasteignasala_nyb_stadir (
  timabil_fra         date        NOT NULL,
  timabil_til         date        NOT NULL,
  gluggi              text        NOT NULL,
  regla_version       text        NOT NULL,
  nybyggingar         text        NOT NULL CHECK (nybyggingar IN ('med','an','adeins')),
  n_samningar         integer     NOT NULL,          -- M staðarins
  velta_samninga      bigint      NOT NULL,
  n_eignadar_stofu    integer     NOT NULL,
  velta_eignud_stofu  bigint      NOT NULL,
  n_med_sala          integer     NOT NULL,
  n_salar_sameiginl   integer     NOT NULL,
  eignun_laegst_man   numeric(5,4),                  -- lægsta mánaðarhlutfall eignunar í tímabilinu (gólfið les það)
  stada_stofa         text        NOT NULL CHECK (stada_stofa IN ('ohaeft','bradabirgda','endanlegt')),
  stada_sali          text        NOT NULL CHECK (stada_sali IN ('ohaeft','undir_golfi','bradabirgda','endanlegt')),
  fyrirvari_sali      text        NOT NULL,
  reiknad             timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (timabil_fra, timabil_til, gluggi, regla_version, nybyggingar),
  CONSTRAINT nyb_stadir_teljarar_chk CHECK (
        n_samningar >= 0 AND n_eignadar_stofu BETWEEN 0 AND n_samningar
    AND n_med_sala BETWEEN 0 AND n_eignadar_stofu
    AND n_salar_sameiginl BETWEEN 0 AND n_med_sala
    AND velta_eignud_stofu BETWEEN 0 AND velta_samninga),
  CONSTRAINT nyb_stadir_nefnarar_fk FOREIGN KEY (timabil_fra, timabil_til, gluggi, regla_version)
        REFERENCES semantic.fasteignasala_nefnarar (timabil_fra, timabil_til, gluggi, regla_version) ON DELETE CASCADE
);
COMMENT ON TABLE semantic.fasteignasala_nyb_stadir IS
  'cc223: nefnarar og stöðumerki per nýbyggingarstað (med/an/adeins). med = nefnarar-röðin. Allt = Án + Aðeins (fjöldi og velta).';

ALTER TABLE semantic.fasteignasala_nyb_stadir ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE semantic.fasteignasala_nyb_stadir FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE semantic.fasteignasala_nyb_stadir TO anon, authenticated;
CREATE POLICY fasteignasala_nyb_stadir_les ON semantic.fasteignasala_nyb_stadir FOR SELECT TO anon, authenticated USING (true);

-- 3. RLS manudur: stað-gátt þar sem stað-röð er til, annars óbreytt cc213-regla
DROP POLICY fasteignasala_manudur_les ON semantic.fasteignasala_manudur;
CREATE POLICY fasteignasala_manudur_les ON semantic.fasteignasala_manudur FOR SELECT TO anon, authenticated
  USING (
    CASE
      WHEN EXISTS (SELECT 1 FROM semantic.fasteignasala_nyb_stadir s
                    WHERE s.timabil_fra = fasteignasala_manudur.timabil_fra AND s.timabil_til = fasteignasala_manudur.timabil_til
                      AND s.gluggi = fasteignasala_manudur.gluggi AND s.regla_version = fasteignasala_manudur.regla_version
                      AND s.nybyggingar = fasteignasala_manudur.nybyggingar)
      THEN EXISTS (SELECT 1 FROM semantic.fasteignasala_nyb_stadir s
                    WHERE s.timabil_fra = fasteignasala_manudur.timabil_fra AND s.timabil_til = fasteignasala_manudur.timabil_til
                      AND s.gluggi = fasteignasala_manudur.gluggi AND s.regla_version = fasteignasala_manudur.regla_version
                      AND s.nybyggingar = fasteignasala_manudur.nybyggingar
                      AND CASE WHEN fasteignasala_manudur.adili_tegund = 'stofa' THEN s.stada_stofa <> 'ohaeft'
                               ELSE s.stada_sali IN ('bradabirgda','endanlegt') END)
      ELSE (adili_tegund = 'stofa'
            OR EXISTS (SELECT 1 FROM semantic.fasteignasala_nefnarar n
                        WHERE n.timabil_fra = fasteignasala_manudur.timabil_fra AND n.timabil_til = fasteignasala_manudur.timabil_til
                          AND n.gluggi = fasteignasala_manudur.gluggi AND n.regla_version = fasteignasala_manudur.regla_version
                          AND n.stada_sali IN ('bradabirgda','endanlegt')))
    END);

COMMIT;
