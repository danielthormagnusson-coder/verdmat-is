# PROMOTE-TIMEOUT RÓTARGREINING — cc11

**Stimpill:** 2026-07-10T08:45Z (klukka sannreynd tvíhliða: local 08:36:58 = UTC, ytri viðmiðun google Date-haus 08:36:59 GMT — Ísland er UTC, frávik ≤1s)
**Staða:** GREINING LOKIÐ + VALKOSTA-MAT — **HALT fyrir lið 3, ekkert lagað, ekkert keyrt sem skrifar**
**Leiðrétting á verkbeiðni:** bilaða skriptan er `scripts/promote_listings_append.py` (Lag-1 append í promote-fasa nightly-delta-keðjunnar), EKKI „rebuild_lookup_grid.py" — það skriptunafn er ekki til í trénu; JARDTENGING_2026-07-09 lið 5 nefnir rétta nafnið.

---

## 0. STÓRFRÉTT SEM BREYTIR VERKINU: nótt 09→10 var CHAIN CLEAN — skuldin er þegar flushed

Verkbeiðnin gerði ráð fyrir 3ja nátta frosinni skuld. Raunin (night_20260710.log + Task Scheduler):

| Nótt | Promote | Smáatriði |
|---|---|---|
| 06→07 | ✓ clean | append 23.373 raðir á 1.017,9s |
| 07→08 | ✗ ABORT exit 14 | `QueryCanceled: statement timeout` í write_batch |
| 08→09 | ✗ ABORT exit 14 | nákvæmlega sama lína |
| **09→10** | **✓ CHAIN CLEAN exit 0** | **append 25.023 raðir á 1.361,8s; extraction keyrði (effective_n=200, valued 841, $1,42); TOTAL 79 síður/1.234 listing; Task Scheduler Last Result = 0x0** |

Full-endur-upsert-hönnunin þýðir að ein hrein keyrsla skrifar ALLAN korpusinn — þ.m.t. það sem nætur 08+09 misstu af. Sannreynt í DB: `max(last_seen_at) mbl = 2026-07-10 03:08Z`, 25.030 mbl-raðir. **Engin handvirk catch-up-keyrsla þarf; liður 3 í verkbeiðninni fellur niður að hálfu.** En keðjan er á hnífsegg — nótt 10 tókst með FLEIRI raðir en næturnar sem féllu; það er dreifni, ekki bati. Rótarfixið stendur óbreytt eftir.

---

## 1. GREINING

### 1a. Nákvæm villa og ferill nætur

**Villan (07→08 og 08→09, staflarekjur samhljóða):**
```
File "...\promote_listings_append.py", line 206, in write_batch
  execute_values(cur, "INSERT INTO scraper.listings (...) VALUES %s
                       ON CONFLICT (source, source_listing_id) DO UPDATE SET ...", rows, page_size=1000)
psycopg2.errors.QueryCanceled: canceling statement due to statement timeout
```

**Hve langt komið per nótt:** parse ✓ + canonical sale ✓ (260–303s) + canonical rent ✓ komust alltaf í gegn; aðeins Lag-1-append féll. Hvaða 2.000-raða skammtur (af 13) féll er **óþekkt — skriptan loggar enga per-skammt framvindu** (sama athugunar-gat og Stage B, sbr. feedback_stage_b_observability_gap). Extraction keyrði ekki nætur 08/09 (gate-uð aftar í keðju).

**Stærðir og tímar per tilraun (úr promote_*.log):**

| Nótt | Raðir (records) | Append-tími | ms/röð |
|---|---|---|---|
| 06-29 | 19.537 | 711,7s | 36,4 |
| 07-04 | 22.282 | 942,6s | 42,3 |
| 07-05 | 22.448 | 890,2s | 39,7 |
| 07-06 | 22.629 | 944,3s | 41,7 |
| 07-07 | 23.373 | 1.017,9s | 43,5 |
| 07-08 | 24.007 | **TIMEOUT** | — |
| 07-09 | 24.513 | **TIMEOUT** | — |
| 07-10 | 25.023 | 1.361,8s | 54,4 |

### 1b. Af hverju óx tíminn — og hvert er þakið

