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
2. **Sprint 3 Áfangi 0 (scraper upgrade)**: comprehensive properties scraper — top-priority (Bug 4 follow-up)
3. **Sprint 3 Áfangi 5a**: pro foundation (auth, profile, saved valuations)
4. **Sprint 3 Áfangi 5b**: pro tooling (manual override, attributed PDF, audit log)

Áfangi 5a krefur að Áfangi 4 sé a.m.k. í framkvæmd. Áfangi 5b krefur að Áfangi 5a sé lokinn. Áfangi 0 scraper er independent af 5a/5b og má run parallel eftir að Fasi E launch polish fyrir Áfangi 4 er lokið.

---

## Sprint 3 Áfangi 4.8 — Eldri-stock calibration analysis (v1.1, estimated 1 day, post-launch competitive review)

**Why**: Egilsgata 10 spot-check 2026-04-27 shows iter4 standalone prediction = 84,8 M kr, samkeppnisaðili (verdmat.is competitor) shows 91,25 M kr — a **7 % gap on the same property**. Hypothesis: the competitor either (a) uses HMS fasteignamat as a feature (which iter4 was deliberately decoupled from per Áfangi 2-5 DECISIONS), and/or (b) over-prices old-stock cells with an implicit renovation assumption that our LLM-extracted condition score already controls for.

**What**:
- Cross-validate iter4 predictions against the competitor on **50-100 properties in postnr 101 RVK with byggar < 1950**
- Decompose the gap per-feature: fasteignamat dropping (Áfangi 2-5), segment × postnr × byggar cell sample size, calibration drift, condition signal contribution
- **Decision**: re-introduce fasteignamat as a feature in iter5 with explicit guardrails (e.g. clipped at trailing 12-mo HMS values, weighted ≤ 0.2 of final), OR keep standalone and frame the 7 % undershoot as a credibility strength ("we don't blindly track HMS — when HMS overshoots, we hold")

