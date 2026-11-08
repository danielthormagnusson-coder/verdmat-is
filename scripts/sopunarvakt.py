"""sopunarvakt.py — cc324: sér ÞÖGULT svelti í lifecycle-sópun. Aðeins lestur; 0 mbl-beiðnir.

Tilefni (D:/_audit/cc324_sopun/SKIL_CC324.md): kort-lotan stóð frá 23.10 í 15+ daga. Verkið skilaði rc 0 hvern dag,
ein keyrsla 0 beiðnir, og ekkert af því sem vaktin las breyttist. Vaktin spyr því ekki hvort verkið keyrði heldur
hvort HVER LOTA hafi skilað sér á ÁFANGASTAÐ.

  K0  ríki sópunar uppfært síðustu 26 klst (verkið keyrði)
  K1  síðasti kort-atburður í scraper.listing_lifecycle_events yngri en 48 klst      (áfangastaður)
  K2  leigu-hringur lokið síðustu 13 d  (7 d taktur + mest 5 keyrslur á 100 beiðnum + svigrúm)
  K3  sölu-hringur lokið síðustu 28 d   (áætlun eftir uppsöfnun: mest 25 d; stöðugt um 15 d)
  K4  draugar úr þekjuprófi, 7 síðustu mælingar: >= 5 % á nefnara >= 150 (sólarhringsþak 20 % sá ekkert)
  K5  keyrslulína: engin beiðni í tveimur keyrslum í röð þótt eitthvað bíði (ef lifecycle_sweep_runs.jsonl er til)

Úttak: ein lína per athugun + `SOPUNARVAKT: OK|FALL (...)`. rc 0 OK · 1 FALL · 3 mæling mistókst (telst ekki OK).
Föllin eru hrein (meta) svo söguprófið keyri á sömu reglu og vaktin.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

K0_KLST, K1_KLST, K2_DAGAR, K3_DAGAR = 26, 48, 13, 28
K4_MAELINGAR, K4_NEFNARI, K4_HLUTFALL = 7, 150, 0.05
K5_RAD = 2
UTC = timezone.utc


def _p(s):
    return datetime.fromisoformat(s) if s else None


def meta(nu, riki_breytt, kort_sidast, leiga_lokid, sala_lokid, draugar, keyrslur=None):
    """Hrein regla. draugar = [(draug_n, nefnari)] elsta fyrst. Skilar [(kóði, stenst, skýring)]."""
    ut = []
    k0 = riki_breytt is not None and (nu - riki_breytt) <= timedelta(hours=K0_KLST)
    ut.append(("K0", k0, "ríki síðast skrifað %s" % riki_breytt))
    k1 = kort_sidast is not None and (nu - kort_sidast) <= timedelta(hours=K1_KLST)
    ut.append(("K1", k1, "síðasti kort-atburður %s (þak %d klst)" % (kort_sidast, K1_KLST)))
    k2 = leiga_lokid is not None and (nu - leiga_lokid) <= timedelta(days=K2_DAGAR)
    ut.append(("K2", k2, "leiga síðast lokið %s (þak %d d)" % (leiga_lokid, K2_DAGAR)))
    k3 = sala_lokid is not None and (nu - sala_lokid) <= timedelta(days=K3_DAGAR)
    ut.append(("K3", k3, "sala síðast lokið %s (þak %d d)" % (sala_lokid, K3_DAGAR)))
    sidast = draugar[-K4_MAELINGAR:]
    n, d = sum(x[0] for x in sidast), sum(x[1] for x in sidast)
    k4 = d < K4_NEFNARI or (n / d) < K4_HLUTFALL
    ut.append(("K4", k4, "draugar %d/%d í %d mælingum (þak %.0f %%)" % (n, d, len(sidast), K4_HLUTFALL * 100)))
    if keyrslur:
        rod = keyrslur[-K5_RAD:]
        tomar = len(rod) == K5_RAD and all(
            r.get("requests") == 0 and ((r.get("card_due") or 0) > 0 or r.get("rent_total") or r.get("sale_total"))
            for r in rod)
        ut.append(("K5", not tomar, "beiðnir síðustu keyrslna %s" % [r.get("requests") for r in rod]))
    return ut


def lesa_db(url):
    import psycopg2
    c = psycopg2.connect(url, connect_timeout=15, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
    try:
        with c.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute("SET LOCAL statement_timeout = 60000")
            cur.execute("SELECT max(event_at) FROM scraper.listing_lifecycle_events "
                        "WHERE source='mbl' AND evidence->>'sweep_id' LIKE %s AND event_at > now() - interval '60 days'",
                        ("%\\_card\\_%",))
            kort = cur.fetchone()[0]
            cur.execute("SELECT draug_n, draug_nefnari FROM (SELECT dags, draug_n, draug_nefnari FROM scraper.thekjuprof "
                        "ORDER BY dags DESC LIMIT %s) t ORDER BY dags", (K4_MAELINGAR,))
            draugar = [(int(a), int(b)) for a, b in cur.fetchall()]
        return kort, draugar
    finally:
        c.rollback()
        c.close()


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--gagnamappa", default=r"D:\verdmat-is\scraper_data")
    ap.add_argument("--dbconfig", default=r"D:\verdmat-is\.dbconfig")
    a = ap.parse_args()
    d = Path(a.gagnamappa)
    nu = datetime.now(UTC)
    try:
        rp = d / "lifecycle_sweep_state.json"
        st = json.loads(rp.read_text(encoding="utf-8"))
        riki = datetime.fromtimestamp(rp.stat().st_mtime, UTC)
        kort, draugar = lesa_db(Path(a.dbconfig).read_text(encoding="utf-8-sig").strip())
        rl = d / "lifecycle_sweep_runs.jsonl"
        keyrslur = [json.loads(x) for x in rl.read_text(encoding="utf-8").splitlines()[-K5_RAD:]] if rl.exists() else None
    except Exception as exc:   # vaktin má ekki þegja: mæling sem tekst ekki er ekki OK
        print("SOPUNARVAKT: MÆLING MISTÓKST (%s)" % type(exc).__name__)
        return 3
    nid = meta(nu, riki, kort, _p(st["rent"].get("last_completed_at")), _p(st["sale"].get("last_completed_at")),
               draugar, keyrslur)
    for kodi, ok, sk in nid:
        print("%s %s %s" % (kodi, "ok  " if ok else "FALL", sk))
    foll = [k for k, ok, _ in nid if not ok]
    print("SOPUNARVAKT: %s" % ("OK" if not foll else "FALL (%s)" % ",".join(foll)))
    return 1 if foll else 0


if __name__ == "__main__":
    sys.exit(main())
