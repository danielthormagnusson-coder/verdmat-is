-- cc234 (GO Danna 11.10.2026): tvíauglýsingarlína á verkefnissíðu — „N íbúðir eru nú auglýstar bæði til sölu og leigu" (birt ef N >= 2).
--   verkefni.n_tviaugl_nu = fastanúmer verkefnisins sem eru NÚ samtímis í mbl-söluauglýsingu (fundin lifandi í sópun, ekki last_seen_at)
--                           og virkri leiguauglýsingu (myigloo/mbl). Hlutmengi n_leiga. Aðferð: app/scripts/nyb_tviaugl.py.
--   verkefni.leiguadili   = birtanlegt heiti leiguaðila (aðeins leigufélag á leyfislista eða sölustofa) sem auglýsir >= 50 % af N; annars null.
--                           Einstaklingar og önnur félög aldrei.
--   verkefni.leiguadili_n = fjöldi af N sem leiguaðilinn auglýsir.
-- Fyllist í útgáfu cc224-v8; v7 stendur sem afturköllun. Beitt með psycopg2 (lock_timeout 10s / statement_timeout 120s).
alter table semantic.nybygging_verkefni add column if not exists n_tviaugl_nu integer not null default 0;
alter table semantic.nybygging_verkefni add column if not exists leiguadili text;
alter table semantic.nybygging_verkefni add column if not exists leiguadili_n integer;
alter table semantic.nybygging_verkefni add constraint nybygging_verkefni_tviaugl_chk check (
  n_tviaugl_nu >= 0 and n_tviaugl_nu <= n_leiga
  and (leiguadili is null) = (leiguadili_n is null)
  and (leiguadili_n is null or (leiguadili_n >= 1 and 2 * leiguadili_n >= n_tviaugl_nu and leiguadili_n <= n_tviaugl_nu)));
notify pgrst, 'reload schema';
