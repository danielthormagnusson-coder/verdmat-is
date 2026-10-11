-- Afturköllun cc228 heildarkaup: framendi fyrst aftur á cc224-v4, svo:
delete from semantic.nybygging_einingar where utgafa = 'cc224-v5';
delete from semantic.nybygging_verkefni where utgafa = 'cc224-v5';
alter table semantic.nybygging_verkefni drop constraint if exists nybygging_verkefni_heildarkaup_chk;
alter table semantic.nybygging_verkefni drop column if exists n_heildarkaup;
alter table semantic.nybygging_einingar drop constraint nybygging_einingar_chk;
alter table semantic.nybygging_einingar add constraint nybygging_einingar_chk check (
  n_undireiningar >= 1 and (heildareining or n_undireiningar = 1)
  and ((stada = any (array['seld', 'magnsala'])) = (sala_dags is not null))
  and (stada = 'seld' or kaupverd is null) and (kr_m2 is null or stada = 'seld') and n_laekkanir >= 0);
alter table semantic.nybygging_einingar drop constraint nybygging_einingar_stada_check;
alter table semantic.nybygging_einingar add constraint nybygging_einingar_stada_check
  check (stada = any (array['seld', 'magnsala', 'a_solu', 'oseld']));
notify pgrst, 'reload schema';
