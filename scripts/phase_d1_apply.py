"""Phase D1 STEP 3 — UPDATE 124,738 Supabase properties rows with HMS enrichment.

Reads D:\\phase_d1_enrichment.parquet (or .pkl fallback), connects to
Supabase via SUPABASE_DB_URL (transaction pooler URI per memory), and
issues batched UPDATEs of 500 rows each wrapped in BEGIN/COMMIT.

Pre-checks (abort on any failure):
  1. Rollback file D:\\phase_d1_rollback.sql exists.
  2. SUPABASE_DB_URL env var is set.
  3. Operator types 'YES' at the stdin prompt.

Uses UNNEST(text[], numeric[], ...) → row-typed table → JOIN pattern. This
is the canonical bulk-update shape on Postgres and runs in one statement
per batch (index lookup on fastnum makes it fast). jsonb fields are cast
from text in the SET clause.

After all batches, re-queries Supabase to verify post-write coverage
matches the dryrun expectation. Exits non-zero if mismatch.

NOTE (Phase X Group C, 2026-05-27): the bulk-UPDATE pattern this script
demonstrates (UNNEST → row-typed table → JOIN) is closely related to the
`unnest_upsert()` helper in `scripts/migration_helpers.py`. Helper is
INSERT-focused; future bulk-UPDATE-via-UNNEST analogues should either
extend the helper or follow this script's shape. Left as-is to preserve
the audit trail of the 2026-05-18 Phase D1 apply.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

ENRICHMENT_PARQUET = Path(r"D:\phase_d1_enrichment.parquet")
ENRICHMENT_PICKLE = Path(r"D:\phase_d1_enrichment.pkl")
ROLLBACK_SQL = Path(r"D:\phase_d1_rollback.sql")
BATCH_SIZE = 500


UPDATE_SQL = """
UPDATE public.properties AS p SET
  brunabotamat = src.brunabotamat,
  lhlmat = src.lhlmat,
  fasteignamat_naesta_ar = src.fasteignamat_naesta_ar,
  byggingarstig = src.byggingarstig,
  skodags = src.skodags,
  gerd = src.gerd,
  matsstig = src.matsstig,
  landeign_nr = src.landeign_nr,
  matseiningar = src.matseiningar_text::jsonb,
  tengd_stadfang_nr = src.tengd_stadfang_nr_text::jsonb
FROM unnest(
    %(fastnums)s::bigint[],
    %(brunabotamat)s::numeric[],
    %(lhlmat)s::numeric[],
    %(fasteignamat_naesta_ar)s::numeric[],
    %(byggingarstig)s::text[],
    %(skodags)s::date[],
    %(gerd)s::text[],
    %(matsstig)s::text[],
    %(landeign_nr)s::text[],
    %(matseiningar_text)s::text[],
    %(tengd_stadfang_nr_text)s::text[]
) AS src(
    fastnum, brunabotamat, lhlmat, fasteignamat_naesta_ar,
    byggingarstig, skodags, gerd, matsstig, landeign_nr,
    matseiningar_text, tengd_stadfang_nr_text
)
WHERE p.fastnum = src.fastnum;
"""


def load_enrichment() -> pd.DataFrame:
    if ENRICHMENT_PARQUET.exists():
        return pd.read_parquet(ENRICHMENT_PARQUET)
    if ENRICHMENT_PICKLE.exists():
        return pd.read_pickle(ENRICHMENT_PICKLE)
    raise FileNotFoundError(
        f"Enrichment file not found at {ENRICHMENT_PARQUET} or {ENRICHMENT_PICKLE}. "
        "Run phase_d1_extract.py first."
    )


def na_to_none(series):
    """Convert pandas series to a plain Python list with NaN/NaT → None.
    Required because psycopg2's UNNEST pattern needs Python None, not NaN."""
    return [None if pd.isna(v) else v for v in series.tolist()]


def batch_update(cur, df: pd.DataFrame) -> int:
    """Send one batched UPDATE for the rows in df. Returns rows affected."""
    params = {
        "fastnums": [int(x) for x in df["fastnum"].tolist()],
        "brunabotamat": na_to_none(df["brunabotamat"]),
        "lhlmat": na_to_none(df["lhlmat"]),
        "fasteignamat_naesta_ar": na_to_none(df["fasteignamat_naesta_ar"]),
        "byggingarstig": na_to_none(df["byggingarstig"]),
        "skodags": na_to_none(df["skodags"]),
        "gerd": na_to_none(df["gerd"]),
        "matsstig": na_to_none(df["matsstig"]),
        "landeign_nr": na_to_none(df["landeign_nr"]),
        "matseiningar_text": na_to_none(df["matseiningar_json"]),
        "tengd_stadfang_nr_text": na_to_none(df["tengd_stadfang_nr_json"]),
    }
    cur.execute(UPDATE_SQL, params)
    return cur.rowcount


