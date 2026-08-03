# FASTINN-ÚTTEKTIN (cc82) — eiginleika-samanburður, read-only

**Lota:** cc82, 03.08.2026 · **Staða:** READ-ONLY, engin breyting nokkurs staðar · **Heimild verkbeiðni:**
`docs/PRODUCT_SPEC_v1.md` §14 og `docs/PLANNING_BACKLOG.md` „Óskir eiganda 03.08" liður 2 (cc77).

**Forsenda liðarins (óbreytt):** fastinn.is er ÓNÝTUR sem krossheimild — hann speglar mbl-auðkenni
(`reference_alt_sources_unviable`, staðfest aftur í cc68; sjá §2.13 hér að neðan þar sem
auðkennið 1712922 er SAMA mbl-auðkennið og við berum). Þar með er hann hreinn
**eiginleika-samanburður**: það sem hann sýnir og við ekki er **eiginleikaskuld**, ekki gagnaskuld.

---

## 0. Aðferð og mörk

| Atriði | Bókun |
|---|---|
| Athugun | EIN opinber síða skoðuð í vafra: `fastinn.is/soluskra/1712922` (Álftamýri 39, 108 Rvk — sama eign og cc68/cc76 bera) |
| Skröpun | ENGIN. Engin fjöldasókn, engin API-köll, engin auðkenning, engin áskrift keypt |
| Áskriftarefni | EKKI skoðað. Það sem er á bak við 3.850 kr/mán múrinn er merkt `[á bak við áskrift]` og lýst EINS OG MÚRINN LÝSIR ÞVÍ, ekki eins og innihaldið sé þekkt |
| Okkar hlið | Mæld á lifandi DB (`szzjsvmvxfrhyexblzvq`) og skrám á D: — allar tölur bera nefnara |
| Alhæfingarmörk | ⚠ Ein eign er EITT tilvik. Það sem hér er sannreynt á 2013952 er sannreynt á 2013952. Þekjutölur okkar megin eru mældar á öllu safninu og merktar sem slíkar |
| Ómælt | Hvernig fastinn reiknar sínar tölur (aðferð þeirra er ósýnileg); hvort gjaldskrártölur þeirra séu réttar; hvað er á bak við áskriftina |

> **LEIÐRÉTTING 03.08 (skráð við upphaf framkvæmdalotunnar, sama dag).** Fyrsta útgáfa þessa
> skjals mældi „hvað appið ber" í **röngu repói** — `D:\verdmat-is\app` (eldra verdmat-is-appið)
> í stað LIFANDI appsins `D:\verdmat-is\verdmat-ai` (verdmat.ai, HEAD `a640788` = cc75).
> Það felldi **§2.7 þjónustustig** ranglega: nærþjónustu-flöturinn ER lifandi á /eign.
> §1-taflan og §2.7 eru leiðréttar hér að neðan; aðrar mælingar skjalsins voru gerðar á DB,
> HMS-safninu eða `parsed_mbl.db` og snerta ekki repo-valið.

**Síðan sjálf, 03.08.2026:** ásett 174.000.000 kr · 910.042 kr/m² · 191 m² · byggð 1966 ·
44 myndir · „11 daga á Fastanum / Enn í birtingu" · þjónustustig 8.9/10 · umferðarhávaði
„Lítill sem enginn".

**Áskriftarmúrinn (3.850 kr/mán, engin binding):** læsir ÞREMUR flötum — *Verðmat Fastans*
(+ tímalína frá 2006), *Viðhaldsskuld/viðhaldsáætlun*, *Umfjallanir*. Allt annað er OPIÐ,
þar með talin öll opinberu gjöldin, umferðarhávaðinn, þjónustustigið, kaupsamningarnir,
auglýsingasagan og fasteignaskráin.

---

## 1. HEILDARTAFLA — hver flötur sem fastinn ber

