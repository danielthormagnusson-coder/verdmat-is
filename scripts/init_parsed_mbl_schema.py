"""init_parsed_mbl_schema — Step 3c schema bootstrap (idempotent).

Creates SCRAPER_SPEC_v2 §2.2 parsed tier for mbl in a SEPARATE DB,
D:\\verdmat-is\\scraper_data\\parsed_mbl.db (locked Step 3c architecture) — NOT inside
raw_mbl.db, so the parser never holds a write handle on the DB the fetcher writes to.
TWO source-flavored tables (mbl's two Hasura root types share NO field names):

  * parsed_mbl_sale — fs_fasteign:        all 49 list-query scalars 1:1
  * parsed_mbl_rent — rentals_property:   all 21 list-query scalars 1:1

Nested objects (v2_enriched generation only) land as deterministic JSON columns;
v1_scalar-generation rows keep them NULL (fields_version column disambiguates a
v1-missing nested column from a v2-null one). raw_id/content_hash reference
raw_mbl.db rows; cross-DB, so NOT FK-enforced — lineage columns only.

ONE row per source_listing_id (upsert precedence lives in parse_mbl.py:
fields_version v2_enriched > v1_scalar; newer fetched_at within a generation).

CLI:  python init_parsed_mbl_schema.py

stdlib only.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_scraper_data_dir  # noqa: E402

PARSED_DB_NAME = "parsed_mbl.db"


def get_parsed_db_path() -> Path:
    return get_scraper_data_dir() / PARSED_DB_NAME


# Shared parse-metadata block (identical on both tables).
_META_COLS = """
  parse_id            INTEGER PRIMARY KEY AUTOINCREMENT,
  source_listing_id   INTEGER NOT NULL UNIQUE,  -- = eign_id (sale) / id (rent); generic key for §3d
  raw_id              INTEGER NOT NULL,         -- raw_fetches.raw_id in raw_mbl.db (cross-DB, unenforced)
  content_hash        TEXT NOT NULL,            -- raw_blobs.content_hash in raw_mbl.db (cross-DB, unenforced)
  fetched_at          TEXT NOT NULL,            -- raw_fetches.fetched_at of the winning blob
  fields_version      TEXT NOT NULL CHECK (fields_version IN ('v1_scalar','v2_enriched')),
  parser_version      TEXT NOT NULL,
  parsed_at           TEXT NOT NULL,            -- ISO8601 from the Python call-site
  flags               TEXT,                     -- JSON array of parse concerns, NULL if none
