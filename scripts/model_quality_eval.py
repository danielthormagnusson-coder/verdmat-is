"""model_quality_eval.py — VÉL 1: out-of-sample model quality (two OOS scores).

Weekly engine producing model_metrics rows from frozen iter4 predictions vs realized
thinglyst sale prices. Two scores on the SAME fresh out-of-sample sales:

  EINKUNN 1 (baseline)  — iter4 prediction with extraction features NULLED (structured
                          -only path) vs realized price. SKREF B uses the FROZEN
                          public.predictions over ALL OOS (sample_scope='all_oos'):
                          for the OOS universe almost no property had a listing at
                          scoring time, so the frozen prediction == structured-only.
  EINKUNN 2 (full)      — same property, Haiku reads the söluyfirlit, fills extraction,
                          re-scores. Measured only on the paired subset (SKREF D,
                          sample_scope='paired_oos'); GAP = full - baseline on that subset.

Measured NOMINAL/NOMINAL (de-anchored like v_model_vs_sold): nominal_pred =
real_pred * cpi[saleM] / cpi[model_pred_anchor_ym], compared to kaupverd_nominal.
The de-anchor base is model_pred_anchor_ym (the model real-scale anchor, frozen until
iter5) — NOT sales_history_anchor_ym — so it is stable under the weekly CPI re-anchor,
which only moves the latter. BOTH scopes (all_oos and paired_oos) use the SAME de-anchor
base; a uniform anchor change rescales every prediction by a constant and SHIFTS MAPE/bias
systematically (it does NOT cancel), so the two scopes are only comparable when the base
is identical — hence both pin cpi[model_pred_anchor_ym] (ÁKVÖRÐUN 2, 2026-06-27).

Two distinct CPI layers, do not conflate them:
  - INSIDE the adapter (phase_d3 score → nominal): cpi_factor is pinned to the FREEZE
    anchor the frozen predictions were written with (model_pred_anchor_ym at freeze =
    2026-05), NOT the live re-anchored training_data_v2.pkl, so the adapter reproduces
    public.predictions exactly (parity ~0%). See freeze_cpi_factor (ÁKVÖRÐUN 1).
  - METRICS de-anchor (here): cpi[saleM] / cpi[model_pred_anchor_ym] (live), identical
    in both scopes (ÁKVÖRÐUN 2).

OOS_CUTOFF = 2026-04-20: the iter4 model (.lgb) was trained 2026-04-21 on kaupskra
through ~2026-04-20, so sales after that date are genuinely out-of-sample. (predicted_at
2026-04-01 is a nominal stamp, NOT the train cutoff — do not use it.)

Metric core mirrors validate_metrics.py:compute_metrics (MAPE real-space, coverage of
realized price within [lo,hi], bias). Point estimate = real_pred_mean.

Logged to pipeline_runs/steps via migration_helpers; writes public.model_metrics.

CLI:
  python scripts/model_quality_eval.py --dryrun   # compute + print, no writes
  python scripts/model_quality_eval.py            # compute + write model_metrics (baseline/all_oos)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from rebuild_sales_history import open_ro_conn, DBCONFIG  # noqa: E402
from migration_helpers import (  # noqa: E402
    start_run, start_step, finish_step, finish_run, open_connection,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(
    sys.stdout, "reconfigure") else None

OOS_CUTOFF = "2026-04-20"            # iter4 .lgb trained 2026-04-21 → sales after = OOS
MODEL_VERSION = "iter4_final_v1"
ANCHOR_KEY = "model_pred_anchor_ym"  # model real-scale anchor (frozen until iter5)

# ÁKVÖRÐUN 1 (2026-06-27) — adapter freeze anchor. public.predictions were frozen by
# phase_d3_score_extract when model_pred_anchor_ym was 2026-05; the weekly CPI engine has
# since moved the live anchor to 2026-07 AND re-anchored training_data_v2.pkl, whose
# cpi_factor the adapter reads. Re-scoring through the live pkl rescales every adapter
# prediction by cpi[2026-05]/cpi[2026-07] = -0.8768% uniform (empirically confirmed to 6dp,
# std 0 → pure scale, not model error). The fix pins the adapter's real→nominal conversion
# to the FREEZE anchor below, NOT the live pipeline_config value. This constant records the
# anchor the predictions were written with (not queryable — the live config was overwritten).
FREEZE_ANCHOR_YM = "2026-05"
PRED_VALUATION_YM = "2026-04"        # phase_d3 VALUATION_YEAR/MONTH — stored preds nominal @ this

# Resumable raw-extraction cache (outside repo). Keyed by fastnum + listing-hash so a
# killed/repeated run resumes without re-paying Haiku, and a changed listing re-extracts.
EXTRACT_CACHE = Path(r"D:\model_quality_extraction_cache.jsonl")

# Self-log to a persistent file (mirror daily_sales_refresh / monthly_cpi_reanchor) so the
# scheduled S4U run leaves a durable stdout trace (per-call durations, skips) beyond the
# DB record in pipeline_runs/model_metrics.
LOGFILE = Path(r"D:\model_quality_eval.log")


class _Tee:
    """Write stdout to the console AND the run log. Logging must never crash the run."""
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
            except Exception:
                pass

    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass

# MAPE/coverage flag thresholds (validate_metrics.py convention)
MAPE_FLAG_PP = 0.5
COV_FLAG_PP = 3.0
# validate_metrics held baseline (for context flags in `extra`)
BASELINE = {"mape": 7.00, "cov80": 73.1, "cov95": 92.7}

PRICE_BANDS = [(0, 40_000_000, "<40M"), (40_000_000, 70_000_000, "40-70M"),
               (70_000_000, 100_000_000, "70-100M"), (100_000_000, 9e18, ">=100M")]

# D-side modules live on D:\ (training/scoring tree), not in scripts/.
sys.path.insert(0, r"D:\\")


# API key lives OUTSIDE the repo AND outside the CC process environment: a global
# ANTHROPIC_API_KEY once caused CC itself to bill the key ($8 leak). The file name is
# non-standard ("env.local", no leading dot) so python-dotenv does NOT auto-load it —
# the absolute path is mandatory.
ENV_LOCAL = r"D:\env.local"


def anthropic_key() -> str | None:
    """ANTHROPIC_API_KEY read ONLY from D:\\env.local, never from the CC process
    environment (os.environ / Windows registry). dotenv_values parses the file without
    mutating os.environ, so the CC environment stays key-free and cannot self-bill."""
    from dotenv import dotenv_values
    return dotenv_values(ENV_LOCAL).get("ANTHROPIC_API_KEY") or None


def metrics_from_arrays(actual, pred, lo80, hi80, lo95, hi95) -> dict | None:
    """MAPE/medAPE/bias/cov80/cov95 from nominal arrays (shared by E1 + E2)."""
    actual = np.asarray(actual, float); pred = np.asarray(pred, float)
    if len(actual) == 0:
        return None
    ape = np.abs(actual - pred) / actual
    in80 = (actual >= np.asarray(lo80, float)) & (actual <= np.asarray(hi80, float))
    in95 = (actual >= np.asarray(lo95, float)) & (actual <= np.asarray(hi95, float))
    return {
        "n": int(len(actual)),
        "mape": round(float(100 * ape.mean()), 4),
        "med_ape": round(float(100 * np.median(ape)), 4),
        "bias": round(float(100 * ((actual - pred) / actual).mean()), 4),
        "cov80": round(float(100 * in80.mean()), 4),
        "cov95": round(float(100 * in95.mean()), 4),
    }


def fetch_oos(conn) -> pd.DataFrame:
    """Pull OOS (prediction, sale) pairs with de-anchor inputs + segment dims."""
    sql = f"""
    WITH anchor AS (
      SELECT cpi AS anchor_cpi FROM public.cpi_index
      WHERE year_month = (SELECT value FROM public.pipeline_config WHERE key='{ANCHOR_KEY}')
    )
    SELECT s.fastnum, s.thinglystdags, s.kaupverd_nominal,
           p.real_pred_mean, p.real_pred_lo80, p.real_pred_hi80,
           p.real_pred_lo95, p.real_pred_hi95,
           cs.cpi AS cpi_sale, a.anchor_cpi,
           pr.matsvaedi_numer, pr.canonical_code, pr.is_new_build, pr.region_tier
    FROM public.predictions p
    JOIN public.sales_history s ON s.fastnum = p.fastnum
    JOIN public.properties pr ON pr.fastnum = p.fastnum
    CROSS JOIN anchor a
    LEFT JOIN public.cpi_index cs ON cs.year_month = to_char(s.thinglystdags, 'YYYY-MM')
    WHERE p.model_version = '{MODEL_VERSION}'
      AND s.thinglystdags > DATE '{OOS_CUTOFF}'
      AND s.onothaefur = 0          -- arm's-length only; onothaefur=1 are non-market
                                    -- (gifts/partial transfers) and would wreck MAPE/bias
      AND s.kaupverd_nominal IS NOT NULL AND s.kaupverd_nominal > 0
      AND p.real_pred_mean IS NOT NULL
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    return df


