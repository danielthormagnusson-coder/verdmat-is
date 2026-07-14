-- disk_io_read_indexes — mótvægi við Disk-IO-Budget viðvörun 14.07 (DISK_IO_GREINING_20260714T2131Z.md)
-- GATE: apply aðeins eftir samþykki; taka utan nætur-glugga (00:55–06:30) — stuttir locks á properties/comps_index.
-- Rollback: sjá blokk neðst.

-- 1) Nætur-promoterarnir (promote_mbl/myigloo/visir) lesa
--    (fastnum, heimilisfang, postnr, einflm, lat, lng) WHERE postnr = ANY(...)
--    ~nóttlega yfir 80%+ af 413 MB töflunni. Covering-index (~25-35 MB) gerir það
--    að index-only skanni sem situr í shared_buffers. Leysir idx_properties_postnr af hólmi.
CREATE INDEX idx_properties_postnr_covering
  ON public.properties (postnr)
  INCLUDE (fastnum, heimilisfang, einflm, lat, lng);

DROP INDEX public.idx_properties_postnr;  -- sama leiðandi lykill; covering-indexið þjónar öllum fyrri notendum

-- 2) fetch_hms_einflm (daily_sales_refresh 02:30 + backfill):
--    SELECT fastnum, einflm FROM properties WHERE einflm IS NOT NULL (204K raðir)
--    var full-skann; partial covering-index (~7 MB) gerir index-only.
CREATE INDEX idx_properties_einflm_ios
  ON public.properties (fastnum)
  INCLUDE (einflm)
  WHERE einflm IS NOT NULL;

-- 3) ops + markadur/modelstada „nýjasta scrape"-stimpill:
--    ORDER BY scraped_at_latest DESC NULLS LAST LIMIT 1 (með IS NOT NULL filter í app).
--    58.437 not-null raðir → ~1,5 MB index í stað 460 MB skann+sortu á kall.
CREATE INDEX idx_properties_scraped_at_notnull
  ON public.properties (scraped_at_latest DESC NULLS LAST)
  WHERE scraped_at_latest IS NOT NULL;

-- 4) ops „nýjasta sala í comps"-stimpill: comps_index (1,1M raðir) hafði aðeins PK
--    (fastnum, rank) → ORDER BY last_sale_date DESC LIMIT 1 var 160 MB sorta á kall.
CREATE INDEX idx_comps_index_last_sale_date
  ON public.comps_index (last_sale_date DESC NULLS LAST);

-- ---------------------------------------------------------------------------
-- ROLLBACK (handvirkt, ef þarf):
--   DROP INDEX public.idx_properties_postnr_covering;
--   DROP INDEX public.idx_properties_einflm_ios;
--   DROP INDEX public.idx_properties_scraped_at_notnull;
--   DROP INDEX public.idx_comps_index_last_sale_date;
--   CREATE INDEX idx_properties_postnr ON public.properties USING btree (postnr);
