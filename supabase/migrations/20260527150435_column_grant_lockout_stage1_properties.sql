-- Phase X Group B column-grant lockout — Stage 1 (public.properties)
--
-- Replaces blanket SELECT ON public.properties FROM {anon, authenticated}
-- with a 44-column allowlist (43 v_properties-projected columns +
-- `deregistered` for the view's WHERE clause).
--
-- Excluded (3 columns; not exposed to anon/authenticated):
--   landeign_nr        — HMS lot ID; D4 server-side joins only
--   matseiningar       — jsonb sub-unit array; Phase Z UI decides surface
--   tengd_stadfang_nr  — jsonb cross-stadfang refs; D4 join material
--
-- augl_id_latest stays IN allowlist (intentional per 2026-05-21 DECISIONS):
-- exposing fastnum↔augl_id was already true on the base table; v_properties
-- adds no exposure. Bug 26 fix is SSR deep-link via service-role key, not
-- column-strip. This lockout does NOT close the fastnum↔augl_id leak.
--
-- Value delivered: (1) 3-column exclusion enforced at PostgREST layer;
-- (2) default-deny on any future column added to public.properties — any
-- new v_properties projection MUST add a matching GRANT or the view 42501s.
--
-- Verification (post-COMMIT, run as anon role):
--   SELECT count(*) FROM v_properties;         -- must equal pre-lockout
--   SELECT landeign_nr FROM properties LIMIT 1; -- MUST raise 42501

BEGIN;

REVOKE SELECT ON public.properties FROM anon;
REVOKE SELECT ON public.properties FROM authenticated;

GRANT SELECT (
  fastnum, heimilisfang, husnr, postnr, postheiti, svfn, sveitarfelag,
  tegund_raw, canonical_code, unit_category, unit_family,
  is_residential, is_summerhouse, is_new_build, is_main_unit,
  einflm, lod_flm, byggar, fjherb, fullbuid,
  lat, lng, matsvaedi_numer, matsvaedi_nafn, matsvaedi_bucket, region_tier,
  fasteignamat, fasteignamat_gildandi, fasteignamat_naesta_ar,
  brunabotamat, lhlmat, byggingarstig, skodags, gerd, matsstig,
  augl_id_latest, list_price_latest, effective_date_latest, scraped_at_latest,
  lysing_truncated, first_photo_url, photo_urls_json, n_photos,
  deregistered
) ON public.properties TO anon;

GRANT SELECT (
  fastnum, heimilisfang, husnr, postnr, postheiti, svfn, sveitarfelag,
  tegund_raw, canonical_code, unit_category, unit_family,
  is_residential, is_summerhouse, is_new_build, is_main_unit,
  einflm, lod_flm, byggar, fjherb, fullbuid,
  lat, lng, matsvaedi_numer, matsvaedi_nafn, matsvaedi_bucket, region_tier,
  fasteignamat, fasteignamat_gildandi, fasteignamat_naesta_ar,
  brunabotamat, lhlmat, byggingarstig, skodags, gerd, matsstig,
  augl_id_latest, list_price_latest, effective_date_latest, scraped_at_latest,
  lysing_truncated, first_photo_url, photo_urls_json, n_photos,
  deregistered
) ON public.properties TO authenticated;

COMMIT;
