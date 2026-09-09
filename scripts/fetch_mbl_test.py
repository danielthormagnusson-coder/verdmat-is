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

    # ── force_restart history archive ──
    def test_t29_force_restart_archives_old_state(self):
        st = fm.default_state()
        st["seed_sale"].update({"frozen_max_id": 500, "last_offset": 320, "total_fetched": 800,
                                "completed": True, "universe_pages": 40})
        snap = {}

        def handler(q, idx):
            if "limit:1)" in q:
                # state at max_id time = right after the reset -> must be clean default
                snap["at_reset"] = dict(fref["f"].state["seed_sale"])
                return FakeResp(200, body({"data": {"fs_fasteign": [{"eign_id": 925}]}}))
            if "aggregate" in q:
                return FakeResp(200, agg_body(16, 0))
            return FakeResp(200, body({"data": {"fs_fasteign": []}}))   # exhaust immediately
        fref = {}
        f = fetcher(FakeSession(handler), mem_conn(), state=st, mode="seed-sale", force=True)
        fref["f"] = f
        f.run()
        # old window archived intact at history[0], stamped
        hist = f.state["seed_sale_history"]
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["frozen_max_id"], 500)
        self.assertEqual(hist[0]["total_fetched"], 800)
        self.assertTrue(hist[0]["completed"])
        self.assertIn("archived_at", hist[0])
        # new state was a clean default at re-establish time...
        self.assertIsNone(snap["at_reset"]["frozen_max_id"])
        self.assertEqual(snap["at_reset"]["last_offset"], 0)
        self.assertFalse(snap["at_reset"]["completed"])
        self.assertNotIn("archived_at", snap["at_reset"])
        # ...and the re-seed then self-established the NEW window
        self.assertEqual(f.state["seed_sale"]["frozen_max_id"], 925)

        # second force_restart -> history grows to 2, in order
        f2 = fetcher(FakeSession(handler), mem_conn(), state=f.state, mode="seed-sale", force=True)
        fref["f"] = f2
        f2.run()
        hist = f2.state["seed_sale_history"]
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0]["frozen_max_id"], 500)    # original window first
        self.assertEqual(hist[1]["frozen_max_id"], 925)    # then the re-seeded one
        self.assertLessEqual(hist[0]["archived_at"], hist[1]["archived_at"])

    def test_t30_state_roundtrip_preserves_history_key(self):
        p = tmp_state()
        st = fm.default_state()
        st["seed_sale_history"] = [{"frozen_max_id": 500, "total_fetched": 800,
                                    "completed": True, "archived_at": "2026-06-11T00:00:00+00:00"}]
        fm.save_state(p, st)
        self.assertFalse(os.path.isfile(p + ".tmp"))       # atomic path unchanged
        loaded = fm.load_state(p)
        self.assertEqual(loaded["seed_sale_history"][0]["frozen_max_id"], 500)
        self.assertNotIn("seed_sale_history", fm.default_state())   # created lazily, not a default
        os.remove(p)

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


