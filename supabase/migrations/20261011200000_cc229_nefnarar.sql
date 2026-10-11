-- cc229 (C) (GO Danna 11.10.2026 f.3): leigulína á verkefnissíðu — „Minnst N af M íbúðum hafa verið í leiguauglýsingu".
--   verkefni.n_leiga = fastanúmer verkefnisins sem hafa verið í leiguauglýsingu (mbl/myigloo, sást fyrst >= 2021-01-01).
-- Fyllist í útgáfu cc224-v6; v5 stendur sem afturköllun. Beitt með psycopg2 (lock_timeout 10s / statement_timeout 120s).
alter table semantic.nybygging_verkefni add column if not exists n_leiga integer not null default 0;
alter table semantic.nybygging_verkefni add constraint nybygging_verkefni_leiga_chk check (n_leiga >= 0 and n_leiga <= n_einingar);
notify pgrst, 'reload schema';
