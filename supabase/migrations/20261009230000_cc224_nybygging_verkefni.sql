-- =====================================================================
-- cc224 fasi 1 — /nybyggingar: gagnalag (eitt verkefni = einn kassi)
-- Skrifað af scripts/cc224_nybygging_verkefni.py (útgáfa cc224-v1).
-- Rollback: supabase/rollback/20261009230000_cc224_nybygging_verkefni_rollback.sql
-- Skil: D:\_audit\cc224_nybyggingar\SKIL_CC224_0.md (§7) + SKIL_CC224_1.md (ákvarðanir Danna 09.10).
--
-- Skilgreining (cc224-v1, ákvörðun Danna 09.10 — sú sem cc223-backlog segir að aðrar síður samræmist við):
--   nýbygging (eining) = íbúð skv. reglu 7 ∧ (FULLBUID=0 ∨ BYGGAR ≥ ár−2 ∨ (byggingarstig B0–B3 ∧ matsstig 0–6))
--   „fullbúin innan tveggja ára EÐA í byggingu skv. auglýsingu/HMS"
--   verkefni = landeign, sameinuð þar sem STAÐFEST verkefnisslóð og gata eru sameiginleg (nybygging_slodir)
--   Y (einingar verkefnis) = íbúðir á landeignum verkefnisins byggðar ≥ ár−3 eða innan skilgreiningar;
--       eldri hús á sömu lóð ekki talin; óskipt fastnúmer (≥3 auglýstar stærðir) = max(1, auglýstar einingar)
--   X (seldar) = einingar með þinglýstum samningi ONOTHAEFUR=0 frá 2021-01-01; magnsala (samningur > 1 fastnr)
--       talin í X, merkt, utan kr/m²
--   gólf: Y ≥ 4 ∧ (X ≥ 1 ∨ ≥ 1 virk auglýsing) ∧ ≥ 1 eining innan skilgreiningar
--
-- Fjórar töflur:
--   semantic.nybygging_keyrslur  endurskoðunarslóð: ein röð per keyrsla (nefnarar + md5). LÆST.
--   semantic.nybygging_slodir    handstaðfestar verkefnisslóðir (Danni). LÆST. Tóm þar til slodir_ryni.csv er skilað.
--   semantic.nybygging_verkefni  kassarnir. anon/authenticated SELECT.
--   semantic.nybygging_einingar  einingalisti per verkefni (hlekkur á /eign). anon/authenticated SELECT.
--
-- NEFNARASKYLDA ER DÁLKASKYLDA (sbr. cc210/cc213): teljarar NOT NULL + CHECK teljari ≤ nefnari.
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan

-- ---------------------------------------------------------------------
-- 1. Endurskoðunarslóð
-- ---------------------------------------------------------------------
CREATE TABLE semantic.nybygging_keyrslur (
  keyrsla_id            bigserial   PRIMARY KEY,
  utgafa                text        NOT NULL,
  skilgreining          text        NOT NULL,          -- reglan orðrétt eins og skriftan beitti henni
  hofst                 timestamptz NOT NULL,
  lauk                  timestamptz NOT NULL DEFAULT now(),
  sala_fra              date        NOT NULL,          -- sölugólf (2021-01-01)
  data_through          date,                          -- max thinglystdags í sales_history
  listings_snapshot     timestamptz,                   -- max last_seen_at söluauglýsinga
  n_einingar_skilgr     integer     NOT NULL,          -- íbúðir innan skilgreiningar (landið)
  n_hopar               integer     NOT NULL,          -- verkefnahópar fyrir gólf
  n_verkefni            integer     NOT NULL,          -- á gólfi = raðir í nybygging_verkefni
  n_uppselt             integer     NOT NULL,
  n_einingar            integer     NOT NULL,          -- ΣY
  n_seld                integer     NOT NULL,          -- ΣX
  n_magnseld            integer     NOT NULL,
  n_virkar              integer     NOT NULL,
  n_slodir_stadfestar   integer     NOT NULL,
  n_sameinad_um_slod    integer     NOT NULL,          -- landeignir sem sameinuðust öðrum um staðfesta slóð
  md5_verkefni          text        NOT NULL,
  md5_einingar          text        NOT NULL,
  CONSTRAINT keyrslur_tolur_chk CHECK (
        n_verkefni BETWEEN 0 AND n_hopar AND n_uppselt BETWEEN 0 AND n_verkefni
    AND n_seld BETWEEN 0 AND n_einingar AND n_magnseld BETWEEN 0 AND n_seld AND n_virkar >= 0)
);
CREATE INDEX nybygging_keyrslur_utgafa_idx ON semantic.nybygging_keyrslur (utgafa, lauk DESC);
COMMENT ON TABLE semantic.nybygging_keyrslur IS
  'cc224: ein röð per keyrsla scripts/cc224_nybygging_verkefni.py — nefnarar, gólf og md5 þeirra raða sem voru skrifaðar. LÆST.';

