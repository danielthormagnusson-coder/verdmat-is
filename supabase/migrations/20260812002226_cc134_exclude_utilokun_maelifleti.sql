-- cc134 KOSTUR (c) — EXCLUDE UNDANSKILIÐ Á MÆLIFLÖTUNUM
-- ============================================================================
-- ÓAPPLÝJUÐ. Þessi skrá er HÖNNUN, skrifuð á diski og bókuð; hún hefur EKKI
-- verið keyrð gegnum Supabase MCP `apply_migration`. HALT fyrir framkvæmd.
--
-- SAMHENGI (mælt cc134, 12.08.2026, read-only — sjá
-- docs/fable_prep/audits/EXCLUDE_VERDMATSLEID_CC134_20260812T0006Z.md):
--
--   Nætur-vélin frysti verðmöt á flokki sem líkanið var ALDREI þjálfað á.
--   `training_data_v2.pkl` (sha256[:16] 32f9a1242b212d11 = manifest lifandi
--   líkans) ber 0 EXCLUDE-raðir af 146.841; `canonical_code` er Categorical
--   með 12 flokkum sem EXCLUDE er ekki í, svo hann varpast í NaN við skorun.
--   Talan er ekki mat á atvinnuhúsnæði — að þvinga flokkinn í APT_FLOOR færir
--   hana um 3,10 prósent að meðaltali.
--
--   Borðið valdi (a)+(c) 12.08:
--     (a) SÍA FRAMVEGIS  -> scripts/extraction_engine.py
--                           (`AND pr.canonical_code <> 'EXCLUDE'`), LOKIÐ.
--     (c) ÞESSI SKRÁ     -> mæliflötunum er hlíft við menguninni.
--     (b) HREINSUN GAMLA -> FELLD. Þær 2.372 raðir sem fyrir eru STANDA. Þær
--                           eru söguleg heimild um hvað vélin sagði, sömu rök
--                           og cc116 fyrir 20.642 sögulegu raðirnar.
--                           ÞESS VEGNA er (c) til: gögnin standa, mælingin
--                           verður hrein.
--
-- MÆLD ÁHRIF (12.08, á lifandi gögnum):
--
--   scraper.v_expected_vs_real       23.605 -> 21.233 raðir
--     base_pct_error bjagi (n=206)   +8,22  -> +6,06 prósent   (2,16 pp)
--     MAPE                           15,50  -> 13,56 prósent   (1,94 pp)
--     sama á eignastigi (n=82)       +5,46  -> +3,16 prósent   (2,30 pp)
--     extraction_gap meðaltal        +0,2721 -> +0,4927 M kr   (+81 prósent)
--
--   ops_scraper_signals()
--     total_valuations               23.605 -> 21.233
--     val_count_latest_day            2.000 ->  1.821
--     backlog.live_res_sale          11.944 -> 11.792
--     backlog.live_res_sale_valued    4.199 ->  4.156
--     backlog.unprocessed             7.745 ->  7.636
--
--   Samlagningin heldur: 11.792 = 4.156 + 7.636. Backlog-teljararnir ÞRÍR fá
--   sömu síu, ekki einn þeirra — annars hættir spjaldið að stemma við sjálft sig.
--   `unprocessed` -109 er nákvæmlega VARANLEGA GÓLFIÐ sem kostur (a) hefði
--   annars skilið eftir: 109 auglýsingar sem vélin sækir aldrei framar og sem
--   spjaldið hefði talið sem ógert verk að eilífu. (a) og (c) loka hvor annarri.
--
-- ÚTILOKUNARSKILYRÐIÐ: `canonical_code IS DISTINCT FROM 'EXCLUDE'`.
--   * Borðið valdi S1-orðalagið. Mælt cc134: S1 og S2
--     (`NOT (is_residential OR is_summerhouse)`) eru SAMA MENGIÐ — 0 frávik af
--     232.887 eignum — svo línan má lesast sem hvort tveggja.
--   * `IS DISTINCT FROM` en ekki `<>`, öfugt við Python-síuna. Þar er INNER JOIN
--     á properties og röð án eignar kemst aldrei að; hér er LEFT JOIN og röð án
--     eignar Á að lifa. Þær eru annar liður (cc130 §5d: 717 canonical-auglýsingar
--     bera engan fastnum og ná hvorki verðmati né brú) og mega ekki hverfa
--     hljóðlaust inn í þessa síu. Mælt í dag: 0 raðir í sýninni eru án eignar,
--     svo greinin bítur ekki enn — hún er þarna svo hún bíti rétt þegar hún gerir.
--
-- ROLLBACK: supabase/rollback/20260812002226_cc134_exclude_utilokun_maelifleti_rollback.sql
-- ============================================================================


