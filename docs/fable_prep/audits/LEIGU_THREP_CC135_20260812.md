# cc135 — valuation_tiers_rent á reglu R (HALT fyrir flipp)

**Dagsetning:** 2026-08-12 · **Staða:** **FLIPPAÐ LIVE 09:54 (GO), postverify PASS.**
Frysting + forsendumæling + build + staging + parity + kohort + skammtasvörun + raunprófun LOKIÐ.
**Tilefni:** cc131 FASI A §2 — `valuation_tiers_rent` 57.417/158.314 (36,27%) bera
rangan `canonical_code`.

Skriftur: `precompute/cc135_freeze.py` · `cc135_forsendur.py` · `build_rent_tiers.py`
(breytt) · `cc135_parity.py` · `cc135_flip.py` (óframkvæmd).
Rollback: `app/scripts/valuation_tiers_rent_rollback_cc135.sql`.

---

## 1. FRYSTING (LOKIÐ)

`valuation_tiers_rent_pre_cc135` — CREATE TABLE AS + `ENABLE ROW LEVEL SECURITY` +
`REVOKE ALL FROM anon, authenticated` í SÖMU txn. Hliðið „neita að yfirskrifa
snapshot sem er til" beit ekki (snapshot var ekki til).

| | live | snapshot |
|---|---|---|
| count(\*) | 158.314 | 158.314 |
| sum(threp) | 376.627 | 376.627 |
| sum(n_local) | 46.342.605 | 46.342.605 |
| sum(pi80_pct) | 6.504.296,91 | 6.504.296,91 |
| threp=1 / threp=5 | 35.110 / 15.405 | 35.110 / 15.405 |
| distinct canonical_code / segment | 12 / 26 | 12 / 26 |

`relacl = {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres}`, `rls=true`
— anon/authenticated ekki í ACL (relacl er eina grantor-mælingin, cc105).
Rollback-SQL skrifað á disk **fyrir** framkvæmd.

---

## 2. FORSENDUMÆLINGIN — TILEFNISBRÉFIÐ VAR TVÖFALT ÓRÉTT

Bréfið gekk út frá að „endurkeyrsla + staging-flipp læknar án frekari hönnunar".
Mælingin fellir það á tveimur ásum og finnur þriðja sem er ÓLÆKNANDI í þessari lotu.

### 2A. Lindin var ENDURNEFND — byggjarinn gat ekki keyrt

`load_universe()` las `public.predictions_rent_staging`. cc30-flippið
(`20260719_cc30_leigumat_flip.sql`) endurnefndi þá töflu í `predictions_rent`.

```
to_regclass(public.predictions_rent_staging    ) = None      <- LINDIN ER EKKI TIL
to_regclass(public.valuation_tiers_rent_staging) = None
VÍSIR predictions_rent_staging_pkey     tilheyrir NÚ predictions_rent
VÍSIR valuation_tiers_rent_staging_pkey tilheyrir NÚ valuation_tiers_rent
```

Endurnefning flytur EKKI vísanöfn. Tvennt af því:

1. Byggjarinn hefði fallið á `relation "predictions_rent_staging" does not exist`.
2. `CREATE TABLE ... fastnum bigint PRIMARY KEY` á staging hefði fallið á
   `relation "valuation_tiers_rent_staging_pkey" already exists` — nafnið er upptekið
   af LIFANDI töflunni. Þvingunin er nú NEFND (`valuation_tiers_rent_staging_pk`).

Gamla hliðið „LIVE predictions_rent verður að vera 0" var cc30-arfur (taflan var tóm
þar til flippið) og hefði nú alltaf fallið. Það er farið; í staðinn kemur hart hlið á
`--pred-table` (tafla til **og** raðir > 0) með sjálfgildi á lifandi töfluna.
Lifandi lind mæld: `predictions_rent`, n=158.314, `model_version=rent_v1_nan`,
`predicted_at=2026-05-01`, `calibration_version=rent_anchor_v2_herbergi_fm+conformal_v2_tegund_nan`.
Þetta er EINA leigu-spáin — hér er engin lifandi/frosin greining eins og cc131
`--pred`-vandinn; greiningin er endurnefnd/ekki-endurnefnd tafla.

### 2B. ÞÉTTLEIKA-ÁSINN var frosinn — naív endurkeyrsla GERIR ILLT VERRA

