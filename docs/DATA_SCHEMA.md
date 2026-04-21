# DATA SCHEMA — Gagnaskipulag

## Canonical data layer (post-1.6)

```
pre-merge DBs (5x SQLite)
   └─ parse_all_dbs.py + patch_v2_dates.py
         └─ listings_v2.pkl, listings_text_v2.pkl, sales_v2.pkl, properties_v2.pkl
              ├─ pairing.py → pairs_v1.pkl
              └─ geography.py → geography_features.pkl
                    └─ build_training_data.py (Áfangi 2.1) → training_data_v1.pkl
```

**Source**: `D:\Gagnapakkar\fasteignir{,1,2,3,4}.db` (5 SQLite files, ~3 GB)
**Parser**: `D:\parse_all_dbs.py`
**Outputs**:
- `D:\listings_v2.pkl` — 471K listings án lysing texta
- `D:\listings_text_v2.pkl` — (augl_id → lysing) mapping
- `D:\sales_v2.pkl` — 173K sales frá kaups_json
- `D:\properties_v2.pkl` — 125K HMS fasteignaskrá records
- `D:\pairs_v1.pkl` — 174K arm's-length sales með pair_status
- `D:\geography_features.pkl` — 125K per-FASTNUM geo features
- `D:\training_data_v1.pkl` — (post 2.1 build) feature matrix fyrir hedonic baseline
- `D:\parse_summary_v2.txt` — coverage og dedupe stats

**Loading pattern**:
```python
import pandas as pd
pairs = pd.read_pickle(r'D:\pairs_v1.pkl')
clean_fresh = pairs[pairs['pair_status'] == 'paired_fresh']
```

---

## `training_data_v1.pkl` — Áfangi 2.1 feature matrix

Output frá `build_training_data.py`. Ein row per arm's-length single-FASTNUM residential sölu í in-model taxonomy, eftir outlier-filter.

**Row count**: ~148.500 (expected, staðfest við build)

### Features (19 columns — LightGBM input)

| Feature | Type | Notes |
|---|---|---|
| `EINFLM` | float64 | m² einingarstærð (pre-outlier, þegar í 20-1000 range) |
| `BYGGAR` | float64 | Byggingarár |
| `LOD_FLM` | float64 | Lóðarstærð (m²) — einbýli/sérbýli only, NaN fyrir íbúðir |
| `FASTEIGNAMAT` | float64 | Historical fasteignamat á sale date |
| `canonical_code` | category | MAIN/SECONDARY/SUMMERHOUSE kóði (13 categories) |
| `is_new_build` | bool | FULLBUID=0 OR age_at_sale ≤ 2 |
| `matsvaedi_bucket` | category | 213 distinct (M<numer> eða P<postnr>_other) |
| `region_tier` | category | RVK_core / Capital_sub / Country |
| `lat` | float64 | WGS84 latitude |
| `lon` | float64 | WGS84 longitude |
| `postnr` | int64 | Backup geo categorical |
| `unit_category` | category | FEPILOG AA+BB |
| `is_main_unit` | bool | FEPILOG CC == "01" |
| `merking_floor` | float64 | Floor number (0=ground/basement, 1=first, ...) |
| `building_max_floor` | float64 | Max floor í byggingu via landnum grouping |
| `is_top_floor` | float64 (0/1/NaN) | NaN þegar building_max_floor < 2 |
| `floor_fraction` | float64 (NaN) | merking_floor/building_max_floor; NaN þegar max<2 |
| `sale_year` | int | Útdregið úr THINGLYSTDAGS |
| `sale_month` | int | 1–12 |

### Target columns (2)

| Column | Type | Notes |
|---|---|---|
| `real_kaupverd` | float64 | KAUPVERD × CPI factor, ref = latest month (þús. kr) |
| `log_real_kaupverd` | float64 | `log(real_kaupverd)` — LightGBM target |

### Meta columns (retained for join-back / downstream)

