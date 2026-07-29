-- cc52 — VIÐSNÚNINGUR á 20260729075021_cc52_revoke_anon_write_grants.sql
-- Endurheimtir NÁKVÆMLEGA þau grants sem mæld voru FYRIR læsingu
-- (heimild: information_schema.role_table_grants, 2026-07-29T07:03Z).
-- Engin RLS-staða var snert í migrationinu, svo hér er engin "DISABLE ROW LEVEL SECURITY".
--
-- ATH: liðir 1–2 eru teknir með til fullnustu en verða líka NÚLL-AÐGERÐ af sömu ástæðu
-- og í migrationinu (supabase_admin á hlutina, postgres hefur ekki GRANT OPTION).
-- Þeir eru skaðlausir: heimildirnar sem þeir "endurheimta" hurfu aldrei.

BEGIN;

-- 1) spatial_ref_sys  (fyrir: DELETE,INSERT,REFERENCES,SELECT,TRIGGER,TRUNCATE,UPDATE)
GRANT ALL ON public.spatial_ref_sys TO anon, authenticated;

-- 2) PostGIS-yfirlitssýnir (fyrir: DELETE,INSERT,REFERENCES,SELECT,TRIGGER,TRUNCATE,UPDATE)
GRANT ALL ON public.geometry_columns  TO anon, authenticated;
GRANT ALL ON public.geography_columns TO anon, authenticated;

-- 3) Vinnslutöflur (fyrir: DELETE,INSERT,REFERENCES,SELECT,TRIGGER,TRUNCATE,UPDATE)
GRANT ALL ON public.feature_attributions_rent         TO anon, authenticated;
GRANT ALL ON public.feature_attributions_rent_staging TO anon, authenticated;
GRANT ALL ON public.predictions_rent_pre_cc30         TO anon, authenticated;

-- 4) Sýnir (fyrir: DELETE,INSERT,REFERENCES,SELECT,TRIGGER,TRUNCATE,UPDATE)
GRANT ALL ON public.v_properties          TO anon, authenticated;
GRANT ALL ON public.v_current_predictions TO anon, authenticated;
GRANT ALL ON public.v_repeat_sale_index   TO anon, authenticated;
GRANT ALL ON public.v_ats_lookup_by_heat  TO anon, authenticated;

-- 5) property_attributes / property_images (fyrir: REFERENCES,SELECT,TRIGGER,TRUNCATE)
--    Dálkastigs-INSERT authenticated á property_attributes var ekki snert og
--    þarf enga endurheimt.
GRANT REFERENCES, TRIGGER, TRUNCATE ON public.property_attributes TO anon, authenticated;
GRANT REFERENCES, TRIGGER, TRUNCATE ON public.property_images     TO anon, authenticated;

COMMIT;
