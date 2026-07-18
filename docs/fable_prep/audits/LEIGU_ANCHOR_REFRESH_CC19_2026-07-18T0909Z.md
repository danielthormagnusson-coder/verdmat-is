# ÚTTEKT — LEIGU-PROMOTION #1, SKREF 2: ANCHOR-REFRESH (cc19)

> **Lota:** cc19, 2026-07-18 · könnun hófst **2026-07-18T09:09:06Z** (UTC), staðartími 2026-07-18T09:09:10+0000
> **Umboð:** `docs/fable_prep/audit/LEIGUMAT_FORKONNUN_AKVORDUNARBLAD_2026-07-17T1759Z.md` §5 (dómur eiganda), skilyrði 4: **„Anchor aldrei eldri en 2 mánuðir."**
> **Heimild um leiðsluna:** `docs/fable_prep/RENT_MODEL_CARD.md` (`rent_v1`, `rent_anchor_v2_herbergi_fm`, `rent_conformal_v2_tegund`).
> **Eðli lotunnar:** 100 % read-only sókn út á við + read-only SELECT á Supabase. **Engin skrif** í `predictions_rent_staging` / `feature_attributions_rent_staging`, engin endurskorun keyrð, ekkert flippað. Þetta skjal er eina skrif lotunnar (ó-committað við HALT).
> **Ferill:** könnun (§1–4) → HALT → **dómur eiganda 2026-07-18 (§5, liðir A/B/C)** → liður C keyrður (§8) → bókun (§9).
> **Niðurstaða:** ferskara akkeri er ekki til; skilyrði 4 endurskilgreint og **stenst**; endurgerðarpróf á úrtaki **PASS (0 frávik)**. Full endurskorun var **ekki** keyrð (núll-aðgerð, §4) og ekkert skrifað í gagnagrunn.

---

## 1. Það sem var mælt (allt sótt 2026-07-18, UTC)

| Heimild | Slóð | Staða | Útgáfudags (Last-Modified) | Nýjasti gagnamánuður |
|---|---|---|---|---|
| **Leiguverðsjá-CSV** | `hms-web.cdn.prismic.io/hms-web/aik20weQX7-eXI8z_Gogn_til_nidurhals_leiguverdsja.csv` | 200 OK, 219.303 bæti | **2026-06-10** | **2026-05** |
| **Leiguvísitala** | OCI `…/public_data_for_download/o/leiguvisitala.csv` | 200 OK, 1.142 bæti | **2026-07-15** | **2026-05** (=129,3) |
| **Leiguskrá (þinglýst)** | OCI `…/o/leiguskra.csv` | 200 OK, 30.126.573 bæti | **2024-07-25** | 2024-03 *(frosin — sbr. blað §1a)* |

**Lykilmæling:** leiguverðsjár-skráin sem sótt var í dag er **bæti-fyrir-bæti sama skrá** og sú sem akkerið var byggt á 2026-06-29:

```
á disk (sótt 2026-06-29):  219.303 bæti  sha256 0de8a38830ead8d7…
sótt af neti  2026-07-18:  219.303 bæti  sha256 0de8a38830ead8d7…
identical = True
```

Þekja skrárinnar: `DAGSETNING` 2024-01-01 → **2026-05-01**, 29 mánuðir, 2.254 raðir, 8 dálkar, latin-1.

Leiguvísitalan er ný útgáfa (37 → 38 raðir frá 29.06) en **röðin endar líka í 2026-05**:

```
"UTGAFUDAGUR","AR","MANUDUR","VISITALA"
"2026-07-15",2026," 03",127.9
"2026-07-15",2026," 04",128.8
"2026-07-15",2026," 05",129.3
```

Þ.e. HMS gaf út 15.07 **án** þess að bæta við 2026-06.

---

## 2. Nýtt áhættufinn — leiguverðsjár-niðurhalið er horfið af hms.is

Skráin sjálf svarar enn á sinni óbreytanlegu prismic-slóð, en **hlekkurinn á hana finnst hvergi lengur á vefnum.**

Aðferð (uppgötvunarleit, ekki ágiskun):

