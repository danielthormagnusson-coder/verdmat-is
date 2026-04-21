# TAXONOMY — Eignaflokkun

Canonical flokkun sem notuð er í verðmatsmódelinu og markaðsyfirliti. Sannleiksuppsprettan er HMS fasteignaskrá `tegund`. Listings `tegund` og kaupskrá `TEGUND` eru coarser/messier og notað til fallback.

**Staða**: Finalized 18. apríl 2026 á grundvelli fulls audit af 514 distinct HMS tegundum í `fasteignir_merged.db` (124.834 ok-eignir). Sjá `classify_property.py` fyrir canonical logic.

---

## Eignaflokka-fjölskyldur

Taxonomy er skipt í fjórar fjölskyldur. Hver fjölskylda fær sína meðhöndlun í verðmatspipeline.

### 1. MAIN residential — aðalmódel (sameinað baseline)

Deilir grunnmódeli fyrir pr-m² verðspá. Segmentering á milli þessara er gerð í gegnum feature input í LightGBM (einn módel, margar segment-coefficients).

| Canonical code | HMS tegund | Listings tegund | Kaupskrá TEGUND | Lýsing |
|---|---|---|---|---|
| `SFH_DETACHED` | Einbýlishús, Einbýli | einb | Einbýli | Sjálfstætt einbýlishús |
| `SEMI_DETACHED` | Parhús | raðpar/radpar* | Sérbýli* | Parhús — tvö hús sem deila vegg |
| `ROW_HOUSE` | Raðhús | raðpar/radpar* | Sérbýli* | Raðhús — þrjú eða fleiri hús í röð |
| `APT_FLOOR` | Íbúð á hæð | hæðir/haedir | Fjölbýli | Full hæð, oft með sérinngangi |
| `APT_STANDARD` | Íbúð, Íbúð [A-Z/1-9...] | fjolb/fjölb | Fjölbýli | Venjuleg íbúð í fjölbýli |
| `APT_BASEMENT` | Íbúð í kjallara | fjolb | Fjölbýli | Kjallaraíbúð |
| `APT_ATTIC` | Íbúð í risi | fjolb | Fjölbýli | Rishæð |

\* Listings og kaupskrá sameina parhús og raðhús í eitt. HMS er authoritative.

### 2. SECONDARY residential — aðskilið pr-m²

Þessar eignir eru aðrir íbúðaflokkar en fá ekki að deila pr-m² baseline með aðalmódeli. Hver þeirra fær eigin pr-m² estimate, annað hvort:

- Sem offset-coefficient relative to MAIN (shared backbone), þar sem módelið lærir t.d. `price_senior = price_std × (1 + δ_senior)` og δ er lærður á gögnunum, eða
- Sem sjálfstætt LightGBM-módel ef volume leyfir og residual-pattern er marktækur.

Ákvörðun á architecture í Áfanga 2 eftir baseline er keyrt.

| Canonical code | HMS tegund | Tilfelli | Lýsing |
|---|---|---|---|
| `APT_SENIOR` | Öryggisíbúð | 89 | Íbúð fyrir eldri borgara með þjónustu. Restricted buyer pool — verðmyndun systematíkt öðruvísi. |
| `APT_ROOM` | Íbúðarherb í kjall, Íbúðarherb á hæð, Íbúðarherbergi, Íbúðarherb í risi | 54 | Íbúðarherbergi. Ekki sjálfstæð íbúð — getur verið á söluskjali með aðaleign. |
| `APT_HOTEL` | Hótelíbúð, Hótelíbúðir | 65 | Commercial/rental market. Minni rými, hærra pr-m². |
| `APT_MIXED` | Íbúð/vinnustofa | 5 | Live-work loft. Fáar tilfelli í v1. |
| `APT_UNAPPROVED` | Ósamþykkt íbúð, ósamþ íbúð | 155 | Discount-aður flokkur vegna non-approval. |

**Samtals í secondary**: 368 eignir (0,3%). Lítið volume en hvert record er marktækt pr-m² frábrugðið aðal-módeli.

### 3. SUMMERHOUSE — sérmódel

| Canonical code | HMS tegund | Tilfelli |
|---|---|---|
| `SUMMERHOUSE` | Sumarbústaður | 4.264 |
| `SUMMERHOUSE` | Sumarhús | 169 |
| `SUMMERHOUSE` | Orlofshús | 61 |
| `SUMMERHOUSE` | Veiðihús | 18 |
| `SUMMERHOUSE` | Skíðaskáli | 1 |

