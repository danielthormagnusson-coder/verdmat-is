"""Phase X Group B Part 2 — verification of views layer.

Confirms each of the 4 views:
  * exists in public schema
  * has security_invoker=on in reloptions
  * has SELECT grants to anon AND authenticated
  * returns a sensible row count
And for v_current_predictions specifically, that count = count(DISTINCT fastnum)
in predictions.
"""

from __future__ import annotations

import sys

import psycopg2

VIEWS = [
    "v_properties",
    "v_repeat_sale_index",
    "v_ats_lookup_by_heat",
    "v_current_predictions",
]


def main() -> int:
    uri = open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read().strip()
    sys.stdout.reconfigure(encoding="utf-8")

    with psycopg2.connect(uri) as conn, conn.cursor() as cur:
        print("=" * 70)
        print("VIEW EXISTENCE + reloptions (security_invoker)")
        print("=" * 70)
        cur.execute(
            """
            SELECT n.nspname, c.relname, c.relkind, c.reloptions
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public'
               AND c.relname = ANY(%s)
             ORDER BY c.relname
            """,
            (VIEWS,),
        )
        seen = set()
        for nspname, relname, relkind, reloptions in cur.fetchall():
            seen.add(relname)
            kind = {"v": "view", "m": "materialized_view", "r": "table"}.get(relkind, relkind)
            si_ok = bool(reloptions) and any("security_invoker=on" in r for r in reloptions)
            print(f"  {relname:28s} kind={kind:6s} reloptions={reloptions} "
                  f"security_invoker={'OK' if si_ok else 'FAIL'}")
        missing = [v for v in VIEWS if v not in seen]
        if missing:
            print(f"  MISSING VIEWS: {missing}")

        print()
        print("=" * 70)
        print("GRANTS to anon + authenticated")
        print("=" * 70)
        cur.execute(
            """
            SELECT table_name, grantee, privilege_type
              FROM information_schema.role_table_grants
             WHERE table_schema = 'public'
               AND table_name = ANY(%s)
               AND grantee IN ('anon', 'authenticated')
             ORDER BY table_name, grantee
            """,
            (VIEWS,),
        )
        grants = cur.fetchall()
        by_view = {}
        for tn, grantee, priv in grants:
            by_view.setdefault(tn, []).append((grantee, priv))
        for v in VIEWS:
            entries = by_view.get(v, [])
            anon_ok = any(g == "anon" and p == "SELECT" for g, p in entries)
            auth_ok = any(g == "authenticated" and p == "SELECT" for g, p in entries)
            print(f"  {v:28s} anon_SELECT={'OK' if anon_ok else 'FAIL'} "
                  f"authenticated_SELECT={'OK' if auth_ok else 'FAIL'} "
                  f"entries={entries}")

        print()
        print("=" * 70)
        print("ROW COUNTS")
        print("=" * 70)
        cur.execute("SELECT count(*) FROM public.properties")
        n_props = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM public.properties WHERE deregistered IS TRUE")
        n_ghosts = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM public.v_properties")
        n_v_props = cur.fetchone()[0]
        print(f"  properties total          = {n_props}")
        print(f"  properties deregistered   = {n_ghosts}")
        print(f"  v_properties              = {n_v_props}  "
              f"(expect {n_props - n_ghosts}, "
              f"match={'OK' if n_v_props == n_props - n_ghosts else 'FAIL'})")

        cur.execute("SELECT count(*) FROM public.repeat_sale_index")
        n_rsi_t = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM public.v_repeat_sale_index")
        n_rsi_v = cur.fetchone()[0]
        print(f"  repeat_sale_index table   = {n_rsi_t}")
        print(f"  v_repeat_sale_index       = {n_rsi_v}  "
              f"(match={'OK' if n_rsi_t == n_rsi_v else 'FAIL'})")

        cur.execute("SELECT count(*) FROM public.ats_lookup")
        n_ats_t = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM public.v_ats_lookup_by_heat")
        n_ats_v = cur.fetchone()[0]
        print(f"  ats_lookup table          = {n_ats_t}")
        print(f"  v_ats_lookup_by_heat      = {n_ats_v}  "
              f"(match={'OK' if n_ats_t == n_ats_v else 'FAIL'})")

        cur.execute("SELECT count(*) FROM public.predictions")
        n_pred_t = cur.fetchone()[0]
        cur.execute("SELECT count(DISTINCT fastnum) FROM public.predictions")
        n_pred_distinct = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM public.v_current_predictions")
        n_pred_v = cur.fetchone()[0]
        print(f"  predictions total         = {n_pred_t}")
        print(f"  predictions distinct fast = {n_pred_distinct}")
        print(f"  v_current_predictions     = {n_pred_v}  "
              f"(expect {n_pred_distinct}, "
              f"match={'OK' if n_pred_v == n_pred_distinct else 'FAIL'})")

        print()
        print("=" * 70)
        print("ANON-ROLE PROBE (simulated): SET LOCAL ROLE anon + SELECT 1 from each view")
        print("=" * 70)
        for v in VIEWS:
            try:
                cur.execute("BEGIN")
                cur.execute("SET LOCAL ROLE anon")
                cur.execute(f"SELECT count(*) FROM public.{v}")
                cnt = cur.fetchone()[0]
                cur.execute("ROLLBACK")
                print(f"  anon SELECT count(*) FROM {v:28s} -> {cnt} OK")
            except Exception as e:
                cur.execute("ROLLBACK")
                print(f"  anon SELECT count(*) FROM {v:28s} -> FAIL {e!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
