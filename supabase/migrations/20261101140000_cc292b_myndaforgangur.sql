-- cc292b (01.11.2026) — forgangur mynda á eignasíðu. GO Danna 01.11 (framhald 2), liður 1.
-- Skil: D:\_audit\cc292_myndir\SKIL_CC292.md §7
--
-- Áður (cc23 → cc292): safnið (property_images) hafði ALLTAF forgang. Eign á sölu í dag með
-- evalue-safn frá 2018 sýndi 2018-myndirnar (með ártalsmerki) en ekki myndir lifandi auglýsingar.
-- Nú: EITT myndasett per eign, valið svona:
--   1. lifandi (status='active') auglýsing með myndum — nýjust fyrst;
--   2. annars safnið (property_images);
--   3. annars óvirk auglýsing með myndum (R1, cc292) — nýjust fyrst.
-- FRÁVIK frá forskrift („nýrra safn á undan eldra“ líka fyrir óvirkar auglýsingar): mælt í --prof
-- að 1.940 eignir færu þá úr safni í ÓVIRKA auglýsingu, 1.289 þeirra mbl (withdrawn), og 7/19 mbl
-- í HEAD-úrtaki skila 404 (mbl harð-eyðir). Það skipti virkum myndum út fyrir brotnar. Óvirkar
-- auglýsingar víkja því áfram fyrir safni — HALT, D:\_audit\cc292_myndir\SKIL_CC292.md §7.
-- Sett eru aldrei blönduð innan eignar. Dálkar og réttindi óbreytt (CREATE OR REPLACE).
-- `valin` er NOT MATERIALIZED: henni er vísað tvisvar, og efnisgerð CTE hleypir ekki fastnum-síu
-- niður (mælt í --prof: 60 s á eign í stað ~5 ms).
-- Ártalsmerkið (augl_dags eldri en 2 ár) birtist þá ekki á eign sem er auglýst með myndum í dag.
SET TRANSACTION READ WRITE;

CREATE OR REPLACE VIEW public.v_eign_myndir AS
 WITH augl AS (
         SELECT l.fastnum,
            l.listing_id,
            l.photos_json,
            l.status = 'active'::text AS virk,
            COALESCE(l.first_seen_at, l.listed_at)::date AS augl_dags,
            l.listed_at,
            l.first_seen_at
           FROM scraper.listings l
          WHERE l.fastnum IS NOT NULL AND jsonb_typeof(l.photos_json) = 'array'::text
            AND jsonb_array_length(l.photos_json) > 0
        ), safn AS (
         SELECT pi.fastnum
           FROM property_images pi
          WHERE pi.utilokad_kl IS NULL AND NOT (EXISTS ( SELECT 1
                   FROM daudir_myndahyslar d
                  WHERE pi.url ~~* (('%'::text || d.hysill) || '%'::text)))
          GROUP BY pi.fastnum
        ), kandidatar AS (
         SELECT a.fastnum, a.listing_id, a.virk, a.augl_dags, false AS er_safn, a.listed_at, a.first_seen_at
           FROM augl a
        UNION ALL
         SELECT s.fastnum, NULL::bigint, false, e.augl_dags, true, NULL::timestamptz, NULL::timestamptz
           FROM safn s
             LEFT JOIN eign_myndir_augl e ON e.fastnum = s.fastnum
        ), valin AS NOT MATERIALIZED (
         SELECT DISTINCT ON (k.fastnum) k.fastnum, k.listing_id, k.er_safn, k.augl_dags
           FROM kandidatar k
          ORDER BY k.fastnum, k.virk DESC, k.er_safn DESC, k.augl_dags DESC NULLS LAST,
                   k.listed_at DESC NULLS LAST, k.first_seen_at DESC NULLS LAST, k.listing_id DESC
        ), sereind AS (
         SELECT v.fastnum,
            m.url,
            min(m.ord) AS ord,
            v.augl_dags
           FROM valin v
             JOIN scraper.listings l ON l.listing_id = v.listing_id
             CROSS JOIN LATERAL ( SELECT
                        CASE jsonb_typeof(el.value)
                            WHEN 'string'::text THEN el.value #>> '{}'::text[]
                            WHEN 'object'::text THEN COALESCE(el.value ->> 'small'::text, el.value ->> 'regular'::text, el.value ->> 'big'::text)
                            ELSE NULL::text
                        END AS url,
                    el.ord
                   FROM jsonb_array_elements(l.photos_json) WITH ORDINALITY el(value, ord)) m
          WHERE NOT v.er_safn AND m.url ~~ 'https://%'::text
          GROUP BY v.fastnum, m.url, v.augl_dags
        )
 SELECT pi.fastnum,
    pi.url,
    pi.img_order,
    'safn'::text AS uppruni,
    v.augl_dags
   FROM valin v
     JOIN property_images pi ON pi.fastnum = v.fastnum
  WHERE v.er_safn AND pi.utilokad_kl IS NULL
UNION ALL
 SELECT s.fastnum,
    s.url,
    row_number() OVER (PARTITION BY s.fastnum ORDER BY s.ord)::integer AS img_order,
    'auglysing'::text AS uppruni,
    s.augl_dags
   FROM sereind s;

COMMENT ON VIEW public.v_eign_myndir IS
  'Sameinað myndalag eignarsíðunnar (cc23 liður B5, cc292, cc292b). EITT myndasett per eign: (1) lifandi auglýsing með myndum, nýjust fyrst; (2) annars safnið (public.property_images, dags úr eign_myndir_augl); (3) annars óvirk auglýsing með myndum, nýjust fyrst (mbl-myndir horfinna auglýsinga deyja, cc292b). Aldrei blandað innan eignar. img_order er 1-BYGGT báðum megin. uppruni = safn|auglysing. augl_dags = dags auglýsingarinnar sem myndin kemur úr (NULL = óþekkt; þá ekkert ártalsmerki). SECURITY DEFINER (invoker=false) er NAUÐSYNLEGT: scraper.listings og eign_myndir_augl eru læst anon en eignasíðan keyrir á anon-client. Sama þrönga sýnigat og v_leit_listings (cc2).';