Merkingar: **✅** = við eigum gögnin OG berum þau · **◐** = gögnin til, enginn flötur ·
**⛏** = gögnin á diski en ekki í DB · **❌** = eigum ekki · `[á]` = á bak við áskrift hjá þeim.

| # | Flötur hjá fastinn | Staða | (a) Eigum við? Hvar | (b) Ef ekki: hvaðan | (c) Umfang [gróft, ómælt] |
|---|---|---|---|---|---|
| 1 | Fasteignaskattur 248.580 kr | ❌ | Matsstofninn já, **gjaldskráin hvergi** | Álagningarhlutföll sveitarfélaga (opin, birt árlega) | 62 svfn × ~8 reitir/ár + reiknilag |
| 2 | Vatnsgjald 49.105 kr | ❌ | m² já, gjaldskrá nei | Sama | Fylgir #1 |
| 3 | Fráveitugjald 117.862 kr | ❌ | m² já, gjaldskrá nei | Sama | Fylgir #1 |
| 4 | Lóðarleiga 52.800 kr | ⛏❌ | **Lóðarmat á diski (99,0%), EKKI í DB**; gjaldskrá nei; eignarlóðar-fáni **hvergi** | HMS-safnið á D: + gjaldskrár + óþekkt lind fyrir eignarlóð | Sameining úr HMS-safni + #1 + **óleyst skilyrði** |
| 5 | Áætluð heildargjöld 468.347 kr (≈39.029/mán) | ❌ | — | Samtala #1–#4 | Ekkert umfram #1–#4 |
| 6 | Umferðarhávaði (Vegagerðin 2022), 50 dB | ❌ | Ekkert | Hávaðakortlagning (opin GIS-gögn) | Einn flákalagur + punkt-í-fláka á 227.044 hnitum (97,5%) |
| 7 | Þjónustustig 8.9/10, 13 flokkar | ✅◐ | **Nærþjónusta LIFIR á /eign** (9 flokkar, loftlína + kort + sótt-dags). **Samsett stig-tala er ekki til** | Fjórir flokkar til viðbótar úr sömu lind | Reiknilag ofan á lifandi flöt — engin ný gagnasókn |
| 8 | Viðhaldsskuld / ástandsáætlun `[á]` | ◐ | Efniviður til: 36.023 auglýsingatextar á 10.595 fastnúmerum | — | **Blokkerað:** fjöldakeyrsla extraction FROSIN (cc75) |
| 9 | Verðmat + tímalína frá 2006 `[á]` | ✅◐ | Verðmat LIVE (m/vissubili + SHAP); **tímalínan ekki til** | Bakreikningur: `repeat_sale_index` 2006→2026Q2 | Reiknilag + flötur |
| 10 | Þinglýstir kaupsamningar | ✅ | `sales_history` 229.112 raðir, 2006-05-08→2026-07-31 | — | **JAFNTEFLI — við berum meira** (raunvirði) |
| 11 | Auglýsingasaga (söluferli, endurskráningar) | ◐ | `listings` 36.277 · `listing_price_history` 38.960 · `lifecycle_events` 41.067 | — | Enginn flötur — hrein birting |
| 12 | Fasteignaskrá: mat 2026/2025/2024, landeignamat, brunabótamat | ⛏ | **Röng árgerð í DB** (sjá §3.1); 2026 + næsta ár + lóðarmat á diski | HMS-safnið á D: (588 MB, sótt 03.–05.06.2026) | Ein sameiningarkeyrsla |
| 13 | Söluaðili (fasteignasala, sími, netfang, heimilisfang) | ⛏ | **`parsed_mbl.db.agency_json` á 37.517/38.706 (96,9%)** — aldrei flutt í Postgres | — | **Ódýrasti liður úttektarinnar:** promote-dálkar + bakfylling |
| 14 | Löggiltur fasteignasali (nafn + sími) | ❌ | Aðeins innbakað í lýsingartexta | Útdráttur úr texta | Fylgir extraction (frosin) |
| 15 | Teikningar (skjalasafn Rvk-borgar) | ❌ | `attachments_json` aðeins 189 raðir → EKKI lind | Ytri hlekkur á skjalasafn | Hlekkur = ódýrt; eigin safn = dýrt, aðeins Rvk |
| 16 | Gamlar ljósmyndir (Ljósmyndasafn Rvk) | ❌ | Ekkert | Ytri hlekkur | Hlekkur |
| 17 | Umfjallanir í tímaritum `[á]` | ❌ | Ekkert | timarit.is | Leitarvísitala per heimilisfang — dýrt |
| 18 | Samskiptasaga byggingar (byggingarfulltrúi) | ❌ | Ekkert (hjá þeim TÓMT á þessari eign) | Afgreiðslufundir byggingarfulltrúa (opnir) | Skröpun + heimilisfangapörun |
| 19 | Eigindi auglýsingar (4 hópar) | ✅ | `property_attributes`, 28 vokabúlar (cc46) | — | **Við berum fleiri eigindi en þeir** |
| 20 | Dagar í birtingu / „enn í birtingu" | ◐ | `first_seen_at`/`last_seen_at`/lifecycle | — | Hrein birting |
| 21 | Vöktun (fylgjast með eign) | ◐ | `saved_properties`, `saved_searches` til | — | Flötur að hluta til |
| 22 | Hlekkir á mbl/Vísi | ◐ | Uppruna-auðkenni til í `listings` | — | Hlekkur |

