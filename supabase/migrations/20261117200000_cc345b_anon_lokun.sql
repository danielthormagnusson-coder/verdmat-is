-- cc345b (flokkur B): anon (publishable-lykillinn) og authenticated missa beinan lesaðgang að gagnafletinum.
-- Forsenda: kóði cc345 á www (SSR les með þjónslykli, EignSearch-einingar um /api/einingar) + cc345a beitt
-- + 24 klst edge_logs með 0 sb_publishable-köllum frá Vercel á þessa hluti.
-- ÓBREYTT af ásettu ráði: semantic.fasteignasala_{manudur,nefnarar,nyb_stadir} (RLS-sía á óbirtum sölum, service_role
-- sniðgengur RLS) og property_attributes fyrir authenticated (own_notandi_rows; SAFNA=false í dag). PostGIS utan valds.
begin;
set local lock_timeout = '5s';
revoke all on public.ats_dashboard_monthly_heat, public.comps_index_v2, public.comps_t5_basis, public.last_listing_text, public.llm_aggregates_quarterly, public.model_tracking_history, public.predictions_rent, public.repeat_sale_index_stada, public.sales_history, public.v_eign_myndir, public.v_fjoleining_fastnum, public.valuation_tiers, public.valuation_tiers_rent, public.poi, public.property_images, public.v_current_predictions, public.v_properties, public.v_repeat_sale_index, public.latest_regime_per_cell, public.regime_per_cell_monthly, public.repeat_sale_index_by_segment, public.repeat_sale_index_main_pooled from anon, authenticated;
revoke all on public.property_attributes from anon;
revoke select on public.properties from anon, authenticated;        -- fellir einnig dálkaréttindin (sannað í --prof)
revoke select on public.repeat_sale_index from anon, authenticated;
revoke all on semantic.manadarsala_yoy, semantic.nybygging_einingar, semantic.nybygging_solur_manadar, semantic.nybygging_verkefni, semantic.v_fasteignamat_keyrsla, semantic.v_fasteignamat_rodun, semantic.v_hood_heat, semantic.v_matsvaedi_prices_yearly, semantic.v_matsvaedi_trend_quarterly, semantic.v_model_vs_sold_by_hood, semantic.v_newbuild_share, semantic.v_price_distribution_by_hood, semantic.v_street_prices, semantic.v_summerhouse_market, semantic.v_sveitarfelag_lookup, semantic.v_sveitarfelag_market, semantic.v_verdvakt_afsala, semantic.v_verdvakt_breytingar_v2, semantic.v_verdvakt_nefnarar_svaedi_v2, semantic.v_verdvakt_nefnarar_v2, semantic.verdvakt_hbs_postnr from anon, authenticated;
revoke execute on function public.poi_naesta(bigint) from public, anon, authenticated;
revoke execute on function public.search_properties_grouped(text) from public, anon, authenticated;
do $$
declare r record; bad int := 0;
begin
  -- 1) anon les EKKERT í public/semantic nema fasteignasala_* (3) og PostGIS-hlutina
  for r in select c.oid::regclass::text o from pg_class c join pg_namespace n on n.oid=c.relnamespace
           where n.nspname in ('public','semantic') and c.relkind in ('r','v','m','p')
             and c.relname not in ('spatial_ref_sys','geometry_columns','geography_columns',
                                   'fasteignasala_manudur','fasteignasala_nefnarar','fasteignasala_nyb_stadir')
             and (has_table_privilege('anon',c.oid,'SELECT')
                  or exists (select 1 from pg_attribute a where a.attrelid=c.oid and a.attnum>0 and not a.attisdropped
                             and has_column_privilege('anon',c.oid,a.attname,'SELECT'))) loop
    raise warning 'anon les enn: %', r.o; bad := bad + 1;
  end loop;
  -- 2) engin app-föll keyranleg af anon
  for r in select p.oid::regprocedure::text o from pg_proc p join pg_namespace n on n.oid=p.pronamespace
           where n.nspname in ('public','semantic','scraper') and has_function_privilege('anon',p.oid,'EXECUTE')
             and not exists (select 1 from pg_depend d where d.objid=p.oid and d.deptype='e')
             and p.proname <> 'fable_orders_status_guard' loop
    raise warning 'anon keyrir enn: %', r.o; bad := bad + 1;
  end loop;
  -- 3) service_role heldur SELECT á öllu sem www les
  for r in select c.oid::regclass::text o from pg_class c join pg_namespace n on n.oid=c.relnamespace
           where (n.nspname, c.relname) in (select 'public', unnest(string_to_array('properties,sales_history,last_listing_text,valuation_tiers,valuation_tiers_rent,comps_index_v2,comps_t5_basis,predictions_rent,property_attributes,property_images,v_properties,v_current_predictions,v_eign_myndir,v_fjoleining_fastnum,v_repeat_sale_index,poi,llm_aggregates_quarterly,repeat_sale_index_main_pooled,repeat_sale_index_stada',',')))
             and not has_table_privilege('service_role',c.oid,'SELECT') loop
    raise warning 'service_role vantar: %', r.o; bad := bad + 1;
  end loop;
  if not has_function_privilege('service_role','public.poi_naesta(bigint)','EXECUTE')
     or not has_function_privilege('service_role','public.search_properties_grouped(text)','EXECUTE') then
    raise warning 'service_role vantar EXECUTE'; bad := bad + 1; end if;
  if bad > 0 then raise exception 'cc345b eftirathugun brást (% atriði)', bad; end if;
end $$;
commit;
notify pgrst, 'reload schema';
