# RETRAIN_RUNBOOK — endurþjálfunar-hringur sölumódelsins

> **Staða:** v1, skrifað af Fable-lotu 2026-07-02 samhliða rotnunar-backtestinu
> (`docs/fable_prep/audit/RETRAIN_CADENCE.md`) og DECISIONS-færslunni um cadence +
> trigger. Skrifað svo venjuleg Opus-CC lota geti keyrt hringinn án Fable.
> **Hringurinn endar á mannlegu GO — ekkert skref hér flippar live sjálfkrafa.**

## 0. Hvað hringurinn er og hvenær hann keyrir

Sölumódelið (iter4-arkitektúr) er frosið artifact sem endurkvarðast EKKI með
markaðnum; punktmatið rotnar með aldri þjálfunargagnanna (mælt:
`RETRAIN_CADENCE.md`). Hringurinn keyrir:

1. **Reglubundið** — samkvæmt cadence í DECISIONS (sjá „Endurþjálfunar-cadence"
   færsluna, 2026-07-02): endurþjálfun þannig að þjálfunargagna-aldur fari aldrei
   yfir mörkin sem backtestið setti.
2. **Flýtt (drift-trigger)** — þegar d-panel vöktin (comp-vél / weekly-model-quality)
   rýfur trigger-mörkin úr sömu DECISIONS-færslu. Trigger flýtir hring; hann
   breytir ALDREI módeli sjálfur.

**Skylduskref hvers hrings (ófrávíkjanleg röð):**
retrain → conformal-endurkvörðun (ALLTAF með, aldrei erfð) → parity-gate →
mannlegt GO → flip (staging + DB-parity, júlí-flip mynstrið) → næturkeyrslu-vakt.

## 1. Forsendur (áður en nokkuð keyrir)

- [ ] **Fersk training_data_v2.pkl.** `D:\training_data_v2.pkl` endurbyggð af
  precompute-pípunni á ferskri kaupskrá (sjá `rebuild_training_data`-ferlið;
  kaupskrá-fetch er enn handvirkt gate — staðfestu mtime og hámarks-THINGLYSTDAGS).
  Ef pkl er eldri en ~2 vikur: endurbyggja FYRST.
- [ ] **Canonical-sync í gildi** — pkl byggð EFTIR properties_v2-canonical-fixið
  (DECISIONS 2026-06-30); annars endurtekur 67-útlaga parity-brotið sig.
- [ ] Enginn annar þungur process á vélinni; WU-pása ef keyrslan á að standa yfir
  nótt (sjá reference_power_settings).
