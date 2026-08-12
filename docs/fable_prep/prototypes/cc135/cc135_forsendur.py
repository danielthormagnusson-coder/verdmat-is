# -*- coding: utf-8 -*-
"""
cc135_forsendur.py — FORSENDUMAELING (LIDUR 2) adur en valuation_tiers_rent er
endurbyggd a reglu R. READ-ONLY: skrifar EKKERT i DB.

Maelir thrjar forsendur build_rent_tiers.py:
  A. LIND UNIVERSE: load_universe() les public.predictions_rent_staging — sem var
     ENDURNEFND i predictions_rent (cc57). Taflan er EKKI til lengur.
  B. FROSIN THETTLEIKA-LIND: leiga_train.parquet (29.06) ber canonical_code
     PRE reglu R. Universe-hlidin kemur LIFANDI ur properties (03.08, cc78).
     Joinid er thvi milli TVEGGJA MERKINGARKERFA. Maelt her.
  C. SEGMENT-ASINN: predictions_rent.segment = cc|region[|tegund] — reiknad
     2026-05-01 ur PRE-R properties. Bannad ad hrofla vid (BANN i lotu-brefi),
     svo conformal-asinn (fallback_lvl, n_conformal) LAEKNAST EKKI vid endurbyggingu.

Thrjar hólfanir a threpi:
  S0 = stale cc (ur vt) + stale thettleiki   -> a ad endurgera LIFANDI toflu
  S1 = LIVE cc + stale thettleiki            -> "naiv endurkeyrsla"
  S2 = LIVE cc + LIVE-merktur thettleiki     -> samraemd endurbygging
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import psycopg2

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from build_rent_tiers import (CONF, TRAIN, UTILOKADIR, MIN_LOCAL, THRESHOLDS,
                              GRADE_A, GRADE_B, fallback_lvl, load_conformal_n)

DSN = Path(r"D:\verdmat-is\.dbconfig").read_text(encoding="utf-8-sig").strip()


def hr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


def grunn(n: int) -> int:
    if n >= THRESHOLDS["T1"]:
        return 1
    if n >= THRESHOLDS["T2"]:
        return 2
    if n >= THRESHOLDS["T3"]:
        return 3
    return 4


def threp_af(u: pd.DataFrame, cc: pd.Series, n_local: pd.Series) -> pd.DataFrame:
    """Sama regla og build_rent_tiers.assign(), en cc/n_local gefid ad utan."""
    t = n_local.map(grunn) + u.herb_vantar.astype(int) + (u.fallback_lvl == 2).astype(int)
    t = t.clip(upper=4)
    t5 = cc.isin(UTILOKADIR) | (u.fallback_lvl == 3) | (n_local < MIN_LOCAL)
    threp = t.where(~t5, 5)
    ast = pd.Series(None, index=u.index, dtype=object)
    ast[t5 & (n_local < MIN_LOCAL)] = "of_fair_samningar"
    ast[t5 & (u.fallback_lvl == 3)] = "engin_svaedisgogn"
    ast[t5 & cc.isin(UTILOKADIR)] = "eignaflokkur"
    fl = pd.cut(u.pi80, [-1, GRADE_A, GRADE_B, 1e9], labels=["A", "B", "C"]).astype(object)
    fl = pd.Series(fl, index=u.index)
    fl[cc.isin(UTILOKADIR)] = "D"
    return pd.DataFrame({"threp": threp, "t5_astaeda": ast, "flokkur": fl,
                         "n_local": n_local})


def dreifing(name: str, threp: pd.Series) -> None:
    n = len(threp)
    v = threp.value_counts().sort_index()
    print(f"  {name:<28}" + "  ".join(f"T{k}={v.get(k,0):>6,} ({100*v.get(k,0)/n:>5.2f}%)"
                                      for k in range(1, 6)))


def main() -> None:
    conn = psycopg2.connect(DSN)

    # ---------- A. LIND UNIVERSE ----------
    hr("A. LIND UNIVERSE — hvad les build_rent_tiers.py?")
    cur = conn.cursor()
    for t in ("predictions_rent_staging", "predictions_rent",
              "valuation_tiers_rent_staging", "valuation_tiers_rent"):
        cur.execute("SELECT to_regclass(%s)::text", (f"public.{t}",))
        print(f"  to_regclass(public.{t:<30}) = {cur.fetchone()[0]}")
    cur.execute("""SELECT i.relname, t.relname FROM pg_index x
                   JOIN pg_class i ON i.oid=x.indexrelid
                   JOIN pg_class t ON t.oid=x.indrelid
                   WHERE i.relname LIKE '%%_staging_pkey'
                     AND i.relname LIKE ANY (ARRAY['predictions_rent%%','valuation_tiers_rent%%'])""")
    for idx, tbl in cur.fetchall():
        print(f"  VISIR {idx} tilheyrir NU toflunni {tbl}  (endurnefning skildi visinn eftir)")
    cur.execute("""SELECT count(*), count(DISTINCT model_version), max(model_version),
                          max(predicted_at)::text, max(calibration_version)
                   FROM public.predictions_rent""")
    print("  predictions_rent (LIVE): n=%s mv_distinct=%s mv=%s predicted_at=%s calib=%s" % cur.fetchone())

    # ---------- universe ----------
    u = pd.read_sql("""
        SELECT s.fastnum, s.segment, s.pred_mean, s.pred_lo80, s.pred_hi80,
               p.postnr, p.canonical_code AS cc_live, p.region_tier, p.fjherb,
               v.canonical_code AS cc_vt, v.threp AS threp_vt, v.flokkur AS flokkur_vt,
               v.n_local AS n_local_vt, v.fallback_lvl AS fb_vt, v.t5_astaeda AS ast_vt,
               v.herb_vantar AS herb_vt
        FROM public.predictions_rent s
        JOIN public.properties p USING (fastnum)
        JOIN public.valuation_tiers_rent v USING (fastnum)
    """, conn)
    print(f"\n  universe (predictions_rent x properties x valuation_tiers_rent): {len(u):,} radir")
    u["fallback_lvl"] = u.segment.map(fallback_lvl)
    u["n_conformal"] = u.segment.map(load_conformal_n()).astype("Int64")
    u["herb_vantar"] = u.fjherb.isna() | (u.fjherb <= 0)
    u["pi80"] = (u.pred_hi80 - u.pred_lo80) / u.pred_mean.replace(0, pd.NA)
    print(f"  segment-lykill oskilgreindur i conformal-JSON: {u.n_conformal.isna().sum():,}")
    print(f"  fallback_lvl ur segment vs vt.fallback_lvl mismunur: "
          f"{(u.fallback_lvl != u.fb_vt).sum():,}")
    print(f"  herb_vantar (lifandi properties) vs vt.herb_vantar mismunur: "
          f"{(u.herb_vantar != u.herb_vt).sum():,}")

    # ---------- B. FROSIN THETTLEIKA-LIND ----------
    hr("B. FROSIN THETTLEIKA-LIND — leiga_train.parquet gegn lifandi properties")
    c = pd.read_parquet(TRAIN, columns=["fastnum", "prop_postnr", "canonical_code",
                                        "contract_year"])
    c = c[c.contract_year >= 2021].copy()
    c["prop_postnr"] = pd.to_numeric(c.prop_postnr, errors="coerce")
    c = c.dropna(subset=["prop_postnr"]).astype({"prop_postnr": int})
    c["canonical_code"] = c.canonical_code.astype(object)
    live_cc = pd.read_sql("SELECT fastnum, canonical_code FROM public.properties", conn)
    c = c.merge(live_cc.rename(columns={"canonical_code": "cc_live"}), on="fastnum", how="left")
    print(f"  samningar 2021+ : {len(c):,}   an fastnum i properties: {c.cc_live.isna().sum():,}")
    breytt = (c.cc_live.notna()) & (c.canonical_code != c.cc_live)
    print(f"  samningar sem BREYTA merkingu vid reglu R: {breytt.sum():,} "
          f"({100*breytt.sum()/len(c):.2f}%)")
    print("  staerstu vixl (samningar):")
    for (a, b), n in (c[breytt].groupby(["canonical_code", "cc_live"]).size()
                      .sort_values(ascending=False).head(8).items()):
        print(f"    {a:>14} -> {b:<14} {n:>6,}")

    dens_stale = (c.groupby(["prop_postnr", "canonical_code"]).size()
                  .reset_index(name="n_local"))
    cl = c.copy()
    cl["cc_use"] = cl.cc_live.fillna(cl.canonical_code)
    dens_live = (cl.groupby(["prop_postnr", "cc_use"]).size()
                 .reset_index(name="n_local").rename(columns={"cc_use": "canonical_code"}))
    print(f"\n  sellur (postnr x cc): stale={len(dens_stale):,}  live-merkt={len(dens_live):,}")
    j = dens_stale.merge(dens_live, on=["prop_postnr", "canonical_code"], how="outer",
                         suffixes=("_stale", "_live")).fillna(0)
    print(f"  sellur thar sem n_local breytist: "
          f"{(j.n_local_stale != j.n_local_live).sum():,} af {len(j):,}")
    print(f"  sellur sem HVERFA (live=0): {(j.n_local_live == 0).sum():,}   "
          f"NYJAR sellur (stale=0): {(j.n_local_stale == 0).sum():,}")

    def n_local_af(cc_col: str, dens: pd.DataFrame) -> pd.Series:
        m = u[["postnr", cc_col]].merge(
            dens, how="left", left_on=["postnr", cc_col],
            right_on=["prop_postnr", "canonical_code"])
        return m.n_local.fillna(0).astype(int).set_axis(u.index)

    nl_S0 = n_local_af("cc_vt", dens_stale)
    nl_S1 = n_local_af("cc_live", dens_stale)
    nl_S2 = n_local_af("cc_live", dens_live)

    # ---------- C. HÓLFANIR ----------
    hr("C. THREP — thrjar hólfanir (sama regla, mismunandi forsendur)")
    S0 = threp_af(u, u.cc_vt, nl_S0)
    S1 = threp_af(u, u.cc_live, nl_S1)
    S2 = threp_af(u, u.cc_live, nl_S2)
    print("  ENDURGERD LIFANDI TOFLU (S0 gegn valuation_tiers_rent):")
    print(f"    threp mismunur   : {(S0.threp != u.threp_vt).sum():,}")
    print(f"    n_local mismunur : {(S0.n_local != u.n_local_vt).sum():,}")
    print(f"    flokkur mismunur : {(S0.flokkur.fillna('-') != u.flokkur_vt.fillna('-')).sum():,}")
    print(f"    t5_astaeda mism. : {(S0.t5_astaeda.fillna('-') != u.ast_vt.fillna('-')).sum():,}")
    print()
    dreifing("LIVE valuation_tiers_rent", u.threp_vt)
    dreifing("S0 stale cc + stale dens", S0.threp)
    dreifing("S1 LIVE cc + stale dens", S1.threp)
    dreifing("S2 LIVE cc + LIVE dens", S2.threp)
    print(f"\n  radir sem VIXLA threpi S0->S1: {(S1.threp != S0.threp).sum():,}")
    print(f"  radir sem VIXLA threpi S0->S2: {(S2.threp != S0.threp).sum():,}")
    print(f"  radir sem VIXLA threpi S1->S2: {(S2.threp != S1.threp).sum():,}  "
          "<- kostnadur thess ad LATA thettleikann FROSINN")
    print("\n  vixl-hólf S0->S2 (threp_fyrir -> threp_eftir, n):")
    for (a, b), n in (pd.crosstab(S0.threp, S2.threp).stack()
                      .loc[lambda s: s > 0].sort_values(ascending=False).head(14).items()):
        mark = "  (obreytt)" if a == b else ""
        print(f"    T{a} -> T{b}: {n:>7,}{mark}")
    print("\n  T5-astaedur:")
    for name, S in (("LIVE", u.ast_vt), ("S1", S1.t5_astaeda), ("S2", S2.t5_astaeda)):
        vc = S.value_counts(dropna=True)
        print(f"    {name:<5} " + "  ".join(f"{k}={v:,}" for k, v in vc.items()))

    # ---------- D. SEGMENT-ASINN (ólæknandi undir BANNI) ----------
    hr("D. SEGMENT-ASINN — mengunin sem endurbygging LAEKNAR EKKI")
    seg_cc = u.segment.str.split("|").str[0]
    ms = (seg_cc != u.cc_live)
    print(f"  radir thar sem segment-cc != lifandi cc: {ms.sum():,} "
          f"({100*ms.sum()/len(u):.2f}%)")
    print(f"  ... thar af myndi endurbygging skrifa cc_live i toflu OG halda "
          f"segment ur predictions_rent: MOTSOGN a somu rod.")
    print("  staerstu:")
    for (a, b), n in (u[ms].assign(s=seg_cc[ms]).groupby(["s", "cc_live"]).size()
                      .sort_values(ascending=False).head(8).items()):
        print(f"    segment-cc {a:>14} vs live {b:<14} {n:>6,}")
    print(f"\n  conformal-lyklar (n_conformal) eru eiginleiki SEGMENTS -> frosnir.")
    print(f"  fallback_lvl dreifing: {u.fallback_lvl.value_counts().sort_index().to_dict()}")

    conn.close()


if __name__ == "__main__":
    main()