class TestDeltaNegotiableAndPrime(unittest.TestCase):
    """§6-A.1 gap fixes: delta-negotiable modes + prime_delta_since safety gates."""

    # ── delta-negotiable modes ──
    def test_t31_delta_negotiable_modes_and_predicates(self):
        self.assertIn("delta-sale-negotiable", fm.MODE_CHOICES)
        self.assertIn("delta-rent-negotiable", fm.MODE_CHOICES)
        qs = fm.delta_query(fm.MODECFG["delta-sale-negotiable"], "2026-06-11T00:00:00+00:00", 0)
        self.assertIn('br_dags:{_gt:"2026-06-11T00:00:00+00:00"}', qs)
        self.assertIn("verd:{_eq:0}", qs)
        self.assertIn("fermetrar:{_gt:0}", qs)
        self.assertIn("syna:{_eq:true}", qs)
        self.assertNotIn("verd:{_gt:0}", qs)
        qr = fm.delta_query(fm.MODECFG["delta-rent-negotiable"], "2026-06-11T00:00:00+00:00", 0)
        self.assertIn('updated:{_gt:"2026-06-11T00:00:00+00:00"}', qr)
        self.assertIn("price:{_eq:0}", qr)
        self.assertIn("size:{_gt:0}", qr)
        self.assertNotIn("price:{_gt:0}", qr)
        # synthetic URLs carry the op + fields=v2 marker
        u = fm.synthetic_url(fm.MODECFG["delta-sale-negotiable"]["op"], since="2026-06-11")
        self.assertIn("op=delta_check_sale_negotiable", u)
        self.assertIn("fields=v2", u)

    def test_t32_delta_negotiable_own_since_key_and_kind(self):
        st = fm.default_state()
        st["delta_sale"]["last_br_dags_seen"] = "2026-06-01T00:00:00+00:00"   # must stay untouched

        def handler(q, idx):
            # cc201: keyset pages carry no offset — first call serves the page, second is empty
            rows = sale_rows([4, 5]) if idx == 0 else []
            return FakeResp(200, body({"data": {"fs_fasteign": rows}}))
        conn = mem_conn()
        f = fetcher(FakeSession(handler), conn, state=st, mode="delta-sale-negotiable")
        f.run()
        # own high-water advanced to the LAST fetched row (cc201 A1); plain delta-sale untouched
        self.assertEqual(st["delta_sale_negotiable"]["last_br_dags_seen"], sale_rows([4, 5])[-1]["br_dags"])
        self.assertEqual(st["delta_sale_negotiable"]["cursor_pk"], 5)
        self.assertEqual(st["delta_sale"]["last_br_dags_seen"], "2026-06-01T00:00:00+00:00")
        self.assertIsNone(st["delta_sale"]["cursor_pk"])
        # new fetch_kind discriminator, still under the list_page_ prefix (parser-compatible)
        kinds = {r[0] for r in conn.execute("SELECT fetch_kind FROM raw_fetches")}
        self.assertEqual(kinds, {"list_page_sale_negotiable_delta"})

    # ── prime_delta_since ──
    def _parsed_mem(self, sale=((1, "2026-06-09T01:00:00+00:00", 0),
                                (2, "2026-06-09T02:00:00+00:00", 1)),
                    rent=((10, "2026-06-09T03:00:00", 0),
                          (11, "2026-06-09T04:00:00", 1))):
        import init_parsed_mbl_schema as initp
        pc = sqlite3.connect(":memory:")
        initp.init_schema_on_conn(pc)
        for slid, ts, neg in sale:
            pc.execute("INSERT INTO parsed_mbl_sale(source_listing_id, raw_id, content_hash, "
                       "fetched_at, fields_version, parser_version, parsed_at, eign_id, "
                       "br_dags, is_negotiable, is_foreign) VALUES(?,1,'h','f','v1_scalar',"
                       "'p','t',?,?,?,0)", (slid, slid, ts, neg))
        for slid, ts, neg in rent:
            pc.execute("INSERT INTO parsed_mbl_rent(source_listing_id, raw_id, content_hash, "
                       "fetched_at, fields_version, parser_version, parsed_at, id, "
                       "updated, is_negotiable, is_foreign, address_corrupt) "
                       "VALUES(?,1,'h','f','v1_scalar','p','t',?,?,?,0,0)", (slid, slid, ts, neg))
        pc.commit()
        return pc

    def setUp(self):
        import prime_delta_since as pds
        self.pds = pds
        self._orig_procs = pds._live_fetcher_processes
        pds._live_fetcher_processes = lambda: []          # default: no live fetcher
        self.addCleanup(lambda: setattr(pds, "_live_fetcher_processes", self._orig_procs))

    def test_t33_prime_computes_per_slice_maxima(self):
        vals = {(k, sk): v for k, sk, v in self.pds.compute_since_values(self._parsed_mem())}
        self.assertEqual(vals[("delta_sale", "last_br_dags_seen")], "2026-06-09T01:00:00+00:00")
        self.assertEqual(vals[("delta_sale_negotiable", "last_br_dags_seen")],
                         "2026-06-09T02:00:00+00:00")
        self.assertEqual(vals[("delta_rent", "last_updated_seen")], "2026-06-09T03:00:00")
        self.assertEqual(vals[("delta_rent_negotiable", "last_updated_seen")],
                         "2026-06-09T04:00:00")

    def test_t34_prime_dry_run_writes_nothing(self):
        p = tmp_state()
        changes = self.pds.run_priming(self._parsed_mem(), p, confirm=False, log=silent)
        self.assertEqual(len(changes), 4)
        self.assertFalse(os.path.isfile(p))               # dry-run: no state file created

    def test_t35_prime_confirm_writes_all_four(self):
        p = tmp_state()
        self.pds.run_priming(self._parsed_mem(), p, confirm=True, log=silent)
        st = fm.load_state(p)
        self.assertEqual(st["delta_sale"]["last_br_dags_seen"], "2026-06-09T01:00:00+00:00")
        self.assertEqual(st["delta_sale_negotiable"]["last_br_dags_seen"],
                         "2026-06-09T02:00:00+00:00")
        self.assertEqual(st["delta_rent"]["last_updated_seen"], "2026-06-09T03:00:00")
        self.assertEqual(st["delta_rent_negotiable"]["last_updated_seen"], "2026-06-09T04:00:00")
        self.assertFalse(os.path.isfile(p + ".tmp"))      # atomic os.replace path
        os.remove(p)

    def test_t36_prime_refusal_branches(self):
        p = tmp_state()
        # (a) live fetch_mbl process
        self.pds._live_fetcher_processes = lambda: ["python fetch_mbl.py --mode resume"]
        with self.assertRaises(self.pds.PrimeRefusal):
            self.pds.run_priming(self._parsed_mem(), p, confirm=True, log=silent)
        self.pds._live_fetcher_processes = lambda: []
        # (b) recent state activity (heuristic also covers scan-unavailable case)
        st = fm.default_state()
        st["seed_sale"]["last_page_at"] = fm.now_iso()
        fm.save_state(p, st)
        with self.assertRaises(self.pds.PrimeRefusal):
            self.pds.run_priming(self._parsed_mem(), p, confirm=True, log=silent)
        os.remove(p)
        # (c) since_key already set, no --force
        p2 = tmp_state()
        st2 = fm.default_state()
        st2["delta_sale"]["last_br_dags_seen"] = "2026-05-01T00:00:00+00:00"
        fm.save_state(p2, st2)
        with self.assertRaises(self.pds.PrimeRefusal):
            self.pds.run_priming(self._parsed_mem(), p2, confirm=True, log=silent)
        os.remove(p2)
        # (d) empty parsed slice
        with self.assertRaises(self.pds.PrimeRefusal):
            self.pds.run_priming(self._parsed_mem(sale=(), rent=()), tmp_state(),
                                 confirm=True, log=silent)
        self.assertFalse(os.path.isfile(p))               # nothing ever written on refusal

    def test_t37_prime_force_archives_old_value(self):
        p = tmp_state()
        st = fm.default_state()
        st["delta_sale"]["last_br_dags_seen"] = "2026-05-01T00:00:00+00:00"
        fm.save_state(p, st)
        self.pds.run_priming(self._parsed_mem(), p, confirm=True, force=True, log=silent)
        loaded = fm.load_state(p)
        self.assertEqual(loaded["delta_sale"]["last_br_dags_seen"], "2026-06-09T01:00:00+00:00")
        hist = loaded["delta_sale_history"]
        self.assertEqual(hist[0]["last_br_dags_seen"], "2026-05-01T00:00:00+00:00")
        self.assertIn("archived_at", hist[0])
        # modes that were NOT previously set get no history entry
        self.assertNotIn("delta_rent_history", loaded)
        os.remove(p)


