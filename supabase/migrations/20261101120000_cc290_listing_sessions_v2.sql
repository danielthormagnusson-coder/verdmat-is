-- cc290 — AUGLÝSINGALOTUR v2: evalue-safnið (frosið 2026-04-15) ∪ lifandi mbl-sókn (scraper.listings), sameinað á mbl-id.
--
-- ÁKVÖRÐUN 31.10 (GO Danna, SKIL_CC290 viðauki): listing_sessions_v2 í prófunarútgáfu; gamla scraper.listing_sessions (cc85)
-- stendur ÓSNERT. Eini neytandi: scripts/reikna_markadsgreiningar.mjs í verdmat-ai (keyrt staðbundið með eigandaréttindum).
-- www les EKKERT héðan → engin GRANT; RLS á töflunni og REVOKE ALL frá anon/authenticated á öllum hlutum (cc284-reglan).
--
-- REGLA (cc85 §1.1, óbreytt): ný lota ⟺ opnun_i ≥ MAX(lokun_1..i-1) + (gap_dagar+1) dagar, korn fastnum, gap_dagar úr
--   scraper.session_config (90). „+1“ endurgerir Python-skilgreiningu cc85 ((a−b).days > 90 ⟺ a−b ≥ 91 dagar) svo
--   evalue-hlutinn endurgerir listing_sessions nákvæmlega (sannað í --prof).
-- ATBURÐIR:
--   evalue   : opnun = lokun = effective_date (ein dagsetning per birting, eins og cc85). Hlaðið einu sinni úr
--              D:\listings_v2.pkl með scripts/c2 (--beita), byggt_ur = 'listings_v2.pkl@2026-04-15'.
--   mbl_live : scraper.listings (tenure='sale', fastnum not null, innlent 3-stafa póstnúmer).
--              opnun = first_seen_at (mbl endurdagsetur listed_at), lokun = coalesce(withdrawn_at, last_seen_at) (efri mörk).
--              vinstri_ritskodud = first_seen_at < 2026-06-15 (fyrsta heilsókn: raunopnun óþekkt) NEMA id sé líka í evalue.
-- TVÍTALNINGARVÖRN: sama mbl-id í báðum (1.443 mæld 31.10) → evalue-röðin víkur, lifandi röðin heldur og opnun =
--   least(elsta evalue-dags, first_seen_at). Falspróf í --prof: 0 id í báðum heimildum á atburðasýninni.
-- VERÐ: þús. kr; miðgildi yfir ekki-NULL gildi (0 meðtalið) — sama merking og cc85, svo evalue-hlutinn endurgerist.

CREATE TABLE scraper.auglysinga_atburdir (
  heimild    text        NOT NULL CHECK (heimild IN ('evalue')),
  augl_id    text        NOT NULL CHECK (augl_id ~ '^[0-9]+$'),
  fastnum    bigint      NOT NULL,
  opnun      timestamptz NOT NULL,
  lokun      timestamptz NOT NULL CHECK (lokun >= opnun),
  verd_thus  bigint,
  einflm     double precision,                 -- HRÁTT (cc85 rúnnar eftir miðgildi)
  byggt_ur   text        NOT NULL,
  PRIMARY KEY (heimild, augl_id, opnun)
);
CREATE INDEX auglysinga_atburdir_augl_id ON scraper.auglysinga_atburdir (augl_id);
COMMENT ON TABLE scraper.auglysinga_atburdir IS
  'cc290: auglýsingaatburðir sem EKKI eru í scraper.listings (evalue-safnið, frosið 2026-04-15). Ein röð per birting (augl_id, dagsetning). ÞÚS. KR.';
ALTER TABLE scraper.auglysinga_atburdir ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON scraper.auglysinga_atburdir FROM anon, authenticated;

CREATE VIEW scraper.v_auglysinga_atburdir AS
WITH ev_first AS (
  SELECT augl_id, min(opnun) AS opnun FROM scraper.auglysinga_atburdir GROUP BY augl_id
), live AS (
  SELECT l.source_listing_id AS augl_id, l.fastnum, l.first_seen_at, coalesce(l.withdrawn_at, l.last_seen_at) AS lokun,
         round(l.price_amount / 1000.0)::bigint AS verd_thus, l.size_sqm::double precision AS einflm, (l.status = 'active') AS opin
    FROM scraper.listings l
   WHERE l.source = 'mbl' AND l.tenure = 'sale' AND l.fastnum IS NOT NULL
     AND coalesce(l.addr_postcode, '0') ~ '^[0-9]{3}$'
)
SELECT 'mbl_live'::text AS heimild, v.augl_id, v.fastnum,
       CASE WHEN f.opnun IS NOT NULL THEN least(v.first_seen_at, f.opnun) ELSE v.first_seen_at END AS opnun,
       greatest(v.lokun, v.first_seen_at) AS lokun, v.verd_thus, v.einflm,
       (f.opnun IS NULL AND v.first_seen_at < timestamptz '2026-06-15 00:00:00+00') AS vinstri_ritskodud,
       v.opin
  FROM live v LEFT JOIN ev_first f ON f.augl_id = v.augl_id
