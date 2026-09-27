-- =====================================================================
-- cc213 fasi 1 — Fasteignasölu-röðun: gagnalag
-- Skrifað af scripts/cc213_fasteignasala_manudur.py (mánaðarleg keyrsla, 16. hvers mánaðar).
-- Rollback: supabase/rollback/20260927180000_cc213_fasteignasala_manudur_rollback.sql
-- Forskrift: D:\_audit\cc212_fasteignasalar\SKIL_CC212.md §5 + cc212b §5 + ákvarðanir Danna 27.09.
--
-- Fimm töflur:
--   scraper.fasteignasala_vorumerki   sala_id (mbl) -> stofulykill + birtingarheiti. Viðhaldin handvirkt. LÆST.
--   semantic.sali_kort                sali_id <- (stofulykill, grunnnafn); útgáfa. LÆST (ber netföng).
--   semantic.sali_samheiti            beygingar/brot/netföng -> sali_id. LÆST.
--   scraper.fasteignasala_eignun      ein röð per samningur × regla_version (endurskoðunarslóð). LÆST.
--   semantic.fasteignasala_nefnarar   nefnarar + stöðumerki per tímabil. anon/authenticated SELECT.
--   semantic.fasteignasala_manudur    röðunin (Top N). anon/authenticated SELECT m/ RLS:
--                                     sala-raðir sjást aðeins þegar sali-gólfið stenst.
--
-- NEFNARASKYLDA ER DÁLKASKYLDA (sbr. cc210): hver teljari NOT NULL + CHECK teljari <= nefnari.
-- Regla 3 (hver tala rekjanleg): hver röð ber regla_version, data_through, kaupskra_sott, listings_snapshot.
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan

-- ---------------------------------------------------------------------
-- 1. Vörumerkjakort (sala_id er EKKI stofulykill: Miklaborg 617+844; lagaheiti ≠ vörumerki)
-- ---------------------------------------------------------------------
CREATE TABLE scraper.fasteignasala_vorumerki (
  sala_id         integer     PRIMARY KEY,           -- mbl agency.sala_id = scraper.listings.agency_source_id
  lykill          text        NOT NULL,              -- stöðugur stofulykill (lágstafir, a-z0-9_)
  birtingarheiti  text        NOT NULL,
  mbl_heiti       text,                              -- heitið eins og mbl sýndi það við skráningu
  stadfest_af     text,                              -- NULL = sjálfvirk frumfylling, óstaðfest
  stadfest_dags   date,
  athugasemd      text,
  stofnad         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vorumerki_lykill_chk CHECK (lykill ~ '^[a-z0-9_]+$'),
  CONSTRAINT vorumerki_heiti_chk  CHECK (length(birtingarheiti) > 0)
);
CREATE INDEX fasteignasala_vorumerki_lykill_idx ON scraper.fasteignasala_vorumerki (lykill);
COMMENT ON TABLE scraper.fasteignasala_vorumerki IS
  'cc213: mbl sala_id -> stofulykill/birtingarheiti. Viðhaldin tafla (ákvörðun Danna 27.09). stadfest_af NULL = óstaðfest frumfylling.';

-- ---------------------------------------------------------------------
-- 2. Salakort (nafn + stofa -> sali_id)
-- ---------------------------------------------------------------------
CREATE TABLE semantic.sali_kort (
  sali_id       bigserial   PRIMARY KEY,
  stofa_lykill  text        NOT NULL,
  nafn          text        NOT NULL,          -- grunnmynd (nefnifall, lengsta staðfesta mynd)
  netfang       text,                          -- persónulegt netfang ef staðfest
  uppruni       text        NOT NULL,          -- 'nafnaskra' | 'p1_titill' | 'netfang_stadfest' | 'handvirkt'
  utgafa        text        NOT NULL,          -- útdráttarútgáfa sem stofnaði röðina, t.d. 'sali_v3'
  virkt         boolean     NOT NULL DEFAULT true,
  stofnad       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT sali_kort_uk UNIQUE (stofa_lykill, nafn),
  CONSTRAINT sali_kort_nafn_chk CHECK (length(nafn) >= 3)
);
CREATE TABLE semantic.sali_samheiti (
  samheiti      text        NOT NULL,          -- beygingarmynd / brot / netfang (lágstafir fyrir netföng)
  stofa_lykill  text        NOT NULL,
  tegund        text        NOT NULL CHECK (tegund IN ('nafn','netfang')),
  sali_id       bigint      NOT NULL REFERENCES semantic.sali_kort (sali_id) ON DELETE CASCADE,
  utgafa        text        NOT NULL,
  stofnad       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (stofa_lykill, tegund, samheiti)
);
COMMENT ON TABLE semantic.sali_kort IS
  'cc213: sali_id per (stofa_lykill, grunnnafn). Lykill = nafn + stofa (samnefni milli stofa = ólíkir salar). LÆST: ber netföng.';

