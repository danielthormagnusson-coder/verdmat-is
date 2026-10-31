"""cc213_fasteignasala_manudur.py — mánaðarleg röðun fasteignasala (stofur + salar).

Forskrift: D:\\_audit\\cc212_fasteignasalar\\SKIL_CC212.md §5, cc212b §4–5, ákvarðanir Danna 27.09.
Keyrsla: 16. hvers mánaðar (kaupskrá 15. dags lesin 02:30). Idempotent per (tímabil, gluggi, regla_version).

Skilgreiningar (regla_version cc213-v2; v1 + handvirk útilokun sala með sali_kort.virkt = false):
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

cc223 (regla_version cc223-v1 = cc213-v2 + nýbyggingarstaðir): þrír staðir per tímabil — med (allar sölur),
  an (nýbyggingar út), adeins (aðeins nýbyggingar). Hver staður ber eigin röðunarlínur (fasteignasala_manudur.nybyggingar)
  og eigin nefnara + gólf (semantic.fasteignasala_nyb_stadir): eignunargólf per mánuð staðarins, sala-gólf á stað-tölum.
  med = nefnarar-röðin óbreytt. cc213-v2 (lifandi framendi fram að flippi FS_REGLA) er skrifuð samhliða úr sömu
  útreikningum, aðeins med/an og án stað-raða — eldri RLS-regla gildir um hana.

cc286 (regla_version cc286-v1 = cc223-v1 + rétt „virk á kaupsamningsdegi", óháð staðfesting cc287 §6.1):
  lokadagur   = withdrawn_at ef hann er til; annars status='active' → ENN VIRK (opin lok); annars (status='inactive',
                mbl syna≠1 við síðustu sókn) → max(last_seen_at, sidast_fundin_at). last_seen_at er síðasta delta-sókn,
                EKKI lok auglýsingar (DATA_SCHEMA § Lifandi lag): með gömlu reglunni max(withdrawn_at, last_seen_at) „lauk"
                virk auglýsing á síðustu sókn og eignunin hoppaði á eldri auglýsingu annarrar stofu (10 af 2.015 í júl–sep).
  virk á K    = upphafsDAGUR ≤ K ≤ lokadagur (dagsgrunnur: auglýsing sem birtist á kaupsamningsdegi var virk á honum;
                áður var klukkutími upphafs borinn við miðnætti K).
  eignun      = hreinsuð per (regla_version, tímabil reiknuðu mánaðanna), ekki per lista núverandi samninga — samningur
                sem fellur úr menginu (t.d. HMS merkir ONOTHAEFUR 0→1) skilur ekki eftir eignunarröð.
  cc223-v1 er ekki skrifuð lengur; framendinn flippar FS_REGLA → cc286-v1 (verdmat-ai config/fasteignasolur.ts).
  jafntefli   = (ákvörðun Danna 31.10) auglýsingar í sama þrepi og sigurvegarinn sem hófust sama DAG: samningurinn er
                sameiginlegur öllum stofum jafnteflisins — fjöldi óskiptur, velta skipt jafnt, fjoldi_sameiginl á stofulínum
                (sama vélbúnaður og salar). eignun.stofur = allar stofur; eignun.stofa_lykill = sigurvegari (samhæfni).
  R-H         = (ákvörðun Danna 31.10) Fjölbýli með samningsflöt > 500 m² = heildarkaup fjölbýlishúss: utan röðunar,
                talið í M og í nefnurunum n_utan_rodunar / velta_utan_rodunar / utan_rodunar_astaeda (eignun.utan_rodunar).

Notkun:
  python scripts/cc213_fasteignasala_manudur.py --man 2026-08 [--man 2026-07] [--dry-run]
  python scripts/cc213_fasteignasala_manudur.py --sjalfvirkt          # 2026-07 … síðasti mánuður m/ fullnustu ≥ 90 %
  --reglur cc223-v1                    # skrifa aðeins tilgreindar útgáfur (sjálfgefið: cc213-v2 og cc223-v1 til og með
                                       # 16.10.2026, eftir það aðeins cc223-v1)
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

REGLA_VERSION = "cc286-v1"   # cc286 (31.10): cc223-v1 + lokadagur virkrar auglýsingar + virk á K á dagsgrunni
#                              (cc223 09.10: cc213-v2 + þrír nýbyggingarstaðir med/an/adeins með eigin gólfum)
OPIN_LOK = pd.Timestamp("2100-01-01")   # lokadagur virkrar auglýsingar án withdrawn_at („enn virk")
ELDRI_REGLA = "cc213-v2"     # v2 (29.09): handvirk útilokun sala + staðfest vörumerkjakort — lifandi framendi fram að flippi
ELDRI_REGLA_TIL = dt.date(2026, 10, 16)   # ákvörðun Danna 09.10: cc213-v2 skrifuð til og með keyrslunni 16.10, svo hætt
REGLUR = (ELDRI_REGLA, REGLA_VERSION)
SJALFGEFNAR_REGLUR = REGLUR if dt.date.today() <= ELDRI_REGLA_TIL else (REGLA_VERSION,)
# Staðirnir: síur á eignaðar sölur (dálkurinn nyb = regla 5). med = engin sía.
STADIR = {"med": lambda d: d, "an": lambda d: d[~d.nyb], "adeins": lambda d: d[d.nyb]}
KAUPSKRA = Path(r"D:\kaupskra.csv")
PARSED_MBL = Path(r"D:\verdmat-is\scraper_data\parsed_mbl.db")
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
W_DAGAR, EFTIR_DAGAR = 180, 30
EIGNUN_GOLF, SALI_GOLF, FULLNUSTA_GOLF = 0.70, 0.80, 90.0
GLUGGI_UPPHAF = pd.Period("2026-07", "M")
TOPP = 10
IBUD = {"Fjölbýli", "Einbýli", "Sérbýli"}
# cc286 R-H (ákvörðun Danna 31.10): samningur um Fjölbýli með samningsflöt (EINFLM = heildartala samnings) > 500 m² er
# heildarkaup fjölbýlishúss — utan röðunar, talinn í nefnara (n_utan_rodunar). Mælt 2024-01…2026-09: nákvæmlega 5 af
# 27.147 nothæfum íbúðasamningum, öll heil hús; hvert gildi á bilinu 500–1.300 m² gefur sömu 5 (SKIL_CC286 §7.2).
HEILDARKAUP_FLM = 500.0
UTAN_HEILDARKAUP = "heildarkaup_fjolbylishuss"

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
    k["einflm"] = pd.to_numeric(k.EINFLM, errors="coerce")
    k["fjolbyli"] = k.TEGUND.str.strip() == "Fjölbýli"
    k["nyb"] = (k.fullbuid == 0) | (k.byggar >= k.utg.dt.year - 2)
    sott = pd.Timestamp.fromtimestamp(KAUPSKRA.stat().st_mtime)
    return k, k.thgl.max(), sott


def samningar(k: pd.DataFrame) -> pd.DataFrame:
    c = k.groupby("FAERSLUNUMER").agg(utg=("utg", "first"), thgl=("thgl", "max"), kaupverd=("kaupverd", "first"),
                                     ibud=("ibud", "any"), onoth=("onoth", "max"), nyb=("nyb", "any"),
                                     n_fastnum=("fastnum", "nunique"), einflm=("einflm", "max"),
                                     fjolbyli=("fjolbyli", "any")).reset_index()
    c = c[(c.onoth == 0) & c.ibud].copy()
    c["heildarkaup"] = c.fjolbyli & (c.einflm > HEILDARKAUP_FLM)
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


def lokadagur(a: pd.DataFrame) -> pd.Series:
    """Lokadagur auglýsingar (cc286): withdrawn_at → annars active = OPIN_LOK → annars max(last_seen_at, sidast_fundin_at).
    last_seen_at ræður ALDREI lokum virkrar auglýsingar (það er síðasta delta-sókn, ekki líf)."""
    end = a["withdrawn_at"].copy()
    virk = end.isna() & (a["status"] == "active")
    end[virk] = OPIN_LOK
    rest = end.isna()
    end[rest] = a.loc[rest, ["last_seen_at", "sidast_fundin_at"]].max(axis=1)
    return end


def lesa_listings(cur) -> pd.DataFrame:
    cur.execute("""select listing_id, fastnum, agency_source_id, agency_name, lysing, source_listing_id, status,
                          listed_at, first_seen_at, last_seen_at, sidast_fundin_at, withdrawn_at, updated_at
                     from scraper.listings where tenure = 'sale' and fastnum is not null""")
    a = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
    for col in ("listed_at", "first_seen_at", "last_seen_at", "sidast_fundin_at", "withdrawn_at", "updated_at"):
        a[col] = pd.to_datetime(a[col], utc=True).dt.tz_localize(None)
    a["start"] = a[["listed_at", "first_seen_at"]].min(axis=1)
    a["end"] = lokadagur(a)
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
        cur.execute("select sali_id, stofa_lykill, nafn, virkt from semantic.sali_kort")
        self.kort: dict[str, list[tuple[int, str]]] = {}
        self.ovirkir: set[int] = set()     # handvirkt útilokaðir (rýni): sölur telja hjá stofu, ekki á sala-lista
        for sid, st, n, virkt in cur.fetchall():
            self.kort.setdefault(st, []).append((sid, n))
            if not virkt:
                self.ovirkir.add(sid)
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
    m["fyrir"] = m.start.dt.normalize() <= m.utg          # cc286: upphafsDAGUR ≤ K (dagsgrunnur, utg er miðnætti K)
    m["virk"] = m.fyrir & (m.end >= m.utg)
    n_st = m.dropna(subset=["agency_source_id"]).groupby("FAERSLUNUMER").agency_source_id.nunique()
    m = m.sort_values(["FAERSLUNUMER", "virk", "fyrir", "start", "listing_id"], ascending=[True, False, False, False, True])
    p = m.groupby("FAERSLUNUMER").head(1).set_index("FAERSLUNUMER")
    p["regla"] = np.where(p.virk, "virk_a_K", np.where(p.fyrir, "sidasta_fyrir_K", "fyrsta_eftir_K"))
    # cc286 (ákvörðun Danna 31.10): JAFNTEFLI INNAN DAGS — auglýsingar í sama þrepi og sigurvegarinn (virk / fyrir /
    # eftir) sem hófust sama DAG teljast jafnar; klukkutíminn ræður ekki. Samningurinn er þá sameiginlegur öllum stofum
    # jafnteflisins (fjöldi óskiptur, velta skipt jafnt — sami vélbúnaður og fjoldi_sameiginl sala).
    # jafntefli = [(listing_id, agency_source_id)], sigurvegarinn fyrst, ein auglýsing per agency_source_id.
    m["dagur"] = m.start.dt.normalize()
    vinn = m.groupby("FAERSLUNUMER").head(1)[["FAERSLUNUMER", "virk", "fyrir", "dagur"]]
    t = m.merge(vinn, on=["FAERSLUNUMER", "virk", "fyrir", "dagur"], how="inner")      # röð m varðveitt (sigurvegari fyrst)
    t = t.dropna(subset=["agency_source_id"]).drop_duplicates(["FAERSLUNUMER", "agency_source_id"])
    jt = {f: [(int(l), int(a_)) for l, a_ in zip(d.listing_id, d.agency_source_id)] for f, d in t.groupby("FAERSLUNUMER", sort=False)}
    p["jafntefli"] = [jt.get(f, []) for f in p.index]
    r = c.set_index("FAERSLUNUMER").join(p[["listing_id", "agency_source_id", "regla", "jafntefli"]])
    r["regla"] = r.regla.fillna("oparad")
    r["jafntefli"] = [j if isinstance(j, list) and pd.notna(a_) else [] for j, a_ in zip(r.jafntefli, r.agency_source_id)]
    r["n_stofur_i_glugga"] = n_st.reindex(r.index).fillna(0).astype(int)
    return r.reset_index()


# ---------------------------------------------------------------------------- samantekt
def rodun(e: pd.DataFrame, tegund: str, lykill: str, nafn_af, stofa_af, velta_col: str, sameig: bool):
    """Röðunarlínur allra staða (med/an/adeins) — hver staður raðaður sjálfstætt, ekki afleiddur af öðrum."""
    rows = []
    for stad, sia in STADIR.items():
        d = sia(e)
        if d.empty:
            continue
        g = d.groupby(lykill).agg(fjoldi=("faerslunumer", "size"), velta=(velta_col, "sum"),
                                  nyb_fjoldi=("nyb", "sum"),
                                  nyb_velta=("nyb_velta", "sum"))
        g["fjoldi_sameiginl"] = (d[d.sameig].groupby(lykill).size().reindex(g.index).fillna(0).astype(int)
                                 if sameig else 0)
        for maeli in ("fjoldi", "velta"):
            s = g[maeli].rank(method="min", ascending=False).astype(int)
            for lyk, row in g[s <= TOPP].iterrows():
                rows.append(dict(adili_tegund=tegund, adili_lykill=str(lyk), adili_nafn=nafn_af(lyk),
                                 stofa_lykill=stofa_af(lyk)[0], stofa_nafn=stofa_af(lyk)[1], maelikvardi=maeli,
                                 nybyggingar=stad, med_nybyggingum=stad != "an", saeti=int(s[lyk]),
                                 fjoldi=int(row.fjoldi), fjoldi_sameiginl=int(row.fjoldi_sameiginl),
                                 velta=int(round(row.velta)),
                                 nyb_fjoldi=int(row.nyb_fjoldi) if stad != "an" else 0,
                                 nyb_velta=int(round(row.nyb_velta)) if stad != "an" else 0))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--man", action="append", help="YYYY-MM (má endurtaka)")
    ap.add_argument("--sjalfvirkt", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prenta", action="store_true", help="prenta Top 10 (fjöldi, með nýb.) stofa og sala per mánuð")
    ap.add_argument("--reglur", default=",".join(SJALFGEFNAR_REGLUR),
                    help=f"útgáfur sem skrifaðar eru, kommuaðskilið (sjálfgefið {','.join(SJALFGEFNAR_REGLUR)}; "
                         f"{ELDRI_REGLA} aðeins til og með {ELDRI_REGLA_TIL})")
    args = ap.parse_args()
    reglur = [r.strip() for r in args.reglur.split(",") if r.strip()]
    if not reglur or any(r not in REGLUR for r in reglur):
        print(f"[VILLA] --reglur verður að vera úr {REGLUR}"); return 3

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
        cur.execute("SET LOCAL statement_timeout = '15min'")   # pooler-sjálfgildið féll á listings-lestri undir álagi (29.09)
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
            # cc286 R-H: heildarkaup fjölbýlishúss — utan röðunar (engin stofa, engir salar), talið í nefnara
            e["utan_rodunar"] = [UTAN_HEILDARKAUP if h else None for h in e.heildarkaup]
            e.loc[e.heildarkaup.astype(bool), "stofa_lykill"] = None
            # cc286: stofur jafnteflis innan dags (sigurvegarinn fyrst); ein auglýsing per stofulykil
            stofur_l, por_l = [], []
            for j, st0, utan in zip(e.jafntefli, e.stofa_lykill, e.utan_rodunar):
                if utan is not None or not isinstance(st0, str):
                    stofur_l.append([]); por_l.append([]); continue
                sts, pr = [], []
                for lid_, sid_ in j:
                    st_ = vm.get(int(sid_), (None,))[0]
                    if isinstance(st_, str) and st_ not in sts:
                        sts.append(st_); pr.append((lid_, st_))
                stofur_l.append(sts); por_l.append(pr)
            e["stofur"] = stofur_l

            def salar_af(lid, st):
                t = a_ix.at[int(lid), "lysing"]
                nofn = extract(t, st, skra, agw, agency_locals)
                if nofn:
                    ids = [sk.id_nafn(st, n, "nafnaskra" if skra.fletta(st, n)
                                      else ("p1_titill" if len(n.split()) > 1 else "netfang_stadfest")) for n in nofn]
                    for em in personal_emails(t, agency_locals):   # netfang sem samheiti þegar fornafn passar
                        f0 = fold(em.split("@")[0])
                        for n, sid in zip(nofn, ids):
                            if len(f0) >= 3 and fold(n.split()[0]).startswith(f0[:4]):
                                sk._samheiti(st, "netfang", em, sid)
                    return ids, "texti"
                if isinstance(a_ix.at[int(lid), "dealer_email"], str):
                    return [sk.id_netfang(st, a_ix.at[int(lid), "dealer_email"], skra)], "dealer_email"
                return [], None

            salar, upp = [], []
            for pr in por_l:
                ids_all, upp_ = [], None
                for lid_, st_ in pr:
                    ids, u = salar_af(lid_, st_)
                    ids_all += [x for x in ids if x not in ids_all]
                    upp_ = upp_ or u
                salar.append(ids_all); upp.append(upp_)
            n_util = sum(1 for l in salar if any(x in sk.ovirkir for x in l))
            salar = [[x for x in l if x not in sk.ovirkir] for l in salar]
            upp = [u if l else None for u, l in zip(upp, salar)]
            if n_util:
                print(f"  {M}: {n_util} eignaðar sölur báru útilokaðan sala (telja hjá stofu)")
            e["salar"] = salar; e["sali_uppruni"] = upp
            e["fullnusta"] = fullnusta(c_all, M, data_through)
            eignad_man[M] = e

        # skrif: eignun
        allar = pd.concat([eignad_man[M] for M in eignad_man])
        for regla in reglur:
            # cc286: hreinsað per tímabil reiknuðu mánaðanna — samningur sem féll úr menginu skilur ekki eftir röð
            cur.execute("delete from scraper.fasteignasala_eignun where regla_version = %s and utgdag between %s and %s",
                        (regla, min(eignad_man).start_time.date(), max(eignad_man).end_time.date()))
            psycopg2.extras.execute_values(cur, """insert into scraper.fasteignasala_eignun
                (faerslunumer, regla_version, utgdag, thinglyst, kaupverd, n_fastnum, nybygging, regla, listing_id, sala_id,
                 stofa_lykill, n_stofur_i_glugga, salar, sali_uppruni, stofur, utan_rodunar) values %s""",
                [(int(r.faerslunumer), regla, r.utg.date(), r.thgl.to_pydatetime(), int(r.kaupverd), int(r.n_fastnum),
                  bool(r.nyb), r.regla, None if pd.isna(r.listing_id) else int(r.listing_id),
                  None if pd.isna(r.sala_id) else int(r.sala_id), r.stofa_lykill if isinstance(r.stofa_lykill, str) else None,
                  int(r.n_stofur_i_glugga), list(map(int, r.salar)),
                  r.sali_uppruni if isinstance(r.sali_uppruni, str) else None, list(r.stofur),
                  r.utan_rodunar if isinstance(r.utan_rodunar, str) else None) for r in allar.itertuples()], page_size=1000)

        kort_nafn = {}
        cur.execute("select sali_id, nafn, stofa_lykill from semantic.sali_kort")
        for sid, n, st in cur.fetchall():
            kort_nafn[sid] = (n, st)
        heiti = {lyk: h for lyk, h in vm.values()}

        tima = [(M, M, "manudur") for M in manudir] + [(GLUGGI_UPPHAF, M, "fra_juli_2026") for M in manudir]
        yfirlit = []
        for fra, til, gluggi in tima:
            man_i = list(pd.period_range(fra, til, freq="M"))
            e = pd.concat([eignad_man[M] for M in man_i])
            n_M = len(e)
            n_par = int(e.listing_id.notna().sum())
            fulln = min(float(eignad_man[M].fullnusta.iat[0]) if len(eignad_man[M]) else 0.0 for M in man_i)
            lok = (til + 3).start_time

            # stöður per stað (cc223): eignunargólf per MÁNUÐ staðarins (tímabil óhæft ef einhver mánuður fellur),
            # fullnusta sameiginleg, sala-gólf á tölum staðarins. med = cc213-reglan óbreytt.
            stadir = {}
            for stad, sia in STADIR.items():
                es = sia(e)
                eig = es[es.stofa_lykill.notna()].copy()
                eig["nyb_velta"] = np.where(eig.nyb, eig.kaupverd, 0)
                hlutf = [sia(eignad_man[M]).stofa_lykill.notna().mean() if len(sia(eignad_man[M])) else 0.0 for M in man_i]
                laegst = float(min(hlutf)) if hlutf else 0.0
                n_utan = int(es.utan_rodunar.notna().sum())
                velta_utan = int(es.loc[es.utan_rodunar.notna(), "kaupverd"].sum())
                n_st_sam = int((eig.stofur.str.len() > 1).sum())
                n_sal = int((eig.salar.str.len() > 0).sum())
                n_sam = int((eig.salar.str.len() > 1).sum())
                stada_stofa = ("ohaeft" if laegst < EIGNUN_GOLF or fulln < FULLNUSTA_GOLF or len(es) == 0
                               else ("endanlegt" if idag >= lok else "bradabirgda"))
                stada_sali = ("ohaeft" if stada_stofa == "ohaeft"
                              else ("undir_golfi" if len(eig) == 0 or n_sal / len(eig) < SALI_GOLF else stada_stofa))
                fyrirvari = f"Salar eru taldir þar sem nafn er skráð í auglýsingu — {n_sal} af {len(es)} sölum " + \
                            ("mánaðarins." if gluggi == "manudur" else "tímabilsins.")
                stadir[stad] = dict(es=es, eig=eig, n_sal=n_sal, n_sam=n_sam, laegst=laegst, stada_stofa=stada_stofa,
                                    stada_sali=stada_sali, fyrirvari=fyrirvari, n_utan=n_utan, velta_utan=velta_utan,
                                    n_st_sam=n_st_sam)
            # Allt = Án + Aðeins (fjöldi og velta) — vörn í skriftunni sjálfri
            for k_ in ("es", "eig"):
                a_, b_, c_ = (stadir[s][k_] for s in ("med", "an", "adeins"))
                assert len(a_) == len(b_) + len(c_) and int(a_.kaupverd.sum()) == int(b_.kaupverd.sum()) + int(c_.kaupverd.sum()), \
                    f"{gluggi} {fra}..{til}: Allt ≠ Án + Aðeins ({k_})"

            # röðunarlínur allra staða (stofur + salar)
            eig = stadir["med"]["eig"]
            # cc286: stofur — ein röð per (sala, stofa); fjöldi óskiptur, velta skipt jafnt, sameiginlegar taldar (jafntefli innan dags)
            xs = eig.explode("stofur").rename(columns={"stofur": "stofa"})
            xs["n_st"] = xs.groupby("faerslunumer").stofa.transform("size")
            xs["velta_skipt"] = xs.kaupverd / xs.n_st
            xs["nyb_velta"] = np.where(xs.nyb, xs.velta_skipt, 0)
            xs["sameig"] = xs.n_st > 1
            rows = rodun(xs, "stofa", "stofa", lambda l: heiti.get(l, l), lambda l: (l, heiti.get(l, l)), "velta_skipt", True)
            # salar: ein röð per (sala, sali); fjöldi óskiptur, velta skipt jafnt
            x = eig[eig.salar.str.len() > 0].explode("salar").rename(columns={"salar": "sali_id"})
            if not x.empty:
                x["n_s"] = x.groupby("faerslunumer").sali_id.transform("size")
                x["velta_skipt"] = x.kaupverd / x.n_s
                x["nyb_velta"] = np.where(x.nyb, x.velta_skipt, 0)
                x["sameig"] = x.n_s > 1
                rows += rodun(x, "sali", "sali_id", lambda s: kort_nafn[int(s)][0],
                              lambda s: (kort_nafn[int(s)][1], heiti.get(kort_nafn[int(s)][1], kort_nafn[int(s)][1])),
                              "velta_skipt", True)

            m = stadir["med"]
            for regla in reglur:
                key = (fra.start_time.date(), til.end_time.date(), gluggi, regla)
                cur.execute("delete from semantic.fasteignasala_nefnarar where timabil_fra=%s and timabil_til=%s and gluggi=%s and regla_version=%s", key)
                cur.execute("""insert into semantic.fasteignasala_nefnarar (timabil_fra, timabil_til, gluggi, regla_version,
                      n_samningar, velta_samninga, n_nybygging, n_paradar, n_eignadar_stofu, velta_eignud_stofu, n_med_sala,
                      n_salar_sameiginl, fullnusta_aaetlud, stada_stofa, stada_sali, sali_golf, eignun_golf, fyrirvari_sali,
                      data_through, kaupskra_sott, listings_snapshot, n_utan_rodunar, velta_utan_rodunar, utan_rodunar_astaeda,
                      n_stofu_sameiginl)
                      values (%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s,%s, %s,%s,%s, %s,%s,%s,%s)""",
                    key + (n_M, int(e.kaupverd.sum()), int(e.nyb.sum()), n_par, len(m["eig"]), int(m["eig"].kaupverd.sum()),
                           m["n_sal"], m["n_sam"], fulln, m["stada_stofa"], m["stada_sali"], SALI_GOLF, EIGNUN_GOLF,
                           m["fyrirvari"], data_through.date(), kaupskra_sott.to_pydatetime(), listings_snapshot.to_pydatetime(),
                           m["n_utan"], m["velta_utan"], UTAN_HEILDARKAUP if m["n_utan"] else None, m["n_st_sam"]))
                eldri = regla == ELDRI_REGLA
                if not eldri:
                    psycopg2.extras.execute_values(cur, """insert into semantic.fasteignasala_nyb_stadir (timabil_fra, timabil_til,
                        gluggi, regla_version, nybyggingar, n_samningar, velta_samninga, n_eignadar_stofu, velta_eignud_stofu,
                        n_med_sala, n_salar_sameiginl, eignun_laegst_man, stada_stofa, stada_sali, fyrirvari_sali, n_utan_rodunar,
                        n_stofu_sameiginl) values %s""",
                        [key + (s, len(d["es"]), int(d["es"].kaupverd.sum()), len(d["eig"]), int(d["eig"].kaupverd.sum()),
                                d["n_sal"], d["n_sam"], round(d["laegst"], 4), d["stada_stofa"], d["stada_sali"], d["fyrirvari"],
                                d["n_utan"], d["n_st_sam"])
                         for s, d in stadir.items()])
                rr = [r for r in rows if not (eldri and r["nybyggingar"] == "adeins")]
                if rr:
                    psycopg2.extras.execute_values(cur, """insert into semantic.fasteignasala_manudur (timabil_fra, timabil_til,
                        gluggi, regla_version, adili_tegund, adili_lykill, adili_nafn, stofa_lykill, stofa_nafn, maelikvardi,
                        nybyggingar, med_nybyggingum, saeti, fjoldi, fjoldi_sameiginl, velta, nyb_fjoldi, nyb_velta, data_through)
                        values %s""",
                        [key + (r["adili_tegund"], r["adili_lykill"], r["adili_nafn"], r["stofa_lykill"], r["stofa_nafn"],
                                r["maelikvardi"], r["nybyggingar"], r["med_nybyggingum"], r["saeti"], r["fjoldi"],
                                r["fjoldi_sameiginl"], r["velta"], r["nyb_fjoldi"], r["nyb_velta"], data_through.date())
                         for r in rr], page_size=1000)
            if args.prenta and gluggi == "manudur":
                for teg in ("stofa", "sali"):
                    r_ = sorted((r for r in rows if r["adili_tegund"] == teg and r["maelikvardi"] == "fjoldi" and r["nybyggingar"] == "med"),
                                key=lambda r: (r["saeti"], r["adili_nafn"]))
                    print()
                    print(f"  {til} — Top 10 {'stofur' if teg == 'stofa' else 'salar'} (fjöldi, með nýb.):")
                    for r in r_:
                        print(f"    {r['saeti']:>2}. {r['adili_nafn']:<34} {r['fjoldi']:>3}  {r['velta']/1e6:>7,.0f} m.kr" +
                              (f"  ({r['stofa_nafn']})" if teg == "sali" else "") + (f"  [{r['nyb_fjoldi']} nýb.]" if r['nyb_fjoldi'] else ""))
            for s, d in stadir.items():
                yfirlit.append(f"  {gluggi:<14} {fra}..{til} {s:<6}: M={len(d['es'])} stofa={len(d['eig'])} "
                               f"({100*len(d['eig'])/max(len(d['es']),1):.1f} %; lægsti mán. {100*d['laegst']:.1f} %) "
                               f"sali={d['n_sal']} ({100*d['n_sal']/max(len(d['eig']),1):.1f} % af eignuðum) sameig={d['n_sam']} "
                               f"fullnusta={fulln} stada_stofa={d['stada_stofa']} stada_sali={d['stada_sali']} "
                               f"raðir={sum(1 for r in rows if r['nybyggingar'] == s)}")
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
