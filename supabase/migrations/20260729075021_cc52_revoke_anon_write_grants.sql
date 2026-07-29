-- cc52 — ÖRYGGISATVIK RLS_DISABLED_IN_PUBLIC: læsing á rithemildum anon/authenticated.
-- Applýjað 2026-07-29T07:50:21Z gegnum Supabase MCP. Viðsnúningur:
--   supabase/rollback/20260729075021_cc52_revoke_anon_write_grants_rollback.sql
--
-- ENGIN "ENABLE ROW LEVEL SECURITY" á spatial_ref_sys: hún er í eigu supabase_admin og
-- PostGIS-föll (ST_Transform o.fl.) lesa hana sem KALLANDI notandi — RLS þar felldi
-- geo-fyrirspurnir fyrir anon. Flaggið rls_disabled_in_public stendur áfram sem
-- known-accepted (sbr. CLAUDE.md); þessi migration lokar SKRIFLEIÐINNI, ekki flagginu.
--
-- ⚠️  BÓKUN — LIÐIR 1 OG 2 URÐU ÞEGJANDI NÚLL-AÐGERÐ.
-- spatial_ref_sys, geometry_columns og geography_columns eru í eigu `supabase_admin`.
-- Migration keyrir sem `postgres`, sem er EKKI meðlimur í supabase_admin og hefur ekki
-- GRANT OPTION (mælt: pg_has_role=false, has_table_privilege(...,'SELECT WITH GRANT
-- OPTION')=false). PostgreSQL gefur þá WARNING — EKKI villu — svo migration skilaði
-- `success` án þess að breyta neinu. Staðfest eftir á með aclexplode: heimildirnar
-- standa óbreyttar, og anon-REST skilar enn 23505 á dup-INSERT (= skrifheimild veitt).
-- Leið gegnum supabase_privileged_role var einnig reynd og mistókst eins.
-- ÚRLAUSN: krefst supabase_admin -> Supabase support-beiðni. Sjá lotuskýrslu cc52.
-- Liðir 3–5 GENGU EFTIR og eru mældir (200 -> 401 á rent-borðunum þremur).

-- 1) [NÚLL-AÐGERÐ, sjá bókun] spatial_ref_sys: anon/authenticated hafa DELETE/INSERT/
--    UPDATE/TRUNCATE. SELECT á að halda.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON public.spatial_ref_sys FROM anon, authenticated;

-- 2) [NÚLL-AÐGERÐ, sjá bókun] PostGIS-yfirlitssýnir.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON public.geometry_columns  FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON public.geography_columns FROM anon, authenticated;

-- 3) [TÓKST] Vinnslutöflur sem RLS varði nú þegar (lag 2 hélt, lag 1 vantaði).
--    Ekkert anon-kall les þær. Service-role heldur öllu.
REVOKE ALL ON public.feature_attributions_rent          FROM anon, authenticated;
REVOKE ALL ON public.feature_attributions_rent_staging  FROM anon, authenticated;
REVOKE ALL ON public.predictions_rent_pre_cc30          FROM anon, authenticated;

-- 4) [TÓKST] Sýnir með full DML-grants; aðeins SELECT er ætlað.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON public.v_properties          FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON public.v_current_predictions FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON public.v_repeat_sale_index   FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON public.v_ats_lookup_by_heat  FROM anon, authenticated;

-- 5) [TÓKST] TRUNCATE fer FRAMHJÁ RLS. Þessar tvær eru app-lesnar (SELECT óbreyttur),
--    en TRUNCATE-heimildin var hrein mistök. Dálkastigs-INSERT authenticated á
--    property_attributes (6 dálkar, skra_eigind-leiðin) er EKKI snert.
REVOKE TRUNCATE, REFERENCES, TRIGGER
  ON public.property_attributes FROM anon, authenticated;
REVOKE TRUNCATE, REFERENCES, TRIGGER
  ON public.property_images     FROM anon, authenticated;
