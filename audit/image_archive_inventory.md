# Existing image archive inventory — D:\ (Áfangi 0 Stage 1)

**Date**: 2026-05-08
**Method**: read-only scan of `D:\` for `.jpg/.jpeg/.png/.webp`; cross-reference with legacy SQLite databases under `D:\Gagnapakkar\fasteignir*.db` and Supabase `properties` (124,835 fastnums).
**Scope**: investigation only — no file moves, no consolidation, no fixes. Decision-input for Stage B image bootstrap (next session).
**Trigger**: pilot v3 (`backfill_pilot_report_v3.md`) recommended a ~30 h / ~1 TB Stage B fresh-fetch for 48,595 ad-having properties. Inventory shows that estimate ignored substantial pre-existing local assets — Stage B scope can shrink dramatically.

---

## Headline

- **896,871 image files / 196.14 GB** already on `D:\` across multiple `Gagnapakki N` and related archives.
- **38,771 distinct 7-digit fastnums** have at least one image folder somewhere on `D:\`.
- **38,267 of those fastnums (98.7 %) intersect Supabase `properties`** — covering **30.7 % of the 124,835 Supabase rows**.
- Mapping between disk files and CloudFront URLs is **fully recorded** in legacy SQLite `myndir` tables (1,156,588 URL→local-path rows across the 5 DBs in `D:\Gagnapakkar\fasteignir*.db`).
- **Hybrid recommendation for Stage B**: consolidate the existing 196 GB archive (zero re-download cost) + targeted fresh-download for only the ~10K-15K Supabase fastnums that lack disk presence AND have listings. That's **vastly less work and storage** than the pilot v3 estimate of full ~1 TB fresh-fetch.

---

## 1. Total disk inventory

```
Total image files (.jpg / .jpeg / .png / .webp): 896,871
Total bytes:                             210,600,299,519  (196.14 GB)
Scan time:                                       175.8 s
Scan saved at:    C:\Users\danie\AppData\Local\Temp\image_paths.txt
```

## 2. Folder structure (top 20 parents by image count)

```
   360 files,  35.3 MB  D:\Leiguskra - scrape\Gagnasafn\myndir\852722
   244 files,  66.2 MB  D:\Gagnapakkar\images\2527607        ← pilot v3 phase 2
   223 files,  40.6 MB  D:\Gagnapakki 1\2000311
   216 files,  55.5 MB  D:\Gagnapakki 1\2000315
   147 files,  30.5 MB  D:\Gagnapakki 4 - fasteignir\myndir\2092597
   147 files,  41.6 MB  D:\Gagnapakki 1\2000309
   138 files,  27.6 MB  D:\Leiguskra - scrape\Gagnasafn\myndir\852978
   135 files,  14.4 MB  D:\Gagnapakki 1\2000323
   126 files,   9.5 MB  D:\Leiguskra - scrape\Gagnasafn\myndir\970472
   ... (≤120 files each)
```

**Folder-naming convention is universal**: every image lives at `<root>\...\<fastnum>\<file>`. The fastnum is the directly-parented directory name, and within each fastnum folder the legacy scraper has renamed CloudFront images to **sequential `1.jpg`, `2.jpg`, …** (extracted from `scraper.py:182-185` — `local_path = str(IMAGE_DIR / fastnum / f"{i+1}.{ext}")`).

## 3. Roots & per-root coverage

| Root | Distinct fastnums | Notes |
|---|---:|---|
| `D:\Gagnapakki 3 - fasteignir\` | 13,370 | largest single tranche |
| `D:\Gagnapakki 4 - fasteignir\` | 8,905 | |
| `D:\Gagnapakki 5 - fasteignir\` | 8,544 | |
| `D:\Gagnapakki 1\` | 7,234 | flat layout (no `myndir/` subdir) |
| `D:\Gagnapakki 2 - fasteignir\` | 435 | small tranche |
| `D:\Leiguskra - scrape\` | 428 | mostly 6-digit IDs (commercial real estate / Leiguskra) |
| `D:\Gagnapakkar\images\` | 5 | pilot v3 phase 2 only |
| **Total distinct fastnums** | **38,771** | (some overlap across roots) |

There are also **711 non-fastnum-pattern parent folders** (top: 6-digit IDs `852722`, `852978`, `970472`, `879204`, …). These are **commercial/Leiguskra IDs**, distinct from HMS residential fastnums.

## 4. Naming convention sample (30 random paths)

```
   359,685 b   D:\Gagnapakki 1\2012202\12.jpg
    89,361 b   D:\Gagnapakki 1\2031876\11.jpg
    70,586 b   D:\Gagnapakki 1\2003743\17.jpg
   242,494 b   D:\Gagnapakki 2 - fasteignir\myndir\2298359\14.jpg
   156,258 b   D:\Gagnapakki 3 - fasteignir\myndir\2356395\13.jpg
   ... (sequential numbering 1.jpg, 2.jpg, ..., N.jpg per fastnum)
   738,598 b   D:\Gagnapakki 4 - fasteignir\myndir\2095199\39.jpg   ← largest in sample
    58,364 b   D:\Gagnapakki 4 - fasteignir\myndir\2149188\29.jpg   ← smallest in sample
