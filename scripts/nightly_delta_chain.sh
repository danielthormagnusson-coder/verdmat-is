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
EXTRACT_FORWARD=200          # Haiku-hrinan: ný lysingar sem eru útdregnar í nótt
# cc113 — ÞAK Á VERÐMATS-HRINUNA (ekki Haiku-hrinuna; hún hefur EXTRACT_FORWARD +
# --max-n + $10/dag). Biðröðin er skilgreind sem „auglýsingar án verðmats FYRIR ÞETTA
# model_version", svo endurtengingin við iter4r (cc113, ed2d6d5) opnaði hana úr 3 í
# 21.354 í einu vetfangi. Það er skilgreiningin, ekki bilun — en fyrsta stóra hrinan á
# að vera VALIN, ekki afleiðing af fullri biðröð í ómannaðri nótt. Tengingin hafði þá
# keyrt 10 raðir í raun. Ekkert liggur á: enginn notendaflötur les töfluna (aðeins
# scraper.v_expected_vs_real + ferskleikalínan á /ops).
# Þakið stendur þar til biðröðin er tæmd; þá er það hlutlaust (biðröð < þak) og má
# hækka eða fjarlægja að athuguðu máli. Liður (ii) — endurreikningur 953 raðanna —
# er ÓSNERTUR af þessu: það mengi ber gamla stimpilinn og kemst aldrei í þessa biðröð.
#
# cc121 PÁSA — AFLÉTT 12.08 AF cc142. Kaflinn hér að neðan er SAGAN, ekki lifandi
# hegðun; hún byrjar aftur við „LIFANDI HEGÐUN" neðst.
#
# cc121 setti töluna í 0 (ákvörðun eiganda 08.08) og það var ALDREI BILUN.
# 0 = PÁSA (verðmats-þrepinu sleppt alveg); >0 = þak á fjölda raða per nótt.
# Biðröðin var 18.734 raðir við pásu (mælt 08.08, sama tala og cc119).
# Rökin: biðröðin er BAKFYLLING á eldri auglýsingum sem enginn notendaflötur les
# (aðeins scraper.v_expected_vs_real + ferskleikalínan á /ops), og hún á að klárast í
# EINNI mannaðri keyrslu — ellefu skammtar gefa ellefu ósambærilegar frávikadreifingar,
# ein keyrsla gefur EINA hreina á sama akkeri. Kostnaður er $0,00 hvort sem er
# (útdrættirnir eru til, engin Haiku-köll í verðmats-þrepinu).
# FORSENDA fyrir þeirri keyrslu: cc120/cc123/cc140 (miðsæknin — expected_base bar
# real_pred_median meðan /eign og /leit birtu real_pred_mean) varð að vera AFGREIDD
# FYRST, annars hefðum við fryst 18.734 raðir á skilgreiningu sem þyrfti að endurreikna.
# cc140 (12.08, b557245) lenti þeirri forsendu: allar nýjar raðir fæðast á
# `real_pred_mean`. (Sögunni lýkur hér.)
#
# ── LIFANDI HEGÐUN (cc142, 12.08) ────────────────────────────────────────────
# MANNAÐA KEYRSLAN ER GERÐ. `--value-seeded --confirm` (engin Haiku, day_total
# óhreyfður $3,9684) skrifaði 19.022 raðir í einni hrinu: rowcount 23.610 -> 42.632,
# nákvæmlega þurrkeyrslutalan, id-bilið 24568..43589 SAMFELLT. Biðröðin mæld gegnum
# `fetch_extracted_listings_to_value` EFTIR keyrslu = 0. Ein hrein frávikadreifing á
# einu akkeri liggur í D:\_audit\cc142_verdmats_bakfylling\.
#
# TALAN ER 2000, EKKI „ÓTAKMARKAД, OG ÞAÐ ER cc113-ÞAKIÐ SEM STENDUR EFTIR.
# Biðröðin vex ~300/nótt, svo 2000 er HLUTLAUST í venjulegri nótt (biðröð < þak) —
# keðjan tekur einfaldlega nóttina sína. Þakið ver EINA þekkta bilun: biðröðin er
# skilgreind sem „auglýsingar án verðmats FYRIR ÞETTA model_version", svo næsta
# LÍKANASKIPTI opnar allar 42.632 raðirnar í einu vetfangi (mælt í cc113: 3 -> 21.354).
# Sú hrina á að vera VALIN eins og þessi var, ekki afleiðing af ómannaðri nótt.
# Fjarlægðu því ekki þakið við það eitt að biðröðin sé tóm — það er einmitt ástandið
# sem þakið er hlutlaust í og gagnslaust að meta af.
# Útdrátturinn (EXTRACT_FORWARD, Haiku) er ÓSNERTUR — hann er ferskleiki, ekki bakfylling.
EXTRACT_VALUE_LIMIT=2000

