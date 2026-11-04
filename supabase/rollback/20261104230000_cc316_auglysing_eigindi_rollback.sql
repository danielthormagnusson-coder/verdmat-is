-- cc316 rollback. www þolir fjarveru töflunnar (PGRST205/42P01: ekkert birtist). Stöðva líka verkið verdmat-nightly-auglysing-eigindi.
begin;
set local lock_timeout='5s';
drop table if exists public.auglysing_eigindi;
commit;
