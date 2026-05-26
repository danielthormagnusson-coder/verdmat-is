"""HMS Fasteignaskrá full scrape: Phase A -> B -> C, single process, resume-safe.

Phase A (~11,000 requests, ~1h): backfill fastnums known-real but missing from Supabase
  - kaupskra ∖ properties (1,527 confirmed-missing)
  - integers inside mid-size gaps (200..1000 wide) in (Supabase ∪ kaupskra)

Phase B (~125,000 requests, ~11h): enrich every existing Supabase property with HMS data
  - Adds lhlmat, brunabotamat, matseiningar[], byggingarstig, etc. — new model features.

Phase C (~405,000 requests, ~38h): fill remaining integers in span 2,000,044..2,547,000
  - Mostly admin-empty slots (the 122K-wide 2.4M bucket alone is in here).
  - Lowest priority; pre-empt by killing the process if time runs out.

Output: D:\\verdmat-is\\app\\audit\\hms_archive_staging.db (one row per fastnum)
Status:  D:\\verdmat-is\\app\\audit\\hms_full_scrape_status.md (rewritten every batch)
Log:     D:\\verdmat-is\\app\\audit\\hms_full_scrape.log (append-only)

Resume: re-launch the same script. It rebuilds the target sets and skips any
fastnum already present in the staging DB.

Requires: curl_cffi (TLS impersonation — bypasses hms.is Cloudflare WAF that
blocks plain aiohttp/Invoke-WebRequest).
"""
from __future__ import annotations

import asyncio
import json
import random
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from curl_cffi.requests import AsyncSession

AUDIT = Path(__file__).resolve().parent
DB_PATH = AUDIT / 'hms_archive_staging.db'
STATUS_PATH = AUDIT / 'hms_full_scrape_status.md'
LOG_PATH = AUDIT / 'hms_full_scrape.log'
SB_PATH = AUDIT / 'supabase_fastnums.txt'
KAUP_PATH = AUDIT / 'known_real_fastnums.txt'

API = 'https://hms.is/api/fasteignaskra/fasteign'
MIN_FN = 2_000_044
MAX_FN = 2_547_000  # legacy max 2,542,139 + small buffer for recent issuance
CONCURRENCY = 3
PER_WORKER_DELAY = 1.0
JITTER = 0.4
BATCH_SIZE = 200
WAF_BACKOFF_STREAK = 10
WAF_BACKOFF_SECONDS = 300
STATUS_INTERVAL_S = 30

STARTED_AT = datetime.now(timezone.utc)


