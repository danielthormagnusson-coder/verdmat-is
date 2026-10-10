-- cc224b (10.10.2026, ákvörðun Danna): flokkur auglýsingahlekks per einingu.
--   fyrsta_sala  — eining óseld (fyrsta sala)
--   endursala    — eining seld, auglýsing sást fyrst EFTIR þinglýsingu OG (> 180 d frá sölu EÐA önnur stofa en auglýsti
--                  eininguna fyrir sölu; engin slík → söluaðilar verkefnisins fyrir sölu)
--   eftir_solu   — eining seld, auglýsing eftir þinglýsingu en ≤ 180 d og sama stofa („auglýst eftir sölu")
--   fyrir_solu   — eining seld, auglýsingin sást fyrir þinglýsingu („auglýst fyrir sölu")
-- Beitt með psycopg2 (lock_timeout 10s / statement_timeout 120s).
alter table semantic.nybygging_einingar add column if not exists augl_flokkur text;
alter table semantic.nybygging_einingar drop constraint if exists nybygging_einingar_augl_flokkur_check;
alter table semantic.nybygging_einingar add constraint nybygging_einingar_augl_flokkur_check
  check (augl_flokkur in ('fyrsta_sala', 'endursala', 'eftir_solu', 'fyrir_solu'));
