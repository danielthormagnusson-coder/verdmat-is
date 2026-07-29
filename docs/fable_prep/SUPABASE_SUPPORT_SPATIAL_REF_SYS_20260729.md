# DRÖG — Supabase support-beiðni: spatial_ref_sys write grants (cc55, 2026-07-29)

Staða: **DRÖG, ÓSEND.** Danni sendir sjálfur af eigin aðgangi (Supabase dashboard →
Support). Textinn fyrir neðan strikið er tilbúinn til að líma inn óbreyttan.
Heimild allra mælinga: `docs/RLS_FIX_20260729T075021Z.md` (cc52-úttektin, 2026-07-29).

Tillaga að flokkun í support-forminu: Project `szzjsvmvxfrhyexblzvq` · Category
"Database" · Severity: Normal (engin app-gögn í töflunni; heilleika-/aðgengisáhætta
á næturpípu).

---

**Subject:** Request: revoke anon/authenticated write grants on `public.spatial_ref_sys` (owned by `supabase_admin`, cannot fix as `postgres`)

Hi,

Project ref: `szzjsvmvxfrhyexblzvq` (eu-north-1).

The security advisor flags `rls_disabled_in_public` (CRITICAL) for
`public.spatial_ref_sys` (PostGIS catalog table, 8,500 rows). While auditing that
flag on 2026-07-29 we measured — with the plain `anon` key over PostgREST, no
session — that `anon` does not just have read access but also holds
`INSERT`, `UPDATE`, `DELETE` and `TRUNCATE` on the table:

- `GET /rest/v1/spatial_ref_sys` with `Prefer: count=exact` → `206`, `Content-Range: 0-0/8500`
- `POST` of an already-existing key → `409 {"code":"23505","details":"Key (srid)=(4326) already exists."}` — i.e. the request passed authorization all the way to the unique constraint, so INSERT is genuinely granted (no row was written)
- `DELETE` / `PATCH` with a non-matching filter → `204`
- `aclexplode(relacl)` confirms the write grants for both `anon` and `authenticated`

Practical impact: a single anonymous `DELETE /rest/v1/spatial_ref_sys?srid=gt.0`
could empty the SRID registry. The table holds no application data, but our
scraper pipeline computes a `geography(Point,4326)` generated column, so a wipe
would break that processing.

We cannot fix this ourselves: the table is owned by `supabase_admin`, and both SQL
Editor sessions and our migration role run as `postgres`, which is not a member of
`supabase_admin` and holds no `GRANT OPTION` on the table:

```
current_user = postgres        relowner = supabase_admin
pg_has_role('postgres', 'supabase_admin', 'MEMBER')          → false
has_table_privilege(... 'SELECT WITH GRANT OPTION')          → false
```

So `REVOKE ... FROM anon, authenticated` executed as `postgres` raises only a
WARNING and is a silent no-op — the migration reports success while `aclexplode`
and a repeated anon REST test show the grants unchanged. We also tried the same
REVOKE via `supabase_privileged_role` (which `postgres` is a member of); same
result.

**Request:** please run, as a sufficiently privileged role:

```sql
REVOKE INSERT, UPDATE, DELETE, TRUNCATE
  ON TABLE public.spatial_ref_sys
  FROM anon, authenticated;
```

`SELECT` should remain as-is (PostGIS clients read the table), and we are not
asking for RLS or ownership changes — only the removal of the write grants for
the two API roles.

Happy to provide the full audit trail if useful.

Thanks!
