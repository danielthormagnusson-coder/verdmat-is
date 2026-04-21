# EXTRACTION_SCHEMA — LLM-extraction v0.2.2 (component-level rich + pilot refinements)

**Útgáfa**: v0.2.2 (2026-04-19, eftir 3c pilot synthesis)
**Supersedes**: v0.2.1 (2026-04-18)
**Staða**: Frozen fyrir re-pilot á 200 listings; verður frystist í v0.3 eftir batch-round 1 feature-importance greiningu.
**Scope**: Residential paired subset, ~47.179 unique listings eftir hash-dedup af 53.866 paired + length-filtered pool.

---

## Changelog v0.2.1 → v0.2.2

V0.2.2 er additive increment á v0.2.1. Engin field fjarlægð eða endurnefnd; 15 ný fields bætast við og eitt existing field er endurskilgreint (garden_quality). Þrjár refinements á system prompt stefna að því að laga systematic biases sem komu í ljós í 3c pilot.

**Af hverju**: 3c pilot (200 listings á Haiku 4.5) keyrt með zero extraction failures en tvenns konar data-quality issues kom í ljós: (a) þrjú systematic biases í extraction sjálfu (well_maintained over-use, þakkantur-confusion, listing_elaboration inflation); (b) five clusters af recurring signals sem schema nær ekki. Keyword-based gap analysis (120 orð á lýsingu vs extraction) og LLM-based meta-analysis (Sonnet 4.6 á 200 × 1.105 flagged signals) voru aðferðirnar sem gáfu concrete refinement-lista.

**Nýjar fields** (15):

| Klasi | Fields | Rationale |
|---|---|---|
| Size & legal (6) | `unregistered_space_present`, `unregistered_space_sqm_stated`, `unregistered_space_type`, `has_secondary_unit`, `ceiling_height_premium`, `unused_building_rights_present` | 24% af pilot-listings hafa óskráð m²/aukaíbúð/loft signals; zero currently captured. Row 8 pilot: „Óskráð rými á neðri hæð er u.þ.b 40 fm" — ~+15–20% value missed. |
| Outdoor (5) | `lot_type`, `lot_orientation`, `garden_size_framing`, `is_corner_lot`, `is_waterfront_or_seaside` | Sérlóð er major APT premium, fullkomlega ónefnt í v0.2.1. Garden_quality blandaði size + condition. |
| Intra-unit (2) | `laundry_configuration`, `end_unit_position` | Sér þvottahús innan íbúðar (6×) og endaraðhús (5×) endurtökur í LLM discovery. |
| Listing dynamics (2) | `sale_channel`, `immediate_availability` | Ekki verðfeatures per se; hráefni í ask-to-sale-gap og time-on-market módel (Áfangi 7). |

**Refactor** (1): `garden_quality` values endurskilgreind til að vera condition-only, decoupled frá size (sem fer í nýtt `garden_size_framing`).

**Eftir í v0.3** (ekki í v0.2.2): nýbyggingar sub-schema (`finish_package_level`, `delivery_status`, `early_occupancy_available`, `building_permit_status`), sumarbústaða-dedicated schema, image-based features, historical designation.

**Sleppt meðvitað** (LLM discovery benti á þessi klasa, ákvörðun að skilja út):

| Klasi | LLM-tíðni | Af hverju sleppt |
|---|---|---|
| Heated outdoor surfaces (hitalögn/snjóbræðsla) | 11× | 5,5% prevalence í pilot. Sterkt confounded við byggar + matsvaedi + EINFLM. FASTEIGNAMAT er þegar geo-adjusted af HMS. |
| Internal garage access | 4× | Standard í yngri SFH, vantar í eldri. Byggar + canonical_code capture. |
| Arkitekta-teiknað | 2× | 1% prevalence, of sparse til að bera ML signal. Marketing-frekar en price-driver. |
| Botngata / innst í götu | 2× | 1% prevalence, óljóst mælt, alþjóðleg literatúr finnur lítinn premium á fjölbýlis-grade 47K records. |
| Proximity-amenities (skóli, leikskóli, völlur) | 14× | Overlap við matsvaedi_bucket geography features. Agent-stated proximity er síst reliable en objective distance. |
| Kitchen sub-features (eyja, borðkrókur, backsplash) | 6× | Of granular; existing narrative captures concept. |
| First-time-buyer stamp-duty discount | 2× | Legal info, ekki property feature. |
| Maintenance history ("til fyrirmyndar alla tíð") | 2× | Claims án verifiability; tightened `well_maintained` status fangar samsvarandi eftir system prompt fix. |
| Heating system type (geothermal/district/electric) | 2× | Regional determinism; derivast af postnr. |

