r"""endurnyja_eftir_promote.py — cc210 (cc207-tillagan): ógildir /eign-cache-ið fyrir fastnum
sem næturpromote breytti, svo „Á sölu"-kortið birtist strax en ekki eftir SWR-hringinn.

HVERS VEGNA: saekjaEign() í verdmat-ai liggur í unstable_cache (TTL 3600, stale-while-
revalidate). Fyrsta heimsókn eftir promote fékk GÖMLU færsluna (cc207, Akurgerði 37). TTL er
öryggisnet, ekki ógilding. /api/endurnyja (cc73) tekur við fastnum-lista og hendir merkjunum
`eign-<fastnum>`.

INNTAK: scraper_data/mbl_promote_changed_fastnums.json, skrifað af promote_listings_append
(RETURNING undir no-op-verðinum = raunverulega settar/breyttar raðir). --eftir ISO-tími: skráin
verður að vera skrifuð EFTIR hann (keðjan sendir CHAIN_START) — annars er ekkert sent, svo
listi gærdagsins berst aldrei í kall dagsins.

ÞAK: N = MAX_FASTNUMS (2.000) slóðir per kall. Mælt cc210 (scraper.listings.updated_at 01–05
UTC, 12.–27.09): 293–980 einkvæm fastnum per nótt, miðgildi ~700 → þakið er ~2× hæsta nótt.
Yfir þaki → `{allt:true}` (ein aðgerð; leiðin sjálf hafnar >5.000). Lykillinn:
ENDURNYJA_LYKILL úr umhverfi, annars D:\env.local — gildið er ALDREI prentað.

BEST-EFFORT: exit 0 í ÖLLUM tilvikum (vantar lykil, net fellur, HTTP ≠ 200) — keðjan má aldrei
falla á ógildingu; TTL grípur. Ein lína á stdout (keðjan setur hana í night-log).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_scraper_data_dir  # noqa: E402

ENDURNYJA_URL = "https://www.verdmat.ai/api/endurnyja"
ENV_ROT = Path(r"D:\env.local")
CHANGED_FILE = "mbl_promote_changed_fastnums.json"
MAX_FASTNUMS = 2000
TIMEOUT_S = 30


def lesa_lykil(nafn):
    """Umhverfi fyrst, svo D:\\env.local (KEY=value, CRLF, utf-8-sig). Sama regla og cc180."""
    v = os.environ.get(nafn)
    if v:
        return v.strip()
    try:
        for lina in ENV_ROT.read_text(encoding="utf-8-sig").splitlines():
            k, sep, val = lina.partition("=")
            if sep and k.strip() == nafn:
                return val.strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eftir", default=None, help="ISO-tími; skráin verður að vera skrifuð eftir hann")
    ap.add_argument("--dry-run", action="store_true", help="segja hvað yrði sent; ekkert HTTP-kall")
    args = ap.parse_args()

    p = get_scraper_data_dir() / CHANGED_FILE
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("revalidate SLEPPT: %s ólæsileg (%s)" % (p.name, type(e).__name__))
        return 0
    written = datetime.fromisoformat(d["written_at"])
    if args.eftir and written <= datetime.fromisoformat(args.eftir):
        print("revalidate SLEPPT: %s skrifuð %s, ekki eftir %s (engin promote-skrif í nótt?)"
              % (p.name, d["written_at"], args.eftir))
        return 0
    fastnums = [int(f) for f in d.get("fastnums", [])]
    if not fastnums:
        print("revalidate SLEPPT: 0 breytt fastnum")
        return 0
    if len(fastnums) > MAX_FASTNUMS:
        farmur, lysing = {"allt": True}, "allt (%d > þak %d)" % (len(fastnums), MAX_FASTNUMS)
    else:
        farmur, lysing = {"fastnums": fastnums}, "fastnums=%d" % len(fastnums)
    if args.dry_run:
        print("revalidate [dry-run] myndi senda %s" % lysing)
        return 0
    lykill = lesa_lykil("ENDURNYJA_LYKILL")
    if not lykill:
        print("revalidate SLEPPT: ENDURNYJA_LYKILL hvorki í umhverfi né D:\\env.local (%s)" % lysing)
        return 0
    req = urllib.request.Request(ENDURNYJA_URL, data=json.dumps(farmur).encode(), method="POST",
                                 headers={"content-type": "application/json", "x-endurnyja-lykill": lykill})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            print("revalidate %s: HTTP %s %s" % (lysing, r.status, r.read(200).decode("utf-8", "replace")))
    except urllib.error.HTTPError as e:
        print("revalidate FÉLL (%s): HTTP %s — /eign endurnýjast á TTL" % (lysing, e.code))
    except Exception as e:  # noqa: BLE001  best-effort: TTL er öryggisnetið
        print("revalidate FÉLL (%s): %s — /eign endurnýjast á TTL" % (lysing, type(e).__name__))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001  aldrei fella keðjuna
        print("revalidate VILLA (%s) — keðjan heldur áfram" % type(e).__name__)
        sys.exit(0)
