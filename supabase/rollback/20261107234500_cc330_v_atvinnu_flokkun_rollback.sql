-- cc330 rollback (B2). Skrifað á undan migration. Snertir aðeins sýnina; semantic.atvinnu_flokkun og registur_afrit óbreytt.
-- Keyrt um psycopg2 með lock_timeout.
begin;
set local lock_timeout = '5s';
DROP VIEW registur_utflutningur.v_atvinnu_flokkun;
commit;
