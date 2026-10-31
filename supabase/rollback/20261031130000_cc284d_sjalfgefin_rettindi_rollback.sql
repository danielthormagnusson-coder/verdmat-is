-- ROLLBACK cc284d — endurheimtir pg_default_acl postgres eins og hún var mæld 31.10 10:20:
--   postgres | public | r | {postgres=arwdDxtm/postgres,anon=arwdDxtm/postgres,authenticated=arwdDxtm/postgres,service_role=arwdDxtm/postgres}
--   postgres | public | S | {postgres=rwU/postgres,anon=rwU/postgres,authenticated=rwU/postgres,service_role=rwU/postgres}
--   postgres | public | f | {postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}
--   engin færsla fyrir postgres í semantic/scraper og engin altæk (nsp=0) færsla → innbyggt: EXECUTE til PUBLIC á föllum.
-- Áhrif aðeins á hluti sem verða til EFTIR rollback; núverandi hlutir óbreyttir.
begin;
set local lock_timeout = '3s';
alter default privileges for role postgres in schema public grant all on tables    to anon, authenticated;
alter default privileges for role postgres in schema public grant all on sequences to anon, authenticated;
alter default privileges for role postgres in schema public grant execute on functions to anon, authenticated;
alter default privileges for role postgres grant execute on functions to public;
commit;