Ás 1 (aðal-ásinn: n samningar 2021-2023 í `postnr × canonical_code`) er talinn úr
`leiga_train.parquet` (29.06), sem ber `canonical_code` **PRE reglu R**. Universe-hliðin
kemur LIFANDI úr `properties` (03.08, cc78). Joinið lá milli tveggja merkingarkerfa.

* 7.167 af 21.099 samningum (33,97%) bera nú annað `canonical_code`
  (APT_STANDARD→APT_FLOOR 5.150 · APT_FLOOR→SFH_DETACHED 1.201 · APT_FLOOR→ROW_HOUSE 306 …)
* sellur: 441 (frosin merking) → 414 (lifandi). 72 sellur hverfa, 45 nýjar.
  n_local breytist á 327 af 486 sellum.

| hólfun | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|
| LIVE `valuation_tiers_rent` | 35.110 (22,18%) | 74.193 (46,86%) | 18.318 (11,57%) | 15.288 (9,66%) | 15.405 (9,73%) |
| S0 stöðnuð cc + frosinn þéttleiki | 35.110 | 74.193 | 18.318 | 15.288 | 15.405 |
| **S1 naív endurkeyrsla** (lifandi cc + frosinn þéttleiki) | 29.610 | 65.368 | 19.812 | 19.527 | **23.997 (15,16%)** |
| **S2 samræmd** (lifandi cc + lifandi merking) | 32.526 (20,55%) | 71.560 (45,20%) | 20.972 (13,25%) | 19.161 (12,10%) | **14.095 (8,90%)** |

**S0 endurgerir lifandi töfluna EXAKT** — 0 mismunur á þrepi, n_local, flokki og
t5_ástæðu á öllum 158.314 röðum. Mælitækið er því sannað gegn artefaktinu áður en það
er notað til að dæma um breytingu.

S1 hendir **8.592 eignum til viðbótar í T5** (`of_fair_samningar` 14.896 → 23.488).
Sú þynnka er EKKI TIL — hún er merkingar-mismunur milli hliða joinsins.
29.510 raðir skilja S1 og S2: það er kostnaður þess að láta þéttleikann frosinn.

Lækningin (`--dens-label live`, sjálfgildi) endurmerkir samningana úr lifandi
`properties` á fastnum ÁÐUR EN talið er. **Parquet-skráin sjálf er óbreytt** — hún er
þjálfunar-inntak leigulíkansins og bannið stendur.

### 2C. SEGMENT-ÁSINN — ólæknandi undir banninu, bókað

`predictions_rent.segment` er `cc|region[|tegund]`, reiknað 2026-05-01 á PRE-R
`properties`. Á **57.612 röðum (36,39%)** segir segment annan flokk en lifandi
`properties` (APT_STANDARD vs APT_FLOOR 30.179 · APT_FLOOR vs SFH_DETACHED 18.178 …).

Ás 2 (`fallback_lvl`, `n_conformal`) er eiginleiki þess segments. Bannið á
`predictions_rent` þýðir að hann **læknast ekki** við endurbyggingu. Eftir cc135 ber
taflan LIFANDI `canonical_code` og PRE-R `segment` á sömu röð — mótsögn á byggingarstigi
sem er sögð berum orðum hér frekar en falin. Aðeins endurskorun leigu-spárinnar lokar
henni (sér lota; `rent_v1_nan` var þjálfað pre-R, cc131 §2).

---

## 3. BUILD + STAGING + PARITY (PASS)

Build: `python build_rent_tiers.py --apply` (`--pred-table public.predictions_rent`,
`--dens-label live`). Niðurstaða = S2 upp á röð, óháð endurgerð í `cc135_forsendur.py`.

| hlið | mæling | dómur |
|---|---|---|
| universe (predictions_rent × properties) | 158.314 | — |
| staging / live / snapshot rowcount | 158.314 / 158.314 / 158.314 | PASS |
| orphans (staging án properties) | 0 | PASS |
| **staging ↔ properties canonical-mismunur** | **0** (var 57.417) | PASS |
| spá-raðir án þreps í staging | 0 | PASS |
| þrep utan 1..5 eða NULL | 0 | PASS |
| NULL-talningar | aðeins `t5_astaeda` (144.219 stg / 142.909 live — rétt: fyllt eingöngu á T5) | PASS |
| 500-raða sýni DB ↔ CSV, 11 dálkar | 0 mismunur | PASS |

