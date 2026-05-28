"""run_monthly.py — Phase X Group C monthly orchestrator.

Wraps the 6 D:\\ monthly scripts in order, captures an inputs_snapshot,
builds precompute outputs, runs ALL safety gates (CPI shrinkage,
rebuild shape-drift, recalibration drift-blocker, validate_metrics),
then HALTS before pushing precompute CSVs to Supabase.

Push is intentionally a separate confirmed step for now — flip to
auto-on-all-green after 2-3 proven cycles.

Steps (in order):
  1. D:\\refresh_cpi.py
  2. D:\\refresh_kaupskra.py
  3. D:\\rebuild_training_data.py
  4. D:\\refresh_dashboard_tables.py
  5. D:\\monthly_recalibration.py
  6. D:\\validate_metrics.py
  7. D:\\verdmat-is\\precompute\\build_precompute.py
  8. capture inputs_snapshot (writes to Supabase)
  9. HALT — print push-preview, exit; operator runs --push to apply.

Each step is logged to public.pipeline_steps with rowcount-before/after
where measurable, plus a single public.pipeline_runs row for the run.

Cadence: any convenient fixed day. refresh_kaupskra is idempotent on
HMS Last-Modified, so a no-op cycle is fine. Recommended: 1st of each
month 03:30 local (post nightly R2 backup at 03:00). Schedule via
Windows Task Scheduler — same pattern as register_backup_task.ps1.
DO NOT register the task yet; that comes after first manual clean run.

CLI:
  python run_monthly.py              — run pipeline, HALT before push
  python run_monthly.py --dry-run    — log a planned run, execute nothing
  python run_monthly.py --push       — push precompute CSVs to Supabase
                                       (after a prior --report-only finished green)

This script does NOT auto-push. The push must be a separately invoked,
operator-confirmed step until the pipeline is proven over multiple cycles.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

# Local helpers
sys.path.insert(0, str(Path(__file__).parent))
from migration_helpers import (  # noqa: E402
    open_connection,
    subprocess_with_shape_safety,
    file_md5_hex,
    git_sha_head,
    unnest_upsert,
)

DATA = Path(r"D:\\")
PRECOMPUTE = DATA / "verdmat-is" / "precompute"
EXPORTS = PRECOMPUTE / "exports"
RUN_LOG_DIR = Path(r"D:\verdmat-is\app\audit\monthly_runs")
RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------------------
# Step manifest — name, command, optional shape-safety probe
# ----------------------------------------------------------------------
STEPS: list[dict] = [
    {
        "name": "refresh_cpi",
        "cmd": ["python", str(DATA / "refresh_cpi.py")],
        "output": DATA / "cpi_verdtrygging.csv",
        "rowcount_fn": lambda p: sum(1 for _ in open(p, encoding="utf-8")) - 1,
        "max_shrink_pct": 5.0,
    },
    {
        "name": "refresh_kaupskra",
        "cmd": ["python", str(DATA / "refresh_kaupskra.py")],
        "output": DATA / "kaupskra.csv",
        "rowcount_fn": lambda p: sum(1 for _ in open(p, encoding="latin-1")) - 1,
        "max_shrink_pct": 1.0,  # kaupskra is append-only; ANY shrinkage is suspicious
    },
    {
        "name": "rebuild_training_data",
        "cmd": ["python", str(DATA / "rebuild_training_data.py")],
        "output": DATA / "training_data_v2.pkl",
        "rowcount_fn": None,  # pickle — script has its own internal halt-on-10%-drift
        "max_shrink_pct": 10.0,
    },
    {
        "name": "refresh_dashboard_tables",
        "cmd": ["python", str(DATA / "refresh_dashboard_tables.py")],
        "output": DATA / "repeat_sale_index.csv",
        "rowcount_fn": lambda p: sum(1 for _ in open(p, encoding="utf-8-sig")) - 1,
        "max_shrink_pct": 5.0,  # matches refresh_dashboard_tables internal default
    },
    {
        "name": "monthly_recalibration",
        "cmd": ["python", str(DATA / "monthly_recalibration.py")],
        "output": DATA / "calibration_config.json",
        "rowcount_fn": None,  # JSON — script has its own halt-on-30%-drift
        "max_shrink_pct": None,
    },
    {
        "name": "validate_metrics",
        "cmd": ["python", str(DATA / "validate_metrics.py")],
        "output": None,  # log file only; exit code is the gate
        "rowcount_fn": None,
        "max_shrink_pct": None,
    },
    {
        "name": "build_precompute",
        "cmd": ["python", str(PRECOMPUTE / "build_precompute.py")],
        "output": EXPORTS / "properties.csv",
        "rowcount_fn": lambda p: sum(1 for _ in open(p, encoding="utf-8")) - 1,
        "max_shrink_pct": 5.0,
    },
]


# ----------------------------------------------------------------------
# pipeline_runs / pipeline_steps writers (via service-role .dbconfig)
# ----------------------------------------------------------------------
def create_pipeline_run(conn, run_type: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.pipeline_runs
              (run_type, started_at, host, git_sha)
            VALUES (%s, now(), %s, %s)
            RETURNING id
            """,
            (run_type, socket.gethostname(), git_sha_head() or "unknown"),
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def create_pipeline_step(conn, run_id: int, step_name: str, order: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.pipeline_steps
              (run_id, step_name, step_order, started_at)
            VALUES (%s, %s, %s, now())
            RETURNING id
            """,
            (run_id, step_name, order),
        )
        step_id = cur.fetchone()[0]
    conn.commit()
    return step_id


def finalize_pipeline_step(
    conn,
    step_id: int,
    exit_code: int,
    *,
    rowcount_before: int | None = None,
    rowcount_after: int | None = None,
    notes: str | None = None,
    output_paths: list[str] | None = None,
    log_path: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.pipeline_steps
            SET ended_at=now(),
                exit_code=%s,
                rowcount_before=%s,
                rowcount_after=%s,
                notes=%s,
                output_paths=%s,
                log_path=%s
            WHERE id=%s
            """,
            (
                exit_code, rowcount_before, rowcount_after, notes,
                json.dumps(output_paths) if output_paths else None,
                log_path, step_id,
            ),
        )
    conn.commit()


