# TEXTAÞEKJA `last_listing_text` — R3-SÍUFIXIÐ LENT, R1-B LIFANDI BLÖNDUN ÞURRKEYRÐ (cc180)

**Dags.:** 2026-09-02 (00:05–00:20 UTC) · **Lota:** cc180 · **Eðli:** SKRIFALOTA — ein tafla snert (`public.last_listing_text`), ekkert annað · **Engin LLM-köll** · **Staða: HALT A** (R3 flippað og mælt; R1-b þurrkeyrð, EKKI flippuð).
**Grunnur:** `GAGNAVIDGERD_CC178.md` §1.5–1.6 + §4 (R1, R3) · `VERDMETA_SJALFUR_CC177.md` §1.6 (þekjuhrunið) · fordæmi flipps `verdmat-ai/supabase/migrations/20260715_llt_augl_dagur.sql`.
**Úttekt:** `D:\_audit\cc180_textathekja\` (q00–q04, r3_*.log, r1b_build_dryrun.log, rollback-SQL, afrit júlí-árgangs).

---

## 0. NIÐURSTAÐA Í EINNI TÖFLU

| # | Liður | Staða | Tala |
|---|---|---|---|
| 1 | Formæling (fyrir) | ✔ mæld | 18-mán sölugluggi **39,38 %** m/texta (6.404/16.264); 0,0 % frá 2026-05 |
| 2 | **R3-síufixið** | ✔ **FLIPPAÐ 00:15 UTC** | 60.807 → **66.060 raðir** (+5.253, +8,64 %), 44.418 → **47.721 eignir**; parity 6/6; rollback á diski |
| 2a | Fable-comp-þekja eftir R3 | ✔ mæld | **47,11 → 52,51 %** (+5,40 pp) — **nákvæmlega cc178-spáin**; eignir m/ ≥3 textaða compa 66,41 → **74,57 %** |
| 2b | Leikhæfni Verðmeta-sjálfs eftir R3 | ✔ mæld | ≥4: **15,20 → 20,07 %** (23.654 → 31.230); ≥3: 33,58 → 40,59 % |
| 3 | **R1-b lifandi blöndun** | ⏸ **ÞURRKEYRÐ, bíður HALT A** | **+1.350 lifandi raðir** → 67.379 raðir / 48.695 eignir; 2026-07 = 69,2 %, 2026-08 = 77,9 % sölna fá texta |
| 4 | Afleiðingamæling R1-b | ⏸ eftir flipp | — |
| 5 | Skil + commit | ✔ þetta skjal + DECISIONS + commit (ekkert push) | — |

**Frávik frá verkbeiðni, bókuð:** (a) hvítlistinn er á **línu 60**, ekki 59 (lína 59 er athugasemdin); (b) verkbeiðnin nefnir „+9,4 pp" — sú tala finnst hvorki í cc178 né í mælingunum hér; mældu tölurnar eru +8,64 % raðir, +5,40 pp Fable-comp-þekja, +5,60 pp sölugluggi 18 mán, +4,87 pp leikhæfni ≥4; (c) skráin `build_last_listing_text.py` býr á `D:\` (utan repo), ekki í `app/precompute` — patchið er þar, afrit `D:\build_last_listing_text.py.pre_cc180_20260902`.

---

## 1. FORMÆLING — ÞEKJAN Í DAG (q01 `fyrir`, 00:05 UTC, READ-ONLY)

Nefnari = nothæfar sölur (`sales_history.onothaefur = 0`) eftir mánuði þinglýsingar. Teljari = til er röð í `last_listing_text` á `(fastnum, thinglyst_dagur)` með `lysing_plain ≥ 200` stafir (C-skilyrði cc177). Taflan bar 60.807 raðir, 44.418 eignir, `max(scraped_at)` 2026-04-16 13:13:03.

| mán. | sölur | m/texta | % fyrir | % eftir R3 | Δ pp |
|---|---:|---:|---:|---:|---:|
| 2025-06 | 982 | 701 | 71,4 | 75,7 | +4,3 |
| 2025-07 | 1.244 | 837 | 67,3 | 71,5 | +4,2 |
| 2025-08 | 838 | 515 | 61,5 | 66,6 | +5,1 |
| 2025-09 | 1.010 | 513 | 50,8 | 55,7 | +4,9 |
| 2025-10 | 1.036 | 464 | 44,8 | 51,3 | +6,5 |
| 2025-11 | 870 | 357 | 41,0 | 47,4 | +6,4 |
| 2025-12 | 819 | 277 | 33,8 | **46,5** | **+12,7** |
| 2026-01 | 810 | 246 | 30,4 | **44,7** | **+14,3** |
| 2026-02 | 745 | 220 | 29,5 | **42,6** | **+13,1** |
| 2026-03 | 1.086 | 354 | 32,6 | **43,2** | **+10,6** |
| 2026-04 | 730 | 130 | 17,8 | 21,6 | +3,8 |
| 2026-05 | 771 | 0 | 0,0 | 0,0 | 0 |
| 2026-06 | 838 | 0 | 0,0 | 0,0 | 0 |
| 2026-07 | 894 | 0 | 0,0 | 0,0 | 0 |
| 2026-08 | 589 | 0 | 0,0 | 0,0 | 0 |

(2024-06 → 2025-05 í `q01_fyrir_out.txt` / `q01_eftir_r3_out.txt`: 46,9–62,0 % fyrir, +4–6 pp eftir.)

**Gluggar:**

| gluggi | sölur | fyrir | eftir R3 | Δ |
|---|---:|---:|---:|---:|
| 18 mán til dagsins (leikhæfnisglugginn) | 16.264 | 39,38 % | **44,98 %** | +5,60 pp |
| 2025-07-01 → 2026-04-16 (evalue lifandi) | 8.822 | 44,23 % | 52,45 % | +8,22 pp |
| 2025-07-01 → dagsins (hrunkúrfan) | 12.280 | 31,86 % | 37,79 % | +5,93 pp |
| 2026-04-17 → dagsins (eftir frystingu) | 3.458 | 0,32 % | 0,38 % | +0,06 pp |
| 2026-06-01 → dagsins (R1-b-sviðið) | 2.321 | 0,00 % | 0,00 % | 0 |

Hrunkúrfan 2025-06 → 2026-03 réttist um 10–14 pp á 2025-12 → 2026-03 (þar sem `paired_recent` var þéttast), en **frystingin frá 2026-05 er alger og R3 snertir hana ekki** — það er R1-b.

**Beislisstaðfesting:** „fyrir"-dálkurinn endurgerir cc178 q20 lið fyrir lið (Fable 47,11 %; 2025-06 = 79,0 % á 45.148 comp-röðum; 2026-05 → 08 = 0,0 %) og cc177 §1.6 (≥3 leikhæfir 33,58 % í dag vs 33,71 % 31.08 — munurinn er 18-mán glugginn sem færðist um tvo daga).

---

## 2. R3 — SÍUFIXIÐ (FLIPPAÐ)

### 2.1 Sannreynt gegn lifandi skrá (q02, verbatim-lestur)

`D:\build_last_listing_text.py` (mtime 2026-07-15 17:55, sha256 `7d39f16eae482a2a`), línur 59–62 fyrir patch:

```
59:     # Use rows where we have any augl_id associated
60:     pairs = pairs[pairs["pair_status"].isin(["paired_fresh", "paired_stale", "off_market_used"])].copy()
61:     pairs["augl_id"] = pairs["augl_id_final"].fillna(pairs["augl_id_initial"])
62:     pairs = pairs.dropna(subset=["fastnum", "sale_date", "augl_id"]).copy()
```

Krosstafla `pairs_v1.pkl` (174.526 raðir) — `pair_status` × ber `augl_id`: `paired_fresh` 55.544/55.544, `paired_stale` 6.366/6.366, `paired_recent` 3.385/3.385, `paired_no_price` 2.112/2.112, **`off_market_used` 0/62.837**, `off_market_newbuild` 0/12.985, `post_sale_only` 0/31.297. Rótgreining cc178 §1.5 stendur óbreytt.

### 2.2 Spáin endurmæld á dagsins gögnum (q02) — FYRIR nokkur skrif

| | raðir | eignir |
|---|---:|---:|
| Núverandi hvítlisti | 60.807 | 44.418 |
| Tillaga `[paired_fresh, paired_stale, paired_recent, paired_no_price]` | **66.060** | **47.721** |
| Δ | **+5.253 (+8,64 %)** | **+3.303** |

Vænt dreifing: `paired_fresh` 54.426 · `paired_stale` 6.304 · `paired_recent` 3.278 · `paired_no_price` 2.052. (74 `paired_fresh` + 3 `paired_stale` raðir í júlí-árgangi ýtast út af top-3 þakinu af nýrri `paired_recent`/`no_price`-sölum — **77 raðir**, mælt á pkl-um fyrir staging.)

### 2.3 Framkvæmd

1. **Afrit:** `D:\build_last_listing_text.py.pre_cc180_20260902`, `D:\_audit\cc180_textathekja\last_listing_text_pre_cc180_60807.{csv,pkl}` (júlí-árgangurinn, 153 MB).
2. **Patch:** ein lína (60) + athugasemd. Bygging keyrð (`r3_build.log`): `pairs w/ augl_id 67.407 → after join 66.747 → after cap 66.060`, 47.721 eignir, CSV 158,7 MB.
3. **Staging + parity** (`app/scripts/cc180_llt_flip.py --stage`, `r3_stage.log`): `public.last_listing_text_new` stofnuð með PK `(fastnum, sale_rank)` + fastnum-vísi + **RLS + `public_read` + grants Í SÖMU txn** og COPY (6,0 s). Parity, allt read-only eftir commit:

| hlið | mæling | spá | |
|---|---|---|---|
| [1] rowcount | 66.060 | 66.060 | OK |
| [2] `pair_status`-dreifing | 54.426 / 6.304 / 3.278 / 2.052 | sama | OK |
| [3] `sale_rank` 1..3, ≤3 per fastnum, samfelld | 0 / 0 / 0 frávik | 0 | OK |
| [4] NULL-lyklar (`thinglyst_dagur`, `augl_id`, `augl_dagur`, `scraped_at`) | 0 / 0 / 0 / 0 | 0 | OK |
| [4b] arfur byggingar: `lysing_plain` NULL / <200 / HTML-leifar | 8 / 23 / 6 | lifandi 4 / 12 / **6** | OK (ekki verra en lifandi á HTML; NULL/<200 eru `paired_no_price`/`recent`-raðir án texta — sama hegðun og fyrir) |
| [5] sameiginlegar `(fastnum, thinglyst_dagur, augl_id)` við lifandi: texti (md5), `scraped_at`, `augl_dagur`, `pair_status` | 60.744 raðir, **0 misræmi á öllum fjórum** | 0 | OK |
| [6] lifandi raðir ekki í `_new` (ýtt út af þaki) | **77** | 77 | OK |

   Fyrsta keyrsla hliðs [4] **felldi** staging á HTML-leifum = 6. Mælt gegn lifandi: **sömu 6 raðir** (`<br>`-entity-leifar úr `html.unescape` eftir tag-strip, `i_lifandi = true` á öllum) + ein bókstafleg `<hægt að setja eyju þar á milli>`. Hliðið var endurskilgreint sem „ekki verra en lifandi", ekki slakað á lyklunum. Sbr. `feedback_berdu_vid_afleidslukjarnann_ekki_vid_csv_skrana` — arfur er ekki afturför.

4. **Rollback skrifað FYRIR flipp:** `D:\_audit\cc180_textathekja\cc180_rollback_r3.sql` (rename-swap til baka + endurheimt `public_read`; varaleið `\copy` úr júlí-CSV).
5. **Flipp** (`--flip`, 00:15:23 UTC, `r3_flip.log`): EIN txn, `SET TRANSACTION READ WRITE` fyrst; `_new`-rowcount == spá; `last_listing_text → last_listing_text_old_r3` (+ vísanöfn), `_new → last_listing_text` (+ vísanöfn í upprunaleg heiti); `_old_r3` missir `public_read`-stefnuna og anon/authenticated-grants; COMMIT; `NOTIFY pgrst, 'reload schema'`. **Ekki TRUNCATE+COPY** — söluyfirlitssíðan les töfluna lifandi á prod og rename-parið læsir í millisekúndur (júlí-fordæmið).
6. **Eftir flipp:** `last_listing_text` = 66.060 raðir, `max(thinglyst_dagur)` 2026-04-17, `max(scraped_at)` 2026-04-16 13:13:03 (frystingin óbreytt, eins og vænta mátti). relacl lifandi: `anon=r, authenticated=r`; `_old_r3`: **engin** anon/authenticated-réttindi, RLS á, 0 stefnur.
7. **Lifandi flötur mældur** (anon-REST með `.env.local`-lyklinum): `GET /rest/v1/last_listing_text?pair_status=eq.paired_recent` → 206, `Content-Range 0-1/3278`; heildartalning 66.060; `last_listing_text_old_r3` → **401**. PostgREST sá skiptin strax.

### 2.4 Afleiðingar R3 (q01 `eftir_r3`, 00:16 UTC)

**Fable-comp-þekja** (sýnt mengi `comps_index_v2`, `set_role='comp'`, `rank ≤ 8`, 1.106.687 raðir):

| | fyrir | eftir R3 | Δ | cc178-spá |
|---|---:|---:|---:|---:|
| Allt | 47,11 % | **52,51 %** | +5,40 pp | +5,40 pp ✔ |
| S0 (921.941) | 45,03 | 49,95 | +4,92 | +4,92 ✔ |
| S1p (95.139) | 61,90 | 69,33 | +7,43 | +7,43 ✔ |
| S2p (17.293) | 54,79 | 62,35 | +7,56 | +7,56 ✔ |
| S3 (72.314) | 52,26 | 60,61 | +8,35 | +8,35 ✔ |
| Eignir m/ ≥3 textaða compa | 103.321 (66,41 %) | **116.018 (74,57 %)** | +12.697 | +12.697 ✔ |

**Leikhæfni Verðmeta-sjálfs** (cc177 q06-skilgreiningin, 18 mán · ekki suspect · texti ≥200 · myndir ≥5; 155.587 T1/T2-eignir):

| sía | fyrir ≥3 | eftir ≥3 | fyrir ≥4 | eftir ≥4 |
|---|---:|---:|---:|---:|
| A·B (án texta) | 83,82 % | 83,82 % | 75,85 % | 75,85 % |
| A·B·C (texti) | 39,44 % | **47,58 %** | 19,63 % | **25,57 %** |
| A·B·C·D5 (aðalskilgr.) | 33,58 % (52.253) | **40,59 % (63.157)** | 15,20 % (23.654) | **20,07 % (31.230)** |

Valda hliðið (≥4) vex um **7.576 eignir (+32,0 %)** á einni kóðalínu. Textinn er enn stærsti fellirinn (83,8 → 47,6 %).

---

## 3. R1-b — LIFANDI BLÖNDUN (ÞURRKEYRÐ, EKKI FLIPPUÐ)

### 3.1 Hönnun (bókuð hér, framkvæmd bíður HALT A)

- **Lind:** `scraper.listings` (`source='mbl'`, `tenure='sale'`, 50.166 raðir / 10.933 fastnúmer, `lysing ≥ 200` á 50.153). Nætur-skrifuð (`promote_listings_append.py`).
- **Svið:** sölur með `thinglystdags > 2026-04-16` (frostdagur evalue), `onothaefur = 0`. evalue heldur öllu eldra **og vinnur** ef sama `(fastnum, thinglyst_dagur)` á evalue-röð.
- **Pörunarregla** (cc178 q21, óbreytt): sama fastnum · `first_seen_at::date ≤ thinglystdags` · innan 365 daga á undan · nýjasta auglýsingin. **Dedup á `listing_id`:** ein auglýsing → ein sala (sú fyrsta eftir auglýsingu).
- **Uppruni á hverri röð:** `augl_id = 'mbl:<source_listing_id>'` (rekst aldrei á evalue-tölur), `pair_status = 'live_listings'`, `scraped_at = last_seen_at` (sótt dags), `augl_dagur = least(listed_at, first_seen_at)::date` (sami reitur og virka-auglýsingar-leiðin í `eigindi-extraction.js` notar, svo lindirnar dagsetji eins; mbl endur-dagsetur `listed_at` við endurbirtingu — `least` ver gegn því).
- **Texti:** `strip_html` úr `build_last_listing_text.py` — **allar 1.350 lifandi raðir bera HTML-merki í `lysing`** (q03 D), eftir strip 0 leifar / 0 undir 200 stöfum.
- **Röðun:** per fastnum `thinglyst_dagur DESC`, jafntefli brotið á R3-`sale_rank` (evalue) / 0 (lifandi) → deterministic (sbr. `feedback_rodun_an_jafnteflisbrjots_er_ekki_fall`). Þak 3 óbreytt.
- **Hleðsla:** sama `cc180_llt_flip.py --stage/--flip --tag r1b` → `last_listing_text_old_r1b` = R3-árgangurinn sem rollback.

### 3.2 Falspróf pörunarreglunnar (q03 E)

Á glugganum þar sem evalue var lifandi (2025-07-01 → 2026-04-16) para BÁÐAR lindir 49 sölur. Miðgildi dagamunar á `augl_dagur` (evalue) og `least(listed_at, first_seen_at)` (mbl): **0 dagar**; 36/49 innan 45 daga; 6/49 yfir 180 daga (þ.a. 3 evalue-`paired_stale`). Reglan velur sömu auglýsingu í meginþorra tilvika þar sem báðar sjá hana.

### 3.3 Þurrkeyrsla (q03 + `cc180_build_llt_live.py`, snapshot 00:17:49 UTC)

| | |
|---|---|
| Sölur þinglýstar eftir 2026-04-16 (nothæfar) | 3.458 (þ.a. 11 með evalue-röð á 2026-04-17) |
| Paraðar við mbl-auglýsingu | 1.354 → **1.350 eftir dedup** (4 felldar), 1.350 fastnúmer, 1.350 auglýsingar |
| Bil `first_seen → þinglýsing` | p10 17 d · **p50 41 d** · p90 104 d · max 364; 37 yfir 180 d |
| Staða auglýsinga | withdrawn 1.125 · active 212 · inactive 13 |
| `listed_at > þinglýsing` (endur-dagsett) | 2 → `least()` ver |

Per mánuð þinglýsingar (nefnari = nothæfar sölur án evalue-raðar):

| mán. | sölur | fá texta | % |
|---|---:|---:|---:|
| 2026-04 (frá 17.) | 355 | 12 | 3,4 |
| 2026-05 | 771 | 52 | 6,7 |
| 2026-06 | 838 | 208 | 24,8 |
| 2026-07 | 894 | 619 | **69,2** |
| 2026-08 | 589 | 459 | **77,9** |

> Fyrirvarinn úr cc178 stendur: ágúst-nefnarinn (589) er þinglýsingar-töfður og vex. 2026-04-17 → 05-31 (1.126 sölur, 64 fá texta) er **glatað** án fersks evalue-pakka.

**Blandan (SPÁ fyrir parity-hlið `--tag r1b`):**

```
ROWCOUNT=67379  FASTNUM=48695
STATUS=live_listings=1350,paired_fresh=54398,paired_no_price=2051,paired_recent=3278,paired_stale=6302
EXPECT_DISPLACED=31    (evalue-raðir sem falla út af top-3 þaki; 0 lifandi falla út)
```

Allar 1.350 lifandi raðir lenda á `sale_rank = 1` (þær eru nýjasta salan á sínu fastnúmeri í öllum tilvikum); 522 evalue-raðir færast um eitt sæti. CSV: `D:\verdmat-is\precompute\exports\last_listing_text_blend.csv` (67.379 raðir, 163,3 MB) — **ekki hlaðin**.

### 3.4 Það sem framendinn sér (grepp, ekki breytt)

- `soluyfirlit/page.tsx:91,100` sérmeðhöndlar **aðeins** `pair_status === "paired_stale"` („gömul auglýsing"); `paired_recent`, `paired_no_price` og `live_listings` birtast sem venjuleg söluyfirlit með `augl_dagur` sem dagsetningu. `components/eign/types.ts:230` skjalfestir aðeins tvö gildi — **skjalarek, ekki kóðarek**.
- `augl_id` er notað sem lykill (`page.tsx:87`) og sem `eigindi_extraction_runs.augl_id` (`eigindi-extraction.js:563`) — strengur, `'mbl:…'` gengur. Myndir eru sóttar á `fastnum` (`property_images`), ekki `augl_id`.
- `agent-tools.js:478` telur eignir m/ `lysing_plain IS NOT NULL` — 1.350 nýjar eignir verða extraction-kandídatar (dagþak $2,00/88 hashar cc173 heldur).
- `EIGN_CACHE_TTL = 3600` → notendur sjá R3-raðirnar innan 60 mín.

---

## 4. AFLEIÐINGAMÆLING

R3: §2.4 (lokið). R1-b: keyrist með `python q01_maeling.py eftir_r1b` eftir flipp — sömu þrjár mælingar, sömu nefnarar. Vænting (mótpróf, ekki mæling): lifandi raðirnar 1.350 liggja á sölum 2026-06 → 08 sem eru **inni í 18-mán glugganum** og í comp-menginu frá `comps_index_v2`-árgangi 2026-08-12 (comp-raðir m/ söludag ≥ 2026-05: 194.899, í dag 0,0 % texti).

---

## 5. HALT A — ÁKVÖRÐUN SEM ÞARF

**R3 er lent og mælt: parity 6/6, Fable +5,40 pp á pari við spá, leikhæfni ≥4 +4,87 pp. Rollback í `cc180_rollback_r3.sql` og `last_listing_text_old_r3` (60.807).**

Fyrir R1-b þarf **GO/NO-GO** á þessum forsendum, sem allar eru mældar:

1. **Blöndun í SÖMU töflu** (cc178 spurning 3): `pair_status='live_listings'` + `augl_id='mbl:…'` + `scraped_at=last_seen_at` bókar upprunann á hverja röð; engin ný tafla, engin migration. Rollback = rename-swap í `_old_r1b`.
2. **Framendinn tekur við** án breytingar (§3.4) — en `types.ts`-athugasemdin þarf uppfærslu í annarri lotu.
3. **Endurbyggingar-áhætta:** R3-byggingin (`build_last_listing_text.py`) skrifar ENN aðeins evalue-raðir. Ef einhver keyrir `refresh_dashboard_tables_v2.py` → `load_dashboard_v1.py --tables listing` (TRUNCATE+COPY, 6 dálkar!) eftir R1-b-flipp **hverfa lifandi raðirnar og dálkarnir tveir**. Sá hleðari er þegar ósamhæfður 8-dálka töflunni (COPY með 6-dálka lista á 8-dálka CSV fellur) — hann er í reynd dauður síðan júlí. **Tillaga:** eftir GO fer `cc180_build_llt_live.py` inn sem þrep á eftir `build_last_listing_text.py` og `cc180_llt_flip.py` leysir `load_dashboard_v1.py --tables listing` af.
4. **Lifandi lindin frýs aftur** við snapshot 2026-09-02 nema blöndunin sé keyrð reglulega. Ekkert Task-Scheduler-verk er smíðað í þessari lotu (utan umfangs); hún er handkeyrsla eins og evalue-keðjan var.
5. **31 evalue-raðir** (rank 3, elstu sölur) hverfa úr top-3 á fastnúmerum sem fá lifandi röð — sama þak-regla og áður, engin gagnaeyðing (evalue-CSV/pkl standa).

**Bannið haldið:** engin LLM-köll · `predictions/comps/valuation_tiers` ósnert · `Gagnapakkar\*.db` ósnert · `git add -A` ekki notað · ekkert push.

---

## 6. SKRÁR

| Skrá | Hlutverk |
|---|---|
| `D:\build_last_listing_text.py` (+ `.pre_cc180_20260902`) | R3-patch á línu 60 (utan repo) |
| `app/scripts/cc180_llt_flip.py` | staging + 6 parity-hlið + atómískt rename-swap + rollback-SQL + `--status` |
| `app/scripts/cc180_build_llt_live.py` | R1-b blöndun → `last_listing_text_blend.csv` + SPÁ (engin DB-skrif) |
| `D:\_audit\cc180_textathekja\q00_skema.py` | skema, relacl, pg_stat, lesendur |
| `…\q01_maeling.py` (`fyrir` / `eftir_r3` / `eftir_r1b`) | þrjár þekjumælingar með nefnurum |
| `…\q02_r3_spa.py` | verbatim-lestur + spá endurmæld á pkl |
| `…\q03_r1b_thurrkeyrsla.py` | R1-b þurrkeyrsla + falspróf |
| `…\q04_parity4` | rannsókn á hliði [4] (arfur vs afturför) |
| `…\cc180_rollback_r3.sql` | rollback R3 (skrifað FYRIR flipp) |
| `…\last_listing_text_pre_cc180_60807.{csv,pkl}` | júlí-árgangurinn |
| `…\r3_build.log`, `r3_stage.log`, `r3_flip.log`, `r1b_build_dryrun.log` | keyrslusaga |
| `public.last_listing_text_old_r3` | 60.807 raðir, læst anon/authenticated, felld í frágangi lotu |
