"""
rls_sweep.py — Read-only RLS audit of Supabase verdmat-is public schema.

Per SCRAPER_SPEC_v1 §3.3 pattern: RLS enabled by default, public SELECT
via view or explicit policy, service-role bypass for writes.

Reads the production Supabase project via the transaction pooler (port
6543, IPv4-routable per memory note "Supabase direct db hostname is
IPv6-only — use transaction pooler URI for external scripts").

Outputs:
    audit/rls_sweep_report.md   — prose report for human review
    audit/rls_sweep_raw.json    — structured dump for downstream scripting

Usage:
    export SUPABASE_DB_URL='postgresql://...pooler.supabase.com:6543/postgres'
    python audit/rls_sweep.py

Read-only. Does not modify state. Safe to re-run.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import psycopg
except ImportError:
    print("psycopg (v3) required. install: pip install 'psycopg[binary]'", file=sys.stderr)
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "audit"

# Categorization heuristic per task spec. Override in this dict if a
# table needs different treatment than the heuristic assigns.
DASHBOARD_PUBLIC = {
    "properties",
    "predictions",
    "predictions_iter3v2",
    "predictions_iter4",
    "comps_index",
    "feature_attributions",
    "feature_attributions_iter3v2",
    "feature_attributions_iter4",
    "sales_history",
    "repeat_sale_index",
    "last_listing_text",
    "ats_lookup",
    "ats_lookup_by_quarter",
    "ats_lookup_by_heat",
    "ats_dashboard_monthly_heat",
    "ats_dashboard_quarterly",
    "ats_heat_thresholds",
    "llm_aggregates_quarterly",
}

SERVICE_ROLE_ONLY = {
    "model_tracking_history",
}

USER_OWNED_ALREADY_RLS = {
    "pro_users",
    "saved_properties",
    "saved_searches",
    "saved_valuations",
}


SQL_OBJECTS = """
SELECT
  c.relname AS object_name,
  CASE c.relkind
    WHEN 'r' THEN 'table'
    WHEN 'v' THEN 'view'
    WHEN 'm' THEN 'matview'
    WHEN 'p' THEN 'partitioned'
    ELSE c.relkind::text
  END AS kind,
  c.relrowsecurity AS rls_enabled,
  c.reltuples::bigint AS row_count_estimate,
  pg_size_pretty(pg_total_relation_size(c.oid)) AS size
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'v', 'm', 'p')
ORDER BY c.relkind, c.relname;
"""

SQL_POLICIES = """
SELECT
  tablename,
  policyname,
  cmd,
  roles::text AS roles,
  qual AS using_clause,
  with_check AS with_check_clause
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
"""

SQL_GRANTS = """
SELECT
  table_name,
  grantee,
  string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND grantee IN ('anon', 'authenticated', 'service_role', 'public', 'PUBLIC')
GROUP BY table_name, grantee
ORDER BY table_name, grantee;
"""


def categorize(name: str, kind: str) -> str:
    if kind == "view":
        return "view"
    if name in USER_OWNED_ALREADY_RLS:
        return "user_owned_already_rls"
    if name in DASHBOARD_PUBLIC:
        return "dashboard_public"
    if name in SERVICE_ROLE_ONLY:
        return "service_role_only"
    return "unclear"


def main() -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("SUPABASE_DB_URL not set. Use the transaction-pooler URI (port 6543).", file=sys.stderr)
        return 2

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_OBJECTS)
            objects = [
                {
                    "object_name": r[0],
                    "kind": r[1],
                    "rls_enabled": r[2],
                    "row_count_estimate": r[3],
                    "size": r[4],
                }
                for r in cur.fetchall()
            ]
            cur.execute(SQL_POLICIES)
            policies = [
                {
                    "tablename": r[0],
                    "policyname": r[1],
                    "cmd": r[2],
                    "roles": r[3],
                    "using_clause": r[4],
                    "with_check_clause": r[5],
                }
                for r in cur.fetchall()
            ]
            cur.execute(SQL_GRANTS)
            grants = [
                {"table_name": r[0], "grantee": r[1], "privileges": r[2]}
                for r in cur.fetchall()
            ]

    for obj in objects:
        obj["category"] = categorize(obj["object_name"], obj["kind"])

    raw = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": "verdmat-is (szzjsvmvxfrhyexblzvq)",
        "schema": "public",
        "objects": objects,
        "policies": policies,
        "grants": grants,
    }

    (AUDIT_DIR / "rls_sweep_raw.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"wrote {AUDIT_DIR / 'rls_sweep_raw.json'}")
    print("(report.md is generated separately — see Checkpoint 1 deliverable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
