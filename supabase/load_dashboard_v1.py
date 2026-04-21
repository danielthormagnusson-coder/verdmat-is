"""
load_dashboard_v1.py
--------------------

Initial data load for Áfangi 4 dashboard tables:
  - ats_dashboard_monthly_heat    (from D:\\ats_dashboard_monthly_heat.pkl)
  - llm_aggregates_quarterly       (from build_llm_aggregates.py output)
  - model_tracking_history         (from build_model_tracking_snapshot.py output)
  - last_listing_text              (from build_last_listing_text.py output)

Each table is imported TRUNCATE-then-COPY within a transaction so a failed load
rolls back cleanly. Designed to be safely re-run.

Usage:
    python app/supabase/load_dashboard_v1.py \
        [--tables ats,llm,tracking,listing] \
        [--no-truncate]

VM_DB_URL is read from $VM_DB_URL or, if unset, from D:\\verdmat-is\\.dbconfig.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

try:
    import psycopg2
except ImportError:
    sys.stderr.write("Missing psycopg2 — run: pip install psycopg2-binary\n")
    sys.exit(1)

EXPORTS = Path(r"D:\verdmat-is\precompute\exports")
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")

# Each entry: (alias, csv_path, table_name, columns_tuple_or_None)
IMPORT_SPEC = [
    ("ats",
     EXPORTS / "ats_dashboard_monthly_heat.csv",
     "ats_dashboard_monthly_heat",
     None),
    ("llm",
     EXPORTS / "llm_aggregates_quarterly.csv",
     "llm_aggregates_quarterly",
     ("year", "quarter", "period", "canonical_code", "region_tier",
      "n_listings_total",
      "mean_interior_condition_score", "n_listings_condition",
      "pct_recently_renovated", "n_listings_renovation",
      "pct_has_unregistered_space", "n_listings_unregistered",
      "pct_apt_with_serlod", "n_listings_serlod",
      "pct_framing_terse", "pct_framing_standard",
      "pct_framing_elaborate", "pct_framing_promotional")),
    ("tracking",
     EXPORTS / "model_tracking_history.csv",
     "model_tracking_history",
     ("period", "model_version", "calibration_version", "segment",
      "n_held", "mape", "median_ape", "bias_log",
      "cov80", "cov95", "status_label")),
    ("listing",
     EXPORTS / "last_listing_text.csv",
     "last_listing_text",
     ("fastnum", "sale_rank", "thinglyst_dagur", "augl_id",
      "lysing_plain", "scraped_at")),
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def resolve_db_url() -> str:
    url = os.environ.get("VM_DB_URL")
    if url:
        return url
    if DBCONFIG.exists():
        return DBCONFIG.read_text(encoding="utf-8-sig").strip()
    sys.exit("ERROR: neither $VM_DB_URL nor D:\\verdmat-is\\.dbconfig is set.")


def import_one(cur, alias, csv_path, table, cols, truncate):
    if not csv_path.exists():
        log(f"  SKIP {alias} — {csv_path.name} not found")
        return 0
    sz_mb = csv_path.stat().st_size / 1024 / 1024
    log(f"  {table}: {csv_path.name} ({sz_mb:.2f} MB) ...")
    if truncate:
        cur.execute(f"TRUNCATE {table}")
    t0 = time.time()
    col_clause = "(" + ",".join(cols) + ")" if cols else ""
    sql = (f"COPY {table} {col_clause} FROM STDIN "
           f"WITH (FORMAT CSV, HEADER TRUE, NULL '')")
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        cur.copy_expert(sql, f)
    cur.execute(f"SELECT count(*) FROM {table}")
    n = cur.fetchone()[0]
    log(f"    {n:,} rows in {time.time() - t0:.1f}s")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", default="ats,llm,tracking,listing",
                    help="comma list of aliases: ats,llm,tracking,listing")
    ap.add_argument("--no-truncate", action="store_true",
                    help="Skip TRUNCATE before COPY (for append-only workflows)")
    args = ap.parse_args()

    wanted = {s.strip() for s in args.tables.split(",") if s.strip()}
    url = resolve_db_url()

    conn = psycopg2.connect(url)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        total = 0
        for alias, csv_path, table, cols in IMPORT_SPEC:
            if alias not in wanted:
                continue
            total += import_one(cur, alias, csv_path, table, cols,
                                truncate=not args.no_truncate)
        conn.commit()
        log(f"COMMIT — loaded {total:,} rows across {len(wanted)} table(s)")
    except Exception:
        conn.rollback()
        log("ROLLBACK on error")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
