"""backfill_current_snapshot.py — write ONE inputs_snapshots row anchoring
the current live prediction batch (post-D3 + post-column-grant-lockout).

Run ONCE after the Group C migration applies. No pipeline_runs row is
created — this snapshot is operator-historical, not a run output. The
run_id column is left NULL.

The row pins the answer to: "What inputs produced the 167,503 predictions
currently in public.predictions tagged iter4_final_v1 / iter4_conformal_v1?"

Reads:
  D:\\cpi_verdtrygging.csv     (md5)
  D:\\kaupskra.csv              (md5; Last-Modified from kaupskra_fetch_state)
  D:\\training_data_v2.pkl      (md5)
  D:\\iter4a_main_mean.lgb      (feature_names → hash)
  Supabase public.predictions  (model_version, calibration_version, row counts)

Writes:
  ONE row into public.inputs_snapshots with extra.note='backfill of current state'.

Idempotency:
  Re-running creates a NEW row (insert-only). Re-runs are flagged with
  extra.note='backfill (re-run)'. The reproducibility ledger preserves
  history; we never overwrite or delete.

CLI:
  python backfill_current_snapshot.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

sys.path.insert(0, str(Path(__file__).parent))
from migration_helpers import (  # noqa: E402
    open_connection, file_md5_hex, git_sha_head,
)

DATA = Path(r"D:\\")
PRECOMPUTE = DATA / "verdmat-is" / "precompute"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be inserted; do not write")
    parser.add_argument("--note", default="backfill of current state",
                        help="Free-form note recorded in extra.note")
    args = parser.parse_args()

    print("=== backfill_current_snapshot ===")

    # File fingerprints
    fingerprints = {}
    for label, path in [
        ("cpi_csv_md5", DATA / "cpi_verdtrygging.csv"),
        ("kaupskra_csv_md5", DATA / "kaupskra.csv"),
        ("training_data_v2_md5", DATA / "training_data_v2.pkl"),
    ]:
        if not path.exists():
            print(f"  MISSING: {path}")
            return 2
        fingerprints[label] = file_md5_hex(path)
        print(f"  {label:<26s} {fingerprints[label][:12]}…  ({path})")

    # kaupskra Last-Modified
    state_path = DATA / "kaupskra_fetch_state.json"
    kaupskra_last_mod = None
    if state_path.exists():
        st = json.loads(state_path.read_text(encoding="utf-8"))
        lm = st.get("last_modified")
        if lm:
            try:
                kaupskra_last_mod = parsedate_to_datetime(lm)
            except Exception:
                kaupskra_last_mod = None
    print(f"  kaupskra_last_mod         {kaupskra_last_mod}")

    # Feature names hash
    import lightgbm as lgb
    booster = lgb.Booster(model_file=str(DATA / "iter4a_main_mean.lgb"))
    feature_names = booster.feature_name()
    feat_hash = hashlib.sha256("\n".join(feature_names).encode("utf-8")).hexdigest()
    print(f"  feature_names_hash        {feat_hash[:12]}…  ({len(feature_names)} features)")

    # Connect + measure live state
    conn = open_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM public.properties")
        properties_n = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM public.predictions")
        predictions_n = cur.fetchone()[0]
        cur.execute("""
            SELECT model_version, calibration_version, count(*)
            FROM public.predictions
            GROUP BY 1,2
            ORDER BY 3 DESC
            LIMIT 1
        """)
        mv, cv, _ = cur.fetchone()
    print(f"  properties_n              {properties_n:,}")
    print(f"  predictions_n             {predictions_n:,}")
    print(f"  model_version             {mv}")
    print(f"  calibration_version       {cv}")

    # CPI factor at current valuation period
    import pandas as pd
    td = pd.read_pickle(DATA / "training_data_v2.pkl")
    td["_yr"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.year
    td["_mn"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.month
    cpi_lookup = td.groupby(["_yr", "_mn"])["cpi_factor"].first().to_dict()
    latest_ym = max(cpi_lookup.keys())
    val_year, val_month = latest_ym
    cpi_factor_at_val = float(cpi_lookup[latest_ym])
    print(f"  valuation period          {val_year}-{val_month:02d}")
    print(f"  cpi_factor_at_val         {cpi_factor_at_val:.6f}")

    # git SHAs
    gs = git_sha_head() or "unknown"
    pgs = git_sha_head(PRECOMPUTE) if PRECOMPUTE.exists() else None
    print(f"  git_sha                   {gs[:12]}…")
    print(f"  precompute_git_sha        {pgs[:12] if pgs else None}…")

    extra = {
        "note": args.note,
        "captured_via": "scripts/backfill_current_snapshot.py",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "feature_count": len(feature_names),
    }

    if args.dry_run:
        print("\nDRY-RUN — no row written.")
        conn.close()
        return 0

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.inputs_snapshots
              (run_id, model_version, calibration_version,
               valuation_year, valuation_month, cpi_factor_at_val,
               cpi_csv_md5, kaupskra_csv_md5, kaupskra_last_mod,
               training_data_v2_md5, feature_names_hash,
               properties_n, predictions_n,
               git_sha, precompute_git_sha,
               extra)
            VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                mv, cv, val_year, val_month, cpi_factor_at_val,
                fingerprints["cpi_csv_md5"],
                fingerprints["kaupskra_csv_md5"],
                kaupskra_last_mod,
                fingerprints["training_data_v2_md5"],
                feat_hash,
                properties_n, predictions_n,
                gs, pgs,
                json.dumps(extra),
            ),
        )
        snap_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    print(f"\nWrote public.inputs_snapshots.id = {snap_id}")
    print(f"  This row anchors the {predictions_n:,}-row prediction batch")
    print(f"  tagged {mv}/{cv} that is currently live on prod.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
