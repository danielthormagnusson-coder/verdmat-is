-- =====================================================================
-- cc243 f.1 — söluhraði per nýbyggingarverkefni (gagnalag). EKKI BEITT — bíður GO Danna.
-- Skrifað af scripts/cc224_nybygging_verkefni.py + scripts/nyb_soluhradi.py (grein cc243).
-- Rollback (skrifuð á undan): supabase/rollback/20261015090000_cc243_soluhradi_rollback.sql
-- Skil: D:\_audit\cc243_soluhradi\SKIL_CC243.md. Skilgreiningar = cc237 §1 (D:\_audit\cc237_soluhradi\SKIL_CC237.md).
--
-- Útgáfa: dálkarnir fyllast í cc224-v8 (hrein viðbót; enginn núverandi dálkur breytist — sannað í dry-run, 324/324,
-- 8.428/8.428 eins). Eldri útgáfur (v2–v7) fá NULL; CHECK-skilyrðin leyfa það (hradi_stada IS NULL = ekki reiknað).
--
--   lykill        = kaupsamningsdagur (UTGDAG) útgöngusamningsins, ekki þinglýsingardagur (sala_dags)
--   nothaefar     = fyrsta útganga, ONOTHAEFUR 0 (stada seld); heildarkaup = cc228 D2′ + magnsala (teljari b, cc237)
--   oseldar_upphafi = óseldar einingar í boði 1. dag mánaðar (R1: HMS-nálgun ∧ fyrsta auglýsing ∧ fyrsti samningur)
--   óskipt fastnr. utan; verkefni sem er eingöngu óskipt fær ENGAR mánaðarraðir og hradi_stada 'omaelanlegt' (aldrei 0)
--   fullnusta     = q11 (lægri af nothæfum/ónothæfum), bradabirgda = fullnusta < 0,90
--   hradi_90d_*   = sölur á mánuði (sölur í glugga / 3) í 90 d glugga sem endar á síðasta þroskaða degi
--   man_i_uppselt = hradi_oseldar / hradi_90d_nothaefar; aðeins 'maelt', ≥ 5 nothæfar í glugga, ≥ 5 óseldar, ekkert óskipt
--   heildarkaup_* = D2′ eingöngu (= n_heildarkaup); pakki = FAERSLUNUMER; dagsetningar = UTGDAG
--
-- NEFNARASKYLDA ER DÁLKASKYLDA: engir sentinlar — NULL + staða.
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan (WP h)

-- ---------------------------------------------------------------------
-- 1. Dálkar á verkefni
-- ---------------------------------------------------------------------
ALTER TABLE semantic.nybygging_verkefni
  ADD COLUMN IF NOT EXISTS hradi_90d_nothaefar        numeric(7,2),
  ADD COLUMN IF NOT EXISTS hradi_90d_heildarkaup      numeric(7,2),
  ADD COLUMN IF NOT EXISTS hradi_90d_samtals          numeric(7,2),
  ADD COLUMN IF NOT EXISTS hradi_glugga_fra           date,
  ADD COLUMN IF NOT EXISTS hradi_glugga_til           date,          -- síðasti þroskaði dagur (fullnusta ≥ 90 %)
  ADD COLUMN IF NOT EXISTS hradi_oseldar              integer,       -- óseldar skiptar einingar við gluggalok
  ADD COLUMN IF NOT EXISTS man_i_uppselt              numeric(6,1),
  ADD COLUMN IF NOT EXISTS hradi_stada                text,
  ADD COLUMN IF NOT EXISTS heildarkaup_fyrst          date,
  ADD COLUMN IF NOT EXISTS heildarkaup_sidast         date,
  ADD COLUMN IF NOT EXISTS heildarkaup_staersti_pakki integer,       -- íbúðir verkefnisins í stærsta FAERSLUNUMER
  ADD COLUMN IF NOT EXISTS heildarkaup_n_pakkar       integer;

