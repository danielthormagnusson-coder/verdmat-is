-- =====================================================================
-- cc219 fasi 3 — Verðvaktin: NEFNARI PER STAÐ nýbyggingarofans (Allt / Án nýbygginga / Aðeins nýbyggingar)
-- Rollback: supabase/rollback/20261009200000_cc219_verdvakt_nefnari_stadir_rollback.sql
-- Spegill: verdmat-ai/supabase/migrations/20261009200000_cc219_verdvakt_nefnari_stadir.sql (orðrétt afrit)
--
-- Vandinn (backlog cc223 → cc219 fasi 3): /verdvaktin sýndi „af 7.979 eignum á sölu — öllum" undir Án/Aðeins,
-- því v1-nefnarinn (n_virkar_einingar) er ekki skiptur eftir nýbyggingum.
--
-- Skilgreining (regla_version 'cc219-v3-stadir'):
--   eign á sölu = FASTNÚMER með a.m.k. eina auglýsingu sem v_verdvakt_breytingar_v2 telur virka (CTE `virk` þar:
--                 sala, íbúðarhúsnæði, verð ≥ 1 M, ekki „verð samkvæmt beiðni", status 'active', engin
--                 withdrawn_confirmed). SAMA skilgreining og dálkurinn a_solu í v2 → hver eign sem teljarinn telur
--                 „á sölu" er í nefnaranum (mælt h03: 0 af 618 utan; nefnari septemberskýrslunnar,
--                 v_eign_virk_auglysing, sleppir confirmed_absent_1 og hefði skilið 37 af 618 eftir utan).
--   nýbygging  = sama regla og dálkurinn nybygging í v2, metin per auglýsingu; eign telst nýbygging ef EINHVER virk
--                auglýsing hennar uppfyllir regluna (bool_or). NULL (byggingarár og -stig óþekkt) → Án.
--   staðir     = 'med' (allar), 'an' (nýbygging IS NOT TRUE), 'adeins' (nýbygging IS TRUE) → med = an + adeins.
-- v_verdvakt_breytingar_v2 og v_verdvakt_nefnarar_v2 eru ÓSNERT (skýrsla 2026-09 kafli 13 les v2).
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan

CREATE MATERIALIZED VIEW semantic.v_verdvakt_nefnarar_stadir_v2 AS
WITH virk AS (
  SELECT l.fastnum,
         COALESCE(l.byggar, p.byggar::integer) >= (EXTRACT(year FROM CURRENT_DATE)::integer - 1)
           OR (p.byggingarstig = ANY (ARRAY['B0','B1','B2','B3']) AND p.matsstig ~ '^[0-6]$') AS nyb
    FROM scraper.listings l
    LEFT JOIN properties p ON p.fastnum = l.fastnum
   WHERE l.tenure = 'sale' AND l.category = 'residential' AND l.fastnum IS NOT NULL
     AND l.price_amount IS NOT NULL AND l.price_amount >= 1000000 AND NOT COALESCE(l.is_price_on_request, false)
     AND l.status = 'active'
     AND NOT EXISTS (SELECT 1 FROM scraper.listing_lifecycle_events e
                      WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id
                        AND e.event_type = 'withdrawn_confirmed'::scraper.lifecycle_event_enum)
), eign AS (
  SELECT virk.fastnum, bool_or(virk.nyb) AS nyb FROM virk GROUP BY virk.fastnum
)
SELECT s.nybygg,
       CASE s.nybygg WHEN 'med' THEN count(*)
                     WHEN 'an' THEN count(*) FILTER (WHERE eign.nyb IS NOT TRUE)
                     ELSE count(*) FILTER (WHERE eign.nyb IS TRUE) END AS n_eignir_a_solu,
       count(*) FILTER (WHERE eign.nyb IS NULL) AS n_nyb_othekkt,
       'cc219-v3-stadir'::text AS regla_version,
       now() AS byggt_at
  FROM (VALUES ('med'), ('an'), ('adeins')) AS s(nybygg)
  CROSS JOIN eign
 GROUP BY s.nybygg;

CREATE UNIQUE INDEX v_verdvakt_nefnarar_stadir_v2_idx ON semantic.v_verdvakt_nefnarar_stadir_v2 (nybygg);
COMMENT ON MATERIALIZED VIEW semantic.v_verdvakt_nefnarar_stadir_v2 IS
  'Verðvaktin (cc219 fasi 3): eignir (fastnúmer) á sölu per stað nýbyggingarofans, med = an + adeins. Sama „virk"-skilgreining og a_solu í v_verdvakt_breytingar_v2. regla_version cc219-v3-stadir.';

REVOKE ALL ON semantic.v_verdvakt_nefnarar_stadir_v2 FROM PUBLIC;
GRANT SELECT ON semantic.v_verdvakt_nefnarar_stadir_v2 TO anon, authenticated;

COMMIT;
