"""rettindavakt_prof.py — cc350: próf réttindavaktar (scripts/rettindavakt.py).

1. Regla (meta) á gervimælingum: leyft/þekkt stenst; nýtt, meira en þekkt og SECURITY DEFINER fellur.
2. --lifandi: FÖLSUN Í GRUNNI í einni færslu sem er ALLTAF bakfærð (ROLLBACK): búin til tafla og
   SECURITY DEFINER-fall í public, SELECT/EXECUTE veitt anon, SÖMU fyrirspurnir og vaktin keyrir → verða að
   falla; síðan ROLLBACK og vaktin keyrð aftur → OK. lock_timeout 5s; enginn lifandi hlutur snertur.
rc 0 = öll próf stóðust.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rettindavakt as rv  # noqa: E402

villur = 0
ok = 0


def athuga(heiti, skilyrdi, nanar=""):
    global villur, ok
    if skilyrdi:
        ok += 1
    else:
        villur += 1
        print(f"FELLUR: {heiti}{' — ' + str(nanar) if nanar else ''}")


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

GRUNNUR_T = [
    ("anon", "semantic.fasteignasala_manudur", "r", None),
    ("anon", "public.spatial_ref_sys", "r", "postgis"),
    ("anon", "public.geometry_columns", "rawdD", "postgis"),
    ("authenticated", "public.saved_searches", "rawdD", None),
    ("authenticated", "scraper.listings_canonical", "r", None),
]
GRUNNUR_F = [
    ("anon", "fall:public.st_estimatedextent", True, "postgis"),
    ("anon", "fall:public.similarity", False, "pg_trgm"),
    ("authenticated", "fall:public.greining_eignar", False, None),
]
fr, th = rv.meta(GRUNNUR_T, GRUNNUR_F)
athuga("grunnstaða stenst", fr == [], fr)
athuga("þekkt talin", th == 3, th)

fr, _ = rv.meta(GRUNNUR_T + [("anon", "public.last_listing_text", "r", None)], GRUNNUR_F)
athuga("anon les nýja töflu → FALL (B1-atvikið)", fr == [("anon", "public.last_listing_text", "r", "nýtt")], fr)
fr, _ = rv.meta(GRUNNUR_T + [("anon", "semantic.fasteignasala_manudur", "ra", None)], GRUNNUR_F)
athuga("skrif á leyfða sýn → FALL", [f[2] for f in fr] == ["a"], fr)
fr, _ = rv.meta(GRUNNUR_T + [("anon", "scraper.listings_canonical", "r", None)], GRUNNUR_F)
athuga("þekkt hjá authenticated er ekki leyft anon", len(fr) == 1 and fr[0][0] == "anon", fr)
fr, _ = rv.meta([("authenticated", "scraper.listings_canonical", "rw", None)], [])
athuga("meira en þekkt → FALL", fr == [("authenticated", "scraper.listings_canonical", "w", "meira en þekkt")], fr)
fr, _ = rv.meta([], [("anon", "fall:scraper.a_solu_talning", True, None), ("anon", "fall:scraper.a_solu_talning", True, None)])
athuga("SECURITY DEFINER-fall opið anon → FALL, einu sinni per nafn", fr == [("anon", "fall:scraper.a_solu_talning", "x", "SECURITY DEFINER")], fr)
fr, _ = rv.meta([("anon", "public.ny_tafla", "r", "pg_trgm")], [])
athuga("tafla úr annarri viðbót en postgis → FALL", len(fr) == 1, fr)
athuga("lýsing á mannamáli", rv.lysing("anon", "public.x", "r", "nýtt") == "Opni lykillinn (anon) má lesa í public.x (nýtt).")

if "--lifandi" in sys.argv:
    import psycopg2

    url = Path(r"D:\verdmat-is\.dbconfig").read_text(encoding="utf-8-sig").strip()
    p = {"hlutverk": list(rv.HLUTVERK), "vettvangur": list(rv.VETTVANGUR)}
    c = psycopg2.connect(url, connect_timeout=15)
    try:
        c.rollback()
        cur = c.cursor()
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("SET LOCAL lock_timeout = '5s'")
        cur.execute("SET LOCAL statement_timeout = '30s'")
        cur.execute("CREATE TABLE public.cc350_rettindaprof (x int)")
        cur.execute("GRANT SELECT ON public.cc350_rettindaprof TO anon")
        cur.execute("CREATE FUNCTION public.cc350_rettindaprof_fall() RETURNS int LANGUAGE sql SECURITY DEFINER AS 'select 1'")
        cur.execute("GRANT EXECUTE ON FUNCTION public.cc350_rettindaprof_fall() TO anon")
        cur.execute(rv.SQL_TOFLUR, p)
        t = cur.fetchall()
        cur.execute(rv.SQL_FOLL, p)
        f = cur.fetchall()
        fr, _ = rv.meta(t, f)
        hlutir = {(x[0], x[1]) for x in fr}
        athuga("fölsun í grunni: tafla opin anon fellur", ("anon", "public.cc350_rettindaprof") in hlutir, fr)
        athuga("fölsun í grunni: definer-fall opið anon fellur", ("anon", "fall:public.cc350_rettindaprof_fall") in hlutir, fr)
        athuga("fölsun í grunni: ekkert annað fellur", len(fr) == 2, fr)
        print("  fölsun: " + " | ".join(rv.lysing(*x) for x in fr))
    finally:
        c.rollback()
        c.close()
    toflur, foll = rv.lesa_db(url)
    fr, th = rv.meta(toflur, foll)
    athuga("eftir ROLLBACK: lifandi staða OK", fr == [], fr)
    athuga("eftir ROLLBACK: prófhlutir horfnir", not any("cc350_rettindaprof" in r[1] for r in toflur + foll))

print(f"rettindavakt_prof: {ok} í lagi, {villur} féllu")
sys.exit(1 if villur else 0)
