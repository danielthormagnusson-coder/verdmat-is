"""cc224 — /nybyggingar: reiknar semantic.nybygging_verkefni + semantic.nybygging_einingar (útgáfa cc224-v2).

  python scripts/cc224_nybygging_verkefni.py --dryrun [--ut DIR] [--slodir-tillaga CSV]
  python scripts/cc224_nybygging_verkefni.py --skrifa [--ut DIR]
  python scripts/cc224_nybygging_verkefni.py --lesa-slodir CSV [--nei slod,slod] [--athugasemd TEXTI]

--dryrun   reiknar og skrifar verkefni.csv/einingar.csv/samantekt.txt í --ut; ekkert skrifað í gagnagrunn.
--skrifa   sama + skrifar útgáfuna í einni færslu (DELETE útgáfu → INSERT) og eina röð í nybygging_keyrslur.
--slodir-tillaga  (aðeins --dryrun) les slodir_ryni.csv og notar tillaga = já sem staðfest — SPÁ um áhrif
           staðfestingar, aldrei skrifuð.
--lesa-slodir  les slodir_ryni.csv inn í semantic.nybygging_slodir (stadfest-dálkur ef fylltur, annars tillaga;
           --nei snýr tilteknum slóðum í nei). Já-slóð fer á allar landeignir þar sem hún stendur í auglýsingatexta
           (utvikka_slodir); nei-slóð á landeign CSV-raðarinnar. Endurkeyrsla skiptir töflunni út í heild.

Skilgreining (ákvörðun Danna 09.10.2026, SKIL_CC224_1.md §3 + §5 aldursvörn):
  eining innan skilgreiningar = íbúð (regla 7) ∧ ((FULLBUID=0 ∧ (BYGGAR ≥ ár−3 ∨ BYGGAR óskráð)) ∨ BYGGAR ≥ ár−2
                                ∨ (byggingarstig B0–B3 ∧ matsstig 0–6))
  (cc224-v1 dæmdi FULLBUID=0 óháð aldri → 27 gólfverkefni eingöngu úr eldri húsum; v2 = aldursvörn)
  Y = íbúðir á landeignum verkefnisins byggðar ≥ ár−3 eða innan skilgreiningar (eldri hús á sömu lóð ekki talin);
      óskipt fastnúmer (≥3 ólíkar auglýstar stærðir) telur max(1, auglýstar einingar)
  X = einingar með þinglýstum samningi ONOTHAEFUR=0 (regla 2, eingöngu) frá SALA_FRA; magnsala = samningur > 1 fastnr,
      talin í X, merkt, utan kr/m²
  verkefni = landeign; landeignir sameinaðar þar sem STAÐFEST slóð (nybygging_slodir) og gata eru sameiginleg
  gólf: Y ≥ 4 ∧ (X ≥ 1 ∨ virk auglýsing) ∧ ≥ 1 eining innan skilgreiningar
Engin Fable-/API-köll: byggingaraðili með regex.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

sys.stdout.reconfigure(encoding="utf-8")

UTGAFA = "cc224-v2"
SALA_FRA = dt.date(2021, 1, 1)
AR = dt.date.today().year
BYGGAR_SKILGR = AR - 2          # „fullbúin innan tveggja ára"
BYGGAR_Y = AR - 3               # Y: byggð ≥ 2023 (2026)
IBUD = ('Íbúð', 'Íbúð á hæð', 'Íbúð í kjallara', 'Íbúð í risi', 'Einbýlishús', 'Raðhús', 'Parhús')  # regla 7 (hvítlisti)
SKILGREINING = (f"íbúð (regla 7: {', '.join(IBUD)}; ekki sumarhús) ∧ ((FULLBUID=0 ∧ (BYGGAR ≥ {BYGGAR_Y} ∨ BYGGAR óskráð)) ∨ BYGGAR ≥ {BYGGAR_SKILGR} ∨ "
                f"(byggingarstig B0–B3 ∧ matsstig 0–6)); Y = byggð ≥ {BYGGAR_Y} ∨ innan skilgr.; "
                f"X = ONOTHAEFUR=0 frá {SALA_FRA}; magnsala = samningur > 1 fastnr; "
                f"gólf Y ≥ 4 ∧ (X ≥ 1 ∨ virk augl.); sameining = staðfest slóð ∧ sameiginleg gata")
DSN = Path(r"D:\verdmat-is\.dbconfig")

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
HEIMILISFANG = re.compile(r'^(.*?)\s+(\d+)\s*([A-Za-zÁÐÉÍÓÚÝÞÆÖáðéíóúýþæö]?)\b')


def tengja():
    c = psycopg2.connect(DSN.read_text(encoding="utf-8-sig").strip(), connect_timeout=15)
    c.autocommit = False
    return c


def lesa(c):
    cur = c.cursor()
    cur.execute("SET TRANSACTION READ ONLY")
    cur.execute("SET LOCAL statement_timeout = '600s'")
    # aldursvörn (Danni 09.10): FULLBUID=0 telur aðeins ef byggár ≥ ár−3 eða óskráð (NULL/0)
    skilgr_sql = (f"((p.fullbuid = 0 and coalesce(nullif(p.byggar, 0), 9999) >= {BYGGAR_Y}) or p.byggar >= {BYGGAR_SKILGR} "
                  f"or (p.byggingarstig in ('B0','B1','B2','B3') and p.matsstig ~ '^[0-6]$'))")
    ibud_sql = "(p.tegund_raw = any(%(ibud)s) and coalesce(p.unit_family,'') <> 'summerhouse' and not coalesce(p.deregistered,false))"
    prm = dict(ibud=list(IBUD))
    cur.execute(f"select count(*) from public.properties p where {ibud_sql} and {skilgr_sql}", prm)
    n_skilgr_land = cur.fetchone()[0]
    P = pd.read_sql(f"""
        select p.fastnum, p.heimilisfang, p.postnr, p.postheiti, p.sveitarfelag, p.einflm, p.byggar, p.fjherb, p.fullbuid,
               p.byggingarstig, p.matsstig, p.landeign_nr, p.lat, p.lng,
               (select m->>'merking' from jsonb_array_elements(case when jsonb_typeof(p.matseiningar)='array'
                        then p.matseiningar else '[]'::jsonb end) m where (m->>'fastnum')::bigint = p.fastnum limit 1) merking,
               coalesce({skilgr_sql}, false) innan_skilgr
          from public.properties p
         where {ibud_sql} and p.landeign_nr is not null and ({skilgr_sql} or p.byggar >= {BYGGAR_Y})""", c, params=prm)
    fn = [int(x) for x in P.fastnum]
    S = pd.read_sql("""
        with s as (select id, fastnum, thinglystdags, kaupverd_nominal, einflm_at_sale, onothaefur, faerslunumer
                     from public.sales_history where fastnum = any(%(fn)s) and thinglystdags >= %(fra)s)
        select s.*, case when s.faerslunumer is null then 1 else
                    (select count(distinct h.fastnum) from public.sales_history h where h.faerslunumer = s.faerslunumer) end nf
          from s""", c, params=dict(fn=fn, fra=SALA_FRA))
    L = pd.read_sql("""
        select l.listing_id, l.source, l.fastnum, l.price_amount, l.is_price_on_request, l.size_sqm, l.rooms, l.addr_text,
               l.lysing, l.first_seen_at, l.agency_name, l.agency_source_id,
               exists (select 1 from scraper.v_eign_virk_auglysing v where v.listing_id = l.listing_id) virk
          from scraper.listings l
         where l.tenure = 'sale' and l.category = 'residential' and l.fastnum = any(%(fn)s)""", c, params=dict(fn=fn))
    VV = pd.read_sql("""
        select listing_id, fastnum, stefna, nytt_verd, nytt_sast from semantic.v_verdvakt_breytingar_v2
         where fastnum = any(%(fn)s) and not coalesce(grunsamleg,false) and not coalesce(grunur_villa,false)""",
                     c, params=dict(fn=fn))
    VM = pd.read_sql("select sala_id, lykill, birtingarheiti from scraper.fasteignasala_vorumerki", c)
    SL = pd.read_sql("select landeign_nr, slod from semantic.nybygging_slodir where stadfest order by landeign_nr, slod", c)
    cur.execute("select max(thinglystdags) from public.sales_history"); data_through = cur.fetchone()[0]
    cur.execute("select max(last_seen_at) from scraper.listings where tenure='sale'"); snap = cur.fetchone()[0]
    c.rollback()
    return dict(P=P, S=S, L=L, VV=VV, VM=VM, SL=SL, n_skilgr_land=n_skilgr_land, data_through=data_through, snap=snap)


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


def reikna(D):
    P, S, L, VV, VM = D['P'], D['S'].copy(), D['L'].copy(), D['VV'], D['VM']
    U = P.copy()
    U['fastnum'] = U.fastnum.astype('int64')
    U['by'] = pd.to_numeric(U.byggar, errors='coerce').where(lambda x: x > 0)     # byggar 0 = óskráð
    U['sveitarfelag'] = U.sveitarfelag.str.strip()
    L['fastnum'] = L.fastnum.astype('int64')
    L['sz'] = pd.to_numeric(L.size_sqm, errors='coerce').round(0)
    L['rm'] = pd.to_numeric(L.rooms, errors='coerce')

    # óskipt fastnúmer (bygging fyrir eignaskiptingu): ≥3 ólíkar auglýstar stærðir OG HMS-flatarmál ≥ 2 × miðgildi
    # auglýstrar stærðar (annars er þetta ein íbúð auglýst með ólíkum stærðum, t.d. 97/193 m²); Y-framlag =
    # max(1, ólíkar (stærð, herbergi))
    nsz = L.groupby('fastnum').sz.nunique()
    medsz = L[L.sz > 0].groupby('fastnum').sz.median()
    U['heildareining'] = (U.fastnum.map(nsz).fillna(0).ge(3)
                          & (pd.to_numeric(U.einflm, errors='coerce') >= 2 * U.fastnum.map(medsz)))
    nund = L.drop_duplicates(['fastnum', 'sz', 'rm']).groupby('fastnum').size()
    U['n_undireiningar'] = np.where(U.heildareining, np.maximum(1, U.fastnum.map(nund).fillna(1)), 1).astype(int)

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
    L = L[~(L.t0 > L.fastnum.map(U.set_index('fastnum').sala_dags))].copy()

    # virkar auglýsingar — eignarstig (v_eign_virk_auglysing); eining = fastnr, óskipt = (fastnr, stærð, herbergi)
    AV = L[L.virk]
    nvirk = AV.drop_duplicates(['fastnum', 'sz', 'rm']).groupby('fastnum').size()
    U['n_virk'] = np.where(U.heildareining, U.fastnum.map(nvirk).fillna(0), U.fastnum.isin(AV.fastnum).astype(int)).astype(int)
    U['n_virk'] = np.minimum(U.n_virk, U.n_undireiningar)
    av1 = AV[(AV.price_amount >= ASETT_GOLF) & ~AV.is_price_on_request.fillna(False)].sort_values('first_seen_at').groupby('fastnum').last()
    U['asett_verd'] = np.where(U.heildareining, np.nan, U.fastnum.map(av1.price_amount))
    U['asett_flm'] = np.where(U.heildareining, np.nan, U.fastnum.map(av1.size_sqm))

    # Verðvakt v2 — lækkanir (án grunsamlegra/villugruns), afrituð per (fastnr, dags, verð)
    vv = VV.dropna(subset=['fastnum']).copy()
    vv['fastnum'] = vv.fastnum.astype('int64')
    vv['d'] = pd.to_datetime(vv.nytt_sast, utc=True).dt.tz_localize(None).dt.normalize()
    vv = vv.drop_duplicates(['fastnum', 'd', 'nytt_verd', 'stefna'])
    vv = vv[~(vv.d > vv.fastnum.map(U.set_index('fastnum').sala_dags))]
    U['n_laekkanir'] = U.fastnum.map(vv[vv.stefna == 'laekkun'].groupby('fastnum').size()).fillna(0).astype(int)
    U['sidasta_verdbr'] = U.fastnum.map(vv.groupby('fastnum').d.max())
    U['sidasta_ny_augl'] = U.fastnum.map(L.groupby('fastnum').t0.max())

    U['stada'] = np.select([U.seld & ~U.magnsala, U.magnsala, U.n_virk > 0], ['seld', 'magnsala', 'a_solu'], 'oseld')
    U['x'] = np.where(U.seld, U.n_undireiningar, 0)
    U['virk_oseld'] = np.where(U.seld, 0, U.n_virk)

    U['verkefni_id'], n_sameinad = verkefnalykill(U, D['SL'])

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
        if not (Y >= 4 and (X >= 1 or n_virk_any >= 1) and g.innan_skilgr.any()):
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
        rows.append(dict(
            verkefni_id=vid, golf=True, heiti=heiti, heiti_uppruni=uppruni, gotur=gotur or [],
            postnr=int(g.postnr.mode().iloc[0]) if g.postnr.notna().any() else None,
            postheiti=g.postheiti.mode().iloc[0] if g.postheiti.notna().any() else None,
            sveitarfelag=g.sveitarfelag.mode().iloc[0] if g.sveitarfelag.notna().any() else None,
            landeignir=sorted(g.landeign_nr.unique(), key=lambda x: (len(x), x)),
            lat=float(g.lat.median()) if g.lat.notna().any() else None, lng=float(g.lng.median()) if g.lng.notna().any() else None,
            n_einingar=Y, n_einingar_hms=hms_n, n_heildareiningar=int(g.heildareining.sum()),
            n_seld=X, n_magnseld=int(g[g.magnsala].n_undireiningar.sum()),
            n_virkar=int(g.virk_oseld.sum()), n_oseldar=Y - X, n_oseldar_oauglystar=Y - X - int(g.virk_oseld.sum()),
            n_b0=int((~bs.isin(['B1', 'B2', 'B3', 'B4'])).sum()), n_b1=int((bs == 'B1').sum()), n_b2=int((bs == 'B2').sum()),
            n_b3=int((bs == 'B3').sum()), n_b4=int((bs == 'B4').sum()),
            fyrsta_sala=seld_d.min().date() if len(seld_d) else None, sidasta_sala=seld_d.max().date() if len(seld_d) else None,
            kr_m2_seld=int(round(seldar.kr_m2.median())) if len(seldar) else None, n_kr_m2_seld=len(seldar),
            kr_m2_asett=int(round((a.price_amount / a.size_sqm.astype(float)).median())) if len(a) else None, n_kr_m2_asett=len(a),
            n_laekkanir=int(g.n_laekkanir.sum()), stofur=stofur,
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
        asett_verd=E.asett_verd, asett_flm=E.asett_flm, n_laekkanir=E.n_laekkanir))
    E['sala_dags'] = E.sala_dags.where(E.stada.isin(['seld', 'magnsala']))
    E = E.sort_values(['verkefni_id', 'fastnum']).reset_index(drop=True)   # föst röð → endurtekjanlegt md5
    return V, E, dict(n_hopar=n_hopar, n_sameinad=n_sameinad, U=U)


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
         'n_einingar', 'n_einingar_hms', 'n_heildareiningar', 'n_seld', 'n_magnseld', 'n_virkar', 'n_oseldar', 'n_oseldar_oauglystar',
         'n_b0', 'n_b1', 'n_b2', 'n_b3', 'n_b4', 'fyrsta_sala', 'sidasta_sala', 'kr_m2_seld', 'n_kr_m2_seld', 'kr_m2_asett',
         'n_kr_m2_asett', 'n_laekkanir', 'stofur', 'byggingaradili', 'byggingaradili_n_augl', 'slod', 'byggar_min', 'byggar_max',
         'sidasta_virkni', 'uppselt']
ECOLS = ['fastnum', 'verkefni_id', 'heimilisfang', 'merking', 'einflm', 'fjherb', 'byggar', 'byggingarstig', 'innan_skilgr',
         'heildareining', 'n_undireiningar', 'stada', 'sala_dags', 'kaupverd', 'kr_m2', 'asett_verd', 'asett_flm', 'n_laekkanir']


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


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--dryrun', action='store_true'); g.add_argument('--skrifa', action='store_true')
    g.add_argument('--lesa-slodir', metavar='CSV')
    ap.add_argument('--nei', default='', help='slóðir (komma) sem Danni hafnaði þvert á tillögu')
    ap.add_argument('--athugasemd', default=None)
    ap.add_argument('--ut', default=r'D:\_audit\cc224_nybyggingar\keyrsla')
    ap.add_argument('--slodir-tillaga')
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
        V.to_csv(ut / 'verkefni.csv', index=False, encoding='utf-8-sig')
        E.to_csv(ut / 'einingar.csv', index=False, encoding='utf-8-sig')
        U = auk['U']
        lin = [f"útgáfa {UTGAFA} | {'SPÁ m/ slóðatillögum' if a.slodir_tillaga else 'staðfestar slóðir: ' + str(len(D['SL']))}",
               f"skilgreining: {SKILGREINING}",
               f"data_through {D['data_through']} | listings_snapshot {D['snap']}",
               f"íbúðir innan skilgreiningar (landið): {D['n_skilgr_land']}",
               f"einingar í Y-mengi (á landeign): {len(U)} | þar af innan skilgr. {int(U.innan_skilgr.sum())} | byggðar ≥{BYGGAR_Y} utan skilgr. {int((~U.innan_skilgr).sum())}",
               f"   innan skilgr. en byggar < {BYGGAR_Y} (FULLBUID=0 eða B0–B3): {int((U.innan_skilgr & ~(U.by >= BYGGAR_Y)).sum())}",
               f"verkefnahópar {auk['n_hopar']} | á gólfi {len(V)} | uppselt {int(V.uppselt.sum())} | sameinað um slóð {auk['n_sameinad']}"]
        for l in lin:
            print(l)
        (ut / 'samantekt.txt').write_text('\n'.join(lin) + '\n', encoding='utf-8')
        if a.skrifa:
            kid, nv, ne = skrifa(c, V, E, D, auk, hofst)
            print(f"[OK] skrifað keyrsla_id={kid}: verkefni {nv[0]} (ΣY {nv[1]}, ΣX {nv[2]}), einingar {ne}")
        return 0
    finally:
        c.close()


if __name__ == '__main__':
    sys.exit(main())
