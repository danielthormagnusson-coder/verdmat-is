-- valuation_tiers_rent_rollback_cc149.sql — æfður bakleikur (cc149, leigu-endursjónun þrep 3+4).
-- Skilar public.valuation_tiers_rent í ástandið eins og það var FYRIR cc149-flippið.
-- Keyrist í EINNI txn; replica-mode svo FK trufli ekki röðina.
BEGIN;
SET TRANSACTION READ WRITE;
SET LOCAL session_replication_role = 'replica';
TRUNCATE public.valuation_tiers_rent;
INSERT INTO public.valuation_tiers_rent SELECT * FROM public.valuation_tiers_rent_pre_cc149;
COMMIT;
