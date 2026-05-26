# kaupskra.csv staleness check (30-second diagnostic)

**Date**: 2026-05-07
**Trigger**: `scrape_gap_diagnostic_report.md` flagged "stale kaupskra.csv enumeration source" as the most insidious candidate root cause for the 9,000→600/mo listings-volume drop.
**Verdict**: **Hypothesis rejected.** kaupskra.csv is fresh; staleness is not the gap origin. A different operational mechanism is at play.

---

## File inventory

```
D:\kaupskra.csv                                                              46,272,849 b   2026-04-20 09:30  ← canonical, refresh_kaupskra.py output
D:\kaupskra_prev.csv                                                         46,272,642 b   2026-04-20 00:19  ← prior-run snapshot from refresh
D:\Backup v1\kaupskra.csv                                                    46,272,170 b   2026-04-18 10:31
D:\Vinnugögn\Annað\Scrape - skjöl - skipanir\Scrape - stora\kaupskra (1).csv 46,212,122 b   2026-04-10 14:34  ← scraper dir copy
D:\Vinnugögn\Greiningar\Tapshlutfall\kaupskra.csv                            46,156,673 b   2026-04-07 16:00
```

The scraper-dir copy (`kaupskra (1).csv`) was last touched **2026-04-10** — well after mid-2025. The canonical `D:\kaupskra.csv` matches the DECISIONS-recorded refresh date (2026-04-20). Áfangi 4d's `refresh_kaupskra.py` is still running fine.

## Scraper output DB inventory (`D:\Gagnapakkar\fasteignir*.db`)

```
fasteignir.db        362 MB   2026-04-16 11:11    main DB last written
fasteignir1.db       719 MB   2026-04-16 11:17
fasteignir2.db        20 MB   2026-04-16 13:13
fasteignir3.db      1614 MB   2026-04-16 11:17
fasteignir4.db       294 MB   2026-04-16 11:11
*.db-shm                      2026-04-20 23:00    bookkeeping access (read-only open at 23:00)
*.db-wal           0 b each   2026-04-20 23:00
```

The DB files themselves were last written **2026-04-16** — under three weeks ago. The -shm/-wal pair was touched 2026-04-20 23:00 (a parser/reader script opened them, no actual writes since). Output side is also fresh.

## Reframed root cause

Both the source-list (kaupskra.csv) AND the output DB (fasteignir.db) are recently touched. The original "scraper stopped running mid-2025" framing is too coarse — something **is** still happening, just at a much lower throughput.

The structural mechanism that fits the evidence: `scraper.py` and its variants implement **resume-safe skip via `status='ok'`** at line 140-143:

```python
row = conn.execute("SELECT status FROM fasteignir WHERE fastnum=?", (fastnum,)).fetchone()
if row and row[0] == "ok":
    print(f"  ⏭ {fastnum} already scraped, skipping")
    return True
```

Once a fastnum is captured with status='ok', it is **never re-visited.** This means:

- New fastnums entering kaupskra.csv get scraped fresh (their first appearance) ✓
- New listings on already-scraped fastnums **never make it into the DB** ✗

The 124,835 existing rows each got their `augl_json` snapshot at the moment of *first* scrape. If a property has been re-listed since (e.g., Laugavegur 39 with 2026-05-05 + 2026-04-17 listings on top of an older 2024-11-13 baseline), only the original listing(s) ever appeared in the local DB. The recurring scrape's downward-throughput trend is the natural decay of "how many genuinely-new fastnums HMS publishes per month" — which is the new-issuance rate of fastnums (50–200/mo per `SCRAPER_SPEC v1.1` §7.4), NOT the new-listings rate of all properties.

**This shifts the listings-currency gap from "fix the recurring scraper" to "the recurring scraper is doing what it was designed to do; the design itself doesn't cover listings refresh."**

## Implications for next-session architecture decisions

1. **The previous `~48 h augl-only re-scrape` recommendation is now structurally necessary, not optional.** Without it, every existing fastnum's listings stay frozen at first-scrape-time forever.
2. **The recurring scrape design needs a separate refresh-loop:** alongside the new-fastnum loop (driven by kaupskra.csv), a periodic re-scrape loop that revisits already-scraped fastnums on some cadence. Probably weekly or monthly for the most-active properties, less often for never-listed ones.
3. **A simpler short-term path:** drop the `status='ok'` skip on `get_fasteign_augl` specifically. The augl call is cheap, the data turns over frequently — refresh on every visit. Keep the skip on `get_fasteign_data` and `get_fasteign_kaups` where data is stable. Two-tier resume policy.
4. **Image-archive bootstrap pairs naturally with (1) or (3).** Each fresh augl call exposes new CloudFront URLs that need archiving. Single multi-night sweep does both.

These are next-session decisions. **No fixes applied this session.**

## Artifacts

- `audit/kaupskra_staleness_check.md` — this document.

No DB writes, no commits, no scaling action.
