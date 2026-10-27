-- cc283 (27.10.2026): /nybyggingar þrískipting — „þinglýst seld" / „auglýst" / „óþekkt staða"; „óseld" aldrei tala.
-- Skrifað af scripts/cc224_nybygging_verkefni.py útgáfu cc224-v9. v8-raðir (og allar eldri) standast óbreyttar:
-- nýju dálkarnir eru NULL í þeim, og skorðurnar leyfa annaðhvort gamla formið (n_oseldar fyllt, þrískipting NULL)
-- EÐA nýja (þrískipting fyllt, öll „óseld"-afleiða NULL) — aldrei bæði. Beitt með psycopg2 (lock_timeout 10 s,
-- statement_timeout 120 s), sannað með --prof (migration → v9-farmur settur inn → anon les → rollback → samanburður → ROLLBACK).
-- Heimildir: anon/authenticated hafa SELECT á töflunum (ekki dálkaheimildir) og RLS-stefnurnar *_les → nýir dálkar læsilegir.
BEGIN;
SET TRANSACTION READ WRITE;

-- ── verkefni ────────────────────────────────────────────────────────────────
ALTER TABLE semantic.nybygging_verkefni
  ALTER COLUMN n_oseldar DROP NOT NULL,
  ALTER COLUMN n_oseldar_oauglystar DROP NOT NULL,
  ADD COLUMN n_auglyst integer,
  ADD COLUMN n_othekkt integer,
  ADD COLUMN n_forsala_ibudir integer,
  ADD COLUMN n_forsala_thinglyst integer,
  ADD COLUMN n_forsala_auglyst integer,
  ADD COLUMN forsala_osynileg boolean,
  ADD COLUMN forsala_hus text[],
  ADD COLUMN forsala_astaedur text[],
  ADD COLUMN n_augl_an_fastnr integer,
  ADD COLUMN n_augl_an_fastnr_otengd integer;

COMMENT ON COLUMN semantic.nybygging_verkefni.n_auglyst IS 'cc283: íbúðir í virkri söluauglýsingu, ekki þinglýst seldar (= n_virkar; með auglýsingum án fastnr. tengdum með vissu)';
COMMENT ON COLUMN semantic.nybygging_verkefni.n_othekkt IS 'cc283: óþekkt staða (hvorki þinglýst sala né virk auglýsing) — AÐEINS í húsum þar sem kaupskrá getur skorið úr; forsöluhús aldrei talin';
COMMENT ON COLUMN semantic.nybygging_verkefni.n_forsala_ibudir IS 'cc283: íbúðir í húsum þar sem forsala er ósýnileg í kaupskrá (óskipt fastnr. ∨ B0–B2/óskráð ∨ án heimilisfangs ∨ 0 samningar frá 2021)';
COMMENT ON COLUMN semantic.nybygging_verkefni.n_forsala_thinglyst IS 'cc283: þar af þinglýst seldar (í n_seld)';
COMMENT ON COLUMN semantic.nybygging_verkefni.n_forsala_auglyst IS 'cc283: þar af auglýstar (í n_auglyst)';
COMMENT ON COLUMN semantic.nybygging_verkefni.forsala_hus IS 'cc283: heimilisföng forsöluhúsa; ''án heimilisfangs'' = fastnr. með heimilisfang NULL í properties';
COMMENT ON COLUMN semantic.nybygging_verkefni.forsala_astaedur IS 'cc283: oskipt / b0_b2 / an_heimilisfangs / hus_0_samninga';
COMMENT ON COLUMN semantic.nybygging_verkefni.n_augl_an_fastnr IS 'cc283: virkar auglýsingar án fastnr. tengdar einingu með vissu (gata+nr+stafur+póstnr, eitt verkefni)';
COMMENT ON COLUMN semantic.nybygging_verkefni.n_augl_an_fastnr_otengd IS 'cc283: virkar auglýsingar án fastnr. á húsi verkefnisins sem ekki varð tengd einingu (íbúðir standa sem óþekkt staða)';