UNION ALL
SELECT a.heimild, a.augl_id, a.fastnum, a.opnun, a.lokun, a.verd_thus, a.einflm, false, false
  FROM scraper.auglysinga_atburdir a
 WHERE NOT EXISTS (SELECT 1 FROM scraper.listings l
                    WHERE l.source = 'mbl' AND l.tenure = 'sale' AND l.fastnum IS NOT NULL
                      AND coalesce(l.addr_postcode, '0') ~ '^[0-9]{3}$'
                      AND l.source_listing_id = a.augl_id);
COMMENT ON VIEW scraper.v_auglysinga_atburdir IS
  'cc290: allir auglýsingaatburðir (evalue ∪ lifandi mbl), EIN heimild per mbl-id (lifandi röð heldur; evalue-tvífari víkur).';
REVOKE ALL ON scraper.v_auglysinga_atburdir FROM anon, authenticated;

CREATE VIEW scraper.listing_sessions_v2 AS
WITH cfg AS (
  SELECT gildi FROM scraper.session_config WHERE lykill = 'gap_dagar'
), m AS (
  SELECT e.*, max(e.lokun) OVER (PARTITION BY e.fastnum ORDER BY e.opnun, e.augl_id
                                 ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS maxlok_fyrri
    FROM scraper.v_auglysinga_atburdir e
), n AS (
  SELECT m.*, sum(CASE WHEN m.maxlok_fyrri IS NULL
                         OR m.opnun >= m.maxlok_fyrri + make_interval(days => (SELECT gildi FROM cfg) + 1)
                       THEN 1 ELSE 0 END)
              OVER (PARTITION BY m.fastnum ORDER BY m.opnun, m.augl_id ROWS UNBOUNDED PRECEDING) AS lota_nr
    FROM m
), st AS (
  SELECT fastnum, count(DISTINCT round(10 * einflm)) AS n_olikar_staerdir FROM scraper.v_auglysinga_atburdir GROUP BY fastnum
), s AS (
  SELECT n.fastnum, n.lota_nr,
         min(n.opnun) AS opnun_ts, max(n.lokun) AS lokun_ts,
         count(*) AS n_atburdir, count(DISTINCT n.augl_id) AS n_auglysingar,
         round(percentile_cont(0.5) WITHIN GROUP (ORDER BY n.verd_thus))::bigint AS verd_midgildi_thus,
         (round(10 * percentile_cont(0.5) WITHIN GROUP (ORDER BY n.einflm)) / 10)::numeric(12,1) AS einflm_midgildi,  -- round(float8) = hálft að sléttu, eins og pandas (cc85)
         array_agg(DISTINCT n.heimild ORDER BY n.heimild) AS heimildir,
         bool_or(n.opin) AS opin,
         (array_agg(n.vinstri_ritskodud ORDER BY n.opnun, n.augl_id))[1] AS vinstri_ritskodud
    FROM n GROUP BY n.fastnum, n.lota_nr
)
SELECT s.fastnum, s.lota_nr::smallint AS lota_nr,
       (s.opnun_ts AT TIME ZONE 'UTC')::date AS lota_fra, (s.lokun_ts AT TIME ZONE 'UTC')::date AS lota_til,
       s.n_atburdir::int AS n_atburdir, s.n_auglysingar::int AS n_auglysingar,
       s.verd_midgildi_thus, s.einflm_midgildi, st.n_olikar_staerdir::smallint AS n_olikar_staerdir,
       s.heimildir, s.vinstri_ritskodud, s.opin,
       (SELECT gildi FROM cfg)::smallint AS gap_dagar
  FROM s JOIN st USING (fastnum);
COMMENT ON VIEW scraper.listing_sessions_v2 IS
  'cc290: auglýsingalotur úr evalue (frosið 2026-04-15) ∪ lifandi mbl (2026-05→), sama regla og cc85. heimildir = uppruni lotu; '
  'vinstri_ritskodud = fyrsti atburður lotunnar er lifandi auglýsing úr fyrstu heilsókn (raunopnun óþekkt) — má ekki teljast sem endurkoma. '
  'Gatið 2025-08..2026-05 er EKKI fyllt (SKIL_CC290). ÞÚS. KR.';
REVOKE ALL ON scraper.listing_sessions_v2 FROM anon, authenticated;
