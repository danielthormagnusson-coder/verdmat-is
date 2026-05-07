# Áfangi 0 Stage 1 — backfill pilot plan (revised)

**Date**: 2026-05-07
**Status**: drafted, awaiting Danni go-ahead before pilot batch
**Path locked**: A (evalue.is) — Path B (HMS direct API) failed empirical probe today (HMS retired `/api/fasteignaskra/{fastnum}` during their April-May 2026 rebuild to Next.js + Vercel + Prismic stack; all 5 known-good fastnums returned 404 against the documented endpoint)
**Prior pre-flight**: `audit/backfill_preflight_report.md` (now partially obsolete — superseded by template-discovery findings of 2026-05-07)

---

## What we have to work with

Five evalue.is scraper variants in `D:\Vinnugögn\Annað\Scrape - skjöl - skipanir\Scrape - stora\`, all sharing an identical scraping core (POST to `https://www.evalue.is/fastnum/{fastnum}?/{action}` with three actions: `get_fasteign_data`, `get_fasteign_kaups`, `get_fasteign_augl`; SQLite output to `fasteignir.db` matching the schema that produced the legacy `D:\Gagnapakkar\fasteignir*.db` files; resume-safe via `status='ok'` skip; image download to `myndir/{fastnum}/N.jpg`). The variants differ **only in how they enumerate fastnums to scrape** — i.e., the range-walking strategy. Every one of them keys off `kaupskra.csv` as the source list of fastnums.

| Variant | Strategy | Source list | Use case |
|---|---|---|---|
| `scraper.py` | Forward walk from start | `kaupskra.csv`, ascending, limit N | Initial bulk run from low fastnums up |
| `scraper_middle.py` | Forward walk from given start | `kaupskra.csv` filtered `>= 2088385`, ascending | Resume where `scraper.py` stopped |
| `scraper_reverse.py` | Reverse walk from highest | `kaupskra.csv`, descending, limit N | Catch newest issuances (top-down sweep) |
| `scraper_reverse2.py` | Reverse walk from given start | `kaupskra.csv` filtered `<= 2294894`, descending | Resume reverse pass at known-stop |
| `scraper_gap.py` | Fill specific gap range (2x speed) | `kaupskra.csv` filtered `2294894 < fn < 2298494` | Fill known holes between completed sweeps |

The naming + parameters tell the operational story: Danni did a forward sweep to ~2088385, a reverse sweep down to ~2294894, a middle sweep from 2088385 onward, a reverse sweep from 2294894 down, and gap-fills for specific holes between completed ranges. That gave us the existing 124,835 rows.

**Critical limitation for our gap-fill problem**: every variant keys off `kaupskra.csv` as its fastnum source. `kaupskra.csv` lists kaupskrá-records — properties that have been sold and recorded in the public deeds registry. The ~25K missing fastnums in our `properties` table are by definition **properties that have NOT appeared in kaupskrá** (else they would already be there). So the existing variants cannot solve our gap-fill problem on their existing source-list logic. We need a variant that walks the integer fastnum space directly, not driven by kaupskra.csv.

The good news: that's a small change — replace the `load_fastnum_list_*` function with a `range(start, end+1)` generator. Everything else (POST mechanics, retry, SQLite schema, image extraction, resume logic) stays exactly as Danni already built it.

---

## Empirical gap analysis — Supabase `properties` distribution

Live query against production Supabase (2026-05-07):

```
MIN(fastnum)  = 2,000,044
MAX(fastnum)  = 2,541,714
total rows   = 124,835
range span   = 541,670 integers
density      = 124,835 / 541,670  = 23.0% of integer space populated
```

Per-100K-bucket breakdown:

| Bucket | Rows | Range observed |
|---|---:|---|
| 2,000,000 – 2,099,999 | 43,837 | 2,000,044 – 2,096,697 |
| 2,100,000 – 2,199,999 | 18,228 | 2,100,005 – 2,199,998 |
| 2,200,000 – 2,299,999 | 28,897 | 2,200,002 – 2,299,998 |
| 2,300,000 – 2,399,999 | 16,198 | 2,300,000 – **2,377,983** (suspiciously low max for this bucket) |
| **2,400,000 – 2,499,999** | **0** | **TOTAL ABSENCE — likely a huge piece of the missing 25K** |
| 2,500,000 – 2,599,999 | 17,675 | 2,500,015 – 2,541,714 |

Two empirically-grounded targets for the backfill:

