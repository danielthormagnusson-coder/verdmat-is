-- cc365: leiðrétting á kjarna cc362 (scraper.soluferli). Sama undirskrift og skilagerð; aðeins ferla-númerunin (CTE n) breytist.
--
-- Gallinn: í cc362 skiptist ferli þegar þinglýst sala > 30 d á undan stofndegi auglýsingar var önnur en sú sem FYRRI auglýsing sá.
--   30 daga töfin veldur því að sala sem liggur á undan upphafi ferlis (endurbirting eftir sölu, sem 14 d reglan hafði þegar skilið
--   frá eldra ferli) sést fyrst í seinni auglýsingu sama ferlis og klýfur það aftur, með skörun (2049440: sala 10.09, ferli hefst
--   23.09, aftur klofið 26.10). Vöktun sagði þá „kemur á sölu" um eign sem var þegar á sölu.
-- Leiðréttingin: lota = 14 d reglan ein; innan lotu skiptir sala aðeins ef hún er þinglýst á eða eftir upphafi ferlisins sem stendur
--   (upphaf lotu eða stofndagur fyrri kandídats að skiptingu í sömu lotu). Annað óbreytt (N, M, 30 d, síur, dálkar).
-- public.soluferli_opin, public.solusaga og public.solusaga_til lesa fallið og breytast ekki. Engin tafla, engin gögn, enginn vísir.
-- BEGIN/COMMIT eru ekki hér: beitingarskriftan stýrir færslunni (lock_timeout 5s).

