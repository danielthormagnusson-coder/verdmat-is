-- cc224b (10.10.2026): /nybyggingar v3 — forsíðumynd verkefnis, auglýsingahlekkur per einingu, skrá smámynda.
-- Beitt með psycopg2 (lock_timeout 10s / statement_timeout 120s), ekki MCP apply_migration.
-- Allir nýir dálkar eru nullable: útgáfa cc224-v2 (lifandi) stendur óbreytt þar til framendinn les cc224-v3.

-- forsíðumynd: nýjasta söluauglýsing verkefnisins sem á sótta mynd nr. 0 (scraper.auglysingamyndir)
alter table semantic.nybygging_verkefni
  add column if not exists mynd_sha256 text,            -- sha256 frumrits (lykill í nybygging_myndir)
  add column if not exists mynd_lykill text,            -- R2-lykill minnkaðrar útgáfu (720 px WebP)
  add column if not exists mynd_lykill_frumrit text,    -- R2-lykill frumrits (auglysingamyndir.r2_lykill)
  add column if not exists mynd_breidd integer,         -- stærð minnkaðrar útgáfu (width/height á <img>, enginn CLS)
  add column if not exists mynd_haed integer,
  add column if not exists mynd_stofa text,             -- fasteignasala auglýsingarinnar („Mynd úr auglýsingu {stofa}")
  add column if not exists mynd_dags date,              -- birtingardagur auglýsingarinnar
  add column if not exists mynd_listing_id bigint;      -- scraper.listings.listing_id

-- auglýsingahlekkur: nýjasta VIRKA mbl-söluauglýsing einingarinnar (scraper.v_eign_virk_auglysing)
alter table semantic.nybygging_einingar
  add column if not exists augl_id text,                -- mbl eign_id = listings.source_listing_id
  add column if not exists augl_endursala boolean;      -- auglýst eftir fyrstu sölu (eining seld)

-- skrá minnkaðra útgáfa: búnar til EINU SINNI per frumrit, stærð bókuð
create table if not exists semantic.nybygging_myndir (
  sha256 text primary key,
  lykill_frumrit text not null,
  lykill text not null,
  breidd integer not null,
  haed integer not null,
  baeti integer not null,
  frumrit_breidd integer,
  frumrit_haed integer,
  frumrit_baeti integer,
  buid_til timestamptz not null default now(),
  hladid_kl timestamptz                                  -- hvenær hlaðið á opinberan myndahýsil (NULL = ekki enn)
);
alter table semantic.nybygging_myndir enable row level security;
revoke all on semantic.nybygging_myndir from anon, authenticated;
comment on table semantic.nybygging_myndir is
  'cc224b: minnkaðar forsíðumyndir nýbyggingarverkefna (720 px WebP), ein röð per frumrit. Ekki lesin af framenda.';
