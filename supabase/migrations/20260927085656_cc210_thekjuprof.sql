-- =====================================================================
-- cc210 C1 — scraper.thekjuprof: daglegt þekjupróf mbl ↔ scraper.listings
-- Skrifuð af scripts/thekjuprof_mbl.py (Task Scheduler verdmat-daily-thekjuprof 07:15).
-- Rollback: supabase/rollback/20260927085656_cc210_thekjuprof_rollback.sql
--
-- Ein röð per keyrsla. NEFNARASKYLDAN ER DÁLKASKYLDA: hver teljari á sér
-- NOT NULL nefnara og CHECK teljari <= nefnari (NOT NULL er hlífin, CHECK
-- eitt hleypir NULL í gegn).
--   gap_*    = lifandi innlendar mbl-söluauglýsingar í glugga (stofnaðar síðustu
--              14 d, br_dags < delta-bendli) sem EKKI eru í scraper.listings —
--              ein nákvæm aggregate-talning (_nin á okkar auðkenni), ekki úrtak.
--   urtak_*  = 4 síður × 16 slembi á öllu lifandi menginu (klasa-úrtak, ekki
--              óbjagað mat á fjölda; bókað sem vísbending um eldra gat).
--   draug_*  = slembi „Á sölu"-fastnum (v_eign_virk_auglysing, mbl sala) sem
--              EKKI bera lifandi auglýsingu á mbl. draug_ovisst = svar trunkerað
--              (16-raða þak) → utan nefnara.
-- Ekki app-lesin: RLS á, engar heimildir til anon/authenticated (default-deny).
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan

CREATE TABLE scraper.thekjuprof (
  id             bigserial   PRIMARY KEY,
  maelt_kl       timestamptz NOT NULL DEFAULT now(),
  dags           date        NOT NULL,
  adferd         text        NOT NULL,          -- útgáfa aðferðar, t.d. 'thekjuprof_mbl_v1'
  gap_n          integer     NOT NULL,
  gap_nefnari    integer     NOT NULL,
  urtak_vantar   integer     NOT NULL,
  urtak_nefnari  integer     NOT NULL,
  universe_n     integer     NOT NULL,          -- lifandi innlendar verðlagðar söluaugl. á mbl (aggregate)
  draug_n        integer     NOT NULL,
  draug_nefnari  integer     NOT NULL,
  draug_ovisst   integer     NOT NULL DEFAULT 0,
  beidnir        integer     NOT NULL,          -- HTTP-beiðnir á mbl í keyrslunni
  vidvorun       text,                          -- NULL = engin viðvörun
  upplysingar    jsonb       NOT NULL DEFAULT '{}'::jsonb,  -- gluggi, bendlar, dæmi-auðkenni
  CONSTRAINT thekjuprof_gap_chk    CHECK (gap_n >= 0 AND gap_nefnari >= 0 AND gap_n <= gap_nefnari),
  CONSTRAINT thekjuprof_urtak_chk  CHECK (urtak_vantar >= 0 AND urtak_nefnari >= 0 AND urtak_vantar <= urtak_nefnari),
  CONSTRAINT thekjuprof_draug_chk  CHECK (draug_n >= 0 AND draug_nefnari >= 0 AND draug_n <= draug_nefnari
                                          AND draug_ovisst >= 0),
  CONSTRAINT thekjuprof_adferd_chk CHECK (length(adferd) > 0)
);

CREATE INDEX thekjuprof_dags_idx ON scraper.thekjuprof (dags DESC);

COMMENT ON TABLE scraper.thekjuprof IS
  'cc210 C1: daglegt þekjupróf mbl (gap m/ nefnara, klasa-úrtak, draugar á Á sölu-kortum). Skrifuð af scripts/thekjuprof_mbl.py.';

ALTER TABLE scraper.thekjuprof ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE scraper.thekjuprof FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON SEQUENCE scraper.thekjuprof_id_seq FROM PUBLIC, anon, authenticated, service_role;

COMMIT;
