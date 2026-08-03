# cc82 FRAMKVÆMDALOTA — söluaðili í gegn + fasteignamats-árgerðin fullmæld

**Dags.** 03.08.2026 · **Umboð:** GO eiganda á TVENNT úr §5 í `FASTINN_SAMANBURDUR_CC82`
(liðir A1 og A2), ekkert annað. Hvorugt snertir líkan né þjálfun.
**Staða:** VERK 1 framkvæmt og sannreynt · VERK 2 mælt + hannað, **ENGIN framkvæmd** ·
**HALT fyrir push** (ekkert committað, ekkert pushað í hvorugu repói).

**Tvö repo, tvær breytingar:**
`D:\verdmat-is\app` (verdmat-is: pípur, skriftur, migrations) og
`D:\verdmat-is\verdmat-ai` (LIFANDI appið, verdmat.ai, HEAD `a640788`).

> ⚠ **Repo-leiðréttingin.** Fyrsta útgáfa fastinn-úttektarinnar mældi „hvað appið ber" í
> `D:\verdmat-is\app` — sem er EKKI lifandi appið. Það felldi §2.7 (þjónustustig) ranglega:
> nærþjónustu-flöturinn ER lifandi. Leiðrétt í úttektarskjalinu (§0, §1 lína 7, §2.7, §4, §5).

---

## VERK 1 — SÖLUAÐILI Í GEGN (framkvæmt)

### 1.1 Hvað var að

`parse_mbl.py` hefur ALLTAF geymt söluaðilann: `SALE_NESTED`/`RENT_NESTED` skila
`agency → agency_json` í `parsed_mbl_{sale,rent}`. Promote-lagið tók hann aldrei með, svo
Postgres — og þar með hvert einasta notendayfirborð — vissi ekki af honum.

| Lag | Fyrir | Eftir |
|---|---|---|
| `parsed_mbl_sale.agency_json` | 37.517 / 38.706 = **96,9%** | óbreytt (lindin var alltaf í lagi) |
| `parsed_mbl_rent.agency_json` | 3.150 / 3.165 = **99,5%** | óbreytt |
| `scraper.listings` söluaðila-dálkar | **engir** | 7 dálkar |
| `scraper.listings.agency_name` | **0 / 34.654 = 0,0%** | **33.592 / 34.654 = 96,9%** |
| `scraper.v_eign_virk_auglysing` | ber hann ekki | **11.590 / 12.551 = 92,3%** virkra auglýsinga |

