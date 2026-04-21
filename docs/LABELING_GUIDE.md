# LABELING_GUIDE — Hand-labeling leiðbeiningar fyrir gold-standard

**Útgáfa**: v0.1 (2026-04-18, aligned við EXTRACTION_SCHEMA v0.2.1)
**Tilgangur**: Concrete leiðbeiningar fyrir labeler sem hand-labelar 100 gold-standard listings. Þetta skjal er reference sem labeler hefur opið meðan hann labelar — lýsir hvernig á að lesa raun-lýsingu og fylla út hvern field systematically.
**Áætluð lesning**: 30 mín fyrst yfir; svo reference-use meðan labeling stendur yfir.

---

## Hvernig labeler á að vinna hvert listing

Mælst er með eftirfarandi röð per listing — ekki skylda, en dregur úr decision-fatigue og heldur consistency:

1. **Lesa alla lýsinguna í gegn einu sinni** áður en nokkuð er labelað. Fyrstu línur eru oft boilerplate („Glæsileg íbúð í ..."); raunverulegir detail koma oft neðar.
2. **Highlight mentally** (eða í athugasemdum á Google Sheet) allt sem vísar til framkvæmda, ástands, útsýnis, eða óvenjulegra features.
3. **Fylla út component-status matrix** — öll 18 components, í réttri röð (unit-level fyrst, svo building-level). Langflest verða `not_mentioned`.
4. **Fylla út situational fields** — útsýni, útipláss, parking, layout, building-annað.
5. **Negative signals** — lesa aftur með gagnrýnu auga, hefur eitthvað vandamál verið nefnt?
6. **Augl-supplement trilemmas** — fyrir þau 7 flagg sem gætu verið null í augl.
7. **Agent framing** — hvað var lead-ið? Hvað er tone-inn?
8. **Property narrative** — skrifa eigin 2–4 setninga samantekt á íslensku. Ekki copy-paste úr lýsingu.
9. **Meta + extraction_notes** — flagga ef eitthvað er óvenjulegt.
10. **Ef eitthvað er unclear**: nota `not_mentioned` og skrá athugasemd í `confidence_notes` column. **Ekki giska** — gisk spilla gold-standard sem benchmark.

---

## Kjarna-regla: status-enum decision tree

Þessi decision tree gildir fyrir **öll 18 components** í matrixinu. Hvern component-status flokkast í eitt af 7 values.

### Flow chart

```
Er component yfir höfuð nefndur í lýsingu?
│
├─ NEI → `not_mentioned`
│
└─ JÁ, nefndur einhvers staðar
     │
     ├─ Er framkvæmd í gangi („byrjað", „í vinnslu", „áætlað lokið")?
     │   → `in_progress`
     │
     ├─ Er vandamál eða þörf nefnd („þarfnast", „tímabært", „slitið")?
     │   → `needs_work`
     │
     ├─ Er sagt að það sé upprunalegt („upprunalegt", „frá byggingu", „original")?
     │   → `original_functional`
     │
     ├─ Inniheldur lýsing orð eins og „nýtt", „ný", „nýuppgert", „skipt út"?
     │   → `replaced_new`
     │
     ├─ Inniheldur lýsing orð eins og „yfirfarið", „endurbætt", „tekið í gegn",
     │   „endurnýjað" (án „ný")?
     │   → `overhauled`
     │
     └─ Er jákvæð umsögn án specific action („gott ástand", „vel viðhaldið")?
         → `well_maintained`
```

### Per-status dæmi úr raun-íslenskum lýsingum

**`replaced_new`** — explicit „ný" / „skipt" orð.

Trigger-phrases:
- „nýtt eldhús", „nýjar innréttingar", „nýr þakpappi", „ný þakjárn"
- „nýuppgert eldhús", „nýskipt tafla", „nýendurnýjað baðherbergi"
- „skipt út árið 2020", „keypt nýtt 2018"
- „glænýtt" er hype-útgáfa en gildir sama
- „eldhús frá 2022" → ef ljóst að íbúð er eldri og eldhús var skipt út

Counter-examples sem ekki eru replaced_new:
- „glæsilegt eldhús" — aesthetic praise, ekki action → `well_maintained`
- „fallegt eldhús" — sama, `well_maintained`
- „stórt eldhús" — size description, ekki status → `not_mentioned` (fyrir status)

**`overhauled`** — vinnu lokið en ekki „nýtt" explicit.

Trigger-phrases:
- „rafmagnstafla yfirfarin 2021"
- „þak yfirfarið og málað"
- „baðherbergi endurbætt"
- „lagnir endurnýjaðar að hluta"
- „tekið í gegn 2015" (generic renovation action — applies to whichever components are context-specific)
- „pússað upp" („fixed up" en ekki scrapped)
- „snyrt" / „snyrting" þegar það vísar í action frekar en ástand

**Hér er lykil-aðgreining Danni's**: „rafmagnstafla yfirfarin" ≠ „ný rafmagnstafla". Fyrstnefnd er `overhauled`, sú síðari er `replaced_new`. Yfirferð er viðhald + inspection + minor-fixes; „ný" er skipt út fyrir nýja.

Counter-examples:
- „nýtt en bjrúk" — Trumps — ef „nýtt" er nefnt → `replaced_new`
- „tilbúið til endurnýjunar" — inversion, means needs_work

**`well_maintained`** — positive umsögn án specific action.

Trigger-phrases:
- „vel viðhaldið", „í góðu standi", „í prima standi"
- „gott ástand", „í fínum málum"
- „snyrtileg íbúð", „vel með farin"
- „vandaðar innréttingar" (þegar kontext bendir á viðhald, ekki nýjar)

Mikilvægt: **ekki hjálpa Claude með að upgrade-a þetta í `replaced_new`** þótt það freistist. Fasteignasalar skrifa almennt jákvætt — ef þeir hefðu nýtt eldhús myndu þeir skrifa „nýtt". Þegar þeir segja bara „fallegt" er það útgáfa af „ok en ekki nýtt".

**`original_functional`** — upprunalegt og virkar.

Trigger-phrases:
- „upprunalegt eldhús", „original from the 70s"
- „eldhús frá byggingarári" (þegar byggingarár er gamalt)
- „frumleg sérkenni" (í contextinum „ekki breytt")
- „eins og upphaflega" / „eins og það var"

