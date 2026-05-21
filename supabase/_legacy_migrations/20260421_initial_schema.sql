-- verdmat-is — Phase 1B initial schema
-- Matches exact CSV headers in D:\verdmat-is\precompute\exports\
-- NUMERIC used liberally because Phase 1A wrote floats (e.g. "1990.0" for BYGGAR)
-- that would fail COPY INTO INT columns.

-- Extensions must be created before indices that depend on their opclasses.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ═══════════════════════════════════════════════════════════════════════
-- properties — one row per fastnum (~124,835)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS properties (
  fastnum                BIGINT PRIMARY KEY,
  heimilisfang           TEXT,
  husnr                  NUMERIC,
  postnr                 INT,
  postheiti              TEXT,
  svfn                   NUMERIC,
  sveitarfelag           TEXT,
  tegund_raw             TEXT,
  canonical_code         TEXT,
  unit_category          TEXT,            -- "0101" with leading zeros
  unit_family            TEXT,
  is_residential         BOOLEAN,
  is_summerhouse         BOOLEAN,
  einflm                 NUMERIC,
  lod_flm                NUMERIC,
  byggar                 NUMERIC,         -- float in CSV
  fjherb                 NUMERIC,
  fullbuid               NUMERIC,         -- 0.0/1.0/null in CSV
  is_new_build           BOOLEAN,
  is_main_unit           BOOLEAN,
  lat                    DOUBLE PRECISION,
  lng                    DOUBLE PRECISION,
  matsvaedi_numer        INT,
  matsvaedi_nafn         TEXT,
  matsvaedi_bucket       TEXT,
  region_tier            TEXT,
  fasteignamat           NUMERIC,         -- in thús.kr
  fasteignamat_gildandi  NUMERIC,
  augl_id_latest         NUMERIC,
  list_price_latest      NUMERIC,
  lysing_truncated       TEXT,
  scraped_at_latest      TIMESTAMPTZ,
  effective_date_latest  DATE,            -- listing date (not scrape date)
  first_photo_url        TEXT,
  photo_urls_json        JSONB,
  n_photos               INT
);

CREATE INDEX IF NOT EXISTS idx_properties_postnr ON properties(postnr);
CREATE INDEX IF NOT EXISTS idx_properties_canonical ON properties(canonical_code);
CREATE INDEX IF NOT EXISTS idx_properties_residential
  ON properties(is_residential) WHERE is_residential = true;
CREATE INDEX IF NOT EXISTS idx_properties_latlng
  ON properties(lat, lng) WHERE lat IS NOT NULL AND lng IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_properties_region ON properties(region_tier);
CREATE INDEX IF NOT EXISTS idx_properties_heimilisfang_trgm
  ON properties USING gin (heimilisfang gin_trgm_ops);

-- Trigram extension for fuzzy search — enabled below
-- Fulltext search (simple tokenizer because Icelandic is not a default tsvector config)
CREATE INDEX IF NOT EXISTS idx_properties_search
  ON properties USING gin (
    to_tsvector('simple',
      coalesce(heimilisfang, '') || ' ' ||
      coalesce(postheiti, '') || ' ' ||
      coalesce(fastnum::text, '')
    )
  );

-- ═══════════════════════════════════════════════════════════════════════
-- predictions — residential + summerhouse (~110,316)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS predictions (
  fastnum              BIGINT PRIMARY KEY REFERENCES properties(fastnum) ON DELETE CASCADE,
  real_pred_mean       BIGINT,
  real_pred_median     BIGINT,
  real_pred_lo80       BIGINT,
  real_pred_hi80       BIGINT,
  real_pred_lo95       BIGINT,
  real_pred_hi95       BIGINT,
  model_group          TEXT,
  segment              TEXT,
  model_version        TEXT,
  calibration_version  TEXT,
  predicted_at         DATE
);

CREATE INDEX IF NOT EXISTS idx_predictions_segment ON predictions(segment);

-- ═══════════════════════════════════════════════════════════════════════
-- feature_attributions — top 10 SHAP per residential (~1,103,160)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS feature_attributions (
  fastnum                BIGINT NOT NULL REFERENCES properties(fastnum) ON DELETE CASCADE,
  rank                   SMALLINT NOT NULL,
  feature_name           TEXT,
  feature_value          TEXT,
  shap_log_contribution  NUMERIC,
  real_isk_impact        BIGINT,
  PRIMARY KEY (fastnum, rank)
);

CREATE INDEX IF NOT EXISTS idx_attr_feature ON feature_attributions(feature_name);

-- ═══════════════════════════════════════════════════════════════════════
-- comps_index — top 10 nearest comps per residential (~1,101,454)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS comps_index (
  fastnum                BIGINT NOT NULL REFERENCES properties(fastnum) ON DELETE CASCADE,
  rank                   SMALLINT NOT NULL,
  comp_fastnum           BIGINT NOT NULL,
  distance_score         NUMERIC,
  last_sale_date         DATE,
  last_sale_price_real   BIGINT,
  PRIMARY KEY (fastnum, rank)
);

-- ═══════════════════════════════════════════════════════════════════════
-- sales_history — up to 5 sales per fastnum (~173,081)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sales_history (
  id                SERIAL PRIMARY KEY,
  fastnum           BIGINT NOT NULL REFERENCES properties(fastnum) ON DELETE CASCADE,
  thinglystdags     DATE,
  kaupverd_nominal  BIGINT,
  kaupverd_real     BIGINT,
  einflm_at_sale    NUMERIC,
  byggar_at_sale    NUMERIC,
  onothaefur        SMALLINT
);

CREATE INDEX IF NOT EXISTS idx_sales_fastnum ON sales_history(fastnum);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_history(thinglystdags);

-- ═══════════════════════════════════════════════════════════════════════
-- repeat_sale_index — quarterly index per segment × region (~2,673)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS repeat_sale_index (
  canonical_code       TEXT,
  region_tier          TEXT,
  year                 INT,
  quarter              SMALLINT,
  period               TEXT,
  index_value_nominal  NUMERIC,
  log_index_nominal    NUMERIC,
  std_error_nominal    NUMERIC,
  index_value_real     NUMERIC,
  log_index_real       NUMERIC,
  std_error_real       NUMERIC,
  n_pairs_in_period    INT,
  cell_n_pairs         INT,
  insufficient_sample  BOOLEAN,
  data_quality         TEXT,
  PRIMARY KEY (canonical_code, region_tier, year, quarter)
);

-- ═══════════════════════════════════════════════════════════════════════
-- ats_lookup — heat × segment × region stats (~65)
-- NB: heat_bucket can be NULL (summary rows with overall stats only), so we
-- use a SERIAL PK + partial unique index for the non-null bucket rows.
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ats_lookup (
  id                 SERIAL PRIMARY KEY,
  canonical_code     TEXT,
  region_tier        TEXT,
  heat_bucket        TEXT,
  n_pairs            NUMERIC,
  median_log_ratio   NUMERIC,
  dispersion_sd      NUMERIC,
  dispersion_mad     NUMERIC,
  above_list_rate    NUMERIC,
  n_quarters_pooled  NUMERIC,
  data_quality       TEXT,
  p33                NUMERIC,
  p67                NUMERIC,
  median_overall     NUMERIC,
  n_qtrs_stable      INT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ats_lookup_segreg_bucket
  ON ats_lookup (canonical_code, region_tier, heat_bucket)
  WHERE heat_bucket IS NOT NULL;

-- (pg_trgm extension is created at the top of this file, before indices.)
