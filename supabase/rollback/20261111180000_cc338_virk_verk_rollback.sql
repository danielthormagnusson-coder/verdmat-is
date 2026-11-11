-- cc338 ROLLBACK: fjarlægir registur_utflutningur.virk_verk(integer). Ekkert annað háð fallinu í grunni.
-- Eftir rollback fer afrit hluthafa aftur á fyrra hlið (eða bilar á kalli) — láta hluthafa vita.
begin;
set local lock_timeout = '5s';
DROP FUNCTION IF EXISTS registur_utflutningur.virk_verk(integer);
commit;
