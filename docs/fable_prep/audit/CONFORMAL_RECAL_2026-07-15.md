# CONFORMAL_RECAL — endurkvörðun vissubila: holdout-mæling + ákvörðunarblað

> **Status: READ-ONLY greining, HALT — engin breyting keyrð.** cc4-lota 2026-07-15T23:14Z
> (verkbeiðni: F.3-liður 2 úr VERDMAT_FLIPI_2-auditnum, endurstilltur eftir forsendu-leiðréttingu).
> Skript: `docs/fable_prep/prototypes/` — `conformal_recal_holdout.py`,
> `conformal_recal_extra.py`; sellu-aggregat `cell_q80_compare.csv` sama stað.
> Raðgagnaskráin `holdout_rows.csv` (1.488 raðir, per-eign verð+spár+flögg úr
> prod-DB) er VILJANDI EKKI í git (public repo) — hún liggur á
> `docs/fable_prep/prototypes/holdout_rows.csv` á disk og endurskapast
> deterministically með holdout-skriptunni. Allar tölur hér eru úr þeim keyrslum.
>
> **ÚRSKURÐUR (Danni 2026-07-15, eftir HALT):** retrain-hringur GO sem vegvísaliður A
> (A-lotuprompt skrifast á grunni þessa blaðs); interim-blend (c) EKKI virkjað strax —
> endurmetið við tímamat fyrsta retrain-fasa; mánaðarlega þekju-vaktin (§8) SAMÞYKKT
> sem fastur liður retrain-forskriftar; heiðarleikapakki (§7-fletirnir) í texta-HALT.
> Skráð í DECISIONS 2026-07-15.

---

## 0. Forsendu-leiðrétting (skráð, svo næsta lota erfi hana ekki)

Fable-audit F.3 og MODEL_CARD_iter4 §5/§8 sögðu conformal-artifaktið „til en EKKI tengt
í prod". **STALE:** conformal + A/B/C/D flippaði LIVE **2026-07-02** (DECISIONS-færsla
„Conformal PI (iter4_conformal_v1) + width-based A/B/C/D confidence-grade FLIPPAÐ LIVE");
lifandi `predictions` er 100% `iter4_conformal_v1+segcal_fb` (sannreynt í DB þessari lotu).
MODEL_CARD er leiðrétt (þessi lota). **Fable-audit-línan sjálf er í prod-repoinu sem cc2
heldur — sú leiðrétting BÍÐUR cc2-push** (ein lína í F.3 með vísun í DECISIONS 02.07).

Spurning lotunnar varð því: **heldur 2025-kvörðunin enn 80% á sölum eftir
þjálfunar-cutoff (2026-04-20)?** Svarið er nei — sjá §2.

## 1. Holdout-smíð (2.1) — lekaleysi + síubókhald

Sölur með `thinglystdags > 2026-04-20` úr `public.sales_history` (ferskt til 14.07).
Lekaleysi: þjálfun/kvörðun artifacts sá ekkert þinglýst eftir 20.04 (boosters + conformal
byggð 21.04); predictions-endurreikningur 01.07 breytir ekki punktspánni (frosið líkan).
Samanburðargrunnur: `kaupverd_real` er nominal-ígildi @ 2026-07 (mælt: hlutfall við
nominal → 1,0000 í júlí) — sami grunnur og `real_pred_*` dálkarnir.

| Sía | felldar | eftir |
|---|---:|---:|
| post-cutoff raðir alls | — | 3.102 |
| ×1000-próba (sala > 20 mrd kr) | **0** | 3.102 |
| onothaefur ≠ 0 (skyldusía, DECISIONS l.209) | 848 | 2.254 |
| is_suspect_comparable (þ.m.t. kv_extreme/sentinel — ×1000-ættin) | 664 | 1.590 |
| engin prediction-röð (D3-held, nýtt o.fl.) | 102 | 1.488 |
| **HOLDOUT H** | | **1.488** |

Kaupskrár-raðirnar þrjár ×1000 eru **ekki í glugganum** (0 raðir yfir 20 mrd) og
kv_extreme-flögg síuð að auki. Viðmiðunarlína með suspects MEÐ (aðeins onothaefur-sía,
n=1.850): cov80 70,3% — aðal-niðurstaðan versnar sem sagt ekki við suspect-síunina.

