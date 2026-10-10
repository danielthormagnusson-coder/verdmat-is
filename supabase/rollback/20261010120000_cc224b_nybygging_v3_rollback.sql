-- ROLLBACK cc224b — skrifað FYRIR apply. Eyðir v3-röðum og fellir v3-dálka; cc224-v2 óhreyfð.
delete from semantic.nybygging_einingar where utgafa = 'cc224-v3';
delete from semantic.nybygging_verkefni where utgafa = 'cc224-v3';
drop table if exists semantic.nybygging_myndir;
alter table semantic.nybygging_einingar
  drop column if exists augl_id,
  drop column if exists augl_endursala;
alter table semantic.nybygging_verkefni
  drop column if exists mynd_sha256,
  drop column if exists mynd_lykill,
  drop column if exists mynd_lykill_frumrit,
  drop column if exists mynd_breidd,
  drop column if exists mynd_haed,
  drop column if exists mynd_stofa,
  drop column if exists mynd_dags,
  drop column if exists mynd_listing_id;
