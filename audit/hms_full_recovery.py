"""HMS staging-DB false-negative recovery — re-probe all 392K HTTP-500 rows.

Design decisions (from spike findings, 2026-05-21):
  - flat API only (spike: 0/815 leit-only recoveries — flat sufficient)
  - 1 retry on 500/-1 with 1s backoff (spike: 185/185 on 1st attempt; retry is cheap insurance)
  - Outage detection: sliding window of last 100 results; if 0 hits in full window → PAUSE 5min
    → re-window; if still 0 hits → HALT + alert. Prevents repro of the bug if a fresh outage
    hits mid-run.
  - WAF backoff preserved (429/403/503 streak ≥10 → 300s sleep)
  - Schema additive: ALTER TABLE hms_fasteign ADD COLUMN reprobed_at TEXT (already applied)
  - Resumable: target set = WHERE http_status=500 AND reprobed_at IS NULL — re-built every start
  - Polite rate: CONCURRENCY=3, PER_WORKER_DELAY=1.0s + jitter (matches original)
  - NO Supabase writes; NO production-scraper edits

Database semantics:
  Original 500 (from scrape):           reprobed_at IS NULL
  Confirmed-still-500 (after recovery): reprobed_at IS NOT NULL AND http_status=500
  Recovered (was 500, now 200):         reprobed_at IS NOT NULL AND http_status=200
                                        (fasteign_data populated; fetched_at = recovery time)

Halt mechanism: touch file `audit/RECOVERY_HALT` → runner exits gracefully at next batch boundary.

Run from repo root:
    python audit/hms_full_recovery.py
"""
from __future__ import annotations

import asyncio
import json
import random
import sqlite3
import sys
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

from curl_cffi.requests import AsyncSession

AUDIT = Path(__file__).resolve().parent
DB_PATH = AUDIT / 'hms_archive_staging.db'
STATUS_PATH = AUDIT / 'hms_recovery_status.md'
LOG_PATH = AUDIT / 'hms_recovery.log'
REPORT_PATH = AUDIT / 'hms_recovery_report.md'
HALT_FLAG = AUDIT / 'RECOVERY_HALT'

API = 'https://hms.is/api/fasteignaskra/fasteign'

CONCURRENCY = 3
PER_WORKER_DELAY = 1.0
JITTER = 0.4
BATCH_SIZE = 200
HTTP_TIMEOUT = 20

RETRY_BACKOFF = 1.0  # seconds; only 1 retry

WAF_STATUSES = (429, 403, 503)
WAF_BACKOFF_STREAK = 10
WAF_BACKOFF_SECONDS = 300

OUTAGE_WINDOW = 100  # sliding window size for outage detection
OUTAGE_PAUSE_SECONDS = 300
OUTAGE_PAUSE_ATTEMPTS = 2  # halt after this many consecutive zero-hit windows

STATUS_INTERVAL_S = 30
SEED = 4221  # for shuffling target set (reproducible ordering per run)

STARTED_AT = datetime.now(timezone.utc)

STATE = {
    'done': 0,
    'total': 0,
    'recovered_200': 0,
    'confirmed_500': 0,
    'waf_pauses': 0,
    'outage_pauses': 0,
    'halted_by_outage': False,
    'halted_by_flag': False,
    'last_status_write': 0,
    'window_status': deque(maxlen=OUTAGE_WINDOW),
}


def log(msg: str) -> None:
    line = f'[{datetime.now(timezone.utc).isoformat(timespec="seconds")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def fmt_dur(seconds: float) -> str:
    s = int(max(seconds, 0))
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    if h:
        return f'{h}h {m}m {s}s'
    if m:
        return f'{m}m {s}s'
    return f'{s}s'


def setup_db() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=60, isolation_level=None)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=NORMAL')
    c.execute('PRAGMA temp_store=MEMORY')
    cols = {row[1] for row in c.execute('PRAGMA table_info(hms_fasteign)').fetchall()}
    for required in ('reprobed_at', 'full_response'):
        if required not in cols:
            raise RuntimeError(f'Schema not ready: {required} column missing. Run the one-shot migration first.')
    return c


