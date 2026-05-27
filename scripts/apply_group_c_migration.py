"""apply_group_c_migration.py — apply 20260527155123_group_c_audit_tables.sql
to Supabase prod and run post-apply verification.

If any verification fails, rolls back by DROP TABLE on the 3 tables. Nothing
else has been touched yet (this migration is purely net-new).

Idempotency note: the migration uses plain CREATE TABLE (not CREATE TABLE
IF NOT EXISTS). Re-applying after success would fail at "relation already
exists". For first-apply, the script aborts if any of the 3 tables already
exists in public schema.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
sys.path.insert(0, str(Path(__file__).parent))

from migration_helpers import open_connection, apply_migration_sql  # noqa: E402

MIGRATION = Path(
    r"D:\verdmat-is\app\supabase\migrations\20260527155123_group_c_audit_tables.sql"
)
TABLES = ("pipeline_runs", "pipeline_steps", "inputs_snapshots")
EXPECTED_INDEXES = {
    "pipeline_runs_started_idx",
    "pipeline_runs_run_type_idx",
    "pipeline_steps_run_id_idx",
    "pipeline_steps_step_name_idx",
    "inputs_snapshots_run_id_idx",
    "inputs_snapshots_model_cal_idx",
}


def section(t):
    print()
    print("=" * 70)
    print(t)
    print("=" * 70)


def preflight(conn) -> bool:
    """Abort if any target table already exists."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' AND table_name = ANY(%s)
            """,
            (list(TABLES),),
        )
        existing = [r[0] for r in cur.fetchall()]
    if existing:
        print(f"  ABORT: tables already exist: {existing}")
        return False
    print(f"  preflight ok: none of {TABLES} exist in public schema")
    return True


def drop_tables(conn) -> None:
    """Emergency rollback — DROP TABLE the 3 in CASCADE order."""
    with conn.cursor() as cur:
        cur.execute(
            "DROP TABLE IF EXISTS "
            "public.inputs_snapshots, public.pipeline_steps, public.pipeline_runs "
            "CASCADE"
        )
    conn.commit()
    print("  rolled back: DROP TABLE × 3 (CASCADE)")


def verify(conn) -> tuple[bool, list[str]]:
    """Run all post-apply checks. Returns (all_ok, failure_messages)."""
    failures = []

    # 1. All 3 tables exist + correct column counts
    print("\n  table existence + column counts:")
    expected_cols = {"pipeline_runs": 8, "pipeline_steps": 12, "inputs_snapshots": 20}
    with conn.cursor() as cur:
        for t in TABLES:
            cur.execute(
                """
                SELECT count(*) FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                """,
                (t,),
            )
            n = cur.fetchone()[0]
            ok = n == expected_cols[t]
            print(f"    public.{t:<22s} cols={n:>2d} (expected {expected_cols[t]})  "
                  f"{'OK' if ok else 'FAIL'}")
            if not ok:
                failures.append(f"{t}: {n} cols, expected {expected_cols[t]}")

    # 2. RLS enabled on each
    print("\n  RLS enabled (relrowsecurity=t):")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.relname, c.relrowsecurity
            FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
            WHERE n.nspname='public' AND c.relname = ANY(%s)
            ORDER BY c.relname
            """,
            (list(TABLES),),
        )
        for r in cur.fetchall():
            ok = r[1] is True
            print(f"    public.{r[0]:<22s} rls={r[1]}  {'OK' if ok else 'FAIL'}")
            if not ok:
                failures.append(f"{r[0]}: RLS not enabled")

    # 3. 0 anon + 0 authenticated SELECT grants
    print("\n  anon + authenticated SELECT grants (must all be 0):")
    with conn.cursor() as cur:
        for role in ("anon", "authenticated"):
            for t in TABLES:
                cur.execute(
                    """
                    SELECT count(*)
                    FROM information_schema.role_table_grants
                    WHERE grantee=%s AND table_schema='public'
                      AND table_name=%s AND privilege_type='SELECT'
                    """,
                    (role, t),
                )
                n = cur.fetchone()[0]
                ok = n == 0
                print(f"    {role:<15s} {t:<22s} = {n}  {'OK' if ok else 'FAIL'}")
                if not ok:
                    failures.append(f"{role} has {n} SELECT grants on {t}")

    # 4. 6 indexes
    print("\n  expected indexes:")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE schemaname='public' AND tablename = ANY(%s)
            ORDER BY indexname
            """,
            (list(TABLES),),
        )
        actual = {r[0] for r in cur.fetchall()}
    for idx in sorted(EXPECTED_INDEXES):
        present = idx in actual
        print(f"    {idx:<40s} {'OK' if present else 'MISSING'}")
        if not present:
            failures.append(f"index missing: {idx}")
    # PK indexes are auto-created; show but don't gate on them
    pk_actual = actual - EXPECTED_INDEXES
    if pk_actual:
        print(f"    (+ PK/auto indexes: {sorted(pk_actual)})")

    # 5. service_role can SELECT cleanly (no 42501)
    print("\n  service_role SELECT smoke (must return 0 rows cleanly):")
    for t in TABLES:
        try:
            with conn.cursor() as cur:
                cur.execute(f"SET LOCAL ROLE service_role")
                cur.execute(f"SELECT count(*) FROM public.{t}")
                n = cur.fetchone()[0]
        except Exception as e:
            conn.rollback()
            print(f"    public.{t:<22s} FAIL: {type(e).__name__}: {e}")
            failures.append(f"service_role SELECT failed on {t}: {e}")
            continue
        finally:
            try:
                conn.rollback()  # unwind SET LOCAL ROLE
            except Exception:
                pass
        print(f"    public.{t:<22s} count={n}  OK")

    return (len(failures) == 0), failures


def main() -> int:
    if not MIGRATION.exists():
        print(f"ERROR: migration not found at {MIGRATION}")
        return 2

    conn = open_connection()

    section("Preflight")
    if not preflight(conn):
        conn.close()
        return 3

    section("Apply migration")
    ok, rowcount, msg = apply_migration_sql(conn, MIGRATION)
    if not ok:
        print(f"  APPLY FAILED: {msg}")
        conn.close()
        return 4
    conn.commit()
    print(f"  {msg}  (committed)")

    section("Verify")
    all_ok, failures = verify(conn)

    if not all_ok:
        print("\n*** VERIFY FAILED — rolling back ***")
        for f in failures:
            print(f"    {f}")
        drop_tables(conn)
        conn.close()
        return 5

    print("\n*** ALL CHECKS GREEN ***")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