def compute_metrics(sub: pd.DataFrame) -> dict | None:
    """E1/all_oos metrics from FROZEN predictions, de-anchored nominal/nominal.

    Mirrors validate_metrics.compute_metrics. De-anchor base = cpi[model_pred_anchor_ym]
    (anchor_cpi from fetch_oos), the SAME base the paired_oos path uses (ÁKVÖRÐUN 2) so the
    two scopes are comparable. A uniform anchor change shifts MAPE/bias — it does not cancel.
    """
    if len(sub) == 0:
        return None
    f = (sub["cpi_sale"].astype(float) / sub["anchor_cpi"].astype(float)).values
    return metrics_from_arrays(
        sub["kaupverd_nominal"].astype(float).values,
        sub["real_pred_mean"].astype(float).values * f,
        sub["real_pred_lo80"].astype(float).values * f,
        sub["real_pred_hi80"].astype(float).values * f,
        sub["real_pred_lo95"].astype(float).values * f,
        sub["real_pred_hi95"].astype(float).values * f,
    )


def segments(df: pd.DataFrame):
    """Yield (segment_dim, segment_value, sub) for every breakdown."""
    yield ("overall", "", df)
    # hood (matsvaedi) — only segments with >= 10 pairs (stable medians)
    for mv, sub in df.dropna(subset=["matsvaedi_numer"]).groupby("matsvaedi_numer"):
        if len(sub) >= 10:
            yield ("hood", str(int(mv)), sub)
    # property type
    for cc, sub in df.dropna(subset=["canonical_code"]).groupby("canonical_code"):
        if len(sub) >= 10:
            yield ("property_type", str(cc), sub)
    # price band
    nom = df["kaupverd_nominal"].astype(float)
    for lo, hi, label in PRICE_BANDS:
        sub = df[(nom >= lo) & (nom < hi)]
        if len(sub) >= 10:
            yield ("price_band", label, sub)
    # new build
    for flag, sub in df.dropna(subset=["is_new_build"]).groupby("is_new_build"):
        yield ("new_build", "true" if flag else "false", sub)


