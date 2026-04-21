"""
Import all Phase 1A CSV exports into Supabase Postgres via COPY.

Usage:
    export VM_DB_URL="postgresql://postgres:PASS@db.XXXXX.supabase.co:5432/postgres"
    python supabase/import.py [--truncate] [--skip-migration]

Steps:
    1. Run initial schema migration (idempotent)
    2. COPY each CSV into its table via psycopg2.copy_expert
    3. Report row counts and DB size
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

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "supabase" / "migrations" / "20260421_initial_schema.sql"
EXPORTS = Path(r"D:\verdmat-is\precompute\exports")

# Import order matters — predictions + SHAP + comps + sales_history all have FK to properties
TABLES = [
    ("properties.csv", "properties", None),
    ("predictions.csv", "predictions", None),
    ("feature_attributions.csv", "feature_attributions", None),
    ("comps_index.csv", "comps_index", None),
    # sales_history has SERIAL id — must skip it in COPY; specify columns
    ("sales_history.csv", "sales_history",
     "(fastnum, thinglystdags, kaupverd_nominal, kaupverd_real, "
     "einflm_at_sale, byggar_at_sale, onothaefur)"),
    ("repeat_sale_index.csv", "repeat_sale_index", None),
    # ats_lookup has a SERIAL id column — skip it in COPY
    ("ats_lookup.csv", "ats_lookup",
     "(canonical_code, region_tier, heat_bucket, n_pairs, median_log_ratio, "
     "dispersion_sd, dispersion_mad, above_list_rate, n_quarters_pooled, "
     "data_quality, p33, p67, median_overall, n_qtrs_stable)"),
]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truncate", action="store_true",
                    help="TRUNCATE tables before import (keeps schema)")
    ap.add_argument("--skip-migration", action="store_true",
                    help="Skip schema migration (assume already applied)")
    args = ap.parse_args()

    db_url = os.environ.get("VM_DB_URL")
    if not db_url:
        sys.stderr.write("ERROR: VM_DB_URL not set.\n")
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    if not args.skip_migration:
        log("Running migration ...")
        cur.execute(MIGRATION.read_text(encoding="utf-8"))
        conn.commit()
        log("  migration complete")

    if args.truncate:
        log("Truncating tables (cascade) ...")
        cur.execute(
            "TRUNCATE properties, predictions, feature_attributions, "
            "comps_index, sales_history, repeat_sale_index, ats_lookup "
            "RESTART IDENTITY CASCADE"
        )
        conn.commit()

    for csv_name, table, cols in TABLES:
        path = EXPORTS / csv_name
        if not path.exists():
            log(f"  SKIP {csv_name} — not found")
            continue
        sz_mb = path.stat().st_size / 1024 / 1024
        log(f"  {table}: COPY from {csv_name} ({sz_mb:.1f} MB) ...")
        t0 = time.time()
        with open(path, "r", encoding="utf-8") as f:
            col_clause = cols if cols else ""
            sql = (f"COPY {table} {col_clause} FROM STDIN "
                   f"WITH (FORMAT CSV, HEADER TRUE, NULL '')")
            cur.copy_expert(sql, f)
        conn.commit()
        cur.execute(f"SELECT count(*) FROM {table}")
        n = cur.fetchone()[0]
        el = time.time() - t0
        log(f"    {n:,} rows in {el:.1f}s")

    log("Post-import stats ...")
    cur.execute(
        "SELECT pg_size_pretty(pg_database_size(current_database()))"
    )
    log(f"  DB size: {cur.fetchone()[0]}")
    cur.execute(
        "SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) "
        "FROM pg_class WHERE relkind='r' "
        "AND relname IN ('properties','predictions','feature_attributions',"
        "'comps_index','sales_history','repeat_sale_index','ats_lookup') "
        "ORDER BY pg_total_relation_size(oid) DESC"
    )
    for name, sz in cur.fetchall():
        log(f"  {name:<28}  {sz}")

    cur.close()
    conn.close()
    log("Done.")


if __name__ == "__main__":
    main()
