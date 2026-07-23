"""probe_cc39_b.py — FASI 1 þrenging (READ-ONLY): kr/m²-halinn í CSV og DB.

Mælir gráa svæðið milli lögmæta halans og ×1000-raðanna svo þröskuldar
gildisvarnarinnar séu bókaðir út frá gögnunum sjálfum.
"""
import sys
import pandas as pd

sys.path.insert(0, r"D:\verdmat-is\app\scripts")
from rebuild_sales_history import open_ro_conn, fetch_valid_fastnums, KAUPSKRA_CSV  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
kp["FASTNUM_i"] = pd.to_numeric(kp["FASTNUM"], errors="coerce").astype("Int64")
kp["faerslunumer"] = pd.to_numeric(kp["FAERSLUNUMER"], errors="coerce").astype("Int64")
kp["KAUPVERD_n"] = pd.to_numeric(kp["KAUPVERD"], errors="coerce")
kp["EINFLM_n"] = pd.to_numeric(kp["EINFLM"], errors="coerce")

conn = open_ro_conn()
valid = fetch_valid_fastnums(conn)
u = kp[kp["FASTNUM_i"].notna() & kp["FASTNUM_i"].isin(valid)].copy()
u = u[u["KAUPVERD_n"].notna() & (u["KAUPVERD_n"] > 0)]
u["nominal"] = (u["KAUPVERD_n"] * 1000).round()

# --- kr/m² halinn í CSV (EINFLM > 10) ---
m = u[u["EINFLM_n"] > 10].copy()
m["kr_m2"] = m["nominal"] / m["EINFLM_n"]
print(f"FK-raðir m/EINFLM>10: {len(m):,}  (án EINFLM eða <=10: {len(u)-len(m):,})")
for cut in (1_500_000, 2_000_000, 3_000_000, 5_000_000, 10_000_000, 20_000_000):
    print(f"  kr/m2 > {cut:>12,}: {int((m['kr_m2'] > cut).sum())}")
print("\nTOP 12 kr/m2 í CSV:")
top = m.nlargest(12, "kr_m2")
print(top[["FAERSLUNUMER", "FASTNUM", "THINGLYSTDAGS", "KAUPVERD", "EINFLM", "nominal", "kr_m2"]]
      .to_string(index=False))

# --- raðir ÁN nothæfs EINFLM: gæti ×1000-röð falið sig þar? mæli nominal-halann ---
noflm = u[~(u["EINFLM_n"] > 10)]
print(f"\nraðir án EINFLM>10: {len(noflm):,}; TOP 5 nominal þeirra:")
print(noflm.nlargest(5, "nominal")[["FAERSLUNUMER", "FASTNUM", "THINGLYSTDAGS", "KAUPVERD",
                                    "EINFLM", "nominal"]].to_string(index=False))

# --- sjálf-útrennslis-sannreyning á gráa svæðinu: kandídatarnir 3 eftir ÷1000 ---
cand = m[m["kr_m2"] > 10_000_000].copy()
cand["kr_m2_fixed"] = cand["kr_m2"] / 1000
print("\nkandídatar (kr/m2 > 10M) eftir ÷1000:")
print(cand[["FAERSLUNUMER", "kr_m2", "kr_m2_fixed"]].to_string(index=False))

# --- DB-hliðin: max kr/m² í lifandi sales_history ---
with conn.cursor() as cur:
    cur.execute("""
        SELECT faerslunumer, fastnum, thinglystdags, kaupverd_nominal, einflm_at_sale,
               kaupverd_nominal / einflm_at_sale AS kr_m2
        FROM public.sales_history
        WHERE einflm_at_sale > 10
        ORDER BY kaupverd_nominal / einflm_at_sale DESC
        LIMIT 8""")
    print("\nTOP 8 kr/m2 í lifandi sales_history:")
    for r in cur.fetchall():
        print(f"  f={r[0]} fn={r[1]} {r[2]} nominal={r[3]:,} einflm={r[4]} kr_m2={float(r[5]):,.0f}")
    cur.execute("SELECT count(*) FROM public.sales_history "
                "WHERE einflm_at_sale > 10 AND kaupverd_nominal / einflm_at_sale > 2000000")
    print(f"DB-raðir m/kr_m2 > 2M: {cur.fetchone()[0]}")
conn.close()
print("\nPROBE B LOKIÐ — ekkert skrifað.")