def finalize_pipeline_run(
    conn, run_id: int, exit_status: str, summary: dict | None = None
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.pipeline_runs
            SET ended_at=now(), exit_status=%s, summary=%s
            WHERE id=%s
            """,
            (exit_status, json.dumps(summary) if summary else None, run_id),
        )
    conn.commit()


# ----------------------------------------------------------------------
# inputs_snapshot capture
# ----------------------------------------------------------------------
def capture_inputs_snapshot(conn, run_id: int) -> int:
    """Write one inputs_snapshots row fingerprinting current input state.

    Reads:
      - D:\\cpi_verdtrygging.csv  (md5)
      - D:\\kaupskra.csv          (md5; Last-Modified from kaupskra_fetch_state.json)
      - D:\\training_data_v2.pkl  (md5)
      - iter4a_main_mean.lgb     (feature_names list → hash)
      - Supabase predictions table (model_version, calibration_version, row counts)
    """
    import lightgbm as lgb

    # Fingerprint inputs
    cpi_md5 = file_md5_hex(DATA / "cpi_verdtrygging.csv")
    kaupskra_md5 = file_md5_hex(DATA / "kaupskra.csv")
    training_md5 = file_md5_hex(DATA / "training_data_v2.pkl")

    # kaupskra Last-Modified from state file
    state_path = DATA / "kaupskra_fetch_state.json"
    kaupskra_last_mod = None
    if state_path.exists():
        st = json.loads(state_path.read_text(encoding="utf-8"))
        lm = st.get("last_modified")
        if lm:
            try:
                from email.utils import parsedate_to_datetime
                kaupskra_last_mod = parsedate_to_datetime(lm)
            except Exception:
                kaupskra_last_mod = None

    # Feature names hash from main mean booster
    booster = lgb.Booster(model_file=str(DATA / "iter4a_main_mean.lgb"))
    feature_names = booster.feature_name()
    import hashlib
    feat_hash = hashlib.sha256(
        "\n".join(feature_names).encode("utf-8")
    ).hexdigest()

    # Universe sizes from live Supabase
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

    # CPI factor at current valuation period
    # Read from training_data_v2 last (year, month) — same source as score_extract
    import pandas as pd
    td = pd.read_pickle(DATA / "training_data_v2.pkl")
    td["_yr"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.year
    td["_mn"] = pd.to_datetime(td["THINGLYSTDAGS"]).dt.month
    cpi_lookup = td.groupby(["_yr", "_mn"])["cpi_factor"].first().to_dict()
    latest_ym = max(cpi_lookup.keys())
    val_year, val_month = latest_ym
    cpi_factor_at_val = float(cpi_lookup[latest_ym])

    # precompute_git_sha — separate repo
    precompute_sha = git_sha_head(PRECOMPUTE) if PRECOMPUTE.exists() else None

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.inputs_snapshots
              (run_id, model_version, calibration_version,
               valuation_year, valuation_month, cpi_factor_at_val,
               cpi_csv_md5, kaupskra_csv_md5, kaupskra_last_mod,
               training_data_v2_md5, feature_names_hash,
               properties_n, predictions_n,
               git_sha, precompute_git_sha)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                run_id, mv, cv, val_year, val_month, cpi_factor_at_val,
                cpi_md5, kaupskra_md5, kaupskra_last_mod,
                training_md5, feat_hash,
                properties_n, predictions_n,
                git_sha_head() or "unknown", precompute_sha,
            ),
        )
        snapshot_id = cur.fetchone()[0]
    conn.commit()
    return snapshot_id


# ----------------------------------------------------------------------
# Push preview — diff each precompute CSV vs live Supabase
# ----------------------------------------------------------------------
PRECOMPUTE_TARGETS = [
    ("properties", "properties.csv"),
    ("predictions", "predictions.csv"),
    ("sales_history", "sales_history.csv"),
    ("repeat_sale_index", "repeat_sale_index.csv"),
    ("ats_lookup", "ats_lookup.csv"),
    ("comps_index", "comps_index.csv"),
    ("feature_attributions", "feature_attributions.csv"),
]


def push_preview(conn) -> list[dict]:
    """For each precompute CSV, compute (csv_rows, live_rows, delta).

    Read-only. Does NOT push. Returns a list of dicts the operator
    reviews before calling run_monthly.py --push.
    """
    import pandas as pd
    out = []
    for table, csv_name in PRECOMPUTE_TARGETS:
        csv_path = EXPORTS / csv_name
        if not csv_path.exists():
            out.append({"table": table, "csv_rows": None,
                        "live_rows": None, "note": "csv missing"})
            continue
        # Count CSV rows (header-aware)
        try:
            csv_rows = sum(1 for _ in open(csv_path, encoding="utf-8")) - 1
        except Exception as e:
            out.append({"table": table, "csv_rows": None,
                        "live_rows": None, "note": f"csv read error: {e}"})
            continue
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM public.{table}")
            live_rows = cur.fetchone()[0]
        delta = csv_rows - live_rows
        out.append({
            "table": table,
            "csv_rows": csv_rows,
            "live_rows": live_rows,
            "delta": delta,
            "note": "",
        })
    return out


def push_precompute_to_supabase(conn, run_id: int) -> None:
    """Generalised phase_d3_apply UPSERT for the 7 precompute CSVs.

    NOT EXECUTED by the default run_monthly.py invocation. Operator runs
    `--push` explicitly after reviewing the push-preview report. Logged
    as separate pipeline_steps rows under the same run_id.

    Each table goes through migration_helpers.unnest_upsert with
    ON CONFLICT DO UPDATE on the natural key. Idempotent.
    """
    raise NotImplementedError(
        "push_precompute_to_supabase is intentionally not implemented in "
        "this lota — the push pattern is the generalised phase_d3_apply "
        "UNNEST upsert; landing it requires (a) per-table column-type maps, "
        "(b) ON CONFLICT key per table, (c) the precompute pre-data lota's "
        "first clean manual run. Tracked as Group C follow-up."
    )


# ----------------------------------------------------------------------
# Run-log writer (parallel local log; pipeline_steps is the canonical record)
# ----------------------------------------------------------------------
def write_run_log(run_id: int, step_records: list[dict]) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RUN_LOG_DIR / f"run_{ts}_run-{run_id}.json"
    path.write_text(
        json.dumps({"run_id": run_id, "steps": step_records}, indent=2, default=str),
        encoding="utf-8",
    )
    return path


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Log a planned run, execute nothing")
    parser.add_argument("--push", action="store_true",
                        help="Run push_precompute_to_supabase (not implemented yet)")
    args = parser.parse_args()

    if args.push:
        print("ERROR: --push not implemented in this lota.")
        print("After 2-3 proven cycles of the dry pipeline + manual push, ")
        print("we will land push_precompute_to_supabase as a generalised ")
        print("phase_d3_apply UPSERT pattern. Use Supabase Studio or ")
        print("scripts/import_iter4.py-style one-offs for now.")
        return 2

    print(f"=== run_monthly.py ({'DRY-RUN' if args.dry_run else 'LIVE'}) ===")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")

    conn = open_connection()
    run_id = create_pipeline_run(conn, "monthly")
    print(f"  pipeline_runs.id = {run_id}")

    step_records: list[dict] = []
    current_step_id: int | None = None  # tracks the in-flight step for crash-finalize

    try:
        for order, step in enumerate(STEPS, 1):
            name = step["name"]
            cmd = step["cmd"]
            out_path = step.get("output")
            rowcount_fn = step.get("rowcount_fn")
            max_shrink = step.get("max_shrink_pct")
            print(f"\n[{order}/{len(STEPS)}] {name}")
            step_id = create_pipeline_step(conn, run_id, name, order)
            current_step_id = step_id

            rowcount_before = None
            if out_path and out_path.exists() and rowcount_fn:
                try:
                    rowcount_before = rowcount_fn(out_path)
                except Exception:
                    rowcount_before = None

            if args.dry_run:
                print(f"    DRY-RUN — would invoke: {' '.join(str(x) for x in cmd)}")
                finalize_pipeline_step(
                    conn, step_id, 0,
                    rowcount_before=rowcount_before,
                    notes="dry-run"
                )
                current_step_id = None
                step_records.append({
                    "step": name, "exit": 0, "dry_run": True,
                    "rowcount_before": rowcount_before,
                })
                continue

            t0 = time.time()
            exit_code, rowcount_after, msg = subprocess_with_shape_safety(
                cmd,
                output_path=out_path,
                rowcount_before=rowcount_before,
                rowcount_after_fn=rowcount_fn,
                max_shrink_pct=max_shrink if max_shrink is not None else 100.0,
                timeout=3600,
            )
            elapsed = time.time() - t0
            print(f"    exit={exit_code}  elapsed={elapsed:.1f}s  {msg}")

            finalize_pipeline_step(
                conn, step_id, exit_code,
                rowcount_before=rowcount_before,
                rowcount_after=rowcount_after,
                notes=msg,
            )
            current_step_id = None
            step_records.append({
                "step": name, "exit": exit_code, "elapsed_s": round(elapsed, 1),
                "rowcount_before": rowcount_before,
                "rowcount_after": rowcount_after,
                "message": msg,
            })

            if exit_code != 0:
                print(f"\n*** HALT — step {name} failed (exit={exit_code}). ***")
                finalize_pipeline_run(
                    conn, run_id, "halted",
                    summary={"halt_at_step": name, "exit_code": exit_code, "msg": msg},
                )
                log_path = write_run_log(run_id, step_records)
                print(f"    run-log: {log_path}")
                conn.close()
                return 3

        # ============================================================
        # All 7 steps green. Capture inputs_snapshot + push-preview.
        # ============================================================
        if args.dry_run:
            print("\nDRY-RUN — skipping inputs_snapshot + push-preview")
            finalize_pipeline_run(
                conn, run_id, "success",
                summary={"mode": "dry-run", "step_count": len(STEPS)}
            )
            log_path = write_run_log(run_id, step_records)
            print(f"\nRun log: {log_path}")
            conn.close()
            return 0

        print("\nCapturing inputs_snapshot ...")
        snap_id = capture_inputs_snapshot(conn, run_id)
        print(f"    inputs_snapshots.id = {snap_id}")

        print("\nPush preview (precompute CSV → live Supabase row deltas):")
        preview = push_preview(conn)
        print(f"  {'table':<24s} {'csv_rows':>10s} {'live_rows':>10s} {'delta':>10s}  note")
        for r in preview:
            cr = f"{r['csv_rows']:,}" if r.get('csv_rows') is not None else "-"
            lr = f"{r['live_rows']:,}" if r.get('live_rows') is not None else "-"
            dl = f"{r['delta']:+,}" if r.get('delta') is not None else "-"
            print(f"  {r['table']:<24s} {cr:>10s} {lr:>10s} {dl:>10s}  {r.get('note','')}")

        finalize_pipeline_run(
            conn, run_id, "success_halt_pre_push",
            summary={
                "step_count": len(STEPS),
                "snapshot_id": snap_id,
                "push_preview": preview,
            },
        )
        log_path = write_run_log(run_id, step_records + [{
            "step": "_push_preview", "preview": preview, "snapshot_id": snap_id,
        }])

        print(f"\n*** HALT before push. Pipeline is GREEN. ***")
        print(f"    Run log:           {log_path}")
        print(f"    inputs_snapshot:   public.inputs_snapshots.id = {snap_id}")
        print(f"    pipeline_runs.id:  {run_id}  (exit_status='success_halt_pre_push')")
        print(f"\n    Review the push preview above. To push:")
        print(f"      python run_monthly.py --push   (not implemented yet — manual import)")
        conn.close()
        return 0

    except Exception as exc:
        # Crash-finalize: never leave a dangling pipeline_runs / in-flight step.
        import traceback
        tb_head = "\n".join(traceback.format_exc().splitlines()[:10])
        if current_step_id is not None:
            try:
                finalize_pipeline_step(
                    conn, current_step_id, -1,
                    notes=f"crashed: {exc!r}\n{tb_head}",
                )
            except Exception:
                pass
        try:
            finalize_pipeline_run(
                conn, run_id, "crashed",
                summary={"exception": repr(exc), "traceback_head": tb_head},
            )
        except Exception:
            pass
        try:
            write_run_log(run_id, step_records + [{"step": "_crash", "exception": repr(exc)}])
        except Exception:
            pass
        print(f"\n*** CRASH — orchestrator exception ***\n{exc!r}\n{tb_head}")
        try:
            conn.close()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
