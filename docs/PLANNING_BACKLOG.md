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

## Áfangi 4.x — iter5 spec re-frame (logged 2026-05-18, decision pending)

**Context**: Eftir Áfangi 0 Stage 1 weekend run höfum við nýja HMS dálka (brunabotamat,
lhlmat, fasteignamat_naesta_ar, matseiningar[].byggingarstig/gerd/matsstig, landeign_nr)
sem voru ekki accessible þegar iter4 spec var lokað 2026-04-21.

**Open question**: Iter4-spec ákvað að fjarlægja FASTEIGNAMAT vegna circularity og
accepta 3-5 pp MAPE cost. Nokkrar af nýju HMS dálkum eru non-circular og gætu
recoverað hluta af þeim MAPE cost án að undo iter4-rationale.

**Non-circular subset (safe að adda)**: brunabotamat (top-level + per-matseining),
byggingarstig (B0-B4 factual stage marker), gerd, texti, matsstig, landeign-density features.

**Circular subset (cannot adda)**: lhlmat, fasteignamat_naesta_ar, matseiningar[].fasteignamat
— allir derived úr fasteignamatinu og myndu fá sama instability vandamál.

**Gut-check lift potential (empirically validated empirical pending)**:
- brunabotamat: 1,5-2,5 pp MAPE recovery (non-circular size anchor)
- byggingarstig: 0,5-1,5 pp lift, mest í nýbyggingum (5.909 properties B1/B2/B3 á 30K nýjum)
- gerd/texti finer taxonomy: 0,2-0,5 pp
- Samanlagt: 2,2-4,5 pp potential recovery vs iter4-spec baseline

**Three decision scenarios (pending iter5 training)**:
- Scenario A: iter5 = iter4 + non-circular subset, additive lift, iter4-rationale stenst
- Scenario B: iter5 nær iter3v2-level performance með stability — iter4-decision upphafið,
  iter3v2 retired
- Scenario C: lift er marginal (0,5-1,5 pp), iter4-spec stenst as designed

**Empirical inputs needed before C-decision**:
- Train iter5 með non-circular subset, mæla held MAPE per segment
- Probe brunabotamat stability: hvernig hreyfist brunabotamat per fastnum yfir 3 árlegar
  HMS-updates? Ef stable, Scenario B er possible. Ef volatile, Scenario A/C.

**Update 2026-05-18 (eftir að sjá live iter4 metrics á /markadur/modelstada)**:
iter4 held MAPE er 8,2% í apríl 2026, ekki 11-13% sem projected var.
iter4_conformal_v1 calibration appears doing substantially more work en segment-
stretch alternative sem var spá'd. Per-segment matchar iter3v2 nánast exactly
(Íbúð 6,4% vs 6,3%, Íbúð á hæð 8,6% vs 8,3%, Einbýli 16,3% vs 16,2%, Raðhús
7,2% vs 7,5%).

Þetta **reduces urgency** of iter5 strategic re-frame:
- Non-circular HMS feature addition er nú incremental improvement question
  (myndi iter5 nail 7,5% eða betur?), ekki strategic recovery (sem var
  forsendan að iter4 væri 3-5 pp undir target).
- Scenario B (iter4-decision endurmat með full iter5 substitute) er ennþá
  á borðinu en miklu minni urgency.
- Scenario A (additive lift) er primary motivation.

**Caveat**: 8,2% er single-month tala (apríl 2026 eingöngu, sjá Líkansstaða
page chart sem hefur eingöngu einn data-point). 12-mánaða rolling average
verður tiltækt þegar monthly snapshot cycle hefur fyllt 2026Q3-Q4. Decision-
point fyrir iter5 vinnu bíður þess data eða Phase D Supabase sync, hvort
sem kemur fyrr.

**Status**: Pending Phase D Supabase sync (training data inniheldur ekki nýju HMS dálka
ennþá). Ef Phase D er done og train_iteration5.py er priority, þá er þetta næsta
modelling-pickup.

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

## Sprint 3 Áfangi 4.12 — Comparable Properties + Compare Tool (v1.1, estimated 1 week)

**Why**: Núverandi sambærilegar-section á `/eign/[fastnum]` er placeholder — þrjár cards, 6 comps post Bug 14 partial fix (raised frá 6 til 10 — sjá "12-20 target dependencies" section neðar). Real Comparable Properties + Compare Tool spec replaces þetta með richer two-tier layout og side-by-side compare page. Tracked sem Bug 14 fyrir 12-20 comps target, plus expansion til pro-tier UX.

### Á /eign/[fastnum] síðu

**Tier 1 — Primary comparables** (top of section):
- 6 eignir með photo thumbnail + key specs (heimilisfang, m², byggar, predicted/sold price)
- Visual card layout, scannable
- Highest-similarity matches (canonical_code + postnr + price ±15% + byggar ±10yr)

**Tier 2 — Extended list** (below primary):
- 14-20 fleiri eignir í dense tafla
- Columns: heimilisfang, m², byggar, sold/predicted, m² verð, distance score
- Hver row hefur checkbox til vinstri
- Sortable columns

**Compare button**:
- "Bera saman" button efst á extended list
- Disabled þar til 2+ checkboxes valdar (max 4)
- Click → `/eign/[fastnum]/bera-saman?ids=[fastnum1,fastnum2,...]`

**Compare page**:
- Vertical columns per eign side-by-side
- Photo carousel per eign efst
- Key specs hlið við hlið (heimilisfang, tegund, m², byggar, herbergi, fasteignamat, predicted+PI, söluverð+dags, m² verð)
- Highlight differences (anchor neutral, comps tinted)
- Map view með öllum sjást á sama korti
- URL shareable via `?ids=` param
- Mobile: stack vertically, swipeable carousel

**Plus**: Á location map á `/eign/[fastnum]`, bæta secondary markers fyrir top 6 comparables í öðrum lit (terracotta eða sage). Hover sýnir comp address + price differential. Click navigerar til `/eign/[comp_fastnum]`. Toggle "Sýna sambærilegar á korti".

### Bug 14 (12-20 comps target) dependencies — added 2026-04-29

Bug 14 quick-win partial fix shipped 2026-04-29 (commit hash to be filled): raised display limit frá 6 til 10. 67% bump með zero architectural cost. Real 12-20 target er hluti af þessari Áfangi 4.12 redesign vegna fjögurra blocking dependencies:

1. **Precompute widening** — `build_precompute.py` currently writes top-10 nearest comps per residential. 12-20 target krefst widening til top-20 (eða configurable N). 5-10 line change í precompute, en blocks á Bug 23 (precompute er ekki git tracked).

2. **DB size budget** — `comps_index` í dag er ~128 MB (1.1M rows × 10 comps × 11 cols). Top-20 doubles til ~256 MB. Supabase project sits at 424/500 MB free tier; doubling pushes total ~552 MB → yfir cap. Two paths: (a) paid tier (Supabase Pro $25/mán, 8GB DB), eða (b) eviction strategy (drop low-distance comps post-rank-10 fyrir bottom 90% af fastnums sem hafa good top-10 fit, keep top-20 only fyrir hard-to-match cases).

3. **Pagination UI** — current `CompsGrid.js` notar `gridTemplateColumns: "repeat(3, 1fr)"` án dynamic row cap. 12 comps render-ar 4×3 grid, 20 comps render-ar ~7×3 (uneven). Áfangi 4.12 spec already calls for Tier 1 (6 photo cards) + Tier 2 (14 dense table rows) — sem natural splittar 20 comps í primary/extended layout.

4. **Mobile grid responsiveness** — pre-existing concern á `CompsGrid.js` (`repeat(3, 1fr)` án media query er cramped jafnvel á 6 cards á smáum símum). Becomes worse með limit 10 (already shipped). Must be addressed sem hluti af Áfangi 4.12 redesign — Tier 1 fer í swipeable carousel (existing spec mention), Tier 2 fer í horizontally scrollable table eða responsive 1-col stack mobile / multi-col desktop.

### Spec planning

Medium-sized áfangi, 1-2 daga planning + 2-3 daga implementation = ~1 week total. Place í Sprint 3 forgangur, eftir Áfangi 0 scraper og 5a/5b foundation.

**Planning prompt**: Danni skrifar þegar Áfangi 5a/5b are settled.

---

## Sprint 3 Áfangi 4.13 — Market-scan view: active listings vs verðmat (v1.1, estimated 2-3 days post-Áfangi-0)

**Why** (frá Danni's vision 2026-04-29): Þú vilt geta opnað sér glugga sem er með öllum virkum auglýsingum og þar til hliðar er verðmat okkar og ásett verð. Tvíþætt notkun:

1. **Internal calibration** — checka okkar verðmat af móti real market asking prices á live listings. Sjáu hvort iter4 systematically over/under-shootar per genre, region, price band.

2. **Public "best buy" / overpriced discovery** — sýna almenningi hvaða listings eru fyrir neðan okkar verðmat (best buys) og hvaða eru langt fyrir ofan (overpriced). Marketing-angle: viral content, drives launch traffic, generates trust.

**Hard dependencies**:
- **Áfangi 0 scraper (track A — active listings)** — must produce active listings feed með asking_price, list_date, source link. Without scraper, no live data.
- **Per-listing iter4 scoring batch** — `score_new_listing.py` path verður að run á hverri active listing nightly. Currently scoring runs on-demand fyrir `/eign/[fastnum]`; here we need batch run á hundrum-til-þúsundum active listings per cycle.

**Spec elements (fyrir planning session)**:

- Route: `/markadur/auglysingar` (eða svipað navigeranlegt)
- View: tafla með columns (heimilisfang, postnr, m², byggar, asking_price, verdmat_mean, verdmat_PI80, diff_pct, list_date, link til source listing)
- Default sort: diff_pct ascending (largest negative gap first = best buy at top)
- Filter controls: region, segment, price range, byggar range, diff_pct threshold (only show > X% gap í annaðhvort átt)
- Refresh cadence: nightly batch aligned með scraper output
- Row click: navigate til `/eign/[fastnum]` fyrir deep-dive ef fastnum er HMS-known. Ef fastnum vantar (supplement-only property), link til source listing instead

**Open design questions (require Danni decision í planning session)**:

1. **Public eða pro-only?** Public feature gives marketing value en raises stakes (mis-classification = reputational risk + agent friction). Pro-only gives same internal calibration value en loses public marketing angle. Hybrid: public sees top-10 sample, pro sees full filterable list?

2. **Framing language** — "best buy" vs "best value" vs "below verðmat". "Overpriced" vs "above verðmat" vs neutral "diff vs verðmat". Tone affects legal exposure og agent relations. Iceland market is small — agents will recognize their own listings flagged as overpriced.

3. **Confidence threshold** — should low-PI predictions (wide 80% spread) be hidden? Showing "this er overpriced 30%" when our 80% PI er ±25% er misleading. Possible rule: hide listings þar sem `|diff_pct| < width_PI80_pct`.

4. **Scope phasing** — only Höfuðborgarsvæðið first (where HMS coverage er strongest), or all Iceland? Only APT_FLOOR/APT_STANDARD initially (where iter4 MAPE er lowest at 6-8%), or all residential including SFH (16% MAPE — looser confidence)?

**Marketing implication**: this is potentially the strongest viral feature on the site. Once shipped, it becomes the natural anchor for social media content ("this week's best buys í 101", "5 most overpriced flats í Garðabær"). Worth careful design before public launch — design errors here are higher-stakes than typical UI work.

**Planning prompt**: skrifa parallel við Áfangi 0 planning session, since they share data dependencies. Output: `MARKET_SCAN_SPEC_v1.md`.

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

**RESOLVED 2026-04-29** — `precompute/` initialized as separate git repo, pushed to `github.com/danielthormagnusson-coder/verdmat-is-precompute` (initial commit `c85ad83`). Bug 15 root-fix in `build_precompute.py:642-657` now version-controlled.

---

## Sprint 3 Bug 24 — WORKING_PROTOCOL improvement: verbatim-check phrase fetching (v1.1, estimated 30 min)

**Why**: Surfaced 2026-04-29 during STATE.md sync. Verbatim-check rule í WORKING_PROTOCOL prescriberar að logga distinctive phrases sem proof-of-version áður en str_replace edits. En current pattern hefur Claude (eða strategic chat draftar) often spec-a þessar phrases frá memory eða stale spec, ekki frá actual file fetch. Result: verification check fails með false positive þegar phrase var aldrei í file — like `'Áfangi 7 rollfixture í production'` sem var assumed-but-never-actual í STATE.md sync 2026-04-29.

**Fix**: Update `WORKING_PROTOCOL.md` verbatim-check section til að explicitly require:

1. Distinctive phrases fyrir verification MUST be fetched verbatim frá file í pre-edit state (via `grep` + `view` eða svipað)
2. Phrases tekið úr memory eða previous spec drafts má ekki nota sem checks
3. Ef Claude er ekki able til að fetch live file content, halt og bíða eftir upload

Implementation: 5-10 line addition til `WORKING_PROTOCOL.md` hard rule section. Plus example í examples section.

**Pattern lærdómur**: trust canonical over memory. Same lesson sem caught á 2026-04-29 með handoff text drift gegn STATE.md, og með numbering drift milli `BUGS_AND_FEATURES_QUEUE` og `PLANNING_BACKLOG`.

---

## Sprint 3 Bug 25 — Postgres 15+ view security_invoker discipline (Áfangi 0 dependency, 2026-05-06)

**Why**: Surfaced 2026-05-06 during RLS baseline audit. By default, views in Postgres 15+ run with the privileges of the view owner (typically `postgres` superuser), which means a view CAN bypass RLS on underlying tables if not configured with `security_invoker = true`. This is NOT a current security hole — the post-2026-05-06 RLS categorization has zero service-role-only tables, so no view can leak rows that anon doesn't already have access to via underlying `public_read` policies. **It becomes critical the moment Áfangi 0 ships `rejected_commercial_listings` as a service-role-only table.** Any view that joins service-role-only data must declare `security_invoker = true` or it will leak rows to anon callers via the view-as-bypass channel.

**Fix**: Add to Áfangi 0 implementation checklist (Step 4 schema migrations per `SCRAPER_SPEC_v1.md` §8.2). Every CREATE VIEW that touches `rejected_commercial_listings` or any future service-role-only table must include `WITH (security_invoker = true)`. Audit pre-merge that no view in the new migration omits this clause. Existing 4 public views (latest_regime_per_cell, regime_per_cell_monthly, repeat_sale_index_by_segment, repeat_sale_index_main_pooled) do not need backporting because their underlying tables are all dashboard-public — the security_invoker flag is a no-op when the underlying RLS already permits anon SELECT.

**Risk if missed**: silent data leak. A view joining `rejected_commercial_listings` would expose its rows to any anon caller, defeating the service-role-only categorization. Sentry would not catch this — it is a permissioning behavior, not an exception.

**Flagged 2026-05-06 during RLS baseline audit Checkpoint 3 close-out.** Tracked as Áfangi 0 dependency, not standalone bug.

---

## Sprint 3 Bug 26 — `augl_id` back-link column exposure (v1.1 hardening, 2026-05-06)

**Why**: Surfaced 2026-05-06 during RLS baseline audit Checkpoint 1 column inventory of `last_listing_text`. The `augl_id` column on `last_listing_text` and `augl_id_latest` on `properties` are per-source listing identifiers from mbl.is and fasteignir.visir.is. Exposing them to anon via the public read path enables third-party scrapers to back-link our data to source platforms — a brittleness we should not introduce (third-party tooling tracking our listings could fingerprint our scrape cadence and trigger source-side anti-bot measures aimed at the apparent back-linker, which is us). This is the same concern that drove `SCRAPER_SPEC_v1.md` §3.3 to REVOKE `listing_id` from `active_listings_public` view.

**Status**: NOT a current alert. The exposure has been the status quo since Sprint 1 launch. The 2026-05-06 RLS audit did NOT address column-level exposure (alert was about RLS-disabled, not column visibility). `last_listing_text` is correctly tagged dashboard-public per Danni's decision 2026-05-06 because the broader concern is filed here for separate handling.

**Fix (post-Áfangi-0)**: Introduce column-stripping public views and refactor frontend reads:

1. `CREATE VIEW last_listing_text_public AS SELECT fastnum, sale_rank, thinglyst_dagur, lysing_plain, scraped_at FROM last_listing_text;` (drop `augl_id`)
2. `CREATE VIEW properties_public AS SELECT <all properties columns except augl_id_latest> FROM properties;` (column-stripping)
3. Refactor frontend reads (`lib/dashboard-queries.js`, `app/eign/[fastnum]/page.js`, search RPC) to use views instead of underlying tables. The conditional render at `app/eign/[fastnum]/page.js:204` (`{property.augl_id_latest && property.list_price_latest ? ...}`) needs special handling — replace `augl_id_latest` truthy check with a derived boolean column in the view (e.g., `has_listing` computed as `augl_id_latest IS NOT NULL`).
4. `REVOKE SELECT ON last_listing_text, properties FROM anon, authenticated; GRANT SELECT ON last_listing_text_public, properties_public TO anon, authenticated;`
5. Both new views must declare `WITH (security_invoker = true)` per Bug 25.

**Effort**: ~4-6 hours including frontend refactor + view creation + verification suite + smoke test on dashboard pages. Single migration commit.

**Why post-Áfangi-0**: Áfangi 0 implementation will introduce its own column-stripping pattern (`active_listings_public` view per `SCRAPER_SPEC_v1.md` §3.3). Better to ship that pattern first, validate it works, then backport to existing tables in a single follow-up rather than backport-now and re-touch when Áfangi 0 ships its own variant.

**Flagged 2026-05-06 during RLS baseline audit Checkpoint 1 column inventory.** Estimated v1.1 hardening, post-Áfangi-0 implementation.

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

## Sprint 3 Áfangi 0.y — SCRAPER_SPEC v1.1 amendments (post-empirical-probe revisions, 2026-05-07)

**Why**: SCRAPER_SPEC v1 (committed `4d1652e`, 2026-05-06) was drafted before any of the candidate sources had been empirically probed. A 2026-05-07 backfill pre-flight session ran live HTTP probes against `evalue.is`, `fastinn.is`, `fasteignir.is`, `fasteignir.visir.is`, and `hms.is`. Three findings invalidate or substantially revise sections of v1 and need to land as v1.1 amendments before the next Áfangi 0 pre-implementation review.

**Amendment 1 — §7.3 HMS dialogue ladder needs major revision.** v1 framed the §7.3 ladder as *Tier 1 formal API → Tier 2 bulk-export → Tier 3 technical scrape (worst case) → Tier 4 e-value.is fallback*. The ladder assumed HMS had a working public API that we could fall back to scraping if formal access stalled. Empirical probe on 2026-05-07 found that the documented public API at `https://hms.is/api/fasteignaskra/{fastnum}` was **retired during HMS's recent rebuild** (Next.js + Vercel + Prismic stack now serves the site; the API path returns HTTP 404 via the Next.js wildcard `[...uid]` catch-all route, and the search endpoint at `/api/fasteignaskra/leit` sits behind Vercel Security Checkpoint anti-bot). All 5 known-good fastnums probed (including `2000042` from the README's reference example) returned 404 HTML, not the expected JSON. Tier 3 is therefore not "fall back to the same API at conservative throttle" — it is "re-discover a new API surface on the rebuilt site, defeat anti-bot, and operate against an explicit security control". Materially harder than v1 assumed, materially more aggressive ethically. v1.1 needs to update §7.3 with the new posture: Tier 3 is now a substantial discovery + ethics-decision project, not a gentle technical fallback. The pre-flight evidence is captured in `audit/backfill_preflight_report.md`.

**Amendment 2 — §1 Track B fallback ladder (e-value.is) is now the practical short-term path, not theoretical.** v1 listed e-value.is as a Tier 4 fallback to be reached only if Tiers 1-3 all stalled. With Tier 3 now blocked by the HMS rebuild, e-value.is becomes the actual Stage 1 backfill source for the registry-completion goal — backed empirically by Danni's existing 124,835 rows scraped from there over the past year. v1.1 should reorder the ladder: e-value.is moves up from "last resort" to "current primary", with the explicit acknowledgement that this comes with the e-value.is `robots.txt: Disallow: /` ethical posture (which Danni has been operating across successfully but which the spec should surface as a known tradeoff, not paper over). The HMS dialogue email (drafted 2026-05-07, `audit/hms_dialogue_draft.md`) becomes the long-term path back to a clean ladder.