Hliðin `canonical-mismunur=0` og `orphans=0` sitja líka INNAN skrif-txn byggjarans —
falli þau, rúllar hlaðningin til baka.

---

## 4a. KOHORT

| hólf | n | þrep víxlar | % |
|---|---|---|---|
| óbreytt (cc eins) | 100.897 | 12.665 | 12,55% |
| innan fjölskyldu (íbúð↔íbúð, sérb↔sérb) | 30.667 | 3.414 | 11,13% |
| fjölbýli↔sérbýli | 26.750 | 18.405 | **68,80%** |

Víxlin eru mest á fjölbýli↔sérbýli hólfinu — eins og vænta má: þar færist eignin milli
gerólíkra þéttleika-sella (Nýlendugata 41: n_local 1.417 → 20).

**Birt mat** (T5 kæfir leigumatið algerlega, `byggjaLeigumat`; kæfingarnar eru þrjár:
T5, fjöleiningar-smit cc27, engin spá):

* eignir sem **FÁ** birt mat (T5 → T1-T4, sýnilegar): **4.164**
* eignir sem **MISSA** birt mat (T1-T4 → T5, sýnilegar): **2.855**
* nettó T5: 15.405 → 14.095 (−1.310)
* þrepsvíxl á SÝNILEGUM eignum: **34.456**
* fjöleiningar-vörnin grípur aðeins 193 raðir (0,12%) og spá-NULL 0 — hún felur
  því hvorki víxlin né nettóáhrifin.

T5-ástæður: `of_fair_samningar` 14.896 → 13.586 · `engin_svaedisgogn` 195 → 195 ·
`eignaflokkur` 314 → 314.
**Flokkur (A-D) hreyfist ekki á neinni röð** — hann er conformal-breidd og spáin er
fryst; D-mengið (314) er óbreytt. B 48.189 / C 109.811 / D 314, A tómt (cc30-satt).

Úrtak úr víxl-hólfum:

| hólf | fastnum | heimilisfang | víxl | þrep | n_local |
|---|---|---|---|---|---|
| innan fjölsk. | 2066833 | Austurströnd 2, 170 | APT_STANDARD→APT_FLOOR | T3→T2 | 62→122 |
| innan fjölsk. | 2013762 | Álftamýri 8, 108 | APT_STANDARD→APT_BASEMENT | T1→T2 | 337→91 |
| fjölb↔sérb | 2009516 | Samtún 4, 105 | APT_FLOOR→SFH_DETACHED | T2→T3 | 1.112→54 |
| fjölb↔sérb | 2000309 | Nýlendugata 41, 101 | APT_FLOOR→ROW_HOUSE | T1→T3 | 1.417→20 |
| óbreytt | 2000189 | Mýrargata 24, 101 | SFH_DETACHED (eins) | T3→T2 | — |

---

## 4b. SKAMMTASVÖRUN — MERKIÐ ER EKKI TIL Í ÞEIRRI MYND, OG ÞAÐ ER NIÐURSTAÐA

**Leigan hefur ENGA comps-vél.** Engin `comps_*`-tafla er til fyrir leiguna (mælt:
`rent|leig`-töflur í public eru `predictions_rent*`, `feature_attributions_rent*`,
`valuation_tiers_rent`). cc131-mengunarmerkið (comp-akkeri / spá) er því **EKKI TIL**
fyrir leiguna og verður ekki mælt „fyrir og eftir" í þeirri mynd.

Nálgunin sem TIL ER: raun-akkeri sellunnar = miðgildi leiguverðs á m² í
`postnr × canonical_code` úr samningum 2021+ (n ≥ 10). Sama formúla tvisvar: sellan sem
stöðnuð merking valdi (fyrir) og sellan sem regla R velur (eftir). 132.605 mælanlegar raðir.

| hólf | n | fyrir | eftir | \|Δ\| |
|---|---|---|---|---|
| óbreytt | 83.157 | 0,8540 | 0,8533 | 0,07 p.p. |
| innan fjölskyldu | 29.889 | 0,7892 | 0,7864 | 0,29 p.p. |
| fjölbýli↔sérbýli | 19.559 | 1,3993 | 1,3980 | 0,13 p.p. |

