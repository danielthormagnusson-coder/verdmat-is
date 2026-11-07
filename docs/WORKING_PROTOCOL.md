# WORKING_PROTOCOL — Reglur fyrir skjalauppfærslur

**Tilgangur**: Koma í veg fyrir að Claude tapi efni þegar það uppfærir project skjöl. Lesist af Claude í upphafi hverrar session.

---

## Grunnregla: ADDITIVE, NOT REGENERATIVE

Claude má **aldrei** skrifa yfir project skjal með nýrri útgáfu sem er smíðuð upp úr hans eigin minni. Alltaf:

1. **Les** núverandi innihald skjalsins fyrst með `view` tool á `/mnt/project/<skjal>.md`.
2. **Afrita** í `/mnt/user-data/outputs/<skjal>.md` með `bash_tool` (`cp`).
3. **Breyta** með `str_replace` — aldrei með `create_file` nema um nýtt skjal sé að ræða.
4. **Presenta** með `present_files`.

Ástæða: Claude memory er ekki lossless. Hver re-generation drepur details. Eftir 3–4 iterations getur 40%+ af innihaldi skjalsins verið horfið — oft subtle tölur og töflur sem skipta máli.

---

## Hard rule: verbatim-check fyrir edits á STATE eða DECISIONS

Bætt við 2026-04-19 eftir **tvö** sjálfstæð tilvik þar sem Claude endurbyggði þessi skjöl úr knowledge search og tapaði 200+ línum í hvort sinn. Reglan:

**Áður en Claude skrifar `str_replace` (eða ANY edit) á STATE.md eða DECISIONS.md, þá verður:**

1. **Afrita uploaðu / authoritative útgáfuna** í `/mnt/user-data/outputs/<skjal>.md` með `cp` eða `create_file`.
2. **Keyra `wc -l`** á afrituðu útgáfuna og logga niðurstöðuna.
3. **Keyra `grep -c "^## "`** á afritinu til að telja top-level sections.
4. **Bera saman við væntingar**: STATE hefur typically 25+ ## sections, DECISIONS hefur 50+ entries. Ef count er lower en þessir þröskuldir, halt.
5. **Gera spot-check á distinctive phrases** — t.d. `grep -q "Post-parse audit niðurstöður"` á STATE eða `grep -q "Skjalastrúktúr fyrir project continuity"` á DECISIONS. Ef vantar, afritið mistókst — rollback.

Áður en `str_replace` er notað á neðri part af skjali, **view lokadrög** til að staðfesta að efni er óbreytt.

**Rauð flögg sem leggja að Claude heldur niðri og spyrji**:
- Ef uploaðu útgáfan er styttri en væntingar (t.d. STATE < 600 línur).
- Ef Claude „veit" viðbót af distinctive sections sem ekki eru í afriti.
- Ef Danni uploadar skrá og segir „þetta er það sem er á drifinu" — treat hana sem **authoritative**, ekki sem input-merki til að synthesa nýja útgáfu.

**Aldrei**:
- Nota `create_file` til að „endurgera" STATE eða DECISIONS úr `project_knowledge_search` fragments. Knowledge search er eingöngu til backup recovery ef skjalið er **ekki til í project folder og Danni bauð ekki upload**.
- Fella saman sections í styttri útgáfu án explicit samþykkis. T.d. „Áfangi 2.4c niðurstöður" inniheldur sub-tables (Per-year bias, Mechanism 1 validation, Per-segment held MAPE, Per region × segment, SUMMERHOUSE ekki solved, Calibration, Spatial residuals, Go/no-go verdict). **Allar sub-tables eru preserved, ekki summarized**.

---

## Specific reglur

### Fyrir additions (ný section, ný ákvörðun, nýjar tölur)

**Til**: `str_replace` sem finnur anchor-punkt (t.d. ending á fyrri section eða sérstakan comment) og setur inn nýtt efni fyrir ofan eða eftir.

**Dæmi**:
```python
str_replace(
    path="/mnt/user-data/outputs/STATE.md",
    old_str="## Progress tracking\n\n|",
    new_str="## Áfangi 2.4a niðurstöður\n\n[nýtt efni]\n\n---\n\n## Progress tracking\n\n|",
    description="Bæti við 2.4a section fyrir ofan Progress tracking"
)
```

**Ekki**: Re-generate allt skjalið.

### Fyrir corrections (breyta línu, laga tala)

**Til**: `str_replace` með narrow `old_str` sem matchar exact það sem á að breytast, og stuttan `new_str`.

**Dæmi**:
```python
str_replace(
    old_str="**Verkefnisstaða heildar: ~30%**",
    new_str="**Verkefnisstaða heildar: ~35%**",
)
```

### Fyrir structural overhauls (sjaldgæft)

Ef skjal þarf raunverulega endurskipulagningu:

1. **Biðja um explicit heimild**: "Ég vil endurskipuleggja STATE.md — er það ok?"
2. **Gera diff** fyrst: sýna hvaða sections fara, flytjast, koma í staðinn.
3. **Fá samþykki** áður en upp á hendur kemur.

---

## Ábyrgðakröfur fyrir Claude

Í lok hvers túrs þar sem skjal er uppfært, Claude **verður** að:

1. Nefna hvaða skjöl voru uppfærð.
2. Telja línur fyrir/eftir (`wc -l` á gömul vs nýr útgáfu).
3. Ef línum fækkar, útskýra af hverju (t.d. "skiptu út 20-line table fyrir 10-line version sem Danni staðfesti"). Ef ekki explicit samþykki → RED FLAG, rollback.

---

## Bakupp og recovery

**Ef Claude grunar að efni hafi tapast**:

1. Nota `project_knowledge_search` til að finna týnda content í knowledge index (residual snapshots af eldri útgáfum geyma sig þar stundum).
2. Rebuild úr því + núverandi skjali.
3. Sýna Danni diff áður en skipta út.

**Ef Danni bendir á data-tap**:

