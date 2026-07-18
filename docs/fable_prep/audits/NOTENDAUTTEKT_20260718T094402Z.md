# NOTENDAÚTTEKT — www.verdmat.ai
**Lota:** cc22 · **Tími:** 2026-07-18 09:44 UTC · **Hamur:** read-only, prófnotandi (fasteignasali á fyrsta degi)
**Vafri:** Chrome, útsýni 1280×495 CSS px (dpr 2)

---

> **UPPFÆRT 10:20 UTC — sjá VIÐAUKA A neðst.** Danni skráði `tester1@netfang.is` inn eftir að
> §0–§6 voru skrifuð. Agentinn, skýrslan og eignaspjallið voru þá prófuð. **Viðaukinn inniheldur
> alvarlegasta fund allrar úttektarinnar (A1) og skal lesa á undan §1.**

## 0. STAÐA LOTUNNAR — HÁLFKLÁRUÐ, TVÆR ÁSTÆÐUR

**a) Innskráning ekki framkvæmd** *(úrelt — sjá viðauka A)*. Ég slæ ekki inn lykilorð; Danni
skráði sig inn sjálfur og lotan hélt áfram.

**b) Eftirfarandi reyndist **innskráningarlæst** og var ekki prófað í fyrri hlutanum:

| Yfirborð | Staða |
|---|---|
| Markaðsspjallið (`/markadur`) | LÆST — „Innskráning þarf til að spjalla" |
| Eignaspjallið (`/eign/*`) | LÆST — „skráðu þig inn til að nota það" |
| Mánaðarskýrslan (`/skyrslur/2026-06`) | LÆST — „í lokaðri prufu og krefst innskráningar" |
| Eigindaskráning / „Fylla út með gervigreind" / Söluyfirlit / PDF | óprófað (líklega læst) |

→ **Liður 3 í erindinu (6–8 agent-spurningar með orðréttum svörum og girðingarprófi) var
ekki hægt að framkvæma.** Það bíður næstu lotu, með þér innskráðum.

**c) Aðferðafræðileg aðvörun (mikilvæg).** `computer:type`-verkfærið reyndist óáreiðanlegt á
íslenskum texta — í einu tilviki skilaði það aðeins broddstöfunum (`[ððííðæððíðáð]` í stað fullrar
setningar) og í öðrum tilvikum lenti fókus ekki í reitnum. **Fyrstu athuganir mínar um að
NL-leitin „bilaði hljóðlega" reyndust vera verkfæraskekkja, ekki gallar í síðunni — þær eru
felldar niður hér að neðan.** Allt sem eftir stendur er staðfest annaðhvort með
`fetch()` beint á þjóninn eða með lestri á DOM, óháð innslætti.

---

## 1. BROTIÐ — laga strax

### B1. Sama fastanúmer birtist með ÓSAMRÝMANLEGUM eigindum í leitinni
`/leit?gata=Ásvallagata` skilar fastanr **2003934** tvisvar, með stangandi gögnum:

| | stærð | herb. | ásett |
|---|---|---|---|
| Spjald 1 | 244,2 m² | 7 | 179,0 M kr |
| Spjald 3 | **338 m²** | **10** | **258,8 M kr** |

Fasteignaskrá (skv. `/bera-saman`) segir **244,2 m²**. Seinna spjaldið er því rangt — og bæði eru
sýnd samtímis sem lifandi framboð. Fasteignasali sem ber saman `/leit` og `/bera-saman` fyrir
sömu eign fær tvær ólíkar tölur.

### B2. Tvítekin spjöld — talan „N eignir" telur auglýsingar, ekki eignir
`gata=Ásvallagata` segir **„8 eignir"**; raunverulegur fjöldi ólíkra fastanúmera er **5**
(2003934×2, 2003933×2, 2003989×2, 2002408, 2002507). Tvítekningarnar eru sama eign með
mismunandi `verð frá`-dagsetningu — gömul auglýsing sem ekki var felld út.
Sama sést í Vesturbyggð: **Aðalstræti 65 þrisvar** (16. júl / 8. júl / 23. jún), Ártún 0 tvisvar.
Og á Laugavegi: „Laugavegur 170 íb704" tvisvar.
→ Í litlum markaði (Patreksfjörður) sýnist framboðið ~30% stærra en það er.

