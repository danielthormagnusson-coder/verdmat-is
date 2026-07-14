-- cc9 RLS-öryggisfix — loka berskjölduðum snapshot-/staging-töflum
--
-- BAKGRUNNUR: Supabase security-linter flaggaði rls_disabled_in_public
-- (12.07) á public-skemanu. Full skönnun (pg_class.relrowsecurity=false)
-- fann þrjár töflur án RLS í public:
--
--   1. postheiti_snapshot_pre_d3fix_20260706 (232.887 raðir, eigandi postgres)
--      — rollback-snapshot postheiti fyrir d3-fix. HAFÐI FULL default-grants
--      á anon+authenticated (arwdDxtm). RAUN-PRÓF með anon-lykli SANNAÐI opna
--      skrifaleið: anon SELECT 200, anon DELETE 200 (eyddi prófröð). Þetta
--      var eina raunverulega berskjaldaða taflan.
--   2. predictions_staging (167.503 raðir, eigandi postgres) — RLS af EN engin
--      anon/auth-grants → PostgREST náði henni ekki (linter flaggaði hana ekki).
--      Hert hér samt til varnar-dýptar.
--   3. spatial_ref_sys (PostGIS-kerfistafla, eigandi supabase_admin) —
--      MEÐHÖNDLUÐ SÉR (sjá neðar); ekki lagfæranleg úr postgres-hlutverki.
--
-- Flokkur (a) — snapshot/staging: default-deny (ENABLE RLS + REVOKE grants).
-- Töflunum er EKKI eytt — þær eru enn gildar rollback-tryggingar; service_role
-- heldur fullum aðgangi (fer framhjá RLS). Engin policy bætt við (ekki app-lesnar).
ALTER TABLE public.postheiti_snapshot_pre_d3fix_20260706 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.postheiti_snapshot_pre_d3fix_20260706 FROM anon, authenticated;
ALTER TABLE public.predictions_staging ENABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────
-- spatial_ref_sys (flokkur c) — KNOWN-ACCEPTED, ekki keyrt í þessari migration.
-- PostGIS-kerfistafla í eigu supabase_admin. Reynt var:
--   REVOKE INSERT, UPDATE, DELETE ON public.spatial_ref_sys FROM anon, authenticated;
-- en það var NO-OP: grantin voru gefin AF supabase_admin, og postgres er hvorki
-- eigandi né grantor → getur ekki afturkallað þau (has_table_privilege óbreytt
-- eftir á). ENABLE RLS blokkast sömuleiðis af eignarhaldi. Þetta er þekkt
-- Supabase+PostGIS-tilvik sem verður ekki leyst án supabase_admin/superuser.
-- Taflan geymir engin app-gögn (SRID-skilgreiningar), einn rls_disabled-flagg
-- verður áfram og er samþykktur. Sjá RLS_FIX_20260714T214739Z.md.

-- ─────────────────────────────────────────────────────────────────────
-- ROLLBACK (skrifað fyrir apply):
--   ALTER TABLE public.postheiti_snapshot_pre_d3fix_20260706 DISABLE ROW LEVEL SECURITY;
--   GRANT ALL ON public.postheiti_snapshot_pre_d3fix_20260706 TO anon, authenticated;
--   ALTER TABLE public.predictions_staging DISABLE ROW LEVEL SECURITY;
