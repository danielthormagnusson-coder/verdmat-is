-- Bug 6 + Smoothing refinement (2026-04-24): quarterly regime as primary data
-- source for /markadsstada, with smoothed-monthly drill-down and per-cell
-- sample-size-aware fallback.

CREATE TABLE IF NOT EXISTS ats_lookup_by_quarter (
  canonical_code    TEXT NOT NULL,
  region_tier       TEXT NOT NULL,
  quarter           TEXT NOT NULL,
  n_pairs           INT,
  median_log_ratio  NUMERIC,
  dispersion_sd     NUMERIC,
  dispersion_mad    NUMERIC,
  above_list_rate   NUMERIC,
  heat_bucket       TEXT,
  data_quality      TEXT,
  p33               NUMERIC,
  p67               NUMERIC,
  n_qtrs_stable     INT,
  PRIMARY KEY (canonical_code, region_tier, quarter)
);

CREATE INDEX IF NOT EXISTS idx_ats_by_qtr_quarter
  ON ats_lookup_by_quarter(quarter);
CREATE INDEX IF NOT EXISTS idx_ats_by_qtr_segreg
  ON ats_lookup_by_quarter(canonical_code, region_tier);

CREATE OR REPLACE VIEW regime_per_cell_monthly AS
SELECT
  m.canonical_code,
  m.region_tier,
  m.month,
  m.n_month,
  m.median_month,
  m.above_list_rate,
  m.z_3v12,
  m.heat_bucket AS raw_regime,
  CASE
    WHEN m.z_3v12 IS NULL THEN NULL
    WHEN m.z_3v12 >  0.5 THEN 'hot'
    WHEN m.z_3v12 < -0.5 THEN 'cold'
    ELSE 'neutral'
  END AS smoothed_regime,
  q.heat_bucket      AS quarterly_regime,
  q.n_pairs          AS quarterly_n_pairs,
  q.quarter          AS quarterly_period,
  q.data_quality     AS quarterly_data_quality,
  CASE
    WHEN m.n_month >= 50 AND m.z_3v12 IS NOT NULL THEN
      CASE
        WHEN m.z_3v12 >  0.5 THEN 'hot'
        WHEN m.z_3v12 < -0.5 THEN 'cold'
        ELSE 'neutral'
      END
    ELSE q.heat_bucket
  END AS display_regime,
  CASE
    WHEN m.n_month >= 50 AND m.z_3v12 IS NOT NULL THEN 'smoothed_monthly'
    ELSE 'quarterly_fallback'
  END AS regime_source
FROM ats_dashboard_monthly_heat m
LEFT JOIN ats_lookup_by_quarter q
  ON q.canonical_code = m.canonical_code
 AND q.region_tier    = m.region_tier
 AND q.quarter        = (extract(year FROM to_date(m.month, 'YYYY-MM'))::int::text
                          || 'Q'
                          || extract(quarter FROM to_date(m.month, 'YYYY-MM'))::int::text);
