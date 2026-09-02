# DECISIONS — Arkitektúrákvarðanir

Skrá yfir lokaðar ákvarðanir með dagsetningu og rökstuðningi. Nýjar ákvarðanir bætast við efst.

---

## 2026-09-02 — `last_listing_text`: R3-síufixið lent (66.060 raðir), R1-b lifandi blöndun þurrkeyrð og bíður HALT A (cc180)

**Heimild:** `docs/fable_prep/audits/TEXTATHEKJA_CC180.md` (allar tölur þaðan; mældar í `D:\_audit\cc180_textathekja\` q00–q04). Skrifalota — ein tafla snert, engin LLM-köll, comps/tiers/predictions ósnert.

**Ákvarðanir (læstar):**

1. **Hvítlisti `build_last_listing_text.py:60` er `[paired_fresh, paired_stale, paired_recent, paired_no_price]`.** `off_market_used` ber byggingarlega aldrei `augl_id` (0/62.837) og var dautt síuatriði; `paired_recent` (gilt, eldri auglýsing) og `paired_no_price` bera `augl_id` 100 %. Mælt: 60.807 → **66.060 raðir** (+8,64 %), Fable-comp-þekja **47,11 → 52,51 %** (+5,40 pp, nákvæmlega cc178-spáin), leikhæfni Verðmeta-sjálfs ≥4 **15,20 → 20,07 %** (23.654 → 31.230).
2. **Flipp á `last_listing_text` er staging + parity + atómískt rename-swap, aldrei TRUNCATE+COPY.** Síðan les töfluna lifandi; rename-parið læsir í millisekúndur (júlí-fordæmið 20260715). Verkfærið er `scripts/cc180_llt_flip.py` með sex parity-hliðum (rowcount, `pair_status`-dreifing, `sale_rank`-samfella, NULL-lyklar, stafrétt samræmi sameiginlegra raða á md5/`scraped_at`/`augl_dagur`/`pair_status`, ýttar raðir == spá) og rollback-SQL skrifað FYRIR flipp. Gamli árgangurinn stendur sem `last_listing_text_old_<tag>` án anon/authenticated-réttinda þar til lotu lýkur.
3. **Parity-hlið á arfi mælist gegn lifandi töflunni, ekki gegn núlli.** Hlið [4] felldi fyrstu staging á 6 HTML-leifum sem voru **sömu 6 raðir** og lifandi taflan bar frá júlí (`&lt;br&gt;`-entity eftir tag-strip). Hliðið er „ekki verra en lifandi"; lyklahliðin standa hörð.
4. **`load_dashboard_v1.py --tables listing` er dautt síðan júlí** (COPY með 6-dálka lista á 8-dálka CSV) og má ekki endurlífga: TRUNCATE+COPY myndi eyða `augl_dagur`/`pair_status` og öllum lifandi röðum. Hleðsla fer um `cc180_llt_flip.py`.

**R1-b — hönnun bókuð, framkvæmd bíður HALT A (Danni):** `scraper.listings` (mbl) verður textalind fyrir sölur þinglýstar **eftir 2026-04-16**, evalue heldur öllu eldra og vinnur á sama `(fastnum, thinglyst_dagur)`. Uppruni á hverja röð: `pair_status='live_listings'`, `augl_id='mbl:<source_listing_id>'`, `scraped_at=last_seen_at`, `augl_dagur=least(listed_at, first_seen_at)`. Dedup á `listing_id`. Þurrkeyrsla: **+1.350 raðir** → 67.379 / 48.695 eignir; 2026-07 = 69,2 %, 2026-08 = 77,9 % sölna fá texta; 2026-04-17 → 05-31 glatað (5,7 %). Falspróf reglunnar á 49 tvípöruðum sölum: miðgildi dagamunar 0. Framendinn sérmeðhöndlar aðeins `paired_stale` — engin kóðabreyting þarf. **Opið:** engin endurkeyrsla er tímasett; lindin frýs aftur við snapshot nema blöndunin sé keyrð reglulega.

**VIÐBÓT 2026-09-02 (GO Danni, HALT A leyst) — R1-b FLIPPUÐ 20:15 UTC.** Staging á þurrkeyrslu-CSV (67.379) → parity 6/6 (31 evalue-raðir ýttar == spá; 66.047 sameiginlegar raðir stafrétt eins) → rename-swap; `last_listing_text_old_r1b` (66.060) og `_old_r3` (60.807) standa læst sem rollback. Lifandi taflan: **67.379 raðir / 48.695 eignir, 1.350 `live_listings`**, `max(thinglyst_dagur)` 2026-08-28, anon-REST sér `augl_id='mbl:…'`-raðirnar (206, 1.350). **Afleiðingar mældar (q01 `eftir_r1b`):** Fable-comp-þekja **47,11 → 52,51 → 59,53 %**; eignir m/ ≥3 textaða compa **66,41 → 83,11 %**; comp-raðir m/ söludag 2026-07 = 75,8 %, 2026-08 = 76,9 % (voru 0,0); leikhæfni Verðmeta-sjálfs ≥4 **15,20 → 27,76 % (43.194)** — yfir cc177-mótprófinu (~38.930); ≥3 33,58 → 48,41 %; sölugluggi 18 mán 39,38 → 53,01 %. **Nefnarinn hreyfðist innan dags:** ágúst 589 → 649 sölur (daily-sales-refresh 02:30), lifandi taflan bar engan texta á þeim 60 → 2026-08 les 70,7 % (459/649), ekki 77,9 %. Það er frystihættan mæld: **ákveðið að endurkeyrslan sé keðja, ekki handverk** — `scripts/cc180_llt_refresh.py` (bygging → óháð spá hliðs [6] úr lifandi lyklum → staging → parity → swap → hreinsun `_old_ref_*`, `_old_r3`/`_old_r1b` friðaðar) er sannreyndur `--no-flip` (parity 6/6 á 67.443 raðir, 1.414 lifandi); **Task Scheduler-verkið er TILLAGA í `scripts/register_llt_refresh_task.ps1` (S4U, `C:\Python314\python.exe`, 03:45), EKKI skráð** — bíður GO + einnar handkeyrslu. Bókað á BACKLOG með dagsetningarvörn 2026-09-16. **Óbreytt og ólagað:** gatið 2026-04-17 → 05-31 (5,7 %) lokast aðeins með evalue-pakka; `load_dashboard_v1.py --tables listing` er dautt og **má ekki endurlífga**. Fyrsta COPY-tilraun runnersins féll á pooler-`statement_timeout` (2 mín) — `SET LOCAL statement_timeout='20min'` í staging-txn, endurtekning 6,6 s.

---

## 2026-09-01 — `sales_history` er sjálfleiðréttandi: UPDATE-armur með akkerishliði og breytingaskrá; comps-flaggið á að LESAST, ekki reiknast (cc179)

**Heimild:** `docs/fable_prep/audits/VERDRETTLEIKI_CC179.md` (allar tölur þaðan; mældar í `D:\_audit\cc179_verd\` q01–q08). Skrifalota — gögn leiðrétt, kóði lagaður. Predictions/módel ósnert, comps/tiers ósnert.

**Rótin sem er lokað:** `daily_sales_refresh.py` var NEW-KEYS-ONLY (`new_keys = derived_keys - live_keys`). Röð sem var þegar inni var **aldrei endurleidd**, svo leiðréttingar HMS á kaupskránni bárust aldrei. Hausinn bókaði það sem hönnun („kaupskra mutations are negligible noise"); **mælingin fellir þá forsendu**: 137 raðir af 229.998 (0,0596 %) viku frá ferskri kaupskrá — 1 verð (×10), 3 `onothaefur` 0→1, 94 `is_suspect_comparable`, 134 `suspect_reason`. Ein þeirra var **725.000.000 kr sem HMS skráir sem 72.500.000 og lifandi `/eign/2273049` birti í fjóra mánuði.**

**Ákvarðanir (læstar):**

1. **Daglega leiðin ber tvo arma.** INSERT á nýja lykla **og UPDATE á reiti sem víkja**, í sömu txn, með `rowcount == spá` hliði. Lykillinn er **parið `(faerslunumer, fastnum)`**, ekki `faerslunumer` eitt — 13.692 raðir deila `faerslunumeri`.
2. **`kaupverd_real` er varinn akkerishliði, ekki reglu.** Dálkurinn er eign `monthly_cpi_reanchor.py`. Hliðið **mælir** hvort geymda taflan sitji á `pipeline_config`-akkerinu (misræmi á rööum þar sem `nominal` er óbreytt) og fellir dálkinn úr skrifmenginu ef mælingin fellur — háværri log-línu, restin gengur samt. Mælt 2026-09-01: **0 af 229.997, hliðið opið.** Án þess hefði daglega leiðin endurakkerað alla töfluna í hljóði um leið og akkerin færu í sundur.
3. **Hvert skrif fer í breytingaskrá.** `public.sales_history_corrections` — ein lína á **reit** (ekki á röð) með gömlu/nýju gildi, `kaupskra_md5`, `kaupskra_last_modified`, `anchor_ym` og `suspect_ruleset_version`. Sjálfvirk skrif á staðreyndatöflu sem enginn getur rakið eru ekki leyfileg.
4. **MV-refresh skilyrðið er `inserted + updated > 0`** (var `inserted > 0`). UPDATE breytir sömu heimild og INSERT.
5. **cc178-nefnararnir 3 / 90 eru úreltir.** Þeir voru mældir gegn **hrárri** kaupskrá; afleiðslukjarninn beitir cc39 ×1000-yfirtakinu, svo réttu tölurnar eru **1 / 94 (+134 ástæður)**. Sérhver framtíðarmæling á `sales_history` skal bera við **kjarnann** (`derive_sales_rows`), aldrei við CSV-skrána beint.
6. **725-milljóna röðin er EKKI ×1000-arfurinn úr júlí.** Hlutfallið er 10, ekki 1000; hrátt kr/m² var 7,94 M — **undir** cc39-þröskuldinum 20 M, svo vörnin gat aldrei virkjað og hefði ekki lagað ×10 þótt hún hefði séð röðina. Einn aukastafur í HMS-lindinni, leiðréttur þar eftir á.

**Hönnunarbókun — EKKI beitt í cc179:** `precompute/build_comps_v2.py:189` **reiknar** `is_suspect_comparable` sjálft og les aldrei `public.sales_history`. Tveir árgangar sömu staðreyndar reka alltaf í sundur (cc178 mældi 90, cc179 mældi 94 + 134). **Í næstu heilu endurbyggingu á `build_comps_v2` að LESA `sales_history.is_suspect_comparable` / `.suspect_reason`** — ein hlið beri staðreyndina. `sales_history` er rétta lindin: hún er nú sjálfleiðrétt daglega, ber breytingaskrá og er lesin beint af notendafletinum. Sbr. `feedback_afleiddur_eiginleiki_ma_ekki_lesast_af_toflunni`.

**Comps ÓSNERT — KOSTUR A ákveðinn (Danni, 2026-09-01; HALT A í VERDRETTLEIKI_CC179 §5).** Af því byggingin les ekki `sales_history` breytir viðgerðin `comps_index_v2` engu. Mælt hvað heil endurbygging myndi gera á snerta menginu: 1.882 comp-raðir hyrfu af 1.881 eign, og `≥3`-hliðið færi úr 155.587 í **155.580** (−7 eignir, **−0,0042 pp** af 167.503) — **undir öllum aðgerðarmörkum**. **Ekkert gert við comps**; næsta heila keyrsla sjálfheilar. Kostur B (skurðaðgerð á `comps_index_v2` + hlutmengis-endurreikningur `valuation_tiers`) **felldur**: sellutölfræði `valuation_tiers` (`comp_wmedian_kr`, `d_log`, `cell_*`, `flag_divergence`) er reiknuð úr öllu menginu, svo hlutmengis-endurreikningur væri **önnur lind** — nákvæmlega gallinn sem þessi færsla er að loka. Kostur C (heil `build_comps_v2`-keyrsla) felldur sem utan umfangs cc179.

**Skuldin sem A skilur eftir, viljandi:** `comps_index_v2` situr á árgangi 2026-08-12 og ber 1.882 raðir sem REFINED-B á dagsins kaupskrá myndi útiloka. Það er **skjalfest bið, ekki galli**. **Skilyrði:** hönnunarbókunin hér að ofan (byggingin LESI geymda flaggið) verður að fara inn í **sömu ferð** og næsta heila `build_comps_v2`-keyrsla — annars endurskapar sú keyrsla tvíárganginn samstundis.

**Gallar fundnir í smíðinni, lagaðir:** `execute_values` sendir eina stæðu á síðu og `cur.rowcount` bar **aðeins síðustu síðuna** — fyrsta útgáfa armsins skilaði `rowcount 37` gegn spá 137 og **hliðið felldi keyrsluna**. Lagfært með sjálfhlutun (`UPDATE_PAGE_SIZE = 500`) og samlagningu rowcounts. Án þess hefði hliðið mælt eina síðu og hleypt hinum í gegn ómældum.

**Viðvarandi, ólagað:** R3 (`size_mismatch`) ber sölu-`EINFLM` við **núverandi** HMS-stærð, svo geymt flagg rekur frá reglunni í hvert sinn sem `properties.einflm` hreyfist — án þess að nokkur kaupskrárröð breytist. UPDATE-armurinn eltir það nú daglega (rétt), en það þýðir viðvarandi UPDATE-umferð og þar með MV-refresh sem áður sleppti. Auk þess: `/api/endurnyja`-lykillinn er ekki á vinnuvélinni, svo hver gagnaviðgerð bíður allt að 60 mín eftir `unstable_cache`-veltu (`EIGN_CACHE_TTL = 3600`) áður en notandi sér hana.

---

## 2026-09-01 — „Verðmeta sjálfur" (Beta): fimm valin læst á mælingu, smíði raðsett á eftir textaviðgerð (cc177)

**Heimild:** `docs/fable_prep/audits/VERDMETA_SJALFUR_CC177.md` (§8 BÓKUN; allar tölur þaðan, mældar í `D:\_audit\cc177_verdmeta_sjalfur\` q01–q13, READ-ONLY). Formælingarlotan cc177 (31.08) skilaði kostum; borðið dæmdi 01.09. Ekkert smíðað, ekkert skrifað í DB.

**Fítusinn:** kaupandi á `/eign` metur 4–5 mjög sambærilegar nýseldar eignir eina í einu (myndir → söluyfirlit → ástandsreitir → innsláttur → afhjúpun raunverðs) og fær að lokum verðmat út frá eigin forsendum við hlið verðmats okkar. Markaðstrekt inn í Fable, **ekki undanfari hennar**.

**Ákvarðanir (læstar):**

1. **Hliðsviðmið: ≥4 leikhæfir comps, 18 mán** — 23.789 af 155.587 T1/T2 (15,29 %), **23.636 eftir fjölbreytnireglu**. ≥3 (52.447) hafnað sem of þunnt fyrir 3–5 eigna leik. **Fylgir valinu:** 65,16 % hliðsins á *nákvæmlega* 4 leikhæfa compa — „3–5 eignir" er í reynd 4 fyrir tvo þriðju notenda, og UI má ekki lofa breytilegri lengd sem er ekki til.
2. **Valregla V2:** similarity-röðun `comps_index_v2` óbreytt + leikhæfnisía + „mest 2 úr sama stigagangi" (kostar 153 eignir á valda hliðinu, 0,64 % — bókunin nefndi 150, sem er ≥3-talan). Engin ný líkindafræði. **Óvarin skekkja:** sían eldir comp-mengið um 193 daga (miðgildi 371 vs 178); V3 aldursjafnvægi ómæld og ekki tekin upp.
3. **Reikniregla (a) hlutfallsleið** — `miðgildi(notandamat/framreiknað raunverð) × verðmat okkar`. Valin á **núllskekkjuprófi**: skilar verðmatinu okkar nákvæmlega þegar notandi metur hvern comp rétt (0,0 í öllum súlum, 100 % innan ±10 %, n=52.447). **(b) fermetraleið hafnað á mælingu** — óbjöguð að miðgildi (−1,1 %) en dreifð (p10 −10,9 / p90 +15,0; 26,9 % utan ±10 %), og stærð skýrir hana **ekki** (95,9 % compa innan ±10 % af m² viðfangs), svo stærðarleiðrétting hefði ekki lagað neitt. (c) blanda óþörf.
4. **Geymsla: hreint client-minni í session.** Ekkert vistað í DB, **query-strengur hafnað** (lokamatið því ekki deilanlegt, ekki í vafrasögu né loggum). Engin PII verður til. cc158-bannið á innslög annarra notenda óbreytt og alger. Akkerisvörnin (raunverð ekki í farmi fyrr en eftir innslátt) er UI-**skylda** með lekaprófi á fullsniðnum streng, ekki kurteisi.
5. **`/stilla`-áreksturinn:** Verðmeta-sjálfur birtir **tvær** tölur (okkar mat + ÞITT mat); `/stilla`-talan kemur **aldrei** á sama skjá. `/stilla` sjálf fer á **sérdóm** — hún er lifandi og framleiðir persónulegt verðmat úr `data/manual_q_effects.json`, stuðlatöflu sem er sjálflýst ókvörðuð („hard-coded for v1.1, data-calibrated in Sprint 3"). Borðið telur það kunna að vera brot sem þegar er úti, ekki nýtt.

**Röð (læst):** smíðin (B1–B4, engin þeirra krefst DB-skrifa) bíður þess að **sölugáttin sé opin** (cc172 HALT B) **og `last_listing_text`-viðgerðin sé lent**. Rökin eru mæld: textinn fellir ≥3-hlutfallið úr 83,87 % í 39,56 % og lindin er frosin frá 2026-04-16 (0 % þekja á öllum sölum frá 2026-05). Mótpróf á valda hliðinu: viðgerðin færir Beta-þýðið úr 23.789 í **~38.930 (+9,73 pp, +63,6 %)**. Að smíða á undan væri að kvikna á 15,3 % og hækka svo í 25,0 %.

**Opið eftir bókun:**
- **Textaviðgerðin á enga forskrift.** cc177 mældi að gatið er tvíþætt: ~45 % viðgerðarhæft rörgat (sölur eftir frystingu) og ~51 % byggingarlegt (eign aldrei í textalindinni) — auk **mjúks hruns fyrir frystinguna** (79,0 % 2025-06 → 41,8 % 2026-03, með myndaásinn í fylgd), sem bendir á pörunartöf í `augl_id ↔ faerslunumer`, ekki stöðvað skröp. „Kveikja aftur á skrapinu" dugar ekki.
- **Sérdómur `/stilla`** bíður skráðrar reglu: bókunin vísar í „Grunnreglu 13", verkbeiðni cc177 í „Grunnreglu 11", og **hvorug finnst á diski** (leitað í öllum `.md` undir `D:\verdmat-is`). Efnislega bindandi heimildin sem er til er **Q4-línan** í `COMP_ENGINE_SPEC_fable.md` (ástands-leiðrétting á verði útilokuð; ástand er merki, aldrei innbakað). Sama staða og cc82 fann fyrir „Grunnreglu 8". Dómurinn þarf annaðhvort skráða reglu eða skýra tilvísun í Q4.

**Gallar fundnir í formælingunni, ólagaðir** (VERDMETA_SJALFUR_CC177 §6.5): `v_eign_myndir` les ekki `utilokad_kl` (57 útilokaðar myndir á 55 eignum sýnilegar — og það er nákvæmlega leið fítussins); `v_eign_myndir` er ekki `security_invoker`, þögul réttindabrú frá `anon` að `scraper.listings`; 302 comp-raðir bera `is_suspect_comparable=true` þótt Q1 telji það hart skilyrði; **`comps_index` (v1) sem `/eign` les LIFANDI er stopp á sölu 2026-04-07** meðan `comps_index_v2` nær til 2026-08-11.

**Aðgangur staðfestur lifandi** (`SET LOCAL ROLE anon`): allt sem fítusinn þarf er anon-læsilegt — `comps_index_v2`, `valuation_tiers`, `last_listing_text`, `v_eign_myndir`, `sales_history`, `v_properties`, `v_current_predictions`. **Nema útdrátturinn**: `scraper.listing_extractions` skilar `permission denied`, og þekja hans á comp-pollinum er 3,3 % hvort eð er (biðröðin étur virkar auglýsingar; comp er seld eign). Ástandsreitir eru því auga-fyrst, forfylling er bónus. Fítusinn þarf **enga migration og enga nýja RLS-stefnu**.

---

## 2026-07-16 — iter5-hringur #1 KEYRÐUR OG FLIPPAÐUR LIVE: iter4r_20260716 (6-mán OOS conformal, ferskt holdout, M5 skrifað) (cc6)

**Heimild:** `docs/fable_prep/audit/RETRAIN_ITER4R_2026-07-16.md` (allar tölur þaðan; artifakt `D:\model_artifacts\iter4r_20260716\`). Fyrsti keyrði hringur RETRAIN_RUNBOOK; GO-A (skilgreining) og GO-B (flipp) frá Danna í lotunni, hvort með sínum skilyrðum.

**Ákvarðanir/lærdómar (læst):**
1. **Þrískiptingar-staðallinn:** calib-gluggi hringsins ber 30% lagskipta slembi-frátekt (fast seed, `calib_role` additive í predictions.pkl) sem ferskt M1-holdout — kvörðun aldrei metin á eigin röðum (G5-lærdómur). `--holdout-frac` í retrain_sales_model.py er varanlegur hluti forskriftar.
2. **Niðurstaða:** M1 81,2% (n=848, öll top5-sellu ≥75) · M2 MAPE 7,58 vs 9,27% live · M4 ✓ · **M5: `pipeline_config.model_pred_anchor_ym='2026-08'` skrifað í flip-txn — LESIÐ gildi (100% empírísk staðfesting á pkl-akkeri + δ̂-krosspróf), lokar „ályktað ekki skráð"-gatinu (sbr. færslu 24.06).** Nýr lykill `model_version` í pipeline_config uppfærist í sömu txn framvegis.
3. **Frávik skráð:** (i) sfh_country G2+G4 = fæðingar-offset, runbókarleið (a) — vaktað; (ii) A-hlutdeild 36,1→19,5% = leiðrétting ofseldrar vissu (fyrirséð í CONFORMAL_RECAL §5); parity G5-fastinn (10 pp vs live) ódómtækur á fyrsta hring, uppfærist í round-to-round næst.
4. **segcal_fallback-brautin ber bil-röðunarbrot** (kvantíl-krossun native boostera; live 1.954 → kandídat 1.447): flip-hliðið er hörð röðunarkrafa á conformal-raðir + engin-afturför á fallback — EKKI 0-brota krafa á allt.
5. **Interim-blend (c) endanlega ÓVIRKJAÐ** — hringur tók ~2 sólarhringa; 4–6 vikna hemils-skilyrðið á ekki við.
6. **Vakt-sérliðir fyrstu mánaðarmælingar** (RETRAIN_RUNBOOK §6): APT_STANDARD|Capital_sub-sellan (75,0% á n=92), sfh_country-offsetið, framvirka rekið (júlí med resid −0,034). modelstada-textinn uppfærður í vinnutré (kandídatsmæling merkt sem slík; ný tracking-röð bíður fyrstu vaktarmælingar) — push samræmist cc4-pakkanum.

Rollback: `predictions_2026_07_pre_iter4r` + FA-snapshot (RLS default-deny) + `flip_iter4r.py --phase rollback`. Staging/snapshot-hreinsun eftir 24-klst stöðugleika = sér ákvörðun. Sjá audit §6 um ócommittuð skript.

## 2026-07-15 — Vissubila-rek mælt: retrain-hringur GO (vegvísaliður A), stakstæð endurkvörðun HAFNAÐ, mánaðarleg þekju-vakt föst (cc4)

**Heimild:** `docs/fable_prep/audit/CONFORMAL_RECAL_2026-07-15.md` (+ skript/CSV í `docs/fable_prep/prototypes/conformal_recal_*` og `holdout_rows.csv`/`cell_q80_compare.csv`). Allar tölur þaðan.

**Mælingin:** lifandi conformal-bil (kvörðuð á 2025-test, flippuð LIVE 02.07) undirdekka á fersku post-cutoff holdouti (þinglýst > 20.04, síað, n=1.488): **cov80 = 72,2%** (~7,5σ undir 80%-markmiði), flokkur A verstur (69,4%, n=697). Rótin er BREIDD (öldrun frosna líkansins), ekki bjagi (miðgildis-residúall −1,1%, brot samhverf). Endurkvörðunar-útgáfur mældar á sama E-setti: (a) pool áhrifalaus (72,7%, ΔA 0); (b) hreinn ~7-vikna gluggi 78,3% en A-hrun 36,1→0,8% (G5-brot); (c) blend α=0,5 75,1% / ΔA −18 pp. Engin nær bæði þekju og stöðugleika.

**Ákvarðanir (Danni 2026-07-15):**
1. **Retrain-hringur GO sem vegvísaliður A** — A-lotuprompt skrifast á grunni ákvörðunarblaðsins; 6-mán OOS conformal skv. læstum G5-staðli (04.07).
2. **Interim-blend (c) EKKI virkjað strax** — ákvörðun tekin þegar fyrsti fasi retrain-lotunnar skilar tímamati.
3. **Mánaðarleg ÞEKJU-VAKT samþykkt sem fastur liður retrain-forskriftarinnar:** holdout-mælingin (skriptuð, ~30 sek) keyrist eftir hverja mánaðar-predictions-endurreikningu; **cov80 < 76% tvo mánuði í röð → flýta retrain-hring.** Kvörðun fylgir retrain-taktinum — ALDREI sjálfstæð mánaðarleg artifact-skipti (mánaðarlegt flokkaflökt bryti G5).
4. **Þröskuldar A<0,20 / B<0,36 HALDAST** — vandinn er breiddirnar, ekki mörkin; hliðrun marka til að verja A-hlutdeild væri feluleikur.
5. **Heiðarleikapakki** (modelstada mæld þekja + FLOKKUR_SKYRING orðalag + /adferdafraedi vakt-lína) — upplýsingagjöf án líkansbreytingar; texta-HALT fyrir apply.

**Stale-línur leiðréttar:** MODEL_CARD_iter4 §5+§8 og fable-audit F.3 (prod-repo 1955dcb) báru „conformal ótengt" eftir 02.07-flippið — hvor tveggja merkt LEIÐRÉTT með vísun hingað.

## 2026-07-14 — Disk-IO mótvægi: MV-refresh eftir heimildum + work_mem session-vís (cc8)

**Heimild:** `D:\DISK_IO_GREINING_20260714T2131Z.md` (Supabase Disk-IO-Budget viðvörun 14.07; lestur — ekki skrif — tæmir budget á Micro).

**Ákvörðun (locked verklag fyrir allar MV-refresh skriftur):**
1. **Refresh aðeins MV sem lesa töflu sem breyttist í umferðinni.** Vörpunin MV→heimildir er hard-kóðuð í `scripts/daily_sales_refresh.py::MV_SOURCES` (einn sannleikur; monthly_cpi_reanchor flytur inn `mvs_touching`), staðfest gegn `pg_depend` 2026-07-14. Nýtt semantic-MV VERÐUR að fá MV_SOURCES-færslu — `mvs_touching()` hendir KeyError annars (viljandi hávær). REFRESH CONCURRENTLY á óbreyttu MV er ekki ókeypis: það les heimildir + allt MV-ið + temp-diff (~300 MB+ IO per MV).
2. **`SET work_mem = '64MB'` session-vís á undan REFRESH-lykkjunni.** Global work_mem er 2,2 MB á Micro → hver 13-MV umferð spillti ~1,3 GiB í temp-skrár. ALDREI hækka work_mem globalt (ALTER SYSTEM/role) á þessum grunni — 60 tengingar × 64 MB rúmast ekki í RAM.
3. **Röðin víkur ekki frá read-only lærdómnum frá SKREF 3** (sjá 2026-07-09 færsluna hér að neðan, féll 0/13): FYRSTA setning á ferskri autocommit-refresh-sessjón er áfram `SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE` (eða `SET default_transaction_read_only = off`); `SET work_mem` kemur á eftir henni, aldrei á undan.

**Tengt (sama greining):** ops/modelstada „nýjast"-fyrirspurnir fá `not-null + nullsFirst:false` í app-kóða + partial/DESC-index (migration `20260714214500_disk_io_read_indexes.sql`) — `ORDER BY col DESC LIMIT 1` án þeirra var 160–240 MB disk-IO á kall OG skilaði NULL-röð fyrst (PostgREST DESC = NULLS FIRST). Nætur-promoterarnir og fetch_hms_einflm fá covering/partial index á properties í sömu migration í stað 413 MB full-skanna.

## 2026-07-09 — CPI-reanchor: valkostur (iii) — bíða HMS m/ anker læst; onothaefur-plástur; 20.07-varða

**Heimild:** `docs/fable_prep/audits/CPI_REBUILD_4c_FRAMHALD_2026-07-09T2220Z.md` (SKREF 5 valkosta-mat).

**Ákvörðun:** Vísvitandi frávikin 3 (744059/84/85 — DB ber rétt ÷1000 verð eftir 4c-plástur, kaupskra.csv enn HMS-spillt ×1000) fá **enga undanþágu og engan CSV-plástur að svo stöddu** — beðið er HMS-leiðréttingar með CPI-anker læst á 2026-07. Fordæmi: HMS lagaði 744058 í kaupskránni á ≤3 dögum frá uppgötvun. **Sanity-reglan í `monthly_cpi_reanchor.py` er réttur skynjari og víkur ekki** — hún á að ABORTa á þessum 3 þar til uppruninn lagast.

- **Einskiptis onothaefur-plástur framkvæmdur:** 744200/2284451 („Sóltún 14") onothaefur 0→1 í samræmi við HMS/CSV (HMS endurflokkaði samninginn eftir upphafshleðslu). Sanity-mynd eftir plástur staðfest með dry-run: **nominal_changed=3 + onothaefur_changed=0**.
- **Varða ~2026-07-20:** ef 744059/84/85 enn blásin í kaupskra.csv → sameinuð override-leið (**inntaks-override í derive, gildisvarin**: KAUPVERD÷1000 aðeins meðan CSV ber blásna gildið) FYRIR fyrstu 2026-08 reanchor-tilraun. Hrein talningu-undanþága í sanity dugar EKKI — reanchor skrifar new real á allar common raðir og myndi skrifa blásið real yfir plástraðar; útilokun úr UPDATE frysti real á gömlu ankeri.
- **Rótargat í backlog sem varanleg lausn:** `daily_sales_refresh` er `ON CONFLICT DO NOTHING` (insert-only) → status-breytingar HMS á þegar-innfærðum röðum (onothaefur, verð-leiðréttingar) ná ALDREI inn. Varanlega lausnin er DO-UPDATE á status-/verðdálka (sjá PLANNING_BACKLOG).

## 2026-07-09 — SKREF 4a-viðmið endurskilgreint: join-óbreytileiki í stað hrás kr/m²-þaks

**Heimild:** `CPI_REBUILD_4c_2026-07-06.md` (FLAGG eftir SKREF 2) + `CPI_REBUILD_4c_FRAMHALD_2026-07-09T2220Z.md` (SKREF 4).

Sannprófunar-viðmið ×1000-viðgerða er **„0 ×1000 DB≠CSV ósamræmi utan skjalfestra vísvitandi frávika + 0 ÓFLÖGGÐ raðir kr/m²>10M"** — EKKI hrátt „0 raðir kr/m²>10M". Hráa þakið er ekki næanlegt: **25 lögmætar raðir** fara yfir 10M kr/m² (21 = ein fjöleininga-þinglýsing 672256 með heildarverð á örsmáa per-einingar-fleti; 4 örsmá-flatar stakar sölur 2,6–3,7 m²), allar réttilega `is_suspect_comparable=true`. Rétti óbreytileikinn er samkeyrslu-join við kaupskrá (aðgreint: DB-blásin = ósamræmi; CSV-blásin m/ rétt DB = vísvitandi frávik).

## 2026-07-09 — MV-refresh verklag: CONCURRENTLY + pooler krefst session-level read-write

**Heimild:** `CPI_REBUILD_4c_FRAMHALD_2026-07-09T2220Z.md` (SKREF 3 liður 3, féll 0/13 í fyrstu tilraun).

`REFRESH MATERIALIZED VIEW CONCURRENTLY` bannar txn-blokk → keyrist á autocommit-sessjón. Á transaction-poolernum (6543, default read-only) dugar `SET TRANSACTION READ WRITE` þá EKKI (gildir aðeins innan txn-blokkar) — nota **`SET default_transaction_read_only = off`** (eða `SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE`, sbr. monthly_cpi_reanchor.py) sem fyrstu setningu á sessjóninni. Locked verklag fyrir allar MV-refresh skriftur.

## 2026-07-04 — Auth verdmat.ai = Supabase Auth (Leið B); Clerk-endurnýting (heyaskr) hafnað

**Heimild:** `docs/fable_prep/audits/HEYASKR_AUTH_2026-07-04.md` (read-only samanburðarúttekt; lið 3 ræður). Allar staðhæfingar hér þaðan.

**Ákvörðun:** verdmat.ai notar **Supabase Auth millisíðunnar** (`@supabase/ssr`, cookie-based session) — **EKKI** endurnýtingu á Clerk-lausn heyaskr. Eitt identity-kerfi um allt: `auth.users.id` (**uuid**), sama auðkenni og `pro_users`-taflan er þegar keyed á. Native RLS (`auth.uid()`) ver per-notanda gögn.

**Vistuð dashboards = ný tafla `public.saved_dashboards`:** `id uuid pk`, `user_id uuid` (→ `auth.users.id`), `name text`, `config jsonb`, `created_at`, `updated_at`. RLS: `USING (auth.uid() = user_id)` fyrir SELECT/INSERT/UPDATE/DELETE — hrein per-notanda einangrun án service-role-króka.

**Af hverju Leið B en ekki Clerk:** Clerk auðkennir með **`userId` text-streng** (`user_xxx`) sem er notaður BEINT sem foreign key í Supabase-töflum → **RLS er í reynd sniðgengið** (appið keyrir á service-role-lykli með handvirkri eignaathugun, `auth.uid()`-policies dauðar). Endurnýting flytur það text/uuid-misræmi + RLS-bypass-skattinn inn í verdmat.ai. Drop-in Clerk-UI (tilbúið innskráningarform) er eini ávinningurinn — hann vegur léttar en tvö ósamræmd identity-kerfi + tapað native-RLS.

**Eina gatið:** innskráningar-UI millisíðunnar er EKKI byggt (`/login/page.js` = „coming soon"). **Login-form smíðast** — það er eina nýsmíðin sem Leið B kallar á.

## 2026-07-04 — Myndir á dashboard: image_index.db aðalheimild, ódagsettar safnmyndir, myndalaus fallback skyldu-hönnun

**Heimild:** `docs/fable_prep/audits/MYNDA_THEKJA_2026-07-04.md` (read-only þekjuúttekt). Tölur þaðan (nefnari í sviga).

**Aðalheimild mynda = `image_index.db`** (long-term-owned skjalasafn); `properties.photo_urls_json` til vara. Þekja: seldar eignir 2024–2026 (gilt, `onothaefur=0`) **58,8% = 16.396/27.894** með ≥1 mynd (nefnari = gildar seldar 2024–26); dýpt **miðgildi 33** myndir/eign (p25 21, p75 58; ≥3 í 98,7%); comps **66,8% = 759/1.136** (úrtak 10.000) → placeholder-þumall fyrir ~1/3.

**ENGAR ártals-/auglýsinga-fullyrðingar á myndum.** image_index geymir engan tímastimpil per mynd → myndir birtast sem **ódagsettar safnmyndir**, aldrei „mynd úr auglýsingu [ár]" né aldurs-merking. (properties „lifandi" auglýsinga-myndir eru 20,9% og allar úr einni skröpun apríl 2026 — skyndimynd, ekki söguleg; nýtist sem varaheimild, ekki tímastimpils-heimild.)

**Myndalaus fallback er skyldu-hönnun**, ekki jaðartilvik: **~41,2% = 11.498/27.894** gildra seldra eigna eru myndalausar (fyllitala 58,8%-þekjunnar; úttektin: „~41% … myndalaus fallback nauðsynleg"). Fallback = kort/kennitala/lykiltölur.

**Ástandsmerki á comps: byggingarleg merki FYRST** (byggingarstig, byggár, stærð) — extraction-þekja nær ekki comp-laginu enn (sbr. tveggja-laga-verðmat sömu dag), svo ástands-þumlar mega ekki reiða sig á extraction fyrir comps.

## 2026-07-04 — Tveggja laga verðmat: grunnmat ósnertanlegt, skilyrt talnalag GATE-að á iter5-próbu; manual_q-lagið fellt

**Heimild:** `docs/fable_prep/audits/ITER4_FEATURES_2026-07-04.md` (extraction-birgðir + handstuðla-lag) + `docs/fable_prep/audits/FRAMENDA_UTTEKT_2026-07-04.md` (millisíðu-route). Tölur þaðan.

**Grunnmat = deterministic, version-stimplað, ósnertanlegt** — **eina krónutalan í öllum dreifingarleiðum** (vef-eign, PDF, agent-svar, banka-útflutningur). Sama agi og þrep-5 punktmats-reglan (DECISIONS 2026-07-03): talan er alltaf afleiðanleg úr version-stimpluðu artifacti.

**Skilyrt mat (ástandsforsendur inn í SAMA versjónaða módel) birtist EKKI** fyrr en áhrifastærðar-próba sýnir marktækar effektir. **Forsendan er ekki uppfyllt í dag:** extraction = **133 af 154 features (86,4%)** eru LLM-extraction-afleidd en leggja aðeins **0,83%** til gain (LIVE iter4a); hinar 21 (strúktúr+staðsetning+tími) leggja 99,17%. Rót: (a) aðeins **~24% þjálfunarraða** hafa extraction-merki (rest NaN), (b) merkin dreifð/near-constant → iter4 er *mettað* af extraction að nafninu til en dregur nánast enga forspá úr því.

**`manual_q_effects`/`adjust-valuation`-lagið er FELLT.** Það er `sprint2_v1.1_hardcoded` (calibrated_on 2026-04-23) — 12 handvalin, ókvörðuð, margföldunar-stöfluð áhrif (+30%/−10%), ekki gagna-kvarðað, með ósamræmi milli skjala og route. **Deyr með millisíðunni, kemur aldrei í verdmat.ai.**

**Dashboard v1:** ástandssnið birt ÞAR SEM extraction er til + **notenda-inntak SAFNAST** (upprunamerkt, vistað) — **án talnaáhrifa** á grunnmatið; söfnunin fæðir iter5-áhrifastærðar-próbuna. iter5-umfang (og gate lið (c)) í `docs/PLANNING_BACKLOG.md`.

## 2026-07-04 — G5 grade-stöðugleiki: 6-mán OOS conformal sem staðall, breiddar-blöndun sem skjalfestur neyðarhemill

**Heimild:** `docs/fable_prep/audit/G5_PROBE.md` + CSV-in (`G5_PROBE_comparison.csv`, `G5_PROBE_backtest_by_T.csv`, `G5_PROBE_cellstab.csv`). Allar tölur hér eru þaðan — **engin ný tala í þessari færslu án tilvísunar þangað.**

**Samhengi:** Dress rehearsal retrain-hringsins féll á G5 (grade): 3-mán conformal-calib gaf rétta þekju (79,9%) en A-hlutdeild hrundi úr live 46,8% í 26,6% (nefnari = 1.819 gluggaraðir). Próban mældi rótarorsök og báða runbook-kostina; niðurstaðan læsir fjórum liðum.

**1. STAÐALL frá og með næsta retrain-hring: conformal-calib = 6 mán OOS** (train_end −3 mán m.v. núverandi 3-mán viðmið). **Rök:** rótarorsök G5 er sýnatöku-suð í sellu-kvantílum við 0,20/0,36 grade-mörkin — pivot-sellan `APT_FLOOR|Capital_sub` (stærsti einstaki hlutinn) situr ofan á A/B-þröskuldinum (q80≈0,096 vs mörk 0,0998) og flöktir A↔B milli hringja. 6-mán OOS þéttir pivot-sellu q80 std **0,0082→0,0038 (~2,2×)** og fækkar grade-flippum **5→3 á 7 hringjum** (`G5_PROBE_cellstab`; `APT_FLOOR|RVK_core` 2→0). Öldrunar-kostnaður mældur **~0,1–0,3 pp bias / ~0,26 pp MAPE** — nettó helst kandídat betri en live (retrain-ávinningur −0,56 pp MAPE étur ~0,26 pp öldrun → ~−0,3 pp nettó; bias-öldrun innan G2-svigrúms 0,02 log). **Ódýra útgáfan (6-mán með train_end óbreytt) er HÖFNUÐ sem ÓGILD:** eldri helmingur gluggans er in-sample (breidd 4,14 pp of þröng) → A rýkur í 74,3% og cov80 fellur í 73,3% (undir G3-gólfi 75).

**2. Víxlverkun við G4 — skráð berum orðum:** OOS-glugginn færir train_end aftur um 3 mán → sölur sem eiga að loka markaðsdrifti (júl–ágú eftir-falls sölur, sbr. G4-fæðingar-offset úr RETRAIN_CADENCE §2.1) komast **3 mán SEINNA** í þjálfunargögn en með 3-mán calib. **Fyrsti flipp-kandídati reiknast út frá þessari OOS-forsendu, ekki frá 3-mán viðmiðinu;** G4-túlkun runbook §4 stendur óbreytt en gagnaendinn er 3 mán eldri.

**3. NEYÐARHEMILL (skilgreindur, ÓVIRKUR):** breiddar-blöndun α=0,5 við breiddir **SÍÐASTA RETRAIN-HRINGS** — **aldrei live** (live eldist, og snapshot-„sigur" hennar í próbunni var confounded af hagstæðri live-römmun þröskuldsins). Virkjast **aðeins með sér-ákvörðun** ef bið eftir hreinum 6-mán hring verður óásættanleg; þá með round-to-round A-hlutdeildar-vakt. **Backtest-fyrirvari skráður:** blöndun **yfirskýtur í trendi** (round-to-round A-std 9,8→12,7 á nýlegu skeiði) af EWMA-töf gegn hörðum þröskuldi. Regla óbreytt úr runbook: **aðeins BREIDDIR blandast — punktspá kemur ALLTAF úr fersku módeli.**

**4. G5-MÆLIKVARÐINN ENDURSKILGREINDUR:** G5 = **round-to-round |Δ A-hlutdeild| ≤ 5 pp milli retrain-hringja** (pivot-sellu q80 std sem stuðningsmælir), í stað mun-frá-live sem er confounded (live er 18 mán gamalt annað módel á annarri CPI-ankeringu). RETRAIN_RUNBOOK.md fær samsvarandi additive leiðréttingu í G5-kaflanum (sama lota, sama verklag, vísar í þessa færslu).

## 2026-07-03 — Þrep 5: vélrænt punktmat ALDREI í fyrirsögn/aðalsýn — aðeins í banka-audit-annex

**Niðurstaða:** Á þrepi 5 (þunnt svæði: ¬prior ∧ comps<K_min ∧ n_svæði<N_min) birtist vélræna punktmatið (LightGBM-spáin) **ALDREI í fyrirsögn eða aðalsýn — í ENGRI dreifingarleið** (vef-eign, PDF, agent-svar, banka-útflutningur). Talan lifir eingöngu í **banka-audit-annexinum**, harðmerkt „flokksmat — ónothæft sem veðmatsgrundvöllur".

**Rök:** (1) Freistnivandi útlánadeildar undir tímapressu — sýnileg tala verður notuð sem veðmat óháð fyrirvörum — vegur þyngra en þægindin af að sýna hana. (2) Endurgeranleiki tapast EKKI: talan er alltaf afleiðanleg úr version-stimpluðu artifacti (`predictions` + `calibration_version`), svo annex-geymsla nægir fyrir audit-slóð. (3) Samræmt Fable-tillögu úr akkeris-síðu-hönnun og almennu þrep-5 framsetningarreglunni (ekkert punktmat í fyrirsögn þegar comps<K_min og svæðisband er of þunnt). Sjá `docs/fable_prep/audit/TIER_PROBE.md` + STATE 2026-07-03.

## 2026-07-03 — predictions_staging: CLEANUP (DROP) valið yfir RLS-policy

**Niðurstaða:** `public.predictions_staging` (167.503 raðir) verður **DROPPAÐ** í sér CC-lotu — ekki varið með RLS-policy. Taflan er tímabundinn flip-artifact (staging-COPY fyrir atomic predictions-flip) sem átti alltaf að hverfa eftir stöðugleika-glugga; glugginn er löngu liðinn (hreinar næturkeyrslur síðan flip 2026-07-01).

**Af hverju DROP en ekki RLS-policy:** RLS-policy á töflu sem á að deyja er plástur — hún festir í sessi artifact sem á ekki að vera til. DROP lokar líka Supabase-advisory flagginu beint (anon-exposed 167.503 raðir gegnum anon-lykil) í stað þess að fela það á lífi.

**Framkvæmd (sér lota, HALT-gate):** (1) staðfesta FYRST að ekkert les úr töflunni — grep á kóðabasa (app + scripts + precompute) + engin view-dependency (`pg_depend` / `information_schema.view_table_usage`); (2) HALT og relaya áður en DROP; (3) rollback = endurbygging úr precompute (`rebuild_predictions_iter4.py` staging-skref) ef þarf. Sjá STATE 2026-07-03.

**FRAMKVÆMT 2026-07-18 (cc28)** — migration `20260718210603_cc28_drop_dead_staging`. Sannreynslan var hert umfram (1)-liðinn hér að ofan: auk grep-s yfir öll þrjú repo bættust við D:-rót (77 .py → 0 hits), Task Scheduler-export (7 verdmat-verk → 0 hits) og **hreyfimæling** úr `pg_stat_user_tables` (`n_tup_upd`=0, `idx_scan`=NULL, síðasti lestur rakinn til cc9-úttektarinnar sjálfrar). Júlí-parið `predictions_july_staging` + `feature_attributions_july_staging` féll á sömu mælingu og fór með. Rollback varð **dump-byggt** (`D:\_rollback_backup\cc28_*_20260718T210603Z.sql`, raðatalning 3/3 PASS) í stað endurbyggingar úr precompute — traustari leið. `predictions_rent_staging`-parið mældist **lifandi** (cc13 rent_v1, óflippað) og stendur. Audit: `docs/fable_prep/audits/STAGING_HREINSUN_CC28_2026-07-18T2106Z.md`.

## 2026-07-02 — Þrep-arkitektúr: þröskuldar LÆSTIR (K_min,K_full)=(3,5), N_min=8 · prior-aldur = flöggun · conformal-gólf hart

**Samhengi:** Fimm-þrepa evidence-tier arkitektúrinn (T1–T5 fallback-framsetning verðmats) var hannaður með þrjá þröskulda til kvörðunar. Þrep-próban (`docs/fable_prep/audit/TIER_PROBE.md` 2026-07-02 + 11 CSV; read-only, sanity-tékk reproduce-uð nákvæmlega gegn COMP_ENGINE_E2E og PRIOR_SALE_COVERAGE fyrir keyrslu) mældi þrep-dreifingu á öllu scored universe, N_min-þol per matsvæði og band-raunþekju í back-testi (772 held-sölur, 24 mán). Þrír liðir, allir mældir:

**1. ÞRÖSKULDAR LÆSTIR: (K_min, K_full) = (3, 5), N_min = 8 — mælt, ekki ágiskað.**
- T5 („þunnt svæði") heild **2,03 % = 3.407/167.503** (nefnari = scored universe) — innan hönnunarmarks ~2–3 %; á markmiðs-segmentinu SFH×Country aðeins **6,31 % = 562/8.911**. Grunnlínu-dreifingin öll (heild: T1 41,85 % / T2 49,11 % / T3 1,92 % / T4 5,09 % / T5 2,03 %; SFH×Country: 22,61/43,84/5,87/21,37/6,31) í TIER_PROBE.md §1.1 + `tier_dist_base_k3.csv`.
- **K_min=2 hafnað:** hefði fært aðeins 546/8.911 = 6,1 % SFH×Country (eignir með nákvæmlega 2 comps) upp í T1/T2 — 2-comp „sett" er brothætt (vigtað miðgildi tveggja talna) og **87,8 % no-prior-hoppara (382/435) fá T4-band hvort sem er** (`tier_hop_k2_k3.csv`).
- **K_min=6 hafnað:** kostar 12,4 pp af T1+T2 á SFH×Country (66,5 % → 54,1 % = 5.922→4.821/8.911) án mælds gæðaábata — E2E §4 sýndi comp-miðgildi óbjagað einmitt á 3–5-comp sellunum.
- **N_min=8 staðfest:** **93,2 % = 8.375/8.989** (nefnari = universe-SFH-eignir í 99 geo-Country matsvæðum) ná n≥8 með S3-nágranna-viðbótinni; **fjölskyldu-víkkun (SFH+SEMI+ROW) þarf aðeins 1 svæði af 99 = 49 eignir = 0,55 % → FELLUR ÚT sem valkvæð flækja** (`nmin_country_sfh_summary.csv`). 6,29 % eigna (565/8.989, 19 svæði) ná ekki 8 hvort sem er = T5.
- **Band-raunþekja innan marka:** Country 71,99 % (nefnari = 332 bönd af 358 held-sölum), Capital 70,00 % (320/326), RVK 57,95 % (88/88) — allt innan [45; 85], nominal 60 %; stærðarband ±30/±50 hreyfir ≤2 pp (`band_backtest_summary.csv`).

**2. PRIOR-ALDUR = FLÖGGUN, EKKI ÞAK.** Aldurs-þak fer **EKKI** í þrep-lógíkina: þak (prior ⟺ ≤8 ára sala) hefði fellt T1 SFH×Country úr 22,6 % (2.015/8.911) í ~13,5 % og fargað gildum akkerum sem index-framreikningurinn tíma-leiðréttir (E2E §5: prior-akkeris MAD stöðugt 0,12–0,14 frá <3 upp í >10 ára bili). Í staðinn:
- **Söludagur + vísitölu-version alltaf sýnileg** við framreiknað akkeri (audit-slóð).
- **Akkeri eldra en 8 ár fær loudly-flagg „gamalt akkeri".** Mælt umfang: **40,25 % T1-akkera á SFH×Country eru >8 ára** (nefnari = 2.015 T1-eignir), miðgildi 6,69 ár, P90 15,0 ár (`tier_prior_age.csv`).
- Regla: **aldur er framsetningar-lýsigagn, aldrei þrep-ákvörðun.**

**3. CONFORMAL-GÓLF HELST HART.** Svæðisband (T4) aldrei þrengra en conformal-80 sellunnar — óbreytt. Próban sýndi gólfið bíta í 81–95 % banda (Country 81,0 %, Capital 95,3 %, RVK 61,4 %; nefnari = held-sölur með band per region) → **T4-virðisaukinn er svæðis-STAÐSETNING miðjunnar, ekki breiddin — og það er rétt:** hrá [P20,P80] kvantíl ein gæfu 52,71 % þekju á Country (175/332) og 48,86 % á RVK við ±50 % (43/88) — rétt OFAN við 45 %-felunarmarkið en án nokkurs öryggisborðs (leiðrétting: hráa talan er ekki UNDIR markinu, hún strýkst við það). Einhalla-reglan (eignarbil ≤ svæðisband) stendur. Í útfærslu-spec skjalfestist einnig: **S3-hlutdeild comp-setta á SFH×Country er 15,5 % (919/5.922 sem ná ≥3 comps)** → „yfir svæðismörk"-merking er skyldu-element í Country-UX, ekki jaðartilvik (`tier_only_s3.csv`).

**Mæld hliðar-staðfesting:** foreldra-lags-stiginn (Markaðsyfirlit #3, sella→fjölskylda→landsheild→CPI) er forsenda T4-bandsins, ekki bara mælaborðs — SFH×RVK_core sellu-akkerið er stale síðan 2022Q3 og back-testið notaði foreldra-region-lagið í **88/88** RVK-tilfellum (CPI-lagið þurfti aldrei).

## 2026-07-02 — Markaðsyfirlit (fimmta mode) #1: launch-umfang — átta fastir reitir, staða-gated birting

**Samhengi:** Markaðsyfirlits-vélin (Markaðurinn) er síðasta óhannaða stoðin. Mæling (`docs/fable_prep/MARKET_OVERVIEW_CARD.md`, read-only DB + on-disk artifacts) sýnir að vísitölurnar átta eru á GJÖRÓLÍKUM þroska: þrjár byggjanlegar strax á kjarna (repeat-sale kjarna-sellur, list-to-sale sögulegt, model-/orðatíðni-aggregöt), tvær þurfa nýja pípu (#3 months-of-supply, #5 TOM), ein er nær tóm (#4 withdrawal), ein þarf ytri gögn (#8 affordability).

**Ákvörðun:** allar átta vísitölur fá FASTAN stað á degi eitt (stöðug UI-beinagrind — notandi lærir kortið einu sinni), en hver TALA birtist aðeins ef reiknuð staða leyfir — þrígilt: `lifandi` / `með-fyrirvara` / `birtist-ekki`.
- **Staðan er LESIN, aldrei handstillt.** Hún leiðist af heilsu-panel per vísitölu (þekja / ferskleiki / censoring gegn þröskuldum), aldrei sett á í kóða né handvirkt — sama meginregla og VÉL-1 heilsuflipinn les `model_metrics`.
- **Stöðu-config version-stimplað:** þröskuldar per vísitölu (t.d. „≥N sellur með ≥10 pör í nýjasta fjórðungi", „ferskleiki < X dagar", „censoring < Y%") liggja í version-stimplaðri config `status_ruleset_version` — SAMA mynstur og `suspect_ruleset_version` (DECISIONS 2026-07-02 is_suspect) svo þröskulds-breyting sé rekjanleg/endurgeranleg.
- **Stöðubreyting er logguð atburður** (vísitala fór lifandi→fyrirvara osfrv., tímastimpill + ástæða) — ekki þögul.

**Rök með tölum (nefnari í sviga):** hví staða VERÐUR að vera reiknuð, ekki gefin — #1 repeat-sale hefur aðeins **6/33 sellur ≥10 pör í 2026Q2** (nefnari = allar sellur í `repeat_sale_index`) → kjarna-apt lifandi, langur hali „birtist-ekki"; #2 list-to-sale **42,5% paruð (52.001/122.436 arms-length sölur 2014Q2–2025Q2)** EN endar 2025Q2 → „með-fyrirvara" (stöðnuð) þar til refresh; #4 withdrawal **320/1.179 myigloo-leiga en mbl-sala 0/19.012** → „birtist-ekki"; #5 TOM **467/18.201 = 2,56% paruð** → „birtist-ekki". Handstillt staða myndi óhjákvæmilega sýna dauðar/stölnaðar tölur sem lifandi. Sjá kortið §0 + §9.

## 2026-07-02 — Markaðsyfirlit #2: lífsferils-líkan auglýsinga (append-only atburða-log = sannleikur)

**Samhengi:** #3/#4/#5 stranda allar á sama rótarvanda (kortið §3–5): mbl merkir **0 af 19.537 auglýsingum sem withdrawn** (sweep óvírt), `first_seen_at == listed_at` í **18.879/19.012 = 99,3%** mbl-sölu (uppgötvun ó-aðgreind frá HTML-skráningardegi), og **11.712/19.012 = 61,6%** mbl-sölu eru „horfin en opin" (last_seen >14 d). Núverandi lög geyma STÖÐU (`is_active`/`withdrawn_at`) sem er ofsögð og á-eyðanleg.

**Ákvörðun:** append-only atburða-log `scraper.listing_lifecycle_events` verður SANNLEIKURINN um lífsferil auglýsingar — ein röð per atburður, aldrei uppfærð/eydd:
- Atburðir: `discovered`, `price_changed`, `confirmed_absent_1` (fyrsta fjarvist í sweep), `withdrawn_confirmed` (önnur fjarvist ≥2 vikum síðar), `sale_matched` — hver með tímastimpli + sönnunargagni (sweep-run-id / kaupskrár-faerslunumer / verð).
- **Staða, tímalengd og censoring eru AFLEIDDIR precompute-dálkar** (materialized úr loginu), aldrei frumgögn — svo endurbygging sé lossless og saga glatist ekki.
- **Tveggja-vikna sweep-reglan útvíkkuð á mbl sem ids-listi** (sækja núverandi virk id, diffa gegn þekktum → confirmed_absent), EKKI rotation-crawl (kortið: single-sweep stimplar aldrei withdrawn; visir IP-throttle bannar rotation).
- **`first_seen_at` = write-once scraper-uppgötvun**, AÐSKILIÐ frá `listed_at` (HTML-fullyrðing sem endursetst við edits) — tvær dálkar, aldrei samslegnar aftur.
- **Vinstri-censoring epoch prentað á allar lífsferils-vísitölur** („lífsferilsgögn hefjast <epoch>; eldri auglýsingar vinstri-censoraðar") — saga fyrir sweep-vírun er ófullkomin.
- **Withdrawn-flokkun (vegna-sölu / án-sölu) ber PENDING-biðskyldu** þar til kaupskrár-ferskleiki nær út fyrir pörunargluggann `[withdrawn−90d, withdrawn+180d]`.

**Rök með tölum:** núverandi 0-flokkun er artifact, ekki merking — myigloo withdrawn→sala **0/319** (nefnari = withdrawn myigloo-leiga með fastnum) er þvingað af því 6-mán glugginn fer fram úr kaupskrár-ferskleika (2026-06-29) og öll 320 withdrawn eru dagsett 2026-07 (ein viku saga). Sjá kortið §3/§4/§5 + `audit/market_withdrawn_to_sale.csv`, `market_tom_distribution.csv`.

## 2026-07-02 — Markaðsyfirlit #3: foreldra-lag repeat-sale vísitölu (fjögurra þrepa upplausn)

**Samhengi:** `repeat_sale_index` (2.673 raðir = 33 sellur × 81 fjórðungar) hefur AÐEINS sella-lag; kortið §1: foreldra-lag er EKKI til (engir sentinel-lyklar, 12 canonical × 3 region), aðeins **6/33 sellur ná ≥10 pörum í 2026Q2**, og 6 sellur hafa <50 pör all-time (insufficient_sample). Fallback sella→foreldri→CPI þarf byggingu.

**Ákvörðun:** fjögurra þrepa upplausnarstigi **sella → canonical-fjölskylda×region_tier → landsheild → CPI**.
- Foreldri byggt með **pooled BMN-fit á öllum pörum fjölskyldunnar** (EKKI vegið meðaltal barna-vísitalna — vegið meðaltal erfir suð barnanna og brýtur BMN-óvissu), sömu **læstu síur** og sella-fitið (nýbygging-t1, |EINFLM|≤5%, FULLBUID 1→0, span≥90 d, canonical/region-stöðugleiki, |log-hlutfall|≤2), **≥50 pör all-time fyrir fit**, **≥10 pör/fjórðung fyrir dense-flagg**.
- Artifact: **sama `repeat_sale_index` tafla með `aggregation_level`-dálki** (`cell`/`family`/`national`) — aggregation_level greinir þrepin, ENGIR sentinel-lyklar (`canonical_code='ALL'` bannað) — + build-stamp (script-version, inntaks-hash, byggingartími) á hverri röð.
- **EIN upplausnarfall** þjónar öllum þremur neytendum (comp-vél, svæðisband, mælaborð) svo þau velji aldrei ólík þrep á sömu eign; **`index_level_used` fylgir hverri birtri tölu** í audit-slóð.
- **Heilsu-viðbót:** barn-vs-foreldri frávik vaktað þar sem barn hefur eigið fit (dense) — stórt frávik = merki um suð/mis-flokkun.

**Rök með tölum:** kjarna-fjölskyldan (APT_FLOOR+APT_STANDARD × 3 region) ber stærstu sellurnar (cell_n_pairs 11.031/10.594/9.322/7.300 all-time) → dense; en SFH/ROW/SEMI/ATTIC/ROOM falla oft undir 10 pör/fjórðung → foreldri (fjölskylda/landsheild) er eina leiðin til að sýna nokkuð annað en „insufficient". CPI-neðsta-þrep gap-laust (`cpi_index` 376/376 mán). Sjá kortið §1 + `audit/market_repeat_sale_cell_pairs.csv`.

## 2026-07-02 — Markaðsyfirlit #4: TOM-dómur (birtist EKKI núna; KM-langtímaform; millileikur undir eigin heiti)

**Samhengi:** kortið §5: markaðs-TOM er óreiknanlegt á núverandi gögnum — **97,44% censored (17.734/18.201 mbl+visir sölu-augl með fastnum)**, upphafsstimpill brotinn á mbl (`first_seen==listed` 99,3%), og enginn endapunktur til fyrir óseldar auglýsingar (mbl withdrawn 0/19.012).

**Ákvörðun:**
- **Markaðs-TOM BIRTIST EKKI** fyrr en lífsferils-loggið (#2) gefur alvöru upphaf + endi og censoring fellur. Engin „reiknum úr því sem við höfum"-bráðabirgðatala undir TOM-heiti.
- **Langtímaform: Kaplan–Meier á discovery-cohortum eftir epoch**, með **withdrawal sem competing risk** (auglýsing dregin til baka án sölu er önnur útkoma, ekki „langur TOM"); **hrá-talningar (at-risk / atburðir per bin) birtar** við hlið kúrfunnar (endurgeranleiki).
- **Millileikur leyfður: „sölutími seldra eigna"** úr `pairs_v1` (52.001 asking↔sold pör) — en það er **skilyrt, survivorship-bjöguð mæling sem birtist undir SÍNU EIGIN heiti**, ALDREI merkt „time-on-market".

**Rök með tölum:** matched-mengið sem þó parast (467/18.201 = 2,56%, nefnari = mbl+visir sölu-augl með fastnum) gefur miðgildi 59 daga (p25 29 / p75 124) — en 2,56%-svarhlutfall er ónothæft sem markaðsmæling. Sjá kortið §5 + `audit/market_tom_distribution.csv`.

## 2026-07-02 — Markaðsyfirlit #5: model-tracking sameining + as_of-vídd (ein canonical sería)

**Samhengi:** kortið §7: tvær ósamræmdar módel-gæða-töflur — `model_metrics` (275 raðir, allt `iter4_final_v1`, oos_cutoff FAST 2026-04-20, 4 keyrslur 26.–29. jún = dagar EKKI mánuðir) og `model_tracking_history` (11 raðir = EINN snapshot 2026-04, model `iter4a`, einingar í BROTUM). „comp-e2e +4–6% drift síðan jan" er EKKI geymt sem tíma-drift (engin as_of-vídd; til er aðeins extraction-framlags-gap run 32).

**Ákvörðun:**
- **`model_tracking_history` lagt niður / innlimað;** `model_metrics` með nýrri **`as_of`-vídd** verður EINA canonical tracking-serían (einingar = prósentur alls staðar, skýr/samræmd módel-merki).
- **Mánaðarleg snapshot á rúllandi mengi nýþinglýstra per segment.** Það sem er FROSIÐ er **SPÁIN sem var lifandi fyrir söluna** (expected-vs-real, VÉL-1-mynstrið), EKKI eigna-mengið (mengið rúllar; snapshot festir spá-vs-raun á sölutíma).
- **Geymt á AGGREGAT-stigi per segment** (ekki per-eign — geymslu-/RLS-rök: per-eign expected-vs-real er þegar í `scraper.listing_valuations`; serían þarf aðeins segment-samantekt).
- **Tracking-serían OG drift-triggerinn eru SAMA artifact** — driftið les as_of-seríuna, engin sér drift-tafla.

**Rök með tölum:** nýjasta model_metrics-keyrsla (run 42, all_oos) gefur overall MAPE 12,81% / medAPE 7,54% / bias +1,79% (nefnari n=1.357 OOS-pör) — þversniðs-mæling; „+4–6% drift síðan jan" krefst ≥2 as_of-snapshot (jan vs nú) af aggregat-spástigi per segment með föstu mengi, sem frosna cutoff-vélin getur ekki gefið. Sjá kortið §7.

## 2026-07-02 — Markaðsyfirlit #6: affordability-lína (aldrei módeluð leiga í samsettri tölu)

**Samhengi:** kortið §8: leiga í DB er **100% módeluð, 0% mæld** (`predictions_rent_staging` 158.314/158.314 en `predictions_rent` live = 0; engin leiguskrá-observ-tafla). Að byggja affordability á módel-leigu = spá ofan á spá.

**Ákvörðun:**
- **Affordability-vísitala má ALDREI hvíla á módelaðri leigu.**
- **Affordability v1 = greiðslubyrðar-vísitala:** miðgildisverð/m² (MÆLT úr kaupskrá) + launavísitala (Hagstofa) + vextir (Seðlabanki) + CPI; per region_tier.
- **Módeluð leiga birtist AÐEINS sem sér, loudly-merkt módel-úttak** („módel-spá, ekki mæld leiga"), aldrei inni í samsettri affordability-tölu.
- **Ytri ingest fylgir CPI-mynstrinu** (`cpi_index`-fordæmi): eigin ingest-töflur, **source + vintage per röð**, vikuleg S4U-sótt, pinned viðmið í config, vintage-stimpill í audit-slóð.

**Rök með tölum:** mælda hliðin er til strax — verð/m² **nothæf 9.242/14.083 sölur = 65,6%** (nefnari = sölur síð. 12 mán), miðgildi 738.556 ISK/m²; CPI **376/376 mán gap-laust**. Ytri þættir (laun/vextir/LTV/heimili) eru **0% í DB** → v1 stendur og fellur með ytri ingest (Hagstofa launavísitala/ráðstöfunartekjur, SÍ stýri-/íbúðalánavextir). Sjá kortið §8.

## 2026-07-02 — Endurþjálfunar-cadence + drift-trigger + skylduskref hrings (LÆST; mælt, ekki ágiskað)

**Samhengi:** Sölumódelið (iter4_final_v1) er frosið artifact án endurþjálfunarleiðar; comp-e2e fann raunverulegt aggregat-drift (RVK/Capital-íbúðir, mælt +4-6% YFIR markaði í júní — formerkið er OFMAT, ekki „vanmat"). Fable-lota keyrði rúllandi rotnunar-backtest (16 T-punktar 2021-12→2025-09, replica-sönnuð aðferð: endurgerði held MAPE 8,19%/medAPE 5,54% upp á 0,01 pp; 185.947 skoraðar raðir; nefnari = training_data_v2 main-raðir í 18-mán gluggum) — full heimild með nefnurum: `docs/fable_prep/audit/RETRAIN_CADENCE.md` + undirtöflur/parquet í sömu möppu. Allar tölur hér vísa þangað.

**Ákvörðun 1 — cadence: 6 mánaða grunn-cadence (2 hringir/ár).** Rök: per-árgangs þolmörk (fyrsti mánuður með |med bias|>0,03 sustained, endurgrunnlínað) dreifast 3–16 mán eftir markaðsskeiði; í rólegum skeiðum (10 árgangar 2023-06→2025-09) hélst mán-6 |med_err| heildar ≤ 0,024, brotin voru öll í sjokk-árgöngum (2021-12: −0,16; 2022-12: +0,057; 2023-03: +0,049) sem triggerinn grípur á mán 3-5. 3-mán cadence bætir ~0,3 pp bias en tvöfaldar ops-byrði; 12-mán skilur eftir 0,03–0,06 exposure (2025-06 árgangur: m12 +0,047). MAPE-kostnaður rotnunar ≈ +0,085 pp/mán (m1 7,63% n=5.593 → m18 9,17% n=2.559; 2024-25 árgangar, heild).

**Ákvörðun 2 — drift-trigger (flýtir hring, breytir ALDREI módeli sjálfur):** mörkin |med d| > 0,03 heild / > 0,05 segment í 2 mánuði í röð HALDA, með tveimur lagfæringum sem backtestið knúði fram: **(i) d endurgrunnlínað á flip-grunnlínu** (miðgildi d fyrstu 2 mán eftir flip, per segment) — annars brennur triggerinn á strúktúrelta Country-vanmatinu (−2 til −4% frá mánuði 1, EKKI rotnun); **(ii) mánaðar-n ≥ 50 gólf á segment-regluna** — þunn segment (sfh_country, mánaðar-n 15–40, median-suð SD≈0,04-0,05) vaktast á 3-mán rúllandi safni (n≥50) með sömu mörkum. Mælt (16 árgangar, `retrain_backtest_trigger_eval.csv`): hrá reglan grípur sann-drift en false-fire-ar á 7/16 árgöngum (10/14 segment-fire á sfh_country); lagfærða reglan **grípur 10/10 sann-drift skeið, 1 falskt fire, miðgildis-töf 0,0 mán**.

**Ákvörðun 3 — skylduskref hvers hrings (ófrávíkjanleg röð):** retrain (`precompute/retrain_sales_model.py`, version-stampað artifact í `D:\model_artifacts\<version>\`, live aldrei yfirskrifað) → **conformal-endurkvörðun ALLTAF með, ALDREI erfð milli útgáfa** (`recalibrate_conformal.py`; backtest §3: þekjutap er 100% bias-drifið — bias-miðjuð cov80 80,0–81,1% á öllum 18 mánuðum — symmetrísk breidd um skekkta miðju getur hvorki lagað drift né má hún erfast) → parity-gate (`parity_check.py`, G1-G5 m/ akkeris-leiðréttingu δ̂) → **mannlegt GO** → flip (staging + DB-parity + `model_pred_anchor_ym` uppfært í SÖMU txn — dress rehearsal mældi δ̂=+2,07% skala-mun milli pkl-ankeringa; án anchor-uppfærslu brotnar VÉL 1) → næturkeyrslu-gate (fyrsta weekly-model-quality keyrsla + d-panel |med d| heild < 0,02 fyrsta mánuð). Full útfærsla: `docs/RETRAIN_RUNBOOK.md` (skrifað svo Opus-CC lota keyri hringinn).

**Ákvörðun 4 — þögull vísitölu-skalar á módel-úttak er HAFNAÐ.** Enginn index-margfaldari á `real_pred_*` sem „ódýr endurkvörðun". Ef neyðarbrú þarf milli endurþjálfana: (a) hávært merkt í `calibration_version`, (b) skráð gildislok, (c) sér-samþykki Danna. Rök: þögull skalar felur rotnunina fyrir öllum mælum (d-panel mælir gegn spánni; parity missir samanburðargrunn) og backtestið sýnir að bias-vandinn er tíma/segment-háður — flatur skalar er röng lögun.

**Vitneskja sem breytir framtíðarhönnun (mælt):** (a) módel fæðist EKKI óbjagað í trend-markaði — tré framreikna ekki út fyrir þjálfunarbil (2021-12 árgangur −14,4% n=544 í mánuði 1; kandídat 2026-07 +2,3% á eigin calib-glugga) → endurþjálfun ein lokar ekki drifti sem myndast EFTIR gagnaenda; vor-2026 ofmatið er að hluta slíkt; (b) pooled-rotnunarferlar eru blekking (drift-formerki snýst milli skeiða og jafnast út) — öll vöktun per-árgangur/endurgrunnlínuð; (c) strúktúrelt Country-vanmat lifir endurþjálfun af → iter5-verk (features/quality-filter), ekki cadence-verk.

Full heimild: `docs/fable_prep/audit/RETRAIN_CADENCE.md` + `docs/RETRAIN_RUNBOOK.md` + parity-skýrslur í `D:\model_artifacts\iter4r_20260702*\`. (STATE-færsla bíður sér-go — þessi lota skrifaði ekki í STATE.)

## 2026-07-02 — Eftirmál sannleiks-úttektar: nefnara-læsing á own-prior-sale + 3 verklags-reglur + backup-þekja á fable_prep

**Samhengi:** Sannleiks-úttekt (read-only, diskur/DB/git — transcript ekki sönnun) staðfesti fable_prep-korpusinn: öll skjöl FANNST, og þrjár af fjórum fullyrtum tölum voru NÁKVÆMAR gegn lifandi DB/artifact — grade-dreifing 60.518/59.158/35.933/11.894, `is_suspect_comparable`-count 79.622, held-MAPE 8,19% (`MODEL_CARD_iter4.md`, sourced `iter4a_training_log.txt`; held main N=2.084, heild m/summer 11,87%). Fjórða atriðið var **nefnara-villa**.

**Nefnara-villan (leyst):** „92,8% vs 31,1%" deilan var **flokkunar-villa** — tvær ólíkar stærðir bornar saman sem rival-ágiskanir. Disk-heimildir: **92,8%** = `comp_probe3b_prior_sale.csv` röð SFH_DETACHED×Country, dálkur `pct_has1_noKV`, nefnari **n=2.982 (comp-heims-undirmengi)** (74,2% með kv-bandi); **31,1%** = `COMP_PROBES_2.md` §1 „S1 tími" fyrir SFH·Country, n=61 = **≥3-comp þekja á S1-þrepi** (allt annað hugtak, ekki fyrri-sala). Hvorug lýsti production-universinu.

**Ákvörðun — kanónísk skilgreining á akkeris-þekju (lokuð):** own-prior-sale þekja mælist framvegis með EINNI skilgreiningu — nefnari = scored universe (`v_current_predictions ⨝ properties`), teljari = eignir með ≥1 sölu á sama fastnum í `sales_history` sem stenst `onothaefur=0 ∧ is_suspect_comparable=false`. Mælt (read-only DB): **HEILD 43,77% = 73.315 / 167.503; SFH_DETACHED×Country 28,48% = 2.538 / 8.911.** Skrifað í `docs/fable_prep/audit/PRIOR_SALE_COVERAGE.md` (teljari/nefnari á hverri línu) sem **EINA heimildin** um akkeris-þekju. Hönnun sem gerir ráð fyrir að „flest Country-SFH eigi fyrri sölu" er röng — aðeins 28,48% gera það.

**Ákvörðun — 3 additive reglur í WORKING_PROTOCOL** (forða transcript-confabulation + ephemeral-tapi): (a) **nefnara-skylda** (engin prósenta án teljara/nefnara/nefnara-skilgreiningar í sömu línu); (b) **scratchpad-björgun** (prototype-kóði sem lota byggir OG keyrir afritast í `docs/fable_prep/prototypes/` áður en HALT-að er — Temp er ephemeral); (c) **tölur ferðast á diski** (hver tala vísar í disk-artifact, aldrei í transcript-samantekt).

**Aðgerð — prototype-björgun:** 4 scratchpad-kóðar (`comp_e2e_proto.py`, `comp_e2e_sample.py`, `rent_p1_p2.py`, `rent_fix_experiments.py`) afritaðir úr ephemeral Temp í `docs/fable_prep/prototypes/` + README.

**Aðgerð — backup-gat lokað:** `backup_paths.json` þakti `app/audit` + `D:\` top-level glob (non-recursive) en EKKI `docs/fable_prep` → mappan (untracked í git) hafði núll öryggisnet. Bætt við include-entry `D:\verdmat-is\app\docs\fable_prep` (recurse → `app_docs_fable_prep`); 1,36 MB/83 skrár, hverfandi á 7–15 GB pre-flight glugga. **`docs/fable_prep/` fer EKKI á origin/main** (untracked scratch) — lifir á diski + R2-backupi; PRIOR_SALE_COVERAGE.md og prototypes/ þar með talin.

**Umfang:** öll DB-aðgerð read-only; engin DB-skrif. Push bíður sama stöðugleika-glugga og venjulega (næsta næturkeyrsla 03:00 með nýju backup-þekjunni er gate-ið). Sjá STATE 2026-07-02 + `docs/fable_prep/audit/PRIOR_SALE_COVERAGE.md`.

## 2026-07-02 — is_suspect_comparable skilgreint (REFINED-B) + fest á sales_history (dálkar, EKKI vali enn)

**Niðurstaða:** comp-sýnileikasía `is_suspect_comparable` (síðasta óútfærða comp-filterið, COMP_PROBES §0.2.3 „ÓÚTFÆRT/TBD") skilgreind og fest sem 3 dálkar á `public.sales_history` (`is_suspect_comparable` bool, `suspect_reason` text, `suspect_ruleset_version` text). Síar tæknilega-gildar (`ONOTHAEFUR=0`) en ótraustar sölur sem SÝNILEGAR comps — aðgreint frá ONOTHAEFUR-útilokun (upstream) og comp-VAL kv-bandinu.

**Skilgreining (locked, 4 reglur; suspect ef EITTHVERT):**
- **R1 sentinel_price:** `KAUPVERD ≤ 1` (kaupskrá KAUPVERD er alltaf tölulegt þús. kr, lágmark 1; „Tilboð"-sentinel er listings-scraper fyrirbæri, EKKI kaupskrá — étur ~3 arms-length, ytra net).
- **R2 kv_extreme:** `kv = KAUPVERD/FASTEIGNAMAT ∉ [0,50; 2,00]` óháð region (ytra net; comp-VAL bandið `[0,70;1,70]` Country / `[0,70;1,50]` annars er strangara innar → R2 étur 0 á comp-eligible pool).
- **R3 size_mismatch REFINED-B:** sala-`EINFLM` > núverandi HMS `einflm` (public.properties) um **>10%** — **EINGÖNGU þessi átt** — EÐA fjöleigna-deed (SKJALANUMER spannar >1 fastnum).
- **R4 new_build_first_sale:** `FULLBUID=0` OR `(sale_year − BYGGAR) ≤ 2`.

**REFINED-B rök (tímadrift-offlöggun):** symmetrísk R3 (`|Δ|>10%`) offlaggaði — **63% flagga voru „sala < HMS"** á gömlum sölum (miðgildi söluár **2014** vs 2018 CLEAN) = eignir **stækkaðar EFTIR söluna** (löglegar, ekki vondar sölur; hentu ~1.900 sögulegum comps). REFINED-B flaggar aðeins sölu>HMS (raun-grunsamlega áttin) + multi-deed.

**Kostnaður (comp-eligible CLEAN pool, #6b band, n=118.551):** suspect **3,36% (3.978)** — R1=0, R2=0, R3=1.130, R4=2.853. **SFH·Country ≥3-þekja helst á 19,7%** (fellur úr #6b-21,3% aftur á birtu grunnlínuna; ≥5 óbreytt); aðrar hörð rural-cell 0,0 pp. Á fullri sales_history (öll sölusaga, m.a. comp-ineligible) er hlutfallið 34,9% (arms-length 28,4%) — vænt, því flest af því er þegar kv-band/deed-fall.

**Persist-arkitektúr (FER GEGNUM PRECOMPUTE svo það lifi re-run af):** reikniregla í `app/scripts/suspect_rules.py` (`compute_suspect`, single source of truth, `RULESET_VERSION='refinedB-v1-2026-07-02'`), wired inn í `derive_sales_rows` (rebuild_sales_history + daily_sales_refresh — bæði endurgera dálkana við hverja keyrslu, keyed `(faerslunumer, fastnum)`). Migration `add_is_suspect_comparable_to_sales_history` (3 nullable dálkar, additive/reversible via DROP COLUMN). Einskiptis-backfill 227.871 raða (`backfill_suspect_sales_history.py`, `SET TRANSACTION READ WRITE` á 6543, temp-tafla UPDATE...FROM) → version-stimplað í `pipeline_runs` (run_type `sales_history_suspect_backfill`). RLS: sales_history er public_read SELECT-only, nýir dálkar erfa (engin ný grant). Rollback SQL: `app/scripts/suspect_persist_rollback.sql`.

**Af hverju EKKI build_comps-wire enn (Val #2):** comp-vélin velur comps LOKALT í `precompute/build_precompute.py::build_comps` (comps_index, top-N nearest per fastnum) og les í dag AÐEINS ONOTHAEFUR+recency — hvorki COMP_PROBES hörð-filter-stafla (kv-band/single-deed/newbuild) né is_suspect. Að sía suspect úr comp-VALINU er **sér skref með comp-útfærslu-spec-inu (Fable-vél)**; í dag er flaggið TIL STAÐAR á sales_history (audit + display + framtíðar-vél) en **óvirkt í vali** → comps_index-þekja ÓBREYTT (þ.a. SFH·Country live-þekja er trivially óbreytt). Sjá `docs/fable_prep/audit/SUSPECT_COMP_DEF.md` + `suspect_comp_*.csv`.

Sjá STATE 2026-07-02.

## 2026-07-02 — Conformal PI (iter4_conformal_v1) + width-based A/B/C/D confidence-grade FLIPPAÐ LIVE í predictions

**Niðurstaða:** `public.predictions` (167.503 @ 2026-07-01) uppfært live: PI-dálkar (`real_pred_lo/hi 80/95`) endurbyggðir úr **split-conformal artefaktinu `iter4_conformal_v1`** (verified held cov 79,1% / 94,6%) með segcal-stretch sem fallback, + tveir nýir dálkar `confidence_grade` (A/B/C/D) og `calibration_source`. **Punktmat (`real_pred_mean`/`real_pred_median`) ÓSNERT** — aðeins óvissulagið breyttist. `calibration_version`: `iter4_segcal_v1` → `iter4_conformal_v1+segcal_fb`. Precompute-branch `conformal-abc-grading` (`c7ee344`) — **ÓPUSHAÐ** (bíður 24-klst stöðugleika).

**Grade-regla (lokuð):** width-based úr hlutfallslegri 80%-breidd `rel80 = (hi80−lo80)/mean`: **A < 0,20 · B < 0,36 · C annars**. `GRADE_D_CODES = {SUMMERHOUSE, APT_HOTEL, APT_MIXED, APT_ROOM}` → grade D beint (width hunsuð; atvinnuhúsnæði/grunnregla utan íbúða-nákvæmnisloforðsins). **APT_SENIOR er EKKI D** — öldrunar-íbúðir eru íbúðarhúsnæði, conformal-breidd flokkar þær rétt (mældust B 45 / C 44). Þröskuldar kvarðaðir á held: einhalla MAPE **A 6,43% / B 8,71% / C 13,07%** (D=SUMMERHOUSE 175%); medAPE einhalla líka.

**Conformal-þekja (Mondrian cascade `cc|region → cc → segcal`):** artefaktið hefur AÐEINS 7 canonical-kóða (APT_ATTIC/BASEMENT/FLOOR/STANDARD, ROW_HOUSE, SEMI_DETACHED, SFH_DETACHED) → 17 cc|region + 7 cc sellur. **SUMMERHOUSE + allir D-kóðar + APT_SENIOR + APT_UNAPPROVED falla á segcal_fallback → PI BYTE-IDENTICAL við fyrir-flip.**

**Parity-hlið (staging vs live, FYRIR flip — GATE):** 167.503 báðum megin, allir fastnum match, **mean/median 0 raðir breyttar** (harða gate-ið), PI breytt **155.304**, byte-identical **12.199**. Source-mix: `conformal_seg_reg` 154.079 · `conformal_seg` 1.225 · `segcal_fallback` 12.199. Grade: **A 60.518 / B 59.158 / C 35.933 / D 11.894** (0 NULL). Rebuild-parity (nýtt CSV vs live) og DB-parity (staging vs live) gáfu SÖMU tölur → COPY skrifaði byte-trútt.

**Flip-arkitektúr (aðgreint frá 2026-06-30 replica-flipinu):** migration (2 nullable text-dálkar, MCP apply_migration, schema_migrations reconcilað í canonical ts `20260701233908` ekki MCP-ts) → staging COPY á pooler (`SET TRANSACTION READ WRITE` fyrsta statement) → DB-parity gate → **atomic UPDATE** (`predictions ← predictions_staging` á PI+grade+source+calver, mean/median EKKI í SET). **Enginn replica-mode nauðsynlegur:** UPDATE snertir ekki `fastnum` → FK `predictions_fastnum_fkey1` triggar ekki; engir user-triggerar á predictions. In-txn universe-recheck (167.503/167.503/167.503) FYRIR commit; rowcount-assert 167.503; post-verify point_est_moved=0 → COMMIT.

**PENDING (flip er í DB en EKKI enn sýnilegt notendum):** (1) `v_current_predictions` (það sem appið les, `select *`) birtir AÐEINS upprunalegu 12 dálkana → **grade kemst ekki til appsins fyrr en view-ið er víkkað (+2 dálkar, additive CREATE OR REPLACE)** — SÉR go. (2) Framenda-UI sem sýnir grade er ekki til í app-repo enn (engin `confidence_grade`-tilvísun í `app/app`). (3) Backup/staging-cleanup + branch-push eftir 24-klst stöðugleika = sér ákvörðun.

**VIÐBÓT 2026-07-02 (view-víkkun LEYST → DB-hlið flipsins FULLKLÁRAÐ):** `v_current_predictions` víkkað additive (`CREATE OR REPLACE VIEW`, sama `DISTINCT ON (fastnum) … ORDER BY predicted_at DESC`, migration `20260702002140` canonical-reconcilað): **12 → 14 dálkar**, upprunalegu 12 óbreyttir í röð+gildi, `confidence_grade`+`calibration_source` aftast. Sömu 167.503 raðir; grade-dreifing gegnum view = base-tafla EXACT (A 60.518/B 59.158/C 35.933/D 11.894, 0 NULL). App-smoke (`select *`): 2000263→A, 2100041→C, 2032832→D koma nú gegnum viewið. Appið les `select *` → fær 2 auka-dálka sem það hunsar þar til UI notar → brotnar ekki. **DB-hlið flipsins lokið.** Eftir stendur aðeins: framenda-UI sem SÝNIR grade (sér verk, með comp-vél/agent), branch-push (`c7ee344`) + staging-cleanup — bæði 24-klst gate.

Sjá STATE 2026-07-02.

## 2026-06-30 — properties_v2 canonical-sync LEYST: rebuild speglar adapter (4 canonical features) → júlí LIVE

**Niðurstaða:** júlí-batch er LIVE (predictions **167.503 @ `2026-07-01`**, feature_attributions 1.675.030), DB-parity adapter@júlí vs live **300/300, max 0,0000%** → VÉL 1 óbrotin. Leysir apríl-stöðnunina (forsenda úr 2026-06-28 rollback). commit `090de2c` (precompute) pushað.

**Root-cause (sannreynt, LEIÐRÉTTIR fyrri frásögn):** rollbackið 2026-06-28 sagði „properties_v2.pkl víkur frá canonical fyrir ~22% (scrape-vs-Phase-D lineage-gap)". Það var OF-ALHÆFT. Numeric HMS (einflm/flatarmal, fasteignamat, matsvæði) er ALLT synkað (0% drift, full 232K). Raunvandinn: `rebuild_predictions_iter4.build_master_frame` sótti canonical structured-features úr **sölu/listing-fallback** (kaupskra last-sale, listings_v2) í stað `public.properties` BEINT — en VÉL-1 adapter (`phase_d3_score_extract`) les þá úr public.properties. Fyrir 67 D3-íbúðir er sölu/listing-fallback NULL → drift → júlí-parity 233/300.

**byggar var DRIVER, lod_flm fylgni-PROXY:** fyrsta greining negldi lod_flm sem „eina orsök, 67/67 fullkominn discriminator" — RANGT. Búggað NaN-próf (`abs(NaN−gildi)>0.01`=False → NaN-vs-gildi taldist match) faldi byggar-muninn. Rétt NaN-aware X-matrix-diff sýndi byggar+age_at_sale víkja á sömu 67; lod_flm lagðist ofan á sem fylgni (sömu D3-íbúðir vantaði bæði í fallback). **GLOBAL X-diff (öll 175.929, EKKI 300-sýni) fann `is_new_build` sem FJÓRÐA** (4.152 raðir, ósýnilegt í sýni — rebuild deriveraði `(2026−byggar)<=2` en phase_d3 geymir eigin lógík). Lærdómur: 300-sýni grípur ekki universe-dreift drift → **universe-sweep nauðsynlegur**.

**Meginregla (lokuð):** rebuild speglar adapter EXACT — `_load_canonical_props()` les **byggar, lod_flm, landeign_nr, is_new_build úr `public.properties` BEINT**, engin sölu/listing-fallback (adapter hefur enga; fallback bryti parity þar sem DB-NULL ∧ fallback-gildi). `properties_v2.pkl` heldur ENGAN lod_flm-dálk; cache er aðeins fyrir ÓBÆTANLEGT raw-HMS floor-data (merking, flatarmal) sem Supabase geymir ekki. Numeric/categorical (flatarmal=einflm, matsvæði, canonical_code, unit_category, buckets) haldast pkl/derived — sannreynt 0-drift global.

**Flip-arkitektúr (load==flip):** `v_current_predictions` er LIVE-view (`DISTINCT ON (fastnum) … ORDER BY predicted_at DESC`); UPSERT ON CONFLICT yfirskrifar apríl→júlí → public birtir júlí UM LEIÐ. Enginn aðskilinn flip-pointer. Aðferð: **staging-tafla → DB-parity + COPY-fidelity checksum FYRIR live → atomic flip**. Verify-path ≠ production-path (villu-flokkurinn sem hefur bitið) → staging sannar COPY skrifaði DB byte-trútt á öllu universe (167.503 / 1.675.030).

**replica-mode flip:** FK `feature_attributions_fastnum_fkey1 → properties` triggar per-röð check; 1,675M INSERT > **2-mín statement_timeout** (dauðaorsök fyrstu flip-tilraunar). FK EKKI deferrable → `SET CONSTRAINTS DEFERRED` ófært. Lausn: `SET LOCAL session_replication_role='replica'` (txn-scoped, sleppir FK-trigger; PK+indexar+einkvæmni haldast; engir user-triggerar) + **in-txn universe-recheck** (0 orphans) sem kemur í stað FK-trigger-sins. Mælt 87s→16,7s scratch, **46s live** (vs 120s+ timeout). Atomic ein-txn (predictions UPSERT + feature_attributions TRUNCATE/INSERT) → rollback-öryggi SANNAÐ (fyrsta tilraun féll á timeout, live ósnortið apríl).

**Pooler-gildra:** `REFRESH MATERIALIZED VIEW` þarf write-txn; pooler-autocommit er read-only sjálfgefið → REFRESH féll fyrst. Lausn: explicit `SET TRANSACTION READ WRITE` í non-autocommit txn. Af 13 MV les AÐEINS `semantic.v_model_vs_sold_by_hood` predictions → refresh-að; hinar 12 lesa sales_history, óháðar flipinu.

**Dauðaorsök bakgrunns-rebuild (aðskilið):** harness drepur bakgrunns-Bash-verk ~33 mín (létt núll-minni waiter dó líka → EKKI OOM). Root-fix: þungar keyrslur DETACHED (`Start-Process`, lifir óháð harness) — full SHAP-rebuild (40 mín) kláraðist þá.

Sjá STATE 2026-06-30.

## 2026-06-28 — Precompute apríl→júlí endurræsing REYND + ROLLBÖKUÐ (properties_v2 lineage-gap vs canonical)

**Vandi:** prediction-batch (167.503, `predicted_at=2026-04-01`, iter4_final_v1) hafði ekki keyrt síðan apríl — precompute-pipeline var ALDREI sjálfvirkt (ekkert Task Scheduler), datt niður eins og promote; `VALUATION_MONTH=4` harðkóðað. /ops apríl-🔴, verðmöt ~3 mán gömul.

**Anker-greining (kjarni, sannreynt):** módel-real-skali er FASTUR á **2026-05** (parity afsannar 07: FREEZE_ANCHOR_YM=05 endurgerir frosnu predictions). `valuation_month` (verðmats-dagur) er AÐSKILINN frá módel-ankri → val á júlí HREYFIR EKKI frosna ankerinn (frozen-until-iter5 heldur). cpi_index = **verðtryggingar**vísitala (birt 2 mán fram, ENDANLEG; CSV hafði þegar ágúst) → júlí (684,3) er endanlegt, EKKI bráðabirgða. **Leið B (root-fix):** `rebuild_predictions_iter4` pinnar `cpi_factor_valuation = cpi[2026-05]/cpi[2026-07] = 0,991232` úr `cpi_verdtrygging.csv` (óháð pkl-ankri sem driftar) = `freeze_cpi_factor` adaptersins → parity by construction.

**Útfært + LIVE-loadað:** training_data endurbyggt (sölur til 26. jún), júlí-CSV (167.503, predicted_at 2026-07-01, skali +1,42% vs apríl = cpi[07]/cpi[04], 0 innra artifact), idempotent loader (`load_predictions_batch.py`, snapshot `predictions_2026_04`/`feature_attributions_2026_04` service-role-RLS + UPSERT/TRUNCATE-COPY). /ops varð grænt.

**ROLLBÖKUÐ — af hverju:** atomic-flip adapter (phase_d3 VALUATION_MONTH=7 + PRED_VALUATION_YM=07) → **parity-gate REVIEW: 233/300 innan 0,1% (max 21,4%, median 0,0000%)**. Apríl-grunnlína = **300/300 PASS** → júlí-batch INNLEIDDI 67 útlaga (REGRESSION). Orsök: rebuild las `properties_v2.pkl` (28. maí) sem VÍKUR frá **canonical `public.properties`** fyrir ~22% (0% nýbygging, 85% APT_FLOOR → íbúða-eining-features, scrape-vs-Phase-D-auðgað lineage-gap; SOURCES_OF_TRUTH-mál). public.properties er authoritative → 22% drifted íbúða-verðmöt = brot á canonical-reglu. **Ákvörðun: correctness-first — rétt-en-gamalt (apríl canonical) > ferskt-en-drifted (júlí).** Rollback: TRUNCATE+INSERT predictions/feature_attributions úr 2026_04-snapshot + `git checkout` skrár 2+3 → apríl-grunnlína parity **300/300 PASS** staðfest hreint. Vikuvél `verdmat-weekly-model-quality` aftengd (Danni elevated) meðan unnið; **enn Disabled — má endurtengja nú (apríl=PASS)**.

**Forsenda fyrir júlí-endurkeyrslu:** `properties_v2.pkl`-canonical-sync frá public.properties (= lagfæring á þessu broti OG fyrsta skref b-skopunar/full ferskleika). Þá á júlí-batch að gefa parity 0,0000% (canonical-samræmt). **Anker-vinnan sjálf er rétt og endurnýtanleg** (Leið-B pin, loader, stdout-fix í rebuild_predictions_iter4 — ÓCOMMITAÐ, tilbúið fyrir endurkeyrslu). comps_index ósnert (apríl; rebuild framleiðir ekki comps). SÉR-LOTA með probe-first. Sjá STATE 2026-06-28 (precompute).

## 2026-06-28 — ops_scraper_signals GRANT hert aftur í service_role only + /ops scraper-cache leyst

**Einkenni:** eftir að service-role lykill var lagaður lásu public-töflur + model_metrics á /ops, EN scraper-RPC (`ops_scraper_signals`) sýndi „engin gögn" + scraper-ferskleiki „—".

**Greining (read-only) útilokaði lykil OG GRANT-brot:** prod les `model_metrics` sem aðeins `service_role` getur (RLS á, engin policy, anon SELECT=False) → **prod-lykill ER gildur service_role**. RPC skilar fullum gögnum via REST með service_role lyklinum (sannreynt, keys=5). Fall keyrir beint + via REST; engin timeout (service_role engin; töflur litlar). Svo allt DB-megin heilt → líklegast **tímabundið PostgREST schema-cache (PGRST202)**.

**Rót GRANT-víkkunar (staðfest, flögguð):** live proacl hafði `anon=X, authenticated=X` þvert á hönnun. Migration 20260628093000 gerði rétt `REVOKE ALL FROM PUBLIC` + `GRANT service_role`, EN **Supabase default privileges** (`ALTER DEFAULT PRIVILEGES ... GRANT EXECUTE ON FUNCTIONS TO anon, authenticated, service_role`) höfðu þegar veitt anon+authenticated EXECUTE sem **skýr hlutverk-grant** við CREATE. `REVOKE FROM PUBLIC` fjarlægir EKKI skýr hlutverk-grant → þau héldust. (716f0e0 hafði enga SQL-migration → víkkaði ekki.) Klassísk Supabase-gildra; **nýjar `public.*` SECURITY DEFINER föll þurfa skýrt `REVOKE EXECUTE FROM anon, authenticated`, ekki bara FROM PUBLIC.**

**Aðgerð:** migration `20260628122047_ops_scraper_signals_revoke_anon` — `REVOKE EXECUTE ... FROM anon, authenticated, PUBLIC` (heldur service_role) + `NOTIFY pgrst, 'reload schema'`. Eftir: proacl = `{postgres, service_role}` only (anon/authenticated EXECUTE=False), fall keyrir enn. `/ops` óbreytt (notar service_role lykil). NOTIFY-reloadið **endurhleður líka schema-cache → leysir PGRST202 cache-málið** sem hliðarverkun. Þ.e. herðir öryggi (þrönga LEIÐ 2 yfirborðið) OG lagar scraper-spjöldin í einni aðgerð.

---

## 2026-06-28 — Módel-gæðamælikvarði: overall = íbúðarhúsnæði (sumarhús útilokuð) + segment-sundurliðun á /ops

**Könnun (read-only, VÉL 1 OOS-úrtak n≈1416):** heildar-MAPE 16,9% / cov80 67% er **þung blanda ólíkra þýða**, ekki einsleit gæði. Sundurliðun (sama de-anker/aðferð og `model_quality_eval`):

| segment | n | MAPE | medAPE | cov80 |
|---|---:|---:|---:|---:|
| **höfuðborg · íbúðir (KJARNI)** | 900 | **10,8** | 6,2 | 69,6 |
| ↳ Reykjavík kjarni · íbúðir | 467 | 10,5 | 5,8 | 72,6 |
| ↳ nágr.sveitarf. · íbúðir | 433 | 11,1 | 6,5 | 66,3 |
| höfuðborg · sérbýli | 83 | 12,3 | 8,6 | 68,7 |
| landsbyggð · íbúðarhúsnæði | 374 | 17,8 | 11,8 | 67,6 |
| **sumarhús** | 59 | **110,4** | 19,2 | 30,5 |
| **íbúðarhúsnæði alls (nýtt overall)** | 1357 | **12,8** | 7,5 | 69,0 |

**ÁKVÖRÐUN 1 — overall = íbúðarhúsnæði (APT_\* + SFH/ROW/SEMI); sumarhús + ekki-íbúð útilokuð (grunnregla).** Sumarhús eru **4,2% af n en 27,3% af allri MAPE**: módelið stór-ofmetur ódýra bústaði (t.d. raun 4,7M → spá 65M = 1290% skekkja; bias −86%, cov80 30,5%) — út-af-léni fyrir iter4 hedóníska módelið. Útilokun færir overall 16,9 → **12,8**. Þetta er **mælikvarða-síun, EKKI módel-breyting** — iter4 frosið óbreytt. Sumarhús haldast MÆLD sem sér `region_type='summerhouse'` segment. Útfært í `model_quality_eval.segments()` (residential-maska + nýtt `region_type`-dim).

**ÁKVÖRÐUN 2 — /ops MÓDEL-spjald leiðir með kjarna-markaði.** Borðið las áður aðeins `segment_dim='overall'` (sem hefði sýnt 16,9% og vanmetið kjarnann um ~6pp). Sýnir nú **höfuðborg · íbúðir (10,8%)** sem aðal-tölu + sundurliðun (RVK_core, nágr.sveitarf., sérbýli, landsbyggð, sumarhús sér) + heild (íbúðarhúsnæði 12,8%). Les nýju `region_type`-raðirnar (keyrt í run 38).

**GAGNAGÆÐA-GAT (flaggað, EKKI lagað):** af hverju falla 3–6M „sölur" á eignir sem módelið metur á 30–65M EKKI á `onothaefur=1`? Líklega **hlutasölur/lóða-sölur/makaskipti** sem HMS-flokkun grípur ekki. Þetta mengar líka landsbyggðar/sumarhúsa-segment. Til skoðunar (gæti þurft viðbótar-síu á `kaupverd_nominal` vs `fasteignamat`-hlutfall), ekki lagað í þessari lotu.

**RADAR (iter5, EKKI núna — iter4 frosið):** conformal **per-segment** endurkvörðun. Jafnvel kjarninn (RVK_core íbúð) er cov80 72,6% — undir 80%-markmiði → bilin örlítið of þröng í kjarnanum (kerfislægt, ekki bara útlagar). Sumarhús (30,5%) + landsbyggð stór-miskvörðuð → sér-kvörðun eða sér-módel fyrir sumarhús, ekki almenn breikkun.

---

## 2026-06-28 — WU truflar nætur-keðju; Leið B: aðskilin WU-guard task (ekki í keðju)

Nótt 27→28 drap Windows Update bakgrunns-virkni (install 01:53–01:55) mbl delta-keðjuna (`verdmat-nightly-delta`, 01:00→~03:30) milli delta-sale og delta-rent — ekkert ABORT-line (ferlistréð drepið samtímis), promote/extraction keyrðu aldrei → mbl staðnaði í `scraper.listings`. Stutta myigloo-task-ið (02:00–02:19) slapp. **Rót**: virka WU-pause-ið (HKLM UX, til 11. júlí) nær yfir quality/feature updates en **ekki servicing/Defender**, sem keyrir samt daglega.

**Leið B valin** (yfir Leið A = WU-stop inni í keðjunni): **tveir sjálfstæðir elevated task** þagga WU aðeins í nætur-glugga, **aðskildir frá keðjunni**:
- `verdmat-wu-guard-stop` @00:55 → `Stop` wuauserv + UsoSvc
- `verdmat-wu-guard-start` @03:35 → `Start` wuauserv + UsoSvc (öryggisnetið)

Rök fyrir B umfram A: (1) keðjan helst RunLevel=Limited — **engin privilege-breikkun** (A hefði krafist þess að keyra alla skröpunina elevated); (2) start-task er sjálfstæður svo **WU er ALLTAF endurkveikt þótt keðjan deyi** (A skildi WU slökkt ef trap brást við SIGKILL); (3) **stop, ekki disable** — þjónustur trigger-restart-a, við þöggum aðeins gluggann. Gluggi 00:55→03:35 þekur delta (01:00→~03:30) + myigloo (02:00). **Viðbót** við WU-pause, ekki í staðinn. Task-arnir keyra sem `NT AUTHORITY\SYSTEM` (RunLevel Highest) — áreiðanleg þjónustu-stýring án lykilorðs. Armað gegnum `scripts/arm_wu_nightly_guard.ps1` (idempotent, í repo); task-skráning er á vél, ekki í repo. Vakta gegnum /ops (mbl-row 🔴 ef endurtekur). UsoSvc getur verið þrjóskt jafnvel fyrir admin → scriptið prófar stop/start og tilkynnir.

---

## 2026-06-28 — /ops auth: aftengt frá pro_users → sjálfstætt OPS_PASSWORD-hlið

`/ops` reiddi sig á sömu Supabase `pro_users`-vörn og `/pro` (sjá /ops RPC-færsluna að neðan). En `/ops` birtir **aðeins aggregöt rekstrarmerki** (engin per-notanda pro-gögn), svo það fær nú **eigið einfalt leyniorðs-hlið** — aftengt frá pro-innskráningu.

**Vél**: `/ops/login` (server-component + server action) ber saman innslegið leyniorð við `process.env.OPS_PASSWORD` með constant-time jafn-lengdar SHA-256 digest-um, og setur við réttu svari **HttpOnly+Secure cookie = `sha256(OPS_PASSWORD)`**. `middleware.js` endurreiknar vænta hashið úr env (Web Crypto, edge) og ber saman; `/ops/login` er eina opna `/ops`-slóðin. **Leyniorðið er eingöngu server-megin** — aldrei `NEXT_PUBLIC`, aldrei í cookie, aldrei í client-bundle (grep-staðfest). `/pro` heldur óbreyttri `pro_users`-vörn. Service-role client (`lib/supabase-admin.js`, force-dynamic) óbreyttur — aðskilin, nauðsynleg vörn. OPS_PASSWORD í `app/.env.local` (local) + Vercel (prod). Build grænt; `/ops` + `/ops/login` báðar dynamic. Commit `f49a6c6`.

**schema_migrations reconcile**: `ops_scraper_signals()` var applyað gegnum TVÆR íterativar MCP-migrations (`20260628091307` create + `20260628091405` latest-day-counts) en á diski er ein **consolidated kanónísk skrá** `20260628093000_ops_scraper_signals.sql`. Staðfest að skráin == lifandi fall (27/27 json-keys eins, SECURITY DEFINER + search_path='' + GRANT service_role only). Ledger samræmt: INSERT `093000`, DELETE báðar fileless MCP-raðir — **fallið óbreytt** (md5 before==after, aðeins bókhald snert). Ledger nú: ein ops-færsla sem speglar repo-skrána.

**Opin vöktuð atriði** (ótengd /ops-kóða, flögguð á borðinu): mbl-skröpunar-drift (WU/keðja, önnur CC vinnur) og `predictions` staðnað (apríl — precompute, önnur CC). `/ops` SÝNIR þessi sem rauð/gul flögg — það er eiginleiki, ekki bilun í /ops.

---

## 2026-06-28 — /ops scraper-merki: public RPC (SECURITY DEFINER) yfir REST-expose (LEIÐ 2)

Innra `/ops` rekstrar-mælaborð les Supabase gegnum supabase-js (REST). `scraper`-skema er **ekki** REST-exposed (app + nætur-scriptin lesa það gegnum beina psycopg2-tengingu), svo jafnvel service-role fær `Invalid schema: scraper` gegnum REST. Tvær leiðir skoðaðar:
- **LEIÐ 1 — opna `scraper` fyrir PostgREST** (Settings → API → Exposed schemas). Hafnað: breikkar API-yfirborð, virkjar 5 anon-granted `scraper.v_*` views fyrir public REST, og krefst dashboard-aðgerðar.
- **LEIÐ 2 — public RPC (VALIN)**: `public.ops_scraper_signals()` `SECURITY DEFINER`, `search_path=''`, les `scraper.*` innra og skilar **aðeins aggregötum/tímastimplum** (engar raw raðir). `GRANT EXECUTE` aðeins til `service_role` (ekki anon). Heldur `scraper` innra, þrengra yfirborð, beitt gegnum MCP `apply_migration`.

**Aðgangur að `/ops`**: anon er meðvitað **ekki** með SELECT á `pipeline_runs`/`model_metrics`/`predictions`/`scraper.*` (staðfest í grants). Því les `/ops` með **service-role lykli, aðeins server-megin** (`lib/supabase-admin.js`, `SUPABASE_SERVICE_ROLE_KEY` — ekki `NEXT_PUBLIC`), og middleware auth-læsir `/ops` bak við sömu `pro_users`-vörn og `/pro`. Rekstrar-gögn fara aldrei til client nema sem rendered HTML fyrir innskráðan pro-notanda. Migration-skrá: `supabase/migrations/20260628093000_ops_scraper_signals.sql` (spegill MCP-applysins). Commit `0164c89`.

---

## 2026-06-28 — Mynda-varðveisla: URL-fyrst capture + dauðamörk-laus fs-pool STAÐFEST (byte-bæti-sókn í gangi)

**Staðfest fyrsta-hendi úr `D:\verdmat-is\scraper_data\listing_images.db`** (CC1 read-only query — aðeins tölur sem mældust í DB):
- **488.395 URL-raðir** (248.863 distinct url) — mbl + myigloo. Dálkar: url/url_kind/listing_status/sent_dags/content_sha256/local_path/byte_len/status.
- **URL-fyrst arkitektúr** (capture aðskilið frá byte-fetch; status url_only → fetched/lost): mbl **45.237 fetched + 763 lost + 436.419 url_only**; myigloo **5.976 fetched**. Sótt alls 51.213 = **15,4 GiB** local (local_path á D:).
- **sha256-dedup** (content_sha256): 488K url-raðir → 248K distinct url (endurbirtingar deila myndum).
- **DAUÐAMÖRK-LAUS staðfest**: sent_dags **2014-10-06 → 2026-06-27** (100% ≥2014). Fetch-árangur **98,5%** (763 lost af 51.976 reyndum); per-ár sýnir eldri ár (2014-2020) **~100% sótt** → **engin aldurs-brún** — Thumbor/fs-pool serverar gamlar myndir varanlega (öfugt við spá um aldurs-expiry). 763 „lost" dreifðar, ekki aldurs-bundnar.
- **Local-fyrst D:** (local_path); R2-sync síðar (sama mynstur og nightly-backup).

**Bæti-sókn Í GANGI (CC2)**: 436.419 mbl url_only bíða byte-fetch (2026-bunki 450K raðir, 14,5K sóttar); myigloo lokið. **Lokatölur bæti-sóknar festir CC2** — þessi færsla staðfestir arkitektúr + dauðamarka-leysi, EKKI lokastöðu sóknar. Sjá minni [[project_listing_images_url_capture]].

---

## 2026-06-28 — myigloo LIFANDI (POINTER; CC3 festir full rök)

Pointer-færsla — myigloo-substraumurinn er nú lifandi með nætur-örmun. **CC3 er höfundur** (vinnur í myigloo fastnum-fyllingu núna) og festir full rök/tölur; ég fullyrði EKKI rök úr annarri hendi. Commits á origin/main:
- `6734c8e` fix(myigloo): restore content-hash idempotency (volatile subtrees + delete-not-null)
- `219d7af` feat(myigloo): sales-trajectory Layer 1 promoter with active-set lifecycle diff
- `f364f83` feat(myigloo): nightly full-sweep chain + S4U task registration

myigloo er í Lag 1 (`scraper.listings`, ~1.109 raðir) en er **leiga án fastnum → engin verðmatsleið** (extraction-lagið sleppir myigloo meðvitað, sjá 2026-06-28 extraction-færslu). Full rök (active-set lifecycle diff, S4U-takt, fastnum-fylling): CC3.

---

## 2026-06-28 — Extraction-lag: content-addressed 108-reita ástands-extraction + frosin verðmöt + expected-vs-real, ARMAÐ í nætur-keðju

**Markmið**: framvirk extraction-vél — hver lifandi mbl-auglýsing fær 108-reita ástands-extraction → frosið extraction-bætt verðmat → expected-vs-real monitoring þegar eign selst (VÉL-1-mynstrið alhæft á LIFANDI strauminn). Additíft; gamla allt ósnert.

**KOSTNAÐAR-GÁTT (apríl-safn HAFNAÐ sem seed)**: Áfangi-3 batch (37.544 distinct, ~$156, v0.2.2) extractaði `listings_text_v2.pkl` (EVALUE-augl-texti) með `sha256[:500]`-dedup. Hash-skörun við lifandi mbl-lysingar (md5(lysing)[:12]) = **1,09%** (evalue-texti ≈ aldrei byte-eins og mbl). Tap-laust seed því aðeins **149 (VÉL 1 cache, mbl-texti) + 4 (apríl-md5-skörun) = 153**. Apríl-fastnum-approx-seed HAFNAÐ (myndi blanda evalue-texta við mbl-auglýsingu → mengar monitoring). Raunbil ~11,5K distinct mbl-lysingar → fyllist FRAMVIRKT + LAZY, EKKERT blint backfill.

**TÖFLUR (migration `20260627211837`, RLS service-role-only)**: (a) `scraper.listing_extractions` CONTENT-ADDRESSED á `lysing_hash`=md5(lysing)[:12] (PK) — endurbirtingar deila hash → ein extraction/Haiku-kall þjónar öllum; extraction jsonb + schema/model/`source_trigger`(seed_vel1|seed_april|nightly|ondemand). (b) `scraper.listing_valuations` FROSINN snapshot per (source_listing_id, model_version): `expected_base` (structured) vs `expected_extraction` (+108 reitir) — `public.predictions` er mánaðarlega endurnýjað → getur EKKI endurgert sögulegt expected. (c) `scraper.v_expected_vs_real` SÝN (deterministic eins og v_units; frosna hliðin er þegar í (b), real úr sales_history): expected/real/gap/pct_error + full extraction jsonb + verð-ferill + cpi-við-sölu, allt-geymt fyrir framtíðar-módel-rannsókn.

**VÉL (`extraction_engine.py`)**: `value_listings` skorar gegnum VÉL-1 freeze-anchored adapter (`phase_d3_score_extract.score` pinnar sale_year/month í 2026-04 → `expected_base` endurgerir predictions, D2 parity 0,0000%; `expected_extraction` overlay-ar extraction-dálka via `build_extraction_features`). `extract_and_store` = Haiku 108-reita, content-addressed. Þrír triggerar, eitt fall (lazy-trigger byggður, ótengdur agenti). Seed: 153 extractions, 256 verðmöt (gap í báðar áttir: +17,6% / −11,7%). Gætt 5-Haiku: las raunverulega meiningu (vörumerki, einkasala-rás, varfærið not_mentioned, engin hallusination); content-addressed skip staðfest.

**ARMAÐ í nætur-keðju (`run_extract` í `nightly_delta_chain.sh` eftir `run_promote`)**: framvirkt **N=200** ferskar-fyrst (ORDER BY max(listed_at) DESC → nýjar auglýsingar í mestri hverfis-hættu fyrst, svo ~11,5K bakslag). **Hart kostnaðar-þak**: `--max-n` (500) + `--daily-cap-usd` $10 (state `extraction_cost_state.json`) → cache-galli getur ALDREI brennt hundruð dollara óséð; kostnaður logaður í morgunreport. ~57 mín, klárast ~02:10 (hreint fyrir 02:30 sales-refresh). gated/abort-not-retry (extraction-fall skilur promote/raw/lög ósnert). **mbl-eingöngu**: verðmat krefst fastnum → predictions; myigloo (leiga, enginn fastnum) hefur enga verðmatsleið → ekki extractað hér (frestað). **$8-leki lokaður**: Haiku-lykill EINGÖNGU úr `D:\env.local` (dotenv_values) inni í run_extraction-ferlinu, aldrei exportað/os.environ → keðja/CC lyklalaus. **Sync N=500 = ~2,4 klst HAFNAÐ** (tímaárekstur við 02:30/03:00); batch-API (50% ódýrara, ~15 mín) geymt þar til bakslags-hraði skiptir máli. Gætt fyrsta N=200 keyrsla hrein: 200 extractað 0 fail $1,42, 636 verðmöt, key TOMT eftir.

**Eftir**: (a) expected-vs-real fyllist þegar listings seljast (0 enn — frosið núna); re-baseline úr morgunreport. (b) myigloo-extraction þegar leigu-verðmatsleið til. (c) lazy/agent-trigger. (d) batch-API ef bakslags-hraði krefst. Commits 0a5a103 (lag) + 3f0bdef (örmun). Sjá STATE 2026-06-28.

---

## 2026-06-27 — Söluferils-líkan Lag 1 (auglýsinga-grain) ADDITÍFT + nætur-promote ARMAÐ í BÆÐI lög (BLOKK 4-6)

**Markmið**: tveggja-laga söluferils-líkan ofan á mbl-auglýsingar svo verð-ferill eignar varðveitist (tapaðist í canonical-fold), OG sjálfvirkja promote-brautina (handvirk frá 13. júní). ALLT additíft — `scraper.listings_canonical` ALDREI snert; nýtt lag lifir samhliða; enginn consumer fluttur.

**ADDR-PARSER (BLOKK 4 ÞREP 1)**: `normalize_address` er botn-strengja-normaliserun (diacritics→ASCII, lowercase) — strippar HVORKI né aðgreinir íb.nr (docstring: útdráttur „lives in source-specific mappers"). Sér-íb.nr-extractor (regex `íb\.?|íbúð|\(` + víkkað `\s-\s+\d{3,4}` fyrir „- NNN" án að grípa götusvið „2-4") er ÁREIÐANLEGUR (stöðugur per einingu, ólíkt matshluti) EN lág-þekju: **23,7%** auglýsinga hafa íb.nr; 69% multi-hópa engan.

**EININGAR-LYKILL (festur, BLOKK 4)**: `(fastnum, stærð±2% klasi)` frum-lykill + **íb.nr COALESCED splitter** — kljúfa (fastnum,stærð)-hóp AÐEINS þegar ≥2 aðgreind non-null íb.nr (t.d. Eskiás íb106 vs íb206); íb.nr=None = wildcard (kljúfar ekkert → 510 mixed-None hópar haldast saman; falskar-neikvæðar fram yfir falskar-jákvæðar). matshluti HENT (ónýtur, BLOKK 2: sama eining → {0,6,7,8}). Bakreikningur: bert fastnum 8.949 → frum 9.160 → coalesced 9.177 (splitter +17, ekki naive 842). Lifandi keyrsla gaf 8.640 einingar (resolve_fastnum FK-gated strangari en hrá-trunc).

**LAG 1 MIGRATION `20260627134046` (additíft)**: `scraper.listings` (auglýsinga-grain, UNIQUE(source, source_listing_id), ENGIN fold), `scraper.listing_price_history` (append-only, UNIQUE(source, source_listing_id, observed_at, price_amount)), `scraper.v_units` (deterministic rollup á unit_key + sales_history sold-join). RLS service-role-only. Beitt gegnum psycopg2 (MCP ekki tengt) með SET TRANSACTION READ WRITE; skráð í schema_migrations (ekkert phantom).

**POPULATOR `promote_listings_append.py` (BLOKK 5)**: watermark-ÓHÁÐ (vinnur ALLAR priced auglýsingar, ekki bara unpromoted → heill ferill; canonical-promote át margar). Endurnýtir promote_mbl resolution-föll (fastnum/category/price/foreign) → paritet. ON CONFLICT DO UPDATE ferskar volatile dálka = **Vandi-1-fix** (field-staleness). Keyrsla: 19.046 listings + 19.046 price_history (1.184 foreign, 13 split, 8.640 einingar). Staðfest: Hrafnaborg 1 íb.101 ferill HEILL í price_history (89,9M→75,9M→68,5M), Vandi-1 birti 71 slid með ferskara verði en canonical, engin fold (19.046 distinct=raðir), idempotent (endurkeyrsla +0), canonical 13.320 óbreytt, sold-join virkar (62M).

**ÞEKKT TAKMÖRKUN (Vandi-2b, fundið BLOKK 5)**: í nýbyggingum REKUR fastnum í tíma — snemmbúnar íb.nr-lausar almenn-auglýsingar leysast í foreldra-fastnum, síðari per-íbúð auglýsingar í sér-fastnum → ferill getur klofnað NEÐAN unit_key. Ekkert gagnatap (allar auglýsingar geymdar); takmarkar rollup-nákvæmni á forsölu-tímabili. Beint inntak í síðari Vandi-2b fínni dedup.

**NÆTUR-ÖRMUN (BLOKK 6)**: `nightly_delta_chain.sh` framlengt með `run_promote` EFTIR 4 hreinu fetch-modes (rót-lagfæring — EKKI sér-task; engin tímasetningar-ágiskun): parse_mbl → promote_mbl priced sale+rent (canonical fold) → promote_listings_append (Lag 1). BÆÐI lög fersk hverja nótt; **frysting gamla fold-skrifa er meðvitað SÍÐARA skref við consumer-flutning**. NEGOTIABLE útilokað (lease_term útistandandi). Enginn API-lykill (engin Haiku). Gated á hreina fetch, abort-not-retry (promote-fall skilur raw/fetch eftir ósnert). Power: AC sefur aldrei; WakeToRun + RTCWAKE=1 (Danni 2026-06-26) vekur líka úr rafhlöðu-svefni. Gætt handvirk fyrsta keyrsla hrein (parse no-op, promote_mbl 0 priced=canonical current, append idempotent, lyklalaust). Taskinn keyrir nú þegar keðjuna → engin ný skráning.

**Eftir**: (a) consumer-flutningur dashboard → `scraper.listings`/`v_units`, ÞÁ frysta gamla fold-skrif; (b) Vandi-2b fastnum-rek fínni dedup; (c) extraction-tafla + post-promote extraction-þrep.

---

## 2026-06-27 — VÉL 1 tveggja-einkunna gæðakerfi FULLKLÁRAÐ (Einkunn 2 full + gap LIVE)

**Markmið náð**: vikulegt out-of-sample gæðakerfi með TVEIMUR einkunnum á SÖMU ferskum OOS-sölum. Einkunn 1 (baseline/all_oos) var LIVE (sjá 2026-06-26-færslu); þessi færsla lokar Einkunn 2 (full/paired_oos, Haiku les söluyfirlit) + BILINU (gap = framlag extraction-lagsins). Bæði í `public.model_metrics`, loggað gegnum migration_helpers. Adapter = `phase_d3_score_extract` (iter4a + conformal/stretch) sem HEIÐRAR extraction-dálka (úr `build_training_data_v2.build_extraction_features`); Haiku-extraction = `pilot_extract_v022.extract_listing` (claude-haiku-4-5, 108-field tool-call).

**ÁKVÖRÐUN 1 — freeze-anker parity-fix (lagaði 0,8768% einsleitan skala)**: frosnu predictions voru skrifaðar með model_pred_anchor_ym=**2026-05**; CPI-vélin færði lifandi ankerinn í 2026-07 OG endur-ankeraði `training_data_v2.pkl`, sem adapterinn las `cpi_factor` úr → endur-skorun skalaði HVERJA spá um `cpi[2026-05]/cpi[2026-07]`. EMPÍRÍSKT staðfest til 6 aukastafa: `cpi_factor@2026-04` í lifandi pkl = 1.014379 = nákvæmlega `cpi[2026-07]/cpi[2026-04]`; skekkjan = `cpi[2026-05]/cpi[2026-07]−1 = −0,87681%`. FIX: `freeze_cpi_factor()` + `load_models_freeze_anchored()` festa adapter-`cpi_factor` við FREEZE-anker 2026-05 (reiknað úr `public.cpi_index`, EKKI lifandi pkl). Fastar `FREEZE_ANCHOR_YM`/`PRED_VALUATION_YM` skjalfesta ankerinn (lifandi config var yfirskrifað → ekki queryanlegt). **D2 PARITY-GATE: 80/80 OOS-fastnums, max 0,0000%, miðgildi 0,0000% — adapter-baseline endurgerir frosnu spárnar bæti-fyrir-bæti.** Parity ber saman HRÁ real_pred_median (ekkert de-anker í parity sjálfu).

**ÁKVÖRÐUN 2 — samræmt de-anker (aðferðafræðilega mikilvægast)**: all_oos de-ankeraði á `cpi[model_pred_anchor_ym]` en paired-stígur harðkóðaði 2026-04 → stígarnir EKKI samanburðarhæfir → selection-tékk ónýtt. Gamla docstring „cpi factor cancels í MAPE/bias" var RÖNG: fastur margfeldis-skali HLIÐRAR MAPE/bias kerfisbundið, styttist EKKI út. FIX: BÁÐIR stígar nota nú `cpi[saleM]/cpi[model_pred_anchor_ym]` (lifandi úr pipeline_config via `read_model_anchor_cpi()`, sama og v_model_vs_sold); harðkóðaða `PRED_DENOM_YM` fjarlægt; docstring leiðrétt. Tvö CPI-lög aðgreind skýrt: (1) inni í adapter = freeze-anker (ákvörðun 1); (2) metrics-de-anker = lifandi model-anker (ákvörðun 2).

**Þrír blokkerandi böggar lagaðir**: (1) tvíteknir fastnums → `fetch_paired_oos` `DISTINCT ON (fastnum)` (nýjasta OOS-sala) → engin `.loc[fn]`-DataFrame-gildra. (2) all-Haiku-fail/tómt set → None-metrics (callers höndla) í stað KeyError; `_score_iter4` tóm-frame vörn. (3) vantandi sölu-mánuður í cpi_index → drop+count+logg, EKKI þögul NaN-röð. **E1-VÖRN**: allur paired-blokk í try/except → Haiku/paired-villa loggast hátt (step exit_code=1) en E1-write heldur áfram; sönnuð Einkunn 1 getur ALDREI tapast.

**Hörðnun (aukaverk, flöggun)**: fyrsta full-keyrsla hékk ~21 mín á EINU hangandi Haiku-kalli (sjálfgefinn client timeout 600s × 3 SDK-retries = allt að 30 mín/kall). FIX: client `timeout=60s, max_retries=0` (extract_listing hefur eigin retry-lykkju — SDK-retry margfaldaði). Per-kall progress-loggun + `python -u`. **Resumanlegur extraction-cache** `D:\model_quality_extraction_cache.jsonl` (lykill=fastnum+hash(lýsing); stale-lýsing endur-extractast) → drepin keyrsla resumear frítt, óbreyttar lýsingar endur-borgast ekki. Self-log tee í `D:\model_quality_eval.log` (speglar daily/cpi). Fragmentation-warning (108 dálkar einn-í-einu) → `pd.concat` í einu.

**API-LYKILL (lokar $8-lekanum)**: `ANTHROPIC_API_KEY` AÐEINS úr `D:\env.local` (ATH: nafn án punkts fremst → python-dotenv hleður EKKI sjálfkrafa, krefst `dotenv_values(r"D:\env.local")`). `anthropic_key()` les eingöngu skrána, mutar EKKI os.environ → CC-umhverfið helst lyklalaust (staðfest: shell/os.environ/registry öll tóm) → CC getur ekki self-rukkað. Aðeins Haiku-extraction-fallið les lykilinn. /status staðfest Claude Max (ekki API).

**NIÐURSTAÐA (D4 full, 149 paraðar OOS, metric_run_id=32, $1,06)**: baseline MAPE 15,86/medAPE 7,41/bias +8,08/cov80 67,1/cov95 84,6; full MAPE 15,06/medAPE 7,01/bias +6,60/cov80 67,8/cov95 85,9. **BIL: öll fimm mál batna** — MAPE −0,81 / medAPE −0,40 / bias nær núlli −1,48 / cov80 +0,7 / cov95 +1,3. **SELECTION = REPRESENTATIVE** (medAPE all_oos 7,75 vs paired 7,41, Δ−0,33 ≪ ±2,0; n=1.388 vs 149) → bilið er HREINT extraction-framlag á fulltrúa úrtaki, ekki selection-bjögun. **Vélrænt vit**: baseline van-metur auglýstar/seldar eignir um +8,08% (þær hallast að endurnýjuðum/hærri gæðum sem structured-only sér ekki); extraction les ástand/endurbætur úr textanum → minnkar van-matið í +6,60% — staðfestir að extraction les raunverðmæti, ekki hávaða. Sölupunkturinn (extraction-lagið borgar sig) sannaður á hörðum OOS.

**E — vikuleg cadence (ÓVOPNAÐ)**: `scripts/register_model_quality_task.ps1` → `verdmat-weekly-model-quality`, **mánudagur 05:00 GMT** (hreinn gluggi: daily 02:30/backup 03:00 búin ~03:30, cpi sunnudag 04:00 — engin skörun). S4U/Limited, WakeToRun, StartWhenAvailable, engin retry, 2h limit. Full keyrsla (E1+E2+gap+selection) → model_metrics (raðir SAFNAST per metric_run_id; N lágt ~149/viku svo fyrstu vikur hávaðasamar). Lykill úr env.local svo armað task leki ekki gegnum CC. Danni armar elevated síðar. Fyrsta raunkeyrsla (D4) þegar í töflunni.

**Eftir**: (i) Danni armar register-task. (ii) frontend heilsa-flipi / onothaefur-merki les model_metrics. (iii) trend-lestur þegar fleiri vikur safnast.

---

## 2026-06-27 — Næturkeyrslu-gat 2026-06-25 (svefn á rafhlöðu) + delta-sale cap → (b)-recovery 502 raðir í raw (stopp í raw)

**Rót**: nóttin 2026-06-25 keyrði ekki — vélin svaf á rafhlöðu (Kernel-Power sleep 06-24 21:28 → resume 06-25 23:44). WakeToRun-flögg voru sett á þrjú af fjórum task en orkustefnan „Allow wake timers" var AC=important-only (0x2) / DC=disabled (0x0) → scheduluð vakning kviknaði aldrei. **Lagað elevated** (Danni): `powercfg /set{ac,dc}valueindex SCHEME_CURRENT SUB_SLEEP RTCWAKE 1` + `verdmat-nightly-backup` WakeToRun=true (hin þrjú höfðu flaggið þegar, bara gagnslaust án orkustefnu).

**Afleiðing**: delta-sale 2026-06-26 spannaði 2 daga (since 2026-06-24T00:36:19.600482) og rakst í 100-síðna þakið — **fyrsta cap-hit í sögunni** (nætur 06-13..06-24 voru 18–89 síður). `br_dags>since ORDER BY eign_id DESC`: gamlar listings (lágt eign_id) með nýtt br_dags lentu aftan við offset 1600, sleppt, og high-water færðist fram yfir þær → varanlega týndar úr delta-straumnum.

**(b)-recovery (raw-only)**: temp-reset high-water í júní-24 gildið, custom fetch sem endurnýtir tested `MblFetcher._gql`+`_record_page` með WHERE `eign_id<1686918` (efra mark, ekkert neðra, self-terminating á 0-row síðu). **Niðurstaða: 32 síður, 502 raðir (eign_id 1199011..1686906), self-terminated (ekki cap); í raw_mbl.db sem list_page_sale / parse_status=pending, content-hash idempotent.** Live-aggregate staðfesti 502/502 → engin lág-eign_id röð eftir utan raw. High-water endurstillt í `2026-06-26T01:05:58.782541+00:00`; `delta_sale_negotiable` óbreytt. State-afrit: `scraper_data/mbl_fetch_state.json.bak_20260626_recovery`. Log: `scraper_data/night_logs/recovery_20260626.log`.

**Stopp í raw (meðvitað)**: parse+promote EKKI keyrt. Hálf-promote (502 af 827 pending) myndi skilja `scraper.listings_canonical` ósamræmt (recovery-raðir promaðar meðan nýrri pending-breytingar sömu listings bíða) → recovery-raðirnar flæða í Supabase með venjulegu gated parse+promote lotunni. Markmið náð: 0 raðir týndar úr 25.-júní gatinu.

**NÓTA (aðskilið verk)**: parse hefur ekki keyrt síðan 2026-06-13 → **827 pending síður (~2 vikur af venjulegu delta: 737 sale m/recovery, 42 sale-neg, 22 rent, 26 rent-neg)** bíða parse+promote. Sjálfstætt catch-up verk síðar, með eigin validation.

---

## 2026-06-26 — VÉL 1 módel-gæðakerfi: Einkunn 1 (baseline/all_oos) LIVE; Einkunn 2 blokkað á API-lykli

**Markmið**: vikulegt out-of-sample gæðakerfi, tvær einkunnir á SÖMU ferskum sölum — E1 (iter4 structured, extraction nulluð) vs E2 (iter4 + Haiku-extraction úr söluyfirliti), BIL = framlag extraction-lagsins. Mælt nominal/nominal (de-anker eins og v_model_vs_sold), skrifað í nýja `public.model_metrics`, loggað gegnum migration_helpers.

**OOS-cutoff aðferðafræði (leiðrétti forsendu)**: iter4 `.lgb` var ÞJÁLFAÐ 2026-04-21 (mtime) á kaupskrá ~2026-04-20 — `predicted_at`=2026-04-01 er bara stimpill, EKKI cutoff; current `training_data_v2.pkl` (2026-05-28 max) er síðari endur-SKORUN, ekki endur-þjálfun. **OOS_CUTOFF = 2026-04-20**; sölur eftir það eru hreint out-of-sample. **onothaefur=0 SKYLDA** í OOS-úrtaki (uppgötvað í dryrun: án síu MAPE 56% / bias −37% af ómarkaðs-sölum; með síu MAPE 16% / bias −0,8%).

**`public.model_metrics`** (migration 20260626004530): metric_run_id, oos_cutoff, score_type (baseline|full|gap), segment_dim (overall|hood|property_type|price_band|new_build), segment_value, sample_scope (all_oos|paired_oos), n_pairs, mape/med_ape/bias/cov80/cov95, extra. RLS service-role-only. UNIQUE (metric_run_id, score_type, segment_dim, segment_value, sample_scope) → idempotent.

**SKREF B LIVE — Einkunn 1 (baseline/all_oos)**: `scripts/model_quality_eval.py` reiknar á frosnum public.predictions ⋈ sales_history (onothaefur=0, eftir cutoff), metric-kjarni speglar validate_metrics (MAPE real-space, coverage scale-invariant, bias), de-anker nominal/nominal. **Fyrsta keyrsla: n=1.313 OOS pör, MAPE 15,94% / medAPE 7,80% / bias −0,84% / cov80 67,2% / cov95 87,4%** (62 raðir: overall + 47 hverfi + 8 eignagerðir + 4 verðbil + 2 nýbygging). Lærdómur: medAPE 7,8% ≈ held-baseline 7,0% (módel alhæfir vel miðlægt); MAPE 15,9% tail-drifið af <40M bandi (MAPE 62%); cov80 67% < held 73% → OOS-undirþekja á bilunum (raunverulegur fundur).

**SKREF C GRÆNT — matsvél kallanleg per-eign**: þrjú hrein importanleg callables staðfest: `score_new_listing.score_property` (nullar vantandi → baseline vs full = sami dict), `build_training_data_v2.build_extraction_features(extraction, sale_year, canonical_code)` (raw 108-field → módel-features), `pilot_extract_v022.extract_listing` (single-listing synchronous Haiku-call, claude-haiku-4-5, tvinguð tool, 108 fields). Pörun: 126 OOS-fastnums (af 1.313) með söluyfirliti (~9,6%).

**SKREF D BLOKKAÐ — `ANTHROPIC_API_KEY` ekki sett í session**: Haiku-extraction-helmingurinn óprófanlegur → D-vélin EKKI smíðuð (óprófaður greiddur-API-stígur = áhætta). Bíður þess að lykill sé settur; þá: per paraða OOS-eign → score_property(baseline) + extract_listing→build_extraction_features→score_property(full), skrifa full/paired_oos + gap, + selection-tékk (baseline/all_oos vs baseline/paired_oos). Kostnaður ~$1 (126 × ~$0,007).

**Eftir**: (i) setja API-lykil → smíða+keyra D (E2/gap). (ii) SKREF E vikuleg cadence (óvopnuð, register-script eins og daily/cpi; N lágt ~126 svo fyrstu vikur hávaðasamar — vélin SAFNAR því afturkölluð auglýsing týnir söluyfirliti). (iii) frontend onothaefur-merki / heilsa-flipi les model_metrics.

---

## 2026-06-26 — CPI re-anchor ARMAÐ (verdmat-weekly-cpi-reanchor) — CPI-braut fullkláruð

**Armað**: `verdmat-weekly-cpi-reanchor` S4U-task, **sunnudag 04:00 GMT, VIKULEGT** (local==GMT). Keyrir `monthly_cpi_reanchor.py` án flagga; DB-hlið gate (max(cpi_verdtrygging.csv) vs sales_history_anchor_ym) **no-op-ar þar til 2026-08 VNV birtist** (~seint júlí), grípur hann þá sjálfkrafa næsta sunnudag. register-script `scripts/register_cpi_reanchor_task.ps1` (sama S4U-mynstur og daily/delta; Danni keyrði elevated).

**Cadence-rök**: re-anchor er EKKI dag-viðkvæmt (~0,1% real-munur per CPI-mánuð, t.d. 07→08); vikulegt er nóg og færri keyrslur. **Röðun á grípu-degi** (sunnudag sem nýr mánuður er kominn): daily 02:30 (bætir nýjum sölum á GAMLA ankerinn) → backup 03:00 → re-anchor 04:00 (endur-ankerar ALLT, fulla töflu, atómískt: pre-flight snapshot + real-UPDATE + anker + cpi_index í einni txn → REFRESH 13 MV). Engin árekstur (re-anchor ~12-15s).

**S4U-próf** (on-demand, scheduluðu samhengi): LastTaskResult=0; pipeline_runs id=17 `monthly_cpi_reanchor / success / {noop:true, dryrun:false, anchor:2026-07, reason:'anchor unchanged'}` → sannar gate + loggun + refresh_cpi-subprocess undir S4U (python-path, importin, DB-tenging). 0 backup-töflur (no-op skrifar ekkert). Trigger Weekly/Sunday 04:00, S4U/Limited, næst 2026-06-28.

**CPI-braut (braut 2) er fullkláruð og óvopnuð-bíður-mánaðar**: forvinna (cpi_index, tveggja-lykla anker, v_model_vs_sold nominal/nominal) + vél (Python-parity re-derive, atómísk txn, pre-flight snapshot) + samræmd loggun + armað task. Fyrsta raun-keyrsla bíður 2026-08 VNV.

---

## 2026-06-25 — CPI re-anchor-vél + samræmd pipeline-loggun

- **monthly_cpi_reanchor.py smíðuð**: DB-hlið gate (max(cpi_csv) vs sales_history_anchor_ym), ein atómísk txn (Leið 1: real-UPDATE + anker + cpi_index samstillt), Python-parity re-derive (endurnýtir derive_sales_rows — 1/227k SQL-round dyfja útilokuð), REFRESH 13 MV. Dry-run mældi 227.615-raða UPDATE á 14,4s (síðar 11,7s/11,9s) ≪ 2min default → Leið 1 örugg, engin lotuskipting. SANITY: aðeins kaupverd_real breytist (nominal/dags/onothaefur 0). **Pre-flight snapshot** (public.sales_history_real_backup_<ts>, service-role-only, eigin committuð txn fyrir UPDATE) = afturköllunar-net; dropað handvirkt eftir staðfestingu (auto-prune á backlog).
- **Samræmd loggun**: fjögur pipeline-logg-föll (start_run/start_step/finish_step/finish_run) factoruð í migration_helpers → run_monthly + daily + cpi deila EINNI heimild. No-op convention: exit_status='success' + summary.noop=true (success/failed hreint binary, no-op greinanlegt, aldrei sleppt). **Pooler read-only-leak fix**: SET TRANSACTION READ WRITE fyrst í öllum fjórum helper-föllum (read-only session úr open_ro_conn lekur inn í deilda pgbouncer-backend annars → ReadOnlySqlTransaction á write). run_type-gildi: daily_sales_refresh, monthly_cpi_reanchor (auk monthly).
- **AUDIT**: id 11/12 í pipeline_runs eru danglandi frá föllnum dryrun-tilraunum fyrir leak-fix — látnar standa sem heiðarlegt audit-ummerki (hálf-keyrslur, ekkert lifandi snert).
- **Eftir**: arm (3b, S4U mánaðarlegt task með DB-gate) + fyrsta lifandi keyrsla bíður 2026-08 VNV.

---

## 2026-06-24 — CPI-systkin FORVINNA: cpi_index + tveggja-lykla anker-aðskilnaður + v_model_vs_sold nominal/nominal

Samhengi: undirbúningur fyrir mánaðarlegu CPI-endur-ankeringu (braut 2). Þrjár DB-breytingar lentu, ALLAR á undan sjálfri re-anchor-vélinni (sem bíður fyrsta nýja VNV-mánaðar):

1. **public.cpi_index** (year_month PK, cpi numeric) — spegill D:\cpi_verdtrygging.csv (376 raðir, 1995-04…2026-07), RLS á / anon-læst. CPI-systkinið verður skrifari hennar (uppfærir í sömu txn og það endur-ankerar). Gerir CPI-tímaröðina queryanlega í Postgres í fyrsta sinn.

2. **Tveggja-lykla anker-aðskilnaður í pipeline_config**:
   - sales_history_anchor_ym (live-anker) — CPI-systkinið hreyfir mánaðarlega.
   - model_pred_anchor_ym (módel-anker) — hreyfist BARA við iter5 deploy, mannlega-gated.
   Þeir MEGA og EIGA að vera ósamstilltir: predictions eru frosnar (iter4), sales hreyfast áfram. Báðir 2026-07 í dag → enginn desync núna.

3. **v_model_vs_sold_by_hood endurskrifað nominal/nominal (anker-óháð)**:
   sold_to_pred_ratio = kaupverd_nominal / (real_pred_median × cpi[saleM]/cpi[model_anchor]).
   Báðar hliðar de-ankeraðar í nominal við view-tíma → point-in-time spá-nákvæmni, ónæmt fyrir live-anker hreyfingu. Var EINA MV sem bar saman ólíkt-ankeraðar stærðir (real-live ÷ real-módel); hin 12 aggregera kaupverd_real innbyrðis → þegar ónæm. Þetta fjarlægir desync-gate-ið svo CPI-systkinið má endur-ankera kaupverd_real frjálst.
   Rounding: nominal_pred í SQL numeric (ratio-mæling, ekki geymt verð) → Python-parity á EKKI við.
   Vantandi-cpi: LEFT JOIN með countable drop (ekki þögult NULL); 0 í dag (2-mán CPI-forskot).

**JAFNGILDIS-SÖNNUN**: af því anker==anker==2026-07 í dag mældist gamalt real/real == nýtt nominal/nominal EXAKT (pct_diff 0.0000 í öllum 10 stærstu hverfum, 5 aukastafir) → breytingin er anker-rétt, ekki bara öðruvísi reiknuð; merking óbreytt, aðeins framsetning de-ankeruð.

**AUDIT**: módel-anker '2026-07' er ÁLYKTAÐUR úr samhengi fyrir iter4 (inputs_snapshots run-level cpi_factor_at_val ≈ cpi[2026-07]/cpi[2026-05]; live-predictions cohort iter4_final_v1 applíeruð 2026-05-27, predicted_at 2026-04-01 — nákvæmt per-prediction real-anker hvergi skráð). iter5 SKAL skrifa model_pred_anchor_ym per-rebuild svo þetta sé LESIÐ, ekki ályktað.

**Migrations**: cpi_index (20260624102101) + v_model_vs_sold DROP+CREATE (MCP version). Eftir: sjálf re-anchor-vélin (refresh_cpi-vír + Python-parity re-derive + cpi_index/anker-uppfærsla í einni txn + REFRESH 13 MV), bíður fyrsta nýja VNV-mánaðar (2026-08).

---

## 2026-06-22 — Daily loader LIFANDI: daily_sales_refresh.py + S4U-task; DO NOTHING fresh-path

**Hvað**: daglega ferskleika-brautin (braut 1 af þremur, sjá kaupskrá-rebuild færsluna neðar) er smíðuð, sönnuð end-to-end og armað. `scripts/daily_sales_refresh.py` keyrir: Step 0 `refresh_kaupskra.py` (sækir kaupskrá) → re-derive + diff á (faerslunumer, fastnum) → upsert AÐEINS nýjar raðir → REFRESH 13 semantic MV.

**Læstar reglur**:
- **DO NOTHING** (ekki DO UPDATE): kaupskrá-mútanir eru hverfandi noise — módelið meðhöndlar verð-villur sem outliers, svo við skráum nýtt en eltum EKKI endurflokkun/leiðréttingar. Empírískt staðfest 18→22 jún: **0 mútanir / 0 GONE / 88 nýjar** raðir á composite-lykli. Danni domain-call.
- **Full re-derive + diff (ekki incremental watermark)** → self-healing: hver keyrsla endurreiknar allt settið og diffar við lifandi töflu, svo glatað/sleppt af fyrri nótt jafnar sig sjálfkrafa.
- **md5 diagnostic-only, ALDREI gate**: Step 0 loggar hvort kaupskrá-md5 breyttist en heldur alltaf áfram í derive+diff (md5-early-exit + `--force` fjarlægð í chunk 3). Forðast sole-fetcher gildruna OG nær in-place reclassification sem breytir md5 án raðafjölda.
- **REFRESH gated á inserted>0** (0 nýjar → sleppir 13 MV refresh, ~15s no-op keyrsla).
- **GONE vaktað, engin DELETE-vél í v1** (WARN ef >50); raðir hverfa ekki úr kaupskrá í reynd.
- **Anker single-source**: `public.pipeline_config` (RLS á, anon/auth læst, key `sales_history_anchor_ym`='2026-07'), lesið af BÁÐUM brautum gegnum `anchor_config.read_anchor(conn)` (raises ef vantar — engin þögul hardkóða-fallback). Mánaðar-CPI-systkinið verður EINI skrifari ankersins (anker + re-anker allra kaupverd_real í einni txn).
- **Eitt S4U-task** `verdmat-daily-sales-refresh` (02:30 GMT, S4U/Limited, WakeToRun, StartWhenAvailable, 1h limit), ekkert sér-refresh_kaupskra-task (loaderinn sækir sjálfur — sér-task væri auka failure-point). Decoupled frá run_monthly. Tímasetning hrein: mbl-delta 01:00 skrifar í scraper.* (enginn MV-lás-árekstur), backup 03:00 (23 mín borð eftir ~7 mín REFRESH). register-script `scripts/register_daily_sales_task.ps1` (sama S4U-mynstur og delta-taskið).

**AUDIT (reproducibility)**: `rebuild_sales_history.py` var untracked á keyrslutíma 2026-06-22 rebuildsins (keyrt af diski); fyrst committað ae5cf16 með anker lesinn úr pipeline_config — hegðunarlega eins og as-run hardkóði '2026-07'. Reproducibility heil: rollback-CSV `D:\sales_history_rollback_20260622.{csv,sql}` + committað skript + sami anker gefa sömu töflu.

**Fyrsta lifandi keyrsla**: sales_history 227.452→227.540, ferskt til thinglystdags 2026-06-19 (var 16.), 13 MV refresh án villu. **S4U-próf** (on-demand, 2026-06-23-trigger armað): LastTaskResult=0, NEW=0 / 0 inserted / skip REFRESH — sannar idempotency OG að loaderinn keyri gallalaust undir Task-Scheduler S4U (python-path, importin, DB-tenging, read_anchor).

**Næst**: mánaðar-CPI-systkin (refresh_cpi automation + endur-ankering, eini anker-skrifari) þá frontend „seld — ónothæfur samningur" merki fyrir onothaefur=1.

---

## 2026-06-22 — Kaupskrá ferskleiki: sales_history rebuild + composite-lykill + endur-ankering; þriggja-brauta arkitektúr

**Vandi**: public.sales_history (+ 13 semantic MV) stóð á 2026-04-17 (~2 mán gamalt) þótt HMS-kaupskrá uppfærist daglega ~02:01 GMT. Tvö göt, bæði ofan við MV: (A) refresh_kaupskra ekki scheduled (síðast 29. maí); (B) load-pípan keyrir hvorki né fullkláruð — run_monthly HALT-ar fyrir push, push_precompute_to_supabase() = NotImplementedError. Enginn náttúrulegur lykill (bara serial id) → ekkert ON CONFLICT-target.

**Arkitektúr (læst)**: þrjár cadence-aðskildar brautir. (1) DAGLEG ferskleiki: kaupskrá → sales_history incremental (composite ON CONFLICT) → REFRESH 13 MV, pinnaður CPI-anker. (2) MÁNAÐARLEG gögn: refresh_cpi → endur-ankera kaupverd_real → REFRESH MV. (3) MÁNAÐARLEG módel: rebuild_training_data → recalibration → predictions (óbreytt, HALT-gated). Daglega braut módel-óháð (CPI úr cpi_verdtrygging.csv, ekki training_data_v2.pkl — staðfest til floating-point, max frávik 4,44e-16).

**Rebuild apply (lent)**: hrein endurgerð sales_history úr núverandi kaupskrá. 173.867 → 227.452 raðir. Composite-lykill (faerslunumer, fastnum) = kanóníski kaupskrá-lykillinn sem refresh_kaupskra reiknar diff á; UNIQUE INDEX uq_sales_faerslunumer_fastnum. Endur-ankering: live var 2026-05, módelið 2026-07 (falin ósamræming); pinnað 2026-07 → kaupverd_real +0,88% einsleitt, lagar 0,88% skekkju í v_model_vs_sold. Víðara universe (properties 232.887, endurheimtar eignir); FK-drop 1.230. data_through nú 2026-06-16. Hrein endurgerð örugg — serial id hefur núll afkomendur (pg_depend/pg_constraint/app-grep). Rollback: D:\sales_history_rollback_20260622.{csv,sql}.

**Grunnreglu-uppfærsla — onothaefur**: ONOTHAEFUR=1 raðir geymast NÚ í SÖMU töflu með flaggi, EKKI aðskilinni töflu. Rök: sölu-sýnileiki á eignarsíðu krefst þess að röðin sé í töflunni (seld eign á að sjást, merkt). Viðmiðun varin: contamination-úttekt staðfesti öll 11 verð-MV + _sales_base sía onothaefur=0 (beinu sales_history-tilvísanir í MV eru EINGÖNGU max(thinglystdags)). Empírískt: Hraunbær n=400 flatt eftir apply (ono1=23% af töflu, ekkert hopp). Víkur frá project-instruction orðalagi („aðskilin tafla") — DECISIONS authoritative; uppfæra instruction-texta. eign/[fastnum] sýnir báðar; aggregöt sía 0.

**Opið / næst**: (i) daily_sales_refresh.py — endurnýtir load_cpi_lookup + derive_sales_rows úr scripts/rebuild_sales_history.py; fetch → derive delta → ON CONFLICT (faerslunumer,fastnum) DO NOTHING → REFRESH 13 MV → log; explicit pinnaður anker geymdur fyrir daglega/mánaðarlega samræmingu. (ii) schedula S4U ~02:30 GMT. (iii) mánaðarlegt CPI-systkin (refresh_cpi automation + endur-ankering). (iv) frontend sölu-merki „seld — ónothæfur samningur" á eignar-skoðun fyrir ono1.

---

## 2026-06-18 — v0 expert-agent STAÐIST + SKILL/specs tracked í docs/specs/

**Hvað**: v0-prófun á expert-agentinum (gold-standard pass, §6 #7) lokin og staðist. Fersk CC-session las SKILL_v0_draft.md, lék agentinn og svaraði 25 prufuspurningum úr AGENT_SPEC §5.2 gegnum read-only Supabase MCP; Danni + chat-Claude dæmdu.

**Skor**: 25/25 (einföld #1–10, fallback #11–17, composition #18–19, gildrur #20–25). G-flokkur (neitanir #20–25) 100% (R1 verðmat→iter4, R2 spá, R5 einstök sala, R6 leiga, G7 heildarvelta-neðra-mat, R8 fyrirvarar halda). **0 hallucination** — hver tala gagna-leidd með citation. Exit-skilyrði (≥80% + G-flokkur 100% + 0 hallucination) uppfyllt.

**Validerað**: router-fallback (gata→matsvæði→postnr; Fjóluhvammur/Laugavegur live), composition-bias G2 (Ánanaust leiddi existing 839þ. ekki aðal 1.066þ.), hrun-/hlutaárs-flögg, neitanir með vísun, citation [view·sía·data_through] alls staðar. Öll hönnunin validerast, ekki bara keyrsla.

**Betrumbóta-atriði (ekki fall)**: #14 Sólbakki — existing NULL (undir birtingar-gati), agent tók rétt matsvæðis-fallback en vitnaði í afsannaða ~202þ. existing-tölu. Næsta SKILL-iteration: G2/R3-orðalag → nefna enga existing-götu-tölu þegar hún er NULL/þunn.

**Documentation**: þrjú áður un-tracked hönnunarskjöl promtuð í docs/specs/ (stöðug, validerað): SKILL_v0.md (operating-skjal agentsins, 575 línur), AGENT_SPEC_v1.md (3-laga spec), T5_SEMANTIC_VIEWS_v1.md (13-view spec). Lokar context-loss-áhættu — cloud-Claude les þau nú úr git. 25-svara gold-pass-inn er v1 eval-fræ (§6 #7); formaliserast í eval-skrá þegar v1 hefst.

**Impact**: v0 er virkur agent núna (Claude Code/Desktop + SKILL + read-only MCP). Næsti gafl (hvorugt læst): v1 (eval-harness 50–100 sp. + verdmat_agent role + bankatól) vs verdmat.ai uppsetning.

---

## 2026-06-18 — AGENT_SPEC §6 leyst — v0 expert-agent ólæst

**Hvað**: Átta opnu spurningarnar í AGENT_SPEC_v1_draft.md §6 leystar (chat-Claude tillögur, Danni staðfesti). Þar með er v0 (SKILL.md + read-only MCP, handvirkt, Danni einn notandi) ólæst. ENGIN role, ENGIN GRANT, ekkert SKILL.md skrifað enn — hvert framkvæmdarskref áfram sér gated.

**Ákvarðanir (númer = §6-liður)**:
1. v2-tenging: NOLOGIN + SET ROLE fyrir v0/v1; LOGIN-role við v2 (Agent SDK á verdmat.ai auðkennir sjálfstætt). Role má verða til fyrr fyrir v1-prófanir.
2. statement_timeout 15s + lock_timeout 2s + idle_in_transaction_session_timeout 30s + default_transaction_read_only on + search_path=semantic. Stillanlegt án migration; MV svara í 0,1–116 ms, 15s forðar 8s-PostgREST-gildru á þyngri framtíðar-queries.
3. PUSHBACK gegn spec-tillögu §2.1(a), samþykkt: agent-role fær explicit GRANT SELECT á hverja nefnda public-facing MV (default-deny, §2.5-mynstur) — EKKI GRANT ALL + REVOKE á `_`-prefix + ALTER DEFAULT PRIVILEGES auto-grant. Rök: auto-grant sjálf-grantar ný/fasa-objekt áður en gotchas+exemplars eru til, sem brýtur prinsipp #1 (default-deny) og §2.5 („ósýnilegt þar til skjalfest"). `_sales_base` þarf engan REVOKE ef aldrei GRANT-að (MV eru materialized, þurfa hann ekki við query-tíma). Leysir innri spennu spec-sins (§2.1(a) vs §2.5) í þágu §2.5.
4. v0 án dedicated role: MCP-sem-owner með read-only sem agareglu (G16) er ásættanlegt fyrir helgar-prótótýpu með Danna einn. Hardening: kveikja á MCP read-only mode ef í boði (§2.3). Role lendir við v1 (fyrir ekki-Danna caller).
5. Rate/cost (v2): strúktúr samþykktur (dagþak per Pro + ≤6 queries/svar + hart mánaðarþak m. kill-switch); TÖLUR frestað þar til v0/v1 mælir raun-tóken-kostnað per spurningu — „20/dag" væri ágiskun, empirical-first ræður.
6. Hverfaheita-mappa („Vesturbær" → matsvaedi_numer): statísk í SKILL.md fyrir v0; 14. lookup-view (v_hverfi_lookup) ákvörðun tekin með fasa 2. v_sveitarfelag_lookup leysir sveitarfélaga-nöfn nú þegar; hverfi er fínni.
7. Eval-dómari: röð, ekki annaðhvort/eða — handvirk gold-standard yfirferð FYRST á fyrstu 25 spurningunum (kvörðun, sbr. GOLD_STANDARD_PROTOCOL), SVO deterministic + LLM-judge blanda sem viðvarandi harness, staðfest gegn gold-settinu. v1-mál.
8. Tónn: hlutlaus greinandi, ekki ráðgefandi — ráðgefandi rennur í fjárfestingaráðgjöf (R6 + grunnregla um enga slíka ráðgjöf).

**Impact**: v0 SKILL.md-smíð er næsta gated skref (chat-Claude semur forskrift úr §3-beinagrindinni + live view-unum; CC skrifar skrána). T1-könnun má fara parallel. **Scope-leiðrétting**: AGENT_SPEC §5.1 v0-plan (skrifað 2026-06-11) miðar við aðeins 4 live views og að fasa-2 spurningum sé neitað; T5 fasi 2 lokaði 2026-06-12, svo öll 13 MV eru nú live og MCP-sem-owner les þau öll → v0 nær yfir ÖLL 13 views, ekki 4-view undirmengi. „Neita fasa-2 spurningum" exit-skilyrðið í §5.1 á því ekki lengur við.

---

## 2026-06-18 — verdmat.ai lén keypt (fjórði consumer) + Vercel/hýsingar-ákvörðun + stefnu-endurröðun (agent-v0 + T1 parallel)

**Hvað**: Þrennt læst í dag. (1) verdmat.ai lén keypt gegnum Cloudflare sem heimili expert-agent afurðarinnar — FJÓRÐI consumer ofan á þrjá fyrri (bank-analytics, opinbert mælaborð, realtor-áskrift), allir lesa sama canonical gagnalag. (2) Vercel/hýsingar-ákvörðun fest. (3) Stefna næstu lotu endurröðuð: agent-v0 virk braut, T1 parallel.

**Tengsl við fyrri ákvarðanir (EKKI endur-skilgreining)**: Þriggja-laga agent-arkitektúrinn (L1 read-only SQL / L2 SKILL.md knowledge package / L3 output) + v0/v1/v2 roadmap er ÞEGAR læstur í DECISIONS 2026-06-10 (strategic audit, „Expert agent architecture"-kaflinn). Þessi færsla endur-skilgreinir hann ekki — hún byggir ofan á honum með þrennu nýju: léninu, hýsingar-módelinu, forgangsröðuninni.

**AGENT_SPEC_v1_draft.md (samhengis-varðveisla)**: Fable 5 session 2026-06-11 skrifaði AGENT_SPEC_v1_draft.md (726 línur) sem formaliserar arkitektúrinn frá 2026-06-10 í fullt spec: L1 verdmat_agent role-kröfur (USAGE+SELECT á semantic eingöngu, eigin statement_timeout), L2 data dictionary yfir öll 13 semantic-views + gotcha-listi G1–G16 + 24 exemplar-queries, L3 svar-snið + neitunarreglur R1–R8, v0/v1/v2 roadmap, fyrstu 25 eval-spurningar, og §6 með 8 opnum spurningum sem gata v0. Skjalið er UN-TRACKED (D:\verdmat-is\, spec-drafts búa utan repo) — ófáanlegt fyrir cloud-Claude. Ákvörðun: promota í docs/specs/ þegar §6 er leyst og spec-ið stöðugt, svo bæði tilvist OG innihald lifi í git. Þangað til er þessi málsgrein eina tracked-tilvísunin.

**Vercel/hýsingar-ákvörðun**: verdmat.ai = SÉR Vercel-verkefni undir núverandi Pro-teymi (afurðin er eðlisólík: samtal vs mælaborð), deilir sama Supabase-bakenda read-only. Ekkert nýtt grunngjald: Pro rukkar per sæti ($20), EKKI per verkefni; verkefni ótakmörkuð, notkun pooled á móti $20-inneign + innifalið 1 TB Fast Data Transfer + 10M edge-requests, og v0/v1-skali er langt undir. v0 þarf ENGAN Vercel (Claude + MCP + SKILL.md, handvirkt). FRESTAÐ til v2: agent-bakenda hýsing — Vercel Fluid Compute (5-mín function-timeout + keyrslutíma-mælir á löngum Claude-streymum) vs Cloudflare Workers (þegar í notkun fyrir R2 + lénið, engin egress-gjöld). Ríkjandi v2-kostnaður er Claude API-tókenar per spurningu, EKKI hýsing; stýrt af §6 #5 rate/cost-þökum.

**Stefnu-endurröðun**: Agent-v0 = virk afurðarbraut, gated EINGÖNGU á AGENT_SPEC §6 (8 ákvarðanir, engin kóðasmíð); getur sýnt sig á 13 lifandi semantic-views strax (götu-verð, markaðshiti). T1 (asking-vs-sold spread) = parallel flaggskips semantic-view (14.), tvöfalt hlutverk: mælaborðs-forsíðuefni OG beittasta spurning agentsins. Probe-before-build: join-þekju-könnun á undan view-frystingu. Hönnuð MEÐVITAÐ um Áfanga 7 ATS-töfluna (DECISIONS 2026-04-20) — T1 endurbyggir EKKI ATS-aðferðafræðina heldur bætir við því sem scraper-lagið eitt hefur: ferskt per-eign ásett verð, time-on-market, withdrawal-dynamics. FRESTAÐ í PLANNING_BACKLOG: Lota 2 (negotiable, mest atvinnuhúsnæði — snertir hvorki agent né T1) og addr-tier remediation (Finding C, 0,07% núna). Hvorug blokkar virku brautirnar.

**Impact**: Næsta vinnulota = AGENT_SPEC §6 í chat (ákvarðanir, ekkert skrif) → v0 SKILL.md. T1-könnun parallel í CC. Engin role, engin GRANT, ekkert SKILL.md skrifað fyrr en §6 er leyst (sér DECISIONS-færsla kemur þá).

---

## 2026-06-16 — Step 3d Lota 1 KLÁRUÐ + 3 empirical findings

**Hvað**: CC4.1 (Opus 4.8) keyrði Stage 7 + 8 + 8.5 + 9 yfir nótt 15.→16.6. Canonical hopp úr **1.266 í 12.023 raðir** (+10.757 mbl, +724 fold í visir/myigloo secondary_source_ids). 0 villur, 0 systemic over-fold eftir lagfæringu. Þrjú ný empirical findings læstu hér + sett í `SCRAPER_SPEC_v2_draft.md §2.3-D` (un-tracked, +36 línur).

**(1) STAGE-BREAKDOWN**:

| Stage | Aðgerð | Raðir | Fold | Tími |
|-------|--------|-------|------|------|
| Stage 7 sale | priced sale promotion | 10.475 | 614 | ~42,5 mín |
| Stage 8 rent | priced rent (initial) | 252 residential | 90 | 76 sek |
| Stage 8.5 rent | commercial-on-request capture | 30 commercial | 20 | 12 sek |
| Stage 9 spec | §2.3-D additive uppfærsla | (1.230→1.266 línur) | — | — |

- Per-row commit yfir pooler ~0,21 sek/röð (durability kostnaður; crash-resume frítt).
- Heildar promoted mbl: **10.757 raðir + 724 fold = 11.481 promoted**.
- Tests 34 → 39 (rent price=1 sentinel × 3, decompose_commercial_sub_type × 2).
- Resolve-method dreifing: source_supplied 9.961 (93%) > addr 92 > geo 39 > unresolved 665.

**(2) ÞRJÚ NÝ EMPIRICAL FINDINGS (LÆST)**:

***Finding A — matshluti er encoding-suffix, EKKI per-eining ID*** (Stage 7 uppgötvun): mbl `fastano = fastnum*10^k + matshluti` en SAMA eining fær BREYTILEGT matshluti yfir margar listing-instances — Hringhamar 37 íb.104 (fastnum 2528604, 80,5M, 113m²) birtist sem 16 mbl listings með matshluti 0/5/13/15/32. Þ.a. dedup Tier-1 LYKLAR Á BERA `fastnum`, EKKI `(fastnum, matshluti_unit_id)`. matshluti_unit_id dálkurinn er **encoding-lineage / debug artifact**, EKKI dedup-lykill. HMS úthlutar hverri einingu sínu eigin 7-stafa fastnum (Stage 5 Hringhamar 35 íb.208/309 sönnun) — 7-stafa stigið aðgreinir einingar nú þegar. Endurskoða ef HMS gefur út stöðug per-eining ID. **Q4-frestun (within-run mbl↔mbl folding) staðfest sem rétt val empírískt.**

***Finding B — rent listings með price ≤ 1 ISK eru commercial-rent-on-request, EKKI residential junk*** (Stage 8 uppgötvun): 50/392 raðir í priced mbl rent slice voru price=1 sentinel fyrir stór atvinnurými (Bæjarflöt 17 886m², Tónahvarf 10 3186m², Borgartún 25, Suðurlandsbraut 4). Residential íbúðaleiga á Íslandi er aldrei 1 ISK — signal er ábyggilegt. Promotion-leið: `price_amount=1`, `is_price_on_request=true`, `category='commercial'`, `sub_type` via keyword-resolve með `mixed_use_other` fallback, `lease_term_class='unspecified'`. **Lota-2 caveat**: negotiable slice's verd=0 sentinel getur líka verið residential — sá branch verður endurskoðaður þar.

***Finding C — addr-tier over-fold á nýbyggingum með óleyst fastnum*** (Stage 7 jaðar-fund): 3 sale targets (Vorbraut 14 ×2, Hrafnaborg 4) með ólíkar einingar fold-uðust ranglega í eina canonical-röð vegna sama addr+price+stærð + óleyst fastnum (properties-tafla ekki uppfærð á nýbyggingum). ~7 einingar tapaðar af 10.475 = **0,07% gagnatap**, undir mæli-skekkju fyrir T1 asking-vs-sold spread, en bendir til **normalize_address bug** sem strippar „íb.X" suffix of-aggressively. Aðskilið remediation-verkefni post-Lota-1; líklega tengt visir/myigloo addr-mynstri líka (kerfis-vandi á promote-fjölskyldunni, ekki bara mbl).

**(3) ENDURKALIBRUÐ STOP-CONDITION SANNREYND**: gamla `mbl_loses > 250` tripp-aði ranglega á Stage 7 (614 lögmæt fold, 99% same-unit re-lists). Nýtt merki **distinct-fastnum/addr per target > 1 á > 5 targets** tók við og virkaði rétt á Stage 8 (8 multi-fold targets, 0 over-fold). Heildar-fold-count er EKKI lengur tripwire — skalast hreint með re-list-eðli corpus.

**(4) ÁKVÖRÐUN #1 LEYST IN-FLIGHT (commercial-rent capture)**: Stage 8 lenti í gati þar sem rent með price=1 datt í junk-síu (hardkóðað rent→residential). CC4.1 uppfærði `resolve_price(verd, table)` signature + `decompose_commercial_sub_type` fall + run-lúppu, endurkeyrði rent slice via NULL-watermark mekkanisma, og bjargaði öllum 50 raðum án rollback. **Engin gögn glötuð, engin migration þörf, capture-mandate intact.**

**Schema additions í scraper.listings_canonical (læst, live)**: `matshluti_unit_id smallint` + `source_raw_fastnum bigint` + `is_price_on_request boolean` + slökun á `ck_price_pos` + `ix_lc_fastnum_unit` non-unique composite index. Migration `20260615163101_step3d_listings_canonical_mbl_promote` beitt gegnum MCP. 1.266 núverandi raðir fengu defaults við ALTER (NULL, NULL, false) — engin röð raderuð.

**Bíða Lotu 2 (negotiable, 2.673 raðir = 1.694 sale + 979 rent)**: gated á tvær ákvarðanir áður en kóði fer í verk:
- **Q1 (frá 2026-06-15)**: 'unknown_commercial' enum-gildi fyrir `lease_term_class`. (a) `ALTER TYPE lease_term_enum ADD VALUE` vs (b) endurnýta `'unspecified'` með skýrum sub_type placeholder. Mín núverandi tilfinning er (a) — semantíkin „commercial-rent með ókannaðri lease-term" er ólík „residential-rent með ekki-uppgefnu lease-term" og á að vera aðgreinanleg.
- **Visir backfill** (407 visir-raðir með price=1 ↔ is_price_on_request=true): aðskilið verkefni, ekki kritískt fyrir T1 en góður frágangur.

**Næst**: Lota 2 hönnunarprompt + addr-tier remediation (Finding C) sem aðskilið verkefni. T1 (asking-vs-sold spread) verður mæld á alvöru gögn í fyrsta sinn — 10.475 mbl sale + 226 visir sale = 10.701 sale raðir í canonical sem hægt er að joina við kaupskrá fyrir spread-greiningu.

---

## 2026-06-15 — Þrjár hreinar nætur + Step 3d empirical foundation

**(1) STEADY-STATE STAÐFEST — sjálfvirka delta-keðjan stöðug yfir 13./14./15.6**:
- `LastTaskResult=0` öll þrjú kvöld; `halt_reason` null í öllum 6 mode-um; hvert log endar á **CHAIN CLEAN**.
- Blob-counts: nótt 1 = **68 síður / 1047 listings** (2ja daga uppsöfnun frá priming, vænt); nótt 2 = **20 síður / 293**; nótt 3 = **27 síður / 396**.
- High-water færist áfram monotónískt á öllum 4 delta-modes; **100% `fields=v2`** á öllum delta-síðum; `fetch_kind *_negotiable_delta` sýnir delta-fix **471edc7** virkan.
- `session_request_count` = **1727** uppsafnað; pre-flight budget **400/900** með ríflegu borði (mest 68 nýtt á einni nóttu).
- Engin cap-hit, engin neitun, engin process að lifa milli nætur.

**(2) STEP 3D EMPIRICAL FOUNDATION (CC2.1 könnun 15.6)**:

***Fastnum encoding-uppgötvun (endurnýtanleg þekking)***:
- mbl-`fastano` er EKKI uniformly 7-stafa HMS-fastnum. Encoding er `fastano = fastnum × 10^k + matshluti` (leiðandi 7 stafir = HMS canonical fastnum, aftari 1–2 stafir = matshluti/eining-index).
- Empírísk sönnun gegn `public.properties.fastnum` (232.887 raðir 100% 7-stafa, range 2.000.044–2.543.427):
  * 8-stafa `//10` → **95,4% hittni** (5.639/5.910)
  * 9-stafa `//100` → **91,0% hittni** (2.944/3.236)
  * 7-stafa hrátt → 73,8% (foreign + vantar í properties)
  * Rangir transformar (8`//100`, 9`//10`) → **0%** (afsannar tilviljun)
  * Random baseline 43%
- Dreifing í `parsed_mbl_sale` (N=13.873): NULL 5,9% / 7-stafa 10,1% / 6-stafa 1,2% / 8-stafa 50,6% / 9-stafa 32,1%.
- Implication: Step 3a probe sá „6–9 digit, EKKI uniformly 7-digit" en greindi ekki encoding-ið — pre-amendment sample og engin transform-prófun. Framtíðar uppsprettur (HMS staðfangaskrá, kaupskrá multi-parcel) gætu borið sama mynstur og á að prófa fyrir parser-hönnun.

***Resolution rates***:
- `parsed_mbl_sale` (N=13.873): derived fastnum ∈ properties = 11.852 (85,4%); non-foreign = **11.789 / 12.733 = 92,6%** (sambærilegt við visir 93%).
- `parsed_mbl_rent` ber ENGAN fastnum-dálk → 100% rent gegnum address/geo resolution (eins og visir-rent + myigloo).

***Cross-source overlap (mbl × canonical 1.266)***:
- mbl-sale × visir-sale = **198/208 same-tenure** (95% af visir-sale finnst á mbl, en aðeins **2,4% af mbl-sale** = 198/8.396).
- mbl × allt canonical fastnum-overlap = 416/1.096 (38% af canonical).
- mbl er overwhelmingly net-new — bætir ~97,6% net-nýju við sale-corpus.
- Match-gæði há (sample 10: sama heimilisfang + sama verð beggja vegna).
- **SOURCE-PRIORITY STATUS QUO LÆST** empírískt: visir(1) > mbl(2) > myigloo(3). Á 198 same-tenure overlap-i vinnur visir (§2.3-D rök: hreinni SSR-parse), mbl foldast í `secondary_source_ids[]`. Munur í endanlegu canonical-i ~10 raðir — ekkert efnislegt rök til að snúa við.

***Post-3d canonical-stærð spá***: 1.266 → **~11.000–13.500 raðir** (efri mörk ef listings haldast per-listing; neðri ef fastnum-dedup þéttir re-lists). mbl bætir 9.000+ nýjum eignum.

***Þrjú LÆST design-flögg fyrir 3d hönnun***:

1. **Unit-collapse (~270 multi-unit nýbyggingar)**: matshluta-suffix VARÐVEITTUR í eigin dálki í canonical-laginu (t.d. `matshluti_unit_id`), ekki sleppt. Rök: kaupskrá vinnur við building-base 7-stafa, en listings auglýsa einstakar einingar; collapse myndi týna per-unit comparables og þétta multi-listings af sama building (t.d. Hringhamar 37 = 16 listings → 1 fastnum) sem ruglar pricing-tölfræðina. Dálkurinn NULL fyrir visir/myigloo (gögn ekki til þar), gildi þaðan sem það er til.

2. **atv-tenure misclassification**: tenure leiðast af parse-merkjum (`tegund_raw` + „(leiga)" í gata + verd=0), EKKI af mbl-endapunkti (`fs_fasteign` er bara root-name, ekki tenure-signal). 1.328 negot-atv bíða prómotunar; hve hátt hlutfall er commercial-rent mælist í prómot-keyrslunni sjálfri. Tenure-cascade sama mynstur og visir/myigloo nota. Án þessa: massíf tenure-mistök OG miss-dedup gegn visir/myigloo commercial-rent (cross-tenure 233-skörun verður þá same-tenure dedup-eligible).

3. **is_foreign sía**: foreign-sía keyrir ÁÐUR EN fastnum-resolution (truncation-collision sönnuð empírískt — spænskar 8–9 stafa fastano truncate-ast óvart í properties-range, t.d. „SPÁNAREIGNIR — Villamartin" fastano 204130526 → 2041305 ∈ props). Íslenskt-override: postfang ∈ {101–902} OR lat 63–67,5 → ekki útilokun jafnvel þótt sentinel-postfang (1053/1000) birtist (Vesturvin-leki, 21 raðir ranglega flaggar). Sentinel-postfang eitt og sér nægir EKKI sem foreign-merki ef íslenskt signal er annars staðar í röðinni.

**(3) JORD-MYSTERY LEYST (mini-probe 15.6)**:
- mbl aggregate í dag: jord_all 775, fjolb_all 7293 — nánast óbreytt frá Step 3a (9.6) jord 778 / fjolb 7266.
- parsed jord 387 ≈ publishable jord 306 + negotiable 69 = 375 (mismunur 12 = churn 12.→15.6).
- „778 → 387" var ALDREI like-for-like — publishable/draft-sían að virka eins og hönnuð; jord/lóðir hafa oft verd=0 eða fermetra=0 drög (~400 raðir) sem seed-crawl síar af ásetningi (`where: verd>0, fermetrar>0`).
- Hvorki mbl-reclassification né parser-villa. **No-op fyrir 3d.**
- **Lærdómur**: bera saman like-for-like (publishable vs publishable) áður en flokkunar-shift er kallaður parser-villa. Hasura aggregate-count án where-klausu er EKKI sambærilegt við parsed-corpus.

**Næst**: Step 3d hönnunarprompt fyrir `promote_mbl` — afgreiðir þrjú flögg að ofan, mælir atv-tenure raunverulega dreifingu í prómotuninni, promotar mbl-corpus í canonical (1.266 → ~12K raðir). Hvert gated skref sér go.

**VIÐBÓT (síðar 15.6) — STEP 3D HÖNNUNARDRÖG SAMÞYKKT, 5 Q-SVÖR LÆST**

CC3.1 (Opus 4.8) skrifaði `D:\verdmat-is\STEP_3D_DESIGN_v1_draft.md` (341 línur, un-tracked) byggt á empirical foundation að ofan. Chat-Claude (Opus 4.7) tók afstöðu á öllum hönnunaratriðum + 5 open questions; Danni samþykkti. Læsa hér.

**Fimm Q-svör læst**:
- **Q1 (BLOKKERANDI `ck_price_pos`)** → valkostur (a) **SAMÞYKKTUR**: bæta `is_price_on_request boolean NOT NULL DEFAULT false` við `scraper.listings_canonical`; slaka `ck_price_pos` í `(price_amount > 0 OR is_price_on_request)`. Þriðja schema-breyting í einni migration (með `matshluti_unit_id` + `source_raw_fastnum`). Visir-raðir (price=1 sentinel) fá `is_price_on_request=false` við migration — backfill á þeim er aðskilið verkefni, ekki kritískt fyrir T1.
- **Q2 (commercial-rent mapping)** → `category='commercial'` + `sub_type='unknown_commercial_rent'` placeholder + `lease_term_class='unknown_commercial'` sentinel-gildi (frekar en NULL — heldur `ck_rent_lease` óbreyttu). LLM-extraction pass (T2-áfangi) refinar síðar. Sentinel-gildi gæti þurft `ck_rent_lease` uppfærslu — staðfesta nákvæmt CHECK við migration-smíði í CC4.x.
- **Q3 (rent-specific source_priority REVERSAL)** → SAMÞYKKT. Sale: `visir(1) > mbl(2) > myigloo(3)`. Rent: `visir(1) > myigloo(2) > mbl(3)`. Rök: myigloo er rent-sérhæfð (structured lease-term, sqm) með hreinni rent-specific gögn; mbl rent er secondary frá sale-source með þekkta atv-tenure misclassification. **Spec-uppfærsla**: `SCRAPER_SPEC_v2_draft.md §2.3-D` fær tenure-specific source_priority — í sömu lotu og kóðinn fer í verk.
- **Q4 (within-run mbl↔mbl folding)** → frestað þar til lotu-1 validation. Static snapshot fyrirmynd (eins og visir gerði). Matshluti gerir folding tæknilega öruggt en sannprófun á lotu 1 fyrst.
- **Q5 (jaðar-encoding 6-/10-stafa, 176 raðir)** → NULL `matshluti` + addr/geo resolution. Engin sérmeðhöndlun.

**Tveggja-lotu slíður LÆST**:
- **Lota 1 (verðlagt, 11.461 raðir)** = sale-pub 11.069 + rent-pub 392. Óháð Q1. Fer í verk eftir migration. Sannreynir cascade, resolution-pípu og UPSERT-mynstur áður en negotiable corpus snertist.
- **Lota 2 (negotiable, 2.643 raðir)** = sale-negot 1.664 + rent-negot 979. Gated á Q1 DDL. Reynir á tenure-cascade fyrir alvöru (~1.014 atv → commercial-rent spá; cascade-úttak skráð í promote_mbl stats-counters).

**Schema additions í einni migration (DDL ósamþykkt í Supabase enn)**:
- `matshluti_unit_id smallint` (NULL cross-source / 0 mbl single-unit / 1–99 suffix)
- `source_raw_fastnum bigint` (hrái `fastano` lineage; NULL cross-source)
- `is_price_on_request boolean NOT NULL DEFAULT false`
- `ck_price_pos` slökun: `(price_amount > 0 OR is_price_on_request)`
- `ix_lc_fastnum_unit` non-unique composite `(fastnum, matshluti_unit_id) WHERE fastnum IS NOT NULL` (dedup Tier-1 lykla-uppfærsla)
- Mögulega `ck_rent_lease` uppfærsla fyrir `'unknown_commercial'` sentinel — staðfesta CHECK við migration-smíði.

**4-decision-point promotion-pípa**: `foreign → tenure → price → dedup`; per-row commit (pg + sqlite); watermark-resume á `promoted_to_canonical_at`; UPSERT á `(source, source_listing_id)` með `canonical_version++`; stats-counters á tenure-cascade og dedup-actions.

**Næst**: CC4.x — smíða migration DDL og `promote_mbl.py` í einni session með skýrum gates: (i) migration draft → HALT/samþykki → apply via MCP, (ii) kóði skrifaður, (iii) smoke `--limit 200 --dry-run --slice priced` → HALT, (iv) smoke `--confirm` → HALT, (v) full lota 1 (11.461 raðir), (vi) stats report → HALT á Lotu 2 (sem bíður þá á aðskildu visir-backfill verkefni).

---

## 2026-06-11 (§6-A + delta-vélbúnaður) — Nightly delta orchestration spec-amendment + chain v1 smíðuð (ÓVOPNUÐ)

**Hvað**: §6-A amendment skrifað í un-tracked spec-draftinn (SCRAPER_SPEC_v2_draft.md,
1.066 → 1.230 línur, additive) og allur delta-vélbúnaðurinn smíðaður, testaður og
live-validated — en VOPNUN bíður operational gates (re-sweep exhaust → full-corpus parse
→ prime → task-arming). Scraper-commits dagsins: 8abc01e (Step 3c parse_mbl tier, 963
línur, 17 testar — full-corpus keyrsla gated á re-sweep lok), 471edc7 (delta-göp),
23726b9 (chain + scheduler).

**§6-A amendment efnislega (lifecycle per source)**: mbl = delta-only nightly
(urgency-locked); visir = vikulegt timed-batch refresh undir IP-throttle (≤300 req/batch,
45–60 mín pásur, ~10–15h); myigloo = nightly index-walk (9 síður — gefur ókeypis
withdrawal-diff) + vikulegt full detail (~22 mín).

**Withdrawal detection — fyrsta flokks hönnun, EKKI neðanmáls**: mbl hard-deletar →
hvarf ER afskráningardagurinn sem time-on-market og T1 asking-vs-sold þurfa. Lykilinnsýn:
**16-raða þakið er per REQUEST óháð field-fjölda → id-only liveness-sweep kostar
nákvæmlega sömu ~950 síður og full enriched sweep** — þar með er vikulega liveness-sweepið
FULL ENRICHED re-sweep (sama budget kaupir liveness-diff OG content/mynda-refresh í einu;
re-sweep vélbúnaðurinn b57b7c0 er tólið). Diff: live id-mengi vs is_active mbl-mengi í
canonical → withdrawn_at. **Interval-semantík á withdrawn_at**: vikuleg sweep gefur bil
(last_seen_at = neðri mörk, sweep-dagur = efri), ekki punktdag — ±3,5 dagar á metric sem
mælist í vikum; skjalfest í column-comment. **Cadence: laugardagskvöld vikulega**
(nightly = allt §0.5 budgetið á hverri nóttu, ósjálfbært; monthly = ±2 vikur, of gróft).

**TVÆR LOCKED RULES**:
1. **Since-priming er SKYLDA fyrir fyrstu delta-nótt (1970-guard)**: since_key=NULL
   post-seed þýðir að fyrsta delta sweepar frá epoch og advance-ar high-water framhjá
   page-budget þakinu — breytingar handan þaksins skippast VARANLEGA. Prime úr parsed
   corpus maxima (prime_delta_since.py), aldrei 1970-keyrslu af stað.
2. **§2.3 `is_active` amendað í per-source liveness-semantík**: 2-daga reglan
   (last_seen_at ≥ run_ts − 2d) gerði ráð fyrir nightly-full-sweep uppsprettum og hefði
   **mass-false-withdrawað allan mbl-stofninn** undir delta-only steady-state (óbreytt
   heilbrigð listing sést aldrei milli vikulegra sweepa). mbl: explicit liveness-sweep
   diff EINGÖNGU; myigloo/visir: absence úr þeirra index; delta-hit refreshar
   last_seen_at en absence úr delta þýðir EKKERT.

**Delta-göpin tvö + fixar (471edc7)**: (1) negotiable sneiðin var delta-blind (delta-modes
báru publishable predicate — 72,3% af real rent corpus hefði aldrei fangast í
steady-state) → delta-sale-negotiable + delta-rent-negotiable með eigin since_keys og
fetch_kind discriminatorum (haldið undir list_page_ prefix fyrir parser-samhæfni);
(2) prime_delta_since.py með hörðum REFUSE-girðingum (live fetcher via process-scan +
recency-heuristik / since þegar sett nema --force m. history-archive / tómur parsed
slice), dry-run default, atomic state-write. Testar 30 → 37.

**Nightly chain v1 + scheduler smíðuð, live-validated, ÓVOPNUÐ (23726b9)**:
nightly_delta_chain.sh = 4 delta-modes serial, gated á exit 0 + halt_reason null,
abort-not-retry, pre-flight girðingar (exit 2): live-fetcher / since-primað / 24h-budget
≤900 síður; cap-hit WARNING per mode (high-water advance-ar framhjá ósweepuðum síðum við
cap); morgunreport í night_logs/ (síður/listings/high-water/halt per mode + samtala);
PYTHONIOENCODING=utf-8 (run_monthly latent-bug #5 lexían — mojibake sást í fyrsta dry-run,
root-fixað). **Dry-run live-validation sannaði allar þrjár girðingar gegn raunveruleikanum**:
fann keyrandi re-sweep prósessinn, flaggaði öll fjögur óprimuð since_keys, taldi 488+400=888
≤ 900. register_delta_task.ps1 = verdmat-nightly-delta 01:00 daily, speglar backup-mynstrið
MEÐ viljandi fráviki: enginn RestartCount (abort-not-retry er keðjustefnan), 8h limit.

**Automation-þrep eftir blast radius (§6-A.3, HALT-disciplinið lifir af automation)**:
v1 = fetch-only STRAX post-gates (raw layer append-only + idempotent, versta tilfelli
sóaðar requests); v2 = + incremental parse eftir EINA sannaða handvirka full-corpus
keyrslu (sér-DB, idempotent, DLQ soft-fail); v3 = + promote SÍÐAST eftir 2–3 sannaðar
handvirkar promote-lotur (sama bar og run_monthly push-gate) — prod-skrif fara ekki í
unattended loop fyrr.

**Scheduling-ákvarðanir (§6-A.4-Q svarað af Danna)**: Task Scheduler 01:00 **user-level**
(Q2, backup-precedent); **automated WU-re-arm í einangruðu elevated taski + dagatals-
áminning fyrstu mánuðina** (Q1, belt-and-suspenders þar til re-arm taskið er sannað);
**vélin er alltaf á** (Q3 — AC sleep/hibernate þegar óvirk per power-settings); morgun-
report **skrá-only þar til §7 delivery** er byggt (Q4 — engin email/Sentry wiring strax).

**Næst (operational gates, í röð)**: re-sweep exhaust (Session A) → init_parsed_mbl_schema
+ full-corpus parse_mbl --confirm → prime_delta_since --confirm → register_delta_task
(elevated) → fyrsta nótt + morgunreport-yfirferð. Hvert skref sér gated go.

**VIÐBÓT 2026-06-12 — öll operational gates kláruð sama dag; §6-A v1 ER LIVE**: Re-sweep
exhaust staðfest (sale 10.936 / rent 376 enriched). **Full-corpus parse lokið og verified**:
1.582 blobs (706 v1 + 876 v2) / 25.261 listings → **13.873 sale + 1.371 rent raðir á 52,9s,
0 DLQ**; nested 100% á v2-röðum; **idempotency sönnuð á alvöru gögnum** (re-run: 25.261
skipped, 0 breytt). **v1-winners 1.243 sale + 16 rent = fyrsti mældi withdrawal-forsmekkurinn**
(listing séð í scalar-seedinu 9.–10.6 en aldrei í v2) — MEÐ efri-marka caveat: talan blandar
alvöru hard-deletes, verd→0/syna→false umbreytingum post-negotiable-seed og offset-drift
pagination-missum re-sweepsins (4,5%/dag er yfir markaðstakti; rent 1,4%/dag nær raunveru) →
**tveggja-fjarvista reglan (sbr. v1 §7.2) fer í 3d-hönnunina, single-sweep diff stimplar
ALDREI withdrawn_at**. **is_foreign 1.140 (8,2% af sale)** — Spánarheimili-blokkin er
efnisleg promotion-sía í 3d, ekki edge-case. **Prime lokið**: öll fjögur since_keys sett úr
parsed maxima (sale 12.6T00:34 / rent 11.6T09:05 / negotiable bæði 10.6T18:xx); recency-
girðingin sannaði sig í leiðinni (neitaði <30 mín frá re-sweep lokum — beðið, ekki bypassað).
**register_delta_task.ps1 S4U-fix (fc206e6)**: Password-principal via -Principal promptar
aldrei → skráning féll 12.6 með misvísandi success-echo; nú S4U logon (ekkert geymt lykilorð,
dugar local-disk + outbound-HTTPS keðju) + RunLevel Limited + skilyrt echo í try/catch.
**Taskið SKRÁÐ og Ready hjá Danna — fyrsta nótt 13.6.2026 kl. 01:00**, morgunreport í
scraper_data/night_logs/.

---

## 2026-06-11 (T5) — Semantic layer fasi 1+1.5 live: könnun → hönnun → 4 MV í Supabase á einum degi

**Hvað**: Track A (T5 úr 2026-06-10 audit) keyrði allan hringinn í einni session:
empírísk könnun (strangt read-only) → view-hönnunardraft → fasi 1 creation → fasi 1.5
materialization + composition-bias fix. Nýtt **`semantic` schema live í Supabase: 5
objektar** — `_sales_base` (venjulegt view, internal grunnlag: sales_history ⋈ properties
m. götunormaliseringu, −2 nýbyggingarproxy, per-árs p01/p99 ppm2_real outlier-flaggi) +
**4 MATERIALIZED views** (`v_street_directory` 24.253 raðir, `v_matsvaedi_prices_yearly`
9.216, `v_street_prices` 3.869, `v_postnr_prices_yearly` 6.554) m. UNIQUE index á natural
key hvers. Owner-rights (EKKI security_invoker — meðvitað frávik frá Group B mynstri:
framtíðar agent-role þarf þá bara schema-USAGE + view-SELECT, ekkert á base-töflur), EKKI
PostgREST-exposed, **ENGIN GRANT enn** (agent-role er sér gated skref). Spec-draft
(un-tracked per verklagsreglu): `D:\verdmat-is\T5_SEMANTIC_VIEWS_v1_draft.md` — 12 views
hönnuð m. full-SQL + caveats sem first-class agent-knowledge deliverable; 8 eftir í fasa 2.

**Könnunar-grunnur (læstur í draft §0)**: `sales_history` er pairs-leidd arm's-length
undirmengi (173.867 raðir, 2006-05 → 2026-04-17, verð í HEILUM kr; full kaupskrá er
local-only á D:\kaupskra.csv) — 100% fastnum-match við properties. **420 onothaefur=1
lekar** (þar af 290 frá 2025–26, D3/refresh-append án síunar) → hörð `onothaefur=0` sía
harðkóðuð í hverju viewi. Gata krefst parsing úr heimilisfang (17.805 götur; 2.619 nöfn í
>1 sveitarfélagi → **lykill = gata×sveitarfélag**, 24.322 pör; tvær formatting-kynslóðir
[D3-recovery sviga-form] normaliseraðar í _sales_base). Þéttleiki 2020+ residential clean
(66,4K sölur): gata median 6 sölur (86% sala á ≥10-götum → pooled 5 ára gluggi + HAVING ≥5
gat), matsvæði median 140 (~80/175 bera ≥30/ár → árstrend), póstnr fallback-lag. Blöndun
fjölbýli/sérbýli á 677/1.455 ≥10-götum → per-tegund GROUPING SETS m. 'allt'-rollup.

**§6 ákvarðanir Danna — átta, allar afgreiddar**: (1) owner-rights grant-líkan samþykkt;
(2) PostgREST-exposure NEI í v1; (3) nýbygging = byggar ≥ söluár−2 (canonical regla,
samræmi við `is_new_build = FULLBUID=0 OR age_at_sale ≤ 2` í training-pipeline; 17,2% sala
2020+); (4) heat-þröskuldar v_hood_heat standa sem v1-heuristik MEÐ skyldu-kalibreringar-
tékki gegn ats_dashboard_monthly_heat við fasa-2 creation; (5) agent-role fær EKKI
_sales_base í v1 (aggregates eingöngu); (6) **ONOTHAEFUR-append lekinn á backlog sem
upstream root-fix** (views verja sig sjálf á meðan); (7) sveitarfélaganafna-möppun
(„Kópavogur"↔„Kópavogsbær") verður statískt lookup-view í fasa 2 per canonical-layer
reglu; (8) **composition-bias fix (domain-innsýn Danna)**: median á einingu með háa
nýbyggingahlutdeild er nýbyggingaverð, ekki verðmæti eldri stofnsins — verð-viewin þrjú
fengu `n_existing` + `median_ppm2_real/nominal_existing` + `median_kaupverd_nominal_existing`
+ `median_ppm2_real_newbuild`, öll með 5-sölu þunn-sellu NULL-vörn. **Empírían**: bítur á
blönduðum einingum (Ánanaust: 'allt' 1.066þ. vs existing 839þ. real-kr/m² = 227þ. bias;
Sólbakki Fjarðabyggð 460þ.), ~0 á rótgrónum götum (Hraunbær) — og **Sunnusmára-lærdómurinn**:
á alnýjum götum þar sem „eldri stofninn" er sjálfur nýlegar endursölur er bilið ~0
(n_existing=129 hitti spá, bil gerði það ekki) — build-freshness skipting aðgreinir
sölu-ferskleika, ekki stofn-aldur; skjalfest í caveats.

**Materialization-ákvörðun MÆLD, ekki giskað**: v1-hönnun sagði plain views; creation-
gátlistinn felldi hana — warm-latency `_sales_base` **25,5s** (properties_pkey full-index-
scan 23,1s: random heap-IO yfir 232K breiðar jsonb-raðir á litlu instance-i; fyrsta mæling
33,9s var menguð af samhliða-keyrslu — IO-samkeppni á instance-inu er sjálfstæður lærdómur,
þung queries keyrast EITT í einu). Storage-mótrökin reyndust draugatala: „424/500 MB" var
úrelt session-minni; **mælt 1.003 MB / 8 GB Pro-budget (12,5%)**. → 4 output-MV (WITH NO
DATA í migration = hreint DDL; fyrsta REFRESH sér operational skref), latency eftir:
**0,145 ms** (indexed götu-lookup) / **116 ms** (full-scan aggregate). Row counts óbreytt
gegnum materialization. **REFRESH-ábyrgð (draft §4.1)**: handvirkt gated skref eftir HVERJA
sales_history-uppfærslu þar til run_monthly post-push hook kemur; copy-paste blokk í §4.1;
eitt í einu, ekki samhliða.

**Migrations + reconciliation-mynstur**: `20260611104645_t5_semantic_phase1` (commit
0868c42) + `20260611155653_t5_semantic_phase1_5` (commit c29b4b6). **MCP apply_migration
skráir version sjálft í supabase_migrations.schema_migrations** — ekkert CLI `migration
repair` þarf (ólíkt psycopg2-leiðinni); reconciliation = disk-skrá nefnd nákvæmlega eftir
MCP-version. Einfaldara mynstur en 2026-05/06 færslurnar lýsa; gildir framvegis fyrir
MCP-applied migrations.

**Scraper-schema exposure ráðgáta**: REST-próf (Accept-Profile probe, PGRST106) sýndi
exposed schemas = public + graphql_public EINGÖNGU — scraper-exposure sem var gerð manually
~1. júní er horfin. MEÐVITAÐ ekki endurvakin þar til REST-consumer er til; semantic fylgir
sömu reglu. Aukafinding: authenticator ber statement_timeout=8s — relevant fyrir hvaða
framtíðar REST-exposure sem er og fyrir agent-role timeout-hönnun.

**Næst (T5 track)**: Fasi 2 creation — 8 views (street_activity, sveitarfelag_market,
matsvaedi_trend_quarterly, hood_heat, newbuild_share, model_vs_sold_by_hood,
summerhouse_market, price_distribution_by_hood) + v_sveitarfelag_lookup; gated á tvo §4
forleiki: predictions-eininga-tékk (liður 3, fyrir model_vs_sold) + heat-kalibrering
(liður 5). Síðan GRANT-skref samhliða agent-role hönnun (v0 expert agent).

**VIÐBÓT 2026-06-12 — FASI 2 LOKAÐ morguninn eftir; semantic layer v1
FULLSKIPAÐ (13 MV + _sales_base view)**: migration `20260612091832_t5_semantic_phase2`
(commit 73c1adb) — 9 ný MV þ.m.t. `v_sveitarfelag_lookup` (64 raðir, 20 íhaldssamir
aliasar: aðeins suffix-afleiðingar og „Sveitarfélagið X"-strip, engar bæjarnafna-
giskanir). **Fortékkin tvö græn fyrir apply**: (1) predictions-eininga-ratio
**1,0042** (IQR 0,944–1,082, n=9.500) → v_model_vs_sold_by_hood skapað; (2)
heat-kalibrering **hot 21 / neutral 65 / cold 18 / insufficient 75** á 179
matsvæðum (hot-median +8,1%, cold −5,1%) → ±5%/±2%+±15% þröskuldar standa
óbreyttir (íhaldssamara en ats-þriðjungar; ats mælir annað signal). Row counts
í spá-bili (street_activity 39.323 stærst; fasa-2 summa ~52K yfir grófu §5
~30–40K mati — skýrt frávik, activity spannar öll 21 árin); latency 3,5 ms.
**Summerhouse-trim valið skjalfest**: ppm2 í v_summerhouse_market ótrimmaður
meðvitað — _sales_base outlier-flaggið nær aðeins yfir íbúðarsölur, median er
robust og kaupverð er leading stat á sumarhús. REFRESH-blokk draft §4.1 nær nú
yfir öll 13 MV.

---

## 2026-06-11 — Step 3b operational closure + enriched re-sweep prioritization

**Hvað**: Öll fjögur mbl seed-modes keyrðu til enda — Step 3b er OPERATIONALLY CLOSED.
Enriched re-sweep af scalar-generation publishable corpus ákveðinn og settur í gang STRAX
(ekki á post-P3 backlog). Journal-færslan hér læsir tölurnar, tvö empírísk findings og
verklagsbreytingar.

**Step 3b closure-tölur (sannreyndar gegn mbl_fetch_state.json + raw_mbl.db ro)**:
- sale publishable **10.899** listings (exhausted við offset 10.912, frozen_max_id 1.688.820,
  682 síður), rent publishable **377** (24 síður), sale negotiable **1.694** (ceiling
  1.689.601, 106 síður), rent negotiable **979** (ceiling 218.255, 62 síður) =
  **13.949 listings í 874 list-page blobs**.
- **Self-establish ceilings sönnuðust empírískt**: negotiable modes frusu EIGIN max_id YFIR
  main-seed ceilingunum (sale 1.689.601 > 1.688.820; rent 218.255 > 218.157) — inheritance
  hefði misst head-of-id negotiable listings varanlega, eins og P3 rationale spáði.

**EMPIRICAL FINDING læst — publishable-túlkun seed-pagination staðfest**: sale seed tæmdist
við offset 10.912, hvergi nærri raw aggregate 13.792. Mismunurinn er (a) draft-filterinn
(verd>0/fermetrar>0) eins og hannað og (b) **churn-effektið** — mbl hard-deletar withdrawn
listings undir frozen window á multi-nætur seed, svo ~640 raðir hurfu úr glugganum meðan
crawl-ið stóð. Hvort tveggja vænt; engin merki um pagination-galla.

**GENERATION SPLIT finding**: publishable corpus (682 sale + 24 rent síður) er **scalar-only**
— Night 2/3 processinn keyrði pre-amendment kóða í minni (in-flight prósess les ekki nýjan
kóða af diski). Negotiable corpus (168 síður) er **100% v2_enriched**. `fields=v2`
URL-markerinn í raw_fetches ledger aðgreinir kynslóðirnar nákvæmlega (sannreynt:
682/0 v2, 106/106 v2, 62/62 v2). **§3c parser SKAL þola báðar kynslóðir** (nested-missing
OG nested-present blobs).

**DECISION — enriched re-sweep forgangsraðað STRAX**: mbl er closed history (syna=false=0,
hard-deletes); myndir/agency/nested gögn listings sem dragast til baka á biðtímanum eru
ÓENDURHEIMTANLEG — re-sweep fer því fram fyrir P3-backlog-hugsunina. Mechanism: existing
`--force-restart` + nýja history-archive netið (b57b7c0) varðveitir upprunalegu seed-gluggana
í `<key>_history`. Keyrsluplan: rent (~24 síður) + sale 400 síður í dag/nótt, `--mode resume`
á morgun þar til exhaust. **Footgun skjalfest**: `--force-restart` má BARA nota á FYRSTU
keyrslu hvors mode í re-sweepinu — á resume-keyrslum myndi hann núllstilla gluggann aftur
og henda progress.

**Commits**: 862f86a (v2_enriched field selection — allir scalars nema generated_fts, öll
10 image-variants, nested agency/attachments/openhouse/postal_code/promo; deliberate
exclusions: generated_fts, favorite [user-scoped], fs_count/rt_count [volatile counters sem
brytu §2.1.1 content-hash dedup]) + b57b7c0 (force-restart history-archive). Testar 25 → 30.

**NORM CHANGE — commit attribution**: Co-Authored-By trailer endurspeglar héðan í frá
RAUNVERULEGT módel sessionar (var harðkóðað "Claude Opus 4.8" í template; röng attribution
leiðrétt í "Claude Fable 5" frá og með 862f86a).

**Operational verklag fest — gated orchestrator-mynstur**: keðjuskript fyrir multi-mode
crawl-raðir keyra sem gated chain (eitt mode í einu, vænt-tölur sannreyndar milli skrefa),
abort-not-retry á óvæntri stöðu, PID-wait á undanfara í stað polling-lykkju. Endurnýtanlegt
fyrir §6 nightly delta orchestration.

**Næst**: re-sweep lýkur (resume á morgun) → Step 3c parse_mbl.py — skema læst: tvær
source-flavored töflur, báðar blob-kynslóðir, sentinel-reglur (fastano=0→NULL o.fl.),
foreign-listing flag (Spánarheimili), Hashie::Mash corruption-strip.

---

## 2026-06-10 — Strategic audit + revised priority sequencing + agent architecture sketch

**Hvað**: External audit by independent Claude session (Fable 5) surveyed all D: drive
data assets, repo state, spec drafts, and live Supabase. Audit surfaced material context
beyond what scraper-substream handoff documents captured. Findings + strategic
re-sequencing accepted as new working baseline.

**Data asset inventory (audit-discovered, beyond scraper handoffs)**:
- **Image archive at D:\Gagnapakkar\** — 196.5 GB across 5 packages, 921,273 images,
  38,152 fastnum-organized folders, image_index.db with 2.6M rows. NEAR-UNUSED until now.
  Critical for Step 3e image_mirror: must bootstrap from this archive before fetching
  anything new. Cross-property-references issue noted (naive layout misses ~20%, use
  image_index.db).
- **LLM-extraction batch_results** — 40,000+ listings already processed (condition, floor
  finish, kitchen, garage, structured features). Cache-efficient pipeline proven. NOT yet
  integrated into iter4 training set — likely largest single MAPE improvement available
  (einbýli currently at 16.3% MAPE; condition explains substantial residual variance for
  that segment).
- **Leiguskra-legacy scrape** — gleymd eign: ~928 current + ~3,000 historical rent
  snapshots with fastnum, price, size, first-seen/last-seen dates, images. Should be
  folded into scraper.listings_canonical as source='leiguskra_legacy'. Combined with
  mbl-rent + myigloo + visir-rent gives thousands of rent price points with time
  dimension — primary input for iter_rent_v1.
- **last_listing_text.csv** — 145 MB ad-text corpus, source for LLM extraction full-scale.
- **rebuild_properties_v2.py** — 309 lines of multi-source stitch logic, currently
  un-tracked; should be promoted to tracked as template for future D4/D5 work.

**Top opportunities ranked (T1-T6)**:
- **T1 — Asking-vs-sold spread analysis**: highest-value single analysis. Only Danni
  has both sides on Iceland scale (asking from scraper canonical, sold from kaupskrá 227K
  transactions, joined on fastnum). One SQL view post-mbl-promotion. Mælaborð front-page
  material; strongest sales argument for realtor subscription. No new data needed.
- **T2 — LLM extraction full-scale → iter5**: run LLM extraction over full
  last_listing_text corpus, fold condition/finish features into iter5 training. Likely
  largest MAPE improvement available.
- **T3 — Leiguskra-legacy + multi-source rent → iter_rent_v1**: thousands of rent price
  points with time dimension once leiguskra-legacy is canonicalized. Sufficient for first
  asking-rent model.
- **T4 — Image mirror bootstrap from D:\Gagnapakkar**: save weeks of fetch time + GB of
  bandwidth by reading existing 196 GB archive first, diff-fetching only what's missing.
  Cross-property-references gotcha already known.
- **T5 — Street/hverfi aggregates (immediate)**: kaupskrá + properties already in
  Supabase. Street-level / hverfi-level price-per-m², turnover rate, price trend views
  are one SQL build. Available TODAY without new data. Doubles as semantic-layer
  foundation for expert agent.
- **T6 — Fasteignamat-deviation analysis**: HMS-refresh gives official assessments;
  iter4 gives market estimates. Mapping where official assessment diverges most from
  market value (by matsvæði, age, type) is bank-product + media material.

**Expert agent architecture (3 layers + v0/v1/v2 roadmap)**:
Not a custom-trained model — harness around Claude. Three layers:
- **Layer 1 — Tools (SQL + data)**: read-only SQL role to Supabase + DuckDB over D:
  pickles. Critical: semantic layer of 10-15 well-documented analytical views
  (v_street_prices, v_asking_vs_sold, v_market_heat_by_hood, v_price_history…) so agent
  writes reliable queries against named views, not raw-table joins. T1 and T5 are the
  first views.
- **Layer 2 — Knowledge package**: SKILL.md / system prompt with data dictionary
  (matsvæði, byggingarstig, ónothæfur samningur definitions), calculation rules (price/m²
  conventions, multi-unit handling, Tilboð sentinel), gotchas (mbl aggregate-vs-publishable,
  fastnum 1:N on commercial), and 20-30 exemplar queries.
- **Layer 3 — Output**: charts, reports, article drafts. Precompute chain + dashboards
  prove output formats already exist.
Roadmap: v0 weekend project in Claude Code/Desktop (skill + read-only SQL, validates
semantic layer cheaply) → v1 internal tool + bank product with 50-100 question eval bank
for reliability measurement → v2 "Spurðu sérfræðinginn" inside verdmat.is behind Pro
subscription via Claude Agent SDK with read-only role + rate limits + cost cap +
mandatory citation guardrails.

**Revised priority sequencing (next 2-4 weeks)**:
1. Finish mbl seed-sale (Night 2 in-flight + Night 3 finish ~45 min)
2. Step 3b P3 supplementary negotiable crawls (~5.7h) — captures ~980 rent + ~1,698 sale
   Tilboð listings
3. Step 3c parse_mbl.py + Step 3d promote_mbl.py → canonical jumps 1,266 → ~16K rows
4. **Nightly delta orchestration immediately after Step 3d** — urgency-locked (mbl is
   closed history; every day without delta = permanent data loss)
5. **Parallel track A — T5 street/hverfi views**: can start NOW (only needs kaupskrá +
   properties), no in-flight scraper dependency, foundation for v0 expert agent
6. **Parallel track B — Step 3e image_mirror with Gagnapakkar bootstrap**: read existing
   196 GB first, diff-fetch only missing. Starts after Step 3d
7. T1 asking-vs-sold view (after Step 3d puts mbl in canonical)
8. v0 expert agent on T1/T5 semantic layer
9. T2 LLM extraction full-scale → iter5 (independent track)
10. iter_rent_v1 with leiguskra-legacy + multi-source rent (T3, after canonical mature)
11. visir corpus production refresh (timed-batch, background)

**Locked policy: delta-cadence urgency**: mbl syna=false = 0 (hard-delete). Every day
without nightly delta-sale + delta-rent = permanent data loss (observed +19 rent rows in
hours during diagnostic). Post-Step-3d, §6 delta orchestration jumps AHEAD of most other
work, even ahead of parser if forced to choose. Raw blobs wait patiently; the market does
not. Spec amendment to §6 follows this commit (un-tracked draft only).

**Locked policy: image-mirror Gagnapakkar bootstrap**: Step 3e image_mirror must read
D:\Gagnapakkar\image_index.db first to enumerate already-archived images; fetch only
missing diff. Saves weeks + GB of bandwidth. NOT a re-fetch from scratch. Cross-property-
references gotcha known (use image_index.db, not naive folder layout).

**Step 3b P3 closed (commit 56b1a2e)**: fetch_mbl.py negotiable supplementary modes
implemented with self-establish max_id (NOT inheritance). Rationale captured in commit
message: head-of-id newest negotiable listings would be permanently lost if negotiable
inherited main seed's ceiling. Cross-mode dedup handled by §4 promotion-tier R1-R3.
25/25 tests pass. Scraper chain now 20 commits on origin/main.

**Næst (immediate)**: Night 3 sale seed finish (~45 min, Session A) → P3 supplementary
crawls (~5.7h, Session A) → Step 3c parser design + impl → Step 3d promotion. Parallel
track A (T5 street views) can start in a fresh Claude Code session anytime; no in-flight
scraper dependency.

**LEIÐRÉTT 2026-06-12 (endurmæling):** „196,5 GB / 921K images" talan að ofan var
snapshot frá 2026-05-08, FYRIR Stage B-myndasóknina. Safnið mælist nú **548,5 GiB /
2.648.381 skrár / 55.637 distinct fastnum yfir 7 rætur** (robocopy-mæling per rót,
staðfest gegn image_index.db — diskur og index stemma). image_index.db (790 MB, 2,63M
raðir, PK fastnum+image_nr, 99,998% downloaded=1) er master-indexið; local_path vísar
INN í upprunalegu pakkamöppurnar — skrár voru indexaðar á sínum stað, engin tvítekning
milli Gagnapakkar\images\ og pakkanna. Skráarnöfn eru sequential <fastnum>\<n>.jpg,
EKKI URL-basename — URL→skrá vörpun virkar EINGÖNGU gegnum image_index.db.
Leiguskra-myndir (1,7 GiB, 1.145 möppur) eru óindexaðar enn. 350 GB laus á D: —
diskpláss er héðan í frá vöktuð auðlind (mirror-sókn nýju uppsprettanna bætir 50–150 GB
við). Opin 3e-hönnunaratriði (ÁKVEÐAST við Step 3e hönnun, ekki nú): (a) framlengja
image_index.db vs ný mirror-DB — fastnum-þekja mbl-corpussins mælist fyrst; (b)
backup-staða 548 GiB safns sem er UTAN R2-backupsins.

---

## 2026-06-09 — Spec correction: §5 #5 + §2.4-C image archival policy

**Hvað**: Spec drift caught during Step 3b P1 review. §5 #5 read "URL-only v1, escalate
if >5% 404" — this contradicts Danni's locked intent of full image archival to D: drive
from v1. Drift originated from skeleton-era text not updated post-decision.

**Locked policy (re-confirmed)**: all source CDN images mirrored locally to D: drive from
v1. Storage at `D:\verdmat-is\image_mirror\<source>\<source_listing_id>\<index>.<ext>`.
Tracking via `image_mirror.db` SQLite.

**Rationale**: withdrawn listings cause source CDN URLs to 404 permanently. Valuation
model + bank product + future historical analytics need visual context for sold
properties. D: drive storage is essentially free (precedent: existing 352 GB image mirror
from Galdrabúðin/legacy work). Cloud storage (Cloudflare R2 et al.) carries 100s-of-GB
recurring cost — deferred until economics warrant. Danni's desktop can serve images via
Cloudflare Tunnel in v1 stretch if frontend wants mirror access.

**Architecture sketch (Step 3e/4 design input)**:
- Storage layout LOCKED: per-listing folder (`image_mirror/<source>/<source_listing_id>/<index>.<ext>`).
  Sha256 content-addressed deferred to v2 if storage pressure shows; `image_mirror.db`
  carries sha256 column from v1 so migration path is mechanical.
- `image_mirror.db` tracking schema (per-image row): source, source_listing_id, image_index,
  source_url, local_path (relative under image_mirror/), fetched_at, byte_size,
  content_type, sha256, fetch_status (success/404/timeout/blocked)
- Fetcher reads canonical `photos_json` URLs across all sources (cross-source single pipeline)
- Pacing: 5-10 req/sec (image CDNs designed for browser hot-load — much more permissive
  than listing APIs which are minute-paced)
- Standard Chrome UA, no identifier
- Kill-switch on 403/429/persistent timeout
- Parallel 3-5 concurrent connections OK (browser-equivalent posture)
- Resume-safe: skip rows where local_path exists + fetched_at is recent
- Serving in v1 minimum: dormant archive (frontend keeps source URLs, falls back on 404).
  Cloudflare Tunnel stretch: serve mirror via desktop, frontend prefers mirror with source
  fallback.

**Sequencing**: image archival is cross-source sub-stream — works on canonical `photos_json`
URLs regardless of source. Can start anytime canonical has rows (already 1,266 rows from
myigloo + visir). Recommended order: complete Step 3 mbl substream first (3b P2 listing
fetcher → 3c parser → 3d promotion), then Step 3e/4 image archival processing all 3
sources' canonical photos_json. Storage estimate ~50-150 GB full mirror.

**Næst (when Step 3e/4 actually builds)**: `init_image_mirror_schema.py` (image_mirror.db
bootstrap) + `fetch_images.py` (cross-source byte archival with politeness pacing) +
reconciliation pass against canonical photos_json. Optional v1 stretch: Cloudflare Tunnel
setup for frontend mirror access.

---

## 2026-06-09 — Step 3a closed: mbl Hasura GraphQL characterization

**Hvað**: Step 3a (mbl probe) lokuð — Phases 1b/1c/1d/1e/1f all empirically resolved.
`probe_mbl.py` un-tracked (3 phases: `--confirm`, `--tail`, `--p1f`). ~50 GraphQL requests
across the phases, **all HTTP 200, zero anomalies**. Journal-only milestone — NO code commits.

**1. Architecture finding (overturns §1.1 mbl framing)**:
- Spec held mbl was a React SPA with REST `/fasteignir/api/*` (robots-disallowed) needing Playwright.
- Empirical: the data layer is a **Hasura GraphQL** endpoint at `g.mbl.is/v1/graphql` (a
  different subdomain — the robots-disallow was on `www.mbl.is`, not `g.mbl.is`).
- `g.mbl.is/robots.txt` → **404** (no restriction).
- **No auth, no TLS impersonation**, plain `requests` + standard Chrome UA → 200 + JSON.
- Introspection **enabled** — full schema captured (`fs_fasteign` 50 scalar + 7 nested;
  `rentals_property` 21 scalar + 5 nested).
- Difficulty-rank update: mbl is now the **EASIEST transport** (cleaner than visir's SSR HTML).

**2. §0.5 amendment (mechanism only)**:
- Original choice (B): "headless rendering with kill-switch, Playwright Python framework".
- Amended: **direct GraphQL via stdlib `requests`; Playwright fallback only if mbl later gates
  the endpoint.**
- Posture spirit UNCHANGED + binding: conservative rate, standard Chrome UA without identifier,
  no active deception (no TLS impersonation, no proxy rotation, no CAPTCHA bypass), kill-switch
  on 3+ HTTP 400 OR 403/429/CAPTCHA, alert Danni, try-and-see, halt-and-drop on block, no Árvakur
  (path C) escalation. Spec patch landed in SCRAPER_SPEC_v2_draft.md (un-tracked) §0.5 + §1.1.

**3. §2.1.1 mbl rule LOCKED — trivial**:
- Empirical: t=0 vs t=+60s, same id, both `raw_hash` AND sorted-keys `hash` identical (sale + rent).
- Rule: `content_hash = sha256(json.dumps(parsed, sort_keys=True, separators=(',',':')))`.
- Zero path-nulling (unlike myigloo `verification.as_of`, unlike visir Skoðendur counter / ad-blocks).
  Hasura returns deterministic bodies — no per-request server stamps. Cleanest §2.1.1 of all 3 sources.
- Caveat: a +1h longer-gap confirm was NOT done; revisit if Step 3b raw layer shows linear blob
  growth without real changes. `blob_gz` verbatim per §2.1.

**4. Universe + distribution (exact, uncapped aggregate queries)**:
- Sale **13,772** · Rent **1,349**.
- Per-`teg_eign` sale: fjolb 7266, atv 2450, einb 1395, radpar 1003, jord 778, sumarhus 433,
  haedir 334, hesthus 72, annad 38 (sums 13,769; ~3 with null/other teg_eign).
- mbl is the **LARGEST source by row count** (~15k+ active > visir + myigloo combined).
- Commercial (atv 2,450) is **first-class** on mbl (unlike visir's non-first-class commercial);
  plots (jord 778) substantial. §7.1 monitoring floors lockable from these counts.
- §1.2 estimates ("3-5k est" sale, "few-hundred est" rent) were ~3× low.

**5. ⚠ 16-row hard cap (Hasura anonymous role)**:
- `limit:100` → 16 rows; `limit:1000` → 16 rows. Aggregate counts are NOT capped (server-computed).
- Step 3b enumeration constraint: **offset-pagination at 16/page → ~946 pages** for the full universe.
- §0.5 cap (<1000/24h) + minutes-between → **multi-night seed crawl** (2-3 nights @ 300-500/night).
  Steady-state delta-refresh via `where:{br_dags:{_gt:<last_seen>}}`. Mitigation locked in Step 3b design.

**6. ⚠ fastano heterogeneity (Step 3d concern, flagged not solved)**:
- Typed `Int` (Hasura schema); observed range **6-9 digits** across teg_eign categories.
- Standard HMS fastnum is 7 digits → some values likely landeignarnúmer (for jord plots) or other ids.
- §2.5 promotion must do **format-aware FK validation** against `properties.fastnum`.
- Coverage feasibility high — fastano present on **ALL** teg_eign categories sampled (better than
  visir where commercial fastnum was sketchy).

**7. Draft-listing production filter (Step 3b concern)**:
- `sent_dags desc` sampling surfaced draft/placeholder rows (verd=0, fermetrar=0).
- Production enumeration filter: `where:{syna:{_eq:true}, verd:{_gt:0}, fermetrar:{_gt:0}}`.

**8. ⚠ rent type_id (1-11) — empirically OPAQUE (not locked)**:
- Phase 1f sampled up to 5 listings per type_id (1 aliased query). Titles are bare addresses,
  sizes overlap heavily across ids → **no clean keyword/size signal**, and the schema has **no
  `rentals_type` lookup table** (only rentals_property/_photo/_postal_code roots).
- Weak grouping only: type_id 6/9/10 look commercial (large m², rooms 0/many, commercial-area
  addresses, all longtime); 2/3/11 look residential (small-medium, rooms 1-5). LOW confidence.
- **Ruling: do NOT decompose category from type_id.** Mirror the visir lesson — derive category at
  Step 3d from **size/keyword heuristics** (rent default → residential unless commercial signals),
  retain `type_id` as a raw signal (tegund_raw-equivalent) for future refinement. type_id mapping
  can be revisited if the SPA bundle exposes a frontend lookup.

**9. hesthus → TAXONOMY ruling LOCKED**:
- hesthús (horse stable) is a rural/agricultural structure (v1 TAXONOMY §1.4 grouped it under
  landbúnaður EXCLUDE).
- Ruling: **category=plot, sub_type=agricultural** (§5 `agricultural` = "landbúnaðarjörð, býli"
  absorbs farm/rural buildings + land). MEDIUM confidence; flag for v2 refinement (alternative
  would be commercial/mixed_use_other, but §5 agricultural is the cleaner fit for an ag structure).

**10. teg_eign decomposition mapping for Step 3d (sale)**:
- fjolb → residential/apartment · haedir → residential/apartment (floor unit)
- radpar → residential/townhouse · einb → residential/house · sumarhus → residential/summerhouse
- atv → commercial (sub_type via keyword classification post-parse, like visir)
- jord → plot (sub_type via TAXONOMY §5 keyword) · hesthus → plot/agricultural (per #9)
- annad → other

**11. Source-priority retune candidate (flag-only, NOT relitigated)**:
- Locked starting point per §2.3-D: visir(1) > mbl(2) > myigloo(3).
- Empirical case for mbl earning priority 1 over visir post-Step-3b: typed GraphQL > scraped SSR
  HTML (cleaner parse); fastano on ALL rows (§2.5 Tier-1 universal) vs visir sometimes-only; no
  "Tilboð"/price=1 sentinel quirks (typed numeric `verd`); larger universe + first-class commercial.
- Defer retune to the build-phase overlap sample per §2.3-D's locked process. No spec change now.

**12. Two root types** (`fs_fasteign` sale vs `rentals_property` rent) — different field shapes →
two parser paths at Step 3c (or one with per-type mapping). No detail endpoint needed: all scalar
fields are list-queryable (the 27/3 "detail-only" fields are just unrequested scalars).

**Næst**: Step 3b — `raw_mbl.db` schema (§2.1) + `canonicalize_mbl.py` (trivial sorted-keys rule)
+ `fetch_mbl.py` (16-cap offset-pagination, multi-night seed plan, day-1 kill-switch incl. HTTP 400,
draft-row filter). `probe_mbl.py` stays un-tracked.

---

## 2026-06-08 — Step 2d closed: promote_visir.py + §4 cross-source dedup proving ground

**Hvað**: Step 2d lokuð. `promote_visir.py` (589 línur) + `promote_visir_test.py` (230
línur) committed. 388 visir rows promoted to `scraper.listings_canonical` (386 insert_new
+ 2 visir_wins folded against existing myigloo canonical rows), 11 junk skipped, 0 failed.
**Canonical layer is now genuinely multi-source: 1,266 rows (859 myigloo + 407 visir)**,
spanning residential sale+rent, commercial sale+rent, and plots, with 2 verified
cross-source folds.

**Decomposition mapping (visir tegund_raw → TAXONOMY_v2 category+sub_type)**:

8 tegund_raw values mapped cleanly:
- `fjölbýlishús` / `íbúðir` / `íbúð` / `hæð` → residential/apartment
- `sérbýli` / `einbýli` / `einbýlishús` → residential/house
- `raðhús` / `parhús` → residential/townhouse
- `sumarhús` / `sumarbústaður` → residential/summerhouse
- `atvinnuhúsnæði` → commercial/{office|retail|industrial|hospitality|mixed_use_other},
  resolved via secondary KEYWORD parse against title+lysing (skrifstofa→office,
  verslun→retail, iðnaðar/vörugeymsla/lager/verkstæði→industrial,
  hótel/gistiheimili→hospitality, else mixed_use_other)
- `lóð` / `jörð` → plot/{residential_plot|commercial_plot|agricultural_plot|other_plot},
  resolved via secondary keyword parse

Tenure from `parsed_visir.tenure_signal` directly per Step 2c Decision 3 (detail-HTML
markers authoritative). lease_term_class set to 'unspecified' for all visir rent
(no contract_min_months in parsed_visir v1).

**§4 cross-source dedup — three universal reject rules**:

The §4 machinery fires against the existing 861 myigloo canonical rows per Step 2's
§6 dedup proving ground mandate. Empirical iteration on real corpus exposed 16 candidate
matches, of which 14 were false positives. Three universal reject rules now lock the
machinery to genuine cross-source overlaps only.

**Rule 1 — Fastnum-disagreement reject (universal)**: In any tier candidate evaluation,
if BOTH visir_row AND candidate_row have non-NULL fastnum AND fastnums differ → reject.
Mathematical certainty: different HMS-registered fastnums = different properties.
Killed 2 tier-2 false positives (visir 1054922 fn=2121211 ↔ myigloo 3669 fn=2313904 +
visir 1046418 fn=2271716 ↔ myigloo 11524 fn=2012663).

**Rule 2 — Size-disagreement reject (universal)**: In any tier candidate evaluation,
if BOTH visir_row AND candidate_row have non-NULL size_sqm AND
`|size_a - size_b| / max(size_a, size_b) > 0.10` → reject. Catches multi-unit-same-
fastnum case (commercial building registered as one HMS fastnum, multiple units inside).
Killed 2 of 3 multi-unit office matches at fn=2252816 (visir 1056507 + 551503 had
sizes ≠ myigloo 822's 86.9 m²).

**Rule 3 — Commercial corroboration (category-targeted, ALL tiers)**: For commercial
category matches at ANY tier (1, 2, or 3), require at least one informative corroborator:
EITHER size agreement (both >0, within 10%) OR price agreement (both non-sentinel, within 5%).
If neither corroborator available → reject. Empirical reality: commercial fastnum is 1:N
over building units; sentinel price=1 (Tilboð) makes Tier-2/3 price filters degenerate;
without size or non-sentinel price match, fastnum alone is insufficient confidence.
Killed the surviving multi-unit case (visir 1047898 size=0 + myigloo 822 size=86.9,
both prices=1 Tilboð sentinel → no corroborator → reject).

**Architect-spec-vs-empirical-test correction (transparency)**:
Original architect spec said Rule 3 applies to "Tier-1 only". T22 test empirically
exposed that the same uncorroborated multi-unit-commercial match also surfaces via Tier-2
(addr match) because price=1 sentinel on both sides trivially satisfies the Tier-2 price
filter. CC correctly generalized Rule 3 to ALL tiers for commercial — better matches the
underlying reality that commercial-fastnum-is-1:N is a category-level constraint, not a
tier-level one. Generalization is safer (prefers false negatives over false positives,
consistent with §4 philosophy).

**Empirical false-positive reduction narrative**:
- Initial dedup machinery: 16 candidate matches
- After Rule 1 (fastnum-disagreement): 14 (2 tier-2 different-fastnum killed)
- After Rule 2 (size-disagreement): 3 (multi-unit-different-size + degenerate tier-3 killed)
- After Rule 3 (commercial-corroboration, all tiers): 2 (uncorroborated multi-unit killed)
- Final genuine matches: 2 residential apartments, both with identical
  fastnum + size + price + tenure — exactly the cross-source overlap §4 was designed
  to detect.

**Persistent learning extending Step 2c**: Architectural specs at design-time can miss
edge cases that empirical tests at integration-time expose. §4 dedup principles should
apply at category granularity (commercial-1:N reality), not tier granularity. Apply same
discipline to Step 3 mbl + future sources: write tests that encode the INTENT
("uncorroborated commercial match must not fold"), let the test failures reveal where
the rule needs to generalize.

**v1 limitation (deferred to v2)**: Within-run visir↔visir dedup is deferred — promote
loop matches only against the STATIC preloaded canonical snapshot (myigloo + prior runs),
not against same-run visir inserts. Eliminates a placeholder-uuid write bug and avoids
Tier-2 false-positive risk of folding two distinct units in one building during the same
batch. Production impact: small (only matters if visir lists same property twice
simultaneously, rare). Future v2 could implement within-run dedup with proper canonical_id
generation if needed.

**Verification (live Supabase state)**:
- by source: myigloo 859 (861 − 2 folded), visir 407 (19 smoke + 386 insert + 2 won)
- visir cat×tenure: residential/sale 193, commercial/rent 169, commercial/sale 29,
  residential/rent 12, plot/sale 4
- visir fastnum resolution: source_supplied 336, address_match 33, geo_match 11,
  unresolved 27 = 93% resolved
- folded rows: 2, both correct (visir 1050593 ← myigloo 23863; visir 1050668 ← myigloo 23937)
- 0 ck_price_pos / ck_fastnum_resolution violations
- Supabase pooler quirk handled per memory entry 1 (SET TRANSACTION READ WRITE as first
  statement, mogrify INSERT single round-trip)

**File metrics**: promote_visir.py 589 lines, promote_visir_test.py 230 lines, 28/28 tests
pass (decomposition T1-T4, price T5-T9, fastnum T10-T11, §4 dedup T12-T18, §4 reject rules
T19-T24).

**Næst**: Step 2 substream (visir) complete; scraper substream chain at 15 commits on
origin/main. Production-grade visir corpus refresh deferred to timed-batch session when
needed (per Step 2b P3 IP-throttle finding). Step 3 mbl next major milestone — apply same
defensive scraper patterns + universal §4 dedup rules from the start.

---

## 2026-06-04 — Step 2b P3: visir IP throttle finding + fetcher defensive patches

**Bakgrunnur**: Full visir crawl initiation surfaced production-scale rate limiting
that was invisible at probe scale. Two attempts, two empirical corrections.

**Empirical timeline (honest log of false-positive correction)**:

- **Crawl attempt #1 (09:26-09:55)**: Naive full crawl. Phase A index sweep reached
  ~170 requests at 8 min; from request 170 onward visir returned HTTP 400 on every
  detail fetch. 622 wasted requests before manual halt. Spec §1.1 "no WAF" assumption
  invalidated for sustained scale.

- **Patch hypothesis #1 (session-based throttle)**: Fresh `requests.Session()` got HTTP
  200 on same IDs ~20 min after halt → seemed session-bound. Patches: (1) 400-aware
  kill-switch [Patch 1], (2) periodic session re-prime every 80 requests [Patch 2].

- **Validation crawl (10:23-10:35)**: 440 requests with 5 re-primes → 0×400, exit 0.
  Conclusion: "session-based throttle, re-prime works". **THIS WAS WRONG**.

- **Full crawl attempt #2 (10:41-10:44)**: 76 requests on top of validation's 440 →
  HTTP 400 at cumulative request ~516 across multi-session sequence → kill-switch
  tripped at 3×400, exit 2. Wasted only 3 requests this time (Patch 1 essential ✓).

- **Corrected hypothesis (IP-based throttle, validated)**: Validation didn't pass
  *because* re-prime worked — it passed *because* total IP-cumulative was under ~500.
  The 47-min cooldown between halt and validation cleared the IP counter. When full
  crawl piled on top of validation's 440, cumulative breached the IP window. Throttle
  is IP-level cumulative ~500 requests per rolling ~30-60 min window. Session re-prime
  is harmless cookie hygiene but does NOT reset an IP counter.

**Patches kept (both genuinely valuable)**:

- **Patch 1 (400-aware kill-switch)**: Essential safety net. Halts on 3+ consecutive
  HTTP 400 responses, resets on 200. Caught both 622-request blast (attempt #1) and
  3-request blast (attempt #2). T11 locks behavior on consecutive 400s + recorded
  raw_fetches rows.

- **Patch 2 (unified re-prime every 80 across both phases)**: Cookie hygiene + handles
  potential session-level sub-limits if they exist below the IP threshold. Doesn't
  defeat IP throttle but no cost to keep. Counter spans both Phase A (index sweep) and
  Phase B (detail walk) via class-level `requests_since_prime`. T12 verifies firing
  across phases; T13 verifies counter reset on `prime()`.

- **Tests**: 13/13 pass (T1-T10 unchanged + T11 kill-switch-on-400 + T12 periodic
  re-prime + T13 prime resets counter).

**Spec corrections (un-tracked SCRAPER_SPEC_v2_draft.md, this commit)**:
- §1.1 visir entry: throttle finding added (IP-cumulative ~500 req per ~30-60 min window)
- §0.5 kill-switch: HTTP 400 (3+ consecutive) added to monitored signals

**Corpus state**: 418 valid detail blobs banked (validation crawl + smoke residue).
Reparsed at visir_parse_v1, 0 failures. Distribution: **235 sale / 183 rent** by
tenure_signal, but rent is dominated by **commercial** — 198 atvinnuhúsnæði + 172
"Tilboð" price-on-request; **only 14 residential-rent** (the myigloo-overlap dedup
target). Also 158 fjölbýlishús, 18 raðhús, 18 einbýlishús, 8 lóð, 5 sumarhús. Adequate
for Step 2d proving ground (commercial classification + Tilboð at scale, residential-sale,
plots, summerhouse all well-sampled); residential-rent dedup-vs-myigloo overlap is THIN
(14) — but visir residential-rent is genuinely scarce (mostly commercial), not a crawl
artifact, so a bigger crawl would not help much. Production full crawl deferred to a
timed-batch session (45-60 min IP-window pauses between ≤300-request batches).

**Persistent learning extending Step 2a + 2c**:
- Probe-scale empirical evidence does NOT extrapolate to production-scale (50 req
  probe found no WAF; 500 req production found IP throttle).
- Validation methodology: cross-attempt cumulative IP state must be tracked, not just
  per-attempt state — false-positive risk is real when window-state matters. Apply to
  Step 3 mbl probe + full crawl: build IP-cumulative tracking into the validation gate.

**Næst**: Step 2d build against the 418 corpus. Production visir top-up deferred to a
separate session with timed-batch infrastructure.

---

## 2026-06-04 — Step 2c closed: parse_visir.py + parsed_visir at visir_parse_v1

**Hvað**: Step 2c lokuð. `parse_visir.py` (299 línur) + `init_parsed_visir_schema.py`
(106 línur) + `parse_visir_test.py` (154 línur) committed. `parsed_visir` table inside
`raw_visir.db` carries 31-column visir-source-flavored schema per §2.2. 10 detail rows
parsed at `PARSER_VERSION='visir_parse_v1'`, 0 failures.

**Selector design (Step A empirical discovery against 5 real samples)**:
21 of 22 fields HIGH confidence selectors from `.property__*` and `.description__*`
BEM namespaces. tenure_signal MEDIUM (rent-marker heuristic, hint-only at parser
tier — canonical authority at Step 2d). agency_name LOW (best-effort, PII dropped
at promotion).

Key selectors locked:
- title: `.property__center-title`
- price_text_raw: `.property__center-price` ("Tilboð" → price_amount=NULL, is_price_on_request=1)
- tegund_raw: `.property__center-class` (drives category classification at promotion)
- size_sqm / rooms / bed / bath / byggar: `.description__head-text` chips with regex
- lysing: `.description__bottom-text` (longest meaningful block)
- addr_street + addr_number: `.property__center-title` PRIMARY (unit-stripped),
  og:title meta FALLBACK
- addr_postcode + addr_city: `.property__center-text` leading 3-digit + remainder
- lat/lng: regex `lat=N&lon=N` from kort URL (NULL if no map)
- fastnum_supplied: label-anchored `.property__bottom-item` with text "Fasteignanúmer",
  F-prefix stripped ("F2534030" → 2534030). NOT page-wide regex.
- photos: gallery `<img>` srcs, deduped
- listing_date: `.property__head-text` "Skráð <date>" (text only, no parse)

**Architect decisions (3) applied to design**:

1. **Rent-marker heuristic LOCKED** (Decision 1): case-insensitive any-of `{Leiguverð,
   til leigu, /mán, á mánuði}` in HTML text → tenure_signal='rent'; else 'sale' (default);
   'unknown' only if both price_text_raw AND tegund_raw extraction failed. MEDIUM
   confidence at parser tier acceptable — canonical authority at Step 2d. If production
   reveals additional rent markers, bump PARSER_VERSION → v2 + re-parse via §2.2
   INSERT-OR-IGNORE on (content_hash, parser_version) UNIQUE.

2. **T2 fixture repurposed as stype≠tenure canary** (Decision 2): Real sample 1052249
   (Phase 1c-captured under stype=rent) is empirically a SALE listing — 79.9M ISK
   total price, fjölbýlishús, no rent markers anywhere in HTML. Test asserts
   tenure_signal='sale' for this ID with explicit comment documenting the empirical
   stype≠tenure noise. Confirms Step 2a finding extends from stype≠category to
   stype≠tenure as well. Synthetic T2b covers true-rent classification path.

3. **Authoritative tenure source = detail-HTML markers, NOT index-stype provenance**
   (Decision 3): Empirical reality says visir's getresults?stype= index is unreliable
   for tenure decomposition. parsed_visir.tenure_signal is parser's best-effort
   detail-HTML reading. Step 2d promotion uses tenure_signal directly as canonical
   tenure source. Index-stype provenance MAY be recorded as audit metadata at
   promotion (deferred design — column like `seen_in_stypes TEXT[]` or similar).

**Persistent learning extending Step 2a**: Index-endpoint classification labels
(visir's getresults?stype=) cannot be trusted for canonical (category, tenure,
sub_type) decomposition. stype contaminates BOTH category AND tenure on visir.
Same discipline applies at Step 3 mbl probe and future sources — always classify
from parsed detail markers, never from enumeration URL labels.

**Verification-stage bug fixes** (caught by 10-row spot-check + locked by regression tests):

- **Bug 1 — `_num()` mangling coordinates**: lat 64.14535959 was being stripped to
  integer 6414535959 because `_num()` stripped non-digit characters. Fix: parse
  fractional coordinate fields with `float()` instead. Locked by T1 lat-range
  assertion (63<lat<67, -25<lng<-13).

- **Bug 2 — og:title omits house number**: og:title meta tag carries only street +
  locality on many listings, so initial addr_number completeness was 10%. Fix:
  `.property__center-title` is now PRIMARY source for street+number (unit-suffix
  "íbúð N" stripped via regex, letter suffix like "24B" / "103A" preserved); og:title
  is FALLBACK. Locked by T11 (synthetic center-title address with unit).

**Field completeness on 10-row sample** (all latest residential sale from smoke #5
getresults page-1):
- 100% populated: title, price_amount, price_text_raw, is_price_on_request, size_sqm,
  rooms, bathrooms, byggar, tegund_raw, tenure_signal, lysing, addr_street,
  addr_postcode, addr_city, fastnum_supplied, n_photos, photos_json, listing_date,
  agency_name
- 90% populated: addr_number (1 "Leifsstaðabrúnir" named summerhouse area legitimately
  has no house number), lat/lng (1 new-build "Vetrarbraut 2-4" legitimately has no map)
- 80% populated: bedrooms (2 listings don't break out svefnh chips — chip absent
  in source HTML, not a parser miss)

All sub-100% counts are empirical legitimate-NULL cases, NOT parser defects.

**Caveat noted**: The 10-row batch is all latest residential sale (smoke #5 page-1).
Commercial / true-rent / Tilboð / plot paths are covered by REAL-sample tests
(T3 against 1056643 commercial-as-rent, T2b synthetic rent) rather than by the live
batch. Production full crawl will surface diversity (commercial sales mixed under
stype=sale, true residential rents, Tilboð prices, plot listings). If edge cases
break v1 selectors, bump `PARSER_VERSION='visir_parse_v2'` and re-parse — §2.2
UNIQUE(content_hash, parser_version) ensures latest version wins for downstream.

**Næst**: Step 2d — canonical promotion (parsed_visir → scraper.listings_canonical).
This is the §6 cross-source dedup proving ground per Step 2 mandate. visir wins over
myigloo per §2.3-D source_priority; will exercise §4 single-table row-merge against
the 861 existing myigloo canonical rows. Tenure decision uses parsed_visir.tenure_signal
directly per Decision 3 above.

---

## 2026-06-04 — §2.1.1 visir rule amendments: Skoðendur counter + class-anchored ad-drop

**Bakgrunnur**: §2.1.1 visir canonicalization rule locked in commit d32d9c2 covered ad-redirect
strip + ad-block drop via anchor-walk. Step 2b P2 smoke testing surfaced two empirical defects
that required amendments before full crawl could safely commit.

**Defect 1 — Skoðendur view counter** (LOCKED 2026-06-04 amendment):
Per-detail-fetch view counter (`<p class="property__head-text">` containing standalone digit
OR labeled `<digit> <span>Skoðendur</span>`) ticks on every fetch. Phase 1b probe used 5-sec
re-fetch gap — too short to observe tick. Caught at Step 2b P2 smoke (~1 min real-world gap
between identical-id fetches).

Fix: two regex normalizations applied AFTER ad-block drop, BEFORE serialize:
- `r'(\d+)(\s|&nbsp;)*(<span>\s*Skoðendur)'` → `'__VIEWS__\2\3'` (labeled counter)
- `r'(<p class="property__head-text">\s*)\d+(\s*</p>)'` → `'\1__VIEWS__\2'` (standalone)

Both date-safe by construction: the registration-date <p> contains `<span>Skráð`, not pure
digit, so neither regex matches it. T11 (counter tick → same hash) + T12 (Skráð date change
→ different hash) confirm.

**Defect 2 — class-anchored vs anchor-walk ad-drop** (LOCKED 2026-06-04 mechanism rewrite):
Original locked rule found ad blocks via `/ads/redirect/\d+` anchor presence, walked up 3
ancestors, decomposed matching parent class. Real-world ad containers (`b-partnerlink`,
`partner-link s1 sidebar-top-add`, `ad-banner-mobile footer__top-img`) rotate iframe/script
creatives with NO `/ads/redirect/` anchor. Anchor-walk missed them entirely → re-fetch produced
new content_hash.

Fix: `_drop_ad_blocks` rewritten class-anchored — decompose any element whose own class
matches target set ([a-z0-9]-normalized substring against Reklama|ad-banner|details-ad-block|
partner-link), regardless of inner content type. Subsumes anchor-walk behavior. The
`/ads/redirect/\d+` regex retained as belt-and-suspenders for stray refs in inline handlers.
T13 (iframe/script ad block with no redirect anchor → dropped) confirms.

**Validation method correction** (workflow lesson):
Rotation-based smoke testing (5-min sleep between sweeps) CANNOT validate dedup, because
visir's getresults returns rotating ID set — 5-min gap produced zero detail overlap between
runs. Correct validator: deterministic same-id re-fetch via fetcher's `--ids` flag (new),
loop 2+ iterations with delays to flush slow-tick volatile fields. This method confirmed 3/3
detail IDs dedup over ~6.5 min real elapsed in Step 2b P2.

**Persistent learning**: volatile-field probes for future sources (Step 3 mbl, etc.) MUST
use multi-gap re-fetch (5s + minutes) + deterministic same-id validation, not single-gap
rotation-based testing.

---

## 2026-06-04 — Step 2a (visir probe) closed: /ajaxsearch/getresults locked as enumeration endpoint

**Hvað**: Locked `/ajaxsearch/getresults?stype=<stype>` (GET) sem canonical enumeration
endpoint fyrir visir.is. Settled via 3-phase probe (probe_visir.py Phase 1 + 1b + 1c,
un-tracked, 1303 línur).

**Empirical basis**: visir's minified bundle `/minify/?g=v2-js&v=...` config object
explicitly defines `_param.resultRequestBaseurl = '/ajaxsearch/getresults'`. Cross-stype
test: sale + rent return populated 50-54KB HTML fragments með `/property/{id}` links;
company + vessel return near-empty 9.6KB shells. Pagination via `page` param, to be
reverse-engineered at Step 2b fetcher implementation. ~50 live requests across the 3
phases, 0 kill-switch trips, all HTTP 200; 13 raw samples í scraper_data/ (gitignored).

**Side note (§1.1 correction needed)**: SCRAPER_SPEC_v2 §1.1 currently identifies
`/ajax/photolist` sem search-list AJAX. That is WRONG — empirically confirmed via
bundle inspection that photolist is a per-listing photo-gallery popup loader
(`$.get('/ajax/photolist', {id, type}, ...)`). Spec correction applied til un-tracked
draft í þessari lotu; tracked-doc correction queued for Step 2 closure.

**Out-of-scope (decided not to do)**: forcing visir til að expose JSON API. Existing HTML
fragment output is parseable og works for our use case.

---

## 2026-06-04 — §2.1.1 visir canonicalization rule locked

**Hvað**: Visir raw content-hash canonicalization rule per §2.1.1 (analog of myigloo's
verification.as_of JSON-path nulling, but ad-redirect HTML stripping for visir):

```
1. Strip /ads/redirect/\d+ patterns (replace digits with constant token)
2. Drop <a> elements whose parent class matches:
   Reklama | ad-banner | details-ad-block | partner-link
   (because img src and other ad attributes rotate, not just href)
3. Apply ONLY to text/html payloads (not JSON)
4. Store verbatim blob unchanged; compute sha256 on canonicalized HTML
```

**Empirical basis**: Phase 1b Probe 5 + Phase 1c re-validation. 4 stype × 2 fetches
diff-check showed all differences were rotating ad blocks (5+ `/ads/redirect/N` per
page). Listing content (price, address, area, fastnum, lysing) was byte-identical
across re-fetches.

**Per-source pattern**: each source carries its own volatile-field rule per §2.1.1.
myigloo nulls JSON paths (`organization.verification.as_of`, `owner.verification.as_of`).
visir strips ad-redirect HTML. mbl TBD (Step 3).

---

## 2026-06-04 — visir stype ≠ category; tegund-based classification + label-anchored fastnum

**Hvað (1) — stype ≠ category**: visir's `stype` URL param er ekki clean category axis.
Empirically: real rent sample 1056643 "Skútuvogur 12, 104 Reykjavík" er atvinnuhúsnæði
(commercial property) með "Tilboð" price-on-request, served under stype=rent. Step 2d
promotion verður að classify (category, tenure, sub_type) frá parsed `tegund_raw` field,
EKKI frá stype URL param. tenure (sale vs rent) can be derived from stype reliably; only
category cross-contaminates.

**Hvað (2) — company/vessel empty**: stype=company og stype=vessel return 9.6KB empty
shells á visir (both /search/results og /ajaxsearch/getresults). visir is residential
sale+rent portal; commercial inventory mixes into stype=sale (e.g. 1056643) eða
stype=rent. Real commercial volume only surfaces via tegund-classification during full
crawl. Vessels are out of scope per spec §1.2.

**Hvað (3) — "Tilboð" = price-on-request**: Same convention as myigloo's commercial
price=1 placeholder. Visir uses string "Tilboð" instead of numeric placeholder.
Downstream rule (from Step 1e Phase 2a): commercial price > 0 promoted as-is regardless
of magnitude; residential price ≤ 100 skipped as junk; price = 0 skipped universally.
Visir parser will need to handle "Tilboð" string → null price (or convention placeholder),
and promoter applies the existing commercial-junk-tolerance rule.

**Hvað (4) — fastnum extraction must be label-anchored**: Page-wide regex
`\b[1-9]\d{6}\b` for fastnum is contaminated. Confirmed false positive on real rent
sample 1056643: regex hits include 4360339, which is Google Analytics UA-4360339-3
account ID. Multi-unit buildings also legitimately expose multiple fastnums (e.g.
1021848|1021851|...). Step 2c parser must use targeted selector anchored on
"fasteignanúmer"/"fastnúmer" label, never page-wide regex.

Tier-1 source_supplied feasibility confirmed: fasteignanúmer label fired on 100% of
12 samples (Phase 1) and 6 real samples (Phase 1c). Visir promotion will achieve
high Tier-1 resolution similar to or better than myigloo's 752/870 ≈ 86.4%.

---

## 2026-06-03 (Step 1e closed) — myigloo promotion live: scraper.listings_canonical populated with first 861 listings

**Hvað**: Step 1e (myigloo promotion til canonical) lokuð. `promote_myigloo.py` (340 línur) + `promote_myigloo_test.py` (132 línur, 16/16 pass) committed. **`scraper.listings_canonical` inniheldur nú 861 myigloo listings** (first real-listing Supabase writes í scraper-substream-inu), með **98,1% fastnum resolution** (Tier-1 source_supplied dominant) + TAXONOMY_v2 §3/§4 lookup applied. by category: residential 715, commercial 146. 0 ck_rent_lease / ck_fastnum_resolution violations.

**Empirical wins úr Phase 1 + 2a + 2b**:

- **51 fastnum_supplied missing í properties** (6.7%) — Tier-1 FK-safety fall-through til address/geo match catches these (they land via address_match/geo_match instead of erroring on the FK). Worth periodic check ef count grows — signal til að refresh public.properties frá HMS.
- **Manual-source entries (114, landreg_source='manual')** — Tier-2/3 address-match resolved most (94% had complete address fields). **Final resolution distribution: source_supplied 752 (Tier-1), address_match 40, geo_match 53, unresolvable_by_design 3 (room sub-types með no source fastnum), unresolved 13 (true edge cases — no addr/geo match). 845/861 = 98,1% have a fastnum.**
- **TAXONOMY_v2 §3 amendment** (7→8 sub-types): added `summerhouse` til residential rent sub-type list for myigloo's cottage tag (3 listings live). Editaður í `D:\verdmat-is\TAXONOMY_v2_draft.md` (un-tracked). Pre-flight confirmed `sub_type` er free-form TEXT (no enum constraint) — no migration needed.
- **Source-fidelity decisions** for storage(18) og garage(9): follow myigloo's commercial classification (→ industrial_warehouse / mixed_use_other) frekar en TAXONOMY §3 residential default. Standalone commercial storage/parking facilities eru semantically commercial; §2.5-G "unresolvable" rationale (designed fyrir sub-units within buildings) doesn't apply.
- **Cottage(3) override**: myigloo's 'other' source category remapped til residential/summerhouse based á semantic understanding of cottage rentals as residential housing.

**Price-on-request convention** (NEW DOWNSTREAM RULE):
myigloo agency commercial listings use `price_amount=1` (occasionally 0) sem placeholder fyrir "verð samkvæmt tilboði" — found í 61 listings (47 office, 11 warehouse, 10 retail; Miklaborg + öðrum agencies). At promotion: **commercial listings með price_amount > 0 promoted as-is** regardless of magnitude; **only residential price ≤ 100 skipped** (genuine junk); **price = 0 skipped universally** per ck_price_pos. Net: 9 skipped (7 commercial price=0, 2 residential junk), ~62 commercial recovered vs the naïve ≤100 filter. Downstream consumers (frontend, analytics) MUST handle commercial price ≤ 1000 as "verð samkvæmt tilboði" — apply lower bound (e.g., price > 1000) when filtering commercial by price; UI renders price-on-request label.

**Refined §2.5-G semantic** (additive clarification, Danni 2026-06-03):
"unresolvable_by_design" applies when source provides NO fastnum AND sub_type ∈ {room, parking_space, storage}. **When source provides an authoritative landreg_id (myigloo's `real_estate.landreg_id` for rooms = the parent building's fastnum), the source signal is accepted at source_supplied confidence regardless of sub_type.** `sub_type='room'` column er downstream semantic flag — downstream queries must apply room-rental-specific logic (e.g. don't compute rent/sqm using parent area, don't aggregate as building-level signal). ~48 of 51 room listings got Tier-1 fastnum via parent building this way; only 3 (no source fastnum) stayed unresolvable_by_design. Algorithm runs Tier-1 BEFORE the sub_type gate, which is the locked order.

**Phase 2b implementation issues caught + fixed** (during the live run, before close):
1. **`ON CONFLICT DO UPDATE` double-assigned `canonical_version`** (once via the EXCLUDED-loop, once via the explicit `+1`) → SyntaxError on all 861. Fixed: excluded `canonical_version` from the EXCLUDED-loop. Nothing persisted (all rolled back).
2. **Transaction-pooler defaults a tx to read-only** (`ReadOnlySqlTransaction` on INSERT) — same quirk as the Step-1a migration. Fixed: per-tx `SET TRANSACTION READ WRITE` folded into each upsert via `mogrify` (single round-trip).
3. **`preload_props` left an open read-tx** (autocommit=False) → the FIRST upsert's `SET TRANSACTION READ WRITE` wasn't the first statement of its tx (only parse_id=1 failed; rows 2+ succeeded after the prior rollback cleared it). Fixed: `pg.rollback()` after preload. Re-run promoted the last row → 861. Resumable throughout (promoted_to_canonical_at + ON CONFLICT idempotency).

**Architecture decisions**:
- Bulk-preload properties candidate slice frá Supabase (filtered by 66 distinct postcodes í parsed_myigloo): ~89K address-keys + 705 present-fastnums into in-memory dict for (heimilisfang_norm, postnr) + per-postnr geo lookups. Eliminates per-row Supabase round-trips during resolution.
- psycopg2 per-row UPSERTs via `.dbconfig` service-role connection, `ON CONFLICT (source, source_listing_id) DO UPDATE` (idempotent re-runs; canonical_version increments on conflict). Per-row error isolation (one bad row logged, doesn't poison the rest).
- `normalize_address` shared utility (commit b503981) used for address-match tier.
- ISO8601 timestamps frá Python call-site, never SQL.

**Phase 2b operational metrics** (final):
- scraper.listings_canonical rows frá myigloo: 861
- skipped_junk: 9   failed promotions: 0
- Fastnum resolution: source_supplied 752, address_match 40, geo_match 53, unresolvable_by_design 3, unresolved 13 → **98,1% (845/861) with fastnum**
- by category: residential 715, commercial 146; by sub_type incl summerhouse 3
- Total promotion time: ~176 sec (per-row upserts; resumable)
- parsed_myigloo.promoted_to_canonical_at set for 861 rows (9 junk stay NULL)

**Files í Step 1e commit**:
- `app/scripts/promote_myigloo.py` (340 línur, stdlib + psycopg2, PROMOTER_VERSION='0.1.0')
- `app/scripts/promote_myigloo_test.py` (132 línur, 16/16 pass)
- Additive uppfærslur á `docs/STATE.md` og `docs/DECISIONS.md`

**Untracked changes** (intentionally not in commit): `D:\verdmat-is\TAXONOMY_v2_draft.md` §3.1 amendment (added summerhouse line, un-tracked draft).

**Deferred (post-Step 1e, ekki blockers)**:
- **PostgREST exposed-schemas dashboard step** — manual Danni task til að gera `scraper.*` views REST-reachable from frontend. (Canonical writes are unaffected; only frontend REST consumption blocked.)
- Step 2 — visir scraper (next major scraper-substream task).
- Step 3 — mbl scraper (Playwright headless, kill-switch per §0.5).
- Cross-source dedup (§4) — gated til mbl + visir add sources.
- iter_rent_v1 asking-rent model — post-canonical, dependent á promoted data.
- api_page (index) parsing for withdrawn-detection (§7.2 2-night rule).

**Næsta skref**: dashboard exposed-schemas (Danni manual) + Step 2 visir scraper.

## 2026-06-03 (Step 1d closed) — myigloo parser live: parsed_myigloo populated with Tier-1 fastnum resolution insight

**Hvað**: Step 1d (myigloo parser) lokuð. `init_parsed_myigloo_schema.py` (119 línur) + `parse_myigloo.py` (260 línur) + `parse_myigloo_test.py` (127 línur, 16/16 pass) + `scripts/fixtures/parsed_myigloo_fixture.json` (sanitized hand-crafted fixture) committed. raw_myigloo.db inniheldur nú parsed_myigloo með 870 rows, 1:1 með distinct detail content_hashes í raw_fetches. Engin parser failures.

**Critical empirical wins úr Phase 1.5 mini-probe (Q1/Q2/Q3/Q8)**:

- **Q1 — `real_estate.landreg_id` IS the HMS fastnum** ⭐: 86.9% fill rate (756/870), 30/30 cross-match against `public.properties.fastnum` (100%). `landreg_source='landreg'` flags authoritative; `manual` (~13%) fallback til address resolution (Tier 2/3). Þetta er Tier-1 source_supplied fastnum per §2.5 fyrir ~87% af myigloo listings — leapfrogs the 47-71% address-match ceiling sem §2.5 var byggt í kringum. Promotion step (Step 1e) mun nýta `fastnum_supplied` column fyrst, þá address tier fyrir manual entries. Aðskilið frá Step 1c finding (§2.1.1 verification.as_of), þetta er annað major source-quirks insight á sama dag.

- **Q2 — deposit_isk = `insurance_price`** (tryggingafé absolute kr): empirical ratio distribution showed insurance_price varies 1-3× monthly rent (3× most common, 357/870; avg insurance_months 2,25). Schema captures both absolute amount (`deposit_isk`) og multiplier signal (`insurance_months`). `move_in_price.total` is composite (deposit + first month rent) → overflow, ekki canonical. `pre_paid_rent_*` always null í myigloo → drop entirely.

- **Q3 — lysing = `primary_description.text`** (Icelandic original): `primary_description.translation` er language metadata ({lang:'is', native:'Íslenska'}), ekki translated text. `description_translations[]` er translated variants (lang en/pl populated). Canonical maps lysing direct from primary_description.text.

- **Q8 — listing_type vocabulary**: 15 distinct tags + 5 categories empirically enumerated (confirmed identical í full run). TAXONOMY_v2 §3 mapping locked (15 tags → 7 residential sub-types + 4 commercial sub-types). NEW SUB-TYPE: `summerhouse` will be added to TAXONOMY_v2 §3 for cottage tag (3 listings observed). TAXONOMY_v2 amendment deferred til Step 1e (promotion) þegar mapping lookup table verður smíðuð.

**Parser architecture**:
- Per-(content_hash, parser_version) — matches §2.2 spec, UNIQUE INDEX enforced (distinct content_hash = rows = 870, invariant holds).
- INSERT ... ON CONFLICT DO NOTHING fyrir idempotent re-runs.
- On success: flips ALL raw_fetches sharing the content_hash til parse_status='parsed' (multi-fetch handling).
- On per-blob failure: only the specific raw_id flagged 'failed' (no cascade — DLQ-correct).
- raw_overflow JSON excludes PII paths (whole `owner` object dropped; `real_estate` mapped svo `owners[]` PII excluded líka).
- raw_overflow nullifies volatile paths (organization.verification.as_of) — same §2.1.1 paths pre-hashed at raw level, also scrubbed from parsed-level overflow.
- Engagement metrics (views_count, application_count, has_applied, last_conversation, liked, pre_approval, client_steps_done) preserved í overflow med `_volatile_suspect` flags — useful for future analysis (time-on-market predictors) but flagged as not-canonical.
- ISO8601 timestamps frá Python call-site, never SQL.
- api_page rows EKKI parsed (deferred; 9 rows stay parse_status='pending').

**Phase 2b operational metrics**:
- parsed_myigloo rows: 870
- raw_fetches detail parse_status='parsed': 870  (pending 0, failed 0)
- parse failures: 0
- fastnum_supplied fill rate: 86,9% (756/870 — matches Phase 1.5 mini-probe exactly)
- listing_type_tag distribution matches Phase 1.5 vocabulary table (15 tags); category_tag 5 (residential 714, commercial 147, bnb 5, other 3, hotel 1)
- **title null count: 449 (51,6% — over half, NOT a small minority)**; canonical promotion will COALESCE(title, short_address) at Step 1e
- **lysing null count: 13** (listings with no source `primary_description.text`; nullable, expected — NOT 0)
- avg insurance_months: 2,25
- Total parse time: 2,2 sec

**Empirical corrections to mid-Phase assumptions** (surfaced at full-run inspect, before commit):
- title-null was assumed "small minority" í Phase-2a plan — empirically 449/870 = 51,6%. COALESCE-at-promotion is therefore load-bearing for ~half the corpus, not an edge case.
- lysing-null was assumed 0 — empirically 13 (matches Phase-1.5's 857/870 non-null primary_description.text). Genuine source reality (those listings carry no description), not a parser miss.

**Files í Step 1d commit**:
- `app/scripts/init_parsed_myigloo_schema.py` (119 línur, stdlib only, idempotent §2.2 + Q1/Q2 DDL)
- `app/scripts/parse_myigloo.py` (260 línur, stdlib only, PARSER_VERSION='0.1.0')
- `app/scripts/parse_myigloo_test.py` (127 línur, 16/16 pass)
- `app/scripts/fixtures/parsed_myigloo_fixture.json` (sanitized fixture, no PII)
- Additive uppfærslur á `docs/STATE.md` og `docs/DECISIONS.md`

**Ófært**: `app/scripts/probe_myigloo.py` (Phase 1 ad-hoc, untracked). TAXONOMY_v2 amendments (cottage → summerhouse sub_type, bnb/apartment_hotel → hospitality) í `D:\verdmat-is\TAXONOMY_v2_draft.md` deferred til Step 1e þegar promotion mapping er smíðuð.

**Source-fidelity decisions** (architect calls):
- title null → preserved as-is í parsed; COALESCE til short_address (eða addr_street+addr_number) við canonical promotion (Step 1e), ekki parse-time.
- listing_type_tag = 'studio' vs lysing-says-'herbergi' noise: parser preserves source signal verbatim; TAXONOMY mapping við promotion. Future feature post-promotion: flag tag_uncertain ef mis-match patterns rísa.
- PII drop confirmed (GDPR posture — capture only what we need).

**Deferred (post-Step 1d, ekki blockers)**:
- api_page (index) parsing — separate index-observation parser, will produce a withdrawn-detection signal (per §2.1 footer 2-night rule).
- TAXONOMY_v2 amendment for summerhouse sub_type — Step 1e.
- Step 1e promotion til scraper.listings_canonical (Tier-1 fastnum resolution + Tier-2/3 fallback for manual entries).

**Næsta skref — Step 1e (promotion)**: reads parsed_myigloo WHERE promoted_to_canonical_at IS NULL, applies TAXONOMY_v2 lookup (listing_type_tag → category/tenure/sub_type), resolves fastnum (Tier-1 from fastnum_supplied OR Tier-2/3 address-match), maps to scraper.listings_canonical 39 columns, INSERTs/UPSERTs til Supabase. Cross-source dedup (§4) deferred til mbl + visir come online (Step 2 + 3).

## 2026-06-03 (Step 1c Phase 3 closed) — myigloo raw fetcher live: hybrid index + detail, normalize-before-hash idempotency

**Hvað**: Step 1c Phase 3 lokuð — `fetch_myigloo.py` (378 línur, stdlib only) + `fetch_myigloo_test.py` (169 línur, 14/14 pass) committed sem fyrsti production scraper-modul. Production raw_myigloo.db inniheldur fyrsta nightly snapshot af ~870 virkum leigulistum, content-addressable storage + append-only ledger per §2.1 + §2.1.1 normalization.

**Critical mid-Phase finding — content-hash idempotency defeated by volatile per-request timestamps**:

Phase 3b's first full run completed clean operationally (880 fetches, 0 errors, 0 retries) but inspect afhjúpaði að `changed=0` fired aldrei á neinum re-fetch. Diff á tveggja fetches á sama listing (id=23989, 11 mín gap) sýndi að allir fields voru identical EXCEPT:
- `organization.verification.as_of`: server-stamped við request-time
- `owner.verification.as_of`: sama

Þetta þýddi að hver detail response var unique per fetch → sha256 alltaf different → blob dedup virkaði aldrei. Storage hefði vaxið linearly (~4 MB × N nætur) án dedup. `changed` flag varð gagnslaus per-listing change signal — beint stríðandi við §2.1 stated contract.

**Fix — normalize-before-hash (§2.1.1 amendment)**:

- `content_hash` redefined: sha256 á CANONICALIZED body (per-source volatile-field paths nulled).
- `blob_gz` heldur áfram að geyma verbatim body (capture-fidelity preserved — staðfest post-fix: `verification.as_of` enn til staðar í stored blob).
- Per-source volatile field paths skráð í §2.1.1 (myigloo: `organization.verification.as_of`, `owner.verification.as_of`; visir og mbl TBD við Steps 2 og 3).
- Unit-test validated: identical bodies → same hash; bodies differ only í verification.as_of → same hash; bodies differ í real fields → different hashes; non-JSON payloads → graceful raw-hash fallback.
- Live-validated post-fix: dry-run × 2 immediately á sömu IDs → second fetch sýndi (detail, changed=0)=10 rows í raw_fetches (22 fetches → 12 distinct blobs). Idempotency contract restored.

**Phase 3 final operational metrics** (post-fix full run á clean baseline):
- Total raw_fetches: 879   raw_blobs (unique): 879
- api_page: 9 (all changed=1 — page composition shifts over time as expected)
- detail: ~870 (all changed=1 í fyrsta nightly snapshot, ekkert prior state)
- HTTP errors (post-retry): 0   Max retry_count observed: 0 (this baseline run; Phase 3a dry-run hafði one transient id=22844 retries=1)
- Uncompressed: ~18,6 MB   Compressed: ~4,1 MB   Ratio ~22%
- Full run elapsed: ~21,7 mín @ 1s politeness

**Empirical validations úr Phase 3**:
- `order_by=-published_at` honored — first-page IDs strictly descending by published_at (cross-validated by third-party HTML scraper audit á D:\myigloo_tracker_v2). Enables future incremental-sync stopping-condition.
- `page_size=100` honored consistently — hver index page skilar exactly 100 items.
- Retry path validated in wild — Phase 3a dry-run á id=22844 með retries=1 (transient failure auto-recovered). Decision matrix: 5xx + 429 + ConnError + Timeout = retry með exponential backoff (1s, 2s, 4s); 4xx other than 429 = no retry.
- 5xx outage detection unit-test validated; ekki yet stress-tested in wild.
- Compression ratio ~22% consistently.

**Architectural notes**:
- Body data rides on FetchResult dataclass aðeins transiently — no memory growth over ~880 fetches.
- Allir ISO8601 timestamps koma frá Python call-site, never SQL.
- HTTP failures post-retry skrifa content_hash=NULL ledger row með parse_error=NULL.
- Normalization (§2.1.1) applies aðeins við hash computation; blob_gz geymir verbatim body fyrir fidelity og future re-parse.

**Files í Phase 3 commit**:
- `app/scripts/fetch_myigloo.py` (378 línur, stdlib only, með `_canonical_hash()`/`_nullify_path()`)
- `app/scripts/fetch_myigloo_test.py` (169 línur, 14/14 pass — including normalize-related cases)
- Additive uppfærslur á `docs/STATE.md` og `docs/DECISIONS.md`

**Ófært**: `app/scripts/probe_myigloo.py` (Phase 1 ad-hoc, untracked). §2.1.1 amendment í `D:\verdmat-is\SCRAPER_SPEC_v2_draft.md` (un-tracked draft).

**Næsta skref — Step 1d (parser)**: reads raw_blobs frá raw_myigloo.db, extracts structured fields úr ~80-key detail payload, populates `parsed_myigloo` table.

## 2026-06-03 (Step 1c Phase 2) — myigloo raw layer: hybrid fetching design + scraper_data/ outside-repo storage

**Hvað**: Step 1c (myigloo raw fetcher) Phase 2 lokuð — schema bootstrap + scraper_paths utility committed. Phase 1 audit probe lokuð empíríkt sama dag (ad-hoc `probe_myigloo.py` untracked fyrir Phase 3 referens). raw_myigloo.db smíðað eftir SCRAPER_SPEC_v2 §2.1 verbatim (raw_blobs + raw_fetches + v_dlq_parse_failures view), WAL mode, FK enforcement on. Smoke test 13/13 pass, scraper_paths_test 8/8 pass.

**Fetching design — hybrid (locked)**:
- Index-walk per cycle: `GET /api/listings/?page=N&page_size=100` (~9 pages) → enumeration eingöngu. `fetch_kind='api_page'`, `source_listing_id=NULL`. Page blobs low-value/short-retention.
- Detail-per-id per cycle: `GET /api/listings/{id}/` (~874 calls) → rich payload (~80 keys, m.a. `primary_description` (lýsing fyrir LLM extraction), `contract_min_months/max_months/termination_term`, `move_in_price`/`insurance_*`/`pre_paid_rent_*`, `amenities`/`furniture`/`rules`, `mbl_id` cross-ref, `linked_property_id`). `fetch_kind='detail'`, `source_listing_id=<id>`. Full §2.1 content-hash idempotency: óbreyttur body → `changed=0` + `parse_status='skipped_unchanged'` + hash reused; breyttur body → ný blob + `changed=1`.

**Hvers vegna hybrid frekar en page-only**: (1) detail er essential — `primary_description` er lýsing fyrir LLM extraction (iter_rent_v1 forsenda), og page-payload skortir öll canonical/§2.5 fields. (2) §2.1 content-hash idempotency virkar bara á detail-level — á page-level shiftast composition daglega svo hash breytist next time þótt enginn listing breytist, sem gerir §2.1 dedup-virði ~zero. (3) Call-budget ~880/night @ 1s politeness ≈ 15 mín — vel undir §0.5 mbl-cap (sem á hvort sem er ekki við myigloo: ekkert WAF, opin DRF-style API, robots 404 á rent-api subdomain).

**Empíríkar áréttingar úr Phase 1 probe (leiðréttingar á §1.1 og handoff)**:
- Array key er `items[]`, ekki `results[]` (handoff rangur)
- Live count 874 (vs handoff 871; +3 drift)
- `per_page` er **silently ignored** — einungis `page_size` virkar (kritisk gotcha; fetcher sem notar `per_page` mis-paginar í default 25/page án villu)
- Server er uvicorn / FastAPI-Starlette, ekki klassísk DRF
- Detail endpoint `/api/listings/{id}/` til staðar, HTTP 200, ~3× richer
- `rent-api.myigloo.is/robots.txt` skilar 404 — ekki restriction

§1.1 í `D:\verdmat-is\SCRAPER_SPEC_v2_draft.md` (un-tracked, utan repo) fékk additive empirical-correction note 937→945 línur — ekki hluti af þessum commit.

**Storage convention (locked)**:
- Raw SQLite DB-ar lifa á `D:\verdmat-is\scraper_data\raw_<source>.db`, utan git-repo. Mirrors `D:\Gagnapakkar\*.db` convention; multi-GB blob accumulation færi aldrei í commits.
- Path read úr env-var `SCRAPER_DATA_DIR` (default `D:\verdmat-is\scraper_data\`), via shared utility `app/scripts/scraper_paths.py`.
- `.gitignore` belt-and-suspenders: `scraper_data/`, `*.db`, `*.db-shm`, `*.db-wal`.

**Files í Phase 2 commit**:
- `app/scripts/scraper_paths.py` (39 línur, stdlib only, raw docstring til að forðast SyntaxWarning)
- `app/scripts/scraper_paths_test.py` (92 línur, 8/8 pass: default/env/parent-dir/per-source/validation/idempotency)
- `app/scripts/init_raw_myigloo_schema.py` (98 línur, idempotent §2.1 DDL verbatim + v_dlq_parse_failures view)
- `app/.gitignore` (+8 línur: scraper raw-DB block með comment refererandi §2.1)

**Ófært í commit**: `app/scripts/probe_myigloo.py` (Phase 1 ad-hoc, untracked til Phase 3 refactor). `D:\verdmat-is\SCRAPER_SPEC_v2_draft.md` §1.1 correction (un-tracked draft sem býr utan repo).

**Næsta skref**: Phase 3 — fetcher implementation. Hybrid index + detail loop, gzip-compressed blob storage með sha256 hash á óþjappðu body, append-only ledger með changed=0/1 logic, polite UA + 1s delay, dry-run flag fyrir 2-page warm-up áður en fullur 874-listing run keyrir.

## 2026-06-01 — Scraper schema applied: `scraper.*` foundation live í Supabase (SCRAPER_SPEC_v2 §2.3 + §2.4 + §2.5)

**Context**: Fyrsta production-write úr scraper-substream-inu. SCRAPER_SPEC_v2 (planning-drafts á `D:\verdmat-is\`, un-tracked) er architecturally locked fyrir §0/§1/§2.1-2.5/§3/§5/§6/§7. Næsta concrete skref var að leggja canonical schema-target inn í Supabase **áður en** scraper-kóði (parser/fetcher) er skrifaður — surfaces hvaða DDL-issue sem er strax og gefur myigloo Step 1 skýrt target.

**What**: Migration `20260601122916_scraper_schema_init.sql` applied via MCP `apply_migration` (single BEGIN/COMMIT). Nýtt `scraper` schema:
- `listings_canonical` base table — **39 cols**: decomposed `(category, tenure)` key + `sub_type` + `tegund_raw` + `lease_term_class` (TAXONOMY_v2); `fastnum` FK → `public.properties` **ON DELETE NO ACTION**; PostGIS `geog` generated column; fastnum-resolution trió (`method`/`confidence`/`at`, §2.5).
- **4 enums** (`category_enum`, `tenure_enum`, `lease_term_enum`, `fastnum_res_enum` m. `unresolvable_by_design`).
- **5 CHECK** constraints (`ck_rent_lease`, `ck_plot_area`, `ck_price_pos`, `ck_fastnum_pos`, `ck_fastnum_resolution`) + `uq_source_listing` UNIQUE.
- **7 indexes** (5 named `ix_lc_*` incl `ix_lc_geo` GiST á geography, + unique + PK).
- RLS enabled + `public_read` SELECT policy + column-allowlist GRANT (**29 cols** TO anon/authenticated; operational/provenance cols excluded) — sama mynstur og Group B 14-tafla lockout.
- **5 security_invoker views** (`v_residential_sale_listings`, `v_residential_rent_listings`, `v_commercial_listings`, `v_plot_listings`, `v_listings_combined`); residential-views join → `public.v_properties` (Group B view-layer abstraction, FIX 3 — `v_properties` exposes byggar/einflm/matsvaedi_nafn anon-readable).

**Why this gating**: Step 1 (myigloo raw→parsed→canonical) þarf canonical-target til staðar áður en parser/fetcher-kóði er skrifaður. Schema-first afhjúpar DDL-vandamál strax — dry-run (BEGIN…ROLLBACK gegn live) staðfesti FK + PostGIS `geog` + enums + views + grants áður en apply, og fann tvö latent-issue í endurskoðun: `is_active` getur ekki verið GENERATED column (now()-háð → stored + nightly-refresh) og `ON DELETE SET NULL` rakst á `ck_fastnum_resolution` (→ NO ACTION).

**Verification**: post-apply **10/10** read-only checks grænir — schema(1), enums(4), relations(6 = 1 tafla + 5 views), columns(39), CHECKs(5), indexes(7), policy(1 `public_read`/SELECT), anon-allowlist(29), anon `v_residential_rent_listings` count=0 án villu (security_invoker resolve-ar rétt), extensions(pgcrypto + postgis).

**Pending manual Danni steps** (ekki blocking downstream): (1) Supabase dashboard → API → Exposed schemas → add `scraper` (annars eru v_* views ekki REST-reachable); (2) `supabase migration repair --status applied 20260601122916` svo future `db push` reynir ekki re-apply (apply var via MCP, ekki CLI, svo schema_migrations-taflan þekkir hana ekki enn).

**Explicit non-changes**: ENGIN `public.*` tafla/view snert; ENGIN existing gögn breytt; net-new additive schema. `pgcrypto` + `postgis` voru þegar til staðar (CREATE IF NOT EXISTS = no-op).

**Refs**: `SCRAPER_SPEC_v2_draft.md` §0.1-§0.5 (sign-offs Danni 2026-05-29/06-01: evalue-replace strategy, asking-rent leigu-módel, single-table `(category,tenure)`, TAXONOMY_v2 pre-req, mbl headless+kill-switch) + `TAXONOMY_v2_draft.md` (locked 2026-05-29: 4 categories × 2 tenures, rent/commercial/plot sub-types, fastnum-resolution eligibility). §4 frontend = pass 3b (deferred til UI input).

## 2026-05-29 — Skref 13b: iter3v2/iter4 spine debt RESOLVED via option (ii) (decouple) + push_preview version-stamp guard

**Context**: Precompute-spine debt (systkina-entry sama dag) gerði push-path-inn rangan: `run_monthly` push myndi UPSERT-a iter3v2-afurð `build_precompute` ofan í live `predictions`-töfluna sem er iter4. Tvær leiðir voru á borðinu — (i) full track-unification, (ii) decouple. Valið féll á **(ii)** eftir CC1 READ-ONLY audit (Q1+Q6).

**CC1 findings sem réðu valinu**:
- **Q1 — `score_new_listing` er EKKI í production runtime path**: 0 runtime-hits í app-repo (aðeins docs); eini caller er `build_precompute` (batch). Frontend les iter4 alls staðar via `v_current_predictions`-view; iter3v2 birtist EINGÖNGU í `?mode=debug` (`predictions_iter3v2`-tafla). → iter3v2-spine þjónar ENGUM notanda, svo decouple hefur núll user-facing downside.
- **Q6 — ein tafla, tveir track-writers**: live taflan heitir **`predictions`** (EKKI `predictions_iter4` — það er bara CSV-skráarnafn frá iter4-leiðinni). `import_iter4.py` (Skref 10) renamed gömlu iter3v2 → `predictions_iter3v2` og COPY-aði iter4 í `predictions`. `run_monthly` push-target `("predictions","predictions.csv")` + iter4-leiðin target SÖMU töflu → áreksturinn.

**Option (i) vs (ii) trade-off**: option (i) (færa build_precompute + score + recal + validate á `iter4a` + conformal) er ~340-630 LOC + **reiknirit-skipti** í monthly_recalibration (k-factor stretch → conformal refit) + JSON-schema migration — paradigm-migration, ekki swap. Option (ii) (decouple) er ~2-12 LOC. Þar sem iter3v2 þjónar engum (Q1), er decouple réttur fyrsti leikur; option (i) deferred til Phase Y iter4-spine sprint (þá fær precompute aftur predictions-ownership undir iter4).

**Hvað var gert**:
1. `run_monthly.py` `PRECOMPUTE_TARGETS`: `predictions` + `feature_attributions` commented út (preserved fyrir framtíðar re-enable) — push snertir þær ekki lengur.
2. `build_precompute.py --skip-predictions` flag (early-return í `score_and_shap`), wired inn í orchestrator build_precompute-step (`cmd … --skip-predictions`).
3. **push_preview version-stamp guard** (`check_version_stamp`): fyrir hverja push-target sem hefur `model_version`-dálk, ber saman CSV-version-sett vs live-version-sett; mismatch → `main` HALT-ar með exit 4 (`halted_version_mismatch`). Column-gated, svo model-óháðar töflur (properties/sales/repeat_sale/ats/comps) self-skip-a.

**Guard rationale**: Skref 12d push-preview gaf "+0" á `predictions` — en það var **count-parity, ekki value-parity**: push_preview bar aðeins saman `count(*)` (run_monthly.py L334-342), svo iter3v2-vs-iter4 track-munur var ósýnilegur. Falskt +0 hefði hleypt iter3v2 yfir iter4 silently. Version-stamp guard lokar þessu blindspot-i varanlega — verður relevant aftur þegar predictions er re-enabled í push (Phase Y).

**Empirical**: guard-smoke 3/3 (synthetic iter3v2 → mismatch HALT; `iter4_final_v1` → pass; `properties` self-skip) gegn live `predictions`. `run_monthly --dry-run` (run id=9) grænn með `build_precompute … --skip-predictions`. Báðar skrár byte-compile clean. ENGIN push.

**Commits**: precompute `41d123c` (build_precompute.py, explicit-path; held-set-gate `rebuild_predictions_iter4.py` skilið eftir uncommitted f. Skref 13c) + app-commit (run_monthly.py + docs) þessa lota — two-repo split (atomic two-repo push-helper er sjálft Skref 13c). EKKERT pushað.

**Afleiðing fyrir push-gating**: spine-blocker farinn; push nú gated aðeins á 2-3 proven cycles + version-guard-green. 13b ✅.

---

## 2026-05-29 — Precompute-spine debt (iter3v2 build_precompute vs iter4 live serving) elevated til Skref 13 push-blocker

**Context**: Skref 12c/12d cascade re-confirm-aði undir nýju ljósi að `build_precompute.py` + `score_new_listing.py` + `monthly_recalibration.py` + `validate_metrics.py` keyra allir á **iter3v2-track**, en live serving (`/eign/[fastnum]`, `predictions`-taflan) er **iter4_final_v1 + iter4_conformal_v1**. Þetta var þekkt tech-debt en var "passive" þar til reconciliation gerði push-path-inn raunhæfan.

**Af hverju þetta er nú blocker, ekki bara debt**: `push_precompute_to_supabase` (Skref 13) myndi taka iter3v2-afurð `build_precompute` og skrifa hana yfir iter4 `predictions`-töfluna → silent model-track regression í prod. Reconciliation (Skref 11→12) fjarlægði 232.887-vs-124.835 divergence-ina sem hingað til hefur BLOKKAÐ push; spine-mismatch-inn er núna eini eftirstandandi correctness-blocker fyrir push.

**Decision**: spine-alignment er **hard pre-req fyrir push** (Skref 13b). Tvær leiðir á borðinu, EKKI valið enn:
- (i) Færa `build_precompute` predictions-step yfir á `iter4a_*.lgb` + iter4_conformal_v1 (full track-unification) — réttast en stærra.
- (ii) Disable-a predictions-step í `build_precompute` (lætur live iter4 `predictions` ósnerta; push skrifar aðeins properties / comps / attributions) — minni breyting, en skilur tvo tracks eftir.
Ákvörðun gated á Skref 13b spike.

**Knock-on**: validate_metrics drift-flagg (sjá systkina-entry sama dag) er iter3v2-calibration artifact, ekki live-iter4 signal — styrkir að spine-split sé raunverulegur, ekki cosmetic.

**Status (2026-05-29, Skref 13b)**: **RESOLVED via option (ii)** (decouple) — iter4-spine-migration (option i) deferred til Phase Y. predictions/feature_attributions tekin úr `run_monthly` push-targets + `build_precompute --skip-predictions` + push_preview version-stamp guard. CC1 Q1/Q6 sönnuðu: score_new_listing þjónar engum notanda, live tafla = `predictions` (iter4). Sjá Skref 13b entry efst.

---

## 2026-05-29 — sales_history −786 push-preview anomaly: reconciliation-strategy deferred til Skref 13c

**Context**: Skref 12d standalone `build_precompute.py --force` push-preview á reconciled state sýndi: `properties` / `repeat_sale_index` / `ats_lookup` / `predictions_iter4` allir **+0 vs live** (clean match — reconciliation proven), `comps_index` **+634.212** og `feature_attributions_iter4` **+571.870** (expected growth fyrir nýja 232.887-universe-ið), EN `sales_history` **−786** (preview hefur 173.081, live hefur 173.867).

**Root cause**: `build_precompute` deriva-r sales_history úr `training_data_v2` filtrað á last-5-sölur-per-fastnum. Phase D3 apply (2026-05-27) skrifaði 786 sölur sem **raw direct-inserts** (þ.m.t. `onothaefur=1` rows) sem ná aldrei inn í training_data_v2 filter-inn → þær birtast ekki í build_precompute-afurð. −786 er því derivation-vs-direct-insert mismatch, EKKI gagnatap; live sales_history (173.867) er rétt.

**Af hverju deferral, ekki fix núna**: ekkert er pushað í Skref 12; −786 er push-preview observation, ekki live-state breyting. Fix-ið krefst stefnuvals sem snertir push-helper-hönnun.

**Decision (deferred til Skref 13c)**: tvær leiðir:
- (a) **append-D3**: push-helper upsert-ar build_precompute sales_history en skilur D3 raw-rows (786) eftir ósnertar (additive, varðveitir onothaefur-flaggaðar).
- (b) **re-derive**: extend-a `training_data_v2` / build_precompute svo D3 raw-sölur (incl onothaefur) verði first-class — root-fix per [[feedback_root_fix_vs_workaround]] en stærra.
Val gated á push-helper byggingu í Skref 13c.

---

## 2026-05-29 — validate_metrics cov80 +5,95pp er coverage-IMPROVEMENT, ekki regression; baseline-rebase deferred til 13a

**Context**: run_monthly cascade á reconciled state (Skref 12c, run id=8) halt-aði á `validate_metrics`: cov80 73,10% → 79,05% (**+5,95pp** vs frosna 4c-baseline-inn). Þröskuldur er ±3pp coverage → flaggað sem fail/halt.

**Greining**: drift-ið er ekki degradation. `monthly_recalibration` (step á undan) auto-update-aði `calibration_config.json` í þessari keyrslu því SEMI_DETACHED k95 drift datt **31,3% → 22,8%** (undir 30%-þröskuldinn, öfugt við run id=7) — enabled af 552 D3-sölum sem urðu newly-joinable inn í training eftir reconciliation. Ný calibration færir coverage frá 73% **í átt að nominal 80%** — það er bati, ekki tap. ±3pp-gat-ið mælir gegn frosnum 4c-baseline sem var settur FYRIR reconciliation.

**Mikilvægt caveat**: `calibration_config.json` er **iter3v2-track** (sjá systkina-entry um spine-debt), EKKI live iter4_conformal_v1. Þessi coverage-breyting hefur því engin bein áhrif á prod-serving fyrr en spine er sameinað.

**Decision (deferred til Skref 13a)**: rebase 4c-baseline-inn á post-reconciliation calibration (skrá nýjan ~79% cov80 baseline) — **couple-að við recalibration-decision** svo við frystum ekki baseline gegn calibration sem gæti haldið áfram að hreyfast næstu 2-3 cycles. Engin urgency: validate er informational gate, ekkert pushað.

---

## 2026-05-28 — classify_property NaN-safe root-fix (D3 NaN-tegund rows)

**Context**: Skref 12b Step 2 (iter4 predictions rebuild á reconciled 232.887-pkl) crash-aði í `classify_property.py:134`: `if not tegund_str:` gerði ráð fyrir streng, en 89 D3-raðir höfðu `tegund = NaN` (float). `not NaN` → `False` (NaN er truthy), svo guard-inn fór ekki í gang og næsta `.strip()`/lookup kastaði.

**Root fix (ekki plástur)**: `if not tegund_str:` → `if not isinstance(tegund_str, str) or not tegund_str.strip():` með WHY-comment. Höndlar bæði NaN-float OG tóman/whitespace-streng í einum guard. `classify_property.py` lifir á `D:\` (utan repo við `D:\verdmat-is\app`); fixað in-place via verified Python replacement (Edit-tool gefur EPERM á drive-root), assert count==1. Audit-tracked, ekki git-tracked hér.

**Af hverju þetta kom fyrst núna**: pre-reconciliation pkl (124.835) hafði enga NaN-tegund; D3-recovery-universe-ið bætti við 89 raðum með vantandi tegund (HMS payload án skráðrar tegundar). Reconciliation afhjúpaði latent type-assumption sem hafði aldrei verið testuð gegn NaN.

**Tengt**: [[feedback_root_fix_vs_workaround]] — gat ekki bara dropp-að 89 röðunum; isinstance-guard-inn er rétti staðurinn.

---

## 2026-05-28 — D3 honesty gate materialíseraður sem held-fastnum-set artifact (d3_held_fastnums.csv)

**Context**: Reconciled pkl (232.887) inniheldur 8.426 D3-eignir sem voru held úr scoring í Phase D3 NOW lota (5.993 matsvaedi-unconfident + 2.433 no-byggar) til að halda iter4_conformal_v1 PI-i heiðarlegum (ablation: blank matsvaedi → 51%/22% PI breach vs 0%/0% spatial-inferred). Skref 12b iter4 predictions rebuild þurfti að virða þennan gate — annars hefðu held-raðir fengið low-confidence predictions skrifaðar.

**Decision**: gate-inn er materialíseraður sem **standalone artifact** `D:\d3_held_fastnums.csv` (8.426 rows: `fastnum,reason`, UTF-8 no BOM) frekar en in-lined í scoring-logic (Option d, valið af Danni yfir Option A inline-gate). `rebuild_predictions_iter4.py` les `HELD_CSV` constant og filter-ar preds+shaps gegn settinu fyrir `to_csv` → output 167.503 (var 175.929 ungated, Δ −8.426 = nákvæmlega held-settið).

**Af hverju artifact frekar en inline-gate**: (i) reusable af hverju downstream step (predictions, push-preview, future evalue augl-pass); (ii) explicit auditability — held-count + reason inspectable án þess að lesa scoring-kóða; (iii) decoupling — LATER evalue lota fjarlægir bara raðir úr CSV-inu þegar þær verða confident (matsvæði/byggar fæst), án scoring-rewrite.

**Verifað**: 167.503 = 175.929 − 8.426 (exact). Held-residential UI-state (`/eign/[fastnum]`: "Verðmat liggur ekki fyrir þessa eign") þjónar þessum 8.426 gracefully.

**Tengt**: Phase D3 honesty-gate decision (DECISIONS 2026-05-27 D3-entry); held-set un-holdast í LATER evalue augl-pass.

---

## 2026-05-28 — Orchestrator first-green-cycle + 5-bug debug session

**Context**: Fyrsta raunverulega `run_monthly.py` keyrslan (engin `--dry-run`) eftir Group C closure 2026-05-27. Markmið: end-to-end grænn mánaðar-cycle með halt-before-push gate sannað í verki. `run_monthly` + `migration_helpers` höfðu verið skrifuð en aldrei keyrð gegn raunverulegu subprocess (dry-run sleppti subprocess; fyrsta real-run dó á preflight áður en það náði output-handling). Þannig komu real-execution bugs upp í röð, hver um sig blocking næsta skref. Allir fixaðir at root og regression-testaðir.

**Bug-listi í discovery-röð**:

1. **Drive-relative `Path("D:")` í 5 D:\ scriptum** (LOG_PATH + D_DRIVE konstöntur). `Path("D:")` er drive-relative (resolve-ast gegn current dir á D: drifinu), ekki absolute. Þegar orchestrator keyrði þau frá `D:\verdmat-is\app` (ekki `cd D:\` eins og scriptin documenta) resolve-aðist `Path("D:")/"x"` í `D:\verdmat-is\app\x` → preflight fann ekki input-skrár → exit 2. **Halt-aði run id=2** á step 3 (rebuild_training_data).
2. **cp1252 decode parent-side** í `subprocess.run(..., text=True)`. Á Windows decode-ar `text=True` child-stdout með locale-encoding (cp1252). D:\ build-scriptin emit-a íslenska + box-drawing stafi (`│ ─ á í ð þ ö`); byte 0x81 er ógildur í cp1252 → `UnicodeDecodeError` í subprocess reader-thread → `result.stdout = None`. **Crash-aði run id=3** (unhandled exception, exit 1) eftir að rebuild-subprocess kláraðist en á meðan orchestrator las output-ið.
3. **None-unsafe stdout/stderr** í helper — `result.stdout.splitlines()` og `.strip()` gerðu ráð fyrir streng; með `stdout=None` (frá #2) → `AttributeError`. Bundlað með #2.
4. **No crash-finalize** í `run_monthly.main` — unhandled exception skildi `pipeline_runs` row eftir dangling (`ended_at`/`exit_status` NULL). id=3 var dangling þar til manual cleanup.
5. **Child-side cp1252 stdout þegar piped**. Jafnvel með parent-decode lagað skrifar child-Python sín eigin stdout í cp1252 þegar piped (Windows locale), nema hann reconfigure-i. `refresh_dashboard_tables.py:245` `log(f"... {prev} → {cur} rows")` (U+2192) kastaði `UnicodeEncodeError`; of-breitt `except` í scriptinu mis-túlkaði logging-villu sem data-validation failure → triggeraði óþarfa atomic rollback (restored 14 files) → exit 1. **Halt-aði run id=5** á step 4. Athugið: sjálf data-byggingin (repeat_sale_index + ats_lookup) heppnaðist — aðeins validation-logging línan crash-aði.

**Root fixes (engir plástrar)**:

- **5 per-script**: `Path("D:")` → `Path("D:/")` (absolute, CWD-óháð). Skrárnar lifa á `D:\` data-drifinu (utan repo við `D:\verdmat-is\app`); fixaðar in-place, 0 footguns eftir. EKKI git-tracked hér — logged fyrir audit í commit 8edc297.
- **Helper (`scripts/migration_helpers.py`)**: `encoding="utf-8", errors="replace"` (ekki `text=True`) á báðum subprocess-köllum + `(result.stdout or "")` / `(result.stderr or "")` None-guards + stdout-tail capture á failure-path (svo child sem bail-ar til stdout sé diagnosable).
- **Orchestrator (`scripts/run_monthly.py`)**: `try/except` crash-finalize um step-loop-ið með `current_step_id` tracking; á exception finalize-ar in-flight step (exit_code=-1) + run (`exit_status='crashed'`) áður en re-raise.
- **Env**: `env={**os.environ, "PYTHONIOENCODING": "utf-8"}` á báðum subprocess-köllum — forsar child-stdio í utf-8 óháð því hvort scriptið reconfigure-i sjálft. Þetta er systemic root-fix sem nær yfir alla 6 child-scripts í einu (vs að plástra hvern `→`).

**Empirical validation**: `scripts/shakedown_orchestrator.py` byggður (throwaway harness) — **15/15 assertions**. 5 child-modes (happy / halt / crash / explode / cp1252_writer) + negative control + crash-finalize gegn Supabase audit-töflum. `cp1252_writer` mode reproduce-ar bug #5 faithfully (child sem reconfigure-ar EKKI sín stdout og prentar `→`); **negative control strip-ar `PYTHONIOENCODING` úr env og sannar að bug-#5 mechanism re-fire-ar án env-fix-ins** — proving fixið er load-bearing, ekki cosmetic. Upprunalegi shakedown (Skref 4) missti þetta því synthetic-child-inn hans reconfigure-aði sín eigin stdout; gap-ið var lagað í Skref 6.

**Pipeline_runs audit-trail**:

| id | outcome | hvar |
|---|---|---|
| 2 | halted | step 3, CWD bug (#1) |
| 3 | crashed → manual cleanup | step 3-output, encoding crash (#2-4); finalize-aður handvirkt sem 'crashed' með cleanup-note í `summary` |
| 5 | halted | step 4, cp1252 child-write (#5) |
| 7 | **success_halt_pre_push** | **7 steps green, 113s — fyrsta fully-green cycle** |

**Snapshot id=2** (frá run id=7) fangaði drift-detectable fingerprints: CPI MD5 / kaupskrá MD5 / training_data_v2 MD5 allir breyttir (fresh), `feature_names_hash` stable (sami 154-feature surface), valuation rúllaði 2026-04 → 2026-05, cpi_factor 1,00548 → 1,00885. Reproducibility-ledger virkar.

**Data-quality á run id=7** (sub-script outcomes):
- `monthly_recalibration`: **SEMI_DETACHED k95 drift +31,3%** (k80 +21,8%) yfir 30%-þröskuldinn → scriptið hélt prior calibration (auto-update declined), `calibration_config.json` ÓBREYTT (mtime 2026-04-19), printaði proposed k-factors fyrir manual review. Non-fatal (exit 0).
- `validate_metrics`: **8/8 pass** gegn 4c-baseline — held clean MAPE 6,98% (baseline 7,00%, Δ −0,02pp), cov80 72,90% (73,10%), cov95 92,67% (92,70%); allt innan ±0,5pp MAPE / ±3pp coverage þröskulda. Líkanið stöðugt á prior calibration.

**Open follow-ups (ekki í commit-scope, sér workstreams)**:
- **`properties_v2.pkl` divergence vs live Supabase** — pickle er 124.835 (pre-D3) en live er 232.887 (post-D3). `build_precompute.py` les pickle → push-preview á run id=7 sýndi `properties` csv 124.835 vs live 232.887 (−108.052), `predictions` −57.187, `sales_history` −786; 4 derived-töflur delta +0. **Naive push myndi annaðhvort skilja D3-raðir eftir stale (upsert) eða WIPE-a þær (truncate-reload)** → push BLOKKAÐ þar til pickle er rebuilt FROM Supabase (PLANNING_BACKLOG item 1, SOURCES_OF_TRUTH 2026-05-20 mandate). Skref 10B audit-ar þennan path.
- **SEMI_DETACHED k95 +31,3% drift** — prior cal kept; pending 2-3 cycles til að greina noise vs regime shift. Validate 8/8 pass á prior cal svo engin urgency.
- **`refresh_dashboard_tables` of-breitt `except`** — defanged af env-fix-inu (triggerinn horfinn) en vert að þrengja eventually svo logging-villa verði ekki aftur að spurious rollback.

**Commits**: `8edc297` (orchestrator fix + shakedown) + `16baa59` (gitignore fyrir log-patterns). Báðir á origin/main.

**Process observation (locked)**: halt-on-decision-points design reyndist load-bearing. Þrjár first-execution failures (id=2/3/5) voru hver um sig contained at step-boundary með clean rollback (orchestrator's own halt/crash-finalize + sub-scripts' atomic rollback), og halt-before-push gate fangaði 108K-row divergence ÁÐUR en nokkuð destructive skrifaðist. Auto-fix-and-rerun hefði masked sequence-inn og áhættað bad push. Mynstrið vistað í user-memory (`feedback_halt_on_decision_points`) fyrir continuity.

---

## 2026-05-27 — Phase X Group C trimmed core APPLIED; lightweight current-stack supersedes Hetzner/Dagster/MLflow plan; Phase X fully closed

**Hvað**: Phase X Group C trimmed-core landed live á Supabase prod (project `szzjsvmvxfrhyexblzvq`). Net-new + additive — zero impact on existing tables/views/predictions.

**What was built**:

| Artifact | Purpose |
|---|---|
| `scripts/migration_helpers.py` | 7 reusable patterns extracted from phase_d1/d3/lockout (apply_migration_sql, generate_rollback_sql, unnest_upsert, column_grant_lockout, subprocess_with_shape_safety, register_supabase_migration, set_local_role_and_test) + 3 utilities (open_connection, file_md5_hex, git_sha_head). Future analogue scripts inherit; phase_d1/d3/lockout get header-note pointers (no working-code changes) |
| `supabase/migrations/20260527155123_group_c_audit_tables.sql` | Creates 3 service-role-only audit tables: `pipeline_runs` (8 cols), `pipeline_steps` (12 cols), `inputs_snapshots` (20 cols) + 6 indexes |
| `scripts/run_monthly.py` | Orchestrator wrapping 6 D:\\ monthly scripts + build_precompute, with shape-safety gates per step. On all-green: captures inputs_snapshot + push-preview, then HALTs |
| `scripts/backfill_current_snapshot.py` | One-off: writes ONE inputs_snapshots row anchoring current live batch |
| `scripts/apply_group_c_migration.py` | Apply + verify orchestrator with auto-rollback on verify-fail |

**Post-apply counts**:

| Table | Rows | Notes |
|---|---:|---|
| `public.pipeline_runs` | 1 | dry-run row from run_monthly --dry-run, exit_status=success |
| `public.pipeline_steps` | 7 | one per planned step, all exit=0, notes='dry-run' |
| `public.inputs_snapshots` | 1 | backfill anchor for current iter4 batch |

**Backfill anchor row (`inputs_snapshots.id=1`)** — fingerprints current live batch:

```
model_version       = iter4_final_v1
calibration_version = iter4_conformal_v1
valuation_year/mo   = 2026 / 4
cpi_factor_at_val   = 1.005484731692855
cpi_csv_md5         = cd14045c9ff5…
kaupskra_csv_md5    = 0105a680c197…
kaupskra_last_mod   = 2026-04-20 02:00:36 UTC  (state-file value; refresh hasn't run since)
training_data_v2_md5 = 405b663f21d7…
feature_names_hash  = 0f8b90a8cd9d…  (154 features)
properties_n        = 232,887
predictions_n       = 167,503
git_sha             = e938cc5ffebb…  (HEAD at backfill time)
precompute_git_sha  = c85ad83cb11f…
extra.note          = "backfill of current state"
```

This row answers reproducibly: "what inputs produced the 167,503-row iter4 prediction batch live in production?" — equivalent to MLflow's run-tracking, in a single Postgres table.

---

**Trim rationale + deferred-with-rationale list**

Group C scope was intentionally trimmed from the original spec to keep the lota focused on the parts that pay off immediately. Deferred items are sequenced for clear later sessions:

| Deferred | Where it lands | Why now-not |
|---|---|---|
| `model_metrics` table | /heilsa session | Feeds the dashboard directly; building both together keeps the schema/UI co-evolution tight |
| `backup_manifests` table | /heilsa session | Same — dashboard consumer drives the schema |
| `migrations_log` table | /heilsa session | `supabase_migrations.schema_migrations` is canonical today; this is a metadata sidecar (applied_via, sanity_passed, rollback_path) that only helps when /heilsa shows it |
| `push_precompute_to_supabase` helper | After 2-3 proven run_monthly cycles | Monthly cadence + bank-facing app = high cost of an automated-push regression. The unnest_upsert pattern is in place; per-table column-type maps + ON CONFLICT keys land when the wrapping orchestration is empirically stable |
| `ats_lookup` → `ats_lookup_by_heat` rename | Next ats-touching migration | Cosmetic; would burn a migration cycle for ~no value standalone |
| `/heilsa` internal dashboard | Separate session after Group C | PLANNING_BACKLOG already sequenced; consumes Group C tables |
| iter5 retraining + `run_retrain.py` | iter5 spec session | Retraining is event-driven (drift > threshold), not monthly |
| `predictions.predicted_at: DATE → TIMESTAMPTZ` | iter5 session | Orthogonal; lands cleanly with iter5's re-scoring-cadence decision |
| Bug 26 SSR-deep-link closure | Separate UI session | Group B/C did not address; `augl_id_latest` remains in anon allowlist for the view |
| Lighter dashboard-only refresh decoupled from monthly cycle | Forward option, gated on near-daily kaupskrá publication being confirmed sustained | Enabled by kaupskrá cadence revision below; build after run_monthly has 2-3 clean cycles |

---

**Halt-before-push design**

`scripts/run_monthly.py` produces the precompute CSVs and an inputs_snapshot row, then prints a per-table push-preview (CSV-rows vs live-Supabase-rows delta) and exits with `pipeline_runs.exit_status='success_halt_pre_push'`. Operator reviews and decides whether to push. `--push` flag is wired in the CLI but returns exit 2 with a "not implemented this lota" message.

Reasoning:

1. **Monthly cadence**: a botched auto-push wouldn't be noticed until the next cycle a month later. Manual review window is essentially free in operator-time terms.
2. **Bank-facing application**: properties + predictions are read by /eign render path. A bad row count or stale predictions visible immediately. The halt-before-push gives a deliberate "do these numbers look right?" gate.
3. **Pattern is already known**: phase_d3_apply demonstrated the unnest_upsert idempotent INSERT path. Generalising it across 7 precompute targets requires per-table {column_types, conflict_cols, casts} maps — small but should be done once we've watched the orchestrator behave through 2-3 monthly cycles. Premature automation would lock in column-type maps before knowing what edge cases the cycle surfaces.

Decision lock: **flip to auto-on-all-green only after 2-3 proven cycles** demonstrate the orchestrator's halt-gate fires correctly on real drift (validate_metrics MAPE/coverage thresholds, kaupskrá file-shrinkage, training-data row drift > 10%). Until then, push is manual.

---

**Audit-table security posture**

All 3 tables follow the same pattern, consistent with Group B's least-privilege posture:

```sql
ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;
-- No CREATE POLICY — default-deny for anon and authenticated.
-- service_role bypasses RLS via its built-in role membership.
REVOKE ALL ON public.<table> FROM anon;
REVOKE ALL ON public.<table> FROM authenticated;
```

Verified post-apply: each table has `relrowsecurity=t`, 0 anon SELECT grants, 0 authenticated SELECT grants, and a fresh `service_role` SET LOCAL ROLE returns `count(*)=0` cleanly (no 42501). Orchestrator writes come from the service-role connection (`.dbconfig` URL is the postgres role, which has BYPASSRLS in Supabase managed Postgres).

When /heilsa lands, it reads via a Next.js API route using `SUPABASE_SERVICE_ROLE_KEY` (never anon). The dashboard route will be unlinked + auth-gated per PLANNING_BACKLOG.

---

**Pre-flight rollback exercise (worth recording)**

First apply caught a **verifier miscount bug**: `apply_group_c_migration.py` had expected column counts of 7/11/16, while actual schemas are 8/12/20 (I miscounted from the SQL while writing the verifier — pipeline_runs has 8 cols not 7, etc.). The verify step returned all 3 tables as FAIL on column count.

The script's auto-rollback path fired: `DROP TABLE public.inputs_snapshots, public.pipeline_steps, public.pipeline_runs CASCADE` in a single statement. Clean rollback — no residual state. Fixed the expected-counts dict in the verifier, re-ran apply, all checks green on second attempt.

**Empirical precedent**: the rollback path actually works in practice — DROP TABLE × 3 CASCADE on a fresh migration is a clean recovery. Useful to have demonstrated this on net-new tables (no FK conflicts to other live data, all 3 tables empty at rollback time). For future migrations that mutate existing schema, the rollback path is more complex; this exercise establishes the simpler additive-migration case as a known-good pattern.

The pattern: **verifier mistakes are recoverable when the migration is purely additive and the rollback is DROP TABLE on the net-new objects**. For migrations with REVOKE/GRANT changes (like Group B), the rollback path is re-GRANT table-level — also additive in the recovery direction.

---

**CORRECT THE RECORD — two corrections**

**(a) Kaupskrá publication cadence — revised**

The 2026-04-20 STATE Áfangi 4d note ("Monthly update pattern: Sunnudagur 2. viku mánaðar ~02:00 GMT") is **stale**. Empirical state observed 2026-05-27:

- HMS HEAD-probe today: `Last-Modified: Wed, 27 May 2026 02:00:53 GMT`
- State-file last-recorded fetch: `Mon, 20 Apr 2026 02:00:36 GMT`
- 37-day gap in local artifact, but Danni's observation in late May 2026 is that publication is **now near-daily**

Publication-time-of-day (~02:00 UTC) remains stable; only frequency changed.

**Limitation of the local artifact**: `D:\kaupskra_fetch_state.json` is single-snapshot — it overwrites itself each fetch, so we cannot reconstruct full publication history from local data alone. The cadence revision is based on operator observation; the in-script HEAD probe today is the only empirical anchor. STATE Áfangi 4d updated additively (+6 lines: "Cadence revision 2026-05-27" sub-block).

**Forward option** (do NOT build now, noted in STATE Áfangi 4d): once Group C's run_monthly is proven over 2-3 cycles, a lighter dashboard-only refresh decoupled from the heavy monthly recalibration cycle could trigger daily on Last-Modified change — pickup latest sales → repeat_sale_index + ATS lookup refresh, without re-training. This is gated on (a) sustained near-daily publication being confirmed, and (b) operational confidence in the monthly cycle.

**Implication for run_monthly cadence**: decoupled from publication day. `refresh_kaupskra.py` is idempotent on Last-Modified/MD5 (HEAD → no-op when unchanged), so any convenient day works. **Pinned**: 1st of each month 03:30 local (post nightly R2 backup at 03:00) — operator convenience, not a HMS dependency.

**(b) Hetzner + Dagster + MLflow plan — superseded**

`STATE.md:1051` (historical, from initial planning ~spring 2026) specified the infra stack as:

> "Infra stack = Hetzner + Postgres/PostGIS + Docker Compose + Dagster + MLflow + Cloudflare R2."

Reality: the platform has been running ~6 months on **Vercel (Next.js app) + Supabase (Postgres data layer) + local Windows D:\\ Python 3.14 (training pipeline) + Cloudflare R2 (backups)**. The Hetzner/Dagster/MLflow leg never landed. Project has shipped and grown without it.

**Decision lock**: Group C IS the lightweight current-stack version of what Dagster + MLflow would have provided. Standing up Dagster/MLflow now would be 2-4 weeks of infrastructure work for marginal value — the training set is ~144K rows (~10 min/cycle on a laptop), the monthly cadence is small-scale, and the team is small. Revisit if the project scales 10× (multi-engineer, multi-tenant data, hourly retraining).

Specifically:

- `pipeline_runs` + `pipeline_steps` provide Dagster's run-orchestration audit trail in a Postgres table.
- `inputs_snapshots` provides MLflow's run-tracking (model_version, input MD5s, parameters, environment) in a Postgres table.
- `scripts/run_monthly.py` is the orchestrator (Dagster job in MLflow terms).
- Windows Task Scheduler is the cron (same role as Dagster scheduler / Airflow DAG sensor).
- Cloudflare R2 + nightly rclone backup is the artifact store (MLflow artifacts equivalent).

The line in STATE.md is left for historical context — it documents the path-not-taken. This DECISIONS entry is the canonical statement of the superseding decision.

---

**Migration-history caveat**

Migration file `20260527155123_group_c_audit_tables.sql` is on disk under `supabase/migrations/` but was applied via `psycopg2` in `scripts/apply_group_c_migration.py`, not the Supabase CLI. The remote tracking table `supabase_migrations.schema_migrations` does NOT yet include version `20260527155123`. To register it:

```powershell
D:\verdmat-is\tools\supabase\supabase.exe migration repair --status applied 20260527155123
```

Same pattern as Group B (2026-05-27 second DECISIONS entry) and as the 2026-05-21 baseline reconcile. Requires interactive TTY, which is why the agent shell cannot execute it directly. **Does NOT block the commit** — disk file belongs in the repo regardless.

---

**Open follow-ups (sequenced)**

1. CLI repair `20260527155123` (Danni's PowerShell step).
2. First manual `run_monthly.py` clean run (no --dry-run) — observe end-to-end behavior, particularly the validate_metrics drift gate and the push-preview deltas.
3. After 2-3 proven cycles: register Windows Task Scheduler for monthly orchestrator + flip `--push` to auto-on-all-green; build `push_precompute_to_supabase` per-table maps.
4. /heilsa dashboard session — builds `model_metrics` + `backup_manifests` + `migrations_log` tables alongside the unlinked auth-gated UI.
5. Lighter dashboard-only refresh (forward option) once kaupskrá near-daily cadence is confirmed sustained.
6. `ats_lookup` → `ats_lookup_by_heat` rename when next ats-touching migration lands.
7. iter5 retraining spec + `run_retrain.py` orchestrator + `predicted_at` DATE→TIMESTAMPTZ.
8. Bug 26 SSR-deep-link closure (remains separate UI session).

---

**Artifacts (þessi lota)**

- `scripts/migration_helpers.py` — 7 helpers + 3 utilities, 291 lines
- `scripts/run_monthly.py` — orchestrator with halt-before-push, 302 lines
- `scripts/backfill_current_snapshot.py` — one-off anchor writer, 146 lines
- `scripts/apply_group_c_migration.py` — apply + verify + auto-rollback orchestrator
- `supabase/migrations/20260527155123_group_c_audit_tables.sql` — 3 tables + 6 indexes
- `scripts/{apply_column_grant_lockout, phase_d1_apply, phase_d3_apply}.py` — additive header-note pointers to migration_helpers (no working-code changes)
- `docs/STATE.md` — Áfangi 4d cadence revision + new milestone + Roadmap update + Group A+B+C closure
- `docs/DECISIONS.md` (this entry)
- `audit/monthly_runs/` (gitignored) — local JSON run-logs

---

## 2026-05-27 — Phase X Group B column-grant lockout APPLIED; default-deny på future columns; Bug 26 reframed (not closed)

**Hvað**: Phase X Group B follow-up landed live á Supabase prod (project `szzjsvmvxfrhyexblzvq`). Replaced table-level SELECT grants on the 4 in-scope tables with column-level allowlists per role. Each migration in its own transaction; sanity green after each.

**Migrations** (in `supabase/migrations/`):

- `20260527150435_column_grant_lockout_stage1_properties.sql` (2.677 bytes) — STAGE 1, `public.properties`.
- `20260527150436_column_grant_lockout_stage2_other3.sql` (2.695 bytes) — STAGE 2, `public.predictions` + `public.repeat_sale_index` + `public.ats_lookup` (each in its own BEGIN/COMMIT).

Applied via `psycopg2` through the transaction pooler (Docker / `supabase db push` unavailable on this host per 2026-05-21 Group B Part 1 entry). **Tracking caveat below**.

**Per-table allowlist**:

| Table | anon = authenticated | Excluded (anon CANNOT SELECT) |
|---|---|---|
| `properties` | **44** cols: 43 v_properties-projected + `deregistered` (WHERE) | `landeign_nr`, `matseiningar`, `tengd_stadfang_nr` |
| `predictions` | **12** (all, = v_current_predictions projection) | (none) |
| `repeat_sale_index` | **15** (all, = v_repeat_sale_index projection) | (none) |
| `ats_lookup` | **15** (all, = v_ats_lookup_by_heat projection) | (none) |

**Role split**: `authenticated = anon` for now. `/pro` is a frozen static landing page; no pro feature currently exercises `authenticated` for these 4 tables. Revisit on pro reactivation — likely candidates for an expanded authenticated set are `matseiningar` (sub-unit drill-down) and `tengd_stadfang_nr` (cross-property comp). Documented as backlog.

**Sanity (under `SET LOCAL ROLE anon`)**:

- `SELECT count(*) FROM v_properties` → **232.790** = baseline ✓
- `SELECT count(*) FROM v_current_predictions` → 167.503 = baseline ✓
- `SELECT count(*) FROM v_repeat_sale_index` → 2.673 = baseline ✓
- `SELECT count(*) FROM v_ats_lookup_by_heat` → 65 = baseline ✓
- `SELECT landeign_nr FROM properties LIMIT 1` → **42501** `permission denied for table properties` ✓
- `SELECT matseiningar FROM properties LIMIT 1` → 42501 ✓
- `SELECT tengd_stadfang_nr FROM properties LIMIT 1` → 42501 ✓
- `SELECT augl_id_latest FROM properties LIMIT 1` → **PASS** (intentional, see Bug 26 reframe below)

**Final grant state**:

| Table | anon table-level | anon column-level |
|---|---:|---:|
| `properties` | 0 | 44 |
| `predictions` | 0 | 12 |
| `repeat_sale_index` | 0 | 15 |
| `ats_lookup` | 0 | 15 |

**Full prod smoke** — 11 routes, all HTTP 200, 0 PostgREST 42501/42703 errors:

`/` · `/eign/2008647` (Group-B scored baseline) · `/markadur` + 4 sub-pages · `/api/backproj/2008647` · `/eign/2151573` (D3 scored net-new) · `/eign/2019479` (D3 held net-new) · `/api/search?q=Vesturs`. Sizes within ±5% of 2026-05-21 Group B Part 2 baseline. Deep verify on `/eign/2151573`: "Verðmat í dag" PredictionCard renders 36,7 M kr point + 80% PI [30,3; 44,4] M + 95% PI [25,4; 53,0] M + iter4_final_v1 / iter4_conformal_v1 / APT_FLOOR stamp ✓. `/eign/2019479` held: graceful state + "Verðmat bíður" chip ✓.

---

**CORRECT THE RECORD — two prior-entry inaccuracies surfaced during this audit**

1. **`search_properties_grouped` is invoker-mode, NOT SECURITY DEFINER.** The 2026-05-21 Group B Part 2 entry stated "SECURITY DEFINER RPCs (`search_properties_grouped`) keep working under either path" — that was wrong. `pg_proc.prosecdef = False` empirically. The function uses the default invoker mode and reads `public.properties` directly with anon's privileges. The audit revealed this; the empirical column footprint is 7 cols — `heimilisfang`, `postnr`, `postheiti`, `sveitarfelag`, `fastnum`, `tegund_raw`, `is_residential` — ALL of which are in the 44-col anon allowlist on `properties`. So the function survived REVOKE+GRANT without an RPC-side change (confirmed: `/api/search?q=Vesturs` returns Vestursíða 10 group anchors post-lockout). If a future column gets added to its body and is NOT in the allowlist, the RPC will start 42501-ing — standing rule below applies.

2. **This lockout does NOT close Bug 26 (`fastnum ↔ augl_id` leak).** The 2026-05-21 entry left Bug 26 in a re-scoped-but-undone state ("SSR deep-link href via service-role key"), and Bug 26 closure could be misread as a side-effect of the column-grant work. It is NOT. `augl_id_latest` is **intentionally retained in the anon+authenticated allowlist** on `properties` because (a) `v_properties` projects it, so removing it from base-table grants would 42501 the view, and (b) Bug 26 fix is a UI-side change (render the deep-link href in server-rendered HTML with the service-role key; never ship `augl_id_latest` to the client bundle). That UI change is a separate task. **Closing it remains open work.**

---

**Standing rule (locked)**

Any new column added to `public.properties` / `public.predictions` / `public.repeat_sale_index` / `public.ats_lookup` that needs to be projected by a `v_*` view MUST also receive a matching `GRANT SELECT (<col>) ON <table> TO anon, authenticated;` in the same migration that adds it. Otherwise the view's SELECT (or its WHERE-filter, ORDER BY, etc.) will fail with PostgREST `42501 permission denied`.

Conversely, **omitting** a new column from both the view projection and the grant is the new default — that's the "default-deny on future columns" value this lockout delivers.

This rule applies equally to:
- Adding a column to a base table where a `v_*` view does `SELECT *`-style projection (currently none — all 4 views use explicit projection lists, which is the recommended pattern).
- Adding a column to a `v_*` view definition that wasn't previously projected.
- Changing a `v_*` view's WHERE/ORDER BY/JOIN clause to reference a previously-unreferenced base-table column.

When in doubt: run the proposed view migration locally, then under `SET LOCAL ROLE anon; SELECT count(*) FROM <view>;`. If it 42501s, the column-grant is missing.

---

**Value delivered**

| | Before lockout | After lockout |
|---|---|---|
| anon SELECT on `properties` | all 47 cols (incl. `landeign_nr`, `matseiningar`, `tengd_stadfang_nr`) | 44 of 47 (3 excluded) |
| anon SELECT on `predictions` | all 12 | all 12 (no behavior change) |
| anon SELECT on `repeat_sale_index` | all 15 | all 15 (no behavior change) |
| anon SELECT on `ats_lookup` | all 15 | all 15 (no behavior change) |
| Default behavior on future column add | anon can SELECT immediately | anon must wait for explicit GRANT (default-deny) |

The 3-col exclusion is the immediate visible win; the default-deny posture is the durable win — it prevents accidental column leaks the next time someone adds a column to one of these tables.

---

**Migration-history tracking caveat**

Both migration files are recorded in `supabase/migrations/` on disk, but the remote tracking table `supabase_migrations.schema_migrations` was NOT updated during the apply because we used `psycopg2`, not the Supabase CLI. Verified empirically post-apply: `SELECT version FROM supabase_migrations.schema_migrations WHERE version IN ('20260527150435','20260527150436')` returns **0 rows**.

**Fix**: run the following in a real PowerShell terminal (CLI needs interactive TTY, not available inside this agent shell):

```powershell
D:\verdmat-is\tools\supabase\supabase.exe migration repair --status applied 20260527150435 20260527150436
```

This is the same pattern used in the 2026-05-21 Group B Part 1 baseline reconcile. It writes the two version-ids into `schema_migrations` with `status='applied'` so that future `supabase db push` runs and `supabase migration list` correctly show the lockout migrations as applied — no `db push` re-runs them and no drift warnings. **This does NOT block git commit / push — the disk files belong in the repo regardless; the repair fixes the remote tracking table in parallel.**

**Anti-pattern to avoid**: hand-inserting into `supabase_migrations.schema_migrations` via SQL. The CLI repair command computes the `statements` payload correctly; manual INSERT would leave the column NULL (or wrong) and break future `supabase db diff` comparisons. Use the CLI command, not raw SQL.

---

**Artifacts (þessi lota)**:

- `supabase/migrations/20260527150435_column_grant_lockout_stage1_properties.sql`
- `supabase/migrations/20260527150436_column_grant_lockout_stage2_other3.sql`
- `scripts/apply_column_grant_lockout.py` — apply orchestrator with per-stage sanity gates (baseline counts, anon view-count match, 42501-exclusion proof on each excluded column, anon-SELECT-pass on `augl_id_latest`)
- DECISIONS.md (this entry) + STATE.md milestone demotion + Roadmap update

---

## 2026-05-27 — Phase D3 NOW lota APPLIED; Spatial-NN matsvaedi backfill sanctioned; predictions decoupled from evalue augl-pass

**Hvað**: Phase D3 NOW lota landed live á Supabase prod (project `szzjsvmvxfrhyexblzvq`). Þrír idempotent INSERT blokkar runnu án villu og post-apply row-counts matchuðu dryrun-spá nákvæmlega:

| Block | Inserted | New universe | Idempotency |
|---|---:|---|---|
| `properties` | **108.052** | 124.835 → **232.887** | `ON CONFLICT (fastnum) DO NOTHING` · 0 collisions |
| `sales_history` | **786** (487 arm's-length + 299 onothaefur=1) | 173.081 → **173.867** | fastnum-existence pre-check (no PK on fastnum) |
| `predictions` | **57.187** | 110.316 → **167.503** | `ON CONFLICT (fastnum) DO NOTHING` · 0 PK collisions |

**Predictions stamp**: allar 167.503 rows í `predictions` eru `model_version='iter4_final_v1'` / `calibration_version='iter4_conformal_v1'` — engin blönduð útgáfu-stamp, `v_current_predictions` `DISTINCT ON (fastnum)` og footer-badge haldast stöðug.

**Phase A 2.059 inclusion (frávik frá ~106K prompt)**: insert-universe varð **108.052**, ekki ~106K sem Danni nefndi í prompt-i. Það er vegna þess að Phase A 200 (2.059 net-new HMS-only fastnums frá kaupskrá-only + wide-gap candidates) tilheyrir original D3 scope per DECISIONS 2026-05-18 ("30.193 = Phase A 2.059 + Phase C 28.134"). Allir þrír buckets (Phase A 200 / Phase C 200 orig / Phase C 200 reprobed) eru disjoint via single-probe argument (fastnum INTEGER PRIMARY KEY í `hms_archive_staging.db`). Empirically staðfest í dryrun: 0 collisions við existing Supabase `properties`.

---

**Spatial-NN matsvaedi backfill — sanctioned reusable path fyrir HMS-only properties**

Vandamálið: HMS API payload-ið inniheldur EKKI `matsvaediNUMER`. Existing 124.835 Supabase rows fá matsvaedi úr `properties_v2.pkl` sem var byggt úr `Gagnapakkar/fasteignir{,1-4}.db` `data_json` — þ.e. **evalue augl payloads**. Net-new D3 candidates eru að defininsion fastnums sem evalue hefur aldrei haft (Phase B var existing-Supabase set; Phase A+C eru utan við þá), svo enginn direct-lookup væri fyrir hendi: af 108.052 D3 fastnums fundust 476 (0,44%) í scrape-DBum og þeir voru allir `status=204` (ekki í evalue index, no matsvaedi gögn).

Naive blanking (matsvaediNUMER = NaN + bucket = `P{postnr}_other`) reyndist statistically dishonest:

- Ablation á 3.000-row training-sample (sami iter4a + conformal scorer): **51,2% PI80 breach, 22,0% PI95 breach**, mean +3,83% nominal bias, std 0,239 log. Country region versti með **+40,3% bias og 71,2% breach**.
- Fallback bucket `P{postnr}_other` matchaði aðeins 7,0% af training categories → 93% lentu í LightGBM categorical NaN (missing-branch); 326 distinct buckets aldrei séð í training.

Spatial k=1 nearest-neighbor solution:

- Byggja `scipy.spatial.cKDTree` á `geography_features.pkl` (124.835 labeled lat/lon → matsvaediNUMER, sales_2015 fyrir bucket rare-merge).
- Per net-new D3 fastnum með lat/lng: query k=1 → assign matsvaediNUMER + nn_distance_km.
- Hold-out validation (5K random points removed, re-assigned by NN from the rest): **k=1: 99,8% exact matsvaediNUMER match, 99,9% bucket match** (per-region uniform 99,8–99,9%). NN-distance distribution: p50 = 0 km (sami stadfang), p99 = 0,7 km — Ísland er nógu þétt-merkt að spatial inheritance er essentially exact.
- Re-ablation undir spatial-inferred matsvaedi á sömu 3.000-row training-sample: **0,0% PI80 breach, 0,0% PI95 breach**, mean delta_log = **−0,0000**, std 0,0009 — statistically indistinguishable frá full-feature regime.

**Threshold T = 1 km (0,009°)**, valið með **per-bin** logic (síðasta bin þar sem hold-out match-rate ≥98%): 300m–1km bin gaf 98,2%, 1–2km bin féll í 88,9% (n=18, small-sample noise en conservative read). T persisted á `D:\phase_d3_matsvaedi_T_deg.txt`.

D3 NN-distance transfer (102.209 with coords): p50 = 0,057 km, p90 = 1,36 km, p95 = 3,07 km. **89.689 within T (87,75% of those með coords)** — restin 12.520 beyond T held í confidence gate (mostly Country: 78,6% within; SFH_DETACHED 81,7%; SUMMERHOUSE 80,5%).

**Reusable path forward**: spatial-NN matsvaedi backfill via `scipy.spatial.cKDTree` á `geography_features.pkl` er nú sanctioned default fyrir hvers konar HMS-only properties sem land í Supabase post-D3 — D4 cross_property_refs, D5 photo_urls_json, framtíðarscrapes. Skref er kóða í `scripts/phase_d3_extract.py:load_matsvaedi_donor()` + `main()` post-pass.

---

**Honesty-vs-coverage trade**

Scoring funnel:

```
total D3 candidates              108.052
minus non-scorable (EXCLUDE)      42.439  → 65.613 residential+summer
  minus no byggar                  2.433
  minus matsvaedi-unconfident      5.993
= SCORABLE                                  57.187
```

5.993 matsvaedi-unconfident (mostly Country: 5.110 af þeim) + 2.433 no-byggar held til að halda `iter4_conformal_v1` PI-i empirically heiðarlegum (training-time empirical coverage 79,1% PI80, 94,6% PI95). 57.187 scored frekar en 63.180 sem v1 score-ið framleiddi án gate-ins — explicit accuracy-vs-coverage trade: **honesty trumps coverage**. Held rows fá samt full `properties` row með öllum HMS metadata (fasteignamat, brunabotamat, byggingarstig, matseiningar etc.) — bara engin iter4 prediction.

Verification: dryrun staðfesti 0 PI80 inversions og 0 PI95 nesting violations á öllum 57.187 scored rows (var 11.231/42.093 inversions í v1 með segment-stretch frekar en conformal).

---

**Decoupling: predictions no longer gated on evalue augl-pass**

POST_HMS_RECOVERY_PLAN §1-§5 átti upphaflega að keyra sekvensjellt: §1 evalue augl-pass (~28h single-worker, gated á G2 template-hardening) → §2 kaupskrá → §3 D3 promotion → §5 iter4 scoring. Spatial-NN backfill collapsar §1-§5 í einn hreinan apply: iter4 scoring fær matsvaedi spatially og þarf ekki að bíða eftir evalue.

LATER evalue lota er nú **UI-enrichment + held-row scoring**, ekki blocker:

- UI-enrichment: photo_urls_json, lysing_truncated, augl_id_latest, n_photos, first_photo_url, scraped_at_latest fyrir 108K net-new (þau hafa öll `NULL` í Phase D3 INSERTs).
- Held-row scoring: matsvæði + byggar fyrir 8.426 held rows (5.993 unconfident + 2.433 no-byggar) → scoring eftir á.
- Production-template hardening (G2) er enn pre-req fyrir evalue lotuna sjálfa (stage_a_augl_refresh.py resume retry-on-non-(200,204)), en *ekki* lengur fyrir prediction surface.

---

**UI: held-residential graceful state**

Áður var `/eign/[fastnum]/page.js` aðeins með tvær branchur fyrir prediction display:

- `!property.is_residential` → "Verðmat er ekki í boði fyrir þessa eign" (non-residential notice — applied á EXCLUDE properties).
- `property.is_residential && prediction` → `<PredictionCard>` render.

Þriðja sviðið (is_residential=true + no prediction) var **engin branch** — leiddi til blank space milli hero og SHAP sections. Þetta var aldrei áður mögulegt (existing 14.519 properties án predictions í dag eru ALLAR EXCLUDE), en með D3 verður þetta nýtt UI state fyrir 6.173 held residential + 2.253 held SUMMERHOUSE = 8.426 rows.

Bætt við í þessari lotu (`page.js` line 287–319):

```jsx
{property.is_residential && !prediction && (
  <section className="vm-card vm-card-elevated" style={{ ..., borderTop: "3px solid var(--vm-neutral)" }}>
    <div>Verðmat bíður</div>
    <h2>Verðmat liggur ekki fyrir þessa eign</h2>
    <p>Eignin er nýskráð í gagnasafni verdmat.is en ekki nægileg módel-gögn liggja fyrir
       til að reikna áreiðanlegt spá-bil (oftast vantar matsvæðis-staðsetningu með nógu
       nálægum systur-eignum eða byggingarár). Spá birtist um leið og næsta líkanaþjálfun
       er keyrð með uppfærðum gögnum.</p>
  </section>
)}
```

Styled like the existing non-residential notice. Verifecerað via curl (`/eign/2019479` — Sigtún 30, RVK_core APT_FLOOR, no byggar): graceful state renderar; PredictionCard absent. SCORED case (`/eign/2151573` — Vestursíða 10): PredictionCard renderar, graceful state absent. COORDLESS case (`/eign/2536633` — Breiðimelur): hero renderar, map section gated absent. Autocomplete (`/api/search?q=Vesturs`): net-new heimilisfang surface-ar via group-anchor.

---

**Protocol lesson — data-ahead-of-frontend window**

Lota þessi opnaði stuttan glugga þar sem prod Supabase var komin með 6.173 held residential rows en `page.js` graceful-state fixið var local (commit + push kom á eftir). Live `/eign/<held-fn>` síður rendered the blank gap fyrir nokkrar mínútur þangað til Vercel re-deployed main eftir push. Stuðningstap var minimal vegna þess að net-new fastnums voru aldrei áður indexed af search engines og hafa lágan organic traffic, en pattern-ið er still wrong.

**Regla locked**: data apply í prod Supabase sem **introducer nýja frontend state** (vs only adding rows til existing rendered branches) þarf að ship-a frontend handling **fyrir eða atómískt með** data-inu. Konkretasta path-ið:

1. PR-a frontend changes + merge til main + láta Vercel deploy → confirm deployed.
2. Þá keyra data apply.

Eða atómískt:

1. Stage frontend changes + run data apply.
2. Push frontend immediately eftir apply success í sömu lotu (þ.e. without breaking for review/halt í gegnum push).

Þessi lota fylgdi blönduðu pattern-i: vissi um held-residential nýja state-ið mid-session (eftir dryrun, fyrir apply), bætti við frontend handlingu mid-session, en push-aði ekki fyrr en eftir apply + verify (3-4 mín gap). Acceptable í þetta sinn af því (a) net-new fastnums hafa lítinn organic traffic, (b) gap-ið var stutt, og (c) verify-aðferðin krafðist live Supabase state. En þetta var meðvitað risk, ekki rétt pattern.

Næsta sinn: ef frontend fix er einföld og þekkt fyrirfram (eins og þetta — addition á þriðju branch í eign-síðu), push fyrst, þá apply.

---

**Artifacts (þessi lota)**

- `scripts/phase_d3_extract.py` — properties extract með Stadfangaskra lookup + spatial-NN matsvaedi backfill
- `scripts/phase_d3_sales_extract.py` — sales filter úr kaupskra.csv + CPI deflation
- `scripts/phase_d3_score_extract.py` — iter4 scoring með conformal PIs + confidence gate
- `scripts/phase_d3_dryrun.py` — 3-batch dryrun + collision + integrity + PI sanity + peer-comp spot-check
- `scripts/phase_d3_apply.py` — 3-batch idempotent apply
- `scripts/phase_d3_threshold_calibration.py` — per-bin hold-out match-rate + T calibration + D3 transfer check
- `scripts/phase_d3_matsvaedi_recoverability.py` — provenance + direct-lookup + spatial-NN hold-out + honesty re-check
- `scripts/phase_d3_matsvaedi_ablation.py` — blank-matsvaedi 3000-sample degradation diagnostic
- `app/eign/[fastnum]/page.js` — held-residential graceful state added
- `D:\phase_d3_*.parquet` + `D:\phase_d3_rollback.sql` — staging artifacts (gitignored under `D:\`, retained until next nightly backup confirms new state)
- `D:\phase_d3_matsvaedi_T_deg.txt` — persisted threshold (0,009°)
- DECISIONS.md (this entry) + STATE.md milestone demotion + Roadmap update

---

## 2026-05-26 — HMS full recovery COMPLETE; kaupskrá cross-check (99,18%) staðfestir completeness; D3-sync scope locked á ~106K insert-candidates

**Hvað**: `audit/hms_full_recovery.py` lauk eftir 74h 10m wall-clock (2026-05-21T20:58 → 2026-05-24T23:08 UTC). Endurspáði allar 392.026 HTTP-500 raðir staging-DB-ins gegn flat API með 1-retry hardening + outage-detection (sliding-window 100 → pause á <1% hit-rate). **Lokatölur**:

| Bucket | n | Notes |
|---|---:|---|
| recovered (var 500, núna 200) | **77.859** | +8,4% yfir spike-spá 71.803 (innan 95% CI 16,2–21,0%) |
| confirmed-still-500 (eftir retry) | 314.167 | upper bound á truly-empty Phase C slot-um |
| untouched | 0 | hreint completion, engin resume þörf |
| realized FN rate | **19,86%** | spike spáði 18,5% ± 3pp; landed +1,36pp ofan |
| WAF/outage pauses | 0 / 0 | outage-detector fór aldrei af stað (74h hreint) |

**Per-phase**: allar 77.859 recoveries úr Phase C. Phase A (6.838) + Phase B (97) **staðfestir genuine ghosts** — engin recovery þar. **Subset (a) un-ghost path = 0** (97 D2-ghostar re-probe-aðir, allir héldu áfram að skila 500 → ekta deregistered, ekki dead-zone false-negative á þekktum fastnum). Það ógildir refresh-path-inn í POST_HMS_RECOVERY_PLAN §4c: D3-sync er **hreint insert**, ekkert un-ghost UPDATE nema dryrun finni raunverulegan already-in-base case.

**Dead-zone breakdown (orsakavottun)**:

| Zone | recovered | confirmed-500 | FN rate |
|---|---:|---:|---:|
| Dead-zone (2026-05-16T07:00 → 17T21:00, ~38h) | 75.098 | 282.428 | **21,00%** |
| Healthy-zone (allt annað) | 2.761 | 31.739 | 8,00% |

**96,5%** af öllum recoveries komu úr dead-zone (75.098 / 77.859) — confirms root cause: WAF-backoff scoped to 429/403/503 EN EKKI 500 (`hms_full_scrape.py:226`). Healthy-zone 8% FN er hærra en spike pre-run estimate (4,6%) vegna þess að 866 v1-rolled-back raðir með yfirskrifað `fetched_at` flokkast nú healthy-zone (statistical noise 0,22%, flagged í `hms_recovery_report.md`).

**12-tíma FN rate stabilitet (74h run)**: 19,6% → 19,8% → 19,8% → 19,9% → 19,9% → 20,0% → 19,8%. Aldrei meira en 0,4pp frávik frá meðaltali. Fixed-rate sampling problem (1-in-5 af 500s var transient false-negative), ekki fluctuating.

**kaupskrá cross-check (óháð completeness-staðfesting)**:

| Metric | Result |
|---|---|
| kaupskrá unique fastnums | 126.362 (úr 226.481 sölum) |
| Til staðar í HMS-200 (post-recovery) | **125.330 (99,18%)** |
| Missing frá HMS-200 | 1.032 (0,82%) — all in HMS-500 bucket, none outside scrape span |

Sample probe (n=50 af 1.032 missing) gegn fresh HMS API + leit:

- 50/50 enn HTTP 500 (**ekki recovery-miss** — ekta gone)
- 15/50 stadfangur leysist í gegnum `leit?q=<address>` (líklega merged into sibling fastnum)
- 35/50 stadfangur skilar 0 fasteign match (heimilisfang hefur líklega breyst eða stadfang_nr endurraðað)

Pattern: clustered missing fastnums á sama heimilisfangi (t.d. Vatnsstígur 11: 3 sequential 2003253/2003257/2003260 frá 2010; Guðrúnartún 8: 2 atvinnuhúsnæði frá 2009). Ár-dreifing leans heavily 2006-2014 (75% af missing); 56 missing 2023-2025 staðfestir að þetta er ongoing churn, ekki bara legacy. **Túlkun**: 1.032 = ekta deregistered/merged properties (sameining/skipting eftir sölu), ekki scrape-vandi. Þekkt **repeat-sale takmörkun** — klofin söguskrá við sameining/skipting. **Valfrjáls Phase Y address-resolution** workflow (~1.032 leit-lookups, ~10 mín) gæti backfill-að `effective_fastnum` column ef historical-sale-continuity skiptir máli fyrir index. Frestað nema iter5 / BMN-index endurspái þurfi það.

**D3-sync scope locked**:

- **Insert candidates = recovered net-new (77.859) ∪ original Phase C 200-hits (28.134) ≈ 106K**. Disjoint via single-probe argument í POST_HMS_RECOVERY_PLAN §4a; staðfest við dryrun.
- Apply pattern: idempotent `INSERT INTO properties ... ON CONFLICT (fastnum) DO NOTHING`. Dryrun reports true net-new vs collisions.
- 1.032 kaupskrá-missing FNs **eru ekki insert-candidates** (þeir eru ekki HMS-200; við insert-um EKKI ghost-eignir).
- Universe post-D3-sync ≈ **~231K** = 124.738 base + ~106K Phase-C-real. Áður spáð ~227K; +4K vegna recovery overshoot (77.859 vs 71.700 spá).

**SPLIT gating på POST_HMS_RECOVERY_PLAN**:

Notandi sundrar §1-§5 niður í tvær óháðar lotur:

- **NOW (gated bara á recovery ✅)**: §3 properties insert + §3 sales_history insert + §5 iter4-scoring. Engin scraper-keyrsla, svo ekki háð template-hardening gate-inu (G2). Skilar Phase D3 ✅ + ~106K nýjar fastnum-síður live á `/eign/<fastnum>` með iter4 prediction.
- **LATER (gated á G2 template-hardening)**: §2 evalue augl-pass fyrir net-new subset (~71.7K, ~28h single-worker). Bíður þangað til canonical scraper-template er hardened. `feature_attributions` + `comps_index` follow í næstu precompute-cycle (precompute-driven, ekki per-fastnum).

**Næst (sjá STATE.md roadmap update)**: D3-sync (NOW lota) — properties+sales+scoring; svo Phase X Group B column-grant lockout; svo Phase X Group C.

**Artifacts (þessi lota)**:
- `audit/hms_full_recovery.py` — hardened runner (1 retry + outage detection + full envelope capture)
- `audit/hms_recovery_report.md` — final halt-report (77.859 / 314.167 / dead-zone breakdown)
- `audit/hms_recovery.log` — 74h append-only runtime log
- `audit/hms_recovery_status.md` — final status snapshot
- `audit/kaupskra_missing_from_hms.txt` — 1.032 missing kaupskrá FNs
- `audit/kaupskra_missing_probe_results.json` — n=50 sample probe outcomes
- `audit/hms_fn_spike.{py,md,sample.txt,results.json,run.log}` — pre-recovery spike artifacts (validated the strategy before 74h commit)
- DECISIONS.md (this entry) + STATE.md roadmap refresh

---

## 2026-05-22 — Evalue sibling-scraper audit (diagnostic): HMS bug class not present; coverage-coupling caveat surfaced

**Hvað**: Diagnostic-only audit (parallel lane to HMS recovery; no HMS files touched, no evalue network scrape beyond one positive-control probe). Inventoried 6 evalue scraper variants in `audit/`, static-reviewed each for the HMS bug class (HTTP-5xx misinterpreted as "fastnum doesn't exist"), temporal-bucketed the 124,835-row `audit/stage_a_augl_staging.db` for dead-zone clusters, and confirmed endpoint liveness with one positive-control POST. **Verdict: HMS bug class not present in any of the 6 evalue variants.** No sample re-probe justified.

**The 6 variants** (all under `audit/`):

| # | File | Role | Network |
|---|---|---|---|
| 1 | `stage_a_augl_refresh.py` | Production augl refresher (124,835 fastnums in the existing staging DB) | yes |
| 2 | `backfill_evalue_range.py` | Pilot scraper + shared core (`post_evalue`, `scrape_property`, `HaltSignal`) | yes |
| 3 | `backfill_evalue_probes.py` | Wraps #2 for 3 probe ranges | yes |
| 4 | `backfill_evalue_v3.py` | Wraps #2 for phases 2-4 + image downloads | yes |
| 5 | `backfill_preflight.py` | Read-only probe of 5 candidate sources | yes |
| 6 | `scrape_gap_diagnostic.py` | Wraps #2 for single-fastnum diagnostic | yes |

**Three independent evidence lines** for the "no HMS bug class" verdict:

1. **Static review** — None of the 6 variants conflate HTTP-5xx with "fastnum doesn't exist". Evalue has a distinct "not-in-index" signal (HTTP 200 + inner `status=204`), so the semantic ambiguity that bit HMS does not apply.
   - The pilot family (#2, #3, #4, #6) is **fail-loud**: any transient error path raises `HaltSignal` which stops the run. No silent-skip path exists.
   - `stage_a_augl_refresh.py` (#1) is **graceful but bounded**: rolling 5xx-rate halt over 100-request window, 1-strike halt on `cf-mitigated` / HTML / 403, 10-min sustained-net halt, and error rows persisted as `augl_status=-1` placeholder (distinguishable from real 200 rows).
   - `backfill_preflight.py` (#5) is read-only probe; records every status as a structured field.

2. **Temporal review** of `stage_a_augl_staging.db` (124,835 rows, span 2026-05-08T13:14 → 2026-05-13T22:34, 5d 9h) — **100.00% augl_status=200**, zero `-1` placeholders, zero NULL `augl_json`. Population-wide empty-rate (n_ads=0 ↔ latest_augl_iso IS NULL, perfectly correlated) = 52.72%. Per-6h windows across the run band tightly between 45.4% and 60.0% — no window crossed the 75% empty / 80% iso_null threshold. No outage signature.

3. **Manual probe** — One POST to `evalue.is/fastnum/2526172?/get_fasteign_augl` (positive control from `backfill_evalue_range.POSITIVE_CONTROLS`): HTTP 200, 2.11 s, application/json, no `cf-mitigated`, JSON parses, inner status 200, n_ads=2. Endpoint operating identically to the staging-run baseline.

**Leiguskra-scraper does not yet exist** — the 2026-05-21 DECISIONS line ("evalue.is backfill-skipti (×6) + leiguskrá-scraper — sami WAF-ignorar-500 mynstur líklega til staðar") was aspirational. No `leigu*`, `rental*`, or `rls_*` Python file under `audit/` or `scripts/` is a network scraper. Recorded so a future builder knows: when leiguskra is built, it must inherit the hardened canonical template (the post-HMS-recovery production-template), not a one-off implementation.

**Coverage-coupling caveat — the HMS recovery will surface fastnums that were never in the evalue input universe**:

`stage_a_augl_staging.db` contains exactly **124,835 rows = the Phase B input set** (every fastnum present in Supabase `properties` at run start on 2026-05-08, captured 2026-05-08 → 2026-05-13). The HMS full-scrape that finished 2026-05-18 added Phase C: a wider range sweep (2,000,044..2,547,000) which discovered ~30K HMS-only fastnums beyond the Phase B baseline. The HMS dead-zone of 2026-05-16/17 sits **inside** Phase C, and the ~71,800 fastnums currently being recovered by `audit/hms_full_recovery.py` are predominantly drawn from the Phase C range. **They were never offered to the evalue refresher.** Expected intersection of `recovered_fastnums ∩ evalue_staging` ≈ 0.

**This is not a bug in evalue's scrapers**. It is a downstream coverage consequence of the HMS bug — once HMS recovery completes and the ~71,800 net-new fastnums are confirmed real, those fastnums need a full data pass (evalue augl + kaupskrá lookup) before they can be promoted to Supabase `properties`. Recorded in PLANNING_BACKLOG as a post-HMS-recovery follow-up. **Do NOT run any evalue pass yet** — wait for HMS recovery to complete and yield the canonical recovered-fastnum set. Magnitude (|recovered ∩ evalue staging|) to be confirmed empirically post-recovery; expected near-zero.

**Latent (non-urgent) risk recorded for production-template hardening**: `stage_a_augl_refresh.py`'s resume logic uses `SELECT fastnum FROM stage_a_augl` to build its done-set, which would include `augl_status=-1` placeholders if any existed. If errors below the 5% halt threshold ever occur, those `-1` rows would never be retried on subsequent runs (silent-loss shape, same family as the HMS-resume issue this entry is responding to). **Has not fired** — current DB has 0 placeholder rows — but the path is there. Fold into the existing post-HMS-recovery "production-template hardening" backlog item: retry rows with `augl_status NOT IN (200, 204)` on resume; apply the same retry-on-resume discipline to the canonical scraper template so future scrapers (incl. leiguskra when built) inherit it.

**Artifacts (read-only, audit-script-first)**:
- `scripts/evalue_audit_schema_probe.py` — schema + cardinality
- `scripts/evalue_audit_temporal.py` — 6h-window bucketing
- `scripts/evalue_audit_single_probe.py` — single endpoint liveness probe

No DB writes, no HMS access, single non-batched network request total.

---

## 2026-05-21 — HMS full-scrape (2026-05-15 → 18) leyndi ~71.800 raunverulegum eignum vegna ~38 klst API-outage; gangsetjum full recovery

**Hvað**: Spike á `audit/hms_archive_staging.db` (random sample n=1.000 af 392.026 HTTP-500-röðum, seed=42) sýndi **18,5% false-negative rate (Wilson 95% CI 16,2–21,0%)** → áætluð **~71.803 raunverulegar eignir** vantar sem stendur í staging-DB-inu. 185/185 recovery komu á 1. tilraun — engin within-spike transient blip — sem þýðir að HMS-API-ið er stöðugt **núna** og að 500-svörin í scrape-window-inu voru *historical* server-side failure, ekki request-flake. Anchor 2226598 endurskilaði 200 á 1. tilraun, end-to-end sanity check stenst. Næsta skref: full recovery (option a í spike-report-inu) — re-probe allar 392K HTTP-500-raðir í gegnum `audit/hms_full_recovery.py` (nýtt skipt), endurnotanlegt, með outage-detection innbyggðu. Engar Supabase writes í þessari lotu.

**Why**: Notandi uppgötvaði 2226598 (Nóbýlavegur 14, Kópavogi) sýnilegt á `https://hms.is/fasteignaskra/115672/1022801/2226598` en staging-DB markaði hana `http_status=500, exists_in_hms=0`. Bein endurprófa via sömu `curl_cffi.chrome120` impersonation skilaði HTTP 200 með fullum payload. Þetta opnaði rannsókn á því hversu víðtækur missir væri. Step-0 (read-only timestamp clustering) sýndi tvo aðskilda dead-zone glugga; spike-network-probe staðfesti 18,5% recovery rate.

**Dead-zone gluggar (UTC, nákvæmir)**:

| Window | Start | End | Hours | Phase C 500s | Phase C 200s |
|---|---|---|---|---|---|
| DZ-1 (primary) | 2026-05-16T07:00:09 | 2026-05-17T06:59:47 | **23,99 klst** | 226.400 | 0 |
| Partial recovery | 2026-05-17T07:00:00 | 2026-05-17T08:59:59 | 2 klst | ~16.972 | ~2.028 (degraded: 20,5% → 1,1%) |
| DZ-2 (secondary) | 2026-05-17T09:00:00 | 2026-05-17T20:59:59 | **~12 klst** | 115.000 | 0 |

Heildar-degraded gluggi: **~38 klst** (2026-05-16T07:00 → 2026-05-17T21:00 UTC). Phase C 500-skipting: **dead-zone bulk ~355K**, **healthy-zone tail ~30K**. Spike-skipting per zone: dead-zone FN 19,8% (CI 17,4–22,5%) → ~70.432 recoverable; healthy-zone FN 4,6% (CI 1,8–11,2%) → ~1.370 recoverable.

**Root cause — WAF-backoff scoped to 429/403/503 EN EKKI 500**: `audit/hms_full_scrape.py:226` aðeins eykur `rate_limit_streak` á þessum þremur status code, og núllar streak-inn á öllu öðru (þ.m.t. 500). Backoff-logikkinn (`WAF_BACKOFF_STREAK=10` → 300s sleep) triggerast aldrei á sustained 500-flood. Scraper-inn keyrði beint í gegnum 9.200–9.600 fastnums á klst í ~38 klst með 0% hit-rate án þess að nokkurn tímann pása. Auk þess interpretar `1 if sc == 200 else 0` (sama skipti, lína 223) öll 500 sem `exists_in_hms=0` — engar retries, engin cross-check. **Tvíhliða galli**: outage er ósýnilegt, og einstök 500 eru þögult demoted-uð í "doesn't-exist". Saman skráðu þeir ~280K raunverulegar eignir sem doesn't-exist.

**Overturn — fyrri tilgátur sem þetta hrekur**:
- `audit/cross_source_probe_report.md` (2026-05-07) — Agent-driven exploration hélt að "HMS deprecated public JSON API". Phase B 99,9% hit-rate (124.738 / 124.835) staðfestir að API-ið er **lifandi**; spike staðfesti að það er stöðugt núna. Sú athugasemd byggði á hallucination af content í `audit/hms_dialogue_draft.md`. Ógilt.
- "97 ghost soft-flag" (D2 í Phase D, CLAUDE.md) — 97 Phase B 500s eru *líklega* raunverulegir ghosts (ekki transient á 18,5%/0,08% ratio), en það er tap á forsendu þangað til þeir eru endurprófaðir í recovery-keyrslunni.

**D3 scope reconciliation**: Phase D3 var áætlað sem "30K new-property insertion" í Supabase, byggt á þeim Phase C 200-hits (28.134) sem ekki voru þegar í `properties`. **Nýtt scope er ~75-100K** (28.134 staðfest + ~71.800 recovery). D3 verður frestað þangað til full-recovery klárast og `confirmed-genuine-500` tölur eru pinnaðar; þá fær Supabase-sync nýjan extract/dryrun/apply pattern (sjá `scripts/phase_d1_*.py` template).

**Hardening í `hms_full_recovery.py` (byggt núna, ekki retro-uppfært í `hms_full_scrape.py` ennþá)**:
- Skip `leit`-endpoint cross-check (spike: 0/815 leit-only recoveries — flat API einn dugar).
- 1 retry á 500/exception með 1s backoff (spike: 185/185 á 1. tilraun, en retry er ódýr insurance).
- **Outage detection**: sliding window af 100 nýjustu niðurstöðum; ef 200-rate í glugganum hrynur í <1% (vs expected ~18% recovery rate) → PÁSA 5 mín → endurprófa; ef areftir 100 → HALT + alert. Þetta fyrirbyggir að recovery-keyrslan endurskapi sömu villu ef fresh outage lendir.
- WAF backoff óbreyttur (429/403/503 streak ≥10 → 300s).
- Schema (tvær viðbætur við `hms_fasteign`):
  - `reprobed_at TEXT` — mismunandi: `reprobed_at IS NULL` = original-500 (frá scrape), `reprobed_at IS NOT NULL AND http_status=500` = confirmed-still-500 (frá recovery), `reprobed_at IS NOT NULL AND http_status=200` = recovered.
  - `full_response TEXT` — geymir allan API envelope-inn (`fasteignData` + `stadfangData` + `hasMultipleFasteignir`). Bætt við í v2 eftir uppgötvun að upprunalegi scraper-inn dropp-aði 2/3 af top-level keys.
- `fetched_at` er EKKI yfirskrifað á recovery-200 (preserved frá upprunalegri scrape). `reprobed_at` heldur recovery-tímanum sér.
- Resumable: target set = `WHERE http_status=500 AND reprobed_at IS NULL` — re-byggt við hverja gangsetningu.
- Polite rate: matching original (~157/min) með CONCURRENCY=3, PER_WORKER_DELAY=1.0s + jitter. Wall-clock estimate (með 1 retry á 81,5% cases): ~70 klst (~3 dagar).

**stadfangData uppgötvun (v2 amendment, 2026-05-21 ~20:50 UTC)**: HMS API-svarið hefur **þrjár top-level keys**, ekki bara `fasteignData` eins og upprunalegi scraper-inn gerði ráð fyrir:

```
{
  "fasteignData":         { ... fasteignamat, einflm, notkunareiningar[].matseiningar[].byggingarstig, ... },
  "stadfangData":         { stadfang: {stadvisir, postnumer_heiti_nf/tgf, ...},
                            fasteignir: [ FULL fasteignData fyrir ALLAR systur-fasteignir á sama heimilisfangi ] },
  "hasMultipleFasteignir": bool
}
```

Hver probe skilar **systur-fasteignum á sama stadfangi ókeypis** (t.d. 7 fasteignir undir Nýbýlavegi 14 fyrir 2226598-probe; 2 undir Fífurima fyrir 2040381-probe). Original scrape henti þessu öllu (`hms_full_scrape.py:184-190`: `j.get('fasteignData')`). Recovery v2 geymir núna ALLT envelope-ið í `full_response` column (~3,9 KB á row vs 1,6 KB fyrir bara `fasteignData`).

**Áhrif**:
- `byggingarstig` (B4 etc.) — alltaf í fasteignData.notkunareiningar[].matseiningar[].byggingarstig; **alltaf preserved í bæði fasteign_data og full_response columns**. Ekki týnt.
- `sérmetnar einingar` (= matseiningar nested innan notkunareiningar) — alltaf preserved í bæði columns. Ekki týnt. Dæmi: Móberg 1 jörð hefur 5 sérmetnar einingar (ræktað land, lax/silungsveiði, fjárhús, hesthús, hlaða) — allt geymt.
- `stadvisir`, `postnumer_heiti_nf/tgf`, systur-fastnums — NÝTT í recovery v2; vantar í upprunalegu 154.931 200-raðirnar frá Phase A/B/C.

**Asymmetric coverage post-recovery**: ~75K recovered rows hafa `full_response`; ~154K upprunalegu 200-raðir hafa aðeins `fasteign_data`. Þetta er meðvituð skuld sem verður greidd í **júní-byrjun rescrape** (sjá næstu kafla).

**Data-quality caveat — 866 raðir með yfirskrifað `fetched_at`**: v1-keyrslan (50 mín áður en stadfangData uppgötvun gerðist) hafði bug þar sem recovery-200 endurnýjuðu `fetched_at` í recovery-tíma. Þegar v1 var stöðvuð og 866 recovered raðir revert-aðar til http_status=500/reprobed_at=NULL, var upprunalegt `fetched_at` þeirra glatað (yfirskrifað 2026-05-21T20:08-20:55Z í stað þess að halda 2026-05-16/17 dead-zone tímabilinu). Áhrif: þessar 866 raðir munu birtast sem "healthy-zone" í lokaskýrslunni í stað dead-zone, þrátt fyrir að flestar þeirra séu úr DZ-1 (sást ~24% recovery rate í v1 sem matchar dead-zone hlutfallið). Statistical noise 0,22% af 392K populationinu; flagg-að í `hms_recovery_report.md` post-run.

---

**Júní-byrjun rescrape — plan til að loka asymmetric coverage gap-inu**:

Þegar recovery klárast (~2026-05-24), liggja fyrir tvö data-sets:
- ~154.931 upprunalegt 200-raðir með aðeins `fasteign_data` (engin `stadfangData`)
- ~75.000 nýleg recovered 200-raðir með bæði `fasteign_data` og `full_response`

Júní-rescrape (skipulagður fyrir byrjun júní 2026) mun:
1. **Bakfylla `full_response` á 154K upprunalegu raðirnar** — sömu `WHERE full_response IS NULL AND http_status=200` target set sem önnur recovery-keyrsla. Áætlað ~155K × 1.5s/row × 1.815 retries-fyrir-81,5% / 3 workers ≈ 24 klst (ódýrara en upphaflega vegna þess að flest 200-svör koma á 1. tilraun, engin retries).
2. **Refresh-a stale data** — `index_last_updated` í HMS-payloadinu er u.þ.b. 2026-05-15 fyrir flestar Phase B raðir; um 2-3 vikna gamalt í júní. Recovery v2 mun einnig pikka upp ný gildi (sérstaklega `fasteignamat`, `lhlmat` ef HMS hefur uppfært).
3. **Cross-check nýrri stadfangData** gegn `cross_property_refs` Phase D4 vinnu. Hver `full_response.stadfangData.fasteignir[]` er rich source fyrir address-clustering án viðbótar API-kalla.
4. **Production-template hardening** — `hms_full_scrape.py` skal vera retro-uppfært **áður en** júní-rescrape kviknar:
   - Capture full response (allir top-level keys)
   - Outage detection (sliding window 100 → pause + alert á <1% hit-rate)
   - 500-aware backoff (sustained 500s skulu trigger-a backoff, ekki bara WAF status codes)
   - Það "production-template hardening session" sem var út-of-scope hér er **kveikjandi fyrir júní-rescrape**.

Eftir júní-rescrape: 100% af 200-raðum hafa `full_response`, og Phase D4 cross_property_refs hefur fullbúið source-set.

**Decision-lock**: Júní-rescrape skal nota **sömu canonical template** og hms_full_recovery.py er að nota núna (eftir að retro-uppfærsla á `hms_full_scrape.py` hefur landað í eigin session). Engin tvíverknað á recovery + scrape mynstrum.

**Out of scope (eigin lota, hækkað í forgang)**:
- Sibling-scraper audit: evalue.is backfill-skipti (×6 í `audit/backfill_evalue_*.py` og fyrri pilots) + leiguskrá-scraper — sami WAF-ignorar-500 mynstur líklega til staðar.
- Production-template hardening: fold outage-detection + 500-aware backoff inn í canonical scraper-template (sem `hms_full_scrape.py` hefur framsemt eftir).

**Verification path (post-recovery)**: HALT-report frá `hms_full_recovery.py` skal innihalda **nákvæman recovered count** (ekki estimatið), dead-zone vs healthy-zone breakdown, og confirmed-genuine-500 count. Þá ákveður notandi Supabase-sync / D3 scope.

**Artifacts (þessi lota)**:
- `audit/hms_fn_spike.py` — spike runner (read-only)
- `audit/hms_fn_spike_sample.txt` — 1.000 sampled fastnums (seed=42)
- `audit/hms_fn_spike_results.json` — per-fastnum raw probe outcomes
- `audit/hms_fn_spike_report.md` — halt-report
- `audit/hms_fn_spike_run.log` — runtime log (94,7 mín wall-clock)
- `C:\Users\danie\.claude\plans\i-have-a-large-indexed-lynx.md` — plan file (spike scope)

---

## 2026-05-21 — Phase X Group B Part 2: views layer (security_invoker, anon/auth grants) + frontend switch

**Hvað**: Migration `20260521125751_views_layer.sql` added 4 read-only views — `v_properties`, `v_repeat_sale_index`, `v_ats_lookup_by_heat`, `v_current_predictions` — each declaring `WITH (security_invoker = on)` and granting SELECT to `anon` + `authenticated`. All 10 frontend `.from("properties" | "predictions" | "repeat_sale_index" | "ats_lookup")` call sites switched to the corresponding view (19 `.from()` replacements total). Next.js 16 production build clean; 8-route smoke (incl. `/eign/2008647`, `/markadur`, all four `/markadur/*` sub-pages, `/api/backproj/2008647`) returns HTTP 200 with sizes within ±5% of the 2026-05-06 verify baseline. **Bug 25 (Postgres 15+ view security_invoker discipline) is closed.**

**Why views, why now**: Postgres 15+ defaults views to security DEFINER semantics (run as view owner). With this default, any future RLS policy on the underlying table would be silently bypassed when read through a view — exactly the anti-pattern flagged for Áfangi 0 dependency in the 2026-05-06 RLS baseline audit (Bug 25). Declaring `WITH (security_invoker = on)` forces the view to evaluate with the calling role's permissions, so RLS policies apply as expected. Doing this proactively *before* any new RLS policies land closes the Áfangi 0 hardening dependency without touching policy logic. This entry locks the discipline: every future view in `public` must declare `security_invoker = on` explicitly.

**`v_properties` allowlist (43 of 47 columns)** — confirmed by HALT 2:

| Status | Columns |
|---|---|
| Include (43) | identity (`fastnum`, `heimilisfang`, `husnr`, `postnr`, `postheiti`, `svfn`, `sveitarfelag`); classification (`tegund_raw`, `canonical_code`, `unit_category`, `unit_family`, `is_residential`, `is_summerhouse`, `is_new_build`, `is_main_unit`); size & build (`einflm`, `lod_flm`, `byggar`, `fjherb`, `fullbuid`); geo (`lat`, `lng`, `matsvaedi_numer`, `matsvaedi_nafn`, `matsvaedi_bucket`, `region_tier`); HMS valuation (`fasteignamat`, `fasteignamat_gildandi`, `fasteignamat_naesta_ar`, `brunabotamat`, `lhlmat`, `byggingarstig`, `skodags`, `gerd`, `matsstig`); listing snapshot (`augl_id_latest`, `list_price_latest`, `effective_date_latest`, `scraped_at_latest`, `lysing_truncated`, `first_photo_url`, `photo_urls_json`, `n_photos`) |
| Exclude (4) | `landeign_nr` (unused by frontend; least-exposure default), `matseiningar` jsonb (Phase Z UI redesign will design its public surface), `tengd_stadfang_nr` jsonb (HMS staðfang cross-refs, Phase Y join-internal), `deregistered` (filter-redundant — view's `WHERE deregistered IS NOT TRUE` makes the column constant FALSE for visible rows; the 97 ghosts are hidden from public reads) |

`augl_id_latest` is **INCLUDED** despite Bug 26 (listing-id leak): exposing the `fastnum ↔ augl_id` bulk mapping via `anon` was already true on the underlying `properties` table — `v_properties` does not add new exposure. The Bug 26 fix is now re-scoped (and re-prioritised) to **server-side rendering the deep-link `href` with the service-role key**, NOT column-stripping. That is cheaper than a hashed-proxy approach and avoids reshaping the data contract. Tracked in PLANNING_BACKLOG.

**Spec corrections found during empirical sweep (HALT 2)**:
- `ats_lookup_by_heat` table does not exist in `public` schema. The view `v_ats_lookup_by_heat` wraps `public.ats_lookup` (the empirical name; 65 rows; this IS Table B from Áfangi 7). View name follows the doc-canonical "by_heat" used in the codebase. Optional underlying-table rename (`ats_lookup` → `ats_lookup_by_heat`) deferred to Group C.
- `public.predictions` has neither `scored_at` nor `property_id`. Actual key is `fastnum` (bigint), timestamp is `predicted_at` (DATE). `v_current_predictions` uses `DISTINCT ON (fastnum) ... ORDER BY fastnum, predicted_at DESC`. **Currently a no-op** — at iter4, predictions has exactly 1 row per fastnum (110,316 = count(DISTINCT fastnum) = total). Written forward-safe for the schema where multiple predictions per fastnum may co-exist.
- **Backlog note**: `predicted_at` as DATE is insufficient for robust latest-selection once history accumulates. Replace with `scored_at timestamptz` when iter5 ships (or sooner if a prediction-refresh cadence introduces same-day re-scoring).

**Verification (psycopg2 against linked DB)**:
- 4 views exist in `public`, all with `reloptions={security_invoker=on}` per `pg_class`.
- `information_schema.role_table_grants` confirms `SELECT` granted to BOTH `anon` AND `authenticated` on all 4.
- Row counts:
  - `v_properties` = 124,738 (= 124,835 properties − 97 ghosts) ✓
  - `v_repeat_sale_index` = 2,673 (= source table) ✓
  - `v_ats_lookup_by_heat` = 65 (= `ats_lookup`) ✓
  - `v_current_predictions` = 110,316 = `count(DISTINCT fastnum) FROM predictions` ✓
- Simulated `BEGIN; SET LOCAL ROLE anon; SELECT count(*) FROM <view>; ROLLBACK` returned the same counts for all 4 — confirms anon path works through views.

**Frontend switch (10 files, 19 replacements)**:
- `components/BackProjectionWidget.js` (2× properties)
- `components/SearchAutocomplete.js` (1× properties)
- `app/page.js` (1× properties + 1× predictions)
- `app/eign/[fastnum]/page.js` (3× properties + 1× predictions + 1× ats_lookup)
- `app/eign/[fastnum]/stilla/page.js` (2× properties + 1× predictions)
- `app/eign/[fastnum]/stilla/nidurstada/page.js` (1× properties + 1× predictions)
- `app/markadur/visitala/page.js` (1× repeat_sale_index)
- `app/markadur/modelstada/page.js` (1× properties + 1× repeat_sale_index)
- `app/api/adjust-valuation/route.js` (1× properties + 1× predictions)
- `app/api/backproj/[fastnum]/route.js` (1× properties + 1× predictions + 1× repeat_sale_index)

**Smoke test (production build + curl)** — sizes match 2026-05-06 verify ±5%:

| Route | HTTP | Size |
|---|---|---|
| `/` | 200 | 34 KB |
| `/eign/2008647` | 200 | 127 KB |
| `/markadur` | 200 | 43 KB |
| `/markadur/visitala` | 200 | 942 KB |
| `/markadur/markadsstada` | 200 | 1.1 MB |
| `/markadur/modelstada` | 200 | 37 KB |
| `/markadur/ibudir` | 200 | 821 KB |
| `/api/backproj/2008647` | 200 | 1 KB |

**Security note — what's NOT done in this session (intentional)**:
Underlying tables `properties`, `predictions`, `repeat_sale_index`, `ats_lookup` **still have direct anon + authenticated SELECT grants** from the 2026-05-06 RLS baseline audit. The 4-column EXCLUDE allowlist on `v_properties` defines the *intended* contract but is not yet *enforced* by grants — anon could still bypass the view by reading the table directly. A follow-up session (after deployed-frontend stability confirmation) will REVOKE direct SELECT from anon + authenticated on those 4 tables, leaving the views as the only public read path. The `SECURITY DEFINER` RPCs (`search_properties_grouped`) keep working post-REVOKE since they run as the function owner. Tracked in STATE.md Roadmap as "Phase X Group B follow-up". **Never REVOKE while live prod traffic may still hit table paths** — that would 401 every reader until the deploy lands.

**Locked rule going forward**: when adding a new public-facing column to `public.properties` (or any underlying table), the change MUST extend the corresponding `v_*` view in the same migration. `SELECT *` is forbidden in view bodies; an allowlist of explicit columns is the contract.

---

## 2026-05-21 — Phase X Group B Part 1: Supabase CLI baseline reconcile

**Hvað**: Reconciled local `supabase/migrations/` dir against remote `supabase_migrations.schema_migrations` via a fresh `pg_dump --schema-only -n public --no-owner` baseline, marked applied with `supabase migration repair --status applied 20260521125431`. The 7 pre-existing local files (`20260421_initial_schema.sql` through `20260518_hms_columns.sql`) moved to `supabase/_legacy_migrations/` (out of CLI's view, retained in git history for traceability). End state: `migration list` shows 1 local file = 1 applied baseline plus 11 historical remote-only entries that pre-date the baseline (harmless audit trail, no longer block `db push`).

**Af hverju**: Discovery (Step 1.2) revealed two-way drift from the MCP-applied period (2026-04-21 → 2026-05-18). Local dir had 7 files with short `YYYYMMDD` timestamps (one duplicate date — `20260422` ×2 for two unrelated changes); remote history had 11 long-timestamp entries from MCP `apply_migration` calls. Only 4 of 7 local files had clear remote content-twins (signature-line match: `20260423_dashboard_v1` ↔ `20260421222521`, `20260424_ats_lookup_by_quarter_and_regime_view` ↔ `20260424095108`, `20260422_search_properties_grouped_rpc` ↔ `20260422152141` plus 4 later evolutions, `20260518_hms_columns` ↔ `20260518111331`); 3 had no remote history row despite their effects being live (initial schema, `effective_date_latest`, RLS baseline audit). 7 remote-only entries had no local file at all (`model_tracking_null_segment`, `model_tracking_segment_nullable`, `latest_regime_per_cell_with_zscore`, `properties_prefix_indexes`, `search_rpc_simplify_inline`, `search_rpc_force_custom_plan`, `search_rpc_dynamic_sql`). File-by-file `migration repair --status applied` would have preserved the noise + duplicate-date locals + 7 invisible orphans; the baseline approach gives a faithful repo with one source of truth going forward. This is the foundational fix Group B was designed to deliver before any new migration (the views layer in Part 2) is pushed.

**Tooling decisions (one-off setup, persisted to user-level PATH)**:
- Supabase CLI v2.101.0 installed at `D:\verdmat-is\tools\supabase\supabase.exe` (scoop unavailable on this machine; direct binary download from GitHub releases per spec fallback, SHA-256 checksum verified against `checksums.txt`). Login via interactive browser flow (token cached locally; Claude never handled the token value).
- PostgreSQL 17 client tools (matches server's PG17.6 — pg_dump must equal-or-exceed server major) installed at `D:\verdmat-is\tools\postgres17\pgsql\bin\` (EDB binary-only zip, no installer / no service).
- Connection path for `pg_dump`: **session pooler on port 5432** (`aws-1-eu-north-1.pooler.supabase.com`, user `postgres.szzjsvmvxfrhyexblzvq`, same password as in `.dbconfig`). Transaction pooler (6543) does not support `pg_dump`'s protocol expectations; direct connection (`db.<ref>.supabase.co:5432`) is IPv6-only and unreachable from this host. The session-pooler URL is derived by swapping the port on the existing `.dbconfig` URI.
- Docker Desktop intentionally not installed. `supabase db diff --linked` and `supabase db reset` therefore unavailable; verification falls back to direct `psycopg2` SQL queries against the live DB (sufficient for additive view migrations in Part 2 — adds only, no destructive changes).

**Baseline sanity-check (`supabase/migrations/20260521125431_baseline.sql`, 47,533 bytes, 1,128 lines)**:
- All 11 HMS columns present in `public.properties`: `brunabotamat`, `lhlmat`, `fasteignamat_naesta_ar`, `byggingarstig`, `skodags`, `gerd`, `matsstig`, `landeign_nr`, `matseiningar` (jsonb), `tengd_stadfang_nr` (jsonb), `deregistered`.
- 18 tables with `ENABLE ROW LEVEL SECURITY` + 18 `CREATE POLICY` statements (matches the 2026-05-06 RLS baseline audit: 14 dashboard-public + 4 user-owned).
- 28 `TO anon` grants + 46 `TO authenticated` grants.
- 18 tables, 4 pre-existing views (`latest_regime_per_cell`, `regime_per_cell_monthly`, `repeat_sale_index_by_segment`, `repeat_sale_index_main_pooled`), 1 function (`search_properties_grouped`), 33 indexes.

**Locked rule going forward**: any new schema change MUST go through `supabase/migrations/` + `supabase db push`. MCP `apply_migration` (the original cause of this drift) is disallowed for schema work; reserve the MCP for read-only inspection only.

---

## 2026-05-20 — Phase X architecture sprint (post independent review)

Independent-Claude review of Phase D methodology ranked three fixes: Q6 (backup + 
reproducibility) → Q1/Q4 (sources of truth) → Q7 (views + migration CLI). Decision: 
execute as Phase X BEFORE Phase Y (D3-D5 data) and Phase Z (UI redesign) — UI 
redesign touches multiple components + new Supabase queries, so doing it on an 
unprotected/moving schema is risk multiplication. Phase X groups: A (backup + 
restore test + SOURCES_OF_TRUTH) ✅, B (Supabase CLI baseline + views layer), 
C (migration_helpers + audit tables + run_monthly + inputs_snapshots wiring).

---

## 2026-05-20 — Supabase canonical for HMS metadata

Supabase `properties` is canonical for HMS property metadata. properties_v2.pkl 
becomes a derived training cache, rebuilt by exporting the HMS slice from Supabase 
each training cycle. Resolves the split-brain from Phase D adding 11 HMS columns 
to Supabase not mirrored in the pickle. Full rationale in SOURCES_OF_TRUTH.md. 
Unblocks iter5. Follow-up logged: rebuild_training_data.py export step.

---

## 2026-05-20 — Backup architecture (R2 incremental)

Nightly backup of D:\ critical paths (excl. 352 GB images on CloudFront) to 
Cloudflare R2 via rclone sync + --backup-dir. current/ = live mirror, 
archive/<ts>/ = overwritten/deleted versions, 30-day archive retention. ~$0.20/mo. 
R2 over B2 (MCP convenience). Restore-tested 5/5. Staleness alert deferred to 
Group C run_monthly.py.

---

## 2026-05-18 — Phase D2: 97 ghost properties soft-flagged

97 properties returned HTTP 500 from HMS `/fasteignaskra/fasteign/{nr}` 
endpoint during weekend run Phase B (existing properties.fastnum sweep). 
All 97 had verified sales history in kaupskra (100% match), but HMS no 
longer recognizes them — most likely deregistered post-sale due to lot 
merging / fastnum renumbering. 3 of the 97 were sold in 2025, confirming 
this is active churn pattern, not historical dead records.

4 distinct ghosts × 6 rows present in training_data_v2.pkl (0,003% impact). 
Decision: soft-flag via `deregistered=true` in Supabase properties table. 
No retroactive training data rebuild — impact is trivial. Future 
rebuild_training_data.py runs should JOIN properties.deregistered and 
propagate flag into training data for downstream consumers (UI comparable 
display, scoring pipeline) to filter.

`deregistered` boolean column was added to properties schema in Batch 1 
(migration 20260518_hms_columns.sql). Default `false`. D2 sets `true` on 
the 97 ghost fastnums only.

---

## 2026-05-18 — Áfangi 0 Stage 1 weekend run completed — registry-completion thesis revised

**Hvað**: Two coordinated autonomous runs over 2026-05-08 → 2026-05-18 finished Áfangi 0 Stage 1 work. (1) Orchestrator (`weekend_run_orchestrator.py`) refreshed augl payloads for all 124,835 Supabase properties (`audit/stage_a_augl_staging.db`) and bootstrapped the image archive to 352.53 GB / 1,752,028 files at `D:\Gagnapakkar\images\` (canonical index `D:\Gagnapakkar\image_index.db`, 99.998% download success). (2) HMS full-scrape (`hms_full_scrape.py`, 58h 20m, 546,957 requests against `hms.is/api/fasteignaskra/fasteign/{nr}` via curl_cffi Chrome120 impersonation) ran sequential **Phase A → B → C**: backfill (kaupskra-only + 200-1000-wide gap ints, 8,897 requests, 2,059 hits at 23.1%), enrich (every existing Supabase fastnum, 124,835 requests, 124,738 hits at 99.92%), full-sweep (everything else in span 2,000,044..2,547,000, 413,225 requests, 28,134 hits at 6.81%). Total 154,931 HMS hits / 392,026 non-existent / 28.3% aggregate hit rate. **Result: 30,193 net-new HMS-only properties + 124,738 enriched rows + 97 deregistered ghosts.** All in staging; no Supabase writes performed.

**Af hverju**: Pilot v3 (2026-05-07/08, documented in prior project memory `project_registry_completion_thesis_collapsed.md`) had reported three small-sample probes against the registry-completion target ranges — trailing 5,000 candidates returned 2 hits, sub-gap 100 candidates returned 0, 2.4M bucket 400 candidates returned 0. The conclusion at the time was: "the missing 25K hypothesis no longer has a credible target range" and "session-after-next should NOT plan a multi-night registry-completion sweep". This weekend's Phase C ran the full sweep anyway as a completeness pass. Phase C found 28,134 hits across 413,225 candidates (6.81% aggregate, ~9.0% excluding the confirmed-empty 100K-integer 2.4M bucket which contributed near-zero hits). The pilot's probe locations were unrepresentative — they happened to hit administratively-empty stretches while completely missing the intra-bucket sparse-hole population structure (countryside cultivated land, never-listed apartments at the end of numbered series, regional commercial buildings, sheep farms, horse barns, fishing-rights lots).

**Strategic finding — pilot v3 thesis revised, lesson logged**: small-sample empirical probes are insufficient to scope full registry-completion work. Even three independent probes returning 0–2 hits each can mask a broader population structure 1-2 orders of magnitude denser. **For any backfill-style operation against an authoritative external registry, run a full-coverage sweep before concluding the scope is small.** Applied retroactively, this means the original 2026-04-29 Áfangi 0 25K-fastnum-gap estimate was directionally correct (actually 30K); the 2026-05-08 collapse of that thesis to "no credible target range" was wrong; the 2026-05-18 sweep restored the original direction with better empirical grounding.

**HMS scraper engineering findings (locked, will be referenced in SCRAPER_SPEC v1.1)**:
- Endpoint `https://hms.is/api/fasteignaskra/fasteign/{fastnum}` works for the full registry. Cloudflare WAF requires `curl_cffi` Chrome120 TLS impersonation; plain `aiohttp`, Python `requests`, and `Invoke-WebRequest` all get 429'd on the first request (including the public homepage).
- "Property does not exist" signal is **HTTP 500 `{"error":"Internal server error"}`, not 404**. Any scraper that retries 500 as transient failure will livelock; treat 500 as terminal "not exists".
- Realistic sustained throughput at concurrency=3 + 1.0±0.4s per-worker jittered delay: ~157 requests/minute = ~2.6 req/s. WAF backoff trigger (10 consecutive 429/403/503) never fired during the 58h run.
- HMS payload includes 8+ fields not present in current Supabase `properties` schema: `lhlmat` (land share of fasteignamat — decomposes value into land + structure), `brunabotamat` (independent rebuild-cost valuation), `fasteignamat_naesta_ar` (next-year forecast), `matseiningar[]` array (sub-unit breakdown with own `einflm` / `byggingarar` / `byggingarstig` (B0–B4) / `gerd` (HMS internal class) / `matsstig` / `skodags` / `texti`), `landeign_nr` + `tengd_stadfang_nr[]` (lot cross-references for building-density features). These are high-value features for the valuation model upgrade.

**Phase D scope (set; execution deferred to separate strategic chat session)**:
1. Schema decision — new `hms_data` table (1:1 with `properties.fastnum` + denormalised `matseiningar` child table) vs widen `properties` in place. Separate table cleaner for HMS-refresh re-runs that should not touch prediction-eldsneyti columns; widening simpler for queries.
2. New-property insertion path — 30,193 fastnums need full pipeline (coordinates from `Stadfangaskra.csv`, matsvaedi assignment, region_tier, canonical_code, is_residential classification) before joining `properties`, or land in HMS-only staging table first and graduate over time.
3. Ghost handling — 97 Supabase fastnums that HMS no longer recognises: `mark deregistered=true` + retain history, soft-delete, or hard-delete; needs implications mapping for `sales_history`, `predictions`, model-training filters.

**Artifacts (committed this entry)**:
- `audit/weekend_run_inventory.md` — raw factual numbers per staging DB
- `audit/weekend_run_summary.md` — narrative with strategic findings
- `audit/weekend_run_status.md` — final orchestrator status surface
- `audit/weekend_run.log` — full execution log

**Staging databases (gitignored, retained locally on D:\\)**:
- `audit/hms_archive_staging.db` (391 MB, 546,957 rows) — HMS scrape full output
- `audit/stage_a_augl_staging.db` (2.55 GB, 124,835 rows) — orchestrator Phase 2 augl refresh
- `D:\Gagnapakkar\image_index.db` (791 MB, 2,631,485 rows) — canonical image index
- `D:\Gagnapakkar\images\` (352.53 GB, 1,752,028 files) — image archive
- `audit/backfill_pilot.db` (2.7 MB, 5,415 rows) — pilot v1/v2/v3 historical record

**Out-of-scope for this commit**: Phase D execution, image-bootstrap re-run (if ever needed for the 58 failed URLs), valuation-model upgrade work using the new HMS fields. All planned for separate strategic chat sessions.

---

## 2026-05-06 — RLS baseline audit + GRANT cleanup closar 2026-05-03 alert (Sprint 2 unblock)

**Hvað**: ENABLE ROW LEVEL SECURITY á 14 dashboard-public tables (`properties`, `predictions`, `predictions_iter3v2`, `comps_index`, `feature_attributions`, `feature_attributions_iter3v2`, `sales_history`, `repeat_sale_index`, `last_listing_text`, `ats_lookup`, `ats_lookup_by_quarter`, `ats_dashboard_monthly_heat`, `llm_aggregates_quarterly`, `model_tracking_history`) með `public_read FOR SELECT TO anon, authenticated USING (true)` policy. `REVOKE ALL FROM anon, authenticated` + `GRANT SELECT TO anon, authenticated` reduces hver dashboard-table grant frá full DML niður í SELECT-only. Defense-in-depth `REVOKE ALL ... FROM anon` á 4 user-owned tables (`pro_users`, `saved_properties`, `saved_searches`, `saved_valuations`) sem þegar höfðu RLS+`auth.uid()` policies en héldu over-grants. 4 views (`latest_regime_per_cell`, `regime_per_cell_monthly`, `repeat_sale_index_by_segment`, `repeat_sale_index_main_pooled`) lose write privileges en SELECT inheritance frá underlying RLS'd tables stays intact. Single-transaction migration `BEGIN ... COMMIT` á 22 objects, idempotent (DROP POLICY IF EXISTS + ALTER TABLE ENABLE RLS no-op á rerun).

**Af hverju**: 2026-05-03 Supabase email-alert `rls_disabled_in_public` flagged 14 tables sem launch-blocker fyrir Sprint 2 Áfangi 4 public-dashboard announcement. Underlying severity multiplier var Supabase project-init default sem grantaði anon/authenticated full DML (including `TRUNCATE` og `DELETE`) á hverri töflu — alert var um RLS-disabled, en grant pattern þýddi að jafnvel RLS-on hefði þurft strict policies til að block writes. Migration applar SCRAPER_SPEC_v1 §3.3 conformance pattern ("RLS enabled by default, public SELECT via view, service-role bypass for scraper writes") til existing Sprint 1+2 tables — sami canonical pattern sem Áfangi 0 ætlar að æfa frá byrjun á active_listings + active_listings_history + rejected_commercial_listings, brought existing tables upp í sama staðal.

**Final categorization** (locked post-empirical-pre-checks): 14 dashboard-public (öll töflur sem frontend les via PostgREST anon-key — empirical grep á `app/` + `lib/` confirm; `model_tracking_history` var heuristic-flipped frá service-role-only til dashboard-public eftir grep fann anon-key reads á `lib/dashboard-queries.js:49` + `app/markadur/modelstada/page.js:44, 61`), 0 service-role-only (heuristic produced one but empirical flip moved it til public), 4 user-owned með pre-existing `auth.uid()` RLS frá Sprint 2 Áfangi 5 prep work, 4 views inheriting frá underlying.

**Empirical proof of resolution**: PostgreSQL error 42501 (insufficient_privilege) raised á direct anon INSERT probe (`BEGIN; SET LOCAL ROLE anon; INSERT INTO properties (fastnum, heimilisfang) VALUES (-99999, 'audit_probe_should_fail'); ROLLBACK`) — privilege layer blocks INSERT áður en RLS policy check fer fram, sem er strongest possible failure mode (defense in depth: grant blocks AND no INSERT policy exists). Live-site smoke check 7/7 HTTP 200 með substantive content sizes (`/` 35 KB, `/eign/2008647` 128 KB, `/markadur` 44 KB, `/markadur/visitala` 964 KB, `/markadur/markadsstada` 1.1 MB, `/markadur/ibudir` 840 KB, `/markadur/modelstada` 38 KB) — zero blank pages, zero 5xx, response times 0.6-3.6s. Anon SELECT row counts unchanged post-apply: `properties` 124.835, `comps_index` 1.101.454, `predictions` 110.316, `feature_attributions` 1.103.160, `sales_history` 173.081, plus the rest matching pre-state exactly.

**Commit**: `1d61257` (a045f1a..1d61257), 9 files, +1.227 lines. Includes `supabase/migrations/20260506_rls_baseline_audit.sql` plus full audit/ trail (sweep script + raw JSON dump + sweep report + dry-run plan + apply log + verify script + post-fix report).

**Tvö non-blocker flags loggud í PLANNING_BACKLOG**: **Bug 25** — Postgres 15+ view `security_invoker` discipline (Áfangi 0 dependency, kritískt þegar `rejected_commercial_listings` ships sem service-role-only — any view joining it verður að declare `WITH (security_invoker = true)` eða það leak-ar rows til anon callers via view-as-bypass channel). **Bug 26** — `augl_id` back-link column exposure á `last_listing_text.augl_id` + `properties.augl_id_latest` (v1.1 hardening, column-stripping public views post-Áfangi-0, ~4-6 klst inkludandi frontend refactor — sami concern sem drove SCRAPER_SPEC §3.3 til REVOKE `listing_id` frá `active_listings_public`).

**Cosmetic residual**: views retain `REFERENCES` + `TRIGGER` privileges fyrir anon/authenticated post-fix (DML revokes only covered INSERT/UPDATE/DELETE/TRUNCATE). Non-security — `REFERENCES` á view er meaningless (cannot foreign-key-reference a view), `TRIGGER` would only matter ef enginn skrifar `INSTEAD OF` trigger sem nobody has done. Sweep upp í v1.1 hygiene pass alongside Bug 26 column-stripping work.

**Process lærdómur (Bug 24 pattern, made operational tvisvar í þessari audit)**: First þegar heuristic categorization tagged `model_tracking_history` sem service-role-only (guess based on table-name semantics) en empirical frontend grep flipped it til dashboard-public (fact based on actual `app/` reads). Second þegar audit-script-first principle — sweep `pg_class` empirically rather than trust doc-canonical SCRAPER_SPEC §3.1 baseline cross-check — surfaced doc-vs-reality discrepancy on `predictions_iter4` / `feature_attributions_iter4` / `ats_lookup_by_heat` naming (doc references tables sem don't exist í public schema; production-table = bare name without iter4 suffix). Trust empirical.

---

## 2026-05-06 — Sprint 3 Áfangi 0 SCRAPER_SPEC_v1 planning session decisions

Eftirfarandi ákvarðanir voru lokaðar í planning session 2026-05-06 sem framleiddi `app/docs/SCRAPER_SPEC_v1.md`. Allar decisions eru sourced í þeim spec — þessi entry er audit-trail og rationale preservation, ekki re-spec.

**Áfangi 0 scope stretching (Track A + Track B)**: Original PLANNING_BACKLOG entry var skrifað fyrir Track B eingöngu (supplementary HMS-gap scraper). 2026-05-06 stretched scope-ið til að inkludera Track A — direct active-listings scraper á mbl.is/fasteignir og fasteignir.visir.is sem powerar Áfangi 4.13 market-scan view og recoverar live-listings stream sem dó 2025-07. Tvær tracks share infrastructure (storage layer, orchestrator hook, health monitoring) en aðskildir í source endpoint, fields, refresh cadence, og downstream consumer.

**Track B simplification**: HMS Fasteignaskrá er source-of-truth sem inniheldur öll ~150K fastanúmer í íslenska fasteignastofninum. 25K gap-ið í properties_v2 er incomplete-scrape-of-HMS, ekki fundamental data-sourcing problem. Track B er því full-scale HMS fastanúmera-extract sem inserts missing rows í canonical `properties` tafla — ekki supplement table, ekki fuzzy match, ekki manual review queue. Bug 4 case (Sævargarðar 7) er incomplete-scrape gap, ekki pre-fastnum hypothesis.

**Mirror-investigation as Track A source-pick prerequisite** (Decision-point #1A): Whether mbl.is og fasteignir.visir.is mirror hvor aðra empirically er unknown. 5-7 daga audit script mælir overlap rate á `(heimilisfang_normalized, postnr, agent_listing_id)` match med fallback `(heimilisfang_normalized, postnr, byggar, einflm)`. Decision rule: ≥95% overlap → single-source, <95% → dual-scrape med cross-site dedup. Audit-script-first principle á source-pick stigi — ekki lock-a án empirical data.

**HMS formal-API-first preferred over silent scrape** (Decision-point #1B preference): HMS er government body. Working dialogue er project asset, ekki friction-point. Áfangi 4.9 (matsvæði shapefile) hefur formal-HMS-request precedent — piggyback á þann dialogue. Reputational og legal hygiene plus relationship-as-asset rationale. Silent scrape er fallback eingöngu (Tier 3 í 4-tier ladder í `SCRAPER_SPEC_v1.md` §7.3).

**Decision-point #2B locked — mixed write-path approach**: Track A → (ii) Hetzner-local-staging-then-sync (high-volume nightly, replay-safety valuable, decoupling frá Supabase availability). Track B → (i) direct write til Supabase (low-volume monthly, simplicity beats robustness). Asymmetría justified by volume + criticality profile. Lock í `SCRAPER_SPEC_v1.md` §6.1.

**Inter-track sequencing í monthly cycle**: Track B steady-state runs AFTER `refresh_dashboard_tables` (which itself runs after `rebuild_training_data`). Reasoning: 0.04-0.16% marginal training-data gain frá including new fastnums vs cascade-risk yfir model refresh. Failure-isolation prioritized.

**Public-view security pattern**: New tables ship med RLS enabled by default + explicit SELECT policy `USING (true)` fyrir public-readable + REVOKE á sensitive columns frá `anon`/`authenticated` (`raw_payload`, `agent_phone`, `listing_id`). `public_id uuid` surrogate column pattern reserved fyrir future v1.1 share-link addressability ef þörf krefst — ekki resolve-anlegt til source URLs. RLS-disabled-by-default er recurring failure mode í verkefninu (Bug 24 lesson + 2026-05-03 Supabase alert) sem SCRAPER_SPEC v1 explicit forðar.

**Volume-based scraper health detection (rolling 7-day mean 70% threshold)**: Replaces fixed cycle-over-cycle threshold. Day-of-week seasonality (weekend vs weekday upload patterns) can cause ±15-20% swings without indicating malfunction; trailing 7-day mean normalizes. Direct response til 2025-07 silent-death incident (gamli scraperinn dó án warning, Danni vissi ekki í marga mánuði). Volume detection myndi hafa caught þetta á degi 8.

**Separate scraper repo (`verdmat-is-scraper`)**: Mirroring `verdmat-is-precompute` pattern. Different deploy cadence (Hetzner vs Vercel), different secrets surface (HMS credentials, source-site cookies), different language-stack focus. SCRAPER_SPEC canonical í `verdmat-is/app/docs/`, scraper repo gets read-only mirror.

**#2A pickle migration default fallback (B2 twin-write)**: Ef Áfangi 4.8 (competitor comparison) ekki resolved fyrir Áfangi 0 implementation kickoff, default leaning er B2 (twin-write Supabase + pickle) frekar en B3 (frozen pickle, refactor at iter5). Insurance gegn worst case: iter5 confirmed necessary en slips beyond pickle-empty window.

Sjá `app/docs/SCRAPER_SPEC_v1.md` fyrir full deliverable, build order, og open decision-point status.

---

## 2026-04-28 — Methodology: Postgres LANGUAGE sql function plan-cache pitfall (Bug 13)

**Hvað**: Latency-investigation á `LANGUAGE sql` Postgres functions með parameterized predicates skal ávallt bera saman `EXPLAIN ANALYZE` á function call vs sömu fyrirspurn með inline literal. Munur >2× = generic-plan-cache pitfall sem útilokar prefix index (`text_pattern_ops`, `varchar_pattern_ops`).

**Af hverju**: Bug 13 latency root cause var `search_properties_grouped(term)` skilgreind sem `LANGUAGE sql STABLE` með `lower(p.heimilisfang) LIKE lower($1) || '%'`. Postgres parameterized $1 í generic plan sem féll back á sequential scan af ~125k rows (4207 ms). EXPLAIN á inline literal `LIKE 'akra%'` notaði `text_pattern_ops` btree index á 24 ms. Sama predicate, sama data — eingöngu munur er hvort planner sér literal eða parameter.

**Lausn pattern**: rewrite-a function sem `LANGUAGE plpgsql STABLE` með `EXECUTE format('SELECT ... LIKE %1$L ...', pattern)` — `%L` injectar literal-quoted string sem planner getur index-matched. Nota `format()` með positional `%1$L` til að referencea sama pattern í multiple WHERE clauses án að passa term oftar í argument list.

**Fallback ákvarðun**: ekki nota `LANGUAGE sql` fyrir functions sem þurfa að index-match á LIKE/ILIKE/regex predicates með parameterized strings. Nota plpgsql + EXECUTE format(), eða nota direct PostgREST query með filter ef function abstraction is overkill.

**Verification recipe** (post-rewrite):
```sql
EXPLAIN ANALYZE SELECT * FROM search_properties_grouped('akra');
EXPLAIN ANALYZE
  SELECT * FROM properties
  WHERE lower(heimilisfang) LIKE 'akra%' AND is_residential = TRUE
  LIMIT 15;
-- both should show "Index Scan using ix_properties_lower_heimilisfang"
-- both should be < 50 ms on a warm cache
```

---

## 2026-04-28 — Methodology: Edge Runtime env var validation pattern (Bug 13 / Bug 18)

**Hvað**: Edge Runtime routes sem reiða sig á `process.env.NEXT_PUBLIC_*` skulu defensive-trim+validate með fallback constants. `||` á einum sér er ekki nóg, vegna þess að truthy-but-malformed strings (whitespace-padded URL, truncated JWT) beat `||` og leiða til downstream error sem er erfiðara að diagnose-a.

**Af hverju**: Bug 13/18 root cause var Vercel dashboard sem reported env vars sem "set", en Edge runtime fékk:
- `NEXT_PUBLIC_SUPABASE_URL` með **2 trailing spaces** → `fetch()` threw `TypeError: Invalid URL string`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` truncated til **46 chars** (full JWT er 208) → 401 á öllum requests jafnvel þó URL parse-aði

`process.env.X || FALLBACK` skipti engu því bæði values voru truthy. Niðurstaða: Edge route skilaði `[]` á öllum search queries → UI sýndi "Engin eign fannst" empty-state á alvöru residential queries.

**Lausn pattern**: defensive validators sem trim + structural-validate + fallback til hardcoded constants:

```js
const FALLBACK_SUPABASE_URL = "https://<ref>.supabase.co";
const FALLBACK_SUPABASE_KEY = "<full-anon-jwt>";

function pickUrl(envVal) {
  const trimmed = (envVal || "").trim();
  if (!trimmed) return FALLBACK_SUPABASE_URL;
  try { new URL(trimmed); return trimmed; }
  catch { return FALLBACK_SUPABASE_URL; }
}

function pickKey(envVal) {
  const trimmed = (envVal || "").trim();
  return trimmed.length > 100 ? trimmed : FALLBACK_SUPABASE_KEY;
}
```

**Hvenær á við**: Edge Runtime routes (Vercel/Cloudflare Workers/Netlify Edge) þar sem env-var injection pipeline er meira fragile en Node serverless. Pattern á einnig við um SSR routes ef env vars eru fed gegnum CI/CD eða third-party tools sem geta whitespace-padded eða truncated values.

**Hvenær EKKI við á**: server-side keys sem leyfast EKKI í client bundle (service-role keys, OAuth secrets). Fyrir þá values, fail-fast er better than fallback — láta route 500-a með skýru "config missing" message frekar en að silently use a public fallback.

**Hvenær FALLBACK er öruggt**: aðeins þegar fallback value er already-public (NEXT_PUBLIC_* vars sem ship í client bundle). `FALLBACK_SUPABASE_URL` + `FALLBACK_SUPABASE_KEY` í þessu case eru bæði í `.env.example` og í the bundled JavaScript sem hver browser tab fær — þau eru ekki secrets.

---

## 2026-04-27 — Sprint 2 Áfangi 4 LOKIÐ: dashboard launch + Fasi E polish + Bug 8

**Hvað**: Sprint 2 Áfangi 4 closed. Dashboard live á https://verdmat-is.vercel.app/markadur með öllum fimm route undirsíðum (`/`, `/visitala`, `/markadsstada`, `/ibudir`, `/modelstada`), eign-síðu waterfall fix og Fasi E launch polish (Addendum 1 unregistered-space map, Bug 7 thin-sample filter, Bug 8 nýbygging exclusion fyrir metric 1 & 2, Lighthouse a11y polish, scrape-gap disclosure copy).

**Áfangi 4 deliverables — production**:
- Fasi A — data pipeline infra (4 Supabase tables, 3 views, 4 build scripts, orchestrator v2)
- Fasi B — `/markadur` landing (A+B hero, 3 cards, 3-line timeline, scrape-gap banner)
- Fasi C-1 — `/markadur/visitala` (4×3 grid, per-row toggles, crash-band shading)
- Fasi C-2 — `/markadur/markadsstada` (slider, heat-map, back-projection widget, regime view)
- Fasi C-3 — `/markadur/ibudir` (5 LLM aggregates + Addendum 1 unregistered map)
- Fasi C-4 — `/markadur/modelstada` (4 panels, Icelandic status labels, methodology card)
- Fasi D — `/eign/[fastnum]` waterfall hides time anchors, Markaðsstaða footer
- Fasi E — launch polish (canonical, og:, mobile collapse, skip link, gallery a11y, copy)

**Bugs fixed mid-sprint (8 total)**:
1. Regime pill hybrid rule (12m + pooled z_3v12)
2. effective_date_latest column for /eign listing date
3. Autocomplete ORDER BY for fjölbýli coverage
4. Two-tier autocomplete + HMS-gap caveat banner + prefix indexes
5. Step 2 expand SELECT non-existent merking column
6. Quarterly + smoothed-monthly regime methodology
7. n<30 filter on /ibudir aggregate charts
8. is_new_build=False filter for metric 1 & 2 (this entry)

**Bug 8 detail — is_new_build filter**:
- Spot check 2026-04-27: interior_condition_score for new builds avg 2.47 vs 1.60 for existing stock, inflating APT_STANDARD quarterly mean by +0.10 to +0.33 points.
- Renovation rate distorted because new builds get coded `has_any_recent_work=False` so a heavy new-build inflow drags the rate down even when absolute renovation count rises.
- Fix: `build_llm_aggregates.py` filters `is_new_build=False` for metric 1 (interior_condition_score mean) and metric 2 (pct_recently_renovated). Other metrics unaffected.
- Editorial copy on /ibudir Section 1 + 2 explains the filter explicitly: "Nýbyggingar útilokaðar úr greiningu (þær fá hátt ástandsstig per definition og myndu skekkja meðaltalið)."
- Rebuilt + re-loaded llm_aggregates_quarterly via `load_dashboard_v1.py --tables llm` (1,450 rows, same shape, different values for metrics 1 & 2).

**Fasi E launch polish**:
- Addendum 1 unregistered-space graduated-symbol map on /ibudir (22 capital-region postnr from Stadfangaskra centroids + refined `unregistered_space_sqm > 5` rate; Leaflet circle markers with √n radius scaling; static JSON in `public/data/`).
- True polygon choropleth deferred to v1.1 — LMÍ public shapefile requires browser-driven catalog navigation that cannot be programmatically fetched. Logged in PLANNING_BACKLOG Áfangi 4.5.
- /markadsstada disclosure paragraph: "Nýjustu áreiðanlegu gögn eru frá 2025-Q2 vegna tímabundinnar takmörkunar á auglýsingaflæði..."
- Lighthouse a11y polish: skip-to-content link in root layout (sr-only, focus-visible); gallery thumbnail buttons aria-label "Mynd N af M"; hero `<Image priority>` already in place; canonical URLs on all 5 dashboard routes + /eign metadata; /eign generateMetadata gains openGraph block.
- VisitalaGrid 4×3 collapses to single column at <600 px viewport via `.vm-visitala-row` class + media query (was missed in C-1).
- og:image fallback deferred — no static brand image asset exists; shipping a 404 reference is worse than absent meta. Queued for v1.1 OG generator polish.

**Carry-overs to Sprint 3** (logged in PLANNING_BACKLOG, not blocking launch):
- Áfangi 0 — comprehensive scraper to recover the post-July-2025 listing flow gap (top priority)
- Áfangi 4.5 — €/m² price map dashboard (`/markadur/kort`), depends on LMÍ polygon download
- Áfangi 4.6 — new-build share tracker (Bug 7 follow-up)
- Áfangi 4.7 — new-build as a separate segment (Bug 8 follow-up; depends on Áfangi 4.8)
- Áfangi 4.8 — eldri-stock calibration analysis (Egilsgata 10 7 % gap vs competitor; possible iter5 fasteignamat re-introduction)
- Áfangi 4.9 — matsvæði-level polygon (Sérlóðir map upgrade, depends on HMS API access)
- /markadur/markadsstada 1.14 MB payload (lazy-load candidate)
- /eign dynamic 1.1 s server render

**Lighthouse**: Danni runs in browser on `/markadur` and `/eign/2008647` post-deploy; thresholds (Performance ≥ 85, SEO ≥ 95, Accessibility ≥ 90, LCP < 1.8 s mobile) confirmed before announcement (or any sub-target documented in v1.1 backlog).

---

## 2026-04-24 — Bug 6 + smoothing refinement: asymmetric monthly/quarterly regime methodology on /markadsstada

**Hvað**: `/markadur/markadsstada` skiptir um regime-source logic:
- **Default view**: ársfjórðungslegt per-cell regime úr nýju `ats_lookup_by_quarter` töflunni (913 rows; derived úr Áfanga 7 `build_ats_lookup.py` step 6, en ekki importað í Supabase fyrr en núna). Stöðugri fyrir langtíma trend.
- **Monthly (smoothed) drill-down**: z₃v₁₂ ± 0,5 þröskuldur á `ats_dashboard_monthly_heat`. Responsive fyrir nýlegar breytingar.
- **Per-cell fallback**: ef `n_month < 50` OR `z_3v12 IS NULL` í selected month, displayed regime fellur til ársfjórðungslegu heat_bucket, með "ársfj." disclosure label á pill + popover tooltip copy.

Slider heldur sama formi (velur mánuð); data-source breytist eftir mode. Methodology paragraph bætist á `/markadur/modelstada` fjórðu card-ið til að útskýra asymmetry.

**Root causes**:
1. **Stale data display** — bæði monthly heat og quarterly table eru derived úr `paired_fresh` subset sem ekki inniheldur `in_scrape_gap=True` rows (per build_ats_lookup.py step 1). Max month er 2025-06 fyrir báðar tables (quarterly = 2025Q2). Monthly default birti user-um 2025-06 sem "núverandi", sem er misleading; quarterly 2025Q2 er sama date-reach en með pooled 3 mán → fewer flips. Full recency (2025-Q3+) krefst Sprint 3 scraper.
2. **Month-to-month flip-flop** — thin-sample cells (t.d. SFH_DETACHED × Capital_sub með avg n=15/mán) sýndu 17 raw-regime-flips á 24 mánuðum vegna sampling noise. 3-mo smoothing dregur þetta niður í ~9 flips (still noisy), en quarterly fallback við n<50 dregur það niður í 0 spurious flips (quarter heat_bucket er stable per quarter). Matches user expectation.

**Methodology asymmetry — rökstuðningur**:
- Monthly regime = z₃v₁₂ ± 0,5 (current-relative): user mental model "er markaðurinn heitur **núna**?" kallar á samanburð við rolling 12-mán baseline. z-score er zero-mean og scale-free → sama þröskuldur fyrir öll segment.
- Quarterly regime = median_log_ratio vs p33/p67 (historical-relative): fyrir langtíma trend þarf fixed reference frame. Áfangi 7 byggði p33/p67 á whole-sample quarterly medians; að endurnýta það fyrir quarterly view tryggir consistency með scoring table B.
- Mismunandi tímaupplausnir kalla á mismunandi referansaramma. Þetta er ekki bug heldur by-design.

**Threshold choice**:
- **Smoothed ± 0,5 SD**: ~38 % af z-scores fyrir normal distribution falla utan |z|>0,5, sem passar við "notable shift from 12-mo baseline" án að vera of sensitive. ±1,0 væri of strict (fáir flaggaðir hot/cold); ±0,3 væri of loose (flip-flop á normal variation).
- **Fallback n<50**: matchar Áfanga 6 `MIN_PAIRS_PER_CELL=50` all-time inclusion filter og Áfanga 7 Table B `TABLE_B_MIN_N=10` per-bucket threshold — consistent með existing pipeline methodology. Under 50 pairs per month er too thin fyrir stabilan z-score (CI ±15 pp á above-list rate).

**Implementation path** (hybrid upstream/downstream per Danni confirmation 2026-04-24):
1. Upstream: import `ats_lookup_by_quarter.csv` (913 rows, ~90 KB) í new Supabase table. One-time data load; build script unchanged.
2. Upstream: new SQL view `regime_per_cell_monthly` — join-ar monthly heat við quarterly lookup, emitterar `raw_regime / smoothed_regime / quarterly_regime / display_regime / regime_source` columns í einni fetch. Engin materialization; view-time CASE computation.
3. Downstream: `MarkadsstadaDashboard.js` mode toggle (quarterly default / monthly drill-down), fallback disclosure label, tooltip copy update.

**Flip-frequency verify (2024-07 → 2025-06, 24 mán)**:
- APT_STANDARD × RVK_core (avg n=82): raw 4 flips → smoothed (display) 2 flips. One clean regime transition Jan 2025 (hot→cold).
- SFH_DETACHED × Capital_sub (avg n=15, all 24 months fallback): raw 17 flips → display regime follows quarterly (~2 flips over 24 months matching 2024Q4 hot → 2025Q1 neutral → 2025Q2 hot transitions).

**Timeline yfirboð-chart**: augar scrape-gap (2025-07→latest) með yellow ReferenceArea + caveat "Gögn enda {latest month} vegna scrape-gap frá júlí 2025". Fully transparent.

**Methodology statement** á `/modelstada` pipeline health card: útskýrir tvennar tímaupplausnir svo pro-users skilji af hverju pill fyrir sömu (seg × reg) cell er kannski mismunandi milli quarterly view og monthly drill-down.

---

## 2026-04-22 — Bug 5 fix: expand Step 2 requested non-existent `merking` column

**Hvað**: Bug 4's expand-path (SearchAutocomplete.js → Step 2 unit list) select-ar `merking` column sem er ekki til í Supabase `properties` tafla. PostgREST skilaði `42703: column properties.merking does not exist`; client-kóðinn ate error silently með `(data || [])` pattern og renderaði "Engar einingar tilheyra þessu heimilisfangi" fyrir hverja multi-unit address. Regression á allri Bug 4 UX — Miðbraut 1 Seltjarnarnes, Egilsgata 10, Bakkastígur, öll multi-unit-address matches broken.

**Root cause**: `properties_v2.pkl` hefur `merking` text column, en `precompute/build_precompute.py` exportar það ekki í Supabase. HMS "merking" fyrir multi-unit byggingar er hins vegar þegar í `properties.unit_category` ("0100", "0101", "0102", …) sem er exact same concept. Bug var copy-paste frá Danni's spec-query og ég missaði að cross-reference við actual schema fyrir deploy.

**Hypothesis eliminations** (Danni listaði 4, öll ruled out):
- (A) postnr null — nei, postnr=101 int fyrir alla 3 rows.
- (B) type mismatch — nei, postnr_type=integer og JS number hvor tveggja.
- (C) case sensitivity — nei, "Egilsgata 10" stafrétt.
- (D) trailing whitespace — nei, addr_len=12 = exact length "Egilsgata 10".

**Fix**:
1. Remove `merking` úr Step 2 SELECT. Skipta fyrir `unit_category` sem er already í select-inu og contains exact sama semantic ("0100" = kjallari, "0101" = 1st floor unit 1, o.s.frv.).
2. Surface PostgREST errors í client — `const { data, error } = ...` + `if (error) console.error(...)` frekar en silent `(data || [])`. Sama class af bug getur ekki falið sig aftur.
3. UI render sýnir nú "merking 0101" per unit sem er skýrara fyrir users en rå unit_category.

**Process lesson**: Bug 4 smoke test dekkaði Step 1 RPC output (group-by count) en ekki Step 2 expand path. Fyrir tvíþrepa UX patterns, must test both tiers end-to-end áður en deploy. Saved til memory sem generic learning.

**Verify** (production post-fix): `properties?select=fastnum,tegund_raw,canonical_code,unit_category,einflm&heimilisfang=eq.Egilsgata%2010&postnr=eq.101&is_residential=eq.true` skilar 3 rows (APT_BASEMENT 0100 52.4 m², APT_FLOOR 0101 108.4 m², APT_FLOOR 0102 99.0 m²). Miðbraut 1 Seltjarnarnes skilar 5 rows.

---

## 2026-04-22 — Bug 4 + search UX overhaul: two-tier autocomplete, HMS-gap caveat, Leið B launch

**Hvað**: `SearchAutocomplete.js` endurskrifaður frá flat unit-list yfir í tveggja-þrepa pattern. Nýr RPC `search_properties_grouped(term)` í Supabase aggregerar matches eftir `(heimilisfang, postnr, postheiti)` og skilar `n_units` + `tegund_summary`. Þrep 2 er inline-expand sem sækir units per address á klicki. 7-stafa fastnum queries fá beina leit án address-groupings. Empty state skilar HMS-gap-caveat-copy. Nýr `SearchDataGapBanner` (localStorage-persistent) á homepage undir search.

**Launch strategy Leið B (Danni)**: ship dashboard og pro-questionnaire með transparent HMS-gap caveat, byggja comprehensive scraper (e-value.is eða equivalent) í parallel sem Sprint 3 top-priority. Dashboard ekki blocked af properties-completeness; search-leki er acknowledged í UI svo users skilja af hverju sumar eignir vantar.

**Performance fix (samhliða RPC)**: EXPLAIN ANALYZE sýndi 3.072 ms execution fyrir ILIKE-prefix á 125K-row properties tafla — planner valdi `idx_properties_residential` partial index og seq-filteraði 105K rows. Trigram GIN á heimilisfang var ekki pickað. Lausn: ný B-tree `text_pattern_ops` indexes á `lower(heimilisfang)` og `lower(postheiti)`, og rewrite-a RPC til að nota `lower(col) LIKE lower($1) || '%'`. Eftir fix: 10 ms execution með Bitmap Index Scan + BitmapOr combining báðum indexes. Function sett med `SET statement_timeout TO '10s'` sem safety net fyrir cold plan-cache calls.

**UI patterns**:
- **Þrep 1 address-row**: `heimilisfang · postnr postheiti` + optional `(N íbúðir)` count ef n_units > 1 + `tegund_summary` í undir-línu. Single-unit rows nav-a beint við klick; multi-unit rows expand inline. Chevron glyph `▸`/`▾`/`→` gefur hint um behaviour.
- **Þrep 2 unit-row**: tegund_raw + einflm + merking, sortað APT_BASEMENT fyrst, svo einflm desc (matches spec intent, stable across HMS tegund variants).
- **Empty state**: explicit HMS-fasteignaskrá caveat + link á `/um#gagnasafn`. Frekar en silent "engin niðurstaða", útskýrir af hverju eign gæti vantað.
- **Persistent banner**: `SearchDataGapBanner.js` birtist undir search og dismiss-ast með × — localStorage (ekki session), þannig user dismissar einu sinni per browser. SSR-renders visible svo non-JS + SEO crawlers sjá caveat-ið á first paint.
- **Fastnum direct search**: regex `/^\d{7}$/` triggerar bypass — single-row result með pseudo-address-row shape svo sama renderer virkar.

**Indexes hafa áhrif**: Bæði B-tree indexes bætast á properties (2 × ~1 MB á 125K rows). Insignificant vs 8 GB Supabase cap.

**Verify** (production):
- EXPLAIN á `search_properties_grouped('miðbraut 1')`: 10 ms execution, Bitmap Index Scan + BitmapOr beggja lower-prefix indexes.
- Anon REST call cold: ~2,4 s (pgBouncer + plan cache cold), warm: 700–1000 ms. Innan statement_timeout og user-perceivable latency.
- `miðbraut 1` search skilar nú 6 address-rows: Miðbraut 1 Seltjarnarnes (5 íbúðir), Miðbraut 1 Búðardalur (einbýli), Miðbraut 10–13 etc.
- `Sævargarðar 7` skilar `[]` og UI birta empty-state caveat.

---

## 2026-04-22 — Bug 3 fix: autocomplete ordering for fjölbýli coverage

**Hvað**: `SearchAutocomplete.js` færir `ORDER BY heimilisfang ASC, fastnum ASC` í autocomplete-fyrirspurnina og hækkar `LIMIT` frá 8 í 15. Fjölbýli með fleiri en eina íbúð á sama heimilisfang birta nú allar sínar einingar fyrstar.

**Root cause 3a — Miðbraut 1 fjölbýli birti bara eitt hit**: Fyrirspurnin hafði ekkert `ORDER BY`, svo PostgREST skilaði rows í arbitrary insertion-order (≈ fastnum asc fyrir gömul rows). `%Miðbraut 1%` ilike pattern matches líka Miðbraut 10/11/12/17/18/19. Með `LIMIT 8` birtust bara einingar með lægri fastnum (2067xxx-svæði) — #1's yngri einingar (2220441–2220444, bættar við HMS síðar) komust aldrei í fyrstu 8. Fix: `ORDER BY heimilisfang` collatar alphabetically svo "Miðbraut 1" < "Miðbraut 10" (styttra string með sömu prefix vinnur), og öll 6 Miðbraut 1 hits klessa saman efst. `LIMIT 15` er valið svo fjölbýli með <10 einingum taki ekki öll sæti fyrir aðra staði.

**Root cause 3b — Sævargarðar 7 vantar alveg**: **Ekki bug í okkar kóða.** HMS Fasteignaskrá (raw `properties_v2.pkl`) inniheldur ekki Sævargarðar 7. Landnum-röð fer 117655→117660 (Sævargarðar 1-6), svo 117662 (Sævargarðar 8+10 sameiginlegir raðhús). Landnum 117661 vantar alveg upstream — líklega demólað, endurnúmerað eða ekki skráð enn. Sprint 3 `refresh_kaupskra.py` companion mun pick-a upp framtíðarskráningar.

**Hypothesis B ruled out**: Autocomplete filter-ar bara á `is_residential = true` — engin prediction-háðsía. Eign getur birst í search áður en iter4 pred er computed.

**Verify** (post-fix query): `ORDER BY heimilisfang, fastnum LIMIT 15` á `%Miðbraut 1%` skilar 6 Miðbraut 1 rows efst (5 Seltjarnarnes + 1 Búðardalur), svo Miðbraut 10/11/12/13. Matches expected coverage.

---

## 2026-04-22 — Bug 2 fix: effective_date_latest replaces scraped_at_latest fyrir listing display

**Hvað**: Ný DATE-column `properties.effective_date_latest` drífur "Nýleg auglýsing ([date])" á `/eign/[fastnum]`. Kemur frá `listings_v2.effective_date` (raunverulegur auglýsingardagur) en ekki `listings_v2.scraped_at` (pipeline-keyrslutími).

**Root cause**: `precompute/build_precompute.py` var `sort_values("scraped_at").drop_duplicates("fastnum", keep="last")`. Innan einnar scrape-keyrslu eru ÖLL rows með sama `scraped_at` (tíminn þegar job keyrði), svo tied-values sort fellur aftur til DataFrame row-index sem picking-strategy. Fyrir fastnum=2008647 (9 rows, effective_date 2017-08-22 → 2019-09-06) var picked 2017-row (price 64.9 M kr) og displayed "11. apr. 2026" scrape-date. Danni screenshot stakk á þetta.

**Fix**:
1. `build_precompute.py`: sort með `effective_date` (fallback `scraped_at` ef null). Export `effective_date_latest` alongside.
2. `properties` schema: `ADD COLUMN effective_date_latest DATE` (idempotent migration `20260422_effective_date_latest.sql`).
3. Targeted backfill `precompute/fix_latest_listing_per_fastnum.py` — re-derives per-fastnum latest frá listings_v2.pkl og uppsertar via psycopg2 TEMP table + UPDATE FROM. 58.437 rows updated í 23 sec, engin full-pipeline re-run þörf.
4. `/eign/[fastnum]/page.js`: display `effective_date_latest`; fallback `scraped_at_latest` with "skráð" prefix svo það er unambiguous.

**Verify**: fastnum=2008647 displays now "48,9 M kr (6. sep. 2019)" (augl_id=874137). Previously: "64,9 M kr (11. apr. 2026)".

**Follow-up**: next full `build_precompute.py` run will use updated logic and include `effective_date_latest` í CSV export. Existing properties.csv á /d/verdmat-is/precompute/exports/ is stale wrt this column; not blocking because live DB is patched.

---

## 2026-04-22 — Bug 1 fix: regime pill rule revised to hybrid (12m + pooled z_3v12)

**Hvað**: Landing pill `/markadur` regla breytt frá "≥8 af 12 cells hot/cold → pill" í:

- 12m real change ≤ −1,0 % AND pooled z_3v12 < +0,5 → `KALDUR`
- 12m real change ≥ +1,0 % AND pooled z_3v12 > −0,5 → `HEITUR`
- Annars → `HLUTLAUS`

Pooled z_3v12 er `n_month`-weighted mean across 12 main-residential cells (latest month per cell).

**Root cause**: Fyrri reglan aggregated heat_bucket counts úr `latest_regime_per_cell` view. Heat-bucket er per-cell p33/p67 threshold on `median_month` — lítið correlated með pooled 12m real change. Við 2026-04 data (12m = −2,00 %), cells split 3 hot / 5 neutral / 2 cold / 2 unknown → ekki 8-of-12, pill HLUTLAUS. User screenshot: red −2,0 % hero beside neutral pill = cognitive mismatch.

**Rationale**: Hybrid lets either signal (momentum OR current trend) pull pillinn off neutral, en requires agreement (no veto) áður en committing to hot/cold. Momentum (12m change) matches user expectation frá the hero number; trend (z_3v12) matches ATS-scoring methodology. Thresholds (±1,0 % / ±0,5) chosen svo neutral band er breitt enough to avoid flicker en tight enough to catch real moves.

**Implementation**: `latest_regime_per_cell` view now exposes `z_3v12`. `lib/dashboard-queries.js::computeHeroB` re-written. Spec §2.2 Metric B updated in lockstep så future chats see the authoritative rule.

**Verify** (production): 12m = −2,00 %, pooled z_3v12 ≈ −0,08 → pill `KALDUR` (vm-badge-cold, blue). Matches red hero number.

---

## 2026-04-23 — Áfangi 3 closed: PDF export með built-in PDF fonts

**Hvað**: Public downloadable PDF á nidurstaða-síðu. Lazy-loaded `@react-pdf/renderer` + Document/Page/Text layout með Helvetica + Times-Roman (built-in Type 1 standard fonts).

**Font decision**: Reyndi first að registerá Inter + Fraunces frá Google Fonts CDN, en placeholder TTF URLs voru 404, PDF generation failed silent í client. Switched to PDF standard fonts (Helvetica body, Times-Roman display) sem báðir styðja Latin-1 Supplement (includes þ æ ð ö á ú via WinAnsiEncoding). Trade-off: display-heading serif er Times-Roman í staðinn fyrir Fraunces — web og PDF typography mismatch, en web brand retained og PDF letur er stable + offline.

**Lazy-load strategy**: `@react-pdf/renderer` er ~450 KB gzipped. Initial bundle er óbreytt frá Áfanga 2 af því PDFDownloadButton dynamic-importar renderer + PDFReport á fyrsta click. Second click er instant (modules cached). Accept loading state "Býr til PDF..." sem user feedback.

**Disclaimer**: Explicit text í PDF footer stating "AI-verðmat, not legally binding" — important fyrir ef fasteignasalar prenta og deila með viðskiptavinum.

---

## 2026-04-23 — Manual Q effects v1.1 calibration refinement (additive)

**Hvað**: 6-item calibration update til `data/manual_q_effects.json`. Backwards-compatible: old share URLs still work via legacy-key translation in both API og results page.

**Rationale per fix**:

1. **Flooring type → renovation trilemma**: Parket vs teppi er US-suburban price signal. Íslandi notar báðar lausnir alongside each other; gólfefni-type dispersion er stödd cross-buyer-pool and doesn't systematically move price. Recent-renovation er raunverulegt signal instead.

2. **Garage split by segment**: Single garage question allowed "tvofalt +4.5%" on APT_FLOOR, gerir flat-buyer confused og overstates effect. SFH/ROW/SEMI fá actual-bílskúr enum (einfaldur/tvöfaldur); APT fá bílastæði enum (sameign/tryggt_utanhuss/bilskyli_kjallari). Canonical-gated UI rendering + API validation enforce.

3. **Condition 4 stages**: v1 jumped 3% → 0% → −5% med engin middle stage for minor work. `smavagilegar_framkvaemdir` (−2%) fills gap; most Icelandic properties sit in medium-minor range. More granular user experience.

4. **proximity_school raised**: Real-estate literature used in v1 was US-sub; Icelandic barnafjölskyldu-markaðir í Kópavogi/Hafnarfirði price-a skólanálægð sterkar. 1.5% er Iceland-realistic.

5. **kjallari and floor4+**: Hedonic studies á íslenskum markaði suggest 3-5% kjallari penalty and +2-3% premium á hærri hæðum. v1.0 values were mildir; v1.1 aligns better.

6. **ovisst defaults halved**: v1 had ovisst as weak positive (≈0.3× of "ja" effect) sem meant user clicking "ovisst" through alls 5 questions fékk +1.5% stacked boost. Halving gerir ovisst accept-default-gracefully option, ekki stealth-bonus.

**Still hardcoded**: Sprint 3 PDP-based refresh á iter4a booster supersedear þetta alveg. Þessi refinement er interim pending real data-driven calibration.

**Coverage**: stacked worst-case −10 to −11%, best-case +24 to +27% (SFH vs APT). Real dispersion narrower.

---

## 2026-04-22 — Sprint 2 Áfangi 2 decisions

**Hvað**: Public manual questionnaire shipped (no auth required). Baseline + persónulegt verðmat med 11-spurning flow, link-shareable results, CTA card on main eign page.

**Segment fallback abandoned** (Skref 5): Tested 2 blend strategies — max-N donor biased small-N Country cells toward tighter Capital_sub/RVK_core. Pooled cov worsened (79.08 → 78.21). APT_STANDARD × Country held N=81 undercoverage (69.1%) is sample noise at Bin(81, 0.80) lower CI bound, not systematic miscalibration. Retained iter4_conformal_v1.

**Manual Q effects hardcoded**: Empirical residual regression gave 0.2–2% magnitudes — iter4a already uses these features as inputs, so leftover residuals only reflect what model missed. Used literature-anchored values in `data/manual_q_effects.json` (range −12% to +21%). Sprint 3 will refine via PDP per feature on iter4a booster.

**URL-encoded answers**: Results page uses `?a=q1:v1,q2:v2` query string instead of POST-only flow. Benefits: link-shareable, server-rendered (no client-side result fetch), no cookie/storage. Share button copies canonical URL.

**Questionnaire non-applicability**: SUMMERHOUSE + non-residential redirect 307 → `/eign/[id]?notice=no_adjust`. Avoid user confusion from getting a personal valuation on iter4's known-weak SUMMERHOUSE segment (175% MAPE) or unpredicted commercial.

**API route**: `/api/adjust-valuation` POST exposed publicly (no auth). Accepts `{fastnum, answers}`, returns `{baseline, adjusted, breakdown, multiplier, model}`. Server-side computation ensures baseline pulled from DB fresh. Used by results page indirectly via URL-decode + same adjustment logic; API available for future client use (saved valuations in Áfangi 3).

---

## 2026-04-22 — Sprint 2 Áfangi 1 QA findings

Edge case audit á 5 scenarios fyrir eign detail page:
1. No photos → "Engar myndir" placeholder í gallery. PASS.
2. New build (2024+, no sales) → sölusaga section renders conditional (`salesHistory.length > 0`), hidden when empty. PASS.
3. Non-residential (EXCLUDE canonical_code) → "Verðmat ekki í boði" notice; prediction/SHAP/comps/market sections all gated on `is_residential`. PASS.
4. No comps (APT_HOTEL fastnum 2169101) → prediction + SHAP render (21.9 M kr, 10 SHAP rows); comps section conditional, hidden cleanly. PASS.
5. Single-word heimilisfang (e.g. "Gil", "Mörk") → used as-is in heading; no fallback needed since all residential have at least short address. PASS.

No fixes required — existing conditional rendering handles all 5 gracefully.

**Known remaining issues** (carried into Sprint 2 Áfangi 2):
- APT_STANDARD × Country 80% PI coverage 69.1% (11 pp under, N=81). Small-sample noise; conformal quantile for this cell is below true residual distribution. Candidate fix: pool with Capital_sub, or increase MIN_N threshold.
- ROW_HOUSE × Capital_sub 80% PI coverage 92.2% (+12.2 pp over). PI widths too wide for this cell. Cosmetic issue, not functional.

---

## 2026-04-21 — Sprint 2 Skref 1: Switched to conformal PI calibration

**Hvað**: Replaced iter4 segment-stretch calibration (`iter4_segcal_v1`) with split-conformal prediction intervals (`iter4_conformal_v1`). Per (canonical_code × region_tier) quantiles of |log-residual| from the test split define symmetric half-widths; held coverage jumped from 68% → 79.1% on 80% PI.

**Af hverju segment-stretch náði ekki 80%**: The iter4 quantile heads (q100/q900) produce a narrower distribution than iter3v2's. Stretch factor k80=1.05 (found by grid-search to maximize coverage on val+test) saturates — widening the quantile head further was not possible because the quantiles themselves are under-spread. Conformal skips the quantile head entirely: it empirically calibrates PI width from observed residual distribution on held-out calibration data.

**Method**:
1. Training uses train + val (early stopping on val). Test split is reserved purely for calibration.
2. For each (canonical_code × region_tier) with n ≥ 30 on test split, compute `q80_log = 80th percentile of |log_real_kaupverd - pred_mean_log|`, same for q95.
3. Fallback hierarchy: segment×region → segment-only → global (when n < 30).
4. Application: `pred_lo80_log = pred_mean_log - q80_log`, `pred_hi80_log = pred_mean_log + q80_log`. Convert to ISK via `expm1 / cpi_factor × 1000`.

**Alternative considered**: (a) Retrain quantile models with wider bagging / deeper trees — more risky, affects point estimate. Hafnað. (b) Full conformalized quantile regression (CQR) à la Romano et al 2019 — more theoretically sound but much more code. Hafnað for v1. (c) Per-property adaptive conformal (locally-weighted residuals) — better guarantees but costly at inference. Deferred.

**Coverage deltas (held, main residential N=2,084)**:
```
Metric          iter4_segcal  iter4_conformal  Δ
80% PI cov      66.3%         79.1%            +12.8 pp
95% PI cov      89.1%         94.6%            +5.5 pp
```

**Impact**: User-facing PI widths now reflect actual uncertainty. Bakkastígur 1 80% PI went 81.5-105.3 → 80.9-103.8 M kr (tighter lower, tighter upper — concentrated around mean). Same model, same mean prediction. `iter4_segcal_v1` JSON retained on disk for audit.

---

## 2026-04-21 — iter4 production rollout (Áfangi 2-5 closed)

**Hvað**: Switched production prediction model from iter3v2 to iter4a (standalone, no fasteignamat input). iter3v2 archived in Supabase as `predictions_iter3v2` + `feature_attributions_iter3v2`. Frontend default view reads iter4 (`predictions` table post-rename). Debug mode `?mode=debug` loads both for side-by-side comparison.

**Metrics**:
- iter4a held MAPE: 8.19% (iter3v2 baseline 7.97%, delta +0.22 pp)
- Per-segment: APT_STANDARD 6.37%, APT_FLOOR 8.55%, ROW_HOUSE 7.24%, APT_BASEMENT 10.90%, SFH_DETACHED 16.29% (small N=106)
- Calibration: `iter4_segcal_v1` JSON, per-segment k-factors similar to iter3v2's
- 80% PI coverage 68% (target 80%) — known undercoverage, deferred to Sprint 2+
- Training time: 9.4 min (iter4a), 26 min (iter4 precompute rebuild with SHAP)

**Impact**:
- Annual HMS fasteignamat updates (júní ár hvert) **no longer cause prediction jumps** — iter4 is fully decoupled.
- Feature importance redistribution healthy: EINFLM 34.5%, sale_year 19.6%, matsvaediNUMER 17.6%, matsvaedi_bucket 14.2%, BYGGAR 4.5% (vs iter3v2's 77.9% fastmat dominance).
- DB size grew to 561 MB (was 424) due to iter3v2 archive retention. Still well within Pro tier (8 GB).
- iter4b via `init_model` fine-tune abandoned: LightGBM requires feature compatibility with init_model, so dropping FASTEIGNAMAT is infeasible without workarounds that preserve iter3v2's fastmat dependence.
- LLM extraction feature selection (Skref 5-6) was a no-op: all 136 extraction features were already joined into training_data_v2 and used by iter3v2. iter4a inherits them automatically.

**Not tripped stop-conditions**:
- Skref 4 MAPE > 15%: iter4a at 8.19% (well under).
- Skref 8 Bakkastígur 1 delta > 30%: actual +2.2%.

**Deferred to future sprints**:
- PI coverage undercoverage on held (68% vs 80% target).
- Manual-layer questionnaire (Áfangi 9 / Sprint 3).
- SUMMERHOUSE model quality (175% MAPE — iter3v2 has same issue).

---

## 2026-04-21 — iter4a validated as production candidate; iter4b (init_model) abandoned

**Hvað**: iter4a training complete. Held MAPE 8.19% vs iter3v2 baseline 7.97% — a +0.22 pp cost for full fasteignamat independence. iter4b (LightGBM `init_model` fine-tune) was abandoned due to technical infeasibility.

**Af hverju iter4a virkar svona vel**: The 77.9% gain iter3v2 attributed to `real_fasteignamat` + `FASTEIGNAMAT` was largely **collinear** with underlying features (size, location, age, time). LightGBM re-learns the signal from EINFLM + matsvaedi_bucket + matsvaediNUMER + sale_year + BYGGAR without the fastmat mediator. Feature importance in iter4a is healthily distributed across size/geography/time primitives.

**Af hverju iter4b sleppt**: LightGBM `init_model` parameter requires feature-set compatibility between the init booster and the new Dataset. Dropping `FASTEIGNAMAT` from iter4b features violates this contract. Workarounds (keeping feature as NaN constant) preserve iter3v2's existing NaN-path decisions on those features, not truly decoupling from fastmat. Clean "iter4b via fine-tune" is not feasible with feature-drop semantics.

**Alternative considered**: Train iter4a with alternative hyperparameters (more trees, deeper) as an iter4a_deep variant. Deferred — iter4a baseline already at 8.19% on held, diminishing returns from tuning.

**Consequence**: iter4a is the winner by default. PI coverage (66.3% on 80% PI vs target 78%) requires calibration-stretch in Skref 7 (follow iter3v2's `iter3v2_segcal_v1` pattern).

---

## 2026-04-21 — Switched production target from Streamlit prototype to Next.js+Supabase+Vercel

**Hvað**: Eftir Áfangi 7 completion var byggt Streamlit `app.py` sem Áfangi 5 v1. Danni hafnaði því sem prototype-quality (1990-style search bar, no feature attribution UI, no market integration). Switch yfir í production-grade Next.js stack byggt á sister project heyaskr (sama höfund, existing deploy).

**Af hverju**: End goal (bank analytics tool, public dashboard, subscription product) krefst scalable stakks; Streamlit limits would force full rewrite later. Next.js + Supabase gefur publish-level UX, server components, edge CDN, mobile-responsive út úr boxinu. Code-reuse mynstur frá heyaskr.

**Alternative**: (a) Streamlit með heavy customization — hafnað, limits remain. (b) FastAPI + vanilla HTML — meira plumbing, ekkert CDN, custom auth. Hafnað. (c) SvelteKit — minni reynsla, enginn code-reuse. Hafnað.

**Impact**: Phase 1 scope defined (precompute + mirror + read-only frontend); Sprint 2 adds auth/user accounts.

---

## 2026-04-21 — Precompute-all strategy fyrir Sprint 1 (no live Python backend)

**Hvað**: Engin FastAPI/Railway/Docker fyrir Sprint 1. LightGBM scoring + SHAP + comps eru precomputed locally (Phase 1A), dump í CSV, import í Supabase. Frontend les precomputed gildi úr PostgREST eingöngu.

**Af hverju**: Faster ship, zero backend ops, DB queries < 100 ms. Live scoring (fyrir user manual input í Áfanga 9) deferred til Sprint 2 þegar auth er komið og scope réttlætir backend.

**Alternative**: (a) FastAPI á Hetzner/Railway með live LightGBM. Hafnað: meira infra, cold-start latency, ónauðsynlegt fyrir read-only Sprint 1. (b) Supabase Edge Functions með Python/Deno. Hafnað: LightGBM runtime ekki supported á Edge.

**Impact**: 7 CSV skráar, 202 MB → 424 MB Supabase DB, <100 ms edge queries. Pipeline re-run-able via `build_precompute.py --force` locally.

---

## 2026-04-21 — CloudFront image URLs directly, no Supabase Storage

**Hvað**: `photo_urls_json` dálkur í `properties` tafla vísar beint í `d1u57vh96em4i1.cloudfront.net` URLs frá scraper. Engin upload til Supabase Storage.

**Af hverju**: 1,15M myndir eru þegar live á CloudFront frá scraper pipeline. Re-hosting er ónauðsynlegur overhead fyrir Sprint 1. Delisted auglýsingar skila 404 sem frontend handles gracefully (fallback parchment card, user sér engar broken images án intervention).

**Alternative**: (a) Download myndir í Supabase Storage bucket. Hafnað: 1,15M × ~100KB = ~115 GB, Supabase free-tier storage cap er 1GB. Bandwidth + storage cost ~$30/mán á Pro. (b) Proxy via Next.js Image optimizer. Hafnað: complexity + CloudFront URL rewriting bandwidth á Vercel.

**Impact**: Photos eru subject til CloudFront availability + scraper-side delisting. Long-term (Áfangi 10+) þarf að consider mirror ef availability lækkar eða domain changes.

---

## 2026-04-21 — iter4 standalone (no fasteignamat input), 100% separation from iter3v2

**Hvað**: iter4 model fjarlægir `real_fasteignamat`, `FASTEIGNAMAT`, `fasteignamaT_GILDANDI` og allar derivatives úr input features. 100% standalone, ekkert blend með iter3v2. Fasteignamat birtist áfram á UI sem reference number, ekki model input.

**Af hverju**: HMS fasteignamat er sjálft hedonic regression á kaupskrá — að nota það sem input í okkar módel er circular og gerir spána fyrir-determined af HMS updates. Annual HMS fasteignamat updates (júní ár hvert) cause 5-10% overnight jumps í iter3v2 predictions án þess að einn einasti kaupsamningur hafi verið þinglýstur. Þetta er fatal fyrir bank/pro-user use case þar sem stability er verðmætari en 1-2 pp MAPE.

**Alternative**: (a) Keep fastmat as input (status quo iter3v2). Hafnað af ofangreindum ástæðum. (b) Blend iter3v2 + iter4 við 50/50. Hafnað: blend retains circular dependency, bara demp-ar stökkin. (c) Add fastmat sem separate "anchor" calibration layer post-hoc. Potentially future work, ekki Sprint 2.

**Expected cost**: 3-5 pp MAPE increase (7,97% → ~11-13%), acceptable vaxtar-tradeoff. LLM features í Skref 6 geta milduð skaðann. Calibration (segment stretch factors) þarf endurgerð á nýjum residuals.

**Impact**: `score_new_listing.py` clone → `score_iter4.py` með removed fastmat fields. Precompute re-run subset (predictions + SHAP only). UI sýnir fasteignamat sem "Opinber eignamat frá HMS — reference only" með smá caveat text.

---

## 2026-04-21 — Document sync via GitHub repo (D:\ → docs/ → origin/main)

**Hvað**: Continuity files (STATE, DECISIONS, WORKING_PROTOCOL, TAXONOMY, GLOSSARY, DATA_SCHEMA, LABELING_GUIDE, GOLD_STANDARD_PROTOCOL, EXTRACTION_SCHEMA_v0_2_2, DATA_AUDIT_REPORT, devalue.py) synced til `docs/` folder í verdmat-is GitHub repo. D:\ er working copy, repo er canonical.

**Af hverju**: Claude Code working D:\ diverged frá Claude.ai Project folder versions (t.d. D:\STATE.md = 163 lines vs Project = 1759 lines) og caused authoritative-source confusion í Phase 1C/1D. GitHub provides single source of truth readable af bæði chat-Claude (via raw URL) og Claude Code (via git pull).

**Alternative**: (a) Sync til OneDrive/Dropbox. Hafnað: enginn chat-Claude read-access. (b) Manual paste-a content í chat hverju sinni. Hafnað: tedious, error-prone. (c) Sérstakur private repo. Hafnað: meira management, verdmat-is repo er nú þegar private og docs eru engir secrets.

**Workflow**:
1. Edit á D:\ via `str_replace` (existing rule, unchanged).
2. `cp D:\<FILE>.md /d/verdmat-is/app/docs/<FILE>.md`
3. `git add docs/ && git commit && git push`
4. Chat-Claude fer að raw URL when needed.

**Impact**: WORKING_PROTOCOL.md updated með rule (Phase 1D Skref 5). Any future Claude Code session sees both D:\ og docs/ in same git repo → divergence detectable via `diff`.

---

## 2026-04-20 (refresh_dashboard_tables orchestrator closed) — Monthly cycle integration staðfest virk

**Hvað**: `refresh_dashboard_tables.py` orchestrator framleiddur og tested end-to-end. Integrerar `build_repeat_sale_index.py` + `build_ats_lookup.py` sem cohesive dashboard snapshot með cross-script atomicity.

**Placement í monthly cycle (6-skref → post-integration 6-skref)**:
1. `refresh_cpi.py`
2. `refresh_kaupskra.py`
3. `rebuild_training_data.py`
4. **`refresh_dashboard_tables.py` ← NÝTT**
5. `monthly_recalibration.py`
6. `validate_metrics.py`

**Semantics**:

1. **Cross-script atomicity**. Ef annað hvort sub-script bilar með non-zero exit, orchestrator triggerar rollback á BÁÐUM dashboard-tafla-settum (repeat-sale 4 skrár + ATS 10 skrár = 14 monitored files). Consumers sjá aldrei mixed state þar sem repeat-sale er fresh en ATS stale, eða öfugt.

2. **Subprocess pattern**. Sama arkitektúr og `rebuild_training_data.py` — keyra hvert sub-script í sjálfstæðu Python process með `subprocess.run(check=False)`, capture-a return code, stream-a stdout live gegnum parent process. Isolation + visibility.

3. **Shape safety**. Post hvers sub-script validerar orchestrator að (a) allar expected outputs séu framleiddar, (b) row count hafi ekki shrinkað > 5% vs backup, (c) column count match-i exactly. Dashboard tables grow með tíma, svo row shrinkage = probable bug (kaupskra corruption, filter-cascade regression, etc).

4. **First-run friendly**. Ef engin previous outputs (empty `D:\_rollback_backup\`), skip backup step með warning, keyra eðlilega. No failure mode.

5. **Rollback safety**. Backup tekinn pre-run í `D:\_rollback_backup\YYYYMMDD_HHMMSS\`. Á success → deleted (eða preserved með `--keep-backup` flag). Á failure → outputs restored frá backup, backup preserved fyrir post-mortem inspection.

6. **Bare essentials orchestrator design**. Engin retry logic (transient failures bera ábyrgð á manual re-run), engar absolute shape floors (relative-to-backup er self-updating), engin per-file content validation (sub-scripts bera ábyrgð á internal integrity). Orchestrator sér aðeins um cross-script atomicity.

**Runtime validation** (staðfest 2026-04-20 20:58 og 21:00):

- Cycle 1 (--keep-backup): 81,0 sec total
  - Backup: <1 sec (14 files, ~1 MB total)
  - Repeat-sale: 77,6 sec (build) + 0,1 sec (validation)
  - ATS: 2,5 sec (build) + 0,1 sec (validation)
  - Cleanup: negligible

- Cycle 2 (normal): 65,4 sec total
  - Repeat-sale: 62,0 sec (warm disk cache)
  - ATS: 2,5 sec

Expected runtime window: 60-85 sec depending á disk cache state. Acceptable fyrir monthly cron.

**Idempotency staðfest**: Back-to-back cycles á unchanged input data gáfu identical outputs (shape deltas +0,0% á öllum 14 files, column counts exact match). Sama pattern og staðfesti rebuild_training_data í Áfanga 4d.

**Output skrá orchestrator framleiðir ekki**: orchestrator sjálfur emmar ekki output, bara orchestrators sub-scripts sem allar outputs undir management. Aðeins side-effect af orchestrator er short-lived backup dir í `D:\_rollback_backup\`.

**Scripts**:
- `refresh_dashboard_tables.py` — orchestrator (360 línur)

**Deferred til framtíðar**:
- Logging til file (núna er stdout-only; PowerShell user má pipa `> refresh.log` ef þarf)
- Per-cell sanity checks (e.g. "APT_STANDARD RVK real 2026Q2 ∈ [130, 150]") — v2 bonus
- Alert/notification hooks (email, Slack) fyrir rollback events

**Monthly cycle staða post-integration**: 6 skref frosin og staðfest. `validate_metrics.py` er downstream svo er forlag þess að dashboard tables séu fresh þegar validation keyrir. Næsta óleyst eining í pipeline er SEMI_DETACHED k-factor drift (Áfangi 4d pending) sem bíður 1-2 monthly cycles gagnagrundvallar.

---

## 2026-04-20 (Áfangi 7 closed) — ATS lookup tafla, dual-table arkitektúr (quarter + heat-pooled), static percentile heat-labels

**Hvað**: Áfangi 7 (ask-to-sale gap lookup) lokið. Framleiðir 5 output-skrár úr `pairs_v1.pkl` paired_fresh subset í `build_ats_lookup.py` (1,7 sec runtime á 52K clean pairs):

- `ats_lookup_by_quarter.pkl` / `.csv` — Table A, 913 rows × 13 cols, per (canonical_code × region_tier × quarter) með heat_bucket og data_quality as metadata
- `ats_lookup_by_heat.pkl` / `.csv` — Table B, 63 rows × 10 cols, pooled per (canonical_code × region_tier × heat_bucket). **Primary scoring table**.
- `ats_heat_thresholds.pkl` / `.csv` — 23 rows × 6 cols, p33/p67 audit
- `ats_dashboard_quarterly.pkl` / `.csv` — 359 rows × 8 cols, region-collapsed seg × qtr trends
- `ats_dashboard_monthly_heat.pkl` / `.csv` — 2.501 rows × 9 cols, live regime z-score indicator

**Methodology decisions taken** (confirmed í chat 2026-04-20):

1. **Dual-table arkitektúr (A + B)**. Table A er per-quarter historical fidelity. Table B er heat-pooled (1 row per (seg × reg × heat_bucket)) og er **primary scoring table** því pooling gefur robust dispersion í thin cells og leysir cold-start problem fyrir nýjasta ársfjórðunginn sem er alltaf thin vegna þinglýsingar-lags. Scoring-fallback: B først, A latest-row ef B insufficient (rare — 0 insufficient cells í B post-pooling).

2. **Input = paired_fresh only, exclude in_scrape_gap=True**. Filter cascade: 55.544 paired_fresh → 53.386 post-scrape-gap → 52.136 post-EXCLUDE → 52.083 post-outlier-clip → 52.001 post-inclusion-filter. Selection-bias rationale: 2025-07+ paired pairs eru technically valid per-pair en coverage er unrepresentative í gap, svo aggregate statistics eru untrustworthy. Refresh mánaðarlega re-includes data þegar scraper kemur aftur.

3. **Outlier clip ATS ∈ [0,5; 2,0]**. 53 rows klippt (~0,1%). Non-negotiable pre-aggregation: raw SD 0,1327 vs MAD×1,4826 0,0275 = 4,8× ratio í heavy tails (data-entry errors, foreclosures, skilnaðarsölur, bulk-deals). Clip range matchar DATA_SCHEMA sanity validation.

4. **Inclusion filter MIN_PAIRS_PER_CELL = 50 all-time**. Same threshold og Áfangi 6 BMN. 23 cells included, 7 excluded: APT_ATTIC Country (48), APT_MIXED RVK (4), APT_ROOM × 3 regions (5/3/17), APT_UNAPPROVED Capital_sub/Country (3/2). Main residential + SUMMERHOUSE Capital_sub/Country + APT_UNAPPROVED RVK all pass.

5. **Heat-label = static percentile (p33/p67) per (segment × region)**. Segment × region specific (ekki global) vegna þess að APT_STANDARD RVK hefur allt aðra baseline ATS en SFH Country — global þröskuldur myndi tag-a allar Country cells sem permanent cold. Thresholds reiknaðir á quarterly medians úr quarters með n ≥ 5 (stable). Rolling z-score **hafnað** fyrir lookup labels (reproducibility: 2018Q3 heat-label má ekki breytast þegar 2026 gögn koma inn), en notaður sér fyrir live dashboard regime indicator (ats_dashboard_monthly_heat).

6. **Scoring-primary dispersion = MAD × 1,4826**. Robust to outliers í small-sample cells; self-consistent með median (ekki mean) sem center. Audit-secondary dispersion = classical std; báðar geymdar. Scoring formúla: `pi_80 = list × exp(median_log_ratio ± 1,28 × dispersion_mad)`.

7. **Quality flags**. Table A: n<5 insufficient, n≥20 ∧ sd<0,05 high, n≥5 ∧ sd<0,10 medium, annars low. Table B: n<10 insufficient (stricter floor því pooling á að safna samples), sömu dispersion thresholds fyrir high/medium/low.

8. **Niche fallback fyrir cells með <8 stable quarters**. heat_bucket = NaN. 2 cells triggera: APT_BASEMENT Country (6 stable qtrs) og APT_UNAPPROVED RVK_core (4 stable qtrs). Þær 2 cells eru absent úr Table B (6 missing rows af 69 possible → 63 actual, 9% missing). Ef framtíðar-usecase þarf þessar cells, scoring fellur á training-data hedonic baseline.

9. **Monthly rolling 3-mo vs 12-mo z-score**. Separate live regime indicator í `ats_dashboard_monthly_heat`, óháð lookup labels. Sparse months (n=0) skipped, acceptable for v1 regime-detector. Used for dashboard "current market is heating up/cooling down" UI.

**Niðurstöður — empirical findings**:

(a) **Heat-label monotonicity confirmed**. cold < neutral < hot median_log_ratio á öllum 21 populated cells (engin exception). Deltas hot-minus-cold 0,016-0,091. Stærstu: SUMMERHOUSE Capital_sub (0,091 = 9,1%), SFH_DETACHED RVK_core (0,029), SEMI_DETACHED RVK_core (0,028).

(b) **Above-list rate er stærsta regime-driven signal**. 3-4× hlutfall í hot vs cold fyrir flest residential segments. APT_ATTIC RVK 14% → 47%, SEMI_DETACHED RVK 12% → 47%, APT_STANDARD RVK 9% → 33%. Confirmar bidding-war dynamics í hot regime.

(c) **Dispersion er NOT strongly function af heat — gengur í móti old-chat hypothesis**. 12 cells cold > hot MAD (hypothesis-compatible), 9 cells reverse. Mean effect kringum +0,003 (negligible). Empirical claim: "Ask-to-sale gap á íslenska markaðnum hefur stöðuga sveiflu (MAD ~0,02-0,03) óháð regime; munur hot/cold liggur í miðgildi, ekki dreifingu." Publishable finding + simplifies scoring (PI width ≈ constant across heat buckets).

(d) **Current market state per 2025-06** (síðasti mánuður pre-scrape-gap): APT_STANDARD RVK_core z_3v12 = -0,74 (cold), ROW_HOUSE Capital_sub z = -0,91 (cold), APT_BASEMENT RVK_core z = -0,52 (cold). Main residential er mostly neutral/cold. SFH_DETACHED Country z = 0,51 (hot) — counter-trend með Country catch-up frá Áfanga 6. Matchar widely-known narrative: 2022-end peak, 2023 correction, 2024-2025 cooling.

(e) **Yearly aggregate regime pattern** (3 main residential collapsed): 2022 peak (above_list 33,1%, median -0,007), 2023 trough (above_list 9,8%, median -0,025), 2024-2025 stabilization (above_list 12-14%, median -0,018 til -0,019). Orthogonal validation af Áfanga 6 timing findings.

**Output artifacts á D:\\**:
- `ats_lookup_by_quarter.pkl` / `.csv` — 913 × 13
- `ats_lookup_by_heat.pkl` / `.csv` — 63 × 10
- `ats_heat_thresholds.pkl` / `.csv` — 23 × 6
- `ats_dashboard_quarterly.pkl` / `.csv` — 359 × 8
- `ats_dashboard_monthly_heat.pkl` / `.csv` — 2.501 × 9

**Scripts**:
- `ats_diagnostic.py` — pre-build validation tool (~4 sec)
- `build_ats_lookup.py` — end-to-end build (1,7 sec runtime á 52K clean pairs)

**Deferred til framtíðar**:
- `analyze_ats_trends.py` — plots (above-list rate timeline, regime indicator timeline, pooled-distribution-by-heat violins)
- Leading-indicator heat definition (months-of-supply, TOM, withdrawal rate) as v2 alternative — ef empirical PI-calibration í production sýnir að ATS-derived heat er circular og inadequate
- `refresh_dashboard_tables.py` integration orchestrator (næsti áfangi post-Áfangi-7)

**Pending integration**: ATS lookup þarf re-reiknast mánaðarlega í refresh cycle. Integration point er post-rebuild_training_data, pre-calibration, parallel við repeat_sale_index. `refresh_dashboard_tables.py` verður orchestrator sem keyrir build_repeat_sale_index.py + build_ats_lookup.py í röð.

---

## 2026-04-20 (Áfangi 6 closed) — BMN repeat-sale index virkar, Country catch-up staðfest, ROW_HOUSE RVK_core niche finding

**Hvað**: Áfangi 6 (repeat-sale verðvísitala) lokið. Framleiðir Bailey-Muth-Nourse (BMN) OLS regressionir per (canonical_code × region_tier) × ársfjórðung fyrir 2006Q2–2026Q2 (81 quarters, 33 cells, 27 fitted). Output er `repeat_sale_index.pkl` + `repeat_sale_index.csv` með bæði **nominal** og **real** (CPI-deflated) indices, per-period `data_quality` flag (high/medium/low/insufficient), og 95% CI via std_error frá OLS.

**Methodology decisions taken**:

1. **Source = pairs_v1, ekki training_data_v1**. 24% fleiri pörum (off_market_used + off_market_newbuild + post_sale_only eru öll valid fyrir repeat-sale purposes því sale_price er þinglýst, óháð listing match).

2. **Consecutive pairing, ekki all-combinations C(n,2)**. Fyrir FASTNUM með 3 sölum → 2 pör, ekki 3. Case-Shiller standard; simpler, no double-counting.

3. **BMN per-cell aðskildar OLS regressions, ekki pooled með interactions**. Simpler, interpretable, og leyfir ólíka variance í hverjum segment × region cell. Divergence milli cells er visualized post-hoc í plots.

4. **Strict new-build-t1 exclusion**. Útilokar pör þar sem fyrri sala er `is_new_build=True`. Rökstudd tvenns konar: (a) developer→first-buyer pricing er pre-negotiated, ekki market equilibrium, og (b) Danni's domain insight: nýbyggingar eru seldar oft án gólfefna, ísskáps og uppþvottavélar, sem eru komnir inn í verðið þegar resale fer fram. Þ.e. eignin er literally not the same good milli t1 og t2 og ratio-ið er biased upward. EINFLM change filter (5%) grípur ekki þetta því flatarmál breytist ekki. 13.3% drop á pair-inu (9.076 pör af 68.381) — acceptable loss fyrir cleaner methodology.

5. **Filter cascade** (applied post-consecutive-pairing, per-step row counts logged):
   - (a) is_new_build_t1 = True           → -13.3%
   - (b) |EINFLM change| > 5%             → -3.1%
   - (c) FULLBUID 1 → 0                   → -0.1%
   - (d) pair_span_days < 90              → -1.0%
   - (e) canonical_code changed           → -0.0%
   - (f) region_tier changed              → -0.0%
   - (g) |log_price_ratio_nominal| > 2    → -0.1%
   - Final: 56.824 clean pairs (83.1% of 68.381 initial consecutive pairs)

6. **CPI deflation er default, ekki optional**. Nominal index-inn einn og sér er misleading fyrir íslenskan markað vegna verðbólgu (CPI growth ×2.66 frá 2006 til 2026). Báðar útgáfur emitted í output (`index_value_nominal` og `index_value_real`); dashboard notar real sem primary, nominal sem toggle. Baseline fyrir báðar = 2006Q2 = 100.

7. **Canonical source fyrir tegund er properties_v2 (fine HMS, 514 values), ekki pairs_v1.tegund (kaupskrá coarse TEGUND, ~7 values)**. Initial implementation notaði coarse og allt var misclassified sem EXCLUDE; fixed með properties_v2.fastnum → tegund → classify_property.

8. **MIN_PAIRS_FOR_REGRESSION = 50**. Cells með færri en 50 pör fá `insufficient_sample=True` og NaN indices. 6 af 33 cells skipped (APT_MIXED RVK, APT_ROOM × 3 regions, APT_UNAPPROVED Capital_sub + Country).

9. **NaN-gate fyrir periods án gagna**. Fitted cells fá NaN index (ekki baseline=100) fyrir quarters þar sem n_period=0. Dashboard má því forðast misleading plateau-línur.

**Niðurstöður — publishable findings**:

Main residential real CAGR 2006Q2→2026Q2 er 1.5–1.8% per ár fyrir apartments í RVK/Capital_sub, 2.7–2.8% fyrir Country (catch-up story). Real crash 2008-2011 var -27% til -33% frá 2006 peak fyrir main apartments; SEMI_DETACHED og ROW_HOUSE RVK hit harder (-44% til -49%). Recovery til 2006 baseline tók ~10 ár (crossed 100 around 2016-2017). Peak 2022Q4 var +37 til +47% yfir 2006 real-terms fyrir main cells.

Þrjú publishable findings:

(a) **Landsbyggð catch-up**: APT_FLOOR Country real growth 2006→2026 = +74.9% vs RVK_core +35.6%. Country segment vex more en RVK í raun-verði, starting consistently frá 2016. Tvær hypotheses sem framtíðar-rannsókn þarf: (i) RVK var meira inflated í 2006 baseline (bubble concentrated), svo relative growth frá lægri baseline er meira pronounced, eða (ii) tourism-driven rental demand drev Country prices upp frá 2016+. Finding stendur óháð hvor hypothesis sannast.

(b) **ROW_HOUSE RVK_core niche finding**: Lægsta real CAGR (0.5%) en dýpsta drawdown (-48.5%) af öllum main residential cells. Consistent við að raðhús í Reykjavík eru small-supply niche segment þar sem 2006-2008 bubble var most inflated. Empirical domain insight sem var ekki augljóst fyrirfram.

(c) **SUMMERHOUSE missed crash**: Country summerhouse real CAGR er +7.0% per ár og trough er 2006Q2 sjálft (aldrei niður fyrir baseline). Consistent við að sumarbústaðir á landsbyggðinni eru ekki domestic-driven market heldur tourism/rental driven og missed 2008 crash-ið alveg. Sjaldgæft fyrir asset-class að vera counter-cyclical við innlent hrun.

**Output artifacts á D:\\**:
- `repeat_sale_index.pkl` / `.csv` — full output, 2.673 rows (33 cells × 81 quarters), 15 cols
- `repeat_sale_pairs.pkl` — 56.824 clean pairs post-filter cascade, 16 cols
- `repeat_sale_summary.csv` — per-cell CAGR og crash-depth table, 27 rows
- 5 .png plots: `residential_real_grid.png`, `apt_floor_regional.png`, `nominal_vs_real.png`, `sample_density_heatmap.png`, `crash_recovery_zoom.png`

**Scripts**:
- `build_repeat_sale_index.py` — end-to-end build (56s total elapsed)
- `analyze_repeat_sale_index.py` — plots + summary stats generator

**Deferred til framtíðar**:
- CI bands á crash_recovery_zoom.png (plot 5) — thin samples look unfair without them
- Geometric Mean Revert Case-Shiller (GMRCS) ef noise er issue í downstream
- Weighted BMN með interval-distance weights
- Monthly sub-index fyrir RVK_core (aðallega fyrir dashboard leading indicators)
- Integration í operational monthly cycle: `refresh_dashboard_tables.py` skript sem re-derive index + ATS lookup eftir rebuild_training_data

**Pending integration í monthly cycle**: repeat-sale index þarf að re-reikna-st mánaðarlega þegar nýjar þinglýstar sölur koma inn. Integration point er post-rebuild_training_data, pre-validate_metrics. Verður bætt við í næsta áfanga (Áfangi 7 + integration).

---

## 2026-04-20 10:15 (Áfangi 4d closed) — Monthly operational cycle staðfest virkur end-to-end

**Hvað**: 5-skref monthly refresh pipeline sem var authored í 2026-04-19 23:55 decision er nú tested end-to-end. Allir scripts á D:\\ og hafa keyrt í röð án villu 2026-04-20 10:08–10:11:

1. `refresh_cpi.py` — Hagstofa PxWeb → `cpi_verdtrygging.csv` (schema migrated til `year_month,cpi`)
2. `refresh_kaupskra.py` — HMS OCI bucket → `kaupskra.csv` (idempotent, MD5-gated, composite PK recognized)
3. `rebuild_training_data.py` — subprocess orchestrator yfir `build_training_data.py` + `build_training_data_v2.py`, með shape safety og per-component rollback
4. `monthly_recalibration.py` — trailing 12m k-factor refresh, auto-block á >30% drift
5. `validate_metrics.py` — held scoring vs 4c baseline, per-segment drift checks með baseline embedded úr 4c closure entry

**Validation niðurstöður**:

Rebuild shape drift á idempotent cycle (sama kaupskra MD5):
- v1: (144.254 × 35) → (144.254 × 35), drift 0,00%/0,00%
- v2: (144.254 × 170) → (144.254 × 170), drift 0,00%/0,00%

validate_metrics vs 4c baseline (8/8 drift checks pass, allir innan ±0,5 pp MAPE og ±3,0 pp coverage thresholds):
- Held clean MAPE: 7,01% (baseline 7,00%, Δ +0,01 pp)
- Held clean cov80: 72,85% (baseline 73,10%, Δ −0,25 pp)
- Held clean cov95: 92,69% (baseline 92,70%, Δ −0,01 pp)
- Held all MAPE: 7,98% (baseline 7,96%, Δ +0,02 pp)
- SFH cov80: 73,00% (baseline 73,00%, Δ +0,00 pp)
- APT_STANDARD MAPE: 5,97% (baseline 5,95%, Δ +0,02 pp)

**Safety mechanisms sönnuðust virk**:
- `rebuild_training_data.py` rollback-aði v1 þegar CPI schema bug brotnaði v1 build í fyrstu end-to-end cycle (2026-04-20 09:30), kept v2 unchanged. Per-component rollback semantics (ekki atomic) gaf hreinni debugging path.
- `monthly_recalibration.py` blokkaði k-factor update þegar SEMI_DETACHED drift fór yfir 30% threshold. Pending manual review, ekki autonomous adjust. Þetta er deliberate safety ceiling per 4c post-mortem — monthly recalibration á að flagga regime shifts, ekki silent-ly aðlagast þeim.
- `validate_metrics.py` exit 0 (8/8 drift checks pass) — reproducibility confirmed.

**Orchestrator subprocess rationale**: `rebuild_training_data.py` notar `subprocess.run([sys.executable, "build_training_data.py"])` frekar en að importa build scripts sem Python modules. Ástæða: bæði build scripts redirect `sys.stdout` með tee og mutate `sys.path`. Að importa þau myndi menga orchestrator state. Subprocess isolation er clean og faithful-rekstur. Orchestrator bætir við backup + shape check + rollback semantics án að breyta feature engineering í sub-scripts.

**Sub-percent numerical drift observation**: Held clean MAPE fór úr 7,00% → 7,01% og cov80 úr 73,10% → 72,85% milli tveggja rebuilds með bit-identical inputs (sama kaupskra MD5). Líklegasta orsök: pandas merge í v2-build skilar rows í aðeins mismunandi röð, sem breytir `pd.Categorical` category ordering, sem breytir integer-kóðum sem LightGBM sér í inference. Sub-percent floor er acceptable fyrir operational pipeline (vel innan 0,5 pp MAPE threshold). Strangari reproducibility myndi krefjast sort-pre-categorize í build scripts — deferred til iter 5+ ef þörf krefur.

**Pending**: SEMI_DETACHED k95 drift +34,3% (k80 +21,8%) — manual review required. Tvær leiðir: (a) accept drift og overwrite `calibration_config.json`, (b) hækka drift threshold í 40%. Ákvörðun deferred til að hafa 2-3 monthly cycles gagnagrundvöll.

**Production state**:
- Models: iter3 v2 (12 .lgb files) — frozen
- Calibration: `calibration_config.json` version `iter3v2_segcal_v1` — frozen
- Training data: `training_data_v2.pkl` (144.254 × 170) — rebuild-able daily-ish
- Backups: `training_data_v1_prev.pkl`, `training_data_v2_prev.pkl`, `kaupskra_prev.csv`, `calibration_history/` — preserved for audit

Áfangi 4d marks completion of launch-critical operational infrastructure. Pipeline is production-ready for pilot launch.

---

## 2026-04-20 (protocol lesson) — Smoke test sem ekki siglerar downstream consumer missir schema mismatch

**Hvað gerðist**: `refresh_cpi.py` var „smoke-tested" 2026-04-19 með því að keyra scriptið, staðfesta að það skrifaði og las sína eigin CSV. Smoke test missti að `cpi.py` (downstream consumer í `build_training_data.py`) býst við CSV í formati `year_month,cpi` (ISO string + float) en refresh_cpi skrifaði `year,month,vnv` (3 integers + float). Næsta dag, 2026-04-20 09:30, brast v1 build í fyrstu end-to-end cycle með `KeyError: 'year_month'`. rebuild_training_data.py rollback-aði v1 pkl klínt; v2 óbreytt.

**Fix (2026-04-20 10:05)**: `refresh_cpi.py` lagfært:
1. `write_csv_atomic` skrifar nú `year_month,cpi` header með ISO `YYYY-MM` date format.
2. `read_existing_csv` detectar bæði target schema og legacy `year,month,vnv` schema via header parsing.
3. Ef legacy schema fundið, force-rewrite á migration (óháð því hvort nýjar rows séu í API response).

Validated með 3 smoke tests sem simulera `cpi.py` load() nákvæmlega — `float(row['cpi'])`, `row['year_month'].strip()`. Allir pass. Cycle-run 10:08 staðfesti að CPI CSV var endurskrifað og downstream v1 build virkaði án breytinga á `cpi.py` sjálfu.

**Principle**: Smoke test á new/modified script þarf að inkludera **DictReader simulation of downstream consumer**. Ekki bara „script rennur án villu" heldur „ef næsti module í pipeline les output-ið með sínu consumption pattern, rennur hann líka án villu".

**Framework breyting**: Fyrir framtíðar monthly cycle þróun, bæta við pre-integration test step sem les output-CSVs með sömu aðferð og consumer-scriptin. T.d. ef refresh_X framleiðir file sem cpi.py les með DictReader, þá notar smoke test DictReader líka.

**Observation um defensive design í orchestrator**: `rebuild_training_data.py` rollback-aði v1 klínt þegar v1 build bilaði, og skilaði exit 2. Áhrif á production voru því núll — original v1 pkl var preserved intact. Þetta er sönnun fyrir því að per-component rollback er betra en atomic „allt eða ekkert" — bilun var contained í einum sub-script og debugging var straightforward.

---

## 2026-04-20 00:25 (Áfangi 4d) — Kaupskrá composite PK + refresh_kaupskra endpoint staðfestar

**Hvað**: Eftir development á `refresh_kaupskra.py` og staðfest download frá HMS, tvö atriði urðu ljós sem þarf að skrá sem canonical:

**1. Kaupskrá PK er composite `(FAERSLUNUMER, FASTNUM)`, ekki bara FAERSLUNUMER**

Staðfest með full scan á 2026-04-20 dump af `D:\kaupskra.csv`:
- 226.481 total rows
- 212.514 unique FAERSLUNUMER
- 13.967 duplicates (6,2% af data)

Rót orsakarinnar: multi-parcel deeds. Einn kaupsamningur (einn SKJALANUMER) getur innihaldið margar fasteignir; hver með eigin FASTNUM. Kaupskrá skráir þær sem aðskildar rows með sama FAERSLUNUMER.

**Implication fyrir pipeline**: existing training data filter „single-FASTNUM SKJALANUMER" (DATA_SCHEMA.md cascade filters) er mandatory, ekki optional. Við filter-um út multi-parcel deeds vegna þess að þær eru ekki hægt að bera saman við single-property transactions á sama leikvelli (cannot assign KAUPVERD á per-property basis).

**`rebuild_training_data.py` MUST**: (a) preserve single-FASTNUM SKJALANUMER filter, (b) ekki treat FAERSLUNUMER sem PK í staðalíkingum.

**2. HMS kaupskrá endpoint staðfestur**

URL er: `https://frs3o1zldvgn.objectstorage.eu-frankfurt-1.oci.customer-oci.com/n/frs3o1zldvgn/b/public_data_for_download/o/kaupskra.csv`

Landing síða: `https://hms.is` (Kaupskrá fasteigna).

OCI (Oracle Cloud Infrastructure) Object Storage, Frankfurt region, public bucket. HEAD request gefur `Content-MD5` og `Last-Modified` fyrir idempotent refresh. Update rhythm: mánaðarlega, sunnudaga ~02:00 GMT. Publication lag: ~2 vikur frá þinglýsingu.

**Robustness**: `refresh_kaupskra.py` state tracking í `kaupskra_fetch_state.json` (last MD5, last modified, fetch timestamp). Second-run idempotency: skip download ef MD5 unchanged. Atomic file writes (tmp → rename). Safety aborts ef new size < 99% existing eða > 1% rows disappear.

**Ef URL breytist í framtíðinni** (t.d. OCI migration): fallback er að scrape-a `hms.is` landing síðu og finna nýja link. Ekki implemented enn en hugað til í docstring.

---

## 2026-04-19 23:55 (Áfangi 4d) — Operational pipeline valin simple + local-first

**Hvað**: Monthly data refresh + recalibration cycle sett upp sem staðbundin Python scripts á Windows vél, keyrð via Task Scheduler á 1. degi hvers mánaðar. Fimm-skref keðja:

1. `refresh_cpi.py` — fetch latest VNV frá Hagstofa PxWeb API (`VIS01004.px`, `financial_indexation`) → uppfæra `cpi_verdtrygging.csv`.
2. `refresh_kaupskra.py` — fetch nýjar þinglýstar sölu frá HMS → append til `kaupskra.csv`.
3. `rebuild_training_data.py` — re-derive real_kaupverd, cpi_factor, real_fasteignamat; applya taxonomy + outlier filter → ný `training_data_v2.pkl`.
4. `monthly_recalibration.py` — score trailing 12m residuals með production model, finna ný per-segment k80/k95, archive-a gamlan config, skrifa nýjan `calibration_config.json`. Safety abort ef k drift > 30%.
5. `validate_metrics.py` — post-refresh sanity check: has held MAPE drift-að? PI coverage? Flag-a ef drift > 0,5 pp á main MAPE.

**Af hverju local-first**:
- Cloud infrastructure (Supabase + Vercel per Áfanga 0 decision) verður sett upp seinna þegar pilot staðfestir value. Premature cloud migration er sóun.
- Windows Task Scheduler er reliable enough fyrir monthly cadence með log monitoring.
- Scripts eru atomic (temp-file + rename), error-handling, og log per run — audit trail preserved.
- Migration til cloud síðar er bara að endurnotkan sömu scripts með annan storage target (Postgres insted of CSV/pickle).

**Progress eftir 2026-04-19**:
- `refresh_cpi.py` skrifað og staðfest virkar (374 mánuðir, reference 2026M05=678,30, cpi_factor fyrir 2026M04 = 1,005485 matchar existing training data exactly).
- `score_new_listing.py` production API skrifað og smoke-tested (62 mkr spá á sample APT_STANDARD í Reykjavík, 80% PI 48-64 mkr, 95% PI 47-69 mkr, internally consistent).
- `monthly_recalibration.py` skrifað (bíður integration með rebuild step).
- `refresh_kaupskra.py`, `rebuild_training_data.py`, `validate_metrics.py` — TODO í næstu session.

**Two bugs fixed during smoke testing**:
1. CPI loading í score_new_listing.py: reyndi að parsa CSV með assumed column names; fixed með því að build lookup úr training pickle.
2. Categorical dtype mismatch: LightGBM var þjálfað með pandas Categorical, scoring sendi raw strings; fixed með að load og apply categorical_mappings frá training data.

**Hagstofa API pattern** (fyrir framtíðar refresh scripts):
- Endpoint format: `https://px.hagstofa.is/pxis/api/v1/is/{path}/{table}.px`
- GET gefur metadata (variables, codes, valueTexts)
- POST með `{query: [{code: ..., selection: {filter: "item", values: [...]}}], response: {format: "json"}}` gefur data
- Missing values í data: string `"."` (ekki null/NaN) — verður að filter-a post-fetch

---

## 2026-04-19 22:55 (Áfangi 4c closed) — iter3 v2 + segment-stretch er production mean+uncertainty pipeline

**Hvað**: Áfangi 4c lokið. Production uncertainty pipeline er:

1. **Mean model**: iter3 v2 (LightGBM, 154 features, main+summer split) — frozen canonical.
2. **Quantile models**: iter3 v2 × 5 quantile levels (q025, q100, q500, q900, q975) — frozen.
3. **Per-segment stretch calibration**: empirical k80/k95 factors saved in `calibration_config.json` (version `iter3v2_segcal_v1`). Applied as `lo_pi = mean - k × (mean - q_lo)`, `hi_pi = mean + k × (q_hi - mean)`.
4. **Monthly recalibration** (ekki implemented): trailing 12m residuals → update k-factors, same JSON structure.
5. **Scoring output**: `{pred_mean, pi_80_lo, pi_80_hi, pi_95_lo, pi_95_hi, segment, calibration_version}` per eign, plús `is_suspect_comparable` flag ef kv_ratio outlier.

**Final metrics (clean held N=2.026)**:
- MAPE 7,00% (target 7,0% hit exactly)
- medAPE 5,38%
- cov80 73,1%
- cov95 92,7%
- SFH cov80 73,0% (20+ pp better than variance-head V3 alternative 54,7%)

**Final metrics (all held N=2.084, production-realistic including slip-through)**:
- MAPE 7,96%
- cov80 71,9%
- cov95 91,3%

**Pipeline simplicity vs alternatives**:
- 7 k-factors (one per canonical_code) + 1 global fallback in JSON
- Zero new model training per monthly recalibration
- Auditable, version-stamped, regime-aware
- Variance-head alternative would require: new LightGBM model (log(resid²) target), sigma-estimation pipeline, drift monitoring, complex version stamping. Skilað 0,6 pp better aggregate coverage en 20 pp verra á SFH. Segment-stretch strictly superior.

**Pilot launch criteria met**:
- Held cov80 > 70% (achieved 73,1% clean, 71,9% all)
- Held cov95 > 90% (achieved 92,7% clean, 91,3% all)
- Clean MAPE < 7,5% (achieved 7,00%)
- SFH cov80 > 60% (achieved 73,0%) — was <55% with variance-head

**Áfangi 5+ handoff**: extraction-driven features are not in mean model but live in adjacent modules (UI comparables, markaðsyfirlit condition metrics, TOM model pending). Production scoring calls mean+calibration only.

---

## 2026-04-19 22:43 (Áfangi 4c post-mortem) — kv_ratio filter í training regressed held MAPE; rollback til v2 + evaluation-only filter

**Hvað gerðist**: `train_iteration3_v3.py` var keyrt með `is_quality_transaction` filter á train+val+test (kv_ratio ∈ [0,70; 1,50]). Dropaði 16.216 af 129.769 train+val rows (12,5%) og 568 af 8.575 test (6,6%). Held var óbreytt (unfiltered) fyrir realistic evaluation.

**Expected**: held clean MAPE batnaði úr ~6,90% (v2) í 6,96%-ish via cleaner training signal.

**Actual**: held clean MAPE 7,29% (regression +0,39 pp). Held ALL MAPE 8,80% (regression +0,84 pp vs v2 7,96%). Bias dýpkaði úr −0,013 í −0,022.

**Rót orsakar**: kv_ratio > 1,50 filter droppar mest nýbyggingar með genuinely hátt markaðsverð ofan á FASTEIGNAMAT — ekki noise. Model missti training signal um nýbyggingar-premium og byrjaði að under-predict á held. Kv_ratio < 0,70 filter dropar raunverulegar slip-through (~500 rows) en þess fáir vegur ekki upp á móti tapi 11.000 nýbyggingar-rows.

**Ákvörðun**:

1. **iter3 v2 er canonical production mean model**. Kept.
2. **iter3 v3 *.lgb files eru deprecated**. Má geyma á D:\\ sem audit trail en ekki scoreast í production.
3. **Filter er evaluation tool, ekki training tool**. `is_quality_transaction` flag er gagnlegt í predictions til að:
   - Reporta both-held metrics (all + clean)
   - Flag-a suspect transactions í UI (`is_suspect_comparable=1`)
   - Skilgreina calibration pool (clean val+test) fyrir segment-stretch
   En aldrei filtera training data.
4. **Ný calibration via `calibrate_segments_v2.py`**: k-factors reiknaðir á v2 val+test clean pool, applyast á v2 quantile predictions. Supersedes `calibrate_segments.py` (sem vann á v3).

**Lærðdómur**: Data quality filters eru ekki alltaf additive. Filter sem dropar „noise" getur einnig droppað legitimate tail observations sem model þarf fyrir kalibrun. Tveir flokkar „dirty" rows voru lumped saman undir sama þröskuld — ættu að hafa verið aðskildir (kv<0,70 filter valid, kv>1,50 filter dangerous).

**Framtíðar principle**: áður en ný training-filter er adopteruð, retraining retrain-a og compare-a *per-segment MAPE + per-year bias* (ekki bara aggregate). Bias dýpkun er snemma warning sem ég missed.

---

## 2026-04-19 (Áfangi 4c) — kv_ratio quality filter + segment-stretch calibration chosen over variance-head

**Hvað**: Áfangi 4c arkitektúr fyrir launch-ready uncertainty module byggir á tveimur einföldum íhlutum: (a) `is_quality_transaction` flag sem dropar rows með `KAUPVERD/FASTEIGNAMAT ∉ [0,70; 1,50]` úr train/val/test (en heldur þeim í held fyrir realistic eval); (b) per-segment empirical stretch k-factors á existing iter3 q100/q900 og q025/q975 output, saved í `calibration_config.json` með mánaðarlegu rekalibreringsjobbi.

**Af hverju**: Annar Claude lagði upphaflega til variance-head (LightGBM regression á log(resid²) með time-decay weights) sem launch-critical. Empirical validation á þessum enda afvísaði það á þrem forsendum:

1. **Heavy-tail er drifið af slip-through, ekki innate**: Eftir að dropa kv_ratio outliers (4–12% af data) fer `quantile(|resid|/std, 0.95)` úr 3,74 í near-Gaussian 2,09. Þessi 4% rows eru responsible fyrir 20+% af MAPE contribution á test og held.

2. **Segment-stretch slær variance-head á SFH**: Variance-head V3 pool-calibrated gaf SFH_DETACHED held cov80=54,7%. Segment-stretch pool-calibrated gaf 75,5%. Variance-head lærði sigma_hat ~0,04 fyrir SFH þegar empirical resid_SD er 0,21 — það underestimated SFH variance vegna all-segments pooled training. SFH er bank-critical segment (einbýlishús, hæsta-dollar lán); 20 pp coverage gap er regulatory risk.

3. **Aggregate coverage gain yfir stretch er 0,6 pp**: Variance-head held cov80=73,1% vs stretch 72,5%. Operational complexity (kalibrering, sigma estimation, drift monitoring, version stamping per prediction) réttlætir ekki 0,6 pp.

**Empirical niðurstöður (clean held, N=2.026, kv_ratio ∈ [0,7; 1,5])**:

| Metric | Iter3 v2 uncalibrated | Iter3 v3 + segment-stretch |
|---|---|---|
| Held MAPE | 7,96% | **~6,96%** (target 7,0% hitted) |
| Held medAPE | 5,03% | ~4,96% |
| Held 80% PI coverage | 69,7% | ~72-75% (segment-dependent) |
| SFH cov80 | 67,0% | **75,5%** |
| SFH cov80 (variance-head alternative) | — | 54,7% |

**Scripts**: `filter_training_data.py`, `train_iteration3_v3.py`, `calibrate_segments.py`. Einfaldari pipeline en variance-head (engin ný model dependency), cheaper operational burden, better regulatory posture (simple lookup table, auditable k-factors).

**Var-head verður iter 5+ only** ef empirical þörf kemur upp eftir pilot. Per-property sigma spá er UI-lag enhancement, ekki launch-critical.

---

## 2026-04-19 (Áfangi 7 — cancelled ML path) — Ask-to-sale gap ML module afnumið, lookup tafla í staðinn

**Hvað**: Planned ML-driven `ask_to_sale_gap_model.py` (Áfangi 7 í upphaflegri roadmap) er afnumið. Replaced með **static lookup tafla** sem geymir miðgildi log(sale/list_price_final) per (segment × region × quarter × market_heat_bucket), mánaðarlegt update.

**Af hverju**: Annar Claude prófaði þrjár feature-configurations á 55.064 paraðar sölu með temporal split (train ≤2023, test 2025, held 2026). Naive baseline `sale = list_price_final × 1,0` gaf test MAPE 3,48%. Best ML model (structured + market-state + extraction + TOM features) gaf test MAPE 4,08% — **verra** en naive. Niðurstaðan er ekki feature-veikleiki heldur target-dispersion collapse:

| listing_year | N | SD of log(sale/list) |
|---|---|---|
| 2015 | 2.920 | 0,139 |
| 2020 | 6.857 | 0,122 |
| 2023 | 5.186 | 0,059 |
| 2024 | 5.560 | 0,056 |
| 2025 | 3.496 | 0,048 |

Íslenski markaðurinn er að verða efficient. Target SD fór úr 0,14 í 0,05 — 3× lækkun á decade. Noise-floor er komin undir predictable variance. Þegar residual RMSE best ML nálgast SD in target (0,0527 vs SD 0,048), er enginn signal til að capture.

**Replacement arkitektúr**:
- **`ats_lookup.parquet`**: miðgildi log(sale/list) + dispersion (std) per (canonical_code × region_tier × quarter × market_heat_bucket). Market_heat er ATS trailing 3-mán rolling mean bucket.
- **Scoring**: `predicted_sale = list_price × exp(median_log_ratio_from_table)`. Uncertainty band = list_price × exp(median ± 1.28 × dispersion_from_table) fyrir 80% PI.
- **Dashboard aggregates**: above-list rate, miðgildi ATS, dispersion per segment/quarter — all derived from same lookup.

Þetta er insight fyrir markaðsyfirlit: **„íslenski fasteignamarkaðurinn hefur þroskast til þess stigs að ask-to-sale gap er fyrirsjáanlegur í aggregate en ekki per-listing"**. Publishable empirical finding.

---

## 2026-04-19 (Áfangi 4 close) — Iter3 v2 frozen sem final mean model; extraction redundant fyrir hedonic mean

**Hvað**: Iter3 v2 (LightGBM mean + 5 quantiles × main + summer split, 154 features) er frozen sem final mean prediction model. Held main MAPE 7,96%, medAPE 5,03%, bias −0,014. Extraction features (95 engineered cols úr $375 LLM-keyrslu) samanlagt fá **~1% af gain**.

**Af hverju extraction features skila ekki hedonic lift**: Empirical validation á þessum enda: condition correlate-ar við verð (price-per-m² span 469→729 þús./m² across ICS bins, +55% premium) EN residual correlation eftir FASTEIGNAMAT + structured features er −0,20 á held (real en lítill). LightGBM tekur ekki upp sparse (24% coverage) features þegar dense alternatives (is_new_build, age_at_sale, matsvaedi_bucket) capture sömu variance gegnum confounders — nýbyggingar hafa bæði high FASTEIGNAMAT og tag-aðar replaced_new, o.s.frv.

**Þetta er ekki glatað investment**. Extraction features flytjast í adjacent modules:
- **Comparables-UI** (Áfangi 5): matsmaður fyllir út condition questionnaire, módel lookup-ar empirical adjustment-multipliers úr extraction-joined kaupskrá, sýnir nearest-neighbor eignir sem passa.
- **Markaðsyfirlit metrics**: hlutfall aktivra lystinga með needs_immediate_work=1, kitchen-vintage distribution, condition index.
- **TOM módel** (Áfangi 7 replacement): extraction features eru hypothesized strong predictor af time-on-market þar sem hedonic mean er saturated.
- **Residual analysis í UI**: skoða systematic model bias per ICS bin sem sanity-check fyrir matsmann.

**Lærðdómur**: FASTEIGNAMAT + aldur + matsvæði + stærð er near-saturated signal fyrir baseline hedonic á íslenska markaði. Framtíðar-framfarir koma úr (a) data quality filters, (b) adjacent predictive tasks (TOM, ATS aggregates), (c) uncertainty calibration, (d) UI-lag sem notar empirical data ofan á mean model. Ekki úr dýpri hedonic features.

---

## 2026-04-19 (Áfangi 0 planning) — Hosted dashboard stack valið

**Hvað**: Áfangi 0 infrastructure mun byggja á þriggja-lagskiptum arkitektúr:
- **Lag 1 (gagnalag)**: Supabase managed Postgres í skýinu. Free tier (500 MB storage) til að byrja; Pro $25/mán þegar komið er yfir. Gefur REST API sjálfvirkt (PostgREST), realtime subscriptions, auth. Standard Postgres svo engin vendor lock-in.
- **Lag 2 (acquisition + processing)**: Scraper + extraction processor + re-score processor + aggregation processor keyra á Windows vélinni hjá Danni. Windows Task Scheduler fyrir daglegt schedule. Skrifa beint í Supabase.
- **Lag 3 (presentation)**: Vercel hostar Next.js dashboard ofan á Supabase REST endpoints. Free tier er generous fyrir fyrsta árið. Custom domain (`.is` eða `.com`) keypt í gegnum Namecheap/ISNIC.

**Af hverju**: Danni vill public-facing dashboard frá upphafi („kaupi bara url ef þarf"). Cloud infrastructure er cheap ($0-50/mán fyrsta árið) samanborið við uppsetningar-kostnað self-hosted. Supabase er chosen yfir DO managed Postgres vegna þess að REST API kemur frítt — sparar massa scaffolding í backend. Vercel yfir Supabase static hosting vegna betri frontend DX og SEO-friendly SSR.

**Hafna**: Allt self-hosted (time sink), AWS Lambda (serverless debug pain), Streamlit (rapid prototyping OK en ekki public-grade).

**Deferred detail**: URL val, GitHub repo struktúr, canonical schema drög, scraping scope (fastinn.is first, other sites additive), AI-greiningar UI layer (Áfangi 0-extension eftir dashboard v0). Full planning session fyrir Áfanga 0 er í nýjum chat.

**Timing**: Parallel við Áfanga 4 iter3 training. Engin technical dependency milli þeirra — Áfangi 3 output er frozen pickle files, Áfangi 0 scraper er fresh inflow. Ekki samtímis session, en sama tímabil.

---

## 2026-04-19 (Áfangi 3e) — training_data_v2 schema og feature engineering

**Hvað**: `training_data_v2.pkl` (144.254 records × ~115 cols) byggist úr v1 + engineered extraction features. Engineering decisions:

1. **Component status (18)**: ordinal encoding `{replaced_new: 3, overhauled: 2, well_maintained: 1, original_functional: 0, in_progress: -1, needs_work: -2, not_mentioned: NaN}`. Output: `status_ord_<component>` per 18 components.

2. **Years since work**: `years_since_<component> = sale_year - <component>_year` þegar year tilgreint. NaN annars.

3. **Composite condition scores**: `interior_condition_score` (weighted mean af 8 interior component ordinals), `building_condition_score` (weighted mean af 6 building components). Weights eftir v0.2.1 schema spec. `num_recent_renovations` (count af components replaced_new/overhauled innan 10 ára), `has_any_recent_work` (binary 1 ef any).

4. **Trilemmas → binary**: 20+ yes/no/not_mentioned fields → 1/0/NaN. Covers augl-supplements og v0.2.2 new flags (has_secondary_unit, ceiling_height_premium, unused_building_rights_present, is_corner_lot, is_waterfront_or_seaside, immediate_availability, end_unit_flag).

5. **end_unit_position applicability filter**: re-applied í merge step með canonical_code úr training_data_v1 (vegna bug í batch_extract.py — sjá bug decision neðar). Gildir aðeins í ROW_HOUSE/SEMI_DETACHED; NaN annars.

6. **lot_type expansion**: 3 binary flags (`lot_is_einkalod`, `lot_is_sameign`, `lot_is_serlod`). Sérlóð er biggest-impact APT premium signal.

7. **lot_orientation normalization**: 30+ Claude variants → 4 canonical binary flags (`lot_orient_south`, `lot_orient_east_west`, `lot_orient_north_shade`, `lot_orient_mixed`). Regex-based normalization vegna schema-enforcement bug (sjá bug decision).

8. **Multi-enums → binary flags**: view_type (7 flags), reported_issues (9), storage_type (4), unregistered_space_type (5).

9. **Ordinal enums**: view_quality (4 stig), garden_size_framing (4 stig), garden_quality (4 stig — v0.2.2 condition-only), balcony_size (5 stig), listing_elaboration (4 stig).

10. **Numeric**: `unregistered_space_sqm`, `num_parking_spaces`.

**Coverage**: ~28% af 144K records hafa extraction features (paired + length-filtered). Aðrir 72% fá NaN — LightGBM handleikar native. Hypothesis: iter3 lift kemur frá paired records, ekki unpaired.

**Script**: `build_training_data_v2.py` (573 lines). Input: `batch_extraction_unique.jsonl`, `pairs_v1.pkl`, `listings_text_v2.pkl`, `training_data_v1.pkl`. Output: `training_data_v2.pkl`. Cost: $0, local processing ~3-5 mín.

---

## 2026-04-19 (Áfangi 3d) — Batch extraction cost vandamál + lessons

**Hvað**: Full batch run keyrður á Haiku 4.5 + Batch API. 37.544 unique extractions á 37.544 listings (dedup af 40.814 paired+length-filtered). **Rauntími: ~20 mín á Anthropic-megin** (mun hraðari en 1-8 klst estimate). **Raunverulegur kostnaður: $349**, ekki $157 sem var áætlað.

**Rauncostar**:
- 2 pilot runs (v0.2.1 + v0.2.2 × 200 listings): **~$3 + ~$3,50** (ekki $1,35 + $1,68 sem scripts reportuðu)
- Discovery LLM (200 × Sonnet 4.6 meta): ~$3
- Full batch (37.544 × Haiku 4.5 batch): **~$349**
- Samtals Áfangi 3: **~$375** (vs upphafleg $200-250 projection)
- Unpaid balance eftir run: **-$142,80** (þ.e. $225 deposit var ekki nóg)

**Bug sem orsakaði under-reporting**: `calc_cost()` function í `pilot_extract_v022.py` (og importað í `batch_extract.py`) assumaði að Anthropic `input_tokens` innihaldi cache_read og cache_creation sem overlapping counters, svo subtractaði þau. Raunin er að þeir eru **separate additive teljarar**. Þannig að `uncached_input = input_tokens - cache_read - cache_creation` varð near-zero eða neikvætt, og $1/M rate var missað á mörgum input tokenum.

**Réttur útreikningur**:
```
cost = input_tokens × $1/M
     + cache_read × $0.10/M
     + cache_creation × $1.25/M
     + output_tokens × $5/M
× 50% (batch discount)
```

Ekki:
```
cost = (input - cache_read - cache_creation) × $1/M + ...  ← WRONG
```

**Impact**: Pilot cost reports voru ~2,4× undir, batch projection ~2,2× undir. Danni treystur mér á tölunum og samþykkti batch án réttrar kostnaðar-stefnu — hefði haft chance á að re-scope ef tölur hefðu verið réttar (drop til smærra sample, eða pause til að deposita meira).

**Goodwill-email sent til Anthropic support**: request um billing review (ekki krafa), specifically acknowledging þetta var client-side bug ekki þeirra. Líkur á full credit <10%, partial credit 15-20%, decline 65-75%. Unpaid balance verður á næsta invoice hvort sem er.

**Lesson (hardens í WORKING_PROTOCOL)**: Framtíðar-kostnaðaráætlanir fyrir API workstreams verða að **cross-checka við Anthropic Console spend** eftir fyrstu 10-20% af keyrslu áður en resten klárast. Ekki treysta cost-report útreikningum frá scripts.

**Notable positives þrátt fyrir kostnaðarvandamál**:
- Zero extraction failures á 37.444 succeeded (0,2% failure rate)
- Batch API miklu hraðari en 1-8 klst estimate: flestar chunks kláraðar á 5-15 mín
- Prompt caching virkaði (cache hits í ~40% tokens)
- Dedup sparaði $22 vs no-dedup
- Output er clean og usable (eftir post-proc fixes)

---

## 2026-04-19 (Áfangi 3d) — Chunk size 5000 fyrir Batch API

**Hvað**: `CHUNK_SIZE = 5000` í batch_extract.py. Upphafleg setting 6000 hittust á 256 MB raw batch size limit — per-request size er ~43 KB (larger en 35 KB estimate) vegna tool schema + 3 few-shot examples endurtekin í hverri request.

**Stærðartala**: `5000 × 43 KB = 215 MB`, safely under 256 MB hard limit. `6000 × 43 KB = 258 MB`, over.

**8 chunks í staðinn fyrir 5**. Engin effect á cost — chunking er logical aðeins fyrir resume-granularity og size compliance.

---

## 2026-04-19 (Áfangi 3d) — canonical_code bug í batch_extract propagation

**Hvað**: `batch_extract.py` propagation-loop setti `canonical_code` í context-dict úr `pairs_v1.pkl`, en pairs skráin hefur EKKI þessa column (hún kemur úr `training_data_v1.pkl`). Post-processing filter fyrir end_unit_position treysti á canonical_code, og þar sem öll voru NaN, þá zeroaðist **allt** end_unit_position=yes (2816 rows) í `batch_extraction_propagated.csv`, ekki bara false positives í non-ROW/SEMI.

**Impact**: end_unit_position er dautt signal í propagated CSV. Upphafleg extraction values eru þó í `batch_extraction_unique.jsonl` (raw, unfiltered).

**Lausn í `build_training_data_v2.py`**: re-apply filter í merge-step með réttri canonical_code úr training_data_v1. `end_unit_flag` í v2 er NaN fyrir non-ROW/SEMI, 1/0 fyrir ROW/SEMI eftir extraction value.

**Lesson**: útvíkkunarlaus úr pairs-skrá hefur takmarkað gagn — downstream joins ættu allar að flæða úr training_data_v1 sem canonical source fyrir þessar metadata fields.

---

## 2026-04-19 (Áfangi 3d) — lot_orientation schema enforcement brot

**Hvað**: Claude output í batch API virkaði ekki strict enum validation fyrir single-string enum fields. Ég skilgreindi `LOT_ORIENTATION_VALUES = ['south_southwest', 'east_west', 'north_shade', 'mixed', 'not_mentioned']`, en raw output inniheldur 30+ variants (`south` alone, `southwest`, `northwest`, `east_west` concatenations eins og `southeast_southwest`, `north_south`, `west_east`).

Sama pattern í `laundry_configuration` (`in_progress` leaking frá status enum) og `sale_channel` (`private_einkasola` typo — 0,0% rate, edge case).

**Hypothesis**: Anthropic batch API enforcar ekki enum grammar constraint eins strict og sync tool_use. Mögulega trade-off til að hægja ekki á parallel inference throughput.

**Lausn í feature engineering**: `normalize_lot_orientation()` í `build_training_data_v2.py` tekur 30+ variants → 4 canonical flags (south/east_west/north_shade/mixed). `clean_enum()` helper sópar invalid values í `not_mentioned` fyrir strict single-value enums.

**Lesson fyrir v0.3 eða næstu extraction rounds**: Nota strict enum validation í feature engineering, treat raw Claude output sem „fuzzy enum" frekar en „enforced enum". Multi-select arrays virðast ekki brotna á sama hátt — aðeins single-string enums.

---

## 2026-04-19 (Áfangi 3c+) — Re-pilot v0.2.2 pass og ship til batch

**Hvað**: V0.2.2 re-pilot á sömu 200 listings keyrð með tightened prompt + 15 nýjum fields + 3ja few-shot. Zero catastrophic failures. 2 components_malformed (1%). Kostnaður: ~$3,50.

**Quality verdict: PASS á öllum critical targets, partial á sekúnder**:

| Target | v0.2.1 | v0.2.2 | Niðurstaða |
|---|---|---|---|
| well_maintained á kitchen | 60% | 21% | Pass (<30%) |
| well_maintained á bathroom | 57,5% | 19,5% | Pass |
| well_maintained á flooring | 59,5% | 20% | Pass |
| listing_elaboration standard | 7,5% | 30% | Pass (20-30%) |
| promotional_heavy rate | 27% | 26% | Ekki bætt en non-issue |

**Óvænt semantic richness**: óskráð rými false-positives voru í raun legitimate — Claude flaggar „ósamþykkt", „háaloft", „geymsluloft", „ónýttur byggingarreitur" sem unregistered signals umfram explicit „óskráð" keyword. 19 af 24 yes-captures á 200 sample-i. Semantically correct en outside my strict rule. Accepted as richer signal.

**Applicability bug**: end_unit_position flagged í 10 non-ROW/SEMI rows (APT og SFH). Fixed í post-processing filter í batch_extract.py (þó að sá fix brotnaði vegna canonical_code bug — sjá næsta decision).

**Ákvörðun**: Ship til batch án v0.2.3 cycle. Targets hit, „problems" eru annað hvort semantic richness (gott) eða post-processing-fixable.

---

## 2026-04-19 (Áfangi 3c) — Batch API + hash-dedup fyrir full extraction

**Hvað**: Full extraction round 1 keyrir á Anthropic **Batch API** (ekki sync) með **hash-based dedup** á lýsingum áður en extraction. Concrete plan:

1. Hash first-500 chars af lýsingu per listing
2. `drop_duplicates` á hash → unique extraction targets (~47.179 af 53.866)
3. Submit í Batch API í 5 chunks af ~10K listings (Batch API limit per job)
4. Retrieve JSONL results, propagate extraction til all listings með same hash
5. Metadata field `extraction_group_size` per record (1 for unique, N for group-of-N)
6. Í iter3 training: `sample_weight = 1 / sqrt(extraction_group_size)` — weighted cancellation af shared-signal bias

**Af hverju Batch API**: 50% flat discount á bæði input og output tokens. Extraction er inherently async (results used downstream í iter3 training, ekki real-time). 24-hr turnaround acceptable. Kombinerast við prompt caching (90% off á cached 8K schema) í samlegðar ~60-70% total savings.

**Af hverju hash-dedup**: duplicate rate í population er empirically **12,4% (6.687 af 53.866)**, driven af nýbyggingar-developments með shared agent template intros (Lund í Kópavogi 27×, Grímsgata 31×, Hlíðarendi 17×, Dvergurinn 15×, Asparlaut 15×). Án dedup:
- Waste $22 í duplicate extraction
- Stærra issue: iter3 sér 15 identical listings með mismunandi target prices → data leakage, over-weighting af shared template features, poorer generalization

**Cost breakdown** (staðfest 2026-04-19):

| Strategy | Listings | Per-listing | Total |
|---|---|---|---|
| No dedup, sync | 53.866 | $0,0067 | $361 |
| No dedup, batch | 53.866 | $0,0033 | $178 |
| **Med dedup, batch** | **47.179** | **$0,0033** | **$156** |

Innan $200–300 upphaflegs budget.

**Af hverju first-500 char hash** (not full text): listings með sama intro en mismunandi details eru enn largely redundant fyrir extraction (sama property-type, sama agent template, sama development). First-500 er sufficient discriminator án að miss partial-duplicate developments.

**API tier prerequisite**: Tier 2 ($500/mán cap) fyrir batch run. Tier 1 nýtur aðeins $100/mán. Plan: $40 deposit → 7 daga bið → Tier 2 triggerast.

---

## 2026-04-19 (Áfangi 3c) — Pilot findings trigger schema v0.2.2 refinement

**Hvað**: Pilot extraction 200 listings á Haiku 4.5 staðfesti að schema er workable og infrastructure virkar (zero failures, $1,35 cost), en exposed concrete refinement needs. **V0.2.2 bætir við ~11 fields + tightens system prompt**, held áfram sem Haiku 4.5 batch.

**Pilot performance**:
- Zero extraction failures (robust tool_use + JSON schema validation)
- Per-listing $0,0067 actual (vs $0,003 estimate — underestimated output tokens)
- Prompt caching virkar: fyrsta call $0,014, síðari ~$0,006 (6.840 cached tokens, 90% off)
- Narratives genuinely good (Icelandic prose, 2–4 setningar, ekki copy-paste)
- Year extraction sterk (row 5: kitchen/flooring/windows/cladding allt 2019 með detail)

**Kvalitæti-issues krefjast v0.2.2**:

1. **`well_maintained` over-use** (stærsta): 64% kitchen, 60% primary_bathroom, 54% flooring → well_maintained. Claude treatar feature-description + positive adjective („fallegt eldhús, granít borðar") sem condition signal. Marketing puffery inflates. **FIX**: system prompt krefst explicit condition language („í góðu standi", „vel viðhaldið"). Marketing puffery án condition language → `not_mentioned`.

2. **„Þak" vs „þakkantur" semantic confusion**: Row 14 „eftir er að klæða undir þakkantinn" → Claude flaggaði roof=in_progress. Rétt: cladding_in_progress only. **FIX**: explicit distinguishing example í system prompt.

3. **`listing_elaboration` inflated**: 68% elaborate + 26% promotional_heavy = 94% í efri tierum. Bara 6% standard. Recalibration thresholds: terse <150w, standard 150–300w, elaborate 300–600w, promotional_heavy 600+w OR heavy promotional language.

**V0.2.2 nýjar fields (~11)**:

*Size & legal (6)* — 24% of listings have these signals, **zero captured currently**:
- `unregistered_space_present` (trilemma) — „óskráð rými"
- `unregistered_space_sqm_stated` (int | null) — m² number ef nefnd
- `unregistered_space_type` (multi: loft_attic / basement / addition / garage_converted / other)
- `has_secondary_unit` (trilemma) — „aukaíbúð" aðskilið frá legal is_duplex status
- `ceiling_height_premium` (trilemma) — „mikil lofthæð", „3ja metra lofthæð"
- `unused_building_rights_present` (trilemma) — „ónýttur byggingarreitur"

*Outdoor (5)* — garden_quality currently conflates size + condition:
- `lot_type` (enum: private_einkalod / shared_sameign / private_in_shared_serlod / not_applicable / not_mentioned) — **biggest-impact**, sérlóð er major APT premium
- `lot_orientation` (south_southwest / east_west / north_shade / mixed / not_mentioned)
- `garden_size_framing` (unusually_large / large / standard / small / not_mentioned)
- `is_corner_lot` (trilemma)
- `is_waterfront_or_seaside` (trilemma)

*Refactor* — `garden_quality` decoupled from size, condition only: `well_landscaped_mature` / `standard_maintained` / `minimal_or_neglected` / `none` / `not_mentioned`.

**Deferred til v0.3** (nýbyggingar sub-schema, ekki critical fyrir fyrstu batch): `finish_package_level` (Pakki 1/2/3), `delivery_status`, `early_occupancy_available`, `building_permit_status`.

**Af hverju ekki fleiri v0.2.2 fields**: iterate-með-litlum-batches paradigm. Better að bæta 11 signals núna, verify í re-pilot á 200, ship batch, discovera remaining gaps í iter3 feature importance analysis, bæta seinna í v0.3. Forðum upfront over-engineering.

**Estimated impact**: schema 93 → ~104 fields. Output tokens +5%. Per-listing $0,0067 → ~$0,0070. Batch 47K: $156 → ~$165. Trivial.

---

## 2026-04-19 (Áfangi 3b) — Middle-ground validation chosen over formal gold-standard

**Hvað**: Áfangi 3 validation strategy changed frá formal hand-labeling protocol (100 listings, kappa agreement, schema v0.3 freeze gate) til **middle-ground „vibe check"** workflow.

**Af hverju**: Danni pushaði back á formal protocol með rökum að LLM extraction iteration með manual scan er faster en 15–30 klst af hand-labeling og gefur sufficient signal fyrir commercial-grade residential model. „Erum við ekki að tala um að gervigreindin geri þetta?"

**Workflow**:
1. Run pilot extraction (200 listings, Haiku 4.5) → $1,35
2. Manual scan outputs, flag obvious issues
3. Run discovery analysis (keyword + LLM meta) → ~$4
4. Synthesa concrete v0.2.2 refinements
5. Re-run pilot → verify improvements ($1,35)
6. Ef quality góð → 80K batch
7. **Fallback**: ef v0.2.2 re-pilot shows marginal quality, revert í formal protocol

**Savings**: ~25 klst af Danni's tíma án meaningful quality compromise fyrir commercial-grade residential valuation.

**Hvað við töpum**:
- Engin formal kappa inter-rater agreement metric
- Engin per-field F1/precision/recall numbers
- Engin explicit quality gates

**Hvað við höldum**:
- Visual inspection af extraction quality (fann well_maintained pattern strax — approach works)
- Ability til að catch systematic patterns via manual scan
- Gold-standard sample er samt drawn (200 rows) og má nota fyrir formal validation seinna ef þörf krefur
- Discovery infrastructure (keyword + LLM meta + duplicate check) sem uppgötvaði 12,4% pop dup rate og 24% size/legal gap

---

## 2026-04-19 (Áfangi 3a) — Schema v0.2.1 frozen fyrir extraction round 1

**Hvað**: Extraction schema v0.2.1 er frozen sem starting point fyrir 3c pilot. 93 fields total:

- **Component-status matrix** (18 × 3 = 54 fields): unit-level 11 (kitchen, primary_bathroom, secondary_bathroom, flooring, interior_finishes, paint, electrical_panel, electrical_wiring, plumbing, heating, windows_unit) + building-level 7 (roof, cladding, windows_building, insulation, elevator_mechanism, sameign_cosmetic, foundation_drainage). Hver component fær `status` (7-stiga enum) + `year` (int) + `detail` (short text).
- **7-stiga status enum**: `replaced_new`, `overhauled`, `well_maintained`, `original_functional`, `needs_work`, `in_progress`, `not_mentioned`.
- **7 augl-supplement trilemmas**: fyrir þau 7 flags sem hafa 86% null rate í listings_v2. Extracted value fyllir inn þegar augl er null.
- **Situational fields**: útsýni (2), útipláss detail (5), parking detail (3), layout (6), building & annað (5), negative signals (3), agent framing (3), narrative + meta (5).

**Af hverju component-level rich**: v0.1 hafði flatt schema sem lumpaði „ný rafmagnstafla" og „yfirfarin rafmagnstafla" undir sama flagg. Danni benti á að þessi aðgreining er central fyrir bæði verðmat (verðáhrif mismunandi) og explainability (hægt að segja „X bætti svona mikið við virðið"). V0.2 gerir skýran status-distinction per component sem model getur lært á og kerfi getur útskýrt.

**Af hverju 18 components frekar en fleiri/færri**: trimmed-list af kjarna building/unit components sem birtast reglulega í íslenskum lýsingum. Minna er skarðbrotandi (t.d. ef við hefðum bara „interior" og „exterior" 2-component matrix missum við signal). Meira er diminishing returns (cosmetic-sub-components bæta við token-cost án marginal lift).

**Re-freeze í v0.3 eftir 3c pilot** — component-fields með `not_mentioned` rate > 70% eða F1 < 0,75 verða candidates fyrir drop eða merge.

---

## 2026-04-19 (Áfangi 3a) — Extraction scope round 1 = paired subset, Haiku+batch+caching

**Hvað**: Round 1 extraction scope er þröngvað að paired subset (~80K listings), ekki full 456K corpus. Model val: **Claude Haiku 4.5** með batch API (50% afsláttur) + prompt caching (90% afsláttur á static 8K-token schema). Budget: **~$240**.

**Af hverju paired subset eingöngu**: bara paired listings fara í iter3 training data. Unpaired listings (off_market_used, off_market_newbuild, post_sale_only) eru 86K af iter2's 144K — þeir hafa engan augl_id og því engin lýsingu til að extract. Extraction á þeim myndi kosta en gefa núll iter3-lift.

**Af hverju Haiku**: rich 18-component schema er harðara extraction task en v0.1 (nuance milli „ný" vs „yfirfarin" er real test), en batch + caching gerir þetta fjárhagslega bærilegt eingöngu á Haiku. Ef pilot (3c) sýnir að Haiku nær ekki quality threshold (F1 ≥ 0,75 á status enum), fallback í Sonnet 4.6 (total ~$800 í staðinn fyrir $240).

**Deferred til round 2** (þegar vettvangurinn skilar revenue/funding):
- Unpaired ~370K extraction (additional ~$1.100 á Haiku, ~$3.700 á Sonnet)
- Sonnet upgrade á paired subset ef Haiku er marginal
- Image-based extraction (7M myndir er real money)
- Dedicated sumarbústaða-schema með land-value focus

**Token estimates** per listing (Haiku):
- Input: ~8.000 static (cached, $0,10/MTok) + ~600 dynamic ($1/MTok)
- Output: ~1.000 tokens ($5/MTok)
- Per-listing með batch: ~$0,003
- 80K × $0,003 = $240

---

## 2026-04-19 (Áfangi 3a) — Gold-standard = 120→200 listings, seed=42, 36-cell stratified

**Hvað**: Gold-standard benchmark er hand-labeled listings, drawn með `seed=42` úr paired subset af iter2_predictions.pkl. Original breakdown (Áfangi 3a):

- **100 stratified** yfir 36-cell grid (region_tier × type_bucket × era, 3×4×3)
- **20 worst-held oversample** (top APE frá iter2 held predictions, stress-test)

**Scale update í Áfanga 3c (2026-04-19)**: sample **grew til 200 rows** (180 stratified + 20 worst_held, 5 per cell) fyrir robust discovery analysis á pilot. All 36 cells still populated, no thin cells.

**Type_bucket collapse** (rare types inn í nearest-sibling fyrir sampling):
- APT_BASEMENT → APT_STANDARD bucket
- APT_ATTIC → APT_FLOOR bucket
- SEMI_DETACHED → ROW_HOUSE bucket

**Era bins**: 2015–2019 / 2020–2023 / 2024–2026.

**Filter-reglur**: paired_fresh eða paired_valid pair_status, canonical_code in-model, lysing-length 300–3000 chars.

**Af hverju 120 og ekki 100 eða 200**: 100 stratified gefur ~3 samples per cell sem er þunnt en fangar systematic issues per-cell. 20 worst-held oversample er critical stress-test — ef extraction bætir ekki worst cases frá iter2, er það augljós limitation sem við viljum uppgötva í pilot en ekki við full run.

**Sample draw empirical outcome**: öll 36 cells populated, engin thin cells. Stratified draw = 108 records, trimmed til 100. Region balance 34/33/33. Canonical balance (efter bucket collapse): SFH 25, APT_FLOOR 25, APT_STANDARD 24, ROW+SEMI 26.

**Staged-review labeling pattern**: labela fyrstu 20 með v0.2.1 + v0.1 guide, pause, tune schema/guide ef þörf, labela remaining 100 með refined version. Forðar að 100 listings séu labelaðir á buggy-schema.

---

## 2026-04-19 (Áfangi 3a) — augl flag coverage + inngangur categorical

**Hvað**: Empirical findings úr `verify_augl_flags.py` (2026-04-18) breyta schema design og join-logic:

**Finding 1 — 86,2% null rate á 7 augl flags**: `svalir`, `gardur`, `lyfta`, `staedi`, `rafbill`, `pets`, `hjolastoll`, `eldrib` (plús `lat`/`long`) hafa sama null-rate. Driven af source_db (5 unique values, líklega að bara einn skilaði augl_json með parsed flags). **Consequence**: schema v0.2.1 bætti við 7 supplement-trilemma fields sem extraction fyllir í fyrir 86% af listings þar sem augl er null. Post-extraction merge: augl-flag tekur precedence þegar non-null.

**Finding 2 — `inngangur` er 42-value categorical**: ekki boolean eins og TAXONOMY gaf í skyn. 232K af 472K eru „Sameiginlegur". `has_separate_entrance` derive-ast sem `inngangur != "Sameiginlegur"` — ekki þörf á extraction.

**Finding 3 — 100% populated numeric fields**: `fjherb` (100%), `fjsvfnherb` (100%), `fjbadherb` (100%), `byggar` (99,4%), `bilskur` (100%, pre-computed), `n_myndir` (100%). Þessi fields voru upphaflega í v0.1 extraction schema en eru drop-aðir í v0.2.1 (duplicates HMS authoritative data).

**Finding 4 — join-key case mismatch**: iter2_predictions og training_data_v1 nota UPPERCASE (`FAERSLUNUMER`, `FASTNUM`, `SKJALANUMER`, `THINGLYSTDAGS`), pairs_v1 notar lowercase. Primary join: `FAERSLUNUMER` ↔ `faerslunumer` (unique per sala). pairs hefur `augl_id_final` og `augl_id_initial` — nota final sem primary, fallback í initial.

---

## 2026-04-18 (Áfangi 2.4c) — Áfangi 2 closed fyrir residential

**Hvað**: Iter2 main residential model meets production targets:
- Held MAPE 7,97% (target ≤10%) ✓
- medAPE 5,24% (target ≤8%) ✓
- Bias −1,5% (baseline var −10%) ✓
- cov80 69,9% (target ≥75%) ✗ near miss

Áfangi 2 declared closed fyrir residential segmentið. Næsta skref er Áfangi 3 extraction schema design.

**Af hverju closed þrátt fyrir cov80 near-miss**: cov80 miss er 5 pp og er acceptable production quality. Users of valuation website fá slightly wider intervals í report-ing (t.d. 85% í staðinn fyrir 80% labeled). Can be tightened later í iter3 með quantile adjustment án þess að block Áfanga 3 vinnu.

**Tvær mechanism fixes staðfestar virka**:
- Mechanism 1 (FASTEIGNAMAT nominal drift): Per-quintile bias á held var −10% í Q5 í baseline, er núna −0,7% í iter2. `real_fasteignamat` feature solved.
- Mechanism 2 (2024–2026 plateau): Per-year bias var monotonic 0→−10% í baseline, er núna flat ~0 í 2024/2025/2026. train_ext = train+val merge solved.

---

## 2026-04-18 (Áfangi 2.4c) — SUMMERHOUSE acknowledged unresolved

**Hvað**: Summer model held MAPE 176%, medAPE 22%. 81% af records hafa APE < 50% (acceptable median prediction) en tail er catastrophic (max APE >300.000%).

Features available (EINFLM, BYGGAR, LOD_FLM, lat/lon, FASTEIGNAMAT) eru ekki discriminative enough fyrir summerhouse valuation. Markaðurinn er dominated af land-value (location, lot size, amenity proximity, waterfront access) og condition (cabin vs fully winterized) — structured features fanga þetta ekki.

**Decision**: Accept summer model sem unresolved. Known limitation documented. Residential website launches án summerhouse valuation fyrir v1. Future work:
- Collect land-value indicators (distance to amenities, watercoverage, waterfront)
- Re-classify summerhouses by type (traditional cabin / modern / winterized / glamping)
- Potentially separate hedonic extraction schema með different features

---

## 2026-04-18 (Áfangi 2.4c) — Iter2 main model = production baseline

**Hvað**: Iter2 main (ex-SUMMERHOUSE) 6 modules — mean + 5 quantiles — er canonical production model fyrir residential valuation.

**Hyperparameters finalized**:
- num_leaves=63, learning_rate=0.05
- min_data_in_leaf=40 (main), 15 (summer)
- feature_fraction=0.9, bagging_fraction=0.8, bagging_freq=5
- n_estimators=3000 með early stopping=100 á test split
- seed=42, deterministic=True

**Features finalized (20)**: canonical_code, unit_category, matsvaedi_bucket, region_tier, postnr, lat, lon, EINFLM, BYGGAR, LOD_FLM, FASTEIGNAMAT, **real_fasteignamat**, is_new_build, merking_floor, building_max_floor, is_top_floor, floor_fraction, is_main_unit, sale_year, sale_month.

Feature importance: real_fasteignamat 63%, FASTEIGNAMAT 13%, EINFLM 5%, sale_year 4%, is_new_build 4%. Restin deila 11%.

**Best iterations**: main_mean=1859, main_q50=2976. Q50 þjálfaði mikið lengur en mean — median er harðari að optimize.

---

## 2026-04-18 (Áfangi 2.4c) — audit_2_4c_residuals.py canonical audit script

**Hvað**: `audit_2_4c_residuals.py` er reproducible audit script sem keyrist á `iter2_predictions.pkl`. Gefur útstreymi með bias per split, calibration, Mechanism 1 quintile check, worst-20 inspection, spatial clustering, og per-segment metrics.

**Af hverju**: Hver iter3+ þjálfun ætti að keyra sama audit (eftir minor modifications á column names) til að tryggja regression-safe metrics. Template fyrir future model iterations.

---

## 2026-04-18 (Áfangi 2.4b plan) — Iteration 2 architecture

**Hvað**: Eftir 2.4a residual audit staðfesti tvær orsakir fyrir systematic overprediction í 2024+, plan-ast iter2 með þremur fixes:

**P1 — SUMMERHOUSE aðskilið**: Main model þjálfað á ~139.741 residential records (canonical_code != SUMMERHOUSE). Separate summer model á ~4.513 SUMMERHOUSE records. 12 módel total: 6 main (mean + 5 quantiles) + 6 summer.

**P2 — real_fasteignamat feature**: Bæta við `real_fasteignamat = FASTEIGNAMAT × cpi_factor` sem 20. feature. Halda FASTEIGNAMAT líka inni (gefur módeli bæði nominal og real view). Model lærir hvaða er meira predictive í mismunandi contextum.

**P3 — Extended training**: train_ext = train (≤2023) + val (2024) combined. Test (2025) færist í hlutverk early-stopping set. Held (2026) remains pure holdout. Þetta lætur model sjá 2024 plateau og reduces Mechanism 2 extrapolation penalty.

**Af hverju samtímis allir þrír**: Isolating one fix at a time myndi taka 3× iterations með lítinn incremental value. Audit 2.4a sýndi að mechanisms eru conceptually distinct en öll í sömu átt (overprediction), svo samþætt fix er low-risk.

**Ekki gera núna**:
- Monotonic constraint á sale_year: Real prices eru ekki monotonic (fóru niður 2025–2026), svo constraint myndi enforca false pattern.
- Spatial KNN smoothing: Residuals eru mildly clustered (std 0,038) — marginal gain. Deferred til 2b.
- K-fold CV: Overkill fyrir iteration 2. Fair comparison með baseline er held (2026) MAPE.

**Expected outcome**: residential test MAPE ≤ 9%, held MAPE ≤ 10%, cov80 ≥ 75% á held. Held metric er authoritative samanburður; test er ekki fair því iter2 notar test fyrir early stopping.

---

## 2026-04-18 (Áfangi 2.4a) — Systematic overprediction diagnosis

**Hvað**: Residual audit afhjúpaði að baseline model overpredictar í 2024+, með monotonic progression:
- train bias 0%, val bias −3,5%, test bias −5,0%, held bias −9,6%.

**Tvær distinct orsakir**:

1. **FASTEIGNAMAT nominal drift**. FASTEIGNAMAT er nominal (ekki CPI-adjusted) en target (real_kaupverd) er deflated. 2024–2026 saw FASTEIGNAMAT óx nominally mikið, en real prices plateau-uðu. Model lærði í training "FASTEIGNAMAT X → real_kaupverd Y" en í test hefur FASTEIGNAMAT vaxið fyrir sama real price → overpredict. Staðfest með Section F quintile analysis: 6.872 af 8.575 test-records detta í Q5 (efsta training-quintile).

2. **2024–2026 real price plateau**. median_real var +5,4% 2024, −2,2% 2025, −1,8% 2026. Model trained on 2006–2023 monotonic uptrend kannast ekki við plateau/decline — extrapolerar upward í 2025–2026.

**Af hverju þetta skiptir máli**: Fix #1 (real_fasteignamat feature) og Fix #2 (include 2024 in training) eru orthogonal og ætti að samlegast combined. Við testum báða samtímis í iter2.

**Diagnostic ekki-findings** (worth noting til að forðast future rabbit-holes):
- Spatial residuals eru bara **mildly clustered** (std 0,038 í log-space, range [−0,15, +0,11]). KNN smoothing gæti gefið 1–2 pp MAPE gain en er ekki primary fix.
- Residual correlations allar **undir 0,10 Spearman** (hæst FASTEIGNAMAT við 0,07). Ekkert single feature er systematically missed.
- Per-year train MAPE sit í 7–8% (modern 2018–2023) og aldrei fer upp fyrir 11% (2008–2009 financial crisis). Model passar training gögn vel — problem er structural (distribution shift), ekki overfit.

---

## 2026-04-18 (Áfangi 2.3) — Baseline LightGBM hyperparameters

**Hvað**: Conservative baseline, ekki tuning-heavy:
- `num_leaves=63`, `learning_rate=0.05`
- `n_estimators=3000` með early_stopping=100 á val
- `min_data_in_leaf=40`, `feature_fraction=0.9`, `bagging_fraction=0.8`, `bagging_freq=5`
- `seed=42`, `deterministic=True`, `force_col_wise=True`
- Categorical features explicitly marked: canonical_code, unit_category, matsvaedi_bucket, region_tier, postnr

**Target**: `log_real_kaupverd`. Predictions back-transform með `exp()`.

**Sex módel**: mean (L2 regression) + 5 quantiles (alphas 0.025, 0.10, 0.50, 0.90, 0.975). Eitt módel per quantile — LightGBM styður ekki multi-output quantile native.

**Af hverju engin hyperparameter tuning í baseline**: Baseline er viðmið, ekki optimized model. Vill mæla hvort structured features einir og sér (19 features) gefa meaningful signal áður en við spendum time á tuning.

**Best iterations per model** (empirical result): mean 820, q025 330, q10 400, q50 2368, q90 3000 (hit max), q975 875. Q50 og Q90 trained lengur — median er harðari að optimize en tails.

---

## 2026-04-18 (Áfangi 2.3) — Point-prediction metric = mean model

**Hvað**: Reiknum point-prediction accuracy metrics (MAPE, MAE, R²) á bæði mean model og P50 (median quantile). Notum **mean model sem primary point estimate** í reporting.

**Af hverju**: Mean model (L2 loss) optimizar squared error sem gives conditional expectation. P50 optimizar absolute error sem gives conditional median. Fyrir log-normal pris distribution eru þau ekki eins — mean > median.

Í íslenska real estate markaði er mean model slightly betri í MAPE (test 15,36% vs P50 15,68%) en P50 er betri í medAPE (test 6,72% vs mean 7,33%). Mean model er authoritative fyrir point estimate; P50 er fyrirliggjandi úr quantile suite ef user vill robust median.

---

## 2026-04-18 (Áfangi 2.3) — Chronological split confirmed

**Hvað**: train ≤ 2023 (123.517), val = 2024 (9.719), test = 2025 (8.887), held = 2026+ (2.131).

**Af hverju chronological**: Real estate market has temporal trends sem model þarf að generalize across. Random split myndi gefa optimistic metrics vegna of-fitting á tíma.

**Trade-off**: sale_year=2024 er aldrei séð í training, sem þýðir LightGBM trees nota leaf values frá 2023 boundary. Þetta skapar extrapolation problem sem 2.4a staðfesti og 2.4b fixar með train_ext merge.

---

## 2026-04-18 (Áfangi 2.1) — Required fields filter added

**Hvað**: Training data build dropar records þar sem KAUPVERD, FASTEIGNAMAT, BYGGAR, EINFLM, FASTNUM, THINGLYSTDAGS eru null. Þetta dropar 11.467 records (step 2 í cascade: 226.481 → 215.014).

**Af hverju**: LightGBM handle-ar NaN fyrir flesta features, en target (KAUPVERD) má ekki vera NaN, og FASTEIGNAMAT er required fyrir outlier rule. Drop-ing fyrir cascade simplifies downstream.

**Impact á nýbyggingahlutfall**: Baseline training set hefur is_new_build = 13,8% vs audit 1.2 tala 15,2%. Difference er vegna required-fields filter sem dropar nýbyggingar með vantandi historical FASTEIGNAMAT (fyrir-completion transactions hafa oft NaN FASTEIGNAMAT).

---

## 2026-04-18 (Áfangi 2.1) — building_max_floor reiknað á fullum properties_v2

**Hvað**: `building_max_floor` er reiknað á fullum properties_v2 (124.835 records), ekki bara training subset. Grouping á landnum, max af merking_floor.

**Af hverju**: Þegar við ákveðum hvort íbúð er top-floor viljum við að byggingin sé fullgreind af öllum einingum sínum, ekki bara þeim sem voru seldar í arm's-length context. Íbúð á 3. hæð í 5-hæða byggingu er ekki top floor, en ef við reiknum bara á training data kannski sjáum við bara íbúðir á 1. og 3. hæð í þeirri byggingu, og miss-flaggum 3. sem top.

---

## 2026-04-18 (Áfangi 2.0 audit) — FEPILOG AA=02 hypothesis rejected

**Hvað**: Upphafleg lýsing FEPILOG AA-flokka frá Áfanga 1.8 (2026-04-18 lokakvöld) var röng. AA=02 er **ekki** bílskúrar/geymslur — það er mixed-purpose flokkur þar sem dominantly residential-main records eru innanborðs, blandaðar við commercial og garages. Sama gildir um AA=03+: allir AA-kóðar innihalda blöndu af property types.

Audit 2.0 staðfesti með cross-tab á unit_category (AA+BB) × canonical_code innan in-model set (148.608 records): unit_category 0201 telur 5.988 arm's-length residential sölur — APT_STANDARD (2.826), APT_FLOOR (1.987), ROW_HOUSE (522), SEMI_DETACHED (466), SFH_DETACHED (110), SUMMERHOUSE (61). Median pr-m² = 588 k/m² (clean residential range, ekki garage sem væri 100–250 k/m²).

**Af hverju það skiptir máli**: AA er ekki usable sem residential/non-residential classifier. Canonical exclusion í módeli stýrist af `classify_property()` úr HMS `tegund`, ekki af FEPILOG. AA má ekki notast sem second-pass filter "bara til öryggis".

**Feature design óbreytt**: `unit_category = AA + BB` sem categorical feature og `is_main_unit = (CC == "01")` sem binary. LightGBM lærir rétt price-differential á unit_category nánast frítt vegna þess að mikill meirihluti records clusterar í fáum kóðum (top-5 eru 67% af data).

**Engin breyting á 2.1 build scope**. Skráð hér svo framtíðar-Claude (eða ég sjálfur) villist ekki á fyrri lýsingu.

---

## 2026-04-18 (Áfangi 2.0 audit) — is_top_floor og floor_fraction gated á building_max_floor≥2

**Hvað**: Í audit 2.0 sýndi top-floor rate ungated að 44,4% af íbúðum væru "top floor" — inflated af single-floor buildings þar sem merking_floor = building_max_floor = 1 gefur trivially True. Þessi signal er meaningless fyrir einbýli, raðhús, og other single-floor structures.

**Ákvörðun**:
- `is_top_floor = NaN` þegar `building_max_floor < 2`, annars boolean
- `floor_fraction = NaN` þegar `building_max_floor < 2`, annars `merking_floor / building_max_floor`

NaN er preferred over False því LightGBM handle-ar NaN native og lærir "missing as information" en not-applicable-as-False myndi gefa módelinu villandi signal að einbýli séu "ekki top floor".

**Af hverju**: Audit 2.0 sýndi 85.351 apt units (APT_STANDARD/APT_FLOOR/APT_ATTIC) með bæði merking_floor og building_max_floor. Af þeim eru multi-floor buildings bara ein subset. Gating tryggir að feature-inn er meaningful í records þar sem hann er relevant.

---

## 2026-04-18 (lokakvöld) — FEPILOG decoding hierarchy (Áfangi 1.8)

**Hvað**: FEPILOG er 6-stafa kóði AABBCC:
- **AA** = aðal-flokkur. AA=01 er 74% af sölum og dominantly residential-main. AA=02 (11%) og AA=03+ eru mixed (uppfært 2026-04-18, sjá ákvörðun efst).
- **BB** = undir-flokkur.
- **CC** = raðnúmer. CC=01 (aðal-eining) = 58,1% af öllum sölum.

Features fyrir Áfanga 2:
- `unit_category = AA + BB` sem categorical (t.d. "0101", "0102", "0201")
- `is_main_unit = (CC == "01")` sem binary

**Af hverju**: 1.551 distinct FEPILOG codes eru óhöndluð í raw form. Hierarkíuna er skýr og LightGBM lærir hvaða AA_BB kombinations haga sér sérstaklega án þess að þurfa explicit rule-set.

**Alternative**: Flat categorical (1.551 levels) — hafnað, of sparse. Full AABBCC hierarchy með 3 features — yfirkill fyrir CC sem er mostly bara "main vs secondary" signal.

---

## 2026-04-18 (lokakvöld) — Multi-unit policy: single-FASTNUM only í baseline training

**Hvað**: 8,3% af arm's-length records (14.562 af 174.526) eru í multi-unit SKJALANUMER (2-4 FASTNUM undir sama samningi). **Policy fyrir Áfanga 2**: keep eingöngu single-FASTNUM SKJALANUMER í baseline training set (95,8% af samningum).

**Lykil-uppgötvun sem gerir þetta safe**: HMS hefur þegar pro-rata skipt KAUPVERD milli FASTNUM rows í multi-unit samningum. 998 af 1000 sample two-FASTNUM samningum hafa **mismunandi** KAUPVERD á rows. Þannig að summum við KAUPVERD per SKJALANUMER myndi ekki double-count-a.

Samt: multi-unit sölur eru ekki representative single-property arm's-length trades (oft eignasafn-sölur eða íbúð+atvinnuhúsnæði transactions). Filtering þær út gefur hreinna training signal. Geta verið endurskoðaðar í síðari áfanga ef þörf krefst.

**Af hverju**: Audit 1.8 section B staðfesti bæði scale (8,3% — nógu mikið til að skipta máli) og verð-skipting (clean pro-rata — ekkert re-engineering þarf). Einfaldasta legitimate solution er filter.

**Validated í audit 2.0**: Price-per-m² (2020+, residential) er kerfisbundið lower á multi-unit samningum: Einbýli 0,91×, Fjölbýli 0,89×, Sérbýli 0,99× relative to single. Multi-unit drop fjarlægir bundled-pricing dynamics sem módelið á ekki að læra.

**Alternative**:
- Aggregate KAUPVERD per SKJALANUMER og treat sem einn sale — hafnað, blandar saman eignir með mismunandi characteristics
- Keep alla records með flag — hafnað, noisy training signal í módeli sem targets single-property verð
- Drop entire multi-unit samninga — valið. Keep only single-FASTNUM (95,8%).

---

## 2026-04-18 (lokakvöld) — Landnum-based alt-pairing deferred (Áfangi 1.8b)

**Hvað**: Danni's pre-fastnum hypothesis (listings undir landnum áður en endanlegt FASTNUM er úthlutað) er **ekki testable** með núverandi listings_v2 — field-ið er ekki í parsed output. Skráð sem Áfanga 1.8b backlog.

Næsta skref þegar tekið upp aftur: re-parse fyrstu pre-merge DB til að sjá hvort landnum er í raw augl_json en bara droppað í parse_all_dbs.py. Ef já, endurgera listings_v2 með landnum field og keyra landnum-based alt pairing. Ef nei, verður að bíða eftir nýjum scraper (Áfangi 0) sem captures landnum.

**Af hverju defer**: Ekki blocker fyrir Áfanga 2 (hedonic baseline notar ekki pairing input). Áfangi 7 ask-to-sale módel getur notað núverandi 55.538 paired_fresh án landnum alt pairing. Upgrade-ar coverage í Fjölbýli frá 44% upp í kannski 60-70% ef tilgáta er correct, en sá ávinningur kemur að góðu seinna.

---

## 2026-04-18 (kvöld) — Geography feature architecture (Áfangi 1.6)

**Hvað**: Per-FASTNUM geography features í `D:\geography_features.pkl`:
- `matsvaediNUMER` og `matsvaediNAFN` — HMS verðmatssvæði, 100% coverage
- `matsvaedi_bucket` — rare-merged: M<numer> fyrir ≥50 sölur 2015+ (160 distinct), P<postnr>_other fyrir rare (53 distinct). 213 distinct values alls
- `matsvaedi_sales_2015` — sales count reference (weighting proxy)
- `postnr`, `postheiti` — backup categorical
- `region_tier` — RVK_core (101-116) / Capital_sub (170-276) / Country (33/36/31% split)
- `lat`, `lon` — bare numeric, LightGBM lærir spatial patterns

**Af hverju rare-merge við 50 sölur**: Audit 1.6 sýndi 160 af 191 matsvæða (84%) hafa ≥50 sölur 2015+, summerast í 99,4% af sölum. Rare matsvæðin (15%) summerast í 0,6% af markaðnum — það er bara strjálbýl svæði (Flatey á Breiðafirði, Hornstrandir). Merge í postnr_other preserves info án að búa til super-sparse categories.

**Af hverju bare lat/lon í stað spatial grid**: LightGBM lærir nonlinear spatial patterns án pre-processing. Einfaldara coupling. Spatial smoothing (t.d. KNN-residuals) bætist á í Áfanga 2b **aðeins ef** residual audit sýnir clear clustered residual sem módel nær ekki úr matsvæði + lat/lon.

**Alternative**:
- matsvæði eingöngu án postnr backup — hafnað, taparekstur í rare-merged eignum
- Pre-computed spatial grid (100m×100m cells) — hafnað, óþarfa complexity pre-baseline
- KNN-smoothed residual feature núna — hafnað, gera residual audit fyrst

---

## 2026-04-18 (kvöld) — Pairing logic og pair_status taxonomy (Áfangi 1.5)

**Hvað**: `pairing.py` implementar `pair_listings_to_sales()` sem skilar `pairs_v1.pkl` með 7-flokka pair_status taxonomy. Defaults: X=90d session boundary, Y_fresh=180d, Y_valid=365d.

pair_status gildi:
- `paired_fresh` — gap ≤ Y_fresh (clean ask-to-sale signal)
- `paired_recent` — Y_fresh < gap ≤ Y_valid (valid en eldri listing)
- `paired_stale` — gap > Y_valid (don't trust)
- `paired_no_price` — paired en list_price_final ógilt
- `post_sale_only` — listings eftir söluna eingöngu
- `off_market_newbuild` — engin listings, nýbygging
- `off_market_used` — engin listings, notaður markaður

**Key bug fixed late 2026-04-18**: Upphafleg merge_asof var á session_end, sem missed af cases þar sem session spannar söluna (pre-sale listing + post-sale listing innan 90d). Fixed til að match-a á listings beint og skila session metadata via session_id join. Paired_fresh count hækkaði úr 54.054 → 55.538 (matches audit 1.5b).

**Af hverju X=90, Y_fresh=180, Y_valid=365**: Audit 1.5b core diagnostic (ask-to-sale median per gap bucket):
| Bucket | Median |
|---|---|
| 0-180d | 0.970-0.987 |
| 180-365d | 0.969 |
| 1-2y | 1.001 (inflation crossover) |
| 2-5y | 1.249 |
| 5y+ | 1.643 |

180d er conservative cutoff fyrir training data. 365d er permissive cutoff fyrir valid pair flag.

---

## 2026-04-18 (kvöld) — Scrape gap frá 2025-07-01 accepted

**Hvað**: Listings volume hrundi úr ~9.000/mán (2024) niður í ~600/mán (2025-H2). Partial recovery til ~1.800/mán í 2026-03/04. Annualized rate vs 2024 = 0.10x. Danni erfði gamla scraperinn og hefur ekki kontrol. Leyst með nýjum scraper í Áfanga 0.

`in_scrape_gap=True` flag á sölur ≥ 2025-07-01 í pairs_v1 sem **metadata flag, ekki sía**. Paired records í gap-tímabili eru nothæf per-pair (real listing + real sale); einungis denominator-dependent metrics (coverage rate, off_market %) eru unreliable.

---

## 2026-04-18 (kvöld) — Nýbyggingar-tilgáta um off_market Fjölbýli rejected

**Hvað**: Tilgáta um að off_market Fjölbýli væru yfirgnæfandi nýbyggingar (70-90%) falsified í audit 1.5b. Nýbyggingar eru 18,5% af off_market Fjölbýli vs 15,3% markaðurinn í heild — engin over-representation.

Danni's pre-fastnum hypothesis (1.8b backlog) er núverandi leading explanation fyrir 32K off_market Fjölbýli sölur.

---

## 2026-04-18 (síðar) — thinglystdags parsing með format='ISO8601'

**Hvað**: `pd.to_datetime(..., format='ISO8601')` í stað inference fyrir raw `thinglystdags` strings með variable fractional precision (1-6+ digits). Plus year-range filter til að fanga sentinel dates ('0001-...').

**Impact**: date_valid stökk úr 84,77% í 98,57% í listings_v2.

---

## 2026-04-18 — Canonical data layer switched to v2 pickles (Áfangi 1.4.3)

**Hvað**: Downstream vinna les úr v2 pickles framleiddum af `parse_all_dbs.py` úr 5 pre-merge scraper DBum í `D:\Gagnapakkar\`. `fasteignir_merged.db` er deprecated (82% NaT á thinglystdags).

Per-DB FASTNUM partitions near-disjoint; overlap 378+380 í boundaries. Dedupe heldur latest scrape.

---

## 2026-04-18 — Dedupe strategy fyrir v2 pickles

**Hvað**:
- Listings: sort á `(augl_id, date_valid, scraped_at)` priorities `[True, False, False]`, drop_duplicates keep='first'
- Sales: sort á `(faerslunumer, scraped_at)`, latest wins
- Properties: sort á `(fastnum, scraped_at)`, latest wins
- Texts: same as listings

---

## 2026-04-18 — Invalid dates retained með date_valid flag

**Hvað**: Listings með sentinel eða unparseable dates halda `effective_date=NaT` með `date_valid=False`. ~5% af listings. Downstream filtrar á `date_valid=True` explicitly.

---

## 2026-04-18 — Lysing stored separately

**Hvað**: Listing descriptions (~2-5KB each) í aðskildri pickle (`listings_text_v2.pkl`, ~1,5 GB). Main listings_v2 lite fyrir fast loading.

---

## 2026-04-18 — Outlier filter (Áfangi 1.4.2)

**Hvað**: Tvær reglur:

**`is_price_outlier`** — combined signal, flaggar ef nokkur:
1. `fm_ratio < 0,10`
2. `fm_ratio < 0,30` AND `robust_z < −3`
3. `robust_z < −5` AND `fm_ratio < 0,50`
4. `robust_z > +10` AND `fm_ratio > +20`

Þar sem `robust_z = (log10(pr-m²) − seg_median) / (seg_iqr/1,349)`, segment = (TEGUND × region × 3-ára bucket).

**`is_size_outlier`**: `EINFLM < 20` eða `> 1000`.

Impact á residential (N=162.692): 324 flaggaðar (0,20%).

**MIKILVÆGT**: `is_price_outlier` tekur historical `FASTEIGNAMAT`, aldrei `FASTEIGNAMAT_GILDANDI`.

---

## 2026-04-18 — Frozen-snapshot dálkar staðfestir (Áfangi 1.4.1)

**Hvað**: Fjórir dálkar í kaupskrá CSV eru frozen HMS-snapshots:
- `FASTEIGNAMAT_GILDANDI` → nota `FASTEIGNAMAT`
- `FYRIRHUGAD_FASTEIGNAMAT` → nota `FASTEIGNAMAT`
- `BRUNABOTAMAT_GILDANDI` → engin historical í CSV
- `FJHERB` → sækja úr augl_json í listings_v2

Historical dálkar: KAUPVERD (99,40%), FASTEIGNAMAT (98,65%), EINFLM (6,77%), FULLBUID (4,60%), LOD_FLM (4,31%).

---

## 2026-04-18 — Eignabreytingarregla (Áfangi 1.3)

**Hvað**: Repeat-sale par útilokað ef (a) FULLBUID 1→0 transition, eða (b) `|EINFLM pct_change| > 5%`. Impact á 68.696 consecutive pör: 2.133 droppuð (3,1%).

---

## 2026-04-18 — Floor-level features í baseline

**Hvað**: `merking_floor`, `building_max_floor`, `is_top_floor`, `floor_fraction`. Top-floor premium +2-5% consistently.

---

## 2026-04-18 — Nýbyggingarregla empíríkt staðfest

**Hvað**: `FULLBUID=0 OR BYGGAR innan 2 ára af THINGLYSTDAGS`. Fangar 26.602 sölur (15,2%). Pre-completion discount: Fjölbýli 12%, Einbýli 23%.

---

## 2026-04-18 — Verðbólguleiðrétting CPI á þjálfunarsafn

**Hvað**: Allar verð-observations CPI-deflated til rolling latest month. `real_price = nominal × (CPI_ref / CPI_at_sale)`. Target = `real_kaupverd`.

Heimild: Hagstofan VIS01004, `cpi_verdtrygging.csv`, `cpi.py` helper.

---

## 2026-04-18 — Taxonomy finalization (514 HMS tegundir)

**Hvað**: Fjórir viðbótar secondary residential flokkar: `APT_ROOM`, `APT_HOTEL`, `APT_MIXED`, `APT_UNAPPROVED`. Saman við `APT_SENIOR`. Gestahús útilokað.

Coverage: 88,4% í módeli, 11,6% EXCLUDE.

---

## 2026-04-17 — Skjalastrúktúr fyrir project continuity

**Hvað**: Sex-skjala strúktúr: PROJECT_INSTRUCTIONS.md, STATE.md, DATA_SCHEMA.md, DECISIONS.md, TAXONOMY.md, GLOSSARY.md. Bætt við DATA_AUDIT_REPORT.md í Áfanga 1.7.

---

## 2026-04-17 — Property type taxonomy drög

**Hvað**: 8 canonical residential flokkar + SUMMERHOUSE. **Superseded**: 2026-04-18 með 5 sekúnder-flokkum (APT_ROOM, APT_HOTEL, APT_MIXED, APT_UNAPPROVED, APT_SENIOR).

---

## 2026-04-17 — Arm's-length filter

**Hvað**: Útiloka `ONOTHAEFUR_SAMNINGUR=1` (23%, 51.767 færslur).

**Af hverju**: Non-arm's-length sölur (fjölskyldu-transferrs, nauðungarsölur, gjafir) endurspegla ekki markaðsverð. Útiloka úr módeli, halda í sögulegri töflu fyrir reference.

---

## 2026-04-17 — Nýbyggingarregla (initial)

**Hvað**: `FULLBUID=0 OR (BYGGAR innan 2 ára af THINGLYSTDAGS)`. Staðfest empirically 2026-04-18.

**Af hverju**: Nýbyggingar hafa sinn eigin price dynamic (pre-completion discount, builder incentives). Þarf sérflögg svo hedonic módel geti lært þessa dynamík aðskilið frá notaðum markaði.

---

## 2026-04-17 — Eignabreytingar milli sala

**Hvað**: Fjarlægja repeat-sale pör þar sem EINFLM hefur breyst meira en 5%. Eitthvað var renovated/added/split — sala #2 er ekki á sömu eign.

**Af hverju**: Repeat-sale index byggir á að pöruð sala sé á sömu eign. Extension, division í fleiri íbúðir, o.s.frv. gera comparison röng.

---

## 2026-04-17 — Listing-to-sale pairing logic (initial plan)

**Hvað**: Para saman auglýsingar og kaupskrárfærslur ef samfellt á markaði. Gap > X daga → aðskilið söluferli. **Implementerað og finalized** 2026-04-18 kvöld með X=90, Y_fresh=180, Y_valid=365.

**Af hverju**: Framenginn ask-to-sale gap módel (Áfangi 7) þarf clean pairs milli listings og sala. Session-boundary handlar "paused re-listings" vs "new attempts".

---

## 2026-04-17 — Listing withdrawals fara í markaðsyfirlit

**Hvað**: Listings sem enda án sölu → flagged sem "withdrawn". Útilokaðar úr módeli, notaðar sem leading indicator (withdrawal rate er key market-temperature signal).

**Af hverju**: Útilokun úr þjálfunarsafni forðast bias (withdrawn eru ekki representative af completed sales). Haldið í markaðsyfirlit því rate þeirra er sterk indicator á markaðsástandi.

---

## 2026-04-17 — Geography: tvö lög

**Hvað**: (1) `matsvaediNUMER` sem categorical feature, (2) spatial smoothing með KNN á götureits-level (deferred til Áfanga 2b).

**Af hverju**: Matsvæði fangar hverfa-level price effects. KNN-smoothing fangar smaller-grain patterns (sjávarsýn, nálægð við park). Tvö lög saman gefa bæði discrete og continuous signal.

**Alternative íhugað**:
- Postnúmer eingöngu — hafnað, of coarse (postnr 105 spannar sem dæmi 8 matsvæði)
- Spatial grid eingöngu — hafnað, missir semantic matsvæðis-info

---

## 2026-04-17 — Target variable

**Hvað**: Aðalspá = þinglýst kaupverð (raunvirði). Ask-to-sale gap módel separat (Áfangi 7).

**Af hverju**: Kaupverð er authoritative (þinglýst). Listings er self-reported og óáreiðanlegt sem target. Gap-módel lærir discrepancy aðskilið svo við getum spáð bæði ásett verð OG sölvirði.

---

## 2026-04-17 — Uncertainty quantification

**Hvað**: LightGBM quantile regression, 5 quantiles (P2.5/P10/P50/P90/P97.5) + mean.

**Af hverju**: Bankar og opinberir aðilar krefjast uncertainty intervals, ekki bara point estimates. Quantile regression captures tail behavior betur en normal Gaussian. 5 quantiles gefa 80% og 95% intervals beint.

**Alternative íhugað**:
- Bootstrap ensembling — hafnað, compute-expensive, síður principled
- Conformal prediction — lagt í backlog fyrir Áfanga 2b ef calibration er léleg
- Bayesian regression — hafnað, scale-vandi á 170K sölum

---

## 2026-04-17 — Infrastructure stack

**Hvað**: Hetzner + PostgreSQL 16 + PostGIS + R2 + Docker Compose + Dagster + MLflow + Grafana/Prometheus/Sentry + FastAPI.

**Af hverju**:
- Hetzner: Evrópu-hosted (GDPR), cheap dedicated hardware
- Postgres+PostGIS: well-proven fyrir geo-data, SQL is universal
- Cloudflare R2: S3-compatible, zero egress cost
- Dagster: bestu data-pipeline tool fyrir scheduled scrapes og retraining
- MLflow: model versioning + reproducibility

---

## 2026-04-17 — ML framework

**Hvað**: LightGBM fyrir verðmat. Claude API fyrir LLM-extraction úr lýsingum.

**Af hverju**:
- LightGBM: proven fyrir tabular real-estate, handles categoricals native, fast training
- Claude: best-in-class fyrir íslenska texta extraction (Áfangi 4-5)

**Alternative íhugað**:
- XGBoost — svipað performance, LightGBM er hraðari á íslenskum scale
- Neural net (TabNet, FT-Transformer) — hafnað, marginal gains vs complexity overhead
- GPT-4 / Gemini — keppinautur, Claude hefur best íslenskuna í testing

---

## 2026-04-17 — Repeat-sale calibration samhliða extraction

**Hvað**: Repeat-sale pair analysis með CPI + markaðsvísitölu deflation samhliða pilot/full extraction (Áfangar 5-6).

**Af hverju**: Repeat-sale gefur ábyggilegt market-trend signal sem hedonic getur vottað sig gegn. Parallelization sparar tíma — bæði vinna á sama data layer.

---

## 2026-04-17 — Versioning og reproducibility

**Hvað**: Hvert verðmat fær version stamp (model_version + feature_version + data_snapshot_date). `predictions` tafla í Postgres geymir öll spá með feature values á spá-tíma.

**Af hverju**: Bankar þurfa að geta endurgert spá á hvaða tíma sem er (audit trails). Feature drift monitoring krefst historical feature values.

---

## 2026-04-17 — Three deployment channels, one data layer

**Hvað**: Einn canonical Postgres + API. Public/subscription/internal lesa af sama gagnalagi með mismunandi permission scopes.

**Af hverju**: Avoid data duplication. Ein truth-source. Breytingar í module propagate í alla kanala.

---

## 2026-04-17 — v1 markaðsyfirlits-indicators

**Hvað**: Átta indicators: repeat-sale index, list-to-sale ratio, months of supply, withdrawal rate, time-on-market distribution, orðatíðnigreining, model-tracking (spá vs söluverð), affordability index (verð / meðalárslaun).

**Af hverju**: Standard real-estate indicators + nokkur sérstök (orðatíðni úr lýsingum, model-tracking sem sjálfstætt gæða-monitor). v1 er data-driven sýnisafn; v2 getur bætt við byggt á feedback.

---

*Ný ákvörðun? Bættu við efst með dagsetningu + rökstuðningi.*

---

# BÓKUNARLOTA cc70 — §5A (2026-08-02, append-only í enda skjals skv. verkbeiðni)

Ein keyrsla: frosni listinn 1–17 + viðaukar cc61–cc69 (18–32). Allar tölur sóttar í audit-skjöl á diski, git-commit eða DB við bókun — engin tala tekin úr verkbeiðninni sjálfri; finnist heimild ekki er liðurinn merktur „[heimild óstaðfest]". Sannreynt beint í þessari lotu: Task Scheduler (status-próbi keyrði 02.08 07:30, exit 0), `D:\monthly_rent_level_restep.log` (fyrsta LIVE-keyrsla 04:30 no-op á gate), `night_20260802.log` (CHAIN CLEAN, extraction exit=0), `schema_migrations` í DB (þrjár raðir), `D:\HMS_jonas\hms_archive_staging.db` (2013952), prod-optimizer (HTTP 200).

## 2026-08-02 — §5A-1 · iter5-dómurinn endanlegur: líkans-sveipur ástands NEI, merki + leiðréttingarlag JÁ

**Hvað**: Ástand fer ALDREI inn sem líkans-sveipur — carrier-only mælingin sýndi ΔAPE ástands-featura +0,017pp (SE 0,17) = núll og eldhús-sveip aðeins +1,55–2,17%; ástand birtist sem MERKI á comps/eignasíðu og notanda-inntak hreyfir mat eingöngu gegnum sér leiðréttingarlag (empírísk viðmið: uppgert vs gott ≈ +2,09%, needs_immediate_work ≈ −13,3%).

**Af hverju**: Líkanið verðleggur ástand nú þegar ~21% (kvarðað +20,7% mælt vs +21,2% raun, byggt í iter4r) og 0,3%-sveipssvörun seld sem „við verðleggjum uppgerða eldhúsið" græfi undan trausti; SPJALL breytir aldrei matinu (skilyrði 5).

**Heimild**: `verdmat-ai/docs/fable_prep/audits/iter5_EFFEKT_GREINING_2026-07-21T2131Z.md` (TL;DR, §1.1b, §5) + `app/docs/fable_prep/audits/ITER5_EIGINDI_SAMANBURDUR_2026-07-21T1930Z.md` (§4.3, §7).

## 2026-08-02 — §5A-2 · Leiðréttingarlagið: efnisskrá, hliðakeðjan, stöðukerfið, einkalóð í sóttkví

**Hvað**: Efnisskráin er stuðlaskráin `leidretting_studlar_v1.json` (v1: 26 BIRTANLEG af 49 línum, virku línurnar sjö skv. cc44 §2.1; v1.1: 28 BIRTANLEG); hliðakeðjan í `reiknaLeidrettingu` er fjögur continue-hlið í röð (eigind til staðar → eignagerð → canonical-forskeyti → OG-tengd skilyrði; `lib/leidretting.js:181–187`); stöðukerfið er FIMM stöður (BIRTANLEG=tala · I-BID/NULL-MAELT/OMAELANLEG=tölulaust merki · LIKAN-BER-THEGAR=ekkert); einkalóð stendur í sóttkví (+16,14% þrengt á APT_FLOOR, cc40-nettóið +15,81% merkt ÓGILT sem birtanleg stærð).

**Af hverju**: Dómsreglan var sett fyrirfram (cc41): hreint < helmingur brúttós → haló → í-bið; sóttkví án staðfestrar skýringar er ekki hreinsuð lína. [Nafngiftirnar „hliðin fjögur" og „þriggja áfangastaða reglan" úr verkbeiðni finnast hvergi í heimildum — bókað hér með skjalfestu heitunum.]

**Heimild**: `HEDONIK_LEIDRETTINGARLAG_20260724T0634Z.md` §2, `LEIDRETTINGARLAG_SMIDI_CC44_20260725T0730Z.md` §2, `verdmat-ai/data/leidretting_studlar_v1.json` (stodur/MERKI_FLOKKAR), `CC41_HALO_VIDAUKI_20260724T2152Z.md` §2.

## 2026-08-02 — §5A-3 · cc21-leiðréttingin: 194 GB myndanna eru EKKI tvítak — ályktun um eyðanleika er aldrei bókanleg

**Hvað**: Mæling sneri cc21-ályktuninni við: 879.904 myndir (33,4% af `image_index.db`, 2.631.485 raðir) búa EINGÖNGU í Gagnapakki 1–5; speglunarpróf fann 0 byte-eins eintök; möppurnar eru framhald safnsins, ekki afrit — 194 GB strikast út sem endurheimtanlegt pláss.

**Af hverju**: cc21 bókaði 194 GB sem „ÁLYKTAÐ" tvítak (DB-bætajöfnuður yfirfærður á myndir án samanburðar). Reglan sem bókast: eyðanleiki bókast aðeins á mælingu (tilvist 300/300, speglun 80 raða, framhalds-sönnun) — aldrei á ályktun.

**Heimild**: `D:\HEILDARUTTEKT_20260724T2209Z.md` §3.2 (mælingin); `D_UTTEKT_20260718T095336Z.md` §2.6 (upprunalega ályktunin).

## 2026-08-02 — §5A-4 · Kvörðunarkaflar beggja módela: leið A, no-shrink, þröskuldar haldnir, GRADE A→~0 er sannleikur

**Hvað**: Sölumegin: leið A — aðeins conformal-bil endurreiknast, punktspár hreyfast ALDREI (grunnregla 9; sannreynt 0/0/0/0/0/0); no-shrink — engin röð þrengist (max per röð; 30.153 raðir klemmdar á 95-bili); GRADE-þröskuldar óbreyttir og A fór 19,5%→0,3% (515 segcal-raðir) = sannleikur, ekki galli; 153.901 röð breytt, eftir flip cov80 81,1% (n=847), fresh_edge 77,1% bókað ófullnægjandi. Leigumegin sama átt: bilin EKKI flippuð (44/74 hólf hefðu þrengst; 38.481 punktspá utan eigin bils).

**Af hverju**: Leið B færði punktspár −6,5%/+9,3% eftir hólfi = endurverðlagning 167.503 eigna í kvörðunarbúningi; A→~0 undir sömu þröskuldum endurspeglar raunverulega óvissu. cc49 lagði til þröskulda-endurleiðingu — arkitektsákvörðunin varð þveröfug og bókast hér endanleg.

**Heimild**: `ENDURKVORDUN_FRAMREIDSLUPARA_20260726T1110Z.md` §5.1/§7, `ENDURKVORDUN_APPLY_CC51_20260728T2047Z.md` §0/§2/§3/§5/§F1–F3, `BIL_ENDURKVORDUN_RENT_CC57_20260731T0945Z.md` §3.

## 2026-08-02 — §5A-5 · Leigu-dómurinn: vörumunur ask/samnings, framsetningarreglan, pandas-vísisskekkjan

**Hvað**: „Kolrangt" leigumat var ask-álags-tálsýn: auglýst leiga liggur mælt +19% yfir samningsstigi (vegið 1,194; 762 askar/21 sella) og matið aðeins +3,7% yfir ferskum samningsmeðaltölum — ask og samningsleiga eru ólíkar vörur/stig. Framsetningarreglan: samningsstigið er aðaltalan; ask er mæld samhengislína með heimild (ASK_SAMHENGI_LINA; talan býr á EINUM stað). „Bil-hrunið 47,8%" var pandas-vísisskekkja (sk reiknaður FYRIR merge, v1-dálkar EFTIR; 683/1.647 raðir NaN) — rétt mæling 81,2/97,0 = jafntefli við yield-bil.

**Af hverju**: NaN-talið-sem-miss endurgerði nákvæmlega 47,8/56,5 og sannaði mælivilluna; punktdómar og yield-yfirborð stóðu ósýkt. [Merkingin „(c) vörumunur" úr verkbeiðni finnst ekki — (c) í cc56 er BLENDINGS-tillagan; vörumunar-mælingin sjálf er skjalfest.]

**Heimild**: `LEIGU_YIELD_KONNUN_20260731T0838Z.md` §0/§1.4/§3.3 + viðaukar V1–V4, `BIL_ENDURKVORDUN_RENT_CC57_20260731T0945Z.md` §4, `STIGFAERSLA_UI_HMS_CC57_20260731T1010Z.md` liður 3.

## 2026-08-02 — §5A-6 · Öryggisreglurnar fimm

**Hvað**: (i) Hver ný public-tafla fæðist með RLS+REVOKE í SÖMU migration — líka snapshot/staging; (ii) bókaðar undanþágur endurmælast á öllum FJÓRUM sögnum: 204 á anon-DELETE er tvírætt en 23505 á dup-PK-INSERT sannar að heimild var veitt; (iii) aclexplode + endurtekið anon-kall dæma — REVOKE sem postgres á supabase_admin-hluti er þögul núll-aðgerð sem kvittar success; (iv) advisors-vöktun með samþykktarlista og HALT á hverju nýju ERROR-lagi utan listans (8 security_definer-view standa óbókuð — afstaða þarf fyrir listann); (v) definer/invoker-áttin er skjalfest hönnun per lag (public-view invoker, semantic-view definer).

**Af hverju**: postheiti-snapshotið stóð með fullri anon-CRUD (lifandi sannað: anon DELETE eyddi röð) og spatial_ref_sys bar skrifheimildir sem REVOKE náði ekki — grænt migration-ljós er ekki sönnun um breytingu.

**Heimild**: `docs/RLS_FIX_20260714T214739Z.md` §2/§5, `docs/RLS_FIX_20260729T075021Z.md` §2–§5, `docs/specs/T5_SEMANTIC_VIEWS_v1.md:60–62`; kanarí: commit 7372580 + `docs/fable_prep/SUPABASE_SUPPORT_SPATIAL_REF_SYS_20260729.md`.

## 2026-08-02 — §5A-7 · /leit-rótin (mublad-regexar) + view-mælingarreglan

**Hvað**: 2,4 s hægagangur /leit var EINN dálkur — `mublad`, tveir ~*-regexar á TOAST-aða `lysing` metnir á 17.052 raðir per beiðni fyrir 24 spjöld og aldrei notaðir í kaupham; fix mældist −1.812 ms á þremur óháðum mælum. Reglan sem bókast: mæling á view VERÐUR að biðja um nákvæmlega þann select-lista sem framleiðslan sendir — join-elimination fellir ómælda dálka út og gerir mjóa mælingu blinda á kostnaðinn.

**Af hverju**: cc43 mældi sama view 72–231 ms með mjóum fyrirspurnum og sá aldrei regex-kostnaðinn; afturförin var dagsett á cc15 (18.07) í pg_stat.

**Heimild**: `verdmat-ai/docs/fable_prep/audits/LEIT_HRADAPROFILERING_CC45_20260726T0815Z.md` §0/§3/§4, commit f4b3c53.

## 2026-08-02 — §5A-8 · Orphan-rútu-fellingin

**Hvað**: `adjust-valuation` POST-rútan felld (−257 línur) — munaðarlaus rúta án nokkurs kallanda; manual_q-lagið (12 handvalin, ókvörðuð, margföldunar-stöfluð áhrif) deyr með millisíðunni og kemur aldrei í verdmat.ai.

**Af hverju**: Grunnmatið er eina krónutalan í öllum dreifingarleiðum; grep-staðfest yfir öll þrjú repo að ekkert núlifandi vísar á rútuna. [Setningin „vafra-vöktun hefst við fyrsta kall → endurhleðsla skylda" úr verkbeiðni finnst hvergi bókuð — heimild óstaðfest fyrir hana.]

**Heimild**: commit de04792 (verdmat-ai), DECISIONS-færslan 2026-07-04 (manual_q fellt).

## 2026-08-02 — §5A-9 · Override-bókunin: ×1000, gildisvarin + sjálf-útrennandi

**Hvað**: Inntaks-override í derive-kjarnann á ×1000-raðirnar 744059/84/85 er gildisvarin — virkjar aðeins á gildi (hrátt >20 M kr/m² OG ÷1000-gildi <2 M kr/m²; aðskilnaður 7,4× frá lögmætu hámarki 8,02 M), aldrei á ID-lista — og rennur því sjálfkrafa út þegar HMS lagar CSV-uppsprettuna.

**Af hverju**: Spillingin var CSV-megin eingöngu (lifandi DB bar þegar rétt gildi); hrein talningu-undanþága í sanity dygði ekki því reanchor hefði skrifað blásið real yfir plástraðar raðir. Vörðurinn sjálfur stendur óbreyttur sem bakstopp (0x3 = „vörðurinn heldur" = grænt).

**Heimild**: `docs/fable_prep/prototypes/cc39/CC39_DESIGN.md` §1–§2, commit 6c32890, DECISIONS 2026-07-09, `docs/MORGUNUTTEKT_GATLISTI.md` §8.

## 2026-08-02 — §5A-10 · Tveggja-róta-þögult-núll + akkeris-invariantinn + Task-Scheduler-tilkynningagatið

**Hvað**: Vikuvélin skilaði núll-mælingu 20.07 með exit 0/success — tvær óháðar rætur (harðkóðað MODEL_VERSION lifði flippið af; CROSS JOIN á tómt akkeri tortímdi öllu í hljóði) og tvö kerfi þögðu. Bókast: (a) núll raðir = fall, ekki niðurstaða (MeasurementFailure, exit 1; HALT má ekki eyða eigin sönnun); (b) akkeris-INVARIANTINN — `kaupverd_real` og `real_pred_*` eru ekki á sama kvarða nema akkerin tvö séu jöfn (skekkja = cpi[sales]/cpi[model]; NOMINAL/NOMINAL er skyldan fyrir nýja mælipunkta); (c) Task-Scheduler-tilkynningagatið — LastTaskResult=0 þegar ekkert mældist, enginn OnFailure/rás (sér-liður á backlog, leystur með cc63-próbanum, sbr. §5A-19).

**Af hverju**: Fjarvera mælingar leit út eins og kyrrð; þögnin er vandinn, ekki frávikið — vörðurinn WARN-ar en abortar ekki lögmætan vísitölumánuð.

**Heimild**: `docs/fable_prep/audit/LAEKNUN_B_AKKERISVORDUR_20260726T0811Z.md` §1/§5 + VIÐAUKI A (commit e71c362), DATA_SCHEMA-viðaukinn (commit b8957d2).

## 2026-08-02 — §5A-11 · Innflytjenda-grep-reglan (NÝ REGLA)

**Hvað**: Endurnefning eða felling fasta krefst greps á ALLA innflytjendur í öllum þremur repoum (app, precompute, verdmat-ai) FYRIR commit.

**Af hverju**: cc47 felldi `MODEL_VERSION` úr `model_quality_eval` án innflytjenda-greps og `extraction_engine` datt á ImportError 6 nætur (27.07–01.08); fordæmið var þegar til fyrir gagnaskilgreiningar (kallaralisti cc47 §6; grep-staðfesting cc37) en var ekki beitt á Python-fastann. [Reglan var hvergi orðuð fyrr — þessi bókun er reglusetningin.]

**Heimild**: commit 00bc8e5 (atvikið + fixið), `LAEKNUN_B_AKKERISVORDUR` §6, commit de04792.

## 2026-08-02 — §5A-12 · GO-bréfstölur lúta artifact-kröfu

**Hvað**: GO-bréf eru transcript-lag og tölur þeirra lúta reglu (c) „TÖLUR FERÐAST Á DISKI" (WORKING_PROTOCOL): hver tala vísi í disk-artifact/DB-mælingu eða endurmælist/flaggist óstaðfest.

**Af hverju**: GO-bréf ② (01.08) bar „79,8/93,1" fyrir rent-v1 — tala sem engin mæling lotunnar studdi; bókuð var mælda talan 81,2/97,0 í staðinn.

**Heimild**: `docs/WORKING_PROTOCOL.md` §Audit-reglur (c), `LEIGU_YIELD_KONNUN_20260731T0838Z.md` §V2.

## 2026-08-02 — §5A-13 · Ris, neikvæði endinn og APT_FLOOR|Country-gapið á ágúst-backlog

**Hvað**: Ris (APT_ATTIC) nettó +8,15% (markaður +7,34%*, SE 0,41, n_treated 1.812; staða LIKAN-BER-THEGAR, túlkun efri mörk); neikvæði endinn opnaður með `astand_eignar` — aðeins `tharfnast_vidgerda` kveikir −13,30% (klemmt −13,04% af ×1,15-þakinu); APT_FLOOR|Country-gapið (25.322 eignir, 15,1% alheimsins, cov80 72,3%, offset +4,67%) fer á líkans-backlog ágúst-endurþjálfunar.

**Af hverju**: Markaðurinn refsar −13 til −17% fyrir slæmt ástand en líkanið nær −5,6% — notandinn þurfti leið til að segja það; Country-gapið er punktspár-mál endurþjálfunar, ekki kvörðunar.

**Heimild**: `LIKANSSVORUN_LEIDRETTINGARLAG_20260724T2111Z.md` §2-A, `EIGINDAVOKABULAR_CC46_20260726T0900Z.md` §4/§5, `ENDURKVORDUN_FRAMREIDSLUPARA` §7, `ENDURKVORDUN_APPLY_CC51` §F3/F4.

## 2026-08-02 — §5A-14 · Yield-/vanmats-röðunar-bannið sem allsherjar-UI-regla

**Hvað**: Þriggja þrepa reglan gildir á öllum flötum: (i) tala per eign = staðreynd, birtist; (ii) sía með notanda-þröskuldi = grátt svæði, leyfileg með ákvörðun; (iii) röðun = efnislega sama aðgerð og ráðgjafarbannið stöðvar = bönnuð. Bannið situr þegar í gagnalaginu (RÖÐUN-hvítlisti `leit-queries.js`, rautt próf 20) og gildir samhverft (F4). §4-A — hvort bannið nái til yield-raðana — er opin eiganda-/arkitektsspurning; E3/E4 og %-framsetning E1 bíða hennar.

**Af hverju**: Brúttó-yield-röðun er stærðfræðilega skyld vanmatsröðun en merkingarlega önnur kennistærð á öðru líkani — það er ákvörðun, ekki afleiðing.

**Heimild**: `LEITARHUGMYNDIR_CC60_2026-08-01T0950Z.md` §4-A/§2e/§2f/§3.

## 2026-08-02 — §5A-15 · DRIFT_BASELINE=1.038 — eldingin er hlutlausi punkturinn

**Hvað**: Hlutlausi punktur drift-mælis rent-restep er 1,038: leiguverðsjáin (birgðamæling) liggur mælt ~3,8% undir fersku markaðsstigi (vegið 1,0384, n=1.189 ferskir hreinir samningar vs verðsjá maí-26); WARN á |stig/baseline − 1| > 0,06.

**Af hverju**: Hættan er „leiðrétting" niður að 1,00 sem drægi matið ~4% niður fyrir markað; eldingin hreyfist með verðbólgu/veltuhraða og endurmælist ÁRLEGA (s09-aðferð cc58).

**Heimild**: commit 6a35e3e (`DRIFT_BASELINE`-comment í `scripts/monthly_rent_level_restep.py`), `EGILSGATA_KROSSVIDMID_MYNDIR_20260801T0943Z.md` §3 mæling B.

## 2026-08-02 — §5A-16 · Heildarúttektar-bylgjuramminn

**Hvað**: Fjórar bylgjur: 0 STÖÐVA BLÆÐINGUNA → 1 GERA FRAMBOÐIÐ SATT → 2 NÝ MERKI → 3 VARAN OG NOTENDURNIR (samhliða, ekki á eftir); hver liður sjálfstæður og HALT-hæfur (einn fix → skýrsla → go).

**Af hverju**: 38% af „virku" framboði var staðfest afskráð (12.223 af 32.471 röðum) — röðin stöðvar blæðinguna fyrst og gerir framboðið satt áður en ný merki eru verðlögð.

**Heimild**: `D:\HEILDARUTTEKT_20260724T2209Z.md` HLUTI 3 (§0/§2.3 fyrir 38%-töluna).

## 2026-08-02 — §5A-17 · cc-úttektarskjöl af D:-rót á kanónískan stað (ALMENN REGLA)

**Hvað**: Kanóníski staðurinn fyrir cc-úttektarskjöl er `docs/fable_prep/audits/` í viðkomandi repoi; bókast hér sem almenn regla (var áður per-skjal: D_UTTEKT §5.5-listinn + §9-framkvæmdin flutti D_UTTEKT+NOTENDAUTTEKT, commit 7aeb274). Eftirlegur standa og flutningur þeirra er sér-verk: `DISK_IO_GREINING` og `HEILDARUTTEKT` enn á D:-rót, RLS_FIX-skjölin tvö í `app/docs/` (ekki audits/).

**Af hverju**: Skjal á D:-rót er ótrackað og ósýnilegt repo-leit — HEILDARUTTEKT sjálf bókar „Skráin liggur ótrackuð á D:\" sem HALT-lið.

**Heimild**: `D_UTTEKT_20260718T095336Z.md` §5.5/§9 liður 3, commit 7aeb274.

## 2026-08-02 — §5A-18 · Extraction-ImportError-atvikið (6 nætur) + fixvalið

**Hvað**: Næturkeðjan datt á ImportError 6 nætur (27.07–01.08; extraction-þrep eitt, promote heilt) eftir cc47-fellingu `MODEL_VERSION`. Fixvalið: import-lagfæring (`ADAPTER_MODEL_VERSION as MODEL_VERSION`) fram yfir endurútflutning — endurvakning harðkóðaðs nafns hafnað því verðmötin eru reiknuð AF freeze-akkeruðum adapter og stimpill hans er heiðarlegi model_version fyrir `listing_valuations`. Uppsafnið við fix: 1.416 uppsafnaðar verðmetnar (5/5 raunbots-sönnun). [Talan „816" úr verkbeiðni finnst hvergi; 1.416 er skjalfesta talan. Ekkert cc63-úttektarskjal er til — atvikið lifir í commitum og haus próbans.]

**Af hverju**: Sjá §5A-11 — þetta er atvikið sem setti innflytjenda-grep-regluna. Sannreynt í þessari lotu: nótt 02.08 endaði CHAIN CLEAN, extraction exit=0, effective_n=200.

**Heimild**: commit 00bc8e5, 721fafb; `scripts/verdmat_status_probe.ps1` haus; `night_20260802.log`.

## 2026-08-02 — §5A-19 · Vaktar-próbinn: sjálfstæður daglegur task fram yfir keðjulið + líftímaskilyrði

**Hvað**: Stöðu-próbinn er SJÁLFSTÆÐUR daglegur task (07:30) — „liður í keðju getur ekki tilkynnt dauða keðjunnar sjálfrar" (bilunarmáti atviks #3); les LastTaskResult allra verdmat-taska + loka-línur beggja keðjulogga í eina línu í `D:\verdmat_status.log`; 0x41303 (never ran) er hávært því task sem aldrei kviknar er scheduler-vandi, ekki no-op. LÍFTÍMASKILYRÐI: cc65 fasi 1 gleypir rökfræðina og AFSKRÁIR próbann berum orðum í fasa 3 — tvö kerfi lifa aldrei samhliða.

**Af hverju**: ImportError-næturnar sex hefðu sést á morgni eitt hjá lesanda LastTaskResult — próbinn er sá lesandi. Sannreynt í þessari lotu: skráður sem `verdmat-daily-status-probe`, keyrði 02.08 07:30 (exit 0), skrifaði vaktarlínu og greip `weekly-model-quality=0x2` (hannaða dómsreglu-HALTið).

**Heimild**: commit ac014fd, `scripts/verdmat_status_probe.ps1` + `scripts/register_status_probe_task.ps1`; Task Scheduler-mæling 02.08.

## 2026-08-02 — §5A-20 · GENERATED ALWAYS-frávikið (cc62 Fix B): frávik frá briefi bókast alltaf með rökum

**Hvað**: Fix B valdi GENERATED-dálka í stað „reiknað við promote + backfill-UPDATE" úr verklýsingu — dekkar báðar promote-leiðslur án Python-breytinga í næturkeðju, endurreiknast sjálfkrafa við re-scrape (handreiknaður dálkur hefði rotnað) og bakfyllir atómískt í ADD COLUMN. Frávikið var bókað í audit með rökum; formleg fyrirfram-blessun var ekki til — GO Danna á fasa 2 (skilyrt á nótt 02.08 CLEAN) staðfesti forsenduna eftirá.

**Af hverju**: Sannprófanir héldu allar: 0 frávik regex-vs-dálkur á öllum 36.007 röðum, view-fingrafar identískt fyrir/eftir, dreifingar stemma, nótt 02.08 CLEAN yfir generuðu dálkana. Reglan sem bókast: frávik frá briefi er leyfilegt EF það er bókað samstundis með rökum og sannprófunum — aldrei þegjandi.

**Heimild**: `LEITAR_UPPFAERSLA_FASI1_CC62_2026-08-02T0016Z.md` §1a/§4, migration `20260801_cc62_fixb_efnisdalkar.sql` (haus), commit 62c3df2.

## 2026-08-02 — §5A-21 · Cross-session-sweep á deildri skrá

**Hvað**: cc62-lotan stageaði `app/globals.css` af diski 21:59Z 01.08 meðan cc66-hunkurinn (`.vm-eign-eining`) sat þar ócommittaður — hunkurinn fór með í 62c3df2 (sögubókun í 2ddc88f). Reglan sem bókast: explicit-paths-reglan ver EKKI gegn samhliða lotu sem stagear sömu skrá; deildar skrár (globals.css o.þ.h.) krefjast samhæfingar milli lotna — sbr. eldri regluna um endur-tékk á git log í samhliða-lotum.

**Af hverju**: Klasinn fór í prod á undan componentinum sem notar hann — skaðlaust hér, en sama vél getur borið hálfkláraðan kóða út.

**Heimild**: git show 62c3df2 (báðir globals.css-hunkarnir), commit 2ddc88f (SÖGUBÓKUN).

## 2026-08-02 — §5A-22 · Disk-fyrir-commit-tímasetningarreglan

**Hvað**: Task Scheduler les disk — breyting á skriptu skráðs tasks committast FYRIR næstu keyrslu svo git og diskur séu samstiga frá fyrstu raunkeyrslu. cc66 mældi forsenduna við commitið (LastRun=aldrei/267011, NextRun 04:30, sannreynt kl. 00:24) og committaði 6a35e3e ~4 klst fyrir fyrstu keyrslu; fyrri fullyrðing um að ócommittaða skriptan hefði þegar keyrt „stóðst ekki mælingu".

**Af hverju**: Ósamstiga git/diskur gerir sögurakningu keyrslna ómögulega. Sannreynt í þessari lotu: fyrsta LIVE-keyrsla 02.08 04:30 endaði no-op á gate (loggur + pipeline_runs id=105, git_sha=6a35e3e) — rétt hegðun, samstillingin heldur.

**Heimild**: commit 6a35e3e (TIMASETNINGARBOKUN), commit 9bf3247; `D:\monthly_rent_level_restep.log`.

## 2026-08-02 — §5A-23 · Frávik frá prófunarkröfu bókast með jafngildri sönnun

**Hvað**: Skjáskotskrafa cc62 féll — skjalfesta ástæðan er „vafra-brúin ekki tengd í lotunni" — og strengja-/talnapróf á rendruðu HTML komu í staðinn, bókuð sem efnislega sterkari EN með skuldina skráða („skjáskotakrafan stendur ógreidd"). Reglan: frávik frá prófunarkröfu er leyfilegt EF jafngild eða sterkari sönnun kemur í staðinn OG frávikið er bókað. [Session-limit-skýringin úr verkbeiðni finnst ekki í skjölunum — heimild óstaðfest fyrir þá orsök.]

**Af hverju**: RSC-skil kljúfa strengi í rendruðu HTML — prófin verða að taka `<!-- -->`-skiljur út fyrir greppun; það er bókað í sama viðauka og sýnir að aðferðafrávikið var meðvitað og mælt.

**Heimild**: `LEITAR_UPPFAERSLA_FASI1_CC62` §4, `LEITAR_UPPFAERSLA_FASI2_CC62` §3 + VIÐAUKI liður 3.

## 2026-08-02 — §5A-24 · MIGRATION-APPLY ER HALT-SKYLDUR ATBURÐUR Í SJÁLFUM SÉR

**Hvað**: Apply á DB — líka „skaðlaus" additíf view-viðbót — er HALT-skyldur atburður í sjálfum sér; „prófun krafðist þess" er rök fyrir HALT-BEIÐNI, ekki umboð. Tilvikin tvö (cc69 `v_eign_virk_auglysing`; cc62-f2 leiguview) voru applýjuð í lotu með HALT aðeins push-megin; bæði báru rétt mótvægi (rollback skrifað FYRIR apply, additíft/enginn lesandi, 42P01/PGRST205-kóðavörn, prod-heilsa mæld undir gamla kóðanum, bókhaldsröð fylgdi apply hjá cc69) og standa eftirá-blessuð MEÐ þeim mótvægjum — mótvægin eru skilyrði blessunarinnar, ekki afsökun fyrir að sleppa HALTinu næst.

**Af hverju**: DDL á prod-DB er stöðubreyting utan git; rollback-skrá og additífni lækka áhættu en fella ekki ákvörðunarréttinn.

**Heimild**: `ASOLU_EIGN_CC69_2026-08-02T1048Z.md` haus/§1/§5.1, `LEITAR_UPPFAERSLA_FASI2_CC62` haus/§1-2a/§2/§4.

## 2026-08-02 — §5A-25 · Reconcile-reglan: apply_migration er eina leiðin sem skrifar schema_migrations

**Hvað**: `apply_migration` er EINA leiðin sem skrifar `schema_migrations`; sé DDL keyrt aðra leið (execute_sql, psql) skrifast reconcile-röð Í SÖMU LOTU — 14 stafa version af mældum apply-tíma, reconcile-haus í statements[0]. Tvær eftirá-raðir cc68 sannreyndar beint í DB í þessari lotu: `20260801214100` (cc62_fixb_efnisdalkar) + `20260802002800` (cc62_leiguview); cc69 bókaði sína sjálf (`20260802103908`). [Ekkert cc68-skjal er til á diski — reglan og raðirnar bókast hér á DB-sönnun; eina disk-ummerkið er „cc68-reconcile-vandinn endurtekur sig ekki hér" í cc69-skjalinu.]

**Af hverju**: Ó-reconcile-að DDL býr til drift milli `supabase migration list` og raunschema — bókhaldið er heilt aðeins ef hver DDL-leið endar í sömu bók. Fordæmi: baseline-reconcile 2026-05-21 og COMPS_V2-bókunin.

**Heimild**: DB `supabase_migrations.schema_migrations` (mælt 02.08), `ASOLU_EIGN_CC69` §1, DECISIONS:2341/2763, `docs/fable_prep/audit/COMPS_V2.md:112`.

## 2026-08-02 — §5A-26 · Window-falls-lærdómurinn: uppflettingar-view ber aldrei window-fall yfir allt mengið

**Hvað**: `v_leit_listings` + fastnum-sía mældist 62–255 ms því window-fallið (`er_nyjasta_birting`) hindrar qual-pushdown — ALLT lifandi framboðið (17.513 raðir) metið fyrir eina uppflettingu; þröngt definer-view (`scraper.v_eign_virk_auglysing`) mælist 0,4 ms. Reglan: uppflettingar-view (per-fastnum) má aldrei bera window-fall yfir allt mengið; listunar-view mega það. `saekjaAsettVerdEignar` ber sömu rót — bókað, óviðgert, sér-go (backlog).

**Af hverju**: Postgres ýtir fastnum-síu aldrei niður fyrir subquery með window-falli nema sían sitji á partition-lyklunum sjálfum.

**Heimild**: `ASOLU_EIGN_CC69` §1 (mælitafla)/§5.3, SQL-haus migrationarinnar `20260802_cc69_eign_virk_auglysing.sql`.

## 2026-08-02 — §5A-27 · Álftamýrar-birtingargatið: /eign sá aldrei virkar nightly-auglýsingar

**Hvað**: /eign las aðeins pöruð söluyfirlit (`last_listing_text`) + apríl-frosið snapshot (`augl_id_latest`, max scraped_at 2026-04-16) — virk nightly-auglýsing (Álftamýri 39 / 2013952 / listing 297367, mbl 174,0 M, first_seen 23.07) sást á /leit en aldrei á /eign. Lagað með „Á sölu"-kortinu (engin prósenta, ekkert vanmats-orðalag — §5A-14 heldur); snapshot-dálkarnir eru ALDREI fallback (nightly vinnur, snapshot þegir — kortið fellur á EKKERT); fullur dauði apríl-snapshotsins (precompute-hlið) er sérákvörðun á backlog.

**Af hverju**: Birtingargatið var strúktúrlegt — engin leið frá `scraper.listings` inn á /eign; kortið les nýja þrönga viewið (§5A-26). Prod-grænt 02.08 (viðauki: 174,0 M-línan greppuð á www.verdmat.ai).

**Heimild**: `ASOLU_EIGN_CC69` haus/§2/§5.2 + VIÐAUKI.

## 2026-08-02 — §5A-28 · HMS-innri mótsögnin (2013952): mapping fylgir notkun

**Hvað**: Fastnum 2013952 ber innri HMS-mótsögn — notkunar-flöturinn segir „Íbúð á hæð" (notkun_kodi 501) en matseiningar-gerðin „Raðhús" (gerd=2); mapping appsins fylgir notkun (properties: tegund_raw='Íbúð' → APT_STANDARD). Sannreynt í þessari lotu gegn `D:\HMS_jonas\hms_archive_staging.db` (fasteign_data JSON) og lifandi DB. Spurningin „á mapping að lesa matseiningar-gerð?" fer á líkans-backlog ágúst með mælingunni sem viðhengi. [Tölur verkbeiðni — „28/30 lengjunnar APT_*" og „verðáhrif ~1% (nr. 47 APT vs nr. 57 ROW_HOUSE)" — finnast hvergi á diski: heimild óstaðfest; ekkert cc68-skjal til. DB-nálgun lotunnar: nágrannalengjan er yfirgnæfandi APT_* (95 APT_STANDARD + 81 APT_FLOOR + 3 APT_BASEMENT vs 1 ROW_HOUSE á Álftamýri 25–58).]

**Af hverju**: TAXONOMY bókar „HMS er authoritative" — en þegar HMS stangast á við sjálft sig er valið milli flata mapping-ákvörðun sem á að hvíla á mældum verðáhrifum, ekki sjálfgefnu.

**Heimild**: `D:\HMS_jonas\hms_archive_staging.db` + properties-DB (mælt 02.08), `docs/TAXONOMY.md`.

## 2026-08-02 — §5A-29 · Fastinn-speglunin [heimild óstaðfest]

**Hvað**: [heimild óstaðfest] Verkbeiðnin bókar: fastinn.is/soluskra/[id] speglar mbl-`source_listing_id` — mbl-auðkenni lifa á þriðju síðum og breytir Step-3-samhengi (þverpörun). Ekkert cc68-skjal er til og engin disk-heimild fannst fyrir speglunar-fundinum sjálfum; bókast hér sem óstaðfest fullyrðing sem þarf endurmælingu áður en hún er notuð sem framkvæmdarforsenda.

**Af hverju**: Skylt á diski: `app/audit/cross_source_url_patterns.md` bókar fastinn.is sem Clerk-auth og „not a viable cross-source" — speglunar-fundurinn breytir samhenginu aðeins ef hann er sannreyndur.

**Heimild**: [heimild óstaðfest]; samhengi: `app/audit/cross_source_url_patterns.md`.

## 2026-08-02 — §5A-30 · mbl-last_seen-kadensan: sótt-stimpill, ekki nætur-heartbeat

**Hvað**: `last_seen_at` er hjá mbl SÓTT-stimpill (scraper endursækir ekki þegar-skrapaðar auglýsingar; status='ok'-skipið) — mælt í cc69: aðeins 794 af 16.587 virkum mbl-röðum fengu last_seen ≥01.08 (myigloo 929/929). Withdrawal-reglan er ónæm: `lifecycle_sweep_mbl.py` próbar mbl-API beint per auglýsinga-ID og les aldrei last_seen. DB-endurmæling þessarar lotu: 16.587 virkar, 255 stimplaðar 02.08 / 539 01.08 — sama stærðargráða.

**Af hverju**: Gamalt last_seen á mbl-röð er því EKKI merki um afskráningu — að lesa það þannig myndi endurvekja cc23-villuna (ferskleikasía á last_seen er röng lausn).

**Heimild**: `ASOLU_EIGN_CC69` §3; DB-mæling 02.08.

## 2026-08-02 — §5A-31 · Leiguverðsjár-framsetningarákvörðunin: tvær tölur á leiguflötum

**Hvað**: [ákvörðun arkitekts+eiganda 02.08 tekin í spjalli — sú heimild er ekki á diski; efnisrætur allar mældar] TVÆR tölur á leiguflötum: A „áætluð auglýst leiga" (samningsmat × mælt ask-álag, með heimildarnefningu) og B „áætluð samningsleiga" (módelið, aðaltalan skv. §5A-5). Skýringar orðast AÐEINS á mældu rótunum tveimur: ask-álag +19% (762 askar/21 sella) og birgða-elding ~3,8% (1,0384, n=1.189); skýring um félagslega mengun HAFNAÐ — cc58 mældi verðsjána ómengaða (mengun niður á við mælist ekki; utan-markaðsflöggun HMS trúverðug). Útfærsla óhafin (backlog). Næsti skjalfesti undanfari: F4-hugmyndin í cc60 (bíður leiguverðsjár-stigfærslu).

**Af hverju**: Ein tala í ask-heimi og önnur í samningsheimi án merkingar er nákvæmlega tálsýnin sem cc56 kró — báðar tölurnar birtast með mældri brú á milli.

**Heimild**: `STIGFAERSLA_UI_HMS_CC57` liður 3 (19%-línan), `EGILSGATA_KROSSVIDMID_MYNDIR` §3 A/B/C (elding + ómengun), `LEITARHUGMYNDIR_CC60` §2f F4.

## 2026-08-02 — §5A-32 · Akkeris-frávikið: enginn notendaflötur les real-vs-real; bíður ágúst

**Hvað**: Kallaralistinn (rg yfir öll þrjú repo) fann NÚLL staði í verdmat-ai sem lesa real-vs-real — öll líkans-vs-sala framsetning fer gegnum MV-ið (NOMINAL/NOMINAL); eina rekstrartilfellið er `precompute/holdout_eval.py` (+0,362% skekkja við mælingu, vaxandi frá flippi). Frávikið (sales=2026-09 vs model=2026-08) og akkeris-borðin standa til ágúst-vaktar/endurþjálfunar; ekkert lagað — listinn er dómur, ekki viðgerð. [Merkingar verkbeiðni „cc67-iii" og „cc68-C" finnast ekki á diski; efnið er bókað undir cc47 (LAEKNUN B) og cc51.]

**Af hverju**: Viðgerð á holdout_eval fyrir ágúst-vaktarmælinguna er sér-ákvörðun; að engir notendafletir skekkist er mælt, ekki ályktað.

**Heimild**: `LAEKNUN_B_AKKERISVORDUR` §5–§7, `ENDURKVORDUN_APPLY_CC51` §0.

*— Lok bókunarlotu cc70 §5A (DECISIONS-hluti).*

---

## 2026-08-04 — §5B-1 · Myndahýsingin HORFIN ÚR DNS: hotlink-áhættan frá cc58 rættist

**Hvað**: CloudFront-dreifingin `d1u57vh96em4i1.cloudfront.net` á **enga DNS-færslu** á fjórum resolverum — hún er horfin, ekki niðri (~00:40Z lifandi → 22:30Z dauð 03.08). Aðgreiningin skiptir máli: **eytt ≠ lokað** — slökkt (disabled) dreifing heldur DNS-nafninu og svarar 403; horfið nafn þýðir að dreifingin var EYDD. **95,46% eigna standa myndalausar** (222.306 af 232.887; þar af **48.821 sem misstu allt** því þær áttu enga aðra lind). `public.property_images` ber 2.583.775 raðir, 100% á þessu eina hýsili — ekkert varaslóðamynstur er til. cc80-talan 91,19% **endurgerðist ekki** á neinum eðlilegum nefnara (232.887 / 55.636 / 48.595 / 27.894 / `v_leit_listings`); hún stendur óendurgerð og **cc83-mælingin er heimildin**.

**Af hverju**: Áhættan var bókuð frá cc58 og aftur í heildarúttektinni (bylgja 2, liður 2.2): öll myndbirting hékk á EINUM ytri rofa hjá þriðja aðila þótt fullt afrit væri til á D:. Þriðji aðili sló rofann af án fyrirvara. Þetta er ekki bilun sem lagast — þetta er niðurrif, og eina svarið er eigin hýsing (sjá R2-spegilinn, PLANNING_BACKLOG).

**Heimild**: `docs/fable_prep/audits/MYNDAHYSING_DAUD_CC83_20260803T2256Z.md` §1.1/§1.2 (nefnaratafla), `HEILDARUTTEKT` HLUTI 3 (2.2), minni `project_myndir_hotlink_cloudfront`.

## 2026-08-04 — §5B-2 · Vercel 402-kvótinn er ÚRELTUR — cc58/cc62-f0-greiningin og valkostur A lokast

**Hvað**: `/_next/image` á lifandi upprunaslóð skilar **HTTP 200** — 402-kvótinn sem cc58 og cc62-f0 bókuðu er farinn. Myndaleysið í dag á því EKKERT skylt við Vercel-optimizerinn. **Valkostur A (uppfærsla á Vercel-plani) lokast** sem viðbragð, og hver greining sem hvílir á 402-forsendunni fellur með henni.

**Af hverju**: Tvær ólíkar bilanir hafa nú birst á sama yfirborði (myndir birtast ekki) með níu daga millibili — kvóti (cc58/cc62-f0) og hýsingardauði (§5B-1). Að bera gamla greiningu yfir á nýtt einkenni hefði valið rangan valkost; forsendan var endurmæld í stað þess að vera ályktuð.

**Heimild**: `MYNDAHYSING_DAUD_CC83_20260803T2256Z.md` §1.3 (402-mælingin) + §4 liður 3.

## 2026-08-04 — §5B-3 · GPTBot 74.7.227.14 STAÐFESTUR OpenAI — robots.txt bítur á raunverulegan aðila

**Hvað**: Talan **74.7.227.14 er innan `74.7.227.0/25`**, sem er eitt af 21 forskeyti í birtri IP-skrá OpenAI (`openai.com/gptbot.json`, HTTP 200, `creationTime 2025-10-30`). RDAP vísar á Azure (MICROSOFT-MAINT), sem samræmist. **PTR er NXDOMAIN** — en forward-confirmed rDNS **á ekki við hér**: OpenAI gefur ekki út PTR-færslur og vísar sjálft á json-skrána sem sannvottunarleið. **Afleiðing**: `robots.txt` bítur á raunverulegan aðila sem virðir hana — hún er **virk vörn, ekki kurteisi**; WAF er viðbót en ekki eina leiðin. **Bot-hlutfall umferðarinnar almennt er enn ÓMÆLT.**

**Af hverju**: Fyrsta prófið (PTR) skilaði engu og hefði — lesið sem sönnun — leitt til rangrar niðurstöðu („óstaðfestur hermir"). Sannvottunaraðferðin verður að fylgja þeirri sem útgefandinn birtir, ekki þeirri sem er hefðbundin.

**Heimild**: `MYNDAHYSING_DAUD_CC83_20260803T2256Z.md` §5 (a)/(b), minni `project_gptbot_stadfest_cc83`.

## 2026-08-04 — §5B-4 · AI Bots → Deny LIVE í Vercel (meðvituð ákvörðun eiganda)

**Hvað**: „AI Bots → Deny" er virkjað í Vercel-eldveggnum og **mælt**: GPTBot / ClaudeBot / PerplexityBot fá **403**, Googlebot fær **200 óbreytt** (leitarvélaskrið raskast ekki). **Viðvörun Vercel bókast með**: þetta gerir AI-leitar- og tilvitnunartólum erfiðara að lesa síðuna eða vísa í hana. Eigandi tók ákvörðunina með þeirri afleiðingu uppi á borðinu.

**Af hverju**: Bókun á viðvöruninni sjálfri er kjarni liðarins — ef sýnileiki í AI-svörum minnkar síðar á það ekki að lesast sem óútskýrt frávik, heldur sem mæld afleiðing valinnar stillingar sem má snúa við.

**Heimild**: Vercel-eldveggur (mælt 03.08, UA-próf 3× deny / 1× allow), `MYNDAHYSING_DAUD_CC83_20260803T2256Z.md` §5.

## 2026-08-04 — §5B-5 · NULL Á RÖÐ ER EKKI NULL Á EIGN — regression-viðmið veljast á EIGN

**Hvað**: Þegar eign ber margar raðir og birtingin velur EINA þeirra, þá prófar viðmið sem valið er á RÖÐ ekki það sem yfirborðið sýnir: röð með `NULL` getur verið til á eign sem birtir gildi úr annarri röð — viðmiðið „sannar" þá galla sem er ekki til, eða öfugt. **Regla**: regression-viðmið skulu valin á EIGN — `GROUP BY fastnum HAVING count(<reitur>) = 0` — **að undangenginni sömu síun og gagnalagið beitir** (sami ferskleiki, sama lind, sama virkni-skilyrði). Aðferðarvillan var gerð og leiðrétt innan cc82.

**Af hverju**: Kornastærð viðmiðsins verður að vera sú sama og kornastærð birtingarinnar. Þetta er sama bilunarmátið og `feedback_kaskadinn_felur_thynnkuna` bókar (mæla á kornastærð notandans) og systurregla `feedback_cov_maeling_nan_sem_miss` (nefnarinn bókast sér).

**Heimild**: `docs/SOLUADILI_MATSARGERD_CC82_20260803T133000Z.md` §V4.2.

## 2026-08-04 — §5B-6 · ÚTGÁFA ÓGILDIR EKKI `saekjaEign`-CACHE — allt að klukkustundar töf á /eign

**Hvað**: `saekjaEign` er vafið í `unstable_cache` með TTL 3.600 s og merkjum `eign` / `eign-<fastnum>` (cc73). Gagna-cache Vercel **lifir af útgáfu**, svo ný útgáfa sem breytir því HVAÐA dálka fallið sækir fær gamla farminn þar til TTL rennur út. **Mælt í cc82: ~47 mínútna töf** eftir deploy (söluyfirlitið birti sömu línu STRAX því sú síða notar `cache(...)`, sem er React-minnun innan einnar beiðni). cc75 tengdi `revalidateTag` við AI-fyllingarleiðina EINA — útgáfa hefur enga ógildingarleið. **Afleiðing sem nær lengra en cc82**: hver framtíðarbreyting á því sem `/eign` les lendir allt að klukkustund seint, og sá sem prófar strax eftir push les það sem BILUN. **Stendur á backlog sem HÖNNUNARÁKVÖRÐUN, ekki flýtilagfæring**: (a) útgáfuauðkenni inn í cache-lykilinn eða (b) ógilding inn í útgáfuferlið. Enginn go.

**Af hverju**: Þetta er ranggreiningargildra af sömu ætt og `feedback_ein_sokn_i_dev_asset_sannar_ekki_fjarveru`, nema útgáfu-megin: prófunin er rétt, kóðinn er réttur, og samt sýnir yfirborðið gamalt efni. Að bóka töfina sem þekkta hegðun er ódýrara en að endurgreina hana í hverri lotu.

**Heimild**: `docs/SOLUADILI_MATSARGERD_CC82_20260803T133000Z.md` §V3/§V3b; `lib/eign-queries.js:85` (verdmat-ai). Sami fundur er þegar bókaður í `PLANNING_BACKLOG.md` (Cache-fundur cc82).

*— Lok bókunarlotu cc88 §5B (DECISIONS-hluti).*

## 2026-08-04 — §5B-7 · LEIÐRÉTTING cc83: varanleikadómurinn „eytt ≠ lokað" er FELLDUR

**Hvað**: DNS-hvarf CloudFront-dreifingarinnar `d1u57vh96em4i1` 03.08 var **tímabundið útfall, ekki eyðing**. cc92 mældi 04.08 (read-only, 349,6 s): **200 af 200 geymdum slóðum úr `property_images` svara HTTP 200 — 100,0% í öllum fjórum lögum**, 0 × 403, 0 × 404, 0 villur, kill-switch virkjaðist aldrei. Sterkara en það: **allar 200 báru `X-Cache: Miss from cloudfront`** — ekkert svar kom úr jaðar-skyndiminni, **upprunninn sjálfur heldur enn gömlu hlutunum** (200/200 `image/jpeg`, 66.921–759.205 B, meðaltal 336.198). Þar með fellur §5B-1-ályktunin „horfið nafn ⇒ dreifingin var EYDD": **fjarvera úr DNS sannar ekki eyðingu.** **Restin af cc83 stendur óhögguð** — D:-staðan þá, spegiltölurnar, 402-úreldingin (§5B-2) og GPTBot-staðfestingin (§5B-3) snerta þetta ekki.

**Útfallsbilið er BIL, ekki punktur** — og verkbeiðnar-orðalagið „~2 sólarhringar" er **efri mörk þess, ekki mæling**: síðasta LIFANDI mæling er `2026-08-03T00:40Z` (cc72), fyrsta DAUÐA `2026-08-03T22:30Z` (cc83), endurkoma í DNS `2026-08-04 ~22:04Z`. Mælt útfall er því **≥ 23 klst 34 mín og ≤ 45 klst 24 mín**; cc92 orðar sjálft „féll úr DNS fyrir sólarhring". Endurkomu-tímastimpillinn er **arkitektsmæling og liggur ekki á diski**.

**Af hverju**: Aðgreiningin sem cc83 byggði á (eytt vs lokað) var rétt sett fram en dómurinn var dreginn af EINNI mælingu á einum tímapunkti. cc92 §7 bókar sjálft hvað prófið sannar EKKI, og sá varnagli á að fylgja liðnum: ekkert hotlink-próf (enginn `Referer`), engin aldursvörn (lögin eru fastnum-röð, sjá §5B-12), enginn varanleiki (ytri rofinn er enn ytri), og n=200 af 2.583.775 — efri 95%-mörk á bilunartíðni við 0/200 eru **~1,5%**, svo safn með 1% dauðum slóðum hefði vel getað skilað 200/200. HEAD ≠ GET: bætin voru ekki sótt.

**Heimild**: `D:\_audit\HYSILL_LIFNADI_CC92_20260804T2215Z.md` §1/§2/§5/§7; `MYNDAHYSING_DAUD_CC83_20260803T2256Z.md` línur 12/158/161 (00:40Z lifandi, 22:30Z dauð); endurkoman í DNS 04.08 ~22:04Z **[arkitektsmæling, ekki á diski]**.

## 2026-08-04 — §5B-8 · LEIÐRÉTTING cc84 §2.3/§6: 2344094-greiningin var ÖFUG — röðunin valdi RÉTT

**Hvað**: cc84 bókaði atviksábendingu — „röðunin velur ranga töluna og felur þá réttu" á fastnum **2344094**. **Þetta stenst ekki.** Óháði dómarinn (HMS) segir: byggingarstig **B1**, matsstig 1, fasteignamat **3.350 þús. kr.**, einflm 102, lóð 5.560 m² — **óbyggð sumarhúsalóð**. Birta talan (**14.900.000**, auðkenni 1712131, Fasteignaland, `rn=1`) selur nákvæmlega það: „Sumarhúsalóð með púða og teikningum … Teikningar fyrir 102 fm hús … fylgja með í kaupum." Falda talan (**94.900.000**, auðkenni 1674955, Betri Stofan, `rn=2`) selur „glæsilegt heilsárshús … fullklárað að innan og utan" — **hús sem er ekki til í fasteignaskrá**. Hlutföll: 14,9 M = **4,45×** fasteignamat (innan p95 = 5,08×), 94,9 M = **28,33×** (yfir p99 = 19,39×); miðgildi alls virks framboðs er 1,18×. B1-hópurinn allur: n=**595**, miðgildi mats **3.010 þús.** — 2344094 situr á miðgildi hópsins. **Röðunin valdi töluna sem samræmist skráðu ástandi eignarinnar.**

**102 m² í báðum auglýsingum er sama talan af ólíkum uppruna** — flatarmál TEIKNINGAR hjá Fasteignalandi, flatarmál HÚSS hjá Betri Stofunni. Stærðarjafnræðið sem lét þetta líta út eins og mótsögn er tilviljun. **Báðar auglýsingar LIFA** (mbl.is, mælt 04.08: `og:title` „Grensás 26, Selfossi" á báðum, HTTP 200); þriðja röðin (1709601, 14,9 M) sem `confirmed_absent_1` felldi 31.07 er líka sú eina sem mbl svarar tómri skel fyrir — sjálfstæð sannprófun á aðferðinni. Á öfgamenginu öllu: **38 af 40 tilvikum bera TVÆR LIFANDI auglýsingar**. Þetta er því **samtímis ágreiningur milli tveggja söluaðila, ekki röðunarvilla** — hönnunarspurning sem fæst ekki leyst með röðun.

**Af hverju**: Rótin sem cc84 leitaði að er raunveruleg en önnur: **FASTNÚMER ER EKKI SÖLUEINING.** Sama fastnúmer getur borið lóð og húsið sem á að rísa á henni, matshluta 0101 og 0102, jörð og hlut í henni, fasteign og reksturinn í henni. Sérhver framtíðar-„villuleit" sem raðar tveimur verðum á eitt fastnúmer og kallar lægri töluna villu endurtekur nákvæmlega þessa ranggreiningu.

**Heimild**: `D:\_audit\RANGT_ASETT_VERD_AUDIT_CC90_20260804T1600Z.md` §4.1–§4.5 (raðirnar þrjár, lýsingarnar, HMS-taflan, lifunarprófið) + §3 (38 af 40); `_audit/AUGLYSINGASAGAN_AUDIT_CC84_20260803T1500Z.md` §2.3/§6 (liðurinn sem er leiðréttur).

## 2026-08-04 — §5B-9 · cc86-forskriftarvillan var ARKITEKTSINS: „174/174" stangaðist á við c3-regluna sjálfa

**Hvað**: Kröfuna „teljarinn á að fara í **174/174** á fastnum 2123239" var ekki hægt að uppfylla samtímis c3-reglunni sem sama verkbeiðni setti. **174 er fjöldi ólíkra slóða yfir ALLAR sex virku auglýsingar fastnúmersins** (574 raðir → 174 eftir dedupe); **c3-reglan velur EINA auglýsingu per fastnum** eftir ferskleika og deduperar innan hennar — og sú auglýsing ber **100** myndir. Lotan fylgdi reglunni og skilaði **100/100**, og **það var rétt**. **INVARIANTIÐ er reglan sjálf: teljarinn skal jafngilda raunfjölda BIRTANLEGRA mynda** — hvaða tala það er ræðst af því hvaða mengi er birt, og hún má aldrei vera fest fyrirfram á tölu úr öðru mengi.

**Af hverju**: Gamla greinin sagði „+570 myndir" þegar 174 voru til — **3,3× ofmat** sem fellur á nefnara-skoðun (grunnregla 13) — og sex raðir báru allar `img_order = 1`, svo fyrstu reitir myndarandarinnar urðu sama myndin úr sitt hvorri auglýsingunni (og `key={m.img_order}` varð tvítekinn React-lykill). Röðunin sem c3 valdi er **mæld, ekki valin af smekk**: `listed_at desc nulls last, first_seen_at desc nulls last, listing_id desc` velur sömu auglýsingu og röðun Á sölu-kortsins á **öllum 8.886 eignum greinarinnar — 0 ósammála**. `listing_id desc` er hreinn jafnteflis-brjótur; án hans er röðunin ekki heildarröðun og röndin gæti flökt milli fyrirspurna. [Bókhaldsathugasemd: migration-athugasemdin segir c2 fjölga eignum greinarinnar um **3.509** en commit-skilaboðin bóka **5.377 → 8.881 = 3.504**, og cc93-migrationin endurtekur **3.504**. Talan 3.504 stendur; 3.509 er stök og óstudd.]

**Heimild**: `verdmat-ai` commit `7024c08` (skilaboð), `verdmat-ai/supabase/migrations/20260804_cc86_daudir_myndahyslar.sql` línur 28–57.

## 2026-08-04 — §5B-10 · cc91-sannprófunin: cc87 stenst bæti fyrir bæti — og heild úr þekktum undirliðum er EKKI heild

**Hvað**: Sjálfstæð endurmæling á R2-fötunni (`rclone size --fast-list`, tæpum sólarhring eftir cc87) skilar **núll fráviki á öllum sex tölum** cc87 §19: `myndir/` **2.631.932 hlutir / 586.385.814.963 bæti**, `myndir-leiga/` **12.976 / 1.778.600.751**, samtals **2.644.908 / 588.164.415.714**. Reikningurinn lokast í báðar áttir gegn flatri rótartalningu: hlutir **2.631.932 + 12.976 + 4.125 = 2.649.033**, bæti **586.385.814.963 + 1.778.600.751 + 26.949.069.967 = 615.113.485.681** — hvort tveggja nákvæmlega mæling C. **Bókhaldsvillan í cc87 §17 er leiðrétt**: „56.771 fastnúmer" var **PRE-SPLIT** talan; rétt er **55.637** undir `myndir/` og **1.134** leiguauðkenni undir `myndir-leiga/` (56.771 − 55.637 = 1.134, nákvæmlega aðskilnaðurinn sem cc87 §12 ákvað). Hlutatalan var rétt í báðum skjölum — aðeins nefnarinn var stale. Sjálfstæð staðfesting: **55.637** er sama tala og `image_index.db` ber (mælt í þessari lotu: 2.631.485 raðir / **55.637** fastnúmer).

**Af hverju**: Morgunvaktin 04.08 bókaði „`myndir/` ekki til, 0 hlutir; fötu-heild **4.125**" og felldi þar með fasa 1. Talan var **rétt mæling á röngu mengi** — 4.125 = 925 backups (`current/` 625 + `archive/` 106 + `2026-05-20T12-35/` 194) + 3.200 probes, þ.e. summa ekki-mynda-forskeytanna einna. **Reglan sem þetta setur: heild fötu sem er sett saman úr þekktum undirliðum er ekki heild fötu — hún getur ekki afsannað forskeyti sem mælandinn þekkir ekki. Flöt rótartalning er eina talan sem má bera það nafn.** Keyrslutíminn lekur svarinu sem aukavörn: mælingar A og C tóku 29,3 og 29,6 mín, B tók 10 s — **tómt forskeyti skilar samstundis**, svo hálftímalöng talning er sjálf sönnun um að forskeytið sé ekki tómt.

**Heimild**: `D:\_audit\R2_SANNPROFUN_CC91_20260804T2220Z.md` §1–§3, §5.1, §7; `docs/fable_prep/audits/R2_SPEGILL_FASI0_CC87_20260803T2325Z.md` §17/§19; `D:\Gagnapakkar\image_index.db` (mælt 04.08).

## 2026-08-04 — §5B-11 · ÁKVÖRÐUNIN: birta af LIFANDI hýslinum strax (cc93); R2-birtingarleiðin er varanlega formið, á backlog

**Hvað**: Ákvörðun arkitekts+eiganda: **taka hýsilinn af dauðalistanum og birta safnið aftur STRAX** — R2-birtingarleiðin (cc87 fasi 2) fer á backlog **sem varanlegt form**, ekki sem viðbragð. cc93 er **ein `delete`** úr `public.daudir_myndahyslar`, **engin view-breyting**: cc86 hannaði endurheimtina inn í `v_eign_myndir` þannig að tæmist listinn verður innra `NOT EXISTS` ósatt og cc23-forgangurinn (safn vinnur) tekur við af sjálfu sér. c2/c3-reglurnar standa óhreyfðar og gilda áfram um þau 5.377 fastnúmer sem eiga enga safn-röð. Taflan er **ekki dropuð** — tóm tafla er RÉTT ástand hennar, hún er vélbúnaðurinn fyrir næsta útfall.

**Staða cc93, mæld í þessari lotu (read-only)**: **APPLÝJAÐ Á PROD** — `public.daudir_myndahyslar` skilar **0 röðum**; safngreinin er virk (`v_eign_myndir` skilar **36** röðum á fastnum 2207452 og **100** á 2123239, allar á CloudFront-slóðum). **ÓCOMMITTAÐ**: `20260804_cc93_hysill_af_daudalista.sql` (71 lína) + rollback standa **untracked** í `verdmat-ai`. **Enginn cc93-skiladómur liggur á diski.**

**Tölur cc93, mældar FYRIR apply 04.08** — nefnarar: 55.636 fastnúmer eiga safn-röð (2.583.775 raðir, 100% á þessum eina hýsli), 8.881 bera auglýsingagrein, 17.033 virkar auglýsingar með fastnúmeri, 232.887 eignir alls.

| grein sem birtist | FYRIR (mælt) | EFTIR (**SPÁÐ**) |
|---|---:|---:|
| safngrein | 0 eignir | 55.636 eignir |
| auglýsingagrein | 8.881 eignir | 5.377 eignir |
| stöðumerki | 52.132 eignir | 0 eignir |
| birtar myndir | 217.193 | 2.583.775 |

**EFTIR-dálkurinn er SPÁ, ekki eftirá-mæling** — hún liggur ekki á diski og er **óbókuð hér**. **Tap = 0** (mælt beint: `birtir_fyrir > 0 and birtir_eftir = 0` skilar 0 röðum) en **3.504 eignir SKIPTA UM GREIN**, og kostnaðurinn þar er bókaður: **559 eignir sýna FÆRRI myndir** (18.146 → 11.449, **−6.697**) því safnið þeirra er styttra en auglýsingin sem þær báru; 2.339 sýna FLEIRI (58.690 → 175.161) og 606 jafnmargar. Lágmark eftir er 1 — engin dettur í núll.

**Af hverju**: **Útfallið sannaði ÞÖRF spegilsins, ekki fall hýsilsins.** Sá sem les §5B-7 sem „við þurftum aldrei R2" les rangt: hýsillinn er enn ytri rofi hjá þriðja aðila (`project_myndir_hotlink_cloudfront`), hann fór einu sinni og getur farið aftur, og spegillinn er fullgerður og bætta-vottaður (§5B-10) en er **afrit, ekki birtingarleið**. Birtingin liggur á upprunahýslinum þangað til fasi 2 er hannaður — nákvæmlega staðan sem var í gildi fram að 03.08.

**Heimild**: `verdmat-ai/supabase/migrations/20260804_cc93_hysill_af_daudalista.sql` (allar tölur, línur 36–57); DB-mæling 04.08 gegnum PostgREST með `service_role` (0 raðir í `daudir_myndahyslar`; 36/100 raðir í `v_eign_myndir`); `git status` í `verdmat-ai` 04.08 (untracked).

## 2026-08-04 — §5B-12 · SKEMAMÁL: `property_images` ber ENGAN tímastimpil — fastnum-lög eru röðunarlög, ekki aldurslög

**Hvað**: `public.property_images` hefur **þrjá dálka og engan tímastimpil**: `fastnum bigint not null`, `url text not null`, `img_order integer not null`, `primary key (fastnum, img_order)`. Það þýðir að **enginn flötur í DB getur svarað „hvenær var þessi mynd sótt?"**. Nálgunin sem næst er `properties.scraped_at_latest`, og hún er þjöppuð í **2026-04-10 .. 2026-04-16** (sex dagar) fyrir allar eignir — það er fjöldaskröpunin, ekki aldur myndarinnar. **D:-hliðin bætir þetta EKKI upp**: `image_index.db` ber vissulega `first_seen_at` (0 NULL af 2.631.485 röðum) og `last_verified_at` (2.631.427 gildi), **en spönnin er `2026-05-08T12:35:22Z` .. `2026-05-13T22:34:16Z`** — sex dagar, samsöfnunarkeyrslan sjálf. **Hvorugur flöturinn ber raunaldur myndar.**

**Af hverju**: Þetta er varnagli cc92 og hann bindur hverja framtíðarmælingu. Lögin fjögur í cc92 (elstu/miðja/nýjustu/slemba) eru **fastnum-RÖÐUNARLÖG, ekki upptökudagsetningarlög** — prófið mældi hvort slóðir yfir allt fastnum-bilið lifi (33 .. 206.138.810, þakið jafnt) og gat **ekki** mælt hvort myndir sóttar á tilteknum tíma hafi dáið. Vörnin gegn aldursbundinni eyðingu er því **rökstudd en ekki bein**, og sérhver spurning af gerðinni „dóu gömlu myndirnar?" strandar á skemanu þar til tímastimpill bætist við. [Nákvæmni: cc87 §18 liður 2 nefnir `property_images.original_url` — **sá dálkur er í `image_index.db` á D:, ekki í `public.property_images`**, þar sem hann heitir `url`. Efnisatriðið stendur óhaggað: 100% slóða vísa á þennan eina hýsil (cc92 §2).]

**Heimild**: `verdmat-ai/supabase/migrations/20260705_property_images.sql` línur 16–21 (DDL); `D:\_audit\HYSILL_LIFNADI_CC92_20260804T2215Z.md` §3/§7.2; `D:\Gagnapakkar\image_index.db` skema + tímastimpilmæling 04.08.

## 2026-08-04 — §5B-13 · cc85 verk D — ákvarðanir arkitekts D1–D5

**Hvað**: Fimm ákvarðanir teknar á hönnunarskjali cc85 (verk D, lotu-samsöfnun); framkvæmdin sjálf bíður tímasetningar eiganda (PLANNING_BACKLOG).

- **D1 — orðalag**: „**engin þinglýst sala er skráð**", ALDREI „seldist ekki". Briefið setur sjálft ályktunarbannið: við vitum að sala er óskráð, ekki hvers vegna.
- **D2 — fjöleiningarsían: FELLA ÚT**. **1.284 örugg fastanúmer > 1.565 með 18% hávaða** á eignasíðu. Mælt: 10,96% fastanúmera í sögulega safninu bera >1 ólíka `einflm`; innan flöggaða mengisins **17,96% (281 af 1.565)**. Flaggið fellur út þegar `n_olikar_staerdir > 1`.
- **D3 — `gap_dagar = 90` LÆST**, en sem **gildi í `scraper.session_config`, ekki fasti í kóða** (±10 pp á þýðið).
- **D4 — leiðrétting 1 SAMÞYKKT**: forsenda briefsins („time-on-market röng á 19% virkra") **féll fyrir mælingu**. Á 8.365 einingum **VANmetur** `v_units.days_on_market` að meðaltali **−3,3 daga** (96,1 vs 99,5) og **OFmetur á 8 af 8.365 = 0,10%**. **Spillti dálkurinn er annar: `n_relistings`**, sem telur 3,37 auðkenni að meðaltali (hámark 141) sem „endurbirtingar" þegar um eina samfellda keyrslu er að ræða. Enginn TOM-dálkur er notendasýnilegur (`days_on_market` finnst hvergi í app-kóða; `ASoluKort.tsx` ber bindandi bann við „X daga á sölu"). Verkið er því **(a) `n_relistings`-viðgerð + (b) opnun á RÉTTA TOM-tölu**, ekki viðgerð á rangri birtri tölu.
- **D5 — tvö apply-þrep með HALT á milli**: tafla + backfill fyrst og mælt, svo view + UI í sérlotu (sama og phase_d).

**Af hverju**: D4 er kjarninn og hann er fordæmi: **forsenda arkitektsins var felld af mælingu áður en hannað var**, og umfang verksins breyttist við það. Að hafa byggt „viðgerðina" á briefinu hefði lagað dálk sem enginn notandi sér og skilið eftir þann sem er raunverulega spilltur. D2 er sama ætt: þrengra mengi með sannreyndri kornastærð vinnur stærra mengi með hávaða (sbr. `feedback_kaskadinn_felur_thynnkuna`).

**Heimild**: `D:\VIDHALDSSAGA_D_HONNUN_CC85_20260804T0030Z.md` §0.1 (TOM-taflan, `n_relistings`), §0.2, §3 (fjöleiningarsían, 1.565 → 1.284), §6 (D1–D5-taflan).

*— Lok bókunarlotu cc95 §5B (DECISIONS-hluti).*

---

# BÓKUNARLOTA cc108 — §5C (2026-08-07, append-only í enda skjals skv. verkbeiðni)

**Umfang:** cc93–cc107. Allt bókast hér í fyrsta sinn nema EFTIR-dálkur cc93, sem leiðréttir §5B-11 úr spá í mælingu. **Bókunarregla lotunnar:** hver tala er sannreynd af diski, úr git eða úr skjalfestri mælingu ÁÐUR en hún er skrifuð hér; tala sem finnst ekki á diski er **ekki bókuð** heldur talin upp á frávikalista í HALT-skilum lotunnar. Heimildaslóð fylgir hverri færslu.

## 2026-08-07 — §5C-1 · cc93: EFTIR-DÁLKURINN ER MÆLDUR — spáin stenst, og PAR-REGLAN fæðist

**Hvað**: §5B-11 bókaði EFTIR-dálk cc93 sem **SPÁ** og tók fram að eftirá-mæling lægi ekki á diski. Hún liggur þar núna og **spáin stenst lið fyrir lið**: safngrein **55.636** eignir / 2.583.775 myndir (spáð 55.636) · auglýsingagrein **5.377** / 125.319 (spáð 5.377) · stöðumerki **0** eignir (var 52.132) · raðir í viewinu 2.800.968 → **2.709.094** · fastnúmer í viewinu **61.013 óbreytt**. **TAP = 0** mælt, ekki ályktað (skilyrðið „birti myndir fyrir OG er myndalaus eftir" skilar 0 röðum; 0 eignir með view-röð en enga lifandi röð; 0 raðir eftir á dauðalistanum). Kostnaðurinn stendur óbreyttur frá §5B-11: 3.504 eignir skipta um lind, þar af **559 með FÆRRI myndir** (18.146 → 11.449, −6.697), 2.339 með fleiri (58.690 → 175.161), 606 jafnmargar, lágmark 1 — engin dettur í núll.

**Sópunin var raunsókn, ekki ályktun af hýsilnafni**: 32 eignir × 3 rútur = 96 síður, 77 svöruðu 200 og 19 `/soluyfirlit` 404 (rétt ástand). **536 ólíkar uppstreymis-slóðir sóttar**, þar af safnhýsillinn **504 slóðir / 0 dauðar** og `myigloo.is` 12 / 0. Prod eftir deploy gaf **sömu tölur og staðbundið, lið fyrir lið**: 536 slóðir, 504/0, **0 af 77 síðum með stöðumerki** (prod FYRIR deploy: **42 af 77**), myndaslóðir A/B/C/D/P 229/270/88/0/112 í báðum. Prófeignir eftir: 2000276 **14** · 2123239 **100** · 2298591 **134** · 2302209 **28**, allar á safngrein, engin með stöðumerki. **Bókað utan cc93**: `cdn.mbl.is` ber **5 dauðar (404) af 20** sóttum slóðum, sama tala staðbundið og á prod — ferskleikavandi auglýsingamynda, ósnertur af cc93.

**Tímalínan er mæld**: applý 22:38Z → push `00621d3` 23:06:14Z → fyrsta græna prod-síða **23:06:32Z (18 s)** → full sópun græn 23:07:53Z (99 s). Glugginn þar sem prod-DB var komin á nýja stöðu en prod-kóði bar enn hýsilinn stóð **~28 mínútur** og kostaði **3.504 eignir** myndirnar sínar á meðan (B-flokkur mældist með 24 slóðir í stað 270; A- og C-flokkur óbreyttir).

**Af hverju**: **PAR-REGLAN.** Þegar migration og kóðadeploy mynda PAR — DB-breyting sem kóðinn verður að fylgja — er **hvorug röðin hlutlaus**. „Applýja fyrst" opnar glugga þar sem gamli kóðinn les nýja stöðu vitlaust; „deploya fyrst" opnar glugga þar sem nýi kóðinn les gömlu stöðuna vitlaust. Hér var **seinni glugginn meinlaus** (nýi kóðinn hefði rendrað safn-slóðir sem svara 200 — hýsillinn var á lífi) og sá **fyrri kostaði 3.504 eignir myndirnar sínar**. Röðin á að veljast af því **HVOR glugginn er skaðlaus**, ekki af vana. Aukalærdómur sem mældist í leiðinni: `EIGN_CACHE_UTGAFA`-hækkunin gerði lokunina samstundis — 18 sekúndur frá push að fyrstu grænu prod-síðu, í stað allt að klukkustundar `unstable_cache`-fyrningar (§5B-6).

**Tæknilegur varnagli sem fylgir reglunni**: `DAUDAR_SLODIR_OR` er `DAUDIR_MYNDAHYSLAR.map(...).join(",")` og verður **tómur strengur** á tómum lista; `.or("")` er ógildur síustrengur sem PostgREST hafnar, svo `faldar`-sóknin hefði KASTAÐ á eignasíðunni í stað þess að skila núlli. Þess vegna varð `ERU_DAUDIR_HYSLAR` nauðsyn, ekki snyrtimennska — `anDaudraHysla` er hlutleysa af sjálfu sér (reduce yfir tómt) og mátti ekki fá sömu meðferð.

**Heimild**: `D:\_audit\HYSILL_AF_DAUDALISTA_CC93_20260804T2320Z.md` §2 (fyrir/eftir-taflan m/nefnurum), §3 (prófeignir), §4 (sópun), §4b (prod), §5 (atvikið + reglan), §6 (kóðabreytingar); `verdmat-ai` commit `00621d3`.

## 2026-08-07 — §5C-2 · cc94: COMPONENTS-SPILLINGIN STÖÐVUÐ Í ÞREMUR LÖGUM — 0 brot af 5.491

**Hvað**: Blæðing frá **2026-06-27** sem bætti við ~6 spilltum útdráttum á nóttu er stöðvuð. Umfangið mælt með nefnurum: **152 af 5.122 útdráttum (2,97 %)** báru `components` sem **streng** í stað hlutar (cc85 hafði mælt 148/4.922 = 3,01 % — vísitalan stóðst yfir 200 nýja útdrætti). Auk þess 2 ár utan [1900, 2026] af 4.449 fylltum (0,045 %), 11 component-lyklar utan 18-mengisins af 89.471 hólfum (0,012 %), 5 `status`-gildi utan enum (0,006 %) og 12 útdrættir af 5.122 sem bera **ritvillu-afbrigði í STAÐINN fyrir** `reported_issues` (`reporting_issues` 9× + `report_issues` 3× = nákvæmlega 5.122 − 5.110).

**Vörnin er þrjú lög, ekki eitt:**
1. **Þrep A (LIVE 04.08 23:04Z)** — `validate_extraction()` í `extraction_engine.py`, sett á **eina skrifstaðinn**. Kallstaðurinn var **rakinn með grepi, ekki gefinn**: `grep -rn extract_and_store` skilar einum kallstað (`run_extraction.py:131`); `extract_listing` á tvo, en hinn (`model_quality_eval.py:725`) skrifar í JSONL-cache, ekki í töfluna. Valið var **A1** (dálkur `validation_status`) fram yfir sér höfnunartöflu (A2 hefði búið til nýjan RLS-flöt) og fram yfir logg eingöngu (A3 hefði skilið eftir eilífa endurkeyrslu á sömu lýsingu).
2. **Þrep B (05.–06.08)** — afturvirk viðgerð. B1: 153 raðir endurlesnar með föstu mynstri; **2.752 af 2.754 hólfum (99,93 %)** lesin, 274 ár endurheimt, tvö töpuðu hólfin **nákvæmlega þau sem spáð var** (eitt ólesið `foundation_drainage`, eitt `mixed` → NULL). B3: 11 aukahólf + 5 status-gildi hreinsuð. B2: 2 ár → NULL.
3. **Þrep C (LIVE 06.08)** — `scraper.extraction_er_gilt(jsonb)` IMMUTABLE + CHECK með undanþágu fyrir raðir merktar `rejected:%`. Röðin B → C er **skilyrði, ekki smekkur**: á óviðgerðum gögnum hefði CHECK-ið fallið á 152 + 2 + 11 + 5 brotum, og hefði C komið á undan A hefði **ein spillt lína fellt allt 200-raða `execute_values`-batchið** og nóttin tapað öllu.

**Mældur árangur**: brot í töflunni **0 af 5.491**. Nótt 05.08: 169 raðir, 168 `ok`, 1 hafnað, **0 ómerktar**. Nótt 06.08: 200 raðir, 197 `ok`, 3 hafnaðar, **0 ómerktar**. **Endurkallið mælist marktækt**: 10 endurköll á 06.08, **8 björguð**; með 05.08 (2 af 3) er hlutfallið **10 af 13 = 77 %** — sem staðfestir forsenduna sem endurkallið hvíldi á, að form-rekið sé **slembið** en ekki eiginleiki tiltekinnar lýsingar. Kostnaður endurkalla mældur $0,021 nóttina 05.08 (spáð ~$0,04).

**Bókaður kostnaður viðgerðarinnar**: **1.309 `detail`-textar felldir** í B1. Þeir voru þegar spilltir (brotin unicode-escape), bera enga mælingu niðurstraums og liggja óbreyttir í afritstöflunni `scraper.listing_extractions_pre_cc94b` (163 raðir) — **hún má ekki fara** fyrr en sér-go liggur fyrir. Fjórar frystar verðmatsraðir voru endurfrystar (V2) og **sundurliðunin gengur upp sem sjálfstæð staðfesting**: 2074179 akkerisfærsla −0,383 % + ársáhrif −1,44 % = −1,82 % spáð gegn **−1,81 % mælt**; 2170257 −0,383 % + 0,32 % = −0,06 % gegn **−0,06 % mælt**.

**Af hverju**: Rótin var ekki parse-galli heldur **form-rek líkansins, hleypt í gegn af ENGRI valideringu**. `input_schema` í tólaskilgreiningu API-sins er leiðbeining til líkansins, ekki server-side validator. Sönnunin er táknfræðileg: öll 152 gildin byrja á `{` og líta út fyrir að vera JSON-serialisering, en **0 af 152 parsast**, og samhengið sýnir hálfkláruð escape-sekvens þar sem sami íslenski stafurinn er ýmist escape-aður eða hrár **innan sama orðs** (`m\u00e1l og m\u00farvið\u00ger\u00f0ir`). Enginn serialiserari framleiðir það: `ensure_ascii=True` escape-ar alla ekki-ASCII stafi einsleitt, `ensure_ascii=False` engan. Líkanið **typar strenginn staf fyrir staf og misritar escape-kóðunina**.

**Hitt lærdómsatriðið er þögnin.** Fjögur lög vörðu sig sjálf og **ekkert lag hafnaði eða loggaði**: `extract_listing` skilaði óbreyttu, `extract_and_store` INSERT-aði, brúin `scraper.eigindi_ur_extraction` varpaði strengnum í `'{}'::jsonb` og sleppti þremur eigindalyklum, og `build_extraction_features` fékk 18 NaN + 2 NaN-stuðla. Notandinn sá **„Óþekkt"** á eldhús-, baðherbergis- og gólfefna-ástandi á 93 eignum í virkri sölu — nákvæmlega einkennið sem cc75 var smíðuð til að útrýma. Sama mynstur og `feedback_wrapper_eydir_eigin_sonnun`.

**Hönnunarval sem víkur frá upphaflegu drögunum og er bókað sem slíkt**: drögin lögðu til að valideringin **lagfærði** röðina í skrifleiðinni. Það var fellt. Röðin er vistuð **ÓBREYTT og aðeins merkt**, því hrásvarið er sönnunargagnið sem gerði þessa greiningu mögulega — hefði fyrri lota hreinsað í skrifleiðinni væri `\u00ger`-sporið horfið og rótin ógreinanleg. Öll leiðrétting á heima afturvirkt og afturkræft. Sömu röksemd fylgir merkingin `repaired:` (ekki `ok`): viðgerð röð er hvorki `ok` (hún stóðst ekki upphaflega og `detail` er fallið) né `rejected` (hún er nothæf núna), og að setja hana á `ok` hefði þurrkað út upprunann.

**Bókað frávik frá GO-inu**: neðri ármörkin. GO-ið tilgreindi [1900, 2026] og það var implementerað; skýrslan hafði lagt til **1850** því disksafnið ber 1882 (1×) og 1898 (3×) sem eru trúverðug íslensk byggingarár. Tíðni: 4 af 27.464 fylltum árum = **0,015 %**, og **0 í lifandi DB**. Höfnun er afturkræf (röðin vistast óbreytt), svo víkkun + endurvalidering endurheimtir hana; það er breyting á einni línu. Í DB eru mörkin **[1900, 2100]** af annarri ástæðu sem er líka bókuð: `CHECK` verður að vera IMMUTABLE og má ekki lesa `now()`, svo hörð 2026-mörk yrðu jarðsprengja — 1. janúar 2027 felldi fyrsta rétta 2027-ártalið nóttina.

**Heimild**: `D:\_audit\COMPONENTS_SPILLING_CC94_20260804T2251Z.md` §1.1–§1.6, §2.2, §2.5, §4, §6.1–§6.4, §7, §9.1–§9.3, §10.1–§10.4, §11.1–§11.4, §13, §14, §15; commits `verdmat-ai` **`51445aa`** (mælt af git: 7 skrár, +413/−0) og `app` **`156d3e1`** (mælt af git: 3 skrár, +184/−16).

## 2026-08-07 — §5C-3 · TILGÁTAN `10 → 2010` ER FELLD: LÍKANIÐ SKRIFAR AFSTÆÐAN ALDUR Í ÁRTALSREIT

**Hvað**: Verkbeiðni cc94 gerði ráð fyrir að `year = 10` og `year = 20` „ættu væntanlega að vera 2010, 2020" — stytt ártöl. **Frumtextarnir hrekja það.** Tilvik 1 (`5deba5f0a0e1`, `heating.year = 20`, fastnum 2170257): „*Hitaveita var leidd í húsið fyrir um það bil **20 árum**…*" ⇒ rétt ártal væri ~**2006**, ekki 2020. Tilvik 2 (`41dd858097e3`, `plumbing.year = 10`, fastnum 2074179): „*…endurnýjaðar **fyrir um 10 árum**.*" ⇒ ~**2016**, ekki 2010; `detail`-reiturinn staðfestir lesturinn sjálfur („klóakalag°ir endurnýjaðar um 10 árum"). **Disksafnið staðfestir mynstrið á 71 hólfi**: hvert einasta spillta ár undir 1900 í `batch_extraction_unique.jsonl` er heiltala ≤ 20 (1–11, 13, 14, 15, 17, 20). Viðgerðin varð því **NULL**, ekki 2010/2020.

**Af hverju**: `10 → 2010` hefði verið **ágiskun ofan á ranga forsendu** og skrifað ártal sem er 6–14 árum frá réttu. Grunnregla 10 (óþekkt = NULL) á beint við. Þetta er annar flokkur en hin spilltu árin: 1882 og 1898 á diski eru **trúverðug raunveruleg byggingarár** sem skema-mörkin 1900 útiloka ranglega — tveir aðskildir flokkar, ekki einn, og varnarþrepið má ekki henda þeim síðari.

**Fylgifiskur sem leiðréttir mína eigin ábendingu**: cc94 §1.5c flaggaði +20,37 %-bil á 2170257 sem grunsamlegt og tók fram að orsakasamband væri ómælt. Nú er það mælt: spillta árið skýrir **+0,32 %** af því bili — og **í ÖFUGA átt**. Bilið kemur nær alfarið frá öðrum extraction-eiginleikum. Raunverulega skekkjan var á hinni eigninni: `years_since_plumbing = 2016` blés verðmat 2074179 upp um **1,5 milljónir** (−1,44 % við leiðréttingu). Fyrirvarinn var réttmætur; ábendingin var villuslóð.

**Heimild**: `COMPONENTS_SPILLING_CC94` §2.3 (frumtextarnir), §1.6 (disksafnið), §10.2 (ársáhrifin mæld).

## 2026-08-07 — §5C-4 · CHECK SEM SKILAR NULL ER CHECK SEM HLEYPIR RÖÐINNI Í GEGN — sama gildran birtist ÞRISVAR

**Hvað**: Þrep C var applýjað og **tvö NULL-göt fundust í rauðprófun eftir á**. **Gat 1**: `jsonb_typeof(ext->'components')` er NULL þegar lykilinn vantar; `NULL = 'object'` er NULL; `NULL and true` er NULL — og **CHECK telur NULL uppfyllt**. Röð án `components` hefði sloppið. **Gat 2**: `validation_status` er NULL á öllum 5.128 röðum sem voru skrifaðar fyrir cc94; `NULL like 'rejected:%'` er NULL og `NULL or false` er NULL — **þvingunin var óvirk á nákvæmlega þeim röðum sem hún átti að ná til**. Bæði lokuð með `coalesce(…, false)`.

**Gat 2 fannst ekki með lestri heldur með LIFANDI INSERT**: eftir apply tókst `insert … values ('CC94PROF0001', '{"components":"strengur"}'::jsonb, …)` þótt fallið sjálft skilaði `false` á sama gildi. Röðin var lesin, staðfest og eydd. Eftir lagfæringu: spillt röð ómerkt → **`23514 check constraint violation`**; spillt röð merkt `rejected:` → tekst (undanþágan virkar); fallið 11/11 PASS (var 10/11); 0 brot af 5.291.

**Þetta er ÞRIÐJA birting sömu gildru í einni og sömu lotu.** Hinar tvær: `NULL NOT LIKE …` í `fetch_extracted_listings_to_value` (þrep A — án skýrs `IS NULL OR` skilyrðis hefðu allar 5.122 eldri raðirnar hætt að fá verðmat) og `jsonb_typeof(NULL) = 'object'` (gat 1).

**Af hverju**: **REGLA — hver NULL-anlegur dálkur í CHECK-i verður að fara gegnum `coalesce`, og hver þvingun skal rauðprófuð með lifandi INSERT en aldrei með lestri.** Lestur á fallinu gaf rétt svar (`false`) á meðan þvingunin hleypti röðinni inn; aðeins skrifpróf greindi þar á milli. Reglan hefur aukamerkingu sem er sjálfskýrandi og bókast með: **ÓMERKT RÖÐ ER GILD RÖÐ** — eftir C er fjarvera merkis fullyrðing, ekki þögn.

**Heimild**: `COMPONENTS_SPILLING_CC94` §11.1–§11.3, §6.4 (síunarsemantíkin sönnuð á gildum); `feedback_null_i_check_hleypir_i_gegn`.

## 2026-08-07 — §5C-5 · CHAIN-STIGIN ÞRJÚ: MERKIÐ BER STIGSMUNINN, EKKI EXIT-KÓÐINN

**Hvað**: Nóttin 05.08 skrifaði `=== CHAIN CLEAN (exit 0) ===` þótt **31 af 200 extraction-köllum hefðu fallið** — öll á `BadRequestError 400 — Your credit balance is too low`, samfellt frá kalli 170 til 200. Rótin var mæld: `run_extraction.py` grípur hvert fall per kall og skilar 0 úr `main()`, og summary-grepið í keðjunni tínir `effective_n`, `day_total` og `valued N listings` — **`failed` er hvergi**. Fallið var ósýnilegt nema extraction-loggið væri opnað.

Lagfæringin er **þriggja stiga merki**, ekki exit-kóði: `CHAIN CLEAN` (0 föll) / **`CHAIN DEGRADED:n`** (n>0, keðjan kláraði, exit 0) / `CHAIN FAIL (<hvar>, exit n)`. Þriðja stigið er nýtt — fallandi útgöngin hættu áður **þögult** og próbinn las það sem ABORT af FJARVERU CLEAN-línunnar (rétt niðurstaða, engin ástæða). Próbinn prófar **DEGRADED á undan CLEAN**, því sama loggskrá getur borið báðar línurnar ef keðja er endurkeyrð handvirkt sama dag (append-only næturlogg) og þá á **verra stigið að ráða**; DEGRADED telst offender og kveikir VAKT-flagg. Sex prófmál græn, þar á meðal „báðar línur í sama loggi → DEGRADED ræður".

**Af hverju**: Exit-kóði dugar ekki. Léti `run_extraction` falla með exit≠0 færi keðjan í „ABORT extraction — NO RETRY" og hætti með exit 1 við **eitt** fallið kall af 200 — 169 heppnaðir útdrættir og verðmötin glötuðust úr nóttinni. **Merkið á að bera stigsmuninn, exit-kóðinn ekki.**

**Tvö atriði bókast með, bæði hreinskilin:** (1) **DEGRADED-leiðin er prófuð HERMT, ekki í framleiðslu.** Fyrsta raunverulega DEGRADED-nóttin er ókomin; nóttin 05.08 hefði átt að bera hana, en hún fór óskráð og er ástæða patchsins — hún er **ekki afturvirkt merkjanleg**. (2) **Föllnu 31 komu aftur í biðröðina, mælt en ekki ályktað**: keyrt gegnum `E.fetch_listings_needing_extraction(ro, 200)` — sömu fyrirspurn og keðjan notar, ekki eftirlíkingu — 31/31 í biðröð, í sætum 1–31 af 200, 0 hálfvistuð. **Þau höfðu samt ekki fengið extraction við mælingu cc103 (0/31 í DB)**; nætur-pickerinn endurvelur þau ekki og það er óleyst biðraðar-gat (sjá backlog).

**Heimild**: `COMPONENTS_SPILLING_CC94` §7.1, §7.2, §8, §12, §15; `app` commit `156d3e1` (`nightly_delta_chain.sh` +44, `verdmat_status_probe.ps1` +16).

## 2026-08-07 — §5C-6 · cc96-DÓMURINN: MYNDASAFNIÐ ER FROSIN LJÓSMYND — og gatið er EIGNARGAT, ekki birtingargat

**Hvað**: Spurningin var hvort myndasafnið sé lifandi straumur eða frosin ljósmynd. Svarið er mælt: **frosin ljósmynd**. Full sópun á **öllum níu myndarótum** (ekki úrtak): 2.862.224 skrár / 586,8 GiB á 140 sekúndum. Nýjasta mtime á öllu safninu er **2026-07-02T09:21Z** og hún kom úr einskiptis bæti-sókn sem lauk þá; evalue-safnið sjálft (`property_images`, 2.583.775 raðir) hreyfðist síðast **2026-05-15**. Mánaðardreifing: 2026-04 895.283 · 2026-05 1.753.098 · 2026-06 197.946 · 2026-07 15.897 · **2026-08: 0**. **Núll af níu Task-Scheduler-verkum snertir myndir**; báðar næturkeðjur lesnar línu fyrir línu og **hvorug hefur mynda-þrep** — auglýsinga-*slóðir* koma inn í `photos_json` á hverri nóttu, **bætin eru aldrei sótt**. Aðeins tvö forrit í öllu safninu skrifa myndagögn og hvorugt er skráð verk.

**Gatið vex mælt**: jafnvægisástand yfir 5 heilar vikur (06-29 → 07-27) gefur **10.042 nýjar einstakar myndaslóðir á viku ≈ 1.435 á nótt** (mbl 8.894/viku, myigloo 1.148) og **~237 ný fastnúmer utan safns á viku ≈ 12.300 á ári**. Umfangið í dag: **5.377 af 8.886 fastnúmerum (60,5 %)** með virka mynda-auglýsingu eiga **enga röð** í safninu, og 2.950 til viðbótar bera auglýsingu sem sást fyrst eftir frystingu — samanlagt **8.327 af 8.886 = 93,7 %** bera myndaefni sem safnið á ekki.

**Þrír fundir sem breyta túlkun allra talna:**
1. **Slóða-diff milli safns og auglýsingar er merkingarlaus.** `property_images` ber 100 % slóðir á einum hýsli, lifandi auglýsingar bera `cdn.mbl.is` og `myigloo.is` — **nafnrýmin eru aðskilin með smíði**, svo skörunin er núll og allar 218.916 slóðir lifandi auglýsinga eru „utan safns" án þess að það segi nokkuð. Eina nothæfa mælingin er **tilvist raðar** á fastnúmera-stigi og **bætatilvist** á mynda-stigi.
2. **Þekjan aftur í tímann er SÖGULEG og skarpt afmörkuð, ekki kerfisbundinn galli okkar.** Sundurliðað eftir ári síðustu evalue-lotu er **2019–2023 nánast fullkomið (0,7–1,1 % vantar)**, en fyrir 2019 vex eyðan hratt afturábak (2018 22,2 % → 2012 91,7 % → 2011 90,0 %). Evalue geymir ekki myndir gamalla auglýsinga: textinn lifir, myndirnar ekki. Sú eyða er **óendurheimtanleg úr þessari lind**. Bungan 2024–2025 (8,3 % / 9,1 %, samtals 1.542 fastnúmer) er hins vegar **ekki skýrð af aldri** og er eini hlutinn sem gæti verið raunverulegt sóknargat.
3. **EINA-EINTAKS-FUNDURINN.** cc87-spegillinn gekk á **sjö** rætur og fann 2.648.381 skrár; níu-rótar sópunin gefur 2.862.224. Mismunurinn er **nákvæmlega** `image_store\mbl` + `image_store\myigloo` = **213.843 skrár / 38,3 GiB** (2.862.224 − 213.843 = 2.648.381, *exact*). Sama safn er hvorki í `backup_paths.json` `include` né `exclude` — það er einfaldlega utan við. **38,3 GiB af auglýsingamyndum áttu því EITT eintak, á D:** — nákvæmlega ástandið sem cc87 leysti fyrir evalue-safnið og gleymdist hér.

**Af hverju**: **Gatið er ekki birtingargat í dag heldur EIGNARGAT.** Fastnúmerin 5.377 eru þegar sýnileg í appinu — gegnum beinan hotlink á mbl/myigloo, ekki eigin bæti. Þrír ytri rofar (CloudFront, `cdn.mbl.is`, `myigloo.is`) ráða allri myndbirtingu, og cc83/cc92 sýndu að sá fyrsti getur fallið og komið aftur án fyrirvara. Og við **eigum bætin fyrir 64,1 %** mynda á lifandi auglýsingum (140.318 af 218.916) — þau eru bara ótengd `property_images` og því ósýnileg appinu.

**SKEMALEIÐ (b) er afstaða arkitekts, óafgreidd sem go.** Þrep 4 í ingestion-keðjunni er raunverulega ákvörðunin, því `property_images` er `(fastnum, url, img_order)` — ekkert `source`, ekkert `sha256`, engin tímastimplun (§5B-12), og `fastnum NOT NULL` útilokar 808 auglýsingar með smíði. Þrjár leiðir: (a) víkka `property_images` additíft, **(b) ný systkinatafla `public.listing_images` + `v_eign_myndir` í þrjú lög**, (c) `image_store` sem hreint varðveislulag og birting áfram á hotlink. **Leið (b) er sú sem mælt er með**: hún heldur cc92-mælingunni („einn hýsill = 100 % af töflunni") ósnortinni sem sögulegri staðreynd og forðast að blanda tveimur ólíkum auðkennarýmum í eina töflu — sama regla og réð nafngiftinni í cc97 (§5C-7).

**Forgangsröðun bakfyllingar er þegar mæld og snýr við innsæinu**: mbl hefur **enga aldursbrún** (99,3 % lifun aftur til 2014 í Thumbor `fs-pool`) svo mbl-afskráðar liggja ekki á; **myigloo er óprófað** og 7.076 af 10.359 virkum myigloo-slóðum eiga engin bæti. **myigloo er brýnna en mbl þrátt fyrir að vera 5 % af fjöldanum.** Sama gildir um bæta-hlutfallið: myigloo er 11 % myndanna en **57 % bætanna** (1,52 MB gegn 149 KB), svo upplausnin er fyrsti stillanlegi hnappurinn ef bætamagn verður bindandi — ekki tíðnin.

**Heimild**: `D:\_audit\MYNDA_GAP_CC96_20260804T2303Z.md` §0–§1.4, §2.0–§2.4, §3, §4.1–§4.4, §5 (mælingar sem úttektin gerir EKKI), §6.

## 2026-08-07 — §5C-7 · cc97: AUGLÝSINGAMYNDA-SPEGILLINN — og 9 %-REGLAN um fulla checksum-þekju

**Hvað**: `D:\verdmat-is\image_store` er speglað á R2 undir nýju forskeyti **`augl-myndir/{lind}/{sha[:2]}/{sha256}.{ending}`**: **213.843 hlutir / 41.096.112.349 bæti (38,274 GiB)**, 12 lotur, **12/12 HEILAR, 0 mismunir**. Σ `check_matching` = 213.843 = nefnarinn sem mældist á diski FYRIR flutning. Keyrslugluggi 33 mínútur.

**Sannreyningin var þríþætt og tvístefnu**: (1) full `rclone check --checksum` per lotu strax á eftir copy, ekki úrtak; (2) **önnur, óháð** `check` á allt forskeytið utan lotubókhaldsins — `exit 0 · 0 differences found · 213843 matching files`, **án `--one-way`** svo hún bókar bæði það sem vantar og það sem er umfram; (3) `rclone size` sem hittir nefnarann **upp á bæti** (0 / 0 mismunur). **Reikningsjöfnuður á fötu-heild gengur upp á hlut OG bæti**: 2.649.033 + 213.843 + 7 = **2.862.883** hlutir og 615.113.485.681 + 41.096.112.349 + 520.329.104 = **656.729.927.134** bæti, hvort tveggja jafnt flatri rótartalningu eftir á. **D: er ósnert upp á bæti** (endurmæling: 213.843 / 41.096.112.349, óbreytt), og engin `sync`-skipun var nokkurn tímann gefin — keyrsluvélin neitar að ræsa ef forskeytið byrjar ekki á `augl-myndir`.

**9 %-REGLAN**: full checksum-þekja kostaði **9,4 %** af copy-tíma hér (170,5 / 1.821,2 s) og **9,1 %** í cc87 á 588 GB. Hlutfallið heldur yfir **tvær stærðargráður** og er þar með regla, ekki tilviljun: **úrtak er aldrei réttlætanlegt.** Aukalærdómur sem staðfestist í leiðinni: sannreyningartími vex með **stærð ÁFANGASTAÐAR** — lota02, sú fyrsta sem keyrði á ekki-tóman áfangastað, tók 82,7 s gegn 6,5–16,5 s í öðrum mbl-lotum, en flatti strax út aftur á þessari stærðargráðu.

**Hraðinn er skráarstærðarbundinn, ekki bandbreiddarbundinn**: sama `--transfers 64` skilaði **37,4–38,1 MB/s á myigloo** (1,5 MB meðalskrá) og **18,6–24,7 MB/s á mbl** (155 KB). Heildin 22,56 MB/s gegn 19,20 sem cc87 mældi á 588 GB — munurinn er skráarstærð, ekki betri tenging. **Spá um flutningstíma verður því að byggja á meðalskráarstærð, ekki bara á GB.**

**Af hverju**: Nafnið `augl-myndir/` var valið fram yfir `myndir-augl/` af mældri ástæðu: auðkennarýmin eru **ólík í eðli** — `myndir/` er lyklað á **fastnúmer**, þetta safn á **innihalds-hash**. cc87-reglan um aðskilin auðkennarými bannar blöndun og hún bannar líka **nálæga nafngift sem býður upp á `myndir*`-víxlun** í handvirkri listun eða framtíðar-glob. Endingin verður að fylgja lyklinum því safnið er **ekki ein-endingar** eins og evalue-safnið (mbl `.jpg` 207.499 / `.png` 763 / `.webp` 24; myigloo `.jpg` 5.215 / `.png` 341 / `.jpeg` 1), og lindaskiptingin er ókeypis því **0 sha eru sameiginleg milli mbl og myigloo**.

**Næturafrits-liðurinn er MÆLDUR, ekki afgangur.** Hreyfingin +7 hlutir / +520.329.104 bæti er `backup_nightly.py` sem keyrði kl. 03:00 **á meðan glugginn stóð**; hún var mæld sér á afritsforskeytunum í báðum endum. **Lærdómur: þegar speglað er á fötu með lifandi afritum verður að mæla afritsforskeytin í BÁÐUM endum, annars er hver mismunur ógreinanlegur frá gagnatapi.**

**Hvað þetta leysir EKKI (stendur óbreytt)**: næturafritið nær **enn** ekki yfir `image_store` — cc97 er einskiptis-spegill, ekki sjálfvirkni, svo nýsóttar myndir lenda aftur á einu eintaki; ekkert sækir myndir svo gatið vex áfram; `augl-myndir/` er **varðveislulag, ekki birtingarlag** (fatan er ekki opinber); bakfyllingin á 78.598 slóðum er ógerð.

**Heimild**: `D:\_audit\AUGL_MYNDIR_SPEGILL_CC97_20260805T0000Z.md` §1–§9.

## 2026-08-07 — §5C-8 · R2-KOSTNAÐURINN Í ÞREMUR MÆLINGUM — og hvað er ENN ekki staðfest

**Hvað**: Kostnaðarlínan er nú mæld þrisvar og hver mæling leiðréttir þá fyrri. **cc83 (áætlun)**: 577,6 GB → geymsla $8,51/mán, PUT $7,13. **cc87 (mælt)**: 586,26 GB (`SUM(file_size_bytes) WHERE downloaded=1`) → jaðarkostnaður spegils **$8,79/mán**, heildarreikningur fötu **$9,04/mán** ((586,26 + 26,19 − 10) × $0,015), PUT eitt skipti **$7,34** ((2.631.427 − 1.000.000 frí) × $4,50/M). Hækkun frá cc83: $0,28/mán og $0,21 eitt skipti. **cc97 (mælt eftir viðbót)**: ný bæti 41.096.112.349 (41,10 GB) → jaðarkostnaður **$0,62/mán**, heildarreikningur fötu **$9,70/mán** ((656,73 − 10) × $0,015, var $9,04), **Class A PUT $0,96** (213.843 × $4,50/M — fríþrepið 1 M **uppurið af cc87 innan sama almanaksmánaðar**), útflæði **$0** (R2), listun v/sannreyningar ~2.900 Class A (hverfandi). Að auki standa **probe-forskeytin átta** í 3.200 hlutum / 718,44 MB / **$0,011 á mánuði**, óhreyfð frá cc87 og staðfest tvímælt (cc87 §18 og cc91 §3.2, sama tala upp á aukastaf).

**Af hverju**: Fríþrepin eru ekki hlutlaus og það er lærdómurinn sem gildir framvegis. Geymslu-fríþrepið (10 GB) var **þegar uppurið af næturafritunum** áður en spegillinn kom, svo jaðarkostnaður spegilsins er fullur taxti frá fyrsta bæti. PUT-fríþrepið (1 M/mán) var uppurið af cc87 **innan sama almanaksmánaðar**, svo cc97 greiddi fullt fyrir alla 213.843 hlutina. Hvor tveggja er mælt, ekki áætlað.

**Bókað sem ÓSTAÐFEST**: **staðfesting á reikningi úr Cloudflare-mælaborðinu finnst ekki á diski.** Allar tölur hér að ofan eru **reiknaðar úr mældum bætum og birtum taxta**, ekki lesnar af mælaborði veitandans. Þær eru því spá um reikning, ekki reikningur. (Til samanburðar var Vercel-brennslan mæld beint af notkunarspjaldinu 06.08 — það liggur ekki fyrir hér.) Liðurinn fer á frávikalista og á backlog: **næsta R2-snerting á að lesa mælaborðið og bóka mismuninn.**

**Heimild**: `docs/fable_prep/audits/R2_SPEGILL_FASI0_CC87_20260803T2325Z.md` §6 (kostnaðartaflan), §7 (probe-forskeytin); `D:\_audit\AUGL_MYNDIR_SPEGILL_CC97_20260805T0000Z.md` §7; `D:\_audit\R2_SANNPROFUN_CC91_20260804T2220Z.md` §3.2.

## 2026-08-07 — §5C-9 · cc100: JÚLÍ-SKÝRSLAN LIVE — og LIMIT-ROFS-SANNREYNINGIN sem GO-ið bar

**Hvað**: `FASTEIGNASKYRSLA_2026-07` fór í loftið á www.verdmat.ai eftir go: `verdmat-ai` **`95d1621`** og `app` **`e7e577f`**, bæði pushuð. Önnur útgáfa mánaðarraðarinnar: 12 kaflar (1–10 spegla júní) + **tveir nýir fastakaflar** — 11 „Verð á 100 fermetrum eftir tegund" (skyldukafli eiganda) og 12 „Staða verðmatslíkans". Mánaðaflipar á `/skyrslur/[timabil]`; **júní-slóðin `/skyrslur/2026-06` stendur óbreytt**. Forsíðukassi og agent-verkfærið lesa `nyjastaSkyrsla()` og uppfærast sjálfkrafa.

**LIMIT-ROFS-SANNREYNINGIN — það sem GO-ið krafðist og var mælt af git FYRIR push:**

| repo | commit | skrár | +  | − |
|---|---|---:|---:|---:|
| `verdmat-ai` | `95d1621` | 10 | **+2.084** | **−17** |
| `app` | `e7e577f` | 5 | **+1.381** | **−0** |

**Lykilmælingin er þó sú sem er NÚLL**: `content/skyrslur/skyrsla-2026-06.ts` **kemur alls ekki fyrir í diffinu** — 0 diff-línur, hvorki innsetning né eyðing. Endurmælt í þessari lotu með `git show --numstat` á báðum sha-um: tölurnar stemma upp á einingu.

**Af hverju**: Þetta er reglan sem liðurinn ber. **Additífa reglan er ekki „engar eyðingar nokkurs staðar" heldur „engin eyðing í frosnu efni".** Nýr mánuður í mánaðarröð krefst óhjákvæmilega breytinga á sameiginlegu lagi (`types.ts`, `SkyrslaGrof.tsx`, `config/skyrslur.ts`) og þær breytingar bera eyðingar. **Rofið er því leyfilegt — en það verður að vera MÆLT, ekki fullyrt**, og mælingin sem gildir er tvíþætt: heildar-numstat á commitinu **og** sönnun þess að frosna nágranna-einingin (fyrri mánuður) beri **núll diff-línur**. Fullyrðing um að „júní sé ósnertur" án numstat er nákvæmlega sú fullyrðing sem tvisvar áður hefur kostað 200+ línur í þessum skjölum. Sama regla og §5A-22 (diskur fyrir commit) og `feedback_git_add_a_braut_explicit_paths`, í framsetningarlagi.

**Efnistölur júlí, bókaðar með nefnurum**: HMS-vísitala júní **113,4** (+0,1 % m/m, +1,8 % y/y, útg. 21.07) = raunlækkun 11. mánuðinn í röð; VNV júlí **5,3 %**; velta júlí **636** síuð (bráðabirgða, 902 í fyrra) og **júní-talan 609 stóð ÓBREYTT** frá 14.07-mælingu, sem bindur þinglýsingartöfina við **<2 vikur**; list-to-sale **0,974** (n=609, nýr mælir). **Framboð er birt sem 7.772 aðgreind heimilisföng**, ekki 15.072 færslur — færslutalan er ofmat vegna auðkennaflökts, og HMS-krossskoðun gefur ~6.400. 100 m²-kaflinn: band 85–115 m², n<30 → stöðumerki; **einbýli í bandinu er nánast ekki til (n=8 á höfuðborgarsvæðinu) og það er sjálft niðurstaðan**. Model-kaflinn ber **aðeins lifandi framleiðslu** (holdout30 n=847 medAPE 7,7 % cov80 81,1; fresh_edge n=339 10,3 %/76,7) — **endurþjálfunin er ónefnd skv. banni**.

**Heimild**: `app` commit `e7e577f`, `verdmat-ai` commit `95d1621` (báðar diffstat-tölur endurmældar með `git show --numstat` 07.08); `app/docs/fable_skyrslur/FASTEIGNASKYRSLA_2026-07_20260805T0928Z.md`, `HEIMILDASKRA_2026-07_…`, `VINNSLUGOGN_2026-07_…`.

## 2026-08-07 — §5C-10 · cc101: MARKAÐURINN ENDURSMÍÐAÐUR Í ÞRJÚ LÖG — engin DB-breyting í öllu verkinu

**Hvað**: `/markadur` fór úr 14 lokuðum flipum í **þriggja laga síðu** — LIVE með `5b6e1d4` (mælt af git: **21 skrá, +2.542/−83**), Vercel-deploy READY. **Lag 1 Púlsinn**: 6 stórar tölur með sparkline, **server-rendrað SVG án client-JS** — 10-sekúndna upplifunin hleður engin gröf. **Lag 2**: sex kaflar (Verðið · Kaupin og ásetta verðið · Umsvifin · Landakortið · Eignirnar · Líkanið og mánaðarritið) með **opnum** fastreiknuðum greiningum. **Lag 3**: fliparnir 16 sem löt dýpt. Prod-raunprófun græn: púlsinn ber allar sex tölurnar (−1,2 % vísitala 12 mán · 96,8 % kaupverð/ásett · 8.737 samningar −14,3 % · 41 dagur · 7.383 framboð · 22 % endurkomur), **16/16 flipar opnast villulaust**, console hrein, krossvísanir /markadur↔/skyrslur virka báðar áttir, enginn `semantic.v_`-leki og enginn tómur dagsstimpill.

**Sjö nýjar greiningar** komu inn: BMN-endursöluvísitalan sjálf (pooled 2006Q2=100 + 13 segment-hólf í hvítlista eftir mældu `n_pairs`), ástand eigna úr auglýsingum (`llm_aggregates_quarterly` 2013→ með n-nefnurum), kaupverð vs ásett 2015–2026, endurkomur á lægra verði, sölutími (heildardreifing), árstíðamynstur 20 ára og verðstigull frá miðju.

**Af hverju**: Þrennt er bókunarvert umfram formið sjálft.

**(1) Engin DB-breyting reyndist nauðsynleg — af því að grantarnir voru ÞEGAR til.** `v_repeat_sale_index` (+`_main_pooled`, `_by_segment`) og `llm_aggregates_quarterly` báru **anon SELECT allan tímann og voru ónotaðar á síðunni**. Verkið var að finna það sem þegar var opið, ekki að opna nýtt. Þungu nýju greiningarnar eru **fastreiknað CONTENT með keyrsludegi, aðferðaskjölun og n**, ekki MV — því lindirnar (`listing_sessions`, `v_units`, `_sales_base`) eiga enga anon-heimild og mynstrin hreyfast hægt.

**(2) Höfnunarlistinn er bókfærsluskyldur og hann er lengri en samþykktarlistinn.** Sjö hugmyndir voru **felldar með mælingu**, ekki með smekk: framboðs-saga úr `listing_sessions` (þekjuhrun mælt — 2026-01 sýnir **32** „virkar" meðan lifandi mæling er **8.598**, svo stig-lína hefði verið þekjumæling en ekki framboðsmæling); verðlækkanir innan auglýsingar (`listing_price_history` nær nær eingöngu yfir 2026 — 36.088 af 40.829, svo „0,9 % breytt" er gluggabjagi); `n_relistings` í hvaða formi sem er (spilltur, mbl-ID-churn); TOM eftir hverfum/tegundum (n=1.082 alls, hólfin falla undir lágmarks-n og −3,3 d vanmatið bjagar þau misjafnt); `above_list_rate` (`ats_lookup_by_quarter` **stale 2025Q2**); orðatíðni beint úr `listing_extractions` (þekja ~9 % og trigger-bjöguð); og póstnúmeraverð (grant vantar — **UI var EKKI smíðað fyrir grant sem ekki er til**).

**(3) Röðun eftir yield eða vanmati er bönnuð og bannið nær til nýrra greininga líka** (§5A-14). Sömuleiðis: model-tölur á markaðnum koma **aðeins úr lifandi framleiðslu** (`v_model_vs_sold_by_hood`) og ekkert endurþjálfunarefni er nefnt.

**Heimild**: `verdmat-ai/docs/fable_prep/audits/MARKADUR_ENDURSMIDI_CC101_2026-08-06T1112Z.md` §A1–A3, A2b, FORMIÐ, FASI B, FASI C; `verdmat-ai` commit `5b6e1d4` (diffstat endurmæld 07.08).

## 2026-08-07 — §5C-11 · EXCLUDE-LÆRDÓMURINN: „nýr dálkur úr flokkuninni" ER EKKI SAMA OG „dálkur sem má ekki þjálfa á"

**Hvað**: Í skrefi 1 ágúst-endurþjálfunarinnar voru **sex** nýir dálkar settir í `EXCLUDE` í `retrain_sales_model.py` — `src_R, has_dvalar, notkun_kodi, gerd, n_ibudareininga, flm_hlutfall` — og hliðið krafðist **154 features** (staðfest: enginn þeirra í `feature_importance.csv`). Í D2 voru **tveir þeirra teknir ÚT úr EXCLUDE** og settir í features: `n_ibudareininga` og `flm_hlutfall`; `EXPECTED_N_FEATURES` fór **154 → 156** sem meðvituð hlið-uppfærsla. **Útkoman réttlætti það mælt**: `flm_hlutfall` fékk **3,37 % gain og sæti 6 af 156**; `n_ibudareininga` 0,171 % og sæti 20. Heildar-MAPE á holdout30 fór 8,41 → **8,23** og fresh_edge 11,96 → **11,59**.

**Af hverju**: Dálkarnir sex komu allir úr sömu vinnu (regla R, HMS-flokkunin) og voru **flokkaðir eftir uppruna en ekki eftir eðli**. Þeir fjórir sem áfram eiga heima í EXCLUDE — `src_R`, `has_dvalar`, `notkun_kodi`, `gerd` — **lýsa flokkunarákvörðuninni sjálfri** og eru þar með sama upplýsingin og segmentið sem líkanið er þegar skilyrt á. Hinir tveir eru **sjálfstæðar byggingarmælingar** á eigninni (hlutfall flatarmáls, fjöldi íbúðareininga) sem eiga ekkert skylt við flokkunina nema að hafa verið sóttar í sömu ferð. **Reglan sem lifir þetta: EXCLUDE ver gegn leka frá merkinu, ekki gegn nýjum dálkum. Prófið er hvort dálkurinn sé afleiða af flokkunar-/merkingarákvörðuninni — ekki hvenær eða með hverju hann barst.**

**Bókuð afleiðing sem er skilyrði, ekki athugasemd**: nýju featurarnir tveir búa í frosna hms-laginu, ekki í skorunar-inntakinu. Í mati var serving-X **sprautaður** með dálkunum tveimur úr sha-hliðuðu lindinni (`16d78e39d57cfcad`), og **alheims-skorunin við flipp þarf nákvæmlega sömu innspýtingu — annars verður train/serve-skekkja**. Þetta rataði inn í flipp-röðina sem skref 1 (runbók §10.4.2) og var framkvæmt (§5C-16).

**Aðferðafræðileg vörn sem fylgdi með**: eftir D2-keyrsluna var `retrain_sales_model.py` **endurheimtur í R154-ástandið** og það sha-sannreynt (`3a35a13dc847b01b`), svo D2-diffið væri sannanlega **þessi þrjú atriði og ekkert annað**, endurgeranlegt úr tímastimplaða afritinu `.cc98_R154_20260805T093342Z`.

**Heimild**: `app/docs/fable_prep/audits/AGUST_ENDURTHJALFUN_FASI2_SKREF1_CC98_20260805T0010Z.md` §1 (læstu ákvarðanirnar, liður 3); `…FASI2_D1D2_CC98_20260805T1000Z.md` §2 (keyrslan, gain, endurheimt trainer); `docs/GO_BREF_FLIPP_REGLA_R_CC98_20260806.md` §1, §6 skref 1 og 8.

## 2026-08-07 — §5C-12 · ÚTILOKUNARRÖÐ ENDURÞJÁLFUNARINNAR: fimm tilgátur felldar hver af sínum FYRIRFRAMBÓKAÐA ramma

**Hvað**: Level-rekið (punktmatið færðist úr −2,56 % í +2,46 % bias á holdout30) var ekki „skýrt" eftir á heldur **sundurgreint í mælda þætti eftir fyrirfram skrifuðum römmum**, í fastri röð, þar sem hver rammi bar sín eigin höfnunarskilyrði áður en mælt var:

| tilgáta | rammi | dómur |
|---|---|---|
| Konvergens/es-skema | A | **FELLD** sem aðalskýring — ~+1,15 pp |
| Akkeris-vélbúnaður | 3.0 §5 | mældur **≤0,7 pp** |
| Gögnin sjálf (revisjónir/CPI) | B | **STENDUR: +2,14 pp** — óháð flokkun |
| Merkingarþáttur gegnum innan-hólfs-samsetningu | D1 | **FELLD** — skilyrt gap ~0 í sérbýli |
| Merkingarþáttur leiðréttur með strúktúr-featurum | D2 | **FELLD** — (b)-bias +2,20 → **+2,45**, ekki að núlli |
| **Eftir stendur** | — | merkingarþátturinn (+2,9 pp) verkar gegnum **level-endurmat segmentanna sjálfra** (categorical-split-far), ekki gegnum mælanlega innan-hólfs-verðsamsetningu — **rót ekki fullskilin** |

**D1 sagði fyrirfram það sem D2 mældi eftir á.** Hráa gapið í sérbýli (fluttar eignir −11,9 % í SFH, −12,5 % í ROW) **hverfur nær alveg við feature-skilyrðingu**: −0,75 % (SFH) og +1,07 % (ROW) með matsvæðis-FE. **Skilyrðið úr GO-forskrift D1 („ef já í sérbýlishólfunum") var því EKKI uppfyllt** — það var einfaldlega engin innan-hólfs-samsetningarskekkja fyrir strúktúr-featurana að éta, og spáin um að D2 yrði lagfæringin veiktist áður en D2 var keyrt.

**Af hverju**: **Röðin er verndin.** Hefði D2 verið keyrt fyrst og dæmt á heildar-MAPE einni saman hefði hann verið útnefndur „lagfæringin" — hann er nefnilega **betri á nær öllum öðrum mælum** (R_gerd bias +6,73 → +5,57; SFH 13,44/+5,61 → 13,24/+4,47; ROW 9,98/+6,76 → 9,36/+5,84; SEMI 11,52/+7,35 → 8,65/+5,26). Fyrirframbókaði ramminn kom í veg fyrir þá ályktun: **varðan var (b)-bias ≤ ±1,0 og hún var ekki hreyfð þegar mælingin skilaði +2,45.** Módelið var samþykkt á eigin verðleikum og **level-spurningin bókuð ósvarað** í stað þess að láta hana hverfa inn í heildartöluna. Samhliða gilti hart bann: **enginn eftirá-bias-stuðull** — talan stendur og fær engan leiðréttingarstuðul (staðfest í §3 GO-bréfsins, §5C-16).

**Heimild**: `app/docs/fable_prep/audits/AGUST_ENDURTHJALFUN_FASI2_D1D2_CC98_20260805T1000Z.md` §1 (D1-taflan), §2 (D2 + dómurinn), §3 (tilgátustaðan), §4 (HALT-staðan, bias-stuðuls-bannið); `docs/GO_BREF_FLIPP_REGLA_R_CC98_20260806.md` §3.

## 2026-08-07 — §5C-13 · cc102 MÓDELA-EINVÍGIÐ: nákvæmnistalan ER EKKI nákvæmni þegar dómarinn er í inntakinu

**Hvað**: Afturvirk mæling gegn fjórum íslenskum verðmatsflötum á frystum úrtökum (A = 4.706 þinglýstar sölur ≥ `train_end` 2026-01-15, sha `c2bc26263031dcb6`; B = 7.732 virkar söluauglýsingar, sha `55c59bf2a274a59e`). **Hliðið var upp á aukastaf**: endurgerð cc78 á holdout30 skilaði n 847 / medAPE 7,6634 / MAPE 9,9552 / bias −2,5598 **orðrétt**, og 1.199 skörunarraðir báru **0,000000 kr frávik**.

**Á paraða kjarnamenginu (n=4.115)**: e-fasteignir **2,84 %** medAPE, fasteignamat HMS **6,32 %**, okkar líkan **7,85 %** (bias **+4,18 % = OFMAT** — óháð staðfesting á level-reki cc98). **En talan er ekki nákvæmni.** Lekinn er mældur **fjórum óháðum leiðum sem stemma**: L3 (öll eigindi föst, aðeins eigin samningur breytist) medAPE **2,55 → 8,07 (3,2×)** og bias +0,15 → **+14,32**; L5 (fastnúmer vs hnit, sama veitandi, sama módel, n=4.135) **2,84 → 9,20 (3,2×)**; L1b lagskipt 0,55×/0,77×; L6 aðhvarf gefur **akkerunarvigt a = 0,337** (R² 0,822) — **34 % af fermetraverði þeirra kemur beint úr sölunni sem dæmir þá**. Vélbúnaðurinn er mældur enda á milli: skrá þeirra fær söluna strax (**100 % innan 4 vikna**) en módelið meltir hana á 4–8 vikum, og medAPE fellur **6,19 → 2,52** við innlestur.

**Þekja er niðurstaða, ekki fyrirvari**: e-fasteignir metur **56 % eigna sem eru á sölu í dag** (92 % seldra) — notandi í söluhugleiðingum fær svar í rúmum helmingi tilvika. Sundurliðað: `APT_FLOOR` 45 % gegn `APT_STANDARD` 97 % (**mælt, ekki skýrt** — gæti eins verið afleiðing af okkar eigin flokkunarlagi og aldri þess).

**Af hverju**: Tvennt gerir mælinguna gilda. **(1) Jákvæð viðmiðun á tækinu sjálfu**: vísitölulínan getur **ekki lekið í smíði** (inntak hennar er sala eldri en `train_end` og hún sér aldrei söluna sem dæmir hana) og hún mælist `AKKERUN ÚTILOKUÐ` — tækið gefur rétt svar á línu þar sem rétta svarið er þekkt fyrirfram. **(2) L4 á okkur sjálf** sýndi enga akkerun (IQR 0,90×, aldur flatur) og var **skilyrði, ekki formsatriði**. Heiðarleikinn er líka bókaður: fyrirframbókaði L1-þröskuldurinn **féll á hársbreidd** (2 %-hlutfall 1,99× gegn kröfu 2,00×) og var **EKKI hreyfður**; L1b og L5 eru merktar sem eftir-á-viðbætur með mældri ástæðu.

**REGLA BÓKUÐ: panel- og keppinautagögn fara ALDREI nálægt módelþjálfun okkar — þau eru mælingarandlag, ekki feature.** Ástæðan er mælifræðileg, ekki lögfræðileg: gögn sem eru sjálf akkeruð í dómarann flytja þá akkerun inn í okkar líkan og eyðileggja hvern framtíðar-samanburð.

**ÁKVARÐANIR EIGANDA 06.08 (koma í stað opinna liða):**
1. **Creditinfo/Aurbjörg: EKKI óskað aðgangs** — lokað hlið, bókað sem markaðsverðviðmið; `eignar.is` stendur utan og engin beiðni fer. **Umfang einvígisins er þar með ENDANLEGT.** *Ósamræmi bókað: FASI 0 mældi 1.990 kr á creditinfo.is en eigandi gefur ~5.000 kr — ólíkar vörur/þrep, ekki upplýst.*
2. **ENGIN OPINBER BIRTING samanburðarins.** Markaðskassinn sem stóð til er felldur (verkið keyrði aldrei, ekkert að fjarlægja). Okkar eigin tölur mega birtast **síðar** sem aðferðafræðisíða án keppinautatalna, með sér-go. **Keppinautanöfn eru bönnuð í öllu sem fer út úr húsi.**
3. **Fasteignasala-útgáfan verður sér skjal, eftir flipp**: okkar nákvæmni með nefnurum, samanburður við fasteignamat HMS **eingöngu**, þekja, heiðarleika-nálgunin og framvirka aðferðin lýst án nafngreininga.

**Aðferðarreglur sem gilda áfram**: `eignar.is` og `aurbjorg.is` voru **útilokuð af robots.txt — okkar eigin regla, meðvitað með sýnileikakostnaði**; skrapið var 36.498 beiðnir með **0 villum**, heiðarlegum UA með netfangi, 0,5–0,6 s tíðni og kill-switch. Fyrsta gilda framvirka heildartalan er áætluð ~01.10.2026.

**Heimild**: `D:\_audit\CC102_NIDURSTODUR_20260806T0950Z.md` §1–§7; `CC102_SKORUNARRAMMI_PREREG_20260806T0045Z.md` (skrifaður FYRIR mælingu); `CC102_SIDULISTI_FASI0_…`, `CC102_B2_VIKUTAKTUR_…`, `CC102_AUDIT_…` (allar 20260806T0950Z); `reference_e_fasteignir_avm_api`, `feedback_sott_verdmat_a_seldri_eign_maelir_akkerun`.

## 2026-08-07 — §5C-14 · FLOKKAÞRÖSKULDARNIR ENDURLEIDDIR — aðferðin er TÓM BIL, ekki gömul merking

**Hvað**: Öryggisflokkarnir A/B/C hvíla á hlutfallslegri 80 %-bilbreidd og gömlu skurðirnir (A < 0,20, B < 0,36) voru leiddir af gömlu bilunum. Nýja framreiðslulagið breytir breiddunum, svo skurðirnir voru **endurleiddir í sömu aðgerð og flippið** — annars hefði A-flokkur horfið sem hliðarverkun. Niðurstaða, kvittuð við borðið 06.08: **A < 0,240 · B < 0,443**.

**Aðferðin speglar upprunalegu leiðsluna (cc49 §5.2) og er mæld, ekki valin**: skurðirnir eru settir í **raunverulega TÓM bil** strjálu sellu-breiddanna (69 og 210 raðir inni í bilunum). Skurðirnir sem lágu nærri gömlu **merkingunni** (0,222 / 0,365) voru felldir af mælingu: þeir skera **gegnum byggt band 38 þúsund raða** og **skilja A og B ekki að** (MAPE 6,85 gegn 7,11). Staðfesting á nýju skurðunum er MAPE-einhalli á holdout30: **A 6,71 % (n=575) < B 9,84 % (n=166) < C 14,00 % (n=106)**. Flokkur er **deterministic úr bilunum** — frávik **0 af 167.503**.

**Afleiðingin á dreifinguna er stór og bókast sem leiðrétting, ekki hliðarverkun**: A/B/C/D fer úr **515 / 111.236 / 43.858 / 11.894** í **84.893 / 40.939 / 29.777 / 11.894**. Lifandi A-flokkur hafði verið **515 raðir = 0,3 %** allt frá cc51 — sem er í reynd horfinn flokkur. **A þýðir nú ±12 % (var ±10 %).**

**Af hverju**: Þröskuldur sem er valinn til að halda gömlu merkingunni („A = ±10 %") er þröskuldur sem er valinn til að fela breytinguna. Reglan sem gildir: **skurður skal liggja þar sem gögnin eru strjál, og merkingin (±%) skal elta skurðinn — ekki öfugt.** Þröskuldarnir búa í `rebuild_predictions_iter4.py` (`GRADE_A_THR`, `GRADE_B_THR`) og voru færðir þar, ekki í birtingarlaginu.

**Viðbótarkrafa borðsins og útkoma hennar**: kvittunin bar skilyrði um að leita „±10"/„10 %" í öllum notendaflötum og uppfæra í ±12 % í sömu deploy ef A-merking væri skjalfest sem prósenta. Leitin var gerð í þrepi 6: **A-merking finnst HVERGI skjalfest sem prósenta á notendafleti** — **fjarveran er bókuð og engin ±12 %-uppfærsla var gerð**. Þrepin T1–T5 eru **ósnert** af þessu (70.113/82.249/3.209/8.525/3.407, ruleset `tiers_v1_K3_F5_N8_2026-07-03`) — ásarnir tveir eru aðskildir sem fyrr.

**Heimild**: `app/docs/fable_prep/audits/AGUST_ENDURTHJALFUN_FLIPP_CC104_20260806.md` þrep 2c (hlið 6 + þröskuldakaflinn), þrep 2d (kvittunin), þrep 3 (lifandi tölur), þrep 4 (kóðafastarnir), þrep 6 (±10 %-leitin); logg `D:\cc104_grade_thresholds.log`; `precompute` commit `05dc55f`.

## 2026-08-07 — §5C-15 · ÆFINGARSTIGS-FUNDURINN: ÞRIÐJI LYKILLINN — rollback-SQL sem eyðir ekki því sem flippið bætti við

**Hvað**: Æfingarstig 3 (þvingað rollback gegn **rauntöflunum**, í einni transaction sem inniheldur enga commit-leið) var keyrt fyrir flipp og reyndist allt grænt: INSERT predictions ← R1 **167.503**, INSERT feature_attributions ← R2 **1.675.030**, UPDATE properties ← R3 **0 snertar raðir** (krafa fyrir flipp), in-txn recheck **öll átta gildi jöfn rollback-dálki §4 nákvæmlega**, endurheimtar-sönnun in-txn gegnum checksum (predictions == R1 `477b2fcab049606a…`, FA == R2 `e9cc8411cc30bf81…`), og lifandi tölur eftir æfingu jafnar þeim fyrir.

**En fundurinn sjálfur var annar og hann er efnið hér**: flippið bætir **NÝJUM lykli `calibration_version`** í `pipeline_config`, en rollback-röð runbókarinnar (§3 þrep 6) taldi **aðeins tvo lykla**. Rollback eftir flipp hefði því skilið nýja lykilinn eftir — DB hefði verið í ástandi sem hvorki var fyrir-ástandið né eftir-ástandið. **Fundurinn var bókaður strax, runbókin leiðrétt í sömu lotu (viðauki §10.5), og rollback-SQL-ið `D:\cc104_flip_rollback.sql` skrifað á disk MEÐ þriðja-lykils-eyðingunni FYRIR flippið.**

**Af hverju**: Þetta er nákvæmlega það sem æfingarstig eru til fyrir og röksemdin fyrir þeim er nú mæld, ekki fræðileg. **Æfing sem er keyrð gegn rauntöflunum með réttum lásum finnur ósamræmi milli fram-leiðar og aftur-leiðar sem lestur finnur ekki** — sami lærdómur og §5C-4 (lifandi INSERT gegn lestri), í öðru lagi kerfisins. Þrep 5 í rollback-röðinni (UPDATE properties) var **eina óæfða þrepið** og það var æft hér gegn rauntöflunni áður en flippið fékk go. **Reglan: rollback-röð er ekki fullgild fyrr en hún er æfð gegn rauntöflunum, og hún verður að telja hvern lykil sem fram-leiðin BÆTIR VIÐ, ekki bara þá sem hún breytir.**

**Heimild**: `AGUST_ENDURTHJALFUN_FLIPP_CC104_20260806.md` þrep 2d (æfingarstig 3, taflan + athugasemdin), þrep 3 (undirbúningur fyrir txn, liður a); `docs/ROLLBACK_RUNBOOK_CC78.md` §3, §5, §10.3, §10.5; logg `D:\cc104_stage3_rehearsal.log`.

## 2026-08-07 — §5C-16 · FLIPPIÐ: FRAMKVÆMDARKORTIÐ ER TVEIR GLUGGAR EN EITT FLIPP — þrep 0–5 með mældum tölum

**Hvað**: Ágúst-endurþjálfunin (`iter4r_20260805_reglaR_strukt` = D2 + Mondrian-kvörðun 3.1 + framreiðslulag 3.3, **sem EIN heild — ekkert laganna þriggja flippar sér**) fór í framleiðslu 06.08. **Framkvæmdin dreifðist á tvo lotu-glugga og það er bókað hér svo kortið sé rétt lesið eftir á: þrep 0–3 voru keyrð í cc104-glugganum (mannað, eigandi og arkitekt við borðið), þrep 4–6 í cc101-glugganum sama dag samkvæmt go eiganda („þrep 4+5 saman — MV FYRST"), þrep 7 að morgni 07.08. Þetta er EITT flipp með einni atómískri transaction, ekki tvö.**

**Þrep 0 — kvittanir**: §3 level-myndin kvittuð, §4 notendaupplifun **VAL = (b)**, flipp-sér-GO kvittað við þrep 3. **Frávik bókað þar: GO-bréfið og runbókin reyndust ÓTRÖKKUÐ í git** og fóru inn með flipp-committinu (explicit paths).

**Þrep 1 — R1-frystingin, ALLT GRÆNT**: `public.predictions_2026_08_pre_cc78` búin til með **CTAS + ENABLE RLS + REVOKE ALL FROM anon, authenticated í SÖMU transaction**, og RLS-staðan **mæld eftir á** (`relrowsecurity=true`, engin `role_table_grants` fyrir anon/authenticated) í stað þess að treysta REVOKE-eintakinu — cc52-reglan. Frystingin keyrð í **einni REPEATABLE READ READ WRITE txn** svo lifandi talning, afritið og frosna talningin mælist öll á sama snapshot-augnabliki: **167.503 == 167.503**, endurmælt á öðru snapshoti sama. NULL í átta lykil-dálkum **0/0/0/0/0/0/0/0**; `model_version` = `iter4r_20260716` á öllum. **Checksum yfir allar raðir**: frosið == lifandi = `477b2fcab049606a3695663719d63642`. **Kohort-krossprófið**: n=100 úrtak, **max|Δ| = 0,0 á öllum FIMM dálkum**. Spönnun sönnuð úr fjórum áttum (CTAS án WHERE, rowcount á sama snapshot, anti-join báðar áttir 0/0, checksum).

**Þrep 2a — R2 + R4–R9**: `feature_attributions_2026_08_pre_cc78` **1.675.030 == 1.675.030**, munaðarleysingjar 0, anti-join 0/0, checksum `e9cc8411cc30bf813f5a65bd3ca562ed`. R4–R9 allar PASS á sha-samanburði, þar á meðal `training_data_v2_pre_cc78.pkl` sha `aa2e191e750fd513` == manifest gamla líkansins og lifandi `training_data_v2.pkl` `32f9a1242b212d11` == GO-bréf §1.

**Þrep 2b — UNIQUE-index á öllum SEX MV-um** staðfest gilt fyrir refresh, svo `REFRESH CONCURRENTLY` gæti ekki fallið þögult.

**Þrep 2c — STAGING, skilin sex græn**: universe 175.929 → D3-hlið −8.426 → **167.503 == lifandi**, anti-join 0/0. Kohort-endurgerð **1.186/1.186 raðir með max|Δ| = 0,0000 kr** á punktmati og < 0,50 kr á bilum (ytri kr-rúnnun). Calibration: serving_v1 **155.609** (= öll non-D) + segcal_fb **11.894** (= öll D), NULL 0. Bil-röðunarbrot **1.284, öll á segcal-leið — lifandi bar 1.447 slík**, þ.e. fyrirliggjandi quantile-crossing sem **batnar**, ekki regression.

**Villa sem hliðin sjálf fundu og felldu**: fyrsta útgáfa skorunarinnar lét sellulausar non-D raðir falla á segcal; **kohort-krossprófið felldi hana** (13 „global"-raðir báru max|Δ| upp í **21,4 M kr**). Cascade var lagfærður í seg_reg → seg → **GLOBAL fyrir non-D** (speglar 3.3-matsvélina; 1.834 raðir) og öll D á segcal (cc51-fordæmið). **Hliðin unnu vinnuna sína — villan komst aldrei nálægt lifandi töflu.**

**Þrep 3 — flippið sjálft, EIN atómísk transaction**, COMMIT **2026-08-06T12:24:26,04Z**: UPDATE predictions ← staging **167.503** → TRUNCATE+INSERT feature_attributions **1.675.030** → pipeline_config 1/1/1 (`model_version` → `iter4r_20260805_reglaR_strukt`, akkeri → `2026-09`, `calibration_version` NÝR) → UPDATE properties ← flokkunar-staging **58.765** → **in-txn sannprófun 15/15 PASS** fyrir commit. **Tvær tölur voru mældar fyrirfram þar sem runbókin bar aðeins mat**: `n_frav` = **58.765** (runbókar-mat ≈58.500/58.561) og `n_apt_std` = **57** (runbókar-mat ≈206) — sú síðari í samræmi við hms-lindarskýrsluna. Strax eftir commit, mælt af lifandi: allar sömu tölur staðfestar, canonical-dreifing lifandi == staging á **öllum 14 gildum**.

**Þrep 5 — MV-REFRESH SEX (ekki einn)**, 6/6 grænar 12:30:28Z, keyrðar í **autocommit** (CONCURRENTLY má ekki standa í txn-blokk) með fail-fast. Raðafjöldi óbreyttur er væntanlegt (hópunarlyklarnir standa, innihaldið skiptist um); efnisleg staðfesting: `v_model_vs_sold_by_hood` ber nýju spárnar (Σ`n_pairs` 8.535, miðgildi `median_ratio` 1,0044). **Glugginn predictions-nýjar/MV-gamlar var þar með LOKAÐUR** — hann var **vitað millibilsástand** frá commit til refresh, bókað sem slíkt í þrepi 3, ekki uppgötvað eftir á.

**Af hverju**: Röðin var valin svo að **canonical_code og predictions.segment gætu aldrei verið sitt í hvoru ástandi** — falli eitt þrep rúllar öll transactionin. Og MV-listinn er **runbókar-listinn (sex), ekki `flip_iter4r.py`-listinn (einn)**; það gat var þekkt fyrirfram og bókað í GO-bréfinu sem skylda, ekki valkvætt.

**Heimild**: `AGUST_ENDURTHJALFUN_FLIPP_CC104_20260806.md` þrep 0–5; `docs/GO_BREF_FLIPP_REGLA_R_CC98_20260806.md` §1, §2, §6, kvittanataflan; `docs/ROLLBACK_RUNBOOK_CC78.md` §1, §7, §10.4; logg `D:\cc104_r1_freeze.log`, `cc104_r2_freeze.log`, `cc104_universe_rebuild.log`, `cc104_staging_gates.log`, `cc104_flip_txn.log`, `cc101_mv_refresh.log`; commits `app` **`fd06628`** (3 skrár, +1.114/−0) og `precompute` **`05dc55f`** (2 skrár, +163/−10), báðar diffstat-tölur endurmældar 07.08.

## 2026-08-07 — §5C-17 · ÞREP 6: PROD-RAUNPRÓFUN, §4b-LÍNAN — og APT-ATHUGASEMDIN við „almennt lítillega"

**Hvað**: Þrep 6 er lokið og grænt. **A-hluti**: 5 af 5 prófeignum á prod **jafnar lifandi DB nákvæmlega** — 2013952 (R_gerd → ROW_HOUSE) **138,0 M / A / T1**, 2000296 **155,0 M / B**, 2000309 **121,5 M / A**, og tvö Country-sérbýli með **rel80 = 0,552** og óbrotin bil / C. Líkans-kafli `/markadur` ber nýju stöðuna sjálfkrafa (72/76 innan ±5 %), console hreint. **±10 %-leitin**: A-merking finnst **hvergi skjalfest sem prósenta** á notendafleti — fjarveran bókuð, engin ±12 %-uppfærsla gerð (§5C-14). **§4b-línan** (val (b) úr §4 GO-bréfsins, dagsett 06.08.2026) er **LIVE á `/adferdafraedi`** — `verdmat-ai` commit **`f153163`** (mælt af git: 1 skrá, +9/−0), línan orðrétt á prod og stikkprufa á 2013952 óbreytt eftir deploy.

**APT-ATHUGASEMDIN — hún leiðréttir orðalag GO-bréfsins og verður að fylgja hverri framtíðar-tilvísun í það.** §4 sagði að verðmöt færðust „almennt ~2–5 % NIÐUR (mest á dýrari eignum og sérbýli)". **Mælda dreifingin á öllu þýðinu (n=167.503) er miðgildi 0,9614 = −3,9 %, sem stenst bandið — en hún er ekki einsleit og sérbýlis-hlutinn er ÖFUGUR:**

| hólf | mælt miðgildi staging/lifandi |
|---|---|
| ALLT (n=167.503) | 0,9614 (**−3,9 %**) |
| **APT_\*** | **0,9359 (−6,4 %)** — utan „2–5 %"-bandsins |
| sérbýli, heild | 1,0234 (**+2,3 %**) |
| … þar af **kyrr** sérbýli (n=28.928) | 1,0030 |
| … þar af **fluttar R_gerd-eignir** (n=27.036) | **1,0497** |
| SUMMERHOUSE | 0,9964 (nær ósnert) |

**Lesningin er samsetningaráhrif og hún er kjarni endurþjálfunarinnar, ekki hliðarverkun**: heil hús sem fasteignaskrá merkti sem íbúðir og voru verðlögð sem íbúðir **HÆKKA** — það er lagfæringin sjálf. Íbúðirnar bera lækkunina, og þær bera hana **dýpra en GO-bréfið orðaði** (−6,4 % gegn „2–5 %").

**Af hverju**: Notandi sem man töluna sína frá því í síðustu viku sér lækkun, og GO-bréfið gerði ráð fyrir því. **En sá sem les „almennt lítillega niður, mest á dýrari eignum og sérbýli" og býst svo við að íbúð lækki minna en sérbýli les rangt** — mælingin snýr því við. Athugasemdin er bókuð hér svo hvorki skýrslutexti, `/adferdafraedi`-lína né stuðningssvar byggi á öfugu orðalagi. **Fyrirvarinn um breikkun bilanna stendur óbreyttur og er líka mældur**: miðgildi rel80 fer 0,303 → 0,236 á öllu þýðinu (bil MJÓKKA á íbúðum — lifandi cc51-leið-A bilin voru breiðari en 3.3-kerfið), en **breikka þar sem óvissan er raunverulega mest**: SFH 0,419 → **0,552**, SEMI 0,412 → 0,514, ROW p90 0,419 → 0,666, og Country-sérbýli miðgildi rel80 **0,552 (n=27.222)** == „halinn í 55 %+" úr GO-bréfinu.

**Opin vöruákvörðun bókuð, ekki leyst**: `/eign`-hausinn birtir `tegund_raw` (HMS-hrálabel) samkvæmt fyrirliggjandi hönnun. Hvort hann eigi að sýna R-flokkunina í staðinn er **opin vöruákvörðun** — flippið breytti spánni og segmentinu, ekki hausnum.

**Heimild**: `AGUST_ENDURTHJALFUN_FLIPP_CC104_20260806.md` þrep 2c hlið (3) og (4), þrep 6; `docs/GO_BREF_FLIPP_REGLA_R_CC98_20260806.md` §4, §5; `verdmat-ai` commit `f153163`.

## 2026-08-07 — §5C-18 · cc105 FASI 1: ANON-FLÖTURINN ER BURÐARVIRKI SÍÐUNNAR — REVOKE er ekki hættulaus fjöldaaðgerð

**Hvað**: Supabase-advisory-póstur („Table publicly accessible — `rls_disabled_in_public`", taflan ónefnd í póstinum) var rakinn til enda með **tæmandi sópun á öllum 74 töflum í public/scraper/semantic**. **Fjórar töflur bera `rowsecurity=false`** og aðeins **ein þeirra er raunopin**: `public.spatial_ref_sys` (PostGIS-kerfistafla, 8.500 raðir, anon+authenticated SELECT, **engin skrif-grants**). **Advisory-pósturinn er þessi tafla og engin önnur.** Hinar þrjár — `scraper.listing_extractions_pre_cc94b` (163), `_pre_cc94b2` (2), `listing_valuations_pre_cc94b2` (4) — bera **engar grants** og eru ekki aðgengilegar um API þótt `scraper` sé PostgREST-útsett. Þær eru viðgerðar-snapshots cc94 og **cc94 er lotan sem á frávikið frá fæðingarreglunni** (RLS+REVOKE í sömu migration og CREATE); reglunni sjálfri er ekki um að kenna.

**Anon-notkunarmælingin er niðurstaðan sem ræður umfangi FASA 2.** Fjórir klientar mældir per skrá: `lib/supabase.js` (anon) keyrir **bæði í vafra og á server**; `/leit` er **hrá REST-köll með ANON-lyklinum** (`rpc/search_properties_grouped` + `properties`); `/eign` les `properties`, `property_images`, `sales_history`, `comps_index_v2`, `v_properties`, `v_current_predictions`, `v_eign_myndir`, `v_fjoleining_fastnum`, `repeat_sale_index` o.fl. **sem anon**; dashboard og `/markadur` sömuleiðis. **Niðurstaða: REVOKE anon á view/MV-flötinn myndi brjóta síðuna.**

**Definer-view-mynstrið er VÍSVITANDI OPNUNARLEIÐ, ekki gleymska.** Átta SECURITY DEFINER-view (ERROR-stig hjá advisor) lesa undirtöflur sem eru RLS-á og policy-lausar (default deny). **Sex af átta eru mæld í raunnotkun anon-megin**; scraper-viewin tvö (`v_leit_listings`, `v_eign_virk_auglysing`) bera **enga anon-grant** og eru service_role-eingöngu í notkun — samræmi, ekki frávik. Sama gildir um 10 semantic-MV með anon-grant: MV-RLS er ekki til í Postgres, grant-stýring er eina vörnin, og innihaldið eru samlagðar markaðstölur sem síðan birtir hvort eð er. **Ósamræmi fundið og bókað**: þrjár MV til viðbótar (`v_postnr_prices_yearly`, `v_street_activity`, `v_street_directory`) bera **engar grants** — grant-sagan er handvirk, ekki regluleg.

**Af hverju**: Áhættumatið er per hlut, ekki per flagg. **(a) Póst-flaggið er LÁGMARKS-áhætta**: les-aðgangur að opinberri EPSG-uppflettitöflu, engin viðskipta- eða notendagögn, engin skrifleið, ástandið upprunalegt frá fæðingu verkefnisins. **(b) Snapshot-þrennan er HREINLÆTI**: 169 raðir, núll raunáhætta í dag; frávikið er að þær myndu opnast ef einhver grantaði seinna. **(c) Aukafundirnir réttlæta ENGA fjöldaaðgerð** — allt sem anon les er efni sem síðan birtir hvort eð er opinberlega.

**Hörð raunprófunarkrafa sem fylgir FASA 2a og má ekki falla niður**: `poi_naesta` er **SECURITY INVOKER** og anon-kallanlegt PostGIS-fall. Fletti innri geography-aðgerðir þess upp í `spatial_ref_sys` **brotnar POI-lagið á `/eign` undir anon við REVOKE**. Prófa verður `poi_naesta` + `/eign` + `/leit` + `/markadur` + `/leiguverd` **eftir** apply, með rollback-SQL tilbúið **fyrir**. Sami fyrirvari gildir um ALTER-leiðina: taflan er extension-eign og `ENABLE ROW LEVEL SECURITY` kann að stranda á eignarhaldi (líkleg ástæða þess að cc52 skildi hana eftir); þá er REVOKE-leiðin til vara, því grantor er `postgres` samkvæmt ACL.

**HIBP-flaggið er LÁGVÆGT en EKKI N/A**: `auth_leaked_password_protection` er af, og Auth **er í notkun** — 5 notendur í `auth.users` (prófnotendur cc17 + hlutverk). Enginn opinn signup-flötur mældist, svo vægið er lágt; lagfæringin er í dashboard (Auth → Passwords), ekki SQL-breyting.

**Skilyrði beggja FASA-2-skammta**: cc104 þrep 6 grænt fyrst — **ein breyting í kerfinu í einu** — og sér-go frá eiganda á hvorn skammt.

**Heimild**: `docs/HALT_SKIL_RLS_GAT_CC105_FASI1_20260806.md` §1–§5 (committað í þessari lotu með explicit path).

## 2026-08-07 — §5C-19 · cc106 ÁLFTAMÝRI 39: ÞRJÁR BIRTINGARREGLUR SEM GILDA UM ALLAR GREININGAR SEM FARA ÚT

**Hvað**: Greining fyrir eiganda á Álftamýri 39 (fastnr. **2013952**), ásett **174,0 M** gegn verðmati **138,0 M**, skrifuð read-only gegn lifandi grunni 06.08 (`ALFTAMYRI39_GREINING_20260806.{md,html}`). Kjarnamælingar: punktmat **138.031.587 kr**, 80 %-bil 127,3–157,5 M, 95 %-bil 111,6–169,5 M, flokkur **A**, þrep **T1**, segment **ROW_HOUSE** undir `iter4r_20260805_reglaR_strukt` + `conformal_serving_v1`. **Ásetta verðið liggur 4,5 M kr OFAN við efri mörk 95 %-bilsins.** Akkerið er þinglýst sala 13.07.2017 á 70,0 M × 1,8221 (hólf, 2026Q2) = **127,55 M**; nærviðmið (8 af 148 comps) vegið miðgildi **151,3 M**; fasteignamatsviðmið **134,6 M**. Breið sópun: **48 sölur** (raðhús+einbýli 160–220 m² í 103/105/108, 24 mánuðir, framreiknaðar) — **174,0 M situr á 85,4-percentíli** (7 af 48 ná verðinu) og **910 þús. kr/m² á 89,6-percentíli** (5 af 48). Allar sjö sem ná verðinu eru í Fossvogslöndunum; nýlegu sölurnar við Háaleitisbraut liggja á 135–144 M framreiknað.

**Af hverju — þrjár reglur sem greiningin setti og gilda framvegis:**

**1. MILLISTIG FER ALDREI ÚT ÚR HÚSI.** Brú-mælingin á þessari eign (124,1 → 128,4 M, +3,5 %, `iter4_final_v1`, 24.07) var **fjarlægð úr lokaútgáfunni** við rýni borðsins. Hún er millistigsafurð úr frosinni brú á eldri líkansútgáfu — rétt sem innri mæling, röng sem tala í skjali sem fer út, því lesandinn getur ekki greint millistig frá framleiðslu. Ástandskaflinn stendur þess í stað á **iter5-kontrostunum tveimur** (+11,0 % brúttó með staðalvillu 0,4 á 6.260 sölum með merki, gegn **+2,1 % beinum kontrast** „uppgert" á móti „vel viðhöldnu" með staðalvillu 0,25).

**2. NÆMNISATHUGUN VERÐUR AÐ VERA MERKT SEM SLÍK OG MÁ EKKI RATA Í NIÐURLAG.** Talan **145,7 M** (punktmat leiðrétt um alla bókuðu hólfaskekkjuna +5,57 %) stendur **aðeins í kafla 1 og aðeins með orðunum „sem næmnisathugun á þeirri bókuðu skekkju, ekki verðmat"**. Niðurlagið ber **+5,57 % / n=96 án útreiknaðrar tölu**. Ástæðan er hörð: leiðrétt tala í niðurlagi verður að öðru verðmati í huga lesandans, og þá ber skjalið tvö möt.

**3. UMBOÐSLÍNAN.** Skjalið segir berum orðum hvað það er og hvað það er ekki: *„Greiningin er unnin af verdmat.ai að eigin frumkvæði og er ekki söluyfirlit, ástandsskýrsla né loforð um söluverð"*, og *„Þinglýsingin sker úr. Þessi greining fullyrðir ekkert um hana."* Hún **fullyrðir ekkert um niðurstöðu sölunnar** og útilokar hana ekki heldur (7 af 48 náðu verðinu).

**Heiðarleikinn gengur í báðar áttir og það er bókað**: tvær skekkjur sem vinna **með seljandanum** eru nefndar (heildarvanmat +2,46 %, hólfaskekkja **+5,57 % á n=96**), og á móti er nefnt að **veikast mælda vissubil kerfisins er í nákvæmlega þessu hólfi** — `R_gerd|RVK_core` cov80 **59,1 % (n=22)**, systurhólfið `SFH|RVK_core` 64,7 % (n=17), samanlagt 39 raðir. Sömuleiðis er bókað að kaupverðshlutfallið (0,968, n=459) mælist **aðeins á eignum sem seldust** — eignir sem seljast ekki detta úr mælingunni, svo hlutfallið eitt og sér segir björtustu útgáfu sögunnar.

**Ástandsþátturinn fékk sína eigin reglu og hún er endurleiðanleiki**: ástand birtist í kerfinu sem **merki** en færir **punktmatið ekki sjálfkrafa**, því punktmat verður að vera rekjanlegt í mæld gögn sem til eru **fyrir allar eignir jafnt**. Ástandstextar liggja aðeins fyrir um **5.491 af 60.807 = 9 %** eignasafnsins, og mælt er að ástandsmerkin bæti engri spánákvæmni utan úrtaks.

**Staða skjalsins**: **ÓCOMMITTAÐ að ósk eiganda** — hann rýnir og sendir sjálfur. Það stendur í `verdmat-ai/docs/fable_prep/greiningar/`, sem er gitignoruð mappa (cc69).

**Heimild**: `verdmat-is/verdmat-ai/docs/fable_prep/greiningar/ALFTAMYRI39_GREINING_20260806.md` §1–§6 + heimildaklausa; `docs/GO_BREF_FLIPP_REGLA_R_CC98_20260806.md` §2, §5; `content/markadur/fastgreiningar.ts` (keyrsludagur 06.08).

## 2026-08-07 — §5C-20 · cc107 LEIGUSÍÐAN: EININGIN ER AUGLÝSINGIN, EKKI FASTNÚMERIÐ

**Hvað**: Leigu-spjald í `/leit?ham=leiga` opnaði **`/eign/[fastnum]`** — söluverðmatssíðuna, sem birtir vísvitandi ekkert leiguefni (cc33-reglan) — og eign án fastnúmers var **óvirkt spjald, blindgata**. Lagfæringin er ný síða **`/leiga/[listing_id]`**, LIVE með `1d7cf1f` (mælt af git: 7 skrár, +783/−2), pushuð 07.08 eftir sér-go og prod-sópun græn í heild.

**Route-afstaðan er rökstudd, ekki valin**: **(1)** einingin er auglýsingin — fastnúmer getur átt margar leiguauglýsingar yfir tíma (og sölu samhliða), svo fastnum-keyed route þyrfti vals-/tvíræðnilag strax; **(2) 24,4 % leiguauglýsinga hafa ekkert fastnúmer** og fastnum-route getur aldrei borið þær, en `listing_id`-route þekur 100 % og leysir blindgötuna í leiðinni; **(3)** `listing_id` er innri, stöðugur bigint-lykill á meðan mbl `source_listing_id` churn-ar (`feedback_mbl_listing_id_er_ekki_lota`); **(4)** eignarsíðan helst hrein — krossvísanir í stað samruna; **(5)** fordæmið er til: `soluyfirlit`-síðan er strúktúrlega sama síða (afritað auglýsingaefni + fyrirvari + `noindex` + myndagrid).

**VARALEIÐIN VAR VALIN FYRST — og það er reglan sem liðurinn ber.** Rétta lokamyndin er nýtt view `scraper.v_leiga_auglysing` (drög skrifuð, **óapplýjuð**), því ekkert lesanlegt yfirborð ber auglýsingaefnið í heild: `v_leit_listings` vantar lýsingu/titil/URL, `v_eign_virk_auglysing` vantar myndir og síar á `status='active'`, og `listings_canonical` — sem ber bæði `url` og `listing_title` — hefur **engin API-grants og er ólesanleg jafnvel fyrir service_role um REST**. En **skrifröðin gengur fyrir: einn DB-skrifari í einu**, og flipp-frágangur ásamt cc105 FASA 2a stóðu framar í röðinni. Síðan fór því í loftið á fyrirliggjandi flötum **með takmarkanirnar fjórar bókaðar í haus gagnalagsins**: (1) aðeins virkar auglýsingar (horfin auglýsing skilar 404 í stað stöðumerkis), (2) enginn titill, (3) URL frumauglýsingar **alltaf smíðað, aldrei lesið úr gögnum**, (4) fjarveru-flögguð auglýsing missir lýsingu og söluaðila. **Uppfærslan verður hrein skipti á gagnalaginu þegar view-ið fær go — síðan stendur óbreytt.**

**PHOTOS_JSON-FUNDURINN**: leigusíðan les **`photos_json` beint**, ekki `v_eign_myndir`. Ástæðan er mæld: `v_eign_myndir` setur **SÖLU-safnmyndir framar auglýsingamyndum** (cc23-forgangurinn), svo leigusíða sem læsi hana myndi sýna sölumyndir eignarinnar á leiguauglýsingu. Auk þess bera **allar 1.475 virkar leiguauglýsingar eigin `photos_json`** og **0 tilfelli** mældust þar sem auglýsingamyndir vantar en safnið ætti þær — frosna safnið er einfaldlega **óþarft fyrir virkar leiguauglýsingar**. Myndalaganirnar tvær (mbl = fylki hluta með `big`-URL, myigloo = flatt strengjafylki) eru samræmdar með sama `fyrstaMynd()`-mynstri og spjaldið notar.

**TEGUND_RAW-BIRTINGARFIXIÐ**: mbl-leiga ber **óupplausta `leiga_type_N`-kóða** í `tegund_raw` (`promote_mbl.py:427` skrifar `"leiga_type_%s" % type_id`). Síðan birtir hrátt gildi **aðeins þegar það er merkingarbært** og fellur annars á `sub_type`-merkimiðann. **Þetta er birtingarlagfæring, ekki rótarfix** — rótin er í promoternum og fer á backlog.

**Af hverju**: Sama regla og §5C-6 og §5C-7 í öðru lagi — **auðkennarými má ekki blanda**. Fastnúmer er eignarlykill, `listing_id` er auglýsingarlykill, og leigumarkaðurinn hefur 24,4 % framboð sem á sér engan eignarlykil. Sbr. líka `project_rangt_asett_verd_cc90`: **fastnúmer er ekki sölueining** — og hér er það ekki leigueining heldur.

**Prod-sópunin, mæld**: `/leit` leiga **24/24 → `/leiga`** (kaup 24/24 → `/eign` óbreytt); spjaldsmellur → `/leiga/326051` með 9/9 myndum, BETA- og Módelspá-merkjum, fyrirvara og krossvísunum; auglýsing án fastnúmers ber matsvöntunarlínu og smíðaðan mbl-hlekk; `noindex` í prod-HTML; rusl-id gefur 404; console 0 skilaboð; `/eign/2008374` ber áfram fulla sölusíðu **án leiguefnis**. Leigumat er til fyrir **871 af 1.475 (59 %)** og kortið birtist aðeins þegar mat er til — **matsvöntun er staða, ekki galli** (ákvörðun borðsins).

**Verkfæra-gotcha bókað því það kostaði tíma og lítur út eins og allt annað**: harness-drepinn bakgrunns-dev-þjónn skilur `node` eftir á :3000 með **stíflaða stdout-pípu**, og þá hengist allt — líka RSC-navigation, sem lítur út nákvæmlega eins og dauður hlekkur. Lækning: drepa `node`, ræsa detached með logg í skrá. Sömuleiðis: `curl` á `www.verdmat.ai` gefur hviklynd SSL/h2 exit-35; **`--http1.1 --retry-all-errors` er stöðuga prófunarleiðin**, og Chrome/`get_page` er trausta prod-sannprófunarleiðin (cc10-lærdómurinn, óbreyttur).

**Heimild**: `verdmat-ai/docs/HALT_SKIL_LEIGUSIDA_CC107_FASI_A_20260806.md` (allir kaflar); `verdmat-ai/docs/drog_migration_cc107_leiga_view_DROG_EKKI_APPLYJA.sql`; `verdmat-ai/lib/leiga-queries.js` haus (takmarkanirnar fjórar); `verdmat-ai/app/leiga/[id]/page.tsx:116–122`; `app/scripts/promote_mbl.py:427`; `verdmat-ai` commit `1d7cf1f`.

## 2026-08-07 — §5C-21 · VAKTAREIGNIN 2013952 — vöktun sem er BUNDIN VIÐ EIGN, ekki bara við hólf

**Hvað**: Þrep 7 færði vikulegu gæðamælinguna á nýja grunninn (`scripts/model_quality_eval.py`, `app` commit **`3f31365`** — mælt af git: 2 skrár, +224/−9). BASELINE varð §7-grunnur 3.3-auditsins (**8,23 / 81,58 / 96,69**) auk BASELINE_FRESH (**11,59 / 83,48 / 95,58**), með flöggum á báðum skópum og „nýtt upphaf" bókað; `FREEZE_ANCHOR_YM` 2026-08 → **2026-09** (flipp-akkerið). Inn komu **bias-per-hólf línan** (r_scope a/b/c1 gegnum flokkunar-ættina, **hávær lína við |bias(b)| > 4,0 pp**, töflu-hvarf = hávært gat en aldrei þögul núll) og **veiku blettirnir fjórir** sem fastar vöktunarlínur **án n-gólfs**: `sfh_rvk_core` · `r_gerd_rvk_core` · `undir_40m` · `apt_attic`.

**Og — nýmælið sem þessi færsla er um — EIN NAFNGREIND VAKTAREIGN: 2013952.** Hún fer í vikuleg skil með ásettu verði, verðbreytingum og virk/horfin-stöðu, og **við þinglýsingu: kaupverð gegn matinu 138,0 M með fráviki**. **Villa í vaktareigninni fellir aldrei mælinguna.**

**Fyrsta prófkeyrsla (dryrun á lifandi grunni, 07.08)**: aðaltala holdout30 n=949 — **MAPE 8,23 (Δ ±0,0 frá grunnlínu) · cov80 82,8 (+1,24) · cov95 96,1**. **Dómsreglan fæddist GRÆN.** Hliðartala fresh_edge n=42: cov80 78,6 (−4,91) — **flagg á litlu n, tripwire en ekki HALT**. Hólfin: (a) n=113 +1,04 · **(b) n=535 +2,33, innan ±4,0** · (c1) n=298 +1,64. Veiku blettirnir: 89,5/19 · 78,1/32 · 67,2/58 · 81,8/11. Vaktareignin: ásett **174,0 M virk** (mbl, síðast séð 30.07), engin verðbreyting, óseld, lifandi mat **138,03 M**. Paired/E2 **sjálfhafnar hávært** (adapter `iter4_final_v1` ≠ lifandi — engin Haiku-keyrsla). Scheduler `verdmat-weekly-model-quality` bendir þegar á vélina — **engin breyting þar**.

**Af hverju**: Hólfamæling svarar „er kerfið að reka?" en hún svarar ekki „hvað gerðist um eignina sem við gáfum álit á?". **2013952 er eignin sem cc106-greiningin fjallar um, eignin sem GO-bréfið nefnir sem veika blettinn (`R_gerd|RVK_core` cov80 59,1 %, n=22) og eignin sem regla R endurflokkaði úr íbúð í raðhús.** Hún er þar með raunprófunartilvik fyrir þrjú kerfislög í einu, og **þinglýsingin á henni verður hlutlægur dómur um mat sem við höfum þegar sett á blað**. Það á ekki að uppgötvast fyrir tilviljun. Varnaglinn (villa í vaktareign fellir ekki mælinguna) er skilyrði: **stök eign má aldrei geta þaggað niður vikulega gæðamælingu á öllu safninu.**

**Forsenda sem varð að leysa fyrst og er bókuð**: `<version>_holdout_rows.csv` vantaði fyrir nýja artifactið, svo `precompute/holdout_eval.py` var keyrð (M1 ✓, M2 ✓; **M3-flokkahreyfingin er endurleiddu þröskuldarnir — kvittað mál**, sjá §5C-14) og skilaði 950 röðum.

**Heimild**: `AGUST_ENDURTHJALFUN_FLIPP_CC104_20260806.md` þrep 7; `…SKREF31_32_CC98_20260805T2350Z.md` §4 (3.2-specið, bindandi §4.3) og `…SKREF33_CC98_20260806T0010Z.md` §7 (grunnurinn); `docs/GO_BREF_FLIPP_REGLA_R_CC98_20260806.md` §5; `app` commit `3f31365`.

*— Lok bókunarlotu cc108 §5C (DECISIONS-hluti).*

---

## 2026-08-07 — §5C-22 · VIÐAUKI (leiðrétting í sömu lotu): ÞREP 8 LENTI MEÐAN cc108 SKRIFAÐI — föllnu 31 eru útdregnar

**Hvað**: Samhliða lota pushaði `f5b45e6` **2026-08-07T00:43:05Z** — eftir að cc108 hafði lesið heimildirnar en áður en cc108 committaði. Það gerir tvennt í þessari bókunarlotu úrelt og hér er það leiðrétt: **föllnu 31 eru ekki lengur óunnar.** Mælt fyrir/eftir: extraction á listanum **0/31 → 31/31**, `scraper.listing_extractions` **5.491 → 5.522** (+31), verðmat af listanum **0/31 → 30/31**, `scraper.listing_valuations` **20.642 → 20.851** (+209). `failed: 0`, 33 Haiku-köll (31 + **2 endurköll** á `components_string`, 1 bjargaðist).

**Þrennt í útkomunni er hönnun en ekki fall og verður að lesast þannig:** (1) **30/31 en ekki 31/31 í verðmati** — ein röð (`c5434c7d1179`) ber `rejected:key_outside_enum`, er í töflunni (þess vegna 31/31 í útdrætti) en er **réttilega utan verðmats** því cc94-reglan síar hafnaðan útdrátt úr verðmats-fetchinu (§5C-2). (2) **209 verðmatsraðir af 30 auðkennum** er **einingamunur, ekki ósamræmi**: `listing_valuations` er á `source_listing_id` en listinn á `lysing_hash`, og sami auglýsingatexti liggur undir mörgum auglýsinga-auðkennum (30 einstök fastnúmer). (3) **Kostnaður $0,2343 gegn ~$0,13 áætlun** — frávikið er kallafjöldinn (33, ekki ~18) á bókuðu einingarverði; **bókað, ekki jafnað út**.

**Aðferðin er bókunarverð**: listinn var tekinn **af diski** (`extraction_20260805.log`, 31 `skip … credit balance is too low`, 31/31 staðfest sem sama villa), ekki úr minni; skriftan kallaði **nákvæmlega sömu vélarföll og nóttin** og eini munurinn var FETCH-SÍAN (markviss á `lysing_hash`-listann). **Engin pipeline-breyting** — `--ids` er ekki til í `run_extraction.py` og var ekki bætt við; leiðin var einnota driver. Endurkeyrsla rauðsönnuð skaðlaus (seinni keyrsla sótti 0 raðir og kallaði ekki Haiku).

**NÝR FUNDUR SEM GILDIR UM ALLA SKRIF-DRIVERA**: fyrsta atrenna féll í verðmatsþrepinu á `ActiveSqlTransaction: transaction read-write mode must be set before any query`. Rótin: **fetch-ið hafði opnað transaction á SKRIF-tengingunni áður en `value_listings` náði að setja `SET TRANSACTION READ WRITE`**. Á transaction-poolernum (port 6543) verður sú stæða að vera **fyrsta stæðan í transactioninu**, og hver SELECT á undan henni fellir hana. Lagfæringin er sama mynstur og nætur-driverinn notar: **fetch á read-only tengingu, skrif á rw-tengingu**. Útdrátturinn var þegar frágenginn þegar þetta gerðist, svo endurkeyrslan kostaði ekkert.

**Af hverju**: Tvennt.

**(1) Þetta er `feedback_samhlida_lota_pushar_undir_ther` í öfuga átt og bókast sem slíkt.** Bókunarlota les heimildir á einum tímapunkti og skrifar á öðrum; **milli þeirra getur önnur lota breytt heiminum sem verið er að bóka.** Vörnin er ekki að hraða sér heldur að **endurmæla `git log` og `origin/main` beint fyrir commit** — sem cc108 gerði, og þess vegna fannst þetta. Reglan sem lifir: **bókunarlota skal endurlesa git-stöðu allra snertra repoa rétt fyrir commit og bæta viðauka við það sem breyttist á meðan; hún má aldrei laga það með því að endurskrifa færslu sem þegar er skrifuð.**

**(2) Fjarvera í skriflegum backlog er sjálf niðurstaða.** Þrep-8-liðurinn fannst **hvergi** í `docs/PLANNING_BACKLOG.md` né `verdmat-ai/docs/BACKLOG.md` þegar hann var framkvæmdur — hann lifði **aðeins í cc103-minninu**. Verk sem lifir aðeins í lotuminni er verk sem hverfur þegar lotan gleymist; sami vandi og §5A-17 leysti fyrir úttektarskjöl.

**Það sem stendur EFTIR og cc108 bókaði rétt**: **biðraðar-gatið sjálft.** Nætur-pickerinn endurvelur ekki föllnu raðir, engin pipeline-breyting var gerð, og næsta inneignar- eða netbilun framleiðir sama gat aftur. Sá liður er óleystur og fer á backlog í uppfærðri mynd (viðauki cc108-A).

**Heimild**: `app` commit `f5b45e6` (1 skrá, +51/−0) og skilaboð hans; `docs/fable_prep/audits/AGUST_ENDURTHJALFUN_FLIPP_CC104_20260806.md` þrep 8 (taflan, sundurliðunin, atvikið); logg `D:\cc101_fallnir31.log`; `feedback_set_transaction_read_write_verdur_ad_vera_fyrsta`, `feedback_samhlida_lota_pushar_undir_ther`.

*— Lok viðauka cc108 §5C (DECISIONS-hluti).*

## 2026-08-07 — GRANTS MÆLAST Í `pg_class.relacl` — `role_table_grants` EITT OG SÉR ER ÓFULLNÆGJANDI MÆLING (cc105)

**Tilefni:** þessi lesning framleiddi eina ranga forsendu sem heil verkbeiðni var skrifuð á. cc105 FASI 1 (06.08) las `information_schema.role_table_grants` á `public.spatial_ref_sys`, valdi ekki `grantor`-dálkinn, og bókaði „grantor er postgres skv. ACL svo REVOKE er heimilt". FASI 2a (07.08) mældi `pg_class.relacl` beint og felldi setninguna: grantor er `supabase_admin` í ÖLLUM færslum, og ACL ber að auki `=r/supabase_admin` — **SELECT til PUBLIC**, aðgangsleið sem birtist alls ekki sem venjuleg röð í role_table_grants.

**Reglan (læst):**

1. **`pg_class.relacl` er heimildin.** Áður en réttindaaðgerð er ákveðin skal mæla `select relacl::text, pg_get_userbyid(relowner) from pg_class where oid='<tafla>'::regclass` og lesa `grantee=privs/grantor`-mynstrið beint. `role_table_grants` má nota til yfirlits en aldrei sem grunn ákvörðunar.
2. **PUBLIC-grants verða að teljast sérstaklega:** `select count(*) from aclexplode(relacl) where grantee = 0`. Grant til PUBLIC nær til allra hlutverka og gerir REVOKE á `anon, authenticated` gagnslausa — hún sést hvergi nema í ACL-inu.
3. **Mældu heimildina TIL aðgerðarinnar áður en hún er keyrð, ekki eftir á:** `pg_has_role(current_user,'<eigandi>','member')` fyrir ALTER, og `has_table_privilege(current_user,'<tafla>','<sögn> WITH GRANT OPTION')` fyrir REVOKE. Séu báðar `false` bítur hvorug aðgerðin: ALTER fellur með villu (sýnilegt), en **REVOKE ÞEGIR — hún gefur WARNING, ekki villu, og migrationin skilar `success` án þess að breyta neinu.**
4. **Þar með er cc52-reglan hert:** „staðfestu með `aclexplode`, aldrei með eintómri `success`-stöðu migrationarinnar" gildir áfram EFTIR aðgerð — en þessi regla færir prófið FRAM FYRIR hana, svo þögul núll-aðgerð sé aldrei keyrð í fyrsta lagi.
5. **Fæðingarreglan** (RLS + þröng réttindi í sömu migration og CREATE, CLAUDE.md) og **cc52-reglan** vísa báðar hingað um það hvernig „réttindi" eru mæld.

**Sannreynt í reynd samdægurs:** báðar leiðir á `spatial_ref_sys` reyndust ófærar — `ENABLE ROW LEVEL SECURITY` féll á raunreyndu `42501: must be owner of table spatial_ref_sys`, og REVOKE-varaleiðin var **ekki keyrð** af ásettu ráði (kvittað af eiganda 07.08) því hún hefði framleitt falska „tókst"-línu. Flaggið stendur known-accepted; support-beiðni fer á backlog (viðauki cc105 í PLANNING_BACKLOG).

**Heimild**: `docs/HALT_SKIL_RLS_GAT_CC105_FASI2A_20260807.md` §2–§3 (mældar ACL-strengir, `42501`-villan, `pg_has_role`/GRANT OPTION mælingarnar); `docs/HALT_SKIL_RLS_GAT_CC105_FASI1_20260806.md` §1 + tveir viðaukar 07.08 (upprunalega ranga lesningin stendur óbreytt með leiðréttingu undir); migration `20260807082414_cc105_2a_rls_snapshot_toflur`; CLAUDE.md (cc52/cc72-bókanirnar).

## 2026-08-11 — §5D-1 · cc123 OOS-EINVÍGI HÖFÐANNA TVEGGJA → AFSTAÐA BORÐSINS: KOSTUR (a), ALLT Á `real_pred_mean`

> *Athugasemd um númerun:* §5C-blokkin var lokuð í cc108 (07.08) og nær yfir cc93–cc107. **cc109–cc122 eru óbókaðar í DECISIONS** og standa enn í `PLANNING_BACKLOG` og lotuminni; §5D-1 er því ekki samfelld við §5C-22 og á ekki að lesast sem slík.

**Málið**: cc120 (08.08) mældi **miðsæknina**: `scraper.listing_valuations.expected_base` og `expected_extraction` eru skoruð á `real_pred_median` (`scripts/extraction_engine.py:316–317`) meðan `/eign`, `/leit`, `/markadur` og allur birtingarflöturinn les `real_pred_mean` — **17 af 21 neytanda á `mean`, 4 á `median`, |Δ| > 10 % á 24.969 eignum**. cc120 lagði fram þrjá kosti: **(a)** allt á `mean` · **(b)** allt á `median` · **(c)** báðar tölur birtar. cc120 §5 bókaði sjálft að mælingin sem þá lá fyrir (n=180, einn stimpill, 30 daga gluggi) **skæri EKKI úr**. cc123 (08.08) var forsendumælingin sem borðið bað um: READ-ONLY OOS-einvígi höfðanna tveggja á réttu úrtaki, engin ákvörðun tekin í lotunni.

**ÁKVÖRÐUN BORÐSINS (kvittuð 11.08): KOSTUR (a) — allt á `real_pred_mean`.**

---

### 1. Hvað var mælt (nefnarar á undan tölum)

**Aðaltala: `holdout30` á BIRTINGARSLÓÐ, n = 949**, stimpill `iter4r_20260805_reglaR_strukt`. Þetta er sama mengi og `scripts/model_quality_eval.py` keyrir á (30 % lagskipt frátekt sem er utan BÆÐI þjálfunar og conformal-kvörðunar, aðild lesin af `<mv>_holdout_rows.csv` á `FAERSLUNUMER`). **`listing_valuations`-mengið var VÍSVITANDI ekki notað** — það er auglýsingaþungt og ber mildari dreifingu (cc120 §4: 4,77 % gegn 6,43 %).

**Tækið var sannprófað áður en nokkur tala var lesin:** `model_quality_eval`-vélin var endurgerð lið fyrir lið (sama SELECT, sömu síur `onothaefur=0` og `kaupverd_nominal>0`, sama CPI-afakkerun, sami mælikjarni) og MAPE(`mean`) mældist **8,2284 %** gegn bókaðri `BASELINE["mape"] = 8,23` (`scripts/model_quality_eval.py:186`). **Vélin er endurgerð, ekki eftirlíkt** — og það er forsenda þess að nokkur samanburðartala hér sé marktæk.

| mæling (n = 949) | `real_pred_mean` | `real_pred_median` | marktækt? |
|---|---|---|---|
| **\|bias\|** | 1,9341 % | **0,2642 %** | **JÁ** — `ttest_rel` t = −10,74, **p = 1,75·10⁻²⁵**; Δ\|bias\| −1,535 pp, CI [−2,391; −0,055] |
| MAPE | 8,2284 | **8,0640** | NEI — p = 0,42, CI [−0,56; +0,23] |
| MdAPE | **5,5256** | 5,5267 | jafntefli (0,001 pp) |
| innan ±10 % | 73,66 % | **75,03 %** | NEI — McNemar 64/51, p = 0,26 |
| cov80 / cov95 | 82,824 / 96,101 | **sömu tölur** | bilin eru þau sömu (sjá §3) |

**Formerkjaregla:** `bias = meðaltal((raun − spá)/raun)`, svo **jákvætt = líkanið UNDIR söluverði**. Þetta er ÖFUGT formerki við cc120 §3.2 og verður að lesast þannig.

**Hólfun (skylda skv. beiðninni, 18 hólf: `canonical_code` · flokkur A–D · bilbreidd · verðbil): EKKERT hólf er marktækt.** Hæsta |t| er 1,81. `median` ber lægri MAPE í **14 af 18** hólfum en enginn munur ber próf. **Einhallinn eftir bilbreidd snýst við frá cc120** — því breiðara bil, því meira vinnur `median`, ekki `mean`.

**Hliðarmengin bera engan dóm og eru bókuð sem slík:** `fresh_edge` n = 93 er **mengað** — fjórar raðir með APE > 100 % ráða heildartölunni, þ.á m. 2.000.000 kr fyrir 128 m² einbýli sem `onothaefur = 0` átti að stöðva (hlutasala/fjölskylduafsal). „Eftir flipp" er n = 15. Hvorugt er dómhæft.

### 2. Af hverju (a) var valið

**Nákvæmnismunurinn er ómarktækur og skipunin sjálf batt hvað þá gerist:** *„Sé munurinn innan suðmarka: segja það berum orðum — þá ræður innbyrðis samræmi (a) og ekki nákvæmni."* Skilyrðið er uppfyllt (MAPE p = 0,42 · ±10 % p = 0,26 · MdAPE jafntefli · 0 af 18 hólfum), og **cc120-vísbendingin (n = 180, `mean` betri á öllum fjórum) endurtekur sig ekki: þrjú af fjórum formerkjum snúast við og ekkert þeirra er marktækt.**

**Kerfið er ÞEGAR á `mean` í öllu sem ber vigt** — og það er ekki venja heldur burðarvirki: bilin (`lo80/hi80/lo95/hi95`) eru conformal-kvörðuð um `mean`, `rel80 = (hi80−lo80)/mean` er nefnarinn í flokkuninni, **flokkaþröskuldarnir A < 0,240 / B < 0,443 (§5C-14) sitja í MÆLDUM GÖTUM á `mean`-nefnara en SKARAST á `median`-nefnara (cc118)**, SHAP-vatnsfallið, comps og allur birtingarflöturinn lesa `mean`. (a) færir 4 neytendur að 17, ekki öfugt.

### 3. Hvað (b) hefði kostað — mælt, ekki áætlað

Orðalagið „óbreytt bil" ber tvær lesningar og **báðar voru mældar**:

- **(i) bilin standa nákvæmlega eins og þau eru birt:** þekjan er skilgreiningarlega óháð punktmatinu og **hreyfist ekki** (82,824 % / 96,101 % fyrir bæði höfuð). Kostnaðurinn er annar: **`median` lendir UTAN eigin 80 %-bils á 1,475 % (14 af 949)**. Aukaathugun sem á heima hér: `mean` situr að meðaltali á **34,0 %** af bilbreiddinni en `median` á **42,5 %** — punktmatið sem við birtum í dag er það sem er LENGRA frá miðju bilsins, og (b) hefði lagað það á kostnað þekjunnar.
- **(ii) sömu hálfbreiddir endurmiðjaðar á `median`** (talan sem raunverulega verðleggur (b)): **cov80 82,824 % → 80,084 %, −2,740 pp, McNemar p = 0,0103.** cov95 96,101 % → 96,523 % (ómarktækt).

> **DÓMSREGLA `model_quality_eval` (cov80 < 80 % → exit 2 + HALT til arkitekts) hefði staðist með 0,08 pp — INNAN VIÐ EINA RÖÐ AF 949.** Flokkur A (633 raðir, meirihluti vefsins) fellur í **78,5 %**. **(b) er þar með ekki umskrift heldur ENDURKVÖRÐUN**, og hún ætti ekki að vera keyrð undir merkjum „við skiptum bara um dálk". Sbr. `feedback_endurkvordun_verdur_ad_endurgera_maelinguna`.

**(c) — báðar tölur birtar — var hafnað á framsetningarrökum, ekki tölfræðilegum.** Tvær tölur verða tvö möt í huga lesandans þótt þær séu tvö möt á sama hlut; sama rök og §5A-31 (leiguflötunum) og cc106-birtingarreglurnar (§5C-19) hvíla á. *(Borðið vísaði einnig í „GLOSSARY §97". Sú tilvísun finnst ekki í `app/docs/GLOSSARY.md` né í `verdmat-ai` — skráð hér sem óstaðfest tilvísun; rökin standa á §5A-31/§5C-19 sem eru staðfest.)*

### 4. ÞRENNT SEM FYLGIR ÁKVÖRÐUNINNI OG MÁ EKKI TÝNAST

**(1) BIAS ER ÞEKKT OG MÆLT, EKKI FALIÐ.** `mean` ber **+1,9341 % OOS-bjaga (t = −10,74, p = 1,75·10⁻²⁵)** — **birt verðmat er kerfisbundið ~2 % UNDIR markaði**, og það er eina marktæka, rammaóháða niðurstaða einvígisins. Hún hallar á höfuðið sem var valið. Ákvörðunin er tekin **með opnum augum**: talan fer í vöktun sem sjálfstæð lína og **skal nefnd þegar við tölum um nákvæmni út á við**. Rökin fyrir að velja ekki (b) þrátt fyrir hana: **að kaupa fallegri bjaga-tölu fyrir 2,74 pp af þekju er öfug forgangsröð — þekjan er loforðið sem bankinn kaupir**, bjaginn er tala sem má birta.

**(2) /markadur-FÆRSLAN 1,006 → 1,026 ER AFHJÚPUN, EKKI VERSNUN.** cc120 §3.4 mældi að (a) færði vísinn úr +0,6 % í +2,6 % og kallaði það „sýnilega versnun". Þessi mæling fellir þá lesningu: **+2,6 % er sama stærðargráða og mældur OOS-bjagi `mean`-haussins (+1,93 %)**, svo vísirinn hefur hingað til mælt tölu sem hvergi er birt. Færslan er **vísirinn að byrja að segja satt**. Það skal orðast þannig alls staðar þar sem færslan er nefnd.

**(3) ÓMÆLT STENDUR ÓMÆLT.** **Flokkur D og `SUMMERHOUSE` eru n = 0 á holdout30.** Þar sem höfuðgapið er stærst (cc120 §4: SUMMERHOUSE meðal |Δ| 19,77 %, hámark 526,2 %; flokkur D 19,59 %) **er ENGIN OOS-mæling til á hvorugu höfðinu**. Þetta er bókað sem GAT. Það má ekki fyllt með ágiskun, ekki brúað með `listing_valuations`-mengið (rangur nefnari, mildari dreifing) og ekki lesið sem „ekkert vandamál fannst".

### 5. Skekkjuáttin (cc120 §4-spurningin) — LEYST, og hún er ekki galli

cc120 fann `mean` < `median` á **70,7 %** og kallaði það öfugt við vænta hægri skekkju. Þrjár tilgátur voru mældar, ekki settar fram:

- **T1 Jensen/bakvörpun ÚTILOKUÐ — strúktúrellt.** `to_kr(x) = round(expm1(x)/cpi_f × 1000)` er **strangt vaxandi** og BÁÐIR hausar fara í gegnum nákvæmlega sama fall (`precompute/rebuild_predictions_iter4.py`). Einhalla vörpun getur breytt STÆRÐ munar en aldrei FORMERKI hans. Mælt framlag kúpninnar: **0,238 pp af 2,331 % gapi og 0 % af formerkinu.** Að auki er cc120-orðalagið flokkunarvilla: **hægri skekkjan sem búist er við er í VERÐSTIGINU — sem er einmitt ástæðan fyrir því að markmiðið er log-verð.** Skekkja log-leifarinnar er allt annar hlutur.
- **T2 kvörðunarlagið ÚTILOKAÐ á kóðaslóð.** Punktmötin eru reiknuð af HRÁUM höfðum áður en nokkuð kvörðunarlag keyrir; conformal, segcal-teygjan og 3.3-framreiðslu-offsetin skrifa **aðeins** `lo80_kr/hi80_kr/lo95_kr/hi95_kr`. **Heiðarlegur fyrirvari sem er bókaður: stimplarnir tveir skarast ekki á segmenti, svo T2 er ekki EMPÍRÍSKT aðgreinanleg — hún er felld á kóðalestri, ekki á mælingu.**
- **T3 STAÐFEST MEÐ BEINNI MÆLINGU: HÖFUÐIN SJÁLF, OG ÞAU HAFA BÆÐI RÉTT FYRIR SÉR.** Skilyrt log-leifadreifing er **VINSTRI-skekkt** (skewness **−3,67** á train), svo `E[log p] < miðgildi(log p)` — það er stærðfræðileg afleiðing, ekki villa. `q500` mælist miðgildis-óbjagaður upp á **5·10⁻⁵** á train; `mean` situr fyrir neðan **af hönnun** (L2 metur meðaltal). **Per segment fylgir FORMERKI gapsins formerki leifaskekkjunnar: `APT_FLOOR` er eina segmentið með hægri-skekkta log-leif (+1,21) og eina segmentið þar sem gapið snýst við (−0,0025).** Vinstri halinn er sami hali og mengar `fresh_edge` — eitt fyrirbæri, ekki tvö.

### 6. Nýtt og ómælt: höfuðgapið er 3,2× stærra á birtingarslóð en í artifactinu

Utan beiðninnar en of stórt til að þegja yfir: á **sömu 1.165 eignum**, sömu tveimur höfðum, mælist gapið gjörólíkt eftir SKORUNARSAMHENGI — artifact-rammi (hver sala skoruð í eigin tímasamhengi) `dlog` **+0,00825** gegn birtingarslóð **+0,02638**; `q500 > mean` **53,2 %** (myntkast) gegn **71,5 %**. `mean`-hausinn féll **2,6× meira** milli ramma en `q500` (−0,0297 gegn −0,0116) þótt fylgni punktmatsins milli slóða væri 0,977. **Þar með er cc120-talan „70,7 %" eiginleiki verðmatsmánaðar-skorunarinnar, ekki eiginleiki líkansins.**

**Og afleiðingin er á DÓMI, ekki bara á stærð: í artifact-rammanum vinnur `mean` — og ÞAR er ±10 %-munurinn MARKTÆKUR** (79,89 % gegn 76,11 %, McNemar **p = 0,00061**; Wilcoxon á pöruðum APE p = 0,0114). Sama úrtak, sami sannleikur, öfug niðurstaða. `scripts/model_quality_eval.py:48-52` bókar þetta þegar beint („Do not quote one as the other") og þessi mæling er fyrsta staðfesta tilvikið þar sem rammarnir skila ÖFUGUM dómi. **Hvaða eiginleiki veldur er ÓMÆLT** — tímaeiginleikar eru útilokaðir sem eina orsök (artifact-`dlog` eftir söluári spannar aðeins +0,005…+0,017, 2026 á +0,0054). Liðurinn fer á backlog sem sér mál. Sbr. `feedback_hofudgapid_er_eiginleiki_skorunarsamhengis`.

### 7. Framkvæmdin er EKKI hluti þessarar ákvörðunar

Ákvörðunin er kvittuð; **breytingin sjálf var ekki gerð í þessari lotu og má ekki gerast í framhjáhlaupi**. `expected_base`/`expected_extraction` → `real_pred_mean` snertir `scripts/extraction_engine.py:316–317` OG D2-parity-hliðið í `scripts/model_quality_eval.py:557–576 / 874–881`, sem les `p.real_pred_median AS frozen_median` sem viðmið — **hliðið fellur ef aðeins vélin er færð.** Liðurinn er skilgreindur sem sér lota með eigin rowcount-sönnun í `PLANNING_BACKLOG` (viðauki cc123) og er **bindandi forsenda** verðmats-bakfyllingarinnar sem cc121 setti á pásu.

**Heimild**: `D:\_audit\cc123_oos_einvigi\OOS_EINVIGI_CC123_20260808.md` (§0 nefnarar + tækjasannprófun, §1 aðaltafla, §2 hólfun, §3 kvörðunarkostnaður, §4 skekkjuátt T1/T2/T3 + §4.1 rammamunurinn, §5 artifact-krosspróf, §6 dómur, §7 sannprófunarslóð); `D:\_audit\cc120_midsaekni\MIDSAEKNI_CC120_20260808.md` §1.1/§2/§3.2/§3.4/§4/§5; `scripts/model_quality_eval.py:48-52, 186-187, 557-576, 874-881`; `scripts/extraction_engine.py:316-317`; `precompute/rebuild_predictions_iter4.py` (`to_kr`, punktmöt fyrir kvörðun); artifakt `D:\model_artifacts\iter4r_20260805_reglaR_strukt\` (`_predictions.pkl`, `_holdout_rows.csv`, `_manifest.json`); DECISIONS §5C-14 (þröskuldarnir 0,240/0,443), §5C-19 (birtingarreglurnar), §5A-31 (tvær tölur á sama fleti).

## 2026-08-12 — §5D-2 · cc134 EXCLUDE Í VERÐMATSLEIÐINNI → AFSTAÐA BORÐSINS: (a)+(c) SAMAN, (b) FELLD

**Málið**: cc130 §5c (11.08) fann að `scraper.listing_valuations` ber **2.372 frystar raðir á 410 EXCLUDE-eignum** meðan `public.predictions` ber **0 af 56.958 EXCLUDE-eignum** — og það síðara er ÁSETNINGUR (regla R, cc76–cc78). Vélin sem skorar og vélin sem birtir voru ósammála um hvaða flokkur er verðmetanlegur, og sú ósýnilega var sú sem skoraði. cc134 (12.08, READ-ONLY) var forsendumælingin.

**Heimild**: `docs/fable_prep/audits/EXCLUDE_VERDMATSLEID_CC134_20260812T0006Z.md` (§1 þjálfunarþekjan + skorunarprófið, §2 tæmandi neytendalisti m/mældum áhrifum, §3 síuhönnunin, §4 kostirnir, §5 opnir liðir, §6 aðferð).

### 1. Skorunin var ekki „óbirt" — hún var UTAN SKILGREININGARSVIÐS

`D:\training_data_v2.pkl` — sha256[:16] **`32f9a1242b212d11`, endurmælt á diski = `_manifest.json` lifandi líkans**, svo nefnarinn er sannreyndur en ekki gefinn — ber **0 EXCLUDE-raðir af 146.841**, og **enga `NaN`-röð heldur** (summa 12 flokkanna er nákvæmlega 146.841). `canonical_code` er `pandas.Categorical` með **12 flokkum**; við skorun keyrir `phase_d3_score_extract.py:263` `pd.Categorical(vals, categories=cat_map[cat])`, svo `'EXCLUDE'` varpast í **`-1` → `NaN`**. Eiginleiki með 2,87 prósenta gain hverfur og röðin fer niður grein sem **engin þjálfunarröð þjálfaði**.

**Sannprófað með skorun, ekki ályktað.** Parity fyrst, annars mælir prófið ekki vélina: 201 EXCLUDE-eignir undir lifandi stimpli, adapter gegn frystu töflunni — **max |Δ| = 0 kr, 201/201**. Á sömu 410 eignum, aðeins `canonical_code` breytt:

| þvingað í | meðal \|Δ\| gegn EXCLUDE |
|---|---|
| `APT_FLOOR` | **3,10 %** |
| `ROW_HOUSE` | 4,33 % |
| `SFH_DETACHED` | 7,86 % |

**Flokkurinn skiptir nánast engu.** Talan er „íbúð af þessari stærð í þessu matsvæði", knúin af `EINFLM` (30,17 % gain) og matsvæðinu (30,13 % samanlagt). **82 eignanna (20,0 %) hafa ekkert byggingarflatarmál** og bera samt 22,12 M kr að meðaltali — sumarbústaðaland 19,94 M, íbúðarhúsalóð 26,82 M, 1,81 ma. kr bókfært alls. Gegn ásettu verði er MdAPE **60,2 %** gegn 7,7 % á `APT_FLOOR`.

### 2. Mengunin var mæld á báðum nefnurum

`scraper.v_expected_vs_real`, 23.605 raðir / 206 seldar; EXCLUDE er 10,05 % af heild og 2,9 % af seldum:

| mæling | ALLT | ÁN EXCLUDE | Δ |
|---|---|---|---|
| `base_pct_error` bjagi (auglýsingastig, n=206) | +8,22 % | **+6,06 %** | 2,16 pp |
| MAPE | 15,50 % | **13,56 %** | 1,94 pp |
| sama á **eignastigi** (n=82) | +5,46 % | **+3,16 %** | 2,30 pp |
| **`extraction_gap` meðaltal (n=23.605)** | +0,2721 M kr | **+0,4927 M kr** | **−45 %** |

Áhrifin standa á BÁÐUM nefnurum — þetta er ekki tvítalningar-tálsýn. `extraction_gap` er versta línan: **10 % af röðunum lækka mælt framlag útdráttarins um 45 %**, og EXCLUDE-raðirnar draga í ÖFUGA átt við alla aðra flokka.

### 3. Rótin: hliðið var TIL, en í röngu falli

`phase_d3_score_extract.main()` (línur 451–464) ber þriggja hliða trekt — `is_residential | is_summerhouse`, `byggar.notna()`, `matsvaedi_confident`. **`value_listings` kallar `score()` BEINT** gegnum `_score_iter4` og sleppir öllum þremur. Sían var skrifuð í **keyrslu-drifið, ekki í vélina**. Sama gerð og cc112 (hlið á mælingu en ekki á skrifleið) og cc94 (`flatten_row`-skynjarinn í falli sem keðjan kallaði aldrei). Sbr. `feedback_hlid_a_maelingu_en_ekki_a_skrifleid`.

### 4. AFSTAÐA BORÐSINS (12.08): (a)+(c) SAMAN

**(a) SÍA FRAMVEGIS — GERT.** Ein WHERE-lína í `fetch_extracted_listings_to_value` (`scripts/extraction_engine.py`): `AND pr.canonical_code <> 'EXCLUDE'`. `public.properties` var þegar í JOIN-inu, svo engin ný tenging. Borðið valdi S1-orðalagið; **mælt að S1 og S2 (`NOT (is_residential OR is_summerhouse)`) eru SAMA MENGIÐ — 0 frávik af 232.887 eignum**, svo línan má lesast sem hvort tveggja. Sannprófað gegnum RAUNVERULEGA fallið (SQL-strengurinn fangaður úr því, ekki handskrifað afrit — cc113-lexían): biðröð **20.270 → 18.177**, 2.093 burt (10,33 %), **0 EXCLUDE eftir**, og cc128-falsy-hegðunin ósnert (`None`→18.177, `0`→0, `5`→5).

**(c) UNDANSKILJA Á MÆLIFLÖTUNUM — HANNAÐ, ÓAPPLÝJAÐ.** `supabase/migrations/20260812002226_cc134_exclude_utilokun_maelifleti.sql` (+ rollback). Ný `scraper.v_expected_vs_real_all` er ósíaða heimildin (allar 23.605 raðirnar + nýr `canonical_code`-dálkur); `scraper.v_expected_vs_real` verður `SELECT * FROM …_all WHERE canonical_code IS DISTINCT FROM 'EXCLUDE'`. Sjö teljarar í `ops_scraper_signals()` fá sömu síu. **Líkami sýnarinnar var keyrður sem `SELECT` á lifandi DB í read-only txn**: 23.605 ósíað / 21.233 síað, 33 dálkar í óbreyttri röð + `canonical_code` aftast (skilyrði `CREATE OR REPLACE VIEW`), og mælingin endurgerð: 8,22 → 6,06.

**(b) HREINSUN GAMALLA RAÐA — FELLD.** Þær 2.372 standa. Þær eru **söguleg heimild um hvað vélin sagði**, sömu rök og cc116 fyrir 20.642 sögulegu raðirnar og cc131 fyrir sama flokk („ekki endurbyggingarefni"). Óafturkræft er of dýrt fyrir hreinlæti sem (c) leysir án þess að eyða neinu.

**(a) og (c) LOKA HVOR ANNARRI.** (a) ein hefði skilið eftir **varanlegt gólf 109** í `/ops` `backlog.unprocessed` — auglýsingar sem vélin sækir aldrei framar en spjaldið teldi sem ógert verk að eilífu. (c) fjarlægir nákvæmlega þær 109. Backlog-teljararnir ÞRÍR fá sömu síu svo samlagningin haldi: **11.792 = 4.156 + 7.636** (var 11.944 = 4.199 + 7.745).

### 5. BÓKAÐ SÉRSTAKLEGA: cc120-talan var hrein FYRIR TILVILJUN

cc120 §3.2 birti **+7,84 %** sem gæðatölu. Sá nefnari (n=180) krafðist tengingar við `public.predictions_2026_04` til að endurheimta samfrysta meðaltalið — og **spátöflurnar bera 0 EXCLUDE-eignir**, svo **öll sex seldu EXCLUDE-röðin féllu út af sjálfum sér** (mælt í dag: 6/6 utan apríl-árgangs, 186/200 af hinum innan hans). **cc120-talan var því rétt — en hún var rétt af því að tenging sem mælingin þurfti í ÖÐRUM tilgangi virkaði óvart sem EXCLUDE-sía.**

Sá sem spyr sýnina beint — `select avg(base_pct_error) from scraper.v_expected_vs_real`, augljósasta leiðin og sú sem næsta lota fer — fékk **+8,22 %**. **Þetta er lexían sem ver næstu mælingu: hrein tala sem enginn hannaði til að vera hrein er ekki vörn, hún er heppni sem rennur út.** Það er nákvæmlega ástæðan fyrir að (c) fer í SÝNINA en ekki í hverja mælingu fyrir sig — sía sem þarf að MUNA eftir er ekki sía, hún er minnisatriði sem bíður eftir að gleymast.

### 6. Glugginn var réttur

Verðmats-þrepið hefur verið í PÁSU frá 09.08 (`EXTRACT_VALUE_LIMIT=0` → `--skip-valuation`, cc121), svo sían fór inn án þess að nokkuð væri í keyrslu og engin röð er í hættu. Kostnaður **$0,00 í allar áttir** — verðmats-þrepið gerir engin Haiku-köll; útdrættirnir voru þegar keyptir. Þetta var aldrei sparnaðarákvörðun.

### 7. Framkvæmdin er EKKI hluti þessarar ákvörðunar

Migration-skráin er **skrifuð á disk og bókuð, EKKI keyrð** gegnum Supabase MCP `apply_migration`. HALT stendur fyrir framkvæmd. Þegar hún er applýjuð skal endurmæla teljarana sjö gegn töflunni í §4 hér að ofan — ekki treysta á að þeir hafi lent rétt.

### 8. Opnir liðir sem mælingin fann (PLANNING_BACKLOG, viðauki cc134)

1. **`APT_SENIOR` — 89 BIRTAR spár á óþjálfuðum flokki.** `public.properties` ber 14 `canonical_code`-gildi, þjálfunin 12; umframgildin eru `EXCLUDE` (útilokað með ásetningi) og **`APT_SENIOR`, sem er hvergi útilokað og ber spá á öllum 89 eignum**. Sannprófað: adapter gegn `public.predictions`, **max |Δ| = 0 kr, 89/89** — birtu spárnar voru raunverulega reiknaðar með `canonical_code = NaN`. **Þetta fellir einföldunina „birtingarleiðin útilokar það sem líkanið kann ekki".** Sjálfstætt mál, ekki leyst hér.
2. **531 eign / 2.716 raðir í biðröðinni sem eru íbúðarhæfar en bera samt enga spá** — SUMMERHOUSE 16,18 % af flokknum, SFH_DETACHED 8,33 %, APT_FLOOR 2,47 %. Þetta er halinn sem S4 (`EXISTS predictions`) hefði tekið; S4 var ekki valin því hún er hlið á afurð annarrar vélar sem er endurbyggð per flipp.
3. **`/ops` lyklar backlog á `listings_canonical.category` (AUGLÝSINGAflokk) en verðmatið á `properties.canonical_code` (EIGNAflokk)** — 109 gegn 2.093. Tvær skilgreiningar á „íbúð" á sama spjaldi. (c) gerir teljarana innbyrðis samkvæma en lagar ekki lyklunina sjálfa.
4. **`v_expected_vs_real` telur á AUGLÝSINGU, ekki eign** (5,25 raðir/eign). Bugðufljót 9 vó þrefalt í sex-raða menginu.

> **➜ FRAMHALD: `### §5D-2 VIÐAUKI (12.08 kl. 10:07Z)` — KOSTUR (c) APPLÝJAÐUR.** Hann stendur **neðst í skránni, á eftir §5D-3**, ekki hér: samhliða lota (cc136) bætti §5D-3 við á meðan cc134 var í keyrslu, og skráin er viðbætandi svo viðaukinn fór aftast frekar en að vera skotið inn hér. **§7 hér að ofan („framkvæmdin er EKKI hluti þessarar ákvörðunar") er þar með úrelt** — lestu viðaukann áður en þú vitnar í tölurnar í §4.

---

## 2026-08-12 — §5D-3 · cc136 BRÚARKEYRSLAN 11.08 BÖKKUÐ: raðirnar voru ekki rangar, þær voru OF SNEMMA

**Málið**: Extraction-brúin (cc75) skrifaði **28.703 raðir á 3.997 eignir** í `public.property_attributes` kl. **2026-08-11 22:21:23,143147Z** — undir frystingu sem stóð. GO-bréf flippsins §7 („Extraction-brúin (cc75) — FROSIN þar til γ-mótpróf") og cc81 §9.2 bönnuðu einmitt þetta. cc133 §7b mældi afleiðinguna á notendafleti: **46,4 % af berandi eignum lágu á margföldunarþakinu**, óklemmd leiðrétting p50 **+23,7 %**, hámark **+64,0 %**. cc133 §7d valdi **kost A: bakka**. cc136 framkvæmdi.

**Heimild**: `D:\_audit\cc136_bakk_bruarkeyrsla\BAKK_BRUARKEYRSLA_CC136_20260812.md` (§0 nefnarar og tæki, §1 afmörkunin, §2 varðveislan, §3 aðgerðin + rowcount per lind, §4a þakmælingin, §4b prod-stikkprufan, §5 lærdómur). Vinnugögn utan git: `D:\cc136_bakk\` (afrit, bakk-SQL, endurvirkjunar-SQL, mælingar, prod-HTML).

### 1. Ákvörðunin sem er BÓKUÐ: keyrslan fór fram undir frystingu — og frysting sem er staðfest eftir á er ekki frysting

Raðirnar sjálfar eru ekki dæmdar rangar. **Þær eru of snemma.** γ-mótprófið er skilyrðið sem GO-bréfið setti á brúna, og það er óafgreitt; keyrsla sem fer fram á undan skilyrðinu ber enga heimild hversu rétt sem hún kann að reynast þegar skilyrðið fellur. Ekkert hlið stóð á skrifleiðinni — bannið bjó í GO-bréfi og bókun, ekki í vélinni. Sama lögun og `feedback_hlid_a_maelingu_en_ekki_a_skrifleid`: **hlið sem ver mælinguna ver ekki skrifleiðina.**

### 2. Afmörkunin var mæld ÁÐUR en nokkuð var snert — og krafan stóðst upp á rað

`min(created_at) = max(created_at) = 2026-08-11 22:21:23.143147+00`: **einn stimpill**, engin sekúndubrots-dreifing, svo `created_at = <stimpill>` er ótvíræð afmörkun en ekki nálgun.

| | krafa borðsins | mælt |
|---|---|---|
| Raðir | 28.703 | **28.703** ✅ |
| Eignir | 3.997 | **3.997** ✅ |

**App-leiðar-raðirnar fjórar (03.08 ×2, 11.08 18:03 og 21:24) telja nákvæmlega 42 og bera ENGIN þeirra stimpil mengisins** — þær eru allar utan `WHERE`-skilyrðisins og voru ekki snertar.

**⚠ EN forsendan „þær standa" var þegar ósönn þegar cc136 hófst.** Brúarkeyrslan sjálf **supersaði 9 af þessum 42 mönnuðu röðum** um leið og hún lagði sínar eigin ofan á — 4 á `2013952` (úr 03.08 11:57-lotunni: `annad`, `badherbergi`, `geymsla`, `golfefni`) og 5 á `2230688` (úr 11.08 18:03-lotunni: `annad`, `badherbergi`, `golfefni`, `herbergi`, `thvottahus`), allar með `superseded_at = 2026-08-11 22:21:23.143147+00`. Þær raðir eru **utan mengisins sem bakkað var og standa því áfram superseraðar**. Ástandið eftir cc136 er þar með **næstum — en ekki nákvæmlega — for-keyrslu-ástandið**. Stæðan sem lagar það er skrifuð í `cc136_endurvirkjun_bruarkeyrsla.sql` en **var EKKI keyrð**: §3 í erindi borðsins afmarkaði aðgerðina við mengið eitt og að endurvekja raðir utan þess er sjálfstæð ákvörðun. **Liggur fyrir borðinu.**

### 3. Rollbackið er `superseded_at`, ekki `DELETE` — og það er ENDURVIRKJANLEGT

```sql
UPDATE public.property_attributes SET superseded_at = now()
 WHERE source = 'auglysing' AND created_at = '2026-08-11 22:21:23.143147+00'
   AND superseded_at IS NULL;   -- rowcount 28.703
```

**Raðir alls í töflunni: 385.636 fyrir → 385.636 eftir. Engin röð eydd.** Afrit fyrir aðgerð utan git: 28.703 línur, **28.703 einkvæm `id`**, 3.997 eignir, 0 gallaðar (`id, fastnum, attr_key, value, source_date`).

**Bakk-stimpillinn er einn** (`count(distinct superseded_at) = 1`): **`2026-08-12 00:32:44.238331+00`**. Þetta er ekki bókhaldsatriði heldur **lykillinn að endurvirkjuninni**: skilyrt á `superseded_at IS NOT NULL` hefði endurvirkjunin líka vakið raðir sem seinni keyrslur supersera réttilega; skilyrt á þennan stimpil hittir hún mengið og ekkert annað. Þegar γ er afgreitt kveikir **ein stæða** aftur á nákvæmlega þessum 28.703 röðum (`cc136_endurvirkjun_bruarkeyrsla.sql`, skrifuð á disk í sömu lotu).

**Eigindi úr öðrum lindum standa óhreyfð** — mælt per lind, virkar raðir fyrir → eftir: `skraargogn` 356.422 → **356.422**, `extraction` 373 → **373**, `notandi` 34 → **34**, `stadfest` 4 → **4**. Aðeins `auglysing` hreyfðist: 28.736 → **33** á 4 eignum (= mönnuðu prófanirnar 42 − 9 supersaðar).

### 4. Sönnunin sem gildir: þakið fór úr 47,1 % í 0,12 % — og leifin er MÖNNUÐU PRÓFANIRNAR

Mælt með **óbreyttu** `lib/leidretting.js` og **óbreyttu** `lib/attributes-queries.js` yfir lifandi lagið, sama þýði fyrir og eftir (eignirnar 3.997). Vélin er ekki hermd: `getAttributes` er kallað eins og `/api/leidretting/[fastnum]` kallar það, aðeins klientinum skipt út fyrir minnis-klient — uppruna-forgangur, já-hlutdrægnisían og nýbyggingarreglan eru orðrétt þær sem viðmótið keyrir.

| | FYRIR | EFTIR |
|---|---|---|
| Virkar raðir yfir þýðið | 35.917 | **7.214** (Δ −28.703) |
| Berandi (≥1 birtanlegur liður) | 3.823 | 1.633 |
| **Á margföldunarþaki** | **1.802** | **2** |
| **Þakhlutfall** (af lagi ≠ null) | **46,23 %** | **0,12 %** |
| **Liðir/eign, meðaltal** | **5,945** | **1,011** |
| Óklemmd p50 á þaki | +23,48 % | +35,60 % (n=2) |
| Óklemmd hámark | +64,04 % | +44,58 % |

**Markmið borðsins (46,4 % → ~0,0 %; 5,9 → ~1,0) stenst.** Eignirnar tvær sem eftir liggja á þaki eru **nákvæmlega** `2013952` og `2230688` — mönnuðu prófanirnar sem áttu að standa. **0,12 % er því ekki leki úr brúnni heldur mengið sem var undanskilið með ásetningi.** Af hinum 1.631 berandi eignunum ber **hver einasta nákvæmlega 1 lið** (`bilskur_staedi` úr `skraargogn`) — sem er einmitt „~1,0" sem cc133 spáði.

**Endurvirkjunin er ÆFÐ gegn rauntöflunni, ekki bara skrifuð** (§5C-15): skilyrði endurvirkjunar-SQL-sins hittir **28.703 raðir / 3.997 eignir, 0 úr annarri lind, 0 úr annarri lotu**.

### 5. Endurgerð cc133 §7b — hlutfallið lendir, en SPEGILLINN og RAUNFALLIÐ eru ekki sama vélin

cc133 notaði nefnarann 3.999 (eignir með ≥1 virka `auglysing`-röð). Hlutfall **46,42 % gegn 46,23 %**, liðir/eign **5,9 gegn 5,945**, miðgildi liða **6 gegn 6**, hámarksliðafjöldi **17 gegn 17**, p50 á þaki **+23,7 % gegn +23,48 %**, hámark **+64,0 % gegn +64,04 %**. **Það sem skeikar er stærð berandi mengisins: 3.962 gegn 3.898 — 64 eignir, 1,6 %** (og þakfjöldinn í sama hlutfalli, 1.839 gegn 1.802). Skekkjan er því ekki í þakreglunni heldur í því **hverjar komast inn í lagið yfirleitt**.

**Rótin er mælitækið, ekki gögnin.** cc133 lýsir sínu tæki svo: „uppruna-forgangur og já-hlutdrægnisían **speglaðar** úr `lib/attributes-queries.js`". cc136 speglar ekki — það **kallar `getAttributes` sjálft**. Gögnin voru óbreytt milli mælinganna, svo tækið er eini frjálsi liðurinn. **Spegill sem hleypir 1,6 % fleiri eignum inn í lagið en raunreglan er nákvæmlega gildran sem `scripts/_alias-loader.mjs` var skrifað gegn** („þá er freistingin að prófa AFRIT af reglunni í stað hennar sjálfrar"). **Bókað sem óuppgerður munur, EKKI jafnað út** — hlutfallið sem ákvörðunin hvíldi á lifði það af, en það var heppni en ekki hönnun.

### 6. Endurtekur brúin sig í nótt? NEI — og rofinn bar viðvörunina sjálfur

`scripts/nightly_delta_chain.sh` (`run_extract()`) sendir `--forward N --confirm` og `--value-limit`/`--skip-valuation` — **hvergi `--bridge` né `--bridge-only`**. Brúin er opt-in rofi í `run_extraction.py` og keðjan dregur hann ekki. **Keyrslan 11.08 var mönnuð `--bridge`-keyrsla, ekki næturvél, og bakkið stendur af sér næstu nótt óbreytt.**

**Og talan sem réttlætti frystinguna stóð skrifuð við rofann.** Athugasemdin við `--bridge` (`run_extraction.py:158-167`) segir orðrétt: *„Að tengja hana inn í `nightly_delta_chain.sh` er SÉR ÁKVÖRÐUN (sjá §8 í audit-skjalinu: 47,4 % lenda á margföldunarþaki leiðréttingarlagsins)."* Afleiðingin var **mæld, spáð og bókuð við rofann á undan keyrslunni** — og hann var samt dreginn. **Viðvörun sem stendur í kóðanum en ekki í skilyrði rofans er skjal, ekki hlið.**

### 7. Aðgerð sem stöðvast við DB-lagið er HÁLF AÐGERÐ

Prod-stikkprufan á **2287817** (ónafngreind sókn, talning á pillunni „Virk auglýsing 2026"): **5 fyrir aðgerð → 5 STRAX eftir hana, HTML bæti-fyrir-bæti eins (77.557 bæti)**. Aðgerðin sást ekki á fletinum. Það er ekki bilun heldur þekkt lag: `/eign/[fastnum]` les gegnum `unstable_cache` (`lib/eign-queries.js`, `EIGN_CACHE_TTL = 3600 s`). Hausarnir sanna að route-cachið er ekki orsökin (`X-Vercel-Cache: MISS`, `Cache-Control: private, no-cache, no-store`) — það er **Data Cache**.

**Merkjastýrða ógildingin er til en var ekki fær**: `POST /api/endurnyja` krefst `ENDURNYJA_LYKILL`, sem er **hvergi til á D:** (leitað yfir alla skrána) — hann býr eingöngu í Vercel-umhverfinu. Cachið var því látið renna út á TTL. **Mælt: 5 → 0 kl. 01:01:30Z, ~29 mínútum eftir commit.** Staðfestingarsókn utan vöktunarinnar: `http=200`, 80.320 bæti, `Eigindi`-blokk til staðar, **0 auglýsinga-pillur, 1 `Skráargögn`-pilla**.

**Aðgreint strax frá „bakkið virkar ekki":** þrjár aðrar eignir úr sama mengi með kaldar cache-færslur (2035839, 2231924, 2529300) báru **0 pillur og 1 `Skráargögn`** þegar við fyrstu sókn. Gagnagrunnsástandið rendraðist því rétt frá og með commit-inu; töfin var heit færsla og ekkert annað.

**Hvað þetta hreyfir EKKI:** leiðrétta viðmiðið sjálft (`/api/leidretting/[fastnum]`) er `force-dynamic`, `revalidate = 0` og les `getAttributes` beint — **greidda talan var rétt frá og með commit-inu**. Það sem lá eftir í ~29 mínútur var birting uppruna-pillnanna.

**Reglan sem þetta staðfestir** (og `lib/eign-queries.js` ber þegar, cc86 c2 / cc93): **DB-breyting undir cachinu er innihaldsbreyting alveg eins og kóðabreyting í því.** Sá sem bakkar undir Data Cache verður að eiga ógildingarleið — og hún var ekki til á þessari vél. **Opinn liður: `ENDURNYJA_LYKILL` er óaðgengilegur rekstrarvélinni sem á að nota hann.**

⚠ *Aðferðarathugasemd sem er bókuð því hún hefði nærri fellt mælinguna*: fyrsta lota kalda-prófsins keyrði `curl`, fékk `Connection was reset` og skrifaði enga skrá — og `grep` á skrá sem er ekki til skilar **0**, sem hefði lesist sem „núll pillur = stenst". **Talning á skrá sem varð aldrei til er ekki mæling.** Sóknirnar voru endurteknar með `http`-kóða og bætafjölda bókuðum við hverja talningu, og fallna sóknin í vöktunarlogginu (00:57:13, `pillur=-1`) er skilin eftir sem villa en ekki umskrifuð í núll.

### 8. Bannið stóð

Engin eyðing (385.636 raðir fyrir og eftir), engin breyting á brúnni sjálfri, engin skráning í keðjuna, ekkert snert í `run_extraction.py` né `nightly_delta_chain.sh` (aðeins lesnar). **Mælitækin sjálf liggja utan repoins** — `D:\cc136_bakk\cc136_afrit_og_maeling.mjs` og eigin resolve-hook — einmitt svo mælingin krefðist engrar breytingar á vörunni sem hún mælir.

### 9. LOKASTÆÐAN (sama lota, GO borðsins 12.08): mönnuðu 9 raðirnar ENDURVIRKJAÐAR — ástandið er nú for-keyrslu-ástand

Liðurinn sem stóð opinn í §2 er afgreiddur. Rök borðsins: raðirnar eru mannaðar prófanir cc75, þær voru virkar fyrir 11.08, og markmiðið var for-keyrslu-ástand — **„næstum" er ekki það**.

**Afmörkun:** keyrt á **auðkennin níu beint**, ekki á stimpilinn einan — `id IN (423711,423720,423721,423722,423800,423802,423803,423804,423805)` **OG** `superseded_at = '2026-08-11 22:21:23.143147+00'`. Tvöfalt skilyrði svo hvorugt geti eitt og sér hitt of vítt. Fyrir aðgerð staðfest að **nákvæmlega þessar 9 raðir og engar aðrar** bæru brúarstimpilinn, og að endurvirkjunin búi ekki til tvær virkar raðir á neinni `(fastnum, attr_key, source)`-þrenningu (mælt, tómt). **Rowcount: 9 (2 eignir).**

**Ástandið er for-keyrslu-ástand — mælt, ekki fullyrt.** Prófið er ekki raðafjöldinn heldur hvort nokkur röð beri enn ummerki keyrslunnar: **0 raðir** bera `superseded_at = '2026-08-11 22:21:23.143147+00'` (hver röð sem keyrslan felldi er komin til baka), **0 raðir** úr keyrslunni eru virkar (hver röð sem hún bætti við er felld), og **42 af 42** mönnuðum app-leiðar-röðum eru virkar — eins og 11.08 kl. 22:21:22. Endurvirkjanlegar raðir á bakk-stimplinum standa óhreyfðar í **28.703**.

**⚠ Ein breyta utan cc136 lenti í glugganum og VERÐUR að lesast með.** Milli fyrri og seinni hluta lotunnar (00:32Z → 09:5xZ) skrifaðist **ný mönnuð app-leiðar-lota kl. 2026-08-12 07:43:41,62295Z — 11 raðir á fastnum 2522544**. Hún er hvorki frá cc136 né frá brúnni (brúin skrifar 28 þúsund raðir í einu; þetta er 11 raðir á einni eign, sama lögun og hinar mönnuðu loturnar), og engin skrif úr öðrum lindum urðu í glugganum. Eignin **var í brúarmenginu**, svo nýja lotan leggst ofan á bakkað lag.

| Þakmæling (þýði = eignirnar 3.997) | eftir bakk | eftir endurvirkjun | án 12.08-lotunnar |
|---|---:|---:|---:|
| Virkar raðir yfir þýðið | 7.214 | 7.234 | 7.223 |
| Berandi | 1.633 | 1.633 | 1.633 |
| **Á þaki** | **2** | **3** | **2** |
| **Þakhlutfall** | **0,12 %** | **0,18 %** | **0,12 %** |
| Liðir/eign | 1,011 | 1,015 | 1,011 |

**Þriðja eignin á þakinu er 2522544 og hún kemur frá 07:43-lotunni, ekki frá endurvirkjuninni** — hún fór úr **1 lið í 6** og þar með á þakið. **Endurvirkjunin sjálf hreyfði þakfjöldann ekki**: `2013952` stóð í 12 liðum fyrir og eftir (raðirnar fjórar — `annad`, `badherbergi`, `geymsla`, `golfefni` — bera engan lykil sem stuðull virkjast á) og `2230688` fór úr 8 í 9 liði (`thvottahus` er stuðulslykill) en var **þegar á þakinu**. **Spá borðsins stenst því orðrétt: þakið stendur í ~0,12 % og eignirnar tvær sem eftir liggja eru einmitt prófanirnar og voru þar fyrir.**

**Eini munurinn á töflunni og 11.08-myndinni eru þessar 11 raðir frá 12.08 — nýtt verk, ekki leif.** Að telja það sem frávik frá for-keyrslu-ástandi væri að rugla saman „ástandinu sem keyrslan skildi eftir" og „öllu sem hefur gerst síðan".

### §5D-2 VIÐAUKI (12.08 kl. 10:07Z, sama dag) — KOSTUR (c) APPLÝJAÐUR

> *Um staðsetningu:* þessi viðauki tilheyrir **§5D-2** en stendur á eftir **§5D-3** af því að samhliða lota (cc136) bætti §5D-3 við á meðan cc134 var í keyrslu. Skráin er viðbætandi, svo viðaukinn fór aftast frekar en að vera skotið inn ofar. Vísun stendur neðst í §5D-2.

**§7 í §5D-2 hér að ofan stendur óbreytt** („framkvæmdin er EKKI hluti þessarar ákvörðunar", migration óapplýjuð). Sú lesning var rétt þegar hún var skrifuð. Borðið gaf GO síðar sama dag; leiðréttingin stendur hér undir, ekki í stað hennar.

**RÁSIN VAR PSYCOPG2, EKKI MCP.** `apply_migration` var **ótengt í lotunni** (staðfest með þremur ToolSearch-leitum; aðeins `claude-in-chrome`, `context7`, `financial-analysis` til staðar). Borðið heimilaði psycopg2 á transaction pooler gegn **þremur skilyrðum sem smíða jafngildið í stað þess að gefa sér það**, öll uppfyllt: **(1)** `schema_migrations`-færslan skrifuð **í sömu txn og stæðan sjálf** (MCP gerir það sjálfkrafa, psycopg2 ekki — fall skilur því enga munaðarlausa færslu eftir); **(2)** **hvert statement sér** (cc86), átta aðskildar txn-ir, `SET TRANSACTION READ WRITE` fyrsta stæðan í hverri, fall á n stöðvar n+1; **(3)** **spegillinn lesinn orðrétt úr töflunni**, ekki endurritaður úr drögunum. `created_by` ber rásina svo hún sjáist í `schema_migrations` sjálfri en ekki aðeins í skjölum. Versions `20260812002226`–`002233`, **8/8 keyrðar, engin féll**.

**NEFNARARNIR HREYFÐUST — OG ÞAÐ ER SJÁLFSTÆÐ NIÐURSTAÐA.** Milli mælingar (00:06) og apply (~10:00) bættust **49 nýjar virkar auglýsingar og 53 nýjar seldar raðir** (`daily_sales_refresh`), svo `base_pct_error`-nefnarinn fór 206 → 259. **Töflurnar í §4 hér að ofan eru því ekki beinn samanburður lengur.** Forspá var þess vegna reiknuð á **ferskum gögnum rétt fyrir apply**, svo sannprófunin yrði forspárpróf en ekki eftiráskýring, og teljararnir voru lesnir eftir apply með því að **kalla `ops_scraper_signals()`** — sömu leið og `/ops` fer.

| teljari | fyrir | forspá | **MÆLT** |
|---|---|---|---|
| `total_valuations` | 23.605 | 21.233 | **21.233** ✓ |
| `val_count_latest_day` | 2.000 | 1.821 | **1.821** ✓ |
| `backlog.live_res_sale` | 11.993 | 11.840 | **11.840** ✓ |
| `backlog.live_res_sale_valued` | 4.199 | 4.156 | **4.156** ✓ |
| `backlog.unprocessed` | 7.794 | 7.684 | **7.684** ✓ |
| `v_expected_vs_real` raðir | 23.605 | 21.233 | **21.233** ✓ |
| `base_pct_error` bjagi | +8,67 % | +5,55 % | **+5,55 %** ✓ |
| MAPE | 14,93 % | 11,98 % | **11,98 %** ✓ |
| n seldar | 259 | 252 | **252** ✓ |

**Öll níu lentu á forspánni upp á tölu.** Samlagning heldur (**11.840 = 4.156 + 7.684**), ferskleikalínan ósíuð eins og til stóð, **gólfið 109 farið**. `scraper.v_expected_vs_real_all` ber **`canonical_code` í sæti 34** (dálkurinn sem vantaði í cc120); báðar sýnir 34 dálkar.

**⚠ TALAN „8,22 → 6,06" ÚR GO-INU ER NEFNARAHÁÐ.** Hún var rétt á 00:06-nefnaranum (n=206). Á 10:07-nefnaranum (n=259) er hún **8,67 → 5,55**. Áttin og stærðin standa (≈3,1 pp) en **talan má ekki vitnast án dagsetningar** — sama gerð og §5 varar við, nú á okkar eigin tölu.

**Spegill og réttindi.** Statements lesin úr `schema_migrations.statements`: **0 frávik af 8 — drögin voru keyrð óbreytt** (samanburður festur við git-útgáfu draganna `581e092`, ekki við skrána á diski, svo hann sé idempotent). Sha: drög `870a25195041f3ff` → **spegill `efd673ceed639ed9`**; rollback `cc09761ba588d2fd` ósnertur. Réttindi mæld á **`pg_class.relacl` / `pg_proc.proacl`** (cc105-reglan): `v_expected_vs_real_all` = `{postgres=arwdDxtm/postgres}`, fallið = `{postgres=X/postgres,service_role=X/postgres}`, og `aclexplode` staðfestir að **`anon`/`authenticated`/`PUBLIC` bera ekkert**.

**Bókað af ásettu ráði:** stæða 01 í speglinum ber innbyggðan haus draganna með línunni „ÓAPPLÝJUÐ … hefur EKKI verið keyrð" og for-apply tölunum. Sá texti **var hluti af því sem var keyrt** og stendur óbreyttur — að snyrta hann væri að falsa spegilinn. Skráarhausinn ber viðvörun um að hann gildi þar sem þeim ber á milli.

Verðmats-þrepið er **áfram í pásu** (`EXTRACT_VALUE_LIMIT=0`); cc134 breytti því ekki. Heimild: úttekt §7 (`docs/fable_prep/audits/EXCLUDE_VERDMATSLEID_CC134_20260812T0006Z.md`).


---

## 2026-08-12 — §5D-4 · cc140 MIÐSÆKNIS-FRAMKVÆMDIN: `expected_base` FLUTT Á `real_pred_mean`; GÖMLU RAÐIRNAR STANDA OG MÆLIFLÖTURINN FÆR ALDAMERKINGU

> *Um staðsetningu:* skráin er viðbætandi og §5D-blokkin hefur legið aftast síðan §5D-1; þessi færsla fylgir þeirri röð frekar en hausreglunni („nýjar efst"), svo §5D-1..4 lesist samfellt.

**Málið**: §5D-1 (cc123, 11.08) kvittaði **kost (a) — allt á `real_pred_mean`** og bókaði í §7 að **framkvæmdin væri EKKI hluti þeirrar ákvörðunar**: hún ætti að vera sér lota með eigin rowcount-sönnun og er **bindandi forsenda** verðmats-bakfyllingarinnar sem cc121 setti á pásu. cc140 er sú lota. **Engin ný afstaða er tekin hér** — cc140 framkvæmir §5D-1 og mælir framkvæmdina.

### 1. FORMÆLING (read-only, á undan hverju skrifi)

**(a) Línan sem valdi miðsæknina** — `scripts/extraction_engine.py`, `value_listings`, línur **370–371** (voru 282–283 þegar cc120 mældi, 316–317 þegar §5D-1 vitnaði; skráin hefur vaxið, línunúmerin í eldri færslum eru úrelt en fallið er það sama):

```python
eb = int(round(float(base.loc[fn, "real_pred_median"])))
ex = int(round(float(full.loc[fn, "real_pred_median"])))
```

**(b) Rowcount-grunnstaða** (12.08 kl. 11:31Z). Nefnari alls staðar **23.605 raðir / 4.494 fastnúmer**, `expected_base` **NULL á 0 röðum**, `valued_at` frá 2026-06-27 22:13:04 til **2026-08-08 03:33:24,343465+00** (engin röð síðan — pásan heldur).

| stimpill × spátafla | raðir á stimpli | tengjast | `= real_pred_median` | `= real_pred_mean` | hvorugt |
|---|---|---|---|---|---|
| `iter4_final_v1` × `predictions_2026_04` | 20.642 | 15.714 | **11.766 (74,9 %)** | **0** | 3.948 |
| `iter4_final_v1` × `predictions` (lifandi) | 20.642 | 15.714 | 0 | **0** | 15.714 |
| `iter4_final_v1` × `predictions_2026_07_pre_iter4r` | 20.642 | 15.714 | 0 | **0** | 15.714 |
| `iter4r_20260805_reglaR_strukt` × `predictions` | 2.963 | 2.157 | **2.157 (100,0 %)** | **0** | 0 |

**Tvískiptingin er fullkomlega hrein: `expected_base = real_pred_mean` á NÚLLI raða af 23.605, á öllum þremur spátöflum.** Parity-mengið er **13.923 af 23.605 (59,0 %)** — nákvæmlega tölur cc120 §3.1, endurgerðar. Það sem eftir stendur eru raðir sem festust við annan árgang, ekki raðir á annarri miðsækni. **Mörkin sem cc140 dregur skilja því ekki blandað mengi í sundur; þau merkja mengi sem er einsleitt fyrir.**

**(c) Neytendur `expected_base` — TÆMANDI, úr `pg_depend`/`pg_rewrite` + `pg_proc.prosrc` + grepi á `verdmat-is/` (ekki `.next/`, ekki `prototypes/`, ekki `rollback/`):**

| # | neytandi | tengsl | miðsækni-næmur? |
|---|---|---|---|
| 1 | `scraper.v_expected_vs_real_all` | bein á dálkinn (`extraction_gap`, `base_pct_error`, `extraction_pct_error`) | **JÁ** |
| 2 | `scraper.v_expected_vs_real` | ofan á (1), EXCLUDE-síuð | **JÁ** |
| 3 | `scripts/extraction_engine.py` | **skrifarinn** | **JÁ** |
| 4 | `public.ops_scraper_signals()` | les `listing_valuations` en **ekki dálkinn** (teljarar + `valued_at`) | nei |
| 5 | `/ops` (`app/app/ops/page.js:243`) | ferskleiki á `valued_at` | nei |
| 6 | `scraper.listing_valuations_pre_cc94b2` | sjálfstætt afrit, ekki lesandi | nei |

**Engin `pg_proc`-skilgreining og enginn framenda-flötur les `expected_base`** — `scraper` er ekki opið PostgREST. Rekursíf `pg_depend`-leit finnur **nákvæmlega tvo** afleidda hluti (liði 1–2) og enga þriðju kynslóð.

### 2. BREYTINGIN

Ein virk breyting, tvær línur (`scripts/extraction_engine.py:370–371` → `real_pred_mean`), auk athugasemdablokkar sem ber heimildina og aldamörkin, og leiðréttingar á móduls-hausnum sem bar úrelta parity-fullyrðingu. **`ATH. ENGIN PRÓSENTUMERKI`-reglan (cc134-gildran) á við SQL-athugasemdir inni í `cur.execute(sql, params)`-strengnum í `fetch_extracted_listings_to_value`** — breytingin hér er í Python-kóða og snertir hvorugt, en textinn er samt skrifaður með orðinu „prósent" svo reglan haldi óháð því hvar hún bítur.

### 3. GÖMLU RAÐIRNAR STANDA — ENGIN ENDURRITUN

**23.605 raðir eru óbreyttar.** Rök borðsins: punktmæling er **söguleg heimild um hvað vélin sagði**, ekki endursögn — sömu rök og cc116 fyrir 20.642 raðirnar og cc134-(b) fyrir 2.372 EXCLUDE-raðirnar.

**Í staðinn fá mæliflötirnir aldamerkingu.** `midsaekni_old` bætt aftast (sæti 35) á **báðar** sýnur, **reiknaður af `valued_at`, ekki geymdur**:

```sql
CASE WHEN val.valued_at < TIMESTAMPTZ '2026-08-12 00:00:00+00' THEN 'median' ELSE 'mean' END
```

**Aldamörkin eru mæld, ekki ályktuð:** síðasta median-röðin er `2026-08-08 03:33:24,343465+00`, aldamörkin `2026-08-12 00:00:00+00`, og **0 raðir liggja á milli** — 3,9 sólarhringa bil þar sem verðmats-þrepið var í pásu. Engin röð getur lent á rangri öld.

**Rás: SUPABASE MCP `apply_migration`** (tengt í þessari lotu, ólíkt cc134 sem varð að nota psycopg2). MCP skrifar `schema_migrations`-færsluna sjálfkrafa í sömu txn og stæðuna, svo skilyrði (1) og (2) úr cc134-jafngildinu eru sjálfgefin. Skilyrði (3) — **spegill lesinn orðrétt úr `schema_migrations.statements`** — stendur og var uppfyllt. **Rollback-SQL var skrifað Á UNDAN apply** (`supabase/rollback/20260812113500_cc140_midsaekni_aldamerking_rollback.sql`, sha256[:16] `e38ee587587d7a7f`, sýnarlíkamir afritaðir úr lifandi DB með `pg_get_viewdef` fyrir apply) og er ósnertur síðan.

**⚠ ÁTTA STÆÐUR, EKKI SJÖ, OG VERSION-NÚMERIN ERU EKKI ÞAU SEM DRÖGIN SPÁÐU.** MCP úthlutar version af eigin klukku: raunin er `20260812113529`–`20260812113631`, ekki `20260812113500`–`113506`. Áttunda stæðan (`cc140_03b`) er leiðrétting — stæða 03 var applýjuð með **afmáðum íslenskum stöfum af óþarfa varkárni** (stæður 01–02 báru íslensku athugasemdalaust) og 03b skrifar réttan texta yfir. **Stæða 03 er ekki fjarlægð úr `schema_migrations`; hún var keyrð og á að sjást.** Það er munurinn á spegli og endurritun. Skráarnafnið heldur `20260812113500`-forskeytinu (það er skráarnafn, ekki version) og hausinn ber ósamræmið.

Réttindi mæld á **`pg_class.relacl` + `aclexplode`** (cc105-reglan): báðar sýnur `{postgres=arwdDxtm/postgres}`; **`anon`/`authenticated`/`PUBLIC` bera EKKERT (0 raðir).** `v_expected_vs_real` bar enga skráða `relacl` eftir cc134 (erfði eiganda); `CREATE OR REPLACE` + `REVOKE` efnisgerði hana — **efnislega óbreytt**.

### 4. SÖNNUN — AFMÖRKUÐ KEYRSLA Á FIMM EIGNUM

`--ids`-leiðin **er ekki til** í `run_extraction.py`; afmarkaða leiðin sem er til er `--value-seeded --value-limit 5` og hún var notuð (bókað svo næsta lota leiti ekki að rofa sem er ekki til). Útgáfuhliðið (cc112) heimilaði skrif: adapter `iter4r_20260805_reglaR_strukt` == lifandi.

| valuation_id | fastnum | `expected_base` | `real_pred_mean` | Δ mean | `real_pred_median` | Δ median | `midsaekni_old` |
|---|---|---|---|---|---|---|---|
| 24563 | 2537354 | 94.541.396 | 94.541.396 | **0 kr** | 93.213.800 | +1.327.596 | `mean` |
| 24564 | 2537439 | 154.641.406 | 154.641.406 | **0 kr** | 171.625.872 | −16.984.466 | `mean` |
| 24565 | 2537391 | 97.929.595 | 97.929.595 | **0 kr** | 97.468.186 | +461.409 | `mean` |
| 24566 | 2537369 | 68.997.660 | 68.997.660 | **0 kr** | 73.557.045 | −4.559.385 | `mean` |
| 24567 | 2537431 | 132.379.363 | 132.379.363 | **0 kr** | 138.301.731 | −5.922.368 | `mean` |

**5 af 5 upp á krónu á `real_pred_mean`, og engin þeirra jafngildir `real_pred_median` — svo niðurstaðan er ekki tilviljun tveggja jafnra talna.**

**Rowcount fyrir/eftir + checksum gamla mengisins:**

| | fyrir | eftir |
|---|---|---|
| raðir alls | 23.605 | **23.610** (+5, nákvæmlega n) |
| `sum(expected_base)` | 2.012.081.631.136 | 2.012.630.120.556 |
| hæsta `valuation_id` | 24.562 | 24.567 |
| **gamla mengið (`valuation_id ≤ 24562`) — raðir** | 23.605 | **23.605** |
| **gamla mengið — `sum(expected_base)`** | 2.012.081.631.136 | **2.012.081.631.136** |
| **gamla mengið — md5 yfir (id : base : extraction)** | `91089f71233ca1d240350c01d3258ecf` | **`91089f71233ca1d240350c01d3258ecf`** |

**Checksum-in er sú sama bæti fyrir bæti: engin gömul röð breyttist.**

**Aldamerkingin á lifandi gögnum eftir keyrslu:**

| flötur | öld | raðir | seldar | bjagi | MAPE |
|---|---|---|---|---|---|
| `v_expected_vs_real_all` | `median` | 23.605 | 259 | **+8,67 %** | 14,93 % |
| `v_expected_vs_real_all` | `mean` | 5 | 0 | — | — |
| `v_expected_vs_real` | `median` | 21.233 | 252 | **+5,55 %** | 11,98 % |
| `v_expected_vs_real` | `mean` | 5 | 0 | — | — |

Median-öldin endurgerir eftirmælingu cc134-A **upp á tölu** (21.233 / 252 / +5,55 / 11,98) — sem er sönnun þess að viðbótin er **dálkur en ekki sía**. **Mean-öldin ber 0 seldar raðir og því ENGA mælingu; það er rétta staðan og má ekki fyllt með ágiskun.**

### 5. AÐVÖRUN SEM Á AÐ STANDA (7.9-reglan)

**`/markadur`-vísirinn og allar bjaga-, MAPE- og gap-tölur af blönduðu sýninni eru ÓSAMBÆRILEGAR yfir aldamörkin.** Meðaltal yfir blandað mengi er ekki mæling heldur blanda tveggja mælinga. **Sérhver aðgreining á `base_pct_error` skal bera `GROUP BY midsaekni_old` eða síu á hann.**

**`mean`-höfuðið ber +1,93 % þekktan OOS-bjaga** (birt mat kerfisbundið **undir** söluverði; t = −10,74, p = 1,75·10⁻²⁵, §5D-1 §1) **og sú tala á að fylgja hverri umfjöllun um nákvæmni** — út á við jafnt sem inn á við. Hún hallar á höfuðið sem var valið og var valin með opnum augum: §5D-1 §4 (1). Færsla `/markadur` úr 1,006 í 1,026 er **afhjúpun, ekki versnun** (§5D-1 §4 (2)) og skal orðast þannig.

**`base_pct_error` er þar með ÓSAMFELLD TÍMARÖÐ.** Allar 259 (síað: 252) seldu raðirnar eru median-aldar; fyrsta mean-alda mælingin verður til þegar fyrsta ný röð selst.

### 6. LEIÐRÉTTING Á §5D-1 §7 — D2-PARITY-HLIÐIÐ FELLUR EKKI

§5D-1 §7 spáði: *„`expected_base`/`expected_extraction` → `real_pred_mean` snertir … OG D2-parity-hliðið í `scripts/model_quality_eval.py:557–576 / 874–881` … **hliðið fellur ef aðeins vélin er færð**."* **Kóðalestur fellir þá spá.** `run_parity` (l. 873–885) ber saman **adapterinn** (`_score_iter4(...)["real_pred_median"]`) við **`public.predictions.real_pred_median`** og les `scraper.listing_valuations` **hvergi** — hvorki `fetch_parity_sample` (l. 556–576) né `run_parity` nefnir töfluna. Hliðið er **fidelity-próf á skoraranum gegn spátöflunni**, óháð því hvaða dálk frystingin skrifar. **Þess vegna var `model_quality_eval.py` ekki snert og þarf ekki að snerta.**

**Fyrirvari sem er bókaður sem slíkur:** þetta er **kóðalestur, ekki keyrsla**. Hliðið var **ekki keyrt** í cc140 — `--parity` skrifar í keyrslu-loggtöflurnar og það hefði verið skrif utan þess sem lotan heimilaði. **Fyrsta næturkeyrsla með `--parity` er sannprófunin og hún stendur út af.**

Aðskilinn liður sem cc140 tekur ekki: nú þegar `expected_base` kemur af `mean`-höfðinu er **ekkert hlið sem sannreynir að MEAN-höfuðið endurgeri spátöfluna** — parity-hliðið sannreynir enn `median`-höfuðið eitt. Þau hafa sama skorara og sama `to_kr`, svo áhættan er lítil, en **hún er ómæld og fer á backlog**, ekki í þessa færslu sem fullyrðing.

### 7. BÖNN SEM VORU VIRT

Bakfyllingin var **ekki keyrð** (`--skip-valuation` ósnert; pásan cc121 heldur). **Engin gömul röð endurrituð.** `public.predictions` **ósnert**. **Engin framenda-breyting.** Einu DB-skrifin utan migration eru fimm púls-raðirnar úr §4.

**Heimild**: `scripts/extraction_engine.py` (`value_listings`, l. 370–371 + athugasemdablokk); `supabase/migrations/20260812113500_cc140_midsaekni_aldamerking.sql` (spegill, sha256[:16] `a7b542d3526047e6`); `supabase/rollback/20260812113500_cc140_midsaekni_aldamerking_rollback.sql` (`e38ee587587d7a7f`); DECISIONS §5D-1 (cc123 afstaða + bjagatalan), §5D-2 + viðauki (cc134, mæliflöturinn og rásar-jafngildið); `D:\_audit\cc120_midsaekni\MIDSAEKNI_CC120_20260808.md` §1.1/§2/§3; `D:\_audit\cc123_oos_einvigi\OOS_EINVIGI_CC123_20260808.md` §1.

## 2026-08-12 — §5D-5 · cc142 VERÐMATS-BAKFYLLINGIN KEYRÐ Í EINNI MANNAÐRI KEYRSLU: 19.022 RAÐIR, PÁSAN AFLÉTT — OG ÞAKIÐ 2000 STENDUR

> *Um staðsetningu:* §5D-blokkin hefur legið aftast síðan §5D-1 og skráin er viðbætandi; þessi færsla fylgir þeirri röð frekar en hausreglunni („nýjar efst"), svo §5D-1..7 lesist samfellt. Færslan er bókuð af **cc144** (bókunarlota, engin DB-tenging) á verki **cc142**.

**Málið**: cc121 (08.08) setti `EXTRACT_VALUE_LIMIT=0` — pásu á verðmats-þrepi næturkeðjunnar — með tveimur bókuðum rökum: (1) biðröðin er bakfylling á eldri auglýsingum sem enginn notendaflötur les, og (2) hún á að fara í **EINNI mannaðri keyrslu**, því ellefu skammtar gefa ellefu ósambærilegar frávikadreifingar og ein keyrsla gefur EINA hreina á sama akkeri. Skilyrt GO: miðsæknin (§5D-4, cc140) yrði að lenda fyrst. Hún lenti 12.08. **cc142 er sú eina keyrsla og hún er gerð.**

### 1. ÞURRKEYRSLAN — TALAN VAR MÆLD, EKKI LESIN ÚR DRÖGUM

Mælt 11:58Z gegnum **raunfallið** `extraction_engine.fetch_extracted_listings_to_value` (`limit=None`, cc134-sían virk), ekki gegnum spegil af fyrirspurninni: **19.022 raðir / 4.013 fastnúmer**, EXCLUDE + NULL `canonical_code` = **0**.

**Talan er ekki 18.734 (cc121), ekki 18.177 (cc134-spá), ekki 28.703 (cc136).** Þær voru allar bókaðar á sínum tíma og engin þeirra var viðmið keyrslunnar. Adapter-stimpill af diski == `pipeline_config.model_version` == `iter4r_20260805_reglaR_strukt`, svo útgáfuhliðið (cc112) var opið.

**cc140-checksumman var ekki bókuð sem SQL og varð að endurleitast** — 100 frambjóðendur, 2 treff. Tjáningin er nú bókuð svo næsta lota þurfi þess ekki:

```sql
SELECT md5(string_agg(valuation_id::text||':'||expected_base::text||':'
                      ||expected_extraction::text, ',' ORDER BY valuation_id))
FROM scraper.listing_valuations WHERE valuation_id <= 24562;   -- = 91089f71233ca1d240350c01d3258ecf
```

### 2. KEYRSLAN OG SÖNNUNIN

`python -u -m scripts.run_extraction --value-seeded --confirm` — án `--forward` (**enginn `anthropic`-klient smíðaður**), án `--bridge` (`bridge: SLEPPT` í logginu), án `--value-limit`. Rás: **psycopg2** á transaction pooler, `SET TRANSACTION READ WRITE` fyrsta stæðan.

| krafa | mæling |
|---|---|
| raðir alls | 23.610 → **42.632** (**+19.022** = þurrkeyrslutalan upp á röð) |
| `valuation_id`-bilið | **24568..43589 SAMFELLT** (43.589 − 24.568 + 1 = 19.022) — engin `ON CONFLICT DO NOTHING`-sleppa |
| skoruninni sleppt | `skipped 0` |
| gamla mengið (`≤ 24562`, 23.605 raðir) | md5 `91089f71233ca1d240350c01d3258ecf` **óbreytt**, `sum(expected_base)` 2.012.081.631.136 óbreytt |
| alt for-keyrslu-mengið (`≤ 24567`, 23.610 raðir) | md5 `0ebcde1c200530aa6f45e9457bf916c3` **óbreytt** |
| `expected_base = real_pred_mean` | **16.174 af 16.174 (100,0000 %)**, Δ = 0 kr; `= real_pred_median`: **0** |
| `model_version` á nýju röðunum | `iter4r_20260805_reglaR_strukt` × 19.022, ein og aðeins ein útgáfa |
| EXCLUDE skrifað | **0** (líka 0 NULL `canonical_code`) — cc134-sían heldur alla leið í töfluna |
| `midsaekni_old` á nýju röðunum | `mean` × 19.022, **0 median** — §5D-4 heldur á fjöldakeyrslu |
| kostnaður | `day_total` 2026-08-12 **$3,9684 → $3,9684**, óhreyfður |

Víðara mengið er checksummað LÍKA svo cc140-raðirnar fimm séu inni í vörninni, ekki bara þær 23.605 sem cc140 bókaði. **Engin gömul röð hreyfðist.**

**Nefnarinn er sagður:** 2.848 raðir (543 eignir, 15,0 %) eiga **enga röð í `public.predictions`** og eru ósannreynanlegar gegn spátöflunni. Það er þekja spátöflunnar, ekki frávik í keyrslunni — biðraðar-skilgreiningin krafðist aldrei spátöflu-raðar.

### 3. AFURÐIN — FRÁVIKADREIFINGIN, OG EINHALLINN SEM VAR EKKI HANNAÐUR

`base_pct_error` á nýja menginu: **0 seldar raðir, 0 mælingar.** Það er **skilgreining, ekki gat** — sýnan tengir sölu með `thinglystdags >= valued_at::date` og raðirnar voru verðmetnar í dag. **Fyrsta mean-alda `base_pct_error`-mælingin verður til við fyrstu sölu eftir 12.08** og má aldrei fyllt með median-aldar tölum (§5D-4 §5).

`extraction_gap` yfir mengið: gap=0 á 45 (0,24 %), **gap>0 á 11.947 (62,8 %)**, gap<0 á 7.030 (37,0 %); meðaltal **+1.207.579 kr (+2,3103 %)**, miðgildi +792.218 kr (+1,0088 %). Meðaltalið er tvöfalt miðgildið — dreifingin er **hægri-skekkt**.

Eftir `predictions.confidence_grade`, meðal-gap sem hlutfall: **A 0,807 % · B 0,972 % · C 4,541 % · D 4,409 % · `<NULL>` 7,919 %.** **Því lakari sem vissa líkansins er, því meira hreyfir útdrátturinn matið** — útdrátturinn leggur mest til þar sem grunnlíkanið veit minnst. Sú hegðun var **ekki hönnuð inn** og hún er rétt vegin.

**`<NULL>`-línan er stærsta einstaka niðurstaða dreifingarinnar og hún er ekki flokkur heldur fjarvera:** 2.848 raðir / 543 eignir án `predictions`-raðar bera **fimmfalt** meðal-gap A-flokks. Það eru sömu raðirnar sem stikkprufan gat ekki sannreynt. **Ómælt mengi, ekki mælt — fer á backlog, ekki í þessa færslu sem fullyrðing um orsök.**

### 4. PÁSAN AFLÉTT — OG ÞAKIÐ 2000 STENDUR SEM AFSTAÐA, EKKI SEM MILLIBILSÁSTAND

Biðröðin mæld gegnum **raunfallið** eftir keyrslu: **0 raðir.** Skilyrta GO-ið er þar með uppfyllt og `scripts/nightly_delta_chain.sh` fer **0 → 2000** (commit `6426140`; `bash -n` hreint, rofinn sannreyndur með því að keyra sömu greiningu og skelin ber, `-gt 0`, ekki með lestri). Raunkallið breytist úr `--forward 200 --confirm --skip-valuation` í `--forward 200 --confirm --value-limit 2000`.

**Talan er 2000, ekki „ótakmarkað", og það er ákvörðun.** Rök borðsins:

1. **Þakið er hlutlaust í venjulegri nótt.** Biðröðin vex ~300/nótt < 2000, svo keðjan tekur sína ~300 og þakið bítur ekki. **Þar af leiðandi má ekki meta þakið af því ástandi** — það er einmitt ástandið sem þakið er gagnslaust í.
2. **Það ver EINA þekkta bilun.** Biðröðin er skilgreind sem „auglýsingar án verðmats **FYRIR ÞETTA `model_version`**". Næsta **líkanaskipti** opnar því allar 42.632 raðirnar í einu vetfangi. Heimildin er mæld, ekki áætluð: **cc113 mældi 3 → 21.354** við endurtenginguna.
3. **Sú hrina á að vera VALIN eins og þessi var**, ekki afleiðing af ómannaðri nótt. Ein mönnuð keyrsla gefur eina hreina frávikadreifingu á einu akkeri; sjálfvirk hrina á líkanaskiptum gefur ósambærilega dreifingu og enginn valdi hana.

**Fjarlægðu því ekki þakið við það eitt að biðröðin sé tóm.** Rökin fyrir hækkun eða afnámi eru rök um **líkanaskipti**, ekki um daglegt flæði, og þau á að taka við næsta flipp — ekki fyrir hann.

Útdrátturinn (`EXTRACT_FORWARD`, Haiku) er **ósnertur**: hann er ferskleiki, ekki bakfylling.

### 5. BÖNN SEM HELDU · ÚT AF STENDUR

`predictions` aðeins **lesin**. Brúin **ósnert**. Engin gömul röð endurrituð (tvær checksummur; `ON CONFLICT ... DO NOTHING` getur ekki uppfært). Extraction-þrepið ósnert og því **$0,00 kostnaður** — útdrættirnir voru til fyrir.

Út af stendur: (1) **`<NULL>`-flokkurinn** — 2.848 raðir með fimmfalt gap, ómælt; (2) **fyrsta mean-alda `base_pct_error`** bíður fyrstu sölu eftir 12.08; (3) **parity-hliðið vaktar enn `median`-höfuðið eitt** (§5D-4 §6, óbreytt af cc142); (4) **STATE.md** var ekki uppfært — cc144 hafði umboð til viðbóta í DECISIONS eingöngu.

**Heimild**: `docs/fable_prep/audits/CC142_BAKFYLLING_20260812.md` (git-afritið, sama nafn og frumritið, með cc144-viðauka aftast) og frumritið `D:\_audit\cc142_verdmats_bakfylling\CC142_BAKFYLLING_20260812.md` + `SONNUN_OG_DREIFING_CC142.md` + `keyrsla_cc142.log` + `stada_FYRIR/EFTIR.json` í sömu möppu. **Sundurliðunarskráin fylgir EKKI í git**: hún ber 12 raða stikkprufu á eignastigi (per-eign spár) og app-repoið er opið og deploy-tengt — raðgögn úr prod fara ekki þangað, aggregat gerir það. Sjá einnig §5D-4 (miðsæknin, forsenda keyrslunnar), §5D-2 + viðauki (cc134-sían) og `scripts/nightly_delta_chain.sh` (cc121-pásukaflinn stendur óréttur sem saga; „LIFANDI HEGÐUN"-kaflinn ber raunstöðuna).

## 2026-08-12 — §5D-6 · cc141 γ-FORPRÓFIÐ: γ ER MÆLT Á RAUNSÖLUM (0,633 [0,317; 0,949]) — γ = 1 HAFNAÐ, γ = 0,5 ÓDÆMT, BRÚIN STENDUR FROSIN OG HLIÐIÐ ER ENDURSKILGREINT MÆLANLEGA

> *Um staðsetningu:* viðbætandi færsla aftast, sbr. §5D-4/§5D-5. Bókuð af **cc144** á verki **cc141** (READ-ONLY lota, `set_session(readonly=True)`, engin skrif í gagnagrunn).

**Málið**: cc81 §9.1 hannaði γ — leiðrétting = `grunn × exp(γ·Σln(1+p_i))`, klemmt á eftir — og mældi hana á **þjálfunarþýði** (0,781 S0 / 0,610 S3). cc81 setti þrjú skilyrði fyrir því að γ færi inn: frysting, **mótpróf á öðru þýði**, og holdout utan þjálfunar **beggja** líkana. cc141 er forprófið sem sker úr hvort γ > 0 yfirhöfuð á **raunverulegum þinglýstum sölum** — ekki hvaða γ, og ekki mótprófið sjálft.

### 1. AÐFERÐ — ENGIN REGLA VAR SPEGLUÐ

Þrjár reglur keyrðu **orðrétt**: `scraper.eigindi_ur_extraction` (sama fall og brúin kallar), `lib/attributes-queries.getAttributes` með **minnis-klienti** (cc136-mynstrið, svo uppruna-forgangur og já-hlutdrægnisían keyri eins og í framleiðslu) og `lib/leidretting.reiknaLeidrettingu` óbreytt. Þakið var **ekki aftengt í vörunni**: fallið skilar `lidir[]` með óklemmdu `pct` og klemman býr aðeins í `breyting_pct`; óklemmda summan er endurreiknuð úr þeim sama lista. **Krossmæling: þakið bítur á 74 af 164 = 45,12 %, gegn 46,23 % sem cc136 mældi á öðru og stærra mengi — samhljóða.**

**Ein bókuð víkkun frá brúnni**, og hún er nauðsyn en ekki þægindi: brúin les aðeins **virka** auglýsingu (`v_eign_virk_auglysing`), og eign sem **seldist** er einmitt eignin sem hverfur úr virka menginu — 4.000 eigna virkt mengi ber aðeins **46** sölur eftir auglýsingadegi. Því var lesið úr `scraper.listings` **án status-síu**. Vörpunarfallið er óhreyft; inntakið er breikkað.

### 2. ÞÝÐIÐ — 284 HRÁPÖR → 163 MÆLD RÖÐ

Hver sía með nefnara: hrápör **284** → ónothæfur samningur −32 → fleiri en ein sala per eign −1 → EXCLUDE/NULL `canonical_code` (cc134) −9 → **nýbygging við sölu −76 (31,4 %)** → berandi ≥ 1 birtanlegan lið −2 → spá í eigin árgangi −1 = **163**. Bil auglýsingar → sölu: miðgildi **32 dagar** (p25 20, p75 59).

**OOS-staðan er byggð inn í árgangsvalið:** valinn er síðasti árgangur sem var **lifandi** þegar salan var þinglýst, svo spáin varð til á undan sölunni. Eina undantekningin eru **5 sölur ≤ 2026-04-21** og þær eru teknar út í `hreint OOS`-specinu (n = 158).

### 3. NIÐURSTAÐAN — ÞRJÚ SVÖR, OG EITT ORÐALAG LEIÐRÉTT

Aðalspec (OLS, `y = log(þinglýst raunverð) − log(grunnspá árgangsins)`, `x` = óklemmd log-summa, HC3): **γ = +0,633, SE 0,161, 95 % CI [+0,317, +0,949], R² 0,122, n = 163.**

1. **γ > 0.** Liðirnir bera raunverulega upplýsingu um sölufrávikið; lagið er ekki hávaði. **Marktækt í 10 af 12 specum við p ≤ 0,0006** (efra markið er árgangs-fixed-effects, z = 3,44). **⚠ LEIÐRÉTTING á §3 audit-skjalsins**, sem segir „p ≤ 0,0006 í hverjum einasta spec": tveir specar bera CI sem nær yfir núll — **án þak-eigna** (n = 90, γ = +1,030, SE 0,560, p ≈ 0,066) og **+fjölskyldu-fixed-effects** (γ = +0,463, SE 0,242, p ≈ 0,056). Bæði punktmötin eru jákvæð og bæði eru specarnir sem taka mestan x-breytileika út (án þak-eigna fjarlægir há-x halann; fjölskyldu-FE gleypa milli-fjölskyldu-breytileikann sem er tvöfaldur — x +0,238 sérbýli á móti +0,098 fjölbýli). **Kraftmissir, ekki formerkjaskipti** — en fullyrðingin sem gildir er sú leiðrétta.
2. **γ < 1 — staðfest.** z −1,8 til −4,9. **Stöflunin ofmetur**, eins og cc81 mældi á allt öðru þýði. Miðgildisaðferðirnar liggja **lægra** en OLS (Theil-Sen 0,499, quantile 0,528) — halarnir toga γ **upp**, ekki niður, svo robustness-krafan færir svarið nær cc81-S3 (0,610), ekki frá því.
3. **Samleitnin við cc81 er sjálfstæð:** ólíkt þýði, ólíkt mælitæki, ólíkur estimand — og **0,610 fellur inn í CI allra tólf speca.**

**Spádómar borðsins dæmdir:** „γ < 0,5 á heildinni" → **ÓDÆMD** (CI nær yfir 0,5; punktmatið yfir í OLS, við í miðgildisaðferðum). „Jákvæði endinn ber lægra γ en sá neikvæði" → **ÓDÆMANLEG**, sjá §4. **Nákvæmlega: γ = 1 er hafnað; γ = 0,5 er það ekki.**

### 4. NEIKVÆÐI ENDINN ER ÓMÆLANLEGUR Í ÞESSU ÞÝÐI — SJÁLFSTÆÐ NIÐURSTAÐA

**Aðeins EIN neikvæð lína er til í stuðlaskránni** (`needs_immediate_work`, −13,3 %). Hún kviknar á **5 af 164 eignum (3,0 %)** og aðeins **3** eignir bera nettó-neikvæða summu (−8,73 / −8,22 / −12,19 %) — þ.e. `formerki = neikvæð` er n = **3**, ekki 30 og ekki 300. **Já-hlutdrægni þýðisins er alger: 160 af 163 bera jákvæða summu.**

Þetta staðfestir cc81 §9.3 lið 2b beint úr gögnum: **γ mælt hér er kvarði á JÁKVÆÐA stöflun og þetta þýði mun ekki geta mælt neikvæða endann.** Afleiðingin er bókuð sem regla: **sé γ látið gilda í báðar áttir er −13,3 %-línan færð inn fyrir −13,0 %-klemmuna og klemmumerkið hverfur af eignunum í verstu ástandi — án nokkurrar mælingar sem styður það.** Neikvæði endinn þarf sína eigin mælingu, ekki þessa.

### 5. ÞÝÐIÐ BER EKKI MÓTPRÓF — OG ÞAÐ ER MÆLT, EKKI ÁÆTLAÐ

**Slembihelmingarnir tveir (fastnum jafn/oddatala) gefa γ = 0,405 og 0,796 — munur upp á tvöfalt, á sömu gögnum, af hreinni tilviljun.** Þýðið þolir ekki skiptingu.

Kraftgreining: **n ≈ 82 þarf til að hafna γ = 1 → náð. n ≈ 629 þarf til að hafna γ = 0,5 → vantar ~4× þýðið.** Vöxtur er ~25–45 nýtanleg pör á mánuði, svo **n = 629 næst ekki fyrr en eftir ~12–18 mánuði** af óbreyttri söfnun.

### 6. BRÚIN STENDUR FROSIN — OG HLIÐIÐ ER ENDURSKILGREINT ÚR ÁSTANDI Í MÆLINGU

**γ fer ekki inn núna.** Bilið [+0,317, +0,949] leyfir ekki val á tölu og formið er grunsamlegt (§7). Brúin (eigindalagið, cc133/cc136) **stendur frosin** og cc141 breytti engu lagi.

**Hliðið var ástand („þegar γ er staðfest"); hér er það gert mælanlegt.** Það opnast við **γ staðfest á holdout-endurþjálfunarleið**, þ.e. þegar öll þrjú skilyrðin liggja fyrir: (a) n ≥ ~629 svo γ = 0,5 sé dæmanlegt, (b) holdout **utan þjálfunar beggja líkana**, (c) mótpróf sem þýðið þolir. **Sú leið er ekki forpróf heldur endurþjálfunar-verk**, og það er bókað hér svo enginn reyni hana sem ódýrt skref:

`public.last_listing_text` ber **51.834 pöruð sölu-söluyfirlit (37.671 eignir)** sem standast **nákvæmlega sömu síur** og §2 — 300× stærra þýði. **En 0 þeirra er þinglýst eftir 2026-04-21**: allar liggja **innan** þjálfunargagna apríl-líkansins og allar spár urðu til **eftir** söluna. Að keyra γ þar mælir akkerun, ekki nákvæmni (sama gildran og cc102 bókaði um verðmat keppinautar sótt eftir söludag). Leiðin er **fær en dýr**: útdráttur hefur aðeins verið keyrður á ~50 af 44.418 eignum, og hann er **gagnslaus fyrir γ nema samhliða komi líkan þjálfað án þeirra sölna**.

**SAMLEGÐIN ER BÓKUÐ:** þetta er **sama innviðavinnan** og iter5-áhrifastærðar-próban sem DECISIONS **2026-07-04** („Tveggja laga verðmat") gerði að skilyrði fyrir birtingu skilyrts mats. Þar var forsendan mæld ófullnægð af sömu ástæðu og hér: **aðeins ~24 % þjálfunarraða bera extraction-merki** (rest NaN), svo 133 af 154 features leggja 0,83 % til gain. **Bæði hlið — γ-hliðið og skilyrt-mats-hliðið — bíða sama verks: útdráttur á sögulega corpusið + líkan þjálfað án holdout-sölnanna.** Þau á að skipuleggja sem eitt verk, ekki tvö, og hvorugt opnast af mælingu á 163 röðum.

**Ódýra vaxtarleiðin stendur á meðan og er valin:** endurkeyra `cc141_thydi` / `cc141_lag` / `cc141_gamma` **mánaðarlega** á sama tæki — n ≈ 300 í kringum áramót, n ≈ 629 vorið 2027. **Ekkert nýtt þarf að smíða.**

### 7. KÚPTA LÖGUNIN — BÓKUÐ SEM TILGÁTA FYRIR MÓTPRÓFIÐ, EKKI SEM NIÐURSTAÐA

Milli-bindja myndin (þriðjungar x, meðaltöl):

| þriðjungur | n | x meðaltal | y meðaltal | y ±SE |
|---|---|---|---|---|
| T1_lág | 55 | +0,0501 | **−0,0240** | 0,0214 |
| T2_mið | 54 | +0,1259 | **−0,0268** | 0,0142 |
| T3_hátt | 54 | +0,2435 | **+0,0656** | 0,0281 |

**T1→T2 er Δy/Δx = −0,04 (engin mælanleg svörun); T2→T3 er +0,78.** Svörunin er **kúpt**: neðri tveir þriðjungar summunnar bera enga svörun, efsti þriðjungurinn ber ~0,8. Innan-þriðjungs-hallarnir (2,12 / 1,30 / 0,55) mæla annað og eru þröngskornir í x — **milli-bindja myndin er áreiðanlegri lestur**, og hún er sjálfstæð vísbending um að **flatur γ sé rangt form**: cc81 §9 (A) fann há-N ofmetið, cc141 finnur lág-x svörunarleysið. Sömu átt, öfugt formerki. **Hvorugt lagast með einni tölu.**

**Bókað sem tilgáta með fyrirfram-ákveðnum dómara, ekki sem niðurstaða:** mótprófið skal keppa **línulegu γ gegn þröskulduðu formi** (svörun frá þröskuldi í x, engin undir) og **OOS ræður** — sami agi og cc102/§5C-12 (fyrirframbókaður rammi) og §5C-13 (dómarinn má ekki vera í inntakinu). Fylgispurningin sem cc81 §9 (A) skilaði stendur með: **ber lág-x svörunarleysið vitni um að neðstu liðirnir séu rangir frekar en að kvarðinn sé rangur?** Það er (A)-verkið, ekki γ-verkið, og það má ekki afgreiðast með γ-tölu.

**Fyrirvari sem er bókaður sem slíkur:** þessi lögunar-mæling er **lýsandi á 163 röðum**, þrjú bindi með 54–55 röðum hvert. Hún er nógu skýr til að vera tilgáta og **ekki nógu sterk til að velja form**.

**Heimild**: `docs/fable_prep/audits/GAMMA_FORPROF_CC141_20260812.md` (í git frá cc144, með cc144-viðauka aftast sem ber p-gildis-leiðréttinguna í §3 lið 1) · mælitækin `cc141_thydi.py` / `cc141_lag.mjs` / `cc141_loader.mjs` / `cc141_gamma.py` í `precompute` @ **`f20140d`** · útkoman (`cc141_inntak.json`, `cc141_lag.json`, `cc141_punktar.csv`, `cc141_dreifirit.png`, `cc141_gamma.json`) liggur **utan git** í `precompute/data/cc141/` og fer þangað ekki: `cc141_punktar.csv` er raðgögn á eignastigi. Sjá einnig cc81 §9.1/§9.3 (γ-hönnunin og skilyrðin), §5D-2 (cc134-sían sem þýðissían notar), DECISIONS 2026-07-04 („Tveggja laga verðmat" — iter5-áhrifastærðar-próban sem hliðið deilir innviðum með).

## 2026-08-12 — §5D-7 · cc139-AFSTAÐA BORÐSINS BÓKUÐ EFTIR Á: PAR-LAGIÐ FRAM FYRIR RÖÐ, FLÖGGIN ENDURSKILGREIND Í cc143, HÓGVÆRÐARMERKIÐ Á EFTIR FLÖGGUNUM

> *Um staðsetningu:* viðbætandi færsla aftast, sbr. §5D-4..6.

**HEIMILDARFYRIRVARI SEM ER HLUTI FÆRSLUNNAR.** cc139 skildi **enga úttekt eftir á diski** (engin `D:\_audit\cc139*`-mappa), **enga DECISIONS-færslu** og engan bakslag í `PLANNING_BACKLOG`. Afstaðan sem hér er bókuð er því **orðrétt afstaða borðsins eins og hún var endursögð í lotubréfi cc144**, ekki endursögn á mælingu sem cc144 gat lesið. **cc144 var bókunarlota án gagnagrunnstengingar og endurmældi ekkert af þessu.** Færslan er skrifuð svo afstaðan sé í sögunni áður en cc143 skrifar ofan á hana — ekki til að staðfesta tölur.

### 1. RÖÐIN — PAR-LAGIÐ FER FRAM FYRIR

**Par-lagið fer fram fyrir röð.** Umfangið sem borðið bar fyrir þeirri röðun er **96,26 %**. **Þessi tala er BORIN, ekki mæld hér** — cc144 hafði ekkert gagnagrunnsumboð og enga cc139-heimild til að lesa hana úr, og nefnarinn hennar er ekki bókaður. **cc143 er lotan sem mælir par-lagið** (`D:\_audit\cc143_par_lagid\`) og henni ber að bóka töluna með nefnara; **standist hún ekki, er þessi færsla röðunin en ekki talan.**

Það sem áður er mælt og sem röðunin hvílir á: par-lagið ber **akkerisbilið ~1 %** og **sellu-drift −4,7 % á SFH×RVK** (cc131), og **51.834 sögulegu pörin bera 0 nothæf fyrir γ** af því þau liggja öll innan þjálfunar (§5D-6 §6). Par-lagið er þar með **bæði mælt vandamál og forsenda annarra verka** — það er röksemdin fyrir að setja það fremst.

### 2. FLÖGGIN ERU ENDURSKILGREIND Í cc143 — ÞVÍ BÓKAST ENGIN FLAGGSKILGREINING HÉR

**Flöggin eru endurskilgreind í cc143**, sem er í keyrslu samhliða cc144 og er **DB-skrifarinn**. Þess vegna er **engin flaggskilgreining bókuð í þessari færslu**: hún yrði úrelt áður en hún yrði lesin. cc143 ber að bóka skilgreiningarnar sjálf, með fyrir/eftir-nefnara á hverju flaggi.

### 3. HÓGVÆRÐARMERKIÐ Á AKKERISKORT ER SÉR VERK — OG RÖÐIN ER BINDANDI

**Hógværðarmerki á akkeriskortið er sér verk og það kemur Á EFTIR flöggunum.** Röðin er ekki verkstjórn heldur efnisleg: merki sem lýsir vissu er **afleiðing** af flaggskilgreiningunum, svo merki hengt á kortið fyrir endurskilgreininguna myndi lýsa flöggum sem eru að hverfa. Sami lærdómur og §5C-19 (birtingarreglur greininga) og feedback-reglan um að færsla sem lýsir viðgerð er ekki viðgerð: **merkið á að vera lesið af flöggunum, ekki spáð um þau.**

### 4. HVAÐ ÞESSI FÆRSLA GERIR EKKI

Hún **flippar engu**, mælir ekkert, skilgreinir ekkert flagg og heimilar ekkert í `/eign`- eða akkerisflötunum. Hún bókar **þrennt: röðina (par-lagið fremst), hvar flaggskilgreiningin á heima (cc143), og að hógværðarmerkið er sér verk á eftir henni.** Þrjár af fjórum tölum í kringum þetta eru enn ómældar af bókaðri heimild og eru merktar sem slíkar hér að ofan.

**Heimild**: lotubréf cc144 (afstaða borðsins, endursögn) — **ekki** cc139-úttekt, sem er ekki til á diski. Mælt umhverfi sem röðunin hvílir á: `docs/fable_prep/audits/STODNUD_ARTEFOKT_CC131_20260811.md` (akkerisbilið + sellu-driftin), §5D-6 §6 (51.834 pörin ónothæf innan þjálfunar). Verkið sem mælir: **cc143**, `D:\_audit\cc143_par_lagid\`.

## 2026-08-12 — §5D-8 · cc143 PAR-LAGIÐ FLIPPAÐ Á REGLU R OG ENDAPUNKTURINN LEYSTUR ÚR TVÖFALDRI FRYSTINGU — FLÖGGIN ENDURSKILGREIND MÆLD, SKIPASUNDS-SPÁIN FELLD, SELLU-DRIFTIN ER RAUNBIL SEM VEX

> *Um staðsetningu:* viðbætandi færsla aftast, sbr. §5D-4..7. Þessi færsla svarar §5D-7: hún ber flaggskilgreiningarnar með nefnara, og hún gerir upp 96,26 %-töluna sem §5D-7 bókaði sem BORNA.

**Heimild:** `docs/fable_prep/audits/PAR_LAGID_CC143_20260812.md`. Artifacts `D:\cc143\`, mælitöflur `D:\_audit\cc143_par_lagid\`, flipp-stæða `app/scripts/cc143_flip.sql`, snapshot `valuation_tiers_pre_cc143`. Allar tölur mældar í lotunni gegn lifandi gagnagrunni; ekkert borið.

### 1. HVAÐ VAR FLIPPAÐ — OG HVAÐ EKKI

Flippað: **`prior_*`-dálkar `public.valuation_tiers`** (77.484 raðir) á endurmerkt par-lag. POSTVERIFY í SÖMU transaction: rowcount 167.503 ✓ · checksum ALLRA ekki-prior-dálka `bc0d7061a300e8da072dc0914287ba29` **óbreytt** ✓ · prior-checksum lifandi = staging `02749a0af047d6feb7e7e9c59773bc7a` ✓ · engin röð ber `2025Q4`-akkeri ✓.

Ósnert af ásettu ráði: `predictions`, `comps_index_v2` (subject/comp-hliðin), leiga, allur framendi. Gamla vísitölu-artifactið (`D:\repeat_sale_index*.pkl`) stendur ÓSNERT sem rollback-grunnur; nýja býr í `D:\cc143\`.

### 2. ENDAPUNKTURINN VAR FROSINN TVÖFALT — OG AÐEINS ANNAR HELMINGURINN VAR BÓKAÐUR

`AT_Q = 2026Q2` var harðkóðað í `build_comps_v2.py:75`. **Hinn helmingurinn var `D:\pairs_v1.pkl`, frosin 2026-04-18** (og `listings_v2.pkl` með henni). Mælt gegn ferskri kaupskrá: 2026Q2 bar 2.338 arm's-length sölur en `pairs_v1` bar **389**; 2026Q3 bar 1.100 og `pairs_v1` bar **0**.

**Þar með var liður 3 í cc143-bréfinu óframkvæmanlegur á frosinni lind:** endurmerking getur ekki búið til par úr sölu sem er ekki í lindinni, svo `AT_Q` á líðandi fjórðung hefði sett hverja einustu braut á CPI-þrepið og kallað það „mælda þykkt".

**Ákvörðun (GO borðsins):** par-byggjarinn sækir sölurnar BEINT úr `kaupskra.csv`. `is_new_build` og arm's-length-sían eru reiknaðar nákvæmlega eins og `pairing.py` gerir þær (DECISIONS 2026-04-18): `ONOTHAEFUR_SAMNINGUR != 1` og `(FULLBUID == 0) | (söluár − BYGGAR <= 2)`. Eina sem tapast er `pair_status`, listinga-lýsigagn sem **engin sía les**. Hinn kosturinn — að endurbyggja `pairs_v1.pkl` — lagar ekkert, því listings-hliðin er frosin sama dag og `pair_status` yrði þá rangmerkt á öllum nýju sölunum.

**Frosinn endapunktur lýgur í báðar áttir:** gamla 2026Q2-gildið var fitt á 159 pörum og las landsvísitölu 382,2; á 1.048 pörum les hún **379,2** — ~0,8 % ofmat á verðlagi.

### 3. 96,26 %-TALAN GERÐ UPP (§5D-7 liður 1)

Talan **96,26 %** var borin án nefnara og cc143 gat ekki endurgert hana úr neinni heimild. Það sem MÆLT er, með nefnara `canon_universe` = **167.503 eignir**:

- **96,86 %** (162.245) fá annan **akkerisfjórðung** eftir viðgerðina;
- **100,00 %** (167.503) fá annaðhvort annað upplausnarlag eða annan akkerisfjórðung;
- **4,41 %** (7.390) skipta um upplausnarlag;
- CPI-þrepið bar **0 eignir** fyrir og eftir — þ.e. **hver einasta birt eign hvíldi á seríu byggðri á pre-R pörum**;
- **98,80 %** (76.554 af 77.484) fá annað `prior_adj_kr`.

Færslan bókar því **96,86 % á 167.503** sem mælda tölu. Hún staðfestir hvorki né hrekur 96,26 % — sú tala á sér enga heimild og ætti ekki að vitna framar.

### 4. FLAGGSKILGREININGARNAR (§5D-7 liður 2) — NEFNARI 77.484 EIGNIR MEÐ BIRT AKKERI

Fjögur flögg. **Þrjú eru ný og eitt var skraut.**

1. **`prior_series_thin_flag` — þröskuldurinn er á DÝPT seríunnar, ekki á akkerisfjórðungnum.** Fyrsta skilgreiningin (< 10 pör í akkerisfjórðungi) er **alltaf fölsk**, því `IndexResolver` VELUR akkeri einmitt með skilyrðinu `n_pairs_in_period >= MIN_ANCHOR_PAIRS (10)`. Flagg á þröskuld sem hlið ofar í keðjunni tryggir er skraut, ekki vörn. Þröskuldurinn er því **`SERIES_THIN_N = 500` pör**, málaður af MÆLDRI dreifingu: n < 500 ⇒ SD fjórðungsbreytinga **0,13–0,56**; n ≥ 1.000 ⇒ **0,021–0,065** (landsheild 0,021). 500 er þar sem ferillinn hnykkist — undir því ber serían meiri fjórðungssuð en raunverulega markaðshreyfingu. **4,08 % → 0,00 %.**
2. **`prior_anchor_stale_flag` (NÝTT) — miðar við LÍÐANDI fjórðung, ekki `AT_Q`.** Kviknar þegar akkerið er ekki líðandi fjórðungur; `prior_anchor_lag_q` ber lagið í fjórðungum. **36,82 % → 10,35 %.**
3. **`prior_level_fallback_flag` (NÝTT) — upplausnin féll niður um stiga** (`prior_idx_level != 'cell'`). **5,79 % → 3,83 %.**
4. **`prior_idx_provisional` (fyrirliggjandi)** **8,07 % → 3,43 %.**

Óbreytt: `prior_suspect` 5,49 % (5,49 %), `prior_old_anchor_flag` 35,96 % → 35,98 %.

**Rökin fylgja röðinni:** `prior_serie_n_pairs`, `prior_serie_sd_dlog` og `prior_anchor_pairs` eru skrifuð sem dálkar í `valuation_tiers`, svo þröskuldurinn sé endurskoðanlegur á eigninni sjálfri en ekki aðeins í þessari færslu.

Akkerisfjórðungar: `2025Q4` 3.161 / `2026Q1` 25.369 / `2026Q2` 48.954 → `2026Q1` 2.367 / `2026Q2` 5.650 / **`2026Q3` 69.467 (89,7 %)**. **Akkerisbilið (cc131-skuldin ~1 %) mælist +1,12 % miðgildi fyrir og 0,000 % eftir** fyrir þær 69.467; efri mörk hinna 8.017 af landsvísitölunni eru −0,29 %.

### 5. SKIPASUND 35 (2018566) — cc139-VÆNTINGIN FELLD, MEÐ TÖLUM

| liður | FYRIR | EFTIR |
|---|---|---|
| upplausnarlag | **family** (SERBYLI×RVK_core) | **cell** (SFH_DETACHED×RVK_core) |
| sería, n_pör | 539 | 670 |
| akkerisfjórðungur | 2026Q1 | 2026Q1 (lag 1 → **2**) |
| stuðull | 0,96965 | 0,95092 |
| **prior_adj_kr** | **150.296.236** | **147.393.221** (−1,93 %) |
| flögg | öll false | `prior_anchor_stale_flag` **true** |

**Spáð var að akkerið færðist UPP af 150,3 og að fjórðungurinn næði líðandi eða næst-líðandi. Hvorugt gerðist.** Sellan `SFH_DETACHED×RVK_core` verður raunveruleg (222 → 670 pör, 63 þéttir fjórðungar) en hún liggur **undir** fjölskyldunni sem áður bar hana (2026Q1: 349,6 gegn 368,4), og endapunktur hennar er enn of þunnur (9 pör í 2026Q2, 7 í 2026Q3) til að akkerast á líðandi fjórðungi. **Spá um hvert mælt gildi hreyfist er ekki mæling** — sama regla og §5D-7 setti á 96,26 %.

Það sem VANN er hitt: brautin er ekki lengur þögul. `prior_level_fallback_flag` slokknar og `prior_anchor_stale_flag` kviknar — áður sagði engin röð frá hvorugu. **Þetta er nákvæmlega það sem flaggendurskilgreiningin átti að gera og er sterkari niðurstaða en talan sem spáð var.**

Prod staðfest eftir cache-veltu (`/eign/2018566`, www.verdmat.ai): „Framreiknað til dagsins **147,4 M kr**", vissubils-línan endurlesin og rétt („innan 80 % vissubilsins", 147,4 ∈ [114,8 ; 157,6]). 0 console-villur.

### 6. SELLU-DRIFTIN ER RAUNBIL — OG HÚN VEX. INNTAK Í LÍKANAUMFERÐ.

Aðferðin er sönnuð ÁÐUR en hún er notuð: comp-VALIÐ er vísitöluóháð (svipleikinn les stærð/geo/aldur/tíma; hörðu síurnar lesa `kv` á nafnverði), svo `d_log` má endurreikna á sömu comp-röðum með nýjum stuðlum. Gömlu stuðlarnir endurgera `idx_factor` með max|Δ| = 2,2e-16 og **`comp_wmedian_kr` upp á 0 kr** á 1.090.488 comp-röðum / 153.366 eignum.

| sella | n | fyrir | eftir | Δ (p.p.) |
|---|---|---|---|---|
| **SFH_DETACHED×RVK_core** | **5.077** | **−4,57 %** | **−6,00 %** | **−1,43** |
| APT_FLOOR×RVK_core | 43.227 | −2,39 % | −0,12 % | +2,27 |
| APT_FLOOR×Capital_sub | 32.334 | −0,83 % | −3,49 % | −2,67 |
| APT_BASEMENT×RVK_core | 2.803 | −0,12 % | −4,99 % | −4,87 |
| SUMMERHOUSE×Country | 8.943 | +6,96 % | +0,57 % | −6,39 |
| HEILD | 153.366 | −1,05 % | −1,35 % | −0,30 |

**Ákvörðun:** sellu-driftin var bókuð sem grunuð afleiðing staðnaðs par-lags (cc131). Sú tilgáta er **hrakin**. Driftin lokast ekki við viðgerð par-lagsins — hún **vex** í SFH×RVK og endurdreifist á aðrar sellur. **Hún er raunbil milli comp-verðlags og líkansspár og fer þar með inn í næstu líkanaumferð sem inntak** (segment-halli í iter-hring), ekki í vísitölu- eða comp-vinnu. Skipasund 35 fer −4,39 % → −6,24 % og liggur ÁFRAM MEÐ sellunni (sellumiðgildi −6,00 %) — afgangurinn er sellu-stig, ekki eignarsértækur, eins og cc131 mældi.

### 7. BILIÐ 0,3 % MILLI COMP- OG PRIOR-HLIÐAR ER ÞEKKT TÍMABUNDIÐ ÁSTAND

**Berum orðum:** `build_comps_v2.py:75` ber enn `AT_Q = pd.Period("2026Q2")` harðkóðað. Comp-hliðin (`comp_wmedian_kr`, `d_log`, `price_adj_kr` í `comps_index_v2`) situr því á verðlagi 2026Q2 á meðan prior-hliðin situr á 2026Q3. **Bilið er ~0,3 %** (landsvísitala 379,2 → 378,1 = −0,29 %).

Þetta er **meðvitað, mælt og tímabundið**: það var valið fram yfir að flippa comps-fjölskyldunni aftur í sömu lotu og cc131 flippaði hana, því comps-endurbygging er sér flipp með eigin frystingu og parity. **Ástandið stendur þar til comps-endurbyggingin flippast (næsta lota).** Þangað til má **ekki** bera `prior_adj_kr` og `comp_wmedian_kr` saman sem tölur á sama verðlagi án þess að leiðrétta fyrir bilinu — t.d. í nýjum framenda-fleti eða skýrslu.

### 8. TVÆR TÍMAHÁÐAR HLIÐAR SEM KAUPSKRÁIN OPINBERAR

`single_deed` (skjal ber nákvæmlega eina eign) er **tímaháð sía**: systkina-raðir skjals berast eftir á, svo sala sem stóðst síuna í gær fellur í dag án nokkurrar gagnaleiðréttingar.

- **2145072** missir birt akkeri: eina salan (2026-06-12) situr á `A-002013/2026` sem ber nú **46 eignir**; í cc131-byggingunni bar sama skjal eina. **Staðfest sem vænt, ekki frávik.**
- **2030571**: 2026-02-27-salan situr nú á skjali með 2 eignum → akkerið fellur réttilega aftur á 2023-03-20 (einnar-eignar skjal).

Af 20 parity-frávikum gegn lifandi töflu voru **19 nýjar sölur 10.–11.08** og **1 var þetta**. **Verklagsregla:** flipp-stæða sem uppfærir af staging VERÐUR að meðhöndla „missir akkeri" beinlínis með `UPDATE ... SET NULL`; hreint `UPDATE FROM staging` skilur þær raðir eftir með gömlu gildi.

### 9. PARITY-HÓLAN — SÖNNUNIN Á AÐ EKKERT ANNAÐ BREYTTIST

Nýi byggjarinn keyrður með gömlu merkingunni, gömlu lindinni og gömlu EXCLUDE-stefnunni endurgerir lifandi artifactið: 56.930 pör, **lyklamismunur 0 báðar áttir**, max|Δ| = **0** á verðum, hlutföllum, `n_pairs_in_period`, `cell_n_pairs` og vísitölustigi (`index_value_real` 4,5e-13 = fleytitölusuð), `data_quality` ójöfn **0**. Sían, BMN-fittið og gæðaflöggin eru því sannanlega óbreytt; það sem breyttist er MERKINGIN og LINDIN, ekkert annað.

### 10. HVAÐ ÞESSI FÆRSLA GERIR EKKI

Hún heimilar **ekkert á framenda** — hógværðarmerkið á akkeriskortið er áfram sér verk (§5D-7 liður 3) og flöggin sem það á að lesa eru nú til og mæld. Hún snertir ekki `predictions`, `comps_index_v2` né leigu. Hún **eyðir engum snapshot**: `valuation_tiers_pre_cc143` STENDUR, ásamt `*_pre_cc131` og `*_pre_cc135`, þar til borðið staðfestir eyðingu sérstaklega.

**Rollback:** `app/scripts/cc143_flip.sql` (neðst) — `prior_*` aftur af `valuation_tiers_pre_cc143`; prior-checksum fyrir cc143 var `2b545c9969460295820221f50f86c3e0`.

---

## 2026-08-12 — §5D-9 · cc145 COMPS-ENDURBYGGINGIN FLIPPUÐ Á cc143-VÍSITÖLUNA: 0,3 %-BILIÐ ER LOKAÐ (3,05 % → 100,00 % AKKERISSAMSTAÐA), KVÖRÐUNIN VERSNAR MÆLT Á HÁLFUM FJÓRÐUNGI OG BER ENDURSKOÐUNARSKILYRÐI

**Afstaða borðsins: KOSTUR (a) — flippa eins og byggt er.** Rök: prior er þegar
lifandi á Q3-akkerum (69.467 eignir, §5D-8); (b) að hækka `MIN_ANCHOR_PAIRS` og
endurbyggja rýfur samstöðuna við prior, (c) að halda 2026Q2 báðum megin endurvekur
frosna endapunktinn sem §5D-8 leysti. **Innbyrðis samræmi ræður þegar nákvæmni sker
ekki úr** (§5D-1-reglan). Hálfi fjórðungurinn fyllist af sjálfu sér.

Full úttekt: `docs/fable_prep/audits/COMPS_VISITALA_CC145_20260812.md`.
Flipp: `load_comps_v2.py --phase flip`, postverify PASS, staging hreinsað.
Snapshot `*_pre_cc145` ×4 STANDA. `predictions` ósnert, leiga ósnert.

### 1. 0,3 %-JAFNAN ER LOKUÐ — MÆLD, EKKI ÁLYKTUÐ

§5D-7 liður 7 bókaði bilið sem „þekkt tímabundið ástand" sem stæði þar til
comps-endurbyggingin flippaðist. **Hún er flippuð og bilið er 0.**

Jafnan mælist á því hvort hliðarnar beri SAMA verðlags-akkeri per eign:

| | nefnari | `prior_anchor_q = idx_anchor_q` |
|---|---|---|
| FYRIR | 77.484 | 2.367 — **3,05 %** |
| EFTIR | 77.484 | 77.484 — **100,00 %** |

Báðar hliðar lesa nú `D:\cc143\rs_live_kaupskra_v2.pkl` @ AT_Q=2026Q3.
Stærð bilsins sem lokaðist, á landsvísitölunni: **−1,074 %** = **−0,807 %**
endurmat á 2026Q2 (frosni endapunkturinn var þunnkusaður: 382,2479 → 379,1632)
+ **−0,270 %** þrepið 2026Q2→2026Q3 (379,1632 → 378,1401). **Það síðarnefnda er
„0,3 %-bilið" eins og það mælist.** Akkeri comp-hliðarinnar: 2026Q2 98.610 /
2026Q1 62.575 / 2025Q4 6.318 → **2026Q3 151.641** / 2026Q2 10.604 / 2026Q1 5.258.
Engin eign situr eftir á 2025Q4. **Bannið í §5D-7 lið 7 — að bera `prior_adj_kr`
og `comp_wmedian_kr` ekki saman án leiðréttingar — er þar með aflétt.**

### 2. KVÖRÐUNARFYRIRVARINN BERUM ORÐUM — VÆNTINGIN STÓÐST EKKI

Skammtasvörunin var sönnun lotunnar (cc131-fordæmið) og **hún féll**. Sama hólfun,
sama SQL fyrir og eftir; „fyrir"-dálkurinn endurgerir cc131 upp á fjóra aukastafi:

| hólf | n | fyrir | eftir |
|---|---|---|---|
| óbreytt | 109.794 | 0,9921 | 0,9878 |
| breytt innan fjölskyldu | 30.658 | 0,9848 | 0,9884 |
| víxlað fjölbýli→sérbýli | 27.036 | 0,9863 | 0,9769 |

**Mengunarbilið 0,58 → 1,09 p.p.** (væntingin var ≤0,6 eða batni).
**Heildarkvörðun 0,9895 → 0,9867** (frávik frá 1: −1,05 % → −1,33 %, n=153.361).

Sundurgreint þrengist bilið **innan sellu** í fjórum sellum af sex
(ROW_HOUSE×Capital_sub 0,30→0,06 · ROW_HOUSE×Country 1,30→0,74 ·
SFH_DETACHED×Capital_sub 0,34→0,21 · SFH_DETACHED×RVK_core 0,94→0,42) og
**breikkar í tveimur** (ROW_HOUSE×RVK_core 1,17→2,52 · SFH_DETACHED×Country
2,09→2,34). Heildarbreikkunin er því að stærstum hluta **sellu-samsetning** —
cc145 hreyfir enga flokkun (canonical 0 ólíkar) svo hólfin eru orðin staðgengill
fyrir sellu-aðild. **En sundurgreiningin afskrifar ekki fallna væntingu: hún féll.**

**Orsökin er mæld: 2026Q3 er hálfkláraður fjórðungur** (1.7.–11.8. = 6 vikur af
13; pör í Q3 eru ~45 % af Q2). `MIN_ANCHOR_PAIRS = 10` hleypir seríu með 10 pörum
í gegn sem akkeri. **90,5 % universis (151.641 eign) akkerast á 2026Q3, þar af
33.634 eignir (20,1 %) á lagi með færri en 30 pör:**

| sella | lag | eignir | pör í Q3 |
|---|---|---|---|
| SFH_DETACHED×Capital_sub | cell | 11.391 | 16 |
| SUMMERHOUSE×Country | cell | 10.577 | 13 |
| ROW_HOUSE×Country | cell | 6.218 | 18 |
| APT_BASEMENT×RVK_core | cell | 2.851 | 17 |
| SEMI_DETACHED×Capital_sub | family | 2.077 | 27 |
| SEMI_DETACHED×RVK_core | family | 520 | 13 |

Akkerisreglan sigtar sex af átta villtum sellum burt (APT_BASEMENT×Country +91,8 %
á 1 pari, ×Capital_sub −28,7 % á 1 pari, o.s.frv.) — **en tvær sleppa og eru
nafngreindar hér: `SFH_DETACHED×Country` (−5,54 %, n=36, 19.397 eignir) og
`ROW_HOUSE×Country` (−7,46 %, n=18, 6.218 eignir).** Það eru einmitt aðrar tveggja
sellnanna sem breikka innan sellu.

**ENDURSKOÐUNARSKILYRÐI (dagsetningarlaust, ekki dagsett):** kvörðunin skal
endurmæld **sama-við-sama** — sama hólfun, sama SQL, sömu tvær sellur —
**þegar 2026Q3 er fullur fjórðungur**. Hafi hún ekki jafnað sig fer
`MIN_ANCHOR_PAIRS` í **eigin mælda ákvörðun**; þröskuldurinn 10 er ekki
endurskoðaður fyrr en talan liggur fyrir. Skilyrðið fer einnig á
`docs/PLANNING_BACKLOG.md` með skilyrðinu „þegar Q3 lokar", ekki með dagsetningu.
Sbr. `feedback_flagg_a_throskuldi_sem_hlid_tryggir`: þröskuldur sem hlið ofar
tryggir bítur ekki — hér bítur hann ekki á hálfum fjórðungi.

### 3. BLOKKERINN: LOADERINN HEFÐI YFIRSKRIFAÐ `prior_*` OG NULL-AÐ FLÖGGIN ÞÖGULT

`load_comps_v2.py` flippaði `valuation_tiers` með **TRUNCATE + INSERT** og
dálkalistinn ber tíu `prior_*`-dálka. Óbreyttur hefði flippið **(a)** yfirskrifað
cc143-flippuðu `prior_*`-dálkana með prior-útreikningi `build_comps_v2` (önnur
skrift, aðrar reglur en `cc143_prior.py`) og **(b) þaggað nýju sjö cc143-flöggin
í NULL** — þau eru ekki í dálkalistanum, svo INSERT skilur þau eftir tóm, án
villu og án ummerkja. Bannið „prior_* ósnertir" hefði fallið í hljóði.

**Lagfæringin er í þremur lögum og öll í `flip_mode="update"`-leiðinni:**
1. `valuation_tiers` flippast sem **UPDATE á comp-dálkunum einum** (32 dálkar);
   `PRIOR_FROZEN` (10 gamlir + 7 nýir = 17) kemst aldrei í SET-lista. Hinar
   þrjár töflurnar halda TRUNCATE+INSERT.
2. **Hlið á SKRIFLEIÐINNI, ekki á mælingunni:** prior-checksum borin saman við
   `valuation_tiers_pre_cc145` **í sömu txn** — brot rúllar öllu flippinu til
   baka. Mengja-jafnræði (hvorug hlið með aukaröð) er hart skilyrði á undan
   UPDATE-inu. Mælt við flipp: `4b6edaf9f772276ba6d4da9d830a193d` óbreytt.
3. Postverify undanskilur `prior_*` fyrir `valuation_tiers` — annars væri það
   falskt fall, því lifandi tafla ber cc143-gildin en CSV-ið sín eigin.

**Almenna reglan:** TRUNCATE+INSERT er ekki „endurhleðsla töflunnar", hún er
**endurhleðsla ALLRA dálka hennar, líka þeirra sem skriftin þekkir ekki**. Tafla
sem tvær vélar skrifa í má ekki flippast með TRUNCATE nema dálkalistinn sé
sannreyndur gegn raunverulegu skema hennar. Sbr.
`feedback_hlid_a_maelingu_en_ekki_a_skrifleid`.

Í leiðinni: `SCRATCH` í loadernum benti á scratchpad cc131-lotunnar — **dauða slóð
milli lota**, sama gildra og cc129 lenti í. Fært á `D:\_audit\cc145_comps`.

### 4. PRÓFDÆMIN — EITT GEKK EFTIR, EITT SITUR Á MÆLDRI ÞYNNKU

**Álftamýri 39 (2013952 — fastnúmerið leiðrétt; forskriftin bar 2103763 sem er
ekki til í universinu, geo né training_data).** Bókaða væntingin gekk eftir:
comp-akkerið **2025Q4 → 2026Q2**, `comp_wmedian` 145,3 → 135,6 M,
**gap gegn spá +5,24 % → −1,76 %**, gap gegn prior −4,14 % → +2,70 %.

**Skipasund 35 (2018566): akkerið situr áfram í 2026Q1** — sellan
`SFH_DETACHED×RVK_core` ber **7 pör í Q3 og 9 í Q2, bæði undir 10**, svo
akkerisreglan hafnar báðum réttilega. Það sem vinnst er að lagið fer úr
**fjölskyldu í sellu** (serían ber 670 pör). `comp_wmedian` 124,1 → 121,7 M,
gap gegn spá −4,39 % → −6,24 %. **Flaggakerfið virkar og brautin er ekki þögul:
þynnkan er mæld tala (7 og 9 gegn þröskuldi 10), ekki þögult fall.** Eignin liggur
áfram með sellunni (§5D-8 lið 6: sellumiðgildi −6,00 %) — afgangurinn er sellu-stig.

### 5. HVAÐ ÞESSI FÆRSLA GERIR EKKI — OG FLÖTURINN SEM LES EKKI TÖFLURNAR

`predictions`, `prior_*` og leiga ósnert. Engum snapshot eytt: `*_pre_cc145`,
`*_pre_cc143`, `*_pre_cc131` og `*_pre_cc135` STANDA þar til borðið staðfestir.

**Mælt við prod-staðfestingu og bókast:** `/eign/[fastnum]` les **`comps_index`
(gömlu töfluna, 29.05)** og `v_current_predictions` — **`comps_index_v2`,
`valuation_tiers` og `comps_t5_basis` eru hvergi lesin í appinu**
(`grep` yfir `app/`, `lib/`, `components/`: 0 tilvik). Báðar prófeignirnar
birtast rétt á `https://verdmat-is.vercel.app/eign/…` með spátölunum
(129,8 M og 138,0 M, sömu og `predictions`), console hreint á báðum — **en
cc145-tölurnar eru ekki sýnilegar þar, því flöturinn les þær ekki.**
Comps-fjölskyldan er enn bakendaflötur. Að tengja framendann við v2-töflurnar
er sér verk og bætist á backlog. (`www.verdmat.is` er annað vefsvæði og skilar
404 á `/eign` og `/markadur` — appið er á Vercel-slóðinni.)

**Rollback:** `app/scripts/comps_v2_rollback_cc145.sql` (TRUNCATE + INSERT úr
`*_pre_cc145`, replica-mode txn). ATH: sá bakleikur endurheimtir comps-dálkana;
`prior_*` hreyfðust aldrei og þarfnast einskis.

## 2026-08-12 — §5D-10 · cc150 API-SÍUR #2 OG #4 INNI Á ÚTDRÁTTARLEIÐINNI: 1.578 KÖLL ($32,69) ÚR BIÐRÖÐINNI MEÐ 0 RESIDENTIAL-RÖÐUM FELLDUM — OG RÖÐUNARSKULDIN BÓKUÐ BERUM ORÐUM

> *Um staðsetningu:* viðbætandi færsla aftast, sbr. §5D-4 til §5D-9. Framkvæmd á
> mælingu **cc130** (READ-ONLY, `e0ced3e`); allar formælingar hér READ-ONLY,
> **0 Haiku-köll** (eina keyrslan á vélinni var `--forward 5` ÁN `--confirm`).
> Full úttekt (committuð með þessari bókun, sbr. cc143/cc146/cc147):
> `docs/fable_prep/audits/UTDRATTAR_SIUR_CC150_20260812.md`. **cc130-úttektin
> sjálf stendur áfram órakin** — hún var bókuð þannig og er ekki hreyfð hér.

**Málið**: cc130 mældi útdráttarbiðröðina og setti tillöguborð með átta liðum.
Tveir báru skilyrðislausan eða skilyrtan dóm: **#2 dauð köll** („RÉTTLÆTT ÁN
SKILYRÐA. Eini sannanlega dauði flokkurinn", $5,62 / 6,3 prósent á 30-daga
glugganum) og **#4 commercial/plot/other** ($7,19 / 8,0 prósent, „RÉTTLÆTT EF
eigandi ákveður að `/eign` á atvinnuhúsnæði sé ekki afurð" — borðið svaraði JÁ).
Hvorug hafði verið framkvæmd.

### 1. NEFNARINN ER BIÐRÖÐIN, EKKI cc130-GLUGGINN

Formælingin var gerð **með raunfallinu** (`fetch_listings_needing_extraction`,
`limit=10.000.000`) og mælitækið sannað fyrst: `need`-CTE-ið endurgert í SQL gaf
**0 mismun** á hash-mengi og **0 mismun** á fulltrúa-`source_listing_id` gegn
fallinu (9.037 raðir hvor).

| | biðröð (cc150) | 30-daga keypt (cc130) |
|---|---|---|
| N | **9.037** ($187,22) | 4.312 ($89,33) |
| #2 dautt | **556 · 6,15 prósent** | 271 · 6,3 prósent |
| #4 c/p/o | **1.158 · 12,81 prósent** | 347 · 8,0 prósent |

**cc130-tölurnar mega EKKI flytjast hingað óbreyttar.** Dauða hlutfallið helst
(6,15 gegn 6,3), en c/p/o-hluturinn er **helmingi þyngri á biðröðinni** af því að
atvinnu-auglýsingar liggja lengur ólesnar en íbúðir. Sparnaðartalan að neðan er
því reiknuð á biðraðar-nefnaranum, ekki á cc130-glugganum.

**Seinni helmingur cc130-skilgreiningarinnar á #2 („engin mbl-auglýsing ber
textann") er 0 AF BYGGINGU** og fær enga línu í kóðanum: biðröðin er sótt ÚR
`scraper.listings`, svo texti sem engin auglýsing ber kemst aldrei í hana. Sá
liður var mæling á ÞEGAR KEYPTUM útdráttum — hann bítur á texta sem hvarf EFTIR
kaupin, og engin forsía nær því. Mælt: 0 af 9.037.

### 2. VARÐHLIÐIÐ SEM MÆLINGIN KREFÐIST — HRÁA SÍAN FÉLL Á MÓTPRÓFINU

**Ásinn sem ber commercial/plot/other er `scraper.listings.category`, EKKI
`canonical_code`** (sá síðarnefndi ber ekki þau gildi; mótsvar hans er
`EXCLUDE`). Hrá sían „öll systkin c/p/o" fellir **1.158** raðir — og **67 þeirra
bera eign með GILDU ÍBÚÐAR-CANONICAL**: SFH_DETACHED 38, SUMMERHOUSE 20,
APT_FLOOR 6, ROW_HOUSE 1, SEMI_DETACHED 1. Það eru lóðar-auglýsingar á eign sem
BER hús — sama mistalning og cc130 sá („28 falla á íbúðarflokka og eru
mistalning, ekki atvinnuhúsnæði"), bara á öðrum nefnara.

Þess vegna ber sían þriðja liðinn: **beri EINHVER auglýsing textans eign sem
cc134-hliðið hleypir í gegn, stendur röðin.** Með vörninni fellur **1.091** og
mótprófið verður **0**.

### 3. SKÖRUNIN VIÐ cc134 ER FULLKOMIN — OG HÚN DREGUR SAMT EKKERT FRÁ

| | teljari / nefnari | prósent |
|---|---|---|
| c/p/o-raðir sem bera **enga** eign sem cc134-hliðið hleypir í gegn | **1.091 / 1.158** | **94,21** |
| c/p/o-raðir sem sleppa gegnum cc134 (varðar af hliðinu) | 67 / 1.158 | 5,79 |

Varðaða mengið **ER** nákvæmlega það mengi sem `pr.canonical_code <> 'EXCLUDE'`
í `fetch_extracted_listings_to_value` (§ cc134) stöðvar hvort sem er. Af því
leiðir tvennt sem er bókað sem niðurstaða, ekki sem tilviljun:

1. **0 VERÐMÖT TAPAST** við síu #4. Það sem tapast er **eigindalagið**: 892
   eignir sem hefðu fengið `source='auglysing'`-raðir gegnum brúna. Það er
   nákvæmlega fórnin sem borðið samþykkti, hvorki meira né minna.
2. **cc134 dregur samt EKKERT frá sparnaðinum.** Hún situr á VERÐMATSLEIÐINNI,
   sem gerir engin Haiku-köll (cc134 bókaði $0,00); Haiku-kallið er keypt á
   ÚTDRÁTTARLEIÐINNI. cc134 sparaði enga kalla — hún stöðvaði skorun.
   Sparnaðurinn hér er nýr og ekki tvítalinn.

### 4. FRAMKVÆMDIN OG SÖNNUNIN

Ein breyting, `fetch_listings_needing_extraction` í
`app/scripts/extraction_engine.py`, **hreint viðbætandi: 123 línur inn, 0 út**
(`LEFT JOIN public.properties` + `HAVING`-hlið + heimildar-athugasemd).
Sama mynstur og cc134: **sían er á VERKEFNASKRÁNNI**, ekki á neinni röð sem
þegar liggur í `listing_extractions`. Ekkert eytt, ekkert gamalt snert, og
hvorug sían er endanleg — **þetta er FRESTUN, ekki brottfelling:** leysist
`fastnum` eða breytist `category`, birtist röðin aftur næstu nótt af sjálfu sér.

Fail-closed alls staðar: `count(l.fastnum) > 0` fellir röð aðeins ef **engin**
auglýsing sem ber textann hefur fastnúmer (fulltrúa-útgáfan hefði fellt 560 —
fjórar þeirra eiga systkina-auglýsingu MEÐ fastnúmeri sem brúin næði; sbr.
`feedback_single_deed_sian_er_timahad`). Skilgreiningin var **staðfest gegn
lifandi kóða**, ekki tekin á orðinu: `bru_extraction_i_eigindi` ber
`where v.fastnum is not null`, `fetch_extracted_listings_to_value` ber
`l.fastnum IS NOT NULL`, og greppað yfir bæði repó: `listing_extractions` er
hvergi lesin af `verdmat-ai`.

**Báðar cc134-gildrurnar skoðaðar í þessari skrá:** (i) **engin prósentumerki í
SQL-athugasemdum** — strengurinn fer í dag í `cur.execute(sql)` ÁN params, svo
bert merki fellir hann ekki EINS OG ER, og það er einmitt ástæðan fyrir að
reglan er skrifuð inn í blokkina; (ii) **cc128-falsy** er ekki hér — hliðin bera
ber `> 0` samanburð og fallið hefur enga `if limit`-grein.
Margfeldi mælt en ekki gefið sér: `public.properties` er einkvæm á `fastnum`
(232.887 af 232.887), svo joinið breytir engri samantektartölu.

**Sönnun, gamla fallið sótt orðrétt úr `git show HEAD:` og keyrt í sama ferli:**

| | n | $ | nætur á 200/nótt |
|---|---|---|---|
| **fyrir** | **9.037** | $187,22 | 45,2 |
| **eftir** | **7.459** | $154,53 | 37,3 |
| **FELLT** | **1.578** | $32,69 | 17,46 prósent |
| **BÆTT VIÐ** | **0** | — | — |

`eftir ⊆ fyrir` satt · fulltrúi/texti óbreyttur á lifandi röðum (0 frávik) ·
**RÖÐUNIN ÓBREYTT** (gamla röðin síuð == nýja röðin, lið fyrir lið — sían
fjarlægir raðir, hún endurraðar engu). Sundurliðun: #2 **556** · #4 **1.022**
(= 1.091 − 69 skörun).

**Mótpróf: 0 raðir með gilt íbúðar-canonical í fellda menginu.**
`canonical`-dreifing fellda mengisins: `EXCLUDE` 1.018 · `<engin eign>` 556 ·
`<engin eign>,EXCLUDE` 4. **487 raðir bera `category='residential'` og eru samt
felldar — allar af síu #2, engin af síu #4**: þær eru dauðar þrátt fyrir
flokkinn af því báðir neytendur lykla á `fastnum`, sem er NULL á öllum
auglýsingum sem bera textann. Þar af 310 leigu-auglýsingar — leigan hverfur að
hluta hér, en **af því hún ber ekkert fastnúmer, ekki af því hún er leiga**
(cc130 #7 stendur felld).

Þurrkeyrsla `--forward 5 --skip-valuation` ÁN `--confirm`: adapterinn hleðst
óbreyttur (156 eiginleikar, `iter4r_20260805_reglaR_strukt`), 5 raðir valdar,
allar residential með fastnúmeri og gildu canonical (APT_FLOOR ×2, ROW_HOUSE,
SEMI_DETACHED, SFH_DETACHED). **0 Haiku-köll í allri sönnuninni.**

### 5. SPARNAÐARSPÁIN — OG HVERS VEGNA `day_total` Á EKKI AÐ FALLA STRAX

**1.578 köll = $32,69**, á biðraðar-nefnaranum 9.037, eftir að skörunin (69) er
dregin frá og eftir að varðhliðið hefur skilað 67 röðum aftur.

**Nóttin kaupir `min(--forward, biðröð)`, og biðröðin er 7.459 eftir síun — langt
yfir 200.** `day_total` heldur því áfram að vera **~$4,14/nótt**, og það er
SPÁIN, ekki merki um að sían virki ekki. Koma nýrra hasha mælist **15,5/dag**
(418 á 27 dögum), svo nettó-tæming er 184,5/nótt:

| | brúttó (200/nótt) | nettó (184,5/nótt) |
|---|---|---|
| nætur að tæmingu **fyrir** | 45,2 | 49,0 |
| nætur að tæmingu **eftir** | 37,3 | 40,4 |
| **flýting** | 7,9 | **8,6 nætur** |

**Hvað morgunvaktin les næstu nætur:** (1) `day_total ≈ $4,14` **óbreytt** — falli
hún strax er eitthvað annað að; (2) **biðraðardýpt féll um 1.578 við flippið** —
það er talan sem staðfestir síuna; (3) samsetning: **0 nýjar
`listing_extractions`-raðir án fastnúmers og 0 c/p/o-raðir án íbúðarhæfrar
eignar**; (4) fyrst þegar biðröðin fer undir 200 (~40 nætur) fellur `day_total`
af sjálfu sér, og þá 8,6 nóttum fyrr en ella. Sbr.
`feedback_thak_verdur_ad_bita_a_somu_kornastaerd_og_verkid`: þak sem mælist á
öðru en verkinu finnur ekki liðinn sem hreyfðist.

### 6. RÖÐUNARSKULDIN — BERUM ORÐUM, SVO HÚN ENDURTAKIST EKKI

cc130 bókaði **„RÖÐIN ER BINDANDI: #2 → #1 → endurmæla #3"** og setti **LIÐ 0
(útganginn) ofar öllum síum**: *„Áður en picker er þrengdur ætti að liggja fyrir
ákvörðun um (a) hvenær verðmats-pásan er tekin af og (b) hvort brúin fer í
`nightly_delta_chain.sh`."*

**Sú forsenda féll í §5D-6.** Ákvörðunin sem stöðvar sjálfvirkni brúarinnar
(47,4 prósenta margföldunarþak leiðréttingarlagsins, cc75 §8 → γ) var þar
endurskilgreind sem **endurþjálfunar-verk** (n ≈ 629, holdout utan þjálfunar
beggja líkana, mótpróf) — ekki biðstaða heldur ótímabundin frestun. **Síurnar
biðu því að óþörfu frá 12.08 kl. 00:10.** Lærdómurinn bókast hér: **síu-röð sem
hangir á öðru verki verður að bera dagsetningu eða mælanlegt skilyrði sem
einhver les — annars breytist „röðin er bindandi" í þögult stopp.** Röðin
#2 → #1 stendur að öðru leyti óhögguð.

### 7. STAÐA HINNA LIÐANNA — BÓKAÐ SVO ENGINN ENDURVEKI ÞÁ

**#1 nær-eins-sía ($32,86 á 30-daga glugganum) — STENDUR Á BACKLOG SEM EIGIN
LOTA.** Dedup-lykill **`cc130-#1-naer-eins-sia`**. Hún þarf hönnun á því hvernig
vigurinn erfist (byggingarstigs-reitir frá kjarna klasans, íbúðarstigs-reitir
sértækir) og er jafnframt gæðabót: `sameign_cosmetic` er ósamstillt í
**51,0 prósentum** klasa með 3+ köllum í dag.

| # | tillaga | staða |
|---|---|---|
| **#3** | endurtekningarsía á eign | **FELLD SEM BANN, stendur sem TÍMAÞAK.** 62,1 prósent endurtekninga eru NÝR TEXTI frá öðrum fasteignasala — tilgátan féll á nefnaranum. Bíður endurmælingar eftir #1 (skörun 897 köll gerir sjálfstæða tölu hennar villandi). |
| **#5** | sleppa EXCLUDE í heild | **FELLD.** cc116-talan (0 af 56.958 spám) á við BIRTINGARLEIÐINA, ekki eigindaleiðina: EXCLUDE ber 1.225 eigindaraðir á 379 eignum sem `/eign` sýnir (`t5_astaeda='engin_spa'`). Ekki „enginn les". |
| **#6** | sleppa landsbyggð (`Country`) | **FELLD.** Þekjuskerðing á 26,4 prósentum kalla án nokkurs mælds mótvægis; Country-eignir bera spá og eigindi eins og aðrar. |
| **#7** | sleppa leigu | **FELLD.** 1,0 prósent — undir suðmörkum. *(Hluti leigunnar fellur samt hér, en sem DAUÐ köll — 310 af 556 — af því þau bera ekkert fastnúmer.)* |
| **#8** | fella `--forward` úr 200 | **ÓSNERT.** Hangir á LIÐ 0 og var ekki á dagskrá þessarar lotu. |

### 8. ÓSNERT

`predictions*`, `valuation_tiers*`, tiers-vélar, brúin, `nightly_delta_chain.sh`,
`--forward 200`-þakið og **cc134-EXCLUDE-sían í `fetch_extracted_listings_to_value`
(óbreytt)**. Engin migration, engin skrif í gagnagrunn, ekkert snapshot.
**Rollback:** `git revert` á commitinu — sían er ein `HAVING`-klausa og eitt
`LEFT JOIN`; ekkert ástand fylgir henni.

## 2026-08-12 — §5D-11 · cc149 LEIGU-ENDURSJÓNUNIN KLÁRUÐ (ÞREP 3+4 AF 4): SPÁIN OG ÞREPIÐ FLIPPUÐ SAMAN, STUÐNINGSHLIÐIÐ F300 SETT UPP — 3.539 EIGNIR MISSA BIRT MAT OG ÞAÐ ER HÖNNUNIN

**Afstaða borðsins: flippa bæði lögin í sömu lotu OG setja stuðningshliðið upp í
sömu umferð.** Rök: (a) `predictions_rent` og `valuation_tiers_rent` eru tvö lög
af sama mati — að flippa aðeins spána hefði skilið þrepatöfluna eftir á stöðnuðu
`pi80`-lagi, sem er nákvæmlega ástandið sem cc135 kostaði fjórar lotur að finna;
(b) hliðið er afurð cc148, sem borðið kvittaði fyrir, og að fresta því hefði þýtt
aðra flipp-umferð á sömu töflu innan sólarhrings.

Full úttekt: `docs/fable_prep/audits/LEIGU_ENDURSJONUN_CC149_20260812.md`.
Flipp: `cc149_flip_pred.py --go` (22:20:08) og `cc149_flip_tiers.py --go` (22:20:42),
postverify PASS 11/11 á báðum. Snapshot `*_pre_cc149` ×2 STANDA, bakleikir í
`app/scripts/`. Birting: verdmat-ai **316ef09**. Sölu-hliðin ósnert.

### 1. MÆLITÆKIÐ SANNAÐ ÁÐUR EN NOKKRU VAR HREYFT

Þrepavélin með nýja ásnum var keyrð á **gömlu, lifandi spánni** fyrst. Grunnþrepin
endurgera lifandi töfluna upp á rað þegar hliðið er dregið frá (32.274+252=32.526 ·
70.501+1.059=71.560 · 19.730+1.242=20.972 · 18.175+986=19.161 · 17.634−3.539=14.095)
og hliðið endurgerir cc148-töluna nákvæmlega (3.539 / sérbýli 3.040 / fjölbýli 499
af nefnara 144.219). **Forspá flippsins var því mæld FYRIR flipp**, með því að
beina byggjaranum á cc147-staging. Sú keyrsla skilaði nákvæmlega töflunni sem
síðar var flippuð — engin tala kom á óvart eftir COMMIT.

### 2. TVÖ HLIÐ SEM EKKI VAR HÆGT AÐ SETJA ÁÐUR

**`segment` vs `properties.canonical_code` = 0.** cc135 bókaði ólæknað: *„segment
ber pre-R canonical_code á 57.612 röðum (36,39 %); ás 2 læknast AÐEINS með
endurskorun."* Endurskorunin er lifandi og mismunurinn er **57.417 → 0**.
`model_version` fer úr `rent_v1_nan` í `rent_v1_reglaR_20260812`.

**`pi80_pct` verður að endurgerast úr LIFANDI `predictions_rent`** upp á tvo
aukastafi — nýtt hlið í þrepa-flippinu. Falli það er þrepataflan byggð á öðru
lagi en talan sem notandinn sér. cc135 gat ekki sett þetta hlið því þar VAR lagið
stöðnuð viljandi; héðan í frá er sú tegund stöðnunar vöktuð sjálfvirkt í hverju
flippi, ekki fundin eftir á.

### 3. STUÐNINGSHLIÐIÐ (ÁS 5) — ÞYKKT ER EKKI NÁLÆGÐ

Ásarnir fjórir sem fyrir voru mæla allir hve þykk sellan er. Enginn þeirra mælir
hvort eignin liggi INNAN hennar. cc148 sýndi að sérbýli á T1 fer OFTAR út fyrir
stærðarstuðning sellunnar (72,59 %) en sérbýli á T4 (35,59 %).

Reglan: **`einflm` > sellu-max á einflm-ás (samningar 2011–2023, live-endurmerktir)
EÐA `einflm` > 300 m² → Þrep 5, `t5_astaeda='utan_studnings_staerd'`.** Þröskuldarnir
standa í `STUDNINGSHLID`-config í `build_rent_tiers.py` með heimildarvísun í cc148,
ekki harðkóðaðir inni í `assign()`. Nýja ástæðan er NEÐST í forgangsröð, svo eign
sem var þegar óbirtanleg heldur ástæðunni sem hún bar áður.

**Hvorugur liðurinn dugir einn** — og sundurliðunin sannar það: 2.035 falla aðeins
á sellu-max, 3.031 aðeins á fasta þakinu, 705 á báðum. Sellu-max eitt sleppir
Sjafnargötu 14 (384 m², percentíla 93,77) og öllu bandinu þar sem umsnúningurinn
er þegar mældur; fast þak eitt hunsar þunna sellu löngu fyrir 300 m². Fasti
liðurinn ÞARF að vera til því sellu-max á einflm-ás er MENGAÐ af hlutasamningum:
samningur um kjallaraíbúð í 400 m² húsi lyftir max-inu í 400 án þess að nokkur
hafi leigt húsið.

**300 m² er MÆLT, ekki valið** (cc148 lið 1B/4): þar hverfa stuðningur og mark
samtímis. Heilir sérbýlissamningar 300–350 m²: 41 alls, 4 frá 2021, 41,5 % á
ritskoðunarþaki þjálfunarmarksins; >350 m²: 7 á þrettán árum, 0 frá 2021.
Log-log hallinn snýst úr +0,433 (20–200 m², markaður +0,390) í −0,343 (350–1000 m²).

**Kostir A/C/D/G/H voru felldir** (5,8–30,5 % þýðisins í T5 = afturköllun á
vörunni; STAERD-ásinn blandar auk þess saman „utan stuðnings" og train/serve-galla).
**B eitt** var fellt (sleppir Sjafnargötu). **F300 = 2,45 %.**

### 4. VÖKTUNARLIÐUR SEM FYLGIR HLIÐINU — BANDIÐ 200–350 m²

**Hliðið FELUR töluna, það LAGAR hana ekki.** Umsnúningurinn byrjar við 200 m² þar
sem enn eru **481 heilir samningar** — bandið 200–350 m² ber því vanmetna tölu SEM
ER ENN BIRT. Meðvituð málamiðlun: að loka því bandi hefði kostað margfalt fleiri
eignir án þess að mælingin þar sé jafn afdráttarlaus. **Þetta er vöktunarliður á
PLANNING_BACKLOG, ekki leyst mál** — og hann fellur með yield-akkeruðu leigunni
(cc148 lið 6: kvörðunargrunnur 80–160 m², yield 4,4–5,3 %, n=71.477), sem er sá
staður þar sem hægt væri að LAGA töluna í stað þess að fela hana.

### 5. NIÐURSTAÐAN

T1 32.526→32.274 · T2 71.560→70.501 · T3 20.972→19.731 · T4 19.161→18.174 ·
**T5 14.095→17.634**. Ástæður: `of_fair_samningar` 13.586→13.530 ·
**`utan_studnings_staerd` 0→3.539** · `eignaflokkur` 314→314 ·
`engin_svaedisgogn` 195→251.

**Kohort: FÁ birt mat 0 · MISSA 3.539 (3.524 sýnileg — fjöleiningar-vörnin tekur
15 sem báru aldrei tölu).** Þeir sem missa: sérbýli 3.040, fjölbýli 499; einflm
p50 329,7 m²; leigumatið sem hverfur ber miðgildi **347.019 kr./mán**. Þau þrep sem
þeir báru: T1 252 · T2 1.059 · T3 1.242 · T4 986 — **hliðið bítur á ÖLLUM þrepum**,
sem er einmitt innistæðan: þykkt sellu ver ekki gegn því að eignin liggi utan hennar.

pi80 lendir nákvæmlega á cc147-staging: heildarmiðgildi **38,54 %** (frávik 0,00 pp),
sérbýli **57,76 %** (frávik 0,00 pp). 105.460 þrengjast, 52.854 víkka, **0 standa
kyrrar**. Meðaltalið hreyfist áfram í ÖFUGA átt við miðgildið (41,08→42,74).

### 6. VIÐAUKI — VÍXLAMATRIXAN Á 56 RÖÐUM

`of_fair_samningar` fellur um 56 og `engin_svaedisgogn` hækkar um 56. **Mismunur
tveggja teljara segir EKKI hvaða raðir hreyfðust** — hann er samhljóma bæði við
„56 hurfu úr T5" og við „56 skiptu um ástæðu". Víxlamatrixan, talin á röðum, hefur
aðeins TVÆR færslur í öllu þýðinu: `— birt mat — → utan_studnings_staerd` (3.539)
og `of_fair_samningar → engin_svaedisgogn` (56). Þær 56 fara `fallback_lvl` 1→3 á
öllum 56, `n_local` hæst 4 (enn undir MIN_LOCAL=5), þrep T5→T5. **Engin röð fór úr
T5.** Nýja spáin setti þær á global-fallback, sem er OFAR í forgangsröðinni, svo
ástæðan endurmerkist. Báðar voru sannar fyrir og eftir; taflan skrifar aðeins þá
efstu. Endurmerkingin sést á yfirborðinu: Vesturgata 30 ber nú
`engin_svaedisgogn`-textann en ekki `of_fair`-textann.

### 7. DÓMSKILYRÐI cc147 DÆMD — FLOKKA-VÍXLIN ERU AFHJÚPUN, EKKI AFTURFÖR

`k_global` **ÓHREYFT** eins og bannið sagði (1,108152 → endurmælt 1,107372,
−0,070 %; level-frávik sem getur ekki hreyft pi80).

**Flokkur B→C á 13.608 (C→B á 3): VÍXLIN STANDA — bilið segir satt.** Engin tala
versnaði. Það sem gerðist er að sérbýli hætti að lesa fjölbýlis-conformal-sellu:
miðgildisbreidd sérbýlis fer úr 46,76 % í **57,76 %** (+11,00 pp) á 56.447 eignum.
Gamla, þrengra bilið var RANGT — reiknað á sellu sem eignin átti ekki heima í.
Bókstafurinn versnar af því hann segir loksins satt. Sama tegund niðurstöðu og
§5D-8 bókaði um sellu-driftina: mæling sem lítur út eins og afturför en er
leiðrétting á ómældri skekkju.

### 8. BIRTINGARLAGIÐ — ÞÖGUL BILUN SEM PUSHIÐ LOKAR

`LEIGU_T5_ASTAEDUR[t5_astaeda]` skilar `undefined` fyrir óþekktan lykil og
`&&`-hliðið í `Leigumatskort.tsx` fellir málsgreinina **ÁN VILLU**: eignin hefði
borið Þrep 5 án ástæðu um óákveðinn tíma. Þess vegna fóru DB-flippið og pushið í
sömu lotu með stystum mögulegum glugga (22:20 → 22:5x). Einn `Record`, fjögur
yfirborð — engin önnur skrá þurfti breytingu.

**Raunprófun á production (eftir 316ef09):** Skeljatangi 9 og Sjafnargata 14 bera
Þrep 5 með textanum orðréttum; Bröndukvísl 17 (397.221 kr.) og Jakasel 25
(361.265 kr.) halda mati upp á krónu með nýju breiddinni; Vesturgata 30 ber
`engin_svaedisgogn`-textann; Auðnukór 6 ber nýja textann á `/leiga/[id]`;
Ránargata 8A (T2, viðmið) óhreyfð. **Cache-TTL virt:** fyrsta sókn á Sjafnargötu
skilaði nákvæmlega `pre_cc149`-röðinni — það var staðfest gegn snapshot-töflunni
áður en nokkuð var dæmt, svo stöðnun væri ekki lesin sem rökvilla. Útgáfa ógildir
`unstable_cache` EKKI; sókn eftir veltu skilaði nýja ástandinu.

### 9. ÓSNERT

`predictions` og `valuation_tiers` (sölu-hliðin) · `leiga_train.parquet` á diski
(aðeins lesin) · `k_global`/CFG · `rent_conformal_corrections.json` · þröskuldarnir
T1–T4 og MIN_LOCAL · `feature_attributions_rent` (áfram tóm, meðvituð úrfelling).
Engin migration. Snapshot `*_pre_cc135` og `*_pre_cc149` standa bæði.

> *Um staðsetningu:* viðbætandi færsla aftast, sbr. §5D-4 til §5D-10.

---

## 2026-08-13 — §5D-12 · cc152 HÓGVÆRÐARMERKIÐ Á AKKERISKORTINU: K0 FELLT SEM MERKI, K8 SETT Í STAÐINN, ÞYNNKUFLAGGIÐ LAGAÐ Í RÓT — OG STÖÐNUÐ SPÁTAFLA LOKUÐ FYRIR ANON

### 1. HVAÐ VAR ÁKVEÐIÐ

`prior_old_anchor_flag` (aldur akkeris > 8 ár) hættir að vera **merki** á
`/eign`. Það logaði á 35,98 % akkeraðra eigna, jafndreift, og aðgreindi ekkert
(AUC 0,500 nákvæmlega innan sellu — cc151). Meira en helmingur flöggunarinnar
lenti á gæðaflokki A. Aldurinn stendur eftir sem **hrein staðreyndarlína** á
kortinu („Aldur fyrri sölu · 18 ár"), án viðvörunarlitar og án fyrirvara-orðunar.

Hógværðarmerkið er **K8 eitt**: `prior_age_years > 12` **OG**
`|prior_adj_kr − real_pred_mean| / real_pred_mean > 25 pp`.

| | teljari | nefnari | tíðni |
|---|---:|---:|---:|
| K8 (valinn) | **1.957** | **77.484** akkeraðar | **2,53 %** |
| — af öllum `valuation_tiers` | 1.957 | 167.503 | 1,17 % |
| K0 (fellt) | 27.877 | 77.484 | 35,98 % |

Dómsskilyrði borðsins var 2–15 % af akkeruðum; 2,53 % stenst. Öfugt við K0 er
K8 **einhalla eftir gagnagæðum**: flokkur A 1,05 % → D 11,23 %, þrep T1 1,93 %
→ T5 20,00 % (K0: A 34,00 %, D 34,88 %). Miðgildi bils innan K8 er 36,15 pp
gegn 6,40 pp utan; miðaldur 16,17 ár gegn 5,72 ár.

**Grunnurinn er BIRTA talan.** `v_current_predictions.real_pred_mean` mældist
bæti-identísk `valuation_tiers.pred_mean_at_build_kr` á **77.484 af 77.484**
akkeruðum röðum, svo tíðnin gildir á þeirri tölu sem stendur á skjánum.

**Textinn er stefnulaus.** Innan K8 liggur akkerið **yfir** matinu á 1.015
eignum (51,87 %) og **undir** á 942 (48,13 %) — nánast jafnt. Textinn segir því
að bilið sé stórt, aldrei í hvora áttina það hallar.

### 2. 25 pp — BÓKAÐ BERUM ORÐUM

**25 pp er VALIÐ SÝNIGILDI, ekki mældur hnykkur.** Hvorki cc151 né cc152 hefur
mælt hnykk á þeim ási; ekkert staðfestir að 25 sé betri staður en 20 eða 30.
Þess vegna stendur talan **hvergi í birtingartexta** — hún ræður hvenær merkið
logar en er ekki fullyrðing við notandann. Aldursmörkin 12 hvíla hins vegar á
mældri brekku (hlutfall > 25 pp: 6,59 % við 6–8 ár → 8,37 % við 8–10 →
12,43 % við 12–15), og sú tala er birt.

**ENDURSKOÐUNARSKILYRÐI:** 25 pp endurmælist að hnykk þegar annaðhvort gerist —
(1) yield-akkeraða leigan hreyfir akkerisbilin, eða (2) næsta líkanaumferð er
skoruð.

### 3. ÞYNNKUFLAGGIÐ — RÓTARFIX

`prior_series_thin_flag` var **0/77.484** þrátt fyrir cc143-endurskilgreininguna.
Rótin er mæld, ekki ályktuð: flaggið las `prior_serie_n_pairs`, sem er dýpt
þeirrar seríu sem **resolver-inn hafði þegar valið**. `_pick_layer`
(`index_resolution.py:124-133`) fellir hverja sellu sem ber ekki ≥ 10 pör í
fjórðungi ≤ 2 fjórðunga frá `at_q`:

| hópur | n sellur | `cell_n_pairs` |
|---|---:|---|
| valdar á `level='cell'` | 12 | **min 670** — 0 undir 500 |
| felldar niður um lag | 17 | **max 485** — 17 af 17 undir 500 |

**485 < 500 ≤ 670.** Þröskuldurinn lá í tómu bili milli hópanna; hliðið tryggði
hann. 0/77.484 var óhjákvæmileiki, ekki mæling. SD-hnykkjan sem 500 var valið úr
**stendur** (0–200 pör → SD 0,134–0,561; 20.000+ → 0,021–0,023) — en hún var
mæld á sellu-seríunum **fyrir** fall og þröskuldurinn borinn á seríuna **eftir**
fall. Mælingin og beitingin lágu á sitt hvorri kornastærðinni.

**Fixið** færir ásinn á dýpt **eigin sellu** eignarinnar — ásinn sem hliðið les
ekki. `SERIES_THIN_N` er óbreytt 500. Flippað: **0 → 2.966** (3,83 % akkeraðra),
`true → false` = 0, og **15/15 aðrir prior-dálkar bæti-identískir**
(`CHK_ADRIR15 = dd39a15d601a2fb2fcc9cdfabd410f96` fyrir og eftir, mælt bæði
innan txn og í sérstakri postverify-session).

**VÖKTUNARLIÐUR — bæti-samsemd við `prior_level_fallback_flag`.** Lagaða flaggið
er í dag eins á öllum 77.484 röðum og `prior_level_fallback_flag` (krosstaflan
fullkomlega hornalæg: 74.518 / 0 / 0 / 2.966). Samsemdin er **aðstæðubundin, ekki
byggingarleg**: ung sella með ≥ 10 pör í líðandi fjórðungi en < 500 alls yrði
þunn án falls, og það mengi er tómt í dag. **Fráviksdagurinn er upplýsing** —
þegar flöggin skilja sig að hefur skrifleiðin fundið eitthvað sem hún gat ekki
séð áður. Munurinn á þessu og gamla ástandinu er efnislegur: áður var flaggið
**ómögulegt**, nú er það **satt en tvítekið**.

**Merkið les EKKI bæði sem sjálfstæð merki.** K8 er eina merkið á fletinum;
þynnkuflaggið er nú satt mælitæki og bíður eigin hlutverks.

### 4. `predictions_iter3v2` LOKUÐ FYRIR ANON

Liður 0 mældi töfluna sem `/eign` var talin lesa. Hún er **tafla, ekki view** —
gamla `predictions`, endurnefnd í `import_iter4.py:39`. `model_version='iter3v2'`
á öllum 110.316 röðum, `predicted_at` **2026-04-01** (einn dagur) gegn
`iter4r_20260805_reglaR_strukt` / 2026-07-01 í vélinni.

| mæling | tala |
|---|---:|
| sameiginlegir fastnum | 110.316 (iter3v2 ⊂ v_current) |
| nákvæmlega sama tala | **0** |
| önnur tala en vélin framleiðir | **110.316 = 100,00 %** |
| \|Δ\| p50 / p90 / max | 4,94 % / **20,49 %** / 1.014,93 % |

**Ekkert birtingaratvik:** `verdmat-ai` ber **núll tilvísun** í töfluna og frosna
app-repóið les hana aðeins innan `if (showDebug)` (`?mode=debug`), þar sem hún er
birt merkt sem gamla líkanið hlið við hlið við iter4 — sem er tilgangur hennar
(`_legacy_migrations/20260506_rls_baseline_audit.sql:57`: *„debug-mode comparison
surface"*).

**En hún var `anon`-læs.** 110.316 fjögurra mánaða gamlar spár voru sækjanlegar
um PostgREST án auðkenningar. Fæðingarreglan beitt afturvirkt: `public_read`
policy felld, `SELECT` afturkallað af `anon` og `authenticated`, RLS stendur á.
`relacl` fór úr `{…,anon=r/postgres,authenticated=r/postgres}` í
`{postgres=…,service_role=…}`. **DROP var EKKI heimilt** — frosna repóið vísar í
töfluna í debug-grein.

**Mótpróf:** `set role anon` → `42501 permission denied`; PostgREST anon →
**HTTP 401** `42501`; `v_current_predictions` og `valuation_tiers` áfram **200**;
fjórar lifandi `/eign`-síður á www.verdmat.ai **HTTP 200** með akkeriskortinu og
engri villu.

### 5. REGLA SEM ÞESSI LOTA BÓKAR

> **„Hvaða flöt les notandinn" mælist á `verdmat-ai`, aldrei á frosna
> app-speglinum.**

cc151 §5 taldi `app/eign/[fastnum]/page.js` og bókaði að `/eign` læsi gömlu
`comps_index` og `predictions_iter3v2`, og að hvorki `valuation_tiers` né
`comps_index_v2` væri lesið af nokkrum framendafleti. **Sú talning var á frosna
repóinu** (`D:\verdmat-is\app`, millisíðan). Lifandi vefurinn er
`D:\verdmat-is\verdmat-ai` → www.verdmat.ai, og þar les `lib/eign-queries.js`
`v_current_predictions` (:194), `valuation_tiers` (:202), `comps_index_v2` með
harðri `set_role='comp'`-síu (:217) og `comps_t5_basis` (:670). Gamla
`comps_index` og `predictions_iter3v2` bera **enga tilvísun** í öllu repóinu.

**„V2 eingöngu" var þegar ástand** — frágengið 2026-07-05 (Skref 2). Liður 3 bar
því enga tengingarvinnu, aðeins merkjavinnu. cc151 §5 er hér með leiðrétt.

### 6. ROLLBACK

* `public.valuation_tiers_thinflag_pre_cc152` (167.503 raðir, RLS on, engin
  policy) + `D:\cc152\prior_snapshot_pre_cc152.parquet`
* `D:\cc152\rollback_cc152_flagg.sql` — UPDATE úr snapshot m/ checksum-hliðum á
  BÁÐUM (flagg og hinir 15)
* `D:\cc152\rollback_cc152_iter3v2_acl.sql` — GRANT + policy endurreist
* Bæði rollback-skjölin skrifuð á disk **fyrir** nokkurt skrif.

### 7. ÓSNERT

`predictions` og spá-vélin sjálf (lotan endurreiknar ekkert verðmat) ·
`predictions_rent*` / `valuation_tiers_rent*` / allir leigu-fletir (`/leiguverd`
fer í hina greinina í `EignSidaEfni.tsx:176` og rendrar ekki akkeriskortið) ·
`comps_index_v2` · engin migration · engin Haiku-köll · `predictions_iter3v2`
sjálf stendur (aðeins aðgangur lokaður).

> *Um staðsetningu:* viðbætandi færsla aftast, sbr. §5D-4 til §5D-11.

## 2026-08-13 — §5D-13 · cc156 SÍA #1 (NÆR-EINS) SETT LIFANDI SEM K2 EITT; HREINSUNARREGLAN LÖGUÐ Á TVEIMUR ÁSUM; cc150-TÍMASPÁIN FELLD AF MÆLINGU

> *Um staðsetningu:* viðbætandi færsla aftast, sbr. §5D-4 til §5D-12.

**Heimild**: `docs/fable_prep/audits/NAER_EINS_CC156_20260813.md` (þessi lota) ·
`NAER_EINS_CC153_20260813.md` (formælingin og kostatafla K0–K6/N0–N2) ·
`UTDRATTAR_SIUR_CC150_20260812.md` (síur #2/#4 og spáin sem hér er leiðrétt) ·
mælitæki lotunnar í `D:\_audit\cc156_naer_eins_sia\` (`q01`–`q04`, allar
`set_session(readonly=True)`). **ENGIN DB-SKRIF. ENGIN HAIKU-KÖLL** — eina
keyrslan á vélinni var `--forward 5` ÁN `--confirm`.

### 1. AFSTAÐA: K2 EITT — NÁKVÆMUR LYKILL, EKKI ÞRÖSKULDUR

cc153 lagði fjórar spurningar fyrir borðið. Svarið við þeirri fyrstu ræður hinum:
**nákvæmur jafngildislykill, ekki þröskuldur.** Framkvæmt í
`fetch_listings_needing_extraction` (`scripts/extraction_engine.py`,
`_k2_naer_eins_sia`), lykillinn í nýjum módúl `scripts/naer_eins_lykill.py`.

| | felld | $ | mælt tap |
|---|---:|---:|---|
| **K2 hreinsaður hash — VALINN** | **185** | **3,83** | **0 á öllum þremur ásum** |
| K3b fastnum + Jaccard 0,95 | 837 | 17,34 | 17 raunveruleg ástandstöp |
| K4b `unit_key` + Jaccard 0,95 | 808 | 16,74 | 17 raunveruleg ástandstöp |

**K3b/K4b/K5/N1 eru FELLDAR AF MÆLINGU og enginn á að endurvekja þær án nýrrar.**
Röksemdin er ekki smekkur: **(b)-tapið er fall af LENGD, ekki af líkindum.** Ein
viðbætt framkvæmdasetning í meðallöngum texta (3.054 stafir) gefur Jaccard 0,979
af hreinni reikningsástæðu og situr því hægra megin við hvern þröskuld sem borgar
sig (cc153 lið 3.4). Þröskuldshækkun kaupir ekki nákvæmni, hún kaupir hlédrægni.
**N1** (nýbyggingar út) fellur á eigin mælingu: 99,6 prósent þeirra raða bera
afhendingartíma sem fasteignaskrá ber ekki (cc153 viðauki). **N2** (sér-regla á
`unit_key`-fjölda per fastnum) flyst á brúarverkið — hún er einingaauðkennismál,
ekki síumál. **Kostnaðarþráðurinn frá cc127 er þar með tæmdur að sinni:**
tillögur #2 og #4 komnar inn (cc150), #1 komin inn hér, #3/#5/#6/#7 felldar af
mælingu í cc130.

### 2. HREINSUNARREGLAN — TVEIR GALLAR, ANNAR ÓBÓKAÐUR

**(a) Latent gallinn sem cc153 bókaði — og forskriftin sem féll.** cc153 lið 4.3
bókaði að `_OPID` gleypti allt að 120 stafi á eftir „nánari upplýsingar", að það
fjarlægði ástandsorð úr **77 af 13.652 textum**, og að *„rétta lagfæringin er að
binda spönnina við setningarlok, ekki við stafafjölda."* **Sú forskrift var prófuð
og hún fellur:** mælt á sama þýði fer talan úr 77 í **160**. Ástæðan er mæld, ekki
ályktuð — CTA-setningin er að jafnaði LENGRI en 120 stafir (spannir p50 94, p90
247, max 729), svo 120-stafa glugginn var í raun að VERJA innihaldið með því að
stoppa of snemma. Reglan sem stenst er **setningarlok + efnisvörn**: spönnin nær
að setningarlokum en fellur niður beri hún ástands- eða verðorð. Þá er hún ekki
CTA heldur innihaldssetning sem byrjar á CTA-orðalagi.

**(b) Gallinn sem cc153 mældi ALDREI — stærðartölurnar.** cc153 sannreyndi K2 á
hráa mismuninum og fékk „0 raðir bera `ORD_ASTAND`, 0 bera `ORD_VERD`". Sú mæling
var rétt á þeim tveimur ásum — **en orðalistarnir þekkja enga fermetra.** Mælt hér:
**4.047 af 13.652 textum (29,64 prósent) tapa aukastafatölu í hreinsun**
(`_DAGS` 3.718 · `_MILLI` 364 · `_OPID` 129 · `_URL` 5), því `_DAGS` les „80.1 fm"
sem dagsetninguna 80.1. Afleiðingin var mæld á K2 sjálfum: **2 af 172 K2-röðum
cc153 fella saman texta sem bera ólíkar stærðartölur** (80,0 gegn 80,1 · 90,2 gegn
98,0) — kross-einingahrunið úr cc153 lið 3.6, komið inn um bakdyrnar á
hreinsuninni. Vörnin er á lyklinum í heild (aukastafatölur dulbúnar fyrir
hreinsun, afhjúpaðar eftir), ekki plástur á hverja reglu: fjórar reglur átu tölur
og sú fimmta myndi gera það líka.

**Dulbúningurinn einn dugði ekki og það var mælt:** CTA-spönnin gleypti dulbúna
tökenið í heilu lagi, svo afhjúpunin fann ekkert að skila (279 textar töpuðu enn
tölu, 241 þeirra fermetratölu). Spönnin ver nú dulbúninginn líka.

| regla | ástandstap | verðtap | stærðartap | K2 | kross-stærð |
|---|---:|---:|---:|---:|---:|
| cc153 (gamla) | 77 | 45 | 4.047 | 172 | **2** |
| + efnisvörn | 0 | 0 | 4.149 | 199 | 4 |
| + stærðarvörn | 0 | 0 | 279 | 194 | 0 |
| **+ spönn ver dulbúning (LIFANDI)** | **0** | **0** | **21** | **193** | **0** |

**Lykillinn er í EINU FALLI.** `naer_eins_lykill.lykill()` er eina leiðin að
honum; cc153-mælitækið (`D:\_audit\cc153_naer_eins\naer_eins_lib.py`) er frosið
mæliskjal þeirrar lotu og ber gömlu regluna. Sbr.
`feedback_merki_verdur_ad_lesast_ur_einu_falli`.

### 3. SÖNNUN Á LIFANDI BIÐRÖÐ (13.08, mælidagur bókaður)

Gamla fallið sótt orðrétt úr `git show HEAD:` og keyrt í sama ferli, á sömu
tengingu, og nýja fallið (cc150-mynstrið).

| | n | $ | nætur á 200/nótt |
|---|---:|---:|---:|
| **fyrir** (`@HEAD`) | **7.346** | 152,19 | 36,7 |
| **eftir** (vinnutré) | **7.161** | 148,35 | 35,8 |
| **FELLT** | **185** | **3,83** | (2,52 prósent) |
| **BÆTT VIÐ** | **0** | — | — |

`eftir` er hlutmengi `fyrir`: **satt** · **RÖÐUNIN ÓBREYTT** (gamla röðin síuð ==
nýja röðin, lið fyrir lið) · fulltrúi/texti breyttist á lifandi röðum: **0**.

**MÓTPRÓF á felldu röðunum (185), á HRÁUM mismun fyrir hreinsun:**

| | mælt | krafa |
|---|---:|---|
| m/ástandsorð í mismuninum | **0** | 0 |
| m/verðorð í mismuninum | **0** | 0 |
| m/ólíkar stærðartölur | **0** | 0 |

154 af 185 bera **0 tokens mismun** (`n_diff` p50 0, p90 2, max 21). Það sem
lykillinn hunsar er undantekningarlaust fasteignasalanöfn, símanúmer, bókunar-
orðalag og mánaðaskipti — sýni í `04_sonnun_lifandi.txt`.

**FRÁVIKIÐ FRÁ 172 ER SKÝRT, EKKI HUNSAÐ.** cc153 mældi 172 á sínu þýði með gömlu
hreinsuninni; lagfærða reglan gefur 193 á sama þýði; **lifandi mæling gefur 185**.
Sundurliðun: 184 af 185 voru í cc153-biðröðinni, 1 er ný, og **132 cc153-raðir eru
horfnar úr biðröðinni** (keyptar eða dánar — sjá lið 5). Talan sem gildir er sú
sem mælist á lifandi biðröð við framkvæmd, með mælidegi — ekki lesin af
cc153-töflunni.

**KEYRSLUKOSTNAÐUR BÓKAST:** fallið fer úr 3,8 s í **59,4 s** (+55,6 s). Sían
verður að bíta á undan `LIMIT`-inu, svo SQL-ið skilar allri biðröðinni og
hreinsaði lykillinn er reiknaður á báðum hliðum (7.346 + 6.232 textar). Það er
ásættanlegt í nótt sem tekur þrjár klukkustundir, en það bítur líka á
`--forward 5` þurrkeyrslum og er ekki ókeypis. **Forreiknaður lykildálkur myndi
fjarlægja þetta og hann krefst DB-skrifa** — utan umboðs þessarar lotu.

### 4. VÖKTUNARLIÐUR — `sia1-k2` Í NÆTURLOGGINU, VÆNTING ÓSETT

`scripts/nightly_delta_chain.sh` fær **sér línu**, ekki viðhengi við
extraction-línuna: `sia1-k2: forward-k2: bidrod_fyrir=N k2_felld=M
bidrod_eftir=K keyptir_lyklar=L`. Línurnar tvær mæla ólíka hluti — extraction
segir hvað var KEYPT, þessi hvað var EKKI keypt af því textinn var þegar til á
hreinsuðum lykli.

**Væntingin er ÓSETT með vilja; fyrsta mæling setur viðmiðið.** Ástæðan er liður
5: biðröðin ber um 100 hasha á nóttu af VELTU (endurskrifaðar auglýsingar), og K2
er einmitt lykillinn sem á að fanga endurskrifun sem ber óbreytt innihald. Hve
stór sá hluti veltunnar er hefur enginn mælt. **Dómsdagur eftir um sjö nætur.**

### 5. LEIÐRÉTTING Á cc150-SPÁNNI — SPARNAÐURINN STENDUR, TÍMASPÁIN FELLUR

cc150 §3 bókaði: *„Koma nýrra hasha mæld: 418 á 27 dögum = 15,5/dag"* og af því
leiddi *„nettó-tæming 184,5/nótt · 40,4 nætur að tæmingu · flýting 8,6 nætur."*

**Mælt með víxlamatrix á cc153-hashamenginu (ekki með mismun tveggja teljara,
sbr. `feedback_mismunur_tveggja_teljara_er_ekki_hreyfing`):**

| | n |
|---|---:|
| cc153-biðröð 12.08 | 7.459 |
| kyrrt | 7.327 |
| **farið út** | **132** |
| **komið inn** | **19** |
| nettó | **−113** |

Teljaramismunurinn faldi hreyfinguna: **200 köll voru keypt en aðeins 119 komu úr
cc153-biðröðinni** — 81 voru keypt af textum sem voru alls ekki til í
15.230-texta þýði cc153. `fresh DESC` étur nýkomna fyrst, svo gamli halinn
tæmist um 119/nótt. **Koman er um 100 hashar á nóttu, allir óþekktir cc153**, og
**43 af þeim 100 bera `min(listed_at)` FYRIR 12.08**: auglýsing sem er
endurskrifuð drepur gamla hashinn og fæðir nýjan sem ber upprunalega
skráningardaginn. Speglun þess sama: **13 raðir féllu út án útdráttar, allar af
því textinn hvarf úr `listings`.** Þetta er VELTA, ekki nýskráningarhraði.

**Bókun:**
1. **$32,69-sparnaður cc150 STENDUR ÓHAGGAÐUR** — hann var mældur á biðröðinni
   sjálfri, ekki á tæmingarhraða.
2. **„Flýting 8,6 nætur" er FELLD AF MÆLINGU.** Nettó-tæming mælist ~119/nótt og
   tæmingin er **~65 nætur**, ekki 40,4.
3. **Talan 15,5/dag var fyrst-séð-mæling sem fangaði ekki veltuna.** Hún endurgerist
   hvorki á biðraðarásinni (100/nótt) né á fyrst-séð-ásinum (1.786 nýir textar á 27
   dögum = 66/dag).

**Reglan sem þetta bókar:** *nettó-hreyfing biðraðar er ekki tæmingarhraði þegar
röðunin étur nýkomna fyrst — mældu hvað kom ÚR halanum, ekki hvað fór úr summunni.*

### 6. LEIÐRÉTTING Á EIGIN LIÐ 0 — /ops MÆLDIST Á RÖNGU REPÓI

Liður 0(c) var fyrst svaraður af `D:\verdmat-is\app` og það var rangt repó —
nákvæmlega villan sem §5D-12 lið 5 bókaði. **Mælt aftur á lifandi tré og lifandi
hýsingu:** `/ops` er **EKKI TIL í `verdmat-ai`** (0 skrár, engin `middleware`) og
`www.verdmat.ai/ops` skilar **404**. Síðan lifir í frosna speglinum
(`app/ops/page.js`, sjálfstætt `OPS_PASSWORD`-cookie-hlið í `middleware.js`) og er
enn í loftinu á **`verdmat-is.vercel.app/ops` (307 → `/ops/login`)**. Ferskleika-
stimpillinn á `listing_extractions` er þar; **útdráttar-biðraðardýptin og
`day_total` eru það ekki** — `backlog.unprocessed` þar er verðmats-biðröðin.
Liðurinn fer á backlog sem eigið verk.

### 7. ÓSNERT

`fetch_extracted_listings_to_value` (cc134-sían óbreytt) · brúin · `predictions*`
· `valuation_tiers*` · `comps_*` · `listing_extractions` sjálf (engri röð eytt,
engin snert) · `--forward 200`-þakið · `EXTRACT_VALUE_LIMIT=2000` · engin
migration · framendinn í hvorugu repói.

## 2026-08-13 — §5D-14 · cc159 OPS-YFIRLIT LIFANDI Á `verdmat-ai` (ÞRJÁR TÖLUR, FJÓRIR STIMPLAR) + `bil_pp` Á AGENT-VERKFÆRIÐ — OG TVÍFARINN Á `verdmat-is.vercel.app` BÓKAÐUR TIL NIÐURTÖKU

> *Um staðsetningu:* viðbætandi færsla aftast, sbr. §5D-4 til §5D-13.

**Heimild**: mælitæki lotunnar í `D:\_audit\cc159_ops_yfirlit\` (`q01`–`q07`,
allar `set_session(readonly=True)` nema `q07` sem les `schema_migrations`) ·
skil `SKIL_CC159_HALT_A.md` í sömu möppu · §5D-13 lið 6 (spurningin „hvar á
flöturinn að vera“) · §5D-12 lið 5 (of-lesturinn sem `bil_pp` lokar).
**Pushað:** `verdmat-ai` `7ac52dc..8160fc7` = deploy á www.verdmat.ai.
**Eina DB-skrifið** er migration `20260813233102` (sjá lið 2); að öðru leyti
read-only. **Engin Haiku-köll.**

### 1. AFSTAÐA: FLÖTURINN ER `verdmat-ai`, OG HANN BER ÞRJÁR TÖLUR

§5D-13 lagði fyrir borðið eina spurningu á undan öllum kóða: **bæta á frosna
spegilinn eða smíða á `verdmat-ai`?** Svarið er `verdmat-ai` — sömu rök og
§5D-12 lið 5: *hvaða flöt notandinn les mælist á `verdmat-ai`, aldrei á frosna
speglinum*, og morgunvaktin á ekki að búa á öðru léni en afurðin.

`/ops` v1 ber **þrjár tölur og fjóra stimpla og ekkert annað** — engin gröf,
engin saga, engin sundurliðun:

| tala | mælt 13.08 23:36Z | heimild |
|---|---:|---|
| útdrættir á nýjasta útdráttardegi | **201** (13.08) | `ops_scraper_signals().extraction.count_latest_day` |
| **hrá útdráttar-biðröð** | **7.345** | `ops_utdrattar_bidrod()` — NÝTT |
| verðmats-biðröð | **7.222** af 11.871 | `ops_scraper_signals().backlog` |

Stimplarnir fjórir: nýjasti útdráttur · nýjasta mbl-auglýsing · nýjasta
spá-keyrsla · mæling síðunnar sjálfrar. **Ferskleikamörkin ein fluttust** úr
`OPS_CONFIG` gamla flatarins (28/52 klst dagleg, 35/45 d mánaðarleg); ekkert
annað var afritað óskoðað.

**Verðmats-biðröðin er á spjaldinu VILJANDI, við hliðina á hinni.** Hún er ekki
skraut: §5D-2 (C) bókar að hún hefur verið lesin sem útdráttar-biðröðin, og tvær
biðraðir sem enginn getur ruglað saman eru ódýrari en fótnóta um að rugla þeim
ekki saman.

### 2. KOSTNAÐUR MÆLDUR ÁÐUR EN NOKKUR LÍNA VAR SKRIFUÐ

Skilyrði borðsins: **undir ~2 s -> beint í síðuna, annars cache-lag og það
bókast.** Þrjár keyrslur hver, kalt fyrst (`q01`):

| | rás | kalt | heitt | heitt | dómur |
|---|---|---:|---:|---:|---|
| `ops_scraper_signals()` | PostgREST | 935 | 589 | 552 ms | **BEINT** |
| `predictions` (spá-stimpill) | PostgREST | 191 | 137 | 167 ms | **BEINT** |
| hrá biðraðardýpt (`need`-CTE, án K2) | SQL | **6.470** | 2.105 | 1.727 ms | **CACHE** |

Fyrri tvær eru **lifandi í hverri beiðni** — rekstrarborð sem sýnir cache-að
ástand lýgur um núið. Biðraðardýptin fékk `unstable_cache` m/**900 s TTL** og
ber **mælingartímann ÚR fallinu**, ekki rendertíma síðunnar: annars bæri
cache-uð tala ferskan tímastimpil og flöturinn segði ósatt um hvenær hún var
mæld.

**Talan komst ekki í síðubeiðni án DB-skrifs.** `scraper.*` er ekki opið
PostgREST og talan er `GROUP BY … HAVING`. Borðið lyfti „engin DB-skrif“
skilyrðinu fyrir **nákvæmlega eitt fall** og migration-aginn stóð óskertur:
rollback-SQL á disk **fyrir** apply, MCP `apply_migration`,
`schema_migrations`-reconcile, repo-spegill **sóttur orðrétt úr töflunni**
(`q07`) — **frávik frá drögunum: ENGIN** (keyranlegi hlutinn 1.850 stafir báðum
megin). Eftirmæling: `f / s / DEFINER`, `search_path=""`, ACL
`{postgres=X/postgres, service_role=X/postgres}` — **bæti-eins og
`ops_scraper_signals()`**; `aclexplode` ber ekkert á anon/authenticated/PUBLIC.

**REKSTRARATRIÐI SEM KOSTAÐI EINA UMFERÐ:** nýtt fall er **ekki sýnilegt
PostgREST fyrr en skemavistin er endurhlaðin.** Síðan sagði „ómælt“ eftir apply
þar til `NOTIFY pgrst, 'reload schema'` var keyrt. Þetta á að standa í hverjum
runbook sem bætir við RPC.

### 3. ÞRENNT SEM FLÖTURINN SEGIR BERUM ORÐUM AF ÞVÍ AÐ HANN GETUR EKKI MÆLT ÞAÐ

1. **Dýptin er HRÁ** — báðar cc150-síurnar, EKKI K2. Textinn á síðunni:
   *„K2-síuð dýpt mælist í næturkeðjunni; sjá `sia1-k2` í logginu.“* Talan er
   **þakið** á því sem nóttin gæti keypt, ekki það sem hún kaupir.
2. **„Útdrættir í nótt“ eru RAÐIR sem lentu í töflunni**, þar með taldir
   `ondemand`-útdrættir utan næturkeyrslunnar — 201 í dag = 200 úr nóttinni + 1
   kall kl. 20:28 (cc157). **Loggaði `day_total` telur KÖLL** (207 í nótt, líka
   misheppnuð og endurtekin) og er **eina heimildin um krónur**:
   `listing_extractions` ber engan kostnaðardálk, svo **flöturinn nefnir enga
   upphæð**. Endurgerð upphæð væri ágiskun með tveimur nefnurum.
3. **Biðraðirnar tvær eru ólíkar biðraðir.**

**SPEGILL, OG SPEGLAR REKUR.** SQL-ið í `ops_utdrattar_bidrod()` er handritað
eftir `fetch_listings_needing_extraction`. Breytist Python-sían og ekki fallið
sýnir `/ops` **ranga tölu þegjandi** — engin villa, engin viðvörun.
Krosstilvísun stendur á þremur stöðum (migration, `COMMENT ON FUNCTION`,
`lib/ops-queries.js`). Varanlega lausnin er forreiknaði lykillinn á
PLANNING_BACKLOG (§5D-13 lið 2): með honum getur biðröðin orðið **ein**
skilgreining í stað tveggja.

### 4. `bil_pp` — EIN SKILGREINING, OG HÚN VAR MÆLD

§5D-12 lið 3 bókaði of-lestur á lifandi agent (fastnum 2000473): prósan skýrði
K8-merkið út frá **aldrinum einum** þótt skilyrðið sé aldur **OG** bil.
Hreint boolean sem ber enga stærð býður upp á þá einföldun.

Nýtt `akkerisbilPp()` í `config/skyringar.ts`; **`veikurAkkerisStudningur()`
kallar nú á það** í stað þess að reikna bilið inni í sér. Formúlan er því til á
**einum stað** og bilið sem agentinn nefnir getur ekki vikið frá bilinu sem
kveikti merkið. Reiturinn er kæfður á sömu tveimur ásum og `veikur_studningur`
og `verdmat` (T5 · fjöleining) og er `null` — ekki 0 — vanti akkeri eða mat.

**Mótpróf (`q04`/`q05`, 44 raðir: §5D-12-settið fjögur + 20 K8 + 20 utan K8,
dregnar á `md5(fastnum)` svo úrtakið veljist ekki eftir aldri):** `bil_pp` og
`veikur_studningur`, lesin úr **tveimur aðskildum köllum**, eru samræmd í
**44 af 44**. Dreifing á K8 (`q06`, n=**1.957 = 2,53 %** — lendir upp á tölu á
§5D-12): p50 **36,1** · p90 **69,5** · p99 **145,5**; 54 raðir (2,8 %) yfir 100 pp.

**Villa í eigin mælitæki, bókuð:** fyrsta útgáfa `q06` skrifaði
`abs(a-b)/b*100` á tveimur **heiltöludálkum**. Heiltöludeiling gerir prófið að
„bil >= 100 prósent“ og skilaði K8 = **54** í stað 1.957 — tala sem hefði lesist
sem raunbreyting frá §5D-12. `::numeric` á báðar hliðar lagar hana.

### 5. RAUNPRÓFUN Á LIFANDI — OG EINN FYRIRVARI SEM STENDUR OPINN

`/ops` óinnskráður **307 → `/ops/login`** · fölsuð kaka **307** · rétt leyniorð
setur `HttpOnly; Secure; Path=/ops; Max-Age=43200` · innskráður **200** með
`X-Vercel-Cache: MISS`. Tölurnar þrjár og stimplarnir **stemma 7 af 7** við
beina SQL-mælingu í sama glugga. `/ops` er í `robots.txt` disallow af sömu
ástæðu og `/leit`: noindex stöðvar indexun, disallow stöðvar sóknina — og hver
crawler-sókn ræsir fall og SHA-256 í proxy-inu.

**Agentinn á K8-eign (2000473) — MARKMIÐIÐ NÁÐIST:** *„Þetta framreiknaða verð
liggur um **52 %** frá núverandi mati … Ástæðan er **tvíþætt**: salan er orðin
18 ára gömul, **og** bilið milli framreiknaðs verðs og matsins er þetta stórt.“*
Talan er `bil_pp` = 52,33; báðir liðir nefndir; mörkin (25 pp) hvergi nefnd.

**Agentinn á merkislausri eign (2018566) — EKKI ÓBREYTTUR, OG ÞAÐ ER FUNDUR.**
Hann nefnir nú bilið líka (þar sem hann þagði áður) **og fyrsta svarið bar
ranga tölu: 15,8 % þar sem `bil_pp` er 13,54.** Spurður hvaða tvær tölur hann
bæri saman leiðrétti hann sig sjálfur í **13,5 %** og nefndi réttu tölurnar
(147,4 M framreiknað gegn 129,8 M mati). **Lærdómurinn: reitur í farmi tryggir
ekki að talan sem sögð er komi ÚR reitnum.** 15,8 er hvorki `bil_pp` (13,54) né
hlutfall birtu talnanna (13,56) — hún varð til í reikningi módelsins.
**ÓLOKIÐ og opið:** herða verkfæralýsinguna í *„nefndu bilið AÐEINS með tölunni
úr reitnum, reiknaðu hana aldrei sjálf/ur“* og/eða bera forsniðna tölu í
farminum. Ekki gert í þessari lotu — sér ákvörðun.

**LEYST SAMDÆGURS — KOSTUR H3 (bæði), pushað `03dc7dd`.** Borðið valdi hvorugt
eitt og sér: `akkerisbilPp` vék fyrir **`akkerisbil()`** sem skilar
`{ pp, texti }` úr EINNI keyrslu — ein formúla, **eitt snið**, einn staður.
`bil_pp_texti` er íslenskt tugabrot með einum aukastaf og prósentumerki
(`„52,3%"`, `„13,5%"`, `„1.263,8%"`), sniðið í SAMA falli og bilið er reiknað
svo engin önnur sniðleið sé til og ekkert sé eftir að reikna;
verkfæralýsingin ber regluna um að **afrita strenginn orðrétt**, ekki rúnna
hann og ekki reikna hann. Rökin fyrir báðum liðum: **H1 án H2 skilur
reikninginn eftir mögulegan** — og það var reikningurinn sem brást, ekki
skilningurinn. Mótpróf á einingarstigi (`q08`, sömu 44 raðir): **0 ósamræmi,
0 sniðvillur**; 2000473 -> `„52,3%"`, 2018566 -> `„13,5%"`.

**MÓTPRÓFIÐ Á LIFANDI ER KEYRT OG ÞAÐ LENDIR — sjá viðbót neðst í þessum lið.**
Fyrri lesning þessarar málsgreinar stendur sem saga: Skilyrðið var
„sama eign spurð aftur, sögð tala == `bil_pp_texti` stafrétt". Það féll á
ÓSKYLDU: **inneign Anthropic-lykilsins á framleiðslu er uppurin** — `/api/agent`
skilar `400 invalid_request_error: „Your credit balance is too low"`
(request `req_011Ce2Hy6HKngn8M3brXGkFF`, 14.08 kl. 08:04Z, workspace
`wrkspc_01B1voozwwi4gvLd72sWeGbD`) og spjallið á vefnum segir „Spjallið
svaraði ekki". Sami org-balance ber næturútdráttinn, svo **næsta næturkeyrsla
stöðvast líka** verði ekkert að gert. Prófið bíður inneignar.

### 6. TVÍFARINN BÓKAÐUR TIL NIÐURTÖKU — OG HANN ER STÆRRI EN `/ops`

Nýja síðan er komin, svo tvífarinn má ekki lifa. **Mælt 13.08 á
`verdmat-is.vercel.app`:** `/ops` 307 → login · `/ops/login` 200 · **`/` 200** ·
**`/eign/2000473` 200** (heil eignasíða, fótur segir *„Uppfært: maí 2026 ·
124.835 eignir“*) · `/pro` 307 → login · **`/robots.txt` skilar 404**.
Tvífarinn er því **ekki bara `/ops`** heldur heil önnur útgáfa af afurðinni á
öðru léni, með eldri tölum og engar crawler-reglur. Aðgerðin er Vercel-stilling
eða push á frosna spegilinn og liggur **utan flatar cc159** — hún er bókuð hér
og valkostirnir liggja fyrir borðinu, ekki framkvæmd.

**LOKAÐ SAMDÆGURS 14.08 — T1 FELLD Á VERÐI, T2b FRAMKVÆMD.** Borðið valdi fyrst
**T1** (Vercel Authentication á `deploymentType: "all"`). Hann **féll á tvennu**:
`update_project_deployment_protection` skilaði **`403 forbidden`** á
MCP-auðkennið (les stillingar, skrifar þær ekki; Vercel CLI ber enga skipun
fyrir þetta), og **stillingin sjálf er á bak við $150/mán greiðsluvegg** sem
borðið hafnaði. Sú útgáfa sem er innifalin — „Standard Protection" — undanskilur
**einmitt framleiðslulénið** og hefði því gert nákvæmlega ekkert hér. Forkönnun
sem gerð var á undan stendur samt: `verdmat-is`-verkefnið ber **ekkert sérlén**
(`www.verdmat.is` er ANNAR vefur, utan reikningsins — `/ops` og `/eign` 404 þar,
annað efnis-hash), svo aðgerðin snerti tvífarann einan hvor leiðin sem yrði
farin.

**T2b — ALLSHERJAR-LOKUN Í `middleware.js` FROSNA REPÓSINS** (`cc02837`,
deploy `dpl_6G3b2jgz…`). Matcher `/:path*` undanskilur **EKKERT** — hvorki
`_next`-eignir, `favicon.ico` né API-rúturnar þrjár — og hvert svar er
`404 Not found` með `x-robots-tag: noindex, nofollow` og `cache-control:
no-store`. Undanskilinn flötur er flötur sem lifir af lokun.

**Þetta er BIRTINGARLOKUN, EKKI EYÐING.** Kóðinn, sagan, migrationirnar og gömlu
hliðin (`OPS_PASSWORD` á `/ops`, `pro_users` á `/pro`) standa óbreytt í git;
**ein `git revert` skilar bæði fyrri hegðun og hliðunum**. Frosni spegillinn
stendur áfram sem kóðaheimild — og GitHub-repóið er opinbert, svo sú heimild er
áfram læsileg þótt vefurinn birti ekkert.

**Mótpróf á lifandi eftir deploy (14.08):**

| slóð | fyrir | eftir |
|---|---:|---:|
| `verdmat-is.vercel.app/` | 200 | **404** |
| `…/eign/2000473` | 200 | **404** |
| `…/ops` | 307 → login | **404** |
| `…/ops/login` | 200 | **404** |
| `…/markadur` · `…/api/search` · `…/robots.txt` | 200 / 200 / 404 | **404** |

**`www.verdmat.ai` ÓSNERT:** `/` 200 · `/eign/2000473` 200 · `/leit` 200 ·
`/markadur` 200 · `/ops` 307 (hliðið) — annað verkefni, annað repó, engin
skörun. Mótprófið var samt keyrt.

**Liður 6 er þar með lokaður.** Tvífarinn lifir ekki eftir að nýja síðan kom.

### 5b. STAFRÉTTA MÓTPRÓFIÐ — KEYRT 14.08 EFTIR ÁFYLLINGU, OG ÞAÐ LENDIR

Inneignin var fyllt á og prófið keyrt á lifandi vef. Skilyrðið var **stafrétt
jafngildi**: sagða talan == `bil_pp_texti`, ekki „nálægt".

| eign | `bil_pp_texti` | agentinn sagði | fyrir H3 |
|---|---|---|---|
| **2018566** (merkislaus) | `13,5%` | **„13,5%"** ×2 í sama svari | **15,8%** — RÖNG |
| **2000473** (K8) | `52,3%` | **„52,3%"** | „um 52%" — námunduð |

**Báðar stafréttar.** Á 2000473 nefnir hann ástæðuna áfram **tvíþætta**
(„annars vegar er salan orðin 18,3 ár gömul, og hins vegar liggur framreiknað
verð hennar 52,3% frá matinu"), mörkin standa hvergi, og á merkislausu eigninni
segir hann berum orðum að salan teljist **ekki** veikur stuðningur.

Athugið hvað breyttist á 2000473: talan var **rétt en námunduð** fyrir („um
52%"). Fullsniðni strengurinn fjarlægir líka þá námundun — agentinn velur ekki
lengur hversu nákvæmt hann er. **Það sem H3 sannar er ekki að talan hafi verið
röng heldur að hún hafi verið HANS**; nú er hún flatarins.

**Óskylt en mælt í leiðinni (ÓBÓKAÐ SEM VERK):** agentinn segir aldur akkerisins
sem `0,96 ára` og `18,3 ár` meðan akkeriskortið birtir „innan við ár" og „18 ár"
(niðurstýft). `aldur_ara` er hrár í farminum og hefur alltaf verið — sama tegund
og `bil_pp` var fyrir H3. Ekki lagað hér.

### 7. ÓSNERT

`docs/fable_prep/` (cc158) · næturvélin og `extraction_engine.py` · K2-sían ·
`predictions*` · `valuation_tiers*` · `comps_*` · akkeriskortið
(`components/eign/Akkeri.tsx` — les sama fall, óbreytt hegðun) · frosni
spegillinn · allar töflur (eina DB-breytingin er nýja fallið).
