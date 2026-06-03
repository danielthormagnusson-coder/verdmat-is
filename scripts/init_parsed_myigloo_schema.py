"""init_parsed_myigloo_schema — Step 1d Phase 2a parsed-layer schema bootstrap.

Creates the LOCKED parsed_myigloo table (SCRAPER_SPEC_v2 §2.2 + Phase-1.5
empirical additions: fastnum_supplied/landreg_source (Q1), deposit_isk via
insurance_price + insurance_months (Q2), lysing via primary_description.text
(Q3), verbatim listing_type tags (Q8)) in the same local raw_myigloo.db.
Idempotent (IF NOT EXISTS). No HTTP, schema only.

stdlib only.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path  # noqa: E402

PARSED_DDL = """
CREATE TABLE IF NOT EXISTS parsed_myigloo (
  -- provenance / meta
  parse_id           INTEGER PRIMARY KEY,
  raw_id             INTEGER NOT NULL REFERENCES raw_fetches(raw_id),
  content_hash       TEXT NOT NULL,
  source_listing_id  TEXT NOT NULL,
  parser_version     TEXT NOT NULL,
  parsed_at          TEXT NOT NULL,                  -- ISO8601 Python call-site

  -- canonical-mapped (feed scraper.listings_canonical at promotion)
  title              TEXT,                            -- <- title
  lysing             TEXT,                            -- <- primary_description.text (Q3: Icelandic)
  price_amount       NUMERIC,                         -- <- price.price (string -> Decimal)
  price_currency     TEXT,                            -- <- price.currency.code
  size_sqm           NUMERIC,                         -- <- size (string -> Decimal)
  rooms              NUMERIC,
  bedrooms           NUMERIC,
  bathrooms          NUMERIC,
  tegund_raw         TEXT,                            -- <- listing_type.name (full Icelandic)
  deposit_isk        NUMERIC,                         -- <- insurance_price (Q2: tryggingafe abs kr)
  available_from     TEXT,                            -- <- available_from
  photos_json        TEXT,                            -- <- JSON array of image.file_field URLs

  -- source enum tags (TAXONOMY_v2 lookup at promotion, not here)
  listing_type_tag   TEXT,                            -- <- listing_type.tag (one of 15 values)
  category_tag       TEXT,                            -- <- listing_type.category.tag (5 values)

  -- address (canonical addr_* + §2.5 resolution keys)
  addr_street        TEXT,                            -- <- address.street_name
  addr_number        TEXT,                            -- <- address.street_number (preserves "14A")
  addr_city          TEXT,                            -- <- address.city.name
  addr_postcode      TEXT,                            -- <- address.postal_code.code (postnr block key)
  addr_country       TEXT,                            -- <- address.country.name
  lat                NUMERIC,                         -- <- location.lat
  lng                NUMERIC,                         -- <- location.lng

  -- lease signals
  contract_min_months INTEGER,                        -- <- contract_min_months
  contract_max_months INTEGER,                        -- <- contract_max_months
  insurance_months    INTEGER,                        -- <- insurance_months (1/2/3, Q2 deposit-multiplier)

  -- Tier-1 source_supplied fastnum (Q1 WIN: ~87% coverage)
  fastnum_supplied    INTEGER,                        -- <- real_estate.landreg_id (HMS fastnum; null when manual)
  landreg_source      TEXT,                           -- <- real_estate.landreg_source ('landreg' | 'manual')

  -- other source signals
  mbl_id              TEXT,                           -- <- mbl_id (§4 cross-source dedup)
  linked_property_id  TEXT,                           -- <- linked_property_id (myigloo uuid)
  source_visible      INTEGER,                        -- <- visible (bool -> int)
  source_published_at TEXT,                           -- <- published_at
  source_last_edit    TEXT,                           -- <- last_edit

  -- overflow (JSON of un-mapped fields; future-extractable)
  raw_overflow        TEXT,                           -- excludes PII (owner.*) + volatile (*.verification.as_of)

  -- promotion tracking
  promoted_to_canonical_at TEXT                       -- NULL = not yet promoted
);
"""

INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_parsed_myigloo_blob ON parsed_myigloo(content_hash, parser_version);",
    "CREATE INDEX IF NOT EXISTS ix_parsed_myigloo_listing ON parsed_myigloo(source_listing_id, parser_version);",
    "CREATE INDEX IF NOT EXISTS ix_parsed_myigloo_fastnum ON parsed_myigloo(fastnum_supplied) WHERE fastnum_supplied IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS ix_parsed_myigloo_unpromoted ON parsed_myigloo(promoted_to_canonical_at) WHERE promoted_to_canonical_at IS NULL;",
]


def init_schema(db_path) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        journal_mode = cur.execute("PRAGMA journal_mode").fetchone()[0]  # already WAL from raw bootstrap
        cur.execute("PRAGMA foreign_keys=ON")
        cur.executescript(PARSED_DDL)
        for ix in INDEXES:
            cur.execute(ix)
        conn.commit()
        cols = [r[1] for r in cur.execute("PRAGMA table_info(parsed_myigloo)")]
        idx = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='parsed_myigloo' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {"journal_mode": journal_mode, "n_columns": len(cols), "indexes": idx}
    finally:
        conn.close()


def main():
    db_path = get_raw_db_path("myigloo")
    info = init_schema(db_path)
    print("=== init_parsed_myigloo_schema ===")
    print("DB path      : %s" % db_path)
    print("journal_mode : %s" % info["journal_mode"])
    print("parsed_myigloo columns : %d" % info["n_columns"])
    print("indexes      : %s" % info["indexes"])
    print("OK (idempotent - safe to re-run).")


if __name__ == "__main__":
    main()
