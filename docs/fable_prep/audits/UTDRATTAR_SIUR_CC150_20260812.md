# cc150 — API-SÍUR #2 OG #4: DAUÐ KÖLL OG NON-RESIDENTIAL ÚT ÚR ÚTDRÁTTARBIÐRÖÐINNI

**12.08.2026 · framkvæmd á `fetch_listings_needing_extraction` · heimild cc130.**
Allar formælingar READ-ONLY (`set_session(readonly=True)`). **Engin Haiku-köll:**
eina keyrslan á vélinni var `--forward 5` ÁN `--confirm` (þurrkeyrsla, 0 köll).
Verðeining $0,020717/kall (cc127). Nótt = `--forward 200` = $4,143.

---

## 0. FORMÆLING MEÐ RAUNFALLINU

**Mælitækið sannað fyrst.** Biðröðin var sótt með sjálfu
`E.fetch_listings_needing_extraction(ro, 10_000_000)` og `need`-CTE-ið síðan
endurgert í SQL til sundurliðunar. Spegillinn:

| | |
|---|---|
| raunfallið | **9.037 hashar** |
| CTE-endurgerð | 9.037 |
| mismunur hash-mengja | **0** |
| mismunur fulltrúa-`source_listing_id` | **0** |

Sundurliðunin sem á eftir kemur er því á sama mengi og pickerinn sér.
*(cc130 mældi 9.112 þann 12.08 kl. 00:10 — rek um 75 hasha á rúmum hálfum
sólarhring, biðröðin tæmist hraðar en hún fyllist. Sjá lið 3.)*

### (a) DAUÐ KÖLL — SKILGREINING cc130 ORÐRÉTT

