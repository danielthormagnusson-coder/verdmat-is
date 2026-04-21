# DATA AUDIT REPORT — Áfangi 1 heildarniðurstöður

**Framleitt**: 18. apríl 2026
**Framleiðslu-scripta**: `D:\audit_1_7_full_report.py` (re-runnable)
**Gildir fyrir**: v2 pickles + kaupskra snapshot frá 2026-04-18

Þetta skjal er samantekt á öllum niðurstöðum úr Áfanga 1 (1.1–1.6). Þjónar sem reference fyrir downstream vinnu og onboarding fyrir nýja samstarfsaðila.

---

## Headline

Íslenski fasteignamarkaðurinn er með óvenju hreint data layer. HMS gögnin eru nánast 100% complete á structured fields. Aðalveikleiki er **scrape gap frá 2025-07-01** þar sem listings volume hrundi úr ~9.000/mán í ~600/mán og hefur ekki rétt úr sér. Það er ekki fixable retroactive en verður leyst með nýjum scraper í Áfanga 0.

Paired_fresh coverage er 44% af 2015+ markaðinum (55.538 hreinir pairs). Það er lægra en upphaflega spáð 70-80% en lítill hluti af þeim halla skýrist af nýbyggingum. Danni's pre-fastnum tilgáta (listings undir landnum í stað fullkláraðs FASTNUM) er aðalhypotheses fyrir restina, testable í Áfanga 1.8.

**Heildarmat**: Data layer er production-ready fyrir baseline hedonic módel (Áfangi 2). Pairing coverage er nógu þétt fyrir ask-to-sale gap módel í Áfanga 7.

---

## 1. Canonical data layer

Fimm pickles + einn CSV mynda core layer-ið:

| Skrá | Stærð | Rows | Lykilatriði |
|---|---|---|---|
| `listings_v2.pkl` | 105 MB | 471.591 | 98.57% valid dates, 58.437 unique FASTNUM |
| `listings_text_v2.pkl` | 1.6 GB | 456K | lysing HTML á demand |
| `sales_v2.pkl` | 21 MB | 173.409 | kaups_json sub-set |
| `properties_v2.pkl` | 23 MB | 124.835 | 100% coverage á geo |
| `pairs_v1.pkl` | 28 MB | 174.526 | 1 row per arm's-length sala |
| `geography_features.pkl` | 12 MB | 124.835 | 100% coverage á matsvæði + bucket |
| `kaupskra.csv` | 46 MB | 226.481 | Authoritative transaction data |

Deprecated: `fasteignir_merged.db` (3 GB) — ekki lesin úr lengur vegna 82% NaT á thinglystdags.

---

## 2. Taxonomy coverage (Áfangi 1.1)

514 distinct HMS tegundir flokkaðar í canonical codes via `classify_property.py`.

| Fjölskylda | Records | % |
|---|---|---|
| MAIN residential (7 codes) | 105.435 | 84.5% |
| SECONDARY residential (5 codes) | 368 | 0.3% |
| SUMMERHOUSE | 4.513 | 3.6% |
| **Í módeli alls** | **110.316** | **88.4%** |
| EXCLUDE | 14.519 | 11.6% |

**Per canonical code** (MAIN + SECONDARY + SUMMER):

| Code | N | Lýsing |
|---|---|---|
| APT_FLOOR | 50.795 | Íbúð á hæð |
| APT_STANDARD | 33.535 | Venjuleg íbúð í fjölbýli |
| SFH_DETACHED | 9.027 | Einbýlishús |
| ROW_HOUSE | 5.576 | Raðhús |
| SUMMERHOUSE | 4.513 | Sumarbústaðir |
| SEMI_DETACHED | 2.918 | Parhús |
| APT_BASEMENT | 2.561 | Kjallaraíbúð |
| APT_ATTIC | 1.023 | Rishæð |
| APT_UNAPPROVED | 155 | Ósamþykkt íbúð |
| APT_SENIOR | 89 | Öryggisíbúð |
| APT_HOTEL | 65 | Hótelíbúð |
| APT_ROOM | 54 | Íbúðarherbergi |
| APT_MIXED | 5 | Íbúð/vinnustofa |

