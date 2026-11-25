-- cc381d — ROLLBACK CHECK-víkkunar: þrengir t5_astaeda aftur í sex lykla (tvær færslur eins og víkkunin).
-- RÖÐ: flipp-rollback FYRST; meðan einhver röð ber 'byggar_vantar' stöðvar hliðið hér.
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM public.valuation_tiers WHERE t5_astaeda = 'byggar_vantar') THEN
    RAISE EXCEPTION 'HALT: valuation_tiers ber enn byggar_vantar — keyrðu flipp-rollback cc381d fyrst';
  END IF;
END $$;
ALTER TABLE public.valuation_tiers DROP CONSTRAINT valuation_tiers_t5_astaeda_check;
ALTER TABLE public.valuation_tiers ADD CONSTRAINT valuation_tiers_t5_astaeda_check
  CHECK (t5_astaeda = ANY (ARRAY['staerd_othekkt'::text, 'landbunadur_sumarhus'::text, 'utihus'::text, 'staerd_utan'::text,
                                 'gogn_vantar'::text, 'thunnt_svaedi'::text])) NOT VALID;
-- @@NY_FAERSLA@@
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '120s';
ALTER TABLE public.valuation_tiers VALIDATE CONSTRAINT valuation_tiers_t5_astaeda_check;
