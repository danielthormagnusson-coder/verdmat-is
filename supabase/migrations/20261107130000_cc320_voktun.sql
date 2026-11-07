-- cc320 áfangi B (GO Danna 07.11): vöktun með tölvupósti. Aðeins nýjar tóma töflur. Rollback: supabase/rollback/20261107130000_cc320_voktun_rollback.sql.
-- Aðgangur: aðeins service_role; anon og authenticated engin réttindi (ný public-tafla kemur með anon=arwdDxtm).
-- Lykill vaktaðs hlutar: eign/eignin_min = fastnum; gata = <postnr>/<gotuSlod>; postnr = <postnr>; leit = sha256 skilyrða; frettabref/manadarskyrsla = allt.
-- Tákn aðeins sem sha256. Engin IP í áskrifendatöflum. voktun_sendur ber engin netföng.
begin;
set local lock_timeout = '5s';

create table public.voktun_askrifandi (
  id              uuid primary key default gen_random_uuid(),
  netfang         text not null unique check (netfang = lower(btrim(netfang)) and length(netfang) between 6 and 254 and netfang like '%_@_%._%'),
  stofnad         timestamptz not null default now(),
  stadfest_at     timestamptz,
  endurnyjun_at   timestamptz not null default (now() + interval '12 months'),
  endurnyjun_send timestamptz
);

create table public.voktun_samthykki (
  askrifandi_id uuid not null references public.voktun_askrifandi(id) on delete cascade,
  tilgangur     text not null check (tilgangur in ('tilkynningar','markadsefni')),
  utgafa        text not null,
  veitt_at      timestamptz not null default now(),
  primary key (askrifandi_id, tilgangur)
);

create table public.voktun_askrift (
  id            uuid primary key default gen_random_uuid(),
  askrifandi_id uuid not null references public.voktun_askrifandi(id) on delete cascade,
  tegund        text not null check (tegund in ('eign','gata','postnr','leit','eignin_min','frettabref','manadarskyrsla')),
  lykill        text not null,
  heiti         text not null check (length(heiti) between 1 and 200),
  atburdir      text[] not null check (cardinality(atburdir) > 0),
  tidni         text not null check (tidni in ('strax','vikuleg')),
  vikudagur     smallint check (vikudagur between 1 and 7),
  einu_sinni    boolean not null default false,
  skilyrdi      jsonb,
  stofnad       timestamptz not null default now(),
  breytt        timestamptz not null default now(),
  stadfest_at   timestamptz,
  sidast_sent   timestamptz,
  unique (askrifandi_id, tegund, lykill),
  constraint voktun_vikudagur_chk check ((tidni = 'vikuleg') = (vikudagur is not null)),
  constraint voktun_skilyrdi_chk check ((tegund = 'leit') = (skilyrdi is not null)),
  constraint voktun_atburdir_chk check (
    (tegund = 'eign' and atburdir <@ array['a_solu','verd','selst','af_solu']::text[])
    or (tegund in ('gata','postnr') and atburdir <@ array['ny','laekkun','sala']::text[])
    or (tegund = 'leit' and atburdir <@ array['ny']::text[])
    or (tegund in ('eignin_min','frettabref','manadarskyrsla') and atburdir <@ array['utgafa']::text[])),
  constraint voktun_lykill_chk check (
    (tegund in ('eign','eignin_min') and lykill ~ '^[0-9]{7}$')
    or (tegund = 'gata' and lykill ~ '^[0-9]{3}/[a-z0-9-]{1,120}$')
    or (tegund = 'postnr' and lykill ~ '^[0-9]{3}$')
    or (tegund = 'leit' and lykill ~ '^[0-9a-f]{64}$')
    or (tegund in ('frettabref','manadarskyrsla') and lykill = 'allt'))
);
create index voktun_askrift_samkeyrsla_idx on public.voktun_askrift (tegund, lykill);
create index voktun_askrift_askrifandi_idx on public.voktun_askrift (askrifandi_id);

-- Staðreyndir sem næturverk finnur. Opinber gögn, engin tenging við áskrifanda. lykill tryggir eina röð per atburð.
create table public.voktun_atburdur (
  id           bigint generated always as identity primary key,
  lykill       text not null unique,
  tegund       text not null check (tegund in ('ny','verd','sala','af_solu','utgafa')),
  fastnum      bigint,
  gata_lykill  text,
  postnr       integer,
  gogn         jsonb not null,
  atburdar_at  timestamptz not null,
  fundid_at    timestamptz not null default now()
);
create index voktun_atburdur_fundid_idx on public.voktun_atburdur (fundid_at);
create index voktun_atburdur_fastnum_idx on public.voktun_atburdur (fastnum);
create index voktun_atburdur_gata_idx on public.voktun_atburdur (gata_lykill);
create index voktun_atburdur_postnr_idx on public.voktun_atburdur (postnr);