# ======================================================================
# EINKUNN 2 (full) — paired OOS, Haiku extraction (SKREF D)
# ======================================================================
def fetch_paired_oos(conn) -> pd.DataFrame:
    """OOS sales (onothaefur=0, after cutoff) that have a listing description.

    One row per (fastnum, sale); lysing = most-recent listing for that fastnum.
    """
    sql = f"""
    WITH listing AS (
      SELECT DISTINCT ON (fastnum) fastnum, lysing
      FROM scraper.listings_canonical
      WHERE fastnum IS NOT NULL AND lysing IS NOT NULL AND length(lysing) >= 300
      ORDER BY fastnum, last_seen_at DESC NULLS LAST
    )
    -- DISTINCT ON (fastnum): one row per property (BÖGGUR 1). A fastnum with >1 OOS sale
    -- would otherwise make pred_df.loc[fastnum] return a frame → TypeError in scoring.
    -- Pick the most-recent OOS sale (closest to the listing); scoring is per-property
    -- anyway (the iter4 prediction is identical across a property's sales).
    SELECT DISTINCT ON (s.fastnum)
           s.fastnum, s.thinglystdags, s.kaupverd_nominal,
           EXTRACT(year FROM s.thinglystdags)::int  AS sale_year,
           EXTRACT(month FROM s.thinglystdags)::int AS sale_month,
           pr.einflm, pr.lod_flm, pr.byggar, pr.matsvaedi_numer, pr.matsvaedi_bucket,
           pr.region_tier, pr.canonical_code, pr.unit_category, pr.is_main_unit,
           pr.is_new_build, pr.postnr, pr.lat, pr.lng, pr.landeign_nr, l.lysing
    FROM public.predictions p
    JOIN public.sales_history s ON s.fastnum = p.fastnum
    JOIN public.properties pr ON pr.fastnum = p.fastnum
    JOIN listing l ON l.fastnum = p.fastnum
    WHERE p.model_version = '{MODEL_VERSION}'
      AND s.thinglystdags > DATE '{OOS_CUTOFF}'
      AND s.onothaefur = 0
      AND s.kaupverd_nominal IS NOT NULL AND s.kaupverd_nominal > 0
    ORDER BY s.fastnum, s.thinglystdags DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return _coerce_numeric(pd.DataFrame(cur.fetchall(), columns=cols))


def fetch_parity_sample(conn, n: int) -> pd.DataFrame:
    """Sample OOS fastnums with structured cols + FROZEN real_pred_median (D2 gate)."""
    sql = f"""
    SELECT DISTINCT ON (s.fastnum)
           s.fastnum, p.real_pred_median AS frozen_median,
           pr.einflm, pr.lod_flm, pr.byggar, pr.matsvaedi_numer, pr.matsvaedi_bucket,
           pr.region_tier, pr.canonical_code, pr.unit_category, pr.is_main_unit,
           pr.is_new_build, pr.postnr, pr.lat, pr.lng, pr.landeign_nr
    FROM public.predictions p
    JOIN public.sales_history s ON s.fastnum = p.fastnum
    JOIN public.properties pr ON pr.fastnum = p.fastnum
    WHERE p.model_version = '{MODEL_VERSION}'
      AND s.thinglystdags > DATE '{OOS_CUTOFF}' AND s.onothaefur = 0
      AND p.real_pred_median IS NOT NULL
    ORDER BY s.fastnum
    LIMIT {int(n)}
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return _coerce_numeric(pd.DataFrame(cur.fetchall(), columns=cols))


