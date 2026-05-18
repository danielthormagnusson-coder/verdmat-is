"""Phase D1 STEP 2 — read-only dryrun + coverage report + rollback SQL gen.

Loads D:\\phase_d1_enrichment.parquet (or .pkl fallback), prints detailed
coverage stats, generates D:\\phase_d1_rollback.sql, and (when SUPABASE_DB_URL
is set) verifies that a 500-fastnum sample exists in Supabase.

No Supabase WRITES. Halts the operator for explicit review before STEP 3.

If SUPABASE_DB_URL is not set, the 500-sample alignment check is left to
the runtime operator (Claude session uses execute_sql MCP). The dryrun
itself still produces full coverage stats + rollback SQL.
"""
from __future__ import annotations

import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ENRICHMENT_PARQUET = Path(r"D:\phase_d1_enrichment.parquet")
ENRICHMENT_PICKLE = Path(r"D:\phase_d1_enrichment.pkl")
ROLLBACK_SQL = Path(r"D:\phase_d1_rollback.sql")

ENRICHMENT_COLS = [
    "brunabotamat",
    "lhlmat",
    "fasteignamat_naesta_ar",
    "byggingarstig",
    "skodags",
    "gerd",
    "matsstig",
    "landeign_nr",
    "matseiningar",
    "tengd_stadfang_nr",
]


def load_enrichment() -> pd.DataFrame:
    if ENRICHMENT_PARQUET.exists():
        return pd.read_parquet(ENRICHMENT_PARQUET)
    if ENRICHMENT_PICKLE.exists():
        return pd.read_pickle(ENRICHMENT_PICKLE)
    raise FileNotFoundError(
        f"Neither {ENRICHMENT_PARQUET} nor {ENRICHMENT_PICKLE} found. "
        "Run phase_d1_extract.py first."
    )


def supabase_500_sample_check(fastnums: list[int]) -> tuple[int, int, list[int]]:
    """Returns (matched, sampled, missing_fastnums). Uses psycopg2 + env var.
    If SUPABASE_DB_URL not set, returns (-1, len(fastnums), []) — operator
    should run the check via MCP separately."""
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        return -1, len(fastnums), []
    try:
        import psycopg2
    except ImportError:
        print("  WARN psycopg2 not installed; skipping Supabase sample check")
        return -1, len(fastnums), []
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fastnum FROM public.properties WHERE fastnum = ANY(%s)",
                (fastnums,),
            )
            found = {r[0] for r in cur.fetchall()}
    finally:
        conn.close()
    sampled = set(fastnums)
    missing = sorted(sampled - found)
    return len(found), len(sampled), missing


