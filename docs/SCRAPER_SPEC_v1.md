# SCRAPER_SPEC_v1.md

**Status**: final v1, awaiting Danni sign-off
**Last updated**: 2026-05-06
**Tracks**: A (active listings stream) + B (HMS fastanúmera completion)
**Owners**: Danni (decisions) + Claude (drafting)

---

## Section 1 — Source selection

### Pre-decision research deliverable (blocks Track A source pick)

Before Track A source is locked, run a **mirror-investigation audit script**
to determine whether mbl.is/fasteignir and fasteignir.visir.is mirror each
other or diverge.

**Method**:
- Scrape both sites' active-listings indexes for **5-7 consecutive days**
  (sample window must span a full weekly cycle — Monday/Friday upload peaks
  differ from weekend volume; 2-3 days is liable to bias overlap
  measurement), persist raw rows
- Match key tuple: `(heimilisfang_normalized, postnr, agent_listing_id)` if
  listing_id exposed; fall back to `(heimilisfang_normalized, postnr,
  byggar, einflm)` if not — property attributes are stable across listing
  lifecycle, whereas `list_price` was rejected as fallback because
  mid-listing price drops are common and would inflate false-divergence
- Outputs:
  - overlap rate (% of mbl listings present in visir, vice versa)
  - per-site uniques: counts and per-region/segment distribution
  - per-day flux (do new listings appear simultaneously, or with lag?)
  - recommendation memo

**Decision rule**:
- ≥95% overlap → single-source sufficient; pick stabler HTML or richer field set
- <95% overlap → dual-scrape with cross-site dedup on the tuple key

**Implementation**: Python script under `audit/` in scraper repo, ~150-300
LOC, runs once before source-lock decision. Output committed to spec as a
v1.1 amendment.

This is **audit-script-first principle on source-pick** — do not lock a
source decision without empirical data. (Pattern lærdómur frá Bug 24:
trust canonical/empirical over assumption.)

### Track A — Active listings stream

#### Primary candidates