-- ---------------------------------------------------------------------
-- 2. Staðfestar verkefnisslóðir (óstaðfest slóð birtist aldrei og sameinar aldrei verkefni)
-- ---------------------------------------------------------------------
CREATE TABLE semantic.nybygging_slodir (
  landeign_nr     text        NOT NULL,
  slod            text        NOT NULL,              -- lén(+slóð) í lágstöfum, án https:// og www.
  stadfest        boolean     NOT NULL,              -- true = birtist og má sameina; false = hafnað
  stadfest_af     text        NOT NULL,
  stadfest_dags   date        NOT NULL,
  athugasemd      text,
  stofnad         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (landeign_nr, slod),
  CONSTRAINT nybygging_slodir_slod_chk CHECK (slod ~ '^[a-z0-9][a-z0-9.\-]*\.is(/[a-z0-9._\-]+)*$')
);
COMMENT ON TABLE semantic.nybygging_slodir IS
  'cc224: handstaðfestar verkefnisslóðir (slodir_ryni.csv, Danni). Aðeins stadfest = true les skriftan. LÆST.';

-- ---------------------------------------------------------------------
-- 3. Verkefni (kassar)
-- ---------------------------------------------------------------------
CREATE TABLE semantic.nybygging_verkefni (
  utgafa                  text        NOT NULL,
  verkefni_id             text        NOT NULL,      -- lægsta landeign_nr hópsins (stöðugt)
  slug                    text        NOT NULL,      -- <verkefni_id>-<heiti>, slóð /nybyggingar/[slug]
  heiti                   text        NOT NULL,
  heiti_uppruni           text        NOT NULL CHECK (heiti_uppruni IN ('hms','auglysing')),
  gotur                   text[]      NOT NULL,
  postnr                  integer,
  postheiti               text,
  sveitarfelag            text,
  landeignir              text[]      NOT NULL,
  lat                     double precision,
  lng                     double precision,
  n_einingar              integer     NOT NULL,      -- Y
  n_einingar_hms          integer     NOT NULL,      -- fastnúmer í HMS
  n_heildareiningar       integer     NOT NULL,      -- óskipt fastnúmer (Y = max(HMS, auglýstar))
  n_seld                  integer     NOT NULL,      -- X (þ.m.t. magnsölur)
  n_magnseld              integer     NOT NULL,
  n_virkar                integer     NOT NULL,      -- einingar á sölu núna (eignarstig)
  n_oseldar               integer     NOT NULL,      -- Y − X
  n_oseldar_oauglystar    integer     NOT NULL,      -- óseldar án virkrar auglýsingar
  n_b0                    integer     NOT NULL,      -- byggingarstig (fastnúmer); b0 = B0 eða óskráð
  n_b1                    integer     NOT NULL,
  n_b2                    integer     NOT NULL,
  n_b3                    integer     NOT NULL,
  n_b4                    integer     NOT NULL,
  fyrsta_sala             date,
  sidasta_sala            date,
  kr_m2_seld              integer,                   -- miðgildi, sölur 1 fastnr, ONOTH=0
  n_kr_m2_seld            integer     NOT NULL,
  kr_m2_asett             integer,                   -- miðgildi virkra auglýsinga (eining = fastnr/stærð/herbergi)
  n_kr_m2_asett           integer     NOT NULL,
  n_laekkanir             integer     NOT NULL,      -- Verðvakt v2, lækkanir (án grunsamlegra)
  stofur                  jsonb       NOT NULL,      -- topp-3 [{lykill, nafn, n_einingar}]
  byggingaradili          text,                      -- aðeins þar sem hann finnst í texta
  byggingaradili_n_augl   integer     NOT NULL DEFAULT 0,
  slod                    text,                      -- STAÐFEST verkefnisslóð eða NULL
  byggar_min              smallint,
  byggar_max              smallint,
  sidasta_virkni          date        NOT NULL,      -- max(sala, ný auglýsing, verðbreyting) — röðun kassa
  uppselt                 boolean     NOT NULL,
  keyrsla_id              bigint      NOT NULL REFERENCES semantic.nybygging_keyrslur (keyrsla_id),
  reiknad                 timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (utgafa, verkefni_id),
  CONSTRAINT nybygging_verkefni_slug_uk UNIQUE (utgafa, slug),
  CONSTRAINT nybygging_verkefni_tolur_chk CHECK (
        n_einingar >= 4
    AND n_einingar_hms BETWEEN 1 AND n_einingar AND n_heildareiningar BETWEEN 0 AND n_einingar_hms
    AND n_seld BETWEEN 0 AND n_einingar AND n_magnseld BETWEEN 0 AND n_seld
    AND n_virkar BETWEEN 0 AND n_einingar
    AND n_oseldar = n_einingar - n_seld
    AND n_oseldar_oauglystar BETWEEN 0 AND n_oseldar
    AND n_b0 + n_b1 + n_b2 + n_b3 + n_b4 = n_einingar_hms
    AND n_kr_m2_seld BETWEEN 0 AND n_seld - n_magnseld
    AND (n_kr_m2_seld > 0) = (kr_m2_seld IS NOT NULL)
    AND (n_kr_m2_asett > 0) = (kr_m2_asett IS NOT NULL)
    AND n_laekkanir >= 0
    AND (n_seld >= 1 OR n_virkar >= 1)
    AND uppselt = (n_seld = n_einingar)
    AND (fyrsta_sala IS NULL OR sidasta_sala >= fyrsta_sala)),
  CONSTRAINT nybygging_verkefni_stofur_chk CHECK (jsonb_typeof(stofur) = 'array' AND jsonb_array_length(stofur) <= 3),
  CONSTRAINT nybygging_verkefni_slod_chk CHECK (slod IS NULL OR slod ~ '^[a-z0-9][a-z0-9.\-]*\.is(/[a-z0-9._\-]+)*$')
);
CREATE INDEX nybygging_verkefni_rod_idx ON semantic.nybygging_verkefni (utgafa, uppselt, sidasta_virkni DESC, verkefni_id);
COMMENT ON TABLE semantic.nybygging_verkefni IS
  'cc224: einn kassi per nýbyggingarverkefni (gólf: Y ≥ 4 ∧ (sala ∨ virk auglýsing)). Röðun: uppselt neðst, sidasta_virkni DESC, verkefni_id. '
  'slod aðeins úr nybygging_slodir.stadfest = true.';

