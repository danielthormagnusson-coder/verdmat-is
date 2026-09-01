-- cc179_corrections_schema.sql — breytingaskrá fyrir public.sales_history.
--
-- Rót (cc178 §3.2, cc179 q02): daily_sales_refresh.py var NEW-KEYS-ONLY. Röð sem var
-- þegar inni var aldrei endurleidd, svo leiðrétting HMS á kaupskránni barst aldrei.
-- Mælt 2026-09-01: 137 raðir af 229.998 víkja frá ferskri kaupskrá (1 verð ×10,
-- 3 onothaefur 0→1, 94 suspect-flögg, 40 suspect_reason).
--
-- Þessi tafla er BREYTINGASKRÁIN sem UPDATE-armurinn skrifar í: ein lína á hvern
-- REIT sem breyttist, með gamla og nýja gildinu og útgáfu kaupskrárinnar sem
-- leiðréttingin kom úr. Hún er hvorki lesin af vefnum né af PostgREST — hún er
-- rekjanleiki (og rollback-heimild) fyrir sjálfvirk skrif á staðreyndatöflu.
--
-- Keyrsla: python scripts/cc179_apply_corrections.py --schema
-- Rollback: sjá cc179_corrections_rollback.sql

CREATE TABLE IF NOT EXISTS public.sales_history_corrections (
  id                       bigserial PRIMARY KEY,
  corrected_at             timestamptz NOT NULL DEFAULT now(),
  run_id                   bigint,          -- public.pipeline_runs.id (má vera NULL)
  source                   text        NOT NULL,   -- 'daily_sales_refresh' | 'cc179_sweep'
  faerslunumer             bigint      NOT NULL,
  fastnum                  bigint      NOT NULL,
  column_name              text        NOT NULL,
  old_value                text,            -- NULL = reiturinn var NULL
  new_value                text,
  kaupskra_md5             text,            -- content_md5 úr D:\kaupskra_fetch_state.json
  kaupskra_last_modified   text,            -- Last-Modified haus HMS-skrárinnar
  suspect_ruleset_version  text,            -- suspect_rules.RULESET_VERSION við skrif
  anchor_ym                text             -- pipeline_config.sales_history_anchor_ym
);

CREATE INDEX IF NOT EXISTS idx_shc_key
  ON public.sales_history_corrections (faerslunumer, fastnum);
CREATE INDEX IF NOT EXISTS idx_shc_at
  ON public.sales_history_corrections (corrected_at DESC);
CREATE INDEX IF NOT EXISTS idx_shc_run
  ON public.sales_history_corrections (run_id);

COMMENT ON TABLE public.sales_history_corrections IS
  'cc179: breytingaskrá — hver reitur í public.sales_history sem UPDATE-armur '
  'daily_sales_refresh (eða cc179-sópunin) skrifaði yfir, með gömlu/nýju gildi og '
  'útgáfu kaupskrárinnar sem leiðréttingin kom úr. Ein lína á reit, ekki á röð.';

-- ----------------------------------------------------------------------------
-- LÆSING (cc179 q09): Supabase-sjálfgildið `ALTER DEFAULT PRIVILEGES ... GRANT ALL
-- ON TABLES TO anon, authenticated` gaf ÞESSARI TÖFLU (og staging-afritinu) fullt
-- DML — SELECT/INSERT/UPDATE/DELETE/TRUNCATE — til `anon`, með RLS SLÖKKT. Mælt með
-- relacl: `anon=arwdDxtm/postgres`. Til samanburðar ber public.sales_history sjálf
-- `anon=r` og RLS á. Breytingaskrá og rollback-heimild sem anon getur TRUNCATE-að
-- er hvorugt. Læst hér, í sömu migration og taflan verður til.
-- Sbr. feedback_relacl_er_eina_grantor_maelingin.
-- ----------------------------------------------------------------------------
REVOKE ALL ON public.sales_history_corrections FROM PUBLIC, anon, authenticated;
GRANT  SELECT ON public.sales_history_corrections TO service_role;
ALTER TABLE public.sales_history_corrections ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON SEQUENCE public.sales_history_corrections_id_seq FROM PUBLIC, anon, authenticated;
