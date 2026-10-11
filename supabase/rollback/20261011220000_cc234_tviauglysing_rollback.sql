-- Afturköllun cc234: framendi fyrst aftur á cc224-v7, svo:
delete from semantic.nybygging_einingar where utgafa = 'cc224-v8';
delete from semantic.nybygging_verkefni where utgafa = 'cc224-v8';
delete from semantic.nybygging_keyrslur where utgafa = 'cc224-v8';
alter table semantic.nybygging_verkefni drop constraint if exists nybygging_verkefni_tviaugl_chk;
alter table semantic.nybygging_verkefni drop column if exists leiguadili_n;
alter table semantic.nybygging_verkefni drop column if exists leiguadili;
alter table semantic.nybygging_verkefni drop column if exists n_tviaugl_nu;
notify pgrst, 'reload schema';
