"""Phase D3 diagnostic — can matsvaediNUMER be backfilled for the 108K
D3 candidates WITHOUT the evalue augl-pass? READ-ONLY.

Steps:
  (1) PROVENANCE summary (printed)
  (2) DIRECT-LOOKUP: scan Gagnapakkar/fasteignir{,1-4}.db data_json for
      any D3 fastnum, report fraction covered.
  (3) SPATIAL-NN HOLD-OUT: from geography_features.pkl (labeled), blank
      5K random points, re-assign via k-NN (k=1, k=5 majority) on
      (lat, lng). Report matsvaediNUMER + matsvaedi_bucket match rates.
  (4) HONESTY RE-CHECK: 3000-sample, assign matsvaedi spatially from
      hold-out neighbors, re-score iter4 + conformal, recompute breach.
  (5) D3 ASSIGNABILITY count.

Prints summary. No writes.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
sys.path.insert(0, r"D:\\")

GEO_PKL = Path(r"D:\geography_features.pkl")
TRAINING_PKL = Path(r"D:\training_data_v2.pkl")
PROPS_PARQUET = Path(r"D:\phase_d3_insert_rows.parquet")
CALIB_JSON = Path(r"D:\iter4_calibration_config.json")
CONFORMAL_JSON = Path(r"D:\iter4_conformal_corrections.json")
MODEL_DIR = Path(r"D:\\")
SCRAPE_DBS = [Path(r"D:\Gagnapakkar") / f"fasteignir{i}.db"
              for i in ("", "1", "2", "3", "4")]

VALUATION_YEAR = 2026
VALUATION_MONTH = 4
CATEGORICALS = ["canonical_code", "matsvaedi_bucket", "region_tier", "unit_category"]
SEED = 20260527
HOLDOUT_N = 5000
SAMPLE_N = 3000

RESIDENTIAL_CODES = {
    "APT_FLOOR", "APT_STANDARD", "APT_BASEMENT", "APT_ATTIC",
    "SFH_DETACHED", "SEMI_DETACHED", "ROW_HOUSE",
    "APT_ROOM", "APT_HOTEL", "APT_MIXED", "APT_UNAPPROVED", "APT_SENIOR",
}
SCORABLE = RESIDENTIAL_CODES | {"SUMMERHOUSE"}
MATSVAEDI_MIN_SALES_2015 = 50  # matches geography.py default


def section(t: str):
    print()
    print("=" * 70)
    print(t)
    print("=" * 70)


# ----- iter4 scoring helpers (mirror phase_d3_score_extract.py) -----
def load_models():
    out: dict = {}
    for grp in ("main", "summer"):
        for suffix in ("mean", "q500"):
            path = MODEL_DIR / f"iter4a_{grp}_{suffix}.lgb"
            out[f"{grp}_{suffix}"] = lgb.Booster(model_file=str(path))
    with open(CONFORMAL_JSON, "r", encoding="utf-8") as f:
        out["conformal"] = json.load(f)
    out["feature_names"] = out["main_mean"].feature_name()
    td = pd.read_pickle(TRAINING_PKL)
    out["categorical_mappings"] = {}
    for cat in CATEGORICALS:
        if cat in td.columns and hasattr(td[cat], "cat"):
            out["categorical_mappings"][cat] = list(td[cat].cat.categories)
    return out


def conformal_q(canon, region, conformal):
    sr = conformal.get("by_segment_region", {})
    e = sr.get(f"{canon}|{region}")
    if e:
        return e["q80_log"], e["q95_log"]
    seg = conformal.get("by_segment", {})
    e = seg.get(canon)
    if e:
        return e["q80_log"], e["q95_log"]
    g = conformal["global"]
    return g["q80_log"], g["q95_log"]


def build_X(rows: pd.DataFrame, feat_names, cat_map, *,
            override_matsvaedi: np.ndarray | None = None,
            override_bucket: np.ndarray | None = None) -> pd.DataFrame:
    """If override_matsvaedi / override_bucket are provided, use them
    instead of rows' columns (in iter4 feature names)."""
    N = len(rows)
    X = pd.DataFrame({n: pd.array([np.nan] * N, dtype="float64") for n in feat_names})

    src_map = {
        "FASTNUM": "FASTNUM",
        "EINFLM": "EINFLM",
        "BYGGAR": "BYGGAR",
        "LOD_FLM": "LOD_FLM",
        "matsvaediNUMER": "matsvaediNUMER",
        "postnr": "postnr",
        "landnum": "landnum",
        "lat": "lat",
        "lon": "lon",
    }
    for feat_col, src_col in src_map.items():
        if feat_col not in feat_names or src_col not in rows.columns:
            continue
        if feat_col == "matsvaediNUMER" and override_matsvaedi is not None:
            X[feat_col] = pd.to_numeric(override_matsvaedi, errors="coerce").astype("float64")
            continue
        X[feat_col] = pd.to_numeric(rows[src_col], errors="coerce").to_numpy(dtype="float64")

    if "LOD_FLM" in feat_names and "LOD_FLM" in rows.columns:
        X["LOD_FLM"] = pd.to_numeric(rows["LOD_FLM"], errors="coerce").fillna(0.0).to_numpy()
    if "sale_year" in feat_names:
        X["sale_year"] = float(VALUATION_YEAR)
    if "sale_month" in feat_names:
        X["sale_month"] = float(VALUATION_MONTH)
    if "age_at_sale" in feat_names:
        X["age_at_sale"] = float(VALUATION_YEAR) - pd.to_numeric(
            rows["BYGGAR"], errors="coerce").to_numpy()
    if "has_extraction_data" in feat_names:
        X["has_extraction_data"] = 0

    for cat in CATEGORICALS:
        if cat not in feat_names:
            continue
        if cat == "matsvaedi_bucket" and override_bucket is not None:
            vals = override_bucket
        elif cat in rows.columns:
            vals = rows[cat].astype(object).to_numpy()
        else:
            vals = [None] * N
        if cat in cat_map:
            X[cat] = pd.Categorical(vals, categories=cat_map[cat])
        else:
            X[cat] = vals

    for b in ("is_main_unit", "is_new_build"):
        if b in feat_names and b in rows.columns:
            X[b] = rows[b].astype(bool).to_numpy()

    return X