1. Taka þessu alvarlega — ekki reyna að útskýra burt.
2. Keyra diff: núverandi skjal vs elri útgáfur úr search.
3. Identify hvað hefur horfið.
4. Restore með `str_replace` insertions.
5. Bæta protocol-ið við nýja reglu sem forðar sama mynstri.

---

## Skrár sem þetta protocol gildir fyrir

| Skjal | Notkun |
|---|---|
| `STATE.md` | Snapshot af núverandi stöðu. Additive updates per áfangi. |
| `DECISIONS.md` | Logg af ákvörðunum. Nýjar entries efst. |
| `DATA_SCHEMA.md` | Reference fyrir gagnaskipulag. Breytist þegar gögn breytast. |
| `TAXONOMY.md` | Canonical property type flokkar. Sjaldan breytist. |
| `GLOSSARY.md` | Íslensk hugtök. Bætist við eftir þörf. |
| `DATA_AUDIT_REPORT.md` | Point-in-time snapshot. Ný útgáfa = ný skrá með suffix (t.d. DATA_AUDIT_REPORT_v2.md). |
| `WORKING_PROTOCOL.md` | Þetta skjal. Breytist þegar vinnubrögð læra. |

---

## Workflow template fyrir hvern session start

Nýtt session byrjar. Fyrst:

```
1. view /mnt/project/STATE.md (skil núverandi stöðu)
2. view /mnt/project/DECISIONS.md (sjá hvaða ákvarðanir eru lokaðar)
3. view /mnt/project/WORKING_PROTOCOL.md (þetta skjal — minna mig á reglur)
4. view aðrar skrár eftir þörf (TAXONOMY, GLOSSARY, DATA_SCHEMA)
5. Svara Danni
```

Allar uppfærslur á skjölum í þeim session nota `str_replace` pattern á afrituðu eintaki í `/mnt/user-data/outputs/`.

**Fyrir STATE og DECISIONS sérstaklega**: áður en `str_replace` er notað, keyrðu verbatim-check (sjá Hard rule section):

```
cp /mnt/project/STATE.md /mnt/user-data/outputs/STATE.md
wc -l /mnt/user-data/outputs/STATE.md  # staðfesti línufjöldi match-ar væntingar
grep -c "^## " /mnt/user-data/outputs/STATE.md  # staðfesti section count
grep -q "<distinctive phrase>" /mnt/user-data/outputs/STATE.md  # spot-check
```

Ef Danni upload-ar skrárnar í message (inline document), treat hann uploadið sem authoritative og smíðaðu afritið með `create_file` úr content-inu verbatim. **Ekki mix-a við knowledge search output**.

---

## Workflow template fyrir session END (STATE.md refresh, added 2026-05-27)

Þegar STATE.md er uppfært í lok session — og sérstaklega þegar nýr milestone hefur shipped (Phase complete, recovery klárað, deploy live, o.fl.):

- **Demote fyrri "Síðast uppfært" milestone** í nýjan "Previous <X> milestone" lykil (haldið orðrétt sem var; bara breytt label-inu). Stack-ur upp eins og changelog: "Previous SCRAPER_SPEC milestone", "Previous post-launch polish milestone", "Previous launch-polish milestone", o.s.frv.
- **Bæta nýrri "Síðast uppfært"** efst í skjalinu með núverandi milestone (dagsetning + 2-4 setninga samantekt á helstu áfanga session-arinnar; nefna ALLAR meiriháttar shipped-areas, ekki bara þá sem þetta session vann að).
- **Uppfæra "Verkefnisstaða heildar: ~X%"** ef nýir áfangar hafa shippað sem færa hlutfallið. Halda parenthetical breakdown current (lista hvað er ✅ vs eftir).
- **Roadmap-position blokk** (additive bullets per Phase) er sjálfstæð frá milestone-headers ofan — bæta þar inn nýjum bullet eins og hingað til; en það kemur **til viðbótar** við milestone-header demotion, ekki í staðinn fyrir.

**Reason**: Fyrstu ~5 línurnar af STATE.md verða ALLTAF að endurspegla núverandi stöðu. Project-knowledge panel, raw-GitHub fetch-readers, og skim-lesarar reiða sig á þá fyrstu skjáfyllingu sem source-of-truth check. Ef "Síðast uppfært" er stale, lesendurnir álykta að skjalið sé apríl-útgáfa jafnvel þegar deeper-section content (Roadmap-position, Phase status) er current. Uppgötvað 2026-05-27 sem follow-up á panel-stale diagnostic (sjá DECISIONS 2026-05-26 og þessa lotu).

Þetta er additive til "Workflow template fyrir hvern session start" reglnanna að ofan: **start-template les top-5 línurnar; end-template tryggir að top-5 verði current áður en session lokast**. Saman myndar þetta full-cycle source-of-truth discipline.

DECISIONS.md er *ekki* háð þessari reglu af sömu ástæðu og hingað til: newest-entry-on-top conventionin þar gerir top-of-doc alltaf current sjálfkrafa. STATE.md hefur milestone-header pattern sem þarf eksplisita demotion.

---

## Hvenær er OK að nota `create_file` í stað `str_replace`?

- **Nýtt skjal sem ekki er til** (t.d. fyrsta útgáfa af WORKING_PROTOCOL.md sjálfu).
- **Point-in-time snapshot** með dagsettu nafni (t.d. `DATA_AUDIT_REPORT_2026-04-18.md`) þar sem skjalið er ætlað að vera immutable.
- **Python/script file** þar sem augljóst að öll logic er í skjalinu og ekki dependent á history.

Aldrei fyrir: STATE, DECISIONS, DATA_SCHEMA, TAXONOMY, GLOSSARY.


---

## Document editing (updated 2026-05-06)

