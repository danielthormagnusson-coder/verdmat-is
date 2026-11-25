-- cc381b — byggár lagað í gagnalaginu (DECISIONS 2026-11-25, cc381 ákvarðanir 1, 2, 3, 4, 6). Byggt á drögum cc381.
-- EKKI BEITT. Beiting: beita_migration_cc381b.py --beita --go-danna, aðeins master eftir GO Danna, eftir sópun, fyrir 00:30 UTC.
-- Regla:
--   1) byggar NULL, <= 0 eða utan [1700, líðandi ár + 2] -> byggingarár AÐALEININGAR í properties.matseiningar (HMS),
--      valin eins og phase_d3_extract.pick_primary_matseining ('Aðaleining' -> stærsta einflm > 0 -> fyrsta eining),
--      aðeins fjögurra stafa ár innan [1700, ár + 2]; annars NULL (grunnregla 10; 0 er sentinel, ekki HMS-gildi).
--      „Utan bils“ nær líka til 4 innsláttarvillna (201, 201, 208, 1224), svo hlið (4) standist á lifandi gögnum.
--   2) is_new_build endurreiknað á SÖMU röðum (grunnregla 5 = rules.is_new_build): fullbuid = 0 -> true;
--      fullbuid = 1 og 0 <= ár - byggar <= 2 -> true; annars false (vantar = false). Aðrar raðir ósnertar.
--   3) valuation_tiers_t5_astaeda_check víkkuð um lykilinn 'byggar_vantar' (ákv. 3). Keðjan skrifar hann (sér skref: flipp).
-- Mæling 25.11 (s10_vaent.py, af diski, gögn ~16:15 UTC): 20.536 raðir = 20.410 fylltar + 126 -> NULL; is_new_build 2.222 false -> true.
-- Engin DDL á properties (aðeins UPDATE; raðlásar). DDL á valuation_tiers SÍÐAST (ACCESS EXCLUSIVE aðeins frá ALTER til COMMIT).
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '120s';

DO $$ BEGIN
  IF to_regclass('public.properties_byggar_pre_cc381b') IS NOT NULL THEN
    RAISE EXCEPTION 'HALT: public.properties_byggar_pre_cc381b er þegar til';
  END IF;
END $$;

CREATE TEMP TABLE cc381b_byggar ON COMMIT DROP AS
WITH m AS (
  SELECT p.fastnum, e.u, e.i,
         CASE WHEN (e.u->>'einflm') ~ '^-?\d+(\.\d+)?$' THEN (e.u->>'einflm')::numeric ELSE -1 END AS flm,
         lower(btrim(coalesce(e.u->>'merking', ''))) = 'aðaleining' AS adal
    FROM public.properties p
    CROSS JOIN LATERAL jsonb_array_elements(
         CASE jsonb_typeof(p.matseiningar) WHEN 'array' THEN p.matseiningar
                                           WHEN 'object' THEN jsonb_build_array(p.matseiningar)
                                           ELSE '[]'::jsonb END) WITH ORDINALITY e(u, i)
   WHERE p.byggar IS NULL OR p.byggar < 1700 OR p.byggar > extract(year FROM current_date)::int + 2
), mx AS (
  SELECT fastnum, max(flm) AS mflm FROM m GROUP BY fastnum
), prim AS (
  SELECT DISTINCT ON (m.fastnum) m.fastnum, btrim(coalesce(m.u->>'byggingarar', '')) AS ar_txt
    FROM m JOIN mx USING (fastnum)
   ORDER BY m.fastnum, m.adal DESC, CASE WHEN mx.mflm > 0 THEN m.flm END DESC NULLS LAST, m.i
), v AS (
  SELECT p.fastnum, p.byggar AS byggar_gamalt, p.is_new_build AS inb_gamalt, p.fullbuid,
         CASE WHEN pr.ar_txt ~ '^\d{4}$'
               AND pr.ar_txt::int BETWEEN 1700 AND extract(year FROM current_date)::int + 2
              THEN pr.ar_txt::numeric END AS byggar_nytt
    FROM public.properties p
    LEFT JOIN prim pr USING (fastnum)
   WHERE p.byggar IS NULL OR p.byggar < 1700 OR p.byggar > extract(year FROM current_date)::int + 2
)
SELECT fastnum, byggar_gamalt, byggar_nytt, inb_gamalt,
       coalesce(fullbuid = 0
                OR (fullbuid = 1 AND extract(year FROM current_date)::int - byggar_nytt BETWEEN 0 AND 2), false) AS inb_nytt
  FROM v
 WHERE NOT (byggar_gamalt IS NULL AND byggar_nytt IS NULL);

