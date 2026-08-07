# AGUST_ENDURTHJALFUN — FLIPP-AUDIT cc104 (2026-08-06)

**Lota:** cc104 — flippið sjálft, mannað (eigandi + arkitekt við borðið, HALT á
hverju þrepi). **Heimild:** `docs/GO_BREF_FLIPP_REGLA_R_CC98_20260806.md` +
`docs/ROLLBACK_RUNBOOK_CC78.md` §2/§10.3/§10.4.
**Skjalið er append-only framkvæmdarbókun** — hvert þrep bókast hér með mældum
tölum eftir framkvæmd.

---

## Þrep 0 — kvittanir eiganda bókaðar í GO-bréfið (06.08, fyrir R1)

- §3 level-myndin: **KVITTAÐ 06.08.2026** (eigandi við borðið).
- §4 notendaupplifun: **VAL = (b)** — ein lína á `/adferdafraedi` m/dagsetningu.
- Flipp-sér-GO (skref 5) stendur ÓKVITTAÐ þar til við þrep 3.
- GO-bréfið 163→165 línur (additíft). Frávik bókað: GO-bréf og runbók reyndust
  ótrökkuð í git — fara inn með flipp-committinu (explicit paths).

## Þrep 1 — R1-frystingin (runbók §1/R1) — **ALLT GRÆNT 2026-08-06T10:14Z**

Framkvæmd: `cc104_r1_freeze.py` (scratchpad) · logg `D:\cc104_r1_freeze.log` ·
psycopg2 á pooler 6543 · frystingin keyrð í **EINNI REPEATABLE READ READ WRITE
txn** (`SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ WRITE` fyrsta
statement) svo lifandi talning, CTAS-afritið og frosna talningin mælast öll á
sama snapshot-augnabliki. Vörður felldi yfirskrift: taflan mátti ekki vera til
fyrir (staðfest to_regclass=NULL áður).

| # krafa | mælt |
|---|---|
| (1) frystitafla + RLS+REVOKE í sömu aðgerð | `public.predictions_2026_08_pre_cc78` — CTAS + `ENABLE ROW LEVEL SECURITY` + `REVOKE ALL FROM anon, authenticated` í sömu txn, COMMIT eitt. Eftir á MÆLT (ekki treyst á REVOKE-eintakið, cc52-reglan): `relrowsecurity=true`, `role_table_grants` fyrir anon/authenticated = **ENGIN** |
| (2) rowcount frosið == lifandi, sami tímastimpill | TXN A snapshot `2026-08-06T10:14:32.872607Z`: lifandi **167.503** = frosið **167.503** (in-txn, sama snapshot). Endurmælt TXN B snapshot `10:14:33.859950Z`: **167.503 / 167.503** |
| (3) engin NULL + model_version einsleitt | NULL í mean/lo80/hi80/lo95/hi95/confidence_grade/fastnum/model_version = **0/0/0/0/0/0/0/0** (af 167.503). model_version = **`iter4r_20260716` á öllum 167.503** — calibration_version tvískipt skv. runbókar-KRÖFU: `…_conformal_serving_v1` 153.901 + `…_conformal_v1+segcal_fb` 13.602 (summa 167.503) |
| (4) checksum bókað | md5 yfir allar raðir (md5(row::text), ORDER BY fastnum,h): frosið **`477b2fcab049606a3695663719d63642`** = lifandi **`477b2fcab049606a3695663719d63642`** |
| (5) kohort-krossprófið | kohort-pkl sha256[:16] **`c0e548cfddc4b1ff`** staðfest fyrst. Úrtak n=100 (seed 20260803, runbók §1d), 100 distinct fastnum, 100 merged raðir: **max\|Δ\| = 0,0 á öllum FIMM dálkum** (mean, lo80, hi80, lo95, hi95) |
| (6) spannar ALLT lifandi safnið | CTAS án WHERE · rowcount jafnt á sama snapshoti · anti-join báðar áttir **0/0** · checksum frosið == lifandi · fastnum einkvæmt 167.503/167.503 |

