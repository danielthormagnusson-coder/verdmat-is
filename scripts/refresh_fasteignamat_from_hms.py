"""refresh_fasteignamat_from_hms.py — cc82: fasteignamat úr HMS-safni í NÝJA dálka m/árgerð.

ÁKVÖRÐUN EIGANDA 03.08: NÝR DÁLKUR + ÁRGERÐARMERKI, ekki uppfærsla á staðnum.
`public.properties.fasteignamat` er EKKI snert. Rökin: fasteignamat er birt tala
sem notandi getur borið saman við aðrar síður; án árgerðar er hvorki hægt að
útskýra mun né mæla hann síðar, og uppfærsla á staðnum eyðir sögunni.

SKREF 0 ER LOKIÐ (scripts/hms_mat_argerd_skref0.py): árgerðin er SÖNNUÐ innanhúss
með tímaprófi á kaupskrá — 2026-sölur hitta HMS-reitinn `fasteignamat` í 93,9%
tilvika og 2025-sölur hitta `fasteignamat_nuverandi` í 91,4%, með miðgildi
hlutfalls 1,0000 í báðum. Ekkert hér hvílir á framsetningu þriðja aðila.

ÁRGERÐIN ER LEIDD, EKKI HARÐKÓÐUÐ. Fasteignamat tekur gildi 31.12 og gildir
almanaksárið á eftir, svo reiturinn `fasteignamat` ber ALLTAF árgerð þess
almanaksárs sem röðin var sótt á. Þess vegna er árgerðin reiknuð úr `fetched_at`
hverrar raðar en ekki fest sem fastinn 2026 — harðkóðuð árgerð myndi lifa af
næstu endursókn og ljúga þá (sbr. `feedback_hardkodadur_argangur_lifir_flipp`).
⚠ Skriftin stöðvast ef sóknardagar spanna fleiri en eitt ár: þá er 31.12-jaðarinn
inni í safninu og reglan þarf mannlega ákvörðun.

EINING: ÞÚSUND KRÓNUR (138.100 = 138.100.000 kr.), sama og `properties.fasteignamat`
og kaupskrá.

ÞRÍSKIPTINGIN (CLAUDE.md, phase_d1-mynstrið): extract → dryrun (HALT) → apply.
  --dry-run  les, telur, skrifar rollback-SQL á disk, skrifar EKKERT í DB
  --confirm  keyrir uppfærsluna

CLI:
  python scripts/refresh_fasteignamat_from_hms.py            # docstring + exit 0
  python scripts/refresh_fasteignamat_from_hms.py --dry-run
  python scripts/refresh_fasteignamat_from_hms.py --confirm
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
HMS_ARCHIVE = Path(r"D:\HMS_jonas\hms_archive_staging.db")
ROLLBACK = Path(r"D:\cc82_fasteignamat_hms_rollback.sql")
COLS = ("fasteignamat_hms", "fasteignamat_hms_argerd", "fasteignamat_hms_sott")


def extract(log=print):
    """[(fastnum, mat, argerd, sott)] úr HMS-safninu. Árgerð leidd af sóknardegi."""
    sq = sqlite3.connect(f"file:{HMS_ARCHIVE}?mode=ro", uri=True)
    ut, ar_teljari, n_ekkert_mat = [], Counter(), 0
    for fastnum, blob, fetched_at in sq.execute(
            "SELECT fastnum, fasteign_data, fetched_at FROM hms_fasteign "
            "WHERE exists_in_hms = 1 AND fasteign_data IS NOT NULL"):
        try:
            d = json.loads(blob)
        except (TypeError, ValueError):
            continue
        mat = d.get("fasteignamat")
        if mat in (None, 0):
            n_ekkert_mat += 1
            continue
        sott = str(fetched_at)[:10]          # ISO-8601 úr scrape-skriftinni
        argerd = int(sott[:4])
        ar_teljari[argerd] += 1
        ut.append((int(fastnum), float(mat), argerd, sott))
    sq.close()
    log(f"  HMS-safn: {len(ut)} raðir m/fasteignamati ({n_ekkert_mat} án mats, slepptar)")
    log(f"  árgerðir leiddar af sóknardegi: {dict(ar_teljari)}")
    if len(ar_teljari) > 1:
        raise SystemExit(
            "HALT: sóknardagar spanna fleiri en eitt ár — 31.12-jaðarinn er inni í "
            "safninu og árgerðarreglan þarf mannlega ákvörðun. Ekkert skrifað.")
    return ut


def dryrun(pg, radir, log=print):
    cur = pg.cursor()
    cur.execute("CREATE TEMP TABLE nytt (fastnum bigint PRIMARY KEY, mat numeric, "
                "argerd smallint, sott date) ON COMMIT PRESERVE ROWS")
    execute_values(cur, "INSERT INTO nytt VALUES %s ON CONFLICT DO NOTHING",
                   radir, page_size=5000)
    cur.execute("""
        SELECT count(*)                                                   AS n_join,
               count(*) FILTER (WHERE p.fasteignamat_hms IS NOT NULL)     AS thegar_fyllt,
               count(*) FILTER (WHERE p.fasteignamat IS DISTINCT FROM n.mat) AS vikur_fra_gomlu,
               round(percentile_cont(0.5) WITHIN GROUP (
                     ORDER BY n.mat / nullif(p.fasteignamat, 0))::numeric, 4) AS midgildi
          FROM nytt n JOIN public.properties p USING (fastnum)
    """)
    n_join, thegar, vikur, midgildi = cur.fetchone()
    cur.execute("SELECT count(*) FROM nytt n LEFT JOIN public.properties p USING (fastnum) "
                "WHERE p.fastnum IS NULL")
    utan = cur.fetchone()[0]
    log(f"  SNERTIFLÖTUR: {n_join} raðir í properties fá gildi "
        f"({utan} HMS-raðir eiga enga properties-röð og eru sleppt)")
    log(f"  þegar fylltar (endurkeyrsla): {thegar}")
    log(f"  víkja frá núverandi `fasteignamat`: {vikur} "
        f"({100.0 * vikur / max(n_join, 1):.1f}%), miðgildi nýtt/gamalt = {midgildi}")
    ROLLBACK.write_text(
        "-- cc82 rollback — bakfærsla á fasteignamat_hms* (READ: einn UPDATE dugar).\n"
        "-- Dálkarnir voru ALLIR NULL fyrir keyrslu (nýir í migration 20260803140500),\n"
        "-- svo bakfærslan er ekki raðbundin: það er ekkert eldra gildi að endurheimta.\n"
        "-- `properties.fasteignamat` var ALDREI snert og kemur hvergi við sögu hér.\n"
        "BEGIN;\n"
        "SET TRANSACTION READ WRITE;\n"
        "UPDATE public.properties\n"
        "   SET fasteignamat_hms = NULL,\n"
        "       fasteignamat_hms_argerd = NULL,\n"
        "       fasteignamat_hms_sott = NULL;\n"
        "COMMIT;\n", encoding="utf-8")
    log(f"  rollback-SQL skrifað: {ROLLBACK}")
    return n_join


def apply(pg, radir, log=print):
    cur = pg.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    execute_values(cur, """
        UPDATE public.properties p
           SET fasteignamat_hms = v.mat,
               fasteignamat_hms_argerd = v.argerd,
               fasteignamat_hms_sott = v.sott
          FROM (VALUES %s) AS v (fastnum, mat, argerd, sott)
         WHERE p.fastnum = v.fastnum
    """, radir, page_size=2000,
        template="(%s, %s::numeric, %s::smallint, %s::date)")
    pg.commit()
    cur.execute("SELECT count(*) FILTER (WHERE fasteignamat_hms IS NOT NULL), count(*) "
                "FROM public.properties")
    fyllt, alls = cur.fetchone()
    log(f"  ÞEKJA EFTIR: {fyllt}/{alls} = {100.0 * fyllt / max(alls, 1):.1f}% "
        f"(nefnari = allar raðir í properties)")
    cur.execute("SELECT fasteignamat, fasteignamat_hms, fasteignamat_hms_argerd, "
                "fasteignamat_hms_sott FROM public.properties WHERE fastnum = 2013952")
    log(f"  viðmiðunareign 2013952: {cur.fetchone()}")
    pg.rollback()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    a = ap.parse_args()
    if not (a.dry_run or a.confirm):
        print(__doc__)
        return 0
    print("=== refresh_fasteignamat_from_hms (cc82) ===")
    radir = extract()
    pg = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    try:
        dryrun(pg, radir)
        pg.rollback()
        if not a.confirm or a.dry_run:
            print("  --dry-run: engin skrif. HALT.")
            return 0
        apply(pg, radir)
    finally:
        pg.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
