"""Unit tests for sali_utdrattur (stdlib unittest; runnable standalone).

    python scripts/sali_utdrattur_test.py

Tilbúin nöfn og stofur — engin gögn úr prod. Hvert próf endurgerir MYNSTUR sem handrýni cc212b
(100 raðir × 2) fann, með skálduðum nöfnum.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sali_utdrattur import Nafnaskra, clean, extract, same_person  # noqa: E402

AGW = frozenset({"skuggi", "fasteignasala", "fasteignasalan", "ehf"})


def skra(*nofn: str, stofa: str = "skuggi") -> Nafnaskra:
    s = Nafnaskra()
    for n in nofn:
        s.baeta_vid(stofa, n)
        s.baeta_vid(stofa, n)
    s.smida()
    return s


class TestUtdrattur(unittest.TestCase):

    def test_titill_a_eftir(self):
        t = "Nánari upplýsingar veitir Jónfríður Ámundadóttir löggiltur fasteignasali í síma 555-1234."
        self.assertEqual(extract(t, "skuggi", skra(), AGW), ["Jónfríður Ámundadóttir"])

    def test_stofa_og_nafn_kynna(self):
        t = "Skuggi fasteignasala og Hrafnbergur Lóðinsson, löggiltur fasteignasali, kynna: Björt íbúð."
        self.assertEqual(extract(t, "skuggi", skra(), AGW), ["Hrafnbergur Lóðinsson"])

    def test_hastafir(self):
        t = "HRAFNBERGUR LÓÐINSSON OG SKUGGI FASTEIGNASALA KYNNA: EINBÝLI. UPPLÝSINGAR VEITIR HRAFNBERGUR LÓÐINSSON LÖGG FASTEIGNASALI"
        self.assertEqual(extract(t, "skuggi", skra("Hrafnbergur Lóðinsson"), AGW), ["Hrafnbergur Lóðinsson"])

    def test_vill_stofa_er_ekki_sali(self):
        # falsnafn v1: „Vill Skuggi fasteignasala því benda …"
        t = "Vill Skuggi fasteignasala því benda væntanlegum kaupendum á að kynna sér ástand."
        self.assertEqual(extract(t, "skuggi", skra(), AGW), [])

    def test_framkvaemdaradili_ekki_sali(self):
        t = "Skuggi fasteignasala og Steinhús kynna með stolti nýjar íbúðir."
        self.assertEqual(extract(t, "skuggi", skra(), AGW), [])

    def test_starfsheiti_klippt_aftan_af(self):  # lagfæring 1
        self.assertEqual(clean("Jónfríður Ámundadóttir Lögiltur", AGW), "Jónfríður Ámundadóttir")
        self.assertEqual(clean("Jónfríður Ámundadóttir Viðskiptafræðingur", AGW), "Jónfríður Ámundadóttir")

    def test_thagufall_fornafn_sameinast(self):  # lagfæring 2
        t = ("Skuggi fasteignasala og Herborg Valb. Kolladóttir kynna: íbúð. Bókið skoðun hjá Herborgu í síma 555-1111 "
             "eða herborg@skuggi.is.")
        self.assertEqual(extract(t, "skuggi", skra("Herborg Valb. Kolladóttir"), AGW), ["Herborg Valb. Kolladóttir"])

    def test_beygt_fullt_nafn_sameinast(self):
        self.assertTrue(same_person("Guðlaug Jóna", "Guðlaugu Jónu"))
        self.assertTrue(same_person("Ásmundur Skeggjason", "Ásmundi Skeggjasyni"))

    def test_likt_nafn_annar_madur(self):  # lagfæring 3 (#20 í handrýni v2)
        self.assertFalse(same_person("Guðbjörg Helga", "Guðrún Þórhalla Helgadóttir"))

    def test_fornafn_stadfest_af_netfangi(self):
        t = "Upplýsingar veitir Arnbjörn í s: 555-2222 eða arnbjorn@skuggi.is"
        self.assertEqual(extract(t, "skuggi", skra(), AGW), ["Arnbjörn"])

    def test_nafnlaus_stofa(self):
        t = "Nánari upplýsingar í síma 555-0000 eða skuggi@skuggi.is"
        self.assertEqual(extract(t, "skuggi", skra(), AGW, frozenset({"skuggi"})), [])

    def test_tveir_salar_rod(self):
        t = ("Nánari upplýsingar veita: Jónfríður Ámundadóttir löggiltur fasteignasali 555-1234 "
             "og Hrafnbergur Lóðinsson löggiltur fasteignasali 555-4321.")
        self.assertEqual(extract(t, "skuggi", skra(), AGW), ["Jónfríður Ámundadóttir", "Hrafnbergur Lóðinsson"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