**R1 = GRÆNT. HALT — þrep 2 (staging) bíður go.**

## Þrep 2a — 0b: R2 + R4–R9 — **ALLT GRÆNT 2026-08-06T10:36Z**

**R2** (`cc104_r2_freeze.py` · logg `D:\cc104_r2_freeze.log`): `public.feature_attributions_2026_08_pre_cc78` fædd m/RLS+REVOKE í einni REPEATABLE READ txn. Rowcount sama snapshot: lifandi **1.675.030** == frosið **1.675.030** (KRAFA runbókar). Munaðarleysingjar gegn R1-frystingunni: **0**. Anti-join báðar áttir (fastnum-stig): **0/0**. NULL í fastnum/feature_name/rank/shap_log_contribution: **0/0/0/0**. Checksum frosið == lifandi: **`e9cc8411cc30bf813f5a65bd3ca562ed`**. RLS mælt virkt, anon/authenticated réttindi engin.

| # | mælt | dómur |
|---|---|---|
| R4 | `pipeline_config` orðrétt: `model_version=iter4r_20260716` · `model_pred_anchor_ym=2026-08` · `sales_history_anchor_ym=2026-09` (3 lyklar) | **PASS** |
| R5 | `iter4r_20260716_manifest.json` `data_sha256_16=aa2e191e750fd513` · mtime 2026-07-16 óbreytt | **PASS** |
| R6 | `training_data_v2_pre_cc78.pkl` sha16 **`aa2e191e750fd513`** == manifest gamla líkansins · lifandi `training_data_v2.pkl` (D2) sha16 **`32f9a1242b212d11`** == GO-bréf §1 | **PASS** |
| R7 | frumrit 49.248.213 b / mtime 2026-07-06 22:49 (KRAFA) · **afrit `properties_v2_pre_cc78.pkl` BÚIÐ TIL í þessari lotu** · sha16 frumrit == afrit `f7c101f5fa9f5b0b` | **PASS** |
| R8 | `classify_property.py.pre_cc78_…` md5 `35c1cad66538eec64ab9d8f3a49825f2` (KRAFA) · `build_training_data.py.pre_cc98_…` sha16 `757cbd2c22450e4b` (≠ lifandi R-variant `0419231e2c152875`, rétt) · `rebuild_training_data.py.pre_cc98_…` sha16 `0677222bdf3877f1` == lifandi (óbreytt skrá, rétt) | **PASS** |
| R9 | kohort sha16 `c0e548cfddc4b1ff` (KRAFA) · **mælt í næturafritsmanifesti `2026-08-06T03-00`** (`current/D_root/cc78_frozen_cohort_v1.pkl`) | **PASS** |

## Þrep 2b — 0c: UNIQUE-index-tékk MV-lista (§7) — **ALLT GRÆNT**

| MV | index | unique | indisvalid | dálkar |
|---|---|---|---|---|
| `v_model_vs_sold_by_hood` | `uq_mv_model_vs_sold_by_hood` | ✓ | ✓ | (matsvaedi_numer) |
| `v_hood_heat` | `uq_mv_hood_heat` | ✓ | ✓ | (matsvaedi_numer) |
| `v_street_directory` | `uq_mv_street_directory` | ✓ | ✓ | (street, sveitarfelag) |
| `v_street_activity` | `uq_mv_street_activity` | ✓ | ✓ | (street, sveitarfelag, sale_year) |
| `v_sveitarfelag_lookup` | `uq_mv_sveitarfelag_lookup` | ✓ | ✓ | (sveitarfelag) |
| `v_summerhouse_market` | `uq_mv_summerhouse_market` | ✓ | ✓ | (sveitarfelag, sale_year) |

REFRESH CONCURRENTLY er þar með gerlegt á öllum sex — engin þögul CONCURRENTLY-fall-hætta.

