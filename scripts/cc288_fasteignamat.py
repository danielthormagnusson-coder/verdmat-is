# -*- coding: utf-8 -*-
"""cc288 — fasteignamat HMS á /markadur: hleðsla mats eftir árgerð + röðun gatna og svæða.

EKKI í næturkeðju. Keyrt handvirkt:
  · eftir nýja HMS-sókn (birt mat næsta árs, júní) og
  · við árgerðaskipti (31.12: þá verður ARGERD 2027 og breytingin 2027→2028 þegar hún er til).

  python scripts/cc288_fasteignamat.py --dryrun  [--safn D:/HMS_jonas/hms_archive_staging.db]
  python scripts/cc288_fasteignamat.py --skrifa  [--safn ...]

--dryrun reiknar allt og prentar samantekt, skrifar EKKERT (read-only tenging).
--skrifa: í EINNI færslu → (1) fasteignamat_argerd: árgerð 2026 úr properties.fasteignamat_hms, árgerð 2027 úr safni
          (fasteignamat_naesta_ar) → (2) röðun reiknuð úr DB-töflunum → (3) ný keyrsla, gömul óvirk → COMMIT.

GRUNNREGLA 8: les ALDREI predictions, comps eða þrep. Aðeins properties (eigindi), semantic.fasteignamat_argerd
og semantic.atvinnu_flokkun. Sjá prof_regla8 í prófunum.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from datetime import date

import numpy as np
import pandas as pd

REGLA = "cc288-v3"
ARGERD = 2026
ARGERD_BREYTING = 2027
LAGMARK_N = 5
IBUD_M2 = (60, 150)          # stærðarbil aðalröðunar íbúða (Á2)
IBUD_GILD_M2 = (20, 500)     # hreinsun: jarðir bera land í einflm, heil fjölbýli á einu fastanúmeri
GEYMSLUBIL_M2 = 50           # cc288-v2: eining í iðnaði/lager undir 50 m² = geymslubil → talin, ekki raðað (D:/_audit/cc288_fasteignamat/d2_mork.out)
RADAFLOKKAR = ("verslun", "skrifstofa", "idnadur_lager", "gisting")
FJOLBYLI = ("APT_FLOOR", "APT_STANDARD", "APT_BASEMENT", "APT_ATTIC")
SERBYLI = ("SFH_DETACHED", "ROW_HOUSE", "SEMI_DETACHED")
SAFN_SJALFGEFID = r"D:\HMS_jonas\hms_archive_staging.db"
LAGM_THEKJA = 0.95           # hlið: hlutfall fullmetinna eininga með mat í ARGERD

_BIL = re.compile(r"\s+")
_GATA = re.compile(r"^(\D+?)\s+(\d+)\s*([A-Za-zÁÐÉÍÓÚÝÞÆÖáðéíóúýþæö]?)\b")


def norm(t):
    """Bil normuð + btrim. None/NaN → None."""
    if not isinstance(t, str):
        return None
    s = _BIL.sub(" ", t).strip()
    return s or None


def gata_ur(heimilisfang):
    """'Laugavegur 18a' → ('Laugavegur', '18A'); án húsnúmers → (None, None)."""
    h = norm(heimilisfang)
    if not h:
        return None, None
    m = _GATA.match(h)
    if not m:
        return None, None
    return m.group(1).strip(), m.group(2) + m.group(3).upper()


# ------------------------------------------------------------------ lestur
PROP_SQL = """
select fastnum, heimilisfang, postnr, svfn, sveitarfelag, tegund_raw, canonical_code, unit_family,
       is_residential, einflm, matsstig, coalesce(deregistered, false) as deregistered,
       matsvaedi_numer, matsvaedi_nafn
  from public.properties