-- ── 1. ÓSÍAÐA HEIMILDIN ─────────────────────────────────────────────────────
-- Sami líkami og v_expected_vs_real hafði fyrir cc134, með TVEIMUR viðbótum:
-- LEFT JOIN á properties og `canonical_code` aftast. Þetta er heimildarflöturinn
-- — hann ber áfram allar 23.605 raðirnar, líka EXCLUDE. Kostur (b) var felldur
-- af því að sagan á að standa; hún á þá líka að vera SÝNILEG, ekki bara geymd.
-- Hér er líka eina staðsetningin þar sem `canonical_code` er til reiðu fyrir
-- lagskipta mælingu — það vantaði í cc120 og var ástæðan fyrir að EXCLUDE-halinn
-- sást ekki þá.
CREATE OR REPLACE VIEW scraper.v_expected_vs_real_all AS
SELECT
  val.valuation_id,
  val.fastnum,
  val.source_listing_id,
  val.lysing_hash,
  val.expected_base,
  val.expected_extraction,
  (val.expected_extraction - val.expected_base)                        AS extraction_gap,
  val.extraction_applied,
  val.model_version,
  val.valued_at,
  l.unit_key, l.category, l.tenure, l.sub_type, l.size_sqm, l.byggar, l.addr_text,
  l.price_amount                                                       AS asking_price,
  ext.extraction, ext.extraction_schema_version, ext.extraction_model,
  u.n_relistings, u.days_on_market, u.first_listed_at, u.last_seen_at,
  s.kaupverd_nominal                                                   AS real_price,
  s.thinglystdags                                                      AS sold_at,
  (s.fastnum IS NOT NULL)                                              AS sold,
  CASE WHEN s.kaupverd_nominal > 0 AND val.expected_base IS NOT NULL
       THEN (val.expected_base - s.kaupverd_nominal)::numeric / s.kaupverd_nominal END
                                                                       AS base_pct_error,
  CASE WHEN s.kaupverd_nominal > 0 AND val.expected_extraction IS NOT NULL
       THEN (val.expected_extraction - s.kaupverd_nominal)::numeric / s.kaupverd_nominal END
                                                                       AS extraction_pct_error,
  to_char(s.thinglystdags, 'YYYY-MM')                                  AS sale_ym,
  ci.cpi                                                               AS cpi_at_sale,
  ph.price_trajectory,
  -- cc134 VIÐBÓT: eignaflokkurinn sem skorunin réðst af.
  pr.canonical_code
FROM scraper.listing_valuations val
LEFT JOIN scraper.listings l
       ON l.source = 'mbl' AND l.source_listing_id = val.source_listing_id
LEFT JOIN scraper.listing_extractions ext ON ext.lysing_hash = val.lysing_hash
LEFT JOIN scraper.v_units u ON u.unit_key = l.unit_key
-- cc134: LEFT, ekki INNER. Röð án eignar á að lifa af í heimildarfletinum.
LEFT JOIN public.properties pr ON pr.fastnum = val.fastnum
LEFT JOIN LATERAL (
  SELECT s2.fastnum, s2.kaupverd_nominal, s2.thinglystdags
  FROM public.sales_history s2
  WHERE s2.fastnum = val.fastnum
    AND s2.onothaefur = 0
    AND s2.thinglystdags >= val.valued_at::date
  ORDER BY s2.thinglystdags ASC
  LIMIT 1
) s ON true
LEFT JOIN public.cpi_index ci ON ci.year_month = to_char(s.thinglystdags, 'YYYY-MM')
LEFT JOIN LATERAL (
  SELECT jsonb_agg(jsonb_build_object('observed_at', p.observed_at,
                                      'price', p.price_amount)
                   ORDER BY p.observed_at) AS price_trajectory
  FROM scraper.listing_price_history p
  JOIN scraper.listings l3 ON l3.source = p.source
                          AND l3.source_listing_id = p.source_listing_id
  WHERE l3.unit_key = l.unit_key
) ph ON true;

