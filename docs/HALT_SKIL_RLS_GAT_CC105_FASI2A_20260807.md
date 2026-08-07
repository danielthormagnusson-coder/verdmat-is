# HALT-SKIL cc105 FASI 2a — RLS: snapshot-þrennan + spatial_ref_sys

Applýjað 2026-08-07T08:24:14Z. Framhald af FASA 1
(`HALT_SKIL_RLS_GAT_CC105_FASI1_20260806.md`).

## 0. Forsendur GO staðfestar fyrir apply

| Forsenda | Sönnun |
|---|---|
| cc101 þrep 8 lent | `f5b45e6` 2026-08-07 00:43 „cc101 flipp threp 8: follnu 31 utdregnar (31/31) og verdmetnar (30/31)"; auk þess `90f4b96` (cc108-bókun) og `290b77b` („threp 8 lenti medan bokunin var skrifud") |
| HALT-skjal FASA 1 heilt | 196 línur, 11.281 bæti, síðasta lína heil setning: `— cc105 FASI 1, read-only, HALT.` |

## 1. Migration

- **Version (schema_migrations): `20260807082414`**, nafn `cc105_2a_rls_snapshot_toflur`.
  Staðfest efst í `supabase_migrations.schema_migrations`.
- Skrá í git-tré: `supabase/migrations/20260807082414_cc105_2a_rls_snapshot_toflur.sql`
- Rollback **skrifaður FYRIR apply**:
  `supabase/rollback/20260807082414_cc105_2a_rls_snapshot_toflur_rollback.sql`
  (nafn og innri version samræmd við skráða version eftir á).
- Sex statement, hvert sér (cc86-venjan): 3 × `ENABLE ROW LEVEL SECURITY`
  + 3 × `REVOKE ALL ... FROM anon, authenticated`.

## 2. Mæld réttindi EFTIR apply (pg_class + has_table_privilege)

| Tafla | RLS | stefnur | relacl | anon SELECT | auth SELECT |
|---|---|---|---|---|---|
| `scraper.listing_extractions_pre_cc94b` | **true** | 0 | `{postgres=arwdDxtm/postgres}` | false | false |
| `scraper.listing_extractions_pre_cc94b2` | **true** | 0 | `{postgres=arwdDxtm/postgres}` | false | false |
| `scraper.listing_valuations_pre_cc94b2` | **true** | 0 | `{postgres=arwdDxtm/postgres}` | false | false |
| `public.spatial_ref_sys` | false (ÓBREYTT) | 0 | `{supabase_admin=arwdDxtm/supabase_admin, postgres=arwdDxtm/supabase_admin, anon=rxtm/…, authenticated=rxtm/…, service_role=arwdDxtm/…, =r/supabase_admin}` | true | true |

`relforcerowsecurity=false` á öllum þremur ⇒ eigandinn (postgres — migrations og
ops-leiðin) les áfram. Sannreynt með lifandi talningu eftir apply: **163 / 2 / 4
raðir**, óbreytt frá fyrir apply. Ops-keðjan er því ósnortin.

Advisors eftir apply: töflurnar þrjár færðust úr `rls_disabled_in_public`-menginu
yfir í `rls_enabled_no_policy` (INFO) — nákvæmlega sama ástand og hinar ~37
default-deny töflurnar. `rls_disabled_in_public` telur nú **eina** töflu:
`spatial_ref_sys`.

## 3. spatial_ref_sys — HVORUG LEIÐIN FÆR, OG ÞAÐ ER RÉTT NIÐURSTAÐA

Þetta er efnislega frávikið frá verkbeiðninni og krefst kvittunar.

**Aðalleiðin reynd og féll (raunreynt, ekki ályktað):**
```
alter table public.spatial_ref_sys enable row level security;
→ ERROR 42501: must be owner of table spatial_ref_sys
```
Taflan er í eigu `supabase_admin`; migrations keyra sem `postgres`.
Mælt: `pg_has_role(postgres,'supabase_admin','member') = false`.

**Varaleiðin (REVOKE SELECT) var EKKI keyrð — þrjár óháðar ástæður:**

1. **Forsenda verkbeiðnarinnar stenst ekki.** Hún sagði „postgres er grantor,
   heimilt". Það var **villa í FASA 1-skjalinu mínu**: ég las
   `information_schema.role_table_grants` án þess að velja `grantor`-dálkinn og
   ályktaði grantor = postgres. Bein mæling á `pg_class.relacl` sýnir að grantor
   er **supabase_admin** í ÖLLUM færslum. Leiðrétt hér með.