| Column | Type | Notes |
|---|---|---|
| `FAERSLUNUMER` | int64 | Kaupskra primary key |
| `FASTNUM` | Int64 | HMS fasteignanúmer |
| `SKJALANUMER` | str | "R-NNNNNN/YYYY" format |
| `THINGLYSTDAGS` | datetime | Sale date |
| `KAUPVERD` | float64 | Nominal kaupverð í þús. kr |
| `cpi_factor` | float64 | CPI factor used for deflation |
| `TEGUND` | category | Kaupskra coarse categorical |
| `tegund` | str | HMS fine-grained tegund |
| `FEPILOG` | str | Raw 6-digit |
| `merking` | str | Raw merking |
| `landnum` | int | HMS lóðarnúmer |
| `matsvaediNUMER` | int64 | For join to non-bucketed geography |
| `age_at_sale` | float64 | sale_year − BYGGAR |
| `split` | str | "train" (≤2023) / "val" (2024) / "test" (2025) / "held" (2026+) |

### Filters applied (cascade)

1. Valid THINGLYSTDAGS (2006-2026)
2. Required fields non-null (FAERSLUNUMER, FASTNUM, KAUPVERD, FASTEIGNAMAT, EINFLM, BYGGAR, ONOTHAEFUR, SKJALANUMER, FEPILOG)
3. Arm's-length (ONOTHAEFUR_SAMNINGUR=0)
4. Single-FASTNUM SKJALANUMER
5. Property join with properties_v2 (inner)
6. In-model taxonomy (MAIN + SECONDARY + SUMMERHOUSE via classify_property)
7. Geography join (inner, expected 100% coverage)
8. Size filter 20 ≤ EINFLM ≤ 1000
9. rules.py full outlier filter (is_price_outlier OR is_size_outlier)

### Usage example

```python
import pandas as pd

td = pd.read_pickle(r'D:\training_data_v1.pkl')

FEATURE_COLS = [
    'EINFLM', 'BYGGAR', 'LOD_FLM', 'FASTEIGNAMAT',
    'canonical_code', 'is_new_build',
    'matsvaedi_bucket', 'region_tier', 'lat', 'lon', 'postnr',
    'unit_category', 'is_main_unit',
    'merking_floor', 'building_max_floor', 'is_top_floor', 'floor_fraction',
    'sale_year', 'sale_month',
]
CAT_COLS = ['canonical_code', 'matsvaedi_bucket', 'region_tier', 'unit_category']

train = td[td['split'] == 'train']
val = td[td['split'] == 'val']
test = td[td['split'] == 'test']

X_train, y_train = train[FEATURE_COLS], train['log_real_kaupverd']
```

---

## `geography_features.pkl` — per-FASTNUM geography

Output frá `build_geography_features()` í `geography.py`. Ein row per fastnum.

**Row count**: 124.835 (allar properties_v2 eignir)

| Dálkur | Type | Lýsing |
|---|---|---|
| `fastnum` | Int64 | Fasteignanúmer (primary key) |
| `matsvaediNUMER` | int64 | HMS verðmatssvæði (191 distinct) |
| `matsvaediNAFN` | str | Nafn matsvæðis |
| `matsvaedi_bucket` | object | Rare-merged bucket (213 distinct) |
| `matsvaedi_sales_2015` | int64 | Sales count í matsvæði (2015+) |
| `postnr` | int64 | Póstnúmer (173 distinct) |
| `postheiti` | str | Póstheiti |
| `region_tier` | str | RVK_core / Capital_sub / Country |
| `lat` | float64 | WGS84 latitude |
| `lon` | float64 | WGS84 longitude |

**matsvaedi_bucket encoding**:
- `M<numer>` — own bucket fyrir matsvæði með ≥50 sölur 2015+ (160 buckets)
- `P<postnr>_other` — rare-merged fyrir smá matsvæði (53 buckets)
- `unknown` — hvorki matsvæði né postnr (0 í núverandi data)

**region_tier definition** (mapped from postnr):
- `RVK_core`: postnr 101-116 (Reykjavík proper)
- `Capital_sub`: postnr 170-276 (Capital region suburbs)
- `Country`: rest

**Coverage**: 100% á öllum dálkum, 0 nulls.

