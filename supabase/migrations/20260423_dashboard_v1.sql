-- verdmat-is — Sprint 2 Áfangi 4 Dashboard v1 schema additions
-- Adds: ats_dashboard_monthly_heat, model_tracking_history,
--       llm_aggregates_quarterly, last_listing_text
-- Plus views: repeat_sale_index_main_pooled, repeat_sale_index_by_segment,
--             latest_regime_per_cell

-- ═══════════════════════════════════════════════════════════════════════
-- ats_dashboard_monthly_heat — per (seg × reg × month) regime indicator
-- Schema matches actual build_ats_lookup.py step 8 output (2026-04-23 rebuild).
-- month is "YYYY-MM" text (period stringification); heat_bucket derived via
-- p33/p67 thresholds from ats_heat_thresholds (same methodology as quarterly).
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ats_dashboard_monthly_heat (
  canonical_code     TEXT NOT NULL,
  region_tier        TEXT NOT NULL,
  month              TEXT NOT NULL,                    -- 'YYYY-MM'
  n_month            INT,
  median_month       NUMERIC,
  above_list_rate    NUMERIC,
  rolling_3mo_median NUMERIC,
  rolling_12mo_mean  NUMERIC,
  rolling_12mo_sd    NUMERIC,
  z_3v12             NUMERIC,
  heat_bucket        TEXT,                             -- 'hot'|'neutral'|'cold'|NULL
  PRIMARY KEY (canonical_code, region_tier, month)
);

CREATE INDEX IF NOT EXISTS idx_ats_monthly_month
  ON ats_dashboard_monthly_heat(month);
CREATE INDEX IF NOT EXISTS idx_ats_monthly_segreg
  ON ats_dashboard_monthly_heat(canonical_code, region_tier);

-- ═══════════════════════════════════════════════════════════════════════
-- model_tracking_history — monthly held-set MAPE/coverage snapshot, append-only
-- ═══════════════════════════════════════════════════════════════════════
-- segment = NULL means "overall pooled" row; only one per (period, model_version).
-- PK uses COALESCE so NULL compares equal to other NULLs in uniqueness check.
CREATE TABLE IF NOT EXISTS model_tracking_history (
  period              TEXT NOT NULL,        -- 'YYYY-MM'
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  model_version       TEXT NOT NULL,
  calibration_version TEXT,
  segment             TEXT,                 -- canonical_code; NULL = overall pooled
  n_held              INT,
  mape                NUMERIC,
  median_ape          NUMERIC,
  bias_log            NUMERIC,
  cov80               NUMERIC,
  cov95               NUMERIC,
  status_label        TEXT                  -- 'ok'|'caveat'|'wavering'|'broken'
);

CREATE UNIQUE INDEX IF NOT EXISTS model_tracking_history_pkey
  ON model_tracking_history (period, model_version, (COALESCE(segment, '__OVERALL__')));

CREATE INDEX IF NOT EXISTS idx_model_tracking_period
  ON model_tracking_history(period);

-- ═══════════════════════════════════════════════════════════════════════
-- llm_aggregates_quarterly — five LLM-derived metrics per (seg × region × quarter)
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS llm_aggregates_quarterly (
  year                            INT NOT NULL,
  quarter                         SMALLINT NOT NULL,
  period                          TEXT NOT NULL,        -- 'YYYYQq'
  canonical_code                  TEXT NOT NULL,
  region_tier                     TEXT NOT NULL,        -- 'POOLED' for all-regions rows
  -- Metric 1: Ástandsvísitala
  mean_interior_condition_score   NUMERIC,
  n_listings_condition            INT,
  -- Metric 2: Endurnýjunartíðni
  pct_recently_renovated          NUMERIC,
  n_listings_renovation           INT,
  -- Metric 3: Óskráð rými rate
  pct_has_unregistered_space      NUMERIC,
  n_listings_unregistered         INT,
  -- Metric 4: Sérlóð í APT
  pct_apt_with_serlod             NUMERIC,
  n_listings_serlod               INT,
  -- Metric 6: Agent framing distribution (metric 5 deferred to v1.1)
  pct_framing_terse               NUMERIC,
  pct_framing_standard            NUMERIC,
  pct_framing_elaborate           NUMERIC,
  pct_framing_promotional         NUMERIC,
  n_listings_total                INT,
  created_at                      TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (year, quarter, canonical_code, region_tier)
);

CREATE INDEX IF NOT EXISTS idx_llm_agg_period
  ON llm_aggregates_quarterly(period);
CREATE INDEX IF NOT EXISTS idx_llm_agg_segment
  ON llm_aggregates_quarterly(canonical_code);

-- ═══════════════════════════════════════════════════════════════════════
-- last_listing_text — top 3 most recent arm's-length listings per fastnum
-- HTML stripped, capped to save storage.
-- ═══════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS last_listing_text (
  fastnum         BIGINT NOT NULL,
  sale_rank       SMALLINT NOT NULL,     -- 1 = most recent, 2 = second-most, 3 = third
  thinglyst_dagur DATE,
  augl_id         TEXT,
  lysing_plain    TEXT,
  scraped_at      TIMESTAMPTZ,
  PRIMARY KEY (fastnum, sale_rank)
);

CREATE INDEX IF NOT EXISTS idx_last_listing_fastnum
  ON last_listing_text(fastnum);

-- ═══════════════════════════════════════════════════════════════════════
-- Views
-- ═══════════════════════════════════════════════════════════════════════

-- Main residential pooled — for landing hero metric A and CAGR card.
-- Weighted by n_pairs_in_period per quarter.
CREATE OR REPLACE VIEW repeat_sale_index_main_pooled AS
SELECT year,
       quarter,
       period,
       SUM(index_value_real * n_pairs_in_period)
         / NULLIF(SUM(n_pairs_in_period), 0)    AS index_real,
       SUM(index_value_nominal * n_pairs_in_period)
         / NULLIF(SUM(n_pairs_in_period), 0)    AS index_nominal,
       SUM(n_pairs_in_period)                   AS n_pairs
FROM repeat_sale_index
WHERE canonical_code IN ('APT_FLOOR','APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
  AND insufficient_sample = FALSE
GROUP BY year, quarter, period;

-- Per-segment pooled across regions — for landing 3-line timeline chart.
CREATE OR REPLACE VIEW repeat_sale_index_by_segment AS
SELECT canonical_code,
       year,
       quarter,
       period,
       SUM(index_value_real * n_pairs_in_period)
         / NULLIF(SUM(n_pairs_in_period), 0)    AS index_real,
       SUM(index_value_nominal * n_pairs_in_period)
         / NULLIF(SUM(n_pairs_in_period), 0)    AS index_nominal,
       SUM(n_pairs_in_period)                   AS n_pairs
FROM repeat_sale_index
WHERE canonical_code IN ('APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
  AND insufficient_sample = FALSE
GROUP BY canonical_code, year, quarter, period;

-- Latest regime per (seg × region) — for landing hero B pill + heat-map default.
CREATE OR REPLACE VIEW latest_regime_per_cell AS
SELECT DISTINCT ON (canonical_code, region_tier)
       canonical_code,
       region_tier,
       month,
       heat_bucket,
       above_list_rate,
       n_month
FROM ats_dashboard_monthly_heat
WHERE canonical_code IN ('APT_FLOOR','APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
ORDER BY canonical_code, region_tier, month DESC;
