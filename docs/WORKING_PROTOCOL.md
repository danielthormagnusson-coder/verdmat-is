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