DRY=0
[ "$1" = "--dry-run" ] && DRY=1

TS=$(date +%Y%m%d)
REPORT=$NIGHTLOGS/night_${TS}.log
CHAIN_START=$(python -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())")

# cc94/cc99 — stigsmunur á nóttinni. run_extraction skilar 0 þótt einstök köll
# falli (per-kall grip, viljandi: eitt fall má ekki fella 199 heppnuð). Fjöldi
# falla er því EINA merkið um skerta nótt og verður að komast í keðjulínuna.
EXTRACT_FAILED=0
EXTRACT_REJECTED=0

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
    say "[dry-run] would run: canary_spatial_ref_sys; parse_mbl --confirm; promote_mbl --slice priced --table {sale,rent}; promote_listings_append --confirm"
    return 0
  fi
  local plog=$MODELOGS/promote_${TS}.log
  ( cd "$APP" || exit 90
    # cc55 canary: refuse before any geog-computing write if the SRID registry deviates
    # (anon write grants on spatial_ref_sys still open — RLS_FIX_20260729T075021Z.md §3)
    echo "=== canary spatial_ref_sys ===";  python -m scripts.canary_spatial_ref_sys                            || exit 10
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
# hard cost cap (runaway guard if the content-addressed cache ever regresses).
# TVÖ AÐSKILIN ÞÖK, ekki eitt (cc113): EXTRACT_FORWARD þakar HAIKU-hrinuna (kostnað),
# EXTRACT_VALUE_LIMIT þakar VERÐMATS-hrinuna (skrif í listing_valuations). Þau eru ótengd —
# verðmats-biðröðin er allt safnið sem á ekki verðmat undir lifandi model_version, ekki bara
# það sem var útdregið í nótt, svo Haiku-þakið ver hana ekki. The Haiku key is read
# ONLY from D:\env.local inside the run_extraction process (dotenv_values) — never exported, so the
# chain/CC environment stays keyless and cannot self-bill.
run_extract() {
  # cc113: rökin eru byggð EINU SINNI og notuð af BÁÐUM greinum. Áður var þurrkeyrslu-
  # línan handskrifaður strengur við hliðina á raunkallinu — hún gat því sagt eitt meðan
  # nóttin gerði annað, og þurrkeyrsla sem sannar ekki raunkallið sannar ekki neitt.
  local xargs=(--forward "$EXTRACT_FORWARD" --confirm)
  # cc121 — PÁSAN ER ÞÝDD HÉR, EKKI SEND NIÐUR SEM 0. MÆLT 08.08: `--value-limit 0` er
  # ÓTAKMARKAÐ, ekki ekkert — fetch_extracted_listings_to_value sleppir LIMIT-liðnum á
  # falsy limit (`if limit`, extraction_engine.py:188), svo limit=0 skilaði sömu 18.734
  # röðum og limit=None. Að senda 0 niður hefði því skrifað ALLA biðröðina í nótt —
  # þveröfugt við pásuna. Skelin ber `-gt 0`, þar sem 0 er ótvírætt, og velur sér-rofann.
  if [ "$EXTRACT_VALUE_LIMIT" -gt 0 ]; then
    xargs+=(--value-limit "$EXTRACT_VALUE_LIMIT")
  else
    xargs+=(--skip-valuation)
  fi
  if [ $DRY -eq 1 ]; then
    say "[dry-run] would run: run_extraction ${xargs[*]} (max-n 500, daily-cap \$10)"
    return 0
  fi
  local xlog=$MODELOGS/extraction_${TS}.log
  ( cd "$APP" && python -u -m scripts.run_extraction "${xargs[@]}" ) > "$xlog" 2>&1
  local rc=$?
  local summary
  summary=$(grep -oE "(effective_n=[0-9]+|day_total=\\\$[0-9.]+|valued [0-9]+ listings)" "$xlog" | tr '\n' ' ')
  # cc94 — `failed`/`rejected` úr extract-samantektinni inn í keðjulínuna.
  # Vanti línan (t.d. ef Haiku-hlutinn var stöðvaður af kostnaðarþaki) haldast núllin.
  EXTRACT_FAILED=$(grep -oE "'failed': [0-9]+" "$xlog" | tail -1 | grep -oE "[0-9]+")
  EXTRACT_REJECTED=$(grep -oE "'rejected': [0-9]+" "$xlog" | tail -1 | grep -oE "[0-9]+")
  : "${EXTRACT_FAILED:=0}" "${EXTRACT_REJECTED:=0}"
  say "extraction: exit=$rc ${summary}failed=$EXTRACT_FAILED rejected=$EXTRACT_REJECTED -> $xlog"
  # cc156 — SÍA #1 (K2) FÆR SÍNA EIGIN LÍNU, ekki viðhengi við extraction-línuna.
  # Hún mælir annað: extraction-línan segir hvað var KEYPT, þessi segir hvað var
  # EKKI keypt af því textinn var þegar til á hreinsuðum lykli. VÆNTING ER ÓSETT —
  # fyrsta mæling setur viðmiðið (cc156 liður 2). Talan sem hún vaktar er hlutur
  # VELTUNNAR sem ber óbreytt innihald: cc156 liður 0 mældi ~100 nýja hasha á nóttu
  # af endurskrifuðum auglýsingum (ekki 15,5 af nýskráningu), og K2 er lykillinn
  # sem á að fanga þær. Falli talan í 0 margar nætur í röð er annaðhvort veltan
  # hætt eða sían hætt að bíta — hvort tveggja er frétt. Dómsdagur ~7 nætur.
  local k2line
  k2line=$(grep -oE "forward-k2: bidrod_fyrir=[0-9]+ k2_felld=[0-9]+ bidrod_eftir=[0-9]+ keyptir_lyklar=[0-9]+" "$xlog" | tail -1)
  say "sia1-k2: ${k2line:-<engin k2-lina i loggnum>}"
  if [ $rc -ne 0 ]; then
    say "ABORT extraction (exit $rc) — NO RETRY (abort-not-retry); promote/raw/layers untouched"
    return 1
  fi
  return 0
}

# cc94 — eitt útgönguorð fyrir öll fallandi útgöngin, svo CHAIN FAIL sé alltaf
# ritað í næturloggið (áður hættu þau þögult og vaktarprófið las það sem ABORT
# af FJARVERU CLEAN-línunnar — rétt niðurstaða, engin ástæða).
chain_fail() {
  say "=== CHAIN FAIL ($1, exit $2) ==="
  exit "$2"
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
    chain_fail "pre-flight" 2
  fi
fi

# §6-A.5 rule 1: delta always runs first / is the whole v1 night. Serial, gated.
run_mode delta-sale            delta_sale            last_br_dags_seen  || chain_fail "delta-sale" 1
run_mode delta-rent            delta_rent            last_updated_seen  || chain_fail "delta-rent" 1
run_mode delta-sale-negotiable delta_sale_negotiable last_br_dags_seen  || chain_fail "delta-sale-neg" 1
run_mode delta-rent-negotiable delta_rent_negotiable last_updated_seen  || chain_fail "delta-rent-neg" 1

# v2/v3: parse + promote BOTH layers (priced sale+rent; negotiable excluded). Gated on the
# four clean fetch modes above; abort-not-retry. Added BLOKK 6 (2026-06-27).
run_promote || chain_fail "promote" 1

# forward extraction + frozen valuation (mbl), after both layers are fresh. Added EXTRACTION ÞREP 5.
run_extract || chain_fail "extraction" 1

if [ $DRY -eq 1 ]; then
  say "[dry-run] would append night totals + CHAIN CLEAN to $REPORT"
  exit 0
fi

TOT=$(night_totals)
while IFS= read -r line; do say "  $line"; done <<< "$TOT"
# cc94 — ÞRJÚ STIG. Keðjan kláraði í báðum tilvikum hér (exit 0); munurinn er
# hvort eitthvað féll á leiðinni. DEGRADED er flagg, ekki bilun: gögnin sem
# tókust eru rétt, en nóttin er ekki heil og biðröðin ber afganginn áfram.
if [ "$EXTRACT_FAILED" -gt 0 ]; then
  say "=== CHAIN DEGRADED:$EXTRACT_FAILED (exit 0) ==="
else
  say "=== CHAIN CLEAN (exit 0) ==="
fi
exit 0
