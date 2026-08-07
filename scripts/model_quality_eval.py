"""model_quality_eval.py — VÉL 1: out-of-sample model quality (two OOS scores).

Weekly engine producing model_metrics rows from the LIVE frozen predictions vs realized
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

OOS-SKILGREININGIN ER TVÖFÖLD (cc47, arkitektsákvörðun 2026-07-26). A single date
cutoff cannot serve both purposes at once, so the engine measures BOTH and labels them
apart. They are DISJOINT row sets and must NEVER be summed or averaged together:

  (a) AÐALTALA   sample_scope='holdout30' — the 30% stratified holdout (seed 20260716)
                 held out of train AND of conformal calibration. This is the
                 KVÖRÐUNARHEILINDI number: rows the deployed artifact provably never
                 saw. Membership is read off disk from the artifact folder
                 (<version>_holdout_rows.csv, FAERSLUNUMER key); seed/frac/train_end are
                 validated against <version>_manifest.json. oos_cutoff = manifest
                 train_end. DÓMSREGLA: cov80 < 80% => exit 2 + HALT to the architect.
  (b) HLIÐARTALA sample_scope='fresh_edge' — sales with THINGLYSTDAGS > manifest
                 data_end, i.e. the market strictly after the training data ended.
                 Small n by construction; a drift tripwire, not the headline.
                 oos_cutoff = manifest data_end.

Both are measured through the SAME deployed path (public.predictions de-anchored to the
sale month), so they answer "what does the artifact in production actually deliver",
NOT "what did the candidate score at training time". Those two differ: the training-time
holdout report scores each sale in its own time context, while the deployed path scores
each property once at the valuation month and CPI-rewinds. Do not quote one as the other.

MODEL VERSION IS NEVER HARD-CODED (cc47 rótarfix). It is read from
pipeline_config.model_version — the key flip_iter4r.py writes inside the flip txn
alongside model_pred_anchor_ym. A hard-coded version silently survives a model flip and
measures a cohort that no longer exists: run 76 (2026-07-20) wrote 0 rows with
exit_status='success' for exactly that reason and nobody noticed for six days.

ZERO ROWS IS A FAILURE, NOT A RESULT (cc47 rótarfix). Any scope that finds no pairs, and
any write that lands 0 rows, is a loud log line + exit 1. Silence is not evidence of calm.

Metric core mirrors validate_metrics.py:compute_metrics (MAPE real-space, coverage of
realized price within [lo,hi], bias). Point estimate = real_pred_mean.

Logged to pipeline_runs/steps via migration_helpers; writes public.model_metrics.

Exit codes: 0 = measured, cov80 >= 80%. 1 = measurement failed / zero rows / zero
written. 2 = measured AND written, but the DÓMSREGLA tripped (cov80 < 80%) — the run is
NOT a success, the architect owns the next move.

CLI:
  python scripts/model_quality_eval.py --dryrun   # compute + print, no writes
  python scripts/model_quality_eval.py            # compute + write model_metrics
  python scripts/model_quality_eval.py --force-model-version <x>   # rauðsönnun only
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

# ---- FASTI 1: model version. NOT a constant any more (cc47 rótarfix) --------------
# Read from pipeline_config at runtime; flip_iter4r.py writes it in the flip txn next to
# model_pred_anchor_ym, so the engine follows every future flip with no code edit.
MODEL_VERSION_KEY = "model_version"
ANCHOR_KEY = "model_pred_anchor_ym"  # model real-scale anchor (moves only on a flip)

# ---- FASTI 2: OOS-skilgreiningin, tvöföld (cc47) -----------------------------------
# Neither bound is written here. Both come off the artifact manifest on disk
# (D:\model_artifacts\<model_version>\<model_version>_manifest.json):
#   train_end -> oos_cutoff for scope (a) holdout30
#   data_end  -> oos_cutoff for scope (b) fresh_edge, AND the > bound of that scope
# Reading them means a retrain cannot leave the engine measuring a stale window.
ARTIFACT_ROOT = Path(r"D:\model_artifacts")
SCOPE_HOLDOUT = "holdout30"
SCOPE_FRESH = "fresh_edge"
HOLDOUT_MIN_ROWS = 200   # sanity floor: 30% of a real calib window is never this small
FRESH_MIN_ROWS = 1       # by construction tiny right after a retrain; 0 is still a failure

# ---- FASTAR 3+4: adapter freeze anchor / valuation month (E2 Haiku path only) -------
# ÁKVÖRÐUN 1 (2026-06-27), repointed to iter4r_20260716 (cc47). Source of truth is
# docs/fable_prep/audit/RETRAIN_ITER4R_2026-07-16.md, read off disk — not inferred:
#   §2 M5   -> model_pred_anchor_ym = '2026-08', written inside the flip txn 16.07 21:06Z
#   §4      -> predicted_at stays 2026-07-01 (verðmats-mánuður, not flip day)
# The adapter divides its real output by cpi[FREEZE]/cpi[PRED_VALUATION] to reproduce the
# stored nominal scale. Pinning to the FREEZE anchor (not the live pipeline_config value)
# keeps the adapter reproducing the frozen rows even after a weekly CPI re-anchor moves
# sales_history_anchor_ym past it.
# Þrep 7 flippsins (cc101): frosnu spárnar eru nú iter4r_20260805_reglaR_strukt,
# skrifaðar með --anchor-ym 2026-09 (flipp-txn setti model_pred_anchor_ym='2026-09');
# predicted_at stendur áfram á 2026-07-01 (verðmats-mánuðurinn, mælt í DB).
FREEZE_ANCHOR_YM = "2026-09"
PRED_VALUATION_YM = "2026-07"

# The E2/parity adapter (phase_d3_score_extract) still loads D:\iter4a_*.lgb and stamps
# 'iter4_final_v1'. After the iter4r flip that is a DIFFERENT model from the one in
# public.predictions, so rescoring through it would compare two models and call the
# difference "extraction gap". The paired block therefore refuses to run unless the
# adapter's stamp matches the live model_version — loudly, and booked, never silently.
ADAPTER_MODEL_VERSION = "iter4_final_v1"

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
# ---- GRUNNLÍNUR (þrep 7 flippsins, cc101): nýtt upphaf á D2+3.1+3.3 ----
# Heimildin er 3.2-specið á diski (AGUST_ENDURTHJALFUN_FASI2_SKREF31_32 §4 +
# SKREF33 §7): serían er NÝTT UPPHAF við flipp (FASI0 §4.4) og grunnlínan er
# §7-grunnur 3.3-auditsins — framreiðslurammi, frosni kohorturinn, ekki
# validate_metrics-grunnurinn gamli. Flags mæla frávik frá þessum grunni.
BASELINE = {"mape": 8.23, "cov80": 81.58, "cov95": 96.69}          # holdout30 (n=847)
BASELINE_FRESH = {"mape": 11.59, "cov80": 83.48, "cov95": 95.58}   # fresh_edge (n=339)

# ---- BIAS-PER-HÓLF vöktunarlínan (3.2-spec §4.3, bindandi forskrift) ----
# (a) src_R='R_gerd' · (b) src_R='notkun' ∧ cc_R==cc_gamalt ·
# (c1) src_R='notkun' ∧ cc_R≠cc_gamalt. Hólfin krefjast flokkunar-ættarinnar:
# cc_source úr properties_class_cc78_staging (flokkunar-staging flippsins) og
# gamla canonical_code úr properties_canonical_pre_cc78 (R3-rollback-akkerið).
# Báðar töflur eru varanleg flipp-artifact; hverfi þær er hólfalínan HÁVÆRT
# gat í skilunum, aldrei þögul núll (sjá segments()).
# Viðvörunarmörk skv. GO-bréfi §3: |bias(b)| > 4,0 pp flaggar HÁTT (ekki HALT).
BIAS_B_FLAG_PP = 4.0
# Upphafslínan (holdout30, 3.2-spec §4.3): (a) +5,57 n=96 · (b) +2,45 n=484 ·
# (c1) +1,42 n=265 — bókuð í extra til samanburðar í hverri viku.
R_SCOPE_UPPHAF = {"a_r_gerd": 5.57, "b_notkun_ohreyfd": 2.45, "c1_notkun_hreyfd": 1.42}

# ---- VEIKU BLETTIRNIR FJÓRIR (GO-bréf §5) sem fastar vöktunarlínur ----
# Engin n-gólf: lágt n er hluti merkisins og bókast með. Grunnlínur (cov80/n)
# af GO-bréfi §5, framreiðslurammi 05.08 — aðgerð aðeins ef mynstur styrkist
# á vaxandi n.
VEIKIR_BLETTIR_UPPHAF = {
    "sfh_rvk_core": {"cov80": 64.7, "n": 17},
    "r_gerd_rvk_core": {"cov80": 59.1, "n": 22},
    "undir_40m": {"cov80": 72.1, "n": 43},
    "apt_attic": {"cov80": 60.0, "n": 10},
}

# ---- VAKTAREIGNIR í weekly-skil (þrep 7, GO 07.08) ----
# Ástæða 2013952: GO-bréfs-prófeign flippsins + ásett verð 26% yfir mati
# (174,0 M vs mat 138,0 M — 4,5 M yfir hi95) + cc106-greiningin send út.
# Vikulega: ásett verð + verðbreytingar + virk/horfin; við þinglýsingu:
# kaupverð vs bókaða matið m/fráviki.
VAKTAREIGNIR = [
    {"fastnum": 2013952, "mat_ref_kr": 138_000_000,
     "astaeda": "GO-bréfs prófeign flippsins · ásett 26% yfir mati · cc106-greining send út"},
]

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


class MeasurementFailure(RuntimeError):
    """A measurement that produced nothing. Distinguished from a crash so main() can book
    it as a FAILED run and exit 1 instead of writing an empty 'success' (cc47)."""


def loud(msg: str) -> None:
    """A line that must survive skimming a 40 KB log. Used only for failures/HALTs."""
    bar = "!" * 78
    print(f"\n{bar}\n!! {msg}\n{bar}\n")


def read_model_version(conn, override: str | None = None) -> str:
    """Live model version from pipeline_config (cc47 rótarfix — never hard-coded).

    `override` exists ONLY for the rauðsönnun (--force-model-version): pointing the engine
    at a name that does not exist must make it fail loudly, not return a quiet zero.
    """
    if override:
        print(f"  model_version: '{override}' (--force-model-version — RAUÐSÖNNUN, "
              f"pipeline_config bypassed)")
        return override
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM public.pipeline_config WHERE key=%s",
                    (MODEL_VERSION_KEY,))
        row = cur.fetchone()
    if row is None or not row[0]:
        raise MeasurementFailure(
            f"pipeline_config missing '{MODEL_VERSION_KEY}' — refusing to guess a model "
            f"version. The flip writes this key; if it is absent the flip is incomplete.")
    print(f"  model_version: '{row[0]}' (pipeline_config.{MODEL_VERSION_KEY})")
    return row[0]


def read_manifest(model_version: str) -> dict:
    """Training manifest off disk — the source for train_end / data_end / holdout seed.

    Not inferred and not duplicated as a constant: a retrain rewrites this file, so the
    OOS window follows the artifact automatically. Missing manifest = measurement failure,
    because guessing the window would silently mislabel every row written.
    """
    import json
    p = ARTIFACT_ROOT / model_version / f"{model_version}_manifest.json"
    if not p.exists():
        raise MeasurementFailure(f"manifest not found: {p} — cannot resolve the OOS window "
                                 f"for model_version='{model_version}'")
    mf = json.loads(p.read_text(encoding="utf-8"))
    for k in ("train_end", "data_end", "holdout_seed", "holdout_frac"):
        if k not in mf:
            raise MeasurementFailure(f"{p.name} missing '{k}'")
    print(f"  manifest: train_end={mf['train_end']} data_end={mf['data_end']} "
          f"holdout={mf['holdout_frac']:.0%} seed={mf['holdout_seed']} "
          f"n_features={mf.get('n_features')}")
    return mf


def read_holdout_faerslunumer(model_version: str, manifest: dict) -> list[int]:
    """FAERSLUNUMER of the 30% holdout, read off the artifact folder (cc47 scope (a)).

    holdout_rows.csv is written by precompute/holdout_eval.py from predictions.pkl
    calib_role=='holdout' AFTER the same filters the training report used (onothaefur=0,
    not is_suspect_comparable). Keyed on FAERSLUNUMER (the sale PK) rather than FASTNUM: a
    property with two sales in the window would otherwise pull in a sale that WAS in
    calibration and quietly contaminate the held-out set.
    """
    p = ARTIFACT_ROOT / model_version / f"{model_version}_holdout_rows.csv"
    if not p.exists():
        raise MeasurementFailure(
            f"holdout rows not found: {p} — scope '{SCOPE_HOLDOUT}' is undefined without "
            f"the membership list. Re-run precompute/holdout_eval.py for this artifact.")
    h = pd.read_csv(p)
    for c in ("FAERSLUNUMER", "calib_role"):
        if c not in h.columns:
            raise MeasurementFailure(f"{p.name} missing column '{c}'")
    bad = set(h["calib_role"].unique()) - {"holdout"}
    if bad:
        raise MeasurementFailure(f"{p.name} contains non-holdout calib_role: {sorted(bad)}")
    fnr = sorted({int(x) for x in h["FAERSLUNUMER"]})
    print(f"  holdout membership: {len(fnr)} FAERSLUNUMER from {p.name} "
          f"(seed {manifest['holdout_seed']}, {manifest['holdout_frac']:.0%} stratified)")
    return fnr


# Shared SELECT for both scopes. anchor_cpi is passed IN as a parameter, deliberately NOT
# joined as `CROSS JOIN (SELECT cpi ... WHERE year_month = (SELECT value ...))`: if the
# anchor month were absent from cpi_index that CROSS JOIN silently annihilates every row
# and the engine reports a clean zero. That is exactly how run 76 died. read_model_anchor_cpi
# resolves the anchor first and raises on a miss, so the failure is loud and located.
_OOS_SELECT = """
    SELECT s.fastnum, s.faerslunumer, s.thinglystdags, s.kaupverd_nominal,
           p.real_pred_mean, p.real_pred_lo80, p.real_pred_hi80,
           p.real_pred_lo95, p.real_pred_hi95,
           cs.cpi AS cpi_sale, %(anchor_cpi)s::numeric AS anchor_cpi,
           pr.matsvaedi_numer, pr.canonical_code, pr.is_new_build, pr.region_tier,
           -- 3.2-spec §4.3: flokkunar-ættin fyrir bias-per-hólf línuna. LEFT JOIN:
           -- fastnum utan flipp-staging (nýjar eignir) fá NULL og falla utan hólfa.
           cls.cc_source, gam.canonical_code AS canonical_pre
    FROM public.predictions p
    JOIN public.sales_history s ON s.fastnum = p.fastnum
    JOIN public.properties pr ON pr.fastnum = p.fastnum
    LEFT JOIN public.cpi_index cs ON cs.year_month = to_char(s.thinglystdags, 'YYYY-MM')
    LEFT JOIN public.properties_class_cc78_staging cls ON cls.fastnum = p.fastnum
    LEFT JOIN public.properties_canonical_pre_cc78 gam ON gam.fastnum = p.fastnum
    WHERE p.model_version = %(mv)s
      AND s.onothaefur = 0          -- arm's-length only; onothaefur=1 are non-market
                                    -- (gifts/partial transfers) and would wreck MAPE/bias
      AND s.kaupverd_nominal IS NOT NULL AND s.kaupverd_nominal > 0
      AND p.real_pred_mean IS NOT NULL
