-- ROLLBACK fyrir 20260807082414_cc105_2a_rls_snapshot_toflur.sql
-- SKRIFAÃ FYRIR APPLY (cc105 FASI 2a, 2026-08-07T08:23:37Z).
--
-- MÃ†LD BYRJUNARSTAÃA (pg_class, rÃ©tt fyrir apply â€” Ã¾etta er Ã¡standiÃ°
-- sem Ã¾essi skrÃ¡ skilar kerfinu Ã­):
--   scraper.listing_extractions_pre_cc94b    relrowsecurity=false  relacl={postgres=arwdDxtm/postgres}  eigandi=postgres
--   scraper.listing_extractions_pre_cc94b2   relrowsecurity=false  relacl={postgres=arwdDxtm/postgres}  eigandi=postgres
--   scraper.listing_valuations_pre_cc94b2    relrowsecurity=false  relacl={postgres=arwdDxtm/postgres}  eigandi=postgres
--
-- ATH 1: anon/authenticated hÃ¶fÃ°u ENGIN rÃ©ttindi Ã¡ Ã¾essum Ã¾remur tÃ¶flum fyrir apply
--        (relacl ber aÃ°eins postgres). REVOKE-liÃ°urinn Ã­ migrationinni er Ã¾vÃ­
--        BELTI, ekki breyting â€” og hann Ã¾arf EKKERT viÃ°snÃºnings-GRANT hÃ©r.
--        Ef GRANT vÃ¦ri sett hÃ©r til baka vÃ¦ri Ã¾aÃ° RÃ‰TTINDAAUKNING, ekki rollback.
--
-- ATH 2: public.spatial_ref_sys er EKKI snert af migrationinni (sjÃ¡ bÃ³kun Ã­
--        migration-skrÃ¡nni) og Ã¡ sÃ©r Ã¾vÃ­ engan liÃ° hÃ©r.

-- 1) Skila RLS-fÃ¡nanum Ã­ mÃ¦lda byrjunarstÃ¶Ã°u (false) Ã¡ Ã¶llum Ã¾remur.
ALTER TABLE scraper.listing_extractions_pre_cc94b   DISABLE ROW LEVEL SECURITY;
ALTER TABLE scraper.listing_extractions_pre_cc94b2  DISABLE ROW LEVEL SECURITY;
ALTER TABLE scraper.listing_valuations_pre_cc94b2   DISABLE ROW LEVEL SECURITY;

-- 2) SannprÃ³fun eftir rollback â€” Ã¡ aÃ° skila false/false/false og
--    relacl={postgres=arwdDxtm/postgres} Ã¡ Ã¶llum Ã¾remur.
-- select n.nspname||'.'||c.relname, c.relrowsecurity, c.relacl::text
--   from pg_class c join pg_namespace n on n.oid=c.relnamespace
--  where n.nspname='scraper'
--    and c.relname in ('listing_extractions_pre_cc94b',
--                      'listing_extractions_pre_cc94b2',
--                      'listing_valuations_pre_cc94b2');