---

## 2. FLÖTUR FYRIR FLÖT — mælingarnar

### 2.1–2.5 Opinber gjöld (OPIÐ hjá þeim, sá flötur sem eigandi nefndi fyrstan)

Fastinn sundurliðar hvern lið **með reiknireglunni sýnilegri**:

| Liður | Þeirra tala | Þeirra regla eins og hún birtist |
|---|---|---|
| Fasteignaskattur | 248.580 kr | 0,18% af fasteignamati (138.100.000) |
| Vatnsgjald | 49.105 kr | fastagjald 5.831 + 226,33 kr/m² × 191,2 (þak 0,5% af mati) |
| Fráveitugjald | 117.862 kr | fastagjald 14.065 + 542,87 kr/m² × 191,2 (þak 0,5% af mati) |
| Lóðarleiga | 52.800 kr | 0,2% af lóðarmati (26.400.000) — „á ekki við þegar um eignarlóð er að ræða" |
| **Samtals** | **468.347 kr** | ≈ 39.029 kr/mán |

**Okkar staða, þrír aðskildir hlutar:**

1. **Matsstofninn — EIGUM (en sjá §3.1):** `properties.fasteignamat` þekja 232.887/232.887 (100%),
   `einflm` til.
2. **Lóðarmatið — Á DISKI, EKKI Í DB (§3.2).** HMS-safnið ber `lhlmat` = 26.400 (þús. kr.) fyrir
   þessa eign — **nákvæmlega talan sem fastinn birtir sem „Landeignamat 2026"** — með þekju
   230.376/232.817 = **99,0%**.
3. **Gjaldskrárnar — EIGUM EKKI, hvergi á diski né í DB.** Þetta er eina raunverulega ytri
   gagnaþörfin í öllum gjaldaflötunum. 62 sveitarfélög eru í `properties`; álagningarhlutföll
   (fasteignaskattur A/B/C, vatns- og fráveitugjald, lóðarleiga) eru opinberlega birt árlega.

⚠ **Óleyst skilyrði — eignarlóð vs leigulóð.** Lóðarleiga fellur niður á eignarlóð. HMS-safnið
greinir aðeins `land_gerd` = Lóð (224.688) / Jörð (7.871) / Þjóðlenda (258) — **það greinir EKKI
eignarlóð frá leigulóð**. Án þeirrar breytu væri lóðarleigu-liðurinn annaðhvort rangur á
eignarlóðum eða yrði að fela. Hvernig fastinn leysir þetta er ósýnilegt. **Þetta er opin
gagnaspurning, ekki útfærsluatriði.**

