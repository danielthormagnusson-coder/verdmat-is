-- cc329: vistuð leit (endurkomuhugmynd 2 af 5, ákvörðun Danna 06.11). ÓBEITT; GO Danna þarf.
-- Rollback: supabase/rollback/20261107230000_cc329_vistud_leit_rollback.sql (skrifað fyrst).
--
-- Ein ný tafla: hvaða sellur (eigind × tegund × lind) mega láta eign passa við eigind í vistaðri leit.
-- Aðeins sellur sem stóðust blint úrtak (rangt já <= 2 %, birt >= 15). Heimild = SKIL-skrá og lína.
-- Eign passar ef til er röð í `tafla` með `attr_key` sem uppfyllir `skilyrdi` (value @> skilyrdi; í lysing_astand:
-- jsonb_build_object('stada', stada) @> skilyrdi), OG tegund nýjustu auglýsingar = `tegund`. Engin röð = óþekkt,
-- aldrei „nei" (cc316: 0/false er ekki nei). Skrá HMS (property_attributes) er EKKI sella hér: hún stóðst ekki blint
-- úrtak heldur er skrá; sjá SKIL_CC329 §ákvarðanir.
-- Næturverkið (scripts/voktun_verk.py) les töfluna; www les hana ekki (listinn er speglaður í lib/vistud-leit.ts og
-- prófaður gegn þessari skrá).
begin;
set local lock_timeout = '5s';

create table public.vistud_leit_sella (
  eigind    text not null check (eigind in ('lyfta','svalir','bilskur','verond','gardur','serinngangur','eldhus','bad')),
  tegund    text not null check (tegund in ('apartment','house','townhouse')),
  tafla     text not null check (tafla in ('auglysing_eigindi','lysing_eigindi','lysing_vidbot','lysing_astand')),
  attr_key  text not null check (attr_key ~ '^[a-z_]{2,40}$'),
  skilyrdi  jsonb not null check (jsonb_typeof(skilyrdi) = 'object' and skilyrdi <> '{}'::jsonb
                                  and not skilyrdi @> '{"til": false}'::jsonb and not skilyrdi @> '{"gerd": "ekkert"}'::jsonb),
  heimild   text not null check (length(heimild) between 5 and 200),
  primary key (eigind, tegund, tafla, attr_key)
);

insert into public.vistud_leit_sella (eigind, tegund, tafla, attr_key, skilyrdi, heimild) values
  ('lyfta','apartment','auglysing_eigindi','lyfta','{"til": true}','SKIL_CC316 §1 l.70 (0 fals-já/30), §3 l.119'),
  ('lyfta','apartment','lysing_eigindi','lyfta','{"til": true}','SKIL_CC316 cc316c §2 l.415 (0/54)'),
  ('svalir','apartment','auglysing_eigindi','svalir','{"til": true}','SKIL_CC316 §1 l.71 (0 fals-já/34), §3 l.120'),
  ('svalir','apartment','lysing_eigindi','svalir','{"til": true}','SKIL_CC316 cc316c §2 l.416 (2/108)'),
  ('svalir','house','lysing_eigindi','svalir','{"til": true}','SKIL_CC316 cc316d §2 l.486 (0/39)'),
  ('svalir','townhouse','lysing_eigindi','svalir','{"til": true}','SKIL_CC316 cc316d §2 l.491 (0/38)'),
  ('bilskur','apartment','auglysing_eigindi','bilskur_staedi','{"gerd": "bilskur_eda_geymsla"}','SKIL_CC316 §1 l.73 (0 fals-já/25), §3 l.121'),
  ('bilskur','house','lysing_vidbot','bilskur_staedi','{"gerd": "bilskur"}','SKIL_CC319 §1 l.51 (1/180)'),
  ('bilskur','townhouse','lysing_vidbot','bilskur_staedi','{"gerd": "bilskur"}','SKIL_CC319 §1 l.51 (0/95)'),
  ('verond','apartment','lysing_eigindi','verond_pallur','{"til": true}','SKIL_CC316 cc316c §2 l.418 (0/32)'),
  ('verond','house','lysing_eigindi','verond_pallur','{"til": true}','SKIL_CC316 cc316d §2 l.488 (0/81)'),
  ('verond','townhouse','lysing_eigindi','verond_pallur','{"til": true}','SKIL_CC316 cc316d §2 l.493 (0/81)'),
  ('gardur','apartment','lysing_eigindi','gardur','{"til": true}','SKIL_CC316 cc316c §2 l.419 (0/16)'),
  ('gardur','house','lysing_eigindi','gardur','{"til": true}','SKIL_CC316 cc316d l.489 (0/68), cc316f l.648 (0/30)'),
  ('gardur','townhouse','lysing_eigindi','gardur','{"til": true}','SKIL_CC316 cc316d l.494 (0/63), cc316f l.649 (0/36)'),
  ('serinngangur','apartment','lysing_vidbot','serinngangur','{"til": true}','SKIL_CC319 §1 l.44 (1/78)'),
  ('eldhus','apartment','lysing_astand','eldhus','{"stada": "endurnyjad"}','SKIL_CC316 cc316g l.727 (0/25), l.757'),
  ('eldhus','house','lysing_astand','eldhus','{"stada": "endurnyjad"}','SKIL_CC316 cc316g l.733 (0/14), l.758'),
  ('eldhus','townhouse','lysing_vidbot','eldhus_astand','{"stada": "endurnyjad"}','SKIL_CC319 §1 l.65 (0/17)'),
  ('bad','apartment','lysing_vidbot','badherbergi_astand','{"stada": "endurnyjad"}','SKIL_CC319 §1 l.66 (0/93)'),
  ('bad','house','lysing_vidbot','badherbergi_astand','{"stada": "endurnyjad"}','SKIL_CC319 §1 l.66 (0/63)'),
  ('bad','townhouse','lysing_vidbot','badherbergi_astand','{"stada": "endurnyjad"}','SKIL_CC319 §1 l.66 (0/16)');

-- Ekki app-lesin: RLS án stefnu, engar heimildir anon/authenticated (ný public-tafla kemur annars með anon=arwdDxtm).
alter table public.vistud_leit_sella enable row level security;
revoke all on public.vistud_leit_sella from public, anon, authenticated;
grant select on public.vistud_leit_sella to service_role;

do $$ begin
  if has_table_privilege('anon', 'public.vistud_leit_sella', 'select') or has_table_privilege('authenticated', 'public.vistud_leit_sella', 'select')
     or has_table_privilege('anon', 'public.vistud_leit_sella', 'insert') or has_table_privilege('authenticated', 'public.vistud_leit_sella', 'delete') then
    raise exception 'cc329: vistud_leit_sella opin fyrir anon/authenticated';
  end if;
  if (select count(*) from public.vistud_leit_sella) <> 22 then
    raise exception 'cc329: sellufjöldi rangur';
  end if;
end $$;
commit;