1. **The 2,400,000 – 2,499,999 bucket**, currently zero rows. Either HMS literally does not use this range (unlikely — bracketed by populated 2,300K and 2,500K buckets), or Danni's prior sweep skipped it entirely. The latter is overwhelmingly more likely. If this bucket is normal-density (~20K-30K like its neighbors), it accounts for most or all of the missing 25K by itself.

2. **The 2,541,715+ trailing range** — fastnums issued by HMS since Danni's last sweep MAX (likely up through 2026-05-07 issuances). Magnitude unknown; probably small (50-200/month per `SCRAPER_SPEC_v1.md` §7.4), which over the 2-3 months since the last scrape is maybe 200-600 rows.

There is also probable sparse-gap content within the populated buckets — e.g., `2,300,000 – 2,399,999` shows a max of `2,377,983` despite the bucket extending to `2,399,999`, suggesting another sub-gap in `2,378,000 – 2,399,999`. Worth checking after the 2.4M sweep is complete; could be another 5K-10K rows.

### Implication for pilot strategy

A 100-row pilot batch should be a **slice of the 2,400,000 bucket** specifically. That tests three things at once: (a) does evalue.is still respond to fastnums in this range with a working API, (b) is the bucket actually populated (do we get hits, not 404s), (c) does the schema we receive match what `parse_all_dbs.py` and the existing `properties` table expect.

