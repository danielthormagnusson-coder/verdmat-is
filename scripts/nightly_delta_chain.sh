#!/bin/bash
# nightly_delta_chain.sh — §6-A.3 v1 (fetch-only) nightly mbl delta chain.
#
# Runs the FOUR delta modes serially (sale, rent, sale-negotiable, rent-negotiable),
# each gated on exit 0 + halt_reason null (resweep_runner gate pattern). ABORT-NOT-RETRY
# on any failure or kill-switch. The raw layer is append-only + content-hash idempotent,
# so the worst unattended failure is wasted requests.
#
# v2/v3 ACTIVE (BLOKK 6, 2026-06-27): after the four fetch modes complete cleanly, run_promote
# parses pending raw and promotes priced sale+rent into BOTH layers — old fold path
# (promote_mbl -> listings_canonical) AND new append layer (promote_listings_append ->
# scraper.listings + listing_price_history). NEGOTIABLE is NOT promoted (lease_term pending).
# No API key is ever read (no Haiku in this chain). promote is gated on a clean fetch and is
# abort-not-retry; a promote failure leaves raw/fetch untouched. Freezing the old fold write
# is a deliberate LATER step at consumer migration — both layers stay fresh until then.
#
# PRE-FLIGHT GATES (all must pass before ANY fetcher call; exit 2 on refusal):
#   (a) no live fetch_mbl process (reuses prime_delta_since detection; state-recency
#       heuristic as fallback when the process scan is unavailable)
#   (b) ALL FOUR delta since_keys primed — §6-A.1 LOCKED RULE: the chain must never
#       launch a 1970-epoch sweep (run prime_delta_since.py --confirm first)
#   (c) §6-A.5 budget: pages fetched in the trailing 24h (raw_mbl.db mode=ro) + the
#       night's worst case (4 x DELTA_MAX_PAGES) must stay under NIGHT_BUDGET (~900,
#       margin below the §0.5 <1000/24h cap)
#
# Morning report: scraper_data/night_logs/night_YYYYMMDD.log (timestamped, append-only):
# per mode pages/listings/new high-water/halt_reason + totals. A mode that hits
# DELTA_MAX_PAGES gets a WARNING line — _delta advances the high-water past unswept
# pages when capped (pk-desc ordering), so a cap-hit means possible skipped changes
# that need a manual follow-up run.
#
# Exit codes: 0 clean, 1 chain abort (mode failure/halt), 2 pre-flight refusal —
# readable as Task Scheduler last-result.
#
# Usage: nightly_delta_chain.sh [--dry-run]
#   --dry-run: run the pre-flight gates read-only, print what WOULD run, call no
#              fetcher, write no night-log. Always exits 0.

export PYTHONIOENCODING=utf-8   # piped python children default to cp1252 on Windows
                                # (run_monthly latent-bug #5 lesson, DECISIONS 2026-05-28)
APP=/d/verdmat-is/app
DATA=/d/verdmat-is/scraper_data
STATE=$DATA/mbl_fetch_state.json
RAWDB=$DATA/raw_mbl.db
NIGHTLOGS=$DATA/night_logs
MODELOGS=$DATA/logs
DELTA_MAX_PAGES=100          # per-mode cap; bounds the night at 4x100 pages worst case
NIGHT_BUDGET=900             # §6-A.5 margin under the §0.5 <1000 pages/24h cap

DRY=0
[ "$1" = "--dry-run" ] && DRY=1

TS=$(date +%Y%m%d)
REPORT=$NIGHTLOGS/night_${TS}.log
CHAIN_START=$(python -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())")

say() {                       # stdout always; night-log only on a real run (append-only)
  local line="$(date '+%Y-%m-%d %H:%M:%S') $*"
  echo "$line"
  [ $DRY -eq 0 ] && echo "$line" >> "$REPORT"
}

[ $DRY -eq 0 ] && mkdir -p "$NIGHTLOGS" "$MODELOGS"

# ── pre-flight (read-only: process scan + state read + ro db count) ──────────
preflight() {
  python - "$STATE" "$RAWDB" "$NIGHT_BUDGET" "$((4 * DELTA_MAX_PAGES))" <<'PY'
import json, sqlite3, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, r"D:\verdmat-is\app\scripts")
import prime_delta_since as pds   # reuse the tested detection (gate a)

state_path, rawdb, budget, planned = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
problems = []

state = json.load(open(state_path, encoding="utf-8")) if Path(state_path).is_file() else {}

# (a) no live fetcher
procs = pds._live_fetcher_processes()
if procs:
    problems.append("live fetch_mbl process: " + "; ".join(procs)[:200])
elif procs is None:               # scan unavailable -> recency heuristic fallback
    recent = pds._recent_activity(state)
    if recent:
        problems.append("process scan unavailable + recent state activity: "
                        + "; ".join(recent)[:200])

