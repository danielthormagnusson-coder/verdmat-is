# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

verdmat.is — Icelandic property-valuation web app. Next.js 16 (Turbopack) + Supabase + Vercel front-end serving an LightGBM hedonic-pricing model (iter4 prod, conformal-calibrated) trained on ~226K thinglýstir kaupsamningar. The repo also holds the Python pipelines that scrape HMS Fasteignaskrá, build training data, and sync the resulting HMS metadata into Supabase. Live at https://verdmat-is.vercel.app.

**Language**: JavaScript, not TypeScript. `jsconfig.json` sets the `@/` alias (root). No `types.ts` — Supabase columns are inferred at runtime via `@supabase/supabase-js`.

## Commands

```bash
npm run dev        # Next.js 16 dev server (Turbopack)
npm run build      # production build — must pass before pushing UI changes
npm run lint       # eslint (config: eslint.config.mjs, eslint-config-next 16.1.6)
npm run start      # serve the production build locally
```

Python ops scripts live in `scripts/` and are invoked directly (Python 3.14, deps installed at user level — pandas, psycopg2, curl_cffi, python-dotenv, pyarrow). Run from repo root:

```bash
python scripts/phase_d1_extract.py        # local-only, reads audit/hms_archive_staging.db
python scripts/phase_d1_dryrun.py         # coverage report + generates D:\phase_d1_rollback.sql
python scripts/phase_d1_apply.py          # writes to Supabase; requires SUPABASE_DB_URL env var
python scripts/backup_setup.py            # generates D:\verdmat-is\tools\rclone\rclone.conf
python scripts/backup_nightly.py          # sync → r2backup:verdmat-backups/current/
python scripts/backup_restore_test.py     # 5-file SHA-256 round-trip from current/
```

Supabase migrations land in `supabase/migrations/YYYYMMDD_<name>.sql` and are applied via the Supabase MCP `apply_migration` tool (or the Supabase CLI when set up — Phase X Group B work). The MCP is the primary execution channel for SQL during development sessions.

## Architecture — big picture

