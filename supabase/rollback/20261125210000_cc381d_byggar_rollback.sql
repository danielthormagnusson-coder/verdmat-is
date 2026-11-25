-- cc381d — ROLLBACK byggárslagfæringar (aðeins properties.byggar; is_new_build var aldrei snert).
-- Skilar byggar nákvæmlega eins og fyrir (0 þar sem 0, NULL þar sem NULL) og fellir afritið. Engin DDL á lifandi töflu.
-- RÖÐ: flipp-rollback (cc381d_flip_rollback.sql) og CHECK-rollback (rb_20261125210100_...) á undan, ef þau voru beitt.
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '120s';

DO $$ BEGIN
  IF to_regclass('public.properties_byggar_pre_cc381d') IS NULL THEN
    RAISE EXCEPTION 'HALT: afritið public.properties_byggar_pre_cc381d er ekki til';
  END IF;
END $$;

UPDATE public.properties p
   SET byggar = b.byggar
  FROM public.properties_byggar_pre_cc381d b
 WHERE p.fastnum = b.fastnum;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.properties p JOIN public.properties_byggar_pre_cc381d b USING (fastnum)
   WHERE p.byggar IS DISTINCT FROM b.byggar;
  IF n <> 0 THEN RAISE EXCEPTION 'HALT: % raðir víkja frá afriti', n; END IF;
END $$;

DROP TABLE public.properties_byggar_pre_cc381d;