**Stærsta hreyfing yfir öll hólf: 0,29 p.p.** Það er innistæðan — og hún er
HREYFINGARLEYSI, ekki lokun: endurbyggingin færir ÞREPIÐ, ekki leigutöluna. Spáin er
fryst og ber enn PRE-R segment á 36,39% raða. **Mengunin í TÖLUNNI stendur eftir cc135.**
Þetta er skipulagslegur munur frá cc131: þar var akkerið (`comp_wmedian_kr`) sjálft
endurreiknað, svo bilið gat lokast 2,9→0,6 p.p.; hér er akkerið ekki til og talan fryst.

**STIGIÐ á fjölbýli↔sérbýli hólfinu (+54,5 p.p. gegn óbreyttu) er ÓDÓMTÆKT** og má
ekki bókast sem mengunarmæling. Nefnara-próf á eignum með eigin samning 2021+:

| hólf | n | einflm p50 | samn.stærð p50 | einflm/stærð | spá / eigin leiga |
|---|---|---|---|---|---|
| fjölbýli↔sérbýli | 1.086 | 214,9 | 70,0 | **3,290** | 1,863 |
| innan fjölskyldu | 3.304 | 81,8 | 79,8 | 1,000 | 1,396 |
| óbreytt | 8.794 | 84,6 | 74,8 | 1,000 | 1,456 |

Leigusamningur á fastnum getur verið um HLUTA matseiningarinnar; á víxl-hólfinu er
matseiningin 3,3× samningsstærðin. Hlutfall á m² er þar nefnara-artefakt. Aðeins 15 af
26.750 þeirra raða eru gripnar af `v_fjoleining_fastnum` — **sjálfstæð ábending, ekki
löguð hér** (sjá §6).

---

## 5. FLIPP — FRAMKVÆMT 2026-08-12 09:54 (GO), POSTVERIFY PASS

```
09:54:01 forkröfur OK: staging 158.314 raðir, canonical-mismunur 0, snapshot til
09:54:02 INSERT: 158.314 raðir
09:54:04 postverify: n=158.314  threp={1: 32526, 2: 71560, 3: 20972, 4: 19161, 5: 14095}
09:54:04 postverify: canonical-mismunur=0  orphans=0  EXCEPT-diff=0
09:54:04 postverify: rls=True  policies=1  SELECT-grants=2
09:54:05 FLIPP COMMIT — postverify PASS á öllum hliðum
```

Öll níu hliðin stóðust á fyrstu atrennu; ekkert rollback. Snapshot
`valuation_tiers_rent_pre_cc135` STENDUR sem rollback-grunnur.

Aðferð: `python cc135_flip.py --go`.
`TRUNCATE + INSERT ... SELECT` í EINNI txn (EKKI rename: heldur töflu, þvingunum, RLS,
policy `public_read` og GRANT SELECT óbreyttum; TRUNCATE tekur ACCESS EXCLUSIVE svo
lesandi sér aldrei hálft sett). Postverify INNAN txn — rúllar til baka falli eitt hlið:
rowcount 158.314 · T1 32.526 / T2 71.560 / T3 20.972 / T4 19.161 / T5 14.095 ·
canonical-mismunur 0 · orphans 0 · `EXCEPT`-diff gegn staging 0 · rls=true ·
policies=1 · SELECT-grants=2. Forkröfuhlið: snapshot til, staging rétt talið,
canonical-mismunur 0. Þurr keyrsla: **forkröfur OK**.

Snapshot `valuation_tiers_rent_pre_cc135` STENDUR eftir flipp sem rollback-grunnur.

---

## 6. RAUNPRÓFUN Á NOTENDAFLETI (eftir flipp)

Dev-þjónn ræstur 09:58 (ferskt ferli → **cache var kalt**; fyrsta sókn er því fersk).
Öll tilvik úr fjölbýli↔sérbýli-hólfinu, báðar áttir sjást.

**`/leiga/[id]` — ferskt (`saekjaLeigumatEignar`, engin `unstable_cache`):**

| slóð | eign | víxl | þrep→ | birt |
|---|---|---|---|---|
| `/leiga/271060` | Einarsnes 6, 102 (2029356) | APT_STANDARD→ROW_HOUSE, **T2→T5** | Þrep 5 | **engin tala** + „Of fáir þinglýstir leigusamningar eru skráðir fyrir eignir af þessari gerð í þessu postnúmeri." |
| `/leiga/335276` | Keilufell 10, 111 (2051581) | APT_FLOOR→SFH_DETACHED, **T1→T2** | Þrep 2 | 402.110 kr./mán (331.092–488.361) |

**`/leiguverd/[fastnum]` — cachaður farmur:**

