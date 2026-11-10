-- cc329b: skrá HMS gildir fyrir bílskúr í vistaðri leit (ákvörðun Danna 10.11, V1). ÓBEITT; GO Danna þarf.
-- Rollback: supabase/rollback/20261110213000_cc329b_vistud_leit_skra_rollback.sql (skrifað fyrst).
--
-- `tafla = 'skraargogn'` þýðir: public.property_attributes með source='skraargogn' og superseded_at is null
-- (næturverkið, scripts/voktun_verk.py, varpar því). Aðeins gerd='bilskur' (value @> {"gerd":"bilskur"} nær líka
-- röðum með m2). staedi_bilakjallara og staedi eru ekki með: ákvörðunin nefnir bílskúr. Skráin ber engin „nei"-gildi.
-- Þetta er skrá, ekki sella sem stóðst blint úrtak; heimild dálksins segir það.
begin;
set local lock_timeout = '5s';

alter table public.vistud_leit_sella drop constraint vistud_leit_sella_tafla_check;
alter table public.vistud_leit_sella add constraint vistud_leit_sella_tafla_check
  check (tafla in ('auglysing_eigindi','lysing_eigindi','lysing_vidbot','lysing_astand','skraargogn'));

insert into public.vistud_leit_sella (eigind, tegund, tafla, attr_key, skilyrdi, heimild) values
  ('bilskur','apartment','skraargogn','bilskur_staedi','{"gerd": "bilskur"}','Skrá HMS; ákvörðun Danna 10.11 (V1), SKIL_CC329 §00b'),
  ('bilskur','house','skraargogn','bilskur_staedi','{"gerd": "bilskur"}','Skrá HMS; ákvörðun Danna 10.11 (V1), SKIL_CC329 §00b'),
  ('bilskur','townhouse','skraargogn','bilskur_staedi','{"gerd": "bilskur"}','Skrá HMS; ákvörðun Danna 10.11 (V1), SKIL_CC329 §00b');

do $$ begin
  if (select count(*) from public.vistud_leit_sella) <> 25 then
    raise exception 'cc329b: sellufjöldi ekki 25';
  end if;
  if has_table_privilege('anon', 'public.vistud_leit_sella', 'select') or has_table_privilege('authenticated', 'public.vistud_leit_sella', 'select') then
    raise exception 'cc329b: vistud_leit_sella opin fyrir anon/authenticated';
  end if;
end $$;
commit;
