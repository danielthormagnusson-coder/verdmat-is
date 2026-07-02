-- Rollback: is_suspect_comparable persist on public.sales_history (2026-07-02)
-- Reverses migration 20260702082504_add_is_suspect_comparable_to_sales_history + the one-time backfill.
-- Reversible: these are additive nullable columns, no existing data touched.

ALTER TABLE public.sales_history
  DROP COLUMN IF EXISTS is_suspect_comparable,
  DROP COLUMN IF EXISTS suspect_reason,
  DROP COLUMN IF EXISTS suspect_ruleset_version;

DELETE FROM public.pipeline_runs WHERE run_type = 'sales_history_suspect_backfill';

-- Code revert (durable-pipeline wiring), if also reverting the ruleset:
--   git -C D:\verdmat-is\app checkout -- scripts/rebuild_sales_history.py scripts/daily_sales_refresh.py
--   del D:\verdmat-is\app\scripts\suspect_rules.py D:\verdmat-is\app\scripts\backfill_suspect_sales_history.py
