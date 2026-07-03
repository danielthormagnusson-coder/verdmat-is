"""lifecycle_sweep_mbl.py — Phase A weekly lifecycle sweep for mbl listings.

Deterministic weekly re-fetch of ALL known-active mbl listing ids (from the DB,
NOT a rotation) to detect withdrawals and price changes, writing lifecycle events
into scraper.listing_lifecycle_events.

WHY a by-id sweep: mbl has NO detail endpoint (fetch_mbl §: "NO detail endpoint").
Data is Hasura GraphQL at g.mbl.is/v1/graphql; the anonymous role hard-caps 16 rows
per query. So per-id presence is checked with a `where:{<pk>:{_in:[...<=16...]}}`
filter, minimal selection (pk + price + syna). Batch size = PAGE = 16.

Known-active id set (the denominator) =
    scraper.listings WHERE source='mbl' AND tenure=? AND status='active'
    AND NOT EXISTS a terminal 'withdrawn_confirmed' event for that listing.
The withdrawn exclusion keeps the sweep from re-hitting listings already confirmed
gone (so the denominator shrinks honestly instead of growing forever). No write to
scraper.listings.status is made here — the event log is the lifecycle source of truth
(status-sync is a deliberate later step, out of Phase A scope).

Per id, per sweep:
  * found (returned AND, for sale, syna=true):
      - live price == db price   -> NOTHING written (found => no event, per spec)
      - live price != db price    -> price_changed  (evidence: old + new)
  * absent (not returned, or sale syna=false):
      - no prior confirmed_absent_1  -> confirmed_absent_1
      - has prior confirmed_absent_1 -> withdrawn_confirmed (evidence.withdrawn_at = now)

Two-strike withdrawal note: "found => nothing" means we do NOT record presence, so a
listing that went absent, reappeared, then went absent again cannot be distinguished
from two consecutive absences without a presence event. For Phase A this matches the
spec ("fjarvera + fyrri absent frá fyrri viku -> withdrawn_confirmed"); reappearance is
rare and the mis-timing is at most one sweep. A future 'confirmed_present'/streak-reset
is the refinement if it ever matters.

Polite crawl: same discipline as the delta chain — default 120s spacing, fetch_mbl's
kill-switch (3x HTTP 400 / 403 / 429 / CAPTCHA / GraphQL errors / 3x timeout).

WRITE SAFETY: events are written via psycopg2 on the 6543 transaction pooler, which
defaults READ ONLY; every write transaction issues `SET TRANSACTION READ WRITE` as its
FIRST statement (locked pooler rule). --dry-run writes NOTHING to the DB (CSV only).

CLI:
  python -m scripts.lifecycle_sweep_mbl                                  # docstring + exit 0
  python -m scripts.lifecycle_sweep_mbl --dry-run --tenure both --limit 200 [--spacing 15]
                                                        # CSV probe, no DB writes
  python -m scripts.lifecycle_sweep_mbl --confirm --tenure both          # FULL run, writes events
  python -m scripts.lifecycle_sweep_mbl --confirm --tenure rent          # rent-only (cheap) slice

deps: stdlib + requests + psycopg2 + fetch_mbl (transport constants) + scraper_paths.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import psycopg2
from psycopg2.extras import execute_values, Json

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_mbl import (  # noqa: E402  reuse the exact transport + kill-switch discipline
    ENDPOINT, UA, TIMEOUT_S, MAX_CONSEC_400, MAX_CONSEC_TIMEOUT,
    MIN_SPACING_FLOOR, KillSwitch, _is_captcha,
)
from scraper_paths import get_scraper_data_dir, get_raw_db_path  # noqa: E402

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
SWEEP_VERSION = "lifecycle_sweep_mbl_v1"
PAGE = 16                    # Hasura anonymous-role hard cap = batch size
DEFAULT_SPACING = 120.0      # seconds between queries (delta-chain politeness)

# --- A1 scheduled-mode (resume-safe multi-session) config ---
STATE_PATH = get_scraper_data_dir() / "lifecycle_sweep_state.json"
SWEEP_DAILY_BUDGET = 700     # sweep's own trailing-24h request cap (leaves ~300 for delta under §0.5)
COMBINED_CAP = 950           # sweep + delta trailing-24h hard margin under the §0.5 <1000/24h rule
RENT_CADENCE_DAYS = 7        # rent = one full lota per week
SALE_CADENCE_DAYS = 7        # sale = one full round per week, resumed nightly over ~2 days

# slice config mirrors fetch_mbl.MODECFG (roots/pks/price fields), minimal selection.
SLICES = {
    "sale": {"root": "fs_fasteign",      "pk": "eign_id", "price": "verd",
             "sel": "eign_id verd syna", "has_syna": True},
    "rent": {"root": "rentals_property", "pk": "id",      "price": "price",
             "sel": "id price",          "has_syna": False},
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def read_db_url() -> str:
    # .dbconfig is UTF-8 with BOM (CLAUDE.md); utf-8-sig strips it. Pooler URI, port 6543.
    return DBCONFIG.read_text(encoding="utf-8-sig").strip()


# ── DB reads (denominator + prior-absent set) ────────────────────────────────
def load_active_ids(conn, tenure):
    """Known-active id list for a slice: status='active' minus terminal withdrawals.

    Ordered by listing_id (stable insertion order) so a strided dry-run sample is
    deterministic and spans old..new rather than clustering on newest ids.
    Returns list of (source_listing_id:str, price_amount:int|None, fastnum:int|None).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT l.source_listing_id, l.price_amount, l.fastnum
            FROM scraper.listings l
            WHERE l.source='mbl' AND l.tenure=%s AND l.status='active'
              AND NOT EXISTS (
                SELECT 1 FROM scraper.listing_lifecycle_events e
                WHERE e.source='mbl'
                  AND e.source_listing_id = l.source_listing_id
                  AND e.event_type = 'withdrawn_confirmed')
            ORDER BY l.listing_id
            """,
            (tenure,),
        )
        return [(str(r[0]), r[1], r[2]) for r in cur.fetchall()]


def load_prior_absent_set(conn, tenure, before=None):
    """source_listing_ids that already carry a confirmed_absent_1 event (non-terminal,
    since withdrawn ids are excluded from the active set upstream). A second absence
    for one of these escalates to withdrawn_confirmed.

    `before` (timestamptz): count only events strictly earlier — so a multi-day round's
    own confirmed_absent_1 writes are NOT mistaken for "a prior week's" absence."""
    q = """
        SELECT DISTINCT e.source_listing_id
        FROM scraper.listing_lifecycle_events e
        JOIN scraper.listings l
          ON l.source='mbl' AND l.source_listing_id = e.source_listing_id
             AND l.tenure=%s
        WHERE e.source='mbl' AND e.event_type='confirmed_absent_1'
        """
    params = [tenure]
    if before is not None:
        q += " AND e.event_at < %s"
        params.append(before)
    with conn.cursor() as cur:
        cur.execute(q, params)
        return {str(r[0]) for r in cur.fetchall()}


# ── transport (standalone, fetch_mbl kill-switch discipline) ─────────────────
class Transport:
    def __init__(self, spacing, log=print):
        self.s = requests.Session()
        self.spacing = max(MIN_SPACING_FLOOR, float(spacing))
        self.log = log
        self._consec_400 = 0
        self._consec_timeout = 0
        self._last_at = 0.0
        self.request_count = 0

    def _pace(self):
        dt = time.monotonic() - self._last_at
        if self._last_at and dt < self.spacing:
            time.sleep(self.spacing - dt)
        self._last_at = time.monotonic()

    def gql(self, query):
        for _ in range(3):
            self._pace()
            try:
                r = self.s.post(ENDPOINT, json={"query": query},
                                headers={"User-Agent": UA, "Accept": "application/json",
                                         "Content-Type": "application/json"}, timeout=TIMEOUT_S)
            except requests.RequestException:
                self._consec_timeout += 1
                if self._consec_timeout >= MAX_CONSEC_TIMEOUT:
                    raise KillSwitch("%d consecutive timeouts" % self._consec_timeout)
                time.sleep(2)
                continue
            self._consec_timeout = 0
            status = r.status_code
            if status == 400:
                self._consec_400 += 1
                if self._consec_400 >= MAX_CONSEC_400:
                    raise KillSwitch("%d consecutive HTTP 400 — likely throttle" % self._consec_400)
                time.sleep(2)
                continue
            self._consec_400 = 0
            if status in (403, 429):
                raise KillSwitch("HTTP %s" % status)
            if status != 200:
                raise KillSwitch("unexpected HTTP %s" % status)
            body = r.content or b""
            if _is_captcha(body):
                raise KillSwitch("CAPTCHA/challenge body")
            try:
                data = json.loads(body)
            except Exception:
                raise KillSwitch("non-JSON 200 body")
            if isinstance(data, dict) and data.get("errors"):
                raise KillSwitch("GraphQL errors: %s" % json.dumps(data["errors"])[:200])
            self.request_count += 1
            return data
        raise KillSwitch("retries exhausted")


def in_query(cfg, ids):
    # ids are numeric strings; Hasura int pk accepts a bare-int _in list.
    id_list = ",".join(str(int(i)) for i in ids)
    return "query { %s(where:{%s:{_in:[%s]}}) { %s } }" % (
        cfg["root"], cfg["pk"], id_list, cfg["sel"])


# ── classification ───────────────────────────────────────────────────────────
def classify_batch(cfg, batch, returned, prior_absent, sweep_id, tenure, event_at):
    """batch: list of (id, db_price, fastnum). returned: {pk_str: row}. Yields dicts:
       {id, fastnum, status: found|price_changed|absent, event_type|None, evidence, note}."""
    pkf, pricef, has_syna = cfg["pk"], cfg["price"], cfg["has_syna"]
    out = []
    for sid, db_price, fastnum in batch:
        row = returned.get(sid)
        absent = False
        note = ""
        if row is None:
            absent, note = True, "not_in_response"
        elif has_syna and row.get("syna") is False:
            absent, note = True, "syna_false"

        if absent:
            if sid in prior_absent:
                etype = "withdrawn_confirmed"
                evidence = {"sweep_id": sweep_id, "slice": tenure, "reason": note,
                            "withdrawn_at": event_at.isoformat(), "prior": "confirmed_absent_1"}
            else:
                etype = "confirmed_absent_1"
                evidence = {"sweep_id": sweep_id, "slice": tenure, "reason": note}
            out.append({"id": sid, "fastnum": fastnum, "status": "absent",
                        "event_type": etype, "evidence": evidence,
                        "db_price": db_price, "live_price": None, "note": note})
            continue

        live_price = row.get(pricef)
        lp = int(live_price) if live_price is not None else None
        dp = int(db_price) if db_price is not None else None
        if lp != dp:
            evidence = {"sweep_id": sweep_id, "slice": tenure, "old": dp, "new": lp}
            if lp == 0:  # verd/price -> 0 = converted to "tilboð"/negotiable; flag for
                evidence["to_negotiable"] = True  # price-history analysis without a new enum value
            out.append({"id": sid, "fastnum": fastnum, "status": "price_changed",
                        "event_type": "price_changed", "evidence": evidence,
                        "db_price": dp, "live_price": lp, "note": "price_delta"})
        else:
            out.append({"id": sid, "fastnum": fastnum, "status": "found",
                        "event_type": None, "evidence": None,
                        "db_price": dp, "live_price": lp, "note": ""})
    return out


def sweep_slice(conn, transport, tenure, sweep_id, event_at, ids, prior_absent, log):
    """Run the by-id sweep over `ids` (list of (id, db_price, fastnum)); return event dicts."""
    cfg = SLICES[tenure]
    results = []
    n_batches = (len(ids) + PAGE - 1) // PAGE
    for b in range(n_batches):
        batch = ids[b * PAGE:(b + 1) * PAGE]
        data = transport.gql(in_query(cfg, [x[0] for x in batch]))
        rows = data["data"][cfg["root"]]
        returned = {str(r[cfg["pk"]]): r for r in rows}
        res = classify_batch(cfg, batch, returned, prior_absent, sweep_id, tenure, event_at)
        results.extend(res)
        got = sum(1 for r in res if r["status"] != "absent")
        log("  [%s] batch %d/%d: %d ids -> %d present, %d absent"
            % (tenure, b + 1, n_batches, len(batch), got, len(batch) - got))
    return results


# ── event write (real run only) ──────────────────────────────────────────────
def write_events(conn, events, log=print):
    """INSERT lifecycle events. First statement SET TRANSACTION READ WRITE (pooler rule)."""
    rows = [(e["source"], e["id"], e["fastnum"], e["event_type"],
             e["event_at"], Json(e["evidence"])) for e in events]
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ WRITE")
        execute_values(cur,
            "INSERT INTO scraper.listing_lifecycle_events "
            "(source, source_listing_id, fastnum, event_type, event_at, evidence) VALUES %s",
            rows, page_size=1000)
    conn.commit()
    log("wrote %d events" % len(rows))


# ── dry-run CSV ──────────────────────────────────────────────────────────────
def write_csv(path, all_results):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tenure", "source_listing_id", "fastnum", "status",
                    "would_event_type", "db_price", "live_price", "note", "evidence"])
        for tenure, res in all_results:
            for r in res:
                w.writerow([tenure, r["id"], r["fastnum"], r["status"],
                            r["event_type"] or "", r["db_price"], r["live_price"],
                            r["note"], json.dumps(r["evidence"], ensure_ascii=False) if r["evidence"] else ""])


def strided_sample(seq, k):
    """Deterministic ~k-element sample spanning the whole list (old..new)."""
    n = len(seq)
    if k is None or k >= n:
        return seq
    step = n / float(k)
    return [seq[int(i * step)] for i in range(k)]


# ── summary ──────────────────────────────────────────────────────────────────
def summarize(tenure, ids_total, results):
    found = sum(1 for r in results if r["status"] == "found")
    pc = sum(1 for r in results if r["status"] == "price_changed")
    absent = sum(1 for r in results if r["status"] == "absent")
    ca1 = sum(1 for r in results if r["event_type"] == "confirmed_absent_1")
    wd = sum(1 for r in results if r["event_type"] == "withdrawn_confirmed")
    return {"tenure": tenure, "swept": len(results), "active_total": ids_total,
            "found": found, "price_changed": pc, "absent": absent,
            "confirmed_absent_1": ca1, "withdrawn_confirmed": wd}


# ── A1 scheduled mode: resume-safe per-slice state + budget-gate + multi-session sale ──
def _iso(dt):
    return dt.isoformat()


def _parse(s):
    return datetime.fromisoformat(s) if s else None


def _default_state():
    return {
        "rent": {"epoch": None, "last_completed_at": None},
        "sale": {"epoch": None, "enabled": False, "round_file": None,
                 "round_started_at": None, "cursor": 0, "round_total": 0,
                 "last_completed_at": None},
        "request_log": [],
    }


def load_sweep_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return _default_state()


def save_sweep_state(state):
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE_PATH)   # atomic


def prune_request_log(state, now):
    cutoff = now - timedelta(hours=24)
    kept = [t for t in state.get("request_log", []) if _parse(t) and _parse(t) > cutoff]
    state["request_log"] = kept
    return len(kept)


def delta_requests_24h(now):
    """Trailing-24h mbl page-loads by the delta chain (raw_mbl.db raw_fetches). Best-effort; 0
    on failure. The sweep does NOT log to raw_fetches, so this is the ONLY cross-term needed to
    keep sweep + delta under the §0.5 <1000/24h combined politeness rule."""
    try:
        raw = str(get_raw_db_path("mbl")).replace("\\", "/")
        c = sqlite3.connect("file:%s?mode=ro" % raw, uri=True)
        cutoff = (now - timedelta(days=1)).isoformat()
        n = c.execute("SELECT COUNT(*) FROM raw_fetches WHERE fetched_at >= ?", (cutoff,)).fetchone()[0]
        c.close()
        return int(n)
    except Exception:
        return 0


def budget_now(state, now):
    """Returns (allowed_requests, sweep_used_24h, delta_24h). Enforces both the sweep's own
    daily cap and the combined <1000/24h §0.5 rule."""
    used = prune_request_log(state, now)
    delta = delta_requests_24h(now)
    allowed = max(0, min(SWEEP_DAILY_BUDGET - used, COMBINED_CAP - delta - used))
    return allowed, used, delta


def results_to_events(results, event_at):
    return [{"source": "mbl", "id": r["id"], "fastnum": r["fastnum"], "event_type": r["event_type"],
             "event_at": event_at, "evidence": r["evidence"]} for r in results if r["event_type"]]


def _due(last_iso, now, days):
    return last_iso is None or (now - _parse(last_iso)) >= timedelta(days=days)


def run_scheduled(conn, dry_run, log=print):
    """Task-Scheduler entry point. State-gated per-slice cadence: rent = one full lota/week;
    sale = one full round/week, snapshotted then resumed nightly over ~2 days under budget.
    --dry-run reports decisions and makes ZERO requests and ZERO DB writes."""
    now = now_utc()
    state = load_sweep_state()
    budget, used, delta = budget_now(state, now)
    log("=== scheduled run @ %s | dry_run=%s ===" % (_iso(now), dry_run))
    log("budget=%d requests (sweep_used_24h=%d, delta_24h=%d; caps sweep=%d combined=%d)"
        % (budget, used, delta, SWEEP_DAILY_BUDGET, COMBINED_CAP))
    transport = Transport(spacing=DEFAULT_SPACING)   # clamps up to the 60s floor

    def record():
        state["request_log"].append(_iso(now_utc()))

    # ---- RENT: atomic full lota, weekly ----
    rent = state["rent"]
    if not _due(rent.get("last_completed_at"), now, RENT_CADENCE_DAYS):
        nxt = RENT_CADENCE_DAYS - (now - _parse(rent["last_completed_at"])).total_seconds() / 86400.0
        log("[rent] not due (last=%s, next in %.1fd)" % (rent.get("last_completed_at"), nxt))
    else:
        active = load_active_ids(conn, "rent")
        need = -(-len(active) // PAGE)
        if dry_run:
            log("[rent] DUE — would sweep %d ids (%d requests); budget=%d" % (len(active), need, budget))
        elif budget < need:
            log("[rent] due but budget %d < need %d — deferring to next run" % (budget, need))
        else:
            rent_ts = now_utc()
            prior = load_prior_absent_set(conn, "rent", rent_ts)
            sid = "%s_rent_%s" % (SWEEP_VERSION, rent_ts.strftime("%Y%m%dT%H%M%SZ"))
            results = []
            for b in range(need):
                batch = active[b * PAGE:(b + 1) * PAGE]
                data = transport.gql(in_query(SLICES["rent"], [x[0] for x in batch])); record()
                returned = {str(r[SLICES["rent"]["pk"]]): r for r in data["data"][SLICES["rent"]["root"]]}
                results.extend(classify_batch(SLICES["rent"], batch, returned, prior, sid, "rent", rent_ts))
            events = results_to_events(results, rent_ts)
            if events:
                write_events(conn, events, log)
            rent["last_completed_at"] = _iso(rent_ts)
            if not rent.get("epoch"):
                rent["epoch"] = _iso(rent_ts)
            save_sweep_state(state)
            budget -= need
            log("[rent] done: %d ids, %d events, epoch=%s" % (len(active), len(events), rent["epoch"]))

    # ---- SALE: weekly round, resumed nightly over ~2 days ----
    sale = state["sale"]
    if not sale.get("enabled"):
        log("[sale] disabled — awaiting deliberate first-round kickoff (--enable-sale after WU-pause)")
    elif budget <= 0:
        log("[sale] no budget remaining this run (used=%d, delta=%d)" % (used, delta))
    else:
        in_flight = bool(sale.get("round_file")) and sale.get("cursor", 0) < sale.get("round_total", 0)
        if in_flight:
            if dry_run:
                log("[sale] round IN FLIGHT — would resume cursor %d/%d, budget=%d"
                    % (sale["cursor"], sale["round_total"], budget))
            else:
                log("[sale] resuming round: cursor %d/%d" % (sale["cursor"], sale["round_total"]))
                _process_sale_chunk(conn, transport, state, budget, record, log)
        elif _due(sale.get("last_completed_at"), now, SALE_CADENCE_DAYS):
            active = load_active_ids(conn, "sale")
            need = -(-len(active) // PAGE)
            if dry_run:
                log("[sale] round DUE — would freeze %d ids (%d requests, ~%.1f days at %d/day)"
                    % (len(active), need, need / float(SWEEP_DAILY_BUDGET), SWEEP_DAILY_BUDGET))
            else:
                rf = get_scraper_data_dir() / ("lifecycle_sale_round_%s.json" % now.strftime("%Y%m%dT%H%M%SZ"))
                rf.write_text(json.dumps(active), encoding="utf-8")
                sale.update({"round_file": str(rf), "round_started_at": _iso(now),
                             "cursor": 0, "round_total": len(active)})
                save_sweep_state(state)
                log("[sale] new round: %d ids frozen -> %s" % (len(active), rf.name))
                _process_sale_chunk(conn, transport, state, budget, record, log)
        else:
            log("[sale] round not due (last=%s)" % sale.get("last_completed_at"))

    if not dry_run:
        save_sweep_state(state)
    log("requests_this_run=%d" % transport.request_count)
    return 0


def _process_sale_chunk(conn, transport, state, budget, record, log):
    """Process sale batches from the frozen round file, from cursor, within `budget` requests.
    Writes events + advances cursor + saves state PER BATCH: a WU-kill resumes next run losing
    at most the in-flight batch. A rare re-processed batch yields benign duplicate events, which
    the append-only design tolerates (analysis keys on distinct listing / (old,new) price)."""
    sale = state["sale"]
    round_ids = json.loads(Path(sale["round_file"]).read_text(encoding="utf-8"))
    round_start = _parse(sale["round_started_at"])
    prior = load_prior_absent_set(conn, "sale", round_start)   # events strictly before this round
    sid = "%s_saleround_%s" % (SWEEP_VERSION, round_start.strftime("%Y%m%dT%H%M%SZ"))
    done = 0
    while sale["cursor"] < sale["round_total"] and done < budget:
        i = sale["cursor"]
        batch = [tuple(x) for x in round_ids[i:i + PAGE]]
        obs = now_utc()
        data = transport.gql(in_query(SLICES["sale"], [x[0] for x in batch])); record()
        returned = {str(r[SLICES["sale"]["pk"]]): r for r in data["data"][SLICES["sale"]["root"]]}
        res = classify_batch(SLICES["sale"], batch, returned, prior, sid, "sale", obs)
        events = results_to_events(res, obs)
        if events:
            write_events(conn, events, log=lambda *_a, **_k: None)
        sale["cursor"] = i + len(batch)
        done += 1
        save_sweep_state(state)
    if sale["cursor"] >= sale["round_total"]:
        if not sale.get("epoch"):
            sale["epoch"] = sale["round_started_at"]   # left-censor mark = first full round start
        sale["last_completed_at"] = _iso(now_utc())
        sale["round_file"] = None
        sale["cursor"] = 0
        sale["round_total"] = 0
        save_sweep_state(state)
        log("[sale] ROUND COMPLETE — epoch=%s" % sale["epoch"])
    else:
        log("[sale] round paused at cursor %d/%d (budget exhausted, %d batches this run)"
            % (sale["cursor"], sale["round_total"], done))


def enable_sale():
    state = load_sweep_state()
    state["sale"]["enabled"] = True
    save_sweep_state(state)
    print("sale sweep ENABLED — the next 06:00 scheduled run will start the first full sale round.")
    print("state: %s" % STATE_PATH)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenure", choices=["sale", "rent", "both"], default="both")
    ap.add_argument("--dry-run", action="store_true", help="classify + write CSV; NO DB writes")
    ap.add_argument("--confirm", action="store_true", help="full run: WRITE events to the DB")
    ap.add_argument("--limit", type=int, default=None,
                    help="dry-run: strided sample size per requested tenure (~ids to probe)")
    ap.add_argument("--spacing", type=float, default=DEFAULT_SPACING,
                    help="seconds between queries (floor %ds)" % int(MIN_SPACING_FLOOR))
    ap.add_argument("--scheduled", action="store_true",
                    help="Task-Scheduler entry: state-gated per-slice cadence (rent weekly, sale round resumed nightly)")
    ap.add_argument("--enable-sale", action="store_true",
                    help="one-time: flip sale.enabled=true so the next scheduled run starts the first sale round")
    args = ap.parse_args()

    if args.enable_sale:
        return enable_sale()

    if args.scheduled:
        conn = psycopg2.connect(read_db_url())
        conn.autocommit = False
        try:
            return run_scheduled(conn, args.dry_run)
        finally:
            conn.close()

    if not (args.dry_run or args.confirm):
        print(__doc__)
        return 0
    if args.dry_run and args.confirm:
        print("ERROR: choose --dry-run OR --confirm, not both")
        return 2

    tenures = ["sale", "rent"] if args.tenure == "both" else [args.tenure]
    sweep_ts = now_utc()
    sweep_id = "%s_%s" % (SWEEP_VERSION, sweep_ts.strftime("%Y%m%dT%H%M%SZ"))
    mode = "DRY-RUN (no DB writes)" if args.dry_run else "CONFIRM (writing events)"
    print("=== lifecycle sweep mbl — %s ===" % mode)
    print("sweep_id=%s  spacing=%.0fs  tenures=%s" % (sweep_id, max(MIN_SPACING_FLOOR, args.spacing), tenures))

    conn = psycopg2.connect(read_db_url())
    conn.autocommit = False
    transport = Transport(args.spacing)
    all_results = []
    summaries = []
    try:
        for tenure in tenures:
            active = load_active_ids(conn, tenure)
            prior_absent = load_prior_absent_set(conn, tenure)
            total = len(active)
            ids = strided_sample(active, args.limit) if args.dry_run else active
            print("[%s] active_total=%d  prior_absent=%d  probing=%d"
                  % (tenure, total, len(prior_absent), len(ids)))
            res = sweep_slice(conn, transport, tenure, sweep_id, sweep_ts, ids, prior_absent, print)
            all_results.append((tenure, res))
            summaries.append(summarize(tenure, total, res))

        if args.confirm:
            events = [{"source": "mbl", "id": r["id"], "fastnum": r["fastnum"],
                       "event_type": r["event_type"], "event_at": sweep_ts, "evidence": r["evidence"]}
                      for _t, res in all_results for r in res if r["event_type"]]
            if events:
                write_events(conn, events, print)
            else:
                print("no events to write (all found, no changes)")
        else:
            out = get_scraper_data_dir() / ("lifecycle_sweep_dryrun_%s.csv"
                                            % sweep_ts.strftime("%Y%m%dT%H%M%SZ"))
            write_csv(out, all_results)
            print("CSV: %s" % out)
    finally:
        conn.close()

    print("--- summary (denominators) ---")
    for s in summaries:
        print(("[%(tenure)s] probed=%(swept)d of active_total=%(active_total)d | "
               "found=%(found)d price_changed=%(price_changed)d absent=%(absent)d "
               "(confirmed_absent_1=%(confirmed_absent_1)d withdrawn_confirmed=%(withdrawn_confirmed)d)") % s)
    print("requests_to_mbl=%d" % transport.request_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
