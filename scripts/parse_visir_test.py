"""Unit tests for parse_visir. stdlib unittest, NO pytest. Real Phase-1c samples as
fixtures (no network) + synthetic edge cases.

    python -m unittest scripts.parse_visir_test -v
"""
from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_visir as pv                     # noqa: E402
import init_parsed_visir_schema as initpv    # noqa: E402

SAMPLES = Path(r"D:\verdmat-is\scraper_data\probe_visir_samples")


def parse_file(name, slid):
    p = SAMPLES / name
    if not p.is_file():
        return None
    return pv.VisirParser(None).parse_html_bytes(p.read_bytes(), raw_id=1,
                                                 content_hash="h", source_listing_id=slid)


def parse_bytes(html: bytes, slid="999"):
    return pv.VisirParser(None).parse_html_bytes(html, raw_id=1, content_hash="h",
                                                 source_listing_id=slid)


class TestParseVisir(unittest.TestCase):

    # T1 — real sale sample: core fields populated.
    def test_t1_real_sale_993646_parsing(self):
        f = parse_file("property_REAL_sale_993646.html", "993646")
        if f is None:
            self.skipTest("sample missing")
        self.assertTrue(f["title"])
        self.assertGreater(f["price_amount"], 0)
        self.assertGreater(f["size_sqm"], 0)
        self.assertTrue(f["tegund_raw"])
        self.assertTrue(63 < f["lat"] < 67, "lat must be a real Iceland coord, not _num-mangled")
        self.assertTrue(-25 < f["lng"] < -13, "lng must keep sign + decimal")
        self.assertGreater(f["fastnum_supplied"], 0)
        self.assertIn(f["tenure_signal"], ("sale", "unknown"))

    # T2 — CANARY: 1052249 came off the stype=rent index, but the detail HTML is a SALE
    # (79.9M total price, fjölbýlishús, no rent markers). Guards the stype≠tenure noise
    # documented in Step 2a closure.
    def test_t2_real_1052249_is_sale_not_rent(self):
        f = parse_file("property_REAL_rent_1052249.html", "1052249")
        if f is None:
            self.skipTest("sample missing")
        self.assertEqual(f["tenure_signal"], "sale")
        self.assertEqual(f["is_price_on_request"], 0)
        self.assertGreater(f["price_amount"], 0)

    # T2b — synthetic rent markers -> tenure_signal='rent'.
    def test_t2b_synthetic_rent_markers_classified_rent(self):
        html = ('<html><body>'
                '<span class="property__center-price">250.000 kr./mán</span>'
                '<span class="property__center-class">íbúðir</span>'
                '<p>Leiguverð: 250.000 kr./mán. Til leigu strax.</p>'
                '</body></html>').encode("utf-8")
        self.assertEqual(parse_bytes(html)["tenure_signal"], "rent")

    # T3 — real commercial-as-rent (Skútuvogur 12, Tilboð).
    def test_t3_real_commercial_as_rent_1056643(self):
        f = parse_file("property_REAL_rent_1056643.html", "1056643")
        if f is None:
            self.skipTest("sample missing")
        self.assertIn("atvinnu", (f["tegund_raw"] or "").lower())   # atvinnuhúsnæði
        self.assertEqual(f["is_price_on_request"], 1)
        self.assertIsNone(f["price_amount"])
        self.assertEqual(f["tenure_signal"], "rent")

    # T4 — Tilboð -> price NULL + on-request flag.
    def test_t4_price_tilbod_to_null(self):
        html = b'<html><body><span class="property__center-price">Tilbo\xc3\xb0</span></body></html>'
        f = parse_bytes(html)
        self.assertIsNone(f["price_amount"])
        self.assertEqual(f["is_price_on_request"], 1)

    # T5 — numeric price extracted.
    def test_t5_price_numeric_extracted(self):
        html = ('<html><body><span class="property__center-price">54.900.000 kr.</span>'
                '</body></html>').encode("utf-8")
        f = parse_bytes(html)
        self.assertEqual(f["price_amount"], 54900000)
        self.assertEqual(f["is_price_on_request"], 0)

    # T6 — fastnum label-anchored, not contaminated by stray 7-digit (analytics UA).
    def test_t6_fastnum_label_anchored(self):
        html = ('<html><body>'
                '<div class="property__bottom-item">'
                '<div class="property__bottom-text">Fasteignanúmer</div>'
                '<h4 class="property__bottom-title">F2123456</h4></div>'
                '<script>var ua="UA-4360339-3";</script>'   # stray 7-digit 4360339
                '</body></html>').encode("utf-8")
        self.assertEqual(parse_bytes(html)["fastnum_supplied"], 2123456)

    # T7 — address split preserves house-number letter suffix (§2.5-F).
    def test_t7_address_split_preserves_letter(self):
        html = ('<html><head>'
                '<meta property="og:title" content="Fasteignir: Kaupvangur 23A, 200 Kópavogur"/>'
                '</head><body>'
                '<span class="property__center-text">200 Kópavogur</span></body></html>').encode("utf-8")
        f = parse_bytes(html)
        self.assertEqual(f["addr_street"], "Kaupvangur")
        self.assertEqual(f["addr_number"], "23A")
        self.assertEqual(f["addr_postcode"], "200")
        self.assertEqual(f["addr_city"], "Kópavogur")

    # T8 — idempotency: same (content_hash, parser_version) inserts once.
    def test_t8_idempotency(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(initpv.PARSED_VISIR_DDL)
        p = pv.VisirParser(conn)
        f = parse_bytes(b'<html><body><span class="property__center-title">X</span></body></html>')
        f["content_hash"] = "samehash"
        p._insert(f); p._insert(f)        # second is a no-op via UNIQUE(content_hash, parser_version)
        conn.commit()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM parsed_visir").fetchone()[0], 1)

    # T9 — missing price selector -> price NULL, other fields still extracted.
    def test_t9_graceful_field_failure(self):
        html = ('<html><body><span class="property__center-title">Nice flat</span>'
                '<span class="property__center-class">íbúð</span></body></html>').encode("utf-8")
        f = parse_bytes(html)
        self.assertIsNone(f["price_amount"])
        self.assertEqual(f["title"], "Nice flat")
        self.assertEqual(f["tegund_raw"], "íbúð")

    # T10 — malformed HTML must not crash.
    def test_t10_malformed_html_no_crash(self):
        f = parse_bytes(b"<html><body><div class='property__center-price'>not closed <span>")
        self.assertIsInstance(f, dict)
        self.assertEqual(f["parser_version"], pv.PARSER_VERSION)

    # T11 — address from .property__center-title (primary source): unit stripped, letter kept.
    # og:title omits the house number on some listings, so center-title is primary.
    def test_t11_address_from_center_title_with_unit(self):
        html = ('<html><body>'
                '<span class="property__center-title">Borgartún 24B íbúð 202</span>'
                '<span class="property__center-text">105 Reykjavík</span></body></html>').encode("utf-8")
        f = parse_bytes(html)
        self.assertEqual(f["addr_street"], "Borgartún")
        self.assertEqual(f["addr_number"], "24B")          # unit "íbúð 202" stripped, letter kept


if __name__ == "__main__":
    unittest.main(verbosity=2)