def write_status() -> None:
    now = datetime.now(timezone.utc)
    elapsed = (now - STARTED_AT).total_seconds()
    rate = STATE['done'] / max(elapsed, 1) * 60
    pct = (STATE['done'] / STATE['total'] * 100) if STATE['total'] else 0
    eta = ((STATE['total'] - STATE['done']) / max(rate / 60, 1e-6)) if rate > 0 else 0
    win_200 = sum(1 for s in STATE['window_status'] if s == 200)
    win_size = len(STATE['window_status'])
    win_pct = 100 * win_200 / max(win_size, 1)

    lines = [
        '# HMS recovery status',
        '',
        f'**Updated:** {now.isoformat(timespec="seconds")}',
        f'**Started:** {STARTED_AT.isoformat(timespec="seconds")}',
        f'**Elapsed:** {fmt_dur(elapsed)}',
        '',
        '## Progress',
        f'- Done: {STATE["done"]:,} / {STATE["total"]:,} ({pct:.1f}%)',
        f'- Rate: {rate:.1f}/min',
        f'- ETA: {fmt_dur(eta)}',
        '',
        '## Outcomes so far',
        f'- recovered-200:     {STATE["recovered_200"]:,}',
        f'- confirmed-500:     {STATE["confirmed_500"]:,}',
        f'- realized FN rate:  {100*STATE["recovered_200"]/max(STATE["done"],1):.2f}%',
        '',
        '## Health',
        f'- Sliding window (last {win_size} results) 200-rate: {win_pct:.1f}% (expected ~18%)',
        f'- WAF pauses so far:    {STATE["waf_pauses"]}',
        f'- Outage pauses so far: {STATE["outage_pauses"]}',
    ]
    if STATE['halted_by_outage']:
        lines += ['', '## HALT', 'Halted by outage detection — sliding-window 200-rate stayed at 0% across configured threshold.']
    if STATE['halted_by_flag']:
        lines += ['', '## HALT', f'Halted by HALT_FLAG file at {HALT_FLAG}.']
    STATUS_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')


async def fetch_one(sem: asyncio.Semaphore, session: AsyncSession, fastnum: int) -> tuple[int, int, str | None, str | None]:
    """Returns (final_status, attempts_used, fasteignData_json, full_response_json). 1 retry on 500/-1.

    full_response_json captures the entire API envelope (fasteignData + stadfangData + hasMultipleFasteignir),
    so downstream Phase D4 (cross_property_refs) and address-level enrichment can use the sibling-fastnum
    + stadvisir/postnumer_heiti payloads we get for free on every probe.
    """
    async with sem:
        sc = -1
        payload = None
        full_payload = None
        for attempt in range(2):  # 1 initial + 1 retry
            try:
                r = await session.get(f'{API}/{fastnum}', timeout=HTTP_TIMEOUT)
                sc = r.status_code
                if sc == 200:
                    try:
                        j = r.json()
                        if isinstance(j, dict):
                            full_payload = json.dumps(j, ensure_ascii=False)
                            fd = j.get('fasteignData')
                            if fd is not None:
                                payload = json.dumps(fd, ensure_ascii=False)
                    except Exception:
                        payload = (r.text or '')[:5000] or None
                    break
                if sc in WAF_STATUSES:
                    break  # let caller handle WAF
                # 500 / unexpected → maybe retry
            except Exception as e:
                sc = -1
                payload = f'EXC:{type(e).__name__}:{str(e)[:200]}'
            if attempt == 0:
                await asyncio.sleep(RETRY_BACKOFF)
        await asyncio.sleep(PER_WORKER_DELAY + random.uniform(-JITTER, JITTER))
        return sc, attempt + 1, payload, full_payload


