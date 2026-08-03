"""hms_mat_argerd_skref0.py — cc82 SKREF 0: er árgerð HMS-reitanna staðfestanleg innanhúss?

SPURNINGIN (eigandi, 03.08): má staðfesta hvor HMS-reiturinn (`fasteignamat` vs
`fasteignamat_nuverandi`) er hvaða árgerð ÚR OKKAR EIGIN GÖGNUM — í stað þess að
álykta það af framsetningu fastinn.is á EINNI eign?

AÐFERÐIN — TÍMAPRÓF Á KAUPSKRÁ:
`D:\\kaupskra.csv` ber `FASTEIGNAMAT` sem er SÖGULEGT mat á söludegi (DATA_SCHEMA:
„Historical fasteignamat á sale date", ólíkt `FASTEIGNAMAT_GILDANDI` sem er frosinn
snapshot). Fasteignamat tekur gildi 31.12 og gildir almanaksárið á eftir. Þar með:

  · sala þinglýst 2026 → söguleg tala hennar Á að vera matið sem gildir 2026
  · sala þinglýst 2025 → talan Á að vera matið sem gilti 2025

Ef `fasteignamat` er 2026-árgerðin og `fasteignamat_nuverandi` sú frá 2025, þá eiga
2026-sölur að hitta FYRRI reitinn og 2025-sölur þann SEINNI. Það er próf á okkar eigin
gögnum gegn HMS-safninu — enginn þriðji aðili kemur nálægt því.

⚠ HVAÐ PRÓFIÐ GETUR EKKI: það greinir ekki eign sem BREYTTIST (nýbygging, stækkun,
endurmat) frá árgerðamun. Þess vegna er hlutfallið lesið, ekki einstök tilvik, og
báðir reitir mældir á sama úrtaki (sami nefnari) svo skekkjan bitni jafnt á báðum.

READ-ONLY: les kaupskra.csv og HMS-safnið á diski. Engin tenging við Supabase,
ekkert skrifað.

CLI:
  python scripts/hms_mat_argerd_skref0.py
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

KAUPSKRA = Path(r"D:\kaupskra.csv")
HMS_ARCHIVE = Path(r"D:\HMS_jonas\hms_archive_staging.db")
AR = (2023, 2024, 2025, 2026)


def lesa_hms():
    sq = sqlite3.connect(f"file:{HMS_ARCHIVE}?mode=ro", uri=True)
    radir = []
    for fastnum, blob in sq.execute(
            "SELECT fastnum, fasteign_data FROM hms_fasteign "
            "WHERE exists_in_hms = 1 AND fasteign_data IS NOT NULL"):
        try:
            d = json.loads(blob)
        except (TypeError, ValueError):
            continue
        radir.append((int(fastnum), d.get("fasteignamat"),
                      d.get("fasteignamat_nuverandi"), d.get("fasteignamat_naesta_ar")))
    sq.close()
    return pd.DataFrame(radir, columns=["FASTNUM", "hms_mat", "hms_nuv", "hms_naesta"])


def main():
    print("=== hms_mat_argerd_skref0 (cc82, READ-ONLY) ===")
    hms = lesa_hms()
    print(f"  HMS-safn: {len(hms)} fastnúmer")

    k = pd.read_csv(KAUPSKRA, sep=";", encoding="latin-1", low_memory=False,
                    usecols=["FASTNUM", "THINGLYSTDAGS", "FASTEIGNAMAT", "ONOTHAEFUR_SAMNINGUR"])
    k["THINGLYSTDAGS"] = pd.to_datetime(k["THINGLYSTDAGS"], format="ISO8601", errors="coerce")
    k["ar"] = k["THINGLYSTDAGS"].dt.year
    for c in ("FASTNUM", "FASTEIGNAMAT", "ONOTHAEFUR_SAMNINGUR"):
        k[c] = pd.to_numeric(k[c], errors="coerce")
    # Ónothæfir samningar eru ekki markaðsviðskipti — sömu sía og þjálfunargögnin nota.
    k = k[(k["ONOTHAEFUR_SAMNINGUR"] == 0) & k["FASTEIGNAMAT"].notna() & (k["FASTEIGNAMAT"] > 0)]
    print(f"  kaupskrá: {len(k)} nothæfar sölur m/sögulegu mati")

    df = k.merge(hms, on="FASTNUM", how="inner")
    print(f"  samtenging: {len(df)} sölur eiga HMS-röð\n")

    print("  HITTNI SÖGULEGA MATSINS Á HVORN REIT (nefnari = sölur ársins í samtengingunni)")
    print(f"  {'ár':<6}{'n':>8}{'= hms_mat':>14}{'= hms_nuv':>14}{'= naesta':>12}{'hvorugt':>10}")
    for ar in AR:
        d = df[df["ar"] == ar]
        n = len(d)
        if not n:
            continue
        a = int((d["FASTEIGNAMAT"] == d["hms_mat"]).sum())
        b = int((d["FASTEIGNAMAT"] == d["hms_nuv"]).sum())
        c = int((d["FASTEIGNAMAT"] == d["hms_naesta"]).sum())
        hv = int((~((d["FASTEIGNAMAT"] == d["hms_mat"]) | (d["FASTEIGNAMAT"] == d["hms_nuv"])
                    | (d["FASTEIGNAMAT"] == d["hms_naesta"]))).sum())
        print(f"  {ar:<6}{n:>8}{a:>9} {100.0*a/n:>4.1f}%{b:>9} {100.0*b/n:>4.1f}%"
              f"{c:>7} {100.0*c/n:>4.1f}%{hv:>9}")

    # Hlutfallspróf: miðgildi hms_mat / sögulegt mat eftir söluári. Sé hms_mat
    # árgerð 2026 á miðgildið að nálgast 1,00 fyrir 2026-sölur og vaxa afturábak.
    print("\n  MIÐGILDI hms_mat / sögulegt mat  ·  hms_nuv / sögulegt mat")
    for ar in AR:
        d = df[(df["ar"] == ar) & (df["FASTEIGNAMAT"] > 0)]
        if not len(d):
            continue
        r1 = (d["hms_mat"] / d["FASTEIGNAMAT"]).median()
        r2 = (d["hms_nuv"] / d["FASTEIGNAMAT"]).median()
        print(f"  {ar:<6}n={len(d):<8}{r1:>8.4f}{r2:>12.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
