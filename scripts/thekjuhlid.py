"""cc244 f.2 — ÞEKJUHLIÐ ÞJÁLFUN ↔ REKSTUR (P1 í D:\\_audit\\cc244_haed\\SKIL_CC244.md §4.2).

READ-ONLY: les pkl, líkans-artifact og DB í read-only session. Skrifar ekkert nema
valfrjálst --json úttak. EKKI tengt í næturkeyrslu (sjá SKIL cc244 f.2 um hvar).

Hvað það ver: cc244 fann að fjögur hæðar-features (merking_floor, building_max_floor,
is_top_floor, floor_fraction) eru ~100 % þakin í þjálfun en 100 % NaN í rekstri, af því að
engin skorunarleið leiddi þau nokkurn tíma. Holdout-tölurnar sáu það aldrei, því þær eru í
þjálfunarham. Þetta hlið ber NaN-hlutfall per feature í þjálfunar-X saman við rekstrar-X
hverrar skorunarleiðar:

  rebuild  — precompute/rebuild_predictions_iter4.build_master_frame + build_X_matrix
             (lotuskorun sem skrifar public.predictions)
  adapter  — scripts/phase_d3_score_extract.build_X_matrix í artifact-ham (VÉL-1; nætur-
             vélin og value_listings), grunnlína án extraction, inntak úr public.properties
  phase1a  — precompute/build_precompute.build_master_frame + _build_X_batch (Phase 1A)

FELL á feature f í leið L ef
  (a) þekja(þjálfun) ≥ 50 % og þekja(L) < 50 %, eða
  (b) |þekja(L) − þekja(þjálfun)| > 20 pp.

SAMBÆRILEGUR SAMANBURÐUR. Þekja þjálfunar er ekki hrátt hlutfall yfir allt þjálfunarmengið,
heldur VEGIN eftir samsetningu leiðarinnar í sellum (canonical_code × has_extraction_data):
    þekja_þjálfun(f | L) = Σ_sella  hlutur_L(sella) · þekja_þjálfun(f | sella)
Ástæður, báðar mældar 15.10.2026:
  * Rekstrargrunnlínan er has_extraction_data=0. Í þjálfun bera 23,8 % raða extraction, svo
    hrátt hlutfall lætur 48 extraction-features falla á (b), þótt NaN þar sé hannað.
    Í sama ham (has_extraction_data=0) er þekja þeirra ~0 bæði megin.
  * Úrtak eða leið með aðra tegundablöndu (t.d. aðeins fjölbýli) fengi annars gervifall á
    gated features eins og is_top_floor (72,6 % alls, 96,7 % í fjölbýli).
Engin hvítlisti: ef extraction-feature fyllist í rekstrargrunnlínu, eða fellur í þjálfun í
rekstrarham, bítur hliðið á það eins og á hvert annað feature.

rc: 0 = stenst · 1 = FELL · 2 = leið gat ekki smíðað X (mæling ekki gerð — telst ekki stenst).

Notkun (úr app-rót):
  python scripts/thekjuhlid.py                     # allar þrjár leiðir, líkan úr pipeline_config
  python scripts/thekjuhlid.py --leidir rebuild,adapter --model iter4r_20260805_reglaR_strukt
  python scripts/thekjuhlid.py --sjalfsprof        # falspróf á frosnu úrtaki cc244
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import psycopg2

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

HERE = Path(__file__).resolve().parent
PRECOMPUTE_DIR = r"D:/verdmat-is/precompute"
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
ARTIFACT_ROOT = Path(r"D:\model_artifacts")
TRAINING_PKL = Path(r"D:\training_data_v2.pkl")
HMS_PKL = Path(r"D:\hms_classification_v1.pkl")
HMS_SHA16 = "16d78e39d57cfcad"
URTAK_CC244 = Path(r"D:\_audit\cc244_haed\m01_urtak.json")

THR_HALF = 50.0     # (a) ≥ 50 % í þjálfun → verður að vera ≥ 50 % í rekstri
THR_DELTA = 20.0    # (b) |Δ þekju| > 20 pp
FLOOR = ["merking_floor", "building_max_floor", "is_top_floor", "floor_fraction"]
LEIDIR = ("rebuild", "adapter", "phase1a")


def log(*a):
    print(*a, flush=True)


def ro_conn():
    conn = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    conn.set_session(readonly=True, autocommit=True)
    return conn


def read_model_version() -> str:
    conn = ro_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM public.pipeline_config WHERE key='model_version'")
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        raise SystemExit("pipeline_config.model_version vantar")
    return row[0]


def _prod():
    if PRECOMPUTE_DIR not in sys.path:
        sys.path.insert(0, PRECOMPUTE_DIR)
    import rebuild_predictions_iter4 as R  # noqa: E402
    return R


# ---------------------------------------------------------------------------
# Þjálfunarhlið: þekja per sella (canonical_code × has_extraction_data)
# ---------------------------------------------------------------------------

def training_coverage(feats: list[str]):
    td = pd.read_pickle(TRAINING_PKL)
    td = td[td["canonical_code"].astype(str) != "SUMMERHOUSE"].copy()   # main-líkanið
    # = retrain_sales_model.py:165 (has_extraction_data er afleitt við þjálfun, ekki dálkur)
    td["has_extraction_data"] = td["extraction_success"].fillna(0).astype(int)
    cat_map = {c: list(td[c].cat.categories) for c in ("canonical_code", "matsvaedi_bucket",
               "region_tier", "unit_category") if c in td.columns and hasattr(td[c], "cat")}
    missing = [f for f in feats if f not in td.columns]
    if missing:
        raise SystemExit(f"features sem þjálfunar-pkl ber ekki: {missing}")
    key = td["canonical_code"].astype(str) + "|" + td["has_extraction_data"].astype(str)
    cov = td[feats].notna().groupby(key.to_numpy()).mean() * 100      # sella × feature
    raw = td[feats].notna().mean() * 100
    return cov, raw, len(td), cat_map


def serving_cells(cc: pd.Series, X: pd.DataFrame) -> pd.Series:
    hed = X["has_extraction_data"] if "has_extraction_data" in X.columns else pd.Series(0, index=X.index)
    hed = pd.to_numeric(pd.Series(np.asarray(hed), index=cc.index), errors="coerce").fillna(0).astype(int)
    return cc.astype(str).reset_index(drop=True) + "|" + hed.astype(str).reset_index(drop=True)


def gate(X: pd.DataFrame, cells: pd.Series, cov_tr: pd.DataFrame, raw_tr: pd.Series,
         gain: dict) -> tuple[pd.DataFrame, dict]:
    share = cells.value_counts(normalize=True)
    known = share[share.index.isin(cov_tr.index)]
    dropped = float(share[~share.index.isin(cov_tr.index)].sum())
    w = known / known.sum()
    tr_w = (cov_tr.loc[w.index].mul(w, axis=0)).sum(axis=0)
    serv = X.notna().mean() * 100
    T = pd.DataFrame({"gain_pct": pd.Series(gain), "thjalfun_hratt": raw_tr,
                      "thjalfun_vegid": tr_w, "rekstur": serv})
    T["delta_pp"] = T["rekstur"] - T["thjalfun_vegid"]
    fa = (T.thjalfun_vegid >= THR_HALF) & (T.rekstur < THR_HALF)
    fb = T.delta_pp.abs() > THR_DELTA
    T["fell"] = fa | fb
    T["regla"] = np.where(fa & fb, "a+b", np.where(fa, "a", np.where(fb, "b", "")))
    meta = {"n": int(len(X)), "hlutur_sella_utan_thjalfunar": dropped,
            "sellur": int(len(share)), "has_extraction_1_hlutur": float(
                cells.str.endswith("|1").mean())}
    return T, meta


def prenta(leid: str, T: pd.DataFrame, meta: dict, allt: bool):
    log(f"\n=== {leid}: n={meta['n']:,}  sellur={meta['sellur']}  "
        f"has_extraction_data=1: {meta['has_extraction_1_hlutur']*100:.1f} %  "
        f"hlutur utan þjálfunarsella: {meta['hlutur_sella_utan_thjalfunar']*100:.2f} %")
    S = T if allt else T[T.fell | (T.delta_pp.abs() > 5)]
    S = S.sort_values(["fell", "gain_pct"], ascending=[False, False])
    log(f"  {'feature':32s} {'gain%':>6s} {'þjálf.hrátt':>11s} {'þjálf.vegið':>11s} "
        f"{'rekstur':>8s} {'Δ pp':>7s}  dómur")
    for f, r in S.iterrows():
        d = f"FELL ({r.regla})" if r.fell else "ok"
        log(f"  {f:32s} {r.gain_pct:6.2f} {r.thjalfun_hratt:11.1f} {r.thjalfun_vegid:11.1f} "
            f"{r.rekstur:8.1f} {r.delta_pp:+7.1f}  {d}")
    n_f = int(T.fell.sum())
    log(f"  → {'FELL' if n_f else 'STENST'}: {n_f} af {len(T)} features"
        + (f" ({', '.join(T.index[T.fell])})" if n_f else "")
        + ("" if allt else "  [sýnd: föll + |Δ| > 5 pp; --allt fyrir öll]"))


# ---------------------------------------------------------------------------
# Rekstrarleiðirnar þrjár — hver smíðar X með SÍNUM eigin kóða (innflutt, ekki afritað)
# ---------------------------------------------------------------------------

def x_rebuild(feats, cat_map, fastnums=None):
    R = _prod()
    R.HMS_PKL = str(HMS_PKL)       # framleiðslan keyrir með --hms-pkl (156 features)
    resi = R.build_master_frame()
    resi = resi[~resi["canonical_code"].eq("SUMMERHOUSE")].reset_index(drop=True)
    if fastnums is not None:
        resi = resi[resi["fastnum"].astype("int64").isin(fastnums)].reset_index(drop=True)
    X = R.build_X_matrix(resi, feats, cat_map)
    return X, resi["canonical_code"], resi


def x_adapter(feats, cat_map, model_version):
    sys.path.insert(0, str(HERE))
    import phase_d3_score_extract as P  # noqa: E402
    models = P.load_models(artifact_dir=str(ARTIFACT_ROOT / model_version),
                           hms_pkl=str(HMS_PKL), hms_sha16=HMS_SHA16)
    if models["feature_names"] != feats:
        raise RuntimeError("adapter hleður annan feature-lista en main_mean líkansins")
    conn = ro_conn()
    try:
        with conn.cursor() as cur:
            # sama dálkaval og grunnlína VÉL-1 les af public.properties (model_quality_eval)
            cur.execute("""
                SELECT pr.fastnum, pr.einflm, pr.lod_flm, pr.byggar, pr.matsvaedi_numer,
                       pr.matsvaedi_bucket, pr.region_tier, pr.canonical_code, pr.unit_category,
                       pr.is_main_unit, pr.is_new_build, pr.postnr, pr.lat, pr.lng, pr.landeign_nr
                FROM public.properties pr
                JOIN public.v_current_predictions p ON p.fastnum = pr.fastnum
                WHERE p.model_group = 'main'""")
            cols = [d[0] for d in cur.description]
            scor = pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()
    for c in ("einflm", "lod_flm", "byggar", "matsvaedi_numer", "postnr", "lat", "lng", "landeign_nr"):
        scor[c] = pd.to_numeric(scor[c], errors="coerce")
    scor = scor.drop_duplicates("fastnum").reset_index(drop=True)
    scor = P.mirror_derived_dims(scor, models)       # = score() í artifact-ham
    scor = P.attach_hms_features(scor, models["hms"])
    X = P.build_X_matrix(scor, feats, cat_map, models["valuation_year"], models["valuation_month"])
    return X, scor["canonical_code"]


def x_phase1a(feats, cat_map):
    if PRECOMPUTE_DIR not in sys.path:
        sys.path.insert(0, PRECOMPUTE_DIR)
    import build_precompute as B  # noqa: E402
    resi = B.build_master_frame()
    resi = resi[~resi["canonical_code"].eq("SUMMERHOUSE")].reset_index(drop=True)
    X = B._build_X_batch(resi, feats, cat_map, None)
    return X, resi["canonical_code"]


# ---------------------------------------------------------------------------
# Sjálfspróf (falspróf) á frosnu úrtaki cc244
# ---------------------------------------------------------------------------

def _haed_fixture(fastnums: np.ndarray) -> pd.DataFrame:
    """PRÓFUNARFESTING, ekki lagfæring: hæðar-features leidd eins og
    D:\\build_training_data.py:313-356 (regex HHFFUU á properties_v2.merking;
    building_max_floor = max per landnum á FULLU properties_v2; is_top_floor/floor_fraction
    hlið á max ≥ 2). Lagfæringin sjálf á að vera eitt sameiginlegt fall (SKIL cc244 §4.1)."""
    rx = re.compile(r"^(\d{2})(\d{2})(\d{2})$")

    def mf(m):
        if not isinstance(m, str):
            return np.nan
        t = rx.match(m.strip())
        return int(t.group(2)) if t else np.nan
    pr = pd.read_pickle(r"D:\properties_v2.pkl").dropna(subset=["fastnum"]).copy()
    pr["fastnum"] = pr["fastnum"].astype("int64")
    pr["merking_floor"] = pr["merking"].apply(mf)
    bm = pr[pr.merking_floor.notna()].groupby("landnum")["merking_floor"].max().rename("building_max_floor")
    d = pr[["fastnum", "landnum", "merking_floor"]].merge(bm, on="landnum", how="left")
    multi = d.merking_floor.notna() & d.building_max_floor.notna() & (d.building_max_floor >= 2)
    d["is_top_floor"] = np.nan
    d.loc[multi, "is_top_floor"] = (d.loc[multi, "merking_floor"] == d.loc[multi, "building_max_floor"]).astype(float)
    d["floor_fraction"] = np.nan
    d.loc[multi, "floor_fraction"] = d.loc[multi, "merking_floor"] / d.loc[multi, "building_max_floor"]
    return d.drop_duplicates("fastnum").set_index("fastnum").reindex(fastnums)


def sjalfsprof(feats, cov_tr, raw_tr, cat_map, gain) -> int:
    fz = np.array(json.load(open(URTAK_CC244, encoding="utf-8"))["fastnum"], dtype="int64")
    log(f"\nSJÁLFSPRÓF á frosnu úrtaki cc244 ({URTAK_CC244.name}, n={len(fz):,}) — rebuild-leið")
    X0, cc, resi = x_rebuild(feats, cat_map, fastnums=set(fz.tolist()))
    cells = serving_cells(cc, X0)
    F = _haed_fixture(resi["fastnum"].astype("int64").to_numpy())
    X1 = X0.copy()
    for f in FLOOR:
        X1[f] = F[f].to_numpy(dtype="float64")
    X2 = X1.copy()
    X2["postnr"] = np.nan                       # stökkbreyting: eitt annað feature tæmt
    tilvik = [("(i)  núverandi rekstur", X0, set(FLOOR)),
              ("(ii) hæð fyllt (dry-run)", X1, set()),
              ("(iii) hæð fyllt + postnr tæmt (stökkbreyting)", X2, {"postnr"})]
    ok_all = True
    for nafn, X, vaenst in tilvik:
        T, meta = gate(X, cells, cov_tr, raw_tr, gain)
        prenta(f"sjálfspróf {nafn}", T, meta, allt=False)
        fell = set(T.index[T.fell])
        ok = fell == vaenst
        ok_all &= ok
        log(f"  vænst FELL á {sorted(vaenst) or '∅'} → fékk {sorted(fell) or '∅'}: "
            f"{'RÉTT' if ok else 'RANGT'}")
    log(f"\nSJÁLFSPRÓF: {'STENST' if ok_all else 'FELL'}")
    return 0 if ok_all else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", help="artifact-útgáfa (sjálfgefið pipeline_config.model_version)")
    ap.add_argument("--leidir", default=",".join(LEIDIR), help="komma-listi úr " + ",".join(LEIDIR))
    ap.add_argument("--sjalfsprof", action="store_true", help="falspróf á frosnu úrtaki cc244")
    ap.add_argument("--allt", action="store_true", help="prenta öll features, ekki aðeins föll")
    ap.add_argument("--json", help="skrifa niðurstöðu í þessa skrá")
    a = ap.parse_args()

    mv = a.model or read_model_version()
    booster = lgb.Booster(model_file=str(ARTIFACT_ROOT / mv / f"{mv}_main_mean.lgb"))
    feats = booster.feature_name()
    g = dict(zip(feats, booster.feature_importance("gain")))
    gt = sum(g.values())
    gain = {f: 100 * v / gt for f, v in g.items()}
    log(f"ÞEKJUHLIÐ · líkan {mv} main_mean · {len(feats)} features · "
        f"regla: (a) þjálfun ≥ {THR_HALF:.0f} % og rekstur < {THR_HALF:.0f} %, (b) |Δ| > {THR_DELTA:.0f} pp")
    cov_tr, raw_tr, n_tr, cat_map = training_coverage(feats)
    log(f"þjálfun: {TRAINING_PKL.name} main n={n_tr:,}; {len(cov_tr)} sellur (canonical_code × has_extraction_data)")

    if a.sjalfsprof:
        return sjalfsprof(feats, cov_tr, raw_tr, cat_map, gain)

    rc = 0
    out = {"likan": mv, "regla": {"half": THR_HALF, "delta_pp": THR_DELTA}, "leidir": {}}
    for leid in [s.strip() for s in a.leidir.split(",") if s.strip()]:
        if leid not in LEIDIR:
            raise SystemExit(f"óþekkt leið: {leid}")
        try:
            X, cc = (x_rebuild(feats, cat_map)[:2] if leid == "rebuild"
                     else x_adapter(feats, cat_map, mv) if leid == "adapter"
                     else x_phase1a(feats, cat_map))
        except Exception as e:  # leið sem smíðar ekki X er ekki „stenst"
            log(f"\n=== {leid}: VILLA — X ekki smíðað: {type(e).__name__}: {e}")
            out["leidir"][leid] = {"villa": f"{type(e).__name__}: {e}"}
            rc = max(rc, 2)
            continue
        T, meta = gate(X, serving_cells(cc, X), cov_tr, raw_tr, gain)
        prenta(leid, T, meta, a.allt)
        out["leidir"][leid] = {**meta, "fell": list(T.index[T.fell]),
                               "tafla": T.round(3).reset_index(names="feature").to_dict("records")}
        if T.fell.any():
            rc = max(rc, 1)
    log(f"\nNIÐURSTAÐA: {'STENST' if rc == 0 else 'FELL' if rc == 1 else 'VILLA'} (rc={rc})")
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
