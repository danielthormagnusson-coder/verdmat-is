-- Rollback cc331 B5: fjarlægir dálkana þrjá og skorðuna. Skriftan verður fyrst að vera bökkuð (git revert + ff),
-- annars fellur næsta næturkeyrsla á INSERT í dálka sem ekki eru til.
BEGIN;
SET TRANSACTION READ WRITE;
ALTER TABLE semantic.nybygging_einingar DROP CONSTRAINT IF EXISTS nybygging_einingar_augl_stofur_chk;
ALTER TABLE semantic.nybygging_einingar
  DROP COLUMN IF EXISTS augl_stofa_lykill,
  DROP COLUMN IF EXISTS augl_stofa,
  DROP COLUMN IF EXISTS augl_stofur;
COMMIT;