-- ---------------------------------------------------------------------
-- 3. Eignun per samningur (endurskoðunarslóð)
-- ---------------------------------------------------------------------
CREATE TABLE scraper.fasteignasala_eignun (
  faerslunumer        bigint      NOT NULL,
  regla_version       text        NOT NULL,
  utgdag              date        NOT NULL,          -- kaupsamningsdagur (UTGDAG)
  thinglyst           timestamptz NOT NULL,          -- max THINGLYSTDAGS samnings
  kaupverd            bigint      NOT NULL,          -- kr, samningur óskiptur
  n_fastnum           integer     NOT NULL,
  nybygging           boolean     NOT NULL,          -- regla 5: FULLBUID=0 ∨ BYGGAR ≥ ár(UTGDAG)−2
  regla               text        NOT NULL CHECK (regla IN ('virk_a_K','sidasta_fyrir_K','fyrsta_eftir_K','oparad')),
  listing_id          bigint,                        -- eignuð auglýsing (scraper.listings)
  sala_id             integer,
  stofa_lykill        text,
  n_stofur_i_glugga   integer     NOT NULL DEFAULT 0,
  salar               bigint[]    NOT NULL DEFAULT '{}',   -- sali_id í röð fyrstu komu
  sali_uppruni        text,                          -- 'texti' | 'dealer_email' | NULL
  reiknad             timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (faerslunumer, regla_version),
  CONSTRAINT eignun_oparad_chk CHECK ((regla = 'oparad') = (listing_id IS NULL))
);
CREATE INDEX fasteignasala_eignun_utg_idx ON scraper.fasteignasala_eignun (regla_version, utgdag);
COMMENT ON TABLE scraper.fasteignasala_eignun IS
  'cc213: ein röð per þinglýstur íbúðarsamningur (ONOTH=0) × regla_version. Endurskoðunarslóð röðunarinnar. LÆST.';

-- ---------------------------------------------------------------------
-- 4. Nefnarar + stöðumerki per tímabil
-- ---------------------------------------------------------------------
CREATE TABLE semantic.fasteignasala_nefnarar (
  timabil_fra         date        NOT NULL,
  timabil_til         date        NOT NULL,
  gluggi              text        NOT NULL CHECK (gluggi IN ('manudur','fra_juli_2026')),
  regla_version       text        NOT NULL,
  n_samningar         integer     NOT NULL,          -- M: allir þinglýstir íbúðarsamningar (ONOTH=0) m/ UTGDAG í tímabili
  velta_samninga      bigint      NOT NULL,
  n_nybygging         integer     NOT NULL,
  n_paradar           integer     NOT NULL,
  n_eignadar_stofu    integer     NOT NULL,
  velta_eignud_stofu  bigint      NOT NULL,
  n_med_sala          integer     NOT NULL,          -- N: eignaðar sölur með lesið nafn sala
  n_salar_sameiginl   integer     NOT NULL,          -- eignaðar sölur með 2+ skráða sala
  fullnusta_aaetlud   numeric(4,1) NOT NULL,         -- % þinglýst af áætluðum endanlegum fjölda
  stada_stofa         text        NOT NULL CHECK (stada_stofa IN ('ohaeft','bradabirgda','endanlegt')),
  stada_sali          text        NOT NULL CHECK (stada_sali IN ('ohaeft','undir_golfi','bradabirgda','endanlegt')),
  sali_golf           numeric(3,2) NOT NULL,         -- 0,80 (N / n_eignadar_stofu)
  eignun_golf         numeric(3,2) NOT NULL,         -- 0,70 (n_eignadar_stofu / n_samningar)
  fyrirvari_sali      text        NOT NULL,          -- orðrétt fyrirvaralína kassans
  data_through        date        NOT NULL,          -- max THINGLYSTDAGS í kaupskrá
  kaupskra_sott       timestamptz NOT NULL,
  listings_snapshot   timestamptz NOT NULL,
  reiknad             timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (timabil_fra, timabil_til, gluggi, regla_version),
  CONSTRAINT nefnarar_teljarar_chk CHECK (
        n_samningar >= 0 AND n_paradar BETWEEN 0 AND n_samningar
    AND n_eignadar_stofu BETWEEN 0 AND n_paradar
    AND n_med_sala BETWEEN 0 AND n_eignadar_stofu
    AND n_salar_sameiginl BETWEEN 0 AND n_med_sala
    AND n_nybygging BETWEEN 0 AND n_samningar
    AND velta_eignud_stofu BETWEEN 0 AND velta_samninga),
  CONSTRAINT nefnarar_timabil_chk CHECK (timabil_til >= timabil_fra)
);

