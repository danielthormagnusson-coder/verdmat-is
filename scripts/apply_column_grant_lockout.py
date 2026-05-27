"""Phase X Group B column-grant lockout — apply Stage 1 + Stage 2.

Reads the 2 migration SQL files, applies them sequentially with
sanity-check gates between Stage 1 and Stage 2.

Stage 1: properties (44-col allowlist; 3 cols excluded).
Stage 2: predictions, repeat_sale_index, ats_lookup (all-cols; default-deny
         on future columns).

Sanity per stage:
  - SET LOCAL ROLE anon; SELECT count(*) FROM v_*; matches baseline.
  - Stage 1 only: SELECT landeign_nr FROM properties LIMIT 1 → must 42501.

If any sanity fails → ROLLBACK by re-GRANT table-level SELECT and STOP.

NOTE (Phase X Group C, 2026-05-27): future analogue scripts should import
the reusable patterns from `scripts/migration_helpers.py`:
  - column_grant_lockout()      replaces the per-table REVOKE+GRANT block
  - apply_migration_sql()       replaces apply_sql_file()
  - set_local_role_and_test()   replaces anon_view_count + anon_should_42501
  - open_connection()           replaces get_conn()
This file was committed before the helpers module landed; left as-is to
preserve the audit trail of the 2026-05-27 lockout apply.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import psycopg2
from psycopg2 import errors as pg_errors

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

MIGRATIONS = Path(r"D:\verdmat-is\app\supabase\migrations")
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")

STAGE1 = MIGRATIONS / "20260527150435_column_grant_lockout_stage1_properties.sql"
STAGE2 = MIGRATIONS / "20260527150436_column_grant_lockout_stage2_other3.sql"


def section(t):
    print()
    print("=" * 70)
    print(t)
    print("=" * 70)


def get_conn():
    url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn


def baseline_counts(conn) -> dict:
    out = {}
    with conn.cursor() as cur:
        for v in ("v_properties", "v_current_predictions",
                  "v_repeat_sale_index", "v_ats_lookup_by_heat"):
            cur.execute(f"SELECT count(*) FROM public.{v}")
            out[v] = cur.fetchone()[0]
    conn.rollback()
    return out


def anon_view_count(conn, view: str) -> int | None:
    with conn.cursor() as cur:
        try:
            cur.execute("SET LOCAL ROLE anon")
            cur.execute(f"SELECT count(*) FROM public.{view}")
            n = cur.fetchone()[0]
        except Exception as e:
            print(f"  ERROR as anon on {view}: {type(e).__name__}: {e}")
            n = None
        finally:
            conn.rollback()
    return n


def anon_should_42501(conn, sql: str) -> tuple[bool, str]:
    """Run `sql` as anon role inside a transaction. Returns (got_42501, msg).
    Intended only for sanity probes; the txn is always rolled back."""
    with conn.cursor() as cur:
        try:
            cur.execute("SET LOCAL ROLE anon")
            cur.execute(sql)
        except pg_errors.InsufficientPrivilege as e:
            conn.rollback()
            return True, str(e).strip().split("\n")[0]
        except Exception as e:
            conn.rollback()
            return False, f"unexpected {type(e).__name__}: {e}"
        else:
            conn.rollback()
            return False, "NO ERROR — exclusion FAILED"


def apply_sql_file(conn, path: Path) -> bool:
    sql = path.read_text(encoding="utf-8")
    print(f"  applying {path.name} ({len(sql):,} bytes)")
    with conn.cursor() as cur:
        try:
            cur.execute(sql)
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            conn.rollback()
            return False
    conn.commit()
    return True


def rollback_stage1(conn):
    """Emergency: re-GRANT table-level SELECT on properties."""
    print("\nROLLING BACK Stage 1 ...")
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute("GRANT SELECT ON public.properties TO anon")
        cur.execute("GRANT SELECT ON public.properties TO authenticated")
        cur.execute("COMMIT")
    print("  table-level GRANTs restored")


def main() -> int:
    if not STAGE1.exists() or not STAGE2.exists():
        print(f"ERROR: missing migration files")
        return 2

    conn = get_conn()

    section("Baseline counts (pre-lockout)")
    base = baseline_counts(conn)
    for v, n in base.items():
        print(f"  {v:<26s} {n:>7,}")

    # ============================================================
    # STAGE 1 — properties
    # ============================================================
    section("STAGE 1 — public.properties (44-col allowlist)")
    if not apply_sql_file(conn, STAGE1):
        print("STAGE 1 APPLY FAILED")
        return 3

    # Sanity 1: v_properties count unchanged under anon
    print("\nSanity: SET LOCAL ROLE anon; SELECT count(*) FROM v_properties ...")
    n = anon_view_count(conn, "v_properties")
    if n != base["v_properties"]:
        print(f"  FAIL: anon count = {n!r}, expected {base['v_properties']:,}")
        rollback_stage1(conn)
        return 4
    print(f"  PASS: {n:,} (matches baseline)")

    # Sanity 2: 42501 on excluded column landeign_nr
    print("\nSanity: SET LOCAL ROLE anon; SELECT landeign_nr FROM properties LIMIT 1 ...")
    got_42501, msg = anon_should_42501(
        conn, "SELECT landeign_nr FROM public.properties LIMIT 1"
    )
    if not got_42501:
        print(f"  FAIL — exclusion not enforced: {msg}")
        rollback_stage1(conn)
        return 5
    print(f"  PASS: 42501 raised — {msg}")

    # Sanity 2b: 42501 on the other 2 excluded columns
    for col in ("matseiningar", "tengd_stadfang_nr"):
        got, msg = anon_should_42501(
            conn, f"SELECT {col} FROM public.properties LIMIT 1"
        )
        marker = "PASS" if got else "FAIL"
        print(f"    {col:<22s} {marker}: {msg}")
        if not got:
            rollback_stage1(conn)
            return 6

    # Sanity 3: confirm anon can still read the INCLUDED augl_id_latest column
    # (intentional — Bug 26 fix is SSR deep-link, not column-strip)
    print("\nSanity: SET LOCAL ROLE anon; SELECT augl_id_latest FROM properties LIMIT 1 ...")
    with conn.cursor() as cur:
        try:
            cur.execute("SET LOCAL ROLE anon")
            cur.execute("SELECT augl_id_latest FROM public.properties "
                        "WHERE augl_id_latest IS NOT NULL LIMIT 1")
            r = cur.fetchone()
            print(f"  PASS: anon can read augl_id_latest (sample: {r[0]})")
        except Exception as e:
            print(f"  FAIL: {type(e).__name__}: {e}")
            rollback_stage1(conn)
            return 7
        finally:
            conn.rollback()

    print("\nSTAGE 1 GREEN.")

    # ============================================================
    # STAGE 2 — predictions, repeat_sale_index, ats_lookup
    # ============================================================
    section("STAGE 2 — predictions, repeat_sale_index, ats_lookup (all-cols)")
    if not apply_sql_file(conn, STAGE2):
        print("STAGE 2 APPLY FAILED")
        return 8

    # Per-table sanity: view counts unchanged
    for view in ("v_current_predictions",
                 "v_repeat_sale_index",
                 "v_ats_lookup_by_heat"):
        n = anon_view_count(conn, view)
        if n != base[view]:
            print(f"  FAIL: {view} anon count = {n!r}, expected {base[view]:,}")
            return 9
        print(f"  PASS: {view:<26s} {n:>7,} (matches baseline)")

    print("\nSTAGE 2 GREEN.")

    # ============================================================
    # Final state — column-level grants in place
    # ============================================================
    section("Final per-table grant state")
    with conn.cursor() as cur:
        for t in ("properties", "predictions", "repeat_sale_index", "ats_lookup"):
            cur.execute("""
                SELECT count(*)
                FROM information_schema.role_table_grants
                WHERE grantee=%s AND table_schema='public' AND table_name=%s
                  AND privilege_type='SELECT'
            """, ("anon", t))
            n_table = cur.fetchone()[0]
            cur.execute("""
                SELECT count(*)
                FROM information_schema.role_column_grants
                WHERE grantee=%s AND table_schema='public' AND table_name=%s
                  AND privilege_type='SELECT'
            """, ("anon", t))
            n_col = cur.fetchone()[0]
            print(f"  {t:<22s} anon: table-level={n_table}  column-level={n_col}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