### 2.6 Umferðarhávaði — ❌ eigum ekkert

Þeir sýna dB-tölu (50), bil (50–55), kvarða 48→72 dB, sex þrepa merkingu og fyrirvarann að
mælt sé í 4 m hæð utanhúss. Heimild: kortlagning Vegagerðarinnar 2022.

Okkar hlið: **engin mæld hávaðagögn**. Hnit eru til á 227.044/232.887 = **97,5%** eigna, svo
punkt-í-fláka-pörun er tæknilega bein leið EF flákalagið fæst. ⚠ Ómælt: hvort kortlagningin nái
til allra svæða — hún er lögbundin fyrir stofnvegi og þéttbýli, ekki endilega allt landið.

⚠ **Eina hávaðamerkið okkar í dag er textafengið og virkar ekki.** `LABELING_GUIDE` skilgreinir
`noise_issues` („hávaðamengun", „umferðarhávaði") sem útdráttarlykil, og líkanbreytan
`issue_noise_issues` ER til í iter4r — með **nákvæmlega 0,0 gain, aldrei notuð í splits**
(`docs/fable_prep/audits/ITER4_FEATURES_2026-07-04.md`). Það sem seljandi nefnir í auglýsingu er
því ekki sama breytan og mæld dB-tala utan við húsið; núllvirði fyrri breytunnar segir ekkert um
þá síðari — hvorki með né á móti.

### 2.7 Þjónustustig — ✅◐ LEIÐRÉTT: flöturinn LIFIR, stig-talan vantar

Þeir sýna heildartölu (8.9/10 í haus, 89 í kafla), tvo flipa (Almennt / Fjölskylda) og
**13 flokka** (6 sýndir, 7 faldir): matvara 6.8, strætó 4.7, sundlaug 8.0, líkamsrækt 9.8,
leikskóli 8.3, grunnskóli 9.8 + 7 til viðbótar.

Okkar `public.poi` (sótt **15.07.2026**), 2.635 raðir í **9 flokkum**:

| flokkur | n | | flokkur | n |
|---|---|---|---|---|
| strætó | 1.498 | | apótek | 107 |
| leikskóli | 276 | | líkamsrækt | 66 |
| matvöruverslun | 258 | | heilsugæsla | 45 |
| grunnskóli | 213 | | framhaldsskóli | 35 |
| sundlaug | 137 | | | |

**Sex af sex sýnilegum flokkum þeirra eru til hjá okkur.**

⚠ **LEIÐRÉTT (sjá §0):** flöturinn er EKKI ógerður. `components/eign/Naerthjonusta.tsx` +
`lib/poi.js` + RPC `poi_naesta` birta **næsta stað hverrar af 9 tegundum** á `/eign` og
`/bera-saman`, með fjarlægð, korti, orðinu „loftlína" á hverri línu og upprunalínunni
„OpenStreetMap, sótt [dags]". Fyrsta útgáfa þessa skjals las eldra repóið og fullyrti að engin
notkun væri til nema cc38-frumgerðin — það var rangt.

**Raunverulegur munur er því þrengri en fyrst var bókað:** þeir birta **samsetta stig-tölu**
(8.9/10 + 89, tveir flipar), við birtum **hráar fjarlægðir**. Skuldin er *stigagjöfin* —
vigtun, fjarlægðarfall og kvörðun gegn höfuðborgarsvæðinu — ekki gögnin og ekki flöturinn.
Fjórir flokkar þeirra umfram okkar níu eru ómældir (7 af 13 voru faldir bak við hnapp).

### 2.8 Viðhaldsskuld `[á bak við áskrift]` — ◐ blokkerað

Múrinn lýsir: „Grófreiknuð viðhaldsskuld eignarinnar útfrá nefndum framkvæmdum og áætluðum
líftíma helstu viðhaldsatriða" — byggð á **öllum auglýstum eignum í byggingunni**.

