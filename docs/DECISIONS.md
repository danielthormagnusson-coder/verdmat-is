# DECISIONS — Arkitektúrákvarðanir

Skrá yfir lokaðar ákvarðanir með dagsetningu og rökstuðningi. Nýjar ákvarðanir bætast við efst.

---

## 2026-06-15 — Þrjár hreinar nætur + Step 3d empirical foundation

**(1) STEADY-STATE STAÐFEST — sjálfvirka delta-keðjan stöðug yfir 13./14./15.6**:
- `LastTaskResult=0` öll þrjú kvöld; `halt_reason` null í öllum 6 mode-um; hvert log endar á **CHAIN CLEAN**.
- Blob-counts: nótt 1 = **68 síður / 1047 listings** (2ja daga uppsöfnun frá priming, vænt); nótt 2 = **20 síður / 293**; nótt 3 = **27 síður / 396**.
- High-water færist áfram monotónískt á öllum 4 delta-modes; **100% `fields=v2`** á öllum delta-síðum; `fetch_kind *_negotiable_delta` sýnir delta-fix **471edc7** virkan.
- `session_request_count` = **1727** uppsafnað; pre-flight budget **400/900** með ríflegu borði (mest 68 nýtt á einni nóttu).
- Engin cap-hit, engin neitun, engin process að lifa milli nætur.

**(2) STEP 3D EMPIRICAL FOUNDATION (CC2.1 könnun 15.6)**:

***Fastnum encoding-uppgötvun (endurnýtanleg þekking)***:
- mbl-`fastano` er EKKI uniformly 7-stafa HMS-fastnum. Encoding er `fastano = fastnum × 10^k + matshluti` (leiðandi 7 stafir = HMS canonical fastnum, aftari 1–2 stafir = matshluti/eining-index).
- Empírísk sönnun gegn `public.properties.fastnum` (232.887 raðir 100% 7-stafa, range 2.000.044–2.543.427):
  * 8-stafa `//10` → **95,4% hittni** (5.639/5.910)
  * 9-stafa `//100` → **91,0% hittni** (2.944/3.236)
  * 7-stafa hrátt → 73,8% (foreign + vantar í properties)
  * Rangir transformar (8`//100`, 9`//10`) → **0%** (afsannar tilviljun)
  * Random baseline 43%
- Dreifing í `parsed_mbl_sale` (N=13.873): NULL 5,9% / 7-stafa 10,1% / 6-stafa 1,2% / 8-stafa 50,6% / 9-stafa 32,1%.
- Implication: Step 3a probe sá „6–9 digit, EKKI uniformly 7-digit" en greindi ekki encoding-ið — pre-amendment sample og engin transform-prófun. Framtíðar uppsprettur (HMS staðfangaskrá, kaupskrá multi-parcel) gætu borið sama mynstur og á að prófa fyrir parser-hönnun.

***Resolution rates***:
- `parsed_mbl_sale` (N=13.873): derived fastnum ∈ properties = 11.852 (85,4%); non-foreign = **11.789 / 12.733 = 92,6%** (sambærilegt við visir 93%).
- `parsed_mbl_rent` ber ENGAN fastnum-dálk → 100% rent gegnum address/geo resolution (eins og visir-rent + myigloo).

***Cross-source overlap (mbl × canonical 1.266)***:
- mbl-sale × visir-sale = **198/208 same-tenure** (95% af visir-sale finnst á mbl, en aðeins **2,4% af mbl-sale** = 198/8.396).
- mbl × allt canonical fastnum-overlap = 416/1.096 (38% af canonical).
- mbl er overwhelmingly net-new — bætir ~97,6% net-nýju við sale-corpus.
- Match-gæði há (sample 10: sama heimilisfang + sama verð beggja vegna).
- **SOURCE-PRIORITY STATUS QUO LÆST** empírískt: visir(1) > mbl(2) > myigloo(3). Á 198 same-tenure overlap-i vinnur visir (§2.3-D rök: hreinni SSR-parse), mbl foldast í `secondary_source_ids[]`. Munur í endanlegu canonical-i ~10 raðir — ekkert efnislegt rök til að snúa við.

***Post-3d canonical-stærð spá***: 1.266 → **~11.000–13.500 raðir** (efri mörk ef listings haldast per-listing; neðri ef fastnum-dedup þéttir re-lists). mbl bætir 9.000+ nýjum eignum.

***Þrjú LÆST design-flögg fyrir 3d hönnun***:

1. **Unit-collapse (~270 multi-unit nýbyggingar)**: matshluta-suffix VARÐVEITTUR í eigin dálki í canonical-laginu (t.d. `matshluti_unit_id`), ekki sleppt. Rök: kaupskrá vinnur við building-base 7-stafa, en listings auglýsa einstakar einingar; collapse myndi týna per-unit comparables og þétta multi-listings af sama building (t.d. Hringhamar 37 = 16 listings → 1 fastnum) sem ruglar pricing-tölfræðina. Dálkurinn NULL fyrir visir/myigloo (gögn ekki til þar), gildi þaðan sem það er til.

2. **atv-tenure misclassification**: tenure leiðast af parse-merkjum (`tegund_raw` + „(leiga)" í gata + verd=0), EKKI af mbl-endapunkti (`fs_fasteign` er bara root-name, ekki tenure-signal). 1.328 negot-atv bíða prómotunar; hve hátt hlutfall er commercial-rent mælist í prómot-keyrslunni sjálfri. Tenure-cascade sama mynstur og visir/myigloo nota. Án þessa: massíf tenure-mistök OG miss-dedup gegn visir/myigloo commercial-rent (cross-tenure 233-skörun verður þá same-tenure dedup-eligible).

3. **is_foreign sía**: foreign-sía keyrir ÁÐUR EN fastnum-resolution (truncation-collision sönnuð empírískt — spænskar 8–9 stafa fastano truncate-ast óvart í properties-range, t.d. „SPÁNAREIGNIR — Villamartin" fastano 204130526 → 2041305 ∈ props). Íslenskt-override: postfang ∈ {101–902} OR lat 63–67,5 → ekki útilokun jafnvel þótt sentinel-postfang (1053/1000) birtist (Vesturvin-leki, 21 raðir ranglega flaggar). Sentinel-postfang eitt og sér nægir EKKI sem foreign-merki ef íslenskt signal er annars staðar í röðinni.

**(3) JORD-MYSTERY LEYST (mini-probe 15.6)**:
- mbl aggregate í dag: jord_all 775, fjolb_all 7293 — nánast óbreytt frá Step 3a (9.6) jord 778 / fjolb 7266.
- parsed jord 387 ≈ publishable jord 306 + negotiable 69 = 375 (mismunur 12 = churn 12.→15.6).
- „778 → 387" var ALDREI like-for-like — publishable/draft-sían að virka eins og hönnuð; jord/lóðir hafa oft verd=0 eða fermetra=0 drög (~400 raðir) sem seed-crawl síar af ásetningi (`where: verd>0, fermetrar>0`).
- Hvorki mbl-reclassification né parser-villa. **No-op fyrir 3d.**
- **Lærdómur**: bera saman like-for-like (publishable vs publishable) áður en flokkunar-shift er kallaður parser-villa. Hasura aggregate-count án where-klausu er EKKI sambærilegt við parsed-corpus.

**Næst**: Step 3d hönnunarprompt fyrir `promote_mbl` — afgreiðir þrjú flögg að ofan, mælir atv-tenure raunverulega dreifingu í prómotuninni, promotar mbl-corpus í canonical (1.266 → ~12K raðir). Hvert gated skref sér go.

---

## 2026-06-11 (§6-A + delta-vélbúnaður) — Nightly delta orchestration spec-amendment + chain v1 smíðuð (ÓVOPNUÐ)

**Hvað**: §6-A amendment skrifað í un-tracked spec-draftinn (SCRAPER_SPEC_v2_draft.md,
1.066 → 1.230 línur, additive) og allur delta-vélbúnaðurinn smíðaður, testaður og
live-validated — en VOPNUN bíður operational gates (re-sweep exhaust → full-corpus parse
→ prime → task-arming). Scraper-commits dagsins: 8abc01e (Step 3c parse_mbl tier, 963
línur, 17 testar — full-corpus keyrsla gated á re-sweep lok), 471edc7 (delta-göp),
23726b9 (chain + scheduler).

**§6-A amendment efnislega (lifecycle per source)**: mbl = delta-only nightly
(urgency-locked); visir = vikulegt timed-batch refresh undir IP-throttle (≤300 req/batch,
45–60 mín pásur, ~10–15h); myigloo = nightly index-walk (9 síður — gefur ókeypis
withdrawal-diff) + vikulegt full detail (~22 mín).

**Withdrawal detection — fyrsta flokks hönnun, EKKI neðanmáls**: mbl hard-deletar →
hvarf ER afskráningardagurinn sem time-on-market og T1 asking-vs-sold þurfa. Lykilinnsýn:
**16-raða þakið er per REQUEST óháð field-fjölda → id-only liveness-sweep kostar
nákvæmlega sömu ~950 síður og full enriched sweep** — þar með er vikulega liveness-sweepið
FULL ENRICHED re-sweep (sama budget kaupir liveness-diff OG content/mynda-refresh í einu;
re-sweep vélbúnaðurinn b57b7c0 er tólið). Diff: live id-mengi vs is_active mbl-mengi í
canonical → withdrawn_at. **Interval-semantík á withdrawn_at**: vikuleg sweep gefur bil
(last_seen_at = neðri mörk, sweep-dagur = efri), ekki punktdag — ±3,5 dagar á metric sem
mælist í vikum; skjalfest í column-comment. **Cadence: laugardagskvöld vikulega**
(nightly = allt §0.5 budgetið á hverri nóttu, ósjálfbært; monthly = ±2 vikur, of gróft).

**TVÆR LOCKED RULES**:
1. **Since-priming er SKYLDA fyrir fyrstu delta-nótt (1970-guard)**: since_key=NULL
   post-seed þýðir að fyrsta delta sweepar frá epoch og advance-ar high-water framhjá
   page-budget þakinu — breytingar handan þaksins skippast VARANLEGA. Prime úr parsed
   corpus maxima (prime_delta_since.py), aldrei 1970-keyrslu af stað.
2. **§2.3 `is_active` amendað í per-source liveness-semantík**: 2-daga reglan
   (last_seen_at ≥ run_ts − 2d) gerði ráð fyrir nightly-full-sweep uppsprettum og hefði
   **mass-false-withdrawað allan mbl-stofninn** undir delta-only steady-state (óbreytt
   heilbrigð listing sést aldrei milli vikulegra sweepa). mbl: explicit liveness-sweep
   diff EINGÖNGU; myigloo/visir: absence úr þeirra index; delta-hit refreshar
   last_seen_at en absence úr delta þýðir EKKERT.

**Delta-göpin tvö + fixar (471edc7)**: (1) negotiable sneiðin var delta-blind (delta-modes
báru publishable predicate — 72,3% af real rent corpus hefði aldrei fangast í
steady-state) → delta-sale-negotiable + delta-rent-negotiable með eigin since_keys og
fetch_kind discriminatorum (haldið undir list_page_ prefix fyrir parser-samhæfni);
(2) prime_delta_since.py með hörðum REFUSE-girðingum (live fetcher via process-scan +
recency-heuristik / since þegar sett nema --force m. history-archive / tómur parsed
slice), dry-run default, atomic state-write. Testar 30 → 37.

**Nightly chain v1 + scheduler smíðuð, live-validated, ÓVOPNUÐ (23726b9)**:
nightly_delta_chain.sh = 4 delta-modes serial, gated á exit 0 + halt_reason null,
abort-not-retry, pre-flight girðingar (exit 2): live-fetcher / since-primað / 24h-budget
≤900 síður; cap-hit WARNING per mode (high-water advance-ar framhjá ósweepuðum síðum við
cap); morgunreport í night_logs/ (síður/listings/high-water/halt per mode + samtala);
PYTHONIOENCODING=utf-8 (run_monthly latent-bug #5 lexían — mojibake sást í fyrsta dry-run,
root-fixað). **Dry-run live-validation sannaði allar þrjár girðingar gegn raunveruleikanum**:
fann keyrandi re-sweep prósessinn, flaggaði öll fjögur óprimuð since_keys, taldi 488+400=888
≤ 900. register_delta_task.ps1 = verdmat-nightly-delta 01:00 daily, speglar backup-mynstrið
MEÐ viljandi fráviki: enginn RestartCount (abort-not-retry er keðjustefnan), 8h limit.

**Automation-þrep eftir blast radius (§6-A.3, HALT-disciplinið lifir af automation)**:
v1 = fetch-only STRAX post-gates (raw layer append-only + idempotent, versta tilfelli
sóaðar requests); v2 = + incremental parse eftir EINA sannaða handvirka full-corpus
keyrslu (sér-DB, idempotent, DLQ soft-fail); v3 = + promote SÍÐAST eftir 2–3 sannaðar
handvirkar promote-lotur (sama bar og run_monthly push-gate) — prod-skrif fara ekki í
unattended loop fyrr.

**Scheduling-ákvarðanir (§6-A.4-Q svarað af Danna)**: Task Scheduler 01:00 **user-level**
(Q2, backup-precedent); **automated WU-re-arm í einangruðu elevated taski + dagatals-
áminning fyrstu mánuðina** (Q1, belt-and-suspenders þar til re-arm taskið er sannað);
**vélin er alltaf á** (Q3 — AC sleep/hibernate þegar óvirk per power-settings); morgun-
report **skrá-only þar til §7 delivery** er byggt (Q4 — engin email/Sentry wiring strax).

**Næst (operational gates, í röð)**: re-sweep exhaust (Session A) → init_parsed_mbl_schema
+ full-corpus parse_mbl --confirm → prime_delta_since --confirm → register_delta_task
(elevated) → fyrsta nótt + morgunreport-yfirferð. Hvert skref sér gated go.

**VIÐBÓT 2026-06-12 — öll operational gates kláruð sama dag; §6-A v1 ER LIVE**: Re-sweep
exhaust staðfest (sale 10.936 / rent 376 enriched). **Full-corpus parse lokið og verified**:
1.582 blobs (706 v1 + 876 v2) / 25.261 listings → **13.873 sale + 1.371 rent raðir á 52,9s,
0 DLQ**; nested 100% á v2-röðum; **idempotency sönnuð á alvöru gögnum** (re-run: 25.261
skipped, 0 breytt). **v1-winners 1.243 sale + 16 rent = fyrsti mældi withdrawal-forsmekkurinn**
(listing séð í scalar-seedinu 9.–10.6 en aldrei í v2) — MEÐ efri-marka caveat: talan blandar
alvöru hard-deletes, verd→0/syna→false umbreytingum post-negotiable-seed og offset-drift
pagination-missum re-sweepsins (4,5%/dag er yfir markaðstakti; rent 1,4%/dag nær raunveru) →
**tveggja-fjarvista reglan (sbr. v1 §7.2) fer í 3d-hönnunina, single-sweep diff stimplar
ALDREI withdrawn_at**. **is_foreign 1.140 (8,2% af sale)** — Spánarheimili-blokkin er
efnisleg promotion-sía í 3d, ekki edge-case. **Prime lokið**: öll fjögur since_keys sett úr
parsed maxima (sale 12.6T00:34 / rent 11.6T09:05 / negotiable bæði 10.6T18:xx); recency-
girðingin sannaði sig í leiðinni (neitaði <30 mín frá re-sweep lokum — beðið, ekki bypassað).
**register_delta_task.ps1 S4U-fix (fc206e6)**: Password-principal via -Principal promptar
aldrei → skráning féll 12.6 með misvísandi success-echo; nú S4U logon (ekkert geymt lykilorð,
dugar local-disk + outbound-HTTPS keðju) + RunLevel Limited + skilyrt echo í try/catch.
**Taskið SKRÁÐ og Ready hjá Danna — fyrsta nótt 13.6.2026 kl. 01:00**, morgunreport í
scraper_data/night_logs/.

---

## 2026-06-11 (T5) — Semantic layer fasi 1+1.5 live: könnun → hönnun → 4 MV í Supabase á einum degi

**Hvað**: Track A (T5 úr 2026-06-10 audit) keyrði allan hringinn í einni session:
empírísk könnun (strangt read-only) → view-hönnunardraft → fasi 1 creation → fasi 1.5
materialization + composition-bias fix. Nýtt **`semantic` schema live í Supabase: 5
objektar** — `_sales_base` (venjulegt view, internal grunnlag: sales_history ⋈ properties
m. götunormaliseringu, −2 nýbyggingarproxy, per-árs p01/p99 ppm2_real outlier-flaggi) +
**4 MATERIALIZED views** (`v_street_directory` 24.253 raðir, `v_matsvaedi_prices_yearly`
9.216, `v_street_prices` 3.869, `v_postnr_prices_yearly` 6.554) m. UNIQUE index á natural
key hvers. Owner-rights (EKKI security_invoker — meðvitað frávik frá Group B mynstri:
framtíðar agent-role þarf þá bara schema-USAGE + view-SELECT, ekkert á base-töflur), EKKI
PostgREST-exposed, **ENGIN GRANT enn** (agent-role er sér gated skref). Spec-draft
(un-tracked per verklagsreglu): `D:\verdmat-is\T5_SEMANTIC_VIEWS_v1_draft.md` — 12 views
hönnuð m. full-SQL + caveats sem first-class agent-knowledge deliverable; 8 eftir í fasa 2.

**Könnunar-grunnur (læstur í draft §0)**: `sales_history` er pairs-leidd arm's-length
undirmengi (173.867 raðir, 2006-05 → 2026-04-17, verð í HEILUM kr; full kaupskrá er
local-only á D:\kaupskra.csv) — 100% fastnum-match við properties. **420 onothaefur=1
lekar** (þar af 290 frá 2025–26, D3/refresh-append án síunar) → hörð `onothaefur=0` sía
harðkóðuð í hverju viewi. Gata krefst parsing úr heimilisfang (17.805 götur; 2.619 nöfn í
>1 sveitarfélagi → **lykill = gata×sveitarfélag**, 24.322 pör; tvær formatting-kynslóðir
[D3-recovery sviga-form] normaliseraðar í _sales_base). Þéttleiki 2020+ residential clean
(66,4K sölur): gata median 6 sölur (86% sala á ≥10-götum → pooled 5 ára gluggi + HAVING ≥5
gat), matsvæði median 140 (~80/175 bera ≥30/ár → árstrend), póstnr fallback-lag. Blöndun
fjölbýli/sérbýli á 677/1.455 ≥10-götum → per-tegund GROUPING SETS m. 'allt'-rollup.

**§6 ákvarðanir Danna — átta, allar afgreiddar**: (1) owner-rights grant-líkan samþykkt;
(2) PostgREST-exposure NEI í v1; (3) nýbygging = byggar ≥ söluár−2 (canonical regla,
samræmi við `is_new_build = FULLBUID=0 OR age_at_sale ≤ 2` í training-pipeline; 17,2% sala
2020+); (4) heat-þröskuldar v_hood_heat standa sem v1-heuristik MEÐ skyldu-kalibreringar-
tékki gegn ats_dashboard_monthly_heat við fasa-2 creation; (5) agent-role fær EKKI
_sales_base í v1 (aggregates eingöngu); (6) **ONOTHAEFUR-append lekinn á backlog sem
upstream root-fix** (views verja sig sjálf á meðan); (7) sveitarfélaganafna-möppun
(„Kópavogur"↔„Kópavogsbær") verður statískt lookup-view í fasa 2 per canonical-layer
reglu; (8) **composition-bias fix (domain-innsýn Danna)**: median á einingu með háa
nýbyggingahlutdeild er nýbyggingaverð, ekki verðmæti eldri stofnsins — verð-viewin þrjú
fengu `n_existing` + `median_ppm2_real/nominal_existing` + `median_kaupverd_nominal_existing`
+ `median_ppm2_real_newbuild`, öll með 5-sölu þunn-sellu NULL-vörn. **Empírían**: bítur á
blönduðum einingum (Ánanaust: 'allt' 1.066þ. vs existing 839þ. real-kr/m² = 227þ. bias;
Sólbakki Fjarðabyggð 460þ.), ~0 á rótgrónum götum (Hraunbær) — og **Sunnusmára-lærdómurinn**:
á alnýjum götum þar sem „eldri stofninn" er sjálfur nýlegar endursölur er bilið ~0
(n_existing=129 hitti spá, bil gerði það ekki) — build-freshness skipting aðgreinir
sölu-ferskleika, ekki stofn-aldur; skjalfest í caveats.

**Materialization-ákvörðun MÆLD, ekki giskað**: v1-hönnun sagði plain views; creation-
gátlistinn felldi hana — warm-latency `_sales_base` **25,5s** (properties_pkey full-index-
scan 23,1s: random heap-IO yfir 232K breiðar jsonb-raðir á litlu instance-i; fyrsta mæling
33,9s var menguð af samhliða-keyrslu — IO-samkeppni á instance-inu er sjálfstæður lærdómur,
þung queries keyrast EITT í einu). Storage-mótrökin reyndust draugatala: „424/500 MB" var
úrelt session-minni; **mælt 1.003 MB / 8 GB Pro-budget (12,5%)**. → 4 output-MV (WITH NO
DATA í migration = hreint DDL; fyrsta REFRESH sér operational skref), latency eftir:
**0,145 ms** (indexed götu-lookup) / **116 ms** (full-scan aggregate). Row counts óbreytt
gegnum materialization. **REFRESH-ábyrgð (draft §4.1)**: handvirkt gated skref eftir HVERJA
sales_history-uppfærslu þar til run_monthly post-push hook kemur; copy-paste blokk í §4.1;
eitt í einu, ekki samhliða.

**Migrations + reconciliation-mynstur**: `20260611104645_t5_semantic_phase1` (commit
0868c42) + `20260611155653_t5_semantic_phase1_5` (commit c29b4b6). **MCP apply_migration
skráir version sjálft í supabase_migrations.schema_migrations** — ekkert CLI `migration
repair` þarf (ólíkt psycopg2-leiðinni); reconciliation = disk-skrá nefnd nákvæmlega eftir
MCP-version. Einfaldara mynstur en 2026-05/06 færslurnar lýsa; gildir framvegis fyrir
MCP-applied migrations.

**Scraper-schema exposure ráðgáta**: REST-próf (Accept-Profile probe, PGRST106) sýndi
exposed schemas = public + graphql_public EINGÖNGU — scraper-exposure sem var gerð manually
~1. júní er horfin. MEÐVITAÐ ekki endurvakin þar til REST-consumer er til; semantic fylgir
sömu reglu. Aukafinding: authenticator ber statement_timeout=8s — relevant fyrir hvaða
framtíðar REST-exposure sem er og fyrir agent-role timeout-hönnun.

**Næst (T5 track)**: Fasi 2 creation — 8 views (street_activity, sveitarfelag_market,
matsvaedi_trend_quarterly, hood_heat, newbuild_share, model_vs_sold_by_hood,
summerhouse_market, price_distribution_by_hood) + v_sveitarfelag_lookup; gated á tvo §4
forleiki: predictions-eininga-tékk (liður 3, fyrir model_vs_sold) + heat-kalibrering
(liður 5). Síðan GRANT-skref samhliða agent-role hönnun (v0 expert agent).

**VIÐBÓT 2026-06-12 — FASI 2 LOKAÐ morguninn eftir; semantic layer v1
FULLSKIPAÐ (13 MV + _sales_base view)**: migration `20260612091832_t5_semantic_phase2`
(commit 73c1adb) — 9 ný MV þ.m.t. `v_sveitarfelag_lookup` (64 raðir, 20 íhaldssamir
aliasar: aðeins suffix-afleiðingar og „Sveitarfélagið X"-strip, engar bæjarnafna-
giskanir). **Fortékkin tvö græn fyrir apply**: (1) predictions-eininga-ratio
**1,0042** (IQR 0,944–1,082, n=9.500) → v_model_vs_sold_by_hood skapað; (2)
heat-kalibrering **hot 21 / neutral 65 / cold 18 / insufficient 75** á 179
matsvæðum (hot-median +8,1%, cold −5,1%) → ±5%/±2%+±15% þröskuldar standa
óbreyttir (íhaldssamara en ats-þriðjungar; ats mælir annað signal). Row counts
í spá-bili (street_activity 39.323 stærst; fasa-2 summa ~52K yfir grófu §5
~30–40K mati — skýrt frávik, activity spannar öll 21 árin); latency 3,5 ms.
**Summerhouse-trim valið skjalfest**: ppm2 í v_summerhouse_market ótrimmaður
meðvitað — _sales_base outlier-flaggið nær aðeins yfir íbúðarsölur, median er
robust og kaupverð er leading stat á sumarhús. REFRESH-blokk draft §4.1 nær nú
yfir öll 13 MV.

---

## 2026-06-11 — Step 3b operational closure + enriched re-sweep prioritization

**Hvað**: Öll fjögur mbl seed-modes keyrðu til enda — Step 3b er OPERATIONALLY CLOSED.
Enriched re-sweep af scalar-generation publishable corpus ákveðinn og settur í gang STRAX
(ekki á post-P3 backlog). Journal-færslan hér læsir tölurnar, tvö empírísk findings og
verklagsbreytingar.

**Step 3b closure-tölur (sannreyndar gegn mbl_fetch_state.json + raw_mbl.db ro)**:
- sale publishable **10.899** listings (exhausted við offset 10.912, frozen_max_id 1.688.820,
  682 síður), rent publishable **377** (24 síður), sale negotiable **1.694** (ceiling
  1.689.601, 106 síður), rent negotiable **979** (ceiling 218.255, 62 síður) =
  **13.949 listings í 874 list-page blobs**.
- **Self-establish ceilings sönnuðust empírískt**: negotiable modes frusu EIGIN max_id YFIR
  main-seed ceilingunum (sale 1.689.601 > 1.688.820; rent 218.255 > 218.157) — inheritance
  hefði misst head-of-id negotiable listings varanlega, eins og P3 rationale spáði.

**EMPIRICAL FINDING læst — publishable-túlkun seed-pagination staðfest**: sale seed tæmdist
við offset 10.912, hvergi nærri raw aggregate 13.792. Mismunurinn er (a) draft-filterinn
(verd>0/fermetrar>0) eins og hannað og (b) **churn-effektið** — mbl hard-deletar withdrawn
listings undir frozen window á multi-nætur seed, svo ~640 raðir hurfu úr glugganum meðan
crawl-ið stóð. Hvort tveggja vænt; engin merki um pagination-galla.

**GENERATION SPLIT finding**: publishable corpus (682 sale + 24 rent síður) er **scalar-only**
— Night 2/3 processinn keyrði pre-amendment kóða í minni (in-flight prósess les ekki nýjan
kóða af diski). Negotiable corpus (168 síður) er **100% v2_enriched**. `fields=v2`
URL-markerinn í raw_fetches ledger aðgreinir kynslóðirnar nákvæmlega (sannreynt:
682/0 v2, 106/106 v2, 62/62 v2). **§3c parser SKAL þola báðar kynslóðir** (nested-missing
OG nested-present blobs).

**DECISION — enriched re-sweep forgangsraðað STRAX**: mbl er closed history (syna=false=0,
hard-deletes); myndir/agency/nested gögn listings sem dragast til baka á biðtímanum eru
ÓENDURHEIMTANLEG — re-sweep fer því fram fyrir P3-backlog-hugsunina. Mechanism: existing
`--force-restart` + nýja history-archive netið (b57b7c0) varðveitir upprunalegu seed-gluggana
í `<key>_history`. Keyrsluplan: rent (~24 síður) + sale 400 síður í dag/nótt, `--mode resume`
á morgun þar til exhaust. **Footgun skjalfest**: `--force-restart` má BARA nota á FYRSTU
keyrslu hvors mode í re-sweepinu — á resume-keyrslum myndi hann núllstilla gluggann aftur
og henda progress.

**Commits**: 862f86a (v2_enriched field selection — allir scalars nema generated_fts, öll
10 image-variants, nested agency/attachments/openhouse/postal_code/promo; deliberate
exclusions: generated_fts, favorite [user-scoped], fs_count/rt_count [volatile counters sem
brytu §2.1.1 content-hash dedup]) + b57b7c0 (force-restart history-archive). Testar 25 → 30.

**NORM CHANGE — commit attribution**: Co-Authored-By trailer endurspeglar héðan í frá
RAUNVERULEGT módel sessionar (var harðkóðað "Claude Opus 4.8" í template; röng attribution
leiðrétt í "Claude Fable 5" frá og með 862f86a).

**Operational verklag fest — gated orchestrator-mynstur**: keðjuskript fyrir multi-mode
crawl-raðir keyra sem gated chain (eitt mode í einu, vænt-tölur sannreyndar milli skrefa),
abort-not-retry á óvæntri stöðu, PID-wait á undanfara í stað polling-lykkju. Endurnýtanlegt
fyrir §6 nightly delta orchestration.

**Næst**: re-sweep lýkur (resume á morgun) → Step 3c parse_mbl.py — skema læst: tvær
source-flavored töflur, báðar blob-kynslóðir, sentinel-reglur (fastano=0→NULL o.fl.),
foreign-listing flag (Spánarheimili), Hashie::Mash corruption-strip.

---

## 2026-06-10 — Strategic audit + revised priority sequencing + agent architecture sketch

**Hvað**: External audit by independent Claude session (Fable 5) surveyed all D: drive
data assets, repo state, spec drafts, and live Supabase. Audit surfaced material context
beyond what scraper-substream handoff documents captured. Findings + strategic
re-sequencing accepted as new working baseline.

**Data asset inventory (audit-discovered, beyond scraper handoffs)**:
- **Image archive at D:\Gagnapakkar\** — 196.5 GB across 5 packages, 921,273 images,
  38,152 fastnum-organized folders, image_index.db with 2.6M rows. NEAR-UNUSED until now.
  Critical for Step 3e image_mirror: must bootstrap from this archive before fetching
  anything new. Cross-property-references issue noted (naive layout misses ~20%, use
  image_index.db).
- **LLM-extraction batch_results** — 40,000+ listings already processed (condition, floor
  finish, kitchen, garage, structured features). Cache-efficient pipeline proven. NOT yet
  integrated into iter4 training set — likely largest single MAPE improvement available
  (einbýli currently at 16.3% MAPE; condition explains substantial residual variance for
  that segment).
- **Leiguskra-legacy scrape** — gleymd eign: ~928 current + ~3,000 historical rent
  snapshots with fastnum, price, size, first-seen/last-seen dates, images. Should be
  folded into scraper.listings_canonical as source='leiguskra_legacy'. Combined with
  mbl-rent + myigloo + visir-rent gives thousands of rent price points with time
  dimension — primary input for iter_rent_v1.
- **last_listing_text.csv** — 145 MB ad-text corpus, source for LLM extraction full-scale.
- **rebuild_properties_v2.py** — 309 lines of multi-source stitch logic, currently
  un-tracked; should be promoted to tracked as template for future D4/D5 work.

**Top opportunities ranked (T1-T6)**:
- **T1 — Asking-vs-sold spread analysis**: highest-value single analysis. Only Danni
  has both sides on Iceland scale (asking from scraper canonical, sold from kaupskrá 227K
  transactions, joined on fastnum). One SQL view post-mbl-promotion. Mælaborð front-page
  material; strongest sales argument for realtor subscription. No new data needed.
- **T2 — LLM extraction full-scale → iter5**: run LLM extraction over full
  last_listing_text corpus, fold condition/finish features into iter5 training. Likely
  largest MAPE improvement available.
- **T3 — Leiguskra-legacy + multi-source rent → iter_rent_v1**: thousands of rent price
  points with time dimension once leiguskra-legacy is canonicalized. Sufficient for first
  asking-rent model.
- **T4 — Image mirror bootstrap from D:\Gagnapakkar**: save weeks of fetch time + GB of
  bandwidth by reading existing 196 GB archive first, diff-fetching only what's missing.
  Cross-property-references gotcha already known.
- **T5 — Street/hverfi aggregates (immediate)**: kaupskrá + properties already in
  Supabase. Street-level / hverfi-level price-per-m², turnover rate, price trend views
  are one SQL build. Available TODAY without new data. Doubles as semantic-layer
  foundation for expert agent.
- **T6 — Fasteignamat-deviation analysis**: HMS-refresh gives official assessments;
  iter4 gives market estimates. Mapping where official assessment diverges most from
  market value (by matsvæði, age, type) is bank-product + media material.

**Expert agent architecture (3 layers + v0/v1/v2 roadmap)**:
Not a custom-trained model — harness around Claude. Three layers:
- **Layer 1 — Tools (SQL + data)**: read-only SQL role to Supabase + DuckDB over D:
  pickles. Critical: semantic layer of 10-15 well-documented analytical views
  (v_street_prices, v_asking_vs_sold, v_market_heat_by_hood, v_price_history…) so agent
  writes reliable queries against named views, not raw-table joins. T1 and T5 are the
  first views.
- **Layer 2 — Knowledge package**: SKILL.md / system prompt with data dictionary
  (matsvæði, byggingarstig, ónothæfur samningur definitions), calculation rules (price/m²
  conventions, multi-unit handling, Tilboð sentinel), gotchas (mbl aggregate-vs-publishable,
  fastnum 1:N on commercial), and 20-30 exemplar queries.
- **Layer 3 — Output**: charts, reports, article drafts. Precompute chain + dashboards
  prove output formats already exist.
Roadmap: v0 weekend project in Claude Code/Desktop (skill + read-only SQL, validates
semantic layer cheaply) → v1 internal tool + bank product with 50-100 question eval bank
for reliability measurement → v2 "Spurðu sérfræðinginn" inside verdmat.is behind Pro
subscription via Claude Agent SDK with read-only role + rate limits + cost cap +
mandatory citation guardrails.

**Revised priority sequencing (next 2-4 weeks)**:
1. Finish mbl seed-sale (Night 2 in-flight + Night 3 finish ~45 min)
2. Step 3b P3 supplementary negotiable crawls (~5.7h) — captures ~980 rent + ~1,698 sale
   Tilboð listings
3. Step 3c parse_mbl.py + Step 3d promote_mbl.py → canonical jumps 1,266 → ~16K rows
4. **Nightly delta orchestration immediately after Step 3d** — urgency-locked (mbl is
   closed history; every day without delta = permanent data loss)
5. **Parallel track A — T5 street/hverfi views**: can start NOW (only needs kaupskrá +
   properties), no in-flight scraper dependency, foundation for v0 expert agent
6. **Parallel track B — Step 3e image_mirror with Gagnapakkar bootstrap**: read existing
   196 GB first, diff-fetch only missing. Starts after Step 3d
7. T1 asking-vs-sold view (after Step 3d puts mbl in canonical)
8. v0 expert agent on T1/T5 semantic layer
9. T2 LLM extraction full-scale → iter5 (independent track)
10. iter_rent_v1 with leiguskra-legacy + multi-source rent (T3, after canonical mature)
11. visir corpus production refresh (timed-batch, background)

**Locked policy: delta-cadence urgency**: mbl syna=false = 0 (hard-delete). Every day
without nightly delta-sale + delta-rent = permanent data loss (observed +19 rent rows in
hours during diagnostic). Post-Step-3d, §6 delta orchestration jumps AHEAD of most other
work, even ahead of parser if forced to choose. Raw blobs wait patiently; the market does
not. Spec amendment to §6 follows this commit (un-tracked draft only).

**Locked policy: image-mirror Gagnapakkar bootstrap**: Step 3e image_mirror must read
D:\Gagnapakkar\image_index.db first to enumerate already-archived images; fetch only
missing diff. Saves weeks + GB of bandwidth. NOT a re-fetch from scratch. Cross-property-
references gotcha known (use image_index.db, not naive folder layout).

**Step 3b P3 closed (commit 56b1a2e)**: fetch_mbl.py negotiable supplementary modes
implemented with self-establish max_id (NOT inheritance). Rationale captured in commit
message: head-of-id newest negotiable listings would be permanently lost if negotiable
inherited main seed's ceiling. Cross-mode dedup handled by §4 promotion-tier R1-R3.
25/25 tests pass. Scraper chain now 20 commits on origin/main.

**Næst (immediate)**: Night 3 sale seed finish (~45 min, Session A) → P3 supplementary
crawls (~5.7h, Session A) → Step 3c parser design + impl → Step 3d promotion. Parallel
track A (T5 street views) can start in a fresh Claude Code session anytime; no in-flight
scraper dependency.

**LEIÐRÉTT 2026-06-12 (endurmæling):** „196,5 GB / 921K images" talan að ofan var
snapshot frá 2026-05-08, FYRIR Stage B-myndasóknina. Safnið mælist nú **548,5 GiB /
2.648.381 skrár / 55.637 distinct fastnum yfir 7 rætur** (robocopy-mæling per rót,
staðfest gegn image_index.db — diskur og index stemma). image_index.db (790 MB, 2,63M
raðir, PK fastnum+image_nr, 99,998% downloaded=1) er master-indexið; local_path vísar
INN í upprunalegu pakkamöppurnar — skrár voru indexaðar á sínum stað, engin tvítekning
milli Gagnapakkar\images\ og pakkanna. Skráarnöfn eru sequential <fastnum>\<n>.jpg,
EKKI URL-basename — URL→skrá vörpun virkar EINGÖNGU gegnum image_index.db.
Leiguskra-myndir (1,7 GiB, 1.145 möppur) eru óindexaðar enn. 350 GB laus á D: —
diskpláss er héðan í frá vöktuð auðlind (mirror-sókn nýju uppsprettanna bætir 50–150 GB
við). Opin 3e-hönnunaratriði (ÁKVEÐAST við Step 3e hönnun, ekki nú): (a) framlengja
image_index.db vs ný mirror-DB — fastnum-þekja mbl-corpussins mælist fyrst; (b)
backup-staða 548 GiB safns sem er UTAN R2-backupsins.

---

## 2026-06-09 — Spec correction: §5 #5 + §2.4-C image archival policy

**Hvað**: Spec drift caught during Step 3b P1 review. §5 #5 read "URL-only v1, escalate
if >5% 404" — this contradicts Danni's locked intent of full image archival to D: drive
from v1. Drift originated from skeleton-era text not updated post-decision.

**Locked policy (re-confirmed)**: all source CDN images mirrored locally to D: drive from
v1. Storage at `D:\verdmat-is\image_mirror\<source>\<source_listing_id>\<index>.<ext>`.
Tracking via `image_mirror.db` SQLite.

**Rationale**: withdrawn listings cause source CDN URLs to 404 permanently. Valuation
model + bank product + future historical analytics need visual context for sold
properties. D: drive storage is essentially free (precedent: existing 352 GB image mirror
from Galdrabúðin/legacy work). Cloud storage (Cloudflare R2 et al.) carries 100s-of-GB
recurring cost — deferred until economics warrant. Danni's desktop can serve images via
Cloudflare Tunnel in v1 stretch if frontend wants mirror access.

**Architecture sketch (Step 3e/4 design input)**:
- Storage layout LOCKED: per-listing folder (`image_mirror/<source>/<source_listing_id>/<index>.<ext>`).
  Sha256 content-addressed deferred to v2 if storage pressure shows; `image_mirror.db`
  carries sha256 column from v1 so migration path is mechanical.
- `image_mirror.db` tracking schema (per-image row): source, source_listing_id, image_index,
  source_url, local_path (relative under image_mirror/), fetched_at, byte_size,
  content_type, sha256, fetch_status (success/404/timeout/blocked)
- Fetcher reads canonical `photos_json` URLs across all sources (cross-source single pipeline)
- Pacing: 5-10 req/sec (image CDNs designed for browser hot-load — much more permissive
  than listing APIs which are minute-paced)
- Standard Chrome UA, no identifier
- Kill-switch on 403/429/persistent timeout
- Parallel 3-5 concurrent connections OK (browser-equivalent posture)
- Resume-safe: skip rows where local_path exists + fetched_at is recent
- Serving in v1 minimum: dormant archive (frontend keeps source URLs, falls back on 404).
  Cloudflare Tunnel stretch: serve mirror via desktop, frontend prefers mirror with source
  fallback.

**Sequencing**: image archival is cross-source sub-stream — works on canonical `photos_json`
URLs regardless of source. Can start anytime canonical has rows (already 1,266 rows from
myigloo + visir). Recommended order: complete Step 3 mbl substream first (3b P2 listing
fetcher → 3c parser → 3d promotion), then Step 3e/4 image archival processing all 3
sources' canonical photos_json. Storage estimate ~50-150 GB full mirror.

**Næst (when Step 3e/4 actually builds)**: `init_image_mirror_schema.py` (image_mirror.db
bootstrap) + `fetch_images.py` (cross-source byte archival with politeness pacing) +
reconciliation pass against canonical photos_json. Optional v1 stretch: Cloudflare Tunnel
setup for frontend mirror access.

---

## 2026-06-09 — Step 3a closed: mbl Hasura GraphQL characterization

**Hvað**: Step 3a (mbl probe) lokuð — Phases 1b/1c/1d/1e/1f all empirically resolved.
`probe_mbl.py` un-tracked (3 phases: `--confirm`, `--tail`, `--p1f`). ~50 GraphQL requests
across the phases, **all HTTP 200, zero anomalies**. Journal-only milestone — NO code commits.

**1. Architecture finding (overturns §1.1 mbl framing)**:
- Spec held mbl was a React SPA with REST `/fasteignir/api/*` (robots-disallowed) needing Playwright.
- Empirical: the data layer is a **Hasura GraphQL** endpoint at `g.mbl.is/v1/graphql` (a
  different subdomain — the robots-disallow was on `www.mbl.is`, not `g.mbl.is`).
- `g.mbl.is/robots.txt` → **404** (no restriction).
- **No auth, no TLS impersonation**, plain `requests` + standard Chrome UA → 200 + JSON.
- Introspection **enabled** — full schema captured (`fs_fasteign` 50 scalar + 7 nested;
  `rentals_property` 21 scalar + 5 nested).
- Difficulty-rank update: mbl is now the **EASIEST transport** (cleaner than visir's SSR HTML).

**2. §0.5 amendment (mechanism only)**:
- Original choice (B): "headless rendering with kill-switch, Playwright Python framework".
- Amended: **direct GraphQL via stdlib `requests`; Playwright fallback only if mbl later gates
  the endpoint.**
- Posture spirit UNCHANGED + binding: conservative rate, standard Chrome UA without identifier,
  no active deception (no TLS impersonation, no proxy rotation, no CAPTCHA bypass), kill-switch
  on 3+ HTTP 400 OR 403/429/CAPTCHA, alert Danni, try-and-see, halt-and-drop on block, no Árvakur
  (path C) escalation. Spec patch landed in SCRAPER_SPEC_v2_draft.md (un-tracked) §0.5 + §1.1.

**3. §2.1.1 mbl rule LOCKED — trivial**:
- Empirical: t=0 vs t=+60s, same id, both `raw_hash` AND sorted-keys `hash` identical (sale + rent).
- Rule: `content_hash = sha256(json.dumps(parsed, sort_keys=True, separators=(',',':')))`.
- Zero path-nulling (unlike myigloo `verification.as_of`, unlike visir Skoðendur counter / ad-blocks).
  Hasura returns deterministic bodies — no per-request server stamps. Cleanest §2.1.1 of all 3 sources.
- Caveat: a +1h longer-gap confirm was NOT done; revisit if Step 3b raw layer shows linear blob
  growth without real changes. `blob_gz` verbatim per §2.1.

**4. Universe + distribution (exact, uncapped aggregate queries)**:
- Sale **13,772** · Rent **1,349**.
- Per-`teg_eign` sale: fjolb 7266, atv 2450, einb 1395, radpar 1003, jord 778, sumarhus 433,
  haedir 334, hesthus 72, annad 38 (sums 13,769; ~3 with null/other teg_eign).
- mbl is the **LARGEST source by row count** (~15k+ active > visir + myigloo combined).
- Commercial (atv 2,450) is **first-class** on mbl (unlike visir's non-first-class commercial);
  plots (jord 778) substantial. §7.1 monitoring floors lockable from these counts.
- §1.2 estimates ("3-5k est" sale, "few-hundred est" rent) were ~3× low.

**5. ⚠ 16-row hard cap (Hasura anonymous role)**:
- `limit:100` → 16 rows; `limit:1000` → 16 rows. Aggregate counts are NOT capped (server-computed).
- Step 3b enumeration constraint: **offset-pagination at 16/page → ~946 pages** for the full universe.
- §0.5 cap (<1000/24h) + minutes-between → **multi-night seed crawl** (2-3 nights @ 300-500/night).
  Steady-state delta-refresh via `where:{br_dags:{_gt:<last_seen>}}`. Mitigation locked in Step 3b design.

**6. ⚠ fastano heterogeneity (Step 3d concern, flagged not solved)**:
- Typed `Int` (Hasura schema); observed range **6-9 digits** across teg_eign categories.
- Standard HMS fastnum is 7 digits → some values likely landeignarnúmer (for jord plots) or other ids.
- §2.5 promotion must do **format-aware FK validation** against `properties.fastnum`.
- Coverage feasibility high — fastano present on **ALL** teg_eign categories sampled (better than
  visir where commercial fastnum was sketchy).

**7. Draft-listing production filter (Step 3b concern)**:
- `sent_dags desc` sampling surfaced draft/placeholder rows (verd=0, fermetrar=0).
- Production enumeration filter: `where:{syna:{_eq:true}, verd:{_gt:0}, fermetrar:{_gt:0}}`.

**8. ⚠ rent type_id (1-11) — empirically OPAQUE (not locked)**:
- Phase 1f sampled up to 5 listings per type_id (1 aliased query). Titles are bare addresses,
  sizes overlap heavily across ids → **no clean keyword/size signal**, and the schema has **no
  `rentals_type` lookup table** (only rentals_property/_photo/_postal_code roots).
- Weak grouping only: type_id 6/9/10 look commercial (large m², rooms 0/many, commercial-area
  addresses, all longtime); 2/3/11 look residential (small-medium, rooms 1-5). LOW confidence.
- **Ruling: do NOT decompose category from type_id.** Mirror the visir lesson — derive category at
  Step 3d from **size/keyword heuristics** (rent default → residential unless commercial signals),
  retain `type_id` as a raw signal (tegund_raw-equivalent) for future refinement. type_id mapping
  can be revisited if the SPA bundle exposes a frontend lookup.

**9. hesthus → TAXONOMY ruling LOCKED**:
- hesthús (horse stable) is a rural/agricultural structure (v1 TAXONOMY §1.4 grouped it under
  landbúnaður EXCLUDE).
- Ruling: **category=plot, sub_type=agricultural** (§5 `agricultural` = "landbúnaðarjörð, býli"
  absorbs farm/rural buildings + land). MEDIUM confidence; flag for v2 refinement (alternative
  would be commercial/mixed_use_other, but §5 agricultural is the cleaner fit for an ag structure).

**10. teg_eign decomposition mapping for Step 3d (sale)**:
- fjolb → residential/apartment · haedir → residential/apartment (floor unit)
- radpar → residential/townhouse · einb → residential/house · sumarhus → residential/summerhouse
- atv → commercial (sub_type via keyword classification post-parse, like visir)
- jord → plot (sub_type via TAXONOMY §5 keyword) · hesthus → plot/agricultural (per #9)
- annad → other

**11. Source-priority retune candidate (flag-only, NOT relitigated)**:
- Locked starting point per §2.3-D: visir(1) > mbl(2) > myigloo(3).
- Empirical case for mbl earning priority 1 over visir post-Step-3b: typed GraphQL > scraped SSR
  HTML (cleaner parse); fastano on ALL rows (§2.5 Tier-1 universal) vs visir sometimes-only; no
  "Tilboð"/price=1 sentinel quirks (typed numeric `verd`); larger universe + first-class commercial.
- Defer retune to the build-phase overlap sample per §2.3-D's locked process. No spec change now.

**12. Two root types** (`fs_fasteign` sale vs `rentals_property` rent) — different field shapes →
two parser paths at Step 3c (or one with per-type mapping). No detail endpoint needed: all scalar
fields are list-queryable (the 27/3 "detail-only" fields are just unrequested scalars).

**Næst**: Step 3b — `raw_mbl.db` schema (§2.1) + `canonicalize_mbl.py` (trivial sorted-keys rule)
+ `fetch_mbl.py` (16-cap offset-pagination, multi-night seed plan, day-1 kill-switch incl. HTTP 400,
draft-row filter). `probe_mbl.py` stays un-tracked.

---

## 2026-06-08 — Step 2d closed: promote_visir.py + §4 cross-source dedup proving ground

**Hvað**: Step 2d lokuð. `promote_visir.py` (589 línur) + `promote_visir_test.py` (230
línur) committed. 388 visir rows promoted to `scraper.listings_canonical` (386 insert_new
+ 2 visir_wins folded against existing myigloo canonical rows), 11 junk skipped, 0 failed.
**Canonical layer is now genuinely multi-source: 1,266 rows (859 myigloo + 407 visir)**,
spanning residential sale+rent, commercial sale+rent, and plots, with 2 verified
cross-source folds.

**Decomposition mapping (visir tegund_raw → TAXONOMY_v2 category+sub_type)**:

8 tegund_raw values mapped cleanly:
- `fjölbýlishús` / `íbúðir` / `íbúð` / `hæð` → residential/apartment
- `sérbýli` / `einbýli` / `einbýlishús` → residential/house
- `raðhús` / `parhús` → residential/townhouse
- `sumarhús` / `sumarbústaður` → residential/summerhouse
- `atvinnuhúsnæði` → commercial/{office|retail|industrial|hospitality|mixed_use_other},
  resolved via secondary KEYWORD parse against title+lysing (skrifstofa→office,
  verslun→retail, iðnaðar/vörugeymsla/lager/verkstæði→industrial,
  hótel/gistiheimili→hospitality, else mixed_use_other)
- `lóð` / `jörð` → plot/{residential_plot|commercial_plot|agricultural_plot|other_plot},
  resolved via secondary keyword parse

Tenure from `parsed_visir.tenure_signal` directly per Step 2c Decision 3 (detail-HTML
markers authoritative). lease_term_class set to 'unspecified' for all visir rent
(no contract_min_months in parsed_visir v1).

**§4 cross-source dedup — three universal reject rules**:

The §4 machinery fires against the existing 861 myigloo canonical rows per Step 2's
§6 dedup proving ground mandate. Empirical iteration on real corpus exposed 16 candidate
matches, of which 14 were false positives. Three universal reject rules now lock the
machinery to genuine cross-source overlaps only.

**Rule 1 — Fastnum-disagreement reject (universal)**: In any tier candidate evaluation,
if BOTH visir_row AND candidate_row have non-NULL fastnum AND fastnums differ → reject.
Mathematical certainty: different HMS-registered fastnums = different properties.
Killed 2 tier-2 false positives (visir 1054922 fn=2121211 ↔ myigloo 3669 fn=2313904 +
visir 1046418 fn=2271716 ↔ myigloo 11524 fn=2012663).

**Rule 2 — Size-disagreement reject (universal)**: In any tier candidate evaluation,
if BOTH visir_row AND candidate_row have non-NULL size_sqm AND
`|size_a - size_b| / max(size_a, size_b) > 0.10` → reject. Catches multi-unit-same-
fastnum case (commercial building registered as one HMS fastnum, multiple units inside).
Killed 2 of 3 multi-unit office matches at fn=2252816 (visir 1056507 + 551503 had
sizes ≠ myigloo 822's 86.9 m²).

**Rule 3 — Commercial corroboration (category-targeted, ALL tiers)**: For commercial
category matches at ANY tier (1, 2, or 3), require at least one informative corroborator:
EITHER size agreement (both >0, within 10%) OR price agreement (both non-sentinel, within 5%).
If neither corroborator available → reject. Empirical reality: commercial fastnum is 1:N
over building units; sentinel price=1 (Tilboð) makes Tier-2/3 price filters degenerate;
without size or non-sentinel price match, fastnum alone is insufficient confidence.
Killed the surviving multi-unit case (visir 1047898 size=0 + myigloo 822 size=86.9,
both prices=1 Tilboð sentinel → no corroborator → reject).

**Architect-spec-vs-empirical-test correction (transparency)**:
Original architect spec said Rule 3 applies to "Tier-1 only". T22 test empirically
exposed that the same uncorroborated multi-unit-commercial match also surfaces via Tier-2
(addr match) because price=1 sentinel on both sides trivially satisfies the Tier-2 price
filter. CC correctly generalized Rule 3 to ALL tiers for commercial — better matches the
underlying reality that commercial-fastnum-is-1:N is a category-level constraint, not a
tier-level one. Generalization is safer (prefers false negatives over false positives,
consistent with §4 philosophy).

**Empirical false-positive reduction narrative**:
- Initial dedup machinery: 16 candidate matches
- After Rule 1 (fastnum-disagreement): 14 (2 tier-2 different-fastnum killed)
- After Rule 2 (size-disagreement): 3 (multi-unit-different-size + degenerate tier-3 killed)
- After Rule 3 (commercial-corroboration, all tiers): 2 (uncorroborated multi-unit killed)
- Final genuine matches: 2 residential apartments, both with identical
  fastnum + size + price + tenure — exactly the cross-source overlap §4 was designed
  to detect.

**Persistent learning extending Step 2c**: Architectural specs at design-time can miss
edge cases that empirical tests at integration-time expose. §4 dedup principles should
apply at category granularity (commercial-1:N reality), not tier granularity. Apply same
discipline to Step 3 mbl + future sources: write tests that encode the INTENT
("uncorroborated commercial match must not fold"), let the test failures reveal where
the rule needs to generalize.

**v1 limitation (deferred to v2)**: Within-run visir↔visir dedup is deferred — promote
loop matches only against the STATIC preloaded canonical snapshot (myigloo + prior runs),
not against same-run visir inserts. Eliminates a placeholder-uuid write bug and avoids
Tier-2 false-positive risk of folding two distinct units in one building during the same
batch. Production impact: small (only matters if visir lists same property twice
simultaneously, rare). Future v2 could implement within-run dedup with proper canonical_id
generation if needed.

**Verification (live Supabase state)**:
- by source: myigloo 859 (861 − 2 folded), visir 407 (19 smoke + 386 insert + 2 won)
- visir cat×tenure: residential/sale 193, commercial/rent 169, commercial/sale 29,
  residential/rent 12, plot/sale 4
- visir fastnum resolution: source_supplied 336, address_match 33, geo_match 11,
  unresolved 27 = 93% resolved
- folded rows: 2, both correct (visir 1050593 ← myigloo 23863; visir 1050668 ← myigloo 23937)
- 0 ck_price_pos / ck_fastnum_resolution violations
- Supabase pooler quirk handled per memory entry 1 (SET TRANSACTION READ WRITE as first
  statement, mogrify INSERT single round-trip)

**File metrics**: promote_visir.py 589 lines, promote_visir_test.py 230 lines, 28/28 tests
pass (decomposition T1-T4, price T5-T9, fastnum T10-T11, §4 dedup T12-T18, §4 reject rules
T19-T24).

**Næst**: Step 2 substream (visir) complete; scraper substream chain at 15 commits on
origin/main. Production-grade visir corpus refresh deferred to timed-batch session when
needed (per Step 2b P3 IP-throttle finding). Step 3 mbl next major milestone — apply same
defensive scraper patterns + universal §4 dedup rules from the start.

---

## 2026-06-04 — Step 2b P3: visir IP throttle finding + fetcher defensive patches

**Bakgrunnur**: Full visir crawl initiation surfaced production-scale rate limiting
that was invisible at probe scale. Two attempts, two empirical corrections.

**Empirical timeline (honest log of false-positive correction)**:

- **Crawl attempt #1 (09:26-09:55)**: Naive full crawl. Phase A index sweep reached
  ~170 requests at 8 min; from request 170 onward visir returned HTTP 400 on every
  detail fetch. 622 wasted requests before manual halt. Spec §1.1 "no WAF" assumption
  invalidated for sustained scale.

- **Patch hypothesis #1 (session-based throttle)**: Fresh `requests.Session()` got HTTP
  200 on same IDs ~20 min after halt → seemed session-bound. Patches: (1) 400-aware
  kill-switch [Patch 1], (2) periodic session re-prime every 80 requests [Patch 2].

- **Validation crawl (10:23-10:35)**: 440 requests with 5 re-primes → 0×400, exit 0.
  Conclusion: "session-based throttle, re-prime works". **THIS WAS WRONG**.

- **Full crawl attempt #2 (10:41-10:44)**: 76 requests on top of validation's 440 →
  HTTP 400 at cumulative request ~516 across multi-session sequence → kill-switch
  tripped at 3×400, exit 2. Wasted only 3 requests this time (Patch 1 essential ✓).

- **Corrected hypothesis (IP-based throttle, validated)**: Validation didn't pass
  *because* re-prime worked — it passed *because* total IP-cumulative was under ~500.
  The 47-min cooldown between halt and validation cleared the IP counter. When full
  crawl piled on top of validation's 440, cumulative breached the IP window. Throttle
  is IP-level cumulative ~500 requests per rolling ~30-60 min window. Session re-prime
  is harmless cookie hygiene but does NOT reset an IP counter.

**Patches kept (both genuinely valuable)**:

- **Patch 1 (400-aware kill-switch)**: Essential safety net. Halts on 3+ consecutive
  HTTP 400 responses, resets on 200. Caught both 622-request blast (attempt #1) and
  3-request blast (attempt #2). T11 locks behavior on consecutive 400s + recorded
  raw_fetches rows.

- **Patch 2 (unified re-prime every 80 across both phases)**: Cookie hygiene + handles
  potential session-level sub-limits if they exist below the IP threshold. Doesn't
  defeat IP throttle but no cost to keep. Counter spans both Phase A (index sweep) and
  Phase B (detail walk) via class-level `requests_since_prime`. T12 verifies firing
  across phases; T13 verifies counter reset on `prime()`.

- **Tests**: 13/13 pass (T1-T10 unchanged + T11 kill-switch-on-400 + T12 periodic
  re-prime + T13 prime resets counter).

**Spec corrections (un-tracked SCRAPER_SPEC_v2_draft.md, this commit)**:
- §1.1 visir entry: throttle finding added (IP-cumulative ~500 req per ~30-60 min window)
- §0.5 kill-switch: HTTP 400 (3+ consecutive) added to monitored signals

**Corpus state**: 418 valid detail blobs banked (validation crawl + smoke residue).
Reparsed at visir_parse_v1, 0 failures. Distribution: **235 sale / 183 rent** by
tenure_signal, but rent is dominated by **commercial** — 198 atvinnuhúsnæði + 172
"Tilboð" price-on-request; **only 14 residential-rent** (the myigloo-overlap dedup
target). Also 158 fjölbýlishús, 18 raðhús, 18 einbýlishús, 8 lóð, 5 sumarhús. Adequate
for Step 2d proving ground (commercial classification + Tilboð at scale, residential-sale,
plots, summerhouse all well-sampled); residential-rent dedup-vs-myigloo overlap is THIN
(14) — but visir residential-rent is genuinely scarce (mostly commercial), not a crawl
artifact, so a bigger crawl would not help much. Production full crawl deferred to a
timed-batch session (45-60 min IP-window pauses between ≤300-request batches).

**Persistent learning extending Step 2a + 2c**:
- Probe-scale empirical evidence does NOT extrapolate to production-scale (50 req
  probe found no WAF; 500 req production found IP throttle).
- Validation methodology: cross-attempt cumulative IP state must be tracked, not just
  per-attempt state — false-positive risk is real when window-state matters. Apply to
  Step 3 mbl probe + full crawl: build IP-cumulative tracking into the validation gate.

**Næst**: Step 2d build against the 418 corpus. Production visir top-up deferred to a
separate session with timed-batch infrastructure.

---

## 2026-06-04 — Step 2c closed: parse_visir.py + parsed_visir at visir_parse_v1

**Hvað**: Step 2c lokuð. `parse_visir.py` (299 línur) + `init_parsed_visir_schema.py`
(106 línur) + `parse_visir_test.py` (154 línur) committed. `parsed_visir` table inside
`raw_visir.db` carries 31-column visir-source-flavored schema per §2.2. 10 detail rows
parsed at `PARSER_VERSION='visir_parse_v1'`, 0 failures.

**Selector design (Step A empirical discovery against 5 real samples)**:
21 of 22 fields HIGH confidence selectors from `.property__*` and `.description__*`
BEM namespaces. tenure_signal MEDIUM (rent-marker heuristic, hint-only at parser
tier — canonical authority at Step 2d). agency_name LOW (best-effort, PII dropped
at promotion).

Key selectors locked:
- title: `.property__center-title`
- price_text_raw: `.property__center-price` ("Tilboð" → price_amount=NULL, is_price_on_request=1)
- tegund_raw: `.property__center-class` (drives category classification at promotion)
- size_sqm / rooms / bed / bath / byggar: `.description__head-text` chips with regex
- lysing: `.description__bottom-text` (longest meaningful block)
- addr_street + addr_number: `.property__center-title` PRIMARY (unit-stripped),
  og:title meta FALLBACK
- addr_postcode + addr_city: `.property__center-text` leading 3-digit + remainder
- lat/lng: regex `lat=N&lon=N` from kort URL (NULL if no map)
- fastnum_supplied: label-anchored `.property__bottom-item` with text "Fasteignanúmer",
  F-prefix stripped ("F2534030" → 2534030). NOT page-wide regex.
- photos: gallery `<img>` srcs, deduped
- listing_date: `.property__head-text` "Skráð <date>" (text only, no parse)

**Architect decisions (3) applied to design**:

1. **Rent-marker heuristic LOCKED** (Decision 1): case-insensitive any-of `{Leiguverð,
   til leigu, /mán, á mánuði}` in HTML text → tenure_signal='rent'; else 'sale' (default);
   'unknown' only if both price_text_raw AND tegund_raw extraction failed. MEDIUM
   confidence at parser tier acceptable — canonical authority at Step 2d. If production
   reveals additional rent markers, bump PARSER_VERSION → v2 + re-parse via §2.2
   INSERT-OR-IGNORE on (content_hash, parser_version) UNIQUE.

2. **T2 fixture repurposed as stype≠tenure canary** (Decision 2): Real sample 1052249
   (Phase 1c-captured under stype=rent) is empirically a SALE listing — 79.9M ISK
   total price, fjölbýlishús, no rent markers anywhere in HTML. Test asserts
   tenure_signal='sale' for this ID with explicit comment documenting the empirical
   stype≠tenure noise. Confirms Step 2a finding extends from stype≠category to
   stype≠tenure as well. Synthetic T2b covers true-rent classification path.

3. **Authoritative tenure source = detail-HTML markers, NOT index-stype provenance**
   (Decision 3): Empirical reality says visir's getresults?stype= index is unreliable
   for tenure decomposition. parsed_visir.tenure_signal is parser's best-effort
   detail-HTML reading. Step 2d promotion uses tenure_signal directly as canonical
   tenure source. Index-stype provenance MAY be recorded as audit metadata at
   promotion (deferred design — column like `seen_in_stypes TEXT[]` or similar).

**Persistent learning extending Step 2a**: Index-endpoint classification labels
(visir's getresults?stype=) cannot be trusted for canonical (category, tenure,
sub_type) decomposition. stype contaminates BOTH category AND tenure on visir.
Same discipline applies at Step 3 mbl probe and future sources — always classify
from parsed detail markers, never from enumeration URL labels.

**Verification-stage bug fixes** (caught by 10-row spot-check + locked by regression tests):

- **Bug 1 — `_num()` mangling coordinates**: lat 64.14535959 was being stripped to
  integer 6414535959 because `_num()` stripped non-digit characters. Fix: parse
  fractional coordinate fields with `float()` instead. Locked by T1 lat-range
  assertion (63<lat<67, -25<lng<-13).

- **Bug 2 — og:title omits house number**: og:title meta tag carries only street +
  locality on many listings, so initial addr_number completeness was 10%. Fix:
  `.property__center-title` is now PRIMARY source for street+number (unit-suffix
  "íbúð N" stripped via regex, letter suffix like "24B" / "103A" preserved); og:title
  is FALLBACK. Locked by T11 (synthetic center-title address with unit).

**Field completeness on 10-row sample** (all latest residential sale from smoke #5
getresults page-1):
- 100% populated: title, price_amount, price_text_raw, is_price_on_request, size_sqm,
  rooms, bathrooms, byggar, tegund_raw, tenure_signal, lysing, addr_street,
  addr_postcode, addr_city, fastnum_supplied, n_photos, photos_json, listing_date,
  agency_name
- 90% populated: addr_number (1 "Leifsstaðabrúnir" named summerhouse area legitimately
  has no house number), lat/lng (1 new-build "Vetrarbraut 2-4" legitimately has no map)
- 80% populated: bedrooms (2 listings don't break out svefnh chips — chip absent
  in source HTML, not a parser miss)

All sub-100% counts are empirical legitimate-NULL cases, NOT parser defects.

**Caveat noted**: The 10-row batch is all latest residential sale (smoke #5 page-1).
Commercial / true-rent / Tilboð / plot paths are covered by REAL-sample tests
(T3 against 1056643 commercial-as-rent, T2b synthetic rent) rather than by the live
batch. Production full crawl will surface diversity (commercial sales mixed under
stype=sale, true residential rents, Tilboð prices, plot listings). If edge cases
break v1 selectors, bump `PARSER_VERSION='visir_parse_v2'` and re-parse — §2.2
UNIQUE(content_hash, parser_version) ensures latest version wins for downstream.

**Næst**: Step 2d — canonical promotion (parsed_visir → scraper.listings_canonical).
This is the §6 cross-source dedup proving ground per Step 2 mandate. visir wins over
myigloo per §2.3-D source_priority; will exercise §4 single-table row-merge against
the 861 existing myigloo canonical rows. Tenure decision uses parsed_visir.tenure_signal
directly per Decision 3 above.

---

## 2026-06-04 — §2.1.1 visir rule amendments: Skoðendur counter + class-anchored ad-drop

**Bakgrunnur**: §2.1.1 visir canonicalization rule locked in commit d32d9c2 covered ad-redirect
strip + ad-block drop via anchor-walk. Step 2b P2 smoke testing surfaced two empirical defects
that required amendments before full crawl could safely commit.

**Defect 1 — Skoðendur view counter** (LOCKED 2026-06-04 amendment):
Per-detail-fetch view counter (`<p class="property__head-text">` containing standalone digit
OR labeled `<digit> <span>Skoðendur</span>`) ticks on every fetch. Phase 1b probe used 5-sec
re-fetch gap — too short to observe tick. Caught at Step 2b P2 smoke (~1 min real-world gap
between identical-id fetches).

Fix: two regex normalizations applied AFTER ad-block drop, BEFORE serialize:
- `r'(\d+)(\s|&nbsp;)*(<span>\s*Skoðendur)'` → `'__VIEWS__\2\3'` (labeled counter)
- `r'(<p class="property__head-text">\s*)\d+(\s*</p>)'` → `'\1__VIEWS__\2'` (standalone)

Both date-safe by construction: the registration-date <p> contains `<span>Skráð`, not pure
digit, so neither regex matches it. T11 (counter tick → same hash) + T12 (Skráð date change
→ different hash) confirm.

**Defect 2 — class-anchored vs anchor-walk ad-drop** (LOCKED 2026-06-04 mechanism rewrite):
Original locked rule found ad blocks via `/ads/redirect/\d+` anchor presence, walked up 3
ancestors, decomposed matching parent class. Real-world ad containers (`b-partnerlink`,
`partner-link s1 sidebar-top-add`, `ad-banner-mobile footer__top-img`) rotate iframe/script
creatives with NO `/ads/redirect/` anchor. Anchor-walk missed them entirely → re-fetch produced
new content_hash.

Fix: `_drop_ad_blocks` rewritten class-anchored — decompose any element whose own class
matches target set ([a-z0-9]-normalized substring against Reklama|ad-banner|details-ad-block|
partner-link), regardless of inner content type. Subsumes anchor-walk behavior. The
`/ads/redirect/\d+` regex retained as belt-and-suspenders for stray refs in inline handlers.
T13 (iframe/script ad block with no redirect anchor → dropped) confirms.

**Validation method correction** (workflow lesson):
Rotation-based smoke testing (5-min sleep between sweeps) CANNOT validate dedup, because
visir's getresults returns rotating ID set — 5-min gap produced zero detail overlap between
runs. Correct validator: deterministic same-id re-fetch via fetcher's `--ids` flag (new),
loop 2+ iterations with delays to flush slow-tick volatile fields. This method confirmed 3/3
detail IDs dedup over ~6.5 min real elapsed in Step 2b P2.

**Persistent learning**: volatile-field probes for future sources (Step 3 mbl, etc.) MUST
use multi-gap re-fetch (5s + minutes) + deterministic same-id validation, not single-gap
rotation-based testing.

---

## 2026-06-04 — Step 2a (visir probe) closed: /ajaxsearch/getresults locked as enumeration endpoint

**Hvað**: Locked `/ajaxsearch/getresults?stype=<stype>` (GET) sem canonical enumeration
endpoint fyrir visir.is. Settled via 3-phase probe (probe_visir.py Phase 1 + 1b + 1c,
un-tracked, 1303 línur).

**Empirical basis**: visir's minified bundle `/minify/?g=v2-js&v=...` config object
explicitly defines `_param.resultRequestBaseurl = '/ajaxsearch/getresults'`. Cross-stype
test: sale + rent return populated 50-54KB HTML fragments með `/property/{id}` links;
company + vessel return near-empty 9.6KB shells. Pagination via `page` param, to be
reverse-engineered at Step 2b fetcher implementation. ~50 live requests across the 3
phases, 0 kill-switch trips, all HTTP 200; 13 raw samples í scraper_data/ (gitignored).

**Side note (§1.1 correction needed)**: SCRAPER_SPEC_v2 §1.1 currently identifies
`/ajax/photolist` sem search-list AJAX. That is WRONG — empirically confirmed via
bundle inspection that photolist is a per-listing photo-gallery popup loader
(`$.get('/ajax/photolist', {id, type}, ...)`). Spec correction applied til un-tracked
draft í þessari lotu; tracked-doc correction queued for Step 2 closure.

**Out-of-scope (decided not to do)**: forcing visir til að expose JSON API. Existing HTML
fragment output is parseable og works for our use case.

---

## 2026-06-04 — §2.1.1 visir canonicalization rule locked

**Hvað**: Visir raw content-hash canonicalization rule per §2.1.1 (analog of myigloo's
verification.as_of JSON-path nulling, but ad-redirect HTML stripping for visir):

```
1. Strip /ads/redirect/\d+ patterns (replace digits with constant token)
2. Drop <a> elements whose parent class matches:
   Reklama | ad-banner | details-ad-block | partner-link
   (because img src and other ad attributes rotate, not just href)
3. Apply ONLY to text/html payloads (not JSON)
4. Store verbatim blob unchanged; compute sha256 on canonicalized HTML
```

**Empirical basis**: Phase 1b Probe 5 + Phase 1c re-validation. 4 stype × 2 fetches
diff-check showed all differences were rotating ad blocks (5+ `/ads/redirect/N` per
page). Listing content (price, address, area, fastnum, lysing) was byte-identical
across re-fetches.

**Per-source pattern**: each source carries its own volatile-field rule per §2.1.1.
myigloo nulls JSON paths (`organization.verification.as_of`, `owner.verification.as_of`).
visir strips ad-redirect HTML. mbl TBD (Step 3).

---

## 2026-06-04 — visir stype ≠ category; tegund-based classification + label-anchored fastnum

**Hvað (1) — stype ≠ category**: visir's `stype` URL param er ekki clean category axis.
Empirically: real rent sample 1056643 "Skútuvogur 12, 104 Reykjavík" er atvinnuhúsnæði
(commercial property) með "Tilboð" price-on-request, served under stype=rent. Step 2d
promotion verður að classify (category, tenure, sub_type) frá parsed `tegund_raw` field,
EKKI frá stype URL param. tenure (sale vs rent) can be derived from stype reliably; only
category cross-contaminates.

**Hvað (2) — company/vessel empty**: stype=company og stype=vessel return 9.6KB empty
shells á visir (both /search/results og /ajaxsearch/getresults). visir is residential
sale+rent portal; commercial inventory mixes into stype=sale (e.g. 1056643) eða
stype=rent. Real commercial volume only surfaces via tegund-classification during full
crawl. Vessels are out of scope per spec §1.2.

**Hvað (3) — "Tilboð" = price-on-request**: Same convention as myigloo's commercial
price=1 placeholder. Visir uses string "Tilboð" instead of numeric placeholder.
Downstream rule (from Step 1e Phase 2a): commercial price > 0 promoted as-is regardless
of magnitude; residential price ≤ 100 skipped as junk; price = 0 skipped universally.
Visir parser will need to handle "Tilboð" string → null price (or convention placeholder),
and promoter applies the existing commercial-junk-tolerance rule.

**Hvað (4) — fastnum extraction must be label-anchored**: Page-wide regex
`\b[1-9]\d{6}\b` for fastnum is contaminated. Confirmed false positive on real rent
sample 1056643: regex hits include 4360339, which is Google Analytics UA-4360339-3
account ID. Multi-unit buildings also legitimately expose multiple fastnums (e.g.
1021848|1021851|...). Step 2c parser must use targeted selector anchored on
"fasteignanúmer"/"fastnúmer" label, never page-wide regex.

Tier-1 source_supplied feasibility confirmed: fasteignanúmer label fired on 100% of
12 samples (Phase 1) and 6 real samples (Phase 1c). Visir promotion will achieve
high Tier-1 resolution similar to or better than myigloo's 752/870 ≈ 86.4%.

---

## 2026-06-03 (Step 1e closed) — myigloo promotion live: scraper.listings_canonical populated with first 861 listings

**Hvað**: Step 1e (myigloo promotion til canonical) lokuð. `promote_myigloo.py` (340 línur) + `promote_myigloo_test.py` (132 línur, 16/16 pass) committed. **`scraper.listings_canonical` inniheldur nú 861 myigloo listings** (first real-listing Supabase writes í scraper-substream-inu), með **98,1% fastnum resolution** (Tier-1 source_supplied dominant) + TAXONOMY_v2 §3/§4 lookup applied. by category: residential 715, commercial 146. 0 ck_rent_lease / ck_fastnum_resolution violations.

**Empirical wins úr Phase 1 + 2a + 2b**:

- **51 fastnum_supplied missing í properties** (6.7%) — Tier-1 FK-safety fall-through til address/geo match catches these (they land via address_match/geo_match instead of erroring on the FK). Worth periodic check ef count grows — signal til að refresh public.properties frá HMS.
- **Manual-source entries (114, landreg_source='manual')** — Tier-2/3 address-match resolved most (94% had complete address fields). **Final resolution distribution: source_supplied 752 (Tier-1), address_match 40, geo_match 53, unresolvable_by_design 3 (room sub-types með no source fastnum), unresolved 13 (true edge cases — no addr/geo match). 845/861 = 98,1% have a fastnum.**
- **TAXONOMY_v2 §3 amendment** (7→8 sub-types): added `summerhouse` til residential rent sub-type list for myigloo's cottage tag (3 listings live). Editaður í `D:\verdmat-is\TAXONOMY_v2_draft.md` (un-tracked). Pre-flight confirmed `sub_type` er free-form TEXT (no enum constraint) — no migration needed.
- **Source-fidelity decisions** for storage(18) og garage(9): follow myigloo's commercial classification (→ industrial_warehouse / mixed_use_other) frekar en TAXONOMY §3 residential default. Standalone commercial storage/parking facilities eru semantically commercial; §2.5-G "unresolvable" rationale (designed fyrir sub-units within buildings) doesn't apply.
- **Cottage(3) override**: myigloo's 'other' source category remapped til residential/summerhouse based á semantic understanding of cottage rentals as residential housing.

**Price-on-request convention** (NEW DOWNSTREAM RULE):
myigloo agency commercial listings use `price_amount=1` (occasionally 0) sem placeholder fyrir "verð samkvæmt tilboði" — found í 61 listings (47 office, 11 warehouse, 10 retail; Miklaborg + öðrum agencies). At promotion: **commercial listings með price_amount > 0 promoted as-is** regardless of magnitude; **only residential price ≤ 100 skipped** (genuine junk); **price = 0 skipped universally** per ck_price_pos. Net: 9 skipped (7 commercial price=0, 2 residential junk), ~62 commercial recovered vs the naïve ≤100 filter. Downstream consumers (frontend, analytics) MUST handle commercial price ≤ 1000 as "verð samkvæmt tilboði" — apply lower bound (e.g., price > 1000) when filtering commercial by price; UI renders price-on-request label.

**Refined §2.5-G semantic** (additive clarification, Danni 2026-06-03):
"unresolvable_by_design" applies when source provides NO fastnum AND sub_type ∈ {room, parking_space, storage}. **When source provides an authoritative landreg_id (myigloo's `real_estate.landreg_id` for rooms = the parent building's fastnum), the source signal is accepted at source_supplied confidence regardless of sub_type.** `sub_type='room'` column er downstream semantic flag — downstream queries must apply room-rental-specific logic (e.g. don't compute rent/sqm using parent area, don't aggregate as building-level signal). ~48 of 51 room listings got Tier-1 fastnum via parent building this way; only 3 (no source fastnum) stayed unresolvable_by_design. Algorithm runs Tier-1 BEFORE the sub_type gate, which is the locked order.

**Phase 2b implementation issues caught + fixed** (during the live run, before close):
1. **`ON CONFLICT DO UPDATE` double-assigned `canonical_version`** (once via the EXCLUDED-loop, once via the explicit `+1`) → SyntaxError on all 861. Fixed: excluded `canonical_version` from the EXCLUDED-loop. Nothing persisted (all rolled back).
2. **Transaction-pooler defaults a tx to read-only** (`ReadOnlySqlTransaction` on INSERT) — same quirk as the Step-1a migration. Fixed: per-tx `SET TRANSACTION READ WRITE` folded into each upsert via `mogrify` (single round-trip).
3. **`preload_props` left an open read-tx** (autocommit=False) → the FIRST upsert's `SET TRANSACTION READ WRITE` wasn't the first statement of its tx (only parse_id=1 failed; rows 2+ succeeded after the prior rollback cleared it). Fixed: `pg.rollback()` after preload. Re-run promoted the last row → 861. Resumable throughout (promoted_to_canonical_at + ON CONFLICT idempotency).

**Architecture decisions**:
- Bulk-preload properties candidate slice frá Supabase (filtered by 66 distinct postcodes í parsed_myigloo): ~89K address-keys + 705 present-fastnums into in-memory dict for (heimilisfang_norm, postnr) + per-postnr geo lookups. Eliminates per-row Supabase round-trips during resolution.
- psycopg2 per-row UPSERTs via `.dbconfig` service-role connection, `ON CONFLICT (source, source_listing_id) DO UPDATE` (idempotent re-runs; canonical_version increments on conflict). Per-row error isolation (one bad row logged, doesn't poison the rest).
- `normalize_address` shared utility (commit b503981) used for address-match tier.
- ISO8601 timestamps frá Python call-site, never SQL.

**Phase 2b operational metrics** (final):
- scraper.listings_canonical rows frá myigloo: 861
- skipped_junk: 9   failed promotions: 0
- Fastnum resolution: source_supplied 752, address_match 40, geo_match 53, unresolvable_by_design 3, unresolved 13 → **98,1% (845/861) with fastnum**
- by category: residential 715, commercial 146; by sub_type incl summerhouse 3
- Total promotion time: ~176 sec (per-row upserts; resumable)
- parsed_myigloo.promoted_to_canonical_at set for 861 rows (9 junk stay NULL)

**Files í Step 1e commit**:
- `app/scripts/promote_myigloo.py` (340 línur, stdlib + psycopg2, PROMOTER_VERSION='0.1.0')
- `app/scripts/promote_myigloo_test.py` (132 línur, 16/16 pass)
- Additive uppfærslur á `docs/STATE.md` og `docs/DECISIONS.md`

**Untracked changes** (intentionally not in commit): `D:\verdmat-is\TAXONOMY_v2_draft.md` §3.1 amendment (added summerhouse line, un-tracked draft).

**Deferred (post-Step 1e, ekki blockers)**:
- **PostgREST exposed-schemas dashboard step** — manual Danni task til að gera `scraper.*` views REST-reachable from frontend. (Canonical writes are unaffected; only frontend REST consumption blocked.)
- Step 2 — visir scraper (next major scraper-substream task).
- Step 3 — mbl scraper (Playwright headless, kill-switch per §0.5).
- Cross-source dedup (§4) — gated til mbl + visir add sources.
- iter_rent_v1 asking-rent model — post-canonical, dependent á promoted data.
- api_page (index) parsing for withdrawn-detection (§7.2 2-night rule).

**Næsta skref**: dashboard exposed-schemas (Danni manual) + Step 2 visir scraper.

## 2026-06-03 (Step 1d closed) — myigloo parser live: parsed_myigloo populated with Tier-1 fastnum resolution insight

**Hvað**: Step 1d (myigloo parser) lokuð. `init_parsed_myigloo_schema.py` (119 línur) + `parse_myigloo.py` (260 línur) + `parse_myigloo_test.py` (127 línur, 16/16 pass) + `scripts/fixtures/parsed_myigloo_fixture.json` (sanitized hand-crafted fixture) committed. raw_myigloo.db inniheldur nú parsed_myigloo með 870 rows, 1:1 með distinct detail content_hashes í raw_fetches. Engin parser failures.

**Critical empirical wins úr Phase 1.5 mini-probe (Q1/Q2/Q3/Q8)**:

- **Q1 — `real_estate.landreg_id` IS the HMS fastnum** ⭐: 86.9% fill rate (756/870), 30/30 cross-match against `public.properties.fastnum` (100%). `landreg_source='landreg'` flags authoritative; `manual` (~13%) fallback til address resolution (Tier 2/3). Þetta er Tier-1 source_supplied fastnum per §2.5 fyrir ~87% af myigloo listings — leapfrogs the 47-71% address-match ceiling sem §2.5 var byggt í kringum. Promotion step (Step 1e) mun nýta `fastnum_supplied` column fyrst, þá address tier fyrir manual entries. Aðskilið frá Step 1c finding (§2.1.1 verification.as_of), þetta er annað major source-quirks insight á sama dag.

- **Q2 — deposit_isk = `insurance_price`** (tryggingafé absolute kr): empirical ratio distribution showed insurance_price varies 1-3× monthly rent (3× most common, 357/870; avg insurance_months 2,25). Schema captures both absolute amount (`deposit_isk`) og multiplier signal (`insurance_months`). `move_in_price.total` is composite (deposit + first month rent) → overflow, ekki canonical. `pre_paid_rent_*` always null í myigloo → drop entirely.

- **Q3 — lysing = `primary_description.text`** (Icelandic original): `primary_description.translation` er language metadata ({lang:'is', native:'Íslenska'}), ekki translated text. `description_translations[]` er translated variants (lang en/pl populated). Canonical maps lysing direct from primary_description.text.

- **Q8 — listing_type vocabulary**: 15 distinct tags + 5 categories empirically enumerated (confirmed identical í full run). TAXONOMY_v2 §3 mapping locked (15 tags → 7 residential sub-types + 4 commercial sub-types). NEW SUB-TYPE: `summerhouse` will be added to TAXONOMY_v2 §3 for cottage tag (3 listings observed). TAXONOMY_v2 amendment deferred til Step 1e (promotion) þegar mapping lookup table verður smíðuð.

**Parser architecture**:
- Per-(content_hash, parser_version) — matches §2.2 spec, UNIQUE INDEX enforced (distinct content_hash = rows = 870, invariant holds).
- INSERT ... ON CONFLICT DO NOTHING fyrir idempotent re-runs.
- On success: flips ALL raw_fetches sharing the content_hash til parse_status='parsed' (multi-fetch handling).
- On per-blob failure: only the specific raw_id flagged 'failed' (no cascade — DLQ-correct).
- raw_overflow JSON excludes PII paths (whole `owner` object dropped; `real_estate` mapped svo `owners[]` PII excluded líka).
- raw_overflow nullifies volatile paths (organization.verification.as_of) — same §2.1.1 paths pre-hashed at raw level, also scrubbed from parsed-level overflow.
- Engagement metrics (views_count, application_count, has_applied, last_conversation, liked, pre_approval, client_steps_done) preserved í overflow med `_volatile_suspect` flags — useful for future analysis (time-on-market predictors) but flagged as not-canonical.
- ISO8601 timestamps frá Python call-site, never SQL.
- api_page rows EKKI parsed (deferred; 9 rows stay parse_status='pending').

**Phase 2b operational metrics**:
- parsed_myigloo rows: 870
- raw_fetches detail parse_status='parsed': 870  (pending 0, failed 0)
- parse failures: 0
- fastnum_supplied fill rate: 86,9% (756/870 — matches Phase 1.5 mini-probe exactly)
- listing_type_tag distribution matches Phase 1.5 vocabulary table (15 tags); category_tag 5 (residential 714, commercial 147, bnb 5, other 3, hotel 1)
- **title null count: 449 (51,6% — over half, NOT a small minority)**; canonical promotion will COALESCE(title, short_address) at Step 1e
- **lysing null count: 13** (listings with no source `primary_description.text`; nullable, expected — NOT 0)
- avg insurance_months: 2,25
- Total parse time: 2,2 sec

**Empirical corrections to mid-Phase assumptions** (surfaced at full-run inspect, before commit):
- title-null was assumed "small minority" í Phase-2a plan — empirically 449/870 = 51,6%. COALESCE-at-promotion is therefore load-bearing for ~half the corpus, not an edge case.
- lysing-null was assumed 0 — empirically 13 (matches Phase-1.5's 857/870 non-null primary_description.text). Genuine source reality (those listings carry no description), not a parser miss.

**Files í Step 1d commit**:
- `app/scripts/init_parsed_myigloo_schema.py` (119 línur, stdlib only, idempotent §2.2 + Q1/Q2 DDL)
- `app/scripts/parse_myigloo.py` (260 línur, stdlib only, PARSER_VERSION='0.1.0')
- `app/scripts/parse_myigloo_test.py` (127 línur, 16/16 pass)
- `app/scripts/fixtures/parsed_myigloo_fixture.json` (sanitized fixture, no PII)
- Additive uppfærslur á `docs/STATE.md` og `docs/DECISIONS.md`

**Ófært**: `app/scripts/probe_myigloo.py` (Phase 1 ad-hoc, untracked). TAXONOMY_v2 amendments (cottage → summerhouse sub_type, bnb/apartment_hotel → hospitality) í `D:\verdmat-is\TAXONOMY_v2_draft.md` deferred til Step 1e þegar promotion mapping er smíðuð.

**Source-fidelity decisions** (architect calls):
- title null → preserved as-is í parsed; COALESCE til short_address (eða addr_street+addr_number) við canonical promotion (Step 1e), ekki parse-time.
- listing_type_tag = 'studio' vs lysing-says-'herbergi' noise: parser preserves source signal verbatim; TAXONOMY mapping við promotion. Future feature post-promotion: flag tag_uncertain ef mis-match patterns rísa.
- PII drop confirmed (GDPR posture — capture only what we need).

**Deferred (post-Step 1d, ekki blockers)**:
- api_page (index) parsing — separate index-observation parser, will produce a withdrawn-detection signal (per §2.1 footer 2-night rule).
- TAXONOMY_v2 amendment for summerhouse sub_type — Step 1e.
- Step 1e promotion til scraper.listings_canonical (Tier-1 fastnum resolution + Tier-2/3 fallback for manual entries).

**Næsta skref — Step 1e (promotion)**: reads parsed_myigloo WHERE promoted_to_canonical_at IS NULL, applies TAXONOMY_v2 lookup (listing_type_tag → category/tenure/sub_type), resolves fastnum (Tier-1 from fastnum_supplied OR Tier-2/3 address-match), maps to scraper.listings_canonical 39 columns, INSERTs/UPSERTs til Supabase. Cross-source dedup (§4) deferred til mbl + visir come online (Step 2 + 3).

## 2026-06-03 (Step 1c Phase 3 closed) — myigloo raw fetcher live: hybrid index + detail, normalize-before-hash idempotency

**Hvað**: Step 1c Phase 3 lokuð — `fetch_myigloo.py` (378 línur, stdlib only) + `fetch_myigloo_test.py` (169 línur, 14/14 pass) committed sem fyrsti production scraper-modul. Production raw_myigloo.db inniheldur fyrsta nightly snapshot af ~870 virkum leigulistum, content-addressable storage + append-only ledger per §2.1 + §2.1.1 normalization.

**Critical mid-Phase finding — content-hash idempotency defeated by volatile per-request timestamps**:

Phase 3b's first full run completed clean operationally (880 fetches, 0 errors, 0 retries) but inspect afhjúpaði að `changed=0` fired aldrei á neinum re-fetch. Diff á tveggja fetches á sama listing (id=23989, 11 mín gap) sýndi að allir fields voru identical EXCEPT:
- `organization.verification.as_of`: server-stamped við request-time
- `owner.verification.as_of`: sama

Þetta þýddi að hver detail response var unique per fetch → sha256 alltaf different → blob dedup virkaði aldrei. Storage hefði vaxið linearly (~4 MB × N nætur) án dedup. `changed` flag varð gagnslaus per-listing change signal — beint stríðandi við §2.1 stated contract.

**Fix — normalize-before-hash (§2.1.1 amendment)**:

- `content_hash` redefined: sha256 á CANONICALIZED body (per-source volatile-field paths nulled).
- `blob_gz` heldur áfram að geyma verbatim body (capture-fidelity preserved — staðfest post-fix: `verification.as_of` enn til staðar í stored blob).
- Per-source volatile field paths skráð í §2.1.1 (myigloo: `organization.verification.as_of`, `owner.verification.as_of`; visir og mbl TBD við Steps 2 og 3).
- Unit-test validated: identical bodies → same hash; bodies differ only í verification.as_of → same hash; bodies differ í real fields → different hashes; non-JSON payloads → graceful raw-hash fallback.
- Live-validated post-fix: dry-run × 2 immediately á sömu IDs → second fetch sýndi (detail, changed=0)=10 rows í raw_fetches (22 fetches → 12 distinct blobs). Idempotency contract restored.

**Phase 3 final operational metrics** (post-fix full run á clean baseline):
- Total raw_fetches: 879   raw_blobs (unique): 879
- api_page: 9 (all changed=1 — page composition shifts over time as expected)
- detail: ~870 (all changed=1 í fyrsta nightly snapshot, ekkert prior state)
- HTTP errors (post-retry): 0   Max retry_count observed: 0 (this baseline run; Phase 3a dry-run hafði one transient id=22844 retries=1)
- Uncompressed: ~18,6 MB   Compressed: ~4,1 MB   Ratio ~22%
- Full run elapsed: ~21,7 mín @ 1s politeness

**Empirical validations úr Phase 3**:
- `order_by=-published_at` honored — first-page IDs strictly descending by published_at (cross-validated by third-party HTML scraper audit á D:\myigloo_tracker_v2). Enables future incremental-sync stopping-condition.
- `page_size=100` honored consistently — hver index page skilar exactly 100 items.
- Retry path validated in wild — Phase 3a dry-run á id=22844 með retries=1 (transient failure auto-recovered). Decision matrix: 5xx + 429 + ConnError + Timeout = retry með exponential backoff (1s, 2s, 4s); 4xx other than 429 = no retry.
- 5xx outage detection unit-test validated; ekki yet stress-tested in wild.
- Compression ratio ~22% consistently.

**Architectural notes**:
- Body data rides on FetchResult dataclass aðeins transiently — no memory growth over ~880 fetches.
- Allir ISO8601 timestamps koma frá Python call-site, never SQL.
- HTTP failures post-retry skrifa content_hash=NULL ledger row með parse_error=NULL.
- Normalization (§2.1.1) applies aðeins við hash computation; blob_gz geymir verbatim body fyrir fidelity og future re-parse.

**Files í Phase 3 commit**:
- `app/scripts/fetch_myigloo.py` (378 línur, stdlib only, með `_canonical_hash()`/`_nullify_path()`)
- `app/scripts/fetch_myigloo_test.py` (169 línur, 14/14 pass — including normalize-related cases)
- Additive uppfærslur á `docs/STATE.md` og `docs/DECISIONS.md`

**Ófært**: `app/scripts/probe_myigloo.py` (Phase 1 ad-hoc, untracked). §2.1.1 amendment í `D:\verdmat-is\SCRAPER_SPEC_v2_draft.md` (un-tracked draft).

**Næsta skref — Step 1d (parser)**: reads raw_blobs frá raw_myigloo.db, extracts structured fields úr ~80-key detail payload, populates `parsed_myigloo` table.

## 2026-06-03 (Step 1c Phase 2) — myigloo raw layer: hybrid fetching design + scraper_data/ outside-repo storage

**Hvað**: Step 1c (myigloo raw fetcher) Phase 2 lokuð — schema bootstrap + scraper_paths utility committed. Phase 1 audit probe lokuð empíríkt sama dag (ad-hoc `probe_myigloo.py` untracked fyrir Phase 3 referens). raw_myigloo.db smíðað eftir SCRAPER_SPEC_v2 §2.1 verbatim (raw_blobs + raw_fetches + v_dlq_parse_failures view), WAL mode, FK enforcement on. Smoke test 13/13 pass, scraper_paths_test 8/8 pass.

**Fetching design — hybrid (locked)**:
- Index-walk per cycle: `GET /api/listings/?page=N&page_size=100` (~9 pages) → enumeration eingöngu. `fetch_kind='api_page'`, `source_listing_id=NULL`. Page blobs low-value/short-retention.
- Detail-per-id per cycle: `GET /api/listings/{id}/` (~874 calls) → rich payload (~80 keys, m.a. `primary_description` (lýsing fyrir LLM extraction), `contract_min_months/max_months/termination_term`, `move_in_price`/`insurance_*`/`pre_paid_rent_*`, `amenities`/`furniture`/`rules`, `mbl_id` cross-ref, `linked_property_id`). `fetch_kind='detail'`, `source_listing_id=<id>`. Full §2.1 content-hash idempotency: óbreyttur body → `changed=0` + `parse_status='skipped_unchanged'` + hash reused; breyttur body → ný blob + `changed=1`.

**Hvers vegna hybrid frekar en page-only**: (1) detail er essential — `primary_description` er lýsing fyrir LLM extraction (iter_rent_v1 forsenda), og page-payload skortir öll canonical/§2.5 fields. (2) §2.1 content-hash idempotency virkar bara á detail-level — á page-level shiftast composition daglega svo hash breytist next time þótt enginn listing breytist, sem gerir §2.1 dedup-virði ~zero. (3) Call-budget ~880/night @ 1s politeness ≈ 15 mín — vel undir §0.5 mbl-cap (sem á hvort sem er ekki við myigloo: ekkert WAF, opin DRF-style API, robots 404 á rent-api subdomain).

**Empíríkar áréttingar úr Phase 1 probe (leiðréttingar á §1.1 og handoff)**:
- Array key er `items[]`, ekki `results[]` (handoff rangur)
- Live count 874 (vs handoff 871; +3 drift)
- `per_page` er **silently ignored** — einungis `page_size` virkar (kritisk gotcha; fetcher sem notar `per_page` mis-paginar í default 25/page án villu)
- Server er uvicorn / FastAPI-Starlette, ekki klassísk DRF
- Detail endpoint `/api/listings/{id}/` til staðar, HTTP 200, ~3× richer
- `rent-api.myigloo.is/robots.txt` skilar 404 — ekki restriction

§1.1 í `D:\verdmat-is\SCRAPER_SPEC_v2_draft.md` (un-tracked, utan repo) fékk additive empirical-correction note 937→945 línur — ekki hluti af þessum commit.

**Storage convention (locked)**:
- Raw SQLite DB-ar lifa á `D:\verdmat-is\scraper_data\raw_<source>.db`, utan git-repo. Mirrors `D:\Gagnapakkar\*.db` convention; multi-GB blob accumulation færi aldrei í commits.
- Path read úr env-var `SCRAPER_DATA_DIR` (default `D:\verdmat-is\scraper_data\`), via shared utility `app/scripts/scraper_paths.py`.
- `.gitignore` belt-and-suspenders: `scraper_data/`, `*.db`, `*.db-shm`, `*.db-wal`.

**Files í Phase 2 commit**:
- `app/scripts/scraper_paths.py` (39 línur, stdlib only, raw docstring til að forðast SyntaxWarning)
- `app/scripts/scraper_paths_test.py` (92 línur, 8/8 pass: default/env/parent-dir/per-source/validation/idempotency)
- `app/scripts/init_raw_myigloo_schema.py` (98 línur, idempotent §2.1 DDL verbatim + v_dlq_parse_failures view)
- `app/.gitignore` (+8 línur: scraper raw-DB block með comment refererandi §2.1)

**Ófært í commit**: `app/scripts/probe_myigloo.py` (Phase 1 ad-hoc, untracked til Phase 3 refactor). `D:\verdmat-is\SCRAPER_SPEC_v2_draft.md` §1.1 correction (un-tracked draft sem býr utan repo).

**Næsta skref**: Phase 3 — fetcher implementation. Hybrid index + detail loop, gzip-compressed blob storage með sha256 hash á óþjappðu body, append-only ledger með changed=0/1 logic, polite UA + 1s delay, dry-run flag fyrir 2-page warm-up áður en fullur 874-listing run keyrir.

## 2026-06-01 — Scraper schema applied: `scraper.*` foundation live í Supabase (SCRAPER_SPEC_v2 §2.3 + §2.4 + §2.5)

**Context**: Fyrsta production-write úr scraper-substream-inu. SCRAPER_SPEC_v2 (planning-drafts á `D:\verdmat-is\`, un-tracked) er architecturally locked fyrir §0/§1/§2.1-2.5/§3/§5/§6/§7. Næsta concrete skref var að leggja canonical schema-target inn í Supabase **áður en** scraper-kóði (parser/fetcher) er skrifaður — surfaces hvaða DDL-issue sem er strax og gefur myigloo Step 1 skýrt target.

**What**: Migration `20260601122916_scraper_schema_init.sql` applied via MCP `apply_migration` (single BEGIN/COMMIT). Nýtt `scraper` schema:
- `listings_canonical` base table — **39 cols**: decomposed `(category, tenure)` key + `sub_type` + `tegund_raw` + `lease_term_class` (TAXONOMY_v2); `fastnum` FK → `public.properties` **ON DELETE NO ACTION**; PostGIS `geog` generated column; fastnum-resolution trió (`method`/`confidence`/`at`, §2.5).
- **4 enums** (`category_enum`, `tenure_enum`, `lease_term_enum`, `fastnum_res_enum` m. `unresolvable_by_design`).
- **5 CHECK** constraints (`ck_rent_lease`, `ck_plot_area`, `ck_price_pos`, `ck_fastnum_pos`, `ck_fastnum_resolution`) + `uq_source_listing` UNIQUE.
- **7 indexes** (5 named `ix_lc_*` incl `ix_lc_geo` GiST á geography, + unique + PK).
- RLS enabled + `public_read` SELECT policy + column-allowlist GRANT (**29 cols** TO anon/authenticated; operational/provenance cols excluded) — sama mynstur og Group B 14-tafla lockout.
- **5 security_invoker views** (`v_residential_sale_listings`, `v_residential_rent_listings`, `v_commercial_listings`, `v_plot_listings`, `v_listings_combined`); residential-views join → `public.v_properties` (Group B view-layer abstraction, FIX 3 — `v_properties` exposes byggar/einflm/matsvaedi_nafn anon-readable).

**Why this gating**: Step 1 (myigloo raw→parsed→canonical) þarf canonical-target til staðar áður en parser/fetcher-kóði er skrifaður. Schema-first afhjúpar DDL-vandamál strax — dry-run (BEGIN…ROLLBACK gegn live) staðfesti FK + PostGIS `geog` + enums + views + grants áður en apply, og fann tvö latent-issue í endurskoðun: `is_active` getur ekki verið GENERATED column (now()-háð → stored + nightly-refresh) og `ON DELETE SET NULL` rakst á `ck_fastnum_resolution` (→ NO ACTION).

**Verification**: post-apply **10/10** read-only checks grænir — schema(1), enums(4), relations(6 = 1 tafla + 5 views), columns(39), CHECKs(5), indexes(7), policy(1 `public_read`/SELECT), anon-allowlist(29), anon `v_residential_rent_listings` count=0 án villu (security_invoker resolve-ar rétt), extensions(pgcrypto + postgis).

**Pending manual Danni steps** (ekki blocking downstream): (1) Supabase dashboard → API → Exposed schemas → add `scraper` (annars eru v_* views ekki REST-reachable); (2) `supabase migration repair --status applied 20260601122916` svo future `db push` reynir ekki re-apply (apply var via MCP, ekki CLI, svo schema_migrations-taflan þekkir hana ekki enn).

**Explicit non-changes**: ENGIN `public.*` tafla/view snert; ENGIN existing gögn breytt; net-new additive schema. `pgcrypto` + `postgis` voru þegar til staðar (CREATE IF NOT EXISTS = no-op).

**Refs**: `SCRAPER_SPEC_v2_draft.md` §0.1-§0.5 (sign-offs Danni 2026-05-29/06-01: evalue-replace strategy, asking-rent leigu-módel, single-table `(category,tenure)`, TAXONOMY_v2 pre-req, mbl headless+kill-switch) + `TAXONOMY_v2_draft.md` (locked 2026-05-29: 4 categories × 2 tenures, rent/commercial/plot sub-types, fastnum-resolution eligibility). §4 frontend = pass 3b (deferred til UI input).

## 2026-05-29 — Skref 13b: iter3v2/iter4 spine debt RESOLVED via option (ii) (decouple) + push_preview version-stamp guard

**Context**: Precompute-spine debt (systkina-entry sama dag) gerði push-path-inn rangan: `run_monthly` push myndi UPSERT-a iter3v2-afurð `build_precompute` ofan í live `predictions`-töfluna sem er iter4. Tvær leiðir voru á borðinu — (i) full track-unification, (ii) decouple. Valið féll á **(ii)** eftir CC1 READ-ONLY audit (Q1+Q6).

**CC1 findings sem réðu valinu**:
- **Q1 — `score_new_listing` er EKKI í production runtime path**: 0 runtime-hits í app-repo (aðeins docs); eini caller er `build_precompute` (batch). Frontend les iter4 alls staðar via `v_current_predictions`-view; iter3v2 birtist EINGÖNGU í `?mode=debug` (`predictions_iter3v2`-tafla). → iter3v2-spine þjónar ENGUM notanda, svo decouple hefur núll user-facing downside.
- **Q6 — ein tafla, tveir track-writers**: live taflan heitir **`predictions`** (EKKI `predictions_iter4` — það er bara CSV-skráarnafn frá iter4-leiðinni). `import_iter4.py` (Skref 10) renamed gömlu iter3v2 → `predictions_iter3v2` og COPY-aði iter4 í `predictions`. `run_monthly` push-target `("predictions","predictions.csv")` + iter4-leiðin target SÖMU töflu → áreksturinn.

**Option (i) vs (ii) trade-off**: option (i) (færa build_precompute + score + recal + validate á `iter4a` + conformal) er ~340-630 LOC + **reiknirit-skipti** í monthly_recalibration (k-factor stretch → conformal refit) + JSON-schema migration — paradigm-migration, ekki swap. Option (ii) (decouple) er ~2-12 LOC. Þar sem iter3v2 þjónar engum (Q1), er decouple réttur fyrsti leikur; option (i) deferred til Phase Y iter4-spine sprint (þá fær precompute aftur predictions-ownership undir iter4).

**Hvað var gert**:
1. `run_monthly.py` `PRECOMPUTE_TARGETS`: `predictions` + `feature_attributions` commented út (preserved fyrir framtíðar re-enable) — push snertir þær ekki lengur.
2. `build_precompute.py --skip-predictions` flag (early-return í `score_and_shap`), wired inn í orchestrator build_precompute-step (`cmd … --skip-predictions`).
3. **push_preview version-stamp guard** (`check_version_stamp`): fyrir hverja push-target sem hefur `model_version`-dálk, ber saman CSV-version-sett vs live-version-sett; mismatch → `main` HALT-ar með exit 4 (`halted_version_mismatch`). Column-gated, svo model-óháðar töflur (properties/sales/repeat_sale/ats/comps) self-skip-a.

**Guard rationale**: Skref 12d push-preview gaf "+0" á `predictions` — en það var **count-parity, ekki value-parity**: push_preview bar aðeins saman `count(*)` (run_monthly.py L334-342), svo iter3v2-vs-iter4 track-munur var ósýnilegur. Falskt +0 hefði hleypt iter3v2 yfir iter4 silently. Version-stamp guard lokar þessu blindspot-i varanlega — verður relevant aftur þegar predictions er re-enabled í push (Phase Y).

**Empirical**: guard-smoke 3/3 (synthetic iter3v2 → mismatch HALT; `iter4_final_v1` → pass; `properties` self-skip) gegn live `predictions`. `run_monthly --dry-run` (run id=9) grænn með `build_precompute … --skip-predictions`. Báðar skrár byte-compile clean. ENGIN push.

**Commits**: precompute `41d123c` (build_precompute.py, explicit-path; held-set-gate `rebuild_predictions_iter4.py` skilið eftir uncommitted f. Skref 13c) + app-commit (run_monthly.py + docs) þessa lota — two-repo split (atomic two-repo push-helper er sjálft Skref 13c). EKKERT pushað.

**Afleiðing fyrir push-gating**: spine-blocker farinn; push nú gated aðeins á 2-3 proven cycles + version-guard-green. 13b ✅.

---

## 2026-05-29 — Precompute-spine debt (iter3v2 build_precompute vs iter4 live serving) elevated til Skref 13 push-blocker

**Context**: Skref 12c/12d cascade re-confirm-aði undir nýju ljósi að `build_precompute.py` + `score_new_listing.py` + `monthly_recalibration.py` + `validate_metrics.py` keyra allir á **iter3v2-track**, en live serving (`/eign/[fastnum]`, `predictions`-taflan) er **iter4_final_v1 + iter4_conformal_v1**. Þetta var þekkt tech-debt en var "passive" þar til reconciliation gerði push-path-inn raunhæfan.

**Af hverju þetta er nú blocker, ekki bara debt**: `push_precompute_to_supabase` (Skref 13) myndi taka iter3v2-afurð `build_precompute` og skrifa hana yfir iter4 `predictions`-töfluna → silent model-track regression í prod. Reconciliation (Skref 11→12) fjarlægði 232.887-vs-124.835 divergence-ina sem hingað til hefur BLOKKAÐ push; spine-mismatch-inn er núna eini eftirstandandi correctness-blocker fyrir push.

**Decision**: spine-alignment er **hard pre-req fyrir push** (Skref 13b). Tvær leiðir á borðinu, EKKI valið enn:
- (i) Færa `build_precompute` predictions-step yfir á `iter4a_*.lgb` + iter4_conformal_v1 (full track-unification) — réttast en stærra.
- (ii) Disable-a predictions-step í `build_precompute` (lætur live iter4 `predictions` ósnerta; push skrifar aðeins properties / comps / attributions) — minni breyting, en skilur tvo tracks eftir.
Ákvörðun gated á Skref 13b spike.

**Knock-on**: validate_metrics drift-flagg (sjá systkina-entry sama dag) er iter3v2-calibration artifact, ekki live-iter4 signal — styrkir að spine-split sé raunverulegur, ekki cosmetic.

**Status (2026-05-29, Skref 13b)**: **RESOLVED via option (ii)** (decouple) — iter4-spine-migration (option i) deferred til Phase Y. predictions/feature_attributions tekin úr `run_monthly` push-targets + `build_precompute --skip-predictions` + push_preview version-stamp guard. CC1 Q1/Q6 sönnuðu: score_new_listing þjónar engum notanda, live tafla = `predictions` (iter4). Sjá Skref 13b entry efst.

---

## 2026-05-29 — sales_history −786 push-preview anomaly: reconciliation-strategy deferred til Skref 13c

**Context**: Skref 12d standalone `build_precompute.py --force` push-preview á reconciled state sýndi: `properties` / `repeat_sale_index` / `ats_lookup` / `predictions_iter4` allir **+0 vs live** (clean match — reconciliation proven), `comps_index` **+634.212** og `feature_attributions_iter4` **+571.870** (expected growth fyrir nýja 232.887-universe-ið), EN `sales_history` **−786** (preview hefur 173.081, live hefur 173.867).

**Root cause**: `build_precompute` deriva-r sales_history úr `training_data_v2` filtrað á last-5-sölur-per-fastnum. Phase D3 apply (2026-05-27) skrifaði 786 sölur sem **raw direct-inserts** (þ.m.t. `onothaefur=1` rows) sem ná aldrei inn í training_data_v2 filter-inn → þær birtast ekki í build_precompute-afurð. −786 er því derivation-vs-direct-insert mismatch, EKKI gagnatap; live sales_history (173.867) er rétt.

**Af hverju deferral, ekki fix núna**: ekkert er pushað í Skref 12; −786 er push-preview observation, ekki live-state breyting. Fix-ið krefst stefnuvals sem snertir push-helper-hönnun.

**Decision (deferred til Skref 13c)**: tvær leiðir:
- (a) **append-D3**: push-helper upsert-ar build_precompute sales_history en skilur D3 raw-rows (786) eftir ósnertar (additive, varðveitir onothaefur-flaggaðar).
- (b) **re-derive**: extend-a `training_data_v2` / build_precompute svo D3 raw-sölur (incl onothaefur) verði first-class — root-fix per [[feedback_root_fix_vs_workaround]] en stærra.
Val gated á push-helper byggingu í Skref 13c.

---

## 2026-05-29 — validate_metrics cov80 +5,95pp er coverage-IMPROVEMENT, ekki regression; baseline-rebase deferred til 13a

**Context**: run_monthly cascade á reconciled state (Skref 12c, run id=8) halt-aði á `validate_metrics`: cov80 73,10% → 79,05% (**+5,95pp** vs frosna 4c-baseline-inn). Þröskuldur er ±3pp coverage → flaggað sem fail/halt.

**Greining**: drift-ið er ekki degradation. `monthly_recalibration` (step á undan) auto-update-aði `calibration_config.json` í þessari keyrslu því SEMI_DETACHED k95 drift datt **31,3% → 22,8%** (undir 30%-þröskuldinn, öfugt við run id=7) — enabled af 552 D3-sölum sem urðu newly-joinable inn í training eftir reconciliation. Ný calibration færir coverage frá 73% **í átt að nominal 80%** — það er bati, ekki tap. ±3pp-gat-ið mælir gegn frosnum 4c-baseline sem var settur FYRIR reconciliation.

**Mikilvægt caveat**: `calibration_config.json` er **iter3v2-track** (sjá systkina-entry um spine-debt), EKKI live iter4_conformal_v1. Þessi coverage-breyting hefur því engin bein áhrif á prod-serving fyrr en spine er sameinað.

**Decision (deferred til Skref 13a)**: rebase 4c-baseline-inn á post-reconciliation calibration (skrá nýjan ~79% cov80 baseline) — **couple-að við recalibration-decision** svo við frystum ekki baseline gegn calibration sem gæti haldið áfram að hreyfast næstu 2-3 cycles. Engin urgency: validate er informational gate, ekkert pushað.

---

## 2026-05-28 — classify_property NaN-safe root-fix (D3 NaN-tegund rows)

**Context**: Skref 12b Step 2 (iter4 predictions rebuild á reconciled 232.887-pkl) crash-aði í `classify_property.py:134`: `if not tegund_str:` gerði ráð fyrir streng, en 89 D3-raðir höfðu `tegund = NaN` (float). `not NaN` → `False` (NaN er truthy), svo guard-inn fór ekki í gang og næsta `.strip()`/lookup kastaði.

**Root fix (ekki plástur)**: `if not tegund_str:` → `if not isinstance(tegund_str, str) or not tegund_str.strip():` með WHY-comment. Höndlar bæði NaN-float OG tóman/whitespace-streng í einum guard. `classify_property.py` lifir á `D:\` (utan repo við `D:\verdmat-is\app`); fixað in-place via verified Python replacement (Edit-tool gefur EPERM á drive-root), assert count==1. Audit-tracked, ekki git-tracked hér.

**Af hverju þetta kom fyrst núna**: pre-reconciliation pkl (124.835) hafði enga NaN-tegund; D3-recovery-universe-ið bætti við 89 raðum með vantandi tegund (HMS payload án skráðrar tegundar). Reconciliation afhjúpaði latent type-assumption sem hafði aldrei verið testuð gegn NaN.

**Tengt**: [[feedback_root_fix_vs_workaround]] — gat ekki bara dropp-að 89 röðunum; isinstance-guard-inn er rétti staðurinn.

---

## 2026-05-28 — D3 honesty gate materialíseraður sem held-fastnum-set artifact (d3_held_fastnums.csv)

**Context**: Reconciled pkl (232.887) inniheldur 8.426 D3-eignir sem voru held úr scoring í Phase D3 NOW lota (5.993 matsvaedi-unconfident + 2.433 no-byggar) til að halda iter4_conformal_v1 PI-i heiðarlegum (ablation: blank matsvaedi → 51%/22% PI breach vs 0%/0% spatial-inferred). Skref 12b iter4 predictions rebuild þurfti að virða þennan gate — annars hefðu held-raðir fengið low-confidence predictions skrifaðar.

**Decision**: gate-inn er materialíseraður sem **standalone artifact** `D:\d3_held_fastnums.csv` (8.426 rows: `fastnum,reason`, UTF-8 no BOM) frekar en in-lined í scoring-logic (Option d, valið af Danni yfir Option A inline-gate). `rebuild_predictions_iter4.py` les `HELD_CSV` constant og filter-ar preds+shaps gegn settinu fyrir `to_csv` → output 167.503 (var 175.929 ungated, Δ −8.426 = nákvæmlega held-settið).

**Af hverju artifact frekar en inline-gate**: (i) reusable af hverju downstream step (predictions, push-preview, future evalue augl-pass); (ii) explicit auditability — held-count + reason inspectable án þess að lesa scoring-kóða; (iii) decoupling — LATER evalue lota fjarlægir bara raðir úr CSV-inu þegar þær verða confident (matsvæði/byggar fæst), án scoring-rewrite.

**Verifað**: 167.503 = 175.929 − 8.426 (exact). Held-residential UI-state (`/eign/[fastnum]`: "Verðmat liggur ekki fyrir þessa eign") þjónar þessum 8.426 gracefully.

**Tengt**: Phase D3 honesty-gate decision (DECISIONS 2026-05-27 D3-entry); held-set un-holdast í LATER evalue augl-pass.

---

## 2026-05-28 — Orchestrator first-green-cycle + 5-bug debug session

**Context**: Fyrsta raunverulega `run_monthly.py` keyrslan (engin `--dry-run`) eftir Group C closure 2026-05-27. Markmið: end-to-end grænn mánaðar-cycle með halt-before-push gate sannað í verki. `run_monthly` + `migration_helpers` höfðu verið skrifuð en aldrei keyrð gegn raunverulegu subprocess (dry-run sleppti subprocess; fyrsta real-run dó á preflight áður en það náði output-handling). Þannig komu real-execution bugs upp í röð, hver um sig blocking næsta skref. Allir fixaðir at root og regression-testaðir.

**Bug-listi í discovery-röð**:

1. **Drive-relative `Path("D:")` í 5 D:\ scriptum** (LOG_PATH + D_DRIVE konstöntur). `Path("D:")` er drive-relative (resolve-ast gegn current dir á D: drifinu), ekki absolute. Þegar orchestrator keyrði þau frá `D:\verdmat-is\app` (ekki `cd D:\` eins og scriptin documenta) resolve-aðist `Path("D:")/"x"` í `D:\verdmat-is\app\x` → preflight fann ekki input-skrár → exit 2. **Halt-aði run id=2** á step 3 (rebuild_training_data).
2. **cp1252 decode parent-side** í `subprocess.run(..., text=True)`. Á Windows decode-ar `text=True` child-stdout með locale-encoding (cp1252). D:\ build-scriptin emit-a íslenska + box-drawing stafi (`│ ─ á í ð þ ö`); byte 0x81 er ógildur í cp1252 → `UnicodeDecodeError` í subprocess reader-thread → `result.stdout = None`. **Crash-aði run id=3** (unhandled exception, exit 1) eftir að rebuild-subprocess kláraðist en á meðan orchestrator las output-ið.
3. **None-unsafe stdout/stderr** í helper — `result.stdout.splitlines()` og `.strip()` gerðu ráð fyrir streng; með `stdout=None` (frá #2) → `AttributeError`. Bundlað með #2.
4. **No crash-finalize** í `run_monthly.main` — unhandled exception skildi `pipeline_runs` row eftir dangling (`ended_at`/`exit_status` NULL). id=3 var dangling þar til manual cleanup.
5. **Child-side cp1252 stdout þegar piped**. Jafnvel með parent-decode lagað skrifar child-Python sín eigin stdout í cp1252 þegar piped (Windows locale), nema hann reconfigure-i. `refresh_dashboard_tables.py:245` `log(f"... {prev} → {cur} rows")` (U+2192) kastaði `UnicodeEncodeError`; of-breitt `except` í scriptinu mis-túlkaði logging-villu sem data-validation failure → triggeraði óþarfa atomic rollback (restored 14 files) → exit 1. **Halt-aði run id=5** á step 4. Athugið: sjálf data-byggingin (repeat_sale_index + ats_lookup) heppnaðist — aðeins validation-logging línan crash-aði.

**Root fixes (engir plástrar)**:

- **5 per-script**: `Path("D:")` → `Path("D:/")` (absolute, CWD-óháð). Skrárnar lifa á `D:\` data-drifinu (utan repo við `D:\verdmat-is\app`); fixaðar in-place, 0 footguns eftir. EKKI git-tracked hér — logged fyrir audit í commit 8edc297.
- **Helper (`scripts/migration_helpers.py`)**: `encoding="utf-8", errors="replace"` (ekki `text=True`) á báðum subprocess-köllum + `(result.stdout or "")` / `(result.stderr or "")` None-guards + stdout-tail capture á failure-path (svo child sem bail-ar til stdout sé diagnosable).
- **Orchestrator (`scripts/run_monthly.py`)**: `try/except` crash-finalize um step-loop-ið með `current_step_id` tracking; á exception finalize-ar in-flight step (exit_code=-1) + run (`exit_status='crashed'`) áður en re-raise.
- **Env**: `env={**os.environ, "PYTHONIOENCODING": "utf-8"}` á báðum subprocess-köllum — forsar child-stdio í utf-8 óháð því hvort scriptið reconfigure-i sjálft. Þetta er systemic root-fix sem nær yfir alla 6 child-scripts í einu (vs að plástra hvern `→`).

**Empirical validation**: `scripts/shakedown_orchestrator.py` byggður (throwaway harness) — **15/15 assertions**. 5 child-modes (happy / halt / crash / explode / cp1252_writer) + negative control + crash-finalize gegn Supabase audit-töflum. `cp1252_writer` mode reproduce-ar bug #5 faithfully (child sem reconfigure-ar EKKI sín stdout og prentar `→`); **negative control strip-ar `PYTHONIOENCODING` úr env og sannar að bug-#5 mechanism re-fire-ar án env-fix-ins** — proving fixið er load-bearing, ekki cosmetic. Upprunalegi shakedown (Skref 4) missti þetta því synthetic-child-inn hans reconfigure-aði sín eigin stdout; gap-ið var lagað í Skref 6.

**Pipeline_runs audit-trail**:

| id | outcome | hvar |
|---|---|---|
| 2 | halted | step 3, CWD bug (#1) |
| 3 | crashed → manual cleanup | step 3-output, encoding crash (#2-4); finalize-aður handvirkt sem 'crashed' með cleanup-note í `summary` |
| 5 | halted | step 4, cp1252 child-write (#5) |
| 7 | **success_halt_pre_push** | **7 steps green, 113s — fyrsta fully-green cycle** |

**Snapshot id=2** (frá run id=7) fangaði drift-detectable fingerprints: CPI MD5 / kaupskrá MD5 / training_data_v2 MD5 allir breyttir (fresh), `feature_names_hash` stable (sami 154-feature surface), valuation rúllaði 2026-04 → 2026-05, cpi_factor 1,00548 → 1,00885. Reproducibility-ledger virkar.

**Data-quality á run id=7** (sub-script outcomes):
- `monthly_recalibration`: **SEMI_DETACHED k95 drift +31,3%** (k80 +21,8%) yfir 30%-þröskuldinn → scriptið hélt prior calibration (auto-update declined), `calibration_config.json` ÓBREYTT (mtime 2026-04-19), printaði proposed k-factors fyrir manual review. Non-fatal (exit 0).
- `validate_metrics`: **8/8 pass** gegn 4c-baseline — held clean MAPE 6,98% (baseline 7,00%, Δ −0,02pp), cov80 72,90% (73,10%), cov95 92,67% (92,70%); allt innan ±0,5pp MAPE / ±3pp coverage þröskulda. Líkanið stöðugt á prior calibration.

**Open follow-ups (ekki í commit-scope, sér workstreams)**:
- **`properties_v2.pkl` divergence vs live Supabase** — pickle er 124.835 (pre-D3) en live er 232.887 (post-D3). `build_precompute.py` les pickle → push-preview á run id=7 sýndi `properties` csv 124.835 vs live 232.887 (−108.052), `predictions` −57.187, `sales_history` −786; 4 derived-töflur delta +0. **Naive push myndi annaðhvort skilja D3-raðir eftir stale (upsert) eða WIPE-a þær (truncate-reload)** → push BLOKKAÐ þar til pickle er rebuilt FROM Supabase (PLANNING_BACKLOG item 1, SOURCES_OF_TRUTH 2026-05-20 mandate). Skref 10B audit-ar þennan path.
- **SEMI_DETACHED k95 +31,3% drift** — prior cal kept; pending 2-3 cycles til að greina noise vs regime shift. Validate 8/8 pass á prior cal svo engin urgency.
- **`refresh_dashboard_tables` of-breitt `except`** — defanged af env-fix-inu (triggerinn horfinn) en vert að þrengja eventually svo logging-villa verði ekki aftur að spurious rollback.

**Commits**: `8edc297` (orchestrator fix + shakedown) + `16baa59` (gitignore fyrir log-patterns). Báðir á origin/main.

**Process observation (locked)**: halt-on-decision-points design reyndist load-bearing. Þrjár first-execution failures (id=2/3/5) voru hver um sig contained at step-boundary með clean rollback (orchestrator's own halt/crash-finalize + sub-scripts' atomic rollback), og halt-before-push gate fangaði 108K-row divergence ÁÐUR en nokkuð destructive skrifaðist. Auto-fix-and-rerun hefði masked sequence-inn og áhættað bad push. Mynstrið vistað í user-memory (`feedback_halt_on_decision_points`) fyrir continuity.

---

## 2026-05-27 — Phase X Group C trimmed core APPLIED; lightweight current-stack supersedes Hetzner/Dagster/MLflow plan; Phase X fully closed

**Hvað**: Phase X Group C trimmed-core landed live á Supabase prod (project `szzjsvmvxfrhyexblzvq`). Net-new + additive — zero impact on existing tables/views/predictions.

**What was built**:

| Artifact | Purpose |
|---|---|
| `scripts/migration_helpers.py` | 7 reusable patterns extracted from phase_d1/d3/lockout (apply_migration_sql, generate_rollback_sql, unnest_upsert, column_grant_lockout, subprocess_with_shape_safety, register_supabase_migration, set_local_role_and_test) + 3 utilities (open_connection, file_md5_hex, git_sha_head). Future analogue scripts inherit; phase_d1/d3/lockout get header-note pointers (no working-code changes) |
| `supabase/migrations/20260527155123_group_c_audit_tables.sql` | Creates 3 service-role-only audit tables: `pipeline_runs` (8 cols), `pipeline_steps` (12 cols), `inputs_snapshots` (20 cols) + 6 indexes |
| `scripts/run_monthly.py` | Orchestrator wrapping 6 D:\\ monthly scripts + build_precompute, with shape-safety gates per step. On all-green: captures inputs_snapshot + push-preview, then HALTs |
| `scripts/backfill_current_snapshot.py` | One-off: writes ONE inputs_snapshots row anchoring current live batch |
| `scripts/apply_group_c_migration.py` | Apply + verify orchestrator with auto-rollback on verify-fail |

**Post-apply counts**:

| Table | Rows | Notes |
|---|---:|---|
| `public.pipeline_runs` | 1 | dry-run row from run_monthly --dry-run, exit_status=success |
| `public.pipeline_steps` | 7 | one per planned step, all exit=0, notes='dry-run' |
| `public.inputs_snapshots` | 1 | backfill anchor for current iter4 batch |

**Backfill anchor row (`inputs_snapshots.id=1`)** — fingerprints current live batch:

```
model_version       = iter4_final_v1
calibration_version = iter4_conformal_v1
valuation_year/mo   = 2026 / 4
cpi_factor_at_val   = 1.005484731692855
cpi_csv_md5         = cd14045c9ff5…
kaupskra_csv_md5    = 0105a680c197…
kaupskra_last_mod   = 2026-04-20 02:00:36 UTC  (state-file value; refresh hasn't run since)
training_data_v2_md5 = 405b663f21d7…
feature_names_hash  = 0f8b90a8cd9d…  (154 features)
properties_n        = 232,887
predictions_n       = 167,503
git_sha             = e938cc5ffebb…  (HEAD at backfill time)
precompute_git_sha  = c85ad83cb11f…
extra.note          = "backfill of current state"
```

This row answers reproducibly: "what inputs produced the 167,503-row iter4 prediction batch live in production?" — equivalent to MLflow's run-tracking, in a single Postgres table.

---

**Trim rationale + deferred-with-rationale list**

Group C scope was intentionally trimmed from the original spec to keep the lota focused on the parts that pay off immediately. Deferred items are sequenced for clear later sessions:

| Deferred | Where it lands | Why now-not |
|---|---|---|
| `model_metrics` table | /heilsa session | Feeds the dashboard directly; building both together keeps the schema/UI co-evolution tight |
| `backup_manifests` table | /heilsa session | Same — dashboard consumer drives the schema |
| `migrations_log` table | /heilsa session | `supabase_migrations.schema_migrations` is canonical today; this is a metadata sidecar (applied_via, sanity_passed, rollback_path) that only helps when /heilsa shows it |
| `push_precompute_to_supabase` helper | After 2-3 proven run_monthly cycles | Monthly cadence + bank-facing app = high cost of an automated-push regression. The unnest_upsert pattern is in place; per-table column-type maps + ON CONFLICT keys land when the wrapping orchestration is empirically stable |
| `ats_lookup` → `ats_lookup_by_heat` rename | Next ats-touching migration | Cosmetic; would burn a migration cycle for ~no value standalone |
| `/heilsa` internal dashboard | Separate session after Group C | PLANNING_BACKLOG already sequenced; consumes Group C tables |
| iter5 retraining + `run_retrain.py` | iter5 spec session | Retraining is event-driven (drift > threshold), not monthly |
| `predictions.predicted_at: DATE → TIMESTAMPTZ` | iter5 session | Orthogonal; lands cleanly with iter5's re-scoring-cadence decision |
| Bug 26 SSR-deep-link closure | Separate UI session | Group B/C did not address; `augl_id_latest` remains in anon allowlist for the view |
| Lighter dashboard-only refresh decoupled from monthly cycle | Forward option, gated on near-daily kaupskrá publication being confirmed sustained | Enabled by kaupskrá cadence revision below; build after run_monthly has 2-3 clean cycles |

---

**Halt-before-push design**

`scripts/run_monthly.py` produces the precompute CSVs and an inputs_snapshot row, then prints a per-table push-preview (CSV-rows vs live-Supabase-rows delta) and exits with `pipeline_runs.exit_status='success_halt_pre_push'`. Operator reviews and decides whether to push. `--push` flag is wired in the CLI but returns exit 2 with a "not implemented this lota" message.

Reasoning:

1. **Monthly cadence**: a botched auto-push wouldn't be noticed until the next cycle a month later. Manual review window is essentially free in operator-time terms.
2. **Bank-facing application**: properties + predictions are read by /eign render path. A bad row count or stale predictions visible immediately. The halt-before-push gives a deliberate "do these numbers look right?" gate.
3. **Pattern is already known**: phase_d3_apply demonstrated the unnest_upsert idempotent INSERT path. Generalising it across 7 precompute targets requires per-table {column_types, conflict_cols, casts} maps — small but should be done once we've watched the orchestrator behave through 2-3 monthly cycles. Premature automation would lock in column-type maps before knowing what edge cases the cycle surfaces.

Decision lock: **flip to auto-on-all-green only after 2-3 proven cycles** demonstrate the orchestrator's halt-gate fires correctly on real drift (validate_metrics MAPE/coverage thresholds, kaupskrá file-shrinkage, training-data row drift > 10%). Until then, push is manual.

---

**Audit-table security posture**

All 3 tables follow the same pattern, consistent with Group B's least-privilege posture:

```sql
ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;
-- No CREATE POLICY — default-deny for anon and authenticated.
-- service_role bypasses RLS via its built-in role membership.
REVOKE ALL ON public.<table> FROM anon;
REVOKE ALL ON public.<table> FROM authenticated;
```

Verified post-apply: each table has `relrowsecurity=t`, 0 anon SELECT grants, 0 authenticated SELECT grants, and a fresh `service_role` SET LOCAL ROLE returns `count(*)=0` cleanly (no 42501). Orchestrator writes come from the service-role connection (`.dbconfig` URL is the postgres role, which has BYPASSRLS in Supabase managed Postgres).

When /heilsa lands, it reads via a Next.js API route using `SUPABASE_SERVICE_ROLE_KEY` (never anon). The dashboard route will be unlinked + auth-gated per PLANNING_BACKLOG.

---

**Pre-flight rollback exercise (worth recording)**

First apply caught a **verifier miscount bug**: `apply_group_c_migration.py` had expected column counts of 7/11/16, while actual schemas are 8/12/20 (I miscounted from the SQL while writing the verifier — pipeline_runs has 8 cols not 7, etc.). The verify step returned all 3 tables as FAIL on column count.

The script's auto-rollback path fired: `DROP TABLE public.inputs_snapshots, public.pipeline_steps, public.pipeline_runs CASCADE` in a single statement. Clean rollback — no residual state. Fixed the expected-counts dict in the verifier, re-ran apply, all checks green on second attempt.

**Empirical precedent**: the rollback path actually works in practice — DROP TABLE × 3 CASCADE on a fresh migration is a clean recovery. Useful to have demonstrated this on net-new tables (no FK conflicts to other live data, all 3 tables empty at rollback time). For future migrations that mutate existing schema, the rollback path is more complex; this exercise establishes the simpler additive-migration case as a known-good pattern.

The pattern: **verifier mistakes are recoverable when the migration is purely additive and the rollback is DROP TABLE on the net-new objects**. For migrations with REVOKE/GRANT changes (like Group B), the rollback path is re-GRANT table-level — also additive in the recovery direction.

---

**CORRECT THE RECORD — two corrections**

**(a) Kaupskrá publication cadence — revised**

The 2026-04-20 STATE Áfangi 4d note ("Monthly update pattern: Sunnudagur 2. viku mánaðar ~02:00 GMT") is **stale**. Empirical state observed 2026-05-27:

- HMS HEAD-probe today: `Last-Modified: Wed, 27 May 2026 02:00:53 GMT`
- State-file last-recorded fetch: `Mon, 20 Apr 2026 02:00:36 GMT`
- 37-day gap in local artifact, but Danni's observation in late May 2026 is that publication is **now near-daily**

Publication-time-of-day (~02:00 UTC) remains stable; only frequency changed.

**Limitation of the local artifact**: `D:\kaupskra_fetch_state.json` is single-snapshot — it overwrites itself each fetch, so we cannot reconstruct full publication history from local data alone. The cadence revision is based on operator observation; the in-script HEAD probe today is the only empirical anchor. STATE Áfangi 4d updated additively (+6 lines: "Cadence revision 2026-05-27" sub-block).

**Forward option** (do NOT build now, noted in STATE Áfangi 4d): once Group C's run_monthly is proven over 2-3 cycles, a lighter dashboard-only refresh decoupled from the heavy monthly recalibration cycle could trigger daily on Last-Modified change — pickup latest sales → repeat_sale_index + ATS lookup refresh, without re-training. This is gated on (a) sustained near-daily publication being confirmed, and (b) operational confidence in the monthly cycle.

**Implication for run_monthly cadence**: decoupled from publication day. `refresh_kaupskra.py` is idempotent on Last-Modified/MD5 (HEAD → no-op when unchanged), so any convenient day works. **Pinned**: 1st of each month 03:30 local (post nightly R2 backup at 03:00) — operator convenience, not a HMS dependency.

**(b) Hetzner + Dagster + MLflow plan — superseded**

`STATE.md:1051` (historical, from initial planning ~spring 2026) specified the infra stack as:

> "Infra stack = Hetzner + Postgres/PostGIS + Docker Compose + Dagster + MLflow + Cloudflare R2."

Reality: the platform has been running ~6 months on **Vercel (Next.js app) + Supabase (Postgres data layer) + local Windows D:\\ Python 3.14 (training pipeline) + Cloudflare R2 (backups)**. The Hetzner/Dagster/MLflow leg never landed. Project has shipped and grown without it.

**Decision lock**: Group C IS the lightweight current-stack version of what Dagster + MLflow would have provided. Standing up Dagster/MLflow now would be 2-4 weeks of infrastructure work for marginal value — the training set is ~144K rows (~10 min/cycle on a laptop), the monthly cadence is small-scale, and the team is small. Revisit if the project scales 10× (multi-engineer, multi-tenant data, hourly retraining).

Specifically:

- `pipeline_runs` + `pipeline_steps` provide Dagster's run-orchestration audit trail in a Postgres table.
- `inputs_snapshots` provides MLflow's run-tracking (model_version, input MD5s, parameters, environment) in a Postgres table.
- `scripts/run_monthly.py` is the orchestrator (Dagster job in MLflow terms).
- Windows Task Scheduler is the cron (same role as Dagster scheduler / Airflow DAG sensor).
- Cloudflare R2 + nightly rclone backup is the artifact store (MLflow artifacts equivalent).

The line in STATE.md is left for historical context — it documents the path-not-taken. This DECISIONS entry is the canonical statement of the superseding decision.

---

**Migration-history caveat**

Migration file `20260527155123_group_c_audit_tables.sql` is on disk under `supabase/migrations/` but was applied via `psycopg2` in `scripts/apply_group_c_migration.py`, not the Supabase CLI. The remote tracking table `supabase_migrations.schema_migrations` does NOT yet include version `20260527155123`. To register it:

```powershell
D:\verdmat-is\tools\supabase\supabase.exe migration repair --status applied 20260527155123
```

Same pattern as Group B (2026-05-27 second DECISIONS entry) and as the 2026-05-21 baseline reconcile. Requires interactive TTY, which is why the agent shell cannot execute it directly. **Does NOT block the commit** — disk file belongs in the repo regardless.

---

**Open follow-ups (sequenced)**

1. CLI repair `20260527155123` (Danni's PowerShell step).
2. First manual `run_monthly.py` clean run (no --dry-run) — observe end-to-end behavior, particularly the validate_metrics drift gate and the push-preview deltas.
3. After 2-3 proven cycles: register Windows Task Scheduler for monthly orchestrator + flip `--push` to auto-on-all-green; build `push_precompute_to_supabase` per-table maps.
4. /heilsa dashboard session — builds `model_metrics` + `backup_manifests` + `migrations_log` tables alongside the unlinked auth-gated UI.
5. Lighter dashboard-only refresh (forward option) once kaupskrá near-daily cadence is confirmed sustained.
6. `ats_lookup` → `ats_lookup_by_heat` rename when next ats-touching migration lands.
7. iter5 retraining spec + `run_retrain.py` orchestrator + `predicted_at` DATE→TIMESTAMPTZ.
8. Bug 26 SSR-deep-link closure (remains separate UI session).

---

**Artifacts (þessi lota)**

- `scripts/migration_helpers.py` — 7 helpers + 3 utilities, 291 lines
- `scripts/run_monthly.py` — orchestrator with halt-before-push, 302 lines
- `scripts/backfill_current_snapshot.py` — one-off anchor writer, 146 lines
- `scripts/apply_group_c_migration.py` — apply + verify + auto-rollback orchestrator
- `supabase/migrations/20260527155123_group_c_audit_tables.sql` — 3 tables + 6 indexes
- `scripts/{apply_column_grant_lockout, phase_d1_apply, phase_d3_apply}.py` — additive header-note pointers to migration_helpers (no working-code changes)
- `docs/STATE.md` — Áfangi 4d cadence revision + new milestone + Roadmap update + Group A+B+C closure
- `docs/DECISIONS.md` (this entry)
- `audit/monthly_runs/` (gitignored) — local JSON run-logs

---

## 2026-05-27 — Phase X Group B column-grant lockout APPLIED; default-deny på future columns; Bug 26 reframed (not closed)

**Hvað**: Phase X Group B follow-up landed live á Supabase prod (project `szzjsvmvxfrhyexblzvq`). Replaced table-level SELECT grants on the 4 in-scope tables with column-level allowlists per role. Each migration in its own transaction; sanity green after each.

**Migrations** (in `supabase/migrations/`):

- `20260527150435_column_grant_lockout_stage1_properties.sql` (2.677 bytes) — STAGE 1, `public.properties`.
- `20260527150436_column_grant_lockout_stage2_other3.sql` (2.695 bytes) — STAGE 2, `public.predictions` + `public.repeat_sale_index` + `public.ats_lookup` (each in its own BEGIN/COMMIT).

Applied via `psycopg2` through the transaction pooler (Docker / `supabase db push` unavailable on this host per 2026-05-21 Group B Part 1 entry). **Tracking caveat below**.

**Per-table allowlist**:

| Table | anon = authenticated | Excluded (anon CANNOT SELECT) |
|---|---|---|
| `properties` | **44** cols: 43 v_properties-projected + `deregistered` (WHERE) | `landeign_nr`, `matseiningar`, `tengd_stadfang_nr` |
| `predictions` | **12** (all, = v_current_predictions projection) | (none) |
| `repeat_sale_index` | **15** (all, = v_repeat_sale_index projection) | (none) |
| `ats_lookup` | **15** (all, = v_ats_lookup_by_heat projection) | (none) |

**Role split**: `authenticated = anon` for now. `/pro` is a frozen static landing page; no pro feature currently exercises `authenticated` for these 4 tables. Revisit on pro reactivation — likely candidates for an expanded authenticated set are `matseiningar` (sub-unit drill-down) and `tengd_stadfang_nr` (cross-property comp). Documented as backlog.

**Sanity (under `SET LOCAL ROLE anon`)**:

- `SELECT count(*) FROM v_properties` → **232.790** = baseline ✓
- `SELECT count(*) FROM v_current_predictions` → 167.503 = baseline ✓
- `SELECT count(*) FROM v_repeat_sale_index` → 2.673 = baseline ✓
- `SELECT count(*) FROM v_ats_lookup_by_heat` → 65 = baseline ✓
- `SELECT landeign_nr FROM properties LIMIT 1` → **42501** `permission denied for table properties` ✓
- `SELECT matseiningar FROM properties LIMIT 1` → 42501 ✓
- `SELECT tengd_stadfang_nr FROM properties LIMIT 1` → 42501 ✓
- `SELECT augl_id_latest FROM properties LIMIT 1` → **PASS** (intentional, see Bug 26 reframe below)

**Final grant state**:

| Table | anon table-level | anon column-level |
|---|---:|---:|
| `properties` | 0 | 44 |
| `predictions` | 0 | 12 |
| `repeat_sale_index` | 0 | 15 |
| `ats_lookup` | 0 | 15 |

**Full prod smoke** — 11 routes, all HTTP 200, 0 PostgREST 42501/42703 errors:

`/` · `/eign/2008647` (Group-B scored baseline) · `/markadur` + 4 sub-pages · `/api/backproj/2008647` · `/eign/2151573` (D3 scored net-new) · `/eign/2019479` (D3 held net-new) · `/api/search?q=Vesturs`. Sizes within ±5% of 2026-05-21 Group B Part 2 baseline. Deep verify on `/eign/2151573`: "Verðmat í dag" PredictionCard renders 36,7 M kr point + 80% PI [30,3; 44,4] M + 95% PI [25,4; 53,0] M + iter4_final_v1 / iter4_conformal_v1 / APT_FLOOR stamp ✓. `/eign/2019479` held: graceful state + "Verðmat bíður" chip ✓.

---

**CORRECT THE RECORD — two prior-entry inaccuracies surfaced during this audit**

1. **`search_properties_grouped` is invoker-mode, NOT SECURITY DEFINER.** The 2026-05-21 Group B Part 2 entry stated "SECURITY DEFINER RPCs (`search_properties_grouped`) keep working under either path" — that was wrong. `pg_proc.prosecdef = False` empirically. The function uses the default invoker mode and reads `public.properties` directly with anon's privileges. The audit revealed this; the empirical column footprint is 7 cols — `heimilisfang`, `postnr`, `postheiti`, `sveitarfelag`, `fastnum`, `tegund_raw`, `is_residential` — ALL of which are in the 44-col anon allowlist on `properties`. So the function survived REVOKE+GRANT without an RPC-side change (confirmed: `/api/search?q=Vesturs` returns Vestursíða 10 group anchors post-lockout). If a future column gets added to its body and is NOT in the allowlist, the RPC will start 42501-ing — standing rule below applies.

2. **This lockout does NOT close Bug 26 (`fastnum ↔ augl_id` leak).** The 2026-05-21 entry left Bug 26 in a re-scoped-but-undone state ("SSR deep-link href via service-role key"), and Bug 26 closure could be misread as a side-effect of the column-grant work. It is NOT. `augl_id_latest` is **intentionally retained in the anon+authenticated allowlist** on `properties` because (a) `v_properties` projects it, so removing it from base-table grants would 42501 the view, and (b) Bug 26 fix is a UI-side change (render the deep-link href in server-rendered HTML with the service-role key; never ship `augl_id_latest` to the client bundle). That UI change is a separate task. **Closing it remains open work.**

---

**Standing rule (locked)**

Any new column added to `public.properties` / `public.predictions` / `public.repeat_sale_index` / `public.ats_lookup` that needs to be projected by a `v_*` view MUST also receive a matching `GRANT SELECT (<col>) ON <table> TO anon, authenticated;` in the same migration that adds it. Otherwise the view's SELECT (or its WHERE-filter, ORDER BY, etc.) will fail with PostgREST `42501 permission denied`.

Conversely, **omitting** a new column from both the view projection and the grant is the new default — that's the "default-deny on future columns" value this lockout delivers.

This rule applies equally to:
- Adding a column to a base table where a `v_*` view does `SELECT *`-style projection (currently none — all 4 views use explicit projection lists, which is the recommended pattern).
- Adding a column to a `v_*` view definition that wasn't previously projected.
- Changing a `v_*` view's WHERE/ORDER BY/JOIN clause to reference a previously-unreferenced base-table column.

When in doubt: run the proposed view migration locally, then under `SET LOCAL ROLE anon; SELECT count(*) FROM <view>;`. If it 42501s, the column-grant is missing.

---

**Value delivered**

| | Before lockout | After lockout |
|---|---|---|
| anon SELECT on `properties` | all 47 cols (incl. `landeign_nr`, `matseiningar`, `tengd_stadfang_nr`) | 44 of 47 (3 excluded) |
| anon SELECT on `predictions` | all 12 | all 12 (no behavior change) |
| anon SELECT on `repeat_sale_index` | all 15 | all 15 (no behavior change) |
| anon SELECT on `ats_lookup` | all 15 | all 15 (no behavior change) |
| Default behavior on future column add | anon can SELECT immediately | anon must wait for explicit GRANT (default-deny) |

The 3-col exclusion is the immediate visible win; the default-deny posture is the durable win — it prevents accidental column leaks the next time someone adds a column to one of these tables.

---

**Migration-history tracking caveat**

Both migration files are recorded in `supabase/migrations/` on disk, but the remote tracking table `supabase_migrations.schema_migrations` was NOT updated during the apply because we used `psycopg2`, not the Supabase CLI. Verified empirically post-apply: `SELECT version FROM supabase_migrations.schema_migrations WHERE version IN ('20260527150435','20260527150436')` returns **0 rows**.

**Fix**: run the following in a real PowerShell terminal (CLI needs interactive TTY, not available inside this agent shell):

```powershell
D:\verdmat-is\tools\supabase\supabase.exe migration repair --status applied 20260527150435 20260527150436
```

This is the same pattern used in the 2026-05-21 Group B Part 1 baseline reconcile. It writes the two version-ids into `schema_migrations` with `status='applied'` so that future `supabase db push` runs and `supabase migration list` correctly show the lockout migrations as applied — no `db push` re-runs them and no drift warnings. **This does NOT block git commit / push — the disk files belong in the repo regardless; the repair fixes the remote tracking table in parallel.**

**Anti-pattern to avoid**: hand-inserting into `supabase_migrations.schema_migrations` via SQL. The CLI repair command computes the `statements` payload correctly; manual INSERT would leave the column NULL (or wrong) and break future `supabase db diff` comparisons. Use the CLI command, not raw SQL.

---

**Artifacts (þessi lota)**:

- `supabase/migrations/20260527150435_column_grant_lockout_stage1_properties.sql`
- `supabase/migrations/20260527150436_column_grant_lockout_stage2_other3.sql`
- `scripts/apply_column_grant_lockout.py` — apply orchestrator with per-stage sanity gates (baseline counts, anon view-count match, 42501-exclusion proof on each excluded column, anon-SELECT-pass on `augl_id_latest`)
- DECISIONS.md (this entry) + STATE.md milestone demotion + Roadmap update

---

## 2026-05-27 — Phase D3 NOW lota APPLIED; Spatial-NN matsvaedi backfill sanctioned; predictions decoupled from evalue augl-pass

**Hvað**: Phase D3 NOW lota landed live á Supabase prod (project `szzjsvmvxfrhyexblzvq`). Þrír idempotent INSERT blokkar runnu án villu og post-apply row-counts matchuðu dryrun-spá nákvæmlega:

| Block | Inserted | New universe | Idempotency |
|---|---:|---|---|
| `properties` | **108.052** | 124.835 → **232.887** | `ON CONFLICT (fastnum) DO NOTHING` · 0 collisions |
| `sales_history` | **786** (487 arm's-length + 299 onothaefur=1) | 173.081 → **173.867** | fastnum-existence pre-check (no PK on fastnum) |
| `predictions` | **57.187** | 110.316 → **167.503** | `ON CONFLICT (fastnum) DO NOTHING` · 0 PK collisions |

**Predictions stamp**: allar 167.503 rows í `predictions` eru `model_version='iter4_final_v1'` / `calibration_version='iter4_conformal_v1'` — engin blönduð útgáfu-stamp, `v_current_predictions` `DISTINCT ON (fastnum)` og footer-badge haldast stöðug.

**Phase A 2.059 inclusion (frávik frá ~106K prompt)**: insert-universe varð **108.052**, ekki ~106K sem Danni nefndi í prompt-i. Það er vegna þess að Phase A 200 (2.059 net-new HMS-only fastnums frá kaupskrá-only + wide-gap candidates) tilheyrir original D3 scope per DECISIONS 2026-05-18 ("30.193 = Phase A 2.059 + Phase C 28.134"). Allir þrír buckets (Phase A 200 / Phase C 200 orig / Phase C 200 reprobed) eru disjoint via single-probe argument (fastnum INTEGER PRIMARY KEY í `hms_archive_staging.db`). Empirically staðfest í dryrun: 0 collisions við existing Supabase `properties`.

---

**Spatial-NN matsvaedi backfill — sanctioned reusable path fyrir HMS-only properties**

Vandamálið: HMS API payload-ið inniheldur EKKI `matsvaediNUMER`. Existing 124.835 Supabase rows fá matsvaedi úr `properties_v2.pkl` sem var byggt úr `Gagnapakkar/fasteignir{,1-4}.db` `data_json` — þ.e. **evalue augl payloads**. Net-new D3 candidates eru að defininsion fastnums sem evalue hefur aldrei haft (Phase B var existing-Supabase set; Phase A+C eru utan við þá), svo enginn direct-lookup væri fyrir hendi: af 108.052 D3 fastnums fundust 476 (0,44%) í scrape-DBum og þeir voru allir `status=204` (ekki í evalue index, no matsvaedi gögn).

Naive blanking (matsvaediNUMER = NaN + bucket = `P{postnr}_other`) reyndist statistically dishonest:

- Ablation á 3.000-row training-sample (sami iter4a + conformal scorer): **51,2% PI80 breach, 22,0% PI95 breach**, mean +3,83% nominal bias, std 0,239 log. Country region versti með **+40,3% bias og 71,2% breach**.
- Fallback bucket `P{postnr}_other` matchaði aðeins 7,0% af training categories → 93% lentu í LightGBM categorical NaN (missing-branch); 326 distinct buckets aldrei séð í training.

Spatial k=1 nearest-neighbor solution:

- Byggja `scipy.spatial.cKDTree` á `geography_features.pkl` (124.835 labeled lat/lon → matsvaediNUMER, sales_2015 fyrir bucket rare-merge).
- Per net-new D3 fastnum með lat/lng: query k=1 → assign matsvaediNUMER + nn_distance_km.
- Hold-out validation (5K random points removed, re-assigned by NN from the rest): **k=1: 99,8% exact matsvaediNUMER match, 99,9% bucket match** (per-region uniform 99,8–99,9%). NN-distance distribution: p50 = 0 km (sami stadfang), p99 = 0,7 km — Ísland er nógu þétt-merkt að spatial inheritance er essentially exact.
- Re-ablation undir spatial-inferred matsvaedi á sömu 3.000-row training-sample: **0,0% PI80 breach, 0,0% PI95 breach**, mean delta_log = **−0,0000**, std 0,0009 — statistically indistinguishable frá full-feature regime.

**Threshold T = 1 km (0,009°)**, valið með **per-bin** logic (síðasta bin þar sem hold-out match-rate ≥98%): 300m–1km bin gaf 98,2%, 1–2km bin féll í 88,9% (n=18, small-sample noise en conservative read). T persisted á `D:\phase_d3_matsvaedi_T_deg.txt`.

D3 NN-distance transfer (102.209 with coords): p50 = 0,057 km, p90 = 1,36 km, p95 = 3,07 km. **89.689 within T (87,75% of those með coords)** — restin 12.520 beyond T held í confidence gate (mostly Country: 78,6% within; SFH_DETACHED 81,7%; SUMMERHOUSE 80,5%).

**Reusable path forward**: spatial-NN matsvaedi backfill via `scipy.spatial.cKDTree` á `geography_features.pkl` er nú sanctioned default fyrir hvers konar HMS-only properties sem land í Supabase post-D3 — D4 cross_property_refs, D5 photo_urls_json, framtíðarscrapes. Skref er kóða í `scripts/phase_d3_extract.py:load_matsvaedi_donor()` + `main()` post-pass.

---

**Honesty-vs-coverage trade**

Scoring funnel:

```
total D3 candidates              108.052
minus non-scorable (EXCLUDE)      42.439  → 65.613 residential+summer
  minus no byggar                  2.433
  minus matsvaedi-unconfident      5.993
= SCORABLE                                  57.187
```

5.993 matsvaedi-unconfident (mostly Country: 5.110 af þeim) + 2.433 no-byggar held til að halda `iter4_conformal_v1` PI-i empirically heiðarlegum (training-time empirical coverage 79,1% PI80, 94,6% PI95). 57.187 scored frekar en 63.180 sem v1 score-ið framleiddi án gate-ins — explicit accuracy-vs-coverage trade: **honesty trumps coverage**. Held rows fá samt full `properties` row með öllum HMS metadata (fasteignamat, brunabotamat, byggingarstig, matseiningar etc.) — bara engin iter4 prediction.

Verification: dryrun staðfesti 0 PI80 inversions og 0 PI95 nesting violations á öllum 57.187 scored rows (var 11.231/42.093 inversions í v1 með segment-stretch frekar en conformal).

---

**Decoupling: predictions no longer gated on evalue augl-pass**

POST_HMS_RECOVERY_PLAN §1-§5 átti upphaflega að keyra sekvensjellt: §1 evalue augl-pass (~28h single-worker, gated á G2 template-hardening) → §2 kaupskrá → §3 D3 promotion → §5 iter4 scoring. Spatial-NN backfill collapsar §1-§5 í einn hreinan apply: iter4 scoring fær matsvaedi spatially og þarf ekki að bíða eftir evalue.

LATER evalue lota er nú **UI-enrichment + held-row scoring**, ekki blocker:

- UI-enrichment: photo_urls_json, lysing_truncated, augl_id_latest, n_photos, first_photo_url, scraped_at_latest fyrir 108K net-new (þau hafa öll `NULL` í Phase D3 INSERTs).
- Held-row scoring: matsvæði + byggar fyrir 8.426 held rows (5.993 unconfident + 2.433 no-byggar) → scoring eftir á.
- Production-template hardening (G2) er enn pre-req fyrir evalue lotuna sjálfa (stage_a_augl_refresh.py resume retry-on-non-(200,204)), en *ekki* lengur fyrir prediction surface.

---

**UI: held-residential graceful state**

Áður var `/eign/[fastnum]/page.js` aðeins með tvær branchur fyrir prediction display:

- `!property.is_residential` → "Verðmat er ekki í boði fyrir þessa eign" (non-residential notice — applied á EXCLUDE properties).
- `property.is_residential && prediction` → `<PredictionCard>` render.

Þriðja sviðið (is_residential=true + no prediction) var **engin branch** — leiddi til blank space milli hero og SHAP sections. Þetta var aldrei áður mögulegt (existing 14.519 properties án predictions í dag eru ALLAR EXCLUDE), en með D3 verður þetta nýtt UI state fyrir 6.173 held residential + 2.253 held SUMMERHOUSE = 8.426 rows.

Bætt við í þessari lotu (`page.js` line 287–319):

```jsx
{property.is_residential && !prediction && (
  <section className="vm-card vm-card-elevated" style={{ ..., borderTop: "3px solid var(--vm-neutral)" }}>
    <div>Verðmat bíður</div>
    <h2>Verðmat liggur ekki fyrir þessa eign</h2>
    <p>Eignin er nýskráð í gagnasafni verdmat.is en ekki nægileg módel-gögn liggja fyrir
       til að reikna áreiðanlegt spá-bil (oftast vantar matsvæðis-staðsetningu með nógu
       nálægum systur-eignum eða byggingarár). Spá birtist um leið og næsta líkanaþjálfun
       er keyrð með uppfærðum gögnum.</p>
  </section>
)}
```

Styled like the existing non-residential notice. Verifecerað via curl (`/eign/2019479` — Sigtún 30, RVK_core APT_FLOOR, no byggar): graceful state renderar; PredictionCard absent. SCORED case (`/eign/2151573` — Vestursíða 10): PredictionCard renderar, graceful state absent. COORDLESS case (`/eign/2536633` — Breiðimelur): hero renderar, map section gated absent. Autocomplete (`/api/search?q=Vesturs`): net-new heimilisfang surface-ar via group-anchor.

---

**Protocol lesson — data-ahead-of-frontend window**

Lota þessi opnaði stuttan glugga þar sem prod Supabase var komin með 6.173 held residential rows en `page.js` graceful-state fixið var local (commit + push kom á eftir). Live `/eign/<held-fn>` síður rendered the blank gap fyrir nokkrar mínútur þangað til Vercel re-deployed main eftir push. Stuðningstap var minimal vegna þess að net-new fastnums voru aldrei áður indexed af search engines og hafa lágan organic traffic, en pattern-ið er still wrong.

**Regla locked**: data apply í prod Supabase sem **introducer nýja frontend state** (vs only adding rows til existing rendered branches) þarf að ship-a frontend handling **fyrir eða atómískt með** data-inu. Konkretasta path-ið:

1. PR-a frontend changes + merge til main + láta Vercel deploy → confirm deployed.
2. Þá keyra data apply.

Eða atómískt:

1. Stage frontend changes + run data apply.
2. Push frontend immediately eftir apply success í sömu lotu (þ.e. without breaking for review/halt í gegnum push).

Þessi lota fylgdi blönduðu pattern-i: vissi um held-residential nýja state-ið mid-session (eftir dryrun, fyrir apply), bætti við frontend handlingu mid-session, en push-aði ekki fyrr en eftir apply + verify (3-4 mín gap). Acceptable í þetta sinn af því (a) net-new fastnums hafa lítinn organic traffic, (b) gap-ið var stutt, og (c) verify-aðferðin krafðist live Supabase state. En þetta var meðvitað risk, ekki rétt pattern.

Næsta sinn: ef frontend fix er einföld og þekkt fyrirfram (eins og þetta — addition á þriðju branch í eign-síðu), push fyrst, þá apply.

---

**Artifacts (þessi lota)**

- `scripts/phase_d3_extract.py` — properties extract með Stadfangaskra lookup + spatial-NN matsvaedi backfill
- `scripts/phase_d3_sales_extract.py` — sales filter úr kaupskra.csv + CPI deflation
- `scripts/phase_d3_score_extract.py` — iter4 scoring með conformal PIs + confidence gate
- `scripts/phase_d3_dryrun.py` — 3-batch dryrun + collision + integrity + PI sanity + peer-comp spot-check
- `scripts/phase_d3_apply.py` — 3-batch idempotent apply
- `scripts/phase_d3_threshold_calibration.py` — per-bin hold-out match-rate + T calibration + D3 transfer check
- `scripts/phase_d3_matsvaedi_recoverability.py` — provenance + direct-lookup + spatial-NN hold-out + honesty re-check
- `scripts/phase_d3_matsvaedi_ablation.py` — blank-matsvaedi 3000-sample degradation diagnostic
- `app/eign/[fastnum]/page.js` — held-residential graceful state added
- `D:\phase_d3_*.parquet` + `D:\phase_d3_rollback.sql` — staging artifacts (gitignored under `D:\`, retained until next nightly backup confirms new state)
- `D:\phase_d3_matsvaedi_T_deg.txt` — persisted threshold (0,009°)
- DECISIONS.md (this entry) + STATE.md milestone demotion + Roadmap update

---

## 2026-05-26 — HMS full recovery COMPLETE; kaupskrá cross-check (99,18%) staðfestir completeness; D3-sync scope locked á ~106K insert-candidates

**Hvað**: `audit/hms_full_recovery.py` lauk eftir 74h 10m wall-clock (2026-05-21T20:58 → 2026-05-24T23:08 UTC). Endurspáði allar 392.026 HTTP-500 raðir staging-DB-ins gegn flat API með 1-retry hardening + outage-detection (sliding-window 100 → pause á <1% hit-rate). **Lokatölur**:

| Bucket | n | Notes |
|---|---:|---|
| recovered (var 500, núna 200) | **77.859** | +8,4% yfir spike-spá 71.803 (innan 95% CI 16,2–21,0%) |
| confirmed-still-500 (eftir retry) | 314.167 | upper bound á truly-empty Phase C slot-um |
| untouched | 0 | hreint completion, engin resume þörf |
| realized FN rate | **19,86%** | spike spáði 18,5% ± 3pp; landed +1,36pp ofan |
| WAF/outage pauses | 0 / 0 | outage-detector fór aldrei af stað (74h hreint) |

**Per-phase**: allar 77.859 recoveries úr Phase C. Phase A (6.838) + Phase B (97) **staðfestir genuine ghosts** — engin recovery þar. **Subset (a) un-ghost path = 0** (97 D2-ghostar re-probe-aðir, allir héldu áfram að skila 500 → ekta deregistered, ekki dead-zone false-negative á þekktum fastnum). Það ógildir refresh-path-inn í POST_HMS_RECOVERY_PLAN §4c: D3-sync er **hreint insert**, ekkert un-ghost UPDATE nema dryrun finni raunverulegan already-in-base case.

**Dead-zone breakdown (orsakavottun)**:

| Zone | recovered | confirmed-500 | FN rate |
|---|---:|---:|---:|
| Dead-zone (2026-05-16T07:00 → 17T21:00, ~38h) | 75.098 | 282.428 | **21,00%** |
| Healthy-zone (allt annað) | 2.761 | 31.739 | 8,00% |

**96,5%** af öllum recoveries komu úr dead-zone (75.098 / 77.859) — confirms root cause: WAF-backoff scoped to 429/403/503 EN EKKI 500 (`hms_full_scrape.py:226`). Healthy-zone 8% FN er hærra en spike pre-run estimate (4,6%) vegna þess að 866 v1-rolled-back raðir með yfirskrifað `fetched_at` flokkast nú healthy-zone (statistical noise 0,22%, flagged í `hms_recovery_report.md`).

**12-tíma FN rate stabilitet (74h run)**: 19,6% → 19,8% → 19,8% → 19,9% → 19,9% → 20,0% → 19,8%. Aldrei meira en 0,4pp frávik frá meðaltali. Fixed-rate sampling problem (1-in-5 af 500s var transient false-negative), ekki fluctuating.

**kaupskrá cross-check (óháð completeness-staðfesting)**:

| Metric | Result |
|---|---|
| kaupskrá unique fastnums | 126.362 (úr 226.481 sölum) |
| Til staðar í HMS-200 (post-recovery) | **125.330 (99,18%)** |
| Missing frá HMS-200 | 1.032 (0,82%) — all in HMS-500 bucket, none outside scrape span |

Sample probe (n=50 af 1.032 missing) gegn fresh HMS API + leit:

- 50/50 enn HTTP 500 (**ekki recovery-miss** — ekta gone)
- 15/50 stadfangur leysist í gegnum `leit?q=<address>` (líklega merged into sibling fastnum)
- 35/50 stadfangur skilar 0 fasteign match (heimilisfang hefur líklega breyst eða stadfang_nr endurraðað)

Pattern: clustered missing fastnums á sama heimilisfangi (t.d. Vatnsstígur 11: 3 sequential 2003253/2003257/2003260 frá 2010; Guðrúnartún 8: 2 atvinnuhúsnæði frá 2009). Ár-dreifing leans heavily 2006-2014 (75% af missing); 56 missing 2023-2025 staðfestir að þetta er ongoing churn, ekki bara legacy. **Túlkun**: 1.032 = ekta deregistered/merged properties (sameining/skipting eftir sölu), ekki scrape-vandi. Þekkt **repeat-sale takmörkun** — klofin söguskrá við sameining/skipting. **Valfrjáls Phase Y address-resolution** workflow (~1.032 leit-lookups, ~10 mín) gæti backfill-að `effective_fastnum` column ef historical-sale-continuity skiptir máli fyrir index. Frestað nema iter5 / BMN-index endurspái þurfi það.

**D3-sync scope locked**:

- **Insert candidates = recovered net-new (77.859) ∪ original Phase C 200-hits (28.134) ≈ 106K**. Disjoint via single-probe argument í POST_HMS_RECOVERY_PLAN §4a; staðfest við dryrun.
- Apply pattern: idempotent `INSERT INTO properties ... ON CONFLICT (fastnum) DO NOTHING`. Dryrun reports true net-new vs collisions.
- 1.032 kaupskrá-missing FNs **eru ekki insert-candidates** (þeir eru ekki HMS-200; við insert-um EKKI ghost-eignir).
- Universe post-D3-sync ≈ **~231K** = 124.738 base + ~106K Phase-C-real. Áður spáð ~227K; +4K vegna recovery overshoot (77.859 vs 71.700 spá).

**SPLIT gating på POST_HMS_RECOVERY_PLAN**:

Notandi sundrar §1-§5 niður í tvær óháðar lotur:

- **NOW (gated bara á recovery ✅)**: §3 properties insert + §3 sales_history insert + §5 iter4-scoring. Engin scraper-keyrsla, svo ekki háð template-hardening gate-inu (G2). Skilar Phase D3 ✅ + ~106K nýjar fastnum-síður live á `/eign/<fastnum>` með iter4 prediction.
- **LATER (gated á G2 template-hardening)**: §2 evalue augl-pass fyrir net-new subset (~71.7K, ~28h single-worker). Bíður þangað til canonical scraper-template er hardened. `feature_attributions` + `comps_index` follow í næstu precompute-cycle (precompute-driven, ekki per-fastnum).

**Næst (sjá STATE.md roadmap update)**: D3-sync (NOW lota) — properties+sales+scoring; svo Phase X Group B column-grant lockout; svo Phase X Group C.

**Artifacts (þessi lota)**:
- `audit/hms_full_recovery.py` — hardened runner (1 retry + outage detection + full envelope capture)
- `audit/hms_recovery_report.md` — final halt-report (77.859 / 314.167 / dead-zone breakdown)
- `audit/hms_recovery.log` — 74h append-only runtime log
- `audit/hms_recovery_status.md` — final status snapshot
- `audit/kaupskra_missing_from_hms.txt` — 1.032 missing kaupskrá FNs
- `audit/kaupskra_missing_probe_results.json` — n=50 sample probe outcomes
- `audit/hms_fn_spike.{py,md,sample.txt,results.json,run.log}` — pre-recovery spike artifacts (validated the strategy before 74h commit)
- DECISIONS.md (this entry) + STATE.md roadmap refresh

---

## 2026-05-22 — Evalue sibling-scraper audit (diagnostic): HMS bug class not present; coverage-coupling caveat surfaced

**Hvað**: Diagnostic-only audit (parallel lane to HMS recovery; no HMS files touched, no evalue network scrape beyond one positive-control probe). Inventoried 6 evalue scraper variants in `audit/`, static-reviewed each for the HMS bug class (HTTP-5xx misinterpreted as "fastnum doesn't exist"), temporal-bucketed the 124,835-row `audit/stage_a_augl_staging.db` for dead-zone clusters, and confirmed endpoint liveness with one positive-control POST. **Verdict: HMS bug class not present in any of the 6 evalue variants.** No sample re-probe justified.

**The 6 variants** (all under `audit/`):

| # | File | Role | Network |
|---|---|---|---|
| 1 | `stage_a_augl_refresh.py` | Production augl refresher (124,835 fastnums in the existing staging DB) | yes |
| 2 | `backfill_evalue_range.py` | Pilot scraper + shared core (`post_evalue`, `scrape_property`, `HaltSignal`) | yes |
| 3 | `backfill_evalue_probes.py` | Wraps #2 for 3 probe ranges | yes |
| 4 | `backfill_evalue_v3.py` | Wraps #2 for phases 2-4 + image downloads | yes |
| 5 | `backfill_preflight.py` | Read-only probe of 5 candidate sources | yes |
| 6 | `scrape_gap_diagnostic.py` | Wraps #2 for single-fastnum diagnostic | yes |

**Three independent evidence lines** for the "no HMS bug class" verdict:

1. **Static review** — None of the 6 variants conflate HTTP-5xx with "fastnum doesn't exist". Evalue has a distinct "not-in-index" signal (HTTP 200 + inner `status=204`), so the semantic ambiguity that bit HMS does not apply.
   - The pilot family (#2, #3, #4, #6) is **fail-loud**: any transient error path raises `HaltSignal` which stops the run. No silent-skip path exists.
   - `stage_a_augl_refresh.py` (#1) is **graceful but bounded**: rolling 5xx-rate halt over 100-request window, 1-strike halt on `cf-mitigated` / HTML / 403, 10-min sustained-net halt, and error rows persisted as `augl_status=-1` placeholder (distinguishable from real 200 rows).
   - `backfill_preflight.py` (#5) is read-only probe; records every status as a structured field.

2. **Temporal review** of `stage_a_augl_staging.db` (124,835 rows, span 2026-05-08T13:14 → 2026-05-13T22:34, 5d 9h) — **100.00% augl_status=200**, zero `-1` placeholders, zero NULL `augl_json`. Population-wide empty-rate (n_ads=0 ↔ latest_augl_iso IS NULL, perfectly correlated) = 52.72%. Per-6h windows across the run band tightly between 45.4% and 60.0% — no window crossed the 75% empty / 80% iso_null threshold. No outage signature.

3. **Manual probe** — One POST to `evalue.is/fastnum/2526172?/get_fasteign_augl` (positive control from `backfill_evalue_range.POSITIVE_CONTROLS`): HTTP 200, 2.11 s, application/json, no `cf-mitigated`, JSON parses, inner status 200, n_ads=2. Endpoint operating identically to the staging-run baseline.

**Leiguskra-scraper does not yet exist** — the 2026-05-21 DECISIONS line ("evalue.is backfill-skipti (×6) + leiguskrá-scraper — sami WAF-ignorar-500 mynstur líklega til staðar") was aspirational. No `leigu*`, `rental*`, or `rls_*` Python file under `audit/` or `scripts/` is a network scraper. Recorded so a future builder knows: when leiguskra is built, it must inherit the hardened canonical template (the post-HMS-recovery production-template), not a one-off implementation.

**Coverage-coupling caveat — the HMS recovery will surface fastnums that were never in the evalue input universe**:

`stage_a_augl_staging.db` contains exactly **124,835 rows = the Phase B input set** (every fastnum present in Supabase `properties` at run start on 2026-05-08, captured 2026-05-08 → 2026-05-13). The HMS full-scrape that finished 2026-05-18 added Phase C: a wider range sweep (2,000,044..2,547,000) which discovered ~30K HMS-only fastnums beyond the Phase B baseline. The HMS dead-zone of 2026-05-16/17 sits **inside** Phase C, and the ~71,800 fastnums currently being recovered by `audit/hms_full_recovery.py` are predominantly drawn from the Phase C range. **They were never offered to the evalue refresher.** Expected intersection of `recovered_fastnums ∩ evalue_staging` ≈ 0.

**This is not a bug in evalue's scrapers**. It is a downstream coverage consequence of the HMS bug — once HMS recovery completes and the ~71,800 net-new fastnums are confirmed real, those fastnums need a full data pass (evalue augl + kaupskrá lookup) before they can be promoted to Supabase `properties`. Recorded in PLANNING_BACKLOG as a post-HMS-recovery follow-up. **Do NOT run any evalue pass yet** — wait for HMS recovery to complete and yield the canonical recovered-fastnum set. Magnitude (|recovered ∩ evalue staging|) to be confirmed empirically post-recovery; expected near-zero.

**Latent (non-urgent) risk recorded for production-template hardening**: `stage_a_augl_refresh.py`'s resume logic uses `SELECT fastnum FROM stage_a_augl` to build its done-set, which would include `augl_status=-1` placeholders if any existed. If errors below the 5% halt threshold ever occur, those `-1` rows would never be retried on subsequent runs (silent-loss shape, same family as the HMS-resume issue this entry is responding to). **Has not fired** — current DB has 0 placeholder rows — but the path is there. Fold into the existing post-HMS-recovery "production-template hardening" backlog item: retry rows with `augl_status NOT IN (200, 204)` on resume; apply the same retry-on-resume discipline to the canonical scraper template so future scrapers (incl. leiguskra when built) inherit it.

**Artifacts (read-only, audit-script-first)**:
- `scripts/evalue_audit_schema_probe.py` — schema + cardinality
- `scripts/evalue_audit_temporal.py` — 6h-window bucketing
- `scripts/evalue_audit_single_probe.py` — single endpoint liveness probe

No DB writes, no HMS access, single non-batched network request total.

---

## 2026-05-21 — HMS full-scrape (2026-05-15 → 18) leyndi ~71.800 raunverulegum eignum vegna ~38 klst API-outage; gangsetjum full recovery

**Hvað**: Spike á `audit/hms_archive_staging.db` (random sample n=1.000 af 392.026 HTTP-500-röðum, seed=42) sýndi **18,5% false-negative rate (Wilson 95% CI 16,2–21,0%)** → áætluð **~71.803 raunverulegar eignir** vantar sem stendur í staging-DB-inu. 185/185 recovery komu á 1. tilraun — engin within-spike transient blip — sem þýðir að HMS-API-ið er stöðugt **núna** og að 500-svörin í scrape-window-inu voru *historical* server-side failure, ekki request-flake. Anchor 2226598 endurskilaði 200 á 1. tilraun, end-to-end sanity check stenst. Næsta skref: full recovery (option a í spike-report-inu) — re-probe allar 392K HTTP-500-raðir í gegnum `audit/hms_full_recovery.py` (nýtt skipt), endurnotanlegt, með outage-detection innbyggðu. Engar Supabase writes í þessari lotu.

**Why**: Notandi uppgötvaði 2226598 (Nóbýlavegur 14, Kópavogi) sýnilegt á `https://hms.is/fasteignaskra/115672/1022801/2226598` en staging-DB markaði hana `http_status=500, exists_in_hms=0`. Bein endurprófa via sömu `curl_cffi.chrome120` impersonation skilaði HTTP 200 með fullum payload. Þetta opnaði rannsókn á því hversu víðtækur missir væri. Step-0 (read-only timestamp clustering) sýndi tvo aðskilda dead-zone glugga; spike-network-probe staðfesti 18,5% recovery rate.

**Dead-zone gluggar (UTC, nákvæmir)**:

| Window | Start | End | Hours | Phase C 500s | Phase C 200s |
|---|---|---|---|---|---|
| DZ-1 (primary) | 2026-05-16T07:00:09 | 2026-05-17T06:59:47 | **23,99 klst** | 226.400 | 0 |
| Partial recovery | 2026-05-17T07:00:00 | 2026-05-17T08:59:59 | 2 klst | ~16.972 | ~2.028 (degraded: 20,5% → 1,1%) |
| DZ-2 (secondary) | 2026-05-17T09:00:00 | 2026-05-17T20:59:59 | **~12 klst** | 115.000 | 0 |

Heildar-degraded gluggi: **~38 klst** (2026-05-16T07:00 → 2026-05-17T21:00 UTC). Phase C 500-skipting: **dead-zone bulk ~355K**, **healthy-zone tail ~30K**. Spike-skipting per zone: dead-zone FN 19,8% (CI 17,4–22,5%) → ~70.432 recoverable; healthy-zone FN 4,6% (CI 1,8–11,2%) → ~1.370 recoverable.

**Root cause — WAF-backoff scoped to 429/403/503 EN EKKI 500**: `audit/hms_full_scrape.py:226` aðeins eykur `rate_limit_streak` á þessum þremur status code, og núllar streak-inn á öllu öðru (þ.m.t. 500). Backoff-logikkinn (`WAF_BACKOFF_STREAK=10` → 300s sleep) triggerast aldrei á sustained 500-flood. Scraper-inn keyrði beint í gegnum 9.200–9.600 fastnums á klst í ~38 klst með 0% hit-rate án þess að nokkurn tímann pása. Auk þess interpretar `1 if sc == 200 else 0` (sama skipti, lína 223) öll 500 sem `exists_in_hms=0` — engar retries, engin cross-check. **Tvíhliða galli**: outage er ósýnilegt, og einstök 500 eru þögult demoted-uð í "doesn't-exist". Saman skráðu þeir ~280K raunverulegar eignir sem doesn't-exist.

**Overturn — fyrri tilgátur sem þetta hrekur**:
- `audit/cross_source_probe_report.md` (2026-05-07) — Agent-driven exploration hélt að "HMS deprecated public JSON API". Phase B 99,9% hit-rate (124.738 / 124.835) staðfestir að API-ið er **lifandi**; spike staðfesti að það er stöðugt núna. Sú athugasemd byggði á hallucination af content í `audit/hms_dialogue_draft.md`. Ógilt.
- "97 ghost soft-flag" (D2 í Phase D, CLAUDE.md) — 97 Phase B 500s eru *líklega* raunverulegir ghosts (ekki transient á 18,5%/0,08% ratio), en það er tap á forsendu þangað til þeir eru endurprófaðir í recovery-keyrslunni.

**D3 scope reconciliation**: Phase D3 var áætlað sem "30K new-property insertion" í Supabase, byggt á þeim Phase C 200-hits (28.134) sem ekki voru þegar í `properties`. **Nýtt scope er ~75-100K** (28.134 staðfest + ~71.800 recovery). D3 verður frestað þangað til full-recovery klárast og `confirmed-genuine-500` tölur eru pinnaðar; þá fær Supabase-sync nýjan extract/dryrun/apply pattern (sjá `scripts/phase_d1_*.py` template).

**Hardening í `hms_full_recovery.py` (byggt núna, ekki retro-uppfært í `hms_full_scrape.py` ennþá)**:
- Skip `leit`-endpoint cross-check (spike: 0/815 leit-only recoveries — flat API einn dugar).
- 1 retry á 500/exception með 1s backoff (spike: 185/185 á 1. tilraun, en retry er ódýr insurance).
- **Outage detection**: sliding window af 100 nýjustu niðurstöðum; ef 200-rate í glugganum hrynur í <1% (vs expected ~18% recovery rate) → PÁSA 5 mín → endurprófa; ef areftir 100 → HALT + alert. Þetta fyrirbyggir að recovery-keyrslan endurskapi sömu villu ef fresh outage lendir.
- WAF backoff óbreyttur (429/403/503 streak ≥10 → 300s).
- Schema (tvær viðbætur við `hms_fasteign`):
  - `reprobed_at TEXT` — mismunandi: `reprobed_at IS NULL` = original-500 (frá scrape), `reprobed_at IS NOT NULL AND http_status=500` = confirmed-still-500 (frá recovery), `reprobed_at IS NOT NULL AND http_status=200` = recovered.
  - `full_response TEXT` — geymir allan API envelope-inn (`fasteignData` + `stadfangData` + `hasMultipleFasteignir`). Bætt við í v2 eftir uppgötvun að upprunalegi scraper-inn dropp-aði 2/3 af top-level keys.
- `fetched_at` er EKKI yfirskrifað á recovery-200 (preserved frá upprunalegri scrape). `reprobed_at` heldur recovery-tímanum sér.
- Resumable: target set = `WHERE http_status=500 AND reprobed_at IS NULL` — re-byggt við hverja gangsetningu.
- Polite rate: matching original (~157/min) með CONCURRENCY=3, PER_WORKER_DELAY=1.0s + jitter. Wall-clock estimate (með 1 retry á 81,5% cases): ~70 klst (~3 dagar).

**stadfangData uppgötvun (v2 amendment, 2026-05-21 ~20:50 UTC)**: HMS API-svarið hefur **þrjár top-level keys**, ekki bara `fasteignData` eins og upprunalegi scraper-inn gerði ráð fyrir:

```
{
  "fasteignData":         { ... fasteignamat, einflm, notkunareiningar[].matseiningar[].byggingarstig, ... },
  "stadfangData":         { stadfang: {stadvisir, postnumer_heiti_nf/tgf, ...},
                            fasteignir: [ FULL fasteignData fyrir ALLAR systur-fasteignir á sama heimilisfangi ] },
  "hasMultipleFasteignir": bool
}
```

Hver probe skilar **systur-fasteignum á sama stadfangi ókeypis** (t.d. 7 fasteignir undir Nýbýlavegi 14 fyrir 2226598-probe; 2 undir Fífurima fyrir 2040381-probe). Original scrape henti þessu öllu (`hms_full_scrape.py:184-190`: `j.get('fasteignData')`). Recovery v2 geymir núna ALLT envelope-ið í `full_response` column (~3,9 KB á row vs 1,6 KB fyrir bara `fasteignData`).

**Áhrif**:
- `byggingarstig` (B4 etc.) — alltaf í fasteignData.notkunareiningar[].matseiningar[].byggingarstig; **alltaf preserved í bæði fasteign_data og full_response columns**. Ekki týnt.
- `sérmetnar einingar` (= matseiningar nested innan notkunareiningar) — alltaf preserved í bæði columns. Ekki týnt. Dæmi: Móberg 1 jörð hefur 5 sérmetnar einingar (ræktað land, lax/silungsveiði, fjárhús, hesthús, hlaða) — allt geymt.
- `stadvisir`, `postnumer_heiti_nf/tgf`, systur-fastnums — NÝTT í recovery v2; vantar í upprunalegu 154.931 200-raðirnar frá Phase A/B/C.

**Asymmetric coverage post-recovery**: ~75K recovered rows hafa `full_response`; ~154K upprunalegu 200-raðir hafa aðeins `fasteign_data`. Þetta er meðvituð skuld sem verður greidd í **júní-byrjun rescrape** (sjá næstu kafla).

**Data-quality caveat — 866 raðir með yfirskrifað `fetched_at`**: v1-keyrslan (50 mín áður en stadfangData uppgötvun gerðist) hafði bug þar sem recovery-200 endurnýjuðu `fetched_at` í recovery-tíma. Þegar v1 var stöðvuð og 866 recovered raðir revert-aðar til http_status=500/reprobed_at=NULL, var upprunalegt `fetched_at` þeirra glatað (yfirskrifað 2026-05-21T20:08-20:55Z í stað þess að halda 2026-05-16/17 dead-zone tímabilinu). Áhrif: þessar 866 raðir munu birtast sem "healthy-zone" í lokaskýrslunni í stað dead-zone, þrátt fyrir að flestar þeirra séu úr DZ-1 (sást ~24% recovery rate í v1 sem matchar dead-zone hlutfallið). Statistical noise 0,22% af 392K populationinu; flagg-að í `hms_recovery_report.md` post-run.

---

**Júní-byrjun rescrape — plan til að loka asymmetric coverage gap-inu**:

Þegar recovery klárast (~2026-05-24), liggja fyrir tvö data-sets:
- ~154.931 upprunalegt 200-raðir með aðeins `fasteign_data` (engin `stadfangData`)
- ~75.000 nýleg recovered 200-raðir með bæði `fasteign_data` og `full_response`

Júní-rescrape (skipulagður fyrir byrjun júní 2026) mun:
1. **Bakfylla `full_response` á 154K upprunalegu raðirnar** — sömu `WHERE full_response IS NULL AND http_status=200` target set sem önnur recovery-keyrsla. Áætlað ~155K × 1.5s/row × 1.815 retries-fyrir-81,5% / 3 workers ≈ 24 klst (ódýrara en upphaflega vegna þess að flest 200-svör koma á 1. tilraun, engin retries).
2. **Refresh-a stale data** — `index_last_updated` í HMS-payloadinu er u.þ.b. 2026-05-15 fyrir flestar Phase B raðir; um 2-3 vikna gamalt í júní. Recovery v2 mun einnig pikka upp ný gildi (sérstaklega `fasteignamat`, `lhlmat` ef HMS hefur uppfært).
3. **Cross-check nýrri stadfangData** gegn `cross_property_refs` Phase D4 vinnu. Hver `full_response.stadfangData.fasteignir[]` er rich source fyrir address-clustering án viðbótar API-kalla.
4. **Production-template hardening** — `hms_full_scrape.py` skal vera retro-uppfært **áður en** júní-rescrape kviknar:
   - Capture full response (allir top-level keys)
   - Outage detection (sliding window 100 → pause + alert á <1% hit-rate)
   - 500-aware backoff (sustained 500s skulu trigger-a backoff, ekki bara WAF status codes)
   - Það "production-template hardening session" sem var út-of-scope hér er **kveikjandi fyrir júní-rescrape**.

Eftir júní-rescrape: 100% af 200-raðum hafa `full_response`, og Phase D4 cross_property_refs hefur fullbúið source-set.

**Decision-lock**: Júní-rescrape skal nota **sömu canonical template** og hms_full_recovery.py er að nota núna (eftir að retro-uppfærsla á `hms_full_scrape.py` hefur landað í eigin session). Engin tvíverknað á recovery + scrape mynstrum.

**Out of scope (eigin lota, hækkað í forgang)**:
- Sibling-scraper audit: evalue.is backfill-skipti (×6 í `audit/backfill_evalue_*.py` og fyrri pilots) + leiguskrá-scraper — sami WAF-ignorar-500 mynstur líklega til staðar.
- Production-template hardening: fold outage-detection + 500-aware backoff inn í canonical scraper-template (sem `hms_full_scrape.py` hefur framsemt eftir).

**Verification path (post-recovery)**: HALT-report frá `hms_full_recovery.py` skal innihalda **nákvæman recovered count** (ekki estimatið), dead-zone vs healthy-zone breakdown, og confirmed-genuine-500 count. Þá ákveður notandi Supabase-sync / D3 scope.

**Artifacts (þessi lota)**:
- `audit/hms_fn_spike.py` — spike runner (read-only)
- `audit/hms_fn_spike_sample.txt` — 1.000 sampled fastnums (seed=42)
- `audit/hms_fn_spike_results.json` — per-fastnum raw probe outcomes
- `audit/hms_fn_spike_report.md` — halt-report
- `audit/hms_fn_spike_run.log` — runtime log (94,7 mín wall-clock)
- `C:\Users\danie\.claude\plans\i-have-a-large-indexed-lynx.md` — plan file (spike scope)

---

## 2026-05-21 — Phase X Group B Part 2: views layer (security_invoker, anon/auth grants) + frontend switch

**Hvað**: Migration `20260521125751_views_layer.sql` added 4 read-only views — `v_properties`, `v_repeat_sale_index`, `v_ats_lookup_by_heat`, `v_current_predictions` — each declaring `WITH (security_invoker = on)` and granting SELECT to `anon` + `authenticated`. All 10 frontend `.from("properties" | "predictions" | "repeat_sale_index" | "ats_lookup")` call sites switched to the corresponding view (19 `.from()` replacements total). Next.js 16 production build clean; 8-route smoke (incl. `/eign/2008647`, `/markadur`, all four `/markadur/*` sub-pages, `/api/backproj/2008647`) returns HTTP 200 with sizes within ±5% of the 2026-05-06 verify baseline. **Bug 25 (Postgres 15+ view security_invoker discipline) is closed.**

**Why views, why now**: Postgres 15+ defaults views to security DEFINER semantics (run as view owner). With this default, any future RLS policy on the underlying table would be silently bypassed when read through a view — exactly the anti-pattern flagged for Áfangi 0 dependency in the 2026-05-06 RLS baseline audit (Bug 25). Declaring `WITH (security_invoker = on)` forces the view to evaluate with the calling role's permissions, so RLS policies apply as expected. Doing this proactively *before* any new RLS policies land closes the Áfangi 0 hardening dependency without touching policy logic. This entry locks the discipline: every future view in `public` must declare `security_invoker = on` explicitly.

**`v_properties` allowlist (43 of 47 columns)** — confirmed by HALT 2:

| Status | Columns |
|---|---|
| Include (43) | identity (`fastnum`, `heimilisfang`, `husnr`, `postnr`, `postheiti`, `svfn`, `sveitarfelag`); classification (`tegund_raw`, `canonical_code`, `unit_category`, `unit_family`, `is_residential`, `is_summerhouse`, `is_new_build`, `is_main_unit`); size & build (`einflm`, `lod_flm`, `byggar`, `fjherb`, `fullbuid`); geo (`lat`, `lng`, `matsvaedi_numer`, `matsvaedi_nafn`, `matsvaedi_bucket`, `region_tier`); HMS valuation (`fasteignamat`, `fasteignamat_gildandi`, `fasteignamat_naesta_ar`, `brunabotamat`, `lhlmat`, `byggingarstig`, `skodags`, `gerd`, `matsstig`); listing snapshot (`augl_id_latest`, `list_price_latest`, `effective_date_latest`, `scraped_at_latest`, `lysing_truncated`, `first_photo_url`, `photo_urls_json`, `n_photos`) |
| Exclude (4) | `landeign_nr` (unused by frontend; least-exposure default), `matseiningar` jsonb (Phase Z UI redesign will design its public surface), `tengd_stadfang_nr` jsonb (HMS staðfang cross-refs, Phase Y join-internal), `deregistered` (filter-redundant — view's `WHERE deregistered IS NOT TRUE` makes the column constant FALSE for visible rows; the 97 ghosts are hidden from public reads) |

`augl_id_latest` is **INCLUDED** despite Bug 26 (listing-id leak): exposing the `fastnum ↔ augl_id` bulk mapping via `anon` was already true on the underlying `properties` table — `v_properties` does not add new exposure. The Bug 26 fix is now re-scoped (and re-prioritised) to **server-side rendering the deep-link `href` with the service-role key**, NOT column-stripping. That is cheaper than a hashed-proxy approach and avoids reshaping the data contract. Tracked in PLANNING_BACKLOG.

**Spec corrections found during empirical sweep (HALT 2)**:
- `ats_lookup_by_heat` table does not exist in `public` schema. The view `v_ats_lookup_by_heat` wraps `public.ats_lookup` (the empirical name; 65 rows; this IS Table B from Áfangi 7). View name follows the doc-canonical "by_heat" used in the codebase. Optional underlying-table rename (`ats_lookup` → `ats_lookup_by_heat`) deferred to Group C.
- `public.predictions` has neither `scored_at` nor `property_id`. Actual key is `fastnum` (bigint), timestamp is `predicted_at` (DATE). `v_current_predictions` uses `DISTINCT ON (fastnum) ... ORDER BY fastnum, predicted_at DESC`. **Currently a no-op** — at iter4, predictions has exactly 1 row per fastnum (110,316 = count(DISTINCT fastnum) = total). Written forward-safe for the schema where multiple predictions per fastnum may co-exist.
- **Backlog note**: `predicted_at` as DATE is insufficient for robust latest-selection once history accumulates. Replace with `scored_at timestamptz` when iter5 ships (or sooner if a prediction-refresh cadence introduces same-day re-scoring).

**Verification (psycopg2 against linked DB)**:
- 4 views exist in `public`, all with `reloptions={security_invoker=on}` per `pg_class`.
- `information_schema.role_table_grants` confirms `SELECT` granted to BOTH `anon` AND `authenticated` on all 4.
- Row counts:
  - `v_properties` = 124,738 (= 124,835 properties − 97 ghosts) ✓
  - `v_repeat_sale_index` = 2,673 (= source table) ✓
  - `v_ats_lookup_by_heat` = 65 (= `ats_lookup`) ✓
  - `v_current_predictions` = 110,316 = `count(DISTINCT fastnum) FROM predictions` ✓
- Simulated `BEGIN; SET LOCAL ROLE anon; SELECT count(*) FROM <view>; ROLLBACK` returned the same counts for all 4 — confirms anon path works through views.

**Frontend switch (10 files, 19 replacements)**:
- `components/BackProjectionWidget.js` (2× properties)
- `components/SearchAutocomplete.js` (1× properties)
- `app/page.js` (1× properties + 1× predictions)
- `app/eign/[fastnum]/page.js` (3× properties + 1× predictions + 1× ats_lookup)
- `app/eign/[fastnum]/stilla/page.js` (2× properties + 1× predictions)
- `app/eign/[fastnum]/stilla/nidurstada/page.js` (1× properties + 1× predictions)
- `app/markadur/visitala/page.js` (1× repeat_sale_index)
- `app/markadur/modelstada/page.js` (1× properties + 1× repeat_sale_index)
- `app/api/adjust-valuation/route.js` (1× properties + 1× predictions)
- `app/api/backproj/[fastnum]/route.js` (1× properties + 1× predictions + 1× repeat_sale_index)

**Smoke test (production build + curl)** — sizes match 2026-05-06 verify ±5%:

| Route | HTTP | Size |
|---|---|---|
| `/` | 200 | 34 KB |
| `/eign/2008647` | 200 | 127 KB |
| `/markadur` | 200 | 43 KB |
| `/markadur/visitala` | 200 | 942 KB |
| `/markadur/markadsstada` | 200 | 1.1 MB |
| `/markadur/modelstada` | 200 | 37 KB |
| `/markadur/ibudir` | 200 | 821 KB |
| `/api/backproj/2008647` | 200 | 1 KB |

**Security note — what's NOT done in this session (intentional)**:
Underlying tables `properties`, `predictions`, `repeat_sale_index`, `ats_lookup` **still have direct anon + authenticated SELECT grants** from the 2026-05-06 RLS baseline audit. The 4-column EXCLUDE allowlist on `v_properties` defines the *intended* contract but is not yet *enforced* by grants — anon could still bypass the view by reading the table directly. A follow-up session (after deployed-frontend stability confirmation) will REVOKE direct SELECT from anon + authenticated on those 4 tables, leaving the views as the only public read path. The `SECURITY DEFINER` RPCs (`search_properties_grouped`) keep working post-REVOKE since they run as the function owner. Tracked in STATE.md Roadmap as "Phase X Group B follow-up". **Never REVOKE while live prod traffic may still hit table paths** — that would 401 every reader until the deploy lands.

**Locked rule going forward**: when adding a new public-facing column to `public.properties` (or any underlying table), the change MUST extend the corresponding `v_*` view in the same migration. `SELECT *` is forbidden in view bodies; an allowlist of explicit columns is the contract.

---

## 2026-05-21 — Phase X Group B Part 1: Supabase CLI baseline reconcile

**Hvað**: Reconciled local `supabase/migrations/` dir against remote `supabase_migrations.schema_migrations` via a fresh `pg_dump --schema-only -n public --no-owner` baseline, marked applied with `supabase migration repair --status applied 20260521125431`. The 7 pre-existing local files (`20260421_initial_schema.sql` through `20260518_hms_columns.sql`) moved to `supabase/_legacy_migrations/` (out of CLI's view, retained in git history for traceability). End state: `migration list` shows 1 local file = 1 applied baseline plus 11 historical remote-only entries that pre-date the baseline (harmless audit trail, no longer block `db push`).

**Af hverju**: Discovery (Step 1.2) revealed two-way drift from the MCP-applied period (2026-04-21 → 2026-05-18). Local dir had 7 files with short `YYYYMMDD` timestamps (one duplicate date — `20260422` ×2 for two unrelated changes); remote history had 11 long-timestamp entries from MCP `apply_migration` calls. Only 4 of 7 local files had clear remote content-twins (signature-line match: `20260423_dashboard_v1` ↔ `20260421222521`, `20260424_ats_lookup_by_quarter_and_regime_view` ↔ `20260424095108`, `20260422_search_properties_grouped_rpc` ↔ `20260422152141` plus 4 later evolutions, `20260518_hms_columns` ↔ `20260518111331`); 3 had no remote history row despite their effects being live (initial schema, `effective_date_latest`, RLS baseline audit). 7 remote-only entries had no local file at all (`model_tracking_null_segment`, `model_tracking_segment_nullable`, `latest_regime_per_cell_with_zscore`, `properties_prefix_indexes`, `search_rpc_simplify_inline`, `search_rpc_force_custom_plan`, `search_rpc_dynamic_sql`). File-by-file `migration repair --status applied` would have preserved the noise + duplicate-date locals + 7 invisible orphans; the baseline approach gives a faithful repo with one source of truth going forward. This is the foundational fix Group B was designed to deliver before any new migration (the views layer in Part 2) is pushed.

**Tooling decisions (one-off setup, persisted to user-level PATH)**:
- Supabase CLI v2.101.0 installed at `D:\verdmat-is\tools\supabase\supabase.exe` (scoop unavailable on this machine; direct binary download from GitHub releases per spec fallback, SHA-256 checksum verified against `checksums.txt`). Login via interactive browser flow (token cached locally; Claude never handled the token value).
- PostgreSQL 17 client tools (matches server's PG17.6 — pg_dump must equal-or-exceed server major) installed at `D:\verdmat-is\tools\postgres17\pgsql\bin\` (EDB binary-only zip, no installer / no service).
- Connection path for `pg_dump`: **session pooler on port 5432** (`aws-1-eu-north-1.pooler.supabase.com`, user `postgres.szzjsvmvxfrhyexblzvq`, same password as in `.dbconfig`). Transaction pooler (6543) does not support `pg_dump`'s protocol expectations; direct connection (`db.<ref>.supabase.co:5432`) is IPv6-only and unreachable from this host. The session-pooler URL is derived by swapping the port on the existing `.dbconfig` URI.
- Docker Desktop intentionally not installed. `supabase db diff --linked` and `supabase db reset` therefore unavailable; verification falls back to direct `psycopg2` SQL queries against the live DB (sufficient for additive view migrations in Part 2 — adds only, no destructive changes).

**Baseline sanity-check (`supabase/migrations/20260521125431_baseline.sql`, 47,533 bytes, 1,128 lines)**:
- All 11 HMS columns present in `public.properties`: `brunabotamat`, `lhlmat`, `fasteignamat_naesta_ar`, `byggingarstig`, `skodags`, `gerd`, `matsstig`, `landeign_nr`, `matseiningar` (jsonb), `tengd_stadfang_nr` (jsonb), `deregistered`.
- 18 tables with `ENABLE ROW LEVEL SECURITY` + 18 `CREATE POLICY` statements (matches the 2026-05-06 RLS baseline audit: 14 dashboard-public + 4 user-owned).
- 28 `TO anon` grants + 46 `TO authenticated` grants.
- 18 tables, 4 pre-existing views (`latest_regime_per_cell`, `regime_per_cell_monthly`, `repeat_sale_index_by_segment`, `repeat_sale_index_main_pooled`), 1 function (`search_properties_grouped`), 33 indexes.

**Locked rule going forward**: any new schema change MUST go through `supabase/migrations/` + `supabase db push`. MCP `apply_migration` (the original cause of this drift) is disallowed for schema work; reserve the MCP for read-only inspection only.

---

## 2026-05-20 — Phase X architecture sprint (post independent review)

Independent-Claude review of Phase D methodology ranked three fixes: Q6 (backup + 
reproducibility) → Q1/Q4 (sources of truth) → Q7 (views + migration CLI). Decision: 
execute as Phase X BEFORE Phase Y (D3-D5 data) and Phase Z (UI redesign) — UI 
redesign touches multiple components + new Supabase queries, so doing it on an 
unprotected/moving schema is risk multiplication. Phase X groups: A (backup + 
restore test + SOURCES_OF_TRUTH) ✅, B (Supabase CLI baseline + views layer), 
C (migration_helpers + audit tables + run_monthly + inputs_snapshots wiring).

---

## 2026-05-20 — Supabase canonical for HMS metadata

Supabase `properties` is canonical for HMS property metadata. properties_v2.pkl 
becomes a derived training cache, rebuilt by exporting the HMS slice from Supabase 
each training cycle. Resolves the split-brain from Phase D adding 11 HMS columns 
to Supabase not mirrored in the pickle. Full rationale in SOURCES_OF_TRUTH.md. 
Unblocks iter5. Follow-up logged: rebuild_training_data.py export step.

---

## 2026-05-20 — Backup architecture (R2 incremental)

Nightly backup of D:\ critical paths (excl. 352 GB images on CloudFront) to 
Cloudflare R2 via rclone sync + --backup-dir. current/ = live mirror, 
archive/<ts>/ = overwritten/deleted versions, 30-day archive retention. ~$0.20/mo. 
R2 over B2 (MCP convenience). Restore-tested 5/5. Staleness alert deferred to 
Group C run_monthly.py.

---

## 2026-05-18 — Phase D2: 97 ghost properties soft-flagged

97 properties returned HTTP 500 from HMS `/fasteignaskra/fasteign/{nr}` 
endpoint during weekend run Phase B (existing properties.fastnum sweep). 
All 97 had verified sales history in kaupskra (100% match), but HMS no 
longer recognizes them — most likely deregistered post-sale due to lot 
merging / fastnum renumbering. 3 of the 97 were sold in 2025, confirming 
this is active churn pattern, not historical dead records.

4 distinct ghosts × 6 rows present in training_data_v2.pkl (0,003% impact). 
Decision: soft-flag via `deregistered=true` in Supabase properties table. 
No retroactive training data rebuild — impact is trivial. Future 
rebuild_training_data.py runs should JOIN properties.deregistered and 
propagate flag into training data for downstream consumers (UI comparable 
display, scoring pipeline) to filter.

`deregistered` boolean column was added to properties schema in Batch 1 
(migration 20260518_hms_columns.sql). Default `false`. D2 sets `true` on 
the 97 ghost fastnums only.

---

## 2026-05-18 — Áfangi 0 Stage 1 weekend run completed — registry-completion thesis revised

**Hvað**: Two coordinated autonomous runs over 2026-05-08 → 2026-05-18 finished Áfangi 0 Stage 1 work. (1) Orchestrator (`weekend_run_orchestrator.py`) refreshed augl payloads for all 124,835 Supabase properties (`audit/stage_a_augl_staging.db`) and bootstrapped the image archive to 352.53 GB / 1,752,028 files at `D:\Gagnapakkar\images\` (canonical index `D:\Gagnapakkar\image_index.db`, 99.998% download success). (2) HMS full-scrape (`hms_full_scrape.py`, 58h 20m, 546,957 requests against `hms.is/api/fasteignaskra/fasteign/{nr}` via curl_cffi Chrome120 impersonation) ran sequential **Phase A → B → C**: backfill (kaupskra-only + 200-1000-wide gap ints, 8,897 requests, 2,059 hits at 23.1%), enrich (every existing Supabase fastnum, 124,835 requests, 124,738 hits at 99.92%), full-sweep (everything else in span 2,000,044..2,547,000, 413,225 requests, 28,134 hits at 6.81%). Total 154,931 HMS hits / 392,026 non-existent / 28.3% aggregate hit rate. **Result: 30,193 net-new HMS-only properties + 124,738 enriched rows + 97 deregistered ghosts.** All in staging; no Supabase writes performed.

**Af hverju**: Pilot v3 (2026-05-07/08, documented in prior project memory `project_registry_completion_thesis_collapsed.md`) had reported three small-sample probes against the registry-completion target ranges — trailing 5,000 candidates returned 2 hits, sub-gap 100 candidates returned 0, 2.4M bucket 400 candidates returned 0. The conclusion at the time was: "the missing 25K hypothesis no longer has a credible target range" and "session-after-next should NOT plan a multi-night registry-completion sweep". This weekend's Phase C ran the full sweep anyway as a completeness pass. Phase C found 28,134 hits across 413,225 candidates (6.81% aggregate, ~9.0% excluding the confirmed-empty 100K-integer 2.4M bucket which contributed near-zero hits). The pilot's probe locations were unrepresentative — they happened to hit administratively-empty stretches while completely missing the intra-bucket sparse-hole population structure (countryside cultivated land, never-listed apartments at the end of numbered series, regional commercial buildings, sheep farms, horse barns, fishing-rights lots).

**Strategic finding — pilot v3 thesis revised, lesson logged**: small-sample empirical probes are insufficient to scope full registry-completion work. Even three independent probes returning 0–2 hits each can mask a broader population structure 1-2 orders of magnitude denser. **For any backfill-style operation against an authoritative external registry, run a full-coverage sweep before concluding the scope is small.** Applied retroactively, this means the original 2026-04-29 Áfangi 0 25K-fastnum-gap estimate was directionally correct (actually 30K); the 2026-05-08 collapse of that thesis to "no credible target range" was wrong; the 2026-05-18 sweep restored the original direction with better empirical grounding.

**HMS scraper engineering findings (locked, will be referenced in SCRAPER_SPEC v1.1)**:
- Endpoint `https://hms.is/api/fasteignaskra/fasteign/{fastnum}` works for the full registry. Cloudflare WAF requires `curl_cffi` Chrome120 TLS impersonation; plain `aiohttp`, Python `requests`, and `Invoke-WebRequest` all get 429'd on the first request (including the public homepage).
- "Property does not exist" signal is **HTTP 500 `{"error":"Internal server error"}`, not 404**. Any scraper that retries 500 as transient failure will livelock; treat 500 as terminal "not exists".
- Realistic sustained throughput at concurrency=3 + 1.0±0.4s per-worker jittered delay: ~157 requests/minute = ~2.6 req/s. WAF backoff trigger (10 consecutive 429/403/503) never fired during the 58h run.
- HMS payload includes 8+ fields not present in current Supabase `properties` schema: `lhlmat` (land share of fasteignamat — decomposes value into land + structure), `brunabotamat` (independent rebuild-cost valuation), `fasteignamat_naesta_ar` (next-year forecast), `matseiningar[]` array (sub-unit breakdown with own `einflm` / `byggingarar` / `byggingarstig` (B0–B4) / `gerd` (HMS internal class) / `matsstig` / `skodags` / `texti`), `landeign_nr` + `tengd_stadfang_nr[]` (lot cross-references for building-density features). These are high-value features for the valuation model upgrade.

**Phase D scope (set; execution deferred to separate strategic chat session)**:
1. Schema decision — new `hms_data` table (1:1 with `properties.fastnum` + denormalised `matseiningar` child table) vs widen `properties` in place. Separate table cleaner for HMS-refresh re-runs that should not touch prediction-eldsneyti columns; widening simpler for queries.
2. New-property insertion path — 30,193 fastnums need full pipeline (coordinates from `Stadfangaskra.csv`, matsvaedi assignment, region_tier, canonical_code, is_residential classification) before joining `properties`, or land in HMS-only staging table first and graduate over time.
3. Ghost handling — 97 Supabase fastnums that HMS no longer recognises: `mark deregistered=true` + retain history, soft-delete, or hard-delete; needs implications mapping for `sales_history`, `predictions`, model-training filters.

**Artifacts (committed this entry)**:
- `audit/weekend_run_inventory.md` — raw factual numbers per staging DB
- `audit/weekend_run_summary.md` — narrative with strategic findings
- `audit/weekend_run_status.md` — final orchestrator status surface
- `audit/weekend_run.log` — full execution log

**Staging databases (gitignored, retained locally on D:\\)**:
- `audit/hms_archive_staging.db` (391 MB, 546,957 rows) — HMS scrape full output
- `audit/stage_a_augl_staging.db` (2.55 GB, 124,835 rows) — orchestrator Phase 2 augl refresh
- `D:\Gagnapakkar\image_index.db` (791 MB, 2,631,485 rows) — canonical image index
- `D:\Gagnapakkar\images\` (352.53 GB, 1,752,028 files) — image archive
- `audit/backfill_pilot.db` (2.7 MB, 5,415 rows) — pilot v1/v2/v3 historical record

**Out-of-scope for this commit**: Phase D execution, image-bootstrap re-run (if ever needed for the 58 failed URLs), valuation-model upgrade work using the new HMS fields. All planned for separate strategic chat sessions.

---

## 2026-05-06 — RLS baseline audit + GRANT cleanup closar 2026-05-03 alert (Sprint 2 unblock)

**Hvað**: ENABLE ROW LEVEL SECURITY á 14 dashboard-public tables (`properties`, `predictions`, `predictions_iter3v2`, `comps_index`, `feature_attributions`, `feature_attributions_iter3v2`, `sales_history`, `repeat_sale_index`, `last_listing_text`, `ats_lookup`, `ats_lookup_by_quarter`, `ats_dashboard_monthly_heat`, `llm_aggregates_quarterly`, `model_tracking_history`) með `public_read FOR SELECT TO anon, authenticated USING (true)` policy. `REVOKE ALL FROM anon, authenticated` + `GRANT SELECT TO anon, authenticated` reduces hver dashboard-table grant frá full DML niður í SELECT-only. Defense-in-depth `REVOKE ALL ... FROM anon` á 4 user-owned tables (`pro_users`, `saved_properties`, `saved_searches`, `saved_valuations`) sem þegar höfðu RLS+`auth.uid()` policies en héldu over-grants. 4 views (`latest_regime_per_cell`, `regime_per_cell_monthly`, `repeat_sale_index_by_segment`, `repeat_sale_index_main_pooled`) lose write privileges en SELECT inheritance frá underlying RLS'd tables stays intact. Single-transaction migration `BEGIN ... COMMIT` á 22 objects, idempotent (DROP POLICY IF EXISTS + ALTER TABLE ENABLE RLS no-op á rerun).

**Af hverju**: 2026-05-03 Supabase email-alert `rls_disabled_in_public` flagged 14 tables sem launch-blocker fyrir Sprint 2 Áfangi 4 public-dashboard announcement. Underlying severity multiplier var Supabase project-init default sem grantaði anon/authenticated full DML (including `TRUNCATE` og `DELETE`) á hverri töflu — alert var um RLS-disabled, en grant pattern þýddi að jafnvel RLS-on hefði þurft strict policies til að block writes. Migration applar SCRAPER_SPEC_v1 §3.3 conformance pattern ("RLS enabled by default, public SELECT via view, service-role bypass for scraper writes") til existing Sprint 1+2 tables — sami canonical pattern sem Áfangi 0 ætlar að æfa frá byrjun á active_listings + active_listings_history + rejected_commercial_listings, brought existing tables upp í sama staðal.

**Final categorization** (locked post-empirical-pre-checks): 14 dashboard-public (öll töflur sem frontend les via PostgREST anon-key — empirical grep á `app/` + `lib/` confirm; `model_tracking_history` var heuristic-flipped frá service-role-only til dashboard-public eftir grep fann anon-key reads á `lib/dashboard-queries.js:49` + `app/markadur/modelstada/page.js:44, 61`), 0 service-role-only (heuristic produced one but empirical flip moved it til public), 4 user-owned með pre-existing `auth.uid()` RLS frá Sprint 2 Áfangi 5 prep work, 4 views inheriting frá underlying.

**Empirical proof of resolution**: PostgreSQL error 42501 (insufficient_privilege) raised á direct anon INSERT probe (`BEGIN; SET LOCAL ROLE anon; INSERT INTO properties (fastnum, heimilisfang) VALUES (-99999, 'audit_probe_should_fail'); ROLLBACK`) — privilege layer blocks INSERT áður en RLS policy check fer fram, sem er strongest possible failure mode (defense in depth: grant blocks AND no INSERT policy exists). Live-site smoke check 7/7 HTTP 200 með substantive content sizes (`/` 35 KB, `/eign/2008647` 128 KB, `/markadur` 44 KB, `/markadur/visitala` 964 KB, `/markadur/markadsstada` 1.1 MB, `/markadur/ibudir` 840 KB, `/markadur/modelstada` 38 KB) — zero blank pages, zero 5xx, response times 0.6-3.6s. Anon SELECT row counts unchanged post-apply: `properties` 124.835, `comps_index` 1.101.454, `predictions` 110.316, `feature_attributions` 1.103.160, `sales_history` 173.081, plus the rest matching pre-state exactly.

**Commit**: `1d61257` (a045f1a..1d61257), 9 files, +1.227 lines. Includes `supabase/migrations/20260506_rls_baseline_audit.sql` plus full audit/ trail (sweep script + raw JSON dump + sweep report + dry-run plan + apply log + verify script + post-fix report).

**Tvö non-blocker flags loggud í PLANNING_BACKLOG**: **Bug 25** — Postgres 15+ view `security_invoker` discipline (Áfangi 0 dependency, kritískt þegar `rejected_commercial_listings` ships sem service-role-only — any view joining it verður að declare `WITH (security_invoker = true)` eða það leak-ar rows til anon callers via view-as-bypass channel). **Bug 26** — `augl_id` back-link column exposure á `last_listing_text.augl_id` + `properties.augl_id_latest` (v1.1 hardening, column-stripping public views post-Áfangi-0, ~4-6 klst inkludandi frontend refactor — sami concern sem drove SCRAPER_SPEC §3.3 til REVOKE `listing_id` frá `active_listings_public`).

**Cosmetic residual**: views retain `REFERENCES` + `TRIGGER` privileges fyrir anon/authenticated post-fix (DML revokes only covered INSERT/UPDATE/DELETE/TRUNCATE). Non-security — `REFERENCES` á view er meaningless (cannot foreign-key-reference a view), `TRIGGER` would only matter ef enginn skrifar `INSTEAD OF` trigger sem nobody has done. Sweep upp í v1.1 hygiene pass alongside Bug 26 column-stripping work.

**Process lærdómur (Bug 24 pattern, made operational tvisvar í þessari audit)**: First þegar heuristic categorization tagged `model_tracking_history` sem service-role-only (guess based on table-name semantics) en empirical frontend grep flipped it til dashboard-public (fact based on actual `app/` reads). Second þegar audit-script-first principle — sweep `pg_class` empirically rather than trust doc-canonical SCRAPER_SPEC §3.1 baseline cross-check — surfaced doc-vs-reality discrepancy on `predictions_iter4` / `feature_attributions_iter4` / `ats_lookup_by_heat` naming (doc references tables sem don't exist í public schema; production-table = bare name without iter4 suffix). Trust empirical.

---

## 2026-05-06 — Sprint 3 Áfangi 0 SCRAPER_SPEC_v1 planning session decisions

Eftirfarandi ákvarðanir voru lokaðar í planning session 2026-05-06 sem framleiddi `app/docs/SCRAPER_SPEC_v1.md`. Allar decisions eru sourced í þeim spec — þessi entry er audit-trail og rationale preservation, ekki re-spec.

**Áfangi 0 scope stretching (Track A + Track B)**: Original PLANNING_BACKLOG entry var skrifað fyrir Track B eingöngu (supplementary HMS-gap scraper). 2026-05-06 stretched scope-ið til að inkludera Track A — direct active-listings scraper á mbl.is/fasteignir og fasteignir.visir.is sem powerar Áfangi 4.13 market-scan view og recoverar live-listings stream sem dó 2025-07. Tvær tracks share infrastructure (storage layer, orchestrator hook, health monitoring) en aðskildir í source endpoint, fields, refresh cadence, og downstream consumer.

**Track B simplification**: HMS Fasteignaskrá er source-of-truth sem inniheldur öll ~150K fastanúmer í íslenska fasteignastofninum. 25K gap-ið í properties_v2 er incomplete-scrape-of-HMS, ekki fundamental data-sourcing problem. Track B er því full-scale HMS fastanúmera-extract sem inserts missing rows í canonical `properties` tafla — ekki supplement table, ekki fuzzy match, ekki manual review queue. Bug 4 case (Sævargarðar 7) er incomplete-scrape gap, ekki pre-fastnum hypothesis.

**Mirror-investigation as Track A source-pick prerequisite** (Decision-point #1A): Whether mbl.is og fasteignir.visir.is mirror hvor aðra empirically er unknown. 5-7 daga audit script mælir overlap rate á `(heimilisfang_normalized, postnr, agent_listing_id)` match med fallback `(heimilisfang_normalized, postnr, byggar, einflm)`. Decision rule: ≥95% overlap → single-source, <95% → dual-scrape med cross-site dedup. Audit-script-first principle á source-pick stigi — ekki lock-a án empirical data.

**HMS formal-API-first preferred over silent scrape** (Decision-point #1B preference): HMS er government body. Working dialogue er project asset, ekki friction-point. Áfangi 4.9 (matsvæði shapefile) hefur formal-HMS-request precedent — piggyback á þann dialogue. Reputational og legal hygiene plus relationship-as-asset rationale. Silent scrape er fallback eingöngu (Tier 3 í 4-tier ladder í `SCRAPER_SPEC_v1.md` §7.3).

**Decision-point #2B locked — mixed write-path approach**: Track A → (ii) Hetzner-local-staging-then-sync (high-volume nightly, replay-safety valuable, decoupling frá Supabase availability). Track B → (i) direct write til Supabase (low-volume monthly, simplicity beats robustness). Asymmetría justified by volume + criticality profile. Lock í `SCRAPER_SPEC_v1.md` §6.1.

**Inter-track sequencing í monthly cycle**: Track B steady-state runs AFTER `refresh_dashboard_tables` (which itself runs after `rebuild_training_data`). Reasoning: 0.04-0.16% marginal training-data gain frá including new fastnums vs cascade-risk yfir model refresh. Failure-isolation prioritized.

**Public-view security pattern**: New tables ship med RLS enabled by default + explicit SELECT policy `USING (true)` fyrir public-readable + REVOKE á sensitive columns frá `anon`/`authenticated` (`raw_payload`, `agent_phone`, `listing_id`). `public_id uuid` surrogate column pattern reserved fyrir future v1.1 share-link addressability ef þörf krefst — ekki resolve-anlegt til source URLs. RLS-disabled-by-default er recurring failure mode í verkefninu (Bug 24 lesson + 2026-05-03 Supabase alert) sem SCRAPER_SPEC v1 explicit forðar.

**Volume-based scraper health detection (rolling 7-day mean 70% threshold)**: Replaces fixed cycle-over-cycle threshold. Day-of-week seasonality (weekend vs weekday upload patterns) can cause ±15-20% swings without indicating malfunction; trailing 7-day mean normalizes. Direct response til 2025-07 silent-death incident (gamli scraperinn dó án warning, Danni vissi ekki í marga mánuði). Volume detection myndi hafa caught þetta á degi 8.

**Separate scraper repo (`verdmat-is-scraper`)**: Mirroring `verdmat-is-precompute` pattern. Different deploy cadence (Hetzner vs Vercel), different secrets surface (HMS credentials, source-site cookies), different language-stack focus. SCRAPER_SPEC canonical í `verdmat-is/app/docs/`, scraper repo gets read-only mirror.

**#2A pickle migration default fallback (B2 twin-write)**: Ef Áfangi 4.8 (competitor comparison) ekki resolved fyrir Áfangi 0 implementation kickoff, default leaning er B2 (twin-write Supabase + pickle) frekar en B3 (frozen pickle, refactor at iter5). Insurance gegn worst case: iter5 confirmed necessary en slips beyond pickle-empty window.

Sjá `app/docs/SCRAPER_SPEC_v1.md` fyrir full deliverable, build order, og open decision-point status.

---

## 2026-04-28 — Methodology: Postgres LANGUAGE sql function plan-cache pitfall (Bug 13)

**Hvað**: Latency-investigation á `LANGUAGE sql` Postgres functions með parameterized predicates skal ávallt bera saman `EXPLAIN ANALYZE` á function call vs sömu fyrirspurn með inline literal. Munur >2× = generic-plan-cache pitfall sem útilokar prefix index (`text_pattern_ops`, `varchar_pattern_ops`).

**Af hverju**: Bug 13 latency root cause var `search_properties_grouped(term)` skilgreind sem `LANGUAGE sql STABLE` með `lower(p.heimilisfang) LIKE lower($1) || '%'`. Postgres parameterized $1 í generic plan sem féll back á sequential scan af ~125k rows (4207 ms). EXPLAIN á inline literal `LIKE 'akra%'` notaði `text_pattern_ops` btree index á 24 ms. Sama predicate, sama data — eingöngu munur er hvort planner sér literal eða parameter.

**Lausn pattern**: rewrite-a function sem `LANGUAGE plpgsql STABLE` með `EXECUTE format('SELECT ... LIKE %1$L ...', pattern)` — `%L` injectar literal-quoted string sem planner getur index-matched. Nota `format()` með positional `%1$L` til að referencea sama pattern í multiple WHERE clauses án að passa term oftar í argument list.

**Fallback ákvarðun**: ekki nota `LANGUAGE sql` fyrir functions sem þurfa að index-match á LIKE/ILIKE/regex predicates með parameterized strings. Nota plpgsql + EXECUTE format(), eða nota direct PostgREST query með filter ef function abstraction is overkill.

**Verification recipe** (post-rewrite):
```sql
EXPLAIN ANALYZE SELECT * FROM search_properties_grouped('akra');
EXPLAIN ANALYZE
  SELECT * FROM properties
  WHERE lower(heimilisfang) LIKE 'akra%' AND is_residential = TRUE
  LIMIT 15;
-- both should show "Index Scan using ix_properties_lower_heimilisfang"
-- both should be < 50 ms on a warm cache
```

---

## 2026-04-28 — Methodology: Edge Runtime env var validation pattern (Bug 13 / Bug 18)

**Hvað**: Edge Runtime routes sem reiða sig á `process.env.NEXT_PUBLIC_*` skulu defensive-trim+validate með fallback constants. `||` á einum sér er ekki nóg, vegna þess að truthy-but-malformed strings (whitespace-padded URL, truncated JWT) beat `||` og leiða til downstream error sem er erfiðara að diagnose-a.

**Af hverju**: Bug 13/18 root cause var Vercel dashboard sem reported env vars sem "set", en Edge runtime fékk:
- `NEXT_PUBLIC_SUPABASE_URL` með **2 trailing spaces** → `fetch()` threw `TypeError: Invalid URL string`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` truncated til **46 chars** (full JWT er 208) → 401 á öllum requests jafnvel þó URL parse-aði

`process.env.X || FALLBACK` skipti engu því bæði values voru truthy. Niðurstaða: Edge route skilaði `[]` á öllum search queries → UI sýndi "Engin eign fannst" empty-state á alvöru residential queries.

**Lausn pattern**: defensive validators sem trim + structural-validate + fallback til hardcoded constants:

```js
const FALLBACK_SUPABASE_URL = "https://<ref>.supabase.co";
const FALLBACK_SUPABASE_KEY = "<full-anon-jwt>";

function pickUrl(envVal) {
  const trimmed = (envVal || "").trim();
  if (!trimmed) return FALLBACK_SUPABASE_URL;
  try { new URL(trimmed); return trimmed; }
  catch { return FALLBACK_SUPABASE_URL; }
}

function pickKey(envVal) {
  const trimmed = (envVal || "").trim();
  return trimmed.length > 100 ? trimmed : FALLBACK_SUPABASE_KEY;
}
```

**Hvenær á við**: Edge Runtime routes (Vercel/Cloudflare Workers/Netlify Edge) þar sem env-var injection pipeline er meira fragile en Node serverless. Pattern á einnig við um SSR routes ef env vars eru fed gegnum CI/CD eða third-party tools sem geta whitespace-padded eða truncated values.

**Hvenær EKKI við á**: server-side keys sem leyfast EKKI í client bundle (service-role keys, OAuth secrets). Fyrir þá values, fail-fast er better than fallback — láta route 500-a með skýru "config missing" message frekar en að silently use a public fallback.

**Hvenær FALLBACK er öruggt**: aðeins þegar fallback value er already-public (NEXT_PUBLIC_* vars sem ship í client bundle). `FALLBACK_SUPABASE_URL` + `FALLBACK_SUPABASE_KEY` í þessu case eru bæði í `.env.example` og í the bundled JavaScript sem hver browser tab fær — þau eru ekki secrets.

---

## 2026-04-27 — Sprint 2 Áfangi 4 LOKIÐ: dashboard launch + Fasi E polish + Bug 8

**Hvað**: Sprint 2 Áfangi 4 closed. Dashboard live á https://verdmat-is.vercel.app/markadur með öllum fimm route undirsíðum (`/`, `/visitala`, `/markadsstada`, `/ibudir`, `/modelstada`), eign-síðu waterfall fix og Fasi E launch polish (Addendum 1 unregistered-space map, Bug 7 thin-sample filter, Bug 8 nýbygging exclusion fyrir metric 1 & 2, Lighthouse a11y polish, scrape-gap disclosure copy).

**Áfangi 4 deliverables — production**:
- Fasi A — data pipeline infra (4 Supabase tables, 3 views, 4 build scripts, orchestrator v2)
- Fasi B — `/markadur` landing (A+B hero, 3 cards, 3-line timeline, scrape-gap banner)
- Fasi C-1 — `/markadur/visitala` (4×3 grid, per-row toggles, crash-band shading)
- Fasi C-2 — `/markadur/markadsstada` (slider, heat-map, back-projection widget, regime view)
- Fasi C-3 — `/markadur/ibudir` (5 LLM aggregates + Addendum 1 unregistered map)
- Fasi C-4 — `/markadur/modelstada` (4 panels, Icelandic status labels, methodology card)
- Fasi D — `/eign/[fastnum]` waterfall hides time anchors, Markaðsstaða footer
- Fasi E — launch polish (canonical, og:, mobile collapse, skip link, gallery a11y, copy)

**Bugs fixed mid-sprint (8 total)**:
1. Regime pill hybrid rule (12m + pooled z_3v12)
2. effective_date_latest column for /eign listing date
3. Autocomplete ORDER BY for fjölbýli coverage
4. Two-tier autocomplete + HMS-gap caveat banner + prefix indexes
5. Step 2 expand SELECT non-existent merking column
6. Quarterly + smoothed-monthly regime methodology
7. n<30 filter on /ibudir aggregate charts
8. is_new_build=False filter for metric 1 & 2 (this entry)

**Bug 8 detail — is_new_build filter**:
- Spot check 2026-04-27: interior_condition_score for new builds avg 2.47 vs 1.60 for existing stock, inflating APT_STANDARD quarterly mean by +0.10 to +0.33 points.
- Renovation rate distorted because new builds get coded `has_any_recent_work=False` so a heavy new-build inflow drags the rate down even when absolute renovation count rises.
- Fix: `build_llm_aggregates.py` filters `is_new_build=False` for metric 1 (interior_condition_score mean) and metric 2 (pct_recently_renovated). Other metrics unaffected.
- Editorial copy on /ibudir Section 1 + 2 explains the filter explicitly: "Nýbyggingar útilokaðar úr greiningu (þær fá hátt ástandsstig per definition og myndu skekkja meðaltalið)."
- Rebuilt + re-loaded llm_aggregates_quarterly via `load_dashboard_v1.py --tables llm` (1,450 rows, same shape, different values for metrics 1 & 2).

**Fasi E launch polish**:
- Addendum 1 unregistered-space graduated-symbol map on /ibudir (22 capital-region postnr from Stadfangaskra centroids + refined `unregistered_space_sqm > 5` rate; Leaflet circle markers with √n radius scaling; static JSON in `public/data/`).
- True polygon choropleth deferred to v1.1 — LMÍ public shapefile requires browser-driven catalog navigation that cannot be programmatically fetched. Logged in PLANNING_BACKLOG Áfangi 4.5.
- /markadsstada disclosure paragraph: "Nýjustu áreiðanlegu gögn eru frá 2025-Q2 vegna tímabundinnar takmörkunar á auglýsingaflæði..."
- Lighthouse a11y polish: skip-to-content link in root layout (sr-only, focus-visible); gallery thumbnail buttons aria-label "Mynd N af M"; hero `<Image priority>` already in place; canonical URLs on all 5 dashboard routes + /eign metadata; /eign generateMetadata gains openGraph block.
- VisitalaGrid 4×3 collapses to single column at <600 px viewport via `.vm-visitala-row` class + media query (was missed in C-1).
- og:image fallback deferred — no static brand image asset exists; shipping a 404 reference is worse than absent meta. Queued for v1.1 OG generator polish.

**Carry-overs to Sprint 3** (logged in PLANNING_BACKLOG, not blocking launch):
- Áfangi 0 — comprehensive scraper to recover the post-July-2025 listing flow gap (top priority)
- Áfangi 4.5 — €/m² price map dashboard (`/markadur/kort`), depends on LMÍ polygon download
- Áfangi 4.6 — new-build share tracker (Bug 7 follow-up)
- Áfangi 4.7 — new-build as a separate segment (Bug 8 follow-up; depends on Áfangi 4.8)
- Áfangi 4.8 — eldri-stock calibration analysis (Egilsgata 10 7 % gap vs competitor; possible iter5 fasteignamat re-introduction)
- Áfangi 4.9 — matsvæði-level polygon (Sérlóðir map upgrade, depends on HMS API access)
- /markadur/markadsstada 1.14 MB payload (lazy-load candidate)
- /eign dynamic 1.1 s server render

**Lighthouse**: Danni runs in browser on `/markadur` and `/eign/2008647` post-deploy; thresholds (Performance ≥ 85, SEO ≥ 95, Accessibility ≥ 90, LCP < 1.8 s mobile) confirmed before announcement (or any sub-target documented in v1.1 backlog).

---

## 2026-04-24 — Bug 6 + smoothing refinement: asymmetric monthly/quarterly regime methodology on /markadsstada

**Hvað**: `/markadur/markadsstada` skiptir um regime-source logic:
- **Default view**: ársfjórðungslegt per-cell regime úr nýju `ats_lookup_by_quarter` töflunni (913 rows; derived úr Áfanga 7 `build_ats_lookup.py` step 6, en ekki importað í Supabase fyrr en núna). Stöðugri fyrir langtíma trend.
- **Monthly (smoothed) drill-down**: z₃v₁₂ ± 0,5 þröskuldur á `ats_dashboard_monthly_heat`. Responsive fyrir nýlegar breytingar.
- **Per-cell fallback**: ef `n_month < 50` OR `z_3v12 IS NULL` í selected month, displayed regime fellur til ársfjórðungslegu heat_bucket, með "ársfj." disclosure label á pill + popover tooltip copy.

Slider heldur sama formi (velur mánuð); data-source breytist eftir mode. Methodology paragraph bætist á `/markadur/modelstada` fjórðu card-ið til að útskýra asymmetry.

**Root causes**:
1. **Stale data display** — bæði monthly heat og quarterly table eru derived úr `paired_fresh` subset sem ekki inniheldur `in_scrape_gap=True` rows (per build_ats_lookup.py step 1). Max month er 2025-06 fyrir báðar tables (quarterly = 2025Q2). Monthly default birti user-um 2025-06 sem "núverandi", sem er misleading; quarterly 2025Q2 er sama date-reach en með pooled 3 mán → fewer flips. Full recency (2025-Q3+) krefst Sprint 3 scraper.
2. **Month-to-month flip-flop** — thin-sample cells (t.d. SFH_DETACHED × Capital_sub með avg n=15/mán) sýndu 17 raw-regime-flips á 24 mánuðum vegna sampling noise. 3-mo smoothing dregur þetta niður í ~9 flips (still noisy), en quarterly fallback við n<50 dregur það niður í 0 spurious flips (quarter heat_bucket er stable per quarter). Matches user expectation.

**Methodology asymmetry — rökstuðningur**:
- Monthly regime = z₃v₁₂ ± 0,5 (current-relative): user mental model "er markaðurinn heitur **núna**?" kallar á samanburð við rolling 12-mán baseline. z-score er zero-mean og scale-free → sama þröskuldur fyrir öll segment.
- Quarterly regime = median_log_ratio vs p33/p67 (historical-relative): fyrir langtíma trend þarf fixed reference frame. Áfangi 7 byggði p33/p67 á whole-sample quarterly medians; að endurnýta það fyrir quarterly view tryggir consistency með scoring table B.
- Mismunandi tímaupplausnir kalla á mismunandi referansaramma. Þetta er ekki bug heldur by-design.

**Threshold choice**:
- **Smoothed ± 0,5 SD**: ~38 % af z-scores fyrir normal distribution falla utan |z|>0,5, sem passar við "notable shift from 12-mo baseline" án að vera of sensitive. ±1,0 væri of strict (fáir flaggaðir hot/cold); ±0,3 væri of loose (flip-flop á normal variation).
- **Fallback n<50**: matchar Áfanga 6 `MIN_PAIRS_PER_CELL=50` all-time inclusion filter og Áfanga 7 Table B `TABLE_B_MIN_N=10` per-bucket threshold — consistent með existing pipeline methodology. Under 50 pairs per month er too thin fyrir stabilan z-score (CI ±15 pp á above-list rate).

**Implementation path** (hybrid upstream/downstream per Danni confirmation 2026-04-24):
1. Upstream: import `ats_lookup_by_quarter.csv` (913 rows, ~90 KB) í new Supabase table. One-time data load; build script unchanged.
2. Upstream: new SQL view `regime_per_cell_monthly` — join-ar monthly heat við quarterly lookup, emitterar `raw_regime / smoothed_regime / quarterly_regime / display_regime / regime_source` columns í einni fetch. Engin materialization; view-time CASE computation.
3. Downstream: `MarkadsstadaDashboard.js` mode toggle (quarterly default / monthly drill-down), fallback disclosure label, tooltip copy update.

**Flip-frequency verify (2024-07 → 2025-06, 24 mán)**:
- APT_STANDARD × RVK_core (avg n=82): raw 4 flips → smoothed (display) 2 flips. One clean regime transition Jan 2025 (hot→cold).
- SFH_DETACHED × Capital_sub (avg n=15, all 24 months fallback): raw 17 flips → display regime follows quarterly (~2 flips over 24 months matching 2024Q4 hot → 2025Q1 neutral → 2025Q2 hot transitions).

**Timeline yfirboð-chart**: augar scrape-gap (2025-07→latest) með yellow ReferenceArea + caveat "Gögn enda {latest month} vegna scrape-gap frá júlí 2025". Fully transparent.

**Methodology statement** á `/modelstada` pipeline health card: útskýrir tvennar tímaupplausnir svo pro-users skilji af hverju pill fyrir sömu (seg × reg) cell er kannski mismunandi milli quarterly view og monthly drill-down.

---

## 2026-04-22 — Bug 5 fix: expand Step 2 requested non-existent `merking` column

**Hvað**: Bug 4's expand-path (SearchAutocomplete.js → Step 2 unit list) select-ar `merking` column sem er ekki til í Supabase `properties` tafla. PostgREST skilaði `42703: column properties.merking does not exist`; client-kóðinn ate error silently með `(data || [])` pattern og renderaði "Engar einingar tilheyra þessu heimilisfangi" fyrir hverja multi-unit address. Regression á allri Bug 4 UX — Miðbraut 1 Seltjarnarnes, Egilsgata 10, Bakkastígur, öll multi-unit-address matches broken.

**Root cause**: `properties_v2.pkl` hefur `merking` text column, en `precompute/build_precompute.py` exportar það ekki í Supabase. HMS "merking" fyrir multi-unit byggingar er hins vegar þegar í `properties.unit_category` ("0100", "0101", "0102", …) sem er exact same concept. Bug var copy-paste frá Danni's spec-query og ég missaði að cross-reference við actual schema fyrir deploy.

**Hypothesis eliminations** (Danni listaði 4, öll ruled out):
- (A) postnr null — nei, postnr=101 int fyrir alla 3 rows.
- (B) type mismatch — nei, postnr_type=integer og JS number hvor tveggja.
- (C) case sensitivity — nei, "Egilsgata 10" stafrétt.
- (D) trailing whitespace — nei, addr_len=12 = exact length "Egilsgata 10".

**Fix**:
1. Remove `merking` úr Step 2 SELECT. Skipta fyrir `unit_category` sem er already í select-inu og contains exact sama semantic ("0100" = kjallari, "0101" = 1st floor unit 1, o.s.frv.).
2. Surface PostgREST errors í client — `const { data, error } = ...` + `if (error) console.error(...)` frekar en silent `(data || [])`. Sama class af bug getur ekki falið sig aftur.
3. UI render sýnir nú "merking 0101" per unit sem er skýrara fyrir users en rå unit_category.

**Process lesson**: Bug 4 smoke test dekkaði Step 1 RPC output (group-by count) en ekki Step 2 expand path. Fyrir tvíþrepa UX patterns, must test both tiers end-to-end áður en deploy. Saved til memory sem generic learning.

**Verify** (production post-fix): `properties?select=fastnum,tegund_raw,canonical_code,unit_category,einflm&heimilisfang=eq.Egilsgata%2010&postnr=eq.101&is_residential=eq.true` skilar 3 rows (APT_BASEMENT 0100 52.4 m², APT_FLOOR 0101 108.4 m², APT_FLOOR 0102 99.0 m²). Miðbraut 1 Seltjarnarnes skilar 5 rows.

---

## 2026-04-22 — Bug 4 + search UX overhaul: two-tier autocomplete, HMS-gap caveat, Leið B launch

**Hvað**: `SearchAutocomplete.js` endurskrifaður frá flat unit-list yfir í tveggja-þrepa pattern. Nýr RPC `search_properties_grouped(term)` í Supabase aggregerar matches eftir `(heimilisfang, postnr, postheiti)` og skilar `n_units` + `tegund_summary`. Þrep 2 er inline-expand sem sækir units per address á klicki. 7-stafa fastnum queries fá beina leit án address-groupings. Empty state skilar HMS-gap-caveat-copy. Nýr `SearchDataGapBanner` (localStorage-persistent) á homepage undir search.

**Launch strategy Leið B (Danni)**: ship dashboard og pro-questionnaire með transparent HMS-gap caveat, byggja comprehensive scraper (e-value.is eða equivalent) í parallel sem Sprint 3 top-priority. Dashboard ekki blocked af properties-completeness; search-leki er acknowledged í UI svo users skilja af hverju sumar eignir vantar.

**Performance fix (samhliða RPC)**: EXPLAIN ANALYZE sýndi 3.072 ms execution fyrir ILIKE-prefix á 125K-row properties tafla — planner valdi `idx_properties_residential` partial index og seq-filteraði 105K rows. Trigram GIN á heimilisfang var ekki pickað. Lausn: ný B-tree `text_pattern_ops` indexes á `lower(heimilisfang)` og `lower(postheiti)`, og rewrite-a RPC til að nota `lower(col) LIKE lower($1) || '%'`. Eftir fix: 10 ms execution með Bitmap Index Scan + BitmapOr combining báðum indexes. Function sett med `SET statement_timeout TO '10s'` sem safety net fyrir cold plan-cache calls.

**UI patterns**:
- **Þrep 1 address-row**: `heimilisfang · postnr postheiti` + optional `(N íbúðir)` count ef n_units > 1 + `tegund_summary` í undir-línu. Single-unit rows nav-a beint við klick; multi-unit rows expand inline. Chevron glyph `▸`/`▾`/`→` gefur hint um behaviour.
- **Þrep 2 unit-row**: tegund_raw + einflm + merking, sortað APT_BASEMENT fyrst, svo einflm desc (matches spec intent, stable across HMS tegund variants).
- **Empty state**: explicit HMS-fasteignaskrá caveat + link á `/um#gagnasafn`. Frekar en silent "engin niðurstaða", útskýrir af hverju eign gæti vantað.
- **Persistent banner**: `SearchDataGapBanner.js` birtist undir search og dismiss-ast með × — localStorage (ekki session), þannig user dismissar einu sinni per browser. SSR-renders visible svo non-JS + SEO crawlers sjá caveat-ið á first paint.
- **Fastnum direct search**: regex `/^\d{7}$/` triggerar bypass — single-row result með pseudo-address-row shape svo sama renderer virkar.

**Indexes hafa áhrif**: Bæði B-tree indexes bætast á properties (2 × ~1 MB á 125K rows). Insignificant vs 8 GB Supabase cap.

**Verify** (production):
- EXPLAIN á `search_properties_grouped('miðbraut 1')`: 10 ms execution, Bitmap Index Scan + BitmapOr beggja lower-prefix indexes.
- Anon REST call cold: ~2,4 s (pgBouncer + plan cache cold), warm: 700–1000 ms. Innan statement_timeout og user-perceivable latency.
- `miðbraut 1` search skilar nú 6 address-rows: Miðbraut 1 Seltjarnarnes (5 íbúðir), Miðbraut 1 Búðardalur (einbýli), Miðbraut 10–13 etc.
- `Sævargarðar 7` skilar `[]` og UI birta empty-state caveat.

---

## 2026-04-22 — Bug 3 fix: autocomplete ordering for fjölbýli coverage

**Hvað**: `SearchAutocomplete.js` færir `ORDER BY heimilisfang ASC, fastnum ASC` í autocomplete-fyrirspurnina og hækkar `LIMIT` frá 8 í 15. Fjölbýli með fleiri en eina íbúð á sama heimilisfang birta nú allar sínar einingar fyrstar.

**Root cause 3a — Miðbraut 1 fjölbýli birti bara eitt hit**: Fyrirspurnin hafði ekkert `ORDER BY`, svo PostgREST skilaði rows í arbitrary insertion-order (≈ fastnum asc fyrir gömul rows). `%Miðbraut 1%` ilike pattern matches líka Miðbraut 10/11/12/17/18/19. Með `LIMIT 8` birtust bara einingar með lægri fastnum (2067xxx-svæði) — #1's yngri einingar (2220441–2220444, bættar við HMS síðar) komust aldrei í fyrstu 8. Fix: `ORDER BY heimilisfang` collatar alphabetically svo "Miðbraut 1" < "Miðbraut 10" (styttra string með sömu prefix vinnur), og öll 6 Miðbraut 1 hits klessa saman efst. `LIMIT 15` er valið svo fjölbýli með <10 einingum taki ekki öll sæti fyrir aðra staði.

**Root cause 3b — Sævargarðar 7 vantar alveg**: **Ekki bug í okkar kóða.** HMS Fasteignaskrá (raw `properties_v2.pkl`) inniheldur ekki Sævargarðar 7. Landnum-röð fer 117655→117660 (Sævargarðar 1-6), svo 117662 (Sævargarðar 8+10 sameiginlegir raðhús). Landnum 117661 vantar alveg upstream — líklega demólað, endurnúmerað eða ekki skráð enn. Sprint 3 `refresh_kaupskra.py` companion mun pick-a upp framtíðarskráningar.

**Hypothesis B ruled out**: Autocomplete filter-ar bara á `is_residential = true` — engin prediction-háðsía. Eign getur birst í search áður en iter4 pred er computed.

**Verify** (post-fix query): `ORDER BY heimilisfang, fastnum LIMIT 15` á `%Miðbraut 1%` skilar 6 Miðbraut 1 rows efst (5 Seltjarnarnes + 1 Búðardalur), svo Miðbraut 10/11/12/13. Matches expected coverage.

---

## 2026-04-22 — Bug 2 fix: effective_date_latest replaces scraped_at_latest fyrir listing display

**Hvað**: Ný DATE-column `properties.effective_date_latest` drífur "Nýleg auglýsing ([date])" á `/eign/[fastnum]`. Kemur frá `listings_v2.effective_date` (raunverulegur auglýsingardagur) en ekki `listings_v2.scraped_at` (pipeline-keyrslutími).

**Root cause**: `precompute/build_precompute.py` var `sort_values("scraped_at").drop_duplicates("fastnum", keep="last")`. Innan einnar scrape-keyrslu eru ÖLL rows með sama `scraped_at` (tíminn þegar job keyrði), svo tied-values sort fellur aftur til DataFrame row-index sem picking-strategy. Fyrir fastnum=2008647 (9 rows, effective_date 2017-08-22 → 2019-09-06) var picked 2017-row (price 64.9 M kr) og displayed "11. apr. 2026" scrape-date. Danni screenshot stakk á þetta.

**Fix**:
1. `build_precompute.py`: sort með `effective_date` (fallback `scraped_at` ef null). Export `effective_date_latest` alongside.
2. `properties` schema: `ADD COLUMN effective_date_latest DATE` (idempotent migration `20260422_effective_date_latest.sql`).
3. Targeted backfill `precompute/fix_latest_listing_per_fastnum.py` — re-derives per-fastnum latest frá listings_v2.pkl og uppsertar via psycopg2 TEMP table + UPDATE FROM. 58.437 rows updated í 23 sec, engin full-pipeline re-run þörf.
4. `/eign/[fastnum]/page.js`: display `effective_date_latest`; fallback `scraped_at_latest` with "skráð" prefix svo það er unambiguous.

**Verify**: fastnum=2008647 displays now "48,9 M kr (6. sep. 2019)" (augl_id=874137). Previously: "64,9 M kr (11. apr. 2026)".

**Follow-up**: next full `build_precompute.py` run will use updated logic and include `effective_date_latest` í CSV export. Existing properties.csv á /d/verdmat-is/precompute/exports/ is stale wrt this column; not blocking because live DB is patched.

---

## 2026-04-22 — Bug 1 fix: regime pill rule revised to hybrid (12m + pooled z_3v12)

**Hvað**: Landing pill `/markadur` regla breytt frá "≥8 af 12 cells hot/cold → pill" í:

- 12m real change ≤ −1,0 % AND pooled z_3v12 < +0,5 → `KALDUR`
- 12m real change ≥ +1,0 % AND pooled z_3v12 > −0,5 → `HEITUR`
- Annars → `HLUTLAUS`

Pooled z_3v12 er `n_month`-weighted mean across 12 main-residential cells (latest month per cell).

**Root cause**: Fyrri reglan aggregated heat_bucket counts úr `latest_regime_per_cell` view. Heat-bucket er per-cell p33/p67 threshold on `median_month` — lítið correlated með pooled 12m real change. Við 2026-04 data (12m = −2,00 %), cells split 3 hot / 5 neutral / 2 cold / 2 unknown → ekki 8-of-12, pill HLUTLAUS. User screenshot: red −2,0 % hero beside neutral pill = cognitive mismatch.

**Rationale**: Hybrid lets either signal (momentum OR current trend) pull pillinn off neutral, en requires agreement (no veto) áður en committing to hot/cold. Momentum (12m change) matches user expectation frá the hero number; trend (z_3v12) matches ATS-scoring methodology. Thresholds (±1,0 % / ±0,5) chosen svo neutral band er breitt enough to avoid flicker en tight enough to catch real moves.

**Implementation**: `latest_regime_per_cell` view now exposes `z_3v12`. `lib/dashboard-queries.js::computeHeroB` re-written. Spec §2.2 Metric B updated in lockstep så future chats see the authoritative rule.

**Verify** (production): 12m = −2,00 %, pooled z_3v12 ≈ −0,08 → pill `KALDUR` (vm-badge-cold, blue). Matches red hero number.

---

## 2026-04-23 — Áfangi 3 closed: PDF export með built-in PDF fonts

**Hvað**: Public downloadable PDF á nidurstaða-síðu. Lazy-loaded `@react-pdf/renderer` + Document/Page/Text layout með Helvetica + Times-Roman (built-in Type 1 standard fonts).

**Font decision**: Reyndi first að registerá Inter + Fraunces frá Google Fonts CDN, en placeholder TTF URLs voru 404, PDF generation failed silent í client. Switched to PDF standard fonts (Helvetica body, Times-Roman display) sem báðir styðja Latin-1 Supplement (includes þ æ ð ö á ú via WinAnsiEncoding). Trade-off: display-heading serif er Times-Roman í staðinn fyrir Fraunces — web og PDF typography mismatch, en web brand retained og PDF letur er stable + offline.

**Lazy-load strategy**: `@react-pdf/renderer` er ~450 KB gzipped. Initial bundle er óbreytt frá Áfanga 2 af því PDFDownloadButton dynamic-importar renderer + PDFReport á fyrsta click. Second click er instant (modules cached). Accept loading state "Býr til PDF..." sem user feedback.

**Disclaimer**: Explicit text í PDF footer stating "AI-verðmat, not legally binding" — important fyrir ef fasteignasalar prenta og deila með viðskiptavinum.

---

## 2026-04-23 — Manual Q effects v1.1 calibration refinement (additive)

**Hvað**: 6-item calibration update til `data/manual_q_effects.json`. Backwards-compatible: old share URLs still work via legacy-key translation in both API og results page.

**Rationale per fix**:

1. **Flooring type → renovation trilemma**: Parket vs teppi er US-suburban price signal. Íslandi notar báðar lausnir alongside each other; gólfefni-type dispersion er stödd cross-buyer-pool and doesn't systematically move price. Recent-renovation er raunverulegt signal instead.

2. **Garage split by segment**: Single garage question allowed "tvofalt +4.5%" on APT_FLOOR, gerir flat-buyer confused og overstates effect. SFH/ROW/SEMI fá actual-bílskúr enum (einfaldur/tvöfaldur); APT fá bílastæði enum (sameign/tryggt_utanhuss/bilskyli_kjallari). Canonical-gated UI rendering + API validation enforce.

3. **Condition 4 stages**: v1 jumped 3% → 0% → −5% med engin middle stage for minor work. `smavagilegar_framkvaemdir` (−2%) fills gap; most Icelandic properties sit in medium-minor range. More granular user experience.

4. **proximity_school raised**: Real-estate literature used in v1 was US-sub; Icelandic barnafjölskyldu-markaðir í Kópavogi/Hafnarfirði price-a skólanálægð sterkar. 1.5% er Iceland-realistic.

5. **kjallari and floor4+**: Hedonic studies á íslenskum markaði suggest 3-5% kjallari penalty and +2-3% premium á hærri hæðum. v1.0 values were mildir; v1.1 aligns better.

6. **ovisst defaults halved**: v1 had ovisst as weak positive (≈0.3× of "ja" effect) sem meant user clicking "ovisst" through alls 5 questions fékk +1.5% stacked boost. Halving gerir ovisst accept-default-gracefully option, ekki stealth-bonus.

**Still hardcoded**: Sprint 3 PDP-based refresh á iter4a booster supersedear þetta alveg. Þessi refinement er interim pending real data-driven calibration.

**Coverage**: stacked worst-case −10 to −11%, best-case +24 to +27% (SFH vs APT). Real dispersion narrower.

---

## 2026-04-22 — Sprint 2 Áfangi 2 decisions

**Hvað**: Public manual questionnaire shipped (no auth required). Baseline + persónulegt verðmat med 11-spurning flow, link-shareable results, CTA card on main eign page.

**Segment fallback abandoned** (Skref 5): Tested 2 blend strategies — max-N donor biased small-N Country cells toward tighter Capital_sub/RVK_core. Pooled cov worsened (79.08 → 78.21). APT_STANDARD × Country held N=81 undercoverage (69.1%) is sample noise at Bin(81, 0.80) lower CI bound, not systematic miscalibration. Retained iter4_conformal_v1.

**Manual Q effects hardcoded**: Empirical residual regression gave 0.2–2% magnitudes — iter4a already uses these features as inputs, so leftover residuals only reflect what model missed. Used literature-anchored values in `data/manual_q_effects.json` (range −12% to +21%). Sprint 3 will refine via PDP per feature on iter4a booster.

**URL-encoded answers**: Results page uses `?a=q1:v1,q2:v2` query string instead of POST-only flow. Benefits: link-shareable, server-rendered (no client-side result fetch), no cookie/storage. Share button copies canonical URL.

**Questionnaire non-applicability**: SUMMERHOUSE + non-residential redirect 307 → `/eign/[id]?notice=no_adjust`. Avoid user confusion from getting a personal valuation on iter4's known-weak SUMMERHOUSE segment (175% MAPE) or unpredicted commercial.

**API route**: `/api/adjust-valuation` POST exposed publicly (no auth). Accepts `{fastnum, answers}`, returns `{baseline, adjusted, breakdown, multiplier, model}`. Server-side computation ensures baseline pulled from DB fresh. Used by results page indirectly via URL-decode + same adjustment logic; API available for future client use (saved valuations in Áfangi 3).

---

## 2026-04-22 — Sprint 2 Áfangi 1 QA findings

Edge case audit á 5 scenarios fyrir eign detail page:
1. No photos → "Engar myndir" placeholder í gallery. PASS.
2. New build (2024+, no sales) → sölusaga section renders conditional (`salesHistory.length > 0`), hidden when empty. PASS.
3. Non-residential (EXCLUDE canonical_code) → "Verðmat ekki í boði" notice; prediction/SHAP/comps/market sections all gated on `is_residential`. PASS.
4. No comps (APT_HOTEL fastnum 2169101) → prediction + SHAP render (21.9 M kr, 10 SHAP rows); comps section conditional, hidden cleanly. PASS.
5. Single-word heimilisfang (e.g. "Gil", "Mörk") → used as-is in heading; no fallback needed since all residential have at least short address. PASS.

No fixes required — existing conditional rendering handles all 5 gracefully.

**Known remaining issues** (carried into Sprint 2 Áfangi 2):
- APT_STANDARD × Country 80% PI coverage 69.1% (11 pp under, N=81). Small-sample noise; conformal quantile for this cell is below true residual distribution. Candidate fix: pool with Capital_sub, or increase MIN_N threshold.
- ROW_HOUSE × Capital_sub 80% PI coverage 92.2% (+12.2 pp over). PI widths too wide for this cell. Cosmetic issue, not functional.

---

## 2026-04-21 — Sprint 2 Skref 1: Switched to conformal PI calibration

**Hvað**: Replaced iter4 segment-stretch calibration (`iter4_segcal_v1`) with split-conformal prediction intervals (`iter4_conformal_v1`). Per (canonical_code × region_tier) quantiles of |log-residual| from the test split define symmetric half-widths; held coverage jumped from 68% → 79.1% on 80% PI.

**Af hverju segment-stretch náði ekki 80%**: The iter4 quantile heads (q100/q900) produce a narrower distribution than iter3v2's. Stretch factor k80=1.05 (found by grid-search to maximize coverage on val+test) saturates — widening the quantile head further was not possible because the quantiles themselves are under-spread. Conformal skips the quantile head entirely: it empirically calibrates PI width from observed residual distribution on held-out calibration data.

**Method**:
1. Training uses train + val (early stopping on val). Test split is reserved purely for calibration.
2. For each (canonical_code × region_tier) with n ≥ 30 on test split, compute `q80_log = 80th percentile of |log_real_kaupverd - pred_mean_log|`, same for q95.
3. Fallback hierarchy: segment×region → segment-only → global (when n < 30).
4. Application: `pred_lo80_log = pred_mean_log - q80_log`, `pred_hi80_log = pred_mean_log + q80_log`. Convert to ISK via `expm1 / cpi_factor × 1000`.

**Alternative considered**: (a) Retrain quantile models with wider bagging / deeper trees — more risky, affects point estimate. Hafnað. (b) Full conformalized quantile regression (CQR) à la Romano et al 2019 — more theoretically sound but much more code. Hafnað for v1. (c) Per-property adaptive conformal (locally-weighted residuals) — better guarantees but costly at inference. Deferred.

**Coverage deltas (held, main residential N=2,084)**:
```
Metric          iter4_segcal  iter4_conformal  Δ
80% PI cov      66.3%         79.1%            +12.8 pp
95% PI cov      89.1%         94.6%            +5.5 pp
```

**Impact**: User-facing PI widths now reflect actual uncertainty. Bakkastígur 1 80% PI went 81.5-105.3 → 80.9-103.8 M kr (tighter lower, tighter upper — concentrated around mean). Same model, same mean prediction. `iter4_segcal_v1` JSON retained on disk for audit.

---

## 2026-04-21 — iter4 production rollout (Áfangi 2-5 closed)

**Hvað**: Switched production prediction model from iter3v2 to iter4a (standalone, no fasteignamat input). iter3v2 archived in Supabase as `predictions_iter3v2` + `feature_attributions_iter3v2`. Frontend default view reads iter4 (`predictions` table post-rename). Debug mode `?mode=debug` loads both for side-by-side comparison.

**Metrics**:
- iter4a held MAPE: 8.19% (iter3v2 baseline 7.97%, delta +0.22 pp)
- Per-segment: APT_STANDARD 6.37%, APT_FLOOR 8.55%, ROW_HOUSE 7.24%, APT_BASEMENT 10.90%, SFH_DETACHED 16.29% (small N=106)
- Calibration: `iter4_segcal_v1` JSON, per-segment k-factors similar to iter3v2's
- 80% PI coverage 68% (target 80%) — known undercoverage, deferred to Sprint 2+
- Training time: 9.4 min (iter4a), 26 min (iter4 precompute rebuild with SHAP)

**Impact**:
- Annual HMS fasteignamat updates (júní ár hvert) **no longer cause prediction jumps** — iter4 is fully decoupled.
- Feature importance redistribution healthy: EINFLM 34.5%, sale_year 19.6%, matsvaediNUMER 17.6%, matsvaedi_bucket 14.2%, BYGGAR 4.5% (vs iter3v2's 77.9% fastmat dominance).
- DB size grew to 561 MB (was 424) due to iter3v2 archive retention. Still well within Pro tier (8 GB).
- iter4b via `init_model` fine-tune abandoned: LightGBM requires feature compatibility with init_model, so dropping FASTEIGNAMAT is infeasible without workarounds that preserve iter3v2's fastmat dependence.
- LLM extraction feature selection (Skref 5-6) was a no-op: all 136 extraction features were already joined into training_data_v2 and used by iter3v2. iter4a inherits them automatically.

**Not tripped stop-conditions**:
- Skref 4 MAPE > 15%: iter4a at 8.19% (well under).
- Skref 8 Bakkastígur 1 delta > 30%: actual +2.2%.

**Deferred to future sprints**:
- PI coverage undercoverage on held (68% vs 80% target).
- Manual-layer questionnaire (Áfangi 9 / Sprint 3).
- SUMMERHOUSE model quality (175% MAPE — iter3v2 has same issue).

---

## 2026-04-21 — iter4a validated as production candidate; iter4b (init_model) abandoned

**Hvað**: iter4a training complete. Held MAPE 8.19% vs iter3v2 baseline 7.97% — a +0.22 pp cost for full fasteignamat independence. iter4b (LightGBM `init_model` fine-tune) was abandoned due to technical infeasibility.

**Af hverju iter4a virkar svona vel**: The 77.9% gain iter3v2 attributed to `real_fasteignamat` + `FASTEIGNAMAT` was largely **collinear** with underlying features (size, location, age, time). LightGBM re-learns the signal from EINFLM + matsvaedi_bucket + matsvaediNUMER + sale_year + BYGGAR without the fastmat mediator. Feature importance in iter4a is healthily distributed across size/geography/time primitives.

**Af hverju iter4b sleppt**: LightGBM `init_model` parameter requires feature-set compatibility between the init booster and the new Dataset. Dropping `FASTEIGNAMAT` from iter4b features violates this contract. Workarounds (keeping feature as NaN constant) preserve iter3v2's existing NaN-path decisions on those features, not truly decoupling from fastmat. Clean "iter4b via fine-tune" is not feasible with feature-drop semantics.

**Alternative considered**: Train iter4a with alternative hyperparameters (more trees, deeper) as an iter4a_deep variant. Deferred — iter4a baseline already at 8.19% on held, diminishing returns from tuning.

**Consequence**: iter4a is the winner by default. PI coverage (66.3% on 80% PI vs target 78%) requires calibration-stretch in Skref 7 (follow iter3v2's `iter3v2_segcal_v1` pattern).

---

## 2026-04-21 — Switched production target from Streamlit prototype to Next.js+Supabase+Vercel

**Hvað**: Eftir Áfangi 7 completion var byggt Streamlit `app.py` sem Áfangi 5 v1. Danni hafnaði því sem prototype-quality (1990-style search bar, no feature attribution UI, no market integration). Switch yfir í production-grade Next.js stack byggt á sister project heyaskr (sama höfund, existing deploy).

**Af hverju**: End goal (bank analytics tool, public dashboard, subscription product) krefst scalable stakks; Streamlit limits would force full rewrite later. Next.js + Supabase gefur publish-level UX, server components, edge CDN, mobile-responsive út úr boxinu. Code-reuse mynstur frá heyaskr.

**Alternative**: (a) Streamlit með heavy customization — hafnað, limits remain. (b) FastAPI + vanilla HTML — meira plumbing, ekkert CDN, custom auth. Hafnað. (c) SvelteKit — minni reynsla, enginn code-reuse. Hafnað.

**Impact**: Phase 1 scope defined (precompute + mirror + read-only frontend); Sprint 2 adds auth/user accounts.

---

## 2026-04-21 — Precompute-all strategy fyrir Sprint 1 (no live Python backend)

**Hvað**: Engin FastAPI/Railway/Docker fyrir Sprint 1. LightGBM scoring + SHAP + comps eru precomputed locally (Phase 1A), dump í CSV, import í Supabase. Frontend les precomputed gildi úr PostgREST eingöngu.

**Af hverju**: Faster ship, zero backend ops, DB queries < 100 ms. Live scoring (fyrir user manual input í Áfanga 9) deferred til Sprint 2 þegar auth er komið og scope réttlætir backend.

**Alternative**: (a) FastAPI á Hetzner/Railway með live LightGBM. Hafnað: meira infra, cold-start latency, ónauðsynlegt fyrir read-only Sprint 1. (b) Supabase Edge Functions með Python/Deno. Hafnað: LightGBM runtime ekki supported á Edge.

**Impact**: 7 CSV skráar, 202 MB → 424 MB Supabase DB, <100 ms edge queries. Pipeline re-run-able via `build_precompute.py --force` locally.

---

## 2026-04-21 — CloudFront image URLs directly, no Supabase Storage

**Hvað**: `photo_urls_json` dálkur í `properties` tafla vísar beint í `d1u57vh96em4i1.cloudfront.net` URLs frá scraper. Engin upload til Supabase Storage.

**Af hverju**: 1,15M myndir eru þegar live á CloudFront frá scraper pipeline. Re-hosting er ónauðsynlegur overhead fyrir Sprint 1. Delisted auglýsingar skila 404 sem frontend handles gracefully (fallback parchment card, user sér engar broken images án intervention).

**Alternative**: (a) Download myndir í Supabase Storage bucket. Hafnað: 1,15M × ~100KB = ~115 GB, Supabase free-tier storage cap er 1GB. Bandwidth + storage cost ~$30/mán á Pro. (b) Proxy via Next.js Image optimizer. Hafnað: complexity + CloudFront URL rewriting bandwidth á Vercel.

**Impact**: Photos eru subject til CloudFront availability + scraper-side delisting. Long-term (Áfangi 10+) þarf að consider mirror ef availability lækkar eða domain changes.

---

## 2026-04-21 — iter4 standalone (no fasteignamat input), 100% separation from iter3v2

**Hvað**: iter4 model fjarlægir `real_fasteignamat`, `FASTEIGNAMAT`, `fasteignamaT_GILDANDI` og allar derivatives úr input features. 100% standalone, ekkert blend með iter3v2. Fasteignamat birtist áfram á UI sem reference number, ekki model input.

**Af hverju**: HMS fasteignamat er sjálft hedonic regression á kaupskrá — að nota það sem input í okkar módel er circular og gerir spána fyrir-determined af HMS updates. Annual HMS fasteignamat updates (júní ár hvert) cause 5-10% overnight jumps í iter3v2 predictions án þess að einn einasti kaupsamningur hafi verið þinglýstur. Þetta er fatal fyrir bank/pro-user use case þar sem stability er verðmætari en 1-2 pp MAPE.

**Alternative**: (a) Keep fastmat as input (status quo iter3v2). Hafnað af ofangreindum ástæðum. (b) Blend iter3v2 + iter4 við 50/50. Hafnað: blend retains circular dependency, bara demp-ar stökkin. (c) Add fastmat sem separate "anchor" calibration layer post-hoc. Potentially future work, ekki Sprint 2.

**Expected cost**: 3-5 pp MAPE increase (7,97% → ~11-13%), acceptable vaxtar-tradeoff. LLM features í Skref 6 geta milduð skaðann. Calibration (segment stretch factors) þarf endurgerð á nýjum residuals.

**Impact**: `score_new_listing.py` clone → `score_iter4.py` með removed fastmat fields. Precompute re-run subset (predictions + SHAP only). UI sýnir fasteignamat sem "Opinber eignamat frá HMS — reference only" með smá caveat text.

---

## 2026-04-21 — Document sync via GitHub repo (D:\ → docs/ → origin/main)

**Hvað**: Continuity files (STATE, DECISIONS, WORKING_PROTOCOL, TAXONOMY, GLOSSARY, DATA_SCHEMA, LABELING_GUIDE, GOLD_STANDARD_PROTOCOL, EXTRACTION_SCHEMA_v0_2_2, DATA_AUDIT_REPORT, devalue.py) synced til `docs/` folder í verdmat-is GitHub repo. D:\ er working copy, repo er canonical.

**Af hverju**: Claude Code working D:\ diverged frá Claude.ai Project folder versions (t.d. D:\STATE.md = 163 lines vs Project = 1759 lines) og caused authoritative-source confusion í Phase 1C/1D. GitHub provides single source of truth readable af bæði chat-Claude (via raw URL) og Claude Code (via git pull).

**Alternative**: (a) Sync til OneDrive/Dropbox. Hafnað: enginn chat-Claude read-access. (b) Manual paste-a content í chat hverju sinni. Hafnað: tedious, error-prone. (c) Sérstakur private repo. Hafnað: meira management, verdmat-is repo er nú þegar private og docs eru engir secrets.

**Workflow**:
1. Edit á D:\ via `str_replace` (existing rule, unchanged).
2. `cp D:\<FILE>.md /d/verdmat-is/app/docs/<FILE>.md`
3. `git add docs/ && git commit && git push`
4. Chat-Claude fer að raw URL when needed.

**Impact**: WORKING_PROTOCOL.md updated með rule (Phase 1D Skref 5). Any future Claude Code session sees both D:\ og docs/ in same git repo → divergence detectable via `diff`.

---

## 2026-04-20 (refresh_dashboard_tables orchestrator closed) — Monthly cycle integration staðfest virk

**Hvað**: `refresh_dashboard_tables.py` orchestrator framleiddur og tested end-to-end. Integrerar `build_repeat_sale_index.py` + `build_ats_lookup.py` sem cohesive dashboard snapshot með cross-script atomicity.

**Placement í monthly cycle (6-skref → post-integration 6-skref)**:
1. `refresh_cpi.py`
2. `refresh_kaupskra.py`
3. `rebuild_training_data.py`
4. **`refresh_dashboard_tables.py` ← NÝTT**
5. `monthly_recalibration.py`
6. `validate_metrics.py`

**Semantics**:

1. **Cross-script atomicity**. Ef annað hvort sub-script bilar með non-zero exit, orchestrator triggerar rollback á BÁÐUM dashboard-tafla-settum (repeat-sale 4 skrár + ATS 10 skrár = 14 monitored files). Consumers sjá aldrei mixed state þar sem repeat-sale er fresh en ATS stale, eða öfugt.

2. **Subprocess pattern**. Sama arkitektúr og `rebuild_training_data.py` — keyra hvert sub-script í sjálfstæðu Python process með `subprocess.run(check=False)`, capture-a return code, stream-a stdout live gegnum parent process. Isolation + visibility.

3. **Shape safety**. Post hvers sub-script validerar orchestrator að (a) allar expected outputs séu framleiddar, (b) row count hafi ekki shrinkað > 5% vs backup, (c) column count match-i exactly. Dashboard tables grow með tíma, svo row shrinkage = probable bug (kaupskra corruption, filter-cascade regression, etc).

4. **First-run friendly**. Ef engin previous outputs (empty `D:\_rollback_backup\`), skip backup step með warning, keyra eðlilega. No failure mode.

5. **Rollback safety**. Backup tekinn pre-run í `D:\_rollback_backup\YYYYMMDD_HHMMSS\`. Á success → deleted (eða preserved með `--keep-backup` flag). Á failure → outputs restored frá backup, backup preserved fyrir post-mortem inspection.

6. **Bare essentials orchestrator design**. Engin retry logic (transient failures bera ábyrgð á manual re-run), engar absolute shape floors (relative-to-backup er self-updating), engin per-file content validation (sub-scripts bera ábyrgð á internal integrity). Orchestrator sér aðeins um cross-script atomicity.

**Runtime validation** (staðfest 2026-04-20 20:58 og 21:00):

- Cycle 1 (--keep-backup): 81,0 sec total
  - Backup: <1 sec (14 files, ~1 MB total)
  - Repeat-sale: 77,6 sec (build) + 0,1 sec (validation)
  - ATS: 2,5 sec (build) + 0,1 sec (validation)
  - Cleanup: negligible

- Cycle 2 (normal): 65,4 sec total
  - Repeat-sale: 62,0 sec (warm disk cache)
  - ATS: 2,5 sec

Expected runtime window: 60-85 sec depending á disk cache state. Acceptable fyrir monthly cron.

**Idempotency staðfest**: Back-to-back cycles á unchanged input data gáfu identical outputs (shape deltas +0,0% á öllum 14 files, column counts exact match). Sama pattern og staðfesti rebuild_training_data í Áfanga 4d.

**Output skrá orchestrator framleiðir ekki**: orchestrator sjálfur emmar ekki output, bara orchestrators sub-scripts sem allar outputs undir management. Aðeins side-effect af orchestrator er short-lived backup dir í `D:\_rollback_backup\`.

**Scripts**:
- `refresh_dashboard_tables.py` — orchestrator (360 línur)

**Deferred til framtíðar**:
- Logging til file (núna er stdout-only; PowerShell user má pipa `> refresh.log` ef þarf)
- Per-cell sanity checks (e.g. "APT_STANDARD RVK real 2026Q2 ∈ [130, 150]") — v2 bonus
- Alert/notification hooks (email, Slack) fyrir rollback events

**Monthly cycle staða post-integration**: 6 skref frosin og staðfest. `validate_metrics.py` er downstream svo er forlag þess að dashboard tables séu fresh þegar validation keyrir. Næsta óleyst eining í pipeline er SEMI_DETACHED k-factor drift (Áfangi 4d pending) sem bíður 1-2 monthly cycles gagnagrundvallar.

---

## 2026-04-20 (Áfangi 7 closed) — ATS lookup tafla, dual-table arkitektúr (quarter + heat-pooled), static percentile heat-labels

**Hvað**: Áfangi 7 (ask-to-sale gap lookup) lokið. Framleiðir 5 output-skrár úr `pairs_v1.pkl` paired_fresh subset í `build_ats_lookup.py` (1,7 sec runtime á 52K clean pairs):

- `ats_lookup_by_quarter.pkl` / `.csv` — Table A, 913 rows × 13 cols, per (canonical_code × region_tier × quarter) með heat_bucket og data_quality as metadata
- `ats_lookup_by_heat.pkl` / `.csv` — Table B, 63 rows × 10 cols, pooled per (canonical_code × region_tier × heat_bucket). **Primary scoring table**.
- `ats_heat_thresholds.pkl` / `.csv` — 23 rows × 6 cols, p33/p67 audit
- `ats_dashboard_quarterly.pkl` / `.csv` — 359 rows × 8 cols, region-collapsed seg × qtr trends
- `ats_dashboard_monthly_heat.pkl` / `.csv` — 2.501 rows × 9 cols, live regime z-score indicator

**Methodology decisions taken** (confirmed í chat 2026-04-20):

1. **Dual-table arkitektúr (A + B)**. Table A er per-quarter historical fidelity. Table B er heat-pooled (1 row per (seg × reg × heat_bucket)) og er **primary scoring table** því pooling gefur robust dispersion í thin cells og leysir cold-start problem fyrir nýjasta ársfjórðunginn sem er alltaf thin vegna þinglýsingar-lags. Scoring-fallback: B først, A latest-row ef B insufficient (rare — 0 insufficient cells í B post-pooling).

2. **Input = paired_fresh only, exclude in_scrape_gap=True**. Filter cascade: 55.544 paired_fresh → 53.386 post-scrape-gap → 52.136 post-EXCLUDE → 52.083 post-outlier-clip → 52.001 post-inclusion-filter. Selection-bias rationale: 2025-07+ paired pairs eru technically valid per-pair en coverage er unrepresentative í gap, svo aggregate statistics eru untrustworthy. Refresh mánaðarlega re-includes data þegar scraper kemur aftur.

3. **Outlier clip ATS ∈ [0,5; 2,0]**. 53 rows klippt (~0,1%). Non-negotiable pre-aggregation: raw SD 0,1327 vs MAD×1,4826 0,0275 = 4,8× ratio í heavy tails (data-entry errors, foreclosures, skilnaðarsölur, bulk-deals). Clip range matchar DATA_SCHEMA sanity validation.

4. **Inclusion filter MIN_PAIRS_PER_CELL = 50 all-time**. Same threshold og Áfangi 6 BMN. 23 cells included, 7 excluded: APT_ATTIC Country (48), APT_MIXED RVK (4), APT_ROOM × 3 regions (5/3/17), APT_UNAPPROVED Capital_sub/Country (3/2). Main residential + SUMMERHOUSE Capital_sub/Country + APT_UNAPPROVED RVK all pass.

5. **Heat-label = static percentile (p33/p67) per (segment × region)**. Segment × region specific (ekki global) vegna þess að APT_STANDARD RVK hefur allt aðra baseline ATS en SFH Country — global þröskuldur myndi tag-a allar Country cells sem permanent cold. Thresholds reiknaðir á quarterly medians úr quarters með n ≥ 5 (stable). Rolling z-score **hafnað** fyrir lookup labels (reproducibility: 2018Q3 heat-label má ekki breytast þegar 2026 gögn koma inn), en notaður sér fyrir live dashboard regime indicator (ats_dashboard_monthly_heat).

6. **Scoring-primary dispersion = MAD × 1,4826**. Robust to outliers í small-sample cells; self-consistent með median (ekki mean) sem center. Audit-secondary dispersion = classical std; báðar geymdar. Scoring formúla: `pi_80 = list × exp(median_log_ratio ± 1,28 × dispersion_mad)`.

7. **Quality flags**. Table A: n<5 insufficient, n≥20 ∧ sd<0,05 high, n≥5 ∧ sd<0,10 medium, annars low. Table B: n<10 insufficient (stricter floor því pooling á að safna samples), sömu dispersion thresholds fyrir high/medium/low.

8. **Niche fallback fyrir cells með <8 stable quarters**. heat_bucket = NaN. 2 cells triggera: APT_BASEMENT Country (6 stable qtrs) og APT_UNAPPROVED RVK_core (4 stable qtrs). Þær 2 cells eru absent úr Table B (6 missing rows af 69 possible → 63 actual, 9% missing). Ef framtíðar-usecase þarf þessar cells, scoring fellur á training-data hedonic baseline.

9. **Monthly rolling 3-mo vs 12-mo z-score**. Separate live regime indicator í `ats_dashboard_monthly_heat`, óháð lookup labels. Sparse months (n=0) skipped, acceptable for v1 regime-detector. Used for dashboard "current market is heating up/cooling down" UI.

**Niðurstöður — empirical findings**:

(a) **Heat-label monotonicity confirmed**. cold < neutral < hot median_log_ratio á öllum 21 populated cells (engin exception). Deltas hot-minus-cold 0,016-0,091. Stærstu: SUMMERHOUSE Capital_sub (0,091 = 9,1%), SFH_DETACHED RVK_core (0,029), SEMI_DETACHED RVK_core (0,028).

(b) **Above-list rate er stærsta regime-driven signal**. 3-4× hlutfall í hot vs cold fyrir flest residential segments. APT_ATTIC RVK 14% → 47%, SEMI_DETACHED RVK 12% → 47%, APT_STANDARD RVK 9% → 33%. Confirmar bidding-war dynamics í hot regime.

(c) **Dispersion er NOT strongly function af heat — gengur í móti old-chat hypothesis**. 12 cells cold > hot MAD (hypothesis-compatible), 9 cells reverse. Mean effect kringum +0,003 (negligible). Empirical claim: "Ask-to-sale gap á íslenska markaðnum hefur stöðuga sveiflu (MAD ~0,02-0,03) óháð regime; munur hot/cold liggur í miðgildi, ekki dreifingu." Publishable finding + simplifies scoring (PI width ≈ constant across heat buckets).

(d) **Current market state per 2025-06** (síðasti mánuður pre-scrape-gap): APT_STANDARD RVK_core z_3v12 = -0,74 (cold), ROW_HOUSE Capital_sub z = -0,91 (cold), APT_BASEMENT RVK_core z = -0,52 (cold). Main residential er mostly neutral/cold. SFH_DETACHED Country z = 0,51 (hot) — counter-trend með Country catch-up frá Áfanga 6. Matchar widely-known narrative: 2022-end peak, 2023 correction, 2024-2025 cooling.

(e) **Yearly aggregate regime pattern** (3 main residential collapsed): 2022 peak (above_list 33,1%, median -0,007), 2023 trough (above_list 9,8%, median -0,025), 2024-2025 stabilization (above_list 12-14%, median -0,018 til -0,019). Orthogonal validation af Áfanga 6 timing findings.

**Output artifacts á D:\\**:
- `ats_lookup_by_quarter.pkl` / `.csv` — 913 × 13
- `ats_lookup_by_heat.pkl` / `.csv` — 63 × 10
- `ats_heat_thresholds.pkl` / `.csv` — 23 × 6
- `ats_dashboard_quarterly.pkl` / `.csv` — 359 × 8
- `ats_dashboard_monthly_heat.pkl` / `.csv` — 2.501 × 9

**Scripts**:
- `ats_diagnostic.py` — pre-build validation tool (~4 sec)
- `build_ats_lookup.py` — end-to-end build (1,7 sec runtime á 52K clean pairs)

**Deferred til framtíðar**:
- `analyze_ats_trends.py` — plots (above-list rate timeline, regime indicator timeline, pooled-distribution-by-heat violins)
- Leading-indicator heat definition (months-of-supply, TOM, withdrawal rate) as v2 alternative — ef empirical PI-calibration í production sýnir að ATS-derived heat er circular og inadequate
- `refresh_dashboard_tables.py` integration orchestrator (næsti áfangi post-Áfangi-7)

**Pending integration**: ATS lookup þarf re-reiknast mánaðarlega í refresh cycle. Integration point er post-rebuild_training_data, pre-calibration, parallel við repeat_sale_index. `refresh_dashboard_tables.py` verður orchestrator sem keyrir build_repeat_sale_index.py + build_ats_lookup.py í röð.

---

## 2026-04-20 (Áfangi 6 closed) — BMN repeat-sale index virkar, Country catch-up staðfest, ROW_HOUSE RVK_core niche finding

**Hvað**: Áfangi 6 (repeat-sale verðvísitala) lokið. Framleiðir Bailey-Muth-Nourse (BMN) OLS regressionir per (canonical_code × region_tier) × ársfjórðung fyrir 2006Q2–2026Q2 (81 quarters, 33 cells, 27 fitted). Output er `repeat_sale_index.pkl` + `repeat_sale_index.csv` með bæði **nominal** og **real** (CPI-deflated) indices, per-period `data_quality` flag (high/medium/low/insufficient), og 95% CI via std_error frá OLS.

**Methodology decisions taken**:

1. **Source = pairs_v1, ekki training_data_v1**. 24% fleiri pörum (off_market_used + off_market_newbuild + post_sale_only eru öll valid fyrir repeat-sale purposes því sale_price er þinglýst, óháð listing match).

2. **Consecutive pairing, ekki all-combinations C(n,2)**. Fyrir FASTNUM með 3 sölum → 2 pör, ekki 3. Case-Shiller standard; simpler, no double-counting.

3. **BMN per-cell aðskildar OLS regressions, ekki pooled með interactions**. Simpler, interpretable, og leyfir ólíka variance í hverjum segment × region cell. Divergence milli cells er visualized post-hoc í plots.

4. **Strict new-build-t1 exclusion**. Útilokar pör þar sem fyrri sala er `is_new_build=True`. Rökstudd tvenns konar: (a) developer→first-buyer pricing er pre-negotiated, ekki market equilibrium, og (b) Danni's domain insight: nýbyggingar eru seldar oft án gólfefna, ísskáps og uppþvottavélar, sem eru komnir inn í verðið þegar resale fer fram. Þ.e. eignin er literally not the same good milli t1 og t2 og ratio-ið er biased upward. EINFLM change filter (5%) grípur ekki þetta því flatarmál breytist ekki. 13.3% drop á pair-inu (9.076 pör af 68.381) — acceptable loss fyrir cleaner methodology.

5. **Filter cascade** (applied post-consecutive-pairing, per-step row counts logged):
   - (a) is_new_build_t1 = True           → -13.3%
   - (b) |EINFLM change| > 5%             → -3.1%
   - (c) FULLBUID 1 → 0                   → -0.1%
   - (d) pair_span_days < 90              → -1.0%
   - (e) canonical_code changed           → -0.0%
   - (f) region_tier changed              → -0.0%
   - (g) |log_price_ratio_nominal| > 2    → -0.1%
   - Final: 56.824 clean pairs (83.1% of 68.381 initial consecutive pairs)

6. **CPI deflation er default, ekki optional**. Nominal index-inn einn og sér er misleading fyrir íslenskan markað vegna verðbólgu (CPI growth ×2.66 frá 2006 til 2026). Báðar útgáfur emitted í output (`index_value_nominal` og `index_value_real`); dashboard notar real sem primary, nominal sem toggle. Baseline fyrir báðar = 2006Q2 = 100.

7. **Canonical source fyrir tegund er properties_v2 (fine HMS, 514 values), ekki pairs_v1.tegund (kaupskrá coarse TEGUND, ~7 values)**. Initial implementation notaði coarse og allt var misclassified sem EXCLUDE; fixed með properties_v2.fastnum → tegund → classify_property.

8. **MIN_PAIRS_FOR_REGRESSION = 50**. Cells með færri en 50 pör fá `insufficient_sample=True` og NaN indices. 6 af 33 cells skipped (APT_MIXED RVK, APT_ROOM × 3 regions, APT_UNAPPROVED Capital_sub + Country).

9. **NaN-gate fyrir periods án gagna**. Fitted cells fá NaN index (ekki baseline=100) fyrir quarters þar sem n_period=0. Dashboard má því forðast misleading plateau-línur.

**Niðurstöður — publishable findings**:

Main residential real CAGR 2006Q2→2026Q2 er 1.5–1.8% per ár fyrir apartments í RVK/Capital_sub, 2.7–2.8% fyrir Country (catch-up story). Real crash 2008-2011 var -27% til -33% frá 2006 peak fyrir main apartments; SEMI_DETACHED og ROW_HOUSE RVK hit harder (-44% til -49%). Recovery til 2006 baseline tók ~10 ár (crossed 100 around 2016-2017). Peak 2022Q4 var +37 til +47% yfir 2006 real-terms fyrir main cells.

Þrjú publishable findings:

(a) **Landsbyggð catch-up**: APT_FLOOR Country real growth 2006→2026 = +74.9% vs RVK_core +35.6%. Country segment vex more en RVK í raun-verði, starting consistently frá 2016. Tvær hypotheses sem framtíðar-rannsókn þarf: (i) RVK var meira inflated í 2006 baseline (bubble concentrated), svo relative growth frá lægri baseline er meira pronounced, eða (ii) tourism-driven rental demand drev Country prices upp frá 2016+. Finding stendur óháð hvor hypothesis sannast.

(b) **ROW_HOUSE RVK_core niche finding**: Lægsta real CAGR (0.5%) en dýpsta drawdown (-48.5%) af öllum main residential cells. Consistent við að raðhús í Reykjavík eru small-supply niche segment þar sem 2006-2008 bubble var most inflated. Empirical domain insight sem var ekki augljóst fyrirfram.

(c) **SUMMERHOUSE missed crash**: Country summerhouse real CAGR er +7.0% per ár og trough er 2006Q2 sjálft (aldrei niður fyrir baseline). Consistent við að sumarbústaðir á landsbyggðinni eru ekki domestic-driven market heldur tourism/rental driven og missed 2008 crash-ið alveg. Sjaldgæft fyrir asset-class að vera counter-cyclical við innlent hrun.

**Output artifacts á D:\\**:
- `repeat_sale_index.pkl` / `.csv` — full output, 2.673 rows (33 cells × 81 quarters), 15 cols
- `repeat_sale_pairs.pkl` — 56.824 clean pairs post-filter cascade, 16 cols
- `repeat_sale_summary.csv` — per-cell CAGR og crash-depth table, 27 rows
- 5 .png plots: `residential_real_grid.png`, `apt_floor_regional.png`, `nominal_vs_real.png`, `sample_density_heatmap.png`, `crash_recovery_zoom.png`

**Scripts**:
- `build_repeat_sale_index.py` — end-to-end build (56s total elapsed)
- `analyze_repeat_sale_index.py` — plots + summary stats generator

**Deferred til framtíðar**:
- CI bands á crash_recovery_zoom.png (plot 5) — thin samples look unfair without them
- Geometric Mean Revert Case-Shiller (GMRCS) ef noise er issue í downstream
- Weighted BMN með interval-distance weights
- Monthly sub-index fyrir RVK_core (aðallega fyrir dashboard leading indicators)
- Integration í operational monthly cycle: `refresh_dashboard_tables.py` skript sem re-derive index + ATS lookup eftir rebuild_training_data

**Pending integration í monthly cycle**: repeat-sale index þarf að re-reikna-st mánaðarlega þegar nýjar þinglýstar sölur koma inn. Integration point er post-rebuild_training_data, pre-validate_metrics. Verður bætt við í næsta áfanga (Áfangi 7 + integration).

---

## 2026-04-20 10:15 (Áfangi 4d closed) — Monthly operational cycle staðfest virkur end-to-end

**Hvað**: 5-skref monthly refresh pipeline sem var authored í 2026-04-19 23:55 decision er nú tested end-to-end. Allir scripts á D:\\ og hafa keyrt í röð án villu 2026-04-20 10:08–10:11:

1. `refresh_cpi.py` — Hagstofa PxWeb → `cpi_verdtrygging.csv` (schema migrated til `year_month,cpi`)
2. `refresh_kaupskra.py` — HMS OCI bucket → `kaupskra.csv` (idempotent, MD5-gated, composite PK recognized)
3. `rebuild_training_data.py` — subprocess orchestrator yfir `build_training_data.py` + `build_training_data_v2.py`, með shape safety og per-component rollback
4. `monthly_recalibration.py` — trailing 12m k-factor refresh, auto-block á >30% drift
5. `validate_metrics.py` — held scoring vs 4c baseline, per-segment drift checks með baseline embedded úr 4c closure entry

**Validation niðurstöður**:

Rebuild shape drift á idempotent cycle (sama kaupskra MD5):
- v1: (144.254 × 35) → (144.254 × 35), drift 0,00%/0,00%
- v2: (144.254 × 170) → (144.254 × 170), drift 0,00%/0,00%

validate_metrics vs 4c baseline (8/8 drift checks pass, allir innan ±0,5 pp MAPE og ±3,0 pp coverage thresholds):
- Held clean MAPE: 7,01% (baseline 7,00%, Δ +0,01 pp)
- Held clean cov80: 72,85% (baseline 73,10%, Δ −0,25 pp)
- Held clean cov95: 92,69% (baseline 92,70%, Δ −0,01 pp)
- Held all MAPE: 7,98% (baseline 7,96%, Δ +0,02 pp)
- SFH cov80: 73,00% (baseline 73,00%, Δ +0,00 pp)
- APT_STANDARD MAPE: 5,97% (baseline 5,95%, Δ +0,02 pp)

**Safety mechanisms sönnuðust virk**:
- `rebuild_training_data.py` rollback-aði v1 þegar CPI schema bug brotnaði v1 build í fyrstu end-to-end cycle (2026-04-20 09:30), kept v2 unchanged. Per-component rollback semantics (ekki atomic) gaf hreinni debugging path.
- `monthly_recalibration.py` blokkaði k-factor update þegar SEMI_DETACHED drift fór yfir 30% threshold. Pending manual review, ekki autonomous adjust. Þetta er deliberate safety ceiling per 4c post-mortem — monthly recalibration á að flagga regime shifts, ekki silent-ly aðlagast þeim.
- `validate_metrics.py` exit 0 (8/8 drift checks pass) — reproducibility confirmed.

**Orchestrator subprocess rationale**: `rebuild_training_data.py` notar `subprocess.run([sys.executable, "build_training_data.py"])` frekar en að importa build scripts sem Python modules. Ástæða: bæði build scripts redirect `sys.stdout` með tee og mutate `sys.path`. Að importa þau myndi menga orchestrator state. Subprocess isolation er clean og faithful-rekstur. Orchestrator bætir við backup + shape check + rollback semantics án að breyta feature engineering í sub-scripts.

**Sub-percent numerical drift observation**: Held clean MAPE fór úr 7,00% → 7,01% og cov80 úr 73,10% → 72,85% milli tveggja rebuilds með bit-identical inputs (sama kaupskra MD5). Líklegasta orsök: pandas merge í v2-build skilar rows í aðeins mismunandi röð, sem breytir `pd.Categorical` category ordering, sem breytir integer-kóðum sem LightGBM sér í inference. Sub-percent floor er acceptable fyrir operational pipeline (vel innan 0,5 pp MAPE threshold). Strangari reproducibility myndi krefjast sort-pre-categorize í build scripts — deferred til iter 5+ ef þörf krefur.

**Pending**: SEMI_DETACHED k95 drift +34,3% (k80 +21,8%) — manual review required. Tvær leiðir: (a) accept drift og overwrite `calibration_config.json`, (b) hækka drift threshold í 40%. Ákvörðun deferred til að hafa 2-3 monthly cycles gagnagrundvöll.

**Production state**:
- Models: iter3 v2 (12 .lgb files) — frozen
- Calibration: `calibration_config.json` version `iter3v2_segcal_v1` — frozen
- Training data: `training_data_v2.pkl` (144.254 × 170) — rebuild-able daily-ish
- Backups: `training_data_v1_prev.pkl`, `training_data_v2_prev.pkl`, `kaupskra_prev.csv`, `calibration_history/` — preserved for audit

Áfangi 4d marks completion of launch-critical operational infrastructure. Pipeline is production-ready for pilot launch.

---

## 2026-04-20 (protocol lesson) — Smoke test sem ekki siglerar downstream consumer missir schema mismatch

**Hvað gerðist**: `refresh_cpi.py` var „smoke-tested" 2026-04-19 með því að keyra scriptið, staðfesta að það skrifaði og las sína eigin CSV. Smoke test missti að `cpi.py` (downstream consumer í `build_training_data.py`) býst við CSV í formati `year_month,cpi` (ISO string + float) en refresh_cpi skrifaði `year,month,vnv` (3 integers + float). Næsta dag, 2026-04-20 09:30, brast v1 build í fyrstu end-to-end cycle með `KeyError: 'year_month'`. rebuild_training_data.py rollback-aði v1 pkl klínt; v2 óbreytt.

**Fix (2026-04-20 10:05)**: `refresh_cpi.py` lagfært:
1. `write_csv_atomic` skrifar nú `year_month,cpi` header með ISO `YYYY-MM` date format.
2. `read_existing_csv` detectar bæði target schema og legacy `year,month,vnv` schema via header parsing.
3. Ef legacy schema fundið, force-rewrite á migration (óháð því hvort nýjar rows séu í API response).

Validated með 3 smoke tests sem simulera `cpi.py` load() nákvæmlega — `float(row['cpi'])`, `row['year_month'].strip()`. Allir pass. Cycle-run 10:08 staðfesti að CPI CSV var endurskrifað og downstream v1 build virkaði án breytinga á `cpi.py` sjálfu.

**Principle**: Smoke test á new/modified script þarf að inkludera **DictReader simulation of downstream consumer**. Ekki bara „script rennur án villu" heldur „ef næsti module í pipeline les output-ið með sínu consumption pattern, rennur hann líka án villu".

**Framework breyting**: Fyrir framtíðar monthly cycle þróun, bæta við pre-integration test step sem les output-CSVs með sömu aðferð og consumer-scriptin. T.d. ef refresh_X framleiðir file sem cpi.py les með DictReader, þá notar smoke test DictReader líka.

**Observation um defensive design í orchestrator**: `rebuild_training_data.py` rollback-aði v1 klínt þegar v1 build bilaði, og skilaði exit 2. Áhrif á production voru því núll — original v1 pkl var preserved intact. Þetta er sönnun fyrir því að per-component rollback er betra en atomic „allt eða ekkert" — bilun var contained í einum sub-script og debugging var straightforward.

---

## 2026-04-20 00:25 (Áfangi 4d) — Kaupskrá composite PK + refresh_kaupskra endpoint staðfestar

**Hvað**: Eftir development á `refresh_kaupskra.py` og staðfest download frá HMS, tvö atriði urðu ljós sem þarf að skrá sem canonical:

**1. Kaupskrá PK er composite `(FAERSLUNUMER, FASTNUM)`, ekki bara FAERSLUNUMER**

Staðfest með full scan á 2026-04-20 dump af `D:\kaupskra.csv`:
- 226.481 total rows
- 212.514 unique FAERSLUNUMER
- 13.967 duplicates (6,2% af data)

Rót orsakarinnar: multi-parcel deeds. Einn kaupsamningur (einn SKJALANUMER) getur innihaldið margar fasteignir; hver með eigin FASTNUM. Kaupskrá skráir þær sem aðskildar rows með sama FAERSLUNUMER.

**Implication fyrir pipeline**: existing training data filter „single-FASTNUM SKJALANUMER" (DATA_SCHEMA.md cascade filters) er mandatory, ekki optional. Við filter-um út multi-parcel deeds vegna þess að þær eru ekki hægt að bera saman við single-property transactions á sama leikvelli (cannot assign KAUPVERD á per-property basis).

**`rebuild_training_data.py` MUST**: (a) preserve single-FASTNUM SKJALANUMER filter, (b) ekki treat FAERSLUNUMER sem PK í staðalíkingum.

**2. HMS kaupskrá endpoint staðfestur**

URL er: `https://frs3o1zldvgn.objectstorage.eu-frankfurt-1.oci.customer-oci.com/n/frs3o1zldvgn/b/public_data_for_download/o/kaupskra.csv`

Landing síða: `https://hms.is` (Kaupskrá fasteigna).

OCI (Oracle Cloud Infrastructure) Object Storage, Frankfurt region, public bucket. HEAD request gefur `Content-MD5` og `Last-Modified` fyrir idempotent refresh. Update rhythm: mánaðarlega, sunnudaga ~02:00 GMT. Publication lag: ~2 vikur frá þinglýsingu.

**Robustness**: `refresh_kaupskra.py` state tracking í `kaupskra_fetch_state.json` (last MD5, last modified, fetch timestamp). Second-run idempotency: skip download ef MD5 unchanged. Atomic file writes (tmp → rename). Safety aborts ef new size < 99% existing eða > 1% rows disappear.

**Ef URL breytist í framtíðinni** (t.d. OCI migration): fallback er að scrape-a `hms.is` landing síðu og finna nýja link. Ekki implemented enn en hugað til í docstring.

---

## 2026-04-19 23:55 (Áfangi 4d) — Operational pipeline valin simple + local-first

**Hvað**: Monthly data refresh + recalibration cycle sett upp sem staðbundin Python scripts á Windows vél, keyrð via Task Scheduler á 1. degi hvers mánaðar. Fimm-skref keðja:

1. `refresh_cpi.py` — fetch latest VNV frá Hagstofa PxWeb API (`VIS01004.px`, `financial_indexation`) → uppfæra `cpi_verdtrygging.csv`.
2. `refresh_kaupskra.py` — fetch nýjar þinglýstar sölu frá HMS → append til `kaupskra.csv`.
3. `rebuild_training_data.py` — re-derive real_kaupverd, cpi_factor, real_fasteignamat; applya taxonomy + outlier filter → ný `training_data_v2.pkl`.
4. `monthly_recalibration.py` — score trailing 12m residuals með production model, finna ný per-segment k80/k95, archive-a gamlan config, skrifa nýjan `calibration_config.json`. Safety abort ef k drift > 30%.
5. `validate_metrics.py` — post-refresh sanity check: has held MAPE drift-að? PI coverage? Flag-a ef drift > 0,5 pp á main MAPE.

**Af hverju local-first**:
- Cloud infrastructure (Supabase + Vercel per Áfanga 0 decision) verður sett upp seinna þegar pilot staðfestir value. Premature cloud migration er sóun.
- Windows Task Scheduler er reliable enough fyrir monthly cadence með log monitoring.
- Scripts eru atomic (temp-file + rename), error-handling, og log per run — audit trail preserved.
- Migration til cloud síðar er bara að endurnotkan sömu scripts með annan storage target (Postgres insted of CSV/pickle).

**Progress eftir 2026-04-19**:
- `refresh_cpi.py` skrifað og staðfest virkar (374 mánuðir, reference 2026M05=678,30, cpi_factor fyrir 2026M04 = 1,005485 matchar existing training data exactly).
- `score_new_listing.py` production API skrifað og smoke-tested (62 mkr spá á sample APT_STANDARD í Reykjavík, 80% PI 48-64 mkr, 95% PI 47-69 mkr, internally consistent).
- `monthly_recalibration.py` skrifað (bíður integration með rebuild step).
- `refresh_kaupskra.py`, `rebuild_training_data.py`, `validate_metrics.py` — TODO í næstu session.

**Two bugs fixed during smoke testing**:
1. CPI loading í score_new_listing.py: reyndi að parsa CSV með assumed column names; fixed með því að build lookup úr training pickle.
2. Categorical dtype mismatch: LightGBM var þjálfað með pandas Categorical, scoring sendi raw strings; fixed með að load og apply categorical_mappings frá training data.

**Hagstofa API pattern** (fyrir framtíðar refresh scripts):
- Endpoint format: `https://px.hagstofa.is/pxis/api/v1/is/{path}/{table}.px`
- GET gefur metadata (variables, codes, valueTexts)
- POST með `{query: [{code: ..., selection: {filter: "item", values: [...]}}], response: {format: "json"}}` gefur data
- Missing values í data: string `"."` (ekki null/NaN) — verður að filter-a post-fetch

---

## 2026-04-19 22:55 (Áfangi 4c closed) — iter3 v2 + segment-stretch er production mean+uncertainty pipeline

**Hvað**: Áfangi 4c lokið. Production uncertainty pipeline er:

1. **Mean model**: iter3 v2 (LightGBM, 154 features, main+summer split) — frozen canonical.
2. **Quantile models**: iter3 v2 × 5 quantile levels (q025, q100, q500, q900, q975) — frozen.
3. **Per-segment stretch calibration**: empirical k80/k95 factors saved in `calibration_config.json` (version `iter3v2_segcal_v1`). Applied as `lo_pi = mean - k × (mean - q_lo)`, `hi_pi = mean + k × (q_hi - mean)`.
4. **Monthly recalibration** (ekki implemented): trailing 12m residuals → update k-factors, same JSON structure.
5. **Scoring output**: `{pred_mean, pi_80_lo, pi_80_hi, pi_95_lo, pi_95_hi, segment, calibration_version}` per eign, plús `is_suspect_comparable` flag ef kv_ratio outlier.

**Final metrics (clean held N=2.026)**:
- MAPE 7,00% (target 7,0% hit exactly)
- medAPE 5,38%
- cov80 73,1%
- cov95 92,7%
- SFH cov80 73,0% (20+ pp better than variance-head V3 alternative 54,7%)

**Final metrics (all held N=2.084, production-realistic including slip-through)**:
- MAPE 7,96%
- cov80 71,9%
- cov95 91,3%

**Pipeline simplicity vs alternatives**:
- 7 k-factors (one per canonical_code) + 1 global fallback in JSON
- Zero new model training per monthly recalibration
- Auditable, version-stamped, regime-aware
- Variance-head alternative would require: new LightGBM model (log(resid²) target), sigma-estimation pipeline, drift monitoring, complex version stamping. Skilað 0,6 pp better aggregate coverage en 20 pp verra á SFH. Segment-stretch strictly superior.

**Pilot launch criteria met**:
- Held cov80 > 70% (achieved 73,1% clean, 71,9% all)
- Held cov95 > 90% (achieved 92,7% clean, 91,3% all)
- Clean MAPE < 7,5% (achieved 7,00%)
- SFH cov80 > 60% (achieved 73,0%) — was <55% with variance-head

**Áfangi 5+ handoff**: extraction-driven features are not in mean model but live in adjacent modules (UI comparables, markaðsyfirlit condition metrics, TOM model pending). Production scoring calls mean+calibration only.

---

## 2026-04-19 22:43 (Áfangi 4c post-mortem) — kv_ratio filter í training regressed held MAPE; rollback til v2 + evaluation-only filter

**Hvað gerðist**: `train_iteration3_v3.py` var keyrt með `is_quality_transaction` filter á train+val+test (kv_ratio ∈ [0,70; 1,50]). Dropaði 16.216 af 129.769 train+val rows (12,5%) og 568 af 8.575 test (6,6%). Held var óbreytt (unfiltered) fyrir realistic evaluation.

**Expected**: held clean MAPE batnaði úr ~6,90% (v2) í 6,96%-ish via cleaner training signal.

**Actual**: held clean MAPE 7,29% (regression +0,39 pp). Held ALL MAPE 8,80% (regression +0,84 pp vs v2 7,96%). Bias dýpkaði úr −0,013 í −0,022.

**Rót orsakar**: kv_ratio > 1,50 filter droppar mest nýbyggingar með genuinely hátt markaðsverð ofan á FASTEIGNAMAT — ekki noise. Model missti training signal um nýbyggingar-premium og byrjaði að under-predict á held. Kv_ratio < 0,70 filter dropar raunverulegar slip-through (~500 rows) en þess fáir vegur ekki upp á móti tapi 11.000 nýbyggingar-rows.

**Ákvörðun**:

1. **iter3 v2 er canonical production mean model**. Kept.
2. **iter3 v3 *.lgb files eru deprecated**. Má geyma á D:\\ sem audit trail en ekki scoreast í production.
3. **Filter er evaluation tool, ekki training tool**. `is_quality_transaction` flag er gagnlegt í predictions til að:
   - Reporta both-held metrics (all + clean)
   - Flag-a suspect transactions í UI (`is_suspect_comparable=1`)
   - Skilgreina calibration pool (clean val+test) fyrir segment-stretch
   En aldrei filtera training data.
4. **Ný calibration via `calibrate_segments_v2.py`**: k-factors reiknaðir á v2 val+test clean pool, applyast á v2 quantile predictions. Supersedes `calibrate_segments.py` (sem vann á v3).

**Lærðdómur**: Data quality filters eru ekki alltaf additive. Filter sem dropar „noise" getur einnig droppað legitimate tail observations sem model þarf fyrir kalibrun. Tveir flokkar „dirty" rows voru lumped saman undir sama þröskuld — ættu að hafa verið aðskildir (kv<0,70 filter valid, kv>1,50 filter dangerous).

**Framtíðar principle**: áður en ný training-filter er adopteruð, retraining retrain-a og compare-a *per-segment MAPE + per-year bias* (ekki bara aggregate). Bias dýpkun er snemma warning sem ég missed.

---

## 2026-04-19 (Áfangi 4c) — kv_ratio quality filter + segment-stretch calibration chosen over variance-head

**Hvað**: Áfangi 4c arkitektúr fyrir launch-ready uncertainty module byggir á tveimur einföldum íhlutum: (a) `is_quality_transaction` flag sem dropar rows með `KAUPVERD/FASTEIGNAMAT ∉ [0,70; 1,50]` úr train/val/test (en heldur þeim í held fyrir realistic eval); (b) per-segment empirical stretch k-factors á existing iter3 q100/q900 og q025/q975 output, saved í `calibration_config.json` með mánaðarlegu rekalibreringsjobbi.

**Af hverju**: Annar Claude lagði upphaflega til variance-head (LightGBM regression á log(resid²) með time-decay weights) sem launch-critical. Empirical validation á þessum enda afvísaði það á þrem forsendum:

1. **Heavy-tail er drifið af slip-through, ekki innate**: Eftir að dropa kv_ratio outliers (4–12% af data) fer `quantile(|resid|/std, 0.95)` úr 3,74 í near-Gaussian 2,09. Þessi 4% rows eru responsible fyrir 20+% af MAPE contribution á test og held.

2. **Segment-stretch slær variance-head á SFH**: Variance-head V3 pool-calibrated gaf SFH_DETACHED held cov80=54,7%. Segment-stretch pool-calibrated gaf 75,5%. Variance-head lærði sigma_hat ~0,04 fyrir SFH þegar empirical resid_SD er 0,21 — það underestimated SFH variance vegna all-segments pooled training. SFH er bank-critical segment (einbýlishús, hæsta-dollar lán); 20 pp coverage gap er regulatory risk.

3. **Aggregate coverage gain yfir stretch er 0,6 pp**: Variance-head held cov80=73,1% vs stretch 72,5%. Operational complexity (kalibrering, sigma estimation, drift monitoring, version stamping per prediction) réttlætir ekki 0,6 pp.

**Empirical niðurstöður (clean held, N=2.026, kv_ratio ∈ [0,7; 1,5])**:

| Metric | Iter3 v2 uncalibrated | Iter3 v3 + segment-stretch |
|---|---|---|
| Held MAPE | 7,96% | **~6,96%** (target 7,0% hitted) |
| Held medAPE | 5,03% | ~4,96% |
| Held 80% PI coverage | 69,7% | ~72-75% (segment-dependent) |
| SFH cov80 | 67,0% | **75,5%** |
| SFH cov80 (variance-head alternative) | — | 54,7% |

**Scripts**: `filter_training_data.py`, `train_iteration3_v3.py`, `calibrate_segments.py`. Einfaldari pipeline en variance-head (engin ný model dependency), cheaper operational burden, better regulatory posture (simple lookup table, auditable k-factors).

**Var-head verður iter 5+ only** ef empirical þörf kemur upp eftir pilot. Per-property sigma spá er UI-lag enhancement, ekki launch-critical.

---

## 2026-04-19 (Áfangi 7 — cancelled ML path) — Ask-to-sale gap ML module afnumið, lookup tafla í staðinn

**Hvað**: Planned ML-driven `ask_to_sale_gap_model.py` (Áfangi 7 í upphaflegri roadmap) er afnumið. Replaced með **static lookup tafla** sem geymir miðgildi log(sale/list_price_final) per (segment × region × quarter × market_heat_bucket), mánaðarlegt update.

**Af hverju**: Annar Claude prófaði þrjár feature-configurations á 55.064 paraðar sölu með temporal split (train ≤2023, test 2025, held 2026). Naive baseline `sale = list_price_final × 1,0` gaf test MAPE 3,48%. Best ML model (structured + market-state + extraction + TOM features) gaf test MAPE 4,08% — **verra** en naive. Niðurstaðan er ekki feature-veikleiki heldur target-dispersion collapse:

| listing_year | N | SD of log(sale/list) |
|---|---|---|
| 2015 | 2.920 | 0,139 |
| 2020 | 6.857 | 0,122 |
| 2023 | 5.186 | 0,059 |
| 2024 | 5.560 | 0,056 |
| 2025 | 3.496 | 0,048 |

Íslenski markaðurinn er að verða efficient. Target SD fór úr 0,14 í 0,05 — 3× lækkun á decade. Noise-floor er komin undir predictable variance. Þegar residual RMSE best ML nálgast SD in target (0,0527 vs SD 0,048), er enginn signal til að capture.

**Replacement arkitektúr**:
- **`ats_lookup.parquet`**: miðgildi log(sale/list) + dispersion (std) per (canonical_code × region_tier × quarter × market_heat_bucket). Market_heat er ATS trailing 3-mán rolling mean bucket.
- **Scoring**: `predicted_sale = list_price × exp(median_log_ratio_from_table)`. Uncertainty band = list_price × exp(median ± 1.28 × dispersion_from_table) fyrir 80% PI.
- **Dashboard aggregates**: above-list rate, miðgildi ATS, dispersion per segment/quarter — all derived from same lookup.

Þetta er insight fyrir markaðsyfirlit: **„íslenski fasteignamarkaðurinn hefur þroskast til þess stigs að ask-to-sale gap er fyrirsjáanlegur í aggregate en ekki per-listing"**. Publishable empirical finding.

---

## 2026-04-19 (Áfangi 4 close) — Iter3 v2 frozen sem final mean model; extraction redundant fyrir hedonic mean

**Hvað**: Iter3 v2 (LightGBM mean + 5 quantiles × main + summer split, 154 features) er frozen sem final mean prediction model. Held main MAPE 7,96%, medAPE 5,03%, bias −0,014. Extraction features (95 engineered cols úr $375 LLM-keyrslu) samanlagt fá **~1% af gain**.

**Af hverju extraction features skila ekki hedonic lift**: Empirical validation á þessum enda: condition correlate-ar við verð (price-per-m² span 469→729 þús./m² across ICS bins, +55% premium) EN residual correlation eftir FASTEIGNAMAT + structured features er −0,20 á held (real en lítill). LightGBM tekur ekki upp sparse (24% coverage) features þegar dense alternatives (is_new_build, age_at_sale, matsvaedi_bucket) capture sömu variance gegnum confounders — nýbyggingar hafa bæði high FASTEIGNAMAT og tag-aðar replaced_new, o.s.frv.

**Þetta er ekki glatað investment**. Extraction features flytjast í adjacent modules:
- **Comparables-UI** (Áfangi 5): matsmaður fyllir út condition questionnaire, módel lookup-ar empirical adjustment-multipliers úr extraction-joined kaupskrá, sýnir nearest-neighbor eignir sem passa.
- **Markaðsyfirlit metrics**: hlutfall aktivra lystinga með needs_immediate_work=1, kitchen-vintage distribution, condition index.
- **TOM módel** (Áfangi 7 replacement): extraction features eru hypothesized strong predictor af time-on-market þar sem hedonic mean er saturated.
- **Residual analysis í UI**: skoða systematic model bias per ICS bin sem sanity-check fyrir matsmann.

**Lærðdómur**: FASTEIGNAMAT + aldur + matsvæði + stærð er near-saturated signal fyrir baseline hedonic á íslenska markaði. Framtíðar-framfarir koma úr (a) data quality filters, (b) adjacent predictive tasks (TOM, ATS aggregates), (c) uncertainty calibration, (d) UI-lag sem notar empirical data ofan á mean model. Ekki úr dýpri hedonic features.

---

## 2026-04-19 (Áfangi 0 planning) — Hosted dashboard stack valið

**Hvað**: Áfangi 0 infrastructure mun byggja á þriggja-lagskiptum arkitektúr:
- **Lag 1 (gagnalag)**: Supabase managed Postgres í skýinu. Free tier (500 MB storage) til að byrja; Pro $25/mán þegar komið er yfir. Gefur REST API sjálfvirkt (PostgREST), realtime subscriptions, auth. Standard Postgres svo engin vendor lock-in.
- **Lag 2 (acquisition + processing)**: Scraper + extraction processor + re-score processor + aggregation processor keyra á Windows vélinni hjá Danni. Windows Task Scheduler fyrir daglegt schedule. Skrifa beint í Supabase.
- **Lag 3 (presentation)**: Vercel hostar Next.js dashboard ofan á Supabase REST endpoints. Free tier er generous fyrir fyrsta árið. Custom domain (`.is` eða `.com`) keypt í gegnum Namecheap/ISNIC.

**Af hverju**: Danni vill public-facing dashboard frá upphafi („kaupi bara url ef þarf"). Cloud infrastructure er cheap ($0-50/mán fyrsta árið) samanborið við uppsetningar-kostnað self-hosted. Supabase er chosen yfir DO managed Postgres vegna þess að REST API kemur frítt — sparar massa scaffolding í backend. Vercel yfir Supabase static hosting vegna betri frontend DX og SEO-friendly SSR.

**Hafna**: Allt self-hosted (time sink), AWS Lambda (serverless debug pain), Streamlit (rapid prototyping OK en ekki public-grade).

**Deferred detail**: URL val, GitHub repo struktúr, canonical schema drög, scraping scope (fastinn.is first, other sites additive), AI-greiningar UI layer (Áfangi 0-extension eftir dashboard v0). Full planning session fyrir Áfanga 0 er í nýjum chat.

**Timing**: Parallel við Áfanga 4 iter3 training. Engin technical dependency milli þeirra — Áfangi 3 output er frozen pickle files, Áfangi 0 scraper er fresh inflow. Ekki samtímis session, en sama tímabil.

---

## 2026-04-19 (Áfangi 3e) — training_data_v2 schema og feature engineering

**Hvað**: `training_data_v2.pkl` (144.254 records × ~115 cols) byggist úr v1 + engineered extraction features. Engineering decisions:

1. **Component status (18)**: ordinal encoding `{replaced_new: 3, overhauled: 2, well_maintained: 1, original_functional: 0, in_progress: -1, needs_work: -2, not_mentioned: NaN}`. Output: `status_ord_<component>` per 18 components.

2. **Years since work**: `years_since_<component> = sale_year - <component>_year` þegar year tilgreint. NaN annars.

3. **Composite condition scores**: `interior_condition_score` (weighted mean af 8 interior component ordinals), `building_condition_score` (weighted mean af 6 building components). Weights eftir v0.2.1 schema spec. `num_recent_renovations` (count af components replaced_new/overhauled innan 10 ára), `has_any_recent_work` (binary 1 ef any).

4. **Trilemmas → binary**: 20+ yes/no/not_mentioned fields → 1/0/NaN. Covers augl-supplements og v0.2.2 new flags (has_secondary_unit, ceiling_height_premium, unused_building_rights_present, is_corner_lot, is_waterfront_or_seaside, immediate_availability, end_unit_flag).

5. **end_unit_position applicability filter**: re-applied í merge step með canonical_code úr training_data_v1 (vegna bug í batch_extract.py — sjá bug decision neðar). Gildir aðeins í ROW_HOUSE/SEMI_DETACHED; NaN annars.

6. **lot_type expansion**: 3 binary flags (`lot_is_einkalod`, `lot_is_sameign`, `lot_is_serlod`). Sérlóð er biggest-impact APT premium signal.

7. **lot_orientation normalization**: 30+ Claude variants → 4 canonical binary flags (`lot_orient_south`, `lot_orient_east_west`, `lot_orient_north_shade`, `lot_orient_mixed`). Regex-based normalization vegna schema-enforcement bug (sjá bug decision).

8. **Multi-enums → binary flags**: view_type (7 flags), reported_issues (9), storage_type (4), unregistered_space_type (5).

9. **Ordinal enums**: view_quality (4 stig), garden_size_framing (4 stig), garden_quality (4 stig — v0.2.2 condition-only), balcony_size (5 stig), listing_elaboration (4 stig).

10. **Numeric**: `unregistered_space_sqm`, `num_parking_spaces`.

**Coverage**: ~28% af 144K records hafa extraction features (paired + length-filtered). Aðrir 72% fá NaN — LightGBM handleikar native. Hypothesis: iter3 lift kemur frá paired records, ekki unpaired.

**Script**: `build_training_data_v2.py` (573 lines). Input: `batch_extraction_unique.jsonl`, `pairs_v1.pkl`, `listings_text_v2.pkl`, `training_data_v1.pkl`. Output: `training_data_v2.pkl`. Cost: $0, local processing ~3-5 mín.

---

## 2026-04-19 (Áfangi 3d) — Batch extraction cost vandamál + lessons

**Hvað**: Full batch run keyrður á Haiku 4.5 + Batch API. 37.544 unique extractions á 37.544 listings (dedup af 40.814 paired+length-filtered). **Rauntími: ~20 mín á Anthropic-megin** (mun hraðari en 1-8 klst estimate). **Raunverulegur kostnaður: $349**, ekki $157 sem var áætlað.

**Rauncostar**:
- 2 pilot runs (v0.2.1 + v0.2.2 × 200 listings): **~$3 + ~$3,50** (ekki $1,35 + $1,68 sem scripts reportuðu)
- Discovery LLM (200 × Sonnet 4.6 meta): ~$3
- Full batch (37.544 × Haiku 4.5 batch): **~$349**
- Samtals Áfangi 3: **~$375** (vs upphafleg $200-250 projection)
- Unpaid balance eftir run: **-$142,80** (þ.e. $225 deposit var ekki nóg)

**Bug sem orsakaði under-reporting**: `calc_cost()` function í `pilot_extract_v022.py` (og importað í `batch_extract.py`) assumaði að Anthropic `input_tokens` innihaldi cache_read og cache_creation sem overlapping counters, svo subtractaði þau. Raunin er að þeir eru **separate additive teljarar**. Þannig að `uncached_input = input_tokens - cache_read - cache_creation` varð near-zero eða neikvætt, og $1/M rate var missað á mörgum input tokenum.

**Réttur útreikningur**:
```
cost = input_tokens × $1/M
     + cache_read × $0.10/M
     + cache_creation × $1.25/M
     + output_tokens × $5/M
× 50% (batch discount)
```

Ekki:
```
cost = (input - cache_read - cache_creation) × $1/M + ...  ← WRONG
```

**Impact**: Pilot cost reports voru ~2,4× undir, batch projection ~2,2× undir. Danni treystur mér á tölunum og samþykkti batch án réttrar kostnaðar-stefnu — hefði haft chance á að re-scope ef tölur hefðu verið réttar (drop til smærra sample, eða pause til að deposita meira).

**Goodwill-email sent til Anthropic support**: request um billing review (ekki krafa), specifically acknowledging þetta var client-side bug ekki þeirra. Líkur á full credit <10%, partial credit 15-20%, decline 65-75%. Unpaid balance verður á næsta invoice hvort sem er.

**Lesson (hardens í WORKING_PROTOCOL)**: Framtíðar-kostnaðaráætlanir fyrir API workstreams verða að **cross-checka við Anthropic Console spend** eftir fyrstu 10-20% af keyrslu áður en resten klárast. Ekki treysta cost-report útreikningum frá scripts.

**Notable positives þrátt fyrir kostnaðarvandamál**:
- Zero extraction failures á 37.444 succeeded (0,2% failure rate)
- Batch API miklu hraðari en 1-8 klst estimate: flestar chunks kláraðar á 5-15 mín
- Prompt caching virkaði (cache hits í ~40% tokens)
- Dedup sparaði $22 vs no-dedup
- Output er clean og usable (eftir post-proc fixes)

---

## 2026-04-19 (Áfangi 3d) — Chunk size 5000 fyrir Batch API

**Hvað**: `CHUNK_SIZE = 5000` í batch_extract.py. Upphafleg setting 6000 hittust á 256 MB raw batch size limit — per-request size er ~43 KB (larger en 35 KB estimate) vegna tool schema + 3 few-shot examples endurtekin í hverri request.

**Stærðartala**: `5000 × 43 KB = 215 MB`, safely under 256 MB hard limit. `6000 × 43 KB = 258 MB`, over.

**8 chunks í staðinn fyrir 5**. Engin effect á cost — chunking er logical aðeins fyrir resume-granularity og size compliance.

---

## 2026-04-19 (Áfangi 3d) — canonical_code bug í batch_extract propagation

**Hvað**: `batch_extract.py` propagation-loop setti `canonical_code` í context-dict úr `pairs_v1.pkl`, en pairs skráin hefur EKKI þessa column (hún kemur úr `training_data_v1.pkl`). Post-processing filter fyrir end_unit_position treysti á canonical_code, og þar sem öll voru NaN, þá zeroaðist **allt** end_unit_position=yes (2816 rows) í `batch_extraction_propagated.csv`, ekki bara false positives í non-ROW/SEMI.

**Impact**: end_unit_position er dautt signal í propagated CSV. Upphafleg extraction values eru þó í `batch_extraction_unique.jsonl` (raw, unfiltered).

**Lausn í `build_training_data_v2.py`**: re-apply filter í merge-step með réttri canonical_code úr training_data_v1. `end_unit_flag` í v2 er NaN fyrir non-ROW/SEMI, 1/0 fyrir ROW/SEMI eftir extraction value.

**Lesson**: útvíkkunarlaus úr pairs-skrá hefur takmarkað gagn — downstream joins ættu allar að flæða úr training_data_v1 sem canonical source fyrir þessar metadata fields.

---

## 2026-04-19 (Áfangi 3d) — lot_orientation schema enforcement brot

**Hvað**: Claude output í batch API virkaði ekki strict enum validation fyrir single-string enum fields. Ég skilgreindi `LOT_ORIENTATION_VALUES = ['south_southwest', 'east_west', 'north_shade', 'mixed', 'not_mentioned']`, en raw output inniheldur 30+ variants (`south` alone, `southwest`, `northwest`, `east_west` concatenations eins og `southeast_southwest`, `north_south`, `west_east`).

Sama pattern í `laundry_configuration` (`in_progress` leaking frá status enum) og `sale_channel` (`private_einkasola` typo — 0,0% rate, edge case).

**Hypothesis**: Anthropic batch API enforcar ekki enum grammar constraint eins strict og sync tool_use. Mögulega trade-off til að hægja ekki á parallel inference throughput.

**Lausn í feature engineering**: `normalize_lot_orientation()` í `build_training_data_v2.py` tekur 30+ variants → 4 canonical flags (south/east_west/north_shade/mixed). `clean_enum()` helper sópar invalid values í `not_mentioned` fyrir strict single-value enums.

**Lesson fyrir v0.3 eða næstu extraction rounds**: Nota strict enum validation í feature engineering, treat raw Claude output sem „fuzzy enum" frekar en „enforced enum". Multi-select arrays virðast ekki brotna á sama hátt — aðeins single-string enums.

---

## 2026-04-19 (Áfangi 3c+) — Re-pilot v0.2.2 pass og ship til batch

**Hvað**: V0.2.2 re-pilot á sömu 200 listings keyrð með tightened prompt + 15 nýjum fields + 3ja few-shot. Zero catastrophic failures. 2 components_malformed (1%). Kostnaður: ~$3,50.

**Quality verdict: PASS á öllum critical targets, partial á sekúnder**:

| Target | v0.2.1 | v0.2.2 | Niðurstaða |
|---|---|---|---|
| well_maintained á kitchen | 60% | 21% | Pass (<30%) |
| well_maintained á bathroom | 57,5% | 19,5% | Pass |
| well_maintained á flooring | 59,5% | 20% | Pass |
| listing_elaboration standard | 7,5% | 30% | Pass (20-30%) |
| promotional_heavy rate | 27% | 26% | Ekki bætt en non-issue |

**Óvænt semantic richness**: óskráð rými false-positives voru í raun legitimate — Claude flaggar „ósamþykkt", „háaloft", „geymsluloft", „ónýttur byggingarreitur" sem unregistered signals umfram explicit „óskráð" keyword. 19 af 24 yes-captures á 200 sample-i. Semantically correct en outside my strict rule. Accepted as richer signal.

**Applicability bug**: end_unit_position flagged í 10 non-ROW/SEMI rows (APT og SFH). Fixed í post-processing filter í batch_extract.py (þó að sá fix brotnaði vegna canonical_code bug — sjá næsta decision).

**Ákvörðun**: Ship til batch án v0.2.3 cycle. Targets hit, „problems" eru annað hvort semantic richness (gott) eða post-processing-fixable.

---

## 2026-04-19 (Áfangi 3c) — Batch API + hash-dedup fyrir full extraction

**Hvað**: Full extraction round 1 keyrir á Anthropic **Batch API** (ekki sync) með **hash-based dedup** á lýsingum áður en extraction. Concrete plan:

1. Hash first-500 chars af lýsingu per listing
2. `drop_duplicates` á hash → unique extraction targets (~47.179 af 53.866)
3. Submit í Batch API í 5 chunks af ~10K listings (Batch API limit per job)
4. Retrieve JSONL results, propagate extraction til all listings með same hash
5. Metadata field `extraction_group_size` per record (1 for unique, N for group-of-N)
6. Í iter3 training: `sample_weight = 1 / sqrt(extraction_group_size)` — weighted cancellation af shared-signal bias

**Af hverju Batch API**: 50% flat discount á bæði input og output tokens. Extraction er inherently async (results used downstream í iter3 training, ekki real-time). 24-hr turnaround acceptable. Kombinerast við prompt caching (90% off á cached 8K schema) í samlegðar ~60-70% total savings.

**Af hverju hash-dedup**: duplicate rate í population er empirically **12,4% (6.687 af 53.866)**, driven af nýbyggingar-developments með shared agent template intros (Lund í Kópavogi 27×, Grímsgata 31×, Hlíðarendi 17×, Dvergurinn 15×, Asparlaut 15×). Án dedup:
- Waste $22 í duplicate extraction
- Stærra issue: iter3 sér 15 identical listings með mismunandi target prices → data leakage, over-weighting af shared template features, poorer generalization

**Cost breakdown** (staðfest 2026-04-19):

| Strategy | Listings | Per-listing | Total |
|---|---|---|---|
| No dedup, sync | 53.866 | $0,0067 | $361 |
| No dedup, batch | 53.866 | $0,0033 | $178 |
| **Med dedup, batch** | **47.179** | **$0,0033** | **$156** |

Innan $200–300 upphaflegs budget.

**Af hverju first-500 char hash** (not full text): listings með sama intro en mismunandi details eru enn largely redundant fyrir extraction (sama property-type, sama agent template, sama development). First-500 er sufficient discriminator án að miss partial-duplicate developments.

**API tier prerequisite**: Tier 2 ($500/mán cap) fyrir batch run. Tier 1 nýtur aðeins $100/mán. Plan: $40 deposit → 7 daga bið → Tier 2 triggerast.

---

## 2026-04-19 (Áfangi 3c) — Pilot findings trigger schema v0.2.2 refinement

**Hvað**: Pilot extraction 200 listings á Haiku 4.5 staðfesti að schema er workable og infrastructure virkar (zero failures, $1,35 cost), en exposed concrete refinement needs. **V0.2.2 bætir við ~11 fields + tightens system prompt**, held áfram sem Haiku 4.5 batch.

**Pilot performance**:
- Zero extraction failures (robust tool_use + JSON schema validation)
- Per-listing $0,0067 actual (vs $0,003 estimate — underestimated output tokens)
- Prompt caching virkar: fyrsta call $0,014, síðari ~$0,006 (6.840 cached tokens, 90% off)
- Narratives genuinely good (Icelandic prose, 2–4 setningar, ekki copy-paste)
- Year extraction sterk (row 5: kitchen/flooring/windows/cladding allt 2019 með detail)

**Kvalitæti-issues krefjast v0.2.2**:

1. **`well_maintained` over-use** (stærsta): 64% kitchen, 60% primary_bathroom, 54% flooring → well_maintained. Claude treatar feature-description + positive adjective („fallegt eldhús, granít borðar") sem condition signal. Marketing puffery inflates. **FIX**: system prompt krefst explicit condition language („í góðu standi", „vel viðhaldið"). Marketing puffery án condition language → `not_mentioned`.

2. **„Þak" vs „þakkantur" semantic confusion**: Row 14 „eftir er að klæða undir þakkantinn" → Claude flaggaði roof=in_progress. Rétt: cladding_in_progress only. **FIX**: explicit distinguishing example í system prompt.

3. **`listing_elaboration` inflated**: 68% elaborate + 26% promotional_heavy = 94% í efri tierum. Bara 6% standard. Recalibration thresholds: terse <150w, standard 150–300w, elaborate 300–600w, promotional_heavy 600+w OR heavy promotional language.

**V0.2.2 nýjar fields (~11)**:

*Size & legal (6)* — 24% of listings have these signals, **zero captured currently**:
- `unregistered_space_present` (trilemma) — „óskráð rými"
- `unregistered_space_sqm_stated` (int | null) — m² number ef nefnd
- `unregistered_space_type` (multi: loft_attic / basement / addition / garage_converted / other)
- `has_secondary_unit` (trilemma) — „aukaíbúð" aðskilið frá legal is_duplex status
- `ceiling_height_premium` (trilemma) — „mikil lofthæð", „3ja metra lofthæð"
- `unused_building_rights_present` (trilemma) — „ónýttur byggingarreitur"

*Outdoor (5)* — garden_quality currently conflates size + condition:
- `lot_type` (enum: private_einkalod / shared_sameign / private_in_shared_serlod / not_applicable / not_mentioned) — **biggest-impact**, sérlóð er major APT premium
- `lot_orientation` (south_southwest / east_west / north_shade / mixed / not_mentioned)
- `garden_size_framing` (unusually_large / large / standard / small / not_mentioned)
- `is_corner_lot` (trilemma)
- `is_waterfront_or_seaside` (trilemma)

*Refactor* — `garden_quality` decoupled from size, condition only: `well_landscaped_mature` / `standard_maintained` / `minimal_or_neglected` / `none` / `not_mentioned`.

**Deferred til v0.3** (nýbyggingar sub-schema, ekki critical fyrir fyrstu batch): `finish_package_level` (Pakki 1/2/3), `delivery_status`, `early_occupancy_available`, `building_permit_status`.

**Af hverju ekki fleiri v0.2.2 fields**: iterate-með-litlum-batches paradigm. Better að bæta 11 signals núna, verify í re-pilot á 200, ship batch, discovera remaining gaps í iter3 feature importance analysis, bæta seinna í v0.3. Forðum upfront over-engineering.

**Estimated impact**: schema 93 → ~104 fields. Output tokens +5%. Per-listing $0,0067 → ~$0,0070. Batch 47K: $156 → ~$165. Trivial.

---

## 2026-04-19 (Áfangi 3b) — Middle-ground validation chosen over formal gold-standard

**Hvað**: Áfangi 3 validation strategy changed frá formal hand-labeling protocol (100 listings, kappa agreement, schema v0.3 freeze gate) til **middle-ground „vibe check"** workflow.

**Af hverju**: Danni pushaði back á formal protocol með rökum að LLM extraction iteration með manual scan er faster en 15–30 klst af hand-labeling og gefur sufficient signal fyrir commercial-grade residential model. „Erum við ekki að tala um að gervigreindin geri þetta?"

**Workflow**:
1. Run pilot extraction (200 listings, Haiku 4.5) → $1,35
2. Manual scan outputs, flag obvious issues
3. Run discovery analysis (keyword + LLM meta) → ~$4
4. Synthesa concrete v0.2.2 refinements
5. Re-run pilot → verify improvements ($1,35)
6. Ef quality góð → 80K batch
7. **Fallback**: ef v0.2.2 re-pilot shows marginal quality, revert í formal protocol

**Savings**: ~25 klst af Danni's tíma án meaningful quality compromise fyrir commercial-grade residential valuation.

**Hvað við töpum**:
- Engin formal kappa inter-rater agreement metric
- Engin per-field F1/precision/recall numbers
- Engin explicit quality gates

**Hvað við höldum**:
- Visual inspection af extraction quality (fann well_maintained pattern strax — approach works)
- Ability til að catch systematic patterns via manual scan
- Gold-standard sample er samt drawn (200 rows) og má nota fyrir formal validation seinna ef þörf krefur
- Discovery infrastructure (keyword + LLM meta + duplicate check) sem uppgötvaði 12,4% pop dup rate og 24% size/legal gap

---

## 2026-04-19 (Áfangi 3a) — Schema v0.2.1 frozen fyrir extraction round 1

**Hvað**: Extraction schema v0.2.1 er frozen sem starting point fyrir 3c pilot. 93 fields total:

- **Component-status matrix** (18 × 3 = 54 fields): unit-level 11 (kitchen, primary_bathroom, secondary_bathroom, flooring, interior_finishes, paint, electrical_panel, electrical_wiring, plumbing, heating, windows_unit) + building-level 7 (roof, cladding, windows_building, insulation, elevator_mechanism, sameign_cosmetic, foundation_drainage). Hver component fær `status` (7-stiga enum) + `year` (int) + `detail` (short text).
- **7-stiga status enum**: `replaced_new`, `overhauled`, `well_maintained`, `original_functional`, `needs_work`, `in_progress`, `not_mentioned`.
- **7 augl-supplement trilemmas**: fyrir þau 7 flags sem hafa 86% null rate í listings_v2. Extracted value fyllir inn þegar augl er null.
- **Situational fields**: útsýni (2), útipláss detail (5), parking detail (3), layout (6), building & annað (5), negative signals (3), agent framing (3), narrative + meta (5).

**Af hverju component-level rich**: v0.1 hafði flatt schema sem lumpaði „ný rafmagnstafla" og „yfirfarin rafmagnstafla" undir sama flagg. Danni benti á að þessi aðgreining er central fyrir bæði verðmat (verðáhrif mismunandi) og explainability (hægt að segja „X bætti svona mikið við virðið"). V0.2 gerir skýran status-distinction per component sem model getur lært á og kerfi getur útskýrt.

**Af hverju 18 components frekar en fleiri/færri**: trimmed-list af kjarna building/unit components sem birtast reglulega í íslenskum lýsingum. Minna er skarðbrotandi (t.d. ef við hefðum bara „interior" og „exterior" 2-component matrix missum við signal). Meira er diminishing returns (cosmetic-sub-components bæta við token-cost án marginal lift).

**Re-freeze í v0.3 eftir 3c pilot** — component-fields með `not_mentioned` rate > 70% eða F1 < 0,75 verða candidates fyrir drop eða merge.

---

## 2026-04-19 (Áfangi 3a) — Extraction scope round 1 = paired subset, Haiku+batch+caching

**Hvað**: Round 1 extraction scope er þröngvað að paired subset (~80K listings), ekki full 456K corpus. Model val: **Claude Haiku 4.5** með batch API (50% afsláttur) + prompt caching (90% afsláttur á static 8K-token schema). Budget: **~$240**.

**Af hverju paired subset eingöngu**: bara paired listings fara í iter3 training data. Unpaired listings (off_market_used, off_market_newbuild, post_sale_only) eru 86K af iter2's 144K — þeir hafa engan augl_id og því engin lýsingu til að extract. Extraction á þeim myndi kosta en gefa núll iter3-lift.

**Af hverju Haiku**: rich 18-component schema er harðara extraction task en v0.1 (nuance milli „ný" vs „yfirfarin" er real test), en batch + caching gerir þetta fjárhagslega bærilegt eingöngu á Haiku. Ef pilot (3c) sýnir að Haiku nær ekki quality threshold (F1 ≥ 0,75 á status enum), fallback í Sonnet 4.6 (total ~$800 í staðinn fyrir $240).

**Deferred til round 2** (þegar vettvangurinn skilar revenue/funding):
- Unpaired ~370K extraction (additional ~$1.100 á Haiku, ~$3.700 á Sonnet)
- Sonnet upgrade á paired subset ef Haiku er marginal
- Image-based extraction (7M myndir er real money)
- Dedicated sumarbústaða-schema með land-value focus

**Token estimates** per listing (Haiku):
- Input: ~8.000 static (cached, $0,10/MTok) + ~600 dynamic ($1/MTok)
- Output: ~1.000 tokens ($5/MTok)
- Per-listing með batch: ~$0,003
- 80K × $0,003 = $240

---

## 2026-04-19 (Áfangi 3a) — Gold-standard = 120→200 listings, seed=42, 36-cell stratified

**Hvað**: Gold-standard benchmark er hand-labeled listings, drawn með `seed=42` úr paired subset af iter2_predictions.pkl. Original breakdown (Áfangi 3a):

- **100 stratified** yfir 36-cell grid (region_tier × type_bucket × era, 3×4×3)
- **20 worst-held oversample** (top APE frá iter2 held predictions, stress-test)

**Scale update í Áfanga 3c (2026-04-19)**: sample **grew til 200 rows** (180 stratified + 20 worst_held, 5 per cell) fyrir robust discovery analysis á pilot. All 36 cells still populated, no thin cells.

**Type_bucket collapse** (rare types inn í nearest-sibling fyrir sampling):
- APT_BASEMENT → APT_STANDARD bucket
- APT_ATTIC → APT_FLOOR bucket
- SEMI_DETACHED → ROW_HOUSE bucket

**Era bins**: 2015–2019 / 2020–2023 / 2024–2026.

**Filter-reglur**: paired_fresh eða paired_valid pair_status, canonical_code in-model, lysing-length 300–3000 chars.

**Af hverju 120 og ekki 100 eða 200**: 100 stratified gefur ~3 samples per cell sem er þunnt en fangar systematic issues per-cell. 20 worst-held oversample er critical stress-test — ef extraction bætir ekki worst cases frá iter2, er það augljós limitation sem við viljum uppgötva í pilot en ekki við full run.

**Sample draw empirical outcome**: öll 36 cells populated, engin thin cells. Stratified draw = 108 records, trimmed til 100. Region balance 34/33/33. Canonical balance (efter bucket collapse): SFH 25, APT_FLOOR 25, APT_STANDARD 24, ROW+SEMI 26.

**Staged-review labeling pattern**: labela fyrstu 20 með v0.2.1 + v0.1 guide, pause, tune schema/guide ef þörf, labela remaining 100 með refined version. Forðar að 100 listings séu labelaðir á buggy-schema.

---

## 2026-04-19 (Áfangi 3a) — augl flag coverage + inngangur categorical

**Hvað**: Empirical findings úr `verify_augl_flags.py` (2026-04-18) breyta schema design og join-logic:

**Finding 1 — 86,2% null rate á 7 augl flags**: `svalir`, `gardur`, `lyfta`, `staedi`, `rafbill`, `pets`, `hjolastoll`, `eldrib` (plús `lat`/`long`) hafa sama null-rate. Driven af source_db (5 unique values, líklega að bara einn skilaði augl_json með parsed flags). **Consequence**: schema v0.2.1 bætti við 7 supplement-trilemma fields sem extraction fyllir í fyrir 86% af listings þar sem augl er null. Post-extraction merge: augl-flag tekur precedence þegar non-null.

**Finding 2 — `inngangur` er 42-value categorical**: ekki boolean eins og TAXONOMY gaf í skyn. 232K af 472K eru „Sameiginlegur". `has_separate_entrance` derive-ast sem `inngangur != "Sameiginlegur"` — ekki þörf á extraction.

**Finding 3 — 100% populated numeric fields**: `fjherb` (100%), `fjsvfnherb` (100%), `fjbadherb` (100%), `byggar` (99,4%), `bilskur` (100%, pre-computed), `n_myndir` (100%). Þessi fields voru upphaflega í v0.1 extraction schema en eru drop-aðir í v0.2.1 (duplicates HMS authoritative data).

**Finding 4 — join-key case mismatch**: iter2_predictions og training_data_v1 nota UPPERCASE (`FAERSLUNUMER`, `FASTNUM`, `SKJALANUMER`, `THINGLYSTDAGS`), pairs_v1 notar lowercase. Primary join: `FAERSLUNUMER` ↔ `faerslunumer` (unique per sala). pairs hefur `augl_id_final` og `augl_id_initial` — nota final sem primary, fallback í initial.

---

## 2026-04-18 (Áfangi 2.4c) — Áfangi 2 closed fyrir residential

**Hvað**: Iter2 main residential model meets production targets:
- Held MAPE 7,97% (target ≤10%) ✓
- medAPE 5,24% (target ≤8%) ✓
- Bias −1,5% (baseline var −10%) ✓
- cov80 69,9% (target ≥75%) ✗ near miss

Áfangi 2 declared closed fyrir residential segmentið. Næsta skref er Áfangi 3 extraction schema design.

**Af hverju closed þrátt fyrir cov80 near-miss**: cov80 miss er 5 pp og er acceptable production quality. Users of valuation website fá slightly wider intervals í report-ing (t.d. 85% í staðinn fyrir 80% labeled). Can be tightened later í iter3 með quantile adjustment án þess að block Áfanga 3 vinnu.

**Tvær mechanism fixes staðfestar virka**:
- Mechanism 1 (FASTEIGNAMAT nominal drift): Per-quintile bias á held var −10% í Q5 í baseline, er núna −0,7% í iter2. `real_fasteignamat` feature solved.
- Mechanism 2 (2024–2026 plateau): Per-year bias var monotonic 0→−10% í baseline, er núna flat ~0 í 2024/2025/2026. train_ext = train+val merge solved.

---

## 2026-04-18 (Áfangi 2.4c) — SUMMERHOUSE acknowledged unresolved

**Hvað**: Summer model held MAPE 176%, medAPE 22%. 81% af records hafa APE < 50% (acceptable median prediction) en tail er catastrophic (max APE >300.000%).

Features available (EINFLM, BYGGAR, LOD_FLM, lat/lon, FASTEIGNAMAT) eru ekki discriminative enough fyrir summerhouse valuation. Markaðurinn er dominated af land-value (location, lot size, amenity proximity, waterfront access) og condition (cabin vs fully winterized) — structured features fanga þetta ekki.

**Decision**: Accept summer model sem unresolved. Known limitation documented. Residential website launches án summerhouse valuation fyrir v1. Future work:
- Collect land-value indicators (distance to amenities, watercoverage, waterfront)
- Re-classify summerhouses by type (traditional cabin / modern / winterized / glamping)
- Potentially separate hedonic extraction schema með different features

---

## 2026-04-18 (Áfangi 2.4c) — Iter2 main model = production baseline

**Hvað**: Iter2 main (ex-SUMMERHOUSE) 6 modules — mean + 5 quantiles — er canonical production model fyrir residential valuation.

**Hyperparameters finalized**:
- num_leaves=63, learning_rate=0.05
- min_data_in_leaf=40 (main), 15 (summer)
- feature_fraction=0.9, bagging_fraction=0.8, bagging_freq=5
- n_estimators=3000 með early stopping=100 á test split
- seed=42, deterministic=True

**Features finalized (20)**: canonical_code, unit_category, matsvaedi_bucket, region_tier, postnr, lat, lon, EINFLM, BYGGAR, LOD_FLM, FASTEIGNAMAT, **real_fasteignamat**, is_new_build, merking_floor, building_max_floor, is_top_floor, floor_fraction, is_main_unit, sale_year, sale_month.

Feature importance: real_fasteignamat 63%, FASTEIGNAMAT 13%, EINFLM 5%, sale_year 4%, is_new_build 4%. Restin deila 11%.

**Best iterations**: main_mean=1859, main_q50=2976. Q50 þjálfaði mikið lengur en mean — median er harðari að optimize.

---

## 2026-04-18 (Áfangi 2.4c) — audit_2_4c_residuals.py canonical audit script

**Hvað**: `audit_2_4c_residuals.py` er reproducible audit script sem keyrist á `iter2_predictions.pkl`. Gefur útstreymi með bias per split, calibration, Mechanism 1 quintile check, worst-20 inspection, spatial clustering, og per-segment metrics.

**Af hverju**: Hver iter3+ þjálfun ætti að keyra sama audit (eftir minor modifications á column names) til að tryggja regression-safe metrics. Template fyrir future model iterations.

---

## 2026-04-18 (Áfangi 2.4b plan) — Iteration 2 architecture

**Hvað**: Eftir 2.4a residual audit staðfesti tvær orsakir fyrir systematic overprediction í 2024+, plan-ast iter2 með þremur fixes:

**P1 — SUMMERHOUSE aðskilið**: Main model þjálfað á ~139.741 residential records (canonical_code != SUMMERHOUSE). Separate summer model á ~4.513 SUMMERHOUSE records. 12 módel total: 6 main (mean + 5 quantiles) + 6 summer.

**P2 — real_fasteignamat feature**: Bæta við `real_fasteignamat = FASTEIGNAMAT × cpi_factor` sem 20. feature. Halda FASTEIGNAMAT líka inni (gefur módeli bæði nominal og real view). Model lærir hvaða er meira predictive í mismunandi contextum.

**P3 — Extended training**: train_ext = train (≤2023) + val (2024) combined. Test (2025) færist í hlutverk early-stopping set. Held (2026) remains pure holdout. Þetta lætur model sjá 2024 plateau og reduces Mechanism 2 extrapolation penalty.

**Af hverju samtímis allir þrír**: Isolating one fix at a time myndi taka 3× iterations með lítinn incremental value. Audit 2.4a sýndi að mechanisms eru conceptually distinct en öll í sömu átt (overprediction), svo samþætt fix er low-risk.

**Ekki gera núna**:
- Monotonic constraint á sale_year: Real prices eru ekki monotonic (fóru niður 2025–2026), svo constraint myndi enforca false pattern.
- Spatial KNN smoothing: Residuals eru mildly clustered (std 0,038) — marginal gain. Deferred til 2b.
- K-fold CV: Overkill fyrir iteration 2. Fair comparison með baseline er held (2026) MAPE.

**Expected outcome**: residential test MAPE ≤ 9%, held MAPE ≤ 10%, cov80 ≥ 75% á held. Held metric er authoritative samanburður; test er ekki fair því iter2 notar test fyrir early stopping.

---

## 2026-04-18 (Áfangi 2.4a) — Systematic overprediction diagnosis

**Hvað**: Residual audit afhjúpaði að baseline model overpredictar í 2024+, með monotonic progression:
- train bias 0%, val bias −3,5%, test bias −5,0%, held bias −9,6%.

**Tvær distinct orsakir**:

1. **FASTEIGNAMAT nominal drift**. FASTEIGNAMAT er nominal (ekki CPI-adjusted) en target (real_kaupverd) er deflated. 2024–2026 saw FASTEIGNAMAT óx nominally mikið, en real prices plateau-uðu. Model lærði í training "FASTEIGNAMAT X → real_kaupverd Y" en í test hefur FASTEIGNAMAT vaxið fyrir sama real price → overpredict. Staðfest með Section F quintile analysis: 6.872 af 8.575 test-records detta í Q5 (efsta training-quintile).

2. **2024–2026 real price plateau**. median_real var +5,4% 2024, −2,2% 2025, −1,8% 2026. Model trained on 2006–2023 monotonic uptrend kannast ekki við plateau/decline — extrapolerar upward í 2025–2026.

**Af hverju þetta skiptir máli**: Fix #1 (real_fasteignamat feature) og Fix #2 (include 2024 in training) eru orthogonal og ætti að samlegast combined. Við testum báða samtímis í iter2.

**Diagnostic ekki-findings** (worth noting til að forðast future rabbit-holes):
- Spatial residuals eru bara **mildly clustered** (std 0,038 í log-space, range [−0,15, +0,11]). KNN smoothing gæti gefið 1–2 pp MAPE gain en er ekki primary fix.
- Residual correlations allar **undir 0,10 Spearman** (hæst FASTEIGNAMAT við 0,07). Ekkert single feature er systematically missed.
- Per-year train MAPE sit í 7–8% (modern 2018–2023) og aldrei fer upp fyrir 11% (2008–2009 financial crisis). Model passar training gögn vel — problem er structural (distribution shift), ekki overfit.

---

## 2026-04-18 (Áfangi 2.3) — Baseline LightGBM hyperparameters

**Hvað**: Conservative baseline, ekki tuning-heavy:
- `num_leaves=63`, `learning_rate=0.05`
- `n_estimators=3000` með early_stopping=100 á val
- `min_data_in_leaf=40`, `feature_fraction=0.9`, `bagging_fraction=0.8`, `bagging_freq=5`
- `seed=42`, `deterministic=True`, `force_col_wise=True`
- Categorical features explicitly marked: canonical_code, unit_category, matsvaedi_bucket, region_tier, postnr

**Target**: `log_real_kaupverd`. Predictions back-transform með `exp()`.

**Sex módel**: mean (L2 regression) + 5 quantiles (alphas 0.025, 0.10, 0.50, 0.90, 0.975). Eitt módel per quantile — LightGBM styður ekki multi-output quantile native.

**Af hverju engin hyperparameter tuning í baseline**: Baseline er viðmið, ekki optimized model. Vill mæla hvort structured features einir og sér (19 features) gefa meaningful signal áður en við spendum time á tuning.

**Best iterations per model** (empirical result): mean 820, q025 330, q10 400, q50 2368, q90 3000 (hit max), q975 875. Q50 og Q90 trained lengur — median er harðari að optimize en tails.

---

## 2026-04-18 (Áfangi 2.3) — Point-prediction metric = mean model

**Hvað**: Reiknum point-prediction accuracy metrics (MAPE, MAE, R²) á bæði mean model og P50 (median quantile). Notum **mean model sem primary point estimate** í reporting.

**Af hverju**: Mean model (L2 loss) optimizar squared error sem gives conditional expectation. P50 optimizar absolute error sem gives conditional median. Fyrir log-normal pris distribution eru þau ekki eins — mean > median.

Í íslenska real estate markaði er mean model slightly betri í MAPE (test 15,36% vs P50 15,68%) en P50 er betri í medAPE (test 6,72% vs mean 7,33%). Mean model er authoritative fyrir point estimate; P50 er fyrirliggjandi úr quantile suite ef user vill robust median.

---

## 2026-04-18 (Áfangi 2.3) — Chronological split confirmed

**Hvað**: train ≤ 2023 (123.517), val = 2024 (9.719), test = 2025 (8.887), held = 2026+ (2.131).

**Af hverju chronological**: Real estate market has temporal trends sem model þarf að generalize across. Random split myndi gefa optimistic metrics vegna of-fitting á tíma.

**Trade-off**: sale_year=2024 er aldrei séð í training, sem þýðir LightGBM trees nota leaf values frá 2023 boundary. Þetta skapar extrapolation problem sem 2.4a staðfesti og 2.4b fixar með train_ext merge.

---

## 2026-04-18 (Áfangi 2.1) — Required fields filter added

**Hvað**: Training data build dropar records þar sem KAUPVERD, FASTEIGNAMAT, BYGGAR, EINFLM, FASTNUM, THINGLYSTDAGS eru null. Þetta dropar 11.467 records (step 2 í cascade: 226.481 → 215.014).

**Af hverju**: LightGBM handle-ar NaN fyrir flesta features, en target (KAUPVERD) má ekki vera NaN, og FASTEIGNAMAT er required fyrir outlier rule. Drop-ing fyrir cascade simplifies downstream.

**Impact á nýbyggingahlutfall**: Baseline training set hefur is_new_build = 13,8% vs audit 1.2 tala 15,2%. Difference er vegna required-fields filter sem dropar nýbyggingar með vantandi historical FASTEIGNAMAT (fyrir-completion transactions hafa oft NaN FASTEIGNAMAT).

---

## 2026-04-18 (Áfangi 2.1) — building_max_floor reiknað á fullum properties_v2

**Hvað**: `building_max_floor` er reiknað á fullum properties_v2 (124.835 records), ekki bara training subset. Grouping á landnum, max af merking_floor.

**Af hverju**: Þegar við ákveðum hvort íbúð er top-floor viljum við að byggingin sé fullgreind af öllum einingum sínum, ekki bara þeim sem voru seldar í arm's-length context. Íbúð á 3. hæð í 5-hæða byggingu er ekki top floor, en ef við reiknum bara á training data kannski sjáum við bara íbúðir á 1. og 3. hæð í þeirri byggingu, og miss-flaggum 3. sem top.

---

## 2026-04-18 (Áfangi 2.0 audit) — FEPILOG AA=02 hypothesis rejected

**Hvað**: Upphafleg lýsing FEPILOG AA-flokka frá Áfanga 1.8 (2026-04-18 lokakvöld) var röng. AA=02 er **ekki** bílskúrar/geymslur — það er mixed-purpose flokkur þar sem dominantly residential-main records eru innanborðs, blandaðar við commercial og garages. Sama gildir um AA=03+: allir AA-kóðar innihalda blöndu af property types.

Audit 2.0 staðfesti með cross-tab á unit_category (AA+BB) × canonical_code innan in-model set (148.608 records): unit_category 0201 telur 5.988 arm's-length residential sölur — APT_STANDARD (2.826), APT_FLOOR (1.987), ROW_HOUSE (522), SEMI_DETACHED (466), SFH_DETACHED (110), SUMMERHOUSE (61). Median pr-m² = 588 k/m² (clean residential range, ekki garage sem væri 100–250 k/m²).

**Af hverju það skiptir máli**: AA er ekki usable sem residential/non-residential classifier. Canonical exclusion í módeli stýrist af `classify_property()` úr HMS `tegund`, ekki af FEPILOG. AA má ekki notast sem second-pass filter "bara til öryggis".

**Feature design óbreytt**: `unit_category = AA + BB` sem categorical feature og `is_main_unit = (CC == "01")` sem binary. LightGBM lærir rétt price-differential á unit_category nánast frítt vegna þess að mikill meirihluti records clusterar í fáum kóðum (top-5 eru 67% af data).

**Engin breyting á 2.1 build scope**. Skráð hér svo framtíðar-Claude (eða ég sjálfur) villist ekki á fyrri lýsingu.

---

## 2026-04-18 (Áfangi 2.0 audit) — is_top_floor og floor_fraction gated á building_max_floor≥2

**Hvað**: Í audit 2.0 sýndi top-floor rate ungated að 44,4% af íbúðum væru "top floor" — inflated af single-floor buildings þar sem merking_floor = building_max_floor = 1 gefur trivially True. Þessi signal er meaningless fyrir einbýli, raðhús, og other single-floor structures.

**Ákvörðun**:
- `is_top_floor = NaN` þegar `building_max_floor < 2`, annars boolean
- `floor_fraction = NaN` þegar `building_max_floor < 2`, annars `merking_floor / building_max_floor`

NaN er preferred over False því LightGBM handle-ar NaN native og lærir "missing as information" en not-applicable-as-False myndi gefa módelinu villandi signal að einbýli séu "ekki top floor".

**Af hverju**: Audit 2.0 sýndi 85.351 apt units (APT_STANDARD/APT_FLOOR/APT_ATTIC) með bæði merking_floor og building_max_floor. Af þeim eru multi-floor buildings bara ein subset. Gating tryggir að feature-inn er meaningful í records þar sem hann er relevant.

---

## 2026-04-18 (lokakvöld) — FEPILOG decoding hierarchy (Áfangi 1.8)

**Hvað**: FEPILOG er 6-stafa kóði AABBCC:
- **AA** = aðal-flokkur. AA=01 er 74% af sölum og dominantly residential-main. AA=02 (11%) og AA=03+ eru mixed (uppfært 2026-04-18, sjá ákvörðun efst).
- **BB** = undir-flokkur.
- **CC** = raðnúmer. CC=01 (aðal-eining) = 58,1% af öllum sölum.

Features fyrir Áfanga 2:
- `unit_category = AA + BB` sem categorical (t.d. "0101", "0102", "0201")
- `is_main_unit = (CC == "01")` sem binary

**Af hverju**: 1.551 distinct FEPILOG codes eru óhöndluð í raw form. Hierarkíuna er skýr og LightGBM lærir hvaða AA_BB kombinations haga sér sérstaklega án þess að þurfa explicit rule-set.

**Alternative**: Flat categorical (1.551 levels) — hafnað, of sparse. Full AABBCC hierarchy með 3 features — yfirkill fyrir CC sem er mostly bara "main vs secondary" signal.

---

## 2026-04-18 (lokakvöld) — Multi-unit policy: single-FASTNUM only í baseline training

**Hvað**: 8,3% af arm's-length records (14.562 af 174.526) eru í multi-unit SKJALANUMER (2-4 FASTNUM undir sama samningi). **Policy fyrir Áfanga 2**: keep eingöngu single-FASTNUM SKJALANUMER í baseline training set (95,8% af samningum).

**Lykil-uppgötvun sem gerir þetta safe**: HMS hefur þegar pro-rata skipt KAUPVERD milli FASTNUM rows í multi-unit samningum. 998 af 1000 sample two-FASTNUM samningum hafa **mismunandi** KAUPVERD á rows. Þannig að summum við KAUPVERD per SKJALANUMER myndi ekki double-count-a.

Samt: multi-unit sölur eru ekki representative single-property arm's-length trades (oft eignasafn-sölur eða íbúð+atvinnuhúsnæði transactions). Filtering þær út gefur hreinna training signal. Geta verið endurskoðaðar í síðari áfanga ef þörf krefst.

**Af hverju**: Audit 1.8 section B staðfesti bæði scale (8,3% — nógu mikið til að skipta máli) og verð-skipting (clean pro-rata — ekkert re-engineering þarf). Einfaldasta legitimate solution er filter.

**Validated í audit 2.0**: Price-per-m² (2020+, residential) er kerfisbundið lower á multi-unit samningum: Einbýli 0,91×, Fjölbýli 0,89×, Sérbýli 0,99× relative to single. Multi-unit drop fjarlægir bundled-pricing dynamics sem módelið á ekki að læra.

**Alternative**:
- Aggregate KAUPVERD per SKJALANUMER og treat sem einn sale — hafnað, blandar saman eignir með mismunandi characteristics
- Keep alla records með flag — hafnað, noisy training signal í módeli sem targets single-property verð
- Drop entire multi-unit samninga — valið. Keep only single-FASTNUM (95,8%).

---

## 2026-04-18 (lokakvöld) — Landnum-based alt-pairing deferred (Áfangi 1.8b)

**Hvað**: Danni's pre-fastnum hypothesis (listings undir landnum áður en endanlegt FASTNUM er úthlutað) er **ekki testable** með núverandi listings_v2 — field-ið er ekki í parsed output. Skráð sem Áfanga 1.8b backlog.

Næsta skref þegar tekið upp aftur: re-parse fyrstu pre-merge DB til að sjá hvort landnum er í raw augl_json en bara droppað í parse_all_dbs.py. Ef já, endurgera listings_v2 með landnum field og keyra landnum-based alt pairing. Ef nei, verður að bíða eftir nýjum scraper (Áfangi 0) sem captures landnum.

**Af hverju defer**: Ekki blocker fyrir Áfanga 2 (hedonic baseline notar ekki pairing input). Áfangi 7 ask-to-sale módel getur notað núverandi 55.538 paired_fresh án landnum alt pairing. Upgrade-ar coverage í Fjölbýli frá 44% upp í kannski 60-70% ef tilgáta er correct, en sá ávinningur kemur að góðu seinna.

---

## 2026-04-18 (kvöld) — Geography feature architecture (Áfangi 1.6)

**Hvað**: Per-FASTNUM geography features í `D:\geography_features.pkl`:
- `matsvaediNUMER` og `matsvaediNAFN` — HMS verðmatssvæði, 100% coverage
- `matsvaedi_bucket` — rare-merged: M<numer> fyrir ≥50 sölur 2015+ (160 distinct), P<postnr>_other fyrir rare (53 distinct). 213 distinct values alls
- `matsvaedi_sales_2015` — sales count reference (weighting proxy)
- `postnr`, `postheiti` — backup categorical
- `region_tier` — RVK_core (101-116) / Capital_sub (170-276) / Country (33/36/31% split)
- `lat`, `lon` — bare numeric, LightGBM lærir spatial patterns

**Af hverju rare-merge við 50 sölur**: Audit 1.6 sýndi 160 af 191 matsvæða (84%) hafa ≥50 sölur 2015+, summerast í 99,4% af sölum. Rare matsvæðin (15%) summerast í 0,6% af markaðnum — það er bara strjálbýl svæði (Flatey á Breiðafirði, Hornstrandir). Merge í postnr_other preserves info án að búa til super-sparse categories.

**Af hverju bare lat/lon í stað spatial grid**: LightGBM lærir nonlinear spatial patterns án pre-processing. Einfaldara coupling. Spatial smoothing (t.d. KNN-residuals) bætist á í Áfanga 2b **aðeins ef** residual audit sýnir clear clustered residual sem módel nær ekki úr matsvæði + lat/lon.

**Alternative**:
- matsvæði eingöngu án postnr backup — hafnað, taparekstur í rare-merged eignum
- Pre-computed spatial grid (100m×100m cells) — hafnað, óþarfa complexity pre-baseline
- KNN-smoothed residual feature núna — hafnað, gera residual audit fyrst

---

## 2026-04-18 (kvöld) — Pairing logic og pair_status taxonomy (Áfangi 1.5)

**Hvað**: `pairing.py` implementar `pair_listings_to_sales()` sem skilar `pairs_v1.pkl` með 7-flokka pair_status taxonomy. Defaults: X=90d session boundary, Y_fresh=180d, Y_valid=365d.

pair_status gildi:
- `paired_fresh` — gap ≤ Y_fresh (clean ask-to-sale signal)
- `paired_recent` — Y_fresh < gap ≤ Y_valid (valid en eldri listing)
- `paired_stale` — gap > Y_valid (don't trust)
- `paired_no_price` — paired en list_price_final ógilt
- `post_sale_only` — listings eftir söluna eingöngu
- `off_market_newbuild` — engin listings, nýbygging
- `off_market_used` — engin listings, notaður markaður

**Key bug fixed late 2026-04-18**: Upphafleg merge_asof var á session_end, sem missed af cases þar sem session spannar söluna (pre-sale listing + post-sale listing innan 90d). Fixed til að match-a á listings beint og skila session metadata via session_id join. Paired_fresh count hækkaði úr 54.054 → 55.538 (matches audit 1.5b).

**Af hverju X=90, Y_fresh=180, Y_valid=365**: Audit 1.5b core diagnostic (ask-to-sale median per gap bucket):
| Bucket | Median |
|---|---|
| 0-180d | 0.970-0.987 |
| 180-365d | 0.969 |
| 1-2y | 1.001 (inflation crossover) |
| 2-5y | 1.249 |
| 5y+ | 1.643 |

180d er conservative cutoff fyrir training data. 365d er permissive cutoff fyrir valid pair flag.

---

## 2026-04-18 (kvöld) — Scrape gap frá 2025-07-01 accepted

**Hvað**: Listings volume hrundi úr ~9.000/mán (2024) niður í ~600/mán (2025-H2). Partial recovery til ~1.800/mán í 2026-03/04. Annualized rate vs 2024 = 0.10x. Danni erfði gamla scraperinn og hefur ekki kontrol. Leyst með nýjum scraper í Áfanga 0.

`in_scrape_gap=True` flag á sölur ≥ 2025-07-01 í pairs_v1 sem **metadata flag, ekki sía**. Paired records í gap-tímabili eru nothæf per-pair (real listing + real sale); einungis denominator-dependent metrics (coverage rate, off_market %) eru unreliable.

---

## 2026-04-18 (kvöld) — Nýbyggingar-tilgáta um off_market Fjölbýli rejected

**Hvað**: Tilgáta um að off_market Fjölbýli væru yfirgnæfandi nýbyggingar (70-90%) falsified í audit 1.5b. Nýbyggingar eru 18,5% af off_market Fjölbýli vs 15,3% markaðurinn í heild — engin over-representation.

Danni's pre-fastnum hypothesis (1.8b backlog) er núverandi leading explanation fyrir 32K off_market Fjölbýli sölur.

---

## 2026-04-18 (síðar) — thinglystdags parsing með format='ISO8601'

**Hvað**: `pd.to_datetime(..., format='ISO8601')` í stað inference fyrir raw `thinglystdags` strings með variable fractional precision (1-6+ digits). Plus year-range filter til að fanga sentinel dates ('0001-...').

**Impact**: date_valid stökk úr 84,77% í 98,57% í listings_v2.

---

## 2026-04-18 — Canonical data layer switched to v2 pickles (Áfangi 1.4.3)

**Hvað**: Downstream vinna les úr v2 pickles framleiddum af `parse_all_dbs.py` úr 5 pre-merge scraper DBum í `D:\Gagnapakkar\`. `fasteignir_merged.db` er deprecated (82% NaT á thinglystdags).

Per-DB FASTNUM partitions near-disjoint; overlap 378+380 í boundaries. Dedupe heldur latest scrape.

---

## 2026-04-18 — Dedupe strategy fyrir v2 pickles

**Hvað**:
- Listings: sort á `(augl_id, date_valid, scraped_at)` priorities `[True, False, False]`, drop_duplicates keep='first'
- Sales: sort á `(faerslunumer, scraped_at)`, latest wins
- Properties: sort á `(fastnum, scraped_at)`, latest wins
- Texts: same as listings

---

## 2026-04-18 — Invalid dates retained með date_valid flag

**Hvað**: Listings með sentinel eða unparseable dates halda `effective_date=NaT` með `date_valid=False`. ~5% af listings. Downstream filtrar á `date_valid=True` explicitly.

---

## 2026-04-18 — Lysing stored separately

**Hvað**: Listing descriptions (~2-5KB each) í aðskildri pickle (`listings_text_v2.pkl`, ~1,5 GB). Main listings_v2 lite fyrir fast loading.

---

## 2026-04-18 — Outlier filter (Áfangi 1.4.2)

**Hvað**: Tvær reglur:

**`is_price_outlier`** — combined signal, flaggar ef nokkur:
1. `fm_ratio < 0,10`
2. `fm_ratio < 0,30` AND `robust_z < −3`
3. `robust_z < −5` AND `fm_ratio < 0,50`
4. `robust_z > +10` AND `fm_ratio > +20`

Þar sem `robust_z = (log10(pr-m²) − seg_median) / (seg_iqr/1,349)`, segment = (TEGUND × region × 3-ára bucket).

**`is_size_outlier`**: `EINFLM < 20` eða `> 1000`.

Impact á residential (N=162.692): 324 flaggaðar (0,20%).

**MIKILVÆGT**: `is_price_outlier` tekur historical `FASTEIGNAMAT`, aldrei `FASTEIGNAMAT_GILDANDI`.

---

## 2026-04-18 — Frozen-snapshot dálkar staðfestir (Áfangi 1.4.1)

**Hvað**: Fjórir dálkar í kaupskrá CSV eru frozen HMS-snapshots:
- `FASTEIGNAMAT_GILDANDI` → nota `FASTEIGNAMAT`
- `FYRIRHUGAD_FASTEIGNAMAT` → nota `FASTEIGNAMAT`
- `BRUNABOTAMAT_GILDANDI` → engin historical í CSV
- `FJHERB` → sækja úr augl_json í listings_v2

Historical dálkar: KAUPVERD (99,40%), FASTEIGNAMAT (98,65%), EINFLM (6,77%), FULLBUID (4,60%), LOD_FLM (4,31%).

---

## 2026-04-18 — Eignabreytingarregla (Áfangi 1.3)

**Hvað**: Repeat-sale par útilokað ef (a) FULLBUID 1→0 transition, eða (b) `|EINFLM pct_change| > 5%`. Impact á 68.696 consecutive pör: 2.133 droppuð (3,1%).

---

## 2026-04-18 — Floor-level features í baseline

**Hvað**: `merking_floor`, `building_max_floor`, `is_top_floor`, `floor_fraction`. Top-floor premium +2-5% consistently.

---

## 2026-04-18 — Nýbyggingarregla empíríkt staðfest

**Hvað**: `FULLBUID=0 OR BYGGAR innan 2 ára af THINGLYSTDAGS`. Fangar 26.602 sölur (15,2%). Pre-completion discount: Fjölbýli 12%, Einbýli 23%.

---

## 2026-04-18 — Verðbólguleiðrétting CPI á þjálfunarsafn

**Hvað**: Allar verð-observations CPI-deflated til rolling latest month. `real_price = nominal × (CPI_ref / CPI_at_sale)`. Target = `real_kaupverd`.

Heimild: Hagstofan VIS01004, `cpi_verdtrygging.csv`, `cpi.py` helper.

---

## 2026-04-18 — Taxonomy finalization (514 HMS tegundir)

**Hvað**: Fjórir viðbótar secondary residential flokkar: `APT_ROOM`, `APT_HOTEL`, `APT_MIXED`, `APT_UNAPPROVED`. Saman við `APT_SENIOR`. Gestahús útilokað.

Coverage: 88,4% í módeli, 11,6% EXCLUDE.

---

## 2026-04-17 — Skjalastrúktúr fyrir project continuity

**Hvað**: Sex-skjala strúktúr: PROJECT_INSTRUCTIONS.md, STATE.md, DATA_SCHEMA.md, DECISIONS.md, TAXONOMY.md, GLOSSARY.md. Bætt við DATA_AUDIT_REPORT.md í Áfanga 1.7.

---

## 2026-04-17 — Property type taxonomy drög

**Hvað**: 8 canonical residential flokkar + SUMMERHOUSE. **Superseded**: 2026-04-18 með 5 sekúnder-flokkum (APT_ROOM, APT_HOTEL, APT_MIXED, APT_UNAPPROVED, APT_SENIOR).

---

## 2026-04-17 — Arm's-length filter

**Hvað**: Útiloka `ONOTHAEFUR_SAMNINGUR=1` (23%, 51.767 færslur).

**Af hverju**: Non-arm's-length sölur (fjölskyldu-transferrs, nauðungarsölur, gjafir) endurspegla ekki markaðsverð. Útiloka úr módeli, halda í sögulegri töflu fyrir reference.

---

## 2026-04-17 — Nýbyggingarregla (initial)

**Hvað**: `FULLBUID=0 OR (BYGGAR innan 2 ára af THINGLYSTDAGS)`. Staðfest empirically 2026-04-18.

**Af hverju**: Nýbyggingar hafa sinn eigin price dynamic (pre-completion discount, builder incentives). Þarf sérflögg svo hedonic módel geti lært þessa dynamík aðskilið frá notaðum markaði.

---

## 2026-04-17 — Eignabreytingar milli sala

**Hvað**: Fjarlægja repeat-sale pör þar sem EINFLM hefur breyst meira en 5%. Eitthvað var renovated/added/split — sala #2 er ekki á sömu eign.

**Af hverju**: Repeat-sale index byggir á að pöruð sala sé á sömu eign. Extension, division í fleiri íbúðir, o.s.frv. gera comparison röng.

---

## 2026-04-17 — Listing-to-sale pairing logic (initial plan)

**Hvað**: Para saman auglýsingar og kaupskrárfærslur ef samfellt á markaði. Gap > X daga → aðskilið söluferli. **Implementerað og finalized** 2026-04-18 kvöld með X=90, Y_fresh=180, Y_valid=365.

**Af hverju**: Framenginn ask-to-sale gap módel (Áfangi 7) þarf clean pairs milli listings og sala. Session-boundary handlar "paused re-listings" vs "new attempts".

---

## 2026-04-17 — Listing withdrawals fara í markaðsyfirlit

**Hvað**: Listings sem enda án sölu → flagged sem "withdrawn". Útilokaðar úr módeli, notaðar sem leading indicator (withdrawal rate er key market-temperature signal).

**Af hverju**: Útilokun úr þjálfunarsafni forðast bias (withdrawn eru ekki representative af completed sales). Haldið í markaðsyfirlit því rate þeirra er sterk indicator á markaðsástandi.

---

## 2026-04-17 — Geography: tvö lög

**Hvað**: (1) `matsvaediNUMER` sem categorical feature, (2) spatial smoothing með KNN á götureits-level (deferred til Áfanga 2b).

**Af hverju**: Matsvæði fangar hverfa-level price effects. KNN-smoothing fangar smaller-grain patterns (sjávarsýn, nálægð við park). Tvö lög saman gefa bæði discrete og continuous signal.

**Alternative íhugað**:
- Postnúmer eingöngu — hafnað, of coarse (postnr 105 spannar sem dæmi 8 matsvæði)
- Spatial grid eingöngu — hafnað, missir semantic matsvæðis-info

---

## 2026-04-17 — Target variable

**Hvað**: Aðalspá = þinglýst kaupverð (raunvirði). Ask-to-sale gap módel separat (Áfangi 7).

**Af hverju**: Kaupverð er authoritative (þinglýst). Listings er self-reported og óáreiðanlegt sem target. Gap-módel lærir discrepancy aðskilið svo við getum spáð bæði ásett verð OG sölvirði.

---

## 2026-04-17 — Uncertainty quantification

**Hvað**: LightGBM quantile regression, 5 quantiles (P2.5/P10/P50/P90/P97.5) + mean.

**Af hverju**: Bankar og opinberir aðilar krefjast uncertainty intervals, ekki bara point estimates. Quantile regression captures tail behavior betur en normal Gaussian. 5 quantiles gefa 80% og 95% intervals beint.

**Alternative íhugað**:
- Bootstrap ensembling — hafnað, compute-expensive, síður principled
- Conformal prediction — lagt í backlog fyrir Áfanga 2b ef calibration er léleg
- Bayesian regression — hafnað, scale-vandi á 170K sölum

---

## 2026-04-17 — Infrastructure stack

**Hvað**: Hetzner + PostgreSQL 16 + PostGIS + R2 + Docker Compose + Dagster + MLflow + Grafana/Prometheus/Sentry + FastAPI.

**Af hverju**:
- Hetzner: Evrópu-hosted (GDPR), cheap dedicated hardware
- Postgres+PostGIS: well-proven fyrir geo-data, SQL is universal
- Cloudflare R2: S3-compatible, zero egress cost
- Dagster: bestu data-pipeline tool fyrir scheduled scrapes og retraining
- MLflow: model versioning + reproducibility

---

## 2026-04-17 — ML framework

**Hvað**: LightGBM fyrir verðmat. Claude API fyrir LLM-extraction úr lýsingum.

**Af hverju**:
- LightGBM: proven fyrir tabular real-estate, handles categoricals native, fast training
- Claude: best-in-class fyrir íslenska texta extraction (Áfangi 4-5)

**Alternative íhugað**:
- XGBoost — svipað performance, LightGBM er hraðari á íslenskum scale
- Neural net (TabNet, FT-Transformer) — hafnað, marginal gains vs complexity overhead
- GPT-4 / Gemini — keppinautur, Claude hefur best íslenskuna í testing

---

## 2026-04-17 — Repeat-sale calibration samhliða extraction

**Hvað**: Repeat-sale pair analysis með CPI + markaðsvísitölu deflation samhliða pilot/full extraction (Áfangar 5-6).

**Af hverju**: Repeat-sale gefur ábyggilegt market-trend signal sem hedonic getur vottað sig gegn. Parallelization sparar tíma — bæði vinna á sama data layer.

---

## 2026-04-17 — Versioning og reproducibility

**Hvað**: Hvert verðmat fær version stamp (model_version + feature_version + data_snapshot_date). `predictions` tafla í Postgres geymir öll spá með feature values á spá-tíma.

**Af hverju**: Bankar þurfa að geta endurgert spá á hvaða tíma sem er (audit trails). Feature drift monitoring krefst historical feature values.

---

## 2026-04-17 — Three deployment channels, one data layer

**Hvað**: Einn canonical Postgres + API. Public/subscription/internal lesa af sama gagnalagi með mismunandi permission scopes.

**Af hverju**: Avoid data duplication. Ein truth-source. Breytingar í module propagate í alla kanala.

---

## 2026-04-17 — v1 markaðsyfirlits-indicators

**Hvað**: Átta indicators: repeat-sale index, list-to-sale ratio, months of supply, withdrawal rate, time-on-market distribution, orðatíðnigreining, model-tracking (spá vs söluverð), affordability index (verð / meðalárslaun).

**Af hverju**: Standard real-estate indicators + nokkur sérstök (orðatíðni úr lýsingum, model-tracking sem sjálfstætt gæða-monitor). v1 er data-driven sýnisafn; v2 getur bætt við byggt á feedback.

---

*Ný ákvörðun? Bættu við efst með dagsetningu + rökstuðningi.*
