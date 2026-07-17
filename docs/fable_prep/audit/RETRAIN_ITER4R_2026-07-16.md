# RETRAIN_ITER4R — iter5-hringur #1 (vegvísaliður A): iter4r_20260716 FLIPPAÐ LIVE

> **cc6-lota 2026-07-16T21:06Z.** Fyrsti keyrði endurþjálfunarhringur skv.
> RETRAIN_RUNBOOK + G5-staðli (6-mán OOS conformal). Heimild: CONFORMAL_RECAL_2026-07-15.md
> (úrskurður Danna 15.07: retrain GO sem vegvísaliður A) + GO-A/GO-B í lotunni sjálfri.
> Artifakt + allar skýrslur: `D:\model_artifacts\iter4r_20260716\`
> (training_log, conformal_log, parity_report, holdout_report.{json,md}, holdout_rows.csv,
> rebuild_stdout.log, manifest.json).

## 1. Hringskilgreining (GO-A 16.07, fjórir liðir samþykktir)

- **Gagnastofn:** kaupskra.csv 15.07 (max þinglýst 14.07); training_data_v2.pkl
  endurbyggð 16.07 (146.499×170, +461 raðir) — pkl 28.06 var byggð FYRIR canonical-fixið.
- **×1000-override (varða 20.07 óleyst):** 744059/84/85 enn blásnar í CSV →
  gildisvarin ÷1000 í `build_training_data.py` (guard >1 mrd kr, faerslunumer-skorðað;
  löglegar fjöleininga-þinglýsingar ná 10 mrd → guard sker öruggt) + assert
  max KAUPVERD ≤ 20 mrd. 3/3 leiðréttar. Fellur sjálfkrafa út þegar HMS lagar.
- **Þrískipting (lekaleysi):** train ≤ 2026-01-15 (mínus 5% es seed 42) ·
  calib = 70% af 6-mán OOS glugganum (15.01→15.07) · **holdout = 30% lagskipt
  slembival (seed 20260716, skráð í manifest)** — sá hvorki þjálfun, es né kvörðun.
  Merkt additive í predictions.pkl (`calib_role`). Fyrirvari skráður: holdout deilir
  tímabili með calib (engri röð) → M1 = exchangeable-þekja; framtíðarrek er vaktarinnar.
- **Aðferð:** EXACT iter4a (154 features, enginn fasteignamat). Nafnaregla:
  iter4r_* = arkitektúr óbreyttur; „iter5" frátekið fyrir feature-breytingu.
- **Interim-blend (c): ÓVIRKJAÐ endanlega** (GO-A c-liður) — hringur tók ~2 sólarhringa
  enda-á-milli, víðs fjarri 4–6 vikna þröskuldinum.

## 2. Mæling (HALT-B, öll skjöl í artifact-möppunni)

| Markmið | Niðurstaða | Dómur |
|---|---|---|
| M1 cov80 ≥79% heild + top5 sellur ≥75% | **81,2%** (n=848, ±2,7 pp); sellur 86,6/80,5/81,8/81,0/**75,0** | STENST |
| M2 punktspá ≤ live á SAMA holdouti | MAPE **7,58 vs 9,27%**, medAPE −1,26 pp, MAE −1,51 M | STENST |
| M3 flokkadreifing | alheimur A 36,1→**19,5%**, B 35,3→67,9, C 21,5→5,5, D 7,1 óbr. | skýring samþ. í GO-B |
| M4 6-mán OOS kvörðun | calib n=2.552 (15.01→15.07), innri cov80 82,8 | STENST |
| M5 model_pred_anchor_ym | **'2026-08' skrifað í flip-txn** (LESIÐ: 100% empírísk staðfesting á pkl; δ̂-krosspróf +1,82% ≈ log(cpi[08]/cpi[05])) | STENST |

Calib-MAPE main 8,67% (bil 6,5–9,5 ✓); conformal innri sannprófun cov80 82,8 / cov95 96,1 ✓.

## 3. FRÁVIK SKRÁÐ (GO-B skilyrði 1)

1. **sfh_country: G2+G4 parity-hliðin féllu BÆÐI á þessu eina segmenti** (n=100;
   bias cand +0,073 > 0,04; drift-lokun víkur 0,074 > 0,03). Mánaðarraðir sýna
   kandídat ≈ live-leiðrétt frá mars (júní +0,034/+0,033) = **fæðingar-offset**
   (markaðskólnun EFTIR gagnaenda þjálfunar) — **runbókarleið (a) valin**: flippað
   með G1/G3 græn og skýran MAPE-ávinning (−1,35 pp á segmentinu sjálfu). Vaktað.
2. **M3 A-fall −16,6 pp (36,1→19,5):** leiðrétting á ofseldri vissu — live-A þakti
   mælt 69,4% í stað 80 (CONFORMAL_RECAL); stefna+stærðargráða fyrirséð í
   ákvörðunarblaðinu; 19,5% ≫ 0,8%-hrun hafnaða 7-vikna gluggans. G5-parity-fastinn
   (10 pp vs live) er eldri en endurskilgreiningin 04.07 (round-to-round) og var
   ekki dómtækur á fyrsta hring — `parity_check.py` G5-fastinn uppfærist í næsta hring
   þegar round-to-round viðmiðun er til (fyrri-hrings artifact geymt).

## 4. Live-skipti (Fasi 3, allar tölur úr keyrslunni 21:02–21:06 UTC)

- **Rollback FYRST:** `predictions_2026_07_pre_iter4r` (167.503) +
  `feature_attributions_2026_07_pre_iter4r` (1.675.030), bæði RLS default-deny;
  Test-Path staðfest á gömlu artifaktana; `flip_iter4r.py --phase rollback` =
  endurheimtaruppskrift (TRUNCATE+INSERT úr snapshot + pipeline_config til baka).
- **Staging-hlið 7/7 PASS** (rowcount==CSV, universe exact 167.503, 0 NULL,
  bil-röðun conformal-raða 0 brot, corr 0,9912, med|Δlog|=0,047).
  **Lærdómur skráður:** bil-röðunarbrot í segcal_fallback-braut eru fyrirliggjandi
  eiginleiki (kvantíl-krossun native boostera): live bar 1.954, kandídat **1.447
  (færri)** — hliðið er hörð krafa á conformal-raðir + engin-afturför á fallback.
- **Atómískt flipp 12,6 s:** replica-mode txn (UPDATE predictions FROM staging;
  FA TRUNCATE+INSERT; **M5-lyklar í SÖMU txn**; in-txn recheck 167.503/167.503/0
  orphans FYRIR commit). MV `semantic.v_model_vs_sold_by_hood` refreshuð.
- **Eftir-flipps sannreynsla:** cohort 100% iter4r_20260716; grade A 32.625 /
  B 113.814 / C 9.170 / D 11.894 (= HALT-B vörpunin ±0,3 pp); NULL-tékk 0;
  10-eigna fyrir/eftir eðlilegt; v_current_predictions 167.503; **anon-REST smoke
  ✓** (2000281 → 92,3 M, B, iter4r — PostgREST-lagið ber nýja líkanið).
- predicted_at helst 2026-07-01 (verðmats-mánuður, ekki flipp-dags); appið les
  model_version dýnamískt úr DB → líkansheiti uppfærist sjálfkrafa alls staðar.

## 5. Vaktin (GO-B skilyrði 2) + heiðarleikasamræmi (skilyrði 4)

- Mánaðarleg þekju-vakt + **þrír nafngreindir sérliðir fyrstu mælingar**
  (APT_STANDARD|Capital_sub 75,0%-sellan; sfh_country offsetið; framvirka rekið
  −0,034 í júlí) — skráð additive í RETRAIN_RUNBOOK §6.
- modelstada-málsgreinin uppfærð í vinnutré: „endurþjálfað 16.07.2026; næsta
  þekju-mæling ágúst 2026"; 81,2% merkt **kandídatsmæling við þjálfun, ekki
  vaktarmæling**; engin ný tracking-röð fyrr en fyrsta vaktarmæling liggur fyrir.
  **Ópushað — samræmist cc4-textapakkanum við push-ákvörðun.**

## 6. Eftirstandandi (sér-ákvarðanir)

- Staging-töflur (`predictions_iter4r_staging` + FA, RLS default-deny) + snapshot-töflur:
  hreinsun eftir 24-klst stöðugleika + backup-nótt (júlí-flip mynstrið).
- Skript-breytingar ócommittaðar í precompute-vinnutré: retrain_sales_model
  (--holdout-frac/-seed), recalibrate_conformal (calib_role), rebuild_predictions_iter4
  (argparse kandídat-hamur), holdout_eval.py (nýtt), flip_iter4r.py (nýtt) +
  build_training_data.py ×1000-override (D:\ rót, utan repo). Commit/push = sér-go.
- `parity_check.py` G5-fasti → round-to-round í næsta hring (sjá §3.2).
- Vikuvél verdmat-weekly-model-quality: fyrsta keyrsla á nýju predictions er GATE
  (runbók §6) — VÉL-1 de-anchor les nú model_pred_anchor_ym='2026-08' (M5 tilgangurinn).

— cc6, 2026-07-16 · hringurinn allur: GO-A → þjálfun/mæling → HALT-B → GO-B → flipp
→ þessi audit. Næsti reglubundni hringur: skv. þekju-vakt (cov80<76% ×2 mán → flýta).

## 7. Hreinsun staging-taflna (cc14, 2026-07-17) — §6 fyrsti liður AFGREIDDUR

Skilyrði uppfyllt fyrir GO: 24+ klst frá flippi (16.07 21:06Z), backup-nótt hrein
(cc10 10/10), morgunúttekt 17.07 GRÆN.

**Féll (DROP, migration `cc14_drop_iter4r_flip_staging`):**

| Tafla | Raðir fyrir drop |
|---|---|
| `predictions_iter4r_staging` | 167.503 |
| `feature_attributions_iter4r_staging` | 1.675.030 |

Báðar tölur smullu við flipp-bókunina í §4 (rowcount==CSV, 10 FA-raðir á spá).

**Stendur ÁFRAM (ekki snert):**
- Rollback-snapshotið `predictions_2026_07_pre_iter4r` (167.503) +
  `feature_attributions_2026_07_pre_iter4r` (1.675.030) — til FYRSTU
  ágúst-vaktarmælingar skv. bókun HALT-C.
- `D:\last_listing_text_BACKUP_20260715.csv` — eigin varða ~22.07.
- `predictions_rent_staging` + `feature_attributions_rent_staging` — cc13-leigumatið
  í staging (promotion-leið), UTAN þessa flipps.

**Eftirtekt (utan §6-marka, sér-ákvörðun síðar):** `predictions_july_staging` +
`feature_attributions_july_staging` (júlí-mánaðarflippið) og generísk
`predictions_staging` standa enn í public — sama hreinsunarmynstur á við þegar
þeirra vörður falla, en þær tilheyra ekki iter4r-hringnum og féllu því ekki nú.

**Sannreynsla eftir drop:** `v_current_predictions` 167.503 ✓; anon-REST stikkprufa
2000281 → 92,3 M / gráða B / iter4r_20260716 ✓ (samhljóða §4-smoke). Lifandi lagið
ósnert.

— cc14, 2026-07-17 · push-hash skráður í commit-skilaboðum lotunnar.
