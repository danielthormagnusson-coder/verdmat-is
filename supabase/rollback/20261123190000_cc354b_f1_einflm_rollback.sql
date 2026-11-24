-- cc354b — ROLLBACK reglu F-v1 á public.properties.einflm. Skilar einflm nákvæmlega eins og fyrir (NULL þar sem NULL), fellir afritið.
-- Þrep/comps fara til baka með cc354b_flip.py --afturkalla (sér skref); properties_v2.pkl úr D:\properties_v2_pre_cc354b.pkl.
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '120s';

DO $$ BEGIN
  IF to_regclass('public.properties_einflm_pre_cc354b') IS NULL THEN
    RAISE EXCEPTION 'HALT: afritið public.properties_einflm_pre_cc354b er ekki til';
  END IF;
END $$;

UPDATE public.properties p
   SET einflm = b.einflm
  FROM public.properties_einflm_pre_cc354b b
 WHERE p.fastnum = b.fastnum;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.properties p JOIN public.properties_einflm_pre_cc354b b USING (fastnum)
   WHERE p.einflm IS DISTINCT FROM b.einflm;
  IF n <> 0 THEN RAISE EXCEPTION 'HALT: % raðir víkja frá afriti', n; END IF;
END $$;

DROP TABLE public.properties_einflm_pre_cc354b;
