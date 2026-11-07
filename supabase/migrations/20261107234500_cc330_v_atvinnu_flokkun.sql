-- cc330 (B2, GO Danna 07.11): sýn í brúna til hluthafar. Sama mynstur og v_lb_auglysingar:
-- eigandi postgres, ekki security_invoker (registur_afrit fær ekkert á semantic), aðeins SELECT til registur_afrit.
-- Sýnin læsir dálkagerðum semantic.atvinnu_flokkun: breyting þar krefst DROP/CREATE sýnar í sömu migration.
-- Keyrt um psycopg2 með lock_timeout (ekki MCP apply_migration). Rollback: supabase/rollback/20261107234500_cc330_v_atvinnu_flokkun_rollback.sql
begin;
set local lock_timeout = '5s';
CREATE VIEW registur_utflutningur.v_atvinnu_flokkun AS
  SELECT tegund, yfirflokkur, flokkur, radast, regla_version FROM semantic.atvinnu_flokkun;
REVOKE ALL ON registur_utflutningur.v_atvinnu_flokkun FROM public, anon, authenticated, service_role;
GRANT SELECT ON registur_utflutningur.v_atvinnu_flokkun TO registur_afrit;
commit;