**mbl.is/fasteignir/**
- Type: direct upload from real-estate agents, Morgunblaðið real-estate vertical
- Pros: well-known agent destination, rich photo galleries, "for sale" focus
- Cons: HTML structure change risk (mbl.is has redesigned multiple times);
  robots.txt + ToS need verification before scrape

**fasteignir.visir.is**
- Type: direct upload from real-estate agents, partnered with Sýn/Stöð 2 media
- Pros: dedicated real-estate vertical (fewer cross-traffic signals affecting
  layout), historically more stable URL structure
- Cons: same brittleness risk as any direct-source HTML scrape

#### Fallback

**e-value.is**
- Type: aggregator that scrapes mbl.is + fasteignir.visir.is + others;
  presents normalized listings UI
- Pros: single endpoint, normalized fields, lower scrape volume against
  primary sources
- Cons: introduces second-order brittleness — e-value.is can change schema
  or break source compatibility without notice; aggregator outage =
  both inputs vanish simultaneously
- Use only if: both primary sites prove hostile to direct scraping
  (aggressive bot detection, ToS denial, or rate-prohibitive)

#### Pros/cons matrix

| Criterion | mbl.is/fasteignir | fasteignir.visir.is | e-value.is (fallback) |
|---|---|---|---|
| Source-of-truth proximity | High (direct agent post) | High (direct agent post) | Low (aggregator) |
| HTML stability | Medium-Low | Medium-High | Low (third-party schema) |
| Field richness | High | High | Medium (normalized subset) |
| Brittleness layers vs source | 1 | 1 | 2 |
| Single-point-of-failure risk | Site outage isolated | Site outage isolated | Aggregator outage = both dark |

#### Operational pre-checks (per primary source)

Audit-script must record before lock-in:
- robots.txt content and any disallowed paths/UAs
- Terms of Service: explicit anti-scraping clauses, IP-block-on-detection
- Rate-limit reality: serial requests at 1 req/sec — does the site stay
  responsive? Does it 429 or 503? What rate is sustainable?
- Authentication: do listings require login? (If yes, scope expands materially)
- Raw-data freshness: how long after agent posts does listing appear in index?

🔶 **Decision-point #1A** (deferred — gated by mirror-investigation): Given
mirror-investigation results + operational pre-checks, single-source or
dual-scrape? Pick which primary site (or both). Locked as deferred per
Danni 2026-05-06; resolved before implementation kickoff.

### Track B — HMS fastanúmera completion

(Simplified per Danni 2026-05-06 — Track B is incomplete-scrape-of-HMS, not
fundamental data-sourcing problem.)

#### Primary

**hms.is/fasteignaskra (HMS Fasteignaskrá)**
- Type: official source-of-truth, Icelandic property registry
  containing ALL ~150K fastanúmer
- Existing access: `properties_v2.pkl` already contains 124,835 rows
  scraped historically — gap of ~25K is incomplete-scrape, not absent data
- Pros: canonical source, full metadata available (canonical_code, einflm,
  byggar, fasteignamat, address, segment classification), single primary
  key (fastnum), no fuzzy match needed
- Cons: needs research on access mechanism — public records query? HMS
  public API (verify exists)? bulk export endpoint? Access cadence
  governance

#### Fallback

**e-value.is**
- Use only if: HMS direct access proves blocked or rate-prohibitive
- Tradeoff: e-value.is may not surface complete fastnum metadata; would need
  post-fetch enrichment for fields like canonical_code or fasteignamat

#### Operational pre-checks

**Preferred path: formal API access, not silent scrape.** HMS is a
government body (Húsnæðis- og mannvirkjastofnun), and a working dialogue
with them is a project asset, not a friction point to route around.
Áfangi 4.9 (matsvæði-level polygon shapefile, in `PLANNING_BACKLOG.md`)
already has a formal-HMS-request precedent — **piggyback on that dialogue**
with a registered fastanúmera-data request as part of the same engagement.
Reputational and legal hygiene rationale, plus the relationship is more
useful long-term than tactical scraping.

- Open formal data-access request with HMS, ideally bundled with the
  Áfangi 4.9 matsvæði request
- Document any registered API contract or bulk-export agreement that comes
  out of the dialogue
- If formal access is denied or impractically slow: probe public records
  query at hms.is, identify pagination for systematic walk — but only as
  fallback, not first move
- Rate-limit governance (whether formal API or scrape fallback): HMS is a
  public-records-disclosure body; aggressive parallelism is reputationally
  risky for the project. Throttle conservatively (1 req per 2-5 sec),
  spread over days
- Match strategy when scrape encounters fastnum already in `properties`:
  treat as opportunity to refresh stale metadata, not insert duplicate

🔶 **Decision-point #1B** (deferred — gated by HMS access research):
Confirm HMS direct access path post-research. Locked as deferred per
Danni 2026-05-06; resolved before implementation kickoff.

#### Out-of-scope clarifications (recorded so future-Claude does not regress)

- Track B is **not** "supplement-only properties with no HMS data" — every
  Track B row has full HMS metadata by definition (fastnum primary key)
- Track B is **not** "fuzzy address matching to existing properties" —
  every fastnum is uniquely keyed
- Track B is **not** "create separate `properties_supplement` table" —
  Track B inserts canonical `properties` rows
- Áfangi 4.10 (commercial empty-state UX) and `is_residential = FALSE`
  cases are independent of Track B

The supplementary-table misframing appeared in earlier drafts because the
gap was assumed to be a data-sourcing problem. Clarification 2026-05-06
corrected the framing.

---

## Section 2 — Scraper arkitektúr

### Resolved infrastructure context (DECISIONS.md cross-check)

DECISIONS.md line 912 (Áfangi 1 era) describes scrapers running on Danni's
Windows machine via Task Scheduler writing direct to Supabase. DECISIONS.md
line 1729 (later infrastructure decision) commits to **Hetzner +
PostgreSQL 16 + PostGIS + R2 + Docker Compose + Dagster + MLflow +
Grafana/Prometheus/Sentry + FastAPI** as the target stack for "scheduled
scrapes og retraining".

**Resolution for Áfangi 0**: target the Hetzner + Dagster stack from day
one. Windows Task Scheduler approach was the bridge for early Áfangi
scripts (`refresh_kaupskra.py`, `refresh_cpi.py`); new scrapers should not
perpetuate that bridge given the explicit later decision. This makes
Áfangi 0 the first deployment to the production-target infra, with
subsequent Sprint 3+ pipelines following the same shape.

### Track A — Active listings stream

#### Crawl strategy: incremental delta crawl

- Each cycle fetches active-listings index page(s) for each source
- Compute content hash per listing entry (or use ETags/Last-Modified if
  site provides)
- Listings unchanged since last cycle: skip detail-page fetch
- New or changed listings: fetch detail page, parse, write
- Withdrawn listings (present last cycle, absent this cycle): mark
  `withdrawn_at = now()`, retain row for history (retention duration TBD
  in §3 storage taxonomy — indefinite vs N-month archive cutoff)

Rationale: full-sweep at 24h cadence is wasteful when ~95% of listings are
unchanged day-to-day. Incremental design is also gentler on source sites
(matters for ToS / agent relations).

#### Change detection
- Index-level: hash listing-card content (price, status, days_on_market)
- Detail-level: hash structured fields after parse (catches price-change
  events, lysing edits, photo updates)

#### Parallelism
- Within source: serial (rate-limit compliance; concurrent requests to
  same domain raise detection-flag risk)
- Across sources: parallel (mbl.is and fasteignir.visir.is independent infra)

#### Retry / circuit-breaker
- Exponential backoff, max 5 attempts
- 4xx not retried (except 429 → wait full Retry-After)
- Circuit-breaker: 5+ consecutive 5xx from a source → halt that source for
  30 min, alert Sentry; do not cascade-fail the other source

#### Cadence
- **Nightly** (00:00-04:00 Reykjavík time, low-traffic window)
- Track A independent of monthly model-refresh cycle; output lands in
  tables consumable by other pipelines on their own schedules

### Track B — HMS fastanúmera completion

#### Crawl strategy: phased full-sweep, incremental thereafter
- **Phase 1 — gap identification**: depends on Decision-point #1B outcome
  - If HMS bulk export exists: take latest export, diff against
    `properties.fastnum`, the diff IS the missing population
  - If no bulk export: systematic walk of fastnum number-space (e.g.
    range 100000-9999999) with anti-block throttle
- **Phase 2 — backfill**: fetch each missing fastnum's detail record,
  normalize, insert into `properties`
- **Phase 3 — steady state**: monthly re-check to catch new fastnum
  issuances (typically ~50-200/month for new construction)

#### Change detection
- Track B is mostly insert-only for missing fastnums
- Updates to existing rows (canonical metadata refresh) is a separate
  concern, not Áfangi 0 v1 scope

#### Parallelism
- **Strictly serial**. HMS is a public-records body; aggressive parallelism
  is reputational risk. Throttle 1 req per 2-5 sec, even if technically
  permitted

#### Retry / circuit-breaker
- Exponential backoff, max 3 attempts
- Halt + alert if HMS returns sustained 5xx (>10 minutes)
- Per-day fetch budget: e.g. 5K-10K fetches/night max, staged over 3-5
  nights for full backfill, then quiescent

#### Cadence
- Initial backfill: one-time, over 3-5 consecutive nights
- Steady-state: monthly, aligned with `refresh_*.py` cycle (small delta)

### Shared concerns

#### Deployment surface

**Hetzner dedicated host (per DECISIONS line 1729)**:
- Dockerized Python services (one container per scraper track + one
  Dagster orchestration container)
- Write path: see Decision-point #2B below
- No Windows Task Scheduler. Cron-equivalent is Dagster schedules.

🔶 **Decision-point #2B** (deferred to §3 or §6 — whichever section makes
the implications more concrete): scraper-to-Supabase write path.

- **(i) Direct write** to Supabase Postgres via `psycopg` (v3 async
  preferred for throughput). Simpler, fewer moving parts, lower latency
  from scrape to availability.
- **(ii) Hetzner-local Postgres staging, then sync** to Supabase. More
  robust — decouples scraper liveness from Supabase availability, allows
  replay of failed syncs, gives a local rollback target if a corrupt
  batch needs redo.

Trade-off: (i) ships faster and is simpler to reason about; (ii) is more
robust under network/Supabase incidents and gives a clean replay surface
for partial-failure recovery. Not silently resolved here — flagged for
explicit decision when §3 storage shapes or §6 orchestrator integration
makes the cost asymmetry concrete.

**Repository**: scraper code lives in **separate repo** at
`github.com/danielthormagnusson-coder/verdmat-is-scraper`, mirroring the
verdmat-is-precompute pattern. Reasoning: scraper infra has different
deploy cadence than `app/`, different secrets surface (HMS credentials if
any, source-site cookies), and different language stack focus (more crawl
tooling, less Next.js). `SCRAPER_SPEC_v1.md` itself remains canonical in
`verdmat-is/app/docs/`; scraper repo gets a read-only mirror committed at
implementation kickoff.

#### Health monitoring

**Lessons from 2025-07 silent death**: gamli scraperinn dó án warning;
Danni vissi ekki í marga mánuði þar til downstream metrics (~600/mán
listings inflow) blöstu við. Volume-based detection is a hard requirement.

**Required signals**:
- **Heartbeat**: per-cycle Prometheus counter
  `scraper_cycle_completed_total{track="A|B", source="..."}` increments
  on every successful cycle. Grafana alert if no increment for 2× expected
  cadence (Track A nightly → alert at 48h silence)
- **Volume signal**: per-cycle gauge
  `scraper_listings_fetched_total{track,source}`. Sentry-flag if drop
  >50% week-over-week (catches selector decay producing partial fetches)
- **Health page**: simple `/health` endpoint exposing `last_run_at`,
  `last_success_at`, `listings_processed_last_run`, `error_rate_24h`
- **Sentry**: any unhandled exception ships to Sentry; structured errors
  ("selector returned 0 results — HTML changed?") raise dedicated alerts

**SLA**:
- Track A nightly: missed run alert at 48h. "Dead" = no successful run for
  7 days
- Track B monthly: missed run alert at 7 days. "Dead" = no successful run
  for 30 days

**Definition of "dead"**: scraper is dead when **either** (a) consecutive
failures exceed SLA threshold, **or** (b) volume signal drops below 25%
of trailing-30-day baseline for 7 days. Volume-based detection catches
silent partial failures (selectors stale, fewer listings without erroring)
that heartbeat-only monitoring misses. The 2025-07 incident would have
been caught by (b) on day 8.

#### Storage strategy preliminary direction (full spec in §3)

Track A is straightforward: direct-to-Supabase write with a JSONB
`raw_payload` audit column on the landing tables. No legacy pickle path,
no ML-pipeline dependency, hreinn cutover.

Track B is non-trivial because `properties_v2.pkl` is read by the ML
pipeline (training_data builders, comps_index regeneration, model
retrain cycles). Eliminating the pickle path silently breaks iter5
retrain. **§3 specs three explicit paths (B1, B2, B3) at decision-point
#2A** — clean refactor, twin-write transition, or accept frozen iter3v2
pickle until iter5 retrain absorbs the Supabase-read refactor as part of
that scope. This decision is gated by ML retrain timing and is not
silently resolved here.

---

## Section 3 — Storage taxonomy

### Existing schema baseline (cross-check)

Current Supabase canonical tables (per Sprint 1+ live state, ~current as
of 2026-05-06): `properties` (~125K fastnum-keyed rows, both residential
and non-residential), `predictions` / `predictions_iter4` /
`predictions_iter3v2`, `comps_index` (1.1M rows, ~110K fastnums × 10
comps each), `sales_history` (~173K), `repeat_sale_index`,
`ats_lookup_by_heat` and other ats variants, `feature_attributions` and
its iter4 variant, `last_listing_text`, `model_tracking_history`.

Data flow today: legacy scraper → SQLite DBs in `D:\Gagnapakkar\` →
`parse_all_dbs.py` → v2 pickles (`listings_v2.pkl`, `sales_v2.pkl`,
`properties_v2.pkl`, `listings_text_v2.pkl`) → `build_precompute.py` →
CSV outputs in `precompute/exports/` → `load_dashboard_v1.py` → Supabase
tables. There is no current persistent active-listings table —
`last_listing_text` carries the most recent listing description per
fastnum but not the full listing index. **Áfangi 0 introduces the first
persistent active-listings storage**, which is one of the two main
schema deltas in this spec (the other is the `properties` audit columns
for Track B).

### 3.1 Track A landing tables

Two new tables: `active_listings` (current state) + `active_listings_history`
(append-only audit log).

**`active_listings`** (current state, hot read path for market-scan UI)

| Column | Type | Notes |
|---|---|---|
| `source` | text NOT NULL | `'mbl'` \| `'visir'` \| `'evalue'` (fallback) |
| `listing_id` | text NOT NULL | per-source unique id |
| `fastnum` | bigint NULL | matched HMS fastnum if known, NULL otherwise |
| `heimilisfang` | text NOT NULL | |
| `postnr` | integer NOT NULL | |
| `canonical_code` | text NULL | pulled from `properties` if `fastnum` matched |
| `einflm` | numeric NULL | |
| `byggar` | integer NULL | |
| `asking_price` | numeric NOT NULL | |
| `list_date` | date NOT NULL | first observed in scrape |
| `withdrawn_at` | timestamptz NULL | set when listing disappears from index |
| `agent_name` | text NULL | |
| `agent_phone` | text NULL | PII — restricted (see §3.3) |
| `lysing` | text NULL | description text |
| `photos` | text[] NULL | ordered list of photo URLs |
| `content_hash` | text NOT NULL | per-listing hash for change detection |
| `first_seen_at` | timestamptz NOT NULL DEFAULT now() | |
| `last_seen_at` | timestamptz NOT NULL DEFAULT now() | |
| `raw_payload` | jsonb NOT NULL | complete scrape blob, audit trail — restricted (see §3.3) |
| **PK** | `(source, listing_id)` | composite |

Indexes:
- `(fastnum) WHERE fastnum IS NOT NULL` — partial, for joins to `properties`
- `(postnr, withdrawn_at)` — for region filters in market-scan
- `(withdrawn_at) WHERE withdrawn_at IS NOT NULL` — partial, for archive queries
- `(list_date DESC)` — for newest-listings ordering
- GIN on `lysing` (full-text Icelandic) — only if market-scan UI ships text-filter feature; defer if not v1

`days_on_market` is computed on read (`COALESCE(withdrawn_at, now()) - list_date`), not stored — avoids stale-update problem.

**`active_listings_history`** (append-only audit log, partition-by-quarter)

| Column | Type | Notes |
|---|---|---|
| `source` | text NOT NULL | |
| `listing_id` | text NOT NULL | |
| `observed_at` | timestamptz NOT NULL DEFAULT now() | |
| `asking_price` | numeric NOT NULL | |
| `status` | text NOT NULL | `'active'` \| `'withdrawn'` \| `'price_changed'` \| `'attributes_changed'` |
| `content_hash` | text NOT NULL | matches the active row that produced this event |
| **PK** | `(source, listing_id, observed_at)` | composite |

Partitioned: `PARTITION BY RANGE (observed_at)`, one partition per quarter
(e.g. `active_listings_history_2026q3`). Dagster job creates next-quarter
partition 30 days ahead of need.

**Why split**: `active_listings` is small + hot (current-state, ~5-10K
rows). `active_listings_history` grows ~5-10K rows/cycle → 1-3M rows/year.
UI reads current; analytics (TOM tracking, price-change cadence, market-scan
historical overlay) reads history. Splitting prevents row bloat on the
hot table and isolates query patterns.

**Audit sidecar table: `rejected_commercial_listings`** (introduced in
§5.4 commercial-filtering pipeline; DDL lives here for single-source-of-truth
on storage shape)

```sql
CREATE TABLE rejected_commercial_listings (
  source           text NOT NULL,
  listing_id       text NOT NULL,
  rejected_at      timestamptz NOT NULL DEFAULT now(),
  rejection_reason text NOT NULL,  -- 'level_1' | 'level_2' | 'level_3'
  raw_payload      jsonb NOT NULL,
  PRIMARY KEY (source, listing_id, rejected_at)
);

-- Internal-only: no public read use case
ALTER TABLE rejected_commercial_listings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON rejected_commercial_listings FROM anon, authenticated;
GRANT ALL ON rejected_commercial_listings TO service_role;
```

**Retention**: indefinite. Audit value is accumulating — trend on
commercial-rejection rate over time is the signal that backs §5.4's
Sentry-flag rule (rejection rate >5% week-over-week → heuristic drift
or source-side category re-shuffle). Truncating audit data invalidates
the trend.

**Partitioning**: deferred to v1.1 — quarterly partitions on
`rejected_at` if row volume justifies (matching `active_listings_history`
pattern). v1 ships as single table; expected volume is bounded by
`(source × index_size × 0-2% rejection_rate)` ≈ low thousands of rows
per year, comfortably single-table for the foreseeable horizon.

### 3.2 Track B landing approach

Track B does **not** introduce new tables. It inserts/updates rows in
canonical `properties`. (Per simplification 2026-05-06: every Track B row
is canonical HMS metadata, fastnum primary key.)

Schema delta to existing `properties`:

```sql
ALTER TABLE properties ADD COLUMN hms_fetched_at  timestamptz NULL;
ALTER TABLE properties ADD COLUMN hms_payload     jsonb       NULL;
```

`hms_fetched_at` records the most recent successful HMS sync per row.
`hms_payload` retains the raw HMS API/scrape response for audit and for
re-derivation if downstream needs change. No other schema changes — all
existing columns stay untouched.

### 3.3 RLS policies (security baseline)

**Pattern for all new tables and views: RLS enabled by default, public
SELECT via view, service-role bypass for scraper writes.**

This is direct lærdómur from prior Supabase security alerts where
RLS-disabled-by-default was flagged as a recurring failure mode in this
project. Áfangi 0 implementation must enable RLS + view-public pattern
from day one — no new table ships without an explicit policy decision
recorded in this section.

**Policy template per table**:

```sql
ALTER TABLE active_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_listings_history ENABLE ROW LEVEL SECURITY;

-- No anon/authenticated SELECT directly on tables — go through view
-- (raw_payload + agent_phone are not safe for public)
REVOKE ALL ON active_listings, active_listings_history FROM anon, authenticated;

-- Service role (scraper) needs unrestricted access
GRANT ALL ON active_listings, active_listings_history TO service_role;
```

**Public-readable view for `active_listings`**:

```sql
CREATE VIEW active_listings_public AS
SELECT
  source, fastnum,
  -- listing_id EXCLUDED (per-source identifier, see rationale below)
  heimilisfang, postnr, canonical_code, einflm, byggar,
  asking_price, list_date, withdrawn_at,
  agent_name,                                  -- public OK
  -- agent_phone EXCLUDED (PII / scraping etiquette)
  lysing, photos,
  COALESCE(withdrawn_at, now())::date - list_date AS days_on_market,
  first_seen_at, last_seen_at
  -- raw_payload EXCLUDED (audit-only, may contain agent metadata,
  -- scraping signatures, source-side internal fields)
FROM active_listings;

GRANT SELECT ON active_listings_public TO anon, authenticated;
```

**Why `listing_id` is REVOKED from the public view**: `listing_id` is the
per-source listing identifier exposed by mbl.is or fasteignir.visir.is.
It serves as our internal dedup key and cross-site match anchor, but
exposing it via public view enables third-party scrapers to back-link
our data to source platforms — a brittleness we should not introduce
(third-party tooling tracking our listings could fingerprint our scrape
cadence and trigger source-side anti-bot measures aimed at the apparent
back-linker, which is us). No user-facing UI consumes this column. If
public addressability of individual listings becomes necessary in v1.1
(e.g. share-link to a specific listing in market-scan view), introduce
a surrogate `public_id uuid DEFAULT gen_random_uuid()` column that is
not resolvable to source URLs.

UI consumers (`/markadur/auglysingar` market-scan, search RPC) read from
`active_listings_public`, not the underlying table.

`active_listings_history` exposed similarly via `active_listings_history_public`
with content_hash excluded (audit-only field — useful for scraper logic,
not for UI).

For Track B (`properties` audit columns):
- `hms_payload` JSONB column should be REVOKED from anon/authenticated
- `hms_fetched_at` is OK to expose (timestamp only, useful for debug "when
  was this last refreshed")
- `properties` already has RLS policies in place from Sprint 1 — Áfangi 0
  must extend the existing policy to handle the new columns (verify column-level
  GRANT before write of first Track B row)

**Why view-pattern over column-level GRANT**: views allow adding/removing
public fields without revoking grants on the underlying table, decouple
public schema evolution from internal schema, and make the
"publishable-vs-internal" distinction explicit in code. Column-level
GRANT works mechanically but obscures intent at review time.

### 3.4 Retention policy

Per cross-link from §2:

| Surface | Retention | Notes |
|---|---|---|
| `active_listings` (current state) | Indefinite | Withdrawn rows stay queryable via `withdrawn_at IS NOT NULL` |
| `active_listings_history` | Indefinite | Quarterly partitioning for query performance, no archival |
| `properties.hms_payload` | Indefinite | Audit trail for HMS data evolution |

**Rationale**: Supabase row count is not the binding constraint at current
free-tier pricing (~424/500 MB now; post-Áfangi 0 expected growth is
~50-150 MB depending on photo array vs URL-only storage choice — well
within tier headroom, and any tier upgrade is backed by Áfangi 4.13
market-scan revenue case). Quarterly partitions on history solve query
performance without requiring archival. Quarterly is coarser than monthly
(less management overhead) and finer than yearly (still useful for
hot/cold tiering if needed in 2027+).

If row count becomes a binding constraint later: easiest archive surface
is `active_listings_history` partitions older than 24 months → cold-tier
copy + drop partition. Schema design above supports this without
migration.

### 3.5 🔶 Decision-point #2A — Track B pickle migration

`properties_v2.pkl` is read by the ML pipeline (`build_precompute.py`,
training data builders, `build_comps`, model retrain cycles). Track B
inserts ~25K new rows into Supabase `properties` — but the pickle is
the read source for ML, not Supabase. Eliminating the pickle silently
breaks iter5 retrain. Three explicit paths:

#### B1 — Direct-to-Supabase only, ML pipelines refactored as v1.1 follow-up

**Behavior**:
- Track B writes directly to `properties` Supabase table with full HMS metadata
- `parse_all_dbs.py` retains its job parsing legacy DBs for `listings_v2`,
  `sales_v2`, `listings_text_v2` but no longer writes `properties_v2.pkl`
- `build_precompute.py` and downstream consumers refactored to read
  `properties` from Supabase instead of pickle (~1-2 day refactor logged
  as Bug 25 / immediate v1.1 follow-up after Áfangi 0 ships)

**Pros**:
- Cleanest end-state — single source of truth for properties data
- Retires pickle file entirely, simplifies the pipeline
- Aligns with Hetzner+Postgres+Dagster decision (no Windows-machine pickle ETL)

**Cons**:
- 1-2 day refactor outside Áfangi 0 scope
- Blocks iter5 retrain until refactor lands
- Risk of subtle data-shape drift between pickle reads and Postgres reads
  (column names, dtypes, NaN handling — every consumer needs verification)

#### B2 — Twin-write — Supabase primary + parallel pickle-emit for backward compat

**Behavior**:
- Track B writes to `properties` Supabase table AND emits an updated
  `properties_v2.pkl` covering the new rows (or full table) on each cycle
- ML pipeline reads pickle as before — zero changes downstream

**Pros**:
- No ML refactor required, preserves current pipeline as-is
- Does not block iter5 retrain on refactor timing
- Decouples Áfangi 0 ship date from ML team scope

**Cons**:
- Dual maintenance overhead — every schema change to `properties` requires
  updating the pickle emitter
- Risk of drift between Supabase and pickle if emitter fails or runs stale
  (defensive: invariant check at end of each cycle: "row count and PK set
  match Supabase ↔ pickle")
- Perpetuates the pickle layer past its natural sunset point

#### B3 — Direct-to-Supabase only, accept frozen iter3v2 pickle until iter5 retrain

**Behavior**:
- Track B writes directly to `properties` Supabase table
- `properties_v2.pkl` is frozen at its current state (124,835 rows from
  iter3v2-era scrape) — no further updates from Track B
- Production iter4 model continues to score using its frozen training
  distribution; Track B's new ~25K rows are searchable in Supabase but
  not yet scored by iter4
- Next retrain (iter5) absorbs the Supabase-read refactor as part of its scope

**Pros**:
- Ships fastest — no separate refactor commit needed
- Aligns naturally with retrain cadence (next retrain refactors anyway)
- Single source of truth at end-state, like B1

**Cons**:
- ~25K newly-discovered fastnums are search-coverage gain but not
  prediction gain until iter5 ships
- If iter5 retrain slips, supplement rows show in search but
  `/eign/[fastnum]` falls back to "verðmat ekki tiltækt" — UI work needed
  for that state (Áfangi 4.10 partially covers it for `is_residential = FALSE`
  but Track B rows are residential, so a different empty-state copy is
  needed)
- No twin-source defensive verification possible

#### Decision-context for Danni

- iter5 retrain is on horizon per PLANNING_BACKLOG Áfangi 4.8 (eldri-stock
  calibration analysis) — that scope already implies an iter5
- **B3 leaning** if iter5 retrain is committed within ~2-3 months of
  Áfangi 0 ship (the `/eign` empty-state copy gap is bounded and acceptable)
- **B2 leaning** if Áfangi 0 must not block on iter5 timing — twin-write
  decouples cleanly at modest operational cost
- **B1 leaning** if the refactor work is appetizing in its own right
  (cleanup value beyond just unblocking iter5; takes ML pipeline off
  Windows-machine middleware sooner)

**Note on iter5 timing assumption**: "B3 leaning if iter5 within 2-3
months" depends on iter5 actually being scheduled. iter5 itself is
conditional on Áfangi 4.8 (competitor-comparison analysis, see
`PLANNING_BACKLOG.md`) outcome — the comparison may conclude that iter5
retrain is unnecessary (frame current undershoot as credibility strength)
or necessary (re-introduce FASTEIGNAMAT as feature). Until Áfangi 4.8
has run, B3 leaning is built on an unsettled assumption.

**Default fallback**: if Áfangi 4.8 has not been resolved by Áfangi 0
implementation kickoff, leaning shifts to **B2 (twin-write)** —
preserves pickle-reader path until iter5 timing is confirmed, accepts
operational overhead as insurance against the worst case (iter5 confirmed
necessary but slips beyond the empty-state-copy gap window).

🔶 **Decision-point #2A: locked as deferred for Danni close.** Spec does
not silently resolve.

### 3.6 Decision-point #2B reprise — write path (cross-reference §2)

Track A volume profile (~5-10K rows updated nightly per primary site)
makes local-staging-then-sync (option ii from §2) more compelling for
Track A — sync replay matters when a multi-thousand-row write fails
mid-batch. Track B is low-volume (~25K total over backfill, then
~50-200/month) — direct write (option i) is fine.

**Recommendation pending §6 orchestrator integration**: **(ii) for Track
A, (i) for Track B**. Tracks have different volume/criticality profiles;
mixing approaches is OK if Dagster orchestrator surfaces both clearly.
Final lock at §6.

---

## Section 4 — Dedup and match logic

### 4.1 Track B dedup (trivial)

Per simplification 2026-05-06: fastnum is canonical HMS primary key. No
fuzzy match. No supplement-vs-canonical concept. No manual review queue.

Behavior on encountering a fastnum during HMS walk:

```sql
INSERT INTO properties (
  fastnum, heimilisfang, postnr, canonical_code, einflm, byggar,
  fasteignamat, /* ... full HMS field set ... */
  hms_fetched_at, hms_payload
)
VALUES (...)
ON CONFLICT (fastnum) DO UPDATE SET
  heimilisfang   = EXCLUDED.heimilisfang,        -- HMS may have corrected typos
  postnr         = EXCLUDED.postnr,
  canonical_code = EXCLUDED.canonical_code,
  einflm         = EXCLUDED.einflm,              -- can change with conversions
  byggar         = EXCLUDED.byggar,              -- generally stable
  fasteignamat   = EXCLUDED.fasteignamat,        -- changes annually
  hms_fetched_at = now(),
  hms_payload    = EXCLUDED.hms_payload