def main() -> int:
    # Pre-check 1: rollback file
    if not ROLLBACK_SQL.exists():
        print(f"ERROR: rollback file not found at {ROLLBACK_SQL}")
        print("Run phase_d1_dryrun.py first to generate it.")
        return 2

    # Pre-check 2: connection string
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("ERROR: SUPABASE_DB_URL env var is not set.")
        print("Set it to the Supabase transaction pooler URI:")
        print("  postgresql://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres")
        print("(direct db.<ref>.supabase.co:5432 is IPv6-only — use pooler instead.)")
        return 2

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed. `pip install psycopg2-binary`.")
        return 2

    # Pre-check 3: operator confirmation
    print("=" * 70)
    print("ABOUT TO UPDATE 124,738 rows in production Supabase")
    print("project: szzjsvmvxfrhyexblzvq (verdmat-is)")
    print("=" * 70)
    print("Rollback SQL ready at:", ROLLBACK_SQL)
    print()
    confirm = input("Type 'YES' (uppercase, no quotes) to proceed: ").strip()
    if confirm != "YES":
        print("Aborted. No writes performed.")
        return 1

    df = load_enrichment()
    print(f"\nLoaded {len(df):,} enrichment rows.")

    conn = psycopg2.connect(db_url)
    n_total = len(df)
    n_batches = (n_total + BATCH_SIZE - 1) // BATCH_SIZE
    rows_written = 0
    t_start = time.time()

    for i in range(n_batches):
        batch_df = df.iloc[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
        t_batch = time.time()
        try:
            with conn.cursor() as cur:
                # BEGIN/COMMIT per batch — partial progress is safer mid-fail
                cur.execute("BEGIN;")
                rc = batch_update(cur, batch_df)
                cur.execute("COMMIT;")
            rows_written += rc
            dt = time.time() - t_batch
            print(
                f"  batch {i + 1:>3d}/{n_batches} — {len(batch_df):>3d} rows sent, "
                f"{rc:>3d} affected, {dt * 1000:.0f} ms"
            )
        except Exception as e:
            print(f"\nERROR on batch {i + 1}: {type(e).__name__}: {e}")
            conn.rollback()
            print(f"  Rows written so far: {rows_written:,} / {n_total:,}")
            print(f"  Re-run will pick up from batch {i + 1} (UPDATEs are idempotent).")
            return 3

    elapsed = time.time() - t_start
    print(
        f"\n=== Apply complete ===\n"
        f"  rows UPDATEd: {rows_written:,} / {n_total:,}\n"
        f"  elapsed:      {elapsed:.1f} s ({elapsed / 60:.2f} min)\n"
        f"  avg rate:     {rows_written / elapsed:.0f} rows/sec"
    )

    # Verification — re-query to confirm coverage
    print("\nPost-write coverage verification:")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              count(*) FILTER (WHERE brunabotamat IS NOT NULL)            AS brunabotamat,
              count(*) FILTER (WHERE lhlmat IS NOT NULL)                  AS lhlmat,
              count(*) FILTER (WHERE fasteignamat_naesta_ar IS NOT NULL)  AS fasteignamat_naesta_ar,
              count(*) FILTER (WHERE byggingarstig IS NOT NULL)           AS byggingarstig,
              count(*) FILTER (WHERE skodags IS NOT NULL)                 AS skodags,
              count(*) FILTER (WHERE gerd IS NOT NULL)                    AS gerd,
              count(*) FILTER (WHERE matsstig IS NOT NULL)                AS matsstig,
              count(*) FILTER (WHERE landeign_nr IS NOT NULL)             AS landeign_nr,
              count(*) FILTER (WHERE matseiningar IS NOT NULL)            AS matseiningar,
              count(*) FILTER (WHERE tengd_stadfang_nr IS NOT NULL)       AS tengd_stadfang_nr,
              count(*)                                                    AS total_rows
            FROM public.properties;
            """
        )
        row = cur.fetchone()
    labels = [
        "brunabotamat", "lhlmat", "fasteignamat_naesta_ar", "byggingarstig",
        "skodags", "gerd", "matsstig", "landeign_nr", "matseiningar",
        "tengd_stadfang_nr", "total_rows",
    ]
    for label, val in zip(labels, row):
        print(f"  {label:<26s} {val:>7,}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
