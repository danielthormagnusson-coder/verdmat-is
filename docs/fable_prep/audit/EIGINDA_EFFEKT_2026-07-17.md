# EIGINDA_EFFEKT — endurmæling eiginda-effekta á iter4r-holdouti: þekja + residúal-greining + ákvörðunarblað

> **Status: READ-ONLY greining — SAMÞYKKT af eiganda 2026-07-17, cc12 LOKIÐ.**
> cc12-lota 2026-07-17T17:58Z (verkbeiðni: forsenda vegvísaliðar B; spurningin úr
> fable-audit F.4 í VERDMAT_FLIPI_2: breytir fasa-A eigindastofninn 0,83%-mælingunni?).
> Aðferðin er sniðin að CONFORMAL_RECAL_2026-07-15.md (holdout-sniðmátið); mæligrunnur
> er **iter4r_20260716** (lifandi líkanið): `D:\training_data_v2.pkl` (146.499 raðir,
> data_end 2026-07-15) + `D:\model_artifacts\iter4r_20260716\iter4r_20260716_holdout_rows.csv`
> (holdout H=848 eftir onothaefur- og suspect-síur, sama síubókhald og holdout-skýrslan).
> Eigindastofninn lesinn read-only úr `public.property_attributes` + `properties.fjherb`
> um poolerinn (readonly-session); join lókalt í pandas. Engin raðgögn í þessari skrá
> (aggregat eingöngu). Vinnuskript lotunnar voru í session-scratchpad; aðferðin er
> lýst hér að fullu til endurkeyrslu.

---

## 0. Spurningin (F.4-samhengið)

Gamla mælingin (MODEL_CARD §3 / DECISIONS l.3520): 133/154 features extraction-afleidd,
samanlagt gain **0,83%**, `has_extraction_data` gain 0,0 — mæld á 24% þjálfunarþekju og
ÁN matseiningar-backfillsins úr fable-fasa A (geymsla 4.888 · bílskúr/stæði 64.514 ·
íbúðarrými 47.128 · fjherb 55.596). Spurning: ber nýi stofninn merki sem líkanið missir —
og réttlætir það B-lið (tveggja laga verðmat, leiðréttingarlag birt aðgreint)?

## 1. ÞEKJA á seldum (þjálfunarstofninn, 89.307 distinct fastnum)

| eigindi | seldar n | seldar % | holdout H (845 fastnum) | uppruni |
|---|---:|---:|---:|---|
| herbergi (fjherb/attributes) | 47.796 | **53,5%** | 55,0% | nær allt skraargogn (extraction 35) |
| bilskur_staedi | 35.085 | **39,3%** | 37,4% | skraargogn |
| ibudarrymi_vs_heild | 23.786 | **26,6%** | 23,2% | skraargogn |
| geymsla | 1.958 | 2,2% | 2,1% | skraargogn (aðeins jákvæðar raðir, sbr. A.2) |
| badherbergi | 35 | 0,04% | 0,1% | extraction |
| eldhus_astand / badherbergi_astand | 23 / 13 | **~0%** | 0 | extraction on-demand (~45 eignir alls) |

**Tvíþætt svar við þekju-forsendunni:** hún reyndist RÖNG fyrir skráar-eigindin
(27–54% á seldum — mælanleg) en Í REYND RÉTT fyrir allt extraction-lagið: fasi B er
on-demand per eign, svo ástand/baðherbergi — eigindin með stærstu mögulegu
verð-effektana — hafa enga þekju á seldum og ekkert er þar að mæla.
Ath: **fjherb er EKKI meðal 154 features iter4r**; gamla 24%-extractionið á þar hins
vegar parking_is_garage, storage_*, bathroom-status-raðirnar.

## 2. EFFEKT-MÆLING (residúal-greining á H, n=848)

Residúall = log(sala) − log(spá); + = líkanið VANmetur. Miðgildi per sella með 95%-CI
miðgildis (binomial order-statistic). **Viðmið alls H: med resid −0,0195,
CI95 [−0,0245, −0,0111]** — almenn ~2% ofspá (framvirka rekið úr holdout-skýrslunni)
liggur undir öllum sellum; deltan gegn viðmiði/mótflokki er mælikvarðinn.

