-- Rollback cc365: scraper.soluferli aftur í skilgreiningu cc362 (20261121220000_cc362_solusaga), orðrétt. Sama undirskrift.
-- Ath.: ef cc364 (scraper.soluferli_opin_mv) er beitt þarf REFRESH MATERIALIZED VIEW á eftir.

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
  ), n AS (
    SELECT m.*, sum(CASE WHEN maxlok_fyrri IS NULL
                           OR fra > maxlok_fyrri + interval '14 days'
                           OR sala_a_undan IS DISTINCT FROM sala_fyrri THEN 1 ELSE 0 END)
                  OVER (PARTITION BY fastnum ORDER BY fra, augl_id ROWS UNBOUNDED PRECEDING)::integer AS ferli_nr
      FROM m
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
  'cc362: söluferli fastnúmera (N=14 d sameining, skipting á sölu). Eina skilgreiningin á „dagar á sölu"; lesið af public.solusaga og public.soluferli_opin. Aðeins service_role.';


NOTIFY pgrst, 'reload schema';
