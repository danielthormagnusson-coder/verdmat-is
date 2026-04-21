-- Bug 2 fix (2026-04-22): /eign/[fastnum] "Nýleg auglýsing" showed scrape timestamp
-- instead of the listing date. build_precompute.py now sorts latest-listing-per-
-- fastnum by effective_date rather than scraped_at; this column carries the
-- date we display. Idempotent — safe to replay on existing deployments.

ALTER TABLE properties
  ADD COLUMN IF NOT EXISTS effective_date_latest DATE;
