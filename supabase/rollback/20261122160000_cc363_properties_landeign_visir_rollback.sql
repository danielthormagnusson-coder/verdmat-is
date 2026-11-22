-- cc363 rollback: fjarlægir vísinn á public.properties(landeign_nr).
-- Skrifað Á UNDAN migration (WP). BEGIN/COMMIT eru ekki hér: beitingarskriftan stýrir færslunni (lock_timeout 5s).
-- Engin gögn og engin réttindi breytast: talning íbúða á lóð (reiknivél á /eign) verður aftur raðskönnun, sem skilar
-- sömu tölu, aðeins hægar. DROP INDEX tekur ACCESS EXCLUSIVE á töfluna í augnablik (lock_timeout 5s ver www).
DROP INDEX IF EXISTS public.idx_properties_landeign_nr;
