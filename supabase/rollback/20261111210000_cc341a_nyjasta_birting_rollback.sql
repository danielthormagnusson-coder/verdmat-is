-- cc341 (a) ROLLBACK — skilar v_leit_listings og leit_auglysingar í skilgreininguna fyrir 20261111210000 (lesin lifandi 11.11).
begin;
set local lock_timeout = '5s';

create or replace view scraper.v_leit_listings as
SELECT l.listing_id,
    l.source,
    l.source_listing_id,
    l.fastnum,
    l.tenure,
    l.category,
    l.sub_type,
    l.tegund_raw,
    l.price_amount,
    l.is_price_on_request,
    ph.asett_verd_dags,
    l.size_sqm,
    l.rooms,
    l.bedrooms,
    l.bathrooms,
    COALESCE((l.byggar)::numeric, p.byggar) AS byggar,
    l.addr_text,
    l.addr_postcode,
    btrim(COALESCE(p.sveitarfelag, l.addr_municipality, pn.sveitarfelag)) AS sveitarfelag,
    btrim(p.matsvaedi_nafn) AS hverfi,
    p.matsvaedi_numer,
    COALESCE((l.lat)::double precision, p.lat) AS lat,
    COALESCE((l.lng)::double precision, p.lng) AS lng,
    l.photos_json,
    p.first_photo_url,
    l.listed_at,
    l.first_seen_at,
    l.last_seen_at,
    l.br_dags,
    (EXISTS ( SELECT 1
           FROM scraper.listing_lifecycle_events ea
          WHERE ((ea.source = l.source) AND (ea.source_listing_id = l.source_listing_id) AND (ea.event_type = 'confirmed_absent_1'::scraper.lifecycle_event_enum)))) AS er_fjarveru_flaggad,
    (EXISTS ( SELECT 1
           FROM predictions pr
          WHERE ((pr.fastnum = l.fastnum) AND (pr.real_pred_mean IS NOT NULL)))) AS er_metanleg,
        CASE
            WHEN (l.is_price_on_request OR (l.price_amount IS NULL) OR (l.size_sqm IS NULL) OR (l.size_sqm <= (0)::numeric)) THEN NULL::numeric
            ELSE round(((l.price_amount)::numeric / l.size_sqm))
        END AS fermetraverd_kr,
    l.mublad,
    p.is_new_build,
    l.er_atvinnuhusnaedi,
    (row_number() OVER (PARTITION BY l.tenure, l.category, COALESCE((l.fastnum)::text, ('addr:'::text || lower(btrim(l.addr_text)))), l.price_amount, l.size_sqm ORDER BY l.listed_at DESC NULLS LAST, l.listing_id DESC) = 1) AS er_nyjasta_birting,
    (l.addr_text ~* '(\yseld\y|\yseldar\y|\yseldur\y|\ysold\y|\yfrátekin\y|\yfrátekið\y)'::text) AS er_auglyst_seld,
    ((l.price_amount IS NOT NULL) AND (EXISTS ( SELECT 1
           FROM scraper.listing_price_history ph3
          WHERE ((ph3.source = l.source) AND (ph3.source_listing_id = l.source_listing_id) AND (ph3.price_amount > l.price_amount))))) AS verd_laekkad,
        CASE
            WHEN (l.tenure = 'rent'::text) THEN c.available_from
            ELSE NULL::date
        END AS laus_fra,
        CASE
            WHEN (l.tenure = 'rent'::text) THEN (c.lease_term_class)::text
            ELSE NULL::text
        END AS leigutimi,
        CASE
            WHEN (l.tenure = 'rent'::text) THEN c.deposit_isk
            ELSE NULL::numeric
        END AS trygging_isk
   FROM ((((scraper.listings l
     LEFT JOIN v_properties p USING (fastnum))
     LEFT JOIN scraper.listings_canonical c ON (((c.source = l.source) AND (c.source_listing_id = l.source_listing_id))))
     LEFT JOIN LATERAL ( SELECT pp.sveitarfelag
           FROM properties pp
          WHERE ((l.addr_postcode ~ '^[0-9]+$'::text) AND (pp.postnr = (l.addr_postcode)::integer) AND (pp.sveitarfelag IS NOT NULL))
         LIMIT 1) pn ON (true))
     LEFT JOIN LATERAL ( SELECT max(ph2.observed_at) AS asett_verd_dags
           FROM scraper.listing_price_history ph2
          WHERE ((ph2.source = l.source) AND (ph2.source_listing_id = l.source_listing_id))) ph ON (true))
  WHERE ((l.status = 'active'::text) AND (NOT (EXISTS ( SELECT 1
           FROM scraper.listing_lifecycle_events e
          WHERE ((e.source = l.source) AND (e.source_listing_id = l.source_listing_id) AND (e.event_type = 'withdrawn_confirmed'::scraper.lifecycle_event_enum))))) AND (NOT (EXISTS ( SELECT 1
           FROM scraper.tvitok_falin tf
          WHERE (tf.listing_id = l.listing_id)))));

