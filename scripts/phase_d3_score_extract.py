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

# ── cc113 ENDURTENGING — ARTIFACT-HAMUR ────────────────────────────────────────
# Fram að cc113 gat þessi adapter aðeins hlaðið D:\iter4a_*.lgb (154 eiginleikar,
# óhreyfðir frá 21.04) og stimplað 'iter4_final_v1'. Framleiðslan flippaði 06.08 á
# iter4r_20260805_reglaR_strukt (156) og adapterinn fylgdi ekki með — cc112 setti
# útgáfuhlið á skrifleiðina og keðjan hefur fallið viljandi síðan.
#
# ARTIFACT-HAMUR (load_models(artifact_dir=...)) speglar framleiðsluvélina
# rebuild_predictions_iter4.py lið fyrir lið. HELPER-FÖLLIN ERU EKKI AFRITUÐ:
# kvörðunar-kaskadinn (_conformal_halfwidths / _serving_offsets / _confidence_grade)
# og flokkaþröskuldarnir eru FLUTTIR INN úr precompute-vélinni sjálfri, svo næsta
# breyting þar berst hingað sjálfkrafa. Það var nákvæmlega lexía cc112: hlið sem
# ver mælinguna en ekki skrifleiðina, og tvö afrit sem drifu í sundur.
#
# ÁN artifact_dir er hegðunin ÓBREYTT bæti fyrir bæti (D3-lotan sögulega, 2026-04,
# symmetrískur conformal m/global-fallback, stimplar 'iter4_final_v1').
PRECOMPUTE_DIR = r"D:/verdmat-is/precompute"


def _prod():
    """Framleiðsluvélin sem skrifaði lifandi public.predictions. Lazy import: án
    artifact-hams má þessi adapter ekki krefjast precompute-trésins."""
    if PRECOMPUTE_DIR not in sys.path:
        sys.path.insert(0, PRECOMPUTE_DIR)
    import rebuild_predictions_iter4 as R  # noqa: E402
    return R


