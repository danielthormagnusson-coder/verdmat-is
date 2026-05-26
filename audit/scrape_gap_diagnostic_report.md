# Áfangi 0 Stage 1 — listings-volume gap diagnostic

**Date**: 2026-05-07
**Trigger**: existing scraped-DB shows listings volume dropped from ~9,000/month (mid-2025) to ~600/month (post-mid-2025). Two competing hypotheses to disambiguate.
**Method**: re-scrape one fastnum with empirically-known recent listings (per Danni's 2026-05-07 evalue.is screenshot of Laugavegur 39 / fastnum 2004765 showing listings dated 2026-05-05, 2026-04-17, 2024-11-13). Cross-check against pilot-DB augl payloads.
**Output DB**: `audit/scrape_gap_diagnostic.db` (1 row, separate from `backfill_pilot.db` per task spec).
**Status**: diagnostic complete. **PAUSED** for Danni review. No commits, no scaling action.

---

## Verdict — **Hypothesis B (operational) confirmed**

**The existing scraper format still captures recent listings correctly.** The gap is operational, not data-path.

### Direct evidence — Laugavegur 39 (fastnum 2004765), freshly scraped 2026-05-07T14:14 UTC

`augl_json` decoded to **3 ads** (matches the screenshot's 3 listings exactly). Listing dates extracted from the inner array, slot 6 of each ad (`thinglystdags` per the schema map):

| Ad # | Slot offset | Address | Date captured |
|---|---|---|---|
| 0 | flat[6] | Laugavegur 39 | **2026-05-05T12:38:54.852624** |
| 1 | flat[102] | Laugavegur 11 | **2026-04-17T15:05:51.685842** |
| 2 | flat[124] | Laugavegur Þrjár íbúðir 28 | 2024-11-13T09:22:59.033 |

**All three Danni-screenshot dates appear verbatim in the freshly-scraped payload.** The two post-mid-2025 listings (2026-04-17, 2026-05-05) are present. Image-URL slots populated correctly (CloudFront URLs at `d1u57vh96em4i1.cloudfront.net/2004765/*.jpg`). Schema map identical to the canonical 16-position layout. No format anomaly.

The dates were initially missed by a naive regex (`\b\d{4}-\d{2}-\d{2}\b`) because they're ISO-8601 with a `T<time>` suffix, not bare dates. That was a measurement artifact in my first scan, not a data anomaly — the dates have been there in the payload all along.

### Cross-check — pilot DB positive controls (re-scraped 2026-05-07T12:18 UTC)

| fastnum | n_ads | most recent listing | interpretation |
|---|---|---|---|
| 2503270 | 0 | — | property never listed via evalue.is |
| 2506715 | 0 | — | property never listed |
| 2512191 | 10 | 2023-01-23 | last on market early-2023, dormant since |
| 2526172 | 2 | 2025-02-24 | last on market early-2025, dormant since |
| 2528893 | 0 | — | property never listed |

None of the positive controls had post-mid-2025 listings. **This is consistent with Hypothesis B**, not against it: the 5 controls are random-sampled from the 2,500,015–2,541,714 range (very low transaction velocity Icelandic regional / outer-suburb stock), and a property must actually be re-listed for a new ad to appear. Properties without recent activity correctly show no recent ads. Laugavegur 39 is a downtown Reykjavík asset with frequent listing activity — hence it carries the post-mid-2025 ads. The format faithfully captures both states.

### What we are NOT seeing (the smoking gun for B)

If Hypothesis A (data-path break) were true, we'd expect:
- Laugavegur 39's recent listings to be missing from the freshly-scraped payload, or
- The schema map to have new fields we don't capture, or
- A post-mid-2025 cutoff in any active-listings property's augl regardless of how active it is.

**None of these hold.** The format captures Laugavegur 39's full 3-ad history including ads from yesterday-equivalent (2026-05-05). Schema is unchanged from the original positive-control pattern. Image URLs intact.

---

## Implications — what changed mid-2025 was the run cadence, not the data

The ~9,000/month → ~600/month drop reflects the scraper running less often (or partially) post-mid-2025. The most natural interpretations:

1. **The recurring scrape job slowed or stopped mid-2025** and only sporadic runs since (gap-fills, partial sweeps) have produced the trickle of ~600/month. Whoever owns the cron / manual-run cadence (Danni's local environment) drifted off.
2. **The fastnum-enumeration source went stale.** All five existing variants enumerate from `kaupskra.csv`. If the local copy of `kaupskra.csv` hasn't been refreshed since mid-2025, the recurring scraper would only see fastnums that appeared in the kaupskrá pre-mid-2025, missing all post-mid-2025-newly-sold properties (which would have appeared in a fresh kaupskrá but not in the stale local copy). This would *also* miss new listings on previously-listed properties, because the variant only re-visits fastnums that appear in the source list. Even fastnums Danni already has rows for would not get refreshed if they weren't in the latest kaupskrá window the script reads.
3. **Combination**: cadence dropped AND source list went stale.

(2) is the most insidious. The scraper might appear to "still be running" but only against a frozen view of the world. To distinguish: check the modification time of the local `kaupskra.csv`. If it's older than mid-2025, that's the proximate cause of the trickle — fresh listings on already-known fastnums never got picked up.

---

## Strategic implications for Stage 1 scope

The previous Stage 1 plan was framed as: *fill the registry-completion gap (the ~25K missing fastnums)*. Today's diagnostic adds a second, distinct gap: **post-mid-2025 listings on already-known fastnums**.

These are structurally different problems with different scaling shapes:

| Gap | Source | Volume | Action |
|---|---|---|---|
| Registry-completion | the ~25K fastnums missing from `properties` | trailing range walk (`2,541,715+`) + `2,378,000–2,399,999` sub-gap probe | per pilot v2 plan |
| Listings-currency | already-known fastnums whose last `augl` snapshot is pre-mid-2025 | unknown — but a re-scrape of all 124,835 existing rows would refresh all of them at known cost | NEW Stage-1 work-item |

Scaling cost for the listings-currency gap, single-action (`get_fasteign_augl` only):

- 124,835 fastnums × ~1.4 s (1 action + 1 s delay) = ~48 h
- = ~2 nights at full throttle, or 4-5 nights at half-night cadence

The image-download policy from PLANNING_BACKLOG.md Áfangi 0.y Amendment 4 hooks directly into this re-scrape: every fresh `augl` capture is the moment to download newly-extracted CloudFront URLs to `D:\Gagnapakkar\images\`. The two pieces of work compound: a single 48 h `augl` re-scrape covers both the listings-currency backfill and the image-archive bootstrap.

**Recommended priority re-ordering**:

1. **First**: lock the image-ownership policy + storage convention (next session, was already on the plan).
2. **Second**: 5K trailing-range walk (registry-completion edge, expected ~100 new rows).
3. **Third**: full `augl` re-scrape of the 124,835 existing fastnums **with image downloads** to `D:\Gagnapakkar\images\` simultaneously. ~48 h wall-clock, multi-night staging. Closes the listings-currency gap and bootstraps the image archive in one pass.
4. **Fourth**: `2,378,000–2,399,999` sub-gap probe + conditional sweep (registry-completion volume).
5. **Fifth onward**: intra-bucket sparse-gap audit, recurring scrape setup.

Skip 2.4M sweep entirely (per pilot v2).

This re-orders the trailing-range walk above the `augl` re-scrape because the trailing walk is short (~85 min) and produces immediate testable data for the mapping shim's Phase-2 implementation. The big multi-night `augl` re-scrape comes after the image-policy is locked and the trailing range is in.

---

## Out-of-scope (next session candidates)

- **Verifying the (2) hypothesis** — check `kaupskra.csv` mtime in `D:\Vinnugögn\Annað\Scrape - skjöl - skipanir\Scrape - stora\` and similar dirs. ~30 seconds of local work; not appropriate to mix into this diagnostic.
- **Setting up a recurring scrape** — separate engineering session per `SCRAPER_SPEC v1` §2 cadence design. Requires a fresh `kaupskra.csv` source decision (HMS dialogue outcome dependent) and a host (cron on Windows, scheduled task, or hosted runner).
- **Building the actual `augl` re-scrape variant** — minor adaptation of `backfill_evalue_range.py` to (a) take a fastnum-list source (already supported via the import pattern in `backfill_evalue_probes.py`), (b) skip `get_fasteign_data`/`get_fasteign_kaups` actions (single-action mode), (c) integrate image-download per locked policy. ~1-2 h once the image policy is locked.

---

## Artifacts on disk

- `audit/scrape_gap_diagnostic.db` — 1 row (fastnum 2004765 freshly scraped)
- `audit/scrape_gap_diagnostic.py` — diagnostic runner (importing from `backfill_evalue_range`)
- `audit/scrape_gap_diagnostic_report.md` — this document

No commits. No Supabase writes. No scaling actions. **Paused for Danni review.**