## Þrep 2c — STAGING — **skilin sex GRÆN 2026-08-06T11:50Z**

**Skorunin** (`rebuild_predictions_iter4.py`, breytt skv. runbók §10.4.2 — breytingin
committast með flipp-committinu í precompute-repoi): kandídat-boosterar (156 features),
hms-lags-innspýting sha-hliðuð `16d78e39d57cfcad` (0 raðir án hms-línu), R-flokkun
alheims m/`classify_property_r` (scope_policy='preserve'; cc_source: notkun 133.299 /
fallback 70.386 / **R_gerd 28.063** / exclude_preserved 1.005 / sertaxonomi 134 = 232.887),
`--anchor-ym 2026-09` (== pkl-akkeri, cpi-stuðull 1,013006), serving-lag 3.3 ósamhverft.
Universe 175.929 → D3-hlið −8.426 → **167.503**. Logg `D:\cc104_universe_rebuild.log`.

**Villa fundin og lagfærð AF hliðunum sjálfum:** fyrsta útgáfa lét sellulausar non-D
raðir falla á segcal; kohort-krossprófið felldi hana (13 'global'-raðir báru max|Δ| upp
í 21,4 M kr). Cascade lagfærður í seg_reg→seg→**GLOBAL fyrir non-D** (speglar 3.3-matsvélina;
1.834 raðir: ATTIC 1.474 / UNAPPROVED 216 / SENIOR 89 / STANDARD 55); öll D á segcal
(cc51-fordæmið). Eftir lagfæringu allt grænt.

| # | skil | mælt |
|---|---|---|
| (1) | rowcount + universe | staging **167.503** == lifandi **167.503** == R1-talan · anti-join báðar áttir **0/0** — sama þýði, engin síun |
| (2) | kohort-endurgerð | allar **1.186/1.186** raðir: pred_nom **max\|Δ\| = 0,0000 kr** · bil (lo80/hi80/lo95/hi95) max\|Δ\| **< 0,50 kr** (ytri kr-rúnnun á akkeris-skala, by construction) · segment == kohort cc_R frávik **0** |
| (3) | dreifing mean staging/lifandi | ALLT n=167.503: p10 0,8933 / **med 0,9614** / p90 1,0734 (−3,9 % med — innan GO-bréfs ~2–5 % niður). APT_* med 0,9359 (−6,4 %); sérbýli med 1,0234 — **samsetningaráhrif**: kyrr sérbýli med 1,0030 (n=28.928) en fluttar R_gerd-eignir med **1,0497** (n=27.036 — heil hús sem voru verðlögð sem íbúðir HÆKKA, það er lagfæringin sjálf). SUMMERHOUSE med 0,9964 (nær ósnert) |
| (4) | bilbreiddir rel80 | ALLT med 0,303→0,236 (lifandi cc51-leið-A bilin voru breiðari en 3.3-kerfið á íbúðum: APT_FLOOR 0,284→0,226) · breikkun þar sem óvissan er mest: SFH med 0,419→**0,552**, SEMI 0,412→0,514, ROW p90 0,419→0,666 · **Country-sérbýli med rel80 = 0,552 (n=27.222)** == GO-bréfs „halinn í 55 %+" |
| (5) | calibration + NULL | serving_v1 **155.609** (= öll non-D: seg_reg 150.222 + seg 3.553 + global 1.834) · +segcal_fb **11.894** (= öll D) · NULL í lykil-dálkum **0** · bil-röðunarbrot 1.284, öll á segcal-leið — **lifandi ber 1.447 slík** (fyrirliggjandi quantile-crossing, ekki regression, batnar heldur) |
| (6) | ásarnir tveir | A/B/C/D: 515/111.236/43.858/11.894 → **84.893/40.939/29.777/11.894** m/nýjum þröskuldum (sjá að neðan) · flokkur deterministic úr bilunum: frávik **0 af 167.503** · þrep T1–T5 ÓSNERT: 70.113/82.249/3.209/8.525/3.407, ruleset `tiers_v1_K3_F5_N8_2026-07-03` — ásarnir aðskildir sem fyrr |

