# -*- coding: utf-8 -*-
"""
cc135_freeze.py — FRYSTING fyrir leigu-threpa-endurbygginguna (cc135 lidur 1).

Snapshot-ar valuation_tiers_rent i valuation_tiers_rent_pre_cc135 (CREATE TABLE AS
+ RLS default-deny + REVOKE i SOMU txn — CLAUDE.md reglan), maelir rowcount +
checksum a badum hlidum, og skrifar rollback-SQL a disk FYRIR framkvaemd.

NEITAR ad yfirskrifa snapshot sem er til (flip_iter4r / cc131 mynstrid).
Rollback: app/scripts/valuation_tiers_rent_rollback_cc135.sql (TRUNCATE + INSERT).
"""
import sys
import time
from pathlib import Path

import psycopg2

sys.stdout.reconfigure(encoding="utf-8")

TABLES = ["valuation_tiers_rent"]
CHECKSUMS = {
    "valuation_tiers_rent": ("count(*), sum(threp), sum(n_local), sum(pi80_pct), "
                             "count(*) filter (where threp=1), "
                             "count(*) filter (where threp=5), "
                             "count(distinct canonical_code), count(distinct segment)"),
}
ROLLBACK_SQL = Path(r"D:\verdmat-is\app\scripts\valuation_tiers_rent_rollback_cc135.sql")


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    dsn = Path(r"D:\verdmat-is\.dbconfig").read_text(encoding="utf-8-sig").strip()
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()

    for t in TABLES:
        cur.execute("SELECT to_regclass(%s)", (f"public.{t}_pre_cc135",))
        if cur.fetchone()[0] is not None:
            raise SystemExit(f"HALT: {t}_pre_cc135 er til - aldrei yfirskrifa rollback-grunn.")

    cur.execute("BEGIN")
    cur.execute("SET TRANSACTION READ WRITE")
    cur.execute("SET LOCAL statement_timeout = '600s'")
    for t in TABLES:
        snap = f"{t}_pre_cc135"
        cur.execute(f"CREATE TABLE public.{snap} AS SELECT * FROM public.{t}")
        cur.execute(f"ALTER TABLE public.{snap} ENABLE ROW LEVEL SECURITY")
        cur.execute(f"REVOKE ALL ON public.{snap} FROM anon, authenticated")
        log(f"snapshot {snap}: {cur.rowcount if cur.rowcount != -1 else '?'} radir")
    conn.commit()
    log("snapshot-txn COMMIT")

    ok = True
    for t in TABLES:
        cur.execute(f"SELECT {CHECKSUMS[t]} FROM public.{t}")
        live = cur.fetchone()
        cur.execute(f"SELECT {CHECKSUMS[t]} FROM public.{t}_pre_cc135")
        snap = cur.fetchone()
        match = live == snap
        ok &= match
        log(f"checksum {t}:")
        log(f"  live = {live}")
        log(f"  snap = {snap}   {'OK' if match else 'MISMATCH!'}")

    # RLS/grant-sonnun a snapshotinu (relacl er eina grantor-maelingin, cc105)
    for t in TABLES:
        cur.execute("SELECT relrowsecurity, coalesce(relacl::text,'(null)') "
                    "FROM pg_class WHERE oid = %s::regclass", (f"public.{t}_pre_cc135",))
        rls, acl = cur.fetchone()
        log(f"{t}_pre_cc135: rls={rls}  relacl={acl}")
        if not rls:
            ok = False
            log("  RLS EKKI KVEIKT - ekki treystandi")
        if "anon" in acl or "authenticated" in acl:
            ok = False
            log("  ANON/AUTHENTICATED ENN I relacl - REVOKE beit ekki")

    lines = ["-- valuation_tiers_rent_rollback_cc135.sql - aefdur bakleikur (cc135)",
             "-- Keyrist i EINNI txn; replica-mode svo FK trufli ekki rodina.",
             "BEGIN;", "SET TRANSACTION READ WRITE;",
             "SET LOCAL session_replication_role = 'replica';"]
    for t in TABLES:
        lines += [f"TRUNCATE public.{t};",
                  f"INSERT INTO public.{t} SELECT * FROM public.{t}_pre_cc135;"]
    lines += ["COMMIT;"]
    ROLLBACK_SQL.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"rollback-SQL -> {ROLLBACK_SQL}")

    conn.close()
    if not ok:
        raise SystemExit("FRYSTING EKKI TREYSTANDI - sja MISMATCH/RLS ad ofan")
    log("FRYSTING LOKID - allt OK")


if __name__ == "__main__":
    main()