Oft er þetta nefnt sem selling-point á eldri húsum („upprunalegar innréttingar frá 1970, vel viðhaldnar") — þá kemur þetta á móti `well_maintained` í decision tree, og við veljum **`original_functional`** því það er meira specific.

**`needs_work`** — explicit þörf á framkvæmdum.

Trigger-phrases:
- „þarfnast endurnýjunar", „tímabært að endurnýja"
- „orðið tímabært", „orðin dugleg" (e.g. „gólfefnin eru orðin dugleg" = slitið)
- „slitið", „lítið eftir", „komið á aldur"
- „þarfnast viðhalds", „þarfnast lagfæringar"
- „tækifæri til endurnýjunar" — selling-framing fyrir needs_work
- „barn síns tíma" — eufemism fyrir gamall en virkar
- „fixer upper" — enska orðið, sjaldgæft í íslenskum lýsingum en kemur fyrir

**`in_progress`** — framkvæmd í gangi.

Trigger-phrases:
- „byrjað að klæða húsið", „klæðning í vinnslu"
- „framkvæmdir í gangi", „framkvæmdir yfirstandandi"
- „áætlað lokið 2026", „áætlað að klára"
- „þak verið að skipta um"
- „í miðri endurnýjun"

Mikilvægt: **in_progress er different frá replaced_new** þótt lokaniðurstaða sé sú sama. Timing matters — eign í miðri framkvæmd hefur uncertain value þar til lokið.

**`not_mentioned`** — þetta er **default og algengast**.

Flest listings nefna bara 3–6 af 18 components explicit. Hin 12–15 verða `not_mentioned`. Þetta er rétt — ekki overreach og giska.

---

## Year-extraction reglur

`<component>_year` er int eða null. Reglur:

**Explicit ár í lýsingu** → slá inn beint.
- „eldhús endurnýjað 2020" → `kitchen_year = 2020`
- „baðherbergi tekið í gegn árið 2018" → `primary_bathroom_year = 2018`
- „þak 2023" → `roof_year = 2023`

**Án árs** → `null`. Ekki impute mid-point í raw labeling.
- „nýtt eldhús" → `kitchen_year = null` (post-processing fyllir inn fallback)
- „þak nýskipt nýlega" → `roof_year = null`

**Árabil** → miðpunkt.
- „endurnýjað 2018–2020" → 2019
- „milli 2015 og 2018" → 2016 eða 2017 (óskir miðpunkt)

**Relative-time** → reikna með sale_year (sölu-ár hvers listing er í sample-context-upplýsingum).
- Sale_year = 2024, „fyrir 5 árum síðan endurnýjað" → 2024 - 5 = 2019
- „í fyrra" þegar sölu-ár er 2023 → 2022
- „fyrir örfáum árum" → `null` (of vague fyrir specific ár)

**Áætluð ár** → taka lægri endapunkt.
- „endurnýjað um 2015" → 2015
- „seint á 10. áratugnum" → 2019

**Decade-level only** → `null`.
- „endurnýjað á 10. áratugnum" → null (too vague)
- „tekið í gegn einhvern tímann á 00s" → null

---

## Detail-field reglur

`<component>_detail` er stutt string (max 50 chars) eða null. Bætir við specific information þegar relevant. Ekki fyrir hvert component — notað aðallega fyrir:

- **`flooring`**: viðartegund eða efni. Dæmi: „eik parket", „flísar á gólfi", „massíft parket", „laminat", „mars-náttúrusteinn".
- **`heating`**: type-specific. Dæmi: „hitaveituofnar", „gólfhiti á baðherbergi", „nýjir ofnar".
- **`insulation`**: efni. Dæmi: „glerull", „steinull", „polyúretanfrauð".
- **`kitchen`**: material/style þegar það er explicit. Dæmi: „eik innrétting", „Kvik innréttingar".
- **`elevator_mechanism`**: type. Dæmi: „Schindler 2019", „ný hraðlyfta".

**Ekki fylla út** detail fyrir paint, wiring, plumbing, o.fl. nema það sé raunverulega informative.

**Ef nothing informative** → null.

---

## Per-component reference

18 components. Hver fær sitt section með component-specific phrases. Status-enum decision tree að ofan gildir — hér er bara component-specific guidance fyrir confusing cases.

### Unit-level (11 components)

#### 1. `kitchen` (eldhús)

Mikilvægasti renovation-ás fyrir íbúðir — oft explicit nefnt.

Component-specific phrases:
- „nýjar innréttingar" → `replaced_new` (þegar „innréttingar" eru í eldhús-context; ef nefnt ein og sér, fer í `interior_finishes`)
- „endurnýjaðir skápar" → `overhauled` (skápar = partial renovation)
- „nýir tæki" í eldhúsi → `overhauled` (tækin uppfærð en ekki innréttingin sjálf)
- „eldhús eldra en nýir ofnar og spansuhella" → `overhauled`

**Detail field**: viðartegund (eik, hvítt), brand (Miele tæki, Kvik innréttingar).

#### 2. `primary_bathroom` (aðal-baðherbergi)

Ef fleiri en eitt baðherbergi í íbúð → aðal = stærra eða með baðkari.

Component-specific phrases:
- „flísalagt baðherbergi" er ekki action — flísar gætu verið original. Leita að „nýflísalagt", „flísar skipt út".
- „gólfhitar á baðherbergi" bendir til recent renovation (gólfhitar voru ekki standard í eldri byggingum).
- „nýr baðklefi" → `overhauled` (part renovation, baðklefi einn af elementum)

#### 3. `secondary_bathroom` (aukabaðherbergi)

Aðeins populated ef fleiri en eitt baðherbergi — annars `not_mentioned`. Sama logic og primary.

#### 4. `flooring` (gólfefni)

Oft explicit nefnt því gólfefni eru visible og stórt price-impact.

Component-specific phrases:
- „nýtt parket", „nýlögð flísar" → `replaced_new`
- „pússað parket", „sléttað og lakkað" → `overhauled` (refinish, ekki replace)
- „slitin gólfefni" → `needs_work`
- „fallegt gegnheilt parket" án action → `well_maintained`
- „upprunaleg gólfefni" → `original_functional`

**Detail field**: parket-tegund (eik, beykir, teak, furu, massíft) eða efni (flísar, laminat, steingólf).

#### 5. `interior_finishes` (innréttingar, innihurðir)

Fataskápar, búskápar, sérsmíði, innihurðir, skotgreypnjr o.s.frv. — EKKI eldhúsinnrétting (sem er í `kitchen`).

Component-specific phrases:
- „sérsmíðaðir fataskápar" án action → `well_maintained` (premium feature en ekki nýtt)
- „nýjar innihurðir" → `replaced_new`
- „vandaðar innréttingar" án action → `well_maintained`

#### 6. `paint` (málning)

Cosmetic refresh flag.

Component-specific phrases:
- „nýmálað", „nýlega málað" → `replaced_new` (it's cosmetic but still a distinct action)
- „lítur vel út málning" → `well_maintained`
- „málning orðin slitin" → `needs_work`

#### 7. `electrical_panel` (rafmagnstafla) — **kjarna-dæmi Danni's**

Hér er aðgreining á „ný" vs „yfirfarin" alveg sérstaklega mikilvæg.

| Íslenskt orðalag | Status |
|---|---|
| „ný rafmagnstafla" | `replaced_new` |
| „nýskipt tafla" | `replaced_new` |
| „tafla skipt út 2020" | `replaced_new` (með year=2020) |
| „rafmagnstafla yfirfarin 2021" | `overhauled` (með year=2021) |
| „tafla skoðuð af rafvirkja" | `overhauled` |
| „allt í lagi með tafla" | `well_maintained` |
| „upprunaleg tafla frá 1978" | `original_functional` (með year hjá `BYGGAR`, ekki stað) |
| „tafla orðin gömul, tímabært að skipta" | `needs_work` |

**Ruglingsatriði**: „rafmagnstafla yfirfarin og skipt út öryggi" → `overhauled` (ekki `replaced_new`) því hér er ekki sagt að taflan sjálf sé ný, bara að hún hafi verið gerð í gegn með öryggis-skiptum.

#### 8. `electrical_wiring` (raflagnir)

Aðskilið frá töflu. Lagnir á bak við vegg, í lofti.

Component-specific phrases:
- „nýjar raflagnir" → `replaced_new`
- „raflagnir endurnýjaðar að hluta" → `overhauled`
- „upprunalegar raflagnir" → `original_functional`

Sérstaklega tekið: „rafmagn tekið í gegn" er general — gildir fyrir taflu + lagnir + mögulega ofl. Ef bæði tafla og lagnir eru nefnd generic saman, flaggaðu bæði `overhauled`.

#### 9. `plumbing` (pípulagnir)

Vatns- og frárennsli sameinað.

Component-specific phrases:
- „nýjar lagnir" → `replaced_new`
- „lagnir yfirfarnar" → `overhauled`
- „nýtt pípulagnakerfi" → `replaced_new`
- „leki í lögnum" → `needs_work` + flagga í `reported_issues` sem `plumbing_issues`
- „frárennsli lagfært" → `overhauled`

#### 10. `heating` (hitakerfi)

Hitaveituofnar + gólfhiti + tenging.

Component-specific phrases:
- „nýjir ofnar" → `replaced_new`
- „ofnar yfirfarnir" → `overhauled`
- „hitaveitutenging endurnýjuð" → `overhauled`
- „gólfhiti á öllu" → detail field, status væntanlega `replaced_new` eða `well_maintained`

**Detail field**: „hitaveituofnar", „gólfhiti á hjónaherbergjum", „nýjir loftofnar".

#### 11. `windows_unit` (gluggar íbúðar)

Aðeins ef gluggar eru nefndir íbúðar-level (ekki byggingar-wide skipti). Ef allt hús fékk nýja glugga → `windows_building` er notað, ekki þetta.

Component-specific phrases:
- „nýjir gluggar í stofu" → `windows_unit: replaced_new`
- „tveggja lags einangrunargler, nýtt" → `windows_unit: replaced_new`
- „gluggar eru þéttir" → `windows_unit: well_maintained`

### Building-level (7 components)

#### 12. `roof` (þak)

Einn af áhrifamestu components á sameign-hliðina.

Component-specific phrases:
- „nýtt þak" → `replaced_new`
- „nýskipt þakpappi" → `replaced_new` (þakpappi = shingles, skipti um = roof work)
- „nýtt þakjárn" → `replaced_new`
- „þak yfirfarið" → `overhauled`
- „þak lagfært" → `overhauled`
- „þak lekur" → `needs_work` + `reported_issues: roof_leak_current`
- „þak verið að skipta um" → `in_progress`

Important: „þakpappi skipt út fyrir 5 árum" með sale_year 2024 → year=2019.

#### 13. `cladding` (klæðning)

Oft partial á Íslandi — húsi er klætt í áföngum, eitt hús í senn.

Component-specific phrases:
- „nýklæðning", „nýklætt hús" → `replaced_new`
- „klæðning í góðu standi" → `well_maintained`
- „byrjað að klæða húsið að utan" → `in_progress`
- „áætlað að klæða húsið 2025" → `in_progress` (jafnvel þótt enn ekki byrjað, ef plan er concrete)
- „klæðning orðin slitin" → `needs_work`

#### 14. `windows_building` (byggingar-wide gluggaskipti)

Bara ef allir gluggar voru skiptir út samtímis í sameign-level framkvæmd.

Component-specific phrases:
- „gluggum skipt út 2018 í allri byggingu" → `replaced_new` með year=2018
- „byggingar-wide gluggaskipti í fyrra" → `replaced_new` (year relative)
- „gluggar framtíðar-project" → `needs_work` (planned but not in_progress)

#### 15. `insulation` (einangrun)

Sjaldan explicit nefnt — ef það er, er það oft selling-point.

Component-specific phrases:
- „ný einangrun á þakinu" → `replaced_new`
- „glerull í veggjum" án action → `well_maintained` eða `original_functional` eftir samhengi
- „létt einangrun, þarf að bæta" → `needs_work`

**Detail field**: „glerull", „steinull", „polyúretan", „frauðplast".

#### 16. `elevator_mechanism` (lyftu-mekanismi)

**EKKI same og `has_elevator_available`**. Þetta er um endurnýjun eða ástand lyftunnar sem mekanismi.

Component-specific phrases:
- „ný lyfta" → `replaced_new` (bætt við lyftu-mekanisma refresh)
- „lyfta skipt út 2020" → `replaced_new` með year
- „lyfta yfirfarin" → `overhauled`
- „gömul lyfta frá byggingu" → `original_functional`

Ef lýsing segir bara „lyfta" án action-orða → `not_mentioned` (því flag-coverage er aðskilin í augl-supplement; þetta er specifically um state of mechanism, sem er ekki almenni).

**Detail field**: brand og ár. „Schindler 2020", „Otis 2015".

#### 17. `sameign_cosmetic` (sameignar-málning og gólf)

Common-area refresh. Stigagangur, forstofa, sameiginlegir gangar.

Component-specific phrases:
- „stigagangur nýmálaður" → `replaced_new`
- „sameign tekin í gegn" → `overhauled`
- „sameign snyrtileg" → `well_maintained`
- „sameign þarfnast málningar" → `needs_work`

#### 18. `foundation_drainage` (grunnur, frárennsli í kringum hús)

Sjaldgæft en stórt þegar nefnt. Foundation leak er notable red flag.

Component-specific phrases:
- „nýtt drainage í kringum húsið" → `replaced_new`
- „grunnur lagfærður", „grunnsvæði yfirfarið" → `overhauled`
- „rakaskemmdir í kjallara" → `needs_work` + `reported_issues: damp_mold`
- „settlement í grunni" → `needs_work` + `reported_issues: settlement_cracks`

---

## Situational fields — leiðbeiningar

### Útsýni

**`view_type`** — multi-select. Lístu öll gildi sem eiga við. Ef eitt view er augljóst kjarni (t.d. „sjávarsýn") en annað er smávægilegt („smá útsýni yfir bæinn") → bara lístu kjarna.

**`view_quality`** — verste-að-fínasta scale:
- `premium`: hyped language, „einstakt", „stórkostlegt", „ótrúlegt", „cinematic view", „views of the century"
- `good`: nefnt jákvætt án hype. „Fín sjávarsýn", „útsýni yfir Esju"
- `partial`: takmarkað eða indirekt. „Svipur af sjó", „takmarkað útsýni", „í fjarlægð"
- `none`: explicit sagt að engið útsýni sé. „Horfir að bakhlið", „engið útsýni"
- `not_mentioned`: ekki nefnt yfir höfuð

**Ruglingsatriði**: „snýr í suður" er ekki view signal — það er orientation signal (→ `balcony_orientation` ef um svalir er að ræða, eða nothing ef almennt).

### Útipláss detail

**`balcony_size_bucket`**:
- Explicit stærð í m² → bucket beint: `<5 small / 5–10 medium / 10–20 large / >20 wraparound`
- Qualitative: „franskar svalir" → `small`; „rúmar svalir" → `medium`; „stórar svalir" → `medium` eða `large` eftir samhengi; „þakverönd" → `wraparound_or_huge`; „hringsvalir" → `wraparound_or_huge`
- Ef augl `svalir=true` en lýsing nefnir ekki → `not_mentioned` (heldur svalir-existence frá augl)
- Ef augl `svalir=false` eða null og lýsing nefnir ekki → `none` eða `not_mentioned` eftir samhengi

**`balcony_orientation`** — reyna að infer úr „suðursvalir", „vesturgluggar", o.s.frv. Ef ekki nefnt → `not_mentioned`.

**`has_pallur_veroend`** — **distinct frá svölum**. Pallur er útigarður-level structure, oft fyrir einbýlishús eða raðhús á jarðhæð. Verönd er yfirbyggður pallur.

**`garden_quality`**:
- `premium`: „stór garður með pallur", „ræktaður garður", „gróskumikill garður"
- `standard`: „snyrtilegur garður", venjulegur
- `minimal`: „lítill garður" eða bara grasblettur
- `none`: explicit „engið garður"
- `not_mentioned`: ekki rætt

**`has_hot_tub`** — trilemma. „Heitur pottur" → `yes`. Ekki nefnt → `not_mentioned`.

### Bílastæði detail

**`parking_type`** — velja nákvæmasta gildi:
- `enclosed_garage`: „bílskúr" í hefðbundnum skilningi (lokað herbergi, oft með sérhurð inn í hús)
- `underground_unheated`: „bílastæði í bílakjallara" án hita-mention
- `underground_heated`: „upphitaður bílakjallari" — notable premium
- `carport`: „bílastæði undir þaki", „bílaskýli"
- `assigned_outdoor`: „sérstæði úti", „merkt stæði"
- `unassigned_outdoor`: „bílastæði á lóð"
- `none`: explicit sagt að ekkert bílastæði sé
- `not_mentioned`: ekki rætt

**`num_parking_spaces`** — explicit tala ef nefnd. „Tvö stæði" → 2.

**`parking_for_large_vehicle`** — trilemma. „Nógu rúmt fyrir jeppi" → `yes`. „Fyrir húsbíl" → `yes`. Ekki nefnt → `not_mentioned`.

### Layout

**`num_toilets_separate`** — **aðskilið frá `fjbadherb`** (sem telur baðherbergi með baðkari/sturtu). Þetta er gestasalerni / sér-WC fyrir utan baðherbergi.

- „gestasalerni" → 1
- „tvö sér-WC" → 2
- „WC innaf forstofu" → 1 (usually separate)
- Ekki nefnt → `not_mentioned`

**`has_ensuite_master`** — trilemma. „Baðherbergi innaf hjónaherbergi", „master en suite" → `yes`.

**`is_penthouse` / `is_duplex` / `is_studio` / `open_plan_living`** — trilemma hver. Explicit mentions only.

- Penthouse: „efstu hæð með þakverönd", „penthouse", „þaklýbúðin" (ekki bara „efsta hæðin" — 4-hæða blokk top unit er ekki penthouse)
- Duplex: „tvær hæðir innan íbúðar", „palli upp á svefnherbergjahæð"
- Studio: „1 herbergis íbúð", „studio"
- Open plan: „opið rými", „eldhús og stofa opin saman", „opnun milli eldhús og stofu"

### Byggingin & annað

**`heating_type`**:
- `hitaveita`: standard á höfuðborgarsvæðinu og mörgum landsbyggðar bæjum (Akureyri, Húsavík etc.)
- `electric`: Westfirðir, sum Austfirðir þar sem hitaveita er ekki til
- `heat_pump`: „varmadæla", sjaldgæft
- `geothermal_local`: „jarðvarmi á eigin lóð" — sjaldgæft, premium signal fyrir sveitabýli
- `mixed`: kombinasjon (t.d. hitaveita fyrir ofna + electric gólfhiti)
- `not_mentioned`: ekki rætt

**`num_units_in_building_stated`** — explicit tala. „Í 4 íbúða húsi" → 4.

**`has_sauna`** — trilemma. Í íbúð eða sameign.

**`has_fireplace`** — trilemma. „Arinn", „kamína" → `yes`. „Gervi-eldstæði" → `no` (til stemningar en ekki functional fireplace).

**`storage_type`** — multi-select:
- `sergeymsla`: „sérgeymsla í kjallara" eða „stor geymsla"
- `hjolageymsla_sameign`: „hjólageymsla í sameign"
- `thvotta_in_unit`: „þvottahús í íbúð"
- `thvotta_sameign`: „þvottahús í sameign"
- `none_mentioned`: explicitly ekkert eða ekki nefnt

### Negative signals

**`reported_issues`** — multi-select. Pickaðu öll vandamál sem eru **explicit nefnd**. Ekki extrapolate frá „þarfnast endurnýjunar" — sú upplýsing er þegar fangað í component status.

- `damp_mold`: „raki", „mygla"
- `roof_leak_current`: „þak lekur" (núverandi vandamál — fyrri lekur sem er viðgerður er ekki þetta)
- `plumbing_issues`: „leki í lögnum", „stíflur"
- `electrical_issues`: „rafmagn óstöðugt"
- `settlement_cracks`: „sprungur" (í concrete / grunni)
- `noise_issues`: „hávaðamengun", „umferðarhávaði"
- `heating_issues`: „hitakerfi virkar ekki alltaf"
- `pest_issues`: „músavandi", sjaldgæft en alvarlegt
- `moisture_history`: „fyrri rakaskemmdir viðgerðar"
- `none_mentioned`: default ef ekkert explicit vandamál

**`needs_immediate_work`** — trilemma. `yes` eingöngu ef lýsing segir **explicit** að framkvæmdir þurfi áður en innflutningur. „Tækifæri til endurnýjunar" → `yes`. „Barn síns tíma" → `no` (lifir-in-habitable). „Þarfnast mikillar vinnu" → `yes`.

**`sold_as_is`** — trilemma. `yes` ef phrase eins og „selt í núverandi ástandi", „sold as-is", „no repairs".

### Augl-supplement trilemma

Sjö fields — `has_balcony`, `has_garden`, `has_elevator_available`, `has_assigned_parking`, `has_ev_charging`, `is_accessible`, `is_senior_marketed`.

Hvert er trilemma. Labeler labelar út frá **lýsingu** eingöngu — post-processing sameinar við augl.

- `has_balcony`: „svalir", „svala", „bakvið" → yes. Explicit „engar svalir" → no. Ekki nefnt → not_mentioned.
- `has_garden`: „garður", „lóð", „grasblettur" → yes. Explicit engið → no.
- `has_elevator_available`: „lyfta í húsi" → yes. „Ekki lyfta, þriggja hæða ganga" → no.
- `has_assigned_parking`: „sérstæði", „eigið bílastæði" → yes. „Bílastæði á götu" → no (street parking ekki assigned).
- `has_ev_charging`: „hleðslustöð", „rafbíll hleðslu" → yes.
- `is_accessible`: „hjólastólsvænt", „aðgengi fyrir fatlaða" → yes.
- `is_senior_marketed`: „fyrir eldri borgara", „60+", „senior friendly" → yes.

### Agent framing

**`agent_lead_selling_point`** — einn value, að því sem fasteignasali hefur **leitt með** í fyrstu 2–3 setningum lýsingar.

- `location`: „Í hjarta miðborgarinnar", „besta staðsetning í Reykjavík"
- `view`: „Með einstakt sjávarsýn"
- `recent_renovations`: „Nýuppgert í gegn"
- `size_layout`: „Rúmgóð og björt íbúð"
- `condition_overall`: „Glæsileg íbúð í toppstandi"
- `investment_potential`: „Tækifæri til fjárfestingar", „útleigumöguleikar"
- `new_build_appeal`: „Ný bygging", „rétt af nýbyggingar-line"
- `historical_charm`: „Klassísk", „tímalaus hönnun", „30's style"
- `other`: annað specific
- `not_clear`: ef lýsing er terse og leads ekki með neitt klárt

**`urgency_signals`**:
- `motivated_seller`: „seljandi þarf að selja fljótt", „fljótafgreiðsla"
- `priced_for_quick_sale`: „verði þarf að halda", „price motivator"
- `recent_price_reduction`: „lækkað verð", „newly reduced"
- `unmotivated_neutral`: „verð á réttum markaði"
- `not_mentioned`: ekki rætt

**`listing_elaboration`** — qualitative judgment:
- `terse`: undir 200 orðum, basic facts only
- `standard`: 200–500 orð, reglulega described
- `elaborate`: 500–1000 orð, details on features
- `promotional_heavy`: yfir 1000 orð eða þétt með marketing-speak („einstakur", „á heimsmælikvarða" etc.)

---

## Property narrative

Labeler skrifar 2–4 setninga samantekt á íslensku af eigninni. Ekki copy-paste úr lýsingu — eigin orð.

**Form**:
> „[Íbúðategund] á [hæð] í [hverfi eða matsvæði]. [Nokkur nothæf feature frá lýsingu]. [Ástand / renovations eða vantanir]. [Útipláss eða parking ef significant]."

**Dæmi**:
> „3ja herbergja íbúð á 4. hæð í Hlíðum. Eldhús og baðherbergi endurnýjuð nýlega (2020–2022). Nýtt þak á byggingu (2023), klæðning í vinnslu. Upphitaður bílakjallari og suðursvalir."

Tonbeit: neutral, factual. Ekki promotional. Notaðu upplýsingar sem ekki eru fangaðar í structured fields (t.d. mood af íbúðar, specific area nefnt, óvenjulegar features).

Max 400 chars.

---

## Edge cases og tricky situations

### Sama phrase fyrir marga components
„Tekið í gegn 2018" — hvaða components?

→ Labeler les samhengi. Ef listing segir „eldhús og baðherbergi tekið í gegn 2018", þá bæði fá `overhauled + year=2018`. Ef generic „íbúðin öll tekin í gegn", þá labelaðu `overhauled` fyrir interior components (kitchen, primary_bathroom, flooring, paint, interior_finishes) með year.

### Listing mentions renovation but no explicit component

„Nýuppgert" án specification → label kitchen + primary_bathroom sem líklegustu kandidata (mest common renovations) sem `replaced_new` með year=null. Flagga í `confidence_notes` að „nýuppgert" var generic.

Þetta er **inference** og nokkur labeler-judgment. Sé í lagi — gold-standard má innihalda slíkt svo lengi sem it's consistent.

### Listing er á ensku
Flagga `listing_lang_is_icelandic: no` og label eins og hægt er. Status-enum gildir eins á ensku og íslensku (same decisions).

### Listing er próftextur eða broken
T.d. raw HTML leftovers, dead text. Flagga `listing_minimally_informative: yes` og labelaðu `not_mentioned` á flest fields. Skrifaðu í `extraction_notes`: „Listing mestmegnis boilerplate án concrete detail."

### Component er nefnt tvisvar með mismunandi status
T.d. „gólfefni upprunaleg í stofu en nýskipt í eldhúsi". → Labeler veldur dominant component (stærri flötur, meira visible) → hér `flooring: original_functional` með athugasemd, eða nota meirihluta. Skrifaðu í `extraction_notes`.

### „Nýtt og notað"
„Glænýjar innréttingar en notaðir ofnar" → components fá mismunandi status. Skipta.

---

## Þrjú complete worked examples

### Dæmi 1: APT_FLOOR í RVK_core, elaborate listing

**Raw lýsing**:
> „Glæsileg 3ja herbergja íbúð á 4. hæð með lyftu í vinsælu fjölbýli á besta stað í Vesturbænum. Íbúðin hefur verið tekin í gegn á síðustu árum: eldhús nýuppgert 2022 með nýjum Miele-tækjum og eik innréttingu, baðherbergi endurnýjað 2020 með gólfhita og walk-in sturtuklefa. Nýlega lagt eik parket á alla íbúðina. Rafmagnstafla yfirfarin 2021 af fagmanni. Stórar suðursvalir með útsýni yfir sjóinn. Nýtt þak var sett á húsið 2023, klæðning á ytri vegg er hafin (áætlað að ljúka 2025), gluggum var skipt út 2018 í allri byggingu. Upphitaður bílakjallari með sérstæði. Sérgeymsla í kjallara. Íbúðin er í topp standi og rólegu umhverfi."

**Extraction**:

```json
{
  "augl_id": "<example>",
  "extraction_version": "v0.2.1",
  "listing_lang_is_icelandic": "yes",
  "listing_minimally_informative": "no",
  "components": {
    "kitchen": { "status": "replaced_new", "year": 2022, "detail": "eik innrétting, Miele" },
    "primary_bathroom": { "status": "replaced_new", "year": 2020, "detail": null },
    "secondary_bathroom": { "status": "not_mentioned", "year": null, "detail": null },
    "flooring": { "status": "replaced_new", "year": null, "detail": "eik parket" },
    "interior_finishes": { "status": "not_mentioned", "year": null, "detail": null },
    "paint": { "status": "not_mentioned", "year": null, "detail": null },
    "electrical_panel": { "status": "overhauled", "year": 2021, "detail": null },
    "electrical_wiring": { "status": "not_mentioned", "year": null, "detail": null },
    "plumbing": { "status": "not_mentioned", "year": null, "detail": null },
    "heating": { "status": "well_maintained", "year": null, "detail": "gólfhiti á baðherbergi" },
    "windows_unit": { "status": "not_mentioned", "year": null, "detail": null },
    "roof": { "status": "replaced_new", "year": 2023, "detail": null },
    "cladding": { "status": "in_progress", "year": 2024, "detail": null },
    "windows_building": { "status": "replaced_new", "year": 2018, "detail": null },
    "insulation": { "status": "not_mentioned", "year": null, "detail": null },
    "elevator_mechanism": { "status": "not_mentioned", "year": null, "detail": null },
    "sameign_cosmetic": { "status": "not_mentioned", "year": null, "detail": null },
    "foundation_drainage": { "status": "not_mentioned", "year": null, "detail": null }
  },
  "view_type": ["sea"],
  "view_quality": "good",
  "balcony_size_bucket": "large",
  "balcony_orientation": "south",
  "has_pallur_veroend": "not_mentioned",
  "garden_quality": "not_mentioned",
  "has_hot_tub": "not_mentioned",
  "parking_type": "underground_heated",
  "num_parking_spaces": 1,
  "parking_for_large_vehicle": "not_mentioned",
  "num_toilets_separate": "not_mentioned",
  "has_ensuite_master": "not_mentioned",
  "is_penthouse": "no",
  "is_duplex": "no",
  "is_studio": "no",
  "open_plan_living": "not_mentioned",
  "heating_type": "hitaveita",
  "num_units_in_building_stated": "not_mentioned",
  "has_sauna": "not_mentioned",
  "has_fireplace": "not_mentioned",
  "storage_type": ["sergeymsla"],
  "reported_issues": ["none_mentioned"],
  "needs_immediate_work": "no",
  "sold_as_is": "not_mentioned",
  "has_balcony": "yes",
  "has_garden": "not_mentioned",
  "has_elevator_available": "yes",
  "has_assigned_parking": "yes",
  "has_ev_charging": "not_mentioned",
  "is_accessible": "not_mentioned",
  "is_senior_marketed": "not_mentioned",
  "agent_lead_selling_point": "condition_overall",
  "urgency_signals": "not_mentioned",
  "listing_elaboration": "elaborate",
  "property_narrative": "Þriggja herbergja íbúð á 4. hæð í Vesturbænum með lyftu. Íbúðin hefur verið tekin í gegn undanfarin ár: nýtt eldhús (2022) og baðherbergi (2020), nýlagt parket. Byggingin í góðu viðhaldi: nýtt þak (2023), gluggaskipti 2018, klæðning í vinnslu. Suðursvalir með sjávarsýn og upphitaður bílakjallari.",
  "extraction_notes": null
}
```

Athugasemdir um dæmi 1:
- „Tekin í gegn á síðustu árum" er generic — ég flaggaði ekki sem overhauled á specific components; í staðinn flagg ég specific components sem eru nefnd (eldhús replaced_new, baðherbergi replaced_new, parket replaced_new, rafmagnstafla overhauled). Generic-phrase-ið er implicit í þeim.
- „Nýlega lagt" parket — year null því ekki explicit.
- „Gólfhiti" á baðherbergi flagað sem detail í `heating`, status `well_maintained` (ekki renovation action nefnd fyrir hita-kerfið sjálft).
- Lyftan er `not_mentioned` í component matrix (mekanismi er ekki rætt) en `has_elevator_available: yes` í supplement.
- „Áætlað að ljúka 2025" — cladding `in_progress` með year=2024 (núverandi aðgerð).
- „Upphitaður bílakjallari" → `parking_type: underground_heated`, og `has_assigned_parking: yes`.

### Dæmi 2: SFH_DETACHED í Country, terse listing

**Raw lýsing**:
> „Einbýli á Akranesi, 140 fm. Eldhús frá byggingu. Tveimur baðherbergjum. Garður í kringum hús. Bílskúr. Verð tilboð. Tilbúið til endurnýjunar."

**Extraction**:

```json
{
  "augl_id": "<example>",
  "extraction_version": "v0.2.1",
  "listing_lang_is_icelandic": "yes",
  "listing_minimally_informative": "yes",
  "components": {
    "kitchen": { "status": "original_functional", "year": null, "detail": null },
    "primary_bathroom": { "status": "not_mentioned", "year": null, "detail": null },
    "secondary_bathroom": { "status": "not_mentioned", "year": null, "detail": null },
    "flooring": { "status": "not_mentioned", "year": null, "detail": null },
    "interior_finishes": { "status": "not_mentioned", "year": null, "detail": null },
    "paint": { "status": "not_mentioned", "year": null, "detail": null },
    "electrical_panel": { "status": "not_mentioned", "year": null, "detail": null },
    "electrical_wiring": { "status": "not_mentioned", "year": null, "detail": null },
    "plumbing": { "status": "not_mentioned", "year": null, "detail": null },
    "heating": { "status": "not_mentioned", "year": null, "detail": null },
    "windows_unit": { "status": "not_mentioned", "year": null, "detail": null },
    "roof": { "status": "not_mentioned", "year": null, "detail": null },
    "cladding": { "status": "not_mentioned", "year": null, "detail": null },
    "windows_building": { "status": "not_mentioned", "year": null, "detail": null },
    "insulation": { "status": "not_mentioned", "year": null, "detail": null },
    "elevator_mechanism": { "status": "not_mentioned", "year": null, "detail": null },
    "sameign_cosmetic": { "status": "not_mentioned", "year": null, "detail": null },
    "foundation_drainage": { "status": "not_mentioned", "year": null, "detail": null }
  },
  "view_type": ["not_mentioned"],
  "view_quality": "not_mentioned",
  "balcony_size_bucket": "not_mentioned",
  "balcony_orientation": "not_mentioned",
  "has_pallur_veroend": "not_mentioned",
  "garden_quality": "standard",
  "has_hot_tub": "not_mentioned",
  "parking_type": "enclosed_garage",
  "num_parking_spaces": "not_mentioned",
  "parking_for_large_vehicle": "not_mentioned",
  "num_toilets_separate": "not_mentioned",
  "has_ensuite_master": "not_mentioned",
  "is_penthouse": "no",
  "is_duplex": "not_mentioned",
  "is_studio": "no",
  "open_plan_living": "not_mentioned",
  "heating_type": "not_mentioned",
  "num_units_in_building_stated": 1,
  "has_sauna": "not_mentioned",
  "has_fireplace": "not_mentioned",
  "storage_type": ["none_mentioned"],
  "reported_issues": ["none_mentioned"],
  "needs_immediate_work": "yes",
  "sold_as_is": "not_mentioned",
  "has_balcony": "not_mentioned",
  "has_garden": "yes",
  "has_elevator_available": "no",
  "has_assigned_parking": "yes",
  "has_ev_charging": "not_mentioned",
  "is_accessible": "not_mentioned",
  "is_senior_marketed": "not_mentioned",
  "agent_lead_selling_point": "not_clear",
  "urgency_signals": "priced_for_quick_sale",
  "listing_elaboration": "terse",
  "property_narrative": "Einbýli á Akranesi, 140 fm með tveimur baðherbergjum. Eldhús upprunalegt frá byggingu. Garður og bílskúr. Lýsing skilgreinir að eignin er tilbúin til endurnýjunar.",
  "extraction_notes": "Lýsing er mjög terse — flest components not_mentioned. 'Tilbúið til endurnýjunar' flag-gað sem needs_immediate_work=yes. 'Verð tilboð' sem priced_for_quick_sale signal."
}
```

Athugasemdir um dæmi 2:
- Listing er terse → flest fields `not_mentioned`, sem er rétt. Ekki overreach.
- „Eldhús frá byggingu" → `kitchen: original_functional`.
- „Tveimur baðherbergjum" → already í `fjbadherb`, ekki í extraction. `primary_bathroom` er not_mentioned því ekkert er sagt um status.
- „Tilbúið til endurnýjunar" → `needs_immediate_work: yes`.
- „Verð tilboð" (suggesting seller is negotiable) → `urgency_signals: priced_for_quick_sale`.
- `listing_elaboration: terse` því lýsing er undir 50 orð.

### Dæmi 3: ROW_HOUSE í Capital_sub, mixed signals

**Raw lýsing**:
> „Snyrtilegt raðhús á Seltjarnarnesi, 180 fm, byggt 1985. Eldhús og baðherbergi hafa verið yfirfarin undanfarin ár, en innréttingar eru enn upprunalegar. Nýjir ofnar og rafmagnstafla yfirfarin. Þak lekur þó sjaldan — áætlað er að skipta því út á næsta ári. Gólfefnin eru orðin dugleg. Rúmgóður garður með pallur, heitur pottur. Bílskúr tvöfaldur. Sérgeymsla. Tilboð óskast."

**Extraction**:

```json
{
  "augl_id": "<example>",
  "extraction_version": "v0.2.1",
  "listing_lang_is_icelandic": "yes",
  "listing_minimally_informative": "no",
  "components": {
    "kitchen": { "status": "overhauled", "year": null, "detail": null },
    "primary_bathroom": { "status": "overhauled", "year": null, "detail": null },
    "secondary_bathroom": { "status": "not_mentioned", "year": null, "detail": null },
    "flooring": { "status": "needs_work", "year": null, "detail": null },
    "interior_finishes": { "status": "original_functional", "year": null, "detail": null },
    "paint": { "status": "not_mentioned", "year": null, "detail": null },
    "electrical_panel": { "status": "overhauled", "year": null, "detail": null },
    "electrical_wiring": { "status": "not_mentioned", "year": null, "detail": null },
    "plumbing": { "status": "not_mentioned", "year": null, "detail": null },
    "heating": { "status": "replaced_new", "year": null, "detail": "nýjir ofnar" },
    "windows_unit": { "status": "not_mentioned", "year": null, "detail": null },
    "roof": { "status": "in_progress", "year": null, "detail": null },
    "cladding": { "status": "not_mentioned", "year": null, "detail": null },
    "windows_building": { "status": "not_mentioned", "year": null, "detail": null },
    "insulation": { "status": "not_mentioned", "year": null, "detail": null },
    "elevator_mechanism": { "status": "not_mentioned", "year": null, "detail": null },
    "sameign_cosmetic": { "status": "not_mentioned", "year": null, "detail": null },
    "foundation_drainage": { "status": "not_mentioned", "year": null, "detail": null }
  },
  "view_type": ["not_mentioned"],
  "view_quality": "not_mentioned",
  "balcony_size_bucket": "not_mentioned",
  "balcony_orientation": "not_mentioned",
  "has_pallur_veroend": "yes",
  "garden_quality": "premium",
  "has_hot_tub": "yes",
  "parking_type": "enclosed_garage",
  "num_parking_spaces": 2,
  "parking_for_large_vehicle": "not_mentioned",
  "num_toilets_separate": "not_mentioned",
  "has_ensuite_master": "not_mentioned",
  "is_penthouse": "no",
  "is_duplex": "not_mentioned",
  "is_studio": "no",
  "open_plan_living": "not_mentioned",
  "heating_type": "not_mentioned",
  "num_units_in_building_stated": "not_mentioned",
  "has_sauna": "not_mentioned",
  "has_fireplace": "not_mentioned",
  "storage_type": ["sergeymsla"],
  "reported_issues": ["roof_leak_current"],
  "needs_immediate_work": "not_mentioned",
  "sold_as_is": "not_mentioned",
  "has_balcony": "not_mentioned",
  "has_garden": "yes",
  "has_elevator_available": "not_mentioned",
  "has_assigned_parking": "yes",
  "has_ev_charging": "not_mentioned",
  "is_accessible": "not_mentioned",
  "is_senior_marketed": "not_mentioned",
  "agent_lead_selling_point": "size_layout",
  "urgency_signals": "priced_for_quick_sale",
  "listing_elaboration": "standard",
  "property_narrative": "Raðhús á Seltjarnarnesi (180 fm, byggt 1985). Eldhús og baðherbergi yfirfarin nýlega en innréttingar enn upprunalegar. Nýjir ofnar, rafmagnstafla yfirfarin. Þak lekur sjaldan — verður skipt út á næsta ári. Rúmgóður garður með pallur og heitum potti. Tvöfaldur bílskúr.",
  "extraction_notes": "Mixed status-signals — eldhús overhauled en innréttingar original, gólfefni needs_work. Þak `in_progress` því áætlað skipti á næsta ári."
}
```

Athugasemdir um dæmi 3:
- „Hafa verið yfirfarin undanfarin ár" → `overhauled` fyrir eldhús og baðherbergi, year=null (ekki explicit ár).
- „Innréttingar enn upprunalegar" → `interior_finishes: original_functional`. **Þetta yfirgefur counterfactual verðmat**: eldhús er `overhauled` en innréttingar eru `original` — labeler respectaði distinction.
- „Nýjir ofnar" → `heating: replaced_new` með detail „nýjir ofnar".
- „Þak lekur þó sjaldan — áætlað að skipta" → tvöfaldur signal: `roof: in_progress` (áætlun concrete) + `reported_issues: roof_leak_current` (núverandi vandamál).
- „Gólfefnin eru orðin dugleg" → `flooring: needs_work`.
- „Bílskúr tvöfaldur" → `num_parking_spaces: 2`, `parking_type: enclosed_garage`.
- „Heitur pottur" → `has_hot_tub: yes`, sem lyftir `garden_quality` upp í `premium` (pallur + heitur pottur + rúmgóður garður → premium).
- „Tilboð óskast" → `urgency_signals: priced_for_quick_sale`.

---

## Common mistakes sem ég vil forðast

Frá reynslu með tilfinningu fyrir hvar LLM-extraction og hand-labeling lenda í ósamræmi:

**Mistake 1: Upgrade-a `well_maintained` í `replaced_new`**. Seljandi segir „fallegt eldhús" → labeler freistast að merkja `replaced_new` því hann veit að sellers marketera jákvætt. Röng — „fallegt" án „nýtt"-orðs er `well_maintained`.

**Mistake 2: Sleppa `not_mentioned` á components sem eru implied en ekki nefnd**. Listing sem segir „íbúðin er í góðu standi" implikar hmmmm 18 components allir OK — en nefnir þá ekki specific. → `not_mentioned` fyrir alla, `condition_grade` positive aðskilið. Don't over-infer.

**Mistake 3: Ruglast á `overhauled` og `replaced_new`**. „Endurnýjað" eitt og sér er ambiguous — íslenska orðið getur þýtt bæði „ný" eða „tekið í gegn". Regla: ef „ný" orð er nefnd beint í setningu, → `replaced_new`. Ef „yfirfarið" eða „endurbætt" eingöngu, → `overhauled`.

**Mistake 4: Fylla `not_mentioned` þegar augl-supplement er nefnd**. T.d. `has_balcony: not_mentioned` þegar lýsing segir „suðursvalir". → `has_balcony: yes` (beint úr lýsingu).

**Mistake 5: Gefa upp tíma í year-estimation**. „Nýlega" er ekki „fyrir 2 árum síðan" — það er null. Ef ekki explicit → null.

**Mistake 6: Narrative sem er copy-paste**. Labeler á að skrifa eigin orð. Copy-paste spillir explainability-hæft output sem á að vera Claude-authored narrative í production.

---

## Labeling-sheet columns

Google Sheet setup — einn tab „labeling" og einn „guide".

`labeling` tab columns:
- `sample_order` (1–100), `augl_id`, `canonical_code`, `region_tier`, `sale_year`, `lysing_preview` (fyrstu 500 chars)
- 18 × 3 = 54 component-matrix columns (status_<comp>, year_<comp>, detail_<comp>)
- Situational fields (~25 columns)
- Negative signals (~3 columns)
- Augl-supplement trilemmas (7 columns)
- Agent framing (3 columns)
- `property_narrative` (string)
- `extraction_notes` (string)
- `labeler_id`, `labeled_at`, `confidence_notes`

Total ~95+ columns. Nota data validation dropdowns fyrir enum fields — blokkar typos.

Ef Google Sheet verður þunglamalega með 100 × 95 cells, þá er hægt að klippa sample í tvo batch (50 + 50) með separate sheets. En ætti að virka.

---

## Quality check eftir labeling

Eftir hver 20 labeled listings, stop og gera self-review:

1. Er `not_mentioned` rate í samræmi? Ef 95% af kitchen-fields eru `not_mentioned` → líklega labeler að missa signal. Ef 20% → líklega labeler að overreach.
2. Fyrstu 20 vs síðustu 20 — sama labeler-decisions á svipuðum phrase-um?
3. Status distribution sanity check — ef `original_functional` er 0% af total, einhverju er sleppt.
4. Years distribution — er meirihluta af years-fields ≥ 2015? Ef flest eru fyrir 2010, er líklega verið að taka „frá byggingu" sem year.

Ef self-review bendir á issue → consult með mér áður en halda áfram. Betri að laga 20 listings en 80.

---

## Ending notes

Þetta guide er stöðugt mikið skjal. Gerðu ekki einn-session job úr því — labelaðu í 2–4 klst blokkum með pásum. Labeler-fatigue er raunverulegt og drags-ar niður quality eftir ~20 listings í beit.

Ef eitthvað er óljóst eftir að hafa lesið þetta, markið down og við ræðum áður en labeling er lokið. Schema-refinement er part af processinu.