cc130 §5d („Flokkarnir sem enginn getur lesið"), límt óbreytt:

> | flokkur | 30 d | $ | af hverju dautt |
> |---|---|---|---|
> | **fastnum ÓLEYST (NULL)** | 108 | $2,24 | `fetch_extracted_listings_to_value` krefst `fastnum IS NOT NULL`; brúin lyklar á fastnum. **Hvorug leiðin nær þeim.** |
> | **engin mbl-auglýsing ber textann** | 163 | $3,38 | textinn er horfinn úr `listings` — hvorki verðmat né brú finnur hann |
> | samtals | **271** | **$5,62** | **6,3 % næturinnar** |
>
> Þetta er eini flokkurinn sem er **sannanlega** tap: hann getur ekki náð neinum
> fleti, óháð ákvörðun um pásur eða brú.

**Skilgreiningin staðfest gegn lifandi kóða 12.08, ekki tekin á orðinu:**
`public.bru_extraction_i_eigindi` ber `where v.fastnum is not null`;
`fetch_extracted_listings_to_value` ber `l.fastnum IS NOT NULL`. Greppað yfir
bæði repó: `listing_extractions` er **hvergi lesin af `verdmat-ai`** (aðeins
ferskleika-stimpillinn á `/ops`, `app/ops/page.js:242`) — þriðja leiðin sem
gæti bjargað þessum röðum er ekki til.

Mælt á biðröðinni:

| liður | n | af 9.037 | $ |
|---|---|---|---|
| fastnum NULL á **öllum** auglýsingum sem bera textann (fail-closed) | **556** | 6,15 prósent | $11,52 |
| fastnum NULL á **fulltrúanum** einum (cc130 §4-talning) | 560 | 6,20 prósent | $11,60 |
| engin mbl-auglýsing ber textann | **0** | 0,00 prósent | $0,00 |
| fastnum til en engin `properties`-röð | 0 | 0,00 prósent | $0,00 |

**Seinni helmingur cc130-skilgreiningarinnar er 0 AF BYGGINGU á þessum fleti.**
Biðröðin er sótt ÚR `scraper.listings`; lýsing sem engin auglýsing ber kemst
aldrei í hana. Sá liður var mæling á ÞEGAR KEYPTUM útdráttum — hann bítur á
texta sem hvarf EFTIR kaupin og engin forsía nær því. Hann fær því enga línu í
kóðanum og ekkert í sparnaðartölunni.

**Munurinn 560 gegn 556** er fjórar raðir sem eiga systkina-auglýsingu MEÐ
fastnúmeri. Fail-closed útgáfan (`count(l.fastnum) > 0`) var valin: sbr.
`feedback_single_deed_sian_er_timahad` — samantekt á öllum systkinum er eina
greiningin sem er ekki tímaháð.

**Er `fastnum NULL` skammvinnt ástand?** Nei. NULL-hlutfall mbl-auglýsinga
(`lysing >= 300`) eftir aldri: ≤2 d **2,23 prósent** · 3–7 d 4,88 · 8–30 d 2,96
· 31–90 d 4,75 · >90 d **9,11**. Það vex með aldri í stað þess að falla, svo
NULL er ekki „óleyst enn". Og af 556 dauðu röðunum eru **549 eldri en 30 daga**
(7 í 8–30 d, 181 í 31–90 d, 368 eldri). Sían er hvort eð er FRESTUN, ekki
brottfelling: leysist fastnúmerið birtist röðin aftur næstu nótt af sjálfu sér.

### (b) COMMERCIAL / PLOT / OTHER

**Ásinn er `scraper.listings.category`, EKKI `canonical_code`.** `canonical_code`
ber ekki gildin commercial/plot/other yfirhöfuð — mótsvar hans er `EXCLUDE`, og
hann er notaður hér sem VÖRN (liður c) en aldrei sem sían sjálf. cc130 felldi
þriðja ásinn: `er_atvinnuhusnaedi` er RENT-ONLY, `NULL` á öllum 37.236
sölu-auglýsingum.

| liður | n | af 9.037 | $ |
|---|---|---|---|
| **allar** auglýsingar textans eru c/p/o (fail-closed) | **1.158** | 12,81 prósent | $23,99 |
| fulltrúinn er c/p/o (cc130 §4-talning) | 1.208 | 13,37 prósent | $25,03 |
| einhver auglýsing textans er c/p/o | 1.208 | 13,37 prósent | $25,03 |

Fulltrúa-dreifing biðraðarinnar: residential 7.829 · commercial 887 · plot 259 ·
other 62 · NULL **0**.

**VARÐHLIÐIÐ SEM MÆLINGIN KREFÐIST.** Af hráu 1.158 bera **67 raðir eign með
GILDU ÍBÚÐAR-CANONICAL**: SFH_DETACHED 38, SUMMERHOUSE 20, APT_FLOOR 6,
ROW_HOUSE 1, SEMI_DETACHED 1, o.fl. Það eru lóðar-auglýsingar á eign sem BER
hús — nákvæmlega sama mistalning og cc130 sá („28 falla á íbúðarflokka og eru
mistalning, ekki atvinnuhúsnæði"), bara á biðraðar-nefnaranum í stað
30-daga-nefnarans. **Hrá sían fellur á mótprófinu.** Með `canonical_code`-vörn
fellur **1.091** og mótprófið verður 0.

### (c) SKÖRUNIN VIÐ cc134-EXCLUDE-SÍUNA

| | teljari / nefnari | prósent |
|---|---|---|
| af c/p/o-menginu bera **enga** eign sem cc134-hliðið hleypir í gegn | **1.091 / 1.158** | **94,21** |
| af c/p/o-menginu bera íbúðarhæfa eign (sleppa gegnum cc134) | 67 / 1.158 | 5,79 |

**Skörunin er FULLKOMIN eftir vörnina:** varðaða mengið (1.091) ER nákvæmlega
það mengi c/p/o-raða sem `pr.canonical_code <> 'EXCLUDE'` í
`fetch_extracted_listings_to_value` stöðvar hvort sem er. Af því leiðir:

- **0 verðmöt tapast** við síu #4 — cc134 stöðvaði þau öll þegar.
- Það sem tapast er **eigindalagið**: 892 eignir sem hefðu fengið
  `source='auglysing'`-raðir gegnum brúna. Það er fórnin sem borðið samþykkti.

**En cc134 dregur EKKERT frá sparnaðinum.** Hún situr á VERÐMATSLEIÐINNI, sem
gerir engin Haiku-köll (cc134 bókaði $0,00). Haiku-kallið er keypt á
ÚTDRÁTTARLEIÐINNI. cc134 sparaði enga kalla; hún stöðvaði skorun. Sparnaðurinn
hér er nýr og ekki tvítalinn.

---

## 1. SÍURNAR

Ein breyting, í `fetch_listings_needing_extraction` (`scripts/extraction_engine.py`),
**hreint viðbætandi: 123 línur inn, 0 út.**

```sql
LEFT JOIN public.properties pr ON pr.fastnum = l.fastnum      -- nýtt
...
GROUP BY 1
HAVING count(l.fastnum) > 0                                    -- sía #2
   AND (count(*) FILTER (WHERE l.category IS DISTINCT FROM 'commercial'
                           AND l.category IS DISTINCT FROM 'plot'
                           AND l.category IS DISTINCT FROM 'other') > 0
     OR count(*) FILTER (WHERE pr.canonical_code IS NOT NULL
                           AND pr.canonical_code <> 'EXCLUDE') > 0)   -- sía #4 + vörn
```

Auk þess ~110 línu athugasemdablokk með cc130-heimildinni orðréttri og mældu
tölunum úr lið 0.

**Sama mynstur og cc134:** sían er á VERKEFNASKRÁNNI (hvað er keypt í kvöld),
ekki á neinni röð sem þegar liggur í `listing_extractions`. Ekkert eytt, ekkert
gamalt snert, og hvorug sían er endanleg.

**cc134-gildrurnar tvær, báðar skoðaðar í þessari skrá:**
1. **Prósentumerki í SQL-athugasemd.** Strengurinn fer í dag í `cur.execute(sql)`
   ÁN params, svo bert merki fellir hann EKKI eins og er — sem er einmitt
   ástæðan fyrir að reglan er skrifuð inn í blokkina: athugasemdir fá enga
   skoðun og params bætast við síðar. **Orðið „prósent" alls staðar, aldrei
   merkið.** Sannprófað með því að KEYRA strenginn, ekki lesa hann.
2. **cc128-falsy (0 er gildi).** Skoðuð og hún er ekki hér: hliðin bera ber
   `> 0` samanburð, ekki sannleiksgildi, og fallið hefur enga `if limit`-grein
   (`limit` er alltaf heiltala frá `run_extraction`, sem stöðvar á
   `effective_n <= 0` á undan).

**Margfeldi mælt, ekki gefið sér:** `public.properties` er einkvæm á `fastnum`
(232.887 raðir, 232.887 einkvæm) — `LEFT JOIN`-ið breytir engri samantektartölu
í `HAVING`.

---

## 2. SÖNNUN

Gamla fallið sótt **orðrétt úr `git show HEAD:scripts/extraction_engine.py`** og
keyrt í sama ferli og nýja fallið, á sömu tengingu.

### 2a. Biðröð fyrir/eftir — upp á röð

| | n | $ | nætur á 200/nótt |
|---|---|---|---|
| **fyrir** (`@HEAD`) | **9.037** | $187,22 | 45,2 |
| **eftir** (vinnutré) | **7.459** | $154,53 | 37,3 |
| **FELLT** | **1.578** | $32,69 | (17,46 prósent) |
| **BÆTT VIÐ** | **0** | — | — |

- `eftir ⊆ fyrir`: **satt**
- fulltrúi/texti breyttist á lifandi röðum: **0**
- **RÖÐUNIN ÓBREYTT:** gamla röðin síuð == nýja röðin, lið fyrir lið
  (`fresh DESC NULLS LAST` heldur nákvæmlega). Sían fjarlægir raðir; hún
  endurraðar engu.

Sundurliðun fellda mengisins: sía #2 **556** · sía #4 **1.022**
(= 1.091 − 69 skörun).

| mengi | n | $ |
|---|---|---|
| #2 dautt | 556 | $11,52 |
| #4 varðað | 1.091 | $22,60 |
| **skörun** | **69** | $1,43 |
| **sameining** | **1.578** | **$32,69** |

### 2b. Mótpróf — 0 residential-raðir felldar

| | |
|---|---|
| raðir í fellda menginu með **gilt íbúðar-canonical** | **0** ← krafa |

`canonical`-dreifing fellda mengisins: `EXCLUDE` 1.018 · `<engin eign>` 556 ·
`<engin eign>,EXCLUDE` 4. **Ekkert íbúðarhæft canonical kemur fyrir.**

`category`-dreifing fellda mengisins: commercial 834 · **residential 485** ·
plot 197 · other 59 · commercial+residential 2 · commercial+other 1.

**485 + 2 = 487 raðir bera `category='residential'` og eru samt felldar — allar
af síu #2, engin af síu #4.** Þær eru dauðar þrátt fyrir flokkinn: báðir
neytendur (verðmat og brú) lykla á `fastnum`, sem er NULL á öllum
auglýsingum sem bera textann. Þar af eru **310 leigu-auglýsingar** — sem er
jafnframt svarið við því af hverju leigan (cc130 tillaga #7, felld á 1,0
prósent) hverfur að hluta hér: hún hverfur ekki af því hún er leiga, heldur af
því hún ber ekkert fastnúmer.

### 2c. Þurrkeyrsla á 5 kalla sýni — vélin keyrir óbreytt

`python -m scripts.run_extraction --forward 5 --skip-valuation` (ÁN `--confirm`):

```
forward: requested=5 max_n=500 daily_cap=$10.0 spent_today=$3.9684
         budget_calls=268 -> effective_n=5
forward: 5 fresh distinct lysingar to extract (fresh-first)
[dry] re-run with --confirm to call Haiku.
VALUATION SKIPPED: --skip-valuation ...
bridge: SLEPPT (opt-in ...)
```

Adapterinn hleðst óbreyttur (156 eiginleikar, `iter4r_20260805_reglaR_strukt`,
hms-lind sha `16d78e39d57cfcad`). Sýnið sem pickerinn valdi:

| hash | augl. | m/fastnum | category | canonical | ferskt |
|---|---|---|---|---|---|
| `0ae9641321ab` | 2 | 2 | residential | APT_FLOOR | 2026-08-10 |
| `4c948f41238f` | 2 | 2 | residential | ROW_HOUSE | 2026-08-10 |
| `58dd629ab092` | 1 | 1 | residential | SEMI_DETACHED | 2026-08-10 |
| `69764135c981` | 2 | 2 | residential | APT_FLOOR | 2026-08-10 |
| `b2f9dfef8a45` | 3 | 3 | residential | SFH_DETACHED | 2026-08-10 |

**0 Haiku-köll í allri sönnuninni.**

---

## 3. SPARNAÐARSPÁ — MEÐ NEFNARA ÚR LIÐ 0

**Nefnarinn er BIÐRÖÐIN (9.037), ekki cc130-glugginn (4.312 keypt köll á 30
dögum).** cc130-tölurnar $5,62 og $7,19 mega ekki flytjast hingað óbreyttar:
biðröðin ber þyngri c/p/o-hlut (12,8 gegn 8,0 prósentum) af því að
atvinnu-auglýsingar liggja lengur ólesnar en íbúðir. Dauða hlutfallið helst
hins vegar nánast eins (6,15 gegn 6,3 prósentum).

**Sparnaður: 1.578 köll = $32,69**, mældur á biðröðinni eftir að skörunin (69)
er dregin frá og eftir að cc134-varðhliðið hefur skilað 67 röðum aftur.

### ÞETTA LÆKKAR EKKI `day_total` STRAX — OG ÞAÐ ER EKKI GALLI

Nóttin kaupir `min(--forward, biðröð)`. Biðröðin er **7.459** eftir síun, langt
yfir 200, svo **`day_total` heldur áfram að vera ~$4,143/nótt.** Sparnaðurinn
kemur fram sem STYTTRI BIÐRÖÐ: 1.578 köll verða aldrei keypt.

Koma nýrra hasha mæld: **418 á 27 dögum = 15,5/dag**, langt undir 200. Nettó-
tæming er því 184,5/nótt:

| | brúttó (200/nótt) | nettó (184,5/nótt) |
|---|---|---|
| nætur að tæmingu **fyrir** | 45,2 | 49,0 |
| nætur að tæmingu **eftir** | 37,3 | 40,4 |
| **flýting** | 7,9 | **8,6 nætur** |

**Það sem morgunvaktin getur í raun lesið næstu nætur:**

1. **`day_total` ≈ $4,14 óbreytt** — það er SPÁIN, ekki merki um að sían virki
   ekki. Falli hún strax er eitthvað annað að.
2. **`backlog`/biðraðardýpt féll um 1.578 við flippið** — það er talan sem
   staðfestir síuna.
3. **Samsetning keyptra kalla:** 0 raðir án fastnúmers, 0 c/p/o-raðir án
   íbúðarhæfrar eignar meðal nýrra `listing_extractions`-raða.
4. Fyrst þegar biðröðin fer undir 200 (~40 nætur) fellur `day_total` af sjálfu
   sér — og þá 8,6 nóttum fyrr en ella.

---

## 4. RÖÐUNARSKULDIN — BERUM ORÐUM

cc130 bókaði: **„RÖÐIN ER BINDANDI: #2 → #1 → endurmæla #3"** og setti LIÐ 0
(útganginn) ofar öllum síum: *„Áður en picker er þrengdur ætti að liggja fyrir
ákvörðun um (a) hvenær verðmats-pásan er tekin af og (b) hvort brúin fer í
`nightly_delta_chain.sh`."*

**Sú forsenda féll í DECISIONS §5D-6:** brúin er frosin á holdout-skilyrði, svo
„brúin fyrst" er ekki lengur biðstaða heldur ótímabundin frestun. Síurnar biðu
því **að óþörfu** frá 12.08 kl. 00:10 þar til nú — skuldin er bókuð hér svo hún
sé ekki endurtekin: **síu-röð sem hangir á öðru verki verður að bera dagsetningu
eða skilyrði sem einhver les.** Röðin #2 → #1 stendur að öðru leyti óhögguð.

**#1 (nær-eins-sía, $32,86 á 30-daga glugganum) stendur á backlog sem EIGIN
LOTA** — hún þarf hönnun á því hvernig vigurinn erfist (byggingarstigs-reitir
frá kjarna klasans, íbúðarstigs-reitir sértækir) og er jafnframt gæðabót:
`sameign_cosmetic` er ósamstillt í 51,0 prósentum klasa í dag.
**Dedup-lykill: `cc130-#1-naer-eins-sia`.**

**#3 / #5 / #6 eru FELLDAR AF MÆLINGU (cc130) og bókast hér svo enginn
endurveki þær:**

| # | tillaga | af hverju felld |
|---|---|---|
| **#3** | endurtekningarsía á eign | 62,1 prósent endurtekninga eru NÝR TEXTI frá öðrum fasteignasala — tilgátan féll á nefnaranum. **Tímaþak, ekki bann**, og bíður endurmælingar eftir #1 (skörun 897 köll). |
| **#5** | sleppa EXCLUDE í heild | cc116-talan (0/56.958 spár) á við BIRTINGARLEIÐINA, ekki eigindaleiðina. EXCLUDE ber 1.225 eigindaraðir á 379 eignum sem `/eign` sýnir. **EKKI „enginn les".** |
| **#6** | sleppa landsbyggð (`Country`) | þekjuskerðing á 26,4 prósentum kalla án nokkurs mælds mótvægis. Country-eignir bera spá og eigindi eins og aðrar. |
| **#7** | sleppa leigu | 1,0 prósent — undir suðmörkum. *(Hluti leigunnar fellur samt hér, en sem DAUÐ köll: 310 af 556, af því þau bera ekkert fastnúmer — ekki af því þau eru leiga.)* |

---

## MÆLINGARFYRIRVARAR

- **Sían er FRESTUN, ekki brottfelling.** Verkefnaskráin er endurmetin á hverri
  nóttu; leysist `fastnum` eða breytist `category`, birtist röðin aftur.
- **Nefnarinn hreyfist.** 9.037 er mælt 12.08; cc130 mældi 9.112 kl. 00:10 sama
  dag. Prósentutölurnar eru stöðugar en heildar-dollaratalan hreyfist með
  biðröðinni.
- **`category` er skröpuð merking, ekki eignaskrá.** cc130 bókaði að
  index-endapunktar ljúga; varðhliðið á `canonical_code` er einmitt vörnin gegn
  því og það greip 67 raðir.
- **892-talan (eignir sem missa eigindi) er á biðröðinni eins og hún er í dag**,
  ekki spá um heildar-eigindatap yfir tíma.
- Mæliforritin liggja í scratchpad lotunnar (`cc150_formaeling.py`,
  `cc150_formaeling2.py`, `cc150_formaeling3.py`, `cc150_sonnun.py`,
  `cc150_sql_prof.py`) — öll read-only.
- **Ósnert í þessari lotu:** brúin, `fetch_extracted_listings_to_value`
  (cc134-sían óbreytt), `predictions*`, `valuation_tiers*`, tiers-vélar,
  `nightly_delta_chain.sh`, `--forward 200`-þakið.
