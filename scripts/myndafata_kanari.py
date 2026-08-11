#!/usr/bin/env python3
r"""myndafata_kanari.py — cc117 FASI B, þrep 2.

Vaktar að OPINBERA myndafatan beri EKKERT nema birtingarmyndir.

Fata sem opnast rétt í dag er ekki fata sem helst rétt. Þrjú próf, hvert
sjálfstætt, öll fail-closed:

  P1  FORSKEYTAÚTTEKT     rót fötunnar má bera nákvæmlega hvítlistuðu
                          forskeytin — hvorki fleiri né færri. Nýtt forskeyti
                          (t.d. `current/` ef einhver beinir næturafritinu
                          á ranga fötu) fellir kanaríið SAMSTUNDIS.
  P2  EINKALYKILL 404     HTTP-sókn á lykil sem á EKKI að vera opinber skal
                          skila 404/403. Skili hann 200 eru afritin á neti.
  P3  BIRTINGARLYKILL 200 þekktur myndalykill skal svara 200 með image/*.
                          Fall hér er birtingargat, ekki öryggisgat — en það
                          á að sjást í sömu mælingu.

P1 keyrir GEGN S3-API-inu (rclone, einkaheimild) og er því óháður því hvort
lénið sé komið upp. P2/P3 keyra gegn OPINBERA léninu og eru sleppt með
skýrri stöðu ef `--len` vantar — þau mæla ekkert fyrr en þrep 1 er komið.

REGLAN SEM ÞETTA VER: R2 kann enga forskeytis-skorðun á opinberum aðgangi.
Opinber fata er opinber Í HEILD. Þess vegna er hvítlistinn hér eina vörnin
milli birtingar og næturafritanna — og hann verður að vera MÆLDUR, ekki
treyst. Sbr. feedback_fotu_heild_ur_undirlidum_er_ekki_heild.

Skilar 0 þegar allt stenst, 2 þegar próf fellur. Ætlað í næturkeðjuna við
hlið cc55-kanarísins.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROT         = Path(r"D:\verdmat-is")
RCLONE      = ROT / "tools" / "rclone" / "rclone.exe"
RCLONE_CONF = ROT / "tools" / "rclone" / "rclone.conf"

# HVÍTLISTINN. Breyting hér er stefnubreyting og á að vera commit með rökum.
LEYFD_FORSKEYTI = {"myndir/", "augl-myndir/"}

# myndir-leiga/ er VÍSVITANDI EKKI á listanum (cc117 §3.5): auðkennin para ekki
# við leiguauglýsingarnar og enginn núlifandi ferill skrifar forskeytið.
# Uppruni óstaðfestur ⇒ bætin fara ekki á opinn hýsil fyrr en það liggur fyrir.

EINKALYKLAR = [           # P2 — mega ALDREI svara 200 á opinbera léninu
    "current/Gagnapakkar/fasteignir.db",
    "archive/",
    "myndamanifest/stada.json",
]
BIRTINGARLYKLAR = [       # P3 — eiga að svara 200
    "myndir/33/1.jpg",
    "augl-myndir/",       # fyllt af --birtingarlykill ef gefinn
]


def _rclone(*args: str) -> str:
    return subprocess.run(
        [str(RCLONE), "--config", str(RCLONE_CONF), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout


def p1_forskeyti(fata: str) -> tuple[bool, dict]:
    ut = _rclone("lsf", f"{fata}", "--dirs-only", "--max-depth", "1")
    fundin = {l.strip() for l in ut.splitlines() if l.strip()}
    umfram = sorted(fundin - LEYFD_FORSKEYTI)
    vantar = sorted(LEYFD_FORSKEYTI - fundin)
    return (not umfram and not vantar), {
        "fundin": sorted(fundin), "umfram": umfram, "vantar": vantar,
    }


def _http(url: str) -> int:
    import urllib.error
    import urllib.request
    bein = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(bein, timeout=20) as svar:
            return svar.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def p2_einkalyklar(len_: str) -> tuple[bool, list]:
    nid = []
    for lykill in EINKALYKLAR:
        kodi = _http(f"https://{len_}/{lykill}")
        nid.append({"lykill": lykill, "http": kodi, "ok": kodi in (403, 404)})
    return all(n["ok"] for n in nid), nid


def p3_birtingarlyklar(len_: str, aukalykill: str | None) -> tuple[bool, list]:
    lyklar = [k for k in BIRTINGARLYKLAR if not k.endswith("/")]
    if aukalykill:
        lyklar.append(aukalykill)
    nid = []
    for lykill in lyklar:
        kodi = _http(f"https://{len_}/{lykill}")
        nid.append({"lykill": lykill, "http": kodi, "ok": kodi == 200})
    return all(n["ok"] for n in nid), nid


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fata", default="r2backup:verdmat-backups")
    p.add_argument("--len", dest="len_", default=None,
                   help="opinbera lénið, t.d. myndir.verdmat.ai. "
                        "Vanti það eru P2/P3 SLEPPT — ekki talin standast.")
    p.add_argument("--birtingarlykill", default=None)
    a = p.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nid = {"ts": ts, "fata": a.fata, "len": a.len_}

    ok1, d1 = p1_forskeyti(a.fata)
    nid["P1_forskeyti"] = {"stada": "OK" if ok1 else "FELLUR", **d1}
    print(f"P1 forskeytaúttekt : {'OK' if ok1 else 'FELLUR'}")
    print(f"   fundin  : {d1['fundin']}")
    if d1["umfram"]:
        print(f"   UMFRAM  : {d1['umfram']}   <- fatan ber meira en birtingu")
    if d1["vantar"]:
        print(f"   VANTAR  : {d1['vantar']}")

    if not a.len_:
        nid["P2_einkalyklar"] = {"stada": "SLEPPT", "astaeda": "lén ekki gefið"}
        nid["P3_birtingarlyklar"] = {"stada": "SLEPPT", "astaeda": "lén ekki gefið"}
        print("P2 einkalyklar     : SLEPPT (lén ekki gefið — þrep 1 ógert)")
        print("P3 birtingarlyklar : SLEPPT (lén ekki gefið — þrep 1 ógert)")
        heild = ok1
    else:
        ok2, d2 = p2_einkalyklar(a.len_)
        nid["P2_einkalyklar"] = {"stada": "OK" if ok2 else "FELLUR", "prof": d2}
        print(f"P2 einkalyklar     : {'OK' if ok2 else 'FELLUR'}")
        for n in d2:
            print(f"   {n['http']:>4}  {n['lykill']}"
                  f"{'' if n['ok'] else '   <- SVARAR! afritin eru a neti'}")
        ok3, d3 = p3_birtingarlyklar(a.len_, a.birtingarlykill)
        nid["P3_birtingarlyklar"] = {"stada": "OK" if ok3 else "FELLUR", "prof": d3}
        print(f"P3 birtingarlyklar : {'OK' if ok3 else 'FELLUR'}")
        for n in d3:
            print(f"   {n['http']:>4}  {n['lykill']}")
        heild = ok1 and ok2 and ok3

    nid["heild"] = "OK" if heild else "FELLUR"
    print(json.dumps(nid, ensure_ascii=False))
    return 0 if heild else 2


if __name__ == "__main__":
    sys.exit(main())
