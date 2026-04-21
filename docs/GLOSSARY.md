# GLOSSARY — Íslensk og tæknileg hugtök

Skrá yfir lykilhugtök sem koma fyrir í verkefninu — bæði íslensk fasteignahugtök og tæknileg ML/infra-hugtök sem gott er að hafa á einum stað.

---

## Íslensk fasteignahugtök

**Fasteignanúmer (fastnum)** — HMS-auðkenni eignar. Einkvæmt númer sem HMS gefur hverri fasteign. Join-key í öllum kerfum.

**Landnúmer (landnum)** — auðkenni lóðar. Margar eignir geta deilt sama landnúmeri (t.d. allar íbúðir í sama fjölbýli).

**Heimilisnúmer (heinum)** — tengist póstáritun.

**Merking** — unit-auðkenni innan fjölbýlis (dæmi: "010101" = fyrsta íbúð á fyrstu hæð í aðalinngangi).

**Fasteignamat** — opinbert verðmat HMS á eign, uppfært árlega. Notað fyrir fasteignagjöld. Oftast undir markaðsvirði en fylgir þó þróun.

**Fasteignamat_gildandi** — núverandi gildandi mat (fyrir yfirstandandi ár).

**Fasteignamat_næsta** — mat næsta árs, ef það hefur verið útgefið.

**Brunabótamat** — vátryggingafjárhæð fyrir húseign (byggir á byggingarkostnaði, ekki markaðsvirði).

**Matsvæði (matsvaediNUMER, matsvaediNAFN)** — HMS hverfaskipting sem notuð er við fasteignamat. Finari en póstnúmer, með nafni eins og "Mosfellsbær: Höfðar, Hlíðar". Notað sem geography feature í módelinu.

**Kaupskrá** — opinber skrá HMS yfir þinglýsta kaupsamninga. Uppfærist að jafnaði vikulega (opinberlega mánaðarlega). Einn af lykil-gagnagjöfum verkefnisins.

**Fasteignaskrá** — opinber skrá HMS yfir allar fasteignir landsins með eignatengdum upplýsingum (stærð, tegund, staðsetning, mat, osfrv.).

**Kaupverð** — verð eignar í samningi. Í kaupskrá er þetta í þúsundum króna. **Athuga**: Í listings-gögnum er `kaupverd` field-ið **ásett verð** (listing price), ekki söluverð — óljós field-naming.

**Þinglýstdagur (thinglystdags)** — dagurinn sem kaupsamningur var þinglýstur. Notað sem sale-date í kaupskrá.

**Útgáfudagur (utgdag)** — dagurinn sem samningur var útgefinn (undirritaður). Getur verið nokkrum dögum á undan þinglýsingardegi.

**Þinglýsing** — lagaleg skráning á kaupsamningi hjá sýslumanni. Án hennar er kaupverð ekki opinbert.

**Ónothæfur samningur (ONOTHAEFUR_SAMNINGUR)** — HMS flaggar samninga sem eru ekki á markaðsverði (t.d. fjölskyldusölur, undirverðs skipti, partitioning). 23% af öllum transaktíónum. Útilokað úr verðmatsmódeli.

**Fullbyggt (FULLBUID)** — flagg sem segir hvort eignin var fullbyggð á kaupdegi. FULLBUID=0 = nýbygging keypt áður en hún var tilbúin.

**Byggingarár (byggar)** — árið sem eignin var byggð.

**Einflm (einflm)** — einingastærð í m² (notagild stærð íbúðar).

**Lóðarstærð (lod_flm)** — flatarmál lóðar.

**FEPILOG** — 6-stafa kóði HMS sem flokkar property units (aðalíbúð, seinni íbúð, bílskúr, osfrv.). Decoding í TAXONOMY.md.

**Sveitarfélag (SVFN)** — sveitarfélagsnúmer. 1100 = Seltjarnarnesbær, 0000 = Reykjavík, osfrv.