Efniviðurinn er til hjá okkur: auglýsingatextar segja það sem þarf (á þessari eign:
„málað að utanverðu 2025/2026", „múrviðgerð 2024/2025", „gluggar endurnýjaðir 2024/2026",
„eldhús 2021", „bað 2020"). Þekja: **36.023 auglýsingar með texta >200 stafa á 10.595
fastnúmerum**. Byggingar-hópun er möguleg um `landeign_nr`/staðfang.

⚠ **Blokkerað tvennt:** (i) `listing_extractions` telur aðeins **4.922** raðir og
ástands-eigindi (`eldhus_astand`, `badherbergi_astand`, `astand_eignar`) eru á **36
fastnúmerum**; (ii) fjöldakeyrsla brúarinnar er **FROSIN til eftir ágúst-endurþjálfun** (cc75).

### 2.9 Verðmat + tímalína frá 2006 `[á]` — ✅ að hluta

Verðmatið sjálft er okkar sterkasti flötur og er **opið** hjá okkur en **læst** hjá þeim
(3.850 kr/mán). Það sem við eigum EKKI er **tímalínan**: söguleg þróun verðmats sömu eignar
aftur til 2006. Efniviður: `repeat_sale_index` nær **2006 → 2026Q2** eftir
`canonical_code` × `region_tier`. Bakreikningur er því fær án nýrra gagna. ⚠ Aðferðin þeirra er
ósýnileg — ekkert hér segir að tímalínurnar yrðu sambærilegar.

### 2.10 Þinglýstir kaupsamningar — ✅ JAFNTEFLI, við berum meira

Þeirra tafla á þessari eign: 1 samningur, 13.07.2017, 70.000.000 kr, 191.2 m²,
366.109 kr/m², „Sérbýli", heimild HMS.

Okkar `sales_history` fyrir 2013952: **13.07.2017 · 70.000.000 · 191,2 m² — nákvæmlega sama**,
og til viðbótar **`kaupverd_real` = 109.534.989** (CPI-leiðrétt) sem þeir sýna ekki. Safnið:
229.112 raðir, 2006-05-08 → 2026-07-31.

⚠ Þeir para á „eignum sem deila heimilisfangi og stærð"; við pörum á fastnúmeri. Munurinn
skiptir máli í fjöleininga-húsum og er ómældur hér.

### 2.11 Auglýsingasaga — ◐ gögnin til, enginn flötur

Þeirra tafla: „Söluferli 1 · 174.000.000 · 910.042 kr/m² · seld ❌ · 23.07.2026 – Í söluferli".

Okkar gögn fyrir sömu eign (`listing_id` 297367, mbl 1712922): verð 174.000.000, 191,2 m²,
5 herbergi, 3 svefnherbergi, 2 baðherbergi, 46 myndir, `listed_at`/`first_seen_at` **23.07.2026**,
`last_seen_at` 30.07.2026, status `active`. Safnið ber `listing_price_history` (38.960 raðir) og
`listing_lifecycle_events` (41.067) — endurskráningar og verðbreytingar eru þar með **mælanlegar**,
þær eru bara hvergi birtar.

### 2.12 Söluaðili — ⛏ ÓDÝRASTI LIÐUR ÚTTEKTARINNAR

Fastinn birtir: Híbýli · hibyli@hibyli.is · 5858800 · Kringlunni 4-6, 103 Reykjavík ·
Ingibjörg Þórðardóttir (8648800).

**Við eigum þetta þegar — á diski, óflutt.** `parsed_mbl.db` → `parsed_mbl_sale.agency_json`
ber fyrir þessa eign: `nafn` Híbýli, `email_tl` hibyli@hibyli.is, `simi` 585-8800,
`heimilisfang` Kringlunni 4-6, `postnumer` 103 Reykjavík, `vefslod`, `logo_url`, `sala_id` 411.
Þekja: **37.517 / 38.706 raðir = 96,9%**.

