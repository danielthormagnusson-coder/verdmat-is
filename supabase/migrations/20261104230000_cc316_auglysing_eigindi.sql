-- cc316 (GO Danna 04.11.2026). Ein ný tafla; snertir enga lifandi töflu, sýn eða fall.
-- Aðeins www-þjónninn les (service_role, lesThjonn); anon og authenticated fá ekkert (sbr. cc304).
-- Beiting um psycopg2 með lock_timeout (feedback_ddl_um_psycopg2).
begin;
set local lock_timeout='5s';

create table public.auglysing_eigindi (
  fastnum      bigint not null,
  attr_key     text   not null check (attr_key in ('lyfta','svalir','bilskur_staedi')),
  value        jsonb  not null,
  source       text   not null default 'mbl_reitur',
  source_listing_id text not null,   -- nýjasta auglýsing eignarinnar
  source_date  date   not null,      -- listed_at, ella first_seen_at, þeirrar auglýsingar
  hladid_at    timestamptz not null default now(),
  primary key (fastnum, attr_key),
  -- „Nei" er ekki til í þessari töflu: reitur mbl greinir ekki nei frá „ekki fyllt út" (SKIL_CC316 §2).
  constraint auglysing_eigindi_adeins_ja check (
    (attr_key in ('lyfta','svalir') and value = '{"til":true}'::jsonb)
    or (attr_key = 'bilskur_staedi' and value->>'gerd' in ('staedi_bilakjallara','bilskur_eda_geymsla','staedi'))
  )
);
comment on table public.auglysing_eigindi is
  'cc316: já-gildi úr strúktúreruðum reitum virkrar mbl-auglýsingar. Aðeins birting í eigindaspjaldi; ekki líkaninntak, ekki property_attributes.';

alter table public.auglysing_eigindi enable row level security;
revoke all on public.auglysing_eigindi from anon, authenticated;
grant select on public.auglysing_eigindi to service_role;
-- Hleðarinn notar sömu tengingu og næturkeðjan (.dbconfig, eigandi); engin önnur skrif.
commit;
