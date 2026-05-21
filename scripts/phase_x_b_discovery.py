"""Phase X Group B — Step 1.2 discovery (read-only).

Reads remote schema_migrations + properties columns via the pooler URI in
D:\\verdmat-is\\.dbconfig. Emits a structured report to stdout. No writes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg2

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
LOCAL_MIG_DIR = Path(r"D:\verdmat-is\app\supabase\migrations")


def load_dburi() -> str:
    return DBCONFIG.read_text(encoding="utf-8-sig").strip()


def main() -> int:
    dburi = load_dburi()
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 70)
    print("LOCAL MIGRATION FILES")
    print("=" * 70)
    local_files = sorted(LOCAL_MIG_DIR.glob("*.sql"))
    for p in local_files:
        print(f"  {p.name}  ({p.stat().st_size} bytes)")

    with psycopg2.connect(dburi) as conn, conn.cursor() as cur:
        print()
        print("=" * 70)
        print("REMOTE supabase_migrations.schema_migrations")
        print("=" * 70)
        cur.execute(
            """
            SELECT version, name,
                   COALESCE(array_length(statements, 1), 0) AS n_stmts,
                   length(array_to_string(statements, E'\n')) AS total_chars
              FROM supabase_migrations.schema_migrations
             ORDER BY version
            """
        )
        remote_rows = cur.fetchall()
        for version, name, n_stmts, total_chars in remote_rows:
            print(f"  {version}  name={name!r:40s}  stmts={n_stmts}  chars={total_chars}")

        print()
        print("=" * 70)
        print("PUBLIC.PROPERTIES — information_schema.columns")
        print("=" * 70)
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable
              FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'properties'
             ORDER BY ordinal_position
            """
        )
        cols = cur.fetchall()
        print(f"  total_columns={len(cols)}")
        for c, t, n in cols:
            print(f"    {c:40s} {t:25s} nullable={n}")

        print()
        print("=" * 70)
        print("HMS-COLUMN PRESENCE CHECK (vs 20260518_hms_columns.sql)")
        print("=" * 70)
        hms_expected = [
            "brunabotamat",
            "lhlmat",
            "fasteignamat_naesta_ar",
            "landeign_nr",
            "tengd_stadfang_nr",
            "notkunareiningar",
            "matseiningar",
            "byggingarstig",
            "skodags",
            "gerd",
            "matsstig",
            "deregistered",
        ]
        present_cols = {c for c, _, _ in cols}
        for h in hms_expected:
            mark = "OK" if h in present_cols else "MISSING"
            print(f"  [{mark:7s}] {h}")

        print()
        print("=" * 70)
        print("SEMANTIC CORRESPONDENCE — local-file SQL vs remote statements")
        print("=" * 70)
        for p in local_files:
            local_text = p.read_text(encoding="utf-8", errors="replace")
            # Try to match by matching a non-trivial signature string against any remote row's statements
            cur.execute(
                """
                SELECT version, name
                  FROM supabase_migrations.schema_migrations
                 WHERE array_to_string(statements, E'\n') ILIKE %s
                 ORDER BY version
                """,
                ("%" + (local_text.strip().split("\n", 1)[0][:80] if local_text.strip() else "") + "%",),
            )
            matches = cur.fetchall()
            # Fallback signature: pick a unique-ish object name from the file
            sig = None
            for line in local_text.splitlines():
                line = line.strip()
                if line.upper().startswith(("CREATE TABLE", "ALTER TABLE", "CREATE VIEW", "CREATE INDEX", "CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", "GRANT", "REVOKE", "ENABLE ROW LEVEL")):
                    sig = line[:120]
                    break
            sig_matches = []
            if sig:
                cur.execute(
                    """
                    SELECT version, name
                      FROM supabase_migrations.schema_migrations
                     WHERE array_to_string(statements, E'\n') ILIKE %s
                     ORDER BY version
                    """,
                    ("%" + sig + "%",),
                )
                sig_matches = cur.fetchall()
            print(f"  LOCAL {p.name}")
            print(f"    first-line matches: {len(matches)} -> {[m[0] for m in matches]}")
            print(f"    signature line: {sig!r}")
            print(f"    sig matches:    {len(sig_matches)} -> {[m[0] for m in sig_matches]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
