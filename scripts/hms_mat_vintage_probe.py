"""hms_mat_vintage_probe.py — cc82 FULLMÆLING á árgerð fasteignamats (READ-ONLY).

SPURNINGIN: `properties.fasteignamat` í Supabase — hve margar raðir bera ELDRI
árgerð en HMS-safnið á diski geymir nú þegar?

BAKGRUNNUR (FASTINN_SAMANBURDUR_CC82 §3.1): fastinn.is birtir fyrir 2013952
138.100.000 sem „Fasteignamat 2026" og 121.450.000 sem „Fasteignamat 2025".
HMS-safnið (`D:\\HMS_jonas\\hms_archive_staging.db`, sótt 03.–05.06.2026,
546.957 fastnúmer sótt / 232.817 til) ber BÁÐAR tölurnar í sitthvorum reit:
  · `fasteignamat`            = 138.100  → svarar til „2026" hjá fastinn
  · `fasteignamat_nuverandi`  = 121.450  → svarar til „2025" hjá fastinn
  · `fasteignamat_naesta_ar`  = 146.500  → hvorugt, næsta ár
DB-in ber 121.450 fyrir þessa eign. 582-raða forkönnun benti til að ~20% safnsins
væru á eldri reitnum. Þessi skrift mælir ALLT safnið í stað úrtaks.

READ-ONLY: eina skrifið er `CREATE TEMP TABLE` sem hverfur með tengingunni.
Engin varanleg tafla, enginn UPDATE, engin DDL á varanlegu skema.

⚠ MÖRK: árgerðamerkingin sjálf (hvor reiturinn er gildandi álagningarstofn) er
EKKI sönnuð hér — hún hvílir á framsetningu fastinn.is á EINNI eign. Skriftin
mælir MISMUNINN og dreifingu hans; hún dæmir ekki hvor reiturinn er réttur.

CLI:
  python scripts/hms_mat_vintage_probe.py            # mælir og prentar
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
HMS_ARCHIVE = Path(r"D:\HMS_jonas\hms_archive_staging.db")

REITIR = ("fasteignamat", "fasteignamat_nuverandi", "fasteignamat_naesta_ar",
          "lhlmat", "lhlmat_naesta_ar", "brunabotamat", "land_lmat")


def lesa_safn(log=print):
    """[(fastnum, *REITIR)] úr HMS-safninu. Aðeins fastnúmer sem eru til í HMS."""
    sq = sqlite3.connect(f"file:{HMS_ARCHIVE}?mode=ro", uri=True)
    ut, n = [], 0
    for fastnum, blob in sq.execute(
            "SELECT fastnum, fasteign_data FROM hms_fasteign "
            "WHERE exists_in_hms = 1 AND fasteign_data IS NOT NULL"):
        try:
            d = json.loads(blob)
        except (TypeError, ValueError):
            continue
        n += 1
        rad = [int(fastnum)]
        for r in REITIR:
            v = d.get(r)
            try:
                rad.append(float(v) if v is not None else None)
            except (TypeError, ValueError):
                rad.append(None)
        ut.append(rad)
    sq.close()
    log(f"  HMS-safn: {len(ut)} raðir lesnar (af {n} læsilegum)")
    return ut


SQL_MAELING = """
SELECT
  count(*)                                                              AS n_join,
  count(*) FILTER (WHERE p.fasteignamat IS NOT NULL)                    AS n_db_mat,
  count(*) FILTER (WHERE h.mat IS NOT NULL)                             AS n_hms_mat,
  count(*) FILTER (WHERE p.fasteignamat = h.mat)                        AS eq_yngri,
  count(*) FILTER (WHERE p.fasteignamat = h.nuv)                        AS eq_eldri,
  count(*) FILTER (WHERE p.fasteignamat = h.mat AND h.mat = h.nuv)      AS eq_baedi,
  count(*) FILTER (WHERE p.fasteignamat IS DISTINCT FROM h.mat
                     AND p.fasteignamat IS DISTINCT FROM h.nuv)         AS eq_hvorugt,
  count(*) FILTER (WHERE h.mat IS DISTINCT FROM h.nuv)                  AS reitir_olikir,
  -- STRANGA TALAN: DB ber eldri reitinn OG reitirnir eru raunverulega ólíkir.
  -- Raðir þar sem reitirnir eru eins geta ekki verið „á eldri árgerð" — að
  -- telja þær með væri sama tegund af ofmati og NaN-sem-miss.
  count(*) FILTER (WHERE p.fasteignamat = h.nuv
                     AND h.mat IS DISTINCT FROM h.nuv)                  AS eldri_strangt,
  round(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY h.mat / nullif(h.nuv, 0))::numeric, 4)                 AS midgildi_mat_nuv,
  round(percentile_cont(0.5) WITHIN GROUP (
        ORDER BY h.mat / nullif(p.fasteignamat, 0))::numeric, 4)        AS midgildi_mat_db,
  count(*) FILTER (WHERE h.lodmat IS NOT NULL AND h.lodmat > 0)         AS hms_lodmat,
  count(*) FILTER (WHERE h.naesta IS NOT NULL AND h.naesta > 0)         AS hms_naesta
