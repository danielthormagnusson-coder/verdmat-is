-- cc316b rollback. www þolir fjarveru töflunnar (PGRST205/42P01: ekkert birtist). Stöðva líka verkið verdmat-nightly-lysing-eigindi.
-- ATH: eyðir keyptum svörum í scraper.lysing_eigindi_svar. Afritaðu þau fyrst ef á að halda þeim.
begin;
set local lock_timeout='5s';
drop table if exists public.lysing_eigindi;
drop table if exists scraper.lysing_eigindi_svar;
commit;
