-- 20260506_rls_baseline_audit.sql
--
-- Baseline RLS + GRANT cleanup per SCRAPER_SPEC_v1 §3.3 pattern.
--
-- Resolves Supabase security alert "rls_disabled_in_public" (2026-05-03)
-- by enabling row-level security on every table in public, granting
-- explicit SELECT to anon/authenticated for dashboard-public surfaces,
-- and revoking the over-permissive default DML grants (DELETE, INSERT,
-- UPDATE, TRUNCATE) from anon/authenticated everywhere they should not
-- have them.
--
-- Categorization (locked 2026-05-06 post-empirical-verification):
--
--   DASHBOARD-PUBLIC (14 tables) — RLS on, public_read SELECT policy,
--   anon/authenticated keep SELECT only, service_role unrestricted.
--
--   USER-OWNED (4 tables, RLS already enabled with auth.uid() policies)
--   — REVOKE ALL from anon (anon has no role on these tables);
--   authenticated keeps full DML for users to manage their own rows
--   (RLS policy gates by user_id); service_role unrestricted.
--
--   VIEWS (4) — REVOKE write privileges from anon/authenticated for
--   hygiene; SELECT is inherited from underlying (now-RLS'd) tables.
--
-- Idempotent: ALTER TABLE ENABLE RLS is a no-op if already enabled;
-- DROP POLICY IF EXISTS handles repeat runs; REVOKE/GRANT are
-- idempotent. Wrapped in single transaction for all-or-nothing apply.

BEGIN;

-- ============================================================
-- Section 1 — Dashboard-public tables (14)
-- ============================================================
-- Pattern per table:
--   1. Enable RLS
--   2. Drop and recreate public_read policy (idempotent)
--   3. Revoke all from anon, authenticated (default-deny baseline)
--   4. Grant SELECT to anon, authenticated (frontend read path)
--   5. Grant all to service_role (scraper/precompute writes)

-- properties (~125K rows, 206 MB)
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON properties;
CREATE POLICY public_read ON properties FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON properties FROM anon, authenticated;
GRANT SELECT ON properties TO anon, authenticated;
GRANT ALL ON properties TO service_role;

-- predictions (~110K rows, 37 MB)
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON predictions;
CREATE POLICY public_read ON predictions FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON predictions FROM anon, authenticated;
GRANT SELECT ON predictions TO anon, authenticated;
GRANT ALL ON predictions TO service_role;

-- predictions_iter3v2 (~110K rows, 18 MB) — debug-mode comparison surface
ALTER TABLE predictions_iter3v2 ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON predictions_iter3v2;
CREATE POLICY public_read ON predictions_iter3v2 FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON predictions_iter3v2 FROM anon, authenticated;
GRANT SELECT ON predictions_iter3v2 TO anon, authenticated;
GRANT ALL ON predictions_iter3v2 TO service_role;

-- comps_index (1.1M rows, 225 MB)
ALTER TABLE comps_index ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON comps_index;
CREATE POLICY public_read ON comps_index FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON comps_index FROM anon, authenticated;
GRANT SELECT ON comps_index TO anon, authenticated;
GRANT ALL ON comps_index TO service_role;

-- feature_attributions (1.1M rows, 119 MB)
ALTER TABLE feature_attributions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON feature_attributions;
CREATE POLICY public_read ON feature_attributions FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON feature_attributions FROM anon, authenticated;
GRANT SELECT ON feature_attributions TO anon, authenticated;
GRANT ALL ON feature_attributions TO service_role;

-- feature_attributions_iter3v2 (1.1M rows, 121 MB) — debug-mode surface
ALTER TABLE feature_attributions_iter3v2 ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON feature_attributions_iter3v2;
CREATE POLICY public_read ON feature_attributions_iter3v2 FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON feature_attributions_iter3v2 FROM anon, authenticated;
GRANT SELECT ON feature_attributions_iter3v2 TO anon, authenticated;
GRANT ALL ON feature_attributions_iter3v2 TO service_role;

-- sales_history (~173K rows, 24 MB)
ALTER TABLE sales_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON sales_history;
CREATE POLICY public_read ON sales_history FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON sales_history FROM anon, authenticated;
GRANT SELECT ON sales_history TO anon, authenticated;
GRANT ALL ON sales_history TO service_role;

-- repeat_sale_index (~2,673 rows, 584 kB)
ALTER TABLE repeat_sale_index ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON repeat_sale_index;
CREATE POLICY public_read ON repeat_sale_index FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON repeat_sale_index FROM anon, authenticated;
GRANT SELECT ON repeat_sale_index TO anon, authenticated;
GRANT ALL ON repeat_sale_index TO service_role;

-- last_listing_text (~60K rows, 128 MB)
-- NOTE: column inventory verified 2026-05-06 — no PII (no agent_phone,
-- no agent_email). lysing_plain is publicly-displayed listing
-- description; augl_id is per-source listing identifier (back-link
-- concern flagged for separate v1.1 hardening pass via column-stripping
-- view, not in scope of this audit).
ALTER TABLE last_listing_text ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON last_listing_text;
CREATE POLICY public_read ON last_listing_text FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON last_listing_text FROM anon, authenticated;
GRANT SELECT ON last_listing_text TO anon, authenticated;
GRANT ALL ON last_listing_text TO service_role;

-- ats_lookup (~65 rows, 80 kB)
ALTER TABLE ats_lookup ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON ats_lookup;
CREATE POLICY public_read ON ats_lookup FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON ats_lookup FROM anon, authenticated;
GRANT SELECT ON ats_lookup TO anon, authenticated;
GRANT ALL ON ats_lookup TO service_role;

-- ats_lookup_by_quarter (~913 rows, 360 kB)
ALTER TABLE ats_lookup_by_quarter ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON ats_lookup_by_quarter;
CREATE POLICY public_read ON ats_lookup_by_quarter FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON ats_lookup_by_quarter FROM anon, authenticated;
GRANT SELECT ON ats_lookup_by_quarter TO anon, authenticated;
GRANT ALL ON ats_lookup_by_quarter TO service_role;

-- ats_dashboard_monthly_heat (~2,501 rows, 624 kB)
ALTER TABLE ats_dashboard_monthly_heat ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON ats_dashboard_monthly_heat;
CREATE POLICY public_read ON ats_dashboard_monthly_heat FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON ats_dashboard_monthly_heat FROM anon, authenticated;
GRANT SELECT ON ats_dashboard_monthly_heat TO anon, authenticated;
GRANT ALL ON ats_dashboard_monthly_heat TO service_role;

-- llm_aggregates_quarterly (~1,450 rows, 416 kB)
ALTER TABLE llm_aggregates_quarterly ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON llm_aggregates_quarterly;
CREATE POLICY public_read ON llm_aggregates_quarterly FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON llm_aggregates_quarterly FROM anon, authenticated;
GRANT SELECT ON llm_aggregates_quarterly TO anon, authenticated;
GRANT ALL ON llm_aggregates_quarterly TO service_role;

-- model_tracking_history (small) — flipped from service-role-only to
-- dashboard-public after frontend grep found anon-key reads at
-- lib/dashboard-queries.js:49 and app/markadur/modelstada/page.js:44, 61
ALTER TABLE model_tracking_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON model_tracking_history;
CREATE POLICY public_read ON model_tracking_history FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON model_tracking_history FROM anon, authenticated;
GRANT SELECT ON model_tracking_history TO anon, authenticated;
GRANT ALL ON model_tracking_history TO service_role;


-- ============================================================
-- Section 2 — User-owned tables (4) — RLS already enabled
-- ============================================================
-- These tables already have correct auth.uid() policies. The remaining
-- gap is anon over-grants (anon currently has DELETE/INSERT/UPDATE/
-- TRUNCATE despite having no role on user-owned data). REVOKE ALL from
-- anon; keep authenticated grants intact (RLS policy gates by
-- user_id); service_role unrestricted.

REVOKE ALL ON pro_users FROM anon;
REVOKE ALL ON saved_properties FROM anon;
REVOKE ALL ON saved_searches FROM anon;
REVOKE ALL ON saved_valuations FROM anon;


-- ============================================================
-- Section 3 — Views (4)
-- ============================================================
-- Views inherit row-level access from underlying (now-RLS'd) tables.
-- SELECT continues to work via inheritance. Write privileges on views
-- are mostly nonsensical (Postgres only auto-makes simple views
-- updatable) but are revoked here for hygiene and to make \dp output
-- reflect intent.

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON latest_regime_per_cell FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON regime_per_cell_monthly FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON repeat_sale_index_by_segment FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON repeat_sale_index_main_pooled FROM anon, authenticated;


COMMIT;
