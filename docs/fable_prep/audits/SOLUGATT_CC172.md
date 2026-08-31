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
