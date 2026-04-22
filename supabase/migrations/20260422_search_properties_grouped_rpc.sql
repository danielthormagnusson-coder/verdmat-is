-- Bug 4 + Search UX overhaul (2026-04-22): two-tier autocomplete.
-- Step 1 aggregates matches by (heimilisfang, postnr, postheiti) so a fjölbýli
-- renders as one row with a unit count + tegund summary, instead of 5 flat
-- entries that crowd the dropdown. Single-unit addresses pass through
-- unchanged (n_units = 1 → client navigates directly).

CREATE OR REPLACE FUNCTION search_properties_grouped(term TEXT)
RETURNS TABLE (
  heimilisfang   TEXT,
  postnr         INT,
  postheiti      TEXT,
  sveitarfelag   TEXT,
  n_units        BIGINT,
  anchor_fastnum BIGINT,
  tegund_summary TEXT
)
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
  SELECT
    p.heimilisfang,
    p.postnr,
    p.postheiti,
    p.sveitarfelag,
    COUNT(*) AS n_units,
    MIN(p.fastnum) AS anchor_fastnum,
    STRING_AGG(DISTINCT p.tegund_raw, ', ' ORDER BY p.tegund_raw) AS tegund_summary
  FROM properties p
  WHERE p.is_residential = TRUE
    AND (
      p.heimilisfang ILIKE term || '%'
      OR p.postheiti  ILIKE term || '%'
    )
  GROUP BY p.heimilisfang, p.postnr, p.postheiti, p.sveitarfelag
  ORDER BY p.heimilisfang, p.postnr
  LIMIT 15;
$$;

GRANT EXECUTE ON FUNCTION search_properties_grouped(TEXT) TO anon, authenticated;