Continuity files (STATE, DECISIONS, WORKING_PROTOCOL, TAXONOMY, GLOSSARY, DATA_SCHEMA, LABELING_GUIDE, GOLD_STANDARD_PROTOCOL, EXTRACTION_SCHEMA_v0_2_2, DATA_AUDIT_REPORT) eru canonical í `D:\\verdmat-is\\app\\docs\\*.md`. Edits happen þar directly via Claude Code, þá commit + push origin main. **`docs/` folder ER source of truth.** `D:\\*.md` working copies frá pre-2026-05-06 era eru immutable historical snapshots — ekki touched, ekki canonical.

### Pattern fyrir hvert edit

```bash
# Edit docs/<file>.md directly via str_replace tool
cd /d/verdmat-is/app
git add docs/<file>.md
git commit -m "docs: <short description of change>"
git push origin main
```

### Verbatim-check rules (essential, applied til docs/)

Áður en Claude skrifar `str_replace` (eða ANY edit) á canonical doc:

1. **View** current file fyrst með Read tool á `/d/verdmat-is/app/docs/<file>.md`.
2. **Keyra `wc -l`** á current file og logga niðurstöðuna.
3. **Keyra `grep -c "^## "`** á current file til að telja top-level sections.
4. **Bera saman við væntingar** — sjá distinctive thresholds í `Hard rule` section ofar. Counts hafa vaxið síðan 2026-04-19 entry (STATE núna 2.000+ línur, DECISIONS 1.800+ línur); flag ef substantially lower.
5. **Spot-check distinctive phrases** — t.d. `grep -q "Áfangi 4c LOKIÐ"` á STATE eða `grep -q "Nýjar ákvarðanir bætast við efst"` á DECISIONS. Ef vantar, file is not at expected version — halt.

Áður en `str_replace` er notað á neðri part af skjali, view lokadrög til að staðfesta að efni er óbreytt.

Eftir str_replace, verify wc -l increased (additive principle). Negative line-count delta krefst eksplisít rationale — annars rollback frá pre-edit backup.

### Never use create_file on existing canonical docs
(existing rule, unchanged — `create_file` allowed only fyrir nýtt skjal sem ekki er til, sjá *Hvenær er OK að nota `create_file`* section ofar.)

### Canonical raw URLs (for chat-Claude reference)

- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/STATE.md
- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/DECISIONS.md
- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/WORKING_PROTOCOL.md
- (same pattern for TAXONOMY, GLOSSARY, DATA_SCHEMA, LABELING_GUIDE, GOLD_STANDARD_PROTOCOL, EXTRACTION_SCHEMA_v0_2_2, DATA_AUDIT_REPORT)

### Changelog

**2026-05-06**: D:\\ ↔ docs/ sync pattern retired. Canonical er `docs/` direct via Claude Code editing í `/d/verdmat-is/app/docs/`. D:\\ working copies frá pre-2026-05-06 era left as immutable historical snapshots, ekki touched. Reason: empirical drift Apr 21 → May 6 — all sessions edited docs/ directly without syncing back, D:\\ fell 392 lines behind across STATE+DECISIONS over 15 days. Pattern was solving problem that didn't exist í practice (D:\\ as separate working copy added overhead without preventing any actual data loss). Verbatim-check + line-count + create_file rules retained, just applied til docs/ instead of D:\\. Surfaced 2026-05-06 Bug-24-pattern halt during STATE+DECISIONS catch-up post RLS-baseline-audit — `cp D:\\<file> docs/<file>` would have destroyed 392 lines of recent work; halt + spec-revision averted.

---

## Audit- og heiðarleika-reglur (added 2026-07-02)

Bætt við eftir sannleiks-úttekt sem fann eina nefnara-villu (92,8% vs 31,1% — hvorug var production-tala; sjá `docs/fable_prep/audit/PRIOR_SALE_COVERAGE.md` og DECISIONS 2026-07-02). Þrjár reglur til að forða transcript-confabulation og ephemeral-tapi.

### (a) NEFNARA-SKYLDA

**Engin prósenta í audit-skjali án teljara, nefnara OG nefnara-skilgreiningar í sömu línu.** „X %" eitt og sér er merkingarlaust — sama hugtakið (t.d. own-prior-sale þekja) gefur 28 %, 40 %, 58 % eða 93 % eftir því hvort nefnarinn er scored-universe, ever-sold, sold-in-window eða comp-heims-undirmengi. Ritháttur: `28,48 % = 2.538 / 8.911 (nefnari = scored universe v_current_predictions ⨝ properties)`. Ef sama stærð er mæld á fleiri en einum nefnara skal EIN skjal-heimild vera lýst „kanónísk" og hinar vísa í hana.

### (b) SCRATCHPAD-BJÖRGUN

