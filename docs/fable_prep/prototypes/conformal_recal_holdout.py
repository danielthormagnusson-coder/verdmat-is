# cc4 2026-07-15 — ENDURKVÖRÐUN VISSUBILA, fasi 2 (read-only)
# 2.2' Live conformal-bil á fersku post-cutoff holdout (>2026-04-20)
# 2.3' Endurkvarðaðar útgáfur: (a) pool 2025-test + C-helmingur, (b) hreinn C-helmingur
# 2.4' Samanburður: þekja/breidd/flokkadreifing. ENGIN DB-skrif (SELECT eingöngu).
import json, sys, math
from pathlib import Path
import numpy as np
import pandas as pd
import psycopg2

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(r"C:\Users\danie\AppData\Local\Temp\claude\D--\6e08a093-1c6d-4325-b69e-e5854bd3182e\scratchpad")

MIN_N = 30          # sama og conformal_calibration.py
CUTOFF = "2026-04-20"
GRADE_D = {"SUMMERHOUSE", "APT_HOTEL", "APT_MIXED", "APT_ROOM"}
A_THR, B_THR = 0.20, 0.36

def db_uri():
    txt = open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read()
    for tok in txt.split():
        if tok.startswith("postgres"):
            return tok.strip().strip('"')
        if "postgres" in tok and "=" in tok:
            return tok.split("=", 1)[1].strip().strip('"')
    raise SystemExit("no pooler URI found in .dbconfig")

def q(conn, sql):
    return pd.read_sql(sql, conn)

conn = psycopg2.connect(db_uri())
conn.set_session(readonly=True)

# ---------- 1. Holdout pull ----------
H = q(conn, f"""
SELECT s.fastnum, s.thinglystdags, s.kaupverd_nominal, s.kaupverd_real,
       s.onothaefur, s.is_suspect_comparable, s.suspect_reason, s.faerslunumer,
       pr.real_pred_mean, pr.real_pred_lo80, pr.real_pred_hi80,
       pr.real_pred_lo95, pr.real_pred_hi95,
       pr.confidence_grade, pr.calibration_source, pr.model_group,
       p.canonical_code, p.region_tier
FROM public.sales_history s
LEFT JOIN public.predictions pr ON pr.fastnum = s.fastnum
LEFT JOIN public.properties  p  ON p.fastnum  = s.fastnum
WHERE s.thinglystdags > '{CUTOFF}'
""")
UNIV = q(conn, """
SELECT pr.segment AS canonical_code, p.region_tier, pr.confidence_grade,
       pr.calibration_source, count(*) AS n
FROM public.predictions pr JOIN public.properties p ON p.fastnum = pr.fastnum
GROUP BY 1,2,3,4
""")
conn.close()

H["thinglystdags"] = pd.to_datetime(H["thinglystdags"])
ledger = [("post-cutoff raðir alls", len(H))]

# einingar-tékk: kaupverd vs pred sama skala?
both = H.dropna(subset=["kaupverd_real", "real_pred_mean"])
ratio = (both["real_pred_mean"] / both["kaupverd_real"]).median()
scale = 1000.0 if 300 < ratio < 3000 else 1.0
H["sala_kr"] = H["kaupverd_real"] * scale
print(f"einingar: median pred/sala = {ratio:.3f} -> sala_scale = {scale}")

n1000 = int((H["sala_kr"] > 2e10).sum())
ledger.append(("×1000-próba (sala>20 mrd kr)", n1000))
H = H[H["sala_kr"] <= 2e10]

m = (H["onothaefur"].fillna(0) == 0)
ledger.append(("felld: onothaefur<>0", int((~m).sum()))); H = H[m]
m = ~H["is_suspect_comparable"].fillna(False).astype(bool)
ledger.append(("felld: is_suspect_comparable", int((~m).sum()))); H = H[m]
m = H["real_pred_mean"].notna()
ledger.append(("felld: engin prediction-röð", int((~m).sum()))); H = H[m]
m = H["canonical_code"].notna() & H["region_tier"].notna()
ledger.append(("felld: vantar cell-lykla", int((~m).sum()))); H = H[m]
m = (H["sala_kr"] > 1e6) & (H["real_pred_mean"] > 1e6)
ledger.append(("felld: verð/spá <= 1 Mkr (öryggissía)", int((~m).sum()))); H = H[m]
ledger.append(("HOLDOUT H (síað)", len(H)))

H["resid_log"] = np.log(H["sala_kr"]) - np.log(H["real_pred_mean"])
H["abs_resid"] = H["resid_log"].abs()
H["in80"] = (H["sala_kr"] >= H["real_pred_lo80"]) & (H["sala_kr"] <= H["real_pred_hi80"])
H["in95"] = (H["sala_kr"] >= H["real_pred_lo95"]) & (H["sala_kr"] <= H["real_pred_hi95"])
H["rel80"] = (H["real_pred_hi80"] - H["real_pred_lo80"]) / H["real_pred_mean"]
H["cell"] = H["canonical_code"].astype(str) + "|" + H["region_tier"].astype(str)

