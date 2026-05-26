# Weekend run runbook (Áfangi 0 Stage 1)

**Started**: 2026-05-08 13:14 UTC (Phase 2 launched)
**Expected total wall-clock**: ~58 h Phase 2 + ~10–15 h Phase 3 ≈ 3 days
**Status surface**: `cat audit/weekend_run_status.md` from any terminal

---

## What's running right now

Phase 2 (`stage_a_augl_refresh.py`) is sweeping all 124,835 fastnums against
`evalue.is/get_fasteign_augl` at 1 req/sec, writing each row to
`audit/stage_a_augl_staging.db`. Throughput observed ~36 rows/min →
ETA ~58 h.

## How to monitor

**Anytime, any terminal** (separate from the run process):
```
cat audit/weekend_run_status.md
```
The status file is rewritten every minute by the running process. Shows
phase state, current item progress, ETA, recent log, halt list, disk usage.

For deeper inspection of staging progress:
```
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
c = sqlite3.connect(r'D:\verdmat-is\app\audit\stage_a_augl_staging.db', timeout=5)
c.execute('PRAGMA query_only=ON')
print('rows:', c.execute('SELECT COUNT(*) FROM stage_a_augl').fetchone()[0])
print('by status:')
for r in c.execute('SELECT augl_status, COUNT(*) FROM stage_a_augl GROUP BY augl_status'):
    print(' ', r)
"
```

## How to resume after kill / session end / Cloudflare halt

Phase 2 is fully resume-safe. If the process dies (Claude session ends,
machine reboots, anything), simply re-launch:

```
cd D:\verdmat-is\app
python audit/stage_a_augl_refresh.py
```

It reads `stage_a_augl_staging.db` on startup, builds a done-set,
and skips fastnums already in the table. Picks up at the row count where
it left off.

## How to launch Phase 3 after Phase 2 completes

When `stage_a_augl_staging.db` has rows for ≥124,000 of the 124,835
fastnums (visible via the above inspect snippet), launch Phase 3:

```
cd D:\verdmat-is\app
python audit/stage_b_image_bootstrap.py
```

Phase 3 will:
1. Walk Stage A's payloads to discover any new image URLs not in
   `image_index.db` and insert them as `downloaded=0` placeholders.
2. Spawn 4 worker threads to drain all `downloaded=0` rows from CloudFront
   in parallel.
3. Update `image_index.db` for each successful fetch.

ETA ~10–15 h depending on number of new URLs discovered + parallelism
efficiency.

## How to launch the whole pipeline at once

If you want to launch everything serially (orchestrator handles
"already-done" detection):

```
cd D:\verdmat-is\app
python audit/weekend_run_orchestrator.py
```

The orchestrator skips already-completed phases (image_index.db with
>1M rows = Phase 1 done; stage_a DB with 124K rows = Phase 2 done; phase
3 sentinel file = Phase 3 done) and runs the rest.

## Halt conditions and what to do

The status file's `## Halts` section lists any halts. Causes the run might
halt:
- **Cloudflare 403 / interactive challenge / HTML response from evalue.is**:
  the evalue.is anti-bot has tightened. Investigate from a browser, may
  need UA rotation or residential proxy. Do not retry-with-delay.
- **CloudFront 403 rate >5% on rolling 100-fetch window** (Phase 3 only):
  CDN is blocking us. Could be a temporary regional thing. Wait a few
  hours and retry.
- **Disk free < 5%**: free up space on D:\ (currently ~715 GB free, very
  unlikely to hit).
- **Sustained network failure >10 min**: ISP, DNS, etc. Recover network,
  re-launch.

After any halt, the script writes the halt reason to the status file and
exits. To continue, fix the underlying issue then re-launch the same
script — it picks up from where it stopped.

## Phase 4 (final commit + push) — manual, after Phase 3 completes

The weekend run does NOT auto-commit. After Phase 3 completes, a Claude
session writes the final summary report and commits + pushes the audit
artifacts. The image archive itself + the staging/index DBs are
gitignored — only `audit/*.md` and `audit/*.py` are committed.

## Files involved

**Input / source-of-truth**:
- `audit/stage_a_fastnum_manifest.txt` — 124,835 fastnums (one per line)
- `D:\Gagnapakkar\fasteignir{,1,2,3,4}.db` — legacy SQLite DBs (read-only)

**Output / state**:
- `D:\Gagnapakkar\image_index.db` — canonical URL→file index (~70 MB, 1.15M rows pre-Phase-3)
- `audit/stage_a_augl_staging.db` — fresh augl payloads (~50–100 MB at completion)
- `D:\Gagnapakkar\images\<fastnum>\<n>.jpg` — image archive (existing 196 GB + new ~300–750 GB)

**Observability**:
- `audit/weekend_run_status.md` — live status (re-written every minute)
- `audit/weekend_run.log` — append-only log
- per-phase reports: `legacy_myndir_collation_log.md`, `integrity_repair_report.md`,
  `storage_policy_validation_report.md`, `stage_a_completion_report.md`,
  `stage_b_completion_report.md`, `weekend_run_summary.md`
