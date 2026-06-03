"""Unit tests for scraper_paths (stdlib unittest; runnable standalone).

    python scripts/scraper_paths_test.py   # runs all tests, exits non-zero on failure

stdlib only; pytest-discoverable if installed.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scraper_paths  # noqa: E402
from scraper_paths import get_scraper_data_dir, get_raw_db_path  # noqa: E402


class TestScraperPaths(unittest.TestCase):

    def setUp(self):
        self._saved = os.environ.get("SCRAPER_DATA_DIR")

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("SCRAPER_DATA_DIR", None)
        else:
            os.environ["SCRAPER_DATA_DIR"] = self._saved

    # 1. default path when env unset
    def test_default_dir_when_env_unset(self):
        os.environ.pop("SCRAPER_DATA_DIR", None)
        self.assertEqual(get_scraper_data_dir(), scraper_paths._DEFAULT_DIR)
        self.assertTrue(get_scraper_data_dir().exists())

    # 2. env override
    def test_env_override(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["SCRAPER_DATA_DIR"] = td
            self.assertEqual(get_scraper_data_dir(), Path(td))

    # 3. parent-dir creation (nested, not pre-existing)
    def test_parent_dir_creation(self):
        with tempfile.TemporaryDirectory() as td:
            nested = Path(td) / "a" / "b" / "c"
            os.environ["SCRAPER_DATA_DIR"] = str(nested)
            d = get_scraper_data_dir()
            self.assertTrue(d.exists() and d.is_dir())
            self.assertEqual(d, nested)

    # 4. per-source naming
    def test_per_source_naming(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["SCRAPER_DATA_DIR"] = td
            self.assertEqual(get_raw_db_path("myigloo").name, "raw_myigloo.db")
            self.assertEqual(get_raw_db_path("visir").name, "raw_visir.db")
            self.assertEqual(get_raw_db_path("mbl").name, "raw_mbl.db")

    # 5. source validation — traversal / separators rejected
    def test_source_validation_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["SCRAPER_DATA_DIR"] = td
            for bad in ("../foo", "a/b", "a.b", "a\\b", "foo;rm", "with space"):
                with self.subTest(bad=bad):
                    self.assertRaises(ValueError, get_raw_db_path, bad)

    # 6. source validation — empty / None rejected
    def test_source_validation_empty(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["SCRAPER_DATA_DIR"] = td
            self.assertRaises(ValueError, get_raw_db_path, "")
            self.assertRaises(ValueError, get_raw_db_path, None)

    # 7. idempotency — call twice, same path, no error
    def test_idempotency(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["SCRAPER_DATA_DIR"] = td
            a = get_scraper_data_dir()
            b = get_scraper_data_dir()
            self.assertEqual(a, b)
            self.assertTrue(b.exists())

    # 8. db path sits under the data dir
    def test_db_path_under_data_dir(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["SCRAPER_DATA_DIR"] = td
            self.assertEqual(get_raw_db_path("myigloo").parent, get_scraper_data_dir())


if __name__ == "__main__":
    unittest.main(verbosity=2)
