# -*- coding: utf-8 -*-
"""
cc135_parity.py — PARITY + KOHORT + SKAMMTASVÖRUN fyrir leigu-þrepin (cc135 liðir 3-4).

READ-ONLY: les valuation_tiers_rent (LIVE), valuation_tiers_rent_staging (nýbyggt),
properties, predictions_rent og leiga_train.parquet. Skrifar EKKERT í DB.

  LIÐUR 3  parity : rowcount, 500-raða sýni staging<->CSV, orphans, universe-tala,
                    NULL-talningar, staging<->properties canonical-mismunur.
  LIÐUR 4a kohort : víxl-hólfin (óbreytt / innan fjölskyldu / fjölbýli<->sérbýli),
                    þrepa-víxl per hólf, og HVE MARGAR eignir vinna/tapa birtu mati
                    (T5 kæfir leigumatið algerlega — sjá byggjaLeigumat).
  LIÐUR 4b skammtasvörun : leigan hefur ENGA comps-vél, svo cc131-mengunarmerkið
                    (comp-akkeri / spá) er EKKI TIL. Nálgunin sem TIL ER: raun-akkeri
                    sellunnar = miðgildi leiguverðs á m2 í (postnr x canonical_code)
                    úr samningum 2021+. Mælt með SÖMU formúlu tvisvar: sellan sem
                    STÖÐNUÐ merking valdi (fyrir) og sellan sem regla R velur (eftir).
                    Spáin sjálf er FRYST (predictions_rent, bann) — hún hreyfist ekki;
                    það sem hreyfist er HVAÐA raun-sellu eignin er borin við.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from build_rent_tiers import TRAIN, OUT_CSV

DSN = Path(r"D:\verdmat-is\.dbconfig").read_text(encoding="utf-8-sig").strip()

FJOLB = {"APT_STANDARD", "APT_FLOOR", "APT_BASEMENT", "APT_ATTIC", "APT_SENIOR",
         "APT_MIXED", "APT_UNAPPROVED", "APT_ROOM", "APT_HOTEL"}
SERB = {"SFH_DETACHED", "ROW_HOUSE", "SEMI_DETACHED"}
COLS = ["fastnum", "threp", "flokkur", "t5_astaeda", "n_local", "n_conformal",
        "fallback_lvl", "herb_vantar", "pi80_pct", "segment", "canonical_code"]


def hr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


def fam(cc: str) -> str:
    if cc in FJOLB:
        return "fjolbyli"
    if cc in SERB:
        return "serbyli"
    return "annad"


def main() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    # =================== LIÐUR 3: PARITY ===================
    hr("LIÐUR 3 — PARITY (staging gegn CSV, properties og lifandi töflu)")
    cur.execute("SELECT count(*) FROM public.valuation_tiers_rent_staging")
    n_stg = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM public.valuation_tiers_rent")
    n_live = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM public.valuation_tiers_rent_pre_cc135")
    n_snap = cur.fetchone()[0]
    cur.execute("""SELECT count(*) FROM public.predictions_rent s
                   JOIN public.properties p USING (fastnum)""")
    n_uni = cur.fetchone()[0]
    print(f"  universe (predictions_rent x properties) : {n_uni:,}")
    print(f"  staging                                  : {n_stg:,}")
    print(f"  live valuation_tiers_rent                : {n_live:,}")
    print(f"  snapshot *_pre_cc135                     : {n_snap:,}")
    print(f"  rowcount-hlið: {'PASS' if n_stg == n_uni == n_live == n_snap else 'FAIL'}")

    cur.execute("""SELECT count(*) FROM public.valuation_tiers_rent_staging s
                   LEFT JOIN public.properties p USING (fastnum)
                   WHERE p.fastnum IS NULL""")
    orph = cur.fetchone()[0]
    cur.execute("""SELECT count(*) FROM public.valuation_tiers_rent_staging s
                   JOIN public.properties p USING (fastnum)
                   WHERE s.canonical_code IS DISTINCT FROM p.canonical_code""")
    ccm = cur.fetchone()[0]
    cur.execute("""SELECT count(*) FROM public.predictions_rent s
                   LEFT JOIN public.valuation_tiers_rent_staging t USING (fastnum)
                   WHERE t.fastnum IS NULL""")
    vantar = cur.fetchone()[0]
    print(f"  orphans (staging an properties)          : {orph}   {'PASS' if not orph else 'FAIL'}")
    print(f"  staging<->properties canonical-mismunur  : {ccm}   {'PASS' if not ccm else 'FAIL'}")
    print(f"  spa-radir an threps i staging            : {vantar}   {'PASS' if not vantar else 'FAIL'}")

    print("\n  NULL-talningar (staging | live):")
    for c in COLS:
        cur.execute(f"SELECT count(*) FROM public.valuation_tiers_rent_staging WHERE {c} IS NULL")
        a = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM public.valuation_tiers_rent WHERE {c} IS NULL")
        b = cur.fetchone()[0]
        flag = "" if c in ("t5_astaeda", "flokkur", "n_conformal") else \
               ("   <- MA EKKI vera NULL" if a else "")
        print(f"    {c:<16} {a:>7,} | {b:>7,}{flag}")
    cur.execute("SELECT count(*) FROM public.valuation_tiers_rent_staging WHERE threp IS NULL "
                "OR threp NOT BETWEEN 1 AND 5")
    print(f"  threp utan 1..5 eda NULL: {cur.fetchone()[0]}")

    # --- 500-raða sýni: DB gegn CSV-inu sem byggingin skrifaði ---
    csv = pd.read_csv(OUT_CSV)
    rng = np.random.default_rng(135)
    sample = rng.choice(csv.fastnum.values, size=500, replace=False)
    db = pd.read_sql("SELECT " + ",".join(COLS) +
                     " FROM public.valuation_tiers_rent_staging WHERE fastnum = ANY(%(f)s)",
                     conn, params={"f": [int(x) for x in sample]})
    c5 = csv[csv.fastnum.isin(sample)].copy()
    print(f"\n  500-raða sýni: DB={len(db)}  CSV={len(c5)}")
    db = db.sort_values("fastnum").reset_index(drop=True)
    c5 = c5.sort_values("fastnum").reset_index(drop=True)
    mism = 0
    for c in COLS:
        a, b = db[c], c5[c]
        if c == "pi80_pct":
            d = (pd.to_numeric(a).round(2) != pd.to_numeric(b).round(2)) & ~(a.isna() & b.isna())
        elif c == "herb_vantar":
            d = a.astype(str).str.lower().str[0] != b.astype(str).str.lower().str[0]
        else:
            d = (a.astype(str) != b.astype(str)) & ~(a.isna() & b.isna())
        if d.sum():
            mism += int(d.sum())
            print(f"    MISMUNUR {c}: {d.sum()} radir")
    print(f"  sýni-parity: {'PASS (0 mismunur a 11 dalkum x 500 radir)' if not mism else f'FAIL ({mism})'}")

    # =================== LIÐUR 4a: KOHORT ===================
    hr("LIÐUR 4a — KOHORT: víxl-hólfin og hvað þau gera við birt mat")
    u = pd.read_sql("""
        SELECT v.fastnum, v.threp AS threp_fyrir, v.canonical_code AS cc_fyrir,
               v.n_local AS nl_fyrir, v.t5_astaeda AS ast_fyrir, v.flokkur AS fl_fyrir,
               s.threp AS threp_eftir, s.canonical_code AS cc_eftir,
               s.n_local AS nl_eftir, s.t5_astaeda AS ast_eftir, s.flokkur AS fl_eftir,
               p.postnr, p.einflm, p.heimilisfang, p.postheiti,
               r.pred_mean, r.segment, (fj.fastnum IS NOT NULL) AS fjoleining
        FROM public.valuation_tiers_rent v
        JOIN public.valuation_tiers_rent_staging s USING (fastnum)
        JOIN public.properties p USING (fastnum)
        JOIN public.predictions_rent r USING (fastnum)
        LEFT JOIN public.v_fjoleining_fastnum fj USING (fastnum)
    """, conn)
    u["holf"] = np.where(
        u.cc_fyrir == u.cc_eftir, "obreytt",
        np.where([fam(a) == fam(b) for a, b in zip(u.cc_fyrir, u.cc_eftir)],
                 "innan_fjolskyldu", "fjolb<->serb"))
    print(f"  {len(u):,} raðir; víxl-hólf:")
    for h, g in u.groupby("holf"):
        vixl = (g.threp_fyrir != g.threp_eftir).sum()
        print(f"    {h:<18} n={len(g):>7,}  þrep víxlar á {vixl:>7,} ({100*vixl/len(g):>5.2f}%)")

    print("\n  BIRT MAT (T5 kæfir leigumatið algerlega — byggjaLeigumat):")
    tap = ((u.threp_fyrir != 5) & (u.threp_eftir == 5)).sum()
    vinn = ((u.threp_fyrir == 5) & (u.threp_eftir != 5)).sum()
    print(f"    eignir sem FÁ mat  (T5 -> T1..T4): {vinn:,}")
    print(f"    eignir sem MISSA mat (T1..T4 -> T5): {tap:,}")
    print(f"    nettó T5: {(u.threp_fyrir==5).sum():,} -> {(u.threp_eftir==5).sum():,} "
          f"({vinn - tap:+,})")
    # Kæfingarnar eru ÞRJÁR (byggjaLeigumat): T5, fjöleiningar-smit (cc27) og
    # engin spá. Nettóáhrifin á BIRT mat verða að mælast eftir þeim öllum.
    syn = ~u.fjoleining & u.pred_mean.notna()
    print(f"    fjöleiningar-vörnin (cc27) grípur: {u.fjoleining.sum():,} raðir "
          f"({100*u.fjoleining.mean():.2f}%)  |  spá NULL: {u.pred_mean.isna().sum():,}")
    print(f"    FÁ birt mat (sýnilegar)   : {((u.threp_fyrir==5)&(u.threp_eftir!=5)&syn).sum():,}")
    print(f"    MISSA birt mat (sýnilegar): {((u.threp_fyrir!=5)&(u.threp_eftir==5)&syn).sum():,}")
    print(f"    þrepsvíxl á SÝNILEGUM eignum: {((u.threp_fyrir!=u.threp_eftir)&syn).sum():,}")

    print("\n  þrepa-víxl per hólf (fyrir -> eftir):")
    for h, g in u.groupby("holf"):
        ct = pd.crosstab(g.threp_fyrir, g.threp_eftir)
        off = [(a, b, int(n)) for a in ct.index for b in ct.columns
               if a != b and (n := ct.loc[a, b]) > 0]
        off.sort(key=lambda x: -x[2])
        print(f"    {h}: " + ", ".join(f"T{a}->T{b}={n:,}" for a, b, n in off[:8]))

    print("\n  T5-ástæður fyrir -> eftir:")
    for a in ("of_fair_samningar", "engin_svaedisgogn", "eignaflokkur"):
        print(f"    {a:<20} {(u.ast_fyrir==a).sum():>7,} -> {(u.ast_eftir==a).sum():>7,}")
    b_fl = u.fl_fyrir.value_counts().to_dict()
    e_fl = u.fl_eftir.value_counts().to_dict()
    print(f"  flokkur fyrir={b_fl}  eftir={e_fl}")
    n_fl = (u.fl_fyrir.fillna("-") != u.fl_eftir.fillna("-")).sum()
    print(f"  raðir þar sem FLOKKUR breytist: {n_fl:,} (flokkur = conformal-breidd, "
          "spáin fryst -> aðeins D-merkingin getur hreyfst)")

    print("\n  ÚRTAK úr hverju víxl-hólfi (3 per stærsta víxlpar):")
    for h in ("innan_fjolskyldu", "fjolb<->serb"):
        g = u[(u.holf == h) & (u.threp_fyrir != u.threp_eftir)]
        for (a, b), gg in sorted(g.groupby(["cc_fyrir", "cc_eftir"]),
                                 key=lambda kv: -len(kv[1]))[:2]:
            print(f"    [{h}] {a} -> {b}  (n={len(gg):,})")
            for r in gg.head(3).itertuples():
                print(f"       {r.fastnum}  {str(r.heimilisfang)[:28]:<28} {r.postnr} "
                      f"T{r.threp_fyrir}->T{r.threp_eftir}  n_local {r.nl_fyrir}->{r.nl_eftir}")

    # =================== LIÐUR 4b: SKAMMTASVÖRUN ===================
    hr("LIÐUR 4b — SKAMMTASVÖRUN (raun-akkeri sellunnar / leigu-spá)")
    print("  ATH: leigan hefur ENGA comps-vél -> cc131-mengunarmerkið (comp-akkeri/spá)")
    print("  er EKKI TIL fyrir leiguna. Akkerið hér er RAUNVERÐ sellunnar úr samningum.")
    c = pd.read_parquet(TRAIN, columns=["fastnum", "prop_postnr", "canonical_code",
                                        "contract_year", "heildarverd", "staerd"])
    c = c[(c.contract_year >= 2021) & (c.heildarverd > 0) & (c.staerd > 0)].copy()
    c["prop_postnr"] = pd.to_numeric(c.prop_postnr, errors="coerce")
    c = c.dropna(subset=["prop_postnr"]).astype({"prop_postnr": int})
    c["canonical_code"] = c.canonical_code.astype(object)
    c["rpm2"] = c.heildarverd / c.staerd
    live = pd.read_sql("SELECT fastnum, canonical_code AS cc_live FROM public.properties", conn)
    c = c.merge(live, on="fastnum", how="left")
    c["cc_r"] = c.cc_live.fillna(c.canonical_code)

    def akkeri(cc_col: str) -> pd.DataFrame:
        g = c.groupby(["prop_postnr", cc_col]).rpm2.agg(["median", "size"]).reset_index()
        g.columns = ["postnr", "cc", "akkeri_rpm2", "n_sella"]
        return g

    a_fyrir, a_eftir = akkeri("canonical_code"), akkeri("cc_r")
    u["pred_rpm2"] = u.pred_mean / u.einflm.replace(0, np.nan)
    x = (u.merge(a_fyrir.rename(columns={"akkeri_rpm2": "ak_f", "n_sella": "n_f"}),
                 left_on=["postnr", "cc_fyrir"], right_on=["postnr", "cc"], how="left")
          .drop(columns=["cc"])
          .merge(a_eftir.rename(columns={"akkeri_rpm2": "ak_e", "n_sella": "n_e"}),
                 left_on=["postnr", "cc_eftir"], right_on=["postnr", "cc"], how="left")
          .drop(columns=["cc"]))
    MIN_SELLA = 10
    m = (x.pred_rpm2.notna() & x.ak_f.notna() & x.ak_e.notna()
         & (x.n_f >= MIN_SELLA) & (x.n_e >= MIN_SELLA))
    x = x[m].copy()
    x["r_fyrir"] = x.ak_f / x.pred_rpm2
    x["r_eftir"] = x.ak_e / x.pred_rpm2
    print(f"\n  mælanlegar raðir (bæði akkeri n>={MIN_SELLA}, einflm>0): {len(x):,} af {len(u):,}")
    print("  ATH: samningarnir eru 2021-2023, spáin 2026-05 -> nafnverðs-akkerisbil er")
    print("  SAMEIGINLEGT öllum hólfum. Merkið er BILIÐ MILLI HÓLFA, ekki stigið sjálft.")
    print(f"\n  {'hólf':<18} {'n':>7}  {'fyrir':>8} {'eftir':>8}   {'Δ p.p. gegn óbreyttu':>22}")
    base_f = x.loc[x.holf == "obreytt", "r_fyrir"].median()
    base_e = x.loc[x.holf == "obreytt", "r_eftir"].median()
    for h in ("obreytt", "innan_fjolskyldu", "fjolb<->serb"):
        g = x[x.holf == h]
        if not len(g):
            continue
        rf, re_ = g.r_fyrir.median(), g.r_eftir.median()
        print(f"  {h:<18} {len(g):>7,}  {rf:>8.4f} {re_:>8.4f}   "
              f"fyrir {100*(rf-base_f):>+6.2f}  eftir {100*(re_-base_e):>+6.2f}")
    print("\n  NIÐURSTAÐA — INNISTÆÐAN ER HREYFINGARLEYSI, EKKI LOKUN:")
    mx = 0.0
    for h in ("obreytt", "innan_fjolskyldu", "fjolb<->serb"):
        g = x[x.holf == h]
        if len(g):
            d = abs(100 * (g.r_eftir.median() - g.r_fyrir.median()))
            mx = max(mx, d)
            print(f"    {h:<18} |Δ fyrir->eftir| = {d:.2f} p.p.")
    print(f"    stærsta hreyfing yfir öll hólf: {mx:.2f} p.p.")
    print("    -> endurbyggingin færir ÞREPIÐ, ekki leigutöluna. Spáin er fryst")
    print("       (bann á predictions_rent) og ber enn PRE-R segment á 36,39% raða")
    print("       (cc135_forsendur.py lið D). Mengunin í TÖLUNNI stendur eftir cc135")
    print("       og verður aðeins læknuð með endurskorun — sér lota.")

    # --- HVERS VEGNA STIGIÐ SJÁLFT ER ÓDÓMTÆKT Á VÍXL-HÓLFINU ---
    # Hlutfallið er á m2. Fyrir eignir sem víxla milli fjölbýlis og sérbýlis er
    # NEFNARINN (properties.einflm) ekki sama einingin og leigusamningurinn nær yfir:
    # samningur á fastnum getur verið um HLUTA matseiningarinnar. Þá er stigið
    # (+54 p.p.) NEFNARA-ARTEFAKT, ekki mengunarmerki — mælt hér svo það sé bókað.
    d = c.groupby("fastnum").agg(samn_staerd=("staerd", "median"),
                                 eigin_leiga=("heildarverd", "median")).reset_index()
    y = u.merge(d, on="fastnum")
    y = y[y.einflm > 0]
    print("\n  NEFNARA-PRÓF (eignir m/eigin samning 2021+, hvers vegna STIGIÐ er ódómtækt):")
    print(f"    {'hólf':<18}{'n':>7}{'einflm p50':>12}{'samn.stærð p50':>16}"
          f"{'einflm/stærð':>14}{'spá/eigin leiga':>17}")
    for h, g in y.groupby("holf"):
        print(f"    {h:<18}{len(g):>7,}{g.einflm.median():>12.1f}"
              f"{g.samn_staerd.median():>16.1f}{(g.einflm/g.samn_staerd).median():>14.3f}"
              f"{(g.pred_mean/g.eigin_leiga).median():>17.3f}")
    print("    -> einflm/samningsstærð ~3,3x á fjolb<->serb gegn 1,000 annars staðar:")
    print("       samningurinn nær yfir HLUTA matseiningarinnar. Stigið á því hólfi er")
    print("       ÓDÓMTÆKT sem mengunarmæling; hreyfingarleysið að ofan er það ekki.")

    conn.close()


if __name__ == "__main__":
    main()
