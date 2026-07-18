-- ROLLBACK fyrir 20260718210603_cc28_drop_dead_staging.sql
--
-- Endurreisn er TVÍÞÆTT: skemað hér að neðan, gögnin úr dumpunum.
-- Gögnin eru EKKI í þessari skrá (167.503 + 167.503 + 1.675.030 raðir).
--
-- SKREF 1 — skema (keyrðu þennan hluta):

BEGIN;

CREATE TABLE public.predictions_staging (
    fastnum bigint NOT NULL,
    real_pred_mean bigint,
    real_pred_median bigint,
    real_pred_lo80 bigint,
    real_pred_hi80 bigint,
    real_pred_lo95 bigint,
    real_pred_hi95 bigint,
    model_group text,
    segment text,
    model_version text,
    calibration_version text,
    predicted_at date,
    confidence_grade text,
    calibration_source text
);

CREATE TABLE public.predictions_july_staging (
    fastnum bigint NOT NULL,
    real_pred_mean bigint,
    real_pred_median bigint,
    real_pred_lo80 bigint,
    real_pred_hi80 bigint,
    real_pred_lo95 bigint,
    real_pred_hi95 bigint,
    model_group text,
    segment text,
    model_version text,
    calibration_version text,
    predicted_at date
);

CREATE TABLE public.feature_attributions_july_staging (
    fastnum bigint NOT NULL,
    rank smallint NOT NULL,
    feature_name text,
    feature_value text,
    shap_log_contribution numeric,
    real_isk_impact bigint
);

-- SKYLDA: þessar fæðast LOKAÐAR (RLS á, engin policy, engin anon/auth grant)
-- — sama staða og þær höfðu við DROP. Ekki sleppa þessu skrefi.
ALTER TABLE public.predictions_staging ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.predictions_july_staging ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_attributions_july_staging ENABLE ROW LEVEL SECURITY;

COMMIT;

-- SKREF 2 — gögn (úr dumpunum, utan þessarar skráar):
--
--   psql "$DSN" -f D:\_rollback_backup\cc28_predictions_staging_20260718T210603Z.sql
--   psql "$DSN" -f D:\_rollback_backup\cc28_predictions_july_staging_20260718T210603Z.sql
--   psql "$DSN" -f D:\_rollback_backup\cc28_feature_attributions_july_staging_20260718T210603Z.sql
--
--   ATH: dumparnir bera SÍNAR EIGIN CREATE TABLE-setningar (pg_dump
--   --schema=public --table=... --no-owner --no-privileges). Ef þú keyrir
--   dumpana beint á hreint umhverfi skaltu SLEPPA skrefi 1 og keyra þess í
--   stað ENABLE ROW LEVEL SECURITY-línurnar þrjár á eftir — dumparnir bera
--   ekki RLS-stöðuna og skilja töflurnar eftir OPNAR ef eigandi er ekki postgres.
--
-- SKREF 3 — sannreyning eftir endurreisn:
--
--   SELECT 'predictions_staging', count(*) FROM public.predictions_staging
--   UNION ALL SELECT 'predictions_july_staging', count(*) FROM public.predictions_july_staging
--   UNION ALL SELECT 'feature_attributions_july_staging', count(*) FROM public.feature_attributions_july_staging;
--   -- vænt: 167503 / 167503 / 1675030
--
--   SELECT relname, relrowsecurity FROM pg_class
--   WHERE relname IN ('predictions_staging','predictions_july_staging','feature_attributions_july_staging');
--   -- vænt: allar true