**Áhvílandi** — lán sem hvíla á eigninni þegar hún er seld.

**Ferskt (ferskt flag)** — óljós merking í augl-gögnum. Líklega "nýlega sett á sölu" signal.

---

## Íslensk eignatagnakerfi

**Fjölbýli** — fjölbýlishús, íbúðarblokk með >2 íbúðum.

**Sérbýli** — kaupskrá flokkur sem sameinar parhús + raðhús + sérhæð.

**Einbýli** — einbýlishús, sjálfstætt hús á eigin lóð.

**Parhús** — tvö hús sem deila vegg, eitt á hvorri hlið.

**Raðhús** — þrjú eða fleiri hús í röð sem deila veggjum.

**Sérhæð / Íbúð á hæð** — heil hæð í fjölbýli sem er sér-eign, oft með sérinngangi.

**Rishæð** — efsta hæð undir risþaki, oftast með halla á loftum.

**Kjallaraíbúð** — íbúð í kjallara. Verðlögð oftast lægra per m² en jarðhæð.

**Penthouse** — efsta hæð, oft með stórum svölum/þakverönd, premium-verðlagt. Ekki HMS flokkur — birtist í lýsingum.

---

## Samningahugtök

**Kaupsamningur** — samningur um kaup á fasteign.

**Afsal** — skjal sem staðfestir eignarrétt. Getur komið á undan eða eftir þinglýsingu.

**Skjalanúmer** — sýslumannsembættis-númer (t.d. "R-005069/2006").

---

## Listing og scrape hugtök

**Listing event (raunveruleg auglýsing)** — Sjálfstæður atburður þar sem eign er sett á sölu, fær nýtt ásett verð, eða er re-listed eftir hlé. Hefur eigin `augl_id` frá fastinn.is og þinglystdags-dagsetningu sem endurspeglar hvenær listing var created eða updated. Pre-2024-10 listings í gögnunum eru næstum allt þess háttar; midnight timestamps (T00:00:00) eru dæmigerð.

**Scrape snapshot (daglegur scrape)** — Daglegt polling-snapshot af aktífri listing á fastinn.is. Post-2024-10 bætti scraper okkar við þessum reglulega. Precise timestamps (t.d. T09:12:03.423) gefa þá til kynna. Mörg snapshots geta verið af sömu underlying listing.

**Session (selling session)** — Lífsferill listings á sömu eign: frá fyrsta listing þar til það er withdrawn eða leiðir til sölu. Ein eign getur haft margar sessions yfir árin (t.d. tilraun 2016 sem endaði í withdrawal, önnur tilraun 2023 sem leiddi í sölu 2024).

**Augl_id** — Globally unique listing identifier frá fastinn.is. Monotonic approximately over time (Spearman > 0,99 við thinglystdags). Notað sem fallback date signal þegar thinglystdags er corrupt.

**Withdrawn listing** — Listing sem endaði án sölu (ekki matching kaupskrá record innan reasonable time window). Ekki í þjálfun módels, en notað sem leading indicator í markaðsyfirliti.

**Ask-to-sale ratio** — `sale_price / listing_price` fyrir paraðar listings+sales. Median ~0,98 á Íslandi (listings markaðsverð er 2% lægra en sale price á average, eftir negotiation).

---

## Gagnalag-hugtök í verkefninu

**Pre-merge DB** — Raw scraper output SQLite files (`D:\Gagnapakkar\fasteignir{,1,2,3,4}.db`), hver framleidd af einum scraper-instance. Canonical source.

**v2 pickles** — Hreinar pickle skrár framleiddar af `parse_all_dbs.py` úr öllum 5 pre-merge DBum, með réttri dedupe og clean dates. Canonical data layer fyrir Áfanga 1.5+.

**Merged DB** — `D:\fasteignir_merged.db`, aflögð (deprecated). Tapaði 82% af `thinglystdags` í merge-ferlinu. Haldin á diski fyrir sögulega reference.

