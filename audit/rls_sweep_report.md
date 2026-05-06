# RLS sweep report — verdmat-is Supabase public schema

**Generated**: 2026-05-06
**Project**: `szzjsvmvxfrhyexblzvq` (verdmat-is)
**Schema**: `public`
**Method**: Supabase MCP `execute_sql` via service-role; queried `pg_class.relrowsecurity`, `pg_policies`, `information_schema.role_table_grants`
**Status**: read-only sweep complete; CHECKPOINT 1 PAUSE — awaiting Danni go-ahead before drafting migration

---

## Executive summary

The 2026-05-03 Supabase security alert (`rls_disabled_in_public`) is rooted in a broader configuration drift: **14 of 18 tables have row-level security disabled**, and **every one of the 22 objects in the public schema (18 tables + 4 views) has the same over-permissive grant pattern** — `anon`, `authenticated`, and `service_role` all hold the full set of privileges (`DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE`). That grant pattern is the Supabase project default, which explains how it propagated to every object created since project init, but it is the underlying severity multiplier: any holder of the public anon key (which lives in client-side JavaScript and is therefore not secret) currently has the technical ability to issue DELETE or TRUNCATE against production tables. RLS being disabled means there is no policy layer blocking those calls today.

Four tables (`pro_users`, `saved_properties`, `saved_searches`, `saved_valuations`) already have RLS enabled with `auth.uid()`-keyed policies — those were Sprint 2 Áfangi 5 prep work and are correctly secured for read access. They still carry the same over-grants on `anon`, however, so RLS is the only thing standing between a public anon caller and a `DELETE` against `saved_valuations`. This is defensible (RLS does block the call) but it is not defense-in-depth.

The fix matches the canonical pattern locked in `SCRAPER_SPEC_v1.md` §3.3: enable RLS on every table, grant `SELECT` to `anon`/`authenticated` via explicit policy on dashboard-public surfaces, revoke write privileges from `anon`/`authenticated` everywhere except where user ownership policies exist (saved_*), and keep `service_role` unrestricted for scraper and precompute writes.

---

## Highlights

**Severity 1 — RLS DISABLED on 14 production tables** (alert source)

| Table | Rows | Size | Category |
|---|---:|---:|---|
| `comps_index` | 1,101,454 | 225 MB | dashboard-public |
| `feature_attributions_iter3v2` | 1,103,160 | 121 MB | dashboard-public |
| `feature_attributions` | 1,103,160 | 119 MB | dashboard-public |
| `last_listing_text` | 60,807 | 128 MB | dashboard-public |
| `properties` | 124,835 | 206 MB | dashboard-public |
| `sales_history` | 173,081 | 24 MB | dashboard-public |
| `predictions` | 110,316 | 37 MB | dashboard-public |
| `predictions_iter3v2` | 110,316 | 18 MB | dashboard-public |
| `ats_dashboard_monthly_heat` | 2,501 | 624 kB | dashboard-public |
| `repeat_sale_index` | 2,673 | 584 kB | dashboard-public |
| `llm_aggregates_quarterly` | 1,450 | 416 kB | dashboard-public |
| `ats_lookup_by_quarter` | 913 | 360 kB | dashboard-public |
| `ats_lookup` | 65 | 80 kB | dashboard-public |
| `model_tracking_history` | small | 48 kB | service-role-only |

These are the tables Supabase flagged. Every one of them is currently world-writable as well as world-readable through the anon key.

**Severity 1 — Over-permissive grants are universal**

Every single object in the public schema — including the four views and the four already-RLS-enabled user tables — has `anon` and `authenticated` granted full DML (`DELETE, INSERT, UPDATE, TRUNCATE`) plus DDL-adjacent privileges (`TRIGGER`, `REFERENCES`). This pattern looks like a Supabase project-init default that was never tightened. Once RLS is enabled, the policies will reject most of these calls; revoking the grants on top is defense-in-depth and makes the privilege model legible to future readers (the database tells the truth about who can do what; today it lies).

**Severity 2 — Views inherit the issue**

