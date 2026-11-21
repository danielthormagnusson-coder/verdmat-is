-- cc364: lind fyrir leit/síun á öllu framboði — efnisgerð sýn (MV) yfir opin söluferli, úr SAMA kjarna og /eign (scraper.soluferli, cc362).
--
-- Hvers vegna: public.soluferli_opin(bigint[]) tekur um 8 ms á eign (75 s fyrir 8.554). Það dugar fyrir /eign (1 eign) og vöktun
-- (næturverk), en ekki fyrir síun/talningu á öllu framboði í rauntíma (/leit „Nýtt í vikunni", samantekt, svæðissíður).
-- Valið (SKIL_CC364 §B1): MV með einkvæmum vísi, endurnýjuð CONCURRENTLY eftir sópun (verdmat-daily-lifecycle-sweep).
--   * MV geymir aðeins upphaf og vissu; dagafjöldi er reiknaður við lestur (sama formúla og scraper.soluferli), svo talan
--     eldist ekki um sólarhring milli endurnýjana.
--   * REFRESH ... CONCURRENTLY tekur EXCLUSIVE-lás á MV eina (lesendur stöðvast ekki) og ACCESS SHARE á grunntöflur.
--   * Engin breyting á töflum sem www skrifar eða les; engin dálkur á scraper.listings (sjá §B1 um hafnaða kosti).
-- Aðgangur: MV í scraper; SELECT tekið af PUBLIC/anon/authenticated (MV ber ekki RLS — réttindin eru vörnin), veitt service_role.
-- Lesfall public.soluferli_opin_mv(bigint[]) skilar sömu dálkum og public.soluferli_opin + reiknad_at; EXECUTE aðeins service_role.
-- MV er búin til WITH NO DATA: fyrsta fylling er sér skref í beitingu (REFRESH án CONCURRENTLY, ~75 s, enginn les MV þá).
-- BEGIN/COMMIT eru ekki hér: beitingarskriftan stýrir færslunni (lock_timeout 5s).

CREATE MATERIALIZED VIEW scraper.soluferli_opin_mv AS
  SELECT DISTINCT ON (s.fastnum)
         s.fastnum, s.upphaf, s.upphaf_viss, s.lok_viss, s.n_auglysingar, s.fasteignasolur, s.fyrsta_verd, s.sidasta_verd,
         now() AS reiknad_at
    FROM scraper.soluferli(ARRAY(SELECT DISTINCT v.fastnum FROM scraper.v_eign_virk_auglysing v
                                  WHERE v.tenure = 'sale' AND v.fastnum IS NOT NULL ORDER BY 1)) s
   WHERE s.opid
   ORDER BY s.fastnum, s.upphaf DESC
  WITH NO DATA;

CREATE UNIQUE INDEX soluferli_opin_mv_fastnum ON scraper.soluferli_opin_mv (fastnum);
CREATE INDEX soluferli_opin_mv_upphaf ON scraper.soluferli_opin_mv (upphaf);

REVOKE ALL ON scraper.soluferli_opin_mv FROM PUBLIC, anon, authenticated;
GRANT SELECT ON scraper.soluferli_opin_mv TO service_role;

COMMENT ON MATERIALIZED VIEW scraper.soluferli_opin_mv IS
  'cc364: opið söluferli per fastnúmer (nýjasta upphaf), úr scraper.soluferli. Endurnýjuð CONCURRENTLY eftir sópun '
  '(scripts/endurnyja_soluferli_opin.py). Dagar reiknast við lestur (public.soluferli_opin_mv).';

-- Lesfall: sömu dálkar og public.soluferli_opin (cc362) + reiknad_at. Dagaformúla = scraper.soluferli (ein formúla).
CREATE FUNCTION public.soluferli_opin_mv(p_fastnums bigint[] DEFAULT NULL)
 RETURNS TABLE(fastnum bigint, upphaf timestamptz, dagar integer, dagar_minnst integer, upphaf_viss boolean, n_auglysingar integer,
               fasteignasolur text[], fyrsta_verd bigint, sidasta_verd bigint, reiknad_at timestamptz)
 LANGUAGE sql STABLE SECURITY DEFINER
 SET search_path TO 'scraper', 'public', 'pg_temp'
AS $function$
  SELECT m.fastnum, m.upphaf,
         CASE WHEN m.upphaf_viss AND m.lok_viss THEN (extract(epoch FROM (now() - m.upphaf)) / 86400)::integer END AS dagar,
         (extract(epoch FROM (now() - m.upphaf)) / 86400)::integer AS dagar_minnst,
         m.upphaf_viss, m.n_auglysingar, m.fasteignasolur, m.fyrsta_verd, m.sidasta_verd, m.reiknad_at
    FROM scraper.soluferli_opin_mv m
   WHERE p_fastnums IS NULL OR m.fastnum = ANY (p_fastnums)
$function$;

REVOKE ALL ON FUNCTION public.soluferli_opin_mv(bigint[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.soluferli_opin_mv(bigint[]) TO service_role;

NOTIFY pgrst, 'reload schema';
