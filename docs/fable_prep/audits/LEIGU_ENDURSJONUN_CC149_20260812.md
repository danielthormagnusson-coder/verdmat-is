# LEIGU-ENDURSJÓNUNIN, ÞREP 3+4 AF 4 — SPÁIN OG ÞREPIÐ FLIPPUÐ, STUÐNINGSHLIÐIÐ F300 SETT UPP

**cc149 · 2026-08-12 · LIVE (predictions_rent + valuation_tiers_rent) + verdmat-ai deploy**

Undanfari: cc146 (forpróf, read-only) → cc147 (endurskorun, staging only) →
cc148 (stuðningshliðið mælt, read-only) → **cc149 (flipp + hlið + birting)**.

Mælitöflur: `D:\_audit\cc149_leigu_flipp\`.
Skriftur: `precompute/cc149_freeze.py` · `cc149_flip_pred.py` · `cc149_flip_tiers.py` ·
`cc149_maeling.py` · `build_rent_tiers.py` (breytt, afrit `.pre_cc149_20260812T204705Z`).
Bakleikir: `app/scripts/predictions_rent_rollback_cc149.sql` ·
`app/scripts/valuation_tiers_rent_rollback_cc149.sql`.
Snapshot `predictions_rent_pre_cc149` og `valuation_tiers_rent_pre_cc149` STANDA.

---

## 0. MÆLITÆKIÐ SANNAÐ FYRST — Á GAMLA INNTAKINU

Þrepavélin með nýja ásnum var keyrð á **lifandi (gömlu) spánni** áður en nokkru
var hreyft. Tvennt þurfti að standast og gerði það:

1. **Grunnþrepin endurgera lifandi töfluna.** T1 32.274 + 252 = **32.526** ·
   T2 70.501 + 1.059 = **71.560** · T3 19.730 + 1.242 = **20.972** ·
   T4 18.175 + 986 = **19.161** · T5 17.634 − 3.539 = **14.095**. Hvert einasta
   þrep lendir á lifandi tölunni þegar hliðið er dregið frá — hliðið er eina
   hreyfingin sem vélin bætir við.
2. **Hliðið endurgerir cc148-töluna upp á rað:** 3.539 alls, sérbýli 3.040,
   fjölbýli 499, nefnari 144.219 — nákvæmlega F300-lína
   `05_throskuldskostir.csv` úr cc148.

Þetta er sami agi og [[feedback_keyrdu_velina_a_gamla_inntakinu_fyrst]] kostaði
cc147 að læra: án núll-keyrslunnar væri ekki hægt að segja hvað er nýi ásinn og
hvað er rek í vélinni.

**Forspá flippsins var því mæld FYRIR flipp**, með því að beina byggjaranum á
cc147-staging (`--pred-table public.predictions_rent_cc147_staging`). Sú keyrsla
skilaði nákvæmlega þeirri töflu sem síðar var flippuð.

---

## 1. FLIPPIN TVÖ — POSTVERIFY INNAN txn

Bæði flippin eru TRUNCATE+INSERT í einni txn (cc135-rökin: RENAME færir
nafnaflækjuna með sér — vísarnir heita enn `*_staging_pkey` eftir cc30). Öll
hlið mælast á LIFANDI töflunni eftir INSERT og fyrir COMMIT.

### `predictions_rent` ← `predictions_rent_cc147_staging` (22:20:08)

| hlið | gildi | krafa |
|---|---|---|
| raðir | 158.314 | 158.314 |
| EXCEPT-diff **báðar áttir**, 12 dálkar | 0 | 0 |
| munaðarleysingjar | 0 | 0 |
| **segment vs `properties.canonical_code`** | **0** | 0 |
| rangt `model_version` | 0 | 0 |
| bilaröð brotin (lo95≤lo80≤mean≤hi80≤hi95) | 0 | 0 |
| Σ pred_mean | 48.534.230.514 | 48.534.230.514 |
| NULL á 12 dálkum | 0 | 0 |
| RLS · policies · SELECT-grants | True · 1 · 2 | True · 1 · 2 |

**cc135-ólæknaða málið er lokað.** Þar stóð bókað: *„`segment` ber pre-R
canonical_code á 57.612 röðum (36,39 %); ás 2 læknast AÐEINS með endurskorun."*
Sú endurskorun er nú lifandi og mismunurinn er **57.417 → 0**.
`model_version` fer úr `rent_v1_nan` í `rent_v1_reglaR_20260812`.

### `valuation_tiers_rent` ← `valuation_tiers_rent_staging` (22:20:42)

Byggð AF LIFANDI, NÝFLIPPUÐU `predictions_rent` — ekki af staging. Röðin skiptir
máli: hefði þrepið verið byggt fyrst væri það byggt á lagi sem er á leiðinni út.

| hlið | gildi | krafa |
|---|---|---|
| raðir · EXCEPT-diff · canonical-mismunur · munaðarleysingjar | 158.314 · 0 · 0 · 0 | — |
| T5 án ástæðu / ástæða utan T5 | 0 / 0 | 0 / 0 |
| **segment vs spá** | **0** | 0 |
| **pi80 endurgerist ekki úr lifandi spá** | **0** | 0 |
| RLS · policies · SELECT-grants | True · 1 · 2 | True · 1 · 2 |

**`pi80_endurgerist_ekki = 0` er hliðið sem cc135 gat ekki sett.** Það krefst
þess að `pi80_pct` í þrepatöflunni endurgerist upp á tvo aukastafi úr
`(hi80−lo80)/mean` í lifandi `predictions_rent`. Falli það hlið er þrepataflan
byggð á öðru lagi en talan sem notandinn sér — nákvæmlega gallinn sem cc135
þurfti fjórar lotur til að finna, nú vaktaður sjálfvirkt í hverju flippi.

---

## 2. STUÐNINGSHLIÐIÐ (ÁS 5) — HVAÐ ÞAÐ ER OG HVERS VEGNA

Ásarnir fjórir sem fyrir voru mæla allir **hve þykk sellan er**. Enginn þeirra
mælir **hvort eignin liggi innan hennar**. cc148 sýndi að þetta er ekki sami
hluturinn: sérbýli á T1 fer OFTAR út fyrir stærðarstuðning sellunnar (72,59 %)
en sérbýli á T4 (35,59 %). Sjá [[feedback_selluthykkt_er_ekki_nalaegd]].

**Reglan (`STUDNINGSHLID` í `build_rent_tiers.py`):**

```
einflm > sellu-max (einflm-ás, samningar 2011-2023, LIVE-endurmerktir)
  EÐA einflm > 300 m²
    -> Þrep 5, t5_astaeda = 'utan_studnings_staerd'
