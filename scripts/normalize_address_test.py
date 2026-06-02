"""Unit tests for normalize_address (stdlib unittest; runnable standalone).

    python scripts/normalize_address_test.py   # runs all tests, exits non-zero on failure

Also pytest-discoverable (pytest collects unittest.TestCase) if pytest is
installed. stdlib only — no external deps.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_address import normalize_address  # noqa: E402


class TestNormalizeAddress(unittest.TestCase):

    # 1. Diacritic table coverage --------------------------------------------
    def test_diacritic_single_chars(self):
        cases = {
            "þ": "th", "Þ": "th",
            "ð": "d",  "Ð": "d",
            "æ": "ae", "Æ": "ae",
            "ö": "o",  "Ö": "o",
            "á": "a",  "Á": "a",
            "é": "e",  "É": "e",
            "í": "i",  "Í": "i",
            "ó": "o",  "Ó": "o",
            "ú": "u",  "Ú": "u",
            "ý": "y",  "Ý": "y",
        }
        for src, exp in cases.items():
            with self.subTest(char=src):
                self.assertEqual(normalize_address(src), exp)

    def test_diacritic_in_context(self):
        self.assertEqual(normalize_address("Þórsgata 5"), "thorsgata 5")
        self.assertEqual(normalize_address("Ægisíða 12"), "aegisida 12")
        self.assertEqual(normalize_address("Höfðabakki 9"), "hofdabakki 9")
        self.assertEqual(normalize_address("Óðinsgata 7"), "odinsgata 7")
        self.assertEqual(normalize_address("Mýrargata 2"), "myrargata 2")
        self.assertEqual(normalize_address("Úlfarsbraut 44"), "ulfarsbraut 44")
        # every diacritic in one string
        self.assertEqual(
            normalize_address("þÞðÐæÆöÖáÁéÉíÍóÓúÚýÝ"),
            "ththddaeaeooaaeeiioouuyy",
        )

    # 2. Letter suffix preservation ------------------------------------------
    def test_letter_suffix_preserved(self):
        self.assertEqual(normalize_address("Kaupvangur 23A"), "kaupvangur 23a")
        self.assertEqual(normalize_address("Sóleyjargata 12b"), "soleyjargata 12b")
        self.assertEqual(normalize_address("Brautin 15C"), "brautin 15c")

    # 3. Range preservation ---------------------------------------------------
    def test_range_preserved(self):
        self.assertEqual(normalize_address("Langitangi 9-13"), "langitangi 9-13")
        self.assertEqual(normalize_address("Eikjuvogur 23-25"), "eikjuvogur 23-25")

    # 4. Whitespace collapse --------------------------------------------------
    def test_whitespace_collapse(self):
        self.assertEqual(normalize_address("  Hverfisgata  12 "), "hverfisgata 12")
        self.assertEqual(normalize_address("Foo\t\t12"), "foo 12")
        self.assertEqual(normalize_address("\nFoo   12\n"), "foo 12")
        self.assertEqual(normalize_address("a   b   c"), "a b c")

    # 5. Lowercase ------------------------------------------------------------
    def test_lowercase(self):
        self.assertEqual(normalize_address("HVERFISGATA 12"), "hverfisgata 12")
        self.assertEqual(normalize_address("KaUpVaNgUr 1"), "kaupvangur 1")

    # 6. Edge cases -----------------------------------------------------------
    def test_edge_cases(self):
        self.assertIsNone(normalize_address(None))
        self.assertIsNone(normalize_address(""))
        self.assertIsNone(normalize_address("   "))
        self.assertIsNone(normalize_address("\t"))
        self.assertIsNone(normalize_address(" "))
        self.assertIsNone(normalize_address("\n\t  "))

    # 7. Idempotency ----------------------------------------------------------
    def test_idempotency(self):
        samples = [
            "Kaupvangur 23A",
            "Langitangi 9-13",
            "Þórsgata 5",
            "  Höfðabakki  12 ",
            "ÆGISÍÐA 7B",
        ]
        for s in samples:
            once = normalize_address(s)
            twice = normalize_address(once)
            with self.subTest(sample=s):
                self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main(verbosity=2)