-- ---------------------------------------------------------------------
-- 4. Einingar (síða verkefnis)
-- ---------------------------------------------------------------------
CREATE TABLE semantic.nybygging_einingar (
  utgafa            text        NOT NULL,
  fastnum           bigint      NOT NULL,
  verkefni_id       text        NOT NULL,
  heimilisfang      text,
  merking           text,                          -- HMS matseining, t.d. 05-0108
  einflm            numeric,
  fjherb            smallint,
  byggar            smallint,
  byggingarstig     text,
  innan_skilgr      boolean     NOT NULL,          -- false = byggð ≥ ár−3 en utan skilgreiningar (fullbúin eldri)
  heildareining     boolean     NOT NULL,
  n_undireiningar   integer     NOT NULL,          -- 1, eða auglýstar einingar óskipts fastnúmers
  stada             text        NOT NULL CHECK (stada IN ('seld','magnsala','a_solu','oseld')),
  sala_dags         date,
  kaupverd          bigint,                        -- kr; NULL fyrir magnsölu
  kr_m2             integer,
  asett_verd        bigint,
  asett_flm         numeric,
  n_laekkanir       integer     NOT NULL,
  PRIMARY KEY (utgafa, fastnum),
  CONSTRAINT nybygging_einingar_verkefni_fk FOREIGN KEY (utgafa, verkefni_id)
        REFERENCES semantic.nybygging_verkefni (utgafa, verkefni_id) ON DELETE CASCADE,
  CONSTRAINT nybygging_einingar_chk CHECK (
        n_undireiningar >= 1 AND (heildareining OR n_undireiningar = 1)
    AND (stada IN ('seld','magnsala')) = (sala_dags IS NOT NULL)
    AND (stada = 'seld' OR kaupverd IS NULL)
    AND (kr_m2 IS NULL OR stada = 'seld')
    AND n_laekkanir >= 0)
);
CREATE INDEX nybygging_einingar_verkefni_idx ON semantic.nybygging_einingar (utgafa, verkefni_id);
COMMENT ON TABLE semantic.nybygging_einingar IS
  'cc224: einingar per verkefni. stada: seld (ONOTH=0, 1 fastnr) · magnsala (ONOTH=0, samningur > 1 fastnr) · a_solu (virk auglýsing, eignarstig) · oseld.';

-- ---------------------------------------------------------------------
-- Heimildir: default-deny, svo opnað nákvæmlega
-- ---------------------------------------------------------------------
ALTER TABLE semantic.nybygging_keyrslur  ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic.nybygging_slodir    ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic.nybygging_verkefni  ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic.nybygging_einingar  ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE semantic.nybygging_keyrslur, semantic.nybygging_slodir,
                   semantic.nybygging_verkefni, semantic.nybygging_einingar
       FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON SEQUENCE semantic.nybygging_keyrslur_keyrsla_id_seq FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT ON TABLE semantic.nybygging_verkefni TO anon, authenticated;
GRANT SELECT ON TABLE semantic.nybygging_einingar TO anon, authenticated;
CREATE POLICY nybygging_verkefni_les ON semantic.nybygging_verkefni FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY nybygging_einingar_les ON semantic.nybygging_einingar FOR SELECT TO anon, authenticated USING (true);

COMMIT;
