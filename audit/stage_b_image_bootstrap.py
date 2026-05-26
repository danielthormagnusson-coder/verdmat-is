"""
stage_b_image_bootstrap.py — Phase 3 (Áfangi 0 weekend run)

Reads downloaded=0 rows from image_index.db plus newly-discovered image
URLs from Stage A's stage_a_augl_staging.db, fetches each from CloudFront
under the locked storage policy, and updates image_index.

Architecture: bounded queue + 4 worker threads. Each worker has its own
SQLite connection (WAL mode tolerates concurrent writers). Polite 0.1 s
delay per worker between fetches. CloudFront tolerates 4-way parallelism.

Halt rules per task spec:
  - Cloudflare 403 on >5% of requests in rolling 100-fetch window → halt
  - Disk free < 5% → halt
  - Sustained network failure (10 min unable to fetch) → halt

Resume-safety: idempotent. Re-running skips URLs whose image_index row
shows downloaded=1 + file exists.
"""

from __future__ import annotations

import json
import queue
import shutil
import sqlite3
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from weekend_run_status import get_writer  # noqa: E402
from image_archive import (  # noqa: E402
    INDEX_DB_PATH, CANONICAL_IMAGE_ROOT, CF_RE,
    download_image_to_disk,
)

AUDIT_DIR = Path(__file__).resolve().parent
STAGE_A_DB = AUDIT_DIR / "stage_a_augl_staging.db"

NUM_WORKERS = 4
INTER_FETCH_DELAY_S = 0.1
QUEUE_CAPACITY = 5000
DISK_FREE_THRESHOLD = 0.05
HALT_5XX_RATE = 0.05
HALT_ROLLING_WINDOW = 100
SUSTAINED_NET_FAIL_S = 600


class HaltFlag:
    def __init__(self):
        self.flag = threading.Event()
        self.reason = None

    def set(self, reason):
        if not self.flag.is_set():
            self.reason = reason
            self.flag.set()

    def is_set(self):
        return self.flag.is_set()