1. Lendingarsíða `hms.is/gogn-og-maelabord/maelabordleiguskra/leiguverdsja` sótt (200, 177.653 bæti) — **0 hlekkir á `.csv`/`.xlsx`** í HTML né í `__NEXT_DATA__`.
2. Prismic-skjalið sjálft (`ZvqgcRIAAC0AQap4`) sótt beint af API — inniheldur **enga** miðils-/skráartengingu. `last_publication_date` **2026-07-01T09:43:12Z** (skjalið var endurbirt eftir að við sóttum skrána 29.06).
3. **Heildarsópun á öllu Prismic-safni hms.is** (master ref `alo4QBEAACcA8T4W`, 34 síður × 100 = 3.339 skjöl): 143 einstakar `.csv`/`.xlsx`-slóðir alls, **engin þeirra leiguverðsjá**. Til samanburðar fundust bæði `leiguskra.csv` og `leiguvisitala.csv` réttilega í sópuninni — aðferðin virkar.
4. OCI-fatan: skráalisti ekki opinn (404); beinar nafnaprófanir `leiguverdsja.csv`, `Gogn_til_nidurhals_leiguverdsja.csv`, `leiguverdsja_gogn.csv`, `markadsleiga.csv`, `leiguverdsja.xlsx` — **allar 404**.

**Túlkun (varfærin):** við vitum með vissu að (a) engin ný útgáfa er til og (b) hlekkurinn er farinn af síðunni sem var endurbirt 01.07. Við vitum **ekki** hvort það er varanleg afturköllun eða tímabundið rót í endurbirtingu. Hvort tveggja snertir **vaktarrás #1** blaðsins („leiguverðsjá mánaðarlega") beint: sú rás byggir á bulk-CSV sem stendur núna á einni óbreytanlegri, ótengdri slóð.

---

## 3. Aldursmat akkerisins gegn skilyrði 4

Núverandi akkeri (`data/processed/rent_calibration_config.json`, ritað 2026-06-30):

```
version                   rent_anchor_v2_herbergi_fm
generated_for_valuation_ym  2026-05
valuation_window          2026-03-01, 2026-04-01, 2026-05-01
k_global                  1.103054
```

Akkerið er **þegar á nýjasta birta mánuði**. Aldur fer eftir mælikvarða — báðir gefnir hreint, engin ein tala valin fyrir eigandann:

| Mælikvarði | Reikningur | Aldur í dag (2026-07-18) | Gegn „≤ 2 mán" |
|---|---|---|---|
| **Útgáfudagur skrárinnar** | 2026-06-10 → 2026-07-18 | **1 mán 8 d** | **STENST** |
| **Endi matsgluggans** | 2026-05-31 → 2026-07-18 | **1 mán 18 d** | **STENST** |
| **Gagnamánuður (val-ym)** | 2026-05 → 2026-07 | **2 mánuðir** | **Á MÖRKUM** |
| **Upphaf matsgluggans** | 2026-03-01 → 2026-07-18 | 4 mán 17 d | fellur *(en glugginn er 3-mán meðaltal að hönnun — ekki réttur mælikvarði)* |

**Hlutlægt:** skilyrðið fellur ekki í dag á neinum af þeim þremur mælikvörðum sem eðlilegt er að nota. En það er **á mörkum** og **fellur fyrirsjáanlega 1. ágúst** á gagnamánaðar-mælikvarðanum ef HMS birtir ekki 2026-06 — og útgáfutaktinn er þegar farinn að skrika (2026-05-gögn birt 10.06; 2026-06-gögn hefðu átt að birtast ~10.07; engin birting, og hlekkurinn horfinn 01.07).

---

## 4. Af hverju skrefi 3 var ekki hleypt af stað

Endurskorun (skref 3) er **stærðfræðilega núll-aðgerð** við þessar aðstæður:

- Akkerið er fall af leiguverðsjár-skránni. Skráin er bæti-identísk. → `rent_calibration_config.json` yrði identískt (HFAC + k óbreytt).
- Frosna módelið (`rent_v1` @2023) og conformal-leiðréttingarnar eru óbreyttar.
- Skorunar-universið og `predicted_at=2026-05-01` eru óbreytt.

Endurskorun myndi því skrifa **158.314 + 1.583.140 raðir** yfir sjálfar sig með sömu gildum. Það gefur enga nýja mælingu fyrir skref 4 (cov80, PI-breidd og sneiðadreifing yrðu tölulega óbreytt frá smíðinni: cov80 80,55 % / cov95 94,99 %, PI-breidd 38,2 %/77,1 %), en kostar fulla endurritun á staging og felur í sér skrif-áhættu án ávinnings.

Rowcount-hliðið sem skref 3 átti að verja var þess í stað **staðfest read-only**:

