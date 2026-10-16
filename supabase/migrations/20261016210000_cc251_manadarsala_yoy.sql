-- =====================================================================
-- cc251 f.2 — mánaðarsala á móti sama mánuði í fyrra (gagnalag fyrir /markadur „Umsvifin").
-- Skilgreining = cc249 m1 (D:\_audit\cc249_manadarsala\SKIL_CC249.md §2), ekki endurhönnuð:
--   samningur  = FAERSLUNUMER í kaupskrá HMS; íbúðasamningur = einhver lína TEGUND ∈ {Fjölbýli, Einbýli, Sérbýli}
--   nothæfur   = ONOTHAEFUR_SAMNINGUR 0 á ÖLLUM línum samnings
--   mánuður    = kaupsamningsdagur (UTGDAG), ekki þinglýsingardagur
--   velta      = KAUPVERD × 1000 kr, tekið EINU sinni per samning (heildartala endurtekin per línu)
--   hbs        = SVFN 0000/1000/1100/1300/1400/1604/1606 (sama mengi og cc237 HOFUDB)
--   fullnusta  = q11 (cc232/cc237): miðgildi yfir þroskaða mánuði T−15…T−4 af hlut samninga sem var þinglýstur
--                jafnlangt eftir mánaðarlok og data_through er nú eftir lok T; stada 'bradabirgda' ef < 0,97
--   *_sama_tof = mánuðurinn T−12 eins og hann stóð jafnlangt eftir SÍN mánaðarlok og nú er liðið frá lokum T
--   *_fyrra_nu = mánuðurinn T−12 eins og hann stendur núna
--   Δ (reiknað í framenda): endanlegt → n / n_fyrra_nu − 1; bradabirgda → n / n_fyrra_sama_tof − 1
-- Skrifari: scripts/cc251_manadarsala_yoy.py --skrifa (næturkeðja, á eftir delta). Eitt sett per regla_version;
-- skrifarinn eyðir og skrifar í sömu færslu.
-- Rollback (skrifuð á undan): supabase/rollback/20261016210000_cc251_manadarsala_yoy_rollback.sql
-- NEFNARASKYLDA ER DÁLKASKYLDA: engir sentinlar — NULL ef ómælt.
-- =====================================================================
BEGIN;
SET TRANSACTION READ WRITE;

CREATE TABLE semantic.manadarsala_yoy (
  regla_version         text          NOT NULL,
  svaedi                text          NOT NULL,
  manudur               date          NOT NULL,     -- 1. dagur kaupsamningsmánaðar
  n                     integer       NOT NULL,
  velta                 bigint        NOT NULL,     -- kr
  n_fyrra_nu            integer,                    -- T−12 eins og hann stendur núna
  velta_fyrra_nu        bigint,
  n_fyrra_sama_tof      integer,                    -- T−12 þinglýst jafnlangt eftir sín mánaðarlok
  velta_fyrra_sama_tof  bigint,
  fullnusta             numeric(5,4),               -- q11-miðgildi; NULL ef ómælt
  fullnusta_min         numeric(5,4),
  fullnusta_max         numeric(5,4),
  stada                 text,                       -- NULL iff fullnusta NULL
  reiknad               timestamptz   NOT NULL,
  data_through          date          NOT NULL,     -- síðasti þinglýsingardagur í kaupskrá keyrslunnar
  PRIMARY KEY (regla_version, svaedi, manudur),
  CONSTRAINT manadarsala_yoy_chk CHECK (
        svaedi IN ('land', 'hbs')
    AND date_trunc('month', manudur)::date = manudur
    AND n >= 0 AND velta >= 0
    AND (n_fyrra_nu IS NULL) = (velta_fyrra_nu IS NULL)
    AND (n_fyrra_sama_tof IS NULL) = (velta_fyrra_sama_tof IS NULL)
    AND (n_fyrra_sama_tof IS NULL OR n_fyrra_nu IS NULL OR n_fyrra_sama_tof <= n_fyrra_nu)
    AND (fullnusta IS NULL OR (fullnusta BETWEEN 0 AND 1 AND fullnusta_min <= fullnusta AND fullnusta <= fullnusta_max))
    AND (fullnusta IS NULL) = (stada IS NULL)
    AND (stada IS NULL OR stada = CASE WHEN fullnusta < 0.97 THEN 'bradabirgda' ELSE 'endanlegt' END)
    AND manudur < date_trunc('month', data_through)::date)
);
COMMENT ON TABLE semantic.manadarsala_yoy IS
  'cc251: nothæfir íbúðakaupsamningar (FAERSLUNUMER) og velta per kaupsamningsmánuð (UTGDAG), landið og HBS, með sama '
  'mánuði í fyrra (nú og á sömu töf). Skilgreining cc249 m1. stada bradabirgda = q11-fullnusta < 97 %.';

ALTER TABLE semantic.manadarsala_yoy ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE semantic.manadarsala_yoy FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE semantic.manadarsala_yoy TO anon, authenticated;
CREATE POLICY manadarsala_yoy_les ON semantic.manadarsala_yoy FOR SELECT TO anon, authenticated USING (true);

NOTIFY pgrst, 'reload schema';
COMMIT;