async def run_recovery(conn: sqlite3.Connection, targets: list[int]) -> None:
    STATE['total'] = len(targets)
    sem = asyncio.Semaphore(CONCURRENCY)
    waf_streak = 0
    outage_pause_count = 0
    last_status = time.time()

    async with AsyncSession(impersonate='chrome120') as session:
        for batch_start in range(0, len(targets), BATCH_SIZE):
            # Halt flag check at every batch boundary
            if HALT_FLAG.exists():
                STATE['halted_by_flag'] = True
                log(f'Halt flag detected at {HALT_FLAG} — exiting gracefully at batch boundary.')
                write_status()
                return

            batch = targets[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*(fetch_one(sem, session, fn) for fn in batch))
            now_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')

            rows_200 = []
            rows_500 = []
            for fn, (sc, attempts, payload, full_payload) in zip(batch, results):
                STATE['window_status'].append(sc)
                if sc == 200:
                    # Preserve original fetched_at (don't overwrite); only update reprobed_at.
                    rows_200.append((sc, payload, full_payload, now_iso, fn))
                    STATE['recovered_200'] += 1
                    waf_streak = 0
                elif sc in WAF_STATUSES:
                    waf_streak += 1
                    # defer this fastnum to next attempt (reprobed_at stays NULL; next run picks it up)
                else:
                    # 500 / -1 / other → confirmed-still-500 (record reprobed_at, leave http_status/data alone)
                    rows_500.append((now_iso, fn))
                    STATE['confirmed_500'] += 1
                    waf_streak = 0

            if rows_200:
                conn.executemany(
                    'UPDATE hms_fasteign SET http_status=?, fasteign_data=?, full_response=?, exists_in_hms=1, reprobed_at=? WHERE fastnum=?',
                    rows_200,
                )
            if rows_500:
                conn.executemany(
                    'UPDATE hms_fasteign SET reprobed_at=? WHERE fastnum=?',
                    rows_500,
                )

            STATE['done'] += len(batch)

            if time.time() - last_status > STATUS_INTERVAL_S:
                write_status()
                log(
                    f'progress {STATE["done"]:,}/{STATE["total"]:,}  '
                    f'recovered={STATE["recovered_200"]:,}  '
                    f'confirmed-500={STATE["confirmed_500"]:,}  '
                    f'window-200rate={100*sum(1 for s in STATE["window_status"] if s==200)/max(len(STATE["window_status"]),1):.1f}%'
                )
                last_status = time.time()

            # === WAF backoff (preserved from original) ===
            if waf_streak >= WAF_BACKOFF_STREAK:
                STATE['waf_pauses'] += 1
                log(f'WAF backoff: {waf_streak} consecutive {WAF_STATUSES} responses → sleeping {WAF_BACKOFF_SECONDS}s')
                write_status()
                await asyncio.sleep(WAF_BACKOFF_SECONDS)
                waf_streak = 0

            # === Outage detection (NEW) ===
            # Trigger only once window is full (avoid early-run false positives)
            if len(STATE['window_status']) >= OUTAGE_WINDOW:
                window_200 = sum(1 for s in STATE['window_status'] if s == 200)
                if window_200 == 0:
                    outage_pause_count += 1
                    STATE['outage_pauses'] += 1
                    log(f'OUTAGE SIGNATURE: 0/{OUTAGE_WINDOW} sliding-window 200s (expected ~18%). '
                        f'Pause attempt {outage_pause_count}/{OUTAGE_PAUSE_ATTEMPTS}; sleeping {OUTAGE_PAUSE_SECONDS}s.')
                    write_status()
                    if outage_pause_count >= OUTAGE_PAUSE_ATTEMPTS:
                        STATE['halted_by_outage'] = True
                        log('Outage persists past pause threshold → HALT.')
                        write_status()
                        return
                    await asyncio.sleep(OUTAGE_PAUSE_SECONDS)
                    STATE['window_status'].clear()  # fresh window post-pause
                else:
                    outage_pause_count = 0  # reset on any recovery

    write_status()


