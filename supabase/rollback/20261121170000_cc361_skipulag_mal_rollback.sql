-- cc361 rollback: fjarlægir public.skipulag_saga(bigint) og public.skipulag_mal.
-- Skrifað Á UNDAN migration (WP). BEGIN/COMMIT eru ekki hér: beitingarskriftan stýrir færslunni.
-- Gögnin í töflunni eru endurgeranleg úr vikulegum innlestri (scripts/skipulag_innlestur.py); ekkert annað les þau.
DROP FUNCTION IF EXISTS public.skipulag_saga(bigint);
DROP TABLE IF EXISTS public.skipulag_mal;
NOTIFY pgrst, 'reload schema';
