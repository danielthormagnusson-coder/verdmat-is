r"""scraper_paths — shared local-storage paths for the scraper substream.

Per SCRAPER_SPEC_v2 §2.1: the raw layer lives in ONE local SQLite DB per
source, on D:\ **outside the git repo** (mirrors the D:\Gagnapakkar\*.db
convention; keeps multi-GB blob DBs out of git). Default dir is
D:\verdmat-is\scraper_data\, overridable via the SCRAPER_DATA_DIR env var.

Fetchers / init scripts in app/scripts/ import these helpers — never hard-code
the DB path, and never place raw_*.db inside the repo tree.

stdlib only.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

_DEFAULT_DIR = Path(r"D:\verdmat-is\scraper_data")
_SOURCE_RE = re.compile(r"^[A-Za-z0-9_]+$")


def get_scraper_data_dir() -> Path:
    """Return the scraper-data dir (SCRAPER_DATA_DIR env or default), ensuring it exists."""
    raw = os.environ.get("SCRAPER_DATA_DIR", "").strip()
    d = Path(raw) if raw else _DEFAULT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_raw_db_path(source: str) -> Path:
    """Return <data_dir>/raw_<source>.db.

    `source` must be a bare identifier (alphanumeric + underscore). Rejects
    empty/None and any path-traversal or separator characters.
    """
    if not isinstance(source, str) or not _SOURCE_RE.match(source):
        raise ValueError("invalid source %r - must match [A-Za-z0-9_]+" % (source,))
    return get_scraper_data_dir() / ("raw_%s.db" % source)
