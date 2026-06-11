"""prime_delta_since — gated one-shot priming of the mbl delta high-water marks.

§6-A.1 LOCKED RULE: fetch_mbl's delta modes start with since_key=None, which means a
first delta run sweeps from the 1970 epoch — i.e. attempts the WHOLE universe — and if
it hits the --max-pages budget the high-water still advances to the max br_dags/updated
SEEN, silently skipping every changed row beyond the page cap, forever. So before the
first nightly: prime each since_key from the parsed corpus max instead.

Targets (one per delta mode, each its own state dict):
  delta_sale.last_br_dags_seen             = max(br_dags)  WHERE is_negotiable=0
  delta_sale_negotiable.last_br_dags_seen  = max(br_dags)  WHERE is_negotiable=1
  delta_rent.last_updated_seen             = max(updated)  WHERE is_negotiable=0
  delta_rent_negotiable.last_updated_seen  = max(updated)  WHERE is_negotiable=1

SAFETY GATES (each REFUSES with exit 1):
  1. any live fetch_mbl process (PowerShell Win32_Process command-line scan), PLUS a
     state-file recency heuristic (any mode page/run activity within the last 30 min) —
     the heuristic also covers the case where the process scan is unavailable;
  2. any target since_key already set — unless --force, which archives the old value
     into <key>_history first (the b57b7c0 history pattern);
  3. parsed_mbl.db missing, tables missing, or any target slice empty (a NULL max would
     just re-create the 1970 problem).

--dry-run is the DEFAULT; --confirm writes (atomic os.replace via fetch_mbl.save_state).
Before/after values are always printed.

NOTE: the priming RUN itself is a separate gated operational step — it waits for the
full-corpus parse (parsed_mbl.db must hold the whole corpus, not a sample).

stdlib only.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_mbl import (DEFAULT_STATE_PATH, load_state, save_state, now_iso)  # noqa: E402
from init_parsed_mbl_schema import get_parsed_db_path  # noqa: E402

RECENT_MINUTES = 30

# (state_key, since_key, table, column, is_negotiable)
TARGETS = (
    ("delta_sale",             "last_br_dags_seen", "parsed_mbl_sale", "br_dags", 0),
    ("delta_sale_negotiable",  "last_br_dags_seen", "parsed_mbl_sale", "br_dags", 1),
    ("delta_rent",             "last_updated_seen", "parsed_mbl_rent", "updated", 0),
    ("delta_rent_negotiable",  "last_updated_seen", "parsed_mbl_rent", "updated", 1),
)


class PrimeRefusal(RuntimeError):
    pass


# ── gate 1: no live fetcher ──────────────────────────────────────────────────
def _live_fetcher_processes():
    """Return list of python command lines containing 'fetch_mbl', or None if the
    process scan is unavailable (non-Windows / PowerShell failure)."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" "
             "| ForEach-Object { $_.CommandLine }"],
            capture_output=True, text=True, timeout=30)
        lines = (out.stdout or "").splitlines()
        return [ln.strip() for ln in lines if "fetch_mbl" in ln]
    except Exception:
        return None


def _recent_activity(state, now=None):
    """State-file heuristic: any mode with page/run activity in the last RECENT_MINUTES."""
    now = now or datetime.now(timezone.utc)
    hits = []
    for key, sub in state.items():
        if not isinstance(sub, dict):
            continue
        for ts_field in ("last_page_at", "last_run_at"):
            ts = sub.get(ts_field)
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts)
            except ValueError:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if (now - dt).total_seconds() < RECENT_MINUTES * 60:
                hits.append("%s.%s=%s" % (key, ts_field, ts))
    return hits


def check_no_fetcher(state, now=None):
    procs = _live_fetcher_processes()
    if procs:
        raise PrimeRefusal("live fetch_mbl process(es): %s" % "; ".join(procs)[:300])
    recent = _recent_activity(state, now)
    if recent:
        raise PrimeRefusal("recent fetcher activity in state (<%d min): %s"
                           % (RECENT_MINUTES, "; ".join(recent)[:300]))
    if procs is None:
        return "process scan unavailable — relied on state-recency heuristic only"
    return None