def fetch_cpi_lookup(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT year_month, cpi FROM public.cpi_index")
        return {ym: float(c) for ym, c in cur.fetchall()}


def freeze_cpi_factor(cpi_lookup: dict) -> float:
    """cpi_factor the FROZEN public.predictions were written with (ÁKVÖRÐUN 1).

    phase_d3.to_kr divides the model's real output by cpi_factor to get nominal @ the
    valuation month: cpi_factor = cpi[anchor] / cpi[valuation_month]. Pinning anchor to
    the FREEZE anchor (2026-05) rather than the live re-anchored pkl reproduces the frozen
    predictions exactly. Computed from public.cpi_index (DB), independent of the pkl.
    """
    for ym in (FREEZE_ANCHOR_YM, PRED_VALUATION_YM):
        if ym not in cpi_lookup:
            raise RuntimeError(f"cpi_index missing {ym} — cannot pin freeze anchor")
    return cpi_lookup[FREEZE_ANCHOR_YM] / cpi_lookup[PRED_VALUATION_YM]


def load_models_freeze_anchored(conn) -> dict:
    """load iter4 boosters, then override cpi_factor to the FREEZE anchor (ÁKVÖRÐUN 1).

    load_models() reads cpi_factor from the LIVE training_data_v2.pkl, which the weekly
    CPI engine re-anchors → would rescale every adapter prediction. We replace it with the
    freeze-anchored value so adapter baseline == frozen predictions (D2 parity ~0%).
    """
    from phase_d3_score_extract import load_models as load_iter4
    models = load_iter4()
    live = float(models["cpi_factor"])
    models["cpi_factor"] = freeze_cpi_factor(fetch_cpi_lookup(conn))
    print(f"  cpi_factor override: live(pkl)={live:.6f} -> "
          f"freeze[{FREEZE_ANCHOR_YM}/{PRED_VALUATION_YM}]={models['cpi_factor']:.6f} "
          f"(ÁKVÖRÐUN 1: pin to frozen predictions)")
    return models


def _cache_key(fastnum: int, lysing: str) -> str:
    import hashlib
    return f"{fastnum}:{hashlib.md5((lysing or '').encode('utf-8')).hexdigest()[:12]}"


def load_extract_cache() -> dict:
    """Load the persistent raw-extraction cache → {key: raw_extraction_dict}. Tolerant of a
    partial/corrupt trailing line (an append interrupted by a kill)."""
    import json
    cache: dict[str, dict] = {}
    if EXTRACT_CACHE.exists():
        for line in EXTRACT_CACHE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                cache[rec["key"]] = rec["raw"]
            except Exception:
                continue
    return cache


def append_extract_cache(key: str, fastnum: int, raw: dict) -> None:
    import json
    with open(EXTRACT_CACHE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, "fastnum": fastnum, "raw": raw},
                           ensure_ascii=False) + "\n")


def read_model_anchor_cpi(conn) -> tuple[str, float]:
    """(model_pred_anchor_ym, cpi at that month) — the live metrics de-anchor base used by
    BOTH all_oos and paired_oos (ÁKVÖRÐUN 2), identical to v_model_vs_sold. Raises if the
    anchor month is missing from cpi_index (no silent NaN)."""
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM public.pipeline_config WHERE key=%s", (ANCHOR_KEY,))
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"pipeline_config missing {ANCHOR_KEY}")
        ym = row[0]
        cur.execute("SELECT cpi FROM public.cpi_index WHERE year_month=%s", (ym,))
        crow = cur.fetchone()
        if crow is None:
            raise RuntimeError(f"cpi_index missing model_pred_anchor_ym={ym}")
        return ym, float(crow[0])


