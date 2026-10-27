-- cc283 rollback: fjarlægir v9-þrískiptinguna. EYÐIR v9-röðum (útgáfur sem bera þrískiptingu) — þær eru endurreiknanlegar
-- með scripts/cc224_nybygging_verkefni.py; v8 og eldri standa óbreyttar. Skorðurnar endurheimtar ORÐRÉTT
-- (pg_get_constraintdef 27.10.2026).
BEGIN;
SET TRANSACTION READ WRITE;

DELETE FROM semantic.nybygging_verkefni WHERE n_auglyst IS NOT NULL;   -- FK ON DELETE CASCADE: einingar + solur_manadar
DELETE FROM semantic.nybygging_einingar WHERE thriskipting IS NOT NULL OR stada = 'othekkt';
DELETE FROM semantic.nybygging_solur_manadar WHERE oseldar_upphafi IS NULL;

ALTER TABLE semantic.nybygging_keyrslur DROP COLUMN kodi_hash;
ALTER TABLE semantic.nybygging_solur_manadar ALTER COLUMN oseldar_upphafi SET NOT NULL;

ALTER TABLE semantic.nybygging_einingar DROP CONSTRAINT nybygging_einingar_thriskipting_chk;
ALTER TABLE semantic.nybygging_einingar DROP CONSTRAINT nybygging_einingar_stada_check;
ALTER TABLE semantic.nybygging_einingar ADD CONSTRAINT nybygging_einingar_stada_check CHECK ((stada = ANY (ARRAY['seld'::text, 'magnsala'::text, 'heildarkaup'::text, 'a_solu'::text, 'oseld'::text])));
ALTER TABLE semantic.nybygging_einingar
  DROP COLUMN thriskipting, DROP COLUMN n_thinglyst, DROP COLUMN n_auglyst, DROP COLUMN n_othekkt,
  DROP COLUMN forsala_osynileg, DROP COLUMN forsala_astaedur, DROP COLUMN n_augl_an_fastnr;

ALTER TABLE semantic.nybygging_verkefni DROP CONSTRAINT nybygging_verkefni_thriskipting_chk;
ALTER TABLE semantic.nybygging_verkefni DROP CONSTRAINT nybygging_verkefni_hradi_chk;
ALTER TABLE semantic.nybygging_verkefni ADD CONSTRAINT nybygging_verkefni_hradi_chk CHECK ((((hradi_stada IS NULL) AND (hradi_glugga_fra IS NULL) AND (hradi_glugga_til IS NULL) AND (n_solur_90d IS NULL) AND (hradi_90d IS NULL) AND (hradi_oseldar IS NULL) AND (man_i_uppselt IS NULL)) OR ((hradi_stada = ANY (ARRAY['maelt'::text, 'faar_solur'::text, 'omaelanlegt'::text, 'uppselt'::text])) AND (hradi_glugga_til IS NOT NULL) AND (hradi_glugga_fra = (hradi_glugga_til - 89)) AND ((hradi_stada = 'omaelanlegt'::text) = (n_solur_90d IS NULL)) AND ((n_solur_90d IS NULL) = (hradi_oseldar IS NULL)) AND ((n_solur_90d IS NULL) OR ((n_solur_90d >= 0) AND (hradi_oseldar >= 0))) AND ((hradi_90d IS NOT NULL) = (COALESCE(n_solur_90d, 0) >= 5)) AND ((hradi_90d IS NULL) OR (hradi_90d = round((((n_solur_90d * 30))::numeric / 90.0), 2))) AND ((hradi_stada <> 'uppselt'::text) OR (hradi_oseldar = 0)) AND ((hradi_stada <> 'maelt'::text) OR ((n_solur_90d >= 5) AND (hradi_oseldar > 0))) AND ((hradi_stada <> 'faar_solur'::text) OR ((n_solur_90d < 5) AND (hradi_oseldar > 0))) AND ((man_i_uppselt IS NULL) OR ((hradi_stada = 'maelt'::text) AND (hradi_oseldar >= 5) AND (man_i_uppselt > (0)::numeric))) AND ((heildarkaup_fyrst IS NOT NULL) = (n_heildarkaup > 0)))));
ALTER TABLE semantic.nybygging_verkefni
  DROP COLUMN n_auglyst, DROP COLUMN n_othekkt, DROP COLUMN n_forsala_ibudir, DROP COLUMN n_forsala_thinglyst,
  DROP COLUMN n_forsala_auglyst, DROP COLUMN forsala_osynileg, DROP COLUMN forsala_hus, DROP COLUMN forsala_astaedur,
  DROP COLUMN n_augl_an_fastnr, DROP COLUMN n_augl_an_fastnr_otengd;
ALTER TABLE semantic.nybygging_verkefni
  ALTER COLUMN n_oseldar SET NOT NULL,
  ALTER COLUMN n_oseldar_oauglystar SET NOT NULL;

NOTIFY pgrst, 'reload schema';
COMMIT;