FROM hms_tmp h JOIN public.properties p USING (fastnum)
"""

SQL_EFTIR_SVF = """
SELECT p.sveitarfelag,
       count(*)                                        AS n,
       count(*) FILTER (WHERE p.fasteignamat = h.nuv
                          AND h.mat IS DISTINCT FROM h.nuv) AS a_eldri
FROM hms_tmp h JOIN public.properties p USING (fastnum)
GROUP BY 1 ORDER BY 3 DESC NULLS LAST LIMIT 8
"""


def main():
    print("=== hms_mat_vintage_probe (cc82, READ-ONLY) ===")
    radir = lesa_safn()
    pg = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    try:
        cur = pg.cursor()
        cur.execute("""
            CREATE TEMP TABLE hms_tmp (
              fastnum bigint PRIMARY KEY, mat numeric, nuv numeric, naesta numeric,
              lodmat numeric, lodmat_naesta numeric, bruna numeric, land_lmat numeric
            ) ON COMMIT PRESERVE ROWS
        """)
        execute_values(cur, "INSERT INTO hms_tmp VALUES %s ON CONFLICT DO NOTHING",
                       radir, page_size=5000)
        cur.execute("SELECT count(*) FROM hms_tmp")
        print(f"  TEMP-tafla: {cur.fetchone()[0]} raðir")

        cur.execute(SQL_MAELING)
        k = [d[0] for d in cur.description]
        m = dict(zip(k, cur.fetchone()))
        n = m["n_join"]
        print(f"\n  NEFNARI: {n} fastnúmer eru BÆÐI í properties og HMS-safninu")
        print(f"    · properties m/fasteignamat: {m['n_db_mat']}")
        print(f"    · HMS m/fasteignamat:        {m['n_hms_mat']}")
        print(f"    · reitirnir tveir ólíkir í HMS: {m['reitir_olikir']} "
              f"({100.0 * m['reitir_olikir'] / max(n, 1):.1f}%)")
        print(f"\n  ÁRGERÐ Í DB (nefnari {n}):")
        for merki, lykill in (("= yngri reit (`fasteignamat`)", "eq_yngri"),
                              ("= eldri reit (`fasteignamat_nuverandi`)", "eq_eldri"),
                              ("= hvorugum", "eq_hvorugt")):
            v = m[lykill]
            print(f"    {merki:<45} {v:>7}  {100.0 * v / max(n, 1):>5.1f}%")
        print(f"    (þar af raðir þar sem reitirnir eru EINS: {m['eq_baedi']} "
              f"— þær teljast í báðum efri línum og eru ekki frávik)")
        print(f"    ► STRANGT á eldri árgerð (DB=eldri OG reitir ólíkir): "
              f"{m['eldri_strangt']}  {100.0 * m['eldri_strangt'] / max(n, 1):.1f}%")
        print(f"\n  MIÐGILDI yngri/eldri í HMS: {m['midgildi_mat_nuv']}")
        print(f"  MIÐGILDI HMS-yngri / DB:    {m['midgildi_mat_db']}")
        print(f"\n  MEÐ Í SÖMU FERÐ (þekja í HMS-safninu, nefnari {n}):")
        print(f"    · lóðarmat (lhlmat, kr):     {m['hms_lodmat']} "
              f"({100.0 * m['hms_lodmat'] / max(n, 1):.1f}%)")
        print(f"    · fasteignamat næsta árs:    {m['hms_naesta']} "
              f"({100.0 * m['hms_naesta'] / max(n, 1):.1f}%)")

        cur.execute(SQL_EFTIR_SVF)
        print("\n  ÁTTA EFSTU SVEITARFÉLÖG eftir fjölda á eldri árgerð:")
        for svf, n_svf, a_eldri in cur.fetchall():
            h = 100.0 * (a_eldri or 0) / max(n_svf, 1)
            print(f"    {(svf or '(vantar)').strip():<28} {a_eldri:>6} / {n_svf:<6} {h:>5.1f}%")
        pg.rollback()
    finally:
        pg.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
