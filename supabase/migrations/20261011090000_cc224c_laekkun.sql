-- cc224c (11.10.2026): lækkunarmerki og síðasta lækkun per einingu. Regla = Verðvaktin v2 (semantic.v_verdvakt_breytingar_v2,
-- gátir hlutd_grunur/arekstur/grunur_villa/grunsamleg), aðeins fyrsta sala (breyting sem sást eftir þinglýsingu = endursala, utan).
--   einingar.laekkun_dags/_fra/_til/_flokkur — síðasta lækkun einingarinnar í fyrstu sölu („lækkað í auglýsingu" eða
--                                              „endurbirt á nýju verði" með lægra verði)
--   einingar.laekkad_30                      — eining á sölu (stada a_solu) með lækkun sem sást síðustu 30 daga frá keyrslu,
--                                              auglýsingin á sölu (a_solu, sjálfgefið Verðvaktarinnar)
--   verkefni.n_laekkad_30                    — fjöldi slíkra eininga (kassamerkið „Verð lækkað · N íbúðir")
-- Dálkarnir eru nullable/default og fyllast í næstu keyrslu cc224_nybygging_verkefni.py (sama útgáfa cc224-v3).
-- Beitt með psycopg2 (lock_timeout 10s / statement_timeout 120s).
alter table semantic.nybygging_einingar add column if not exists laekkun_dags date;
alter table semantic.nybygging_einingar add column if not exists laekkun_fra bigint;
alter table semantic.nybygging_einingar add column if not exists laekkun_til bigint;
alter table semantic.nybygging_einingar add column if not exists laekkun_flokkur text;
alter table semantic.nybygging_einingar add column if not exists laekkad_30 boolean not null default false;
alter table semantic.nybygging_verkefni add column if not exists n_laekkad_30 integer not null default 0;