WHERE
  -- Only update if HMS-side data has actually changed (cheap diff via
  -- payload hash). Avoids needless row churn / WAL bloat on unchanged rows.
  properties.hms_payload IS DISTINCT FROM EXCLUDED.hms_payload;
```

Single primary key, single source of truth, two-line conflict resolution.
Done.

### 4.2 Track A dedup — two layers

#### 4.2.1 Within-site update dedup (per source)

For a given `(source, listing_id)`, dedup answers "is this the same
listing we saw last cycle, and did anything change?".

Mechanism: `content_hash` of detail-page structured fields (price, status,
attributes, lysing, photos serialized).

On scrape per row:

| State | Action |
|---|---|
| `(source, listing_id)` not in `active_listings` | INSERT new row + INSERT history row with status='active' |
| `(source, listing_id)` exists, `content_hash` matches | UPDATE `last_seen_at` only — no history row |
| `(source, listing_id)` exists, `content_hash` differs, `asking_price` changed | UPDATE row + INSERT history row with status='price_changed' |
| `(source, listing_id)` exists, `content_hash` differs, attributes changed only | UPDATE row + INSERT history row with status='attributes_changed' |
| `(source, listing_id)` was in `active_listings` last cycle, absent this cycle | UPDATE row SET `withdrawn_at = now()` + INSERT history row with status='withdrawn' |

Implementation note: a Postgres trigger on UPDATE to `active_listings`
that auto-inserts the appropriate history row is the cleanest way to
keep caller code simple and ensure no path forgets to log the audit
row. Alternative is explicit dual-write from the scraper Python code —
more visible but error-prone.

**Bounding clause — single-writer regime assumption**: the trigger
pattern assumes only the scraper writes to `active_listings`. If a
second writer (admin tool, migration script, manual SQL) ever needs to
write to this table, revisit this decision: the trigger fires on every
write regardless of source, which may produce unwanted audit rows or
require trigger-bypass mechanisms (`SET LOCAL session_replication_role = 'replica'`
or similar). Cross-link to Decision-point #2B (write path): if (ii)
Hetzner-local-staging-then-sync is chosen, the trigger fires on the
**sync side** (Supabase write), not the scraper side (Hetzner-local
write). Audit history therefore lives on Supabase exclusively, with the
Hetzner-local table being a transient staging layer that does not
itself emit history rows.

#### 4.2.2 Cross-site dedup (gated on mirror-investigation outcome)

If Decision-point #1A ships **single-source**: cross-site dedup is moot.
Skip this layer entirely.

If #1A ships **dual-scrape** (mirror-investigation overlap < 95%):

Each source's listings land in `active_listings` with their own
`(source, listing_id)` PK. UI needs to present "1 listing, possibly 2
source views". Two implementation shapes:

**(a) Derived `canonical_listing_id` column on `active_listings`**

```sql
ALTER TABLE active_listings ADD COLUMN canonical_listing_id text NOT NULL
  GENERATED ALWAYS AS (
    md5(
      lower(regexp_replace(heimilisfang, '\s+', ' ', 'g')) || '|' ||
      postnr::text || '|' ||
      COALESCE(byggar::text, '?') || '|' ||
      COALESCE(round(einflm)::text, '?')
    )
  ) STORED;

