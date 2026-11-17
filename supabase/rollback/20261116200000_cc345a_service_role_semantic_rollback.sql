-- cc345a ROLLBACK — tekur aftur SELECT sem cc345a gaf service_role (service_role hafði ekkert á þessum 18 hlutum 16.11 19:20 UTC).
-- ATH: ekki keyra á meðan kóði cc345 (SSR á service_role) er á www — þá fellur /markadur, /svaedi, /verdvaktin, /nybyggingar.
begin;
set local lock_timeout = '5s';
revoke select on
  semantic.manadarsala_yoy, semantic.nybygging_einingar, semantic.nybygging_solur_manadar, semantic.nybygging_verkefni,
  semantic.v_hood_heat, semantic.v_matsvaedi_prices_yearly, semantic.v_matsvaedi_trend_quarterly, semantic.v_model_vs_sold_by_hood,
  semantic.v_newbuild_share, semantic.v_price_distribution_by_hood, semantic.v_street_prices, semantic.v_summerhouse_market,
  semantic.v_sveitarfelag_market, semantic.v_verdvakt_afsala, semantic.v_verdvakt_breytingar_v2, semantic.v_verdvakt_nefnarar_svaedi_v2,
  semantic.v_verdvakt_nefnarar_v2, semantic.verdvakt_hbs_postnr
from service_role;
commit;
notify pgrst, 'reload schema';
