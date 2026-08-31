-- =====================================================================
-- cc165 — model_metrics_insert.sql. ÓBEITT. Skrifað 2026-08-14.
-- Hver lína ber heimildarslóð á D: í source_path + source_section.
-- Engin tala er handslegin: q05_smida_sql.py las hverja tölu úr sinni
-- frosnu heimild og skrifaði þessa skrá. Endursmíð: keyrðu q05 aftur.
-- RAÐIR: 32   GAT-LEIF (ekki innsett): 6
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;

-- holdout30_n_pairs
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.adaltala_holdout30.n_pairs
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_n_pairs', 949.0, 'count', NULL, 949.0, 'Pöruð OOS-sölumöt (holdout30): þinglýstar sölur með oos_cutoff 2026-01-15, skorað í framreiðsluramma; n_pairs úr public.model_metrics metric_run_id=118.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.adaltala_holdout30.n_pairs', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', 847.0, 'D:\verdmat-is\app\docs\GO_BREF_FLIPP_REGLA_R_CC98_20260806.md — §2 tafla „HVAÐ BATNAR — með nefnurum“ + §3 level-myndin (n holdout30)', 'Leysir af úrelta tölu frosnu nákvæmniblokkarinnar sem frumgerðapakkarnir bera (cc163 §1.2). Lifandi mælilag: public.model_metrics metric_run_id=118.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- holdout30_mape
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.adaltala_holdout30.mape
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_mape', 8.2284, 'pct', NULL, 949.0, 'Pöruð OOS-sölumöt (holdout30): þinglýstar sölur með oos_cutoff 2026-01-15, skorað í framreiðsluramma; n_pairs úr public.model_metrics metric_run_id=118.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.adaltala_holdout30.mape', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', 8.23, 'D:\verdmat-is\app\docs\GO_BREF_FLIPP_REGLA_R_CC98_20260806.md — §2 tafla „HVAÐ BATNAR — með nefnurum“ + §3 level-myndin (MAPE holdout30)', 'Leysir af úrelta tölu frosnu nákvæmniblokkarinnar sem frumgerðapakkarnir bera (cc163 §1.2). Lifandi mælilag: public.model_metrics metric_run_id=118.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- holdout30_med_ape
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.adaltala_holdout30.med_ape
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_med_ape', 5.5256, 'pct', NULL, 949.0, 'Pöruð OOS-sölumöt (holdout30): þinglýstar sölur með oos_cutoff 2026-01-15, skorað í framreiðsluramma; n_pairs úr public.model_metrics metric_run_id=118.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.adaltala_holdout30.med_ape', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', 5.87, 'D:\verdmat-is\app\docs\GO_BREF_FLIPP_REGLA_R_CC98_20260806.md — §2 tafla „HVAÐ BATNAR — með nefnurum“ + §3 level-myndin (medAPE holdout30)', 'Leysir af úrelta tölu frosnu nákvæmniblokkarinnar sem frumgerðapakkarnir bera (cc163 §1.2). Lifandi mælilag: public.model_metrics metric_run_id=118.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- holdout30_level_bias
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.adaltala_holdout30.bias
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_level_bias', 1.9341, 'pct', NULL, 949.0, 'Pöruð OOS-sölumöt (holdout30): þinglýstar sölur með oos_cutoff 2026-01-15, skorað í framreiðsluramma; n_pairs úr public.model_metrics metric_run_id=118.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.adaltala_holdout30.bias', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', 2.46, 'D:\verdmat-is\app\docs\GO_BREF_FLIPP_REGLA_R_CC98_20260806.md — §2 tafla „HVAÐ BATNAR — með nefnurum“ + §3 level-myndin (level bias (+ = vanmat))', 'Leysir af úrelta tölu frosnu nákvæmniblokkarinnar sem frumgerðapakkarnir bera (cc163 §1.2). Lifandi mælilag: public.model_metrics metric_run_id=118.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- holdout30_cov80
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.adaltala_holdout30.cov80
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_cov80', 82.824, 'pct', 786.0, 949.0, 'Pöruð OOS-sölumöt (holdout30): þinglýstar sölur með oos_cutoff 2026-01-15, skorað í framreiðsluramma; n_pairs úr public.model_metrics metric_run_id=118.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.adaltala_holdout30.cov80', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', 81.58, 'D:\verdmat-is\app\docs\GO_BREF_FLIPP_REGLA_R_CC98_20260806.md — §2 tafla „HVAÐ BATNAR — með nefnurum“ + §3 level-myndin (cov80 holdout30)', 'Leysir af úrelta tölu frosnu nákvæmniblokkarinnar sem frumgerðapakkarnir bera (cc163 §1.2). Lifandi mælilag: public.model_metrics metric_run_id=118.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- holdout30_cov95
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.adaltala_holdout30.cov95
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_cov95', 96.1012, 'pct', 912.0, 949.0, 'Pöruð OOS-sölumöt (holdout30): þinglýstar sölur með oos_cutoff 2026-01-15, skorað í framreiðsluramma; n_pairs úr public.model_metrics metric_run_id=118.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.adaltala_holdout30.cov95', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', 96.69, 'D:\verdmat-is\app\docs\GO_BREF_FLIPP_REGLA_R_CC98_20260806.md — §2 tafla „HVAÐ BATNAR — með nefnurum“ + §3 level-myndin (cov95 holdout30)', 'Leysir af úrelta tölu frosnu nákvæmniblokkarinnar sem frumgerðapakkarnir bera (cc163 §1.2). Lifandi mælilag: public.model_metrics metric_run_id=118.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- fresh_edge_n_pairs
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.fresh_edge.n_pairs
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('fresh_edge_n_pairs', 87.0, 'count', NULL, 87.0, 'Pöruð OOS-sölumöt á ferska jaðrinum (fresh_edge): þinglýst eftir oos_cutoff 2026-07-31; ÞUNN mæling, aðskilin frá aðaltölunni.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.fresh_edge.n_pairs', '2026-08-14', 'BIRTANLEG', '{holdout30}', 339.0, 'D:\verdmat-is\app\docs\GO_BREF_FLIPP_REGLA_R_CC98_20260806.md — §2 tafla „HVAÐ BATNAR — með nefnurum“ + §3 level-myndin (n fresh_edge)', 'Leysir af úrelta tölu frosnu nákvæmniblokkarinnar sem frumgerðapakkarnir bera (cc163 §1.2). Lifandi mælilag: public.model_metrics metric_run_id=118.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- fresh_edge_mape
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.fresh_edge.mape
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('fresh_edge_mape', 34.6125, 'pct', NULL, 87.0, 'Pöruð OOS-sölumöt á ferska jaðrinum (fresh_edge): þinglýst eftir oos_cutoff 2026-07-31; ÞUNN mæling, aðskilin frá aðaltölunni.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.fresh_edge.mape', '2026-08-14', 'BIRTANLEG', '{holdout30}', 11.59, 'D:\verdmat-is\app\docs\GO_BREF_FLIPP_REGLA_R_CC98_20260806.md — §2 tafla „HVAÐ BATNAR — með nefnurum“ + §3 level-myndin (MAPE fresh_edge)', 'Leysir af úrelta tölu frosnu nákvæmniblokkarinnar sem frumgerðapakkarnir bera (cc163 §1.2). Lifandi mælilag: public.model_metrics metric_run_id=118.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- fresh_edge_cov80
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.fresh_edge.cov80
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('fresh_edge_cov80', 74.7126, 'pct', 65.0, 87.0, 'Pöruð OOS-sölumöt á ferska jaðrinum (fresh_edge): þinglýst eftir oos_cutoff 2026-07-31; ÞUNN mæling, aðskilin frá aðaltölunni.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.fresh_edge.cov80', '2026-08-14', 'BIRTANLEG', '{holdout30}', 83.48, 'D:\verdmat-is\app\docs\GO_BREF_FLIPP_REGLA_R_CC98_20260806.md — §2 tafla „HVAÐ BATNAR — með nefnurum“ + §3 level-myndin (cov80 fresh_edge)', 'Leysir af úrelta tölu frosnu nákvæmniblokkarinnar sem frumgerðapakkarnir bera (cc163 §1.2). Lifandi mælilag: public.model_metrics metric_run_id=118.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- holdout30_mape__property_type_sfh_detached
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.segment_eignarinnar.property_type.mape
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_mape__property_type_sfh_detached', 14.4099, 'pct', NULL, 130.0, 'Pöruð OOS-sölumöt (holdout30) INNAN segments property_type=SFH_DETACHED; hlutmengi 949-para aðaltölunnar, ekki sjálfstætt þýði.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.segment_eignarinnar.property_type.mape', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', NULL, NULL, 'Segmenttala eignarinnar. cc163 §1.2 lína 8: skyldulesning, ekki neðanmálsgrein.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- holdout30_cov80__property_type_sfh_detached
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.segment_eignarinnar.property_type.cov80
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_cov80__property_type_sfh_detached', 83.0769, 'pct', 108.0, 130.0, 'Pöruð OOS-sölumöt (holdout30) INNAN segments property_type=SFH_DETACHED; hlutmengi 949-para aðaltölunnar, ekki sjálfstætt þýði.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.segment_eignarinnar.property_type.cov80', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', NULL, NULL, 'Segmenttala eignarinnar. cc163 §1.2 lína 8: skyldulesning, ekki neðanmálsgrein.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- holdout30_mape__price_band_yfir100m
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.segment_eignarinnar.price_band.mape
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_mape__price_band_yfir100m', 9.2134, 'pct', NULL, 189.0, 'Pöruð OOS-sölumöt (holdout30) INNAN segments price_band=>=100M; hlutmengi 949-para aðaltölunnar, ekki sjálfstætt þýði.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.segment_eignarinnar.price_band.mape', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', NULL, NULL, 'Segmenttala eignarinnar. cc163 §1.2 lína 8: skyldulesning, ekki neðanmálsgrein.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- holdout30_cov80__price_band_yfir100m
--   heimild: D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json
--            nakvaemni_likans.segment_eignarinnar.price_band.cov80
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('holdout30_cov80__price_band_yfir100m', 79.8942, 'pct', 151.0, 189.0, 'Pöruð OOS-sölumöt (holdout30) INNAN segments price_band=>=100M; hlutmengi 949-para aðaltölunnar, ekki sjálfstætt þýði.', NULL, NULL, NULL, '2026-08-10', 'iter4r_20260805_reglaR_strukt', 'D:\_audit\cc163_fable_gaedaprof\PAKKI_2281760_cc163.json', 'nakvaemni_likans.segment_eignarinnar.price_band.cov80', '2026-08-14', 'BIRTANLEG', '{fresh_edge}', NULL, NULL, 'Segmenttala eignarinnar. cc163 §1.2 lína 8: skyldulesning, ekki neðanmálsgrein.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__eldhus_allt__slaemt_m2_m1
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.eldhus_allt_thyði.coef.eldhus_slaemt(-2/-1)
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__eldhus_allt__slaemt_m2_m1', -10.0, 'pct', 239.0, 14759.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: eldhus_allt_thyði (grunnur = upprunalegt(0), allt þýðið); 1787 sellur.', 1.59, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.eldhus_allt_thyði.coef.eldhus_slaemt(-2/-1)', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__eldhus_allt__gott_1
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.eldhus_allt_thyði.coef.eldhus_gott(1)
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__eldhus_allt__gott_1', 8.71, 'pct', 6170.0, 14759.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: eldhus_allt_thyði (grunnur = upprunalegt(0), allt þýðið); 1787 sellur.', 0.39, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.eldhus_allt_thyði.coef.eldhus_gott(1)', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__eldhus_allt__uppgert_2_3
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.eldhus_allt_thyði.coef.eldhus_uppgert(2/3)
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__eldhus_allt__uppgert_2_3', 10.99, 'pct', 6260.0, 14759.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: eldhus_allt_thyði (grunnur = upprunalegt(0), allt þýðið); 1787 sellur.', 0.39, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.eldhus_allt_thyði.coef.eldhus_uppgert(2/3)', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__eldhus_2023plus__slaemt_m2_m1
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.eldhus_2023plus.coef.eldhus_slaemt(-2/-1)
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__eldhus_2023plus__slaemt_m2_m1', -8.25, 'pct', 42.0, 3323.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: eldhus_2023plus (grunnur = upprunalegt(0), sölur 2023+); 437 sellur.', 2.95, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.eldhus_2023plus.coef.eldhus_slaemt(-2/-1)', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__eldhus_2023plus__gott_1
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.eldhus_2023plus.coef.eldhus_gott(1)
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__eldhus_2023plus__gott_1', 6.93, 'pct', 1306.0, 3323.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: eldhus_2023plus (grunnur = upprunalegt(0), sölur 2023+); 437 sellur.', 0.9, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.eldhus_2023plus.coef.eldhus_gott(1)', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__eldhus_2023plus__uppgert_2_3
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.eldhus_2023plus.coef.eldhus_uppgert(2/3)
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__eldhus_2023plus__uppgert_2_3', 10.12, 'pct', 1653.0, 3323.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: eldhus_2023plus (grunnur = upprunalegt(0), sölur 2023+); 437 sellur.', 0.87, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.eldhus_2023plus.coef.eldhus_uppgert(2/3)', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__innra_skor__slaemt_undirm05
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.innra_skor.coef.innra_slaemt(<=-0.5)
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__innra_skor__slaemt_undirm05', -9.56, 'pct', 501.0, 20109.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: innra_skor (grunnur = upprunalegt-band, innra ástandsskor); 2149 sellur.', 1.1, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.innra_skor.coef.innra_slaemt(<=-0.5)', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__innra_skor__gott_05m15
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.innra_skor.coef.innra_gott(0.5-1.5)
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__innra_skor__gott_05m15', 8.11, 'pct', 7556.0, 20109.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: innra_skor (grunnur = upprunalegt-band, innra ástandsskor); 2149 sellur.', 0.41, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.innra_skor.coef.innra_gott(0.5-1.5)', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__innra_skor__uppgert_yfir15
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.innra_skor.coef.innra_uppgert(>1.5)
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__innra_skor__uppgert_yfir15', 10.19, 'pct', 10273.0, 20109.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: innra_skor (grunnur = upprunalegt-band, innra ástandsskor); 2149 sellur.', 0.4, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.innra_skor.coef.innra_uppgert(>1.5)', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__needs_work__needs_immediate_work
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.needs_work.coef.needs_immediate_work
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__needs_work__needs_immediate_work', -13.25, 'pct', 1991.0, 29381.0, 'Within-sella OLS-aðhvarfsúrtak á log-raunverði; sella = canonical_code | matsvaedi_bucket | söluár, >=3 sölur/sellu, stýrt f/ log(EINFLM)+age_at_sale, HC-robust SE. Nefnari = raðir í endanlegu aðhvarfi, teljari = n_treated. Blokk: needs_work (needs_immediate_work gegn öllu öðru); 2650 sellur.', 0.48, NULL, NULL, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.needs_work.coef.needs_immediate_work', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Ástandskontrast cc35 — GAT-LISTI cc163 lína 1, stærsta gatið: skyldukaflinn astandsinnslag_notanda gat enga stærðargráðu borið meðan þessi tala bjó aðeins á D:. BEITT Í FRAMLEIÐSLU: leidretting_studlar_v1.json ber sömu mælingu rúnaða sem markadur_pct=-13.3 (netto_birt -13.3, se 0.5); SAMA MÆLING, ekki önnur — hér er ónúnaða gildið.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- astand__eldhus_allt__parud_sella_midgildi
--   heimild: D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json
--            H3_hedonic.parud_sella_eldhus
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('astand__eldhus_allt__parud_sella_midgildi', 10.04, 'pct', NULL, 902.0, 'Paraðar sellur (canonical x matsvaedi x ár x stærðarband x aldursband) sem bera BÆÐI uppgert og upprunalegt eldhús; miðgildi Δ innan sellu. n_reno=1843, n_orig=1340 raðir í sellunum.', NULL, -2.5, 22.86, '2026-07-21', 'ekki_likansmaeling', 'D:\verdmat-is\app\docs\fable_prep\prototypes\cc35\cc35_fast.json', 'H3_hedonic.parud_sella_eldhus', '2026-07-21', 'BIRTANLEG', NULL, NULL, NULL, 'Robustness-mæling við eldhus_allt_thyði; IQR í ci_lo/ci_hi, ekki öryggisbil.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- list_to_sale_median__lotuparun__2025Q3
--   heimild: D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts
--            KAUPVERD_VS_ASETT[fj=2025Q3]
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('list_to_sale_median__lotuparun__2025Q3', 0.9745, 'ratio', NULL, 1374.0, 'Auglýsingalotur (scraper.listing_sessions, evalue-safnið) paraðar við þinglýsta íbúðarkaupsamninga (semantic._sales_base): fyrsta sala sama fastnúmers −30 til +180 daga frá lotulokum, hlutfall innan [0,5;2,0], ásett > 5 M kr. ÖNNUR PÖRUN EN ats_lookup_by_quarter — systkinamæling, ALDREI framhald sömu raðar. Lotusafnið endar 2026-04-15.', NULL, 0.9539, 0.9933, '2026-08-06', 'ekki_likansmaeling', 'D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts', 'KAUPVERD_VS_ASETT[fj=2025Q3]', '2026-08-06', 'BIRTANLEG', NULL, NULL, NULL, 'GAT-LISTI cc163 lína 2. Heiti ber viðskeytið __lotuparun til að útiloka þögla samsteypu við ats_lookup_by_quarter (sem nær aðeins til 2025Q2). traust=true (þröskuldur 300 pör). ci_lo/ci_hi eru p25/p75 hlutfallsins, ekki öryggisbil.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- list_to_sale_over_asking_share__lotuparun__2025Q3
--   heimild: D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts
--            KAUPVERD_VS_ASETT[fj=2025Q3].yfir
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('list_to_sale_over_asking_share__lotuparun__2025Q3', 8.3, 'pct', NULL, 1374.0, 'Auglýsingalotur (scraper.listing_sessions, evalue-safnið) paraðar við þinglýsta íbúðarkaupsamninga (semantic._sales_base): fyrsta sala sama fastnúmers −30 til +180 daga frá lotulokum, hlutfall innan [0,5;2,0], ásett > 5 M kr. ÖNNUR PÖRUN EN ats_lookup_by_quarter — systkinamæling, ALDREI framhald sömu raðar. Lotusafnið endar 2026-04-15.', NULL, NULL, NULL, '2026-08-06', 'ekki_likansmaeling', 'D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts', 'KAUPVERD_VS_ASETT[fj=2025Q3].yfir', '2026-08-06', 'BIRTANLEG', NULL, NULL, NULL, 'GAT-LISTI cc163 lína 2. Heiti ber viðskeytið __lotuparun til að útiloka þögla samsteypu við ats_lookup_by_quarter (sem nær aðeins til 2025Q2). traust=true (þröskuldur 300 pör).')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- list_to_sale_median__lotuparun__2025Q4
--   heimild: D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts
--            KAUPVERD_VS_ASETT[fj=2025Q4]
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('list_to_sale_median__lotuparun__2025Q4', 0.9658, 'ratio', NULL, 425.0, 'Auglýsingalotur (scraper.listing_sessions, evalue-safnið) paraðar við þinglýsta íbúðarkaupsamninga (semantic._sales_base): fyrsta sala sama fastnúmers −30 til +180 daga frá lotulokum, hlutfall innan [0,5;2,0], ásett > 5 M kr. ÖNNUR PÖRUN EN ats_lookup_by_quarter — systkinamæling, ALDREI framhald sömu raðar. Lotusafnið endar 2026-04-15.', NULL, 0.94, 0.995, '2026-08-06', 'ekki_likansmaeling', 'D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts', 'KAUPVERD_VS_ASETT[fj=2025Q4]', '2026-08-06', 'BIRTANLEG', NULL, NULL, NULL, 'GAT-LISTI cc163 lína 2. Heiti ber viðskeytið __lotuparun til að útiloka þögla samsteypu við ats_lookup_by_quarter (sem nær aðeins til 2025Q2). traust=true (þröskuldur 300 pör). ci_lo/ci_hi eru p25/p75 hlutfallsins, ekki öryggisbil.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- list_to_sale_over_asking_share__lotuparun__2025Q4
--   heimild: D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts
--            KAUPVERD_VS_ASETT[fj=2025Q4].yfir
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('list_to_sale_over_asking_share__lotuparun__2025Q4', 7.53, 'pct', 32.0, 425.0, 'Auglýsingalotur (scraper.listing_sessions, evalue-safnið) paraðar við þinglýsta íbúðarkaupsamninga (semantic._sales_base): fyrsta sala sama fastnúmers −30 til +180 daga frá lotulokum, hlutfall innan [0,5;2,0], ásett > 5 M kr. ÖNNUR PÖRUN EN ats_lookup_by_quarter — systkinamæling, ALDREI framhald sömu raðar. Lotusafnið endar 2026-04-15.', NULL, NULL, NULL, '2026-08-06', 'ekki_likansmaeling', 'D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts', 'KAUPVERD_VS_ASETT[fj=2025Q4].yfir', '2026-08-06', 'BIRTANLEG', NULL, NULL, NULL, 'GAT-LISTI cc163 lína 2. Heiti ber viðskeytið __lotuparun til að útiloka þögla samsteypu við ats_lookup_by_quarter (sem nær aðeins til 2025Q2). traust=true (þröskuldur 300 pör).')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- list_to_sale_median__lotuparun__2026Q1
--   heimild: D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts
--            KAUPVERD_VS_ASETT[fj=2026Q1]
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('list_to_sale_median__lotuparun__2026Q1', 0.9762, 'ratio', NULL, 167.0, 'Auglýsingalotur (scraper.listing_sessions, evalue-safnið) paraðar við þinglýsta íbúðarkaupsamninga (semantic._sales_base): fyrsta sala sama fastnúmers −30 til +180 daga frá lotulokum, hlutfall innan [0,5;2,0], ásett > 5 M kr. ÖNNUR PÖRUN EN ats_lookup_by_quarter — systkinamæling, ALDREI framhald sömu raðar. Lotusafnið endar 2026-04-15.', NULL, 0.9417, 1.0, '2026-08-06', 'ekki_likansmaeling', 'D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts', 'KAUPVERD_VS_ASETT[fj=2026Q1]', '2026-08-06', 'OMAELANLEG', NULL, NULL, NULL, 'GAT-LISTI cc163 lína 2. Heiti ber viðskeytið __lotuparun til að útiloka þögla samsteypu við ats_lookup_by_quarter (sem nær aðeins til 2025Q2). traust=false (þröskuldur 300 pör). ci_lo/ci_hi eru p25/p75 hlutfallsins, ekki öryggisbil.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- list_to_sale_over_asking_share__lotuparun__2026Q1
--   heimild: D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts
--            KAUPVERD_VS_ASETT[fj=2026Q1].yfir
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('list_to_sale_over_asking_share__lotuparun__2026Q1', 19.16, 'pct', 32.0, 167.0, 'Auglýsingalotur (scraper.listing_sessions, evalue-safnið) paraðar við þinglýsta íbúðarkaupsamninga (semantic._sales_base): fyrsta sala sama fastnúmers −30 til +180 daga frá lotulokum, hlutfall innan [0,5;2,0], ásett > 5 M kr. ÖNNUR PÖRUN EN ats_lookup_by_quarter — systkinamæling, ALDREI framhald sömu raðar. Lotusafnið endar 2026-04-15.', NULL, NULL, NULL, '2026-08-06', 'ekki_likansmaeling', 'D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts', 'KAUPVERD_VS_ASETT[fj=2026Q1].yfir', '2026-08-06', 'OMAELANLEG', NULL, NULL, NULL, 'GAT-LISTI cc163 lína 2. Heiti ber viðskeytið __lotuparun til að útiloka þögla samsteypu við ats_lookup_by_quarter (sem nær aðeins til 2025Q2). traust=false (þröskuldur 300 pör).')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- list_to_sale_median__lotuparun__2026Q2
--   heimild: D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts
--            KAUPVERD_VS_ASETT[fj=2026Q2]
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('list_to_sale_median__lotuparun__2026Q2', 0.9683, 'ratio', NULL, 459.0, 'Auglýsingalotur (scraper.listing_sessions, evalue-safnið) paraðar við þinglýsta íbúðarkaupsamninga (semantic._sales_base): fyrsta sala sama fastnúmers −30 til +180 daga frá lotulokum, hlutfall innan [0,5;2,0], ásett > 5 M kr. ÖNNUR PÖRUN EN ats_lookup_by_quarter — systkinamæling, ALDREI framhald sömu raðar. Lotusafnið endar 2026-04-15.', NULL, 0.9471, 0.9842, '2026-08-06', 'ekki_likansmaeling', 'D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts', 'KAUPVERD_VS_ASETT[fj=2026Q2]', '2026-08-06', 'BIRTANLEG', NULL, NULL, NULL, 'GAT-LISTI cc163 lína 2. Heiti ber viðskeytið __lotuparun til að útiloka þögla samsteypu við ats_lookup_by_quarter (sem nær aðeins til 2025Q2). traust=true (þröskuldur 300 pör). ci_lo/ci_hi eru p25/p75 hlutfallsins, ekki öryggisbil.')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- list_to_sale_over_asking_share__lotuparun__2026Q2
--   heimild: D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts
--            KAUPVERD_VS_ASETT[fj=2026Q2].yfir
INSERT INTO public.model_metrics_scalar
  (metric_name, metric_value, unit, numerator, denominator, denominator_def, se, ci_lo, ci_hi, computed_on, model_version, source_path, source_section, source_dated, status, never_sum_with, supersedes_value, supersedes_source, notes)
VALUES
  ('list_to_sale_over_asking_share__lotuparun__2026Q2', 4.14, 'pct', 19.0, 459.0, 'Auglýsingalotur (scraper.listing_sessions, evalue-safnið) paraðar við þinglýsta íbúðarkaupsamninga (semantic._sales_base): fyrsta sala sama fastnúmers −30 til +180 daga frá lotulokum, hlutfall innan [0,5;2,0], ásett > 5 M kr. ÖNNUR PÖRUN EN ats_lookup_by_quarter — systkinamæling, ALDREI framhald sömu raðar. Lotusafnið endar 2026-04-15.', NULL, NULL, NULL, '2026-08-06', 'ekki_likansmaeling', 'D:\verdmat-is\verdmat-ai\content\markadur\fastgreiningar.ts', 'KAUPVERD_VS_ASETT[fj=2026Q2].yfir', '2026-08-06', 'BIRTANLEG', NULL, NULL, NULL, 'GAT-LISTI cc163 lína 2. Heiti ber viðskeytið __lotuparun til að útiloka þögla samsteypu við ats_lookup_by_quarter (sem nær aðeins til 2025Q2). traust=true (þröskuldur 300 pör).')
ON CONFLICT (metric_name, model_version, computed_on) DO UPDATE SET
  metric_value = EXCLUDED.metric_value, unit = EXCLUDED.unit, numerator = EXCLUDED.numerator, denominator = EXCLUDED.denominator, denominator_def = EXCLUDED.denominator_def, se = EXCLUDED.se, ci_lo = EXCLUDED.ci_lo, ci_hi = EXCLUDED.ci_hi, source_path = EXCLUDED.source_path, source_section = EXCLUDED.source_section, source_dated = EXCLUDED.source_dated, status = EXCLUDED.status, never_sum_with = EXCLUDED.never_sum_with, supersedes_value = EXCLUDED.supersedes_value, supersedes_source = EXCLUDED.supersedes_source, notes = EXCLUDED.notes;

-- ---------------------------------------------------------------------
-- HLIÐ: engin röð má hafa sloppið inn án nefnara eða án heimildar.
-- ---------------------------------------------------------------------
-- Hliðið telur AÐEINS raðir þessarar lotu (ekki count(*) á töfluna) svo
-- síðari lotur sem bæta við röðum felli það ekki ranglega.
DO $$
DECLARE
  v_n int; v_vantar int;
  v_nofn text[] := ARRAY['holdout30_n_pairs',
    'holdout30_mape',
    'holdout30_med_ape',
    'holdout30_level_bias',
    'holdout30_cov80',
    'holdout30_cov95',
    'fresh_edge_n_pairs',
    'fresh_edge_mape',
    'fresh_edge_cov80',
    'holdout30_mape__property_type_sfh_detached',
    'holdout30_cov80__property_type_sfh_detached',
    'holdout30_mape__price_band_yfir100m',
    'holdout30_cov80__price_band_yfir100m',
    'astand__eldhus_allt__slaemt_m2_m1',
    'astand__eldhus_allt__gott_1',
    'astand__eldhus_allt__uppgert_2_3',
    'astand__eldhus_2023plus__slaemt_m2_m1',
    'astand__eldhus_2023plus__gott_1',
    'astand__eldhus_2023plus__uppgert_2_3',
    'astand__innra_skor__slaemt_undirm05',
    'astand__innra_skor__gott_05m15',
    'astand__innra_skor__uppgert_yfir15',
    'astand__needs_work__needs_immediate_work',
    'astand__eldhus_allt__parud_sella_midgildi',
    'list_to_sale_median__lotuparun__2025Q3',
    'list_to_sale_over_asking_share__lotuparun__2025Q3',
    'list_to_sale_median__lotuparun__2025Q4',
    'list_to_sale_over_asking_share__lotuparun__2025Q4',
    'list_to_sale_median__lotuparun__2026Q1',
    'list_to_sale_over_asking_share__lotuparun__2026Q1',
    'list_to_sale_median__lotuparun__2026Q2',
    'list_to_sale_over_asking_share__lotuparun__2026Q2'];
BEGIN
  SELECT count(*) INTO v_n FROM public.model_metrics_scalar
   WHERE metric_name = ANY(v_nofn);
  IF v_n <> 32 THEN
    RAISE EXCEPTION 'raðafjöldi lotunnar % <> vænt 32', v_n;
  END IF;
  SELECT count(*) INTO v_vantar FROM public.model_metrics_scalar
   WHERE metric_name = ANY(v_nofn)
     AND (denominator IS NULL OR btrim(coalesce(denominator_def,'')) = ''
          OR left(source_path, 3) <> 'D:\');  -- ekki LIKE: \ er ESCAPE-stafur í LIKE
  IF v_vantar > 0 THEN
    RAISE EXCEPTION 'raðir án nefnara/skilgreiningar/heimildar: %', v_vantar;
  END IF;
END $$;

COMMIT;
