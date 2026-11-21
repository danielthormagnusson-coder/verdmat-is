"""cc364: endurnýjar scraper.soluferli_opin_mv (opin söluferli, lind leitar) með REFRESH ... CONCURRENTLY.

Keyrt af cc193_keyra_verk.ps1 (verk soluferli_mv): eftir næturkeðju (07:40) og eftir sópun (18:00). Lesendur MV stöðvast
ekki (EXCLUSIVE-lás á MV eina; grunntöflur fá aðeins ACCESS SHARE). Mælt í --prof 21.11.2026: 45-61 s, 8.554 raðir.

Hlið fyrir COMMIT: ef raðafjöldi fellur um meira en 25 % frá fyrri fyllingu (eða MV er tóm) er færslunni rúllað til baka
og gamla fyllingin stendur (rc 2). --thurrt keyrir sama og endar á ROLLBACK.
"""
import argparse, sys, time
from pathlib import Path
import psycopg2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BOTN = Path(r"D:\verdmat-is")
HAMARK_FALL = 0.25


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thurrt", action="store_true", help="endurnýjar og rúllar til baka (ekkert vistað)")
    a = ap.parse_args()
    c = psycopg2.connect((BOTN / ".dbconfig").read_text(encoding="utf-8-sig").strip(), connect_timeout=15)
    c.autocommit = False
    try:
        c.rollback()
        cur = c.cursor()
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("SET LOCAL statement_timeout = '600s'")
        cur.execute("SET LOCAL lock_timeout = '10s'")
        cur.execute("select count(*), max(reiknad_at) from scraper.soluferli_opin_mv")
        fyrir, fyrir_at = cur.fetchone()
        t = time.time()
        cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY scraper.soluferli_opin_mv")
        cur.execute("select count(*), count(*) filter (where not upphaf_viss) from scraper.soluferli_opin_mv")
        eftir, ovist = cur.fetchone()
        sek = time.time() - t
        print(f"soluferli_opin_mv: {fyrir} -> {eftir} raðir ({ovist} með óvisst upphaf), {sek:.0f} s; fyrri fylling {fyrir_at}")
        if eftir == 0 or (fyrir and eftir < fyrir * (1 - HAMARK_FALL)):
            c.rollback()
            print(f"[HLIÐ] raðafjöldi féll úr {fyrir} í {eftir} (> {HAMARK_FALL:.0%}): ROLLBACK, gamla fyllingin stendur")
            return 2
        if a.thurrt:
            c.rollback()
            print("--thurrt: ROLLBACK")
            return 0
        c.commit()
        print("COMMIT")
        return 0
    except Exception as e:
        c.rollback()
        print("[VILLA] ROLLBACK:", type(e).__name__, e)
        return 1
    finally:
        c.close()


if __name__ == "__main__":
    sys.exit(main())