**Inputs needed**:
- Competitor predictions for the test set (manual collection via competitor's public site, ~1 hour)
- iter4 predictions table (already in Supabase)
- HMS fasteignamat per fastnum (already in `properties.fasteignamat`)

**Outputs**:
- `audit_4_competitor_comparison.py` — runs the decomposition, writes a markdown report
- DECISIONS entry locking the iter5-or-not choice
- If fasteignamat re-introduced: iter5 spec doc

**Marketing implication**: either way, this answers the inevitable "why is your number different from the other site?" question with data. Strong for credibility on launch.

---

## Sprint 3 Áfangi 4.7 — Nýbyggingar as a separate segment (v1.1, estimated 1-2 days)

**Why**: Bug 8 fix (2026-04-27) excluded new builds from /ibudir metrics 1 & 2 because they distorted both. But nýbyggingar are a real ~9 % of LLM-extracted listings (1,570 of 17,449) and deserve their own analytics layer — they trade differently, they price differently, they carry different risk.

**What**:
- Add canonical codes `NEWBUILD_APT_FLOOR`, `NEWBUILD_APT_STANDARD`, `NEWBUILD_SFH`, `NEWBUILD_ROW` (or simpler binary partition: `*_NEWBUILD` suffix)
- Re-train iter4 (or iter5 if Áfangi 4.8 decides on fasteignamat re-introduce) with new segment codes
- Add a "Nýbyggingar" row to `/markadur/markadsstada` regime grid
- Add a "Nýbyggingar" line to the /ibudir charts (now 4-line, comparing vs Íbúð / Einbýli / Raðhús)
- Update `/markadur/visitala` 4×3 grid to allow swapping a row to NEWBUILD_*

**Risk**: per-segment sample sizes will be ~9 % of the existing segments — Reykjavík NEWBUILD_APT_FLOOR ≈ 800 listings 2018+, sufficient for quarterly aggregates but thin for fine-grained ATS heat.

**Planning prompt**: write after Áfangi 4.8 completes (depends on whether iter5 train happens).

---

## Sprint 3 Áfangi 4.9 — Matsvæði-level polygon shapefile (v1.1, depends on HMS API access)

**Why**: /ibudir Sérlóðir bar chart (Metric 4) is currently a region × segment grid. A matsvæði-level polygon map would surface intra-region variation (matsvaedi 22 Háaleiti vs 47 Vesturbær within RVK 101-105) which the bar chart pools away. Same data is also relevant for Áfangi 4.5 price map dashboard (€/m²).

**What**:
- HMS internal shapefile for matsvæði borders — request via formal HMS API access. Public LMÍ release does not include matsvæði (they're an HMS taxation construct).
- Convert to GeoJSON (TopoJSON for size if >5 MB)
- Re-render Sérlóðir as polygon choropleth on the map; keep bar chart as alternate view
- Reuse for /markadur/kort price map (Áfangi 4.5)

**Blockers**: HMS API access. Mismeta-hraði: low; this is the longest-tail item in the v1.1 set.

**Until matsvæði available**: Áfangi 4.5 + /ibudir map use postnr-level proxy from LMÍ (which itself awaits manual download at present — see Áfangi 4.5 polygon-upgrade note).

---

## Sprint 3 Áfangi 4.11 — Time-anchor methodology section (v1.1, estimated 2-4 hours)

**Why**: Surfaced 2026-04-28 during Bug 17 cleanup. The eign-page waterfall (`AttributionWaterfall.js`) has a footer reconciliation row labeled "Markaðsstaða" that pools `sale_year + sale_month + predicted_at` SHAP impacts. Reason: those three are pure time anchors (when the valuation was priced), not property attributes — surfacing them per-row would mislead a reader into thinking "your property loses 1,2 M kr because of sale_month". Pooling into a single "Markaðsstaða" row keeps the math reconciling without that misleading per-row attribution.

The tooltip currently says "Þessi leiðrétting endurspeglar markaðsaðstæður á þeim tíma sem verðmatið var gert, ekki eigninni sjálfri." — correct as far as it goes, but there is **no user-facing methodology page that explains this mechanism in depth**. `/markadur/modelstada` has an "Aðferðafræði markaðsstöðu" section but that explains the **regime classification** for the `/markadur/markadsstada` dashboard (quarterly p33/p67 vs monthly z₃v₁₂), which is an adjacent-but-distinct mechanism that happens to share the word "Markaðsstaða".

**What**: pick a home and write the methodology section.

Options for the home:
- (a) Add a "Tímalegri leiðrétting" subsection on `/um` (general-audience methodology page) — most user-friendly; keeps the topic together with "Verðbólguleiðrétting" which is the closest existing concept
- (b) Add a second methodology card on `/markadur/modelstada` titled "Aðferðafræði tímaaðlögunar" alongside the existing regime card — keeps both Markaðsstaða-named mechanisms on one page so the namespace collision is at least co-located
- (c) Build a dedicated `/markadur/adferdafraedi` route that consolidates ALL methodology (regime, time-anchor, conformal PI, segment definitions, fasteignamat exclusion) — most thorough; planning-session deliverable

**Recommendation for planning**: option (a) is the cheapest correct answer. Time-anchor reconciliation is a **per-eign** mechanism, so the explanation belongs on the page users actually visit when they have one specific verðmat in front of them, not on a market-wide dashboard. /um is already linked from the eign page footer.

**Once shipped**: re-link the eign-waterfall tooltip from the conservative single-sentence form (Bug 17 fix, 2026-04-28) back to a two-sentence form with `[Sjá aðferðafræði](/um#timaaðlogun)`.

**Planning prompt**: not needed — small enough to spec inline in a Sprint 3 mini-PR if option (a) is chosen.

---

## Sprint 3 Bug 22 — DRY refactor of cpi_factor lookup (v1.1, estimated 30 min)

**Why**: Surfaced 2026-04-29 during Bug 15 root-fix. The `cpi_by_ym` lookup block (load `training_data_v2.pkl` → group by year/month → first → dict + `latest_factor`) is now duplicated between `build_comps` (`build_precompute.py:642-657`) and `build_sales_history` (`build_precompute.py:749-768`). Both produce the same dict from the same source, but if either diverges it'd silently re-introduce a Bug-15-class scale mismatch.

**What**: factor into a shared helper:
```python
def _load_cpi_by_ym(data_dir: Path) -> tuple[dict, float]:
    """Return ((year, month) → cpi_factor, latest_factor) from training_data_v2.pkl.
    Canonical source — never use kaupverD_VISITALA_NEYSLUVERDS."""
    td = pd.read_pickle(data_dir / "training_data_v2.pkl")
    td["_yr"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.year
    td["_mn"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.month
    cpi_by_ym = td.groupby(["_yr", "_mn"])["cpi_factor"].first().to_dict()
    latest = cpi_by_ym[max(cpi_by_ym.keys())]
    return cpi_by_ym, latest
```
Both call sites become one line each. Total diff: −18 lines + helper.

**Risk**: zero — pure refactor, both call sites already pass through the same data. Sanity check: invariant from Bug 15 (`comps_index.last_sale_price_real == sales_history.kaupverd_real`) must still hold post-refactor.

**Planning prompt**: not needed — small enough to spec inline.

---

## Sprint 3 Bug 23 — precompute/ outside git source control (v1.1 reproducibility cleanup, 2026-04-29)

**Why**: `D:\verdmat-is\precompute\` is not under git source control — only `app/` is tracked in the verdmat-is repo. Bug 15 root-fix in `build_precompute.py:642-648` lives on Danni's filesystem, not in any commit. Risk: redeploy, machine swap, or disaster recovery loses the CPI fix and the bug repríserast at the next orchestrator cycle.

**Three fix-paths (cheapest to cleanest)**:

(a) **Document precompute/ as manual filesystem state** in STATE.md plus copy-instructions in a redeploy runbook. Cheapest, fragilest. Works only as long as Danni's machine survives.

(b) **Move `precompute/` into the `app/` tree** (e.g., `app/scripts/precompute/`), update orchestrator paths. Mid-effort — requires path adjustments in `refresh_dashboard_tables.py` and possibly other callers (`load_dashboard_v1.py`, any cron entrypoints, any CI). Side effect: bundles 200+ MB of intermediate pickles unless `.gitignore`'d carefully.

(c) **`git init precompute/`** as a separate repo, push to `danielthormagnusson-coder/verdmat-is-precompute` or similar remote. Cleanest — establishes audit trail for all future precompute changes (CPI fixes, schema migrations, build-script tweaks). Aligns with Áfangi 0 scraper architecture decision (same principle: pipeline scripts deserve git history).

**Recommendation**: (c). 3-min upfront cost, eliminates ongoing reproducibility risk.

**Blocker on future precompute work**: ANY future `build_precompute.py` changes (Bug 22 DRY refactor, schema additions, CPI source updates, new precompute tables) must wait until this is addressed — otherwise they get lost on redeploy.

**Flagged 2026-04-29 during Bug 15 root-fix completion.** Not launch blocker — production already mitigated via direct UPDATE; running CSV is correct.

---

## Sprint 3 Áfangi 0.x — Pre-load invariant assertion harness (defensive infrastructure, Sprint 3+)

**Why**: Bug 15 root-fix had a Step 4 invariant check (build CSV vs Supabase `sales_history.kaupverd_real`, sample 100 rows, abort load if any mismatch > 1 kr tolerance). The pattern is generalizable and should run on every pre-load step in `refresh_dashboard_tables.py` to catch data corruption before it reaches production.

**Generic helper signature**:
```python
def assert_load_invariant(
    csv_path: Path,
    db_query: str,
    join_keys: list[str],
    compare_columns: dict[str, str],   # csv_col -> db_col mapping
    tolerance: float = 1.0,
    sample_size: int = 100,
) -> None:
    """Sample N rows from CSV, fetch DB rows on join_keys, abort load if any
    row deviates beyond tolerance. Logs first 5 mismatches before raising."""
```

**Use cases to harness**:
- `comps_index.last_sale_price_real` == `sales_history.kaupverd_real` — Bug 15 invariant, eternal
- `predictions.real_pred_mean` matches latest `model.predict()` from training_data_v2 features
- `repeat_sale_index` pairs match `pairs_v1.pkl` post-filter cascade
- `ats_lookup_by_heat` thresholds match `ats_heat_thresholds` reference table

Each use case is a separate invariant call in `refresh_dashboard_tables.py`. Failure aborts the orchestrator and surfaces a clear error: *"INVARIANT FAILED: comps_index.last_sale_price_real diverges from sales_history.kaupverd_real on N/100 sample rows. Investigation required before proceeding."*

**Implementation effort**: 1-2 days. Helper itself is ~50 lines. Per-invariant config registration is ~10 lines per check.

**Value**: catches data corruption pre-production, before user sees nonsense prices on `/eign`. Bug 15 was discovered by Danni post-deploy; this harness would have caught it pre-deploy.

**Depends on Bug 23**: precompute/ should be under git source control before adding this kind of safety infrastructure to it — otherwise the harness itself isn't reproducible.

**Flagged 2026-04-29 during Bug 15 root-fix completion.** Sprint 3+ infrastructure pass.

---

## Sprint 3 Bug 19 — broken /um#adferdafraedi anchor (v1.1, estimated 30 min)

**Why**: Surfaced 2026-04-28 during Bug 17 investigation. `app/markadur/modelstada/page.js:260-265` renders a footer link `<Link href="/um#adferdafraedi">Aðferðafræði →</Link>`. The `/um` page (`app/um/page.js`, 93 lines) has no element with `id="adferdafraedi"` — the anchor is dead. Clicking the link lands the user on `/um` but doesn't scroll to any methodology section because none is anchor-tagged.

**What**: pick one:
- (a) Add `id="adferdafraedi"` to the appropriate `<h2>` on /um (likely the "Módelið" heading) so the existing link works.
- (b) Change the link target on `modelstada/page.js:260-265` to `/um` (no anchor) so it just navigates to the page top.

**Recommendation**: (a) if a methodology subsection is added on /um per Áfangi 4.11 — anchor it `#adferdafraedi` and the modelstada link works automatically. (b) if Áfangi 4.11 is deferred — drop the dead anchor in the meantime.

**Single commit**: `fix(modelstada): /um#adferdafraedi anchor — either add target or drop anchor` (resolved depending on chosen branch).

---

## Sprint 3 Áfangi 4.10 — Commercial-address empty-state UX (v1.1, estimated 2-4 hours)

**Why**: Verified 2026-04-28 via Akralind 1-8 spot-check. The street is fully classified `is_residential = FALSE` (Iðnaður / Skrifstofa / Vörugeymsla / Vélaverkstæði / Verslun / Þvottahús) — same with neighbouring Askalind í Lindahverfi Kópavogi. `search_properties_grouped()` correctly filters these out (`WHERE is_residential = TRUE`) because the iter4 model is residential-only and a verðmat flow can't complete. But the user-facing copy is generic ("Engin eign fannst — eignin er kannski ekki í gagnasafninu okkar enn"), which mis-frames the situation: the address IS in the DB, it's just out-of-scope for this product.

**What**: when autocomplete returns zero residential matches, run a fallback query that includes `is_residential = FALSE`. If the fallback finds rows, render explicit copy:
> "Þessi eign er skráð sem atvinnuhúsnæði (iðnaður / skrifstofa / verslun). Verdmat reiknar aðeins verðmat fyrir íbúðarhúsnæði — atvinnuhúsnæði er ekki í scope ennþá."

If the fallback also returns zero, keep the existing HMS-gap copy. So the empty-state has three tiers: (a) residential match → results, (b) commercial-only match → out-of-scope copy, (c) no match at all → HMS-gap copy.

**Implementation**:
- Add `search_properties_grouped_commercial(term)` RPC (mirror of existing function with the `is_residential` predicate flipped) — keep separate so the fast path stays fast and the fallback only fires on empty
- `/api/search` route: if main result is `[]` and `q.length >= 3`, fire the commercial RPC; tag the response shape `{ kind: "commercial", results: [...] }` so the client knows to render the explanatory empty-state instead of the generic one
- `SearchAutocomplete.js`: render the new empty-state variant when the response is `kind: "commercial"`. Keep the same Skoða aðferðafræði → link

**Risk**: low. Function-clone migration is reversible. Edge route fallback adds at most ~50ms on the cold-path (only fires when the main RPC returned 0 rows, which is the path that's already showing an empty state).

**Planning prompt**: not needed — small enough to spec inline in a Sprint 3 mini-PR.

---

## Sprint 3 Áfangi 4.6 — New-build share tracker (v1.1, estimated half-day, post-Bug-7 follow-up)

**Where**: 7th metric on `/markadur/ibudir` (next to Endurnýjunartíðni so the two read in tandem — high new-build share explains why renovation rate dips even when absolute renovations rise; surfaced during Bug 7 fix discussion 2026-04-27).

**What**: Share of arm's-length sales per ársfjórðung × region where the property is flagged as new-build.

**Implementation**:
- Source: `pairs_v1.pkl` filtered to arm's-length paired sales
- Dedup on `fastnum` (count each fastnum once per quarter to avoid double-counting flips)
- `new_build_pct = N(is_new_build=true) / N(total)` per (ársfjórðung × region_tier)
- Output: new Supabase table `new_build_share_quarterly` (ár, ársfjórðungur, region_tier, n_new, n_total, pct_new) — fits the existing monthly orchestrator pattern
- Render: stacked area or 3-line chart (Höfuðborg / Suðurnes / Landsbyggð) OR aggregate single line, decided at planning
- Editorial framing: byggingariðnaðar pipeline indicator, peaks í 2022-2024

**Why useful**: explains the renovation-rate dilution Bug 7 surfaced. Also marketing-relevant standalone metric — building permits and new-build absorption is reported regularly by Hagstofa but never visualised at this granularity for the public.

**Planning prompt**: written by Danni after Sprint 2 launch.

---

## Sprint 3 Áfangi 4.5 — Price map dashboard (v1.1, estimated 1-2 days)

**Route**: new `/markadur/kort` in the `/markadur/*` family.

**What**: €/m² choropleth heatmap for höfuðborgarsvæðið. For each postnr on SV-landi:
- Run iter4 prediction for a 100 m² APT_STANDARD with average byggingarár for that postnr
- Divide by 100 → €/m² anchor value
- Render as a color-graded choropleth polygon per postnr

**Interactions**: slider controls for `einflm` (floor area), `byggar` (building year), and `canonical_code` (APT_STANDARD / SFH_DETACHED / ROW_HOUSE). Re-render triggers a batch prediction for all postnr at the selected preset and re-paints the map.

**Data**:
- `predictions.predict_for_hypothetical` RPC or Edge Function that takes (postnr, einflm, byggar, canonical_code) and returns `real_pred_mean`. Wraps the iter4 scoring pipeline so we don't reimplement feature engineering in JS.
- postnr geometry — reuse the same GeoJSON source we pick for Addendum 1 (Fasi E).

**Caveats**:
- Cold-start cost: 30+ postnr × one prediction each on slider move = meaningful latency unless we cache. Options: (a) precompute a grid of (postnr × size × byggingarår × seg) and store in a `price_map_precompute` table, (b) do server-side batch on-demand with short cache.
- Privacy / misuse: €/m² published at postnr granularity is less sensitive than address-level, but worth a DECISIONS note before ship.

**Planning prompt**: to be written by Danni after Sprint 2 launch (post-Fasi-E polish). Spec-doc should cover data-path choice (precompute vs on-demand), interaction budget, caveat copy, and integration with `/markadur` drill-down CTAs.

**Timing**: v1.1, not blocking. Independent of Áfangi 0 scraper and Áfangar 5a/5b. Most valuable marketing asset after the core dashboard ships.

---

## Sprint 3 Áfangi 0 — Scraper upgrade (top-priority per Bug 4 + Akralind verification, 2026-04-22 / 2026-04-28)

**Why**: Bug 4 smoke-test leiddi í ljós að HMS Fasteignaskrá er ekki nægjanlega comprehensive source fyrir public search coverage. Sævargarðar 7 á Seltjarnarnesi (landnum 117661 vantar upstream), plus nýbyggingar sem hafa ekki fengið endanlegt fastnum úthlutað, plus eignir sem seldust pre-HMS-digital-era og aldrei síðan — allar þessar eignir skila "engin niðurstaða" á verdmat.is leit.

**Akralind staðfesting (2026-04-28)**: Akralind 1-8 í Lindahverfi Kópavogi staðfestu að HMS coverage gap er pattern, ekki isolated incident. Akralind / Askalind eru fully classified sem `is_residential = FALSE` (Iðnaður / Skrifstofa / Verslun / Vörugeymsla) — sem er rétt taxonomy-wise, en surfacar sömu UX failure: real address sem user man → "engin niðurstaða" empty-state. v1.1 commercial empty-state copy (Áfangi 4.10) leysir messaging-ið, en breikkar coverage-grunninn aðeins ef supplementary scraper bring-ar listings sem HMS fasteignaskrá vantar (nýbyggingar sem hafa engin fastnum, residential conversions sem eru ekki re-classified, etc.).

Launch strategy Leið B ships dashboard með transparent HMS-gap caveat (`SearchDataGapBanner` + empty-state copy), en caveat-ið er aðeins stop-gap: Sprint 3 Áfangi 0 verður að catch-a up með comprehensive scraper sem complements HMS með live listings-source data (líkast evalue.is eða fasteignir.is).

**Deliverables (fyrir planning-session að fleshe-a út)**:
- Source selection: evalue.is vs fasteignir.is vs blanda
- Scraper arkitektúr: incremental (nightly) vs full (weekly)
- Storage: new `properties_supplement` tafla eða merge inn í existing `properties`?
- Dedup logic: match á (heimilisfang, postnr) eða fuzzy match á adress?
- UI integration: search RPC needs to include supplemented rows; `/eign/[fastnum]` must render gracefully fyrir supplement-only properties (engin HMS fasteignamat, engin iter4 prediction — show "verðmat ekki tiltækt ennþá" state)
- Orchestrator integration: passa inn í monthly refresh pipeline alongside refresh_kaupskra + refresh_cpi

**Planning prompt**: Danni skrifar eftir Fasi E launch polish á Áfanga 4.

**Timing**: Parallel með Áfanga 5a/5b, ekki blocked af þeim.

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
