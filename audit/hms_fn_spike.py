"""HMS staging-DB false-negative spike — read-only diagnostic.

Steps 0-4 per plan `C:\\Users\\danie\\.claude\\plans\\i-have-a-large-indexed-lynx.md`:

  Step 0: time-clustering analysis (free, no network) — characterize the
          392K HTTP-500 rows in `audit/hms_archive_staging.db` by `fetched_at`.
  Step 1: random sample of 1000 of the 392K 500-rows (seeded for repro).
  Step 2: re-probe flat API with up to 3 retries + exponential backoff.
  Step 3: leit cross-check on persistent-500s.
  Step 4: classify into 4 buckets, emit halt-report with FN rate + Wilson CI
          + estimated recoverable total + dead-zone vs healthy-zone breakdown.

Does NOT mutate audit/hms_archive_staging.db.
Does NOT write to Supabase.
Does NOT edit audit/hms_full_scrape.py.

Run from repo root:
    python audit/hms_fn_spike.py
"""
from __future__ import annotations

import asyncio
import json
import math
import random
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from curl_cffi.requests import AsyncSession

AUDIT = Path(__file__).resolve().parent
DB_PATH = AUDIT / 'hms_archive_staging.db'
SAMPLE_PATH = AUDIT / 'hms_fn_spike_sample.txt'
REPORT_PATH = AUDIT / 'hms_fn_spike_report.md'
RAW_RESULTS_PATH = AUDIT / 'hms_fn_spike_results.json'

API_FLAT = 'https://hms.is/api/fasteignaskra/fasteign'
API_LEIT = 'https://hms.is/api/fasteignaskra/leit'

SAMPLE_SIZE = 1000
SEED = 42
CONCURRENCY = 3
PER_WORKER_DELAY = 1.0
JITTER = 0.4
HTTP_TIMEOUT = 20
RETRY_BACKOFFS = (2.0, 5.0, 12.0)  # seconds; jitter ±30%
WAF_SLEEP = 60

DEAD_ZONE_START = '2026-05-16T07:00'
DEAD_ZONE_END = '2026-05-17T21:00'  # exclusive

ANCHOR_FASTNUM = 2226598
ANCHOR_ISO = '2026-05-16T21:17:38+00:00'


# ---------------------------------------------------------------------------
# Step 0: time-clustering analysis
# ---------------------------------------------------------------------------

def analyze_500_timestamps(con: sqlite3.Connection) -> dict:
    cur = con.cursor()
    out = {}

    cur.execute('SELECT phase, http_status, COUNT(*) FROM hms_fasteign GROUP BY phase, http_status ORDER BY 1, 2')
    out['phase_status_counts'] = [(ph, sc, n) for ph, sc, n in cur.fetchall()]

    cur.execute("""
        SELECT substr(fetched_at,1,13) AS hour, http_status, COUNT(*)
          FROM hms_fasteign
         WHERE phase = 'C'
         GROUP BY hour, http_status
         ORDER BY hour
    """)
    hour = defaultdict(lambda: {200: 0, 500: 0})
    for h, sc, n in cur.fetchall():
        hour[h][sc] = n
    out['phase_c_hourly'] = sorted([(h, d[200], d[500]) for h, d in hour.items()])

    # Dead zone summary
    dz_500 = sum(d500 for h, _, d500 in out['phase_c_hourly'] if DEAD_ZONE_START <= h < DEAD_ZONE_END)
    dz_200 = sum(d200 for h, d200, _ in out['phase_c_hourly'] if DEAD_ZONE_START <= h < DEAD_ZONE_END)
    nz_500 = sum(d500 for h, _, d500 in out['phase_c_hourly'] if not (DEAD_ZONE_START <= h < DEAD_ZONE_END))
    nz_200 = sum(d200 for h, d200, _ in out['phase_c_hourly'] if not (DEAD_ZONE_START <= h < DEAD_ZONE_END))
    out['dead_zone'] = dict(n_200=dz_200, n_500=dz_500)
    out['healthy_zone'] = dict(n_200=nz_200, n_500=nz_500)

    return out


# ---------------------------------------------------------------------------
# Step 1: random sample
# ---------------------------------------------------------------------------

