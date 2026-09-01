# VERÐRÉTTLEIKI — GAGNAVIÐGERÐ #1a (cc179)

**Lota:** cc179 · **Dagur:** 2026-09-01 · **Heimild:** `GAGNAVIDGERD_CC178.md` §3.2–§4 (R4, R5)
**Úttektarskrár:** `D:\_audit\cc179_verd\` (q01–q08) · **Skrifalota** (eina)
**Kaupskrárútgáfa allra mælinga:** `Last-Modified: Tue, 01 Sep 2026 02:00:51 GMT`,
`content_md5 d7mR34/DOVyn+5Uclg5Pug==`, 231.327 raðir
**Akkeri:** `pipeline_config.sales_history_anchor_ym = 2026-09` · **Regla:** `refinedB-v1-2026-07-02`
**Engin LLM-köll. Predictions/módel ósnert. Comps/tiers ÓSNERT.**

---

## 0. NIÐURSTAÐA Í EINNI TÖFLU

| | fyrir | eftir | hlið |
|---|---:|---:|---|
| Raðir `sales_history` sem víkja frá ferskri kaupskrá | **137** / 229.998 | **0** | parity, 9 reitir |
| ...þar af rangt kaupverð (×10) | 1 | 0 | |
| ...þar af `onothaefur` 0→1 (sala sem HMS ógilti) | 3 | 0 | |
| ...þar af `is_suspect_comparable` | 94 | 0 | |
| ...þar af `suspect_reason` (flagg rétt, ástæða röng) | 40 | 0 | |
| Lifandi eignasíður með rangt gildi í sölusögu | **137** | **0** | mælt á 6 síðum |
| `/eign/2273049` þinglýst 7.7.2026 | **725,0 M kr** | **72,5 M kr** | lesið lifandi |
| Comp-raðir sem breytast | — | **0** | ekkert comps-skrif |

**Kóðarótin lokuð:** `daily_sales_refresh.py` ber nú UPDATE-arm með akkerishliði og
breytingaskrá. Þurrkeyrsla eftir sópun: `NEW=0 DRIFT=0`.

**HALT A** (liður 3, fyrir comps-flipp) og **HALT** (liður 4) neðst — §5, §7.

---

## 1. R4 FORMÆLT Á RÖÐ — FULLUR DIFF (q02)

Kjarninn er **fluttur inn**, ekki endurútfærður: `rebuild_sales_history.derive_sales_rows`
— nákvæmlega sá kóði sem `daily_sales_refresh` keyrir, með cc39 ×1000-yfirtakinu virku og
sömu heimildum (`properties`-univers 232.887, HMS-`einflm` 204.451, CPI-akkeri úr
`pipeline_config`).

### 1.1 Lykillinn er PAR, ekki `faerslunumer`

| | |
|---|---:|
| raðir `sales_history` | 229.998 |
| aðgreind `faerslunumer` | **216.306** |
| aðgreind `(faerslunumer, fastnum)` | **229.998** |
| raðir sem deila `faerslunumeri` með annarri röð | **13.692** |

`uq_sales_faerslunumer_fastnum` er á PARINU. Verkbeiðnin bað um „UPSERT á `faerslunumer`";
það hefði samsvarað 13.692 rööum ranglega. **Allt hér keyrir á parinu.**

### 1.2 Reitadiffið — sundurliðað, með nefnara

Nefnari = 229.998 raðir sem finnast í BÁÐUM (`left_only = 0`, `right_only = 0`:
næturkeyrslan 02:30 hafði þegar sett inn 33 nýja lykla, svo lyklamengin voru samstillt).

| reitur | misræmi | nefnari | % |
|---|---:|---:|---:|
| `thinglystdags` | 0 | 229.998 | 0,0000 |
| **`kaupverd_nominal`** | **1** | 229.998 | 0,0004 |
| **`kaupverd_real`** | **1** | 229.998 | 0,0004 |
| `einflm_at_sale` | 0 | 229.998 | 0,0000 |
| `byggar_at_sale` | 0 | 229.998 | 0,0000 |
| **`onothaefur`** | **3** | 229.998 | 0,0013 |
| **`is_suspect_comparable`** | **94** | 229.998 | 0,0409 |
| **`suspect_reason`** | **134** | 229.998 | 0,0583 |
| `suspect_ruleset_version` | 0 | 229.998 | 0,0000 |
| **raðir með ≥1 misræmi** | **137** | 229.998 | **0,0596** |

**Þrennt er nýtt gagnvart cc178** (sem mældi 3 / 3 / 90 gegn HRÁRRI kaupskrá):

1. **Verðmisræmin eru 1, ekki 3.** cc178 bar `sales_history` við hráa kaupskrá án cc39
   ×1000-yfirtaksins. Yfirtakið er hluti afleiðslukjarnans (`rebuild_sales_history.py:79`,
   virkjar á `744084`/`744085`), svo þær tvær raðir **eiga** að víkja frá hráu skránni og
   gera það ekki frá kjarnanum. Réttur nefnari fyrir viðgerð er 1.
2. **`suspect_reason` víkur á 134 rööum — 40 þeirra með RÉTTU flaggi.** Boole-gildið eitt
   felur ástæðuþáttinn; `title`-textinn á „frávik"-pillunni las rangt á 40 síðum til viðbótar.
   Þessi ás var ekki í cc178.
3. **`onothaefur` er 3 raðir, ALLAR 0→1** — sölur sem HMS hefur síðan lýst ónothæfar en
   `/eign` sýndi enn sem gildar (síðan les `.eq('onothaefur', 0)`).

### 1.3 ×10-mynstrið talið sér — **það er EKKI ×1000-arfurinn**

| | |
|---|---|
| hlutföll DB/leitt í öllu diffinu | `10,0 → 1 röð`. Ekkert `1000`, ekkert `0,001`. |
| röðin | `faerslunumer 744841`, `fastnum 2273049`, þinglýst 2026-07-07 |
| DB | 725.000.000 kr (= **725.000** þús.kr í kaupskrárrými) |
| kaupskrá 01.09 | 72.500.000 kr (= **72.500** þús.kr) |
| hrátt kr/m² á DB-gildinu | 725.000.000 / 91,3 = **7.940.854** |
| cc39-þröskuldur `X1000_RAW_KRM2_MIN` | 20.000.000 — **röðin er UNDIR honum** |
| `x1000_override_audit.jsonl` | 107 línur, 3 aðgreind `faerslunumer`: 744059, 744084, 744085. **744841 er ekki þar og hefur aldrei verið.** |

> **Svar við spurningunni í verkbeiðninni: nei.** Þetta er **einn aukastafur** í
> HMS-lindinni sjálfri, ekki ×1000-ættin úr júlí. cc39-vörnin gat aldrei virkjað
> (undir þröskuldi) og hefði ekki lagað ×10 þótt hún hefði séð röðina. Villan var
> leiðrétt í kaupskránni af HMS eftir á — og NEW-KEYS-ONLY hleðarinn bar
> leiðréttinguna aldrei.

### 1.4 Sundurliðun suspect-misræmisins

| | leitt = `false` | leitt = `true` |
|---|---:|---:|
| **DB = `false`** | — | **92** |
| **DB = `true`** | **2** | — |

- Öll 92 vanmerktu bera ástæðuna **`size_mismatch`** — R3 í REFINED-B ber
  sölu-`EINFLM` saman við **NÚVERANDI** HMS-stærð. HMS hefur uppfært `properties.einflm`
  síðan röðin var skrifuð. **Það er TÍMAHÁÐUR ás** (sbr.
  `feedback_single_deed_sian_er_timahad`): flaggið er skilgreint gegn hreyfanlegri stærð,
  svo geymt flagg rekur frá reglunni af sjálfu sér, án þess að nokkur kaupskrárröð breytist.
- Bæði ofmerktu bera `kv_extreme` í DB — `FASTEIGNAMAT` var leiðrétt í kaupskránni,
  svo `kv` féll aftur inn í bandið [0,50–2,00]. Annað þeirra er 744841 sjálft.
- Sölumánuðir misræmisins: 2024-02 (1), 2025-05 (1), 2026-01 (13), 2026-02 (28),
  2026-03 (49), 2026-05 (9), 2026-06 (26), 2026-07 (8), 2026-08 (2).

`suspect_reason` án flaggabreytingar (40 raðir) — allar sama mynstrið, `size_mismatch`
bætist við eða fellur úr samsettri ástæðu:

| geymt | leitt | n |
|---|---|---:|
| `new_build_first_sale` | `size_mismatch+new_build_first_sale` | 18 |
| `kv_extreme+new_build_first_sale` | `kv_extreme+size_mismatch+new_build_first_sale` | 11 |
| `kv_extreme` | `kv_extreme+size_mismatch` | 8 |
| `kv_extreme+new_build_first_sale` | `new_build_first_sale` | 2 |
| `kv_extreme+size_mismatch` | `size_mismatch` | 1 |

### 1.5 Sýnileiki — misræmið er á ÞREMUR yfirborðum, ekki einu (q04)

cc178 taldi comp-gridið. Það er **ekki** stærsta yfirborðið. `/eign` les
`sales_history` **beint** (`verdmat-ai/lib/eign-queries.js:209-215`,
`.eq('onothaefur', 0)`, dálkar `is_suspect_comparable` + `suspect_reason`), og
`components/eign/Verdsaga.tsx:33-40` teiknar „frávik"-pilluna og `title`-textann úr
þeim reitum. **Hver misræmisröð er sitt eigið notendasýnilega yfirborð á síðu
eignarinnar sem SELDIST.**

| yfirborð | raðir | eignasíður |
|---|---:|---:|
| verð rangt (birt tala) | 1 | 1 |
| sala sýnd sem GILD en HMS segir ónothæf | 3 | 3 |
| „frávik"-pilla VANTAR | 92 | 92 |
| „frávik"-pilla OFAUKIÐ | 2 | 2 |
| `title`-texti rangur (flagg rétt, ástæða röng) | 40 | 40 |
| **samtals, án tvítalningar** | **137** | **137** |

Allar 137 eignirnar eru til í `public.properties` (síðurnar svara 200).

| yfirborð 2 — comp-grid annarra eigna | |
|---|---:|
| `comps_index_v2`, `set_role='comp'`, `rank ≤ 8` | **2.184 raðir** á **2.183 eignum**, gegnum **17** `faerslunumer` |

| yfirborð 3 — Fable/agent | |
|---|---|
| `verdmat-ai/lib/agent-tools.js:402` | `fravik = s.is_suspect_comparable` — sama flagg, sami nefnari og yfirborð 1 |

---

## 2. R4 — KÓÐAFIXIÐ (`daily_sales_refresh.py`)

### 2.1 Rótin, orðrétt

```python
new_keys = derived_keys - live_keys        # :233-236 fyrir cc179
to_insert = dk[dk["_k"].isin(new_keys)]
```

Röð sem er þegar inni var **aldrei endurleidd**. Hausinn bókaði það sem hönnun
(„DO NOTHING is locked — kaupskra mutations are negligible noise"). Mælingin fellir þá
forsendu: 137 raðir, þar af ein 725 milljónir á lifandi síðu.

### 2.2 Það sem bættist við

| þáttur | staður | hvað |
|---|---|---|
| `UPDATE_COLS` | `:126` | 9 reitir sem armurinn má skrifa; lykillinn sjálfur er ekki þar |
| `normalize_for_compare` / `_neq` / `compute_drift` | `:214–290` | drift-greining, NULL-örugg, **sama vörpun á báðar hliðar** |
| `real_anchor_parity_gate` | `:293` | **akkerishliðið** — sjá 2.3 |
| `apply_updates` | `:322` | `UPDATE … FROM (VALUES)` + breytingaskrá, **í txn kallandans** |
| skref `[3b]` | í `main()` | drift + hlið, sundurliðað í loggnum |
| `UPDATE_ABORT_THRESHOLD = 5000` | `:150` | ein misheppnuð kaupskrárútgáfa má ekki endurskrifa töfluna |
| MV-refresh | skref `[6]` | skilyrðið er nú `inserted + updated > 0` (var `inserted > 0`) |
| `--no-update` | CLI | gamla hegðunin, ef þarf að einangra arminn |

### 2.3 Akkerishliðið — af hverju `kaupverd_real` er varið

`kaupverd_real = kaupverd_nominal × cpi[akkeri]/cpi[ym]`. Afleiðslukjarninn reiknar það
alltaf á **núverandi** `pipeline_config`-akkeri. Ef geymda taflan situr á öðru akkeri
(því `monthly_cpi_reanchor.py` á þann dálk og keyrir á öðrum takti) myndi blint UPDATE
**endurakkera alla töfluna í hljóði** — nákvæmlega það sem hausinn bannar.

Hliðið **mælir** það í stað þess að gefa sér: á rööum þar sem `kaupverd_nominal` er
**óbreytt** er `kaupverd_real` hrein fylgnistærð af akkerinu einu. Fari misræmið þar yfir
50 raðir eða 0,1 % fellur dálkurinn úr skrifmenginu, með háværri log-línu, og hitt gengur
samt. **Mælt 2026-09-01: 0 af 229.997 — hliðið OPIÐ, taflan er á akkeri 2026-09.**

### 2.4 Galli sem æfingin fann — `rowcount` mældi eina síðu

`execute_values` sendir eina stæðu á síðu (`page_size`, sjálfgefið 100) og `cur.rowcount`
ber **aðeins síðustu síðuna**. Fyrsta útgáfa armsins skilaði því `rowcount 37` gegn spá
137. **Hliðið beit og felldi keyrsluna.** Lagfært: hlutað sjálft (`UPDATE_PAGE_SIZE = 500`)
og rowcount **lagt saman** yfir síður. Án hlutunarinnar hefði hliðið mælt síðustu síðuna
og hleypt hinum í gegn ómældum — sbr. `feedback_maeldu_falsjakvaedni_hlidsins`.

### 2.5 Æfing á skrifleiðinni — MEÐ stökkbreytingu (q05)

Ein txn, alltaf rúllað til baka. Þrjú þrep:

| þrep | mæling | niðurstaða |
|---|---|---|
| **A** | `apply_updates` á raunverulega drift-menginu | `rowcount 137 == spá 137` · breytingaskrá **233 línur** |
| **B** | in-txn parity: raðirnar lesnar aftur INNAN txn gegn leiddu gildi | **0 misræmi á öllum 9 reitum** |
| **C** | **falspróf:** ein röð stökkbreytt í gildi sem kjarninn framleiðir aldrei (`27.000.000 → 27.012.345`) | parity-mælingin **féll (1)** — hliðið bítur |
| — | eftir `ROLLBACK` | breytingaskrá 0 línur · 744841 enn 725.000.000 |

Þrep C er skilyrðið fyrir því að þrep B þýði nokkuð (sbr.
`feedback_sjalfsprof_sem_stokkbreytir_engu`). Auk þess er **sama skriftan** falsprófuð á
sjálfu ástandinu: `--dryrun` skilaði `DRIFT=137` fyrir sópun og `DRIFT=0` eftir hana.

---

## 3. LEIÐRÉTTINGARSÓPUNIN (`cc179_apply_corrections.py`)

**Ein lind:** sópunin flytur inn `compute_drift`, `real_anchor_parity_gate` og
`apply_updates` úr `daily_sales_refresh`. Ekkert endurútfært — annars ræki sópunin og
næturkeyrslan í sundur (`feedback_speglud_regla_er_ekki_reglan`).

### 3.1 Þrepin sem keyrðu

| þrep | aðgerð | niðurstaða |
|---|---|---|
| `--schema` | `public.sales_history_corrections` (`cc179_corrections_schema.sql`) | taflan til, 0 línur |
| `--freeze` | staging-afrit **snertra raða** → `public.sales_history_pre_cc179` | **137 raðir** + `D:\_audit\cc179_verd\cc179_rollback.sql` |
| `--apply` | UPDATE í **einni txn**, `run_id = 153` | **rowcount 137 == spá 137** · breytingaskrá **233 línur == spá 233** · 12 MV endurhlaðin |
| `--parity` | diff gegn kaupskrá endurmælt | **0 á öllum 9 reitum** |

**Rollback-heimildin var til ÁÐUR en skrifað var** — `--apply` neitar að keyra ef
staging vantar eða ber annan fjölda en drift-mengið (hlið, ekki athugasemd).

### 3.1b RÉTTINDAGALLI SEM SMÍÐIN BJÓ TIL — OG VAR LÆSTUR (q09)

Báðar nýju töflurnar erfðu Supabase-sjálfgildið
`ALTER DEFAULT PRIVILEGES … GRANT ALL ON TABLES TO anon, authenticated`. Mælt með
`relacl` (eina grantor-mælingin — `role_table_grants` segir ekki hver veitti):

| tafla | `relacl` við sköpun | RLS |
|---|---|---|
| `sales_history` (til samanburðar) | `anon=r`, `authenticated=r` | **á** |
| `sales_history_corrections` | **`anon=arwdDxtm`**, `authenticated=arwdDxtm` | **af** |
| `sales_history_pre_cc179` | **`anon=arwdDxtm`**, `authenticated=arwdDxtm` | **af** |

Lifandi próf undir `SET LOCAL ROLE anon` **las báðar** (233 og 137 raðir). `d` og `D` í
þeirri ACL eru `DELETE` og `TRUNCATE`: **anon gat eytt rollback-heimildinni og
breytingaskránni.** Breytingaskrá og rollback-heimild sem anon getur `TRUNCATE`-að er
hvorugt.

**Læst samstundis**, í sömu lotu og töflurnar urðu til:
`REVOKE ALL … FROM PUBLIC, anon, authenticated` + `GRANT SELECT … TO service_role` +
`ENABLE ROW LEVEL SECURITY` á báðum (og á `_id_seq`). Endurmælt:

```
sales_history_corrections : relacl {postgres=arwdDxtm, service_role=arwdDxtm}   rls=true
sales_history_pre_cc179   : relacl {postgres=arwdDxtm, service_role=arwdDxtm}   rls=true
anon SELECT -> InsufficientPrivilege: permission denied  (báðar)
```

Reglan er **skjalfest í `CLAUDE.md`** („EVERY new `public` table gets RLS + tight grants in
the SAME migration it is created — including snapshot / staging / scratch tables", cc9
2026-07-14). Smíðin braut hana samt, og aðeins **mæling** fann það — ekki lestur á
reglunni. Læsingin er nú **inni í `cc179_corrections_schema.sql` og inni í `--freeze`**,
svo hún getur ekki gleymst næst.

### 3.2 Breytingaskráin

`public.sales_history_corrections`: **233 línur á 137 rööum**, ein lína á **reit**, hver
með gömlu og nýju gildi, `kaupskra_md5`, `kaupskra_last_modified`, `anchor_ym`,
`suspect_ruleset_version`, `source`, `run_id`.

| dálkur | línur |
|---|---:|
| `suspect_reason` | 134 |
| `is_suspect_comparable` | 94 |
| `onothaefur` | 3 |
| `kaupverd_nominal` | 1 |
| `kaupverd_real` | 1 |

Dæmi (744841), beint úr töflunni:

| reitur | úr | í |
|---|---|---|
| `kaupverd_nominal` | 725000000 | **72500000** |
| `kaupverd_real` | 734429344 | **73442934** |
| `is_suspect_comparable` | `True` | **`False`** |
| `suspect_reason` | `kv_extreme` | **NULL** |

allar með `kaupskra_last_modified = Tue, 01 Sep 2026 02:00:51 GMT`,
`kaupskra_md5 = d7mR34/DOVyn+5Uclg5Pug==`, `anchor_ym = 2026-09`, `source = cc179_sweep`.

### 3.3 Parity utan snerta mengisins

Fyrir sópun mátti afleiðslukjarninn nákvæmlega við **229.861** raðir (229.998 − 137).
Eftir sópun mátti hann við **allar 229.998**, með **óbreyttri kaupskrá** (sami `md5`).
`UPDATE`-rowcount var **137**, samsvörunin var á lyklaparinu úr staging-menginu.
Raðirnar 229.861 mátu því sömu gildi fyrir og eftir: **0 breytingar utan mengisins.**
Heildarfjöldi raða óbreyttur (229.998), `max(thinglystdags)` óbreytt (2026-08-31).

### 3.4 `kaupverd_real` var ENDURREIKNAÐ, ekki afritað

`73.442.934 = 72.500.000 × cpi[2026-09]/cpi[2026-07]` — úr sama afleiðslukjarna og
akkerinu í `pipeline_config`, ekki `725.000.000/10`. Sbr.
`feedback_flipp_verdur_ad_endurgera_afleidda_dalkinn`.

---

## 4. R5 — SUSPECT-MERKINGARNAR (q07)

### 4.1 Gagnahliðin er þegar lent

R5 og R4 eru **sama diffið**, ekki tvö. Sópunin í §3 leiðrétti bæði — 94 flögg og 134
ástæður fóru með í sömu txn. Regla: **`suspect_rules.compute_suspect` gegnum
afleiðslukjarnann**, sama fall og byggingin kallar, aldrei speglað.

| ás | fyrir | eftir |
|---|---:|---:|
| raðir með rangt `is_suspect_comparable` | 94 | **0** |
| raðir með ranga `suspect_reason` | 134 | **0** |
| lifandi eignasíður með ranga „frávik"-pillu eða ranga ástæðu | 134 | **0** |

### 4.2 …EN comps breytast ekki af því — og geta það ekki

> **Mæld staðreynd sem verkbeiðnin gerði ekki ráð fyrir:**
> `precompute/build_comps_v2.py:189` **REIKNAR** `is_suspect_comparable` sjálft úr sinni
> eigin kaupskrárlesningu og síar á það (`:206 f_su`). Það **les aldrei**
> `public.sales_history`. Leiðrétting á `sales_history` breytir `comps_index_v2`
> **engu**, hvorki strax né síðar.

Þetta er nákvæmlega tvíárgangs-vandinn sem cc178 §3.2 lýsti — og hann þýðir að „comps
endurreiknað fyrir snerta mengið" er **ekki flipp á afleiðslu okkar viðgerðar**, heldur
sjálfstæð skurðaðgerð á comps-töflunni. Ekkert comps-skrif var framkvæmt.

### 4.3 Hvað MYNDI gerast — mælt, ekki áætlað

Hliðin tvö sem byggingin beitir á comp-pollinn eru `f_su` (suspect) og `f_on` (ónothæfur).
Fyrir snertu sölurnar 137:

| | fellur út EFTIR = nei | fellur út EFTIR = já |
|---|---:|---:|
| **fellur út FYRIR = nei** | 0 | **79** |
| **fellur út FYRIR = já** | **2** | 56 |

81 sala skiptir um hlið: **79 nú útilokaðar** (voru inni), **2 nú inni** (voru útilokaðar).

Af þeim 79 eru **15** raunverulega sýndar sem comps í dag:

| | |
|---|---:|
| comp-raðir sem hyrfu | **1.882** |
| markeignir sem tapa comp | **1.881** |
| þar af sem tapa 1 comp / 2 compum | 1.880 / 1 |

**Áhrif á `≥3`-hliðið (`K_MIN = 3`, `build_comps_v2.py:89`), versta fall** — hver tapaður
compur talinn aðgreindur `fastnum` í S3-menginu, svo `n_comps` lækkar 1:1:

| | eignir | % af 167.503 |
|---|---:|---:|
| `n_comps ≥ 3` **FYRIR** | 155.587 | 92,886 |
| `n_comps ≥ 3` **EFTIR** | 155.580 | 92,882 |
| **breyting** | **−7** | **−0,0042 pp** |

Miðgildi `n_comps` á snertu markeignunum er **111** (p25 = 72, p75 = 233). Því fer aðeins
0,372 % þeirra niður fyrir hliðið. **Kostnaðurinn sem cc178 óttaðist — „comp-fjöldi
lækkar á allt að 1.888 eignum" — er raunverulegur í rööum talið en 0,0042 pp á hliðinu.**

### 4.4 Eignirnar sjö sem færu undir hliðið

| fastnum | tier | stop_tier | `n_comps` fyrir → eftir | `n_shown` fyrir → eftir | grade |
|---|---|---|---|---|---|
| 2258870 | T2 | S3 | 3 → **2** | 3 → 2 | C |
| 2272351 | T2 | S3 | 3 → **2** | 3 → 2 | B |
| 2272354 | T2 | S3 | 3 → **2** | 3 → 2 | B |
| 2272364 | T2 | S3 | 3 → **2** | 3 → 2 | B |
| 2272367 | T2 | S3 | 3 → **2** | 3 → 2 | B |
| 2277446 | T2 | S3 | 3 → **2** | 3 → 2 | B |
| 2277448 | T2 | S3 | 3 → **2** | 3 → 2 | B |

Allar sjö sitja **nákvæmlega á** `n_comps = 3` og stoppa á `S3` — þynnsta þrepið.

### 4.5 20 eigna sýnishorn (markeignir sem tapa comp)

| fastnum | tier | stop | `n_comps`→ | `n_shown`→ | tapaðir | undir hlið |
|---|---|---|---|---|---:|---|
| 2258870 | T2 | S3 | 3 → 2 | 3 → 2 | 1 | **já** |
| 2272351 | T2 | S3 | 3 → 2 | 3 → 2 | 1 | **já** |
| 2272354 | T2 | S3 | 3 → 2 | 3 → 2 | 1 | **já** |
| 2272364 | T2 | S3 | 3 → 2 | 3 → 2 | 1 | **já** |
| 2272367 | T2 | S3 | 3 → 2 | 3 → 2 | 1 | **já** |
| 2277446 | T2 | S3 | 3 → 2 | 3 → 2 | 1 | **já** |
| 2277448 | T2 | S3 | 3 → 2 | 3 → 2 | 1 | **já** |
| 2065495 | T2 | S0 | 179 → 177 | 8 → 6 | 2 | nei |
| 2321239 | T2 | S3 | 4 → 3 | 4 → 3 | 1 | nei |
| 2159733 | T2 | S3 | 6 → 5 | 6 → 5 | 1 | nei |
| 2160240 | T2 | S3 | 6 → 5 | 6 → 5 | 1 | nei |
| 2277456 | T1 | S3 | 6 → 5 | 6 → 5 | 1 | nei |
| 2289586 | T2 | S3 | 6 → 5 | 6 → 5 | 1 | nei |
| 2272384 | T2 | S2p | 7 → 6 | 5 → 4 | 1 | nei |
| 2272388 | T2 | S2p | 7 → 6 | 5 → 4 | 1 | nei |
| 2272392 | T2 | S2p | 7 → 6 | 5 → 4 | 1 | nei |
| 2272396 | T2 | S2p | 7 → 6 | 5 → 4 | 1 | nei |
| 2277449 | T2 | S3 | 7 → 6 | 7 → 6 | 1 | nei |
| 2277450 | T2 | S3 | 7 → 6 | 7 → 6 | 1 | nei |
| 2277451 | T2 | S3 | 7 → 6 | 7 → 6 | 1 | nei |

Full skrá: `D:\_audit\cc179_verd\q07_markeignir.csv` (1.881 raðir).

---

## 5. HALT A — ÁKVÖRÐUN UM COMPS · **LEYST: KOSTUR A (Danni, 2026-09-01)**

> **GO:** *„KOSTUR A. Ekkert gert við comps; næsta heila keyrsla `build_comps_v2`
> sjálfheilar (−7 eignir, −0,0042 pp af 167.503 — undir öllum aðgerðarmörkum).
> Hönnunarbókunin stendur: næsta heila endurbygging LES
> `sales_history.is_suspect_comparable` í stað þess að reikna sitt eigið."*
>
> Ekkert comps-skrif framkvæmt í cc179 og ekkert áformað. Kostir B og C **felldir**.

**Ekkert comps-skrif framkvæmt. Ekkert staging-mengi búið til fyrir comps.**

Verkbeiðnin bað um „comps/tiers endurreiknað fyrir snerta mengið eitt í staging
(cc171-mynstrið)". Mælingin í §4.2 fellir forsenduna: `comps_index_v2` er ekki afleidd af
`sales_history`, svo ekkert er að flippa sem leiðir af viðgerðinni. Kostirnir eru þrír:

| | kostur | hvað gerist | kostnaður |
|---|---|---|---|
| **A** | **ekkert gert við comps núna** (tillaga) | næsta heila `build_comps_v2`-keyrsla les ferska kaupskrá og felur mismuninn af sjálfri sér — **taflan sjálfheilar** | 1.882 comp-raðir á 1.881 eign sýna comp sem reglan vill útiloka, þar til næst er byggt. Áhrif á hliðið þegar það gerist: **−7 eignir, −0,0042 pp** |
| **B** | **skurðaðgerð núna** — eyða 1.882 rööum úr `comps_index_v2` og endurreikna `valuation_tiers` fyrir 1.881 eign | comps yrðu samstillt strax | `valuation_tiers` ber `comp_wmedian_kr`, `d_log`, `cell_*`-tölfræði og `flag_divergence` sem eru reiknuð úr **öllu sellumenginu**. Að endurreikna þau fyrir hlutmengi er endurútfærsla byggingarinnar — **tvær lindir**, nákvæmlega gallinn sem verið er að laga |
| **C** | **heil `build_comps_v2`-keyrsla** | allt samstillt | snertir langt út fyrir mengið sem cc179 leiðrétti (öll kaupskráin hefur hreyfst síðan 2026-08-12) — **utan banns verkbeiðninnar** |

**Tillaga: A.** Ávinningur B er 0,0042 pp á hliðinu; kostnaðurinn er önnur lind fyrir
tölfræði `valuation_tiers`. Rétta lagfæringin er hönnunarbókunin í §6 — að byggingin
**lesi** geymda flaggið — og hún tekur gildi í næstu heilu endurbyggingu hvort eð er.

**Ákveðið 2026-09-01: A.** −7 eignir og −0,0042 pp eru undir öllum aðgerðarmörkum.

**Hvað A þýðir í reynd — svo næsta lota viti hvað hún erfir:**

1. `comps_index_v2` situr áfram á árgangi **2026-08-12** og ber 1.882 comp-raðir sem
   REFINED-B á dagsins kaupskrá myndi útiloka. Það er **skjalfest bið, ekki galli** — og
   það sem meira er, sömu raðir myndu hvort eð er hreyfast við næstu byggingu af öllum
   hinum kaupskrárbreytingunum síðan 12.08, ekki bara af þessum 15 sölum.
2. **Ósamræmið milli sölusögu og comp-grids er samt horfið á öllum 137 síðunum**, því
   yfirborðin þrjú í §1.5 eru aðskilin: sölusagan les `sales_history` (leiðrétt), comp-
   gridið les `comps_index_v2` (óbreytt). Eina röðin sem bar ósamræmi á SÖMU síðu — 744841
   með 725,0 í söluferli og 72,5 í comp-gridi — er leiðrétt.
3. Þegar `build_comps_v2` er næst keyrt heilt **verður hönnunarbókunin í §6 að fara inn í
   sömu ferð**, annars endurskapar keyrslan tvíárganginn samstundis.

---

## 6. HÖNNUNARBÓKUN — bókuð í `DECISIONS.md` 2026-09-01, EKKI beitt hér

`build_comps_v2.py:189` endurreiknar staðreynd sem `public.sales_history` geymir. Tveir
árgangar sömu staðreyndar reka alltaf í sundur — cc178 mældi 90, cc179 mældi 94 flögg og
134 ástæður. **Í næstu endurbyggingu á `build_comps_v2` að LESA
`sales_history.is_suspect_comparable` / `.suspect_reason` í stað þess að reikna þau**, svo
ein hlið beri staðreyndina. `sales_history` er rétta lindin: hún er nú sjálfleiðrétt
daglega (UPDATE-armurinn), ber breytingaskrá og er lesin beint af notendafletinum.

Sbr. `feedback_afleiddur_eiginleiki_ma_ekki_lesast_af_toflunni` og
`feedback_hlid_sem_les_badar_hlidar_ur_somu_heimild_er_daudt`. **Ekki beitt í cc179.**

---

## 7. SANNPRÓFUN Á LIFANDI FLETI (liður 4)

Cache-athugasemd: `/eign` notar `unstable_cache` með `EIGN_CACHE_TTL = 3600`
(`verdmat-ai/lib/eign-queries.js:144,177`). Fyrsta sókn eftir sópun (09:31 UTC) skilaði
**enn 725,0 M kr** — stale-while-revalidate. Sókn 09:33 skilaði réttu gildi.
**Gagnaviðgerð verður ekki að notendaviðgerð fyrr en cache-ið veltur** (sbr.
`feedback_utgafa_ogildir_ekki_gagna_cache`); `/api/endurnyja` gerir það strax en krefst
`ENDURNYJA_LYKILL`, sem er ekki á þessari vél.

### 7.1 `/eign/2273049` — verðvillan

```
Verðsaga | 2008 · þinglýst 22.4.2008 | 23,0 M kr
         | 2026 · þinglýst 7.7.2026  | 72,5 M kr        ← var 725,0 M kr + „frávik"
