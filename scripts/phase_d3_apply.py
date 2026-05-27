"""Phase D3 NOW-lota STEP 3 — apply 3 idempotent INSERTs to Supabase.

Pre-checks (abort on any failure):
  - Rollback file D:\\phase_d3_rollback.sql exists.
  - Three parquet artifacts present.
  - SUPABASE_DB_URL env var set (or .dbconfig fallback).
  - Data-integrity: matsvaedi-unconfident OR coordless rows must NOT
    carry an M-bucket (stored matsvaedi must match scoring treatment).
  - Operator types 'YES' at the stdin prompt.

Apply order (each block is its own BEGIN/COMMIT per batch of 500):
  1. INSERT properties      (~108K, ON CONFLICT (fastnum) DO NOTHING)
  2. INSERT sales_history   (~786, no on-conflict — fastnum-existence
     dryrun-confirmed, sales_history.id is serial, no composite key)
  3. INSERT predictions     (~57K, ON CONFLICT (fastnum) DO NOTHING,
     model_version='iter4_final_v1', calibration_version='iter4_conformal_v1')

Post-apply: row-count verification queries (read-only).

NOTE (Phase X Group C, 2026-05-27): the per-table UNNEST-INSERT-with-
ON-CONFLICT pattern in this file is now generalised in
`scripts/migration_helpers.py:unnest_upsert()`. Future analogue scripts
(D4 cross_property_refs, D5 photo_urls_json, evalue augl-pass) should
import the helper. Left as-is to preserve the audit trail of the
2026-05-27 Phase D3 apply.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

INSERT_PARQUET = Path(r"D:\phase_d3_insert_rows.parquet")
SALES_PARQUET = Path(r"D:\phase_d3_sales_rows.parquet")
PREDS_PARQUET = Path(r"D:\phase_d3_predictions.parquet")
ROLLBACK_SQL = Path(r"D:\phase_d3_rollback.sql")
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
BATCH = 500


PROPS_INSERT_SQL = """
INSERT INTO public.properties (
  fastnum, heimilisfang, husnr, postnr, postheiti, svfn, sveitarfelag,
  tegund_raw, canonical_code, unit_category, unit_family,
  is_residential, is_summerhouse, is_new_build, is_main_unit,
  einflm, lod_flm, byggar, fjherb, fullbuid,
  lat, lng, matsvaedi_numer, matsvaedi_bucket, region_tier,
  fasteignamat, fasteignamat_gildandi, brunabotamat, lhlmat,
  fasteignamat_naesta_ar, byggingarstig, skodags, gerd, matsstig,
  landeign_nr, matseiningar, tengd_stadfang_nr, deregistered
)
SELECT
  fastnum, heimilisfang, husnr, postnr, postheiti, svfn, sveitarfelag,
  tegund_raw, canonical_code, unit_category, unit_family,
  is_residential, is_summerhouse, is_new_build, is_main_unit,
  einflm, lod_flm, byggar, fjherb, fullbuid,
  lat, lng, matsvaedi_numer, matsvaedi_bucket, region_tier,
  fasteignamat, fasteignamat_gildandi, brunabotamat, lhlmat,
  fasteignamat_naesta_ar, byggingarstig, skodags, gerd, matsstig,
  landeign_nr, matseiningar_text::jsonb, tengd_text::jsonb, deregistered