Suggested pilot range: `2,450,000 – 2,450,099` (mid-bucket, 100 sequential candidates). Conservative throttle (1 second between properties, matching Danni's existing variant defaults) puts pilot at ~5 minutes of activity. Resume-safe via the `status='ok'` skip on the SQLite side, plus we'd guard against re-INSERT into Supabase via `ON CONFLICT (fastnum) DO UPDATE WHERE hash differs`.

---

## Proposed Pilot Batch (Stage 1, 105 rows total)

The pilot has six sequential steps. The first two are pre-checks — they exist because of today's HMS-API failure mode (verified-in-April code that broke by May). The same Bug-24 pattern could apply to evalue.is and we should not assume the legacy scrape pattern still works without an empirical probe first.

**Step 1 — Empirical-first probe with positive controls.** 5 known-good fastnums **drawn from the populated tail of the existing properties table** (selector: `SELECT fastnum FROM properties WHERE fastnum BETWEEN 2500015 AND 2541714 ORDER BY random() LIMIT 5`). Run these first via the existing `scraper.py` POST mechanic (`get_fasteign_data` only, single action per probe). Verify response is JSON (not HTML), schema matches expected (`status: 200`, payload includes `heimilisfang`/`einflm`/`fasteignamat` etc.), no Cloudflare challenge intercept.

Why positive controls drawn from existing data, not random known fastnums: removes ambiguity if the suspected-missing 2.4M range comes back empty. With known-good positive controls confirming the scraper works, an empty 2.4M result distinguishes "scraper still works, range really empty" from "scraper dead, all results meaningless". Same Bug-24 prudence pattern applied to the empirical probe itself.

Ship-stopper: if any positive-control fastnum returns HTML or 403, evalue.is has rebuilt and we need a fresh discovery round before continuing. **Cloudflare-challenge contingency: halt + report only. No retry.** Retry-with-delay trains anti-bot detection toward our request signature, which actively makes future runs harder. If a challenge is encountered, escalate to backlog: UA rotation, residential proxy, or pivot back to HMS dialogue clean-path. Estimated time for Step 1: ~12 seconds (5 fastnums × 2s courtesy delay).

**Step 2 — Adapt one scraper variant to walk the integer space.** Take `scraper.py` as base, replace the `load_fastnum_list` function with `range(START, END+1)`. Keep everything else identical: same POST mechanic, same SQLite output, same resume logic. Output as `audit/backfill_evalue_range.py` (working buffer) — DOES NOT replace any existing template, it's a sixth variant.

**Step 3 — Run pilot on `2,450,000 – 2,450,099`.** 100 fastnums, ~5 minutes wall-clock at 1-second delay. SQLite output to local `audit/backfill_pilot.db`. Capture: hit-rate (X / 100 returned property data, Y / 100 returned not_found), per-row schema sanity, any rate-limit signals or Cloudflare challenges. Same Cloudflare-challenge halt rule as Step 1.

**Step 4 — Quality check on pilot output.** Manual review of 10 sample rows: do the fields populate correctly, does `kaups_json` look complete, are images extractable, does `heimilisfang` look real, does `fasteignamat` look like a reasonable Icelandic-króna value (not zero, not absurdly large). Compare against existing rows in Supabase `properties` for the same field set to confirm shape compatibility.

**Step 5 — Two-phase architecture: pilot validates via SQLite, full backfill writes direct to Supabase.** Pilot uses the existing-pipeline path for safety: SQLite output → `parse_all_dbs.py` (or equivalent for the 105-row subset) → schema validation against `properties` columns. Once pilot passes, write a 1-2 hour mapping shim that converts `data_json` directly to `properties` row format, bypassing the SQLite intermediate for the full backfill. Mapping shim built **after** pilot validates the schema, not before — pilot is the schema discovery surface that drives mapping-shim contracts.

Architecture: pilot SQLite + `parse_all_dbs.py` integration validates that fields-as-scraped match fields-as-expected. Mapping shim then encodes that validated transformation in a direct path. Two-phase split minimizes greenfield code — pilot leans on existing-and-trusted pipeline, full backfill graduates to direct path with empirical schema confidence behind it.

**Step 6 — Pilot report.** `audit/backfill_pilot_report.md` with hit-rate, schema validation, mapping-shim contract, projection for full-bucket sweep. PAUSE for Danni go-ahead before scaling to full 100K-candidate sweep of bucket 2.4M.

### What the full backfill looks like (if pilot passes)

Walk `2,400,000 – 2,499,999` at 1 req/second = 100,000 seconds = ~28 hours of activity, spread over 2-3 nights at ~10-12 hours/night. Resume-safe via `status='ok'` SQLite check, so multi-night staging is operationally trivial. Expected hit-rate: somewhere in the 15-30K range based on neighboring-bucket density (assuming this bucket isn't an anomaly).

After 2.4M sweep: spot-check the `2,378,000 – 2,399,999` sub-gap (22K candidates at 1 req/sec = ~6 hours, expected hit-rate 5-10K). Then the trailing `2,541,715 – {discovered_max}` range. Total Stage 1 work: ~3-4 nights wall-clock for the full 25K backfill, conservatively.

---

## Operating constraints (from prior pre-flight + today's empirical context)

**evalue.is robots.txt is `Disallow: /` for non-search-engine UAs.** Danni's existing scraper has been operating across this directive successfully — 124,835 rows is the proof. The empirical posture is "works at 1 req/sec with Mozilla UA". I'm not going to re-litigate the ethics of that decision in this plan; it's Danni's call and the call was made when the existing rows were scraped. The pilot operates under the same posture as the variants that produced the existing rows.

**Cloudflare bot management may have tightened.** evalue.is fronts on Cloudflare per the pre-flight headers. Their bot-management settings could have changed since Danni's last successful run. Step 1 of the pilot specifically tests this — if the 5-fastnum probe encounters Cloudflare interactive challenges or 403s, we halt before scaling.

**No parallelization within the pilot.** The variants run serially (1 req/sec); the pilot keeps that posture. Parallelism is a v1.1 consideration, contingent on rate-limit-reality probing once pilot proves the basic posture works.

---

## What this plan does NOT do

It does not commit to scraping `kaups_json` or `augl_json` for the missing 25K. The `get_fasteign_kaups` action is irrelevant for never-sold properties (no kaupskrá history exists), and `get_fasteign_augl` (listings/images) is also typically empty for properties that have never been listed. The pilot run uses `get_fasteign_data` only, which is the registry-data action and the only one needed for the registry-completion goal. Saves 67% of HTTP traffic per fastnum compared to the full triple-action variant calls.

It does not address `kaupskra.csv` re-fetch. The variants reference `kaupskra.csv` from a Danni-local file, presumably from his customer access at HMS or another source. For our gap-fill the integer-space walk replaces that source list entirely; we don't need a fresh `kaupskra.csv`.

It does not address Track A (active listings) or any other Áfangi 0 work-stream. Stage 1 is registry-completion only; Track A is Stage 3+ per the original `SCRAPER_SPEC_v1.md` §8.2 build order.

---

## Decisions locked (Danni go-ahead 2026-05-07)

1. **Pilot range**: 5 positive-control fastnums (random sample from existing `properties` 2,500,015 – 2,541,714 range) + 100 candidates from `2,450,000 – 2,450,099`. Total 105 rows.
2. **Cloudflare contingency**: halt + report only. No retry. Retry-with-delay trains anti-bot detection. If hit, escalate to backlog (UA rotation, residential proxy, or pivot back to HMS dialogue clean-path).
3. **Two-phase architecture**: pilot via SQLite + `parse_all_dbs.py` for safety + schema discovery; full backfill via 1-2 hour mapping shim writing direct to Supabase.

## Execution timing

Pilot batch held until **separate go-ahead** post-commit. This commit ships the deliverables to GitHub for Danni's review (HMS email may need tone edit, contact-line replacement, etc.) before scheduled pilot run. No autonomous pilot execution.