COMMENT ON VIEW scraper.v_expected_vs_real_all IS
  'cc134: ÓSÍAÐA heimildin — allar raðir listing_valuations, líka EXCLUDE. '
  'Notaðu v_expected_vs_real fyrir MÆLINGAR; þessa fyrir sögu og þekjumat.';


-- ── 2. MÆLIFLÖTURINN ────────────────────────────────────────────────────────
-- CREATE OR REPLACE heldur nafninu, dálkaröðinni og öllum 33 dálkunum óbreyttum
-- og bætir `canonical_code` AFTAST (Postgres leyfir aðeins viðbót í enda —
-- þess vegna er nýi dálkurinn síðastur í heimildarsýninni að ofan).
--
-- ÞETTA ER LIÐURINN SEM SKIPTIR MÁLI. Mælt cc134: cc120-talan (+7,84 prósent,
-- §3.2) var HREIN — en hrein FYRIR TILVILJUN, ekki að hönnun. Sá nefnari
-- krafðist tengingar við public.predictions_2026_04 til að endurheimta
-- samfrysta meðaltalið, og spátöflurnar bera 0 EXCLUDE-eignir, svo öll sex
-- seldu EXCLUDE-röðin féllu út af sjálfum sér. Sá sem spyr sýnina BEINT —
-- `select avg(base_pct_error) from scraper.v_expected_vs_real`, augljósasta
-- leiðin og sú sem næsta lota fer — fékk +8,22. Eftir þessa breytingu fær hann
-- +6,06 án þess að þurfa að vita neitt af þessu. Sían sem þarf að MUNA eftir er
-- ekki sía; hún er minnisatriði sem bíður eftir að gleymast.
CREATE OR REPLACE VIEW scraper.v_expected_vs_real AS
SELECT *
FROM scraper.v_expected_vs_real_all
WHERE canonical_code IS DISTINCT FROM 'EXCLUDE';

COMMENT ON VIEW scraper.v_expected_vs_real IS
  'cc134: MÆLIFLÖTUR — EXCLUDE undanskilið (líkanið var aldrei þjálfað á '
  'flokknum; mengaði base_pct_error um 2,16 pp og extraction_gap um 45 prósent). '
  'Raðirnar sjálfar standa í töflunni og sjást í v_expected_vs_real_all.';


-- ── 3. GRANTS ───────────────────────────────────────────────────────────────
-- scraper-skemað er ekki opið PostgREST og v_expected_vs_real ber engin grants
-- nema eiganda (mælt cc134: aðeins `postgres`). Nýja sýnin á að erfa sama
-- ástand — sagt BERUM ORÐUM frekar en látið ráðast af default privileges,
-- skv. reglunni í CLAUDE.md.
REVOKE ALL ON scraper.v_expected_vs_real_all FROM anon, authenticated;