**Heildarsafn**: 4.513 (3,6%).

**Athugasemd**: Gestahús (65 tilfelli) er EXCLUDED — of ambiguous (gæti verið aukaeign á sumarbústaðalóð, B&B, eða sjálfstætt smáhús).

### 4. EXCLUDE — ekki í módeli

Heildartala: 14.519 (11,6%), í 365 distinct tegundum.

- **Atvinnuhúsnæði**: Iðnaður, Verslun, Skrifstofa, Vörugeymsla, Veitingahús, Gistiheimili, Gistihús, Vinnustofa, Hótel, Sérhæfð bygging, o.fl.
- **Restricted market / niche**: Verbúð, Sambýlishús, Sambýli, Starfsmannahús, Starfsmannaíbúðir — ekki arm's-length verðmyndun.
- **Land og lóðir**: Jörð, Sumarbústaðaland, Íbúðarhúsalóð, Annað land, Lóð, Ræktunarland, Nytjað, o.fl. `Íbúðarhúsalóð` er fjölbreytt og flókið — útilokum í v1.
- **Landbúnaður**: Hesthús, Fjárhús, Gróðurhús, Fjós, Gripahús, Minkahús, Refahús, Svínahús, Alifuglahús, Sláturhús, o.fl.
- **Stofnanir/opinber**: Skóli, Leikskóli, Félagsheimili, Safn, Slökkvistöð, Íþróttahús, Sjúkrahús, Hjúkrunarheimili, Kirkja, Bókasafn, Kvikmyndahús, o.fl.
- **Geymslur/bílskúrar (standalone)**: Bílskúr, Bátaskýli, Stæði í bílageymslu, Geymslubil, Bílskýli, o.fl.
- **Ambíguous**: Gestahús (65), Herbergi (2).
- **Long-tail data-entry errors**: ~50 stakir 1-count records sem virðast vera heimilisfong eða byggingarnöfn.

---

## Normalizations innan main residential

- `Einbýli` (147) → `SFH_DETACHED` (sama og `Einbýlishús`).
- `íbúð` (213, lowercase) → `APT_STANDARD`.
- `Íbúð A`, `Íbúð 1A`, `Íbúð 33a`, `Íbúð 15.B`, `Íbúð e.h.`, `íbúð A1` o.s.frv. — **114 suffix-afbrigði**, öll APT_STANDARD gegnum regex `^íbúð\s+[a-z0-9.\s-]{1,6}$`.
- `Íbúð og bílskúr` (22) → `APT_STANDARD` + `has_garage=true`.
- `Einbýli - bílskúr` (6) → `SFH_DETACHED` + `has_garage=true`.
- `Raðhús - bílskúr` (5), `Raðhús og bílskúr` (1) → `ROW_HOUSE` + `has_garage=true`.
- `Raðhús 47/49/51` (1 hvor) → `ROW_HOUSE` (data-entry fragments).

---

## Orthogonal flags

Þessir eru ekki sér-flokkar en viðbótareinkenni sem fara sem breytur í módelið. Sum eru triggered af tegundinni sjálfri (bílskúr-combos), önnur koma eingöngu úr `augl_json` fields eða LLM-extraction á `lysing`.

| Flag | Heimild | Lýsing |
|---|---|---|
| `is_penthouse` | Lýsing | Efsta hæð, oft með stórum svölum/þakverönd |
| `is_studio` | Lýsing/fjherb | 1 herbergi, blandað svefn/stofu |
| `has_separate_entrance` | augl `inngangur` + lýsing | Sérinngangur |
| `has_elevator` | augl `lyfta` | Lyfta í byggingu |
| `has_garage` | augl `bilskur` + tegund (bílskúr-combo) + lýsing | Innbyggður/tengdur bílskúr |
| `has_parking_space` | augl `staedi` | Bílastæði (ekki bílskúr) |
| `has_garden` | augl `gardur` | Garður |
| `has_balcony` | augl `svalir` | Svalir |
| `is_accessible` | augl `hjolastoll` | Hjólastólsvænt |
| `is_senior_only` | augl `eldrib` | Listing marketað sem senior-friendly (separat frá APT_SENIOR kanóníska kóðanum sem fangar HMS-registration) |
| `pets_allowed` | augl `pets` | Gæludýr leyfð |
| `ev_charging` | augl `rafbill` | Hleðslustöð |