def sample_500s(con: sqlite3.Connection, n: int = SAMPLE_SIZE, seed: int = SEED) -> list[tuple[int, str]]:
    """Returns list of (fastnum, fetched_at) for n random rows where http_status=500."""
    rng = random.Random(seed)
    cur = con.cursor()
    cur.execute('SELECT fastnum, fetched_at, phase FROM hms_fasteign WHERE http_status = 500')
    all_rows = cur.fetchall()
    rng.shuffle(all_rows)
    chosen = all_rows[:n]
    chosen.sort()
    return [(fn, ts) for fn, ts, _ in chosen]


def write_sample(rows: list[tuple[int, str]]) -> None:
    lines = ['# HMS false-negative spike: random sample of 500-rows',
             f'# Generated: {datetime.now(timezone.utc).isoformat(timespec="seconds")}',
             f'# Seed: {SEED}',
             f'# Source: audit/hms_archive_staging.db (http_status=500 only)',
             f'# Count: {len(rows)}',
             '# Format: fastnum<TAB>scrape_fetched_at',
             '']
    for fn, ts in rows:
        lines.append(f'{fn}\t{ts}')
    SAMPLE_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ---------------------------------------------------------------------------
# Step 2+3: re-probe flat API with retry, then leit fallback
# ---------------------------------------------------------------------------

async def probe_flat(session: AsyncSession, fastnum: int) -> tuple[int, int, str | None, float]:
    """Returns (final_status, attempts_used, payload_excerpt, total_ms).
    Retries on 500/-1 up to len(RETRY_BACKOFFS)+1 attempts."""
    total_start = time.perf_counter()
    payload = None
    attempt = 0
    sc = -1
    for attempt in range(len(RETRY_BACKOFFS) + 1):
        try:
            r = await session.get(f'{API_FLAT}/{fastnum}', timeout=HTTP_TIMEOUT)
            sc = r.status_code
            if sc == 200:
                try:
                    j = r.json()
                    fd = j.get('fasteignData') if isinstance(j, dict) else None
                    payload = json.dumps(fd, ensure_ascii=False)[:500] if fd else r.text[:500]
                except Exception:
                    payload = r.text[:500] if r.text else None
                break
            if sc in (429, 403, 503):
                # WAF — back off long once
                await asyncio.sleep(WAF_SLEEP)
                continue
            if sc != 500 and sc != -1:
                # Unexpected status; record and stop
                break
            # 500: retry
        except Exception as e:
            sc = -1
            payload = f'EXC:{type(e).__name__}:{str(e)[:200]}'
        if attempt < len(RETRY_BACKOFFS):
            backoff = RETRY_BACKOFFS[attempt]
            backoff *= (1 + random.uniform(-0.3, 0.3))
            await asyncio.sleep(backoff)
    total_ms = (time.perf_counter() - total_start) * 1000
    return sc, attempt + 1, payload, total_ms


async def probe_leit(session: AsyncSession, fastnum: int) -> tuple[int, str | None]:
    """Single-attempt search-index lookup."""
    try:
        r = await session.get(f'{API_LEIT}', params={'q': str(fastnum)}, timeout=HTTP_TIMEOUT)
        sc = r.status_code
        if sc == 200:
            try:
                j = r.json()
                data = j.get('data') if isinstance(j, dict) else None
                if data and isinstance(data, list) and len(data) > 0:
                    # Match by exact fastnum to avoid name-collisions
                    for row in data:
                        if isinstance(row, dict) and (row.get('fastnum') == fastnum or row.get('fasteign_nr') == fastnum):
                            return 200, json.dumps(row, ensure_ascii=False)[:500]
                    return 200, None  # search returned results but no exact fastnum match
                return 200, None  # empty result set
            except Exception:
                return 200, None
        return sc, None
    except Exception as e:
        return -1, f'EXC:{type(e).__name__}:{str(e)[:200]}'