**Flokkaþröskuldar endurleiddir (cc49 §5.2, krafa GO-bréfs §6 skref 10) — TILLAGA TIL
KVITTUNAR VIÐ BORÐIÐ:** A < **0,240** · B < **0,443** (gömlu 0,20/0,36). Aðferð speglar
upprunalegu leiðsluna: skurðir í raunverulega TÓMUM bilum strjálu sellu-breiddanna
(69 og 210 raðir inni í bilunum; gömlu-merkingar-nálægu skurðirnir 0,222/0,365 skera
gegnum byggt band 38 þús. raða og skilja A/B ekki að: MAPE 6,85/7,11). MAPE-einhalli
á holdout30 (D2-raðir): **A 6,71 % (n=575) < B 9,84 % (n=166) < C 14,00 % (n=106)**.
A þýðir nú ±12 % (var ±10 %); til samanburðar er lifandi A-flokkur 515 raðir (0,3 %)
síðan cc51 — endurleiðslan er leiðréttingin á því, ekki ný hliðarverkun.
Logg `D:\cc104_grade_thresholds.log` · `D:\cc104_staging_load.log` · `D:\cc104_staging_gates.log`.

**HALT — þrep 3 (transaction-flippið) bíður sér-GO við borðið (þriðja línan í
KVITTANA-töflu GO-bréfsins). Æfingarstig 2/3 á skrifleiðinni standa ókeyrð og þurfa
sitt eigið GO skv. runbók §5/§10.3 áður en þrep 3 er heimilað.**

## Þrep 2d — kvittanir borðsins + ÆFINGARSTIG 3 *(06.08, eftir staging-skil)*

**KVITTAÐ VIÐ BORÐIÐ 06.08.2026:**
1. **Flokkaþröskuldar A < 0,240 / B < 0,443: SAMÞYKKTIR.** Viðbótarkrafa á þrep 6
   (raunprófun): leita „±10"/„10%" í verdmat-ai (adferdafraedi + allir notendafletir);
   sé A-merking skjalfest sem ±10 % uppfærist hún í ±12 % í sömu deploy og
   /adferdafraedi-línan (§4b), annars bókast að hún er hvergi skjalfest.
2. **GO á æfingarstig 3** — skil að neðan. Þrep 3 fær go AÐEINS eftir grænt stig 3,
   gefið sérstaklega við borðið.

### ÆFINGARSTIG 3 — þvingað ROLLBACK gegn rauntöflunum — **ALLT GRÆNT 2026-08-06T12:11Z**

Framkvæmd (`cc104_stage3_rehearsal.py` · logg `D:\cc104_stage3_rehearsal.log`): full
rollback-röð runbókar §3 þrep 2–7 í EINNI txn á pooler 6543 — `SET TRANSACTION READ
WRITE` → timeout 300s/60s → `session_replication_role='replica'` → TRUNCATE+INSERT
predictions ← R1 → TRUNCATE+INSERT feature_attributions ← R2 → **UPDATE properties ←
R3 (óæfða þrepið 5)** → pipeline_config-UPSERT → in-txn recheck → **ÞVINGAÐ ROLLBACK**.
Skriftan inniheldur ENGA commit-leið (skilyrði runbókar §5).

| mæling | gildi |
|---|---|
| INSERT predictions ← R1 | **167.503** raðir |
| INSERT feature_attributions ← R2 | **1.675.030** raðir |
| UPDATE properties ← R3, snertar raðir | **0** (KRAFA 0 fyrir flipp) |
| in-txn recheck §4 (öll átta gildi) | **167.503 / 167.503 / 1.675.030 / 0 / 232.887 / 33.614 / 13.924 / 0 == rollback-dálkur §4 nákvæmlega — PASS** |
| **endurheimtar-sönnun in-txn** | checksum predictions == R1 (`477b2fcab049606a…`) ✔ · checksum FA == R2 (`e9cc8411cc30bf81…`) ✔ |
| lifandi eftir æfingu == fyrir | predictions ✔ · feature_attributions ✔ · properties-5-dálkar (`416c84fed94d50c7…`) ✔ · pipeline_config 3 lyklar óbreyttir ✔ |

