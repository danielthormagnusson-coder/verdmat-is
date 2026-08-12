-- ROLLBACK · cc140 MIÐSÆKNIS-ALDAMERKING Á MÆLIFLÖTUNUM
-- ============================================================================
-- Endurheimtir ástandið eins og það var 12.08.2026 kl. 11:31Z, þ.e. útgáfurnar
-- sem cc134 skildi eftir:
--   supabase/migrations/20260812002226_cc134_exclude_utilokun_maelifleti.sql
-- BÁÐAR afritaðar hér ÚR LIFANDI DB (`pg_get_viewdef(..., true)`, lesið
-- 12.08 kl. 11:2xZ, ÁÐUR en cc140 var applýjað), ekki endursagðar eftir minni.
--
-- ENGIN GÖGN ERU Í HÚFI. cc140-migrationin snertir enga töflu og enga röð —
-- hún bætir EINUM reiknuðum dálki (`midsaekni_old`) við tvær sýnur. Dálkurinn
-- er ekki geymdur: hann er `CASE` á `val.valued_at`. Kóðabreytingin í
-- `scripts/extraction_engine.py` er SJÁLFSTÆÐ og þessi skrá bakkar hana EKKI —
-- sé hún bökkuð líka verður að færa línurnar tvær aftur á `real_pred_median`
-- OG þá er þessi merking marklaus hvort sem er.
--
-- ATH. RÖÐIN. `v_expected_vs_real` (barnið) verður að fara á undan
-- `v_expected_vs_real_all` — DROP á foreldrinu fellur annars á dependency.
-- CREATE OR REPLACE getur ekki FJARLÆGT dálk, svo DROP + CREATE er eina leiðin
-- til baka. Mælt 12.08: ekkert object er skilgreint ofan á `v_expected_vs_real`
-- (pg_depend/pg_rewrite: aðeins hún sjálf) og hvorug sýnin ber grants nema
-- eiganda, svo DROP er staðbundið.
-- ============================================================================

-- ── 1. barnið burt (það á að endurskapast í skrefi 3) ───────────────────────
DROP VIEW IF EXISTS scraper.v_expected_vs_real;

-- ── 2. foreldrið aftur í 34 dálka (cc134-útgáfan, orðrétt úr DB) ────────────
DROP VIEW IF EXISTS scraper.v_expected_vs_real_all;

CREATE VIEW scraper.v_expected_vs_real_all AS
SELECT
  val.valuation_id,
  val.fastnum,
  val.source_listing_id,
  val.lysing_hash,
  val.expected_base,
  val.expected_extraction,
  val.expected_extraction - val.expected_base AS extraction_gap,
  val.extraction_applied,
  val.model_version,
  val.valued_at,
  l.unit_key,
  l.category,
  l.tenure,
  l.sub_type,
  l.size_sqm,
  l.byggar,
  l.addr_text,
  l.price_amount AS asking_price,
  ext.extraction,
  ext.extraction_schema_version,
  ext.extraction_model,
  u.n_relistings,
  u.days_on_market,
  u.first_listed_at,
  u.last_seen_at,
  s.kaupverd_nominal AS real_price,
  s.thinglystdags AS sold_at,
  s.fastnum IS NOT NULL AS sold,
  CASE
    WHEN s.kaupverd_nominal > 0 AND val.expected_base IS NOT NULL
      THEN (val.expected_base - s.kaupverd_nominal)::numeric / s.kaupverd_nominal::numeric
    ELSE NULL::numeric
  END AS base_pct_error,
  CASE
    WHEN s.kaupverd_nominal > 0 AND val.expected_extraction IS NOT NULL
      THEN (val.expected_extraction - s.kaupverd_nominal)::numeric / s.kaupverd_nominal::numeric
    ELSE NULL::numeric
  END AS extraction_pct_error,
  to_char(s.thinglystdags::timestamp with time zone, 'YYYY-MM'::text) AS sale_ym,
  ci.cpi AS cpi_at_sale,
  ph.price_trajectory,
  pr.canonical_code
FROM scraper.listing_valuations val
  LEFT JOIN scraper.listings l ON l.source = 'mbl'::text AND l.source_listing_id = val.source_listing_id
  LEFT JOIN scraper.listing_extractions ext ON ext.lysing_hash = val.lysing_hash
  LEFT JOIN scraper.v_units u ON u.unit_key = l.unit_key
  LEFT JOIN properties pr ON pr.fastnum = val.fastnum
  LEFT JOIN LATERAL (
    SELECT s2.fastnum, s2.kaupverd_nominal, s2.thinglystdags
    FROM sales_history s2
    WHERE s2.fastnum = val.fastnum AND s2.onothaefur = 0 AND s2.thinglystdags >= val.valued_at::date
    ORDER BY s2.thinglystdags
    LIMIT 1) s ON true
  LEFT JOIN cpi_index ci ON ci.year_month = to_char(s.thinglystdags::timestamp with time zone, 'YYYY-MM'::text)
  LEFT JOIN LATERAL (
    SELECT jsonb_agg(jsonb_build_object('observed_at', p.observed_at, 'price', p.price_amount)
                     ORDER BY p.observed_at) AS price_trajectory
    FROM scraper.listing_price_history p
      JOIN scraper.listings l3 ON l3.source = p.source AND l3.source_listing_id = p.source_listing_id
    WHERE l3.unit_key = l.unit_key) ph ON true;

COMMENT ON VIEW scraper.v_expected_vs_real_all IS
  'cc134: ÓSÍAÐA heimildin — allar raðir listing_valuations, líka EXCLUDE. '
  'Notaðu v_expected_vs_real fyrir MÆLINGAR; þessa fyrir sögu og þekjumat.';

-- ── 3. barnið aftur (cc134-útgáfan, 34 dálkar, EXCLUDE-síuð) ────────────────
CREATE VIEW scraper.v_expected_vs_real AS
SELECT
  valuation_id, fastnum, source_listing_id, lysing_hash,
  expected_base, expected_extraction, extraction_gap, extraction_applied,
  model_version, valued_at, unit_key, category, tenure, sub_type, size_sqm,
  byggar, addr_text, asking_price, extraction, extraction_schema_version,
  extraction_model, n_relistings, days_on_market, first_listed_at, last_seen_at,
  real_price, sold_at, sold, base_pct_error, extraction_pct_error, sale_ym,
  cpi_at_sale, price_trajectory, canonical_code
FROM scraper.v_expected_vs_real_all
WHERE canonical_code IS DISTINCT FROM 'EXCLUDE'::text;

COMMENT ON VIEW scraper.v_expected_vs_real IS
  'cc134: MÆLIFLÖTURINN. EXCLUDE-raðir undanskildar — líkanið var aldrei '
  'þjálfað á þeim flokki, svo tölur þeirra eru ekki mælanleg spávilla. '
  'Raðirnar sjálfar standa í töflunni og sjást í v_expected_vs_real_all.';

-- ── 4. réttindin aftur (cc105-reglan: mæla á pg_class.relacl, ekki i_s) ─────
REVOKE ALL ON scraper.v_expected_vs_real_all FROM anon, authenticated;
REVOKE ALL ON scraper.v_expected_vs_real     FROM anon, authenticated;
