# PLANNING_BACKLOG — Framtíðar planning-sessions

Þetta skjal er backlog af planning-prompts fyrir framtíðar verdmat-is þróun. Hver prompt triggerar planning-session sem framleiðir spec-doc. Hver spec-doc fær svo eigin implementation-session síðar. Pattern: chat chain er **planning → spec → implementation**, aldrei blandað saman.

## Notkun

Þegar þú ert tilbúinn að byrja á nýju planning-áfanga:

1. Opna nýjan Claude Code chat
2. Paste handoff-note (sjá hér að neðan) efst
3. Paste selected planning prompt
4. Claude Code les state-docs, byrjar planning-session

Hver planning-session:
- Framleiðir spec-doc í `/d/verdmat-is/app/docs/`
- Hefur 3-4 stoppunarpunkta fyrir Danni's feedback
- Skrifar engan app-kóða (bara docs)

Eftir spec er samþykkt:
- Nýr chat með implementation-prompt sem tekur spec og byggir verbatim

## Handoff-note template

Paste þetta efst í nýjum chat áður en planning prompt:

```
Ég held áfram með verdmat-is. Staða núna:

- Sprint 1 live: https://verdmat-is.vercel.app
- Sprint 2 Áfangar 1-3 kláraðir (questionnaire v1.1 live, PDF export live)
- Sprint 2 Áfangi 4 + Sprint 3 Áfangar 5a/5b eru planning-ready

Les authoritative state:
- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/STATE.md
- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/DECISIONS.md
- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/PLANNING_BACKLOG.md

Paste-a selected planning prompt hér fyrir neðan.
```

## Röð

Planning promptir skulu takast í þessari röð, ekki parallel:

1. **Sprint 2 Áfangi 4**: dashboard + markaðsyfirlit (public)
2. **Sprint 3 Áfangi 5a**: pro foundation (auth, profile, saved valuations)
3. **Sprint 3 Áfangi 5b**: pro tooling (manual override, attributed PDF, audit log)

Áfangi 5a krefur að Áfangi 4 sé a.m.k. í framkvæmd. Áfangi 5b krefur að Áfangi 5a sé lokinn.

---

# Prompt 1 — Sprint 2 Áfangi 4 planning

## Dashboard + markaðsyfirlit (public)

Þetta er **planning session, ekki implementation**. Deliverable er skjal `/d/verdmat-is/app/docs/DASHBOARD_SPEC_v1.md` sem Áfangi 4 build tekur við. Engin kóði, enginn deploy, enginn commit á app/. Aðeins docs.

### Context

Áfangar 1-3 í Sprint 2 eru lokaðir: per-eign verðmat með conformal PI (79% coverage), public questionnaire með live scoring (v1.1 effects), PDF export. Sprint 1 live á Vercel með autocomplete search, kort, comps, sölusaga, og þriggja-boxa ATS card á eign-síðu.

Áfangi 4 byggir public-facing markaðsgreiningar-mælaborð — ekki per-eign view, heldur landswide og segmented market analytics. Þetta er content-marketing tool fyrir SEO og social sharing, og það er sú síða sem pro-user invites (Áfangi 5) benda á sem proof-of-value.

Data infrastructure er þegar til. Repeat-sale index (Áfangi 6) er 2.673 rows × 27 cells í Supabase. ATS lookup tables (Áfangi 7, dual-table arkitektúr) eru komnar. Monthly orchestrator refresh-ar þetta. LLM extraction output (37.544 unique) er unused fyrir aggregate insights. Scrape-gap frá 2025-07 þarf að flagga í UI.

### Les fyrst

- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/STATE.md
- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/DECISIONS.md (sérstaklega Áfangar 6 og 7 closures)
- `git -C /d/verdmat-is/app pull origin main`
- `psql $VM_DB_URL -c "\dt"` til að staðfesta hvaða tables eru í Supabase

### Deliverable sections

Eitt skjal `/d/verdmat-is/app/docs/DASHBOARD_SPEC_v1.md` með sections:

**Section 1 — Dashboard navigation og information architecture**