**Usage dæmi**:
```python
import pandas as pd
geo = pd.read_pickle(r'D:\geography_features.pkl')

# Join við kaupskra fyrir Áfanga 2
kaup = pd.read_csv(r'D:\kaupskra.csv', sep=';', encoding='latin-1')
kaup['FASTNUM'] = pd.to_numeric(kaup['FASTNUM'], errors='coerce').astype('int64')
geo['fastnum'] = geo['fastnum'].astype('int64')  # dtype normalization
joined = kaup.merge(geo, left_on='FASTNUM', right_on='fastnum', how='left')
```

---

## `pairs_v1.pkl` — listing-to-sale pairing

Output frá `pair_listings_to_sales()` í `pairing.py`. Ein row per arm's-length sölu.

**Row count**: 174.526

### Identifiers og tímamælingar

| Dálkur | Type | Lýsing |
|---|---|---|
| `faerslunumer` | int64 | Primary key (kaupskra FAERSLUNUMER) |
| `fastnum` | int64 | Fasteignanúmer |
| `sale_date` | datetime64 | Þinglýsingardagur |
| `sale_year` | int | Útdregið úr sale_date |
| `sale_price` | int64 | KAUPVERD í þús. kr |
| `tegund` | str | Kaupskra TEGUND |
| `is_new_build` | bool | FULLBUID=0 OR age_at_sale ≤ 2 |
| `in_scrape_gap` | bool | sale_date ≥ 2025-07-01 (metadata flag) |

### pair_status — 7-flokka taxonomy

| Gildi | Skilgreining | 2015+ count | 2015+ % |
|---|---|---|---|
| `paired_fresh` | session_end ≤ 180d fyrir sölu, list_price_final > 0 | 55.538 | 44,2% |
| `paired_recent` | 180d < gap ≤ 365d, list_price_final > 0 | 3.380 | 2,7% |
| `paired_stale` | gap > 365d | 6.361 | 5,1% |
| `paired_no_price` | paired en list_price_final ógilt | 2.108 | 1,7% |
| `post_sale_only` | FASTNUM hefur listings en engin preceding | 10.843 | 8,6% |
| `off_market_newbuild` | Engin listings, is_new_build=True | 9.439 | 7,5% |
| `off_market_used` | Engin listings, is_new_build=False | 38.066 | 30,3% |

### Session metadata (NaN fyrir off_market og post_sale_only)

| Dálkur | Type | Lýsing |
|---|---|---|
| `session_id` | float64 (nullable) | Unique session identifier |
| `session_start` | datetime64 | Fyrsta listing í session |
| `session_end` | datetime64 | Síðasta listing í session (getur verið post-sale) |
| `matched_listing_date` | datetime64 | Síðasta **pre-sale** listing date |
| `n_in_session` | Int64 | Fjöldi listings í session |
| `time_on_market_days` | float64 | matched_listing_date - session_start |
| `gap_to_sale_days` | float64 | sale_date - matched_listing_date |
| `list_price_initial` | float64 | Verð á session_start |
| `list_price_final` | float64 | Verð á matched_listing_date (pre-sale) |
| `ask_to_sale_ratio` | float64 | sale_price / list_price_final |
| `augl_id_initial` | Int64 | augl_id fyrir earliest listing |
| `augl_id_final` | Int64 | augl_id fyrir matched listing |

### Notkunarmynstur

```python
# Áfangi 7: Ask-to-sale gap model training (nota öll paired_fresh, in_scrape_gap OK)
train = pairs[pairs['pair_status'] == 'paired_fresh']

# Time-on-market dashboard
tom = pairs[pairs['pair_status'].isin(['paired_fresh', 'paired_recent'])]

# Market coverage statistics (denominator-dependent — filter in_scrape_gap)
coverage = pairs[~pairs['in_scrape_gap']].groupby('tegund')['pair_status'].value_counts()
```

### Defaults

- `X_SESSION_GAP_DAYS = 90`
- `Y_FRESH_DAYS = 180`
- `Y_VALID_DAYS = 365`
- `SCRAPE_GAP_START = 2025-07-01`

Override-able via kwargs í `pair_listings_to_sales()`.

### Validation baseline

Ask-to-sale median á paired_fresh (sane [0.5, 2.0]) = **0,9816**. Regression check á re-run.

