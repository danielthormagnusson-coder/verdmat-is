# Migration dry-run plan — RLS baseline audit

**Migration**: `supabase/migrations/20260506_rls_baseline_audit.sql`
**Generated**: 2026-05-06
**Status**: drafted, awaiting Danni "apply" go-ahead
**Categorization source**: `audit/rls_sweep_report.md` + Danni decisions 2026-05-06 + empirical pre-checks (column inventory, frontend-grep)

---

## What this migration does

Three sections wrapped in a single `BEGIN ... COMMIT` transaction. If any statement fails, the entire migration rolls back and the database returns to the pre-state. There are 14 dashboard-public tables, 4 user-owned tables (already RLS'd, just need anon-revoke), and 4 views (inherit RLS from underlying tables, just need write-revoke). Total: 22 objects touched, ~80 individual SQL statements.

The migration is idempotent. `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` is a no-op when RLS is already on. `DROP POLICY IF EXISTS` handles repeat applies. `REVOKE` and `GRANT` are idempotent by definition. Re-running the migration should produce the same final state without errors.

---

## Section 1 — Dashboard-public tables (14)

Per-table block applies the canonical SCRAPER_SPEC §3.3 pattern: enable RLS, create public_read policy granting SELECT to anon and authenticated, revoke all over-permissive grants from anon and authenticated, grant SELECT back to anon and authenticated, grant unrestricted to service_role for scraper and precompute writes.

The 14 tables in this section, ordered by row count:

| # | Table | Rows | Size | Frontend read path |
|---|---|---:|---:|---|
| 1 | `feature_attributions_iter3v2` | 1,103,160 | 121 MB | `/eign/[fastnum]?mode=debug` waterfall comparison |
| 2 | `feature_attributions` | 1,103,160 | 119 MB | `/eign/[fastnum]` SHAP waterfall |
| 3 | `comps_index` | 1,101,454 | 225 MB | `/eign/[fastnum]` comps card |
| 4 | `sales_history` | 173,081 | 24 MB | `/eign/[fastnum]` sale history |
| 5 | `properties` | 124,835 | 206 MB | search RPC, `/eign/[fastnum]`, `/markadur/*` |
| 6 | `predictions_iter3v2` | 110,316 | 18 MB | `?mode=debug` comparison |
| 7 | `predictions` | 110,316 | 37 MB | `/eign/[fastnum]` prediction card |
| 8 | `last_listing_text` | 60,807 | 128 MB | indirect via PostgREST joins |
| 9 | `repeat_sale_index` | 2,673 | 584 kB | `/markadur/visitala` |
| 10 | `ats_dashboard_monthly_heat` | 2,501 | 624 kB | `/markadur/markadsstada` regime grid |
| 11 | `llm_aggregates_quarterly` | 1,450 | 416 kB | `/markadur/ibudir` |
| 12 | `ats_lookup_by_quarter` | 913 | 360 kB | `/markadur/markadsstada` |
| 13 | `ats_lookup` | 65 | 80 kB | scoring RPC backbone |
| 14 | `model_tracking_history` | small | 48 kB | `/markadur/modelstada` |

Each table receives the same six statements:

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON <table>;
CREATE POLICY public_read ON <table> FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON <table> FROM anon, authenticated;
GRANT SELECT ON <table> TO anon, authenticated;
GRANT ALL ON <table> TO service_role;
```

Net effect: anon and authenticated lose DELETE, INSERT, UPDATE, TRUNCATE, REFERENCES, TRIGGER privileges. They retain only SELECT (granted explicitly after the REVOKE ALL) which is enforced via the new `public_read` policy. The Supabase alert closes because (a) RLS is now enabled on every flagged table, (b) the only policy is a SELECT-only policy, and (c) the underlying privilege grants no longer permit writes.

### Special note on `last_listing_text` columns

Column inventory verified empirically 2026-05-06: `fastnum` (bigint, NOT NULL), `sale_rank` (smallint, NOT NULL), `thinglyst_dagur` (date, nullable), `augl_id` (text, nullable), `lysing_plain` (text, nullable), `scraped_at` (timestamptz, nullable). **No `agent_phone`, no `agent_email`, no PII.** `lysing_plain` is the listing description text that is publicly displayed on source listing platforms (mbl.is, fasteignir.visir.is) and is not sensitive.

`augl_id` is the per-source listing identifier — exposing it to anon via the public table read path is the same back-link concern that drove SCRAPER_SPEC §3.3 to REVOKE `listing_id` from `active_listings_public`. Per Danni's decision, this audit treats `last_listing_text` as fully dashboard-public (no view-pattern column-stripping), and the back-link concern is filed as a separate v1.1 hardening pass that would need to address both `last_listing_text.augl_id` and `properties.augl_id_latest` together (the latter is also exposed today).

### Special note on `model_tracking_history` recategorization

The Checkpoint 1 sweep heuristic tagged `model_tracking_history` as service-role-only based on the table name (sounds like internal monitoring). The empirical frontend grep at Danni's request flipped this categorization: `lib/dashboard-queries.js:49` and `app/markadur/modelstada/page.js:44, 61` both call `.from("model_tracking_history")` from anon-key client contexts. This is the public model-tracking dashboard. Recategorized as dashboard-public, included in Section 1 above.

This flip illustrates the value of the Bug 24 lesson made operational: a heuristic-based categorization confidently put this table in the wrong bucket; an empirical grep against the frontend code surfaced the truth in seconds.

---

## Section 2 — User-owned tables (4)

These tables already have RLS enabled with correct `auth.uid()`-keyed policies. The migration adds nothing on the policy front; it only revokes the over-grants on anon. The four `REVOKE ALL ... FROM anon` statements are the sole content of this section.

```sql
REVOKE ALL ON pro_users FROM anon;
REVOKE ALL ON saved_properties FROM anon;
REVOKE ALL ON saved_searches FROM anon;
REVOKE ALL ON saved_valuations FROM anon;
```

Authenticated users retain full DML so that, when the auth flow ships in a future Sprint, they can manage their own rows under the existing policy gating. Service role retains full access for administrative operations.

Behavioral impact today: zero. No auth flow has shipped, so anon writes to `saved_*` are not in use. The change is defense-in-depth only: removing the technical capability for anon to even attempt a DELETE on `saved_valuations`.

---

## Section 3 — Views (4)

Views in Postgres inherit row-level access rules from their underlying tables. Once Section 1 enables RLS on all the dashboard-public underlying tables, view reads via anon work transparently — the inherited public_read policy fires. No view-side RLS configuration is needed (and Postgres does not enforce table-style RLS on simple views regardless).

The over-grants for INSERT, UPDATE, DELETE, TRUNCATE on views are the cleanup target here. These are mostly nonsensical (Postgres only auto-makes simple views updatable, and most of these views are joins or aggregations that are not updatable through the view interface) but they exist in `\dp` output and should be revoked for hygiene.

```sql
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON latest_regime_per_cell FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON regime_per_cell_monthly FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON repeat_sale_index_by_segment FROM anon, authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON repeat_sale_index_main_pooled FROM anon, authenticated;
```

SELECT is intentionally not revoked — the views are public-read surfaces by design.

---

## Dependencies and ordering

The migration order is: Section 1 (table RLS + policies + grants) → Section 2 (user-owned anon revokes) → Section 3 (view write revokes). This order matters because:

- Views inherit RLS from underlying tables. If Section 3 ran before Section 1, there would be a transient window (within the transaction, but still relevant if a statement failed mid-section) where view reads might bypass policy enforcement on the underlying tables. Since the entire migration is in a single transaction, this is a theoretical concern only — but conceptually the underlying-first order is cleaner.
- User-owned tables are independent of dashboard-public tables (no foreign-key constraints between them at the relation level), so Section 2's order relative to Section 1 is arbitrary. Placed second to keep the file readable.

No Postgres deferrable constraints are involved. No CASCADE behavior triggers. The migration touches policy and privilege metadata only, not row data.

---

## What this migration does NOT do

- It does **not** introduce column-level masking or view-pattern column-stripping. The `augl_id` back-link concern flagged above is out of scope; addressing it requires a v1.1 hardening pass that introduces column-stripping views for `last_listing_text` and `properties` and refactors frontend reads to use them.
- It does **not** change any data. No INSERT, UPDATE, or DELETE on row data is involved.
- It does **not** modify or drop any existing policy on the four user-owned tables. The `auth.uid()` policies created in Sprint 2 Áfangi 5 prep work remain untouched.
- It does **not** address the new tables that will be introduced by Áfangi 0 (`active_listings`, `active_listings_history`, `rejected_commercial_listings`). Those will ship with their own RLS + view-public configuration per SCRAPER_SPEC §3.3 in their own migration.
- It does **not** affect `service_role` access on any object. Scraper writes and precompute writes via `load_dashboard_v1.py` continue to work without modification.
- It does **not** change any RPC / function. Search RPC `search_properties_grouped` and other functions read from underlying tables; once those tables have public_read policies, the functions continue to work for anon callers.

### Postgres 15+ view security_invoker note (deferred to Áfangi 0 implementation)

By default, views in Postgres 15+ run with the privileges of the view owner (typically `postgres` superuser), which means a view CAN bypass RLS on underlying tables if not explicitly configured with `security_invoker = true`. This is **not a current security hole** because the post-fix categorization has zero service-role-only tables — every public table has a `public_read` policy that anon can already use directly, so a view that joins them cannot leak anything anon does not already have access to. But this becomes critical the moment Áfangi 0 introduces `rejected_commercial_listings` as a service-role-only table. Any view that joins that table (or any future service-role-only table) must declare `security_invoker = true` in its definition, or it will leak rows to anon callers via the view-as-bypass channel. Filed as Áfangi 0 implementation checklist item; the v1 RLS audit migration does not need to address it because the threat surface does not yet exist.

---

## Verification plan (executed in Checkpoint 3 post-apply)

The `audit/rls_verify.py` script will run after the migration applies:

1. **State diff**: re-run the Checkpoint 1 sweep and compare against `rls_sweep_raw.json`. Every dashboard-public table should now show `rls_enabled = true` with a `public_read` policy. Every user-owned table should still show `rls_enabled = true` with its existing policy. Anon grants should be reduced to SELECT-only (or empty for service-role-only and user-owned).
2. **Anon-key read path**: connect with `NEXT_PUBLIC_SUPABASE_ANON_KEY` (or its server-side equivalent) and `SELECT count(*) FROM <table>` for each dashboard-public surface. Verify the queries return row counts matching the pre-state row counts.
3. **Anon-key write path**: attempt `INSERT INTO <dashboard-public-table> (...)` with the anon key. Verify the call fails with permission-denied or RLS-violation error. This is the proof that the original Supabase alert is resolved.
4. **Anon-key on views**: verify SELECT works (via inheritance from underlying tables), and INSERT fails (revoked).
5. **Frontend smoke test**: a follow-up manual check on the live site (`/`, `/eign/2008647`, `/markadur`, `/markadur/visitala`, `/markadur/markadsstada`, `/markadur/ibudir`, `/markadur/modelstada`) confirms the dashboard pages still render correctly. This catches any unexpected interaction with the new policies (e.g., a query that joined two tables and one of them was tagged wrong).

If step 2 or step 5 fails — anon read returns zero rows for a table that previously returned data, or a dashboard page goes blank — the migration must be rolled back immediately and the categorization revisited. The single-transaction wrapping makes rollback to pre-state straightforward (the migration either committed atomically or it never happened; partial-applied state is impossible).

---

## Rollback procedure

If post-apply verification fails:

```sql
-- Per affected table, reverse the policy and re-grant (recovery only):
DROP POLICY IF EXISTS public_read ON <table>;
ALTER TABLE <table> DISABLE ROW LEVEL SECURITY;
GRANT ALL ON <table> TO anon, authenticated;  -- restores pre-state
```

Or restore from Supabase point-in-time backup (if PITR retention is configured — verify before relying on this path). Per `SCRAPER_SPEC_v1.md` §9.3 deferred items, formal Supabase PITR retention policy is v2 scope, not currently established. **If rollback via SQL is needed, do it via the SQL above, not via PITR.**

---

## CHECKPOINT 2 PAUSE

The migration is drafted and the dry-run plan is written. **No SQL has been executed against the production database.** The migration file lives at `supabase/migrations/20260506_rls_baseline_audit.sql` and has not been applied (`supabase db push` not invoked).

Awaiting explicit "apply" go-ahead from Danni before proceeding to Checkpoint 3 (apply + verify + report). On go-ahead I will:

1. Apply the migration (preferred via `supabase db push`; fall back to direct `psql` against the transaction pooler URI if CLI unavailable).
2. Capture full apply log to `audit/apply_log_<timestamp>.txt`.
3. Run `audit/rls_verify.py` (anon-key read tests + anon-key write tests + state diff).
4. Run frontend smoke check on the live deployment.
5. Write `audit/post_fix_report.md` summarizing pre/post state with evidence that the Supabase alert is resolved.
6. Commit all audit/ + migration files in a single commit with `security:` prefix.

If any post-apply verification step fails, I will halt and surface the failure mode plus the rollback recommendation, **not** attempt autonomous remediation in production.
