"""Phase D3 diagnostic — quantify iter4 degradation when matsvaediNUMER is missing.

READ-ONLY. No Supabase writes. Prints summary + spot-checks, then exits.

Procedure:
  (1) Sample N=3000 residential+summer rows from training_data_v2.pkl that
      have byggar + a real matsvaediNUMER + matsvaedi_bucket (full-feature
      condition the model trained on).
  (2) Score each row TWICE with the exact phase_d3_score_extract.py scorer:
      (A) full features
      (B) matsvaediNUMER blanked, matsvaedi_bucket → 'P{postnr}_other'
          (mimics the D3 net-new condition).
  (3) Report delta = pred_mean_log(B) - pred_mean_log(A).
  (4) Spot-check 10 D3 net-new residential preds against kaupskrá peer
      median (same postnr × canonical_code × EINFLM ±15%).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

sys.path.insert(0, r"D:\\")
from classify_property import classify_property  # noqa: E402

TRAINING_PKL = Path(r"D:\training_data_v2.pkl")
KAUPSKRA_CSV = Path(r"D:\kaupskra.csv")
CALIB_JSON = Path(r"D:\iter4_calibration_config.json")
CONFORMAL_JSON = Path(r"D:\iter4_conformal_corrections.json")
INSERT_PARQUET = Path(r"D:\phase_d3_insert_rows.parquet")
PREDS_PARQUET = Path(r"D:\phase_d3_predictions.parquet")
MODEL_DIR = Path(r"D:\\")

VALUATION_YEAR = 2026
VALUATION_MONTH = 4
CATEGORICALS = ["canonical_code", "matsvaedi_bucket", "region_tier", "unit_category"]
N_SAMPLE = 3000
SEED = 20260527

RESIDENTIAL_CODES = {
    "APT_FLOOR", "APT_STANDARD", "APT_BASEMENT", "APT_ATTIC",
    "SFH_DETACHED", "SEMI_DETACHED", "ROW_HOUSE",
    "APT_ROOM", "APT_HOTEL", "APT_MIXED", "APT_UNAPPROVED", "APT_SENIOR",
}
SCORABLE = RESIDENTIAL_CODES | {"SUMMERHOUSE"}


def load_models():
    out: dict = {}
    for grp in ("main", "summer"):
        for suffix in ("mean", "q500"):
            path = MODEL_DIR / f"iter4a_{grp}_{suffix}.lgb"
            out[f"{grp}_{suffix}"] = lgb.Booster(model_file=str(path))
    with open(CALIB_JSON, "r", encoding="utf-8") as f:
        out["segcal"] = json.load(f)
    with open(CONFORMAL_JSON, "r", encoding="utf-8") as f:
        out["conformal"] = json.load(f)
    out["feature_names"] = out["main_mean"].feature_name()

    td = pd.read_pickle(TRAINING_PKL)
    out["categorical_mappings"] = {}
    for cat in CATEGORICALS:
        if cat in td.columns and hasattr(td[cat], "cat"):
            out["categorical_mappings"][cat] = list(td[cat].cat.categories)
    td["_yr"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.year
    td["_mn"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.month
    cpi_lookup = td.groupby(["_yr", "_mn"])["cpi_factor"].first().to_dict()
    out["cpi_factor"] = cpi_lookup.get(
        (VALUATION_YEAR, VALUATION_MONTH),
        cpi_lookup[max(cpi_lookup.keys())],
    )
    out["_td"] = td
    return out


def conformal_q(canon: str, region: str, conformal: dict) -> tuple[float, float]:
    key = f"{canon}|{region}"
    sr = conformal.get("by_segment_region", {})
    if key in sr:
        e = sr[key]
        return e["q80_log"], e["q95_log"]
    seg = conformal.get("by_segment", {})
    if canon in seg:
        e = seg[canon]
        return e["q80_log"], e["q95_log"]
    g = conformal["global"]
    return g["q80_log"], g["q95_log"]


def build_X(rows: pd.DataFrame, feat_names, cat_map, *, blank_matsvaedi: bool) -> pd.DataFrame:
    """Construct feature matrix. If blank_matsvaedi: matsvaediNUMER → NaN,
    matsvaedi_bucket → 'P{postnr}_other' (rare-merge fallback)."""
    N = len(rows)
    X = pd.DataFrame({n: pd.array([np.nan] * N, dtype="float64") for n in feat_names})

    # Numeric features from training_data column names
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
        if blank_matsvaedi and feat_col == "matsvaediNUMER":
            X[feat_col] = np.nan
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
        if blank_matsvaedi and cat == "matsvaedi_bucket":
            # Fallback per D3 convention: 'P{postnr}_other'
            pn = pd.to_numeric(rows["postnr"], errors="coerce")
            vals = [f"P{int(p)}_other" if pd.notna(p) else "unknown" for p in pn]
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


def score(rows: pd.DataFrame, models: dict, *, blank_matsvaedi: bool):
    """Return (mean_log, median_log, segment, q80_log, q95_log) arrays."""
    feat_names = models["feature_names"]
    cat_map = models["categorical_mappings"]
    conformal = models["conformal"]

    X = build_X(rows, feat_names, cat_map, blank_matsvaedi=blank_matsvaedi)
    is_summer = rows["canonical_code"].astype(str).eq("SUMMERHOUSE").to_numpy()
    N = len(rows)

    mean_log = np.empty(N, dtype=np.float64)
    median_log = np.empty(N, dtype=np.float64)
    q80 = np.empty(N, dtype=np.float64)
    q95 = np.empty(N, dtype=np.float64)
    segs = rows["canonical_code"].astype(str).to_numpy()
    regs = rows["region_tier"].astype(str).to_numpy()

    for group, mask in (("main", ~is_summer), ("summer", is_summer)):
        if mask.sum() == 0:
            continue
        Xg = X.loc[mask].reset_index(drop=True)
        m_mean = models[f"{group}_mean"]
        m_med = models[f"{group}_q500"]
        mean_log[mask] = m_mean.predict(Xg, num_iteration=m_mean.best_iteration)
        median_log[mask] = m_med.predict(Xg, num_iteration=m_med.best_iteration)

    for i in range(N):
        q80[i], q95[i] = conformal_q(segs[i], regs[i], conformal)

    return mean_log, median_log, segs, regs, q80, q95


def section(title: str):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main() -> int:
    t0 = time.time()
    section("Loading models + training data")
    models = load_models()
    td = models["_td"]
    print(f"  iter4a features: {len(models['feature_names'])}")
    print(f"  training rows:   {len(td):,}")
    print(f"  cpi_factor @ {VALUATION_YEAR}-{VALUATION_MONTH:02d}: "
          f"{models['cpi_factor']:.4f}")

    # ==========================================================
    # (1) Sample full-feature rows
    # ==========================================================
    section(f"(1) Sample N={N_SAMPLE:,} full-feature residential+summer rows")
    pool = td[
        td["canonical_code"].astype(str).isin(SCORABLE)
        & td["BYGGAR"].notna()
        & td["matsvaediNUMER"].notna()
        & td["matsvaedi_bucket"].notna()
        & td["postnr"].notna()
    ].copy()
    print(f"  eligible pool: {len(pool):,} rows")
    sample = pool.sample(n=min(N_SAMPLE, len(pool)), random_state=SEED).reset_index(drop=True)
    print(f"  sampled: {len(sample):,} rows")

    # ==========================================================
    # (2) Score TWICE: (A) full features  (B) blanked matsvaedi
    # ==========================================================
    section("(2) Scoring twice (full vs matsvaedi-blanked)")
    print("  scoring (A) — full features ...")
    A_mean, A_med, segs, regs, q80, q95 = score(sample, models, blank_matsvaedi=False)
    print("  scoring (B) — matsvaediNUMER=NaN, bucket=P{postnr}_other ...")
    B_mean, B_med, _, _, _, _ = score(sample, models, blank_matsvaedi=True)

    delta = B_mean - A_mean
    pct = (np.expm1(delta)) * 100.0

    # ==========================================================
    # (2b) Fallback-bucket category resolution check
    # ==========================================================
    section("(2b) Fallback bucket resolution check")
    cat_map = models["categorical_mappings"]
    training_buckets = set(cat_map.get("matsvaedi_bucket", []))
    pn = pd.to_numeric(sample["postnr"], errors="coerce")
    fb_buckets = [f"P{int(p)}_other" if pd.notna(p) else "unknown" for p in pn]
    resolved = sum(1 for b in fb_buckets if b in training_buckets)
    print(f"  fallback bucket ∈ training categories: "
          f"{resolved:,}/{len(fb_buckets):,}  "
          f"({100.0 * resolved / len(fb_buckets):.1f}%)")
    print(f"  fallback bucket NaN (not in training):  "
          f"{len(fb_buckets) - resolved:,}  "
          f"(LightGBM categorical NaN; uses missing-branch in tree)")

    # ==========================================================
    # (3) Delta distribution
    # ==========================================================
    section("(3) Delta distribution: pred_mean_log(B) − pred_mean_log(A)")
    pcts = [5, 25, 50, 75, 95]
    qvals = np.percentile(delta, pcts)
    print(f"  mean delta_log   = {delta.mean():+.4f}  (% ≈ {(np.expm1(delta.mean()) * 100):+.2f}%)")
    print(f"  median delta_log = {np.median(delta):+.4f}  (% ≈ {(np.expm1(np.median(delta)) * 100):+.2f}%)")
    print(f"  std delta_log    = {delta.std():.4f}")
    print(f"  percentiles (log):")
    for p, q in zip(pcts, qvals):
        print(f"    p{p:>2d}   {q:+.4f}  (% ≈ {(np.expm1(q) * 100):+.2f}%)")

    # ==========================================================
    # (3b) Coverage breach — when does |delta| exceed conformal width?
    # ==========================================================
    section("(3b) % of rows where |delta| breaches conformal half-width")
    breach_q80 = (np.abs(delta) > q80).mean() * 100
    breach_q95 = (np.abs(delta) > q95).mean() * 100
    print(f"  |delta| > q80_log half-width: {breach_q80:5.2f}%  "
          f"({(np.abs(delta) > q80).sum():,}/{len(delta):,} rows)")
    print(f"  |delta| > q95_log half-width: {breach_q95:5.2f}%  "
          f"({(np.abs(delta) > q95).sum():,}/{len(delta):,} rows)")
    print(f"  NOTE: 'breach' means the matsvaedi-induced shift alone exceeds")
    print(f"        the entire PI half-width — i.e. the published PI would")
    print(f"        no longer cover the full-feature prediction.")

    # ==========================================================
    # (3c) Breakdown by canonical_code
    # ==========================================================
    section("(3c) Breakdown by canonical_code")
    df_break = pd.DataFrame({
        "canonical_code": segs,
        "delta": delta,
        "pct": pct,
        "abs_delta": np.abs(delta),
        "breach_q80": np.abs(delta) > q80,
        "breach_q95": np.abs(delta) > q95,
    })
    by_seg = df_break.groupby("canonical_code").agg(
        n=("delta", "size"),
        mean_log=("delta", "mean"),
        median_log=("delta", "median"),
        std_log=("delta", "std"),
        mean_pct=("pct", "mean"),
        breach_q80_pct=("breach_q80", lambda s: s.mean() * 100),
        breach_q95_pct=("breach_q95", lambda s: s.mean() * 100),
    ).sort_values("n", ascending=False)
    print(by_seg.to_string(float_format=lambda x: f"{x:+.3f}"))

    # ==========================================================
    # (3d) Breakdown by region_tier
    # ==========================================================
    section("(3d) Breakdown by region_tier")
    df_break["region_tier"] = regs
    by_reg = df_break.groupby("region_tier").agg(
        n=("delta", "size"),
        mean_log=("delta", "mean"),
        median_log=("delta", "median"),
        std_log=("delta", "std"),
        mean_pct=("pct", "mean"),
        breach_q80_pct=("breach_q80", lambda s: s.mean() * 100),
        breach_q95_pct=("breach_q95", lambda s: s.mean() * 100),
    ).sort_values("n", ascending=False)
    print(by_reg.to_string(float_format=lambda x: f"{x:+.3f}"))

    # ==========================================================
    # (4) Spot-check 10 D3 net-new vs kaupskrá peer median
    # ==========================================================
    section("(4) Spot-check 10 D3 net-new preds vs kaupskrá peer median")
    print(f"  Loading D3 predictions + properties + kaupskrá ...")
    d3_p = pd.read_parquet(PREDS_PARQUET)
    d3_props = pd.read_parquet(INSERT_PARQUET)
    kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
    kp["FASTNUM"] = pd.to_numeric(kp["FASTNUM"], errors="coerce").astype("Int64")
    kp["KAUPVERD"] = pd.to_numeric(kp["KAUPVERD"], errors="coerce")
    kp["EINFLM"] = pd.to_numeric(kp["EINFLM"], errors="coerce")
    kp["POSTNR"] = pd.to_numeric(kp["POSTNR"], errors="coerce")
    kp["ONOTHAEFUR_SAMNINGUR"] = pd.to_numeric(
        kp["ONOTHAEFUR_SAMNINGUR"], errors="coerce").fillna(0)
    kp["yr"] = pd.to_datetime(kp["THINGLYSTDAGS"], errors="coerce", format="ISO8601").dt.year
    # Restrict comparison universe to recent arm's-length sales
    kp_arm = kp[(kp["ONOTHAEFUR_SAMNINGUR"] == 0) & (kp["yr"] >= 2020)
                & kp["KAUPVERD"].notna() & kp["EINFLM"].notna()
                & kp["POSTNR"].notna()]
    # Join canonical_code from properties_v2 for the peer-pool
    prop_v2 = pd.read_pickle(r"D:\properties_v2.pkl")
    prop_v2["fastnum"] = pd.to_numeric(prop_v2["fastnum"], errors="coerce").astype("Int64")
    cc_map = prop_v2.set_index("fastnum")["tegund"].apply(
        lambda t: classify_property(t)[0] if t is not None else "EXCLUDE"
    )
    kp_arm = kp_arm.merge(
        cc_map.rename("canonical_code"),
        left_on="FASTNUM", right_index=True, how="left"
    )

    # Pick 10 residential D3 preds
    rng = np.random.default_rng(SEED)
    pool_d3 = d3_p.merge(
        d3_props[["fastnum", "postnr", "canonical_code", "einflm", "heimilisfang"]],
        on="fastnum", how="left", suffixes=("", "_p")
    )
    # Need real postnr + einflm + residential
    pool_d3 = pool_d3[pool_d3["canonical_code"].isin(RESIDENTIAL_CODES)
                      & pool_d3["postnr"].notna()
                      & pool_d3["einflm"].notna()]
    pick = pool_d3.sample(n=10, random_state=SEED).reset_index(drop=True)

    print(f"\n  {'fastnum':<10s} {'pcc':<14s} {'pnr':>4s} {'einflm':>7s}  "
          f"{'pred_mean (M kr)':>17s}  {'peer_n':>6s}  {'peer_med (M kr)':>17s}  ratio")
    print("  " + "-" * 100)
    rows_out = []
    for _, r in pick.iterrows():
        pn = int(r["postnr"])
        cc = r["canonical_code"]
        ef = float(r["einflm"])
        lo, hi = ef * 0.85, ef * 1.15
        peers = kp_arm[(kp_arm["POSTNR"] == pn) & (kp_arm["canonical_code"] == cc)
                       & (kp_arm["EINFLM"] >= lo) & (kp_arm["EINFLM"] <= hi)]
        peer_n = len(peers)
        peer_med_real = (peers["KAUPVERD"] * 1000).median() if peer_n > 0 else np.nan
        ratio = r["real_pred_mean"] / peer_med_real if peer_n > 0 else np.nan
        print(f"  {int(r['fastnum']):<10d} {cc:<14s} {pn:>4d} {ef:>7.1f}  "
              f"{r['real_pred_mean'] / 1e6:>15.1f}    "
              f"{peer_n:>6,}  "
              f"{(peer_med_real / 1e6) if peer_n > 0 else float('nan'):>15.1f}    "
              f"{ratio:>5.2f}" if peer_n > 0 else
              f"  {int(r['fastnum']):<10d} {cc:<14s} {pn:>4d} {ef:>7.1f}  "
              f"{r['real_pred_mean'] / 1e6:>15.1f}    "
              f"{peer_n:>6,}  {'n/a':>17s}  {'n/a':>5s}")
        rows_out.append({"fastnum": int(r["fastnum"]), "ratio": ratio, "peer_n": peer_n})

    rows_df = pd.DataFrame(rows_out)
    valid = rows_df[rows_df["peer_n"] >= 3]
    if len(valid):
        print(f"\n  ratio (pred / peer_median), peer_n ≥ 3 only "
              f"({len(valid)}/{len(rows_df)} rows):")
        print(f"    min={valid['ratio'].min():.2f}  "
              f"median={valid['ratio'].median():.2f}  "
              f"max={valid['ratio'].max():.2f}")
        print(f"    rule of thumb: a sane iter4 should sit in [0.7, 1.3] vs peer median.")

    section("DONE")
    print(f"  total elapsed: {time.time() - t0:.1f}s")
    print(f"\n  Summary line for prompt:")
    bias = delta.mean()
    bias_pct = np.expm1(bias) * 100
    print(f"    matsvaedi-blanked bias = {bias:+.4f} log ({bias_pct:+.2f}% nominal)")
    print(f"    half-width breach: q80 {breach_q80:.1f}% / q95 {breach_q95:.1f}% of rows")
    print(f"    bucket-fallback ∈ training: "
          f"{100.0 * resolved / len(fb_buckets):.1f}% of sample")
    return 0


if __name__ == "__main__":
    sys.exit(main())