create table public.voktun_sendur (
  id          bigint generated always as identity primary key,
  askrift_id  uuid not null references public.voktun_askrift(id) on delete cascade,
  atburdur_id bigint not null references public.voktun_atburdur(id) on delete cascade,
  sent_at     timestamptz not null default now(),
  resend_id   text,
  unique (askrift_id, atburdur_id)
);

-- (d) Skráð af notanda. EKKI property_attributes: getAttributes setur notanda efst og leiðrétting og spjall lesa það (regla 11).
create table public.notandi_eigindi (
  id            bigint generated always as identity primary key,
  fastnum       bigint not null,
  attr_key      text not null check (attr_key in ('lyfta','svalir','bilskur_staedi','eldhus_astand','badherbergi_astand')),
  value         jsonb not null check (jsonb_typeof(value) = 'object' and value <> '{}'::jsonb and not value @> '{"til": false}'::jsonb),
  askrifandi_id uuid not null references public.voktun_askrifandi(id) on delete cascade,
  stada         text not null default 'bida' check (stada in ('bida','stadfest','birt','hafnad')),
  stofnad       timestamptz not null default now(),
  unique (fastnum, attr_key, askrifandi_id)
);
create index notandi_eigindi_birt_idx on public.notandi_eigindi (fastnum) where stada = 'birt';

create table public.voktun_tak (
  tak_hash      bytea primary key check (octet_length(tak_hash) = 32),
  askrifandi_id uuid not null references public.voktun_askrifandi(id) on delete cascade,
  askrift_id    uuid references public.voktun_askrift(id) on delete cascade,
  eigindi_id    bigint references public.notandi_eigindi(id) on delete cascade,
  rennur_ut     timestamptz not null,
  notad_at      timestamptz,
  stofnad       timestamptz not null default now(),
  constraint voktun_tak_hlutur_chk check (num_nonnulls(askrift_id, eigindi_id) = 1)
);
create index voktun_tak_askrifandi_idx on public.voktun_tak (askrifandi_id);

-- Söluverð, síðasta ásett verð og mat frosið við fyrstu skráningu sölu, svo mat verður aldrei reiknað eftir sölu (D18).
create table public.voktun_seldist (
  fastnum        bigint not null,
  faerslunumer   bigint not null,
  thinglystdags  date not null,
  postnr         integer not null,
  matsvaedi_numer integer,
  matsvaedi_nafn text,
  heimilisfang   text not null,
  asett          bigint not null check (asett > 0),
  asett_dags     date not null,
  sala           bigint not null check (sala > 0),
  mat            bigint,
  mat_utgafa     text,
  fryst_at       timestamptz not null default now(),
  primary key (fastnum, faerslunumer)
);
create index voktun_seldist_postnr_idx on public.voktun_seldist (postnr, thinglystdags desc, fastnum);
create index voktun_seldist_matsvaedi_idx on public.voktun_seldist (matsvaedi_numer, thinglystdags desc, fastnum);

create table public.voktun_bann (
  netfang_hmac bytea primary key,
  astaeda      text not null check (astaeda in ('hard_bounce','kvortun')),
  stofnad      timestamptz not null default now()
);

create table public.voktun_hradi (
  id          bigint generated always as identity primary key,
  lykill_hmac bytea not null,
  tegund      text not null check (tegund in ('ip','netfang','allt')),
  stofnad     timestamptz not null default now()
);
create index voktun_hradi_idx on public.voktun_hradi (tegund, lykill_hmac, stofnad);

do $$
declare t text;
begin
  foreach t in array array['voktun_askrifandi','voktun_samthykki','voktun_askrift','voktun_atburdur','voktun_sendur','notandi_eigindi','voktun_tak','voktun_seldist','voktun_bann','voktun_hradi'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on public.%I from public, anon, authenticated', t);
    execute format('grant select, insert, update, delete on public.%I to service_role', t);
    if has_table_privilege('anon', 'public.'||t, 'select') or has_table_privilege('authenticated', 'public.'||t, 'select') then
      raise exception 'cc320: % opin fyrir anon/authenticated', t;
    end if;
  end loop;
end $$;
grant usage, select on sequence public.voktun_atburdur_id_seq, public.voktun_sendur_id_seq, public.notandi_eigindi_id_seq, public.voktun_hradi_id_seq to service_role;
commit;
