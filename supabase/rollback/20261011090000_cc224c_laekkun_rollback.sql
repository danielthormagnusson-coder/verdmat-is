-- rollback cc224c_laekkun
alter table semantic.nybygging_verkefni drop column if exists n_laekkad_30;
alter table semantic.nybygging_einingar drop column if exists laekkad_30;
alter table semantic.nybygging_einingar drop column if exists laekkun_flokkur;
alter table semantic.nybygging_einingar drop column if exists laekkun_til;
alter table semantic.nybygging_einingar drop column if exists laekkun_fra;
alter table semantic.nybygging_einingar drop column if exists laekkun_dags;
delete from supabase_migrations.schema_migrations where version = '20261011090000';