Óæfða þrepið 5 er þar með ÆFT gegn rauntöflunni með réttum lásum. Athugasemd f/þrep 3:
flippið bætir NÝJUM lykli `calibration_version` í pipeline_config — rollback-SQL þreps 3
skal einnig EYÐA honum (runbók §3 þrep 6 telur aðeins tvo lykla; bókað hér svo það
gleymist ekki).

## Þrep 3 — FLIPPIÐ SJÁLFT — **COMMIT 2026-08-06T12:24:26Z, ALLT GRÆNT**

**Sér-GO við borðið kvittað í GO-bréfstöfluna** ([x] GO 06.08.2026, þriðja línan).
**Undirbúningur fyrir txn:** (a) rollback-SQL á disk FYRIR flipp:
`D:\cc104_flip_rollback.sql` — m/þriðja-lykils-eyðingunni; runbók leiðrétt í sömu lotu
(append §10.5). (b) Flokkunar-staging `public.properties_class_cc78_staging` (232.887,
RLS+REVOKE, PK fastnum; `cc104_props_class_staging.log`): fastnum-mengi == properties
1:1; cc_source nákvæmlega skv. staging-skilum (notkun 133.299 / fallback 70.386 /
R_gerd 28.063 / exclude_preserved 1.005 / sertaxonomi 134); unit_family-reglan:
segment_family(nýr kóði) NEMA EXCLUDE heldur gamla gildinu (sögulegt NULL/'exclude'-
tvíbýli á 42.439/14.519 EXCLUDE-röðum er UTAN umfangs); segment-samkvæmni predictions-
staging == ný flokkun frávik 0 af 167.503. **Vænt mælt fyrirfram: n_frav = 58.765**
(runbókar-≈58.500/58.561 var mat) og **n_apt_std = 57** (runbókar-≈206 var mat —
mælda talan er í samræmi við hms-lindarskýrsluna: 57 APT_STANDARD án dvalar-einingar).

**Transactionin** (`cc104_flip_txn.py` · logg `D:\cc104_flip_txn.log`): EIN txn á pooler
6543 — `SET TRANSACTION READ WRITE` fyrst → 300s/60s → replica-role (æfða leiðin
óbreytt) → UPDATE predictions ← staging **167.503** → TRUNCATE+INSERT
feature_attributions **1.675.030** → pipeline_config 1/1/1 (model_version →
`iter4r_20260805_reglaR_strukt`, anchor → `2026-09`, calibration_version NÝR →
`…_conformal_serving_v1`) → UPDATE properties ← class-staging **58.765** →
**in-txn sannprófun 15/15 PASS** (n_pred/n_mv/n_fa/n_orph/n_props/n_apt_std 57/
n_summer 13.924/is_residential 162.005/n_frav 58.765/class-staging-jöfnuður 0/
calibration 155.609+11.894/NULL 0/segment==canonical 0/pipeline_config 4 lyklar) →
**COMMIT 2026-08-06T12:24:26,04Z**.

**Eftir COMMIT, mælt strax af lifandi (snapshot 12:24:26,67Z):** allar sömu tölur
staðfestar — n_pred 167.503 (öll á nýja model_version), n_fa 1.675.030, n_apt_std 57,
n_summer 13.924, n_frav 58.765, serving_v1 155.609, segment-mismatch 0. Canonical-
dreifing lifandi == flokkunar-staging öll 14 gildi (APT_FLOOR 96.381 · EXCLUDE 56.958 ·
SFH_DETACHED 39.320 · ROW_HOUSE 16.094 · SUMMERHOUSE 13.924 · SEMI 4.335 · o.s.frv.).
A/B/C/D lifandi: **84.893 / 40.939 / 29.777 / 11.894** (samþykktu þröskuldarnir
0,240/0,443). **MV-arnir sex eru nú STÖÐNAÐIR þar til þrep 5 keyrist — vitað
millibilsástand, næsta skref.**

