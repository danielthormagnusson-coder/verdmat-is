-- Afturköllun cc243 (söluhraði per nýbyggingarverkefni). Skrifuð Á UNDAN migration.
-- RÖÐ: (1) framendi af nýju dálkunum (f.2, ef kominn) → (2) smiðurinn aftur á kóða án cc243 (git revert á main), annars
--      fellur næsta næturkeyrsla á INSERT í dálka sem ekki eru til → (3) þetta skjal.
-- Hrein viðbót: engin gögn í núverandi dálkum v2–v8 eru snert; ekkert þarf að endurheimta.
-- Beitt með psycopg2 (lock_timeout 10s / statement_timeout 120s), sjá D:\_audit\cc243_soluhradi\m1_beita_migration.py.
drop table if exists semantic.nybygging_solur_manadar;
alter table semantic.nybygging_verkefni drop constraint if exists nybygging_verkefni_heildarkaup_merki_chk;
alter table semantic.nybygging_verkefni drop constraint if exists nybygging_verkefni_hradi_chk;
alter table semantic.nybygging_verkefni
  drop column if exists heildarkaup_n_pakkar,
  drop column if exists heildarkaup_staersti_pakki,
  drop column if exists heildarkaup_sidast,
  drop column if exists heildarkaup_fyrst,
  drop column if exists hradi_stada,
  drop column if exists man_i_uppselt,
  drop column if exists hradi_oseldar,
  drop column if exists hradi_glugga_til,
  drop column if exists hradi_glugga_fra,
  drop column if exists hradi_90d,
  drop column if exists n_solur_90d;
notify pgrst, 'reload schema';
