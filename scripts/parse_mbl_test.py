"""Unit tests for parse_mbl + init_parsed_mbl_schema. stdlib unittest, NO pytest.

NEVER touches the real raw_mbl.db / parsed_mbl.db: in-memory raw + parsed schemas,
synthetic blobs, plus the REAL probe fixtures from probe_samples/mbl/ (v2_enriched
mini-probe responses + v1-shaped sale/rent samples) — skipped gracefully if absent.

    python -m unittest scripts.parse_mbl_test -v
"""
from __future__ import annotations

import gzip
import json
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_mbl as pm                       # noqa: E402
import init_parsed_mbl_schema as initp       # noqa: E402
import init_raw_mbl_schema as initraw        # noqa: E402
from canonicalize_mbl import canonicalize_mbl  # noqa: E402
from scraper_paths import get_scraper_data_dir  # noqa: E402

FIXDIR = get_scraper_data_dir() / "probe_samples" / "mbl"


def parsed_conn():
    c = sqlite3.connect(":memory:")
    initp.init_schema_on_conn(c)
    return c


def raw_conn():
    c = sqlite3.connect(":memory:")
    c.executescript(initraw.RAW_BLOBS_DDL + initraw.RAW_FETCHES_DDL)
    c.execute(initraw.IX_LISTING)
    c.execute(initraw.IX_PARSE)
    return c


def blob_bytes(root_key, listings):
    return json.dumps({"data": {root_key: listings}}).encode("utf-8")


def insert_raw(rc, body, *, kind, url, fetched_at):
    _, chash = canonicalize_mbl(body, "application/json")
    rc.execute("INSERT OR IGNORE INTO raw_blobs(content_hash, blob_gz, content_type, "
               "byte_len, first_stored) VALUES(?,?,?,?,?)",
               (chash, gzip.compress(body), "application/json", len(body), fetched_at))
    rc.execute("INSERT INTO raw_fetches(source, source_listing_id, url, fetch_kind, "
               "fetched_at, http_status, content_hash, changed, retry_count, parse_status) "
               "VALUES('mbl',NULL,?,?,?,200,?,1,0,'pending')", (url, kind, fetched_at, chash))
    rc.commit()
    return chash


def sale_listing(eign_id, **kw):
    L = {"eign_id": eign_id, "fastano": 1234567, "gata": "Testgata",
         "heimilisfang": "Testgata 1", "normalized_heimilisfang": "testgata 1",
         "postfang": 101, "teg_eign": "fjolb", "fermetrar": 100, "fermetraverd": 500000,
         "fjoldi_herb": 3, "fjoldi_svefnhb": 2, "fjoldi_badherb": 1, "verd": 50000000,
         "fasteignamat": 45000000, "brunabotamat": 30000000, "bygg_ar": 2000,
         "nybygging": False, "latitude": 64.1, "longitude": -21.9, "hverfi": None,
         "lysing": "<p>Fín eign</p>", "sent_dags": "2026-06-09T09:00:00+00:00",
         "br_dags": "2026-06-09T09:00:00+00:00"}
    L.update(kw)
    return L


def rent_listing(rid, **kw):
    L = {"id": rid, "address": "Testgata 2", "normalized_address": "testgata 2",
         "zipcode": 201, "title": "Testgata 2", "type_id": 2, "size": 80, "price": 300000,
         "rooms": 3, "available_from": None, "available_until": None, "longtime": True,
         "lift": False, "pet_allowed": False, "wheelchair_acc": False,
         "created": "2026-05-29T15:13:23.46216", "updated": "2026-05-29T15:13:23.462184",
         "description": "<p>Til leigu</p>"}
    L.update(kw)
    return L


def meta(fetched_at="2026-06-10T00:00:00+00:00"):
    return {"raw_id": 1, "content_hash": "h", "fetched_at": fetched_at,
            "parser_version": pm.PARSER_VERSION, "parsed_at": "2026-06-11T00:00:00+00:00"}


def table_dump(pc, table):
    return pc.execute("SELECT * FROM %s ORDER BY source_listing_id" % table).fetchall()


