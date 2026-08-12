# γ-FORPRÓF — cc141, 12.08.2026 (READ-ONLY)

**Tilefni:** γ-hönnun borðsins (cc81 §9.1) — leiðrétting = `grunn × exp(γ·Σln(1+p_i))`,
klemmt á eftir. cc81 mældi γ á **þjálfunarþýði** (0,781 S0 / 0,610 S3) og setti
skilyrði: frysting + **mótpróf á öðru þýði** + holdout utan þjálfunar beggja
líkana. Þetta forpróf sker úr hvort γ > 0 yfirhöfuð á **raunverulegum
þinglýstum sölum** og skilar kvörðunarþýðinu sem mótprófið þarf.

**BANN virt:** engin skrif í gagnagrunn (tengingin `set_session(readonly=True)`),
`lib/leidretting.js` og extraction-kóði aðeins lesin, engu lagi breytt.

**Mælitæki (committað, `precompute` @ `f20140d`):**
`cc141_thydi.py` · `cc141_lag.mjs` · `cc141_loader.mjs` · `cc141_gamma.py`
**Útkoma (utan git, `precompute/data/cc141/`):**
`cc141_inntak.json` · `cc141_lag.json` · `cc141_punktar.csv` · `cc141_dreifirit.png` · `cc141_gamma.json`

---

## 1. AÐFERÐ — hvað var kallað og hvað var speglað

**Ekkert var speglað.** Þrjár reglur keyrðu orðrétt:

| Regla | Hvernig hún var keyrð |
|---|---|
| útdráttur → eigindi | `scraper.eigindi_ur_extraction(ext, canonical_code)` — sama fall og `bru_extraction_i_eigindi` kallar. IMMUTABLE, engin skrif. |
| val/forgangur eiginda | `lib/attributes-queries.getAttributes(fastnum, klient)` með **minnis-klienti** (cc136-mynstrið) — uppruna-forgangur, já-hlutdrægnisían og nýbyggingarregla lagsins keyra eins og í framleiðslu. |
| leiðréttingin | `lib/leidretting.reiknaLeidrettingu` ÓBREYTT. |

**Hvar þakið var aftengt (bókað):** hvergi í vörunni. Fallið skilar `lidir[]`
með **óklemmdu** `pct`; klemman býr aðeins í `breyting_pct`. Óklemmda summan er
endurreiknuð í mælikóðanum úr þeim sama lista:
`summaLog = Σ ln(1 + pct/100)` (`cc141_lag.mjs` l. 137) — nákvæmlega sama lína
og cc136 notaði. Þakið er einfaldlega ekki lesið.

**Tengingin útdráttur ↔ auglýsing** er lykill vélarinnar sjálfrar:
`e.lysing_hash = substr(md5(l.lysing), 1, 12)`.

**Ein bókuð víkkun frá brúnni.** Brúin les aðeins **virka** auglýsingu
(`v_eign_virk_auglysing`). Þau 4.000 eigna mengi ber aðeins **46** sölur eftir
auglýsingadegi — eign sem **seldist** er einmitt eignin sem hverfur úr virka
menginu. Hér er lesið úr `scraper.listings` **án status-síu** (active +
withdrawn). Vörpunarfallið er óhreyft; inntakið er breikkað.

---

## 2. ÞÝÐIÐ — nefnarar í hverju þrepi

| Þrep | n (sölur) | Athugasemd |
|---|---|---|
| hrápör (útdráttur × sala, sala > auglýsingadagur) | **284** | 283 eignir |
| − ónothæfur samningur (`onothaefur = 1`) | 252 | −32 |
| − fleiri en ein sala per eign (fyrsta valin) | 251 | 1 eign bar tvær |
| − `canonical_code` EXCLUDE/NULL (cc134) | 242 | −9 |
| − **nýbygging við sölu** (byggár ≥ söluár − 2) | **166** | **−76 (31,4 %)** |
| − verðsía (kaupverð vantar) | 166 | −0 |
| berandi ≥ 1 BIRTANLEGAN lið | **164** | 2 báru ekkert |
| + spá í eigin árgangi | **163** | 1 utan spátöflu |

**Sundurliðun eftir canonical_code** (n / miðgildi daga augl.→sölu / x-miðgildi):

