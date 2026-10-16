"""cc251_manadarsala_yoy.py — mánaðarsala á móti sama mánuði í fyrra → semantic.manadarsala_yoy.

Forskrift: D:\\_audit\\cc249_manadarsala\\SKIL_CC249.md §2 (m1), ákvörðun Danna 16.10 (cc251). regla_version cc251-v1.

  samningur  = FAERSLUNUMER í D:\\kaupskra.csv; íbúðasamningur = einhver lína TEGUND ∈ {Fjölbýli, Einbýli, Sérbýli}
  nothæfur   = ONOTHAEFUR_SAMNINGUR 0 á ÖLLUM línum; mánuður = UTGDAG (kaupsamningsdagur)
  velta      = KAUPVERD × 1000 kr, EINU sinni per samning (heildartala endurtekin per línu)
  hbs        = SVFN 0000/1000/1100/1300/1400/1604/1606 (cc237 HOFUDB)
  fullnusta  = q11: miðgildi yfir þroskaða mánuði M ∈ T−15…T−4 af hlut samninga M sem var þinglýstur
               ≤ (lok M) + (data_through + 1 d − lok T); bil = lægsta/hæsta. Reiknað per svæði.
  stada      = 'bradabirgda' ef fullnusta < 0,97, annars 'endanlegt'
  sama töf   = T−12 talinn með sömu þinglýsingartöf: þinglýst ≤ (lok T−12) + (data_through + 1 d − lok T)
  mánuðir    = FYRSTI_MANUDUR … síðasti heili mánuður fyrir data_through (yfirstandandi mánuður aldrei)

Notkun:
  python scripts/cc251_manadarsala_yoy.py                 # þurrkeyrsla: reiknar, prentar, skrifar ekkert
  python scripts/cc251_manadarsala_yoy.py --skrifa        # DELETE + INSERT regla_version í einni færslu
  --csv SLÓÐ                                              # vista útreikning (samanburður við cc249 m1)
DB: aðeins skrif á semantic.manadarsala_yoy, í einni færslu (SET TRANSACTION READ WRITE fyrst).
Exit: 0 í lagi · 2 hlið féll (ekkert skrifað) · 3 villa.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras

REGLA_VERSION = "cc251-v1"
KAUPSKRA = Path(r"D:\kaupskra.csv")
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
HBS = {"0000", "1000", "1100", "1300", "1400", "1604", "1606"}
IBUD = {"Fjölbýli", "Einbýli", "Sérbýli"}
FYRSTI_MANUDUR = pd.Period("2024-01", "M")
BRADABIRGDA_UNDIR = 0.97
# Hlið: kaupskráin þarf að vera fersk og heil áður en töflunni er skipt út.
HAMARKS_ALDUR_DAGA = 7      # data_through má ekki vera eldri en þetta (dagar frá keyrsludegi)
LAGMARK_SAMNINGA = 100_000  # nothæfir íbúðasamningar alls í skránni (16.10.2026: 161.942)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def lesa_samninga(slod: Path) -> tuple[pd.DataFrame, pd.Timestamp]:
    k = pd.read_csv(slod, sep=";", encoding="latin-1", dtype=str,
                    usecols=["FAERSLUNUMER", "SVFN", "UTGDAG", "THINGLYSTDAGS", "KAUPVERD", "TEGUND",
                             "ONOTHAEFUR_SAMNINGUR"])
    k["utg"] = pd.to_datetime(k.UTGDAG.str[:10])
    k["thl"] = pd.to_datetime(k.THINGLYSTDAGS.str[:19])
    k["ibud"] = k.TEGUND.str.strip().isin(IBUD)
    k["onot"] = k.ONOTHAEFUR_SAMNINGUR.astype(int)
    k["kv"] = pd.to_numeric(k.KAUPVERD, errors="coerce")
    data_through = k.thl.max().normalize()
    s = k.groupby("FAERSLUNUMER").agg(utg=("utg", "min"), thl=("thl", "min"), ibud=("ibud", "any"),
                                      onot=("onot", "max"), kv=("kv", "first"), kv_n=("kv", "nunique"),
                                      svfn=("SVFN", "first"))
    s = s[s.ibud & (s.onot == 0)].copy()
    if (s.kv_n > 1).any() or s.kv.isna().any():
        raise ValueError(f"KAUPVERD ekki einkvæmt/vantar: {(s.kv_n > 1).sum()} / {s.kv.isna().sum()} samningar")
    s["man"] = s.utg.dt.to_period("M")
    s["lok"] = (s.man + 1).dt.start_time          # fyrsti dagur næsta mánaðar = mánaðarlok
    s["tof"] = s.thl - s.lok                       # þinglýsingartöf eftir mánaðarlok
    s["velta"] = (s.kv * 1000).round().astype("int64")
    s["hbs"] = s.svfn.isin(HBS)
    return s[["man", "lok", "tof", "velta", "hbs"]], data_through


def reikna_svaedi(d: pd.DataFrame, data_through: pd.Timestamp, manudir: pd.PeriodIndex) -> pd.DataFrame:
    hop = {m: g for m, g in d.groupby("man")}
    tomt = d.iloc[:0]
    rows = []
    for t in manudir:
        # Tími sem nú er liðinn frá lokum T (sama skilgreining og cc232/cc237 q11).
        off = data_through + pd.Timedelta(days=1) - (t + 1).start_time
        g = hop.get(t, tomt)
        f = hop.get(t - 12, tomt)
        hl = [float((hop.get(m, tomt).tof <= off).mean()) for m in pd.period_range(t - 15, t - 4, freq="M")
              if len(hop.get(m, tomt))]
        f_st = f[f.tof <= off]
        rows.append(dict(
            manudur=t.start_time.date(), n=len(g), velta=int(g.velta.sum()),
            n_fyrra_nu=len(f), velta_fyrra_nu=int(f.velta.sum()),
            n_fyrra_sama_tof=len(f_st), velta_fyrra_sama_tof=int(f_st.velta.sum()),
            fullnusta=float(np.median(hl)) if hl else None,
            fullnusta_min=min(hl) if hl else None, fullnusta_max=max(hl) if hl else None,
        ))
    r = pd.DataFrame(rows)
    r["stada"] = np.where(r.fullnusta.isna(), None,
                          np.where(r.fullnusta < BRADABIRGDA_UNDIR, "bradabirgda", "endanlegt"))
    return r


def reikna(s: pd.DataFrame, data_through: pd.Timestamp) -> pd.DataFrame:
    sidasti = data_through.to_period("M") - 1
    manudir = pd.period_range(FYRSTI_MANUDUR, sidasti, freq="M")
    ut = []
    for svaedi, d in (("land", s), ("hbs", s[s.hbs])):
        r = reikna_svaedi(d, data_through, manudir)
        r.insert(0, "svaedi", svaedi)
        ut.append(r)
    return pd.concat(ut, ignore_index=True)


def hlid(s: pd.DataFrame, r: pd.DataFrame, data_through: pd.Timestamp) -> list[str]:
    fall = []
    aldur = (pd.Timestamp(dt.date.today()) - data_through).days
    if aldur > HAMARKS_ALDUR_DAGA:
        fall.append(f"kaupskrá gömul: data_through {data_through.date()} ({aldur} d)")
    if len(s) < LAGMARK_SAMNINGA:
        fall.append(f"of fáir samningar: {len(s)} < {LAGMARK_SAMNINGA}")
    sidasti = r[r.svaedi == "land"].iloc[-1]
    if sidasti.n <= 0:
        fall.append(f"síðasti mánuður {sidasti.manudur} hefur 0 samninga")
    if r.fullnusta.isna().any():
        fall.append(f"fullnusta ómæld í {int(r.fullnusta.isna().sum())} röðum")
    return fall


def skrifa(r: pd.DataFrame, data_through: pd.Timestamp) -> int:
    reiknad = dt.datetime.now(dt.timezone.utc)
    cols = ["svaedi", "manudur", "n", "velta", "n_fyrra_nu", "velta_fyrra_nu", "n_fyrra_sama_tof",
            "velta_fyrra_sama_tof", "fullnusta", "fullnusta_min", "fullnusta_max", "stada"]
    vals = [(REGLA_VERSION, *[None if (isinstance(v, float) and np.isnan(v)) else
                               (round(v, 4) if isinstance(v, float) else (int(v) if isinstance(v, np.integer) else v))
                               for v in row], reiknad, data_through.date())
            for row in r[cols].itertuples(index=False, name=None)]
    c = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip(), connect_timeout=15)
    try:
        cur = c.cursor()
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("SET LOCAL lock_timeout = '10s'")
        cur.execute("SET LOCAL statement_timeout = '120s'")
        cur.execute("DELETE FROM semantic.manadarsala_yoy WHERE regla_version = %s", (REGLA_VERSION,))
        eytt = cur.rowcount
        psycopg2.extras.execute_values(
            cur, "INSERT INTO semantic.manadarsala_yoy (regla_version, " + ", ".join(cols) +
                 ", reiknad, data_through) VALUES %s", vals, page_size=1000)
        cur.execute("SELECT count(*), sum(n) FROM semantic.manadarsala_yoy WHERE regla_version = %s", (REGLA_VERSION,))
        n_rod, n_sum = cur.fetchone()
        if n_rod != len(r) or int(n_sum) != int(r.n.sum()):
            c.rollback()
            print(f"[HLIÐ] teljari í töflu {n_rod}/{n_sum} ≠ DataFrame {len(r)}/{int(r.n.sum())} — ROLLBACK")
            return 2
        c.commit()
        print(f"[SKRIFAÐ] {REGLA_VERSION}: {eytt} eytt, {n_rod} raðir skrifaðar (Σn {n_sum}), data_through {data_through.date()}")
        return 0
    finally:
        c.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skrifa", action="store_true")
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--kaupskra", type=Path, default=KAUPSKRA)
    a = ap.parse_args()
    try:
        s, data_through = lesa_samninga(a.kaupskra)
        r = reikna(s, data_through)
        print(f"kaupskrá {a.kaupskra}: {len(s)} nothæfir íbúðasamningar, data_through {data_through.date()}")
        syn = r[r.manudur >= (data_through.to_period("M") - 3).start_time.date()]
        print(syn.to_string(index=False))
        if a.csv:
            r.to_csv(a.csv, index=False)
        fall = hlid(s, r, data_through)
        if fall:
            print("[HLIÐ FÉLL] " + " · ".join(fall) + " — ekkert skrifað")
            return 2
        if not a.skrifa:
            print("[ÞURRKEYRSLA] ekkert skrifað (--skrifa til að skrifa)")
            return 0
        return skrifa(r, data_through)
    except Exception as ex:
        print(f"[VILLA] {type(ex).__name__}: {ex}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
