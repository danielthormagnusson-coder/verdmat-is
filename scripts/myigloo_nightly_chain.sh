#!/bin/bash
# myigloo_nightly_chain.sh — myigloo nightly FULL-SWEEP chain (fetch -> parse -> promote both layers).
#
# myigloo is a small (~870-listing), friendly CloudFront API with no throttle (CC3 probe
# 2026-06-27): a full sweep is ~15-22 min at 1s politeness, so — unlike mbl, which must run
# nightly DELTAs because its Hasura layer hard-caps 16/page and soft-throttles — myigloo runs
# a full re-sweep every night. The full sweep IS the active set: presence in tonight's sweep
# drives the lifecycle diff (promote_myigloo_listings_append).
#
# STEPS (serial, abort-not-retry — a failed night is a signal for Danni, not a retry loop):
#   1. fetch_myigloo                       full sweep -> raw_myigloo.db (content-hash idempotent,
#                                          run_id-stamped; worst unattended failure = wasted requests)
#   2. parse_myigloo                       pending detail blobs -> parsed_myigloo
#   3. promote_myigloo (canonical)         parsed -> scraper.listings_canonical (old fold path, kept
#                                          in sync during the dual-layer transition)
#   4. promote_myigloo_listings_append     parsed + active-set diff -> scraper.listings (Layer 1) +
#                                          listing_price_history (active/withdrawn lifecycle)
#
# RE-BASELINE (one-time, do not misread): the FIRST nightly under the canon-fix (commit 6734c8e)
# logs changed=1 on ~all listings because the previously-stored hashes are old-canon. This is a
# one-time re-baseline, NOT a content change — stable (~changed=0 on unchanged listings) from
# night 2. The morning report prints this banner until a marker file records that night 1 ran.
#
# Keyless: no step calls an LLM (no Haiku) — ANTHROPIC_API_KEY is not required.
# Exit codes: 0 clean / 1 chain abort / 2 pre-flight refusal — readable as the task last-result.
# Morning report: scraper_data/night_logs/myigloo_night_YYYYMMDD.log (append-only, timestamped).
#
# Usage: myigloo_nightly_chain.sh [--dry-run]
#   --dry-run: print what WOULD run, call no fetcher/promoter, write no night-log. Exits 0.

export PYTHONIOENCODING=utf-8   # piped python children default to cp1252 on Windows
APP=/d/verdmat-is/app
DATA=/d/verdmat-is/scraper_data
NIGHTLOGS=$DATA/night_logs
MODELOGS=$DATA/logs
BASELINE_MARKER=$DATA/myigloo_canon_rebaseline_done

DRY=0
[ "$1" = "--dry-run" ] && DRY=1

TS=$(date +%Y%m%d)
REPORT=$NIGHTLOGS/myigloo_night_${TS}.log

say() {                       # stdout always; night-log only on a real run (append-only)
  local line="$(date '+%Y-%m-%d %H:%M:%S') $*"
  echo "$line"
  [ $DRY -eq 0 ] && echo "$line" >> "$REPORT"
}

[ $DRY -eq 0 ] && mkdir -p "$NIGHTLOGS" "$MODELOGS"

say "=== myigloo nightly chain start (full-sweep, dry_run=$DRY) ==="

# ── pre-flight: refuse if another myigloo fetcher is already live (avoid double-sweep) ──
preflight() {
  local n
  n=$(powershell -NoProfile -Command \
      "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -match 'fetch_myigloo' }).Count" \
      2>/dev/null | tr -d '[:space:]')
  if [ -n "$n" ] && [ "$n" -gt 0 ] 2>/dev/null; then
    say "PRE-FLIGHT REFUSE: $n live fetch_myigloo process(es) already running"
    return 2
  fi
  say "pre-flight ok (no live fetch_myigloo)"
  return 0
}

if [ $DRY -eq 0 ]; then
  preflight || exit 2
else
  say "[dry-run] would run pre-flight (live-fetcher check)"
fi

# ── re-baseline banner (until night 1 marker is dropped) ──
if [ ! -f "$BASELINE_MARKER" ]; then
  say "RE-BASELINE: first nightly under new canon — expect changed=1 on ~ALL listings (old-canon stored hashes). ONE-TIME, NOT a content change. Stable from night 2. Do NOT alert on this spike."
fi

# ── one gated step; abort-not-retry ──
run_step() {                  # $1 label, $2.. command (run from $APP)
  local label=$1; shift
  if [ $DRY -eq 1 ]; then
    say "[dry-run] would run: $label  ::  $*"
    return 0
  fi
  local log=$MODELOGS/myigloo_${label}_${TS}.log
  ( cd "$APP" && "$@" ) > "$log" 2>&1
  local rc=$?
  say "$label: exit=$rc  (log: $log)"
  if [ $rc -ne 0 ]; then
    say "ABORT chain at $label (exit $rc) — NO RETRY (abort-not-retry)"
    say "  last 3 log lines:"; tail -3 "$log" | while IFS= read -r l; do say "    $l"; done
    return 1
  fi
  return 0
}

run_step fetch     python scripts/fetch_myigloo.py                               || exit 1
run_step parse     python scripts/parse_myigloo.py                               || exit 1
run_step canonical python -m scripts.promote_myigloo                             || exit 1
run_step lag1      python -m scripts.promote_myigloo_listings_append --confirm   || exit 1

# ── morning report: lift the key summary lines from the step logs ──
if [ $DRY -eq 0 ]; then
  FLOG=$MODELOGS/myigloo_fetch_${TS}.log
  LLOG=$MODELOGS/myigloo_lag1_${TS}.log
  say "--- summary ---"
  grep -E "changed=1 \(new/changed\)|changed=0 \(unchanged\)|details_fetched" "$FLOG" 2>/dev/null \
    | sed 's/^ *//' | while IFS= read -r l; do say "  fetch: $l"; done
  grep -E "active run:|ledger churn|records=" "$LLOG" 2>/dev/null \
    | sed 's/^ *//' | while IFS= read -r l; do say "  lag1: $l"; done
  # drop the night-1 marker so the re-baseline banner fires only once
  if [ ! -f "$BASELINE_MARKER" ]; then
    echo "first nightly under new canon ran $TS" > "$BASELINE_MARKER"
    say "  (re-baseline marker dropped — banner suppressed from next night)"
  fi
fi

say "=== CHAIN CLEAN (exit 0) ==="
exit 0
