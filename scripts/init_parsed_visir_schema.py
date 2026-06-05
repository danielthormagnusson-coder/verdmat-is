"""init_parsed_visir_schema — Step 2c schema bootstrap (idempotent).

Creates the SCRAPER_SPEC_v2 §2.2 parsed_visir table INSIDE raw_visir.db (same file —
FK to raw_fetches). Source-flavored visir field shape; NO (category, tenure, sub_type)
decomposition (that is Step 2d promotion). Safe to re-run.

CLI:  python init_parsed_visir_schema.py

stdlib only.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path  # noqa: E402

PARSED_VISIR_DDL = """
CREATE TABLE IF NOT EXISTS parsed_visir (
  parse_id            INTEGER PRIMARY KEY AUTOINCREMENT,
  raw_id              INTEGER NOT NULL REFERENCES raw_fetches(raw_id),
  content_hash        TEXT NOT NULL,
  source_listing_id   TEXT NOT NULL,
  parser_version      TEXT NOT NULL,
  parsed_at           TEXT NOT NULL,

  -- visir's own field shape (lightly flattened, NO decomposition):
  title               TEXT,
  price_amount        NUMERIC,            -- NULL if Tilboð / price-on-request
  price_currency      TEXT DEFAULT 'ISK',
  price_text_raw      TEXT,               -- verbatim for audit
  is_price_on_request INTEGER DEFAULT 0,

  size_sqm            NUMERIC,
  rooms               NUMERIC,
  bedrooms            NUMERIC,
  bathrooms           NUMERIC,
  byggar              INTEGER,

  tegund_raw          TEXT,               -- visir's category label, verbatim
  tenure_signal       TEXT,               -- 'sale'|'rent'|'unknown' (best-effort, §2d canonical)

  lysing              TEXT,

  addr_street         TEXT,
  addr_number         TEXT,
  addr_postcode       TEXT,
  addr_city           TEXT,

  lat                 NUMERIC,
  lng                 NUMERIC,

  fastnum_supplied    BIGINT,             -- label-anchored extraction (F-prefix stripped)

  photos_json         TEXT,               -- JSON array of image URLs
  n_photos            INTEGER,

  listing_date        TEXT,               -- "Skráð" label text, no parsing
  agency_name         TEXT,               -- PII — capture, drop at promotion

  promoted_to_canonical_at TEXT,          -- NULL until Step 2d promotion

  UNIQUE(content_hash, parser_version)
);
"""

IX_LATEST = ("CREATE INDEX IF NOT EXISTS ix_parsed_visir_latest "
             "ON parsed_visir(source_listing_id, parser_version);")
IX_PROMOTE = ("CREATE INDEX IF NOT EXISTS ix_parsed_visir_promote "
              "ON parsed_visir(promoted_to_canonical_at) WHERE promoted_to_canonical_at IS NULL;")


def init_schema(db_path: Path) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        pre = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        already = "parsed_visir" in pre
        cur.execute("PRAGMA foreign_keys=ON")
        cur.executescript(PARSED_VISIR_DDL)
        cur.execute(IX_LATEST)
        cur.execute(IX_PROMOTE)
        conn.commit()
        cols = [r[1] for r in cur.execute("PRAGMA table_info(parsed_visir)")]
        return {"already_existed": already, "n_columns": len(cols)}
    finally:
        conn.close()


def main():
    db_path = get_raw_db_path("visir")
    info = init_schema(db_path)
    print("=== init_parsed_visir_schema ===")
    print("DB path  : %s" % db_path)
    print("columns  : %d" % info["n_columns"])
    if info["already_existed"]:
        print("parsed_visir already existed - no changes (idempotent re-run).")
    else:
        print("parsed_visir created (idempotent - safe to re-run).")


if __name__ == "__main__":
    main()
