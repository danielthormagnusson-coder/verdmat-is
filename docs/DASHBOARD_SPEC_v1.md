# DASHBOARD_SPEC_v1

**Status:** FINAL — planning complete, ready for implementation chat.
**Version:** 1.0 (2026-04-23)
**Owner:** Sprint 2 Áfangi 4 planning.
**Successor:** passed verbatim to implementation chat; no spec-level changes
expected without a new planning cycle.

## Table of contents

1. [Dashboard navigation og information architecture](#section-1--dashboard-navigation-og-information-architecture)
2. [Landing view detail spec (`/markadur`)](#section-2--landing-view-detail-spec-markadur)
3. [Repeat-sale explorer (`/markadur/visitala`)](#section-3--repeat-sale-explorer-markadurvisitala)
4. [Markaðsstaða (`/markadur/markadsstada`)](#section-4--markaðsstaða-markadurmarkadsstada)
5. [LLM-derived aggregates (`/markadur/ibudir`)](#section-5--llm-derived-aggregates-markaduribudir)
6. [Model tracking (`/markadur/modelstada`)](#section-6--model-tracking-markadurmodelstada)
7. [Data pipeline additions (consolidated)](#section-7--data-pipeline-additions-consolidated)
8. [`sale_year` waterfall fix (carry-over UX)](#section-8--sale_year-waterfall-fix-carry-over-ux)
9. [Decision points resolved](#section-9--decision-points-resolved)
10. [Build order, time estimates, dependencies](#section-10--build-order-time-estimates-dependencies)

---

## Section 1 — Dashboard navigation og information architecture

### 1.1 Route tree

```
/markadur                        ← LANDING view (overview, hero metrics, CTA)
├── /markadur/visitala           ← Repeat-sale explorer (Áfangi 6 output)
├── /markadur/markadsstada       ← ATS regime heat map + timeline slider
├── /markadur/tilbod             ← Time-on-market distribution (deferred)
├── /markadur/ibudir             ← LLM-derived aggregates (condition, renovation,
│                                  unregistered space, agent framing, word freq)
└── /markadur/modelstada         ← Model trust panel (MAPE/coverage over time)
```

Plus shared chrome:
- Top nav `Markaður` dropdown surfaces all sub-routes
- Persistent scrape-gap banner when current month ≥ 2025-07 AND relevant data is
  touched on the page (see Section 4.3 for decision)
- Footer: methodology link → `/um#adferdafraedi`

### 1.2 Per-route purpose statement

| Route | Purpose (one paragraph) | SEO keyword focus |
|---|---|---|
| `/markadur` | **Overview** for anyone asking "how is the Icelandic real-estate market doing right now?" The landing is the SEO-primary page, the entry-point for social shares, and the proof-of-value target for pro-user invites. Must answer the question in < 5 seconds of scanning, with hero metric + 3-4 cards + a timeline. | "fasteignamarkaður ísland", "fasteignaverð 2026" |
| `/markadur/visitala` | **Repeat-sale explorer** for users who want to see price history not through HMS nominal fasteignamat but through paired same-property resales (the gold standard for price-index methodology). Answers "is the market up or down in real terms since X?" across 27 fitted cells. Editorial anchor: Áfangi 6 publishable findings (Country catch-up, ROW_HOUSE RVK niche, SUMMERHOUSE missed 2008 crash). | "raunverðs vísitala fasteigna", "fasteignaverð raun 2008" |
| `/markadur/markadsstada` | **Current regime state** answering "is the market hot or cold right now, where?" Drill-down from landing's regime pill. Heat-map grid (segment × region) with regime pill per cell, linked above-list-rate timeline, regime-month slider for historical playback. Editorial anchor: Áfangi 7 above-list is 3-4× in hot vs cold. | "fasteignamarkaður heitt kalt", "markaðsstaða 2026" |
| `/markadur/tilbod` | **Time-on-market distribution** per segment × region. Deferred to v1.1 because the scrape gap makes current TOM numbers unreliable — backfilling requires scraper replacement (Áfangi 0). Route stub shipped with "coming soon" messaging. | "tími á markaði", "hvað taka eignir langt að seljast" |
| `/markadur/ibudir` | **Quality of the housing stock** as seen through LLM extraction: how has condition score evolved, how common is recently-renovated, how often do listings mention "þarfnast framkvæmda"? Content-marketing gold: novel angle no competitor has. | "ástand íbúða ísland", "nýlega endurnýjuð fasteignir" |
| `/markadur/modelstada` | **Model trust panel** for pros and technically-minded users. MAPE and PI coverage over time, per-segment breakdown, refresh schedule, methodology link. Required credibility before pro-user invites go out. | "verðmatslíkan ísland", "MAPE fasteignaverðmat" |

### 1.3 v1 scope — CONFIRMED 2026-04-23

**Ship in v1:**
- `/markadur` (landing)
- `/markadur/visitala` (repeat-sale explorer)
- `/markadur/markadsstada` (regime heat map)
- `/markadur/ibudir` (LLM-derived aggregates)
- `/markadur/modelstada` (model trust)

**Deferred to v1.1:**
- `/markadur/tilbod` (needs scraper replacement first — TOM distribution is
  scrape-gap-dependent, would mislead users without full coverage)

**Rationale for keeping `/ibudir` in v1:** LLM extraction cost $375 and produced
insights no Icelandic competitor has published (condition trends, renovation
rates, agent-framing distribution). Strongest public-facing differentiator,
Google-bait, social-share-bait. `llm_aggregates_quarterly` is a pandas group-by
on existing `training_data_v2` — not new data collection, just derivation.

**Rationale for deferring `/tilbod`:** Time-on-market requires continuous
listings coverage. Scrape gap from 2025-07 makes current numbers unreliable and
the historical series unusable beyond pre-gap periods. Better to ship nothing
than a misleading section. Unblocked by scraper replacement (Áfangi 0 backlog).

### 1.4 Route rendering strategy

- All four v1 routes = Next.js server components with ISR `revalidate = 600` (10
  min). Data reads hit Supabase via the anon-key REST endpoint, same pattern as
  existing `/eign/[fastnum]`. No client-side data-fetch for first paint.
- Charts (repeat-sale, regime timeline, model tracking) = Recharts client
  components hydrated from server-passed JSON.
- Regime slider and any interactive controls = `"use client"` islands.
- Scrape-gap banner = server component, pure.
- SEO: each route sets `metadata.title` + `metadata.description`. Landing gets
  OG image + Twitter card pointing at a rendered snapshot of the hero (OG
  generation via `@vercel/og` — already in scope for pro attribution PDF future
  work, can reuse).

---

## Section 2 — Landing view detail spec (`/markadur`)

### 2.1 Wireframe

```
┌──────────────────────────────────────────────────────────────────────┐
│  verdmat.is — Markaður                      [Verðmat] [Markaður] [Um]│
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   FASTEIGNAMARKAÐURINN · 2026-04                                      │
│                                                                       │
│   Raunverð íbúða síðustu 12 mánuði                                    │
│                                                                       │
│   ─────────                                                            │
│    +0,8 %                 (Fraunces display, ~6rem, green if +, red if −)│
│   ─────────                                                            │
│                                                                       │
│   Markaðurinn er núna   [HLUTLAUS]   ← regime pill                    │
│                                                                       │
│   Íslenski fasteignamarkaðurinn í rauntíma. Verdmat.is samantekur     │
│   kaupsamninga, auglýsingar og markaðsástand yfir 20 ára tímabil.     │
│   Skoðaðu þróun eftir svæði, segmenti og tímabili.                    │
│                                                                       │
│  ┌ ⓘ Takmörkuð gögn frá júlí 2025 vegna tímabundinnar breytingar ───┐ │
│  │   á auglýsingaflæði. Historical analytics eru óháð þessu.     × │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌──────────────────┬──────────────────┬──────────────────┐            │
│  │ Yfirboð síðustu  │ Raunverðs CAGR   │ Líkansgæði       │            │
│  │ 3 mánuði         │ síðustu 10 ár    │ (held MAPE)      │            │
│  │ 14 %             │ +2,1 %           │ 8,2 %            │            │
│  │ main residential │ main residential │ mán 2026-03      │            │
│  └──────────────────┴──────────────────┴──────────────────┘            │
│                                                                       │
│  ┌────────────────────────────────────────────────────────┐            │
│  │ Raunverðs vísitala eftir segmenti 2006Q2 → nú          │            │
│  │                                                         │            │
│  │   (3 lines: APT_STANDARD ocean / SFH_DETACHED terracotta/│            │
│  │   ROW_HOUSE sage)                                       │            │
│  │                                                         │            │
│  │   ⋯ annotations: 2008 hrun · 2022Q4 hámark · 2023 leið. │            │
│  │                                                         │            │
│  │ 2006 ──────── 2008 ──── 2015 ──── 2022 ──── 2026        │            │
│  └────────────────────────────────────────────────────────┘            │
│                                                                       │
│  [Raunverðs vísitala →]  [Markaðsstaða →]                              │
│  [Íbúðaástand →]         [Líkansstaða →]                               │
│                                                                       │
│  ── footer ───────────────────────────────────────────────            │
│  Aðferðafræði · Um verdmat · GitHub repo                              │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Hero — CONFIRMED A+B hybrid

**Headline number (A):** 12-month real price change for pooled main residential.

- Label above number: `Raunverð íbúða síðustu 12 mánuði` (Inter 0.75rem,
  uppercase, muted, letter-spacing 0.12em)
- Number: Fraunces display, `clamp(4rem, 10vw, 7rem)`, line-height 0.95
- Prefix sign: always explicit (`+1,2 %` or `−2,5 %`)
- Color rule: `+` = `var(--vm-success)`, `−` = `var(--vm-danger)`, exact zero =
  `var(--vm-ink)`

**Subline (B):** Regime framing in one short Icelandic sentence + regime pill.

- Subline text: `Markaðurinn er núna` (Inter 1.05rem, ink-muted), followed by
  inline regime pill
- Pill labels: `HEITUR` / `HLUTLAUS` / `KALDUR` (uppercase, letter-spacing
  0.08em, weight 600)
- Pill colors — align with existing palette:

  | Regime | Background | Text color |
  |---|---|---|
  | Heitur | `rgba(198, 99, 58, 0.12)` — soft terracotta | `var(--vm-hot)` `#c6633a` |
  | Hlutlaus | `rgba(138, 138, 122, 0.14)` — soft grey | `var(--vm-neutral)` `#8a8a7a` |
  | Kaldur | `rgba(74, 111, 165, 0.12)` — soft ocean | `var(--vm-cold)` `#4a6fa5` |

  (These are already in `globals.css` as `vm-badge-hot/cold/neutral`. Hero pill
  reuses, sized 1.5× the default badge.)

**Pooling rule (both A and B):**
Main residential = weighted average across APT_FLOOR + APT_STANDARD +
SFH_DETACHED + ROW_HOUSE × RVK_core + Capital_sub + Country (12 cells), weights
= `n_pairs_in_period` for A, `n_pairs` for B. Excludes APT_BASEMENT, APT_ATTIC,
SEMI_DETACHED (secondary residential) from landing pool to keep the number
headline-comparable to mainstream real-estate press reports.

**Per-metric data-map:**

Metric A — 12-mo real change:
```sql
-- Uses repeat_sale_index_main_pooled view (see Section 2.5)
SELECT
  ((c.index_real - p.index_real) / p.index_real) * 100 AS pct_12mo
FROM
  (SELECT index_real FROM repeat_sale_index_main_pooled
    ORDER BY year DESC, quarter DESC LIMIT 1) c,
  (SELECT index_real FROM repeat_sale_index_main_pooled
    ORDER BY year DESC, quarter DESC LIMIT 1 OFFSET 4) p;
```
Fallback if < 5 non-null quarters available: hide hero, show
"Ekki tiltæk ennþá" sub-headline and push copy up.

Metric B — Regime (revised 2026-04-22 after Bug 1 fix):
Read latest (year, quarter) per main-residential cell from
`ats_dashboard_monthly_heat` or a derived `latest_regime_per_cell` view. Aggregate
using BOTH the 12-month real price change (same signal the hero number uses) and
the `n_month`-weighted mean of `z_3v12` across the 12 cells:

- 12m ≤ −1,0 % AND pooled z_3v12 < +0,5 → `KALDUR`
- 12m ≥ +1,0 % AND pooled z_3v12 > −0,5 → `HEITUR`
- Otherwise → `HLUTLAUS`

Rationale: the earlier 8-of-12-cells aggregation often produced a `HLUTLAUS`
pill even when the hero number was clearly negative/positive, creating a
cognitive mismatch for the user. The hybrid lets either signal (momentum or
trend) pull the pill off neutral, but requires agreement (no veto) before
committing to hot/cold. Fallback: pill reads `HLUTLAUS` with faint
`(gögn ekki fersk)` tooltip.

### 2.3 Secondary metrics row — 3 cards CONFIRMED

Three cards, equal width, breathe on mobile (1×3 stack under 600 px).

| Card | Value | Source | Query | Fallback |
|---|---|---|---|---|
| **Yfirboð síðustu 3 mánuði** | `14 %` | `ats_dashboard_monthly_heat` | Weighted mean of `above_list_rate` across main-residential cells for the most recent 3 months available. | `—` with caveat. |
| **Raunverðs CAGR síðustu 10 ár** | `+2,1 %` | `repeat_sale_index_main_pooled` | Compound annual growth rate: `(index_real[-1] / index_real[-40])^(1/10) − 1`, multiplied by 100. Quarterly index so 40 quarters = 10 years. | `—` if fewer than 40 non-null quarters. |
| **Líkansgæði (held MAPE)** | `8,2 %` | `model_tracking_history` (new — see Section 7) | Most recent month's held-set MAPE on iter4a mean predictions. | `—` with "fyrsta uppfærsla kemur í maí" if table empty. |

**Rationale — why include MAPE card on landing:**
Transparent-about-predictive-quality is trust-signal for bank/pro audience
arriving from Áfangi 5 invites. Number alone isn't meaningful to casual users,
but the explicit label ("Líkansgæði (held MAPE)") signals "we show our work"
without requiring users to click through to `/modelstada`. Optional hover
tooltip: "Mean Absolute Percentage Error á held-set eignum sem módelið sá
aldrei í þjálfun."

### 2.4 Timeline chart — CONFIRMED 3 lines

Three lines on one chart, pooled across regions per segment, 2006Q2 → latest.

- **APT_STANDARD** (pooled across RVK_core + Capital_sub + Country): `--vm-primary` ocean `#1f3a5f`
- **SFH_DETACHED** (pooled): `--vm-accent` terracotta `#c87146`
- **ROW_HOUSE** (pooled): `--vm-success` sage `#5d7f56`

**Rationale:** Showing segment divergence is itself an Áfangi 6 publishable
finding. Country catch-up vs RVK lead, ROW_HOUSE niche lower CAGR — these are
collapsed away by a single pooled line. Three lines let the reader notice
"wait, row houses moved differently" and click through to `/visitala` for the
full 3×3 grid deep dive.

**Segment pooling query** (per segment, pooled across regions):
```sql
-- Add to Section 7 pipeline: view repeat_sale_index_by_segment
CREATE VIEW repeat_sale_index_by_segment AS
SELECT canonical_code, year, quarter, period,
  SUM(index_value_real * n_pairs_in_period) / SUM(n_pairs_in_period) AS index_real,
  SUM(index_value_nominal * n_pairs_in_period) / SUM(n_pairs_in_period) AS index_nominal,
  SUM(n_pairs_in_period) AS n_pairs
FROM repeat_sale_index
WHERE canonical_code IN ('APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
GROUP BY canonical_code, year, quarter, period;
```

**Annotations** (fixed positions, rendered as subtle callouts):
- Vertical line + label at `2008Q2` → "Hrun byrjar"
- Shaded band `2008Q3`–`2011Q1`, opacity 0.06, label "Fall 40%"
- Vertical line at `2022Q4` → "Hámark"
- Vertical line at `2023Q2` → "Leiðrétting"

**Hover tooltip** format:
```
APT_STANDARD · 2023Q2
Raunverð index: 147,3
(vs 2006Q2 baseline = 100)
```

**Axis:**
- X: 2006, 2010, 2015, 2020, 2026 (5 ticks max on mobile)
- Y: 50, 100, 150, 200 (range auto-fit with padding)
- No gridlines on mobile

**Chart height:** 320 px desktop, 240 px mobile.

### 2.5 Supporting views (migration-sized infra additions)

All collected here for Section 7 integration:

```sql
-- Used by hero A and secondary card 2 (CAGR):
CREATE VIEW repeat_sale_index_main_pooled AS
SELECT year, quarter, period,
  SUM(index_value_real * n_pairs_in_period) / SUM(n_pairs_in_period) AS index_real,
  SUM(index_value_nominal * n_pairs_in_period) / SUM(n_pairs_in_period) AS index_nominal,
  SUM(n_pairs_in_period) AS n_pairs
FROM repeat_sale_index
WHERE canonical_code IN ('APT_FLOOR','APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
GROUP BY year, quarter, period;

-- Used by timeline chart (3 lines):
CREATE VIEW repeat_sale_index_by_segment AS ...  -- see 2.4

-- Used by hero B regime pill:
CREATE VIEW latest_regime_per_cell AS
SELECT DISTINCT ON (canonical_code, region_tier)
  canonical_code, region_tier, year, month,
  heat_bucket, above_list_rate
FROM ats_dashboard_monthly_heat
WHERE canonical_code IN ('APT_FLOOR','APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
ORDER BY canonical_code, region_tier, year DESC, month DESC;
```
(`ats_dashboard_monthly_heat` table already produced by Áfangi 7 build but not
yet imported into Supabase — import task is in Section 7.)

### 2.6 Scrape-gap disclaimer banner — low-key CONFIRMED

Position: on landing, between hero subline and secondary metric cards. On
drill-downs, surfaces only where relevant.

Copy (single sentence):
```
ⓘ  Takmörkuð gögn frá júlí 2025 vegna tímabundinnar breytingar á
   auglýsingaflæði. Historical analytics eru óháð þessu.
```

Styling:
- Inline pill, not full-width card
- Soft yellow background `rgba(212, 179, 70, 0.10)`, 1 px border
  `rgba(212, 179, 70, 0.35)`
- Info icon `ⓘ` in subtle yellow — **not** warning triangle
- Right-side close `×` for session-level dismiss (stored in
  `sessionStorage.scrapeGapDismissed = '1'`, re-shows next session)
- Font size 0.9 rem, line-height 1.4, padding 0.55 rem 0.85 rem
- Max width 100% of container; visually secondary to hero and cards

Trigger logic:
- `/markadur` landing: always show (until dismissed in session)
- `/markadur/visitala`: **hide** — repeat-sale is from kaupskrá, scrape-gap-safe
- `/markadur/markadsstada`: **show** when slider includes ≥ 2025-07; **hide**
  when slider is pre-gap-only
- `/markadur/ibudir`: **hide** — LLM extraction covers 2006–pre-gap window only,
  no user expectation of live data
- `/markadur/modelstada`: **show** — model freshness is affected by scrape-gap
  indirectly (retraining uses listings less than kaupskrá but worth a note)

Rationale for low-key tone: repeat-sale index and regime heat labels are
kaupskrá-driven, unaffected by scrape-gap. Only ATS timeline and TOM are scrape-
dependent. Louder "⚠ Warning" framing would under-mine confidence in data that
is, in fact, fresh.

### 2.7 Drill-down CTA buttons

Four pill buttons in 2×2 grid desktop, 1×4 stack mobile:
- `Raunverðs vísitala →` `/markadur/visitala`
- `Markaðsstaða →` `/markadur/markadsstada`
- `Íbúðaástand →` `/markadur/ibudir`
- `Líkansstaða →` `/markadur/modelstada`

Styling: `vm-btn-secondary` with right-arrow glyph `→`. Hover lifts shadow.

### 2.8 Icelandic copy — all surfaces

Drafts. Refine typography in implementation but these strings ship verbatim.

**Page title (browser tab + SERP):**
```
Fasteignamarkaðurinn á Íslandi — Verdmat
```
56 chars — under Google's 60-char tail truncation.

**Meta description (SERP snippet, 160 char limit):**
```
Hlutlægt yfirlit yfir íslenska fasteignamarkaðinn: verðvísitala, markaðshiti, söluhraði. Byggt á 226.000+ kaupsamningum og 471.000+ auglýsingum.
```
156 chars ✓.

**H1 equivalent (visible above hero number):**
```
Raunverð íbúða síðustu 12 mánuði
```
Semantic H1 is the big number itself; this label acts as the accessible
heading above it. For SEO-only H1 (not visible), use `<h1 className="sr-only">`
with "Fasteignamarkaðurinn á Íslandi".

**Hero supporting paragraph (below regime subline):**
```
Íslenski fasteignamarkaðurinn í rauntíma. Verdmat.is samantekur
kaupsamninga, auglýsingar og markaðsástand yfir 20 ára tímabil til að
gefa þér nákvæma mynd af hvernig verð hafa þróast. Skoðaðu þróun eftir
svæði, segmenti og tímabili.
```
2 sentences, ~45 words. Light SEO-density on primary keyword
"fasteignamarkaður", secondary keywords "verð hafa þróast", "svæði", "segmenti".

**Timeline chart caption** (small text above chart):
```
Raunverðs vísitala eftir segmenti — 2006Q2 = 100
```

**Drill-down section heading** (above 4 CTA buttons):
```
Skoða ítarlega
```

**Footer methodology link cluster:**
```
Aðferðafræði · Um verdmat · Gögn · GitHub
```
Links:
- Aðferðafræði → `/um#adferdafraedi`
- Um verdmat → `/um`
- Gögn → `/um#gognin`
- GitHub → public-repo URL when repo is made public (Áfangi 4+)

### 2.9 SEO keyword strategy

**Primary keyword (one, owns landing):**
```
fasteignamarkaður ísland
```
Rationale: highest monthly Icelandic search volume for the "state of market"
concept; matches how journalists and pros phrase the question. Alternative
("húsnæðismarkaður ísland") is close second but has more apartment-rental
overlap, dilutes intent.

**Secondary keywords — distributed across sub-routes:**

| Sub-route | Primary | Secondary |
|---|---|---|
| `/markadur/visitala` | "raunverðs vísitala fasteigna" | "fasteignaverð raun 2008", "repeat sale index iceland" |
| `/markadur/markadsstada` | "markaðsstaða fasteigna" | "húsnæðismarkaður heitt kalt", "fasteignahitastig" |
| `/markadur/ibudir` | "ástand íbúða ísland" | "nýlega endurnýjaðar íbúðir", "íbúðaþróun 2020" |
| `/markadur/modelstada` | "verðmatslíkan fasteigna" | "MAPE fasteignaverðmat", "fasteignaverð nákvæmni" |

**Keyword placement rule** (for implementation):
- Primary keyword appears in `<title>`, `<meta description>`, visible H1 or
  hero label, first 100 words of body copy
- Secondary keywords appear naturally in section headings, alt text for charts,
  body paragraphs
- Avoid keyword stuffing; density ≤ 1.5%

### 2.10 SEO metadata (Next.js)

```typescript
// app/markadur/page.js
export const metadata = {
  title: "Fasteignamarkaðurinn á Íslandi — Verdmat",
  description:
    "Hlutlægt yfirlit yfir íslenska fasteignamarkaðinn: verðvísitala, markaðshiti, söluhraði. Byggt á 226.000+ kaupsamningum og 471.000+ auglýsingum.",
  openGraph: {
    title: "Fasteignamarkaðurinn á Íslandi — Verdmat",
    description:
      "Raunverðs vísitala, markaðshiti og líkansstaða fyrir íslenska fasteignamarkaðinn. Uppfært mánaðarlega, byggt á þinglýstum kaupsamningum.",
    type: "website",
    locale: "is_IS",
    images: [{ url: "/og/markadur.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Fasteignamarkaðurinn á Íslandi",
    description:
      "Raunverðs vísitala, markaðshiti og líkansstaða — uppfært mánaðarlega.",
    images: ["/og/markadur.png"],
  },
};
```

**OG image strategy:**
- v1: static generated `/og/markadur.png` via `@vercel/og` — hero number +
  timeline snapshot, regenerate via a build-time script when new month's data
  arrives
- v1.1: dynamic per-page OG with segment-specific imagery on
  `/visitala/[segment]` routes (future)

### 2.8 Performance budget

Landing render budget:
- Server component main render ≤ 400 ms p95
- Supabase queries (metrics + timeline): ≤ 120 ms total (sequential acceptable
  since all hit the same connection pool, parallel via `Promise.all` ideally)
- Client hydration for chart ≤ 100 ms
- LCP target 1.8 s on mobile 4G

If timeline view query (`repeat_sale_index_main_pooled` view over all quarters
× 7 segments × 3 regions = 81 × 21 = 1701 rows pre-aggregation) exceeds budget,
materialize the view.

---

---

## Section 3 — Repeat-sale explorer (`/markadur/visitala`)

### 3.1 Scope — 🔶 decision-point #4 CONFIRMED

**Default grid: 4 rows × 3 columns = 12 plots.**

Rows (all always visible):
- APT_FLOOR
- APT_STANDARD
- SFH_DETACHED
- **ROW_HOUSE** (was toggle-only; promoted to always-visible because RVK_core
  niche is our strongest publishable finding — 0.5% real CAGR + 48.5% drawdown
  + small-supply niche framing. Hiding it behind a toggle buries the best
  story.)

Columns: RVK_core · Capital_sub · Country.

**Default grid:**
```
                RVK_core           Capital_sub        Country
APT_FLOOR     [chart 1×1]         [chart 1×2]         [chart 1×3]
APT_STANDARD  [chart 2×1]         [chart 2×2]         [chart 2×3]
SFH_DETACHED  [chart 3×1]         [chart 3×2]         [chart 3×3]
ROW_HOUSE     [chart 4×1]         [chart 4×2]         [chart 4×3]
```

Per-row segment toggle replaces that row's 3 charts with data for another
segment. Default rows = APT_FLOOR / APT_STANDARD / SFH_DETACHED / ROW_HOUSE,
but any row can swap to a secondary variant:
- APT_BASEMENT, APT_ATTIC (thin-N apartment subvariants — curiosity only)
- SEMI_DETACHED (N=48 held, too thin for default)
- SUMMERHOUSE (Country + Capital_sub only; RVK_core cell is empty)

**Mobile:** grid collapses to single column — 12 plots stack vertically, user
scrolls through one at a time. No scan-time loss because scroll replaces
simultaneous-glance workflow.

### 3.2 Wireframe

```
/markadur/visitala
┌──────────────────────────────────────────────────────────────────┐
│  ← Markaður                                                        │
│                                                                    │
│  Raunverðs vísitala                                                │
│  Paired resale index, 2006Q2 = 100                                 │
│                                                                    │
│  [Raun │ Nominal]    [81 ársfjórðungar · 27/33 cells fitted]      │
│                                                                    │
│  Rows × regions — rows default but swappable per-row:              │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ APT_FLOOR  [▾ APT_FLOOR]                                      │  │
│  │ ┌──────────┬──────────┬──────────┐                            │  │
│  │ │ RVK_core │Capital_sub│ Country  │                            │  │
│  │ └──────────┴──────────┴──────────┘                            │  │
│  ├─────────────────────────────────────────────────────────────┤  │
│  │ APT_STANDARD  [▾ APT_STANDARD]                                │  │
│  │ (3 charts)                                                    │  │
│  ├─────────────────────────────────────────────────────────────┤  │
│  │ SFH_DETACHED  [▾ SFH_DETACHED]                                │  │
│  │ (3 charts)                                                    │  │
│  ├─────────────────────────────────────────────────────────────┤  │
│  │ ROW_HOUSE  [▾ ROW_HOUSE]  ← publishable niche finding here    │  │
│  │ (3 charts)                                                    │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  Per-row toggle: compact pill-bar inline with row header, dropdown │
│  or segmented-control style. Click swaps that row's 3 charts only. │
│  Options: APT_FLOOR · APT_STANDARD · SFH_DETACHED · ROW_HOUSE ·    │
│  APT_BASEMENT · APT_ATTIC · SEMI_DETACHED · SUMMERHOUSE            │
│  (SUMMERHOUSE: only Country + Capital_sub have data — RVK_core    │
│   cell renders "—")                                                │
│                                                                    │
│  ── Publishable findings ──                                         │
│                                                                    │
│  ▸  Country catch-up                                                │
│     Raunverð á landsbyggðinni hefur hækkað 74,9 % frá 2006         │
│     miðað við 35,6 % í Reykjavík miðju. Mestur hluti               │
│     "catch-up" gerðist 2020–2024.                                   │
│     [ Skoða nánar → ]                                               │
│                                                                    │
│  ▸  ROW_HOUSE RVK niche                                             │
│     Raðhús í RVK fóru aðra leið en restin: mild crash (~24%)       │
│     en hraðari recovery og platform frá 2013.                      │
│                                                                    │
│  ▸  SUMMERHOUSE missed crash                                        │
│     Sumarhús á landsbyggðinni misstu 2008-hrunið alveg —            │
│     counter-cyclical vs innlent eftirspurnarfall.                   │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 Per-chart rendering

Each of 12 charts:
- Recharts `LineChart`, 160 px tall × flex width (≈ 33% of row; smaller than
  9-chart version because grid is denser)
- Single line, real by default, toggleable to nominal via page-level control
- Line color by segment (ocean APT_STD, terracotta SFH_DETACHED, sage
  ROW_HOUSE; fourth+ segments pick from extended palette documented in
  `globals.css`)
- Faint `--vm-border` horizontal reference line at y = 100 (baseline)
- **Crash-band shading 2008Q3–2011Q1 with data-quality-aware opacity:**

  | `data_quality` flag | Shading |
  |---|---|
  | `high` (n ≥ 50 per quarter in band) | Solid terracotta, 8% opacity |
  | `medium` (20 ≤ n < 50) | Solid terracotta, 5% opacity + subtle border |
  | `low` (10 ≤ n < 20) | Hatched terracotta lines, very sparse |
  | `insufficient` (n < 10 or fewer than 4 quarters fitted) | No shading; chart body also muted 50% + "of fá pör" caption |

  Rationale: universal shading maintains pedagogical context (2008 crash is
  not optional), but varying opacity prevents implying thin-sample data is
  equally trustworthy.

- X-axis: 3 ticks (2006, 2015, 2026), mobile drops to 2 (2006, 2026)
- Y-axis: dynamic range, always includes 0–max with 20% headroom
- Cell-header above chart: canonical × region + current index value
- For `insufficient_sample` cells: greyed out at 50% opacity, no trendline,
  caption "Of fá pör (n < 50 per ársfjórðung)"

**Hover tooltip** per data point:
```
2023Q2 · APT_STANDARD × RVK_core
Raunverð index:   147,3
Nominal:          161,5
n pör þessi ársfjórðung: 42
CI ±:             ±3,2
```

### 3.4 Publishable-findings callouts

Three annotated inline cards at bottom, sourced from Áfangi 6 closure doc:

**Card 1 — Country catch-up:**
- Number: +74,9 % Country vs +35,6 % RVK_core (2006→2026, real)
- Micro-chart: 2-line overlay (Country vs RVK_core for APT_STANDARD), 80px tall
- Body: 2 sentences
- CTA: `Skoða APT_STANDARD ×  Country →` deep-links to (segment, region)
  state in URL hash `#APT_STANDARD.Country`

**Card 2 — ROW_HOUSE RVK niche:**
- Number: −24 % crash depth vs −40 % market (2008–2011)
- Micro-chart: ROW_HOUSE RVK_core single line
- Body: 2 sentences on faster recovery + 2013 platform
- CTA: toggle row 3 to ROW_HOUSE when clicked

**Card 3 — SUMMERHOUSE missed crash:**
- Number: +7,0 % CAGR Country summerhouse, never below 100
- Micro-chart: SUMMERHOUSE Country single line
- Body: 2 sentences on tourism-driven counter-cyclicality
- CTA: toggle row 1 to SUMMERHOUSE (Country only)

### 3.5 Real vs Nominal toggle

Single switch above the grid, left-aligned. States:
- `Raun` (default, CPI-deflated) — headline recommended view
- `Nominal` — raw kaupverð, no CPI adjustment

Clicking swaps all 9 chart data arrays. No URL state for v1 (session-only).
Nominal view shows a helper tooltip first time: "Nominal vísitala sýnir
krónuverðið án verðbólgu-leiðréttingar. Fyrir sögulegan samanburð mælum við
með raun."

### 3.6 Data sources

No new tables. Direct queries on `repeat_sale_index`:
```sql
-- Single cell query (9× on page load, parallel via Promise.all):
SELECT year, quarter, period,
       index_value_real, index_value_nominal,
       std_error_real, std_error_nominal,
       n_pairs_in_period, data_quality, insufficient_sample
FROM repeat_sale_index
WHERE canonical_code = $1 AND region_tier = $2
ORDER BY year, quarter;
```

Annotations card data: computed server-side from full table, cached via ISR.

### 3.7 Scrape-gap banner

Hidden on this route. Repeat-sale is kaupskrá-derived, unaffected by the gap.

### 3.8 Icelandic copy (`/markadur/visitala`)

```
<title>  Raunverðs vísitala — Fasteignaverð á Íslandi 2006–2026
<meta>   Paired-resale vísitala fyrir íslenska fasteignamarkaðinn eftir
         segmenti og svæði. Raunverð vs nominal 2006Q2–nú.
<H1>     Raunverðs vísitala
<sub>    Paired-resale vísitala eftir segmenti og svæði, 2006Q2 = 100
```

### 3.9 SEO keywords

Primary: `raunverðs vísitala fasteigna`
Secondary: `fasteignaverð raun 2008`, `paired resale iceland`,
`housing price index iceland`

### 3.10 Performance

- Parallel 9 queries against `repeat_sale_index` = 9 × 81 rows = 729 rows total.
  Sub-200 ms achievable on Supabase edge.
- Chart rendering: 9 × Recharts LineChart. Consider `LineChart` with
  `isAnimationActive={false}` for initial paint, enable on interaction.
- Callout micro-charts are additional 3 × 2 = 6 mini-charts. Lazy-render under
  viewport intersection observer.

---

## Section 4 — Markaðsstaða (`/markadur/markadsstada`)

### 4.1 Scope

Heat-map grid of current-month regime per (segment × region) cell + timeline
slider for historical playback + linked above-list-rate timeline. Adds a
**property back-projection** widget: for any `fastnum` (via search), show
iter4 current prediction **back-deflated** via real_index to show implied
value trajectory over past 12 months.

### 4.2 Wireframe

```
/markadur/markadsstada
┌──────────────────────────────────────────────────────────────────┐
│  ← Markaður                                                        │
│                                                                    │
│  Markaðsstaða                                                      │
│  Hvaða segmentir eru heitir eða kaldir?                            │
│                                                                    │
│  ┌ Tímabil ──────────────────────────────────────────────────┐    │
│  │ [2023-01 ●────────────────────────── 2026-04]  2026-04     │    │
│  │                                                             │    │
│  │ Slider picks "as of" month. Default = latest pre-gap month.│    │
│  │ Gap period (2025-07→nú) shown greyed on track.             │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                    │
│  Heat map — ástand per 2025-06:                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │            │ RVK_core │ Capital_sub │ Country              │  │
│  │────────────┼──────────┼─────────────┼──────────────────────│  │
│  │ APT_FLOOR  │ KALDUR   │ HLUTLAUS    │ HEITUR (catch-up)    │  │
│  │ APT_STD    │ KALDUR   │ HLUTLAUS    │ HEITUR               │  │
│  │ SFH_DET    │ HLUTLAUS │ HLUTLAUS    │ HEITUR               │  │
│  │ ROW_HOUSE  │ KALDUR   │ KALDUR      │ HLUTLAUS             │  │
│  │ APT_BSMT   │ KALDUR   │ KALDUR      │ KALDUR               │  │
│  │ SEMI_DET   │ HLUTLAUS │ HLUTLAUS    │ HLUTLAUS             │  │
│  │ APT_ATTIC  │ HLUTLAUS │ KALDUR      │ —                    │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  Above-list rate — tímaferill 2006–nú (pooled main residential):   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │   (line chart, shaded region matches slider position)         │  │
│  │                                                               │  │
│  │   2022 hámark ─── 33%                                         │  │
│  │   2023 leiðrétting ─── 10%                                    │  │
│  │   2024-25 stöðugleiki ─── 12-14%                              │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ── Back-projection á eign ──                                      │
│                                                                    │
│  [ Finna eign … ]  (autocomplete by address, same as /)           │
│                                                                    │
│  Eftir að eign er valin:                                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ Bakkastígur 1, 101 RVK — APT_FLOOR                            │  │
│  │ Núverandi iter4 mat: 91,6 M kr                                │  │
│  │                                                               │  │
│  │ Áætlað verðgildi síðustu 12 mánuði:                           │  │
│  │ (line chart, Apr-2025 → Apr-2026)                             │  │
│  │                                                               │  │
│  │ Hæst:     91,6 M kr  (2026-04, núna)                          │  │
│  │ Lægst:    89,9 M kr  (2025-09)                                │  │
│  │ Breyting: +1,9 %                                              │  │
│  │                                                               │  │
│  │ ⚠ Áætlun byggir á raunverðs vísitölu per segment × svæði.    │  │
│  │   Ekki nákvæm spá á sölu — einstök eign getur víkið frá       │  │
│  │   markaðsmeðaltali.                                           │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ⓘ Takmörkuð gögn frá júlí 2025 — regime á gap-period gæti vikið   │
│    frá raunveruleika.                                              │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3 Scrape-gap handling — 🔶 decision-point #3 CONFIRMED

**Choice: Yellow overlay on slider + soft caveat, don't disable.**

The slider is free to range across the full time axis (2006–present), but the
**2025-07 → latest** portion of the track is rendered with a hatched yellow
overlay (30% opacity diagonal stripes) and tooltip on hover: "Takmörkuð
auglýsingagögn á þessu tímabili. Heat-labels kunna að vera ónákvæmir."

**Slider default position: latest data month.**

Default = most recent month where `n_transactions ≥ MIN_TRANSACTIONS` in the
current month's row of `ats_dashboard_monthly_heat` (MIN_TRANSACTIONS = 50
pooled across main residential cells, set empirically at implementation time).
In practice this is typically "current month − 2 weeks" due to HMS þinglýsinga-
lag. Example: on 2026-04-23, default lands on 2026-04 or 2026-03 depending on
processed transaction volume.

Rationale: user landing in April 2026 expects current state, not 10-month-old
snapshot. Scrape-gap caveat is handled by the yellow-overlay slider + per-
position warning banner (below) — users get recency AND transparency about
data limits.

Below the heat-map, when current slider position is in the gap window:
- A small inline note under the grid: "⚠ Heat-labels reikna á takmörkuðum gögnum
  frá júlí 2025."
- Heat-labels themselves are still shown (using what data exists); we don't
  blank them out, users can judge for themselves with the caveat in place.

Pre-gap positions show no warning (data is complete).

### 4.4 Heat-map grid rendering

**Cell content:**
- Large regime label (HEITUR / HLUTLAUS / KALDUR)
- Small caveat under when applicable: "(catch-up)" for Country SFH_DETACHED
  per Áfangi 7 finding, "(small n)" for cells with `n_pairs < 10`
- Click behavior: opens a detail popover showing
  - `above_list_rate` current value
  - `median_log_ratio` value
  - **12-month mini-timeline** of the cell's above-list rate (trade-off: 6 too
    short to see seasonality/regime transitions, 24 cramped in popover; 12
    captures full seasonal cycle + recent trend in a 200–250 px-wide popover)
  - "Skoða vísitölu →" deep-link to `/markadur/visitala#<segment>.<region>`

**Color rule** (consistent with Section 2.2 pill palette):
- `HEITUR` cell: background `rgba(198, 99, 58, 0.08)`, border
  `rgba(198, 99, 58, 0.25)`, text `var(--vm-hot)` bold
- `HLUTLAUS`: background `rgba(138, 138, 122, 0.06)`, muted grey text
- `KALDUR`: background `rgba(74, 111, 165, 0.08)`, text `var(--vm-cold)`
- Empty: "—" with lighter stroke

**Data source:**
```sql
-- ats_dashboard_monthly_heat has monthly z-score + regime per cell.
-- For historical slider: ats_lookup (heat-pooled) can't answer
-- "what was the regime in July 2021?" — need per-month history.
-- ats_dashboard_monthly_heat is the authoritative source for slider.
```

Needs `ats_dashboard_monthly_heat` to be imported to Supabase (it exists as
a build artifact on D:\ — Áfangi 7 — but not yet in Supabase tables). Section 7
covers this migration.

### 4.5 Timeline — above-list rate (pooled main residential)

Linked to slider: shaded vertical band at current slider position, updates
instantly when slider moves. Line chart covers 2006–present, single line (not
3-way split because above-list-rate variance across segments is small relative
to over-time variance — per Áfangi 7).

**Annotations:**
- Label "2022 hámark — 33%" at peak
- Label "2023 leiðrétting" at trough
- Label "2024–25 stöðugleiki" as soft band

**Data source:**
```sql
SELECT year, month,
       SUM(above_list_rate * n_pairs) / SUM(n_pairs) AS pooled_rate,
       SUM(n_pairs) AS n
FROM ats_dashboard_monthly_heat
WHERE canonical_code IN ('APT_FLOOR','APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
GROUP BY year, month
ORDER BY year, month;
```

### 4.6 Property back-projection widget

**🔶 Decision-point #7 resolution: place on BOTH `/markadsstada` AND eigna-síða.**

Rationale: On `/markadsstada` it answers "what would market forces have done
to THIS property's value over the last 12 mo?" — contextualizing abstract
regime discussion with a concrete number. On eigna-síða it's a new section
below current prediction card: "Hvernig hefur þessi eign líklega þróast?"
Both surfaces feed the same widget component, same API.

**Widget states:**

1. **No property selected (default on `/markadsstada`):**
   Autocomplete search bar (reuse `SearchAutocomplete` from `/`). Help text:
   "Sláðu inn heimilisfang til að sjá áætlaða verðþróun."

2. **Property selected:**
   - Header: heimilisfang + segment + current prediction (M kr)
   - Line chart: 12 monthly points, Apr-2025 → Apr-2026
   - Numeric summary: hæst, lægst, current, % breyting
   - Caveat box (identical to above): "Áætlun byggir á raunverðs vísitölu per
     segment × svæði. Ekki nákvæm spá — einstök eign getur vikið frá
     markaðsmeðaltali."

**Computation:**

For a property with:
- `fastnum` (lookup canonical_code, region_tier from `properties`)
- `real_pred_mean` (current iter4 prediction in ISK, from `predictions`)

Back-projection at time `t`:
```
implied_value(t) = real_pred_mean × (index_real[cell, t] / index_real[cell, now])
```

Where `index_real[cell, t]` is interpolated monthly from quarterly
`repeat_sale_index` (linear interpolation between quarters).

**Interpolation caveats:**

- **Linear is fine for v1.** Real prices are already smoothed by quarterly
  aggregation, so linear interp between adjacent quarters doesn't introduce
  meaningful bias for most cells. Missing regime-transition months (sharp 2008
  onset) is rare and historical; iter 5+ can revisit with cubic or GMRCS if
  empirical need arises.
- **Do NOT interpolate across `data_quality = 'insufficient'` quarters.**
  If any quarter in the 12-month window has `insufficient_sample = true`, the
  plot shows a break in the line (dashed or null values) at that position
  rather than a smooth spline through empty data. Prevents lying-smooth-line
  over empty cells.

Example: Bakkastígur 1 (`APT_FLOOR × RVK_core`), current mean 91,6 M kr,
`index_real[now] = 135.2`, `index_real[t-12mo] = 132.7`. Implied value
12 mo ago = `91,6 × 132,7 / 135,2 = 89,9 M kr`.

**Edge cases:**
- Cell has `insufficient_sample`: show widget but with caveat "Of fá endursölu-
  pör í þessu cell — back-projection er bara directional"
- Current quarter missing: back-project to nearest fitted quarter
- Property is non-residential (no prediction): hide widget entirely, show
  "Engin spá til fyrir þessa eign" message
- Property is SUMMERHOUSE: show widget but with extra caveat (iter4 MAPE is
  high for SUMMERHOUSE per known issue)

**Data source:**

Server action `getPropertyBackProjection(fastnum)`:
1. `SELECT * FROM properties WHERE fastnum = $1`
2. `SELECT * FROM predictions WHERE fastnum = $1`
3. `SELECT index_real, year, quarter FROM repeat_sale_index
    WHERE canonical_code = $X AND region_tier = $Y
    AND (year, quarter) IN <last 5 quarters>`
4. Interpolate monthly; compute 12 monthly implied values
5. Return `{ property, prediction, monthly_values, hi, lo, pct_change }`

### 4.7 Icelandic copy (`/markadur/markadsstada`)

```
<title>  Markaðsstaða — Heitt eða kalt á íslenska fasteignamarkaðnum
<meta>   Regime indicator fyrir íslenska fasteignamarkaðinn: 23 cells
         af 33 fitted. Above-list rate timeline, heat map og back-
         projection per eign.
<H1>     Markaðsstaða
<sub>    Hvaða segmentir eru heitir eða kaldir — tímabundið drífari
         í takt við slider-ið.
```

### 4.8 SEO keywords

Primary: `markaðsstaða fasteigna`
Secondary: `fasteignamarkaður heitt kalt`, `fasteignahitastig`,
`yfirboð íbúðir ísland`

### 4.9 Performance

- Slider rendering is client-side (no server round-trip on drag); pre-fetch
  all monthly data on page load (~2.5K rows at worst: 33 cells × 81 months max)
- Back-projection widget: 1 server action per fastnum, ≤ 150 ms
- Heat-map re-render on slider drag: client-only, data in memory

---

## Section 5 — LLM-derived aggregates (`/markadur/ibudir`)

### 5.1 Scope — v1 ships 5 metrics, defers 1

**In v1 (5 metrics):** 1. Ástandsvísitala · 2. Endurnýjunartíðni · 3. Óskráð
rými rate · 4. Sérlóð í APT · 6. Agent framing distribution. All five are
pandas `groupby` operations on `training_data_v2` — zero new data collection,
zero new pipeline beyond a single aggregation script.

**Deferred to v1.1:** **5. Orðatíðni** (word-frequency — "þarfnast framkvæmda"
vs "tilbúið til flutnings" vs "einstakt tækifæri").

**Why defer metric 5:** It's the only metric that requires:
- A new `listing_text_freq_quarterly` table (separate schema)
- A new build script that re-reads 1.6 GB `listings_text_v2.pkl`, runs
  regex/NLP, aggregates, and imports to Supabase
- Orchestrator extension (monthly pipeline refresh)

Meanwhile metrics 1, 2, 3, 4, 6 all live in `training_data_v2` already — a
single `llm_aggregates_quarterly` table + one groupby script covers them all.
Skipping metric 5 saves 1–2 days of infra work without sacrificing launch
breadth (five unique publishable aggregates is plenty for v1 editorial).

Metric 5 section 5.5 below stays in spec as a roadmap anchor — future chat
sees what the v1.1 addition looks like.

### 5.2 The v1 metrics (five)

Each is a quarterly time-series aggregation, segmented by canonical code.

**1. Ástandsvísitala** (condition index)

`mean(interior_condition_score) per year-quarter × segment`
Score range 0–5 from v0.2.2 extraction. Visualize as 3-line time series
(APT_STANDARD / SFH_DETACHED / ROW_HOUSE), same color as Section 2.4 palette.

Editorial story: "Hefur ástand íbúða á markaði farið upp eða niður síðan 2006?"
Hypothesis (to verify via data): ástand er betra í hot-regime-skeiðum þegar
sellers investing in pre-sale cleanup.

**2. Endurnýjunartíðni** (recent renovation rate)

`% of listings with ≥ 1 status field = "replaced_new" and year within last 5`
per year-quarter × segment. Aggregated across kitchen/bathroom/flooring/paint.

Editorial story: "Nýjar endurbætur eru algengari á heitum markaði" — verify.

**3. Óskráð rými rate**

`% of listings with has_unregistered_space = true` per year-quarter × segment.
Higher values suggest a market where properties are over-built relative to
registered square meters; notable in SFH_DETACHED Country.

**4. Sérlóð í APT**

`% of APT listings with lot_is_serlod = true` per year-quarter × region.
Specific to apartments — "does this apartment come with its own lot?" is an
Icelandic nuance absent from continental European markets.

**5. Orðatíðni — DEFERRED to v1.1**

Frequency over time of three exemplar phrases in listing text:
- `"þarfnast framkvæmda"` (needs work)
- `"tilbúið til flutnings"` (move-in ready)
- `"einstakt tækifæri"` (unique opportunity — agent hype signal)

Not in v1 for the scope-reasons documented in Section 5.1. Preserved here as
a roadmap anchor.

**v1.1 implementation notes (for future chat):**
- Source is `listings_text_v2.pkl` (1.6 GB on `D:\`, not currently in Supabase)
- Aggregation: Python script computes quarterly frequencies once per month,
  outputs `listing_text_freq_quarterly.csv` (quarters × phrases × segment ×
  region), imports to Supabase
- New table schema in Section 5.5 below (retained in spec)
- Orchestrator extension: append step after `rebuild_training_data.py` in
  monthly refresh cycle

Editorial hypothesis (to verify with v1.1 data): agent hype ("einstakt
tækifæri") peaks in hot regime, "þarfnast framkvæmda" frequency signals
real-market softening before price adjusts.

**6. Agent framing distribution** (listing_elaboration)

`listing_elaboration` enum values (terse / standard / elaborate /
promotional_heavy) quarterly distribution per segment. Visualized as stacked
area chart — each quarter, what fraction of listings fall into each elaboration
category.

Editorial story: proportion of `promotional_heavy` listings spikes during
competitive-seller periods (early-2022 bidding-war run-up), drops during
buyer's-market (late 2023).

### 5.3 Wireframe

```
/markadur/ibudir
┌──────────────────────────────────────────────────────────────────┐
│  ← Markaður                                                        │
│                                                                    │
│  Íbúðaástand — hvernig hafa íbúðirnar sjálfar breyst?              │
│                                                                    │
│  Novel analysis byggt á AI-greiningu á 37.544 sölulýsingum         │
│  frá 2006–2025.                                                    │
│                                                                    │
│  ─── 1. Ástandsvísitala ───                                        │
│  3-line time series chart (APT_STANDARD / SFH_DETACHED / ROW_HOUSE)│
│  Editorial copy: 3-4 sentences                                     │
│                                                                    │
│  ─── 2. Endurnýjunartíðni ───                                      │
│  Stacked area chart over time                                      │
│  Editorial copy                                                    │
│                                                                    │
│  ─── 3. Óskráð rými ───                                            │
│  Bar chart per region, SFH_DETACHED vs APT highlighted             │
│  Editorial copy                                                    │
│                                                                    │
│  ─── 4. Sérlóð í APT ───                                           │
│  Small multiple by region, 3 mini-charts                           │
│  Editorial copy                                                    │
│                                                                    │
│  ─── 5. Orðatíðni ───                                              │
│  3-line chart: 3 exemplar phrases over time                        │
│  Editorial copy + social-share-friendly insight                    │
│                                                                    │
│  ─── 6. Agent framing ───                                          │
│  Stacked area chart over time per segment                          │
│  Editorial copy                                                    │
│                                                                    │
│  ── Footer ─── "Aðferðafræði"                                      │
└──────────────────────────────────────────────────────────────────┘
```

### 5.4 Data source — `llm_aggregates_quarterly` table (new)

```sql
CREATE TABLE llm_aggregates_quarterly (
  year INT,
  quarter SMALLINT,
  period TEXT,  -- e.g. "2023Q2"
  canonical_code TEXT,
  region_tier TEXT,  -- nullable for "all regions pooled" rows

  -- Metric 1
  mean_interior_condition_score NUMERIC,
  n_listings_condition INT,

  -- Metric 2
  pct_recently_renovated NUMERIC,
  n_listings_renovation INT,

  -- Metric 3
  pct_has_unregistered_space NUMERIC,

  -- Metric 4
  pct_apt_with_serlod NUMERIC,

  -- Metric 6
  pct_framing_terse NUMERIC,
  pct_framing_standard NUMERIC,
  pct_framing_elaborate NUMERIC,
  pct_framing_promotional NUMERIC,

  n_listings_total INT,  -- count per segment × region × quarter
  created_at TIMESTAMPTZ DEFAULT NOW(),

  PRIMARY KEY (year, quarter, canonical_code, region_tier)
);

CREATE INDEX idx_llm_agg_period ON llm_aggregates_quarterly(period);
CREATE INDEX idx_llm_agg_segment ON llm_aggregates_quarterly(canonical_code);
```

**Build script** — `D:\verdmat-is\build_llm_aggregates.py`:

```python
# Pseudocode
df = pd.read_pickle('D:\\training_data_v2.pkl')
df['year'] = pd.to_datetime(df['THINGLYSTDAGS']).dt.year
df['quarter'] = pd.to_datetime(df['THINGLYSTDAGS']).dt.quarter
df['period'] = df['year'].astype(str) + 'Q' + df['quarter'].astype(str)

# Compute 6 metrics per (year, quarter, canonical_code, region_tier)
grouped = df.groupby(['year','quarter','period','canonical_code','region_tier'])
# For each metric: apply np.mean or (count matching) / count,
# guard against n < 10 with NULL
# ...

result.to_csv('llm_aggregates_quarterly.csv')
# Supabase import same pattern as existing Phase 1A pipeline
```

Runs monthly in orchestrator after rebuild_training_data. Idempotent.

### 5.5 Metric 5 (orðatíðni) — v1.1 addition

**Status:** DEFERRED. Not built in v1. Schema kept here as roadmap anchor for
the v1.1 implementation chat.

```sql
-- Future v1.1 table
CREATE TABLE listing_text_freq_quarterly (
  year INT,
  quarter SMALLINT,
  period TEXT,
  canonical_code TEXT,  -- from joined fastnum → properties.canonical_code
  region_tier TEXT,
  phrase TEXT,  -- 'þarfnast framkvæmda', 'tilbúið til flutnings',
                -- 'einstakt tækifæri', extensible to more phrases in v1.2+
  frequency NUMERIC,  -- fraction of listings containing phrase
  n_listings_matched INT,
  n_listings_total INT,
  PRIMARY KEY (year, quarter, canonical_code, region_tier, phrase)
);
```

Build script joins `listings_text_v2.pkl` with `listings_v2.pkl` for `fastnum`,
then with `properties` for `canonical_code` + `region_tier`, applies regex
match for each phrase, aggregates frequencies quarterly. Runs monthly as
orchestrator extension (post-rebuild_training_data).

### 5.6 Icelandic copy (`/markadur/ibudir`)

```
<title>  Íbúðaástand á Íslandi — AI-greining á 37.544 sölulýsingum
<meta>   Ástandsvísitala, endurnýjunartíðni, óskráð rými, sérlóðir og
         agent-framing yfir 20 ára tímabil. Gögn úr AI-greiningu á
         lýsingum úr íslenskum fasteignaauglýsingum.
<H1>     Íbúðaástand
<sub>    Hvernig hafa íbúðirnar sjálfar breyst síðustu 20 ár?
```

### 5.7 SEO keywords

Primary: `ástand íbúða ísland`
Secondary: `nýlega endurnýjaðar íbúðir`, `íbúðaþróun 2020`,
`sölulýsingar greining`

### 5.8 Editorial narrative — placeholder structure

Final prose drafted during implementation once the actual aggregates are
plotted and we can see which patterns stand out. Spec-level placeholder
structure per metric so implementation knows where copy goes and what it
answers — but no pre-written claims we can't back.

Per-metric placeholder template:

```markdown
### [Metric name]

**Editorial hook** (1 sentence, H3 or strong opener)
Frames the question the metric answers in plain Icelandic. Example for
Ástandsvísitala: "Hefur ástand íbúða á íslenska markaðnum farið upp eða
niður síðustu 20 ár?"

**Narrative arc** (2–3 sentences)
Tells the reader what the chart shows, highlights the 1–2 most surprising
numbers, relates to broader context (regime cycle, Country catch-up,
whatever the data actually reveals).

**Key callout (TBD with real data)**
Placeholder for a pull-quote or inline stat — decide at implementation which
segment/year/number is most shareable. Example template: "{segment} {year}:
{number} — {interpretation}".
```

Implementation chat fills out all 5 `(TBD with real data)` slots once charts
are rendered and patterns visible. Spec version ships with placeholders so
structure is locked but prose is honest.

---

---

## Section 6 — Model tracking (`/markadur/modelstada`)

### 6.1 Scope and purpose

Trust-building page. Shows the audience — particularly pro-users arriving from
Áfangi 5 invites — that we measure our own accuracy rigorously, publish the
numbers, and improve over time. Not a sales pitch. Every number on this page
exists to answer "is this model good enough for me to rely on?"

Contents (v1):
1. Held-set MAPE trend — last 6 months of monthly retraining results
2. PI coverage trend — cov80 and cov95 on held over the same 6 months
3. Per-segment MAPE breakdown table — current state
4. Monthly refresh status — last successful run timestamp + pipeline health
5. Transparent methodology link

### 6.2 Wireframe

```
/markadur/modelstada
┌──────────────────────────────────────────────────────────────────┐
│  ← Markaður                                                        │
│                                                                    │
│  Líkansstaða                                                       │
│  Hversu nákvæmur er iter4 verðmatsmódelið?                         │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Held-set MAPE síðustu 6 mánuði                              │  │
│  │                                                               │  │
│  │  ┌── line chart ──────────────────────────────────────────┐  │  │
│  │  │ 10% ─                                                  │  │  │
│  │  │     ╲                                                  │  │  │
│  │  │  8% ─╲__________                                       │  │  │
│  │  │                 ╲___                                   │  │  │
│  │  │  6% ─                                                  │  │  │
│  │  │     2025-11  2026-01  2026-03                          │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  │  Sýnir mean absolute % error á held-set eignum sem          │  │
│  │  módelið sá aldrei í þjálfun.                               │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Vissubil — empirísk coverage                                │  │
│  │                                                               │  │
│  │  2-line chart: cov80 (target 80%) og cov95 (target 95%)     │  │
│  │  yfir sömu 6 mánuði. Target lines dashed.                    │  │
│  │                                                               │  │
│  │  Apríl 2026:  80% bil = 79% (target 80%)                    │  │
│  │               95% bil = 95% (target 95%)                    │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Per-segment MAPE — apríl 2026                               │  │
│  │                                                               │  │
│  │  ┌─────────────┬──────────┬─────┬───────────────────┐       │  │
│  │  │ Segment     │ MAPE     │ N   │ Staða             │       │  │
│  │  ├─────────────┼──────────┼─────┼───────────────────┤       │  │
│  │  │ APT_STANDARD│  6,4 %   │ 740 │ ● Í lagi          │       │  │
│  │  │ APT_FLOOR   │  8,6 %   │1019 │ ● Í lagi          │       │  │
│  │  │ ROW_HOUSE   │  7,2 %   │ 100 │ ● Í lagi          │       │  │
│  │  │ SEMI_DET    │  9,5 %   │  48 │ ● Með athugasemd  │       │  │
│  │  │ APT_BASMNT  │ 10,9 %   │  51 │ ● Með athugasemd  │       │  │
│  │  │ SFH_DET     │ 16,3 %   │ 106 │ ● Sveiflast       │       │  │
│  │  │ SUMMERHOUSE │175   %   │  47 │ ● Þarfnast skoðunar│      │  │
│  │  └─────────────┴──────────┴─────┴───────────────────┘       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Pipeline staða                                              │  │
│  │                                                               │  │
│  │  ✓  Síðasta endurnýjun: 1. apríl 2026 (23 dagar síðan)      │  │
│  │  ✓  repeat_sale_index: fresh (uppfært 1. apríl 2026)        │  │
│  │  ✓  ATS lookup: fresh (uppfært 1. apríl 2026)               │  │
│  │  ✓  Conformal calibration: fresh (iter4_conformal_v1)       │  │
│  │  ⚠ Listings data: scrape-gap frá júlí 2025                  │  │
│  │                                                               │  │
│  │  [Aðferðafræði →]                                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 6.3 Panel 1 — Held MAPE trend

**Chart:**
- Recharts `LineChart`, 220 px tall, full width
- Single line, **up to 12 points** (one per month, rolling window)
- Y-axis: 0–max(values, 10)%, auto-scale with 20% headroom
- X-axis: month labels (e.g. "Maí 25" → "Apr 26")
- Hover tooltip: "2026-03: 8,3% (N=2.084)"

**Disclaimer for first 12 months of production:**
`model_tracking_history` starts populating the month the
`build_model_tracking_snapshot.py` script first runs. Until 12 months of
history accrue, the chart renders all available points but shows a small
caption below:
```
Model tracking byrjaði [first_month]. Fullt 12-mánaða sögufall frá [first_month + 12].
```
Caption auto-hides once the dataset has ≥ 12 rows.

**Data source:** `model_tracking_history` (new — see Section 7).

**Copy under chart:**
```
Held-set MAPE er mean absolute percentage error á eignum sem módelið
sá aldrei í þjálfun. Lægri tala = nákvæmari spár. Nú um stundir er
iter4 að spá verði með 8,2% gagnkvæma skekkju.
```

### 6.4 Panel 2 — PI coverage trend

**Chart:**
- 2-line Recharts chart: cov80 (solid) + cov95 (dashed or secondary color)
- Target lines at 80% and 95% as horizontal dashed references
- Y-axis: 60–100%
- Same X-axis as Panel 1

**Data source:** `model_tracking_history` fields `cov80`, `cov95`.

**Copy under chart:**
```
Vissubil mælir hvernig spurningin "hvar er raunverð líklega?" stenst.
Stöng 80% ríkjandi við 80% er gott merki; stöng 79,1% (apríl 2026)
er innan statistical noise.
```

### 6.5 Panel 3 — Per-segment MAPE table

Static snapshot of current month. Table with 4 columns: Segment · MAPE · N · Status.

**Status indicators (Icelandic, factual tone — no drama):**

| Label | Dot color | Threshold |
|---|---|---|
| **Í lagi** | `var(--vm-success)` green | MAPE drift ≤ 0.5 pp AND coverage ≤ 5 pp off target |
| **Með athugasemd** | `var(--vm-accent-soft)` amber | MAPE drift 0.5–1.0 pp OR coverage 5–10 pp off target |
| **Sveiflast** | `var(--vm-hot)` orange | MAPE drift 1.0–2.0 pp OR coverage 10–15 pp off target |
| **Þarfnast skoðunar** | `var(--vm-danger)` red | MAPE drift > 2.0 pp OR coverage drift > 15 pp, or MAPE > 25% (SUMMERHOUSE) |

Drift measured as `abs(current_month_mape − 3mo_trailing_mean)`. Threshold
numbers are referenced by `validate_metrics.py` logic so status labels stay in
sync with alerting.

Severe-enough without alarmism. "Þarfnast skoðunar" signals something is going
on without implying the system is unusable.

**Data source:** `model_tracking_history` latest row, joined across all
segment rows in one query:
```sql
SELECT segment, mape, n_held, status_label
FROM model_tracking_history
WHERE period = (SELECT max(period) FROM model_tracking_history)
ORDER BY mape ASC;
```

**Copy above table:**
```
MAPE varierar milli eignaflokka. Apartments (APT_STANDARD, APT_FLOOR)
hafa lægstu skekkjuna — stærsta N í þjálfunarsafn og einsleitari
segment. Einbýli og sumarhús eru snöggari. SUMMERHOUSE er þekkt
vandamál og iter5 mun leysa það.
```

### 6.6 Panel 4 — Pipeline health

Static status card: green/yellow/red icons with timestamp per pipeline
component. Updates based on monthly orchestrator output.

Components listed (6 total):
- Síðasta endurnýjun (monthly orchestrator timestamp)
- **Síðasta uppfærsla kaupskrár: `[dags]` · `[N]` færslur síðan** (HMS
  þinglýsingar-lag ~2 vikur; explicit timestamp for transparency — bank audience
  especially wants to know how fresh the underlying transaction data is)
- `repeat_sale_index` freshness
- `ats_lookup` + `ats_dashboard_monthly_heat` freshness
- Conformal calibration version
- Listings data (⚠ scrape-gap flag until Áfangi 0 resolves)

**Data source:** derived from `model_tracking_history.created_at` + a
lightweight health query on the main dashboard tables.

### 6.7 Icelandic copy (`/markadur/modelstada`)

```
<title>  Líkansstaða — Hversu nákvæmt er iter4 verðmatslíkanið?
<meta>   Held-set MAPE, vissubil og per-segment skekkja fyrir iter4
         verðmatslíkanið. Uppfært mánaðarlega með transparent
         aðferðafræði.
<H1>     Líkansstaða
<sub>    Hversu nákvæmur er iter4 verðmatsmódelið?
```

### 6.8 SEO keywords

Primary: `verðmatslíkan fasteigna`
Secondary: `MAPE fasteignaverðmat`, `fasteignaverð nákvæmni`,
`repeat sale index iceland accuracy`

### 6.9 Performance

- 3 sequential queries, ~1 KB each, < 50 ms total
- No heavy charts (max 2 data series)
- ISR 10 min aligns with monthly refresh cadence (refresh is weekly at most,
  daily never)

---

## Section 7 — Data pipeline additions (consolidated)

All new Supabase tables / views / import tasks required for the v1 dashboard
build, consolidated here with CREATE statements and build-script signatures.

### 7.1 New tables

**7.1.1 `model_tracking_history`** (used by `/modelstada`, landing card 3)

```sql
CREATE TABLE model_tracking_history (
  period TEXT NOT NULL,  -- 'YYYY-MM' string for month
  created_at TIMESTAMPTZ DEFAULT NOW(),
  model_version TEXT NOT NULL,
  calibration_version TEXT NOT NULL,

  segment TEXT,  -- canonical_code, NULL for "overall pooled"
  n_held INT,

  mape NUMERIC,
  median_ape NUMERIC,
  bias_log NUMERIC,
  cov80 NUMERIC,
  cov95 NUMERIC,

  status_label TEXT,  -- 'ok' | 'caveat' | 'wavering' | 'broken'

  PRIMARY KEY (period, model_version, segment)
);

CREATE INDEX idx_model_tracking_period ON model_tracking_history(period);
```

**Build script:** `D:\verdmat-is\models\build_model_tracking_snapshot.py`
Runs monthly after retraining. Loads latest iter4 predictions + held-set
actuals, computes per-segment and overall metrics, inserts one row per
(period × segment). Append-only; never overwrites prior periods.

Signature:
```python
def main(period: str = None, model_version: str = None):
    """
    Append monthly model-tracking metrics to Supabase.
    period: 'YYYY-MM', defaults to current month
    model_version: matches predictions.model_version
    """
```

**7.1.2 `llm_aggregates_quarterly`** (used by `/ibudir`)

```sql
CREATE TABLE llm_aggregates_quarterly (
  year INT NOT NULL,
  quarter SMALLINT NOT NULL,
  period TEXT NOT NULL,  -- 'YYYY"Q"Q' like '2023Q2'
  canonical_code TEXT NOT NULL,
  region_tier TEXT,  -- NULL for "all regions pooled" rows

  -- Metric 1: Ástandsvísitala
  mean_interior_condition_score NUMERIC,
  n_listings_condition INT,

  -- Metric 2: Endurnýjunartíðni
  pct_recently_renovated NUMERIC,
  n_listings_renovation INT,

  -- Metric 3: Óskráð rými rate
  pct_has_unregistered_space NUMERIC,
  n_listings_unregistered INT,

  -- Metric 4: Sérlóð í APT
  pct_apt_with_serlod NUMERIC,
  n_listings_serlod INT,

  -- Metric 6: Agent framing distribution (Metric 5 deferred to v1.1)
  pct_framing_terse NUMERIC,
  pct_framing_standard NUMERIC,
  pct_framing_elaborate NUMERIC,
  pct_framing_promotional NUMERIC,

  n_listings_total INT,
  created_at TIMESTAMPTZ DEFAULT NOW(),

  PRIMARY KEY (year, quarter, canonical_code, region_tier)
);

CREATE INDEX idx_llm_agg_period ON llm_aggregates_quarterly(period);
CREATE INDEX idx_llm_agg_segment ON llm_aggregates_quarterly(canonical_code);
```

**Build script:** `D:\verdmat-is\build_llm_aggregates.py`
Single pandas `groupby` on `training_data_v2`. Runs monthly after
`rebuild_training_data.py`. Rebuilds entire table (not append-only) since it's
~800 rows max (20 years × 4 quarters × 10 segments × 3 regions).

**7.1.3 `last_listing_text`** (Danni-requested feature — see Section 8)

```sql
CREATE TABLE last_listing_text (
  fastnum BIGINT NOT NULL,
  thinglyst_dagur DATE,  -- date of sale associated with this listing
  sale_rank SMALLINT,    -- 1 = most recent sale, 2 = second most recent, 3 = third
  augl_id TEXT,          -- listing ID for provenance
  lysing_plain TEXT,     -- listing text, HTML tags stripped
  scraped_at TIMESTAMPTZ,
  PRIMARY KEY (fastnum, sale_rank)
);

CREATE INDEX idx_last_listing_fastnum ON last_listing_text(fastnum);
```

**Purpose:** when user clicks a row in the Sölusaga table on `/eign/[fastnum]`,
render the listing text from the auglýsingar that preceded that sale. Gives
the user "here's how this property was pitched at time of sale" — context for
understanding historical sale prices.

**Size-control rules (applied in build script):**

1. **Cap at top 3 most recent arm's-length sales per `fastnum`.** Average
   property has 1–2 sales; 3 is generous ceiling for common case. User
   scrolling sölusaga realistically clicks rows 1–3 anyway.
2. **Strip HTML tags from `lysing`** before storing. `listings_text_v2.pkl`
   contains raw HTML; we treat the text as plain-text/markdown-ish. ~60–70%
   size reduction per row.

Combined effect: ~150 MB worst-case estimate drops to ~60–80 MB. Comfortable
storage headroom maintained.

**Edge case:** if a property has more than 3 historical sales, clicking an
older row shows `"Sölulýsing ekki aðgengileg fyrir þessa sölu"` fallback
message. Acceptable — rare usage pattern.

**Build script:** `D:\verdmat-is\build_last_listing_text.py`. Joins
`sales_history.csv` × `listings_text_v2.pkl` × `listings_v2.pkl` by
`fastnum` and matched date windows, applies HTML strip + rank cap, runs
monthly.

### 7.2 New views (SQL only, no build script)

```sql
-- Landing hero metric A + secondary card 2 (CAGR)
CREATE VIEW repeat_sale_index_main_pooled AS
SELECT year, quarter, period,
  SUM(index_value_real * n_pairs_in_period) / SUM(n_pairs_in_period) AS index_real,
  SUM(index_value_nominal * n_pairs_in_period) / SUM(n_pairs_in_period) AS index_nominal,
  SUM(n_pairs_in_period) AS n_pairs
FROM repeat_sale_index
WHERE canonical_code IN ('APT_FLOOR','APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
GROUP BY year, quarter, period;

-- Landing timeline chart (3 lines)
CREATE VIEW repeat_sale_index_by_segment AS
SELECT canonical_code, year, quarter, period,
  SUM(index_value_real * n_pairs_in_period) / SUM(n_pairs_in_period) AS index_real,
  SUM(index_value_nominal * n_pairs_in_period) / SUM(n_pairs_in_period) AS index_nominal,
  SUM(n_pairs_in_period) AS n_pairs
FROM repeat_sale_index
WHERE canonical_code IN ('APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
GROUP BY canonical_code, year, quarter, period;

-- Landing hero metric B regime pill (needs ats_dashboard_monthly_heat imported
-- first — see 7.3)
CREATE VIEW latest_regime_per_cell AS
SELECT DISTINCT ON (canonical_code, region_tier)
  canonical_code, region_tier, year, month,
  heat_bucket, above_list_rate
FROM ats_dashboard_monthly_heat
WHERE canonical_code IN ('APT_FLOOR','APT_STANDARD','SFH_DETACHED','ROW_HOUSE')
  AND region_tier IN ('RVK_core','Capital_sub','Country')
ORDER BY canonical_code, region_tier, year DESC, month DESC;
```

All three are plain SQL views; no separate build script, no storage cost,
query-time evaluation.

### 7.3 Existing tables to import (currently on D:\ only)

**`ats_dashboard_monthly_heat`** (Áfangi 7 build output, exists as pkl/csv on
`D:\`, not yet in Supabase).

Required for `/markadsstada` slider + landing hero B regime pill + landing
above-list timeline.

- 2,501 rows × 9 cols (cells × months)
- Schema matches existing build output; direct CSV → COPY same as Phase 1A
- Re-imported monthly as part of orchestrator extension

Migration task for implementation chat:

**⚠ Schema below is TENTATIVE — verify against actual
`D:\ats_dashboard_monthly_heat.pkl` column list before migration.** First
implementation action on this task: run
`python -c "import pandas as pd; print(pd.read_pickle(r'D:\ats_dashboard_monthly_heat.pkl').dtypes)"`
and reconcile with the draft below. Adjust column names/types to match actual.

```sql
-- TENTATIVE — confirm columns from pkl before running this migration
CREATE TABLE ats_dashboard_monthly_heat (
  year INT NOT NULL,
  month SMALLINT NOT NULL,
  canonical_code TEXT NOT NULL,
  region_tier TEXT NOT NULL,
  heat_bucket TEXT,  -- 'hot' | 'neutral' | 'cold' | NULL
  above_list_rate NUMERIC,
  median_log_ratio NUMERIC,
  n_pairs INT,
  z_3v12 NUMERIC,  -- rolling 3-month vs 12-month z-score
  PRIMARY KEY (year, month, canonical_code, region_tier)
);
CREATE INDEX idx_ats_monthly_period ON ats_dashboard_monthly_heat(year, month);
```

### 7.4 Orchestrator extensions

Current `refresh_dashboard_tables.py` (per Áfangi 4d) runs monthly and
refreshes `repeat_sale_index` + `ats_lookup`. v1 dashboard adds three more
steps:

```
CURRENT:  refresh_cpi.py
          ↓
          refresh_kaupskra.py
          ↓
          rebuild_training_data.py
          ↓
          refresh_dashboard_tables.py  (builds repeat_sale_index + ats_lookup)
          ↓
          monthly_recalibration.py
          ↓
          validate_metrics.py

v1 ADDS:  refresh_cpi.py
          ↓
          refresh_kaupskra.py
          ↓
          rebuild_training_data.py
          ↓
          refresh_dashboard_tables.py
          ↓  NEW ──────────────────────────────────────────────
          refresh_dashboard_tables_v2.py  (orchestrator wrapper)
            ├─ refresh_dashboard_tables.py  (existing, no change)
            ├─ build_llm_aggregates.py       (new)
            ├─ build_last_listing_text.py    (new)
            └─ import_ats_monthly_heat_to_supabase.py  (new wrapper)
          ↓
          monthly_recalibration.py
          ↓
          build_model_tracking_snapshot.py  (new — runs after recal so it
                                              reflects latest calibration)
          ↓
          validate_metrics.py
```

New orchestrator script `refresh_dashboard_tables_v2.py` wraps existing one +
3 new sub-scripts in an atomic transaction (all-or-nothing rollback on error).

### 7.5 Import strategy

All new tables use the same COPY-staging pattern proven in Phase 1A + iter4
rebuild:
1. Build CSV/TSV locally on D:\ via Python
2. Connect to Supabase pooler (aws-1-eu-north-1, port 6543)
3. TRUNCATE target table (or CREATE TEMP staging + swap for very large)
4. COPY FROM STDIN
5. Verify row count vs expected

For `model_tracking_history` (append-only): skip TRUNCATE, just INSERT the new
period's rows via executemany or batch COPY. Handle duplicate-period conflicts
by ON CONFLICT (period, model_version, segment) DO UPDATE.

### 7.6 Storage impact

Current Supabase DB: 586 MB. New additions:
- `model_tracking_history`: ~50 KB after 12 months × 10 segments × 2 model
  versions
- `llm_aggregates_quarterly`: ~100 KB (800 rows × ~10 numeric cols)
- `last_listing_text`: ~150 MB worst-case (170K sales × 1 KB avg lysing —
  consider LIMIT to last 3 sales per fastnum to cap)
- `ats_dashboard_monthly_heat`: ~300 KB (2500 rows × 9 cols)

**Total added:** ~150-160 MB, dominated by `last_listing_text`. Supabase Pro
cap is 8 GB. Comfortably within budget.

### 7.7 Build order (recommended)

For implementation chat (not prescriptive, but efficient):

1. **Foundation** — create all new tables + views schema via a single
   migration SQL file. Safe to run idempotently.
2. **ats_dashboard_monthly_heat import** — no-code-dependency data, unblocks
   Sections 2B and 4 immediately.
3. **build_llm_aggregates.py** — fast groupby, small output, unblocks Section 5.
4. **build_model_tracking_snapshot.py** — requires current iter4 held-set
   metrics; can pull from Áfangi 2-5 deployment logs OR re-compute from
   iter4a_predictions.pkl.
5. **build_last_listing_text.py** — largest build, requires listings_text_v2
   join. Can be parallel with other work once table schema exists.
6. **Orchestrator v2 wrapper** — integrates all new scripts.

---

## Section 8 — `sale_year` waterfall fix (carry-over UX)

**Scope note:** This section documents a UX fix on the existing eigna-síða
(`/eign/[fastnum]`), NOT a new dashboard feature. Co-shipping with Áfangi 4
deploy because (a) styling consistency across dashboard + eign waterfall
matters, (b) implementation chat already touches the eign-síða waterfall
component file.

### 8.1 The problem

iter4's SHAP waterfall on `/eign/[fastnum]` lists `sale_year = 2026` as one of
the top feature attributions, with a positive contribution like `+6,4 M kr`.
This is confusing to end-users:

- It's not an attribute of the property itself ("this home has sale_year
  2026" is nonsensical)
- It's a market-index anchor for the model — the year the valuation is priced
  at, not a characteristic of the house
- Users interpret it as "the model thinks 2026 adds 6 M kr to the value of
  this home," which is both literally wrong and obscures the real attributions
  (EINFLM, matsvaedi_bucket, etc.)

### 8.2 The fix

**Default view on `/eign/[fastnum]`:** hide `sale_year`, `sale_month`, and
`predicted_at` from the SHAP waterfall. These are pure time anchors — the
"when" of the valuation, not attributes of the property.

**`age_at_sale` stays visible** (relabeled). It is a property attribute (how
old is the house at sale time) even though it's derived from `sale_year`.
Nýrri eign → hærra verð, all equal. Hiding it would remove a real driver the
user should see.

**Debug/power-user view (`?mode=debug` query param):** unchanged. All SHAP
features shown, including time anchors.

### 8.3 Implementation mechanics

In `/app/eign/[fastnum]/page.js` where the waterfall SHAP rows are built:

```javascript
const TIME_ANCHOR_FEATURES = new Set([
  'sale_year', 'sale_month', 'predicted_at',
  // NB: age_at_sale is intentionally NOT in this set — it's a property
  // attribute (aldur við sölu), not a time anchor, even though derived from
  // sale_year. See DASHBOARD_SPEC_v1 §8.2.
]);

const userFacingAttributions = rawAttributions.filter(
  (a) => showDebug || !TIME_ANCHOR_FEATURES.has(a.feature_name)
);
```

### 8.4 What to preserve

- Debug mode unchanged
- SHAP math unchanged — all features still contribute to the sum; we only hide
  them in display
- "Top 10 features" becomes "Top 10 property-characteristic features" — if
  time anchors would have been in top 10, the next-ranked feature fills the
  slot
- Waterfall totaling: since we're hiding non-zero contributions, the visible
  waterfall no longer sums to the full prediction. Add a footer row with the
  sum of hidden contributions so math still balances for readers who check.

### 8.5 `age_at_sale` relabel

Rename feature label in waterfall UI from internal name `age_at_sale` to the
Icelandic phrase **`Aldur við sölu`**. Value display stays numeric (e.g.
"23 ár"). Tooltip explains: "Aldur eignarinnar á söludegi. Nýrri eign →
hærra verð að öðru óbreyttu."

### 8.6 Copy changes

Waterfall sub-header (above rows):
```
Hvaða þættir eign-sjálfs mest áhrif á matið?
```

Footer row (after top-10):
```
Markaðsstaða         +X,X M kr     [?]
```

"Tímatengsl" dropped — user understands sale_year/month is implicit in
"markaðsstaða". Shorter reads cleaner in info-dense waterfall.

Tooltip on the `[?]`:
```
Þessi leiðrétting endurspeglar markaðsaðstæður á þeim tíma sem verðmatið
var gert (ekki eigninni sjálfri). Notaðu ?mode=debug til að sjá niðurbrot.
```

`?mode=debug` link in tooltip gives advanced users an escape hatch without
cluttering the default UI.

### 8.7 Deployment strategy

**Co-ship with Áfangi 4 deploy.** Same commit, same PR, same QA cycle.

Rationale:
- Styling consistency: Áfangi 4 is the largest UI refresh in Sprint 2; the
  waterfall fix inherits any shared primitives refreshed during that work
- User cognitive load: separate deploys mean users see eign-síða change one
  day, dashboard the next → confusion. One deploy = one new-look moment
- Git discipline: one PR = one QA cycle

**Contingency:** If the waterfall fix exposes a critical bug (unlikely — the
change is additive filter + label rename), spin it out to its own small PR
and defer dashboard deploy until the fix stabilizes. Default path remains
co-ship.

---

---

## Section 9 — Decision points resolved

All 🔶 decision points surfaced during planning, with final resolution:

| # | Decision | Resolution | Section |
|---|---|---|---|
| 1 | v1 route scope | Ship 4 of 5: `/markadur`, `/visitala`, `/markadsstada`, `/ibudir`, `/modelstada`. Defer `/tilbod` (scrape-gap blocker). | §1.3 |
| 2 | Hero metric | A+B hybrid: 12-mo real % as hero number, regime pill as subline. C (above-list) drops to secondary card. | §2.2 |
| 3 | Scrape-gap slider | Yellow hatched overlay on gap portion of slider + soft caveat. Slider stays free-ranging; default position = latest data month (not pre-gap). | §4.3 |
| 4 | Repeat-sale explorer scope | 4×3 default grid (APT_FLOOR, APT_STANDARD, SFH_DETACHED, ROW_HOUSE × RVK_core, Capital_sub, Country). Per-row segment toggle for secondary variants. | §3.1 |
| 5 | Domain/URL | verdmat.is already live (Sprint 2). No change in Áfangi 4. | — |
| 6 | SEO primary keyword | `fasteignamarkaður ísland` on landing. Secondary per sub-route in §2.9. | §2.9 |
| 7 | Back-projection placement | BOTH `/markadsstada` and `/eign/[fastnum]`. Same component, same API. | §4.6 |
| 8 | Section 5 metric 5 (orðatíðni) | Deferred to v1.1 (requires new table + build script + orchestrator extension, heaviest lift of the 6). | §5.1, §5.5 |
| 9 | Section 5 editorial copy | Placeholder structure in spec (Editorial hook + Narrative arc + Key callout TBD). Final prose written at implementation phase once real data is plotted. | §5.8 |
| 10 | Section 6 status labels | Icelandic, factual tone: Í lagi / Með athugasemd / Sveiflast / Þarfnast skoðunar. Thresholds tied to `validate_metrics.py`. | §6.5 |
| 11 | MAPE trend window | 12 months (with 6-month disclaimer caption until data accrues). | §6.3 |
| 12 | Pipeline health panel | 6 items, adds explicit "Síðasta uppfærsla kaupskrár" for transparency. | §6.6 |
| 13 | `last_listing_text` size control | Cap at 3 most recent arm's-length sales per fastnum + strip HTML tags. ~60-80 MB storage. | §7.1.3 |
| 14 | Orchestrator strategy | Atomic rollback across all v1 dashboard tables (same pattern as existing `refresh_dashboard_tables.py`). | §7.4 |
| 15 | `ats_dashboard_monthly_heat` schema | Tentative in spec; verify against actual pkl as first implementation action before migration. | §7.3 |
| 16 | Waterfall hide-set | `{sale_year, sale_month, predicted_at}`. `age_at_sale` stays visible as property attribute, relabeled "Aldur við sölu". | §8.2, §8.5 |
| 17 | Waterfall footer copy | `Markaðsstaða +X,X M kr` (shorter than draft "Markaðs- og tímatengsl"). Tooltip explains anchor + debug-mode escape. | §8.6 |
| 18 | Waterfall fix deploy | Co-ship with Áfangi 4 in one PR. Contingency: spin out if critical bug. | §8.7 |

---

## Section 10 — Build order, time estimates, dependencies

Recommended implementation order for the next chat picking this up.

### 10.1 Build order

```
Phase A — Data infrastructure (unblocks everything)
├── A1. Migration SQL file: all new tables + views + indexes             [2 h]
├── A2. Verify ats_dashboard_monthly_heat pkl schema                     [0.5 h]
├── A3. Import ats_dashboard_monthly_heat to Supabase                    [1 h]
└── A4. build_llm_aggregates.py + initial data load                       [3 h]

Phase B — Data scripts + orchestrator integration                        [6 h]
├── B1. build_model_tracking_snapshot.py (computes + inserts)             [3 h]
├── B2. build_last_listing_text.py (join + HTML strip + top-3 cap)        [2 h]
└── B3. refresh_dashboard_tables_v2.py wrapper with atomic rollback       [1 h]

Phase C — Frontend routes (parallelizable by component)
├── C1. /markadur landing (A+B hero, 3 cards, 3-line timeline, banner)    [8 h]
├── C2. /markadur/visitala (4×3 grid, toggles, crash-band shading)         [10 h]
├── C3. /markadur/markadsstada (slider, heat-map, back-projection)        [14 h]
├── C4. /markadur/ibudir (5 metrics, editorial placeholder structure)      [8 h]
└── C5. /markadur/modelstada (4 panels, status labels, pipeline health)   [6 h]

Phase D — Carry-over + polish
├── D1. Eign-síða waterfall fix (Section 8 — hide + relabel + footer)    [3 h]
├── D2. Scrape-gap banner component (shared across routes)                [1 h]
├── D3. SEO metadata + OG image generation for all routes                 [3 h]
└── D4. Mobile QA pass on all 4 new routes + eign-síða                    [4 h]

Phase E — Deploy
├── E1. Staging Vercel deploy + full route curl verification              [1 h]
├── E2. Production deploy (co-shipped with waterfall fix)                 [0.5 h]
└── E3. STATE + DECISIONS sync + docs/ sync to GitHub                     [1 h]
```

Total estimated: **~75-85 hours** active implementation work. At 8 h/day focused
pace → 10 working days. Plausible for a 2-week sprint with buffer.

### 10.2 Dependencies chart

```
                 ┌──── A1 migration SQL
                 │
                 ├──── A2 verify pkl ──┐
                 │                     │
                 │                     ▼
                 ├──── A3 import ats_dashboard_monthly_heat ──┐
                 │                                             │
                 ├──── A4 llm_aggregates ──┐                   │
                 │                         │                   │
                 ▼                         │                   │
       ┌── B1 model_tracking_snapshot ──┐  │                   │
       │                                │  │                   │
       ├── B2 last_listing_text ────────┤  │                   │
       │                                │  │                   │
       └── B3 orchestrator_v2 wrapper ──┤  │                   │
                                        │  │                   │
                    ┌───────────────────┼──┴───────────────────┤
                    │                   │                      │
                    ▼                   ▼                      ▼
                  C1 landing       C4 ibudir              C3 markadsstada
                  (needs B1        (needs A4)             (needs A3)
                   for cards,
                   A3 for pill)
                    │                   │                      │
                    │           ┌───────┴──────┐               │
                    │           │              │               │
                    ▼           ▼              ▼               ▼
                  C2 visitala (independent — only needs repeat_sale_index
                               which already exists)
                                    │
                                    ▼
                                  C5 modelstada (needs B1)
                                    │
                                    ▼
                                  D1 waterfall fix (eign-síða, independent
                                                     of C-phase work)
                                    │
                                    ▼
                                  D2-D4 polish
                                    │
                                    ▼
                                  E phase deploy
```

**Critical path:** A1 → A3 → C3 (markadsstada is most data-dependent and
most complex UI). All other routes can be worked in parallel by separate
devs / sessions after Phase A.

**Zero-data-dependency route:** `/markadur/visitala` (C2). Uses only
`repeat_sale_index` which already exists. Can be built Day 1 in parallel with
Phase A data work.

**Implementation-chat handoff note:** start with Phase A data migration to
unblock the other phases. If data work hits a snag (schema mismatch on
ats_dashboard_monthly_heat being most likely), proceed with C2 visitala in
the meantime while the Phase A issue is resolved.

### 10.3 Known limitations / v1.1 roadmap

Items explicitly not in v1 but documented in spec for continuity:

- `/markadur/tilbod` (TOM distribution) — needs scraper replacement (Áfangi 0)
- Metric 5 (orðatíðni) + `listing_text_freq_quarterly` table — requires new
  offline NLP pipeline
- Dynamic per-page OG images — static for v1, dynamic in v1.1
- Real editorial narrative copy on `/ibudir` — drafted at implementation with
  real data, refined in v1.1 as more quarterly data accrues

---

## End of spec

Planning session complete. All 10 sections filled, 18 decision points
resolved, build order + dependencies mapped, time estimates grounded.

Next chat picks up this document verbatim and executes Phase A through E.
No further planning expected; if the implementation chat needs a design
pivot, it surfaces the question for Danni rather than edit-in-place on the
spec.
