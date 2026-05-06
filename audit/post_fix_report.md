# RLS baseline audit — post-fix report

**Date applied**: 2026-05-06
**Migration**: `supabase/migrations/20260506_rls_baseline_audit.sql`
**Apply log**: `audit/apply_log_20260506.txt`
**Status**: COMPLETE — all five verification steps passed; original Supabase alert (`rls_disabled_in_public`, 2026-05-03) is resolved.

---

## Outcome summary

The 2026-05-06 RLS baseline audit migration applied cleanly to the verdmat-is production Supabase project (`szzjsvmvxfrhyexblzvq`). Every flagged table now has row-level security enabled with a `public_read` policy that grants `SELECT` to `anon` and `authenticated` and nothing else. The over-permissive default grants of full DML to `anon` and `authenticated` — which were the underlying severity multiplier behind the alert — have been revoked across all 14 dashboard-public tables, the 4 user-owned tables, and the 4 views. Frontend reads continue to work; the dashboard URLs all serve HTTP 200 with substantive content. Anon attempts to write any of the protected tables are now rejected by Postgres with error code `42501` (`insufficient_privilege`) before any policy check is even reached, which is the cleanest possible failure mode and the strongest possible alert-resolution proof.

No rollback was needed. No partial-state risk materialized. The migration is a single transaction so the only possible outcomes were "applied atomically" or "did not apply at all" — the former obtained.

---

## Pre-state vs post-state — dashboard-public tables (14)

The Supabase alert flagged these 14 tables as having RLS disabled. Every one of them also had `anon` and `authenticated` granted the full set of DML privileges (`DELETE, INSERT, UPDATE, TRUNCATE`) plus `SELECT` and the DDL-adjacent `REFERENCES, TRIGGER`. Pre-fix, anyone with the public anon key — which is embedded in client-side JavaScript and is therefore not a secret — held the technical ability to issue a `TRUNCATE TABLE comps_index` against production. Post-fix, that capability has been removed at both the privilege layer (anon now holds only `SELECT`) and the policy layer (the `public_read` policy permits only `SELECT`).

| Table | Rows | Pre-RLS | Post-RLS | Pre-anon-grants | Post-anon-grants |
|---|---:|---|---|---|---|
| `properties` | 124,835 | OFF | ON, public_read | ALL | SELECT |
| `predictions` | 110,316 | OFF | ON, public_read | ALL | SELECT |
| `predictions_iter3v2` | 110,316 | OFF | ON, public_read | ALL | SELECT |
| `comps_index` | 1,101,454 | OFF | ON, public_read | ALL | SELECT |
| `feature_attributions` | 1,103,160 | OFF | ON, public_read | ALL | SELECT |
| `feature_attributions_iter3v2` | 1,103,160 | OFF | ON, public_read | ALL | SELECT |
| `sales_history` | 173,081 | OFF | ON, public_read | ALL | SELECT |
| `repeat_sale_index` | 2,673 | OFF | ON, public_read | ALL | SELECT |
| `last_listing_text` | 60,807 | OFF | ON, public_read | ALL | SELECT |
| `ats_lookup` | 65 | OFF | ON, public_read | ALL | SELECT |
| `ats_lookup_by_quarter` | 913 | OFF | ON, public_read | ALL | SELECT |
| `ats_dashboard_monthly_heat` | 2,501 | OFF | ON, public_read | ALL | SELECT |
| `llm_aggregates_quarterly` | 1,450 | OFF | ON, public_read | ALL | SELECT |
| `model_tracking_history` | 11 | OFF | ON, public_read | ALL | SELECT |

Anon SELECT row counts under the new policy match pre-state exactly for every one of these 14 tables (verified via `SET LOCAL ROLE anon` followed by `SELECT count(*) FROM <table>`). The frontend read path is therefore preserved end-to-end.

---

## Pre-state vs post-state — user-owned tables (4)

