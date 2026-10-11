"""cc224 — /nybyggingar: reiknar semantic.nybygging_verkefni + semantic.nybygging_einingar (útgáfa cc224-v7; myndaval nýrra verkefna cc224e, v6 nefnarar cc229, v5 heildarkaup cc228, v4 myndaval cc224d).

  python scripts/cc224_nybygging_verkefni.py --dryrun [--ut DIR] [--slodir-tillaga CSV]
  python scripts/cc224_nybygging_verkefni.py --skrifa [--ut DIR] [--revalidate] [--hlada-myndir REMOTE]
  python scripts/cc224_nybygging_verkefni.py --lesa-slodir CSV [--nei slod,slod] [--athugasemd TEXTI]

--dryrun   reiknar og skrifar verkefni.csv/einingar.csv/samantekt.txt í --ut; ekkert skrifað í gagnagrunn.
--skrifa   sama + skrifar útgáfuna í einni færslu (DELETE útgáfu → INSERT) og eina röð í nybygging_keyrslur.
--revalidate  (aðeins --skrifa, eftir COMMIT) POST á /api/nybyggingar/endurnyja (verdmat-ai) með ENDURNYJA_LYKILL;
           falli kallið stendur skriftan (rc 0) og síðan endurnýjast á 1 klst TTL.
--slodir-tillaga  (aðeins --dryrun) les slodir_ryni.csv og notar tillaga = já sem staðfest — SPÁ um áhrif
           staðfestingar, aldrei skrifuð.
--lesa-slodir  les slodir_ryni.csv inn í semantic.nybygging_slodir (stadfest-dálkur ef fylltur, annars tillaga;
           --nei snýr tilteknum slóðum í nei). Já-slóð fer á allar landeignir þar sem hún stendur í auglýsingatexta
           (utvikka_slodir); nei-slóð á landeign CSV-raðarinnar. Endurkeyrsla skiptir töflunni út í heild.

--hlada-myndir  (aðeins --skrifa) rclone-áfangi OPINBERS myndahýsils (`r2backup:verdmat-myndir`, borin á myndir.verdmat.ai) sem nýjar
           minnkaðar myndir eru afritaðar á; án hennar eru þær smíðaðar og skráðar en ekki hlaðnar (hladid_kl NULL).
           Afritafatan r2backup:verdmat-backups er LOKUÐ og aldrei áfangastaður birtingarmynda (cc117 §0).

Skilgreining (ákvörðun Danna 09.10.2026, SKIL_CC224_1.md §3 + §5 aldursvörn; cc224b 10.10 §8.6 lið 5):
  eining innan skilgreiningar = íbúð (regla 7) ∧ ((FULLBUID=0 ∨ byggingarstig B0–B3 ∧ matsstig 0–6)
                                                    ∧ (BYGGAR ≥ ár−3 ∨ BYGGAR óskráð)  ∨ BYGGAR ≥ ár−2)
  (cc224-v1 dæmdi FULLBUID=0 óháð aldri → 27 gólfverkefni eingöngu úr eldri húsum; v2 = aldursvörn á FULLBUID-greininni;
   v3 = sama aldursvörn á byggingarstigs-greininni — almenn regla, Digranesheiði 45 bar hús frá 1955 á B1)
  virkt verkefni (framendi) = n_virkar > 0 = ≥ 1 virk söluauglýsing á óseldri einingu (D3, SKIL §8.1)
  forsíðumynd = HANDVALIN útlitsmynd (ljósmynd/3D að utan; aldrei grunnmynd/innimynd/útsýni/kort/lógó) úr
      scripts/nybyggingar_myndaval.csv (cc224_myndaval_lesa.py, §10); „engin" eða ekkert val → engin mynd (hlutlaus flötur);
      minnkuð EINU SINNI í 720 px WebP (semantic.nybygging_myndir), engin safnmynd
  augl_id = nýjasta VIRKA mbl-söluauglýsing einingarinnar (eignarstig, v_eign_virk_auglysing); augl_endursala = eining seld
  lækkanir (cc224c) = Verðvakt v2 með gátum Verðvaktarinnar, fyrsta sala; laekkad_30 = eining á sölu með lækkun síðustu 30 d
  Y = íbúðir á landeignum verkefnisins byggðar ≥ ár−3 eða innan skilgreiningar (eldri hús á sömu lóð ekki talin);
      óskipt fastnúmer (cc229 A, regla 1) = fastnr. með ≥ 2 íbúðarmatseiningar hjá HMS; telur fjölda þeirra
  íbúðir án byggingarárs (cc229 B): íbúð á landeign verkefnis með byggár NULL/0 utan Y telst með ef sama hús (landeign +
      heimilisfang) EÐA sami kaupsamningur (færslunúmer, öll ár) og eining í Y — NEMA ELDRI EIGN (cc229 f.3): fastnr. stofnað >
      2 árum á undan byggingarári systureininga; stofndagur fastnr. er EKKI til í gögnunum (properties ber aðeins skodags/
      scraped_at_latest) → VARALEIÐ: fyrsti kaupsamningur (nothæfur eða ekki) > 4 árum á undan lægsta byggári systureininga
      (sama hús, annars sama landeign)
  n_leiga (cc229 C) = fastnr. verkefnisins sem hafa verið í leiguauglýsingu (mbl/myigloo, sást fyrst ≥ SALA_FRA)
  X = einingar með þinglýstum samningi ONOTHAEFUR=0 (regla 2, eingöngu) frá SALA_FRA; magnsala = samningur > 1 fastnr,
      talin í X, merkt, utan kr/m²; HEILDARKAUP (cc228 D2′, GO Danna 11.10) = eining án nothæfs samnings með ÓNOTHÆFAN
      samning frá SALA_FRA, NEMA söluauglýsing hennar sást fyrst eftir síðasta ónothæfa samninginn EÐA hún sé á sölu núna;
      talin í X, ekkert verð (kaupverd/kr_m2 NULL, utan kr/m²), dagsetning = síðasti ónothæfi samningur; ekkert verðgólf
  verkefni = landeign; landeignir sameinaðar þar sem STAÐFEST slóð (nybygging_slodir) og gata eru sameiginleg
  gólf: Y ≥ 4 ∧ (X ≥ 1 ∨ virk auglýsing) ∧ ≥ 1 eining innan skilgreiningar
Engin Fable-/API-köll: byggingaraðili með regex.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

sys.stdout.reconfigure(encoding="utf-8")

UTGAFA = "cc224-v7"   # cc224e: = v6 + forsíðumyndir 20 nýrra verkefna úr cc229 (H); cc229 (v6): = v5 + óskipt skv. HMS (A), íbúðir án byggár tengdar (B), n_leiga (C); cc228 (v5): heildarkaup
SALA_FRA = dt.date(2021, 1, 1)
AR = dt.date.today().year
BYGGAR_SKILGR = AR - 2          # „fullbúin innan tveggja ára"
BYGGAR_Y = AR - 3               # Y: byggð ≥ 2023 (2026)
ELDRI_AR = 4                    # cc229 f.3 (B) varaleið: fyrsti samningur > 4 árum fyrir byggár systra = eldri eign
IBUD = ('Íbúð', 'Íbúð á hæð', 'Íbúð í kjallara', 'Íbúð í risi', 'Einbýlishús', 'Raðhús', 'Parhús')  # regla 7 (hvítlisti)
SKILGREINING = (f"íbúð (regla 7: {', '.join(IBUD)}; ekki sumarhús) ∧ (((FULLBUID=0 ∨ (byggingarstig B0–B3 ∧ matsstig 0–6)) ∧ "
                f"(BYGGAR ≥ {BYGGAR_Y} ∨ BYGGAR óskráð)) ∨ BYGGAR ≥ {BYGGAR_SKILGR}); Y = byggð ≥ {BYGGAR_Y} ∨ innan skilgr.; "
                f"X = ONOTHAEFUR=0 frá {SALA_FRA}; magnsala = samningur > 1 fastnr; "
                f"gólf Y ≥ 4 ∧ (X ≥ 1 ∨ virk augl.); sameining = staðfest slóð ∧ sameiginleg gata")
DSN = Path(r"D:\verdmat-is\.dbconfig")
MYNDAVAL = Path(__file__).resolve().parent / 'nybyggingar_myndaval.csv'   # handval útlitsmynda (cc224b §10)

# byggingaraðili úr auglýsingatexta (regex, cc224 fasi 0)
BA = re.compile(r'(?:byggingara[ðd]ili(?:nn)?(?: er| verkefnisins er|:)?|byggt af|verktaki(?:nn)?(?: er|:)|byggjandi(?: er|:)?)\s+'
                r'([A-ZÁÐÉÍÓÚÝÞÆÖ][\w&\.\-]*(?:\s+(?:ehf\.?|hf\.?|[A-ZÁÐÉÍÓÚÝÞÆÖ][\w&\.\-]*)){0,3})')
BA_EKKI = re.compile(r'^(Íbúð|Íbúðir|Húsið|Eignin|Verkefnið|Sjá|Nánar|Allar|Hér|Um|Til|Frá|Í|Á|Með|Og|Er|Sem|Hann|Það|Fasteignasal)', re.I)
# handvirk samheiti (beygingar/brot sem regex skilar) → nefnifall; CC-handrýni 09.10, engin API-köll
BA_SAMHEITI = {'Skugga': 'Skuggi', 'Þ.G': 'ÞG Verk', 'ÞG Verk. Útveggir': 'ÞG Verk', 'Byggingarfélagi Bakka ehf': 'Byggingarfélagið Bakki ehf',
               'Byggingarfélag Gylfa': 'Byggingarfélag Gylfa og Gunnars hf', 'BYGG': 'Byggingarfélag Gylfa og Gunnars hf'}
BA_MIN_AUGL = 2                 # byggingaraðili birtist aðeins ef hann finnst í ≥ 2 auglýsingum verkefnisins
KR_M2_GOLF = 100_000            # kr/m² undir þessu = villa í verði/stærð (t.d. 43 þús./m²) → utan tölfræði
ASETT_GOLF = 1_000_000          # ásett verð undir 1 m.kr. = leiga/villa → utan tölfræði
ENDURSALA_DAGAR = 180           # „endursala" ef auglýst > 180 d eftir þinglýsta sölu (eða önnur stofa) — Danni 10.10
LAEKKUN_DAGAR = 30            # lækkunarmerki kassa = gluggi Verðvaktarinnar (sjálfgefið „síðustu 30 dagar“)
HEIMILISFANG = re.compile(r'^(.*?)\s+(\d+)\s*([A-Za-zÁÐÉÍÓÚÝÞÆÖáðéíóúýþæö]?)\b')


def tengja():
    c = psycopg2.connect(DSN.read_text(encoding="utf-8-sig").strip(), connect_timeout=15)
    c.autocommit = False
    return c


def lesa(c):
    cur = c.cursor()
    cur.execute("SET TRANSACTION READ ONLY")
    cur.execute("SET LOCAL statement_timeout = '600s'")
    # aldursvörn (Danni 09.10, v3 10.10): FULLBUID=0 OG byggingarstigs-greinin telja aðeins ef byggár ≥ ár−3 eða óskráð (NULL/0)
    skilgr_sql = (f"(((p.fullbuid = 0 or (p.byggingarstig in ('B0','B1','B2','B3') and p.matsstig ~ '^[0-6]$')) "
                  f"and coalesce(nullif(p.byggar, 0), 9999) >= {BYGGAR_Y}) or p.byggar >= {BYGGAR_SKILGR})")
    ibud_sql = "(p.tegund_raw = any(%(ibud)s) and coalesce(p.unit_family,'') <> 'summerhouse' and not coalesce(p.deregistered,false))"
    prm = dict(ibud=list(IBUD))
    cur.execute(f"select count(*) from public.properties p where {ibud_sql} and {skilgr_sql}", prm)
    n_skilgr_land = cur.fetchone()[0]
    P = pd.read_sql(f"""
        select p.fastnum, p.heimilisfang, p.postnr, p.postheiti, p.sveitarfelag, p.einflm, p.byggar, p.fjherb, p.fullbuid,
               p.byggingarstig, p.matsstig, p.landeign_nr, p.lat, p.lng,
               (select m->>'merking' from jsonb_array_elements(case when jsonb_typeof(p.matseiningar)='array'
                        then p.matseiningar else '[]'::jsonb end) m where (m->>'fastnum')::bigint = p.fastnum limit 1) merking,
               (select count(*) from jsonb_array_elements(case when jsonb_typeof(p.matseiningar)='array'
                        then p.matseiningar else '[]'::jsonb end) m
                 where (m->>'fastnum')::bigint = p.fastnum and m->>'notkun_texti' ilike 'Íbúð%%') n_ibud_hms,
               coalesce({skilgr_sql}, false) innan_skilgr,
               not coalesce({skilgr_sql} or p.byggar >= {BYGGAR_Y}, false) byggar_kandidat
          from public.properties p
         where {ibud_sql} and p.landeign_nr is not null
           and (({skilgr_sql} or p.byggar >= {BYGGAR_Y})
                or (coalesce(nullif(p.byggar, 0), -1) = -1 and p.landeign_nr in (
                      select p.landeign_nr from public.properties p
                       where {ibud_sql} and p.landeign_nr is not null and ({skilgr_sql} or p.byggar >= {BYGGAR_Y}))))""", c, params=prm)
    fn = [int(x) for x in P.fastnum]
    # cc229 B: ALLIR samningar (öll ár, nothæfir og ónothæfir) — tenging um færslunúmer og vörn „eldri eign"; aldrei verð
    SA = pd.read_sql("""select fastnum, faerslunumer, thinglystdags from public.sales_history where fastnum = any(%(fn)s)""",
                     c, params=dict(fn=fn))
    # cc229 C: leiguauglýsingar á fastnr. (sást fyrst ≥ SALA_FRA)
    RL = pd.read_sql("""select distinct fastnum from scraper.listings
                          where tenure = 'rent' and fastnum = any(%(fn)s) and first_seen_at >= %(fra)s""", c, params=dict(fn=fn, fra=SALA_FRA))
    S = pd.read_sql("""
        with s as (select id, fastnum, thinglystdags, kaupverd_nominal, einflm_at_sale, onothaefur, faerslunumer
                     from public.sales_history where fastnum = any(%(fn)s) and thinglystdags >= %(fra)s)
        select s.*, case when s.faerslunumer is null then 1 else
                    (select count(distinct h.fastnum) from public.sales_history h where h.faerslunumer = s.faerslunumer) end nf
          from s""", c, params=dict(fn=fn, fra=SALA_FRA))
    L = pd.read_sql("""
        select l.listing_id, l.source, l.source_listing_id, l.fastnum, l.price_amount, l.is_price_on_request, l.size_sqm, l.rooms,
               l.addr_text, l.lysing, l.first_seen_at, coalesce(l.listed_at, l.first_seen_at) birt, l.agency_name, l.agency_source_id,
               exists (select 1 from scraper.v_eign_virk_auglysing v where v.listing_id = l.listing_id) virk
          from scraper.listings l
         where l.tenure = 'sale' and l.category = 'residential' and l.fastnum = any(%(fn)s)""", c, params=dict(fn=fn))
    # forsíðumyndir: handval (cc224_myndaval_lesa.py → nybyggingar_myndaval.csv)
    import csv as _csv
    MV = {r['verkefni_id']: r for r in _csv.DictReader(open(MYNDAVAL, encoding='utf-8'))} if MYNDAVAL.exists() else {}
    MY = pd.read_sql("select sha256, lykill, breidd, haed, baeti, hladid_kl from semantic.nybygging_myndir", c)
    VV = pd.read_sql("""
        select listing_id, fastnum, stefna, fyrra_verd, nytt_verd, nytt_sast, flokkur, a_solu from semantic.v_verdvakt_breytingar_v2
         where fastnum = any(%(fn)s) and not coalesce(hlutd_grunur,false) and not coalesce(arekstur,false)
           and not coalesce(grunur_villa,false) and not coalesce(grunsamleg,false)""",
                     c, params=dict(fn=fn))
    VM = pd.read_sql("select sala_id, lykill, birtingarheiti from scraper.fasteignasala_vorumerki", c)
    SL = pd.read_sql("select landeign_nr, slod from semantic.nybygging_slodir where stadfest order by landeign_nr, slod", c)
    cur.execute("select max(thinglystdags) from public.sales_history"); data_through = cur.fetchone()[0]
    cur.execute("select max(last_seen_at) from scraper.listings where tenure='sale'"); snap = cur.fetchone()[0]
    c.rollback()
    return dict(P=P, S=S, SA=SA, RL=RL, L=L, MV=MV, MY=MY, VV=VV, VM=VM, SL=SL, n_skilgr_land=n_skilgr_land, data_through=data_through, snap=snap)


def ba_ur_texta(t):
    m = BA.search(t or '')
    if not m:
        return None
    n = m.group(1).strip(' .,')
    n = re.sub(r'^(.*?\b(?:ehf|hf))\b.*$', r'\1', n)      # skera aftan við ehf/hf
    n = BA_SAMHEITI.get(n, n)
    return None if BA_EKKI.match(n) or len(n) < 3 else n


def gata_hus(h):
    h = h if isinstance(h, str) else ''
    m = HEIMILISFANG.match(h)
    return (m.group(1).strip(), int(m.group(2)), m.group(3).upper()) if m else (h.strip() or None, None, '')


def heiti_ur_hms(df):
    g = Counter()
    nr = {}
    for h in df.heimilisfang.dropna():
        gata, n, st = gata_hus(h)
        if not gata:
            continue
        g[gata] += 1
        if n is not None:
            nr.setdefault(gata, set()).add((n, st))
    if not g:
        return None, []
    gotur = [k for k, _ in sorted(g.items(), key=lambda kv: (-kv[1], kv[0]))]
    def fmt(gata):
        s = sorted(nr.get(gata, set()))
        if not s:
            return gata
        if len({n for n, _ in s}) == 1:
            stafir = [st for _, st in s if st]
            return f"{gata} {s[0][0]}" + (f"{stafir[0]}–{stafir[-1]}" if len(stafir) > 1 else (stafir[0] if stafir else ''))
        return f"{gata} {s[0][0]}–{s[-1][0]}"
    h = ', '.join(fmt(x) for x in gotur[:2]) + (' o.fl.' if len(gotur) > 2 else '')
    return h, gotur


def heiti_ur_augl(addr):
    a = [re.sub(r'\s*[-,(].*$', '', x).strip() for x in addr.dropna() if x and x.strip()]
    return Counter(a).most_common(1)[0][0] if a else None


def slugify(s):
    t = s.lower().replace('–', '-').replace('þ', 'th').replace('ð', 'd').replace('æ', 'ae').replace('ö', 'o')
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', t)).strip('-')[:60]


def verkefnalykill(U, SL):
    """landeign; sameinað um staðfesta slóð ∧ sameiginlega götu (union-find). Skilar (Series fastnum->verkefni_id, n_sameinad)."""
    lei = sorted(U.landeign_nr.unique(), key=lambda x: (len(x), x))
    foreldri = {x: x for x in lei}
    def finna(a):
        while foreldri[a] != a:
            foreldri[a] = foreldri[foreldri[a]]; a = foreldri[a]
        return a
    gotur = U.assign(g=U.heimilisfang.map(lambda h: gata_hus(h)[0])).dropna(subset=['g']).groupby('landeign_nr').g.agg(set)
    SL = SL[SL.landeign_nr.isin(foreldri)]
    for _, les in SL.groupby('slod').landeign_nr:
        les = sorted(set(les), key=lambda x: (len(x), x))
        for i, a in enumerate(les):
            for b in les[i + 1:]:
                if gotur.get(a, set()) & gotur.get(b, set()):
                    ra, rb = finna(a), finna(b)
                    if ra != rb:
                        lo, hi = sorted([ra, rb], key=lambda x: (len(x), x))
                        foreldri[hi] = lo
    kort = {x: finna(x) for x in lei}
    return U.landeign_nr.map(kort), sum(1 for k, v in kort.items() if k != v)


def _gata(h):
    return re.sub(r'\s+', ' ', h.strip().lower()) if isinstance(h, str) else ''


def tengja_byggar_kandidata(U, SA):
    """cc229 B: íbúðir án byggingarárs (byggar_kandidat) inn í Y ef tengdar einingu í Y um sama hús (landeign + heimilisfang)
    EÐA sama kaupsamning (færslunúmer, öll ár) — nema ELDRI EIGN (cc229 f.3): stofndagur fastnr. ekki til → varaleið: fyrsti
    kaupsamningur (nothæfur eða ekki) > ELDRI_AR árum á undan lægsta byggári systureininga (sama hús, annars sama landeign).
    Skilar (U án ótengdra og stöðvaðra, talningu)."""
    k = U.byggar_kandidat.astype(bool)
    Y0 = U[~k]
    K = U[k].copy()
    hus = set(zip(Y0.landeign_nr, Y0.heimilisfang.map(_gata)))
    K['sama_hus'] = [(l, _gata(h)) in hus and _gata(h) != '' for l, h in zip(K.landeign_nr, K.heimilisfang)]
    sa = SA.dropna(subset=['faerslunumer']).copy()
    sa['fastnum'] = sa.fastnum.astype('int64')
    f_y = set(sa[sa.fastnum.isin(Y0.fastnum)].faerslunumer)
    K['sami_pakki'] = K.fastnum.isin(sa[sa.faerslunumer.isin(f_y)].fastnum)
    K['tengd'] = K.sama_hus | K.sami_pakki
    by_hus = Y0.assign(h=Y0.heimilisfang.map(_gata)).groupby(['landeign_nr', 'h']).by.min()
    by_land = Y0.groupby('landeign_nr').by.min()
    K['by_systra'] = [by_hus.get((l, _gata(h)), np.nan) for l, h in zip(K.landeign_nr, K.heimilisfang)]
    K['by_systra'] = K.by_systra.fillna(K.landeign_nr.map(by_land))
    fyrsti = pd.to_datetime(SA.thinglystdags).groupby(SA.fastnum.astype('int64')).min()
    K['fyrsti_ar'] = K.fastnum.map(fyrsti).dt.year
    K['eldri'] = K.tengd & K.fyrsti_ar.notna() & K.by_systra.notna() & ((K.by_systra - K.fyrsti_ar) > ELDRI_AR)
    inn = K[K.tengd & ~K.eldri]
    auk = dict(b_kandidatar=int(len(K)), b_tengd=int(K.tengd.sum()), b_sama_hus=int(K.sama_hus.sum()),
               b_sami_pakki=int(K.sami_pakki.sum()), b_eldri=int(K.eldri.sum()), b_inn=int(len(inn)),
               b_an_vidmids=int((K.tengd & K.by_systra.isna()).sum()), b_K=K)
    return pd.concat([Y0, inn]), auk


def reikna(D):
    P, S, L, VV, VM = D['P'], D['S'].copy(), D['L'].copy(), D['VV'], D['VM']
    U = P.copy()
    U['fastnum'] = U.fastnum.astype('int64')
    U['by'] = pd.to_numeric(U.byggar, errors='coerce').where(lambda x: x > 0)     # byggar 0 = óskráð
    U, auk_b = tengja_byggar_kandidata(U, D['SA'])
    U['sveitarfelag'] = U.sveitarfelag.str.strip()
    L['fastnum'] = L.fastnum.astype('int64')
    L['sz'] = pd.to_numeric(L.size_sqm, errors='coerce').round(0)
    L['rm'] = pd.to_numeric(L.rooms, errors='coerce')

    # óskipt fastnúmer (cc229 A, regla 1): HMS skráir eitt fastnr. með ≥ 2 íbúðarmatseiningum (eignaskiptayfirlýsing ekki
    # komin); Y-framlag = fjöldi íbúðarmatseininga HMS. (Áður: ≥ 3 ólíkar auglýstar stærðir — vantaldi, Baughamar 7: 5 vs 55.)
    nhms = pd.to_numeric(U.n_ibud_hms, errors='coerce').fillna(0).astype(int)
    U['heildareining'] = nhms >= 2
    U['n_undireiningar'] = np.where(U.heildareining, nhms, 1).astype(int)

    # ónothæfir samningar (cc228 D2′): aðeins dagsetning síðasta per fastnr — aldrei verð (regla 2)
    So = S[S.onothaefur == 1]
    ono_sidast = pd.to_datetime(So.thinglystdags).groupby(So.fastnum.astype('int64')).max()
    # sölur — regla 2: ONOTHAEFUR=0 eingöngu
    S = S[S.onothaefur == 0].copy()
    S['fastnum'] = S.fastnum.astype('int64')
    S['t'] = pd.to_datetime(S.thinglystdags)
    S = S.sort_values(['t', 'id'])
    mk = S[S.nf == 1].groupby('fastnum').first()
    mg = S[S.nf > 1].groupby('fastnum').first()
    U['sala_dags'] = U.fastnum.map(mk.t).fillna(U.fastnum.map(mg.t))
    U['magnsala'] = U.fastnum.isin(mg.index) & ~U.fastnum.isin(mk.index)
    U['seld'] = U.sala_dags.notna()
    U['kaupverd'] = U.fastnum.map(mk.kaupverd_nominal)
    flm = pd.to_numeric(U.fastnum.map(mk.einflm_at_sale), errors='coerce')
    U['kr_m2'] = np.where((flm > 0) & U.kaupverd.notna(), U.kaupverd / flm, np.nan)
    U.loc[U.heildareining | (U.kr_m2 < KR_M2_GOLF), 'kr_m2'] = np.nan

    # auglýsingar og verðbreytingar verkefnisins = á óseldri einingu eða fyrir fyrstu sölu hennar
    # (endursala seldrar íbúðar er ekki virkni verkefnisins og stofa endursölunnar ekki söluaðili þess)
    L['t0'] = pd.to_datetime(L.first_seen_at, utc=True).dt.tz_localize(None)
    L['birt'] = pd.to_datetime(L.birt, utc=True).dt.tz_localize(None)
    vm = VM.set_index('sala_id')
    L['stofa_lykill'] = L.agency_source_id.map(vm.lykill).fillna(L.agency_name.fillna('').str.strip().str.lower())
    Lallar = L.copy()                    # allar söluauglýsingar einingarinnar, líka endursala (auglýsingahlekkur)
    L = L[~(L.t0 > L.fastnum.map(U.set_index('fastnum').sala_dags))].copy()

    # virkar auglýsingar — eignarstig (v_eign_virk_auglysing); eining = fastnr, óskipt = (fastnr, stærð, herbergi)
    AV = L[L.virk]
    nvirk = AV.drop_duplicates(['fastnum', 'sz', 'rm']).groupby('fastnum').size()
    U['n_virk'] = np.where(U.heildareining, U.fastnum.map(nvirk).fillna(0), U.fastnum.isin(AV.fastnum).astype(int)).astype(int)
    U['n_virk'] = np.minimum(U.n_virk, U.n_undireiningar)
    av1 = AV[(AV.price_amount >= ASETT_GOLF) & ~AV.is_price_on_request.fillna(False)].sort_values('first_seen_at').groupby('fastnum').last()
    U['asett_verd'] = np.where(U.heildareining, np.nan, U.fastnum.map(av1.price_amount))
    U['asett_flm'] = np.where(U.heildareining, np.nan, U.fastnum.map(av1.size_sqm))

    # Verðvakt v2 — sömu gátir og Verðvaktin (lib/verdvakt-queries.js `gild`: hlutd_grunur, arekstur, grunur_villa,
    # grunsamleg; cc224c), afrituð per (fastnr, dags, verð). Aðeins fyrsta sala: breyting sem sást EFTIR sölu er endursala.
    vv = VV.dropna(subset=['fastnum']).copy()
    vv['fastnum'] = vv.fastnum.astype('int64')
    vv['ts'] = pd.to_datetime(vv.nytt_sast, utc=True).dt.tz_localize(None)
    vv['d'] = vv.ts.dt.normalize()
    vv = vv.sort_values(['fastnum', 'ts', 'listing_id']).drop_duplicates(['fastnum', 'd', 'nytt_verd', 'stefna'])
    vv = vv[~(vv.d > vv.fastnum.map(U.set_index('fastnum').sala_dags))]
    lk = vv[vv.stefna == 'laekkun']
    U['n_laekkanir'] = U.fastnum.map(lk.groupby('fastnum').size()).fillna(0).astype(int)
    # síðasta lækkun (dálkur verkefnissíðu) og lækkunarmerki (cc224c): lækkun í auglýsingu EÐA endurbirt á lægra verði
    # sem sást síðustu LAEKKUN_DAGAR daga (frá keyrslu), auglýsingin á sölu (a_solu, sjálfgefið Verðvaktar) og einingin á
    # sölu í fyrstu sölu núna (stada a_solu — sami teljari og „á sölu núna")
    sl = lk.groupby('fastnum').last()
    U['laekkun_dags'] = U.fastnum.map(sl.d)
    U['laekkun_fra'] = U.fastnum.map(sl.fyrra_verd)
    U['laekkun_til'] = U.fastnum.map(sl.nytt_verd)
    U['laekkun_flokkur'] = U.fastnum.map(sl.flokkur)
    nylega = lk[(lk.ts >= pd.Timestamp.now(tz='UTC').tz_localize(None) - pd.Timedelta(days=LAEKKUN_DAGAR)) & lk.a_solu.fillna(False)]
    U['laekkad_30'] = U.fastnum.isin(nylega.fastnum)
    U['sidasta_verdbr'] = U.fastnum.map(vv.groupby('fastnum').d.max())
    U['sidasta_ny_augl'] = U.fastnum.map(L.groupby('fastnum').t0.max())

    # heildarkaup (cc228 D2′): ónothæfur samningur án nothæfs, ekki endurauglýst til sölu eftir hann, ekki á sölu núna
    U['ono_dags'] = U.fastnum.map(ono_sidast)
    endurauglyst = U.fastnum.map(Lallar.groupby('fastnum').t0.max()).gt(U.ono_dags)
    U['heildarkaup'] = ~U.seld & U.ono_dags.notna() & ~endurauglyst & (U.n_virk == 0)
    U['stada'] = np.select([U.seld & ~U.magnsala, U.magnsala, U.heildarkaup, U.n_virk > 0],
                           ['seld', 'magnsala', 'heildarkaup', 'a_solu'], 'oseld')
    U['x'] = np.where(U.seld | U.heildarkaup, U.n_undireiningar, 0)
    U['laekkad_30'] = U.laekkad_30 & (U.stada == 'a_solu')
    U['virk_oseld'] = np.where(U.seld, 0, U.n_virk)

    # auglýsingahlekkur: nýjasta VIRKA mbl-söluauglýsing einingarinnar (eignarstig). augl_endursala = einingin var seld
    # ÁÐUR en auglýsingin sást fyrst; seld eining með auglýsingu frá því fyrir sölu fær False (framendinn merkir hana sér)
    la_virk = Lallar[Lallar.virk & (Lallar.source == 'mbl') & Lallar.source_listing_id.notna()]
    augl = la_virk.sort_values(['birt', 'listing_id']).groupby('fastnum').last()
    U['augl_id'] = U.fastnum.map(augl.source_listing_id)
    U['augl_t0'] = U.fastnum.map(augl.t0)
    U['augl_stofa'] = U.fastnum.map(augl.stofa_lykill)

    U['verkefni_id'], n_sameinad = verkefnalykill(U, D['SL'])

    # flokkur auglýsingahlekks (ákvörðun Danna 10.10, cc224b §9.6): seld eining með auglýsingu sem sást fyrst EFTIR
    # þinglýsingu = „endursala" aðeins ef > ENDURSALA_DAGAR frá sölu EÐA önnur stofa en auglýsti eininguna fyrir sölu
    # (engin slík → söluaðilar verkefnisins fyrir sölu); annars „eftir_solu". Auglýsing frá því fyrir sölu = „fyrir_solu".
    sd = U.set_index('fastnum').sala_dags
    fyrir = Lallar[(Lallar.t0 <= Lallar.fastnum.map(sd)) & (Lallar.stofa_lykill != '')]
    stofur_einingar = fyrir.groupby('fastnum').stofa_lykill.agg(set)
    stofur_verkefnis = fyrir.assign(v=fyrir.fastnum.map(U.set_index('fastnum').verkefni_id)).groupby('v').stofa_lykill.agg(set)
    def augl_flokkur(r):
        if pd.isna(r.augl_id):
            return None
        if not r.seld:
            return 'fyrsta_sala'
        if not (pd.notna(r.augl_t0) and r.augl_t0 > r.sala_dags):
            return 'fyrir_solu'
        vidmid = stofur_einingar.get(r.fastnum) or stofur_verkefnis.get(r.verkefni_id) or set()
        onnur = r.augl_stofa not in vidmid
        return 'endursala' if (r.augl_t0 - r.sala_dags).days > ENDURSALA_DAGAR or onnur else 'eftir_solu'
    U['augl_flokkur'] = U.apply(augl_flokkur, axis=1)
    U['augl_endursala'] = np.where(U.augl_id.notna(), U.augl_flokkur == 'endursala', None)

    # stofa: vörumerki (sala_id) ef til, annars agency_name
    vm = VM.set_index('sala_id')
    L['stofa_lykill'] = L.agency_source_id.map(vm.lykill).fillna(L.agency_name.fillna('').str.strip().str.lower())
    L['stofa_nafn'] = L.agency_source_id.map(vm.birtingarheiti).fillna(L.agency_name)
    L['ba'] = L.lysing.fillna('').map(ba_ur_texta)
    L = L.merge(U[['fastnum', 'verkefni_id']], on='fastnum')

    rows = []
    for vid, g in U.groupby('verkefni_id'):
        la = L[L.verkefni_id == vid]
        Y = int(g.n_undireiningar.sum()); X = int(g.x.sum())
        n_virk_any = int(g.n_virk.sum())
        # gólf á NOTHÆFUM sölum (cc228): heildarkaup færa X en hleypa ekki nýjum verkefnum inn
        X_golf = int(np.where(g.seld, g.n_undireiningar, 0).sum())
        if not (Y >= 4 and (X_golf >= 1 or n_virk_any >= 1) and g.innan_skilgr.any()):
            rows.append(dict(verkefni_id=vid, golf=False)); continue
        heiti, gotur = heiti_ur_hms(g)
        uppruni = 'hms'
        if not heiti:
            heiti, uppruni = heiti_ur_augl(la.addr_text), 'auglysing'
        if not heiti:
            heiti, uppruni = f"Landeign {vid}", 'hms'
        seldar = g[(g.stada == 'seld') & g.kr_m2.notna() & ~g.heildareining]
        # ásett kr/m²: óseld venjuleg eining = nýjasta virka auglýsing hennar (1 per fastnr); óskipt = (stærð, herbergi)
        a = la[la.virk & (la.sz > 0) & (la.price_amount >= ASETT_GOLF) & ~la.is_price_on_request.fillna(False)]
        a = a[a.fastnum.isin(g[~g.seld & g.heildareining].fastnum)].drop_duplicates(['fastnum', 'sz', 'rm'])
        e1 = g[~g.seld & ~g.heildareining & g.asett_verd.notna() & (pd.to_numeric(g.asett_flm, errors='coerce') > 0)]
        a = pd.concat([a[['price_amount', 'size_sqm']],
                       pd.DataFrame(dict(price_amount=e1.asett_verd, size_sqm=pd.to_numeric(e1.asett_flm)))])
        st = Counter()
        nofn = {}
        sd = la[la.stofa_lykill != ''].drop_duplicates(['stofa_lykill', 'fastnum', 'sz', 'rm'])
        for k, n in zip(sd.stofa_lykill, sd.stofa_nafn):
            st[k] += 1; nofn.setdefault(k, n)
        stofur = [dict(lykill=k, nafn=nofn[k], n_einingar=v) for k, v in sorted(st.items(), key=lambda kv: (-kv[1], kv[0]))[:3]]
        ba = Counter(la.dropna(subset=['ba']).drop_duplicates(['listing_id']).ba)
        ba = {k: v for k, v in ba.items() if v >= BA_MIN_AUGL}
        ba_n, ba_nafn = (max((v, k) for k, v in ba.items()) if ba else (0, None))
        bs = g.byggingarstig.fillna('')
        hms_n = len(g)
        virkni = [g.sala_dags.max(), g.sidasta_verdbr.max(), g.sidasta_ny_augl.max()]
        virkni = max([v for v in virkni if pd.notna(v)])
        seld_d = g[g.seld].sala_dags
        # forsíðumynd: HANDVALIN útlitsmynd (scripts/nybyggingar_myndaval.csv, cc224b §10); ekkert val eða „engin" → engin mynd
        mv = D['MV'].get(vid)
        mynd = mv if mv and mv['sha256'] else None
        rows.append(dict(
            mynd_sha256=mynd['sha256'] if mynd else None,
            mynd_lykill_frumrit=mynd['r2_lykill'] if mynd else None,
            mynd_stofa=(mynd['stofa'].strip() or None) if mynd else None,
            mynd_dags=dt.date.fromisoformat(mynd['birt']) if mynd and mynd['birt'] else None,
            mynd_listing_id=int(mynd['listing_id']) if mynd else None,
            verkefni_id=vid, golf=True, heiti=heiti, heiti_uppruni=uppruni, gotur=gotur or [],
            postnr=int(g.postnr.mode().iloc[0]) if g.postnr.notna().any() else None,
            postheiti=g.postheiti.mode().iloc[0] if g.postheiti.notna().any() else None,
            sveitarfelag=g.sveitarfelag.mode().iloc[0] if g.sveitarfelag.notna().any() else None,
            landeignir=sorted(g.landeign_nr.unique(), key=lambda x: (len(x), x)),
            lat=float(g.lat.median()) if g.lat.notna().any() else None, lng=float(g.lng.median()) if g.lng.notna().any() else None,
            n_einingar=Y, n_einingar_hms=hms_n, n_heildareiningar=int(g.heildareining.sum()),
            n_seld=X, n_magnseld=int(g[g.magnsala].n_undireiningar.sum()),
            n_heildarkaup=int(g[g.stada == 'heildarkaup'].n_undireiningar.sum()),
            n_leiga=int(g.fastnum.isin(D['RL'].fastnum.astype('int64')).sum()),
            n_virkar=int(g.virk_oseld.sum()), n_oseldar=Y - X, n_oseldar_oauglystar=Y - X - int(g.virk_oseld.sum()),
            n_b0=int((~bs.isin(['B1', 'B2', 'B3', 'B4'])).sum()), n_b1=int((bs == 'B1').sum()), n_b2=int((bs == 'B2').sum()),
            n_b3=int((bs == 'B3').sum()), n_b4=int((bs == 'B4').sum()),
            fyrsta_sala=seld_d.min().date() if len(seld_d) else None, sidasta_sala=seld_d.max().date() if len(seld_d) else None,
            kr_m2_seld=int(round(seldar.kr_m2.median())) if len(seldar) else None, n_kr_m2_seld=len(seldar),
            kr_m2_asett=int(round((a.price_amount / a.size_sqm.astype(float)).median())) if len(a) else None, n_kr_m2_asett=len(a),
            n_laekkanir=int(g.n_laekkanir.sum()), n_laekkad_30=int(g.laekkad_30.sum()), stofur=stofur,
            byggingaradili=ba_nafn, byggingaradili_n_augl=int(ba_n), slod=None,
            byggar_min=int(g.by.min()) if g.by.notna().any() else None, byggar_max=int(g.by.max()) if g.by.notna().any() else None,
            sidasta_virkni=pd.Timestamp(virkni).date(), uppselt=(X == Y)))
    V = pd.DataFrame(rows)
    n_hopar = len(V)
    V = V[V.golf].drop(columns='golf').copy()
    V['slug'] = [f"{v}-{slugify(h)}" for v, h in zip(V.verkefni_id, V.heiti)]
    # slóð verkefnis = staðfest slóð sem nær yfir flestar landeignir þess (jafntefli: stafrófsröð)
    def slod_verkefnis(les):
        c = Counter(D['SL'][D['SL'].landeign_nr.isin(les)].slod)
        return min(c.items(), key=lambda kv: (-kv[1], kv[0]))[0] if c else None
    V['slod'] = V.landeignir.map(slod_verkefnis)
    V = V.sort_values(['uppselt', 'sidasta_virkni', 'verkefni_id'], ascending=[True, False, True]).reset_index(drop=True)

    E = U[U.verkefni_id.isin(V.verkefni_id)].copy()
    def merk(m):
        return f"{m[:2]}-{m[2:]}" if isinstance(m, str) and re.fullmatch(r'\d{6}', m) else m
    E = pd.DataFrame(dict(
        fastnum=E.fastnum, verkefni_id=E.verkefni_id, heimilisfang=E.heimilisfang, merking=E.merking.map(merk),
        einflm=pd.to_numeric(E.einflm, errors='coerce'), fjherb=pd.to_numeric(E.fjherb, errors='coerce'),
        byggar=E.by, byggingarstig=E.byggingarstig, innan_skilgr=E.innan_skilgr.astype(bool),
        heildareining=E.heildareining.astype(bool), n_undireiningar=E.n_undireiningar, stada=E.stada,
        sala_dags=E.sala_dags.dt.date, kaupverd=np.where(E.stada == 'seld', E.kaupverd, np.nan),
        kr_m2=np.where((E.stada == 'seld') & E.kr_m2.notna(), E.kr_m2.round(), np.nan),
        asett_verd=E.asett_verd, asett_flm=E.asett_flm, n_laekkanir=E.n_laekkanir,
        laekkun_dags=E.laekkun_dags.dt.date, laekkun_fra=E.laekkun_fra, laekkun_til=E.laekkun_til,
        laekkun_flokkur=E.laekkun_flokkur, laekkad_30=E.laekkad_30.astype(bool),
        augl_id=E.augl_id, augl_endursala=E.augl_endursala, augl_flokkur=E.augl_flokkur))
    E['sala_dags'] = E.sala_dags.where(E.stada.isin(['seld', 'magnsala']))
    hk = E.stada == 'heildarkaup'
    E.loc[hk, 'sala_dags'] = E.loc[hk, 'fastnum'].map(ono_sidast).dt.date
    E = E.sort_values(['verkefni_id', 'fastnum']).reset_index(drop=True)   # föst röð → endurtekjanlegt md5
    return V, E, dict(n_hopar=n_hopar, n_sameinad=n_sameinad, U=U, **auk_b)


def utvikka_slodir(slodir, D):
    """Staðfest slóð → allar landeignir (í Y-mengi) þar sem slóðin stendur í texta söluauglýsingar. Sama regla og
    innlestur slodir_ryni.csv notar þegar Danni skilar (ein röð per landeign × slóð í nybygging_slodir)."""
    P, L = D['P'], D['L']
    lf = L[['fastnum', 'lysing']].dropna().merge(P[['fastnum', 'landeign_nr']], on='fastnum')
    txt = lf.lysing.str.lower()
    ut = []
    for s in slodir:
        # heil slóð: ekki hluti af lengra léni (g1.is ≠ teig1.is) og ekki forskeyti lengri slóðarliðar
        m = txt.str.contains(r'(?<![\w.\-])(?:www\.)?' + re.escape(s.lower()) + r'(?![\w\-])', regex=True)
        for le in sorted(lf[m].landeign_nr.unique()):
            ut.append(dict(landeign_nr=le, slod=s))
    return pd.DataFrame(ut, columns=['landeign_nr', 'slod'])


RCLONE = Path(r"D:\verdmat-is\tools\rclone\rclone.exe")
RCLONE_CONF = Path(r"D:\verdmat-is\tools\rclone\rclone.conf")
FRUMRIT_REMOTE = "r2backup:verdmat-backups"    # frumrit LESIN héðan; aldrei skrifað (lokuð afritafata, cc117 §0)
MYNDA_STORE = Path(r"D:\verdmat-is\myndir_nyb")  # staðbundið eintak minnkaðra útgáfa, sami lykill og á hýsli
SMA_BREIDD, WEBP_GAEDI = 720, 80


def sma_lykill(sha):
    return f"nyb/{SMA_BREIDD}/{sha[:2]}/{sha}.webp"


def rclone(*args, timeout=3600):
    import subprocess
    p = subprocess.run([str(RCLONE), *args, "--config", str(RCLONE_CONF)], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"rclone {args[0]} féll ({p.returncode}): {p.stderr[-400:]}")
    return p


def smida_myndir(c, V, MY, hlada_remote=None):
    """Minnkar forsíðumyndir sem vantar í semantic.nybygging_myndir EINU SINNI (720 px WebP) og skráir stærðina.
    Með hlada_remote: afritar óhlaðnar útgáfur á opinbera myndahýsilinn, sannprófar (rclone check) og merkir hladid_kl."""
    from PIL import Image, ImageOps
    if hlada_remote and hlada_remote.rstrip('/').split('/')[0] == FRUMRIT_REMOTE:
        raise SystemExit(f"NEITA: {hlada_remote} er afritafatan — birtingarmyndir fara aldrei þangað")
    vantar = V.dropna(subset=['mynd_sha256'])
    vantar = vantar[~vantar.mynd_sha256.isin(MY.sha256)].drop_duplicates('mynd_sha256')
    nyjar = []
    if len(vantar):
        tmp = MYNDA_STORE / '_frumrit_tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        ff = tmp / 'files_from.txt'
        ff.write_text('\n'.join(vantar.mynd_lykill_frumrit) + '\n', encoding='utf-8')
        rclone('copy', FRUMRIT_REMOTE, str(tmp), '--files-from', str(ff), '--transfers', '8', '--no-traverse')
        for r in vantar.itertuples():
            src = tmp / r.mynd_lykill_frumrit
            if not src.exists():
                print(f'  mynd vantar í afriti: {r.mynd_lykill_frumrit}'); continue
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im).convert('RGB')
                fb, fh = im.size
                if fb > SMA_BREIDD:
                    im = im.resize((SMA_BREIDD, round(fh * SMA_BREIDD / fb)), Image.LANCZOS)
                ut = MYNDA_STORE / sma_lykill(r.mynd_sha256)
                ut.parent.mkdir(parents=True, exist_ok=True)
                im.save(ut, 'WEBP', quality=WEBP_GAEDI, method=6)
                nyjar.append((r.mynd_sha256, r.mynd_lykill_frumrit, sma_lykill(r.mynd_sha256), im.size[0], im.size[1],
                              ut.stat().st_size, fb, fh, src.stat().st_size))
            src.unlink()
    cur = c.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    cur.execute("SET LOCAL lock_timeout = '10s'")
    cur.execute("SET LOCAL statement_timeout = '120s'")
    if nyjar:
        execute_values(cur, """insert into semantic.nybygging_myndir (sha256, lykill_frumrit, lykill, breidd, haed, baeti,
                                 frumrit_breidd, frumrit_haed, frumrit_baeti) values %s on conflict (sha256) do nothing""", nyjar)
    n_hladid = 0
    if hlada_remote:
        # aðeins myndir sem verkefni þessarar keyrslu vísa í (ónotað eldra val fer aldrei á opinbera hýsilinn)
        cur.execute("select lykill from semantic.nybygging_myndir where hladid_kl is null and sha256 = any(%s)",
                    (list(V.mynd_sha256.dropna()),))
        oh = [r[0] for r in cur.fetchall()]
        if oh:
            ff = MYNDA_STORE / 'hlada_files_from.txt'
            ff.write_text('\n'.join(oh) + '\n', encoding='utf-8')
            rclone('copy', str(MYNDA_STORE), hlada_remote, '--files-from', str(ff), '--no-traverse', '--transfers', '8')
            rclone('check', str(MYNDA_STORE), hlada_remote, '--files-from', str(ff), '--one-way')
            cur.execute("update semantic.nybygging_myndir set hladid_kl = now() where lykill = any(%s)", (oh,))
            n_hladid = len(oh)
    c.commit()
    MY = pd.read_sql("select sha256, lykill, breidd, haed, baeti, hladid_kl from semantic.nybygging_myndir", c)
    c.rollback()
    return MY, len(nyjar), n_hladid


def mynd_i_verkefni(V, MY):
    """mynd_lykill/breidd/haed úr skránni (aðeins myndir sem eru smíðaðar)."""
    m = MY.set_index('sha256')
    V['mynd_lykill'] = V.mynd_sha256.map(m.lykill)
    V['mynd_breidd'] = V.mynd_sha256.map(m.breidd)
    V['mynd_haed'] = V.mynd_sha256.map(m.haed)
    return V


def md5_df(df):
    return hashlib.md5(df.to_csv(index=False).encode('utf-8')).hexdigest()


def nn(v):
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if v is pd.NaT:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


VCOLS = ['verkefni_id', 'slug', 'heiti', 'heiti_uppruni', 'gotur', 'postnr', 'postheiti', 'sveitarfelag', 'landeignir', 'lat', 'lng',
         'n_einingar', 'n_einingar_hms', 'n_heildareiningar', 'n_seld', 'n_magnseld', 'n_heildarkaup', 'n_leiga', 'n_virkar', 'n_oseldar', 'n_oseldar_oauglystar',
         'n_b0', 'n_b1', 'n_b2', 'n_b3', 'n_b4', 'fyrsta_sala', 'sidasta_sala', 'kr_m2_seld', 'n_kr_m2_seld', 'kr_m2_asett',
         'n_kr_m2_asett', 'n_laekkanir', 'n_laekkad_30', 'stofur', 'byggingaradili', 'byggingaradili_n_augl', 'slod', 'byggar_min', 'byggar_max',
         'sidasta_virkni', 'uppselt', 'mynd_sha256', 'mynd_lykill', 'mynd_lykill_frumrit', 'mynd_breidd', 'mynd_haed', 'mynd_stofa',
         'mynd_dags', 'mynd_listing_id']
ECOLS = ['fastnum', 'verkefni_id', 'heimilisfang', 'merking', 'einflm', 'fjherb', 'byggar', 'byggingarstig', 'innan_skilgr',
         'heildareining', 'n_undireiningar', 'stada', 'sala_dags', 'kaupverd', 'kr_m2', 'asett_verd', 'asett_flm', 'n_laekkanir',
         'augl_id', 'augl_endursala', 'augl_flokkur', 'laekkun_dags', 'laekkun_fra', 'laekkun_til', 'laekkun_flokkur', 'laekkad_30']


def skrifa(c, V, E, D, auk, hofst):
    cur = c.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    cur.execute("SET LOCAL lock_timeout = '10s'")
    cur.execute("SET LOCAL statement_timeout = '120s'")
    cur.execute("""insert into semantic.nybygging_keyrslur (utgafa, skilgreining, hofst, sala_fra, data_through, listings_snapshot,
                     n_einingar_skilgr, n_hopar, n_verkefni, n_uppselt, n_einingar, n_seld, n_magnseld, n_virkar,
                     n_slodir_stadfestar, n_sameinad_um_slod, md5_verkefni, md5_einingar)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning keyrsla_id""",
                (UTGAFA, SKILGREINING, hofst, SALA_FRA, D['data_through'], D['snap'], D['n_skilgr_land'], auk['n_hopar'],
                 len(V), int(V.uppselt.sum()), int(V.n_einingar.sum()), int(V.n_seld.sum()), int(V.n_magnseld.sum()),
                 int(V.n_virkar.sum()), len(D['SL']), auk['n_sameinad'], md5_df(V[VCOLS]), md5_df(E[ECOLS])))
    kid = cur.fetchone()[0]
    cur.execute("delete from semantic.nybygging_verkefni where utgafa = %s", (UTGAFA,))
    vr = [[UTGAFA] + [json.dumps(r[k], ensure_ascii=False) if k == 'stofur' else nn(r[k]) for k in VCOLS] + [kid]
          for r in V.to_dict('records')]
    execute_values(cur, f"insert into semantic.nybygging_verkefni (utgafa, {', '.join(VCOLS)}, keyrsla_id) values %s", vr,
                   page_size=1000)
    er = [[UTGAFA] + [nn(r[k]) for k in ECOLS] for r in E.to_dict('records')]
    execute_values(cur, f"insert into semantic.nybygging_einingar (utgafa, {', '.join(ECOLS)}) values %s", er, page_size=2000)
    cur.execute("select count(*), coalesce(sum(n_einingar),0), coalesce(sum(n_seld),0) from semantic.nybygging_verkefni where utgafa=%s", (UTGAFA,))
    nv = cur.fetchone()
    cur.execute("select count(*) from semantic.nybygging_einingar where utgafa=%s", (UTGAFA,))
    ne = cur.fetchone()[0]
    assert nv == (len(V), int(V.n_einingar.sum()), int(V.n_seld.sum())) and ne == len(E), (nv, ne, len(V), len(E))
    c.commit()
    return kid, nv, ne


def lesa_slodir(c, D, csv, nei, athugasemd, stadfest_af='Danni'):
    """slodir_ryni.csv → semantic.nybygging_slodir (skipt út í heild, ein færsla). Skilar (n_ja_rada, n_nei_rada, n_csv_ja)."""
    t = pd.read_csv(csv, dtype=str, encoding='utf-8-sig').fillna('')
    t['ákv'] = np.where(t.stadfest.str.strip() != '', t.stadfest.str.strip().str.lower(), t.tillaga.str.strip().str.lower())
    t.loc[t.slod.isin(nei), 'ákv'] = 'nei'
    assert t['ákv'].isin(['já', 'nei']).all(), t[~t['ákv'].isin(['já', 'nei'])]
    ja = utvikka_slodir(sorted(t[t['ákv'] == 'já'].slod.unique()), D)
    # já-slóð sem finnst ekki í texta á Y-landeign fær að minnsta kosti landeign CSV-raðarinnar
    vantar = t[(t['ákv'] == 'já') & ~t.slod.isin(ja.slod)]
    ja = pd.concat([ja, pd.DataFrame(dict(landeign_nr=vantar.verkefni_id, slod=vantar.slod))]).drop_duplicates()
    neir = t[t['ákv'] == 'nei'][['verkefni_id', 'slod']].rename(columns=dict(verkefni_id='landeign_nr')).drop_duplicates()
    neir = neir[~neir.set_index(['landeign_nr', 'slod']).index.isin(ja.set_index(['landeign_nr', 'slod']).index)]
    rows = ([(r.landeign_nr, r.slod.lower(), True, stadfest_af, dt.date.today(), athugasemd) for r in ja.itertuples()]
            + [(r.landeign_nr, r.slod.lower(), False, stadfest_af, dt.date.today(), athugasemd) for r in neir.itertuples()])
    cur = c.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    cur.execute("SET LOCAL lock_timeout = '10s'")
    cur.execute("SET LOCAL statement_timeout = '120s'")
    cur.execute("delete from semantic.nybygging_slodir")
    execute_values(cur, "insert into semantic.nybygging_slodir (landeign_nr, slod, stadfest, stadfest_af, stadfest_dags, athugasemd) values %s",
                   rows, page_size=1000)
    cur.execute("select count(*) filter (where stadfest), count(*) filter (where not stadfest) from semantic.nybygging_slodir")
    n = cur.fetchone()
    assert n == (len(ja), len(neir)), (n, len(ja), len(neir))
    c.commit()
    return len(ja), len(neir), int((t['ákv'] == 'já').sum()), int((t['ákv'] == 'nei').sum())


def revalidate():
    """Ógildir merkið `nybyggingar` í verdmat-ai (sama mynstur og cc188_verdvakt_refresh.revalidate)."""
    url = os.environ.get('NYBYGGINGAR_ENDURNYJA_URL', 'https://www.verdmat.ai/api/nybyggingar/endurnyja')
    lykill = os.environ.get('ENDURNYJA_LYKILL')
    if not lykill:
        print('revalidate SLEPPT: ENDURNYJA_LYKILL ekki í umhverfi'); return
    req = urllib.request.Request(url, data=b'{}', method='POST',
                                 headers={'content-type': 'application/json', 'x-endurnyja-lykill': lykill})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(f"revalidate: HTTP {r.status} {r.read(200).decode('utf-8', 'replace')}")
    except Exception as e:  # noqa: BLE001 — síðan endurnýjast á TTL
        print(f'revalidate FÉLL (síðan endurnýjast á TTL): {type(e).__name__} {getattr(e, "code", "")}')


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--dryrun', action='store_true'); g.add_argument('--skrifa', action='store_true')
    g.add_argument('--lesa-slodir', metavar='CSV')
    ap.add_argument('--nei', default='', help='slóðir (komma) sem Danni hafnaði þvert á tillögu')
    ap.add_argument('--athugasemd', default=None)
    ap.add_argument('--ut', default=r'D:\_audit\cc224_nybyggingar\keyrsla')
    ap.add_argument('--slodir-tillaga')
    ap.add_argument('--revalidate', action='store_true', help='POST á /api/nybyggingar/endurnyja eftir --skrifa')
    ap.add_argument('--hlada-myndir', metavar='REMOTE', default=os.environ.get('NYBYGGINGAR_MYNDA_REMOTE'),
                    help='rclone-áfangi opinbers myndahýsils (sjálfgefið NYBYGGINGAR_MYNDA_REMOTE; ekkert = ekki hlaðið)')
    a = ap.parse_args()
    if a.lesa_slodir:
        c = tengja()
        try:
            D = lesa(c)
            nei = [x.strip().lower() for x in a.nei.split(',') if x.strip()]
            r = lesa_slodir(c, D, a.lesa_slodir, nei, a.athugasemd)
            print(f"[OK] nybygging_slodir: {r[0]} já-raðir (landeign × slóð) úr {r[2]} já-verkefnum · {r[1]} nei-raðir úr {r[3]} nei-verkefnum")
            return 0
        finally:
            c.close()
    if a.slodir_tillaga and a.skrifa:
        print('[STOPP] --slodir-tillaga er aðeins spá (--dryrun)'); return 3
    hofst = dt.datetime.now(dt.timezone.utc)
    ut = Path(a.ut); ut.mkdir(parents=True, exist_ok=True)
    c = tengja()
    try:
        D = lesa(c)
        if a.slodir_tillaga:
            t = pd.read_csv(a.slodir_tillaga, dtype=str, encoding='utf-8-sig')
            t = t[t.tillaga == 'já']
            D['SL'] = utvikka_slodir(t.slod.unique(), D)
        V, E, auk = reikna(D)
        n_nyjar = n_hladid = 0
        MY = D['MY']
        if a.skrifa:
            MY, n_nyjar, n_hladid = smida_myndir(c, V, MY, a.hlada_myndir)
        V = mynd_i_verkefni(V, MY)
        V.to_csv(ut / 'verkefni.csv', index=False, encoding='utf-8-sig')
        E.to_csv(ut / 'einingar.csv', index=False, encoding='utf-8-sig')
        U = auk['U']
        lin = [f"útgáfa {UTGAFA} | {'SPÁ m/ slóðatillögum' if a.slodir_tillaga else 'staðfestar slóðir: ' + str(len(D['SL']))}",
               f"skilgreining: {SKILGREINING}",
               f"data_through {D['data_through']} | listings_snapshot {D['snap']}",
               f"íbúðir innan skilgreiningar (landið): {D['n_skilgr_land']}",
               f"einingar í Y-mengi (á landeign): {len(U)} | þar af innan skilgr. {int(U.innan_skilgr.sum())} | byggðar ≥{BYGGAR_Y} utan skilgr. {int((~U.innan_skilgr).sum())}",
               f"   innan skilgr. en byggar < {BYGGAR_Y} (FULLBUID=0 eða B0–B3): {int((U.innan_skilgr & ~(U.by >= BYGGAR_Y)).sum())}",
               f"verkefnahópar {auk['n_hopar']} | á gólfi {len(V)} | uppselt {int(V.uppselt.sum())} | sameinað um slóð {auk['n_sameinad']}",
               f"virk (n_virkar>0) {int((V.n_virkar > 0).sum())} | óvirk {int((V.n_virkar == 0).sum())} = uppselt {int(V.uppselt.sum())}"
               f" + ekki auglýst {int(((V.n_virkar == 0) & ~V.uppselt.astype(bool)).sum())}",
               f"forsíðumynd valin {int(V.mynd_sha256.notna().sum())}/{len(V)} | smíðuð (720 px WebP) {int(V.mynd_lykill.notna().sum())}"
               f" | nýjar í þessari keyrslu {n_nyjar} | hlaðnar á hýsil {n_hladid}",
               f"staða eininga: " + ' · '.join(f"{k} {n}" for k, n in E.stada.value_counts().items())
               + f" | heildarkaup (D2′) Σ undireininga {int(V.n_heildarkaup.sum())} í {int((V.n_heildarkaup > 0).sum())} verkefnum"
               + f" | ΣX {int(V.n_seld.sum())}",
               f"einingar m/ virka mbl-auglýsingu {int(E.augl_id.notna().sum())} | flokkar "
               + ' · '.join(f"{k} {n}" for k, n in E.augl_flokkur.value_counts().items()),
               f"óskipt (HMS) {int(E.heildareining.sum())} fastnr., Σ undireininga {int(E[E.heildareining].n_undireiningar.sum())}"
               f" | byggár-kandídatar {auk['b_kandidatar']}: tengd {auk['b_tengd']} (hús {auk['b_sama_hus']}, pakki {auk['b_sami_pakki']})"
               f", eldri eign stöðvuð {auk['b_eldri']} ({100 * auk['b_eldri'] / max(1, auk['b_tengd']):.1f} %), inn {auk['b_inn']}"
               f", án viðmiðs {auk['b_an_vidmids']} | n_leiga Σ {int(V.n_leiga.sum())} í {int((V.n_leiga > 0).sum())} verkefnum"]
        for l in lin:
            print(l)
        (ut / 'samantekt.txt').write_text('\n'.join(lin) + '\n', encoding='utf-8')
        auk['b_K'].to_csv(ut / 'byggar_kandidatar.csv', index=False, encoding='utf-8')
        if a.skrifa:
            kid, nv, ne = skrifa(c, V, E, D, auk, hofst)
            print(f"[OK] skrifað keyrsla_id={kid}: verkefni {nv[0]} (ΣY {nv[1]}, ΣX {nv[2]}), einingar {ne}")
            if a.revalidate:
                revalidate()
        return 0
    finally:
        c.close()


if __name__ == '__main__':
    sys.exit(main())