# ── cc201 (2026-09-09): A2 domestic-postfang predicate + A1 keyset cursor in _delta ──
def _cursor(q):
    """(since, pk_after) the fetcher put in the where-object (mock stands in for Hasura)."""
    m = re.search(r'_or:\[\{(\w+):\{_gt:"([^"]+)"\}\},\{\1:\{_eq:"\2"\}, (\w+):\{_gt:(\d+)\}\}\]', q)
    return m.group(2), int(m.group(4))


class HasuraLike:
    """Keyset-faithful mock of fs_fasteign / fs_fasteign_aggregate over a fixed dataset:
    rows strictly after (br_dags, eign_id) cursor, ordered (br_dags asc, eign_id asc), 16/page."""
    def __init__(self, rows):
        self.rows = sorted(rows, key=lambda r: (r["br_dags"], r["eign_id"]))
        self.served = []                       # every row served, in order (dup detection)
        self.agg_calls = 0

    def __call__(self, q, idx):
        since, pk = _cursor(q)
        after = [r for r in self.rows if (r["br_dags"], r["eign_id"]) > (since, pk)]
        if "_aggregate" in q:
            self.agg_calls += 1
            return FakeResp(200, body({"data": {"fs_fasteign_aggregate": {"aggregate": {"count": len(after)}}}}))
        page = after[:fm.PAGE]
        self.served.extend(page)
        return FakeResp(200, body({"data": {"fs_fasteign": page}}))


