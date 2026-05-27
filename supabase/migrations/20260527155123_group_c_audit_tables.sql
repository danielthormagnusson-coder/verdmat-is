-- Phase X Group C — audit tables (pipeline_runs, pipeline_steps, inputs_snapshots)
--
-- Net-new, additive. Zero impact on existing tables/views.
-- SERVICE-ROLE ONLY: RLS enabled with no public policy (consistent with the
-- Group B least-privilege posture). Default-deny for anon + authenticated.
--
-- These tables back the lightweight Group C orchestration:
--   pipeline_runs       — one row per orchestrator invocation
--   pipeline_steps      — one row per step within a run (subprocess invocations)
--   inputs_snapshots    — one row per scoring run, fingerprints all inputs that
--                         determine the prediction batch (reproducibility ledger)
--
-- Deferred to future migrations (not built in this lota):
--   model_metrics       — feeds /heilsa dashboard
--   backup_manifests    — supplements rclone manifest
--   migrations_log      — supplements supabase_migrations.schema_migrations
--
-- Service-role writes from scripts/run_monthly.py + scripts/backfill_current_snapshot.py.
-- The future /heilsa dashboard will read via a Next.js API route using
-- SUPABASE_SERVICE_ROLE_KEY (not anon).

BEGIN;

-- =========================================================
-- pipeline_runs — per orchestrator invocation
-- =========================================================
CREATE TABLE public.pipeline_runs (
  id          bigserial PRIMARY KEY,
  run_type    text NOT NULL,                         -- 'monthly', 'd3_sync', 'column_grant_lockout', ...
  started_at  timestamptz NOT NULL DEFAULT now(),
  ended_at    timestamptz,
  exit_status text,                                  -- 'success', 'failed', 'halted', 'rolled_back'
  host        text,                                  -- gethostname() at run start
  git_sha     text,                                  -- HEAD of verdmat-is at run start
  summary     jsonb                                  -- free-form per run-type
);
CREATE INDEX pipeline_runs_started_idx ON public.pipeline_runs(started_at DESC);
CREATE INDEX pipeline_runs_run_type_idx ON public.pipeline_runs(run_type, started_at DESC);
COMMENT ON TABLE  public.pipeline_runs IS 'Phase X Group C — one row per orchestrator invocation';
COMMENT ON COLUMN public.pipeline_runs.run_type IS 'monthly | d3_sync | column_grant_lockout | manual | other';
COMMENT ON COLUMN public.pipeline_runs.exit_status IS 'success | failed | halted | rolled_back';

ALTER TABLE public.pipeline_runs ENABLE ROW LEVEL SECURITY;
-- No CREATE POLICY — default-deny for anon and authenticated. service_role bypasses RLS.

REVOKE ALL ON public.pipeline_runs FROM anon;
REVOKE ALL ON public.pipeline_runs FROM authenticated;

-- =========================================================
-- pipeline_steps — per step within a run
-- =========================================================
CREATE TABLE public.pipeline_steps (
  id              bigserial PRIMARY KEY,
  run_id          bigint NOT NULL REFERENCES public.pipeline_runs(id) ON DELETE CASCADE,
  step_name       text NOT NULL,                    -- 'refresh_cpi', 'refresh_kaupskra', ...
  step_order      smallint NOT NULL,
  started_at      timestamptz NOT NULL DEFAULT now(),
  ended_at        timestamptz,
  exit_code       integer,
  log_path        text,                             -- D:\... — operator-readable
  output_paths    jsonb,                            -- list of files produced
  rowcount_before integer,                          -- pre-step row count (shape-safety baseline)
  rowcount_after  integer,                          -- post-step row count
  notes           text
);
CREATE INDEX pipeline_steps_run_id_idx ON public.pipeline_steps(run_id, step_order);
CREATE INDEX pipeline_steps_step_name_idx ON public.pipeline_steps(step_name, started_at DESC);
COMMENT ON TABLE public.pipeline_steps IS 'Phase X Group C — one row per step within a pipeline_runs invocation';

ALTER TABLE public.pipeline_steps ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.pipeline_steps FROM anon;
REVOKE ALL ON public.pipeline_steps FROM authenticated;

-- =========================================================
-- inputs_snapshots — per scoring run, the reproducibility ledger
-- =========================================================
CREATE TABLE public.inputs_snapshots (
  id                    bigserial PRIMARY KEY,
  run_id                bigint REFERENCES public.pipeline_runs(id) ON DELETE SET NULL,
  captured_at           timestamptz NOT NULL DEFAULT now(),

  -- model identity
  model_version         text NOT NULL,              -- 'iter4_final_v1'
  calibration_version   text NOT NULL,              -- 'iter4_conformal_v1'

  -- inputs that determine predictions
  valuation_year        integer NOT NULL,
  valuation_month       integer NOT NULL,
  cpi_factor_at_val     numeric NOT NULL,           -- 1.0055 for 2026-04
  cpi_csv_md5           text NOT NULL,              -- SHA-256 of D:\cpi_verdtrygging.csv
  kaupskra_csv_md5      text NOT NULL,              -- SHA-256 of D:\kaupskra.csv
  kaupskra_last_mod     timestamptz,                -- HMS publication ts
  training_data_v2_md5  text NOT NULL,              -- SHA-256 of D:\training_data_v2.pkl
  feature_names_hash    text NOT NULL,              -- SHA-256 of model.feature_name() list

  -- universe sizes (sanity)
  properties_n          integer NOT NULL,
  predictions_n         integer NOT NULL,
  scorable_n            integer,                    -- residential+summer with byggar+matsvaedi
  held_n                integer,                    -- e.g. 8,426 in D3 terminology

  -- code identity
  git_sha               text NOT NULL,              -- HEAD of verdmat-is
  precompute_git_sha    text,                       -- HEAD of verdmat-is-precompute

  -- free-form auditing
  extra                 jsonb
);
CREATE INDEX inputs_snapshots_run_id_idx
  ON public.inputs_snapshots(run_id);
CREATE INDEX inputs_snapshots_model_cal_idx
  ON public.inputs_snapshots(model_version, calibration_version, captured_at DESC);
COMMENT ON TABLE public.inputs_snapshots IS
  'Phase X Group C — reproducibility ledger. Given a snapshot row + model files at that git_sha + source CSVs at those MD5s, the prediction batch is reproducible.';

ALTER TABLE public.inputs_snapshots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.inputs_snapshots FROM anon;
REVOKE ALL ON public.inputs_snapshots FROM authenticated;

COMMIT;
