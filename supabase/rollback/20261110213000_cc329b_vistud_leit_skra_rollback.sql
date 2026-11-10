-- cc329b rollback. Skrifað Á UNDAN migration (WP). Fjarlægir aðeins bílskúrssellur úr skrá HMS (tafla='skraargogn')
-- og setur CHECK á `tafla` aftur í fyrra horf. Hinar 22 sellur cc329 standa óhreyfðar.
begin;
set local lock_timeout = '5s';
delete from public.vistud_leit_sella where tafla = 'skraargogn';
alter table public.vistud_leit_sella drop constraint vistud_leit_sella_tafla_check;
alter table public.vistud_leit_sella add constraint vistud_leit_sella_tafla_check
  check (tafla in ('auglysing_eigindi','lysing_eigindi','lysing_vidbot','lysing_astand'));
do $$ begin
  if (select count(*) from public.vistud_leit_sella) <> 22 then
    raise exception 'cc329b rollback: sellufjöldi ekki 22';
  end if;
end $$;
commit;
