r"""cc292 — CF_RE grípur `_extra/<augl_id>/`-slóðir og skráir þær á auglýsandi eign.

Rótin (D:\_audit\cc292_myndir\SKIL_CC292.md §0.6): CF_RE krafðist `cloudfront.net/(\d+)/`,
svo 464.952 `_extra`-slóðir í stage_a fundust aldrei. Prófin keyra gegn raunverulegu
farmi-sniði (JSON-strengur með slóðum) og gegn viðmiðinu sem pakkar 1–5 skrifuðu
(2294806 ← _extra/1120478).

FALSPRÓF: `FalsprofGamlaRegex` keyrir SÖMU athuganir gegn gamla mynstrinu og krefst
að þær FALLI — sannar að prófið greinir villuna en stenst ekki óháð henni.

Keyrsla:  python -m unittest tests.test_cc292_cf_re   (úr rót safnsins)
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "audit"))
import image_archive as IA  # noqa: E402

GAMLA = re.compile(
    r"https://d1u57vh96em4i1\.cloudfront\.net/(\d+)/([A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp))",
    re.IGNORECASE,
)
CF = "https://d1u57vh96em4i1.cloudfront.net"
FARMUR = json.dumps([
    {"id": 1120478, "myndir": [
        {"nr": 1, "url": f"{CF}/_extra/1120478/mrZxYw4F.jpg"},
        {"nr": 2, "url": f"{CF}/_extra/1120478/SPGp-3NQ.jpg"},
        {"nr": 3, "url": f"{CF}/2352932/aetXKTJv.jpg"},
        {"nr": 4, "url": f"{CF}/0/7pJkmMab.jpeg"},
        {"nr": 5, "url": "https://cdn.mbl.is/m2/abc=/x1280/smart/fs-pool/83/8357.jpg"},
        {"nr": 6, "url": f"{CF}/_extra/1120478/mrZxYw4F.jpg"},  # tvítekning
    ]},
])
ADV = 2294806


def nidurstada(regex):
    """parse_cf_urls með gefnu mynstri (til að falsprófið keyri sama kóða)."""
    gamalt = IA.CF_RE
    IA.CF_RE = regex
    try:
        return IA.parse_cf_urls(FARMUR, ADV)
    except ValueError:
        return None
    finally:
        IA.CF_RE = gamalt


class Athuganir:
    regex = None

    def utkoma(self):
        return nidurstada(self.regex)

    def test_extra_slodir_finnast(self):
        u = self.utkoma()
        self.assertIsNotNone(u)
        slodir = [x[2] for x in u]
        self.assertIn(f"{CF}/_extra/1120478/mrZxYw4F.jpg", slodir)
        self.assertIn(f"{CF}/_extra/1120478/SPGp-3NQ.jpg", slodir)

    def test_extra_skrast_a_auglysanda_ekki_augl_id(self):
        u = self.utkoma()
        self.assertIsNotNone(u)
        extra = [x for x in u if "/_extra/" in x[2]]
        self.assertEqual(len(extra), 2)
        self.assertTrue(all(x[0] == ADV for x in extra), extra)
        self.assertFalse(any(x[0] == 1120478 for x in u))

    def test_rod_og_fjoldi(self):
        u = self.utkoma()
        self.assertIsNotNone(u)
        self.assertEqual([x[2].rsplit("/", 1)[1] for x in u],
                         ["mrZxYw4F.jpg", "SPGp-3NQ.jpg", "aetXKTJv.jpg", "7pJkmMab.jpeg"])


class NyjaRegex(Athuganir, unittest.TestCase):
    regex = IA.CF_RE

    def test_talnamoppur_obreyttar(self):
        u = self.utkoma()
        self.assertIn((2352932, "aetXKTJv.jpg", f"{CF}/2352932/aetXKTJv.jpg"), u)
        self.assertIn((0, "7pJkmMab.jpeg", f"{CF}/0/7pJkmMab.jpeg"), u)

    def test_mbl_ekki_gripid(self):
        self.assertFalse(any("mbl.is" in x[2] for x in self.utkoma()))

    def test_extra_an_auglysanda_sleppt(self):
        self.assertEqual([x for x in IA.parse_cf_urls(FARMUR) if "/_extra/" in x[2]], [])

    def test_cf_source_fastnum(self):
        self.assertEqual(IA.cf_source_fastnum("2352932", ADV), 2352932)
        self.assertEqual(IA.cf_source_fastnum("_extra/1120478", ADV), ADV)
        self.assertIsNone(IA.cf_source_fastnum("_extra/1120478"))
        with self.assertRaises(ValueError):
            IA.cf_source_fastnum("_annad/1", ADV)

    def test_ekki_hluti_ur_annarri_slod(self):
        # `_extra` aðeins sem FYRSTI hluti slóðar á réttum hýsli
        t = json.dumps([f"https://evil.example/_extra/1/abcd.jpg", f"{CF}/x/_extra/1/abcd.jpg"])
        self.assertEqual(IA.parse_cf_urls(t, ADV), [])


class FalsprofGamlaRegex(unittest.TestCase):
    """Sömu athuganir gegn gamla mynstrinu VERÐA að falla."""

    def test_gamla_fellur_a_ollum(self):
        fell = 0
        for nafn in ("test_extra_slodir_finnast", "test_extra_skrast_a_auglysanda_ekki_augl_id", "test_rod_og_fjoldi"):
            klasi = type("G", (Athuganir, unittest.TestCase), {"regex": GAMLA})
            r = unittest.TestResult()
            klasi(nafn).run(r)
            fell += (len(r.failures) + len(r.errors)) > 0
        self.assertEqual(fell, 3, "gamla regex stóðst athugun — prófið greinir ekki villuna")


if __name__ == "__main__":
    unittest.main()