Four views (`latest_regime_per_cell`, `regime_per_cell_monthly`, `repeat_sale_index_by_segment`, `repeat_sale_index_main_pooled`) have the same over-grants. Postgres views inherit row-level access rules from underlying tables, so once the underlying tables have RLS + SELECT policy, view reads work transparently for `anon`. The DML grants on views (TRUNCATE, INSERT, UPDATE) are mostly nonsensical — Postgres only auto-makes simple views updatable — but they should still be revoked for hygiene and so that `\dp` output reflects intent.

**Already correct — RLS-enabled with auth.uid() policies (4 tables)**

| Table | Policy | Note |
|---|---|---|
| `pro_users` | `read own` (SELECT, `auth.uid() = id`) | Sprint 2 Áfangi 5 prep |
| `saved_properties` | `own saves` (ALL, `auth.uid() = user_id`) | user-owned saves |
| `saved_searches` | `own searches` (ALL, `auth.uid() = user_id`) | user-owned searches |
| `saved_valuations` | `own valuations` (ALL, `auth.uid() = user_id`) | user-owned valuations |

These need `anon` revokes (anon has no business inserting into `saved_valuations`) but otherwise are correctly architected.

---

## Per-table inventory by proposed category

### Dashboard-public (13 tables)

These tables back the public-facing app. Frontend reads them via PostgREST with the anon key. The application has never written to any of them through the anon path — all writes happen via `load_dashboard_v1.py` with the service-role key during monthly refresh cycles. The fix is therefore symmetric for all 13: enable RLS, grant explicit SELECT to `anon`/`authenticated`, revoke all write privileges from `anon`/`authenticated`, leave `service_role` untouched.

The full list, ordered by row count: `comps_index`, `feature_attributions`, `feature_attributions_iter3v2`, `properties`, `sales_history`, `predictions`, `predictions_iter3v2`, `last_listing_text`, `repeat_sale_index`, `ats_dashboard_monthly_heat`, `llm_aggregates_quarterly`, `ats_lookup_by_quarter`, `ats_lookup`. All currently RLS-disabled. None have any policies. All have over-grants.

### Service-role-only (1 table)

`model_tracking_history` is internal model-performance tracking. The frontend does not read it; only the orchestrator writes to it during monthly refresh. Fix: enable RLS, no SELECT policy at all, revoke everything from `anon`/`authenticated`, leave `service_role` untouched. Without a SELECT policy under RLS, anon and authenticated cannot read this table even if they hold the public key — the policy default is deny.

### User-owned, already-RLS'd (4 tables)

`pro_users`, `saved_properties`, `saved_searches`, `saved_valuations`. RLS is on. Policies are correct. The only outstanding concern is the over-grants for `anon`. With RLS enforced, anon attempts to write are blocked at the policy layer, but the GRANT pattern still says anon has the right to attempt the call. Cleanest fix: REVOKE all from `anon` (anon has no role on these tables); leave `authenticated` grants intact (the auth.uid() policy gates per-user access correctly); `service_role` unrestricted.

### Views (4 objects)

`latest_regime_per_cell`, `regime_per_cell_monthly`, `repeat_sale_index_by_segment`, `repeat_sale_index_main_pooled`. Read access is governed by the underlying tables' RLS once those are fixed; no view-side RLS is needed (and Postgres does not enforce view-level RLS on simple views the way it does on tables). The over-grants for INSERT/UPDATE/DELETE/TRUNCATE on views are noise to clean up: REVOKE the same DML privileges from `anon`/`authenticated` for hygiene. SELECT remains via inheritance, so frontend dashboard queries against these views continue to work after the underlying tables get their `public_read` policies.

### Unclear / out of scope

None encountered in this sweep. The 22 objects partition cleanly into the four categories above. (The task spec listed `predictions_iter4`, `feature_attributions_iter4`, `ats_lookup_by_heat`, and a few others as expected canonical tables — those do not currently exist in `public`. Probable explanation: they live in the production pipeline but were never deployed to Supabase via `load_dashboard_v1.py`, or they were deployed under different names. This is a doc-canonical vs empirical-canonical mismatch worth flagging but not blocking — see Discrepancy note below.)

---

## Doc-canonical vs empirical-canonical discrepancy (Bug 24 lesson)