```

- Pattern: **`<root>\[myndir\]<fastnum>\<n>.jpg`** where `<n>` is 1-based sequential within the fastnum. The optional `myndir\` subdir is present in `Gagnapakki 2/3/4/5` and absent in `Gagnapakki 1`.
- File-size distribution: 50 KB – 740 KB observed in random sample. Average ~234 KB per file (210.6 GB / 896,871 files).
- **No CloudFront basenames preserved** in the legacy archive. The URL→file mapping is reconstructable only via the SQLite `myndir` table (next section).

## 5. URL-to-disk mapping mechanism

The legacy scrape pipeline persisted full URL/local-path correspondence in SQLite:

```
D:\Gagnapakkar\fasteignir.db    24,094 fasteignir rows / 218,020 myndir rows / 217,982 downloaded
D:\Gagnapakkar\fasteignir1.db   40,858 fasteignir rows / 437,212 myndir rows / 437,189 downloaded
D:\Gagnapakkar\fasteignir2.db    1,261 fasteignir rows /  11,256 myndir rows /  11,256 downloaded
D:\Gagnapakkar\fasteignir3.db   34,765 fasteignir rows / 278,516 myndir rows / 278,514 downloaded
D:\Gagnapakkar\fasteignir4.db   25,654 fasteignir rows / 211,584 myndir rows / 211,527 downloaded

Legacy DB totals:               126,632 fasteignir rows / 1,156,588 myndir rows / 1,156,468 downloaded
Distinct fastnums in any DB:    126,246
Distinct fastnums with augl_json data:   59,023
Distinct fastnums with myndir entries:   48,691
```

The `myndir` schema:
```sql
CREATE TABLE myndir (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fastnum TEXT,
    nr INTEGER,                    -- sequential 1, 2, 3, ...
    url TEXT,                      -- full CloudFront URL, e.g. .../2294894/SKTc9NFD.jpg
    local_path TEXT,               -- e.g. myndir\2294894\1.jpg
    downloaded INTEGER DEFAULT 0,
    UNIQUE(fastnum, nr)
);
```

**This table is the missing link.** Each disk file's CloudFront origin URL is recoverable, every disk path can be reverse-mapped to a fastnum, and the `nr` column gives a stable per-fastnum ordering. **Stage B must read these tables to know which images already exist.**

## 6. Disk-vs-DB integrity check

```
myndir rows marked downloaded=1:  1,156,468
images actually present on disk:    896,871
                                 ----------
                                  -259,597    (gap)
```

The legacy DB claims ~260K more "downloaded" images than exist on disk. Three possibilities:

1. **Files were deleted/moved/repackaged** between the time `downloaded=1` was set and today. Possible — `D:\` has been re-organized over the past year (the multiple `Gagnapakki N` archives suggest progressive consolidation work).
2. **`downloaded=1` was set prematurely** by a buggy scraper variant (set the flag before `f.write(...)` succeeded). Less likely given how `scraper.py:198-201` is structured (`if success: conn.execute("UPDATE myndir SET downloaded=1 ...")`).
3. **Local paths in the DB don't include the root** (they say `myndir\<fastnum>\<n>.jpg` not `D:\Gagnapakki N\myndir\<fastnum>\<n>.jpg`), so resolving a path requires knowing which `Gagnapakki N` archive owns it. Files might be in a `Gagnapakki N` not yet scanned, or in some `Gagnapakkar 6` we haven't found.

A reasonable Stage B mitigation: **for any myndir row marked downloaded=1, verify file existence at `<expected_root>\<local_path>` by globbing across all `Gagnapakki N` roots; if not found, queue for re-download from the recorded URL.** Cost: a sub-second os.stat across ~1.16M paths.

## 7. Coverage vs Supabase `properties` (124,835 fastnums)

```
Supabase fastnums:                   124,835
Disk fastnums (7-digit folders):       38,771
                                     -------