FROM unnest(
    %(fastnum)s::bigint[],
    %(heimilisfang)s::text[],
    %(husnr)s::numeric[],
    %(postnr)s::integer[],
    %(postheiti)s::text[],
    %(svfn)s::numeric[],
    %(sveitarfelag)s::text[],
    %(tegund_raw)s::text[],
    %(canonical_code)s::text[],
    %(unit_category)s::text[],
    %(unit_family)s::text[],
    %(is_residential)s::boolean[],
    %(is_summerhouse)s::boolean[],
    %(is_new_build)s::boolean[],
    %(is_main_unit)s::boolean[],
    %(einflm)s::numeric[],
    %(lod_flm)s::numeric[],
    %(byggar)s::numeric[],
    %(fjherb)s::numeric[],
    %(fullbuid)s::numeric[],
    %(lat)s::double precision[],
    %(lng)s::double precision[],
    %(matsvaedi_numer)s::integer[],
    %(matsvaedi_bucket)s::text[],
    %(region_tier)s::text[],
    %(fasteignamat)s::numeric[],
    %(fasteignamat_gildandi)s::numeric[],
    %(brunabotamat)s::numeric[],
    %(lhlmat)s::numeric[],
    %(fasteignamat_naesta_ar)s::numeric[],
    %(byggingarstig)s::text[],
    %(skodags)s::date[],
    %(gerd)s::text[],
    %(matsstig)s::text[],
    %(landeign_nr)s::text[],
    %(matseiningar_text)s::text[],
    %(tengd_text)s::text[],
    %(deregistered)s::boolean[]
) AS src(
    fastnum, heimilisfang, husnr, postnr, postheiti, svfn, sveitarfelag,
    tegund_raw, canonical_code, unit_category, unit_family,
    is_residential, is_summerhouse, is_new_build, is_main_unit,
    einflm, lod_flm, byggar, fjherb, fullbuid,
    lat, lng, matsvaedi_numer, matsvaedi_bucket, region_tier,
    fasteignamat, fasteignamat_gildandi, brunabotamat, lhlmat,
    fasteignamat_naesta_ar, byggingarstig, skodags, gerd, matsstig,
    landeign_nr, matseiningar_text, tengd_text, deregistered
)
ON CONFLICT (fastnum) DO NOTHING;
"""

SALES_INSERT_SQL = """
INSERT INTO public.sales_history (
  fastnum, thinglystdags, kaupverd_nominal, kaupverd_real,
  einflm_at_sale, byggar_at_sale, onothaefur
)
SELECT * FROM unnest(
    %(fastnum)s::bigint[],
    %(thinglystdags)s::date[],
    %(kaupverd_nominal)s::bigint[],
    %(kaupverd_real)s::bigint[],
    %(einflm_at_sale)s::numeric[],
    %(byggar_at_sale)s::numeric[],
    %(onothaefur)s::smallint[]
) AS src(
    fastnum, thinglystdags, kaupverd_nominal, kaupverd_real,
    einflm_at_sale, byggar_at_sale, onothaefur
);
"""

PREDS_INSERT_SQL = """
INSERT INTO public.predictions (
  fastnum, real_pred_mean, real_pred_median,
  real_pred_lo80, real_pred_hi80, real_pred_lo95, real_pred_hi95,
  model_group, segment, model_version, calibration_version, predicted_at
)
SELECT * FROM unnest(
    %(fastnum)s::bigint[],
    %(real_pred_mean)s::bigint[],
    %(real_pred_median)s::bigint[],
    %(real_pred_lo80)s::bigint[],
    %(real_pred_hi80)s::bigint[],
    %(real_pred_lo95)s::bigint[],
    %(real_pred_hi95)s::bigint[],
    %(model_group)s::text[],
    %(segment)s::text[],
    %(model_version)s::text[],
    %(calibration_version)s::text[],
    %(predicted_at)s::date[]
) AS src(
    fastnum, real_pred_mean, real_pred_median,
    real_pred_lo80, real_pred_hi80, real_pred_lo95, real_pred_hi95,
    model_group, segment, model_version, calibration_version, predicted_at
)
ON CONFLICT (fastnum) DO NOTHING;
"""


def na_to_none(s):
    return [None if pd.isna(v) else v for v in s.tolist()]


def na_to_none_str(s):
    return [None if pd.isna(v) else str(v) for v in s.tolist()]


def integrity_check(props: pd.DataFrame) -> bool:
    print("Data-integrity pre-check ...")
    unconfident = ~props["matsvaedi_confident"].fillna(False).astype(bool)
    no_xy = props["lat"].isna() | props["lng"].isna()
    bad1 = props[unconfident & props["matsvaedi_bucket"].str.startswith("M", na=False)]
    bad2 = props[props["matsvaedi_confident"].fillna(False).astype(bool)
                 & props["matsvaedi_numer"].isna()]
    bad3 = props[no_xy & props["matsvaedi_numer"].notna()]
    print(f"  unconfident WITH M-bucket:        {len(bad1):,}  (must be 0)")
    print(f"  confident WITH no matsvaedi_numer: {len(bad2):,}  (must be 0)")
    print(f"  coordless with matsvaedi_numer:    {len(bad3):,}  (must be 0)")
    return len(bad1) == 0 and len(bad2) == 0 and len(bad3) == 0


def get_db_url() -> str:
    if "SUPABASE_DB_URL" in os.environ:
        return os.environ["SUPABASE_DB_URL"]
    if DBCONFIG.exists():
        return DBCONFIG.read_text(encoding="utf-8-sig").strip()
    raise SystemExit("SUPABASE_DB_URL not set and .dbconfig missing")


def apply_properties(conn, df: pd.DataFrame) -> int:
    """INSERT properties in batches of BATCH. Returns total rows affected."""
    total = 0
    n_batches = (len(df) + BATCH - 1) // BATCH
    t_start = time.time()
    for i in range(n_batches):
        b = df.iloc[i * BATCH:(i + 1) * BATCH]
        t_b = time.time()
        params = {
            "fastnum": [int(x) for x in b["fastnum"]],
            "heimilisfang": na_to_none(b["heimilisfang"]),
            "husnr": na_to_none(b["husnr"]),
            "postnr": [None if pd.isna(v) else int(v) for v in b["postnr"]],
            "postheiti": na_to_none(b["postheiti"]),
            "svfn": na_to_none(b["svfn"]),
            "sveitarfelag": na_to_none(b["sveitarfelag"]),
            "tegund_raw": na_to_none(b["tegund_raw"]),
            "canonical_code": na_to_none(b["canonical_code"]),
            "unit_category": na_to_none(b["unit_category"]),
            "unit_family": na_to_none(b["unit_family"]),
            "is_residential": [bool(v) for v in b["is_residential"]],
            "is_summerhouse": [bool(v) for v in b["is_summerhouse"]],
            "is_new_build": [None if pd.isna(v) else bool(v) for v in b["is_new_build"]],
            "is_main_unit": [None if pd.isna(v) else bool(v) for v in b["is_main_unit"]],
            "einflm": na_to_none(b["einflm"]),
            "lod_flm": na_to_none(b["lod_flm"]),
            "byggar": na_to_none(b["byggar"]),
            "fjherb": na_to_none(b["fjherb"]),
            "fullbuid": na_to_none(b["fullbuid"]),
            "lat": na_to_none(b["lat"]),
            "lng": na_to_none(b["lng"]),
            "matsvaedi_numer": [None if pd.isna(v) else int(v) for v in b["matsvaedi_numer"]],
            "matsvaedi_bucket": na_to_none(b["matsvaedi_bucket"]),
            "region_tier": na_to_none(b["region_tier"]),
            "fasteignamat": na_to_none(b["fasteignamat"]),
            "fasteignamat_gildandi": na_to_none(b["fasteignamat_gildandi"]),
            "brunabotamat": na_to_none(b["brunabotamat"]),
            "lhlmat": na_to_none(b["lhlmat"]),
            "fasteignamat_naesta_ar": na_to_none(b["fasteignamat_naesta_ar"]),
            "byggingarstig": na_to_none(b["byggingarstig"]),
            "skodags": na_to_none(b["skodags"]),
            "gerd": na_to_none(b["gerd"]),
            "matsstig": na_to_none(b["matsstig"]),
            "landeign_nr": na_to_none(b["landeign_nr"]),
            "matseiningar_text": na_to_none(b["matseiningar_json"]),
            "tengd_text": na_to_none(b["tengd_stadfang_nr_json"]),
            "deregistered": [bool(v) if not pd.isna(v) else False
                             for v in b["deregistered"]],
        }
        try:
            with conn.cursor() as cur:
                cur.execute("BEGIN;")
                cur.execute(PROPS_INSERT_SQL, params)
                rc = cur.rowcount
                cur.execute("COMMIT;")
            total += rc
            print(f"  properties batch {i + 1:>4d}/{n_batches} — "
                  f"{len(b):>3d} sent, {rc:>3d} inserted, "
                  f"{(time.time() - t_b) * 1000:.0f} ms")
        except Exception as e:
            print(f"  ERROR batch {i + 1}: {type(e).__name__}: {e}")
            conn.rollback()
            return total
    print(f"  properties: {total:,} inserted in {time.time() - t_start:.1f}s")
    return total


def apply_sales(conn, df: pd.DataFrame) -> int:
    total = 0
    n_batches = (len(df) + BATCH - 1) // BATCH
    t_start = time.time()
    for i in range(n_batches):
        b = df.iloc[i * BATCH:(i + 1) * BATCH]
        t_b = time.time()
        params = {
            "fastnum": [int(x) for x in b["fastnum"]],
            "thinglystdags": na_to_none(b["thinglystdags"]),
            "kaupverd_nominal": [None if pd.isna(v) else int(v)
                                  for v in b["kaupverd_nominal"]],
            "kaupverd_real": [None if pd.isna(v) else int(v)
                              for v in b["kaupverd_real"]],
            "einflm_at_sale": na_to_none(b["einflm_at_sale"]),
            "byggar_at_sale": na_to_none(b["byggar_at_sale"]),
            "onothaefur": [int(v) for v in b["onothaefur"]],
        }
        try:
            with conn.cursor() as cur:
                cur.execute("BEGIN;")
                cur.execute(SALES_INSERT_SQL, params)
                rc = cur.rowcount
                cur.execute("COMMIT;")
            total += rc
            print(f"  sales batch {i + 1}/{n_batches} — {len(b)} sent, "
                  f"{rc} inserted, {(time.time() - t_b) * 1000:.0f} ms")
        except Exception as e:
            print(f"  ERROR batch {i + 1}: {type(e).__name__}: {e}")
            conn.rollback()
            return total
    print(f"  sales_history: {total:,} inserted in {time.time() - t_start:.1f}s")
    return total


def apply_predictions(conn, df: pd.DataFrame) -> int:
    total = 0
    n_batches = (len(df) + BATCH - 1) // BATCH
    t_start = time.time()
    for i in range(n_batches):
        b = df.iloc[i * BATCH:(i + 1) * BATCH]
        t_b = time.time()
        params = {
            "fastnum": [int(x) for x in b["fastnum"]],
            "real_pred_mean": [int(v) for v in b["real_pred_mean"]],
            "real_pred_median": [int(v) for v in b["real_pred_median"]],
            "real_pred_lo80": [int(v) for v in b["real_pred_lo80"]],
            "real_pred_hi80": [int(v) for v in b["real_pred_hi80"]],
            "real_pred_lo95": [int(v) for v in b["real_pred_lo95"]],
            "real_pred_hi95": [int(v) for v in b["real_pred_hi95"]],
            "model_group": na_to_none(b["model_group"]),
            "segment": na_to_none(b["segment"]),
            "model_version": na_to_none(b["model_version"]),
            "calibration_version": na_to_none(b["calibration_version"]),
            "predicted_at": na_to_none(b["predicted_at"]),
        }
        try:
            with conn.cursor() as cur:
                cur.execute("BEGIN;")
                cur.execute(PREDS_INSERT_SQL, params)
                rc = cur.rowcount
                cur.execute("COMMIT;")
            total += rc
            print(f"  preds batch {i + 1:>3d}/{n_batches} — {len(b):>3d} sent, "
                  f"{rc:>3d} inserted, {(time.time() - t_b) * 1000:.0f} ms")
        except Exception as e:
            print(f"  ERROR batch {i + 1}: {type(e).__name__}: {e}")
            conn.rollback()
            return total
    print(f"  predictions: {total:,} inserted in {time.time() - t_start:.1f}s")
    return total


def main() -> int:
    print("=" * 70)
    print("Phase D3 NOW-lota apply")
    print("=" * 70)

    if not ROLLBACK_SQL.exists():
        print(f"ERROR: rollback file missing at {ROLLBACK_SQL}")
        print("Run phase_d3_dryrun.py first.")
        return 2
    for p in (INSERT_PARQUET, SALES_PARQUET, PREDS_PARQUET):
        if not p.exists():
            print(f"ERROR: missing artifact {p}")
            return 2

    print(f"Loading parquets ...")
    props = pd.read_parquet(INSERT_PARQUET)
    sales = pd.read_parquet(SALES_PARQUET)
    preds = pd.read_parquet(PREDS_PARQUET)
    print(f"  properties:    {len(props):,}")
    print(f"  sales_history: {len(sales):,}")
    print(f"  predictions:   {len(preds):,}")

    if not integrity_check(props):
        print("ABORT: integrity check failed.")
        return 3

    # Predictions stamping check
    bad_mv = preds["model_version"].ne("iter4_final_v1")
    bad_cv = preds["calibration_version"].ne("iter4_conformal_v1")
    if bad_mv.any() or bad_cv.any():
        print(f"ABORT: predictions wrong stamps "
              f"(mv mismatch={int(bad_mv.sum())}, cv mismatch={int(bad_cv.sum())})")
        return 3
    print(f"  predictions stamps OK: 'iter4_final_v1' + 'iter4_conformal_v1' on all rows")

    # Onothaefur sanity
    n_arm = int((sales["onothaefur"] == 0).sum())
    n_un_arm = int((sales["onothaefur"] == 1).sum())
    print(f"  sales onothaefur: arm's-length={n_arm}, un-arm's-length={n_un_arm}")
    print(f"  (must match dryrun: 487 / 299)")

    db_url = get_db_url()
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed")
        return 2

    print("\n" + "=" * 70)
    print("ABOUT TO WRITE TO SUPABASE (project szzjsvmvxfrhyexblzvq)")
    print("=" * 70)
    print(f"  properties INSERT:    {len(props):,}")
    print(f"  sales_history INSERT: {len(sales):,}")
    print(f"  predictions INSERT:   {len(preds):,}")
    print(f"  Rollback at:          {ROLLBACK_SQL}")
    print()
    confirm = input("Type 'YES' (uppercase, no quotes) to proceed: ").strip()
    if confirm != "YES":
        print("Aborted. No writes performed.")
        return 1

    conn = psycopg2.connect(db_url)

    # ============================================================
    # Block 1: properties
    # ============================================================
    print("\n--- Block 1: properties ---")
    n_props = apply_properties(conn, props)
    if n_props != len(props):
        print(f"  WARN: only {n_props} of {len(props)} rows inserted "
              f"(ON CONFLICT skipped {len(props) - n_props})")

    # ============================================================
    # Block 2: sales_history
    # ============================================================
    print("\n--- Block 2: sales_history ---")
    n_sales = apply_sales(conn, sales)
    if n_sales != len(sales):
        print(f"  WARN: only {n_sales} of {len(sales)} sales inserted")

    # ============================================================
    # Block 3: predictions
    # ============================================================
    print("\n--- Block 3: predictions ---")
    n_preds = apply_predictions(conn, preds)
    if n_preds != len(preds):
        print(f"  WARN: only {n_preds} of {len(preds)} predictions inserted "
              f"(ON CONFLICT skipped {len(preds) - n_preds})")

    # ============================================================
    # Post-apply verification
    # ============================================================
    print("\n" + "=" * 70)
    print("POST-APPLY VERIFICATION")
    print("=" * 70)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM public.properties")
        n_props_now = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM public.predictions")
        n_preds_now = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM public.sales_history")
        n_sales_now = cur.fetchone()[0]
    print(f"  properties     now {n_props_now:,}  (expected 232,887)")
    print(f"  predictions    now {n_preds_now:,}  (expected 167,503)")
    print(f"  sales_history  now {n_sales_now:,}  (expected previous + 786)")

    with conn.cursor() as cur:
        cur.execute(
            "SELECT model_version, calibration_version, count(*) "
            "FROM public.predictions "
            "WHERE model_version='iter4_final_v1' "
            "  AND calibration_version='iter4_conformal_v1' "
            "GROUP BY 1,2"
        )
        for r in cur.fetchall():
            print(f"  predictions stamp {r[0]!r}/{r[1]!r}: {r[2]:,}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