| slóð | eign | víxl | þrep→ | birt |
|---|---|---|---|---|
| `/leiguverd/2269703` | Kistuholt 2, 806 | APT_STANDARD→ROW_HOUSE, **T5→T3** | Þrep 3 | **262.740 kr./mán** (223.775–308.490) — **FÆR birt mat** |
| `/leiguverd/2029356` | Einarsnes 6, 102 | **T2→T5** | Þrep 5 | „Ekki er birt leigumat" — **MISSIR mat** |
| `/leiguverd/2051581` | Keilufell 10, 111 | **T1→T2** | Þrep 2 | 402.110 kr./mán |

Hausinn ber cc132-flokkunina rétt: „Raðhús · skráð sem íbúð · 136,2 m² … fastanr. 2269703".
Talan sjálf er óbreytt þar sem hún birtist (spáin fryst) — það sem hreyfist er þrepið
og hvort talan birtist yfirhöfuð.

**Console hreint:** aðeins React-DevTools-ábending, `[HMR] connected` og fyrirliggjandi
`GoTrueClient … Multiple GoTrueClient instances` (bókasafnsviðvörun supabase-js, ótengd
cc135). Engar villur, ekkert PGRST/42P01.

**Cache-glugginn:** `/leiguverd` les `saekjaEignCached` (`unstable_cache`,
`EIGN_CACHE_UTGAFA="cc93"`, TTL 600 s) — í PROD sýnir hún gamalt þrep í allt að 10 mín
eftir flipp og jafnar sig svo án deploys. Sá gluggi var EKKI mælanlegur hér: dev-ferlið
ræstist eftir flippið, svo cache-ið var kalt og fyrsta sókn þegar fersk.

### 6b. ENDURMÆLING EFTIR AÐ TTL RANN ÚT

Cache-færslurnar urðu til 09:58:40–09:59:35; TTL 600 s → rennur út 10:08:40–10:09:35.
Endurmælt **10:11:34**, þ.e. yfir gluggann:

| slóð | þrep | tölur | „Ekki er birt leigumat" |
|---|---|---|---|
| `/leiguverd/2269703` | Þrep 3 | 262.740 / 223.775 / 308.490 kr./mán | nei |
| `/leiguverd/2029356` | Þrep 5 | engar | **já** |
| `/leiguverd/2051581` | Þrep 2 | 402.110 / 331.092 / 488.361 kr./mán | nei |

Nákvæmlega sömu gildi og við kalda sókn — cachaða leiðin heldur nýju þrepunum yfir
TTL-veltuna og fellur ekki aftur í gamalt. **Það sem þetta sannar EKKI:** umskiptin
stöðnuð→fersk sáust aldrei, því cache-ið var kalt frá byrjun. Í PROD (heitt cache við
flipp) stendur gamla þrepið í allt að 600 s og jafnar sig svo án deploys — það er
eiginleiki TTL-sins, ekki mælt hér.

### FYRIRLIGGJANDI GALLI FUNDINN Í PRÓFUN (ekki lagaður, ekki cc135-afturför)

