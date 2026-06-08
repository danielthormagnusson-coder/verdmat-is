"""fetch_visir — Step 2b P2 visir raw fetcher (hybrid index + detail).

SCRAPER_SPEC_v2 §2.1 raw layer for visir. Index-sweep enumerates listing ids via the
LOCKED endpoint `/ajaxsearch/getresults?stype=<stype>&page=<N>` (Phase 1c), per stype in
{sale, rent} (company + vessel are empty shells on visir). Detail-walk fetches the full
SSR `/property/{id}` HTML. Every fetch lands in raw_visir.db as a content-addressable blob
(verbatim gzip) + an append-only ledger row, with content-hash idempotency where the hash
is computed on the §2.1.1-CANONICALIZED body (canonicalize_visir: ad-redirect/ad-block
stripping) so rotating ads cannot defeat dedup.

NO parsing, NO Supabase, NO canonical promotion — that is Step 2c+.

CLI:
    python fetch_visir.py                    # docstring + exit 0 (no crawl without --confirm)
    python fetch_visir.py --confirm          # FULL crawl (multi-hour)
    python fetch_visir.py --confirm --test   # smoke: 1 page/stype, max 10 details
    [--max-pages N] [--delay-sec S] [--stypes sale,rent]

Timestamp convention (binding, §2.1): every ISO8601 string comes from
datetime.now(timezone.utc).isoformat() at the Python call-site. Never SQL CURRENT_TIMESTAMP.

deps: stdlib + requests + canonicalize_visir (+ its bs4/lxml).
"""
from __future__ import annotations

import argparse
import gzip
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path          # noqa: E402
from canonicalize_visir import content_hash_visir  # noqa: E402

BASE_URL = "https://fasteignir.visir.is"
GETRESULTS = "/ajaxsearch/getresults"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
DEFAULT_DELAY_S = 2.0
DEFAULT_MAX_PAGES = 200
DEFAULT_STYPES = ("sale", "rent")
TIMEOUT_S = 30
MAX_ATTEMPTS = 3                 # internal retries on timeout / 5xx
BACKOFF = (1, 2, 4)
TIMEOUT_KILL_THRESHOLD = 3       # >3 consecutive failed fetches -> dead host
MAX_CONSECUTIVE_400 = 3          # visir soft-throttles with HTTP 400 (Step 2b crawl finding)
DEFAULT_REPRIME_EVERY = 80       # re-prime session every N details (below ~170 throttle threshold)
TEST_DETAIL_CAP = 10

_PROPERTY_RE = re.compile(r"/property/(\d+)")
_CAPTCHA_MARKERS = ("cf-challenge", "just a moment", "attention required",
                    "/cdn-cgi/challenge", "verify you are human")


class KillSwitch(RuntimeError):
    """Tripped on 403/429, CAPTCHA body, or sustained timeouts → exit 2."""


class SchemaMissing(RuntimeError):
    """raw_visir.db has no raw_blobs/raw_fetches — run init_raw_visir_schema.py first."""


@dataclass
class HttpResult:
    status: "int | None"
    body: bytes
    text: str
    content_type: str
    timed_out: bool = False
    captcha: bool = False


@dataclass
class RunStats:
    pages_fetched: int = 0
    ids_found_total: int = 0
    detail_fetches: int = 0
    new_blobs: int = 0
    dedup_hits: int = 0          # changed=0
    changed_1: int = 0
    http_4xx: int = 0
    http_5xx: int = 0
    failures: int = 0            # status NULL / timeouts recorded
    total_uncompressed: int = 0
    total_compressed: int = 0
    elapsed_sec: float = 0.0


# ───────────────────────────────────────────────────────────── pure helpers
def extract_listing_ids(html_text: str) -> list:
    """Return ordered, de-duped /property/{id} ids (as str) from a getresults fragment."""
    seen, out = set(), []
    for m in _PROPERTY_RE.finditer(html_text or ""):
        i = m.group(1)
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def verify_schema(conn) -> bool:
    rows = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    return {"raw_blobs", "raw_fetches"}.issubset(rows)


def _is_captcha(text: str) -> bool:
    low = (text or "")[:4000].lower()
    return any(m in low for m in _CAPTCHA_MARKERS)