**Devalue** — JSON-serialization format SvelteKit (notar flat array með references). Parser í `devalue.py`.

---

## Tæknihugtök í verkefninu

### ML / tölfræði

**Hedonic módel** — regression-módel sem spáir verði út frá eiginleikum (stærð, staðsetning, osfrv.). Gefur "verð án condition-adjustment".

**Residual** — mismunur milli raunverðs og spáverðs. Í módelinu okkar á condition/extraction-lagið að útskýra systematic residuals úr baseline.

**Repeat-sale pair** — tvær sölur á sömu eign. Notað til að mæla raunverulega verðbreytingu án systematic biasar frá eiginleikum.

**CPI-deflated** — verðlag skaleruð niður á sama neyslufverðlag. Notað til að aðskilja raunverðsbreytingar frá verðbólgu.

**Quantile regression** — módel sem spáir ekki bara meðaltali heldur tiltekinni percentile (P10, P50, P90, osfrv.). Notað fyrir prediction intervals.

**Prediction interval** — bil sem spáin ætti að liggja innan með tilteknum líkum (t.d. 80% eða 95%).

**LightGBM** — gradient boosting framework fyrir tabular gögn. Styður quantile loss native.

**SHAP (SHapley Additive exPlanations)** — aðferð til að útskýra hvaða feature höfðu hvaða áhrif á spá. Notað fyrir explainability.

**MAPE (Mean Absolute Percentage Error)** — mælikvarði á módelgæði, hlutfallsleg meðalskekkja.

**Drift detection** — aðferðir til að finna út hvenær gögn (eða performance) módel er að breytast yfir tíma.

**Shadow deployment** — nýtt módel spáir á raunverulegt traffic án þess að notað sé, til samanburðar við núverandi.

**Backtest** — mæling á því hversu vel módel spáir atburðum sem gerðust eftir að það var þjálfað (out-of-time).

### Data engineering

**Form action (SvelteKit)** — server-side endpoint sem tekur við POST og skilar devalue-formatted response.

**ETL** — Extract-Transform-Load, klassískt data pipeline pattern.

**Dagster** — orchestration framework fyrir ETL/ML pipelines. Asset-centric — lýsir hvaða "eignir" (datasets, módel) eru framleiddar af hverju skrefi.

**MLflow** — framework fyrir experiment tracking og model registry.

**Canonical data layer** — endanleg, cleanað gagnalag sem allir consumers lesa af. Einn sannleikur. Í okkar verkefni: v2 pickles.

**Asset lineage** — rekja hvaða dataset varð til úr hvaða, með version og dagsetningu.

**Dedupe (strategy)** — aðferð til að fjarlægja duplicate rows. Í okkar verkefni: sort priorities + `drop_duplicates(keep='first')`, með date_valid og scraped_at sem tiebreakers.

**Monotonic interpolation** — ef gögn eru sorted og monotonic í einum variable, getum við interpolated óþekkt gildi af öðrum. Reynd en deprecated í 1.5c vegna corruption upstream.

### Infrastructure

**Docker** — containerization — keyra applications í einangruðum "container" sem hefur eigin environment.

**Docker Compose** — YAML-skilgreining á multi-container applikíasjón (t.d. app + database + monitoring í einum stack).

**PostgreSQL** — relational database, industry-standard fyrir analytics/OLTP.

**PostGIS** — PostgreSQL extension fyrir spatial queries (lat/long, distances, polygons).

**DuckDB** — analytics-optimized embedded database. Góður fyrir stór aggregation queries. Sidecar ef þarf.

**Cloudflare R2** — S3-compatible object storage án egress-gjalda.

**Backblaze B2** — ódýr object storage, notað fyrir backups.

**Hetzner** — þýskur hosting provider með vel-verðlagðum dedicated servers.

**FastAPI** — Python web framework fyrir API-smíði.

