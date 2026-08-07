# HALT-SKIL cc105 FASI 1 — RLS-GAT (read-only mæling, 06.08.2026)

Tilefni: Supabase security advisory-póstur (issues as of 03.08) —
„Table publicly accessible — rls_disabled_in_public", verkefni
szzjsvmvxfrhyexblzvq, taflan ónefnd í pósti. FASI 1 var read-only:
engin breyting gerð á DB, kóða né stillingum.

## 1. Tæmandi sópun: RLS-staða allra taflna

74 töflur mældar í öllum notenda-skemum (public, scraper, semantic).
**4 töflur með `rowsecurity=false`** — allt hitt með RLS á:

| Tafla | Raðir (talið) | Grants anon/authenticated (mælt úr ACL) | Flokkun |
|---|---|---|---|
| `public.spatial_ref_sys` | 8.500 | anon+authenticated: SELECT,REFERENCES,TRIGGER (grantor postgres) | **(a) RAUNOPIN** — les-aðgengileg um API-lykilinn |
| `scraper.listing_extractions_pre_cc94b` | 163 | ENGIN (aðeins postgres) | (b) linter-frávik — ekki aðgengileg |
| `scraper.listing_extractions_pre_cc94b2` | 2 | ENGIN (aðeins postgres) | (b) linter-frávik — ekki aðgengileg |
| `scraper.listing_valuations_pre_cc94b2` | 4 | ENGIN (aðeins postgres) | (b) linter-frávik — ekki aðgengileg |

Nefnarar: (a) = RLS af OG anon-grant til staðar; (b) = RLS af en engin
grants → PostgREST hafnar (þótt scraper-skemað SÉ útsett, sjá §3.1).
Engin skrif-grants á neinni þeirra fyrir anon/authenticated.

> ⚠️ **VIÐAUKI (FASI 2a, 07.08) — LEIÐRÉTTING Á TÖFLUNNI HÉR AÐ OFAN.**
> Reiturinn „(grantor postgres)" á `spatial_ref_sys`-línunni er RANGUR og
> stendur óbreyttur hér að ofan sem heimild. Hann byggði á
> `information_schema.role_table_grants` án `grantor`-dálks. Bein mæling á
> `pg_class.relacl` (07.08) sýnir grantor = **`supabase_admin`** í öllum
> færslum, og auk þess `=r/supabase_admin`, þ.e. **SELECT til PUBLIC** — leið
> sem birtist alls ekki í role_table_grants. Rétt lesning á reitnum er því:
> anon+authenticated hafa `rxtm` veitt AF supabase_admin, og PUBLIC hefur
> SELECT að auki. Sjá `HALT_SKIL_RLS_GAT_CC105_FASI2A_20260807.md` §3 og
> nýja regluna í DECISIONS (07.08).

