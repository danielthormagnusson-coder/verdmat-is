-- cc82 — FASTEIGNAMAT ÚR HMS-SAFNINU MEÐ ÁRGERÐARMERKI (nýir dálkar, ekki uppfærsla á staðnum).
--
-- ÁKVÖRÐUN EIGANDA 03.08: nýr dálkur + árgerðarmerki. Rökin: fasteignamat er
-- BIRT TALA sem notandi getur borið saman við aðrar síður, og án árgerðar getum
-- við hvorki útskýrt mun né mælt hann síðar; uppfærsla á staðnum eyðir sögunni
-- og gerir næstu árgerðaskipti ómælanleg.
--
-- ÁRGERÐIN ER SÖNNUÐ INNANHÚSS, EKKI ÁLYKTUÐ AF ÞRIÐJA AÐILA (skref 0,
-- scripts/hms_mat_argerd_skref0.py). Kaupskrá ber SÖGULEGT mat á söludegi og
-- fasteignamat tekur gildi 31.12 fyrir árið á eftir. Af 177.036 samtengdum sölum:
--   · sölur þinglýstar 2026: 5.493/5.852 = 93,9% hitta `fasteignamat`,
--     0,0% hitta `fasteignamat_nuverandi`; miðgildi hlutfalls = 1,0000
--   · sölur þinglýstar 2025: 10.615/11.612 = 91,4% hitta `fasteignamat_nuverandi`,
--     0,1% hitta `fasteignamat`; miðgildi hlutfalls = 1,0000
-- => HMS-reiturinn `fasteignamat` er árgerð 2026. Það er mælt, ekki lesið af vef.
--
-- MÆLINGIN SEM KALLAÐI Á ÞETTA (scripts/hms_mat_vintage_probe.py, nefnari 232.767):
--   `properties.fasteignamat` ber eldri árgerð (2025) á 40.429 röðum = 17,4%
--   — þar af Reykjavík 19.341/41.789 = 46,3%. Miðgildismunur +9,8%.
--
-- EINING: ÞÚSUND KRÓNUR, sama og `properties.fasteignamat` og kaupskrá.
-- (138.100 = 138.100.000 kr.) Eining er hluti af merkingunni, ekki aukaatriði.
--
-- GRUNNREGLA 8 ÓHÖGGUÐ: fasteignamat er hvergi líkanbreyta — staðfest á fjórum
-- óháðum heimildum (train_iter4a.py setur FASTEIGNAMAT í EXCLUDE, DECISIONS
-- 2026-04-21; lifandi SHAP ber 25 breytur og enga; leigulíkanið 14 og enga;
-- CLAUDE.md bókar hið sama). Þetta er BIRTINGARLAG.
--
-- ADDITIVE: `properties.fasteignamat` er EKKI snert. Ekkert yfirborð les nýju
-- dálkana enn — þeir eru þögul viðbót þar til birtingarákvörðun er tekin.

alter table public.properties
  add column if not exists fasteignamat_hms        numeric,
  add column if not exists fasteignamat_hms_argerd smallint,
  add column if not exists fasteignamat_hms_sott   date;

comment on column public.properties.fasteignamat_hms is
  'Fasteignamat úr HMS-safni (hms.is/api/fasteignaskra/fasteign, reitur `fasteignamat`). ÞÚSUND KRÓNUR. Árgerðin stendur í fasteignamat_hms_argerd — talan er merkingarlaus án hennar. cc82.';
comment on column public.properties.fasteignamat_hms_argerd is
  'Árgerð fasteignamat_hms (t.d. 2026 = matið sem gildir almanaksárið 2026). Sönnuð með tímaprófi á kaupskrá, ekki lesin af þriðja aðila — sjá scripts/hms_mat_argerd_skref0.py. cc82.';
comment on column public.properties.fasteignamat_hms_sott is
  'Hvenær röðin var sótt úr HMS (fetched_at í hms_archive_staging.db). Uppruna-dagsetning, ekki gildistökudagur matsins. cc82.';
