-- cc316b — DRÖG, ÓBEITT. Bíður GO Danna. Tvær nýjar töflur; snertir enga lifandi töflu, sýn eða fall.
-- Beiting um psycopg2 með lock_timeout, rollback sannaður fyrst (CLAUDE.md, cc231).
begin;
set local lock_timeout='5s';

-- Idempotens per texta og skema-útgáfu: sami texti er aldrei keyptur tvisvar undir sömu útgáfu.
create table scraper.lysing_eigindi_svar (
  lysing_hash  text not null,
  skema_utgafa integer not null,
  model        text not null,
  svar         jsonb not null,
  kostnadur_usd numeric(10,6),
  created_at   timestamptz not null default now(),
  primary key (lysing_hash, skema_utgafa)
);
revoke all on scraper.lysing_eigindi_svar from anon, authenticated;

-- Birtingartafla: já-gildi úr LLM-lestri á lýsingu virkrar auglýsingar. Aðeins birting í eigindaspjaldi.
create table public.lysing_eigindi (
  fastnum      bigint not null,
  attr_key     text   not null check (attr_key in ('lyfta','svalir','geymsla','verond_pallur','gardur')),
  value        jsonb  not null,
  lysing_hash  text   not null,
  skema_utgafa integer not null,
  source_date  date   not null,
  hladid_at    timestamptz not null default now(),
  primary key (fastnum, attr_key),
  -- „Ekki nefnt" er aldrei „nei": neikvætt gildi er ekki til í þessari töflu.
  constraint lysing_eigindi_adeins_ja check (value = '{"til":true}'::jsonb)
);
comment on table public.lysing_eigindi is
  'cc316b: já-gildi úr LLM-lestri á lýsingu virkrar auglýsingar. Aðeins birting; ekki líkaninntak, ekki verðleiðrétting, ekki property_attributes.';
alter table public.lysing_eigindi enable row level security;
revoke all on public.lysing_eigindi from anon, authenticated;
grant select on public.lysing_eigindi to service_role;
commit;
