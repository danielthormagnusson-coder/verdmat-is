-- cc381b — ROLLBACK byggárslagfæringar. Skilar byggar OG is_new_build nákvæmlega eins og fyrir (0 þar sem 0, NULL þar sem NULL),
-- þrengir t5_astaeda-CHECK aftur í sex lykla og fellir afritið.
-- RÖÐ: flipp-rollback (cc381b_flip_rollback.sql) FYRST; meðan einhver röð ber 'byggar_vantar' stöðvar hliðið hér.
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '120s';

DO $$ BEGIN
  IF to_regclass('public.properties_byggar_pre_cc381b') IS NULL THEN
    RAISE EXCEPTION 'HALT: afritið public.properties_byggar_pre_cc381b er ekki til';
  END IF;
  IF EXISTS (SELECT 1 FROM public.valuation_tiers WHERE t5_astaeda = 'byggar_vantar') THEN
    RAISE EXCEPTION 'HALT: valuation_tiers ber enn byggar_vantar — keyrðu flipp-rollback cc381b fyrst';
  END IF;
END $$;

UPDATE public.properties p
   SET byggar = b.byggar, is_new_build = b.is_new_build
  FROM public.properties_byggar_pre_cc381b b
 WHERE p.fastnum = b.fastnum;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.properties p JOIN public.properties_byggar_pre_cc381b b USING (fastnum)
   WHERE p.byggar IS DISTINCT FROM b.byggar OR p.is_new_build IS DISTINCT FROM b.is_new_build;
  IF n <> 0 THEN RAISE EXCEPTION 'HALT: % raðir víkja frá afriti', n; END IF;
END $$;

DROP TABLE public.properties_byggar_pre_cc381b;

ALTER TABLE public.valuation_tiers DROP CONSTRAINT valuation_tiers_t5_astaeda_check;
ALTER TABLE public.valuation_tiers ADD CONSTRAINT valuation_tiers_t5_astaeda_check
  CHECK (t5_astaeda = ANY (ARRAY['staerd_othekkt'::text, 'landbunadur_sumarhus'::text, 'utihus'::text, 'staerd_utan'::text,
                                 'gogn_vantar'::text, 'thunnt_svaedi'::text]));