def write_halt_report(conn: sqlite3.Connection) -> None:
    """Emit final halt-report. Read final counts from the DB itself (source of truth)."""
    cur = conn.cursor()
    # Final counts
    n_recovered = cur.execute(
        'SELECT COUNT(*) FROM hms_fasteign WHERE reprobed_at IS NOT NULL AND http_status=200'
    ).fetchone()[0]
    n_confirmed_500 = cur.execute(
        'SELECT COUNT(*) FROM hms_fasteign WHERE reprobed_at IS NOT NULL AND http_status=500'
    ).fetchone()[0]
    n_remaining = cur.execute(
        'SELECT COUNT(*) FROM hms_fasteign WHERE reprobed_at IS NULL AND http_status=500'
    ).fetchone()[0]
    total_500_orig = n_recovered + n_confirmed_500 + n_remaining
    realized_fn = 100 * n_recovered / max(n_recovered + n_confirmed_500, 1)

    # Per-phase breakdown
    cur.execute("""
        SELECT phase,
               SUM(CASE WHEN reprobed_at IS NOT NULL AND http_status=200 THEN 1 ELSE 0 END) AS rec,
               SUM(CASE WHEN reprobed_at IS NOT NULL AND http_status=500 THEN 1 ELSE 0 END) AS conf,
               SUM(CASE WHEN reprobed_at IS NULL AND http_status=500 THEN 1 ELSE 0 END) AS unt
          FROM hms_fasteign
         WHERE http_status = 500 OR (reprobed_at IS NOT NULL AND http_status=200)
         GROUP BY phase
         ORDER BY phase
    """)
    phase_rows = cur.fetchall()

    # Dead-zone vs healthy-zone breakdown (using canonical UTC windows from DECISIONS.md)
    cur.execute("""
        SELECT
            SUM(CASE WHEN fetched_at >= '2026-05-16T07:00' AND fetched_at < '2026-05-17T21:00'
                     AND reprobed_at IS NOT NULL AND http_status=200 THEN 1 ELSE 0 END) AS dz_rec,
            SUM(CASE WHEN fetched_at >= '2026-05-16T07:00' AND fetched_at < '2026-05-17T21:00'
                     AND reprobed_at IS NOT NULL AND http_status=500 THEN 1 ELSE 0 END) AS dz_conf,
            SUM(CASE WHEN NOT (fetched_at >= '2026-05-16T07:00' AND fetched_at < '2026-05-17T21:00')
                     AND reprobed_at IS NOT NULL AND http_status=200 THEN 1 ELSE 0 END) AS hz_rec,
            SUM(CASE WHEN NOT (fetched_at >= '2026-05-16T07:00' AND fetched_at < '2026-05-17T21:00')
                     AND reprobed_at IS NOT NULL AND http_status=500 THEN 1 ELSE 0 END) AS hz_conf
          FROM hms_fasteign
         WHERE reprobed_at IS NOT NULL
    """)
    dz_rec, dz_conf, hz_rec, hz_conf = cur.fetchone()

    elapsed = (datetime.now(timezone.utc) - STARTED_AT).total_seconds()

    lines = []
    lines.append('# HMS full recovery — halt report')
    lines.append('')
    lines.append(f'**Generated**: {datetime.now(timezone.utc).isoformat(timespec="seconds")}')
    lines.append(f'**Run started**: {STARTED_AT.isoformat(timespec="seconds")}')
    lines.append(f'**Elapsed**: {fmt_dur(elapsed)}')
    lines.append(f'**Target population (start)**: {total_500_orig:,} HTTP-500 rows')
    lines.append('')
    lines.append('## Headline')
    lines.append('')
    lines.append(f'- **Recovered (was 500, now 200)**: **{n_recovered:,}**')
    lines.append(f'- **Confirmed-still-500 (after retry)**: **{n_confirmed_500:,}**')
    lines.append(f'- **Untouched (left in queue)**: **{n_remaining:,}**')
    lines.append(f'- **Realized FN rate**: **{realized_fn:.2f}%** of touched rows')
    lines.append('')
    lines.append('## Per-phase breakdown')
    lines.append('')
    lines.append(f'| Phase | Recovered | Confirmed-500 | Untouched |')
    lines.append(f'|---|---:|---:|---:|')
    for ph, rec, conf, unt in phase_rows:
        lines.append(f'| {ph} | {rec:,} | {conf:,} | {unt:,} |')
    lines.append('')
    lines.append('## Dead-zone vs healthy-zone (by ORIGINAL fetched_at)')
    lines.append('')
    lines.append(f'Dead-zone window: 2026-05-16T07:00 → 2026-05-17T21:00 UTC (~38h)')
    lines.append('')
    lines.append(f'| Zone | Recovered | Confirmed-500 | Realized FN |')
    lines.append(f'|---|---:|---:|---:|')
    dz_touched = (dz_rec or 0) + (dz_conf or 0)
    hz_touched = (hz_rec or 0) + (hz_conf or 0)
    dz_fn = 100 * (dz_rec or 0) / max(dz_touched, 1)
    hz_fn = 100 * (hz_rec or 0) / max(hz_touched, 1)
    lines.append(f'| Dead-zone     | {dz_rec or 0:,} | {dz_conf or 0:,} | {dz_fn:.2f}% |')
    lines.append(f'| Healthy-zone  | {hz_rec or 0:,} | {hz_conf or 0:,} | {hz_fn:.2f}% |')
    lines.append('')
    lines.append('## Run health')
    lines.append('')
    lines.append(f'- WAF pauses:    {STATE["waf_pauses"]}')
    lines.append(f'- Outage pauses: {STATE["outage_pauses"]}')
    if STATE['halted_by_outage']:
        lines.append(f'- **HALTED BY OUTAGE DETECTION** — sliding-window 200-rate stayed at 0% past threshold.')
    elif STATE['halted_by_flag']:
        lines.append(f'- **HALTED BY FLAG** — {HALT_FLAG} touched.')
    elif n_remaining == 0:
        lines.append(f'- Completed cleanly (all targets touched).')
    else:
        lines.append(f'- Partial run — {n_remaining:,} rows still untouched. Re-run to resume.')
    lines.append('')
    lines.append('## Next steps (user decision)')
    lines.append('')
    lines.append(f'- Decide Supabase-sync scope: D3 (originally 30K new properties) now needs to absorb ~{n_recovered:,} additional fastnums.')
    lines.append('- Confirmed-still-500 count ({:,}) sets a new upper bound on truly-empty Phase C slots.'.format(n_confirmed_500))
    lines.append('- Spike-validated production-template hardening (folding outage-detection + 500-aware backoff into the canonical scraper) is now ready — see separate session.')
    lines.append('')

    REPORT_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')


