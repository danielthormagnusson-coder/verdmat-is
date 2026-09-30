-- =====================================================================
-- cc219 fasi 2 — Verðvaktin v2: innan-breytingar úr VERÐSÖGU, dagsettar með ATHUGUN (cc60 „sást þann X")
-- Rollback: supabase/rollback/20260930200000_cc219_verdvakt_v2_rollback.sql
-- Spegill: verdmat-ai/supabase/migrations/20260930200000_cc219_verdvakt_v2.sql (orðrétt afrit, eins og cc188/cc190)
-- Rót (SKIL_CC219_1): v1 dagsetur innan-breytingu aðeins úr sópun (price_changed) og athuganaskrá. Fyrir 05.09
-- var sópunin eina lindin og sá ekki breytingar sem næturdeltað hafði þegar skrifað → 246 af 493 vantaði.
-- Frá 07.09 missir v1 enga (168/168); gatið er sögulegt og lokast hér með bakfyllingu úr hrá-sóknum 09.06–07.09
-- (ákvörðun Danna 30.09: frá fyrstu hrá-sókn, ekki 03.07).
--
-- v1 (semantic.v_verdvakt_breytingar / _nefnarar) STENDUR ÓBREYTT og hliðstætt — fellt í sér-örlotu eftir
-- 7 daga sannprófun v2 (BANN cc219). v1 fær COMMENT sem merkir það v1.
--
-- v2 skilgreining (regla_version 'cc219-v2'):
--   breyting    = tvær samliggjandi verðsöguraðir (id-röð) sömu auglýsingar, ólíkt verð, bæði ≥ 1 M; ALLAR per auglýsingu
--   dagsetning  = fyrsta athugun sem sá nýja verðið, forgangur (i) athuganaskrá (ii) hrá-bakfylling 09.06–07.09
--                 (iii) sópunaratburður; lind pöruð eftir TILVIKI (k-ta (fyrra,nýtt)-par ↔ k-ta umskipti lindar).
--                 Engin lind → ódagsett (talið í nefnurum, ekki birt). Id-svigun ekki notuð (ályktuð).
--   milli       = v1-regla óbreytt (eldri auglýsing horfin áður en ný sást), TALIN (ákvörðun Danna 30.09)
--   flokkur     = tveir flokkar (ákvörðun Danna 30.09): 'endurbirt á nýju verði' (milli) og
--                 'lækkað í auglýsingu' / 'hækkað í auglýsingu' (innan); stefna = 'laekkun' | 'haekkun'
--   afritun     = DISTINCT ON (fastnum, fyrra, nýtt) yfir milli + innan, elsta dagsetning vinnur (eins og v1)
--   gátir       = hlutdeild, árekstur, |Δ| ≥ 30 % (v1) + NÝTT grunsamleg: stökk > ×3 eða < ÷3 (ekki talin)
--   nefnari     = EIGNARSTIG: fastnum með virka sölu-íbúðaauglýsingu (scraper.v_eign_virk_auglysing), með
--                 draugafyrirvara úr scraper.thekjuprof (nýjasta mæling)
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- pooler-reglan

-- ---------------------------------------------------------------------
-- 1. Bakfylling úr hrá-sóknum (raw_mbl.db) — LÆST, skrifuð einu sinni af scripts/cc219_bakfylla_hra_athuganir.py
-- ---------------------------------------------------------------------
CREATE TABLE scraper.verdvakt_hra_athugun (
  listing_id         bigint      NOT NULL REFERENCES scraper.listings (listing_id),
  fyrra_verd         bigint      NOT NULL,
  nytt_verd          bigint      NOT NULL,
  tilvik             integer     NOT NULL,          -- k-ta umskipti (fyrra→nýtt) á auglýsingunni í hrá-sóknum
  sast_sidast_fyrra  timestamptz,                   -- síðasta sókn sem sá fyrra verðið
  sast_fyrst_nytt    timestamptz NOT NULL,          -- fyrsta sókn sem sá nýja verðið = dagsetning breytingar
  raw_id             bigint      NOT NULL,          -- raw_fetches.raw_id fyrstu sóknar nýja verðsins (raw_mbl.db)
  lind               text        NOT NULL DEFAULT 'raw_mbl',
  utgafa             text        NOT NULL,          -- t.d. 'cc219-bakfylling-v1'
  stofnad            timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (listing_id, fyrra_verd, nytt_verd, tilvik),
  CONSTRAINT hra_athugun_verd_chk CHECK (fyrra_verd <> nytt_verd AND fyrra_verd > 0 AND nytt_verd > 0 AND tilvik >= 1),
  CONSTRAINT hra_athugun_rod_chk  CHECK (sast_sidast_fyrra IS NULL OR sast_sidast_fyrra <= sast_fyrst_nytt)
);
COMMENT ON TABLE scraper.verdvakt_hra_athugun IS
  'cc219: athugaðar dagsetningar verðbreytinga úr eigin hrá-sóknum (raw_mbl.db list_page_sale*), bakfylling 09.06–07.09.2026. LÆST.';
ALTER TABLE scraper.verdvakt_hra_athugun ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE scraper.verdvakt_hra_athugun FROM PUBLIC, anon, authenticated, service_role;

-- ---------------------------------------------------------------------
-- 2. v1 merkt
-- ---------------------------------------------------------------------
COMMENT ON MATERIALIZED VIEW semantic.v_verdvakt_breytingar IS
  'Verðvaktin v1 (cc188/cc190). Hliðstætt v2 (cc219) til sannprófunar; fellt í sér-örlotu. Innan-breytingar aðeins sópun + athuganaskrá.';
COMMENT ON MATERIALIZED VIEW semantic.v_verdvakt_nefnarar IS 'Verðvaktin v1 nefnarar (cc188). Hliðstætt v2 (cc219).';

-- ---------------------------------------------------------------------
-- 3. semantic.v_verdvakt_breytingar_v2 — sömu dálkar og v1 + dags_lind, endurbirting, grunsamleg, regla_version
-- ---------------------------------------------------------------------
CREATE MATERIALIZED VIEW semantic.v_verdvakt_breytingar_v2 AS
WITH lst AS (
  SELECT l.listing_id, l.source, l.source_listing_id, l.fastnum, l.size_sqm, l.rooms, l.addr_text, l.byggar, l.status,
         l.first_seen_at, l.last_seen_at, l.price_amount,
         COALESCE((SELECT ph.price_amount FROM scraper.listing_price_history ph
                    WHERE ph.source = l.source AND ph.source_listing_id = l.source_listing_id AND ph.price_amount >= 1000000
                    ORDER BY ph.id LIMIT 1), l.price_amount) AS fyrsta_verd,
         l.addr_text ~* 'hlutdeild' OR l.lysing ~* 'hlutdeildarl[áa]n|hlutdeildarkaup' AS hlutd_texti,
         NOT EXISTS (SELECT 1 FROM scraper.listing_lifecycle_events e
                      WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id
                        AND e.event_type = 'withdrawn_confirmed'::scraper.lifecycle_event_enum) AS an_terminal
    FROM scraper.listings l
   WHERE l.tenure = 'sale' AND l.category = 'residential' AND l.fastnum IS NOT NULL
     AND l.price_amount IS NOT NULL AND l.price_amount >= 1000000 AND NOT COALESCE(l.is_price_on_request, false)
), seq AS (
  SELECT lst.*, lag(lst.price_amount) OVER w AS prev_verd, lag(lst.last_seen_at) OVER w AS prev_sast, lag(lst.listing_id) OVER w AS prev_lid
    FROM lst WINDOW w AS (PARTITION BY lst.fastnum, lst.size_sqm, lst.rooms ORDER BY lst.last_seen_at, lst.listing_id)
), milli AS (
  SELECT seq.listing_id, 'milli'::text AS teg, seq.prev_verd AS fyrra_verd, seq.prev_sast AS fyrra_sast, 'sidast'::text AS fyrra_sast_teg,
         seq.fyrsta_verd AS nytt_verd, seq.first_seen_at AS nytt_sast, seq.prev_lid AS fyrri_listing_id, 'endurbirting'::text AS dags_lind
    FROM seq WHERE seq.prev_verd IS NOT NULL AND seq.prev_sast < seq.first_seen_at AND seq.prev_verd <> seq.fyrsta_verd
), ph AS (
  SELECT l.listing_id, ph.id, ph.price_amount AS nytt,
         lag(ph.price_amount) OVER (PARTITION BY ph.source, ph.source_listing_id ORDER BY ph.id) AS fyrra
    FROM scraper.listing_price_history ph JOIN lst l USING (source, source_listing_id)
), bp AS (
  SELECT ph.listing_id, ph.fyrra, ph.nytt, ph.id,
         row_number() OVER (PARTITION BY ph.listing_id, ph.fyrra, ph.nytt ORDER BY ph.id) AS tilvik
    FROM ph WHERE ph.fyrra IS NOT NULL AND ph.fyrra <> ph.nytt AND ph.fyrra >= 1000000 AND ph.nytt >= 1000000
), ath0 AS (
  SELECT a.listing_id, a.price_amount, a.fyrst_sed,
         lag(a.price_amount) OVER w AS prev, lag(a.sidast_sed) OVER w AS prev_sidast
    FROM scraper.verdvakt_athuganir a WINDOW w AS (PARTITION BY a.listing_id ORDER BY a.fyrst_sed)
), ath AS (
  SELECT ath0.listing_id, ath0.prev AS fyrra, ath0.price_amount AS nytt, ath0.fyrst_sed, ath0.prev_sidast,
         row_number() OVER (PARTITION BY ath0.listing_id, ath0.prev, ath0.price_amount ORDER BY ath0.fyrst_sed) AS tilvik
    FROM ath0 WHERE ath0.prev IS NOT NULL AND ath0.prev <> ath0.price_amount
), sop AS (
  SELECT l.listing_id, (e.evidence ->> 'old')::bigint AS fyrra, (e.evidence ->> 'new')::bigint AS nytt, e.event_at,
         lag(e.event_at) OVER (PARTITION BY e.source, e.source_listing_id ORDER BY e.event_at) AS fyrri_event,
         row_number() OVER (PARTITION BY l.listing_id, (e.evidence ->> 'old')::bigint, (e.evidence ->> 'new')::bigint ORDER BY e.event_at) AS tilvik
    FROM scraper.listing_lifecycle_events e JOIN lst l USING (source, source_listing_id)
   WHERE e.event_type = 'price_changed'::scraper.lifecycle_event_enum
), innan AS (
  SELECT bp.listing_id, 'innan'::text AS teg, bp.fyrra AS fyrra_verd,
         COALESCE(ath.prev_sidast, h.sast_sidast_fyrra, s.fyrri_event, l.first_seen_at) AS fyrra_sast,
         CASE WHEN COALESCE(ath.prev_sidast, h.sast_sidast_fyrra, s.fyrri_event) IS NULL THEN 'fyrst' ELSE 'sidast' END AS fyrra_sast_teg,
         bp.nytt AS nytt_verd,
         COALESCE(ath.fyrst_sed, h.sast_fyrst_nytt, s.event_at) AS nytt_sast,
         NULL::bigint AS fyrri_listing_id,
         CASE WHEN ath.fyrst_sed IS NOT NULL THEN 'athuganaskra' WHEN h.sast_fyrst_nytt IS NOT NULL THEN 'hra_bakfylling' ELSE 'sopun' END AS dags_lind
    FROM bp
    JOIN lst l USING (listing_id)
    LEFT JOIN ath ON ath.listing_id = bp.listing_id AND ath.fyrra = bp.fyrra AND ath.nytt = bp.nytt AND ath.tilvik = bp.tilvik
    LEFT JOIN scraper.verdvakt_hra_athugun h ON h.listing_id = bp.listing_id AND h.fyrra_verd = bp.fyrra AND h.nytt_verd = bp.nytt AND h.tilvik = bp.tilvik
    LEFT JOIN sop s ON s.listing_id = bp.listing_id AND s.fyrra = bp.fyrra AND s.nytt = bp.nytt AND s.tilvik = bp.tilvik
   WHERE COALESCE(ath.fyrst_sed, h.sast_fyrst_nytt, s.event_at) IS NOT NULL
), ch0 AS (
  SELECT milli.listing_id, milli.teg, milli.fyrra_verd, milli.fyrra_sast, milli.fyrra_sast_teg, milli.nytt_verd, milli.nytt_sast, milli.fyrri_listing_id, milli.dags_lind FROM milli
  UNION ALL
  SELECT innan.listing_id, innan.teg, innan.fyrra_verd, innan.fyrra_sast, innan.fyrra_sast_teg, innan.nytt_verd, innan.nytt_sast, innan.fyrri_listing_id, innan.dags_lind FROM innan
), ch1 AS (
  SELECT DISTINCT ON (l.fastnum, c.fyrra_verd, c.nytt_verd) c.*, l.source, l.source_listing_id, l.fastnum, l.size_sqm, l.rooms, l.addr_text, l.byggar, l.hlutd_texti
    FROM ch0 c JOIN lst l USING (listing_id)
   ORDER BY l.fastnum, c.fyrra_verd, c.nytt_verd, c.nytt_sast, c.listing_id
), virk AS (
  SELECT lst.fastnum, lst.size_sqm, lst.rooms FROM lst WHERE lst.status = 'active' AND lst.an_terminal GROUP BY lst.fastnum, lst.size_sqm, lst.rooms
), ch2 AS (
  SELECT c.*,
         c.nytt_verd - c.fyrra_verd AS breyting_kr,
         round((c.nytt_verd - c.fyrra_verd)::numeric / c.fyrra_verd::numeric, 4) AS breyting_hlutfall,
         c.hlutd_texti OR (c.nytt_verd::numeric / c.fyrra_verd::numeric) BETWEEN 0.748 AND 0.752
                       OR (c.nytt_verd::numeric / c.fyrra_verd::numeric) BETWEEN 1.331 AND 1.336 AS hlutd_grunur,
         EXISTS (SELECT 1 FROM ch1 r WHERE r.fastnum = c.fastnum AND r.size_sqm IS NOT DISTINCT FROM c.size_sqm AND r.rooms IS NOT DISTINCT FROM c.rooms
                   AND r.fyrra_verd = c.nytt_verd AND r.nytt_verd = c.fyrra_verd
                   AND abs(EXTRACT(epoch FROM r.nytt_sast - c.nytt_sast)) <= (30 * 86400)::numeric) AS arekstur,
         EXISTS (SELECT 1 FROM virk v WHERE v.fastnum = c.fastnum AND v.size_sqm IS NOT DISTINCT FROM c.size_sqm AND v.rooms IS NOT DISTINCT FROM c.rooms) AS a_solu,
         (c.nytt_verd::numeric / c.fyrra_verd::numeric) > 3 OR (c.nytt_verd::numeric / c.fyrra_verd::numeric) < (1.0 / 3) AS grunsamleg
    FROM ch1 c
)
SELECT row_number() OVER (ORDER BY c.nytt_sast DESC, c.listing_id) AS rod_id,
       c.listing_id, c.source, c.source_listing_id, c.fastnum,
       COALESCE(p.heimilisfang, c.addr_text) AS heimilisfang, c.addr_text AS auglyst_heiti,
       p.postnr, p.postheiti, p.sveitarfelag, p.lat, p.lng,
       round(c.size_sqm, 1) AS size_sqm, c.rooms, COALESCE(c.byggar, p.byggar::integer) AS byggar,
       c.teg, c.fyrra_verd, c.fyrra_sast, c.fyrra_sast_teg, c.nytt_verd, c.nytt_sast,
       c.breyting_kr, c.breyting_hlutfall,
       CASE WHEN c.size_sqm > 0 THEN round(c.breyting_kr::numeric / c.size_sqm) ELSE NULL END AS breyting_kr_fm,
       c.a_solu,
       COALESCE(c.byggar, p.byggar::integer) >= (EXTRACT(year FROM CURRENT_DATE)::integer - 1)
         OR (p.byggingarstig = ANY (ARRAY['B0','B1','B2','B3']) AND p.matsstig ~ '^[0-6]$') AS nybygging,
       p.einflm IS NOT NULL AND abs(c.size_sqm - p.einflm) < 1
         AND EXISTS (SELECT 1 FROM jsonb_array_elements(COALESCE(p.matseiningar, '[]'::jsonb)) m(value)
                      WHERE (m.value ->> 'notkun_kodi') = ANY (ARRAY['504','529'])) AS staerd_telur_bilskur,
       c.hlutd_grunur, c.arekstur, abs(c.breyting_hlutfall) >= 0.30 AS grunur_villa,
       c.fyrri_listing_id,
       c.dags_lind,
       (c.teg = 'milli') AS endurbirting,
       CASE WHEN c.teg = 'milli' THEN 'endurbirt á nýju verði'
            WHEN c.breyting_kr < 0 THEN 'lækkað í auglýsingu' ELSE 'hækkað í auglýsingu' END AS flokkur,
       CASE WHEN c.breyting_kr < 0 THEN 'laekkun' ELSE 'haekkun' END AS stefna,
       c.grunsamleg,
       'cc219-v2'::text AS regla_version,
       now() AS byggt_at
  FROM ch2 c LEFT JOIN properties p ON p.fastnum = c.fastnum;

CREATE UNIQUE INDEX v_verdvakt_breytingar_v2_rod_idx ON semantic.v_verdvakt_breytingar_v2 (rod_id);
CREATE INDEX v_verdvakt_breytingar_v2_nytt_sast_idx ON semantic.v_verdvakt_breytingar_v2 (nytt_sast DESC);
COMMENT ON MATERIALIZED VIEW semantic.v_verdvakt_breytingar_v2 IS
  'Verðvaktin v2 (cc219): innan-breytingar úr verðsögu dagsettar með athugun (athuganaskrá → hrá-bakfylling 09.06–07.09 → sópun); flokkar endurbirt á nýju verði / lækkað-hækkað í auglýsingu. regla_version cc219-v2.';

-- ---------------------------------------------------------------------
-- 4. semantic.v_verdvakt_nefnarar_v2 — eignarstig + draugafyrirvari + lindir + útilokanir
-- ---------------------------------------------------------------------
CREATE MATERIALIZED VIEW semantic.v_verdvakt_nefnarar_v2 AS
WITH lst AS (
  SELECT l.listing_id, l.source, l.source_listing_id FROM scraper.listings l
   WHERE l.tenure = 'sale' AND l.category = 'residential' AND l.fastnum IS NOT NULL
     AND l.price_amount IS NOT NULL AND l.price_amount >= 1000000 AND NOT COALESCE(l.is_price_on_request, false)
), ph AS (
  SELECT ph.price_amount AS nytt, lag(ph.price_amount) OVER (PARTITION BY ph.source, ph.source_listing_id ORDER BY ph.id) AS fyrra
    FROM scraper.listing_price_history ph JOIN lst USING (source, source_listing_id)
), tp AS (
  SELECT t.dags, t.draug_n, t.draug_nefnari, t.draug_ovisst FROM scraper.thekjuprof t ORDER BY t.maelt_kl DESC LIMIT 1
), b AS (SELECT * FROM semantic.v_verdvakt_breytingar_v2)
SELECT 1 AS id, now() AS byggt_at, 'cc219-v2'::text AS regla_version,
       (SELECT count(DISTINCT v.fastnum) FROM scraper.v_eign_virk_auglysing v
         WHERE v.tenure = 'sale' AND v.category = 'residential' AND v.fastnum IS NOT NULL) AS n_eignir_a_solu,  -- = skilgreining septemberskýrslu (cc218 q12)
       (SELECT tp.dags FROM tp) AS draug_dags,
       (SELECT tp.draug_n FROM tp) AS draug_n,
       (SELECT tp.draug_nefnari FROM tp) AS draug_nefnari,
       (SELECT tp.draug_ovisst FROM tp) AS draug_ovisst,
       (SELECT count(*) FROM b) AS n_breytingar_alls,
       (SELECT count(*) FROM b WHERE b.teg = 'innan') AS n_innan,
       (SELECT count(*) FROM b WHERE b.teg = 'milli') AS n_endurbirtingar,
       (SELECT count(*) FROM b WHERE b.flokkur = 'endurbirt á nýju verði' AND NOT b.grunsamleg) AS n_endurbirt_nytt_verd,
       (SELECT count(*) FROM b WHERE b.flokkur = 'lækkað í auglýsingu' AND NOT b.grunsamleg) AS n_laekkad_i_auglysingu,
       (SELECT count(*) FROM b WHERE b.flokkur = 'hækkað í auglýsingu' AND NOT b.grunsamleg) AS n_haekkad_i_auglysingu,
       (SELECT count(*) FROM b WHERE b.dags_lind = 'athuganaskra') AS n_lind_athuganaskra,
       (SELECT count(*) FROM b WHERE b.dags_lind = 'hra_bakfylling') AS n_lind_hra,
       (SELECT count(*) FROM b WHERE b.dags_lind = 'sopun') AS n_lind_sopun,
       (SELECT count(*) FROM b WHERE b.grunsamleg) AS n_grunsamleg,
       (SELECT count(*) FROM b WHERE b.hlutd_grunur AND NOT b.grunsamleg) AS n_hlutd_grunur,
       (SELECT count(*) FROM b WHERE b.arekstur AND NOT b.hlutd_grunur AND NOT b.grunsamleg) AS n_arekstrar,
       (SELECT count(*) FROM b WHERE b.grunur_villa AND NOT b.hlutd_grunur AND NOT b.arekstur AND NOT b.grunsamleg) AS n_grunur_villa,
       (SELECT count(*) FROM ph WHERE ph.fyrra IS NOT NULL AND ph.fyrra <> ph.nytt AND ph.fyrra >= 1000000 AND ph.nytt >= 1000000)
         - (SELECT count(*) FROM semantic.v_verdvakt_breytingar_v2 x WHERE x.teg = 'innan') AS n_innan_odagsett_eda_afritud,
       (SELECT min(a.fyrst_sed)::date FROM scraper.verdvakt_athuganir a) AS athuganaskra_fra,
       (SELECT min(h.sast_fyrst_nytt)::date FROM scraper.verdvakt_hra_athugun h) AS bakfylling_fra,
       (SELECT max(h.sast_fyrst_nytt)::date FROM scraper.verdvakt_hra_athugun h) AS bakfylling_til,
       (SELECT count(*) FROM semantic.v_verdvakt_afsala) AS n_farnar_alls,
       (SELECT max(s.thinglystdags) FROM sales_history s WHERE s.onothaefur = 0) AS kaupskra_til;
CREATE UNIQUE INDEX v_verdvakt_nefnarar_v2_id_idx ON semantic.v_verdvakt_nefnarar_v2 (id);

-- ---------------------------------------------------------------------
-- 5. Heimildir — sama stefna og v1 (anon/authenticated SELECT á semantic-MV Verðvaktar)
-- ---------------------------------------------------------------------
REVOKE ALL ON semantic.v_verdvakt_breytingar_v2, semantic.v_verdvakt_nefnarar_v2 FROM PUBLIC;
GRANT SELECT ON semantic.v_verdvakt_breytingar_v2, semantic.v_verdvakt_nefnarar_v2 TO anon, authenticated;

COMMIT;
