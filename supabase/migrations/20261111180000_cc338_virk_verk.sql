-- cc338 (Danni + arkitekt, leið (a) þrengd 11.11): registur_afrit fær að vita HVORT langar fyrirspurnir
-- eru virkar án þess að sjá pg_stat_activity sjálft. SECURITY DEFINER (eigandi postgres, sem er í
-- pg_read_all_stats), fast search_path, skilar AÐEINS (fjoldi, lengsta_sek) — enginn fyrirspurnatexti,
-- ekkert pid, notandi né gagnagrunnur. Sía = sú sem afrit hluthafa notar + eigin tenging útilokuð.
-- EXECUTE aðeins til registur_afrit. Keyrt um psycopg2 með lock_timeout (ekki MCP apply_migration).
-- Rollback: supabase/rollback/20261111180000_cc338_virk_verk_rollback.sql
begin;
set local lock_timeout = '5s';

CREATE FUNCTION registur_utflutningur.virk_verk(sek integer)
RETURNS TABLE (fjoldi integer, lengsta_sek integer)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $fall$
  SELECT count(*)::integer,
         coalesce(floor(extract(epoch FROM max(now() - a.query_start)))::integer, 0)
  FROM pg_catalog.pg_stat_activity a
  WHERE a.state = 'active'
    AND a.backend_type = 'client backend'
    AND a.usename NOT IN ('supabase_admin', 'authenticator', 'registur_afrit', 'pgbouncer')
    AND a.pid <> pg_catalog.pg_backend_pid()
    AND now() - a.query_start > pg_catalog.make_interval(secs => sek)
$fall$;

ALTER FUNCTION registur_utflutningur.virk_verk(integer) OWNER TO postgres;
COMMENT ON FUNCTION registur_utflutningur.virk_verk(integer) IS
  'cc338: fjöldi og lengd (s) virkra client-fyrirspurna lengri en sek, án texta. Aðeins registur_afrit.';
REVOKE ALL ON FUNCTION registur_utflutningur.virk_verk(integer) FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION registur_utflutningur.virk_verk(integer) TO registur_afrit;

-- Eftirathugun í sömu færslu: kastar (og allt rúllar til baka) ef réttindi eða gerð eru ekki rétt.
DO $chk$
DECLARE f constant text := 'registur_utflutningur.virk_verk(integer)';
        p record;
BEGIN
  SELECT pr.prosecdef, pr.provolatile, pr.proconfig, pg_get_userbyid(pr.proowner) AS eig,
         pg_get_function_result(pr.oid) AS nidur
    INTO p FROM pg_proc pr WHERE pr.oid = f::regprocedure;
  IF NOT p.prosecdef OR p.provolatile <> 's' OR p.eig <> 'postgres'
     OR p.proconfig IS DISTINCT FROM ARRAY['search_path=pg_catalog, pg_temp']
     OR p.nidur <> 'TABLE(fjoldi integer, lengsta_sek integer)' THEN
    RAISE EXCEPTION 'cc338: gerð falls röng: %', row_to_json(p);
  END IF;
  IF has_function_privilege('public', f, 'EXECUTE') OR has_function_privilege('anon', f, 'EXECUTE')
     OR has_function_privilege('authenticated', f, 'EXECUTE') OR has_function_privilege('service_role', f, 'EXECUTE')
     OR NOT has_function_privilege('registur_afrit', f, 'EXECUTE') THEN
    RAISE EXCEPTION 'cc338: EXECUTE-réttindi röng';
  END IF;
END
$chk$;
commit;