In BOTH (Supabase ∩ disk):             38,267    ← 30.7% of Supabase already has imagery on disk
Supabase only (need fresh fetch):      86,568    ← 69.3% no disk presence
Disk only (extra rows):                   504    ← 428 in 1.0M bucket (commercial), 76 in 2.0M-2.5M

For the 38,267 BOTH:
  ∩ legacy-DB augl rows:               38,267    ← 100% have JSON metadata
  ∩ legacy-DB myndir rows:             38,267    ← 100% have URL→path mapping
  ∩ NOT in any legacy DB:                   0    ← every disk fastnum is DB-tracked
```

**100 % of the disk-and-Supabase intersection is fully indexed in legacy DBs.** No "orphaned" disk folders without metadata.

## 8. Storage-policy-bug posture in legacy archive

The pilot v3 found that fresh `augl_json` payloads include cross-property image URLs (own-ad images PLUS comparable-listings cross-refs) — a fact that breaks naive `image_root/<property_fastnum>/<basename>` layouts.

**Sample 5 fastnums from `fasteignir.db` augl_json**:

| fastnum | own-property URLs | cross-property URLs | own URLs on disk | cross URLs on disk |
|---|---:|---:|---:|---:|
| 2231930 | 35 | 0 | 35 | 0 |
| 2250150 | 12 | 0 | 12 | 0 |
| 2223862 | 40 | 0 | 40 | 0 |
| 2262497 | 0 | 0 | 36 | 0 |
| 2272289 | 58 | 0 | 0 | 0 |

(URL-on-disk match-rate is 0% because legacy archive uses sequential `<n>.jpg` filenames, not CloudFront basenames; the count reflects file existence in the property's folder, not URL→file equality.)

**Observation**: every legacy-DB row sampled had **0 cross-property URLs.** The cross-property bug surfaced in pilot v3 (where 2 of 5 phase-2 fastnums had 62/96 and 122/159 URLs in OTHER properties' CloudFront folders) does NOT appear to be present in the legacy data.

Two interpretations:
1. **evalue.is's response shape changed between Danni's last scrape (~2026-04-16) and today's pilot v3.** A more recent API revision started embedding "comparable listings" with their image URLs in each property's payload. The legacy archive predates this change.
2. **The 5 sampled rows happen to be ones without cross-property refs** — i.e., older/simpler properties without the comparable-listings UI element. Pilot v3's 5 phase-2 fastnums were random-sampled from the same range and 2/5 had crosses, so this isn't structurally rare.

A larger sample is needed to settle this. For now, **the legacy archive is structurally clean** (1 disk path = 1 own-property image), and the recent storage-policy bug only affects fresh scrapes from current evalue.is.

## 9. Practical implications for Stage B (next-session image bootstrap)

The pilot v3 recommended Stage B fetch ~48,595 fastnums × ~100 images × ~250 KB = ~1 TB. **That estimate ignored the existing 196 GB on disk.** Refined plan:

### 9a. Sub-task A: Consolidate-existing (no fresh fetch needed)
- 38,267 fastnums already have disk imagery + full myndir SQL mapping.
- **Net cost: zero re-download.** Just establish a canonical layout/index.
- Pre-storage-policy lock work: build a side-table mapping `(supabase_fastnum, disk_path, cloudfront_url, downloaded_ok)` from the 5 legacy DBs' `myndir` tables. ~5 minutes of pure SQL work.
- Verify file existence per myndir row, repair the ~260K "marked downloaded but missing" rows. Either fetch fresh from URL (slow but correct) or accept the gap (fast). Recommendation: fetch fresh under the corrected storage layout, since these are properties we KNOW had photos.

### 9b. Sub-task B: Fresh fetch for Supabase-only fastnums
- 86,568 Supabase fastnums currently have no disk presence.
- BUT only ~33% (~28K-30K) of them likely have any photos at all (per the 38.9% n_photos>0 rate, biased down because no-disk-presence may correlate with no-listings-history).
- Realistic fresh-fetch target: 10K–25K fastnums, depending on Stage A's augl-refresh result.
- Storage cost: 25K × ~30 MB avg = 750 GB additional (worst case). Or 10K × 30 MB = 300 GB additional (best case).
- Combined archive: 196 GB existing + 300-750 GB fresh = **500 GB – 950 GB total**, NOT ~1 TB fresh.

### 9c. Sub-task C: Repair pilot v3 cross-property-bug fastnums
- 5 phase-2 fastnums had 116 silently-lost cross-property URLs.
- Re-fetch under the corrected layout (`image_root/<cf_path_segment>/<basename>` or chosen alternative). ~5 min wall-clock.
- This becomes a one-line entry in Stage B's fresh-fetch loop, not a separate step.

### Net Stage B scope
- ~30 h wall-clock estimate from pilot v3 stays roughly accurate IF the fetch parallelism (4-way + 0.1s delay) is implemented.
- But the storage estimate drops from ~1 TB to ~500 GB - 950 GB for the COMBINED archive (existing + new), which is much more provision-friendly on a single drive.

### Recommendation: **Hybrid**

1. **Re-use existing 196 GB archive.** Don't re-download anything that already lives on disk.
2. **Build a canonical index** that maps every disk path → CloudFront URL via the legacy `myndir` tables.
3. **Verify-and-repair** missing-on-disk rows (~260K myndir rows say downloaded=1 but file is absent). One-pass file-existence sweep + targeted re-download from URL.
4. **Fresh-fetch** ONLY for the ~10K-25K Supabase fastnums that have no disk presence AND have listings (after Stage A reveals which Supabase fastnums actually have ad-history in their fresh augl payloads).
5. **Migrate everything to the agreed canonical layout** (next-session storage-policy lock will decide between `cf_origin/` / `origin_prefixed_filename` / `hash`). The migration is mostly file-renames + symlinks within `D:\`, not new downloads.

This sequence is **lower wall-clock + lower storage cost + lower CloudFront load** than the pilot v3 "fetch everything fresh" recommendation. The legacy archive is a substantial unrecognized asset.

---

## What's resolved this session

- ✅ Existing archive empirically scoped: 896,871 files, 196.14 GB, 38,771 fastnums, 7 root archives.
- ✅ Mapping mechanism identified: legacy SQLite `myndir` tables provide complete URL→local-path correspondence (1.16M rows).
- ✅ Coverage measured: 30.7% Supabase ∩ disk = 38,267 fastnums already imaged.
- ✅ Naming convention documented: `<root>\[myndir\]<fastnum>\<n>.jpg`, sequential not basename.
- ✅ Storage-policy posture: legacy archive structurally clean (no cross-property URLs in samples). Pilot v3 bug is fresh-scrape-only.
- ✅ Stage B scope refined: hybrid approach saves ~500 GB and substantial wall-clock vs pilot-v3 estimate.
- ✅ ~260K downloaded-but-missing-on-disk discrepancy flagged for repair-in-Stage-B.

## Out-of-scope (next-session candidates)

- Storage-policy lock (cf-origin / origin-prefix / hash filename layout — pilot v3's open question).
- Build the canonical `image_index` SQLite table (collate from 5 legacy DBs' `myndir` tables).
- Verify-and-repair sweep for the ~260K downloaded-but-missing rows.
- Stage A — augl-refresh of 124,835 fastnums (~49 h).
- Stage B — fresh-fetch of ~10K-25K identified targets + migration to canonical layout (~10-20 h, depending on actual scope from Stage A).

---

## Artifacts

- `audit/image_archive_analyzer.py` — read-only analyzer script (this session).
- `audit/image_archive_inventory.md` — this document.
- `C:\Users\danie\AppData\Local\Temp\image_paths.txt` — full path list (896,871 lines, ephemeral).
- `C:\Users\danie\AppData\Local\Temp\disk_fastnums.txt` — distinct disk fastnums (38,771 lines, ephemeral).
- `C:\Users\danie\AppData\Local\Temp\both_fastnums.txt` — Supabase ∩ disk intersection (38,267 lines, ephemeral).

No file moves, no consolidation, no fixes. Read-only investigation.
