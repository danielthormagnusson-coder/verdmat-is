# Cross-source probe report — verdmat.is + fastinn.is viability check

**Date**: 2026-05-07
**Scope**: pre-scaling viability check for treating `verdmat.is` and `fastinn.is` as supplementary sources alongside `evalue.is`. Triggered by the v1+v2 pilot finding that evalue.is returned 0/400 across the 2.4M bucket — the question being whether those 204s mean "fastnum truly unassigned in HMS" or "evalue.is missed rows that other aggregators have".
**Status**: **HALTED at Phase 1** for both sites. Phases 2-5 of the original task plan did not execute. This report is the halt-with-diagnostics deliverable.
**Companion doc**: `audit/cross_source_url_patterns.md` (full URL probe transcript).

---

## Headline

- **verdmat.is**: not a viable cross-source. No per-fastnum URL surface exists. Sitemap has 3 entries (`/`, `/verdsaga`, `/god-rad`); every `/eign/<id>`, `/fasteign/<id>`, `/?fastnum=<id>`, `/api/property/<id>` and similar variant returns HTTP 307. Site is a public valuation form, not a registry-style site.
- **fastinn.is**: per-fastnum API exists at `/api/v1/fasteignir/<fastnum>` but is **Clerk-authenticated**. Unauthenticated probes return HTTP 401 with `X-Clerk-Auth-Status: signed-out`. Pursuing this source requires either (a) sign-up + session-token extraction (likely TOS-violating for batch retrieval) or (b) business contact for legitimate API access. Either is a Phase-2-type project, not a 5-minute probe.
- **Net**: empirical cross-source verification of the evalue.is 204s **cannot proceed under the current ethical posture** without significantly expanding scope.

---

## What did NOT happen this session

| Phase | Original plan | Actual |
|---|---|---|
| 1 — URL discovery | discover fastnum-keyed URL patterns on both sites | done; both sites failed viability |
| 2 — positive control | probe 5 known-good fastnums on viable sites | **skipped** — no viable site |
| 3 — 2.4M probe | probe 2,400,000-2,400,099 on viable sites | **skipped** — no viable site |
| 4 — sub-gap probe | probe 2,389,000-2,389,099 on viable sites | **skipped** — no viable site |
| 5 — report | comparison report | this halt-diagnostic report instead |

No HTTP traffic was sent against either site beyond URL-pattern discovery (~20 small requests total, identifying UA, ≥0.5 s spacing). No Clerk auth bypass was attempted. No headless browser was used.

---

## Strategic implication for evalue.is single-source confidence

The original task framed two competing hypotheses for the 0/400 evalue.is finding in the 2.4M bucket:
- **(a)** fastnum truly unassigned in HMS → high confidence in single-source strategy
- **(b)** evalue.is missed rows that other aggregators have → need multi-source

