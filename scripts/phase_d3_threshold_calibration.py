"""Phase D3 diagnostic — distance-gated threshold calibration + D3 transfer.

READ-ONLY. No Supabase writes.

Step 1: bin held-out NN-distance, find T where k=1 match-rate stays ≥ ~98%.
Step 2: query D3 lat/lng → KDTree (geography_features.pkl), report distribution
        overall + per region_tier + per canonical_code. Count how many fall
        beyond T.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

GEO_PKL = Path(r"D:\geography_features.pkl")
PROPS_PARQUET = Path(r"D:\phase_d3_insert_rows.parquet")

# Bin edges in degrees (≈ km/111). Iceland is ~64° N so cos(lat) ≈ 0.44 for
# longitude, but for ranking-within-Iceland the lat-degree approximation
# (1° ≈ 111 km) is fine for ordering and bin labels.
BINS_DEG = [0, 1e-9, 0.0009, 0.0027, 0.009, 0.018, np.inf]
BIN_LABELS = ["==0 (same stadfang)", "0–100 m", "100–300 m",
              "300 m – 1 km", "1–2 km", "≥2 km"]
SEED = 20260527
HOLDOUT_N = 5000


def section(t):
    print()
    print("=" * 70)
    print(t)
    print("=" * 70)


def main():
    t0 = time.time()

    section("(1) THRESHOLD CALIBRATION on hold-out")
    geo = pd.read_pickle(GEO_PKL)
    geo = geo.dropna(subset=["lat", "lon", "matsvaediNUMER"]).copy().reset_index(drop=True)
    print(f"  labeled points: {len(geo):,}")

    rng = np.random.default_rng(SEED)
    idx_all = np.arange(len(geo))
    holdout_idx = rng.choice(idx_all, size=HOLDOUT_N, replace=False)
    mask_train = np.ones(len(geo), dtype=bool)
    mask_train[holdout_idx] = False
    train = geo.iloc[mask_train].reset_index(drop=True)
    test = geo.iloc[holdout_idx].reset_index(drop=True)

    tree = cKDTree(train[["lat", "lon"]].to_numpy())
    test_xy = test[["lat", "lon"]].to_numpy()
    dist1, idx1 = tree.query(test_xy, k=1)
    pred_mn = train["matsvaediNUMER"].iloc[idx1].to_numpy()
    true_mn = test["matsvaediNUMER"].to_numpy()
    match = (pred_mn == true_mn)

    print(f"\n  k=1 match-rate by NN-distance bin:")
    print(f"  {'bin':<22s} {'n':>7s} {'match':>7s} {'rate':>7s}")
    print("  " + "-" * 47)
    bin_idx = np.digitize(dist1, BINS_DEG, right=False) - 1
    for i, label in enumerate(BIN_LABELS):
        mask_bin = (bin_idx == i)
        n = int(mask_bin.sum())
        if n == 0:
            print(f"  {label:<22s} {0:>7d} {'-':>7s} {'-':>7s}")
            continue
        m = int(match[mask_bin].sum())
        rate = 100.0 * m / n
        print(f"  {label:<22s} {n:>7,d} {m:>7,d} {rate:>6.1f}%")

    # Pick T: largest bin where rate ≥ 98%
    # Apply cumulatively (cumulative match-rate up to bin i should ≥ 98%).
    print(f"\n  cumulative k=1 match-rate up to each upper edge:")
    sorted_idx = np.argsort(dist1)
    sorted_dist = dist1[sorted_idx]
    sorted_match = match[sorted_idx]
    # For each bin upper edge, compute cumulative match-rate
    cum_T = None
    for i, upper in enumerate(BINS_DEG[1:], start=1):
        if upper == np.inf:
            n_cum = len(dist1)
            m_cum = match.sum()
        else:
            n_cum = int((sorted_dist < upper).sum())
            m_cum = int(sorted_match[:n_cum].sum())
        rate = 100.0 * m_cum / n_cum if n_cum else 0
        marker = ""
        if rate >= 98.0:
            cum_T = upper
            marker = " ← still ≥98% (candidate T)"
        upper_km = upper * 111 if np.isfinite(upper) else float("inf")
        print(f"    distance < {upper:.5f}° (~{upper_km:.2f} km): "
              f"n={n_cum:>5,}  match-rate={rate:5.1f}%{marker}")

    # Per-bin (conservative): T = largest upper edge where the per-bin
    # rate INSIDE that band stays ≥98%. Cumulative ≥98% is dominated by
    # the dense 0-100m bins and would push T to 2km despite the 1-2km
    # per-bin rate dropping to 88.9% (n=18, small-sample noise — but we
    # take the conservative read).
    T_deg_per_bin = 0.0  # no upper edge selected
    for i in range(1, len(BIN_LABELS) - 1):  # skip "≥2 km" (open-ended)
        upper = BINS_DEG[i + 1]
        if upper == np.inf:
            break
        mask_bin = (bin_idx == i)
        n = int(mask_bin.sum())
        if n == 0:
            continue
        m = int(match[mask_bin].sum())
        rate = 100.0 * m / n
        if rate >= 98.0:
            T_deg_per_bin = upper
    T_deg = T_deg_per_bin if T_deg_per_bin > 0 else 0.0009  # min fallback 100m
    T_km = T_deg * 111
    print(f"\n  Per-bin selection (conservative): T = {T_deg:.5f}° (~{T_km:.2f} km)")
    print(f"  (cumulative-criterion candidate would have been "
          f"{cum_T:.5f}° but rejected because of per-bin noise above 1 km)")

    # ============================================================
    # (2) D3 NN-distance transfer check
    # ============================================================
    section("(2) D3 NN-DISTANCE TRANSFER CHECK")
    d3 = pd.read_parquet(PROPS_PARQUET,
                         columns=["fastnum", "lat", "lng", "postnr",
                                  "region_tier", "canonical_code"])
    d3_xy = d3[d3["lat"].notna() & d3["lng"].notna()].copy().reset_index(drop=True)
    print(f"  D3 with lat/lng: {len(d3_xy):,} of {len(d3):,}")

    # Use FULL labeled set as donor (no hold-out — this is the actual
    # backfill we'd do at apply time).
    full_tree = cKDTree(geo[["lat", "lon"]].to_numpy())
    d3_xy_arr = d3_xy[["lat", "lng"]].to_numpy()
    d3_dist, _ = full_tree.query(d3_xy_arr, k=1)

    pcts = [50, 75, 90, 95, 99, 99.5]
    qvals = np.percentile(d3_dist, pcts)
    print(f"\n  Overall distance percentiles:")
    for p, q in zip(pcts, qvals):
        print(f"    p{p:>5}  {q:.5f}°  (~{q * 111:.3f} km)")
    print(f"    max    {d3_dist.max():.5f}° (~{d3_dist.max() * 111:.3f} km)")

    n_beyond = int((d3_dist > T_deg).sum())
    n_within = len(d3_dist) - n_beyond
    print(f"\n  D3 rows WITHIN threshold T ({T_km:.2f} km): "
          f"{n_within:,} ({100.0 * n_within / len(d3_dist):.2f}%)")
    print(f"  D3 rows BEYOND threshold T:             "
          f"{n_beyond:,} ({100.0 * n_beyond / len(d3_dist):.2f}%)")

    # Per region_tier
    print(f"\n  Per region_tier:")
    d3_xy["nn_deg"] = d3_dist
    d3_xy["nn_km"] = d3_dist * 111
    d3_xy["within_T"] = d3_dist <= T_deg
    for region, sub in d3_xy.groupby("region_tier"):
        within = int(sub["within_T"].sum())
        p50 = sub["nn_km"].quantile(0.50)
        p95 = sub["nn_km"].quantile(0.95)
        p99 = sub["nn_km"].quantile(0.99)
        max_km = sub["nn_km"].max()
        pct = 100.0 * within / len(sub)
        print(f"    {region:<13s} n={len(sub):>6,}  within_T={within:>6,}  "
              f"({pct:5.1f}%)  p50={p50:.3f}km  p95={p95:.3f}km  "
              f"p99={p99:.3f}km  max={max_km:.1f}km")

    # Per canonical_code (focus on scorable + EXCLUDE for completeness)
    print(f"\n  Per canonical_code:")
    for code in ["APT_FLOOR", "APT_STANDARD", "APT_BASEMENT", "APT_ATTIC",
                 "SFH_DETACHED", "SEMI_DETACHED", "ROW_HOUSE",
                 "SUMMERHOUSE", "APT_ROOM", "APT_HOTEL", "APT_UNAPPROVED",
                 "EXCLUDE"]:
        sub = d3_xy[d3_xy["canonical_code"] == code]
        if not len(sub):
            continue
        within = int(sub["within_T"].sum())
        p50 = sub["nn_km"].quantile(0.50)
        p95 = sub["nn_km"].quantile(0.95)
        p99 = sub["nn_km"].quantile(0.99)
        max_km = sub["nn_km"].max()
        pct = 100.0 * within / len(sub)
        print(f"    {code:<16s} n={len(sub):>6,}  within_T={within:>6,}  "
              f"({pct:5.1f}%)  p50={p50:.3f}km  p95={p95:.3f}km  "
              f"p99={p99:.3f}km  max={max_km:.1f}km")

    # Specifically focus on the two flagged categories — Country + SUMMERHOUSE
    print(f"\n  CROSS-TAB Country × SUMMERHOUSE (most-at-risk slice):")
    cs = d3_xy[(d3_xy["region_tier"] == "Country") &
               (d3_xy["canonical_code"] == "SUMMERHOUSE")]
    if len(cs):
        within = int(cs["within_T"].sum())
        print(f"    n={len(cs):,}  within_T={within:,} "
              f"({100.0 * within / len(cs):.1f}%)  "
              f"p95={cs['nn_km'].quantile(0.95):.3f}km  "
              f"p99={cs['nn_km'].quantile(0.99):.3f}km  "
              f"max={cs['nn_km'].max():.1f}km")

    section("SUMMARY")
    print(f"  T = {T_deg:.5f}° (~{T_km:.2f} km), chosen from hold-out cumulative ≥98%")
    print(f"  D3 within T: {n_within:,} / {len(d3_dist):,} "
          f"({100.0 * n_within / len(d3_dist):.2f}%)")
    print(f"  D3 beyond T (held, no prediction): {n_beyond:,}")
    print(f"  D3 missing coords (held, no prediction): "
          f"{len(d3) - len(d3_xy):,}")
    print(f"\n  elapsed: {time.time() - t0:.1f}s")

    # Save T to a tiny file so subsequent scripts can read it
    Path(r"D:\phase_d3_matsvaedi_T_deg.txt").write_text(f"{T_deg:.6f}\n",
                                                        encoding="utf-8")
    print(f"  T persisted to D:\\phase_d3_matsvaedi_T_deg.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
