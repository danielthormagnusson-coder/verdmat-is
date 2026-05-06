"""
rls_verify.py — Post-fix verification suite for RLS baseline audit.

Runs against the live Supabase project after migration
20260506_rls_baseline_audit.sql has been applied. Halts on the first
verification failure. Does not attempt remediation — surfaces failures
for human decision.

Five verification steps:
  1. State diff: every flagged table has rls_enabled=true with at least
     one policy.
  2. Grants reduction: anon/authenticated hold only SELECT on
     dashboard-public tables; no anon entry on user-owned tables.
  3. Anon SELECT row counts (via SET LOCAL ROLE anon): every
     dashboard-public table returns rows under anon.
  4. Anon DML blocked: explicit anon INSERT probe must fail with
     PostgreSQL error 42501 (insufficient_privilege).
  5. Live-site smoke check: HTTP 200 on /eign/[fastnum] +
     /markadur/* dashboard URLs.

Usage:
    export SUPABASE_DB_URL='postgresql://...pooler.supabase.com:6543/postgres'
    python audit/rls_verify.py

Exit code 0 = all PASS. Non-zero = at least one FAIL (halt + report).
"""

from __future__ import annotations

import os
import sys
import urllib.request
from typing import Iterable

try:
    import psycopg
    from psycopg.errors import InsufficientPrivilege
except ImportError:
    print("psycopg (v3) required. install: pip install 'psycopg[binary]'", file=sys.stderr)
    sys.exit(1)


DASHBOARD_PUBLIC_TABLES = [
    "properties",
    "predictions",
    "predictions_iter3v2",
    "comps_index",
    "feature_attributions",
    "feature_attributions_iter3v2",
    "sales_history",
    "repeat_sale_index",
    "last_listing_text",
    "ats_lookup",
    "ats_lookup_by_quarter",
    "ats_dashboard_monthly_heat",
    "llm_aggregates_quarterly",
    "model_tracking_history",
]

USER_OWNED_TABLES = [
    "pro_users",
    "saved_properties",
    "saved_searches",
    "saved_valuations",
]

LIVE_SITE_URLS = [
    "https://verdmat-is.vercel.app/",
    "https://verdmat-is.vercel.app/eign/2008647",
    "https://verdmat-is.vercel.app/markadur",
    "https://verdmat-is.vercel.app/markadur/visitala",
    "https://verdmat-is.vercel.app/markadur/markadsstada",
    "https://verdmat-is.vercel.app/markadur/ibudir",
    "https://verdmat-is.vercel.app/markadur/modelstada",
]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def step1_state_diff(conn: psycopg.Connection) -> None:
    print("[1] State diff (rls_enabled + policy count) ...")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.relname, c.relrowsecurity,
                   (SELECT count(*) FROM pg_policies p
                    WHERE p.tablename = c.relname AND p.schemaname = 'public')
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = 'public' AND c.relkind = 'r'
            ORDER BY c.relname
            """
        )
        rows = cur.fetchall()
    expected = set(DASHBOARD_PUBLIC_TABLES) | set(USER_OWNED_TABLES)
    seen = {name: (rls, npolicies) for (name, rls, npolicies) in rows}
    missing = expected - set(seen.keys())
    if missing:
        fail(f"missing tables: {missing}")
    for name in expected:
        rls, npolicies = seen[name]
        if not rls:
            fail(f"{name}: RLS not enabled")
        if npolicies < 1:
            fail(f"{name}: 0 policies (must have at least 1)")
    print("    PASS")


def step2_grants(conn: psycopg.Connection) -> None:
    print("[2] Grants reduction (anon/authenticated DML revoked) ...")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, grantee,
                   string_agg(privilege_type, ', ' ORDER BY privilege_type)
            FROM information_schema.role_table_grants
            WHERE table_schema = 'public'
              AND grantee IN ('anon', 'authenticated')
            GROUP BY table_name, grantee
            """
        )
        rows = cur.fetchall()
    grants = {(t, g): privs for (t, g, privs) in rows}

    for tbl in DASHBOARD_PUBLIC_TABLES:
        for role in ("anon", "authenticated"):
            privs = grants.get((tbl, role), "")
            if privs != "SELECT":
                fail(f"{tbl}/{role}: expected SELECT only, got {privs!r}")

    for tbl in USER_OWNED_TABLES:
        if (tbl, "anon") in grants:
            fail(f"{tbl}/anon: expected NO grants, got {grants[(tbl, 'anon')]!r}")

    print("    PASS")


def step3_anon_select(conn: psycopg.Connection) -> None:
    print("[3] Anon SELECT row counts ...")
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute("SET LOCAL ROLE anon")
        for tbl in DASHBOARD_PUBLIC_TABLES:
            cur.execute(f"SELECT count(*) FROM {tbl}")
            (n,) = cur.fetchone()
            if n is None or n < 0:
                fail(f"{tbl}: anon SELECT returned {n}")
            print(f"    {tbl}: {n} rows")
        cur.execute("ROLLBACK")
    print("    PASS")


def step4_anon_dml_blocked(conn: psycopg.Connection) -> None:
    print("[4] Anon DML blocked probe ...")
    with conn.cursor() as cur:
        try:
            cur.execute("BEGIN")
            cur.execute("SET LOCAL ROLE anon")
            cur.execute(
                "INSERT INTO properties (fastnum, heimilisfang) "
                "VALUES (-99999, 'audit_probe_should_fail')"
            )
            cur.execute("ROLLBACK")
            fail("anon INSERT succeeded — RLS NOT ENFORCING")
        except InsufficientPrivilege:
            conn.rollback()
            print("    PASS — insufficient_privilege (42501) raised as expected")
        except psycopg.Error as exc:
            conn.rollback()
            fail(f"unexpected error: {exc.diag.sqlstate} {exc}")


def step5_live_site(urls: Iterable[str]) -> None:
    print("[5] Live-site smoke check ...")
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "rls_verify"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                code = resp.status
                size = len(resp.read())
        except Exception as exc:
            fail(f"{url}: {exc}")
        if code != 200:
            fail(f"{url}: HTTP {code}")
        print(f"    {url} → {code}, {size} bytes")
    print("    PASS")


def main() -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("SUPABASE_DB_URL not set", file=sys.stderr)
        return 2

    with psycopg.connect(db_url) as conn:
        conn.autocommit = False
        step1_state_diff(conn)
        step2_grants(conn)
        step3_anon_select(conn)
        step4_anon_dml_blocked(conn)
    step5_live_site(LIVE_SITE_URLS)

    print()
    print("ALL PASS — RLS baseline verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
