-- 20260615163101_step3d_listings_canonical_mbl_promote.sql
-- STEP 3D — schema additions to scraper.listings_canonical for the mbl promotion.
-- Design: D:\verdmat-is\STEP_3D_DESIGN_v1_draft.md (§3 matshluti, §7 raw fastano, §11 DDL);
--         locked in docs/DECISIONS.md 2026-06-15 (VIÐBÓT — 5 Q-svör).
--
-- Net-new, additive. ZERO impact on existing rows: the 1.266 visir/myigloo rows take
--   matshluti_unit_id=NULL, source_raw_fastnum=NULL (cross-source n/a, by design — those
--   sources carry no unit-index / no raw fastano), is_price_on_request=false.
-- Writes: service-role only (unchanged). RLS/grants unchanged (additive columns inherit
--   the existing table policy + the column-allowlisted views are not widened here).
--
-- SCOPE NOTE (Stage 1 finding, 2026-06-15): ck_rent_lease and lease_term_enum are LEFT
--   UNTOUCHED. ck_rent_lease only requires lease_term_class NOT NULL for tenure='rent';
--   Lota-1 rent (parsed_mbl_rent, residential) uses the existing enum value 'unspecified'
--   (same as visir derive_lease). The 'unknown_commercial' sentinel that the design §Q2
--   floated for commercial-rent is a LOTA-2 concern (negotiable atv) and would need a
--   separate ALTER TYPE ... ADD VALUE — deliberately NOT in this migration.
--
-- Rollback: no paired file (repo convention is forward-only). To undo, write a NEW
--   timestamped migration: DROP the 3 columns + DROP INDEX ix_lc_fastnum_unit, then
--   restore ck_price_pos to CHECK (price_amount > 0).
--
-- Applied via MCP apply_migration; the schema_migrations version is assigned by MCP at
--   apply time (≠ this filename's local-clock timestamp). Reconcile only if it matters.

-- 1. matshluti unit-index (mbl unit-suffix; NULL cross-source)
ALTER TABLE scraper.listings_canonical
  ADD COLUMN matshluti_unit_id smallint;
COMMENT ON COLUMN scraper.listings_canonical.matshluti_unit_id IS
  'mbl unit-index 0..99 derived from fastano = fastnum*10^k + matshluti. '
  '0 = mbl single-unit / building-base (7-digit fastano); 1..99 = unit suffix '
  '(8-/9-digit fastano). NULL = source has no unit-index (visir/myigloo), or '
  'mbl 6-/10-digit edge encoding that does not fit *10^k. Dedup Tier-1 keys on '
  '(fastnum, matshluti_unit_id) so a multi-unit building does not collapse to one row.';

-- 2. raw fastano lineage (mbl original; NULL cross-source)
ALTER TABLE scraper.listings_canonical
  ADD COLUMN source_raw_fastnum bigint;
COMMENT ON COLUMN scraper.listings_canonical.source_raw_fastnum IS
  'mbl original fastano (= fastnum*10^k + matshluti) preserved verbatim for lineage: '
  'debug, exact reconstruction (matshluti_unit_id alone is lossy — the multiplier k is '
  'dropped), and future HMS sub-unit granularity. NULL for visir/myigloo (n/a). '
  'fastnum (the 7-digit canonical) remains the FK into public.properties.';

-- 3. price-on-request flag (lets the verd=0 negotiable corpus in for Lota 2)
ALTER TABLE scraper.listings_canonical
  ADD COLUMN is_price_on_request boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN scraper.listings_canonical.is_price_on_request IS
  'True when the listing price is "samkvæmt tilboði" (verd=0 with an otherwise valid '
  'listing) — capture-mandate flag for the negotiable corpus. Existing visir price=1 '
  'sentinel rows are left false here (backfill is a separate, non-critical task). '
  'Pairs with the relaxed ck_price_pos: a row may have price_amount=0 only if this is true.';

-- 4. relax ck_price_pos so price-on-request rows are admissible
ALTER TABLE scraper.listings_canonical DROP CONSTRAINT ck_price_pos;
ALTER TABLE scraper.listings_canonical
  ADD CONSTRAINT ck_price_pos
  CHECK (price_amount > 0 OR is_price_on_request);

-- 5. dedup Tier-1 refinement: (fastnum, matshluti_unit_id), not bare fastnum.
--    The bare ix_lc_fastnum stays; this composite keeps multi-unit buildings distinct.
CREATE INDEX ix_lc_fastnum_unit
  ON scraper.listings_canonical (fastnum, matshluti_unit_id)
  WHERE fastnum IS NOT NULL;
