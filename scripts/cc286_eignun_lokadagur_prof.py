"""cc286 — einingapróf + falspróf fyrir eignun fasteignasala (regla cc286-v1). Engin DB-tenging.

Keyrsla:  python scripts/cc286_eignun_lokadagur_prof.py
Fastar prófanir eru raungögn (scraper.listings + kaupskrá 31.10.2026), ekki tilbúin dæmi:
  Hringhamar 17, fnr 2529237, samningur 746997, K = 2026-09-03:
    Lind 5473   hófst 2026-05-15 23:10, status active, withdrawn_at NULL, last_seen_at 2026-07-24 (síðasta delta-sókn)
    RE/MAX 5894 hófst 2026-05-08 11:09, withdrawn_at 2026-10-08
  Rétt (síðan: „sú sem var virk á kaupsamningsdegi", jafntefli á seinna upphafi): Lind. Gamla reglan gaf RE/MAX.
Falspróf: gamla lokadagsreglan max(withdrawn_at, last_seen_at) og gamli upphafssamanburðurinn (klukkutími) eru keyrð á
SÖMU prófanir og VERÐA að falla. Exit 0 = öll próf standast og öll falspróf falla eins og vænst var.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
import cc213_fasteignasala_manudur as F  # noqa: E402

T = pd.Timestamp
LIND, REMAX, AS = 101, 102, 103
nidur: list[tuple[str, bool]] = []


def prof(nafn, skilyrdi):
    nidur.append((nafn, bool(skilyrdi)))


def auglysingar(radir):
    a = pd.DataFrame(radir, columns=["listing_id", "fastnum", "agency_source_id", "status", "listed_at", "first_seen_at",
                                     "last_seen_at", "sidast_fundin_at", "withdrawn_at"])
    for c in ("listed_at", "first_seen_at", "last_seen_at", "sidast_fundin_at", "withdrawn_at"):
        a[c] = pd.to_datetime(a[c], format="ISO8601")
    a["start"] = a[["listed_at", "first_seen_at"]].min(axis=1)
    return a


def eigna_med(a, end_fall, fyrir_dagur=True, K="2026-09-03", fastnum=2529237, faersla="746997"):
    a = a.copy(); a["end"] = end_fall(a)
    c = pd.DataFrame({"FAERSLUNUMER": [faersla], "utg": [T(K)]})
    k = pd.DataFrame({"FAERSLUNUMER": [faersla], "fastnum": [fastnum]})
    if fyrir_dagur:
        r = F.eigna(c, k, a)
    else:                      # gamli upphafssamanburðurinn (klukkutími gegn miðnætti K) — fyrir falspróf
        r = _eigna_gamalt_upphaf(c, k, a)
    return r.iloc[0]


def _eigna_gamalt_upphaf(c, k, a):
    """Spegill F.eigna með m.fyrir = m.start <= m.utg (cc223-v1) — aðeins fyrir falspróf F2."""
    import numpy as np
    cf = k[k.FAERSLUNUMER.isin(c.FAERSLUNUMER)][["FAERSLUNUMER", "fastnum"]].drop_duplicates()
    m = cf.merge(c[["FAERSLUNUMER", "utg"]], on="FAERSLUNUMER").merge(a[["listing_id", "fastnum", "start", "end", "agency_source_id"]], on="fastnum")
    m = m[((m.start - m.utg).dt.days <= F.EFTIR_DAGAR) & ((m.end - m.utg).dt.days >= -F.W_DAGAR)].copy()
    m["fyrir"] = m.start <= m.utg
    m["virk"] = m.fyrir & (m.end >= m.utg)
    m = m.sort_values(["FAERSLUNUMER", "virk", "fyrir", "start", "listing_id"], ascending=[True, False, False, False, True])
    p = m.groupby("FAERSLUNUMER").head(1).set_index("FAERSLUNUMER")
    p["regla"] = np.where(p.virk, "virk_a_K", np.where(p.fyrir, "sidasta_fyrir_K", "fyrsta_eftir_K"))
    return c.set_index("FAERSLUNUMER").join(p[["listing_id", "agency_source_id", "regla"]]).reset_index()


def gamli_lokadagur(a):
    return a[["withdrawn_at", "last_seen_at"]].max(axis=1)


# ---------------------------------------------------------------- lokadagur()
L = auglysingar([
    (1, 1, LIND, "active", "2026-05-15", "2026-05-15", "2026-07-24", None, None),
    (2, 1, REMAX, "withdrawn", "2026-05-08", "2026-05-08", "2026-09-20", None, "2026-10-08"),
    (3, 1, AS, "inactive", "2026-01-01", "2026-01-01", "2026-03-01", "2026-03-15", None),
    (4, 1, AS, "active", "2026-01-01", "2026-01-01", "2026-03-01", None, "2026-04-01"),
    (5, 1, AS, "inactive", "2026-01-01", "2026-01-01", "2026-03-01", None, None),
])
e = F.lokadagur(L)
prof("L1 active + withdrawn_at NULL → opin lok (ekki last_seen_at)", e[0] == F.OPIN_LOK)
prof("L2 withdrawn_at til → withdrawn_at", e[1] == T("2026-10-08"))
prof("L3 inactive án withdrawn_at → max(last_seen_at, sidast_fundin_at)", e[2] == T("2026-03-15"))
prof("L4 active MEÐ withdrawn_at → withdrawn_at (regla: withdrawn_at ef til)", e[3] == T("2026-04-01"))
prof("L5 inactive, sidast_fundin_at NULL → last_seen_at", e[4] == T("2026-03-01"))
prof("L6 gamla reglan gefur last_seen_at fyrir virka (falspróf-forsenda)", gamli_lokadagur(L)[0] == T("2026-07-24"))

# ---------------------------------------------------------------- Hringhamar 17 (raungögn)
H17 = auglysingar([
    (5473, 2529237, LIND, "active", "2026-05-15 23:10:28", "2026-05-15 23:10:28", "2026-07-24 02:50:46", None, None),
    (5894, 2529237, REMAX, "withdrawn", "2026-05-08 11:09:49", "2026-05-08 11:09:49", "2026-09-20 01:08:04", None, "2026-10-08 14:02:06"),
    (8596, 2529237, AS, "withdrawn", "2025-10-03 14:43:01", "2025-10-03 14:43:01", "2026-06-12 06:33:11", None, "2026-09-14 10:22:04"),
])
r = eigna_med(H17, F.lokadagur)
prof("H1 Hringhamar 17 (746997): ný regla → Lind (5473), virk_a_K", r.listing_id == 5473 and r.agency_source_id == LIND and r.regla == "virk_a_K")
r_gamalt = eigna_med(H17, gamli_lokadagur)
prof("F1 FALSPRÓF: gamla lokadagsreglan → RE/MAX (prófið H1 VERÐUR að grípa það)", r_gamalt.agency_source_id == REMAX and not (r_gamalt.agency_source_id == LIND))

# ---------------------------------------------------------------- virk á K á dagsgrunni
D = auglysingar([
    (21, 7, LIND, "active", "2026-09-03 14:00", "2026-09-03 14:00", "2026-09-03 14:00", None, None),     # hefst á K
    (22, 7, REMAX, "withdrawn", "2026-06-01", "2026-06-01", "2026-06-20", None, "2026-08-01"),             # lauk fyrir K
])
r = eigna_med(D, F.lokadagur, fastnum=7)
prof("D1 auglýsing sem birtist á K (14:00) telst virk á K → Lind, virk_a_K", r.agency_source_id == LIND and r.regla == "virk_a_K")
r_g = eigna_med(D, F.lokadagur, fyrir_dagur=False, fastnum=7)
prof("F2 FALSPRÓF: klukkutímasamanburður → RE/MAX sidasta_fyrir_K (D1 VERÐUR að grípa það)", r_g.agency_source_id == REMAX and r_g.regla == "sidasta_fyrir_K")

# ---------------------------------------------------------------- óbreytt hegðun þar sem reglan á ekki við
U = auglysingar([
    (31, 8, LIND, "withdrawn", "2026-01-01", "2026-01-01", "2026-02-01", None, "2026-02-10"),
    (32, 8, REMAX, "withdrawn", "2026-03-01", "2026-03-01", "2026-04-01", None, "2026-04-15"),
])
prof("U1 engin virk á K → síðasta sem hófst ≤ K (REMAX), eins og áður", eigna_med(U, F.lokadagur, fastnum=8).agency_source_id == REMAX)
prof("U2 sama niðurstaða með gömlu reglunni (breytingin snertir ekki afskráðar)", eigna_med(U, gamli_lokadagur, fastnum=8).agency_source_id == REMAX)
prof("R1 REGLA_VERSION = cc286-v1", F.REGLA_VERSION == "cc286-v1" and F.SJALFGEFNAR_REGLUR == ("cc286-v1",))

ok = all(b for _, b in nidur)
for n, b in nidur:
    print(f"{'STENST' if b else 'FELLUR'}  {n}")
print(f"\n{sum(b for _, b in nidur)}/{len(nidur)} {'— ÖLL STANDAST (falsprófin F1/F2 sýna að gamla reglan fellur)' if ok else '— BRESTUR'}")
sys.exit(0 if ok else 1)
