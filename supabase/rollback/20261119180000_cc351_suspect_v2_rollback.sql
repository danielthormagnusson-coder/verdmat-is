-- cc351 rollback: setur suspect-dálka sales_history aftur á refinedB-v1-2026-07-02 úr afritinu.
-- Röð sem bættist við EFTIR beitingu (ekki í afritinu) heldur v2-gildum sínum; næsta
-- daily_sales_refresh á v1-kóða ber hana saman og lagar (undir UPDATE_ABORT_THRESHOLD).
-- Kóðann (scripts/suspect_rules.py RULESET_VERSION) þarf að færa aftur á v1 í SAMA glugga,
-- annars fellir drift-hlið daily_sales_refresh næstu keyrslu (>5.000 raðir víkja).
UPDATE public.sales_history s
   SET is_suspect_comparable   = b.is_suspect_comparable,
       suspect_reason          = b.suspect_reason,
       suspect_ruleset_version = b.suspect_ruleset_version
  FROM public.sales_history_suspect_v1_cc351 b
 WHERE s.id = b.id;

DELETE FROM public.sales_history_corrections WHERE source = 'cc351_suspect_v2';

DROP TABLE public.sales_history_suspect_v1_cc351;