-- ---------------------------------------------------------------------
-- 5. Röðunin
-- ---------------------------------------------------------------------
CREATE TABLE semantic.fasteignasala_manudur (
  timabil_fra       date        NOT NULL,
  timabil_til       date        NOT NULL,
  gluggi            text        NOT NULL CHECK (gluggi IN ('manudur','fra_juli_2026')),
  regla_version     text        NOT NULL,
  adili_tegund      text        NOT NULL CHECK (adili_tegund IN ('stofa','sali')),
  adili_lykill      text        NOT NULL,          -- stofa: vorumerki.lykill; sali: sali_id::text
  adili_nafn        text        NOT NULL,
  stofa_lykill      text        NOT NULL,          -- stofa sala (= adili_lykill fyrir stofu)
  stofa_nafn        text        NOT NULL,
  maelikvardi       text        NOT NULL CHECK (maelikvardi IN ('fjoldi','velta')),
  med_nybyggingum   boolean     NOT NULL,
  saeti             integer     NOT NULL,          -- deilt sæti: rank() (1,1,3)
  fjoldi            integer     NOT NULL,          -- sölur (óskipt: hver skráður sali fær söluna)
  fjoldi_sameiginl  integer     NOT NULL,          -- þar af sameiginlegar (2+ salar) — 0 fyrir stofu
  velta             bigint      NOT NULL,          -- stofa: óskipt; sali: skipt jafnt milli skráðra sala
  nyb_fjoldi        integer     NOT NULL,
  nyb_velta         bigint      NOT NULL,
  data_through      date        NOT NULL,
  reiknad           timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (timabil_fra, timabil_til, gluggi, regla_version, adili_tegund, maelikvardi, med_nybyggingum, adili_lykill),
  CONSTRAINT manudur_tolur_chk CHECK (saeti >= 1 AND fjoldi >= 1 AND fjoldi_sameiginl BETWEEN 0 AND fjoldi
        AND nyb_fjoldi BETWEEN 0 AND fjoldi AND velta >= 0 AND nyb_velta BETWEEN 0 AND velta
        AND (med_nybyggingum OR nyb_fjoldi = 0)),
  CONSTRAINT manudur_nefnarar_fk FOREIGN KEY (timabil_fra, timabil_til, gluggi, regla_version)
        REFERENCES semantic.fasteignasala_nefnarar (timabil_fra, timabil_til, gluggi, regla_version) ON DELETE CASCADE
);
COMMENT ON TABLE semantic.fasteignasala_manudur IS
  'cc213: Top-N fasteignasölur og salar per tímabil. Stofa: fjöldi og velta óskipt. Sali: fjöldi óskiptur, velta skipt jafnt milli skráðra sala. '
  'Sala-raðir sýnilegar anon aðeins þegar nefnarar.stada_sali ∈ (bradabirgda, endanlegt).';

-- ---------------------------------------------------------------------
-- Heimildir: default-deny, svo opnað nákvæmlega
-- ---------------------------------------------------------------------
ALTER TABLE scraper.fasteignasala_vorumerki  ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic.sali_kort               ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic.sali_samheiti           ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper.fasteignasala_eignun     ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic.fasteignasala_nefnarar  ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic.fasteignasala_manudur   ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE scraper.fasteignasala_vorumerki, semantic.sali_kort, semantic.sali_samheiti,
                   scraper.fasteignasala_eignun, semantic.fasteignasala_nefnarar, semantic.fasteignasala_manudur
       FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON SEQUENCE semantic.sali_kort_sali_id_seq FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT ON TABLE semantic.fasteignasala_nefnarar TO anon, authenticated;
GRANT SELECT ON TABLE semantic.fasteignasala_manudur  TO anon, authenticated;
CREATE POLICY fasteignasala_nefnarar_les ON semantic.fasteignasala_nefnarar FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY fasteignasala_manudur_les  ON semantic.fasteignasala_manudur  FOR SELECT TO anon, authenticated
  USING (adili_tegund = 'stofa'
         OR EXISTS (SELECT 1 FROM semantic.fasteignasala_nefnarar n
                     WHERE n.timabil_fra = fasteignasala_manudur.timabil_fra AND n.timabil_til = fasteignasala_manudur.timabil_til
                       AND n.gluggi = fasteignasala_manudur.gluggi AND n.regla_version = fasteignasala_manudur.regla_version
                       AND n.stada_sali IN ('bradabirgda','endanlegt')));

COMMIT;
