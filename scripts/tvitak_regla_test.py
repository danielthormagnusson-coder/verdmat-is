"""Unit tests for tvitak_regla (cc267) + promote_listings_append.tvitok_ad_merkja. stdlib unittest, engin DB.

    python -m unittest scripts.tvitak_regla_test -v

Falspróf: hvert próf sem segir „EKKI tvítak" breytir NÁKVÆMLEGA einu svæði frumritsins (eða bilinu) —
ef reglan hunsaði svæðið félli prófið (sbr. feedback_sjalfsprof_sem_stokkbreytir_engu).
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tvitak_regla as tr                       # noqa: E402

T0 = datetime(2026, 10, 15, 18, 31, 0, tzinfo=timezone.utc)


def rod(i, dt_s=0, **kw):
    r = dict(listing_id=i, source_listing_id=str(1800000 + i), source="mbl", tenure="sale",
             is_price_on_request=False, fastnum=2536486, addr_text="Laugavegur 170 íb 605 - Heklureitur",
             price_amount=259000000, size_sqm=Decimal("191.7"), agency_source_id=3, lysing="Glæsileg íbúð.",
             listed_at=T0 + timedelta(seconds=dt_s))
    r.update(kw)
    return r


class Regla(unittest.TestCase):
    def test_hrina_ein_frumrit(self):
        rs = [rod(i, dt_s=i) for i in range(1, 51)]           # 50 raðir, 1/s
        m = tr.flokka(rs)
        self.assertEqual(len(m), 49)
        self.assertEqual(set(m.values()), {1})

    def test_rodun_ohad_innlestrarrod(self):
        rs = [rod(i, dt_s=i) for i in range(1, 6)][::-1]
        self.assertEqual(set(tr.flokka(rs).values()), {1})

    def test_kedja_yfir_glugga(self):
        # 0, 9, 18, 27 mín: hvert bil < 10 mín -> einn klasi þótt endar séu 27 mín sundur
        rs = [rod(i, dt_s=60 * 9 * (i - 1)) for i in range(1, 5)]
        self.assertEqual(len(tr.flokka(rs)), 3)

    def test_bil_yfir_glugga_nytt_frumrit(self):
        rs = [rod(1, 0), rod(2, 5), rod(3, 11 * 60), rod(4, 11 * 60 + 5)]
        self.assertEqual(tr.flokka(rs), {2: 1, 4: 3})

    def test_gluggamork_innifalin(self):
        self.assertEqual(tr.flokka([rod(1, 0), rod(2, 600)]), {2: 1})
        self.assertEqual(tr.flokka([rod(1, 0), rod(2, 601)]), {})

    def test_endurbirting_daginn_eftir_ekki_tvitak(self):
        self.assertEqual(tr.flokka([rod(1, 0), rod(2, 86400)]), {})

    def test_falsprof_hvert_svaedi_lykils(self):
        breytt = dict(source="myigloo", tenure="rent", is_price_on_request=True, fastnum=2536480,
                      addr_text="Laugavegur 170 íb 511 - Heklureitur", price_amount=258900000,
                      size_sqm=Decimal("191.8"), agency_source_id=4, lysing="Glæsileg íbúð!")
        for k, v in breytt.items():
            with self.subTest(svaedi=k):
                self.assertEqual(tr.flokka([rod(1, 0), rod(2, 1, **{k: v})]), {}, k)

    def test_ostodug_svaedi_utan_lykils(self):
        # ólíkt source_listing_id/myndir/br_dags/status breytir engu
        a = rod(1, 0, photos_json='["a"]', br_dags="x", status="active")
        b = rod(2, 1, source_listing_id="999", photos_json='["b"]', br_dags="y", status="withdrawn")
        self.assertEqual(tr.flokka([a, b]), {2: 1})

    def test_gerdaohad_samanburdur(self):
        # Postgres (Decimal/int) og parse (float/str) gefa sama lykil
        a = rod(1, 0)
        b = rod(2, 1, size_sqm=191.7, price_amount="259000000", fastnum="2536486", agency_source_id="3",
                listed_at=(T0 + timedelta(seconds=1)).isoformat(), is_price_on_request="f")
        self.assertEqual(tr.flokka([a, b]), {2: 1})

    def test_null_lykill_og_engin_dags(self):
        # fastnum NULL hópast á heimilisfangi; röð án listed_at er aldrei tvítak (fail-closed)
        self.assertEqual(tr.flokka([rod(1, 0, fastnum=None), rod(2, 1, fastnum=None)]), {2: 1})
        self.assertEqual(tr.flokka([rod(1, 0), rod(2, 1, listed_at=None)]), {})
        self.assertEqual(tr.flokka([rod(1, 0, lysing=None), rod(2, 1, lysing="")]), {2: 1})

    def test_jafntefli_a_tima(self):
        # sama listed_at: lægra tölulegt auðkenni er frumrit (ekki strengjaröð: "10" < "9")
        rs = [rod(10, 0, source_listing_id="10"), rod(9, 0, source_listing_id="9")]
        self.assertEqual(tr.flokka(rs, audkenni="source_listing_id"), {"10": "9"})


class Promote(unittest.TestCase):
    def test_tvitok_ad_merkja_sleppir_merktum(self):
        try:
            import promote_listings_append as pla
        except ImportError as e:                       # psycopg2 vantar í umhverfi
            self.skipTest(str(e))
        rs = [rod(i, dt_s=i) for i in range(1, 6)]
        allt = pla.tvitok_ad_merkja(rs, set())
        self.assertEqual(len(allt), 4)
        self.assertTrue(all(f == "1800001" for _, f in allt))
        self.assertEqual(len(pla.tvitok_ad_merkja(rs, {"1800002", "1800003"})), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
