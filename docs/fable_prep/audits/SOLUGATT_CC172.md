# SOLUGATT_CC172 — sölugáttin: pöntun → greiðsla → framleiðsla → afhending

**Lota cc172, hafin 2026-08-24.** DB-skrifaleyfi (eina skrifalota í gangi).
API-pásan gildir: ENGIN Fable-köll án sérstaks GO (lokaprófið í lið 4 fær
sér GO-línu). Hrágögn og drög: `D:\_audit\cc172_solugatt\`.

## §0 Fastar forsendur (verðdómar Danna, teknir fyrir lotu)

- Verð: **2.500 kr listaverð / 1.250 kr kynningarverð, m/VSK.** Kynningarverðið
  birt sem afsláttur af listaverði.
- Sjónarhorn við opnun: **kaupandi EITT** (seljandahlið bíður ástandskontrasta-GAT,
  sjá EFFORT_METRICS_CC165 §2 gat #1).
- Sölusvið: **gæðaþrep T1/T2** — T3+ fær kurteist „ekki í boði fyrir þessa eign enn".
  (Orðanótur: í fyrirmælunum stendur „stop_tier T1/T2"; T1/T2 er `valuation_tiers.tier`
  (gæðaþrep), `stop_tier` er slökunarstig compsins (S0/S1p/S2p/S3). Bókað hér sem
  `tier IN ('T1','T2')` — cc166-dæmið „T2/S0/A" staðfestir lesturinn.)
- Hirðing: **Paddle (merchant-of-record)** — SANDBOX-lyklar í þessari lotu; lifandi
  lyklar verða cc172b þegar skráning Danna klárast. Paddle ber VSK-skil; verð birt m/VSK.
- Worker: á D:-vélinni, Task Scheduler-mynstur — **MVP-ákvörðun bókuð með
  flutningsslóð í ský síðar** (workerinn les/skrifar aðeins Supabase + Storage,
  engin staðbundin ríkisföng önnur en logg → flutningur er endurhýsing, ekki endurhönnun).

## §1 GRUNNURINN Í DB — drög (HALT A, ekkert beitt)

### §1.1 Staðfest upphafsstaða (lesfyrirspurnir, pooler read-only)

Skriptur `q01`–`q05` í `D:\_audit\cc172_solugatt\`, úttök `*_out.json`:

- `model_metrics_scalar`: **EKKI til** — cc165-flutningurinn er sannanlega óbeittur. ✔
- `fable_orders`: ekki til. `storage.buckets`: **TÓM** (fyrsti bucket verkefnisins).
- Engin Paddle/orders/checkout-vísun í verdmat-ai (grep, node_modules undanskilið).
- **Supabase-MCP er ÓTENGT í þessari lotu** (ToolSearch finnur hvorki
  `apply_migration` né `execute_sql`) — sjá beitingarplan §1.5.

### §1.2 Ákvörðunartölur kaupa-hnappsins (q01/q03/q04)

| Mengi | Fjöldi |
|---|---|
| Allar T1-eignir | 71.038 |
| Allar T2-eignir | 84.549 |
| **Allar T1+T2** | **155.587** |
| T1 með virka söluauglýsingu | 2.063 |
| T2 með virka söluauglýsingu | 3.464 |
| **T1+T2 með virka söluauglýsingu** | **5.527** |
| T3–T5 með virka söluauglýsingu (fá „ekki í boði enn") | 372 |
| Virk sala á fastnum ÁN valuation_tiers-raðar | 2.262 |

Mæligildra bókuð í leiðinni: `scraper.v_eign_virk_auglysing.er_atvinnuhusnaedi`
er aðeins reiknað fyrir rent — á öllum sale-röðum er það NULL og `NOT`-sía
fellir þá ALLT (q02 mældi 0; q03 sundurliðaði). Sölutalningar hér eru án
þeirrar síu. 383 sale-raðir bera fastnum NULL og detta úr öllum vörpunum.

### §1.3 model_metrics — cc165-skrárnar beitast ÓBREYTTAR

Þrjár skrár af diski, `D:\_audit\cc165_effort_metrics\`:
`model_metrics_schema.sql` → `model_metrics_insert.sql` (32 raðir, ON CONFLICT
DO UPDATE) → mótprófið `q06_stadfesta_sql.py` **endurkeyrt gegn lifandi töflu
eftir innsetningu** (krafan: 32/32). Rollback cc165 `rollback.sql` (tvö þrep:
DELETE raðir / DROP tafla) stendur óbreytt.

Tillögur á tvær óvaldar cc165-ákvarðanir (staðfestast í GO):
- **Töfluheiti: `model_metrics_scalar` stendur** (drögin, insertið og rollbackið
  eru samhljóða skrifuð; endurnefning nú væri handbreyting á sannreyndu skránum).
- **Lesheimild: default-deny stendur** — lesandinn er pakkasmiður workersins um
  service_role; ekkert síðuyfirborð les töfluna í MVP.

GAT-leifin (6 göt, þ.m.t. `uppgert vs gott` +2,09% án nefnara) stendur bókuð í
`GAT_LEIF.json` og **blokkar ekki kaupandaskýrslur** — harða reglan gildir: tala
sem ekki er í töflunni fer á GAT-lista skýrslunnar, ekki í hana.

### §1.4 fable_orders + skýrslugeymslan — ný drög

Skrár í `D:\_audit\cc172_solugatt\` (rollback skrifað FYRST):

- `rollback_fable_orders.sql` + `fable_orders_schema.sql`
- `rollback_storage_bucket.sql` + `storage_bucket_schema.sql`

Kjarnar `fable_orders` (rök í haus skrárinnar):
- `order_id` uuid = aðgangslykill `/pontun/[id]` (ekkert innskráningarkerfi í MVP).
- **Enginn FK á valuation_tiers** — tiers flippast; í staðinn `tier_vid_pontun`
  fryst við stofnun. Sölusviðshliðið sannreynt í app-laginu.
- Status-vél `created→paid→generating→(qa)→delivered / failed / refunded`
  **varin með BEFORE UPDATE trigger** sem hafnar ólöglegum umskiptum og stimplar
  þrepatímana; refund-slóð frá paid/qa/delivered/failed.
- `paddle_transaction_id` UNIQUE (partial) = idempotens webhooksins;
  `paddle_env` ('sandbox'|'live') heldur sandkassafærslum aðgreindum um alla tíð.
- Verð fryst á röðina (listaverd_kr/verd_kr, CHECK verd ≤ listaverð); netfang
  kaupanda á röðinni (PII) → **RLS default-deny, engin stefna, service_role eingöngu.**
- CHECK-hlið: delivered krefst report_path+sha256; greidd staða krefst paddle_txn_id.
- Pollflötur workersins: partial index `WHERE status='paid'`.

Skýrslugeymslan: bucket **`fable-skyrslur`**, private, 50 MiB þak, MIME
text/html+application/pdf, slóðavenja `{order_id}/skyrsla.html`. Engin policy á
storage.objects (default-deny); afhending EINGÖNGU signed URL af serverhlið,
~1 klst gildistími, nýr við hverja heimsókn.

### §1.5 Beitingarplan (eftir GO) — og MCP-fráviksbókunin

Reglan segir „migrations gegnum MCP apply_migration" — **MCP-þjónninn er ótengdur
í lotunni.** Tveir kostir, Danni velur í GO:

- **(a) Danni endurtengir Supabase-MCP** (t.d. `/mcp` í CLI) → beiting eins og venjulega.
- **(b) psycopg2-beiting af diski** um pooler 6543 (`SET TRANSACTION READ WRITE`
  fyrst — sama skrifleið og lifecycle_sweep notar daglega) + **handvirkt
  schema_migrations-reconcile** (snið staðfest í q05: version=YYYYMMDDHHMMSS,
  name=`cc172_*`; sama mynstur og cc164 `20260814221118_cc164_bru_k3d_staging`).

Röðin, hvor leiðin sem valin er (rollback-skrár eru þegar á diski):
1. `model_metrics_schema.sql` → `model_metrics_insert.sql` → q06-mótprófið gegn
   lifandi töflu (32/32 eða rollback þrep 1).
2. `fable_orders_schema.sql` → sannreyning: tafla+trigger til, ólöglegt umskipti
   kastar (prófað með INSERT+UPDATE í rollback-aðri txn), RLS-flagg + grants mæld
   með aclexplode (ekki treyst á exit-status, cc52-reglan).
3. `storage_bucket_schema.sql` → sannreyning: buckets-röðin, public=false,
   signed-URL round-trip á prufuskrá um service_role, anon-sókn á hráslóð = neitun.
4. schema_migrations-reconcile + repo-spegill: báðar cc172-migrations í
   `verdmat-ai/supabase/migrations/` (vef- og webhook-heimilið), cc165-migrationin
   í `app/supabase/migrations/` (model-metrics-lénið, model_quality_eval býr þar).

## §1.6 BEITT 2026-08-31 (GO Danna 26.08) — leið (b), sannreynt

MCP var **enn ótengt** við beitingu (ToolSearch fann hvorki `apply_migration` né
`execute_sql`) → leið (b): psycopg2 um pooler 6543. Upphafsstaðan endurmæld rétt
fyrir beitingu og óbreytt frá HALT A (báðar töflur fjarverandi, `storage.buckets`
tóm, tier-dreifing stafrétt sú sama).

**Beitingartólið `r01_beita.py`** setur `SET TRANSACTION READ WRITE` inn sem
fyrstu stæðu hverrar txn þar sem hana vantar (poolerinn er sjálfgefið read-only;
MCP-leiðin hefði ekki þurft það) og **vistar KEYRÐA textann** sem
`_KEYRT_<nafn>.sql` — sönnunin er læsileg eftir á, ekki endurgetin.
`autocommit=True` svo `NOTIFY pgrst` komist út fyrir txn.

| Skref | Skrá | Innsett RW-lína | Niðurstaða |
|---|---|---|---|
| 1 | `cc165\model_metrics_schema.sql` | 1 | OK |
| 2 | `cc165\model_metrics_insert.sql` | 0 (bar hana sjálf) | OK |
| 3 | `cc172\fable_orders_schema.sql` | 1 | OK |
| 4 | `cc172\storage_bucket_schema.sql` | 0 | OK |

### A2-krafan: 32/32 gegn LIFANDI töflu — PASS

**q06 dugði ekki og var ekki notaður sem dómur.** Hann les
`model_metrics_insert.sql` af diski og ber gegn heimildunum; endurkeyrsla eftir
innsetningu skilar sama svari og fyrir — hann snertir ekki töfluna. Það er hlið
sem les báðar hliðar úr sömu heimild.

Nýtt hlið `q07_stadfesta_lifandi_toflu.py`: raðirnar **sóttar með SELECT úr
`public.model_metrics_scalar`**, gildi hverrar leitað í heimildinni sem *röðin í
töflunni* nefnir. Dómgrindin (`ritmynd`/`i_heimild`) er **dregin úr q06 með `ast`**
— ekki afrituð — svo reglan sé ein heimild og fylgi q06 ef hann breytist.

```
raðir í LIFANDI töflu : 32
raðir sem STANDAST    : 32
raðir sem FALLA       : 0
raðir án gilds nefnara: 0
KRAFA 32/32 PASS      : JÁ
```
Heimildaskrár opnaðar: `cc35_fast.json`, `PAKKI_2281760_cc163.json`,
`fastgreiningar.ts`. Úttak: `q07_stadfesta_lifandi_toflu_out.json`.

### fable_orders — status-vélin raunprófuð (q08)

Öll hegðunarpróf keyrð í txn sem er **rúllað til baka**; `SAVEPOINT` per aðgerð.
Eftir prófin: `SELECT count(*) FROM public.fable_orders` = **0** (engin prufuröð lifði).

- **Lögleg umskipti 8/8 OK**: created→paid, paid→generating, generating→qa,
  generating→delivered, qa→delivered, paid→refunded, failed→generating,
  delivered→refunded.
- **Ólögleg umskipti 5/5 KASTA** (P0001, með order_id í skilaboðum):
  created→delivered, created→generating, paid→delivered, delivered→generating,
  refunded→paid (refunded er dauðendi).
- **CHECK-hlið 5/5 KASTA**: delivered án skýrslu (`fo_delivered_ber_skyrslu`),
  verd > listaverd, paid án paddle-id, `sjonarhorn='seljandi'`, tvítekið
  paddle_transaction_id (23505 = idempotens webhooksins sönnuð).
- Tímastimplar: paid_at/generating_at/delivered_at/status_changed_at öll stimpluð.

**Prófgalli veiddur og lagaður í leiðinni** (bókað því hann er lærdómurinn, ekki
skemagalli): fyrsta smíðin gaf öllum sporum sama `paddle_transaction_id`, svo eftir
fyrstu heppnuðu röð féllu **7 af 8 LÖGLEGUM umskiptum á 23505** — prófið sagði
„KASTAR" af allt annarri ástæðu en umskiptareglunni. Falsneikvæðni sem hefði lesist
sem „status-vélin virkar". Lagað með einstöku id per spori.

### Heimildir mældar, ekki ályktaðar

`aclexplode` á báðum nýju töflunum: **engar** anon/authenticated-heimildir, RLS-flagg
`true` á báðum, **0 stefnur** skilgreindar (default-deny eins og hannað).
Tóm niðurstaða sannar þó ekkert ein og sér — því var `valuation_tiers` (app-read)
höfð með í SÖMU fyrirspurn sem viðmiðun: hún birtist með `SELECT` fyrir bæði
anon og authenticated. Mælingin getur því skilað röðum; tómið er raunverulegt.

### Bucketinn

`storage.buckets`: `fable-skyrslur`, `public=false`, þak 52.428.800 (50 MiB),
MIME `{text/html, application/pdf}`, 0 objects. Engin stefna á `storage.objects`.

### Reconcile + repo-spegill (r02)

Fjórar færslur bókaðar handvirkt í `supabase_migrations.schema_migrations` í sama
sniði og fyrri lotur (q09: version/name/created_by/statements[1]); `statements` ber
**keyrða textann**, ekki frumskrána, svo færslan lýsi því sem gekk í gegn.
Staðfest með endurlestri úr töflunni — **4/4 JÁ**:

| version | name | repo-spegill |
|---|---|---|
| 20260831101200 | cc165_model_metrics_scalar_schema | `app\supabase\migrations\` |
| 20260831101201 | cc165_model_metrics_scalar_insert | `app\supabase\migrations\` |
| 20260831101202 | cc172_fable_orders | `verdmat-ai\supabase\migrations\` |
| 20260831101203 | cc172_fable_skyrslur_bucket | `verdmat-ai\supabase\migrations\` |

Rollback-skrárnar þrjár standa óbreyttar og gilda (cc165 `rollback.sql`,
`rollback_fable_orders.sql`, `rollback_storage_bucket.sql`) — hver með sínu
ÞREP 0 fyrir þá stöðu að lifandi gögn séu komin í töfluna/bucketinn.

### A1 — sviðið eftir cc171

GO-línan bókar „+2.202 eignir að auki eftir cc171-flippið". **Mæling segir að þær
séu ÞEGAR INNI í 155.587**: tier-dreifingin er stafrétt óbreytt milli 24.08 og
31.08 (T1/S0 60.537 … T5/NONE 2.815), og cc171 lauk 24.08 fyrir fyrri mælinguna.
Sviðið er því **155.587, ekki 157.789**. Talan er ekki áætluð heldur endurmæld
tvisvar með viku millibili.

## §2 HALT A — GO-listinn

| # | Ákvörðun | Tillaga |
|---|---|---|
| A1 | Kaupa-hnappur: aðeins T1/T2 m/virkri auglýsingu (5.527 eignir) eða ALLAR T1/T2 (155.587)? | **Allar T1/T2.** 28× stærra söluyfirborð fyrir sama smíðakostnað; sölusviðshliðið er tier-lesturinn sem síðan gerir hvort eð er; „á sölu"-borðinn birtist áfram þar sem hann á við. Kaupandasjónarhornið stendur jafnt fyrir eign sem er ekki formlega skráð (kauptilboð utan skrár, forskoðun). |
| A2 | model_metrics: cc165-skrár óbreyttar — heitið `model_metrics_scalar` + default-deny? | **Já, óbreytt.** Rök í §1.3. |
| A3 | fable_orders-drögin + rollback | GO/athugasemdir — sjá §1.4 og skrána sjálfa. |
| A4 | Bucket `fable-skyrslur` private + signed-URL-afhending | GO/athugasemdir. |
| A5 | Beitingarleið: (a) MCP endurtengt eða (b) psycopg2+reconcile? | **(a) ef það kostar Danna eina skipun; annars (b)** — skrifleiðin er sú sama og daglegu keyrslurnar nota, reconcile-sniðið er staðfest. |

**GO BÓKAÐ 26.08 (Danni):** A1 = allar T1/T2; A2 = já, óbreytt, 32/32 gegn
lifandi töflu; A3, A4 = GO óbreytt; A5 = MCP reynt fyrst, annars (b).
**Framkvæmt 31.08 — sjá §1.6.** MCP reyndist enn ótengt → leið (b).
Öll fjögur skref beitt og sannreynd; ekkert fall.

Fable-lokaprófið í lið 4 fær sér GO-línu og bíður auk þess staðfestingar
morgunloggs um að extraction-lykillinn sé lifandi (`stored>0`) — cc169-gatið
(200/200 falla frá 19.08) er enn óviðgert skv. cc173-bókun.

## §3 FASI 2 — FRAMLEIÐSLU-WORKERINN

Skrift: `D:\verdmat-is\app\scripts\fable_worker.py`.
Logg + vinnumöppur: `D:\_fable_keyrslur\`.

### §3.1 Það sem kortlagningin breytti

Kortlagning keðjunnar (cc157/158/163/166/167/168) leiddi í ljós tvennt sem
hönnunin varð að taka mið af:

- **Enginn orchestrator er til.** Engin `run.py`, `.bat` né Task Scheduler-
  skilgreining er til í keðjunni. Workerinn er fyrsta slíka lagið.
- **Engin skrift tekur `fastnum` sem rök.** Hver harðkóðar `FASTNUM = 2230688`,
  `PAKKI_2230688_cc166.json`, `HLIDARVEGUR64_SKYRSLA.html` og möppuslóðina
  efst hjá sér — **74 tilvik í 27 skriftum** (mælt). Hver fyrri lota bjó til
  nýja eign með því að AFRITA möppuna og breyta hausunum í höndunum.

**Valið: vinnumappa + mælt patch, EKKI endurskrifun.** Workerinn afritar þær
**16 skriftur sem keyrsluröðin snertir** í `D:\_fable_keyrslur\<order_id>\` og
beitir þremur skiptingum (mappa, fastnum, heiti). Sniðmátsskriftirnar eru
ÓSNERTAR, svo sönnunargildi cc166/cc167/cc168-keyrslnanna helst.

Patchið er **mælt, ekki treyst** (`_stadfesta_patch`): (a) engin leif af
sniðmátsgildunum má standa eftir í keyrsluskriftunum; (b) hver skipting verður
að hafa lent einhvers staðar — skipting sem lendir 0 sinnum þýðir að sniðmátið
hefur breyst undir workernum, og str_replace sem hittir ekki lítur nákvæmlega
út eins og str_replace sem tókst.

**Flutningsslóð bókuð:** rétta lagfæringin er `argparse --fastnum` á
q05/q06/q10/q11. Patch-lagið er hliðið þangað til.

### §3.2 API-hliðið (cc172-bannið í kóða)

`--leyfa-fable` er sjálfgefið **OFF**. Án þess stöðvast workerinn FYRIR þrep 3
og skilar `BIDUR_GO`. Hliðið nær LÍKA yfir `count_tokens`: það er ókeypis og
engin líkanakeyrsla, en það er samt kall á api.anthropic.com með
`model=claude-fable-5`, og bannið er orðað um KÖLL, ekki um kostnað.

### §3.3 Keyrslusönnun (0 API-köll)

Prufupöntun stofnuð á **Snæland 2 (2038121, T1/S0, n_comps 2.106)** — vísvitandi
ÖNNUR eign en sniðmátið, annars væri fastnum-skiptingin no-op og patch-hliðið
sannaði ekkert.

```
PÖNTUN c75d5ad7… — fastnum 2038121 (SNAELAND22038121), tilraun 1
   vinnumappa D:\_fable_keyrslur\c75d5ad7… — patch: fastnum x20, heiti x11, mappa x19
   q05.py  exit=0   2.7s      q06.py  exit=0  12.5s
   q08.py  exit=0   2.2s      q09.py  exit=0   2.5s
   q10.py  exit=0   0.1s
   pakki: PAKKI_2038121_cc166.json (711.953 bæti)
   API-HLIÐIÐ LOKAÐ — stöðvast fyrir þrep 3.
