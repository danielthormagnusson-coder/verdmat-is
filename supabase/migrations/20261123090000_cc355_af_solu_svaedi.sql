-- cc355: „Fer af sölu" (af_solu) leyfður í áskriftum á götu og póstnúmer (eign hafði hann frá cc320).
-- Aðeins CHECK á public.voktun_askrift breytist: engin ný tafla, engin réttindi, engin RLS-breyting (taflan heldur RLS + service_role).
-- public.voktun_atburdur.tegund leyfir 'af_solu' nú þegar (voktun_atburdur_tegund_check), svo þar þarf ekkert.
-- Núverandi raðir (3) standast nýja skilyrðið (mælt 22.11.2026, s30_mig_forprof.py). lock_timeout 5s í beitingarskrift.
alter table public.voktun_askrift drop constraint voktun_atburdir_chk;
alter table public.voktun_askrift add constraint voktun_atburdir_chk check (
     ((tegund = 'eign') and (atburdir <@ array['a_solu','verd','selst','af_solu']::text[]))
  or ((tegund = any (array['gata','postnr']::text[])) and (atburdir <@ array['ny','laekkun','sala','af_solu']::text[]))
  or ((tegund = 'leit') and (atburdir <@ array['ny']::text[]))
  or ((tegund = any (array['eignin_min','frettabref','manadarskyrsla']::text[])) and (atburdir <@ array['utgafa']::text[])));
