"""cc288 — einingapróf á flokkun og röðun fasteignamats (scripts/cc288_fasteignamat.py).

Engin DB: tilbúin smágögn. Hvert próf ber eitt invariant; falsprófin (Fals*) stökkbreyta inntaki og krefjast þess
að reglan felli það.

Run:  python -m unittest tests.test_cc288_fasteignamat   (from repo root)
"""
import re
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import cc288_fasteignamat as F  # noqa: E402

FLOKKUN = pd.DataFrame([("Verslun", "verslun", True), ("Skrifstofa", "skrifstofa", True), ("Iðnaður", "idnadur_lager", True),
                        ("Hótel", "gisting", True), ("Sérhæfð bygging", "annad_atvinnu", False), ("Bílskúr", "bilskur_geymsla", False)],
                       columns=["tegund", "flokkur", "radast"])


def eining(fn, gata="Prófgata", nr=1, postnr=101, svfn=0, svf="Reykjavíkurborg", tegund="Íbúð á hæð", cc="APT_FLOOR",
           fam="main", res=True, flm=100.0, matsstig="7", mat=50000, mat_b=51000, msv=20):
    return dict(fastnum=fn, heimilisfang=f"{gata} {nr}", postnr=postnr, svfn=svfn, sveitarfelag=svf, tegund_raw=tegund,
                canonical_code=cc, unit_family=fam, is_residential=res, einflm=flm, matsstig=matsstig, deregistered=False,
                matsvaedi_numer=msv, matsvaedi_nafn="Miðbær", _mat=mat, _mat_b=mat_b)


def keyra(rows):
    p = pd.DataFrame(rows)
    m = pd.concat([p[["fastnum"]].assign(argerd=F.ARGERD, mat_thkr=p._mat),
                   p.loc[p._mat_b.notna(), ["fastnum"]].assign(argerd=F.ARGERD_BREYTING, mat_thkr=p._mat_b)])
    e, tal = F.undirbua(p.drop(columns=["_mat", "_mat_b"]), m, FLOKKUN)
    return F.reikna(e), tal


def gotur(n, gata="Prófgata", **kw):
    return [eining(1000 + i + hash(gata) % 100000 * 100, gata=gata, nr=i + 1, **kw) for i in range(n)]


class Gotugreining(unittest.TestCase):
    def test_gata_ur(self):
        self.assertEqual(F.gata_ur("Laugavegur 18a"), ("Laugavegur", "18A"))
        self.assertEqual(F.gata_ur("  Bakki 3 Sólbakki "), ("Bakki", "3"))
        self.assertEqual(F.gata_ur("Hvammur"), (None, None))
        self.assertEqual(F.gata_ur(None), (None, None))

    def test_norm_bil(self):
        self.assertEqual(F.norm("Akraneskaupstaður           "), "Akraneskaupstaður")
        self.assertEqual(F.norm("Íbúð  á   hæð"), "Íbúð á hæð")


