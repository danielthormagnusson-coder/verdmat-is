-- Extraction layer: content-addressed 108-field condition extraction + frozen extraction-
-- enhanced valuation snapshot + expected-vs-real monitoring view. ADDITIVE — touches nothing
-- existing (Lag 1 scraper.listings / listing_price_history / v_units and listings_canonical all
-- unchanged). RLS service-role-only on the tables (internal layer, holds derived listing data).
--
-- Design (locked, EXTRACTION-MIGRATION ÞREP 2):
--   * scraper.listing_extractions  : CONTENT-ADDRESSED on md5(lysing)[:12] — re-lists with the
--                                    same lysing share one extraction (one Haiku call serves all).
--   * scraper.listing_valuations   : FROZEN snapshot of expected_base vs expected_extraction at
--                                    valuation time — public.predictions is monthly-refreshed and
--                                    cannot reconstruct a historical expected.
--   * scraper.v_expected_vs_real   : deterministic monitoring join (frozen expected vs realized
--                                    sale), all context retained for downstream model research.

-- ───────────────────── content-addressed extraction (keyed on lysing hash) ─────────────────────
CREATE TABLE scraper.listing_extractions (
  lysing_hash               text PRIMARY KEY,          -- md5(lysing)[:12]; shared across re-lists
  extraction                jsonb NOT NULL,            -- 108-field v0.2.2 structure
  extraction_schema_version text NOT NULL,             -- e.g. 'v0.2.2'
  extraction_model          text NOT NULL,             -- e.g. 'claude-haiku-4-5'
  source_trigger            text NOT NULL
    CHECK (source_trigger IN ('seed_vel1', 'seed_april', 'nightly', 'ondemand')),
  lysing_len                integer,
  extracted_at              timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE scraper.listing_extractions ENABLE ROW LEVEL SECURITY;

-- ───────────────────── frozen valuation snapshot (per listing, per model) ─────────────────────
CREATE TABLE scraper.listing_valuations (
  valuation_id        bigserial PRIMARY KEY,
  fastnum             bigint,
  source_listing_id   text,
  lysing_hash         text,                            -- -> listing_extractions (loose link)
  expected_base       bigint,                          -- structured-only prediction (ISK, nominal)
  expected_extraction bigint,                          -- + extraction features (ISK, nominal)
  extraction_applied  boolean NOT NULL DEFAULT false,
  model_version       text NOT NULL,
  valued_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source_listing_id, model_version)            -- one frozen valuation per listing per model
);
CREATE INDEX ix_valuations_fastnum ON scraper.listing_valuations (fastnum);
CREATE INDEX ix_valuations_hash    ON scraper.listing_valuations (lysing_hash);
ALTER TABLE scraper.listing_valuations ENABLE ROW LEVEL SECURITY;

-- ───────────────────── expected-vs-real monitoring (deterministic VIEW) ─────────────────────
-- VIEW (not table): the only data that must be frozen — expected_base/expected_extraction at
-- valuation time — already lives frozen in listing_valuations; realized price comes from canonical
-- sales_history. Everything else is a deterministic join, like v_units. Materialize later only if
-- performance requires it. All context retained (full extraction jsonb + price trajectory) so a
-- future model can study what mattered without pre-judging it.
CREATE VIEW scraper.v_expected_vs_real AS
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
  -- listing context (Lag 1)
  l.unit_key, l.category, l.tenure, l.sub_type, l.size_sqm, l.byggar, l.addr_text,
  l.price_amount                                                       AS asking_price,
  -- full extraction (downstream decides which fields moved the valuation)
  ext.extraction, ext.extraction_schema_version, ext.extraction_model,
  -- unit-level dynamics
  u.n_relistings, u.days_on_market, u.first_listed_at, u.last_seen_at,
  -- realized sale (first thinglyst sale on this fastnum at/after valuation)
  s.kaupverd_nominal                                                   AS real_price,
  s.thinglystdags                                                      AS sold_at,
  (s.fastnum IS NOT NULL)                                              AS sold,
  CASE WHEN s.kaupverd_nominal > 0 AND val.expected_base IS NOT NULL
       THEN (val.expected_base - s.kaupverd_nominal)::numeric / s.kaupverd_nominal END
                                                                       AS base_pct_error,
  CASE WHEN s.kaupverd_nominal > 0 AND val.expected_extraction IS NOT NULL
       THEN (val.expected_extraction - s.kaupverd_nominal)::numeric / s.kaupverd_nominal END
                                                                       AS extraction_pct_error,
  -- market context at sale
  to_char(s.thinglystdags, 'YYYY-MM')                                  AS sale_ym,
  ci.cpi                                                               AS cpi_at_sale,
  -- full price trajectory of the unit (all-retained)
  ph.price_trajectory
FROM scraper.listing_valuations val
LEFT JOIN scraper.listings l
       ON l.source = 'mbl' AND l.source_listing_id = val.source_listing_id
LEFT JOIN scraper.listing_extractions ext ON ext.lysing_hash = val.lysing_hash
LEFT JOIN scraper.v_units u ON u.unit_key = l.unit_key
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
  SELECT jsonb_agg(jsonb_build_object('observed_at', p.observed_at, 'price', p.price_amount)
                   ORDER BY p.observed_at) AS price_trajectory
  FROM scraper.listing_price_history p
  JOIN scraper.listings l3
    ON l3.source = p.source AND l3.source_listing_id = p.source_listing_id
  WHERE l3.unit_key = l.unit_key
) ph ON true;
