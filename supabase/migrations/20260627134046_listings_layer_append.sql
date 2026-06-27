-- Sales-trajectory model, Layer 1 (listing grain) + price-history + unit rollup view.
-- ADDITIVE: scraper.listings_canonical is NOT touched. These new tables run alongside it;
-- no consumer is moved in this migration. Promote will append here (no fold-deletion) while
-- the old fold path keeps writing listings_canonical unchanged.
--
-- Design (locked, BLOKK 4):
--   * scraper.listings           : one row per (source, source_listing_id), NO fold.
--   * scraper.listing_price_history: append-only, never overwrite.
--   * unit_key = (fastnum, size±2%) + íb.nr coalesced splitter (matshluti discarded).
--   * scraper.v_units            : deterministic rollup over listings, grouped by unit_key.
-- RLS: service-role-only (no anon/authenticated grants) — internal layer, holds raw lysing.

-- ───────────────────────── Layer 1: listing grain ─────────────────────────
CREATE TABLE scraper.listings (
  listing_id          bigserial PRIMARY KEY,
  source              text NOT NULL,                 -- 'mbl' | 'visir' | 'myigloo'
  source_listing_id   text NOT NULL,
  fastnum             bigint,                         -- resolved property (truncated fastano)
  unit_key            text,                           -- (fastnum, size-bucket, coalesced íb.nr)
  ibnr                text,                           -- extracted unit number (NULL if none)
  tenure              text,
  category            text,
  sub_type            text,
  tegund_raw          text,
  price_amount        bigint,
  price_currency      text NOT NULL DEFAULT 'ISK',
  is_price_on_request boolean,
  size_sqm            numeric,
  rooms               numeric,
  bedrooms            integer,
  bathrooms           integer,
  byggar              integer,
  addr_text           text,
  addr_postcode       text,
  addr_municipality   text,
  lat                 numeric,
  lng                 numeric,
  lysing              text,
  photos_json         jsonb,
  listed_at           timestamptz,                    -- sent_dags (listing submission date)
  first_seen_at       timestamptz,
  last_seen_at        timestamptz,                    -- last fetch that observed the listing
  withdrawn_at        timestamptz,
  status              text,                           -- active | withdrawn | sold (inferred)
  surviving_parse_id  bigint,
  br_dags             timestamptz,                    -- last edit date (source-reported)
  promoter_version    text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (source, source_listing_id)                  -- idempotent upsert key; NO fold-deletion
);

CREATE INDEX ix_listings_fastnum  ON scraper.listings (fastnum) WHERE fastnum IS NOT NULL;
CREATE INDEX ix_listings_unit_key ON scraper.listings (unit_key) WHERE unit_key IS NOT NULL;
CREATE INDEX ix_listings_status   ON scraper.listings (status, last_seen_at);
CREATE INDEX ix_listings_segment  ON scraper.listings (category, tenure, sub_type);

ALTER TABLE scraper.listings ENABLE ROW LEVEL SECURITY;
-- No anon/authenticated policy or grants: service-role-only (bypasses RLS) for the sync hop.

-- ───────────────────────── price history (append-only) ─────────────────────────
CREATE TABLE scraper.listing_price_history (
  id                bigserial PRIMARY KEY,
  source            text NOT NULL,
  source_listing_id text NOT NULL,
  observed_at       timestamptz NOT NULL,             -- when this price was observed
  price_amount      bigint NOT NULL,
  price_currency    text NOT NULL DEFAULT 'ISK',
  UNIQUE (source, source_listing_id, observed_at, price_amount)  -- append-idempotent
);

CREATE INDEX ix_price_hist_listing ON scraper.listing_price_history (source, source_listing_id, observed_at);

ALTER TABLE scraper.listing_price_history ENABLE ROW LEVEL SECURITY;

-- ───────────────────────── Layer 2: unit rollup (deterministic view) ─────────────────────────
-- Current state computed on read; materialize as MV later only if performance requires it.
CREATE VIEW scraper.v_units AS
WITH base AS (
  SELECT * FROM scraper.listings WHERE unit_key IS NOT NULL
), agg AS (
  SELECT unit_key,
         max(fastnum)                                  AS fastnum,
         count(*)                                      AS n_relistings,
         count(*) FILTER (WHERE status = 'active')     AS n_active,
         min(listed_at)                                AS first_listed_at,
         max(last_seen_at)                             AS last_seen_at
  FROM base
  GROUP BY unit_key
), cur AS (
  -- newest ACTIVE listing wins; fall back to most-recently-seen
  SELECT DISTINCT ON (unit_key)
         unit_key, source, source_listing_id, price_amount, status, size_sqm, addr_text
  FROM base
  ORDER BY unit_key,
           (status = 'active') DESC,
           listed_at DESC NULLS LAST,
           last_seen_at DESC NULLS LAST
)
SELECT a.unit_key,
       a.fastnum,
       a.n_relistings,
       a.n_active,
       c.price_amount                                  AS current_price,
       c.source                                        AS current_source,
       c.source_listing_id                             AS current_listing,
       c.status                                        AS current_status,
       c.size_sqm,
       c.addr_text,
       a.first_listed_at,
       a.last_seen_at,
       GREATEST((a.last_seen_at::date - a.first_listed_at::date), 0) AS days_on_market,
       (sh.fastnum IS NOT NULL)                        AS sold,
       sh.kaupverd_nominal                             AS sold_price,
       sh.thinglystdags                                AS sold_date
FROM agg a
JOIN cur c USING (unit_key)
-- sold = a thinglyst sale on the property after the unit was first listed. fastnum grain
-- (building-level under truncation), so this is approximate when a fastnum hosts >1 unit.
LEFT JOIN LATERAL (
  SELECT fastnum, kaupverd_nominal, thinglystdags
  FROM public.sales_history
  WHERE fastnum = a.fastnum
    AND onothaefur = 0
    AND thinglystdags >= a.first_listed_at::date
  ORDER BY thinglystdags DESC
  LIMIT 1
) sh ON true;
