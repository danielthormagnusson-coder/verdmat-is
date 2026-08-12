-- predictions_rent_rollback_cc149.sql — æfður bakleikur (cc149, leigu-endursjónun þrep 3+4).
-- Skilar public.predictions_rent í ástandið eins og það var FYRIR cc149-flippið.
-- Keyrist í EINNI txn; replica-mode svo FK trufli ekki röðina.
BEGIN;
SET TRANSACTION READ WRITE;
SET LOCAL session_replication_role = 'replica';
TRUNCATE public.predictions_rent;
INSERT INTO public.predictions_rent SELECT * FROM public.predictions_rent_pre_cc149;
COMMIT;
