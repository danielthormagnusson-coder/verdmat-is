-- cc292 (01.11.2026) — myndagat eignasíðna. GO Danna 01.11, liðir 1 og 5b.
-- Skil: D:\_audit\cc292_myndir\SKIL_CC292.md
--
-- 1. public.eign_myndir_augl: dagsetning auglýsingarinnar sem SAFNmyndir eignar komu úr
--    (evalue-farmur: hæsta dags auglýsinga eignarinnar sem bera ≥1 slóð hennar í property_images).
--    Lesin AÐEINS gegnum v_eign_myndir (SECURITY DEFINER-sýn, eigandi postgres). www les
--    töfluna aldrei beint, svo hún fær ENGIN réttindi til anon/authenticated (cc284-reglan).
-- 2. v_eign_myndir:
--    R1  auglýsingagreinin les líka ÓVIRKAR auglýsingar (127 eignir áttu myndir aðeins þar).
--        Virk auglýsing hefur forgang. Myndlaus auglýsing (tómt fylki) er ekki lengur valin
--        fram yfir eldri auglýsingu MEÐ myndum. Safnið hefur áfram forgang yfir auglýsingu.
--    5b  nýr dálkur augl_dags (date, aftast): dags auglýsingarinnar sem myndin kemur úr.
--        safn: eign_myndir_augl.augl_dags (NULL ef óþekkt); auglýsing: first_seen_at.
--    CREATE OR REPLACE heldur réttindum sýnarinnar (anon=r, authenticated=r) óbreyttum.
SET TRANSACTION READ WRITE;

CREATE TABLE public.eign_myndir_augl (
  fastnum    bigint PRIMARY KEY,
  augl_id    bigint,
  augl_dags  date NOT NULL CHECK (augl_dags >= DATE '2000-01-01' AND augl_dags <= DATE '2100-01-01'),
  heimild    text NOT NULL CHECK (heimild IN ('evalue_farmur', 'cc292_hledsla')),
  skrad_kl   timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.eign_myndir_augl ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.eign_myndir_augl FROM anon, authenticated;
COMMENT ON TABLE public.eign_myndir_augl IS
  'cc292: dags auglýsingar sem safnmyndir eignar (property_images) komu úr. Lesin aðeins um v_eign_myndir.augl_dags (ártalsmerki á myndum úr auglýsingu eldri en 2 ára). Engin anon/authenticated-réttindi; RLS án stefnu.';

CREATE OR REPLACE VIEW public.v_eign_myndir AS
 WITH fersk AS (
         SELECT DISTINCT ON (l.fastnum) l.fastnum,
            l.photos_json,
            COALESCE(l.first_seen_at, l.listed_at)::date AS augl_dags
           FROM scraper.listings l
          WHERE l.fastnum IS NOT NULL AND jsonb_typeof(l.photos_json) = 'array'::text
            AND jsonb_array_length(l.photos_json) > 0 AND NOT (EXISTS ( SELECT 1
                   FROM property_images pi2
                  WHERE pi2.fastnum = l.fastnum AND NOT (EXISTS ( SELECT 1
                           FROM daudir_myndahyslar d
                          WHERE pi2.url ~~* (('%'::text || d.hysill) || '%'::text)))))
          ORDER BY l.fastnum, (l.status = 'active'::text) DESC, l.listed_at DESC NULLS LAST, l.first_seen_at DESC NULLS LAST, l.listing_id DESC
        ), sereind AS (
         SELECT f.fastnum,
            m.url,
            min(m.ord) AS ord,
            f.augl_dags
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
          GROUP BY f.fastnum, m.url, f.augl_dags
        )
 SELECT pi.fastnum,
    pi.url,
    pi.img_order,
    'safn'::text AS uppruni,
    e.augl_dags
   FROM property_images pi
     LEFT JOIN eign_myndir_augl e ON e.fastnum = pi.fastnum
  WHERE pi.utilokad_kl IS NULL
UNION ALL
 SELECT s.fastnum,
    s.url,
    row_number() OVER (PARTITION BY s.fastnum ORDER BY s.ord)::integer AS img_order,
    'auglysing'::text AS uppruni,
    s.augl_dags
   FROM sereind s;

COMMENT ON VIEW public.v_eign_myndir IS
  'Sameinað myndalag eignarsíðunnar (cc23 liður B5). Brúar kyrrstæða safnið (public.property_images, hlaðið 2026-07-05, viðbót cc292 01.11) og auglýsingamyndir (scraper.listings.photos_json). Safnið hefur forgang; auglýsingamyndir birtast AÐEINS þegar safnið er tómt fyrir það fastnum — aldrei blandað innan eignar. cc292 R1: auglýsingagreinin les líka óvirkar auglýsingar (virk fyrst), aldrei myndlausa fram yfir myndbera. img_order er 1-BYGGT báðum megin. uppruni = safn|auglysing. augl_dags (cc292) = dags auglýsingarinnar sem myndin kemur úr (NULL = óþekkt; þá ekkert ártalsmerki). SECURITY DEFINER (invoker=false) er NAUÐSYNLEGT: scraper.listings og eign_myndir_augl eru læst anon en eignasíðan keyrir á anon-client. Sama þrönga sýnigat og v_leit_listings (cc2).';
