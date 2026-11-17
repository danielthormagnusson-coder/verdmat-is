-- cc345b ROLLBACK — endurheimtir anon/authenticated-ACL nákvæmlega eins og mælt 16.11.2026 19:25 UTC (relacl í A1_acl_fyrir.json).
-- Keyrt strax ef einhver síða fellur eftir cc345b. Afturkræft, engin gögn snert.
begin;
set local lock_timeout = '5s';
grant select on public.ats_dashboard_monthly_heat, public.comps_index_v2, public.comps_t5_basis, public.last_listing_text, public.llm_aggregates_quarterly, public.model_tracking_history, public.predictions_rent, public.repeat_sale_index_stada, public.sales_history, public.v_eign_myndir, public.v_fjoleining_fastnum, public.valuation_tiers, public.valuation_tiers_rent to anon, authenticated;
grant select, references on public.poi, public.property_images, public.v_current_predictions, public.v_properties, public.v_repeat_sale_index to anon, authenticated;
grant select, references, trigger, maintain on public.latest_regime_per_cell, public.regime_per_cell_monthly, public.repeat_sale_index_by_segment, public.repeat_sale_index_main_pooled to anon, authenticated;
grant select, references on public.property_attributes to anon;
grant select (fastnum, heimilisfang, husnr, postnr, postheiti, svfn, sveitarfelag, tegund_raw, canonical_code, unit_category, unit_family, is_residential, is_summerhouse, einflm, lod_flm, byggar, fjherb, fullbuid, is_new_build, is_main_unit, lat, lng, matsvaedi_numer, matsvaedi_nafn, matsvaedi_bucket, region_tier, fasteignamat, fasteignamat_gildandi, augl_id_latest, list_price_latest, lysing_truncated, scraped_at_latest, first_photo_url, photo_urls_json, n_photos, effective_date_latest, brunabotamat, lhlmat, fasteignamat_naesta_ar, byggingarstig, skodags, gerd, matsstig, deregistered) on public.properties to anon, authenticated;  -- 44 af 50 dálkum, mælt 16.11
grant select (canonical_code, region_tier, year, quarter, period, index_value_nominal, log_index_nominal, std_error_nominal, index_value_real, log_index_real, std_error_real, n_pairs_in_period, cell_n_pairs, insufficient_sample, data_quality) on public.repeat_sale_index to anon, authenticated;
grant select on semantic.manadarsala_yoy, semantic.nybygging_einingar, semantic.nybygging_solur_manadar, semantic.nybygging_verkefni, semantic.v_fasteignamat_keyrsla, semantic.v_fasteignamat_rodun, semantic.v_hood_heat, semantic.v_matsvaedi_prices_yearly, semantic.v_matsvaedi_trend_quarterly, semantic.v_model_vs_sold_by_hood, semantic.v_newbuild_share, semantic.v_price_distribution_by_hood, semantic.v_street_prices, semantic.v_summerhouse_market, semantic.v_sveitarfelag_lookup, semantic.v_sveitarfelag_market, semantic.v_verdvakt_afsala, semantic.v_verdvakt_breytingar_v2, semantic.v_verdvakt_nefnarar_svaedi_v2, semantic.v_verdvakt_nefnarar_v2, semantic.verdvakt_hbs_postnr to anon, authenticated;
grant execute on function public.poi_naesta(bigint) to anon, authenticated;
grant execute on function public.search_properties_grouped(text) to public, anon, authenticated;
commit;
notify pgrst, 'reload schema';