| kóði | n | dagar | x (log-summa) |
|---|---|---|---|
| APT_FLOOR | 110 | 31 | +0,098 |
| SFH_DETACHED | 23 | 32 | +0,238 |
| ROW_HOUSE | 15 | 46 | +0,252 |
| SUMMERHOUSE | 8 | 36 | +0,225 |
| APT_BASEMENT | 4 | 36 | +0,075 |
| SEMI_DETACHED | 2 | 146 | +0,193 |
| APT_ATTIC | 1 | 15 | +0,089 |

**Bil auglýsingar → sölu:** miðgildi **32 dagar** (p25 20, p75 59).

**Spá-árgangar** — valinn er síðasti árgangur sem var **lifandi** þegar salan
var þinglýst (heimild DECISIONS.md):

| gluggi | tafla | model_version | n |
|---|---|---|---|
| < 2026-06-30 | `predictions_2026_04` | iter4_final_v1 | 100 |
| < 2026-07-16 | `predictions_2026_07_pre_iter4r` | iter4_final_v1+segcal_fb | 8 |
| < 2026-08-06 | `predictions_2026_08_pre_cc78` | iter4r_20260716 | 36 |
| ≥ 2026-08-06 | `predictions` | iter4r_20260805_reglaR_strukt | 19 |

**OOS-staða.** Árgangs-reglan tryggir að spáin varð til fyrir söluna; þar með er
salan utan þjálfunargagna þess árgangs. Eina undantekningin eru **5 sölur ≤
2026-04-21** (eldri en apríl-líkanið sjálft) — þær eru innan þjálfunar og eru
teknar út í `hreint OOS`-specinu að neðan.

**Krossmæling við cc136:** þakið bítur á **74 af 164 berandi = 45,12 %**.
cc136 mældi 46,23 % á öðru (og stærra) mengi með sama tæki — samhljóða.

---

## 3. γ-TAFLAN

`y = log(þinglýst raunverð) − log(grunnspá árgangsins)`,
`x = ÓKLEMMD log-summa = Σ ln(1+p_i/100)`, `y = a + γ·x + e`. HC3-robust SE.

Lýsandi: `x` meðaltal **+0,1393**, sd 0,0920, spönn −0,130 … +0,444.
`y` meðaltal +0,0047, sd **0,1665**, spönn −0,820 … +0,654.

| spec | n | γ | SE | 95 % CI | R² | z vs 1 |
|---|---|---|---|---|---|---|
| **OLS y_real ~ x (aðalspec)** | **163** | **+0,633** | 0,161 | **[+0,317, +0,949]** | 0,122 | −2,28 |
| + árgangs-fixed-effects | 163 | +0,608 | 0,177 | [+0,261, +0,955] | 0,145 | −2,21 |
| + dagar (augl.→sala) | 163 | +0,632 | 0,165 | [+0,308, +0,955] | 0,123 | −2,23 |
| y_nominal ~ x | 163 | +0,602 | 0,166 | [+0,277, +0,927] | 0,111 | −2,40 |
| **Theil-Sen (miðgildishalli)** | 163 | **+0,499** | — | [+0,305, +0,698] | — | — |
| **Quantile q = 0,5** | 163 | **+0,528** | 0,096 | [+0,341, +0,716] | — | −4,93 |
| án `is_suspect_comparable` | 144 | +0,495 | 0,121 | [+0,258, +0,732] | 0,136 | −4,17 |
| án þak-eigna | 90 | +1,030 | 0,560 | [−0,069, +2,128] | 0,110 | +0,05 |
| **aðeins sala > 2026-04-21 (hreint OOS)** | 158 | **+0,542** | 0,144 | [+0,259, +0,825] | 0,090 | −3,17 |
| án SUMMERHOUSE | 155 | +0,706 | 0,168 | [+0,377, +1,034] | 0,150 | −1,76 |
| + fjölskyldu-fixed-effects | 163 | +0,463 | 0,242 | [−0,011, +0,936] | 0,154 | −2,23 |
| **STRANGT (OOS + án sumarhúsa + án suspect)** | **135** | **+0,549** | 0,129 | **[+0,296, +0,802]** | 0,163 | −3,50 |

**Þrjú svör sem standa yfir alla speca:**

1. **γ > 0 — afgerandi.** p ≤ 0,0006 í hverjum einasta spec. Liðirnir bera
   raunverulega upplýsingu um sölufrávikið; lagið er ekki hávaði.
2. **γ < 1 — staðfest.** z-gildi −1,8 til −4,9. Stöflunin **ofmetur**, alveg eins
   og cc81 mældi á allt öðru þýði.