**Data flow**: HMS scrapers (evalue.is + hms.is API) on `D:\` → SQLite + CSV + pickle in `D:\Gagnapakkar\` and `D:\` root → Python precompute pipeline (separate repo `verdmat-is-precompute`) builds training data + LightGBM models → outputs in `D:\*.pkl`, `D:\*.lgb` → Supabase tables (`properties`, `predictions`, `comps_index`, `feature_attributions`, `sales_history`, `ats_lookup`, `llm_aggregates_quarterly`, etc.) → Next.js app reads via `@supabase/supabase-js` → Vercel deploys.

**Supabase project**: `szzjsvmvxfrhyexblzvq` (verdmat-is, eu-north-1). The PostgreSQL direct connection string (transaction pooler, port 6543, IPv6-safe) lives at `D:\verdmat-is\.dbconfig` (UTF-8 with BOM — read via `open(path, encoding='utf-8-sig')`, not bash `tr` which mis-handles the BOM bytes). `D:\verdmat-is\.env` holds R2 backup creds; `app/.env.local` holds the public Supabase URL + anon key for the Next.js app.

**Routes** (`app/` directory, Next.js App Router):
- `/` — landing + autocomplete + 3 featured properties
- `/eign/[fastnum]` — property detail with `PredictionCard`, `AttributionWaterfall` (SHAP), `CompsGrid`, `SalesHistoryTable`, `ValuationStrip` (Path C), `LhlmatBar` (Path C), `ByggingarstigBadge` (Path C), `MarketContextCard`, `PhotoGallery`, react-leaflet map
- `/eign/[fastnum]/stilla` + `/nidurstada` — questionnaire-driven personalised valuation + PDF export
- `/markadur` + 4 sub-routes (`visitala`, `markadsstada`, `ibudir`, `modelstada`) — public dashboard
- `/um`, `/login`, `/pro`, `/auth/callback`, `/api/{adjust-valuation,backproj/[fastnum],search}`

**Source-of-truth boundaries** (decision 2026-05-20, see `docs/SOURCES_OF_TRUTH.md`):
- **Supabase `properties` is canonical for HMS metadata** (fasteignamat, einflm, byggar, byggingarstig, brunabotamat, matseiningar, lhlmat, etc.). `D:\properties_v2.pkl` is now a derived training cache — `rebuild_training_data.py` must export from Supabase each cycle (Phase X/Y follow-up).
- Sales history canonical at `D:\kaupskra.csv` (HMS thinglýsing dump) — joined via `faerslunumer` (sale transaction PK).
- Listings canonical at evalue.is scrape outputs (`D:\Gagnapakkar\fasteignir{,1-4}.db`) — joined via `augl_id` (listing PK).
- `pairs_v1.pkl` is the only non-native join (augl_id ↔ faerslunumer within a fastnum, temporal + price logic).

**Models**: iter4_final_v1 (conformal-calibrated, no fasteignamat input) is production. iter3v2 archived; surfaces in debug mode (`?mode=debug` on `/eign/[fastnum]`) for comparison. iter5 planned — blocked on Phase D bringing HMS data into Supabase + `rebuild_training_data.py` export step (see `docs/PLANNING_BACKLOG.md`).

**Authentication + RLS**: 14 dashboard-public tables have RLS enabled with `public_read FOR SELECT TO anon, authenticated USING (true)`, anon grants reduced to SELECT-only (commit `1d61257`, 2026-05-06). New tables ship with the same pattern by default.

## Working with canonical documentation files

Several Markdown files in `docs/` are **point-in-time append-only logs**, not regenerable narratives. Treat them as you would a database journal: read, find the right anchor, str_replace additively. Never overwrite with a regenerated version — past sessions have lost 200+ lines twice when this rule was broken.

Canonical docs (full rules in `docs/WORKING_PROTOCOL.md`):

| File | Convention |
|---|---|
| `docs/STATE.md` | Project status snapshot. Additive per Áfangi |
| `docs/DECISIONS.md` | Locked architectural decisions. **Newest entries at top**, dated |
| `docs/PLANNING_BACKLOG.md` | Future planning prompts. Append at end |
| `docs/SOURCES_OF_TRUTH.md` | Canonical data-source contracts (2026-05-20) |
| `docs/TAXONOMY.md`, `GLOSSARY.md`, `DATA_SCHEMA.md` | Reference. Edit narrowly |
| `docs/SCRAPER_SPEC_v1.md`, `DASHBOARD_SPEC_v1.md` | Implementation specs |
| `docs/EXTRACTION_SCHEMA_v0_2_2.md`, `LABELING_GUIDE.md`, `GOLD_STANDARD_PROTOCOL.md` | LLM extraction work |
| `docs/DATA_AUDIT_REPORT.md` | Point-in-time snapshot; immutable. New audits get new filename with date suffix |

**Discipline per edit**: read the current file → verify the anchor exists → str_replace → confirm `wc -l` (or git diff) shows growth, not shrinkage. The PowerShell `Measure-Object -Line` and Unix `wc -l` can disagree on Windows due to line-ending counting — `git diff --stat` is the authoritative additive check.

## Operational scripts

**Backups**: `scripts/backup_nightly.py` runs nightly at 03:00 local via Task Scheduler (`verdmat-nightly-backup`, user-level). Uses rclone sync + `--backup-dir`: `r2backup:verdmat-backups/current/` is the live mirror; `archive/<ts>/` holds overwritten versions; 30-day retention prunes `archive/` only. `D:\Gagnapakkar\images\` (352 GB CloudFront-mirrored) is intentionally excluded. To upgrade the scheduled task to wake-from-sleep + run-when-logged-out, re-run `scripts/register_backup_task.ps1` from an elevated PowerShell.

**Phase D Supabase sync**: `scripts/phase_d1_*.py` is a three-script (extract → dryrun → apply) pattern with an explicit halt point between dryrun and apply. The pattern is intentional — every future bulk-write to Supabase should follow the same shape (idempotent script + rollback SQL + sample-size pre-check). Phase D1 (124,738 HMS enrichments) and D2 (97 ghost soft-flag) are done; D3 (30K new-property insertion), D4 (cross_property_refs), D5 (photo_urls_json) are pending and will reuse this pattern.

## Notable environment quirks (lessons learned)

- **Next.js 16 + Turbopack**: bundling Tailwind v4 import in `globals.css` breaks (Turbopack treats postcss as client code). Use plain CSS vars in `globals.css`; skip the Tailwind import. See `feedback_nextjs16_turbopack` in user-level memory.
- **Windows Update auto-restart killed scrapes twice** before the WU pause recipe was found. Before launching anything multi-hour, pause Windows Updates via elevated registry write under `HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings` (max 35 days). AC sleep/hibernate are already disabled on this machine; WU is the separate risk.
- **Long scrapes via curl_cffi**: hms.is sits behind Cloudflare WAF — plain `aiohttp` / `requests` / `Invoke-WebRequest` get 429'd. Use `curl_cffi` with `impersonate="chrome120"` for any HMS API call. The "property does not exist" signal is **HTTP 500 `{"error":"Internal server error"}`**, not 404 — treat 500 as terminal, not retryable.
- **Supabase pooler**: direct `db.<ref>.supabase.co:5432` is IPv6-only. External scripts must use the transaction-pooler URI on port 6543 (already in `.dbconfig`).

## Current status — read the journals, not this file

Don't keep dated phase/status here; it drifts. For current áfangastaða, open items, and next steps, read **docs/STATE.md** + the top of **docs/DECISIONS.md** at the start of every session. The authoritative copy is the working tree on disk — the Project Knowledge panel and raw.githubusercontent.com are both stale.

## Scraper substream · semantic layer · expert agent (built after this file's original draft)

Map only; canonical detail in the noted docs.

- **Multi-source listing scraper** → `scraper.listings_canonical` (one row per canonical_id; re-lists in secondary_source_ids[]). Sources: mbl (nightly delta, Task Scheduler 01:00), visir + myigloo (seed only, no ongoing refresh yet). Locked scraper rules (pooler read-only, distrust index-endpoint labels, visir HTTP 400 soft-throttle, cross-source dedup R1–R3) live in docs/DECISIONS.md.
- **Semantic layer** → `semantic` schema: 13 materialized views (street / postnr / matsvaedi / sveitarfelag prices, newbuild_share, hood_heat, price_distribution, model_vs_sold, summerhouse, sveitarfelag_lookup) reading from public.sales_history, plus one internal `_sales_base` view that agents must NEVER query directly. Spec: docs/specs/T5_SEMANTIC_VIEWS_v1.md.
- **v0 expert agent** → market-analytics agent (Claude + read-only Supabase MCP + SKILL). Answers aggregate questions from semantic.* only; does not value individual properties, forecast, or advise. Operating doc: docs/specs/SKILL_v0.md; design: docs/specs/AGENT_SPEC_v1.md.

## Locked operational rules (recur every session)

- **Supabase writes** via psycopg2 on the transaction pooler (port 6543) default read-only — the first statement of every write transaction must be `SET TRANSACTION READ WRITE`. SQL migrations go through the Supabase MCP `apply_migration` (CLI is blocked by Windows Smart App Control).
- **Task Scheduler**: S4U logon type (password principal fails silently).
- **Docs discipline**: additive str_replace only on the journal files (STATE / DECISIONS / PLANNING_BACKLOG), verify wc -l grows, never regenerate from memory. Git: always explicit paths, never `git add .`. HALT at decision points before consequential actions. Commits carry a Co-Authored-By trailer naming the actual session model. Secrets stay in terminal + .env.

## Launching a session

This file auto-loads only when Claude Code starts with cwd inside `D:\verdmat-is\app`. Start sessions from there (`cd verdmat-is\app` before `claude`) so the orientation loads.