## 2. LIVE bilin á fersku holdouti (2.2′) — undirdekkun er raunveruleg og almenn

**Heild H (n=1.488): cov80 = 72,2% (markmið 80) · cov95 = 91,6% (markmið 95) · med rel80 = 0,215.**
Tvíkosta-óvissa á n=1.488 er ±1,0 pp → 72,2% er ~7,5σ undir markmiði. Ekki suð.
Við flippið 02.07 mældist held-þekjan 79,0% — **rek á ~3 mánuðum eftir cutoff.**

**Greining á rótinni: BREIDD, ekki bjagi.** Miðgildis-residúall −1,1% log (meðaltal +0,5%),
brot samhverf: 14,9% undir lo80 / 12,9% yfir hi80. Punktspáin stendur (medAPE ~6,5%);
dreifni residúala hefur breikkað umfram kvörðunina. Samhverf conformal-breikkun er því
rétta verkfærið — EKKI þrenging: **þrengingar-svigrúmið sem verkbeiðnin vonaðist eftir er
ekki til í heildina; bilin eru nú þegar of þröng.**

**Per flokkur (verri villan — ofseld vissa — er í A):**

| flokkur | n | cov80 | cov95 | med rel80 | medAPE | mat |
|---|---:|---:|---:|---:|---:|---|
| A | 697 | **69,4%** | 91,4% | 0,180 | 6,1% | UNDIR (marktækt, ~7σ) |
| B | 496 | **74,4%** | 90,7% | 0,250 | 6,8% | UNDIR (marktækt) |
| C | 241 | **73,0%** | 93,8% | 0,386 | 12,4% | UNDIR (marktækt) |
| D | 54 | 85,2% | 92,6% | 0,871 | 13,5% | innan óvissu (n<60) |

**Per sella (stærstu eftir holdout-n; tvíkosta-flagg: UNDIR = cov < 0,80 − 2σ, YFIR > 0,88):**

| sella | n | cov80 | med rel80 | flagg |
|---|---:|---:|---:|---|
| APT_FLOOR\|Capital_sub | 300 | **64,3%** | 0,189 | UNDIR — versta stóra sellan (pivot-sellan úr G5) |
| APT_FLOOR\|RVK_core | 288 | 76,4% | 0,250 | innan 2σ |
| APT_STANDARD\|RVK_core | 246 | **73,6%** | 0,180 | UNDIR |
| APT_FLOOR\|Country | 187 | **67,9%** | 0,386 | UNDIR |
| APT_STANDARD\|Capital_sub | 143 | **71,3%** | 0,171 | UNDIR |
| APT_STANDARD\|Country | 49 | 53,1% | 0,246 | UNDIR — en n<50, fyrirvari (sbr. sömu sellu í 04/2026-auditi: suð-grunur þá, kerfisbundið nú) |
| SUMMERHOUSE\|Country | 45 | 86,7% | 0,842 | n<50 (segcal-fallback, D) |
| SFH_DETACHED\|Country | 41 | **92,7%** | 0,607 | **YFIR — eina þrengingar-vísbendingin, n<50 fyrirvari** |
| APT_BASEMENT\|RVK_core | 31 | 80,6% | 0,209 | n<50 |
| ROW_HOUSE\|Capital_sub | 29 | 82,8% | 0,215 | n<50 |

RVK_core-íbúðir sér (fyrirmæli): APT_STANDARD 73,6% (n=246, marktækt undir),
APT_FLOOR 76,4% (n=288, innan 2σ) — kjarninn lekur líka, hóflegar en Capital_sub.
Per mánuð: 04: 78,2% → 05: 70,2% → 06: 71,0% → 07: 74,9% — apríl (næst cutoff) best,
samræmist öldrunar-túlkun.

## 3. Endurkvörðunar-útgáfur (2.3′) — mældar á sama E-setti

Aðferð: nákvæm eftirmynd `conformal_calibration.py` (MIN_N=30, empírísk kvantíl á
|log-resid|, cascade cc|region → cc → [prod-fallback: óbreytt lifandi bil]). Tímaskipting
H-main (n=1.436) á miðgildis-dagsetningu **2026-06-08**: calib-gluggi C (n=737) / mat-sett
E (n=699) — endurkvörðun aldrei metin á eigin kvörðunarröðum. Allar útgáfur metnar á SAMA E.

