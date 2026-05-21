-- Phase X Group B Part 2: read-only views layer.
--
-- All views declare WITH (security_invoker = on) explicitly. Postgres 15+ defaults
-- views to security DEFINER semantics (run as view owner), which would silently
-- bypass any future RLS on the underlying table. security_invoker forces the
-- view to run with the calling role's permissions, so RLS policies on the
-- underlying tables apply as expected. This closes Bug 25.
--
-- GRANTs to anon + authenticated are explicit. The underlying tables currently
-- also have anon/authenticated SELECT grants (see 20260506_rls_baseline_audit);
-- a follow-up session will REVOKE direct table access from anon/authenticated
-- once the frontend has been switched to read from views and prod has been
-- confirmed stable.
--
-- ----------------------------------------------------------------------------
-- Rollback (manual, not auto-executed):
-- ----------------------------------------------------------------------------
--   DROP VIEW IF EXISTS public.v_current_predictions  CASCADE;
--   DROP VIEW IF EXISTS public.v_ats_lookup_by_heat   CASCADE;
--   DROP VIEW IF EXISTS public.v_repeat_sale_index    CASCADE;
--   DROP VIEW IF EXISTS public.v_properties           CASCADE;
-- ----------------------------------------------------------------------------

-- v_properties: 43-column public allowlist. Hides 4 internal columns:
--   * landeign_nr            - HMS land-parcel ID, not consumed by frontend
--   * matseiningar (jsonb)   - HMS sub-unit array, Phase Z UI will design surface
--   * tengd_stadfang_nr      - HMS staðfang cross-refs, Phase Y join-internal only
--   * deregistered           - HMS ghost flag; view filters deregistered IS NOT TRUE
-- augl_id_latest is INCLUDED per HALT 2 decision (Bug 26 is being raised to
-- "fix via server-side rendered deep-link href with service key", not column-strip).
CREATE VIEW public.v_properties WITH (security_invoker = on) AS
  SELECT
    fastnum, heimilisfang, husnr, postnr, postheiti, svfn, sveitarfelag,
    tegund_raw, canonical_code, unit_category, unit_family,
    is_residential, is_summerhouse, is_new_build, is_main_unit,
    einflm, lod_flm, byggar, fjherb, fullbuid,
    lat, lng,
    matsvaedi_numer, matsvaedi_nafn, matsvaedi_bucket, region_tier,
    fasteignamat, fasteignamat_gildandi, fasteignamat_naesta_ar,
    brunabotamat, lhlmat,
    byggingarstig, skodags, gerd, matsstig,
    augl_id_latest, list_price_latest, effective_date_latest,
    scraped_at_latest, lysing_truncated,
    first_photo_url, photo_urls_json, n_photos
  FROM public.properties
  WHERE deregistered IS NOT TRUE;

GRANT SELECT ON public.v_properties TO anon, authenticated;

-- v_repeat_sale_index: passthrough of the 15-column repeat-sale BMN index.
-- All columns are market-aggregate (per cell x quarter), no PII.
CREATE VIEW public.v_repeat_sale_index WITH (security_invoker = on) AS
  SELECT
    canonical_code, region_tier, year, quarter, period,
    index_value_nominal, log_index_nominal, std_error_nominal,
    index_value_real, log_index_real, std_error_real,
    n_pairs_in_period, cell_n_pairs, insufficient_sample, data_quality
  FROM public.repeat_sale_index;

GRANT SELECT ON public.v_repeat_sale_index TO anon, authenticated;

-- v_ats_lookup_by_heat: wraps public.ats_lookup ("Table B" -- pooled per
-- (canonical_code, region_tier, heat_bucket)). View name follows doc-canonical
-- naming used elsewhere in the codebase ("by_heat"); underlying table is the
-- empirical name. Optional table rename deferred to Group C.
CREATE VIEW public.v_ats_lookup_by_heat WITH (security_invoker = on) AS
  SELECT
    id, canonical_code, region_tier, heat_bucket, n_pairs,
    median_log_ratio, dispersion_sd, dispersion_mad, above_list_rate,
    n_quarters_pooled, data_quality, p33, p67, median_overall, n_qtrs_stable
  FROM public.ats_lookup;

GRANT SELECT ON public.v_ats_lookup_by_heat TO anon, authenticated;

-- v_current_predictions: latest prediction per fastnum. DISTINCT ON is currently
-- a no-op (predictions has exactly one row per fastnum at iter4) but is written
-- forward-safe for the future schema where predicted_at gets promoted to
-- timestamptz and multiple rows per fastnum may co-exist. Backlog note:
-- predicted_at as DATE is insufficient for robust latest-selection; tracked
-- for replacement by scored_at timestamptz in a later cycle.
CREATE VIEW public.v_current_predictions WITH (security_invoker = on) AS
  SELECT DISTINCT ON (fastnum)
    fastnum,
    real_pred_mean, real_pred_median,
    real_pred_lo80, real_pred_hi80,
    real_pred_lo95, real_pred_hi95,
    model_group, segment,
    model_version, calibration_version,
    predicted_at
  FROM public.predictions
  ORDER BY fastnum, predicted_at DESC;

GRANT SELECT ON public.v_current_predictions TO anon, authenticated;