Það sem vantar er EKKI gagnasókn heldur **promote-skref**: `scraper.listings` hefur enga
söluaðila-dálka og `parse_mbl.py` skilar `agency_json` sem aldrei fer lengra.
Nafn löggilta salans (Ingibjörg Þórðardóttir) er ekki í `agency_json` — það stendur aðeins í
lýsingartextanum og fylgir því extraction-lotunni.

⚠ Aukageta úr sama lagi: `openhouse_json` er ekki-tómt á **6.272** röðum (opið hús) — flötur sem
fastinn ber ekki einu sinni.

### 2.13 Fasteignaskrá — ⛏ sjá §3.1/§3.2

| Reitur | Fastinn | Okkar DB | HMS-safn á D: |
|---|---|---|---|
| Fasteignamat 2026 | 138.100.000 | — | `fasteignamat` = 138.100 ✅ |
| Fasteignamat 2025 | 121.450.000 | `fasteignamat` = 121.450 | `fasteignamat_nuverandi` = 121.450 |
| Fasteignamat 2024 | 117.500.000 | ❌ | ❌ |
| (næsta ár) | — | `fasteignamat_naesta_ar` = 0 | `fasteignamat_naesta_ar` = 146.500 ✅ |
| Landeignamat 2026 | 26.400.000 | **0,191166 (hlutfall!)** | `lhlmat` = 26.400 ✅ |
| Brunabótamat | 98.300.000 | 101.750 | 104.500 |

