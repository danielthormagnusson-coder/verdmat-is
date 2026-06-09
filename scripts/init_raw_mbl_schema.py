"""init_raw_mbl_schema — Step 3b P1 schema bootstrap (idempotent).

Creates the SCRAPER_SPEC_v2 §2.1 raw-layer schema in raw_mbl.db (path via scraper_paths).
Byte-identical two-table content-addressable schema to raw_myigloo.db / raw_visir.db —
only the per-source semantics differ (documented below). No HTTP, no data — schema only.

mbl is a Hasura GraphQL endpoint (g.mbl.is/v1/graphql) — every fetch POSTs to one URL.
To keep schema parity + ledger greppability/replay, fetch_mbl.py (P2) stores a SYNTHETIC
`url` that encodes intent, and the actual GraphQL body is POSTed regardless of the
querystring. Synthetic URL shapes:
    https://g.mbl.is/v1/graphql?op=list_sale&offset=N
    https://g.mbl.is/v1/graphql?op=list_rent&offset=N
    https://g.mbl.is/v1/graphql?op=aggregate_count
    https://g.mbl.is/v1/graphql?op=delta_check_sale&since=<br_dags>
    https://g.mbl.is/v1/graphql?op=delta_check_rent&since=<updated>

mbl fetch_kind discriminator values (no DB enum — a TEXT column, documented here):
    list_page_sale   — 16-row page of fs_fasteign list query
    list_page_rent   — 16-row page of rentals_property list query
    aggregate_count  — uncapped universe-size check
    delta_check_sale / delta_check_rent — br_dags/updated > last_seen refresh
source_listing_id is NULL for list_page_* / aggregate_* (a page covers many listings);
per-listing decomposition happens at the parsed_mbl tier (Step 3c). content_type is
always 'application/json' for mbl (canonicalize_mbl assumes this). No detail-fetch kind —
the list payload is rich enough (Step 3a probe).

CLI:  python init_raw_mbl_schema.py            # create (idempotent, safe to re-run)
      python init_raw_mbl_schema.py --apply    # explicit create
      python init_raw_mbl_schema.py --dry-run  # print DDL, do NOT touch the DB

stdlib only.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path  # noqa: E402

# --- §2.1 DDL (verbatim across sources; IF NOT EXISTS for idempotency) -------
RAW_BLOBS_DDL = """
CREATE TABLE IF NOT EXISTS raw_blobs (
  content_hash  TEXT PRIMARY KEY,           -- sha256 of CANONICALIZED body (§2.1.1)
  blob_gz       BLOB NOT NULL,              -- gzip-compressed VERBATIM response body
  content_type  TEXT NOT NULL,              -- 'application/json' (mbl: always JSON)
  byte_len      INTEGER NOT NULL,           -- uncompressed length (audit)
  first_stored  TEXT NOT NULL               -- ISO8601 (passed in; no Date.now in spec)
);
"""

RAW_FETCHES_DDL = """
CREATE TABLE IF NOT EXISTS raw_fetches (
  raw_id            INTEGER PRIMARY KEY,     -- autoincrement
  source            TEXT NOT NULL,           -- 'mbl' (this DB) | 'visir' | 'myigloo'
  source_listing_id TEXT,                    -- NULL for list_page_*/aggregate_* (covers many)
  url               TEXT NOT NULL,           -- SYNTHETIC g.mbl.is/v1/graphql?op=... (ledger/replay)
  fetch_kind        TEXT NOT NULL,           -- list_page_sale|list_page_rent|aggregate_count|delta_check_*
  fetched_at        TEXT NOT NULL,           -- ISO8601
  http_status       INTEGER NOT NULL,
  content_hash      TEXT REFERENCES raw_blobs(content_hash),  -- NULL on non-200/empty
  changed           INTEGER NOT NULL,        -- 1 = new content_hash for this target, 0 = unchanged
  retry_count       INTEGER NOT NULL DEFAULT 0,
  parse_status      TEXT NOT NULL DEFAULT 'pending',  -- pending|parsed|failed|skipped_unchanged
  parse_error       TEXT
);
"""

IX_LISTING = ("CREATE INDEX IF NOT EXISTS ix_fetch_listing "
              "ON raw_fetches(source, source_listing_id, fetched_at);")
IX_PARSE = ("CREATE INDEX IF NOT EXISTS ix_fetch_parse "
            "ON raw_fetches(parse_status) WHERE parse_status IN ('pending','failed');")
DLQ_VIEW = ("CREATE VIEW IF NOT EXISTS v_dlq_parse_failures AS "
            "SELECT * FROM raw_fetches WHERE parse_status='failed';")

DDL_STATEMENTS = [RAW_BLOBS_DDL.strip(), RAW_FETCHES_DDL.strip(), IX_LISTING, IX_PARSE, DLQ_VIEW]


def init_schema(db_path: Path) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        pre = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        already = {"raw_blobs", "raw_fetches"}.issubset(pre)
        journal_mode = cur.execute("PRAGMA journal_mode=WAL").fetchone()[0]   # persistent
        cur.execute("PRAGMA synchronous=NORMAL")    # resume-safety per §2.1 rationale
        cur.execute("PRAGMA foreign_keys=ON")       # per-connection; fetchers must also set it
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
        blobs = cur.execute("SELECT COUNT(*) FROM raw_blobs").fetchone()[0]
        fetches = cur.execute("SELECT COUNT(*) FROM raw_fetches").fetchone()[0]
        return {"journal_mode": journal_mode, "tables": tables, "indexes": indexes,
                "views": views, "already_existed": already, "blobs": blobs, "fetches": fetches}
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description="bootstrap raw_mbl.db (§2.1 raw layer)")
    ap.add_argument("--dry-run", action="store_true", help="print DDL, do NOT touch the DB")
    ap.add_argument("--apply", action="store_true", help="explicit create (default behaviour)")
    args = ap.parse_args()
    db_path = get_raw_db_path("mbl")

    if args.dry_run:
        print("=== init_raw_mbl_schema --dry-run ===")
        print("target DB (NOT created): %s\n" % db_path)
        for s in DDL_STATEMENTS:
            print(s if s.endswith(";") else s)
            print()
        return 0

    info = init_schema(db_path)
    print("=== init_raw_mbl_schema ===")
    print("DB path      : %s" % db_path)
    print("journal_mode : %s" % info["journal_mode"])
    print("tables       : %s" % info["tables"])
    print("indexes      : %s" % info["indexes"])
    print("views        : %s" % info["views"])
    print("row counts   : raw_blobs=%d raw_fetches=%d" % (info["blobs"], info["fetches"]))
    if info["already_existed"]:
        print("schema already existed - no changes (idempotent re-run).")
    else:
        print("OK - schema created (idempotent - safe to re-run).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
