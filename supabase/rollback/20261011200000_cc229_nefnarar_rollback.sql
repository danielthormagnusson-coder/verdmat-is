-- Afturköllun cc229: framendi fyrst aftur á cc224-v5, svo:
delete from semantic.nybygging_einingar where utgafa = 'cc224-v6';
delete from semantic.nybygging_verkefni where utgafa = 'cc224-v6';
alter table semantic.nybygging_verkefni drop constraint if exists nybygging_verkefni_leiga_chk;
alter table semantic.nybygging_verkefni drop column if exists n_leiga;
notify pgrst, 'reload schema';
