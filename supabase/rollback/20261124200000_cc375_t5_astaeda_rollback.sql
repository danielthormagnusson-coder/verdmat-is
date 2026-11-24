-- cc375 — ROLLBACK valuation_tiers.t5_astaeda: fellir bæði CHECK og dálkinn. Aðrir dálkar ósnertir.
-- ATH röð: ef flipp cc354b á að fara til baka (cc354b_flip_rollback.sql: INSERT ... SELECT * FROM valuation_tiers_pre_cc354b)
-- verður ÞESSI rollback að fara á undan — afritið ber ekki dálkinn og T5-raðir brytu valuation_tiers_t5_astaeda_tier_check.
-- Keðjan (build_comps_v2 >= v2_4 / load_comps_v2 cc375) krefst dálksins: eftir þennan rollback þarf precompute fyrir cc375.
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='valuation_tiers'
                  AND column_name='t5_astaeda') THEN
    RAISE EXCEPTION 'HALT: valuation_tiers.t5_astaeda er ekki til';
  END IF;
END $$;

ALTER TABLE public.valuation_tiers DROP CONSTRAINT valuation_tiers_t5_astaeda_tier_check;
ALTER TABLE public.valuation_tiers DROP CONSTRAINT valuation_tiers_t5_astaeda_check;
ALTER TABLE public.valuation_tiers DROP COLUMN t5_astaeda;
