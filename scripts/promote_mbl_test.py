"""Unit tests for promote_mbl (Step 3d): DP1 foreign filter (+ Icelandic override), DP2 tenure
cascade, fastano decomposition, DP3 price, category mapping, DP4 tenure-specific dedup priority,
and the pooler write path. stdlib unittest, NO pytest, NO live Supabase (mock conn captures writes)."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import promote_mbl as pm  # noqa: E402

NOW = datetime(2026, 6, 9, tzinfo=timezone.utc)


def cand(canonical_id="c1", source="visir", slid="v1", tenure="sale", fastnum=2500000,
         price=90000000, addr_norm="valshlíð 8", lat=64.13, lng=-21.92, fs=None, size_sqm=None):
    return {"canonical_id": canonical_id, "source": source, "source_listing_id": slid,
            "first_seen_at": fs or NOW, "tenure": tenure, "fastnum": fastnum,
            "price_amount": price, "addr_norm": addr_norm, "lat": lat, "lng": lng,
            "size_sqm": size_sqm}


class MockCursor:
    def __init__(self, store):
        self.store = store

    def execute(self, sql, params=None):
        self.store.append(sql)

    def mogrify(self, sql, params=None):
        return sql.encode("utf-8") if isinstance(sql, str) else bytes(sql)

    def fetchone(self):
        return None

    def fetchall(self):
        return []


class MockConn:
    def __init__(self):
        self.calls = []

    def cursor(self):
        return MockCursor(self.calls)

    def commit(self):
        self.calls.append("COMMIT")

    def rollback(self):
        self.calls.append("ROLLBACK")


def make_common(**over):
    c = {"source_listing_id": "1688798", "url": "u", "is_foreign": 0, "is_negotiable": 0,
         "teg_eign": "fjolb", "fastano": 2534030, "verd": 90900000, "lysing": "",
         "title": "Valshlíð 8", "addr_text": "Valshlíð 8", "postcode": 102,
         "lat": 64.13, "lng": -21.92, "area": 80, "rooms": 3, "bedrooms": 2, "bathrooms": 1,
         "municipality": None, "available_from": None, "tegund_raw": "fjolb",
         "photos_json": "[]", "first_seen": NOW, "last_seen": NOW, "parse_id": 1}
    c.update(over)
    return c


def make_row(**over):
    common = make_common(**over)
    m, raw, k = pm.decompose_fastano(common["fastano"])
    cat, sub = pm.decompose_category(common["teg_eign"], "sale", common["lysing"])
    return pm.build_canonical_row(common, "sale", cat, sub, None, 90900000, False,
                                  m, raw, 2534030, 1.0, "source_supplied", NOW.isoformat())


class TestPromoteMbl(unittest.TestCase):

    # ── DP1: foreign filter + Icelandic override ──
    def test_t1_foreign_happy_excludes(self):
        # genuine foreign: no domestic postcode, no Icelandic latitude
        self.assertTrue(pm.foreign_filter({"is_foreign": 1, "postcode": 3189, "lat": 37.9}))

    def test_t2_override_by_latitude_rescues_vesturvin(self):
        # sentinel postcode 1053 but Icelandic latitude -> kept (Vesturvin leak)
        self.assertFalse(pm.foreign_filter({"is_foreign": 1, "postcode": 1053, "lat": 64.1}))

    def test_t3_override_by_postcode(self):
        self.assertFalse(pm.foreign_filter({"is_foreign": 1, "postcode": 101, "lat": None}))

    def test_t4_non_foreign_kept(self):
        self.assertFalse(pm.foreign_filter({"is_foreign": 0, "postcode": 102, "lat": 64.1}))

    # ── DP2: tenure cascade ──
    def test_t5_cascade_priced_is_sale(self):
        self.assertEqual(pm.tenure_cascade({"is_negotiable": 0, "lysing": "til leigu"}), "sale")

    def test_t6_cascade_leigu_is_rent(self):
        self.assertEqual(pm.tenure_cascade(
            {"is_negotiable": 1, "lysing": "Glæsilegt húsnæði til leigu í miðbænum"}), "rent")

    def test_t7_cascade_solu_is_sale(self):
        self.assertEqual(pm.tenure_cascade(
            {"is_negotiable": 1, "lysing": "Eignin er til sölu, óskað er eftir tilboðum"}), "sale")

    def test_t8_cascade_neither_fallback_sale(self):
        self.assertEqual(pm.tenure_cascade({"is_negotiable": 1, "lysing": "engin merki hér"}), "sale")

    # ── fastano decomposition (truncation decode) ──
    def test_t9_decompose_7digit(self):
        self.assertEqual(pm.decompose_fastano(2534030), (0, 2534030, 1))

    def test_t10_decompose_8digit(self):
        m, raw, k = pm.decompose_fastano(20127542)
        self.assertEqual((m, raw, k), (2, 20127542, 10))
        self.assertEqual(20127542 // k, 2012754)            # derived 7-digit fastnum

    def test_t11_decompose_9digit(self):
        m, raw, k = pm.decompose_fastano(225687628)
        self.assertEqual((m, raw, k), (28, 225687628, 100))
        self.assertEqual(225687628 // k, 2256876)

    def test_t12_decompose_6digit_edge(self):
        self.assertEqual(pm.decompose_fastano(204130), (None, 204130, None))

    def test_t13_decompose_10digit_edge(self):
        self.assertEqual(pm.decompose_fastano(2041305260), (None, 2041305260, None))

    def test_t13b_decompose_none(self):
        self.assertEqual(pm.decompose_fastano(None), (None, None, None))

    # ── DP3: price ──
    def test_t14_price_positive(self):
        self.assertEqual(pm.resolve_price(90900000, "sale"), (90900000, False))

    def test_t15_price_zero_is_on_request(self):
        self.assertEqual(pm.resolve_price(0, "sale"), (1, True))

    def test_t15b_price_none_is_on_request(self):
        self.assertEqual(pm.resolve_price(None, "rent"), (1, True))

    def test_t15c_rent_price1_is_commercial_on_request(self):
        # Stage 8 finding: rent price<=1 => commercial-rent-on-request sentinel
        self.assertEqual(pm.resolve_price(1, "rent"), (1, True))

    def test_t15d_sale_price1_is_not_sentinel(self):
        # sale price=1 is not the POR signal (only rent uses the <=1 commercial sentinel)
        self.assertEqual(pm.resolve_price(1, "sale"), (1, False))

    def test_t15e_rent_real_price_not_sentinel(self):
        self.assertEqual(pm.resolve_price(172917, "rent"), (172917, False))

    # ── category / sub_type ──
    def test_t16_category_residential_apartment(self):
        self.assertEqual(pm.decompose_category("fjolb", "sale"), ("residential", "apartment"))

    def test_t17_category_commercial_keyword_office(self):
        self.assertEqual(pm.decompose_category("atv", "rent", "Til leigu skrifstofa við Borgartún"),
                         ("commercial", "office"))

    def test_t18_category_commercial_default(self):
        self.assertEqual(pm.decompose_category("atv", "sale", "ekkert lykilorð"),
                         ("commercial", "mixed_use_other"))

    def test_t19_category_plot_jord(self):
        self.assertEqual(pm.decompose_category("jord", "sale"), ("plot", "agricultural"))

    def test_t20_category_other_hesthus(self):
        self.assertEqual(pm.decompose_category("hesthus", "sale"), ("other", "equestrian"))

    def test_t20b_commercial_sub_type_keyword(self):
        self.assertEqual(pm.decompose_commercial_sub_type("Stór vörugeymsla til leigu"), "industrial_warehouse")

    def test_t20c_commercial_sub_type_fallback(self):
        self.assertEqual(pm.decompose_commercial_sub_type("ekkert lykilorð hér"), "mixed_use_other")

    # ── integration: tenure cascade -> category ──
    def test_t21_atv_negotiable_rent_is_commercial(self):
        common = {"is_negotiable": 1, "lysing": "Atvinnuhúsnæði til leigu, gott verslunarrými"}
        tenure = pm.tenure_cascade(common)
        cat, sub = pm.decompose_category("atv", tenure, common["lysing"])
        self.assertEqual((tenure, cat, sub), ("rent", "commercial", "retail"))

    # ── DP4: tenure-specific source_priority ──
    def test_t22_priority_mbl_sale_is_2(self):
        self.assertEqual(pm.source_priority("mbl", "sale"), 2)

    def test_t23_priority_mbl_rent_is_3(self):
        self.assertEqual(pm.source_priority("mbl", "rent"), 3)

    def test_t24_priority_myigloo_rent_is_2(self):
        self.assertEqual(pm.source_priority("myigloo", "rent"), 2)

    # ── survivor selection (tenure reversal) ──
    def test_t25_sale_mbl_loses_to_visir(self):
        action, target = pm.select_action([cand(source="visir", tenure="sale")], "sale")
        self.assertEqual(action, "mbl_loses"); self.assertEqual(target["source"], "visir")

    def test_t26_sale_mbl_wins_over_myigloo(self):
        action, _ = pm.select_action([cand(source="myigloo", tenure="sale")], "sale")
        self.assertEqual(action, "mbl_wins")

    def test_t27_rent_mbl_loses_to_myigloo(self):
        # tenure reversal: rent myigloo(2) > mbl(3) -> mbl folds
        action, _ = pm.select_action([cand(source="myigloo", tenure="rent")], "rent")
        self.assertEqual(action, "mbl_loses")

    def test_t28_insert_new_no_candidates(self):
        self.assertEqual(pm.select_action([], "sale"), ("insert_new", None))

    # ── dedup tier matching ──
    def test_t29_dedup_tier1_fastnum_same_tenure(self):
        idx = pm.CanonicalIndex(); idx.add(cand(tenure="sale", fastnum=2534030))
        c, tier = pm.find_dedup_candidates(idx, 2534030, "sale", None, 90000000, None, None, NOW)
        self.assertEqual(tier, "fastnum"); self.assertEqual(len(c), 1)

    def test_t30_dedup_size_disagreement_rejects(self):
        idx = pm.CanonicalIndex(); idx.add(cand(tenure="sale", fastnum=2534030, size_sqm=300))
        c, tier = pm.find_dedup_candidates(idx, 2534030, "sale", None, 90000000, None, None, NOW,
                                           size=60)   # multi-unit: same building fastnum, different unit
        self.assertEqual(c, []); self.assertIsNone(tier)

    # ── write path (pooler quirk) ──
    def test_t31_upsert_on_conflict_and_read_write_first(self):
        conn = MockConn()
        pm.apply_upsert(conn, make_row())
        exec_call = next(x for x in conn.calls if isinstance(x, (bytes, bytearray)))
        self.assertTrue(bytes(exec_call).startswith(b"SET TRANSACTION READ WRITE"))
        self.assertIn(b"ON CONFLICT (source, source_listing_id)", bytes(exec_call))

    def test_t32_row_carries_step3d_columns(self):
        row = make_row(fastano=20127542)
        self.assertEqual(row["matshluti_unit_id"], 2)
        self.assertEqual(row["source_raw_fastnum"], 20127542)
        self.assertEqual(row["is_price_on_request"], False)
        self.assertEqual(row["source"], "mbl")


if __name__ == "__main__":
    unittest.main(verbosity=2)