## Þrep 5 — MV-REFRESH SEX (runbók §7-listinn og -röðin) — **6/6 GRÆNAR 2026-08-06T12:30:28Z**

*(Framkvæmd cc101 skv. GO eiganda „þrep 4+5 saman — MV FYRST“.)* Skrifta
`cc101_mv_refresh.py` (scratchpad) · logg `D:\cc101_mv_refresh.log` · psycopg2 á
pooler 6543 í **autocommit** (CONCURRENTLY má ekki standa í txn-blokk) · prelude
skv. §7: read_only=off, work_mem 64MB, statement_timeout 600s · fail-fast: fyrsta
villa hefði stöðvað röðina (engin keyrð blint áfram — engin villa kom).

| MV (runbókar-röð) | raðir fyrir → eftir | tími |
|---|---|---|
| `v_model_vs_sold_by_hood` | 164 → 164 | 3,9 s |
| `v_hood_heat` | 179 → 179 | 3,6 s |
| `v_street_directory` | 24.253 → 24.253 | 3,2 s |
| `v_street_activity` | 40.002 → 40.002 | 3,9 s |
| `v_sveitarfelag_lookup` | 64 → 64 | 1,1 s |
| `v_summerhouse_market` | 591 → 591 | 1,5 s |

Raðafjöldi óbreyttur er væntur (hópunarlyklarnir standa; innihaldið skiptist um).
Efnisleg sannprófun eftir refresh: `v_model_vs_sold_by_hood` ber nýju spárnar —
Σn_pairs 8.535, miðgildi median_ratio yfir traust svæði 1,0044; lifandi predictions
öll á `iter4r_20260805_reglaR_strukt`, A/B/C/D 84.893/40.939/29.777/11.894 ==
flipp-tölurnar. **Glugginn predictions-nýjar/MV-gamlar er LOKAÐUR.**

## Þrep 4 — TRAINER Í D2-ÁSTAND + KÓÐAFASTAR + COMMITT — *(cc101, sama GO)*

**precompute-repo (`D:\verdmat-is\precompute`):**
- `retrain_sales_model.py` fært í D2-ástand skv. runbók §10.4.1: `n_ibudareininga`
  + `flm_hlutfall` ÚR EXCLUDE (−2), `EXPECTED_N_FEATURES = 154 → 156`,
  Int32→float64 vörpun á nullable-Int featurum fyrir LightGBM. Rauðsannað gegn
  lifandi `training_data_v2.pkl` (sha `32f9a1242b212d11`): **feats == 156**, báðar
  nýju featururnar inni; py_compile hreint. (Fyrir breytingu var skráin byte-jöfn
  154-afritinu `.cc98_R154_20260805T093342Z` — staðfest með diff.)
- `rebuild_predictions_iter4.py`: (a) cc104-skorunarbreytingarnar (hms-lags-
  innspýting + R-flokkun + cascade-lagfæringin úr þrepi 2c) sem áttu að committast
  með flippinu; (b) **flokkaþröskuldarnir endurleiddu þar sem þeir búa:**
  `GRADE_A_THR 0,20 → 0,240` · `GRADE_B_THR 0,36 → 0,443` (kvittun borðsins þrep 2d).

**app-repo (`D:\verdmat-is\app`):** GO-bréfið m/öllum kvittunum ([x]×3), runbókin
m/§10.5 calibration_version-leiðréttingunni og þetta flipp-audit-skjal — allt áður
ótrakkað (frávik bókað í þrepi 0), fer inn með explicit paths.

*(Committ-sha beggja repoa bókast í HALT-skilum cc101 — skjalið sjálft committast
í sömu aðgerð og getur ekki borið eigið sha.)*

