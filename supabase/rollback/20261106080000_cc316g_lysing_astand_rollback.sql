-- cc316g rollback. www þolir fjarveru töflunnar (PGRST205/42P01: ekkert birtist). Keypt svör í scraper.lysing_eigindi_svar standa.
begin;
set local lock_timeout='5s';
drop table if exists public.lysing_astand;
commit;
