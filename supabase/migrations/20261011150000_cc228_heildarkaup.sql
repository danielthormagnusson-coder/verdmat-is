-- cc228 (D) D2′ (GO Danna 11.10.2026): ónothæfur samningur telst „Seld (heildarkaup)" í framvindu NEMA einingin hafi
-- verið auglýst til sölu eftir samningsdag (söluauglýsing sást fyrst eftir síðasta ónothæfa samninginn) EÐA sé á sölu núna.
-- Ekkert verðgólf. Verð birtist hvergi: kaupverd/kr_m2 aðeins á stada='seld' (óbreytt check), söluverðsmiðgildi óbreytt (regla 2).
--   einingar.stada 'heildarkaup' — sala_dags = dagsetning síðasta ónothæfa samnings, kaupverd/kr_m2 NULL
--   verkefni.n_heildarkaup       — einingar í heildarkaupum (taldar í n_seld, utan verðtalna)
-- Fyllist í útgáfu cc224-v5 (cc224_nybygging_verkefni.py); v4 stendur sem afturköllun. Beitt með psycopg2
-- (lock_timeout 10s / statement_timeout 120s).
alter table semantic.nybygging_einingar drop constraint nybygging_einingar_stada_check;
alter table semantic.nybygging_einingar add constraint nybygging_einingar_stada_check
  check (stada = any (array['seld', 'magnsala', 'heildarkaup', 'a_solu', 'oseld']));
alter table semantic.nybygging_einingar drop constraint nybygging_einingar_chk;
alter table semantic.nybygging_einingar add constraint nybygging_einingar_chk check (
  n_undireiningar >= 1 and (heildareining or n_undireiningar = 1)
  and ((stada = any (array['seld', 'magnsala', 'heildarkaup'])) = (sala_dags is not null))
  and (stada = 'seld' or kaupverd is null) and (kr_m2 is null or stada = 'seld') and n_laekkanir >= 0);
alter table semantic.nybygging_verkefni add column if not exists n_heildarkaup integer not null default 0;
alter table semantic.nybygging_verkefni add constraint nybygging_verkefni_heildarkaup_chk check (
  n_heildarkaup >= 0 and n_magnseld + n_heildarkaup <= n_seld and n_kr_m2_seld <= n_seld - n_magnseld - n_heildarkaup);
notify pgrst, 'reload schema';