3. **Miðgildisaðferðirnar liggja lægra en OLS** (0,499 / 0,528 gegn 0,633) — halarnir
   toga γ **upp**, ekki niður. Robustness-krafa liðar 3 er uppfyllt og hún færir
   svarið nær cc81-S3 (0,610), ekki frá því.

**Samleitni við cc81 er sjálfstæð.** cc81 mældi á þjálfunar-pkl í hedónískum
ramma; cc141 mælir á raunverulegum þinglýstum sölum gegn grunnspá sem varð til
á undan sölunni. Ólíkt þýði, ólíkt mælitæki, ólíkur estimand —
**0,610 (cc81-S3) fellur inn í CI allra tólf speca hér.**

---

## 4. SUNDURLIÐUN (n < 30 → mat sleppt)

| sneið | n | γ | 95 % CI |
|---|---|---|---|
| formerki = **jákvæð** | 160 | +0,512 | [+0,225, +0,798] |
| formerki = **neikvæð** | **3** | — | **n < 30, mat sleppt** |
| fjölskylda = FJÖLBÝLI (APT*) | 115 | +0,529 | [−0,212, +1,270] |
| fjölskylda = SÉRBÝLI (SFH/ROW/SEMI) | 40 | +0,500 | [−0,211, +1,211] |
| fjölskylda = ANNAÐ (sumarhús) | 8 | — | n < 30, mat sleppt |
| þriðjungur T1 (x −0,130…+0,092) | 55 | +2,120 | [+0,709, +3,532] |
| þriðjungur T2 (x +0,092…+0,162) | 54 | +1,304 | [+0,230, +2,378] |
| þriðjungur T3 (x +0,164…+0,444) | 54 | +0,546 | [−0,325, +1,418] |

**Fjölskyldurnar tvær gefa nánast sama γ (0,53 / 0,50) — hallinn er því ekki
samsetningar-artefakt.** Þetta þrátt fyrir að x sé rúmlega tvöfalt hærra á
sérbýli (+0,238) en fjölbýli (+0,098).

### 4b. LÖGUNIN — þriðjunga-bindin (það sem borðið á að lesa)

| þriðjungur | n | x meðaltal | y meðaltal | y ±SE | y/x |
|---|---|---|---|---|---|
| T1_lág | 55 | +0,0501 | **−0,0240** | 0,0214 | −0,48 |
| T2_mið | 54 | +0,1259 | **−0,0268** | 0,0142 | −0,21 |
| T3_hátt | 54 | +0,2435 | **+0,0656** | 0,0281 | +0,27 |

**Milli-bindja hallinn er ekki flatur:** T1→T2 er `Δy/Δx = −0,04` (engin svörun),
T2→T3 er `+0,78`. Svörunin er **kúpt**: neðri tveir þriðjungar summunnar bera
enga mælanlega svörun, efsti þriðjungurinn ber ~0,8. Innan-þriðjungs-hallarnir
(2,12 / 1,30 / 0,55) mæla annað og eru þröngskornir í x — milli-bindja myndin er
áreiðanlegri lestur. **Þetta er sjálfstæð vísbending um að flatur γ sé rangt form,
í sömu átt og cc81 §9 (A) en með öfugu formerki: cc81 fann há-N ofmetið, cc141
finnur lág-x svörunarlaust.** Hvorugt lagast með einni tölu.

---

## 5. NEIKVÆÐI ENDINN — sjálfstæð niðurstaða

**Aðeins EIN neikvæð lína er til í stuðlaskránni** (`needs_immediate_work`,
−13,3 %). Hún kviknar á **5 af 164 eignum (3,0 %)** og aðeins **3** eignir bera
nettó-neikvæða summu (−8,73 % / −8,22 % / −12,19 %).

Þetta staðfestir skilyrði cc81 §9.3 liðar 2b beint úr gögnum: **þetta þýði getur
ekki mælt neikvæða endann og mun ekki geta það.** γ mælt hér er kvarði á
**jákvæða stöflun** — nákvæmlega sami annmarki og cc81 bókaði. Sé γ látið gilda
í báðar áttir er −13,3 %-línan færð inn fyrir −13,0 %-klemmuna og
klemmumerkið hverfur af þeim eignum sem eru í verstu ástandi, án nokkurrar
mælingar sem styður það.

**Tíðni línanna í þýðinu** (efstu): `svalir` 84,8 % · `opid_rymi` 61,0 % ·
`lod_sudur` 41,5 % · `bad_uppgert` 39,0 % · `gardur` 37,8 % ·
`golfefni_uppgert` 36,6 % · `verond_pallur` 35,4 % · `storar_svalir` 34,8 % ·
`eldhus_uppgert` 32,3 %. Miðgildi liða per eign = **6**, meðaltal 5,75.