def load_models(artifact_dir=None, serving_json=None, hms_pkl=None,
                hms_sha16=None) -> dict:
    """Hlaða 12 boostera + kvörðunarlög.

    artifact_dir  — kandídat/lifandi artifact-mappa (D:\\model_artifacts\\<ver>);
                    None = sögulega iter4a-leiðin á D:\\ (ÓBREYTT hegðun).
    serving_json  — 3.3-framreiðslulagið (ósamhverf log-offsets), aðeins artifact-hamur.
    hms_pkl       — hms_classification_v1.pkl; gefur n_ibudareininga + flm_hlutfall
                    (eiginleikarnir tveir sem lyfta 154 -> 156). sha-hliðað.
    """
    out: dict = {}
    ad = Path(artifact_dir) if artifact_dir else None
    ver = ad.name if ad else None
    print(f"Loading boosters ({'artifact ' + ver if ad else 'live iter4a'}) ...")
    for grp in ("main", "summer"):
        for suffix in ("mean", "q025", "q100", "q500", "q900", "q975"):
            path = (ad / f"{ver}_{grp}_{suffix}.lgb") if ad \
                else (MODEL_DIR / f"iter4a_{grp}_{suffix}.lgb")
            if not path.exists():
                raise SystemExit(f"Missing model: {path}")
            out[f"{grp}_{suffix}"] = lgb.Booster(model_file=str(path))
    print(f"  loaded 12 boosters")

    with open(CALIB_JSON, "r", encoding="utf-8") as f:
        out["calibration"] = json.load(f)
    print(f"  segcal: {out['calibration']['version']}")
    conf_path = (ad / f"{ver}_conformal.json") if ad else CONFORMAL_JSON
    with open(conf_path, "r", encoding="utf-8") as f:
        out["conformal"] = json.load(f)
    print(f"  conformal: {out['conformal']['version']} "
          f"(method={out['conformal'].get('method', 'n/a')})")

    out["artifact_dir"] = str(ad) if ad else None
    out["model_version"] = ver or MODEL_VERSION
    out["calibration_version"] = (f"{ver}_conformal_v1+segcal_fb") if ad \
        else CALIBRATION_VERSION
    if serving_json:
        with open(serving_json, "r", encoding="utf-8") as f:
            out["serving"] = json.load(f)
        print(f"  serving-lag 3.3 (ósamhverft): {out['serving']['version']} "
              f"(sellur seg_reg={len(out['serving']['by_segment_region'])} "
              f"seg={len(out['serving']['by_segment'])})")

    # Verðmats-mánuðurinn er EIGINLEIKI (sale_year/sale_month) og verður að vera
    # sá sami og framleiðslan skoraði með, annars er punktmatið annað líkan-inntak.
    # Í artifact-ham er hann LESINN úr framleiðsluvélinni, ekki endurritaður hér.
    if ad:
        R = _prod()
        out["valuation_year"], out["valuation_month"] = R.VALUATION_YEAR, R.VALUATION_MONTH
    else:
        out["valuation_year"], out["valuation_month"] = VALUATION_YEAR, VALUATION_MONTH

    if hms_pkl:
        import hashlib
        sha = hashlib.sha256(Path(hms_pkl).read_bytes()).hexdigest()[:16]
        if hms_sha16 and sha != hms_sha16:
            raise SystemExit(f"HALT: hms-lind sha {sha} != {hms_sha16}")
        hms = pd.read_pickle(hms_pkl)[["fastnum", "n_ibudareininga", "flm_hlutfall"]].copy()
        hms["fastnum"] = hms["fastnum"].astype("int64")
        # Int32 -> float64 NaN-native, EINS OG Í ÞJÁLFUN (D2) og í rebuild-vélinni.
        hms["n_ibudareininga"] = pd.to_numeric(hms["n_ibudareininga"], errors="coerce")
        hms["flm_hlutfall"] = pd.to_numeric(hms["flm_hlutfall"], errors="coerce")
        out["hms"] = hms.set_index("fastnum")
        print(f"  hms-lind sha OK ({sha}) · {len(hms):,} fastnum")

    out["feature_names"] = out["main_mean"].feature_name()
    print(f"  feature count: {len(out['feature_names'])}")

    print("Loading CPI lookup + categorical mappings from training_data_v2 ...")
    td = pd.read_pickle(TRAINING_PKL)
    td["_yr"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.year
    td["_mn"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.month
    cpi_lookup = td.groupby(["_yr", "_mn"])["cpi_factor"].first().to_dict()
    out["cpi_factor"] = cpi_lookup.get(
        (out["valuation_year"], out["valuation_month"]),
        cpi_lookup[max(cpi_lookup.keys())],
    )
    print(f"  cpi_factor @ {out['valuation_year']}-{out['valuation_month']:02d}: "
          f"{out['cpi_factor']:.4f}")

    out["categorical_mappings"] = {}
    for cat in CATEGORICALS:
        if cat in td.columns and hasattr(td[cat], "cat"):
            out["categorical_mappings"][cat] = list(td[cat].cat.categories)

    # cc113: region_tier er EKKI dálkur sem lesinn er af eigninni í framleiðslunni —
    # hann er AFLEIDDUR úr matsvaediNUMER (algengasta gildið í þjálfunarrammanum,
    # 'Country' þar sem matsvæðið þekkist ekki). MÆLT 07.08: public.properties.region_tier
    # og þessi vörpun greinir á um 171 af 167.503 eignum, og matsvaedi_bucket um 1.158.
    # Þau eru bæði LÍKANS-EIGINLEIKAR (kategórísk) OG lykill kvörðunar-kaskadans, svo
    # frávik þar er annar heimur — sama tegund bilunar og cc112 stöðvaði, bara minni.
    # Kortið er aðeins byggt í artifact-ham; sögulega leiðin snertir það ekki.
    if ad:
        out["region_tier_map"] = (
            td.groupby("matsvaediNUMER")["region_tier"]
            .agg(lambda s: s.value_counts().idxmax()).to_dict())
    return out


def build_X_matrix(scor: pd.DataFrame, feat_names: list[str],
                   cat_map: dict[str, list],
                   valuation_year: int = None,
                   valuation_month: int = None) -> pd.DataFrame:
    """Vectorized iter4 feature-matrix construction. NaN-native.
    Maps phase_d3_insert_rows column names → model feature names.

    valuation_year/month sjálfgefið = mánuður D3-lotunnar (2026-04). Í artifact-ham
    er hann sendur inn úr models (2026-07) — sale_year/sale_month eru EIGINLEIKAR og
    verða að vera þeir sömu og framleiðslan skoraði með.
    """
    vy = VALUATION_YEAR if valuation_year is None else valuation_year
    vm = VALUATION_MONTH if valuation_month is None else valuation_month
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
        # cc113/cc78-D2 strúktúr-featururnar tvær (154 -> 156). Aðeins virkar þegar
        # hms-innspýtingin er á; annars eru dálkarnir ekki í `scor` OG feature-nöfnin
        # ekki í líkaninu, svo báðar hliðar lykkjunnar sleppa þeim.
        "n_ibudareininga": "n_ibudareininga",
        "flm_hlutfall": "flm_hlutfall",
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
        X["sale_year"] = float(vy)
    if "sale_month" in feat_names:
        X["sale_month"] = float(vm)
    if "age_at_sale" in feat_names:
        X["age_at_sale"] = float(vy) - scor["byggar"].astype("float64").to_numpy()
    if "has_extraction_data" in feat_names:
        X["has_extraction_data"] = 0

    # E2 full-path (VÉL 1): honor LLM-extraction feature columns when the caller
    # provides them in `scor` (e.g. from build_extraction_features). For the D3
    # batch (no such columns) this is a no-op and has_extraction_data stays 0,
    # preserving the original structured-only behaviour byte-for-byte.
    # cc113: n_ibudareininga/flm_hlutfall eru Í col_map og því sjálfkrafa STRÚKTÚR.
    # Það er ekki tilviljun heldur skilyrði: væru þeir utan þessa mengis myndi
    # E2-yfirlagið hér að neðan telja þá extraction-featurur og setja
    # has_extraction_data=1 á GRUNNLÍNUNNI — grunnlínan og full-leiðin yrðu þá
    # sama vigur og útdráttar-gapið mældist núll í hljóði.
    _structural = set(col_map) | set(CATEGORICALS) | {
        "sale_year", "sale_month", "age_at_sale", "has_extraction_data",
        "is_main_unit", "is_new_build", "LOD_FLM"}
    _ext_present = False
    for fn in feat_names:
        if fn in _structural or fn not in scor.columns:
            continue
        X[fn] = pd.to_numeric(scor[fn], errors="coerce").to_numpy(dtype="float64")
        _ext_present = True
    if _ext_present and "has_extraction_data" in feat_names:
        X["has_extraction_data"] = 1

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


def attach_hms_features(scor: pd.DataFrame, hms: pd.DataFrame) -> pd.DataFrame:
    """n_ibudareininga + flm_hlutfall inn á `scor` eftir fastnum (cc113).

    Speglar rebuild_predictions_iter4.build_master_frame: LEFT-samruni, raðir án
    hms-línu fá NaN (NaN-native, eins og í þjálfun D2). Skilar AFRITI — kallandinn
    má ekki fá hliðarverkun á sinn ramma."""
    fn = scor["fastnum"].astype("int64").to_numpy()
    out = scor.copy()
    out["n_ibudareininga"] = hms["n_ibudareininga"].reindex(fn).to_numpy()
    out["flm_hlutfall"] = hms["flm_hlutfall"].reindex(fn).to_numpy()
    return out


def mirror_derived_dims(scor: pd.DataFrame, models: dict) -> pd.DataFrame:
    """region_tier + matsvaedi_bucket AFLEIDD eins og í rebuild_predictions_iter4
    .build_master_frame, ekki lesin af public.properties (cc113).

    Bæði eru kategórískir LÍKANS-eiginleikar OG region_tier er lykill kvörðunar-
    kaskadans ({cc}|{region}), svo þau verða að vera reiknuð úr sömu heimild og
    framleiðslan notaði. Int64-kastið er ekki snyrtimennska: `_coerce_numeric` gerir
    matsvaedi_numer að float64 og "M" + astype(str) gæfi þá 'M85.0' — flokk sem er
    ekki til í þjálfunarvokabúlarnum og myndi lenda sem NaN á hverri einustu röð."""
    out = scor.copy()
    msv = pd.to_numeric(out["matsvaedi_numer"], errors="coerce").astype("Int64")
    out["region_tier"] = msv.map(models["region_tier_map"]).fillna("Country").astype(object)
    out["matsvaedi_bucket"] = ("M" + msv.astype(str)).astype(object)
    return out


def score(scor: pd.DataFrame, models: dict) -> pd.DataFrame:
    feat_names = models["feature_names"]
    cat_map = models["categorical_mappings"]
    cpi_f = models["cpi_factor"]
    conformal = models["conformal"]
    artifact = models.get("artifact_dir")
    vy = models.get("valuation_year", VALUATION_YEAR)
    vm = models.get("valuation_month", VALUATION_MONTH)

    if models.get("region_tier_map") is not None:
        scor = mirror_derived_dims(scor, models)
    if models.get("hms") is not None:
        scor = attach_hms_features(scor, models["hms"])

    X = build_X_matrix(scor, feat_names, cat_map, vy, vm)
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
        # Sögulega leiðin þarf aðeins mean (punkt) + q500 (miðgildi); artifact-hamur
        # þarf allar sex því segcal-fallbackið (D-flokkarnir) byggir á q025/q100/q900/q975.
        for suffix in (("mean", "q025", "q100", "q500", "q900", "q975") if artifact
                       else ("mean", "q500")):
            m = models[f"{group}_{suffix}"]
            preds[suffix] = m.predict(Xg, num_iteration=m.best_iteration)

        canon = Rg["canonical_code"].astype(str).to_numpy()
        region = Rg["region_tier"].astype(str).to_numpy()
        mn = preds["mean"]

        def to_kr(log_vec):
            return np.round((np.expm1(log_vec) / cpi_f) * 1000).astype(np.int64)

        if not artifact:
            # ── SÖGULEGA D3-LEIÐIN, ÓBREYTT ────────────────────────────────────
            q80 = np.empty(n, dtype=np.float64)
            q95 = np.empty(n, dtype=np.float64)
            for i in range(n):
                q80[i], q95[i] = conformal_q(canon[i], region[i], conformal)
            # Conformal PIs in log space — symmetric around mean prediction.
            lo80_kr, hi80_kr = to_kr(mn - q80), to_kr(mn + q80)
            lo95_kr, hi95_kr = to_kr(mn - q95), to_kr(mn + q95)
            grade = np.full(n, None, dtype=object)
            calib_src = np.full(n, None, dtype=object)
            calver = np.full(n, models["calibration_version"], dtype=object)
        else:
            # ── ARTIFACT-HAMUR: SPEGILL AF rebuild_predictions_iter4.score_and_shap ──
            # Hvert einasta kvörðunar-fall er FLUTT INN úr framleiðsluvélinni; hér er
            # engin endursögn á kaskadanum. Röðin er bindandi: 3.1-conformal (symmetrískt,
            # log-rúm) -> segcal þar sem sellu vantar -> to_kr -> 3.3-serving ofan á
            # RÚNNUÐU mean_kr -> flokkur af RÚNNUÐU bilunum. Að reikna flokkinn af
            # órúnnuðu bili gæfi annan staf en DB-ið geymir.
            R = _prod()
            cal = models["calibration"]["segments"]
            fb = cal.get("_global_fallback", {"k80": 1.0, "k95": 1.0})
            k80 = np.array([cal.get(c, fb)["k80"] for c in canon])
            k95 = np.array([cal.get(c, fb)["k95"] for c in canon])
            seg_lo80 = mn - k80 * (mn - preds["q100"])
            seg_hi80 = mn + k80 * (preds["q900"] - mn)
            seg_lo95 = mn - k95 * (mn - preds["q025"])
            seg_hi95 = mn + k95 * (preds["q975"] - mn)

            q80, q95, calib_src = R._conformal_halfwidths(conformal, canon, region)
            has_conf = ~np.isnan(q80)
            lo80 = np.where(has_conf, mn - q80, seg_lo80)
            hi80 = np.where(has_conf, mn + q80, seg_hi80)
            lo95 = np.where(has_conf, mn - q95, seg_lo95)
            hi95 = np.where(has_conf, mn + q95, seg_hi95)

            mean_kr = to_kr(mn)
            lo80_kr, hi80_kr = to_kr(lo80), to_kr(hi80)
            lo95_kr, hi95_kr = to_kr(lo95), to_kr(hi95)

            calver = np.full(len(Rg), models["calibration_version"], dtype=object)
            if models.get("serving") is not None:
                offs, srv_src = R._serving_offsets(models["serving"], canon, region)
                srv = ~np.isnan(offs["lo80"])
                lo80_kr = np.where(srv, np.round(mean_kr * np.exp(offs["lo80"])), lo80_kr).astype(np.int64)
                hi80_kr = np.where(srv, np.round(mean_kr * np.exp(offs["hi80"])), hi80_kr).astype(np.int64)
                lo95_kr = np.where(srv, np.round(mean_kr * np.exp(offs["lo95"])), lo95_kr).astype(np.int64)
                hi95_kr = np.where(srv, np.round(mean_kr * np.exp(offs["hi95"])), hi95_kr).astype(np.int64)
                calib_src = np.where(srv, srv_src, calib_src)
                calver = np.where(srv, models["serving"]["version"], calver)
                print(f"  {group}: serving-lag 3.3 á {int(srv.sum()):,} af {len(Rg):,} "
                      f"röðum · fallback (3.1/segcal) {int((~srv).sum()):,}")
            rel80 = (hi80_kr - lo80_kr) / np.maximum(to_kr(mn), 1)
            grade = R._confidence_grade(rel80, canon)

        pred_parts.append(pd.DataFrame({
            "fastnum": Rg["fastnum"].astype("int64").to_numpy(),
            "real_pred_mean": to_kr(mn),
            "real_pred_median": to_kr(preds["q500"]),
            "real_pred_lo80": lo80_kr,
            "real_pred_hi80": hi80_kr,
            "real_pred_lo95": lo95_kr,
            "real_pred_hi95": hi95_kr,
            "confidence_grade": grade,
            "calibration_source": calib_src,
            "model_group": group,
            "segment": canon,
            "model_version": models["model_version"],
            "calibration_version": calver,
            "predicted_at": pd.to_datetime(f"{vy}-{vm:02d}-01").date(),
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
