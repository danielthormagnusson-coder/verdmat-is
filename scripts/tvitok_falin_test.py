"""cc276: tvitok_falin.endurreikna (hlið + færsla) og tenging hans í lifecycle_sweep_mbl.write_events.

  python -m unittest scripts.tvitok_falin_test
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import psycopg2  # noqa: E402
import tvitok_falin  # noqa: E402
import lifecycle_sweep_mbl as sweep  # noqa: E402


class FalsTenging:
    """Skráir skipanir; to_regclass svarar `til`, endurreikningsfallið (1, 2, 30) eða kastar `villa`."""

    def __init__(self, til=True, villa=None):
        self.til, self.villa, self.log = til, villa, []

    def cursor(self, *a, **k):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, *a):
        self.log.append(sql)
        self._svar = None
        if "to_regclass('scraper.tvitok_falin')" in sql:
            self._svar = (self.til,)
        elif "endurreikna_tvitok_falin()" in sql:
            if self.villa:
                raise self.villa
            self._svar = (1, 2, 30)

    def fetchone(self):
        return self._svar

    def commit(self):
        self.log.append("COMMIT")

    def rollback(self):
        self.log.append("ROLLBACK")


class Endurreikna(unittest.TestCase):
    def test_ovirk_an_toflu_skrifar_ekkert(self):
        c = FalsTenging(til=False)
        self.assertIsNone(tvitok_falin.endurreikna(c, log=lambda *_: None))
        self.assertFalse(any("endurreikna_tvitok_falin()" in s for s in c.log))
        self.assertNotIn("COMMIT", c.log)

    def test_virk_keyrir_fallid_i_les_skrif_faerslu_og_commitar(self):
        c = FalsTenging()
        self.assertEqual(tvitok_falin.endurreikna(c, log=lambda *_: None), (1, 2, 30))
        i_rw = c.log.index("SET TRANSACTION READ WRITE")
        self.assertEqual(c.log[i_rw - 1], "ROLLBACK")          # pooler-reglan: rollback á undan READ WRITE
        i_fall = next(i for i, s in enumerate(c.log) if "endurreikna_tvitok_falin()" in s)
        self.assertLess(i_rw, i_fall)
        self.assertEqual(c.log[-1], "COMMIT")


class SopTenging(unittest.TestCase):
    def setUp(self):
        self._gamla = sweep._write_events_once
        self.skrif = 0

        def _skrifa(*a, **k):
            self.skrif += 1
        sweep._write_events_once = _skrifa

    def tearDown(self):
        sweep._write_events_once = self._gamla

    def _atburdur(self):
        return [{"source": "mbl", "id": "1", "fastnum": 1, "event_type": "confirmed_absent_1",
                 "event_at": None, "evidence": {}}]

    def test_atburdir_kveikja_endurreikning(self):
        c = FalsTenging()
        sweep.write_events(c, self._atburdur(), log=lambda *_: None)
        self.assertTrue(any("endurreikna_tvitok_falin()" in s for s in c.log))

    def test_adeins_found_kveikir_ekki(self):
        c = FalsTenging()
        sweep.write_events(c, [], log=lambda *_: None, found=[("1", None)])
        self.assertFalse(any("endurreikna_tvitok_falin()" in s for s in c.log))

    def test_villa_i_endurreikningi_endurtekur_ekki_skrifin(self):
        # OperationalError er það sem retry-lykkjan grípur — endurreikningurinn má ALDREI kveikja hana
        c = FalsTenging(villa=psycopg2.OperationalError("tenging rofnaði"))
        logg = []
        sweep.write_events(c, self._atburdur(), log=logg.append)
        self.assertEqual(self.skrif, 1)
        self.assertTrue(any(s.startswith("VILLA tvitok_falin") for s in logg))


if __name__ == "__main__":
    unittest.main()