def score_mean_only(rows: pd.DataFrame, models: dict, **override) -> np.ndarray:
    """Return predicted mean (log-space) for each row."""
    feat_names = models["feature_names"]
    cat_map = models["categorical_mappings"]
    X = build_X(rows, feat_names, cat_map, **override)
    is_summer = rows["canonical_code"].astype(str).eq("SUMMERHOUSE").to_numpy()
    N = len(rows)
    out = np.empty(N, dtype=np.float64)
    for group, mask in (("main", ~is_summer), ("summer", is_summer)):
        if mask.sum() == 0:
            continue
        Xg = X.loc[mask].reset_index(drop=True)
        m = models[f"{group}_mean"]
        out[mask] = m.predict(Xg, num_iteration=m.best_iteration)
    return out


# ----- matsvaedi_bucket rebuild logic (mirrors geography.py) -----
def compute_bucket(matsvaedi_numer, postnr, sales_2015,
                   min_sales=MATSVAEDI_MIN_SALES_2015):
    """Return matsvaedi_bucket string per geography.build_matsvaedi_bucket."""
    if matsvaedi_numer is None or pd.isna(matsvaedi_numer):
        if postnr is not None and not pd.isna(postnr):
            return f"P{int(postnr)}_other"
        return "unknown"
    m = int(matsvaedi_numer)
    if sales_2015.get(m, 0) >= min_sales:
        return f"M{m}"
    if postnr is not None and not pd.isna(postnr):
        return f"P{int(postnr)}_other"
    return "unknown"


