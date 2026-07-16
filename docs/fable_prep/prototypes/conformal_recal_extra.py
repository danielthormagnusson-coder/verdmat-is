# cc4 — aukamælingar: (i) suspects-MEÐ lína, (ii) α=0,5 blend (G5-hemill), (iii) E-flokkar
import json, sys, math
from pathlib import Path
import numpy as np
import pandas as pd
import psycopg2

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(r"C:\Users\danie\AppData\Local\Temp\claude\D--\6e08a093-1c6d-4325-b69e-e5854bd3182e\scratchpad")
MIN_N = 30
GRADE_D = {"SUMMERHOUSE", "APT_HOTEL", "APT_MIXED", "APT_ROOM"}
A_THR, B_THR = 0.20, 0.36

def db_uri():
    txt = open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read()
    for tok in txt.split():
        if tok.startswith("postgres"): return tok.strip().strip('"')
        if "postgres" in tok and "=" in tok: return tok.split("=", 1)[1].strip().strip('"')

conn = psycopg2.connect(db_uri()); conn.set_session(readonly=True)
S = pd.read_sql("""
SELECT s.fastnum, s.thinglystdags, s.kaupverd_real, s.onothaefur, s.is_suspect_comparable,
       pr.real_pred_mean, pr.real_pred_lo80, pr.real_pred_hi80, pr.real_pred_lo95, pr.real_pred_hi95,
       pr.confidence_grade, pr.model_group, p.canonical_code, p.region_tier
FROM public.sales_history s
JOIN public.predictions pr ON pr.fastnum = s.fastnum
JOIN public.properties  p  ON p.fastnum  = s.fastnum
WHERE s.thinglystdags > '2026-04-20'
""", conn)
UNIV = pd.read_sql("""
SELECT pr.segment AS canonical_code, p.region_tier, pr.confidence_grade, count(*) AS n
FROM public.predictions pr JOIN public.properties p ON p.fastnum = pr.fastnum
GROUP BY 1,2,3
""", conn)
conn.close()

S["thinglystdags"] = pd.to_datetime(S["thinglystdags"])
S = S[(S["onothaefur"].fillna(0) == 0) & (S["kaupverd_real"] > 1e6) & (S["kaupverd_real"] <= 2e10)]
S["in80"] = (S["kaupverd_real"] >= S["real_pred_lo80"]) & (S["kaupverd_real"] <= S["real_pred_hi80"])
S["in95"] = (S["kaupverd_real"] >= S["real_pred_lo95"]) & (S["kaupverd_real"] <= S["real_pred_hi95"])
print(f"(i) suspects MEÐ  (onothaefur=0 eingöngu): n={len(S)}  cov80={S['in80'].mean():.3f}  cov95={S['in95'].mean():.3f}")
Sf = S[~S["is_suspect_comparable"].fillna(False).astype(bool)]
print(f"    suspects ÁN   (aðal-holdout):          n={len(Sf)}  cov80={Sf['in80'].mean():.3f}  cov95={Sf['in95'].mean():.3f}")

# --- blend + E-flokkar: endurnýta H úr aðalskriptu (CSV) ---
H = pd.read_csv(OUT / "holdout_rows.csv", parse_dates=["thinglystdags"])
Hm = H[H["model_group"] == "main"].copy()
med_date = Hm["thinglystdags"].median()
C = Hm[Hm["thinglystdags"] <= med_date]; E = Hm[Hm["thinglystdags"] > med_date].copy()

def build(calib):
    sr, so = {}, {}
    for cell, sub in calib.groupby("cell"):
        if len(sub) >= MIN_N:
            sr[cell] = (float(sub["abs_resid"].quantile(0.8)), float(sub["abs_resid"].quantile(0.95)), len(sub))
    for cc, sub in calib.groupby("canonical_code"):
        if len(sub) >= MIN_N:
            so[str(cc)] = (float(sub["abs_resid"].quantile(0.8)), float(sub["abs_resid"].quantile(0.95)), len(sub))
    return sr, so

srB, soB = build(C[["canonical_code", "cell", "abs_resid"]])
art = json.load(open(r"D:\iter4_conformal_corrections.json", encoding="utf-8"))
live_sr = {k: (v["q80_log"], v["q95_log"]) for k, v in art["by_segment_region"].items()}
live_so = {k: (v["q80_log"], v["q95_log"]) for k, v in art["by_segment"].items()}