def rows_distinct(n, start=1000, day="2026-09-10"):
    return [{"eign_id": start + i, "verd": 5, "fermetrar": 50, "postfang": 101,
             "br_dags": "%sT%02d:%02d:00+00:00" % (day, i // 60, i % 60)} for i in range(n)]


class TestCc201DeltaCursor(unittest.TestCase):

    def _run(self, mock, state, max_pages, logs=None):
        conn = mem_conn()
        f = fm.MblFetcher(FakeSession(mock), conn, state, tmp_state(), mode="delta-sale",
                          max_pages=max_pages, min_spacing=0, log=(logs.append if logs is not None else silent))
        f._sleep = lambda *a, **k: None
        f.run()
        return f, conn

    # 1) cap: 3-page cap over 5 pages of data -> high-water = last row of page 3, next run
    #    starts at the first row of page 4; nothing skipped, nothing fetched twice.
    def test_c1_cap_is_delay_not_loss(self):
        data = rows_distinct(80)                                   # 5 pages exactly
        mock = HasuraLike(data)
        st = fm.default_state()
        st["delta_sale"]["last_br_dags_seen"] = "2026-09-09T00:00:00+00:00"
        logs = []
        f1, c1 = self._run(mock, st, 3, logs)
        self.assertEqual(f1.stats.pages, 3)
        self.assertEqual(st["delta_sale"]["last_br_dags_seen"], data[47]["br_dags"])   # last row of page 3
        self.assertEqual(st["delta_sale"]["cursor_pk"], data[47]["eign_id"])
        self.assertEqual(st["delta_sale"]["cursor_ts"], data[47]["br_dags"])
        # cap-hit line names the cursor and the aggregate-sized carry-over (32 rows = pages 4-5)
        carry = [l for l in logs if "framhald í nótt" in l]
        self.assertEqual(len(carry), 1)
        self.assertIn("br_dags=%s, eign_id=%d, 32 raðir eftir" % (data[47]["br_dags"], data[47]["eign_id"]), carry[0])
        self.assertEqual(mock.agg_calls, 1)
        self.assertEqual(len(mock.served), 48)
        # next run (same state on disk semantics: same dict) resumes at row 48
        f2, c2 = self._run(mock, st, 100)
        self.assertEqual(f2.stats.pages, 2)
        self.assertEqual(mock.served[48]["eign_id"], data[48]["eign_id"])
        self.assertEqual([r["eign_id"] for r in mock.served], [r["eign_id"] for r in data])   # exact, once each
        self.assertEqual(st["delta_sale"]["last_br_dags_seen"], data[-1]["br_dags"])
        self.assertEqual(mock.agg_calls, 1)                        # no cap on run 2 -> no aggregate

    # 2) ties: >=16 rows sharing one br_dags across page boundaries -> cursor swallows none, repeats none
    def test_c2_tied_br_dags_across_pages(self):
        tie = "2026-09-10T12:00:00+00:00"
        data = rows_distinct(10) \
            + [{"eign_id": 5000 + i, "verd": 5, "fermetrar": 50, "postfang": 101, "br_dags": tie} for i in range(40)] \
            + rows_distinct(7, start=9000, day="2026-09-11")
        mock = HasuraLike(data)
        st = fm.default_state()
        st["delta_sale"]["last_br_dags_seen"] = "2026-09-09T00:00:00+00:00"
        f, _ = self._run(mock, st, 100)
        self.assertEqual(f.stats.pages, 4)                                            # 57 rows -> 16,16,16,9
        self.assertEqual([r["eign_id"] for r in mock.served], [r["eign_id"] for r in mock.rows])
        self.assertEqual(len({r["eign_id"] for r in mock.served}), 57)
        # and a cap INSIDE the tie run resumes mid-tie via the pk tie-breaker
        mock2 = HasuraLike(data)
        st2 = fm.default_state()
        st2["delta_sale"]["last_br_dags_seen"] = "2026-09-09T00:00:00+00:00"
        self._run(mock2, st2, 2)                                                       # stops after row 32 (mid-tie)
        self.assertEqual(st2["delta_sale"]["last_br_dags_seen"], tie)
        self.assertEqual(st2["delta_sale"]["cursor_pk"], 5021)
        self._run(mock2, st2, 100)
        self.assertEqual([r["eign_id"] for r in mock2.served], [r["eign_id"] for r in mock2.rows])

    # 2b) a re-primed since_key invalidates a stale cursor_pk (cursor_ts mismatch -> pk 0)
    def test_c2b_stale_cursor_pk_ignored_after_reprime(self):
        st = fm.default_state()
        st["delta_sale"].update({"last_br_dags_seen": "2026-09-09T00:00:00+00:00",
                                 "cursor_pk": 777, "cursor_ts": "2026-09-01T00:00:00+00:00"})
        sess = FakeSession(lambda q, i: FakeResp(200, body({"data": {"fs_fasteign": []}})))
        f = fm.MblFetcher(sess, mem_conn(), st, tmp_state(), mode="delta-sale", min_spacing=0, log=silent)
        f._sleep = lambda *a, **k: None
        f.run()
        self.assertEqual(_cursor(sess.queries[0]), ("2026-09-09T00:00:00+00:00", 0))
        self.assertEqual(st["delta_sale"]["last_br_dags_seen"], "2026-09-09T00:00:00+00:00")   # empty run: unchanged

    # 3) A2: domestic predicate keeps NULL postfang; only the three priced-sale slices carry it;
    #    the cursor's _or is _and-wrapped so the where-object has ONE top-level _or.
    def test_c3_a2_domestic_predicate_keeps_null(self):
        for mode in ("delta-sale", "delta-sale-negotiable"):
            q = fm.delta_query(fm.MODECFG[mode], "2026-09-09T00:00:00+00:00", 0)
            self.assertIn("postfang:{_lt:1000}", q)
            self.assertIn("postfang:{_is_null:true}", q)
            self.assertIn('_and:[{_or:[{br_dags:{_gt:"2026-09-09T00:00:00+00:00"}}', q)
            self.assertEqual(q.count("_or:["), 2)                       # cursor (_and-wrapped) + SALE_DOMESTIC
            self.assertEqual(q.count(", _or:["), 1)                     # exactly ONE top-level _or
            self.assertIn("order_by:[{br_dags:asc},{eign_id:asc}]", q)
            self.assertNotIn("offset:", q)
        qs = fm.seed_query(fm.MODECFG["seed-sale"], 500, 16)
        self.assertIn("postfang:{_lt:1000}", qs)
        self.assertIn("postfang:{_is_null:true}", qs)
        for mode in ("seed-rent", "delta-rent", "delta-rent-negotiable", "seed-sale-negotiable", "seed-rent-negotiable"):
            cfg = fm.MODECFG[mode]
            q = fm.delta_query(cfg, "x", 0) if "delta_field" in cfg else fm.seed_query(cfg, 9, 0)
            self.assertNotIn("postfang:{", q)                            # (field list still selects postfang)
        # the remaining-count aggregate carries the same where-object
        qa = fm.delta_remaining_query(fm.MODECFG["delta-sale"], "2026-09-09T00:00:00+00:00", 42)
        self.assertIn("fs_fasteign_aggregate(where:{_and:[{_or:[{br_dags:{_gt:", qa)
        self.assertIn("eign_id:{_gt:42}", qa)
        self.assertIn("postfang:{_is_null:true}", qa)
        # dry-run delta: no HTTP, no DB, no state
        conn = mem_conn()
        sess = FakeSession(lambda q, i: FakeResp(200, b"{}"))
        f = fetcher(sess, conn, mode="delta-sale", dry_run=True)
        f.run()
        self.assertEqual(sess.queries, [])
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM raw_fetches").fetchone()[0], 0)
        self.assertFalse(os.path.isfile(f.state_path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