**Empirical resolution of (a) vs (b) is not currently achievable.** Neither alternative source is probeable without a substantial scope expansion (verdmat.is doesn't have the data; fastinn.is gates it behind Clerk).

What we CAN say with the data we have:
1. evalue.is has been Danni's working source for 124,835 rows over the past year — the source is empirically known to carry registry data (the positive controls in `backfill_pilot.db` confirm fields like `heimilisfang`, `fasteignamat`, `flatarmal`, `hnitWGS84_*` populate correctly).
2. evalue.is's relationship to HMS is derivative — it is an aggregator that pulls from HMS-published kaupskrá feeds (per `SCRAPER_SPEC v1` framing). It is structurally unlikely to have rows that HMS doesn't publish, and equally unlikely to publish rows it doesn't have indexed itself.
3. The 2.4M bucket being 0/400 in evalue.is is consistent with HMS not issuing fastnums in that range. The competing hypothesis (evalue.is missed an entire 100K integer-bucket while indexing every neighboring bucket densely) is a much weaker prior — it would imply a structural indexing gap that we have no other evidence for.
4. The 2 trailing-range hits in `2,541,715–2,541,814` (probe v2) further support this: evalue.is updates promptly with new HMS issuances, with no apparent gap-prone behavior.

**Recommendation**: proceed with single-source evalue.is for Stage 1 backfill. The 2.4M-bucket-empty hypothesis is supported by the existing 0/400 evidence and is not contradicted by any cross-source evidence (because there is no accessible cross-source). If a multi-source merge becomes desirable later (e.g., for Track A active-listings cross-validation or for image-archive sourcing diversification), the fastinn.is API access conversation can be reopened as a business engagement.

---

## What it would take to actually resolve (a) vs (b)

Documented for future reference, not as a recommended action:

### Option A — fastinn.is via legitimate sign-up + session-token reuse
**Cost**: ~1 h to sign up, extract Clerk session token, write a token-aware probe variant of `backfill_evalue_range.py`. Then ~6 min to probe the same 2.4M slice.
**Risk**: TOS-violation if fastinn.is restricts batch use of authenticated sessions. Uncertain — would need to read their TOS first.
**Discoverability**: yes — Clerk session tokens are extractable from browser dev tools and reusable in scripted GET requests until the session expires (~24 h or until rotated).
**Verdict**: not a no-cost-no-risk path. Should not be done unilaterally.

### Option B — fastinn.is via business contact
**Cost**: ~2 h email drafting, then unknown latency (days to weeks for a response).
**Risk**: low.
**Outcome**: API access if granted; otherwise back to where we are now.
**Verdict**: a reasonable parallel track if cross-source verification matters more than launching Stage 1 backfill on schedule. But it's not gating — Stage 1 can ship single-source while the dialogue runs.

### Option C — HMS frontend re-discovery
**Cost**: ~4-8 h (HMS rebuilt to Next.js + Vercel + Prismic per `SCRAPER_SPEC v1.1` Amendment 1; the API surface is now `/api/fasteignaskra/leit` behind Vercel Security Checkpoint anti-bot). Re-discovery requires defeating the anti-bot.
**Risk**: substantially more aggressive ethical posture than evalue.is. Vercel Security Checkpoint is an explicit access control.
**Verdict**: dominated by Option B (HMS dialogue).

### Option D — accept the 204s as ground truth
**Cost**: zero — proceed with current evidence.
**Risk**: if 2.4M bucket actually does have HMS data that evalue.is missed, we'd ship a registry-incomplete `properties` table. Probability low (per §3-4 reasoning above) but non-zero.
**Verdict**: pragmatic default. Recommended for Stage 1 launch posture.

---

## Mapping shim implications

Single-source architecture remains the assumption. The mapping shim from Phase 2 of the v1 pilot plan does NOT need a multi-source merge layer at this point.

The schema-position-collision finding from probe v2 (fastnum 2541716 collapsed positions 9 and 14 in the schema map) still applies and is the actual mapping-shim concern — independent of single-vs-multi-source.

---

## Updated recommendation for next session

The original task expected this report to inform a single-vs-multi-source decision before next session. Given Phase 1 halt:

1. **Lock single-source-evalue.is** as the Stage 1 backfill architecture. (Effective null decision — it's been the assumption all along; this just removes the hypothetical multi-source branch from the planning surface.)
2. **Lock the trailing-range walk as the first scaling target** (per pilot v2 report §Updated scaling recommendation). Ready to execute.
3. **Image-ownership policy locking** (the Áfangi 0.y Amendment 4 next-session goal) proceeds as planned. Use the 5 positive-control + 2 trailing-hit `augl_json` payloads in `backfill_pilot.db` for sizing.
4. **Optional parallel track**: draft a brief fastinn.is business-contact email (~30 min), similar in shape to `audit/hms_dialogue_draft.md`. Not gating Stage 1, just opens a long-term option.
5. **No commits, no scaling actions, no Supabase writes** this session, per the user's explicit pause directive.

---

## Artifacts

- `audit/cross_source_url_patterns.md` — Phase 1 transcript (verbatim probes, headers, response sizes).
- `audit/cross_source_probe_report.md` — this document.
- No DB additions, no scraper additions. The cross-source probe was discovery-only and produced no row data.
