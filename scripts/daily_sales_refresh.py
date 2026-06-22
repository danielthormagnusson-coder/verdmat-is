"""daily_sales_refresh.py — daily fresh-data path for public.sales_history.

Cadence-separated from the monthly model pipeline (run_monthly.py). This script
ONLY appends genuinely-new (faerslunumer, fastnum) sales rows and refreshes the
13 semantic materialized views. It never re-anchors kaupverd_real, never touches
predictions / feature_attributions / any model output, and never updates or
deletes existing rows (DO NOTHING is locked — kaupskra mutations are negligible
noise the model treats as outliers; we record new, we do not chase reclassification).

Reuses the derive core from rebuild_sales_history.py by import (no re-implementation)
and the single-source CPI anchor from anchor_config.read_anchor (public.pipeline_config).

Flow:
  0. run D:\\refresh_kaupskra.py; gate on content_md5 change (no-op unless --force).
  1. read pinned anchor + CPI lookup + properties universe (read-only).
  2. re-derive the full rowset from kaupskra.csv (identical transforms).
  3. diff vs live on (faerslunumer, fastnum): NEW + GONE (GONE watched, not deleted).
  4. --dryrun: report + examples, no writes.
  5. upsert ONLY the new rows (INSERT ... ON CONFLICT DO NOTHING).
  6. REFRESH 13 MV CONCURRENTLY iff inserted > 0.

CLI:
  python scripts/daily_sales_refresh.py            # live: fetch -> upsert -> refresh
  python scripts/daily_sales_refresh.py --dryrun   # no writes; report what would happen
  python scripts/daily_sales_refresh.py --force     # ignore md5 no-op gate (test/manual)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
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
    REFRESH_KAUPSKRA,
    DBCONFIG,
)
from anchor_config import read_anchor  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(
    sys.stdout, "reconfigure") else None

STATE_JSON = Path(r"D:\kaupskra_fetch_state.json")
LOGFILE = Path(r"D:\daily_sales_refresh.log")

# 13 semantic materialized views (probe SKREF 6). _sales_base is a plain VIEW -> NOT here.
MV_LIST = [
    "semantic.v_street_directory",
    "semantic.v_matsvaedi_prices_yearly",
    "semantic.v_street_prices",
    "semantic.v_postnr_prices_yearly",
    "semantic.v_street_activity",
    "semantic.v_sveitarfelag_market",
    "semantic.v_matsvaedi_trend_quarterly",
    "semantic.v_hood_heat",
    "semantic.v_newbuild_share",
    "semantic.v_model_vs_sold_by_hood",
    "semantic.v_summerhouse_market",
    "semantic.v_price_distribution_by_hood",
    "semantic.v_sveitarfelag_lookup",
]

# INSERT column order (id is auto-generated via nextval -> skipped).
INSERT_COLS = [
    "faerslunumer", "fastnum", "thinglystdags", "kaupverd_nominal",
    "kaupverd_real", "einflm_at_sale", "byggar_at_sale", "onothaefur",
]

GONE_WARN_THRESHOLD = 50


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # logging must never crash the run


def read_md5() -> str | None:
    if not STATE_JSON.exists():
        return None
    try:
        return json.loads(STATE_JSON.read_text(encoding="utf-8")).get("content_md5")
    except Exception:
        return None


def na_to_none(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if v is pd.NA:
        return None
    return v


def keyset(df: pd.DataFrame) -> set[tuple[int, int]]:
    """Set of (faerslunumer, fastnum) over rows with non-null faerslunumer."""
    sub = df[df["faerslunumer"].notna()]
    return set(zip(sub["faerslunumer"].astype("int64"),
                   sub["fastnum"].astype("int64")))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun", action="store_true", help="no writes; report only")
    ap.add_argument("--force", action="store_true", help="ignore md5 no-op gate")
    args = ap.parse_args()

    log(f"=== daily_sales_refresh ({'DRYRUN' if args.dryrun else 'LIVE'}"
        f"{', FORCE' if args.force else ''}) ===")

    # ---- Step 0: refresh_kaupskra + md5 gate ----
    md5_before = read_md5()
    log("[0] running refresh_kaupskra.py ...")
    res = subprocess.run([sys.executable, str(REFRESH_KAUPSKRA)],
                         capture_output=True, text=True, timeout=900)
    if res.returncode != 0:
        log(f"[0] ERROR refresh_kaupskra exit={res.returncode}; "
            f"stderr tail: {(res.stderr or '')[-500:]}")
        return 1
    md5_after = read_md5()
    log(f"[0] md5 before={md5_before} after={md5_after}")
    if md5_before == md5_after and not args.force:
        log("[0] kaupskra unchanged (md5) — no-op. Exiting.")
        return 0
    if md5_before == md5_after and args.force:
        log("[0] kaupskra unchanged (md5) but --force set — continuing.")

    # ---- Step 1: anchor + cpi + universe (read-only) ----
    conn_ro = open_ro_conn()
    anchor_ym = read_anchor(conn_ro)  # raises if missing — free HALT guard
    cpi = load_cpi_lookup(CPI_CSV, anchor_ym)
    log(f"[1] anchor={anchor_ym} (pipeline_config); cpi months={len(cpi)}")
    valid_fastnums = fetch_valid_fastnums(conn_ro)
    log(f"[1] properties universe={len(valid_fastnums):,}")

    # ---- Step 2: re-derive ----
    kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
    log(f"[2] kaupskra raw rows={len(kp):,}")
    derived, stats = derive_sales_rows(kp, valid_fastnums, cpi)
    log(f"[2] derive stats: fk_dropped={stats['fk_dropped_rows']:,} "
        f"({stats['fk_dropped_distinct_fastnums']:,} distinct), "
        f"rows_in_universe={stats['rows_in_universe']:,}, "
        f"dropped_zero_nominal={stats['dropped_zero_nominal']:,}, "
        f"final_rows={stats['final_rows']:,}")
    if stats["rows_without_cpi"] > 0:
        log(f"[2] WARN: {stats['rows_without_cpi']:,} rows without cpi_factor "
            f"(kaupverd_real NULL for those)")

    # ---- Step 3: diff vs live ----
    with conn_ro.cursor() as cur:
        cur.execute("SELECT faerslunumer, fastnum FROM public.sales_history")
        live_keys = {(int(f), int(fn)) for f, fn in cur.fetchall() if f is not None}
    derived_keys = keyset(derived)
    new_keys = derived_keys - live_keys
    gone_keys = live_keys - derived_keys
    log(f"[3] NEW={len(new_keys):,}  GONE={len(gone_keys):,}  "
        f"(live={len(live_keys):,}, derived={len(derived_keys):,})")
    if len(gone_keys) > GONE_WARN_THRESHOLD:
        log(f"[3] WARN: GONE={len(gone_keys):,} exceeds {GONE_WARN_THRESHOLD} — "
            f"rows vanished from kaupskra; no delete in v1, review needed.")

    # rows to insert (new keys only); informational MAX thinglystdags among them
    dk = derived[derived["faerslunumer"].notna()].copy()
    dk["_k"] = list(zip(dk["faerslunumer"].astype("int64"),
                        dk["fastnum"].astype("int64")))
    to_insert = dk[dk["_k"].isin(new_keys)].drop(columns="_k")
    if len(to_insert):
        max_new = pd.to_datetime(to_insert["thinglystdags"]).max()
        log(f"[3] MAX(thinglystdags) among NEW={max_new.date()} "
            f"(info only — late-registered sales carry old dates)")

    # ---- Step 4: dryrun ----
    if args.dryrun:
        log(f"[4] DRYRUN — engin skrif. Myndi setja inn {len(new_keys):,} raðir.")
        for _, r in to_insert.head(10).iterrows():
            log(f"      faerslunumer={int(r['faerslunumer'])} fastnum={int(r['fastnum'])} "
                f"{r['thinglystdags']} nominal={r['kaupverd_nominal']} "
                f"onothaefur={r['onothaefur']}")
        conn_ro.close()
        log("[4] DRYRUN complete — no upsert, no REFRESH.")
        return 0

    # ---- Step 5: live upsert (new rows only) ----
    import psycopg2
    from psycopg2.extras import execute_values
    inserted = 0
    if len(to_insert) == 0:
        log("[5] 0 new rows — nothing to insert.")
    else:
        rows = [tuple(na_to_none(r[c]) for c in INSERT_COLS)
                for _, r in to_insert.iterrows()]
        # coerce numpy/pandas scalars to native python for psycopg2
        def py(v):
            if v is None:
                return None
            if hasattr(v, "item"):
                return v.item()
            return v
        rows = [tuple(py(x) for x in row) for row in rows]
        url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
        conn_w = psycopg2.connect(url)
        conn_w.autocommit = False
        try:
            with conn_w.cursor() as cur:
                cur.execute("SET TRANSACTION READ WRITE")  # ALLRA-FYRSTA á ferskri tengingu
                execute_values(
                    cur,
                    f"INSERT INTO public.sales_history "
                    f"({', '.join(INSERT_COLS)}) VALUES %s "
                    f"ON CONFLICT (faerslunumer, fastnum) DO NOTHING",
                    rows,
                )
                inserted = cur.rowcount
            conn_w.commit()
            log(f"[5] inserted={inserted:,} (of {len(new_keys):,} new keys)")
            if inserted != len(new_keys):
                log(f"[5] WARN: inserted {inserted:,} != new_keys {len(new_keys):,} "
                    f"(ON CONFLICT skipped some — unexpected for genuinely-new keys)")
        except Exception as e:
            conn_w.rollback()
            log(f"[5] ERROR upsert rolled back: {type(e).__name__}: {e}")
            conn_w.close()
            conn_ro.close()
            return 1
        conn_w.close()

    # ---- Step 6: REFRESH MV (iff inserted > 0) ----
    if inserted > 0:
        url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
        conn_r = psycopg2.connect(url)
        conn_r.autocommit = True  # REFRESH ... CONCURRENTLY must be outside a txn block
        with conn_r.cursor() as cur:
            cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE")
            for mv in MV_LIST:
                cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}")
                log(f"[6] refreshed {mv}")
        conn_r.close()
    else:
        log("[6] 0 inserted — sleppi REFRESH.")

    # ---- Step 7: final log ----
    with conn_ro.cursor() as cur:
        cur.execute("SELECT max(thinglystdags) FROM public.sales_history")
        live_max = cur.fetchone()[0]
    conn_ro.close()
    log(f"[7] done. md5={md5_after} anchor={anchor_ym} "
        f"fk_dropped={stats['fk_dropped_rows']:,} final_rows={stats['final_rows']:,} "
        f"inserted={inserted:,} GONE={len(gone_keys):,} live_max_thinglystdags={live_max}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