---

## 6. SPÁDÓMUR BORÐSINS — DÆMDUR

**(a) „γ < 0,5 á heildinni"** → **ÓDÆMD.**
γ = +0,633, 95 % CI [+0,317, +0,949]. Bilið nær yfir 0,5, svo hvorki fall né
stand. Punktmatið liggur **yfir** 0,5 í OLS og **við** 0,5 í miðgildisaðferðum
(0,499 / 0,528). Nákvæmlega: **γ = 1 er hafnað; γ = 0,5 er það ekki.**

**(b) „jákvæði endinn ber lægra γ en sá neikvæði"** → **ÓDÆMANLEG.**
n(x < 0) = **3**. Ekki 30, ekki 300. Spurningin er ekki illa mæld — hún er
ómælanleg í þessu þýði (§5). **Sjálfstæð niðurstaða: já-hlutdrægni þýðisins er
alger — 160 af 163 bera jákvæða summu.**

---

## 7. BER ÞÝÐIÐ MÓTPRÓF? — NEI, EKKI EITT OG SÉR

**Skiptingar (mælt, ekki áætlað):**

| skipting | n | γ | 95 % CI |
|---|---|---|---|
| sala < 2026-06-15 | 47 | +0,810 | [−0,012, +1,632] |
| sala ≥ 2026-06-15 | 116 | +0,568 | [+0,249, +0,887] |
| fastnum jafn | 77 | +0,405 | [+0,033, +0,776] |
| fastnum oddatala | 86 | +0,796 | [+0,317, +1,274] |

Slembihelmingarnir tveir gefa 0,41 og 0,80 — **munur upp á tvöfalt, á sömu
gögnum, af hreinni tilviljun.** Þýðið þolir ekki skiptingu.

**Kraftgreining** (SE(γ) ≈ sd(e)/(sd(x)·√n), sd(e) = 0,157, sd(x) = 0,092):

| n | SE(γ) | 95 % CI hálfbreidd |
|---|---|---|
| 163 (í dag) | 0,133 | ±0,261 |
| 300 | 0,098 | ±0,192 |
| 500 | 0,076 | ±0,149 |
| 1.000 | 0,054 | ±0,105 |
| 5.000 | 0,024 | ±0,047 |

- n sem þarf til að hafna γ = 1 (m.v. γ ≈ 0,63): **~82** → **náð**.
- n sem þarf til að hafna γ = 0,5: **~629** → **vantar ~4× þýðið**.

**Vöxtur þýðisins.** Nýtanlegar sölur eftir mánuðum í hrámenginu: apríl 8,
maí 29, júní 77, júlí 57, ágúst 27 (mánuður hálfnaður). ~40–70 hrápör á mánuði
→ ~25–45 nýtanleg eftir síur. **n = 629 næst ekki fyrr en eftir ~12–18 mánuði**
af óbreyttri söfnun.

**Stóra þýðið sem er TIL og af hverju það dugar ekki óbreytt.**
`public.last_listing_text` ber **51.834 pöruð sölu-söluyfirlit** (37.671 eignir)
sem standast nákvæmlega sömu síur og §2 — 300× stærra þýði. **En 0 þeirra er
þinglýst eftir 2026-04-21**, þ.e. **allar liggja innan þjálfunargagna
apríl-líkansins og allar spár urðu til EFTIR söluna.** Að keyra γ þar væri brot á
lið 3 lotubréfsins og á cc81-skilyrðinu um holdout utan þjálfunar beggja líkana.
Sá vegur er **fær en dýrari**: útdráttur hefur aðeins verið keyrður á ~50 af
44.418 eignum, og hann er gagnslaus fyrir γ nema samhliða komi líkan þjálfað án
þeirra sölna. **Það er endurþjálfunar-verk, ekki forpróf.**

---

## 8. HVAÐ ÞETTA FORPRÓF SKER ÚR — OG HVAÐ EKKI

**SKER ÚR:**
1. **γ > 0.** Liðirnir spá raunverulegu sölufráviki. Yfir alla tólf speca, p ≤ 0,0006.
2. **γ < 1.** Stöflunin ofmetur á raunsölum, ekki bara á þjálfun. Sjálfstæð
   staðfesting cc81 á öðru þýði, öðru mælitæki og öðrum estimand.
