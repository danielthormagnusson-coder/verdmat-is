# Cross-source URL pattern discovery — verdmat.is + fastinn.is

**Date**: 2026-05-07
**Method**: curl with `Mozilla/5.0` UA, manual URL probing, HTML inspection. No headless browser, no JS execution. Conservative throttle (≥0.5 s between requests, identifying UA).
**Goal**: locate fastnum-keyed URL patterns on each site to determine viability as cross-source registry probes for the Áfangi 0 Stage 1 backfill.

---

## verdmat.is — public valuation form, no per-property URL surface

`robots.txt`:
```
User-agent: *
Allow: /
Sitemap: https://verdmat.is/sitemap.xml
```
Permissive, sitemap declared.

**Sitemap entries (complete list, 3 URLs)**:
- `https://verdmat.is/`
- `https://verdmat.is/verdsaga`
- `https://verdmat.is/god-rad`

**Probed candidate URL patterns** (all returned **HTTP 307**):
| Path | Code | Note |
|---|---|---|
| `/eign/2526172` | 307 | redirected, no per-property route |
| `/fasteign/2526172` | 307 | same |
| `/?fastnum=2526172` | 307 | same |
| `/verdsaga/2526172` | 307 | same |
| `/api/valuation` | 307 | no public API |
| `/api/fasteignir/2526172` | 307 | no public API |
| `/api/property/2526172` | 307 | no public API |
| `/api/verd/2526172` | 307 | no public API |
| `/api/verdsaga` | 307 | no public API |
| `/api/v1/property/2526172` | 307 | no public API |

**Site shape**: valuation tool (Icelandic real estate appraisal). Submit a form (name, address, postal code, email, phone) → receive a valuation by email. There is no per-property page exposed via URL; the data flow is entirely form-driven and presumably backed by a private API used internally.

**Verdict — verdmat.is is not a viable cross-source.** No per-fastnum URL surface exists. Cannot probe a 100-candidate slice because there is nothing to probe.

---

## fastinn.is — Clerk-authenticated, no public read path

`robots.txt`:
```
User-Agent: *
Allow: /

Sitemap: https://fastinn.is/sitemap-index
```
Permissive on robots.txt (matches prior pre-flight finding).

**Site stack**: Next.js SPA hosted on Vercel (`Server: Vercel`, `X-Powered-By: Next.js`, `X-Matched-Path: /api/v1/[[...route]]`).

**Auth posture**: **Clerk authentication required for property data.** The site loads `https://clerk.fastinn.is/npm/@clerk/clerk-js@5/dist/clerk.browser.js` and gates the API behind Clerk session tokens.

**HTML-route surface (page shells, all return HTTP 200)**:
- `/fasteignir/<fastnum>` — page route exists for any integer; **all return identical 63,490-byte HTML shells regardless of fastnum**:
  - `/fasteignir/2526172` (known-good) → 63,490 b, title `"undefined, undefined undefined"`, only 3 echoes of the fastnum (URL-state echoes, not data)
  - `/fasteignir/2400000` (evalue.is 204) → identical 63,490 b
  - `/fasteignir/9999999` (obviously invalid) → identical 63,490 b
- The page is a JS shell that fetches data client-side after auth. Without Clerk auth + JS execution, no data is rendered or embedded.

**API surface (HTTP probes, GET, no auth)**:
| Path | Code | Body | Auth header |
|---|---|---|---|
| `/api/fasteignir/2526172` | 404 | 62,133 b (HTML 404 page) | — |
| `/api/properties/2526172` | 404 | 62,133 b (same) | — |
| `/api/eign/2526172` | 404 | same | — |
| `/api/v1/fasteignir/2526172` | **401** | `{"message":"Unauthorized"}` | `X-Clerk-Auth-Status: signed-out` |
| `/api/v1/leit` | **401** | `{"message":"Unauthorized"}` | same |
| `/api/v1/search` | **401** | `{"message":"Unauthorized"}` | same |
| `/api/v1/public/fasteignir/2526172` | **401** | `{"message":"Unauthorized"}` | same — `public` path-segment is not a bypass |

**Found the live API**: `/api/v1/fasteignir/<fastnum>`. **It is auth-gated.** Auth is enforced by Clerk middleware (`X-Clerk-Auth-Reason: session-token-and-uat-missing`).

**Verdict — fastinn.is is not a viable cross-source under our ethical posture.** A real API exists, the URL pattern is clean, and it likely returns rich JSON when authenticated. But:
- Probing it requires a valid Clerk session token (sign-up + login + cookie/JWT extraction).
- Bypassing or scripting against the auth layer is **materially more aggressive** than evalue.is's `Disallow: /` posture (which is robots.txt non-compliance against an open API). Clerk is an explicit access-control system; circumventing it for unauthorized data access is a step beyond.
- Even if we obtained a valid signed-in session via legitimate sign-up, it is unclear whether the TOS permits programmatic batch retrieval — most authenticated SaaS-style products implicitly forbid this.

**Reasonable next step would be a business contact** (similar in shape to the HMS dialogue draft) requesting API access for academic/research/cross-validation purposes — not a unilateral scrape.

---

## Net result for Phase 1

Phase 1 was tasked with discovering URL patterns to enable Phases 2-4 (positive control + 2.4M probe + sub-gap probe on alternative sources).

- **verdmat.is**: no per-fastnum URL surface exists. Phases 2-4 not executable. Halt this branch.
- **fastinn.is**: per-fastnum API exists but is auth-gated. Phases 2-4 not executable under our ethical posture. Halt this branch.

**Both branches halt at Phase 1.** Phases 2-4 do not run. The cross-source probe report (next file) documents the strategic implication for evalue.is single-source confidence.
