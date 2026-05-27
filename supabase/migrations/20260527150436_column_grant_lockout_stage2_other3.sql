-- Phase X Group B column-grant lockout — Stage 2
-- (public.predictions, public.repeat_sale_index, public.ats_lookup)
--
-- Same pattern as Stage 1 but each table's allowlist is its full column
-- set (the corresponding v_* view projects all columns). No behavioral
-- change today; switching from table-level to column-level grants gives
-- default-deny on any future column added to these tables (a new view
-- projection MUST also add a matching GRANT).
--
-- Each table in its own transaction so a per-table failure does not roll
-- back the prior stage's work.

-- predictions (12 cols; v_current_predictions projects all + ORDER BY)
BEGIN;
REVOKE SELECT ON public.predictions FROM anon;
REVOKE SELECT ON public.predictions FROM authenticated;
GRANT SELECT (
  fastnum, real_pred_mean, real_pred_median,
  real_pred_lo80, real_pred_hi80, real_pred_lo95, real_pred_hi95,
  model_group, segment, model_version, calibration_version, predicted_at
) ON public.predictions TO anon;
GRANT SELECT (
  fastnum, real_pred_mean, real_pred_median,
  real_pred_lo80, real_pred_hi80, real_pred_lo95, real_pred_hi95,
  model_group, segment, model_version, calibration_version, predicted_at
) ON public.predictions TO authenticated;
COMMIT;

-- repeat_sale_index (15 cols; v_repeat_sale_index projects all)
BEGIN;
REVOKE SELECT ON public.repeat_sale_index FROM anon;
REVOKE SELECT ON public.repeat_sale_index FROM authenticated;
GRANT SELECT (
  canonical_code, region_tier, year, quarter, period,
  index_value_nominal, log_index_nominal, std_error_nominal,
  index_value_real, log_index_real, std_error_real,
  n_pairs_in_period, cell_n_pairs, insufficient_sample, data_quality
) ON public.repeat_sale_index TO anon;
GRANT SELECT (
  canonical_code, region_tier, year, quarter, period,
  index_value_nominal, log_index_nominal, std_error_nominal,
  index_value_real, log_index_real, std_error_real,
  n_pairs_in_period, cell_n_pairs, insufficient_sample, data_quality
) ON public.repeat_sale_index TO authenticated;
COMMIT;

-- ats_lookup (15 cols; v_ats_lookup_by_heat projects all)
BEGIN;
REVOKE SELECT ON public.ats_lookup FROM anon;
REVOKE SELECT ON public.ats_lookup FROM authenticated;
GRANT SELECT (
  id, canonical_code, region_tier, heat_bucket, n_pairs,
  median_log_ratio, dispersion_sd, dispersion_mad, above_list_rate,
  n_quarters_pooled, data_quality, p33, p67, median_overall, n_qtrs_stable
) ON public.ats_lookup TO anon;
GRANT SELECT (
  id, canonical_code, region_tier, heat_bucket, n_pairs,
  median_log_ratio, dispersion_sd, dispersion_mad, above_list_rate,
  n_quarters_pooled, data_quality, p33, p67, median_overall, n_qtrs_stable
) ON public.ats_lookup TO authenticated;
COMMIT;
