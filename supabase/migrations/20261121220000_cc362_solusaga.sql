-- cc362: söluferli eignar — „N dagar á sölu" (merki), „Sölusaga" (gluggi) og dagafjöldi í vöktun/leit úr EINUM lesfleti.
--
-- Skilgreining (SKIL_CC362 §A1): söluferli = samfellt tímabil þar sem a.m.k. ein söluauglýsing eignarinnar (fastnum) var virk.
--   * Auglýsingabil (mbl): upphaf = first_seen_at (stofntími mbl). Lok = fyrsta confirmed_absent_1, annars withdrawn_at, annars
--     max(last_seen_at, sidast_fundin_at). Opin = sama skilyrði og scraper.v_eign_virk_auglysing (active, engin fjarvera, engin
--     afskráning) — sama „á sölu" og cc341/cc342. Sömu útilokanir og sýnin: tvitok_falin, „seld/frátekin" í heiti, söluverð < 3 M
--     (birtingarvörn /eign). Búseturéttur (B3, regla hlid-v1) fellur út eins og `fela` í cc354 B.
--   * Auglýsingabil (evalue, frosið 15.04.2026, aðeins auðkenni sem eru ekki í lifandi mbl): stofndagur einn, engin lok.
--   * Sameining: nýtt ferli þegar auglýsing hefst meira en N = 14 dögum eftir hæstu fyrri lok (= LOTU_BIL_DAGAR vöktunar,
--     „Kemur á sölu"), EÐA þegar þinglýst sala fastnúmersins liggur > 30 d á undan stofndegi auglýsingarinnar og sú sala er
--     ekki sú sama og fyrri auglýsing ber (sala skiptir ferlum).
--   * Upphaf óvíst (vinstri ritskoðun): upphaf í auglýsingagati 17.06.2025–15.06.2026 (evalue þynnist 07.2025, lifandi sókn heil
--     frá 06.2026) eða evalue-upphaf fyrir 2015. Lok óviss: ferli sem endar á evalue-punkti.
--   * Þinglýst sala tengd lokuðu ferli: fyrsta sala frá upphafi ferlis, á bilinu [lok − 60 d, lok + M], M = 90 d (lok viss) eða
--     180 d (lok óviss, evalue), og á undan næsta ferli. Samanburðarhæf: onothaefur = 0, eitt fastnúmer á færslu, suspect_reason
--     án kv_extreme/size_mismatch/sentinel_price, kaupverð > 0, ekkert hlutaverð (B4) í ferlinu, hlutfall kaupverð/síðasta ásett
--     á [0,5; 2,0]. Annars „Seld" án talna (regla 13).
--   * Stofnverð auglýsingar = fyrsta verð í listing_price_history; jafntefli á observed_at (1.074 af 1.173 „breytingum" innan
--     auglýsingar eru tvær raðir á sama tíma, A5) leysist á SÍÐUSTU skráningu (hæsta id).
--   * Niðurstaða: a_solu (opið) / seld / tekin_af_solu (engin sala og lok + M liðið fyrir nýjustu þinglýsingu) / af_solu_ovist.
--
-- Aðgangur: öll föll SECURITY DEFINER með föstum search_path; EXECUTE tekið af PUBLIC/anon/authenticated og veitt service_role
-- eingöngu (þjónninn). Engin ný tafla, engin gögn geymd. Nýr vísir á scraper.auglysinga_atburdir(fastnum) (464.866 raðir, frosin
-- tafla sem enginn skrifar í; www les hana ekki beint).
-- BEGIN/COMMIT eru ekki hér: beitingarskriftan stýrir færslunni (lock_timeout 5s).

CREATE INDEX auglysinga_atburdir_fastnum ON scraper.auglysinga_atburdir (fastnum);

-- 1) Kjarni: ferli fyrir mengi fastnúmera. Eitt fall = ein skilgreining; merkið, glugginn, vöktun og leit lesa þetta.
CREATE FUNCTION scraper.soluferli(p_fastnums bigint[])
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

-- 2) Merki, vöktun og leit: opið ferli per fastnúmer (eitt per fastnúmer, nýjasta upphaf ef sala skipti opnu ferli).
CREATE FUNCTION public.soluferli_opin(p_fastnums bigint[])
RETURNS TABLE (fastnum bigint, upphaf timestamptz, dagar integer, dagar_minnst integer, upphaf_viss boolean,
               n_auglysingar integer, fasteignasolur text[], fyrsta_verd bigint, sidasta_verd bigint)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = scraper, public, pg_temp
AS $$
  SELECT DISTINCT ON (s.fastnum) s.fastnum, s.upphaf, s.dagar, s.dagar_minnst, s.upphaf_viss, s.n_auglysingar, s.fasteignasolur,
         s.fyrsta_verd, s.sidasta_verd
    FROM scraper.soluferli(p_fastnums[1:2000]) s
   WHERE s.opid
   ORDER BY s.fastnum, s.upphaf DESC