CREATE INDEX idx_active_listings_canonical ON active_listings (canonical_listing_id);
```

UI groups by `canonical_listing_id`, surfaces multiple `source` rows for
each canonical listing.

**(b) Separate `canonical_listings` table** with FK from `active_listings`

Heavier-weight: separate table with `canonical_listing_id PK`, denormalized
common fields, FK from `active_listings.canonical_listing_id`.

**Recommendation pending #1A outcome**: shape (a) — derived column. Lower
migration cost, fits expected data volume, simple to reason about.
Reserve shape (b) for if cross-site dedup logic gets complex (per-canonical
aggregations like "lowest price across sources", or canonical-level
moderation flags). The match-key components mirror the mirror-investigation
fallback tuple from §1 by design — keeps the algorithm consistent across
research and production.

### 4.3 Inter-track linkage (active_listings ↔ properties)

Track A finds active listing for Hraunbær 162. Track B has confirmed
fastnum 1234567 for Hraunbær 162 in `properties`. Linkage:

- `active_listings.fastnum` is FK to `properties.fastnum` (nullable —
  a NULL means the listing has not yet been matched to an HMS row, not
  that HMS lacks the row)
- Match logic at scrape time:
  - If listing has explicit fastnum metadata in source HTML: trust it,
    set `fastnum`
  - Else: fuzzy-match on `(heimilisfang_normalized, postnr, byggar, einflm)`
    against `properties` rows
  - If fuzzy match yields exactly one candidate within similarity threshold:
    set `fastnum`
  - If fuzzy match yields zero or multiple candidates: leave `fastnum = NULL`
    (deterministic behavior — never auto-resolve ambiguity)

Unmatched-but-possibly-matchable listings are surfaced via Sentry-flagged
metric `active_listings_unmatched_count{source}`. Not a v1 manual-review
queue; just a visibility signal. If the metric trends high, that suggests
either Track B is slow (HMS hasn't issued fastnum yet for new construction)
or the fuzzy-match similarity threshold is too tight.

### 4.4 Edge cases (catalog)

| Case | Resolution |
|---|---|
| Same address, different fastnum (multi-unit building) | Do not auto-match if multiple `properties` candidates within similarity threshold; leave `fastnum = NULL`. UI shows listing as unlinked. |
| Address misspellings | `heimilisfang_normalized` strips diacritics + lowercases + collapses whitespace. Postnr + byggar + einflm act as secondary disambiguators. |
| New construction without fastnum yet | Agent posts "Hagaholt 4" before HMS issues fastnum. Listing lands with `fastnum = NULL`. Track B's monthly walk eventually issues the fastnum. **Bounded Dagster sensor** re-matches — see *Sensor scope* note below table. Pattern mirrors Bug 16 photo-fastnum reconciliation. |
| Listing reappears after withdrawal (relisted) | Same `(source, listing_id)`: clear `withdrawn_at`, INSERT history row with status='active'. Different `(source, listing_id)` for same canonical listing: handled by cross-site / canonical layer. |
| Source returns slightly different HTML structure mid-cycle | `content_hash` flags as 'attributes_changed'. If the change is parser-side (false positive from selector mismatch), Sentry alert from §2 health monitoring catches it. No data corruption — worst case is a spurious history row, easily filtered. |

**Sensor scope (new-construction reconciliation, bounded)**: the Dagster
sensor fires on **Track B 'new fastnum issued' events specifically**
(not on every Track B refresh), and reconciliation scope is bounded to:

- (a) `active_listings` rows with `fastnum IS NULL`
- (b) `first_seen_at >= now() - interval '90 days'` (lookback limit —
  beyond 90 days, an unmatched listing is unlikely to ever match)
- (c) `postnr` matching the new fastnum's `postnr` (locality limit —
  fuzzy address match across postnr is noise)

This bounds sensor cost per Track B refresh by O(new_fastnum_count ×
matching_unmatched_listings), not O(all_unmatched_listings ×
all_new_fastnums) as a naïve implementation would. Typical
new_fastnum_count per Track B monthly cycle is 50-200; bounded
unmatched-listings within 90 days × matching postnr is typically <100.
Sensor work per cycle: ≤20K candidate pair-checks, well within
Dagster + Postgres comfort.

---

## Section 5 — UI integration

(Per consumer. Track-specific implications called out where they apply.)

### 5.1 Search RPC (`search_properties_grouped`)

Existing `search_properties_grouped` reads from `properties`. **Track B**
inserts/updates rows in the same `properties` table → search auto-includes
the new ~25K rows once written. **No RPC changes required for Track B**.

For **Track A**: should search RPC also surface active listings (e.g.
"Hagaholt 4 — virk auglýsing 45M kr")? Out of v1 scope. Conflating
property-registry search with listing search is a UX decision that
needs its own pass. v1 search remains fastnum-keyed; v1.1 may add an
active-listings search variant or join.

### 5.2 `/eign/[fastnum]` page rendering

Track B adds rows to `properties`. Each new row goes through the existing
`/eign` render path. Behavior depends on Decision-point #2A outcome:

| #2A path | iter4 prediction state for new Track B rows | `/eign` render |
|---|---|---|
| **B1** (refactor) | Picked up by iter4 after Supabase-read refactor lands | Renders normally with prediction card |
| **B2** (twin-write) | Picked up by iter4 in next monthly model-refresh cycle | Renders normally after that cycle |
| **B3** (frozen pickle) | Not scored by iter4 until iter5 retrains | Falls back to "verðmat ekki tiltækt" empty-state |

**B3-specific empty-state copy** (distinct from Áfangi 4.10's commercial
empty-state):

> Verðmat fyrir þessa eign er ekki tiltækt núna. Eignin var nýlega bætt
> við úr HMS-gögnum og verður scored í næstu líkanauppfærslu.

Implementation note: distinguish Track B-fresh rows from genuinely
unscored rows via `properties.hms_fetched_at IS NOT NULL AND
predictions.fastnum IS NULL`. The empty-state copy fires only on this
specific predicate; other unscored cases (data-quality exclusions,
non-residential) keep their existing copy.

### 5.3 Market-scan view (`/markadur/auglysingar`) — API surface only

Per original prompt: market-scan UI is a separate spec session
(MARKET_SCAN_SPEC). SCRAPER_SPEC v1 commits the **API surface** Track A
delivers, not the UI:

- `active_listings_public` view (per §3.3): canonical public-readable
  surface
- `active_listings_history_public` view: time-series for TOM tracking,
  price-change overlays
- Suggested join surface for the `verdmat_diff_pct` market-scan column:

  ```sql
  SELECT
    al.fastnum, al.heimilisfang, al.postnr, al.canonical_code, al.einflm,
    al.byggar, al.asking_price, al.list_date, al.days_on_market,
    p.real_pred_mean   AS verdmat_mean,
    p.real_pred_pi80_lo, p.real_pred_pi80_hi,
    ROUND(100 * (al.asking_price - p.real_pred_mean) / p.real_pred_mean, 1) AS verdmat_diff_pct
  FROM active_listings_public al
  LEFT JOIN predictions p USING (fastnum)
  WHERE al.withdrawn_at IS NULL
    AND al.fastnum IS NOT NULL
  ORDER BY verdmat_diff_pct ASC NULLS LAST;
  ```

  This is sketch-level — MARKET_SCAN session will refine.

**Feedback-loop hook**: the MARKET_SCAN UI spec session may surface new
field-requirements (e.g. agent-level aggregations, per-postnr summary
metrics, time-bucketed market-temperature signals). When that happens,
**capture them as v1.1 amendments to SCRAPER_SPEC** — do not block v1
implementation. Pattern: SCRAPER_SPEC and MARKET_SCAN_SPEC are in
feedback loop, but neither blocks the other. SCRAPER_SPEC v1 ships
first → market-scan UI build may surface gap → SCRAPER_SPEC v1.1
amendments → migration → market-scan ships.

### 5.4 Commercial listing filtering (Track A)

mbl.is and fasteignir.visir.is index residential listings primarily but
**include commercial atvinnuhúsnæði** (skrifstofur, verslun, iðnaðarbil).
Without filtering, market-scan UI gets a surprise mixed
residential+commercial feed.

**Cascading filter strategy at scrape time**:

| Filter level | Mechanism | Catches |
|---|---|---|
| Level 1 — index page | Scrape only residential category index pages (íbúðir, sérbýli, sumarhús, parhús, atvinnuhúsnæði intentionally excluded) | Bulk of commercial filtering |
| Level 2 — detail page heuristic | Parse the category/property-type field on each detail page; reject if matches commercial taxonomy (Atvinnuhúsnæði, Skrifstofa, Verslun, Iðnaðarhúsnæði, Vörugeymsla) | Edge-cases on shared category indexes |
| Level 3 — fastnum lookup | If `fastnum` is matched and `properties.is_residential = FALSE`, reject the listing | Agent typing mistakes; misclassified source listings |

**Reject means**: do not insert into `active_listings`. Log to a sidecar
`rejected_commercial_listings` table for audit (was this rejection
correct? If too many false-positives, tune the heuristic).

Audit sidecar table `rejected_commercial_listings` — see §3.1 for table
DDL and RLS policy (internal-only, indefinite retention).

Sentry-flag if rejection rate >5% week-over-week — likely heuristic drift
or source-side category re-shuffle. Audit log enables post-hoc analysis
without re-scraping.

### 5.5 Track B coverage boundary (Áfangi 4.10 cross-reference)

**Track B does not change Akralind / Akralind / commercial-conversion
edge cases**. Track B fills HMS fastanúmer gap, but Track B is not a
re-classification mechanism. Akralind cases are `is_residential = FALSE`
because HMS classifies them as commercial (Iðnaður, Skrifstofa, Verslun,
Vörugeymsla). When Track B scrapes their HMS rows, the rows still come
back as `is_residential = FALSE` and continue to flow through Áfangi 4.10
commercial empty-state copy.

**This is intentional**: HMS taxonomy is the canonical truth.
Re-classifying commercial buildings to residential because someone
happens to live in a converted office is an HMS-side concern, not a
verdmat.is concern. UI handles this via empty-state, not re-classification.

Three states the user might encounter — distinct empty-state copy each:

| Property state | Empty-state copy source | Example |
|---|---|---|
| `is_residential = FALSE` (commercial) | Áfangi 4.10 — "Þessi tegund eigna er ekki innan svigrúms verðmats" | Akralind 1, Vörugeymsla |
| `is_residential = TRUE`, no prediction (Track B fresh row, B3 path) | This spec §5.2 — "Eignin var nýlega bætt við úr HMS-gögnum..." | New construction, freshly issued fastnum |
| `is_residential = TRUE`, no prediction (data-quality exclusion) | Existing copy from Sprint 1 | e.g. extreme byggar outliers |

Do not collapse these three into one empty-state copy. Each communicates
a different signal to the user.

---

## Section 6 — Orchestrator integration

### 6.1 Resolution of Decision-point #2B (write path) — locked here

Per §2 / §3.6 deferral: scraper-to-Supabase write path. (i) direct
write vs (ii) Hetzner-local-staging-then-sync. **Resolved here per
mixed-approach recommendation.**

🔶 **Decision-point #2B — locked**:

- **Track A: (ii) Hetzner-local-staging-then-sync**. Volume profile (5-10K
  rows updated nightly per primary site, possibly 10-20K dual-source) +
  cross-source dedup makes mid-batch failure recovery important.
  Local Postgres staging + sync gives:
  - Replay surface for failed Supabase syncs
  - Atomic rollback if a corrupt batch is detected post-scrape
  - Decoupling from Supabase availability (Supabase outage queues; flushes
    when Supabase recovers — does not kill the scrape)
  - Mid-batch atomicity at sync time

- **Track B: (i) direct write**. Volume profile (~25K total over backfill,
  50-200/month steady-state). Direct write to Supabase via `psycopg` is
  simpler:
  - No staging layer overhead
  - HMS data is canonical; if a write fails, retry from HMS source is
    acceptable (not a transient stream)
  - 25K-row backfill chunks into nightly batches of 5-10K; per-night
    atomic transaction is sufficient

**Mixed-approach is OK** — Dagster orchestrator surfaces both clearly in
its job UI; per-track operational mode is documented and visible.
Trade-off accepted: slightly more infrastructure (a Hetzner-local
Postgres staging instance for Track A) in exchange for the resilience
properties that match Track A's volume + criticality profile. Track B's
lower volume + canonical-source nature means the staging layer would be
operational overhead without commensurate benefit.

**Bounding clause for #2B-(ii)**: per §4.2.1 cross-link, the audit-history
trigger fires on the **Supabase sync side**, not the Hetzner-local write
side. The Hetzner-local table is a transient staging layer with no
trigger. This keeps audit history single-sourced on Supabase.

### 6.2 Failure isolation — Track A nightly vs monthly model-refresh

**Hard requirement**: Track A nightly cycle MUST NOT cascade into monthly
model-refresh failure. Conversely, monthly model-refresh failure MUST
NOT halt Track A cycles.

**Mechanism**:
- Separate Dagster jobs, separate run-history, separate failure semantics
- Track A schedule: cron-like nightly trigger (00:00-04:00 Reykjavík)
- Monthly model-refresh: existing trigger (preserved unchanged)
- **No shared write surface**: Track A writes only to `active_listings`
  / `active_listings_history` / `rejected_commercial_listings`. Monthly
  refresh writes to `properties` / `predictions` / `comps_index` /
  `sales_history` / `repeat_sale_index` / `ats_lookup_*`. Disjoint.

**Reuse pattern from `refresh_dashboard_tables`**:

The Sprint 2 Áfangi 4 closure proved a production atomicity pattern:
subprocess isolation per script, shape-safety validation, rollback on
failure, cross-script transaction boundary. That pattern should be the
template for Áfangi 0 Dagster ops:

- Per-op subprocess isolation (Dagster `op` boundary maps to the
  existing per-script boundary)
- Shape-safety validation: each op declares expected output shape
  (column types, row count tolerance), verified before commit
- Rollback on failure: failed op aborts the wrapping transaction; no
  partial writes
- Sentry alerts on failure: surfaces visibility immediately

**Cross-job dependencies**: none. Dagster job graph for Áfangi 0 is
disconnected from monthly refresh job graph by design.

### 6.3 Inter-track sequencing (Track B steady-state placement)

When Track B steady-state monthly runs (post-initial-backfill), where
does it sit relative to monthly model-refresh?

Two options:
- **Before `rebuild_training_data`**: Track B's new fastnum rows are
  included in this cycle's training data
- **After `rebuild_training_data` (and after `refresh_dashboard_tables`)**:
  model-refresh happens unblocked by Track B; new fastnum rows enter
  training data on the next cycle (1 month later)

**Recommendation: AFTER**. Reasoning:

- Decoupling is more valuable than 1-month training data freshness on the
  marginal ~50-200 new fastnums (out of ~125K total properties). 0.04-0.16%
  marginal coverage gain on training data is not worth the cascade risk.
- Training data has a 1-month kaupskra cadence anyway — adding sub-month
  resolution on Track B is a false-precision optimization
- Monthly model-refresh predictability is more important than freshness
  on edge cases (many of which are new construction that won't have sold
  yet, so no kaupskra row to train on regardless)
- Failure of slow Track B cycle (e.g. HMS rate-limit incident) doesn't
  cascade to model-refresh

**This aligns with Decision-point #2A B3 default**: Track B rows enter
`properties` immediately for search; iter4 (or iter5) scores them on
next training cycle. After-sequencing reflects the same "1-month lag is
acceptable" implicit assumption.

**Sequence (ASCII-time)**:

```
Track A nightly:  [n] [n] [n] [n] [n] [n] [n] [n] [n] [n] [n] [n] ...
                    (independent — every night, never blocked)