**Estimated impact**: 93 → 108 fields. Output tokens +6–8%. Per-listing kostnaður $0,0067 → ~$0,0071. Re-pilot 200: $1,35 → ~$1,42. Batch 47K: $156 → ~$165. Trivial delta.

---

## Nýjar fields — ítarleg spec

### Size & legal cluster (6)

#### `unregistered_space_present`

**Tegund**: trilemma (`yes` / `no` / `not_mentioned`)

**Skilgreining**: Lýsing nefnir eksplisít space sem ekki er skráð í fasteignaskrá (óskráð rými, aukaflatar, óskráðir m² undir þaki eða í kjallara).

**Trigger phrases (yes)**:
- „óskráð rými"
- „óskráðir fermetrar"
- „óskráðir m²"
- „aukaflatar ekki skráð"
- „neðri hæð er ekki skráð"
- „geymsluloft óskráð" (gildir aðeins ef sagt er m²)

**Null rule**: Ef lýsing nefnir „háaloft" eða „kjallari" án að segja m² eða án að nefna að rými sé ekki skráð → `not_mentioned`. Þetta er til að forðast að gera ráð fyrir óskráðu þegar það er bara layout-description.

**Explicit `no`**: Aðeins ef lýsing segir beint „allt rýmið er skráð" eða „engar óskráðar breytingar" (sjaldgæft).

---

#### `unregistered_space_sqm_stated`

**Tegund**: `int | null`

**Skilgreining**: Fermetrafjöldi óskráðs rýmis ef nefndur í lýsingu. Null ef `unregistered_space_present != yes` eða ef `yes` en engin tala nefnd.

**Trigger patterns**:
- „Óskráð rými á neðri hæð er u.þ.b 40 fm" → 40
- „um 25 fermetrar óskráð" → 25
- „20 m² aukaflatar sem ekki eru skráðir" → 20
- „Aukaflatar um 15 fm" → 15 (ef samhengi bendir á óskráð)

