#!/usr/bin/env python
"""cc319 (GO Danna 06.11.2026): fleiri eigindi úr keyptum svörum á lýsingu, aðeins sellur sem stóðust óháð blint úrtak.
Engin API-köll: les skema 3 og 101. Skrifar aðeins í public.lysing_vidbot. Aðeins birting: ekkert í verðleiðréttingu (regla 11).
Aldrei „nei". Skrá HMS og skráð gildi ganga fyrir: röð verður ekki til ef virk röð er í property_attributes, og
herbergi ekki ef properties.fjherb er til. Sjálfgefið þurrkeyrsla; --skrifa skrifar. Hliðin eru frosin í lysing_hlid*.py.
"""
import collections, sys
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

sys.path.insert(0, str(Path(__file__).parent))
import lysing_hlid as H1, lysing_hlid2 as H2  # noqa: E402
from lysing_astand import er_nybygging, rammi  # noqa: E402
from lysing_eigindi_nott import rw, skra  # noqa: E402

A, E, R_ = "apartment", "house", "townhouse"
# Sella = (lykill, tegund). Tölur: SKIL_CC319 §1. Sella sem er ekki hér birtist ekki.
EIG_U1 = {("serinngangur", A), ("lofthaed", A), ("lofthaed", E), ("lofthaed", R_), ("arinn", A), ("arinn", E), ("opid_rymi", E), ("opid_rymi", R_),
          ("endaeining", A), ("endaeining", R_), ("heitur_pottur", R_), ("ev_hledsla", A), ("bilskur_staedi", E), ("bilskur_staedi", R_),
          ("thvottahus", A), ("thvottahus", E), ("thvottahus", R_), ("lodarat", E), ("utsyni", A), ("utsyni", E),
          ("herbergi", A), ("herbergi", R_), ("badherbergi", A)}
EIG_U2 = {("golfefni", E), ("golfefni", R_), ("opid_rymi", A)}
AST_U1 = {("badherbergi", A), ("badherbergi", E), ("badherbergi", R_), ("eldhus", R_), ("gluggar", E), ("lagnir", E), ("thak", E)}
AST_U2 = {("lagnir", A)}
AR = {("eldhus", A), ("golfefni", A), ("almennt", A), ("eldhus", E)}
AST_LYKILL = {"badherbergi": "badherbergi_astand", "eldhus": "eldhus_astand", "gluggar": "gluggar_lysing", "lagnir": "lagnir_lysing", "thak": "thak_lysing"}
S3, S101 = 3, 101


def radir(F, S_3, S_101, PA, FJHERB, LA):
    """F = rammi utan nýbygginga. PA = {(fastnum, attr_key)} virkar skráðar raðir. LA = {(fastnum, attr_key)} úr lysing_astand. Hreint fall."""
    ut = []
    for f, r in F.items():
        t, h, tx, dags = r[5], r[3], r[2], r[1].date().isoformat()
        s3, s1 = S_3.get(h), S_101.get(h)
        if s3:
            for k, tt in EIG_U1 | EIG_U2:
                if tt != t or (f, k) in PA or (k == "herbergi" and FJHERB.get(f) is not None):
                    continue
                v = (H2.EIG2[k] if (k, tt) in EIG_U2 else H1.EIG[k])(s3, tx)
                if v:
                    ut.append((f, k, v, h, S3, dags))
        if s1:
            for k, tt in AST_U1 | AST_U2:
                ly = AST_LYKILL[k]
                if tt != t or (f, ly) in PA:
                    continue
                if H2.lagnir(s1, tx) if (k, tt) in AST_U2 else H1.astand(s1, tx, k):
                    ut.append((f, ly, {"stada": "endurnyjad"}, h, S101, dags))
            for k, tt in AR:  # Ártal bætist aðeins við röð sem er þegar á www, aldrei ný röð
                if tt == t and (f, k) in LA and H1.astand(s1, tx, k):
                    ar = H1.ar(s1, tx, k)
                    if ar:
                        ut.append((f, "ar:" + k, {"ar": ar}, h, S101, dags))
    return ut


def lesa(c):
    c.rollback()
    k = c.cursor()
    k.execute("set transaction read only")
    k.execute("set local statement_timeout='180s'")
    R = rammi(k)
    k.execute("select fastnum,fullbuid,byggar,fjherb from public.properties where fastnum=any(%s)", (list(R),))
    P, FJ = {}, {}
    for f, fb, by, fj in k.fetchall():
        P[f], FJ[f] = (fb, by), fj
    F = {f: r for f, r in R.items() if not er_nybygging(P.get(f), r[1].year)}
    k.execute("select lysing_hash,svar from scraper.lysing_eigindi_svar where skema_utgafa=%s", (S3,))
    s3 = dict(k.fetchall())
    k.execute("select lysing_hash,svar from scraper.lysing_eigindi_svar where skema_utgafa=%s", (S101,))
    s1 = dict(k.fetchall())
    k.execute("select fastnum,attr_key from public.property_attributes where superseded_at is null and fastnum=any(%s)", (list(F),))
    PA = set(k.fetchall())
    k.execute("select fastnum,attr_key from public.lysing_astand")
    LA = set(k.fetchall())
    c.rollback()
    return F, s3, s1, PA, FJ, LA


def uppfaera(c, rows):
    q = rw(c)
    q.execute("select count(*) from public.lysing_vidbot")
    nu = q.fetchone()[0]
    if nu >= 200 and len(rows) < 0.6 * nu:
        c.rollback()
        skra(f"viðbót HLIÐ: {len(rows)} raðir, {nu} í töflu; birting óbreytt")
        return None
    q.execute("create temp table n(fastnum bigint,attr_key text,value jsonb,lysing_hash text,skema_utgafa int,source_date date) on commit drop")
    if rows:
        execute_values(q, "insert into n values %s", [(f, k, Json(v), h, s, d) for f, k, v, h, s, d in rows], page_size=1000)
    q.execute("delete from public.lysing_vidbot t where not exists(select 1 from n where n.fastnum=t.fastnum and n.attr_key=t.attr_key)")
    q.execute("""insert into public.lysing_vidbot(fastnum,attr_key,value,lysing_hash,skema_utgafa,source_date) select * from n
      on conflict(fastnum,attr_key) do update set value=excluded.value,lysing_hash=excluded.lysing_hash,
      skema_utgafa=excluded.skema_utgafa,source_date=excluded.source_date,hladid_at=now()""")
    c.commit()
    return len(rows)


def nott(c):
    """Næturhluti á eftir ástandi: engin köll, $0 á sama $2-þaki. Bilun fellir ekki það sem þegar er skrifað."""
    n = uppfaera(c, radir(*lesa(c)))
    skra(f"viðbót nótt: raðir {n}")
    return 0 if n is not None else 4


if __name__ == "__main__":
    _c = psycopg2.connect(Path(r"D:\verdmat-is\.dbconfig").read_text(encoding="utf-8-sig").strip(), connect_timeout=15, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
    _F, *_u = lesa(_c)
    _rows = radir(_F, *_u)
    _n = collections.Counter((_F[x[0]][5], x[1]) for x in _rows)
    for _x in sorted(_n):
        print(*_x, _n[_x])
    print("raðir", len(_rows), "eignir", len({x[0] for x in _rows}), "rammi", len(_F))
    if "--skrifa" in sys.argv:
        print("skrifað", uppfaera(_c, _rows))