class Rodun(unittest.TestCase):
    def test_n5_radast_n4_ekki(self):
        r, _ = keyra(gotur(5, "Fimmgata") + gotur(4, "Fjórgata"))
        g = r[(r.hopur == "ibud") & (r.tegund == "allt") & (r.stig == "gata")].set_index("gata")
        self.assertTrue(np.isfinite(g.loc["Fimmgata", "midg_kr_m2"]))
        self.assertTrue(np.isnan(g.loc["Fjórgata", "midg_kr_m2"]))
        self.assertTrue(np.isnan(g.loc["Fjórgata", "midg_mat_eign_thkr"]))
        self.assertEqual(int(g.loc["Fjórgata", "n"]), 4)   # n er alltaf skráð

    def test_kr_m2_adeins_60_150(self):
        rows = gotur(5, "Bilgata", flm=100.0) + [eining(9, gata="Bilgata", nr=9, flm=40.0, mat=90000)]
        r, _ = keyra(rows)
        g = r[(r.hopur == "ibud") & (r.tegund == "allt") & (r.stig == "gata")].iloc[0]
        self.assertEqual(int(g.n), 6)
        self.assertEqual(int(g.n_kr_m2), 5)
        self.assertAlmostEqual(g.midg_kr_m2, 500000.0)       # 50.000 þús. kr / 100 m²; 40 m² einingin utan bils

    def test_breyting_summa_somu_eininga(self):
        rows = gotur(5, "Breytgata", mat=50000, mat_b=55000) + [eining(77, gata="Breytgata", nr=77, mat=50000, mat_b=None)]
        r, _ = keyra(rows)
        g = r[(r.hopur == "ibud") & (r.tegund == "allt") & (r.stig == "gata")].iloc[0]
        self.assertEqual(int(g.n_breyting), 5)
        self.assertAlmostEqual(g.breyting_pct, 10.0)

    def test_serbyli_fjolbyli_sia(self):
        rows = gotur(5, "Blandgata", cc="APT_FLOOR") + [eining(500 + i, gata="Blandgata", nr=50 + i, cc="SFH_DETACHED", flm=140.0)
                                                         for i in range(5)]
        r, _ = keyra(rows)
        g = r[(r.hopur == "ibud") & (r.stig == "gata")].set_index("tegund")
        self.assertEqual(int(g.loc["allt", "n"]), 10)
        self.assertEqual(int(g.loc["fjolbyli", "n"]), 5)
        self.assertEqual(int(g.loc["serbyli", "n"]), 5)

    def test_atvinnu_per_flokk_aldrei_alls(self):
        rows = [eining(2000 + i, gata="Atv", nr=i, tegund="Verslun", fam=None, res=False, cc="EXCLUDE", flm=200.0) for i in range(5)]
        rows += [eining(3000 + i, gata="Atv", nr=20 + i, tegund="Skrifstofa", fam=None, res=False, cc="EXCLUDE", flm=200.0) for i in range(5)]
        r, _ = keyra(rows)
        self.assertEqual(set(r.hopur), {"verslun", "skrifstofa"})
        self.assertNotIn("atvinnu_allt", set(r.hopur))
        self.assertEqual(set(r[r.hopur != "ibud"].tegund), {"allt"})

    def test_svf_heiti_btrimud(self):
        rows = gotur(3, "Agata", svf="Akraneskaupstaður", svfn=3000) + gotur(3, "Bgata", svf="Akraneskaupstaður      ", svfn=3000)
        r, _ = keyra(rows)
        s = r[(r.stig == "svf") & (r.tegund == "allt")]
        self.assertEqual(len(s), 1)                         # EITT sveitarfélag, ekki tvö
        self.assertEqual(int(s.iloc[0].n), 6)
        self.assertTrue(all(h == h.strip() for h in r.heiti))

    def test_ofullmetid_og_afskrad_ut(self):
        rows = gotur(5, "Hreingata") + [eining(88, gata="Hreingata", nr=88, matsstig="4")]
        r, tal = keyra(rows)
        g = r[(r.stig == "gata") & (r.tegund == "allt")].iloc[0]
        self.assertEqual(int(g.n), 5)
        self.assertEqual(tal["trappa"]["3_fullmetid_matsstig_7_8"], 5)