def lookup_pair(cell, cc, sr, so):
    if cell in sr: return sr[cell][:2]
    if cc in so: return so[cc][:2]
    return None

def eval_qs(E, qfun, name):
    E = E.copy(); q80 = []; q95 = []; fb = []
    for cell, cc in zip(E["cell"], E["canonical_code"].astype(str)):
        r = qfun(cell, cc)
        if r is None: q80.append(np.nan); q95.append(np.nan); fb.append(True)
        else: q80.append(r[0]); q95.append(r[1]); fb.append(False)
    E["q80"], E["q95"], E["fb"] = q80, q95, fb
    E["n_in80"] = np.where(E["fb"], E["in80"], E["abs_resid"] <= E["q80"])
    E["n_in95"] = np.where(E["fb"], E["in95"], E["abs_resid"] <= E["q95"])
    E["n_rel80"] = np.where(E["fb"], E["rel80"], np.exp(E["q80"]) - np.exp(-E["q80"]))
    def grade(rel, cc):
        if cc in GRADE_D: return "D"
        return "A" if rel < A_THR else ("B" if rel < B_THR else "C")
    E["n_grade"] = [grade(r, cc) for r, cc in zip(E["n_rel80"], E["canonical_code"].astype(str))]
    gd = E["n_grade"].value_counts(normalize=True).reindex(list("ABCD")).fillna(0)
    print(f"\n{name}: E cov80={E['n_in80'].mean():.3f}  cov95={E['n_in95'].mean():.3f}  med rel80={E['n_rel80'].median():.3f}"
          f"  | E-flokkar A {gd['A']:.1%} B {gd['B']:.1%} C {gd['C']:.1%} D {gd['D']:.1%}")
    return E

def q_live(cell, cc): return lookup_pair(cell, cc, live_sr, live_so)
def q_b(cell, cc): return lookup_pair(cell, cc, srB, soB)
def q_blend(cell, cc):
    lv, b = q_live(cell, cc), q_b(cell, cc)
    if lv is None and b is None: return None
    if b is None: return lv
    if lv is None: return b
    return (0.5 * lv[0] + 0.5 * b[0], 0.5 * lv[1] + 0.5 * b[1])

eval_qs(E, q_live, "LIVE (viðmið)")
eval_qs(E, q_b, "(b) hreinn C")
eval_qs(E, q_blend, "(c) BLEND α=0,5 live+C (G5-hemils-form)")

# alheims-flokkar fyrir (c)
def universe_grades(name, qfun):
    rows = []
    for _, r in UNIV.iterrows():
        cc, reg, n = str(r["canonical_code"]), str(r["region_tier"]), int(r["n"])
        if cc in GRADE_D: rows.append(("D", n)); continue
        qq = qfun(f"{cc}|{reg}", cc)
        if qq is None: rows.append((r["confidence_grade"], n)); continue
        rel = math.exp(qq[0]) - math.exp(-qq[0])
        rows.append(("A" if rel < A_THR else ("B" if rel < B_THR else "C"), n))
    s = pd.DataFrame(rows, columns=["g", "n"]).groupby("g")["n"].sum(); tot = s.sum()
    print(f"{name:<34} " + "  ".join(f"{g}: {s.get(g,0):>6} ({100*s.get(g,0)/tot:.1f}%)" for g in "ABCD"))

print("\nALHEIMS-flokkadreifing:")
universe_grades("LIVE", q_live)
universe_grades("(b) hreinn C", q_b)
universe_grades("(c) blend α=0,5", q_blend)

# q80-blend per stóra sellu (til töflu)
print("\nq80 blend per stóru sellurnar:")
for cell in ["APT_FLOOR|Capital_sub", "APT_FLOOR|RVK_core", "APT_STANDARD|RVK_core",
             "APT_FLOOR|Country", "APT_STANDARD|Capital_sub", "APT_STANDARD|Country"]:
    cc = cell.split("|")[0]
    lv, b, bl = q_live(cell, cc), q_b(cell, cc), q_blend(cell, cc)
    rel = lambda t: (math.exp(t[0]) - math.exp(-t[0])) if t else float("nan")
    print(f"  {cell:<26} live q80={lv[0]:.4f} (rel {rel(lv):.3f})  C q80={(b[0] if b else float('nan')):.4f}"
          f"  blend q80={bl[0]:.4f} (rel {rel(bl):.3f})")
