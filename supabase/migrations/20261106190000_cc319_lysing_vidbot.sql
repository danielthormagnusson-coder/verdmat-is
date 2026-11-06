-- cc319 (GO Danna 06.11.2026). Ný tafla: fleiri eigindi úr lýsingu virkrar auglýsingar, aðeins birting. Snertir enga lifandi töflu, sýn eða fall.
-- Hvorki property_attributes né lykillinn oskradir_fm (lib/krass.ts): ekkert hér fer í verðleiðréttingu, stærð, verð á m² né nefnara.
begin;
set local lock_timeout='5s';

create table public.lysing_vidbot (
  fastnum      bigint not null,
  attr_key     text   not null check (attr_key in (
    'serinngangur','lofthaed','arinn','opid_rymi','endaeining','heitur_pottur','ev_hledsla','bilskur_staedi','thvottahus','lodarat','utsyni',
    'golfefni','herbergi','badherbergi',
    'badherbergi_astand','eldhus_astand','gluggar_lysing','lagnir_lysing','thak_lysing',
    'ar:eldhus','ar:golfefni','ar:almennt')),
  value        jsonb  not null,
  lysing_hash  text   not null,
  skema_utgafa integer not null,
  source_date  date   not null,
  hladid_at    timestamptz not null default now(),
  primary key (fastnum, attr_key),
  -- Aldrei „nei": þögn og neikvætt svar birtast sem Óþekkt.
  constraint lysing_vidbot_aldrei_nei check (
    jsonb_typeof(value) = 'object'
    and value <> '{}'::jsonb
    and coalesce(value->>'til', 'true') = 'true'
    and coalesce(value->>'gerd', '') <> 'ekkert'
  )
);
comment on table public.lysing_vidbot is
  'cc319: já úr LLM-lestri á lýsingu virkrar auglýsingar, aðeins sellur sem stóðust blint úrtak. Aðeins birting; ekki líkaninntak, ekki verðleiðrétting, ekki property_attributes.';
alter table public.lysing_vidbot enable row level security;
revoke all on public.lysing_vidbot from anon, authenticated;
grant select on public.lysing_vidbot to service_role;
commit;