async def main() -> int:
    log(f'HMS full recovery starting at {STARTED_AT.isoformat()}')
    log(f'  python={sys.version.split()[0]}, pid=see process list')

    if not DB_PATH.exists():
        log(f'ERROR: staging DB not found at {DB_PATH}')
        return 2

    if HALT_FLAG.exists():
        log(f'ERROR: HALT flag exists ({HALT_FLAG}). Remove it before starting.')
        return 3

    conn = setup_db()

    # Build target set: shuffle for outage-detection cleanliness (spreads expected-200s evenly)
    cur = conn.cursor()
    cur.execute('SELECT fastnum FROM hms_fasteign WHERE http_status=500 AND reprobed_at IS NULL ORDER BY fastnum')
    targets = [row[0] for row in cur.fetchall()]
    rng = random.Random(SEED)
    rng.shuffle(targets)
    log(f'  Target set: {len(targets):,} fastnums (http_status=500 AND reprobed_at IS NULL)')
    log(f'  Shuffled with seed={SEED} for outage-detection cleanliness.')

    # Also report what's already done (resume case)
    n_already_rec = cur.execute(
        'SELECT COUNT(*) FROM hms_fasteign WHERE reprobed_at IS NOT NULL AND http_status=200'
    ).fetchone()[0]
    n_already_conf = cur.execute(
        'SELECT COUNT(*) FROM hms_fasteign WHERE reprobed_at IS NOT NULL AND http_status=500'
    ).fetchone()[0]
    if n_already_rec or n_already_conf:
        log(f'  Resume: {n_already_rec:,} already recovered, {n_already_conf:,} already confirmed-500')

    if not targets:
        log('Nothing to do — target set empty.')
        write_halt_report(conn)
        conn.close()
        return 0

    # Estimate wall-clock
    # Per-fastnum avg time: 200 case ~1.5s, 500 case ~3s (incl. retry), avg ~2.7s; /3 workers → ~0.9s effective
    est_seconds = len(targets) * 0.9
    log(f'  Estimated wall-clock: ~{est_seconds/3600:.1f} hours at {CONCURRENCY} concurrent workers')
    log(f'  Status updates every {STATUS_INTERVAL_S}s to {STATUS_PATH}')
    log(f'  Halt mechanism: touch {HALT_FLAG} for graceful exit at next batch boundary')

    await run_recovery(conn, targets)

    log('=== Recovery loop ended — writing halt report ===')
    write_halt_report(conn)
    log(f'Report written to {REPORT_PATH}')
    conn.close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        log('Interrupted by user — staging DB is safe (WAL + per-batch commits). Re-launch to resume.')
        sys.exit(130)
