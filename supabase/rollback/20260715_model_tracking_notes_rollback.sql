-- Rollback fyrir 20260715_model_tracking_notes.sql (cc4)
-- Fjarlægir notes-dálkinn OG 2026-07 vaktar-röðina; 2026-04 röðin stendur
-- (notes-gildi hennar hverfur með dálknum).
DELETE FROM public.model_tracking_history
WHERE period = '2026-07' AND segment = 'RESIDENTIAL_EX_SUMMER'
  AND calibration_version = 'iter4_conformal_v1+segcal_fb';
ALTER TABLE public.model_tracking_history DROP COLUMN IF EXISTS notes;