```

Keðjan gengur á nýrri eign, á ~20 sekúndum að API-hliðinu.

### §3.4 UPPGÖTVUN: pakkastærð er óstýrð — og hún ræður kostnaði

Pakkinn fyrir Snæland varð **712 KB (532 KB kompakt)** gegn 125 KB hjá
Hlíðarvegi. Sundurliðun (q11) staðsetti þensluna í einum reit:
`sopun.radir` = **1.560 raðir gegn 56**, þ.e. 456 KB af 532.

Sópunin (q06 §3) er allar sölur 24 mán, sama tegund, ±15% flatarmál, í **öllum
póstnúmerum sveitarfélagsins** — og hefur **engin efri mörk**. Reykjavík hefur
~30 póstnúmer, litlu sveitarfélögin eitt. Þess vegna 1.560 gegn 56.

Dreifing mæld á slembiúrtaki 400 T1/T2-eigna (q12; `ORDER BY random()` —
úrtak raðað á fastnum hefði valið eftir ALDRI eignarinnar):

| þrep | p50 | p75 | p90 | p99 | max | >800 raðir |
|---|---|---|---|---|---|---|
| T1 | 112 | 558 | 1.270 | 1.494 | 1.497 | **21%** |
| T2 | 8 | 115 | 497 | 1.479 | 1.493 | 8% |

Afleitt (~97 tókar/sópunarröð + ~30k grunnur): T1 p50 ≈ 41k tókar,
**p90 ≈ 153k**, max ≈ 175k.

**Mæligildra veidd í leiðinni:** fyrsta mælingin notaði EITT póstnúmer og gaf
`max=249` — 6× vanmat, af því nefnarinn var annar en keðjan notar. Talan hefði
lesist sem „engin eign fer yfir 300 raðir". Endurmælt með sveitarfélagi.

**Afleiðing á kóða:** count_tokens-þakið var upphaflega 120.000 og hefði fellt
**fimmtung T1-eigna** sem „bilun" þótt ekkert væri að — þröskuldur undir
eðlilegri dreifingu framleiðir gervi-föll. Hækkað í **250.000**: runaway-vörn,
ekki stærðarstýring.

**Á BORÐI DANNA (§4 a):** á að setja þak á sópunina sjálfa? Það lækkar kostnað
efri helftar T1 um ~$1,3/skýrslu — en sópunartölurnar (p25/p50/p75, histogram)
BIRTAST í skýrslunni og eru raktar í pakkann af dómgrindinni, svo þakið breytir
EFNINU, ekki bara stærðinni. Því ekki tekið upp á eigin spýtur.

### §3.5 Fallmeðferð

Ein endurkeyrsla (`attempt_count`). Falli hún aftur: `status='qa'` +
tölvupóstlína á Danna um Resend (sama leið og `/api/abending` notar).
**Engin sjálfvirk afhending á fallinni skýrslu** — það er allur tilgangur
dómgrindarinnar. Dómgrindarhliðin sem workerinn les: q15 (`a1` dómur, `a2`
skylda n/n, `b` bönn), q27 (`HEILDARDOMUR`), q32 (`DOMUR`).

## §4 FASI 3 — VEFURINN (HALT B)

Allt í `D:\verdmat-is\verdmat-ai\`. Byggt með `npm run build` (Next 16.2.10,
Turbopack) — **grænt**.

| Skrá | Hlutverk |
|---|---|
| `lib/solugatt.js` | EIN heimild: verð, sjónarhorn, sölusvið (`maSelja`), stöðutextar |
| `lib/paddle.js` | Paddle-lagið: transaction-stofnun, **undirskriftar-sannreyning** |
| `components/eign/KaupaSkyrslu.tsx` | Hnappurinn í hnappa-röð eignarhaussins |
| `components/solugatt/KaupaForm.tsx` | Kauphnappurinn (client) |
| `components/solugatt/PontunStada.tsx` | Stöðukassi með polli (15 s) |
| `app/kaupa/[fastnum]/page.tsx` | Pöntunarsíða (force-dynamic) |
| `app/pontun/[id]/page.tsx` | Stöðusíða (noindex) |
| `app/api/pontun/route.js` | Stofnar pöntun -> Paddle-checkout |
| `app/api/pontun/[id]/stada/route.js` | Staðan fyrir pollið (þunn) |
| `app/api/pontun/[id]/skyrsla/route.js` | **Signed URL**, 1 klst, aldrei hrá slóð |
| `app/api/paddle/webhook/route.js` | created -> paid, undirritað + idempotent |
| `app/globals.css` | +97 línur, tókar eingöngu (engin hex-gildi) |
| `components/eign/EignSidaEfni.tsx` | +13 línur: hnappurinn inn í hausinn |

Lykilákvarðanir: **pöntunarröðin er skrifuð FYRST, Paddle-transaction EFTIR**
(annars gæti orðið til greiðsla án pöntunar að hengja hana á);
**sölusviðið er sannreynt í API-inu, ekki bara í hnappnum** (hver sem er getur
POST-að); **verðið er lesið server-megin og fryst** (ekkert verð kemur úr
beiðninni); **hnappurinn stendur ekki í leigu-flæðinu** (skýrslan er skrifuð á
sölulíkani og kaupandasjónarhorni — sömu rök og felldu agentinn af
`/leiguverd` í cc32).

### §4.1 Vefpróf gegn keyrandi þjóni (q13) — STENST 8/8

T1-eign ber hnappinn · T2-eign ber hnappinn · kaupasíðan ber bæði verðin og
afsláttinn · **leigu-flæðið ber hann EKKI** · ógilt fastnum 404 · ógilt
pöntunarnúmer 404 · webhook án undirskriftar hafnað · skýrsluslóð á pöntun sem
er ekki `delivered` skilar 409.

*Prófgalli veiddur:* fyrsta smíð leitaði að samfellda strengnum „50% afsláttur"
og felldi síðuna ranglega — React skýtur `<!-- -->` milli textahluta, svo
strengurinn liggur í HTML sem `50<!-- -->% afsláttur`. Prófið mældi HTML-bæti
þar sem það átti að mæla textann sem SÉST; lagað með því að fjarlægja
`<!-- -->` fyrir samanburð.

### §4.2 Webhook-prófið (q14) — STENST 5/5, RAUNUNDIRRITAÐ

Prófað gegn keyrandi þjóni með raunverulegri HMAC-SHA256 undirskrift:

| Hlið | HTTP | Staða í töflu | Dómur |
|---|---|---|---|
| Röng undirskrift | 401 | created → **created** (óhreyfð) | OK |
| Engin undirskrift | 401 | created | OK |
| Rétt undirskrift | 200 | **created → paid**, txn á röð | OK |
| Endursending sömu færslu | 200 | paid, **1 röð með sama txn** | OK |
| Önnur pöntun, sami txn | 200 | **created** (stelur ekki greiðslu) | OK |

Hlið 1 er kjarninn og það er mælt RÉTT: 401 eitt og sér sannar ekkert ef röðin
breytist samt, svo staðan er **lesin úr töflunni** eftir hvert kall, ekki
ályktuð af HTTP-kóðanum. Prufuraðirnar tvær eyddar í lok prófs.

### §4.3 Eign utan sölusviðs (q16) — STENST 3/3

Þrjár T3-eignir: hnappurinn ber kurteisu línuna („ekki í boði enn"), **enginn
`/kaupa/`-hlekkur í HTML**, kaupasíðan hafnar með skýringu, og
`POST /api/pontun` skilar **409**. Notandi sem sér ekkert veit ekki hvort varan
er ekki til eða síðan biluð — því lína, ekki þögn.

### §4.4 Skjáskot

`D:\_audit\cc172_solugatt\skjaskot\` (Chrome headless, gluggi settur berum
orðum í 1280×1400 — annars klemmist hann í 526 px):
`01_eign_T1_hnappur.png` · `02_kaupa_sida.png` · `03_eign_T2_hnappur.png` ·
`04_pontun_stada.png`.

**Galli sem skjáskotið afhjúpaði og var lagaður:** verðlínan las „1.250 kr"
(server) meðan kauphnappurinn las „1,250 kr" (client, eftir hydration) — sama
tala, tvö snið, á sömu síðu. `toLocaleString("is-IS")` er ICU-háð og skilar
ólíku á server og í vafra. `formatKr` er nú handvirk þúsundaskipting,
deterministic hvar sem hún keyrir. Endurmælt: **öll fimm verðin á síðunni lesa
nú „2.500 kr" / „1.250 kr"**.

### §4.5 Það sem BÍÐUR (ekki bilun)

- **Paddle-lyklarnir eru ekki komnir.** `PADDLE_API_KEY`/`PADDLE_PRICE_ID`
  vantar, svo `/api/pontun` skilar `checkout: null` og skýrri línu til
  notandans í stað hnapps sem gerir ekkert. Pöntunin STENDUR í `created`.
- Í `.env.local` var sett **`PADDLE_WEBHOOK_SECRET=PRUFA_cc172_ekki_raunlykill`**
  til að raunprófa undirskriftina. **Þetta gildi VERÐUR að víkja fyrir
  raunlyklinum í cc172b** — nafnið segir það berum orðum svo það lifi ekki óvart.
- Prufupöntunin `c75d5ad7…` stendur í `failed` (BIDUR_GO) og er merkt
  `PRUFA_cc172_…`; hún er efniviður liðar 4.

## §5 HALT B — á borðinu

**Ekkert er committað og ekkert pushað** (push = deploy). Vinnutréð í
`verdmat-ai` ber aðeins cc172-skrár; óskyldar óraktar skrár fyrri lotna eru
ósnertar (aldrei `git add -A`).

```
 M app/globals.css                  (+97)
 M components/eign/EignSidaEfni.tsx (+13)
