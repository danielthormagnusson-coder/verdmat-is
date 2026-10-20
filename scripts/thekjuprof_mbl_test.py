"""cc267 (d) — ferskleikaviðvaranir þekjuprófsins prófaðar á MÆLDRI sögu. stdlib unittest, engin DB/HTTP.

    python -m unittest scripts.thekjuprof_mbl_test -v

Fixture = mælt 20.10.2026 (D:\\_audit\\cc267_tvitok\\SKIL_CC267.md §5):
  bendilaldur = 07:15 − delta-sale high_water úr night_logs (21.9.–20.10),
  eignir/raðir = scraper.listings eftir discovered_at-degi (25.9.–20.10; almanaksdagur, ekki rúllandi 24 klst).
Krafa: 0 viðvaranir á venjulegum dögum (falsjákvæðni), viðvörun á HVERJUM hrinudegi 16.–20.10.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import thekjuprof_mbl as tp                   # noqa: E402
except ImportError as e:                          # psycopg2/lifecycle-háðir innflutningar
    tp = None
    _ERR = str(e)

# dagur: (bendilaldur kl. 07:15 í klst, einkvæmar nýjar verðs. söluauglýsingar (eignir), mest raðir á eina eign)
VENJULEGT = {
    "09-25": (3.4, 674, 39), "09-26": (4.3, 685, 45), "09-27": (6.3, 296, 23), "09-28": (6.1, 268, 27),
    "09-29": (3.3, 817, 35), "09-30": (4.3, 559, 10), "10-01": (3.2, 897, 26), "10-02": (4.3, 646, 11),
    "10-03": (3.4, 834, 12), "10-04": (6.3, 375, 11), "10-05": (6.3, 231, 2), "10-06": (4.3, 630, 22),
    "10-07": (3.4, 646, 21), "10-08": (4.3, 574, 8), "10-09": (3.9, 513, 11), "10-10": (4.3, 810, 18),
    "10-11": (5.2, 369, 6), "10-12": (6.0, 301, 2), "10-13": (3.4, 780, 25), "10-14": (4.3, 492, 7),
    "10-15": (4.3, 705, 17),
}
HRINA = {
    "10-16": (12.7, 390, 320), "10-17": (36.5, 5, 1595), "10-18": (60.4, 5, 880),
    "10-19": (84.2, 5, 653), "10-20": (107.9, 5, 1035),
}


def f(t):
    return {"bendill_aldur_klst": t[0], "nyjar_verds_sala_eignir_24h": t[1], "mest_radir_a_eign_24h": t[2],
            "mest_radir_eign": "x"}


@unittest.skipIf(tp is None, "thekjuprof_mbl ekki innflytjanlegt")
class Ferskleiki(unittest.TestCase):
    def test_engin_falsvidvorun_a_venjulegum_dogum(self):
        for d, t in VENJULEGT.items():
            with self.subTest(dagur=d):
                self.assertEqual(tp.ferskleika_vidvaranir(f(t)), [], d)

    def test_vidvorun_a_hverjum_hrinudegi(self):
        for d, t in HRINA.items():
            with self.subTest(dagur=d):
                self.assertTrue(tp.ferskleika_vidvaranir(f(t)), d)

    def test_hvert_merki_eitt_og_ser(self):
        # stökkbreyting: eitt merki í einu á hrinugildi, hin á venjulegu — hvert verður að bíta sjálft
        base = (4.3, 600, 20)
        for i, slaemt in enumerate((36.5, 5, 1595)):
            t = list(base); t[i] = slaemt
            with self.subTest(merki=i):
                self.assertEqual(len(tp.ferskleika_vidvaranir(f(tuple(t)))), 1)

    def test_tomt_skilar_engu(self):
        self.assertEqual(tp.ferskleika_vidvaranir(None), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