3. **Kvörðunarþýðið er til og er mælt** — 163 raðir, hreint OOS, allir nefnarar
   birtir, hrámyndin á disk.
4. **Neikvæði endinn er ómælanlegur hér** (n = 3) — cc81-skilyrði 2b stendur
   óhaggað og verður ekki lokað af þessari leið.

**SKER EKKI ÚR:**
1. **Hvaða γ.** [+0,317, +0,949] er of breitt til að velja tölu.
   Miðgildisaðferðirnar (0,50–0,53) og strangasti specinn (0,55) benda á neðri
   helming bilsins, en það er vísbending, ekki val.
2. **Hvort formið sé rétt.** Þriðjunga-bindin (§4b) benda á **kúpta** svörun —
   flatur γ er þá réttur meðaltalskvarði á röngu formi, sama athugasemd og cc81
   §9 liður 1 gerði um einstakar línur.
3. **Mótprófið sjálft.** Þýðið þolir ekki skiptingu (§7).

---

## 9. TILLAGA TIL BORÐSINS (engin framkvæmd, HALT)

1. **γ fer ekki inn núna.** Bilið leyfir ekki val og formið er grunsamlegt.
2. **Vaxtarleiðin er ódýr og sjálfvirk:** endurkeyra cc141_thydi/lag/gamma
   mánaðarlega á sama tæki. n ≈ 300 í kringum áramót, n ≈ 629 vorið 2027.
   Ekkert nýtt þarf að smíða.
3. **Neikvæði endinn þarf sína eigin mælingu**, ekki þessa (§5).
4. **Kúpta formið verðskuldar sína eigin spurningu** áður en flatur γ er valinn:
   ber lág-x svörunarleysið vitni um að neðstu liðirnir séu rangir frekar en að
   kvarðinn sé rangur? Það er (A)-verkið úr cc81 §9, ekki γ-verkið.

**Kvörðunarþýðið stendur skjalfest og endurkeyranlegt. Ekkert var flippað,
engin tala fór í stuðlaskrá, ekkert var skrifað í gagnagrunn.**

---

## VIÐAUKI (cc144, 12.08) — LEIÐRÉTTING Á §3: „p ≤ 0,0006 Í HVERJUM EINASTA SPEC" HELDUR EKKI Í TVEIMUR AF TÓLF

Þessi viðauki er **eina viðbót cc144**; engri línu að ofan var hreyft og engin tala
endurreiknuð — leiðréttingin er lesin **beint úr töflunni í §3**.

§3 liður 1 segir: *„γ > 0 — afgerandi. p ≤ 0,0006 í hverjum einasta spec."* Tveir specar
í sömu töflu bera **95 % CI sem nær yfir núll** og geta því ekki borið p ≤ 0,0006:

| spec | n | γ | SE | 95 % CI | z vs 0 | p vs 0 |
|---|---|---|---|---|---|---|
| án þak-eigna | 90 | +1,030 | 0,560 | **[−0,069, +2,128]** | 1,84 | **≈ 0,066** |
| + fjölskyldu-fixed-effects | 163 | +0,463 | 0,242 | **[−0,011, +0,936]** | 1,91 | **≈ 0,056** |

**Rétt orðalag: γ > 0 í 10 af 12 specum við p ≤ 0,0006** (efra markið er árgangs-fixed-
effects, z = 3,44, p ≈ 5,9·10⁻⁴ — þaðan kemur talan 0,0006). **Í hinum tveimur er γ > 0
ekki marktækt á 5 %.**

**Efnisleg niðurstaða §8 liður 1 stendur samt**, og það er ekki afsökun heldur mælanleg
ástæða: bæði punktmötin eru **jákvæð**, og þetta eru einmitt specarnir tveir sem taka
mestan x-breytileika út — „án þak-eigna" fjarlægir 74 af 164 og með þeim há-x halann
(sd(x) fellur, SE hleypur upp í 0,560), og fjölskyldu-fixed-effects gleypa
milli-fjölskyldu-breytileikann sem §4 mældi (x +0,238 sérbýli á móti +0,098 fjölbýli).
**Það er kraftmissir, ekki formerkjaskipti.**

Fullyrðingin sem fer í DECISIONS (§5D-6) er því sú leiðrétta, ekki §3-orðalagið.
Hvorug tala breytir §6 (γ = 1 hafnað, γ = 0,5 ódæmt), §7 (þýðið þolir ekki skiptingu)
né tillögunni í §9 (γ fer ekki inn núna).