**Nefnarinn er `source = 'mbl'`**, ekki allar 36.277 raðir töflunnar — 1.623 raðir koma úr
öðrum lindum og gátu aldrei fengið mbl-söluaðila. **1.062 mbl-raðir eiga enga parsed-samsvörun
með söluaðila og ná því ALDREI 100%**; það er bókað í skriftinni sjálfri („NÁANLEGT"-línan) svo
þekjutalan sé ekki lesin sem bilun.

### 1.2 Hvað var gert

**(a) Migration** `supabase/migrations/20260803124500_cc82_listings_agency.sql` —
APPLIED gegnum Supabase MCP `apply_migration` (nafn `cc82_listings_agency`, sbr. læsta regluna
í CLAUDE.md). Sjö dálkar á `scraper.listings` (`agency_name/_phone/_email/_addr/_postcode/_url/
_source_id`), allir með `comment on column` sem nefnir lindina, + `create or replace view
scraper.v_eign_virk_auglysing` með nýju dálkunum **aftast** (röð eldri dálka óbreytt — skilyrði
`create or replace`). Additive: enginn dálkur felldur, engin gögn snert, engin vísitala sett á
(enginn síunar-lesandi er til enn — vísitala bíður raunverulegs lesanda).

**Skalarar en ekki jsonb:** hvert gildi sem BIRTIST er sér dálkur (eins og `bedrooms`,
`bathrooms`); `photos_json` er jsonb af því að það er SAFN. Skalararnir gera þekjumælingu
ótvíræða (NULL = vantar) og halda birtingarlaginu lausu við ótýpaða JSON-gröft.

**(b) Promote-leiðin** (framtíðin heldur sér við):
- `scripts/promote_mbl.py` — ný `parse_agency()` + `AGENCY_MAP`/`AGENCY_COLS`, og `agency_json`
  bætt í BÁÐA arma `extract_common` (sale og rent).
- `scripts/promote_listings_append.py` — `parse_agency` inn í `build_record`, `AGENCY_COLS`
  aftast í `_LISTING_COLS` (og þar með sjálfkrafa í `_UPDATE_COLS` og no-op vörnina).

**EITT HEIMILI KORTLAGNINGARINNAR:** `parse_agency` býr í `promote_mbl.py` og er lesin bæði úr
promote-leiðinni og bakfyllingunni. Afrit hefði getað rekið í sundur — nákvæmlega gildran sem
cc71 leysti fyrir auglýsingatextann og cc75 fyrir HTML-hreinsunina.

**(c) Bakfylling** `scripts/backfill_listing_agency.py` (`--dry-run` / `--confirm`).
Hún er til vegna þess að promote-skriftin er **delta-skrift**: write-settið er
parse-vatnsmerki ∪ unit_key-rek ∪ raðir sem vantar í DB. Raðir sem eru þegar í DB og hafa ekki
breyst hefðu ALDREI fengið söluaðilann. Að þvinga fulla endurkeyrslu í staðinn væri ~36K raða
endurritun = TOAST/WAL-hrina sem cc11-rótarfixið var smíðaður til að forðast.

**(d) Birting** (verdmat-ai):
- `lib/eign-queries.js` — þrír dálkar inn í SÖMU sókn og verðið og textinn fara um
  (`saekjaVirkarAuglysingar`), ekki sér-fyrirspurn sem gæti sagt annað.
- `components/eign/types.ts` — `VirkAuglysing` ber `agency_name/_phone/_email`.
- `components/eign/ASoluKort.tsx` — lína **beint ofan við heimildarlínuna**, inni í
  auglýsingakortinu: `Fasteignasala: Híbýli · 585-8800 · hibyli@hibyli.is`.
- `app/eign/[fastnum]/soluyfirlit/page.tsx` — sama lína + `úr auglýsingu (mbl.is)`,
  **ekki gátuð á `lysing`**: auglýsing getur borið söluaðila þótt lýsingin skili sér ekki, og
  að hengja hana á texta-blokkina hefði tapað honum í nákvæmlega þeim tilvikum.
- `app/globals.css` — `.vm-soluyf-soluadili` (sama stigveldi og verð-merkið).

**Birtingarreglan sem valin var:** söluaðili stendur MEÐ auglýsingunni, aldrei sem staðreynd um
eignina — hann er fullyrðing auglýsanda eins og verðið og lýsingin. Vanti hann birtist
**EKKERT** (ekkert „óþekkt", engin eyða) — sama regla og „verð birtist aldrei án dagsetningar".

### 1.3 Sannreyning

| Próf | Niðurstaða |
|---|---|
| Þekja fyrir → eftir | 0,0% → **96,9%** (33.592/34.654 mbl-raðir) |
| Viðmiðunareignin 2013952 | `Híbýli · 585-8800 · hibyli@hibyli.is · Kringlunni 4-6 · 103 Reykjavík · sala_id 411` |
| Virka-viewið | ber söluaðilann fyrir `listing_id` 297367 |
| `extract_common → parse_agency` | **600/600** nýjustu parsed-raðir (sale+rent) bera söluaðila |
| `parse_agency` jaðartilvik | `None`, ólæsilegt JSON, `{"nafn":"  "}` → allt NULL (autt ≠ gildi) |
| `promote_listings_append --confirm --dry-run` | keyrir hreint: 34.636 raðir byggðar, **write-set 0**, vatnsmerki ósnert |
| `npx tsc --noEmit` | hreint |
| `npm run build` | grænt, allar rútur byggðar |
| Dev-render `/eign/2013952` | línan birtist |
| Dev-render `/eign/2013952/soluyfirlit` | línan birtist með lindarmerkingu |
| **Núll-tilvikið** `/eign/2369174` (enginn söluaðili) | „Fasteignasala" birtist **0 sinnum**, heimildarlínan stendur óbreytt |

⚠ **Ósannreynt:** prod (bíður push) og leigu-flæðið `/leiguverd/[fastnum]` — það notar SAMA
`ASoluKort` og sömu sókn, svo það á að fylgja, en það var ekki rendrað í þessari lotu.

⚠ **Valið sem var tekið án þess að spyrja:** sími og netfang eru **berur texti**, ekki
`tel:`/`mailto:`-hlekkir. Rökin: hlekkur er hvatning, og við höfum enga afstöðu til söluaðilans.
Auðvelt að snúa við ef eigandi vill hitt.

---

## VERK 2 — FASTEIGNAMATS-ÁRGERÐIN (mæld + hönnuð, EKKI framkvæmd)

### 2.1 Fullmælingin

`scripts/hms_mat_vintage_probe.py` — READ-ONLY (eina skrifið er `CREATE TEMP TABLE` sem hverfur
með tengingunni). Ber allar 232.817 HMS-raðirnar saman við `public.properties`.

**NEFNARI: 232.767 fastnúmer eru bæði í `properties` og HMS-safninu** (af 232.887 í töflunni;
120 eiga sér enga HMS-röð). Öll 232.767 bera fasteignamat báðum megin.

| Mæling | Fjöldi | Hlutfall |
|---|---|---|
| Reitirnir tveir ólíkir í HMS-safninu | 230.682 | 99,1% |
| DB = **yngri** reit (`fasteignamat`) | 189.587 | 81,4% |
| DB = **eldri** reit (`fasteignamat_nuverandi`) | 42.510 | 18,3% |
| — þar af raðir þar sem reitirnir eru EINS (ekki frávik) | 2.081 | 0,9% |
| **► STRANGT á eldri árgerð** (DB = eldri **OG** reitir ólíkir) | **40.429** | **17,4%** |
| DB = hvorugum reitnum | 2.751 | 1,2% |
| Miðgildi yngri/eldri í HMS | **1,0976** | +9,8% |

Forkönnunin (582 raðir) sagði 20,1%; fullmælingin segir **17,4%** — sama mynd, skarpari tala.

**Landfræðilega er þetta ekki jafndreift.** Átta efstu sveitarfélög eftir fjölda:

| Sveitarfélag | Á eldri árgerð | Af | Hlutfall |
|---|---|---|---|
| Reykjavíkurborg | 19.341 | 41.789 | **46,3%** |
| Akureyrarbær | 2.700 | 7.218 | 37,4% |
| Hafnarfjarðarkaupstaður | 3.615 | 10.811 | 33,4% |
| Sveitarfélagið Árborg | 1.421 | 4.284 | 33,2% |
| Kópavogsbær | 3.992 | 12.548 | 31,8% |
| Garðabær | 1.811 | 6.158 | 29,4% |
| Mosfellsbær | 1.208 | 4.136 | 29,2% |
| Reykjanesbær | 1.397 | 6.658 | 21,0% |

**Næstum helmingur Reykjavíkur ber eldri árgerðina.** Það er dýrasti markaðurinn og sá sem
flestir notendur fletta upp.

**Í sömu ferð liggur fyrir í HMS-safninu** (sami nefnari 232.767): lóðarmat í krónum
**230.326 = 99,0%** og fasteignamat næsta árs **229.450 = 98,6%**.

### 2.2 Staðfesting: fasteignamat er HVERGI líkanbreyta

Fjórar óháðar heimildir, allar á sama veg:

1. **Þjálfunarskriftin sjálf.** `D:\verdmat-is\models\train_iter4a.py` heitir í hausnum
   „standalone (no fasteignamat input)" og setur `'FASTEIGNAMAT'` beinlínis í `EXCLUDE`.
   Rökin sem skráð eru þar: *HMS fasteignamat er sjálft hedónísk aðhvarfsgreining á kaupskrá —
   að nota það sem inntak gerir líkanið hringlaga og veldur 5–10% stökkum á spám við árlega
   HMS-uppfærslu* (DECISIONS 2026-04-21). **Þetta er beinlínis rökstuðningurinn fyrir því að
   uppfærslan sé hættulaus: líkanið var aftengt frá fasteignamati EINMITT til að árleg
   endurnýjun þess hreyfði ekki spár.**
2. **Lifandi SHAP-lagið.** `public.feature_attributions` ber **25 einstök `feature_name`** og
   ekkert þeirra er fasteignamat. ⚠ Gildra: `feature_name ILIKE '%mat%'` skilar 311.915 röðum —
   það eru `matsvaedi_bucket` og `matsvaediNUMER`. Sá sem grep-ar „mat" fær falskt viðvörun.
3. **Leigulíkanið.** `feature_attributions_rent_staging` ber 14 breytur, engin er fasteignamat
   (`feature_attributions_rent` er tóm).
4. **CLAUDE.md** bókar það sama: „iter4_final_v1 (conformal-calibrated, no fasteignamat input)".

**EIN undantekning fannst og hún stendur UTAN seilingar þessarar uppfærslu:**
`models/calibrate_iter4.py` reiknar `kv_ratio = KAUPVERD / FASTEIGNAMAT` og heldur
0,70 ≤ ratio ≤ 1,50 sem „quality transaction" í kvörðunarlauginni. Það er **ekki líkanbreyta**
heldur síuskilyrði á kvörðunarúrtakinu — og `FASTEIGNAMAT` þar kemur úr
`D:\training_data_v2.pkl`, sem `build_training_data.py` byggir úr **`D:\kaupskra.csv`**
(sögulegt mat á söludegi). `properties_v2.pkl` leggur aðeins til `tegund`, `merking`, `landnum`.
**`properties.fasteignamat` snertir hana því hvergi.**

> ⚠ **SKILYRÐI SEM VERÐUR AÐ ENDURMÆLA:** CLAUDE.md boðar að `rebuild_training_data.py` eigi
> síðar að flytja út úr Supabase í stað `properties_v2.pkl` (Phase X/Y). **Gerist það, verður
> kvörðunarsían skyndilega í seilingu og þessa staðfestingu þarf að endurtaka.** Hún gildir um
> þjálfunarleiðina eins og hún er í dag, ekki um hana að eilífu.

### 2.3 Hönnun uppfærsluleiðar — ENGIN FRAMKVÆMD

Þrískiptingin sem CLAUDE.md bindur allar fjöldaskriftir við (extract → dryrun → apply, með
skýrum HALT á milli) og sem `phase_d1_*` fylgir:

**Skref 0 — leysa árgerðaspurninguna FYRST (blokkerar allt hitt).** Merkingin (hvor reiturinn er
gildandi álagningarstofn) hvílir enn á framsetningu fastinn.is á EINNI eign. Uppfærsla á 40.429
raðir á þeim grunni væri ágiskun í fjöldaskala. Ódýrasta sönnunin: fletta 3–5 eignum upp í
opinberri Fasteignaskrá og bera saman við báða reitina. **Þetta er ógert.**

**Skref 1 — `extract`.** Lesa `fastnum, fasteignamat, fasteignamat_naesta_ar, lhlmat,
lhlmat_naesta_ar, brunabotamat, land_lmat` úr `hms_archive_staging.db` (232.817 raðir) í
staging-töflu. Sama form og `hms_mat_vintage_probe.py` notar nú þegar (temp-taflan þar er
tilbúin fyrirmynd).

**Skref 2 — `dryrun`.** Telja nákvæmlega hvað myndi breytast, per dálk og per sveitarfélag, og
**skrifa rollback-SQL á disk** (`phase_d1`-mynstrið: `D:\cc82_matsargerd_rollback.sql` með
gömlu gildunum). HALT.

**Skref 3 — `apply`.** `SET TRANSACTION READ WRITE` fyrst, síðan `UPDATE public.properties`.

**Dálkaspurningin sem eigandi á að svara (ekki ákveðin hér):**

| Valkostur | Hvað gerist | Áhætta |
|---|---|---|
| **A — uppfæra `fasteignamat` á staðnum** | 40.429 raðir fá yngri árgerð | Enginn ferill: gamla gildið hverfur nema rollback-skráin haldi því |
| **B — nýr dálkur `fasteignamat_hms2026` við hliðina** | Ekkert eldra gildi tapast, birting velur | Tveir dálkar með svipuðu nafni = næsta lota les rangan |
| **C — bæði: uppfæra + `fasteignamat_argerd` merkidálkur** | Talan rétt OG árgerðin sýnileg | Mest vinna, en eina leiðin sem gerir árgerðina lesanlega á yfirborðinu |

⚠ **`lhlmat`-nafnaáreksturinn er FORSENDA, ekki aukaatriði.** `properties.lhlmat` er
**hlutfall** (0–1, meðaltal 0,2214) á meðan HMS-reiturinn með sama nafni er **lóðarmat í
krónum**. Sá sem flytur HMS-`lhlmat` inn í `properties.lhlmat` eyðileggur hlutfallsdálkinn í
hljóði. Lóðarmat verður að fá **nýtt dálkanafn** (t.d. `lodarmat_kr`). Þetta bíður
gjaldskrár-lotunnar (sjá „Sérverk" að neðan) en nafnið verður að vera ákveðið áður en nokkur
HMS-sameining er keyrð.

**Birtingarhliðin (ómetin):** `/eign` sýnir fasteignamat í `Verdmatskort`. Hækki það um ~9,8% á
40.429 eignum breytist sú tala fyrir notendur án þess að nokkurt verðmat hreyfist. Það þarf
skýringu á fletinum (árgerð sýnileg), annars les notandinn það sem breytingu á matinu okkar.

---

## SÉRVERK (bókað, óunnið) — LÓÐARMATIÐ OG OPINBERU GJÖLDIN

Bókað að ósk eiganda: **lóðarmatið bíður.** Krónutalan er á diski með 99,0% þekju
(230.326/232.767) en hún er **inntak í opinberu gjöldin**, og sá flötur fer ekki af stað fyrr en
gjaldskrár-spurningin er leyst:

1. **62 sveitarfélög** í `properties` — álagningarhlutföll (fasteignaskattur A/B/C, vatnsgjald,
   fráveitugjald, lóðarleiga) eru hvergi til hjá okkur.
2. **Eignarlóð vs leigulóð** — HMS greinir aðeins Lóð (224.688) / Jörð (7.871) / Þjóðlenda (258).
   Lóðarleiga fellur niður á eignarlóð; án þeirrar breytu er liðurinn ekki reiknanlegur réttur.
3. **`lodarmat_kr` (eða annað nafn) verður að vera ákveðið** áður en nokkuð er flutt — sjá
   `lhlmat`-áreksturinn hér að ofan.

---

## SKRÁARBREYTINGAR (ekkert committað)

**`D:\verdmat-is\app`** — 2 breyttar, 4 nýjar:
```
 M scripts/promote_listings_append.py        (+7 −1)
 M scripts/promote_mbl.py                    (+55)
 ?? scripts/backfill_listing_agency.py        (ný)
 ?? scripts/hms_mat_vintage_probe.py          (ný)
 ?? supabase/migrations/20260803124500_cc82_listings_agency.sql (ný, APPLIED)
 ?? docs/FASTINN_SAMANBURDUR_CC82_20260803T123103Z.md (ný, leiðrétt)
 ?? docs/SOLUADILI_MATSARGERD_CC82_20260803T133000Z.md (þetta skjal)
```
**`D:\verdmat-is\verdmat-ai`** — 5 breyttar (+49 −1):
```
 M app/eign/[fastnum]/soluyfirlit/page.tsx   (+16)
 M app/globals.css                           (+8)
 M components/eign/ASoluKort.tsx             (+12)
 M components/eign/types.ts                  (+9)
 M lib/eign-queries.js                       (+5 −1)
```

⚠ `scripts/leiga_baseline_fasi1.py`, `scripts/load_predictions_batch.py` og `prototypes/` eru
óskráðar en **ekki úr þessari lotu** — þær eiga ekki að fara með í commit (explicit paths).

**Ástandsmisræmi sem stendur þar til pushað er:** DB-in ber söluaðilann NÚNA (migration + 33.592
raðir bakfylltar) en prod-appið les hann ekki fyrr en verdmat-ai er deployað. Það er hættulaust í
þessa átt — nýju dálkarnir eru viðbót og ekkert lifandi yfirborð les þá enn.

---

## VIÐAUKI 03.08 — SKREF 0 LEYST OG VERK 2 FRAMKVÆMT (append-only, bókað eftir push `1d9a8e2`)

Kaflarnir að ofan standa óbreyttir. Þetta er framhaldið eftir GO eiganda:
**dálkavalið = NÝR DÁLKUR + ÁRGERÐARMERKI**, og skilyrðið *„má staðfesta árgerðina úr
safninu sjálfu frekar en að álykta hana af þriðja aðila? Ef já: framkvæma."*

### V2B.1 SKREF 0 — JÁ, árgerðin er sönnuð innanhúss

`scripts/hms_mat_argerd_skref0.py` (READ-ONLY). Fyrst var athugað hvort HMS-svarið sjálft beri
árgerðarmerki: **það gerir það ekki** — geymda JSON-ið er hrátt svar
`hms.is/api/fasteignaskra/fasteign/<nr>` (`hms_full_scrape.py` línur 45/180/233, engin
staðbundin sameining) og enginn reitur ber ártal matsins. Skjölun dugði því ekki.

**Tímaprófið á kaupskrá dugði.** `D:\kaupskra.csv` ber `FASTEIGNAMAT` = sögulegt mat **á
söludegi**. Fasteignamat tekur gildi 31.12 og gildir almanaksárið á eftir, svo sala ársins ber
það mat sem þá gildir. Nefnari: **177.036 nothæfar sölur** sem eiga HMS-röð.

| söluár | n | = `hms_mat` | = `hms_nuv` | miðgildi `hms_mat`/sögulegt | miðgildi `hms_nuv`/sögulegt |
|---|---|---|---|---|---|
| 2023 | 9.563 | 0 — 0,0% | 0 — 0,0% | 1,3088 | 1,1918 |
| 2024 | 12.587 | 0 — 0,0% | 97 — 0,8% | 1,1378 | 1,0393 |
| 2025 | 11.612 | 9 — 0,1% | **10.615 — 91,4%** | 1,0998 | **1,0000** |
| 2026 | 5.852 | **5.493 — 93,9%** | 1 — 0,0% | **1,0000** | 0,9089 |

**Niðurstaða: `fasteignamat` = árgerð 2026, `fasteignamat_nuverandi` = 2025.** Miðgildin
tvö sem lenda á nákvæmlega 1,0000 eru sterkari en hittnitölurnar: allur árgangurinn liggur ofan
á reitnum, ekki bara meirihlutinn. Framsetning fastinn.is er nú **samhljóða vitni, ekki
forsenda** — grunnregla 13 er uppfyllt, við birtum ekki árgerð sem við getum ekki staðfest.

⚠ Prófið greinir ekki eign sem BREYTTIST (nýbygging, stækkun, endurmat) frá árgerðamun — þess
vegna er hlutfallið lesið en ekki einstök tilvik, og báðir reitir mældir á sama úrtaki.
Afgangurinn (2025: 990 „hvorugt", 2026: 359) er af þeirri stærð sem slíkar breytingar skýra.

### V2B.2 Framkvæmdin

**Migration** `20260803140500_cc82_fasteignamat_hms_argerd.sql` — APPLIED. Þrír dálkar á
`public.properties`:

| Dálkur | Merking |
|---|---|
| `fasteignamat_hms` | talan úr HMS, **ÞÚSUND KRÓNUR** (sama eining og `fasteignamat` og kaupskrá) |
| `fasteignamat_hms_argerd` | árgerðin (2026) — talan er merkingarlaus án hennar |
| `fasteignamat_hms_sott` | hvenær röðin var sótt úr HMS (uppruni, ekki gildistökudagur) |

**`properties.fasteignamat` var ALDREI snert.** Sagan stendur, og munurinn er mælanlegur um
alla framtíð með einni samanburðarfyrirspurn — sem var einmitt rökstuðningur eigandans.

**Skriftin** `scripts/refresh_fasteignamat_from_hms.py` fylgir þrískiptingunni
(extract → dryrun m/HALT → apply) og skrifar rollback-SQL á disk
(`D:\cc82_fasteignamat_hms_rollback.sql` — einn `UPDATE ... SET NULL`, því dálkarnir voru allir
NULL fyrir keyrslu og ekkert eldra gildi er til að endurheimta).

**Árgerðin er LEIDD, ekki harðkóðuð.** Hún er reiknuð úr `fetched_at` hverrar raðar
(almanaksár sóknar = árgerð þess mats sem þá gildir). Harðkóðaður fastinn `2026` hefði lifað af
næstu endursókn og logið þá — `feedback_hardkodadur_argangur_lifir_flipp`. Skriftin **stöðvast**
ef sóknardagar spanna fleiri en eitt ár (31.12-jaðarinn krefst mannlegrar ákvörðunar); í þessu
safni gera þeir það ekki: allar 231.153 raðirnar eru sóttar 03.–05.06.2026.

### V2B.3 Mælingar

| Mæling | Tala |
|---|---|
| HMS-raðir m/fasteignamati | 231.153 (1.664 án mats, slepptar) |
| Raðir sem fengu gildi | **231.103 / 232.887 = 99,2%** (nefnari = allar raðir í `properties`) |
| HMS-raðir án `properties`-raðar | 50 (slepptar) |
| Víkja frá núverandi `fasteignamat` | **43.169 = 18,7%** |
| Árgerðir í safninu | ein: 2026 |
| Sóknarspann | 2026-06-03 .. 2026-06-05 |
| Viðmiðunareign 2013952 | `fasteignamat` 121.450 (óbreytt) · `fasteignamat_hms` **138.100** · árgerð **2026** · sótt 2026-06-03 |

Talan 138.100 er nákvæmlega sú sem fastinn birtir sem „Fasteignamat 2026" — nú fengin úr HMS og
árgerðarmerkt af okkar eigin mælingu.

### V2B.4 Ekkert notendayfirborð breyttist — sannreynt, ekki gefið

| Vörn | Mæling |
|---|---|
| Dálkaheimildir `anon`/`authenticated` | 44 dálkar hvor — **nýju þrír EKKI með** (column-grant lockout heldur sjálfkrafa) |
| `public.v_properties` | ber nýju dálkana **EKKI** (skýr dálkalisti, ekki `select *`) |
| Birtingarkóði | ósnertur í báðum repóum |

Nýju dálkarnir eru þögul viðbót. **Birtingarákvörðunin er ÓTEKIN og var ekki hluti af GO-inu:**
hækki birt fasteignamat um ~9,8% á 43.169 eignum les notandinn það sem breytingu á *matinu
okkar* nema árgerðin sjáist á fletinum. Það er næsta ákvörðun, ekki þessi lota.

---

## ÓGERT / OPIÐ

1. **Commit + push** í BÁÐUM repóum — bíður GO. Tvö aðskilin commit, explicit paths.
2. **Prod-sannreyning** eftir deploy: `/eign/2013952`, `/eign/2013952/soluyfirlit`,
   `/leiguverd/[fastnum]` (leigu-flæðið ósannreynt jafnvel í dev).
3. ~~**Árgerðaspurningin (skref 0)**~~ — **LEYST** 03.08, sjá viðauka V2B.1 (sönnuð innanhúss).
4. ~~**Dálkavalið A/B/C**~~ — **ÁKVEÐIÐ**: valkostur C (nýr dálkur + árgerðarmerki), framkvæmt.
4b. **Birting nýju talnanna** á `/eign` — ÓTEKIN ákvörðun, var ekki hluti af GO-inu (V2B.4).
5. **Nafn á lóðarmats-dálk** áður en nokkur HMS-sameining er keyrð.
6. **`tel:`/`mailto:`** á söluaðila-línunni — valið var berur texti.
7. **Bókun í `DECISIONS.md`/`STATE.md`** — engin journal-færsla skrifuð í þessari lotu.
8. **„Grunnregla 8"** úr verkbeiðni finnst ekki sem númeruð regla á diski; efnið
   („fasteignamat er ekki líkanbreyta, aðeins birt") er staðfest í §2.2 og bókað þannig.
