"""rebuild_sales_history.py — KAUPSKRÁ FIX Skref 1: clean rebuild + DRYRUN.

Re-derives the FULL sales_history rowset from D:\\kaupskra.csv using EXACTLY the
transforms of phase_d3_sales_extract.py, with three locked design changes:

  1. FAERSLUNUMER carried through  -> composite natural key (faerslunumer, fastnum).
  2. fastnum-universe = fastnums that EXIST in public.properties (FK guard).
  3. cpi_factor from D:\\cpi_verdtrygging.csv ONLY, anchor PINNED to '2026-07'
     (NOT max): cpi_factor(ym) = cpi['2026-07'] / cpi[ym];
     kaupverd_real = kaupverd_nominal * cpi_factor.  No training_data_v2.pkl.

The derive core (load_cpi_lookup + derive_sales_rows) is factored so the future
daily loader reuses it verbatim.

This script:
  - Step 0: runs D:\\refresh_kaupskra.py first (Gat A local fetch; idempotent).
  - Step 1: re-derives the rowset.
  - Step 2: writes a STAGING parquet (D:\\rebuild_sales_history_staging.parquet).
  - DRYRUN: read-only comparison against the live public.sales_history.

NO writes to public.sales_history. NO migration. NO git. The DB connection is
opened READ ONLY and only SELECTs are issued.

Apply (ADD faerslunumer + TRUNCATE RESTART IDENTITY + reinsert + UNIQUE INDEX
(faerslunumer, fastnum) + REFRESH 13 MV + rollback SQL) is a SEPARATE later step,
after this dryrun is approved.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from anchor_config import read_anchor  # noqa: E402  single source of truth for CPI anchor

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

# ---- Paths / constants ----
REFRESH_KAUPSKRA = Path(r"D:\refresh_kaupskra.py")
KAUPSKRA_CSV = Path(r"D:\kaupskra.csv")
CPI_CSV = Path(r"D:\cpi_verdtrygging.csv")
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
OUT_PARQUET = Path(r"D:\rebuild_sales_history_staging.parquet")

# CPI anchor month is NOT hard-coded here — it lives in public.pipeline_config
# and is read via anchor_config.read_anchor(conn). Single source of truth shared
# with the daily loader; no silent fallback.
CURRENT_LIVE_ROWS = 173_867    # for the delta line
CATCHUP_AFTER = pd.Timestamp("2026-04-17")  # live MAX(thinglystdags) at build time


# ======================================================================
# Reusable derive core (daily loader reuses these two functions verbatim)
# ======================================================================
def load_cpi_lookup(cpi_csv: Path, anchor_ym: str) -> dict[str, float]:
    """Build {'YYYY-MM' -> cpi_factor} from cpi_verdtrygging.csv.

    cpi_factor(ym) = vnv[anchor_ym] / vnv[ym]. Anchor is PINNED (param), never max.
    Raises if the anchor month is absent from the CSV.
    """
    ym2vnv: dict[str, float] = {}
    with open(cpi_csv, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            ym2vnv[r["year_month"]] = float(r["cpi"])
    if anchor_ym not in ym2vnv:
        raise SystemExit(f"ANCHOR {anchor_ym} not in {cpi_csv} "
                         f"(latest available: {max(ym2vnv)})")
    anchor_vnv = ym2vnv[anchor_ym]
    return {ym: anchor_vnv / vnv for ym, vnv in ym2vnv.items() if vnv}


def derive_sales_rows(
    kp: pd.DataFrame,
    valid_fastnums: set[int],
    cpi_factor_by_ym: dict[str, float],
) -> tuple[pd.DataFrame, dict]:
    """Re-derive sales_history rows (sans id, plus faerslunumer) from kaupskra.

    Transforms identical to phase_d3_sales_extract.py except FAERSLUNUMER is
    carried, the fastnum-universe is the live properties set, and cpi_factor is
    the pinned-anchor lookup. Returns (out_df, stats).
    """
    stats: dict = {}
    n_raw = len(kp)

    kp = kp.copy()
    kp["FASTNUM_i"] = pd.to_numeric(kp["FASTNUM"], errors="coerce").astype("Int64")
    kp = kp.dropna(subset=["FASTNUM_i"])
    kp["FASTNUM_i"] = kp["FASTNUM_i"].astype("int64")
    stats["rows_with_fastnum"] = len(kp)

    # FK guard: keep only fastnums that exist in public.properties
    in_universe = kp["FASTNUM_i"].isin(valid_fastnums)
    fk_dropped = kp[~in_universe]
    stats["fk_dropped_rows"] = int(len(fk_dropped))
    stats["fk_dropped_distinct_fastnums"] = int(fk_dropped["FASTNUM_i"].nunique())
    kp = kp[in_universe].copy()
    stats["rows_in_universe"] = len(kp)

    # Dates + numerics
    kp["thinglystdags"] = pd.to_datetime(kp["THINGLYSTDAGS"], errors="coerce",
                                         format="ISO8601")
    kp = kp.dropna(subset=["thinglystdags"]).copy()
    kp["KAUPVERD"] = pd.to_numeric(kp["KAUPVERD"], errors="coerce")
    kp["EINFLM"] = pd.to_numeric(kp["EINFLM"], errors="coerce")
    kp["BYGGAR"] = pd.to_numeric(kp["BYGGAR"], errors="coerce")
    kp["ONOTHAEFUR_SAMNINGUR"] = pd.to_numeric(
        kp["ONOTHAEFUR_SAMNINGUR"], errors="coerce").fillna(0).astype(int)
    kp["faerslunumer"] = pd.to_numeric(kp["FAERSLUNUMER"], errors="coerce").astype("Int64")

    # cpi_factor via pinned-anchor lookup keyed on 'YYYY-MM'
    ym = kp["thinglystdags"].dt.strftime("%Y-%m")
    kp["cpi_factor"] = ym.map(cpi_factor_by_ym)
    stats["rows_without_cpi"] = int(kp["cpi_factor"].isna().sum())

    nominal = (kp["KAUPVERD"] * 1000).round().astype("Int64")
    real = (nominal.astype("float") * kp["cpi_factor"]).round().astype("Int64")

    out = pd.DataFrame({
        "faerslunumer": kp["faerslunumer"].values,
        "fastnum": kp["FASTNUM_i"].astype("int64").values,
        "thinglystdags": kp["thinglystdags"].dt.date.values,
        "kaupverd_nominal": nominal.values,
        "kaupverd_real": real.values,
        "einflm_at_sale": kp["EINFLM"].values,
        "byggar_at_sale": kp["BYGGAR"].values,
        "onothaefur": kp["ONOTHAEFUR_SAMNINGUR"].astype("int16").values,
    })

    # Drop rows with missing / non-positive nominal price
    before = len(out)
    out = out[out["kaupverd_nominal"].notna() & (out["kaupverd_nominal"] > 0)]
    stats["dropped_zero_nominal"] = int(before - len(out))
    stats["final_rows"] = len(out)
    stats["n_raw"] = n_raw
    return out.reset_index(drop=True), stats


# ======================================================================
# DB helpers (READ ONLY)
# ======================================================================
def open_ro_conn():
    import psycopg2
    url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def fetch_valid_fastnums(conn) -> set[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT fastnum FROM public.properties")
        return {int(r[0]) for r in cur.fetchall()}


# ======================================================================
# Step 0 — refresh_kaupskra
# ======================================================================
def run_refresh_kaupskra() -> str:
    print("=" * 70)
    print("[0] D:\\refresh_kaupskra.py (Gat A — local fetch, idempotent)")
    print("=" * 70)
    if not REFRESH_KAUPSKRA.exists():
        print(f"  WARN: {REFRESH_KAUPSKRA} missing — skipping fetch, using csv on disk")
        return "missing"
    res = subprocess.run([sys.executable, str(REFRESH_KAUPSKRA)],
                         capture_output=True, text=True, timeout=900)
    out = (res.stdout or "") + (res.stderr or "")
    print(out.rstrip())
    low = out.lower()
    if "no-op" in low or "no update" in low or "unchanged" in low:
        print("  >> NO-OP: kaupskra.csv unchanged since last fetch (flagged).")
        return "noop"
    if "done." in low:
        print("  >> kaupskra.csv refreshed.")
        return "updated"
    print(f"  >> refresh_kaupskra exit={res.returncode} (review output above).")
    return f"exit{res.returncode}"


# ======================================================================
# main / dryrun
# ======================================================================
def main() -> int:
    fetch_status = run_refresh_kaupskra()

    print("\n" + "=" * 70)
    print("[1] Re-derive full rowset from kaupskra.csv")
    print("=" * 70)
    print("  connecting READ-ONLY to Supabase for properties universe + anchor ...")
    conn = open_ro_conn()
    anchor_ym = read_anchor(conn)  # single source of truth: public.pipeline_config
    cpi_lookup = load_cpi_lookup(CPI_CSV, anchor_ym)
    print(f"  cpi anchor PINNED = {anchor_ym} (from pipeline_config); "
          f"cpi months loaded = {len(cpi_lookup)}")

    print(f"  reading {KAUPSKRA_CSV} ...")
    kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
    print(f"  kaupskra raw rows = {len(kp):,}")

    valid_fastnums = fetch_valid_fastnums(conn)
    print(f"  properties fastnum universe = {len(valid_fastnums):,}")

    out, stats = derive_sales_rows(kp, valid_fastnums, cpi_lookup)

    print("\n" + "=" * 70)
    print("[2] Write staging parquet (NO Supabase writes)")
    print("=" * 70)
    out.to_parquet(OUT_PARQUET, index=False)
    print(f"  wrote {OUT_PARQUET} ({OUT_PARQUET.stat().st_size:,} bytes)")
    print(f"  schema: {list(out.columns)}")

    # ---- live comparison numbers (read-only) ----
    with conn.cursor() as cur:
        cur.execute("SELECT count(*), max(thinglystdags), min(thinglystdags) "
                    "FROM public.sales_history")
        live_n, live_max, live_min = cur.fetchone()

    tdays = pd.to_datetime(out["thinglystdags"])
    new_max, new_min = tdays.max(), tdays.min()
    catchup = int((tdays > CATCHUP_AFTER).sum())
    faerslunumer_nonnull_pct = 100.0 * out["faerslunumer"].notna().mean()

    print("\n" + "=" * 70)
    print("DRYRUN REPORT")
    print("=" * 70)
    print(f"  fetch_status:                 {fetch_status}")
    print(f"  raw kaupskra rows:            {stats['n_raw']:,}")
    print(f"  rows with parseable fastnum:  {stats['rows_with_fastnum']:,}")
    print(f"  FK-DROP rows (fastnum not in properties): {stats['fk_dropped_rows']:,} "
          f"({stats['fk_dropped_distinct_fastnums']:,} distinct fastnums)")
    print(f"  rows in universe:             {stats['rows_in_universe']:,}")
    print(f"  dropped zero/neg nominal:     {stats['dropped_zero_nominal']:,}")
    print(f"  rows without cpi_factor:      {stats['rows_without_cpi']:,}")
    print(f"  --")
    print(f"  NEW rowset rows:              {stats['final_rows']:,}")
    print(f"  CURRENT live sales_history:   {live_n:,}  (baseline const {CURRENT_LIVE_ROWS:,})")
    print(f"  delta (new - live):           {stats['final_rows'] - live_n:+,}")
    print(f"  --")
    print(f"  NEW  thinglystdags MIN/MAX:   {new_min.date()}  ..  {new_max.date()}")
    print(f"  LIVE thinglystdags MIN/MAX:   {live_min}  ..  {live_max}")
    print(f"  catch-up rows newer than {CATCHUP_AFTER.date()}: {catchup:,}")
    print(f"  --")
    print(f"  faerslunumer non-null:        {faerslunumer_nonnull_pct:.4f}%  "
          f"(must be 100.0000%)")

    # ---- CPI spot-check ----
    print(f"  --")
    print(f"  CPI spot-check (anchor {anchor_ym}):")
    for ym, expect in (("2006-05", 2.681426), ("2026-05", 1.008846)):
        got = cpi_lookup.get(ym)
        flag = "OK" if got is not None and abs(got - expect) < 1e-6 else "MISMATCH"
        print(f"    {ym}: cpi_factor={got:.6f}  expected={expect:.6f}  [{flag}]")

    # ---- ANCHOR verification: 5 existing rows reproduce identically ----
    print(f"  --")
    print(f"  ANCHOR verification — 5 live rows re-derived (match on fastnum+dags+nominal):")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT fastnum, thinglystdags, kaupverd_nominal, kaupverd_real, onothaefur "
            "FROM public.sales_history "
            "WHERE kaupverd_real IS NOT NULL AND thinglystdags IS NOT NULL "
            "ORDER BY thinglystdags DESC LIMIT 5"
        )
        live_rows = cur.fetchall()

    idx = out.set_index(["fastnum", "thinglystdags", "kaupverd_nominal"])
    all_match = True
    for fn, dags, nom, real_live, ono in live_rows:
        key = (int(fn), dags, int(nom) if nom is not None else None)
        try:
            cand = idx.loc[[key]]
            real_new = int(cand["kaupverd_real"].iloc[0]) if pd.notna(
                cand["kaupverd_real"].iloc[0]) else None
            same = (real_new == (int(real_live) if real_live is not None else None))
            all_match &= bool(same)
            print(f"    fastnum={fn} {dags} nom={int(nom):,} "
                  f"real_live={int(real_live):,} real_new={real_new:,} "
                  f"-> {'SAME' if same else 'DIFF'}")
        except KeyError:
            all_match = False
            print(f"    fastnum={fn} {dags} nom={nom} -> NOT FOUND in new set")
    print(f"  anchor verification: {'ALL SAME (real unchanged)' if all_match else 'DIFFERENCES — review'}")

    conn.close()
    print("\nHALT — staging parquet written, NO sales_history writes, NO migration, NO git.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