ALTER TABLE semantic.nybygging_verkefni DROP CONSTRAINT nybygging_verkefni_hradi_chk;
ALTER TABLE semantic.nybygging_verkefni ADD CONSTRAINT nybygging_verkefni_hradi_chk CHECK (
  ((((hradi_stada IS NULL) AND (hradi_glugga_fra IS NULL) AND (hradi_glugga_til IS NULL) AND (n_solur_90d IS NULL) AND (hradi_90d IS NULL) AND (hradi_oseldar IS NULL) AND (man_i_uppselt IS NULL)) OR ((hradi_stada = ANY (ARRAY['maelt'::text, 'faar_solur'::text, 'omaelanlegt'::text, 'uppselt'::text])) AND (hradi_glugga_til IS NOT NULL) AND (hradi_glugga_fra = (hradi_glugga_til - 89)) AND ((hradi_stada = 'omaelanlegt'::text) = (n_solur_90d IS NULL)) AND ((n_solur_90d IS NULL) = (hradi_oseldar IS NULL)) AND ((n_solur_90d IS NULL) OR ((n_solur_90d >= 0) AND (hradi_oseldar >= 0))) AND ((hradi_90d IS NOT NULL) = (COALESCE(n_solur_90d, 0) >= 5)) AND ((hradi_90d IS NULL) OR (hradi_90d = round((((n_solur_90d * 30))::numeric / 90.0), 2))) AND ((hradi_stada <> 'uppselt'::text) OR (hradi_oseldar = 0)) AND ((hradi_stada <> 'maelt'::text) OR ((n_solur_90d >= 5) AND (hradi_oseldar > 0))) AND ((hradi_stada <> 'faar_solur'::text) OR ((n_solur_90d < 5) AND (hradi_oseldar > 0))) AND ((man_i_uppselt IS NULL) OR ((hradi_stada = 'maelt'::text) AND (hradi_oseldar >= 5) AND (man_i_uppselt > (0)::numeric))) AND ((heildarkaup_fyrst IS NOT NULL) = (n_heildarkaup > 0)))))
  OR (n_auglyst IS NOT NULL AND hradi_oseldar IS NULL AND man_i_uppselt IS NULL AND (
       (hradi_stada IS NULL AND hradi_glugga_fra IS NULL AND hradi_glugga_til IS NULL AND n_solur_90d IS NULL AND hradi_90d IS NULL)
    OR (hradi_stada = ANY (ARRAY['maelt','faar_solur','omaelanlegt','uppselt'])
        AND hradi_glugga_til IS NOT NULL AND hradi_glugga_fra = (hradi_glugga_til - 89)
        AND ((hradi_stada = 'omaelanlegt') = (n_solur_90d IS NULL))
        AND (n_solur_90d IS NULL OR n_solur_90d >= 0)
        AND ((hradi_90d IS NOT NULL) = (COALESCE(n_solur_90d, 0) >= 5))
        AND (hradi_90d IS NULL OR hradi_90d = round(((n_solur_90d * 30))::numeric / 90.0, 2))
        AND (hradi_stada <> 'maelt' OR n_solur_90d >= 5)
        AND (hradi_stada <> 'faar_solur' OR n_solur_90d < 5)
        AND ((heildarkaup_fyrst IS NOT NULL) = (n_heildarkaup > 0)))))
);

-- annaðhvort gamla formið (óseld-frádráttur) EÐA þrískiptingin — aldrei bæði í sömu röð
ALTER TABLE semantic.nybygging_verkefni ADD CONSTRAINT nybygging_verkefni_thriskipting_chk CHECK (
  (n_auglyst IS NULL AND n_othekkt IS NULL AND n_forsala_ibudir IS NULL AND n_forsala_thinglyst IS NULL
   AND n_forsala_auglyst IS NULL AND forsala_osynileg IS NULL AND forsala_hus IS NULL AND forsala_astaedur IS NULL
   AND n_augl_an_fastnr IS NULL AND n_augl_an_fastnr_otengd IS NULL AND n_oseldar IS NOT NULL)
  OR (n_oseldar IS NULL AND n_oseldar_oauglystar IS NULL AND hradi_oseldar IS NULL AND man_i_uppselt IS NULL
   AND n_auglyst = n_virkar AND n_othekkt >= 0
   AND n_forsala_ibudir BETWEEN 0 AND n_einingar
   AND n_forsala_thinglyst BETWEEN 0 AND LEAST(n_forsala_ibudir, n_seld)
   AND n_forsala_auglyst BETWEEN 0 AND LEAST(n_forsala_ibudir - n_forsala_thinglyst, n_auglyst)
   AND (n_einingar - n_forsala_ibudir) = (n_seld - n_forsala_thinglyst) + (n_auglyst - n_forsala_auglyst) + n_othekkt
   AND forsala_osynileg = (n_forsala_ibudir > 0)
   AND forsala_hus IS NOT NULL AND forsala_astaedur IS NOT NULL
   AND forsala_osynileg = (cardinality(forsala_hus) > 0)
   AND forsala_osynileg = (cardinality(forsala_astaedur) > 0)
   AND forsala_astaedur <@ ARRAY['oskipt','b0_b2','an_heimilisfangs','hus_0_samninga']::text[]
   AND n_augl_an_fastnr >= 0 AND n_augl_an_fastnr_otengd >= 0)
);

