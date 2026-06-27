"""run_extraction.py — driver for the extraction engine (EXTRACTION ÞREP 3-4).

  --value-seeded            value every extracted listing that has no valuation yet (NO Haiku).
  --forward N [--trigger T] extract up to N new distinct lysingar via Haiku, then value them.

Two connections: read-only (autocommit) for model load + fetch; read-write (SET TRANSACTION
READ WRITE per tx) for the inserts. The Haiku key is read ONLY from D:\env.local via
model_quality_eval.anthropic_key (never os.environ); no client is created on --value-seeded.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"D:\\")

from model_quality_eval import load_models_freeze_anchored, anthropic_key  # noqa: E402
import extraction_engine as E  # noqa: E402

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")


def _connect():
    dsn = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    ro = psycopg2.connect(dsn); ro.autocommit = True; ro.set_session(readonly=True)
    rw = psycopg2.connect(dsn); rw.autocommit = False
    return ro, rw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--value-seeded", action="store_true")
    ap.add_argument("--forward", type=int, default=0)
    ap.add_argument("--trigger", default="nightly", choices=["nightly", "ondemand"])
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()

    ro, rw = _connect()
    models = load_models_freeze_anchored(ro)

    if args.forward:
        need = E.fetch_listings_needing_extraction(ro, args.forward)
        print(f"forward: {len(need)} distinct lysingar need extraction")
        if not args.confirm:
            print("[dry] re-run with --confirm to call Haiku.")
            return 0
        import anthropic
        # Haiku key ONLY from D:\env.local (anthropic_key); CC env stays keyless.
        client = anthropic.Anthropic(api_key=anthropic_key(), timeout=60.0, max_retries=0)
        res = E.extract_and_store(rw, client, need, args.trigger)
        print(f"extract: {res}")

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
