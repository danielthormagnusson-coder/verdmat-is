-- cc362 rollback: fjarlægir lesflöt sölusögu (fjögur föll) og vísinn á scraper.auglysinga_atburdir(fastnum).
-- Skrifað Á UNDAN migration (WP). BEGIN/COMMIT eru ekki hér: beitingarskriftan stýrir færslunni (lock_timeout 5s).
-- Engin gögn: lesflöturinn reiknar úr scraper.listings, listing_lifecycle_events, listing_price_history,
-- auglysinga_atburdir og public.sales_history, og ekkert er geymt. Ekkert annað les föllin fyrr en C er birt.
DROP FUNCTION IF EXISTS public.solusaga_til(bigint);
DROP FUNCTION IF EXISTS public.solusaga(bigint);
DROP FUNCTION IF EXISTS public.soluferli_opin(bigint[]);
DROP FUNCTION IF EXISTS scraper.soluferli(bigint[]);
DROP INDEX IF EXISTS scraper.auglysinga_atburdir_fastnum;
NOTIFY pgrst, 'reload schema';
