# verdmat-is continuity docs

These files document the project state, decisions, and protocols.

## Source of truth

`docs/` in this repo is the **canonical source**. `D:\` is a working copy on
Danni's Windows machine.

## Workflow

- Claude Code edits: run on `D:\`, then `cp D:\*.md docs/` and commit + push.
- Readable by chat-Claude via raw URLs (see below).
- Readable by Claude Code via `git pull`.

## Files

| File | Purpose |
|---|---|
| `STATE.md` | Current project phase, open items, next steps |
| `DECISIONS.md` | Architectural decisions with rationale |
| `WORKING_PROTOCOL.md` | How to edit these files (hard rules) |
| `TAXONOMY.md` | Canonical property type classification |
| `GLOSSARY.md` | Icelandic real estate terminology |
| `DATA_SCHEMA.md` | Data layer schemas (devalue, kaupskrá, HMS vocabs) |
| `EXTRACTION_SCHEMA_v0_2_2.md` | LLM extraction schema |
| `LABELING_GUIDE.md` | Pilot extraction labeling reference |
| `GOLD_STANDARD_PROTOCOL.md` | Quality gold-standard sampling methodology |
| `DATA_AUDIT_REPORT.md` | Data quality audit results |
| `devalue.py` | Data format utility |

## Raw URLs (for chat-Claude)

```
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/STATE.md
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/DECISIONS.md
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/WORKING_PROTOCOL.md
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/TAXONOMY.md
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/GLOSSARY.md
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/DATA_SCHEMA.md
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/LABELING_GUIDE.md
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/GOLD_STANDARD_PROTOCOL.md
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/EXTRACTION_SCHEMA_v0_2_2.md
https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/DATA_AUDIT_REPORT.md
```

## Last sync

Initial sync: 2026-04-21 (Phase 1D). Source: Claude.ai Project folder via
bundle upload. Updated Áfangi 8 status in STATE.md, added 5 decisions to
DECISIONS.md, appended sync rule to WORKING_PROTOCOL.md.