-- ── 4. /ops TELJARARNIR ─────────────────────────────────────────────────────
-- Óbreytt frá 20260628093000_ops_scraper_signals.sql NEMA fjórir teljarar sem
-- snerta listing_valuations + þrír backlog-teljarar. search_path='' stendur, svo
-- hvert nafn er fullkvalifíserað.
--
-- BÓKAÐ ÓSAMRÆMI SEM ÞESSI BREYTING LAGAR EKKI: backlog-teljararnir lykla á
-- `listings_canonical.category` (AUGLÝSINGAflokk) meðan verðmatið ræðst af
-- `properties.canonical_code` (EIGNAflokki). Þess vegna eru aðeins 109
-- EXCLUDE-raðir í backloginu en 2.093 í verðmats-biðröðinni — tvær ólíkar
-- skilgreiningar á „íbúð" á sama spjaldi. Sían hér er á EIGNAflokknum í öllum
-- sjö teljurunum, svo þeir verða innbyrðis samkvæmir; sjálft lyklunar-ósamræmið
-- er sér liður á PLANNING_BACKLOG (cc134 §5.3).
CREATE OR REPLACE FUNCTION public.ops_scraper_signals()
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT jsonb_build_object(
    'chain', jsonb_build_object(
      'mbl_last_seen',           (SELECT max(last_seen_at) FROM scraper.listings WHERE source::text = 'mbl'),
      'myigloo_last_seen',       (SELECT max(last_seen_at) FROM scraper.listings WHERE source::text = 'myigloo'),
      'canonical_last_promoted', (SELECT max(last_promoted_at) FROM scraper.listings_canonical),
      'price_history_max',       (SELECT max(observed_at) FROM scraper.listing_price_history),
      'extraction_max',          (SELECT max(extracted_at) FROM scraper.listing_extractions),
      -- cc134: ferskleikinn er ÓSÍAÐUR af ásettu ráði. Hann svarar „keyrði vélin
      -- í nótt", ekki „hvað skrifaði hún" — sía hér myndi láta ferska nótt líta
      -- út fyrir að vera stöðnuð ef hún skrifaði engar íbúðarraðir.
      'valuation_max',           (SELECT max(valued_at) FROM scraper.listing_valuations)
    ),
    'extraction', (
      SELECT jsonb_build_object(
        'count_latest_day', (
          SELECT count(*) FROM scraper.listing_extractions
          WHERE extracted_at >= date_trunc('day', (SELECT max(extracted_at) FROM scraper.listing_extractions))),
        'val_count_latest_day', (
          SELECT count(*) FROM scraper.listing_valuations v
          LEFT JOIN public.properties pr ON pr.fastnum = v.fastnum
          WHERE pr.canonical_code IS DISTINCT FROM 'EXCLUDE'          -- cc134
            AND v.valued_at >= date_trunc('day', (SELECT max(valued_at) FROM scraper.listing_valuations))),
        'model',             e.extraction_model,
        'schema_version',    e.extraction_schema_version,
        'total_extractions', (SELECT count(*) FROM scraper.listing_extractions),
        'total_valuations',  (
          SELECT count(*) FROM scraper.listing_valuations v
          LEFT JOIN public.properties pr ON pr.fastnum = v.fastnum
          WHERE pr.canonical_code IS DISTINCT FROM 'EXCLUDE')         -- cc134
      )
      FROM scraper.listing_extractions e
      ORDER BY e.extracted_at DESC NULLS LAST
      LIMIT 1
    ),
    'backlog', jsonb_build_object(
      -- cc134: sama sía á ÖLLUM ÞREMUR, svo live_res_sale = valued + unprocessed
      -- haldi. Mælt 12.08: 11.792 = 4.156 + 7.636.
      'live_res_sale', (
        SELECT count(*) FROM scraper.listings_canonical c
        LEFT JOIN public.properties pr ON pr.fastnum = c.fastnum
        WHERE c.category::text = 'residential' AND c.tenure::text = 'sale' AND c.withdrawn_at IS NULL
          AND pr.canonical_code IS DISTINCT FROM 'EXCLUDE'),
      'live_res_sale_valued', (
        SELECT count(DISTINCT c.canonical_id)
        FROM scraper.listings_canonical c
        JOIN scraper.listing_valuations v ON v.source_listing_id = c.source_listing_id
        LEFT JOIN public.properties pr ON pr.fastnum = c.fastnum
        WHERE c.category::text = 'residential' AND c.tenure::text = 'sale' AND c.withdrawn_at IS NULL
          AND pr.canonical_code IS DISTINCT FROM 'EXCLUDE'),
      'unprocessed', (
        SELECT count(*) FROM scraper.listings_canonical c
        LEFT JOIN public.properties pr ON pr.fastnum = c.fastnum
        WHERE c.category::text = 'residential' AND c.tenure::text = 'sale' AND c.withdrawn_at IS NULL
          AND pr.canonical_code IS DISTINCT FROM 'EXCLUDE'
          AND NOT EXISTS (SELECT 1 FROM scraper.listing_valuations v WHERE v.source_listing_id = c.source_listing_id))
    ),
    'sources', jsonb_build_object(
      'mbl',            (SELECT count(*) FROM scraper.listings_canonical WHERE source::text = 'mbl'),
      'myigloo',        (SELECT count(*) FROM scraper.listings_canonical WHERE source::text = 'myigloo'),
      'visir',          (SELECT count(*) FROM scraper.listings_canonical WHERE source::text = 'visir'),
      'live',           (SELECT count(*) FROM scraper.listings_canonical WHERE withdrawn_at IS NULL),
      'withdrawn',      (SELECT count(*) FROM scraper.listings_canonical WHERE withdrawn_at IS NOT NULL),
      'total',          (SELECT count(*) FROM scraper.listings_canonical),
      'fastnum_filled', (SELECT count(*) FROM scraper.listings_canonical WHERE fastnum IS NOT NULL)
    ),
    'generated_at', now()
  );
$$;

REVOKE ALL ON FUNCTION public.ops_scraper_signals() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ops_scraper_signals() TO service_role;