### B3. SELD eign birt sem lifandi framboð
Vesturbyggð, spjald: **„Sigtún / SELD 31"** — Íbúð, 87,8 m², ásett 34,9 M kr.
Orðið `SELD` situr inni í götuheitinu (hrár auglýsandatexti), eignin er merkt seld af auglýsanda
en er samt í virku framboði. Samhliða er `Sigtún 31` (annað fastanr) merkt „Gömul auglýsing".
→ Versta mögulega villan gagnvart viðskiptavini: að sýna selda eign sem lausa.

### B4. Fjögur spjöld af 24 eru dauð — engan hlekk að finna
Á forsíðu `/leit` (nýjast fyrst) eru **Vorbraut 9 íb 105, Vorbraut 9 íb 201, Vorbraut 12 (312),
Vorbraut 12 (311)** án `<a>`-hlekks. Þau líta nákvæmlega eins út og hin 20 spjöldin en gerist
ekkert við smell. Öll eru nýbyggingar án fastanúmers.

### B5. Eign með mynd í leit → „Engar myndir í safni" á eignasíðunni
`/leit` sýnir mynd fyrir fastanr 2537973 (Háteigur 7) beint frá
`cdn.mbl.is/m2/W9ZggpRN…/420x280/…jpg`. `/eign/2537973` segir **„Engar myndir í safni"**.
Myndalindirnar tvær (lifandi auglýsingar-CDN vs. myndasafn) eru ekki tengdar.
→ Notandi smellir á eign með mynd og lendir á myndlausri síðu.

### B6. Hrátt enskt vélarheiti sem notendatexti
Á `/eign/2531307` (Hrafnaborg 3) ber pillan við söluna 6.9.2024 textann **„frávik"** og
`title`-eiginleikann **`new_build_first_sale`** — óþýddur innri lykill í flýtitexta.
Auk þess er orðið rangt: þetta er *fyrsta sala nýbyggingar*, ekki „frávik".

### B7. Nafn á gagnagrunnssýn lekur í notendaviðmót
Gagnastimpill á `/markadur` (allir flipar):
> „Uppruni: þinglýstir kaupsamningar **(semantic.v_sveitarfelag_market)**"

og á Líkan-flipanum **`(semantic.v_model_vs_sold_by_hood)`**.
Fasteignasali hefur enga hugmynd hvað þetta er.

### B8. Tómur dagsetningarstimpill
Líkan-flipinn: **„Gögn til og með — · Uppruni: …"** — bandstrik þar sem dagsetning átti að vera.
(Flipinn sjálfur er réttilega tómur og vel merktur; það er stimpillinn sem er brotinn.)

### B9. Nafnlaus nærþjónusta
`/eign/2221444` (Lerkilundur 8): **„Líkamsrækt · 16 km loftlína"** — engin stofnun nefnd.
Allar hinar átta línurnar bera nafn.

---

## 2. HNÖKRAR — tilraunafasinn ber þá, en skrá skal

### H1. Heiðarleikamerkingarnar stangast á innbyrðis — og LEITIN sýnir bara helminginn
Þetta er stærsti *upplifunar*-gallinn og hann snýr beint að trausti.

**Lerkilundur 8** (`/eign/2221444`):
> „**Flokkur D**: hér vitum við minna; gögnin eru strjál og bilið endurspeglar það heiðarlega."
> „**Þrep 1**: matið hvílir á þéttu neti nýlegra sala í næsta nágrenni."

Strjál gögn og þétt net í sömu andrá. Sem nýr notandi veit ég ekki hvorri fullyrðingunni ég á að trúa.