2. **REVOKE væri þögul núll-aðgerð sem skilar `success`.** Mælt:
   `has_table_privilege(postgres,'public.spatial_ref_sys','SELECT WITH GRANT
   OPTION') = false`. Postgres getur ekki afturkallað það sem supabase_admin
   veitti — PostgreSQL gefur WARNING, ekki villu. **Þetta er nákvæmlega gildran
   sem cc52 féll í** (bókuð í CLAUDE.md: „verify with `aclexplode`, never with
   the migration's exit status"). Að keyra hana hefði framleitt falska
   „tókst"-línu í þessi skil.
3. **Jafnvel fullkomin REVOKE lokaði engu.** ACL ber `=r/supabase_admin`, þ.e.
   **PUBLIC hefur SELECT** (mælt: 1 PUBLIC-grant í `aclexplode`). REVOKE á
   anon+authenticated skilur PUBLIC-leiðina eftir opna fyrir öllum hlutverkum.
   Að loka henni krefst líka supabase_admin.

**Auk þess mælir fyrri bókun gegn aðgerðinni:** cc72 lét Supabase support
framkvæma REVOKE á rit-sögnunum sem supabase_admin og bókaði SELECT sem
ÆTLAÐAN („SELECT still works, as intended"), og flaggið sem
known-accepted (CLAUDE.md). cc52-migrationin varar sérstaklega við að RLS þarna
felldi geo-fyrirspurnir fyrir anon.

**Staða:** flaggið stendur óbreytt known-accepted. Raunveruleg lokun krefst
support-beiðni til Supabase (sama leið og cc72). Það er ákvörðun eiganda, ekki
þessarar lotu. **Póst-hnappurinn „Resolve issue" var ALDREI snertur.**

**Gildran sem FASI 1 varaði við reyndist hlutlaus hvort eð er:** `poi_naesta` er
`LANGUAGE sql` með hreinni haversine-reikniformúlu — engin PostGIS-týpa, ekkert
`ST_`-kall, snertir ekki `spatial_ref_sys`. Mælt til viðbótar: **ENGIN** útsett
view/MV kallar `ST_`-fall, og einu geometry/geography-dálkarnir í notendaskemum
eru `scraper.listings_canonical.geog` (anon-lokað) og tvær PostGIS-innri gerðir.
Anon-PostGIS-flöturinn er því í reynd enginn.

## 4. Raunprófun undir anon — 21/21 óbreytt, 0 brot

Sama skrift keyrð fyrir og eftir apply (UTF-8-afkóðun og `\uXXXX`-merki, því
ANSI-afkóðun gaf falskt „0 merki" í fyrstu atrennu).

**A. PostgREST sem anon — 12/12 óbreytt `200`:** `spatial_ref_sys` (15b),
`rpc/poi_naesta` (1.117b, POI-gildran), `rpc/search_properties_grouped`
(2.754b), `properties`, `v_properties`, `v_current_predictions`,
`v_eign_myndir`, `v_fjoleining_fastnum`, `repeat_sale_index_main_pooled`,
`latest_regime_per_cell`, `semantic.v_hood_heat`, `valuation_tiers_rent`.

**B. Á að vera lokað — 4/4 óbreytt `401`:** snapshot-töflurnar þrjár (voru þegar
401 FYRIR apply — sem staðfestir flokkun FASA 1: frávikið var **latent**, ekki
opin leið) og `scraper.v_leit_listings` (`42501 permission denied for view`).

**C. Lifandi síður sem anon — 5/5 `200`, bæti UPP Á BÆTI eins fyrir og eftir:**

| Slóð | Fyrir | Eftir | Merki |
|---|---|---|---|
| `/markadur` | 78.056 b | 78.056 b | visitala |
| `/eign/2000044` | 41.622 b | 41.622 b | **POI(Nærþjónusta), loftlína**, visitala |
| `/leiguverd` | 20.798 b | 20.798 b | — |
| `/leit` | 136.566 b | 136.566 b | — |
| `/leiga/328773` (cc107) | 44.955 b | 44.955 b | — |

POI-kortið birtist sannanlega á /eign bæði fyrir og eftir. Ekkert rollback
þurfti; rollback-skráin stendur ónotuð á diski.

## 5. Umfang sem var VÍSVITANDI ekki snert

FASI 2b (definer-view, semantic-MV-grants, `st_estimatedextent`,
`search_path` á þrjú föll, HIBP, þrenging á `authenticated` í scraper-viewum)
bíður stefnufundar um definer-mynstrið. Ekkert af því var hreyft.

## 6. Ógert / í hendi eiganda

1. **Kvittun á §3** — að sleppa REVOKE-varaleiðinni sé rétt lesning.
2. Ef loka á flagginu í raun: support-beiðni til Supabase (supabase_admin þarf
   að fjarlægja `=r` PUBLIC-grantið og/eða kveikja RLS) — sama leið og cc72.
3. Git: migration + rollback + þetta skjal + FASA 1-skjalið eru **ócommittuð**.
4. Leiðrétta þarf FASA 1-skjalið §4(a) þar sem stendur að postgres sé grantor.

— cc105 FASI 2a, applýjað og mælt, HALT.