| útgáfa | cov80 á E | cov95 á E | med rel80 | alheims-flokkar A/B/C/D | ΔA |
|---|---:|---:|---:|---|---:|
| **LIVE (viðmið)** | 72,0% | 90,3% | 0,189 | 36,1 / 35,3 / 21,5 / 7,1% | — |
| **(a) pool 2025-test + C** | 72,7% | 90,8% | 0,193 | 36,1 / 35,3 / 21,5 / 7,1% (óbreytt) | 0,0 pp |
| **(b) hreinn C-gluggi (~7 vikur)** | **78,3%** | 91,6% | 0,250 | **0,8** / 62,9 / 29,2 / 7,1% | **−35,3 pp** |
| **(c) blend α=0,5 live+C (G5-hemils-form)** | 75,1% | 91,1% | 0,219 | 18,1 / 49,5 / 25,2 / 7,1% | −18,0 pp |

- **(a) er áhrifalaus:** 8.575 gamlar 2025-raðir kaffæra ~700 nýjar — kvantílarnir hreyfast
  varla (q80 APT_FLOOR|Capital_sub 0,0942→0,0965). Nær hvorki þekju né neinu.
- **(b) nær þekju næst (78,3%) en er G5-brot:** A-hlutdeild hrynur 36,1→0,8%. Hluti
  hreyfingarinnar er RAUNVERULEGT merki (allar sellur breikka samstíga = öldrun, ekki suð)
  en ofan á liggur 7-vikna-glugga-suð á þunnum sellum (APT_STANDARD|Country q80
  0,1229→0,2314 á n_cal=30). G5-ákvörðunin (04.07) hafnaði einmitt 3-mán glugga sem
  flokka-óstöðugum; |ΔA| ≤ 5 pp mælikvarðinn brotinn sjöfalt.
- **(c) mildar hvort tveggja en leysir hvorugt:** þekja enn 5 pp undir, ΔA samt −18 pp,
  og G5 skráði yfirskots-fyrirvara á blöndun; virkjun hennar er skilgreind sem sér-ákvörðun.

**Engin endurkvörðunar-útgáfa nær bæði þekju ≥80% og flokka-stöðugleika.** Það er ekki
útfærslugalli heldur eðli málsins: frosið líkan + 3 mán öldrun = raunveruleg
nákvæmnis-rýrnun sem heiðarleg bil VERÐA að sýna — spurningin er aðeins hvort hún birtist
sem breiðari bil á gömlu punktspánni eða sem ferskt líkan með þéttari residúöl.

## 4. Tillaga (b-liður blaðsins)

**AÐALTILLAGA: EKKI stakstæð endurkvörðun — keyra næsta retrain-hring (RETRAIN_RUNBOOK)
með 6-mán OOS conformal-kvörðun skv. læstum G5-staðli, sem fyrsta tækifæri.**
Rök: (i) eina leiðin sem nær þekju OG stöðugleika samtímis — 6-mán OOS gluggi þéttir
sellu-kvantíla ~2,2× (G5-mæling) og ferskt líkan endurheimtir hluta nákvæmninnar
(retrain-ávinningur −0,56 pp MAPE, nettó ~−0,3 pp eftir öldrunarkostnað OOS-gluggans);
(ii) EIN flokka-umskipti fyrir notendur í stað tveggja (interim-kvörðun + retrain skömmu
síðar); (iii) dress rehearsal er þegar keyrð — vélbúnaðurinn er til.

**EF retrain-hringur dregst umfram ~4–6 vikur:** (c) blend α=0,5 sem interim með
formlegri virkjun G5-neyðarhemilsins (sér-ákvörðun + round-to-round A-vakt eins og G5
áskilur). Betri en aðgerðaleysi (72→75%) og hálfa leið að heiðarlegri flokkun, en skilur
þekju eftir undir markmiði — TÍMABUNDIN ráðstöfun, ekki lausn.

**HAFNAÐ:** (a) — mælt áhrifalaus. (b) stakstæð — G5-brot + glugga-suð á þunnum sellum.
Óbreytt ástand án tímamarka — 72% þekja á 80%-loforði er ofseld vissa, verri villan.

## 5. Áhrif á flokka A–D og skýringar (c-liður)

