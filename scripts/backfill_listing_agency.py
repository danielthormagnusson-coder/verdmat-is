"""backfill_listing_agency.py — cc82 einskiptis-bakfylling söluaðila í scraper.listings.

HVERS VEGNA ÞETTA ER TIL (og hvers vegna promote-skriftin ein dugar ekki):
`parse_mbl.py` hefur ALLTAF geymt söluaðilann (`agency_json` í
parsed_mbl_{sale,rent}) — hann kom með í mbl-svarinu frá fyrsta degi. Promote-
lagið tók hann bara aldrei með, svo Postgres vissi ekki af honum
(FASTINN_SAMANBURDUR_CC82 §2.12/§3.3: 37.517/38.706 sale = 96,9%,
3.150/3.165 rent = 99,5% lágu ósótt á diski).

`promote_listings_append.py` skrifar NÚ dálkana (cc82-breyting þar), EN hún er
delta-skrift: write-settið er parse-vatnsmerki ∪ unit_key-rek ∪ raðir sem
vantar í DB. Raðir sem eru þegar í `scraper.listings` og hafa ekki breyst
skipta ENGU máli fyrir vatnsmerkið og myndu því aldrei fá söluaðilann.
Þessi skrift lokar því gati EINU SINNI; eftir það heldur promote-leiðin við.
(Að þvinga fulla endurkeyrslu á promote í staðinn væri ~36K raða endurritun =
TOAST/WAL-hrina sem cc11-rótarfixið var einmitt smíðaður til að forðast.)

MÆLIREGLA (feedback_cov_maeling_nan_sem_miss): þekja er alltaf birt með
NEFNARA og nefnarinn er tvískiptur — (a) allar mbl-raðir í scraper.listings,
(b) þær sem eiga sér samsvarandi parsed-röð. Rað án parsed-samsvörunar getur
ALDREI fengið söluaðila; að fela hana í nefnaranum væri þekjulygi.

Pooler er READ-ONLY að sjálfgefnu: fyrsta stök hverrar skriftar-færslu er
`SET TRANSACTION READ WRITE` (locked rule, CLAUDE.md).

CLI:
  python scripts/backfill_listing_agency.py                # docstring + exit 0
  python scripts/backfill_listing_agency.py --dry-run      # mælir ÁN skrifa
  python scripts/backfill_listing_agency.py --confirm      # bakfyllir
"""
from __future__ import annotations

import argparse

import sqlite3
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, str(Path(__file__).resolve().parent))
# EITT HEIMILI KORTLAGNINGARINNAR: parse_agency býr í promote_mbl og er lesin
# BÆÐI héðan og úr promote_listings_append. Afrit hér hefði getað rekið í
# sundur við promote-leiðina — nákvæmlega gildran sem cc71 leysti fyrir
# auglýsingatextann og cc75 fyrir HTML-hreinsunina.
from promote_mbl import parsed_db_path, parse_agency, AGENCY_COLS  # noqa: E402

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
COLS = AGENCY_COLS


def lesa_agency(log=print) -> dict:
    """{source_listing_id (str): {dálkur: gildi}} úr báðum parsed-töflum."""
    sq = sqlite3.connect(f"file:{parsed_db_path()}?mode=ro", uri=True)
    sq.row_factory = sqlite3.Row
    ut, n_raw, n_bilad = {}, 0, 0
    for tafla in ("sale", "rent"):
        q = (f"SELECT source_listing_id, agency_json FROM parsed_mbl_{tafla} "
             f"WHERE agency_json IS NOT NULL ORDER BY parse_id")
        n_tafla = 0
        for r in sq.execute(q):
            n_raw += 1
            rec = parse_agency(r["agency_json"])
            if all(v is None for v in rec.values()):
                n_bilad += 1
                continue
            if any(v is not None for v in rec.values()):
                # ORDER BY parse_id: nýjasta parse-röð eignarinnar vinnur.
                ut[str(r["source_listing_id"])] = rec
                n_tafla += 1
        log(f"  parsed_mbl_{tafla}: {n_tafla} raðir m/söluaðila")
    sq.close()
    log(f"  alls: {len(ut)} auðkenni ({n_raw} lesin, {n_bilad} ólæsileg JSON)")
    return ut


def maela(cur, log=print, merki=""):
    """Þekja söluaðila í scraper.listings — nefnari alltaf birtur."""
    cur.execute("""
        SELECT count(*) AS n_alls,
               count(*) FILTER (WHERE agency_name IS NOT NULL) AS n_nafn,
               count(*) FILTER (WHERE agency_phone IS NOT NULL) AS n_simi,
               count(*) FILTER (WHERE agency_email IS NOT NULL) AS n_netfang
          FROM scraper.listings WHERE source = 'mbl'
    """)
    n_alls, n_nafn, n_simi, n_net = cur.fetchone()
    p = (100.0 * n_nafn / n_alls) if n_alls else 0.0
    log(f"  ÞEKJA {merki}: nafn {n_nafn}/{n_alls} = {p:.1f}% "
        f"· sími {n_simi} · netfang {n_net}  (nefnari = allar mbl-raðir)")
    return {"n_alls": n_alls, "n_nafn": n_nafn, "n_simi": n_simi, "n_netfang": n_net}


def run(confirm: bool, log=print):
    agency = lesa_agency(log)
    dsn = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    pg = psycopg2.connect(dsn)
    try:
        cur = pg.cursor()
        fyrir = maela(cur, log, "FYRIR")

        # Náanleg þekja: hve margar mbl-raðir eiga sér parsed-samsvörun?
        cur.execute("SELECT source_listing_id FROM scraper.listings WHERE source = 'mbl'")
        i_db = [r[0] for r in cur.fetchall()]
        naanlegt = [s for s in i_db if s in agency]
        log(f"  NÁANLEGT: {len(naanlegt)}/{len(i_db)} mbl-raðir eiga parsed-söluaðila "
            f"({100.0 * len(naanlegt) / max(len(i_db), 1):.1f}%) — "
            f"{len(i_db) - len(naanlegt)} raðir geta ALDREI fengið hann úr þessari lind")
        pg.rollback()

        if not confirm:
            log("  --dry-run: engin skrif.")
            return fyrir, None

        radir = [[s] + [agency[s][c] for c in COLS] for s in naanlegt]
        cur.execute("SET TRANSACTION READ WRITE")
        setja = ", ".join(f"{c} = v.{c}" for c in COLS)
        # Engin no-op vörn hér: þetta er einskiptis-fylling á NULL-dálkum og
        # hver röð er skrifuð í mesta lagi einu sinni.
        execute_values(cur, f"""
            UPDATE scraper.listings l
               SET {setja}, updated_at = now()
              FROM (VALUES %s) AS v (source_listing_id, {", ".join(COLS)})
             WHERE l.source = 'mbl' AND l.source_listing_id = v.source_listing_id
        """, radir, page_size=1000)
        pg.commit()
        log(f"  SKRIFAÐ: {len(radir)} raðir uppfærðar")
        eftir = maela(cur, log, "EFTIR")
        pg.rollback()
        return fyrir, eftir
    finally:
        pg.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--confirm", action="store_true", help="framkvæma bakfyllinguna")
    ap.add_argument("--dry-run", action="store_true", help="mæla án skrifa")
    a = ap.parse_args()
    if not (a.confirm or a.dry_run):
        print(__doc__)
        return 0
    print("=== backfill_listing_agency (cc82) ===")
    run(confirm=a.confirm and not a.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
