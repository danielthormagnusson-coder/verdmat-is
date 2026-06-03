"""Unit tests for parse_myigloo (stdlib unittest, NO HTTP).

    python scripts/parse_myigloo_test.py

Fixture: scripts/fixtures/parsed_myigloo_fixture.json — a HAND-CRAFTED myigloo
detail payload (no real PII; owner.full_name + real_estate.owners are explicit
PII_*_SHOULD_BE_DROPPED sentinels so the overflow-scrub tests can assert they
never leak). Covers every extraction path. stdlib only.
"""
from __future__ import annotations

import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_myigloo as pm  # noqa: E402

FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "parsed_myigloo_fixture.json").read_text(encoding="utf-8"))


class TestParseMyigloo(unittest.TestCase):

    # ── numeric / nav helpers ──
    def test_to_decimal_handles_string_numbers(self):
        self.assertEqual(pm._to_decimal("295000.00"), Decimal("295000.00"))
        self.assertEqual(pm._to_decimal("31.50"), Decimal("31.50"))
        self.assertEqual(pm._to_decimal(2.0), Decimal("2.0"))

    def test_to_decimal_handles_null_and_empty(self):
        self.assertIsNone(pm._to_decimal(None))
        self.assertIsNone(pm._to_decimal(""))
        self.assertIsNone(pm._to_decimal("abc"))

    def test_to_int_round_trips(self):
        self.assertEqual(pm._to_int("13"), 13)
        self.assertEqual(pm._to_int(13), 13)
        self.assertEqual(pm._to_int(13.0), 13)
        self.assertIsNone(pm._to_int(None))
        self.assertIsNone(pm._to_int("x"))

    def test_safe_get_walks_nested(self):
        self.assertEqual(pm._safe_get({"a": {"b": {"c": 5}}}, "a.b.c"), 5)

    def test_safe_get_returns_none_on_missing_path(self):
        self.assertIsNone(pm._safe_get({"a": {}}, "a.b.c"))
        self.assertIsNone(pm._safe_get({}, "x.y"))
        self.assertIsNone(pm._safe_get({"a": 5}, "a.b"))  # non-dict mid-path

    # ── field extraction ──
    def test_extract_lysing_picks_primary_description_text(self):
        row = pm.parse_payload(FIXTURE)
        self.assertEqual(row["lysing"], FIXTURE["primary_description"]["text"])
        self.assertIn("þvottahúsi", row["lysing"])  # Icelandic original

    def test_extract_deposit_isk_from_insurance_price(self):
        row = pm.parse_payload(FIXTURE)
        self.assertEqual(row["deposit_isk"], Decimal("590000"))
        self.assertEqual(row["insurance_months"], 2)

    def test_extract_fastnum_when_landreg_source_is_landreg(self):
        self.assertEqual(pm._extract_fastnum({"landreg_source": "landreg", "landreg_id": "2299866"}), 2299866)
        self.assertEqual(pm.parse_payload(FIXTURE)["fastnum_supplied"], 2005298)

    def test_extract_fastnum_null_when_landreg_source_is_manual(self):
        self.assertIsNone(pm._extract_fastnum({"landreg_source": "manual", "landreg_id": None}))
        # even if an id is present, 'manual' source must not yield a fastnum
        self.assertIsNone(pm._extract_fastnum({"landreg_source": "manual", "landreg_id": "123456"}))

    def test_extract_address_fields_normalize_string_number_with_letter(self):
        row = pm.parse_payload(FIXTURE)
        self.assertEqual(row["addr_street"], "Holtsgata")
        self.assertEqual(row["addr_number"], "14A")     # letter suffix preserved as string
        self.assertEqual(row["addr_postcode"], "101")
        self.assertEqual(row["addr_city"], "Reykjavík")

    def test_extract_photos_json_handles_empty_list(self):
        self.assertEqual(pm._extract_photos([]), "[]")
        self.assertEqual(pm._extract_photos(None), "[]")
        self.assertEqual(json.loads(pm.parse_payload(FIXTURE)["photos_json"]),
                         ["https://myigloo.is/media/a.jpeg", "https://myigloo.is/media/b.jpeg"])

    def test_listing_type_tag_preserved_verbatim(self):
        row = pm.parse_payload(FIXTURE)
        self.assertEqual(row["listing_type_tag"], "apartment")
        self.assertEqual(row["category_tag"], "residential")
        self.assertEqual(row["tegund_raw"], "Íbúð")

    # ── overflow scrubbing ──
    def test_overflow_excludes_pii_paths(self):
        over = json.loads(pm.parse_payload(FIXTURE)["raw_overflow"])
        self.assertNotIn("owner", over)                       # whole owner object dropped
        self.assertNotIn("PII", json.dumps(over, ensure_ascii=False))   # no PII sentinel leaked
        self.assertNotIn("real_estate", over)                 # mapped -> not in overflow (owners[] PII gone too)

    def test_overflow_excludes_volatile_paths(self):
        over = json.loads(pm.parse_payload(FIXTURE)["raw_overflow"])
        self.assertIn("organization", over)                   # org kept (business, not PII)
        self.assertIsNone(over["organization"]["verification"]["as_of"])  # volatile stamp nulled
        self.assertNotIn("2026-06-03T11:34:04", json.dumps(over))         # timestamp value gone

    def test_overflow_includes_engagement_metrics_with_volatile_flag(self):
        over = json.loads(pm.parse_payload(FIXTURE)["raw_overflow"])
        self.assertEqual(over.get("views_count"), 42)
        self.assertEqual(over.get("application_count"), 6)
        self.assertIn("views_count", over["_volatile_suspect"])
        self.assertIn("application_count", over["_volatile_suspect"])

    # ── integration ──
    def test_full_parse_fixture_produces_expected_columns(self):
        row = pm.parse_payload(FIXTURE)
        expected_cols = set(pm._COLUMNS) - {"raw_id", "content_hash", "source_listing_id",
                                            "parser_version", "parsed_at"}
        self.assertTrue(expected_cols.issubset(set(row.keys())))
        self.assertEqual(row["price_amount"], Decimal("295000.00"))
        self.assertEqual(row["price_currency"], "ISK")
        self.assertEqual(row["size_sqm"], Decimal("31.50"))
        self.assertEqual(row["landreg_source"], "landreg")
        self.assertEqual(row["source_visible"], 1)
        self.assertIsNone(row["available_from"])
        self.assertIsNone(row["promoted_to_canonical_at"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
