-- cc381d (v2 af cc381b) — byggár lagað í gagnalaginu: AÐEINS properties.byggar. EKKI BEITT.
-- Svör Danna 25.11: (2) innsláttarvillurnar 4 (201, 201, 208, 1224) lagaðar með HMS-ári þar sem til er, annars NULL;
--                   (3) is_new_build ÓSNERT (ákv. 6 afturkölluð; mæling cc381c).
-- Beiting: beita_migration_cc381d.py --hluti byggar --beita --go-danna (master eftir GO). Ein færsla, aðeins UPDATE (raðlásar
-- á properties, ROW EXCLUSIVE) og ný afritstafla. ENGIN DDL á lifandi töflu í þessari færslu. CHECK-víkkunin er sér færsla
-- (mig_20261125210100_cc381d_t5_check.sql).
-- Regla: byggar NULL, < 1700 (þ.m.t. 0) eða > líðandi ár + 2 -> byggingarár AÐALEININGAR í properties.matseiningar,
--   valin eins og phase_d3_extract.pick_primary_matseining ('Aðaleining' -> stærsta einflm > 0 -> fyrsta eining),
--   aðeins fjögurra stafa ár innan [1700, ár + 2]; annars NULL (0 er sentinel, ekki HMS-gildi).
-- Mæling 25.11 (s10_vaent.py, gögn 20:28 UTC = 16:15): 20.536 raðir = 20.410 fylltar + 126 -> NULL; is_new_build 0 breytingar.
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '120s';

DO $$ BEGIN
  IF to_regclass('public.properties_byggar_pre_cc381d') IS NOT NULL THEN
    RAISE EXCEPTION 'HALT: public.properties_byggar_pre_cc381d er þegar til';
  END IF;
  IF to_regclass('public.properties_byggar_pre_cc381b') IS NOT NULL THEN
    RAISE EXCEPTION 'HALT: drög cc381b (v1) virðast beitt — public.properties_byggar_pre_cc381b er til';
  END IF;
END $$;

CREATE TEMP TABLE cc381d_byggar ON COMMIT DROP AS
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
  SELECT p.fastnum, p.byggar AS byggar_gamalt,
         CASE WHEN pr.ar_txt ~ '^\d{4}$'
               AND pr.ar_txt::int BETWEEN 1700 AND extract(year FROM current_date)::int + 2
              THEN pr.ar_txt::numeric END AS byggar_nytt
    FROM public.properties p
    LEFT JOIN prim pr USING (fastnum)
   WHERE p.byggar IS NULL OR p.byggar < 1700 OR p.byggar > extract(year FROM current_date)::int + 2
)
SELECT fastnum, byggar_gamalt, byggar_nytt FROM v
 WHERE NOT (byggar_gamalt IS NULL AND byggar_nytt IS NULL);

-- Hlið: fjöldi innan 2 % frá mælingu 25.11 (20.536); NULL-raðir innan marka.
DO $$ DECLARE n int; n0 int; BEGIN
  SELECT count(*), count(*) FILTER (WHERE byggar_nytt IS NULL) INTO n, n0 FROM cc381d_byggar;
  IF n < 20125 OR n > 20947 THEN RAISE EXCEPTION 'HALT: % raðir, vænt ~20.536', n; END IF;
  IF n0 > 200 THEN RAISE EXCEPTION 'HALT: % -> NULL, vænt ~126', n0; END IF;
END $$;

CREATE TABLE public.properties_byggar_pre_cc381d AS
SELECT fastnum, byggar_gamalt AS byggar, byggar_nytt, now() AS afritad_at FROM cc381d_byggar;
ALTER TABLE public.properties_byggar_pre_cc381d ADD PRIMARY KEY (fastnum);
ALTER TABLE public.properties_byggar_pre_cc381d ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.properties_byggar_pre_cc381d FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.properties_byggar_pre_cc381d TO service_role;
COMMENT ON TABLE public.properties_byggar_pre_cc381d IS
  'cc381d: fyrra byggar fyrir byggárslagfæringu (is_new_build ósnert); rollback = rb_20261125210000_cc381d_byggar_rollback.sql; geymt 30 daga.';

UPDATE public.properties p
   SET byggar = f.byggar_nytt
  FROM cc381d_byggar f
 WHERE p.fastnum = f.fastnum;

-- Eftirhlið: allar raðir bera nýja gildið; hlið (4) heldur á allri töflunni.
DO $$ DECLARE n int; z int; BEGIN
  SELECT count(*) INTO n FROM public.properties p JOIN public.properties_byggar_pre_cc381d b USING (fastnum)
   WHERE p.byggar IS DISTINCT FROM b.byggar_nytt;
  IF n <> 0 THEN RAISE EXCEPTION 'HALT: % raðir bera ekki nýja gildið', n; END IF;
  SELECT count(*) INTO z FROM public.properties
   WHERE byggar IS NOT NULL AND (byggar < 1700 OR byggar > extract(year FROM current_date)::int + 2);
  IF z <> 0 THEN RAISE EXCEPTION 'HALT: % raðir brjóta hlið (4)', z; END IF;
END $$;
