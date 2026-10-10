-- ROLLBACK cc224b augl_flokkur — skrifað FYRIR apply.
alter table semantic.nybygging_einingar drop constraint if exists nybygging_einingar_augl_flokkur_check;
alter table semantic.nybygging_einingar drop column if exists augl_flokkur;