-- ── einingar ────────────────────────────────────────────────────────────────
ALTER TABLE semantic.nybygging_einingar
  ADD COLUMN thriskipting text,
  ADD COLUMN n_thinglyst integer,
  ADD COLUMN n_auglyst integer,
  ADD COLUMN n_othekkt integer,
  ADD COLUMN forsala_osynileg boolean,
  ADD COLUMN forsala_astaedur text[],
  ADD COLUMN n_augl_an_fastnr integer;

COMMENT ON COLUMN semantic.nybygging_einingar.thriskipting IS 'cc283: thinglyst_seld / auglyst / othekkt (óskipt fastnr. að hluta auglýst = auglyst; n_* bera skiptingu undireininga)';
COMMENT ON COLUMN semantic.nybygging_einingar.forsala_osynileg IS 'cc283: einingin er í húsi þar sem forsala er ósýnileg í kaupskrá';

ALTER TABLE semantic.nybygging_einingar DROP CONSTRAINT nybygging_einingar_stada_check;
ALTER TABLE semantic.nybygging_einingar ADD CONSTRAINT nybygging_einingar_stada_check
  CHECK (stada = ANY (ARRAY['seld','magnsala','heildarkaup','a_solu','oseld','othekkt']));

ALTER TABLE semantic.nybygging_einingar ADD CONSTRAINT nybygging_einingar_thriskipting_chk CHECK (
  (thriskipting IS NULL AND n_thinglyst IS NULL AND n_auglyst IS NULL AND n_othekkt IS NULL AND forsala_osynileg IS NULL
   AND forsala_astaedur IS NULL AND n_augl_an_fastnr IS NULL AND stada <> 'othekkt')
  OR (stada <> 'oseld' AND thriskipting = ANY (ARRAY['thinglyst_seld','auglyst','othekkt'])
   AND n_thinglyst >= 0 AND n_auglyst >= 0 AND n_othekkt >= 0
   AND n_thinglyst + n_auglyst + n_othekkt = n_undireiningar
   AND (thriskipting = 'thinglyst_seld') = (stada = ANY (ARRAY['seld','magnsala','heildarkaup']))
   AND (thriskipting = 'thinglyst_seld') = (n_thinglyst > 0)
   AND (thriskipting = 'auglyst') = (n_auglyst > 0)
   AND forsala_osynileg IS NOT NULL AND forsala_astaedur IS NOT NULL
   AND forsala_osynileg = (cardinality(forsala_astaedur) > 0)
   AND forsala_astaedur <@ ARRAY['oskipt','b0_b2','an_heimilisfangs','hus_0_samninga']::text[]
   AND (heimilisfang IS NOT NULL OR forsala_osynileg)            -- H1 í grunninum sjálfum
   AND n_augl_an_fastnr >= 0)
);

-- ── mánaðarsölur: fjöldi „óseldra" í upphafi mánaðar fer ekki í v9-úttak ────
ALTER TABLE semantic.nybygging_solur_manadar ALTER COLUMN oseldar_upphafi DROP NOT NULL;

-- ── keyrslur: kóði sem framleiddi keyrsluna (frysting afhendinga, cc283 lið 5) ─
ALTER TABLE semantic.nybygging_keyrslur ADD COLUMN kodi_hash text;

NOTIFY pgrst, 'reload schema';
COMMIT;