"""


def fetch_oos(conn, model_version: str, anchor_cpi: float, scope: str,
              manifest: dict, holdout_fnr: list[int] | None) -> pd.DataFrame:
    """Pull (prediction, sale) pairs for ONE scope, with de-anchor inputs + segment dims.

    scope='holdout30'  -> rows whose FAERSLUNUMER is in the artifact holdout list (a)
    scope='fresh_edge' -> rows thinglyst strictly after manifest data_end (b)

    The two are disjoint: data_end is the last day in the training frame, so no holdout
    row can be on the fresh edge. main() asserts that rather than trusting it.
    """
    params: dict = {"anchor_cpi": anchor_cpi, "mv": model_version}
    if scope == SCOPE_HOLDOUT:
        params["fnr"] = holdout_fnr
        sql = _OOS_SELECT + "      AND s.faerslunumer = ANY(%(fnr)s)\n"
    elif scope == SCOPE_FRESH:
        params["edge"] = manifest["data_end"]
        sql = _OOS_SELECT + "      AND s.thinglystdags > DATE %(edge)s\n"
    else:
        raise ValueError(f"unknown scope {scope!r}")
    with conn.cursor() as cur:
        cur.execute(sql, params)
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


# Overall metric = residential DWELLINGS only. Summerhouses (and any non-dwelling) are
# out-of-domain for the iter4 hedonic model — at n≈59 they are ~27% of total OOS error
# (cheap rural cabins predicted at urban prices: e.g. real 4.7M -> pred 65M) and their
# conformal coverage collapses (cov80≈30%). They are still MEASURED as their own segment;
# they are just excluded from the headline 'overall' (base rule, 2026-06-28). iter4 stays
# frozen — this is metric SCOPING, not a model change.
APT_PREFIX = "APT_"
SERBYLI_CODES = {"SFH_DETACHED", "ROW_HOUSE", "SEMI_DETACHED"}
CAPITAL_TIERS = {"RVK_core", "Capital_sub"}


def _is_apt(cc):
    return isinstance(cc, str) and cc.startswith(APT_PREFIX)


def _is_residential(cc):
    """Dwelling for valuation: apartment or sérbýli. Excludes SUMMERHOUSE + non-dwelling."""
    return _is_apt(cc) or cc in SERBYLI_CODES


def segments(df: pd.DataFrame):
    """Yield (segment_dim, segment_value, sub) for every breakdown.

    'overall' is RESIDENTIAL DWELLINGS ONLY (summerhouse + non-dwelling excluded — base
    rule). The 'region_type' dim is the /ops core-market view: capital apartments are the
    headline (the blended overall otherwise hides that the core market is ~10.8% MAPE, not
    ~16.9%); summerhouse is measured but isolated.
    """
    cc = df["canonical_code"]
    rt = df["region_tier"]
    is_apt = cc.apply(_is_apt)
    is_resi = cc.apply(_is_residential)
    is_serbyli = cc.isin(SERBYLI_CODES)
    is_summer = cc == "SUMMERHOUSE"
    is_cap = rt.isin(CAPITAL_TIERS)

    # overall = residential dwellings (the headline model-quality number)
    yield ("overall", "", df[is_resi])

    # region × type — so the blended overall never hides the core market on /ops
    for val, mask in [
        ("capital_apt", is_cap & is_apt),               # höfuðborg · íbúðir (AÐAL/core)
        ("rvk_core_apt", (rt == "RVK_core") & is_apt),
        ("capital_sub_apt", (rt == "Capital_sub") & is_apt),
        ("capital_serbyli", is_cap & is_serbyli),
        ("country_resi", ~is_cap & is_resi),            # landsbyggð íbúðarhúsnæði
        ("summerhouse", is_summer),                     # sumarhús — measured, isolated
    ]:
        sub = df[mask]
        if len(sub) > 0:
            yield ("region_type", val, sub)

    # hood (matsvaedi) — only segments with >= 10 pairs (stable medians)
    for mv, sub in df.dropna(subset=["matsvaedi_numer"]).groupby("matsvaedi_numer"):
        if len(sub) >= 10:
            yield ("hood", str(int(mv)), sub)
    # property type
    for c, sub in df.dropna(subset=["canonical_code"]).groupby("canonical_code"):
        if len(sub) >= 10:
            yield ("property_type", str(c), sub)
    # price band
    nom = df["kaupverd_nominal"].astype(float)
    for lo, hi, label in PRICE_BANDS:
        sub = df[(nom >= lo) & (nom < hi)]
        if len(sub) >= 10:
            yield ("price_band", label, sub)
    # new build
    for flag, sub in df.dropna(subset=["is_new_build"]).groupby("is_new_build"):
        yield ("new_build", "true" if flag else "false", sub)

    # ---- bias-per-hólf (3.2-spec §4.3, inn við flipp) ----
    # (a) R_gerd · (b) notkun óhreyfð (cc==gamalt) · (c1) notkun hreyfð.
    # Byggir á flokkunar-ættinni (cc_source + canonical_pre) úr flipp-töflunum;
    # vanti hana alfarið er það HÁVÆRT gat — bókað í main(), aldrei þögul núll.
    if "cc_source" in df.columns:
        src = df["cc_source"]
        yield ("r_scope", "a_r_gerd", df[src == "R_gerd"])
        er_notkun = src == "notkun"
        ohreyfd = er_notkun & (df["canonical_code"] == df["canonical_pre"])
        yield ("r_scope", "b_notkun_ohreyfd", df[ohreyfd])
        yield ("r_scope", "c1_notkun_hreyfd", df[er_notkun & ~ohreyfd])

    # ---- veiku blettirnir fjórir (GO-bréf §5) — engin n-gólf, n er hluti merkisins ----
    yield ("veikur_blettur", "sfh_rvk_core",
           df[(cc == "SFH_DETACHED") & (rt == "RVK_core")])
    if "cc_source" in df.columns:
        yield ("veikur_blettur", "r_gerd_rvk_core",
               df[(df["cc_source"] == "R_gerd") & (rt == "RVK_core")])
    nom_vb = df["kaupverd_nominal"].astype(float)
    yield ("veikur_blettur", "undir_40m", df[nom_vb < 40_000_000])
    yield ("veikur_blettur", "apt_attic", df[cc == "APT_ATTIC"])


# ======================================================================
# EINKUNN 2 (full) — paired OOS, Haiku extraction (SKREF D)
# ======================================================================
def fetch_paired_oos(conn, model_version: str, oos_cutoff: str) -> pd.DataFrame:
    """OOS sales (onothaefur=0, after cutoff) that have a listing description.

    One row per (fastnum, sale); lysing = most-recent listing for that fastnum.
    Paired/E2 keeps the single-cutoff window (manifest train_end): it measures the
    extraction CONTRIBUTION, a within-subset delta, not the headline calibration number.
    """
    sql = """
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
    WHERE p.model_version = %(mv)s
      AND s.thinglystdags > DATE %(cutoff)s
      AND s.onothaefur = 0
      AND s.kaupverd_nominal IS NOT NULL AND s.kaupverd_nominal > 0
    ORDER BY s.fastnum, s.thinglystdags DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"mv": model_version, "cutoff": oos_cutoff})
        cols = [d[0] for d in cur.description]
        return _coerce_numeric(pd.DataFrame(cur.fetchall(), columns=cols))


