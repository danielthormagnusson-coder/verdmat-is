-- comps_v2_rollback_cc131.sql - aefdur bakleikur (cc131)
-- Keyrist i EINNI txn; replica-mode svo FK trufli ekki rodina.
BEGIN;
SET TRANSACTION READ WRITE;
SET LOCAL session_replication_role = 'replica';
TRUNCATE public.valuation_tiers;
INSERT INTO public.valuation_tiers SELECT * FROM public.valuation_tiers_pre_cc131;
TRUNCATE public.comps_index_v2;
INSERT INTO public.comps_index_v2 SELECT * FROM public.comps_index_v2_pre_cc131;
TRUNCATE public.comps_t5_basis;
INSERT INTO public.comps_t5_basis SELECT * FROM public.comps_t5_basis_pre_cc131;
TRUNCATE public.comps_drift_diagnostics;
INSERT INTO public.comps_drift_diagnostics SELECT * FROM public.comps_drift_diagnostics_pre_cc131;
COMMIT;