| merki | sellur | Δ | mat |
|---|---|---:|---|
| **Bílskúr** (gerd=bilskur n=191: −0,0157 vs engin röð n=531: −0,0199; innan APT_STANDARD n=42: −0,0069) | vanspá-átt | **+0,4 → +1,3 pp** | ÓMARKTÆKT — öll CI-bil skarast |
| **Herbergjaþéttleiki** (herb/m² tercile; þétt n=156: −0,0082 vs gisið n=156: −0,0237) | einhalla, rétt átt | **≈ +1,5 pp** | jaðar; heldur innan APT_FLOOR, ekki innan APT_STANDARD |
| **Íbúðarhlutfall** (lágt = mikið aukarými n=66: −0,0417 vs hátt n=66: −0,0166) | aukarými OFmetið | **≈ −2,5 pp** | stærsti og skynsamlegasti effektinn, jaðar-marktækur (CI [−0,0675,−0,0019] vs [−0,0284,+0,0199]) |
| fjherb=2–3 (−0,023, marktækt) vs fjherb=4 (−0,001) | | ≈ +2 pp | stærðar-samblöndun; sama merki og þéttleikinn |
| Geymsla (n=18) | | — | ómælanlegt |

**Fyrirvarar (n-dempun):** ein tímaskipting; n=848 alls, 40–190 per sellu; rek-grunnlínan
blandast í öll miðgildi; skráar-fjarvera ≠ nei (samanburðarhópur bílskúrs inniheldur
eignir með óskráðan bílskúr — deltan er því NEÐRI mörk). JSON-lykill bílskúrs-raða er
`gerd` (ekki `tegund`) — skráð svo næsta mæling detti ekki í sömu gryfju.

## 3. DÓMUR

1. **B-liður (birt leiðréttingarlag ofan á grunnmat): SEINNA/NEI að sinni.**
   Mældu merkin eru ≤2,5% að miðgildi, jaðar-marktæk, minni en medAPE líkansins (5,4%)
   og af sömu stærðargráðu og rek-grunnlínan. Birt leiðréttingarlag byggt á þessu
   myndi bæta við suði af sömu stærðargráðu og merkið sjálft.
2. **Rétti farvegurinn: skráar-eigindin sem FEATURES í næsta retrain-hring** —
   fjherb (+ þéttleiki), bilskur_staedi (gerd+m²), íbúðarhlutfall, geymslu-flagg.
   LightGBM er NaN-native; 27–54% þekja nothæf án imputation; líkanið kvarðar
   effektinn sjálft í stað handstuðla. Þetta er iter5-liður c (GO/NO-GO hliðið
   sem F.4 skilgreindi).
3. **0,83%-dómurinn stendur óhaggaður fyrir extraction-lagið** — ekki af því að
   ástand skipti ekki máli heldur af því að þekjan á seldum er enn ~0.

## 4. ÚRSKURÐUR EIGANDA (Danni 2026-07-17) — blaðið samþykkt í heild

1. **B-liður = SEINNA.** Endurvakningarhliðið er skilyrðin þrjú: (i) extraction-backfill
   yfir seldar eignir með auglýsingar, (ii) mældur effekt >3% með alvöru n á
   ástands-eigindum, (iii) endurmæling EFTIR að skráar-featurin eru komin inn í retrain
   — ef residúal-merkið lifir það af, þá fyrst á sér-lag rétt á sér.
2. **GO á skráar-featurin inn í NÆSTA retrain-hring** — sem SAMANBURÐARKEYRSLA við
   grunnhring skv. cc6-forskrift 1.3 (grunnur fyrst, feature-tilraun við hlið,
   M1–M3 dæmir). Version-nafn verður iter5-ættar skv. nafnareglu ef featurar fara inn.
   Skráist í PLANNING_BACKLOG sem iter5-liður með vísun í þetta blað.
3. Blaðið vistað í audit-hefðinni — read-only lotan skrifar þessa einu skrá + commit,
   ekkert annað.

— cc12, 2026-07-17T17:58Z–LOKIÐ · engin önnur skrif, enginn push í þessari lotu