def discover_urls_from_stage_a(idx_conn, sw):
    """Walk Stage A staging payloads, extract any CloudFront URLs not yet in image_index,
    insert them as downloaded=0 placeholders so the worker pool can drain them.
    Returns count of inserts."""
    if not STAGE_A_DB.exists():
        sw.log("WARN", f"Stage A DB missing — skipping URL discovery: {STAGE_A_DB}")
        return 0
    sa = sqlite3.connect(STAGE_A_DB, timeout=30)
    sa.execute("PRAGMA query_only=ON")
    inserted = 0
    rows_seen = 0
    cur = sa.execute(
        "SELECT fastnum, augl_json FROM stage_a_augl "
        "WHERE augl_status=200 AND augl_json IS NOT NULL AND length(augl_json) > 50"
    )
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    BATCH = 1000
    for row in cur:
        rows_seen += 1
        fn_referencing, aj = row
        try:
            inner = json.loads(json.loads(aj).get("data") or "")
        except Exception:
            continue
        blob = json.dumps(inner, ensure_ascii=False, default=str)
        seen_urls = set()
        for src_fn_str, basename in CF_RE.findall(blob):
            src_fn = int(src_fn_str)
            url = f"https://d1u57vh96em4i1.cloudfront.net/{src_fn_str}/{basename}"
            if url in seen_urls:
                continue
            seen_urls.add(url)
            # Check + insert (idempotent on (fastnum, image_nr))
            existing = idx_conn.execute(
                "SELECT 1 FROM image_index WHERE original_url=?", (url,)
            ).fetchone()
            if existing:
                continue
            nr = idx_conn.execute(
                "SELECT COALESCE(MAX(image_nr), 0) + 1 FROM image_index WHERE fastnum=?",
                (src_fn,)
            ).fetchone()[0]
            try:
                idx_conn.execute(
                    """INSERT INTO image_index
                       (fastnum, image_nr, original_url, local_path, downloaded,
                        source_db, first_seen_at, last_verified_at, file_size_bytes)
                       VALUES (?, ?, ?, ?, 0, 'stage_a_discovery', ?, NULL, NULL)""",
                    (src_fn, nr, url,
                     str(CANONICAL_IMAGE_ROOT / str(src_fn) / f"{nr}.jpg"),
                     now_iso),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                continue
            # cross_property_refs
            if src_fn != fn_referencing:
                idx_conn.execute(
                    """INSERT OR IGNORE INTO cross_property_refs
                       (referencing_fastnum, referenced_fastnum, image_url, augl_id, augl_capture_at)
                       VALUES (?, ?, ?, '—', ?)""",
                    (fn_referencing, src_fn, url, now_iso),
                )
        if rows_seen % BATCH == 0:
            idx_conn.commit()
            sw.log("INFO", f"  url-discovery: scanned {rows_seen:,} stage-A rows, "
                           f"inserted {inserted:,} new image_index rows")
    idx_conn.commit()
    sa.close()
    return inserted


def fetch_worker(worker_id, work_q, halt_flag, sw, stats_lock, stats):
    """One worker: drain (fastnum, url, expected_local_path) tuples."""
    conn = sqlite3.connect(INDEX_DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    rolling = deque(maxlen=HALT_ROLLING_WINDOW)
    last_ok_at = time.monotonic()
    while not halt_flag.is_set():
        try:
            item = work_q.get(timeout=2.0)
        except queue.Empty:
            return
        if item is None:
            work_q.task_done()
            return
        fastnum, url, local_path_expected = item
        dest = Path(local_path_expected)
        ok, nbytes, info = download_image_to_disk(url, dest)
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if ok:
            conn.execute(
                "UPDATE image_index SET downloaded=1, last_verified_at=?, "
                "file_size_bytes=? WHERE fastnum=? AND original_url=?",
                (now_iso, nbytes, fastnum, url),
            )
            conn.commit()
            with stats_lock:
                stats["downloaded"] += 1
                stats["bytes"] += nbytes
            rolling.append(0)
            last_ok_at = time.monotonic()
        else:
            with stats_lock:
                stats["failed"] += 1
            rolling.append(1)
            # Halt-rate check
            if info.startswith("http-403"):
                halt_flag.set(f"worker {worker_id}: 403 on {url}")
                break
            if (sum(rolling) / max(len(rolling), 1)) > HALT_5XX_RATE \
               and len(rolling) >= HALT_ROLLING_WINDOW:
                halt_flag.set(f"worker {worker_id}: failure rate >{HALT_5XX_RATE*100}% "
                              f"in rolling window (info={info})")
                break
            if time.monotonic() - last_ok_at > SUSTAINED_NET_FAIL_S:
                halt_flag.set(f"worker {worker_id}: sustained fail >{SUSTAINED_NET_FAIL_S}s")
                break
        work_q.task_done()
        time.sleep(INTER_FETCH_DELAY_S)
    conn.close()


def main():
    sw = get_writer()
    sw.start()
    try:
        sw.set_phase("phase_3_stage_b_image_bootstrap")
        sw.set_subphase("discover URLs from Stage A staging")
        sw.log("INFO", f"Phase 3 starting; index_db={INDEX_DB_PATH}")

        idx = sqlite3.connect(INDEX_DB_PATH, timeout=30)
        idx.execute("PRAGMA journal_mode=WAL")

        # 1) discover new URLs from Stage A payloads
        new_urls = discover_urls_from_stage_a(idx, sw)
        sw.log("INFO", f"discovered {new_urls:,} new image_index rows from Stage A")

        # 2) build work queue from all downloaded=0 rows
        sw.set_subphase("build work queue")
        rows = idx.execute(
            "SELECT fastnum, original_url, local_path FROM image_index WHERE downloaded=0"
        ).fetchall()
        idx.close()
        total = len(rows)
        sw.log("INFO", f"queued {total:,} downloaded=0 rows for fetch")
        sw.set_progress(0, total)

        if total == 0:
            sw.log("INFO", "nothing to fetch; Phase 3 complete")
            sw.complete_phase("phase_3_stage_b_image_bootstrap")
            return 0

        # 3) start 4 workers
        sw.set_subphase(f"4-way parallel fetch ({NUM_WORKERS} workers)")
        work_q = queue.Queue(maxsize=QUEUE_CAPACITY)
        halt_flag = HaltFlag()
        stats = {"downloaded": 0, "failed": 0, "bytes": 0}
        stats_lock = threading.Lock()

        workers = []
        for i in range(NUM_WORKERS):
            t = threading.Thread(
                target=fetch_worker,
                args=(i, work_q, halt_flag, sw, stats_lock, stats),
                daemon=True, name=f"fetcher-{i}",
            )
            t.start()
            workers.append(t)

        # 4) feeder
        started = time.monotonic()
        for i, (fn, url, lp) in enumerate(rows):
            if halt_flag.is_set():
                break
            work_q.put((fn, url, lp))
            if i % 200 == 0:
                with stats_lock:
                    done = stats["downloaded"] + stats["failed"]
                elapsed = time.monotonic() - started
                rate = (done / elapsed) * 60 if elapsed > 0 else 0
                sw.set_progress(done, total, rate)
                # Disk check
                if i % 1000 == 0:
                    free = shutil.disk_usage("D:\\")
                    if free.free / free.total < DISK_FREE_THRESHOLD:
                        halt_flag.set(f"disk-low: {free.free/1024**3:.1f} GB free")
                        break

        # 5) drain
        for _ in workers:
            work_q.put(None)
        for t in workers:
            t.join(timeout=300)

        if halt_flag.is_set():
            sw.add_halt(f"phase 3: {halt_flag.reason}")
            return 4

        sw.complete_phase("phase_3_stage_b_image_bootstrap")
        sw.log("INFO", f"Phase 3 COMPLETE downloaded={stats['downloaded']:,} "
                       f"failed={stats['failed']:,} bytes={stats['bytes']:,}")
        return 0
    finally:
        sw.stop()


if __name__ == "__main__":
    sys.exit(main())
