-- is_suspect_comparable: per-sale comp-visibility filter (REFINED-B ruleset).
-- Additive, nullable columns; reversible via DROP COLUMN. sales_history is public_read
-- SELECT-only (RLS) so new columns inherit anon read; no new grant.
-- Applied via Supabase MCP apply_migration 2026-07-02 (ledger version 20260702082504).
ALTER TABLE public.sales_history
  ADD COLUMN IF NOT EXISTS is_suspect_comparable boolean,
  ADD COLUMN IF NOT EXISTS suspect_reason text,
  ADD COLUMN IF NOT EXISTS suspect_ruleset_version text;

COMMENT ON COLUMN public.sales_history.is_suspect_comparable IS
  'REFINED-B: technically-valid (ONOTHAEFUR=0) sale that is untrustworthy as a VISIBLE comp. R1 KAUPVERD<=1; R2 kv not in [0.50,2.00]; R3 sale EINFLM>HMS by >10% OR multi-fastnum deed; R4 FULLBUID=0 OR age<=2. See docs/DECISIONS.md 2026-07-02.';
COMMENT ON COLUMN public.sales_history.suspect_reason IS 'Plus-joined active rule names, NULL when not suspect.';
COMMENT ON COLUMN public.sales_history.suspect_ruleset_version IS 'Ruleset version stamp, e.g. refinedB-v1-2026-07-02.';