---

## ⚠ Scrape gap — 2025-07 til recent

Listings volume `effective_date`:
- 2024 baseline: 7.400-11.800/mán
- 2025-H1: 6.600-10.300/mán
- 2025-07: 2.590 (cliff)
- 2025-08 til 2026-02: 272-920/mán
- 2026-03/04: 1.775-1.857/mán

Pairing effect: `in_scrape_gap=True` fyrir sölur ≥ 2025-07-01. Paired records í gap eru per-pair nothæf en denominator-dependent metrics eru unreliable.

Fix: Nýr scraper í Áfanga 0. Gap-data verður ekki fyllt retroactively.

---

## `listings_v2.pkl` — hreinar auglýsingar

471.591 rows eftir dedupe á `augl_id`. Date coverage 98,57% (464.866 rows) eftir ISO8601 parsing fix og year-range filter [2000, 2030].

### Identifiers

| Dálkur | Type | Lýsing |
|---|---|---|
| `fastnum` | Int64 | Fasteignanúmer (HMS) |
| `augl_id` | Int64 | Listing ID frá fastinn.is (globally unique) |

### Temporal

| Dálkur | Type | Lýsing |
|---|---|---|
| `thinglystdags_raw` | str | Raw ISO date string frá scrape |
| `effective_date` | datetime64 | Parsed date; NaT fyrir sentinel/invalid |
| `date_valid` | bool | True ef effective_date er valid (98,57% af rows) |
| `scraped_at` | datetime64 | Hvenær scraper nálgaðist þessa eign |

### Price

| Dálkur | Type | Lýsing |
|---|---|---|
| `listing_price` | float64 | Ásett verð í þús. kr |
| `fasteignamat` | float64 | Fasteignamat á listing-tíma |
| `brunabotamat` | float64 | Brunabótamat |
| `ahvilandi` | float64 | Áhvílandi lán |
| `kaupverD_VISITALA_NEYSLUVERDS` | float64 | Price × CPI encoded as integer |
| `fasteignamaT_GILDANDI` | float64 | Gildandi fasteignamat |

### Physical

| Dálkur | Type | Lýsing |
|---|---|---|
| `einflm` | float64 | Einingastærð í m² |
| `byggar` | float64 | Byggingarár |
| `fjherb` | float64 | Fjöldi herbergja alls |
| `fjsvfnherb` | float64 | Fjöldi svefnherbergja |
| `fjbadherb` | float64 | Fjöldi baðherbergja |
| `tegund_augl` | str | Auglýsingaflokkur (`fjolb`, `einb`, `raðpar`, ...) |
| `inngangur` | str | T.d. "Sérinngangur" |

### Binary features (bool eða None)

| Dálkur | Lýsing |
|---|---|
| `lyfta` | Lyfta í byggingu |
| `bilskur` | Bílskúr |
| `staedi` | Bílastæði |
| `rafbill` | Hleðslustöð |
| `gardur` | Garður |
| `svalir` | Svalir |
| `hjolastoll` | Hjólastólsvænt |
| `eldrib` | Senior-friendly marketing |
| `pets` | Gæludýr leyfð |
| `ferskt` | "Ferskt" flagg (óljós merking — líklega "nýlega sett á sölu") |

### Location

| Dálkur | Type | Lýsing |
|---|---|---|
| `postnr` | float64 | Póstnúmer |
| `postheiti` | str | Staður |
| `matsvaediNUMER` | float64 | HMS verðmatssvæði |
| `matsvaediNAFN` | str | Nafn verðmatssvæðis |
| `long` | float64 | Lengdargráða (oft null — HMS coords í properties_v2 áreiðanlegri) |
| `lat` | float64 | Breiddargráða |

### Meta

| Dálkur | Type | Lýsing |
|---|---|---|
| `n_myndir` | float64 | Fjöldi mynda í listing (count only, ekki URL-ar) |
| `source_db` | str | Nafn pre-merge DB sem þessi row kom úr |

**Athugið**: listings_v2 hefur ekki `landnum` eða `merking` — þau eru í properties_v2. Landnum alt-pairing (1.8b backlog) krefst re-parse.

