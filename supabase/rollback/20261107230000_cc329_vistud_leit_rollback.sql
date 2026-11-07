-- cc329 rollback. Skrifað Á UNDAN migration (WP). Eyðir aðeins sellutöflu vistaðrar leitar; snertir ekki
-- vöktunartöflur cc320 (áskriftir með tegund='leit' standa, en næturverkið sendir þeim ekkert án sellutöflu).
-- Keyrt um psycopg2 með lock_timeout, aldrei MCP apply_migration.
begin;
set local lock_timeout = '5s';
drop table if exists public.vistud_leit_sella;
do $$ begin
  if to_regclass('public.vistud_leit_sella') is not null then
    raise exception 'cc329 rollback: vistud_leit_sella lifir';
  end if;
end $$;
commit;