The task description listed an expected table inventory drawn from `SCRAPER_SPEC_v1.md` §3 baseline cross-check and STATE.md §Web-app stream. Empirical pg_class disagrees on three points:

1. **`predictions_iter4` and `feature_attributions_iter4` do not exist in `public`.** STATE.md mentions iter4 deploy, but Supabase only carries `predictions` and `predictions_iter3v2`. Hypothesis: `predictions` IS the iter4 production table (named without the suffix because it is the current/active model), and `predictions_iter3v2` is the historical iter3v2 retained for `?mode=debug` waterfall comparison. This matches existing `app/eign/[fastnum]/page.js` reads which query `predictions` for the live card and `predictions_iter3v2` only behind the debug flag. **Conclusion: not a missing table; just a naming convention where production = bare name and historical = suffix-stamped.**

2. **`ats_lookup_by_heat` does not exist in `public`.** Sprint 2 Áfangi 4 closure references it as the primary scoring table. Empirical: only `ats_lookup` and `ats_lookup_by_quarter` exist. Possible explanation: the by-heat aggregation was rolled into `ats_lookup` as the canonical scoring surface and the by-heat naming was deprecated. **Recommendation: confirm with Danni whether `ats_lookup` IS the by-heat table renamed, or whether by-heat genuinely does not exist in the live deployment.** Either way, none of the existing `ats_*` tables are RLS-enabled, so this audit catches them regardless.

3. **`ats_dashboard_quarterly` and `ats_heat_thresholds` are not in `public`.** Same explanation as point 2: probably collapsed into existing `ats_*` tables or never deployed. Audit categorization remains correct for the tables that exist.

These discrepancies do not change the migration design — the audit is exhaustive against actual `pg_class`, not against the expected list — but they should be reconciled in a follow-up doc pass. Trust empirical, fix docs second.

---

## Categorization decision-points for Danni

Three calls needed before Checkpoint 2 migration draft:

**Call 1 — confirm dashboard-public categorization (13 tables)**

Heuristic-applied list above. The sole judgement call here is `last_listing_text`: it carries listing description text and arguably contains agent-attribution metadata that one might want to restrict. Current frontend reads it without restriction. **Default: dashboard-public, public SELECT.** Override only if you want `last_listing_text` treated as service-role-only and read via a view that strips agent fields.

**Call 2 — confirm `model_tracking_history` is service-role-only**

This sweep tags it service-role-only on the heuristic that it is internal model monitoring. If the `/markadur/modelstada` page reads this table directly through the anon client, it needs to be dashboard-public instead. **Default: service-role-only.** Override if the modelstada UI breaks under that classification (test plan in Checkpoint 3 will catch this regardless).

**Call 3 — confirm `anon` revoke on `saved_*` and `pro_users` is acceptable**

Once `anon` loses INSERT/UPDATE/DELETE on these tables, only authenticated users (with valid Supabase Auth JWTs) can write. Today these tables are unused at runtime (no auth flow shipped yet), so the revoke has no behavioral impact. **Default: revoke `anon` writes.** Override only if you have a plan for unauthenticated writes I am not aware of.

---

## Files in this checkpoint

- `audit/rls_sweep.py` — reproducibility script (read-only; run with `SUPABASE_DB_URL` env var pointing at the transaction pooler URI per memory note; outputs `rls_sweep_raw.json`). Self-contained, idempotent, no DB writes.
- `audit/rls_sweep_raw.json` — structured dump of the same sweep this report summarizes. Used by Checkpoint 2 to drive migration generation.
- `audit/rls_sweep_report.md` — this file.

---

## CHECKPOINT 1 PAUSE

No DB changes have been made. The sweep is read-only and the production schema is untouched. Awaiting Danni go-ahead on the three calls above before proceeding to Checkpoint 2 (migration draft).

If you concur with the heuristic-applied categorization on all three calls, reply "samþykkt categorization" and I will draft the migration. If you want to override any of the three (or flag a category I assigned wrong), reply with the override and I will reflect it before drafting. The two doc-canonical discrepancies (iter4 naming, by-heat naming) can be reconciled in a separate follow-up after the security work lands — they do not block this audit.