# (b) all four since_keys primed (1970-sweep guard, hard)
for key, sk in (("delta_sale", "last_br_dags_seen"),
                ("delta_sale_negotiable", "last_br_dags_seen"),
                ("delta_rent", "last_updated_seen"),
                ("delta_rent_negotiable", "last_updated_seen")):
    if not state.get(key, {}).get(sk):
        problems.append("since_key UNSET: %s.%s — run prime_delta_since.py --confirm first"
                        % (key, sk))

# (c) trailing-24h page budget
pages24 = None
try:
    c = sqlite3.connect("file:%s?mode=ro" % rawdb.replace("\\", "/"), uri=True)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    pages24 = c.execute("SELECT COUNT(*) FROM raw_fetches WHERE fetched_at >= ?",
                        (cutoff,)).fetchone()[0]
    c.close()
except Exception as e:
    problems.append("budget check failed (raw db unreadable): %s" % e)
if pages24 is not None:
    print("PAGES_24H=%d planned=+%d budget=%d" % (pages24, planned, budget))
    if pages24 + planned > budget:
        problems.append("BUDGET: %d last-24h + %d planned > %d" % (pages24, planned, budget))

if problems:
    for p in problems:
        print("REFUSE: " + p)
    sys.exit(2)
print("PREFLIGHT OK")
PY
}

# ── per-mode state readout (high-water + halt_reason) ────────────────────────
state_line() {                # $1 = state key, $2 = since key
  python - "$STATE" "$1" "$2" <<'PY'
import json, sys
st = json.load(open(sys.argv[1], encoding="utf-8")).get(sys.argv[2], {})
print("high_water=%s halt_reason=%s" % (st.get(sys.argv[3]), st.get("halt_reason")))
PY
}

# ── run one mode, gated ──────────────────────────────────────────────────────
run_mode() {                  # $1 mode, $2 state key, $3 since key
  local mode=$1 key=$2 sk=$3
  if [ $DRY -eq 1 ]; then
    echo "[dry-run] would run: python $APP/scripts/fetch_mbl.py --mode $mode --max-pages $DELTA_MAX_PAGES"
    return 0
  fi
  local mlog=$MODELOGS/delta_${mode}_${TS}.log
  python $APP/scripts/fetch_mbl.py --mode "$mode" --max-pages $DELTA_MAX_PAGES \
    > "$mlog" 2>&1
  local rc=$?
  local summary
  summary=$(grep -E "delta done" "$mlog" | tail -1 | sed 's/^ *//')
  local st
  st=$(state_line "$key" "$sk")
  say "$mode: exit=$rc ${summary:-<no delta-done line>} $st"
  if [ $rc -ne 0 ]; then
    say "ABORT chain at $mode (exit $rc) — NO RETRY (abort-not-retry)"
    return 1
  fi
  echo "$st" | grep -q "halt_reason=None" || {
    say "ABORT chain at $mode (halt_reason set) — NO RETRY"
    return 1
  }
  # cap-hit warning: _delta advances high-water past unswept pages when capped
  local pages
  pages=$(echo "$summary" | grep -oE "[0-9]+ pages" | grep -oE "[0-9]+")
  if [ -n "$pages" ] && [ "$pages" -ge $DELTA_MAX_PAGES ]; then
    say "WARNING: $mode hit the $DELTA_MAX_PAGES-page cap — possible skipped changes past the cap; run the mode again manually and investigate"
  fi
  return 0
}

# ── night totals (pages + listings fetched since chain start, per kind) ──────
night_totals() {
  python - "$RAWDB" "$CHAIN_START" <<'PY'
import gzip, json, sqlite3, sys
rawdb, since = sys.argv[1], sys.argv[2]
kinds = {"list_page_sale": "delta-sale", "list_page_rent": "delta-rent",
         "list_page_sale_negotiable_delta": "delta-sale-negotiable",
         "list_page_rent_negotiable_delta": "delta-rent-negotiable"}
c = sqlite3.connect("file:%s?mode=ro" % rawdb.replace("\\", "/"), uri=True)
tot_p = tot_l = 0
for kind, mode in kinds.items():
    rows = c.execute("SELECT b.blob_gz FROM raw_fetches f JOIN raw_blobs b "
                     "ON b.content_hash=f.content_hash WHERE f.fetch_kind=? "
                     "AND f.fetched_at >= ?", (kind, since)).fetchall()
    n_l = 0
    for (gz,) in rows:                       # delta nights are small (1-30 pages)
        d = json.loads(gzip.decompress(gz))["data"]
        n_l += len(next(iter(d.values())))
    print("TOTAL %s: pages=%d listings=%d" % (mode, len(rows), n_l))
    tot_p += len(rows); tot_l += n_l
c.close()
print("TOTAL night: pages=%d listings=%d" % (tot_p, tot_l))
PY
}

