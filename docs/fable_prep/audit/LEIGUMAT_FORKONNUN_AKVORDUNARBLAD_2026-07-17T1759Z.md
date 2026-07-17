# ÁKVÖRÐUNARBLAÐ — FORKÖNNUN LEIGUMATS (cc13)

> **Lota:** cc13, 2026-07-17 · könnun hófst 2026-07-17T17:59:04Z, dómur skráður 2026-07-17T19:34:21Z
> **Eðli:** 100 % read-only forkönnun (engin skrif í repo/DB/út á við meðan á könnun stóð; þetta skjal + commit er eina skrifið, að fyrirmælum eiganda eftir dóm).
> **Spurningin:** Getur verdmat.ai boðið leigumat sem stenst sömu heiðarleikakröfur og sölumatið (mælanleg þekja, vissubil, T5-hliðstæða fyrir ómetanlegt)?
> **Fylgiskjöl:** `docs/fable_prep/RENT_MODEL_CARD.md` (heildargreining rent_v1) · `docs/fable_prep/RENT_AUDIT.md` · DECISIONS 2026-07-02 #6 (aldrei módeluð leiga í samsettri tölu).

---

## 0. Stóra uppgötvunin

Spurningin er ekki „getum við smíðað leigumat" — **það er þegar smíðað.** Fable-lota 29.06–01.07.2026 byggði heilan leigu-stakk (`rent_v1`: þjálfun → repeat-panel → leiguverðsjár-anchor → conformal → skorun → staging-load) sem situr í `predictions_rent_staging` (158.314 raðir) og var aldrei flippað live (`predictions_rent` = 0). Forkönnunin breyttist því úr smíðamati í **promotion-mat**.

---

## 1. Gagnakortlagning (mælt 17.07.2026)

### a) HMS leigusamningaskrá — til, en FROSIN

- `leiguskra.csv` í sömu OCI-fötu og kaupskráin (`.../public_data_for_download/o/leiguskra.csv`): 200 OK, 30,1 MB, **120.558 raðir, 21 dálkar** (m.a. FASTNUM, HEILDARVERD, STAERD, FJ_HERBERGI, DAGSFRA/DAGSTIL, VISITALA, TEGUND, ONOTHAEFUR_SAMNINGUR), latin-1, `;`-skil.
- **Last-Modified 25.07.2024**; þinglýst 2011-01→**2024-03**. Árstakturinn hrynur: 2022: 8.716 · 2023: 3.850 · 2024: 118. Til samanburðar var kaupskra.csv í sömu fötu uppfærð 17.07.2026 kl. 02:01. Þinglýsing leigusamninga dó út með nýju leiguskránni — **skráin frýs; þetta er ekki bilun heldur endanlegt.**
- **Nýja leiguskrá HMS**: skráningarskylda ALLRA leigusala frá 1.1.2026 (30 daga frestur frá undirritun) — nær-rauntíma grunnur, en hrágögn **EKKI opin** (samningar undanþegnir upplýsingalögum; tillaga um afléttingu í ferli; mælaborðið er Power BI-embed án bulk-CSV).
- Opinberar afleiður nýju skrárinnar, báðar nothæfar:
  - **Leiguverðsjá-CSV** (prismic-CDN, `Gogn_til_nidurhals_leiguverdsja.csv`): mánaðarleg aggregöt **2024-01→2026-05** per landshluta-/sveitarfélagsflokk × herbergi × markaðsleiguflokk, með FJOLDI_SAMNINGA, MEDAL_LEIGUVERD, MEDAL_FERMETRAVERD. Síðustu 3 mán (mars–maí 2026, markaðsleiga): 56.092 samningsfærslur; allar grófsvæðis-sellur setnar (minnsta 46). ATH: talan er samninga-STOFN per mánuð, ekki nýtt flæði.
  - **Leiguvísitala** (`leiguvisitala.csv`, sama OCI-fata): **LIFANDI** — Last-Modified 15.07.2026; 2023-05=100 → 2026-05=**129,3**.