def main() -> int:
    t0 = time.time()

    # ==========================================================
    # (1) PROVENANCE
    # ==========================================================
    section("(1) PROVENANCE")
    print("""
  Per geography.py + parse_all_dbs.py inspection (read-only this session):
    geography.build_geography_features(properties, kaupskra) takes
      `properties` (= properties_v2.pkl) as the SOURCE of matsvaediNUMER.
      It does NOT compute matsvæði from coordinates — it passes through
      properties_v2['matsvaediNUMER'] verbatim, then assembles the
      rare-merge bucket from those values + sales counts.

    properties_v2.pkl was produced by parse_all_dbs.py from
      D:\\Gagnapakkar\\fasteignir{,1-4}.db, parsing each row's
      `data_json` (devalue-encoded augl.is/evalue.is payload).
      matsvaediNUMER lives inside that payload.

    Mechanism = (iii) pulled from evalue augl payloads.
    No fastnum-keyed registry file exists on D:\\ (no matsv*.csv,
    no shapefile/gpkg, no HMS matsvæði polygons locally).
""")

    # ==========================================================
    # (2) DIRECT-LOOKUP — scan scrape DBs for D3 fastnums
    # ==========================================================
    section("(2) DIRECT-LOOKUP — scrape DB coverage of D3 fastnums")
    d3 = pd.read_parquet(PROPS_PARQUET, columns=["fastnum", "lat", "lng", "postnr"])
    d3_fns = set(int(x) for x in d3["fastnum"].tolist())
    print(f"  D3 candidate fastnums: {len(d3_fns):,}")

    fns_in_scrape: set[int] = set()
    fns_with_matsvaedi: set[int] = set()
    for db_path in SCRAPE_DBS:
        if not db_path.exists():
            print(f"  skip (missing): {db_path}")
            continue
        c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
        c.execute("PRAGMA query_only=ON")
        # Just enumerate fastnums first
        local = set()
        for (fn,) in c.execute("SELECT fastnum FROM fasteignir"):
            try:
                local.add(int(fn))
            except (TypeError, ValueError):
                pass
        c.close()
        overlap = local & d3_fns
        print(f"  {db_path.name:<18s} {len(local):>7,} fastnums, "
              f"overlap with D3 = {len(overlap):,}")
        fns_in_scrape |= overlap

    print(f"\n  TOTAL scrape-coverage of D3: {len(fns_in_scrape):,} / {len(d3_fns):,} "
          f"({100.0 * len(fns_in_scrape) / len(d3_fns):.2f}%)")

    # If overlap >0, peek into data_json for one to confirm matsvaediNUMER presence
    if fns_in_scrape:
        sample_fn = next(iter(fns_in_scrape))
        for db_path in SCRAPE_DBS:
            if not db_path.exists():
                continue
            c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
            r = c.execute(
                "SELECT data_json FROM fasteignir WHERE fastnum=? LIMIT 1",
                (str(sample_fn),)
            ).fetchone()
            c.close()
            if r and r[0]:
                print(f"  sample data_json (fn={sample_fn}, db={db_path.name}): "
                      f"{r[0][:200]} ...")
                break

    # ==========================================================
    # (3) SPATIAL-NN HOLD-OUT on labeled geography_features.pkl
    # ==========================================================
    section("(3) SPATIAL-NN HOLD-OUT — k-NN from labeled (lat, lon)")
    geo = pd.read_pickle(GEO_PKL)
    geo = geo.dropna(subset=["lat", "lon", "matsvaediNUMER"]).copy()
    print(f"  labeled points: {len(geo):,}")

    # sales_2015 for bucket recompute
    sales_2015 = geo.groupby("matsvaediNUMER")["matsvaedi_sales_2015"].first().to_dict()

    rng = np.random.default_rng(SEED)
    idx_all = np.arange(len(geo))
    holdout_idx = rng.choice(idx_all, size=HOLDOUT_N, replace=False)
    mask_train = np.ones(len(geo), dtype=bool)
    mask_train[holdout_idx] = False
    train = geo.iloc[mask_train].reset_index(drop=True)
    test = geo.iloc[holdout_idx].reset_index(drop=True)

    # KD-tree on (lat, lon) — degrees fine for ranking within Iceland bbox
    tree = cKDTree(train[["lat", "lon"]].to_numpy())
    test_xy = test[["lat", "lon"]].to_numpy()

    # k=1
    dist1, idx1 = tree.query(test_xy, k=1)
    pred1_mn = train["matsvaediNUMER"].iloc[idx1].to_numpy()
    true_mn = test["matsvaediNUMER"].to_numpy()
    match1 = (pred1_mn == true_mn)
    print(f"  k=1   exact matsvaediNUMER match: "
          f"{int(match1.sum()):>6,} / {len(test):,}  "
          f"({100.0 * match1.mean():.1f}%)")

    # k=5 majority
    dist5, idx5 = tree.query(test_xy, k=5)
    pred5_mn = np.empty(len(test), dtype=np.float64)
    for i in range(len(test)):
        vals = train["matsvaediNUMER"].iloc[idx5[i]].to_numpy()
        # Mode (with tie-break by min distance — already sorted)
        uniq, cnt = np.unique(vals, return_counts=True)
        pred5_mn[i] = uniq[np.argmax(cnt)]
    match5 = (pred5_mn == true_mn)
    print(f"  k=5   majority matsvaediNUMER match: "
          f"{int(match5.sum()):>6,} / {len(test):,}  "
          f"({100.0 * match5.mean():.1f}%)")

    # matsvaedi_bucket match
    test_bucket_true = test["matsvaedi_bucket"].to_numpy()
    test_pn = test["postnr"].to_numpy()

    bucket1 = np.array([compute_bucket(pred1_mn[i], test_pn[i], sales_2015)
                        for i in range(len(test))])
    bucket5 = np.array([compute_bucket(pred5_mn[i], test_pn[i], sales_2015)
                        for i in range(len(test))])
    print(f"  k=1   matsvaedi_bucket match: "
          f"{int((bucket1 == test_bucket_true).sum()):>6,} / {len(test):,}  "
          f"({100.0 * (bucket1 == test_bucket_true).mean():.1f}%)")
    print(f"  k=5   matsvaedi_bucket match: "
          f"{int((bucket5 == test_bucket_true).sum()):>6,} / {len(test):,}  "
          f"({100.0 * (bucket5 == test_bucket_true).mean():.1f}%)")

    # Distance distribution
    print(f"\n  nearest-neighbor distance distribution (degrees ≈ km/111):")
    pcts = [50, 75, 90, 95, 99]
    qvals = np.percentile(dist1, pcts)
    for p, q in zip(pcts, qvals):
        print(f"    p{p:>2d}  {q:.5f}°  (~{q * 111:.1f} km)")

    # Region-stratified accuracy
    print(f"\n  per region_tier (k=1):")
    by_region = pd.DataFrame({
        "region": test["region_tier"].to_numpy(),
        "ok_mn": match1,
        "ok_bucket": (bucket1 == test_bucket_true),
    })
    for region, sub in by_region.groupby("region"):
        print(f"    {region:<13s} n={len(sub):>5,}  "
              f"matsvaediNUMER ok={sub['ok_mn'].mean() * 100:5.1f}%  "
              f"bucket ok={sub['ok_bucket'].mean() * 100:5.1f}%")

    # ==========================================================
    # (4) HONESTY RE-CHECK — same 3000-sample, spatially inferred matsvaedi
    # ==========================================================
    section("(4) HONESTY RE-CHECK — score with spatially-inferred matsvaedi")
    print("  Loading iter4a + conformal ...")
    models = load_models()
    td = pd.read_pickle(TRAINING_PKL)
    pool = td[
        td["canonical_code"].astype(str).isin(SCORABLE)
        & td["BYGGAR"].notna()
        & td["matsvaediNUMER"].notna()
        & td["matsvaedi_bucket"].notna()
        & td["postnr"].notna()
        & td["lat"].notna() & td["lon"].notna()
    ].copy()
    sample = pool.sample(n=min(SAMPLE_N, len(pool)),
                         random_state=SEED).reset_index(drop=True)
    print(f"  sample: {len(sample):,} rows (full-feature, residential+summer)")

    # Hold-out: re-build the KD-tree on geography_features EXCLUDING these
    # sample rows (by fastnum), so each row's inferred matsvaedi comes from
    # genuinely external neighbors.
    sample_fns = set(int(x) for x in sample["FASTNUM"].tolist())
    geo_train = geo[~geo["fastnum"].astype(int).isin(sample_fns)].reset_index(drop=True)
    tree2 = cKDTree(geo_train[["lat", "lon"]].to_numpy())
    sample_xy = sample[["lat", "lon"]].to_numpy()

    # k=1 inferred matsvaediNUMER for the sample
    _, idx_s = tree2.query(sample_xy, k=1)
    inferred_mn = geo_train["matsvaediNUMER"].iloc[idx_s].to_numpy()
    inferred_bucket = np.array([
        compute_bucket(inferred_mn[i], sample["postnr"].iloc[i], sales_2015)
        for i in range(len(sample))
    ])

    print("  scoring (A) — full true features ...")
    A_mn = score_mean_only(sample, models)
    print("  scoring (B_inferred) — matsvaedi from k=1 spatial NN ...")
    B_mn = score_mean_only(sample, models,
                           override_matsvaedi=inferred_mn,
                           override_bucket=inferred_bucket)
    delta = B_mn - A_mn

    # Half-width breach via conformal
    segs = sample["canonical_code"].astype(str).to_numpy()
    regs = sample["region_tier"].astype(str).to_numpy()
    q80 = np.empty(len(sample), dtype=np.float64)
    q95 = np.empty(len(sample), dtype=np.float64)
    for i in range(len(sample)):
        q80[i], q95[i] = conformal_q(segs[i], regs[i], models["conformal"])
    breach_q80 = (np.abs(delta) > q80).mean() * 100
    breach_q95 = (np.abs(delta) > q95).mean() * 100

    print(f"\n  delta = pred_mean_log(spatial-inferred) − pred_mean_log(true):")
    pcts = [5, 25, 50, 75, 95]
    qvals = np.percentile(delta, pcts)
    print(f"    mean   {delta.mean():+.4f}   (% ≈ {(np.expm1(delta.mean()) * 100):+.2f}%)")
    print(f"    median {np.median(delta):+.4f}   (% ≈ {(np.expm1(np.median(delta)) * 100):+.2f}%)")
    print(f"    std    {delta.std():.4f}")
    for p, q in zip(pcts, qvals):
        print(f"    p{p:>2d}  {q:+.4f}  (% ≈ {(np.expm1(q) * 100):+.2f}%)")

    print(f"\n  half-width breach (compare against blank baseline 51.2% / 22.0%):")
    print(f"    |delta| > q80_log half-width: {breach_q80:5.2f}%")
    print(f"    |delta| > q95_log half-width: {breach_q95:5.2f}%")

    # Per-region breach
    df_b = pd.DataFrame({
        "region": regs,
        "delta": delta,
        "abs_delta": np.abs(delta),
        "br80": np.abs(delta) > q80,
        "br95": np.abs(delta) > q95,
    })
    print(f"\n  per region_tier:")
    for region, sub in df_b.groupby("region"):
        print(f"    {region:<13s} n={len(sub):>5,}  "
              f"mean log={sub['delta'].mean():+.4f}  "
              f"std={sub['delta'].std():.4f}  "
              f"br80={sub['br80'].mean() * 100:5.1f}%  "
              f"br95={sub['br95'].mean() * 100:5.1f}%")

    # ==========================================================
    # (5) D3 ASSIGNABILITY
    # ==========================================================
    section("(5) D3 ASSIGNABILITY")
    n_total = len(d3)
    n_with_xy = int((d3["lat"].notna() & d3["lng"].notna()).sum())
    n_no_xy = n_total - n_with_xy
    print(f"  D3 candidates total:        {n_total:>7,}")
    print(f"  with lat/lng (assignable):  {n_with_xy:>7,}  "
          f"({100.0 * n_with_xy / n_total:.2f}%)")
    print(f"  no lat/lng (residual):      {n_no_xy:>7,}  "
          f"({100.0 * n_no_xy / n_total:.2f}%)")

    # ==========================================================
    # SUMMARY
    # ==========================================================
    section("SUMMARY")
    print(f"  (1) provenance:           pulled from evalue augl payloads (iii)")
    print(f"  (2) scrape-DB direct hit: "
          f"{len(fns_in_scrape):,} / {len(d3_fns):,} "
          f"({100.0 * len(fns_in_scrape) / len(d3_fns):.2f}%)")
    print(f"  (3) spatial k=1 mn match: {100.0 * match1.mean():.1f}%   "
          f"k=5 majority: {100.0 * match5.mean():.1f}%")
    print(f"  (3) spatial k=1 bucket:   {100.0 * (bucket1 == test_bucket_true).mean():.1f}%   "
          f"k=5 bucket: {100.0 * (bucket5 == test_bucket_true).mean():.1f}%")
    print(f"  (4) breach under inferred matsvaedi: "
          f"q80 {breach_q80:.1f}% / q95 {breach_q95:.1f}%   "
          f"(was 51.2% / 22.0% under blank)")
    print(f"  (5) D3 assignability:     {n_with_xy:,} of {n_total:,} have coords")
    print(f"\n  elapsed: {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
