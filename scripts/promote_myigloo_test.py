"""Unit tests for promote_myigloo (stdlib unittest, NO Supabase).

    python scripts/promote_myigloo_test.py

Uses the real PropsIndex populated with a tiny synthetic properties slice,
and the sanitized parsed_myigloo fixture (Step 1d) for title/row tests.
stdlib only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import promote_myigloo as pr  # noqa: E402
from normalize_address import normalize_address  # noqa: E402

# Holtsgata 14A, 101, 31.5 m², landreg fastnum 2005298 — mirrors the Step-1d fixture.
ADDR_NORM = normalize_address("Holtsgata 14A")


def make_idx(present=(), addr_entries=None, geo_entries=None):
    idx = pr.PropsIndex()
    idx.present = set(present)
    for key, rows in (addr_entries or {}).items():
        idx.by_addr[key] = rows
    for pc, rows in (geo_entries or {}).items():
        idx.by_postnr[pc] = rows
    return idx


BASE_LANDREG = {
    "source_listing_id": "23922", "listing_type_tag": "apartment", "landreg_source": "landreg",
    "fastnum_supplied": 2005298, "addr_street": "Holtsgata", "addr_number": "14A",
    "addr_postcode": "101", "size_sqm": 31.5, "lat": 64.146, "lng": -21.94,
}


class TestPromoteMyigloo(unittest.TestCase):

    # ── TAXONOMY lookup ──
    def test_taxonomy_lookup_apartment_residential(self):
        self.assertEqual(pr.TAXONOMY_LOOKUP["apartment"], ("residential", "rent", "apartment"))

    def test_taxonomy_lookup_storage_commercial(self):  # source-fidelity override
        self.assertEqual(pr.TAXONOMY_LOOKUP["storage"], ("commercial", "rent", "industrial_warehouse"))

    def test_taxonomy_lookup_cottage_summerhouse(self):  # §3 amendment
        self.assertEqual(pr.TAXONOMY_LOOKUP["cottage"], ("residential", "rent", "summerhouse"))

    # ── lease_term_class ──
    def test_lease_term_short(self):
        self.assertEqual(pr.derive_lease(3), "short_term")
        self.assertEqual(pr.derive_lease(5), "short_term")

    def test_lease_term_long(self):
        self.assertEqual(pr.derive_lease(6), "long_term")
        self.assertEqual(pr.derive_lease(13), "long_term")

    def test_lease_term_unspecified_on_null(self):  # ck_rent_lease binding
        self.assertEqual(pr.derive_lease(None), "unspecified")

    # ── listing_title COALESCE ──
    def test_listing_title_coalesce_title(self):
        self.assertEqual(pr._listing_title({"title": "Nice flat", "addr_street": "X", "addr_number": "1"}), "Nice flat")

    def test_listing_title_coalesce_addr_fallback(self):
        self.assertEqual(pr._listing_title({"title": None, "addr_street": "Holtsgata", "addr_number": "14A"}), "Holtsgata 14A")

    # ── fastnum resolution ──
    def test_resolve_fastnum_tier1_hit(self):
        idx = make_idx(present={2005298})
        self.assertEqual(pr.resolve_fastnum(BASE_LANDREG, idx, "apartment"), (2005298, 1.0, "source_supplied"))

    def test_resolve_fastnum_tier1_fk_miss_fallthrough(self):
        # fastnum_supplied NOT in properties -> falls through to address-match (2a, area within 5%)
        idx = make_idx(present=set(), addr_entries={(ADDR_NORM, "101"): [(2005298, 31.5, 64.146, -21.94)]})
        self.assertEqual(pr.resolve_fastnum(BASE_LANDREG, idx, "apartment"), (2005298, 0.95, "address_match"))

    def test_resolve_fastnum_tier1_manual_no_supplied(self):
        # manual source must not use Tier-1; with matching address -> address_match
        p = dict(BASE_LANDREG, landreg_source="manual", fastnum_supplied=None)
        idx = make_idx(addr_entries={(ADDR_NORM, "101"): [(2005298, 31.5, None, None)]})
        fn, conf, method = pr.resolve_fastnum(p, idx, "apartment")
        self.assertEqual((fn, method), (2005298, "address_match"))

    def test_resolve_fastnum_unresolvable_room(self):
        self.assertEqual(pr.resolve_fastnum(BASE_LANDREG, make_idx(), "room"),
                         (None, None, "unresolvable_by_design"))

    def test_resolve_fastnum_geo_match_within_30m(self):
        # no address match -> Tier-3 geo (same coords -> 0m)
        idx = make_idx(geo_entries={"101": [(2005298, 64.146, -21.94)]})
        p = dict(BASE_LANDREG, landreg_source="manual", fastnum_supplied=None, addr_street=None, addr_number=None)
        self.assertEqual(pr.resolve_fastnum(p, idx, "apartment"), (2005298, 0.55, "geo_match"))

    def test_resolve_fastnum_geo_miss_beyond_30m(self):
        idx = make_idx(geo_entries={"101": [(2005298, 65.0, -21.0)]})  # far away
        p = dict(BASE_LANDREG, landreg_source="manual", fastnum_supplied=None, addr_street=None, addr_number=None)
        self.assertEqual(pr.resolve_fastnum(p, idx, "apartment"), (None, None, None))

    # ── junk + row shape ──
    def test_is_junk_logic(self):
        cases = [
            # (price_amount, category, expected_skip)
            (0,     "residential", True),    # ck_price_pos: can't insert
            (0,     "commercial",  True),    # ck_price_pos: can't insert
            (1,     "residential", True),    # genuine residential junk
            (1,     "commercial",  False),   # price-on-request -> PROMOTE
            (100,   "residential", True),    # junk boundary
            (100,   "commercial",  False),   # price-on-request boundary -> PROMOTE
            (50000, "residential", False),   # normal rent
        ]
        for price, cat, exp in cases:
            with self.subTest(price=price, category=cat):
                self.assertEqual(pr._is_junk({"price_amount": price}, cat), exp)
        self.assertTrue(pr._is_junk({"price_amount": None}, "commercial"))  # NULL always skipped

    def test_canonical_row_has_39_columns(self):
        row = pr.build_canonical_row(BASE_LANDREG, "residential", "rent", "apartment", "long_term",
                                     2005298, 1.0, "source_supplied", "2026-06-03T00:00:00Z",
                                     "2026-06-03T01:00:00Z", "2026-06-03T02:00:00Z")
        self.assertEqual(len(row), 39)
        self.assertEqual(set(row.keys()), set(pr.CANONICAL_COLUMNS))
        self.assertEqual(row["surviving_source_priority"], 3)
        self.assertEqual(row["url"], "https://myigloo.is/listings/23922")
        self.assertEqual(row["lease_term_class"], "long_term")


if __name__ == "__main__":
    unittest.main(verbosity=2)