# ── gate 3 + value computation ───────────────────────────────────────────────
def compute_since_values(parsed_conn):
    """Return [(state_key, since_key, value), ...]; REFUSE on missing tables/empty slices."""
    values, empty = [], []
    for state_key, since_key, table, col, neg in TARGETS:
        try:
            row = parsed_conn.execute(
                "SELECT MAX(%s) FROM %s WHERE is_negotiable=?" % (col, table), (neg,)).fetchone()
        except sqlite3.OperationalError as e:
            raise PrimeRefusal("parsed_mbl schema missing/incomplete: %s" % e)
        if row is None or row[0] is None:
            empty.append("%s (%s, is_negotiable=%d)" % (state_key, table, neg))
        else:
            values.append((state_key, since_key, row[0]))
    if empty:
        raise PrimeRefusal("empty parsed slice(s) — refuse to prime with NULL "
                           "(would re-create the 1970 sweep): %s" % ", ".join(empty))
    return values


# ── gate 2 + state mutation (pure on the dict) ───────────────────────────────
def prime(state, values, *, force=False):
    """Apply since values to the state dict. Returns [(key, since_key, old, new), ...]."""
    already = ["%s.%s=%s" % (k, sk, state.get(k, {}).get(sk))
               for k, sk, _ in values if state.get(k, {}).get(sk) is not None]
    if already and not force:
        raise PrimeRefusal("since_key(s) already set (use --force to archive+overwrite): %s"
                           % "; ".join(already))
    changes = []
    for key, since_key, val in values:
        sub = state.setdefault(key, {since_key: None, "last_run_at": None, "halt_reason": None})
        old = sub.get(since_key)
        if old is not None:                       # --force path: archive before overwrite
            state.setdefault(key + "_history", []).append(
                {since_key: old, "archived_at": now_iso()})
        sub[since_key] = val
        changes.append((key, since_key, old, val))
    return changes


# ── orchestration (testable; main() is thin wiring) ──────────────────────────
def run_priming(parsed_conn, state_path, *, confirm=False, force=False, now=None, log=print):
    state = load_state(state_path)
    warn = check_no_fetcher(state, now)           # gate 1 (raises)
    if warn:
        log("  WARNING: %s" % warn)
    values = compute_since_values(parsed_conn)    # gate 3 (raises)
    changes = prime(state, values, force=force)   # gate 2 (raises)
    for key, since_key, old, new in changes:
        log("  %s.%s : %s  ->  %s" % (key, since_key, old, new))
    if confirm:
        save_state(state_path, state)             # atomic os.replace
        log("  WRITTEN to %s" % state_path)
    else:
        log("  [dry-run] nothing written (re-run with --confirm)")
    return changes


def main():
    ap = argparse.ArgumentParser(description="prime mbl delta since_keys from parsed corpus")
    ap.add_argument("--confirm", action="store_true", help="write (default is dry-run)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite already-set since_keys (archives old values)")
    ap.add_argument("--state-file", default=DEFAULT_STATE_PATH)
    ap.add_argument("--parsed-db", default=None)
    args = ap.parse_args()

    db = Path(args.parsed_db) if args.parsed_db else get_parsed_db_path()
    if not db.is_file():
        print("REFUSED: parsed_mbl.db not found at %s" % db)
        return 1
    parsed_conn = sqlite3.connect("file:%s?mode=ro" % str(db).replace("\\", "/"), uri=True)
    print("=== prime_delta_since (%s) ===" % ("CONFIRM" if args.confirm else "dry-run"))
    print("parsed DB : %s" % db)
    print("state     : %s" % args.state_file)
    try:
        run_priming(parsed_conn, args.state_file, confirm=args.confirm, force=args.force)
    except PrimeRefusal as e:
        print("REFUSED: %s" % e)
        return 1
    finally:
        parsed_conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