def coverage_report(df: pd.DataFrame) -> None:
    n = len(df)
    print(f"\n=== Coverage report ({n:,} rows) ===\n")

    # Numeric columns
    for col in ("brunabotamat", "lhlmat", "fasteignamat_naesta_ar"):
        non_null = int(df[col].notna().sum())
        non_zero = int(((df[col].fillna(0)) > 0).sum())
        pct_nn = 100.0 * non_null / n if n else 0
        pct_nz = 100.0 * non_zero / n if n else 0
        print(f"  {col:<26s} non-null {non_null:>7,} ({pct_nn:5.1f}%)   non-zero {non_zero:>7,} ({pct_nz:5.1f}%)")

    # lhlmat distribution — verify it's in 0..1 range as documented
    valid_lhlmat = df["lhlmat"].dropna()
    if len(valid_lhlmat) > 0:
        out_of_range = int(((valid_lhlmat < 0) | (valid_lhlmat > 1)).sum())
        print(f"    lhlmat range: min={valid_lhlmat.min():.4f}  median={valid_lhlmat.median():.4f}  max={valid_lhlmat.max():.4f}  out-of-[0,1]={out_of_range}")

    # byggingarstig breakdown
    nn = int(df["byggingarstig"].notna().sum())
    print(f"\n  {'byggingarstig':<26s} non-null {nn:>7,} ({100.0*nn/n:5.1f}%)")
    bcounts = df["byggingarstig"].fillna("(null)").value_counts()
    for stage, count in bcounts.items():
        pct = 100.0 * count / n
        print(f"    {stage!r:<8s} {count:>7,} ({pct:5.1f}%)")

    # skodags range
    nn = int(df["skodags"].notna().sum())
    print(f"\n  {'skodags':<26s} non-null {nn:>7,} ({100.0*nn/n:5.1f}%)")
    valid_dates = df["skodags"].dropna()
    if len(valid_dates) > 0:
        print(f"    date range: {valid_dates.min()} .. {valid_dates.max()}")
        # How many are the 1970-01-01 sentinel ("never inspected")?
        sentinel_count = int((valid_dates == "1970-01-01").sum())
        print(f"    '1970-01-01' sentinel rows: {sentinel_count:,} ({100.0*sentinel_count/n:.1f}% of total)")

    # gerd distinct
    nn = int(df["gerd"].notna().sum())
    print(f"\n  {'gerd':<26s} non-null {nn:>7,} ({100.0*nn/n:5.1f}%)")
    gcounts = df["gerd"].fillna("(null)").value_counts().head(10)
    print(f"    top 10 by frequency:")
    for g, count in gcounts.items():
        print(f"      gerd={g!r:<8s} {count:>7,} ({100.0*count/n:5.1f}%)")

    # matsstig distinct
    nn = int(df["matsstig"].notna().sum())
    print(f"\n  {'matsstig':<26s} non-null {nn:>7,} ({100.0*nn/n:5.1f}%)")
    mcounts = df["matsstig"].fillna("(null)").value_counts().head(10)
    print(f"    top 10 by frequency:")
    for m, count in mcounts.items():
        print(f"      matsstig={m!r:<8s} {count:>7,} ({100.0*count/n:5.1f}%)")

    # landeign_nr non-null
    nn = int(df["landeign_nr"].notna().sum())
    print(f"\n  {'landeign_nr':<26s} non-null {nn:>7,} ({100.0*nn/n:5.1f}%)")
    distinct_le = df["landeign_nr"].nunique(dropna=True)
    print(f"    distinct landeign_nr values: {distinct_le:,}")

    # JSONB array fields
    for col_json, col_label in (("matseiningar_json", "matseiningar"),
                                ("tengd_stadfang_nr_json", "tengd_stadfang_nr")):
        nn = int(df[col_json].notna().sum())
        # Non-empty: column has JSON string AND it parses to non-empty list
        non_empty = 0
        for v in df[col_json].dropna():
            try:
                arr = json.loads(v)
                if isinstance(arr, list) and len(arr) > 0:
                    non_empty += 1
            except json.JSONDecodeError:
                pass
        print(f"\n  {col_label:<26s} non-null {nn:>7,} ({100.0*nn/n:5.1f}%)   non-empty {non_empty:>7,} ({100.0*non_empty/n:5.1f}%)")


def sample_pretty(df: pd.DataFrame, k: int = 5) -> None:
    print(f"\n=== {k} random sample fastnums with full enrichment payload ===\n")
    rng = random.Random(42)
    idxs = rng.sample(range(len(df)), min(k, len(df)))
    for i, idx in enumerate(idxs, 1):
        row = df.iloc[idx]
        print(f"--- sample {i} — fastnum={int(row['fastnum'])} ---")
        for col in ENRICHMENT_COLS:
            src = col + "_json" if col in ("matseiningar", "tengd_stadfang_nr") else col
            val = row[src]
            if col in ("matseiningar", "tengd_stadfang_nr") and val:
                try:
                    parsed = json.loads(val)
                    summary = json.dumps(parsed, ensure_ascii=False, indent=2)
                    if len(summary) > 600:
                        summary = summary[:580] + "\n    ... (truncated)"
                    print(f"  {col}:")
                    for line in summary.splitlines():
                        print(f"    {line}")
                except json.JSONDecodeError:
                    print(f"  {col}: <unparseable>")
            else:
                print(f"  {col}: {val}")
        print()