"""

PARSED_MBL_SALE_DDL = """
CREATE TABLE IF NOT EXISTS parsed_mbl_sale (
""" + _META_COLS + """
  -- fs_fasteign list-query scalars 1:1 (v2_enriched selection; v1_scalar blobs fill 23 of these):
  eign_id             INTEGER NOT NULL,
  fastano             INTEGER,            -- 0 -> NULL sentinel applied
  gata                TEXT,
  heimilisfang        TEXT,
  normalized_heimilisfang TEXT,
  postfang            INTEGER,
  teg_eign            TEXT,
  fermetrar           REAL,               -- coerced float (mixed int/float in JSON)
  fermetraverd        REAL,               -- coerced float; 0 -> NULL sentinel applied
  fjoldi_herb         INTEGER,
  fjoldi_svefnhb      INTEGER,
  fjoldi_badherb      INTEGER,
  fjoldi_haeda        INTEGER,
  verd                INTEGER,            -- RAW value (0 = Tilboð/samkomulag; see is_negotiable)
  fasteignamat        INTEGER,            -- 0 -> NULL sentinel applied
  brunabotamat        INTEGER,            -- 0 -> NULL sentinel applied
  ahvilandi_lan       INTEGER,
  appended_land       REAL,
  bygg_ar             INTEGER,            -- 0 -> NULL sentinel applied
  nybygging           INTEGER,            -- bool 0/1
  latitude            REAL,
  longitude           REAL,
  hverfi              TEXT,
  lysing              TEXT,               -- raw HTML
  inngangur           TEXT,
  aukaibud            INTEGER,            -- bool 0/1
  bilskur             INTEGER,
  gardur              INTEGER,
  lyfta               INTEGER,
  svalir              INTEGER,
  parking             INTEGER,
  parking_shelter     INTEGER,
  electric_car        INTEGER,
  pet_allowed         INTEGER,
  wheelchair_acc      INTEGER,
  seniors             INTEGER,
  makaskipti          INTEGER,
  skiptanleg          INTEGER,
  greidslumat         INTEGER,
  syna                INTEGER,
  dealer_email        TEXT,
  embed               TEXT,
  created             TEXT,               -- tz-normalized ISO8601
  sent_dags           TEXT,               -- tz-aware passthrough
  br_dags             TEXT,               -- tz-aware passthrough
  address_search_id   TEXT,
  price_search_id     TEXT,
  size_search_id      TEXT,
  zip_search_id       TEXT,

  -- derived (parse rules 2/3/7):
  lysing_text         TEXT,               -- deterministic HTML-strip of lysing (LLM pipe)
  is_negotiable       INTEGER NOT NULL DEFAULT 0,   -- verd == 0
  is_foreign          INTEGER NOT NULL DEFAULT 0,   -- non-IS postcode OR coords outside IS bbox

  -- nested (v2_enriched only; NULL on v1_scalar rows), deterministic serialization:
  images_json         TEXT,               -- sorted by imgno (array-index fallback)
  agency_json         TEXT,
  attachments_json    TEXT,
  openhouse_json      TEXT,
  postal_code_json    TEXT,
  promo_json          TEXT,

  promoted_to_canonical_at TEXT           -- NULL until Step 3d promotion
);
"""

PARSED_MBL_RENT_DDL = """
CREATE TABLE IF NOT EXISTS parsed_mbl_rent (
""" + _META_COLS + """
  -- rentals_property list-query scalars 1:1 (21; v1_scalar blobs fill 18 of these):
  id                  INTEGER NOT NULL,
  address             TEXT,               -- Hashie::Mash corruption stripped (see address_corrupt)
  normalized_address  TEXT,               -- ditto
  zipcode             INTEGER,
  title               TEXT,               -- ditto
  type_id             INTEGER,            -- opaque raw signal (Step 3a finding)
  size                INTEGER,
  price               INTEGER,            -- RAW value (0 = Tilboð; see is_negotiable)
  rooms               INTEGER,
  available_from      TEXT,
  available_until     TEXT,
  longtime            INTEGER,            -- bool 0/1
  lift                INTEGER,
  pet_allowed         INTEGER,
  wheelchair_acc      INTEGER,
  from_leiguskjol     INTEGER,
  show_from_date      TEXT,
  show_until_date     TEXT,
  created             TEXT,               -- naive -> +00:00 appended (Iceland is UTC year-round)
  updated             TEXT,               -- ditto
  description         TEXT,               -- raw HTML

  -- derived (parse rules 2/3/4/7):
  description_text    TEXT,               -- deterministic HTML-strip of description (LLM pipe)
  is_negotiable       INTEGER NOT NULL DEFAULT 0,   -- price == 0
  is_foreign          INTEGER NOT NULL DEFAULT 0,   -- non-IS zipcode (rent has no coords)
  address_corrupt     INTEGER NOT NULL DEFAULT 0,   -- Hashie::Mash leak was stripped

  -- nested (v2_enriched only; NULL on v1_scalar rows), deterministic serialization:
  images_json         TEXT,               -- sorted by ordering (array-index fallback)
  agency_json         TEXT,
  postal_code_json    TEXT,
  promo_json          TEXT,

  promoted_to_canonical_at TEXT           -- NULL until Step 3d promotion
);
"""

INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_pms_fastano ON parsed_mbl_sale(fastano);",
    "CREATE INDEX IF NOT EXISTS ix_pms_promote ON parsed_mbl_sale(promoted_to_canonical_at) "
    "WHERE promoted_to_canonical_at IS NULL;",
    "CREATE INDEX IF NOT EXISTS ix_pmr_promote ON parsed_mbl_rent(promoted_to_canonical_at) "
    "WHERE promoted_to_canonical_at IS NULL;",
)


def init_schema_on_conn(conn) -> dict:
    """Create both tables + indexes on an open connection (testable on :memory:)."""
    cur = conn.cursor()
    pre = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    already = {"parsed_mbl_sale", "parsed_mbl_rent"}.issubset(pre)
    cur.executescript(PARSED_MBL_SALE_DDL + PARSED_MBL_RENT_DDL)
    for ix in INDEXES:
        cur.execute(ix)
    conn.commit()
    n_sale = len(list(cur.execute("PRAGMA table_info(parsed_mbl_sale)")))
    n_rent = len(list(cur.execute("PRAGMA table_info(parsed_mbl_rent)")))
    return {"already_existed": already, "n_sale_columns": n_sale, "n_rent_columns": n_rent}


def init_schema(db_path: Path) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        return init_schema_on_conn(conn)
    finally:
        conn.close()


def main():
    db_path = get_parsed_db_path()
    info = init_schema(db_path)
    print("=== init_parsed_mbl_schema ===")
    print("DB path      : %s" % db_path)
    print("sale columns : %d" % info["n_sale_columns"])
    print("rent columns : %d" % info["n_rent_columns"])
    if info["already_existed"]:
        print("tables already existed - no changes (idempotent re-run).")
    else:
        print("parsed_mbl_sale + parsed_mbl_rent created (idempotent - safe to re-run).")


if __name__ == "__main__":
    main()