---

## `listings_text_v2.pkl` — lýsingar (lysing HTML)

Aðskilin pickle af size-ástæðum (~1,5 GB). Schema:

| Dálkur | Type | Lýsing |
|---|---|---|
| `augl_id` | Int64 | Join key til listings_v2 |
| `lysing` | str | HTML lýsing, median ~2,6K chars |
| `source_db` | str | Pre-merge DB source |
| `scraped_at` | datetime64 | Scrape-tími |

Loaded on demand fyrir Phase 4+ LLM extraction.

---

## `sales_v2.pkl` — per-property sales frá kaups_json

173K rows eftir dedupe á `faerslunumer`. Kaups_json er sub-set af canonical kaupskra.csv; join á `faerslunumer` fyrir full fields (ONOTHAEFUR, TEGUND, etc).

### Identifiers

| Dálkur | Type | Lýsing |
|---|---|---|
| `fastnum` | Int64 | Fasteignanúmer |
| `faerslunumer` | Int64 | Primary key; join til kaupskra.csv |

### Temporal

| Dálkur | Type | Lýsing |
|---|---|---|
| `thinglystdags_raw` | str | Raw ISO datetime |
| `sale_date` | datetime64 | Parsed |
| `scraped_at` | datetime64 | — |

### Sale data

| Dálkur | Type | Lýsing |
|---|---|---|
| `sale_price` | float64 | Kaupverð í þús. kr |
| `einflm` | float64 | Stærð á kaupdegi |
| `byggar` | float64 | Byggingarár |
| `fjherb` | float64 | (Athugið: getur verið frozen snapshot eins og í CSV) |
| `postnr` | float64 | |
| `postheiti` | str | |
| `kaupverD_VISITALA_NEYSLUVERDS` | float64 | |

### Meta

| Dálkur | Type | Lýsing |
|---|---|---|
| `source_db` | str | |

**Notkun**: Fyrir arm's-length filter, join við `kaupskra.csv` á `faerslunumer` → `FAERSLUNUMER` til að fá `ONOTHAEFUR_SAMNINGUR` og `TEGUND` fields.

---

## `properties_v2.pkl` — HMS fasteignaskrá per eign

125K rows eftir dedupe á `fastnum`. Sannleiksuppsprettan fyrir structured property attributes.

### Identifiers

| Dálkur | Type | Lýsing |
|---|---|---|
| `fastnum` | Int64 | Fasteignanúmer |
| `landnum` | int64 | Landnúmer (lóðareining), 100% coverage |
| `heinum` | float64 | Heimilisnúmer |

### Address + location

| Dálkur | Type | Lýsing |
|---|---|---|
| `heimilisfang` | str | Gata + númer |
| `merking` | str | Unit identifier (100% coverage) — útdreginn í floor features |
| `postnr`, `postheiti` | int64, str | 100% coverage |
| `matsvaediNUMER`, `matsvaediNAFN` | int64, str | 100% coverage |
| `hnitWGS84_N`, `hnitWGS84_E` | float64 | Coordinates, 100% coverage |

### Property attributes

| Dálkur | Type | Lýsing |
|---|---|---|
| `tegund` | str | HMS canonical tegund (1 af 514) |
| `flatarmal` | float64 | Núverandi stærð (m²) |
| `byggar` | float64 | Byggingarár |
| `fasteignamat` | float64 | |
| `fasteignamaT_NAESTA` | float64 | Næsta fasteignamat |
| `brunabotamat` | float64 | |

Coverage er **100%** á öllum geo-dálkum (staðfest audit 1.6).

---

## Canonical CSV: `kaupskra.csv`

Authoritative source fyrir transaction-data. **Latin-1 encoding, semicolon-separated**. 226.481 rows (2006-05-08 → 2026).

Used by: `pairing.py`, `run_pair_and_validate.py`, `build_training_data.py`, Áfangi 2 baseline módel direct.

### Full column list (25 dálkar)