**Amendment 3 — Existing scrape templates in `D:\Vinnugögn\` should be referenced in spec for future Claude sessions.** v1 was drafted under the assumption that no existing scrape pattern was available in the codebase, and the §8.2 build order accordingly allocated effort for greenfield scraper development. That assumption was wrong: Danni has working evalue.is scraper templates in `D:\Vinnugögn\Annað\Scrape - skjöl - skipanir\Scrape - stora\` (5 variants: forward, middle, reverse, reverse2, gap-fill — all sharing identical scraping core, differing only in fastnum-enumeration strategy), an HMS direct API scraper template in `D:\Vinnugögn\Scrape\Fasteignanúmer\` (now functionally obsolete due to Amendment 1, but useful as reference for re-discovery work), and a commercial real-estate active-listings scraper in `D:\Leiguskra - scrape\Gagnasafn\scrape_atvinnuhusnaedi.ps1` (PowerShell-based reference architecture for Track A active-listings — Phase 1 search → Phase 2 detail → Phase 3 mark-withdrawn → Phase 4 export, exactly the shape SCRAPER_SPEC §2 Track A specifies). v1.1 should add an "Existing implementation references" subsection somewhere prominent (likely §8 Build order intro) listing these template paths so future Claude sessions don't re-do the discovery work on every visit.

**Amendment 4 — Image-ownership policy (image archive at `D:\Gagnapakkar\images\`).** v1 of SCRAPER_SPEC inherits the legacy scraper pattern of recording CloudFront URLs (`d1u57vh96em4i1.cloudfront.net/...`) into the `myndir` SQLite table and downloading the JPGs to `myndir/{fastnum}/N.jpg`. This works tactically but leaves us structurally dependent on a CDN we don't control: if evalue.is migrates off CloudFront, rotates the bucket, or simply bit-rots the URLs, every recorded URL becomes a 404 and the property pages lose imagery silently. **All scrapers — the backfill batch, the recurring cron job, and the future Track A active-listings production pipeline — must download images to a long-term-owned archive at `D:\Gagnapakkar\images\` in addition to the structured-JSON capture.** The archive is the source of truth; the CloudFront URLs are a transient acquisition channel only. Storage convention (per-fastnum subdir vs. content-addressable hash, JPG vs. WebP, dedupe strategy) and refresh policy (re-download on listing change vs. once-and-immutable, retention horizon, repair-mode for broken URLs) will be **locked in the next planning session** post-three-probe-report and pre-image-download-build, using empirical data from the positive-control test in `audit/backfill_pilot.db` (5 known-good fastnums whose `augl_json` will surface the actual image-URL count and structure to drive sizing decisions). v1.1 should add an "Image-ownership policy" subsection in §3 (data model) and a corresponding §8 build-order task that gates "scraper goes to production" on "image archive write path is in place + tested for at least one full property's worth of imagery". Scope note: this is a v1.1 addition, not a retroactive policy — the existing 124,835 rows scraped via the legacy variants used `myndir/{fastnum}/` and that local archive remains the historical record; new policy applies to all scrapes from amendment-merge forward.

**Effort**: ~1-2 hour spec rewrite. Single-commit str_replace edits on `app/docs/SCRAPER_SPEC_v1.md` (rename to v1.1 in header metadata + Amendments-list per §9.4 hook + main-body str_replaces on §1, §3, §7.3, §8 intro). Plus corresponding STATE.md / DECISIONS.md sync entries for the amendment.

**Timing**: not blocking Stage 1 backfill pilot — the pilot proceeds against e-value.is per `audit/backfill_pilot_plan.md` regardless of whether v1.1 spec amendments have shipped. Spec amendment is documentation hygiene, not gating implementation.

**Flagged 2026-05-07 during Áfangi 0 Stage 1 backfill pre-flight + template discovery.**

---

## Sprint 3 Áfangi 0.z — Phase D Supabase sync planning (post 2026-05-18 Stage 1 weekend run)

**Why**: Áfangi 0 Stage 1 weekend run (2026-05-08 → 2026-05-18) completed two coordinated autonomous scrapes that produced ~31K new + 124,738 enriched + 97 ghost rows in local staging databases. Phase D is the controlled sync of that staging data into Supabase `properties` and downstream tables. Three independent decisions are pending; each affects the schema migration path, the prediction-pipeline rebuild surface, and the model retraining cadence. Plan in a fresh strategic chat session with full state-doc context.

**Scope**:

1. **Schema decision** — new `hms_data` table (1:1 with `properties.fastnum` + denormalised `matseiningar` child table) vs widen `properties` in place with new columns (`lhlmat`, `brunabotamat`, `fasteignamat_naesta_ar`, `byggingarstig`, `gerd`, `matsstig`, `skodags`, `landeign_nr`, plus JSON column for `matseiningar[]`). Trade-off: separate table is cleaner for HMS-refresh re-runs that should not touch prediction columns; widening is simpler for downstream queries but couples HMS-refresh cadence to the prediction pipeline. Recommendation working hypothesis: separate `hms_data` table + view that joins to `properties` for the dashboard. Locks in planning session.

2. **30,193 new property insertion path** — these fastnums are real-HMS-known but currently absent from `properties`. Two paths:
   - **Path A (graduated)**: insert into `hms_only_properties` staging table first, exclude from prediction/dashboard scope, graduate to `properties` only after coordinate enrichment (`Stadfangaskra.csv` join), matsvaedi assignment, region_tier classification, canonical_code derivation, is_residential flag. Low blast-radius, lets us audit each cohort.
   - **Path B (single-shot)**: full pipeline build → bulk insert into `properties`. Faster end-state, higher risk if any classification rule mis-fires on the new cohort (mostly countryside, jörð, fjárhús, fishing rights — categories our pipeline has not been tuned for).
   - Recommendation working hypothesis: Path A. Locks in planning session.

3. **97 ghost handling** — Supabase fastnums that HMS no longer recognises (returned HTTP 500 in Phase B). Options:
   - **Soft-flag**: `deregistered=true` + `deregistered_detected_at` columns, retain row, exclude from default queries.
   - **Soft-delete**: move to `properties_archive` table.
   - **Hard-delete**: remove + cascade through `sales_history`, `predictions`, `feature_attributions`.
   - Implications: each ghost row has linked rows in `sales_history` (sometimes), `predictions`, `comps_index`, `feature_attributions`, `repeat_sale_pairs`. Hard-delete cascades risk data-history loss; soft-flag is reversible. Recommendation working hypothesis: soft-flag. Locks in planning session.

**Deliverables (planning session output)**:
- `docs/PHASE_D_SPEC.md` covering schema migration, new-property pipeline, ghost handling, rollback plan, and prediction-pipeline impact assessment.
- Migration SQL drafts (`supabase/migrations/2026MMDD_phase_d_*.sql`).
- Test plan: spot-check 10 new properties + 10 ghosts + 10 enriched properties post-migration to verify schema and feature flow.
- Update of `STATE.md` Áfangi 0 section from ~95% to 100% post-Phase-D-execution.

**Out-of-scope for the planning session**:
- Model retraining using the new HMS features (lhlmat, brunabotamat, matseiningar) — that's a separate Áfangi (likely 4.14 or new Áfangi 5 sub-step).
- Image bootstrap re-run for the 58 failed URLs from Phase 3 — small enough to handle as a one-off cleanup.

**Carried items not addressed by Phase D** (preserved for completeness):
- SCRAPER_SPEC v1.1 amendments (Áfangi 0.y) — still pending.
- Schema variant unit tests — still pending.
- Pre-load invariant assertion harness (Áfangi 0.x) — still pending.
- Stage B image-fetch observability gap (workers emitted no log lines during the orchestrator Phase 3 fetch; real-time progress had to be queried directly from `image_index.db`) — log this as Áfangi 0.aa or fold into Phase D if convenient.

**Effort estimate**: 2-3h planning session producing `PHASE_D_SPEC.md`. Implementation 1-2 days for the schema migrations + pipeline integration + ghost handling + verification.

**Flagged 2026-05-18 at the close of the Áfangi 0 Stage 1 weekend run handoff commit.**

---

## Sprint 3 Bug 16 — FROZEN pending photo backfill (v1.1, frozen 2026-04-29)

**Symptom**: `/eign/2008691` (Leifsgata 9, postnr 101 RVK) sýnir engar myndir í photo gallery þrátt fyrir 50-photo backfill (Bug 11 fix). Aðrar properties á sama svæði rendera 50+ thumbnails correctly. Diagnostic this session showed scope is class-wide: ~8,578 residential properties (8.1%) have `augl_id_latest` set but `n_photos = 0` and `photo_urls_json IS NULL`.

**Status**: FROZEN. Diagnostic + fix work paused 2026-04-29 að beiðni Danni — hann er að græja síðasta pakka af myndum sem vantar locally, og rerunning Bug 16 diagnostic núna myndi hugsanlega clash-a við þann photo backfill work eða gefa stale niðurstöður.

**Unfreeze trigger** (updated 2026-04-29): Danni er working á local photo backfill í parallel við Sprint 3 Áfangi 0 planning. Expected timeline ~1 week. Status check áður en Áfangi 0 implementation phase byrjar — ef backfill er done, run diagnostic queries og resolve. Ef enn í gangi, halda Bug 16 frozen og adjust Áfangi 0 dependencies accordingly. Not blocking other Sprint 3 work.

**Possible post-unfreeze outcomes (frá this session's diagnostic)**:

1. **Photos appear post-backfill** → Bug 16 resolves sjálfkrafa, marka closed.
2. **Photos still missing** → narrow hypothesis space (B legitimate empty source, eða C augl_id mapping bug), proceed með targeted fix.
3. **Different fastnums missing photos than before** → broader pattern á filter scope, hypothesis A.

**Kept í queue**: já. Ekki dropped sem bug, bara frozen með clear unfreeze condition. Status check expected innan 1-2 vikna.

**Three working hypotheses (frá pre-frost diagnostic)**:
- (A) Bug 11 backfill scope filter cut — rejected (NULL not clipped array; backfill operated on already-populated arrays).
- (B) Legitimate empty source — partially possible but doesn't scale to 8.1%.
- (C) Photo-extraction pipeline (`build_precompute.py:_load_photos_map()`) misses a class — strongest fit. To confirm, probe local `D:\fasteignir_merged.db` SQLite for `augl_id 1320064` (Leifsgata 9 listing) post-unfreeze. If photos exist locally → join bug; if not → upstream scraper bug (Áfangi 0).

**Original symptom snapshot for posterity (frá BUGS_AND_FEATURES_QUEUE pre-frost)**:
- `/eign/2008691` sýnir engar myndir þrátt fyrir 50-photo backfill (Bug 11 fix)
- Aðrar properties á sama svæði rendera 50+ thumbnails correctly
- Three working hypotheses: backfill scope filter cut, legitimate empty source, augl_id mapping broken

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

**Stretched scope per SCRAPER_SPEC_v1 (2026-05-06)**: This entry was originally scoped for Track B (HMS supplementary scraper) only. The 2026-05-06 planning session expanded scope to cover **Track A active-listings stream** (mbl.is/fasteignir + fasteignir.visir.is) alongside Track B. Track A powers the Áfangi 4.13 market-scan view and recovers the live-listings stream that died with the legacy scraper in mid-2025. Track B was simplified per Danni clarification 2026-05-06 — HMS Fasteignaskrá contains all ~150K fastanúmer; the 25K gap is incomplete-scrape, not fundamental data sourcing. See `app/docs/SCRAPER_SPEC_v1.md` for full deliverable, decision-points (#1A/#1B/#2A/#2B), and 10-step build order.

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

---

## Framtíðar backlog (cont.) — logged 2026-05-20

1. **rebuild_training_data.py HMS export step** — export HMS metadata slice from Supabase → local parquet before building training matrix. Required by SOURCES_OF_TRUTH Supabase-canonical decision. ~1 day. Non-blocking. Linked to iter5 (unblocks brunabotamat/byggingarstig non-circular features).

2. **Áfangi: Innra heilsumælaborð (/heilsa)** — internal observability dashboard, unlinked subpage. Reads pipeline_runs + migrations_log + inputs_snapshots (Group C) + model metrics + backup manifests. Shows: model health (MAPE/PI coverage/bias/drift), data freshness per source, pipeline status, backup status, schema migration log, reproducibility check. Sequenced after Group C. Add auth gate before exposing anything sensitive.

3. **Long-term north-star: Premium agent** — LLM chat product with access to full dataset for property analysis. Enabled by the canonical-sources + Supabase-serving + audit-trail architecture. No near-term planning; tracked as directional goal.

4. **Image fallback for unlisted properties** — ~53% of properties have no listing images (never listed). Phase Z UI decision: show map/aerial view fallback (lat/lon available 100%) rather than blank. Reconcile local archive (fastnum/n.jpg) vs CloudFront (fastnum/hash.jpg) layout in image backfill Áfangi.

---

## Framtíðar backlog (cont.) — logged 2026-05-22 (evalue-audit follow-ups)

5. **Production-template hardening — fold evalue resume-skip risk into the HMS retro-fix session** — `audit/stage_a_augl_refresh.py`'s resume done-set is `SELECT fastnum FROM stage_a_augl`, which would include `augl_status=-1` placeholder rows if any existed. Below the 5% rolling-5xx halt threshold, errors persist as `-1` placeholders and are never retried on subsequent resume runs (silent-loss shape, same family as the HMS-resume issue). **Has not fired** in the current 2026-05-08→13 run (0 placeholder rows in staging DB), but the path is there. Fix shape: change resume done-set to `SELECT fastnum FROM stage_a_augl WHERE augl_status IN (200, 204)` so error rows get retried automatically. Apply the same retry-on-resume discipline to the canonical scraper template (the one `hms_full_scrape.py` will be retrofitted to, per the 2026-05-21 DECISIONS entry) so all future scrapers — including leiguskra when built — inherit it from one source. Non-urgent.

6. **Post-HMS-recovery: full evalue + kaupskrá pass for the ~71,800 recovered fastnums** — once `audit/hms_full_recovery.py` completes and the recovered set is locked, those fastnums need a full data pass before promotion to Supabase `properties`. **They are NOT in the existing evalue staging DB** (which is exactly the 124,835 Phase B set from 2026-05-08; recovered fastnums are predominantly Phase C range and were never offered to the evalue refresher). Steps:
   - **Magnitude confirm** (cheap, post-recovery): compute `|recovered_fastnums ∩ stage_a_augl_staging.fastnum|`. Expected near-zero. If significantly > 0, investigate why (overlap would indicate a Phase B fastnum was incorrectly classified as HMS-500 during the dead-zone).
   - **Evalue augl pass** for the recovered set using `stage_a_augl_refresh.py` shape but with the hardened template from item 5 (so any non-200 row is retried on resume).
   - **Kaupskrá lookup** for the recovered set — `D:\kaupskra.csv` is canonical for sales history; filter rows where FASTNUM is in the recovered set, ingest.
   - **Supabase promotion** via the Phase D pattern (extract → dryrun → apply scripts in `scripts/phase_d*_*.py`).
   - **Gated on**: HMS recovery completing (canonical recovered set), AND production-template hardening landing (item 5). **Do NOT run evalue pass before either.**

---

## Frestuð scraper-substream verk eftir Step 3d Lota 1 (logged 2026-06-18)

Frestað til að einbeita sér að agent-v0 (AGENT_SPEC §6) + T1. Ekkert af þessu blokkar virku brautirnar; allt vel skilgreint og endurtekið hér svo samhengið tapist ekki.

- **Lota 2 — mbl negotiable promotion** (~2.643 raðir, mest atvinnuhúsnæði). Gated á ákvörðun: 'unknown_commercial' lease_term_enum — (a) ALTER TYPE ADD VALUE vs (b) endurnýta 'unspecified' + sub_type placeholder (tilfinning fyrri sessiona: (a)). Útfæra líka Lota-2 caveat í resolve_price (verd=0 negotiable getur verið residential). Lágur forgangur: snertir hvorki agent né T1.
- **addr-tier remediation (Finding C)**. normalize_address strippar líklega „íb.X" of-aggressively → over-fold á nýbyggingum með óleyst fastnum (3 targets, ~7 einingar, 0,07% núna). Kerfis-vandi á ALLRI promote-fjölskyldunni, versnar í Lotu 2 og mengar dedup. Afmarkað fix + backfill-staðfesting. Sjá scraper_data/night_logs/HALT_REASON*.txt.
- **visir is_price_on_request backfill** (407 raðir, price=1 → true). Léttur frágangur, ekki kritískt.
- **Step 3e — myndaspegill (image mirror) / Gagnapakkar bootstrap** (parkað). ~196,5 GB image-skjalasafn á D:\Gagnapakkar\images\ (921K myndir, 38K fastnum-möppur, image_index.db ~2,6M raðir) NÆR-ÓNOTAÐ. Bootstrap: lesa safnið fyrst, diff-fetch eingöngu vantandi myndir; long-term-owned archive er source of truth, CloudFront-URL transient acquisition (sjá Amendment 4 image-ownership policy). Engin scraper-dependency; má byrja hvenær sem er. Image-bootstrap re-run fyrir 58 failed URLs úr Phase 3 fellur hér undir.
- **myigloo-delta — áframhaldandi refresh** (parkað). myigloo (+ visir) eru SEED-ONLY núna, engin delta-vél (ólíkt mbl sem hefur nightly delta-keðju, Task Scheduler 01:00). Þarf since-priming + delta-mode hliðstætt fetch_mbl/prime_delta_since svo myigloo-listings haldist fersk. Lágur forgangur þar til canonical-layer neytendur (T1 asking-vs-sold) krefjast ferskra myigloo-gagna.

---

## Módel-gæðavél (lokað mæli- og endurbóta-kerfi) — þríþætt, lagskipt (logged 2026-06-23)

**Forsenda**: daglega ferskleika-brautin (LIFANDI frá 2026-06-22, sjá DECISIONS 2026-06-22 daily loader) gerir þessa mælingu fyrst marktæka — áður stóð sales_history á ~2ja mán gömlum gögnum, nú lendir sala innan dags ⇒ módel-einkunn nánast rauntíma. Þrjár aðgreindar vélar, ólíkt þungar, MEGA EKKI renna saman (sama agi og þriggja-brauta CPI/ferskleika-aðskilnaðurinn).

**VÉL 1 — afturvirk módel-vöktun (létt, NÆST eftir CPI-systkin)**:
Frosnar version-stimplaðar spár (public.predictions, iter4 prod) joinaðar við NÝLENT raunverð í sales_history → rúllandi MAPE / bias / coverage á 80% + 95% bilunum, brotið niður eftir hverfi / eignagerð / verðbili. Out-of-sample í eðli sínu (salan gerist EFTIR að spáin var fryst). Engin LLM þörf — hreinn join frosin-spá × ný-sala. Fæðir public.model_metrics + /heilsa mælaborð (þegar á horizon). Byggir beint á því sem armað var 2026-06-22. Nóta: point-in-time nákvæmni → bera saman á SAMA anker (nominal/nominal eða af-ankerað), sjá v_model_vs_sold anker-óháð ákvörðun.

**VÉL 2 — LLM ask-to-sale mæling (þyngri, tengist ask-to-sale gap módelinu í hönnun)**:
Les nýja auglýsingu → LLM-extraction á SÖMU reiti og ítarlega verðmatið → spá → bíða eftir sölu → bera saman. Mælir allt rörið (extraction + verðmat) í rauntíma, ekki bara frosna spá. LÆST fyrirvari: ask-to-sale bilið er markaðs-fyrirbæri (yfir/undirverð, samningar, tími-á-sölu) EKKI módel-skekkja — verður að aðgreina tvennt. Sömu extraction-reitir í mælingu OG framleiðslu halda því hreinu: residual eftir extraction-parity = annaðhvort módel-skekkja eða markaðs-spread, og ask-to-sale gap módelið á að taka spread-hlutann.

**VÉL 3 — sjálfvirk jústering (FRYST MEÐVITAÐ, endurskoðast síðar)**:
Auto-retrain sem eltir nýjustu mælingu áhættar (a) að elta hávaða, (b) ofbregðast árstíðasveiflu, (c) feedback-lykkju þar sem módel spáir sjálfu sér. Mannlega-gated til langs tíma: mælingin segir HVENÆR iter5 borgar sig og HVAR módelið er veikt, en endurþjálfunar-ÁKVÖRÐUN er Danna, ekki sjálfvirk. Mánaðarlegt iteration raunhæft sem mannlega-samþykkt cadence informað af mælingu — EKKI blint auto-retrain. Bíður þar til VÉL 1 hefur safnað nógu mörgum vikum til að eðlilegur breytileiki sé þekktur (annars jústering gegn hávaða = plástur).

**Röðun**: CPI-systkin (í gangi) → VÉL 1 → VÉL 2 (með ask-to-sale gap módeli) → VÉL 3 (gated, frestað).

---

## ITER5 — umfang skilgreint (logged 2026-07-04)

**Heimild:** `docs/fable_prep/audits/ITER4_FEATURES_2026-07-04.md` (kjarna-niðurstaða + iter5-ályktun, gap-mat). **Gate-ar skilyrða talnalagið** í DECISIONS 2026-07-04 (tveggja laga verðmat) — liður (c) er GO/NO-GO hlið þess lags.

iter4 **inniheldur nú þegar** 133 af 154 features (86,4%) sem extraction-afleidd, en dregur úr þeim aðeins **0,83% gain** (LIVE) — iter5 snýst því EKKI um að bæta við extraction-features heldur að **hækka merki-þéttleika og lærða áhrifastærð**:

- **(a) Eignastigs-extraction backfill** — hækka þjálfunarþekju úr **~24% þjálfunarraða** (16,1% birtra eigna): extracta á EIGNASTIGI, ekki bara sölur, svo hver birt eign hafi ástandsvektor. Rótin (24% þekja + dreifð merki) er af hverju gain er 0,83% þrátt fyrir 86% feature-hlutdeild.
- **(b) Merkjaþétting** — 108 extraction-svið (schema v0.2.2) → sameina þunn one-hot flögg í ríkari, hærri-þekju samsett ástandsmerki (t.d. `has_any_recent_renovation` í stað 18 status-dálka með <50% þekju hvor; 5 features hafa nákvæmlega 0 gain). Prófa aggregate-rásina (`llm_aggregates_quarterly`) sem markaðs-feature.
- **(c) Áhrifastærðar-próba = GO/NO-GO hlið á skilyrða lagið** — endurþjálfa með nægu jákvæðu extraction-magni og MÆLA áhrifastærð; skilyrt talnalag birtist aðeins ef próban sýnir marktækar effektir. Kvarða um leið handstuðla-lagið á gögn (partial-dependence á iter4a) í stað hardcoded +30%/−10% (`sprint2_v1.1_hardcoded`).
- **(d) Verðsaga/vísitölu-features metin í leiðinni** — 0 í dag (VERÐSAGA „FANNST EKKI" í feature-menginu), meðvitað; endurmeta með rökum í iter5-hringnum.

Bíður Phase D (HMS-gögn í Supabase + `rebuild_training_data.py` export-skref), sbr. iter5-blokkun í CLAUDE.md.

---

## Eftirmál CPI-REBUILD 4c (logged 2026-07-09)

**Heimild:** `docs/fable_prep/audits/CPI_REBUILD_4c_FRAMHALD_2026-07-09T2220Z.md` + DECISIONS 2026-07-09 (valkostur iii).

- **daily_sales_refresh DO-UPDATE (varanleg lausn hönnunargatsins):** `ON CONFLICT DO NOTHING` er insert-only → HMS status-/verð-leiðréttingar á þegar-innfærðum röðum ná aldrei inn (dæmi: 744200 onothaefur 0→1 þurfti handvirkan plástur; ×1000-leiðréttingar HMS sömuleiðis). Hanna `DO UPDATE` á breytanlega dálka (onothaefur, kaupverd_nominal/real, einflm/byggar_at_sale) með sanity-vörðum — leysir líka framtíðar-útgáfur 4c-vandans við rótina.
- **tiers/comps_v2 endurbygging (handvirk, sjálfstæð ákvörðun):** `build_comps_v2.py` + `load_comps_v2.py` (HALT-gated fasar, enginn scheduler). Hreinsar AKKERI-lekann á `/eign/2315156` (valuation_tiers.prior_* ber enn blásið 33.450 M — les kaupskrá beint, nú leiðrétt fyrir 744058). 744059/84/85 priors haldast blásnir+prior_suspect þar til HMS lagar CSV. Breytingaflötur = full comps/tiers endurbygging.
- **properties.fasteignamat árgangs-frávik á 2533315:** properties ber 2.060 (þús) vs kaupskrá FASTEIGNAMAT_GILDANDI 20.150 — eldra árgangs-gildi á nýbyggingu 2024. Á heima í Phase-D/HMS-sync farveginum (metið hvort fleiri nýbyggingar bera úrelt fasteignamat í properties).

---

## Opið eftir cc10 EIGINDALAG (logged 2026-07-10)

- **vm-bera stöflun ≤720px hlaðin en ósjónprófuð** (verdmat-ai repo, commit 581d35a) — prófa við næsta viðmóts-tékk eða á síma þegar deploy er komið. Heimild: `verdmat-ai/docs/fable_prep/audits/EIGINDALAG_UI_2026-07-10T0900Z.md` §3.1.

---

## Full extraction-backfill — endurmeta við mælda notkun (logged 2026-07-13)

- **On-demand extraction er live í verdmat-ai** (cc5: route `/api/eigindi/soekja`, dagsþak 200 köll/dag, keyrslu-log í `eigindi_extraction_runs`) — full-korpus backfill var HAFNAÐ á þessum tímapunkti. Endurmeta þegar rekstrargögn liggja fyrir: hvaða eigindi eru raunverulega sótt (attrs_written per attr_key úr runs/property_attributes), og haiku vs sonnet gæði úr rekstri (mæld kostnaður sonnet-5 ~2–4,3¢/kall). Heimild: `verdmat-ai/docs/fable_prep/audits/ONDEMAND_EXTRACTION_2026-07-13T2229Z.md`. — ákvörðun 2026-07-13.

---

## Hydration-villa (Recoverable) á /markadur/modelstada — eldri rót, lagfæring bíður (logged 2026-07-16, cc4)

- Next dev-overlay sýnir "Hydration failed because the server rendered text didn't match the client" á modelstada. **A/B-sannað með git stash í cc4-lotu að villan er PRE-EXISTING** — birtist eins án cc4-skýringarlínunnar (statísk JSX getur ekki valdið misræmi). Líklegasta rót: `daysAgo(Date.now())` reiknað server-megin í PipelineHealthPanel-gögnum og/eða recharts SSR-mynstur. Recoverable (client endurteiknar tréð) — engin notendasýnileg bilun, en kostar auka-render og mengar dev-overlay. Lagfæring: færa Date.now()-afleiðslur í client-effect eða suppressHydrationWarning á viðkomandi textahnúta eftir mælingu. Heimild: CONFORMAL_RECAL_2026-07-15.md-lotan (skjámyndir í session-annál).

---

## Skráar-eigindin sem features í næsta retrain-hring — samanburðarkeyrsla (logged 2026-07-17, cc12-bókun 2, skráð í cc14)

**Heimild:** `docs/fable_prep/audit/EIGINDA_EFFEKT_2026-07-17.md` (samþykkt í heild 17.07, commit 3a959ca) + cc6-forskrift 1.3 (RETRAIN_ITER4R nafnaregla).

- **Hvað:** í næsta retrain-hring bætast skráar-eigindin fjögur við feature-mengið sem **SAMANBURÐARKEYRSLA við grunnhring** (iter4r-arkitektúr óbreyttur sem viðmið): fjherb (herbergjaþéttleiki), bílskúr gerd+m2 (gerd-lykillinn í bilskur-JSON, ekki tegund), íbúðarhlutfall (ibudarrymi_vs_heild), geymslu-flagg.
- **Nafnaregla:** fari featurarnir inn eftir samanburðinn heitir hringurinn **iter5-ættar** (feature-breyting), ekki iter4r_* (sbr. cc6-forskrift: iter4r = arkitektúr óbreyttur, „iter5" frátekið fyrir feature-breytingu).
- **Rök úr blaðinu:** þekja á seldum 27–54% (herbergi/fjherb 53,5%, bilskur_staedi 39,3%, ibudarrymi_vs_heild 26,6%); mældir effektar á iter4r-holdouti 0,5–2,5% (jaðar-marktækir) — réttlæta ekki birt B-leiðréttingarlag (SEINNA, þriggja skilyrða endurvakningarhlið í blaðinu) en réttlæta feature-prófun þar sem líkanið lærir áhrifastærðina sjálft.
- **Tengsl:** ekki sami liður og ITER5-umfangið 2026-07-04 að ofan (extraction-þétting a–d) — skráar-eigindin eru óháð extraction-backfillinu og geta farið í fyrsta hring sem býðst; ITER5-liðirnir bíða áfram Phase D.

---

## Pörunargatið í þjálfunarþýðinu — stærsta lyftistöngin á eigindaþekju (logged 2026-07-18, cc20)

**Heimild:** `docs/fable_prep/audits/EXTRACTION_BACKFILL_FORKONNUN_CC20_2026-07-18T0948Z.md` §11.
**Leysir af:** liðinn „Full extraction-backfill — endurmeta við mælda notkun" (2026-07-13) — endurmatið er framkvæmt, sjá dóm A1 í blaðinu (leið = kerfi A).

- **Vandi:** 88.347 af 146.499 samningum þjálfunarþýðisins (**60,3%**) eiga enga pörun við auglýsingu í `pairs_v1.pkl` og þar með engan texta. Extraction getur ekki lagað þetta. Fullur extraction-backfill á (b)-hópinn lyftir eigindaþekju úr 23,8% í **39,7% og ekki hærra** — þakið er pörunin, ekki extraction-fjárhagur (sá er $81).
- **Rekið er í nýlegum gögnum** — þekja eftir ári: 2016 45,0% · 2018 44,4% · 2020 33,0% · 2022 32,2% · **2024 27,9%** · 2025 29,5% · **2026 12,8%**. Fari eigindin inn í líkanið án þess að þetta sé lagað verður featurið kerfisbundið þynnst á nýjustu gögnunum, þ.e. veikast þar sem líkanið er mest notað.
- **Fyrsta mæling (sér-probe):** ~36.100 sölutextar liggja í SQLite á diski (32.376 `parsed_mbl_sale` + 3.291 `parsed_myigloo` + 418 `parsed_visir`) sem `pairs_v1` nær ekki til. Skörun þeirra við (c)-hópinn er **óvituð** — það er fyrsta talan sem þarf.
- **Þekjan er flöt eftir canonical×svæði** (18,8–41,6%): engin eignategund eða svæði er kerfisbundið verr sett, svo markviss hlutabackfill vinnur lítið umfram flatan. Lyftistöngin er pörunin sjálf, ekki forgangsröðun innan hennar.
- **Tengsl:** óháð skráar-eigindaliðnum (cc12) — sá liður getur farið í fyrsta hring sem býðst. Þessi liður ræður hins vegar hve mikið extraction-featurin geta lagt til í iter5-samanburðarkeyrslunni.

---

## SKREF 0 backfill-pilotsins — textalagið frá 18.04 verður að endurbyggjast áður en nokkuð er verðlagt (logged 2026-07-18, cc21)

**Heimild:** `docs/fable_prep/audits/D_UTTEKT_20260718T095336Z.md` §2.5 + §6.
**Tengsl:** gengur Á UNDAN liðnum „Pörunargatið í þjálfunarþýðinu" (cc20) — sama pilot, fyrra skref.

- **Fundur:** `D:\listings_text_v2.pkl` (1,54 GB) og `listings_v2.pkl` (100 MB) eru dagsettar **2026-04-18**, en eru lesnar af `build_training_data_v2.py` sem keyrði **2026-07-16 07:35** og framleiddi lifandi þjálfunargögnin. Gagnagrunnarnir undir þeim (`fasteignir*.db`) og næturleiðslan hafa haldið áfram allan tímann. **iter4r_20260716 var því þjálfað á söluyfirlitstextum eins og þeir stóðu 18.04** — þriggja mánaða texti sem safnast hefur síðan er ekki í þjálfunarþýðinu. Ekki af því að extraction vanti, heldur af því að **millilagið var aldrei endurbyggt**. Óskjalfest fram að þessu.
- **Hvers vegna þetta er SKREF 0:** ný LLM-keyrsla ofan á kyrrstætt textalag nær ekki til textans sem safnaðist eftir 18.04. Endurbygging (`parse_all_dbs.py`) kostar **diskvinnu, ekki tokena** — hún er ódýrari og áhrifameiri fyrsta aðgerð en nokkur extraction. Hún breytir líka nefnaranum sem cc20-liðurinn verðleggur: 36.100 sölutextarnir í SQLite sem `pairs_v1` nær ekki til geta að hluta verið aðgengilegir eftir endurbyggingu.
- **Röð:** (i) endurbyggja `listings_text_v2` og **mæla hvað þekjan fer í án nokkurs LLM-kostnaðar**; (ii) þá fyrst verðleggja backfill á það sem eftir stendur (cc20-liðurinn, $81-matið endurreiknað á nýjum nefnara); (iii) meta eignastigs-leiðsluna (kerfi A) sérstaklega.
- **Engin tímapressa.** Aprílkeyrslan var **Haiku 4.5**, ekki Sonnet — verðlokun sonnet-5 31.08 á ekki við um þessa leiðslu. Ef sú dagsetning á að reka eitthvað er það eignastigs-eigindalagið (leiðsla A, sem raunverulega notar Sonnet 5), ekki þjálfunar-extraction.
- **Athuga við endurbyggingu:** `parse_all_dbs.py` er rót ALLS pkl-trésins (properties_v2 / listings_v2 / listings_text_v2 / sales_v2) og er **ótrackuð á D:-rót**. Endurbygging snertir því fleiri niðurstreymis-eignir en textalagið eitt — sjá D_UTTEKT §2.3 fyrir ættartréð og §5.5 fyrir repo-heimilið sem hana vantar.

---

## Myndamats-sannreyning: 194 GB á ályktun, ekki mælingu (logged 2026-07-18, cc21)

**Heimild:** `docs/fable_prep/audits/D_UTTEKT_20260718T095336Z.md` §2.1 + §2.6 + §7.

- **Staðan:** `Gagnapakki 1/3/4/5` telja **194 GB** og eru allar frosnar 12.–16.04. `Gagnapakkar\images` (352,5 GB, 1,75M skrár) virðist arftakinn. DB-skrárnar í pökkunum eru **sannanlega bætajafnar** eintökum undir `Gagnapakkar` (stærðarjöfnuð staðfest) — en **myndatrén sjálf voru ALDREI borin saman**.
- **Hvað vantar:** raunverulegur bætasamanburður (eða a.m.k. skráarfjöldi + heildarstærð + slembiúrtak af md5) milli `Gagnapakki N` myndatrjánna og `Gagnapakkar\images`, með `image_index.db` (2.631.485 raðir, URL→path) sem þriðju heimild.
- **Hvers vegna þetta má ekki flýta sér:** 194 GB er stærsti einstaki endurheimtanlegi blokkin á disknum, en **ekkert af því plássi má telja endurheimtanlegt fyrr en samanburðurinn er gerður**. Ályktun um bætajöfnuð dregin af DB-stærðum yfirfærist ekki sjálfkrafa á myndirnar.
- **Read-only liður** — sannreyning fyrst, eyðing er sér-ákvörðun síðar og eigin lota.

---

## Bókunarlota cc70 §5A — sjö backlog-liðir (logged 2026-08-02)

**Heimildarregla lotunnar:** allar tölur úr audit-skjölum á diski, git eða DB; „[heimild óstaðfest]" þar sem ekkert fannst. Sjá DECISIONS §5A-1–32 sama dag.

- **saekjaAsettVerdEignar → `scraper.v_eign_virk_auglysing`.** Agent-verkfærið ber sömu window-rót og /eign-gatið (62–255 ms per uppfletting vs 0,4 ms um þrönga viewið); viðgerðin er bókuð sem sér-go í cc69 og bíður hans. Heimild: `ASOLU_EIGN_CC69` §1/§5.3, DECISIONS §5A-26.
- **Apríl-snapshotsins dauði (precompute-ákvörðun).** `list_price_latest`/`augl_id_latest` (max scraped_at 2026-04-16) eru nú aldrei fallback á /eign; fullur dauði þeirra er precompute-hlið sérákvörðunar — hvað les þá enn af þeim og hvað kemur í staðinn. Heimild: `ASOLU_EIGN_CC69` §5.2, DECISIONS §5A-27.
- **Tveggja-talna leiguflöturinn — útfærsla.** Ákvörðunin (A „áætluð auglýst leiga" = samningsmat × 1,19 m/heimild; B „áætluð samningsleiga" = módelið) er bókuð í DECISIONS §5A-31; útfærslan er óhafin. Rætur mældar: +19% (762/21) og elding 1,038 (n=1.189). [Ákvörðunar-spjallið sjálft ekki á diski.]
- **„Kafa dýpra"-yield-reiknivélin.** Notandainntak leggst OFAN á grunnmatið, aldrei INN í það (§5A-1: SPJALL breytir aldrei matinu; §5A-14: röðun bönnuð, tala birtist). [Vísun verkbeiðni á „PRODUCT_SPEC v1" — skjalið finnst hvergi í repoum né á D:-rót: heimild óstaðfest; liðurinn stendur á DECISIONS-reglunum tveimur þar til spec-ið kemur á disk.]
- **Mapping vs matseiningar-gerð (ágúst-endurþjálfun).** Á mapping að lesa matseiningar-gerð þegar hún stangast á við notkunar-flötinn? 2013952-tilvikið sannreynt gegn HMS-safni + DB (Íbúð/501 vs Raðhús/gerd=2, mapping fylgir notkun); verðáhrifamælingin sem ákvörðunin á að hvíla á er [heimild óstaðfest] og þarf endurmælingu í ágúst-lotunni. Heimild: DECISIONS §5A-28.
- **WARN-þröskuldur ferska jaðarsins (ágúst).** fresh_edge cov80 mældist 77,1% (n=323) undir 80%-markinu og var bókað ófullnægjandi (cc51 §F3; vöktunarkassinn ber 81,1/77,1 m/nefnurum síðan cc53). Ágúst-vaktin þarf formlegan WARN-þröskuld á jaðarinn. [Talan „75%" úr verkbeiðni finnst ekki í heimildum — þröskuldsgildið sjálft er opin ákvörðun ágúst-lotunnar.]
- **R2-myndaspegillinn.** Bylgju-2-liður 2.2 í heildarúttektinni; 402-atvikið (cc58/cc62-f0) sýndi að öll myndbirting hangir á einum ytri rofa (CloudFront-hotlink + Vercel-optimizer-kvóti) þótt afrit sé til á D:. Optimizer mælist grænn í dag (HTTP 200, mælt 02.08) — spegillinn er áhættuliður, ekki bruna. Heimild: `HEILDARUTTEKT` HLUTI 3 (2.2), `MYNDIR_402_STODUTEKK_CC62F0`.

---

## Óskir eiganda 03.08 — sex liðir (logged 2026-08-03, cc77)

**Bókunarregla lotunnar:** liðirnir eru teknir úr verkbeiðni eiganda 03.08 og eru ÓMÆLDIR — engin þekjumæling, kostnaðarmat né útfærsluákvörðun fylgir þeim hér, aðeins hvað á að gera og hvers vegna. „[heimild óstaðfest]" merkir vísun sem ekkert skjal á diski styður. Enginn liður er go.

- **1. HMS-staðreyndahnappur við hlið Söluyfirlits.** Hnappur á eignarfleti sem sýnir HMS-skráninguna sem við eigum sjálf (tegund, gerd, stærðir, byggingarár, matseiningar), og REGLA með: stangist HMS á við söluyfirlitið poppar misræmið upp og **notandinn velur lind** — kerfið þegir ekki og velur ekki fyrir hann. Rökin eru að árekstrarnir eru sannreyndir, ekki tilgátulegir: cc68 mældi HMS-innri mótsögn á Álftamýri 39 (gerð Raðhús vs notkun Íbúð, mapping fylgir notkun) og cc68 sýndi jafnframt að /eign les aðeins pörunar-söluyfirlitið — sá flötur sem hnappurinn á að standa við hlið á er því ekki fullur sannleikur um eignina. [Vísun verkbeiðni á „cc76-mælinguna": ekkert cc76-skjal finnst í app-repoinu (`docs/`) né í git-sögunni — heimild óstaðfest; talnagrunnur liðarins þarf að koma á disk áður en hann verður útfærður.]
- **2. Fastinn-samanburður (sér-lota, read-only).** Fara kerfisbundið yfir fastinn.is og bóka hvað vantar hjá okkur, sérstaklega fjóra fleti: **Opinber gjöld** (fasteignaskattur, vatnsgjald, fráveitugjald, lóðarleiga, áætluð heildargjöld/mán), **umferðarhávaði** (kortlagning Vegagerðarinnar 2022), **þjónustustig-stig** og **viðhaldsskuld**. Rökin eru að fastinn er ÓNÝTUR sem krossheimild — hann speglar mbl-id (sbr. `reference_alt_sources_unviable`, staðfest aftur í cc68) — en er þar með hreinn eiginleika-samanburður: það sem hann sýnir og við ekki er vöruskuld, ekki gagnaskuld. Liðurinn er sér-lota því hann er úttekt á ytri síðu, ekki breyting á okkar.
- **3. Kortaleit á /leit.** Leita að eign á korti með mbl-líkri virkni. Rökin: /leit er í dag texta- og síuflötur eingöngu (flokkari 2.0, cc15/cc62), en kortið er innkomuhátturinn sem notendur koma með frá mbl — sá sem veit hverfið en ekki heimilisfangið kemst ekki inn um núverandi flöt.
- **4. Söluyfirlits-smiðja fasteignasala (PRODUCT_SPEC lag 3).** AI-aðstoð sem býr til **tvennt aðskilið**: (a) heilt söluyfirlit samkvæmt STÖÐLUÐU FORMI sem eigandi sendir síðar, og (b) EINGÖNGU lýsingu. Rökin: viðmiðunarefnið er þegar til í gagnasafninu — lýsingar fylgja auglýsingum (`scraper.listings.lysing`, 7.699 eignir, sbr. `lysing_plain`-galla cc69) og eru nothæfar bæði sem þjálfunar- og viðmiðunarefni. **Sendingarferlið sjálft er á hendi eiganda** og telst ekki með í umfanginu. Blokkerar: staðlaða formið er ekki komið; og eins og í cc70 (§5A, „Kafa dýpra") finnst „PRODUCT_SPEC" hvergi í repoum né á D:-rót — lagskiptingin „lag 3" stendur því sem [heimild óstaðfest].
- **5. Aðgangsstjórnunarsíða.** Stofna og eyða aðgöngum og fylgjast með notkun per notanda. Fylgir /ops (cc65) í tíma og tón en er **sjálfstæður flötur** — ekki spjald í vöktunarvélinni. Rökin: hlutverkalagið er þegar til í DB (`stadfest-hlutverk`, cc7) og lykilorðaskipti fara nú fram sem admin-PUT án viðmóts; það er engin leið til að sjá hver notar hvað né til að loka aðgangi án handavinnu í DB.
- **6. Fable-skýrsla júlí (næsta stóra verk — bíður kvóta eiganda).** Sama snið og júní-skýrslan (`GEN_FERLI_v1`, cc7). **Nýr kafli er SKYLDA:** verðmunur á 100 m² eign eftir tegund — íbúð í fjölbýli / heil hæð / rað- eða parhús / einbýli — **mældur með nefnurum** (fjöldi að baki hverri tölu birtur, sbr. `feedback_cov_maeling_nan_sem_miss` og vöktunarkassa-regluna frá cc53). Lotan á að (i) lesa hvað hefur breyst á síðunni síðan í júní, (ii) sækja NÝJUSTU greiningar og markaðstölur af diski/DB — **aldrei úr samantekt eða minni**, (iii) skoða gögnin sjálf, og (iv) smíða nýja skýrslusíðu. Rökin fyrir (ii): endurnotkun á fyrri samantekt er einmitt bilunarmátinn sem cc21 fann í þjálfunarlaginu (kyrrstætt millilag lesið sem ferskt) — skýrslan á að hvíla á mælingu dagsins, ekki á júní-tölum með nýrri dagsetningu.

**/ops-staða 03.08 (óbreytt, til upprifjunar).** Aðeins **cc65 fasi 0** (fornleifauppgröfturinn) er lokinn: gamla /ops er heil í appinu (5 spjöld), RPC + `pipeline_runs` eru í DB, cc63-vélin reyndist ekki til. **Fasar 1–3 eru óbyggðir** og gamla /ops stendur á meðan. Líftímaskilyrði daglega stöðu-próbans stendur óbreytt: fasi 1 gleypir rökfræðina og fasi 3 AFSKRÁIR próbann — tvö kerfi lifa aldrei samhliða (DECISIONS §5A-19, STATE 02.08).

**Viðauki 03.08 — bókaður eftir push (`1bb2cd4`), append-only leiðrétting á kaflanum að ofan.**

- **Liður 1: `[heimild óstaðfest]` FELLD — cc76-mælingin er til.** Mælingin er read-only lota 03.08 sem fullmældi cc68-mótsögnina (HMS `notkun` vs `gerd`): mótsögnin nær til 28.962 íbúðareigna, þar af eru 28.065 **stök eining á heimilisfangi með 100% flatarmáls** — heil hús sem HMS skráir sem notkun 501 „Íbúð á hæð". Lindarprófið (hedónískt viðmið, cellu-FE matssvæði×ár) fellur GERÐ í vil á þeim hópi (MAE −37% / −33%) en NOTKUN í vil á 2–3 eininga hópnum og á öfugu mótsögninni — reglan er því **skilyrt (Regla R)**, ekki „gerð alltaf". **Heimild:** `docs/HMS_MOTSOGN_CC76_20260803T104446Z.md` (480 línur, lenti 03.08 kl. 10:44Z; **tracked** eintak — `.dbconfig`-slóðin stytt í línu 475, að öðru leyti línujafnt frumritinu í `docs/fable_prep/audits/` sem stendur óhreyft); skriftir átta liggja staðbundið í `docs/fable_prep/prototypes/cc76/` (631 lína, utan git skv. cc69). Tölur liðarins og viðaukans krossathugaðar gegn skjalinu: §4 ber 58.561/36,29% og 8.837 af 62.062 (14,24%), §2 ber 28.962 mótsagnir og 28.065 stakar einingar.
- **ÁGÚST-ENDURÞJÁLFUNIN ER FORMLEGA OPNUÐ (arkitektsdómur 03.08).** Fjögur **sjálfstæð** merki knýja hana, og það er fjöldinn og óhæðið sem opnar hana — ekki eitt merki: (i) **bias-fyrning** — MAPE ferska jaðarsins 12,92% (n=323, 31.07) → 14,59% (n=339, 03.08), bias −6,50%; (ii) **fresh_edge cov80 76,70% (n=339 af 352 pörum)** undir 80%-markinu; (iii) **endurgjöf fasteignasala 03.08** um heilar hæðir og rað-/parhús [munnleg, ekki skjalfest — en cc76 mældi að kvartanirnar tvær eru af gjörólíkri stærðargráðu: stök sérbýlis-eining +7,5%/+9,1% leif meðan ekta heilar hæðir bera aðeins +1,5% bjaga]; (iv) **cc76-mælingin**: Regla R færir **58.561 eignir (36,29%)** milli segmenta miðað við `canonical_code` í DB í dag og **8.837 af 62.062 þjálfunarsölum (14,24%)**. Fjórða merkið er afgerandi: conformal-kvörðunin er **lykluð á segment (×region)** (`by_segment_region`/`by_segment`), svo öll vissubil breytast og 81,1%-dómsreglan verður ósamanburðarhæf → **endurþjálfun er SKYLDA, ekki endurmæling**. Dómurinn **leysir af** afstöðu morgunvaktarinnar sama dag („EKKI opnuð núna — ein mæling er ekki þróun", `verdmat-ai/docs/fable_prep/audits/MORGUNVAKT_CC74_2026-08-03T0925Z.md` §L3): sú afstaða hvíldi á einu merki, þessi á fjórum.
- **Liður 4: `[heimild óstaðfest]` FELLD — PRODUCT_SPEC v1 er komið á disk.** Lagskiptingin er nú skjalfest: `docs/PRODUCT_SPEC_v1.md` §2 skilgreinir aðgangsstigin þrjú og setur söluyfirlits-smiðjuna í **lag 3** (fasteignasalar einir), §8 ber útfærslu liðarins óbreytta (tvennt aðskilið: heilt söluyfirlit skv. stöðluðu formi vs lýsing ein og sér, og sendingarferlið utan umfangs). **Heimild:** `docs/PRODUCT_SPEC_v1.md` (151 lína, commit `96a45d1`, pushað 03.08; rýnt og samþykkt af eiganda sama dag) — skjalið er HÖNNUN, ekki staðreyndaskrá, svo tölur úr því standa áfram undir sinni eigin heimildarskoðun. Blokkerinn sem eftir stendur er óbreyttur: staðlaða formið er ekki komið (PRODUCT_SPEC §15, opin ákvörðun 3).

---

## Cache-fundur cc82 (logged 2026-08-03, ákvörðun eiganda: hönnunarákvörðun, ekki flýtilagfæring)

- **Útgáfa ógildir ekki gagna-cache eignasíðunnar.** `lib/eign-queries.js:85` (verdmat-ai) vefur
  `saekjaEign` í `unstable_cache` með TTL 3.600 s og merkjum `eign` + `eign-<fastnum>` (cc73).
  Gagna-cache Vercel **lifir af útgáfu**, svo ný útgáfa sem breytir því HVAÐA dálka `saekjaEign`
  sækir fær gamla farminn þar til TTL rennur út. **MÆLT í cc82-útgáfunni:** söluaðila-línan
  birtist á söluyfirlitinu STRAX (sú síða notar `cache(...)` — React-minnun innan einnar beiðni,
  enginn þrálátur cache) en á `/eign/2013952` fyrst eftir **~47 mínútur**, staðfest með
  sókn-á-mínútu vöktun. Ekkert var að kóðanum; cache-færslan var einfaldlega skrifuð fyrir
  útgáfuna. cc75 tengdi `revalidateTag` við AI-fyllingarleiðina EINA, svo útgáfa hefur enga
  ógildingarleið.
  **Afleiðingin nær lengra en cc82:** hver framtíðar-breyting á því sem `/eign` les lendir allt að
  klukkustund seint á prod, og sá sem prófar strax eftir push les það sem BILUN — nákvæmlega sú
  ranggreining sem `feedback_ein_sokn_i_dev_asset_sannar_ekki_fjarveru` varar við, nema hér er
  gildran útgáfu-megin. **Tveir valkostir, hvorugur valinn:** (a) binda útgáfuauðkenni inn í
  cache-lykil `saekjaEign`, eða (b) bæta ógildingu við útgáfuferlið. Enginn go.
  Heimild: `docs/SOLUADILI_MATSARGERD_CC82_20260803T133000Z.md` §V3/§V3b.

---

## Bókun cc88 (logged 2026-08-04) — myndahýsingin, umkóðun, lindar-þak og WAF-nafnið

**Bókunarregla:** append-only. Liðirnir hér að neðan **leysa af** eldri orðalag ofar í skjalinu þar sem
það er tekið fram; eldri línur standa óbreyttar sem söguleg færsla.

- **R2-MYNDASPEGILLINN ER Í FRAMKVÆMD SEM cc87 (valkostur a1).** **Leysir af** liðinn
  „R2-myndaspegillinn" hér að ofan að því er varðar stöðumatið: sá liður bókar spegilinn sem
  **áhættulið, ekki bruna** („optimizer mælist grænn í dag") — sú forsenda er fallin. Myndahýsingin
  er horfin úr DNS og 95,46% eigna standa myndalausar (DECISIONS §5B-1); optimizer-hliðin er
  jafnframt óviðkomandi því 402-kvótinn er úreltur (§5B-2). Spegillinn er þar með **eina leiðin
  til baka**, ekki varúðarráðstöfun. Umfangið er leiðrétt í minni: spegiláætlunin fer úr
  113 GB í **263 GB** (D:-afritið dekkar 48/48 stikkprufu-eigna).
- **UMKÓÐUN Í WEBP KEMUR SÍÐAR — OFAN Á R2-EINTAKIÐ, EKKI Í STAÐINN.** Röðin er skilyrði, ekki
  smekkur: fyrst kemur heilt, óumkóðað eintak í eigin hýsingu (cc87), síðan umkóðun sem afleidd
  útgáfa ofan á það. Undanfari umkóðunar er **mæling á því HVAÐA stærðir þarf í raun** — ekki
  ágiskun um breiddir. Þau mistök eru þegar bókuð tvisvar: `feedback_fill_getur_ekki_gefid_fa_afbrigdi`
  (`sizes` án `vw` skilar ÖLLUM breiddum) og cc72, þar sem rót kostnaðarblæðingarinnar reyndist
  **breiddaryfirborð** (w=3840). Að umkóða áður en stærðaþörfin er mæld endurtekur nákvæmlega þá
  blæðingu í nýju hýsingunni.
- **LINDAR-ÞAKIÐ Á SÖLUAÐILA: myigloo BER ENGAN AGENCY-REIT.** Mælt: mbl-leiga ber söluaðila á
  **178/178 = 100%**, myigloo á **0 af 915 = 0,0%** — reiturinn er ekki tómur hjá myigloo, hann er
  ekki til í lindinni. Afleiðing fyrir hverja framtíðar-þekjumælingu á söluaðila: **nefnarinn er
  mbl-leiga, ekki allt leiguframboðið**, og 100%-þak næst aldrei á samsettum fleti meðan myigloo er
  með. Röðunin (`asett_verd_dags desc, listed_at desc`) velur eina röð þegar báðar lindir eiga
  eignina — sjá DECISIONS §5B-5 (viðmið veljast á EIGN, ekki röð). Heimild:
  `docs/SOLUADILI_MATSARGERD_CC82_20260803T133000Z.md` §V4 (lindartafla, línur 434–468).
- **WAF-REGLUNAFNIÐ ER VILLANDI — ENDURNEFNA.** Reglan heitir `cc73-UA-maeling-bera-saman`, sem
  lýsir upphaflegu umfangi hennar (UA-mæling á /bera-saman). Hún hefur síðan verið **víkkuð á allan
  flötinn** og nafnið lýsir henni ekki lengur — sá sem les regluna í Vercel-eldveggnum les rangt
  umfang og gæti breytt henni eða fellt hana í trausti þess að hún snerti eina síðu.
  Endurnefning er hrein snyrting án virknibreytingar; **enginn go**. Nafnið finnst hvorki í
  `app/docs/` né `verdmat-ai/docs/` (leitað 04.08) — það lifir eingöngu í Vercel-stillingunum,
  sem er sjálfstæð ástæða til að bóka það hér.

---

## Bókun cc95 (logged 2026-08-04) — R2-birtingarleið, hýsilvöktun, munaðarlausar myndaraðir, probe-hreinsun, cc85-framkvæmd

**Bókunarregla:** append-only; liðirnir bæta við og leysa ekki af neitt ofar í skjalinu. Hver tala er sannreynd af diski eða DB í lotunni og ber heimildarslóð. Sjá DECISIONS §5B-7–13 sama dag. **Enginn liður er go.**

- **R2-BIRTINGARLEIÐIN — FASI 2+3 (hönnun+diff, svo skipti með HALT á milli).** Spegillinn er fullgerður og bætta-vottaður (**2.631.932 + 12.976 hlutir / 588.164.415.714 bæti**, núll frávik á öllum sex tölum í sjálfstæðri endurmælingu — DECISIONS §5B-10), **en hann er afrit, ekki birtingarleið**. Birtingin liggur áfram á upprunahýslinum eftir cc93 (DECISIONS §5B-11); þessi liður er **varanlega formið**, og útfallið 03.–04.08 sannaði þörf hans en ekki fall hýsilsins. **Þrjú forsendumál standa óleyst og eru öll fasa-2-verk, ekki fasa-1-gallar:**
  1. **Fatan er ekki opinber.** Engin opinber slóð, **ekkert `r2.dev`-lén og enginn Worker uppsettur**; táknið er fötu-skorðað og getur ekki búið til fötur. Heimild: `docs/fable_prep/audits/R2_SPEGILL_FASI0_CC87_20260803T2325Z.md` §18 liður 3.
  2. **Slóðirnar vísa allar á hinn hýsilinn.** Geymdu slóðirnar vísa **100% á CloudFront-hýsilinn** — mælt í cc92: 1 hýsill í töflunni, 2.583.775 raðir. [Nákvæmni: cc87 §18 nefnir dálkinn `property_images.original_url`; sá dálkur er í `image_index.db` á D:, í DB heitir hann `url` — sjá DECISIONS §5B-12.] Heimild: `R2_SPEGILL_FASI0_CC87` §18 liður 2, `D:\_audit\HYSILL_LIFNADI_CC92_20260804T2215Z.md` §2.
  3. **`myndir/0/`-frávikið brýtur tengingarforsenduna.** Forskeytið `myndir/0/` ber **47.709 hluti / 8.685.845.481 bæti (8,09 GiB)**, flatnúmeraða `1.jpg` … a.m.k. `10650.jpg`, dagsetta 2026-05-08 til 2026-05-14. **„0" er ekki gilt fastnúmer** — það eru **1,81% allra hluta undir `myndir/`** á auðkenni sem ekki verður tengt við eign. Speglunin gerði rétt í að flytja þá (`copy` á að vera trú upprunanum og skrárnar VORU á D:), en **hver birtingarleið sem gerir ráð fyrir `myndir/{fastnum}/` sem tengjanlegum lykli rekst á þessa 47.709 hluti**. Uppruni númersins er óskýrður. Heimild: `D:\_audit\R2_SANNPROFUN_CC91_20260804T2220Z.md` §5.2.

- **DAGLEG HEAD-VÖKTUN Á MYNDAHÝSINGUNA — inn í cc65-vöktunarhönnunina.** ~5 geymdar safn-slóðir, HEAD-beiðni daglega, viðvörun við ≠200. **Rökin eru mæld, ekki tilgátuleg:** hýsillinn hvarf úr DNS og kom aftur án nokkurs merkis frá okkur — mælt útfall **≥ 23 klst 34 mín og ≤ 45 klst 24 mín** (síðasta lifandi mæling `2026-08-03T00:40Z`, fyrsta dauða `22:30Z` sama dag, endurkoma `2026-08-04 ~22:04Z` [arkitektsmæling, ekki á diski]). **Næsta útfall á að finnast af okkur, ekki af notanda.** Aðferðin liggur fyrir tilbúin úr cc92: fléttuð lög (round-robin) svo kill-switch mæli hýsilheilsu en ekki eitt lag, 1,5 s bil, eigin UTC-stimpill per beiðni. Tveir varnaglar fylgja: **HEAD ≠ GET** (bætin eru ekki sótt) og **ekkert hotlink-próf** — enginn `Referer`-haus var sendur, svo vöktunin segir ekkert um hvort dreifingin hafni beiðnum frá `verdmat.ai`. Heimild: `HYSILL_LIFNADI_CC92_20260804T2215Z.md` §4/§7, DECISIONS §5B-7.

- **MUNAÐARLAUSAR MYNDARAÐIR Í JÖÐRUM FASTNUM-BILSINS — rannsóknarefni (read-only).** Aukafundur cc92, utan verkefnis: **lög A (lægstu fastnum, bil 33 .. 488.073) og C (hæstu, 25.346.373 .. 206.138.810) eiga 0 af 50 raðir í `properties`** — jaðar-fastnúmerin bera myndir en enga eign (477 og 1.309 myndir alls á eignum laganna). Miðjulagið á **50/50** og slembilagið **44/50**. **Myndaraðir eru því til í báðum endum bilsins án eignar á bak við sig.** Ómælt: heildarfjöldi slíkra raða, hvort þær skarast við `myndir/0/`-frávikið, og hvort þær eru leifar, leiguauðkenni eða annað nafnrými. Heimild: `HYSILL_LIFNADI_CC92_20260804T2215Z.md` §3 (lagataflan) + §7.2.

- **PROBE-FORSKEYTIN ÁTTA Á R2 STANDA ÓHREINSUÐ — bíður sér-go.** **3.200 hlutir / 718.441.779 bæti (718,44 MB) / $0,011 á mánuði**, staðfest tvímælt (cc87 §18 og cc91 §3.2, sama tala upp á aukastaf): `probe-b3/`, `probe-b4/`, `probe-b5/` (500 hver), `probe-g1/`, `probe-g2/` (100 hver), `probe-x3-64/`, `probe-x4-128/`, `probe-x5-64/` (500 hver). **Hreinsun er `delete`-aðgerð á fötunni** og fer því ekki fram án sér-go — cc91 var read-only og skildi þau eftir af ásettu ráði. Kostnaðurinn er hverfandi; ástæðan til að hreinsa er bókhaldsleg, ekki fjárhagsleg: forskeyti sem enginn á heima í fötunni gera hverja framtíðar-rótartalningu tvíræða. Heimild: `R2_SANNPROFUN_CC91_20260804T2220Z.md` §3.2 + §6, `R2_SPEGILL_FASI0_CC87` §18 liður 1.

- **cc85 VERK D — FRAMKVÆMDIN, TVÖ ÞREP MEÐ HALT Á MILLI (bíður tímasetningar eiganda).** Ákvarðanirnar D1–D5 eru bókaðar (DECISIONS §5B-13); framkvæmdin er óhafin og **enginn go liggur fyrir**. **Þrep 1:** `scraper.listing_sessions` (tafla) + backfill — **110.165 raðir / 58.349 fastanúmer / ~6,2 MB** við `gap_dagar = 90` — **svo HALT og mæling**. **Þrep 2:** `scraper.v_eign_fyrri_lota` (sýnigat flaggsins, **1.284 öruggar eignir** eftir fjöleiningarsíu) + UI (`FyrriLota.tsx`). **Sérþrep, ekki hluti af hvorugu:** `v_units.n_relistings`-viðgerðin — hún snertir `scraper.v_expected_vs_real` og á sitt eigið dryrun. Orðalagsbannið úr D1 gildir um allan UI-textann: „engin þinglýst sala er skráð", aldrei „seldist ekki". **Staða á diski 04.08:** aðeins þrep-1 migrationin er til, **untracked** (`verdmat-ai/supabase/migrations/20260804_cc85_listing_sessions.sql` + rollback); þrep-2 skrárnar (`20260804_cc85_v_eign_fyrri_lota.sql`, `FyrriLota.tsx`) eru **eingöngu til sem diff í hönnunarskjalinu**, ekki á diski. Heimild: `D:\VIDHALDSSAGA_D_HONNUN_CC85_20260804T0030Z.md` §0.1, §2 (umfangstaflan), §3, §4.1–§4.8 (diffið), §5 (`n_relistings` sem sérþrep), §6.

---

## Bókun cc108 (logged 2026-08-07) — leigusíðan, myndamálið sem heild, endurþjálfunar-eftirmál, RLS-fasi 2 og cc102-eftirstöðvar

**Bókunarregla:** append-only; liðirnir bæta við og leysa ekki af neitt ofar í skjalinu. Hver tala er sannreynd af diski, úr git eða úr skjalfestri mælingu í lotunni og ber heimildarslóð. Sjá DECISIONS §5C-1–21 sama dag. **Enginn liður er go.**

### A — LEIGUBRAUTIN

- **VIEW-APPLY `scraper.v_leiga_auglysing` — DRÖGIN ERU TIL, ÓAPPLÝJUÐ; RÖÐIN ER SKILYRÐIÐ.** Drögin liggja á `verdmat-ai/docs/drog_migration_cc107_leiga_view_DROG_EKKI_APPLYJA.sql` (3.813 B). Aðgerðin sjálf er lítil og afturkræf — `CREATE VIEW` + `GRANT`, **engin töflubreyting, ekkert RLS-rask**, grants eins og systur-viewin (authenticated + service_role, **engin anon-grant** svo cc105-myndin haldist óbreytt, DECISIONS §5C-18). **Röðin er samt bindandi: einn DB-skrifari í einu, og cc105 FASI 2a gengur fyrir** (og flipp-frágangur á undan honum). **Þegar viewið kemur inn hverfa varaleiðar-takmarkanirnar FJÓRAR í einu og uppfærslan er hrein skipti á gagnalaginu — síðan sjálf stendur óbreytt**: (1) horfin auglýsing fær stöðumerki í stað 404 (deildir/bókamerktir hlekkir hætta að deyja), (2) `listing_title` verður til (mbl 348 + myigloo 947 af 1.475), (3) `frumauglysing_url` verður **lesið úr gögnum** hjá 1.295 af 1.475 í stað þess að vera alltaf smíðað, (4) fjarveru-flögguð auglýsing heldur lýsingu og söluaðila. **Prófunarkrafa við apply:** sömu fimm SSR-tilvik og cc107 notaði + 404-jaðrarnir, og `/leit` leiga 24/24 → `/leiga`. Heimild: `verdmat-ai/docs/HALT_SKIL_LEIGUSIDA_CC107_FASI_A_20260806.md` §1, `verdmat-ai/lib/leiga-queries.js` haus (takmarkanirnar fjórar orðréttar), DECISIONS §5C-20.

- **24,4 %-FASTNÚMERA-TALAN ER MÆLISPURNING, EKKI STAÐREYND — hún þarf endurmælingu áður en hún er notuð aftur.** Talan „24,4 % leiguauglýsinga hafa ekkert fastnum" kemur úr **cc60** og var borin óbreytt inn í route-rökin fyrir `/leiga/[listing_id]`. **Hún var EKKI endurmæld í cc107**; það sem cc107 mældi 06.08 var annað: 1.475 virkar leiguauglýsingar (myigloo 947 / mbl 528), lýsing á 99,1 %, `photos_json` á 100 %, leigumat til fyrir 871 (59 %). **Röksemdin stendur óháð tölunni** — `listing_id`-route þekur 100 % hvort sem hlutfallið er 24,4 % eða annað — **en talan sjálf má ekki fara í notendaflöt, skýrslu né stefnuákvörðun fyrr en hún er endurmæld á núverandi framboði með sýnilegum nefnara.** Mælingin er ódýr (ein `count(*) filter (where fastnum is null)` á virku framboði) og á heima í sömu lotu og view-applýið. Heimild: `HALT_SKIL_LEIGUSIDA_CC107_FASI_A_20260806.md` §Kortlagning + §Gagnaflöturinn; DECISIONS §5C-20.

- **`leiga_type_N`-RÓTARFIXIÐ Á HEIMA Í PROMOTERNUM — cc107 lagaði BIRTINGUNA, ekki rótina.** `app/scripts/promote_mbl.py:427` skrifar `"tegund_raw": "leiga_type_%s" % (p.get("type_id") if ... else "na")` — óupplausinn kóði fer beint í gagnalagið. `verdmat-ai/app/leiga/[id]/page.tsx:116–122` ver birtinguna (`!/^leiga_type_/.test(...)` og fellur á `sub_type`-merkimiðann), og `components/leit/LeitSia.tsx:14` ber athugasemd um sömu vörpun. **Þar með eru nú TVEIR neytendur sem verja sig gegn sama spillta gildinu og enginn sem hafnar því** — nákvæmlega mynstrið sem cc94 mældi og §5C-2 bókar. **Rótarfixið er vörpun í promoternum úr `type_id` í merkingarbært gildi (eða `NULL` þar sem vörpun er óþekkt — grunnregla 10), með afturvirkri leiðréttingu á fyrirliggjandi röðum og mælingu fyrir/eftir.** Fyrsta þrepið er ódýr talning: hve margar `scraper.listings`-raðir bera `tegund_raw ~ '^leiga_type_'` og hvaða `type_id`-gildi koma fyrir. Heimild: `promote_mbl.py:427`, `app/leiga/[id]/page.tsx:116–122`, DECISIONS §5C-20.

- **LEIGU-ENDURSJÓNUN FYRIR 01.09 — NÆSTA STÓRA VERK, ekki liður í þessari röð.** Leiguflöturinn er nú samsettur úr lögum sem urðu til hvert í sínu lagi: `/leiguverd` (lendingarsíða), `/leiguverd/[fastnum]` (módelspá), **nýja `/leiga/[listing_id]`** (auglýsingin), leigu-hamur á `/leit`, leigumatskortið með sínum bælingarreglum, og tveggja-talna framsetningin (§5A-31) sem er bókuð en óútfærð. **Endursjónunin á að spyrja hvaða af þessum flötum eiga að vera til, hvernig notandi ferðast milli þeirra, og hvað af leigubrautinni er nógu þroskað til að bera eigin vörulínu.** Undirliggjandi mælingar sem eru þegar til og eiga að liggja fyrir: leigumatsþekja 59 %, framboð 1.475 virkar auglýsingar, ask-vs-samnings-vörumunurinn (§5A-5), 24,4 %-spurningin hér að ofan, og `DRIFT_BASELINE`-staðan úr rent-restep. **Tímamarkið 01.09 er sett af eiganda; hvorki umfang né form er ákveðið og hvorugt fær go í þessari lotu.**

### B — MYNDAMÁLIÐ SEM EIN HEILD

- **MYNDAMÁLIÐ ER EITT MÁL Í FIMM ÞREPUM OG HEFUR VERIÐ AFGREITT SEM FIMM MÁL — það á að taka sem heild næst.** Staðan, öll mæld: **(1) Ingestion er dautt** — 0 af 9 Task-Scheduler-verkum snertir myndir, nýjasta mynd á öllum níu myndarótum er frá **2026-07-02T09:21Z**, og gatið vex um **~237 fastnúmer og ~10.042 einstakar slóðir á viku ≈ 1.435 myndir á nótt** (cc96). **(2) Bæti-pípan er til og sönnuð** (`fetch_listing_images.py`, 386.587 sótt, 1,07 % / 0,00 % lost) — hana vantar aðeins ræsingu, mælt á **~29 mín/nótt og 444 MB/nótt (13,4 GB/mán, 162 GB/ár)**. **(3) Bakfyllingin er ógerð**: 78.598 slóðir virkra auglýsinga eiga engin bæti (~21,1 GiB, **26,2 klst** á 1,2 s takti), og **myigloo er brýnna en mbl þrátt fyrir að vera 5 % af fjöldanum** því mbl hefur enga aldursbrún (99,3 % lifun aftur til 2014) en myigloo er óprófað með 7.076 slóðir án bæta. **(4) Skemað ræður ekki við þetta**: `property_images` er `(fastnum, url, img_order)` — ekkert `source`, ekkert `sha256`, engin tímastimplun, `fastnum NOT NULL` útilokar 808 auglýsingar með smíði; **leið (b) (ný systkinatafla + þriggja laga view) er afstaða arkitekts en hefur ekkert go**. **(5) Birtingarleiðin er blokkeruð**: R2-fatan er ekki opinber (ekkert `r2.dev`, enginn Worker, táknið fötu-skorðað), svo `augl-myndir/` er **varðveislulag, ekki birtingarlag**. Þar við bætist að **næturafritið nær enn ekki yfir `image_store`** (`backup_paths.json` óbreytt) — cc97 var einskiptis-spegill, svo hver ný mynd sem sótt yrði lendir aftur á einu eintaki þar til það er lagað. **Að afgreiða þrep 2 án þrepa 1/3/4/5 framleiðir vaxandi safn sem ekkert les; að afgreiða þrep 5 án þreps 4 er ekki hægt. Röðin sem mælingarnar styðja er: myigloo-bakfylling (~3 klst) → næturtaktur + `backup_paths.json` → skemaákvörðun (a/b/c) → mbl-bakfylling → birtingarleið.** Heimild: `D:\_audit\MYNDA_GAP_CC96_20260804T2303Z.md` §1–§4.4; `D:\_audit\AUGL_MYNDIR_SPEGILL_CC97_20260805T0000Z.md` §8; DECISIONS §5C-6, §5C-7.

- **RÉTTINDAAFSTAÐAN ER ÓBÓKUÐ OG HÚN ER FORSENDA ÞREPS 5, EKKI FYLGISKJAL.** Í dag birtast auglýsingamyndir gegnum **hotlink** á `cdn.mbl.is` og `myigloo.is` — myndirnar eru sóttar af hýsli útgefandans í hvert sinn sem notandi opnar síðu. Þrep 5 (birting af eigin hýsingu) breytir því í **afritun og endurbirtingu af okkar hýsingu**, sem er annars konar aðgerð gagnvart rétthafa. **Engin afstaða til þess finnst skjalfest á neinum diski sem þessi lota leitaði í** — hvorki í `docs/`, `_audit/` né í minni; `augl-myndir/`-spegillinn var rökstuddur sem **varðveisla** (eitt eintak → tvö eintök) og cc97 tók sérstaklega fram að hann breyti engu um birtingu. **Þessi liður er því ekki tæknilegur: hann er afstaða eiganda sem verður að liggja fyrir ÁÐUR en þrep 4 (skema) er hannað**, því skemaleiðin ræður því hvort birting af eigin hýsingu verður yfirhöfuð möguleg. Þangað til stendur hotlink-birtingin óbreytt og er sjálf áhætta sem er þegar mæld (þrír ytri rofar; cc83/cc92 sýndu að einn þeirra getur fallið og komið aftur án fyrirvara). Heimild: fjarvera skjalfestrar afstöðu (leitað 07.08 í `app/docs`, `verdmat-ai/docs`, `D:\_audit`); `MYNDA_GAP_CC96` §4.1; `AUGL_MYNDIR_SPEGILL_CC97` §8 liður 3.

- **R2-REIKNINGURINN HEFUR ALDREI VERIÐ LESINN AF MÆLABORÐI.** Allar kostnaðartölur ($9,70/mán heildarreikningur fötu, +$0,62/mán jaðar, $0,96 PUT eitt skipti, $0,011/mán fyrir probe-forskeytin) eru **reiknaðar úr mældum bætum og birtum taxta**, ekki lesnar af Cloudflare-mælaborðinu. **Næsta R2-snerting á að lesa mælaborðið og bóka mismuninn** — sama vinnubrögð og Vercel-brennslan fékk 06.08, þar sem mælaborðslestur skar úr um að brennslan væri einskiptis. Heimild: DECISIONS §5C-8.

### C — EFTIRMÁL cc94 OG ENDURÞJÁLFUNARINNAR

- **FÖLLNU 31 SITJA ENN ÁN EXTRACTION — BIÐRAÐAR-GAT, ~$0,13.** 31 kall féllu nóttina 05.08 á tómri Anthropic-inneign. Mælt gegnum **sömu fyrirspurn og keðjan notar** komu þau öll aftur í biðröðina (31/31, sæti 1–31 af 200, 0 hálfvistuð) — **en við mælingu cc103 06.08 höfðu 0 af 31 fengið extraction** (forskeytis-mátun rauðsönnuð 4/4 á þekktum jákvæðum; `lysing_hash` geymt 12 stafa). Nætur-pickerinn endurvelur þau ekki. Þetta er **þrep 8 í flipp-röðinni og bíður sér-go**; kostnaður áætlaður ~$0,13. **Fyrsta verkið er að endurmæla hvort þau séu enn óunnin — talan 0/31 er frá 06.08.** Heimild: `COMPONENTS_SPILLING_CC94` §7.2; `project_morgunvakt_cc103` sérliður 2; DECISIONS §5C-5.

- **AFRITSTÖFLURNAR ÞRJÁR MEGA FARA — EN EKKI FYRR EN EFTIR SÉR-GO, Í FYRSTA LAGI ~13.08.** `scraper.listing_extractions_pre_cc94b` (163 raðir) geymir **einu eintökin af 1.309 `detail`-textunum** sem B1 felldi; `_pre_cc94b2` (2 raðir) og `listing_valuations_pre_cc94b2` (4 raðir) geyma grunnlínuna fyrir V2-endurfrystinguna. Skilyrðið sem cc94 setti sjálft: **þrep C þarf að hafa staðið óáreitt í a.m.k. viku** (þ.e. frá ~2026-08-13). Þær eru jafnframt tvær af þremur linter-frávikunum í cc105 §1 — **ENABLE RLS á þær (FASI 2a) og DROP á þær eru tvær aðskildar ákvarðanir og hvorug má afgreiða hina**. Heimild: `COMPONENTS_SPILLING_CC94` §11.4, §14, §15; `docs/HALT_SKIL_RLS_GAT_CC105_FASI1_20260806.md` §1, §4b.

- **`--bridge` VANTAR Í NÆTUR-KEÐJUNA: 22.649 EIGINDARAÐIR ERU REIKNAÐAR EN ALDREI SKRIFAÐAR.** `nightly_delta_chain.sh` kallar `run_extraction --forward 200 --confirm` **án `--bridge`**; þurrkeyrsla staðfestir (`bridge: SLEPPT (opt-in …)`). Mælt í `public.property_attributes`: `source='auglysing'` ber **21 raðir á 2 eignum** — cc75-prófmálin frá 03.08 og ekkert annað. **Vörpunin er mæld til að skila 22.649 röðum á 3.197 eignum.** Þetta endurrammar allt cc94-viðgerðarumfangið: ~143 raðirnar sem strengja-spillingin kostaði eru smáatriði við hliðina á 22.649 röðum sem eru reiknaðar en aldrei skrifaðar. **Þetta er cc75-tengivandi (vantandi rofi í keðjuskrána), ekki cc94-spilling**, og hann bíður sér-ákvörðunar — sem verður að taka mið af því að GO-bréf endurþjálfunarinnar bókaði **brúna FROSNA þar til γ-mótprófið er komið** (§8 í GO-bréfinu: ágúst-endurþjálfun → γ-frysting m/mótprófi og holdout → **afþíðing brúarinnar** → endurmæling þakhlutfallsins). Heimild: `COMPONENTS_SPILLING_CC94` §6.5a; `docs/GO_BREF_FLIPP_REGLA_R_CC98_20260806.md` §7, §8.

- **DISKSAFNIÐ ER ÞJÁLFUNARINNTAK OG ÞAÐ ER SPILLT — 779 STRENGIR + 75 SPILLT ÁR.** `D:\batch_extraction_unique.jsonl` (37.544 færslur) ber **779 strengja-`components` (2,08 %)**, **0 þeirra endurparsanlegir með `json.loads`**, og **75 ár utan [1900, 2026] af 27.464 fylltum (0,27 %)** — þar af **71 afstæður aldur ≤ 20** (sama rót og §5C-3) og 4 raunveruleg byggingarár fyrir 1900. Skráin liggur í `extraction_features_v1.pkl` og **hefur þegar runnið inn í iter4-þjálfunina**. Viðgerð þar er **endurþjálfunarverk, ekki gagnaviðgerð** — sér ákvörðun, og hún á heima í næsta þjálfunarhring, ekki í viðhaldslotu. Heimild: `COMPONENTS_SPILLING_CC94` §1.6, §5 liður 1.

- **`model_quality_extraction_cache.jsonl` CACHAR ÓVALIDERUÐ HRÁSVÖR.** `model_quality_eval.py` kallar sama `extract_listing` **án valideringar** og skrifar í `D:\model_quality_extraction_cache.jsonl`, sem fer beint í `build_extraction_features`. Vikulega gæðamælingin les hann. **Ómælt hvort spilling sé þar** — og mælingin er ódýr (sama `validate_extraction` keyrð á skrána). Vægið óx við þrep 7: vikulega mælingin er nú dómsreglan á nýja grunninum. Heimild: `COMPONENTS_SPILLING_CC94` §6.5b; DECISIONS §5C-21.

- **DEGRADED-LEIÐIN ER PRÓFUÐ HERMT, ALDREI Á RAUNBILUN.** Sex prófmál græn á gerviloggum, en fyrsta raunverulega `CHAIN DEGRADED`-nóttin er ókomin (nóttin 05.08 hefði borið hana en fór óskráð og er ekki afturvirkt merkjanleg). **Ekkert á að gera — þetta er bókun svo að fyrsta raunverulega DEGRADED-nóttin verði lesin sem staðfesting en ekki sem nýtt frávik**, og svo að fjarvera DEGRADED-lína sé ekki lesin sem sönnun um að leiðin virki. Heimild: `COMPONENTS_SPILLING_CC94` §12, §15; DECISIONS §5C-5.

- **`/eign`-HAUSINN BIRTIR `tegund_raw` — OPIN VÖRUÁKVÖRÐUN EFTIR FLIPPIÐ.** Flippið færði spána og segmentið á R-flokkun (58.765 eignir skiptu um flokk), **en hausinn á eignasíðunni birtir áfram HMS-hrálabelið samkvæmt fyrirliggjandi hönnun**. Á eign eins og 2013952 þýðir það að spáin er raðhúsaspá á meðan hausinn getur enn sagt „íbúð á hæð". **Hvort hausinn eigi að sýna R-flokkunina, hrálabelið, eða bæði með skýringu, er vöruákvörðun sem enginn hefur tekið** — hún er ekki galli í flippinu og fær ekkert go hér. Heimild: `AGUST_ENDURTHJALFUN_FLIPP_CC104_20260806.md` þrep 6; DECISIONS §5C-17.

### D — RLS-FASI 2 (cc105) OG cc102-EFTIRSTÖÐVAR

- **cc105 FASI 2a — PÓSTFLAGGIÐ + HREINLÆTIÐ, ein migration með rollback skrifað FYRIR apply.** Þrennt: ENABLE RLS á `pre_cc94b`-töflurnar þrjár (+ REVOKE-belti þótt engar grants séu, fæðingarreglusamræmi); `spatial_ref_sys` — ENABLE RLS **ef eignarhald leyfir**, annars REVOKE-leiðin (grantor er `postgres` skv. ACL svo REVOKE er heimilt); mælt EFTIR um `pg_class`/ACL og advisors endurkeyrðir. **HÖRÐ RAUNPRÓFUNARKRAFA: `poi_naesta` er SECURITY INVOKER og anon-kallanlegt PostGIS-fall — POI-lagið á `/eign` getur brotnað undir anon við REVOKE.** Prófa verður `poi_naesta` sérstaklega undir anon auk `/markadur`, `/eign`, `/leiguverd` og `/leit` eftir apply. **Skilyrði: sér-go, og ein breyting í kerfinu í einu.** Heimild: `docs/HALT_SKIL_RLS_GAT_CC105_FASI1_20260806.md` §4a, §5; DECISIONS §5C-18.

- **cc105 FASI 2b — VIEW/MV/FALLA-FLÖTURINN, fimm smáverk sem ekkert er aðkallandi.** Fyrst stefnuval á definer-mynstrinu (**tillaga: samþykkja og bóka sem meðvitaða opnunarleið**), svo: (i) þrjár grant-lausar semantic-MV — samræma stefnu (granta eða bóka sem innri); (ii) `st_estimatedextent` REVOKE (síðan notar það hvergi, grep: 0); (iii) `search_path` fest á þrjú föll, þar á meðal **`search_properties_grouped` sem er anon-kallanlegt um `/leit`**; (iv) HIBP-vörnin á (dashboard, ekki SQL); (v) þrengja authenticated-grant á scraper-viewunum tveimur í service_role eingöngu. **Hvert með raunprófunarkröfu á `/markadur`, `/eign`, `/leiguverd`, `/leit`.** Heimild: `HALT_SKIL_RLS_GAT_CC105_FASI1_20260806.md` §3.2–§3.4, §4c, §5.

- **cc102: VIKUTAKTS-VERKIÐ KEYRIR AÐEINS ÞEGAR NOTANDI ER INNSKRÁÐUR — S4U-LAGFÆRINGIN ER ÓGERÐ.** `verdmat-weekly-panel-freeze` (sunnud. 05:00, `D:\cc102_weekly.py`) var skráð 06.08 **en með `Interactive` logon-type, ekki bókaða `S4U`** — S4U krefst stjórnandaréttinda (`Access is denied` frá `Register-ScheduledTask`, `schtasks /NP` OG `/XML`). Lagfæringin er tilbúin á diski: **`D:\cc102_fix_s4u.ps1`, ein skipun, þarf hækkuð réttindi.** Þangað til er panelfrystingin ekki áreiðanleg. *Bókað í leiðinni: „fyrra go" um vikutaktinn hafði ALDREI verið framkvæmt — ekkert slíkt verk var til.* Heimild: `D:\_audit\CC102_B2_VIKUTAKTUR_20260806T0950Z.md`; `D:\cc102_fix_s4u.ps1` (1.541 B, dags. 06.08).

- **cc102: FASTEIGNASALA-ÚTGÁFAN OG AÐFERÐAFRÆÐISÍÐAN — sér skjal, eftir flipp, með sér-go.** Ákvörðun eiganda 06.08: **engin opinber birting samanburðarins** og **keppinautanöfn bönnuð í öllu sem fer út úr húsi**. Okkar eigin tölur mega birtast síðar sem aðferðafræðisíða án keppinautatalna; fasteignasala-útgáfan verður sér skjal með okkar nákvæmni m/nefnurum, samanburði við **fasteignamat HMS eingöngu**, þekju, heiðarleika-nálguninni og framvirku aðferðinni lýstri án nafngreininga. **Flippið er nú komið inn, svo forsendan („eftir flipp") er uppfyllt — en hvorugt fær go hér.** ATH að nákvæmnistölur okkar hafa breyst við flippið og allt slíkt efni verður að byggja á nýja grunninum (§7-grunnur 3.3), ekki cc102-tölunum sem mældu `iter4r_20260716 + cc51`. Heimild: `D:\_audit\CC102_NIDURSTODUR_20260806T0950Z.md`; DECISIONS §5C-13, §5C-16.

- **cc101: ÞRJÁR OPNAR SPURNINGAR AF MARKAÐSSÍÐUNNI.** (a) **`v_postnr_prices_yearly`-grantið** — póstnúmera-flipinn var ekki smíðaður því viewið er lokað anon; **UI var vísvitandi ekki smíðað fyrir grant sem ekki er til**, og grant er DB-breyting sem þarf sér-go (og fellur undir cc105 FASA 2b-stefnuvalið). (b) **Mánaðarleg endurreiknun fastgreininganna** — `scripts/reikna_markadsgreiningar.mjs` er til (þarf `DATABASE_URL` + `pg`) en **engin sjálfvirkni**; fastgreiningarnar bera keyrsludag 06.08 og eldast þögult ef enginn keyrir hana. Hún á að fylgja skýrslutaktinum. (c) **`ats_lookup_by_quarter` er STALE 2025Q2** — `above_list_rate` var hafnað sem síðuefni af þeirri ástæðu; endurbygging ats-vélarinnar er sjálfstætt verk. Heimild: `verdmat-ai/docs/fable_prep/audits/MARKADUR_ENDURSMIDI_CC101_2026-08-06T1112Z.md` §A2, §A2b, FASI C; DECISIONS §5C-10.

### Viðauki cc108-A (logged 2026-08-07) — leiðrétting í sömu lotu: föllnu 31 eru afgreiddar, biðraðar-gatið stendur

**Liðurinn „FÖLLNU 31 SITJA ENN ÁN EXTRACTION" hér að ofan er ÚRELTUR og fellur niður.** Samhliða lota pushaði `f5b45e6` kl. 00:43:05Z 07.08 — eftir að cc108 las heimildirnar en fyrir commit — og dró þær út: **0/31 → 31/31** útdregnar (safn 5.491 → 5.522), **30/31 verðmetnar** (safn 20.642 → 20.851, +209 raðir á 30 fastnúmerum; sú eina sem eftir stendur ber `rejected:key_outside_enum` og er **réttilega** utan verðmats skv. cc94-reglunni). Kostnaður **$0,2343** gegn ~$0,13 áætlun — frávikið er kallafjöldinn (33 en ekki ~18), bókað en ekki jafnað út. Sjá DECISIONS §5C-22.

**Það sem EFTIR STENDUR og er hinn raunverulegi liður:**

- **BIÐRAÐAR-GATIÐ SJÁLFT — NÆTUR-PICKERINN ENDURVELUR EKKI FÖLLNU RAÐIRNAR.** Þrep 8 var **einnota markviss keyrsla með engri pipeline-breytingu**: `--ids` er ekki til í `run_extraction.py` og var **ekki** bætt við; leiðin var einnota driver. **Næsta inneignar-, net- eða API-bilun framleiðir því nákvæmlega sama gat aftur**, og það uppgötvast aðeins ef einhver les extraction-loggið. Þrjár leiðir, engin valin: (a) `--ids`-flagg (eða `--retry-failed`) í `run_extraction.py` sem les föllnu hash-in úr gærkvöldsloggi; (b) þrálát biðröð í DB (röð sem féll fær `pending`-merki í stað þess að hverfa); (c) láta `CHAIN DEGRADED:n` merkið (§5C-5) kveikja á endurkeyrslu daginn eftir. **(b) er eina leiðin sem er óháð loggskrám** og hún er líka sú eina sem býr til nýjan DB-flöt — sem er sjálfstæð ástæða til að hugsa hana með cc105-reglunni. Ekkert af þessu fær go hér. Heimild: `docs/fable_prep/audits/AGUST_ENDURTHJALFUN_FLIPP_CC104_20260806.md` þrep 8 („Óbreytt skv. GO"); `app` commit `f5b45e6`.

- **`SET TRANSACTION READ WRITE` VERÐUR AÐ VERA FYRSTA STÆÐAN — og það á við um HVERN skrif-driver, ekki bara migrationir.** Þrep 8 féll í fyrstu atrennu á `ActiveSqlTransaction: transaction read-write mode must be set before any query` af því að **fetch-ið opnaði transaction á SKRIF-tengingunni** áður en skrif-fallið náði að setja stæðuna. Mynstrið sem heldur (og sem nætur-driverinn notar): **fetch á read-only tengingu, skrif á rw-tengingu — aldrei sömu.** Þetta er nú þriðja birtingin á pooler-gildrunni (cc86, cc94-æfingarnar, hér) og á heima í yfirlestri á öllum skrif-driverum sem eru til: einnota skriftur, `phase_d*`-mynstrið og `precompute`-skriftur sem skrifa í Supabase. **Yfirlesturinn er ódýr (grep á `SET TRANSACTION READ WRITE` og hvað kemur á undan honum í hverri transaction) og hefur ekki verið gerður.** Heimild: `AGUST_ENDURTHJALFUN_FLIPP_CC104_20260806.md` þrep 8 (atvikskaflinn); `feedback_set_transaction_read_write_verdur_ad_vera_fyrsta`.

- **VERK SEM LIFIR AÐEINS Í LOTUMINNI ER VERK SEM HVERFUR.** Þrep-8-liðurinn fannst **hvergi** í `docs/PLANNING_BACKLOG.md` né `verdmat-ai/docs/BACKLOG.md` þegar hann var framkvæmdur — hann lifði aðeins í cc103-minninu, og sá sem framkvæmdi hann tók sérstaklega fram að skráning hans væri bókunar-ákvörðun eiganda. **Það er nú gert (hér og í DECISIONS §5C-5/§5C-22).** Reglan sem þetta setur: **liður sem morgunvakt eða read-only lota finnur og telur verk á að rata í PLANNING_BACKLOG í sömu lotu og hann finnst — minnið er vísir, ekki bókhald.**

### Viðauki cc105 (logged 2026-08-07) — RLS: það sem stendur eftir FASA 2a

- **SUPPORT-BEIÐNI TIL SUPABASE UM `public.spatial_ref_sys` — MÁ FLJÓTA MEÐ FYRSTU RAUNVERULEGU SUPPORT-BEIÐNI.** Ákvörðun eiganda 07.08: **ekki að sinni** sem sjálfstætt erindi. Taflan er eina færslan sem eftir stendur undir `rls_disabled_in_public` og hún er **ósnertanleg af okkur**: eigandi er `supabase_admin`, svo `ENABLE ROW LEVEL SECURITY` fellur á raunreyndu `42501 must be owner of table spatial_ref_sys`, og REVOKE-varaleiðin er þögul núll-aðgerð (postgres hefur ekki GRANT OPTION — mælt `false`) sem lokaði hvort eð er engu því ACL ber `=r/supabase_admin`, þ.e. **SELECT til PUBLIC**. Raunveruleg lokun krefst þess að supabase_admin fjarlægi PUBLIC-grantið og/eða kveiki RLS — sama leið og cc72 fór þegar support afturkallaði rit-sagnirnar. **Þangað til stendur flaggið KNOWN-ACCEPTED með mælingu** (les-eingöngu, opinber EPSG-uppflettitafla, engin app-gögn; cc55-kanaríinn vaktar áfram rowcount/srid-rek og er óháður réttindum). Þegar næsta support-erindi verður sent af annarri ástæðu á þessi liður að fljóta með. **„Resolve issue"-hnappurinn í advisory-póstinum má ALDREI nota** — hann lokar ábendingunni án þess að laga neitt. Heimild: `docs/HALT_SKIL_RLS_GAT_CC105_FASI2A_20260807.md` §3; DECISIONS 2026-08-07 (cc105-reglan); CLAUDE.md (cc72-bókunin).

- **FASI 2b BÍÐUR STEFNUFUNDAR UM DEFINER-MYNSTRIÐ — ekkert go.** Óhreyft: átta `SECURITY DEFINER`-view (ERROR-stig, sex þeirra les /eign+dashboard sem anon — þau eru **vísvitandi opnunarleiðin** yfir default-deny töflurnar, ekki gleymska), tíu semantic-MV með anon-grant (/markadur les þær) og þrjár MV **án** grants (`v_postnr_prices_yearly`, `v_street_activity`, `v_street_directory` — grant-sagan er handvirk, sbr. cc101-liðinn (a) hér að ofan), `st_estimatedextent` (anon-EXECUTE, síðan notar hvergi — má REVOKE áhrifalaust), ófest `search_path` á þremur föllum (`search_properties_grouped` er anon-kallanlegt um /leit), HIBP-vörnin af (Auth ER í notkun — 5 notendur — svo N/A á ekki við), og víðari `authenticated`-grant á `scraper.v_leit_listings`/`v_eign_virk_auglysing` en notkunin krefst (service_role eingöngu). **Meginniðurstaða FASA 1 sem stýrir þessu öllu: anon-lykillinn er BURÐARVIRKI síðunnar** (/leit keyrir hrá REST-köll með honum), svo fjölda-REVOKE á view/MV-flötinn bryti síðuna — hver hlutur þarf kortlagningu. Heimild: `docs/HALT_SKIL_RLS_GAT_CC105_FASI1_20260806.md` §2–§4.

### Viðauki cc112 (logged 2026-08-07) — F1-VÖRNIN ER KOMIN: hliðið stöðvar blæðinguna, þrennt stendur eftir

Nætur-verðmatið skrifaði í `scraper.listing_valuations` úr **öðrum heimi en framleiðslan**: adapterinn (`phase_d3_score_extract`) hleður `D:\iter4a_*.lgb` (154 eiginleikar, óhreyfðir frá 21.04) og stimplar `iter4_final_v1`, meðan `pipeline_config.model_version` ber `iter4r_20260805_reglaR_strukt` (156). Mælingin bar hlið gegn þessu síðan cc47 (`model_quality_eval.py:130-134`) — **skrifleiðin bar ekkert**. cc112 setti sama hlið á skrifleiðina (`extraction_engine.assert_write_world_matches_live`, kallað sem fyrsta stæðan í `value_listings`): fellur með `ModelWorldMismatch`, exit ≠ 0, engin skrif. **Umfangið var HLIÐIÐ EITT** — hvorki endurtenging, endurreikningur né önnur pipeline-breyting fylgdi, og þess vegna stendur þrennt eftir:

- **(i) ENDURTENGING NÆTUR-VÉLARINNAR VIÐ iter4r-ARTEFAKTANA + SERVING-LAGIÐ — sér verk með eigin sannprófunarkröfu.** Hliðið stöðvar blæðinguna en tengir ekkert: **frá og með cc112 skrifar nætur-verðmatið EKKERT og keðjan ritar `CHAIN FAIL (extraction)` hverja nótt** þar til þetta er gert (útdrátturinn heldur áfram óskertur — mælt, sjá (iii)-heimildina). Verkið er ekki einnar línu skipti á slóð: adapterinn er **freeze-anchored** (`FREEZE_ANCHOR_YM='2026-09'`, `PRED_VALUATION_YM='2026-07'`, `_score_iter4` + `load_models_freeze_anchored`) og var smíðaður til að endurgera frystu spárnar bæti fyrir bæti. Sannprófunarkrafan sem verkið verður að bera: **156 eiginleikar (ekki 154), kvörðunarlagið með (segcal + conformal á nýja grunninum), og samanburður við lifandi `public.predictions` á sama akkeri** — parity-krafan sem cc47 setti (D2 parity 0,0000 %) á að endurtakast á nýja heiminum, annars er „endurtenging" bara nýr ómældur heimur. Athuga þarf í leiðinni hvort `MODEL_VERSION`-stimpillinn eigi áfram að koma frá adapternum eða beint úr `pipeline_config` — eftir endurtengingu er tvöfaldi upprunninn óþarfur og hliðið verður sjálfkrafa satt. Heimild: `extraction_engine.py` (cc112-hliðið); `model_quality_eval.py:114-134`; cc110 morgunvakt S1.

- **(ii) ENDURREIKNINGUR 953 RAÐANNA EFTIR ENDURTENGINGU — V2-fordæmi cc94 B2.** Raðirnar sem skrifaðar voru eftir `2026-08-06T12:24:26Z` (**953, mælt aftur 07.08: óbreyttar**) bera `iter4_final_v1` en voru frystar eftir að framleiðslan flutti sig; **103 af 478 eignum (21,5 %) eru eignir sem regla R endurflokkaði**, svo tölurnar eru ekki bara gamlar heldur á röngum flokki. Leiðin er bókuð og fordæmið til: **eyða + endurreikna á sama akkeri, gömlu gildin í audit-töflu fyrst** (nákvæmlega V2-mynstrið úr cc94 B2, sbr. `listing_valuations_pre_cc94b2`). **Röðin er BINDANDI: (i) á undan (ii)** — endurreikningur í gegnum ótengda vél endurframleiðir sama frávikið með nýrri dagsetningu. Athuga við framkvæmd að safnið í heild er **21.595 raðir, allar `iter4_final_v1`** — hvort endurreikningurinn eigi að ná til alls safnsins eða aðeins 953 er sér ákvörðun (eldri raðir voru frystar þegar `iter4_final_v1` VAR framleiðslan og eru að því leyti réttar á sínum tíma). Heimild: cc110 morgunvakt S1; `COMPONENTS_SPILLING_CC94` §11.4 (V2-mynstrið).

- **(iii) YFIRLESTUR: HVAÐA AÐRAR SKRIF-VÉLAR SKORA ÁN ÚTGÁFUHLIÐS?** cc112 lokaði **einum** skrifleið — þeirri sem var mæld. Enginn hefur talið hinar. Verkið er grep yfir alla scorer/skrif-drivera (`app/scripts/phase_d*`, einnota skriftur á `D:\`, `precompute`-skrifturnar, allt sem kallar `_score_iter4` / `load_models_freeze_anchored` / skrifar í töflu með `model_version`-dálki) og spurningin fyrir hvern: **ber hann útgáfuhlið, og ef ekki — hvað hefur hann skrifað síðan flippið?** Þetta er systurverk við `SET TRANSACTION READ WRITE`-yfirlesturinn sem þegar er bókaður í Viðauka cc108-A (sami skrá-listi, sami grep-hringur) og **á að framkvæmast með honum, ekki sér**. Ódýrt, read-only, og fyrsta skrefið er talning en ekki viðgerð.

### Viðauki cc116 (logged 2026-08-08) — liður (ii) FRAMKVÆMDUR; tvennt sem mælingin skildi eftir

Liður (ii) hér að ofan er **framkvæmdur 07.08 af cc116**: 953 raðirnar endurreiknaðar á `iter4r_20260805_reglaR_strukt`, `iter4_final_v1` 21.595→20.642 (mengið 953→0), heildartala `scraper.listing_valuations` **21.605 óbreytt**, parity `expected_base` == lifandi `predictions.real_pred_median` 645/645 með max|Δ| = 0 kr, kostnaður $0,00. Gömlu gildin liggja á diski utan git (`D:\_audit\cc116_endurreikningur\listing_valuations_pre_cc116_20260807T2100Z.{csv,jsonl}`, 953 raðir, sha256[:16] `576c7d2e6d319d36` / `d73e4e419ea7225f`). Audit: `docs/fable_prep/audits/ENDURREIKNINGUR_953_CC116_20260807T2340Z.md`. Frávik frá forsendu liðar (ii): talan „103 af 478 eignum" mælist í dag **107 af 507 (21,1 %)** gegn `properties_canonical_pre_cc78` — hlutfallið stenst, nefnarinn ekki. **Tvennt sem endurreikningurinn mældi er verk en ekki niðurstaða og á heima hér:**

- **(a) `EXCLUDE`-HALINN — FLOKKUR UTAN TAXONOMÍUNNAR DREGUR DREIFINGARTÖLURNAR UPP.** Af 953 endurreiknuðum röðum sitja **67 raðir á 47 eignum með `canonical_code = 'EXCLUDE'`**, og sá hópur ber **p95 |Δ| 33,76 %** gegn 25,46 % hjá íbúðarhúsnæði (miðgildi |Δ| 4,86 % gegn 3,60 %, max 37,95 % gegn 31,39 %). **Öll fimm stærstu frávik mengisins eru á `EXCLUDE`-eignum** (mest −37,95 %, fastnum 2356622; fjögur samliggjandi fastnúmer 2537169/71/76/77 öll á −33,76 % með sama grunngildi). Þetta er í sjálfu sér væntanlegt — `EXCLUDE` er utan þeirrar taxonomíu sem líkanið er akkerað á — en það hefur tvær afleiðingar sem enginn hefur tekið afstöðu til: **(1)** p95-talan í hverri dreifingarmælingu á þessum fleti er dregin upp af flokki sem á minnstan rétt á að vera þar, svo „p95 25,7 %" um mengið í heild er blandað tal; **(2)** stærri spurningin er hvort `EXCLUDE`-eignir eigi yfirhöfuð að fá **fryst verðmat** í `scraper.listing_valuations` — biðröðin (`fetch_extracted_listings_to_value`) síar **ekki** á `canonical_code`, svo hver `EXCLUDE`-auglýsing sem ber útdrátt fær frysta tölu úr líkani sem var aldrei þjálfað á hana. Verkið er **fyrst talning yfir alla töfluna** (hve margar af 21.605 sitja á `EXCLUDE`, ekki bara í þessu mengi) og svo ákvörðun um hvort sía eigi þær úr biðröðinni, merkja þær, eða láta standa og undanskilja þær í dreifingarmælingum. **Ódýrt og read-only fyrsta skrefið.** Heimild: `ENDURREIKNINGUR_953_CC116_20260807T2340Z.md` §5.

- **(b) 20.642 SÖGULEGU RAÐIRNAR STANDA ÓENDURREIKNAÐAR — MEÐVITUÐ ÁKVÖRÐUN, EKKI GLEYMSKA.** Raðirnar undir `iter4_final_v1` með `valued_at < 2026-08-06T12:24:26Z` voru frystar **þegar `iter4_final_v1` VAR framleiðslan** og eru að því leyti réttar á sínum tíma; cc116 snerti þær ekki og afmörkunin (`>= flipp`) var valin til að verja þær. Sér-ákvörðunin sem liður (ii) bókaði — „hvort endurreikningurinn eigi að ná til alls safnsins" — er hér með **svarað NEI fyrir cc116 og stendur opin sem sjálfstætt val**. Rökin gegn því að endurreikna þær: frysta talan er **söguleg heimild** um hvað vélin sagði á sínum tíma, og endurreikningur breytir henni í endursögn — `scraper.v_expected_vs_real` ber `base_pct_error` gegn raunverði, svo endurreikningur á seldum eignum myndi mæla nýtt líkan gegn gömlum sölum og líta út eins og söguleg nákvæmni. Rökin með: taflan ber þá **tvo stimpla hlið við hlið til frambúðar** og hver neytandi verður að vita af því (mælt: cc116 skildi eftir 20.642 : 963 skiptingu). **Ef ákvörðunin verður að endurreikna er fordæmið til og kostar $0,00** (allir útdrættir eru til; sami rofi, sama skrifta `D:\_audit\cc116_endurreikningur\cc116_endurreikningur.py` með breyttri afmörkun) — en **frávikadreifingin yrði ekki sambærileg** við cc116-mælinguna, því þær raðir voru frystar á ÖÐRU akkeri og munurinn bæri bæði líkanaskiptin og akkerisfærsluna. **Ekkert go; liðurinn er bókaður svo þögnin sé val en ekki gleymska.** Heimild: `ENDURREIKNINGUR_953_CC116_20260807T2340Z.md` §7; Viðauki cc112 liður (ii).

### Viðauki cc111 (logged 2026-08-08) — myndasækjarinn er í gagninu; þrennt stendur eftir

Bakfyllingin er búin: gatið **101.390 → 11.370**, 22/22 hrinur HEILAR, `augl-myndir/` **299.700 hlutir / 73.816.442.100 b**, manifestið **990.147 línur** eftir slot-útvíkkunina 07.08. Sækjarinn (`scripts/myndasaekjari.py`) og skráningarskriftan (`scripts/skra_myndasaekjari_task.ps1`) eru committaðar hér. Þrennt fær **ekkert go** en er bókað svo það hverfi ekki úr lotuminni:

- **RAUNÞAK mbl-LOKUNAR ER 87,2%, EKKI 100% — 11.367 SLÓÐIR ERU VARANLEGA DAUÐAR.** Mælt á cc109-nefnaranum (mbl 88.669 slóðir): **sótt 77.300, týnt 11.369**, þar af **404 = 11.367** og aðeins **2 endurreynanlegar** (502×1, 504×1). 77.300/88.669 = **87,18%**. cc109 mældi 3.337 `lost` og gaf þar með til kynna ~96% þak; raunveruleikinn er **3,4× fleiri dauðar slóðir**. **Þetta er ekki bilun og á ekki að laga** — mbl fjarlægir myndir af `fs-pool` og slóðin deyr; það sem við náðum ekki áður en hún dó næst aldrei. Liðurinn er bókaður svo að **framtíðarmæling lesi 87,2% sem ÞAKIÐ en ekki sem ólokið verk**, og svo að enginn setji af stað „lokum síðustu 12%"-keyrslu sem getur ekki heppnast. ⚠️ **NEFNARAVARÚÐ:** `myndavisir.db` telur **12.106** mbl-slóðir týndar yfir *allar* slóðir sem hafa verið reyndar (þ.m.t. þær 213.843 sem voru sóttar fyrir manifestið); **11.367 er talan á cc109-gatinu einu**. Tölurnar tvær eru ekki í mótsögn — þær hafa ólíka nefnara. Sbr. `feedback_vidmid_a_eign_ekki_a_rod`. Heimild: `D:\_audit\cc111_myndasaekjari\BAKFYLLING_CC111_20260807.md`; `myndavisir.db.slod`.

- **MANIFEST-SPEGLUNIN Á AÐ RENNA INN Í NÆTURAFRITSVERKIÐ FORMLEGA VIÐ NÆSTU SNERTINGU ÞESS.** `myndamanifest/` speglast í dag á R2 **innan hverrar hrinu sækjarans sjálfs** (`MANIFEST_R2`, cc111 liður 0) — það var rétt ákvörðun þá (bætin lifa tvöfalt, kortlagningin líka) en það þýðir að **spegillinn hvílir á því að sækjarinn keyri**. Keyri hann ekki, eldist spegillinn þögult. `backup_paths.json` nær enn hvorki yfir `myndamanifest/` né `image_store` (cc97-liðurinn stendur óbreyttur). **Aðgerðin er ódýr og á ekki að vera sér-verk:** næst þegar `backup_nightly.py` er snert hvort eð er, fara báðar möppur inn í `backup_paths.json` og speglunin í sækjaranum verður belti en ekki eina ólin. **Ekkert að gera fyrr en þá.** Heimild: `project_myndasaekjari_fasi1_cc111`; `project_augl_myndir_spegill_cc97` („HVAÐ ÞETTA LEYSIR EKKI").

- **3 ENDURREYNANLEGAR SLÓÐIR — ENDURREYNA EFTIR ≥7 DAGA, EKKI FYRR.** Þrjár slóðir í cc109-gatinu féllu á **5xx, ekki 404**: mbl 502×1, mbl 504×1, myigloo 502×1. 5xx er ástand hýsils, ekki dómur um myndina, svo þær eru **eina raunverulega ólokna verkið** í öllu gatinu. Biðin er sett á ≥7 daga af ásettu ráði: styttri endurtilraun mælir sama hýsilástandið aftur og eyðir tilraun. Sækjarinn velur þær sjálfkrafa (`--bakfylling` les vísinn, `sokn_stada='tynt'` með 5xx er endurreynanlegt), svo aðgerðin er **ein keyrsla, engin breyting á kóða**. Náist þær ekki heldur þá eru þær varanlega tapaðar og bætast við 11.367-talinguna. Heimild: `myndavisir.db.slod` (mælt 2026-08-08); `gat_maeling.json`.

### Viðauki cc121 (logged 2026-08-08) — VERÐMATS-BAKFYLLINGIN Á PÁSU; endurræsing er ein tala

Verðmats-hrinan í næturkeðjunni er **á PÁSU frá 08.08 að ákvörðun eiganda**. `EXTRACT_VALUE_LIMIT` í `scripts/nightly_delta_chain.sh` er sett í `0`, sem skelin þýðir í `--skip-valuation`; **biðröðin var 18.734 raðir við pásu** (mælt 08.08 á lifandi DB, sama tala og cc119). `scraper.listing_valuations` stóð í **23.605 röðum** við pásu (20.642 `iter4_final_v1` + 2.963 `iter4r_20260805_reglaR_strukt`). **Útdrátturinn er ÓSNERTUR** (`EXTRACT_FORWARD=200`, Haiku) — hann er ferskleiki, ekki bakfylling. **ENDURRÆSING = ÞESSI EINA TALA (`0` → `2000`)** og krefst engrar annarrar breytingar.

**PÁSAN ER 0 Í SKELINNI EN ALDREI 0 Í PYTHON — MÆLD ÁSTÆÐA.** `--value-limit 0` er **ÓTAKMARKAÐ, ekki ekkert**: `fetch_extracted_listings_to_value` byggir LIMIT-liðinn með `{('LIMIT %d' % int(limit)) if limit else ''}` (`extraction_engine.py:188`) og `0` er falsy, svo liðurinn fellur út. Mælt beint á lifandi DB áður en nokkuð var skrifað: **`limit=None` → 18.734, `limit=0` → 18.734, `limit=5` → 5**. Að setja þakið í 0 og senda það niður hefði því skrifað **18.734 raðir í nótt í stað engra** — þveröfugt við ætlunina. Þess vegna var farin leið **sér-rofa** (`--skip-valuation` í `run_extraction.py`) og skelin ber þýðinguna á `[ "$EXTRACT_VALUE_LIMIT" -gt 0 ]`, þar sem 0 er ótvírætt. Leiðin „if-grein í `run_extract()` sem sleppir verðmats-kallinu" var **ekki tæk**: verðmatið er ekki sér kall í keðjunni heldur þrep innan sama `run_extraction`-ferlis sem `--forward` keyrir, svo það er ekkert kall á skel-stigi til að sleppa. Gildran er skjalfest við rofann sjálfan svo hún verði ekki „einfölduð" til baka. **Falsy-hegðun `--value-limit` sjálfs var EKKI leiðrétt** (umfang var ein breyting) og stendur því sem lifandi gildra fyrir næsta lesanda — hún er bókuð hér sem sjálfstæður, ódýr liður.

**PÁSAN ER ÁKVÖRÐUN UM AÐFERÐ, EKKI FRESTUN.** Bakfyllingin á að klárast í **EINNI mannaðri keyrslu**, ekki í ~300-raða skömmtum yfir 11 nætur. Rökin: **(a)** ein keyrsla gefur **EINA hreina frávikadreifingu á sama akkeri** — ellefu skammtar gefa ellefu ósambærilegar; **(b)** kostnaður er **$0,00 hvort sem er** (útdrættirnir eru til, engin Haiku-köll í verðmats-þrepinu); **(c)** mönnuð keyrsla ber **HALT og rowcount-sönnun**, ómönnuð næturhrina hvorugt; **(d)** endurkoman (~300/nótt vegna `lysing`-hash-skilgreiningarinnar) **hverfur sem vandamál** þegar biðröðin er tæmd í einu lagi. Biðröðin er bakfylling á eldri auglýsingum sem **enginn notendaflötur les** (aðeins `scraper.v_expected_vs_real` + ferskleikalínan á `/ops`).

- **FORSENDA FYRIR MÖNNUÐU KEYRSLUNNI: cc120 VERÐUR AÐ VERA AFGREITT FYRST.** Miðsæknin — `expected_base` ber `real_pred_median` meðan `/eign` og `/leit` birta `real_pred_mean`, **|Δ| > 10 % á 24.969 eignum** — er óafgreidd. Yrði bakfyllingin keyrð á undan frystum við **18.734 raðir á skilgreiningu sem gæti þurft að endurreikna**: nákvæmlega sama vinnan og cc116 vann á 953 röðum, bara tvítugfalt stærri. Röðin er því **bindandi: cc120 → bakfylling.**
- **ENDURKOMAN SJÁLF (~300/NÓTT) STENDUR ÓMÆLD SEM SJÁLFSTÆÐ SPURNING.** Biðröðin er skilgreind á `substr(md5(l.lysing), 1, 12)`, svo hver breyting á auglýsingatextanum framleiðir nýjan `lysing_hash` og röðin kemur aftur inn. **Hve mikið af ~300/nótt er raunveruleg textabreyting og hve mikið er hash-flökt (hvítstafir, HTML-hreinsun, endurbirting sama texta) er ómælt.** Þetta ræður því hvort biðröðin **tæmist** eftir mönnuðu keyrsluna eða **stendur í jafnvægi** við endurkomuna — og þar með hvort pásan má fara af varanlega eða þakið þarf að standa áfram. Mælingin er read-only: bera `lysing`-texta saman milli tveggja `last_seen_at` fyrir sömu `source_listing_id` og telja hve margar hash-breytingar bera merkjanlega textabreytingu. **Ekkert go; bókað svo þögnin sé val.**
- **`--value-limit 0` SEM ÓTAKMARKAÐ ER ÓLEIÐRÉTT GILDRA.** Ein lína (`if limit` → `if limit is not None`) leiðréttir hana, en það var utan umfangs cc121 (ein breyting) og hún snertir biðraðar-fyrirspurnina sem var í banni. Á meðan stendur: **enginn má senda `--value-limit 0` handvirkt** í þeirri trú að það sé varúð — það er fullt safn. Keðjan getur það ekki (hún þýðir 0 í `--skip-valuation`), en handvirk keyrsla getur.

### Viðauki cc126 (logged 2026-08-11) — R2-GraphQL MÆLT: bæði ósamræmin leyst, cc122-taflan fellur á LIST

Lykillinn kom og mælingin var gerð: `r2OperationsAdaptiveGroups` + `r2StorageAdaptiveGroups` fyrir **19.07–11.08**, hrágögn vistuð á disk í `D:\_audit\cc126_r2_graphql\` (stimpill `20260811T222010Z`). Full skil: `R2_GRAPHQL_CC126_20260811.md`. **Vistunin er ekki snyrtimál — geymsluþol Cloudflare er 31 dagur, svo 19.07 dettur út 19.08 og cc87/cc97-speglanirnar 04.–05.08 detta út 4.–5. september; eftir það eru þessar skrár eina heimildin um þær utan okkar eigin bókhalds.** Dómsreglurnar voru forskráðar áður en lykillinn kom og eru endurbirtar óbreyttar í §9 skilanna til sannprófunar. **Fyrirvari á öllum tölum: Cloudflare námundar í næsta tug** — hver einasta tala sem datasettið skilar er margfeldi af 10, svo tölur undir ~100 eru hávaði en ekki mæling.

- **(i) LEYST: „3,13 M" ER HEILDIN. Þekja cc122 stendur í 94,60 % (nefnari 3.138.170).** Mælt Class A fyrir reikningstímabilið 01.–08.08 = **3.138.170** — „3,13 M" upp á 0,3 %. Lesningar (b) og (c) eru **útilokaðar af mælingu**: uppsafnaður fjöldi nær aldrei 4 milljónum, hvorki 08.08 (3.138.170) né 11.08 (3.164.190). Júlí-hluti gluggans er **720 aðgerðir alls**, sem staðfestir sjálfstætt að allur massinn tilheyrir ágúst-tímabilinu. **Matið stenst, nefnarinn er nú mældur.**

- **KOSTNAÐARLÍNAN ER ENN ÓLEYST OG ER ÖNNUR SPURNING — FRÍÞREPIÐ GENGUR EKKI UPP.** Aðgerðaspurningin er svöruð, en $13,50 er það ekki: **með fríþrepi nær Class A-línan aldrei $13,50** (hæsta gildi alls mánaðarins er $9,74). Án fríþreps hittir $13,50 uppsöfnun 05.–06.08 ($13,57, 0,5 % frá) sem er samræmanlegt ef kostnaðarlínan sest 1–2 dögum á eftir teljaranum. **En sú lesning stangast á við hina hlið mælaborðsins:** Class B mældist 5.818.510, sem án fríþreps væri $2,09 og hefði birst sem lína — cc122 §2.4 bókar að engin þriðja lína var. Class B sýnir því fríþrep beitt meðan Class A sýnir það ekki. **GraphQL mælir aðgerðir, ekki reikningslínur, og Cloudflare birtir enga sögu uppgjörslína — þetta er ekki sannreynanlegt héðan.** Tveir kostir standa, hvorugur valinn: (1) kostnaðarlínan dregur ekki fríþrepið frá og sest á eftir; (2) „$13,50" í cc122 var ekki Class A-línan (**við erum að mæla gegn endursögn af mælaborði, ekki gegn skjámynd**). **Ágúst-reikningurinn sker úr og hann kemur af sjálfu sér.** ⚠️ **AFLEIÐING SEM ÞARF AÐ SKOÐA:** cc122 §6 byggir jafnvægistaktinn á því að 151.380 Class A/mán kosti **$0,00 því þær séu 15 % af fríþrepi**. Reynist fríþrepið ekki beitt er sá liður $0,68/mán og geymslan $10,39 (mælt 692,92 GB, ekki 681,09) — jafnvægið ~$11,07 en ekki $10,10, og bilið upp í $15-þakið þrengist úr 48 % í 35 %. **Tillagan „halda $15" stenst enn, en forsendan undir henni er í biðstöðu.**

- **(ii) LEYST: 07.08 BAR $0,49, EKKI $4,5 — ÓMÆLDA SKRIFLEIÐIN ER ÚTILOKUÐ MEÐ 9,2-FALDRI FJARLÆGÐ.** Mælt 07.08: 84.840 PUT + 24.080 LIST + 210 UploadPart = **109.130 Class A = $0,49** gegn bókuðum 96.667 = $0,44. **Munurinn er +12,9 %, ekki 10×.** Til að bera $4,5 hefði dagurinn þurft 1.000.000 aðgerðir. Tilgáta cc122 §3.2 (uppsöfnun en ekki dagsúla) er staðfest í þeim skilningi sem skiptir máli. **Uppruni tölunnar „$4,5" sjálfrar er hins vegar EKKI endurbyggjanlegur og verður það ekki** — uppsöfnunarferillinn sýnir ekkert $4,5 stökk milli neinna tveggja daga (stærsta er 04.08, $12,71), og til að rekja það þyrfti sögu uppgjörslína sem hvergi er birt. **Bókað sem takmörkun mælitækisins, ekki jafnað út með nálgun sem passar.**

- **(4) cc122-TAFLAN: PUT STENST (+2,12 %), LIST FELLUR (+528 %) — TAFLAN LEIÐRÉTT MEÐ MÆLDUM TÖLUM.** Á nefnara 3.138.170: **PUT mælt 3.010.820 = 95,94 %** (cc122 mat 94,2 % — innan ±5 % reglunnar, **STAÐFEST**); **LIST mælt 127.350 = 4,06 %** (cc122 mat 0,6 % — **FELLT, 6,3× vanmat**). **Óskýrt eftir aðgerðategund: 0.** Mælt Class A er 100 % rakið; „óskýrðu 5,2 %" voru ekki óþekktur uppruni heldur **vantalning okkar megin**. Athyglisvert: tilgátan sem cc122 var að fella — „listun ber kostnaðinn" — var **réttari en cc122 komst að** (4,06 % en ekki 0,6 %); hún fellur samt enn því PUT ber 95,94 %. **Niðurstaðan stendur, röksemdin var of sterk.**

- **(5) STIGVELDISLISTUNIN STAÐFEST SEM RÁÐANDI UPPSPRETTA (79 %).** Gapið á mældum nefnara er 169.483 (5,40 %), skipt í LIST-vantalningu **+107.085 (63 %)** og PUT-vantalningu **+62.398 (37 %)**. Af LIST-vantalningunni liggja **84.355 (78,8 %) á 04.08 einum**: mælt `ListObjects` þann dag = **89.650** gegn 5.295 bókuðum. Forskráða reglan krafðist þrenns og allt þrennt heldur — dagurinn er cc87-speglunardagurinn ✔, umfangið er tugþúsundir (55.637 + 34.013, þ.e. ein full stigveldisumferð plús rúmur helmingur af annarri) ✔, og þakið 55.637 × 2 = 111.274 heldur ✔. **Tilgáta cc122 §2.3.2 er staðfest af mælingu.** PUT-vantalningin (+2,1 %) er hins vegar **ekki rakin** — of lítil fyrir nýja skrifleið, of stór fyrir kornastærð; `objectName`-forskeytasundurliðun gæti rakið hana, var utan umfangs.

- **NÝR LIÐUR: SÆKJARINN LISTAR RÚMLEGA TVÖFALT Á VIÐ cc122-LÍKANIÐ.** Afgangurinn af LIST-vantalningunni (+22.730) liggur á 07.–08.08 og er ekki cc87-arfur heldur **lifandi einkenni**: mælt 07.08 = 24.080 listunarköll gegn ~6.200 sem líkan cc122 §2.2 spáir (2 × `r2_maeling` + 2 × `spegla_manifest` per hrina, ⌈N/1000⌉). **Sami galli birtist þrisvar í þessari lotu** — í (ii), í (4) og í (5) — og er því eitt verk en ekki þrjú. Þetta breytir engu um krónur (LIST-kostnaður sækjarans er $0,17/mán skv. cc122 §5 og tvöföldun hans er $0,34) **en það ógildir nefnarann sem T1-tillaga cc122 er reiknuð á**: „−50 % LIST" var reiknað á 616 köll/hrina sem mælast nær 1.300. T1-rökin (að hún **loki mælingargati** milli `eftir(k)` og `fyrir(k+1)`) standa óhögguð — aðeins sparnaðartalan er röng. **Fyrsta skrefið er read-only talning á raunverulegum fjölda listunarkalla per hrina, ekki viðgerð.**

- **NÝR LIÐUR: FÖTURNAR ERU ÞRJÁR, EKKI EIN.** `bucketName` sýnir `verdmat-backups` (99,50 % Class A), **`verdmat-einkasafn`** (0,49 %, allt á 11.08 — það er **cc124 að störfum**, 14.620 `CopyObject` + 1.020 `ListObjects`, allt `success`) og **`verdmat-backup` í eintölu** (10 `ListObjects`, öll **`userError`** — fatan er ekki til). Tvennt af þessu er verk: **(a)** einhver skipun einhvers staðar ber **rangt fötunafn** (innsláttarvilla gerð 07.08) — skaðlaust og gjaldfrítt en ódýrt að finna; **(b)** gagnlegt fyrir cc124: **geymslumælingin sest á eftir aðgerðamælingunni** (geymslupunktur kl. 21:30 sýndi enn `objectCount = 0` á einkasafninu meðan `CopyObject` voru þegar taldar), svo enginn á að staðfesta cc124 á geymslutölu samdægurs.

- **cc122 §2.4 UPPFÆRT: „TVEIR HEAD PER SKRÁ" VAR ÁLYKTAÐ, ER NÚ MÆLT.** cc122 tók sérstaklega fram að vélbúnaðurinn væri „ályktaður af hlutfallinu, ekki lesinn úr rclone-loggi". `actionStatus` les hann beint: `HeadObject` **success 3.089.870 + userError 2.711.700 = 5.801.570 = 1,968 HEAD per skrá**, og skiptingin ≈ eitt misheppnað + eitt heppnað per skrá er nákvæmlega mynstrið „tilvistarathugun á áfangastað (404 = `userError`) og svo gátsummu-lestur". **Ályktunin er staðfest af vídd sem cc122 hafði ekki aðgang að. 47 % allra Class B-aðgerða okkar eru `userError`** — venjulegur rekstur, en ósýnilegur í öllu okkar bókhaldi.

- **cc122 §2.5 UPPFÆRT: 10,6 GB GATIÐ ER OKKAR MEGIN, EKKI CLOUDFLARE MEGIN.** GraphQL mælir **692,92 GB / 2.955.341 hluti** (11.08 21:20Z) gegn mælaborðinu 691,73 GB — 0,17 % munur sem er hrein tímamismunun með þriggja daga vexti á milli. **Mælaborðið er staðfest**, svo frávikið gegn disksamtölunni 681,09 GB liggur á **okkar talningu**. cc122 bókaði það óskýrt og lét ósagt hvor hliðin bæri það; það er nú afmarkað verk í stað opinnar spurningar.

- **TILLAGAN UM VIKULEGAN GraphQL-LIÐ STENDUR OG ER STYRKT — MEÐ EINNI LEIÐRÉTTINGU (ekkert go).** Ný rök: **þrjár af fimm niðurstöðum þessarar lotu voru ósýnilegar í okkar bókhaldi** (LIST-vantalningin, 47 % `userError`, þriðja fatan) — það er skilgreiningin á óháðu hliði; gögnin **fyrnast á 31 degi** svo að lesa ekki er virkt tap; og `bucketName` sannaði sig strax á cc124. **Leiðréttingin:** fyrri tillaga um HALT við `Δ > 20 %` á heildina er **röng kornastærð** — PUT mælist innan 2,1 % meðan LIST er 528 % frá, svo eitt þak á heildina hefði þagað yfir LIST-gallanum (PUT drekkir honum í 95,9 % vigt). **Merkin verða að vera per fjölskyldu: PUT > 5 %, LIST > 25 %.** Sbr. `feedback_vidmid_a_eign_ekki_a_rod`. Bætt við: **ný `bucketName` → HALT** (fötur birtast án þess að nokkur bóki það) og `userError` **á Class A** > 1 % → aðvörun (Class B-userError er venjulegur rekstur og merkið á hvorki að þagga hann né gera hann að viðvörun). **Fyrirvarinn óbreyttur: liðurinn má aldrei verða heimild sem hrinubókhaldið er stemmt af sjálfkrafa** — gildi hans er að hann **er ósammála**, í dag um 169.483 aðgerðir.

### Viðauki cc128 (logged 2026-08-11) — FALSY-GILDRAN LOKUÐ: `--value-limit 0` þýðir nú EKKERT, ekki ALLT

Liðurinn „`--value-limit 0` SEM ÓTAKMARKAÐ ER ÓLEIÐRÉTT GILDRA" (cc121-kaflinn hér að ofan) er **AFGREIDDUR**. Lagfæringin er tvær línur: `if limit` → `if limit is not None` í `fetch_extracted_listings_to_value` (`scripts/extraction_engine.py`) og sama greining á prentlínunni í `scripts/run_extraction.py`, sem áður **þagði** um þakið þegar það var 0 — keyrsla með þaki 0 leit í logginu nákvæmlega eins út og keyrsla án þaks.

- **RAUÐSÖNNUN Á LIFANDI DB (read-only, sama fall, fyrir og eftir).** Fyrir: `limit=None → 20.270 · limit=0 → 20.270 · limit=5 → 5`. Eftir: `limit=None → 20.270 · limit=0 → 0 · limit=5 → 5`. Nefnarinn er stærri en cc121 mældi (18.734) því biðröðin hefur vaxið á þremur nóttum; **það sem sannar gildruna er að `None` og `0` voru SAMA talan**, ekki talan sjálf. Stimpillinn í báðum mælingum: `iter4r_20260805_reglaR_strukt` (bundinn af `load_serving_models` áður en biðröðin er sótt, cc113).
- **NEIKVÆÐ GILDI ERU HÖFNUÐ, EKKI TÚLKUÐ (ákvörðun cc128).** `--value-limit -1` fellur nú í argparse með skýrri villu og kóða 2. Þrír kostir voru til: láta það renna niður í `LIMIT -1` og falla á SQL-villu langt frá kallstaðnum; túlka það sem „ótakmarkað" eins og sums staðar tíðkast; eða hafna strax. Valið er það síðasta — **ótvírætt er betra en klókt**: sá sem skrifar -1 meinti annaðhvort 0 eða ekkert þak, og vélin á ekki að giska á hvort. Þar með ber rofinn nú þrjú aðgreind gildi og ekkert grátt svæði: **sleppt = ótakmarkað · 0 = engar raðir · n > 0 = n raðir · neikvætt = villa**.
- **PÁSAN ER ÓSNERT — SANNAÐ MEÐ ÞURRKEYRSLU, EKKI MEÐ LESTRI.** `nightly_delta_chain.sh --dry-run` prentar eftir sem áður `run_extraction --forward 200 --confirm --skip-valuation`. Keðjan þýðir sitt `EXTRACT_VALUE_LIMIT=0` áfram í sér-rofann (`-gt 0`) og sendir **aldrei** 0 niður í `--value-limit`; sú þýðing var rétt ákvörðun þegar hún var tekin og stendur óbreytt eftir lagfæringuna. **Háværa leiðin er áfram háværa leiðin**: `--skip-valuation` prentar sína eigin línu í næturloggið, meðan `--value-limit 0` myndi aðeins prenta „0 rows" — þögul pása sem enginn afturkallar. Lagfæringin breytir engu í næturkeyrslunni.
- **AFLEIÐING FYRIR MÖNNUÐU BAKFYLLINGUNA (bókað, ekkert go).** Skammta-keyrsla með `--value-limit n` er nú örugg í báðar áttir: þakið bítur eins og talan segir og logginn segir frá því. Forsendan úr cc121-kaflanum stendur ÓBREYTT engu að síður — **cc120 (miðsæknin) verður að vera afgreitt áður en 20.270 raðir eru frystar**; þessi lagfæring fjarlægir gildru, ekki forsendu.

### Viðauki cc127 (logged 2026-08-11) — KOSTNAÐARBÓKHALDIÐ LES RAUNNOTKUN; ÞAKIÐ BÍTUR LOKS VIÐ $10

Liðurinn úr cc125 §A2 er **AFGREIDDUR**. `run_extraction.py:36` bókaði kostnað sem `n_call × PER_CALL_USD` þar sem fastinn var 0,0071, meðan `extract_listing` skilaði raunnotkun (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` — `pilot_extract_v022.py:684-691`) sem kallandinn henti á gólfið. Bókað er nú summa raunkalla; fastinn stendur eftir sem forspá og fallback, og áætlaði hlutinn er **talinn sér og merktur** í logginu.