- **Þakið:** `statement_timeout = 120000 ms (2 mín)` á **instance-stigi** („configuration file" í pg_settings). `postgres`-hlutverkið (sem .dbconfig-pooler-DSN tengist sem) hefur ENGA yfirskrift í rolconfig — instance-gildið gildir. anon=3s/authenticated=8s koma málinu ekki við.
- **Eining sem mælist gegn þakinu:** hver `execute_values`-síða = **ein 1.000-raða INSERT..ON CONFLICT DO UPDATE setning**. 25.023 raðir ≈ 26 síður; heild 1.361,8s ⇒ **~50s meðaltal per síðu; halinn á dreifingunni fer nú yfir 120s** á lakari nóttum. Nótt 10 slapp, 08/09 ekki — hnífsegg, ekki mynstur.
- **Af hverju er 1.000-raða upsert svona þungur:** `scraper.listings` er 26.338 raðir en **400 MB alls — heap 24 MB, index 5 MB, TOAST 364 MB** (~14 KB/röð: lysing-textinn + photos_json). TOAST-stærð ≈ lifandi gagnamagn (26,3K × 14KB ≈ 369MB) svo þetta er **ekki bloat** heldur raunveruleg farmþyngd: full-endur-upsert endurskrifar ~364 MB af TOAST + WAL á hverri nóttu þó ~95% raða séu efnislega óbreyttar (`DO UPDATE ... updated_at=now()` án no-op-varnar þvingar líkamlega endurskrift hverrar raðar). n_tup_upd=240K ævi-uppfærslur, aðeins 28% HOT. Autovacuum heldur í við (n_dead_tup=0, keyrði 04:06 í morgun) — hann er ekki vandinn.
- **Vöxtur korpuss:** ~500 raðir/nótt (24.632 → 25.139 → 25.634 parsed sale 08→10); línulegur vöxtur ofan á ~50s/síðu sem þegar er í 42% af þakinu.
- **Lokk-bið/árekstur ÚTILOKAÐ sem drifkraftur:** bilanirnar urðu 04:12–04:26, EFTIR að myigloo (02:00–02:21), sales-refresh (02:30) og backup (03:00, snertir ekki PG) luku sér af. Nótt 10 tókst með stærsta korpusnum.
- **Index-ástand:** ekki orsök — allir 6 indexar samtals 5 MB.

### 1c. Hvað þarf downstream RAUNVERULEGA

Full-endur-upsert er **hönnunarleif**: docstring-rökin („Watermark-INDEPENDENT ... FULL re-listing trajectory") áttu við EINA backfill-keyrslu, ekki hverja nótt. Lesendur `scraper.listings`:

| Lesandi | Les | Þarf full-upsert? |
|---|---|---|
| ops-merki (20260628093000) | `max(last_seen_at)` per source | NEI — last_seen_at breytist aðeins á röðum sem sáust í delta; diff-skrif skilar sama max |
| lifecycle_sweep_mbl | status/price_amount/fastnum á active | NEI — efnis-svið; delisting kemur hvort eð er frá sweep, ekki promote |
| extraction_engine/seed | efnis-svið kandídata | NEI |
| /ops-síða + MARKET_OVERVIEW | telur/summar efnis-svið | NEI |

**Ekkert les `updated_at` sem „enn á lífi"-merki á óbreyttum röðum.** mbl-fetch er sjálfur delta — parsed-röð óbreytts listings breytist ekki milli nátta, svo endur-upsert hennar er 100% no-op efnislega. Delta-skrif er downstream-jafngilt.

**Delta-lykill er þegar til í gögnunum:** parse_mbl endur-parse = DELETE+INSERT ⇒ breytt/ný listing fær **nýtt hærra parse_id**; óbreytt röð heldur sínu. Næturbreytingamengið er inserted+replaced ≈ 600–1.500 raðir (loggað per nótt). Eina viðbótin: unit_key getur breyst á NÁGRANNARÖÐUM (stærðar-klasar per fastnum) þegar ný röð bætist í klasa — leysanlegt með ódýrum granna-lestri (SELECT source_listing_id, unit_key WHERE source='mbl' — 25K örraðir, engin TOAST-snerting) og diff.

---

## 2. RÓTARFIX-VALKOSTIR (HALT — ekkert keyrt)

### (i) Delta-skrif — **STAÐFEST sem rétta lausnin; MÆLT MEÐ**
Skrifa aðeins: (raðir með parse_id > watermark síðustu hreinu keyrslu) ∪ (raðir þar sem reiknað unit_key ≠ unit_key í PG).
- **Útfærsla:** unit_key-úthlutun reiknast áfram yfir ALLAN korpusinn í minni (SQLite-lestur, sekúndur — óbreytt); aðeins skrifmengið þrengist. Watermark = max(parse_id) per töflu, geymt í state-skrá (mynstur mbl_fetch_state.json) eða PG-örtöflu; **færist aðeins áfram eftir hreina keyrslu** (abort-not-retry helst; endur-keyrsla eftir fall endur-skrifar sama delta — upsert er idempotent, öruggt). price_history-insertar þrengjast eins (ON CONFLICT DO NOTHING helst).
- **Hvað lagast:** næturskrif 25K→~1–2K raðir ⇒ 1–2 setningar ≈ 30–100s heild, ~7% af þakinu per setning; TOAST-churn 364MB→~20MB/nótt; vöxtur verður O(dagleg breyting) í stað O(korpus) — vandinn kemur ekki aftur með vexti.
- **Hvað stendur eftir:** bootstrap fyrsta watermarks (heppilega er staðan NÚNA fullskrifuð eftir hreinu nótt 10 — watermark má stilla á núverandi max(parse_id)); discovered_at/first_seen_at write-once-semantík óbreytt.
- **Áhætta:** lág-miðlungs — villuflötur er watermark-bókhaldið; prófanlegt með --limit-smoke + einni vöktaðri nótt. **Umfang:** ~60–100 línur í promote_listings_append.py + state-geymsla.

### (ii) Chunking/minni síður (page_size 1000→200) — plástur, staðfest mat verkbeiðni
Setning ~10s í stað ~50s; timeout hverfur í bili. **Leysir EKKI:** 364MB TOAST-churn/nótt, ~23 mín skriftími heldur áfram að vaxa O(korpus), autovacuum/WAL-álag. Eins línu breyting, áhætta ~engin. Aðeins réttlætanlegt sem skynditrygging MEÐ (i) í backlog.

### (iii) Session/tx-timeout-hækkun — plástur; tæknilegt smáatriði skiptir máli
Á transaction-pooler (6543) lifir session-`SET` EKKI milli færslna — þyrfti **`SET LOCAL statement_timeout='10min'`** inni í hverri write-færslu (á eftir `SET TRANSACTION READ WRITE`). Virkar, `postgres` má setja GUC-ið. Hreinn plástur: tíminn vex áfram og étur nóttina. Aðeins ásættanlegt sem brú MEÐ (i) — og brúin er varla nauðsynleg lengur því skuldin er núll í dag.

### (iv) Annað úr greiningunni
- **No-op-vörn á upsertinn** (`DO UPDATE ... WHERE (l.br_dags, l.price_amount, l.status, l.last_seen_at) IS DISTINCT FROM (EXCLUDED...)`): sker burt ~95% af heap/TOAST/WAL-skrifum án watermark-bókhalds — en setningin flytur og ber saman áfram allan korpusinn (detoast við samanburð), svo tíminn batnar minna en (i) og O(korpus)-flutningurinn helst. Millileikur ef (i) þykir of stór biti.
- **Per-skammt framvindulogg** (batch i/13, sek/skammt) í write-lykkjuna: ~3 línur; lagar athugunar-gatið óháð valkosti. Mæli með að þetta fylgi hvaða fixi sem valið er.
- **Index/tímasetningar:** hvorugt orsök (index 5MB; árekstrar útilokaðir í 1b) — engin aðgerð.
- **Sama mynstur bíður í `promote_myigloo_listings_append.py`** (execute_values page_size=1000, full-upsert): korpus aðeins 1.308 raðir svo langt í þak, en sama fix-mynstur á við þegar visir (~1,5–2× myigloo) bætist við.

### Tillaga
**(i) delta-skrif sem rótarfix + framvindulogg úr (iv); (iii) SET LOCAL sem öryggisnet í sömu færslu** (skaðlaust, ver catch-up-keyrslur framtíðar). Bootstrap watermark á stöðuna eftir hreinu nótt 09→10. Vöktuð nótt á eftir; vænt tölur EKKI stórar (skuldin er þegar flushed — fyrsta delta-nótt á að skrifa ~600–1.500 raðir, EKKI 25K; ef hún skrifar 25K er watermarkið brotið).

---

## 3. [GATE-AÐ — BÍÐUR GO] Útfærsla

Fellur til eftir go á valkost. Athugið breytta stöðu: **catch-up-liður verkbeiðninnar er þegar uppfylltur af nótt 09→10** (CHAIN CLEAN, halt_reason=None allir fasar, Last Result 0x0, extraction keyrði, totals í night_20260710.log) — staðfestingar-liðirnir snúa því aðeins að fixinu sjálfu: smoke með --limit, ein vöktuð nótt, skjalfesting væntra LÍTILLA talna (öfugt við verkbeiðnina), commit explicit paths + push.

---

## VIÐAUKI A (2026-07-10T09:45Z, eftir go á (i)): morgun-hnignun grunnsins staðfestir I/O-rótina

Við útfærslu-prófun kl. ~09:00–09:30Z reyndist grunnurinn alvarlega hægur: `pgbouncer.get_auth` (venjulega <1ms) tók 13,7s, postgres_exporter-metrics-fyrirspurnin >2 mín, `count(*)` yfir properties (232.887 raðir) 54,4s, og preload_props-postnr-fyrirspurnin (sem gengur á sekúndum á nóttunni) hitti 120s-þakið ítrekað. Postgres-loggar (auto_explain + villur) sýna **~1 statement-timeout á mínútu frá a.m.k. ~08:00 local** — það er postgres_exporter-skrapið sjálft að falla á 120s í hverri umferð, þ.e. vélin var I/O-svelt áður en nokkur cc11-fyrirspurn snerti hana. Katalóg-fyrirspurnir (pg_settings, pg_stat_*) svöruðu samstundis á sama tíma → mynstrið er **disk-I/O-throttle (burst-budget-þurrð), ekki CPU/lokkar**.

Túlkun: næturlega 364MB+ TOAST/WAL-endurskriftin er ekki bara statement-timeout-áhætta kl. 04 — hún étur I/O-budget vélarinnar og skilur morguninn eftir throttl-aðan. Delta-fixið ræðst beint á þetta (skrifmagn ~93–97% minna). Engin merki um OOM, checkpoint-storm, endurræsingu eða lokka í loggunum; ACTIVE_HEALTHY allan tímann.

Aths. tímastimplar: Supabase-logga-tímarnir birtust +7h á undan sannreyndri UTC-klukku (fetch-epoch 09:16:10Z passar við „16:16" í loggum) — mögnun greiningarinnar tekur mið af því; local-klukkan sjálf er rétt.

Framvinda þurrðar: grunnurinn svaraði ekki (pooler-handaband féll, API timeout) ~08:00–11:45Z; bati staðfestur 11:47Z (properties-skann 1,3s, var 54,4s kl. 09:19Z). Engin notenda-aðgerð — jafnaði sig sjálfur, samræmt burst-budget-endurfyllingu. Prod-appið sýndi engar runtime-villur allan tímann.

## VIÐAUKI B (2026-07-10T11:55Z): útfærsla (i) + dry-run-staðfesting

**Útfært í `scripts/promote_listings_append.py` (v2, listings_append_v2):** (a) parse_id-watermark delta ∪ unit_key-drift ∪ missing-in-db self-healing (full-fallback ef state vantar); (b) per-skammt framvindulogg (`batch i/N ... Xs`); (c) no-op-guard `WHERE (röð) IS DISTINCT FROM (EXCLUDED)` á upsertinn; (d) `--dry-run` flagg (núll skrif); watermark færist AÐEINS eftir hreina fulla keyrslu (--limit/--dry-run aldrei). 120s-þakið ósnert skv. fyrirmælum — er nú öryggisnet sem á að gelta ef delta-leiðin bilar. Watermark bootstrappað á hreinu stöðu nætur 09→10: `scraper_data/mbl_promote_append_state.json` (sale=49122, rent=2885).

**Dry-run 11:52Z: PASS.** `write-set: total=1 (parse-delta=0 unit-drift=1 missing-in-db=0; unchanged-skipped=25022)` á 35,0s (vs 1.361,8s full skrif). Eina drift-röðin (slid=1668226) er FYRIRLIGGJANDI v1-ódeterminismi í resolve_fastnum, ekki regression: tvær matseiningar á sömu adressu/hnitum (Vallarbraut 3, 300 — fastnum 2100734 einflm 59,3 / 2100744 einflm 90,4) eru jafntefli fyrir 65,2m² listing og valið flöktir milli keyrslna (flökti líka undir v1 en var ósýnilegt í full-endurskrift). Skaðlaust á n=1 — delta-skrifar þessa einu röð nótt hverja; framtíðar-snyrting = deterministic tie-break (röðun kandídata) í resolve_fastnum (promote_mbl.py).

**SÖNNUNARVIÐMIÐ nætur 10→11 (skráð í STATE):** vænt ~600–1.500 skrifaðar raðir (+1 drift-röðin). **~25K skrifaðar = watermarkið brotið → HALT og greina**, ekki fagna skuldar-flushi. Vænt heildar-append-tími <3 mín með per-skammt línum í promote_20260711.log.
