-- =====================================================================
-- cc213 fasi 2 — semantic.sali_kort fær staðfestingarstimpil (rýni Danna 29.09).
-- Rollback: supabase/rollback/20260929100000_cc213b_sali_kort_stadfesting_rollback.sql
-- virkt = false + stadfest_af = útilokaður sali: sölur hans telja hjá stofu, ekki á sala-lista.
-- =====================================================================
BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan
ALTER TABLE semantic.sali_kort
  ADD COLUMN stadfest_af   text,
  ADD COLUMN stadfest_dags date,
  ADD COLUMN athugasemd    text;
COMMENT ON COLUMN semantic.sali_kort.stadfest_af IS 'cc213: hver staðfesti röðina handvirkt (NULL = sjálfvirk).';
COMMIT;