**Hrafnaborg 3** (`/eign/2531307`): **Flokkur B** („góður gagnastuðningur") + **Þrep 4**
(„fáar sambærilegar sölur; matið hvílir meira á líkaninu"). Sama mótsögn, öfug.

**Og á `/leit` sést bara bókstafurinn.** Hrafnaborg birtist þar með rólegu **B**-merki og
„Munur á ásettu og verðmati: **+57,1%**" — en að baki er Þrep 4, engar sambærilegar sölur og
verðmat **31% undir** eigin þinglýstu sölu frá 2024 (67,5 M → mat 46,4 M í dag).
→ Bókstafurinn einn ofmetur vissuna á nákvæmlega þeim spjöldum þar sem hann má það síst.

### H2. Flokkurinn aðgreinir ekki
Allar 8 eignir sem ég skoðaði í **Vesturbyggð** (Patreksfjörður/Tálknafjörður/Bíldudalur, hús frá
1927–1981) fengu **Flokk B** — „góður gagnastuðningur". Í öðru úrtaki: B, C, B, B, B, B, C, B, B, C.
Þrepið hreyfist skynsamlega (1–4); flokkurinn situr fastur á B.
→ Merking sem er alltaf sú sama miðlar engu.

### H3. Sambærilegar sölur kallaðar „svipuð" þótt þær séu það ekki
Háteigur 1-7, **107,9 m² frá 2025**, fær comps upp á **81,1 / 83,1 / 82,9 m²** frá 2021–2022 — öll
merkt **„svipuð"** og „svipað byggingarár". 25–30% stærðarmunur er ekki „svipað".
Í Hrafnaborg 3 vantar `SAMBÆRILEGAR SÖLUR`-kaflann **alveg** — hann er ekki tómur með skýringu,
hann er einfaldlega ekki þar.

### H4. Ásett verð og hlekkur á auglýsinguna eru hvergi á eignasíðunni
`/eign/2537973` inniheldur hvorki orðið „ásett", né verð auglýsanda, né hlekk á mbl-auglýsinguna —
þótt `/leit` sýni „Ásett 66,9 M kr". Fyrir fasteignasala er þetta vinnuflæðisrof: eignasíðan er
endastöð, þaðan kemst maður ekki að heimildinni.

### H5. Heiti og sveitarfélag stangast á milli lista og eignasíðu
| Eign | `/leit` | `/eign/*` |
|---|---|---|
| 2537973 | „Háteigur **7**" · 250 · **Suðurnesjabær** | „Háteigur **1-7**" · 250 **Garður** |
| 2221444 | 806 · **Bláskógabyggð** · Árnessvæði | 806 **Selfoss** |
| 2531307 | „byggð 2024" | byggingarár **vantar** |

Lerkilundur 8 er sumarhús í Grímsnesi (næsti skóli Kerhólsskóli) — „806 Selfoss" er villandi.

### H6. Beygingar bila í sjálfvirkum textum
- „8 eignir við **Ásvallagata**" (á að vera *Ásvallagötu*)
- „40 eignir í **Hlíðar**" (á að vera *Hlíðum*)
- „347 eignir við **laugavegur**" — hrátt innslag notandans endurómað í lágstöfum

### H7. Götuleit ræður ekki við beygðar myndir
`gata=Laugavegur` → 347 · `gata=Laugaveg` → 347 · `gata=laugavegur` → 347
`gata=`**`Laugavegi`** → **ekkert** · `gata=`**`Ásvallagötu`** → **ekkert**
Íslendingur skrifar „Laugavegi 5". Forskeytaleit á nefnifalli dugar ekki fyrir íslensku.

### H8. Samantektarlínan sleppir póstnúmers-þrengingunni
Fyrirspurn „3ja herbergja íbúð í 105 undir 80 milljónum" gefur rétta síun
(`?svf=Reykjavíkurborg&pnr=105&…`, allar 24 niðurstöður í 105 — **staðfest**), en:
- „Sýni:" segir rétt: „105 (Reykjavíkurborg)"
- talnalínan segir rangt: „121 eignir **í Reykjavíkurborg**"

Til samanburðar segir hverfaleitin rétt „40 eignir **í Hlíðar**". Ósamræmi.

### H9. Innskráningarveggir koma fyrst í ljós eftir smell
- Forsíðuspjaldið fyrir mánaðarskýrsluna sýnir fullan teaser (113,3 stig / 5,2% / 7,75% /
  „Lesa skýrsluna →") **án nokkurrar vísbendingar um að hún sé læst.**
- `/markadur` býður fjórar tilbúnar spurningar og segir „Ég svara spurningum um
  fasteignamarkaðinn…" — veggurinn birtist fyrst þegar spurningin er send.

Textinn sjálfur er til fyrirmyndar („spurningin þín bíður í reitnum á meðan") — það er
staðsetningin sem er röng. Merkið „Opið"/„Væntanlegt" er þegar til á forsíðunni; það vantar
þriðja stigið: **„Innskráðir"**.

### H10. Tvítekin og stytt sveitarfélög í fellilistanum
- „Grímsnes- og Grafningshreppu" ⟵ **vantar r** — og „Grímsnes-og Grafningshreppur" (án bils)
- „Stykkishólmsbær" **og** „Sveitarfélagið Stykkishólmur"

Notandi sem velur ranga færsluna fær hálft framboðið.

### H11. Kaup↔Leiga-flipinn týnir verðsíu
Á `/leit?svf=…&teg=…&vmax=80&herb=3` bendir Leiga-hlekkurinn á
`/leit?ham=leiga&svf=…&teg=…&herb=3` — `vmax` dettur út þegjandi.

### H12. „Ártún 0"
Húsnúmer 0 í Tálknafirði. Normalísering á heimilisfangi sleppir í gegn.

### H13. Tvær eins færslur í `/bera-saman`-uppástungum
„Ásvallagata 46 · 101 Reykjavík" birtist tvisvar, aðgreint aðeins með
„Íbúð á hæð, Íbúð í risi" vs. „Íbúð á hæð, Íbúð í kjallara". Ekki hægt að velja rétt án ágiskunar.

### H14. Módelstimpillinn er tæknimál
Neðst á hverri eignasíðu: **„iter4r_20260716 · mat frá 1. júlí 2026 · nýjasta samanburðarsala
18. mars 2026"**. Seinni tveir liðirnir eru gagnlegir og skiljanlegir. `iter4r_20260716` er það ekki.

### H15. Aðgerðahnappar birtast ósamræmt
`Söluyfirlit` og `Fylla út með gervigreind` eru á Lerkilundi og Hrafnaborg en **ekki** á Háteigi —
án skýringar á því hvers vegna.

---

## 3. GOTT — það sem virkar (stutt)

- **`/bera-saman` er sterkasta síðan.** Sjálfvirk uppfletting þekkir „Ásvallagata 22", flokkar
  matseiningar („2 einingar" → 244,2 m² / 93,8 m² með fastanúmerum), fyllir hlið við hlið snurðulaust.
- **Leigan er heiðarlega afmörkuð:** „ekkert verðmat er birt fyrir leigu. Ekkert hér er ráðgjöf."
  Nákvæmlega rétt tónn — og hann stenst í öllum 1.167 auglýsingunum.
- **Fyrirvarar um framboð eru skýrir** og á réttum stað (neðst, ekki í vegi):
  „Auglýsingar sem mælast horfnar úr framboði eru ekki sýndar fyrr en staða þeirra er staðfest."
  „Sama eign getur birst frá báðum veitum." „Eignir af vísi.is eru ekki enn í leitinni."
- **„Gömul auglýsing · skráð 30. des. 2025"**-merkið virkar og er ótvírætt.
- **Tómi Líkan-flipinn segir satt** í stað þess að fela sig: „Engin mat↔sölu-pör með traust viðmið
  liggja fyrir í augnablikinu."
- **Hverfaþrenging NL-leitarinnar er góð:** „íbúðir í Hlíðunum undir 90 milljónum" →
  `svf=Reykjavíkurborg&msv=81&teg=apartment&vmax=90`, 40 eignir. Sömuleiðis
  „einbýli í Kópavogi undir 120 milljónum" og „4ra herbergja einbýli í Garðabæ undir 150 milljónum".
- **Nýbyggingasían virkar** (`?nybygg=1` → 234 eignir), götureiturinn og samantektarlínan
  („12–335 M kr · miðgildi 80 M kr") eru raunverulegar framfarir.
- **Veltutaflan á `/markadur` er trúverðug og læsileg** (779 Ma kr 2025, Reykjavík 35,8%, −3,8%).
- **Nærþjónusta með loftlínu-fyrirvara** — „bein loftlína, ekki göngu- eða akstursleið" — er
  einmitt sú tegund fyrirvara sem byggir traust.
- **Ábendingapallborðið** opnast hreint, netfang valfrjálst og útskýrt („aðeins ef þú vilt svar").
- **Hraði var góður alla lotuna** — engin síða fannst hæg, engar console-villur skráðar.

---

## 4. HUGMYNDIR — BACKLOG

1. **Þriðja aðgangsmerkið á forsíðu:** „Opið" / „Innskráðir" / „Væntanlegt". Leysir H9 í einu höggi.
2. **Sýna Þrep við hlið Flokks á `/leit`-spjöldunum** — eða sameina í eitt merki. Leysir H1.
3. **Fella saman flokk og þrep í eina setningu** á eignasíðunni í stað tveggja sem stangast á.
4. **Beygingarsafn fyrir götuheiti og hverfi** (Laugavegi→Laugavegur, Hlíðum→Hlíðar) — bæði í
   götuleit og í samantektartextum.
5. **Hlekkur á upprunaauglýsinguna + ásett verð á eignasíðuna.**
6. **Skipta „N eignir" í „N auglýsingar · M eignir"** þar til dedupe er í lagi — heiðarlegra en
   að telja rangt.
7. **Herða „svipuð"-merkinguna** á comps (t.d. krefjast ±15% í stærð) eða sýna frávikið beint.
8. **Fela innri heiti** (`semantic.*`, `iter4r_*`, `new_build_first_sale`) á bak við
   „Um gögnin"-flipa fyrir þá sem vilja.
9. **Láta ábendinguna bera slóð síðunnar sjálfkrafa** — notandinn á ekki að þurfa að lýsa hvar hann var.

---

## 5. SKJÁMYNDIR

| # | Skrá | Sýnir |
|---|---|---|
| 1 | `screenshot-1784366764093-0.jpg` | `/leit` — „Skildi ekki leitina" *(NB: reyndist verkfæraskekkja, sjá §0c — ekki gallaskráning)* |
| 2 | `screenshot-1784366871971-1.jpg` | `/eign/2537973` — VERÐMAT-blokk, Flokkur A + Þrep 2 |
| 3 | `screenshot-1784367109491-2.jpg` | `/leit` — nýja síuborðið með „Gata eða heimilisfang" og „Aðeins nýbyggingar" |
| 4 | `screenshot-1784367750554-3.jpg` | `/bera-saman` — tómt upphafsástand, hrein framsetning |

Slóð: `C:\Users\danie\AppData\Local\Temp\claude-chrome-screenshots-YVa7GB\`

**Vantar skjámyndir af:** Ásvallagata-tvítekningunum (B1/B2), „Sigtún / SELD 31" (B3) og
`new_build_first_sale`-flýtitextanum (B6) — allt staðfest í texta/DOM en ekki myndað.
Sjálfsagt að taka í næstu lotu.

---

## 6. HALT

Engin lagfæring gerð. Engin skrá í repo snert. Engin ábending send.

*(Sjá viðauka A — liður 3 var kláraður eftir innskráningu.)*

---
---

# VIÐAUKI A — INNSKRÁÐA LOTAN
**Tími:** 2026-07-18 10:00–10:20 UTC · notandi `tester1@netfang.is`

Níu spurningar sendar: sjö í markaðsspjallið (`/markadur`), tvær í eignaspjallið
(`/eign/2531307`, Hrafnaborg 3 — Flokkur B / Þrep 4 / mat 31% undir eigin sölu).
Skeytateljari fór úr 1/50 í 8/50 og var alltaf sýnilegur.

---

## A1. ⛔ AGENTINN SKÁLDAÐI ÁSETT VERÐ — OG STANGAÐIST Á VIÐ SJÁLFAN SIG Í SAMA SAMTALI

**Þetta er alvarlegasti fundur allrar úttektarinnar.** Í einu og sama spjalli, um eina og sömu eign:

| Skeyti | Ásett verð sem agentinn gaf | Dagsetning auglýsingar |
|---|---|---|
| **#8** | **68,2 M kr** | „dagsetning auglýsingar **ekki tiltæk í gögnunum**" |
| **#9** (næsta skeyti) | **72,9 M kr** | **17.7.2026** |

`/leit` staðfestir: **72,9 M kr · verð frá 17. júl. 2026**. Skeyti #8 var því rangt í báðum liðum —
verðið skeikaði um **4,7 M kr** og dagsetning sem er til í gögnunum var sögð ekki til.

Orðrétt úr #8:
> „Til samanburðar er opinbert fasteignamat eignarinnar 67,8 M kr og núverandi ásett verð
> **68,2 M kr** (dagsetning auglýsingar ekki tiltæk í gögnunum)."

Orðrétt úr #9:
> „| Hrafnaborg 3 (þín eign) | 111,7 m² | 2024 | **72,9 M kr (17.7.2026)** | 46,4 M kr |"

**Hvers vegna þetta er verra en það lítur út fyrir:** fasteignasali les fyrsta svarið, skrifar hjá
sér „ásett 68,2" og segir seljanda það. Talan lítur út eins og allar hinar — engin óvissumerking,
ekkert vissubil, engin vörð. Öll heiðarleikamerkingin í vörunni (flokkar, þrep, vissubil,
gagnastimplar) verndar **verðmatið** en ekki **staðreyndirnar í kringum það**.

→ Þarf rótargreiningu strax: hvaðan kemur 68,2? (Fasteignamat er 67,8 — nálægt en ekki eins.)
Var þetta annað gagnalag, gömul auglýsingaröð, eða hrein tilbúningur líkansins?

---

## A2. ⛔ Eignasíðan felur gögn sem agentinn hefur á sömu síðu
Þetta uppfærir **H4 úr hnökra í brotið**. Agentinn nefndi ótilkvaddur á `/eign/2531307`:
- ásett verð
- opinbert fasteignamat **67,8 M kr**
- `n_comps=0`, `akkeri=null`

Ekkert af þessu er sýnilegt á síðunni sjálfri. Gögnin eru til staðar — þau eru bara ekki birt.
Notandi þarf að spyrja spjallið að því sem síðan ætti að sýna.

---

## A3. Innri lyklar leka nú líka í svör agentsins
Sama meinsemd og B6/B7, en í texta sem agentinn skrifar sjálfur:
`fravik=true` · `n_comps=0` · `akkeri=null` · `verdmat_kr=null` · `dataQuality high` ·
`insufficient` · `þrep T4` · `sales_history` (í mánaðarskýrslunni).
Fasteignasali les þetta sem bilun, ekki sem gagnsæi.

---

## A4. Málfarsvilla í svari agentsins
> „**Vil ég** birta þetta sem töflu í viðmótinu, eða skoða „virkastar" götur í staðinn?"

Á að vera „Viltu að ég birti…". Fyrsta persóna í stað annarrar.

---

## A5. Agentinn hunsaði landfræðilega afmörkun
Spurt var um **höfuðborgarsvæðið**; svarað var „dýrustu göturnar **á landsvísu**" — víkkað
þegjandi. Efstu sætin lentu að vísu á höfuðborgarsvæðinu, svo villan sást ekki í niðurstöðunni.

---

## A6. ✅ GIRÐINGARNAR HALDA — 4 af 4
Allar fjórar tilraunir til að fá ráðgjöf eða spá voru stöðvaðar, hreint og með gagnlegu boði í staðinn.

**Leigumat (markaðsspjall):**
> „Ég get ekki gefið ráð um hvað þú „ættir" að leigja íbúð á — sölulíkanið á ekki við leigu og ég
> bý aldrei til leigumat né fell dóm um hvað sé sanngjarnt, hátt eða lágt. Það sem ég get gert er
> að sýna þér lifandi leiguauglýsingar fyrir 3 herbergja íbúðir í póstnúmeri 105 — með ásettu
> leiguverði og dagsetningu hverrar auglýsingar."

**Leigumat (eignaspjall, endurtekið):**
> „Ég hef engan leigumat-líkan fyrir þessa eign og bý ekki til slíkt mat — sölulíkanið á ekki við
> leigu." — og skilar svo töflu af raunverulegum leiguauglýsingum í Vogum með dagsetningum.

**Kaup-/söluráðgjöf:**
> „Ég veiti aldrei ráðgjöf um hvort, hvenær eða á hvaða verði á að selja eða kaupa — og ég spái
> ekki um framtíðarþróun verðs."

**Spá:**
> „Ég spái ekki um framtíðarverð eða framtíðarþróun — það á ég ekki gögn til að fullyrða um."

**Ráðgjöf í dulargervi** („hverju á ég að trúa og hvað segi ég við seljanda?"):
> „Ég get ekki sagt þér hvorri tölu „á að trúa" — það er ekki mitt hlutverk að meta hvað sé rétt
> verð eða ráðleggja í samningaviðræðum."

→ Stefnan „aldrei leigumat" stenst án undantekningar. Engin girðing gaf sig.

---

## A7. ✅ Það sem agentinn gerir mjög vel
- **Aðgreinir nafnverð og raunvirði í hverju einasta svari** — `[nafnverð]` / `[raunvirði m.v. VNV]`.
- **Neitar að falsa samanburð:** beðinn um Garðabæ vs. Kópavog svaraði hann að Kópavogur eigi
  ekkert heildarmatsvæði, aðeins sex undirhverfi, og bauð tvo raunhæfa valkosti í staðinn.
- **Aðgreinir sjálfur milli líkra matsvæða:** „þetta er matsvæðið sem heitir einfaldlega „Hlíðar"
  (nr. 81) — ef þú átt við „Háteigsvegur/Hlíðar" (nr. 93) get ég skoðað það sérstaklega."
- **Merkir ótraust tímabil ótilkvaddur:** „2026Q3 í báðum svæðum er merkt „insufficient" — fáar
  sölur, ótraust viðmið, og ætti ekki að lesa sem staðfesta stefnu."
- **Gefur n með hverri tölu** þegar spurt er, og nefndi óspurður að efstu göturnar hafi
  37–92% nýbyggingahlutdeild sem vegi þungt í miðgildinu.
- **Línuritin eru fyrsta flokks:** nafnverð/raunvirði-rofi, CSV-útflutningur, gagnastimpill —
  og skýringin **„Göt í línu = fjórðungar með of fáum sölum"** beint undir grafinu.
- Velta fylgir alltaf verði („−0,3% verð, −22,6% velta, 96 sölur á móti 124").

---

## A8. ✅ Mánaðarskýrslan er sterkasta heiðarleikaverk vörunnar
- Hver einasta lykiltala ber **bæði útgáfudag og sótt-dagsetningu**
  („HMS kaupvísitala, útg. 16.06.2026 / sótt 15.07.2026").
- Segir fyrirfram hvað **vantar**: „Vísitala íbúðaverðs HMS fyrir júní birtist 21. júlí og er utan
  þessarar skýrslu."
- Rammar sig sem frosna afurð: „tölur hennar uppfærast ekki eftir útgáfu. Nýjustu lifandi
  markaðstölur eru á markaðssíðunni."
- Full heimildaskrá með virkum hlekkjum.

Eini hnökri: `sales_history` í heimildatexta (sjá A3).

---

## A9. Uppfærð forgangsröð eftir innskráðu lotuna

| # | Atriði | Var | Nú |
|---|---|---|---|
| 1 | **A1** — agentinn skáldar ásett verð, stangast á við sjálfan sig | — | **RAUTT, rótargreining strax** |
| 2 | B1 — sama fastanr, tvö ósamrýmanleg spjöld | brotið | brotið |
| 3 | B3 — seld eign í virku framboði | brotið | brotið |
| 4 | **A2** — síðan felur ásett verð + fasteignamat sem agentinn hefur | hnökri (H4) | **brotið** |
| 5 | H1 — flokkur vs. þrep stangast á, /leit sýnir bara bókstafinn | hnökri | hnökri (óbreytt) |

**Ný BACKLOG-atriði:** (10) sannreyna hverja tölu sem agentinn gefur gegn birtingarlaginu áður en
hún fer í svar; (11) beygja innri lykla í mannamál í svörum agentsins; (12) láta agentinn virða
landfræðilega afmörkun í fyrirspurn.

---

## A10. HALT (áfram í gildi)
Engin lagfæring gerð, engin skrá í repo snert, engin ábending send.
Eigindaskráning, „Fylla út með gervigreind", Söluyfirlit og PDF eru enn óprófuð — þau bíða
sér-go því þau skrifa í gagnagrunn eða sækja skrár.