**Edge cases**:
- Bil („30–40 fm"): nota miðpunkt (35).
- „u.þ.b.", „um", „ca.": nota töluna sem gefin er (ekki round up).
- Ef margar tölur eru nefndar (t.d. óskráð kjallari + óskráð loft): summa þær.

---

#### `unregistered_space_type`

**Tegund**: multi-select enum (0 eða fleiri) af:
- `loft_attic` (háaloft, þakgluggar, geymsluloft með lofthæð)
- `basement` (kjallari, neðri hæð)
- `addition` (viðbygging, sólstofa, útbygging)
- `garage_converted` (bílskúr breyttur í íbúðarrými)
- `other`
- `none` (notað aðeins þegar `unregistered_space_present = no`)

**Skilgreining**: Hvers konar rými er óskráða. Multi-select því sumar lýsingar nefna tvö (t.d. óskráð kjallaraherbergi + óskráð háaloft).

**Ef `unregistered_space_present = not_mentioned`**: `[]` (empty list).

---

#### `has_secondary_unit`

**Tegund**: trilemma (`yes` / `no` / `not_mentioned`)

**Skilgreining**: Lýsing nefnir aðskilda sub-unit innan sömu eignar sem hægt er að leigja út eða nota sjálfstætt. Þetta er functional status, ekki legal duplex classification (sem lifir í canonical_code = APT_DUPLEX ef á við).

**Trigger phrases (yes)**:
- „aukaíbúð"
- „stúdíóíbúð með sér inngangi"
- „sér inngangur á neðri hæð"
- „aðskilin einstaklingsíbúð"
- „rekstrarhæf tveggja íbúða eign"
- „möguleiki á leigu á neðri hæð"
- „sér stúdíó í kjallara"

**Distinction frá `is_duplex`**:
- `is_duplex = yes`: eignin hefur tvær hæðir innan einnar íbúðar (stairs inside unit)
- `has_secondary_unit = yes`: eignin hefur aðskilda second unit (separate entrance, separate kitchen/bath, leasable)

Eign getur verið bæði (t.d. efri hæð er duplex með tveimur hæðum og neðri hæð er aukaíbúð). Þessir eru independent flags.

**Explicit `no`**: Ef lýsing segir „ekki með aukaíbúð" eða „eitt samfélags heimili" (rare). Oftast `not_mentioned` ef ekki rætt.

---

#### `ceiling_height_premium`

**Tegund**: trilemma (`yes` / `no` / `not_mentioned`)

**Skilgreining**: Lýsing nefnir lofthæð sem premium feature — óvenju há loft, hvolf, sýnileg burðarvirki.

**Trigger phrases (yes)**:
- „mikil lofthæð"
- „hátt til lofts"
- „3 metra lofthæð" (eða hvaða tala yfir 2,6m)
- „uppteknu lofti"
- „loftsýn"
- „sperruloft"
- „hvelfing"
- „hvolf-loft"

**Explicit `no`**: Rare. Ef lýsing segir „lág loft" eða „2,3 metra lofthæð" (skýrt undir standard).

**Standard lofthæð**: 2,5–2,6m er íslenskt byggingarrétt-minimum; nefning á „eðlileg lofthæð" án hype → `not_mentioned`.

---

#### `unused_building_rights_present`

**Tegund**: trilemma (`yes` / `no` / `not_mentioned`)

**Skilgreining**: Lýsing nefnir að lóð eða bygging hafi ónýtt byggingarrétt (unused development rights), sem er raunverulegt verðmæti ekki captured í FASTEIGNAMAT.

**Trigger phrases (yes)**:
- „ónýttur byggingarreitur"
- „ónýtt byggingarréttindi"
- „hægt að stækka um X fm"
- „byggingarréttur til viðbótar hæða"
- „samþykkt teikning á stækkun"
- „deiliskipulagsbreyting heimilar stækkun"
- „ónýtt nýtingarhlutfall"

**Null rule**: „Stór lóð" eða „rúmgóð lóð" án explicit byggingarréttar → `not_mentioned`. Aðeins flagged ef lýsing eksplisít bendir á development potential.

---

### Outdoor cluster (5)

#### `lot_type`

**Tegund**: enum
- `private_einkalod` (einkalóð, eign á eigin lóð — typical SFH)
- `shared_sameign` (sameiginleg lóð — typical APT með fjölbýlishúsi)
- `private_in_shared_serlod` (sérlóð innan sameiginlegrar lóðar — APT með eigin outdoor-svæði afmörkuðu)
- `not_applicable` (t.d. penthouse án outdoor)
- `not_mentioned`

**Skilgreining**: Legal/functional status af lóðinni sem eignin stendur á. **Biggest-impact field í v0.2.2**: sérlóð á APT er major premium (oft 5–10% verðmunur) og var ónefnt í v0.2.1.

**Trigger phrases**:

| Value | Phrases |
|---|---|
| `private_einkalod` | „einkalóð", „eign á eigin lóð", „sjálfstæð lóð" |
| `shared_sameign` | „sameiginleg lóð", „sameign", „hluti af fjölbýlishúsi" |
| `private_in_shared_serlod` | „sérlóð", „eigin garður innan sameignar", „afmarkaður garður", „sér garðhluti" |
| `not_applicable` | Penthouse með engum outdoor og engin sameign nefnt, eða efsta hæð án svala |

**Implicit defaults**: Má leiða af canonical_code ef ekkert er nefnt?
- SFH_DETACHED án lýsingar → typically `private_einkalod`, en Claude á að flagga `not_mentioned` ekki að giska (keep extraction honest).
- APT_* án lýsingar → typically `shared_sameign`, sama regla: `not_mentioned`.

Labeling-guide mun líklega instrúcera post-processing imputation af defaults þegar `not_mentioned`, en extraction layer heldur honest.

---

#### `lot_orientation`

**Tegund**: enum
- `south_southwest` (sól, premium)
- `east_west` (morgun-/kvöldsól)
- `north_shade` (lítil sól, skuggi)
- `mixed` (marghliða eign, sól frá fleiri hliðum)
- `not_mentioned`

**Skilgreining**: Afstaða lóðar / aðal útisvæðis gagnvart sólinni. Meaningful á Íslandi þar sem sólarhreyfing er breið (±90° milli sumar og vetur) og norðurhlíðar fá lítið beint sól.

**Trigger phrases**:
- „Suðurlóð" / „suður-lóð" → `south_southwest`
- „Suðvestur" → `south_southwest`
- „Austur-vestur" → `east_west`
- „Morgun-sól og kvöldsól" → `east_west`
- „Norður" / „í skugga" → `north_shade`
- „Sól allan daginn" → `mixed` (ef margvíslegar áttir) eða `south_southwest` (ef aðeins suður)
- „Hornlóð með sól frá þremur áttum" → `mixed`

**Applicability**: Gildir fyrir allar canonical-types. Ef eignin er APT án outdoor-svæðis, nota `not_mentioned` (ekki `not_applicable`).

---

#### `garden_size_framing`

**Tegund**: enum
- `unusually_large` (nefnt sem óvenjulega stórt, „mikill garður", „stór lóð")
- `large` (nefnt jákvætt sem stórt án hype)
- `standard` (nefnt sem eðlilegt / svipað öðrum)
- `small` (nefnt sem lítið eða takmarkað)
- `not_mentioned`

**Skilgreining**: Framing size-ins á garðinum / lóðinni samkvæmt lýsingu. **Decoupled frá garden_quality** (sem er nú condition-only — sjá refactor hér fyrir neðan).

**Trigger phrases**:

| Value | Phrases |
|---|---|
| `unusually_large` | „afar stór lóð", „óvenjulega stór garður", „mikill garður", „eitt helsta trompið" |
| `large` | „stór garður", „rúmgóð lóð", „góð lóð" |
| `standard` | „hefðbundin lóð", „garður" (án lýsingar), engin ability / athugasemd |
| `small` | „lítil lóð", „takmarkaður garður", „lítill garðbletti" |
| `not_mentioned` | Ekki rætt í lýsingu |

**Athugasemd**: Orð eins og „fallegur garður" eða „vel hirtur garður" eru condition-signal, ekki size-signal — fara í `garden_quality`, ekki hér.

---

#### `is_corner_lot`

**Tegund**: trilemma (`yes` / `no` / `not_mentioned`)

**Skilgreining**: Lýsing nefnir að eignin sé á hornlóð (corner lot). Veitir oft fleiri gluggaáttir, meira ljós, meiri privacy í fjölbýlis-context.

**Trigger phrases (yes)**:
- „hornlóð"
- „horn-lóð"
- „hornhús" (SFH context)
- „endalóð með tveimur götum"

**Explicit `no`**: Rare. Oftast `not_mentioned`.

**Applicability**: Meaningful fyrir SFH_DETACHED, SEMI_DETACHED, ROW_HOUSE (end unit). Fyrir APT er þetta sjaldan relevant nema eignin sé horn-íbúð (handled af floor-plan narrative, ekki hér).

---

#### `is_waterfront_or_seaside`

**Tegund**: trilemma (`yes` / `no` / `not_mentioned`)

**Skilgreining**: Lýsing nefnir sjó-eða-vatnsstaðsetningu sem direct feature. **Ekki útsýnið einlegt** (það er í `view_type = sea`), heldur að eignin sé **við sjó**.

**Trigger phrases (yes)**:
- „við sjó"
- „sjávarlóð"
- „við höfnina"
- „beint fyrir ofan strönd"
- „vatnalóð við Elliðavatn" (hvaða lake sem er)
- „bryggja fylgir"

**Distinction**:
- Útsýni á sjó frá fjarlægð → `view_type = sea`, **ekki** `is_waterfront_or_seaside = yes`.
- Eign á sjávarbakka → **bæði** `view_type = sea` og `is_waterfront_or_seaside = yes`.

**Explicit `no`**: Rare. Oftast `not_mentioned`.

---

### Intra-unit cluster (2)

#### `laundry_configuration`

**Tegund**: enum
- `dedicated_room` (sér þvottahús innan íbúðar, aðskilið rými)
- `hookup_only` (tengi fyrir þvottavél í baðherbergi eða eldhúsi, ekki sér-rými)
- `shared_or_none` (sameiginlegt þvottahús í sameign, eða engin aðstaða nefnd)
- `not_applicable` (leiguíbúð án þvotta-infra?)
- `not_mentioned`

**Skilgreining**: Hvar þvottavél/þurrkari býr í eigninni. Discovery: 6× í LLM, sterkt signal í APT þar sem sér þvottahús er premium.

**Trigger phrases**:

| Value | Phrases |
|---|---|
| `dedicated_room` | „sér þvottahús", „þvottahús innan íbúðar", „þvottaherbergi", „þvottaeldhús" |
| `hookup_only` | „tengi fyrir þvottavél", „þvottavélar-tengi í baðherbergi", „þvotta-aðstaða í baðherbergi" |
| `shared_or_none` | „sameiginlegt þvottahús", „þvottahús í sameign", eða explicit „ekkert þvottahús" |
| `not_mentioned` | Lýsing nefnir ekki |

**Distinction frá `storage_type`**:
- `storage_type` inniheldur `thvotta_in_unit` og `thvotta_sameign` sem multi-select flags. Ný field `laundry_configuration` er richer (aðgreinir dedicated_room frá hookup_only).
- Post-processing: `laundry_configuration = dedicated_room` → set `storage_type` includes `thvotta_in_unit`. Consistency check í merge logic.

---

#### `end_unit_position`

**Tegund**: trilemma (`yes` / `no` / `not_mentioned`)

**Skilgreining**: Fyrir ROW_HOUSE og SEMI_DETACHED, hvort eignin sé end-unit (endaraðhús, endi-semi) frekar en middle-unit. Discovery: 5× í LLM. End-units hafa þriðju gluggaátt, meira ljós, oft auka outdoor access.

**Trigger phrases (yes)**:
- „endaraðhús"
- „enda-hús"
- „endahús í röð"
- „enda-semi"
- „ysta hús í röðinni"
- „eitt af tveimur endahúsum"

**Explicit `no`**:
- „miðju-raðhús"
- „miðjuhús í röðinni" 
- „millihús"

**Applicability**:
- Gildir: ROW_HOUSE, SEMI_DETACHED
- Fyrir SFH_DETACHED, APT_*, SUMMERHOUSE: alltaf `not_mentioned` (applicability mismatch)

Post-processing getur gated þessa field á canonical_code ∈ {ROW_HOUSE, SEMI_DETACHED} og imputed `not_applicable` utan þess.

---

### Listing dynamics cluster (2)

Þessir tvö er **ekki** verðmats-features per se — þau eru raw hráefni í ask-to-sale-gap módel (Áfangi 7) og market-dashboard time-on-market analytics (Áfangi 10). Vistast sem extractuð gögn en koma ekki sjálfkrafa í iter3-features. Aðskilin section í JSON output.

#### `sale_channel`

**Tegund**: enum
- `private_einkasala` (eigandi selur beint án milligöngu)
- `agent_normal` (ef lýsing nefnir fasteignasala eða listingin hefur standard agent template)
- `not_mentioned`

**Skilgreining**: Söluleið. Discovery: 9× endurtökur í LLM.

**Trigger phrases**:
- `private_einkasala`: „kynnir í einkasölu", „einkasala", „eigandi selur", „höfð í einkasölu"
- `agent_normal`: lýsing vísar til fasteignasala, company-header, standard closer („allar nánari upplýsingar hjá..."), eða einfaldlega ekki flagged sem einkasala

**Rationale**: Einkasala getur endurspeglað motivated seller (sparar commission) eða off-market eigna sem fer nú á opinn markað. Notable list-to-sale-gap signal.

---

#### `immediate_availability`

**Tegund**: trilemma (`yes` / `no` / `not_mentioned`)

**Skilgreining**: Lýsing segir að eignin sé laus strax eða innan stutts tíma. Discovery: 6× í LLM.

**Trigger phrases (yes)**:
- „laus strax"
- „eignin er laus"
- „flutningsdagur við undirskrift"
- „tilbúin til afhendingar"
- „lykil við undirskrift"

**Explicit `no`**:
- „afhendist eftir X mánuði"
- „seljandi óskar lengri afhendingartíma"
- „samkvæmt samkomulagi" (oftast `not_mentioned` í staðinn, en eksplisítt „eftir Y mánuði" er `no` á immediate)

**Rationale**: Immediate availability correlates neikvætt við time-on-market (selur hraðar) og getur haft áhrif á final sale price (motivated seller). Ekki direct verðmats-feature, en stock-signal.

---

## Refactor: `garden_quality` decoupled

V0.2.1 values blönduðu size + condition: `premium`, `standard`, `minimal`, `none`, `not_mentioned`.

**V0.2.2 values — condition-only**:
- `well_landscaped_mature` (garður vel hirtur, trjágróður, vandað landscape)
- `standard_maintained` (garður hirtur, ekkert special)
- `minimal_or_neglected` (grassflötur, án vinnslu, eða vanhirt)
- `none` (engin garður)
- `not_mentioned`

**Af hverju**: V0.2.1 value `premium` var oft triggered af „stór garður" (size) frekar en „fallegur garður" (condition). Nú fer size í `garden_size_framing` og condition í `garden_quality`. Orthogonal aftur.

**Trigger phrases fyrir condition**:

| Value | Phrases |
|---|---|
| `well_landscaped_mature` | „vel hirtur garður", „mature gróður", „fallega ræktaður", „einstaklega fallegur garður", „mikið af trjám", „grasflötur með blómabeðum" |
| `standard_maintained` | „hefðbundinn garður", „garður" (án lýsingar), „grasflötur" |
| `minimal_or_neglected` | „vanhirtur", „þarf að fara yfir garðinn", „gróður í flugti" |
| `none` | Explicit „engin garður", eða APT án outdoor |
| `not_mentioned` | Ekki rætt |

**Post-processing note**: V0.2.1 values mappast til v0.2.2 approximately sem:
- `premium` → `well_landscaped_mature` (en losa gæti verið false matches ef v0.2.1 picked „premium" aðeins fyrir size). Re-extraction leysir.
- `standard` → `standard_maintained`
- `minimal` → `minimal_or_neglected`
- `none` → `none`
- `not_mentioned` → `not_mentioned`

Þar sem við re-keyrum pilot á 200 og svo full batch á 47K, þarf ekki retro-mapping af v0.2.1 pilot data.

---

## System prompt refinements (v0.2.2)

Þrjár concrete breytingar á system prompt, drívaðar af pilot-niðurstöðum:

### Refinement 1: `well_maintained` tightening

**Vandamál í v0.2.1**: Claude flaggaði 64% eldhúsa, 60% primary_bathrooms og 54% flooring sem `well_maintained`. Investigation sýndi að trigger var oft marketing puffery + feature description („fallegt eldhús, granít borðar") frekar en explicit condition signal.

**Ný regla í system prompt**:

> `well_maintained` krefst **explicit condition language** í lýsingu. Þessir phrasar eru valid triggers:
> - „í góðu standi"
> - „vel viðhaldið" / „hefur verið vel viðhaldið"
> - „í topp standi" / „í prima standi"
> - „snyrtilegt" (í context um ástand, ekki bara útlit)
> - „gott viðhald"
>
> Eftirfarandi eru **ekki** valid triggers fyrir `well_maintained`:
> - „fallegt", „glæsilegt", „björt", „vönduð" — þetta er marketing puffery, ekki condition signal
> - Feature description án condition frasa („granít borðar", „nútíma innrétting", „hágæða tæki") — þetta lýsir gerð, ekki ástandi
> - Implicit wellness af því að nýbygging er nefnd — nota `original_functional` ef byggar er innan 5 ára og status ekki explicit
>
> Ef lýsing nefnir component en án explicit condition signal → `not_mentioned`. Fyrir nýlega byggð eign (byggar innan 5 ára) þar sem component er ónefndur → `original_functional` getur verið fit, en aðeins ef nothing else suggests renovation.

**Expected effect**: well_maintained distribution fer úr 60% → <30% á kitchen, primary_bathroom, flooring components. Þessar drop-outs fara í not_mentioned (ekki `original_functional`, vegna strict regluna ofan).

---

### Refinement 2: „Þak" vs „þakkantur" distinction

**Vandamál í v0.2.1**: Row 14 SFH Sandgerði — lýsing segir „eftir er að klæða undir þakkantinn" (roof-edge cladding incomplete). Claude flaggaði `roof_status = in_progress` og `cladding_status = in_progress`. Raunin: aðeins cladding_in_progress; þakið sjálft er ekki nefnt.

**Ný regla í system prompt**:

> **„Þak" vs „þakkantur" / „sperra" distinction**:
> - `roof` component vísar til **þakið sjálft** (undirlag, þakjárn, þakplötur) — byggingar-wide skiptiaðgerð.
> - `cladding` component vísar til **ytri klæðningar** á veggjum, **OG undir þakkantur** (vegna þess að þakkantur er eaves-cladding, ekki roof structure).
>
> Dæmi:
> - „eftir er að klæða undir þakkantinn" → `cladding_status = in_progress`, `roof_status = not_mentioned`
> - „nýtt þak" → `roof_status = replaced_new`
> - „klæðning á veggjum og þakkanti" → `cladding_status` (bæði á veggjum og þakkanti er cladding-task)
> - „nýjar sperrur" → `roof_status = replaced_new` (sperrur eru roof structure)
> - „ný þakskegg" → `cladding_status = replaced_new` (þakskegg = eaves-trim, er cladding)

**Expected effect**: Ekki lengur over-flag á roof_status fyrir klæðningar-sub-verk.

---

### Refinement 3: `listing_elaboration` recalibration

**Vandamál í v0.2.1**: Distribution var 68% elaborate, 26% promotional_heavy, 6% standard, 0% terse. Either threshold too low eða sample bias frá 300-3000 char length filter.

**Ný regla í system prompt**:

> `listing_elaboration` er byggt á **orðafjölda** í lýsingu, með þessum þröskuldum:
> - `terse`: <150 orð. Basic list af features, lítið narrative.
> - `standard`: 150–300 orð. Main features nefndir, einhverjir detail.
> - `elaborate`: 300–600 orð. Rich detail, multiple rooms described, some agent context.
> - `promotional_heavy`: 600+ orð **EÐA** heavy promotional language („draumaeign", „einstök", „þú verður að sjá þetta" í ýmsum formum, explicit hype margfaldað).
>
> Reikna orð á einfaldan hátt: splitta á hvítstaf, telja token-fjölda. Round-up ef við þröskulds-línu.

**Expected effect**: Distribution færist til standard-elaborate rangein. Terse verður örfárir í sampleinu (vegna 300+ char filter), standard verður algengari.

---

### Refinement 4: Óskráð rými guidance (bætist við)

**Ný regla í system prompt**:

> **Óskráð rými (unregistered space)** — skoða sérstaklega eftir þessum phrasum:
> - „óskráð", „óskráðir", „ekki skráð", „aukaflatar ekki skráð"
> - Töluyfirlýsingar eins og „40 fm óskráð", „um 25 m² sem ekki eru á teikningum"
>
> Ef nefnt:
> 1. `unregistered_space_present = yes`
> 2. Ef fjöldi er nefndur → `unregistered_space_sqm_stated` = heiltala (round ef þarf).
> 3. `unregistered_space_type` multi-select: velja `loft_attic`, `basement`, `addition`, `garage_converted`, `other` (0+).
>
> Ef lýsing nefnir „háaloft" eða „kjallara" án að segja að það sé óskráð og **án að gefa m²** → `unregistered_space_present = not_mentioned`. Ekki gera ráð fyrir að háaloft sé óskráð.

---

### Third few-shot example (nýtt)

V0.2.1 hafði 2 few-shot examples (Vesturbæjar elaborate + Akranes terse). V0.2.2 bætir við þriðja sem sýnir SFH með multiple v0.2.2-only signals captured correctly. Canonical example: pilot row 8.

**Example 3 structure** (skrifað ítarlega í `pilot_extract.py` update):

- Input: útdráttur úr pilot row 8 lýsingu (SFH_DETACHED, óskráð rými, sérlóð, mikla lofthæð)
- Output JSON með:
  - `unregistered_space_present = yes`
  - `unregistered_space_sqm_stated = 40`
  - `unregistered_space_type = ["basement"]`
  - `ceiling_height_premium = yes`
  - `lot_type = private_einkalod` (SFH með einkalóð)
  - `garden_size_framing = large` (ef rætt)
  - `garden_quality = well_landscaped_mature`
  - öll component fields eins og í lýsingu
  - property_narrative sem nefnir óskráða rýmið sem value add

Sjá `pilot_extract.py` update spec fyrir nákvæman texta.

---

## Field-count summary (v0.2.2)

| Category | # fields v0.2.1 | # fields v0.2.2 | Breyting |
|---|---|---|---|
| Component-status matrix (18 × 3) | 54 | 54 | — |
| Augl-supplement trilemma | 7 | 7 | — |
| Útsýni | 2 | 2 | — |
| Útipláss detail | 5 | 5 | — (garden_quality refactored, ekki bætist við) |
| **Size & legal (nýtt í v0.2.2)** | 0 | 6 | **+6** |
| **Outdoor extension (nýtt í v0.2.2)** | 0 | 5 | **+5** |
| Bílastæði detail | 3 | 3 | — |
| Layout | 6 | 6 | — |
| **Intra-unit extension (nýtt í v0.2.2)** | 0 | 2 | **+2** |
| Byggingin & annað | 5 | 5 | — |
| Negative signals | 3 | 3 | — |
| Agent framing | 3 | 3 | — |
| **Listing dynamics (nýtt í v0.2.2)** | 0 | 2 | **+2** |
| Narrative | 1 | 1 | — |
| Meta | 4 | 4 | — |
| **Samtals** | **93** | **108** | **+15** |

---

## Output JSON structure (v0.2.2 sketch — bara breyttir hlutar)

```json
{
  "augl_id": "...",
  "extraction_version": "v0.2.2",
  "model": "claude-haiku-4-5",
  "extracted_at": "2026-04-DD HH:MM:SS.ssssss",

  // ... component-matrix og existing sections eins og v0.2.1 ...

  "size_and_legal": {
    "unregistered_space_present": "yes",
    "unregistered_space_sqm_stated": 40,
    "unregistered_space_type": ["basement"],
    "has_secondary_unit": "no",
    "ceiling_height_premium": "yes",
    "unused_building_rights_present": "not_mentioned"
  },

  "outdoor_extension": {
    "lot_type": "private_einkalod",
    "lot_orientation": "south_southwest",
    "garden_size_framing": "large",
    "is_corner_lot": "no",
    "is_waterfront_or_seaside": "not_mentioned"
  },

  "intra_unit_extension": {
    "laundry_configuration": "dedicated_room",
    "end_unit_position": "not_mentioned"
  },

  "listing_dynamics": {
    "sale_channel": "agent_normal",
    "immediate_availability": "yes"
  },

  "garden_quality": "well_landscaped_mature"  // refactored, condition-only
  // ... rest of situational fields unchanged ...
}
```

---

## Post-extraction feature engineering (v0.2.2 additions)

### Nýjar derived features fyrir iter3

Þetta fer í feature-engineering script eftir batch extraction, ekki extraction step-ið sjálft.

```python
# Size & legal derived
has_unregistered_space = unregistered_space_present == "yes"
unregistered_sqm_numeric = unregistered_space_sqm_stated if has_unregistered_space else 0
size_total_with_unregistered = EINFLM + unregistered_sqm_numeric
size_unregistered_ratio = unregistered_sqm_numeric / EINFLM if EINFLM > 0 else 0

has_unused_building_rights = unused_building_rights_present == "yes"
has_ceiling_height_premium = ceiling_height_premium == "yes"
has_secondary_unit_flag = has_secondary_unit == "yes"

# Outdoor derived
is_private_lot = lot_type in ["private_einkalod", "private_in_shared_serlod"]
lot_type_serlod = lot_type == "private_in_shared_serlod"  # specifically APT premium
has_sun_orientation = lot_orientation in ["south_southwest", "east_west", "mixed"]
is_waterfront = is_waterfront_or_seaside == "yes"
is_corner = is_corner_lot == "yes"
garden_size_ordinal = {
    "unusually_large": 2, "large": 1, "standard": 0, "small": -1, "not_mentioned": None
}[garden_size_framing]

# Intra-unit derived (applicable per canonical_code)
laundry_dedicated = laundry_configuration == "dedicated_room"
is_end_unit_row = (canonical_code == "ROW_HOUSE" and end_unit_position == "yes")
is_end_unit_semi = (canonical_code == "SEMI_DETACHED" and end_unit_position == "yes")
```

### Listing dynamics (separate pipeline fyrir Áfanga 7)

Ekki joinað við iter3 training matrix. Vistast í aðskilinni töflu `listing_dynamics_v1.parquet` (faerslunumer ↔ sale_channel, immediate_availability, og aðrar agent-framing fields) fyrir ask-to-sale-gap og time-on-market modelling downstream.

---

## Validation planar fyrir 3c re-pilot

Eftir v0.2.2 re-pilot á sömu 200 listings, bera saman við v0.2.1 output á:

**Quality improvements (expected)**:
- `well_maintained` distribution á kitchen, primary_bathroom, flooring: target <30% (frá 54–64%)
- `roof_status = in_progress` false-positives: target 0 á þekktu row 14 pattern
- `listing_elaboration` distribution: target 20–30% standard, 50–60% elaborate, <15% promotional_heavy, <5% terse
- Row 8-style extractions: `unregistered_space_present = yes` með correct m² í ≥90% cases

**New field sanity checks**:
- `lot_type` distribution: SFH_DETACHED dominates `private_einkalod`, APT dominates `shared_sameign`, appearance af `private_in_shared_serlod` ≥3% (at least some APT with sérlóð captured)
- `laundry_configuration`: `dedicated_room` appears í ≥15% af APT_STANDARD og SFH (sampled distribution)
- `end_unit_position = yes` kemur fyrir í ≥10% af ROW_HOUSE rows
- `unregistered_space_present = yes` kemur fyrir í 15–25% af SFH + SEMI (consistent við manual 50-row scan sem flagged 24%)

**Failure modes að watch for**:
- Ef `lot_type = not_mentioned` í >60% APT-rows: trigger phrases ekki að virka, refine system prompt frekar
- Ef `unregistered_space_sqm_stated` kemur sem string (t.d. „40") í stað int: add type-coercion í post-processing
- Ef `end_unit_position = yes` kemur í SFH_DETACHED (applicability mismatch): tighten system prompt til að clarify applicability

---

## Deferrals (backlog fyrir v0.3)

1. **Nýbyggingar sub-schema**: `finish_package_level` (Pakki 1/2/3), `delivery_status`, `early_occupancy_available`, `building_permit_status`. Trigger: batch round 1 sýnir að nýbyggingar exacta worse en expected og þarf dedicated handling.
2. **Sumarbústaða-dedicated schema**: land-value, amenity proximity, ekki sama rich component matrix. Trigger: SUMMERHOUSE iter3.
3. **Image-based features**: Claude-Sonnet-með-vision á myndum. Trigger: UI explainability í Áfanga 9 eða funding unlocked.
4. **Cross-listing consistency checks**: sama eign listuð ítrekað, temporal consistency á extracted values. Post-processing, ekki extraction-step.
5. **Heated outdoor surfaces dedicated field**: rejected í v0.2.2 vegna collinearity við byggar/matsvaedi, en keep in mind ef iter3 residuals benda á það sem missed signal.

---

## Iteration path fyrir 3c→3d

1. **V0.2.2 schema frystist hér** (þetta skjal).
2. **`pilot_extract.py` updated** með v0.2.2 tool schema, tightened system prompt (4 refinements), þriðja few-shot example.
3. **Re-pilot á 200 listings** á Haiku 4.5 með v0.2.2 (~$1,42). Danni keyrir á D:\.
4. **Validate output** á quality targets hér að ofan. Ef pass → freeze v0.2.2 og skrifa `batch_extract.py`.
5. **Batch extract 47K unique** via Batch API í 5 chunks. Resume-safe, dedup propagation með `extraction_group_size`.
6. **Post-processing**: merge í `training_data_v2.pkl` fyrir Áfanga 4 iter3 training.

Ef re-pilot á 200 sýnir further issues (t.d. new systematic bias), v0.2.3 fylgir og endurtaka cycle áður en batch.
