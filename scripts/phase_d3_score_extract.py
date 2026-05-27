"""Phase D3 STEP 1c — score ~74K residential/summerhouse INSERT candidates
with iter4a + iter4_segcal_v1 calibration.

Reads D:\\phase_d3_insert_rows.parquet, builds an iter4 feature matrix
(no LLM-extraction features — has_extraction_data=0), runs the 12
iter4a boosters (6 main + 6 summer), applies per-segment k80/k95 stretch
factors, converts log-space → nominal kr via cpi_factor @ 2026-04, and
writes the result to D:\\phase_d3_predictions.parquet.

EXCLUDE rows (~42K non-residential) get no prediction — they remain in
properties but are absent from predictions, matching the existing base
(124,738 properties → 110,316 predictions).

Schema matches public.predictions (PK = fastnum):
  fastnum, real_pred_mean, real_pred_median,
  real_pred_lo80, real_pred_hi80, real_pred_lo95, real_pred_hi95,
  model_group, segment, model_version, calibration_version, predicted_at

Model versions stamped match the existing base:
  model_version='iter4_final_v1', calibration_version='iter4_conformal_v1'

Note on calibration_version: rebuild_predictions_iter4.py writes
'iter4_segcal_v1' from the JSON's version field. The existing
predictions table has 110,316 rows tagged 'iter4_conformal_v1' (the
conformal-correction layer applied on top). For D3 NOW lota we match
the existing base label so a single calibration_version represents the
deployed model surface. The actual prediction values use segcal_v1
stretch factors only (conformal corrections are precompute-driven and
not re-applied here — feature_attributions also defer to next precompute
cycle per POST_HMS_RECOVERY_PLAN §5).
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

INSERT_PARQUET = Path(r"D:\phase_d3_insert_rows.parquet")
TRAINING_PKL = Path(r"D:\training_data_v2.pkl")
CALIB_JSON = Path(r"D:\iter4_calibration_config.json")
CONFORMAL_JSON = Path(r"D:\iter4_conformal_corrections.json")
MODEL_DIR = Path(r"D:\\")
OUT_PARQUET = Path(r"D:\phase_d3_predictions.parquet")
OUT_PICKLE_FALLBACK = Path(r"D:\phase_d3_predictions.pkl")

VALUATION_YEAR = 2026
VALUATION_MONTH = 4
MODEL_VERSION = "iter4_final_v1"
CALIBRATION_VERSION = "iter4_conformal_v1"

CATEGORICALS = ["canonical_code", "matsvaedi_bucket", "region_tier", "unit_category"]


def load_models() -> dict:
    print("Loading iter4a models ...")
    out: dict = {}
    for grp in ("main", "summer"):
        for suffix in ("mean", "q025", "q100", "q500", "q900", "q975"):
            path = MODEL_DIR / f"iter4a_{grp}_{suffix}.lgb"
            if not path.exists():
                raise SystemExit(f"Missing model: {path}")
            out[f"{grp}_{suffix}"] = lgb.Booster(model_file=str(path))
    print(f"  loaded 12 boosters")

    with open(CALIB_JSON, "r", encoding="utf-8") as f:
        out["calibration"] = json.load(f)
    print(f"  segcal: {out['calibration']['version']}")
    with open(CONFORMAL_JSON, "r", encoding="utf-8") as f:
        out["conformal"] = json.load(f)
    print(f"  conformal: {out['conformal']['version']} "
          f"(method={out['conformal']['method']})")

    out["feature_names"] = out["main_mean"].feature_name()
    print(f"  feature count: {len(out['feature_names'])}")

    print("Loading CPI lookup + categorical mappings from training_data_v2 ...")
    td = pd.read_pickle(TRAINING_PKL)
    td["_yr"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.year
    td["_mn"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.month
    cpi_lookup = td.groupby(["_yr", "_mn"])["cpi_factor"].first().to_dict()
    out["cpi_factor"] = cpi_lookup.get(
        (VALUATION_YEAR, VALUATION_MONTH),
        cpi_lookup[max(cpi_lookup.keys())],
    )
    print(f"  cpi_factor @ {VALUATION_YEAR}-{VALUATION_MONTH:02d}: "
          f"{out['cpi_factor']:.4f}")

    out["categorical_mappings"] = {}
    for cat in CATEGORICALS:
        if cat in td.columns and hasattr(td[cat], "cat"):
            out["categorical_mappings"][cat] = list(td[cat].cat.categories)
    return out


def build_X_matrix(scor: pd.DataFrame, feat_names: list[str],
                   cat_map: dict[str, list]) -> pd.DataFrame:
    """Vectorized iter4 feature-matrix construction. NaN-native.
    Maps phase_d3_insert_rows column names → model feature names."""
    N = len(scor)
    X = pd.DataFrame({n: pd.array([np.nan] * N, dtype="float64") for n in feat_names})

    col_map = {
        # model feat name → phase_d3 column name
        "FASTNUM": "fastnum",
        "EINFLM": "einflm",
        "BYGGAR": "byggar",
        "LOD_FLM": "lod_flm",
        "matsvaediNUMER": "matsvaedi_numer",  # all NULL for D3 candidates
        "postnr": "postnr",
        "landnum": "landeign_nr",  # bigint → cast to float for the model
        "lat": "lat",
        "lon": "lng",
    }
    for feat_col, src_col in col_map.items():
        if feat_col not in feat_names or src_col not in scor.columns:
            continue
        # Always coerce to numeric — feat-matrix columns are float64
        s = pd.to_numeric(scor[src_col], errors="coerce")
        X[feat_col] = s.to_numpy(dtype="float64")

    if "LOD_FLM" in feat_names:
        X["LOD_FLM"] = scor["lod_flm"].fillna(0.0).to_numpy()
    if "sale_year" in feat_names:
        X["sale_year"] = float(VALUATION_YEAR)
    if "sale_month" in feat_names:
        X["sale_month"] = float(VALUATION_MONTH)
    if "age_at_sale" in feat_names:
        X["age_at_sale"] = float(VALUATION_YEAR) - scor["byggar"].astype("float64").to_numpy()
    if "has_extraction_data" in feat_names:
        X["has_extraction_data"] = 0

    for cat in CATEGORICALS:
        if cat not in feat_names:
            continue
        vals = scor[cat].to_numpy() if cat in scor.columns else [None] * N
        if cat in cat_map:
            X[cat] = pd.Categorical(vals, categories=cat_map[cat])
        else:
            X[cat] = vals

    for b in ("is_main_unit", "is_new_build"):
        if b in feat_names and b in scor.columns:
            X[b] = scor[b].astype(bool).to_numpy()

    return X


def conformal_q(canon: str, region: str, conformal: dict) -> tuple[float, float]:
    """Resolve (q80_log, q95_log) for this row.

    Priority: by_segment_region > by_segment > global. This is the
    split-conformal symmetric-logspace half-width per
    iter4_conformal_corrections.json.
    """
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


def score(scor: pd.DataFrame, models: dict) -> pd.DataFrame:
    feat_names = models["feature_names"]
    cat_map = models["categorical_mappings"]
    cpi_f = models["cpi_factor"]
    conformal = models["conformal"]

    X = build_X_matrix(scor, feat_names, cat_map)
    print(f"  X: {X.shape}")

    is_summer = scor["canonical_code"].eq("SUMMERHOUSE").to_numpy()
    pred_parts = []

    for group, mask in (("main", ~is_summer), ("summer", is_summer)):
        n = int(mask.sum())
        if n == 0:
            continue
        Xg = X.loc[mask].reset_index(drop=True)
        Rg = scor.loc[mask].reset_index(drop=True)
        print(f"  {group}: predicting on {n:,} rows ...")
        preds = {}
        # Need mean (point) + q500 (median) only when using conformal PIs.
        # q025/q100/q900/q975 from quantile boosters are no longer the PI
        # source — kept around for diagnostics but unused here.
        for suffix in ("mean", "q500"):
            m = models[f"{group}_{suffix}"]
            preds[suffix] = m.predict(Xg, num_iteration=m.best_iteration)

        canon = Rg["canonical_code"].astype(str).to_numpy()
        region = Rg["region_tier"].astype(str).to_numpy()
        # Per-row conformal half-widths
        q80 = np.empty(n, dtype=np.float64)
        q95 = np.empty(n, dtype=np.float64)
        for i in range(n):
            q80[i], q95[i] = conformal_q(canon[i], region[i], conformal)

        mn = preds["mean"]
        # Conformal PIs in log space — symmetric around mean prediction.
        lo80 = mn - q80
        hi80 = mn + q80
        lo95 = mn - q95
        hi95 = mn + q95

        def to_kr(log_vec):
            return np.round((np.expm1(log_vec) / cpi_f) * 1000).astype(np.int64)

        pred_parts.append(pd.DataFrame({
            "fastnum": Rg["fastnum"].astype("int64").to_numpy(),
            "real_pred_mean": to_kr(mn),
            "real_pred_median": to_kr(preds["q500"]),
            "real_pred_lo80": to_kr(lo80),
            "real_pred_hi80": to_kr(hi80),
            "real_pred_lo95": to_kr(lo95),
            "real_pred_hi95": to_kr(hi95),
            "model_group": group,
            "segment": canon,
            "model_version": MODEL_VERSION,
            "calibration_version": CALIBRATION_VERSION,
            "predicted_at": pd.to_datetime(
                f"{VALUATION_YEAR}-{VALUATION_MONTH:02d}-01").date(),
        }))

    return pd.concat(pred_parts, ignore_index=True) if pred_parts else pd.DataFrame()


def main() -> int:
    if not INSERT_PARQUET.exists():
        print(f"ERROR: insert parquet not found at {INSERT_PARQUET}")
        return 2

    t0 = time.time()
    print(f"Loading insert candidates ...")
    ins = pd.read_parquet(INSERT_PARQUET)
    print(f"  total: {len(ins):,} rows")

    # Hold-out funnel — only rows that pass ALL gates get scored.
    is_scorable = ins["is_residential"] | ins["is_summerhouse"]
    has_byggar = ins["byggar"].notna()
    is_confident = ins["matsvaedi_confident"].fillna(False).astype(bool)

    print(f"\n  scoring funnel:")
    print(f"    total D3 candidates              {len(ins):>7,}")
    print(f"    minus non-scorable (EXCLUDE etc) {int((~is_scorable).sum()):>7,}")
    print(f"    = residential+summer             {int(is_scorable.sum()):>7,}")
    print(f"      minus no byggar                "
          f"{int((is_scorable & ~has_byggar).sum()):>7,}")
    print(f"      minus matsvaedi-unconfident    "
          f"{int((is_scorable & has_byggar & ~is_confident).sum()):>7,}")
    scor = ins[is_scorable & has_byggar & is_confident].reset_index(drop=True)
    print(f"    = SCORABLE                       {len(scor):>7,}")

    # Held-row breakdown (residential+summer rows that did NOT make it)
    held = ins[is_scorable & ~(has_byggar & is_confident)].copy()
    held["hold_reason"] = "?"
    held.loc[~has_byggar.loc[held.index], "hold_reason"] = "no_byggar"
    held.loc[has_byggar.loc[held.index] & ~is_confident.loc[held.index],
             "hold_reason"] = "matsvaedi_unconfident"
    print(f"\n  held residential+summer rows (would have had iter4 in v1):")
    for reason, n in held["hold_reason"].value_counts().items():
        print(f"    {reason:<24s} {n:>7,}")
    print(f"  held by region_tier × reason:")
    for (region, reason), n in held.groupby(["region_tier", "hold_reason"]).size().items():
        print(f"    {region:<13s} {reason:<24s} {n:>7,}")

    models = load_models()

    print(f"\nScoring ...")
    preds = score(scor, models)
    print(f"  predictions: {len(preds):,}")

    print("\nPrediction sanity:")
    print(f"  real_pred_mean   min={int(preds['real_pred_mean'].min()):,}  "
          f"median={int(preds['real_pred_mean'].median()):,}  "
          f"max={int(preds['real_pred_mean'].max()):,}")
    print(f"  by segment:")
    seg_summary = preds.groupby("segment")["real_pred_mean"].agg(
        ["count", "min", "median", "max"]
    )
    for seg, row in seg_summary.iterrows():
        print(f"    {seg:<16s}  n={int(row['count']):>6,}  "
              f"min={int(row['min']):>13,}  med={int(row['median']):>13,}  "
              f"max={int(row['max']):>15,}")
    print(f"  by model_group:")
    for g, n in preds["model_group"].value_counts().items():
        print(f"    {g:<8s} {n:>7,}")

    try:
        preds.to_parquet(OUT_PARQUET, index=False)
        print(f"\nWrote {OUT_PARQUET} ({OUT_PARQUET.stat().st_size:,} bytes)")
    except Exception as e:
        print(f"\nparquet write failed ({type(e).__name__}: {e}); falling back to pickle")
        preds.to_pickle(OUT_PICKLE_FALLBACK)
        print(f"Wrote {OUT_PICKLE_FALLBACK} ({OUT_PICKLE_FALLBACK.stat().st_size:,} bytes)")

    print(f"\nElapsed: {time.time() - t0:.1f}s")
    print("STEP 1c (scoring) complete. NO Supabase writes performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
