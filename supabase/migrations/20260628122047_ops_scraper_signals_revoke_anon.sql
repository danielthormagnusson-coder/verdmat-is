-- Harden ops_scraper_signals EXECUTE down to service_role only.
--
-- The original 20260628093000 migration did `REVOKE ALL FROM PUBLIC` + `GRANT service_role`,
-- but Supabase default privileges (ALTER DEFAULT PRIVILEGES ... GRANT EXECUTE ON FUNCTIONS
-- TO anon, authenticated, service_role) had already granted EXECUTE to anon + authenticated
-- as EXPLICIT role grants at CREATE time. `REVOKE FROM PUBLIC` does not remove explicit role
-- grants, so anon + authenticated retained EXECUTE — widening the API surface the LEIÐ 2 RPC
-- was chosen to keep narrow. Revoke them explicitly; service_role (the /ops client) keeps it.
REVOKE EXECUTE ON FUNCTION public.ops_scraper_signals() FROM anon, authenticated, PUBLIC;

-- reload PostgREST schema cache (also clears any stale PGRST202 on the function)
NOTIFY pgrst, 'reload schema';