- **Þröskuldar A<0,20 / B<0,36 HALDAST.** Vandinn er að breiddirnar eru of þröngar, ekki
  að mörkin séu röng; að hliðra mörkum til að verja A-hlutdeild væri að endurskilgreina
  merkinguna til að fela rýrnun. Eftir retrain+6-mán kvörðun endurreiknast sellu→flokkur
  varpanirnar náttúrulega (búast má við A-hlutdeild milli live 36% og hreinu 0,8% —
  hvar nákvæmlega er mæliniðurstaða hringsins, gate G5 vaktar |ΔA|).
- **FLOKKUR_SKYRING-textarnir (skyringar.ts) standast óbreyttir** — þeir lýsa breiddar-
  þrepum, ekki tölugildum. ATH: fullyrðingin í A/B („hefur reynst áreiðanlegt") er í dag
  hæpin (A cov80 69,4%) — enn ein ástæða að laga breiddirnar frekar en textann.
- SFH_DETACHED|Country (92,7% þekja, n=41) er eina þrengingar-vísbendingin — 6-mán
  glugginn sker úr um hana með alvöru n; engin sér-aðgerð núna.

## 6. Útfærsluleið + rollback (d-liður)

Sama farvegur og 02.07-flippið (sannreyndur): rebuild → CSV → staging → parity-diff
(mean/median 0 breyttar raðir = harða hliðið; aðeins PI/grade-dálkar hreyfast við
kvörðunarbreytingu) → atómískt swap. Rollback: allt version-stimplað
(`calibration_version`); gamla artifactið `iter4_conformal_v1` + segcal-config liggja
óhreyfð á D:\ — endurkeyrsla rebuild með fyrra artifacti endurskapar núverandi bil
nákvæmlega. Retrain-leiðin ber að auki sín G1–G5 hlið + sér-go (spábreytingar).

## 7. Birting notendum (e-liður)

Bil BREIKKA á meirihluta lifandi eigna og hluti A-eigna fer í B — sýnileg breyting.
Þarf: (i) changelog-línu á /adferdafraedi (prod-repo — EFTIR cc2-push), (ii) íhuga að
/markadur/modelstada sýni MÆLDA lifandi þekju (72,2% núna) í stað þess að vitna í
artifact-þekjuna 79,1% frá apríl — heiðarleiki óháð hvaða leið verður valin.

## 8. Taktur framvegis (nýr liður skv. go-fyrirmælum)

**Kvörðunin fylgi retrain-taktinum (RETRAIN_CADENCE) — EKKI sjálfstæð mánaðarleg/
ársfjórðungsleg artifact-skipti** (mánaðarleg endurkvörðun = mánaðarlegt flokkaflökt,
brýtur G5-markmiðið). Í staðinn: **mánaðarleg ÞEKJU-VAKT** — þessi holdout-mæling er nú
skriptuð og ódýr (~30 sek); keyrist eftir hverja mánaðar-predictions-endurreikningu.
Viðbragðsþröskuldur: cov80 (rúllandi 3-mán holdout, n≳1.400, 2σ≈±2 pp) **< 76% tvo mánuði
í röð → flýta retrain-hring** (76 = 80 − 2σ með borði). Rek 79→72 á ~3 mán bendir til að
náttúrulegur taktur hringsins sé ~ársfjórðungslegur — það er mæling, ekki ágiskun.

## 9. Mælifyrirvarar

(i) Söluverð fært á júlí-grunn með CPI (verðtrygging), ekki markaðsvísitölu — bjaga-tékkið
(±1% miðgildi) sýnir að þetta skekkir ekki niðurstöðuna efnislega. (ii) Holdout er
sölu-vigtað (seldar eignir ≠ alheimurinn). (iii) E-sett n=699 → sellu-línur þunnar,
n<50-fyrirvarar merktir. (iv) Suspect-síað skv. fyrirmælum; suspects-MEÐ línan (70,3%)
sýnir að valið mildar ekki dóminn. (v) C/E-skipting tímaröðuð (calib eldri en mat) —
7-vikna kvörðunargluggi (b)-útgáfu er minna en G5-staðallinn 6 mán; það er hluti af
höfnunarrökunum, ekki galli á mælingunni.

— cc4, 2026-07-15 · HALT: engin tenging/kvörðun keyrð; retrain-hringur og/eða interim-blend
eru sér-go; fable-audit F.3 leiðrétting bíður cc2-push.