def log(msg: str) -> None:
    line = f'[{datetime.now(timezone.utc).isoformat(timespec="seconds")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def setup_db() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=60, isolation_level=None)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=NORMAL')
    c.execute('PRAGMA temp_store=MEMORY')
    c.execute('''
        CREATE TABLE IF NOT EXISTS hms_fasteign (
          fastnum         INTEGER PRIMARY KEY,
          http_status     INTEGER NOT NULL,
          fasteign_data   TEXT,
          fetched_at      TEXT NOT NULL,
          phase           TEXT NOT NULL,
          exists_in_hms   INTEGER NOT NULL
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_exists ON hms_fasteign(exists_in_hms)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_phase ON hms_fasteign(phase)')
    return c


def build_targets(sb: set[int], known: set[int], done: set[int]):
    """Return (remaining_A, remaining_B, remaining_C, full_A_size, full_B_size, full_C_size)."""
    populated = sorted(sb | known)
    mid_gap_ints: set[int] = set()
    for a, b in zip(populated, populated[1:]):
        g = b - a - 1
        if 200 <= g <= 1000:
            mid_gap_ints.update(range(a + 1, b))

    phase_a_full = (known - sb) | mid_gap_ints
    phase_b_full = set(sb)
    full_span = set(range(MIN_FN, MAX_FN + 1))
    phase_c_full = full_span - sb - known - mid_gap_ints

    return (
        sorted(phase_a_full - done),
        sorted(phase_b_full - done),
        sorted(phase_c_full - done),
        len(phase_a_full),
        len(phase_b_full),
        len(phase_c_full),
    )


STATE = {
    'phase': None,
    'phase_started': None,
    'done': 0,
    'total': 0,
    'rate_per_min': 0.0,
    'status_counts': Counter(),
    'overall_counts': Counter(),
    'halt': None,
}


def fmt_dur(seconds: float) -> str:
    s = int(max(seconds, 0))
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    if h:
        return f'{h}h {m}m {s}s'
    if m:
        return f'{m}m {s}s'
    return f'{s}s'


def write_status() -> None:
    now = datetime.now(timezone.utc)
    elapsed_phase = (now - STATE['phase_started']).total_seconds() if STATE['phase_started'] else 0
    rate = STATE['done'] / max(elapsed_phase, 1) * 60
    STATE['rate_per_min'] = round(rate, 1)
    pct = (STATE['done'] / STATE['total'] * 100) if STATE['total'] else 0
    eta_sec = ((STATE['total'] - STATE['done']) / max(rate / 60, 1e-6)) if rate > 0 else 0
    elapsed_overall = (now - STARTED_AT).total_seconds()

    lines = [
        '# HMS full-scrape status',
        '',
        f"**Updated:** {now.isoformat(timespec='seconds')}",
        f"**Run started:** {STARTED_AT.isoformat(timespec='seconds')}",
        f"**Total elapsed:** {fmt_dur(elapsed_overall)}",
        '',
        f"## Phase {STATE['phase']}",
        f"- Progress: {STATE['done']:,} / {STATE['total']:,} ({pct:.1f}%)",
        f"- Rate: {STATE['rate_per_min']:.1f}/min",
        f"- ETA (current phase): {fmt_dur(eta_sec)}",
        '',
        '## Current-phase status code distribution',
    ]
    for sc, n in sorted(STATE['status_counts'].items()):
        label = {200: 'real property', 500: 'not exists',
                 429: 'RATE LIMITED', 403: 'BLOCKED', 503: 'UNAVAILABLE',
                 -1: 'exception'}.get(sc, f'HTTP {sc}')
        lines.append(f'- {sc} ({label}): {n:,}')

    if STATE['overall_counts']:
        lines += ['', '## Overall (all phases) status counts']
        for sc, n in sorted(STATE['overall_counts'].items()):
            label = {200: 'real property', 500: 'not exists'}.get(sc, f'HTTP {sc}')
            lines.append(f'- {sc} ({label}): {n:,}')

    if STATE['halt']:
        lines += ['', '## HALT', STATE['halt']]

    STATUS_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')


async def fetch_one(sem: asyncio.Semaphore, session: AsyncSession, nr: int):
    async with sem:
        try:
            r = await session.get(f'{API}/{nr}', timeout=20)
            sc = r.status_code
            data = None
            if sc == 200:
                try:
                    j = r.json()
                    fd = j.get('fasteignData') if isinstance(j, dict) else None
                    if fd is not None:
                        data = json.dumps(fd, ensure_ascii=False)
                except Exception:
                    data = r.text[:5000] if r.text else None
            return nr, sc, data
        except Exception as e:
            return nr, -1, f'EXC:{type(e).__name__}:{str(e)[:200]}'
        finally:
            await asyncio.sleep(PER_WORKER_DELAY + random.uniform(-JITTER, JITTER))


async def run_phase(phase_name: str, targets: list[int], conn: sqlite3.Connection) -> None:
    STATE['phase'] = phase_name
    STATE['phase_started'] = datetime.now(timezone.utc)
    STATE['done'] = 0
    STATE['total'] = len(targets)
    STATE['status_counts'] = Counter()
    write_status()

    if not targets:
        log(f'Phase {phase_name}: 0 fastnums remaining (already complete)')
        return

    log(f'=== Phase {phase_name}: {len(targets):,} fastnums to fetch ===')
    sem = asyncio.Semaphore(CONCURRENCY)
    rate_limit_streak = 0
    last_status = time.time()

    async with AsyncSession(impersonate='chrome120') as session:
        for batch_start in range(0, len(targets), BATCH_SIZE):
            batch = targets[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*(fetch_one(sem, session, nr) for nr in batch))
            now_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')

            rows = []
            for nr, sc, data in results:
                rows.append((nr, sc, data, now_iso, phase_name, 1 if sc == 200 else 0))
                STATE['status_counts'][sc] += 1
                STATE['overall_counts'][sc] += 1
                if sc in (429, 403, 503):
                    rate_limit_streak += 1
                else:
                    rate_limit_streak = 0

            conn.executemany(
                '''
                INSERT INTO hms_fasteign (fastnum, http_status, fasteign_data, fetched_at, phase, exists_in_hms)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(fastnum) DO UPDATE SET
                  http_status=excluded.http_status,
                  fasteign_data=excluded.fasteign_data,
                  fetched_at=excluded.fetched_at,
                  phase=excluded.phase,
                  exists_in_hms=excluded.exists_in_hms
                ''',
                rows,
            )

            STATE['done'] += len(batch)

            if time.time() - last_status > STATUS_INTERVAL_S:
                write_status()
                log(
                    f'Phase {phase_name}: {STATE["done"]:,}/{STATE["total"]:,} '
                    f'({STATE["status_counts"][200]:,} hits, '
                    f'{STATE["status_counts"][500]:,} empty) '
                    f'rate={STATE["rate_per_min"]:.1f}/min'
                )
                last_status = time.time()

            if rate_limit_streak >= WAF_BACKOFF_STREAK:
                STATE['halt'] = (
                    f'WAF backoff: {rate_limit_streak} consecutive rate-limit responses; '
                    f'sleeping {WAF_BACKOFF_SECONDS}s'
                )
                write_status()
                log(STATE['halt'])
                await asyncio.sleep(WAF_BACKOFF_SECONDS)
                rate_limit_streak = 0
                STATE['halt'] = None

    write_status()
    hits = STATE['status_counts'][200]
    hit_pct = 100 * hits / max(STATE['done'], 1)
    log(f'=== Phase {phase_name} complete: {STATE["done"]:,} fetched, '
        f'{hits:,} hits ({hit_pct:.1f}%) ===')


async def main() -> int:
    log(f'HMS full scrape starting at {STARTED_AT.isoformat()}')
    log(f'  python={sys.version.split()[0]}, pid={Path("/proc/self").exists() and "—" or "see process list"}')

    if not SB_PATH.exists() or not KAUP_PATH.exists():
        log(f'ERROR: missing target lists: {SB_PATH} and/or {KAUP_PATH}')
        return 2

    conn = setup_db()

    log('Loading target sets...')
    sb = set(int(x) for x in SB_PATH.read_text(encoding='utf-8').split() if x.strip())
    known = set(int(x) for x in KAUP_PATH.read_text(encoding='utf-8').split() if x.strip())
    done = set(r[0] for r in conn.execute('SELECT fastnum FROM hms_fasteign'))
    log(f'  Supabase fastnums:   {len(sb):,}')
    log(f'  Known-real (kaupskra+legacy): {len(known):,}')
    log(f'  Already in staging:  {len(done):,}')

    a_rem, b_rem, c_rem, a_full, b_full, c_full = build_targets(sb, known, done)
    total_rem = len(a_rem) + len(b_rem) + len(c_rem)
    eta_sec = total_rem / CONCURRENCY  # 1 req/s per worker
    log(f'  Phase A remaining: {len(a_rem):>7,} / {a_full:>7,}')
    log(f'  Phase B remaining: {len(b_rem):>7,} / {b_full:>7,}')
    log(f'  Phase C remaining: {len(c_rem):>7,} / {c_full:>7,}')
    log(f'  Total remaining:   {total_rem:>7,}  (est wall-clock {fmt_dur(eta_sec)} at {CONCURRENCY} req/s)')

    # Backfill overall_counts from prior runs so the status surface is honest
    for sc, n in conn.execute('SELECT http_status, COUNT(*) FROM hms_fasteign GROUP BY http_status'):
        STATE['overall_counts'][sc] = n

    await run_phase('A', a_rem, conn)
    await run_phase('B', b_rem, conn)
    await run_phase('C', c_rem, conn)

    log('=== All phases complete ===')
    log('Final per-phase status counts:')
    for ph, sc, n in conn.execute(
        'SELECT phase, http_status, COUNT(*) FROM hms_fasteign GROUP BY phase, http_status ORDER BY 1, 2'
    ):
        log(f'  Phase {ph} HTTP {sc}: {n:,}')
    conn.close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        log('Interrupted by user — staging DB is safe, re-launch to resume.')
        sys.exit(130)
