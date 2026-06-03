"""Unit tests for fetch_myigloo (stdlib unittest, NO HTTP).

    python scripts/fetch_myigloo_test.py   # runs all, exits non-zero on failure

Per-test temp DB via init_raw_myigloo_schema.init_schema (reuses the §2.1
bootstrap — no hardcoded DDL here). stdlib only.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_myigloo as fm  # noqa: E402
from init_raw_myigloo_schema import init_schema  # noqa: E402

TS1 = "2026-06-03T00:00:00+00:00"
TS2 = "2026-06-03T00:00:05+00:00"
URL = "https://rent-api.myigloo.is/api/listings/123/"


def _temp_conn(stack):
    td = stack.enter_context(tempfile.TemporaryDirectory())
    db = Path(td) / "raw_myigloo.db"
    init_schema(db)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys=ON")
    stack.callback(conn.close)
    return conn


class TestFetchMyigloo(unittest.TestCase):

    def setUp(self):
        import contextlib
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)

    def conn(self):
        return _temp_conn(self._stack)

    # 1
    def test_hash_sha256_deterministic(self):
        self.assertEqual(hashlib.sha256(b"hello").hexdigest(),
                         "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")

    # 2
    def test_gzip_round_trip(self):
        x = b'{"items": [1,2,3], "count": 874}' * 10
        self.assertEqual(gzip.decompress(gzip.compress(x)), x)

    # 3
    def test_changed_logic_fresh_db(self):
        c = self.conn()
        changed, status = fm.compute_changed(c, "detail", "123", URL, "abc")
        self.assertEqual((changed, status), (1, "pending"))

    # 4
    def test_changed_logic_same_hash(self):
        c = self.conn()
        fm.record_success(c, "detail", "123", URL, TS1, 200, 0, b"BODY-X")
        hx = hashlib.sha256(b"BODY-X").hexdigest()
        self.assertEqual(fm.compute_changed(c, "detail", "123", URL, hx), (0, "skipped_unchanged"))

    # 5
    def test_changed_logic_different_hash(self):
        c = self.conn()
        fm.record_success(c, "detail", "123", URL, TS1, 200, 0, b"BODY-X")
        hy = hashlib.sha256(b"BODY-Y").hexdigest()
        self.assertEqual(fm.compute_changed(c, "detail", "123", URL, hy), (1, "pending"))

    # 6
    def test_raw_blobs_insert_or_ignore(self):
        c = self.conn()
        fm.record_success(c, "detail", "123", URL, TS1, 200, 0, b"BODY-X")
        fm.record_success(c, "detail", "123", URL, TS2, 200, 0, b"BODY-X")  # same body, later ts
        n = c.execute("SELECT count(*) FROM raw_blobs").fetchone()[0]
        first_stored = c.execute("SELECT first_stored FROM raw_blobs").fetchone()[0]
        self.assertEqual(n, 1)
        self.assertEqual(first_stored, TS1)  # sticks to the first insert

    # 7
    def test_raw_fetches_appends(self):
        c = self.conn()
        fm.record_success(c, "detail", "123", URL, TS1, 200, 0, b"BODY-X")
        fm.record_success(c, "detail", "123", URL, TS2, 200, 0, b"BODY-X")
        self.assertEqual(c.execute("SELECT count(*) FROM raw_fetches").fetchone()[0], 2)
        # second one is the unchanged re-fetch
        rows = c.execute("SELECT changed, parse_status FROM raw_fetches ORDER BY raw_id").fetchall()
        self.assertEqual(rows, [(1, "pending"), (0, "skipped_unchanged")])

    # 8
    def test_http_retry_decision_matrix(self):
        self.assertTrue(fm.should_retry(status=503))
        self.assertTrue(fm.should_retry(status=500))
        self.assertTrue(fm.should_retry(status=429))
        self.assertTrue(fm.should_retry(exc=ConnectionError()))
        self.assertTrue(fm.should_retry(exc=TimeoutError()))
        self.assertTrue(fm.should_retry(exc=urllib.error.URLError("boom")))
        self.assertTrue(fm.should_retry(exc=urllib.error.HTTPError(URL, 503, "x", {}, None)))
        self.assertFalse(fm.should_retry(status=404))
        self.assertFalse(fm.should_retry(status=410))
        self.assertFalse(fm.should_retry(status=400))
        self.assertFalse(fm.should_retry(exc=urllib.error.HTTPError(URL, 404, "x", {}, None)))

    # 9
    def test_outage_detection_threshold(self):
        od = fm.OutageDetector(threshold=5)
        for _ in range(4):
            self.assertFalse(od.record(503))
        self.assertTrue(od.record(503))   # 5th consecutive -> trip
        # reset behaviour on a fresh detector
        od2 = fm.OutageDetector(threshold=5)
        for _ in range(4):
            od2.record(503)
        od2.record(200)                    # 2xx resets the counter
        self.assertEqual(od2.consecutive, 0)
        self.assertFalse(od2.record(503))  # back to 1, not tripped

    # 10 — §2.1.1 normalization
    def test_normalize_strips_verification_as_of(self):
        b1 = json.dumps({"id": 1, "organization": {"verification": {"as_of": "2026-06-03T11:34:04Z"}}}).encode()
        b2 = json.dumps({"id": 1, "organization": {"verification": {"as_of": "2026-06-03T11:45:19Z"}}}).encode()
        self.assertEqual(fm._canonical_hash(b1, "application/json"),
                         fm._canonical_hash(b2, "application/json"))

    # 11
    def test_normalize_strips_both_verification_paths(self):
        b1 = json.dumps({"id": 1, "organization": {"verification": {"as_of": "A"}},
                         "owner": {"verification": {"as_of": "A"}}}).encode()
        b2 = json.dumps({"id": 1, "organization": {"verification": {"as_of": "B"}},
                         "owner": {"verification": {"as_of": "C"}}}).encode()
        self.assertEqual(fm._canonical_hash(b1, "application/json"),
                         fm._canonical_hash(b2, "application/json"))

    # 12
    def test_normalize_preserves_real_changes(self):
        b1 = json.dumps({"id": 1, "price": {"price": 250000},
                         "organization": {"verification": {"as_of": "A"}}}).encode()
        b2 = json.dumps({"id": 1, "price": {"price": 260000},
                         "organization": {"verification": {"as_of": "A"}}}).encode()
        self.assertNotEqual(fm._canonical_hash(b1, "application/json"),
                            fm._canonical_hash(b2, "application/json"))

    # 13
    def test_normalize_handles_missing_paths(self):
        b = json.dumps({"id": 1, "title": "x"}).encode()  # no organization / owner keys
        h = fm._canonical_hash(b, "application/json")
        self.assertEqual(len(h), 64)
        self.assertEqual(h, fm._canonical_hash(b, "application/json"))  # deterministic

    # 14
    def test_normalize_handles_non_json(self):
        b = b"<html>not json</html>"
        self.assertEqual(fm._canonical_hash(b, "text/html"), hashlib.sha256(b).hexdigest())
        # JSON content-type but unparseable body also falls back to raw hash
        self.assertEqual(fm._canonical_hash(b"BODY-X", "application/json"),
                         hashlib.sha256(b"BODY-X").hexdigest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
