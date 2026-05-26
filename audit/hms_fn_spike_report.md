# HMS false-negative spike — halt report

**Generated**: 2026-05-21T17:26:34+00:00
**Sample size**: 1000 (random sample of 392,026 HTTP-500 rows, seed=42)
**Plan**: `C:\Users\danie\.claude\plans\i-have-a-large-indexed-lynx.md`

## Headline

- **False-negative rate (overall)**: **18.5%** (Wilson 95% CI 16.2–21.0%)
- **Estimated total recoverable real properties**: **~71,803** (dead-zone ~70,432 + healthy-zone ~1,370)
- **Dead-zone FN rate**: 19.8% (CI 17.4–22.5%) on 355,275 dead-zone 500s
- **Healthy-zone FN rate**: 4.6% (CI 1.8–11.2%) on 29,816 healthy-zone 500s
- **Anchor 2226598 in sample**: yes — classified `recovered-200` (flat=200, leit=None, attempts=1)

## Step 0 — Time-clustering signal (the big finding)

Phase C had a sustained API dead zone from **2026-05-16T07:00 → 2026-05-17T21:00 UTC (~38 hours)**.
Hit rate during the dead zone: **0.0%** sustained per hour (9,200-9,600 fastnums/hr, all HTTP 500).
Hit rate outside the dead zone (healthy windows): 9-76% per hour.
Phase B baseline 500-rate: 0.08% (97 / 124,835).

Phase C 500-row distribution:
- Dead zone:       355,275 500s  (5,125 200s)
- Healthy zone:     29,816 500s  (23,009 200s)

## Step 1-3 — Probe outcomes

| Bucket | n | % of sample |
|---|---:|---:|
| recovered-200 | 185 | 18.5% |
| recovered-via-leit-only | 0 | 0.0% |
| persistent-500 | 815 | 81.5% |
| inconclusive (WAF / exception) | 0 | 0.0% |

**Recovered cases time-distribution**: 181/185 fell in dead-zone, 4/185 in healthy zone.

**Attempts-to-recover histogram** (recovered-200 only): 1=185

## Eyeball validation — 10 random recovered cases

| fastnum | scrape ts | stadfang | póstn. | landeign_nr | notkun | sveitarfélag | einflm | fasteignamat |
|---|---|---|---|---|---|---|---|---|
| 2047164 | 2026-05-16T07:27:12+00:00 | Brúnastekkur 5 | 109 | 111826 | Einbýlishús | Reykjavíkurborg | 191 | 129600 |
| 2066398 | 2026-05-16T08:28:56+00:00 | Þverbrekka 2 | 200 | 116534 | Íbúð á hæð | Kópavogsbær | 109.6 | 74700 |
| 2295402 | 2026-05-17T02:15:03+00:00 | Dalaþing 2 | 203 | 202796 | Einbýlishús | Kópavogsbær | 270.7 | 196900 |
| 2339204 | 2026-05-17T05:35:53+00:00 | Lautavegur 14 | 650 | 196244 | Íbúðarhúsalóð | Þingeyjarsveit | — | 2340 |
| 2212918 | 2026-05-16T20:14:08+00:00 | Hafnarskeið 8A | 815 | 172303 | Iðnaður | Sveitarfélagið Ölfus | 3190.4 | 163570 |
| 2128518 | 2026-05-16T13:11:46+00:00 | Hrófá 1  lóð 1 | 511 | 210515 | Einbýlishús | Strandabyggð | 62.7 | 13700 |
| 2346999 | 2026-05-17T06:20:28+00:00 | Ásgarður | 803 | 211849 | Einbýlishús | Flóahreppur | 198.8 | 15850 |
| 2160939 | 2026-05-16T15:44:18+00:00 | Sunnuhvoll lóð | 616 | 204989 | Lóð | Grýtubakkahreppur | — | 493 |
| 2314861 | 2026-05-17T03:33:38+00:00 | Ósvör 12 | 603 | 179864 | Verbúð | Akureyrarbær | 17.6 | 4049 |
| 2066156 | 2026-05-16T08:27:39+00:00 | Vogatunga 79 | 200 | 116454 | Íbúð á hæð | Kópavogsbær | 69.1 | 69850 |

## Recommendation

### (a) Full re-scrape of all 392K 500-rows — STRONGLY recommended

Estimated recovery: ~71,803 real properties currently missing from the staging DB.
Wall-clock at scrape-equivalent rate (~157/min): ~41.6 hours.
The dead-zone bulk (355,275 rows) almost certainly contains the lion's share of recoverable properties.

## Out of scope (not done here)

- No Supabase writes; no production-scraper edits; no audit of sibling scrapers.
- Decision on (a)/(b)/(c) deferred to the user. Next session implements the chosen path.