Auk þess ber HMS-safnið `land_lmat` = 188.750 (heildarlóð), `land_einflm` = 3.224,
`byggingarstig` B4, `matsstig` 7, `skodags` 2002-06-10 og matseiningar (gerd 2 = „Raðhús"
gegn notkun 501 „Íbúð á hæð" — cc68/cc76-mótsögnin, óbreytt).

**Auðkennisstaðfesting:** slóð þeirra er `/soluskra/**1712922**`; okkar
`scraper.listings.source_listing_id` = **1712922**, `source` = mbl. Speglunin er þar með
endurstaðfest í þriðja sinn — fastinn ber EKKERT sjálfstætt auðkenni.

### 2.14–2.18 Ytri söfn — ❌

**Teikningar** (byggingarteikningar úr skjalasafni Reykjavíkurborgar), **gamlar ljósmyndir**
(Ljósmyndasafn Reykjavíkur, „fást keyptar hjá Borgarsögusafni"), **umfjallanir** `[á]`
(blaðaskrá/timarit.is), **samskiptasaga byggingar** (afgreiðslufundir byggingar- og
skipulagsyfirvalda — TÓM á þessari eign hjá þeim).

Öll fjögur eru **ytri söfn sem við snertum hvergi**. `attachments_json` í `parsed_mbl.db` er
ekki-tómt á aðeins **189** röðum og er því ekki teikningalind. Ódýra leiðin á öllum fjórum er
**hlekkur**, ekki eigið safn. Þrjú af fjórum eiga aðeins við Reykjavík eins og þau birtast hjá
fastinn — landsþekja er ómæld.

---

## 3. GAGNAFUNDIR SEM ERU EKKI EIGINLEIKASKULD

Þrír fundir eru **ekki** „það sem þeir hafa og við ekki" heldur **það sem við eigum en berum
rangt eða óflutt**. Þeir komu í ljós BEINT af samanburðinum.

### 3.1 ⚠ Fasteignamatið í DB er af eldri árgerð á ~fimmtungi safnsins

Fastinn merkir 138.100.000 sem **2026** og 121.450.000 sem **2025**. Okkar DB ber 121.450 fyrir
2013952 — **eldri árgerðina**. HMS-safnið á diski ber báðar.

Mæling á 582 handahófs-fastnúmerum úr HMS-safninu, tengd við `properties`:

| Mæling | Fjöldi | Hlutfall |
|---|---|---|
| DB = `fasteignamat` (yngri árgerð) | 460 | 79,0% |
| DB = `fasteignamat_nuverandi` (eldri) | 117 | **20,1%** |
| DB = hvorugt | 5 | 0,9% |
| Reitirnir tveir ólíkir í safninu | 565 / 582 | 97,1% |
| Miðgildi hlutfalls yngri/eldri | 1,0968 | +9,7% |

**Lesturinn:** safnið okkar er blandað — fjórir af hverjum fimm bera yngri árgerðina, einn af
hverjum fimm þá eldri, og munurinn er ~+9,7% að miðgildi. Eignin sem eigandi hefur borið
saman þrisvar (Álftamýri 39) er í eldri fimmtungnum.

⚠ **Mörk fullyrðingarinnar:** árgerðamerkingin (2026 vs 2025) hvílir á framsetningu fastinn á
EINNI eign. Reitanöfnin sjálf segja það ekki. Fyrir aðgerð þarf óháða staðfestingu á því hvor
HMS-reiturinn er gildandi álagningarstofn.

**Líkanáhætta [mæld á tveimur skrám]:** `build_training_data_v2.py` og `rebuild_training_data.py`
nefna `fasteignamat` **hvergi** (0 hits hvor). Endurnýjun lítur því út fyrir að vera
birtingaratriði en ekki líkanbreyta — en það er mælt á tveimur þjálfunarskriftum, ekki öllum.

### 3.2 ⚠ `properties.lhlmat` er HLUTFALL, ekki lóðarmat — nafnaárekstur við HMS

HMS-reiturinn `lhlmat` = **26.400** (þús. kr., lóðarmat eignarhlutans, þekja 99,0%).
DB-dálkurinn `properties.lhlmat` = **0,191166** (lágmark 0, hámark 1, meðaltal 0,2214 yfir
231.129 raðir) — **hlutfallstala, ekki krónur**.

Sami dálkur ber því allt annað en HMS-reiturinn sem hann heitir eftir. **Lóðarmat í krónum er
til á diski en er ekki í DB** — og það er nákvæmlega inntakið sem lóðarleigu-liðurinn (§2.4)
þarf. Hver sem snertir lóðarmat verður að vita þetta ⚠, annars les hann hlutfall sem krónur.

### 3.3 ⛏ Söluaðili liggur fullbúinn á diski (§2.12)

37.517 / 38.706 (96,9%). Vantar aðeins promote-skref.

---

## 4. ÞAÐ SEM VIÐ BERUM OG FASTINN EKKI

Samanburðurinn gengur í báðar áttir. Eftirfarandi sést hvergi á síðu þeirra:

| Flötur | Okkar staða |
|---|---|
| **AI-verðmat, opið öllum** | Þeirra verðmat er á bak við 3.850 kr/mán |
| **Vissubil + kvörðuð þekja** | Sést ekki hjá þeim (múrinn lýsir „sundurliðun matsins", innihald óþekkt) |
| **SHAP-sundurliðun eigindanna** | Sést ekki |
| **Leigumat og leiguverðsjá** | Sést ekki — fastinn er sölumegin eingöngu á þessari síðu |
| **Raunvirði kaupsamninga (CPI)** | Þeir sýna aðeins nafnvirði |
| **Sambærilegar eignir m/mælingu** | Þeir hlekkja á „verðsamanburð", innihald ómetið |
| **Markaðssamhengi / ATS-vísitala** | Sést ekki |
| **NL-flokkari á /leit** | Sést ekki |
| **„Stilla verðmat" spurningalisti + PDF** | Sést ekki |
| **Eigindavokabúlar (28, cc46)** | Þeir sýna 4 hópa + 3 eiginleika úr auglýsingu |
| **Nærþjónusta með MÆLDRI fjarlægð** | 9 tegundir, loftlína + kort + „sótt [dags]"; þeir gefa stig án fjarlægðar |
| **Myndasafn** | `property_images` 2.583.775 raðir |
| **Opið hús** | `openhouse_json` 6.272 raðir — flötur sem hvorugur ber í dag |

---

## 5. RÖÐUN EFTIR KOSTNAÐI — ENGINN GO, AÐEINS RÖÐUN

⚠ Öll umfangsmöt eru **gróf og ómæld**. Enginn liður er ákvörðun; þetta er röðun til
ákvarðanatöku eiganda.

**Þrep A — engin ný gagnalind, aðeins flutningur/reikningur á því sem við EIGUM:**
1. Söluaðili í DB + á /eign (§2.12) — 96,9% þekja bíður á diski.
2. Fasteignamat + lóðarmat + næsta árs mat úr HMS-safni í DB (§3.1, §3.2) — leysir jafnframt
   árgerðarskekkjuna og opnar lóðarleigu-inntakið.
3. Samsett þjónustustig ofan á lifandi nærþjónustu-flötinn (§2.7) — gögnin OG flöturinn eru til,
   aðeins stigagjöfin vantar.
4. Auglýsingasaga + dagar í birtingu (§2.11, #20) — hrein birting á mældum gögnum.
5. Verðmatstímalína úr `repeat_sale_index` (§2.9) — reiknilag, engin ný gögn.

**Þrep B — ein ný ytri lind, vel afmörkuð:**
6. Gjaldskrár sveitarfélaga → fasteignaskattur + vatn + fráveita (§2.1–2.3). **Lóðarleiga er
   EKKI með** fyrr en eignarlóðar-skilyrðið er leyst.
7. Hávaðakortlagning → punkt-í-fláka (§2.6).

**Þrep C — blokkerað eða dýrt:**
8. Viðhaldsskuld — bíður afþíðingar extraction (cc75) og ágúst-endurþjálfunar.
9. Teikningar / gamlar ljósmyndir / umfjallanir / samskiptasaga — hlekkir ódýrir, eigin söfn dýr.
10. Lóðarleiga — bíður eignarlóðar-breytunnar, sem er **óleyst gagnaspurning**.

---

## 6. OPNAR SPURNINGAR (engin þeirra svarast í þessari lotu)

1. **Eignarlóð vs leigulóð** — hvaða lind greinir þar á milli? Án hennar er lóðarleigu-liðurinn
   ekki reiknanlegur rétt (§2.4).
2. **Hvor HMS-matsreiturinn er gildandi álagningarstofn?** Árgerðalesturinn hvílir á framsetningu
   fastinn á einni eign (§3.1).
3. **Vigtun þjónustustigs** — hvaða flokkar, hvaða fjarlægðarfall, hvaða kvörðun? Fastinn sýnir
   niðurstöðu, ekki aðferð (§2.7).
4. **Á að birta áætluð gjöld yfirleitt?** Þau eru áætlun; röng tala á peningaflöt er dýrari en
   engin tala. Fastinn ver sig með fyrirvara („Raunveruleg gjöld geta verið breytileg").
5. **Pörunarreglan í verðsögu** — heimilisfang+stærð (þeirra) vs fastnúmer (okkar); munurinn er
   ómældur (§2.10).
6. **Verðlagningarmerki:** fastinn tekur 3.850 kr/mán fyrir verðmat sem við gefum. Það er
   markaðsupplýsing fyrir §15 í PRODUCT_SPEC, ekki niðurstaða þessarar lotu.

---

## 7. HVAÐ VAR EKKI GERT

- Engin skröpun, engin fjöldasókn, engin API-köll á fastinn.is. Ein síða skoðuð í vafra.
- Engin áskrift keypt — þrír flötir því aðeins þekktir af lýsingu múrsins.
- Engin breyting á DB, kóða, skrám né stillingum. Þessi skrá er eina ritunin í lotunni.
- Engin önnur eign borin saman. **Allar fastinn-hliðar tölur eiga við 2013952 og ekkert annað.**
- Umfangsmötin í §1(c) og §5 eru gróf; engin þeirra er mæld áætlun.