`verdmat-ai/scripts/raudprof-leigumat-t5.mjs` sækir **`/eign/[fastnum]`** — en cc33
hreinsaði leiguna af þeirri slóð og cc107 flutti hana á `/leiguverd`. Prófið skilar því
`1 FÉLL — 4 tilvik`: jákvæða viðmiðið (Mýrargata 37, 2000263, T1) fellur NAUÐSYNLEGA því
`/eign/2000263` ber ekkert leigumatskort, á meðan T5-tilvikin þrjú standast ÓMERKILEGA
af sömu ástæðu. Staðfest að þetta er próf-fúi en ekki afturför: sama fastnum á
`/leiguverd/2000263` ber Þrep 1 og 6 leigutölur, og þrepið er óbreytt T1→T1 yfir flippið.
Þetta er nákvæmlega bilunin sem haus prófsins varar sjálfur við („síða sem sækir aldrei
leigumat stenst T5-hlutann fullkomlega og er samt biluð"). Slóðin þarf að færast á
`/leiguverd` — sér ákvörðun.

---

## 7. EFTIR (ekki gert í cc135)

* **Endurskorun leigu-spárinnar** (segment-ásinn, §2C) — sér lota, bannað hér.
* **einflm vs samningsstærð 3,3× á víxl-hólfinu** (§4b) og að
  `v_fjoleining_fastnum` grípur aðeins 15 af 26.750 — mælt, ekki lagað.
* Snapshot-eyðing (`*_pre_cc131`, `*_pre_cc135`) bíður staðfestingar borðsins.

---

## ⚠ VIÐAUKI A (cc138, 2026-08-12) — ÚTGÁFUSTÝRINGIN VAR RANGT BÓKUÐ

**Viðbætandi. Ekkert að ofan er endurritað.**

### A.1 Rangfærslan

cc135 bókaði precompute-hliðina sem **„utan git"**. Það er rangt.
`D:\verdmat-is\precompute` **er** git-repo (`origin` =
`github.com/danielthormagnusson-coder/verdmat-is-precompute`), það var í fullri
sync við `origin/main` á `05dc55f` (06.08) þegar cc135 keyrði, og er það enn þegar
cc137 mældi það.

**Afleiðing rangfærslunnar er mæld, ekki ályktuð:** breytingin á `build_rent_tiers.py`
(**+103/−16**) stóð sem óbókað `M` í vinnutrénu frá flippi kl. **09:54 12.08** þangað
til cc138 bókaði hana — í tíu klukkustundir bar prod töflu sem enginn commit útskýrði.
Skriftirnar fjórar (`cc135_freeze.py`, `cc135_forsendur.py`, `cc135_parity.py`,
`cc135_flip.py`) stóðu á sama tíma **untracked**, þar á meðal `cc135_flip.py` sem
framkvæmdi flippið sjálft og `cc135_freeze.py` sem smíðaði rollback-grunninn.

Þetta er sama gerð og [[feedback_bokun_um_vidgerd_er_ekki_vidgerd]] varar við, með
öfugu formerki: hér lýsti bókunin ekki viðgerð sem ekki var gerð, heldur **afsakaði
óbókaða viðgerð með repo-ástandi sem var ekki til**. Rangfærslan var ekki fyrirvari —
hún felldi niður skref.

### A.2 Lagað

| | |
|---|---|
| precompute `05dc55f` → **`d5a3175`** | `build_rent_tiers.py` (+103/−16) + skriftirnar fjórar (746 nýjar línur) í rakta stöðu |
| precompute `d5a3175` → **`1bc568f`** | cc131-leifin sem lá í sama repoi: `build_comps_v2.py` (+8/−1), `load_comps_v2.py` (+7/−2) |
| app (þessi commit) | þetta skjal + `docs/fable_prep/prototypes/cc135/` (afrit skriftanna, sbr. `cc39/`) |

**0 skrár eyddar í hvorugu repoi.** Línurnar 16 sem hverfa úr `build_rent_tiers.py` eru
gamla hliðið („live `predictions_rent` verður að vera 0", cc30-arfur) og gamla
`load_local_density`, hvort tveggja **skipt út í sömu skrá** — ekki felld úr sögunni.

### A.3 Aukafrávik fundið við bókun (ekki endurritað hér að ofan)

**Hausinn og línu 8 ber ekki saman.** Hausinn segir *„FLIPPAÐ LIVE 09:54 (GO),
postverify PASS"*; línu 8 í sama haus segir `cc135_flip.py` **(óframkvæmd)**.
Flippið **var** keyrt — postverify 9/9 PASS, canonical-mismunur 57.417→0, taflan lifandi
á reglu R. Línu 8 er leif frá HALT-drögunum áður en GO barst; hausinn var uppfærður,
listinn ekki. Rétt lesning: `cc135_flip.py` **framkvæmd 09:54**.

### A.4 Ólokað eftir cc138 — sama gerð, önnur skrá

Bókunin lokar cc135- og cc131-breytingunum en **ekki öllum verkfærunum**. Enn untracked
og því óvarin á sama hátt:

* `precompute/cc131_freeze.py` — cc131-frystingin (systur-skrá `cc135_freeze.py`)
* `precompute/fetch_canon_support.py` — byggir `support/canon_*.parquet` sem
  `build_comps_v2.py` les
* `app/scripts/comps_v2_rollback_cc131.sql` og
  `app/scripts/valuation_tiers_rent_rollback_cc135.sql` — **báðar rollback-skrárnar**,
  þ.e. viðbragðið sjálft er óútgáfustýrt

Ekki lagað hér: cc138-bréfið afmarkaði bókunina við cc135/cc131-breytingarnar og
`Ekkert annað`. Mælt og lagt fyrir borðið.