- [ ] `D:\model_artifacts\` til (skriftan býr hana til annars).

## 2. Skref 1 — endurþjálfun

```
cd D:\verdmat-is\precompute
python retrain_sales_model.py --version iter4r_<YYYYMMDD>
```

- Þjálfar 12 boostera (main+summer × mean+5 kvantílar), EXACT iter4a-hyperparams
  og features (154, ENGINN FASTEIGNAMAT). Replica-sönnun aðferðarinnar:
  `RETRAIN_CADENCE.md` §1 (endurgerði held MAPE 8,19%/medAPE 5,54% upp á 0,01 pp).
- Split: calib = síðustu 3 mánuðir (conformal + parity, EKKI early-stop), train =
  allt eldra mínus slembið 5% es-holdout (velur aðeins iteration count).
  **Tvö meðvituð frávik frá train_iter4a.py:** (a) heil-árs test-splittið er farið —
  gamla skemað fæddi módel sem var ~16 mán gamalt í gögnum við flip; (b) early-stop
  er á slembi-holdouti en ekki temporal glugga — dress rehearsal 2026-07-02 sýndi
  að es á 3-mán driftuðum glugga stoppar of snemma (best_iter 296 vs ~1900-3000)
  og vanþjálfar (rök + mæling: RETRAIN_CADENCE.md + iter4r_20260702 vs _b
  artifact-logs).
- Úttak: `D:\model_artifacts\<version>\` — skriftan NEITAR að yfirskrifa möppu
  sem er til. Live artifact á `D:\iter4a_*.lgb` er ALDREI snert.
- Keyrslutími: ~10–20 mín (12 boosterar). Keyra detached ef í CC-lotu
  (`Start-Process`, harness drepur bakgrunnsverk ~33 mín).
- **HALT-punktur 1:** skoða `<version>_training_log.txt` — calib-MAPE main á að
  vera á bilinu 6,5–9,5% (heilbrigt); feature-fjöldi 154; engir object-dtype
  árekstrar. Frávik → stoppa, greina, EKKI halda áfram.

## 3. Skref 2 — conformal-endurkvörðun (ALDREI sleppt, ALDREI erfð)

```
python recalibrate_conformal.py --artifact-dir D:\model_artifacts\<version>
```

- Mondrian split-conformal (sama aðferð og `iter4_conformal_v1`:
  `models/conformal_calibration.py`, MIN_N=30, cascade cc|region → cc → global)
  á calib-glugga kandídatsins.
- **Regla:** conformal-breidd er empírísk dreifing residúala ÞESS módels — að erfa
  breidd frá fyrra módeli er ógilt. Backtestið mældi einmitt að þekjan heldur
  aðeins þegar kvörðunin er fersk (RETRAIN_CADENCE.md §3: þekjutapið er
  bias-drifið — miðjan skekkist, breiddin gildir; fersk kvörðun endurmiðjar).
- Innri sannprófun (helmingaskipti calib-gluggans) prentast í log: cov80 á að
  lenda í [74, 86], cov95 í [91, 98,5]. Utan þess → HALT.
- **HALT-punktur 2:** skoða `<version>_conformal_log.txt` + warning-flaggið í
  JSON (`internal_split_verification.warning`).

## 4. Skref 3 — parity-gate

```
python parity_check.py --artifact-dir D:\model_artifacts\<version>
```

Ber kandídat vs live (boosterar + conformal-artifact bæði megin) á síðasta
3-mán sölu-glugganum og skrifar `<version>_parity_report.{json,md}` með
GO/NO-GO tillögu.

**Akkeris-leiðrétting (skylda að skilja):** live-boosterar og kandídat eru þjálfaðir
á ólíkum CPI-ankeringum training-pkl-sins (vikulega CPI-vélin endurankrar
`cpi_factor`). parity_check mælir δ̂ = median(pred_cand − pred_live) á in-train
sneið (2023-24, n=3.000) og hliðrar live-spám um +δ̂ fyrir allan samanburð; δ̂ á að
vera ≈ log(cpi[nýtt akkeri]/cpi[gamalt]) (dress rehearsal: δ̂=+2,07% vs CPI-reiknað
+1,81%). Frávik > 1 pp milli δ̂ og CPI-reiknaðs → HALT (annað en akkeri í gangi).
Þetta er sami villuklasinn og VÉL 1 ÁKVÖRÐUN 1 (freeze-anchor pin).

**Hliðin og rökin:**

| Hlið | Regla | Rök |
|---|---|---|
| G1 nákvæmni | cand MAPE ≤ live MAPE + 0,5 pp, heild og hvert kjarnasegment | aldrei skipa verra módeli; 0,5 pp = flögg-þröskuldur VÉL 1 (`model_quality_eval.MAPE_FLAG_PP`) |
| G2 bias | \|cand bias(log)\| ≤ 0,02 heild; ≤ 0,04 kjarnasegment | ferskt módel á að vera ~óbjagað á eigin samtíma; 0,02 ≈ helmingur drift-viðvörunarmarka |
| G3 þekja | cov80 ∈ [75, 85], cov95 ∈ [91, 98] | conformal-markmið ± úrtaksóvissa á ~2.000 raða glugga |
| G4 drift-lokun | median Δlog(cand−live) per kjarnasegment = −(live bias) ± 0,03 | skiftið á að LOKA mældu drifti; stærra skift en driftið bendir á skema-breytingu, ekki endurkvörðun |
| G5 grade | round-to-round \|Δ A-hlutdeild\| ≤ 5 pp milli hringja (sjá DECISIONS 2026-07-04) | grade-dreifing á ekki að umturnast við hring; stórt stökk = conformal-gluggi óheilbrigður |

Fyrirvari sem skýrslan ber sjálf: kandídatinn notaði gluggann í early-stop +
conformal (quasi-OOS, væg bjartsýni); live er ekta OOS þar. Bias-samanburðurinn
(G2/G4) er ónæmur fyrir þessu; MAPE-munur < ~0,3 pp túlkast ekki sem raunmunur.

**Túlkun á G4-falli (lærdómur dress rehearsal 2026-07-02):** ef G4 fellur en
mánaðarlega bias-röðin sýnir kandídat ≈ live-leiðrétt per mánuð, er driftið
markaðshreyfing EFTIR gagnaenda kandídatsins (fæðingar-offset) — endurþjálfun
getur ekki lokað því. Rétt viðbragð: (a) flippa samt ef G1-G3 standast og
MAPE-ávinningur er skýr (skrá G4-frávikið), eða (b) bíða 1-2 mánuði eftir að
eftir-hreyfingar sölur komi inn í kaupskrá og endurkeyra hringinn. ALDREI
brúa með úttaks-skalar (§7).

**Opið hönnunarverk fyrir fyrsta alvöru hring (G5, dress rehearsal):** 3-mán
conformal-calib gefur rétta þekju en óstöðug grade-mörk (A-hlutdeild sveiflast
>10 pp því sellu-breiddir liggja nærri 0,20/0,36 þröskuldunum). Tveir kostir sem
sér-próba þarf að meta: (a) 6-mán conformal-gluggi — kostar 3 mán auka
gagna-öldrun þjálfunar því calib þarf að vera OOS (backtest §4: ~0,3 pp bias);
(b) halda 3-mán glugga en jafna sellu-BREIDDIR (t.d. blanda eigin glugga og
næstliðins hrings breiddar — ATH breiddar-stöðgun, ekki erfð kvörðunar-miðju;
miðjan kemur alltaf úr fersku módeli). Ákvörðun áður en flippað er á grade-bera
kandídata.

**LEYST (DECISIONS 2026-07-04, heimild `docs/fable_prep/audit/G5_PROBE.md`):** rótarorsök G5
mæld = sýnatöku-suð í sellu-kvantílum við 0,20/0,36 mörkin (pivot-sella `APT_FLOOR|Capital_sub`
situr ofan á A/B-þröskuldi og flöktir A↔B milli hringja). **STAÐALL frá og með næsta hring: 6-mán
OOS conformal-calib** (train_end −3 mán m.v. núverandi 3-mán) — þéttir pivot-sellu q80 std
0,0082→0,0038 og fækkar grade-flippum 5→3 á 7 hringjum; öldrunar-kostnaður ~0,26 pp MAPE /
~0,1–0,3 pp bias (ásættanlegt, nettó betri en live). Ódýra 6-mán útgáfan (train_end óbreytt) er
ÓGILD (eldri helmingur in-sample → cov80 73,3% fellur G3-gólf). **G5-hliðið endurskilgreint:
G5 = round-to-round |Δ A-hlutdeild| ≤ 5 pp milli hringja** (ekki mun-frá-live, sem er confounded;
pivot-sellu q80 std = stuðningsmælir) — leysir af 10 pp / mun-frá-live regluna í G4/G5-töflunni að
ofan. Breiddar-stöðgunin (kostur b) = skjalfestur **NEYÐARHEMILL** (α=0,5 við SÍÐASTA retrain-hring,
aldrei live; virk aðeins með sér-ákvörðun; backtest-fyrirvari: yfirskýtur í trendi); aðeins BREIDDIR
blandast, miðjan alltaf fersk.

**HALT-punktur 3 (aðal):** parity-skýrslan fer til Danna með GO/NO-GO tillögunni.
**Ekkert flip án skýrs „go" frá honum** — líka þegar öll hlið standast.

## 5. Skref 4 — flip (sér-lota, sér-go)

Flippið fylgir júlí-flip mynstrinu (DECISIONS 2026-06-30 + 2026-07-02 conformal-flip):

1. Nýtt universe-rebuild með kandídat-artifactinu:
   `rebuild_predictions_iter4.py`-afbrigði sem les boostera úr artifact-möppunni
   (breytur: booster-slóðir, `MODEL_VERSION='<version>'`,
   `CALIBRATION_VERSION='<version>_conformal_v1'`) → CSV í exports.
   ATH: `MODEL_ANCHOR_YM` fylgir þjálfunar-pkl-inu — við endurþjálfun á
   endur-ankraðri pkl færist real-skalinn; `model_pred_anchor_ym` í
   pipeline_config VERÐUR að uppfærast í flip-transactioninni (annars brotnar
   VÉL 1 de-anchor, sjá model_quality_eval ÁKVÖRÐUN 1/2).
2. Staging-tafla → COPY → **DB-parity gate** (staging vs CSV: rowcount, checksum,
   per-segment dreifing) → snapshot-backup á núverandi predictions
   (`predictions_<YYYY_MM>` mynstrið) → atomic UPDATE/UPSERT í einni txn
   (`SET TRANSACTION READ WRITE` fyrst á pooler; replica-mode aðeins ef
   feature_attributions fylgja með).
3. `pipeline_config.model_pred_anchor_ym` + `model_version` uppfært í SÖMU txn.
4. MV-refresh: aðeins `semantic.v_model_vs_sold_by_hood` les predictions.

**Rollback:** snapshot-taflan úr skrefi 2 + gamla artifact-mappan (live boosterar
eru aldrei yfirskrifaðir) → TRUNCATE+INSERT úr snapshot, `pipeline_config` til
baka, MV-refresh. Æfð aðgerð (DECISIONS 2026-06-28 rollback).

## 6. Skref 5 — næturkeyrslu-gate + vakt

- `verdmat-weekly-model-quality` (VÉL 1) keyrir á nýju predictions; fyrsta keyrsla
  eftir flip er GATE: overall MAPE/bias/cov flögg vs held-baseline mega ekki
  versna > flögg-þröskulda (0,5 pp MAPE / 3 pp cov).
- d-panel (comp-vél diagnostík) á fyrsta mánuði eftir flip á að sýna |med d|
  heildar < 0,02 — annars var drift-lokunin ekki raunveruleg.
- Backup-nótt (03:00) þarf að ganga áður en gamla snapshot-taflan er hreinsuð.

## 7. Vísitölu-skalar á módel-úttak — BANNAÐUR þögull

Læst í DECISIONS 2026-07-02: enginn index-margfaldari á `real_pred_*` dálkana
sem „ódýr endurkvörðun" milli hringa. Ef neyðarbrú þarf einhvern tíma
(t.d. trigger fire-ar en endurþjálfun tefst) skal hún vera (a) hávært merkt í
`calibration_version`, (b) tímabundin með skráðri gildislok, (c) samþykkt af
Danna sérstaklega. Rök: þögull skalar felur rotnunina fyrir öllum mælum
(parity, VÉL 1, d-panel) og gerir næstu endurþjálfun ósamanburðarhæfa.

## 8. Skrár og eignarhald

| Hlutur | Slóð | Eðli |
|---|---|---|
| retrain_sales_model.py | `precompute/` | endurþjálfun → artifact-mappa |
| recalibrate_conformal.py | `precompute/` | Mondrian conformal á kandídat |
| parity_check.py | `precompute/` | GO/NO-GO skýrsla |
| Artifact-möppur | `D:\model_artifacts\<version>\` | aldrei yfirskrifaðar |
| Live boosterar | `D:\iter4a_*.lgb` (+ eftirmenn) | aðeins flip-lota bendir á nýja |
| Backtest-heimildin | `docs/fable_prep/audit/RETRAIN_CADENCE.md` + CSV/parquet | rök cadence/trigger |
| Cadence + trigger ákvörðun | `docs/DECISIONS.md` 2026-07-02 | læst |