Dashboard er accessible á `/markadur` frá main nav. Hierarkía:
- Landing view (`/markadur`): 3-5 prime metrics, SEO-optimized copy
- Drill-down views: `/markadur/visitala` (repeat-sale), `/markadur/markadsstada` (ATS regime), `/markadur/tilbod` (TOM), `/markadur/ibudir` (LLM-derived aggregates), `/markadur/modelstada` (model tracking)

Decision-point 🔶: hvaða sub-routes ganga live í v1 vs deferred til v1.1?

Output: tree-structure diagram af routes + per-route one-paragraph purpose statement.

**Section 2 — Landing view detail spec**

Wireframe fyrir `/markadur`. Ákvarða:
1. Hero metric (A/B/C candidates): 12-mán real price change, current market regime, above-list rate
2. Secondary metrics row (3-4 cards)
3. Compact timeline chart: top-level real index for main residential, 2006-nútíð
4. CTA til drill-downs
5. Scrape-gap disclaimer banner

Output: wireframe + fyrir hverja metric: data source, refresh cadence, fallback ef tafla er tóm.

**Section 3 — Repeat-sale explorer (`/markadur/visitala`)**

Meta-question: hvernig sýnum við 27 cells án að user drukkni?

Baseline: 3×3 grid af plots fyrir main residential cells. Real index á y-axis. Hover-tooltips. Optional: segment toggle, real/nominal toggle, crash-zoom detail view.

Publishable findings frá Áfangi 6 (Country catch-up, ROW_HOUSE niche, SUMMERHOUSE missed crash) verða annotated callouts.

Output: layout mockup + data source + annotation coordinates.

**Section 4 — Markaðsstaða (`/markadur/markadsstada`)**

Regime-timeline slider. 12-24 mán (eða custom range) slider. Below: heat-map grid segment × region annotated með regime pill reflecting state **at selected month**. Linked timeline chart sýnir above-list rate og median ATS.

Design-decision 🔶: scrape-gap period handling — yellow overlay, disable slider, ignore með caveat?

Output: interaction flow + scrape-gap decision + performance consideration.

**Section 5 — LLM-derived aggregates (`/markadur/ibudir`)**

Sex aggregate metrics derive-aðar úr training_data_v2:
1. Ástandsvísitala (mean interior_condition_score per ársfjórðung × segment)
2. Endurnýjunartíðni (% replaced_new síðustu 5 ár)
3. Óskráð rými rate
4. Sérlóð í APT
5. Orðatíðni ("þarfnast framkvæmda" vs "tilbúið til flutnings" vs "einstakt tækifæri")
6. Agent framing distribution (listing_elaboration per ársfjórðung)

Output: per-metric data source (pandas group-by á training_data_v2), rendering component, editorial story.

**Section 6 — Model tracking (`/markadur/modelstada`)**

Trust-building síða:
1. Held-set MAPE trend síðustu 6 mán
2. PI coverage trend (cov80 og cov95)
3. Per-segment MAPE breakdown tafla
4. Monthly refresh status
5. Transparent methodology link

Output: data-source per panel (sumt þarf nýja `model_tracking_history` tafla).

**Section 7 — Data pipeline additions**

