-- cc354b — regla F-v1 á public.properties.einflm (DECISIONS 2026-11-20 a/b; byggt á drögum cc354, afrituðum í þessa möppu).
-- EKKI BEITT. Beiting: beita_migration_cc354b.py --beita, aðeins master eftir GO Danna, utan 00:45–07:30 UTC.
-- Regla: einflm = Σ einflm matseininga HMS með notkun_kodi >= 300 (land/hlunnindi < 300 aldrei; fasteignamat aldrei, regla 8).
--   Ákvörðun a: stærð utan 20–1000 m² HELST eins og F-v1 gefur hana (T5 + stöðumerki fer í þrepin, ekki hingað).
--   NULL aðeins við óþekkta stærð: eign án matseininga/summu 0 er ósnert (regla 10).
--   Ákvörðun b (3.202 íbúðareignir með útihús → stöðumerki í stað tölu) er í þrepunum, ekki hér; einflm fylgir venju HMS.
-- Mæling 23.11 (u02_fv1.txt): 5.592 raðir breytast (3.642 íbúðarflokkar), sama tala og cc354 20.11.
-- Engin DDL á properties: aðeins UPDATE á ~5.600 röðum (raðlásar; SELECT www lokast ekki). Afritstafla ný, lokuð í sömu færslu.
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '120s';

DO $$ BEGIN
  IF to_regclass('public.properties_einflm_pre_cc354b') IS NOT NULL THEN
    RAISE EXCEPTION 'HALT: public.properties_einflm_pre_cc354b er þegar til';
  END IF;
END $$;

CREATE TEMP TABLE cc354b_f1 ON COMMIT DROP AS
SELECT p.fastnum,
       p.einflm AS einflm_gamalt,
       (SELECT round(sum((m->>'einflm')::numeric), 2)
          FROM jsonb_array_elements(CASE WHEN jsonb_typeof(p.matseiningar) = 'array' THEN p.matseiningar ELSE '[]'::jsonb END) m
         WHERE (m->>'notkun_kodi') ~ '^\d+$' AND (m->>'notkun_kodi')::int >= 300
           AND (m->>'einflm') ~ '^-?\d+(\.\d+)?$') AS einflm_nytt
FROM public.properties p;

DELETE FROM cc354b_f1 WHERE einflm_nytt IS NULL OR einflm_nytt <= 0;
DELETE FROM cc354b_f1 WHERE einflm_gamalt IS NOT NULL AND einflm_gamalt > 0 AND abs(einflm_gamalt - einflm_nytt) <= 0.5;

-- Hlið: fjöldi innan 2 prósenta frá mælingu 23.11 (5.592).
DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM cc354b_f1;
  IF n < 5480 OR n > 5704 THEN RAISE EXCEPTION 'HALT: % raðir, vænt ~5.592', n; END IF;
END $$;

CREATE TABLE public.properties_einflm_pre_cc354b AS
SELECT fastnum, einflm_gamalt AS einflm, einflm_nytt, now() AS afritad_at FROM cc354b_f1;
ALTER TABLE public.properties_einflm_pre_cc354b ADD PRIMARY KEY (fastnum);
ALTER TABLE public.properties_einflm_pre_cc354b ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.properties_einflm_pre_cc354b FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.properties_einflm_pre_cc354b TO service_role;

UPDATE public.properties p
   SET einflm = f.einflm_nytt
  FROM cc354b_f1 f
 WHERE p.fastnum = f.fastnum;

DO $$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM public.properties p JOIN public.properties_einflm_pre_cc354b b USING (fastnum)
   WHERE p.einflm IS DISTINCT FROM b.einflm_nytt;
  IF n <> 0 THEN RAISE EXCEPTION 'HALT: % raðir bera ekki nýja gildið', n; END IF;
END $$;