Athugið: Gestahús (65 records) og einfaldur "Herbergi" (2) útilokað sem ambiguous. Sjá TAXONOMY.md fyrir full flokkunartöflu.

---

## 3. Kaupskrá + arm's-length (Áfangi 1.1/1.2)

| Metric | N | % |
|---|---|---|
| Total records | 226.481 | 100% |
| ONOTHAEFUR=1 (non-arm's-length) | 51.955 | 22.9% |
| Arm's-length | 174.526 | 77.1% |

Allir 174.526 arm's-length records hafa valid FASTNUM + THINGLYSTDAGS (100% coverage).

**Per TEGUND** (kaupskrá category, coarser en HMS tegund):

| TEGUND | N | % |
|---|---|---|
| Fjölbýli | 114.971 | 65.9% |
| Einbýli | 24.174 | 13.9% |
| Sérbýli | 18.847 | 10.8% |
| Atvinnuhúsnæði | 10.724 | 6.1% |
| Sumarhús | 4.705 | 2.7% |
| Annað | 800 | 0.5% |
| Bílskúr/skúr | 305 | 0.2% |

---

## 4. Nýbyggingarsegment (Áfangi 1.2)

Regla: `FULLBUID=0 OR age_at_sale ≤ 2`.

| Flokkur | N | % |
|---|---|---|
| FULLBUID=0 eingöngu | 3.371 | 1.9% |
| age ≤ 2 eingöngu | 19.938 | 11.4% |
| Bæði skilyrði | 3.293 | 1.9% |
| **Union (is_new_build)** | **26.602** | **15.2%** |

**Per TEGUND**:

| TEGUND | New-build rate |
|---|---|
| Atvinnuhúsnæði | 23.6% |
| Sérbýli | 22.5% |
| Fjölbýli | 15.3% |
| Sumarhús | 9.9% |
| Einbýli | **5.1%** |

Mikil ósamhverfa milli Einbýli (5.1%) og Sérbýli (22.5%) er áhugaverð — reflexion á því að Sérbýli eru yfirleitt developed í project-scale (raðhús, parhús) á meðan Einbýli eru oftar byggð sem sérbyggingar af eiganda.

Pre-completion discount (via Áfangi 1.2 empirical check): Fjölbýli 12%, Einbýli 23%.

---

## 5. Eignabreytingarregla (Áfangi 1.3)

Repeat-sale par útilokað ef (a) FULLBUID 1→0 transition, eða (b) `|EINFLM pct_change| > 5%`.

| Metric | N | % |
|---|---|---|
| Consecutive arm's-length pör | 68.696 | 100% |
| EINFLM change > 5% | 2.070 | 3.0% |
| FULLBUID 1→0 transition | 88 | 0.1% |
| **Union (dropped)** | **2.133** | **3.1%** |
| Held | 66.563 | 96.9% |

Tölur matchast við Áfanga 1.3 finding — engin drift.

---

## 6. Frozen-snapshot staðfesting (Áfangi 1.4.1)

Fjórir dálkar í kaupskrá CSV eru HMS núverandi gildi per FASTNUM, ekki historical per sölu:

| Dálkur | varies% (multi-sale) | Staða |
|---|---|---|
| FASTEIGNAMAT_GILDANDI | 0.00% | ⚠ Frozen — ekki nota |
| FYRIRHUGAD_FASTEIGNAMAT | 0.00% | ⚠ Frozen — ekki nota |
| BRUNABOTAMAT_GILDANDI | 0.00% | ⚠ Frozen — ekki nota |
| FJHERB | 0.00% | ⚠ Frozen — ekki nota |

**Réttir historical dálkar** (varies á raunverulegum gildum milli sala):

| Dálkur | varies% |
|---|---|
| KAUPVERD | 99.40% |
| FASTEIGNAMAT | 98.65% |
| EINFLM | 6.77% |
| FULLBUID | 4.60% |
| LOD_FLM | 4.31% |

---

## 7. Outlier filter (Áfangi 1.4.2)

Á residential arm's-length records með valid price+size+mat (N=162.692):

| Regla | N | % |
|---|---|---|
| is_price_outlier | 172 | 0.106% |
| is_size_outlier | 153 | 0.094% |
| **Union (drop)** | **324** | **0.199%** |

HMS gögnin eru óvenju hrein — engar factor-1000 innsláttarvillur sjást. Combined fm_ratio + segment robust-z regla er ósymmetrisk (drop-ar bara low-side, allt high er legit luxury).

---

## 8. Data layer cleanup (Áfangi 1.4.3)

| Metric | Value |
|---|---|
| Unique augl_id í listings_v2 | 471.591 |
| Unique FASTNUM í listings_v2 | 58.437 (47% af 124.835 properties) |
| date_valid=True | 98.57% (464.866 rows) |
| effective_date range | 2010-04-15 → 2026-04-15 |

Canonical data pipeline:

```
pre-merge DBs (5x SQLite) 
   → parse_all_dbs.py + patch_v2_dates.py 
      → listings_v2.pkl, sales_v2.pkl, properties_v2.pkl, listings_text_v2.pkl
         → pairing.py 
            → pairs_v1.pkl
         → geography.py
            → geography_features.pkl
```

---

## 9. Listing-to-sale pairing (Áfangi 1.5)

Thresholds: X=90d session boundary, Y_fresh=180d, Y_valid=365d.

**All years** (N=174.526):

| Status | N | % |
|---|---|---|
| off_market_used | 62.837 | 36.0% |
| paired_fresh | 55.544 | 31.8% |
| post_sale_only | 31.297 | 17.9% |
| off_market_newbuild | 12.985 | 7.4% |
| paired_stale | 6.366 | 3.6% |
| paired_recent | 3.385 | 1.9% |
| paired_no_price | 2.112 | 1.2% |

**2015+ subset** (N=125.735) — relevant training window:

| Status | N | % |
|---|---|---|
| paired_fresh | 55.538 | 44.2% |
| off_market_used | 38.066 | 30.3% |
| post_sale_only | 10.843 | 8.6% |
| off_market_newbuild | 9.439 | 7.5% |
| paired_stale | 6.361 | 5.1% |
| paired_recent | 3.380 | 2.7% |
| paired_no_price | 2.108 | 1.7% |

**Ask-to-sale ratio** (paired_fresh, sane [0.5, 2.0]):

- N: 55.460
- Median: **0.9816**
- IQR: [0.960, 1.000]

**in_scrape_gap split**:

- Pre-gap paired_fresh: 53.386 (reliable for training)
- In-gap paired_fresh: 2.158 (valid per-pair, unreliable nefnari)

---

## 10. Geography features (Áfangi 1.6)

100% coverage á matsvæði, postnúmer, og hnit í properties_v2. Allt innan Íslands bbox.

**matsvaedi_bucket** (rare-merged strategy, min 50 sölur 2015+):

| Bucket type | N FASTNUM | % |
|---|---|---|
| M&lt;numer&gt; (own matsvæði, 160 distinct) | 123.587 | 99.0% |
| P&lt;postnr&gt;_other (rare merged, 53 distinct) | 1.248 | 1.0% |
| unknown | 0 | 0.0% |

Total distinct bucket values: 213.

**region_tier** (based on postnr):

| Tier | Range | N | % |
|---|---|---|---|
| RVK_core | 101-116 | 41.701 | 33.4% |
| Capital_sub | 170-276 | 44.788 | 35.9% |
| Country | rest | 38.346 | 30.7% |

Largest 10 matsvæði: Miðbær (20), Selfoss (8010), Kópavogur Austurbær (320), Hafnarfjörður (600), Njarðvík (2040), Akranes (3000), Árnessvæði (8055), Laugarneshverfi/Vogar (100), Keflavík (2050), Grafarvogur (130).

---

## 11. Known issues & backlog

### Scrape gap (Áfangi 0 action)

Listings `effective_date` volume frá 2025-07-01:

| Tímabil | Listings/mán |
|---|---|
| 2024 baseline | ~9.100 |
| 2025-H1 | ~8.700 |
| **2025-07** | **2.590** (cliff byrjar) |
| 2025-08 til 2026-02 | 272-920 |
| 2026-03/04 | 1.775-1.857 |

Annualized rate vs 2024 baseline = 0.10x. Scraperinn sem var í keyrslu var erfður og ekki í Danni control. Leyst með nýjum scraper í Áfanga 0.

**Áhrif á downstream**: `in_scrape_gap=True` flag á sölur ≥ 2025-07-01. Paired records í gap-tímabili eru nothæf per-pair en denominator-dependent metrics (coverage rate, off_market %) eru unreliable í gap.

### Fjölbýli off_market coverage (Áfangi 1.8 backlog)

26.791 Fjölbýli sölur 2015+ eru `off_market_used`. Nýbyggingar-tilgáta er rejected (18.5% í off_market vs 15.3% baseline).

**Danni's pre-fastnum hypothesis**: nýbyggingar eru listed undir landnum (bráðabirgða-auðkenni) í stað endanlegs FASTNUM sem HMS úthlutar eftir completion. Kaupsamningur í kaupskra hefur final FASTNUM, en listing í listings_v2 er tagged með öðrum identifier. Testable í Áfanga 1.8 með landnum-based alternative identifier pairing (properties_v2 → fastnum→landnum mapping + listings_v2 landnum).

### Multi-unit aggregation (Áfangi 1.8)

FEPILOG decoding ekki fullbúið. Sölur með margar einingar undir sama SKJALANUMER þurfa aggregation logic (aðal-eining í main módeli, aðrar í secondary).

### Spatial smoothing (Áfangi 2b ef þörf)

lat/lon eru bare numeric í geography_features. LightGBM lærir nonlinear spatial patterns án pre-processing. KNN-residual smoothing bætist á aðeins ef residual audit í Áfanga 2a sýnir clear spatial clustering sem módel nær ekki að fanga úr matsvæði + lat/lon.

---

## 12. Data quality scorecard

| Categoria | Score | Note |
|---|---|---|
| Coverage — properties_v2 geo | 100% | Allar 124.835 fullkláraðar |
| Coverage — properties_v2 tegund | 100% | Allar flokkaðar via classify_property |
| Coverage — listings_v2 date_valid | 98.6% | 464.866 af 471.591 |
| Coverage — kaupskrá THINGLYSTDAGS | 100% | 226.481 allar valid |
| Arm's-length rate | 77% | 174.526 af 226.481 |
| Pairing — 2015+ paired_fresh | 44% | 55.538 af 125.735 |
| Pairing — Einbýli paired_fresh | 57% | Best coverage, minnstur off-market |
| Pairing — Fjölbýli paired_fresh | 43% | Pre-fastnum hypothesis candidate |
| Ask-to-sale median (paired_fresh) | 0.982 | Stöðugt 10 ára historical |
| Outlier rate (residential) | 0.20% | Óvenju hrein HMS data |
| Scrape freshness (pre-2025-07) | 100% | Healthy ~9K listings/mán |
| Scrape freshness (post-2025-07) | 10% | Gap — ekki backfill-able |

---

## 13. Reproducibility

Til að endurskapa þessa skýrslu: `python D:\audit_1_7_full_report.py`. 

Kóðinn les canonical skrár og prentar consistent tölur. Ef tölur diverge frá þessum skýrslu er annaðhvort canonical data layer breytt eða skriptu-breyting. Nota þetta sem regression check við gagna-uppfærslur.

**Módúlar sem skýrslu-scripta byggja á**:

- `classify_property.py` — HMS tegund → canonical code
- `rules.py` — new-build, property-change, outlier reglur
- `pairing.py` — listing-to-sale pairing (output: pairs_v1.pkl)
- `geography.py` — per-FASTNUM geography features (output: geography_features.pkl)

---

## 14. Áfangi 1 close-out

Áfangi 1 er considered **complete** að undanskildum 1.8 (multi-unit aggregation + landnum-based alt-pairing). 1.8 er ekki blokker fyrir Áfanga 2 baseline hedonic módel — það notar kaupskra + properties_v2 + geography_features beint án pairing input.

Næstu skref:

1. Áfangi 1.8: multi-unit aggregation + landnum-based alternative pairing (test Danni's pre-fastnum hypothesis).
2. Áfangi 2: baseline hedonic módel (LightGBM quantile regression).
