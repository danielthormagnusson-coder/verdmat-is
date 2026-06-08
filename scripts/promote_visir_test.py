"""Unit tests for promote_visir (§2.3 decomposition + §2.5 fastnum + §4 dedup). stdlib
unittest, NO pytest, NO live Supabase (mock connection captures writes)."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import promote_visir as pv  # noqa: E402

NOW = datetime(2026, 6, 8, tzinfo=timezone.utc)


def cand(canonical_id="c1", source="myigloo", slid="m1", tenure="rent", fastnum=2500000,
         price=300000, addr_norm="holtsgata 14a", lat=64.14, lng=-21.9, fs=None, size_sqm=None):
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

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class MockConn:
    def __init__(self):
        self.calls = []

    def cursor(self):
        return MockCursor(self.calls)

    def commit(self):
        self.calls.append("COMMIT")

    def rollback(self):
        self.calls.append("ROLLBACK")


def make_row(**over):
    p = {"source_listing_id": "999", "title": "X", "lysing": "", "tegund_raw": "fjölbýlishús",
         "tenure_signal": "sale", "price_amount": 50000000, "is_price_on_request": 0,
         "size_sqm": 80, "rooms": 3, "bedrooms": 2, "bathrooms": 1,
         "addr_street": "Holtsgata", "addr_number": "14A", "addr_postcode": "101",
         "addr_city": "Reykjavík", "lat": 64.14, "lng": -21.9, "fastnum_supplied": None,
         "photos_json": None, "parse_id": 1, "price_currency": "ISK"}
    p.update(over)
    cat, ten, sub = pv.decompose(p["tegund_raw"], p["tenure_signal"], p["title"], p["lysing"])
    price = pv.resolve_price(p["price_amount"], p["is_price_on_request"], cat)
    return pv.build_canonical_row(p, cat, ten, sub, pv.derive_lease(ten), price, None, None, None,
                                  NOW, NOW, NOW.isoformat())


class TestPromoteVisir(unittest.TestCase):

    # ── decomposition ──
    def test_t1_decompose_apartment(self):
        self.assertEqual(pv.decompose("fjölbýlishús", "sale", "x", ""), ("residential", "sale", "apartment"))

    def test_t2_decompose_commercial_office(self):
        self.assertEqual(pv.decompose("atvinnuhúsnæði", "rent", "Til leigu",
                                      "Glæsilegt skrifstofuhúsnæði við Borgartún"),
                         ("commercial", "rent", "office"))

    def test_t3_decompose_plot_residential(self):
        self.assertEqual(pv.decompose("lóð", "sale", "Lóð", "Falleg íbúðarhúsalóð í hverfinu"),
                         ("plot", "sale", "residential_plot"))

    def test_t3b_decompose_commercial_default(self):
        self.assertEqual(pv.decompose("atvinnuhúsnæði", "rent", "x", "ekkert lykilorð")[2],
                         "mixed_use_other")

    def test_t4_decompose_unknown_raises(self):
        with self.assertRaises(ValueError):
            pv.decompose("vélsleði", "sale", "x", "")

    # ── price ──
    def test_t5_price_tilbod_commercial(self):
        self.assertEqual(pv.resolve_price(None, 1, "commercial"), 1)

    def test_t6_price_tilbod_residential(self):
        self.assertIsNone(pv.resolve_price(None, 1, "residential"))

    def test_t7_price_junk_residential(self):
        self.assertIsNone(pv.resolve_price(50, 0, "residential"))

    def test_t8_price_low_commercial_ok(self):
        self.assertEqual(pv.resolve_price(50, 0, "commercial"), 50)

    def test_t9_price_zero_skip(self):
        self.assertIsNone(pv.resolve_price(0, 0, "commercial"))

    # ── fastnum (§2.5) ──
    def test_t10_fastnum_tier1_source_supplied(self):
        idx = pv.PropsIndex(); idx.present = {2534030}
        self.assertEqual(pv.resolve_fastnum({"fastnum_supplied": 2534030}, idx),
                         (2534030, 1.0, "source_supplied"))

    def test_t11_fastnum_fallthrough_to_address(self):
        idx = pv.PropsIndex()
        from normalize_address import normalize_address
        idx.by_addr[(normalize_address("Holtsgata 14A"), "101")] = [(2534030, 80.0, 64.14, -21.9)]
        p = {"fastnum_supplied": 9999999, "addr_street": "Holtsgata", "addr_number": "14A",
             "addr_postcode": "101", "size_sqm": 80}
        fn, conf, method = pv.resolve_fastnum(p, idx)   # supplied not in props -> address match
        self.assertEqual((fn, method), (2534030, "address_match"))

    # ── §4 dedup ──
    def test_t12_dedup_tier1_fastnum_same_tenure_matches(self):
        idx = pv.CanonicalIndex(); idx.add(cand(tenure="rent", fastnum=2500000))
        c, tier = pv.find_dedup_candidates(idx, 2500000, "rent", None, 300000, None, None, NOW)
        self.assertEqual(tier, "fastnum"); self.assertEqual(len(c), 1)

    def test_t13_dedup_tier1_different_tenure_no_match(self):
        idx = pv.CanonicalIndex(); idx.add(cand(tenure="rent", fastnum=2500000))
        c, tier = pv.find_dedup_candidates(idx, 2500000, "sale", None, 300000, None, None, NOW)
        self.assertEqual(c, []); self.assertIsNone(tier)   # sale != rent -> no fold

    def test_t14_dedup_tier2_addr_price_window(self):
        idx = pv.CanonicalIndex()
        idx.add(cand(fastnum=None, addr_norm="holtsgata 14a", tenure="rent", price=300000, fs=NOW))
        c, tier = pv.find_dedup_candidates(idx, None, "rent", "holtsgata 14a", 305000, None, None,
                                           NOW + timedelta(days=3))
        self.assertEqual(tier, "addr"); self.assertEqual(len(c), 1)

    def test_t14b_dedup_tier2_outside_window_no_match(self):
        idx = pv.CanonicalIndex()
        idx.add(cand(fastnum=None, addr_norm="holtsgata 14a", tenure="rent", price=300000, fs=NOW))
        c, tier = pv.find_dedup_candidates(idx, None, "rent", "holtsgata 14a", 305000, None, None,
                                           NOW + timedelta(days=30))
        self.assertEqual(c, [])    # 30 days > 14-day window

    # ── survivor selection ──
    def test_t15_visir_wins_over_myigloo(self):
        action, target = pv.select_action([cand(source="myigloo")])
        self.assertEqual(action, "visir_wins"); self.assertEqual(target["source"], "myigloo")

    def test_t16_insert_new_on_no_candidates(self):
        self.assertEqual(pv.select_action([]), ("insert_new", None))

    def test_t16b_visir_loses_to_other_visir(self):
        action, _ = pv.select_action([cand(source="visir")])
        self.assertEqual(action, "visir_loses")

    # ── write paths ──
    def test_t17_insert_uses_on_conflict(self):
        conn = MockConn()
        pv.upsert_new(conn, make_row())
        joined = " ".join(str(x) for x in conn.calls)
        self.assertIn("ON CONFLICT (source, source_listing_id)", joined)

    def test_t18_pooler_set_transaction_read_write_first(self):
        conn = MockConn()
        pv.upsert_new(conn, make_row())
        # the single execute() arg must START with the read-write directive
        exec_call = next(x for x in conn.calls if isinstance(x, (bytes, bytearray)))
        self.assertTrue(bytes(exec_call).startswith(b"SET TRANSACTION READ WRITE"))

    # ── §4 false-positive reject rules ──
    def test_t19_fastnum_disagreement_rejects(self):
        visir = {"fastnum": 2121211, "size_sqm": 79}
        candidate = {"fastnum": 2313904, "size_sqm": 80}        # different fastnum, similar size
        rej, reason = pv._reject_match(visir, candidate)
        self.assertTrue(rej); self.assertEqual(reason, "fastnum_disagreement")

    def test_t20_size_disagreement_rejects(self):
        visir = {"fastnum": 2252816, "size_sqm": 50}            # small unit
        candidate = {"fastnum": 2252816, "size_sqm": 300}       # same fastnum, large unit (multi-unit bldg)
        rej, reason = pv._reject_match(visir, candidate)
        self.assertTrue(rej); self.assertEqual(reason, "size_disagreement")

    def test_t21_both_rules_pass_on_genuine_match(self):
        visir = {"fastnum": 2030135, "size_sqm": 93.8}
        candidate = {"fastnum": 2030135, "size_sqm": 94.2}      # same fastnum, size within 10%
        rej, _ = pv._reject_match(visir, candidate)
        self.assertFalse(rej)

    def test_t21b_filter_drops_fastnum_mismatch_from_tier(self):
        idx = pv.CanonicalIndex()
        idx.add(cand(tenure="rent", fastnum=2313904, addr_norm="x 1", price=1))
        # visir has a DIFFERENT fastnum -> tier-2 addr match must be filtered out
        c, tier = pv.find_dedup_candidates(idx, 2121211, "rent", "x 1", 1, None, None, NOW, size=79)
        self.assertEqual(c, []); self.assertIsNone(tier)

    # ── Rule 3: commercial Tier-1 corroboration ──
    def test_t22_commercial_tier1_rejected_without_corroborator(self):
        idx = pv.CanonicalIndex()
        idx.add(cand(tenure="rent", fastnum=2252816, addr_norm="skútuvogur 12", price=1, size_sqm=86.9))
        c, tier = pv.find_dedup_candidates(idx, 2252816, "rent", "skútuvogur 12", 1, None, None, NOW,
                                           size=0, category="commercial")   # size 0 + price sentinel
        self.assertEqual(c, []); self.assertIsNone(tier)

    def test_t23_commercial_tier1_accepted_with_size_corroborator(self):
        idx = pv.CanonicalIndex()
        idx.add(cand(tenure="rent", fastnum=2252816, addr_norm="skútuvogur 12", price=1, size_sqm=150))
        c, tier = pv.find_dedup_candidates(idx, 2252816, "rent", "skútuvogur 12", 1, None, None, NOW,
                                           size=148, category="commercial")   # size within 10%
        self.assertEqual(len(c), 1); self.assertEqual(tier, "fastnum")

    def test_t24_residential_tier1_no_corroborator_required(self):
        idx = pv.CanonicalIndex()
        idx.add(cand(tenure="rent", fastnum=2030135, addr_norm="mávahlíð 15", price=None, size_sqm=None))
        c, tier = pv.find_dedup_candidates(idx, 2030135, "rent", "mávahlíð 15", None, None, None, NOW,
                                           size=None, category="residential")   # Rule 3 N/A
        self.assertEqual(len(c), 1); self.assertEqual(tier, "fastnum")


if __name__ == "__main__":
    unittest.main(verbosity=2)
