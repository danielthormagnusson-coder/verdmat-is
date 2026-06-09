"""Unit tests for fetch_mbl. stdlib unittest, NO pytest, NO live HTTP (FakeSession) and an
in-memory raw_mbl schema. R2 (resume-mid-seed correctness) is the highest-stakes invariant.

    python -m unittest scripts.fetch_mbl_test -v
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_mbl as fm                    # noqa: E402
import init_raw_mbl_schema as initm       # noqa: E402


def mem_conn():
    c = sqlite3.connect(":memory:")
    c.executescript(initm.RAW_BLOBS_DDL + initm.RAW_FETCHES_DDL)
    c.execute(initm.IX_LISTING)
    c.execute(initm.IX_PARSE)
    return c


class FakeResp:
    def __init__(self, status_code, content=b"{}", ctype="application/json"):
        self.status_code = status_code
        self.content = content if isinstance(content, (bytes, bytearray)) else content.encode("utf-8")
        self.headers = {"content-type": ctype}


class FakeSession:
    def __init__(self, handler):
        self.handler = handler
        self.queries = []
        self.headers = {}

    def post(self, url, json=None, headers=None, timeout=None):
        q = (json or {}).get("query", "")
        self.queries.append(q)
        r = self.handler(q, len(self.queries) - 1)
        if isinstance(r, Exception):
            raise r
        return r


def body(obj):
    return json.dumps(obj).encode("utf-8")


def sale_rows(ids):
    return [{"eign_id": i, "verd": 1000 + i, "fermetrar": 50, "br_dags": "2026-06-08T0%d:00:00Z" % (i % 9)}
            for i in ids]


def agg_body(sc=13772, rc=1349):
    return body({"data": {"fs_fasteign_aggregate": {"aggregate": {"count": sc}},
                          "rentals_property_aggregate": {"aggregate": {"count": rc}}}})


def _offset(q):
    m = re.search(r"offset:(\d+)", q)
    return int(m.group(1)) if m else None


def silent(*a, **k):
    pass


def tmp_state():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(p)        # we want the path, not a pre-existing file
    return p


def fetcher(session, conn, state=None, *, mode=None, dry_run=False, force=False, path=None):
    st = state if state is not None else fm.default_state()
    f = fm.MblFetcher(session, conn, st, path or tmp_state(), mode=mode, min_spacing=0,
                      dry_run=dry_run, force_restart=force, log=silent)
    f._sleep = lambda *a, **k: None
    return f


class TestFetchMbl(unittest.TestCase):

    # ── helpers / state ──
    def test_t1_state_roundtrip_forward_compat(self):
        p = tmp_state()
        st = fm.default_state()
        st["seed_sale"]["last_offset"] = 48
        fm.save_state(p, st)
        loaded = fm.load_state(p)
        self.assertEqual(loaded["seed_sale"]["last_offset"], 48)
        self.assertIn("delta_rent", loaded)        # forward-compat fill
        os.remove(p)

    def test_t2_atomic_replace_no_tmp_left(self):
        p = tmp_state()
        fm.save_state(p, fm.default_state())
        self.assertTrue(os.path.isfile(p))
        self.assertFalse(os.path.isfile(p + ".tmp"))
        os.remove(p)

    def test_t3_min_spacing_floor(self):
        f = fm.MblFetcher(None, None, fm.default_state(), "x", min_spacing=10)
        self.assertEqual(f.min_spacing, fm.MIN_SPACING_FLOOR)

    def test_t3b_defaults(self):
        self.assertEqual(fm.PAGE, 16)
        self.assertEqual(fm.DEFAULT_MAX_PAGES, 400)

    # ── query construction ──
    def test_t4_seed_query_frozen_and_offset(self):
        q = fm.seed_query(fm.MODECFG["seed-sale"], 500, 160)
        self.assertIn("eign_id:{_lte:500}", q)
        self.assertIn("offset:160", q)
        self.assertIn("order_by:{eign_id:desc}", q)

    def test_t5_draft_filter_sale(self):
        q = fm.seed_query(fm.MODECFG["seed-sale"], 9, 0)
        for pred in ("syna:{_eq:true}", "verd:{_gt:0}", "fermetrar:{_gt:0}"):
            self.assertIn(pred, q)

    def test_t6_draft_filter_rent(self):
        q = fm.seed_query(fm.MODECFG["seed-rent"], 9, 0)
        self.assertIn("price:{_gt:0}", q)
        self.assertIn("size:{_gt:0}", q)
        self.assertNotIn("syna", q)

    def test_t7_synthetic_url_format(self):
        self.assertEqual(fm.synthetic_url("list_sale", offset=320),
                         "https://g.mbl.is/v1/graphql?op=list_sale&offset=320")
        self.assertEqual(fm.synthetic_url("aggregate_count"),
                         "https://g.mbl.is/v1/graphql?op=aggregate_count")
        self.assertTrue(fm.synthetic_url("delta_check_sale", since="2026-06-08").endswith("since=2026-06-08"))

    # ── pagination ──
    def test_t8_pagination_advance_and_terminate(self):
        def handler(q, idx):
            if "aggregate" in q:
                return FakeResp(200, agg_body(32, 0))
            if "limit:1)" in q:                       # max_id
                return FakeResp(200, body({"data": {"fs_fasteign": [{"eign_id": 999}]}}))
            off = _offset(q)
            rows = sale_rows([999 - off, 998 - off]) if off < 32 else []
            return FakeResp(200, body({"data": {"fs_fasteign": rows}}))
        conn = mem_conn()
        f = fetcher(FakeSession(handler), conn, mode="seed-sale")
        f.run()
        self.assertTrue(f.state["seed_sale"]["completed"])
        # offsets fetched: 0 and 16 (page rows), terminate at 32 (empty)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM raw_fetches WHERE fetch_kind='list_page_sale'").fetchone()[0], 2)

    # ── R2: resume mid-seed correctness (HIGHEST PRIORITY) ──
    def test_t9_resume_mid_seed_uses_persisted_offset_and_frozen(self):
        st = fm.default_state()
        st["seed_sale"].update({"frozen_max_id": 500, "last_offset": 160, "completed": False,
                                "halt_reason": "kill_switch", "universe_pages": 40})

        def handler(q, idx):
            # frozen already known -> a max_id (limit:1) or aggregate query here would be a BUG
            assert "limit:1)" not in q, "resume must NOT re-query max_id"
            assert "aggregate" not in q, "resume must NOT re-query aggregate"
            off = _offset(q)
            rows = sale_rows([500 - off]) if off < 176 else []   # one more page then exhaust
            return FakeResp(200, body({"data": {"fs_fasteign": rows}}))
        sess = FakeSession(handler)
        f = fetcher(sess, mem_conn(), state=st, mode="resume")
        f.run()
        self.assertIn("offset:160", sess.queries[0])            # continued from 160, NOT 0
        self.assertIn("eign_id:{_lte:500}", sess.queries[0])    # persisted frozen window
        self.assertTrue(f.state["seed_sale"]["completed"])

    def test_t10_frozen_persisted_not_requeried_on_resume(self):
        st = fm.default_state()
        st["seed_sale"].update({"frozen_max_id": 700, "last_offset": 0, "completed": False})

        def handler(q, idx):
            self.assertNotIn("limit:1)", q)          # frozen already set -> no max_id query
            return FakeResp(200, body({"data": {"fs_fasteign": []}}))   # immediate exhaust
        f = fetcher(FakeSession(handler), mem_conn(), state=st, mode="seed-sale")
        f.run()
        self.assertTrue(f.state["seed_sale"]["completed"])

    # ── kill-switch ──
    def test_t11_killswitch_consecutive_400(self):
        f = fetcher(FakeSession(lambda q, i: FakeResp(400, b"throttled")), mem_conn(), mode="seed-sale")
        with self.assertRaises(fm.KillSwitch):
            f.run()
        self.assertIsNotNone(f.state["seed_sale"]["halt_reason"])

    def test_t12_killswitch_403(self):
        f = fetcher(FakeSession(lambda q, i: FakeResp(403, b"forbidden")), mem_conn(), mode="seed-sale")
        with self.assertRaises(fm.KillSwitch):
            f.run()

    def test_t13_killswitch_graphql_errors(self):
        def handler(q, idx):
            if "limit:1)" in q:
                return FakeResp(200, body({"data": {"fs_fasteign": [{"eign_id": 9}]}}))
            if "aggregate" in q:
                return FakeResp(200, agg_body(9, 0))
            return FakeResp(200, body({"errors": [{"message": "permission denied"}]}))
        f = fetcher(FakeSession(handler), mem_conn(), mode="seed-sale")
        with self.assertRaises(fm.KillSwitch):
            f.run()

    # ── idempotency ──
    def test_t14_content_hash_idempotency(self):
        conn = mem_conn()
        f = fetcher(FakeSession(lambda q, i: None), conn, mode="seed-sale")
        b = body({"data": {"fs_fasteign": sale_rows([1, 2])}})
        f._record_page(b, "application/json", 200, "list_page_sale", "u", 2)
        f._record_page(b, "application/json", 200, "list_page_sale", "u", 2)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM raw_blobs").fetchone()[0], 1)
        changed = [r[0] for r in conn.execute("SELECT changed FROM raw_fetches ORDER BY raw_id")]
        self.assertEqual(changed, [1, 0])

    # ── dry-run + aggregate-check ──
    def test_t15_dry_run_no_http_no_db(self):
        conn = mem_conn()
        sess = FakeSession(lambda q, i: FakeResp(200, b"{}"))
        f = fetcher(sess, conn, mode="seed-sale", dry_run=True)
        f.run()
        self.assertEqual(sess.queries, [])                                   # no HTTP
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM raw_fetches").fetchone()[0], 0)
        self.assertFalse(os.path.isfile(f.state_path))                       # no state mutation

    def test_t16_aggregate_check_no_writes(self):
        conn = mem_conn()
        p = tmp_state()
        f = fetcher(FakeSession(lambda q, i: FakeResp(200, agg_body(13772, 1349))), conn,
                    mode="aggregate-check", path=p)
        sc, rc = f.run()
        self.assertEqual((sc, rc), (13772, 1349))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM raw_fetches").fetchone()[0], 0)
        self.assertFalse(os.path.isfile(p))                                  # no state mutation

    # ── R1: resume refuses if multiple in-flight ──
    def test_t17_resume_ambiguous_refuses(self):
        st = fm.default_state()
        st["seed_sale"].update({"frozen_max_id": 500, "last_offset": 160, "completed": False})
        st["delta_rent"]["halt_reason"] = "timeout"
        f = fetcher(FakeSession(lambda q, i: None), mem_conn(), state=st, mode="resume")
        with self.assertRaises(fm.AmbiguousResume):
            f.run()


if __name__ == "__main__":
    unittest.main(verbosity=2)