?? app/api/paddle/webhook/route.js      ?? app/api/pontun/route.js
?? app/api/pontun/[id]/stada/route.js   ?? app/api/pontun/[id]/skyrsla/route.js
?? app/kaupa/[fastnum]/page.tsx         ?? app/pontun/[id]/page.tsx
?? components/eign/KaupaSkyrslu.tsx     ?? components/solugatt/*.tsx
?? lib/solugatt.js                      ?? lib/paddle.js
?? supabase/migrations/20260831101202_cc172_fable_orders.sql
?? supabase/migrations/20260831101203_cc172_fable_skyrslur_bucket.sql
```
Í `app`-repoinu: `scripts/fable_worker.py`, tvær cc165-migrations,
þetta skjal.

**GO-listi HALT B:**

| # | Ákvörðun |
|---|---|
| B1 | Commit + push (= deploy) á cc172-skrárnar? |
| B2 | Sópunarþakið (§3.4): á að takmarka `sopun.radir`, eða stendur full sópun og hærri kostnaður á efri helft T1? |
| B3 | Task Scheduler-skráning workersins (S4U, sama mynstur og næturkeðjan) — hvenær og á hvaða bili? |
| B4 | **GO-lína á 1–2 Fable-köll** fyrir enda-í-enda prófið (lið 4). Forsenda Danna er UPPFYLLT: extraction-lykillinn er lifandi (§6). |

## §5B HALT B AFGREITT 31.08 — GO Danna á B1–B4

### B1 — env-hliðið og commit

**Env-hliðið (`gattinOpin()` í `lib/solugatt.js`, kallað úr `KaupaSkyrslu`):**
hnappurinn birtist aðeins þegar `PADDLE_API_KEY` OG `PADDLE_PRICE_ID` eru til
staðar. Hvorugt er `NEXT_PUBLIC_*`, svo þau bundlast aldrei í vafrann; kallist
fallið óvart client-megin les það `undefined` og skilar `false` — lokað er
rétta stefnan við óvissu. Hnappurinn kviknar sjálfkrafa þegar cc172b setur
lyklana: engin kóðabreyting, ekkert nýtt deploy.

Þegar gáttin er lokuð birtist **ekkert** — hvorki hnappur né „ekki í boði"-lína.
Eignin er í lagi; það er varan sem er ekki komin, og lína um það á hverri T1/T2-
síðu væri auglýsing á vöru sem ekki er hægt að kaupa. Það er annað mál en eign
UTAN sölusviðs, þar sem notandinn þarf skýringu á því hvers vegna hann fær ekki
það sem nágranninn fær — þar stendur línan áfram.

**Prófað í BÁÐAR ÁTTIR (q17)** — hlið sem aðeins er prófað lokað gæti verið
fast lokað:

| | kaupa-hlekkur í HTML | „Djúpgreining" | „ekki í boði"-lína |
|---|---|---|---|
| **án lykla** | nei | nei | nei |
| **með prufulyklum** | já | já | nei |

Í báðum stöðum: `/kaupa/[fastnum]` svarar 200 og webhookið svarar 401 á
óundirritað — Paddle-onboarding þarf lifandi endapunkta óháð hnappnum.

**Mæligildra veidd (og hún hefði fellt B1 ranglega):** fyrstu tvær keyrslur
prófsins sýndu hnappinn ÞÓTT lyklana vantaði. Það var hvorki hliðið né ISR:
`npm run start` hafði fallið á **`EADDRINUSE`** — þjónn fyrri umferðar hélt
port 3000 og bar byggingu frá því ÁÐUR en hliðið var skrifað. Þjónn sem svarar
er ekki sönnun þess að hann beri kóðann þinn. Prófið ber nú **BUILD_ID af diski
saman við svar þjónsins** og HALT-ar ella.

Prufu-API-lyklarnir voru **fjarlægðir úr `.env.local` strax eftir prófið** svo
þeir opni ekki hnappinn á fölskum forsendum staðbundið.

**Commit (explicit paths, ekkert `git add -A`):**
- `verdmat-ai` **662942b** — 15 skrár, 1.454 innsetningar, 0 eyðingar.
- `app` **db11fcd** — 4 skrár (worker, tvær cc165-migrations, þetta skjal).

### B1 PUSH — stöðvað tímabundið, svo leyst

**Push var fyrst stöðvað.** Þegar GO-línan barst stóðu ópushuð commit annarra
lotna á undan cc172 í sögunni:

```
verdmat-ai  origin/main..HEAD:  662942b (cc172)  +  e761383 (cc175)
```

`git push` ýtir GREININNI, ekki commitinu, svo push hefði tekið
**cc175-ágústskýrsluna í deploy** — og hún var bókuð „committuð ÓPUSHAÐ, bíður
GO". Að deploya hana hér hefði verið að taka ákvörðun sem Danni tók sérstaklega
frá. Hinar leiðirnar voru skoðaðar og hafnað: `push <sha>:main` ýtir öllu upp
að því SHA, og rebase á cc172 undir cc175 hefði endurskrifað sögu annarrar lotu.

**cc175-lotan leysti þetta frá sinni hlið** meðan cc172 beið: hún pushaði sína
vinnu með cherry-pick beint ofan á `e761383` (`3c1e8ca`) og skildi cc172-commitið
viljandi eftir. Það skildi greinarnar eftir sundraðar — `origin/main` 1 á undan,
staðbundið 2 (mitt commit + staðbundinn tvífari cc175-viðbótarinnar).

**Leyst með `git rebase origin/main`:** tvífarinn `c2ee1be` var **sjálfkrafa
sleppt** („skipped previously applied commit" — patch-jafngildur `3c1e8ca`), og
eftir stóð cc172 eitt ofan á origin. Ekkert commit annarrar lotu endurskrifað.
Byggingin endurkeyrð á sameinuðu tré (**græn**) áður en pushað var.

```
3c1e8ca..e2f8d57  main -> main      (verdmat-ai, DEPLOY)
```

### B1 PROD-RAUNPRÓFUN (q20) — STENST 4/4

Keyrt gegn **https://www.verdmat.ai** eftir deploy. Hlið 0 staðfestir fyrst að
prod BERI cc172 (`/kaupa/[fastnum]` var ekki til áður) — annars mældist gamla
útgáfan og „enginn hnappur" segði ekkert, sama villa og `EADDRINUSE` olli
staðbundið. Slóðin svaraði 200 eftir 2 s.

| atriði | niðurstaða |
|---|---|
| `/eign/2038121` (T1) | **enginn kaupa-hlekkur, engin „ekki í boði"-lína** — env-hliðið lokað í Vercel |
| `/eign/2230688` (T2) | sama |
| `POST /api/pontun` | **200**, pöntun stofnuð, `checkout: null` + „Greiðslugáttin er ekki tengd enn" |
| `POST /api/paddle/webhook` óundirritað | **503** („webhook ekki stilltur" — leyndarlykill ekki í Vercel-env; öruggt, 200 væri fall) |
| `/skyrslur`, `/skyrslur/2026-08`, `/` | **200 ×3** — cc175-flipar og forsíða ósnert |

Env-hliðið virkar því í raunumhverfi: allur kaupferillinn er í loftinu og
prófanlegur, en enginn notandi sér hnapp fyrr en lyklarnir koma.

**Prufuraðir hreinsaðar á eftir:** q20 stofnaði raunpöntun á prod (eydd), og
**tvær leifar fundust frá fyrstu q14-keyrslunni** — sú keyrsla féll á
hreinsuninni (`uuid = text`) og skildi raðirnar eftir. Önnur þeirra stóð í
**`paid`**, sem þýðir að workerinn hefði gripið hana í næstu poll-umferð og
eytt Fable-kalli í prufugagn. *Lexía: hreinsun á heima í `finally`, ekki í
framhaldi af heppnaðri keyrslu.* Biðröðin er nú tóm (`status='paid'` = 0).

App-repoið deployar ekki lifandi flöt (`verdmat-is.vercel.app` er 404-lokun
cc159), svo push þar er ekki deploy.

### B4 — fyrsta atrenna felldi FORSENDU B2 (mæling, ekki bilun)

Fyrsta enda-í-enda keyrslan stöðvaðist á kostnaðarvörninni:

```
q05–q10 á 24,1 s   ->  PAKKI_2038121_cc166.json (711.953 bæti)
q11 count           ->  302.098 inntakstókar (~$3,78 cache-skrif)
FALL: yfir þakinu 250.000  ->  status=failed (ein endurkeyrsla eftir)
```

**Vörnin virkaði nákvæmlega eins og hún átti að gera — og mælingin sem hún
skilaði felldi töluna sem §3.4 hvíldi á.** Afleiðslan þar (`30.000 + 97 *
sópunarraðir`) byggði á **3,5 bæti/tóka, ensku viðmiði**. Raunmælt:

| eign | sópunarraðir | tókar (mælt) | bæti/tóki |
|---|---|---|---|
| Hlíðarvegur 64 | 56 | 48.819 | 2,04 |
| Snæland 2 | 1.560 | **302.098** | 1,76 |

⇒ **`tokar ≈ 39.388 + 168,4 × sópunarraðir`** — íslenskur JSON með
fastanúmerum, dagsetningum og götuheitum er nærri tvöfalt tókafrekari en
enska. Fyrri spá sagði 175k þar sem raunveruleikinn er 302k.

**Þakið hefur nú verið leiðrétt tvisvar af sömu ástæðu** — það var sett undir
efri hluta dreifingarinnar:

| þak | uppruni | afleiðing |
|---|---|---|
| 120.000 | ein ágiskun af einu dæmi | hefði fellt 21% T1-eigna |
| 250.000 | afleitt úr RÖNGUM stuðli | = 1.251 raðir, en T1 p90 er 1.270 ⇒ ~10% féllu |
| **350.000** | **mælt, yfir raunhámarki (291k)** | runaway-vörn, ekki stærðarstýring |

Hækkunin í 350k er **leiðrétting á minni eigin röngu tölu, ekki ný ákvörðun**:
GO-línan festi 250k á þeirri forsendu sem ég bar fram — „vel yfir mældu hámarki
(175k)" — og sú forsenda reyndist röng. Ákvörðunin sjálf (þak = vel yfir
raunhámarki) er framkvæmd óbreytt.

**Raunkostnaður og framlegð** (q18; 1.250 kr − VSK 24% − Paddle 5% = **902 kr
nettó**, gengi 138):

| þrep | hundraðshl. | sópun | tókar | kostn. | framlegð |
|---|---|---|---|---|---|
| T1 | p50 | 112 | 58.250 | $2,48 | **+561 kr** |
| T1 | p75 | 558 | 133.358 | $3,42 | +431 kr |
| T1 | p90 | 1.270 | 253.261 | $4,92 | +224 kr |
| T1 | max | 1.497 | 291.489 | $5,39 | **+158 kr** |
| T2 | p50 | 8 | 40.736 | $2,26 | +591 kr |
| T2 | p90 | 497 | 123.085 | $3,29 | +449 kr |

**Framlegðin er jákvæð alls staðar**, þynnst á efri helft T1. Versta dæmi
kostar ~745 kr, ekki ~420 kr eins og B2-forsendan sagði — en 902 kr nettó ber
það. **B2-ákvörðunin stendur því viðskiptalega**, þótt talan sem hún hvíldi á
hafi verið of lág.

*Viðbót við workerinn í leiðinni:* `--order` má nú grípa pöntun í `failed`
(status-vélin leyfir `failed→generating`; það er einmitt endurkeyrslan sem
reglan gerir ráð fyrir). Án þess væri hver fallin pöntun ósnertanleg nema með
handskrifuðu SQL-i.

### B4 — ENDA-Í-ENDA: FABLE-HLUTINN VIRKAR, EFTIRVINNSLAN ER BUNDIN VIÐ SNIÐMÁTSEIGNINA

Eitt líkanakall gert (auk tveggja `count_tokens`). **Skýrslan varð til og var
RÉTTILEGA EKKI AFHENT** — dómgrindin stöðvaði hana og pöntunin stendur í `qa`.

**Tímalína og kostnaður (mælt):**

| þrep | tími | athugasemd |
|---|---|---|
| q05–q10 (pakki) | 16,7 s | 711.953 bæti |
| q11 count | 3,1 s | 302.098 tókar |
| **q11 run 1 (Fable)** | **492,2 s** (8,2 mín) | `SVARAD_AF_FABLE=true`, `stop_reason=end_turn` |
| q23/q24/q26/q29 (gröf, kort, ísetning, stíll) | ~40 s | **allt exit=0 á nýrri eign** |
| **alls að afhendingarhliði** | **~9,3 mín** | |

Tókar: inn 76 · **cache-skrif 302.022** · út **33.473**. **Kostnaður $5,4497.**
Framlegð á þessari eign: 902 kr − 752 kr = **+150 kr** (í samræmi við q18-spána
+158 kr fyrir T1 max — spáin stóðst).

**Vistunarreglan hélt:** HTML (35.980 bæti) og hugsun (22.543 bæti) voru á diski
áður en nokkur reitur var lesinn úr svarinu.

#### Þrjú atriði stöðvuðu sjálfvirka afhendingu

**(1) NULL-þol — 33,6% sölusviðsins.** q12b kastaði `TypeError` á
`float(E["fasteignamat_gildandi"])`. Mælt: **52.285 af 155.587 T1/T2-eignum
(33,6%) bera NULL** í þeim reit (T1 43,8%, T2 25,1%) — og **100% þeirra bera
gildi í `fasteignamat` í staðinn**. Lagað í vinnumöppu með því að **sleppa
reitnum**, ekki fylla hann úr hinum: gildandi mat og skráð mat eru ólíkar
stærðir, og að setja aðra töluna undir heiti hinnar væri að merkja hana
ranglega. Í leiðinni fannst að ytra gildið í samanburðarlykkjunni var óvarið
(`if not vb` var til, `if not va` vantaði).

**(2) Dómgrindin ber FÖST GILDI HLÍÐARVEGAR 64 — 8 af 30 atriðum** (q23-greining
sem flokkar hvert atriði eftir því hvort gildið er lesið úr pakkanum eða ritað
í skriftina):

| flokkur | atriði |
|---|---|
| **fast gildi** (fella hverja aðra eign) | `dagar_a_markadi` (14/6) · `einflm` (202,3) · `byggar` (1997) · `myndir_44` (44) · `n_shown_5` · `tvo_audkenni` · `leigumat` (377.610) · `visitala_cell_pairs` (11.031) |
| lesið úr pakka (virkar almennt) | 22 atriði, þ.á m. verðmat, bil, ásett, sópun, MAPE, comps |

Af sex brostnum skylduatriðum eru **þrjú hrein gervi-föll**: `einflm` krefst
„202,3" en Snæland er **92 m²**; `byggar` krefst 1997 en eignin er frá **1973**;
`myndir_44` krefst 44. Þrjú til viðbótar eru óviss (`engin_solusaga` á ekki við
því Snæland HEFUR sölusögu; `sopun_n` og `n_comps_136` lesa úr pakka og gætu
verið raunveruleg). q27 felldi sömuleiðis `d2_vidbotartolur`, `d3_graf_krafa` og
`d4_a2_skylda`.

**Dómgrindin er því ekki nothæf sem sjálfvirkt afhendingarhlið** fyrir aðra eign
en þá sem hún var skrifuð fyrir. Þröskuldarnir voru EKKI stilltir til að hún
samþykkti — hlið sem er stillt þar til það hleypir í gegn er ekkert hlið.

**(3) Hnitmiðunin er bundin við nákvæmt HTML sem líkanið endurtekur ekki.**
q31 HALT-aði á „dómslínan fannst ekki í grunnskjalinu": cc168 leitar að
`div.domslina`, en Snælands-skýrslan ber **`class="doms"`**. Efnið er rétt;
**strúktúrinn er ekki deterministic milli keyrslna.** Þetta er dýpsta atriðið:
öll eftirvinnslan (kassinn, V-kaflarnir, prentvörnin) hvílir á því að Fable
skrifi sömu class-heiti í hvert sinn, og það gerir hún ekki. Lagfæringin er
annaðhvort að **festa class-heitin í prompt-grindinni** eða gera eftirvinnsluna
strúktúr-óháða.

*Tvær lagfæringar gerðar í workernum sjálfum (ekki í sniðmátinu):* hann tekur nú
`_pre_hnitmidun.html`-afritið sem q31 krefst (cc168 gerði það í höndunum, og í
framleiðslu er enginn til þess), og hann les út-tókana úr réttum lykli
(`meta["tokar"]["output"]` — fyrsta smíð las `meta["output_tokens"]` og logaði
„0 út-tókar" á keyrslu sem skilaði 33.473; `.get` með sjálfgefnu gildi þegir um
rangan lykil).

#### Hvað B4 sannaði og hvað stendur eftir

| virkar | stendur eftir |
|---|---|
| Pakkasmíð á nýrri eign (patch ×50) | Dómgrindin: 8 föst gildi þarf að lesa úr pakka |
| Fable-keyrsla, effort=high, fallback greip ekki | Prompt-grindin verður að festa class-heitin |
| Vistunarreglan | Skylduatriði sem eiga ekki við allar eignir (`engin_solusaga`) |
| Gröf, kort, ísetning, stílsnið á nýrri eign | NULL-þol inn í sniðmátið (aðeins vinnumappa enn) |
| **Afhending STÖÐVUÐ við fall — `status=qa`, engin sjálfvirk afhending** | Endurkeyrsla q19-afhendingarprófsins þegar hliðin standast |

Kostnaðarspáin stóðst upp á 8 kr, og API-hliðið, vistunarreglan og
fallmeðferðin virkuðu nákvæmlega eins og hannað var. **Það sem vantar er ekki
innviðir heldur að dómgrindin og hnitmiðunin séu leystar frá sniðmátseigninni**
— sama verk og pakkasmiðurinn þurfti, og það er ekki gert upp á eigin spýtur á
sannreyndum skriftum.

### B2 — ekkert sópunarþak (bókað)

Full sópun stendur við opnun; `count_tokens`-vörnin stendur á 250k.
**Bókað á backlog sem hagræðingarkostur, EKKI opnunarbreyting:** deterministic
samantektargrein sópunar í pakkann (p25/p50/p75 + histogram sem **fullsniðnir
strengir**, ekki hráar tölur sem líkanið sníður sjálft) + afmarkað raðasýni,
A/B-mælt gegnum dómgrindina. Framlegðin ber núverandi kostnað: 1.250 kr tekjur
gegn ~420 kr á versta dæmi.

### B3 — Task Scheduler bíður cc172b (bókað)

Skráning fylgir raunlyklunum í einni lotu. Rök: workerinn á ekki að polla með
API-hliðið lokað þegar engin pöntun getur orðið `paid` hvort eð er (engir
lyklar ⇒ ekkert webhook ⇒ ekkert `created→paid`). Þegar að því kemur: **S4U**
(password-principal fellur þögult), full python-slóð **sannreynd fyrir
skráningu**, 5 mín poll, `--leyfa-fable` sett berum orðum í skipunina.

## §5C cc172b — EFTIRVINNSLAN LEYST FRÁ SNIÐMÁTSEIGN (1.–3. + 5.)

**HALT eftir lið 3.** Eitt Fable-kall notað af tveimur heimiluðum.

### §5C.1 Liður 1 — föstu gildin úr dómgrindinni

Hver leið staðfest á TVEIMUR pökkum (Hlíðarvegur + Snæland) svo hún sé heimild
en ekki ágiskun:

| fast gildi (H) | pakkaleið | S |
|---|---|---|
| einflm 202,3 | `eign.einflm` | 92,0 |
| byggar 1997 | `eign.byggar` | 1973 |
| myndir 44 | `myndir.n_alls` | 33 |
| n_shown 5 | `naervidmid.n_synd` | 8 |
| tvo_audkenni 2 | `len(auglysingasaga.mbl_audkenni_2026)` | 1 |
| leigumat 377.610 | `leigumat.pred.pred_mean` | 327.895 |
| cell_pairs 11.031 | `visitala_cellu.sidustu_12_fj[0].cell_n_pairs` | 9.322 |
| dagar 14/6 | `v_units_maeling[0].days_on_market` + lotudagar | 64/85 |

`engin_solusaga` er nú **skilyrt á pakkastöðu** — krafa um að skýrslan segi
„engin þinglýst sala" er krafa um ósannindi á eign sem hefur sölusögu.

**Hliðið (q26): 8 → 0 föst gildi.** En það hlið las EINA blokk í EINNI skrá og
dæmdi því þann stað, ekki keðjuna. Víðari leit (q27_fost_gildi_vitt) fann
**fimm í viðbót**: `q12b` harðkóðaði dagatölur (6/14) sem *afleiddar* — það
skráði RANGAR tölur sem lögmætar og skildi þær réttu eftir órekjanlegar,
hljóðlát bjögun sem er verri en fall; `q12` krafðist „44"; `q27` krafðist
sex nefnara í myndatextum (n=5, 136, 56, n=140, 11.031, 24 pör). Öll rakin í
pakkareiti. **Víðara hliðið: 13 → 0** (skráarnöfn `PAKKI_<fastnum>` undanskilin —
patch-lagið meðhöndlar þau; og docstrings strippaðir með `ast`, því fyrsta
smíðin flaggaði skýringu á fyrri villu sem villuna sjálfa).

**NULL-þolið flutt í sniðmátið** (var aðeins í vinnumöppu): `fasteignamat_gildandi`
sleppt þegar NULL, aldrei fyllt úr `fasteignamat`.

*Villa sem ég olli sjálfur og lagaði:* PowerShell `Get-Content -Raw` +
`Set-Content -Encoding utf8` **tvíkóðaði q15.py**, svo íslensku
samhengis-regexin („ásett|auglýst") urðu að rugli og þrjú skylduatriði sem
stóðust féllu án þess að skýrslan breyttist. Hvorki cp1252- né latin-1-afkóðun
skilaði þeim til baka; skráin var endurheimt úr rollback-afriti og breytingarnar
gerðar aftur með Edit einu. **PowerShell snertir ekki þessar skrár aftur.**

### §5C.2 Liður 2 — strúktúr sem krafa

Prompt-grindin fékk **§6b SKYLDUFORM**: `div.domslina` (eintækt, innan
`div.bordi`), `section.samantekt`, `section.vidauki`, `section.vkafli`,
`table.samanburdur`, `p.caption`, og plásshaldararnir fjórir — með þeirri
skýringu að vanti merki stöðvist vinnslan og skýrslan komist ekki til kaupanda.

- **Nýtt hlið `d6_skylduform`** í q12/q15/q27: mælt STRAX, á sama stað og annað
  form, í stað þess að koma fram sem HALT í q31 löngu eftir að kallið er greitt.
- **q31 les nú markera, ekki nákvæmt class-mengi**: `class="[^"]*\bdomslina\b"`
  (aukaflokkar leyfðir) með bókuðum varaleiðum; þrepsglósan lesin úr pakkanum
  (var fast „T2" og hefði fellt hverja T1/T3/T4/T5-eign).
- **V-kaflarnir fundnir á `section.vkafli` með dýptartalningu**, fjöldinn LESINN
  (var fast 14; nýja skýrslan hefur 15). Bakfærslusönnunin geymir skiptin sem
  pör og er nákvæm andhverfa þeirra — endurgerð úr reglum laumaði inn `\r\n`
  sem var ekki í frumskjalinu og felldi byte-jafngildið á réttri umbreytingu.
- **q32**: lagaskiptingin á `section.vidauki` (var `<!-- ==== LAG B`, athugasemd
  sem cc166 valdi), fyrirsögn má vera h2–h4, kaflafjöldi lesinn.
- **Stökkbreytiprófið smíðar brenglanir ÚR KASSANUM.** Það brenglaði áður
  „143,6", „>14. dagur" og „133,9" — tölur Hlíðarvegar. Á annarri eign hittu þær
  ekkert, `replace` skilaði kassanum óbreyttum, dómurinn felldi hann réttilega
  ekki, og prófið las það sem *„hliðið bítur ekki"*. **Sjálfspróf sem
  stökkbreytir engu mælir ekki hliðið heldur sjálft sig.** Nú er hver brenglun
  staðfest að hafa breytt kassanum áður en dómur er kallaður.

### §5C.3 Liður 3 — pakkaþakið og A/B

Sópunin fékk `similarity` úr `comps_index_v2` (sama lind og lifandi comp-vélin)
með jafnteflisbrjót `thinglystdags DESC, fastnum`; hráar raðir þakaðar við **200**.
**Allar birtar tölur reiknast á FULLA menginu** (1.560) og eru auk þess bornar
fram sem **fullsniðnir strengir** í `sopun.samantekt_strengir` (14 reitir:
n, nefnari, p25/50/75/90, min/max, ppm2, histogram, staða ásetts og mats).

*Bókun sem var leiðrétt fyrir keyrslu:* aðeins **8 af 200 röðum bera similarity**
(comp-vélin þekkir aðeins þær sölur sem hún valdi sjálf). Reglustrengurinn segir
það nú berum orðum — „þær 8 líkustu og þar á eftir nýjustu sölurnar" — í stað
þess að lýsa sér sem similarity-röðun alla leið.

**Þak-A/B (q30): STENST.** `sopun.nidurstada` 26 reitir, `histogram` 34,
`framreikningsstudlar` 37 — **0 munur**. Aðrar greinar: 0 breyttir reitir.
Raðir 1.560 → 200. Kompakt 527.516 → 133.687 bæti (**−74,7%**).

**Tókar (count_tokens, sami endapunktur fyrir/eftir): 302.098 → 77.721 (−74,3%).**

**Fable-kallið (eitt, effort=high):**

| | B4 (fullur pakki) | cc172b (þakaður) | breyting |
|---|---|---|---|
| inntakstókar | 302.022 | 77.787 | **−74,2%** |
| úttakstókar | 33.473 | 33.139 | −1,0% |
| **kostnaður** | **$5,4497** | **$2,63** | **−51,7%** |
| sekúndur | 490,5 | 477,3 | −2,7% |
| HTML stafir | 33.204 | 36.717 | **+10,6%** |
| orð í efnistexta | 3.546 | 4.014 | **+13,2%** |
| myndatextar | 6 | 15 | +150% |
| hugsunarstafir | 22.031 | 15.874 | −27,9% |

**Skýrslan varð LENGRI og ríkari fyrir helmingi lægra verð** — og
sópunartölurnar (n 1.560, p25/p50/p75) standa orðréttar í báðum. Framlegð fer
úr +150 kr í **+529 kr**.

*Ósambærilegt í töflunni:* „V-kaflar 71→15" ber ólíka mælikvarða (textaleit
gegn class-talningu) og segir ekkert; q27-dómurinn FALL→STENST stafar af
dómgrindarlagfæringum liðar 1–2, ekki af þakinu.

### §5C.4 FYRSTA FULLA AFHENDING KEÐJUNNAR

Öll hlið á nýju skýrslunni:

```
q15 (a1)  367 fullyrðingar, 363 BEINT, 4 AFLEITT, 0 ÓREKJANLEGAR  -> STENST
q15 (a2)  SKYLDA 17/17, brostin: []
q15       SKYLDUFORM ALLT TIL (domslina=1, vkafli=15, caption=15)
q27       STENST — d1 61/61, d2 61/61 bókaðar, d3, d5, d4a1, d4a2, d6
q31       15 details-stök, prentvörn virk, bakfærsla byte-eins
q32       STENST — stökkbreytiprófið BÍTUR á öllum fjórum (78,8 / 67 dagar / 7,1 / orð)
```

*Tvær tölur sem dómgrindin veiddi í leiðinni og reyndust réttar:* órekjanlega
talan **1.206** var `n − n_nadu` (1.560−354), lögmæt afleiðsla sem vantaði í
rakningarvélina — fyllimengin eru nú nafngreind. Og myndatextaleitin krafðist
orðsins „graf"; nýja skýrslan ritar „Dreifing framreiknaðra söluverða…".
**Krafa um orð sem líkanið valdi einu sinni er sama villa og krafa um röð sem
það valdi einu sinni.**

**Afhending (r11_afhenda.py — les hliðin af diski, endurkeyrir EKKI Fable):**

```
status delivered · 156.028 bæti · sha cc729bb94393…
signed URL: HTTP 200, SAMA sha úr bucket og á diski og á röð
hrá slóð án undirskriftar: HTTP 400
stöðusíðan: „Tilbúin" + „Opna skýrsluna"
```
q19-afhendingarprófið: **STENST**. Skjáskot `04_pontun_stada.png`,
og hlið-við-hlið `05_skyrsla_B4.png` / `06_skyrsla_cc172b.png`.

*Keyrslutíminn á röðinni (127 mín) er ekki keðjutími* — hann spannar
þróunarvinnuna milli `generating` og `delivered`. Raunkeðjan: pakki 17 s +
count 3 s + **Fable 477 s** + gröf/kort/stíll ~40 s + hnitmiðun ~5 s ≈ **9,1 mín**.

### §5C.5 Liður 5 — myndasýnin (BEITT)

`public.v_eign_myndir` las ekki `property_images.utilokad_kl`, svo útilokaðar
myndir láku á nákvæmlega þeirri lind sem pakkasmiðurinn les OG `/eign/[fastnum]`
birtir. Rollback smíðað **úr lifandi skilgreiningunni** (`pg_get_viewdef`), ekki
handskrifað.

| mæling | gildi |
|---|---|
| útilokaðar raðir sem láku | 57 á 55 eignum |
| þar af á sölusviðinu T1/T2 | 49 á 47 eignum |
| raðir í sýn: fyrir → spá → **mælt** | 2.728.362 → 2.728.305 → **2.728.305** |
| útilokaðar sem leka enn | **0** |
| eignir sem urðu myndalausar | **0** |
| anon/authenticated heimildir | óbreyttar (SELECT) |

Migration `20260831234841_cc172b_v_eign_myndir_utilokad` bókuð í
`schema_migrations` + repo-spegill.

### §5C.7 ENV-MISRÆMIÐ — KOSTUR 2 BEITTUR (01.09)

**Vandinn:** Paddle heldur sandbox- og live-lyklum aðskildum. Heimildarskráin
`D:\env.local` ber fjögur sandbox-gildi með `_SANDBOX`-viðskeyti; kóðinn las
ósuffixuð nöfn alls staðar, svo sandkassinn var ótengjanlegur.

**Liður 1 — ein hjálparlesning.** `lib/paddle-env.js`: `paddleEnv()`,
`paddleLykill(grunnheiti)`, `paddleLykilNafn()`, `paddleRekstrarlyklarTil()`.
`lib/paddle.js` og `app/api/paddle/webhook/route.js` flytja hana inn; engin
`if`-setning afrituð. Villuskilaboð nefna **nafnið sem vantaði, aldrei gildi**.

*Frávik frá fyrirmælunum, bókað:* `app/api/pontun/[id]/stada/route.js` var í
listanum en **les engan Paddle-lykil** (flytur aðeins inn `stadaTexti`) — hún
fékk því enga breytingu. Þriðja skráin sem raunverulega les lykil er
`lib/paddle.js`.

**Liður 2 — gildin afrituð** (r12, `--confirm`): fjögur `_SANDBOX`-nöfn í
`verdmat-ai/.env.local`. `D:\env.local` **óbreytt, aðeins lesin**. Skriftan ber
öryggishlið: hún stöðvast ef ósuffixað Paddle-nafn er þegar í markskránni.
Afritið sem hún tók var **fært út úr repo-möppunni** í `_audit` (það var
gitignored gegnum `.env*`, en leyndarmál á ekki heima í vinnutré).

**Liður 3 — ENV-HLIÐSSÖNNUN (q36): STENST.** Tvær óháðar sannanir, því hvorug
dugir ein: kóði sem lítur rétt út getur verið yfirskyggður, og hegðun sem
stenst gæti staðist af því lyklana vantar alveg.

**(A) Kóðinn** — línan sem hnappshliðið les env í, orðrétt:

```js
return Boolean(process.env.PADDLE_API_KEY && process.env.PADDLE_PRICE_ID);
```
`lib/solugatt.js` → `gattinOpin()`. Mælt: `les_api_key=True`,
`les_price_id=True`, **`nefnir_SANDBOX=False`**, **`kallar_paddleLykil=False`**.
`KaupaSkyrslu.tsx`: `les_env_sjalfur=False`, `kallar_gattinOpin=True` — enginn
framhjáleið.

**(B) Hegðunin** — þjónn með `PADDLE_ENV=sandbox`, **fjórum sandbox-nöfnum og
NÚLL live-nöfnum** (BUILD_ID staðfest í svari):

| eign | kaupa-hlekkur í HTML |
|---|---|
| T1 Snæland 2 | **False** |
| T2 Hlíðarvegur 64 | **False** |

**Sandbox-lykill kveikir ekki hnappinn.** Aðgreiningin er líka fest í
athugasemd í báðum skrám: `paddleLykill()` er fyrir rekstrarlykla og má aldrei
nota í `gattinOpin()` — „að samræma" þau væri ekki hreinsun heldur galli.

### §5C.8 Liður 4 — ÞRJÁR BLOKKANIR MÆLDAR, ENGU FABLE-KALLI EYTT

Sandbox-API-lykillinn **virkar** (`GET /prices` → HTTP 200). En keflið kemst
ekki í gegn, og allar þrjár blokkanirnar eru Paddle-dashboard-verk:

**1. Verðið stemmir ekki (alvarlegast).** `GET /prices/pri_01m1fb4mvse14xhj3v0farnp23`:

| | |
|---|---|
| status | active |
| heiti | „Fable-skýrsla — einskiptiskaup EUR" |
| **upphæð** | **1900 EUR-sent = €19,00** |

Síðan sýnir **1.250 kr** og frystir þá tölu á pöntunarröðina; Paddle myndi
rukka **€19,00 ≈ 2.850 kr** — meira en tvöfalt kynningarverðið og yfir
listaverðinu (2.500 kr). Kaupandi sem sér 1.250 kr og er rukkaður um €19
er ekki verðmisræmi heldur röng verðupplýsing í kaupferli.
**Þarf ISK-verð í Paddle (eða ákvörðun um að selja í EUR og birta það verð).**

**2. Engin default checkout URL.** `POST /api/pontun` skilar 500; Paddle svarar
`transaction_default_checkout_url_not_set`: *„Cannot create a transaction or
open a checkout as no default payment link has been set for this account."*
Pöntunarröðin varð til (röðin er skrifuð FYRST — hönnunin virkaði), Paddle-kallið
féll, og röðin var hreinsuð á eftir.

**3. Engin notification-destination.** `GET /notification-settings` → **0
destinations**, svo **enginn raunverulegur webhook-secret er til**. Aðeins
`PADDLE_WEBHOOK_SECRET=PRUFA_cc172_ekki_raunlykill` stendur í env, og GO-línan
bannar það gildi í þessu prófi — réttilega.

**Ekkert Fable-kall var notað.** Keflið stöðvast á blokkun 2 löngu áður en
`generating` gæti hafist; að greiða $2,63 fyrir keyrslu sem kemst ekki í gegnum
greiðsluskrefið væri sóun. **GO-heimildin á 1 kall stendur ónotuð.**

**Það sem Danni þarf að gera í Paddle sandbox-dashboard:**
1. Setja **default payment link** (Checkout → Settings).
2. Búa til **verð í ISK** á 1.250 kr (eða ákveða EUR-verðlagningu og laga
   `lib/solugatt.js` + textana í samræmi).
3. Búa til **notification destination** á webhook-slóð og skila
   `PADDLE_WEBHOOK_SECRET_SANDBOX`. Athuga: destination þarf **opinbera slóð** —
   localhost gengur ekki, svo annaðhvort tunnel eða Vercel Preview (Production
   er ósnert skv. banni).

### §5C.6 Liður 4 — BÍÐUR (Paddle-lyklar ókomnir)

`PADDLE_API_KEY`/`PADDLE_PRICE_ID` eru enn óstillt, svo env-hliðið er lokað og
enginn hnappur á prod. **`PADDLE_WEBHOOK_SECRET=PRUFA_cc172_ekki_raunlykill`
stendur enn í `.env.local` og VERÐUR að víkja** áður en nokkuð kviknar.
Task Scheduler-skráningin fylgir lyklunum í sömu lotu (S4U, python-slóð
sannreynd fyrir skráningu, 5 mín poll).

## §6 Extraction-lykillinn — FORSENDAN ER UPPFYLLT

Danni setti sem skilyrði fyrir GO á Fable-lokaprófið að morgunloggur staðfesti
`stored>0`. Mælt í ÁFANGASTAÐNUM (`scraper.listing_extractions`), ekki á
stöðuskrá keðjunnar:

| dagur | útdrættir | validation_status='ok' |
|---|---|---|
| 31.08 | 88 | 88 |
| 30.08 | 88 | 88 |
| 29.08 | 88 | 87 |
| 28.08 | 88 | 86 |
| 27.08 | 88 | 87 |
| 26.08 | 88 | 88 |
| 25.08 | 88 | 87 |
| 19.–24.08 | **0** | — |
| 18.08 | 50 | 50 |

Síðasti útdráttur **31.08 kl. 02:48 UTC**. cc169-lykilbilunin (200/200 falla frá
19.08) er því **lokuð frá 25.08**, og nóttin kaupir nákvæmlega 88 hasha —
cc173-þakið bindandi eins og bókað var.

## §7 Bönn lotunnar (staðfest virt)

- **Fable-köll: 0.** API-hliðið í workernum er sjálfgefið lokað og var aldrei
  opnað; keyrslusönnunin í §3.3 stöðvaðist á því. `count_tokens` heldur ekki
  kallað.
- **γ-frost, predictions/módel/comps, cc164-staging: ósnert.** Skrifin í lotunni
  voru nákvæmlega: tvær nýjar töflur (`model_metrics_scalar`, `fable_orders`),
  einn bucket, fjórar `schema_migrations`-færslur, og prufupantanir sem voru
  eyddar aftur (nema `c75d5ad7…`, bókuð í §4.5).
- **Ekkert deploy, ekkert commit, ekkert push** fyrir HALT B.
- Fullar slóðir alls staðar; engar `cd`-samsetningar í skipunum.
- `git add -A` hvergi notað — óskyldar óraktar skrár fyrri lotna standa ósnertar.
