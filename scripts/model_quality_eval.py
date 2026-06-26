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
MAPE/bias/coverage are anchor-invariant per row (the cpi factor cancels), so this is
robust to the weekly CPI re-anchor moving sales_history_anchor_ym.

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

# MAPE/coverage flag thresholds (validate_metrics.py convention)
MAPE_FLAG_PP = 0.5
COV_FLAG_PP = 3.0
# validate_metrics held baseline (for context flags in `extra`)
BASELINE = {"mape": 7.00, "cov80": 73.1, "cov95": 92.7}

PRICE_BANDS = [(0, 40_000_000, "<40M"), (40_000_000, 70_000_000, "40-70M"),
               (70_000_000, 100_000_000, "70-100M"), (100_000_000, 9e18, ">=100M")]


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
    """MAPE/medAPE/cov80/cov95/bias on nominal/nominal de-anchored predictions.

    Mirrors validate_metrics.compute_metrics; anchor-invariant per row.
    """
    n = len(sub)
    if n == 0:
        return None
    f = (sub["cpi_sale"].astype(float) / sub["anchor_cpi"].astype(float)).values
    actual = sub["kaupverd_nominal"].astype(float).values
    pred = sub["real_pred_mean"].astype(float).values * f
    lo80 = sub["real_pred_lo80"].astype(float).values * f
    hi80 = sub["real_pred_hi80"].astype(float).values * f
    lo95 = sub["real_pred_lo95"].astype(float).values * f
    hi95 = sub["real_pred_hi95"].astype(float).values * f
    ape = np.abs(actual - pred) / actual
    in80 = (actual >= lo80) & (actual <= hi80)
    in95 = (actual >= lo95) & (actual <= hi95)
    return {
        "n": int(n),
        "mape": round(float(100 * ape.mean()), 4),
        "med_ape": round(float(100 * np.median(ape)), 4),
        "bias": round(float(100 * ((actual - pred) / actual).mean()), 4),  # signed MPE %
        "cov80": round(float(100 * in80.mean()), 4),
        "cov95": round(float(100 * in95.mean()), 4),
    }


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun", action="store_true", help="compute + print, no writes")
    args = ap.parse_args()
    print(f"=== model_quality_eval ({'DRYRUN' if args.dryrun else 'LIVE'}) — "
          f"EINKUNN 1 baseline/all_oos, cutoff {OOS_CUTOFF} ===")

    conn_log = open_connection()
    run_id = start_run(conn_log, "model_quality_eval")
    print(f"  pipeline_runs.id = {run_id}")
    conn_ro = None
    try:
        sid = start_step(conn_log, run_id, "compute_baseline_all_oos", 1)
        conn_ro = open_ro_conn()
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

        if args.dryrun:
            finish_step(conn_log, sid, 0, rowcount_after=len(df),
                        notes=f"dryrun: {len(rows)} segment rows, oos={len(df)}")
            finish_run(conn_log, run_id, "success",
                       {"dryrun": True, "score": "baseline", "sample_scope": "all_oos",
                        "oos_pairs": len(df), "segment_rows": len(rows),
                        "overall": overall, "flags": flags})
            print("\n  DRYRUN complete — no model_metrics writes.")
            return 0

        # ---- write model_metrics (baseline/all_oos) ----
        import psycopg2
        from psycopg2.extras import execute_values
        import json
        url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
        conn_w = psycopg2.connect(url); conn_w.autocommit = False
        payload = []
        for dim, val, m in rows:
            extra = flags if dim == "overall" else None
            payload.append((run_id, MODEL_VERSION, OOS_CUTOFF, "baseline", dim, val,
                            "all_oos", m["n"], m["mape"], m["med_ape"], m["bias"],
                            m["cov80"], m["cov95"], json.dumps(extra) if extra else None))
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
            print(f"\n  wrote {written} model_metrics rows (baseline/all_oos)")
        except Exception as e:
            conn_w.rollback(); conn_w.close()
            finish_step(conn_log, sid, 1, notes=f"write failed: {type(e).__name__}")
            finish_run(conn_log, run_id, "failed", {"step": "write", "error": str(e)[:500]})
            return 1
        conn_w.close()
        finish_step(conn_log, sid, 0, rowcount_after=len(payload),
                    notes=f"{len(payload)} baseline/all_oos rows")
        finish_run(conn_log, run_id, "success",
                   {"dryrun": False, "score": "baseline", "sample_scope": "all_oos",
                    "oos_pairs": len(df), "segment_rows": len(payload),
                    "overall": overall, "flags": flags})
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


if __name__ == "__main__":
    sys.exit(main())
