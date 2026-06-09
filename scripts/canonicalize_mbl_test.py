"""Unit tests for canonicalize_mbl (§2.1.1 mbl rule). stdlib unittest, NO pytest.

    python -m unittest scripts.canonicalize_mbl_test -v

Inline fixtures for the rule invariants; real Step-3a probe samples for the canonical-truth
tests (skipTest gracefully if the gitignored samples are absent on a clean checkout).
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canonicalize_mbl as cz  # noqa: E402

SAMPLES = Path(r"D:\verdmat-is\scraper_data\probe_samples\mbl")


def _h(b):
    return hashlib.sha256(b).hexdigest()


class TestCanonicalizeMbl(unittest.TestCase):

    # T1 — deterministic: same input twice -> same hash.
    def test_t1_deterministic_stability(self):
        body = b'{"data":{"x":[1,2,3],"y":"abc"}}'
        _, h1 = cz.canonicalize_mbl(body, "application/json")
        _, h2 = cz.canonicalize_mbl(body, "application/json")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    # T2 — sorted-keys: different key order -> SAME hash.
    def test_t2_sorted_keys_insurance(self):
        _, h_ab = cz.canonicalize_mbl(b'{"a":1,"b":2}', "application/json")
        _, h_ba = cz.canonicalize_mbl(b'{"b":2,"a":1}', "application/json")
        self.assertEqual(h_ab, h_ba)

    # T3 — whitespace: spacing-only difference -> SAME hash.
    def test_t3_whitespace_normalization(self):
        _, h_space = cz.canonicalize_mbl(b'{"a": 1, "b":  2}', "application/json")
        _, h_tight = cz.canonicalize_mbl(b'{"a":1,"b":2}', "application/json")
        self.assertEqual(h_space, h_tight)

    # T4 — real sale list page: stable across 10 invocations.
    def test_t4_real_sale_list_stable(self):
        p = SAMPLES / "sale_sample_5.json"
        if not p.is_file():
            self.skipTest("sale_sample_5.json not present")
        body = p.read_bytes()
        hashes = {cz.canonicalize_mbl(body, "application/json")[1] for _ in range(10)}
        self.assertEqual(len(hashes), 1)

    # T5 — real rent list page: stable across 10 invocations.
    def test_t5_real_rent_list_stable(self):
        p = SAMPLES / "rent_sample_5.json"
        if not p.is_file():
            self.skipTest("rent_sample_5.json not present")
        body = p.read_bytes()
        hashes = {cz.canonicalize_mbl(body, "application/json")[1] for _ in range(10)}
        self.assertEqual(len(hashes), 1)

    # T6 — real nested object: sorted-keys handles nested dicts (agency/images/postal_code).
    def test_t6_real_nested_deterministic(self):
        p = SAMPLES / "sale_detail_one.json"
        if not p.is_file():
            self.skipTest("sale_detail_one.json not present")
        body = p.read_bytes()
        c1, h1 = cz.canonicalize_mbl(body, "application/json")
        c2, h2 = cz.canonicalize_mbl(body, "application/json")
        self.assertEqual(h1, h2)
        self.assertEqual(c1, c2)
        # canonical form is the sorted-keys re-serialization (not the raw bytes, given spacing)
        self.assertEqual(h1, _h(c1))

    # T7 — non-JSON content_type -> raw-sha256 fallback, no parse attempt.
    def test_t7_non_json_fallback(self):
        body = b"<html>not json</html>"
        canon, h = cz.canonicalize_mbl(body, "text/html")
        self.assertEqual(canon, body)
        self.assertEqual(h, _h(body))

    # T8 — malformed JSON -> fallback, must NOT raise.
    def test_t8_malformed_json_fallback(self):
        body = b'{not valid json'
        canon, h = cz.canonicalize_mbl(body, "application/json")
        self.assertEqual(canon, body)
        self.assertEqual(h, _h(body))

    # T9 — empty body -> fallback (sha256 of empty), no crash.
    def test_t9_empty_body(self):
        canon, h = cz.canonicalize_mbl(b"", "application/json")
        self.assertEqual(canon, b"")
        self.assertEqual(h, _h(b""))

    # T10 — content_type with charset suffix still treated as JSON.
    def test_t10_charset_suffix_json(self):
        body = b'{"a":1,"b":2}'
        _, h_plain = cz.canonicalize_mbl(body, "application/json")
        _, h_charset = cz.canonicalize_mbl(body, "application/json; charset=utf-8")
        self.assertEqual(h_plain, h_charset)


if __name__ == "__main__":
    unittest.main(verbosity=2)