ALTER TABLE semantic.nybygging_verkefni ADD CONSTRAINT nybygging_verkefni_hradi_chk CHECK (
  (hradi_stada IS NULL
     AND hradi_glugga_fra IS NULL AND hradi_glugga_til IS NULL AND hradi_90d_nothaefar IS NULL
     AND hradi_90d_heildarkaup IS NULL AND hradi_90d_samtals IS NULL AND hradi_oseldar IS NULL AND man_i_uppselt IS NULL)
  OR (hradi_stada IN ('maelt', 'faar_solur', 'omaelanlegt', 'uppselt')
     AND hradi_glugga_til IS NOT NULL AND hradi_glugga_fra = hradi_glugga_til - 89
     AND (hradi_stada = 'omaelanlegt') = (hradi_90d_samtals IS NULL)
     AND (hradi_90d_samtals IS NULL) = (hradi_90d_nothaefar IS NULL)
     AND (hradi_90d_samtals IS NULL) = (hradi_90d_heildarkaup IS NULL)
     AND (hradi_90d_samtals IS NULL) = (hradi_oseldar IS NULL)
     AND (hradi_90d_samtals IS NULL OR (hradi_90d_nothaefar >= 0 AND hradi_90d_heildarkaup >= 0
          AND hradi_90d_samtals >= greatest(hradi_90d_nothaefar, hradi_90d_heildarkaup) AND hradi_oseldar >= 0))
     AND (hradi_stada <> 'uppselt' OR hradi_oseldar = 0)
     AND (man_i_uppselt IS NULL OR (hradi_stada = 'maelt' AND hradi_oseldar >= 5 AND hradi_90d_nothaefar > 0
          AND man_i_uppselt > 0))
     AND (heildarkaup_fyrst IS NOT NULL) = (n_heildarkaup > 0)));

ALTER TABLE semantic.nybygging_verkefni ADD CONSTRAINT nybygging_verkefni_heildarkaup_merki_chk CHECK (
      (heildarkaup_fyrst IS NULL) = (heildarkaup_sidast IS NULL)
  AND (heildarkaup_fyrst IS NULL) = (heildarkaup_staersti_pakki IS NULL)
  AND (heildarkaup_fyrst IS NULL) = (heildarkaup_n_pakkar IS NULL)
  AND (heildarkaup_fyrst IS NULL OR (heildarkaup_fyrst <= heildarkaup_sidast
       AND heildarkaup_staersti_pakki BETWEEN 1 AND n_heildarkaup AND heildarkaup_n_pakkar BETWEEN 1 AND n_heildarkaup)));

-- ---------------------------------------------------------------------
-- 2. Mánaðarsölur per verkefni (eitt sett per keyrslu = útgáfa; smiðurinn eyðir og skrifar í sömu færslu)
-- ---------------------------------------------------------------------
CREATE TABLE semantic.nybygging_solur_manadar (
  utgafa                 text         NOT NULL,
  verkefni_id            text         NOT NULL,
  manudur                date         NOT NULL,     -- 1. dagur kaupsamningsmánaðar
  nothaefar              integer      NOT NULL,
  heildarkaup            integer      NOT NULL,
  uppsafnad_nothaefar    integer      NOT NULL,
  uppsafnad_heildarkaup  integer      NOT NULL,
  oseldar_upphafi        integer      NOT NULL,     -- nefnari: óseldar í boði 1. dag mánaðar (R1, skiptar einingar)
  fullnusta              numeric(5,4) NOT NULL,     -- q11, lægri af nothæfum/ónothæfum
  bradabirgda            boolean      NOT NULL,
  PRIMARY KEY (utgafa, verkefni_id, manudur),
  CONSTRAINT nybygging_solur_manadar_verkefni_fk FOREIGN KEY (utgafa, verkefni_id)
        REFERENCES semantic.nybygging_verkefni (utgafa, verkefni_id) ON DELETE CASCADE,
  CONSTRAINT nybygging_solur_manadar_chk CHECK (
        date_trunc('month', manudur)::date = manudur
    AND nothaefar >= 0 AND heildarkaup >= 0
    AND uppsafnad_nothaefar >= nothaefar AND uppsafnad_heildarkaup >= heildarkaup
    AND oseldar_upphafi >= 0
    AND fullnusta BETWEEN 0 AND 1 AND bradabirgda = (fullnusta < 0.90))
);
COMMENT ON TABLE semantic.nybygging_solur_manadar IS
  'cc243: sölur per verkefni og kaupsamningsmánuð (UTGDAG). nothaefar / heildarkaup (D2′+magnsala) aðskilið; '
  'óskipt fastnr. utan (verkefni eingöngu óskipt = engar raðir, hradi_stada omaelanlegt). bradabirgda = fullnusta q11 < 90 %.';

-- ---------------------------------------------------------------------
-- 3. Heimildir: default-deny, svo opnað nákvæmlega (sama og nybygging_einingar)
-- ---------------------------------------------------------------------
ALTER TABLE semantic.nybygging_solur_manadar ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE semantic.nybygging_solur_manadar FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE semantic.nybygging_solur_manadar TO anon, authenticated;
CREATE POLICY nybygging_solur_manadar_les ON semantic.nybygging_solur_manadar FOR SELECT TO anon, authenticated USING (true);

NOTIFY pgrst, 'reload schema';
COMMIT;