These four tables were already correctly RLS-enabled with `auth.uid()`-keyed policies from the Sprint 2 Áfangi 5 prep work. The remaining audit gap was the over-permissive `anon` grant: anon held full DML on `pro_users`, `saved_properties`, `saved_searches`, `saved_valuations` despite having no role on user-owned data. The migration revoked all anon grants on these tables. Authenticated users retain full DML so that, when the auth flow ships in a future Sprint, they can manage their own rows under the existing user-id-gated policies. Service role retains full access for administrative operations.

Behavioral impact today: zero, because no auth flow is shipped yet and these tables have no runtime callers. Defense-in-depth gain: significant — anon no longer has the technical ability to even attempt a write against user-owned data, so the user-id policy is no longer the sole line of defense.

| Table | RLS | Policy | Pre-anon-grants | Post-anon-grants |
|---|---|---|---|---|
| `pro_users` | ON (already) | `read own` (`auth.uid() = id`) | ALL | none |
| `saved_properties` | ON (already) | `own saves` (`auth.uid() = user_id`) | ALL | none |
| `saved_searches` | ON (already) | `own searches` (`auth.uid() = user_id`) | ALL | none |
| `saved_valuations` | ON (already) | `own valuations` (`auth.uid() = user_id`) | ALL | none |

---

## Pre-state vs post-state — views (4)

The four views are derived joins/aggregations over underlying tables. Postgres views inherit row-level access from their underlying tables, so once Section 1 of the migration enabled RLS on the dashboard-public underlying tables, view reads via anon continue to work transparently. The pre-fix over-grants for `INSERT, UPDATE, DELETE, TRUNCATE` on views were largely nonsensical (Postgres only auto-makes simple views updatable, and these views are aggregations) but the migration revoked them anyway for hygiene and for `\dp` clarity.

| View | Underlying tables | Pre-anon-grants | Post-anon-grants |
|---|---|---|---|
| `latest_regime_per_cell` | `ats_dashboard_monthly_heat`, `ats_lookup_by_quarter` | ALL | REFERENCES, SELECT, TRIGGER |
| `regime_per_cell_monthly` | `ats_dashboard_monthly_heat` | ALL | REFERENCES, SELECT, TRIGGER |
| `repeat_sale_index_by_segment` | `repeat_sale_index` | ALL | REFERENCES, SELECT, TRIGGER |
| `repeat_sale_index_main_pooled` | `repeat_sale_index` | ALL | REFERENCES, SELECT, TRIGGER |

`REFERENCES` and `TRIGGER` residuals are not security concerns — `REFERENCES` on a view is meaningless (you cannot foreign-key-reference a view), and `TRIGGER` would only matter if someone wrote an `INSTEAD OF` trigger (which they have not). These can be cleaned up in a v1.1 hygiene pass alongside the broader column-stripping work flagged below.

---

## Original Supabase alert resolution evidence

The 2026-05-03 Supabase email alert read approximately:

> Table publicly accessible — rls_disabled_in_public
> One or more tables in your database have RLS disabled and are
> exposed to the public.

Pre-fix evidence supporting the alert: 14 tables with `pg_class.relrowsecurity = false` and `anon` grant including all DML privileges. Post-fix evidence demonstrating resolution:

1. **All 14 tables now have `relrowsecurity = true`** — verified via `pg_class` query; see apply log step [1].
2. **All 14 tables have at least one policy** — verified via `pg_policies` count; the policy is `public_read FOR SELECT TO anon, authenticated USING (true)` per migration; see apply log step [1].
3. **Anon DML is rejected with `42501` insufficient_privilege** — verified via direct probe (`BEGIN; SET LOCAL ROLE anon; INSERT INTO properties ... ; ROLLBACK;`) which raised the expected privilege error before any policy check; see apply log step [4].
4. **Anon SELECT continues to return full row counts** — verified via 14 row-count queries under `SET LOCAL ROLE anon`, all matching pre-state; see apply log step [3].
5. **Live-site dashboard URLs serve HTTP 200** — verified via curl probes against `/`, `/eign/2008647`, `/markadur`, `/markadur/visitala`, `/markadur/markadsstada`, `/markadur/ibudir`, `/markadur/modelstada`. All seven URLs returned 200 with substantive response sizes (35 KB to 1.1 MB). See apply log step [5].