Nýjar Supabase tables/views:
- `model_tracking_history`: append-only, populated mánaðarlega
- `llm_aggregates_quarterly`: pre-computed ársfjórðungslegar aggregations
- `last_listing_text`: sölulýsing-in-sölusaga feature (Danni's request)

Output: SQL CREATE statements + per-table build-script signature.

### Decision points (🔶)

1. Hvaða sub-routes ganga live í v1 vs deferred?
2. Hero metric val (A/B/C)
3. Scrape-gap handling á regime slider
4. Repeat-sale explorer scope (3×3 main-only vs full 27 cells)
5. Domain/URL decision (verdmat.is stafsett?)
6. SEO keyword focus

### Constraints

- Engar nýjar data-dependencies (byggir eingöngu á existing pipeline)
- Mobile-first
- SEO-ready (structured metadata per route)
- Performance budget: Supabase edge query < 200 ms per view

### Deliverable checklist

Sjá deliverable list í sections 1-7 hér að ofan. Plus:
- Decision points list (🔶)
- Build order (recommended sequence með rationale)
- Estimated implementation time per section
- Dependencies chart

### Workflow

1. Read context files
2. Draft Sections 1-2 — nav og landing. Stop, paste til Danni
3. Draft Sections 3-5 — content-heavy views. Stop, paste
4. Draft Sections 6-7 — infrastructure. Stop, paste
5. Assembly, lint, commit til docs/, push

### Scope control

Claude Code skal EKKI:
- Skrifa React components eða API routes
- Modify app/-folder
- Touch production deploy
- Byggja nýjar Supabase tables
- Byrja á build fyrir nokkurt element

Claude Code skal:
- Lesa existing kóða til að skilja hvaða tables eru til
- Teikna wireframes í ASCII/Markdown
- Paste spec drafts fyrir review
- Commit spec til docs/ þegar samþykkt
- Sync til GitHub origin/main

Byrja á lestri og Section 1-2 draft.

---

# Prompt 2 — Sprint 3 Áfangi 5a planning

## Pro foundation (auth, profile, saved valuations)

Þetta er **planning session, ekki implementation**. Deliverable er `/d/verdmat-is/app/docs/PRO_FOUNDATION_SPEC_v1.md`. Engin kóði, enginn deploy.

### Context

Sprint 2 er lokinn (questionnaire + PDF + public dashboard live). Auth UI var byggt í Sprint 2 Áfangi 1 en frozen. Sprint 3 virkjar auth og byggir pro-tier infrastructure fyrir 2 invite-only pro-users (fasteignasali + bankamaður).

Áfangi 5a fókuserar á **foundation**: auth activation, pro user profile, saved valuations workspace, autosave. Áfangi 5b byggir ofan á með tooling.

### Les fyrst

- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/STATE.md
- https://raw.githubusercontent.com/danielthormagnusson-coder/verdmat-is/main/docs/DECISIONS.md
- `/d/verdmat-is/app/docs/DASHBOARD_SPEC_v1.md` (Áfangi 4)
- `psql $VM_DB_URL -c "\dt"`
- Existing auth components í `/d/verdmat-is/app/app/(auth)/` og `/d/verdmat-is/app/lib/`

### Deliverable sections

`/d/verdmat-is/app/docs/PRO_FOUNDATION_SPEC_v1.md`:

**Section 1 — Auth activation**

- Hvaða components skal unblocka?
- Supabase Auth provider (email/password v1, OAuth v2?)
- Invite-only flow
- Password requirements á íslensku
- Session management
- Logout edge cases

**Section 2 — Pro user profile**

Supabase `pro_users` tafla:
```sql
CREATE TABLE pro_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name text NOT NULL,
  is_licensed_agent boolean DEFAULT false,
  license_number text,
  brokerage_name text,
  brokerage_is_custom boolean DEFAULT false,
  phone text,
  logo_url text,
  email text NOT NULL,
  role text NOT NULL CHECK (role IN ('agent', 'banker', 'admin')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

Onboarding wizard (5 screens): nafn+email, licensed?, brokerage, logo/sími, review.

Decision-point 🔶: license verification auto vs self-declared.

**Section 3 — Saved valuations workspace**

`saved_valuations` tafla:
```sql
CREATE TABLE saved_valuations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  pro_user_id uuid REFERENCES pro_users(id) ON DELETE CASCADE,
  fastnum bigint NOT NULL,
  status text NOT NULL CHECK (status IN ('draft', 'finalized', 'archived')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  finalized_at timestamptz,
  questionnaire_answers jsonb,
  expert_questionnaire_answers jsonb,
  manual_adjustments jsonb,
  final_valuation_isk bigint,
  signed_pdf_url text,
  pdf_hash text,
  notes text
);
```

`/minar-verdmat` route: table view med filters (status, date, search), row actions (opna, duplicate, archive, download PDF), pagination 50/síða.

**Section 4 — Autosave infrastructure**

- Triggers: screen-transition, adjustment edit, notes edit
- Debounce 2 sek
- Visual indicator
- Error states með exponential backoff
- Resume on reload með valuation_id URL param
- Conflict resolution: last-write-wins með warning

Decision-point 🔶: valuation_id UUID í URL vs hidden í session.

**Section 5 — Draft → Finalized state machine**

- Draft → Finalized: snapshot, PDF gen, hash, upload to Supabase Storage, read-only
- Finalized → Draft: "Un-finalize" með confirmation og audit trail
- Draft/Finalized → Archived: soft-delete
- Archived → Draft: unarchive

Hash-integrity: sha256 af (answers + adjustments + valuation + user_id + timestamp).

**Section 6 — Duplicate detection**

Pro-user opnar `/eign/[fastnum]/stilla` með existing saved valuations á fastnum: banner "Þú hefur [N] áður saved verðmatsvinnur. [Skoða síðasta draft] [Búa til nýtt]".

**Section 7 — Row-level security og pro-only gating**

Supabase RLS policies:
```sql
CREATE POLICY pro_users_select ON pro_users FOR SELECT USING (user_id = auth.uid());
CREATE POLICY saved_valuations_all ON saved_valuations
  USING (pro_user_id IN (SELECT id FROM pro_users WHERE user_id = auth.uid()));
```

UI gating matrix: `/minar-verdmat` pro-only, `/eign/[fastnum]/stilla` public en autosave gated, nav shows "Mín verðmat" aðeins fyrir pro.

**Section 8 — Invite-only signup flow**

Options:
- A: Supabase magic link invite (minimal work)
- B: Custom admin UI með allow-list
- C: Waitlist með manual approval

Recommendation: A í v1, B í v2.

### Decision points (🔶)

1. License verification: self vs auto
2. OAuth: email-only v1 eða Google/Apple strax
3. valuation_id URL: UUID vs hidden
4. Invite flow: A/B/C
5. Autosave conflict: last-write-wins vs realtime lock
6. Session length: 7/30/never

### Constraints

- Supabase free-tier limits (auth 50K, Storage 1 GB, DB 500 MB)
- Mobile-first (`/minar-verdmat` á síma)
- Performance: `/minar-verdmat` < 2 sek fyrir 200 valuations
- RLS mandatory
- Engin pro tooling kóði í 5a

### Deliverable checklist

Sjá í sections + decision points + build order + time estimates + dependencies.

### Workflow

Sama pattern: 4 stoppunarpunktar, assembly, commit, push.

### Scope control

Sama og Áfangi 4: engin kóði, aðeins spec.

Byrja á lestri og Section 1-2 draft.

---

# Prompt 3 — Sprint 3 Áfangi 5b planning

## Pro tooling (manual override, attributed PDF, audit log)

Þetta er **planning session, ekki implementation**. Deliverable er `/d/verdmat-is/app/docs/PRO_TOOLING_SPEC_v1.md`.

### Context

Áfangi 5a lokinn. Auth er active, pro_users + saved_valuations eru í Supabase, onboarding wizard virkar, `/minar-verdmat` live með autosave. Pro-users geta logged in og búið til drafts, en drafts eru bara public-questionnaire adjustments á þessu stigi.

Áfangi 5b bætir við value-add tooling sem aðgreinir pro-tier frá public.

### Les fyrst

- STATE, DECISIONS
- `/d/verdmat-is/app/docs/PRO_FOUNDATION_SPEC_v1.md` (5a completed)
- `git -C /d/verdmat-is/app pull origin main`

### Deliverable sections

`/d/verdmat-is/app/docs/PRO_TOOLING_SPEC_v1.md`:

**Section 1 — Expert questionnaire (sérfræðingsstillingar)**

Pro-only questions:
- Óskráðir fermetrar: m² + type (kjallari/háaloft/geymsluskúr/viðbygging/annað) + leyfisstaða (samþykkt/ósamþykkt/óvíst)
- Lot size premium
- Location micro-adjustment (freetext + slider ±5%)
- Recent offer (upphæð + dags)
- Market timing (vor/sumar)
- Condition detail (pro-level nuanced)

Decision-point 🔶: hardcoded effects v1 eða PDP strax.

`pro_q_effects.json` separate frá `manual_q_effects.json`.

**Section 2 — Manual line-item adjustments**

Table-based UI í pro flow. Rows:
- Ástæða (freetext)
- Upphæð (+/- króna)
- Sýna á PDF (checkbox)

Validation:
- Ástæða ekki tóm
- Upphæð ≠ 0
- Total |sum| manual + questionnaire ≤ 50% baseline

Warning >25%: "Eru þessir þættir raunverulega svo áhrifamiklir?" med override-flag.

`saved_valuations.manual_adjustments` jsonb array.

**Section 3 — Attributed PDF**

Extension á Áfangi 3 PDF:
- Header með fasteignasölu logo (ef til)
- Title: "Verðmat — [heimilisfang]"
- Sub-title: "Útgefið af [full_name], [brokerage_name]" + "Löggiltur fasteignasali" badge
- Nýjar sections: Sérfræðingsstillingar, Handvirkar leiðréttingar, Niðurstaða eftir leiðréttingar
- Signature block: nafn, dags, license_number, brokerage
- Legal disclaimer: "verdmat.is ábyrgist algorithmic component; handvirkar leiðréttingar á ábyrgð útgefanda"

**Section 4 — Audit log**

```sql
CREATE TABLE pro_valuation_audit (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  valuation_id uuid REFERENCES saved_valuations(id) ON DELETE CASCADE,
  pro_user_id uuid REFERENCES pro_users(id) ON DELETE SET NULL,
  action text NOT NULL,
  action_detail jsonb,
  created_at timestamptz DEFAULT now(),
  ip_address inet,
  user_agent text
);
```

Actions: draft_created, draft_updated, adjustment_added/removed/modified, override_confirmed, finalized (med hash), un_finalized, archived, pdf_downloaded, profile_updated.

Admin view: `/admin/audit` fyrir Danni (role='admin').

**Section 5 — Pro pricing og upgrade flow**

Decisions:
- Paid vs invite-only free v1?
- Stripe integration?
- Single flat rate vs usage-based?

Recommendation: v1 invite-free, v1.1 symbolisk pricing 5K/mán, v2 self-serve Stripe.

**Section 6 — Onboarding og support**

v1: Danni direct contact. v2: help docs. v3: Intercom.

**Section 7 — Sharing + collaboration (v2 preview)**

Placeholder: share draft, brokerage aggregate, bulk operations.

### Decision points (🔶)

1. Expert effects: hardcoded vs PDP
2. Manual cap: 50% eða annað
3. Override reasons: freetext vs enum
4. Pricing: free vs paid v1
5. Support: direct vs form
6. Onboarding: overlay vs video

### Constraints

- Byggir á 5a infrastructure
- PDF extends Áfangi 3
- Mobile-compatible
- Audit log launch-critical
- Engin scope-creep í 5a

### Deliverable checklist

Sjá sections + decision points + build order + time + dependencies.

### Workflow

Sama: planning-only, 3-4 stoppunarpunktar, assembly, commit.

### Scope control

Sama og 5a: engin kóði.

Byrja á lestri og Section 1-2 draft.

---

## Framtíðar backlog (án planning prompts enn)

Þessi atriði eru í backlog en þurfa ekki planning prompt enn:

- **Sprint 3+ retraining**: iter5 með fersku gögnum, PDP refresh á öllum hardcoded effects, live-updating model
- **Áfangi 0 scraper replacement**: nýr scraper fyrir fastinn.is með monitoring (leysir scrape gap)
- **Markaðsyfirlit v2**: scraper-dependent metrics (months of supply, withdrawal rate, TOM með fullri coverage)
- **Image extraction**: 7M property photos LLM-greindar fyrir condition verification
- **Atvinnuhúsnæði segment**: separate model fyrir non-residential
- **Sumarhús segment**: land-value features fyrir SUMMERHOUSE (núverandi 175% MAPE)

Þessir þurfa sér planning-session þegar tíminn kemur.
