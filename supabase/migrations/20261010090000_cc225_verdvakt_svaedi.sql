-- =====================================================================
-- cc225 — Verðvaktin: SVÆÐISSÍA (Allt landið · Höfuðborgarsvæðið · Landsbyggðin) × nýbyggingarstaður = 9 hólf
-- Rollback: supabase/rollback/20261010090000_cc225_verdvakt_svaedi_rollback.sql
-- Spegill: verdmat-ai/supabase/migrations/20261010090000_cc225_verdvakt_svaedi.sql (orðrétt afrit)
--
-- Höfuðborgarsvæði = PÓSTNÚMERASKILGREINING septemberskýrslunnar, kafli 13 (Verðvaktin):
--   _audit/cc218_september/a3_lib.py, flokkar(): 101–116 (Reykjavík) + 170, 200–203, 206, 210, 212, 220–222, 225,
--   270, 271, 276 (höfuðborgarsvæði utan Rvk). Önnur ÞEKKT póstnúmer = landsbyggð; óþekkt sér (mælt 0 / 7.403).
--   ATH: aðrir kaflar skýrslunnar (3–6, 11) nota properties.region_tier, sem telur Suðurnes og Voga (230–262, 190–191)
--   til höfuðborgarsvæðis — 724 af 7.403 eignum á sölu (cc225 s01). Hér gildir póstnúmerareglan.
--   Reglan býr á EINUM stað: töflunni semantic.verdvakt_hbs_postnr. MV-ið og framendinn lesa hana.
--
-- Nefnari: NÝTT MV semantic.v_verdvakt_nefnarar_svaedi_v2 (9 hólf), sama „virk"- og nýbyggingarregla og
-- v_verdvakt_nefnarar_stadir_v2 (cc219 fasi 3). Það MV er ÓSNERT: lifandi framendi les það og varpar röðum eftir
-- `nybygg` — 9 raðir í því myndu gefa rangan nefnara frá beitingu til push. Fellt eftir að cc225 er lifandi.
-- Gólf: hólf birtist aðeins með nefnara ≥ 50 (regla kafla 13: „Sneiðar birtast aðeins með nefnara ≥50"); undir því
-- → stöðumerki á síðunni. Dálkurinn undir_golfi ber dóminn úr gagnalaginu.
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan

CREATE TABLE semantic.verdvakt_hbs_postnr (
  postnr  integer PRIMARY KEY CHECK (postnr BETWEEN 100 AND 999),
  regla   text NOT NULL DEFAULT 'cc218-a3-postnr'
);
COMMENT ON TABLE semantic.verdvakt_hbs_postnr IS
  'cc225: póstnúmer höfuðborgarsvæðis = skilgreining septemberskýrslu kafla 13 (cc218 a3_lib.flokkar). Eina lind reglunnar fyrir Verðvaktina.';
INSERT INTO semantic.verdvakt_hbs_postnr (postnr)
SELECT g FROM generate_series(101, 116) g
UNION ALL SELECT unnest(ARRAY[170, 200, 201, 202, 203, 206, 210, 212, 220, 221, 222, 225, 270, 271, 276]);
ALTER TABLE semantic.verdvakt_hbs_postnr ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON semantic.verdvakt_hbs_postnr FROM PUBLIC, anon, authenticated;
GRANT SELECT ON semantic.verdvakt_hbs_postnr TO anon, authenticated;
CREATE POLICY public_read ON semantic.verdvakt_hbs_postnr FOR SELECT TO anon, authenticated USING (true);

CREATE MATERIALIZED VIEW semantic.v_verdvakt_nefnarar_svaedi_v2 AS
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
), eign_sv AS (
  SELECT eign.fastnum, eign.nyb,
         CASE WHEN p.postnr IS NULL THEN 'othekkt'
              WHEN EXISTS (SELECT 1 FROM semantic.verdvakt_hbs_postnr h WHERE h.postnr = p.postnr::integer) THEN 'hbs'
              ELSE 'lands' END AS svaedi
    FROM eign LEFT JOIN properties p ON p.fastnum = eign.fastnum
), holf AS (
  SELECT sv.svaedi, st.nybygg
    FROM (VALUES ('allt'), ('hbs'), ('lands')) AS sv(svaedi)
   CROSS JOIN (VALUES ('med'), ('an'), ('adeins')) AS st(nybygg)
)
SELECT h.svaedi, h.nybygg,
       count(e.fastnum) AS n_eignir_a_solu,
       50 AS golf,
       count(e.fastnum) < 50 AS undir_golfi,
       (SELECT count(*) FROM eign_sv WHERE eign_sv.svaedi = 'othekkt') AS n_postnr_othekkt,
       'cc225-v1'::text AS regla_version,
       now() AS byggt_at
  FROM holf h
  LEFT JOIN eign_sv e
    ON (h.svaedi = 'allt' OR e.svaedi = h.svaedi)
   AND (h.nybygg = 'med' OR (h.nybygg = 'an' AND e.nyb IS NOT TRUE) OR (h.nybygg = 'adeins' AND e.nyb IS TRUE))
 GROUP BY h.svaedi, h.nybygg;

CREATE UNIQUE INDEX v_verdvakt_nefnarar_svaedi_v2_idx ON semantic.v_verdvakt_nefnarar_svaedi_v2 (svaedi, nybygg);
COMMENT ON MATERIALIZED VIEW semantic.v_verdvakt_nefnarar_svaedi_v2 IS
  'Verðvaktin (cc225): eignir (fastnúmer) á sölu per svæði (allt/hbs/lands, póstnúmeraregla kafla 13) × nýbyggingarstað (med/an/adeins); gólf 50. regla_version cc225-v1.';
REVOKE ALL ON semantic.v_verdvakt_nefnarar_svaedi_v2 FROM PUBLIC;
GRANT SELECT ON semantic.v_verdvakt_nefnarar_svaedi_v2 TO anon, authenticated;

COMMIT;