$$;
REVOKE ALL ON FUNCTION public.soluferli_opin(bigint[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.soluferli_opin(bigint[]) TO service_role;
COMMENT ON FUNCTION public.soluferli_opin(bigint[]) IS
  'cc362: opið söluferli per fastnúmer (mest 2000 í kalli): upphaf, dagar (NULL ef upphaf óvíst), dagar_minnst. Merkið á /eign, vöktun og leit. Aðeins service_role.';

-- 3) Glugginn „Sölusaga": öll ferli eignar, nýjast efst, með verðferli og þinglýstri sölu.
CREATE FUNCTION public.solusaga(p_fastnum bigint)
RETURNS TABLE (
  ferli_nr integer, upphaf date, lok date, opid boolean, dagar integer, dagar_minnst integer, upphaf_viss boolean, lok_viss boolean,
  n_auglysingar integer, fasteignasolur text[], fyrsta_verd bigint, sidasta_verd bigint, verdferill jsonb,
  nidurstada text, sala_thinglyst date, sala_kaupverd bigint, sala_samanburdarhaef boolean,
  munur_sidasta_pct numeric, munur_fyrsta_pct numeric
)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = scraper, public, pg_temp
AS $$
  WITH f AS (SELECT * FROM scraper.soluferli(ARRAY[p_fastnum])),
  -- verðpunktar: stofnverð hverrar auglýsingar + price_changed innan auglýsingar; þrep per fasteignasölu (sama verð í röð fellur)
  pt AS (
    SELECT l.fastnum, l.first_seen_at AS t, coalesce(ph.upph, l.price_amount) AS verd, l.agency_name AS sala
      FROM scraper.listings l
      LEFT JOIN LATERAL (SELECT (array_agg(h.price_amount ORDER BY h.observed_at, h.id DESC))[1] AS upph FROM scraper.listing_price_history h
                          WHERE h.source = l.source AND h.source_listing_id = l.source_listing_id) ph ON true
     WHERE l.fastnum = p_fastnum AND l.source = 'mbl' AND l.tenure = 'sale'
       AND NOT EXISTS (SELECT 1 FROM scraper.tvitok_falin t WHERE t.listing_id = l.listing_id)
    UNION ALL
    SELECT l.fastnum, e.event_at, (e.evidence->>'new')::bigint, l.agency_name
      FROM scraper.listings l JOIN scraper.listing_lifecycle_events e
        ON e.source = l.source AND e.source_listing_id = l.source_listing_id AND e.event_type = 'price_changed'::scraper.lifecycle_event_enum
     WHERE l.fastnum = p_fastnum AND l.source = 'mbl' AND l.tenure = 'sale'
       AND NOT EXISTS (SELECT 1 FROM scraper.tvitok_falin t WHERE t.listing_id = l.listing_id)
    UNION ALL
    SELECT a.fastnum, a.opnun, (nullif(a.verd_thus, 0) * 1000)::bigint, NULL::text
      FROM scraper.auglysinga_atburdir a
     WHERE a.fastnum = p_fastnum
       AND NOT EXISTS (SELECT 1 FROM scraper.listings l2 WHERE l2.source = 'mbl' AND l2.source_listing_id = a.augl_id)
  ), ptf AS (
    SELECT f.ferli_nr, pt.t, pt.verd, pt.sala,
           lag(pt.verd) OVER (PARTITION BY f.ferli_nr, pt.sala ORDER BY pt.t) AS fyrra
      FROM pt JOIN f ON pt.t >= f.upphaf AND pt.t <= coalesce(f.lok, now())
     WHERE pt.verd IS NOT NULL AND pt.verd >= 3000000
  ), vf AS (
    SELECT ferli_nr, jsonb_agg(jsonb_build_object('dags', t::date, 'verd', verd, 'fasteignasala', sala) ORDER BY t) AS verdferill
      FROM ptf WHERE fyrra IS NULL OR fyrra <> verd GROUP BY ferli_nr
  ), sm AS (
    SELECT f.ferli_nr, s.thinglystdags, s.kaupverd_nominal, s.onothaefur, s.suspect_reason,
           (SELECT count(DISTINCT s2.fastnum) FROM public.sales_history s2 WHERE s2.faerslunumer = s.faerslunumer) AS n_fastnum
      FROM f
      JOIN LATERAL (SELECT s.* FROM public.sales_history s
                     WHERE s.fastnum = f.fastnum AND NOT f.opid
                       AND s.thinglystdags >= f.upphaf::date
                       AND s.thinglystdags >= (f.lok - interval '60 days')::date
                       AND s.thinglystdags <= (f.lok + CASE WHEN f.lok_viss THEN interval '90 days' ELSE interval '180 days' END)::date
                       AND (f.naesta_upphaf IS NULL OR s.thinglystdags < f.naesta_upphaf::date)
                     ORDER BY s.thinglystdags, s.id LIMIT 1) s ON true
  ), mx AS (SELECT max(thinglystdags) AS sidasta FROM public.sales_history)
  SELECT f.ferli_nr, f.upphaf::date, f.lok::date, f.opid, f.dagar, f.dagar_minnst, f.upphaf_viss, f.lok_viss,
         f.n_auglysingar, f.fasteignasolur, f.fyrsta_verd, f.sidasta_verd, coalesce(vf.verdferill, '[]'::jsonb),
         CASE WHEN f.opid THEN 'a_solu'
              WHEN sm.thinglystdags IS NOT NULL THEN 'seld'
              WHEN (f.lok + CASE WHEN f.lok_viss THEN interval '90 days' ELSE interval '180 days' END)::date <= mx.sidasta THEN 'tekin_af_solu'
              ELSE 'af_solu_ovist' END,
         sm.thinglystdags,
         CASE WHEN k.samanb THEN sm.kaupverd_nominal END,
         coalesce(k.samanb, false),
         CASE WHEN k.samanb THEN round(100.0 * (sm.kaupverd_nominal::numeric / f.sidasta_verd - 1), 1) END,
         CASE WHEN k.samanb AND f.fyrsta_verd > 0 THEN round(100.0 * (sm.kaupverd_nominal::numeric / f.fyrsta_verd - 1), 1) END
    FROM f
    CROSS JOIN mx
    LEFT JOIN vf ON vf.ferli_nr = f.ferli_nr
    LEFT JOIN sm ON sm.ferli_nr = f.ferli_nr
    LEFT JOIN LATERAL (SELECT (sm.thinglystdags IS NOT NULL AND sm.onothaefur = 0 AND sm.n_fastnum = 1
                               AND coalesce(sm.suspect_reason, '') !~ '(kv_extreme|size_mismatch|sentinel)'
                               AND sm.kaupverd_nominal > 0 AND NOT f.hlutaverd AND f.sidasta_verd > 0
                               AND sm.kaupverd_nominal::numeric / f.sidasta_verd BETWEEN 0.5 AND 2.0) AS samanb) k ON true
   ORDER BY f.upphaf DESC
$$;
REVOKE ALL ON FUNCTION public.solusaga(bigint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.solusaga(bigint) TO service_role;
COMMENT ON FUNCTION public.solusaga(bigint) IS
  'cc362: sölusaga eignar, ferli nýjast efst, með verðferli (jsonb) og þinglýstri sölu (tölur aðeins ef samanburðarhæf). Aðeins service_role (/api/solusaga). Engin ferli = engar raðir.';

-- 4) Hnappurinn „Sölusaga": er a.m.k. eitt ferli til? Ódýrt (vísar á fastnum), sömu síur og bil_mbl/bil_ev í soluferli:
--    hvert auglýsingabil myndar ferli, svo „til" ⇔ soluferli skilar ≥ 1 röð.
CREATE FUNCTION public.solusaga_til(p_fastnum bigint)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = scraper, public, pg_temp
AS $$
  SELECT EXISTS (SELECT 1 FROM scraper.listings l
                  WHERE l.fastnum = p_fastnum AND l.source = 'mbl' AND l.tenure = 'sale'
                    AND NOT EXISTS (SELECT 1 FROM scraper.tvitok_falin t WHERE t.listing_id = l.listing_id)
                    AND (l.addr_text IS NULL OR l.addr_text !~* '(\yseld\y|\yseldar\y|\yseldur\y|\ysold\y|\yfrátekin\y|\yfrátekið\y)')
                    AND (coalesce(l.is_price_on_request, false) OR l.price_amount IS NULL OR l.price_amount >= 3000000)
                    AND (l.lysing IS NULL OR l.lysing !~* '(búsetugjald|búseturéttaríbúð|búseturétt(ur|urinn|inn|ar|arins)\M|til sölu (er )?búseturétt\M)'))
      OR EXISTS (SELECT 1 FROM scraper.auglysinga_atburdir a
                  WHERE a.fastnum = p_fastnum
                    AND NOT EXISTS (SELECT 1 FROM scraper.listings l2 WHERE l2.source = 'mbl' AND l2.source_listing_id = a.augl_id))
$$;
REVOKE ALL ON FUNCTION public.solusaga_til(bigint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.solusaga_til(bigint) TO service_role;
COMMENT ON FUNCTION public.solusaga_til(bigint) IS
  'cc362: satt ef eign á a.m.k. eitt söluferli (hnappurinn „Sölusaga" á /eign). Aðeins service_role.';

NOTIFY pgrst, 'reload schema';
