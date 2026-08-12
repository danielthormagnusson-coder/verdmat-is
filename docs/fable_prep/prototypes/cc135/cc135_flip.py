# -*- coding: utf-8 -*-
"""
cc135_flip.py — ATÓMÍSKT FLIPP staging -> live á valuation_tiers_rent (cc135 liður 5).

KEYRIST AÐEINS EFTIR GO. Krefst --go til að skrifa; án þess er hún þurr-keyrsla
sem mælir hliðin og skrifar ekkert.

HVERS VEGNA TRUNCATE+INSERT OG EKKI RENAME (öfugt við cc30-flippið):
  Lifandi taflan ber RLS + policy `public_read` + GRANT SELECT á anon/authenticated
  (migration 20260719). RENAME færir þau með sér en skilur eftir nafnaflækju —
  cc30 endurnefndi þegar staging -> live og vísirinn `valuation_tiers_rent_staging_pkey`
  hangir enn á lifandi töflunni út af því. TRUNCATE+INSERT í EINNI txn heldur
  töflunni, þvingunum, RLS, policy og grants ÓBREYTTUM og er jafn atómískt:
  TRUNCATE tekur ACCESS EXCLUSIVE, svo lesandi sér aldrei hálft sett — hann bíður.

Öll hlið eru INNAN txn: falli eitt, rúllar allt til baka og taflan stendur óbreytt.
Snapshot valuation_tiers_rent_pre_cc135 STENDUR sem rollback-grunnur
(app/scripts/valuation_tiers_rent_rollback_cc135.sql).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import psycopg2

sys.stdout.reconfigure(encoding="utf-8")

DSN = Path(r"D:\verdmat-is\.dbconfig").read_text(encoding="utf-8-sig").strip()
COLS = ("fastnum,threp,flokkur,t5_astaeda,n_local,n_conformal,fallback_lvl,"
        "herb_vantar,pi80_pct,segment,canonical_code")

# Vænt tölur, mældar á staging 2026-08-12 (cc135_parity.py). Flippið fellur sjálft
# frekar en að skila öðru setti en það sem borðið samþykkti.
VAENT = {"n": 158314, 1: 32526, 2: 71560, 3: 20972, 4: 19161, 5: 14095}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="framkvæma flippið (annars þurrt)")
    a = ap.parse_args()

    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()

    # ---- forkröfur: snapshot til, staging til og rétt ----
    cur.execute("SELECT to_regclass('public.valuation_tiers_rent_pre_cc135')")
    if cur.fetchone()[0] is None:
        raise SystemExit("HALT: snapshot valuation_tiers_rent_pre_cc135 vantar — engin flipp án rollback-grunns.")
    cur.execute("SELECT count(*) FROM public.valuation_tiers_rent_staging")
    n_stg = cur.fetchone()[0]
    if n_stg != VAENT["n"]:
        raise SystemExit(f"HALT: staging ber {n_stg:,} raðir, vænt {VAENT['n']:,}.")
    cur.execute("""SELECT count(*) FROM public.valuation_tiers_rent_staging s
                   JOIN public.properties p USING (fastnum)
                   WHERE s.canonical_code IS DISTINCT FROM p.canonical_code""")
    if (m := cur.fetchone()[0]):
        raise SystemExit(f"HALT: staging<->properties canonical-mismunur {m} — ekki flippa stöðnuðu lagi.")
    log(f"forkröfur OK: staging {n_stg:,} raðir, canonical-mismunur 0, snapshot til")

    if not a.go:
        conn.rollback()
        conn.close()
        log("ÞURR KEYRSLA — ekkert skrifað. --go til að flippa.")
        return

    try:
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("SET LOCAL statement_timeout = '600s'")
        cur.execute("TRUNCATE public.valuation_tiers_rent")
        cur.execute(f"INSERT INTO public.valuation_tiers_rent ({COLS}) "
                    f"SELECT {COLS} FROM public.valuation_tiers_rent_staging")
        log(f"INSERT: {cur.rowcount:,} raðir")

        # ---- postverify INNAN txn ----
        cur.execute("SELECT count(*) FROM public.valuation_tiers_rent")
        n = cur.fetchone()[0]
        cur.execute("SELECT threp, count(*) FROM public.valuation_tiers_rent GROUP BY 1 ORDER BY 1")
        dist = dict(cur.fetchall())
        cur.execute("""SELECT count(*) FROM public.valuation_tiers_rent v
                       JOIN public.properties p USING (fastnum)
                       WHERE v.canonical_code IS DISTINCT FROM p.canonical_code""")
        ccm = cur.fetchone()[0]
        cur.execute("""SELECT count(*) FROM public.valuation_tiers_rent v
                       LEFT JOIN public.properties p USING (fastnum)
                       WHERE p.fastnum IS NULL""")
        orph = cur.fetchone()[0]
        # bæti-fyrir-bæti gegn staging (öll 11 gildi, ekki bara tölurnar)
        cur.execute(f"""SELECT count(*) FROM (
                          SELECT {COLS} FROM public.valuation_tiers_rent
                          EXCEPT SELECT {COLS} FROM public.valuation_tiers_rent_staging) d""")
        diff = cur.fetchone()[0]
        cur.execute("""SELECT count(*) FROM pg_policies WHERE schemaname='public'
                       AND tablename='valuation_tiers_rent'""")
        pol = cur.fetchone()[0]
        cur.execute("""SELECT count(*) FROM information_schema.role_table_grants
                       WHERE table_schema='public' AND table_name='valuation_tiers_rent'
                         AND grantee IN ('anon','authenticated') AND privilege_type='SELECT'""")
        gr = cur.fetchone()[0]
        cur.execute("SELECT relrowsecurity FROM pg_class WHERE oid='public.valuation_tiers_rent'::regclass")
        rls = cur.fetchone()[0]

        log(f"postverify: n={n:,}  threp={dist}")
        log(f"postverify: canonical-mismunur={ccm}  orphans={orph}  EXCEPT-diff={diff}")
        log(f"postverify: rls={rls}  policies={pol}  SELECT-grants={gr}")

        brot = []
        if n != VAENT["n"]:
            brot.append(f"rowcount {n} != {VAENT['n']}")
        for t in (1, 2, 3, 4, 5):
            if dist.get(t) != VAENT[t]:
                brot.append(f"T{t} {dist.get(t)} != {VAENT[t]}")
        if ccm:
            brot.append(f"canonical-mismunur {ccm}")
        if orph:
            brot.append(f"orphans {orph}")
        if diff:
            brot.append(f"EXCEPT-diff {diff}")
        if not rls:
            brot.append("RLS AF")
        if pol != 1:
            brot.append(f"policies {pol} != 1 (public_read)")
        if gr != 2:
            brot.append(f"SELECT-grants {gr} != 2 (anon+authenticated)")
        if brot:
            conn.rollback()
            raise SystemExit("FLIPP ROLLBACK — brotin hlið: " + "; ".join(brot))

        conn.commit()
        log("FLIPP COMMIT — postverify PASS á öllum hliðum")
        log("snapshot valuation_tiers_rent_pre_cc135 STENDUR sem rollback-grunnur")
        log("ATH: /leiguverd les cachaða farminn (unstable_cache, TTL 600 s) — "
            "þrepið þar uppfærist innan 10 mín. /leiga/[id] er ferskt.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
