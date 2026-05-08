# Image storage policy — Áfangi 0.y Amendment 4 implementation

**Status**: implemented in `audit/backfill_evalue_range.py` 2026-05-07 for the Stage 1 pilot v3 (phases 2-4). Full policy lock for production scrape pending the multi-night `augl`-refresh sweep.
**Reference**: `docs/PLANNING_BACKLOG.md` Áfangi 0.y Amendment 4.

---

## Layout

```
D:\Gagnapakkar\images\
├── 2526172\
│   ├── j7vzd7Pw.jpg
│   ├── LvOkFbGj.jpg
│   └── ...
├── 2541716\
│   └── ...
└── 2004765\
    ├── j7vzd7Pw.jpg          ← from ad #0 (2026-05-05)
    ├── gZQ69QL7.jpg          ← from ad #1 (2026-04-17)
    └── ...
```

**One folder per fastnum, flat file list inside.** No per-ad subdirectories. Filename is the basename of the CloudFront URL exactly as evalue.is serves it (e.g. `j7vzd7Pw.jpg`). The basename is already content-addressable enough — CloudFront's URL paths are stable identifiers and dedupe naturally across re-scrapes (same URL → same filename → idempotent skip on disk).

## Dedupe across ads

A single property's augl payload may carry multiple ads (Laugavegur 39 has 3, with 25 + 5 + 0 images). The pilot scraper extracts URLs across ALL ads, dedupes by URL, and writes once per unique basename. If the same image URL appears in two ads, it lives at one path. This is conservative: photos are sometimes reused across re-listings.

**Rationale for whole-payload (not first-ad-only)** dedupe: the legacy scraper extracted from `first ad` only. That captured the freshest set but lost historical photos when an ad rotated out. The Amendment 4 mandate is *long-term archive*, so we capture every URL the augl payload references at the moment of scrape.

## Idempotency

`download_image()` checks `dest.exists()` before fetching. A re-run skips already-downloaded files at near-zero cost (one `os.stat` per image) and only network-fetches new URLs. This makes the multi-night sweep restartable.

`tmp = dest.with_suffix(".jpg.partial"); tmp.write_bytes(body); tmp.replace(dest)` — atomic rename pattern. An interrupted download leaves a `.partial` file, never a half-written `.jpg`. Subsequent runs see the missing target and re-download cleanly. (`.partial` files can be safely deleted in cleanup; they are not part of the archive.)

## Failure handling

A single image 404 / 5xx / timeout logs WARN and continues. **It does not abort the property scrape.** CloudFront URLs can rot independently of registry data — an old listing might reference a photo that was later purged, but the registry-data still needs to be captured.

Cloudflare/anti-bot interception by **evalue.is** still hard-halts (per locked plan). Cloudflare/anti-bot interception by **CloudFront** is treated as a per-image WARN, because CloudFront serves images directly and is not on the same anti-bot perimeter as evalue.is's API endpoint. (If the WARN volume becomes a deluge of `http-403`, that's a signal to revisit; pilot data will tell us.)

## Throttle posture

- Inter-request delay: 0.5 s between consecutive image GETs to the same property's CloudFront folder. Less aggressive than evalue.is's 1 s because CloudFront is a CDN designed for fan-out, not a small Icelandic API server.
- No parallelism within a property's image set in the pilot. Future: could parallelize 4-way (CloudFront tolerates it), but pilot keeps serial for simplicity and ease of halt.

## Scope of pilot v3 image archive

**Pilot v3 (phases 2-4)** writes images for:
- 5 phase-2 positive controls (re-scrape of properties already in Supabase) — expected ~50-200 MB total based on positive-control averages from pilot v1
- ~100 phase-3 trailing-range hits (most have `n_ads=0` so few images) — expected <500 MB
- 0-few phase-4 sub-gap hits — expected <100 MB
- **Pilot v3 total disk hit: <1 GB**

This is intentionally small. The full multi-night `augl`-refresh sweep (separate session, post-mapping-shim) will be the storage-bootstrapping moment for the 124,835 existing fastnums plus newly-found rows.

## Production scope — projected (for next session's lock)

- Existing 124,835 fastnums × ~40% with ≥1 ad × ~30 imgs avg × ~150 KB = **~225 GB** archive size, midpoint estimate. Can vary 100-500 GB depending on the actual ad-having distribution and image size distribution.
- The next session's full-scope decision should compute this properly using pilot v3 hit-distribution data; the multiplier (0.4 × 30 × 150 KB) is a placeholder, NOT a measured statistic.

**Open questions for next session's policy lock:**
1. Compression: store JPEG-as-served (largest, most fidelity) or recompress to constant quality? Recommendation: store as-served for the archive; do downstream compression only for serving.
2. Retention: forever, or rolling N-year? Recommendation: forever (storage is cheap; legal retention requirements may apply for valuation/transactions).
3. Backup strategy: one local copy on `D:\` only, or replicate to cloud / external drive? Out of scope for Stage 1; flagged for Áfangi 0.z (operational hygiene) backlog.
4. Should the recurring scrape (post-Stage-1) re-download *all* images on each visit, or only newly-seen URLs? The idempotency design (skip-if-exists) makes both cheap; net-new is the natural behavior.

These remain open. The pilot v3 implementation answers (1) JPEG-as-served, (2) keep, (3) local-only on `D:\`, and is silent on (4) because pilot is one-off, not recurring.
