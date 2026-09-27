"""cc213_fasteignasala_manudur.py — mánaðarleg röðun fasteignasala (stofur + salar).

Forskrift: D:\\_audit\\cc212_fasteignasalar\\SKIL_CC212.md §5, cc212b §4–5, ákvarðanir Danna 27.09.
Keyrsla: 16. hvers mánaðar (kaupskrá 15. dags lesin 02:30). Idempotent per (tímabil, gluggi, regla_version).

Skilgreiningar (regla_version cc213-v1):
  samningur   = FAERSLUNUMER í D:\\kaupskra.csv; íbúð = einhver lína TEGUND ∈ {Fjölbýli, Einbýli, Sérbýli};
                ONOTHAEFUR_SAMNINGUR = 0 á öllum línum; kaupsamningsdagur K = UTGDAG; velta = KAUPVERD×1000 óskipt.
  nýbygging   = regla 5: FULLBUID=0 ∨ BYGGAR ≥ ár(K)−2 á einhverri línu.
  auglýsing   = scraper.listings (tenure='sale', fastnum á samningi), bil [min(listed_at, first_seen_at),
                max(withdrawn_at, last_seen_at)], sem skarast [K−180, K+30].
  eignun      = virk á K → annars síðasta sem hófst ≤ K → annars fyrsta sem hófst í (K, K+30]; jafntefli á listing_id.
  stofa       = scraper.fasteignasala_vorumerki.lykill fyrir agency_source_id (sala_id er ekki stofulykill).
  sali        = sali_utdrattur.extract() á texta eignaðrar auglýsingar (UTGAFA sali_v3) → semantic.sali_kort;
                dealer_email ef enginn texti gefur nafn. Fjöldi óskiptur (hver skráður sali fær söluna);
                velta skipt jafnt milli skráðra sala.
  gólf        = stofa: n_eignadar_stofu / n_samningar ≥ 0,70 og fullnusta ≥ 90 %, annars 'ohaeft'.
                sali: n_med_sala / n_eignadar_stofu ≥ 0,80, annars 'undir_golfi'.
  staða       = 'bradabirgda' fyrir 1. dag M+3, síðan 'endanlegt'.
  gluggar     = 'manudur' (M) og 'fra_juli_2026' (2026-07 … M; ársgluggi „síðan júlí 2026").
  sæti        = deilt: rank() (1, 1, 3). Vistað sæti ≤ TOPP (10), með jafntefli.

Notkun:
  python scripts/cc213_fasteignasala_manudur.py --man 2026-08 [--man 2026-07] [--dry-run]
  python scripts/cc213_fasteignasala_manudur.py --sjalfvirkt          # 2026-07 … síðasti mánuður m/ fullnustu ≥ 90 %
DB: les á pooler read-only; skrif í einni færslu (SET TRANSACTION READ WRITE fyrst). --dry-run rúllar til baka.
Exit: 0 í lagi · 3 villa.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sali_utdrattur import UTGAFA, Nafnaskra, candidates, extract, fold, personal_emails, same_person  # noqa: E402

REGLA_VERSION = "cc213-v1"
KAUPSKRA = Path(r"D:\kaupskra.csv")
PARSED_MBL = Path(r"D:\verdmat-is\scraper_data\parsed_mbl.db")
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
W_DAGAR, EFTIR_DAGAR = 180, 30
EIGNUN_GOLF, SALI_GOLF, FULLNUSTA_GOLF = 0.70, 0.80, 90.0
GLUGGI_UPPHAF = pd.Period("2026-07", "M")
TOPP = 10
IBUD = {"Fjölbýli", "Einbýli", "Sérbýli"}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def slug(s: str) -> str:
    s = fold(s)
    s = re.sub(r"\b(ehf|slf|hf|fasteignasala|fasteignasalan|fasteignamidlun|fasteignir|fast\.?|og radgj\.?)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "ohekkt"


# ---------------------------------------------------------------------------- lestur
def lesa_kaupskra() -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    k = pd.read_csv(KAUPSKRA, sep=";", encoding="latin-1", dtype=str)
    k["utg"] = pd.to_datetime(k.UTGDAG.str[:10])
    k["thgl"] = pd.to_datetime(k.THINGLYSTDAGS.str[:19])
    k["fastnum"] = k.FASTNUM.astype("int64")
    k["kaupverd"] = k.KAUPVERD.astype("int64") * 1000
    k["byggar"] = pd.to_numeric(k.BYGGAR, errors="coerce")
    k["fullbuid"] = pd.to_numeric(k.FULLBUID, errors="coerce")
    k["ibud"] = k.TEGUND.str.strip().isin(IBUD)
    k["onoth"] = k.ONOTHAEFUR_SAMNINGUR.astype(int)
    k["nyb"] = (k.fullbuid == 0) | (k.byggar >= k.utg.dt.year - 2)
    sott = pd.Timestamp.fromtimestamp(KAUPSKRA.stat().st_mtime)
    return k, k.thgl.max(), sott


def samningar(k: pd.DataFrame) -> pd.DataFrame:
    c = k.groupby("FAERSLUNUMER").agg(utg=("utg", "first"), thgl=("thgl", "max"), kaupverd=("kaupverd", "first"),
                                     ibud=("ibud", "any"), onoth=("onoth", "max"), nyb=("nyb", "any"),
                                     n_fastnum=("fastnum", "nunique")).reset_index()
    c = c[(c.onoth == 0) & c.ibud].copy()
    c["faerslunumer"] = c.FAERSLUNUMER.astype("int64")
    c["man"] = c.utg.dt.to_period("M")
    return c


def fullnusta(c: pd.DataFrame, T: pd.Period, data_through: pd.Timestamp) -> float:
    """% af áætluðum endanlegum fjölda samninga í T sem er þinglýstur við data_through (cc212 a03b-aðferð):
    miðgildi, yfir 12 þroskaða mánuði (T−15 … T−4), af hlutfalli þinglýstu jafnlangt frá mánaðarlokum."""
    off = data_through - (T + 1).start_time
    fr = []
    for M in pd.period_range(T - 15, T - 4, freq="M"):
        d = c[c.man == M]
        if len(d):
            fr.append((d.thgl <= (M + 1).start_time + off).mean())
    return round(100 * float(np.median(fr)), 1) if fr else 0.0


def lesa_listings(cur) -> pd.DataFrame:
    cur.execute("""select listing_id, fastnum, agency_source_id, agency_name, lysing, source_listing_id,
                          listed_at, first_seen_at, last_seen_at, withdrawn_at, updated_at
                     from scraper.listings where tenure = 'sale' and fastnum is not null""")
    a = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    for col in ("listed_at", "first_seen_at", "last_seen_at", "withdrawn_at", "updated_at"):
        a[col] = pd.to_datetime(a[col], utc=True).dt.tz_localize(None)
    a["start"] = a[["listed_at", "first_seen_at"]].min(axis=1)
    a["end"] = a[["withdrawn_at", "last_seen_at"]].max(axis=1)
    a["dealer_email"] = None
    if PARSED_MBL.exists():
        p = pd.read_sql("select source_listing_id, dealer_email from parsed_mbl_sale where dealer_email is not null",
                        sqlite3.connect(f"file:{PARSED_MBL.as_posix()}?mode=ro", uri=True))
        de = dict(zip(p.source_listing_id.astype(str), p.dealer_email.str.lower()))
        a["dealer_email"] = a.source_listing_id.astype(str).map(de)
    return a


# ---------------------------------------------------------------------------- vörumerki + nafnaskrá
def vorumerki(cur, a: pd.DataFrame) -> dict[int, tuple[str, str]]:
    cur.execute("select sala_id, lykill, birtingarheiti from scraper.fasteignasala_vorumerki")
    til = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    nyjar = (a.dropna(subset=["agency_source_id"]).groupby("agency_source_id").agency_name
             .agg(lambda s: s.mode().iat[0] if len(s.mode()) else None))
    innsetning = []
    for sid, heiti in nyjar.items():
        sid = int(sid)
        if sid in til or not heiti:
            continue
        lyk = slug(heiti)
        # sama lykill ef annað sala_id ber sama heiti (Miklaborg 617 + 844)
        til[sid] = (lyk, " ".join(heiti.split()))
        innsetning.append((sid, lyk, " ".join(heiti.split()), heiti))
    if innsetning:
        psycopg2.extras.execute_values(cur, """insert into scraper.fasteignasala_vorumerki
            (sala_id, lykill, birtingarheiti, mbl_heiti, athugasemd) values %s on conflict (sala_id) do nothing""",
            innsetning, template="(%s, %s, %s, %s, 'cc213 sjálfvirk frumfylling úr scraper.listings — óstaðfest')")
    return til, len(innsetning)


def agency_words(vm) -> frozenset[str]:
    w = {"fasteignasala", "fasteignasalan", "fasteignir", "ehf", "re", "max", "remax"}
    for lyk, heiti in vm.values():
        for x in re.split(r"[\s/.\-]+", heiti.lower()):
            if len(x) >= 3:
                w.add(fold(x))
    return frozenset(w)


def smida_nafnaskra(a: pd.DataFrame, vm, agw) -> Nafnaskra:
    s = Nafnaskra()
    for sid, t in a[["agency_source_id", "lysing"]].dropna().itertuples(index=False):
        lyk = vm.get(int(sid), (None,))[0]
        if not lyk:
            continue
        for lbl, n in candidates(t, agw):
            if lbl == "P1" and len(n.split()) >= 2:
                s.baeta_vid(lyk, n)
    s.smida(min_n=2)
    return s


class SaliKort:
    """Heldur semantic.sali_kort + sali_samheiti í minni; nýjar raðir skrifaðar í sömu færslu."""

    def __init__(self, cur):
        self.cur = cur
        cur.execute("select sali_id, stofa_lykill, nafn from semantic.sali_kort")
        self.kort: dict[str, list[tuple[int, str]]] = {}
        for sid, st, n in cur.fetchall():
            self.kort.setdefault(st, []).append((sid, n))
        cur.execute("select stofa_lykill, tegund, samheiti, sali_id from semantic.sali_samheiti")
        self.sam = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}
        self.n_nyir = self.n_sam = 0

    def _samheiti(self, st, teg, s, sid):
        if (st, teg, s) in self.sam:
            return
        self.cur.execute("insert into semantic.sali_samheiti (samheiti, stofa_lykill, tegund, sali_id, utgafa) "
                         "values (%s,%s,%s,%s,%s) on conflict do nothing", (s, st, teg, sid, UTGAFA))
        self.sam[(st, teg, s)] = sid
        self.n_sam += 1

    def id_nafn(self, st: str, nafn: str, uppruni: str) -> int:
        if (st, "nafn", nafn) in self.sam:
            return self.sam[(st, "nafn", nafn)]
        for sid, n in self.kort.get(st, []):
            if n == nafn or same_person(nafn, n):
                self._samheiti(st, "nafn", nafn, sid)
                return sid
        self.cur.execute("insert into semantic.sali_kort (stofa_lykill, nafn, uppruni, utgafa) values (%s,%s,%s,%s) "
                         "returning sali_id", (st, nafn, uppruni, UTGAFA))
        sid = self.cur.fetchone()[0]
        self.kort.setdefault(st, []).append((sid, nafn))
        self._samheiti(st, "nafn", nafn, sid)
        self.n_nyir += 1
        return sid

    def id_netfang(self, st: str, netfang: str, skra: Nafnaskra | None = None) -> int:
        """dealer_email án nafns í texta: varpa á ÓTVÍRÆTT nafn í nafnaskrá stofunnar (fornafn ~ local-hluti);
        annars ný röð með local-hluta sem nafni (uppruni 'netfang_ovarpad' — ekki birtingarhæft nafn)."""
        if (st, "netfang", netfang) in self.sam:
            return self.sam[(st, "netfang", netfang)]
        loc = fold(netfang.split("@")[0])
        hits = [n for n in (skra.grunn.get(st, []) if skra else []) if len(loc) >= 3 and fold(n.split()[0]).startswith(loc[:4])]
        if len(hits) == 1:
            sid = self.id_nafn(st, hits[0], "nafnaskra")
        else:
            sid = self.id_nafn(st, netfang.split("@")[0], "netfang_ovarpad")
        self._samheiti(st, "netfang", netfang, sid)
        return sid


# ---------------------------------------------------------------------------- eignun
def eigna(c: pd.DataFrame, k: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    cf = k[k.FAERSLUNUMER.isin(c.FAERSLUNUMER)][["FAERSLUNUMER", "fastnum"]].drop_duplicates()
    m = cf.merge(c[["FAERSLUNUMER", "utg"]], on="FAERSLUNUMER").merge(
        a[["listing_id", "fastnum", "start", "end", "agency_source_id"]], on="fastnum")
    m = m[((m.start - m.utg).dt.days <= EFTIR_DAGAR) & ((m.end - m.utg).dt.days >= -W_DAGAR)].copy()
    m["fyrir"] = m.start <= m.utg
    m["virk"] = m.fyrir & (m.end >= m.utg)
    n_st = m.dropna(subset=["agency_source_id"]).groupby("FAERSLUNUMER").agency_source_id.nunique()
    m = m.sort_values(["FAERSLUNUMER", "virk", "fyrir", "start", "listing_id"], ascending=[True, False, False, False, True])
    p = m.groupby("FAERSLUNUMER").head(1).set_index("FAERSLUNUMER")
    p["regla"] = np.where(p.virk, "virk_a_K", np.where(p.fyrir, "sidasta_fyrir_K", "fyrsta_eftir_K"))
    r = c.set_index("FAERSLUNUMER").join(p[["listing_id", "agency_source_id", "regla"]])
    r["regla"] = r.regla.fillna("oparad")
    r["n_stofur_i_glugga"] = n_st.reindex(r.index).fillna(0).astype(int)
    return r.reset_index()


# ---------------------------------------------------------------------------- samantekt
def rodun(e: pd.DataFrame, tegund: str, lykill: str, nafn_af, stofa_af, velta_col: str, sameig: pd.Series | None):
    rows = []
    for med_nyb in (True, False):
        d = e if med_nyb else e[~e.nyb]
        if d.empty:
            continue
        g = d.groupby(lykill).agg(fjoldi=("faerslunumer", "size"), velta=(velta_col, "sum"),
                                  nyb_fjoldi=("nyb", "sum"),
                                  nyb_velta=("nyb_velta", "sum"))
        g["fjoldi_sameiginl"] = (d[d.sameig].groupby(lykill).size().reindex(g.index).fillna(0).astype(int)
                                 if sameig is not None else 0)
        for maeli in ("fjoldi", "velta"):
            s = g[maeli].rank(method="min", ascending=False).astype(int)
            for lyk, row in g[s <= TOPP].iterrows():
                rows.append(dict(adili_tegund=tegund, adili_lykill=str(lyk), adili_nafn=nafn_af(lyk),
                                 stofa_lykill=stofa_af(lyk)[0], stofa_nafn=stofa_af(lyk)[1], maelikvardi=maeli,
                                 med_nybyggingum=med_nyb, saeti=int(s[lyk]), fjoldi=int(row.fjoldi),
                                 fjoldi_sameiginl=int(row.fjoldi_sameiginl), velta=int(round(row.velta)),
                                 nyb_fjoldi=int(row.nyb_fjoldi) if med_nyb else 0,
                                 nyb_velta=int(round(row.nyb_velta)) if med_nyb else 0))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--man", action="append", help="YYYY-MM (má endurtaka)")
    ap.add_argument("--sjalfvirkt", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    k, data_through, kaupskra_sott = lesa_kaupskra()
    c_all = samningar(k)
    if args.sjalfvirkt:
        T = pd.Period(data_through, "M") - 1
        while fullnusta(c_all, T, data_through) < FULLNUSTA_GOLF:
            T -= 1
        # allir mánuðir frá upphafi gluggans: staða M−3 færist þá sjálfkrafa í 'endanlegt'
        manudir = list(pd.period_range(GLUGGI_UPPHAF, T, freq="M"))
    else:
        manudir = sorted(pd.Period(x, "M") for x in (args.man or []))
    if not manudir:
        print("[VILLA] enginn mánuður"); return 3
    print(f"kaupskrá: {len(k):,} línur · data_through {data_through} · sótt {kaupskra_sott:%Y-%m-%d %H:%M} · mánuðir {[str(m) for m in manudir]}")

    conn = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("SET TRANSACTION READ WRITE")
        a = lesa_listings(cur)
        listings_snapshot = a.updated_at.max()
        vm, n_vm = vorumerki(cur, a)
        agw = agency_words(vm)
        agency_locals = frozenset(fold(lyk) for lyk, _ in vm.values())
        skra = smida_nafnaskra(a, vm, agw)
        sk = SaliKort(cur)
        print(f"listings {len(a):,} (snapshot {listings_snapshot}) · vörumerki +{n_vm} · nafnaskrá "
              f"{sum(len(v) for v in skra.grunn.values())} nöfn / {len(skra.grunn)} stofur")
        a_ix = a.set_index("listing_id")
        idag = pd.Timestamp(dt.date.today())

        # öll mánaðatímabil sem reikna þarf (hver M + ársgluggi til hvers M)
        eignad_man = {}
        for M in sorted(set(manudir) | set(pd.period_range(GLUGGI_UPPHAF, max(manudir), freq="M"))):
            c = c_all[c_all.man == M]
            e = eigna(c, k, a)
            e["sala_id"] = e.agency_source_id.astype("Int64")
            e["stofa_lykill"] = [vm.get(int(s), (None,))[0] if pd.notna(s) else None for s in e.sala_id]
            salar, upp = [], []
            for lid, st in zip(e.listing_id, e.stofa_lykill):
                if pd.isna(lid) or not isinstance(st, str):
                    salar.append([]); upp.append(None); continue
                t = a_ix.at[int(lid), "lysing"]
                nofn = extract(t, st, skra, agw, agency_locals)
                if nofn:
                    salar.append([sk.id_nafn(st, n, "nafnaskra" if skra.fletta(st, n)
                                             else ("p1_titill" if len(n.split()) > 1 else "netfang_stadfest")) for n in nofn])
                    upp.append("texti")
                    for em in personal_emails(t, agency_locals):   # netfang sem samheiti þegar fornafn passar
                        f0 = fold(em.split("@")[0])
                        for n, sid in zip(nofn, salar[-1]):
                            if len(f0) >= 3 and fold(n.split()[0]).startswith(f0[:4]):
                                sk._samheiti(st, "netfang", em, sid)
                elif isinstance(a_ix.at[int(lid), "dealer_email"], str):
                    salar.append([sk.id_netfang(st, a_ix.at[int(lid), "dealer_email"], skra)]); upp.append("dealer_email")
                else:
                    salar.append([]); upp.append(None)
            e["salar"] = salar; e["sali_uppruni"] = upp
            e["fullnusta"] = fullnusta(c_all, M, data_through)
            eignad_man[M] = e

        # skrif: eignun
        allar = pd.concat([eignad_man[M] for M in eignad_man])
        cur.execute("delete from scraper.fasteignasala_eignun where regla_version = %s and faerslunumer = any(%s)",
                    (REGLA_VERSION, list(map(int, allar.faerslunumer))))
        psycopg2.extras.execute_values(cur, """insert into scraper.fasteignasala_eignun
            (faerslunumer, regla_version, utgdag, thinglyst, kaupverd, n_fastnum, nybygging, regla, listing_id, sala_id,
             stofa_lykill, n_stofur_i_glugga, salar, sali_uppruni) values %s""",
            [(int(r.faerslunumer), REGLA_VERSION, r.utg.date(), r.thgl.to_pydatetime(), int(r.kaupverd), int(r.n_fastnum),
              bool(r.nyb), r.regla, None if pd.isna(r.listing_id) else int(r.listing_id),
              None if pd.isna(r.sala_id) else int(r.sala_id), r.stofa_lykill if isinstance(r.stofa_lykill, str) else None,
              int(r.n_stofur_i_glugga), list(map(int, r.salar)),
              r.sali_uppruni if isinstance(r.sali_uppruni, str) else None) for r in allar.itertuples()], page_size=1000)

        kort_nafn = {}
        cur.execute("select sali_id, nafn, stofa_lykill from semantic.sali_kort")
        for sid, n, st in cur.fetchall():
            kort_nafn[sid] = (n, st)
        heiti = {lyk: h for lyk, h in vm.values()}

        tima = [(M, M, "manudur") for M in manudir] + [(GLUGGI_UPPHAF, M, "fra_juli_2026") for M in manudir]
        yfirlit = []
        for fra, til, gluggi in tima:
            e = pd.concat([eignad_man[M] for M in pd.period_range(fra, til, freq="M")])
            n_M, eig = len(e), e[e.stofa_lykill.notna()].copy()
            n_par = int(e.listing_id.notna().sum())
            eig["nyb_velta"] = np.where(eig.nyb, eig.kaupverd, 0)
            n_sal = int((eig.salar.str.len() > 0).sum())
            n_sam = int((eig.salar.str.len() > 1).sum())
            fulln = min(float(eignad_man[M].fullnusta.iat[0]) if len(eignad_man[M]) else 0.0
                        for M in pd.period_range(fra, til, freq="M"))
            lok = (til + 3).start_time
            timabil_ohaeft = any(
                (len(eignad_man[M]) == 0) or (eignad_man[M].stofa_lykill.notna().mean() < EIGNUN_GOLF)
                for M in pd.period_range(fra, til, freq="M"))
            stada_stofa = ("ohaeft" if timabil_ohaeft or fulln < FULLNUSTA_GOLF or n_M == 0
                           else ("endanlegt" if idag >= lok else "bradabirgda"))
            stada_sali = ("ohaeft" if stada_stofa == "ohaeft"
                          else ("undir_golfi" if len(eig) == 0 or n_sal / len(eig) < SALI_GOLF else stada_stofa))
            fyrirvari = f"Salar eru taldir þar sem nafn er skráð í auglýsingu — {n_sal} af {n_M} sölum " + \
                        ("mánaðarins." if gluggi == "manudur" else "tímabilsins.")
            key = (fra.start_time.date(), til.end_time.date(), gluggi, REGLA_VERSION)
            cur.execute("delete from semantic.fasteignasala_nefnarar where timabil_fra=%s and timabil_til=%s and gluggi=%s and regla_version=%s", key)
            cur.execute("""insert into semantic.fasteignasala_nefnarar (timabil_fra, timabil_til, gluggi, regla_version,
                  n_samningar, velta_samninga, n_nybygging, n_paradar, n_eignadar_stofu, velta_eignud_stofu, n_med_sala,
                  n_salar_sameiginl, fullnusta_aaetlud, stada_stofa, stada_sali, sali_golf, eignun_golf, fyrirvari_sali,
                  data_through, kaupskra_sott, listings_snapshot)
                  values (%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s, %s,%s,%s)""",
                key + (n_M, int(e.kaupverd.sum()), int(e.nyb.sum()), n_par, len(eig), int(eig.kaupverd.sum()), n_sal, n_sam,
                       fulln, stada_stofa, stada_sali, SALI_GOLF, EIGNUN_GOLF, fyrirvari, data_through.date(),
                       kaupskra_sott.to_pydatetime(), listings_snapshot.to_pydatetime()))
            # stofur
            rows = rodun(eig, "stofa", "stofa_lykill", lambda l: heiti.get(l, l), lambda l: (l, heiti.get(l, l)), "kaupverd", None)
            # salar: ein röð per (sala, sali); fjöldi óskiptur, velta skipt jafnt
            x = eig[eig.salar.str.len() > 0].explode("salar").rename(columns={"salar": "sali_id"})
            if not x.empty:
                x["n_s"] = x.groupby("faerslunumer").sali_id.transform("size")
                x["velta_skipt"] = x.kaupverd / x.n_s
                x["nyb_velta"] = np.where(x.nyb, x.velta_skipt, 0)
                x["sameig"] = x.n_s > 1
                rows += rodun(x, "sali", "sali_id", lambda s: kort_nafn[int(s)][0],
                              lambda s: (kort_nafn[int(s)][1], heiti.get(kort_nafn[int(s)][1], kort_nafn[int(s)][1])),
                              "velta_skipt", x.sameig)
            if rows:
                psycopg2.extras.execute_values(cur, """insert into semantic.fasteignasala_manudur (timabil_fra, timabil_til,
                    gluggi, regla_version, adili_tegund, adili_lykill, adili_nafn, stofa_lykill, stofa_nafn, maelikvardi,
                    med_nybyggingum, saeti, fjoldi, fjoldi_sameiginl, velta, nyb_fjoldi, nyb_velta, data_through) values %s""",
                    [key + (r["adili_tegund"], r["adili_lykill"], r["adili_nafn"], r["stofa_lykill"], r["stofa_nafn"],
                            r["maelikvardi"], r["med_nybyggingum"], r["saeti"], r["fjoldi"], r["fjoldi_sameiginl"],
                            r["velta"], r["nyb_fjoldi"], r["nyb_velta"], data_through.date()) for r in rows])
            yfirlit.append(f"  {gluggi:<14} {fra}..{til}: M={n_M} paraðar={n_par} stofa={len(eig)} ({100*len(eig)/max(n_M,1):.1f} %) "
                           f"sali={n_sal} ({100*n_sal/max(len(eig),1):.1f} % af eignuðum; {100*n_sal/max(n_M,1):.1f} % af M) "
                           f"sameig={n_sam} fullnusta={fulln} stada_stofa={stada_stofa} stada_sali={stada_sali} raðir={len(rows)}")
        print("\n".join(yfirlit))
        print(f"salakort: +{sk.n_nyir} salar, +{sk.n_sam} samheiti")
        if args.dry_run:
            conn.rollback(); print("[DRY-RUN] rúllað til baka")
        else:
            conn.commit(); print("[OK] skrifað")
        return 0
    except Exception as ex:
        conn.rollback()
        print(f"[VILLA] {type(ex).__name__}: {ex}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