**Skýring á APT_SENIOR vs is_senior_only**: Kanóníski kóðinn `APT_SENIOR` fangar formlega HMS-registration sem Öryggisíbúð — þetta eru íbúðir í þjónustu-kompleksum með restricted buyer pool. Flaggið `is_senior_only` fangar marketing-einkennið í auglýsingu (augl.eldrib=true) — venjuleg íbúð sem er markaðssett fyrir eldri borgara en ekki registered sem Öryggisíbúð. Þessi tvö geta verið present simultaneously eða sjálfstætt.

---

## Segment-breytur fyrir módelið

Aðal-módelið verður segment-aware:

1. **`property_type`** — canonical flokkun að ofan
2. **`is_new_build`** — sjá DECISIONS.md um FULLBUID-regluna
3. **`geography_tier`** — höfuðborgarsvæðið / landsbyggð
4. **`size_band`** — <60m², 60–100, 100–150, 150–200, >200

---

## Coverage summary (post Áfanga 1.1)

| Fjölskylda | # records | % |
|---|---|---|
| MAIN residential (7 canonical codes) | 105.523 | 84,5% |
| SECONDARY residential (5 canonical codes) | 368 | 0,3% |
| SUMMERHOUSE (sérmódel) | 4.513 | 3,6% |
| **Í módeli alls** | **110.404** | **88,4%** |
| EXCLUDE | 14.519 | 11,6% |
| **Samtals** | **124.834** | **100%** |

---

## Aggregate-sölur (multi-unit skjöl)

Þegar ein kaupskrá-færsla nær yfir fleiri en eina einingu (t.d. íbúð + íbúðarherbergi í sama skjali, eða íbúð + bílskúr sem tvær separate FEPILOG einingar undir sama FASTNUM og SKJALANUMER):

- Aðaleining fer í gegnum main-módel fyrir pr-m² verð.
- Aukaeiningar í secondary-módel fyrir eigið pr-m² verð.
- Heildarverðið er summa eininga.

Þetta verður formaliserað í Áfanga 1.5 (listing-to-sale pairing) eða nýjum 1.8 (multi-unit aggregation). Sjá FEPILOG-decoding að neðan.

---

## Gögn gegnum FEPILOG (kaupskrá)

FEPILOG kóðinn í kaupskrá gefur okkur nákvæmari undirflokkun en TEGUND. Þetta þarf decoding í Áfanga 1.2. Frumathugun bendir til:

- `0101XX` — aðalíbúð (mest algengt)
- `0102XX` — seinni íbúð í sömu eign
- `0103XX` — möguleg rishæð eða herbergi
- `0201XX` — bílskúr/geymsla
- `020101` — stakur bílskúr

Þegar FEPILOG er decodað getum við tengt saman einingar á sama skjali fyrir aggregate-sölur.

**TODO**: Finna opinbera FEPILOG key frá HMS eða reverse-engineer á gögnum.

---

## Edge cases — tekið á við

- **Íbúð með suffix (Íbúð A, Íbúð 1A, Íbúð e.h., ...)** — 114 afbrigði, öll APT_STANDARD gegnum regex.
- **Öryggisíbúð** — APT_SENIOR, sekúnder-flokkur. Verðmetin sjálfstætt eða sem offset frá APT_STANDARD.
- **Íbúðarherbergi (4 afbrigði)** — APT_ROOM, sekúnder.
- **Hótelíbúð** — APT_HOTEL, sekúnder.
- **Íbúð/vinnustofa** — APT_MIXED, sekúnder.
- **Ósamþykkt íbúð** — APT_UNAPPROVED, sekúnder.
- **Gestahús** — EXCLUDE (ambiguous: aukabyggð/B&B/smáhús).
- **Verbúð, Sambýlishús, Starfsmannahús** — EXCLUDE (restricted market).
- **Herbergi** (2 tilfelli) — EXCLUDE (of ambiguous).
- **Íbúðarhúsalóð** — EXCLUDE (fjölbreytt og flókið, sleppum).
- **Penthouse-merktar íbúðir** — HMS flokkar ekki sem sér-tegund. Lesum úr lýsingum og set `is_penthouse` flagg.

---

## Viðhaldsregla

Ef ný HMS tegund birtist (t.d. við reglubundið sync), keyra:

```python
from classify_property import classify_property
classify_property('<ný_tegund>')
```

og skoða hvort hún fellur í EXCLUDE by default og hvort það er rétt. Bæta við í `_DIRECT_MAP` ef ný canonical-mapping er þörf. Uppfæra þetta skjal.
