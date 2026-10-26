"""cc281: 5xx-endurtekning í báðum mbl-transportum (fetch_mbl._gql og lifecycle_sweep_mbl.Transport,
sem thekjuprof_mbl notar). Engin lifandi HTTP, engin bið (sleep skráður, ekki sofinn).

    python -m unittest scripts.transport_5xx_test -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_mbl as fm                    # noqa: E402
import lifecycle_sweep_mbl as ls          # noqa: E402
import thekjuprof_mbl as tp               # noqa: E402

OK = b'{"data": {"fs_fasteign": []}}'


class Resp:
    def __init__(self, status, content=OK):
        self.status_code = status
        self.content = content
        self.headers = {"content-type": "application/json"}


class Rod:
    """Svarar úr föstum lista; tæmdur listi = AssertionError (stöðvar óendanlega lykkju)."""
    def __init__(self, svor):
        self.svor = list(svor)
        self.kollud = 0

    def post(self, url, json=None, headers=None, timeout=None):
        self.kollud += 1
        if not self.svor:
            raise AssertionError("fleiri beiðnir en svör (%d)" % self.kollud)
        s = self.svor.pop(0)
        if isinstance(s, Exception):
            raise s
        return Resp(s) if isinstance(s, int) else s


def fetch_transport(svor):
    rod = Rod(svor)
    f = fm.MblFetcher(rod, None, fm.default_state(), "unused.json", min_spacing=0, log=lambda *a: None)
    svefn = []
    f._sleep = svefn.append
    return (lambda: f._gql("{q}")), rod, svefn


def sweep_transport(svor):
    rod = Rod(svor)
    t = ls.Transport(spacing=0, log=lambda *a: None)
    t.s = rod
    t._pace = lambda: None
    svefn = []
    t._sleep = svefn.append
    return (lambda: t.gql("{q}")), rod, svefn


class _Sameiginlegt:
    smida = None

    def kall(self, svor):
        return type(self).smida(svor)

    def test_520_svo_200_tekst(self):
        k, rod, svefn = self.kall([520, 200])
        self.assertIsNotNone(k())
        self.assertEqual((rod.kollud, svefn), (2, [30]))

    def test_502_503_504_svo_200_bil_30_60_120(self):
        k, rod, svefn = self.kall([502, 503, 504, 200])
        k()
        self.assertEqual((rod.kollud, svefn), (4, [30, 60, 120]))

    def test_fjorda_5xx_er_killswitch(self):
        k, rod, svefn = self.kall([520, 520, 520, 520, 200])
        with self.assertRaises(fm.KillSwitch) as cm:
            k()
        self.assertIn("HTTP 520 after 3 retries", str(cm.exception))
        self.assertEqual((rod.kollud, svefn), (4, [30, 60, 120]))

    def test_403_og_429_strax_killswitch(self):
        for st in (403, 429):
            k, rod, svefn = self.kall([st, 200])
            with self.assertRaises(fm.KillSwitch) as cm:
                k()
            self.assertEqual(str(cm.exception), "HTTP %s" % st)
            self.assertEqual((rod.kollud, svefn), (1, []))

    def test_500_og_501_ekki_endurtekin(self):
        for st in (500, 501):
            k, rod, svefn = self.kall([st, 200])
            with self.assertRaises(fm.KillSwitch) as cm:
                k()
            self.assertEqual(str(cm.exception), "unexpected HTTP %s" % st)
            self.assertEqual(rod.kollud, 1)

    def test_5xx_eydir_ekki_400_kvota(self):
        # 400,400 eru 2 af 3; 520 á milli má ekki ýta þeim í „retries exhausted"
        k, rod, svefn = self.kall([400, 400, 520, 200])
        k()
        self.assertEqual((rod.kollud, svefn), (4, [2, 2, 30]))

    def test_400_thak_obreytt(self):
        k, rod, _ = self.kall([400, 400, 400, 200])
        with self.assertRaises(fm.KillSwitch) as cm:
            k()
        self.assertIn("3 consecutive HTTP 400", str(cm.exception))

    def test_timeout_thak_obreytt(self):
        e = requests.ConnectionError("x")
        k, rod, _ = self.kall([e, e, e, 200])
        with self.assertRaises(fm.KillSwitch) as cm:
            k()
        self.assertIn("3 consecutive timeouts", str(cm.exception))

    def test_5xx_teljari_endurstillist_per_kall(self):
        k, rod, svefn = self.kall([520, 520, 520, 200, 520, 520, 520, 200])
        k()
        k()
        self.assertEqual(svefn, [30, 60, 120, 30, 60, 120])


class FetchMbl5xx(_Sameiginlegt, unittest.TestCase):
    smida = staticmethod(fetch_transport)


class Sopur5xx(_Sameiginlegt, unittest.TestCase):
    smida = staticmethod(sweep_transport)


class Thekjuprof(unittest.TestCase):
    def test_thekjuprof_notar_sopstransport(self):
        self.assertIs(tp.Transport, ls.Transport)


if __name__ == "__main__":
    unittest.main()
