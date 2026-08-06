# GO-BRÉF — FLIPP ÁGÚST-ENDURÞJÁLFUNARINNAR (REGLA R + STRÚKTÚR + KVÖRÐUNARLÖGIN TVÖ)

**Til:** eigandi (Danni) — til kvittunar
**Frá:** arkitekt/framkvæmd, cc98 · **Dagsetning:** 2026-08-06
**Staða skjals:** HEIMILD (tracked í docs/). **Engin framkvæmd hefur átt sér
stað; ekkert flipp.** Flippið sjálft (skref 5) fær sitt GO aðeins eftir
kvittanir á §3 og §4 hér að neðan — og keyrist með arkitekt og eiganda VIÐ
BORÐIÐ, ekki ómannað.

**Heimildaslóð ákvarðana:** fasi 0–1 (cc78, 03.08) → skref 1–2 (þjálfun + mat,
04.–05.08) → 3.0/A/B/D1/D2 (rótargreining reksins, 05.08) → útnefning D2 í
sam-rýni → 3.1 (Mondrian) → 3.3 (framreiðslulag; dómsviðmið NÁÐ 06.08).
Audit-skjölin öll í `docs/fable_prep/audits/AGUST_ENDURTHJALFUN_*` og
runbókin í `docs/ROLLBACK_RUNBOOK_CC78.md`.

---

## §1 HVAÐ FLIPPAR — EIN heild, þrjú lög

**`iter4r_20260805_reglaR_strukt`** (D2: regla R-endursegmentun + 156 features
þ.m.t. `flm_hlutfall`/`n_ibudareininga`) **+ Mondrian-kvörðunin 3.1 + framreiðslu-
endurkvörðunarlagið 3.3 — sem EIN heild.** Ekkert laganna þriggja flippar sér.

