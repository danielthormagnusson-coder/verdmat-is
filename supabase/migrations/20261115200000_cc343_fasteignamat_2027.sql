-- cc343 (flokkur B, undirbúningur 15.11 — BEITING BÍÐUR GO DANNA):
-- Þjónninn (service_role) les fasteignamat 2027 og lóðarmat 2027 úr semantic.fasteignamat_argerd
-- (cc288, heimild hms_safn.fasteignamat_naesta_ar, þúsundir kr). AÐEINS árgerð 2027, AÐEINS
-- service_role: engin anon/authenticated/PUBLIC heimild. 2026-lóðarmat fer ekki inn (lhlmat_thkr
-- 2026 í töflunni er hlutfall, ekki krónur). Grunntaflan er óbreytt (RLS á, postgres eitt með heimild).
CREATE VIEW semantic.v_fasteignamat_2027 AS
  SELECT fastnum, mat_thkr, lhlmat_thkr AS lodarmat_thkr
    FROM semantic.fasteignamat_argerd
   WHERE argerd = 2027;
COMMENT ON VIEW semantic.v_fasteignamat_2027 IS
  'cc343: fasteignamat og lóðarmat árgerðar 2027 (þús. kr) fyrir HMS-spjald á /eign. Aðeins service_role.';
REVOKE ALL ON semantic.v_fasteignamat_2027 FROM PUBLIC, anon, authenticated;
GRANT SELECT ON semantic.v_fasteignamat_2027 TO service_role;
NOTIFY pgrst, 'reload schema';
