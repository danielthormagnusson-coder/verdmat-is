-- cc4 2026-07-15: notes-dálkur á model_tracking_history — aðgreinir mæligrunna
-- (held-splitt við þjálfun vs lifandi eftir-cutoff holdout) í sömu trend-seríu.
-- Additive; engin grants/RLS-breyting (taflan ber þegar public_read SELECT policy).
-- Rollback: supabase/rollback/20260715_model_tracking_notes_rollback.sql
ALTER TABLE public.model_tracking_history ADD COLUMN IF NOT EXISTS notes text;
COMMENT ON COLUMN public.model_tracking_history.notes IS
  'Mæligrunnur/samhengi raðar (t.d. held-splitt við þjálfun vs lifandi post-cutoff holdout). cc4 2026-07-15.';
