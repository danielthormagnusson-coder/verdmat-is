-- cc345a (flokkur B, AÐEINS VIÐBÓT): service_role fær SELECT á semantic-hlutina sem www les SSR í dag með anon.
-- Forsenda kóða cc345 (SSR les með þjónslykli). Enginn missir neitt. fasteignasala_* (3) undanskildar af ásettu ráði:
-- RLS-stefna fasteignasala_manudur síar óbirtar sölur og service_role sniðgengur RLS — þær eru áfram lesnar með anon.
begin;
set local lock_timeout = '5s';
grant select on
  semantic.manadarsala_yoy, semantic.nybygging_einingar, semantic.nybygging_solur_manadar, semantic.nybygging_verkefni,
  semantic.v_hood_heat, semantic.v_matsvaedi_prices_yearly, semantic.v_matsvaedi_trend_quarterly, semantic.v_model_vs_sold_by_hood,
  semantic.v_newbuild_share, semantic.v_price_distribution_by_hood, semantic.v_street_prices, semantic.v_summerhouse_market,
  semantic.v_sveitarfelag_market, semantic.v_verdvakt_afsala, semantic.v_verdvakt_breytingar_v2, semantic.v_verdvakt_nefnarar_svaedi_v2,
  semantic.v_verdvakt_nefnarar_v2, semantic.verdvakt_hbs_postnr
to service_role;
do $$
declare r record; bad int := 0;
begin
  for r in select c.oid::regclass::text o from pg_class c join pg_namespace n on n.oid=c.relnamespace
           where n.nspname='semantic' and has_table_privilege('anon',c.oid,'SELECT')
             and c.relname not like 'fasteignasala\_%' and not has_table_privilege('service_role',c.oid,'SELECT') loop
    raise warning 'service_role vantar enn SELECT: %', r.o; bad := bad + 1;
  end loop;
  if bad > 0 then raise exception 'cc345a eftirathugun brást (% hlutir)', bad; end if;
end $$;
commit;
notify pgrst, 'reload schema';