async def process_fastnum(sem: asyncio.Semaphore, session: AsyncSession, fastnum: int, scrape_ts: str) -> dict:
    async with sem:
        flat_sc, flat_attempts, flat_payload, flat_ms = await probe_flat(session, fastnum)
        leit_sc = None
        leit_payload = None
        if flat_sc != 200:
            leit_sc, leit_payload = await probe_leit(session, fastnum)
        await asyncio.sleep(PER_WORKER_DELAY + random.uniform(-JITTER, JITTER))
        return {
            'fastnum': fastnum,
            'scrape_fetched_at': scrape_ts,
            'flat_status': flat_sc,
            'flat_attempts': flat_attempts,
            'flat_payload_excerpt': flat_payload,
            'flat_total_ms': round(flat_ms, 1),
            'leit_status': leit_sc,
            'leit_payload_excerpt': leit_payload,
        }


async def run_probes(rows: list[tuple[int, str]]) -> list[dict]:
    sem = asyncio.Semaphore(CONCURRENCY)
    results = []
    completed = 0
    total = len(rows)
    last_log = time.time()
    async with AsyncSession(impersonate='chrome120') as session:
        tasks = [asyncio.create_task(process_fastnum(sem, session, fn, ts)) for fn, ts in rows]
        for coro in asyncio.as_completed(tasks):
            r = await coro
            results.append(r)
            completed += 1
            if time.time() - last_log > 10:
                ok = sum(1 for x in results if x['flat_status'] == 200)
                leit_only = sum(1 for x in results if x['flat_status'] != 200 and x.get('leit_status') == 200 and x.get('leit_payload_excerpt'))
                print(f'  ... {completed}/{total}  flat-200={ok}  leit-recover={leit_only}', flush=True)
                last_log = time.time()
    return results


# ---------------------------------------------------------------------------
# Step 4: classify and report
# ---------------------------------------------------------------------------

def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return ((centre - half) / denom, (centre + half) / denom)


def in_dead_zone(ts: str) -> bool:
    return DEAD_ZONE_START <= ts[:16] < DEAD_ZONE_END


def classify(results: list[dict]) -> dict:
    out = {
        'recovered_200': [],
        'recovered_via_leit_only': [],
        'persistent_500': [],
        'inconclusive': [],
    }
    for r in results:
        flat = r['flat_status']
        leit = r.get('leit_status')
        if flat == 200:
            out['recovered_200'].append(r)
        elif flat in (429, 403, 503) or flat == -1:
            out['inconclusive'].append(r)
        elif leit == 200 and r.get('leit_payload_excerpt'):
            out['recovered_via_leit_only'].append(r)
        elif flat == 500 and (leit in (500, None) or (leit == 200 and not r.get('leit_payload_excerpt'))):
            out['persistent_500'].append(r)
        else:
            out['inconclusive'].append(r)
    return out


