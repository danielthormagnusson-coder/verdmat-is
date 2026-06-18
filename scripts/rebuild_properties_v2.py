"""rebuild_properties_v2.py — multi-source stitch to reconcile properties_v2.pkl
with the post-D3 Supabase universe (124,835 → 232,887 rows).

WHY this exists
---------------
Phase D3 (2026-05-27) inserted 108,052 net-new properties DIRECTLY into Supabase
`public.properties` via phase_d3_apply, but the local `properties_v2.pkl` (the
input layer for build_training_data / geography / repeat_sale / ats /
rebuild_predictions_iter4 / build_precompute) was never updated. So the precompute
pipeline is 108K rows behind the live universe — run id=7's push-preview showed
properties csv 124,835 vs live 232,887. This script closes that gap so the next
cascade + run_monthly cycle produces a precompute that matches live (push-preview
deltas → ≈0).

WHY a multi-source STITCH (not a simple Supabase export)
--------------------------------------------------------
Neither single source has the full pkl shape for all 232,887 rows (Skref 10b/10c +
Skref 11 Phase A parser audit):
  - The pkl's RAW HMS columns (merking, heinum, landnr, tegund, einflm,
    fasteignamat, brunabotamat, postnr, heimilisfang) live in
    audit/hms_archive_staging.db for the D3 rows — the HMS payload carries them.
    Supabase does NOT store raw `merking` (only the derived unit_category[:4]),
    so a pure Supabase export would lose the load-bearing floor-feature input.
  - The pkl's DERIVED/LOOKED-UP columns (postheiti, hnitWGS84_N/E, matsvaediNUMER)
    are NOT in the HMS payload — the parser audit confirmed phase_d3_extract
    sourced postheiti + lat/lng from Stadfangaskra and matsvaediNUMER from a
    spatial-NN k=1 KDTree, then stored them in Supabase. So for D3 rows these come
    from Supabase (canonical per SOURCES_OF_TRUTH 2026-05-20; ACK Skref 11 Phase A).

So the stitch is:
  existing 124,835 pkl rows (unchanged)
  + 108,052 D3 rows: 11 raw cols from HMS staging + 4 cols from Supabase
    (postheiti, lat→hnitWGS84_N, lng→hnitWGS84_E, matsvaedi_numer→matsvaediNUMER)
    + matsvaediNAFN derived from the baseline numer↔nafn map (flag-1b)
    + byggar=null + source_db literal + scraped_at from staging fetched_at

WHY specific column decisions
-----------------------------
  - matsvaediNAFN derived from baseline numer↔nafn map: phase_d3_extract stored
    only matsvaedi_numer in Supabase (matsvaedi_nafn was left NULL). To restore the
    column's parity with baseline (100% non-null there), we map each D3
    matsvaediNUMER to its name via the baseline pkl's own numer→nafn mode mapping.
    Multi-valued numer→nafn in baseline → mode + warning. D3 numer not in the
    baseline map → leave NULL + log count.
  - byggar kept NULL: the baseline pkl's byggar is 100% NULL by design — it is
    sourced downstream (kaupskra BYGGAR per-sale / listings), NOT from this layer.
    Keeping D3 byggar NULL preserves that intentional contract. (Supabase byggar IS
    populated for D3 from HMS, but that path feeds the serving layer, not this pkl.)
  - ~26% flatarmal NULL + ~2.5% matsvaediNUMER NULL acceptable downstream: HMS
    einflm has a ~26% gap (Skref 10c); LightGBM handles NaN natively in
    build_training_data. matsvaediNUMER is NULL only for the ~5,843 coordless D3
    rows (the rest, incl. scoring-held-unconfident rows, carry their spatial-NN
    value in Supabase). geography.build_matsvaedi_bucket already has an "unknown"
    fallback for NULL matsvaedi — null-tolerance to be verified read-only in the
    Skref 12 cascade prelude before geography rebuild.

Source references: Skref 10c verification (landnum≡landeign_nr 100%, merking 0/10
null, 108,052/108,052 staging coverage, Supabase Pro 991MB/8GB) + Skref 11 Phase A
parser audit (this file's mapping table).

SAFETY: --dry-run is the DEFAULT. Writing requires explicit --apply. Atomic write
(temp + rename), prev-pkl backup, fail-loud pre-write verifications.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
sys.path.insert(0, str(Path(__file__).parent))
from migration_helpers import open_connection  # noqa: E402

PKL = Path(r"D:\properties_v2.pkl")
PKL_BACKUP = Path(r"D:\properties_v2_prev_pre_d3_reconcile.pkl")
PKL_TMP = Path(r"D:\properties_v2.pkl.tmp")
STAGING_DB = Path(r"D:\verdmat-is\app\audit\hms_archive_staging.db")

SOURCE_DB_LITERAL = "d3_hms_recovery_2026-05-27"

# Canonical pkl column order (per Skref 10b audit).
PKL_COLS = [
    "fastnum", "landnum", "heinum", "heimilisfang", "merking", "tegund",
    "flatarmal", "fasteignamat", "fasteignamaT_NAESTA", "brunabotamat",
    "byggar", "postnr", "postheiti", "matsvaediNUMER", "matsvaediNAFN",
    "hnitWGS84_N", "hnitWGS84_E", "source_db", "scraped_at",
]


def coerce_num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def coerce_int(v):
    f = coerce_num(v)
    return None if f is None else int(f)


def coerce_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def extract_d3_raw(staging_db: Path) -> pd.DataFrame:
    """Parse the 11 RAW pkl columns for D3 rows from the HMS staging payload.
    (The 4 lookup/derived cols + matsvaediNAFN are added later from Supabase /
    baseline map — see module docstring for WHY.)"""
    conn = sqlite3.connect(f"file:{staging_db}?mode=ro", uri=True, timeout=30)
    conn.execute("PRAGMA query_only=ON")
    cur = conn.execute(
        "SELECT fastnum, fasteign_data, fetched_at "
        "FROM hms_fasteign WHERE http_status=200 AND phase IN ('A','C')"
    )
    rows = []
    for fastnum, fd, fetched_at in cur:
        try:
            d = json.loads(fd)
        except (json.JSONDecodeError, TypeError):
            continue
        rows.append({
            "fastnum": int(fastnum),
            "landnum": coerce_int(d.get("landnr")),            # ≡ landeign_nr (Skref 10c)
            "heinum": coerce_int(d.get("heinum")),
            "heimilisfang": coerce_str(d.get("heimilisfang")),
            "merking": coerce_str(d.get("merking")),           # load-bearing (floor feats)
            "tegund": coerce_str(d.get("notkun_texti")),       # fine HMS tegund
            "flatarmal": coerce_num(d.get("einflm")),          # ~26% null OK
            "fasteignamat": coerce_int(d.get("fasteignamat")),
            "fasteignamaT_NAESTA": coerce_num(d.get("fasteignamat_naesta_ar")),
            "brunabotamat": coerce_int(d.get("brunabotamat")),
            "byggar": None,                                    # intentional null (downstream-sourced)
            "postnr": coerce_int(d.get("postnumer")),
            "source_db": SOURCE_DB_LITERAL,
            "scraped_at": fetched_at,
        })
    conn.close()
    return pd.DataFrame(rows)


def fetch_supabase_lookup(fastnums: list[int]) -> pd.DataFrame:
    """Pull the 4 lookup/derived cols for D3 rows from Supabase (canonical).
    postheiti + lat/lng + matsvaedi_numer were computed by phase_d3 (Stadfangaskra
    + spatial-NN) and stored in public.properties — the HMS payload lacks them."""
    conn = open_connection()
    out = []
    CH = 10000
    with conn.cursor() as curs:
        for i in range(0, len(fastnums), CH):
            chunk = fastnums[i:i + CH]
            curs.execute(
                "SELECT fastnum, postheiti, lat, lng, matsvaedi_numer "
                "FROM public.properties WHERE fastnum = ANY(%s)",
                (chunk,),
            )
            out.extend(curs.fetchall())
    conn.close()
    return pd.DataFrame(out, columns=[
        "fastnum", "postheiti", "hnitWGS84_N", "hnitWGS84_E", "matsvaediNUMER",
    ])


def build_numer_nafn_map(baseline: pd.DataFrame) -> dict:
    """numer→nafn mode map from baseline (flag-1b). Multi-valued → mode + warn."""
    m = {}
    multi = 0
    g = baseline.dropna(subset=["matsvaediNUMER"]).groupby("matsvaediNUMER")["matsvaediNAFN"]
    for numer, names in g:
        uniq = names.dropna().unique()
        if len(uniq) > 1:
            multi += 1
        mode = names.mode()
        m[int(numer)] = mode.iloc[0] if len(mode) else None
    if multi:
        print(f"  WARN: {multi} matsvaediNUMER have >1 nafn in baseline — used mode")
    return m


def reconcile_dtypes(df: pd.DataFrame, baseline: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Match baseline dtypes per column; widen int64→Int64 for any integer column
    that now carries D3 nulls (documented, downstream-safe — Int64 is nullable int).
    Returns (df, list_of_widenings)."""
    widenings = []
    for col in PKL_COLS:
        base_dt = str(baseline[col].dtype)
        has_null = df[col].isna().any()
        if base_dt == "int64":
            if has_null:
                df[col] = df[col].astype("Int64")          # nullable widening
                widenings.append(f"{col}: int64 → Int64 (D3 nulls present)")
            else:
                df[col] = df[col].astype("int64")
        elif base_dt == "Int64":
            df[col] = df[col].astype("Int64")
        elif base_dt == "float64":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
        elif base_dt.startswith("datetime"):
            # Baseline scraped_at is tz-NAIVE (datetime64[us]); D3 fetched_at are
            # ISO strings WITH tz offset (+00:00). Mixed tz-aware/naive in one
            # column errors — coerce all to UTC then drop tz to match baseline,
            # casting to the baseline unit for exact dtype parity.
            s = pd.to_datetime(df[col], errors="coerce", utc=True).dt.tz_localize(None)
            try:
                df[col] = s.astype(base_dt)
            except (TypeError, ValueError):
                df[col] = s
        else:  # str / object
            df[col] = df[col].astype(object)
    return df, widenings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="Actually write the pkl. Default is dry-run (no write).")
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== rebuild_properties_v2.py ({mode}) ===\n")

    # 1. Load baseline
    baseline = pd.read_pickle(PKL)
    print(f"[1] baseline properties_v2.pkl: {len(baseline):,} rows × {len(baseline.columns)} cols")
    if list(baseline.columns) != PKL_COLS:
        print(f"  WARN: baseline column order differs from expected; using baseline order")

    # 2. Extract D3 raw cols from HMS staging
    d3 = extract_d3_raw(STAGING_DB)
    print(f"[2] D3 raw extract from staging: {len(d3):,} rows")
    crit_null = {c: int(d3[c].isna().sum()) for c in
                 ["merking", "heinum", "landnum", "tegund", "flatarmal",
                  "fasteignamat", "postnr"]}
    print(f"    critical-field null counts: {crit_null}")

    # 3. Supabase lookup join (postheiti, hnit, matsvaediNUMER)
    sup = fetch_supabase_lookup(d3["fastnum"].tolist())
    print(f"[3] Supabase lookup rows: {len(sup):,}")
    d3 = d3.merge(sup, on="fastnum", how="left")
    sup_null = {c: int(d3[c].isna().sum()) for c in
                ["postheiti", "hnitWGS84_N", "hnitWGS84_E", "matsvaediNUMER"]}
    print(f"    post-join null counts: {sup_null}")

    # 3b. matsvaediNAFN from baseline numer→nafn map (flag-1b)
    nmap = build_numer_nafn_map(baseline)
    def map_nafn(numer):
        if pd.isna(numer):
            return None
        return nmap.get(int(numer))
    d3["matsvaediNAFN"] = d3["matsvaediNUMER"].map(map_nafn)
    n_numer = int(d3["matsvaediNUMER"].notna().sum())
    n_nafn = int(d3["matsvaediNAFN"].notna().sum())
    print(f"    matsvaediNAFN derived: {n_nafn:,}/{n_numer:,} numer mapped "
          f"({n_numer - n_nafn:,} D3 numer absent from baseline map → NULL)")

    # Ensure column order before concat
    d3 = d3[PKL_COLS]

    # 4. Concat
    combined = pd.concat([baseline, d3], ignore_index=True)
    print(f"\n[4] concat → {len(combined):,} rows "
          f"(expected {len(baseline) + len(d3):,})")

    # 5. Pre-write verify (fail loud)
    print(f"\n[5] pre-write verification:")
    ok = True
    dups = int(combined["fastnum"].duplicated().sum())
    print(f"    fastnum duplicates: {dups}  ({'OK' if dups == 0 else 'FAIL'})")
    if dups:
        ok = False
        print(f"      sample dup fastnums: {combined.loc[combined['fastnum'].duplicated(keep=False), 'fastnum'].head(10).tolist()}")
    d3_merking_null = int(d3["merking"].isna().sum())
    print(f"    D3 merking nulls: {d3_merking_null}  "
          f"({'OK' if d3_merking_null == 0 else 'FAIL — load-bearing'})")
    if d3_merking_null:
        ok = False
    mn_null = int(combined["matsvaediNUMER"].isna().sum())
    mn_pct = 100.0 * (len(combined) - mn_null) / len(combined)
    print(f"    matsvaediNUMER null (total): {mn_null:,}  "
          f"→ coverage {mn_pct:.2f}%  (baseline was 100%; ~5,843 coordless expected)")

    combined, widenings = reconcile_dtypes(combined, baseline)
    schema_ok = list(combined.columns) == list(baseline.columns)
    print(f"    schema: {len(combined.columns)} cols, order match baseline: {schema_ok}  "
          f"({'OK' if schema_ok else 'FAIL'})")
    if not schema_ok:
        ok = False
    if widenings:
        print(f"    dtype widenings (int64→Int64 for D3-null integer cols):")
        for w in widenings:
            print(f"      {w}")

    print(f"\n    per-column dtype + total null:")
    for c in PKL_COLS:
        print(f"      {c:<22s} {str(combined[c].dtype):<12s} null={int(combined[c].isna().sum()):>6,}")

    # Memory + size estimate
    mem_mb = combined.memory_usage(deep=True).sum() / 1024 / 1024
    base_size_mb = PKL.stat().st_size / 1024 / 1024
    est_size_mb = base_size_mb * len(combined) / len(baseline)
    print(f"\n    in-memory footprint: {mem_mb:.1f} MB")
    print(f"    pkl size estimate: ~{est_size_mb:.0f} MB "
          f"(baseline {base_size_mb:.0f} MB × {len(combined)/len(baseline):.2f})")

    # Sample 5 D3 rows
    print(f"\n    sample 5 D3 rows (post-stitch):")
    d3_fns = set(d3["fastnum"])
    samp = combined[combined["fastnum"].isin(d3_fns)].head(5)
    for _, r in samp.iterrows():
        print(f"      fn={r['fastnum']} merking={r['merking']!r} heinum={r['heinum']} "
              f"landnum={r['landnum']} tegund={r['tegund']!r} "
              f"matsv={r['matsvaediNUMER']} nafn={r['matsvaediNAFN']!r} "
              f"postheiti={r['postheiti']!r} hnit=({r['hnitWGS84_N']},{r['hnitWGS84_E']})")

    if not ok:
        print(f"\n*** VERIFY FAILED — would NOT write even with --apply. ***")
        return 3

    if not args.apply:
        print(f"\n*** DRY-RUN complete. No pkl written. Re-run with --apply to write. ***")
        return 0

    # 6-7. Backup + atomic write
    print(f"\n[6] backup current pkl → {PKL_BACKUP.name}")
    import shutil
    shutil.copy2(PKL, PKL_BACKUP)
    print(f"    backed up ({PKL_BACKUP.stat().st_size/1024/1024:.0f} MB)")
    print(f"[7] atomic write → {PKL.name}")
    combined.to_pickle(PKL_TMP)
    PKL_TMP.replace(PKL)
    print(f"    written ({PKL.stat().st_size/1024/1024:.0f} MB)")

    # 8. Post-write verify
    print(f"\n[8] post-write load test:")
    reloaded = pd.read_pickle(PKL)
    print(f"    reloaded: {len(reloaded):,} rows × {len(reloaded.columns)} cols")
    print(f"    sample 5 D3 rows from disk:")
    for _, r in reloaded[reloaded["fastnum"].isin(d3_fns)].head(5).iterrows():
        print(f"      fn={r['fastnum']} merking={r['merking']!r} matsv={r['matsvaediNUMER']}")
    print(f"\n*** APPLY complete. properties_v2.pkl reconciled to {len(reloaded):,} rows. ***")
    return 0


if __name__ == "__main__":
    sys.exit(main())
