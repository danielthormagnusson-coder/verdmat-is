"""Unit tests for fetch_visir. stdlib unittest, NO pytest. No live HTTP — a FakeSession
is injected into VisirFetcher and an in-memory SQLite carries the §2.1 schema.

    python -m unittest scripts.fetch_visir_test -v
"""
from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_visir as fv                  # noqa: E402
import init_raw_visir_schema as initv     # noqa: E402

import requests  # noqa: E402

REAL_GETRESULTS = Path(
    r"D:\verdmat-is\scraper_data\probe_visir_samples\search_endpoint_ajaxsearch_getresults_sale.html")

LISTING = ('<div class="listing"><h1>Bær 1, 101 Rvk</h1>'
           '<span class="price">{price} kr.</span>'
           '<span class="fastnum">fasteignanúmer: 1021848</span></div>')


def getresults_html(ids):
    links = "".join('<a href="/property/%s">x</a>' % i for i in ids)
    return ("<html><body><div id='inner-result-placeholder'>%s</div></body></html>" % links).encode("utf-8")


def detail_html(price="99.900.000", ad_id="111", ad_img="/a.jpg"):
    ad = ('<div class="ad-banner-mobile"><a href="/ads/redirect/%s">'
          '<img src="%s"></a></div>' % (ad_id, ad_img))
    return ("<html><body>%s%s</body></html>" % (LISTING.format(price=price), ad)).encode("utf-8")


class FakeResponse:
    def __init__(self, status_code, content=b"", content_type="text/html"):
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}

    @property
    def text(self):
        return self.content.decode("utf-8", "replace")


class FakeSession:
    """handler(url, call_idx) -> FakeResponse | Exception(raised)."""
    def __init__(self, handler):
        self.handler = handler
        self.calls = []
        self.headers = {}

    def get(self, url, **kw):
        idx = len(self.calls)
        self.calls.append(url)
        r = self.handler(url, idx)
        if isinstance(r, Exception):
            raise r
        return r


def mem_conn(with_schema=True):
    c = sqlite3.connect(":memory:")
    if with_schema:
        c.executescript(initv.RAW_BLOBS_DDL + initv.RAW_FETCHES_DDL)
        c.execute(initv.IX_LISTING)
        c.execute(initv.IX_PARSE)
    return c


def silent(*a, **k):
    pass