"""


def lesa(cur):
    cur.execute(PROP_SQL)
    p = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    cur.execute("select fastnum, argerd, mat_thkr from semantic.fasteignamat_argerd where argerd in (%s, %s)",
                (ARGERD, ARGERD_BREYTING))
    m = pd.DataFrame(cur.fetchall(), columns=["fastnum", "argerd", "mat_thkr"])
    cur.execute("select tegund, flokkur, radast from semantic.atvinnu_flokkun")
    f = pd.DataFrame(cur.fetchall(), columns=["tegund", "flokkur", "radast"])
    # psycopg2 skilar numeric sem Decimal — float hér svo reikningurinn sé sá sami og á skyndimyndum
    m["mat_thkr"] = m.mat_thkr.astype(float)
    p["einflm"] = pd.to_numeric(p.einflm.astype(object).map(lambda x: None if x is None else float(x)), errors="coerce")
    for col in ("postnr", "svfn", "matsvaedi_numer"):
        p[col] = pd.to_numeric(p[col].astype(object).map(lambda x: None if x is None else float(x)), errors="coerce")
    return p, m, f


# ------------------------------------------------------------------ reikningur (hrein föll, einingaprófuð)
def _flokka(p: pd.DataFrame, m: pd.DataFrame, f: pd.DataFrame):
    """Sameiginlegur grunnur beggja þýða: flokkur, mat (ARGERD og breytingarárgerð), normuð heiti, talning."""
    d = p.copy()
    for c in ("einflm", "postnr", "svfn", "matsvaedi_numer", "fastnum"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["svf"] = d.sveitarfelag.map(norm)
    d["teg_n"] = d.tegund_raw.map(norm)
    fl = dict(zip(f.tegund, f.flokkur))
    d["flokkur"] = d.teg_n.map(fl)
    d.loc[d.unit_family == "main", "flokkur"] = "ibud"
    # óflokkað = ekki-íbúð sem er ekki í flokkunartöflunni
    ekki_ibud = ~d.is_residential.fillna(False).astype(bool)
    talning = {
        "ibud_main": int((d.unit_family == "main").sum()),
        "ibud_aukaflokkur_utan": int((d.unit_family == "secondary").sum()),
        "ekki_ibud": int(ekki_ibud.sum()),
        "oflokkad": int((ekki_ibud & d.flokkur.isna()).sum()),
        "flokkar": {k: int(v) for k, v in d.loc[ekki_ibud, "flokkur"].value_counts().items()},
    }
    mat = m.pivot_table(index="fastnum", columns="argerd", values="mat_thkr", aggfunc="first")
    d["mat"] = d.fastnum.map(mat[ARGERD]) if ARGERD in mat else np.nan
    d["mat_b"] = d.fastnum.map(mat[ARGERD_BREYTING]) if ARGERD_BREYTING in mat else np.nan
    return d, talning


def _afleitt(e: pd.DataFrame) -> pd.DataFrame:
    e["hopur"] = e.flokkur
    e["teg"] = np.where(e.canonical_code.isin(FJOLBYLI), "fjolbyli", np.where(e.canonical_code.isin(SERBYLI), "serbyli", None))
    e["kr_m2"] = e.mat * 1000 / e.einflm.where(e.einflm > 0)
    e["i_bili"] = np.where(e.hopur == "ibud", e.einflm.between(*IBUD_M2), True)  # atvinnu: allar einingar flokks
    g = e.heimilisfang.map(gata_ur)
    e["gata"] = [a for a, _ in g]
    return e


def undirbua(p: pd.DataFrame, m: pd.DataFrame, f: pd.DataFrame):
    """→ (SÍAÐA þýðið: einingar með hopur/tegund/mat/kr_m2/gata, talning-dict). Engin röðun hér."""
    d, talning = _flokka(p, m, f)
    hop = d.flokkur.isin(("ibud",) + RADAFLOKKAR)
    trappa = {}
    e = d[hop].copy(); trappa["0_flokkur"] = len(e)
    e = e[~e.deregistered.astype(bool)]; trappa["1_ekki_afskrad"] = len(e)
    e = e[e.mat > 0]; trappa[f"2_mat_{ARGERD}"] = len(e)
    e = e[e.matsstig.isin(["7", "8"])]; trappa["3_fullmetid_matsstig_7_8"] = len(e)
    e = e[e.einflm > 0]; trappa["4_flatarmal"] = len(e)
    lo, hi = IBUD_GILD_M2
    e = e[(e.flokkur != "ibud") | e.einflm.between(lo, hi)]; trappa["5_ibud_20_500_m2"] = len(e)
    # cc288-v2 (ákv. Danna 31.10): geymslubil sem skráð eru iðnaður/lager (Móhella, Desjamýri o.fl.) — regla á tegund+stærð,
    # aldrei á heimilisföng. Talin í talning["geymslubil"], aldrei raðað.
    gb = (e.flokkur == "idnadur_lager") & (e.einflm < GEYMSLUBIL_M2)
    talning["geymslubil"] = int(gb.sum())
    e = e[~gb]; trappa["6_geymslubil_ut"] = len(e)
    talning["trappa"] = trappa
    talning["thydi"] = {k: int(v) for k, v in e.flokkur.value_counts().items()}
    return _afleitt(e), talning


def heildarthydi(p: pd.DataFrame, m: pd.DataFrame, f: pd.DataFrame):
    """cc288-v3: VÍÐA þýðið fyrir samanlagt mat — allar einingar hópsins með mat > 0, ekki afskráðar, óháð matsstigi og
    stærð (heilt fjölbýli á einu fastanúmeri = EIN eining með fullu mati). Geymslubil (v2) utan. → (eH, talning_heild)."""
    d, _ = _flokka(p, m, f)
    h = d[d.flokkur.isin(("ibud",) + RADAFLOKKAR) & ~d.deregistered.astype(bool) & (d.mat > 0)].copy()
    gb = (h.flokkur == "idnadur_lager") & (h.einflm < GEYMSLUBIL_M2)
    h = h[~gb]
    if h.fastnum.duplicated().any():  # vörn: hvert fastanúmer einu sinni
        raise RuntimeError("heildarþýði: tvítekið fastanúmer")
    return _afleitt(h), {"geymslubil_heild": int(gb.sum()), "thydi_heild": {k: int(v) for k, v in h.flokkur.value_counts().items()}}


def _hopar(e, eH):
    """(hopur, tegund, síað undirmengi, heildar-undirmengi): íbúðir allt/fjölbýli/sérbýli; atvinnu per flokk;
    + cc288-v3 „atvinnu“ = atvinnu samanlagt, AÐEINS heildarmælikvarðinn (síaða mengið tómt)."""
    for h in ("ibud",) + RADAFLOKKAR:
        s, sh = e[e.hopur == h], eH[eH.hopur == h]
        yield h, "allt", s, sh
        if h == "ibud":
            yield h, "fjolbyli", s[s.teg == "fjolbyli"], sh[sh.teg == "fjolbyli"]
            yield h, "serbyli", s[s.teg == "serbyli"], sh[sh.teg == "serbyli"]
    yield "atvinnu", "allt", e.iloc[0:0], eH[eH.hopur.isin(RADAFLOKKAR)]


def _mode(v):
    v = v.dropna()
    return v.mode().iloc[0] if len(v) else None


_SIAD = ["n", "heildarmat_thkr", "midg_mat_eign_thkr", "midg_flm", "n_kr_m2", "midg_kr_m2", "n_breyting", "breyting_pct"]


def _samantekt(s: pd.DataFrame, keys: list[str]):
    if s.empty:
        return pd.DataFrame(columns=keys + _SIAD)
    g = s.groupby(keys, dropna=True, sort=True)
    t = g.agg(n=("fastnum", "size"), heildarmat_thkr=("mat", "sum"), midg_mat_eign_thkr=("mat", "median"),
              midg_flm=("einflm", "median")).reset_index()
    b = s[s.i_bili].groupby(keys, dropna=True).agg(n_kr_m2=("fastnum", "size"), midg_kr_m2=("kr_m2", "median")).reset_index()
    bb = s[s.mat_b > 0].groupby(keys, dropna=True).agg(n_breyting=("fastnum", "size"), _s26=("mat", "sum"), _s27=("mat_b", "sum")).reset_index()
    t = t.merge(b, on=keys, how="left").merge(bb, on=keys, how="left")
    t["n_kr_m2"] = t.n_kr_m2.fillna(0).astype(int)
    t["n_breyting"] = t.n_breyting.fillna(0).astype(int)
    t["breyting_pct"] = (t._s27 / t._s26 - 1) * 100
    return t.drop(columns=["_s26", "_s27"])


def _samantekt_heild(sh: pd.DataFrame, keys: list[str]):
    if sh.empty:
        return pd.DataFrame(columns=keys + ["n_heild", "heildarmat_heild_thkr", "midg_mat_heild_thkr"])
    return sh.groupby(keys, dropna=True, sort=True).agg(n_heild=("fastnum", "nunique"), heildarmat_heild_thkr=("mat", "sum"),
                                                      midg_mat_heild_thkr=("mat", "median")).reset_index()


def _sameina(s, sh, keys):
    t = _samantekt(s, keys).merge(_samantekt_heild(sh, keys), on=keys, how="outer")
    for c in ("n", "n_kr_m2", "n_breyting", "n_heild"):
        t[c] = pd.to_numeric(t[c]).fillna(0).astype(int)
    for c in ("heildarmat_thkr", "midg_mat_eign_thkr", "midg_flm", "midg_kr_m2", "breyting_pct",
              "heildarmat_heild_thkr", "midg_mat_heild_thkr"):
        t[c] = pd.to_numeric(t[c], errors="coerce").astype(float)
    return t


def _meta(s, sh, keys, **agg):
    """Lýsigögn (svf, matsvæði …) úr síaða menginu fyrst (= v2 orðrétt), annars úr heildarmenginu."""
    a = s.groupby(keys).agg(**agg) if not s.empty else None
    b = sh.groupby(keys).agg(**agg) if not sh.empty else None
    if a is None and b is None:  # ekkert mengi ber lykil (t.d. engin gata greind) — tómt, sama snið
        return pd.DataFrame(columns=list(agg)).rename_axis(keys[0] if len(keys) == 1 else None)
    if a is None:
        return b
    return a if b is None else a.combine_first(b)


def reikna(e: pd.DataFrame, eH: pd.DataFrame | None = None) -> pd.DataFrame:
    """Allar röðunarraðir. Miðgildi/breyting/samtala NULL undir LAGMARK_N (sama regla og CHECK í töflunni).
    eH = víða þýðið (cc288-v3); None → síaða þýðið notað (próf)."""
    if eH is None:
        eH = e
    ut = []
    for h, teg, s, sh in _hopar(e, eH):
        if s.empty and sh.empty:
            continue
        # götur
        sg, shg = s[s.gata.notna() & s.postnr.notna()], sh[sh.gata.notna() & sh.postnr.notna()]
        t = _sameina(sg, shg, ["gata", "postnr"])
        if t.empty:
            meta = None
        else:
            meta = _meta(sg, shg, ["gata", "postnr"], svfn=("svfn", _mode), svf=("svf", _mode), matsvaedi_numer=("matsvaedi_numer", _mode))
        if meta is not None:
            t = t.join(meta, on=["gata", "postnr"])
            t["stig"] = "gata"; t["lykill"] = [f"{g}|{int(pn)}" for g, pn in zip(t.gata, t.postnr)]; t["heiti"] = t.gata
            ut.append(t.assign(hopur=h, tegund=teg))
        # svæði
        for stig, keys in (("matsvaedi", ["matsvaedi_numer"]), ("postnr", ["postnr"]), ("svf", ["svfn"])):
            t = _sameina(s, sh, keys)
            if stig == "matsvaedi":
                nofn = _meta(s, sh, ["matsvaedi_numer"], nafn=("matsvaedi_nafn", _mode)).nafn
                t["heiti"] = t.matsvaedi_numer.map(nofn).map(norm)
                t["heiti"] = [hh if isinstance(hh, str) else f"Matsvæði {int(k)}" for hh, k in zip(t.heiti, t.matsvaedi_numer)]
                t["lykill"] = [str(int(k)) for k in t.matsvaedi_numer]
                t = t.join(_meta(s, sh, ["matsvaedi_numer"], svfn=("svfn", _mode), svf=("svf", _mode)), on="matsvaedi_numer")
            elif stig == "postnr":
                t["lykill"] = [str(int(k)) for k in t.postnr]; t["heiti"] = t.lykill
                t = t.join(_meta(s, sh, ["postnr"], svfn=("svfn", _mode), svf=("svf", _mode)), on="postnr")
            else:
                nofn = _meta(s, sh, ["svfn"], svf=("svf", _mode)).svf
                t["svf"] = t.svfn.map(nofn)
                t["heiti"] = [hh if isinstance(hh, str) else f"Sveitarfélag {int(k)}" for hh, k in zip(t.svf, t.svfn)]
                t["lykill"] = [str(int(k)) for k in t.svfn]
            t["stig"] = stig
            ut.append(t.assign(hopur=h, tegund=teg))
        # landið
        t = _sameina(s.assign(_l="land"), sh.assign(_l="land"), ["_l"]).drop(columns="_l")
        t["stig"] = "land"; t["lykill"] = "land"; t["heiti"] = "Landið"
        ut.append(t.assign(hopur=h, tegund=teg))
    r = pd.concat(ut, ignore_index=True)
    for c in ("gata", "postnr", "matsvaedi_numer", "svfn", "svf"):
        if c not in r:
            r[c] = None
    r.loc[r.n_kr_m2 < LAGMARK_N, "midg_kr_m2"] = np.nan
    r.loc[r.n < LAGMARK_N, "midg_mat_eign_thkr"] = np.nan
    r.loc[r.n_breyting < LAGMARK_N, "breyting_pct"] = np.nan
    r.loc[r.n_heild < LAGMARK_N, ["heildarmat_heild_thkr", "midg_mat_heild_thkr"]] = np.nan
    r.loc[r.n == 0, ["heildarmat_thkr", "midg_flm"]] = np.nan
    r["argerd"] = ARGERD
    return r[["argerd", "hopur", "tegund", "stig", "lykill", "heiti", "gata", "postnr", "matsvaedi_numer", "svfn", "svf",
              "n", "n_kr_m2", "midg_kr_m2", "midg_mat_eign_thkr", "heildarmat_thkr", "midg_flm", "n_breyting", "breyting_pct",
              "n_heild", "heildarmat_heild_thkr", "midg_mat_heild_thkr"]]


def md5_df(df: pd.DataFrame) -> str:
    s = df.sort_values(["hopur", "tegund", "stig", "lykill"]).round(6).to_csv(index=False, lineterminator="\n")
    return hashlib.md5(s.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ hleðsla mats
def hlada_argerd(cur, safn: str):
    """2026 úr properties (server-side), 2027 úr safni. Skilar (sott_argerd, sott_breyting, n26, n27)."""
    from psycopg2.extras import execute_values
    cur.execute("delete from semantic.fasteignamat_argerd where argerd in (%s, %s)", (ARGERD, ARGERD_BREYTING))
    cur.execute("""insert into semantic.fasteignamat_argerd (fastnum, argerd, mat_thkr, lhlmat_thkr, heimild, sott)
                   select fastnum, fasteignamat_hms_argerd, fasteignamat_hms, lhlmat, 'properties.fasteignamat_hms', fasteignamat_hms_sott
                     from public.properties
                    where fasteignamat_hms_argerd = %s and fasteignamat_hms > 0 and fasteignamat_hms_sott is not null""", (ARGERD,))
    n26 = cur.rowcount
    cur.execute("select max(fasteignamat_hms_sott) from public.properties where fasteignamat_hms_argerd = %s", (ARGERD,))
    sott26 = cur.fetchone()[0]
    s = sqlite3.connect(f"file:{safn}?mode=ro", uri=True)
    rows, sott27 = [], None
    for fn, fd, fa in s.execute("select fastnum, fasteign_data, fetched_at from hms_fasteign where http_status = 200 and fasteign_data is not null"):
        try:
            d = json.loads(fd)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        # árgerðarvörn: safnreiturinn fasteignamat verður að vera árgerð ARGERD (= properties.fasteignamat_hms) — prófað utan lykkju
        v = d.get("fasteignamat_naesta_ar")
        if v and v > 0:
            dd = date.fromisoformat(fa[:10])
            rows.append((int(fn), ARGERD_BREYTING, v, d.get("lhlmat_naesta_ar"), "hms_safn.fasteignamat_naesta_ar", dd))
            sott27 = max(sott27, dd) if sott27 else dd
    s.close()
    execute_values(cur, "insert into semantic.fasteignamat_argerd (fastnum, argerd, mat_thkr, lhlmat_thkr, heimild, sott) values %s",
                   rows, page_size=5000)
    return sott26, sott27, n26, len(rows)


def argerd_vorn(cur, safn: str) -> tuple[int, int]:
    """Safnreiturinn `fasteignamat` verður að jafngilda properties.fasteignamat_hms (árgerð ARGERD) — annars er
    `naesta_ar` ekki ARGERD+1. Skilar (jafnt, borið saman)."""
    cur.execute("select fastnum, fasteignamat_hms from public.properties where fasteignamat_hms_argerd = %s and fasteignamat_hms > 0", (ARGERD,))
    prop = dict(cur.fetchall())
    s = sqlite3.connect(f"file:{safn}?mode=ro", uri=True)
    jafnt = alls = 0
    for fn, fd in s.execute("select fastnum, fasteign_data from hms_fasteign where http_status = 200 and fasteign_data is not null"):
        if fn not in prop:
            continue
        try:
            v = json.loads(fd).get("fasteignamat")
        except (ValueError, AttributeError):
            continue
        alls += 1
        jafnt += int(v is not None and float(v) == float(prop[fn]))
    s.close()
    return jafnt, alls


def skrifa_rodun(cur, r: pd.DataFrame, talning: dict, sott26, sott27, athugasemd="") -> int:
    from psycopg2.extras import execute_values
    cur.execute("update semantic.fasteignamat_keyrslur set virk = false where virk")
    cur.execute("""insert into semantic.fasteignamat_keyrslur (regla_version, argerd, argerd_breyting, sott_argerd, sott_breyting,
                     lagmark_n, staerdarbil_ibud, talning, n_rodun, md5_rodun, virk, athugasemd)
                   values (%s,%s,%s,%s,%s,%s,numrange(%s,%s,'[]'),%s,%s,%s,true,%s) returning keyrsla_id""",
                (REGLA, ARGERD, ARGERD_BREYTING if sott27 else None, sott26, sott27, LAGMARK_N, IBUD_M2[0], IBUD_M2[1],
                 json.dumps(talning, ensure_ascii=False), len(r), md5_df(r), athugasemd))
    kid = cur.fetchone()[0]
    cols = list(r.columns)

    def nn(x):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return None
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.floating,)):
            return float(x)
        return x
    vals = [[kid] + [nn(x) for x in row] for row in r.itertuples(index=False, name=None)]
    execute_values(cur, f"insert into semantic.fasteignamat_rodun (keyrsla_id, {', '.join(cols)}) values %s", vals, page_size=5000)
    # eldri keyrslur: röðunarraðir fjarlægðar (keyrsluskráin stendur sem saga)
    cur.execute("delete from semantic.fasteignamat_rodun where keyrsla_id <> %s", (kid,))
    return kid


def keyra(cur, safn: str, skrifa: bool, athugasemd: str = "") -> dict:
    """Allt ferlið á gefnum bendli (færslu stýrir kallandi). skrifa=False → engin skrif (dryrun reiknar úr núverandi töflum
    ef þær eru til, annars úr properties beint)."""
    jafnt, alls = argerd_vorn(cur, safn)
    if not alls or jafnt / alls < 0.99:
        raise RuntimeError(f"árgerðarvörn: safn.fasteignamat = properties.fasteignamat_hms á {jafnt}/{alls} — naesta_ar er ekki {ARGERD_BREYTING}")
    sott26 = sott27 = None
    if skrifa:
        sott26, sott27, n26, n27 = hlada_argerd(cur, safn)
    p, m, f = lesa(cur)
    if not skrifa and m.empty:
        raise RuntimeError("fasteignamat_argerd tóm — --dryrun þarf beitta migration + hleðslu, eða keyrðu innan --prof")
    e, talning = undirbua(p, m, f)
    eH, th = heildarthydi(p, m, f)
    talning.update(th)
    thekja = float((e.mat > 0).mean()) if len(e) else 0.0
    full = talning["trappa"]["3_fullmetid_matsstig_7_8"] / max(talning["trappa"]["1_ekki_afskrad"], 1)
    if full < LAGM_THEKJA:
        raise RuntimeError(f"þekjuvörn: aðeins {full:.1%} eininga með fullt mat {ARGERD}")
    r = reikna(e, eH)
    ut = {"arg_vorn": f"{jafnt}/{alls}", "talning": talning, "n_rodun": len(r), "md5": md5_df(r), "thekja": thekja}
    if skrifa:
        ut["keyrsla_id"] = skrifa_rodun(cur, r, talning, sott26, sott27, athugasemd)
        ut["n_argerd"] = {"2026": n26, "2027": n27}
    ut["rodun"] = r
    return ut


def main() -> int:
    import psycopg2
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dryrun", action="store_true")
    g.add_argument("--skrifa", action="store_true")
    ap.add_argument("--safn", default=SAFN_SJALFGEFID)
    ap.add_argument("--dsn", default=r"D:\verdmat-is\.dbconfig")
    a = ap.parse_args()
    c = psycopg2.connect(open(a.dsn, encoding="utf-8-sig").read().strip(), connect_timeout=15)
    try:
        if a.dryrun:
            c.set_session(readonly=True)
        c.autocommit = False
        cur = c.cursor()
        if a.skrifa:
            # Pooler-gildran (CLAUDE.md, WORKING_PROTOCOL (h)): bakendi getur borið lekið session-SET
            # default_transaction_read_only=on — rollback FYRST, svo SET TRANSACTION READ WRITE (cc288: féll á þessu 31.10).
            c.rollback()
            cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("SET LOCAL lock_timeout = '10s'"); cur.execute("SET LOCAL statement_timeout = '300s'")
        ut = keyra(cur, a.safn, skrifa=a.skrifa)
        if a.skrifa:
            c.commit()
        else:
            c.rollback()
        print(json.dumps({k: v for k, v in ut.items() if k != "rodun"}, ensure_ascii=False, indent=1, default=str))
        return 0
    except Exception as ex:
        c.rollback()
        print(f"[VILLA] {type(ex).__name__}: {ex}")
        return 3
    finally:
        c.close()


if __name__ == "__main__":
    sys.exit(main())