CREATE OR REPLACE FUNCTION scraper.soluferli(p_fastnums bigint[])
RETURNS TABLE (
  fastnum bigint, ferli_nr integer, upphaf timestamptz, lok timestamptz, opid boolean,
  dagar integer, dagar_minnst integer, upphaf_viss boolean, lok_viss boolean,
  n_auglysingar integer, fasteignasolur text[], fyrsta_verd bigint, sidasta_verd bigint, hlutaverd boolean,
  naesta_upphaf timestamptz
)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = scraper, public, pg_temp
AS $$
  WITH bil_mbl AS (
    SELECT 'mbl'::text AS heimild, l.source_listing_id AS augl_id, l.fastnum, l.first_seen_at AS fra,
           (l.status = 'active' AND fj.fyrsta IS NULL AND af.fyrsta IS NULL) AS opin,
           CASE WHEN l.status = 'active' AND fj.fyrsta IS NULL AND af.fyrsta IS NULL THEN NULL
                ELSE GREATEST(l.first_seen_at, coalesce(fj.fyrsta, l.withdrawn_at, GREATEST(l.last_seen_at, l.sidast_fundin_at, l.first_seen_at))) END AS til,
           CASE WHEN coalesce(ph.upph, l.price_amount) >= 3000000 THEN coalesce(ph.upph, l.price_amount) END AS verd_upph,  -- 0/beiðnisverð = ekkert verð
           CASE WHEN l.price_amount >= 3000000 THEN l.price_amount END AS verd_nu,
           GREATEST(l.first_seen_at, pc.sidast, ph.sidast) AS asett_dags,
           l.agency_name AS sala,
           (l.lysing ~* '(verð (og fermetraverð )?miðast við (kaup á )?[0-9]{1,2} ?% (eignarhlut|kaup)|verð íbúðar miðað við [0-9]{1,2} ?% sameign er)') AS b4
      FROM scraper.listings l
      LEFT JOIN LATERAL (SELECT min(e.event_at) AS fyrsta FROM scraper.listing_lifecycle_events e
                          WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id
                            AND e.event_type = 'confirmed_absent_1'::scraper.lifecycle_event_enum) fj ON true
      LEFT JOIN LATERAL (SELECT min(e.event_at) AS fyrsta FROM scraper.listing_lifecycle_events e
                          WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id
                            AND e.event_type = 'withdrawn_confirmed'::scraper.lifecycle_event_enum) af ON true
      LEFT JOIN LATERAL (SELECT max(e.event_at) AS sidast FROM scraper.listing_lifecycle_events e
                          WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id
                            AND e.event_type = 'price_changed'::scraper.lifecycle_event_enum) pc ON true
      LEFT JOIN LATERAL (SELECT (array_agg(h.price_amount ORDER BY h.observed_at, h.id DESC))[1] AS upph, max(h.observed_at) AS sidast
                           FROM scraper.listing_price_history h
                          WHERE h.source = l.source AND h.source_listing_id = l.source_listing_id) ph ON true
     WHERE l.fastnum = ANY (p_fastnums) AND l.source = 'mbl' AND l.tenure = 'sale'
       AND NOT EXISTS (SELECT 1 FROM scraper.tvitok_falin t WHERE t.listing_id = l.listing_id)
       AND (l.addr_text IS NULL OR l.addr_text !~* '(\yseld\y|\yseldar\y|\yseldur\y|\ysold\y|\yfrátekin\y|\yfrátekið\y)')
       AND (coalesce(l.is_price_on_request, false) OR l.price_amount IS NULL OR l.price_amount >= 3000000)
       AND (l.lysing IS NULL OR l.lysing !~* '(búsetugjald|búseturéttaríbúð|búseturétt(ur|urinn|inn|ar|arins)\M|til sölu (er )?búseturétt\M)')
  ), bil_ev AS (
    SELECT 'evalue'::text, a.augl_id, a.fastnum, a.opnun, false, a.opnun,
           CASE WHEN a.verd_thus >= 3000 THEN a.verd_thus * 1000 END::bigint, CASE WHEN a.verd_thus >= 3000 THEN a.verd_thus * 1000 END::bigint, a.opnun, NULL::text, false
      FROM scraper.auglysinga_atburdir a
     WHERE a.fastnum = ANY (p_fastnums)
       AND NOT EXISTS (SELECT 1 FROM scraper.listings l2 WHERE l2.source = 'mbl' AND l2.source_listing_id = a.augl_id)
  ), bil AS (
    SELECT b.*, coalesce(b.til, 'infinity'::timestamptz) AS til_r,
           (SELECT max(s.thinglystdags) FROM public.sales_history s
             WHERE s.fastnum = b.fastnum AND s.thinglystdags < (b.fra - interval '30 days')::date) AS sala_a_undan
      FROM (SELECT * FROM bil_mbl UNION ALL SELECT * FROM bil_ev) b
  ), m AS (
    SELECT bil.*,
           max(til_r) OVER w_fyrri AS maxlok_fyrri,
           lag(sala_a_undan) OVER w AS sala_fyrri
      FROM bil
    WINDOW w AS (PARTITION BY fastnum ORDER BY fra, augl_id),
           w_fyrri AS (PARTITION BY fastnum ORDER BY fra, augl_id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
  ), l AS (
    -- cc365: lota = samfellt tímabil eftir N = 14 d reglunni einni (óbreytt frá cc362).
    SELECT m.*, (maxlok_fyrri IS NULL OR fra > maxlok_fyrri + interval '14 days') AS lota_byrjar,
           sum(CASE WHEN maxlok_fyrri IS NULL OR fra > maxlok_fyrri + interval '14 days' THEN 1 ELSE 0 END)
             OVER (PARTITION BY fastnum ORDER BY fra, augl_id ROWS UNBOUNDED PRECEDING) AS lota_nr
      FROM m
  ), l2 AS (
    -- Kandídat að skiptingu á sölu: auglýsing inni í lotu sem sér nýrri þinglýsta sölu (> 30 d á undan stofndegi) en fyrri auglýsing.
    SELECT l.*, min(fra) OVER (PARTITION BY fastnum, lota_nr) AS lota_upphaf,
           (NOT lota_byrjar AND sala_a_undan IS NOT NULL AND sala_a_undan IS DISTINCT FROM sala_fyrri) AS kandidat
      FROM l
  ), l3 AS (
    SELECT l2.*, max(CASE WHEN kandidat THEN fra END)
                   OVER (PARTITION BY fastnum, lota_nr ORDER BY fra, augl_id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS fyrri_kandidat_fra
      FROM l2
  ), n AS (
    -- cc365: sala skiptir ferli AÐEINS ef salan er þinglýst á eða eftir upphafi ferlisins sem stendur (lotu eða fyrri skiptingar).
    -- Sala á undan upphafi ferlisins er þegar að baki því (ferlið er endurbirting eftir söluna) og klýfur það ekki aftur (2049440).
    SELECT l3.*, sum(CASE WHEN lota_byrjar
                            OR (kandidat AND sala_a_undan >= GREATEST(lota_upphaf, coalesce(fyrri_kandidat_fra, lota_upphaf))::date)
                          THEN 1 ELSE 0 END)
                   OVER (PARTITION BY fastnum ORDER BY fra, augl_id ROWS UNBOUNDED PRECEDING)::integer AS ferli_nr
      FROM l3
  ), f AS (
    SELECT n.fastnum, n.ferli_nr, min(n.fra) AS upphaf, max(n.til_r) AS lok_r, bool_or(n.opin) AS opid,
           count(*)::integer AS n_auglysingar,
           array_remove(array_agg(DISTINCT n.sala), NULL) AS fasteignasolur,
           (array_agg(n.verd_upph ORDER BY n.fra, n.augl_id) FILTER (WHERE n.verd_upph IS NOT NULL))[1] AS fyrsta_verd,
           (array_agg(n.verd_nu ORDER BY n.opin DESC, n.asett_dags DESC, n.fra DESC) FILTER (WHERE n.verd_nu IS NOT NULL))[1] AS sidasta_verd,
           bool_or(n.b4) AS hlutaverd,
           (array_agg(n.heimild ORDER BY n.fra, n.augl_id))[1] AS fyrsta_heimild,
           (array_agg(n.heimild ORDER BY n.til_r DESC, n.fra DESC))[1] AS sidasta_heimild
      FROM n GROUP BY n.fastnum, n.ferli_nr
  ), g AS (
    SELECT f.*,
           CASE WHEN f.opid THEN NULL ELSE f.lok_r END AS lok,
           NOT ((f.upphaf >= timestamptz '2025-06-17' AND f.upphaf < timestamptz '2026-06-15')
                OR (f.fyrsta_heimild = 'evalue' AND f.upphaf < timestamptz '2015-01-01')) AS upphaf_viss,
           (f.opid OR f.sidasta_heimild = 'mbl') AS lok_viss,
           lead(f.upphaf) OVER (PARTITION BY f.fastnum ORDER BY f.upphaf) AS naesta_upphaf
      FROM f
  )
  SELECT g.fastnum, g.ferli_nr, g.upphaf, g.lok, g.opid,
         CASE WHEN g.upphaf_viss AND g.lok_viss
              THEN (extract(epoch FROM (coalesce(g.lok, now()) - g.upphaf)) / 86400)::integer END AS dagar,
         (extract(epoch FROM (coalesce(g.lok, now()) - g.upphaf)) / 86400)::integer AS dagar_minnst,
         g.upphaf_viss, g.lok_viss, g.n_auglysingar, g.fasteignasolur, g.fyrsta_verd, g.sidasta_verd, g.hlutaverd, g.naesta_upphaf
    FROM g
$$;
REVOKE ALL ON FUNCTION scraper.soluferli(bigint[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION scraper.soluferli(bigint[]) TO service_role;
COMMENT ON FUNCTION scraper.soluferli(bigint[]) IS
  'cc362/cc365: söluferli fastnúmera (N=14 d sameining; sala skiptir ferli aðeins ef hún er þinglýst eftir upphaf þess). Eina skilgreiningin á „dagar á sölu"; lesið af public.solusaga og public.soluferli_opin. Aðeins service_role.';


NOTIFY pgrst, 'reload schema';