Monthly cycle:                                [refresh_cpi]
                                              [refresh_kaupskra]
                                              [rebuild_training_data]
                                              [refresh_dashboard_tables]
                                              [Track B steady-state]    <-- after-position
                                              ↓
                                              (new fastnum rows in
                                               properties; included
                                               in next month's training)
```

**Initial backfill** (Track B Phase 1+2, one-time over 3-5 nights) sits
**outside the monthly cycle entirely** — it's a one-time op, scheduled
explicitly during a low-traffic window, not on the monthly cron. After
backfill completes, Track B steady-state slots into the after-position
of monthly cycle described above.

### 6.4 Health monitoring integration

Dagster sensor + alert integration with §2 health monitoring spec:

- **Heartbeat counter**: each Dagster op increments
  `scraper_cycle_completed_total{track,source}` via Prometheus pushgateway
  on successful completion. Grafana panel reads this directly.
- **Volume gauge**: each scrape op updates
  `scraper_listings_fetched_total{track,source}` at end of run.
- **Sentry routing**: Dagster op-level failures route to Sentry; volume
  thresholds (per §2) route to Sentry independently. Cascading silence
  detection: if both Sentry and heartbeat fall silent simultaneously,
  Grafana dashboard "scraper liveness" panel shows red.

This last point is the explicit lesson from 2025-07: silent death is
silent in the absence of multiple independent observability channels.
Heartbeat alone is insufficient if the heartbeat-emitter itself dies.
Volume monitoring + Sentry + heartbeat combined catches all known
failure modes.

---

## Section 7 — Tracks-specific edge cases / operational concerns

(Catch-all for per-track operational concerns not captured by the §4.4
dedup edge-case catalog. Focus on operational not data-shape.)

### 7.1 Track A — Anti-bot detection escalation strategy

mbl.is and fasteignir.visir.is may deploy bot detection at any time —
neither has currently aggressive anti-bot, but both may add it in
response to scrape volume or unrelated business decisions.

**Tiered escalation**:

| Tier | Trigger | Response |
|---|---|---|
| 1 | Soft detection (Cloudflare challenge, captcha, anomalous 4xx) | Pause source, alert Sentry, manual review by Danni. **No auto-recovery** — humans decide whether to continue, throttle, or escalate. |
| 2 | IP block (sustained 403/429 from primary Hetzner IP) | Rotate to backup Hetzner IP (one extra IP allocated as part of infra). If second IP also blocked: halt source entirely, alert Sentry, escalate to Tier 3. |
| 3 | Account/header block, or both IPs blocked | Open dialogue with source operator (mbl.is editorial / Sýn fasteignir vertical). Out of automated v1 scope. |
| 4 | Full source unavailability >30 days | Fall back to e-value.is aggregator (per §1 fallback). Tracked as v1.1 amendment. |

**User-Agent + request hygiene** (preventive, not responsive):
- Use a descriptive User-Agent identifying the project:
  `verdmat.is/0.1 (+https://verdmat.is/um) python-requests`. Source
  operators are more lenient with identifying scrapers and the UA gives
  them a contact path if there's a problem.
- Respect `robots.txt` always, even where not technically enforceable
- Respect rate-limit responses (429 backoff, full `Retry-After` honored)
- Don't spoof referrer or session

**Reputational hygiene** (parallel to §1 HMS approach):
- Open dialogue with mbl.is and Sýn proactively before scrape ships:
  "We're building a verðmat platform aggregating listing data; here's
  our scrape footprint; can we do this respectfully?"
- This preempts Tier 3 escalation. Unlike HMS (which is a
  formal-engagement requirement), private-sector source dialogue is
  best-effort but still high-leverage.

### 7.2 Track A — Withdrawn-listing detection robustness

Operational concern: how do we distinguish "truly withdrawn" from
"missed in this scrape" (transient source-side error, scraper-side bug,
network glitch)?

**Mechanism**: 2-night absence rule.

- Listing must be absent from index for **2 consecutive nightly scrapes**
  before `withdrawn_at` is set
- 1-night absence: treated as transient (no state change, just don't
  update `last_seen_at`)
- 2-night absence: confirmed withdrawal, `withdrawn_at = now()`, audit
  history INSERT

**Recovery / relisting**:
- Listing reappears within 14 days of `withdrawn_at`: clear `withdrawn_at`,
  INSERT history row with status='active'. Treat as continuation, not new
  listing.
- Listing reappears after 14 days: typically arrives with different
  `(source, listing_id)` (agent re-posts, gets new internal ID). Handled
  by normal new-listing path.

**Edge case**: source returns a partial index (network-induced or
source-side bug producing only top-N listings). The 2-night rule could
incorrectly mark legitimate active listings as withdrawn if both nights
hit a partial-index bug.

**Sanity check (Track A nightly cycle)**: at end of each fetch pass,
compare today's listing count against the trailing 7-day mean of listing
counts (computed from `active_listings_history` `observed_at` timestamps,
restricted to the same source). If today's count < 70% of the trailing
7-day mean, halt withdrawn-detection logic for this cycle, do not mark
any listings as withdrawn, and raise a Sentry alert with payload
`{today_count, mean_7d, ratio, source}`.

**Rationale**: day-of-week seasonality (weekend vs weekday upload
patterns) can cause ±15-20% swings in index size without indicating any
scraper malfunction; trailing 7-day mean normalizes seasonality
automatically. A fixed cycle-over-cycle threshold (e.g. "50% of last
cycle") was rejected because Saturday → Sunday normal-volume swings can
approach 50% in a stable regime, producing false halts on routine
weekly patterns. The 70%-of-7-day-mean threshold preserves sensitivity
to genuine partial-failure modes (selector decay producing fragmentary
fetches, network drops mid-pagination) without false-tripping on weekly
seasonality.

### 7.3 Track B — HMS dialogue fallback ladder

Operational risk: formal HMS access dialogue (per §1 preferred path) may
take weeks-to-months to resolve. Project cannot wait that long for Track
B implementation if launch timing presses.

**Fallback ladder**:

| Tier | Path | Time-to-start | Acceptable? |
|---|---|---|---|
| 1 | Formal API access | 4-8 weeks dialogue | Preferred. Lock in if granted. |
| 2 | Bulk-export agreement | 4-8 weeks dialogue | Acceptable — periodic full export from HMS, no scraping needed. |
| 3 | Public records query at hms.is (technical scrape) | Immediate | Fallback if Tier 1+2 stalled past 8 weeks. Conservative throttle (1 req per 2-5 sec, spread over days). |
| 4 | e-value.is aggregator fallback (per §1) | Immediate | Last resort. v1 acceptable; v1.1 plan to revisit HMS dialogue once project has more public credibility. |

**Decision tree at implementation kickoff**:

```
Week 0: Open formal HMS dialogue (Tier 1+2 in parallel)
Week 4: Status check — granted, in-progress, or denied?
  - Granted Tier 1 or Tier 2 → lock in, implementation begins
  - In-progress → wait, status check again Week 8
  - Denied → start Tier 3 (technical scrape) immediately
Week 8: If Tier 1+2 still in-progress → start Tier 3 in parallel
        (formal access lock-in if/when it lands later, swap source)
Week 12+: Tier 3 fully active; revisit Tier 1+2 dialogue v1.1
```

Document all dialogue decisions in DECISIONS.md as they happen.

### 7.4 Track B — New-fastnum issuance discovery

HMS issues new fastnums for new construction at varying cadences
(typically monthly batches; sometimes single issuances). Track B
steady-state monthly cycle catches these with 0-30 day lag depending on
issuance timing relative to scrape day.

**Operational concern**: how do we know we caught all new fastnums in a
given cycle, especially if HMS issues out-of-sequence?

**Mechanism**:
- Track B walks fastnum number-space (per §3 Phase 1 strategy) from
  `last_walked_fastnum + 1` each cycle
- HMS generally issues monotonically, but rare out-of-sequence happens
  (e.g. retroactive corrections, fastnum re-issuance after voided record)
- **Compromise**: walk last 6 months of `properties.fastnum` MAX values,
  gap-fill any missing in that range. This catches retroactive
  out-of-sequence issuances without requiring full-range re-walk.
- Full-range re-walk happens only on backfill (one-time), not on
  steady-state.

### 7.5 Inter-track edge cases

Already covered:
- §4.3 — `active_listings ↔ properties` linkage
- §4.4 — edge case catalog including new-construction reconciliation
- §4.4 sensor-scope note — bounded sensor for fastnum-issuance ↔
  unmatched-listing reconciliation

No additional edge cases here. Pointer to those sections for
cross-reference; this subsection exists to make the spec scannable
("did we cover X?").

---

## Section 8 — Build order, time estimates, dependencies

### 8.1 Dependency graph

Build sequence has parallel branches. Step 1 (deployment infra) gates
everything; Steps 2 and 3 run in parallel as independent gates; Steps 5
and 6 run in parallel after their respective gates close.

```
Step 1: Secrets + deployment infra (3-5d)
   │
   ├──────────────────────────────────────╮
   ▼                                      ▼
Step 2: Mirror-investigation       Step 3: HMS dialogue
        audit script (5-7d)               (4-12 weeks, parallel
        │                                  to all other work)
        ▼                                  │
🔶 #1A closes (Track A source pick)        ▼
        │                          🔶 #1B closes (Track B
        │                                   HMS access path)
        │                                  │
        ▼                                  │
Step 4: Schema migrations ◄────────────────┤
        (1-2d)                             │
        │                                  │
        ├──────────────────────────╮       │
        ▼                          ▼       ▼
Step 5: Track A implementation   Step 6: Track B implementation
        (7-10d)                          (5-7d backfill + ongoing)
        │                                │
        ╰─────────────────╮  ╭───────────╯
                          ▼  ▼
                Step 7: Orchestrator wiring (3-5d)
                          │
                          ▼
                Step 8: Health monitoring integration (2-3d)
                          │
                          ▼
                Step 9: UI integration (2-3d)
                          │
                          ▼
                Step 10: Production cutover (1-2d)
```

**Critical-path observations**:
- Step 3 (HMS dialogue) is the long-tail unknown. If formal access lands
  by Week 4, total clock time is ~6-8 weeks. If HMS Tier 3 fallback
  triggers at Week 8 (per §7.3 ladder), total clock is ~10-12 weeks.
- Step 2 audit script can complete during Step 1 deployment if a
  pre-deployment Hetzner box is available, compressing schedule by 5-7 days
- Steps 5 and 6 are theoretically parallel-capable; in
  single-developer-with-AI-assistant practice, parallelism requires
  either two simultaneous Claude Code sessions on disjoint repos
  (operationally expensive — context-management cost, divergent
  decision drift risk) or sequential implementation with
  context-switching overhead. Default planning assumption is
  **sequential 5 → 6** with 6 → 7 dependency-ordering. Parallel
  execution reserved for cases where backlog pressure justifies the
  coordination overhead.

### 8.2 Step-by-step build sequence

#### Step 1 — Secrets management + deployment infra (3-5 days)

**This step is foundation**. It gates everything else, and historically
gets treated as afterthought — addressing first.

Deliverables:
- Hetzner dedicated host provisioned (per DECISIONS line 1729 stack:
  PostgreSQL 16 + PostGIS + R2 + Docker Compose + Dagster + MLflow +
  Grafana/Prometheus/Sentry + FastAPI)
- `verdmat-is-scraper` GitHub repo initialized with `.gitignore`,
  `README.md`, `.env.example`, `docker-compose.yml` skeleton (mirror
  pattern from `verdmat-is-precompute`)
- Secrets management:
  - `.env` file structure documented in `.env.example` (committed)
  - **Production secrets never git-committed** — stored via
    Hetzner-side vault or 1Password Connect, mounted into containers
    at deploy time
  - Secrets surface: HMS API credentials (if Track B Tier 1/2 succeeds),
    source-site session cookies/UA strings (if Track A audit reveals
    login or persistent UA needed), Sentry/Grafana/Prometheus tokens,
    Supabase service-role key, Hetzner-local Postgres staging credentials
- Dagster instance up + reachable + monitored
- Sentry + Grafana + Prometheus baseline dashboards reachable (panel
  scaffolding for Step 8 to populate)

Gating: nothing parallel; everything else depends on this.

#### Step 2 — Mirror-investigation audit script (5-7 days, parallel with Step 3)

Per §1 audit-script-first principle. Script lives in `audit/` directory
of `verdmat-is-scraper` repo.

Deliverables:
- Audit script that scrapes mbl.is + fasteignir.visir.is active-listings
  indexes for 5-7 consecutive days (per §1 sample window)
- Match-key tuple computation: `(heimilisfang_normalized, postnr,
  agent_listing_id)` if listing_id exposed; fallback `(heimilisfang_normalized,
  postnr, byggar, einflm)`
- Output report: overlap %, per-site uniques, per-region/segment
  distribution, per-day flux
- Operational pre-checks recorded: robots.txt + ToS + rate-limit reality
  + auth requirement + freshness lag (per §1 Operational pre-checks
  list)

Gating: Step 1 complete (audit script needs Hetzner host or local Python
env to run; Hetzner preferred so scrape originates from production IP).

Closes 🔶 **Decision-point #1A** on completion.

#### Step 3 — HMS dialogue / formal API request (4-12 weeks, parallel)

Per §7.3 dialogue ladder. Tier 1 and Tier 2 dialogues run in parallel
with all other technical work.

Deliverables:
- Week 0: formal HMS dialogue opened (parallel: Tier 1 API + Tier 2
  bulk-export). Piggyback on Áfangi 4.9 matsvæði-polygon engagement
  per §1.
- Week 4: status check. If granted Tier 1 or 2 → lock in. If
  in-progress → wait. If denied → start Tier 3 (technical scrape)
  immediately.
- Week 8: if Tier 1+2 still in-progress → start Tier 3 in parallel
  (formal-access lock-in if/when it lands later, swap source).
- Week 12+: Tier 3 fully active if Tier 1+2 unresolved; revisit
  dialogue v1.1.

Gating: independent of Step 2 (the two are parallel). Decision-point
#1B closes on Tier 1/2 outcome OR on Week 8 fallback to Tier 3.

#### Step 4 — Schema migrations (1-2 days)

All tables and view definitions per §3 storage taxonomy:
- `active_listings` + indexes
- `active_listings_history` (partitioned by quarter on `observed_at`,
  partition for current + next quarter created)
- `rejected_commercial_listings`
- `properties.hms_fetched_at`, `properties.hms_payload` ALTER TABLE
- `active_listings_public` view (per §3.3 RLS pattern, `listing_id`
  excluded)
- `active_listings_history_public` view (`content_hash` excluded)
- All RLS policies enabled per §3.3
- Audit-trigger on `active_listings` UPDATE per §4.2.1 (single-writer
  bounding clause noted)

Deliverable: migration file in `verdmat-is/app/supabase/migrations/`,
applied to dev → staging → production.

Gating: Step 1 complete (Supabase service-role key needed for migration
apply). Decision-points #1A and #1B do NOT gate Step 4 — schema is
source-pick-agnostic.

#### Step 5 — Track A implementation (7-10 days, parallel with Step 6)

Implementation surface:
- Crawl strategy per §2 Track A subsection (incremental delta crawl,
  content-hash change detection)
- Hetzner-local Postgres staging + sync to Supabase per #2B (i)/(ii)
  locked outcome
- Cascading commercial filter per §5.4 (3 levels + audit log)
- Cross-site dedup per §4.2.2 (gated on #1A outcome — single-source
  ships nothing here, dual-scrape adds derived `canonical_listing_id`
  column)
- Anti-bot escalation hooks per §7.1
- Withdrawn-listing 2-night absence rule + 7-day-mean sanity check per
  §7.2

Gating: Step 4 (schema) + Decision-point #1A closed (source pick known).

#### Step 6 — Track B implementation (5-7 days backfill + ongoing, parallel with Step 5)

Implementation surface:
- Phase 1 gap-identification per §2 Track B subsection + §6.3 (HMS
  bulk-export diff if Tier 2; systematic walk if Tier 3)
- Phase 2 backfill: 5-10K fetches/night × 3-5 nights to cover ~25K gap
- Phase 3 steady-state: monthly 50-200 fastnum delta, slotted AFTER
  `refresh_dashboard_tables` per §6.3 sequencing
- Direct write to Supabase per #2B (i) locked
- ON CONFLICT DO UPDATE WHERE payload-changed per §4.1
- Bounded reconciliation sensor per §4.4 sensor-scope note
- HMS dialogue ladder execution per §7.3

Gating: Step 4 (schema) + Decision-point #1B closed (HMS access path
known). #2A may or may not be closed depending on timing — see §8.3.

#### Step 7 — Orchestrator wiring (3-5 days)

Dagster job graph:
- Track A nightly schedule (cron-like, 00:00-04:00 Reykjavík)
- Track B steady-state monthly schedule (after-position per §6.3)
- Cross-reference reconciliation sensor (per §4.4) wired to Track B
  monthly events
- Failure isolation per §6.2 (separate jobs, disjoint write surfaces)

Gating: Steps 5 and 6 both complete (orchestrator wires them, can't
wire pieces that don't exist).

#### Step 8 — Health monitoring integration (2-3 days)

Per §6.4 + §2:
- Prometheus pushgateway counters/gauges from each Dagster op
- Grafana dashboard panels (heartbeat, volume, error rate, scraper
  liveness)
- Sentry alert routing per §2 SLA + §7.1 escalation tiers
- `/health` endpoint on scraper container

Gating: Step 7 (orchestrator) — monitoring observes orchestrator state.

#### Step 9 — UI integration (2-3 days)

Per §5:
- `/eign/[fastnum]` empty-state copy for Track B fresh rows (per §5.2,
  conditional on #2A B3 path)
- Search RPC: no changes needed for Track B (auto-includes new rows);
  Track A search is v1.1 deferred per §5.1
- Market-scan API surface: views are already in place from Step 4;
  MARKET_SCAN session consumes from there (§5.3)

Gating: Steps 5+6 producing data into the views; Step 4 view DDL.

#### Step 10 — Production cutover (1-2 days)

- Switch Dagster schedules from "manual trigger" to "cron-active"
- Observation period: 1 week of nightly Track A cycles + first monthly
  Track B steady-state cycle
- Sentry/Grafana watch for unexpected signals
- Decision-point #2A closure (B1/B2/B3 path lock) latest by end of
  Track B initial backfill — if not closed by then, defaults to B2
  twin-write per §3.5

Gating: Steps 7-9 all green.

### 8.3 Decision-point gating timeline

| ID | Decision | Closes by | Gates |
|---|---|---|---|
| 🔶 #1A | Track A source pick (single-source vs dual-scrape) | End of Step 2 | Step 5 |
| 🔶 #1B | Track B HMS access path (Tier 1/2/3/4) | Week 4-12 of Step 3 | Step 6 |
| 🔶 #2A | Track B pickle migration (B1/B2/B3) | End of Track B initial backfill (Step 6 Phase 2) at latest | Step 6 Phase 3 (steady-state ETL shape) |
| 🔶 #2B | Write path (direct vs staging) | **LOCKED in §6.1** — Track A: (ii), Track B: (i) | Reference only |

**#2A note**: Decision-point #2A is NOT a blocker for Step 6 initial
backfill — initial backfill writes direct to Supabase per #2B (i)
locked. #2A only matters for steady-state ETL shape post-backfill (does
the steady-state cycle twin-write to pickle, or not). If #2A is not
explicitly closed by end of initial backfill, the spec defaults to B2
(twin-write) per §3.5 fallback rule.

### 8.4 Time estimate summary

| Step | Duration | Critical path? |
|---|---|---|
| 1 | 3-5d | Yes — gates all |
| 2 | 5-7d | Parallel with 3 |
| 3 | 4-12 weeks | Parallel; long-tail unknown |
| 4 | 1-2d | After #1A close |
| 5 | 7-10d | Parallel with 6 |
| 6 | 5-7d backfill + ongoing | Parallel with 5 |
| 7 | 3-5d | After 5+6 |
| 8 | 2-3d | After 7 |
| 9 | 2-3d | After 7 |
| 10 | 1-2d | After 7-9 |

**Total clock time (best case, formal HMS access in ~4 weeks)**: ~6-8 weeks
**Total clock time (HMS Tier 3 fallback at Week 8)**: ~10-12 weeks

These are **scope-only effort estimates, not calendar deadlines**.
Critical path is gated by external dependencies (HMS dialogue timing
especially) and may extend further if any gate stalls. Project
convention favors %-complete tracking over fixed dates per
`WORKING_PROTOCOL.md`.

---

## Section 9 — Open questions and decisions deferred

### 9.1 Empirical unknowns that gate decisions

These cannot be answered from the spec; they require running the
audit-script-first deliverables (§1).

- **Mirror-investigation overlap %** between mbl.is and fasteignir.visir.is
  — gates #1A. Output of Step 2.
- **HMS API existence + access mechanism** — gates #1B. Output of Step 3
  Tier 1/2 dialogue or Tier 3 fallback probe.
- **mbl.is and fasteignir.visir.is robots.txt content** — gates ToS
  posture and acceptable-use boundary. Output of Step 2 operational
  pre-checks.
- **Actual sustainable rate-limit ceiling per source** — gates Track A
  cadence and parallelism choices. Output of Step 2 rate-limit-reality
  probe.

### 9.2 Operational unknowns resolved during implementation

These will resolve naturally as implementation progresses. Listed as
known-unknowns so future-Claude doesn't treat them as gaps.

- **Specific anti-bot detection thresholds per source** — only learned
  by hitting them. Tier-1 escalation per §7.1 catches first occurrence.
- **Source-side cookie / session management requirement** — discovered
  during Step 2 audit. If session-bearing required, Step 5 implementation
  expands by 1-2 days for cookie-jar plumbing.
- **Exact HTML selector stability** — selectors will drift; question is
  *how often*. Volume-based monitoring per §2 catches drift; specific
  selector versions will be refactored as drift events occur.
- **Hetzner instance sizing** — initial provisioning at Step 1 is best-guess
  (probably 4-vCPU + 16GB RAM + 200GB SSD). Adjust based on observed
  scrape concurrency + Postgres staging size after first 30 days.

### 9.3 Items deferred for future v1.x / v2

- **v1.1 share-link surrogate column UI integration**: per §3.3 escape
  hatch — `public_id uuid DEFAULT gen_random_uuid()` exposed via view if
  market-scan UI introduces per-listing share links. Reserved, not v1.
- **v2 cold-storage archival path for `active_listings_history`**:
  partitions older than 24 months → cold-tier copy + drop partition.
  Schema design supports this without migration. v2 only when row count
  becomes binding constraint.
- **v2 multi-region matsvæði polygon overlay**: cross-link to Áfangi
  4.9 (matsvæði-level polygon shapefile, in PLANNING_BACKLOG.md). Once
  shapefiles land, market-scan UI can use them for region-level
  aggregation. SCRAPER_SPEC v1 does not need them.
- **Catastrophic-failure rollback / disaster recovery**: Track A
  inherits implicit rollback from Hetzner-local staging layer (#2B (ii))
  — corrupt batch can be re-synced from staging snapshot. Track B
  direct-write to Supabase has no native rollback in v1; mitigation is
  per-batch transaction with rollback on validation failure (already
  covered in §6.2 atomicity pattern). Future v2 should establish
  formal Supabase PITR retention policy (24-72 hour minimum) as
  project-wide DR baseline, not Áfangi 0 specific.

### 9.4 v1.x amendments hook

SCRAPER_SPEC v1 will accumulate amendments from:

- (a) mirror-investigation results (Step 2)
- (b) HMS dialogue outcomes (Step 3)
- (c) MARKET_SCAN UI spec session field-requirements (per §5.3 hook)
- (d) anti-bot escalation experience post-deployment (per §7.1)

**Format**: append dated subsection at end of doc under heading
`## Amendments — v1.x` with date, source-event, and changed sections.
**Bump rule**: when amendment count exceeds 5, OR any single amendment
is materially scope-changing (introduces new track, retires existing
track, changes DR posture), bump to v2 spec.

### 9.5 Consolidated decision-point status

Single audit-trail list. Cross-references back to where each is
introduced and resolved.

| ID | Decision | Status | Introduced | Closes |
|---|---|---|---|---|
| 🔶 #1A | Track A source pick (single-source vs dual-scrape, which primary) | DEFERRED | §1 | End of Step 2 (mirror-investigation) |
| 🔶 #1B | Track B HMS access path (Tier 1/2/3/4 ladder outcome) | DEFERRED | §1 | Step 3 dialogue, by Week 4-12 |
| 🔶 #2A | Track B pickle migration (B1 / B2 / B3) — default fallback B2 if Áfangi 4.8 unresolved | DEFERRED | §3.5 | End of Track B initial backfill at latest |
| 🔶 #2B | Scraper-to-Supabase write path (direct vs staging) | **LOCKED** — Track A: (ii) Hetzner-local-staging-then-sync; Track B: (i) direct write | §2 (deferred) → §6.1 (locked) | N/A (closed) |

---