```

Þröskuldarnir standa í config með heimildarvísun í cc148, ekki harðkóðaðir inni
í `assign()`. Nýi liðurinn er **neðst í forgangsröð ástæðna** (eignaflokkur >
engin svæðisgögn > of fáir samningar > utan stuðnings), svo eign sem var þegar
óbirtanleg heldur ástæðunni sem hún bar áður.

**Hvorugur liðurinn dugir einn.** Sellu-max eitt sleppir Sjafnargötu 14 (384 m²,
percentíla 93,77 í sinni sellu) og öllu því bandi þar sem umsnúningurinn er
þegar mældur. Fast þak eitt hunsar að sella getur verið þunn löngu fyrir 300 m².
Fasti liðurinn þarf að vera til því **sellu-max á einflm-ás er MENGAÐ af
hlutasamningum**: samningur um kjallaraíbúð í 400 m² húsi lyftir max-inu í 400
án þess að nokkur hafi leigt húsið. Sundurliðunin sýnir að báðir liðir bera
sitt: 2.035 falla aðeins á sellu-max, 3.031 aðeins á fasta þakinu, 705 á báðum.

**Þröskuldurinn 300 m² er mældur, ekki valinn** (cc148 lið 1B/4): þar hverfa
stuðningur og mark samtímis. Heilir sérbýlissamningar 300–350 m²: 41 alls, 4 frá
2021, 41,5 % á ritskoðunarþaki þjálfunarmarksins. Yfir 350 m²: 7 á þrettán árum,
0 frá 2021. Log-log hallinn snýst úr **+0,433** (20–200 m², markaður +0,390) í
**−0,343** (350–1000 m²) — talan hættir að vaxa með stærð og fer að falla.

**Kostir sem borðið hafnaði** (cc148): A/C/D/G/H settu 5,8–30,5 % þýðisins í T5 =
afturköllun á vörunni, og STAERD-ásinn blandar saman „utan stuðnings" og
train/serve-galla (sjá [[feedback_frumas_thjalfadur_a_odru_mengi_en_skorad]]).
B eitt og sér sleppir Sjafnargötu. **F300 = 2,45 %.**

### FYRIRVARI SEM STENDUR MEÐ HLIÐINU — VÖKTUNARLIÐUR

**Hliðið FELUR töluna, það LAGAR hana ekki.** Umsnúningurinn byrjar við 200 m²
þar sem enn eru **481 heilir samningar** — bandið **200–350 m²** ber því
vanmetna tölu SEM ER ENN BIRT. Það er meðvituð málamiðlun: að loka því bandi
líka hefði kostað margfalt fleiri eignir án þess að mælingin þar sé jafn afdrátt-
arlaus. Bandið er vöktunarliður og fer á PLANNING_BACKLOG, ekki „leyst mál".

---

## 3. NIÐURSTAÐAN Á ÞÝÐINU

| | lifandi fyrir | eftir cc149 | breyting |
|---|---|---|---|
| T1 | 32.526 | 32.274 | −252 |
| T2 | 71.560 | 70.501 | −1.059 |
| T3 | 20.972 | 19.731 | −1.241 |
| T4 | 19.161 | 18.174 | −987 |
| **T5** | **14.095** | **17.634** | **+3.539** |

**T5-ástæður (nefnari 158.314):**

| ástæða | fyrir | eftir | breyting | % þýðis |
|---|---|---|---|---|
| `of_fair_samningar` | 13.586 | 13.530 | −56 | 8,55 |
| **`utan_studnings_staerd`** | **0** | **3.539** | **+3.539** | **2,24** |
| `eignaflokkur` | 314 | 314 | 0 | 0,20 |
| `engin_svaedisgogn` | 195 | 251 | +56 | 0,16 |

**Kohort:**

| kohort | allt þýðið | sýnilegt (án fjöleininga) |
|---|---|---|
| FÁ birt mat (T5 → <5) | **0** | 0 |
| MISSA birt mat (<5 → T5) | **3.539** | **3.524** |
| — þar af `utan_studnings_staerd` | 3.539 | 3.524 |
| — þar af annarri ástæðu | 0 | 0 |
| flokkur breytist | 13.611 | 13.597 |
| pi80 þrengist / víkkar / óskert | 105.460 / 52.854 / **0** | — |

Fjöleiningar-vörnin (`v_fjoleining_fastnum`, 197 raðir í þýðinu) tekur 15 af
þeim 3.539: þær báru aldrei tölu á yfirborði, svo raunverulegt tap birtra mata
er **3.524**. Þeir sem missa: sérbýli 3.040, fjölbýli 499; einflm p10 259,9 /
p50 329,7 / p90 441,1 / max 970,0 m²; leigumatið sem hverfur ber miðgildi
**347.019 kr./mán** (hæst 476.376). Þau þrep sem þeir báru: T1 252 · T2 1.059 ·
T3 1.242 · T4 986 — hliðið bítur á ÖLLUM þrepum, sem er einmitt innistæðan:
þykkt sellu ver ekki gegn því að eignin liggi utan hennar.

---

## 4. VIÐAUKI — VÍXLAMATRIXAN Á 56 RÖÐUM

`of_fair_samningar` fellur um 56 og `engin_svaedisgogn` hækkar um 56. Mismunur
tveggja teljara SEGIR EKKI hvaða raðir hreyfðust: hann er samhljóma bæði við
„56 hurfu úr T5" og við „56 skiptu um ástæðu". Víxlamatrixan sker úr, talin á
röðum — og hún hefur **aðeins tvær færslur í öllu þýðinu**:

| fyrir | eftir | n |
|---|---|---|
| — birt mat — | `utan_studnings_staerd` | 3.539 |
| `of_fair_samningar` | `engin_svaedisgogn` | **56** |

Þær 56 fara **`fallback_lvl` 1 → 3 á öllum 56** (segment breyttist á 56 af 56),
`n_local` hæst 4 og því enn undir MIN_LOCAL=5, þrep T5 → T5. **Engin röð fór úr
T5.** Nýja spáin setti þær á global-fallback, sem er ofar í forgangsröðinni en
`of_fair_samningar`, svo ástæðan endurmerkist. Báðar voru sannar fyrir og eftir;
taflan skrifar aðeins þá efstu. Þetta er endurmerking ástæðu, ekki hreyfing á
birtingu — og hún sést á yfirborðinu (Vesturgata 30, lið 6).

---

## 5. DÓMSKILYRÐIÐ ÚR cc147 — DÆMT

cc147 lagði fimm ákvörðunarliði fyrir borðið og skildi tvo eftir sem
dómskilyrði. Staða þeirra eftir cc149:

| liður | staða |
|---|---|
| **`k_global` mælt en ekki hreyft** (1,108152 → 1,107372, −0,070 %) | **ÓHREYFT** eins og bannið sagði. Level-frávik sem getur ekki hreyft pi80. |
| **Flokkur B→C á 13.605** | **DÆMT: bilið segir satt, víxlin standa.** Þetta er AFHJÚPUN, ekki afturför — sjá lið 5.1. |
| `feature_attributions_rent` tóm | óbreytt, meðvituð úrfelling |
| 101 raðir með canonical_code utan leigu-þjálfunar (NaN-flokkur) | óbreytt, á backlog |
| pi95 hreyfist öfugt við pi80 | óbreytt, enginn flötur les 95 %-bilið; á backlog |

### 5.1 FLOKKA-VÍXLIN ERU AFHJÚPUN, EKKI AFTURFÖR

13.608 eignir fara B→C og 3 fara C→B. **Engin tala versnaði.** Það sem gerðist
er að sérbýli hætti að lesa fjölbýlis-conformal-sellu: miðgildisbreidd sérbýlis
fer úr 46,76 % í **57,76 %** (+11,00 pp) á 56.447 eignum. Gamla, þrengra bilið
var rangt — það var reiknað á sellu sem eignin átti ekki heima í. Bókstafurinn
versnar af því hann segir loksins satt.

Þetta er sama tegund niðurstöðu og §5D-8 bókaði um sellu-driftina: mæling sem
lítur út eins og afturför en er leiðrétting á ómældri skekkju.

---

## 6. RAUNPRÓFUN Á PRODUCTION (www.verdmat.ai, eftir deploy 316ef09)

Cache-TTL virt: `/leiguverd/[fastnum]` les `unstable_cache` (TTL 600 s) og
**útgáfa ógildir hann EKKI**. Fyrsta sókn á Sjafnargötu skilaði nákvæmlega
`pre_cc149`-röðinni (317.227 / 237.458–423.794 / Þrep 1) — staðfest gegn
snapshot-töflunni áður en nokkuð var dæmt, svo stöðnun væri ekki lesin sem
rökvilla. Sókn eftir veltu skilaði nýja ástandinu (stale-while-revalidate).

| eign | slóð | á skjá | dómur |
|---|---|---|---|
| **Skeljatangi 9** (2278725, 508 m²) | `/leiguverd/2278725` | Þrep 5 + „Leigumarkaður fyrir eignir af þessari stærð er of lítill á Íslandi til að bera tölfræðilegt mat." · engin tala | ✅ |
| **Sjafnargata 14** (2009073, 384 m²) | `/leiguverd/2009073` | Þrep 5 + sami texti · engin tala | ✅ |
| **Bröndukvísl 17** (2043850) | `/leiguverd/2043850` | **397.221** kr./mán · 298.749–528.151 · Flokkur C · Þrep 3 | ✅ upp á krónu |
| **Jakasel 25** (2057333) | `/leiguverd/2057333` | **361.265** kr./mán · 271.707–480.343 · Flokkur C | ✅ upp á krónu |
| **Vesturgata 30** (2000426, ein af 56) | `/leiguverd/2000426` | „Engin svæðisbundin leigugögn liggja fyrir…" — **EKKI** of_fair-textinn | ✅ endurmerkingin sést |
| **Auðnukór 6** (2314482, 345 m²) | `/leiga/332778` | Þrep 5 + nýi textinn | ✅ auglýsingaflöturinn |
| **Ránargata 8A** (2001693, T2, viðmið) | `/leiguverd/2001693` og `/leiga/342295` | 377.930 · 312.062–457.701 · Flokkur C · Þrep 2 | ✅ engin hliðarverkun |

Console hreint á báðum flötum. Bilin bera nýju breiddina á öllum sem halda mati.

---

## 7. BIRTINGARLAGIÐ

Ein skrá breyttist: `verdmat-ai/config/leiga-skyringar.ts`, +8 línur — nýr lykill
`utan_studnings_staerd` í `LEIGU_T5_ASTAEDUR` með texta borðsins orðréttum og
kóðaathugasemd sem ber cc148-mælinguna.

**Þögula bilunin sem þetta lokar:** `LEIGU_T5_ASTAEDUR[t5_astaeda]` skilaði
`undefined` fyrir óþekktan lykil og `&&`-hliðið í `Leigumatskort.tsx` felldi
málsgreinina **án villu**. Eignin hefði borið Þrep 5 án ástæðu um óákveðinn tíma.
Þess vegna fór DB-flippið og pushið í sömu lotu með stystum mögulegum glugga á
milli (22:20 → 22:5x).

Einn `Record`, fjögur yfirborð: `Leigumatskort`, agent-verkfærin
(`lib/agent-tools.js`), `/leiguverd/[fastnum]` og `/leiga/[id]` lesa sama lykil —
engin önnur skrá þurfti breytingu. Sjá
[[feedback_bakendaflotur_an_notendaflatar]]: framendinn var greppaður ÁÐUR en
flippið var bókað sem notendaáhrif.

---

## 8. ÓSNERT (bann lotunnar, virt)

`predictions` og `valuation_tiers` (sölu-hliðin) · `leiga_train.parquet` á diski
(mtime 2026-06-29, aðeins lesin) · `k_global` og CFG · `rent_conformal_corrections.json` ·
þröskuldarnir T1–T4 og MIN_LOCAL · `feature_attributions_rent`.
Engin migration. Snapshot `*_pre_cc135` og `*_pre_cc149` standa bæði.

**Rollback:** `app/scripts/predictions_rent_rollback_cc149.sql` og
`valuation_tiers_rent_rollback_cc149.sql` (TRUNCATE + INSERT úr snapshot í einni
txn, replica-mode). Birtingarlagið: `git revert 316ef09` — textinn er einn
lykill í `Record` og ekkert ástand fylgir honum.