def generate_rollback(df: pd.DataFrame) -> None:
    fastnums = sorted(df["fastnum"].astype(int).tolist())
    print(f"\n=== Generating rollback SQL ({len(fastnums):,} fastnums) ===")
    in_list = ",".join(str(fn) for fn in fastnums)
    content = (
        "-- Phase D1 rollback — nulls every enrichment column on the 124,738 fastnums\n"
        "-- written by phase_d1_apply.py. Generated by phase_d1_dryrun.py.\n"
        "-- Generated 2026-05-18. Run via Supabase MCP execute_sql or psql against\n"
        "-- the same project (szzjsvmvxfrhyexblzvq).\n"
        "--\n"
        "-- Wrapped in a transaction; defensive IN-list so it cannot accidentally\n"
        "-- null rows inserted by future Phase D2/D3 steps.\n\n"
        "BEGIN;\n"
        "UPDATE public.properties SET\n"
        "  brunabotamat=NULL,\n"
        "  lhlmat=NULL,\n"
        "  fasteignamat_naesta_ar=NULL,\n"
        "  byggingarstig=NULL,\n"
        "  skodags=NULL,\n"
        "  gerd=NULL,\n"
        "  matsstig=NULL,\n"
        "  landeign_nr=NULL,\n"
        "  matseiningar=NULL,\n"
        "  tengd_stadfang_nr=NULL\n"
        f"WHERE fastnum IN ({in_list});\n"
        "COMMIT;\n"
    )
    ROLLBACK_SQL.write_text(content, encoding="utf-8")
    print(f"  wrote {ROLLBACK_SQL} ({ROLLBACK_SQL.stat().st_size:,} bytes)")


def main() -> int:
    df = load_enrichment()
    print(f"Loaded enrichment data: {len(df):,} rows × {len(df.columns)} cols")

    # Map _json column names back to the cleaner labels for the report
    # (extract.py wrote matseiningar_json / tengd_stadfang_nr_json)
    coverage_report(df)
    sample_pretty(df, k=5)

    # Supabase 500-sample alignment check
    print("\n=== Supabase 500-fastnum sample alignment ===")
    rng = random.Random(20260518)
    sample_size = min(500, len(df))
    sample_fastnums = rng.sample(df["fastnum"].astype(int).tolist(), sample_size)
    matched, sampled, missing = supabase_500_sample_check(sample_fastnums)
    if matched == -1:
        print("  SKIPPED — SUPABASE_DB_URL not set or psycopg2 unavailable.")
        print("  Operator should verify via MCP execute_sql:")
        print(f"    SELECT count(*) FROM public.properties WHERE fastnum = ANY(ARRAY[")
        print(f"      {','.join(str(x) for x in sample_fastnums[:10])}, ... (490 more)")
        print(f"    ]::bigint[]);")
        print(f"    Expected: {sampled}/{sampled} matched.")
    else:
        print(f"  Sampled {sampled} fastnums, matched {matched} in Supabase.")
        if matched < sampled:
            print(f"  WARN {sampled - matched} fastnums NOT in Supabase: {missing[:10]} (top 10)")
            print(f"  STOP — staging has fastnums Supabase doesn't have. Investigate.")
            return 1
        else:
            print(f"  OK: {sampled}/{sampled} match. Apply is safe.")

    generate_rollback(df)

    print("\n" + "=" * 70)
    print("STEP 2 complete. NO Supabase writes performed.")
    print("=" * 70)
    print("HALT POINT: review coverage above, spot-check sample fastnums,")
    print("            confirm rollback file exists at D:\\phase_d1_rollback.sql,")
    print("            then explicitly say 'proceed with apply' before STEP 3.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