-- Hlið: fjöldi innan 2 % frá mælingu 25.11 (20.536); NULL-raðir og is_new_build-breytingar innan marka.
DO $$ DECLARE n int; n0 int; nb int; BEGIN
  SELECT count(*), count(*) FILTER (WHERE byggar_nytt IS NULL),
         count(*) FILTER (WHERE inb_nytt IS DISTINCT FROM inb_gamalt)
    INTO n, n0, nb FROM cc381b_byggar;
  IF n < 20125 OR n > 20947 THEN RAISE EXCEPTION 'HALT: % raðir, vænt ~20.536', n; END IF;
  IF n0 > 200 THEN RAISE EXCEPTION 'HALT: % -> NULL, vænt ~126', n0; END IF;
  IF nb > 2400 THEN RAISE EXCEPTION 'HALT: is_new_build breytist á %, vænt ~2.222', nb; END IF;
END $$;

CREATE TABLE public.properties_byggar_pre_cc381b AS
SELECT fastnum, byggar_gamalt AS byggar, inb_gamalt AS is_new_build, byggar_nytt, inb_nytt AS is_new_build_nytt,
       now() AS afritad_at
  FROM cc381b_byggar;
ALTER TABLE public.properties_byggar_pre_cc381b ADD PRIMARY KEY (fastnum);
ALTER TABLE public.properties_byggar_pre_cc381b ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.properties_byggar_pre_cc381b FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.properties_byggar_pre_cc381b TO service_role;
COMMENT ON TABLE public.properties_byggar_pre_cc381b IS
  'cc381b: fyrri byggar/is_new_build fyrir byggárslagfæringu; rollback = rb_20261125200000_cc381b_byggar_rollback.sql; geymt 30 daga.';

UPDATE public.properties p
   SET byggar = f.byggar_nytt, is_new_build = f.inb_nytt
  FROM cc381b_byggar f
 WHERE p.fastnum = f.fastnum;

-- Eftirhlið: allar raðir bera nýju gildin; hlið (4) heldur á allri töflunni.
DO $$ DECLARE n int; z int; BEGIN
  SELECT count(*) INTO n FROM public.properties p JOIN public.properties_byggar_pre_cc381b b USING (fastnum)
   WHERE p.byggar IS DISTINCT FROM b.byggar_nytt OR p.is_new_build IS DISTINCT FROM b.is_new_build_nytt;
  IF n <> 0 THEN RAISE EXCEPTION 'HALT: % raðir bera ekki nýju gildin', n; END IF;
  SELECT count(*) INTO z FROM public.properties
   WHERE byggar IS NOT NULL AND (byggar < 1700 OR byggar > extract(year FROM current_date)::int + 2);
  IF z <> 0 THEN RAISE EXCEPTION 'HALT: % raðir brjóta hlið (4)', z; END IF;
END $$;

-- Ákv. 3: nýr T5-lykill. Síðast í færslunni (ACCESS EXCLUSIVE á valuation_tiers aðeins hér til COMMIT).
ALTER TABLE public.valuation_tiers DROP CONSTRAINT valuation_tiers_t5_astaeda_check;
ALTER TABLE public.valuation_tiers ADD CONSTRAINT valuation_tiers_t5_astaeda_check
  CHECK (t5_astaeda = ANY (ARRAY['staerd_othekkt'::text, 'landbunadur_sumarhus'::text, 'utihus'::text, 'staerd_utan'::text,
                                 'gogn_vantar'::text, 'thunnt_svaedi'::text, 'byggar_vantar'::text]));
