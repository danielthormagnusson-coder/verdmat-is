-- Phase A · lifecycle pipe · migration 2 (additive, reversible).
-- Write-once discovery stamp on scraper.listings.
-- NO default: an ADD COLUMN DEFAULT now() would LOGICALLY backfill all existing
-- rows to now() = the "pretend-start" the lifecycle mandate forbids. Nullable +
-- no default => existing rows stay NULL (discovery history genuinely unknown);
-- new inserts set discovered_at explicitly from the mbl promoter. Write-once is
-- enforced application-side (excluded from the promoter's ON CONFLICT update set,
-- mirroring first_seen_at).
--
-- Rollback: app/scripts/lifecycle_discovered_at_rollback.sql

ALTER TABLE scraper.listings ADD COLUMN discovered_at timestamptz;
