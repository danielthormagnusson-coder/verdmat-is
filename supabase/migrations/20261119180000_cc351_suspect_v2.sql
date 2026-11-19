-- cc351: suspect-reglusett refinedB-v2-2026-11-19 — fjöleignaskjal lyklað á (EMNR, SKJALANUMER).
--
-- Rót: regla R3 (size_mismatch) taldi skjal fjöleigna ef SKJALANUMER spannaði >1 fastanúmer.
-- Skjalanúmer eru aðeins einkvæm innan embættis (EMNR); 21.270 kaupskrárlínur féllu á regluna
-- vegna áreksturs við skjal hjá öðru embætti, 20.916 þeirra án nokkurrar stærðarástæðu.
-- Mæling og nefnarar: D:\_audit\cc351_size_mismatch\SKIL_CC351.md.
--
-- Þessi migration er GAGNA-migration á þrjá dálka sales_history; skema breytist ekki.
-- Nýju gildin reiknar scripts/suspect_rules.py (RULESET_V2) í Python og beitingarskriftan
-- (D:\_audit\cc351_size_mismatch\beita_cc351.py) hleður þeim í pg_temp.cc351_stage
-- (faerslunumer, fastnum, is_suspect, reason) í SÖMU færslu áður en þetta keyrir.
-- BEGIN/COMMIT eru ekki hér: beitingarskriftan stýrir færslunni (lock_timeout 5s).
--
-- 1) Eldri útgáfa geymd: afrit af suspect-dálkunum þremur á hverri röð (rollback-heimild).
--    Ný tafla í public → RLS á + REVOKE ALL í sömu færslu (engin anon/authenticated-réttindi).
CREATE TABLE public.sales_history_suspect_v1_cc351 AS
SELECT id, faerslunumer, fastnum, is_suspect_comparable, suspect_reason, suspect_ruleset_version
  FROM public.sales_history;
ALTER TABLE public.sales_history_suspect_v1_cc351 ADD PRIMARY KEY (id);
ALTER TABLE public.sales_history_suspect_v1_cc351 ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.sales_history_suspect_v1_cc351 FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.sales_history_suspect_v1_cc351 TO service_role;
COMMENT ON TABLE public.sales_history_suspect_v1_cc351 IS
  'cc351: suspect-dálkar sales_history undir refinedB-v1-2026-07-02 fyrir beitingu v2 (rollback-heimild). Ekki lesin af vef.';

-- 2) Breytingaskrá (cc179-reglan: hvert sjálfvirkt skrif á staðreyndatöflu rekjanlegt):
--    ein lína á REIT fyrir is_suspect_comparable og suspect_reason þar sem gildið breytist.
--    Útgáfudálkurinn breytist á öllum röðum og er bókaður í pipeline_runs + afritinu, ekki hér.
INSERT INTO public.sales_history_corrections
       (source, faerslunumer, fastnum, column_name, old_value, new_value, suspect_ruleset_version)
SELECT 'cc351_suspect_v2', s.faerslunumer, s.fastnum, 'is_suspect_comparable',
       s.is_suspect_comparable::text, t.is_suspect::text, 'refinedB-v2-2026-11-19'
  FROM public.sales_history s
  JOIN pg_temp.cc351_stage t USING (faerslunumer, fastnum)
 WHERE s.is_suspect_comparable IS DISTINCT FROM t.is_suspect
UNION ALL
SELECT 'cc351_suspect_v2', s.faerslunumer, s.fastnum, 'suspect_reason',
       s.suspect_reason, t.reason, 'refinedB-v2-2026-11-19'
  FROM public.sales_history s
  JOIN pg_temp.cc351_stage t USING (faerslunumer, fastnum)
 WHERE s.suspect_reason IS DISTINCT FROM t.reason;

-- 3) Nýju gildin. Allar raðir fá útgáfumerkið (daily_sales_refresh ber dálkinn saman).
UPDATE public.sales_history s
   SET is_suspect_comparable   = t.is_suspect,
       suspect_reason          = t.reason,
       suspect_ruleset_version = 'refinedB-v2-2026-11-19'
  FROM pg_temp.cc351_stage t
 WHERE s.faerslunumer = t.faerslunumer
   AND s.fastnum      = t.fastnum;
