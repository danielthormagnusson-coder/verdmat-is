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
                         "https://g.mbl.is/v1/graphql?op=list_sale&offset=320&fields=v2")
        self.assertEqual(fm.synthetic_url("aggregate_count"),
                         "https://g.mbl.is/v1/graphql?op=aggregate_count&fields=v2")
        self.assertTrue(fm.synthetic_url("delta_check_sale", since="2026-06-08")
                        .endswith("since=2026-06-08&fields=v2"))

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

    # ── supplementary "negotiable" modes (inverted price predicate) ──
    def test_t19_negotiable_modes_in_argparse_choices(self):
        self.assertIn("seed-rent-negotiable", fm.MODE_CHOICES)
        self.assertIn("seed-sale-negotiable", fm.MODE_CHOICES)

    def test_t20_negotiable_rent_query_inverts_price(self):
        q = fm.seed_query(fm.MODECFG["seed-rent-negotiable"], 9, 0)
        self.assertIn("price:{_eq:0}", q)          # inverted
        self.assertIn("size:{_gt:0}", q)
        self.assertNotIn("price:{_gt:0}", q)
        self.assertNotIn("syna", q)

    def test_t21_negotiable_sale_query_inverts_verd(self):
        q = fm.seed_query(fm.MODECFG["seed-sale-negotiable"], 9, 0)
        self.assertIn("verd:{_eq:0}", q)           # inverted
        self.assertIn("fermetrar:{_gt:0}", q)
        self.assertIn("syna:{_eq:true}", q)
        self.assertNotIn("verd:{_gt:0}", q)

    def test_t22_negotiable_rent_synthetic_url(self):
        self.assertEqual(fm.synthetic_url("seed_rent_negotiable", offset=48),
                         "https://g.mbl.is/v1/graphql?op=seed_rent_negotiable&offset=48&fields=v2")

    def test_t23_negotiable_sale_synthetic_url(self):
        self.assertEqual(fm.synthetic_url("seed_sale_negotiable", offset=96),
                         "https://g.mbl.is/v1/graphql?op=seed_sale_negotiable&offset=96&fields=v2")

    def test_t24_negotiable_self_establishes_ignoring_main_seed(self):
        # main seed-sale has its own frozen window in-flight, but negotiable must NOT inherit it —
        # it self-establishes its own max_id (mbl hard-deletes -> head-of-id negotiable rows matter).
        st = fm.default_state()
        st["seed_sale"].update({"frozen_max_id": 700, "last_offset": 320, "completed": False})
        saw = {"max": False}

        def handler(q, idx):
            if "limit:1)" in q:                       # negotiable establishes its OWN ceiling
                saw["max"] = True
                return FakeResp(200, body({"data": {"fs_fasteign": [{"eign_id": 925}]}}))
            if "aggregate" in q:
                return FakeResp(200, agg_body(1698, 0))
            return FakeResp(200, body({"data": {"fs_fasteign": []}}))   # exhaust immediately
        sess = FakeSession(handler)
        f = fetcher(sess, mem_conn(), state=st, mode="seed-sale-negotiable")
        f.run()
        self.assertTrue(saw["max"], "negotiable must self-establish, NOT inherit the main seed window")
        self.assertEqual(st["seed_sale_negotiable"]["frozen_max_id"], 925)   # its own, not 700
        self.assertEqual(st["seed_sale"]["frozen_max_id"], 700)              # main seed untouched
        self.assertTrue(st["seed_sale_negotiable"]["completed"])

    # ── v2_enriched field selection (2026-06-10) ──
    def test_t26_enriched_fields_exclusions_and_nested_blocks(self):
        # deliberate exclusions: generated_fts (huge tsvector), favorite (user-scoped),
        # fs_count/rt_count (volatile per-postnr counters -> would break content-hash dedup)
        self.assertNotIn("generated_fts", fm.SALE_FIELDS)
        self.assertNotIn("favorite", fm.SALE_FIELDS)
        self.assertNotIn("fs_count", fm.SALE_FIELDS)
        self.assertNotIn("rt_count", fm.RENT_FIELDS)
        self.assertNotIn("favorite", fm.RENT_FIELDS)
        # nested blocks present (positive guard against accidental scalar-only regression)
        for block in ("images {", "agency {", "attachments {", "latest_openhouse {",
                      "postal_code {", "promo {"):
            self.assertIn(block, fm.SALE_FIELDS)
        for block in ("images {", "agency {", "postal_code {", "promo {"):
            self.assertIn(block, fm.RENT_FIELDS)
        # rent ordering field differs from sale imgno
        self.assertIn("imgno", fm.SALE_FIELDS)
        self.assertIn("ordering", fm.RENT_FIELDS)
        self.assertEqual(fm.FIELDS_VERSION, "v2_enriched")

    def test_t27_all_mode_synthetic_urls_carry_fields_v2(self):
        for mode, cfg in fm.MODECFG.items():
            if "delta_field" in cfg:
                url = fm.synthetic_url(cfg["op"], since="2026-06-10T00:00:00+00:00")
            else:
                url = fm.synthetic_url(cfg["op"], offset=0)
            self.assertIn("fields=v2", url, "mode %s missing fields=v2 marker" % mode)
        self.assertIn("fields=v2", fm.synthetic_url("aggregate_count"))

    def test_t28_enriched_fixtures_hash_deterministic(self):
        # real enriched probe responses (2026-06-10 mini-probe): canonicalize twice -> same hash
        from scraper_paths import get_scraper_data_dir
        from canonicalize_mbl import canonicalize_mbl
        fixdir = get_scraper_data_dir() / "probe_samples" / "mbl"
        for fname in ("enriched_sale_16.json", "enriched_rent_16.json"):
            fpath = fixdir / fname
            if not fpath.is_file():
                self.skipTest("fixture %s not present on this machine" % fname)
            with self.subTest(fixture=fname):
                raw = fpath.read_bytes()
                _, h1 = canonicalize_mbl(raw, "application/json")
                _, h2 = canonicalize_mbl(raw, "application/json")
                self.assertEqual(h1, h2)
                # nested shape survives canonicalization (sanity: it really is the enriched form)
                self.assertIn(b'"images"', raw)

    def test_t25_negotiable_fallback_queries_max_when_no_main_seed(self):
        # main seed never started (frozen_max_id None) -> negotiable queries max + aggregate itself
        st = fm.default_state()
        saw = {"max": False}

        def handler(q, idx):
            if "limit:1)" in q:
                saw["max"] = True
                return FakeResp(200, body({"data": {"rentals_property": [{"id": 300}]}}))
            if "aggregate" in q:
                return FakeResp(200, agg_body(0, 50))
            return FakeResp(200, body({"data": {"rentals_property": []}}))   # exhaust
        f = fetcher(FakeSession(handler), mem_conn(), state=st, mode="seed-rent-negotiable")
        f.run()
        self.assertTrue(saw["max"], "fallback must query max_id when there is no main seed to inherit")
        self.assertEqual(st["seed_rent_negotiable"]["frozen_max_id"], 300)


if __name__ == "__main__":
    unittest.main(verbosity=2)
