"""run_extraction.py — driver for the extraction engine (EXTRACTION ÞREP 3-5).

  --value-seeded            value every extracted listing that has no valuation yet (NO Haiku).
  --forward N [--trigger T] extract up to N fresh distinct lysingar via Haiku, then value them.

Hard cost guard on the forward path (a cache regression must never silently burn $$):
  --max-n        per-run ceiling on Haiku calls (default 500).
  --daily-cap-usd  cumulative Haiku spend allowed per calendar day (default 10.0); tracked in
                 scraper_data/extraction_cost_state.json. effective N = min(N, max-n, budget-left).
  The per-run cost (calls × per-call) is printed (lands in the nightly promote log / morning report)
  and added to today's tally.

Two connections: read-only (autocommit) for model load + fetch; read-write (SET TRANSACTION
READ WRITE per tx) for the inserts. The Haiku key is read ONLY from D:\env.local via
model_quality_eval.anthropic_key (dotenv_values — never exported, never os.environ); no client is
created on --value-seeded.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"D:\\")

from model_quality_eval import load_models_freeze_anchored, anthropic_key  # noqa: E402
import extraction_engine as E  # noqa: E402

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
COST_STATE = Path(r"D:\verdmat-is\scraper_data\extraction_cost_state.json")
PER_CALL_USD = 0.0071  # VÉL 1 empirical Haiku cost per extraction


def _today():
    return datetime.now().date().isoformat()


def _load_today_spend():
    if COST_STATE.exists():
        try:
            return float(json.loads(COST_STATE.read_text(encoding="utf-8")).get(_today(), 0.0))
        except Exception:
            return 0.0
    return 0.0


def _record_spend(amount):
    data = {}
    if COST_STATE.exists():
        try:
            data = json.loads(COST_STATE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data[_today()] = round(float(data.get(_today(), 0.0)) + amount, 4)
    # keep only the last ~30 days
    for k in sorted(data)[:-30]:
        data.pop(k, None)
    COST_STATE.write_text(json.dumps(data), encoding="utf-8")


def _connect():
    dsn = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    ro = psycopg2.connect(dsn); ro.autocommit = True; ro.set_session(readonly=True)
    rw = psycopg2.connect(dsn); rw.autocommit = False
    return ro, rw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--value-seeded", action="store_true")
    ap.add_argument("--forward", type=int, default=0)
    ap.add_argument("--max-n", type=int, default=500)
    ap.add_argument("--daily-cap-usd", type=float, default=10.0)
    ap.add_argument("--trigger", default="nightly", choices=["nightly", "ondemand"])
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()

    ro, rw = _connect()
    models = load_models_freeze_anchored(ro)

    if args.forward:
        spent = _load_today_spend()
        budget_calls = int(max(0.0, args.daily_cap_usd - spent) / PER_CALL_USD)
        effective_n = min(args.forward, args.max_n, budget_calls)
        print(f"forward: requested={args.forward} max_n={args.max_n} "
              f"daily_cap=${args.daily_cap_usd} spent_today=${spent:.4f} "
              f"budget_calls={budget_calls} -> effective_n={effective_n}")
        if effective_n <= 0:
            print("EXTRACTION SKIPPED: daily cost cap reached (or zero budget).")
            return 0
        need = E.fetch_listings_needing_extraction(ro, effective_n)
        print(f"forward: {len(need)} fresh distinct lysingar to extract (fresh-first)")
        if not args.confirm:
            print("[dry] re-run with --confirm to call Haiku.")
            return 0
        import anthropic
        # Haiku key ONLY from D:\env.local (anthropic_key -> dotenv_values); CC env stays keyless.
        client = anthropic.Anthropic(api_key=anthropic_key(), timeout=60.0, max_retries=0)
        res = E.extract_and_store(rw, client, need, args.trigger)
        _record_spend(res["cost_est_usd"])
        print(f"extract: {res} | day_total=${_load_today_spend():.4f}")

    if args.value_seeded or args.forward:
        rows = E.fetch_extracted_listings_to_value(ro)
        print(f"value: {len(rows)} extracted listings without a valuation")
        if args.confirm or args.value_seeded:
            E.value_listings(rw, models, rows)
        else:
            print("[dry] re-run with --confirm to write valuations.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