**Prototype-kóði sem lota byggir OG keyrir afritast í `docs/fable_prep/prototypes/` áður en lotan HALT-ar.** Temp-scratchpad (`C:\Users\...\Temp\claude\<session-id>\scratchpad\`) er ephemeral — hann hverfur með session-inu og er EKKI í git. Ef tala eða niðurstaða í audit-skjali var framleidd af scratchpad-kóða, þá er sá kóði heimild um aðferðina og verður að lifa af lotuna. README-lína skal fylgja (uppruni, dagsetning, „prototype ekki production").

### (c) TÖLUR FERÐAST Á DISKI

**Spjall-lög (transcript) framleiða hönnun, ekki staðreyndir.** Hver tala sem lota notar skal vísa í disk-artifact (CSV/JSON/pkl/DB-mælingu), aldrei í transcript-samantekt fyrri lotu. Transcript telst EKKI sönnun — aðeins diskur, DB og git. Ef lota vitnar í „fyrri lota fann X" án disk-artifacts að baki, skal talan endurmælast eða flaggast sem óstaðfest.

### (d) SAMHLIÐA-LOTU COMMIT-REGLA (added 2026-07-03)

**Lotur sem skrifa í sameiginlegar continuity-skrár (STATE, DECISIONS, WORKING_PROTOCOL) committa STRAX eftir skrif með explicit paths** (`git add docs/<file>.md` → `git commit`, aldrei `git add .`). Ócommittuð doc-breyting í deildu vinnutré er á forræði HVERRAR lotu sem committar næst — hún getur sópast inn í óskylt commit og þá tapast commit-eignarhald og rekjanleiki. **Raundæmi 2026-07-03:** ócommittuð þrep-STATE-lína sópaðist inn í retrain-commit `b701903` (meinlaust í það sinn, en ekki alltaf). Reglan: skrifaðu → committaðu strax með explicit paths → haltu svo áfram. Aldrei skilja doc-skrif eftir ócommittuð milli lota í deildu vinnutré.

### (e) STUÐLASKRÁ: AÐEINS MÆLD LÍNA BREYTIST (added 2026-10-10, cc226b)

**Lína í stuðlaskrá (`verdmat-ai/data/leidretting_studlar_v1.json`) breytist aðeins ef hún hefur sjálf verið mæld. „Sami galli líklega" er tilgáta, og tilgáta breytir engri línu.** Hver stöðu- eða tölubreyting vísar í mælingu á ÞEIRRI línu: hennar þýði, hennar kveikjulind og sú spá sem notandinn sér (rekstrarhams-grunnmat). **Raundæmi 2026-10-10:** v1.2 (cc226) felldi `bilskyli_kjallara_apt` í NÚLL-MÆLT með rökunum „sami frádráttargalli og bílskúr", án mælingar á línunni sjálfri. cc226b mældi hana á rekstrarkveikjunni: grunnmatið vantar +2,94 % ± 0,17 (n = 18.756). 19.093 eignir voru vanmetnar um 2,94 % frá útgáfu v1.2 þar til v1.3 lagaði það (sama dag).

### (f) INNTAK BIRTRAR TÖLU VISTAST Á _audit ÁÐUR EN HÚN FER Í LOFTIÐ (added 2026-10-11, cc230)

**Inntaksgögn birtrar tölu (pickles, CSV, fyrirspurnir) vistast á `D:\_audit\<lota>\` ÁÐUR en talan fer í loftið — aldrei aðeins í Temp/scratchpad.** Regla (b) bjargar kóðanum; þessi regla bjargar gögnunum sem kóðinn las. Frosin mynd gagnagrunns verður ekki endurgerð síðar: grunnurinn hefur hreyfst. **Raundæmi 2026-10-11 (cc230):** inntak cc218 að skýrslu 2026-09 („13,7 % lækka innan 60 d", KM-ferlar) lá aðeins í scratchpad-pickles lotunnar `eaf03c08`. Mappan var tóm þegar mælingagalli fannst, svo talan varð hvorki endurmæld né leiðrétt. Hún var tekin úr birtingu með stöðumerki og verður endurmæld á nýjum gögnum.

### (g) LOKASKIL HEFJAST Á SKIL-LÍNUNNI (added 2026-10-11, cc233)

**Lokaskil hverrar lotu hefjast á línunni `SKIL ccNNN[-hluti] — <ein setning um stöðu>: LOKIÐ / HALT / BÍÐUR GO`. Síðan samantekt.** Ástæða: margar lotur keyra í samhliða gluggum og skil eru framsend (relay) milli þeirra; fyrsta línan verður að segja hvaða lota talar og hvort hún bíður ákvörðunar, án þess að lesa samantektina. Dæmi: `SKIL cc231 — sidast_fundin_at og rollback-lagfæring sviðsett, falspróf stenst, ekkert beitt: BÍÐUR GO`.

### (h) POOLER: `rollback()` Á UNDAN `SET TRANSACTION READ WRITE` (added 2026-10-11, cc233)

**Skrif-færsla á 6543-pooler byrjar alltaf á `conn.rollback()` (eða nýrri tengingu) á undan `SET TRANSACTION READ WRITE`.** „6543 er read-only sjálfgefið" er ekki stilling heldur **lekið session-SET**: bakendar bera `default_transaction_read_only = on` með `source = session` (`reset_val` = off), líklega frá `set_session(readonly=True, autocommit=True)` í lesskriftum, því transaction-pooler endurstillir ekki session-ástand. Ef lesfall hefur opnað óbeina færslu (`autocommit=False`, engin rollback/commit) og bakendinn er smitaður, fellur `SET TRANSACTION READ WRITE` **ákveðið** með `ActiveSqlTransaction` (`InternalError`, sem endurtengingarlykkjur á `OperationalError`/`InterfaceError` grípa ekki). Á hreinum bakenda er SET-ið no-op — þess vegna virtist villan tilfallandi. Falspróf á villunni verður að framkalla nákvæmlega skipunina sem fellur (`SET … READ ONLY` getur aldrei fallið). **Raundæmi:** `lifecycle_sweep_mbl.py` hrundi 07.10 og 09.10 (1 d töf á hringjum); `run_monthly.py` → `migration_helpers.finish_run` ber sama mynstur. Heimild: `D:\_audit\cc231_sopun\SKIL_CC231.md` (3); `D:\_audit\cc230_sidast_sed\SKIL_CC230.md` (4).

### (i) WORKTREE MEÐ `node_modules`-JUNCTION ER ALDREI FJARLÆGT MEÐ `--force` (added 2026-10-11, cc233)

**`git worktree remove --force` á Windows fylgir `node_modules`-junction (mklink /J) og tæmir skotmarkið — `node_modules` aðaltrésins.** Röðin er: fjarlægja tengilinn einan fyrst (`cmd /c rmdir <wt>\node_modules`), staðfesta að `D:\verdmat-is\verdmat-ai\node_modules` standi, **svo** `git worktree remove` án `--force`. Betra: ekkert junction — keyra tsc aðaltrésins með `--project` og byggja aldrei í worktree (Turbopack hafnar junction sem vísar út fyrir verkefnisrót hvort eð er). **Raundæmi 2026-10-10 (cc221):** `node_modules` aðaltrésins tæmdist (0 færslur) meðan aðrar lotur keyrðu á því; `npm ci` endurheimti 705 pakka. Heimild: `D:\_audit\cc221_svaedi\SKIL_CC221.md` § ATVIK — node_modules aðaltrésins tæmt.

---

## Lotu-, push- og DB-reglur (added 2026-11-02, cc306)

Samantekt reglna sem lotur cc223–cc298 settu á disk en voru ekki komnar hingað. Hver liður vísar í SKIL-skrána sem ber hann; orðalag reglu er tekið þaðan.

### (j) GO-FLOKKAR A/B OG TÍMAGLUGGAR (arkitekt 01.11.2026 23:45; gildir í framkvæmd frá þeim tíma)

Heimild: `D:\_audit\master_verklag\WORKING_PROTOCOL_drog_flokkar_AB.md` (drögin nefna `D:\WORKING_PROTOCOL.md`; kanóníska skjalið er þetta, sbr. Changelog 2026-05-06).

- **GO-beiðni:** lota HALT-ar með beiðni á mannamáli, 2–4 línur: hvað breytist, hvar það sést, hvernig er bakkað.
- **Flokkur A** — texti, merki, framendi án gagnabreytinga; bakkað með einu `git revert`. Arkitekt les SKIL af diski og gefur „GO arkitekts". Lotan ýtir sjálf, staðfestir á www og skrifar LOKIÐ. Danni getur alltaf stöðvað með „bíddu".
- **Flokkur B** — migration, eyðing, lyklar, Task Scheduler/keðja, ný notendavirkni, allt sem ekki er bakkað með einu revert. GO frá Danna. Lotan framkvæmir sjálf eftir GO; Danni keyrir aðeins sjálfur það sem krefst stjórnanda-PowerShell eða mælaborðs.
- **Master session gefur aldrei GO sjálf;** hún ber GO áfram og heldur stöðutöflu (lota, staða, hver á næsta skref).
- **Tímagluggar:** ekkert push/ff/migration 01:00–07:30 og engar þungar DB-fyrirspurnir 01:00–07:30. Push á verdmat-ai eitt í einu, í röð sem arkitekt ákveður; hver lota fetchar, endurgrunnar og keyrir próf aftur á undan (`git log HEAD..origin/main` tómt, sbr. `D:\_audit\cc293_manadarskyrsla\SKIL_CC293.md`). Aðeins eitt migration beitt í einu.
- Arkitekt les SKIL beint af diski; um möppur sjá (k).

### (k) ALDREI SKRIFA Í MÖPPU ANNARRAR LOTU (Danni 01.11.2026, cc295)

**Lota skrifar aðeins í eigin möppu `D:\_audit\ccNNN_*` og eigið vinnutré. Lestu úr möppu annarrar lotu, afritaðu í þína möppu og skrifaðu þar.** **Raundæmi 01.11 (cc295):** skrifta cc295 skrifaði yfir frumgagnaskrána `cc218_september\q11_fullnusta.json` (endurgerð úr stdout) og önnur úttaksskrá (`q10_velta.json`) lenti í cc218-möppunni. Staðfesting eftir á: `find D:\_audit -newer SKIL_ccNNN.md` sýnir aðeins eigin möppu. Heimild: `D:\_audit\cc295_manadarskyrsla_okt\SKIL_CC295.md` §6 liður 5; sami texti í (j)-drögunum, liður f.

### (l) DDL Á LIFANDI SÝN: STUTTUR LÁS, ENGIN MÆLING Í SÖMU FÆRSLU (Danni 01.11.2026, cc292)

Orðrétt úr `D:\_audit\cc292_myndir\SKIL_CC292.md` §7.0:
1. `SET LOCAL lock_timeout = '5s'` og `statement_timeout` á hverja skipun í `--prof`/`--beita`.
2. Engin þung mæling í sömu færslu og DDL á sýn sem www les. Ný skilgreining er mæld sem sér sýn með öðru nafni (t.d. `v_eign_myndir_cc292b_prof`) í lesfærslu. `--prof`/`--beita` gera aðeins CREATE OR REPLACE og punktathuganir, svo COMMIT eða ROLLBACK innan sekúndna.
3. Lástími CREATE OR REPLACE er mældur áður en beitt er.

**Raundæmi 01.11 (cc292):** `--prof` keyrði CREATE OR REPLACE VIEW á `v_eign_myndir` og síðan þungar mælingar í sömu færslu; AccessExclusiveLock hélst ~12:05–12:18 og ~12:20–12:32 og lesbeiðnir www biðu. Eftir regluna: DDL 69–102 ms, lás 197–229 ms. Grunnurinn undir þessu (eldri lotur): DDL fer um psycopg2 með `lock_timeout`/`statement_timeout`, `--prof` (ROLLBACK) á undan `--beita`, rollback-SQL skrifað fyrst — aldrei MCP `apply_migration`, sem hefur engin tímamörk (`D:\_audit\cc223_nybyggingarofi\SKIL_CC223.md`; `D:\_audit\cc251_manadarsala\SKIL_CC251.md`).

### (m) NÝR HLUTUR FÆR ENGIN anon-RÉTTINDI SJÁLFKRAFA; GRANT Í SÖMU MIGRATION (cc284, BEITT 31.10.2026)

Migration `20261031130000_cc284d_sjalfgefin_rettindi` breytti `ALTER DEFAULT PRIVILEGES` fyrir `postgres`: nýjar töflur, runur og föll í `public`/`semantic` fá ekki lengur `anon`/`authenticated`-réttindi, og PUBLIC-EXECUTE á föllum er tekið altækt. **Því gildir: hver ný tafla/sýn/fall sem www á að lesa fær GRANT sérstaklega í sinni migration.** Núverandi hlutir eru óbreyttir; áhrifin ná aðeins til nýrra hluta. Sýn sem www les og er endurgerð skal bera saman heimildir anon/authenticated/service_role fyrir og eftir (`D:\_audit\cc272_sitemap\SKIL_CC272.md`), og föll í `scraper` fá REVOKE EXECUTE því skemað er opið í PostgREST (`D:\_audit\cc276_sottkvi_tafla\SKIL_CC276.md`). Heimild: `D:\_audit\cc284_anon_rettindi\SKIL_CC284.md` §7.3 og §8; DECISIONS 2026-10-31.

### (n) FALSPRÓF NOTAR RAUNVERULEGT INNSTREYMI (arkitekt 01.11.2026 23:50, cc296 H5)

**Falspróf á mælingu sem fer eftir tíma (sölutími, endurkomur, lifun) hermir raunverulega skekkjuvaldinn — raunverulegt daglegt innstreymi, stýfingu við upphaf vöktunar — ekki jafnt innstreymi.** Prófið telst aðeins standast ef það getur fallið. **Raundæmi 01.11:** falspróf cc295 (F1/F2) gerði ráð fyrir jöfnu innstreymi; með föstum raunsölutíma (lognormal, miðgildi 60 d) og raunverulegu nýskráningarsniði endurskapaði jafngluggamælingin birta mynstrið 41/50/35/36 — „Jafngluggatalan hefur því ekkert afl, hvorki til að segja „lengist" né „lengist ekki"." Staðalfalsprófið (sölulíkur 35 %, vinstri stýfing 27.06, fræ 2952) er skilyrði: skrifta skrifar ekki hópatölu nema `falsprof.stenst = true`. Heimild: `D:\_audit\cc296_stadfesting_okt\SKIL_CC296.md` §0 (H5) og §2.4; `D:\_audit\cc295_manadarskyrsla_okt\SKIL_CC295.md` §8.2.

### (o) `unstable_cache`: HÆKKA ÚTGÁFULYKIL Í SAMA COMMITI (arkitekt 01.11.2026 23:58, cc298)

**Breytist strengur eða snið sem er búið til inni í `unstable_cache`, skal hækka útgáfulykil skyndiminnisins (t.d. `FS_CACHE_UTGAFA`, `EIGN_CACHE_UTGAFA`) í sama commiti.** Annars sýnir www gömul gögn í allt að TTL, því ný dreifing hreinsar ekki gagnaskyndiminnið. Allar lotur sem breyta framenda athuga þetta fyrir push. **Raundæmi:** cc298 (01.11) — `/fasteignasolur`-töflur sýndu gamla strenginn undir lykli `"cc286"` í ≤ 1 klst eftir push; cc258 (17.10) — `unit_category` bættist í select án hækkunar `EIGN_CACHE_UTGAFA`, og eignir opnaðar fyrir deploy fengu hæð null. Heimild: `D:\_audit\cc298_markadur\SKIL_CC298.md` § Lærdómur; `D:\_audit\cc258_krass_v2\SKIL_CC258.md`.

### (p) PUSH Á app-REPO ER EKKI LOKIÐ FYRR EN STAÐBUNDIÐ `app` main ER ff-AÐ (Danni 02.11.2026)

**„Lota sem ýtir á app-repo er ekki LOKIÐ fyrr en staðbundið app main er ff-að á origin/main og staðfest með fetch (utan 01:00–07:30), nema GO segi annað."** Staðfesting: `git -C D:\verdmat-is\app fetch` og síðan `git -C D:\verdmat-is\app status -sb` sýnir `## main...origin/main` án `[ahead …]`/`[behind …]`. **Raundæmi 02.11:** `D:\verdmat-is\app` stóð á `8f00ba9` frá kvöldi 01.11 til 08:04 02.11, svo nóttin keyrði án `a3262e7` (cc292), `a68d8f3` (cc290) og `d517bd8` (cc292b), sem voru þegar á origin/main. Það skipti ekki máli í það sinn (engin næturskrifta notar þær skrár; DDL var þegar beitt), en hefði gert það ef breytingin hefði snert keðjuna. Heimild: `D:\_audit\cc299_lifsmark\SKIL_CC299.md` §4; `D:\_audit\cc306_afrit_skraning\SKIL_CC306.md` §5.

### (q) NÆTURKEÐJAN: ff Á `app` main ER VIRKJUN (cc263, cc268, cc275, cc281)

Task Scheduler keyrir úr `D:\verdmat-is\app` (harðkóðuð slóð), svo **push eitt virkjar ekkert en ff á staðbundnum `app` main virkjar frá næstu nótt** (`D:\_audit\cc275_kedja\SKIL_CC275.md`). Ekkert ff meðan bash-keðja keyrir og engin migration meðan sópur með gömlum kóða keyrir (`D:\_audit\cc281_app_samthaetting\SKIL_CC281.md`). Tímaþak verks verður að vera stærra en biðhlið + keyrsla (`D:\_audit\cc260_naeturverk\SKIL_CC260.md`). Gagnalagsbreyting sem hreyfir lifandi tölu fer fyrst á prófunarútgáfu sem framendinn flettir yfir á í push-committinu (`D:\_audit\cc224_nybyggingar\SKIL_CC224_1.md` §11.7).

### (t) JÁ ÚR LLM ER ÁLYKTUN ÞAR TIL ÞAÐ ER MÆLT GEGN TEXTANUM; RÖÐ SKREFA ER BUNDIN VIÐ NIÐURSTÖÐU (Danni 05.11.2026, cc316)

**Reitur eða útdráttur birtist ekki sem staðreynd fyrr en hann er mældur á blindu úrtaki gegn textanum sjálfum, per eigind.** „Ekki nefnt" og 0/false úr auglýsingareit eru aldrei „nei". Já úr `listing_extractions` v0.2.2 er ályktun líkans: já án nokkurs orðstofns í hráum texta er 15,5 % á lyftu og 11,6 % á svölum (mælt á 2.588 íbúðum). **Keðja skrifa, hleðslu og push er bundin við niðurstöðu hvers skrefs**, svo fallið skref stöðvi það næsta. **Raundæmi:** cc316 áfangi 1 (04.11), push fór af stað 17 sek. áður en hleðsla tókst. Heimild: `D:\_audit\cc316_eigindi\SKIL_CC316.md`.

### (u) HART KOSTNAÐARÞAK ER BÓKHALD FYRIR HVERT KALL, EKKI SAMTALA EFTIR Á (Danni 05.11.2026, cc316c)

**Þak á líkanskostnað stendur í kóða: hámarkskostnaði kalls er haldið í skrá sem er flush-uð ÁÐUR en kallið fer, og það gert upp eftir svar. Summa skrárinnar er eina heimildin.** Hrun skilur hald eftir, svo endurræsing kemst ekki yfir þakið. Fyrri kostnaður verksins telst með. Stöðvun skilur eftir gild gögn og segir hve langt var komist. **Falspróf með gervi-API áður en keyrt er.** Raundæmi: `a2/prof_thak.py` í cc316c fann að hald á kall var lægra en versta kall. Heimild: `D:\_audit\cc316_eigindi\SKIL_CC316.md`.

### (v) RAMMI FRÁ ÞRIÐJA AÐILA: STAÐFEST MEÐ LESTRI RAMMANS, LYKILL AÐEINS VIÐ SMELL, ENDAPUNKTUR TEKUR AUÐKENNI (arkitekt 05.11.2026, cc318)

**`iframe` í DOM sannar ekki að ramminn hafi hlaðist: rammi sem CSP lokar lítur eins út. Staðfest er með því að lesa texta rammans eða taka skjámynd.** Lykill sem hlýtur að sjást í slóð rammans fer til vafrans aðeins við smell, í svari með `no-store`, og endapunkturinn tekur auðkenni (fastanúmer) en aldrei frjáls hnit, svo opinn stiki geti ekki beint sameiginlegum lykli hvert sem er. **Lyklaskönnun þarf jákvæða viðmiðun:** byggt er með merkistreng í stað lykils, HTML og JS-pakkar skannaðir, og sama skönnun á að finna strenginn í svari endapunktsins. Annars sannar 0 hittar ekkert. **Raundæmi:** cc318, þar sem villutexti Google í rammanum sýndi að ekkert lokar honum og merkistrengurinn fannst 0 sinnum í 66 static-skrám en 1 sinni í svarinu; á www birtist raunmynd og sama skönnun með raunlykli í breytu fann hann 0 sinnum í HTML og JS-pökkum. Heimild: `D:\_audit\cc318_gotumynd\SKIL_CC318.md`.
### (w) ORÐSTOFNSHLIÐ ÞARF STAÐARHEITAPRÓF; ÚRSKURÐUR KEMUR Á EFTIR BLINDRI TÖLU (Danni 05.11.2026, cc316d)

**Stofn getur hitt staðarheiti: „garð" hitti Garðabæ og bæinn Garð, svo já á garð slapp í gegnum hliðið og taldist „óljóst".** Lestu tilvikin sem falla ekki í „rétt", ekki aðeins teljarann. **Blind tala stendur fremst í töflu; úrskurður eftir á er sýndur sér.** Raundæmi: geymsla 0/148 var 1/148 blint, og Sonnet 5 2/151 var 4/151. Heimild: `D:\_audit\cc316_eigindi\SKIL_CC316.md`.

### (x) NÆTURVERK SEM HÁÐ ER KEÐJUNNI LES NÆTURLOGG DAGSINS, EKKI KLUKKUNA (Danni 05.11.2026, cc316d)

**Hliðið les síðustu CHAIN-línu í `night_YYYYMMDD.log`, dagsetta þann dag, svo gamalt CHAIN CLEAN opni ekki.** Keðja í gangi: endanleg bið sem endar fyrir 06:55. Annars sleppt með ástæðu í eigið logg, eigin rc og engin köll. Tímaþak verks er stærra en bið + keyrsla (q). Falspróf: hrein keðja, keðja með villu, vantar logg, logg gærdagsins, keðja enn í gangi (`a3/prof_kedjuhlid.py`).

### (y) SÍMAPRÓF MÆLIR Í MINNSTU STUDDU BREIDD OG BER STAK SAMAN VIÐ SPJALDIÐ SITT (arkitekt 05.11.2026, cc318)

**Mæling á láréttu skruni í einni breidd sér ekki stak sem stendur út fyrir spjaldið sitt en innan gluggans.** Símapróf keyrir í raunverulegri gluggabreidd (tækjahermir, ekki `iframe`) í minnstu studdu breidd, 375 px eða minna, og ber hvert stak líka saman við spjaldið. Nýr texti í föstu merki er prófaður með lengsta gildinu. **Raundæmi:** cc316b prófaði í iPhone 13 (390 px); merki sem endaði í 383 px gaf 0 skrun þar, þótt það stæði 13 px út fyrir spjaldið og ylli skruni í 375 px. Heimild: `D:\_audit\cc318_gotumynd\SKIL_CC318.md`.

### (z) STIG LESTURS ER SÉR MÆLING: „AÐ HLUTA" ER VIÐHALD, OG REGLA VALIN EFTIR Á ÞARF STAÐFESTINGU (Danni 06.11.2026, cc316e)

**Þegar líkan flokkar í stig skal mæla hvert stig sér áður en þau eru lögð saman í „já".** Í cc316e voru nær öll rangt já `ad_hluta` á málun eða viðhaldi. **Birtingarregla sem valin er eftir að villur sjást er tilgáta á þeim gögnum, og það er sagt í skilum með tillögu um staðfestingarúrtak.** Ártal er sér hlið á eftir já: textar telja upp mörg ár, og rangt ár er villa í birtu gildi þótt já standist. Heimild: `D:\_audit\cc316_eigindi\SKIL_CC316.md`.

### (aa) FULLYRÐING UM AÐ LÍKAN HUNSI EIGINLEIKA ÞARF VÍXLPRÓF (Danni 06.11.2026, cc313 D7)

**Áður en sagt er að líkan taki ekki tillit til eiginleika er eiginleikinn víxlaður í rekstrar-X og matið mælt. Autt feature sannar ekki að upplýsingarnar vanti, því annar eiginleiki getur borið þær.** Þetta gildir sérstaklega um texta sem notendur sjá. **Raundæmi 06.11:** `merking_floor` og þrjú önnur hæðarfeatures eru 100 % NaN í rekstri, og cc313 skrifaði því „hæð íbúða er ekki notuð í matinu". Víxl 00 → 01 í `unit_category` hækkaði mat um +3 % að miðgildi, svo fullyrðingin var röng, og hún var á leið í merki á eignasíðum. Heimild: `D:\_audit\cc313_endurthjalfun\SKIL_CC313_HAED.md` §2 og §5.

### (ab) HLIÐ Á TILVITNUN, EKKI Á ALLAN TEXTA (Danni 06.11.2026, cc319)

**Þegar líkan skilar svari með orðréttri tilvitnun skal hlið lesa tilvitnunina, ekki allan textann, áður en nýtt kall er keypt.** Í cc319 lágu kerfisbundnar villur Haiku í því hvað svarið var látið þýða: „tengi fyrir þvottavél" varð þvottahús, lagnaleið varð hleðslustöð, orðstofn einhvers staðar í texta dugði sem staðfesting. Hlið á `brot` stóðst á 34 sellum af óháðu blindu úrtaki, án eins nýs kalls. Tvö skilyrði: hliðin eru frosin á disk áður en úrtak er dregið, og afrit þeirra í kóða er borið saman við frosnu útgáfuna á öllum ramma. Skrá: `D:\_audit\cc319_eigindi\SKIL_CC319.md`.

### (ac) STAÐBUNDIÐ PRÓF ER SKILYRÐI FYRIR PUSH, ALDREI Á EFTIR (Danni 06.11.2026, eftir cc319)

**Lota sem breytir framenda keyrir staðbundið próf (bygging úr eigin vinnutré og `next start` á lausu porti) og fær hreina niðurstöðu ÁÐUR en hún ýtir á verdmat-ai. Próf á www eftir push kemur til viðbótar, ekki í staðinn.** Í skilum stendur tímastimpill beggja prófa og á hvaða þjóni hvort var keyrt, svo röðin sést. Fyrsta lotan sem þetta gildir um er næsta lota sem breytir framenda.

**Raundæmi:** cc319 ýtti `533d2a8` og prófaði á www, en staðbundna prófið var keyrt á eftir. Niðurstaðan var hrein, en það bætti engu við vörn fyrir push.

### (ad) BRÚIN TIL HLUTHAFAR OG MIGRATION ANNARRA VERKEFNA (arkitekt 07.11.2026, eftir flutning registur)

**(a)** Ekki breyta eða eyða `registur_utflutningur` eða `registur_afrit` án GO Danna. **(b)** Láta Danna vita áður en dálkum er breytt í `public.lb_auglysingar`, `public.sales_history` eða `public.property_images`, því brúin les þá. **(c)** Önnur verkefni beita aldrei migration á verdmat-grunninn. Breyting sem þau þurfa fer til verdmat-lotu, með staðbundnu prófi og GO Danna.

**(d) Lestur hluthafar (Danni 07.11.2026):** Hluthafar (D:\hluthafar) má LESA kóða í D:\verdmat-is til að endurnýta lausnir og afritar með tilvísun í uppruna (skrá + commit). Hluthafar skrifar ekkert hér, keyrir ekkert hér og gerir engar git-aðgerðir hér. Verdmat-lotur bera enga skyldu gagnvart afrituðum kóða: breytingar hér berast ekki sjálfkrafa til hluthafar. Nýjar sýnir í registur_utflutningur eru migration á verdmat-grunninn (flokkur B): aðeins eftir beiðni sem Danni áframsendir og með GO frá honum, smíðaðar af verdmat-lotu.

**Raundæmi:** hluthafar skrifaði migration á `search_properties_grouped` undir nafninu cc323, útgáfa `20261107223000`. Hún var tekin af hluthafar og sameinuð verdmat-megin.

### (ae) PÓSTUR Á BAK VIÐ ROFA FER AÐEINS UM HVÍTLISTA Á ÞJÓNI; ATBURÐUR Á EIGN MÆLIST Á FASTANÚMERI (cc320, 07.11.2026)

**Meðan rofi er af tekur þjónninn aðeins við og sendir aðeins á eina netfang eiganda úr þjónsumhverfi, aldrei NEXT_PUBLIC; annað netfang fær hlutlaust svar án raðar. Atburður sem varðar eign er mældur á fastanúmeri, aldrei auglýsingarauðkenni, því mbl gefur nýtt auðkenni við endurbirtingu.** Atburður á óstaðfestri lind er smíðaður á bak við eigið flagg og sendur hvergi fyrr en lindin er staðfest. Mælingar: `D:\_audit\cc320_voktun\SKIL_CC320.md`.

### (af) PRÓF OG PUSH ERU AÐSKILIN SKREF; PRÓFUMHVERFI SKILUR EFTIR SÍÐUSKYNDIMINNI (cc320, 07.11.2026)

**Push fer aldrei í sömu skipun og próf, heldur eftir að niðurstaða hefur verið lesin. Próf með rofa af er keyrt á hreinni byggingu (`.next` eytt): ISR-síður úr fyrri keyrslu með rofa á lifa af endurræsingu.** Raundæmi: cc320 ýtti 2d619e5 í keðju á eftir prófi með 4 föllum, sem reyndust skyndiminni úr prófþjóni; hrein bygging og www stóðust á eftir.

### (ag) DECISIONS BER AÐEINS EIGNAÐAR ÁKVARÐANIR (arkitekt 07.11.2026)

**Færsla í DECISIONS inniheldur aðeins ákvarðanir Danna eða arkitekts, hverja eignaða; greining, tölur og hönnun lotu fara í SKIL og færslan vísar þangað. Lota skrifar aldrei tilvitnun í GO sem barst frá annarri lotu sem staðreynd í varanlegt skjal.**