## Þrep 6 — PROD-RAUNPRÓFUN + ±10%-LEITIN + §4b-LÍNAN — **LOKIÐ 06.08 (cc101)**

A-hluti: 5/5 prófeignir prod == lifandi DB nákvæmlega (2013952 R_gerd→ROW_HOUSE
138,0M/A/T1 · 2000296 155,0M/B · 2000309 121,5M/A · Country-sérbýli ×2 rel80
0,552/C, bil óbrotin); líkans-kafli /markadur ber nýju stöðuna (72/76 innan ±5%);
console hreint. ±10%-leitin: A-merking HVERGI skjalfest sem prósenta á notendafleti
— fjarveran bókuð, engin ±12%-uppfærsla. §4b-línan (val (b), dagsett 06.08.2026)
LIVE á /adferdafraedi — verdmat-ai commit `f153163`.

## Þrep 7 — VAKTIR Á NÝJA GRUNNINN (3.2-spec) — **LOKIÐ 07.08 (cc101)**

Heimildir af diski: 3.2-specið (SKREF31_32 §4, bindandi §4.3) + §7-grunnur
3.3-auditsins (SKREF33). Forsenda leyst fyrst: `<version>_holdout_rows.csv`
vantaði fyrir nýja artifactið — `precompute/holdout_eval.py` keyrð (M1 ✓ M2 ✓;
M3-flokkahreyfingin er endurleiddu þröskuldarnir, kvittað mál); 950 raðir.

`scripts/model_quality_eval.py` færð á nýja grunninn:
- BASELINE → §7-grunnur 3.3 (8,23 / 81,58 / 96,69) + BASELINE_FRESH
  (11,59 / 83,48 / 95,58) m/flöggum á báðum skópum; „nýtt upphaf“ bókað.
- FREEZE_ANCHOR_YM 2026-08 → **2026-09** (flipp-akkerið); PRED_VALUATION_YM
  2026-07 óbreytt (predicted_at mælt í DB).
- **bias-per-hólf línan inn (spec §4.3):** r_scope a/b/c1 gegnum flokkunar-ættina
  (properties_class_cc78_staging × properties_canonical_pre_cc78, LEFT JOIN í
  _OOS_SELECT); |bias(b)|>4,0 pp = hávær lína; upphafslínan í extra; töflu-hvarf
  = hávært gat, aldrei þögul núll.
- **Veiku blettirnir FJÓRIR** (GO-bréf §5) sem fastar vöktunarlínur án n-gólfs
  m/upphafsgildum í extra: sfh_rvk_core · r_gerd_rvk_core · undir_40m · apt_attic.
- **Vaktareign 2013952** í weekly-skil (ásett/verðbreytingar/virk-horfin;
  við þinglýsingu kaupverð vs mat 138,0 m/fráviki); villa í vaktareign fellir
  aldrei mælinguna.

**Fyrsta prófkeyrsla (dryrun, lifandi grunnur, 07.08):** AÐALTALA holdout30
n=949: **MAPE 8,23 (Δ±0,0 frá grunnlínu) · cov80 82,8 (+1,24) · cov95 96,1**
— dómsreglan FÆDDIST GRÆN. Hliðartala fresh_edge n=42: cov80 78,6 (−4,91,
flagg á litlu n — tripwire, ekki HALT). Hólfin: (a) n=113 +1,04 · (b) n=535
**+2,33 innan ±4,0** · (c1) n=298 +1,64. Veiku blettirnir: 89,5/19 · 78,1/32 ·
67,2/58 · 81,8/11. Vaktareignin: ásett 174,0 M virk (mbl, síðast séð 30.07),
engin verðbreyting, óselt, lifandi mat 138,03 M. Paired/E2 sjálfhafnar hávært
(adapter iter4_final_v1 ≠ lifandi — engin Haiku-keyrsla). Scheduler
`verdmat-weekly-model-quality` bendir þegar á vélina — ENGIN breyting.
