"""probe_cc39.py — FASI 1 PROBE (READ-ONLY): ×1000-raðir í kaupskra.csv vs lifandi DB.

Ekkert skrifað í DB. Les kaupskra.csv + opnar READ-ONLY tengingu fyrir
properties-universið (sama FK-sía og derive_sales_rows) og lifandi sales_history
nominal-gildin fyrir kandídata.

Úttak:
  A) hrágildi röðanna 744059/744084/744085 í CSV
  B) dreifing derived nominal (KAUPVERD*1000) á FK-síuðum röðum: kvantílar
  C) dreifing verðs/m² og kv (KAUPVERD/FASTEIGNAMAT)
  D) allir kandídatar: nominal > CAND_CUT — full smáatriði + DB-samanburður
  E) DB-skann: raðir í sales_history með nominal yfir sama þröskuldi
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, r"D:\verdmat-is\app\scripts")
from rebuild_sales_history import (  # noqa: E402
    open_ro_conn, fetch_valid_fastnums, KAUPSKRA_CSV,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EXPECTED = [744059, 744084, 744085]
CAND_CUT = 3_000_000_000  # 3 ma.kr — langt yfir öllu lögmætu íbúðarverði; kvantílar sannreyna

kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
print(f"kaupskra raw rows = {len(kp):,}")

kp["FASTNUM_i"] = pd.to_numeric(kp["FASTNUM"], errors="coerce").astype("Int64")
kp["faerslunumer"] = pd.to_numeric(kp["FAERSLUNUMER"], errors="coerce").astype("Int64")
kp["KAUPVERD_n"] = pd.to_numeric(kp["KAUPVERD"], errors="coerce")
kp["FMAT_n"] = pd.to_numeric(kp["FASTEIGNAMAT"], errors="coerce")
kp["EINFLM_n"] = pd.to_numeric(kp["EINFLM"], errors="coerce")

# ---- A) hrágildi væntu röðanna ----
print("\n=== A) hrágildi 744059/744084/744085 í CSV ===")
cols = ["FAERSLUNUMER", "FASTNUM", "THINGLYSTDAGS", "KAUPVERD", "FASTEIGNAMAT",
        "EINFLM", "BYGGAR", "FULLBUID", "ONOTHAEFUR_SAMNINGUR"]
exp = kp[kp["faerslunumer"].isin(EXPECTED)]
print(exp[cols].to_string(index=False))

# ---- FK-sía (sama universe og derive) ----
conn = open_ro_conn()
valid = fetch_valid_fastnums(conn)
u = kp[kp["FASTNUM_i"].notna() & kp["FASTNUM_i"].isin(valid)].copy()
u = u[u["KAUPVERD_n"].notna() & (u["KAUPVERD_n"] > 0)]
u["nominal"] = (u["KAUPVERD_n"] * 1000).round()
print(f"\nFK-síaðar raðir m/jákvæðu KAUPVERD = {len(u):,}")

# ---- B) dreifing nominal ----
print("\n=== B) dreifing derived nominal (kr) á FK-síuðum röðum ===")
q = u["nominal"].quantile([0.5, 0.9, 0.99, 0.999, 0.9999, 0.99999, 1.0])
for p, v in q.items():
    print(f"  p{p*100:g}: {v:,.0f}")
top = u.nlargest(15, "nominal")
print("\n  TOP 15 nominal:")
print(top[["FAERSLUNUMER", "FASTNUM", "THINGLYSTDAGS", "KAUPVERD", "FASTEIGNAMAT",
           "EINFLM", "nominal"]].to_string(index=False))

# ---- C) verð/m² + kv ----
print("\n=== C) verð/m² (EINFLM>10) og kv = KAUPVERD/FASTEIGNAMAT ===")
m = u[u["EINFLM_n"] > 10].copy()
m["kr_m2"] = m["nominal"] / m["EINFLM_n"]
qq = m["kr_m2"].quantile([0.5, 0.99, 0.999, 0.9999, 1.0])
for p, v in qq.items():
    print(f"  kr/m2 p{p*100:g}: {v:,.0f}")
kvu = u[u["FMAT_n"] > 0].copy()
kvu["kv"] = kvu["KAUPVERD_n"] / kvu["FMAT_n"]
qkv = kvu["kv"].quantile([0.5, 0.99, 0.999, 0.9999, 1.0])
for p, v in qkv.items():
    print(f"  kv    p{p*100:g}: {v:,.3f}")
print(f"  raðir m/kv > 100: {int((kvu['kv'] > 100).sum())}")
print(f"  raðir m/kv í [100, 2000]: {int(kvu['kv'].between(100, 2000).sum())}")

# ---- D) kandídatar yfir CAND_CUT ----
print(f"\n=== D) kandídatar: nominal > {CAND_CUT:,} ===")
cand = u[u["nominal"] > CAND_CUT].copy()
cand["kv"] = cand["KAUPVERD_n"] / cand["FMAT_n"].where(cand["FMAT_n"] > 0)
cand["kr_m2"] = cand["nominal"] / cand["EINFLM_n"].where(cand["EINFLM_n"] > 10)
cand["nominal_div1000"] = cand["nominal"] / 1000
print(f"fjöldi kandídata = {len(cand)}")
print(cand[["FAERSLUNUMER", "FASTNUM", "THINGLYSTDAGS", "KAUPVERD", "FASTEIGNAMAT",
            "EINFLM", "nominal", "nominal_div1000", "kv", "kr_m2"]].to_string(index=False))
print(f"\nsamanburður við væntu 3: fundnir={sorted(cand['faerslunumer'].dropna().astype(int).tolist())} "
      f"væntir={EXPECTED} eins={sorted(cand['faerslunumer'].dropna().astype(int).tolist()) == EXPECTED}")

# ---- E) DB-skann: nominal yfir þröskuldi + gildi kandídata í DB ----
print(f"\n=== E) lifandi sales_history: nominal > {CAND_CUT:,} + DB-gildi kandídata ===")
with conn.cursor() as cur:
    cur.execute("SELECT count(*), max(kaupverd_nominal) FROM public.sales_history")
    n, mx = cur.fetchone()
    print(f"  sales_history rows={n:,}  MAX(nominal)={mx:,}")
    cur.execute("SELECT faerslunumer, fastnum, thinglystdags, kaupverd_nominal, kaupverd_real "
                "FROM public.sales_history WHERE kaupverd_nominal > %s "
                "ORDER BY kaupverd_nominal DESC", (CAND_CUT,))
    rows = cur.fetchall()
    print(f"  raðir yfir {CAND_CUT:,}: {len(rows)}")
    for r in rows:
        print(f"    f={r[0]} fn={r[1]} {r[2]} nominal={r[3]:,} real={r[4]:,}")
    cands = [int(x) for x in cand["faerslunumer"].dropna().astype(int).tolist()]
    if cands:
        cur.execute("SELECT faerslunumer, fastnum, kaupverd_nominal, kaupverd_real "
                    "FROM public.sales_history WHERE faerslunumer = ANY(%s) "
                    "ORDER BY faerslunumer", (cands,))
        print("  DB-gildi kandídata (á að vera leiðrétt ef vörðurinn hélt):")
        for r in cur.fetchall():
            print(f"    f={r[0]} fn={r[1]} nominal={r[2]:,} real={r[3]:,}")
    # neðri halinn: hugsanleg ÷1000-skekkja hin leiðin (of lág gildi)
    cur.execute("SELECT count(*) FROM public.sales_history "
                "WHERE kaupverd_nominal BETWEEN 1000 AND 100000")
    lo = cur.fetchone()[0]
    print(f"  raðir m/nominal í [1.000, 100.000] kr (grunur um vantandi *1000): {lo}")
conn.close()
print("\nPROBE LOKIÐ — ekkert skrifað.")