class TestParseMbl(unittest.TestCase):

    # ── schema ──
    def test_t1_schema_init_idempotent(self):
        c = sqlite3.connect(":memory:")
        info1 = initp.init_schema_on_conn(c)
        info2 = initp.init_schema_on_conn(c)
        self.assertFalse(info1["already_existed"])
        self.assertTrue(info2["already_existed"])
        self.assertEqual(info1["n_sale_columns"], info2["n_sale_columns"])
        # every parser output column exists in the table
        sale_cols = {r[1] for r in c.execute("PRAGMA table_info(parsed_mbl_sale)")}
        rent_cols = {r[1] for r in c.execute("PRAGMA table_info(parsed_mbl_rent)")}
        self.assertTrue(set(pm.SALE_COLUMNS).issubset(sale_cols))
        self.assertTrue(set(pm.RENT_COLUMNS).issubset(rent_cols))

    # ── generation detection (both directions, on REAL fixtures where present) ──
    def test_t2_generation_detection_synthetic(self):
        self.assertEqual(pm.detect_fields_version([sale_listing(1)]), pm.V1)
        self.assertEqual(pm.detect_fields_version([sale_listing(1, images=[])]), pm.V2)
        self.assertEqual(pm.detect_fields_version([]), pm.V1)   # empty page: nothing to parse

    def test_t3_generation_detection_real_fixtures(self):
        cases = (("sale_sample_5.json", "fs_fasteign", pm.V1),
                 ("rent_sample_5.json", "rentals_property", pm.V1),
                 ("enriched_sale_16.json", "fs_fasteign", pm.V2),
                 ("enriched_rent_16.json", "rentals_property", pm.V2))
        for fname, root_key, expect in cases:
            f = FIXDIR / fname
            if not f.is_file():
                self.skipTest("fixture %s not present" % fname)
            with self.subTest(fixture=fname):
                listings = json.loads(f.read_bytes())["data"][root_key]
                self.assertEqual(pm.detect_fields_version(listings), expect)

    # ── precedence ──
    def test_t4_upsert_precedence_v2_over_v1_and_fetched_at(self):
        pc = parsed_conn()
        mk = lambda fv, ts, verd: pm.parse_sale_listing(
            sale_listing(42, verd=verd, **({"images": []} if fv == pm.V2 else {})),
            meta(ts), fv, [])
        # three upserts, deliberately out of order:
        r1 = pm.upsert_row(pc, "parsed_mbl_sale", mk(pm.V1, "2026-06-10T03:00:00+00:00", 111))
        r2 = pm.upsert_row(pc, "parsed_mbl_sale", mk(pm.V2, "2026-06-10T01:00:00+00:00", 222))
        r3 = pm.upsert_row(pc, "parsed_mbl_sale", mk(pm.V1, "2026-06-10T05:00:00+00:00", 333))
        self.assertEqual((r1, r2, r3), ("inserted", "replaced", "skipped"))
        fv, verd = pc.execute("SELECT fields_version, verd FROM parsed_mbl_sale "
                              "WHERE source_listing_id=42").fetchone()
        self.assertEqual((fv, verd), (pm.V2, 222))   # v2 beat BOTH v1s despite older fetched_at
        # within v2: newer fetched_at wins
        r4 = pm.upsert_row(pc, "parsed_mbl_sale", mk(pm.V2, "2026-06-10T02:00:00+00:00", 444))
        self.assertEqual(r4, "replaced")
        self.assertEqual(pc.execute("SELECT verd FROM parsed_mbl_sale "
                                    "WHERE source_listing_id=42").fetchone()[0], 444)
        # exact tie -> skipped (idempotency primitive)
        r5 = pm.upsert_row(pc, "parsed_mbl_sale", mk(pm.V2, "2026-06-10T02:00:00+00:00", 555))
        self.assertEqual(r5, "skipped")
        self.assertEqual(pc.execute("SELECT COUNT(*) FROM parsed_mbl_sale").fetchone()[0], 1)

    # ── idempotent re-parse (full run loop, real v2 fixtures if present) ──
    def test_t5_reparse_idempotent(self):
        rc, pc = raw_conn(), parsed_conn()
        f = FIXDIR / "enriched_sale_16.json"
        if f.is_file():
            body = f.read_bytes()
            url = "https://g.mbl.is/v1/graphql?op=list_sale&offset=0&fields=v2"
        else:
            body = blob_bytes("fs_fasteign", [sale_listing(i) for i in (1, 2, 3)])
            url = "https://g.mbl.is/v1/graphql?op=list_sale&offset=0"
        insert_raw(rc, body, kind="list_page_sale", url=url,
                   fetched_at="2026-06-10T00:00:00+00:00")
        s1 = pm.run(rc, pc, log=lambda *a: None)
        dump1 = table_dump(pc, "parsed_mbl_sale")
        s2 = pm.run(rc, pc, reparse=True, log=lambda *a: None)
        dump2 = table_dump(pc, "parsed_mbl_sale")
        self.assertGreater(s1["inserted"], 0)
        self.assertEqual(s2["inserted"] + s2["replaced"], 0)        # all skipped
        self.assertEqual(s2["skipped"], s1["inserted"])
        self.assertEqual(dump1, dump2)                               # byte-identical incl parsed_at
        self.assertEqual(s1["failed_blobs"], 0)

    # ── sentinels + negotiable ──
    def test_t6_sale_sentinel_zero_to_null(self):
        row = pm.parse_sale_listing(
            sale_listing(7, fastano=0, fasteignamat=0, brunabotamat=0, fermetraverd=0,
                         bygg_ar=0), meta(), pm.V1, [])
        for c in ("fastano", "fasteignamat", "brunabotamat", "fermetraverd", "bygg_ar"):
            self.assertIsNone(row[c], c)
        self.assertEqual(row["verd"], 50000000)      # verd is NOT a 0->NULL column

    def test_t7_is_negotiable_both_roots(self):
        s = pm.parse_sale_listing(sale_listing(8, verd=0), meta(), pm.V1, [])
        self.assertEqual((s["is_negotiable"], s["verd"]), (1, 0))    # raw 0 kept in verd
        s2 = pm.parse_sale_listing(sale_listing(9, verd=1000), meta(), pm.V1, [])
        self.assertEqual(s2["is_negotiable"], 0)
        r = pm.parse_rent_listing(rent_listing(10, price=0), meta(), pm.V1, [])
        self.assertEqual((r["is_negotiable"], r["price"]), (1, 0))

    # ── is_foreign ──
    def test_t8_is_foreign_spain_and_iceland(self):
        # the real Spánarheimili case: postfang 1053 outside 101-902
        s = pm.parse_sale_listing(sale_listing(11, postfang=1053, latitude=37.97864827694563,
                                               longitude=-0.7885337333328358),
                                  meta(), pm.V1, [])
        self.assertEqual(s["is_foreign"], 1)
        # postfang 806 is INSIDE 101-902 — bbox must catch it
        s2 = pm.parse_sale_listing(sale_listing(12, postfang=806, latitude=38.54,
                                                longitude=-0.18), meta(), pm.V1, [])
        self.assertEqual(s2["is_foreign"], 1)
        # Icelandic listing
        s3 = pm.parse_sale_listing(sale_listing(13), meta(), pm.V1, [])
        self.assertEqual(s3["is_foreign"], 0)
        # NULL coords alone do NOT flag (28.8% of sale rows)
        s4 = pm.parse_sale_listing(sale_listing(14, latitude=None, longitude=None),
                                   meta(), pm.V1, [])
        self.assertEqual(s4["is_foreign"], 0)
        # rent: zipcode only
        r = pm.parse_rent_listing(rent_listing(15, zipcode=1053), meta(), pm.V1, [])
        self.assertEqual(r["is_foreign"], 1)

    # ── Hashie::Mash corruption ──
    def test_t9_hashie_strip_and_flag(self):
        bad = 'Dugguvogur 50#<Hashie::Mash @xml:space="preserve">'
        r = pm.parse_rent_listing(rent_listing(16, address=bad, title=bad,
                                               normalized_address=bad.lower()),
                                  meta(), pm.V1, [])
        self.assertEqual(r["address"], "Dugguvogur 50")
        self.assertEqual(r["title"], "Dugguvogur 50")
        self.assertEqual(r["normalized_address"], "dugguvogur 50")
        self.assertEqual(r["address_corrupt"], 1)
        clean = pm.parse_rent_listing(rent_listing(17), meta(), pm.V1, [])
        self.assertEqual(clean["address_corrupt"], 0)

    # ── image ordering ──
    def test_t10_sale_imgno_sort(self):
        imgs = [{"imgno": 3, "big": "c"}, {"imgno": 1, "big": "a"}, {"imgno": 2, "big": "b"}]
        row = pm.parse_sale_listing(sale_listing(18, images=imgs), meta(), pm.V2, [])
        out = json.loads(row["images_json"])
        self.assertEqual([i["imgno"] for i in out], [1, 2, 3])

    def test_t11_rent_ordering_null_fallback(self):
        imgs = [{"ordering": None, "id": 9}, {"ordering": 2, "id": 2},
                {"ordering": None, "id": 8}, {"ordering": 1, "id": 1}]
        row = pm.parse_rent_listing(rent_listing(19, images=imgs), meta(), pm.V2, [])
        out = json.loads(row["images_json"])
        # keyed images sorted by ordering first; NULL-ordering keep array order, after
        self.assertEqual([i["id"] for i in out], [1, 2, 9, 8])
        # determinism: same input -> identical bytes
        row2 = pm.parse_rent_listing(rent_listing(19, images=imgs), meta(), pm.V2, [])
        self.assertEqual(row["images_json"], row2["images_json"])

    # ── timestamps ──
    def test_t12_tz_normalization(self):
        r = pm.parse_rent_listing(rent_listing(20), meta(), pm.V1, [])
        self.assertEqual(r["created"], "2026-05-29T15:13:23.46216+00:00")
        self.assertEqual(r["updated"], "2026-05-29T15:13:23.462184+00:00")
        s = pm.parse_sale_listing(sale_listing(21, created="2026-06-09T09:44:14.247128"),
                                  meta(), pm.V1, [])
        self.assertEqual(s["sent_dags"], "2026-06-09T09:00:00+00:00")   # passthrough
        self.assertEqual(s["created"], "2026-06-09T09:44:14.247128+00:00")
        self.assertEqual(pm._tz_normalize("2026-01-01T00:00:00Z"), "2026-01-01T00:00:00Z")
        self.assertIsNone(pm._tz_normalize(None))

    # ── HTML strip ──
    def test_t13_html_strip_deterministic(self):
        html = ('<p></p><strong>Fasteignamarkaðurinn ehf. s: '
                '<a href="tel:570-4500">570-4500</a></strong><br />Til sölu '
                '&amp; leígu  <u>flótt</u>')
        t1, t2 = pm.html_to_text(html), pm.html_to_text(html)
        self.assertEqual(t1, t2)                                # deterministic
        self.assertNotIn("<", t1)                               # tags gone
        self.assertIn("&", t1)                                  # &amp; unescaped once
        self.assertIn("\n", t1)                                 # <br/> became newline
        self.assertIsNone(pm.html_to_text(None))
        self.assertIsNone(pm.html_to_text(""))

    # ── v1 blob: nested NULL, no crash, no skip ──
    def test_t14_v1_blob_nested_null(self):
        rows, fv = pm.parse_blob(
            blob_bytes("fs_fasteign", [sale_listing(22), sale_listing(23)]),
            root="sale", url="https://g.mbl.is/v1/graphql?op=list_sale&offset=0",
            raw_id=1, content_hash="h", fetched_at="2026-06-10T00:00:00+00:00")
        self.assertEqual(fv, pm.V1)
        self.assertEqual(len(rows), 2)
        for row in rows:
            for col in ("images_json", "agency_json", "attachments_json",
                        "openhouse_json", "postal_code_json", "promo_json"):
                self.assertIsNone(row[col])
            self.assertIsNone(row["flags"])                     # no marker, v1: consistent

    # ── fields marker cross-check ──
    def test_t15_fields_marker_mismatch_flag(self):
        # v2-shaped blob but URL WITHOUT fields=v2 -> flag (and vice versa)
        rows, _ = pm.parse_blob(
            blob_bytes("fs_fasteign", [sale_listing(24, images=[])]),
            root="sale", url="https://g.mbl.is/v1/graphql?op=list_sale&offset=0",
            raw_id=1, content_hash="h", fetched_at="2026-06-10T00:00:00+00:00")
        self.assertEqual(json.loads(rows[0]["flags"]), ["fields_marker_mismatch"])
        rows2, _ = pm.parse_blob(
            blob_bytes("fs_fasteign", [sale_listing(25)]),
            root="sale", url="https://g.mbl.is/v1/graphql?op=list_sale&offset=0&fields=v2",
            raw_id=1, content_hash="h", fetched_at="2026-06-10T00:00:00+00:00")
        self.assertEqual(json.loads(rows2[0]["flags"]), ["fields_marker_mismatch"])
        # consistent v2 -> no flag
        rows3, _ = pm.parse_blob(
            blob_bytes("fs_fasteign", [sale_listing(26, images=[])]),
            root="sale", url="https://g.mbl.is/v1/graphql?op=list_sale&offset=0&fields=v2",
            raw_id=1, content_hash="h", fetched_at="2026-06-10T00:00:00+00:00")
        self.assertIsNone(rows3[0]["flags"])

    # ── full-run over real fixtures: both roots, both generations, ledger updates ──
    def test_t16_run_real_fixtures_end_to_end(self):
        present = [(n, k, u) for n, k, u in (
            ("sale_sample_5.json", "list_page_sale",
             "https://g.mbl.is/v1/graphql?op=list_sale&offset=0"),
            ("rent_sample_5.json", "list_page_rent",
             "https://g.mbl.is/v1/graphql?op=list_rent&offset=0"),
            ("enriched_sale_16.json", "list_page_sale",
             "https://g.mbl.is/v1/graphql?op=list_sale&offset=16&fields=v2"),
            ("enriched_rent_16.json", "list_page_rent",
             "https://g.mbl.is/v1/graphql?op=list_rent&offset=16&fields=v2"),
        ) if (FIXDIR / n).is_file()]
        if len(present) < 4:
            self.skipTest("real probe fixtures not all present")
        rc, pc = raw_conn(), parsed_conn()
        for i, (name, kind, url) in enumerate(present):
            insert_raw(rc, (FIXDIR / name).read_bytes(), kind=kind, url=url,
                       fetched_at="2026-06-10T0%d:00:00+00:00" % i)
        stats = pm.run(rc, pc, log=lambda *a: None)
        self.assertEqual(stats["failed_blobs"], 0)
        self.assertEqual(stats["v1_blobs"], 2)
        self.assertEqual(stats["v2_blobs"], 2)
        # every parsed blob marked in the ledger
        self.assertEqual(rc.execute("SELECT COUNT(*) FROM raw_fetches "
                                    "WHERE parse_status='parsed'").fetchone()[0], 4)
        # v2 rows have images_json; v1 rows have NULL
        n_v2_img = pc.execute("SELECT COUNT(*) FROM parsed_mbl_sale "
                              "WHERE fields_version='v2_enriched' "
                              "AND images_json IS NOT NULL").fetchone()[0]
        self.assertEqual(n_v2_img, 16)
        n_v1 = pc.execute("SELECT COUNT(*) FROM parsed_mbl_sale "
                          "WHERE fields_version='v1_scalar'").fetchone()[0]
        self.assertEqual(pc.execute(
            "SELECT COUNT(*) FROM parsed_mbl_sale WHERE fields_version='v1_scalar' "
            "AND images_json IS NOT NULL").fetchone()[0], 0)
        self.assertGreater(n_v1, 0)
        # real v1 fixture carries the real negotiable/foreign population — spot-check types
        for col in ("is_negotiable", "is_foreign"):
            vals = {r[0] for r in pc.execute("SELECT %s FROM parsed_mbl_sale" % col)}
            self.assertTrue(vals.issubset({0, 1}))
        # rent: descriptions stripped deterministically
        n_txt = pc.execute("SELECT COUNT(*) FROM parsed_mbl_rent "
                           "WHERE description IS NOT NULL "
                           "AND description_text IS NULL").fetchone()[0]
        self.assertEqual(n_txt, 0)

    # ── failed blob -> DLQ, run continues ──
    def test_t17_malformed_blob_fails_soft(self):
        rc, pc = raw_conn(), parsed_conn()
        insert_raw(rc, b'{"data": "not-a-listing-page"}', kind="list_page_sale",
                   url="u1", fetched_at="2026-06-10T00:00:00+00:00")
        insert_raw(rc, blob_bytes("fs_fasteign", [sale_listing(30)]), kind="list_page_sale",
                   url="u2", fetched_at="2026-06-10T01:00:00+00:00")
        stats = pm.run(rc, pc, log=lambda *a: None)
        self.assertEqual(stats["failed_blobs"], 1)
        self.assertEqual(stats["inserted"], 1)                  # second blob still parsed
        st = dict(rc.execute("SELECT url, parse_status FROM raw_fetches"))
        self.assertEqual(st["u1"], "failed")
        self.assertEqual(st["u2"], "parsed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