# ──────────────────────────────────────────────────────────────── fetcher
class VisirFetcher:
    def __init__(self, session, conn, *, delay=DEFAULT_DELAY_S, max_pages=DEFAULT_MAX_PAGES,
                 stypes=DEFAULT_STYPES, test=False, log=print):
        self.s = session
        self.conn = conn
        self.delay = delay
        self.max_pages = max_pages
        self.stypes = tuple(stypes)
        self.test = test
        self.log = log
        self.stats = RunStats()
        self._consec_timeouts = 0
        self._consec_400 = 0                       # visir throttle signal (Patch 1)
        self.requests_since_prime = 0              # unified re-prime cadence (Patch 2, both phases)
        self.REPRIME_EVERY = DEFAULT_REPRIME_EVERY

    # -- HTTP -------------------------------------------------------------
    def _get(self, url: str) -> HttpResult:
        attempts = 0
        while attempts < MAX_ATTEMPTS:
            attempts += 1
            try:
                r = self.s.get(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
                               timeout=TIMEOUT_S)
            except requests.RequestException:
                if attempts < MAX_ATTEMPTS:
                    time.sleep(BACKOFF[attempts - 1])
                    continue
                return HttpResult(None, b"", "", "", timed_out=True)
            status = r.status_code
            body = r.content or b""
            text = r.text or ""
            ctype = (r.headers.get("content-type") or "text/html").split(";")[0].strip() or "text/html"
            if status in (500, 502, 503, 504) and attempts < MAX_ATTEMPTS:
                time.sleep(BACKOFF[attempts - 1])
                continue
            return HttpResult(status, body, text, ctype,
                              captcha=(status == 200 and "html" in ctype and _is_captcha(text)))
        return HttpResult(None, b"", "", "", timed_out=True)

    def _guard(self, res: HttpResult, url: str):
        """Kill-switch gate. Caller records the ledger row BEFORE calling this."""
        if res.status in (403, 429):
            raise KillSwitch("HTTP %s on %s" % (res.status, url))
        if res.captcha:
            raise KillSwitch("CAPTCHA/challenge body on %s" % url)
        # visir soft-throttles sustained crawling with HTTP 400 (not 403/429) — halt on a
        # short run of consecutive 400s instead of hammering through them (Step 2b finding).
        if res.status == 400:
            self._consec_400 += 1
            if self._consec_400 >= MAX_CONSECUTIVE_400:
                raise KillSwitch("%d consecutive HTTP 400 — likely throttle on %s"
                                 % (self._consec_400, url))
        elif res.status == 200:
            self._consec_400 = 0
        if res.timed_out:
            self._consec_timeouts += 1
            if self._consec_timeouts > TIMEOUT_KILL_THRESHOLD:
                raise KillSwitch("%d consecutive timeouts (dead host)" % self._consec_timeouts)
        else:
            self._consec_timeouts = 0

    # -- DB writes --------------------------------------------------------
    def _changed(self, kind, slid, url, new_hash):
        if slid is not None:
            row = self.conn.execute(
                "SELECT content_hash FROM raw_fetches WHERE source='visir' AND fetch_kind=? "
                "AND source_listing_id=? ORDER BY fetched_at DESC, raw_id DESC LIMIT 1",
                (kind, slid)).fetchone()
        else:
            row = self.conn.execute(
                "SELECT content_hash FROM raw_fetches WHERE source='visir' AND fetch_kind=? "
                "AND source_listing_id IS NULL AND url=? ORDER BY fetched_at DESC, raw_id DESC LIMIT 1",
                (kind, url)).fetchone()
        prev = row[0] if row else None
        if prev is not None and prev == new_hash:
            return 0, "skipped_unchanged"
        return 1, "pending"

    def _record_success(self, kind, slid, url, status, body, content_type):
        h = content_hash_visir(body, content_type)        # §2.1.1 canonicalized hash
        body_gz = gzip.compress(body)                      # VERBATIM blob
        changed, parse_status = self._changed(kind, slid, url, h)
        new_blob = self.conn.execute(
            "SELECT 1 FROM raw_blobs WHERE content_hash=?", (h,)).fetchone() is None
        fetched_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR IGNORE INTO raw_blobs(content_hash, blob_gz, content_type, byte_len, first_stored) "
            "VALUES(?,?,?,?,?)", (h, body_gz, content_type, len(body), fetched_at))
        self.conn.execute(
            "INSERT INTO raw_fetches(source, source_listing_id, url, fetch_kind, fetched_at, "
            "http_status, content_hash, changed, retry_count, parse_status) "
            "VALUES('visir',?,?,?,?,?,?,?,0,?)",
            (slid, url, kind, fetched_at, status, h, changed, parse_status))
        self.conn.commit()
        self.stats.total_uncompressed += len(body)
        self.stats.total_compressed += len(body_gz)
        if new_blob:
            self.stats.new_blobs += 1
        if changed:
            self.stats.changed_1 += 1
        else:
            self.stats.dedup_hits += 1
        return changed, new_blob

    def _record_failure(self, kind, slid, url, status):
        fetched_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO raw_fetches(source, source_listing_id, url, fetch_kind, fetched_at, "
            "http_status, content_hash, changed, retry_count, parse_status) "
            "VALUES('visir',?,?,?,?,?,NULL,0,0,'failed')",
            (slid, url, kind, fetched_at, status))
        self.conn.commit()
        self.stats.failures += 1
        if status is not None and 400 <= status < 500:
            self.stats.http_4xx += 1
        elif status is not None and 500 <= status < 600:
            self.stats.http_5xx += 1

    # -- phases -----------------------------------------------------------
    def index_sweep(self) -> list:
        """Phase A: per-stype getresults pagination. Returns ordered unique ids (all stypes)."""
        all_ids = {}        # id -> None (ordered set)
        self.log("--- Phase A: index sweep (stypes=%s, max_pages=%s%s) ---"
                 % (",".join(self.stypes), self.max_pages, ", TEST" if self.test else ""))
        for stype in self.stypes:
            seen_for_stype = set()
            page = 1
            while page <= self.max_pages:
                self._maybe_reprime()
                url = "%s%s?stype=%s&page=%d" % (BASE_URL, GETRESULTS, stype, page)
                res = self._get(url)
                if res.status == 200 and res.body:
                    self._record_success("index", None, url, res.status, res.body, res.content_type)
                    self._guard(res, url)
                    ids = extract_listing_ids(res.text)
                    new = [i for i in ids if i not in seen_for_stype]
                    seen_for_stype.update(ids)
                    for i in ids:
                        all_ids.setdefault(i, None)
                    self.stats.pages_fetched += 1
                    self.log("  stype=%-6s page=%d ids_found=%d new_ids=%d"
                             % (stype, page, len(ids), len(new)))
                    if not new:                       # exhausted: nothing beyond already-seen
                        self.log("  stype=%-6s exhausted at page %d (0 new ids)" % (stype, page))
                        break
                else:
                    self._record_failure("index", None, url, res.status)
                    self._guard(res, url)
                    self.log("  stype=%-6s page=%d non-200 (status=%s) — stopping stype"
                             % (stype, page, res.status))
                    break
                if self.test:
                    self.log("  [test] capping stype=%s at 1 page" % stype)
                    break
                time.sleep(self.delay)
                page += 1
            time.sleep(self.delay)
        self.stats.ids_found_total = len(all_ids)
        return list(all_ids.keys())

    def detail_walk(self, ids: list):
        """Phase B: GET /property/{id} per unique id."""
        if self.test:
            ids = ids[:TEST_DETAIL_CAP]
        self.log("--- Phase B: detail walk (%d ids%s) ---"
                 % (len(ids), ", TEST cap" if self.test else ""))
        for n, lid in enumerate(ids, 1):
            self._maybe_reprime()      # unified counter — refresh session before throttle (both phases)
            url = "%s/property/%s" % (BASE_URL, lid)
            res = self._get(url)
            if res.status == 200 and res.body:
                changed, new_blob = self._record_success(
                    "detail", str(lid), "/property/%s" % lid, res.status, res.body, res.content_type)
                self._guard(res, url)
            else:
                self._record_failure("detail", str(lid), "/property/%s" % lid, res.status)
                self._guard(res, url)
            self.stats.detail_fetches += 1
            if n % 25 == 0:
                self.log("  ...detail progress %d/%d" % (n, len(ids)))
            time.sleep(self.delay)

    def prime(self):
        """One cookie-priming GET; body discarded, not recorded in the ledger."""
        try:
            self.s.get("%s/search/results/?stype=sale" % BASE_URL,
                       headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)
            self.log("  session primed (/search/results/?stype=sale)")
        except requests.RequestException:
            self.log("  prime call failed (non-fatal; getresults works without cookie)")
        self.requests_since_prime = 0              # the prime call itself doesn't count

    def _maybe_reprime(self):
        """Refresh the session every REPRIME_EVERY requests (across BOTH phases) — visir
        throttles a session at ~170 requests (Step 2b crawl finding). Call before each fetch."""
        if self.requests_since_prime >= self.REPRIME_EVERY:
            self.log("  re-priming session at request #%d" % self.requests_since_prime)
            self.prime()                           # resets requests_since_prime to 0
        self.requests_since_prime += 1

    def run(self, ids=None):
        """Crawl. If `ids` is given (explicit list), skip Phase A and detail-walk those
        ids directly (deterministic same-id re-fetch / prod re-check). Otherwise sweep."""
        if not verify_schema(self.conn):
            raise SchemaMissing(
                "raw_visir.db missing raw_blobs/raw_fetches — run init_raw_visir_schema.py first")
        t0 = time.perf_counter()
        if ids:
            self.log("=== visir fetch: EXPLICIT IDS (%d) ===" % len(ids))
            self.prime()
            # --ids is the scope: the test detail-cap does not apply.
            was_test, self.test = self.test, False
            try:
                self.detail_walk([str(i) for i in ids])
            finally:
                self.test = was_test
        else:
            self.log("=== visir fetch: %s ===" % ("SMOKE TEST" if self.test else "FULL CRAWL"))
            self.prime()
            swept = self.index_sweep()
            self.detail_walk(swept)
        self.stats.elapsed_sec = time.perf_counter() - t0
        self._summary()
        return self.stats

    def _summary(self):
        s = self.stats
        ratio = (s.total_compressed / s.total_uncompressed) if s.total_uncompressed else 0.0
        self.log("\n=== END-OF-RUN SUMMARY ===")
        self.log("  pages_fetched     : %d" % s.pages_fetched)
        self.log("  ids_found_total   : %d" % s.ids_found_total)
        self.log("  detail_fetches    : %d" % s.detail_fetches)
        self.log("  new_blobs         : %d" % s.new_blobs)
        self.log("  changed=1         : %d" % s.changed_1)
        self.log("  changed=0 (dedup) : %d" % s.dedup_hits)
        self.log("  failures          : %d  (4xx=%d 5xx=%d)" % (s.failures, s.http_4xx, s.http_5xx))
        self.log("  bytes raw/gzip    : %d / %d  (ratio %.3f)"
                 % (s.total_uncompressed, s.total_compressed, ratio))
        self.log("  elapsed_sec       : %.1f" % s.elapsed_sec)


