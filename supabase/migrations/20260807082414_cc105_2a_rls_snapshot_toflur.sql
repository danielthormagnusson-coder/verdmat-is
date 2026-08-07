-- cc105 FASI 2a — RLS á cc94-viðgerðarsnapshottöflurnar þrjár.
-- Applýjað 2026-08-07T08:24:14Z gegnum Supabase MCP apply_migration.
-- schema_migrations version: 20260807082414
-- Viðsnúningur: supabase/rollback/20260807082414_cc105_2a_rls_snapshot_toflur_rollback.sql
--               (skrifaður FYRIR apply, sbr. verklagsreglu)
--
-- Fæðingarreglan (CLAUDE.md): hver tafla í PostgREST-útsettu skema fær RLS +
-- þröng réttindi í SÖMU migration og CREATE. Þessar þrjár urðu til í viðgerð
-- cc94 (06.08) og sluppu framhjá reglunni.
--
-- MÆLT FYRIR APPLY: relacl={postgres=arwdDxtm/postgres} á öllum þremur — anon og
-- authenticated höfðu ENGIN réttindi. REVOKE-liðurinn er því BELTI (0 breyting),
-- ENABLE RLS er raunbreytingin. Raunmælt fyrir apply: anon-REST skilaði þegar 401
-- á allar þrjár. Þetta lokar því LATENTU leiðinni (ef einhver grantar seinna),
-- ekki opinni leið í dag.
--
-- ⚠️ spatial_ref_sys ER EKKI Í ÞESSARI MIGRATION — sjá bókun í HALT-skilum cc105
--    FASA 2a. Stutt: taflan er í eigu supabase_admin; `ENABLE ROW LEVEL SECURITY`
--    sem postgres fellur á `42501: must be owner of table spatial_ref_sys`
--    (raunreynt 07.08). Varaleiðin REVOKE var EKKI keyrð: postgres hefur ekki
--    GRANT OPTION (mælt false) svo REVOKE er ÞÖGUL NÚLL-AÐGERÐ sem skilar
--    `success` (sama gildra og cc52 féll í), og PUBLIC heldur auk þess `=r`
--    svo REVOKE á anon/authenticated lokaði engu. Flaggið stendur
--    known-accepted skv. cc72-bókun í CLAUDE.md.

ALTER TABLE scraper.listing_extractions_pre_cc94b   ENABLE ROW LEVEL SECURITY;

ALTER TABLE scraper.listing_extractions_pre_cc94b2  ENABLE ROW LEVEL SECURITY;

ALTER TABLE scraper.listing_valuations_pre_cc94b2   ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON scraper.listing_extractions_pre_cc94b   FROM anon, authenticated;

REVOKE ALL ON scraper.listing_extractions_pre_cc94b2  FROM anon, authenticated;

REVOKE ALL ON scraper.listing_valuations_pre_cc94b2   FROM anon, authenticated;

-- MÆLT EFTIR APPLY (pg_class): relrowsecurity=true, 0 stefnur (default deny),
-- relacl óbreytt {postgres=arwdDxtm/postgres}, relforcerowsecurity=false svo
-- eigandinn (postgres — migrations og ops-leiðin) les áfram: 163 / 2 / 4 raðir.