- **RÓTIN VAR ELDRI EN FASTINN OG HÚN VAR ÞEGAR BÓKUÐ.** `calc_cost()` í `D:\pilot_extract_v022.py` dró cache-teljarana FRÁ `input_tokens` (`uncached_input = input - cache_read - cache_creation`) í þeirri trú að teljararnir skarist. Þeir eru **aðskildir og samlagnir** — `input_tokens` er þegar ócacheaði afgangurinn einn — svo liðurinn varð nær-núll eða neikvæður og $1/MTok-taxtinn féll niður á stórum hluta inntaksins. **DECISIONS.md bókaði þetta 2026-04-19** („Batch extraction cost vandamál", vanmat ~2,4×, ógreiddur höfuðstóll −$142,80) og **skrifaði réttu formúluna niður — en lagaði aldrei kóðann.** Fastinn 0,0071 er beinn afkomandi þess vanmats; 2,4× þá og 2,8× nú er sama bilunin, ómæld í fjóra mánuði. **Lexían er ekki um formúlu heldur um bókun: færsla sem lýsir viðgerð er ekki viðgerð.** Sbr. `feedback_hlid_a_maelingu_en_ekki_a_skrifleid`.

- **`pilot_extract_v022.py` ER UTAN GIT OG ÞAÐ ER NÚ BURÐARVIRKI, EKKI TILVILJUN.** Skráin býr á `D:\` sem er ekki git-safn, en `extraction_engine`, `batch_extract` og `model_quality_eval` flytja öll `calc_cost` inn úr henni. Viðgerðin í cc127 er því **hvergi útgáfustýrð** og ekkert hlið ver hana gegn því að verða yfirskrifuð. Afrit fyrir viðgerð liggur í scratchpad lotunnar. **Verkið sem eftir stendur: flytja `pilot_extract_v022.py` (eða a.m.k. verðskrána + `calc_cost`) inn í `app/scripts/` þar sem git sér hana.** Ekkert go.

- **FORSPÁ SEM VANMETUR ER ÞAK SEM LEKUR — MÆLT, EKKI ÁLYKTAÐ.** Þakið verður að umreikna „dollarar eftir" í „köll sem má kaupa" áður en nokkurt kall er gert, svo forspá er óhjákvæmileg. Fyrsta tilraun cc127 setti hana á efri mörk mælda bilsins ($0,0200) og **þurrkeyrslan felldi hana**: rauðsönnunin mældi $0,020717/kall, svo 500 leyfð köll hefðu endað í $10,36. Gildið er nú **$0,0225** (versta mælda tilvik + ~9%). Þurrkeyrsla nærri þaki: versta sviðsmynd endar í **$9,99** gegn **$29,17** á gamla fastanum. Talan $10 er óbreytt — merkingin lagaðist.

- **FASTINN GETUR ALDREI VERIÐ VERÐ, AÐEINS ÞAK — OG MÆLINGIN SÝNIR ÞAÐ.** Sama hrinan kostaði **$0,019430/kall með heitt skyndiminni og $0,020717/kall með kalt** (eitt cache-skrif, 10.295 tókenar, deilist á hrinuna). Kostnaður per kall er fall af skyndiminnis-hita og lengd lýsingar (output er 47,3% kostnaðar), ekki fasti. Þess vegna er bókunin raunnotkun.

- **ÞAKIÐ ER ENN FORSPÁ Á HRINU, EKKI STÖÐVUN Í MIÐRI HRINU (ómælt, ekkert go).** Hliðið reiknast **einu sinni, í upphafi keyrslu**. Bíti forspáin ranglega — óvenju langar lýsingar, kalt skyndiminni alla hrinuna — er ekkert sem stöðvar hrinuna í miðjum klíðum; skekkjan afmarkast af `(raun − forspá) × N` og er í dag varin af 9% svigrúmi og því að nóttin kaupir aðeins 200 köll (~$4,1 af $10). **Hörð trygging krefðist stöðvunar inni í `extract_and_store` þegar uppsafnaður raunkostnaður nær þakinu** — það er breyting á hegðun þaksins, ekki á merkingu þess, og var utan umfangs cc127.

- **`model_quality_eval.py:954` BER SAMA FOSSILINN, ÓSNERTUR.** Sama útdráttarleið (`extract_listing`), sama fleygða `usage`, sama `round(n_calls * 0.0071, 4)`. Hann **stýrir engum útgjöldum** (skilar tölu í gæðaskýrslu, ekki í dagsþak), svo hann var skilinn eftir viljandi frekar en að víkka umfang cc127. **Meðan hann stendur eru kostnaðartölur í gæðaskýrslum ~2,8× of lágar.** Viðgerðin er sama mynstur og hér: safna `calc_cost(usage)` per kall. Ekkert go.

### Viðauki cc123 (logged 2026-08-11) — MIÐSÆKNIN ER ÁKVEÐIN (kostur (a)); FRAMKVÆMDIN ER SÉR LOTA

Borðið kvittaði 11.08 á **kost (a): allt á `real_pred_mean`** — sjá `DECISIONS §5D-1` fyrir mælinguna, rökin, kostnað (b)/(c), bjaga-liðinn og ómælda gatið. **Ákvörðunin er tekin; breytingin er EKKI gerð.** Þrennt fer hér inn og ekkert af því ber go.

- **(i) FRAMKVÆMDIN ER SÉR LOTA MEÐ EIGIN ROWCOUNT-SÖNNUN — HÚN MÁ EKKI FLJÓTA MEÐ ANNARRI VINNU.** Breytingin er lítil í línum talið og **einmitt þess vegna hættuleg**: `eb`/`ex` í `value_listings` lesa `real_pred_median` (`scripts/extraction_engine.py:316–317`) og fara í `real_pred_mean`. En **hún er ekki ein lína, og sá sem heldur það fellir hliðið**: D2-parity-hliðið í `scripts/model_quality_eval.py` sækir `p.real_pred_median AS frozen_median` (`:557–576`) og ber það saman við adapter-grunnlínu (`:874–881`) — það er hliðið sem sannar að vélin skori úr sama heimi og framleiðslan (cc113). **Sé aðeins vélin færð mælir hliðið `mean` gegn `median` og fellur á hverri keyrslu.** Umfang lotunnar er því: (1) báðar línur í `extraction_engine`, (2) D2-hliðið fært á sama dálk, (3) MV-refresh/`scraper.v_expected_vs_real` endurmæld, (4) **rowcount fyrir/eftir á `scraper.listing_valuations` per `model_version`** og (5) mæld frávikadreifing gamalla gilda gegn nýjum á sama sniði og cc116 skilaði (`max|Δ|`, p95, hlutfall óbreyttra). Fordæmið er til og kostar **$0,00** — allir útdrættir eru til, engin Haiku-köll í verðmats-þrepinu; skriftan `D:\_audit\cc116_endurreikningur\cc116_endurreikningur.py` er sniðmátið. **Gömlu gildin fara á disk utan git ÁÐUR en nokkuð er skrifað** (cc116-reglan) og skrifleiðin fylgir `feedback_insert_first_thegar_lykillinn_greinir` ef einkvæmnislykillinn greinir.

- **(ii) RÖÐIN VIÐ BAKFYLLINGUNA ER ÁFRAM BINDANDI — FORSENDAN FÆRÐIST, HÚN HVARF EKKI.** cc121-kaflinn hér að ofan batt: *„cc120 verður að vera afgreitt fyrst"*. **Sú forsenda er nú hálfnuð, ekki uppfyllt.** cc120 er afgreitt sem ÁKVÖRÐUN (§5D-1) en `expected_base` ber enn `real_pred_median` í kóða og í öllum 23.605+ frystu röðunum. Yrði mannaða bakfyllingin keyrð núna frysti hún **yfir 20.270 raðir** (biðröðin mæld 11.08 af cc128) á dálki sem er þegar ákveðið að skipta um — nákvæmlega sama vinnan og cc116 vann á 953 röðum, tuttugufalt stærri, og með þeirri viðbót að hún væri unnin **eftir að við vissum betur**. Röðin er því **bindandi og uppfærð: (a)-framkvæmdin (liður i) → bakfylling.** Pásan (`EXTRACT_VALUE_LIMIT=0` → `--skip-valuation`) stendur óbreytt á meðan og endurræsingin er áfram ein tala (`0` → `2000`). **Spurningin sem cc116 skildi eftir opna — hvort endurreikna eigi 20.642 sögulegu `iter4_final_v1`-raðirnar — er ÓSNERT af þessari ákvörðun** og verður að svarast sérstaklega; (a) breytir hvaða dálk NÝJAR raðir bera, ekki hvað gamlar raðir sögðu á sínum tíma.

- **(iii) HÖFUÐGAPIÐ ER 3,2× STÆRRA Á BIRTINGARSLÓÐ EN Í ARTIFACTINU — ÓMÆLT, SÉR MÁL.** Á sömu 1.165 eignum mælist `dlog` (q500 − mean) **+0,00825 í artifact-ramma gegn +0,02638 á birtingarslóð**, og `q500 > mean` fer úr **53,2 % í 71,5 %**; `mean`-hausinn féll **2,6× meira** milli ramma en `q500` (−0,0297 gegn −0,0116) þótt fylgni punktmatsins milli slóða væri **0,977**. Þar með er cc120-talan „70,7 %" eiginleiki **verðmatsmánaðar-skorunarinnar**, ekki líkansins — og afleiðingin er á DÓMI en ekki bara stærð: **í artifact-rammanum vinnur `mean` og þar er ±10 %-munurinn MARKTÆKUR** (McNemar p = 0,00061), meðan birtingarslóðin gefur jafntefli. **Tímaeiginleikar eru útilokaðir sem EINA orsök** (artifact-`dlog` eftir söluári spannar +0,005…+0,017, 2026 á +0,0054); hvaða eiginleiki eða eiginleikar valda er ómælt. **Af hverju þetta má ekki liggja:** allt sem við sannreynum í artifact-ramma — flokkaþröskuldar, conformal-þekja, retrain-hlið — er sannreynt í RAMMANUM SEM VIÐ BIRTUM EKKI Í. Þessi mæling er fyrsta staðfesta tilvikið þar sem rammarnir tveir skila öfugum dómi, og `scripts/model_quality_eval.py:48-52` bannar þegar að vitna í annan sem hinn. Verkið er read-only og afmarkað: skora sama úrtak í báðum römmum, mæla Δ **per eiginleikahóp** (tími/CPI · staðsetning · stærð · ástand) og staðsetja muninn í eiginleikavigrinum. **Ekkert go; bókað svo þögnin sé val en ekki gleymska.** Sbr. `feedback_hofudgapid_er_eiginleiki_skorunarsamhengis`, `feedback_thjalfunarthekja_er_ekki_utgafuthekja`.

**Bókað sem GAT, ekki sem hrein niðurstaða:** flokkur D og `SUMMERHOUSE` eru **n = 0 á holdout30**, svo þar sem höfuðgapið er stærst (cc120: SUMMERHOUSE meðal |Δ| 19,77 %, hámark 526,2 %) er **engin OOS-mæling til á hvorugu höfðinu**. Það gat má hvorki fylla með ágiskun né brúa með `listing_valuations`-menginu (rangur nefnari, mildari dreifing: 4,77 % gegn 6,43 %). Sömuleiðis: `fresh_edge` (n = 93) er mengað af fjórum röðum sem `onothaefur = 0` átti að stöðva (2 M kr fyrir 128 m² einbýli) — **síuathugunin sjálf er ódýr, read-only og óunnin.**
