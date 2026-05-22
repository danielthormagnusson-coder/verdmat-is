"""Phase 'evalue-audit' — DB schema + cardinality snapshot (read-only)."""

from __future__ import annotations

import sqlite3
import sys

DB = r"D:\verdmat-is\app\audit\stage_a_augl_staging.db"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = conn.cursor()
    print("== schema for stage_a_augl ==")
    cur.execute("SELECT sql FROM sqlite_master WHERE name='stage_a_augl'")
    print(cur.fetchone()[0])
    print()
    print("== column info ==")
    cur.execute("PRAGMA table_info('stage_a_augl')")
    for r in cur.fetchall():
        print(r)
    print()
    print("== row counts and status distribution ==")
    cur.execute("SELECT count(*) FROM stage_a_augl")
    print("total_rows =", cur.fetchone()[0])
    # Look at status-shaped columns
    cur.execute("PRAGMA table_info('stage_a_augl')")
    cols = [r[1] for r in cur.fetchall()]
    print("columns:", cols)
    # Find columns likely to be HTTP status / outcome
    candidates = [c for c in cols if any(k in c.lower() for k in ("status", "code", "outcome", "result", "http"))]
    print("status_candidate_columns:", candidates)
    for c in candidates:
        try:
            cur.execute(f"SELECT \"{c}\", count(*) FROM stage_a_augl GROUP BY \"{c}\" ORDER BY 2 DESC LIMIT 20")
            print(f"-- distribution of {c} --")
            for r in cur.fetchall():
                print(" ", r)
        except sqlite3.Error as e:
            print(f"  query failed: {e}")
    # Timestamp-shaped columns
    ts_cands = [c for c in cols if any(k in c.lower() for k in ("at", "time", "ts", "fetched", "date"))]
    print("timestamp_candidate_columns:", ts_cands)
    for c in ts_cands:
        try:
            cur.execute(f"SELECT min(\"{c}\"), max(\"{c}\"), count(\"{c}\") FROM stage_a_augl WHERE \"{c}\" IS NOT NULL")
            mn, mx, n = cur.fetchone()
            print(f"  {c}: min={mn}  max={mx}  non_null={n}")
        except sqlite3.Error as e:
            print(f"  {c}: query failed: {e}")
    # If payload-shaped column exists, sample-shape it
    payload_cands = [c for c in cols if any(k in c.lower() for k in ("payload", "body", "response", "json", "data"))]
    print("payload_candidate_columns:", payload_cands)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