def binom_flag(cov, n):
    if n == 0 or pd.isna(cov):
        return ""
    se = math.sqrt(0.8 * 0.2 / n)
    tag = ""
    if cov < 0.80 - 2 * se: tag = "UNDIR**"
    elif cov > max(0.88, 0.80 + 2 * se): tag = "YFIR**"
    elif cov > 0.88: tag = "yfir?"
    if n < 50: tag += " (n<50)"
    return tag.strip()

def covtab(df, by):
    g = df.groupby(by, observed=True).agg(
        n=("in80", "size"), cov80=("in80", "mean"), cov95=("in95", "mean"),
        med_rel80=("rel80", "median"), medAPE=("resid_log", lambda s: float(np.median(np.abs(np.expm1(s)))))
    ).reset_index().sort_values("n", ascending=False)
    g["flagg"] = [binom_flag(c, n) for c, n in zip(g["cov80"], g["n"])]
    return g

print("\n=== SÍUBÓKHALD ===")
for k, v in ledger: print(f"  {k}: {v}")

print("\n=== 2.2' LIVE bil á öllu H ===")
print(f"H n={len(H)}  cov80={H['in80'].mean():.3f}  cov95={H['in95'].mean():.3f}  med rel80={H['rel80'].median():.3f}")
for by, nafn in [("confidence_grade", "PER FLOKKUR"), ("cell", "PER SELLA (top 12)"),
                 (H["thinglystdags"].dt.to_period("M").astype(str), "PER MÁNUÐUR")]:
    t = covtab(H, by)
    print(f"\n-- {nafn} --")
    print(t.head(12).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# samanburðarlína: suspects MEÐ (grunnur 79,1%-viðmiðs var án gæðasíu)
# (endurpull ekki þörf: geymt fyrir ofan síur — reikna á afriti fyrir síun er flóknara;
#  einfaldara: lesa aftur) — sleppt hér, gert í SQL-tékki sér.

# ---------- 2. 2025-test residúöl úr pickles ----------
preds = pd.read_pickle(r"D:\iter4a_predictions.pkl")
td = pd.read_pickle(r"D:\training_data_v2.pkl")[["FAERSLUNUMER", "region_tier"]]
preds = preds.merge(td, on="FAERSLUNUMER", how="left")
preds["abs_resid"] = (preds["log_real_kaupverd"] - preds["pred_mean_log"]).abs()
test25 = preds[(preds["model_group"] == "main") & (preds["split"] == "test")][
    ["canonical_code", "region_tier", "abs_resid"]].copy()
test25["cell"] = test25["canonical_code"].astype(str) + "|" + test25["region_tier"].astype(str)
print(f"\n2025-test calib-pool: n={len(test25)} (artifact sagði 8.575)")

# ---------- 3. C/E skipting H ----------
Hm = H[H["model_group"] == "main"].copy()   # conformal nær aðeins main
med_date = Hm["thinglystdags"].median()
C = Hm[Hm["thinglystdags"] <= med_date]
E = Hm[Hm["thinglystdags"] > med_date]
print(f"\nC/E skipting @ {med_date.date()}: C n={len(C)}  E n={len(E)} (main-only; H-main={len(Hm)})")

def build_conformal(calib):
    calib = calib.copy()
    seg_reg, seg_only = {}, {}
    for cell, sub in calib.groupby("cell"):
        if len(sub) >= MIN_N:
            seg_reg[cell] = (float(sub["abs_resid"].quantile(0.80)),
                             float(sub["abs_resid"].quantile(0.95)), len(sub))
    for cc, sub in calib.groupby("canonical_code", observed=True):
        if len(sub) >= MIN_N:
            seg_only[str(cc)] = (float(sub["abs_resid"].quantile(0.80)),
                                 float(sub["abs_resid"].quantile(0.95)), len(sub))
    return seg_reg, seg_only

def lookup(seg_reg, seg_only, cell, cc):
    if cell in seg_reg: return seg_reg[cell][0], seg_reg[cell][1], "seg_reg"
    if cc in seg_only:  return seg_only[cc][0], seg_only[cc][1], "seg"
    return np.nan, np.nan, "fallback"

def evaluate(name, seg_reg, seg_only, E):
    E = E.copy()
    r = [lookup(seg_reg, seg_only, c, cc) for c, cc in zip(E["cell"], E["canonical_code"].astype(str))]
    E["q80"], E["q95"], E["src"] = [x[0] for x in r], [x[1] for x in r], [x[2] for x in r]
    fb = E["src"] == "fallback"
    E["n_in80"] = np.where(fb, E["in80"], E["abs_resid"] <= E["q80"])
    E["n_in95"] = np.where(fb, E["in95"], E["abs_resid"] <= E["q95"])
    E["n_rel80"] = np.where(fb, E["rel80"], np.exp(E["q80"]) - np.exp(-E["q80"]))
    print(f"\n=== {name}: eval á E (n={len(E)}, fallback={int(fb.sum())}) ===")
    print(f"cov80={E['n_in80'].mean():.3f}  cov95={E['n_in95'].mean():.3f}  med rel80={E['n_rel80'].median():.3f}")
    g = E.groupby("cell", observed=True).agg(n=("n_in80", "size"), cov80=("n_in80", "mean"),
                                             med_rel80=("n_rel80", "median")).reset_index().sort_values("n", ascending=False)
    g["flagg"] = [binom_flag(c, n) for c, n in zip(g["cov80"], g["n"])]
    print(g.head(12).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    return E

# LIVE viðmið á E (sömu raðir, lifandi bil)
print(f"\n=== LIVE (viðmið) á E: n={len(E)} ===")
print(f"cov80={E['in80'].mean():.3f}  cov95={E['in95'].mean():.3f}  med rel80={E['rel80'].median():.3f}")
gl = covtab(E, "cell"); print(gl.head(12).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

Ccal = C[["canonical_code", "region_tier", "abs_resid", "cell"]]
segA = build_conformal(pd.concat([test25, Ccal], ignore_index=True))
segB = build_conformal(Ccal)
EA = evaluate("(a) POOL 2025-test + C", *segA, E)
EB = evaluate("(b) HREINN C-gluggi", *segB, E)

# ---------- 4. Flokkadreifing á framleiðslu-alheimi ----------
art = json.load(open(r"D:\iter4_conformal_corrections.json", encoding="utf-8"))
live_sr = {k: (v["q80_log"], v["q95_log"]) for k, v in art["by_segment_region"].items()}
live_s = {k: (v["q80_log"], v["q95_log"]) for k, v in art["by_segment"].items()}

def grade_of(rel80, cc):
    if cc in GRADE_D: return "D"
    if rel80 < A_THR: return "A"
    if rel80 < B_THR: return "B"
    return "C"

def universe_grades(name, seg_reg, seg_only):
    rows = []
    for _, r in UNIV.iterrows():
        cc, reg, n = str(r["canonical_code"]), str(r["region_tier"]), int(r["n"])
        cell = f"{cc}|{reg}"
        if cc in GRADE_D:
            rows.append(("D", n)); continue
        q80, _, src = lookup(seg_reg, seg_only, cell, cc)
        if src == "fallback":
            rows.append((r["confidence_grade"], n))  # fallback: óbreytt live-flokkur
        else:
            rows.append((grade_of(math.exp(q80) - math.exp(-q80), cc), n))
    s = pd.DataFrame(rows, columns=["g", "n"]).groupby("g")["n"].sum()
    tot = s.sum()
    print(f"{name:<28} " + "  ".join(f"{g}: {s.get(g,0):>6} ({100*s.get(g,0)/tot:.1f}%)" for g in "ABCD"))
    return s

print("\n=== FLOKKADREIFING framleiðslu-alheims (167.503) ===")
sr_l = {k: v for k, v in live_sr.items()}; s_l = {k: v for k, v in live_s.items()}
universe_grades("LIVE (artifact 2025)", {k: (*v, 0) for k, v in sr_l.items()}, {k: (*v, 0) for k, v in s_l.items()})
universe_grades("(a) pool 2025+C", *segA)
universe_grades("(b) hreinn C", *segB)

# ---------- 5. Sellu-q80 samanburður (breiddar-átt) ----------
print("\n=== q80 per sella: live vs (a) vs (b) — top eftir holdout-n ===")
topcells = H["cell"].value_counts().head(14).index
rows = []
for cell in topcells:
    cc = cell.split("|")[0]
    lv = live_sr.get(cell, live_s.get(cc, (np.nan,)*2))[0]
    a = segA[0].get(cell, (np.nan,)*3); b = segB[0].get(cell, (np.nan,)*3)
    rows.append((cell, int(H["cell"].value_counts()[cell]), lv, a[0], a[2] if not np.isnan(a[0]) else 0,
                 b[0], b[2] if not np.isnan(b[0]) else 0))
t = pd.DataFrame(rows, columns=["sella", "hold_n", "q80_live", "q80_a", "n_cal_a", "q80_b", "n_cal_b"])
print(t.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

H.to_csv(OUT / "holdout_rows.csv", index=False)
t.to_csv(OUT / "cell_q80_compare.csv", index=False)
print("\nCSV: holdout_rows.csv, cell_q80_compare.csv")