**Grafana / Prometheus** — monitoring stack fyrir infrastructure metrics.

**Sentry** — error tracking / alerting.

**SSH key** — cryptographic key fyrir secure remote login (í stað passwords).

**fail2ban** — tól sem blokkar IP-addresser sem reyna of oft að brute-force login.

---

## Verkefnisstaðlar

**Áfangi 0, 1, 2, ...** — stig verkefnis skilgreind í STATE.md.

**Segmentering** — flokkun gagna í undir-safn (t.d. einbýli í 101) sem módelið meðhöndlar sérstaklega.

**Extraction** — í samhengi okkar: að lesa lýsingu með Claude API og draga fram strúktúruð gögn (ástand, endurbætur, osfrv.).

**Data-driven** — allar ákvarðanir byggðar á því sem gögnin sýna, ekki á forsendum eða plástrum.

**Market health indicator** — mælikvarði sem spáir fyrir um framtíðarþróun markaðar (t.d. withdrawal rate, list-to-sale ratio).

**Affordability index** — mælikvarði á hversu auðvelt/erfitt er fyrir miðgildisheimili að kaupa miðgildiseign, gefið vexti og tekjur.

---

## Repeat-sale index hugtök (Áfangi 6)

**Repeat-sale index** — verðvísitala sem byggir á sömu eign seldri oftar en einu sinni. Styrkur: controllar fyrir „composition drift" (ef dýrari hverfi seljast mest á ákveðnu ári, þá skekkir median-verð-index). Veikleiki: krefst 2+ sölu per eign, svo thin-sample cells fá víðar confidence bands.

**BMN (Bailey-Muth-Nourse)** — OLS regression sem fittar repeat-sale data: target er log(P_t2 / P_t1), design matrix hefur +1 í t2 column, -1 í t1 column, 0 annars staðar. Dummies per quarter. Baseline quarter (2006Q2) fær 0 fyrir identification. Index per quarter = exp(beta_q) × 100. Vanalega best-practice staðall fyrir housing indices; notað af Federal Housing Finance Agency (FHFA) og others.

**Case-Shiller** — repeat-sale methodology sem S&P publishar fyrir US housing. Notar weighted BMN með interval-distance weights. Base BMN er closer í anda; GMRCS (Geometric Mean Revert Case-Shiller) er smoother variant fyrir noisy segments.

**Nominal vs real index** — nominal er pure price change (inniheldur verðbólgu). Real er CPI-deflated, þ.e. raun-markaðshreyfingin. Fyrir Ísland þar sem CPI vex ×2,66 yfir 2006→2026, er munur nominal vs real gríðarlegur (370 vs 141 vísitölupunktar á APT_STANDARD RVK). Real er methodology-lega réttari fyrir market analysis; nominal er aðeins nytsamlegur sem toggle í dashboard.

**Consecutive pairing** — fyrir FASTNUM með 3+ sölum: byggir consecutive pör (t1→t2, t2→t3), ekki all-combinations C(n,2). Simpler, no double-counting; vanalega default fyrir Case-Shiller-style indices.

**Cell (í repeat-sale samhengi)** — (canonical_code × region_tier) slice sem OLS regression keyrir á. Dæmi: APT_STANDARD × RVK_core er ein cell með 10.594 pörum, 81 quarterly beta-gildum plús CI.

**data_quality flag** — per-period flokkun í repeat_sale_index output: `high` (n_period≥20 AND se<0,05), `medium` (n_period≥5 AND se<0,10), `low` (n_period≥1), `insufficient` (n_period=0 → index NaN). Dashboard filtering tool.

**paired_fresh / off_market / post_sale_only (pair_status taxonomy)** — sjá DATA_SCHEMA.md pairs_v1 section. Fyrir repeat-sale index nota allir pair_status sem eru arm's-length (pairs_v1 er þegar ONOTHAEFUR-filtered).

---

*Bætið við nýjum hugtökum eftir því sem þau koma upp.*
