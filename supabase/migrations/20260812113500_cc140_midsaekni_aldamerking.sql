-- cc140 — MIÐSÆKNIS-ALDAMERKING Á MÆLIFLÖTUNUM
-- APPLÝJAÐ 2026-08-12 kl. 11:36Z gegnum SUPABASE MCP `apply_migration`.
--
-- RÁSIN VAR MCP. Ólíkt cc134 (12.08 kl. 10:07Z, sem varð að nota psycopg2 gegn
-- þremur skilyrðum af því að `apply_migration` var ótengt) var MCP tengt í
-- þessari lotu. MCP skrifar `schema_migrations`-færsluna sjálfkrafa í sömu txn
-- og stæðuna, svo skilyrði (1) og (2) úr cc134 eru sjálfgefin hér. Skilyrði (3)
-- stendur eftir sem regla og er uppfyllt: ÞESSI SKRÁ ER SPEGILL, sóttur orðrétt
-- úr `supabase_migrations.schema_migrations.statements`.
--
-- ⚠ VERSION-NÚMERIN ERU EKKI ÞAU SEM DRÖGIN SPÁÐU. MCP úthlutar version af
--   eigin klukku; drögin (sha256[:16] d31530a53a19415f) gerðu ráð fyrir
--   20260812113500..113506 og SJÖ stæðum. Raunin er 20260812113529..113631 og
--   ÁTTA stæður. Áttunda stæðan (`cc140_03b`) er leiðrétting: stæða 03 var
--   applýjuð með afmáðum íslenskum stöfum af óþarfa varkárni (stæður 01-02 báru
--   íslensku athugasemdalaust), og 03b skrifar réttan texta yfir. Stæða 03 er
--   EKKI fjarlægð — hún var keyrð og á að sjást. Það er munurinn á spegli og
--   endurritun.
--
-- SAMHENGI. `scripts/extraction_engine.py` frystir `expected_base` /
-- `expected_extraction` á `real_pred_mean` frá og með 12.08.2026 (cc140,
-- framkvæmd á §5D-1 / cc123 kostur (a)). Frá 27.06.2026 til þess dags frysti
-- hún `real_pred_median`.
--
-- GÖMLU RAÐIRNAR STANDA. 23.605 raðir eru EKKI endurritaðar (kostur (b)
-- felldur; sömu rök og cc116 fyrir 20.642 sögulegu raðirnar og cc134-b fyrir
-- 2.372 EXCLUDE-raðirnar: frysta talan er söguleg heimild um hvað vélin sagði,
-- ekki endursögn). Taflan ber því TVÆR ALDIR og þessi migration er svarið við
-- því: hún gerir öldina SÝNILEGA á mæliflötunum í stað þess að fela hana.
--
-- ALDAMÖRKIN ERU MÆLD, EKKI ÁLYKTUÐ:
--   síðasta median-röðin      2026-08-08 03:33:24.343465+00
--   aldamörk                  2026-08-12 00:00:00+00
--   raðir á milli             0   (mælt 12.08 kl. 11:31Z)
-- Bilið er 3,9 sólarhringar með ENGRI röð — verðmats-þrepið er í pásu
-- (`--skip-valuation`, cc121) — svo engin röð getur lent á rangri öld.
--
-- DÁLKURINN ER REIKNAÐUR, EKKI GEYMDUR. `midsaekni_old` er `CASE` á
-- `val.valued_at`. Engin röð er snert, engin tafla breytist, ekkert er afritað.
-- Sé aldamörkunum einhvern tíma breytt verður að breyta ÞEIM Á BÁÐUM STÖÐUM —
-- hér og í athugasemdinni við `value_listings` í `scripts/extraction_engine.py`
-- — annars merkir mæliflöturinn ranga öld.
--
-- ⚠ AÐVÖRUN SEM FYLGIR DÁLKNUM (7.9-reglan). `base_pct_error`,
--   `extraction_pct_error` og /markadur-vísirinn eru ÓSAMBÆRILEG yfir
--   aldamörkin. Meðaltal yfir blandað mengi er ekki mæling heldur blanda af
--   tveimur mælingum. `mean`-höfuðið ber +1,93 prósent þekktan OOS-bjaga
--   (undir söluverði; t = -10,74, p = 1,75e-25, cc123 §1) og sú tala á að
--   fylgja hverri umfjöllun um nákvæmni þessarar töflu.
--
-- EFTIRMÆLING (12.08 kl. 11:37Z, mæld á sýnunum sjálfum eftir apply):
--   v_expected_vs_real_all   35 dálkar · midsaekni_old í sæti 35
--                            median 23.605 raðir (259 seldar) · mean 0
--   v_expected_vs_real       35 dálkar · midsaekni_old í sæti 35
--                            median 21.233 raðir (252 seldar) · mean 0
--   Rowcountin standa óbreytt frá cc134 — sem er sönnun þess að viðbótin er
--   dálkur en ekki sía.
--
-- RÉTTINDI mæld á `pg_class.relacl` + `aclexplode` (cc105-reglan; grantor og
-- PUBLIC-grants sjást hvergi í information_schema):
--   scraper.v_expected_vs_real_all   {postgres=arwdDxtm/postgres}
--   scraper.v_expected_vs_real       {postgres=arwdDxtm/postgres}
--   aclexplode: anon / authenticated / PUBLIC bera EKKERT (0 raðir).
--   ATH. `v_expected_vs_real` bar ENGA skráða relacl eftir cc134 (erfði
--   eiganda); CREATE OR REPLACE + REVOKE efnisgerði hana. Efnislega óbreytt —
--   anon/authenticated báru ekkert fyrir og bera ekkert eftir.
--
-- ROLLBACK: supabase/rollback/20260812113500_cc140_midsaekni_aldamerking_rollback.sql
--           (sha256[:16] e38ee587587d7a7f, skrifað FYRIR apply, ósnert síðan)
-- Ákvörðun: DECISIONS §5D-4 (framkvæmd §5D-1 / cc123)
-- ============================================================================


