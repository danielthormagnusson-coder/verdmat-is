-- cc320 rollback. Skrifað á undan migration (WP). Eyðir öllum áskrifendum, atburðum og sendingaskrá vöktunar.
-- Snertir ekkert annað. Keyrt um psycopg2 með lock_timeout.
begin;
set local lock_timeout = '5s';
drop table if exists public.voktun_sendur;
drop table if exists public.voktun_tak;
drop table if exists public.notandi_eigindi;
drop table if exists public.voktun_samthykki;
drop table if exists public.voktun_askrift;
drop table if exists public.voktun_atburdur;
drop table if exists public.voktun_seldist;
drop table if exists public.voktun_hradi;
drop table if exists public.voktun_bann;
drop table if exists public.voktun_askrifandi;
do $$ begin
  if exists (select 1 from information_schema.tables where table_schema='public' and (table_name like 'voktun\_%' or table_name='notandi_eigindi')) then
    raise exception 'cc320 rollback: tafla lifir';
  end if;
end $$;
commit;