def fetch_parity_sample(conn, n: int, model_version: str, oos_cutoff: str) -> pd.DataFrame:
    """Sample OOS fastnums with structured cols + FROZEN real_pred_median (D2 gate)."""
    sql = """
    SELECT DISTINCT ON (s.fastnum)
           s.fastnum, p.real_pred_median AS frozen_median,
           pr.einflm, pr.lod_flm, pr.byggar, pr.matsvaedi_numer, pr.matsvaedi_bucket,
           pr.region_tier, pr.canonical_code, pr.unit_category, pr.is_main_unit,
           pr.is_new_build, pr.postnr, pr.lat, pr.lng, pr.landeign_nr
    FROM public.predictions p
    JOIN public.sales_history s ON s.fastnum = p.fastnum
    JOIN public.properties pr ON pr.fastnum = p.fastnum
    WHERE p.model_version = %(mv)s
      AND s.thinglystdags > DATE %(cutoff)s AND s.onothaefur = 0
      AND p.real_pred_median IS NOT NULL
    ORDER BY s.fastnum
    LIMIT %(lim)s
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"mv": model_version, "cutoff": oos_cutoff, "lim": int(n)})
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


def vaktareign_skil(conn, v: dict) -> dict:
    """Vaktareign í weekly-skil (þrep 7): ásett verð + verðbreytingar + virk/horfin
    úr lifandi vöktuninni, og við þinglýsingu kaupverð vs bókaða matið m/fráviki.
    Allt SELECT — engin skrif. Villa í vaktareign fellir ALDREI mælinguna sjálfa."""
    fn = int(v["fastnum"])
    out = {"fastnum": fn, "astaeda": v["astaeda"], "mat_ref_kr": v["mat_ref_kr"]}
    with conn.cursor() as cur:
        cur.execute("""
            SELECT source, source_listing_id, price_amount, asett_verd_dags::text,
                   er_fjarveru_flaggad, last_seen_at::date::text
            FROM scraper.v_leit_listings
            WHERE fastnum=%s AND tenure='sale' AND er_nyjasta_birting
            ORDER BY last_seen_at DESC NULLS LAST LIMIT 1""", (fn,))
        row = cur.fetchone()
        if row is None:
            out["auglysing"] = "HORFIN úr lifandi leit (engin virk söluauglýsing)"
        else:
            src, slid, verd, dags, fjarvist, sedast = row
            out["auglysing"] = {
                "asett_kr": int(verd) if verd is not None else None,
                "asett_dags": dags, "heimild": src,
                "stada": "fjarvistarflögguð" if fjarvist else "virk",
                "sidast_sed": sedast,
            }
            cur.execute("""
                SELECT observed_at::date::text, price_amount
                FROM scraper.listing_price_history
                WHERE source=%s AND source_listing_id=%s
                ORDER BY observed_at""", (src, slid))
            ph = cur.fetchall()
            verdrod = []
            for d, p in ph:
                if not verdrod or verdrod[-1][1] != p:
                    verdrod.append((d, int(p) if p is not None else None))
            out["verdbreytingar"] = (
                [f"{d}: {p:,} kr" for d, p in verdrod] if len(verdrod) > 1
                else "engin verðbreyting mæld")
        # Þinglýsing EFTIR flipp-daginn: kaupverð vs bókaða matið.
        cur.execute("""
            SELECT thinglystdags::text, kaupverd_nominal
            FROM public.sales_history
            WHERE fastnum=%s AND onothaefur=0 AND thinglystdags >= DATE '2026-08-06'
            ORDER BY thinglystdags DESC LIMIT 1""", (fn,))
        sala = cur.fetchone()
        if sala:
            dags, kaup = sala
            fravik = 100.0 * (float(kaup) - v["mat_ref_kr"]) / v["mat_ref_kr"]
            out["thinglyst"] = {"dags": dags, "kaupverd_kr": int(kaup),
                                "fravik_fra_mati_pct": round(fravik, 2)}
        else:
            out["thinglyst"] = "óselt (engin þinglýsing frá flipp-degi)"
        cur.execute("SELECT real_pred_mean FROM public.v_current_predictions WHERE fastnum=%s", (fn,))
        m = cur.fetchone()
        out["lifandi_mat_kr"] = int(m[0]) if m and m[0] is not None else None
    return out


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
    ap.add_argument("--force-model-version", default=None,
                    help="RAUÐSÖNNUN ONLY: bypass pipeline_config and measure this version. "
                         "Pointing it at a name that does not exist MUST exit non-zero.")
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
          f"tvöföld OOS: '{SCOPE_HOLDOUT}' (aðaltala) + '{SCOPE_FRESH}' (hliðartala) ===")

    conn_log = open_connection()
    run_id = start_run(conn_log, "model_quality_eval")
    print(f"  pipeline_runs.id = {run_id}")
    conn_ro = None
    try:
        conn_ro = open_ro_conn()

        # Resolve the live model + its window BEFORE any query. Every one of these raises
        # MeasurementFailure on a miss — the engine must never fall through to a default
        # and produce a confident number about the wrong cohort (cc47 rótarfix).
        model_version = read_model_version(conn_ro, args.force_model_version)
        manifest = read_manifest(model_version)
        anchor_ym, anchor_cpi = read_model_anchor_cpi(conn_ro)
        print(f"  metrics de-anchor base: cpi[{anchor_ym}]={anchor_cpi:.3f} (ÁKVÖRÐUN 2)")

        # ---- D2 PARITY GATE: adapter baseline vs frozen predictions, then exit ----
        if args.parity:
            sid = start_step(conn_log, run_id, "parity_gate", 1)
            models = load_models_freeze_anchored(conn_ro)
            pdf = fetch_parity_sample(conn_ro, args.parity_n, model_version,
                                      manifest["train_end"])
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

        # ================= SKREF A: aðaltala — 30% holdout (kvörðunarheilindi) =========
        sid = start_step(conn_log, run_id, "compute_holdout30", 1)
        holdout_fnr = read_holdout_faerslunumer(model_version, manifest)
        df = fetch_oos(conn_ro, model_version, anchor_cpi, SCOPE_HOLDOUT,
                       manifest, holdout_fnr)
        n_missing_cpi = int(df["cpi_sale"].isna().sum())
        df = df[df["cpi_sale"].notna()].copy()
        print(f"\n  [{SCOPE_HOLDOUT}] pairs={len(df):,} of {len(holdout_fnr)} holdout sales "
              f"(missing-cpi dropped={n_missing_cpi})")
        # cc47 rótarfix: an empty measurement is a FAILURE. Previously this fell straight
        # through to a 0-row write booked as 'success'.
        if len(df) < HOLDOUT_MIN_ROWS:
            raise MeasurementFailure(
                f"scope '{SCOPE_HOLDOUT}' returned {len(df)} pairs (floor {HOLDOUT_MIN_ROWS}) "
                f"for model_version='{model_version}'. Either the version is not in "
                f"public.predictions, or the holdout list belongs to a different artifact.")

        rows = []  # (sample_scope, oos_cutoff, segment_dim, segment_value, metrics)
        overall = None
        for dim, val, sub in segments(df):
            m = compute_metrics(sub)
            if m is None:
                continue
            if dim == "overall":
                overall = m
            rows.append((SCOPE_HOLDOUT, manifest["train_end"], dim, val, m))
        if overall is None:
            raise MeasurementFailure(
                f"scope '{SCOPE_HOLDOUT}': {len(df)} pairs but NO residential dwellings — "
                f"the headline 'overall' segment is empty, so there is no aðaltala to judge.")

        # ================= SKREF B: hliðartala — ferskur jaðar =========================
        # Overall only, deliberately: at this n a segment breakdown would read as detail it
        # cannot support. Written with its own sample_scope + its own oos_cutoff so nothing
        # downstream can sum it into (a).
        edge_df = fetch_oos(conn_ro, model_version, anchor_cpi, SCOPE_FRESH, manifest, None)
        n_edge_missing_cpi = int(edge_df["cpi_sale"].isna().sum())
        edge_df = edge_df[edge_df["cpi_sale"].notna()].copy()
        print(f"  [{SCOPE_FRESH}] pairs={len(edge_df):,} (thinglyst > {manifest['data_end']}, "
              f"missing-cpi dropped={n_edge_missing_cpi})")
        if len(edge_df) < FRESH_MIN_ROWS:
            raise MeasurementFailure(
                f"scope '{SCOPE_FRESH}' returned {len(edge_df)} pairs after "
                f"{manifest['data_end']}. Zero fresh sales means the sales pipeline has "
                f"stalled — that is a finding, not an empty measurement.")

        # DISJOINTNESS: asserted, not assumed. data_end is the last day in the training
        # frame, so a holdout sale cannot also be on the fresh edge; if it can, one of the
        # two windows is mislabelled and both numbers are suspect.
        ov = set(df["faerslunumer"].dropna()) & set(edge_df["faerslunumer"].dropna())
        if ov:
            raise MeasurementFailure(
                f"scopes overlap on {len(ov)} faerslunumer (e.g. {sorted(ov)[:5]}) — "
                f"'{SCOPE_HOLDOUT}' and '{SCOPE_FRESH}' must be disjoint.")

        edge_overall = compute_metrics(edge_df[edge_df["canonical_code"].apply(_is_residential)])
        if edge_overall is None:
            raise MeasurementFailure(
                f"scope '{SCOPE_FRESH}': {len(edge_df)} pairs but no residential dwellings.")
        rows.append((SCOPE_FRESH, manifest["data_end"], "overall", "", edge_overall))

        # ---- console report ----
        print(f"\n  {'scope':<11} {'dim':<13} {'value':<16} {'n':>5} {'mape':>7} {'medape':>7} "
              f"{'bias':>7} {'cov80':>6} {'cov95':>6}")
        for scope, _cut, dim, val, m in rows:
            print(f"  {scope:<11} {dim:<13} {val:<16} {m['n']:>5} {m['mape']:>7.2f} "
                  f"{m['med_ape']:>7.2f} {m['bias']:>7.2f} {m['cov80']:>6.1f} {m['cov95']:>6.1f}")
        print(f"\n  AÐALTALA   [{SCOPE_HOLDOUT}] n={overall['n']}: MAPE {overall['mape']:.2f}% · "
              f"medAPE {overall['med_ape']:.2f}% · bias {overall['bias']:+.2f}% · "
              f"cov80 {overall['cov80']:.1f}% · cov95 {overall['cov95']:.1f}%")
        print(f"  HLIÐARTALA [{SCOPE_FRESH}] n={edge_overall['n']}: MAPE "
              f"{edge_overall['mape']:.2f}% · medAPE {edge_overall['med_ape']:.2f}% · bias "
              f"{edge_overall['bias']:+.2f}% · cov80 {edge_overall['cov80']:.1f}% · cov95 "
              f"{edge_overall['cov95']:.1f}%   (EKKI lagt við aðaltöluna)")

        # flags vs 3.2/3.3-grunnlínunum (nýtt upphaf flippsins — sjá BASELINE)
        flags = {
            "baseline": "3.3-audit §7 (D2+3.1+3.3, framreiðslurammi)",
            "mape_vs_baseline_pp": round(overall["mape"] - BASELINE["mape"], 2),
            "cov80_vs_baseline_pp": round(overall["cov80"] - BASELINE["cov80"], 2),
            "cov95_vs_baseline_pp": round(overall["cov95"] - BASELINE["cov95"], 2),
            "mape_flag": abs(overall["mape"] - BASELINE["mape"]) > MAPE_FLAG_PP,
            "cov80_flag": abs(overall["cov80"] - BASELINE["cov80"]) > COV_FLAG_PP,
            "cov95_flag": abs(overall["cov95"] - BASELINE["cov95"]) > COV_FLAG_PP,
        }
        print(f"\n  overall flags vs grunnlínu flippsins: {flags}")
        flags_fresh = {
            "baseline": "3.3-audit §7 fresh_edge",
            "cov80_vs_baseline_pp": round(edge_overall["cov80"] - BASELINE_FRESH["cov80"], 2),
            "cov95_vs_baseline_pp": round(edge_overall["cov95"] - BASELINE_FRESH["cov95"], 2),
            "cov80_flag": abs(edge_overall["cov80"] - BASELINE_FRESH["cov80"]) > COV_FLAG_PP,
        }
        print(f"  fresh_edge flags vs grunnlínu flippsins: {flags_fresh}")

        # ---- bias-per-hólf flaggið (3.2-spec §4.3): |bias(b)| > 4,0 pp = hávær lína ----
        r_holdout = {val: m for sc, _c, dim, val, m in rows
                     if dim == "r_scope" and sc == SCOPE_HOLDOUT}
        if not r_holdout:
            loud("BIAS-PER-HÓLF GAT: engin r_scope-lína mældist — flokkunar-ættin "
                 "(properties_class_cc78_staging / properties_canonical_pre_cc78) "
                 "vantar eða skilar engu. Hólfalínan er spec-skylda (3.2 §4.3).")
        else:
            b = r_holdout.get("b_notkun_ohreyfd")
            if b is None:
                loud("BIAS-PER-HÓLF GAT: hólf (b) notkun-óhreyfð er tómt á holdout30.")
            elif abs(b["bias"]) > BIAS_B_FLAG_PP:
                loud(f"BIAS-PER-HÓLF FLAGG: (b) notkun-óhreyfð bias = {b['bias']:+.2f}% "
                     f"(|·| > {BIAS_B_FLAG_PP} pp, n={b['n']}; upphaf +2,45).")
                print("  Túlkunarlykill (3.2-spec §4.3): vaxi (b)-VANMATIÐ er það REK; "
                      "kólni markaðurinn inn í spálínuna sest það. Hávær lína, ekki HALT.")
            else:
                print(f"  bias-per-hólf (b) notkun-óhreyfð: {b['bias']:+.2f}% "
                      f"(n={b['n']}, mörk ±{BIAS_B_FLAG_PP} pp, upphaf +2,45) — innan marka")

        # ---- vaktareignir (þrep 7): aldrei fella mælinguna ----
        vaktir = []
        for v in VAKTAREIGNIR:
            try:
                vaktir.append(vaktareign_skil(conn_ro, v))
            except Exception as e:
                vaktir.append({"fastnum": v["fastnum"],
                               "villa": f"{type(e).__name__}: {str(e)[:200]}"})
        print("\n  VAKTAREIGNIR (weekly-skil):")
        for v in vaktir:
            print(f"    {v}")

        # ---- DÓMSREGLA (cc47): cov80 of the AÐALTALA below 80% is an architect HALT ----
        # Evaluated here so the verdict rides along in every write below, but acted on
        # (exit 2) only after the metrics are safely persisted — the measurement must
        # survive the halt, otherwise the halt destroys its own evidence.
        halt_cov80 = overall["cov80"] < 80.0
        verdict = {
            "rule": "cov80(aðaltala) >= 80%",
            "scope": SCOPE_HOLDOUT, "n": overall["n"], "cov80": overall["cov80"],
            "verdict": "HALT" if halt_cov80 else "PASS",
        }
        if halt_cov80:
            loud(f"DÓMSREGLA TRIPPED: cov80({SCOPE_HOLDOUT}) = {overall['cov80']:.1f}% "
                 f"< 80% á n={overall['n']}. HALT til arkitekts.")
            print("  Afleiðingar sem arkitekt á (EKKI gerðar sjálfkrafa):\n"
                  "    - /adferdafraedi þarf stöðumerkingu (grunnregla 13)\n"
                  "    - flýtt endurþjálfun skv. yfirlýstri reglu síðunnar\n"
                  "  Mælingin sjálf er skrifuð í model_metrics; keyrslan endar á exit 2.")
        finish_step(conn_log, sid, 0, rowcount_after=len(df),
                    notes=f"{SCOPE_HOLDOUT} n={overall['n']} cov80={overall['cov80']} "
                          f"| {SCOPE_FRESH} n={edge_overall['n']} cov80={edge_overall['cov80']} "
                          f"| dómsregla={verdict['verdict']}")

        # ---- SKREF D: paired OOS — E1 rescored + E2 full + gap (Haiku) ----
        paired_rows = []          # (score_type, metrics) overall, sample_scope='paired_oos'
        paired_summary = {}
        selection = {}
        # cc47: the adapter still loads iter4a + stamps ADAPTER_MODEL_VERSION. Once the live
        # model differs, an E2 "gap" would be the distance between two MODELS wearing an
        # extraction label. Refuse loudly and book it rather than publish that number.
        if not args.skip_paired and ADAPTER_MODEL_VERSION != model_version:
            sid2 = start_step(conn_log, run_id, "compute_paired", 2)
            loud(f"PAIRED/E2 SKIPPED: adapter (phase_d3_score_extract) scores "
                 f"'{ADAPTER_MODEL_VERSION}' but live model_version is '{model_version}'. "
                 f"A gap measured across two models is not an extraction gap.")
            paired_summary = {"paired_skipped": "adapter_model_mismatch",
                              "adapter_model_version": ADAPTER_MODEL_VERSION,
                              "live_model_version": model_version}
            finish_step(conn_log, sid2, 1,
                        notes=f"paired SKIPPED: adapter={ADAPTER_MODEL_VERSION} != "
                              f"live={model_version} (E1 unaffected)")
        elif not args.skip_paired:
            sid2 = start_step(conn_log, run_id, "compute_paired", 2)
            # E1-VÖRN: the proven aðaltala is already computed in `rows`. A paired/Haiku
            # failure (import, auth, all-fail, etc.) must NEVER abort the run before the E1
            # write. Wrap the whole paired block so any error logs loudly, marks the step
            # failed, and falls through to the E1 write below.
            try:
                models = load_models_freeze_anchored(conn_ro)
                cpi_lookup = fetch_cpi_lookup(conn_ro)
                pdf = fetch_paired_oos(conn_ro, model_version, manifest["train_end"])
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
                # SELECTION: aðaltala (frozen holdout, overall) vs baseline/paired_oos
                # (rescored). Both use the cpi[model_pred_anchor_ym] de-anchor (ÁKVÖRÐUN 2)
                # → comparable. `sel_verdict`, NOT `verdict`: the latter holds the dómsregla
                # and must reach the write untouched.
                bp = scores.get("baseline")
                if overall and bp:
                    d_med = round(bp["med_ape"] - overall["med_ape"], 2)
                    sel_verdict = "REPRESENTATIVE" if abs(d_med) <= 2.0 else "SELECTION-SKEWED"
                    selection = {
                        "reference_scope": SCOPE_HOLDOUT,
                        "reference_n": overall["n"], "paired_n": bp["n"],
                        "medape_reference": overall["med_ape"], "medape_paired": bp["med_ape"],
                        "mape_reference": overall["mape"], "mape_paired": bp["mape"],
                        "bias_reference": overall["bias"], "bias_paired": bp["bias"],
                        "medape_delta": d_med, "verdict": sel_verdict,
                        "note": (f"reference is the {SCOPE_HOLDOUT} aðaltala from frozen "
                                 "predictions; baseline/paired_oos is re-scored "
                                 "structured-only; both de-anchored at "
                                 "cpi[model_pred_anchor_ym] (ÁKVÖRÐUN 2) → comparable. "
                                 "REPRESENTATIVE: gap is pure extraction contribution; "
                                 "SELECTION-SKEWED: paired subset differs from the universe."),
                    }
                    print(f"\n  SELECTION ({sel_verdict}): medAPE {SCOPE_HOLDOUT} "
                          f"{overall['med_ape']:.2f} vs paired {bp['med_ape']:.2f} "
                          f"(Δ{d_med:+.2f}); MAPE {overall['mape']:.2f} vs {bp['mape']:.2f}  "
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

        run_summary = {
            "model_version": model_version,
            "manifest": {k: manifest[k] for k in ("train_end", "data_end",
                                                  "holdout_seed", "holdout_frac")},
            "anchor": {"key": ANCHOR_KEY, "ym": anchor_ym, "cpi": anchor_cpi},
            SCOPE_HOLDOUT: {"pairs": len(df), "overall": overall,
                            "oos_cutoff": manifest["train_end"], "flags": flags},
            SCOPE_FRESH: {"pairs": len(edge_df), "overall": edge_overall,
                          "oos_cutoff": manifest["data_end"], "flags": flags_fresh},
            "domsregla": verdict,
            "bias_per_holf": r_holdout,
            "vaktareignir": vaktir,
            "paired_summary": paired_summary, "selection": selection,
        }

        if args.dryrun:
            finish_run(conn_log, run_id, "success", {"dryrun": True, **run_summary,
                                                     "paired": dict(paired_rows)})
            print("\n  DRYRUN complete — no model_metrics writes.")
            return 2 if halt_cov80 else 0

        # ---- write model_metrics (holdout30 + fresh_edge + paired baseline/full/gap) ----
        import psycopg2
        from psycopg2.extras import execute_values
        import json
        payload = []
        for scope, cutoff, dim, val, m in rows:
            # `extra` carries the dómsregla verdict on BOTH overall rows so a reader of a
            # single model_metrics row can tell whether that number was accepted, without
            # having to join back to pipeline_runs.
            extra = None
            if dim == "overall":
                extra = {"domsregla": verdict, "scope_role":
                         "AÐALTALA" if scope == SCOPE_HOLDOUT else "HLIÐARTALA",
                         "never_sum_with": SCOPE_FRESH if scope == SCOPE_HOLDOUT
                         else SCOPE_HOLDOUT}
                extra.update(flags if scope == SCOPE_HOLDOUT else flags_fresh)
            elif dim == "r_scope":
                # 3.2-spec §4.3: upphafslínan fylgir hverri hólfaröð + b-flaggmörkin.
                extra = {"upphaf_bias_pp": R_SCOPE_UPPHAF.get(val),
                         "flagg_regla": f"|bias(b)| > {BIAS_B_FLAG_PP} pp (hávær, ekki HALT)"}
            elif dim == "veikur_blettur":
                extra = {"upphaf": VEIKIR_BLETTIR_UPPHAF.get(val),
                         "regla": "aðgerð aðeins ef mynstur staðfestist á vaxandi n (GO-bréf §5)"}
            payload.append((run_id, model_version, cutoff, "baseline", dim, val,
                            scope, m["n"], m["mape"], m["med_ape"], m["bias"],
                            m["cov80"], m["cov95"], json.dumps(extra) if extra else None))
        for st, m in paired_rows:
            extra = ({"selection": selection, **paired_summary} if st == "baseline"
                     else (paired_summary if st == "gap" else None))
            payload.append((run_id, model_version, manifest["train_end"], st, "overall", "",
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
            # cc47 rótarfix #2b: a write that lands nothing is a failure, not a quiet
            # success. Rolled back so the run leaves no half-state behind.
            if written == 0:
                conn_w.rollback(); conn_w.close()
                raise MeasurementFailure(
                    f"model_metrics write affected 0 rows from a {len(payload)}-row payload")
            conn_w.commit()
            n_hold = sum(1 for r in rows if r[0] == SCOPE_HOLDOUT)
            n_edge = sum(1 for r in rows if r[0] == SCOPE_FRESH)
            print(f"\n  wrote {written} model_metrics rows "
                  f"({n_hold} {SCOPE_HOLDOUT} + {n_edge} {SCOPE_FRESH} + "
                  f"{len(paired_rows)} paired)")
        except MeasurementFailure:
            raise
        except Exception as e:
            conn_w.rollback(); conn_w.close()
            finish_run(conn_log, run_id, "failed", {"step": "write", "error": str(e)[:500]})
            return 1
        conn_w.close()
        finish_run(conn_log, run_id, "halt_cov80" if halt_cov80 else "success",
                   {"dryrun": False, **run_summary, "rows_written": len(payload)})
        return 2 if halt_cov80 else 0
    except MeasurementFailure as e:
        # An empty or undefined measurement. Loud, booked, exit 1 — the state this engine
        # used to report as a clean 'success' with 0 rows (run 76, 2026-07-20).
        loud(f"MÆLING SKILAÐI ENGU: {e}")
        finish_run(conn_log, run_id, "failed",
                   {"measurement_failure": str(e)[:500],
                    "model_version": args.force_model_version or "<pipeline_config>"})
        return 1
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