-- ── 20260812113529  cc140_01_v_expected_vs_real_all_ald ─────────────────────────
CREATE OR REPLACE VIEW scraper.v_expected_vs_real_all AS
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
  pr.canonical_code,
  -- cc140 ALDAMERKINGIN. Reiknuð af stimplinum, ekki geymd. valued_at er
  -- NOT NULL í töflunni, svo greinarnar tvær eru tæmandi og enginn þriðji
  -- flokkur (NULL) getur laumast inn.
  CASE
    WHEN val.valued_at < TIMESTAMPTZ '2026-08-12 00:00:00+00' THEN 'median'
    ELSE 'mean'
  END AS midsaekni_old
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


-- ── 20260812113538  cc140_02_v_expected_vs_real_ald ─────────────────────────────
CREATE OR REPLACE VIEW scraper.v_expected_vs_real AS
SELECT
  valuation_id, fastnum, source_listing_id, lysing_hash,
  expected_base, expected_extraction, extraction_gap, extraction_applied,
  model_version, valued_at, unit_key, category, tenure, sub_type, size_sqm,
  byggar, addr_text, asking_price, extraction, extraction_schema_version,
  extraction_model, n_relistings, days_on_market, first_listed_at, last_seen_at,
  real_price, sold_at, sold, base_pct_error, extraction_pct_error, sale_ym,
  cpi_at_sale, price_trajectory, canonical_code, midsaekni_old
FROM scraper.v_expected_vs_real_all
WHERE canonical_code IS DISTINCT FROM 'EXCLUDE'::text;


-- ── 20260812113546  cc140_03_comment_col_all ────────────────────────────────────
COMMENT ON COLUMN scraper.v_expected_vs_real_all.midsaekni_old IS
  'cc140: hvor midsaeknin var fryst i expected_base/expected_extraction. median = valued_at < 2026-08-12 (27.06-12.08.2026, real_pred_median); mean = fra og med theim stimpli (real_pred_mean, DECISIONS 5D-4). Reiknad af valued_at, ekki geymt. Gomlu radirnar voru EKKI endurritadar.';


-- ── 20260812113558  cc140_03b_comment_col_all_islenska ──────────────────────────
-- cc140 03b: stæða 03 var applýjuð með afmáðum íslenskum stöfum af óþarfa
-- varkárni. Þessi stæða skrifar réttan texta yfir. Stæða 03 er ekki fjarlægð
-- úr schema_migrations — hún var keyrð og á að sjást.
COMMENT ON COLUMN scraper.v_expected_vs_real_all.midsaekni_old IS
  'cc140: hvor miðsæknin var fryst í expected_base/expected_extraction. median = valued_at < 2026-08-12 (27.06-12.08.2026, real_pred_median); mean = frá og með þeim stimpli (real_pred_mean, DECISIONS §5D-4). Reiknað af valued_at, ekki geymt. Gömlu raðirnar voru EKKI endurritaðar.';


-- ── 20260812113606  cc140_04_comment_col_sia ────────────────────────────────────
COMMENT ON COLUMN scraper.v_expected_vs_real.midsaekni_old IS
  'cc140: sjá v_expected_vs_real_all.midsaekni_old. AÐVÖRUN: base_pct_error og extraction_pct_error eru ÓSAMBÆRILEG yfir aldamörkin — meðaltal yfir blandað mengi er blanda tveggja mælinga, ekki mæling. GROUP BY þennan dálk.';


-- ── 20260812113615  cc140_05_comment_view_all ───────────────────────────────────
COMMENT ON VIEW scraper.v_expected_vs_real_all IS
  'cc134: ÓSÍAÐA heimildin — allar raðir listing_valuations, líka EXCLUDE. Notaðu v_expected_vs_real fyrir MÆLINGAR; þessa fyrir sögu og þekjumat. cc140: ber midsaekni_old (dálkur 35) — taflan geymir TVÆR miðsæknis-aldir og villuhlutföllin eru ósambærileg yfir aldamörkin 2026-08-12.';


-- ── 20260812113625  cc140_06_comment_view_sia ───────────────────────────────────
COMMENT ON VIEW scraper.v_expected_vs_real IS
  'cc134: MÆLIFLÖTURINN. EXCLUDE-raðir undanskildar — líkanið var aldrei þjálfað á þeim flokki, svo tölur þeirra eru ekki mælanleg spávilla. Raðirnar sjálfar standa í töflunni og sjást í v_expected_vs_real_all. cc140: ber midsaekni_old — SÍAÐU EÐA HÓPAÐU á hann áður en bjagi eða MAPE er lesin; mean-öldin ber +1,93 prósent þekktan OOS-bjaga (cc123 §1).';


-- ── 20260812113631  cc140_07_revoke_syn ─────────────────────────────────────────
REVOKE ALL ON scraper.v_expected_vs_real_all FROM anon, authenticated;
REVOKE ALL ON scraper.v_expected_vs_real     FROM anon, authenticated;