`FAERSLUNUMER`, `EMNR`, `SKJALANUMER`, `FASTNUM`, `HEIMILISFANG`, `POSTNR`, `HEINUM`, `SVFN`, `SVEITARFELAG`, `UTGDAG`, `THINGLYSTDAGS`, `KAUPVERD`, `FASTEIGNAMAT`, `FASTEIGNAMAT_GILDANDI`, `FYRIRHUGAD_FASTEIGNAMAT`, `BRUNABOTAMAT_GILDANDI`, `BYGGAR`, `FEPILOG`, `EINFLM`, `LOD_FLM`, `LOD_FLMEIN`, `FJHERB`, `TEGUND`, `FULLBUID`, `ONOTHAEFUR_SAMNINGUR`.

### Key distributions

**TEGUND** (coarser en HMS tegund í properties_v2):
- Fjölbýli 114.971 (65,9% af arm's-length)
- Einbýli 24.174 (13,9%)
- Sérbýli 18.847 (10,8%)
- Atvinnuhúsnæði 10.724 (6,1%)
- Sumarhús 4.705 (2,7%)
- Annað 800, Bílskúr/skúr 305

**FULLBUID**: 212.138 (94%) fullbyggt, 14.050 (6%) ófullgert.

**ONOTHAEFUR_SAMNINGUR**: 174.421 (77%) arm's-length, 51.767 (23%) ónothæfir.

### `SKJALANUMER` format

**String**, ekki numeric. Format: `"X-NNNNNN/YYYY"` þar sem X er flokkur (A, R, etc), NNNNNN er raðnúmer, YYYY er ár.

Dæmi: `"R-005069/2006"`, `"A-000003/2022"`.

**Usage**: `kaup['SKJALANUMER'].astype(str)` — **ekki** `pd.to_numeric`.

### `FEPILOG` hierarchy (Áfangi 1.8 decoded, revised 2.0)

6-stafa kóði `AABBCC`. 1.551 distinct values í kaupskrá.

- **AA** = aðal-flokkur. **Mixed-purpose á öllum gildum**, EKKI clean residential/garage split.
  - 01 dominates (74% af sölum) og er mostly residential-main
  - 02 (11%) og 03+ eru blandaðar: residential-main, commercial, bílskúrar og lóðir saman. Empíríkt staðfest í audit 2.0 — unit_category 0201 í in-model records er APT_STANDARD/APT_FLOOR/ROW_HOUSE/SEMI_DETACHED með median pr-m² = 588 k/m² (clean residential range, ekki garage).
  - Canonical exclusion í módeli stýrist af `classify_property()` úr HMS tegund, EKKI af FEPILOG AA.
- **BB** = undir-flokkur. Dreifing heldur áfram innan hvers AA — ekki predictable hrein flokkun.
- **CC** = raðnúmer
  - 01 = aðal-eining (58,1%)
  - 02+ = aukaeiningar

Mest algeng top-20 codes: `010101` (31,1%), `010201` (7,5%), `010102` (3,9%), `010001` (3,1%), `010202` (3,0%), `010301` (2,9%), `020101` (2,5%), `010103` (2,0%), `010302` (1,8%), `010203` (1,6%), `030101` (1,4%), `010104` (1,3%), `010303` (1,1%), `010204` (1,0%), `020201` (1,0%), `020202` (0,9%), `010401` (0,8%), `040101` (0,8%), `020102` (0,8%), `010105` (0,8%).

Features fyrir Áfanga 2:
- `unit_category = AA + BB` (categorical, top-5 concentrates 67% af in-model sales)
- `is_main_unit = (CC == "01")`

### Frozen snapshot dálkar — ekki nota sem per-sale values

Staðfest 2026-04-18 að fjórir dálkar eru HMS núverandi gildi per FASTNUM, ekki historical:

| Dálkur | Notið í staðinn |
|---|---|
| `FASTEIGNAMAT_GILDANDI` | `FASTEIGNAMAT` |
| `FYRIRHUGAD_FASTEIGNAMAT` | `FASTEIGNAMAT` |
| `BRUNABOTAMAT_GILDANDI` | Engin historical |
| `FJHERB` | `listings_v2.pkl.fjherb` per listing |

### Staðfest historical dálkar (varies milli sala)

| Dálkur | varies% |
|---|---|
| `KAUPVERD` | 99,40% |
| `FASTEIGNAMAT` | 98,65% |
| `EINFLM` | 6,77% |
| `FULLBUID` | 4,60% |
| `LOD_FLM` | 4,31% |

### Multi-unit pattern (Áfangi 1.8)

8,3% af arm's-length records (14.562) eru í multi-unit SKJALANUMER (2-4 FASTNUM per samningur):
- 95,80% SKJALANUMER = 1 FASTNUM
- 3,90% = 2 FASTNUM
- 0,29% = 3 FASTNUM
- 0,02% = 4 FASTNUM

KAUPVERD er þegar pro-rata skipt milli rows í multi-unit samningum (998 af 1000 sample hafa mismunandi verð). **Policy**: Áfangi 2 baseline notar eingöngu single-FASTNUM SKJALANUMER (95,8%).

Validerað í audit 2.0: multi-unit samningar eru kerfisbundið lower pr-m² en single (Einbýli 0,91×, Fjölbýli 0,89×, Sérbýli 0,99×). Filter fjarlægir bundled-pricing bias.

---

## Stadfangaskra.csv

**UTF-8 comma-separated**. 138.643 rows. Húsnúmera-level data (meira granulítt en properties_v2).

Key columns: `FID`, `HNITNUM`, `SVFNR`, `LANDNR`, `HEINUM`, `POSTNR`, `HEITI_NF`, `HUSNR`, `BOKST`, `DAGS_INN`, `N_HNIT_WGS84`, `E_HNIT_WGS84`, `LM_HEIMILISFANG`.

Notað fyrir cross-reference (landnum → hnit mapping) og mögulega fyrir landnum-based alt-pairing í Áfanga 1.8b (þegar listings_v2 fær landnum).

---

## Derived outlier-flögg á kaupskrá færslum (rules.py)

Áfangi 1.4.2 skilgreinir tvö derived flögg fyrir hverja kaupskrá-færslu. Flöggin eru reiknuð af `rules.py`.

### is_price_outlier (bool)

Flaggar ef nokkur eftirfarandi skilyrði uppfyllast:

| Regla | Skilyrði |
|---|---|
| 1 | `fm_ratio < 0.10` |
| 2 | `fm_ratio < 0.30` AND `robust_z < −3` |
| 3 | `robust_z < −5` AND `fm_ratio < 0.50` |
| 4 | `robust_z > +10` AND `fm_ratio > +20` |

Þar sem:
- `fm_ratio = KAUPVERD / FASTEIGNAMAT` (notið historical `FASTEIGNAMAT`, ekki `_GILDANDI`)
- `robust_z = (log10(KAUPVERD/EINFLM) − seg_median) / (seg_iqr / 1.349)`
- `seg_median`, `seg_iqr` úr `compute_segment_stats()` á (TEGUND × region × 3-ára bucket) með min_n=50

Impact á residential (N=162.692): 172 flaggaðar (0,106%).

### is_size_outlier (bool)

- `EINFLM < 20 m²` eða `EINFLM > 1000 m²`

Impact: 153 flaggaðar (0,094%).

### Union (sem ætti að droppa úr training)

324 records (0,199%).

### Notkun

```python
from rules import apply_is_price_outlier, apply_is_size_outlier, compute_segment_stats

seg_stats = compute_segment_stats(kaupskra_df)
seg_stats.to_csv('segment_stats.csv', index=False)

kaupskra_df['is_price_outlier'] = apply_is_price_outlier(kaupskra_df, seg_stats)
kaupskra_df['is_size_outlier'] = apply_is_size_outlier(kaupskra_df['EINFLM'])

clean = kaupskra_df[~kaupskra_df['is_price_outlier'] & ~kaupskra_df['is_size_outlier']]
```

---

## ⚠ Deprecated storage

- `D:\fasteignir_merged.db` (2,8 GB) — 82% NaT á thinglystdags. Sögulegt reference.
- `D:\audit_1_5\*.pkl` — derivatives af corruption.
- `D:\audit_1_5_*.py` skript — logic lært, ekki keyrð aftur.

---

## Devalue-formatið (parser reference)

Scraped data er í devalue formati (SvelteKit). Parser í `D:\devalue.py`. Key function: `parse_outer(raw_string)`.

Byggingin: flat JSON array þar sem:
- Element 0 er root-ið
- Heiltölur innan í strúktúrum eru references í aðrar positions í array-inum
- Negative integers eru sentinel gildi (-1 = undefined, -2 = null, -3 = NaN, -4 = +Inf, -5 = -Inf, -6 = -0)
- Aðrar primitives (string, float, bool, null) eru literal gildi

Cycle detection og memoization eru nauðsynleg vegna þess að mörg fields deila position.

---

## Raw JSON field reference (úr pre-merge DB)

Þótt v2 pickles séu canonical, er gott að muna hvað er í raw JSON fyrir framtíðarvinnu eða ef endurparse þarf.

### `data_json` — HMS fasteignaskrá (einn record per FASTNUM)

Keys: `fastnum`, `landnum`, `heinum`, `heimilisfang`, `merking`, `tegund`, `flatarmal`, `fasteignamat`, `fasteignaMAT_NAESTA`, `brunabotamat`, `postnr`, `hnitWGS84_N`, `hnitWGS84_E`, `matsvaediNUMER`, `matsvaediNAFN`, `postheiti`.

### `kaups_json` — kaupskrárhistoría (listi)

Per-sale: `faerslunumer`, `postnr`, `thinglystdags`, `kaupverd`, `einflm`, `byggar`, `fjherb`, `kaupverD_VISITALA_NEYSLUVERDS`, `postheiti`, `id`.

### `augl_json` — auglýsingahistoría (listi)

Per-listing: allir fields í listings_v2.pkl plús `lysing` (HTML, extracted í listings_text_v2.pkl) og `myndir` (listi af URL-objects, ekki stored í listings_v2).

**Mögulega til en EKKI extracted**: `landnum` field gæti verið í raw augl_json — re-parse check fyrir Áfanga 1.8b.

---

## Image URLs

CloudFront CDN: `https://d1u57vh96em4i1.cloudfront.net/<fastnum>/<hash>.jpg`

Downloaded einungis úr síðustu auglýsingu per eign (pre-existing scraper optimization). Myndir töflur eru í hverri pre-merge DB separately (ekki extractaðar í v2 pickles).

---

## HMS SvelteKit endpoints (reverse-engineered)

Scraper POST-ar per fasteignanúmer:

- `get_fasteign_data` — HMS fasteignaskrá → data_json
- `get_fasteign_kaups` — kaupskrárhistoría → kaups_json
- `get_fasteign_augl` — auglýsingahistoría → augl_json

Response wrapped í `{type: "success", status: 200, data: "<devalue-serialized>"}`.

---

## Data coverage summary

| Mælikvarði | Gildi |
|---|---|
| Unique FASTNUM (properties_v2) | 124.835 |
| Unique FASTNUM í listings_v2 | 58.437 (47% af properties) |
| Unique augl_id | 471.591 |
| Unique faerslunumer | 173.409 |
| Listings með valid date | 464.866 (98,57%) |
| Kaupskrár records | 226.481 |
| Arm's-length records | 174.526 |
| Paired_fresh í pairs_v1 (2015+) | 55.538 |
| Training preview (Áfangi 2.0) | 148.608 |
| Geography coverage | 100% |

---

## HMS tegund vocabulary

Allir 514 distinct flokkaðir í canonical codes í `classify_property.py`. Skilar tuple `(canonical_code, flags_dict)`. Sjá TAXONOMY.md.

Mest algengt MAIN residential: APT_FLOOR (50.795), APT_STANDARD (33.535), SFH_DETACHED (9.027), ROW_HOUSE (5.576), SEMI_DETACHED (2.918), APT_BASEMENT (2.561), APT_ATTIC (1.023).

---

## Listings tegund vocabulary (fastinn.is — `tegund_augl` dálkur)

Messy encoding: `fjolb`, `einb`, `raðpar`/`radpar`, `atv`, `sumarhus`, `hæðir`/`haedir`, `fjölb`.

**Regla**: Nota HMS tegund (properties_v2) fyrir flokkun, listings tegund er bara fallback.