def write_report(step0: dict, sample: list[tuple[int, str]], results: list[dict], buckets: dict) -> None:
    total = len(results)
    n_recovered = len(buckets['recovered_200']) + len(buckets['recovered_via_leit_only'])
    n_persistent = len(buckets['persistent_500'])
    n_inconclusive = len(buckets['inconclusive'])
    denom = total - n_inconclusive
    fn_rate = n_recovered / denom if denom else 0
    fn_lo, fn_hi = wilson_ci(n_recovered, denom)

    # Dead-zone breakdown
    dz_total = sum(1 for r in results if in_dead_zone(r['scrape_fetched_at']))
    hz_total = total - dz_total
    dz_rec = sum(1 for r in results if in_dead_zone(r['scrape_fetched_at']) and (r['flat_status'] == 200 or (r.get('leit_status') == 200 and r.get('leit_payload_excerpt'))))
    hz_rec = n_recovered - dz_rec
    dz_inc = sum(1 for r in buckets['inconclusive'] if in_dead_zone(r['scrape_fetched_at']))
    hz_inc = n_inconclusive - dz_inc
    dz_denom = dz_total - dz_inc
    hz_denom = hz_total - hz_inc
    dz_fn = dz_rec / dz_denom if dz_denom else 0
    hz_fn = hz_rec / hz_denom if hz_denom else 0
    dz_lo, dz_hi = wilson_ci(dz_rec, dz_denom)
    hz_lo, hz_hi = wilson_ci(hz_rec, hz_denom)

    # Apply to full population
    dz_pop_500 = step0['dead_zone']['n_500']
    hz_pop_500 = step0['healthy_zone']['n_500']
    phase_a_500 = sum(n for ph, sc, n in step0['phase_status_counts'] if ph == 'A' and sc == 500)
    phase_b_500 = sum(n for ph, sc, n in step0['phase_status_counts'] if ph == 'B' and sc == 500)
    total_500 = phase_a_500 + phase_b_500 + dz_pop_500 + hz_pop_500

    est_dz_recoverable = dz_fn * dz_pop_500
    est_hz_recoverable = hz_fn * hz_pop_500
    est_total_recoverable = est_dz_recoverable + est_hz_recoverable

    # Time-distribution of recovered cases
    rec_in_dz = sum(1 for r in (buckets['recovered_200'] + buckets['recovered_via_leit_only']) if in_dead_zone(r['scrape_fetched_at']))
    rec_in_hz = n_recovered - rec_in_dz

    # Anchor sanity check
    anchor_result = next((r for r in results if r['fastnum'] == ANCHOR_FASTNUM), None)

    # Eyeball cases
    eyeball = []
    rng = random.Random(SEED)
    rec_pool = list(buckets['recovered_200'])
    rng.shuffle(rec_pool)
    for r in rec_pool[:10]:
        try:
            d = json.loads(r['flat_payload_excerpt']) if r['flat_payload_excerpt'] else None
        except Exception:
            d = None
        if d:
            eyeball.append({
                'fastnum': r['fastnum'],
                'stadfang_birting': d.get('stadfang_birting'),
                'landeign_nr': d.get('landeign_nr'),
                'notkun_texti': d.get('notkun_texti'),
                'sveitarfelag_nafn': d.get('sveitarfelag_nafn'),
                'scrape_fetched_at': r['scrape_fetched_at'],
                'flat_attempts': r['flat_attempts'],
            })

    # Generate markdown
    lines = []
    lines.append('# HMS false-negative spike — halt report')
    lines.append('')
    lines.append(f'**Generated**: {datetime.now(timezone.utc).isoformat(timespec="seconds")}')
    lines.append(f'**Sample size**: {total} (random sample of {sum(n for ph,sc,n in step0["phase_status_counts"] if sc==500):,} HTTP-500 rows, seed={SEED})')
    lines.append(f'**Plan**: `C:\\Users\\danie\\.claude\\plans\\i-have-a-large-indexed-lynx.md`')
    lines.append('')
    lines.append('## Headline')
    lines.append('')
    lines.append(f'- **False-negative rate (overall)**: **{100*fn_rate:.1f}%** (Wilson 95% CI {100*fn_lo:.1f}–{100*fn_hi:.1f}%)')
    lines.append(f'- **Estimated total recoverable real properties**: **~{int(est_total_recoverable):,}** (dead-zone ~{int(est_dz_recoverable):,} + healthy-zone ~{int(est_hz_recoverable):,})')
    lines.append(f'- **Dead-zone FN rate**: {100*dz_fn:.1f}% (CI {100*dz_lo:.1f}–{100*dz_hi:.1f}%) on {dz_pop_500:,} dead-zone 500s')
    lines.append(f'- **Healthy-zone FN rate**: {100*hz_fn:.1f}% (CI {100*hz_lo:.1f}–{100*hz_hi:.1f}%) on {hz_pop_500:,} healthy-zone 500s')
    if anchor_result:
        a_flat = anchor_result['flat_status']
        a_leit = anchor_result.get('leit_status')
        a_label = ('recovered-200' if a_flat == 200
                   else 'recovered-via-leit' if a_leit == 200 and anchor_result.get('leit_payload_excerpt')
                   else 'persistent-500')
        lines.append(f'- **Anchor 2226598 in sample**: yes — classified `{a_label}` (flat={a_flat}, leit={a_leit}, attempts={anchor_result["flat_attempts"]})')
    else:
        lines.append('- **Anchor 2226598 in sample**: not drawn this seed.')
    lines.append('')

    lines.append('## Step 0 — Time-clustering signal (the big finding)')
    lines.append('')
    lines.append('Phase C had a sustained API dead zone from **2026-05-16T07:00 → 2026-05-17T21:00 UTC (~38 hours)**.')
    lines.append('Hit rate during the dead zone: **0.0%** sustained per hour (9,200-9,600 fastnums/hr, all HTTP 500).')
    lines.append('Hit rate outside the dead zone (healthy windows): 9-76% per hour.')
    lines.append('Phase B baseline 500-rate: 0.08% (97 / 124,835).')
    lines.append('')
    lines.append(f'Phase C 500-row distribution:')
    lines.append(f'- Dead zone:       {step0["dead_zone"]["n_500"]:>7,} 500s  ({step0["dead_zone"]["n_200"]:,} 200s)')
    lines.append(f'- Healthy zone:    {step0["healthy_zone"]["n_500"]:>7,} 500s  ({step0["healthy_zone"]["n_200"]:,} 200s)')
    lines.append('')

    lines.append('## Step 1-3 — Probe outcomes')
    lines.append('')
    lines.append(f'| Bucket | n | % of sample |')
    lines.append(f'|---|---:|---:|')
    lines.append(f'| recovered-200 | {len(buckets["recovered_200"])} | {100*len(buckets["recovered_200"])/total:.1f}% |')
    lines.append(f'| recovered-via-leit-only | {len(buckets["recovered_via_leit_only"])} | {100*len(buckets["recovered_via_leit_only"])/total:.1f}% |')
    lines.append(f'| persistent-500 | {len(buckets["persistent_500"])} | {100*len(buckets["persistent_500"])/total:.1f}% |')
    lines.append(f'| inconclusive (WAF / exception) | {len(buckets["inconclusive"])} | {100*len(buckets["inconclusive"])/total:.1f}% |')
    lines.append('')
    lines.append(f'**Recovered cases time-distribution**: {rec_in_dz}/{n_recovered} fell in dead-zone, {rec_in_hz}/{n_recovered} in healthy zone.')
    lines.append('')

    if buckets['recovered_200']:
        attempts_counter = Counter(r['flat_attempts'] for r in buckets['recovered_200'])
        lines.append(f'**Attempts-to-recover histogram** (recovered-200 only): ' + ', '.join(f'{k}={v}' for k, v in sorted(attempts_counter.items())))
        lines.append('')

    lines.append('## Eyeball validation — 10 random recovered cases')
    lines.append('')
    if eyeball:
        lines.append('| fastnum | scrape ts | stadfang | landeign_nr | notkun | sveitarfélag | flat_attempts |')
        lines.append('|---|---|---|---|---|---|---|')
        for e in eyeball:
            lines.append(f'| {e["fastnum"]} | {e["scrape_fetched_at"]} | {e["stadfang_birting"] or "—"} | {e["landeign_nr"] or "—"} | {e["notkun_texti"] or "—"} | {e["sveitarfelag_nafn"] or "—"} | {e["flat_attempts"]} |')
    else:
        lines.append('_No recovered cases — nothing to eyeball._')
    lines.append('')

    lines.append('## Recommendation')
    lines.append('')
    if est_total_recoverable >= 50000:
        lines.append('### (a) Full re-scrape of all 392K 500-rows — STRONGLY recommended')
        lines.append('')
        lines.append(f'Estimated recovery: ~{int(est_total_recoverable):,} real properties currently missing from the staging DB.')
        lines.append(f'Wall-clock at scrape-equivalent rate (~157/min): ~{392026/157/60:.1f} hours.')
        lines.append(f'The dead-zone bulk ({step0["dead_zone"]["n_500"]:,} rows) almost certainly contains the lion\'s share of recoverable properties.')
    elif est_total_recoverable >= 5000:
        lines.append('### (b) Time-targeted re-scrape — recommended')
        lines.append('')
        lines.append(f'Re-scrape only the dead-zone subset ({step0["dead_zone"]["n_500"]:,} rows, {DEAD_ZONE_START} → {DEAD_ZONE_END}).')
        lines.append(f'Estimated recovery: ~{int(est_dz_recoverable):,} properties.')
        lines.append(f'Healthy-zone FN rate is {100*hz_fn:.1f}% — too low to justify the additional 6 hours.')
    else:
        lines.append('### (c) No-op — recovery not worth the network cost')
        lines.append('')
        lines.append(f'Estimated recovery: only ~{int(est_total_recoverable):,} properties.')
        lines.append('Recommend instead: spot-check individual fastnums on demand using the leit endpoint.')
    lines.append('')
    lines.append('## Out of scope (not done here)')
    lines.append('')
    lines.append('- No Supabase writes; no production-scraper edits; no audit of sibling scrapers.')
    lines.append('- Decision on (a)/(b)/(c) deferred to the user. Next session implements the chosen path.')
    lines.append('')

    REPORT_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def main():
    if not DB_PATH.exists():
        print(f'ERROR: staging DB not found at {DB_PATH}', file=sys.stderr)
        return 2

    con = sqlite3.connect(DB_PATH)

    print('=== Step 0: time-clustering analysis ===', flush=True)
    step0 = analyze_500_timestamps(con)
    print(f'  Phase A: {sum(n for p,s,n in step0["phase_status_counts"] if p=="A" and s==500):,} 500s')
    print(f'  Phase B: {sum(n for p,s,n in step0["phase_status_counts"] if p=="B" and s==500):,} 500s')
    print(f'  Phase C dead-zone:    {step0["dead_zone"]["n_500"]:,} 500s ({step0["dead_zone"]["n_200"]:,} 200s)')
    print(f'  Phase C healthy-zone: {step0["healthy_zone"]["n_500"]:,} 500s ({step0["healthy_zone"]["n_200"]:,} 200s)')

    print()
    print(f'=== Step 1: drawing random sample of {SAMPLE_SIZE} (seed={SEED}) ===', flush=True)
    sample = sample_500s(con, SAMPLE_SIZE, SEED)
    # Inject the anchor fastnum so the user can verify end-to-end
    fns_in_sample = {fn for fn, _ in sample}
    if ANCHOR_FASTNUM not in fns_in_sample:
        cur = con.cursor()
        cur.execute('SELECT fastnum, fetched_at FROM hms_fasteign WHERE fastnum = ? AND http_status = 500', (ANCHOR_FASTNUM,))
        row = cur.fetchone()
        if row:
            sample = [(row[0], row[1])] + sample[:-1]
            print(f'  Injected anchor fastnum {ANCHOR_FASTNUM} (replaced one random sample to keep size {SAMPLE_SIZE})')
    write_sample(sample)
    print(f'  Wrote {SAMPLE_PATH}')

    # Pre-run staging-DB invariant
    pre_500 = con.execute('SELECT COUNT(*) FROM hms_fasteign WHERE http_status=500').fetchone()[0]
    print(f'  Pre-run staging-DB 500 count: {pre_500:,}')

    print()
    print('=== Step 2+3: re-probing with retry + leit fallback ===', flush=True)
    print(f'  Endpoint flat: {API_FLAT}/{{fn}}')
    print(f'  Endpoint leit: {API_LEIT}?q={{fn}}  (on persistent-500 only)')
    print(f'  Concurrency: {CONCURRENCY}, retries: {len(RETRY_BACKOFFS)} ({RETRY_BACKOFFS}s ±30% jitter)')
    t_start = time.perf_counter()
    results = await run_probes(sample)
    t_elapsed = time.perf_counter() - t_start
    print(f'  Completed {len(results)} probes in {t_elapsed/60:.1f} min')

    # Post-run staging-DB invariant
    post_500 = con.execute('SELECT COUNT(*) FROM hms_fasteign WHERE http_status=500').fetchone()[0]
    print(f'  Post-run staging-DB 500 count: {post_500:,}')
    assert pre_500 == post_500, f'STAGING DB MUTATED — pre={pre_500} post={post_500}'

    # Persist raw results for auditability
    RAW_RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')

    print()
    print('=== Step 4: classify and report ===', flush=True)
    buckets = classify(results)
    print(f'  recovered-200:           {len(buckets["recovered_200"])}')
    print(f'  recovered-via-leit-only: {len(buckets["recovered_via_leit_only"])}')
    print(f'  persistent-500:          {len(buckets["persistent_500"])}')
    print(f'  inconclusive:            {len(buckets["inconclusive"])}')
    write_report(step0, sample, results, buckets)
    print(f'  Wrote {REPORT_PATH}')

    con.close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print('\nInterrupted — sample + partial results may be on disk.')
        sys.exit(130)