# ── v2/v3: parse + promote BOTH layers (BLOKK 6); only after four clean fetch modes ──
run_promote() {
  if [ $DRY -eq 1 ]; then
    say "[dry-run] would run: parse_mbl --confirm; promote_mbl --slice priced --table {sale,rent}; promote_listings_append --confirm"
    return 0
  fi
  local plog=$MODELOGS/promote_${TS}.log
  ( cd "$APP" || exit 90
    echo "=== parse ===";                  python -m scripts.parse_mbl --confirm                                || exit 11
    echo "=== promote canonical sale ===";  python -m scripts.promote_mbl --confirm --slice priced --table sale  || exit 12
    echo "=== promote canonical rent ===";  python -m scripts.promote_mbl --confirm --slice priced --table rent  || exit 13
    echo "=== append Lag 1 ===";            python -m scripts.promote_listings_append --confirm                  || exit 14
  ) > "$plog" 2>&1
  local rc=$?
  local nact
  nact=$(grep -cE "wrote listings|promoted|inserted=" "$plog")
  say "promote: exit=$rc (${nact} action lines) -> $plog"
  if [ $rc -ne 0 ]; then
    say "ABORT promote (exit $rc) — NO RETRY (abort-not-retry); raw/fetch untouched, both layers stay at last-clean"
    return 1
  fi
  return 0
}

# ── extraction: forward 108-field condition extract + frozen valuation (EXTRACTION ÞREP 5) ──
# Runs after promote (both layers fresh). mbl only — valuation needs a fastnum, which only mbl
# resolves; myigloo (rent, no fastnum) has no valuation path, so it is intentionally not extracted
# here. Fresh-first ordering + N=200 cap (~57 min, finishes ~02:10, clean before 02:30) + a $10/day
# hard cost cap (runaway guard if the content-addressed cache ever regresses). The Haiku key is read
# ONLY from D:\env.local inside the run_extraction process (dotenv_values) — never exported, so the
# chain/CC environment stays keyless and cannot self-bill.
run_extract() {
  if [ $DRY -eq 1 ]; then
    say "[dry-run] would run: run_extraction --forward 200 --confirm (max-n 500, daily-cap \$10)"
    return 0
  fi
  local xlog=$MODELOGS/extraction_${TS}.log
  ( cd "$APP" && python -u -m scripts.run_extraction --forward 200 --confirm ) > "$xlog" 2>&1
  local rc=$?
  local summary
  summary=$(grep -oE "(effective_n=[0-9]+|day_total=\\\$[0-9.]+|valued [0-9]+ listings)" "$xlog" | tr '\n' ' ')
  say "extraction: exit=$rc ${summary}-> $xlog"
  if [ $rc -ne 0 ]; then
    say "ABORT extraction (exit $rc) — NO RETRY (abort-not-retry); promote/raw/layers untouched"
    return 1
  fi
  return 0
}

# ════════════════════════════════ main ═══════════════════════════════════════
say "=== nightly delta chain start (fetch+parse+promote+extraction, dry_run=$DRY) ==="

PRE=$(preflight)
PRERC=$?
while IFS= read -r line; do say "  $line"; done <<< "$PRE"
if [ $PRERC -ne 0 ]; then
  if [ $DRY -eq 1 ]; then
    say "[dry-run] pre-flight WOULD REFUSE (exit 2 on a real run)"
  else
    say "PRE-FLIGHT REFUSED — nothing launched"
    exit 2
  fi
fi

# §6-A.5 rule 1: delta always runs first / is the whole v1 night. Serial, gated.
run_mode delta-sale            delta_sale            last_br_dags_seen  || exit 1
run_mode delta-rent            delta_rent            last_updated_seen  || exit 1
run_mode delta-sale-negotiable delta_sale_negotiable last_br_dags_seen  || exit 1
run_mode delta-rent-negotiable delta_rent_negotiable last_updated_seen  || exit 1

# v2/v3: parse + promote BOTH layers (priced sale+rent; negotiable excluded). Gated on the
# four clean fetch modes above; abort-not-retry. Added BLOKK 6 (2026-06-27).
run_promote || exit 1

# forward extraction + frozen valuation (mbl), after both layers are fresh. Added EXTRACTION ÞREP 5.
run_extract || exit 1

if [ $DRY -eq 1 ]; then
  say "[dry-run] would append night totals + CHAIN CLEAN to $REPORT"
  exit 0
fi

TOT=$(night_totals)
while IFS= read -r line; do say "  $line"; done <<< "$TOT"
say "=== CHAIN CLEAN (exit 0) ==="
exit 0
