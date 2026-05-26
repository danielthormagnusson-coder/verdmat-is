# HMS full recovery — halt report

**Generated**: 2026-05-24T23:08:46+00:00
**Run started**: 2026-05-21T20:58:18+00:00
**Elapsed**: 74h 10m 27s
**Target population (start)**: 392,026 HTTP-500 rows

## Headline

- **Recovered (was 500, now 200)**: **77,859**
- **Confirmed-still-500 (after retry)**: **314,167**
- **Untouched (left in queue)**: **0**
- **Realized FN rate**: **19.86%** of touched rows

## Per-phase breakdown

| Phase | Recovered | Confirmed-500 | Untouched |
|---|---:|---:|---:|
| A | 0 | 6,838 | 0 |
| B | 0 | 97 | 0 |
| C | 77,859 | 307,232 | 0 |

## Dead-zone vs healthy-zone (by ORIGINAL fetched_at)

Dead-zone window: 2026-05-16T07:00 → 2026-05-17T21:00 UTC (~38h)

| Zone | Recovered | Confirmed-500 | Realized FN |
|---|---:|---:|---:|
| Dead-zone     | 75,098 | 282,428 | 21.00% |
| Healthy-zone  | 2,761 | 31,739 | 8.00% |

## Run health

- WAF pauses:    0
- Outage pauses: 0
- Completed cleanly (all targets touched).

## Next steps (user decision)

- Decide Supabase-sync scope: D3 (originally 30K new properties) now needs to absorb ~77,859 additional fastnums.
- Confirmed-still-500 count (314,167) sets a new upper bound on truly-empty Phase C slots.
- Spike-validated production-template hardening (folding outage-detection + 500-aware backoff into the canonical scraper) is now ready — see separate session.

