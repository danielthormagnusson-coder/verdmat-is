-- cc28 — DROP á dauðum staging-artifacts (predictions_staging + júlí-parið)
--
-- SAMHENGI
--   DECISIONS.md 2026-07-03 ákvað DROP (ekki RLS-policy) á
--   public.predictions_staging. cc9-migrationin 20260714214317 setti RLS á
--   sem BRÁÐABIRGÐA-plástur meðan ákvörðunin beið framkvæmdar. Þessi
--   migration framkvæmir ákvörðunina og tekur júlí-parið með, mælt á sömu
--   sannreynslu.
--
-- SANNREYNSLA FYRIR DROP (cc28, 2026-07-18, sjá audit-skjal)
--   1a KYRRSTAÐA  : 0 keyrandi kóðavísanir í öllum þremur repo-um
--                   (app / precompute / verdmat-ai), 0 á D:-rót (77 .py),
--                   0 í Task Scheduler (7 verdmat-verk export'uð).
--                   Einu hittin eru skjöl + ein ATHUGASEMD í
--                   precompute/load_comps_v2.py:9 (vísar í töfluna sem
--                   fordæmi, snertir hana ekki).
--   1b HREYFING   : n_tup_upd=0, n_tup_del=0, idx_scan=NULL á öllum þremur.
--                   predictions_staging síðast lesin 2026-07-14 21:44Z
--                   (= cc9 RLS-úttektin sjálf). Júlí-parið 2026-06-30 19:11Z.
--   1c FLIPP      : precompute/flip_iter4r.py notar SÍNAR EIGIN töflur
--                   (predictions_iter4r_staging / feature_attributions_iter4r_staging,
--                   línur 39 + 107-110, "staging er einnota") — engin vísun
--                   í þessar. Júlí-mánaðarflippið er afstaðið.
--   DB-HÁÐI       : 0 views, 0 matviews, 0 föll, 0 pg_depend-tengsl.
--   KYNSLÓÐ       : allar bera model_version='iter4_final_v1' (predicted_at
--                   2026-07-01) — tveimur kynslóðum á eftir lifandi
--                   predictions (iter4r_20260716).
--
-- ROWCOUNT VIÐ DROP
--   public.predictions_staging                 167.503
--   public.predictions_july_staging            167.503
--   public.feature_attributions_july_staging 1.675.030
--
-- AFRIT (belti og axlabönd, þótt pre_iter4r-snapshotið standi)
--   D:\_rollback_backup\cc28_predictions_staging_20260718T210603Z.sql                24,7 MB
--   D:\_rollback_backup\cc28_predictions_july_staging_20260718T210603Z.sql           19,5 MB
--   D:\_rollback_backup\cc28_feature_attributions_july_staging_20260718T210603Z.sql  72,0 MB
--   Raðafjöldi sannreyndur INNI Í dumpunum: 3/3 PASS.
--
-- EKKI SNERT (líf mælt — HALT skv. cc28 lið 3)
--   public.predictions_rent_staging            158.314  rent_v1, 2026-05-01
--   public.feature_attributions_rent_staging 1.583.140
--   Ástæða: precompute/load_rent_staging.py SKRIFAR í þær (TRUNCATE+COPY),
--   RENT_MODEL_CARD.md skráir promotion sem OPNA ákvörðun, og lestur mældist
--   2026-07-18 09:46Z. Þessar lifa þar til leigu-flippið er afgreitt.

BEGIN;

DROP TABLE public.predictions_staging;
DROP TABLE public.predictions_july_staging;
DROP TABLE public.feature_attributions_july_staging;

COMMIT;
