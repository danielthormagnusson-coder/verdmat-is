"""rettindavakt.py — cc350 (B1.3 cc347): hvað mega opnu hlutverkin anon og authenticated í gagnagrunninum?

Tilefni (D:/_audit/cc347_heilsutekk/SKIL_CC347.md B1): næturflipp last_listing_text gaf anon lesrétt aftur
18.11.2026 eftir lokun cc345b, ÞEGJANDI — advisors sáu það ekki (taflan hafði stefnu). Vaktin mælir réttindin
sjálf, á hverjum degi, og ber saman við LEYFÐA mengið. Aðeins lestur (pg_catalog + has_*_privilege).

Regla (Danni/arkitekt 19.11.2026): anon og authenticated mega AÐEINS
  · lesa (SELECT) semantic.fasteignasala_manudur / _nefnarar / _nyb_stadir, og
  · nota PostGIS-hlutina (hlutir í eigu viðbótarinnar postgis: spatial_ref_sys, geometry_columns, geography_columns
    og föll hennar).
  Sama fyrir EXECUTE á föllum. Allt annað → FALL (VAKT-VIDVORUN í status-loggi og vaktarpósti).

Umfang: öll skemu nema kerfisskemu Postgres og Supabase-skemu sem vettvangurinn stýrir sjálfur (auth, storage,
realtime, extensions …; sjá VETTVANGUR) — ný app-skemu falla því sjálfkrafa undir vaktina. Hlutur telst opinn ef
hlutverkið hefur USAGE á skemanu OG eitthvert réttindi á hlutnum (tafla/dálkur: SELECT/INSERT/UPDATE/DELETE/TRUNCATE;
fall: EXECUTE). Fall sem skilar `trigger` er ekki hægt að kalla beint (hvorki SQL né PostgREST) og er ekki talið.
Föll viðbótarinnar pg_trgm (similarity, gin-/gist-stoðföll; engin gögn) eru leyfð með PostGIS.

ÞEKKT (cc350, BÍÐUR ÁKVÖRÐUNAR DANNA): authenticated hefur 19.11.2026 réttindi á 12 hlutum utan reglunnar — eigin
raðir notenda (pro_users, saved_* ×4, property_attributes; RLS) + scraper.listings_canonical og 5 v_*-sýnir (cc345 §C2)
+ EXECUTE á public.greining_eignar (invoker). Nýskráning er lokuð. Þau eru í THEKKT svo vaktin hrópi ekki daglega á
þekkt ástand (cc337: varanlegt VAKT drekkir raunviðvörunum); hvert NÝTT réttindi á þeim, eða nýr hlutur, er FALL.
Til að framfylgja reglunni bókstaflega: tæma THEKKT (eða REVOKE á hlutunum).

Úttak: ein lína per fráviki + `RETTINDAVAKT: OK|FALL (n)|MÆLING MISTÓKST (...)`.
rc 0 OK · 1 FALL · 3 mæling mistókst (telst ekki OK).

Notkun:  python scripts/rettindavakt.py [--dbconfig SLÓÐ] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HLUTVERK = ("anon", "authenticated")
VETTVANGUR = (
    "pg_catalog", "information_schema", "pg_toast", "auth", "storage", "realtime", "_realtime", "extensions",
    "graphql", "graphql_public", "vault", "net", "supabase_functions", "supabase_migrations", "pgbouncer", "cron",
    "pgsodium", "pgsodium_masks", "topology",
)
LEYFDAR_VIDBAETUR = {"postgis"}           # allir hlutir viðbótarinnar (töflur/sýnir og föll)
LEYFDAR_FALLAVIDBAETUR = {"postgis", "pg_trgm"}
LEYFT_LES = {"semantic.fasteignasala_manudur", "semantic.fasteignasala_nefnarar", "semantic.fasteignasala_nyb_stadir"}
# Þekkt 19.11.2026 (sjá docstring) — (hlutverk, hlutur) → réttindi sem mæld voru. Meira en þetta = FALL.
THEKKT = {
    ("authenticated", "public.pro_users"): "r",
    ("authenticated", "public.property_attributes"): "r",
    ("authenticated", "public.saved_dashboards"): "rad",
    ("authenticated", "public.saved_properties"): "rawdD",
    ("authenticated", "public.saved_searches"): "rawdD",
    ("authenticated", "public.saved_valuations"): "rawdD",
    ("authenticated", "scraper.listings_canonical"): "r",
    ("authenticated", "scraper.v_commercial_listings"): "r",
    ("authenticated", "scraper.v_listings_combined"): "r",
    ("authenticated", "scraper.v_plot_listings"): "r",
    ("authenticated", "scraper.v_residential_rent_listings"): "r",
    ("authenticated", "scraper.v_residential_sale_listings"): "r",
    ("authenticated", "fall:public.greining_eignar"): "x",
}
HEITI_RETTINDA = {"r": "lesa", "a": "bæta við", "w": "breyta", "d": "eyða", "D": "tæma", "x": "keyra"}

SQL_TOFLUR = """
select r.rol, n.nspname || '.' || c.relname,
       concat_ws('',
         case when has_table_privilege(r.rol, c.oid, 'SELECT') or has_any_column_privilege(r.rol, c.oid, 'SELECT') then 'r' end,
         case when has_table_privilege(r.rol, c.oid, 'INSERT') or has_any_column_privilege(r.rol, c.oid, 'INSERT') then 'a' end,
         case when has_table_privilege(r.rol, c.oid, 'UPDATE') or has_any_column_privilege(r.rol, c.oid, 'UPDATE') then 'w' end,
         case when has_table_privilege(r.rol, c.oid, 'DELETE') then 'd' end,
         case when has_table_privilege(r.rol, c.oid, 'TRUNCATE') then 'D' end),
       (select e.extname from pg_depend d join pg_extension e on e.oid = d.refobjid
         where d.classid = 'pg_class'::regclass and d.objid = c.oid and d.deptype = 'e' limit 1)
  from unnest(%(hlutverk)s::text[]) r(rol)
  cross join pg_class c join pg_namespace n on n.oid = c.relnamespace
 where c.relkind in ('r', 'v', 'm', 'p', 'f')
   and n.nspname <> all(%(vettvangur)s::text[]) and n.nspname not like 'pg\\_temp%%' and n.nspname not like 'pg\\_toast\\_temp%%'
   and has_schema_privilege(r.rol, n.oid, 'USAGE')
   and (has_table_privilege(r.rol, c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')
        or has_any_column_privilege(r.rol, c.oid, 'SELECT,INSERT,UPDATE'))
"""
SQL_FOLL = """
select r.rol, 'fall:' || n.nspname || '.' || p.proname, p.prosecdef,
       (select e.extname from pg_depend d join pg_extension e on e.oid = d.refobjid
         where d.classid = 'pg_proc'::regclass and d.objid = p.oid and d.deptype = 'e' limit 1)
  from unnest(%(hlutverk)s::text[]) r(rol)
  cross join pg_proc p join pg_namespace n on n.oid = p.pronamespace
 where n.nspname <> all(%(vettvangur)s::text[]) and n.nspname not like 'pg\\_temp%%'
   and p.prokind in ('f', 'p', 'a', 'w') and p.prorettype <> 'trigger'::regtype
   and has_schema_privilege(r.rol, n.oid, 'USAGE')
   and has_function_privilege(r.rol, p.oid, 'EXECUTE')
"""


def meta(toflur, foll):
    """Hrein regla. toflur = [(hlutverk, hlutur, réttindi, viðbót|None)], foll = [(hlutverk, 'fall:…', definer, viðbót|None)].
    Skilar (frávik, þekkt): frávik = [(hlutverk, hlutur, réttindi umfram, skýring)], þekkt = fjöldi þekktra sem standast."""
    fravik, thekkt = [], 0
    for rol, hlutur, rett, ext in toflur:
        if ext in LEYFDAR_VIDBAETUR:
            continue
        leyft = "r" if hlutur in LEYFT_LES else THEKKT.get((rol, hlutur), "")
        umfram = "".join(x for x in rett if x not in leyft)
        if umfram:
            fravik.append((rol, hlutur, umfram, "nýtt" if (rol, hlutur) not in THEKKT else "meira en þekkt"))
        elif (rol, hlutur) in THEKKT:
            thekkt += 1
    # föll: eitt fall getur haft mörg yfirhleðslur — dæmt per nafn
    sed = set()
    for rol, hlutur, definer, ext in foll:
        if ext in LEYFDAR_FALLAVIDBAETUR or (rol, hlutur) in sed:
            continue
        sed.add((rol, hlutur))
        if (rol, hlutur) in THEKKT:
            thekkt += 1
            continue
        fravik.append((rol, hlutur, "x", "SECURITY DEFINER" if definer else "nýtt"))
    fravik.sort()
    return fravik, thekkt


def lysing(rol, hlutur, umfram, skyring):
    """Ein lína á mannamáli um eitt frávik."""
    hver = "Opni lykillinn (anon)" if rol == "anon" else "Innskráður notandi (authenticated)"
    hvad = ", ".join(HEITI_RETTINDA.get(x, x) for x in umfram)
    if hlutur.startswith("fall:"):
        return f"{hver} getur keyrt fallið {hlutur[5:]} ({skyring})."
    return f"{hver} má {hvad} í {hlutur} ({skyring})."


def lesa_db(url):
    import psycopg2

    c = psycopg2.connect(url, connect_timeout=15)
    try:
        c.rollback()
        cur = c.cursor()
        cur.execute("SET TRANSACTION READ ONLY")
        cur.execute("SET LOCAL statement_timeout = '30s'")
        cur.execute("SET LOCAL lock_timeout = '5s'")
        p = {"hlutverk": list(HLUTVERK), "vettvangur": list(VETTVANGUR)}
        cur.execute(SQL_TOFLUR, p)
        toflur = cur.fetchall()
        cur.execute(SQL_FOLL, p)
        foll = cur.fetchall()
        return toflur, foll
    finally:
        c.rollback()
        c.close()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--dbconfig", default=r"D:\verdmat-is\.dbconfig")
    ap.add_argument("--json", action="store_true", help="hrá mæling sem JSON (fyrir próf)")
    a = ap.parse_args()
    try:
        toflur, foll = lesa_db(Path(a.dbconfig).read_text(encoding="utf-8-sig").strip())
    except Exception as exc:  # engin tengistrengur/lykill í úttak
        print("RETTINDAVAKT: MÆLING MISTÓKST (%s)" % type(exc).__name__)
        return 3
    if a.json:
        print(json.dumps({"toflur": toflur, "foll": foll}, ensure_ascii=False))
    fravik, thekkt = meta(toflur, foll)
    for f in fravik:
        print("R " + lysing(*f))
    nleyft = sum(1 for r in toflur if r[1] in LEYFT_LES)
    print(f"RETTINDAVAKT: {'OK' if not fravik else 'FALL (%d)' % len(fravik)} · leyft {nleyft} · þekkt {thekkt} · "
          f"hlutir mældir {len(toflur)} · föll mæld {len(foll)}")
    return 1 if fravik else 0


if __name__ == "__main__":
    sys.exit(main())