# psycopg2 returns numeric columns as Decimal (pandas object dtype); LightGBM needs
# int/float/bool. Coerce the numeric feature columns the iter4 scorer consumes.
_NUMERIC_COLS = ["einflm", "lod_flm", "byggar", "matsvaedi_numer", "postnr", "lat",
                 "lng", "landeign_nr", "frozen_median", "kaupverd_nominal",
                 "sale_year", "sale_month"]


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for c in _NUMERIC_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _num(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else v


def structured_dict(r) -> dict:
    """Map a paired-OOS row to a score_property property_dict (structured only)."""
    d = {
        "FASTNUM": int(r["fastnum"]),
        "EINFLM": _num(float(r["einflm"])) if r["einflm"] is not None else None,
        "LOD_FLM": _num(float(r["lod_flm"])) if r["lod_flm"] is not None else None,
        "BYGGAR": _num(float(r["byggar"])) if r["byggar"] is not None else None,
        "sale_year": int(r["sale_year"]), "sale_month": int(r["sale_month"]),
        "matsvaediNUMER": int(r["matsvaedi_numer"]) if r["matsvaedi_numer"] is not None else None,
        "matsvaedi_bucket": r["matsvaedi_bucket"], "region_tier": r["region_tier"],
        "canonical_code": r["canonical_code"], "unit_category": r["unit_category"],
        "is_main_unit": bool(r["is_main_unit"]) if r["is_main_unit"] is not None else None,
        "is_new_build": bool(r["is_new_build"]) if r["is_new_build"] is not None else None,
        "postnr": int(r["postnr"]) if r["postnr"] is not None else None,
        "lat": _num(float(r["lat"])) if r["lat"] is not None else None,
        "lon": _num(float(r["lng"])) if r["lng"] is not None else None,
    }
    try:
        d["landnum"] = int(r["landeign_nr"])
    except (TypeError, ValueError):
        pass
    return {k: v for k, v in d.items() if v is not None}


_PRED_COLS = ["fastnum", "real_pred_mean", "real_pred_median", "real_pred_lo80",
              "real_pred_hi80", "real_pred_lo95", "real_pred_hi95"]


def _score_iter4(df: pd.DataFrame, models: dict, ext_by_fastnum: dict | None = None) -> pd.DataFrame:
    """Score paired rows through the iter4a path (phase_d3_score_extract.score).

    Reuses the SAME boosters/conformal/valuation that produced public.predictions, with
    cpi_factor pinned to the freeze anchor (load_models_freeze_anchored) → baseline (no
    extraction) reproduces frozen predictions (parity). When ext_by_fastnum is given,
    overlay extraction feature columns → E2 full path. Stored scale = nominal @
    PRED_VALUATION_YM, like the frozen table; the metrics de-anchor (caller) takes it from
    there. Empty input → empty frame WITH the expected columns (BÖGGUR 2: phase_d3.score
    returns a column-less frame on empty input, which would KeyError on the column select).
    """
    from phase_d3_score_extract import score as iter4_score
    if len(df) == 0:
        return pd.DataFrame(columns=_PRED_COLS)
    scor = df.copy()
    if ext_by_fastnum:
        feat_keys = set()
        for d in ext_by_fastnum.values():
            feat_keys |= set(d.keys())
        fns = [int(fn) for fn in scor["fastnum"]]
        # Add all ~108 extraction columns in ONE concat — per-column insertion fragments
        # the frame (floods logs with PerformanceWarning on the weekly run).
        ext_df = pd.DataFrame(
            {k: [(ext_by_fastnum.get(fn) or {}).get(k, np.nan) for fn in fns]
             for k in feat_keys},
            index=scor.index)
        scor = pd.concat([scor, ext_df], axis=1)
    pred = iter4_score(scor, models)
    if pred.empty:
        return pd.DataFrame(columns=_PRED_COLS)
    return pred[_PRED_COLS]


def run_parity(df: pd.DataFrame, frozen_median: dict, models) -> pd.DataFrame:
    """D2 gate: adapter baseline real_pred_median vs frozen public.predictions."""
    pred = _score_iter4(df, models)  # baseline, no extraction
    pred = pred.set_index("fastnum")
    recs = []
    for fn in df["fastnum"].astype("int64"):
        if fn not in pred.index or fn not in frozen_median:
            continue
        adapter = float(pred.loc[fn, "real_pred_median"])
        frozen = float(frozen_median[fn])
        pct = 100.0 * abs(adapter - frozen) / frozen if frozen else np.nan
        recs.append({"fastnum": fn, "adapter": adapter, "frozen": frozen, "pct_diff": pct})
    return pd.DataFrame(recs)


def run_paired(df: pd.DataFrame, models, cpi_lookup: dict, anchor_cpi: float,
               log_fn) -> tuple[dict, dict]:
    """E2: per paired OOS property — baseline (iter4 structured) + full (iter4 + Haiku
    extraction), de-anchored nominal/nominal vs kaupverd_nominal.

    De-anchor = cpi[saleM] / cpi[model_pred_anchor_ym] (anchor_cpi) — IDENTICAL to the
    all_oos path (ÁKVÖRÐUN 2). Sale months missing from cpi_index are dropped + counted,
    never a silent NaN row (BÖGGUR 3). Haiku failures drop that property (counted), never
    abort (per-property). All-fail / empty set → None metrics, not a KeyError (BÖGGUR 2).
    Extraction cached per fastnum.
    """
    from build_training_data_v2 import build_extraction_features
    from pilot_extract_v022 import build_tool_schema, extract_listing
    import anthropic

    # BÖGGUR 3: rows whose sale month is absent from cpi_index would de-anchor to NaN.
    # Drop them up front (count it) so base + full score the same row set.
    def _ym(r):
        return f"{int(r['sale_year']):04d}-{int(r['sale_month']):02d}"
    miss_mask = df.apply(lambda r: _ym(r) not in cpi_lookup, axis=1)
    n_missing_cpi = int(miss_mask.sum())
    if n_missing_cpi:
        for ym in sorted({_ym(r) for _, r in df[miss_mask].iterrows()}):
            log_fn(f"    drop {int((df[miss_mask].apply(_ym, axis=1) == ym).sum())} row(s): "
                   f"sale month {ym} missing from cpi_index")
        df = df[~miss_mask].copy()

    schema = build_tool_schema()
    # Per-request timeout 60s + NO SDK-level retry: extract_listing already has its own
    # MAX_RETRIES loop, so SDK retries would compound. A hung connection on the default
    # client (timeout 600s × 3 SDK attempts) stalled the first run ~30 min on ONE call;
    # 60s bounds it → extract_listing retries → property skipped, run continues.
    client = anthropic.Anthropic(api_key=anthropic_key(), timeout=60.0, max_retries=0)
    cache = load_extract_cache()
    if cache:
        log_fn(f"    extraction cache: {len(cache)} entries loaded (resumable)")

    ext_by_fastnum: dict[int, dict] = {}
    n_calls = 0; n_fail = 0; n_cached = 0
    keep = []
    total = len(df)
    for i, (_, r) in enumerate(df.iterrows(), 1):
        fastnum = int(r["fastnum"])
        if fastnum in ext_by_fastnum:
            keep.append(fastnum); continue
        key = _cache_key(fastnum, r["lysing"])
        try:
            if key in cache:
                raw = cache[key]; n_cached += 1; dur = "cache"
            else:
                raw, usage, err = extract_listing(client, schema, r["lysing"], lambda *a, **k: None)
                n_calls += 1
                if err or raw is None:
                    raise RuntimeError(err or "no extraction")
                append_extract_cache(key, fastnum, raw)   # persist immediately → resumable
                dur = f"{usage.get('duration_sec', '?')}s"
            ext_by_fastnum[fastnum] = build_extraction_features(
                raw, int(r["sale_year"]), r["canonical_code"])
            keep.append(fastnum)
            log_fn(f"    [{i}/{total}] fastnum={fastnum} ok ({dur})")
        except Exception as e:
            log_fn(f"    [{i}/{total}] skip fastnum={fastnum}: Haiku error {type(e).__name__}: {e}")
            n_fail += 1

    summary = {"haiku_calls": n_calls, "cached": n_cached, "dropped": n_fail,
               "scored": len(keep), "missing_cpi": n_missing_cpi,
               "cost_est_usd": round(n_calls * 0.0071, 4)}

    # BÖGGUR 2: every extraction failed / empty set → nothing to score. Return None metrics
    # (callers handle None) rather than letting an empty frame KeyError downstream.
    if not keep:
        log_fn("    no extractions succeeded — paired metrics unavailable (E1 unaffected)")
        return {"baseline": None, "full": None, "gap": None}, summary

    sub = df[df["fastnum"].astype("int64").isin(keep)].copy()

    base_pred = _score_iter4(sub, models).set_index("fastnum")
    full_pred = _score_iter4(sub, models, ext_by_fastnum).set_index("fastnum")

    def _arrays(pred_df):
        actual, mean, lo80, hi80, lo95, hi95 = [], [], [], [], [], []
        for _, r in sub.iterrows():
            fn = int(r["fastnum"])
            if fn not in pred_df.index:
                continue
            f = cpi_lookup[_ym(r)] / anchor_cpi          # ÁKVÖRÐUN 2: cpi[saleM]/cpi[anchor]
            p = pred_df.loc[fn]
            actual.append(float(r["kaupverd_nominal"]))
            mean.append(float(p["real_pred_mean"]) * f)
            lo80.append(float(p["real_pred_lo80"]) * f); hi80.append(float(p["real_pred_hi80"]) * f)
            lo95.append(float(p["real_pred_lo95"]) * f); hi95.append(float(p["real_pred_hi95"]) * f)
        return actual, mean, lo80, hi80, lo95, hi95

    base_m = metrics_from_arrays(*_arrays(base_pred))
    full_m = metrics_from_arrays(*_arrays(full_pred))
    gap_m = None
    if base_m and full_m:
        gap_m = {"n": base_m["n"]}
        for k in ("mape", "med_ape", "bias", "cov80", "cov95"):
            gap_m[k] = round(full_m[k] - base_m[k], 4)  # full - baseline
    return {"baseline": base_m, "full": full_m, "gap": gap_m}, summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun", action="store_true", help="compute + print, no writes")
    ap.add_argument("--skip-paired", action="store_true", help="E1/all_oos only, no Haiku")
    ap.add_argument("--max-paired", type=int, default=None, help="cap paired properties (test)")
    ap.add_argument("--parity", action="store_true",
                    help="D2 gate: adapter baseline vs frozen predictions, then exit")
    ap.add_argument("--parity-n", type=int, default=100, help="parity sample size")
    args = ap.parse_args()

    # Self-log: tee stdout to LOGFILE (append) so the scheduled run leaves a durable trace.
    import datetime as _dt
    try:
        _logf = open(LOGFILE, "a", encoding="utf-8")
        _logf.write(f"\n===== run @ {_dt.datetime.now().isoformat(timespec='seconds')} "
                    f"argv={sys.argv[1:]} =====\n")
        sys.stdout = _Tee(sys.__stdout__, _logf)
    except Exception:
        _logf = None

    print(f"=== model_quality_eval ({'DRYRUN' if args.dryrun else 'LIVE'}) — "
          f"EINKUNN 1 baseline/all_oos, cutoff {OOS_CUTOFF} ===")

    conn_log = open_connection()
    run_id = start_run(conn_log, "model_quality_eval")
    print(f"  pipeline_runs.id = {run_id}")
    conn_ro = None
    try:
        conn_ro = open_ro_conn()

        # ---- D2 PARITY GATE: adapter baseline vs frozen predictions, then exit ----
        if args.parity:
            sid = start_step(conn_log, run_id, "parity_gate", 1)
            models = load_models_freeze_anchored(conn_ro)
            pdf = fetch_parity_sample(conn_ro, args.parity_n)
            frozen = dict(zip(pdf["fastnum"].astype("int64"), pdf["frozen_median"].astype(float)))
            ptab = run_parity(pdf, frozen, models)
            tot = len(ptab); ok = int((ptab["pct_diff"] < 0.1).sum())
            mx = float(ptab["pct_diff"].max()); med = float(ptab["pct_diff"].median())
            print(f"\n  PARITY (adapter baseline vs frozen real_pred_median), n={tot}")
            print(f"  within 0.1%: {ok}/{tot} | max {mx:.4f}% | median {med:.4f}%")
            print(f"\n  {'fastnum':>10} {'adapter':>14} {'frozen':>14} {'pct_diff':>9}")
            for _, r in ptab.sort_values("pct_diff", ascending=False).head(12).iterrows():
                print(f"  {int(r['fastnum']):>10} {int(r['adapter']):>14,} {int(r['frozen']):>14,} "
                      f"{r['pct_diff']:>8.4f}%")
            # KRAFA: max < 0.1% (D2). After the freeze-anchor fix this should be ~0.00%.
            verdict = "PASS" if mx < 0.1 else "REVIEW"
            print(f"\n  PARITY VERDICT: {verdict}  (threshold max < 0.1%)")
            finish_step(conn_log, sid, 0, rowcount_after=tot,
                        notes=f"parity {verdict}: {ok}/{tot} within 0.1%, max {mx:.4f}%")
            finish_run(conn_log, run_id, "success",
                       {"mode": "parity", "n": tot, "within_0_1pct": ok,
                        "max_pct_diff": round(mx, 6), "verdict": verdict})
            return 0

        sid = start_step(conn_log, run_id, "compute_baseline_all_oos", 1)
        df = fetch_oos(conn_ro)
        n_missing_cpi = int(df["cpi_sale"].isna().sum())
        df = df[df["cpi_sale"].notna()].copy()
        print(f"  OOS pairs={len(df):,} (missing-cpi dropped={n_missing_cpi})")

        rows = []  # model_metrics rows
        overall = None
        for dim, val, sub in segments(df):
            m = compute_metrics(sub)
            if m is None:
                continue
            if dim == "overall":
                overall = m
            rows.append((dim, val, m))

        # console report
        print(f"\n  {'dim':<13} {'value':<16} {'n':>5} {'mape':>7} {'medape':>7} "
              f"{'bias':>7} {'cov80':>6} {'cov95':>6}")
        for dim, val, m in rows:
            print(f"  {dim:<13} {val:<16} {m['n']:>5} {m['mape']:>7.2f} {m['med_ape']:>7.2f} "
                  f"{m['bias']:>7.2f} {m['cov80']:>6.1f} {m['cov95']:>6.1f}")

        # flags vs validate_metrics held baseline (context only)
        flags = {}
        if overall:
            flags = {
                "mape_vs_baseline_pp": round(overall["mape"] - BASELINE["mape"], 2),
                "cov80_vs_baseline_pp": round(overall["cov80"] - BASELINE["cov80"], 2),
                "cov95_vs_baseline_pp": round(overall["cov95"] - BASELINE["cov95"], 2),
                "mape_flag": abs(overall["mape"] - BASELINE["mape"]) > MAPE_FLAG_PP,
                "cov80_flag": abs(overall["cov80"] - BASELINE["cov80"]) > COV_FLAG_PP,
                "cov95_flag": abs(overall["cov95"] - BASELINE["cov95"]) > COV_FLAG_PP,
            }
        print(f"\n  overall flags vs held baseline: {flags}")
        finish_step(conn_log, sid, 0, rowcount_after=len(df),
                    notes=f"baseline/all_oos: {len(rows)} seg rows, oos={len(df)}")

        # ---- SKREF D: paired OOS — E1 rescored + E2 full + gap (Haiku) ----
        paired_rows = []          # (score_type, metrics) overall, sample_scope='paired_oos'
        paired_summary = {}
        selection = {}
        if not args.skip_paired:
            sid2 = start_step(conn_log, run_id, "compute_paired", 2)
            # E1-VÖRN: the proven Einkunn 1 (baseline/all_oos) is already computed in `rows`.
            # A paired/Haiku failure (import, auth, all-fail, etc.) must NEVER abort the run
            # before the E1 write. Wrap the whole paired block so any error logs loudly,
            # marks the step failed, and falls through to the E1 write below.
            try:
                models = load_models_freeze_anchored(conn_ro)
                cpi_lookup = fetch_cpi_lookup(conn_ro)
                anchor_ym, anchor_cpi = read_model_anchor_cpi(conn_ro)
                print(f"  metrics de-anchor base: cpi[{anchor_ym}]={anchor_cpi:.3f} (ÁKVÖRÐUN 2)")
                pdf = fetch_paired_oos(conn_ro)
                pdf = pdf[pdf["canonical_code"].notna()].copy()
                if args.max_paired is not None:
                    pdf = pdf.head(args.max_paired)
                elif args.dryrun:
                    pdf = pdf.head(5)     # dryrun default: prove pipeline on 5 (REAL Haiku)
                print(f"\n  PAIRED OOS properties: {len(pdf)} (Haiku extraction live)")
                scores, paired_summary = run_paired(pdf, models, cpi_lookup, anchor_cpi, print)
                for st in ("baseline", "full", "gap"):
                    if scores.get(st):
                        paired_rows.append((st, scores[st]))
                print(f"\n  {'score':<9} {'n':>4} {'mape':>7} {'medape':>7} {'bias':>7} "
                      f"{'cov80':>6} {'cov95':>6}")
                for st, m in paired_rows:
                    print(f"  {st:<9} {m['n']:>4} {m['mape']:>7.2f} {m['med_ape']:>7.2f} "
                          f"{m['bias']:>7.2f} {m['cov80']:>6.1f} {m['cov95']:>6.1f}")
                print(f"  paired summary: {paired_summary}")
                # SELECTION: baseline/all_oos (frozen, overall) vs baseline/paired_oos (rescored).
                # Both now use cpi[model_pred_anchor_ym] de-anchor (ÁKVÖRÐUN 2) → comparable.
                bp = scores.get("baseline")
                if overall and bp:
                    d_med = round(bp["med_ape"] - overall["med_ape"], 2)
                    verdict = "REPRESENTATIVE" if abs(d_med) <= 2.0 else "SELECTION-SKEWED"
                    selection = {
                        "all_oos_n": overall["n"], "paired_n": bp["n"],
                        "medape_all": overall["med_ape"], "medape_paired": bp["med_ape"],
                        "mape_all": overall["mape"], "mape_paired": bp["mape"],
                        "bias_all": overall["bias"], "bias_paired": bp["bias"],
                        "medape_delta": d_med, "verdict": verdict,
                        "note": ("baseline/all_oos is frozen predictions; baseline/paired_oos is "
                                 "re-scored structured-only; both de-anchored at "
                                 "cpi[model_pred_anchor_ym] (ÁKVÖRÐUN 2) → comparable. "
                                 "REPRESENTATIVE: gap is pure extraction contribution; "
                                 "SELECTION-SKEWED: paired subset differs from the OOS universe."),
                    }
                    print(f"\n  SELECTION ({verdict}): medAPE all_oos {overall['med_ape']:.2f} vs "
                          f"paired {bp['med_ape']:.2f} (Δ{d_med:+.2f}); "
                          f"MAPE {overall['mape']:.2f} vs {bp['mape']:.2f}  "
                          f"[n {overall['n']} vs {bp['n']}]")
                finish_step(conn_log, sid2, 0, rowcount_after=paired_summary.get("scored"),
                            notes=f"paired: {paired_summary}")
            except Exception as e:
                import traceback
                print(f"\n  *** PAIRED block failed ({type(e).__name__}: {e}) — "
                      f"E1 baseline/all_oos PRESERVED, paired skipped ***")
                traceback.print_exc()
                paired_rows = []
                paired_summary = {"paired_error": f"{type(e).__name__}: {str(e)[:300]}"}
                selection = {}
                finish_step(conn_log, sid2, 1,
                            notes=f"paired FAILED (E1 preserved): {type(e).__name__}: {str(e)[:200]}")

        if args.dryrun:
            finish_run(conn_log, run_id, "success",
                       {"dryrun": True, "oos_pairs": len(df), "overall": overall,
                        "flags": flags, "paired_summary": paired_summary,
                        "paired": {st: m for st, m in paired_rows}, "selection": selection})
            print("\n  DRYRUN complete — no model_metrics writes.")
            return 0

        # ---- write model_metrics (baseline/all_oos + paired baseline/full/gap) ----
        import psycopg2
        from psycopg2.extras import execute_values
        import json
        payload = []
        for dim, val, m in rows:
            extra = flags if dim == "overall" else None
            payload.append((run_id, MODEL_VERSION, OOS_CUTOFF, "baseline", dim, val,
                            "all_oos", m["n"], m["mape"], m["med_ape"], m["bias"],
                            m["cov80"], m["cov95"], json.dumps(extra) if extra else None))
        for st, m in paired_rows:
            extra = ({"selection": selection, **paired_summary} if st == "baseline"
                     else (paired_summary if st == "gap" else None))
            payload.append((run_id, MODEL_VERSION, OOS_CUTOFF, st, "overall", "",
                            "paired_oos", m["n"], m["mape"], m["med_ape"], m["bias"],
                            m["cov80"], m["cov95"], json.dumps(extra) if extra else None))
        url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
        conn_w = psycopg2.connect(url); conn_w.autocommit = False
        try:
            with conn_w.cursor() as cur:
                cur.execute("SET TRANSACTION READ WRITE")
                execute_values(cur,
                    "INSERT INTO public.model_metrics "
                    "(metric_run_id, model_version, oos_cutoff, score_type, segment_dim, "
                    " segment_value, sample_scope, n_pairs, mape, med_ape, bias, cov80, cov95, extra) "
                    "VALUES %s "
                    "ON CONFLICT (metric_run_id, score_type, segment_dim, segment_value, sample_scope) "
                    "DO UPDATE SET n_pairs=EXCLUDED.n_pairs, mape=EXCLUDED.mape, "
                    "  med_ape=EXCLUDED.med_ape, bias=EXCLUDED.bias, cov80=EXCLUDED.cov80, "
                    "  cov95=EXCLUDED.cov95, extra=EXCLUDED.extra, computed_at=now()",
                    payload)
                written = cur.rowcount
            conn_w.commit()
            print(f"\n  wrote {written} model_metrics rows "
                  f"({len(rows)} all_oos + {len(paired_rows)} paired)")
        except Exception as e:
            conn_w.rollback(); conn_w.close()
            finish_run(conn_log, run_id, "failed", {"step": "write", "error": str(e)[:500]})
            return 1
        conn_w.close()
        finish_run(conn_log, run_id, "success",
                   {"dryrun": False, "oos_pairs": len(df), "overall": overall, "flags": flags,
                    "paired_summary": paired_summary, "selection": selection,
                    "rows_written": len(payload)})
        return 0
    except Exception as e:
        print(f"*** CRASH: {type(e).__name__}: {e}")
        finish_run(conn_log, run_id, "crashed", {"error": str(e)[:500]})
        raise
    finally:
        if conn_ro is not None:
            try:
                conn_ro.close()
            except Exception:
                pass
        conn_log.close()
        if _logf is not None:
            try:
                sys.stdout = sys.__stdout__
                _logf.close()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
