-- cc381d — t5_astaeda-CHECK víkkuð um 'byggar_vantar' (ákv. 3; Danni 25.11 lið 4: keðjan skrifar lykilinn strax). EKKI BEITT.
-- Tvær færslur (beita_migration_cc381d.py --hluti check skiptir við línuna @@NY_FAERSLA@@):
--   1) DROP + ADD ... NOT VALID: ACCESS EXCLUSIVE á valuation_tiers aðeins meðan tvær katalogbreytingar keyra (engin skönnun);
--   2) VALIDATE CONSTRAINT: SHARE UPDATE EXCLUSIVE (lokar hvorki SELECT www né skrifum), skannar 167.503 raðir.
-- Víkkun: allar núverandi raðir uppfylla nýja skilyrðið (yfirmengi hins gamla).
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
ALTER TABLE public.valuation_tiers DROP CONSTRAINT valuation_tiers_t5_astaeda_check;
ALTER TABLE public.valuation_tiers ADD CONSTRAINT valuation_tiers_t5_astaeda_check
  CHECK (t5_astaeda = ANY (ARRAY['staerd_othekkt'::text, 'landbunadur_sumarhus'::text, 'utihus'::text, 'staerd_utan'::text,
                                 'gogn_vantar'::text, 'thunnt_svaedi'::text, 'byggar_vantar'::text])) NOT VALID;
-- @@NY_FAERSLA@@
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '120s';
ALTER TABLE public.valuation_tiers VALIDATE CONSTRAINT valuation_tiers_t5_astaeda_check;
