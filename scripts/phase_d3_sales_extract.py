"""Phase D3 STEP 1b — extract sales_history INSERT rows for ~108K net-new fastnums.

Reads D:\\kaupskra.csv (HMS thinglýsing dump, current as of 2026-04-20 per
DECISIONS), filters FASTNUM ∈ phase_d3_insert_rows.parquet's fastnum set,
applies CPI deflation via training_data_v2.pkl's per-month cpi_factor
lookup, and writes the result to D:\\phase_d3_sales_rows.parquet.

Schema matches public.sales_history (sans 'id', which is serial-assigned
by Postgres):
  fastnum, thinglystdags, kaupverd_nominal, kaupverd_real,
  einflm_at_sale, byggar_at_sale, onothaefur

Units: kaupskra KAUPVERD is in þús.kr; multiply by 1000 to match
sales_history.kaupverd_nominal (kr). kaupverd_real = KAUPVERD * cpi_factor
* 1000 where cpi_factor brings nominal-at-sale → 2026-04 reference VNV.

onothaefur=1 (un-arm's-length sales) ARE included — the existing
sales_history table contains 121 such rows, so filtering is upstream
consumers' responsibility (training pipeline filters on this column).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

INSERT_PARQUET = Path(r"D:\phase_d3_insert_rows.parquet")
KAUPSKRA_CSV = Path(r"D:\kaupskra.csv")
TRAINING_PKL = Path(r"D:\training_data_v2.pkl")
OUT_PARQUET = Path(r"D:\phase_d3_sales_rows.parquet")
OUT_PICKLE_FALLBACK = Path(r"D:\phase_d3_sales_rows.pkl")


def build_cpi_lookup() -> dict[tuple[int, int], float]:
    """Build (year, month) → cpi_factor lookup from training_data_v2.pkl.

    cpi_factor brings nominal-at-sale to reference VNV (April 2026).
    """
    td = pd.read_pickle(TRAINING_PKL)
    td = td.dropna(subset=["THINGLYSTDAGS", "cpi_factor"]).copy()
    td["_yr"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.year.astype(int)
    td["_mn"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.month.astype(int)
    # cpi_factor is identical within (yr, mn) — take first
    lookup = td.groupby(["_yr", "_mn"])["cpi_factor"].first().to_dict()
    return lookup


def main() -> int:
    if not INSERT_PARQUET.exists():
        print(f"ERROR: insert parquet not found at {INSERT_PARQUET}")
        print("Run phase_d3_extract.py first.")
        return 2

    print(f"Loading insert universe from {INSERT_PARQUET} ...")
    ins = pd.read_parquet(INSERT_PARQUET, columns=["fastnum"])
    insert_fns = set(int(x) for x in ins["fastnum"].tolist())
    print(f"  insert universe: {len(insert_fns):,} fastnums")

    print(f"\nLoading kaupskra.csv ...")
    kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
    print(f"  kaupskra: {len(kp):,} rows")
    kp["FASTNUM"] = pd.to_numeric(kp["FASTNUM"], errors="coerce").astype("Int64")
    kp = kp.dropna(subset=["FASTNUM"])
    kp["FASTNUM_i"] = kp["FASTNUM"].astype("int64")

    # Filter to insert universe
    mask = kp["FASTNUM_i"].isin(insert_fns)
    sub = kp[mask].copy()
    print(f"  sales matching insert universe: {len(sub):,} "
          f"({sub['FASTNUM_i'].nunique():,} distinct fastnums)")

    # Parse + coerce
    sub["thinglystdags"] = pd.to_datetime(sub["THINGLYSTDAGS"], errors="coerce",
                                          format="ISO8601")
    sub = sub.dropna(subset=["thinglystdags"]).copy()
    sub["KAUPVERD"] = pd.to_numeric(sub["KAUPVERD"], errors="coerce")
    sub["EINFLM"] = pd.to_numeric(sub["EINFLM"], errors="coerce")
    sub["BYGGAR"] = pd.to_numeric(sub["BYGGAR"], errors="coerce")
    sub["ONOTHAEFUR_SAMNINGUR"] = pd.to_numeric(sub["ONOTHAEFUR_SAMNINGUR"],
                                                errors="coerce").fillna(0).astype(int)

    # CPI factor lookup
    print(f"\nBuilding CPI factor lookup from training_data_v2.pkl ...")
    cpi_lookup = build_cpi_lookup()
    print(f"  cpi lookup: {len(cpi_lookup)} (year, month) keys")
    sub["_yr"] = sub["thinglystdags"].dt.year.astype(int)
    sub["_mn"] = sub["thinglystdags"].dt.month.astype(int)
    sub["cpi_factor"] = [cpi_lookup.get((y, m)) for y, m in zip(sub["_yr"], sub["_mn"])]
    n_no_cpi = int(sub["cpi_factor"].isna().sum())
    if n_no_cpi:
        print(f"  WARN: {n_no_cpi:,} sales without CPI factor "
              f"({100.0 * n_no_cpi / len(sub):.1f}%) — kaupverd_real will be NULL")

    # Build output frame
    # kaupverd_nominal = KAUPVERD (þús.kr) × 1000 (kr)
    # kaupverd_real    = KAUPVERD × cpi_factor × 1000
    out = pd.DataFrame({
        "fastnum": sub["FASTNUM_i"].astype("int64"),
        "thinglystdags": sub["thinglystdags"].dt.date,
        "kaupverd_nominal": (sub["KAUPVERD"] * 1000).round().astype("Int64"),
        "kaupverd_real": (sub["KAUPVERD"] * sub["cpi_factor"] * 1000).round().astype("Int64"),
        "einflm_at_sale": sub["EINFLM"],
        "byggar_at_sale": sub["BYGGAR"],
        "onothaefur": sub["ONOTHAEFUR_SAMNINGUR"].astype("int16"),
    })

    # Drop rows with no nominal price (KAUPVERD missing or 0)
    before = len(out)
    out = out[out["kaupverd_nominal"].notna() & (out["kaupverd_nominal"] > 0)]
    dropped = before - len(out)
    if dropped:
        print(f"  dropped {dropped:,} rows with missing/zero KAUPVERD")

    print(f"\nFinal sales_history rows: {len(out):,}")
    print(f"  distinct fastnums with sales:    {out['fastnum'].nunique():,}")
    print(f"  insert FNs with NO sales rows:   "
          f"{len(insert_fns) - out['fastnum'].nunique():,} "
          f"(expected — many net-new HMS fastnums were never thinglýstir)")

    print("\nonothaefur breakdown:")
    for v, n in out["onothaefur"].value_counts().sort_index().items():
        print(f"  onothaefur={v}  {n:>7,}")

    print("\nthinglystdags range:")
    print(f"  {out['thinglystdags'].min()} .. {out['thinglystdags'].max()}")
    print(f"  per-decade counts:")
    yrs = pd.to_datetime(out["thinglystdags"]).dt.year
    for decade, n in (yrs // 10 * 10).value_counts().sort_index().items():
        print(f"    {decade}s  {n:>7,}")

    print(f"\nkaupverd_nominal range (kr): "
          f"min={int(out['kaupverd_nominal'].min()):,}  "
          f"max={int(out['kaupverd_nominal'].max()):,}  "
          f"median={int(out['kaupverd_nominal'].median()):,}")

    try:
        out.to_parquet(OUT_PARQUET, index=False)
        print(f"\nWrote {OUT_PARQUET} ({OUT_PARQUET.stat().st_size:,} bytes)")
    except Exception as e:
        print(f"\nparquet write failed ({type(e).__name__}: {e}); falling back to pickle")
        out.to_pickle(OUT_PICKLE_FALLBACK)
        print(f"Wrote {OUT_PICKLE_FALLBACK} ({OUT_PICKLE_FALLBACK.stat().st_size:,} bytes)")

    print("\nSTEP 1b (sales extract) complete. NO Supabase writes performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