class Geymslubil(unittest.TestCase):
    """cc288-v2: eining í iðnaði/lager undir 50 m² er geymslubil — talin, ekki raðað; regla á stærð, ekki heimilisfang."""

    def _idn(self, fn, nr, flm, gata="Bilgata"):
        return eining(fn, gata=gata, nr=nr, tegund="Iðnaður", fam=None, res=False, cc="EXCLUDE", flm=flm, mat=12000)

    def test_undir_50_ut_50_inni(self):
        rows = [self._idn(6000 + i, i, 26.0) for i in range(8)] + [self._idn(7000 + i, 20 + i, 50.0) for i in range(5)]
        r, tal = keyra(rows)
        g = r[(r.hopur == "idnadur_lager") & (r.stig == "gata")].iloc[0]
        self.assertEqual(int(g.n), 5)                  # 50 m² stendur (mörkin eru < 50)
        self.assertEqual(tal["geymslubil"], 8)

    def test_adrir_flokkar_osnortnir(self):
        rows = [eining(8000 + i, gata="Smaversl", nr=i, tegund="Verslun", fam=None, res=False, cc="EXCLUDE", flm=30.0) for i in range(5)]
        r, tal = keyra(rows)
        self.assertEqual(int(r[(r.hopur == "verslun") & (r.stig == "gata")].iloc[0].n), 5)
        self.assertEqual(tal["geymslubil"], 0)

    def test_fals_mork_virka(self):
        gamalt = F.GEYMSLUBIL_M2
        try:
            F.GEYMSLUBIL_M2 = 0
            r, tal = keyra([self._idn(9000 + i, i, 26.0) for i in range(6)])
            self.assertEqual(tal["geymslubil"], 0)
            self.assertEqual(int(r[(r.hopur == "idnadur_lager") & (r.stig == "gata")].iloc[0].n), 6)
        finally:
            F.GEYMSLUBIL_M2 = gamalt


class Fals(unittest.TestCase):
    """Stökkbreytingar sem reglan VERÐUR að fella."""

    def test_fals_gata_n2_radast_ekki(self):
        r, _ = keyra(gotur(2, "Tveggjagata"))
        g = r[(r.stig == "gata") & (r.tegund == "allt")].iloc[0]
        self.assertTrue(np.isnan(g.midg_kr_m2) and np.isnan(g.midg_mat_eign_thkr) and np.isnan(g.breyting_pct))

    def test_fals_annad_atvinnu_radast_ekki(self):
        rows = [eining(4000 + i, gata="Sérgata", nr=i, tegund="Sérhæfð bygging", fam=None, res=False, cc="EXCLUDE") for i in range(20)]
        r, tal = keyra(rows + gotur(5, "Íbgata"))
        self.assertNotIn("annad_atvinnu", set(r.hopur))
        self.assertEqual(tal["flokkar"].get("annad_atvinnu"), 20)   # talið, ekki raðað

    def test_fals_oflokkad_radast_ekki(self):
        rows = [eining(5000 + i, gata="Óþgata", nr=i, tegund="Vörðuás 20", fam=None, res=False, cc="EXCLUDE") for i in range(10)]
        r, tal = keyra(rows + gotur(5, "Íbgata2"))
        self.assertEqual(set(r.hopur), {"ibud"})
        self.assertEqual(tal["oflokkad"], 10)

    def test_fals_regla8_engin_tilvisun_i_likan(self):
        kodi = Path(F.__file__).read_text(encoding="utf-8")
        # SQL-strengir skriftunnar (allt innan """…""" sem byrjar á select/insert/delete/update)
        sql = " ".join(re.findall(r'"""\s*((?:select|insert|delete|update)[\s\S]*?)"""', kodi, flags=re.I))
        sql += " ".join(re.findall(r'"((?:select|insert|delete|update)[^"]*)"', kodi, flags=re.I))
        self.assertTrue(sql.strip())
        for bannad in ("predictions", "comps", "feature_attributions", "real_pred", "threp", "þrep"):
            self.assertNotIn(bannad, sql.lower(), bannad)

    def test_fals_lagmark_virkar_i_reikna(self):
        """Ef LAGMARK_N væri 1 myndi n=2 gata raðast → sannar að prófið hér að ofan mælir regluna, ekki tilviljun."""
        gamalt = F.LAGMARK_N
        try:
            F.LAGMARK_N = 1
            r, _ = keyra(gotur(2, "Tveggjagata"))
            self.assertTrue(np.isfinite(r[(r.stig == "gata") & (r.tegund == "allt")].iloc[0].midg_kr_m2))
        finally:
            F.LAGMARK_N = gamalt


if __name__ == "__main__":
    unittest.main()
