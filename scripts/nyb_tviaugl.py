"""cc234: tvíauglýsing NÚ per nýbyggingarverkefni — íbúðir sem eru samtímis auglýstar til sölu og leigu.

Aðferð = D:\\_audit\\cc234_leiguaugl\\s5_tviaugl.py (= cc229 f3_eftirfylgni.py, 16/16 samræmi):
  mbl-sala lifandi NÚ = opin (status active) ∧ fundin lifandi í söluhring (S) eða kortlotu (K) eða birt (first_seen_at)
                        innan NU_GLUGGI_D daga. ALDREI last_seen_at (cc230: sópun skrifar það ekki).
  leiga virk NÚ       = myigloo: status active ∧ séð í síðustu nætursópun (last_seen_at = MAX(fetched_at), traust);
                        mbl-leiga: status active (óvissara; 4 af 57 í cc234).
  n_tviaugl_nu = fastnr. verkefnisins með hvort tveggja.

Leiguaðili (cc234 GO, Danni 11.10): nafn birtist AÐEINS ef
  (a) leigufélag/félag á LEYFT (handstaðfest), eða
  (b) sölustofa: mbl-auglýsandi sem auglýsir líka íbúðir til sölu (agency_source_id), eða myigloo-heiti sem endar á „fasteignasala",
  og hann auglýsir ≥ 50 % af n_tviaugl_nu. Einstaklingar og önnur félög ALDREI.
  myigloo `organization.name` ber persónunafn hjá einstaklingum → heiti er aðeins lesið út ef það stenst (a)/(b); annars aldrei geymt.
  `owner` og `slug` eru aldrei lesin.
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import re
import sqlite3

import pandas as pd

SD = r'D:\verdmat-is\scraper_data'
RAW_MYIGLOO = os.path.join(SD, 'raw_myigloo.db')
NU_GLUGGI_D = 3
LEIGA_FRA = '2021-01-01'                     # = SALA_FRA, sama og n_leiga
HLUTFALL = 0.5
# handstaðfest (cc234 GO): leigufélög + Rann – Íbúðir (Danni 11.10; tenging við Reir verk ÓSTAÐFEST og aldrei birt)
LEYFT = {'Alma íbúðafélag hf.': 'Alma íbúðafélag', 'Leigufélagið Bríet': 'Leigufélagið Bríet', 'Rann - Íbúðir': 'Rann – Íbúðir'}
SOLUSTOFA_MYIGLOO = re.compile(r'\bfasteignasala$', re.I)


def _soluathuganir(sids, E, EA, st):
    """Söluathuganir per mbl-auðkenni — óbreytt úr f3_eftirfylgni.py (cc229) / s5_tviaugl.py (cc234)."""
    rounds = {}
    for f in sorted(glob.glob(os.path.join(SD, 'lifecycle_sale_round_*.json'))):
        ts = os.path.basename(f).split('_')[3].split('.')[0]
        if ts not in rounds or f.endswith('_cardx.json'):
            rounds[ts] = f
    obs = []
    for ts, f in sorted(rounds.items()):
        ids = [str(x[0]) for x in json.load(open(f))]
        cur_round = st['sale'].get('round_file') and os.path.basename(st['sale']['round_file']) == os.path.basename(f)
        n = st['sale']['cursor'] if cur_round else len(ids)
        sweep = f'lifecycle_sweep_mbl_v1_saleround_{ts}'
        Er = EA[EA.sweep == sweep]
        pos = {s: i for i, s in enumerate(ids[:n])}
        bt = Er.assign(b=Er.sid.map(pos) // 16).dropna(subset=['b']).groupby('b').event_at.min().sort_index()
        allb = bt.set_axis(bt.index.astype(int)).reindex(range((n + 15) // 16)).ffill()
        absent = set(E[E.sweep == sweep].sid)
        for i, s in enumerate(ids[:n]):
            if s in sids and pd.notna(allb.iloc[i // 16]):
                obs.append((s, allb.iloc[i // 16], s not in absent))
    for s, t in st.get('card', {}).get('checked', {}).items():
        if str(s) in sids:
            obs.append((str(s), pd.Timestamp(t), True))
    O = pd.DataFrame(obs, columns=['sid', 't', 'fundin'])
    O['t'] = pd.to_datetime(O.t, utc=True)
    return O


def _myigloo_heiti(sids):
    """sid -> birtanlegt heiti (aðeins LEYFT eða sölustofa); aðrir fá None. Nýjasta detail-blað per auðkenni."""
    if not sids:
        return {}
    c = sqlite3.connect(f'file:{RAW_MYIGLOO}?mode=ro', uri=True)
    try:
        ph = ','.join('?' * len(sids))
        rows = c.execute(f"""select f.source_listing_id, b.blob_gz from raw_fetches f join raw_blobs b on b.content_hash = f.content_hash
                             where f.raw_id in (select max(raw_id) from raw_fetches where http_status = 200 and fetch_kind <> 'api_page'
                                                and source_listing_id in ({ph}) group by source_listing_id)""", list(sids)).fetchall()
    finally:
        c.close()
    ut = {}
    for sid, bz in rows:
        try:
            d = json.loads(gzip.decompress(bz))
        except Exception:
            continue
        g = d.get('organization') if isinstance(d, dict) and isinstance(d.get('organization'), dict) else {}
        nm = (g.get('name') or '').strip()
        if nm in LEYFT:
            ut[str(sid)] = LEYFT[nm]
        elif SOLUSTOFA_MYIGLOO.search(nm):
            ut[str(sid)] = nm
    return ut


def reikna_tviaugl(c, E, nu=None):
    """E: einingar (fastnum, verkefni_id). Skilar (P per verkefni_id: n_tviaugl_nu, leiguadili, leiguadili_n; T per fastnr.)."""
    nu = pd.Timestamp.now(tz='UTC') if nu is None else nu
    gluggi = nu - pd.Timedelta(days=NU_GLUGGI_D)
    fn = [int(x) for x in E.fastnum.unique()]
    q = lambda s, p=None: pd.read_sql(s, c, params=p)
    L = q("""select source, source_listing_id sid, fastnum, tenure, status, first_seen_at, last_seen_at, agency_name, agency_source_id
               from scraper.listings
              where fastnum = any(%(f)s) and ((tenure = 'sale' and category = 'residential' and source = 'mbl')
                                           or (tenure = 'rent' and first_seen_at >= %(fra)s))""", dict(f=fn, fra=LEIGA_FRA))
    for col in ('first_seen_at', 'last_seen_at'):
        L[col] = pd.to_datetime(L[col], utc=True)
    S = L[L.tenure == 'sale']; R = L[L.tenure == 'rent'].copy()
    sids = set(S.sid)
    Ev = q("""select source_listing_id sid, event_type, event_at, evidence->>'sweep_id' sweep from scraper.listing_lifecycle_events
              where source = 'mbl' and source_listing_id = any(%(s)s)""", dict(s=list(sids)))
    EA = q("""select source_listing_id sid, event_at, evidence->>'sweep_id' sweep from scraper.listing_lifecycle_events
              where source = 'mbl' and evidence->>'sweep_id' like '%%saleround%%'""")
    for d in (Ev, EA):
        d['event_at'] = pd.to_datetime(d.event_at, utc=True)
    st = json.load(open(os.path.join(SD, 'lifecycle_sweep_state.json'), encoding='utf-8'))
    O = _soluathuganir(sids, Ev, EA, st)
    fundin = O[O.fundin].groupby('sid').t.max()
    S = S.assign(sidast_fundin=[max([x for x in [fundin.get(s), f] if pd.notna(x)]) for s, f in zip(S.sid, S.first_seen_at)])
    sala_nu = set(S[(S.status == 'active') & (S.sidast_fundin >= gluggi)].fastnum.astype('int64'))
    myig_sop = pd.Timestamp(q("select max(last_seen_at) m from scraper.listings where source = 'myigloo'").m.iloc[0])
    R['virk_nu'] = [(st_ == 'active') and (ls >= myig_sop - pd.Timedelta(hours=12) if src == 'myigloo' else True)
                    for st_, ls, src in zip(R.status, R.last_seen_at, R.source)]
    Rv = R[R.virk_nu & R.fastnum.isin(sala_nu)].copy()
    solustofur = set(q("""select distinct agency_source_id from scraper.listings
                          where tenure = 'sale' and agency_source_id is not null""").agency_source_id.astype(int))
    mh = _myigloo_heiti(sorted(set(Rv[Rv.source == 'myigloo'].sid)))
    Rv['heiti'] = [(an if pd.notna(ai) and int(ai) in solustofur else None) if src == 'mbl' else mh.get(str(sid))
                   for src, sid, an, ai in zip(Rv.source, Rv.sid, Rv.agency_name, Rv.agency_source_id)]
    # eitt heiti per fastnr.: birtanlegt heiti nýjustu virku leiguauglýsingar sem hefur slíkt, annars None
    Rv = Rv.sort_values(['fastnum', 'first_seen_at'])
    hpf = Rv.dropna(subset=['heiti']).groupby('fastnum').heiti.last()
    E1 = E[['fastnum', 'verkefni_id']].drop_duplicates('fastnum').copy()
    E1['fastnum'] = E1.fastnum.astype('int64')
    T = E1[E1.fastnum.isin(set(Rv.fastnum.astype('int64')))].copy()
    T['heiti'] = T.fastnum.map(hpf)
    rows = []
    for vid, g in T.groupby('verkefni_id'):
        n = len(g); k = g.heiti.value_counts()
        topp = k[k == k.max()] if len(k) else k
        ok = sorted(h for h, m in topp.items() if m >= HLUTFALL * n)
        rows.append(dict(verkefni_id=vid, n_tviaugl_nu=n, leiguadili=' og '.join(ok) if ok else None,
                         leiguadili_n=int(topp.iloc[0]) if ok else None))
    P = pd.DataFrame(rows, columns=['verkefni_id', 'n_tviaugl_nu', 'leiguadili', 'leiguadili_n'])
    return P, T