CREATE OR REPLACE FUNCTION scraper.leit_auglysingar(p_tenure text DEFAULT 'sale'::text, p_category text DEFAULT 'residential'::text, p_sub_type text DEFAULT NULL::text, p_sveitarfelag text[] DEFAULT NULL::text[], p_hverfi text DEFAULT NULL::text, p_matsvaedi integer DEFAULT NULL::integer, p_postnr text DEFAULT NULL::text, p_addr text DEFAULT NULL::text, p_verd_min numeric DEFAULT NULL::numeric, p_verd_max numeric DEFAULT NULL::numeric, p_staerd_min numeric DEFAULT NULL::numeric, p_staerd_max numeric DEFAULT NULL::numeric, p_herbergi_min numeric DEFAULT NULL::numeric, p_mublad text DEFAULT NULL::text, p_nybygging boolean DEFAULT false, p_aldur text DEFAULT NULL::text, p_laus text DEFAULT NULL::text, p_leigutimi text DEFAULT NULL::text, p_rodun text DEFAULT 'nyjast'::text, p_sida integer DEFAULT 1, p_med_fjarveru boolean DEFAULT false)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'scraper', 'public'
AS $function$
DECLARE
  v_rodun    text;
  v_svaedi   boolean := p_sveitarfelag IS NOT NULL OR p_hverfi IS NOT NULL OR p_matsvaedi IS NOT NULL OR p_nybygging IS TRUE;
  v_canon    boolean := p_tenure = 'rent' AND (p_laus = 'nuna' OR p_leigutimi IS NOT NULL);
  v_laus     boolean := p_tenure = 'rent' AND p_laus = 'nuna';
  v_addr     text    := NULLIF(btrim(replace(replace(replace(COALESCE(p_addr, ''), '%', ''), '_', ''), '\', '')), '');
  v_postnr   text    := NULLIF(btrim(COALESCE(p_postnr, '')), '');
  v_uppfl    text    := '';
  v_sql      text;
  v_ut       jsonb;
BEGIN
  v_rodun := CASE p_rodun
    WHEN 'verd_haekkandi' THEN 'price_amount ASC NULLS LAST'
    WHEN 'verd_laekkandi' THEN 'price_amount DESC NULLS LAST'
    WHEN 'staerd'         THEN 'size_sqm DESC NULLS LAST'
    WHEN 'fm_verd'        THEN 'fermetraverd_kr ASC NULLS LAST'
    ELSE 'listed_at DESC NULLS LAST'
  END;

  IF v_svaedi THEN
    v_uppfl := v_uppfl || ' LEFT JOIN public.v_properties vp ON vp.fastnum = g.fastnum ';
  END IF;
  IF v_canon THEN
    v_uppfl := v_uppfl || ' LEFT JOIN scraper.listings_canonical cn ON cn.source = g.source AND cn.source_listing_id = g.source_listing_id ';
  END IF;

  v_sql := $sql$
    WITH g AS (
      SELECT l.listing_id, l.source, l.source_listing_id, l.fastnum, l.sub_type, l.price_amount, l.is_price_on_request, l.size_sqm, l.rooms,
             l.addr_text, l.addr_postcode, l.addr_municipality, l.listed_at, l.first_seen_at, l.mublad, l.er_atvinnuhusnaedi,
             CASE WHEN l.is_price_on_request OR l.price_amount IS NULL OR l.size_sqm IS NULL OR l.size_sqm <= 0::numeric THEN NULL::numeric
                  ELSE round(l.price_amount::numeric / l.size_sqm) END AS fermetraverd_kr,
             row_number() OVER (PARTITION BY l.tenure, l.category, COALESCE(l.fastnum::text, 'addr:' || lower(btrim(l.addr_text))), l.price_amount, l.size_sqm
                                ORDER BY l.listed_at DESC NULLS LAST, l.listing_id DESC) = 1 AS nyj
      FROM scraper.listings l
      WHERE l.status = 'active' AND l.tenure = $1 AND l.category = $2
        AND NOT EXISTS (SELECT 1 FROM scraper.listing_lifecycle_events e
                        WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id AND e.event_type = 'withdrawn_confirmed')
        AND NOT EXISTS (SELECT 1 FROM scraper.tvitok_falin tf WHERE tf.listing_id = l.listing_id)
    ),
    f AS (
      SELECT g.listing_id, g.source, g.source_listing_id, g.fastnum, g.price_amount, g.is_price_on_request, g.size_sqm, g.addr_text, g.addr_postcode,
             g.addr_municipality, g.listed_at, g.first_seen_at, g.fermetraverd_kr, g.mublad, g.nyj,
             $sql$ || CASE WHEN v_canon THEN $sql$ CASE WHEN $1 = 'rent' THEN cn.available_from END $sql$ ELSE $sql$ NULL::date $sql$ END || $sql$ AS laus_fra
      FROM g $sql$ || v_uppfl || $sql$
      WHERE (g.addr_text ~* '(\yseld\y|\yseldar\y|\yseldur\y|\ysold\y|\yfrátekin\y|\yfrátekið\y)') = false
        AND ($1 <> 'sale' OR ((g.price_amount >= 3000000 OR g.price_amount IS NULL OR g.is_price_on_request IS TRUE)
                              AND (g.addr_text NOT ILIKE '%leiga%' OR g.addr_text IS NULL)))
        AND ($1 <> 'rent' OR ((g.price_amount >= 50000 OR g.price_amount IS NULL OR g.is_price_on_request IS TRUE)
                              AND ($2 <> 'residential' OR g.er_atvinnuhusnaedi IS NOT TRUE)))
        AND ($3 IS NULL OR g.sub_type = $3)
        AND ($7 IS NULL OR g.addr_postcode = $7)
        AND ($8 IS NULL OR g.addr_text ILIKE '%' || $8 || '%')
        AND ($9 IS NULL OR g.price_amount >= $9)
        AND ($10 IS NULL OR g.price_amount <= $10)
        AND ($11 IS NULL OR g.size_sqm >= $11)
        AND ($12 IS NULL OR g.size_sqm <= $12)
        AND ($13 IS NULL OR g.rooms >= $13)
        AND ($14 IS DISTINCT FROM 'ja' OR g.mublad = true)
        AND ($14 IS DISTINCT FROM 'nei' OR g.mublad = false)
        AND ($14 IS DISTINCT FROM 'othekkt' OR g.mublad IS NULL)
        AND ($16 IS DISTINCT FROM 'nytt7' OR g.first_seen_at >= now() - interval '7 days')
        AND ($16 IS DISTINCT FROM 'eldri90' OR g.listed_at <= now() - interval '90 days')
        $sql$ || CASE WHEN v_svaedi THEN $sql$
        AND ($4 IS NULL OR btrim(COALESCE(vp.sveitarfelag, g.addr_municipality,
              (SELECT pp.sveitarfelag FROM public.properties pp
               WHERE pp.postnr = CASE WHEN g.addr_postcode ~ '^[0-9]+$' THEN g.addr_postcode::integer END AND pp.sveitarfelag IS NOT NULL LIMIT 1))) = ANY ($4))
        AND ($5 IS NULL OR btrim(vp.matsvaedi_nafn) = $5)
        AND ($6 IS NULL OR vp.matsvaedi_numer = $6)
        AND ($15 IS NOT TRUE OR vp.is_new_build = true)
        $sql$ ELSE '' END || CASE WHEN v_canon THEN $sql$
        AND ($18 IS NULL OR cn.lease_term_class::text = $18)
        $sql$ ELSE '' END || $sql$
        AND ($21 IS TRUE OR NOT EXISTS (SELECT 1 FROM scraper.listing_lifecycle_events ea
              WHERE ea.source = g.source AND ea.source_listing_id = g.source_listing_id AND ea.event_type = 'confirmed_absent_1'))
    ),
    f2 AS (
      SELECT f.*, ($17 IS DISTINCT FROM 'nuna' OR f.laus_fra <= (now() AT TIME ZONE 'UTC')::date) AS laus_ok FROM f
    ),
    c AS (
      SELECT count(*) FILTER (WHERE nyj AND laus_ok) AS heild,
             count(*) FILTER (WHERE laus_ok) AS auglysingar,
             count(*) FILTER (WHERE nyj) AS laus_alls,
             count(*) FILTER (WHERE nyj AND laus_fra IS NULL) AS laus_an_dags
      FROM f2
    ),
    p AS (
      SELECT f2.*, row_number() OVER (ORDER BY $sql$ || v_rodun || $sql$, listing_id ASC) AS rn
      FROM f2 WHERE nyj AND laus_ok
      ORDER BY $sql$ || v_rodun || $sql$, listing_id ASC
      LIMIT 24 OFFSET (GREATEST($20, 1) - 1) * 24
    ),
    s AS (
      SELECT f2.price_amount, f2.first_seen_at, f2.listed_at,
             EXISTS (SELECT 1 FROM scraper.listing_price_history ph3
                     WHERE ph3.source = f2.source AND ph3.source_listing_id = f2.source_listing_id AND ph3.price_amount > f2.price_amount) AS verd_laekkad
      FROM f2
      WHERE nyj AND laus_ok AND f2.price_amount IS NOT NULL AND f2.is_price_on_request = false
      -- Sama val og sýnin gaf (raðir hennar koma í röð gluggans), nú skýrt og með jafnteflisbrjót. Þak 1000 óbreytt.
      ORDER BY COALESCE(f2.fastnum::text, 'addr:' || lower(btrim(f2.addr_text))), f2.price_amount, f2.size_sqm, f2.listed_at DESC NULLS LAST, f2.listing_id DESC
      LIMIT 1000
    ),
    v AS (
      SELECT count(*) FILTER (WHERE
               CASE WHEN $1 = 'sale' THEN (g.price_amount < 3000000 AND g.is_price_on_request = false) OR g.addr_text ILIKE '%leiga%'
                    ELSE g.price_amount < 50000 AND g.is_price_on_request = false END) AS vorn,
             count(*) FILTER (WHERE $1 = 'rent' AND $2 = 'residential' AND g.er_atvinnuhusnaedi = true) AS atvinna
      FROM g
      WHERE ((CASE WHEN $1 = 'sale' THEN (g.price_amount < 3000000 AND g.is_price_on_request = false) OR g.addr_text ILIKE '%leiga%'
                   ELSE g.price_amount < 50000 AND g.is_price_on_request = false END)
             OR ($1 = 'rent' AND $2 = 'residential' AND g.er_atvinnuhusnaedi = true))
        AND NOT EXISTS (SELECT 1 FROM scraper.listing_lifecycle_events ea
                        WHERE ea.source = g.source AND ea.source_listing_id = g.source_listing_id AND ea.event_type = 'confirmed_absent_1')
    )
    SELECT jsonb_build_object(
      'radir', COALESCE((
        SELECT jsonb_agg(
                 CASE WHEN $1 = 'rent' THEN to_jsonb(r) - 'rn' ELSE to_jsonb(r) - ARRAY['rn', 'laus_fra', 'leigutimi', 'trygging_isk'] END
                 ORDER BY r.rn)
        FROM (
          SELECT p.rn, l.listing_id, l.source, l.fastnum, l.tenure, l.category, l.sub_type, l.tegund_raw, l.price_amount, l.is_price_on_request,
                 ph.asett_verd_dags, l.size_sqm, l.rooms, l.bedrooms,
                 COALESCE(l.byggar::numeric, vp.byggar) AS byggar,
                 l.addr_text, l.addr_postcode,
                 btrim(COALESCE(vp.sveitarfelag, l.addr_municipality,
                   (SELECT pp.sveitarfelag FROM public.properties pp
                    WHERE pp.postnr = CASE WHEN l.addr_postcode ~ '^[0-9]+$' THEN l.addr_postcode::integer END AND pp.sveitarfelag IS NOT NULL LIMIT 1))) AS sveitarfelag,
                 btrim(vp.matsvaedi_nafn) AS hverfi, vp.matsvaedi_numer,
                 COALESCE(l.lat::double precision, vp.lat) AS lat, COALESCE(l.lng::double precision, vp.lng) AS lng,
                 l.photos_json, vp.first_photo_url, l.listed_at, l.first_seen_at, l.last_seen_at,
                 EXISTS (SELECT 1 FROM public.predictions pr WHERE pr.fastnum = l.fastnum AND pr.real_pred_mean IS NOT NULL) AS er_metanleg,
                 EXISTS (SELECT 1 FROM scraper.listing_lifecycle_events ea
                         WHERE ea.source = l.source AND ea.source_listing_id = l.source_listing_id AND ea.event_type = 'confirmed_absent_1') AS er_fjarveru_flaggad,
                 p.fermetraverd_kr, vp.is_new_build, l.mublad,
                 cn.available_from AS laus_fra, cn.lease_term_class::text AS leigutimi, cn.deposit_isk AS trygging_isk
          FROM p
          JOIN scraper.listings l ON l.listing_id = p.listing_id
          LEFT JOIN public.v_properties vp ON vp.fastnum = l.fastnum
          LEFT JOIN scraper.listings_canonical cn ON $1 = 'rent' AND cn.source = l.source AND cn.source_listing_id = l.source_listing_id
          LEFT JOIN LATERAL (SELECT max(ph2.observed_at) AS asett_verd_dags FROM scraper.listing_price_history ph2
                             WHERE ph2.source = l.source AND ph2.source_listing_id = l.source_listing_id) ph ON true
        ) r), '[]'::jsonb),
      'heild', c.heild,
      'auglysingar', c.auglysingar,
      'samantekt', COALESCE((SELECT jsonb_agg(to_jsonb(s)) FROM s), '[]'::jsonb),
      'vorn', v.vorn,
      'atvinna', v.atvinna,
      'laus_alls', c.laus_alls,
      'laus_an_dags', c.laus_an_dags
    )
    FROM c, v
  $sql$;

  EXECUTE v_sql INTO v_ut
    USING p_tenure, p_category, p_sub_type, p_sveitarfelag, p_hverfi, p_matsvaedi, v_postnr, v_addr,
          p_verd_min, p_verd_max, p_staerd_min, p_staerd_max, p_herbergi_min, p_mublad, p_nybygging,
          p_aldur, CASE WHEN v_laus THEN 'nuna' END, p_leigutimi, p_rodun, p_sida, p_med_fjarveru;
  RETURN v_ut;
END;
$function$;

notify pgrst, 'reload schema';
commit;
