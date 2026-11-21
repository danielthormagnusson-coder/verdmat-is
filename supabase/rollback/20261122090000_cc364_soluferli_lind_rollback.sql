-- cc364 rollback: lind fyrir leit (MV + lesfall). Keyrist EFTIR rollback á 20261122090100_cc364_leit_ferli (leit_auglysingar les MV).
DROP FUNCTION IF EXISTS public.soluferli_opin_mv(bigint[]);
DROP MATERIALIZED VIEW IF EXISTS scraper.soluferli_opin_mv;
DELETE FROM supabase_migrations.schema_migrations WHERE version = '20261122090000';
NOTIFY pgrst, 'reload schema';
