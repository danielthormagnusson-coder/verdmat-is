"""cc219_bakfylla_hra_athuganir.py — einskiptis bakfylling scraper.verdvakt_hra_athugun úr eigin hrá-sóknum (raw_mbl.db).

Fyrir hverja sölu-auglýsingu mbl með verðbreytingu í scraper.listing_price_history: verð-keyrslur úr listasíðu-sóknum
(list_page_sale*) — keyrsla = samfelld röð sókna með sama verði. Umskipti fyrra→nýtt fá sast_sidast_fyrra (síðasta sókn
fyrra verðs) og sast_fyrst_nytt (fyrsta sókn nýja verðs) = athuguð dagsetning (cc60 „sást þann X"). Tilvik = k-ta
umskipti sama (fyrra, nýtt) á auglýsingunni. Aðeins umskipti með sast_fyrst_nytt í glugganum 09.06–07.09.2026 (ákvörðun
Danna 30.09: frá fyrstu hrá-sókn; frá 07.09 dagsetur athuganaskráin).

Snertir EKKI sópun, delta eða afritun (BANN cc219). raw_mbl.db opnað read-only. Ein skrif-færsla (SET TRANSACTION READ WRITE
fyrst), idempotent: DELETE per utgafa + INSERT. --dry-run (sjálfgefið) rúllar til baka.

Notkun:
  python scripts/cc219_bakfylla_hra_athuganir.py              # þurrt: reiknar, setur inn, rúllar til baka
  python scripts/cc219_bakfylla_hra_athuganir.py --skrifa     # skrifar
"""
from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras

UTGAFA = "cc219-bakfylling-v1"
GLUGGI_FRA = pd.Timestamp("2026-06-09", tz="UTC")     # fyrsta hrá-sókn 09.06 16:44Z (ákvörðun Danna 30.09)
GLUGGI_TIL = pd.Timestamp("2026-09-07 19:40", tz="UTC")   # cc193: refresh athuganaskrár skráð 07.09 19:39–19:41Z
RAW = Path(r"D:\verdmat-is\scraper_data\raw_mbl.db")
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skrifa", action="store_true")
    args = ap.parse_args()
    conn = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    cur.execute("SET LOCAL statement_timeout = '15min'")
    cur.execute("""with ph as (select source, source_listing_id, price_amount,
                         lag(price_amount) over (partition by source, source_listing_id order by id) prev
                    from scraper.listing_price_history where source = 'mbl')
                   select distinct l.listing_id, l.source_listing_id
                     from ph join scraper.listings l using (source, source_listing_id)
                    where ph.prev is not null and ph.prev <> ph.price_amount and l.tenure = 'sale'""")
    thorf = {str(s): int(lid) for lid, s in cur.fetchall()}
    print(f"sölu-auglýsingar með breytingu í verðsögu: {len(thorf)}")

    r = sqlite3.connect(f"file:{RAW.as_posix()}?mode=ro", uri=True)
    sed = []
    for rid, fa, h in r.execute("""select raw_id, fetched_at, content_hash from raw_fetches where source='mbl' and http_status=200
                                     and fetch_kind like 'list_page_sale%' order by fetched_at, raw_id"""):
        b = r.execute("select blob_gz from raw_blobs where content_hash=?", (h,)).fetchone()
        if not b:
            continue
        try:
            j = json.loads(gzip.decompress(b[0]))
        except Exception:
            continue
        for it in (j.get("data") or {}).get("fs_fasteign") or []:
            e = str(it.get("eign_id"))
            # verð < 1 M (0 = „tilboð") er ekki athugað verð: slítur ekki keyrslu og myndar ekki par (sama mörk og MV, ≥ 1 M)
            if e in thorf and it.get("verd") is not None and int(it["verd"]) >= 1_000_000:
                sed.append((e, fa, int(rid), int(it["verd"])))
    A = pd.DataFrame(sed, columns=["eign_id", "fetched_at", "raw_id", "verd"])
    A["fetched_at"] = pd.to_datetime(A.fetched_at, utc=True)
    A = A.sort_values(["eign_id", "fetched_at", "raw_id"])
    A["keyrsla"] = (A.verd != A.groupby("eign_id").verd.shift()).groupby(A.eign_id).cumsum()
    K = A.groupby(["eign_id", "keyrsla"]).agg(verd=("verd", "first"), fyrst=("fetched_at", "min"), sidast=("fetched_at", "max"),
                                               raw_id=("raw_id", "first")).reset_index()
    K["fyrra_verd"] = K.groupby("eign_id").verd.shift()
    K["sast_sidast_fyrra"] = K.groupby("eign_id").sidast.shift()
    U = K[K.fyrra_verd.notna()].copy()
    U["fyrra_verd"] = U.fyrra_verd.astype("int64")
    U["tilvik"] = U.groupby(["eign_id", "fyrra_verd", "verd"]).cumcount() + 1
    U = U[(U.fyrst >= GLUGGI_FRA) & (U.fyrst <= GLUGGI_TIL)]
    rows = [(thorf[e], int(f), int(n), int(t), s.to_pydatetime() if pd.notna(s) else None, fy.to_pydatetime(), int(rid), UTGAFA)
            for e, f, n, t, s, fy, rid in zip(U.eign_id, U.fyrra_verd, U.verd, U.tilvik, U.sast_sidast_fyrra, U.fyrst, U.raw_id)]
    print(f"hrá-athuganir {len(A)} · umskipti í glugga {GLUGGI_FRA:%d.%m}–{GLUGGI_TIL:%d.%m}: {len(rows)}")

    cur.execute("delete from scraper.verdvakt_hra_athugun where utgafa = %s", (UTGAFA,))
    psycopg2.extras.execute_values(cur, """insert into scraper.verdvakt_hra_athugun
        (listing_id, fyrra_verd, nytt_verd, tilvik, sast_sidast_fyrra, sast_fyrst_nytt, raw_id, utgafa) values %s""", rows, page_size=1000)
    cur.execute("select count(*), min(sast_fyrst_nytt), max(sast_fyrst_nytt) from scraper.verdvakt_hra_athugun where utgafa = %s", (UTGAFA,))
    print("í töflu:", cur.fetchone())
    if args.skrifa:
        conn.commit(); print("[OK] skrifað")
    else:
        conn.rollback(); print("[ÞURRT] rúllað til baka")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