- Verkefnisskrár: `leigusamningar_gogn.xlsx` fannst EKKI undir því nafni á D:\ né í notandamöppum. Nærgögnin eru `D:\Leiguskra - scrape\` (atvinnuhúsnæðis-leiguscrape apríl 2026): `leigugrunnur_hreinsadur_v2.xlsx` (455 hreinsaðir, hnitaðir, VNV-leiðréttir ATVINNU-leigusamningar) og `leigumatstol.html` (standalone atvinnu-leigumat: vegið mat = VNV-leiðréttur leigugrunnur + kaupskrár-implied yield [WACC-viðmið 6,3–6,7 % frá Reitum/Eik/Heimum/Kaldalóni] × tegundar-/ástandsstuðlar; „Nákvæmt"-flipi með Haversine-radíus-comparables). Gott UI-fordæmi; ekki íbúðagögn.

### b) Eigin leigu-ask (scraper.listings, tenure='rent')

- **1.591 lifandi** (mbl 695 + myigloo 896) + 495 withdrawn = 2.086 alls; first_seen aftur til 2021-02; **1.401 nothæf** (verð > 30K + stærð 20–1000 fm).
- **Ask ≠ samningur — hlutfallið ER mælanlegt: ~1,15–1,20.** RVK 1/2/3 herb: ask-fm 5.065/4.993/4.305 kr vs leiguverðsjá 4.363/4.258/3.619 kr (1,16/1,17/1,19); Capital_sub 2/3 herb: 1,20/1,15. Fyrirvari: leiguverðsjáin telur samningastofn (þ.m.t. eldri samninga), askið er nýtt flæði — hluti bilsins er raunveruleg ask-premía, hluti stofn-tregða. Fyrir vaktarrás dugar bandið; fyrir kvörðun þarf það ekki að vera hreint.

### c) HMS leiguvísitala

Í heimildasafni cc5 (`data/raw/opin_gogn/hms/visitolur/leiguvisitala.csv`) og lifandi mánaðarlega — dugar sem tíma-akkeri.

### d) Það sem þegar er smíðað (rent_v1-stakkurinn, 29.06–01.07.2026)

- **Módel:** LightGBM `rent_v1`, 18 features, þjálfað á **111.818 leiguskrár-samningum 2011–2023** (35.053 fastnum), GroupKFold-by-fastnum: **OOF MAPE 12,97 % / medAPE 7,73 % / bias ~0**.
- **Conformal:** `rent_conformal_v2_tegund` — **sannreynd þekja cov80 = 80,55 % / cov95 = 94,99 %** (held n=21.787); miðgildis-PI-breidd 38 % (80 %) / 77 % (95 %).
- **Anchor:** `rent_anchor_v2_herbergi_fm` — leiguverðsjár-HFAC per herbergi × k_global=1,103; valuation-gluggi **2026-05** (frosinn).
- **Staging:** 158.314 eignir skoraðar; live=0. Flip-gate aldrei keyrt.

---

## 2. Þekjumat (svæði × tegund; mælt, ekki giskað)

- **Fjölbýli þéttbýlis: JÁ — og víðar en grunurinn (101/107/105) sagði.** Einnig 200/220/110/104/108, Reykjanesbær (262: 1.095 samningar 2021–23), Akureyri (600: 881). OOF: APT_FLOOR·RVK 33.192 raðir MAPE 12,3 %; APT_FLOOR·Capital_sub 24.143 raðir **10,0 %**.
- **Sérbýli: veikt alls staðar — en öðruvísi en salan.** SFH 18–20 % MAPE **FLATT yfir öll tíer** (Capital_sub verst, 20,2 %); Country-stórslys sölumódelsins erfist EKKI (Country-tíer +0,7 pp vs RVK á leigu, +10,5 pp á sölu) — leiga verðleggur notagildi, ekki land. Postnr-sellur sérbýlis þunnar (stærsta: 200-einbýli 195/3 ár).
- **Leigu-sérstaka áhættan er óformlegar einingar:** APT_UNAPPROVED 21,4 % · APT_ROOM 20,9 % · APT_ATTIC 19,1 % · APT_BASEMENT 17,7 %.
- **211 af 286 postnr×tegund-sellum < 30 samningar/3 ár** (2021–23, nothæfir) → T5-hliðstæða er skylda, ekki valkostur.
- **fj_herbergi vantar á 66,6 % skorunar-universins** (105.496/158.314 → mean-HFAC fallback) — stærsta einstaka skorunar-takmörkunin.

---

## 3. Aðferðarskissa

- **Leiðin er þegar valin og smíðuð:** módel + leiguverðsjár-anchor + split-conformal. Comparables-leiðin (leigumatstol-mynstrið, Haversine) stendur sem gagnsætt UI-lag („sambærilegar leigueignir í radíus") OFAN Á módelið, ekki í staðinn.
- **T5-leiga (ómetanlegt):** sama þrepahugsun og salan — lágt þrep/ómetanlegt þegar (i) canonical ∈ {APT_UNAPPROVED, APT_ROOM, EXCLUDE}, (ii) conformal-sellan fellur á global-fallback, (iii) fj_herbergi vantar → breiðari bil eða þreplækkun (ákvörðun í promotion-lotu).
- **Vaktin (ágúst-hliðstæðan) er strúktúrelt veikari en sölunnar og verður að segjast hreint út:** engin per-eign truth eftir 2024-03. Þrjár rásir, allar aggregat:
  1. **Leiguverðsjá mánaðarlega** → módel-miðgildi vs LVS-sella per svæði×herbergi (level-drift).
  2. **Leiguvísitala** (lifandi) → anchor-refresh-taktur.
  3. **Eigin ask vs módel** innan ask-premíu-bands 1,15–1,20 (flæðis-vísir).
- **Orðalag vissubila verður að bera kvörðunar-eðlið:** „kvarðað á sögulegum leigusamningum (2011–2023), stigfært á leiguverðsjá HMS" — cov80-fullyrðingin gildir um sögulegu dreifinguna + level-akkerið, ekki um beina 2026-mælingu.

---

## 4. Ákvörðunartafla

| Liður | Mat |
|---|---|
| **Gögn** | Söguleg dýpt sterk (111.818 samningar m/FASTNUM); framvirk truth aðeins aggregat (leiguverðsjá+vísitala lifandi); hrá ný leiguskrá lokuð |
| **Þekja** | Fjölbýli þéttbýlis GO; sérbýli/óformlegt aðeins með T5-lagi; 211/286 postnr-sellur < 30 |
| **Aðferð** | Til og sannreynd (cov80 80,55 %/cov95 94,99 %); vantar promotion-gate, ekki rannsókn |
| **Umfang** | **~3–4 CC-lotur:** (1) anchor-refresh á 2026-07 LVS/vísitölu + endurskorun · (2) T5-þrep + fj_herbergi-stefna · (3) flip-gate parity + loud labeling + agent-reglubreyting · (4) vaktarpípa (LVS-pull + ask-panel) |
| **Heiðarleikaáhætta** | Miðlungs-há: (1) engin per-eign truth eftir 2024-03; (2) fj_herbergi 66,6 % fallback; (3) óformlegar einingar 18–21 %; (4) ask-premía má ekki blandast samningsmati; (5) anchor frosinn 2026-05 → refresh-skylda fyrir flip |
| **Tillaga lotu** | **GO-á-promotion-lotu MEÐ skilyrðum** (T5-lag, loud labeling skv. DECISIONS 2026-07-02 #6, vaktarrásir skilgreindar FYRIR flip, anchor ≤ 2 mán) |

---

## 5. DÓMUR EIGANDA (2026-07-17)

**Samþykkt — GO á promotion-leiðina MEÐ öllum skilyrðum blaðsins:**

1. T5-lag inn.
2. Loud labeling: **„MÓDELSPÁ — ekki mæld leiga"**.
3. Vaktarrásirnar þrjár (leiguverðsjá / leiguvísitala / ask-band) skilgreindar **FYRIR** flip.
4. Anchor aldrei eldri en 2 mánuðir.

**Tímasetning:** promotion-lota #1 ræsist ~22.07.2026, EFTIR override-lotuna (20.–21.07). Arkitektinn skrifar promptana fjóra á grunni þessa blaðs.

**Agent-reglan „aldrei leigumat" stendur ÓBREYTT þar til flip-gate promotion-lotu #3 opnar hana formlega.**

*Skjalfest af cc13 (Claude Fable 5); þetta skjal + commit þess er eina skrif lotunnar.*
