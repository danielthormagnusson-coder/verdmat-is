-- cc284d — sjálfgefin réttindi: NÝIR hlutir sem postgres býr til í public/semantic/scraper fá ENGIN
-- réttindi til anon eða authenticated (töflur, sýnir, MV, runur, föll). Núverandi hlutir óbreyttir.
-- Rollback skrifað á undan: 20261031130000_cc284d_sjalfgefin_rettindi_ROLLBACK.sql
--
-- Hver ný tafla/sýn/fall sem www á að lesa fær GRANT sérstaklega í sinni migration (DECISIONS 2026-10-31).
--
-- Mæling 31.10: postgres er eini eigandi allra hluta í schemunum þremur (extension-hlutir undanskildir).
-- pg_default_acl bar færslur fyrir postgres AÐEINS í public (r/S/f → anon, authenticated, service_role).
-- semantic og scraper bera engar skema-færslur; þar gildir innbyggt sjálfgildi (aðeins eigandi), NEMA
-- föll: innbyggt sjálfgildi Postgres gefur PUBLIC (og þar með anon) EXECUTE á hverju nýju falli.
-- Skema-bundið REVOKE getur ekki afturkallað innbyggt/altækt grant, svo PUBLIC-EXECUTE er afturkallað altækt.
-- supabase_admin ber líka færslur í public; þær eru ekki í okkar valdi (ekki meðlimur) og gilda aðeins
-- um extension-hluti sem supabase_admin býr til.

begin;
set local lock_timeout = '3s';

alter default privileges for role postgres in schema public, semantic, scraper revoke all on tables    from anon, authenticated;
alter default privileges for role postgres in schema public, semantic, scraper revoke all on sequences from anon, authenticated;
alter default privileges for role postgres in schema public, semantic, scraper revoke all on functions from anon, authenticated;
alter default privileges for role postgres revoke execute on functions from public;

commit;
