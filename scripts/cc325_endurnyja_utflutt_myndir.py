#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""cc325: endurnýjar registur_utflutningur.utflutt_eign_myndir, eina sýn, sem eigandi verdmat.

Verk: verdmat-daily-utflutt-myndir, 07:35 (scripts/register_utflutt_myndir_task.ps1).
Ákvörðun: DECISIONS 07.11 (arkitekt 12:45), WORKING_PROTOCOL (ad). Hluthafar les sýnina sem
registur_afrit. Skriftan breytir hvorki skema né réttindum og snertir enga aðra sýn.

Tengingin er 6543 (færslu-pooler), svo session-SET lifir ekki milli færslna. Tímaþökin eru því
SET LOCAL í sömu færslu og REFRESH, og færslan hefst á rollback + READ WRITE (WP (h)). Mælingar
eru utan þeirrar færslu, svo lásinn er ekki haldinn lengur en endurnýjunin.

Lokakóðar. Status-probe telur 0 og 3 gott, svo 3 er aldrei notaður hér:
  0 lokið · 4 banntími · 5 tenging eða forathugun féll, ekkert endurnýjað
  6 endurnýjun féll, sýnin óbreytt · 7 endurnýjun tókst en mæling á eftir féll · 9 óvænt villa
"""
import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import psycopg2

SYN_SKEMA = "registur_utflutningur"
SYN_NAFN = "utflutt_eign_myndir"
SYN = f"{SYN_SKEMA}.{SYN_NAFN}"
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
LOG = Path(r"D:\verdmat-is\logs\utflutt_myndir.log")

LOCK_TIMEOUT = "5s"
STATEMENT_TIMEOUT = "900s"
LES_TIMEOUT = "120s"

# Banntími er 01:00-07:30 UTC. Byrjað er að neita 15 mín. fyrr, því keyrsla sem hefst 00:50
# með 900 s þaki næði inn í bannið. Vélin er á GMT, en klukkan er lesin sem UTC óháð því.
BANN_FRA = dt.time(0, 45)
BANN_TIL = dt.time(7, 30)


def i_banni(kl):
    return BANN_FRA <= kl < BANN_TIL


def skra(texti):
    """Ein lína í log og á stdout. Tengistrengur kemur aldrei hingað."""
    lina = f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S} UTC {texti}"
    print(lina, flush=True)
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(lina + "\n")
    except OSError as e:
        print(f"log ekki skrifanlegt: {type(e).__name__}", flush=True)


def villutexti(e):
    """Hvítlisti: villukóði og aðalskilaboð þjóns. str(e) getur borið hýsil og notanda."""
    kodi = getattr(e, "pgcode", None) or "-"
    diag = getattr(e, "diag", None)
    bod = getattr(diag, "message_primary", None) or "(engin skilaboð frá þjóni)"
    return f"{type(e).__name__} pgcode={kodi}: {bod}"


def les(c, sql, breytur=None):
    """Lestur í eigin færslu með þaki. Skilar fyrstu röð."""
    c.rollback()
    with c.cursor() as q:
        q.execute(f"SET LOCAL statement_timeout = '{LES_TIMEOUT}'")
        q.execute(sql, breytur)
        rod = q.fetchone()
    c.commit()
    return rod


def endurnyja(c):
    """Eina skrifið. Sýnin stendur óbreytt ef eitthvað fellur, því allt er ein færsla."""
    c.rollback()
    with c.cursor() as q:
        q.execute("SET TRANSACTION READ WRITE")
        q.execute(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'")
        q.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
        q.execute("SELECT current_setting('lock_timeout'), current_setting('statement_timeout')")
        lt, st = q.fetchone()
        if lt != "5s" or st != "15min":  # Postgres sýnir 900s sem 15min.
            raise RuntimeError(f"þak ekki sett: lock_timeout={lt} statement_timeout={st}")
        t = time.monotonic()
        q.execute(f"REFRESH MATERIALIZED VIEW {SYN}")
    c.commit()
    return time.monotonic() - t, lt, st


def keyra():
    kl = dt.datetime.now(dt.timezone.utc).time()
    if i_banni(kl):
        skra(f"NEITAÐ: banntími {BANN_FRA:%H:%M}-{BANN_TIL:%H:%M} UTC, klukkan {kl:%H:%M}; ekkert tengt rc=4")
        return 4

    skra(f"START {SYN}")
    try:
        url = DBCONFIG.read_text(encoding="utf-8-sig").strip().strip('"')
        c = psycopg2.connect(url, connect_timeout=30, application_name="cc325_utflutt_myndir",
                             keepalives=1, keepalives_idle=60, keepalives_interval=30, keepalives_count=5)
    except (OSError, psycopg2.Error) as e:
        # Hvorki str(e) né strengurinn: aðeins tegund villu.
        skra(f"FALL tenging: {type(e).__name__}; ekkert endurnýjað rc=5")
        return 5

    try:
        try:
            eigandi, notandi = les(c, """SELECT matviewowner, current_user FROM pg_matviews
                                         WHERE schemaname = %s AND matviewname = %s""", (SYN_SKEMA, SYN_NAFN))
        except TypeError:
            skra(f"FALL forathugun: {SYN} finnst ekki; ekkert endurnýjað rc=5")
            return 5
        if eigandi != notandi:
            skra(f"FALL forathugun: eigandi er {eigandi}, tengdur sem {notandi}; ekkert endurnýjað rc=5")
            return 5
        fyrir, = les(c, f"SELECT count(*) FROM {SYN}")
        wal0, = les(c, "SELECT pg_current_wal_lsn()::text")
    except psycopg2.Error as e:
        skra(f"FALL forathugun: {villutexti(e)}; ekkert endurnýjað rc=5")
        return 5

    try:
        sek, lt, st = endurnyja(c)
    except (psycopg2.Error, RuntimeError) as e:
        try:
            c.rollback()
        except psycopg2.Error:
            pass
        skra(f"FALL endurnýjun: {villutexti(e)}; sýnin óbreytt, raðir_fyrir={fyrir} rc=6")
        return 6

    try:
        eftir, = les(c, f"SELECT count(*) FROM {SYN}")
        wal_b, staerd = les(c, "SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), %s::pg_lsn)::bigint, pg_total_relation_size(%s::regclass)",
                            (wal0, SYN))
    except psycopg2.Error as e:
        skra(f"AÐVÖRUN: endurnýjun tókst á {sek:.1f} s en mæling á eftir féll: {villutexti(e)}; raðir_fyrir={fyrir} rc=7")
        return 7
    finally:
        c.close()

    skra(f"LOKIÐ refresh_s={sek:.1f} raðir_fyrir={fyrir} raðir_eftir={eftir} breyting={eftir - fyrir:+d} "
         f"wal_mb_kerfi={wal_b / 1e6:.0f} staerd_mb={staerd / 1e6:.0f} lock_timeout={lt} statement_timeout={st} rc=0")
    return 0


def main():
    # Sjálfgefin kóðasíða stdout fer eftir ræsingu (S4U án leikjatölvu); íslenskur stafur má ekki fella keyrslu.
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--hlid", metavar="HH:MM", help="prófar aðeins banntímahliðið á gefinni klukku; tengist engu")
    r = a.parse_args()
    if r.hlid:
        kl = dt.time.fromisoformat(r.hlid)
        print(f"{kl:%H:%M} {'NEITAR rc=4' if i_banni(kl) else 'leyfir rc=0'}")
        return 4 if i_banni(kl) else 0
    try:
        return keyra()
    except Exception as e:  # Keyrsla án eftirlits: tegund í log, aldrei str(e).
        skra(f"FALL óvænt: {type(e).__name__} rc=9")
        return 9


if __name__ == "__main__":
    sys.exit(main())