| Tafla | Raðir í dag | Vænt (RENT_MODEL_CARD §9) | Staða |
|---|---:|---:|---|
| `predictions_rent` (live) | **0** | 0 | ✅ óflippað |
| `predictions_rent_staging` | **158.314** | 158.314 | ✅ |
| `feature_attributions_rent_staging` | **1.583.140** | ~1.583.140 | ✅ |

`max(predicted_at)` í staging = **2026-05-01** — í samræmi við akkerið.

---

## 5. DÓMUR EIGANDA (2026-07-18) — liðir A/B/C

HALT-ið lagði þrjár ákvarðanir fyrir eigandann. Allar afgreiddar 2026-07-18.

### A — Skilyrði 4 endurskilgreint (A2 + A3)

Skilyrði 4 í dómi cc13 („anchor aldrei eldri en 2 mánuðir") er **breytt** í:

> **„Akkerið skal aldrei vera eldra en nýjasta BIRTA útgáfa viðkomandi heimildar, og aldrei meira en 4 mánuðir frá enda matsglugga (hörð vörn)."**

**Rök eigandans:** *útgáfutöf HMS er ekki okkar dagatal.* Upphaflega skilyrðið mældi okkur gegn almanaki sem við stjórnum ekki — HMS birtir leiguverðsjá með ~1–2 mánaða innbyggðri töf, svo 2-mánaða reglan var sjálfkrafa fallin um hver mánaðamót án þess að nokkuð væri að leiðslunni okkar. Nýja skilyrðið er tvíþætt af ásettu ráði: **fyrri liðurinn** (nýjasta birta útgáfa) mælir það eina sem er á okkar valdi — að við séum ekki á eftir heimildinni; **seinni liðurinn** (4 mán hörð vörn) heldur eftir raunverulegri stöðvunarreglu ef HMS hættir að birta, svo breytingin sé rýmkun á mælikvarða en ekki afnám vörslunnar.

**Beiting á núverandi stöðu:** akkerið er á `generated_for_valuation_ym = 2026-05`, sem **ER** nýjasta birta útgáfa (§1). Endir matsglugga 2026-05-31 → 2026-07-18 = **1 mán 18 d**, vel innan 4-mán varnarinnar. → **Skilyrði 4 STENST.**

**Afleiðing fyrir tímalínu:** anchor-refresh er þar með afgreiddur fyrir lotu #1 (engin aðgerð þörf, akkerið er ferskt að nýju skilgreiningunni). **Lota #2 (T5-þrep + `fj_herbergi`-stefna) er akkeris-óháð og fær sér-prompt frá arkitekt.**

### B — Vaktarrás #1 útfærist á skrána, ekki hlekkinn

Bókað (útfærslan sjálf tilheyrir lotu #4-vaktarpípunni; hér aðeins skilgreiningin):

- **Vikuleg hash-vöktun** á óbreytanlegu prismic-slóðinni + leiguvísitölu-slóðinni á OCI.
- **Hash breytist** → ferskt akkeri fáanlegt → **refresh-trigger** (ræsir anchor-refresh-lotu).
- **Slóðin hættir að svara** → **HALT-viðvörun** (heimildin dottin út, ekki bara gömul).

**Rökin:** rásin má ekki hanga á hlekk sem HMS getur endurbirt í burtu — eins og gerðist 2026-07-01 (§2). Skráin sjálf á óbreytanlegri slóð er stöðugri mælipunktur en vefsíðan sem vísar á hana.

**Bókuð áhætta:** hvarf leiguverðsjár-hlekksins af hms.is (staðfest 2026-07-18, sópun á öllum 3.339 Prismic-skjölum) stendur sem **opin áhætta** á vaktarrás #1. Óupplýst hvort um varanlega afturköllun eða endurbirtingar-rót er að ræða.

### C — Endurgerðarpróf á úrtaki: keyrt, **PASS**

Sjá §8.

---

## 6. Ask-premían — EKKI mæld í þessari lotu (og af hverju)

Skref 4 bað um ask-premíu-mælingu (viðmið 1,15–1,20) gegn virkum leiguauglýsingum. Hún var **ekki keyrð**, því hún átti að vera mæld *gegn endurskoruðu módeli* og engin endurskorun fór fram. Mælingin frá cc13 stendur óhögguð sem síðasta gildi (RVK 1/2/3 herb: 1,16/1,17/1,19; Capital_sub 2/3 herb: 1,20/1,15).

**Aðgreiningin sem blaðið krefst stendur óbreytt og var ekki hnikað:** ask-premían er **flæðis-vísir á auglýstu verði** og má **aldrei** blandast inn í samningsakkerið (leiguverðsjá = samningastofn). Ekkert í þessari lotu snerti hvorugt.

---

## 7. Staða reglna eftir lotuna

- Agent-reglan **„aldrei leigumat" stendur ÓSNERT** — engin breyting gerð á `lib/agent-prompt.js` né neinu UI.
- `predictions_rent` = 0. Ekkert flippað, engin birting.
- Engin migration keyrð, engin tafla búin til eða breytt.
- Skilyrði blaðsins 1–3 (T5-lag, loud labeling, vaktarrásir) eru óhreyfð verk lotu #2/#3.

---

## 8. Liður C — endurgerðarpróf á úrtaki (keyrt 2026-07-18T09:46Z)

**Umboð:** dómur §5-C — endurskora 1.000 raðir í CSV, **ekkert DB-skrif**, diff gegn staging. Vænt 0 frávik; frávik → HALT.

**Aðferð:** skriftan endurgerir leiðsluna nákvæmlega eins og `score_rent_universe.py` — frosið `rent_v1` fitt á sömu 111.818 raðir (seed 42, 800 lotur), sama HFAC(h) × `k_global=1.103054`, sama conformal-stigveldi `cc|region|tegund (Einbýli) → cc|region → cc → global`, sama `predicted_at=2026-05-01`. Úrtakið er **deterministískt**: hver 158. röð í `fastnum`-röð úr skorunar-universinu (158.314 → 1.000). Skorun er raða-óháð (engin þver-raða staða), svo úrtaks-skorun er gild endurgerð. DB-lotan var `readonly=True`.

**Niðurstaða — 1.000/1.000 raðir pöruðust, 11 dálkar bornir saman:**

| Dálkur | Frávik | | Dálkur | Frávik |
|---|---:|---|---|---:|
| `pred_mean` | **0** | | `model_group` | **0** |
| `pred_median` | **0** | | `segment` | **0** |
| `pred_lo80` | **0** | | `model_version` | **0** |
| `pred_hi80` | **0** | | `calibration_version` | **0** |
| `pred_lo95` | **0** | | `predicted_at` | **0** |
| `pred_hi95` | **0** | | raðir vantar í staging | **0** |

**HEILDARFRÁVIK: 0 → PASS.** Bæti-identísk endurgerð staðfest.

**Hvað þetta sannar (og hvað ekki):** það sannar að leiðslan er **endurgerðanleg** — sömu heimildir + sama kóði gefa sömu tölu, og að `predictions_rent_staging` er raunverulega afurð þeirrar leiðslu (ekkert rek milli 2026-07-01 og í dag). Það er sama eðlis og *rebuild-parity == DB-parity* krafan í flip-hliðinu (RENT_MODEL_CARD §9, sbr. sölu-parity DECISIONS 2026-06-30) — en það er **úrtakspróf (0,63 %)**, ekki fullt parity-hlið. Fullt hlið á 158.314 röðum tilheyrir lotu #3.

**Engin skrif:** CSV-afurðin liggur í scratchpad-möppu lotunnar, ekki í `precompute/exports/` né í repo. `predictions_rent_staging` og `feature_attributions_rent_staging` óhreyfð.

---

## 9. Staða eftir dóm

| Liður | Staða |
|---|---|
| Skilyrði 4 (blað §5.4) | **Endurskilgreint** (§5-A); núverandi akkeri **STENST** |
| Anchor-refresh, lota #1 | **AFGREIDDUR** — engin aðgerð þörf, akkerið er nýjasta birta útgáfa |
| Vaktarrás #1 | **Skilgreind** (§5-B); útfærsla bíður lotu #4 |
| Hvarf hms.is-hlekksins | **Bókað sem opin áhætta** |
| Endurgerðarpróf (C) | **PASS**, 0 frávik af 11.000 samanburðum |
| `predictions_rent` (live) | **0** — óflippað, óbreytt |
| Agent-reglan „aldrei leigumat" | **ÓSNERT** |
| Næsta skref | **Lota #2** (T5-þrep + `fj_herbergi`-stefna), akkeris-óháð, sér-prompt frá arkitekt |

---

*Skjalfest af cc19 (Claude Opus 4.8). Read-only lota að öllu leyti — þetta skjal er eina skrifið í repo; ekkert DB-skrif, engin migration, ekkert flipp.*
