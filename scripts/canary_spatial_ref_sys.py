#!/usr/bin/env python
"""canary_spatial_ref_sys.py — cc55 nightly-chain canary for public.spatial_ref_sys.

Context (docs/RLS_FIX_20260729T075021Z.md §3): anon holds INSERT/UPDATE/DELETE/TRUNCATE
on public.spatial_ref_sys (owner supabase_admin) and a REVOKE run as postgres is a
silent no-op — an anonymous `DELETE ?srid=gt.0` could empty the SRID registry until
Supabase support fixes the grants. The only PostGIS consumer is the generated
`scraper.listings_canonical.geog` column, evaluated on every promote INSERT.

This canary runs at the FRONT of the geog-using link in both nightly chains and
refuses the run (exit != 0) if the table deviates from its shipped state, so the
promote step never computes geog against a wiped/partial SRID registry.

Checks (read-only, one connection, one round-trip):
  rows == 8500          (PostGIS 3.x shipped registry; cc52 measured 8500)
  srid 4326 present     (the one SRID listings_canonical.geog actually uses)

Exit codes: 0 OK · 3 deviation (loud) · 4 cannot connect/query (loud).
"""
from __future__ import annotations

import sys

import psycopg2

EXPECTED_ROWS = 8500
REQUIRED_SRID = 4326
DBCONFIG = r"D:\verdmat-is\.dbconfig"   # utf-8-sig, transaction pooler (port 6543)


def main() -> int:
    try:
        dsn = open(DBCONFIG, encoding="utf-8-sig").read().strip()
        pg = psycopg2.connect(dsn, connect_timeout=30)
        pg.set_session(readonly=True, autocommit=True)
        cur = pg.cursor()
        cur.execute(
            "SELECT count(*), count(*) FILTER (WHERE srid = %s) FROM public.spatial_ref_sys",
            (REQUIRED_SRID,),
        )
        rows, srid_hits = cur.fetchone()
        pg.close()
    except Exception as e:
        print("CANARY FAIL spatial_ref_sys: cannot measure — %s: %s"
              % (type(e).__name__, e), file=sys.stderr)
        print("CANARY FAIL: refusing the run (cannot prove SRID registry intact)",
              file=sys.stderr)
        return 4

    ok = rows == EXPECTED_ROWS and srid_hits == 1
    if ok:
        print("CANARY OK spatial_ref_sys: rows=%d (expected %d), srid %d present"
              % (rows, EXPECTED_ROWS, REQUIRED_SRID))
        return 0

    print("CANARY FAIL spatial_ref_sys: rows=%d (expected %d), srid %d %s"
          % (rows, EXPECTED_ROWS, REQUIRED_SRID,
             "present" if srid_hits == 1 else "MISSING"), file=sys.stderr)
    print("CANARY FAIL: SRID registry deviates from shipped state — anon write "
          "grants on spatial_ref_sys are still open (cc52); geog computation would "
          "produce garbage. ABORTING before any promote write.", file=sys.stderr)
    print("CANARY FAIL: see docs/RLS_FIX_20260729T075021Z.md §3 + the Supabase "
          "support request in docs/fable_prep/.", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
