-- valuation_tiers_rent_rollback_cc135.sql - aefdur bakleikur (cc135)
-- Keyrist i EINNI txn; replica-mode svo FK trufli ekki rodina.
BEGIN;
SET TRANSACTION READ WRITE;
SET LOCAL session_replication_role = 'replica';
TRUNCATE public.valuation_tiers_rent;
INSERT INTO public.valuation_tiers_rent SELECT * FROM public.valuation_tiers_rent_pre_cc135;
COMMIT;
