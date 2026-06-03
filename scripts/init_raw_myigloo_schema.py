"""init_raw_myigloo_schema — Step 1c Phase 2 schema bootstrap (idempotent).

Creates the SCRAPER_SPEC_v2 §2.1 raw-layer schema in the local per-source
SQLite DB for myigloo (path via scraper_paths). No HTTP, no data — schema
only. Safe to re-run.

The two table DDLs are VERBATIM from SCRAPER_SPEC_v2_draft.md §2.1 (column
definitions, types, comments, and the content_hash FK unchanged); only
`IF NOT EXISTS` is added for idempotency.

stdlib only.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path  # noqa: E402

# --- §2.1 DDL (verbatim; IF NOT EXISTS added for idempotency) ---------------
RAW_BLOBS_DDL = """
CREATE TABLE IF NOT EXISTS raw_blobs (
  content_hash  TEXT PRIMARY KEY,           -- sha256 of UNCOMPRESSED body
  blob_gz       BLOB NOT NULL,              -- gzip-compressed response body
  content_type  TEXT NOT NULL,              -- 'application/json' | 'text/html'
  byte_len      INTEGER NOT NULL,           -- uncompressed length (audit)
  first_stored  TEXT NOT NULL               -- ISO8601 (passed in; no Date.now in spec)
);
"""

RAW_FETCHES_DDL = """
CREATE TABLE IF NOT EXISTS raw_fetches (
  raw_id            INTEGER PRIMARY KEY,     -- autoincrement
  source            TEXT NOT NULL,           -- 'myigloo' | 'visir' | 'mbl'
  source_listing_id TEXT,                    -- platform id if cheaply extractable pre-parse; else NULL
  url               TEXT NOT NULL,
  fetch_kind        TEXT NOT NULL,           -- 'index' | 'detail' | 'ajax' | 'api_page'
  fetched_at        TEXT NOT NULL,           -- ISO8601
  http_status       INTEGER NOT NULL,
  content_hash      TEXT REFERENCES raw_blobs(content_hash),  -- NULL on non-200/empty
  changed           INTEGER NOT NULL,        -- 1 = new content_hash for this listing, 0 = unchanged re-fetch
  retry_count       INTEGER NOT NULL DEFAULT 0,
  parse_status      TEXT NOT NULL DEFAULT 'pending',  -- pending|parsed|failed|skipped_unchanged
  parse_error       TEXT
);
"""

IX_LISTING = (
    "CREATE INDEX IF NOT EXISTS ix_fetch_listing "
    "ON raw_fetches(source, source_listing_id, fetched_at);"
)
IX_PARSE = (
    "CREATE INDEX IF NOT EXISTS ix_fetch_parse "
    "ON raw_fetches(parse_status) WHERE parse_status IN ('pending','failed');"
)
DLQ_VIEW = (
    "CREATE VIEW IF NOT EXISTS v_dlq_parse_failures AS "
    "SELECT * FROM raw_fetches WHERE parse_status='failed';"
)


def init_schema(db_path: Path) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        journal_mode = cur.execute("PRAGMA journal_mode=WAL").fetchone()[0]  # persistent
        cur.execute("PRAGMA foreign_keys=ON")  # per-connection; fetchers must also set it
        cur.executescript(RAW_BLOBS_DDL)
        cur.executescript(RAW_FETCHES_DDL)
        cur.execute(IX_LISTING)
        cur.execute(IX_PARSE)
        cur.execute(DLQ_VIEW)
        conn.commit()
        q = "SELECT name FROM sqlite_master WHERE type=? AND name NOT LIKE 'sqlite_%' ORDER BY name"
        tables = [r[0] for r in cur.execute(q, ("table",))]
        indexes = [r[0] for r in cur.execute(q, ("index",))]
        views = [r[0] for r in cur.execute(q, ("view",))]
        return {"journal_mode": journal_mode, "tables": tables, "indexes": indexes, "views": views}
    finally:
        conn.close()


def main():
    db_path = get_raw_db_path("myigloo")
    info = init_schema(db_path)
    print("=== init_raw_myigloo_schema ===")
    print("DB path      : %s" % db_path)
    print("journal_mode : %s" % info["journal_mode"])
    print("tables       : %s" % info["tables"])
    print("indexes      : %s" % info["indexes"])
    print("views        : %s" % info["views"])
    print("OK (idempotent - safe to re-run).")


if __name__ == "__main__":
    main()
