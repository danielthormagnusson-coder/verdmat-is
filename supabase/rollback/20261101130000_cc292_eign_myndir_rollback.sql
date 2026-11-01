-- Rollback cc292 20261101130000: sýnin fer aftur í skilgreininguna fyrir cc292 (4 dálkar).
-- DROP + CREATE, því CREATE OR REPLACE getur ekki fellt dálk. Réttindi eru endurgerð nákvæmlega
-- eins og fyrir (postgres=arwdDxtm, service_role=arwdDxtm, anon=r, authenticated=r), og
-- eign_myndir_augl er felld.
-- ATH. raðir sem cc292-hleðslan bætti í property_images eru EKKI felldar hér. Þær eru skráðar
-- í D:\_audit\cc292_myndir\k10_hladid.csv; afturköllun: k10_hlada_property_images.py --afturkalla.
SET TRANSACTION READ WRITE;

DROP VIEW public.v_eign_myndir;
CREATE VIEW public.v_eign_myndir AS
 WITH fersk AS (
         SELECT DISTINCT ON (l.fastnum) l.fastnum,
            l.photos_json
           FROM scraper.listings l
          WHERE l.status = 'active'::text AND l.fastnum IS NOT NULL AND jsonb_typeof(l.photos_json) = 'array'::text AND NOT (EXISTS ( SELECT 1
                   FROM property_images pi2
                  WHERE pi2.fastnum = l.fastnum AND NOT (EXISTS ( SELECT 1
                           FROM daudir_myndahyslar d
                          WHERE pi2.url ~~* (('%'::text || d.hysill) || '%'::text)))))
          ORDER BY l.fastnum, l.listed_at DESC NULLS LAST, l.first_seen_at DESC NULLS LAST, l.listing_id DESC
        ), sereind AS (
         SELECT f.fastnum,
            m.url,
            min(m.ord) AS ord
           FROM fersk f
             CROSS JOIN LATERAL ( SELECT
                        CASE jsonb_typeof(el.value)
                            WHEN 'string'::text THEN el.value #>> '{}'::text[]
                            WHEN 'object'::text THEN COALESCE(el.value ->> 'small'::text, el.value ->> 'regular'::text, el.value ->> 'big'::text)
                            ELSE NULL::text
                        END AS url,
                    el.ord
                   FROM jsonb_array_elements(f.photos_json) WITH ORDINALITY el(value, ord)) m
          WHERE m.url ~~ 'https://%'::text
          GROUP BY f.fastnum, m.url
        )
 SELECT pi.fastnum,
    pi.url,
    pi.img_order,
    'safn'::text AS uppruni
   FROM property_images pi
  WHERE pi.utilokad_kl IS NULL
UNION ALL
 SELECT s.fastnum,
    s.url,
    row_number() OVER (PARTITION BY s.fastnum ORDER BY s.ord)::integer AS img_order,
    'auglysing'::text AS uppruni
   FROM sereind s;
REVOKE ALL ON public.v_eign_myndir FROM PUBLIC, anon, authenticated, service_role;
GRANT ALL ON public.v_eign_myndir TO service_role;
GRANT SELECT ON public.v_eign_myndir TO anon, authenticated;
COMMENT ON VIEW public.v_eign_myndir IS
  'Sameinað myndalag eignarsíðunnar (cc23 liður B5). Brúar kyrrstæða safnið (public.property_images, hlaðið 2026-07-05) og lifandi auglýsingamyndir (scraper.listings.photos_json). Safnið hefur forgang; auglýsingamyndir birtast AÐEINS þegar safnið er tómt fyrir það fastnum — aldrei blandað innan eignar. img_order er 1-BYGGT báðum megin. uppruni = safn|auglysing svo UI geti merkt heimildina. Þekja virks framboðs mæld 18.07: 40,4% → 99,8%. SECURITY DEFINER (invoker=false) er NAUÐSYNLEGT: scraper.listings er læst anon en eignasíðan keyrir á anon-client. Sama þrönga sýnigat og v_leit_listings (cc2).';

DROP TABLE public.eign_myndir_augl;
