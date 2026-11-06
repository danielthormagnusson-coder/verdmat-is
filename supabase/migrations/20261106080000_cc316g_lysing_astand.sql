-- cc316g (GO Danna 06.11.2026). Ný tafla: ástand úr lýsingu virkrar auglýsingar, aðeins birting. Snertir enga lifandi töflu, sýn eða fall.
-- Hvorki property_attributes né lykillinn oskradir_fm (lib/krass.ts): ekkert hér fer í verðleiðréttingu, stærð, verð á m² né nefnara.
begin;
set local lock_timeout='5s';

create table public.lysing_astand (
  fastnum      bigint not null,
  attr_key     text   not null check (attr_key in ('eldhus','golfefni','gluggar','thak','almennt','oskrad')),
  stada        text   not null check (stada in ('endurnyjad','nefnt')),
  ar           integer check (ar between 1900 and 2100),
  m2           numeric check (m2 > 0),
  lysing_hash  text   not null,
  source_date  date   not null,
  hladid_at    timestamptz not null default now(),
  primary key (fastnum, attr_key),
  -- Óskráð rými er „nefnt", aldrei staðhæfing; ártal á aðeins við endurnýjun, fermetrar aðeins við óskráð rými.
  constraint lysing_astand_samraemi check (
    (attr_key = 'oskrad' and stada = 'nefnt' and ar is null)
    or (attr_key <> 'oskrad' and stada = 'endurnyjad' and m2 is null)
  )
);
comment on table public.lysing_astand is
  'cc316g: endurnýjun og óskráð rými úr LLM-lestri á lýsingu virkrar auglýsingar. Aðeins birting; ekki líkaninntak, ekki verðleiðrétting, ekki property_attributes.';
alter table public.lysing_astand enable row level security;
revoke all on public.lysing_astand from anon, authenticated;
grant select on public.lysing_astand to service_role;
commit;