The Supabase Security Advisor should reflect the resolved status on its next refresh cycle (typically within a few hours). If the alert persists past 24 hours, it is worth checking whether the Advisor has its own definition of "publicly accessible" beyond the `relrowsecurity` flag check.

---

## Lessons captured

**Bug 24 made operational, twice in this audit.** First when the heuristic categorization tagged `model_tracking_history` as service-role-only (a guess based on table name) and the empirical frontend grep flipped it to dashboard-public (a fact based on `app/markadur/modelstada/page.js`). Second when the audit-script-first principle — sweep `pg_class` empirically rather than trust the doc-canonical table list — surfaced the doc-vs-reality discrepancy on `predictions_iter4` / `feature_attributions_iter4` / `ats_lookup_by_heat` naming, which would have produced a partial migration if I had trusted the SCRAPER_SPEC v1 baseline cross-check verbatim.

**Single-transaction migration as default.** Wrapping the entire migration in `BEGIN ... COMMIT` made the apply atomic. The only possible outcomes were "fully applied" or "fully rolled back, no state change" — partial-state was eliminated by construction. This is the right default for any non-trivial schema change, especially security-related ones where partial state could leak data or break the read path mid-flight.

**Privilege-model + policy-layer belt-and-braces.** A single `REVOKE ALL` on anon would have been sufficient to block writes (no INSERT grant means no INSERT capability, regardless of policy state). A single `public_read` policy with no other policies would also have been sufficient (default-deny for INSERT under RLS). Doing both means there are now two independent layers blocking any anon write, and the failure mode under either layer-failure is "still safe". This costs nothing extra in the migration and significantly raises the bar for accidental future misconfiguration.

---

## Files committed

- `supabase/migrations/20260506_rls_baseline_audit.sql` — the migration itself, idempotent, single transaction
- `audit/rls_sweep.py` — Checkpoint 1 reproducibility script (read-only sweep)
- `audit/rls_sweep_report.md` — Checkpoint 1 prose findings
- `audit/rls_sweep_raw.json` — Checkpoint 1 structured dump
- `audit/migration_dry_run_plan.md` — Checkpoint 2 dry-run plan
- `audit/apply_log_20260506.txt` — Checkpoint 3 apply + verification log
- `audit/rls_verify.py` — Checkpoint 3 reproducibility script (post-fix verification)
- `audit/post_fix_report.md` — this file

All committed under `security:` prefix per Checkpoint 3 spec.

---

## Non-blocker follow-ups for backlog

Two items were surfaced during this audit that are out of scope for the immediate alert-resolution work but should be tracked:

**(1) Postgres 15+ view security_invoker default.** By default, views in Postgres 15+ run with the privileges of the view owner (typically `postgres` superuser), which means a view CAN bypass RLS on underlying tables if not explicitly configured with `security_invoker = true`. This is NOT a current security hole because the post-fix categorization has zero service-role-only tables — there is no underlying table whose RLS could be bypassed by a view that anon can SELECT from. But this becomes critical the moment Áfangi 0 introduces `rejected_commercial_listings` as a service-role-only table. Any view that joins that table must declare `security_invoker = true` or it will leak rows to anon callers. Adding to Áfangi 0 implementation checklist via PLANNING_BACKLOG amendment.

**(2) `augl_id` per-source listing identifier exposed via public read.** `last_listing_text.augl_id` and `properties.augl_id_latest` are both exposed to anon via the new public_read policies. These columns are the per-source listing identifiers from mbl.is and fasteignir.visir.is. Exposing them enables third-party scrapers to back-link our data to source platforms — same brittleness concern that drove SCRAPER_SPEC §3.3 to REVOKE `listing_id` from the new `active_listings_public` view. This is not part of the alert resolution (the alert was about RLS-disabled, not column exposure), and the exposure has been the status quo since Sprint 1. Filed as PLANNING_BACKLOG v1.1 hardening item: introduce column-stripping public views (`last_listing_text_public`, `properties_public`) that omit `augl_id` / `augl_id_latest` and refactor frontend reads to use the views. Post-Áfangi-0 timing.