Verðmat í dag                        | 74,2 M kr
Akkeri · fyrri sala · júlí 2026      | 72,5 M kr
```

`725,0 M kr` kemur **0 sinnum** fyrir á síðunni (var 2). `72,5 M kr` kemur 6 sinnum.
„frávik"-pillur á síðunni: **0**. **Sama síða ber nú EINA tölu um söluna** — ósamræmið
milli comp-gridsins (72,5) og söluferilsins (725,0) er horfið.

### 7.2 Sölusagan lesin á fimm eignum til viðbótar

| eign | ástæða | lifandi sölusaga eftir |
|---|---|---|
| `/eign/2126376` | `onothaefur` 0→1 | salan 22.7.2026 **horfin**; eftir standa 2006 og 2017 |
| `/eign/2130774` | `onothaefur` 0→1 | salan 6.8.2026 **horfin**; eftir stendur 2023 |
| `/eign/2070307` | `onothaefur` 0→1 | salan 11.8.2026 **horfin** → „Engin þinglýst sala í kaupskrá frá 2006" |
| `/eign/2038296` | flagg `false→true` | 22.1.2026 · **„frávik"** · 164,9 M kr |
| `/eign/2207267` | flagg `false→true` | 19.1.2026 · **„frávik"** · 34,0 M kr |

### 7.3 Fable-pakkinn — `verdsaga_eignar`, READ-ONLY, engin LLM-köll (q08)

Sama fyrirspurn og `eign-queries.js:209-215` keyrir, undir `SET LOCAL ROLE anon`, vörpuð í
farmsnið `agent-tools.js:398-404` — **fullsniðinn farmur**, ekki hrár dálkur:

```json
{"solur": [
  {"dags": "2008-04-22", "kaupverd_kr": 23000000, "fravik": false},
  {"dags": "2026-07-07", "kaupverd_kr": 72500000, "fravik": false}
]}
```
staging (fyrir): `2026-07-07  kaupverd=725.000.000  onothaefur=0  fravik=True`

| eign | farmur eftir |
|---|---|
| 2273049 | `72500000`, `fravik: false` |
| 2070307 | `{"solur": []}` — ónothæfa salan hverfur úr farminum |
| 2038296 | `164900000`, `fravik: **true**` |

### 7.4 Næturleiðin eftir viðgerð

```
[3]  NEW=0  GONE=0  (live=229.998, derived=229.998)
[3b] akkerishlið OPIÐ: kaupverd_real víkur á 0 af 229.998 — taflan er á akkeri 2026-09
[3b] DRIFT=0 raðir af 229.998 sameiginlegum (0,0000 %)
[4]  DRYRUN — engin skrif. Myndi setja inn 0 raðir og uppfæra 0 raðir.
```

---

## 8. ROLLBACK

| heimild | staður |
|---|---|
| gögn | `public.sales_history_pre_cc179` — **137 raðir**, öll 12 dálkarnir eins og þeir voru |
| SQL | `D:\_audit\cc179_verd\cc179_rollback.sql` — ein txn, `SET TRANSACTION READ WRITE` fyrst, væntur rowcount **137** |
| breytingaskrá | `public.sales_history_corrections` — stendur eftir bakfærslu, sem heimild um að skrifin áttu sér stað |
| kóði | `scripts/daily_sales_refresh.py.pre_cc179_20260901T091620Z` · eða `--no-update` fyrir gömlu hegðunina án bakfærslu |
| MV | bakfærsla krefst `REFRESH MATERIALIZED VIEW CONCURRENTLY` á sömu 12 MV á eftir |

Bakfærslan skilar 725-milljóna villunni á lifandi flötinn. Hún er þarna fyrir bilun, ekki
fyrir eftirsjá.

---

## 9. ÓLEYST / VIÐVARANDI

1. **`size_mismatch` er tímaháður ás.** R3 ber sölu-`EINFLM` við **núverandi**
   HMS-stærð, svo geymt flagg rekur frá reglunni í hvert sinn sem `properties.einflm`
   hreyfist — án þess að nokkur kaupskrárröð breytist. UPDATE-armurinn eltir það nú
   daglega (rétt), en það þýðir **viðvarandi UPDATE-umferð** og þar með daglegan
   MV-refresh sem áður sleppti. Fjöldinn er lítill (92 raðir söfnuðust frá 2024-02) en
   hann er ekki núll í jafnvægi.
2. **Comps eru enn á árgangi 2026-08-12** (§4.2, §5) — bíður GO.
3. **`/api/endurnyja`-lykillinn er ekki á þessari vél.** Hver gagnaviðgerð bíður því allt
   að 60 mín eftir cache-veltu áður en notandi sér hana.
4. **cc178-tölurnar 3 / 90 eru úreltar** — réttu nefnararnir gegn afleiðslukjarnanum eru
   **1 / 94 (+134 ástæður)**. §1.2.
5. **Réttindagallinn í §3.1b var lagaður, en hann bendir á kerfisbundna hættu:** hver
   `CREATE TABLE` í `public` á þessum Supabase-instans kemur með fullt DML til `anon`
   nema það sé afturkallað í sömu ferð. Reglan er skjalfest í `CLAUDE.md`; hún dugði
   ekki. **Mældu `relacl` á hverri nýrri töflu áður en lotu lýkur** — `to_regclass`-tékk
   eða exit 0 á migration segir ekkert um veitingar.

---

## 10. LOKASKIL

**Lotan er lokuð 2026-09-01. Kostur A ákveðinn (§5). Ekkert bíður ákvörðunar.**

### 10.1 Það sem stendur eftir í DB

| hlutur | staða |
|---|---|
| `public.sales_history` | **229.998 raðir, parity 0 á öllum 9 reitum** gegn afleiðslukjarnanum |
| `public.sales_history_corrections` | 233 línur (`run_id 153`), RLS á, `anon` engin réttindi |
| `public.sales_history_pre_cc179` | 137 raðir — **rollback-heimild, má henda þegar Danni telur það óhætt** |
| `public.comps_index_v2` / `valuation_tiers` | **ósnert** (árgangur 2026-08-12) |
| `public.predictions` / módel | **ósnert** |
| 12 semantic-MV | endurhlaðin 09:27–09:28 UTC |

### 10.2 Kóði (repo `D:\verdmat-is\app`, `main`)

| commit | efni |
|---|---|
| `893423e` | UPDATE-armur + akkerishlið + breytingaskrá + sópunarskrifta + þetta skjal + DECISIONS |
| `36f7fa8` | læsing nýju taflnanna (`anon=arwdDxtm` → `service_role` eitt, RLS á) |
| *(lokafærsla)* | GO á kost A bókað í §5 + DECISIONS |

Ekkert pushað. Afrit af upphaflegu skriftunni:
`scripts/daily_sales_refresh.py.pre_cc179_20260901T091620Z`.

### 10.3 Hvað næsta lota erfir

1. **`build_comps_v2` má ekki keyra heilt án hönnunarbókunarinnar** (§6). Sú keyrsla
   endurskapar tvíárganginn samstundis ef byggingin heldur áfram að reikna sitt eigið
   `is_suspect_comparable` í stað þess að lesa geymda flaggið.
2. **UPDATE-armurinn er nýr í næturkeyrslunni.** Fyrsta lifandi keyrsla er 02:30 í nótt.
   Ef `D:\daily_sales_refresh.log` sýnir `[3b] !! AKKERISHLIÐ FALLIÐ` er `sales_history` á
   öðru CPI-akkeri en `pipeline_config` — það er `monthly_cpi_reanchor`-mál, ekki
   viðgerðarmál, og armurinn heldur áfram án `kaupverd_real`. Ef `DRIFT` fer yfir 5.000
   stöðvar skriftan sig sjálf (`UPDATE_ABORT_THRESHOLD`) og merkir keyrsluna `failed`.
3. **`size_mismatch` heldur áfram að reka** (§9.1). Búast má við fáeinum UPDATE-rööum á dag
   og þar með MV-refresh sem áður sleppti á no-op nóttum.
4. **Óleyst utan cc179:** R3 (síugalli `build_last_listing_text.py:59`), R1 (afþíðing
   textalindarinnar), R6 (`fastnum IS NULL`) — allt óhreyft, sjá `GAGNAVIDGERD_CC178.md` §4.

---

*Úttektarskrár: `D:\_audit\cc179_verd\q01–q09` + `q02_diff.pkl`, `q03_misraemi_137.csv`,
`q07_markeignir.csv`, `cc179_drift.csv`, `cc179_rollback.sql`.
Beisli falsprófuð: skrifleiðin stökkbreytt og felld (q05 þrep C); `rowcount`-hliðið beit á
raunverulegum `execute_values`-galla (§2.4); réttindin mæld með `relacl` og lifandi
`anon`-lestri, ekki með exit-kóða (§3.1b); afleiðslukjarninn er fluttur inn, ekki
speglaður, bæði í mælingu og skrifum.*
