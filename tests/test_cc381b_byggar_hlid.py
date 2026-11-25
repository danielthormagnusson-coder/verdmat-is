"""cc381b — byggár við hleðslu nýrra eigna (scripts/byggar_hlid.py) og migration-reglan.

Engin DB. Falsprófin stökkbreyta inntaki og krefjast þess að hliðið felli það.
Run:  python -m unittest tests.test_cc381b_byggar_hlid   (from repo root)
"""
import re
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "scripts"))
import byggar_hlid as H  # noqa: E402

AR = 2026


class ByggarUrHms(unittest.TestCase):
    def test_gild_ar(self):
        self.assertEqual(H.byggar_ur_hms("1985", AR), 1985)
        self.assertEqual(H.byggar_ur_hms(" 2028 ", AR), 2028)
        self.assertEqual(H.byggar_ur_hms(1700.0, AR), 1700)

    def test_sentinel_og_rusl_verda_none_aldrei_0(self):
        for v in ("0", 0, 0.0, "", None, np.nan, "201", "1224", "2029", "19x5", "1985a"):
            self.assertIsNone(H.byggar_ur_hms(v, AR), v)


class Hlid(unittest.TestCase):
    def test_gild_rod(self):
        self.assertEqual(H.byggar_hlid(pd.Series([None, 1700, 2028, np.nan]), "próf", ar=AR), 2)

    def test_fals_0_fellur(self):
        with self.assertRaises(SystemExit):
            H.byggar_hlid(pd.Series([1990.0, 0.0]), "próf", pd.Series([1, 2]), ar=AR)

    def test_fals_utan_bils_fellur(self):
        for v in (1699, 2029, 201):
            with self.assertRaises(SystemExit):
                H.byggar_hlid(pd.Series([v]), "próf", ar=AR)


class MigrationSamraemi(unittest.TestCase):
    """Migration og hleðsla bera sömu mörk (1700 og ár + 2)."""

    def test_sql_mork(self):
        sql = (ROT / "supabase" / "migrations" / "20261125200000_cc381b_byggar.sql").read_text(encoding="utf-8")
        self.assertIn("BETWEEN 1700 AND extract(year FROM current_date)::int + 2", sql)
        self.assertIn("'byggar_vantar'::text", sql)
        self.assertEqual(H.BYGGAR_MIN, 1700)
        self.assertEqual(H.byggar_max(AR), AR + 2)

    def test_d3_extract_notar_hlidid(self):
        s = (ROT / "scripts" / "phase_d3_extract.py").read_text(encoding="utf-8")
        self.assertRegex(s, r"byggar = byggar_ur_hms\(primary\.get\(\"byggingarar\"\)\)")
        self.assertNotRegex(s, r"byggar = coerce_numeric\(primary\.get\(\"byggingarar\"\)\)")

    def test_d3_score_og_apply_fella(self):
        for f in ("phase_d3_score_extract.py", "phase_d3_apply.py"):
            self.assertIn("byggar_hlid(", (ROT / "scripts" / f).read_text(encoding="utf-8"), f)


if __name__ == "__main__":
    unittest.main()
