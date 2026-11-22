-- cc355 rollback: skilyrðið eins og það var fyrir cc355 (pg_get_constraintdef 22.11.2026).
-- ATH: fellur ef einhver gata/postnr-áskrift ber þá 'af_solu'; fjarlægið gildið fyrst:
--   update public.voktun_askrift set atburdir = array_remove(atburdir,'af_solu') where tegund in ('gata','postnr') and 'af_solu' = any(atburdir) and cardinality(atburdir) > 1;
--   (áskrift með 'af_solu' eingöngu þarf ákvörðun: eyða eða setja ['ny'])
alter table public.voktun_askrift drop constraint voktun_atburdir_chk;
alter table public.voktun_askrift add constraint voktun_atburdir_chk check (
     ((tegund = 'eign'::text) and (atburdir <@ array['a_solu'::text, 'verd'::text, 'selst'::text, 'af_solu'::text]))
  or ((tegund = any (array['gata'::text, 'postnr'::text])) and (atburdir <@ array['ny'::text, 'laekkun'::text, 'sala'::text]))
  or ((tegund = 'leit'::text) and (atburdir <@ array['ny'::text]))
  or ((tegund = any (array['eignin_min'::text, 'frettabref'::text, 'manadarskyrsla'::text])) and (atburdir <@ array['utgafa'::text])));
