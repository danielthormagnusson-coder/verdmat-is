"""monthly_cpi_reanchor.py — CPI re-anchor engine (braut 2 core).

When a new VNV month enters D:\\cpi_verdtrygging.csv, the reference anchor for
kaupverd_real moves. This engine re-deflates ALL sales_history.kaupverd_real to
the new anchor in ONE atomic transaction, advances the live anchor key, and
upserts the new CPI month — keeping anchor + real + cpi_index perfectly in sync.

Cadence-separated from the daily fresh-data path (daily_sales_refresh.py) and the
monthly model pipeline (run_monthly.py). It touches ONLY kaupverd_real (a pure
re-expression on a new anchor — nominal/thinglystdags/onothaefur/einflm/byggar
untouched), public.pipeline_config.sales_history_anchor_ym, and public.cpi_index.
It NEVER moves model_pred_anchor_ym (iter5 deploy only) and NEVER touches
predictions / any model output. v_model_vs_sold is anchor-independent (nominal/
nominal) so this re-anchor cannot desync it.

Reuses the derive core from rebuild_sales_history.py by import — re-anchor is the
SAME Python float64 derive path with a different anchor's cpi_lookup, guaranteeing
parity with how the rows were built (no SQL-round drift).

Gate is DB-side, not refresh_cpi stdout: max(cpi_verdtrygging.csv) vs the live
sales_history_anchor_ym. New month => re-anchor; else no-op.

CLI:
  python scripts/monthly_cpi_reanchor.py --dryrun                 # gate + measure, no writes
  python scripts/monthly_cpi_reanchor.py --dryrun --test-anchor 2026-06  # force anchor for test
  python scripts/monthly_cpi_reanchor.py                          # LIVE re-anchor (one atomic txn)
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from rebuild_sales_history import (  # noqa: E402  reuse derive core, no re-implementation
    load_cpi_lookup,
    derive_sales_rows,
    fetch_valid_fastnums,
    open_ro_conn,
    CPI_CSV,
    KAUPSKRA_CSV,
    REFRESH_KAUPSKRA,  # noqa: F401  (kept for symmetry; not used here)
    DBCONFIG,
)
from anchor_config import read_anchor  # noqa: E402  reads sales_history_anchor_ym
from daily_sales_refresh import MV_LIST  # noqa: E402  single source of truth for the 13 MV

sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(
    sys.stdout, "reconfigure") else None

REFRESH_CPI = Path(r"D:\refresh_cpi.py")
LOGFILE = Path(r"D:\monthly_cpi_reanchor.log")
LIVE_ANCHOR_KEY = "sales_history_anchor_ym"


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def csv_max_month() -> str:
    """Return MAX(year_month) present in D:\\cpi_verdtrygging.csv."""
    mx = None
    with open(CPI_CSV, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            ym = r["year_month"]
            if mx is None or ym > mx:
                mx = ym
    if mx is None:
        raise SystemExit(f"no rows in {CPI_CSV}")
    return mx


def csv_rows_at_or_after(ym: str) -> list[tuple[str, float]]:
    """CPI rows with year_month >= ym (for upserting newly-arrived months)."""
    out = []
    with open(CPI_CSV, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["year_month"] >= ym:
                out.append((r["year_month"], float(r["cpi"])))
    return out


def py(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if v is pd.NA:
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun", action="store_true", help="gate + measure, no writes")
    ap.add_argument("--test-anchor", default=None,
                    help="force this anchor (YYYY-MM) for dryrun testing; bypasses the gate")
    args = ap.parse_args()

    log(f"=== monthly_cpi_reanchor ({'DRYRUN' if args.dryrun else 'LIVE'}"
        f"{', TEST-ANCHOR ' + args.test_anchor if args.test_anchor else ''}) ===")

    # ---- Step 0: refresh_cpi (diagnostic only) ----
    if not args.test_anchor:
        log("[0] running refresh_cpi.py ...")
        res = subprocess.run([sys.executable, str(REFRESH_CPI)],
                             capture_output=True, text=True, timeout=300)
        if res.returncode != 0:
            log(f"[0] ERROR refresh_cpi exit={res.returncode}; "
                f"stderr tail: {(res.stderr or '')[-400:]}")
            return 1
        tail = (res.stdout or "").strip().splitlines()[-3:]
        log(f"[0] refresh_cpi tail: {' | '.join(tail)}")
    else:
        log("[0] --test-anchor set — skipping refresh_cpi (using CSV on disk)")

    # ---- Step 2: DB-side gate ----
    conn_ro = open_ro_conn()
    cur_anchor = read_anchor(conn_ro)
    new_anchor = args.test_anchor or csv_max_month()
    log(f"[2] cur_anchor(live)={cur_anchor}  new_anchor={new_anchor}  "
        f"(source={'--test-anchor' if args.test_anchor else 'max(csv)'})")

    if not args.test_anchor and new_anchor <= cur_anchor:
        log(f"[2] anchor unchanged (new={new_anchor} <= cur={cur_anchor}) — no-op. Exiting.")
        conn_ro.close()
        return 0

    # ---- Step 3: re-derive at the new anchor (Python parity) ----
    cpi = load_cpi_lookup(CPI_CSV, new_anchor)  # raises if new_anchor absent — free HALT guard
    valid_fastnums = fetch_valid_fastnums(conn_ro)
    kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
    derived, stats = derive_sales_rows(kp, valid_fastnums, cpi)
    log(f"[3] re-derived at anchor={new_anchor}: final_rows={stats['final_rows']:,}, "
        f"fk_dropped={stats['fk_dropped_rows']:,}, rows_without_cpi={stats['rows_without_cpi']:,}")

    # ---- Step 4: measure change vs live (read) ----
    with conn_ro.cursor() as cur:
        cur.execute("SELECT faerslunumer, fastnum, kaupverd_real, kaupverd_nominal, "
                    "thinglystdags, onothaefur FROM public.sales_history "
                    "WHERE faerslunumer IS NOT NULL")
        live = pd.DataFrame(cur.fetchall(), columns=[
            "faerslunumer", "fastnum", "kaupverd_real", "kaupverd_nominal",
            "thinglystdags", "onothaefur"])
    conn_ro.close()  # done reading before any write txn

    d = derived[derived["faerslunumer"].notna()].copy()
    d["faerslunumer"] = d["faerslunumer"].astype("int64")
    d["fastnum"] = d["fastnum"].astype("int64")
    live["faerslunumer"] = live["faerslunumer"].astype("int64")
    live["fastnum"] = live["fastnum"].astype("int64")
    m = live.merge(
        d[["faerslunumer", "fastnum", "kaupverd_real", "kaupverd_nominal",
           "thinglystdags", "onothaefur"]],
        on=["faerslunumer", "fastnum"], suffixes=("_old", "_new"))
    log(f"[4] common rows (composite-key join): {len(m):,}")

    new_real = pd.to_numeric(m["kaupverd_real_new"], errors="coerce")
    old_real = pd.to_numeric(m["kaupverd_real_old"], errors="coerce")
    changed = (new_real.values != old_real.values)
    n_changed = int(changed.sum())
    abs_delta = (new_real.values - old_real.values)
    max_abs = int(pd.Series(abs_delta).abs().max()) if len(abs_delta) else 0
    log(f"[4] kaupverd_real changes: {n_changed:,} of {len(m):,} common rows; "
        f"max abs delta={max_abs:,} kr")
    ex = m[changed].head(10)
    for _, r in ex.iterrows():
        ym = pd.to_datetime(r["thinglystdags_old"]).strftime("%Y-%m")
        log(f"      f={int(r['faerslunumer'])} fn={int(r['fastnum'])} {ym} "
            f"nominal={int(r['kaupverd_nominal_old']):,} "
            f"real {int(r['kaupverd_real_old']):,} -> {int(r['kaupverd_real_new']):,}")
    # SANITY: nominal/thinglystdags/onothaefur must NOT change (re-anchor touches only real)
    nom_chg = int((pd.to_numeric(m["kaupverd_nominal_new"]).values
                   != pd.to_numeric(m["kaupverd_nominal_old"]).values).sum())
    ono_chg = int((pd.to_numeric(m["onothaefur_new"]).values
                   != pd.to_numeric(m["onothaefur_old"]).values).sum())
    dt_chg = int((pd.to_datetime(m["thinglystdags_new"]).dt.date.values
                  != pd.to_datetime(m["thinglystdags_old"]).dt.date.values).sum())
    log(f"[4] SANITY (must be 0): nominal_changed={nom_chg}, onothaefur_changed={ono_chg}, "
        f"thinglystdags_changed={dt_chg}")
    if nom_chg or ono_chg or dt_chg:
        log("[4] ABORT: re-anchor would change non-real columns — unexpected. No writes.")
        return 3

    # rows to write: composite key + new real (write all common rows; UPDATE is idempotent
    # on unchanged values). Built vectorized from the merged frame.
    upd_rows = [(int(f), int(fn), py(r))
                for f, fn, r in zip(m["faerslunumer"], m["fastnum"], m["kaupverd_real_new"])]

    import psycopg2
    from psycopg2.extras import execute_values

    # ---- Step 5a: DRYRUN — measure UPDATE on a rolled-back txn ----
    if args.dryrun:
        url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
        conn_w = psycopg2.connect(url); conn_w.autocommit = False
        try:
            with conn_w.cursor() as cur:
                cur.execute("SET TRANSACTION READ WRITE")
                cur.execute("SET LOCAL statement_timeout='10min'")
                cur.execute("CREATE TEMP TABLE _reanchor "
                            "(faerslunumer bigint, fastnum bigint, kaupverd_real bigint) "
                            "ON COMMIT DROP")
                execute_values(cur,
                    "INSERT INTO _reanchor (faerslunumer, fastnum, kaupverd_real) VALUES %s",
                    upd_rows, page_size=5000)
                t0 = time.time()
                cur.execute(
                    "UPDATE public.sales_history s SET kaupverd_real = d.kaupverd_real "
                    "FROM _reanchor d "
                    "WHERE s.faerslunumer = d.faerslunumer AND s.fastnum = d.fastnum")
                updated = cur.rowcount
                elapsed = time.time() - t0
            conn_w.rollback()  # NOTHING committed
            verdict = "OK (vel innan 10min borðs)" if elapsed < 120 else \
                      "ENDURMETA — nálægt/yfir 2min; íhuga lotuskiptingu (Leið 2)"
            log(f"[5a] DRYRUN: UPDATE myndi snerta {updated:,} raðir á {elapsed:.1f}s "
                f"(rúllað til baka, ekkert committað). statement_timeout=10min; "
                f"raunmæling {elapsed:.1f}s -> {verdict}")
        except Exception as e:
            conn_w.rollback()
            log(f"[5a] DRYRUN ERROR (rolled back): {type(e).__name__}: {e}")
            conn_w.close()
            return 1
        conn_w.close()
        log("[5a] DRYRUN complete — anchor ÓBREYTTUR, engin skrif, enginn REFRESH.")
        return 0

    # ---- Step 5b: LIVE — one atomic txn (all or nothing) ----
    cpi_upserts = csv_rows_at_or_after(cur_anchor)  # any months from old anchor forward
    url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    conn_w = psycopg2.connect(url); conn_w.autocommit = False
    updated = 0; t0 = time.time()
    try:
        with conn_w.cursor() as cur:
            cur.execute("SET TRANSACTION READ WRITE")
            cur.execute("SET LOCAL statement_timeout='10min'")
            cur.execute("CREATE TEMP TABLE _reanchor "
                        "(faerslunumer bigint, fastnum bigint, kaupverd_real bigint) "
                        "ON COMMIT DROP")
            execute_values(cur,
                "INSERT INTO _reanchor (faerslunumer, fastnum, kaupverd_real) VALUES %s",
                upd_rows, page_size=5000)
            cur.execute(
                "UPDATE public.sales_history s SET kaupverd_real = d.kaupverd_real "
                "FROM _reanchor d "
                "WHERE s.faerslunumer = d.faerslunumer AND s.fastnum = d.fastnum")
            updated = cur.rowcount
            cur.execute(
                "UPDATE public.pipeline_config SET value=%s, updated_at=now() "
                "WHERE key=%s", (new_anchor, LIVE_ANCHOR_KEY))
            execute_values(cur,
                "INSERT INTO public.cpi_index (year_month, cpi) VALUES %s "
                "ON CONFLICT (year_month) DO UPDATE SET cpi=EXCLUDED.cpi",
                cpi_upserts, page_size=1000)
        conn_w.commit()  # anchor + real + cpi_index synced atomically
        elapsed = time.time() - t0
        log(f"[5b] LIVE committed: updated={updated:,} real, anchor {cur_anchor}->{new_anchor}, "
            f"cpi_index upserts={len(cpi_upserts)}, {elapsed:.1f}s")
    except Exception as e:
        conn_w.rollback()
        log(f"[5b] LIVE ERROR rolled back (anchor unchanged): {type(e).__name__}: {e}")
        conn_w.close()
        return 1
    conn_w.close()

    # ---- Step 6: REFRESH 13 MV (iff updated > 0) ----
    if updated > 0:
        conn_r = psycopg2.connect(url); conn_r.autocommit = True
        with conn_r.cursor() as cur:
            cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE")
            for mv in MV_LIST:
                cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}")
                log(f"[6] refreshed {mv}")
        conn_r.close()
    else:
        log("[6] 0 updated — sleppi REFRESH.")

    log(f"[7] done. anchor {cur_anchor}->{new_anchor}, rows_changed={n_changed:,}, "
        f"updated={updated:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