**Stofndagar:**
- `spatial_ref_sys`: fæddist með postgis-extensioninni í public
  (advisor-flaggið `extension_in_public` staðfestir staðsetninguna) —
  þ.e. frá upphafi verkefnisins. Þekkt frá cc52 („stendur EFTIR"),
  kanarí í keðjum frá cc55, vöktunarundanþága lokuð í cc72.
  **Advisory-pósturinn 03.08 er þessi tafla og engin önnur** —
  `rls_disabled_in_public` flaggar hana eina.
- `pre_cc94b*`-töflurnar þrjár: viðgerðar-snapshots cc94-lotunnar
  06.08.2026 (components-spillingin). Urðu til í viðgerð, ekki um
  fæðingarregluna (RLS+REVOKE í sömu migration og CREATE) — cc94 er
  lotan sem á frávikið; reglunni sjálfri er ekki um að kenna.

## 2. Anon-notkunarmælingin (sker úr um FASI 2-umfang)

Live-appið er `D:\verdmat-is\verdmat-ai` (5b6e1d4 = cc101). Fjórir
klientar í lib/:

| Klient | Lykill/hlutverk | Hvar keyrir |
|---|---|---|
| `lib/supabase.js` | **anon** (module-export) | BÆÐI browser (components) og server (lib-queries, API-rútur) |
| `lib/supabase-browser.js` | **anon** (@supabase/ssr) | Browser — auth + innskráðar aðgerðir |
| `lib/supabase-server.js` | **anon** + notenda-session úr kökum | Server (rútur/page.tsx) |
| `lib/supabase-admin.js` | **service_role** | Server eingöngu |

**Anon-flöturinn er BURÐARVIRKI síðunnar** — mælt per skrá:

- `lib/eign-queries.js` (anon): `properties`, `property_images`,
  `sales_history`, `comps_index_v2`, `comps_t5_basis`,
  `last_listing_text`, `valuation_tiers`, `v_properties`,
  `v_current_predictions`, `v_eign_myndir`, `v_fjoleining_fastnum`,
  `repeat_sale_index` — /eign les þetta allt sem anon.
- `lib/dashboard-queries.js` (anon): `latest_regime_per_cell`,
  `repeat_sale_index_by_segment`, `repeat_sale_index_main_pooled`,
  `ats_dashboard_monthly_heat`, `model_tracking_history`.
- `lib/markadur-*.js` (anon): semantic-MV-arnar + `llm_aggregates_quarterly`
  + `repeat_sale_index_main_pooled`.
- `app/api/search/route.js`: hrá REST-köll með **ANON-lyklinum** á
  `rpc/search_properties_grouped` + `properties` — öll /leit keyrir sem anon.
- Browser-components (anon beint úr vafra): `EignSearch`,
  `SearchAutocomplete`, `BackProjectionWidget` (`v_properties`),
  `MyndaViewer` (`v_eign_myndir`), `Eigindi` (`pro_users`,
  `property_attributes` + rpc `skra_eigind*` sem authenticated),
  `Greining`/`GreiningSamanburdur` (rpc `greining_eignar`, authenticated).
- Skriftöflur ábendinga/notkunar (`abending`, `agent_notkun`,
  `flokkari_notkun`): INSERT fer um **service_role** (admin-klient í
  rútunum, staðfest í kóða) — RLS-á/policy-laust = default deny á anon
  er þar meðvitað mynstur.
- scraper-viewin (`v_leit_listings`, `v_eign_virk_auglysing`): lesin
  EINGÖNGU um service_role (mælt í `markadur-puls.js` og
  `eign-queries.js`) — samræmist því að þau bera enga anon-grant.

**Niðurstaða: REVOKE anon á view/MV-flötinn er EKKI hættulaust.**
Anon-lesning er hönnunin sjálf; hún fer nær öll um SECURITY
DEFINER-view og granted töflur. Sérhver breyting á þeim fleti krefst
kortlagningar per hlut (2b), ekki fjöldaaðgerðar.

## 3. Aukafundir advisors-úttektar (full skrá)

### 3.1 SECURITY DEFINER-view — 8 stk (ERROR-stig)

Öll í eigu postgres; definer-mynstrið þýðir að þau lesa undirtöflurnar
framhjá RLS. Undirtöflurnar eru RLS-á og policy-lausar (default deny)
— **view-in eru því vísvitandi opnunarleiðin**, ekki gleymska:

| View | Les úr | anon | authenticated | Anon-notkun mæld í síðu |
|---|---|---|---|---|
| `public.v_current_predictions` | predictions | r | r | JÁ (/eign, backproj, leidretting) |
| `public.v_eign_myndir` | property_images, daudir_myndahyslar, scraper.listings | r | r | JÁ (/eign, MyndaViewer) |
| `public.v_fjoleining_fastnum` | scraper.listings, listing_lifecycle_events | r | r | JÁ (/eign, leidretting) |
| `public.latest_regime_per_cell` | ats_dashboard_monthly_heat | r | r | JÁ (dashboard) |
| `public.regime_per_cell_monthly` | ats_dashboard_monthly_heat, ats_lookup_by_quarter | r | r | ekki fundin í live-app (aðeins grant) |
| `public.repeat_sale_index_by_segment` | repeat_sale_index | r | r | JÁ (dashboard) |
| `public.repeat_sale_index_main_pooled` | repeat_sale_index | r | r | JÁ (dashboard, markadur, puls) |
| `scraper.v_leit_listings` | 7 töflur (þ.m.t. predictions, properties) | **—** | r | nei — service_role eingöngu |
| `scraper.v_eign_virk_auglysing` | 3 scraper-töflur | **—** | r | nei — service_role eingöngu |

(scraper-skemað ER PostgREST-útsett — appið notar `schema("scraper")` —
en anon-grant-leysið heldur anon úti; authenticated=r á scraper-viewunum
tveimur er víðara en notkunin, sem er service_role eingöngu.)

### 3.2 Materialized views í API — semantic (WARN)

10 MV-ar með anon+authenticated=r (allar `_sales_base`-afleiður:
hood_heat, matsvaedi ×2, street_prices, newbuild, summerhouse,
price_distribution, model_vs_sold, sveitarfelag ×2) — **viljandi**:
/markadur les þær anon-megin (cc101: „grants reyndust þegar til").
MV-RLS er ekki til í Postgres; grant-stýring er eina vörnin, og
innihaldið er samlagðar markaðstölur sem síðan birtir hvort eð er.
**Ósamræmi fundið:** 3 MV-ar til viðbótar bera ENGA grants
(`v_postnr_prices_yearly`, `v_street_activity`, `v_street_directory`)
— grant-sagan er handvirk, ekki regluleg.

### 3.3 SECURITY DEFINER-föll

- `skra_eigind` / `skra_eigind_stadfest`: VEL VARIN — krefjast
  `auth.uid()` (42501 annars), stadfest krefst að auki
  `pro_users.role='fasteignasali'`, attr_key-hvítlisti (26 lyklar),
  jsonb-tegundartékk, `search_path` fest, EXECUTE aðeins
  authenticated+service_role (anon EKKI). Engin aðgerð nauðsynleg.
- `st_estimatedextent` (3 yfirhleðslur, PostGIS C-fall): anon+
  authenticated mega kalla um /rest/v1/rpc. Skilar extent-áætlun úr
  tölfræði — efnislega meinlaust; síðan notar það hvergi (grep: 0).
  Má REVOKE í 2b áhrifalaust.

### 3.4 Önnur flögg

- `function_search_path_mutable` (WARN): `search_properties_grouped`
  hefur `statement_timeout=10s` en EKKI fest search_path (anon-kallanlegt
  um /leit — ætti að festa í 2b); `scraper.eigindi_ur_extraction` og
  `scraper.extraction_er_gilt` sömuleiðis ófest (innri föll).
- `rls_enabled_no_policy` (INFO, ~37 töflur): default-deny mynstrið
  okkar — RÉTT ástand, engin aðgerð (opnunin fer um definer-view/RPC).
- `auth_leaked_password_protection` (WARN): HIBP-vörnin AF. Auth ER í
  notkun — 5 notendur í auth.users (prófnotendur cc17 + hlutverk) —
  svo þetta er EKKI N/A. Lágt vægi (enginn opinn signup-flötur mældur),
  kveikt í dashboard (Auth → Passwords), ekki SQL-breyting.

## 4. Áhættumat

**(a) Póst-flaggið — `spatial_ref_sys`: LÁGMARK.**
Les-aðgangur eingöngu að opinberri EPSG-hnitakerfisuppflettitöflu sem
fylgir PostGIS. Enginn viðskiptagagna- eða notendagagnaleki, engin
skrif-leið. Hefur staðið frá upphafi (advisory-pósturinn er dagsettur
03.08 en ástandið er upprunalegt). Tillaga að meðferð í 2a:
`ALTER TABLE ... ENABLE ROW LEVEL SECURITY` — **fyrirvari:** taflan er
extension-eign og ALTER kann að stranda á eignarhaldi (þekkt
Supabase-staða; líklega ástæða þess að cc52 skildi hana eftir). Ef svo:
`REVOKE ALL FROM anon, authenticated` (grantor er postgres skv. ACL svo
REVOKE er heimilt). **Hörð raunprófunarkrafa:** `poi_naesta` er
SECURITY **INVOKER** og anon-kallanlegt PostGIS-fall — ef innri
geography-aðgerðir þess fletta upp í spatial_ref_sys brotnar POI-lag
/eign undir anon við REVOKE. Prófa verður poi_naesta + /eign + /leit
+ /markadur + /leiguverd EFTIR apply, og rollback-SQL tilbúið FYRIR.

> ⚠️ **VIÐAUKI (FASI 2a, 07.08) — LEIÐRÉTTING Á MÁLSGREININNI HÉR AÐ OFAN.**
> Setningin „(grantor er postgres skv. ACL svo REVOKE er heimilt)" stendur
> óbreytt hér að ofan sem heimild, en hún er RÖNG og var aldrei framkvæmd.
> Mælt 07.08 á `pg_class.relacl`: grantor er `supabase_admin`, ekki postgres.
> Postgres hefur hvorki eignarhald né GRANT OPTION (bæði mæld `false`), svo
> **hvorug leiðin er fær**: `ENABLE ROW LEVEL SECURITY` fellur á raunreyndu
> `42501 must be owner of table spatial_ref_sys`, og REVOKE væri þögul
> núll-aðgerð sem skilar `success` (cc52-gildran) — auk þess sem `=r` til
> PUBLIC gerir REVOKE á anon/authenticated gagnslausa. Varaleiðin var því
> EKKI keyrð; flaggið stendur known-accepted. Sjá
> `HALT_SKIL_RLS_GAT_CC105_FASI2A_20260807.md` §3.
>
> **POI-gildran sem hér er lýst reyndist hlutlaus:** `poi_naesta` er
> `LANGUAGE sql` með hreinni haversine-formúlu — engin PostGIS-týpa, ekkert
> `ST_`-kall. Mælt til viðbótar: ekkert útsett view/MV kallar `ST_`-fall.
> Raunprófuð samt fyrir og eftir (200, 1.117 b, óbreytt).

**(b) Linter-frávikin — pre_cc94b-töflurnar þrjár: HREINLÆTI.**
169 raðir samtals, engin grants, ekki aðgengilegar um API. Núll
raunáhætta í dag; frávikið er að þær standa án RLS í útsettu skema og
myndu opnast ef einhver granta-r seinna. ENABLE RLS (engin policy) er
áhrifalaus hreinlætislagfæring. (DROP er freistandi — þær eru
viðgerðar-snapshots cc94 — en það er sjálfstæð ákvörðun um
sönnunargagnavörslu, EKKI hluti af þessari lagfæringu.)

**(c) Aukafundirnir: ENGIN fjöldaaðgerð réttlætanleg.**
Anon-mælingin (§2) sýnir að definer-view-in og MV-grantarnir eru
burðarvirki síðunnar. Raunmat per hlut: allt sem anon les er efni sem
síðan birtir hvort eð er opinberlega. Raunverulegu snyrtiverkin eru
smá og afmörkuð: (i) 3 grant-lausu semantic-MV-arnar — samræma stefnu
(granta eða bóka að þær séu innri), (ii) `st_estimatedextent` REVOKE,
(iii) search_path fest á föllin þrjú, (iv) HIBP á, (v) víðari
authenticated-grant á scraper-viewunum tveimur en notkun krefst —
þrengja má í service_role eingöngu. Ekkert af þessu er aðkallandi.

## 5. FASI 2 — tillaga í tveimur skömmtum

**2a — póst-flaggið + hreinlætið (lítið, öruggt):**
Ein migration m/rollback-SQL skrifað FYRIR apply + schema_migrations
m/rollback-fylki:
1. ENABLE RLS á `pre_cc94b*`-töflurnar þrjár (+ REVOKE-belti þótt engin
   grants séu — fæðingarreglusamræmi).
2. spatial_ref_sys: ENABLE RLS ef eignarhald leyfir, annars REVOKE-leiðin.
3. Mælt EFTIR um pg_class/ACL; advisors endurkeyrðir (flaggið á að hverfa).
4. Raunprófun: /markadur, /eign (þ.m.t. POI-kortið!), /leiguverd, /leit
   — allt svarar; poi_naesta prófað sérstaklega undir anon.

**2b — view/MV/falla-flöturinn (eftir ákvörðun eiganda):**
Stefnuval á definer-mynstrinu (tillaga: samþykkja og bóka sem meðvitaða
opnunarleið), svo smáverkin (i)–(v) úr §4c, hvert m/raunprófunarkröfu á
/markadur, /eign, /leiguverd, /leit.

**Skilyrði beggja: cc104 þrep 6 (raunprófun flippsins) GRÆNT fyrst —
ein breyting í kerfinu í einu — og sér-go frá eiganda á hvorn skammt.**

— cc105 FASI 1, read-only, HALT.