Artifact-mappan `D:\model_artifacts\iter4r_20260805_reglaR_strukt\`, sha256[:16]:

| skrá | sha |
|---|---|
| `_manifest.json` (ber `flip_status: FLIPP-KANDIDAT`) | `f0bb1e01eac9119b` |
| `_main_mean.lgb` | `5108f3d84061d6d6` |
| `_main_q025 / q100 / q500 / q900 / q975.lgb` | `f6e743ae6d41caed` / `172f6414babf1211` / `84b8829572b84927` / `e504a6f132f25623` / `4f7740780678fbcf` |
| `_summer_mean / q025 / q100 / q500 / q900 / q975.lgb` | `72db894e33becdf8` / `de2c51ae24adcda3` / `e8af1aeddca2cb5c` / `3efc01d88d10576a` / `bc2d2326b76b096a` / `39ca8077b4bd234b` |
| `_predictions.pkl` | `e96e5506a13fd811` |
| `_feature_importance.csv` (156) | `658086f45421b599` |
| `_training_log.txt` | `713b267c7f877e95` |
| `_conformal.json` (3.1 Mondrian, 10+5 sellur) | `6dca5e405edee1bd` |
| **`_conformal_serving_v1.json` (3.3 framreiðslulagið)** | **`6e736a47b82d9130`** |

Grunnar: þjálfunargögn `training_data_v2.pkl` sha `32f9a1242b212d11` ·
frosna flokkunarlindin `hms_classification_v1.pkl` sha `16d78e39d57cfcad` ·
frosni samanburðarkohorturinn sha `c0e548cfddc4b1ff`.
`iter4r_20260804_reglaR` (154f) er merkt **ALDREI-FLIPP** í manifesti
(`010c25f1d0954314`); `iter4r_20260805_preR_diag` er diagnostík eingöngu.

## §2 HVAÐ BATNAR — með nefnurum

Allt mælt á frosna kohortnum (847 holdout30 + 339 fresh_edge, sömu sölur undir
báðum kerfum), framreiðslurammi, nominal/nominal:

| stærð | gamalt (iter4r_20260716+cc51) | **nýtt (D2+3.1+3.3)** |
|---|---|---|
| MAPE holdout30 (n=847) | 9,96 % | **8,23 %** |
| medAPE holdout30 | 7,66 % | **5,87 %** |
| ferski jaðarinn MAPE (n=339) | 14,59 % | **11,59 %** |
| **cov80 ferski jaðarinn** | 76,70 — og **gamla kerfið náði honum aldrei yfir 75,4** í sinni kvörðunarlotu (cc49 §3.2) | **83,48** |
| cov80 / cov95 holdout30 | 81,11 / 95,51 | **81,58 / 96,69** |
| miss-samhverfa 80 %-bils (↑/↓) | 16,3 / 7,0 (fyrir 3.3-lag á nýja) | **8,97 / 9,45** |
| R_gerd — heilu húsin sem HMS merkir „Íbúð á hæð" (algengasta kvörtunarefnið): bias | +9,34 % vanmat (n=96) | **+5,57 %** |
| R_gerd cov80 | 63,54 (undir gamalli kvörðun) | **81,25** |
| `APT_FLOOR\|Country` cov80 (15 % alheimsins; gat síðan cc49) | 72,3 (báðar leiðir cc49) | **84,42** (n=77) |

**Endursegmentunin sjálf:** **62.126 sölur af 146.841 (42,3 %) réttflokkast**
í þjálfunargrunninum¹ — þar af 18.552 heil hús úr íbúðahólfunum í sérbýli
(R_gerd) og 43.574 milli íbúðahólfa (notkunar-leiðréttingin); APT_STANDARD
(47.177 sölur, næststærsta segmentið) leysist upp í rétt hólf. Á eignaþýðinu
færast ~58.500 eignir í réttari flokk við flipp (runbók §4).

¹ *GO-forskrift nefndi 62.175; mælt af diski 62.126 (Δ49 = ferskar sölur milli
mælinga). Allar tölur þessa bréfs eru mældar, ekki afritaðar.*

## §3 SÉR-KVITTUN EIGANDA #1 — LEVEL-MYNDIN

Punktmatið ber **+2,46 % heildarvanmat á holdout-glugganum** (óhreyfða
(b)-hólfið sjálft +2,45 %) — þetta er meðvitað verð fyrir R_gerd-lagfæringuna
og lokun jaðar-reksins, ekki hliðarverkun: rótin var sundurgreind í mælda þætti
(gögn +2,14 / merking +2,88; konvergens-, es-, samsetningar- og strúktúr-
tilgátur allar felldar með fyrirframbókuðum römmum) áður en ákvörðunin var
tekin. Til samanburðar bar gamla kerfið **−3,39 % ofmat** á sama hólfi —
|2,45| < |3,39|. Bilin lýsa vanmatinu (ósamhverft framreiðslulag, miss-
samhverfa ~9/9); **talan sjálf stendur og fær engan eftirá-stuðul.**

**Vöktun frá degi eitt:** bias-per-hólf lína ((a) R_gerd / (b) óhreyfðar /
(c1) hreyfðar + verðstigull) í weekly-mælingunni; **flagg við |(b)| > 4,0 %**.
Túlkunarlykill bókaður: vaxi (b)-vanmatið er það rek; kólni markaðurinn inn í
spálínuna sest það.

**[x] KVITTUN EIGANDA — level-myndin samþykkt sem meðvitað verð. KVITTAÐ
06.08.2026 (cc104, eigandi við borðið).**

## §4 SÉR-KVITTUN EIGANDA #2 — NOTENDAUPPLIFUNIN

Við flipp **færast verðmöt almennt ~2–5 % NIÐUR** (mest á dýrari eignum og
sérbýli) og **bil BREIKKA þar sem óvissan er raunverulega mest** — miðgildis-
breikkun ×1,13 á 80 %-bili (19,2→22,6 % af mati), en halinn fer í 55 %+ á
Country-sérbýlum. **Notandi sem man töluna sína frá því í síðustu viku sér
lækkun.** Flokkadreifing A/B/C breytist einnig (þröskuldar endurleiðast í
flipp-aðgerðinni, sbr. §6).

Valkostir að meðhöndlun — val eiganda:

- **(a)** þögult flipp — engin skýring;
- **(b)** ein lína á `/adferdafraedi` m/dagsetningu: endurbætt tegundaflokkun
  (heil hús sem skráin merkti „íbúð" flokkast nú rétt) og endurkvörðuð
  óvissubil; **← tillaga arkitekts: heiðarlegt, hófstillt, ekkert drama;**
- **(c)** = (b) + stutt útskýringarlína á eignasíðum í X daga eftir flipp.

**[x] VAL EIGANDA: (b)** — ein lína á `/adferdafraedi` m/dagsetningu (tillaga
arkitekts samþykkt). KVITTAÐ 06.08.2026 (cc104, eigandi við borðið).

## §5 VEIKU BLETTIRNIR — vöktunarlínur frá degi eitt, engin aðgerð nú

| blettur | mælt | n | eðli |
|---|---:|---:|---|
| `SFH_DETACHED\|RVK_core` cov80 | 64,7 | 17 | miss↓ 29 % — Country-drifin bil-hliðrun yfir-skýtur í RVK |
| `R_gerd\|RVK_core` cov80 | 59,1 | 22 | sama mynstur (~39 raðir samanlagt með SFH\|RVK) |
| <40M-verðbilið cov80 | 72,1 | 43 | ódýri endinn fær miss↓-þunga eftir lag |
| APT_ATTIC cov80 | 60,0 | 10 | n of lágt til aðgerða |

Allt fer inn í weekly-mælinguna sem sér-línur; aðgerð aðeins ef mynstur
staðfestist á vaxandi n.

## §6 FLIPP-RÖÐIN — orðrétt skv. runbók §2 + §10.3 + §10.4, með HALT-merkjum

| # | skref | HALT/skilyrði |
|---|---|---|
| 0 | **R1-frysting iter4r-spánna FYRIR flipp**: `predictions_2026_08_pre_cc78` + RLS + REVOKE; rowcount == 167.503, model_version == iter4r_20260716 á öllum, engin NULL, **handahófsúrtak gegn frosna kohortnum max\|Δ\|=0,0 á öllum fimm dálkum** | ⛔ **HART SKILYRÐI — rollback ómöguleg án; ALDREI eftir á** |
| 0b | R2 (`feature_attributions_…` 1.675.030) + R4 (pipeline_config bókað orðrétt) + R5–R9 (diskur: artifact ósnert, training_data-afrit ✔ þegar til, kóðaafrit ✔ þegar til) | ⛔ öll græn áður en haldið er áfram |
| 0c | R3 ✔ þegar til og sannreynt (232.887, frávik 0) · æfingarstig 1 ✔ grænt (§10.3) · **æfingarstig 2/3 (skrifleiðin á þrepi 5) þurfa SITT EIGIÐ GO skv. runbók §5** — ákvörðun við borðið fyrir flipp | ⛔ sér-GO |
| 1 | universe-rebuild úr kandídat-artifacti → CSV — **með hms-lags-innspýtingu** `n_ibudareininga`+`flm_hlutfall` (sha-hliðuð lind `16d78e39d57cfcad`) í alheims-skorunina (runbók §10.4.2; annars train/serve-skekkja) og **`--anchor-ym 2026-09`** (LESIÐ pkl-akkeri) | |
| 2 | staging-töflur + COPY + hlið (rowcount, universe, checksum, bil-röðun, corr) | HALT ef hlið fellur |
| 3–6 | **EIN atómísk transaction:** `SET TRANSACTION READ WRITE` → replica-role → UPDATE predictions ← staging → TRUNCATE+INSERT feature_attributions → pipeline_config (`model_version`, `model_pred_anchor_ym='2026-09'`, `calibration_version` serving_v1) → **UPDATE properties.canonical_code/unit_family/is_residential/is_summerhouse** → in-txn recheck FYRIR commit (§4-taflan: n_apt_std ≈206, n_summer == 13.924 ÓBREYTT, n_frav ≈58.500) | ⛔ **canonical_code og predictions.segment mega ALDREI vera sitt í hvoru ástandi — falli eitt þrep rúllar ÖLL txn** |
| 7 | COMMIT | |
| 8 | **trainer-skráin í D2-ástand + committ** (EXCLUDE −2 dálkar, `EXPECTED_N_FEATURES=156`, Int32→float64) — runbók §10.4.1; diff varðveitt í `.cc98_R154_20260805T093342Z` | committast VIÐ flipp, ekki fyrr |
| 9 | **MV-refresh — FIMM/SEX, ekki einn** (runbók §7-listinn: `v_model_vs_sold_by_hood`, `v_hood_heat`, `v_street_directory`, `v_street_activity`, `v_sveitarfelag_lookup` [+`v_summerhouse_market`]); UNIQUE-index tékkað ÁÐUR svo CONCURRENTLY falli ekki — **`flip_iter4r.py` endurnýjar aðeins EITT MV, VITAÐ GAT** | skylda, ekki valfrjálst |
| 10 | kóðafastar: `model_quality_eval.py` (BASELINE → §7-grunnur 3.3-auditsins, FREEZE/PRED_YM, bias-per-hólf línan inn) + **flokkaþröskuldar A/B endurleiddir á nýju breiddunum í SÖMU aðgerð** (cc49 §5.2: annars hverfur A-flokkur sem hliðarverkun) + `/markadur/modelstada`-prósa + `/stilla`-fjölskyldur | |
| 11 | raunprófun: `model_quality_eval --dryrun` ≈ §7-grunnurinn · `/eign/2013952` ber R-flokkun · `/stilla` 200 · `/leit` svarar | HALT ef frávik |
| 12 | **dómsregla virk á nýja grunninum frá degi eitt** (cov80 ≥ 80; fæðist græn á 81,58) + fresh_edge-þröskuldur heldur driftvörninni lifandi (cc49 §8.6) | |

Rollback-leiðin öll í runbók §3 (æfð á predictions/FA; þrep 5 ber æfingarstig
2/3 m/eigin GO). **Flippið keyrist með arkitekt og eiganda við borðið.**

## §7 HVAÐ FLIPPAR EKKI

- **Extraction-brúin (cc75)** — FROSIN þar til γ-mótpróf (sjá §8); þjálfunin
  keyrði á frosna apríl-eigindalaginu (bókað, mælt 23,7 % þekja).
- **γ-málið sjálft** (stöflunar-leiðréttingin úr cc81) — ósnert.
- **Birting fasteignamats-árgerðar** — óbreytt.
- Leigu-brautin (`predictions_rent*`), myndamál, semantic-vélarnar að öðru
  leyti — allt óbreytt eftir sem áður.

## §8 EFTIR-FLIPP RÖÐIN (bókuð röðun úr cc81 §9, óbreytt)

**ágúst-endurþjálfun (þetta flipp) → γ-frysting m/mótprófi og holdout →
afþíðing brúarinnar → endurmæling þakhlutfallsins.** Tenging brúarinnar í
nightly-keðjuna er áfram sjálfstæð, síðari ákvörðun (cc75).
**Fable ágúst-skýrslan fær endurþjálfunarsöguna sem kafla — ónefnd þar til þá.**

---

## KVITTANIR

| | staða | dags |
|---|---|---|
| §3 level-myndin — eigandi | [x] KVITTAÐ | 06.08.2026 |
| §4 notendaupplifun, val (a)/(b)/(c) — eigandi | [x] VAL = (b) | 06.08.2026 |
| Flipp (skref 5) — sér-GO, við borðið | [x] GO | 06.08.2026 |
