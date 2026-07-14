-- ROLLBACK fyrir 20260714214317_cc9_rls_fix_snapshot_staging
-- Enduropnar snapshot-/staging-töflurnar í fyrra (berskjaldaða) horf.
-- Aðeins ef lagfæringin brýtur eitthvað óvænt — báðar töflur eru
-- rollback-/vinnutöflur sem ekkert app les, svo þess ætti ekki að þurfa.
ALTER TABLE public.postheiti_snapshot_pre_d3fix_20260706 DISABLE ROW LEVEL SECURITY;
GRANT ALL ON public.postheiti_snapshot_pre_d3fix_20260706 TO anon, authenticated;
ALTER TABLE public.predictions_staging DISABLE ROW LEVEL SECURITY;