class TestFetchVisir(unittest.TestCase):

    # T1 — extract ids from the real getresults sample.
    def test_t1_extract_listing_ids_from_getresults(self):
        if not REAL_GETRESULTS.is_file():
            self.skipTest("real getresults sample not present")
        ids = fv.extract_listing_ids(REAL_GETRESULTS.read_text(encoding="utf-8", errors="replace"))
        self.assertGreaterEqual(len(ids), 5)
        self.assertTrue(all(i.isdigit() for i in ids))

    # T2 — pagination stops when a page yields 0 new ids.
    def test_t2_pagination_stop_on_zero_new_ids(self):
        pages = {1: getresults_html([100, 101, 102]), 2: getresults_html([100, 101])}

        def handler(url, idx):
            page = int(url.split("page=")[1])
            return FakeResponse(200, pages[page])
        f = fv.VisirFetcher(FakeSession(handler), mem_conn(), delay=0, stypes=("sale",), log=silent)
        ids = f.index_sweep()
        self.assertEqual(f.stats.pages_fetched, 2)             # page1 (3 new) + page2 (0 new) -> stop
        self.assertEqual(set(ids), {"100", "101", "102"})

    # T3 — max_pages caps an ever-fresh stream.
    def test_t3_pagination_max_pages_cap(self):
        def handler(url, idx):
            page = int(url.split("page=")[1])
            return FakeResponse(200, getresults_html([page * 10, page * 10 + 1]))  # always new
        f = fv.VisirFetcher(FakeSession(handler), mem_conn(), delay=0, max_pages=3,
                            stypes=("sale",), log=silent)
        f.index_sweep()
        self.assertEqual(f.stats.pages_fetched, 3)

    # T4 — same listing, rotating ads -> 1 blob, 2 fetches, second changed=0.
    def test_t4_content_hash_dedup(self):
        bodies = [detail_html(ad_id="111", ad_img="/a.jpg"),
                  detail_html(ad_id="222", ad_img="/b.jpg")]
        conn = mem_conn()
        for b in bodies:
            f = fv.VisirFetcher(FakeSession(lambda u, i, _b=b: FakeResponse(200, _b)),
                                conn, delay=0, log=silent)
            f.detail_walk(["500"])
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM raw_blobs").fetchone()[0], 1)
        rows = conn.execute("SELECT changed FROM raw_fetches WHERE source_listing_id='500' "
                            "ORDER BY raw_id").fetchall()
        self.assertEqual([r[0] for r in rows], [1, 0])

    # T5 — real content change -> 2 blobs, both changed=1.
    def test_t5_content_hash_changed(self):
        bodies = [detail_html(price="99.900.000"), detail_html(price="143.900.000")]
        conn = mem_conn()
        for b in bodies:
            f = fv.VisirFetcher(FakeSession(lambda u, i, _b=b: FakeResponse(200, _b)),
                                conn, delay=0, log=silent)
            f.detail_walk(["600"])
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM raw_blobs").fetchone()[0], 2)
        rows = conn.execute("SELECT changed FROM raw_fetches WHERE source_listing_id='600' "
                            "ORDER BY raw_id").fetchall()
        self.assertEqual([r[0] for r in rows], [1, 1])

    # T6 — 403 records a ledger row then trips the kill-switch (exit 2 at main level).
    def test_t6_kill_switch_on_403(self):
        conn = mem_conn()
        f = fv.VisirFetcher(FakeSession(lambda u, i: FakeResponse(403, b"forbidden")),
                            conn, delay=0, log=silent)
        with self.assertRaises(fv.KillSwitch):
            f.detail_walk(["1"])
        row = conn.execute("SELECT http_status, parse_status FROM raw_fetches "
                           "WHERE source_listing_id='1'").fetchone()
        self.assertEqual(row[0], 403)
        self.assertEqual(row[1], "failed")

    # T7 — --test caps: 1 page/stype, <=10 details.
    def test_t7_test_mode_caps(self):
        def handler(url, idx):
            if "search/results" in url:
                return FakeResponse(200, b"<html>prime</html>")
            if "getresults" in url:
                return FakeResponse(200, getresults_html(list(range(2000, 2015))))  # 15 ids
            return FakeResponse(200, detail_html(ad_id=str(idx)))
        f = fv.VisirFetcher(FakeSession(handler), mem_conn(), delay=0,
                            stypes=("sale", "rent"), test=True, log=silent)
        f.run()
        self.assertEqual(f.stats.pages_fetched, 2)             # 1 page each stype
        self.assertEqual(f.stats.detail_fetches, 10)           # capped

    # T8 — missing schema fails gracefully.
    def test_t8_schema_missing_fails_gracefully(self):
        empty = mem_conn(with_schema=False)
        self.assertFalse(fv.verify_schema(empty))
        f = fv.VisirFetcher(FakeSession(lambda u, i: FakeResponse(200, b"")), empty,
                            delay=0, log=silent)
        with self.assertRaises(fv.SchemaMissing):
            f.run()

    # T9 — fetch_kind + source_listing_id recorded correctly per phase.
    def test_t9_fetch_kind_recorded_correctly(self):
        def handler(url, idx):
            if "getresults" in url:
                return FakeResponse(200, getresults_html([777]))
            return FakeResponse(200, detail_html())
        conn = mem_conn()
        f = fv.VisirFetcher(FakeSession(handler), conn, delay=0, stypes=("sale",), log=silent)
        ids = f.index_sweep()
        f.detail_walk(ids)
        idx_rows = conn.execute("SELECT source_listing_id FROM raw_fetches "
                                "WHERE fetch_kind='index'").fetchall()
        det_rows = conn.execute("SELECT source_listing_id FROM raw_fetches "
                                "WHERE fetch_kind='detail'").fetchall()
        self.assertTrue(all(r[0] is None for r in idx_rows))
        self.assertEqual([r[0] for r in det_rows], ["777"])

    # T10 — --ids mode: detail-walk only, no index sweep.
    def test_t10_ids_flag_skips_phase_a(self):
        def handler(url, idx):
            if "search/results" in url:           # prime
                return FakeResponse(200, b"<html>prime</html>")
            if "getresults" in url:               # must NOT be called in --ids mode
                raise AssertionError("index sweep ran under --ids: %s" % url)
            return FakeResponse(200, detail_html())
        sess = FakeSession(handler)
        conn = mem_conn()
        f = fv.VisirFetcher(sess, conn, delay=0, log=silent)
        f.run(ids=["123", "456"])
        self.assertFalse(any("getresults" in u for u in sess.calls))   # Phase A skipped
        self.assertEqual(f.stats.detail_fetches, 2)
        kinds = list(conn.execute("SELECT fetch_kind, COUNT(*) FROM raw_fetches GROUP BY fetch_kind"))
        self.assertEqual(dict(kinds), {"detail": 2})                   # 2 detail, 0 index

    # T11 — kill-switch trips on 3 consecutive HTTP 400 (visir soft-throttle).
    def test_t11_kill_switch_on_consecutive_400s(self):
        def handler(url, idx):
            if "search/results" in url:
                return FakeResponse(200, b"<html>prime</html>")
            return FakeResponse(400, b"throttled")
        conn = mem_conn()
        f = fv.VisirFetcher(FakeSession(handler), conn, delay=0, log=silent)
        with self.assertRaises(fv.KillSwitch):
            f.run(ids=["1", "2", "3", "4", "5"])
        self.assertLessEqual(f.stats.detail_fetches, 3)               # halts at/before the 3rd
        # all attempted rows recorded as failed (400)
        self.assertGreaterEqual(
            conn.execute("SELECT COUNT(*) FROM raw_fetches WHERE http_status=400").fetchone()[0], 3)

    # T12 — re-prime fires across BOTH phases via the unified counter (full sweep + detail).
    def test_t12_periodic_session_reprime_unified(self):
        prime_count = [0]

        def handler(url, idx):
            if "search/results" in url:
                prime_count[0] += 1
                return FakeResponse(200, b"<html>prime</html>")
            if "getresults" in url:
                page = int(url.split("page=")[1].split("&")[0])
                if page > 10:
                    return FakeResponse(200, b"")              # end of sweep
                ids = "".join('<a href="/property/%d">x</a>' % (page * 10 + i) for i in range(5))
                return FakeResponse(200, ids.encode())
            return FakeResponse(200, detail_html())
        f = fv.VisirFetcher(FakeSession(handler), mem_conn(), delay=0, log=silent, stypes=["sale"])
        f.REPRIME_EVERY = 15
        f.run()                                                # ~11 index + ~50 detail = ~61 reqs
        self.assertGreaterEqual(prime_count[0], 4)             # initial + ~3 re-primes

    # T13 — prime() resets the unified counter (no double-counting the prime request).
    def test_t13_counter_resets_after_reprime(self):
        f = fv.VisirFetcher(FakeSession(lambda u, i: FakeResponse(200, detail_html())),
                            mem_conn(), delay=0, log=silent)
        f.REPRIME_EVERY = 5
        f.prime()
        self.assertEqual(f.requests_since_prime, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