# ──────────────────────────────────────────────────────────────────── main
def main():
    ap = argparse.ArgumentParser(description="visir raw fetcher (hybrid index + detail)")
    ap.add_argument("--confirm", action="store_true", help="actually crawl (required)")
    ap.add_argument("--test", action="store_true", help="smoke: 1 page/stype, max 10 details")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    ap.add_argument("--delay-sec", type=float, default=DEFAULT_DELAY_S)
    ap.add_argument("--stypes", type=str, default="sale,rent")
    ap.add_argument("--ids", type=str, default="",
                    help="comma-separated listing ids; detail-walk only (skip index sweep)")
    args = ap.parse_args()

    if not args.confirm:
        print(__doc__)
        print("\nThis crawls fasteignir.visir.is live. Re-invoke with --confirm (add --test for a smoke run).")
        return 0

    stypes = tuple(s.strip() for s in args.stypes.split(",") if s.strip())
    db_path = get_raw_db_path("visir")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    print("DB: %s" % db_path)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    fetcher = VisirFetcher(session, conn, delay=args.delay_sec, max_pages=args.max_pages,
                           stypes=stypes, test=args.test)
    explicit_ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    try:
        fetcher.run(ids=explicit_ids or None)
    except SchemaMissing as e:
        print("SCHEMA ERROR: %s" % e)
        return 1
    except KillSwitch as e:
        print("\n!! KILL-SWITCH: %s" % e)
        fetcher._summary()
        return 2
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
