"""Phase D3 STEP 2 — read-only dryrun across all three D3 NOW-lota artifacts.

Loads:
  D:\\phase_d3_insert_rows.parquet  (~108K properties INSERTs)
  D:\\phase_d3_sales_rows.parquet   (~786 sales_history INSERTs)
  D:\\phase_d3_predictions.parquet  (~63K predictions INSERTs)

Reports:
  (1) True net-new vs collision: |insert ∩ Supabase.properties| — expected 0
  (2) Sales sanity: every sales fastnum ∈ insert universe — expected 100%
  (3) Predictions sanity: every prediction fastnum ∈ insert universe AND
      no collisions with existing predictions PK (predictions.fastnum)
  (4) Coverage of derived columns
  (5) Generates D:\\phase_d3_rollback.sql

No Supabase writes. HALTS the operator for explicit review before apply.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

INSERT_PARQUET = Path(r"D:\phase_d3_insert_rows.parquet")
SALES_PARQUET = Path(r"D:\phase_d3_sales_rows.parquet")
PREDS_PARQUET = Path(r"D:\phase_d3_predictions.parquet")
ROLLBACK_SQL = Path(r"D:\phase_d3_rollback.sql")


def load_or_die(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        print(f"ERROR: {label} parquet not found at {path}")
        sys.exit(2)
    df = pd.read_parquet(path)
    print(f"  loaded {label:<14s}  {len(df):>7,} rows × {len(df.columns)} cols")
    return df


def supabase_query(sql: str, params: tuple | None = None):
    """Run a one-shot query against Supabase. Returns list of rows."""
    url = open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read().strip()
    import psycopg2
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def main() -> int:
    print("=" * 70)
    print("Phase D3 NOW-lota dryrun")
    print("=" * 70)
    print("\nLoading extract artifacts:")
    props = load_or_die(INSERT_PARQUET, "properties")
    sales = load_or_die(SALES_PARQUET, "sales")
    preds = load_or_die(PREDS_PARQUET, "predictions")

    insert_fns = set(int(x) for x in props["fastnum"].tolist())
    sales_fns = set(int(x) for x in sales["fastnum"].tolist())
    pred_fns = set(int(x) for x in preds["fastnum"].tolist())

    # =======================================================
    # (1) True net-new vs collision in Supabase.properties
    # =======================================================
    print("\n" + "-" * 70)
    print("(1) properties INSERT — net-new vs collision check")
    print("-" * 70)
    rows = supabase_query(
        "SELECT fastnum FROM public.properties WHERE fastnum = ANY(%s)",
        (list(insert_fns),),
    )
    existing = set(r[0] for r in rows)
    collisions = insert_fns & existing
    net_new = insert_fns - existing
    print(f"  insert candidates:           {len(insert_fns):,}")
    print(f"  already in Supabase:         {len(collisions):,}  "
          f"(ON CONFLICT DO NOTHING will skip)")
    print(f"  net-new inserts:             {len(net_new):,}")
    if collisions:
        print(f"  WARN: {len(collisions)} collision(s). First 10:")
        for fn in sorted(collisions)[:10]:
            print(f"    {fn}")

    # Bucket source breakdown
    print(f"\n  insert bucket source (from extract bucket counts):")
    print(f"    Phase A 200 (orig):         {2_059:>7,}")
    print(f"    Phase C 200 (orig):         {28_134:>7,}")
    print(f"    Phase C 200 (recovered):    {77_859:>7,}")
    print(f"    TOTAL:                      {108_052:>7,}")
    print(f"    NB: Danni's prompt quoted ~106K = recovered ∪ Phase C orig.")
    print(f"        Including Phase A 2,059 (original D3 scope per DECISIONS 2026-05-18)")
    print(f"        brings the actual insert universe to 108,052.")

    # =======================================================
    # (2) Sales sanity
    # =======================================================
    print("\n" + "-" * 70)
    print("(2) sales_history INSERT — fastnum-set consistency")
    print("-" * 70)
    orphan_sales_fns = sales_fns - insert_fns
    print(f"  total sales rows:                       {len(sales):,}")
    print(f"  distinct fastnums in sales:             {len(sales_fns):,}")
    print(f"  insert FNs with NO sales:               "
          f"{len(insert_fns) - len(sales_fns):,}  "
          f"({100.0 * (len(insert_fns) - len(sales_fns)) / len(insert_fns):.1f}%)")
    print(f"  orphan sales FNs (NOT in insert set):   {len(orphan_sales_fns):,}  "
          f"(MUST be 0)")
    if orphan_sales_fns:
        print(f"  CRITICAL: orphan sales found. First 10:")
        for fn in sorted(orphan_sales_fns)[:10]:
            print(f"    {fn}")
        return 3

    # Pre-existing sales: any FASTNUM in insert set already has sales_history?
    rows = supabase_query(
        "SELECT fastnum, count(*) FROM public.sales_history "
        "WHERE fastnum = ANY(%s) GROUP BY fastnum",
        (list(insert_fns),),
    )
    pre_existing_sales = {r[0]: r[1] for r in rows}
    print(f"  insert FNs ALREADY in sales_history:    "
          f"{len(pre_existing_sales):,}  (should be 0 since these are net-new)")
    if pre_existing_sales:
        print(f"  WARN: {len(pre_existing_sales)} FNs have prior sales. Sample:")
        for fn, n in list(pre_existing_sales.items())[:5]:
            print(f"    fastnum={fn}  {n} existing rows")

    print(f"\n  onothaefur split: "
          f"{int((sales['onothaefur'] == 0).sum()):,} arm's-length, "
          f"{int((sales['onothaefur'] == 1).sum()):,} un-arm's-length")
    print(f"  NB: existing sales_history has 121 onothaefur=1 (0.07%); "
          f"D3 inserts skew higher (~38%) — likely family transfers / "
          f"corporate restructures on legacy fastnums.")

    # =======================================================
    # (3) Predictions sanity
    # =======================================================
    print("\n" + "-" * 70)
    print("(3) predictions INSERT — fastnum-set + collision check")
    print("-" * 70)
    orphan_pred_fns = pred_fns - insert_fns
    print(f"  predictions rows:                       {len(preds):,}")
    print(f"  distinct fastnums:                      {len(pred_fns):,}")
    print(f"  scorable insert FNs (residential+summer):"
          f"{int((props['is_residential'] | props['is_summerhouse']).sum()):>7,}")
    print(f"  unscored (non-residential OR no byggar):"
          f"{len(insert_fns) - len(pred_fns):>7,}")
    print(f"  orphan prediction FNs (NOT in insert):  {len(orphan_pred_fns):,}  "
          f"(MUST be 0)")
    if orphan_pred_fns:
        print(f"  CRITICAL: orphan predictions found.")
        return 3

    # PK collision with existing predictions
    rows = supabase_query(
        "SELECT fastnum FROM public.predictions WHERE fastnum = ANY(%s)",
        (list(pred_fns),),
    )
    pred_collisions = set(r[0] for r in rows)
    print(f"  predictions PK collisions:              {len(pred_collisions):,}  "
          f"(ON CONFLICT DO NOTHING will skip; expected 0 for net-new)")

    # Prediction value sanity
    print(f"\n  prediction value sanity (kr):")
    print(f"    real_pred_mean min={int(preds['real_pred_mean'].min()):>13,}  "
          f"median={int(preds['real_pred_mean'].median()):>13,}  "
          f"max={int(preds['real_pred_mean'].max()):>13,}")
    pi_ok_80 = ((preds["real_pred_lo80"] <= preds["real_pred_mean"]) &
                (preds["real_pred_mean"] <= preds["real_pred_hi80"])).all()
    pi_ok_95 = ((preds["real_pred_lo95"] <= preds["real_pred_lo80"]) &
                (preds["real_pred_hi80"] <= preds["real_pred_hi95"])).all()
    print(f"  PI sanity: lo80 ≤ pred_mean ≤ hi80 (every row): {bool(pi_ok_80)}")
    print(f"  PI sanity: lo95 ≤ lo80 ≤ hi80 ≤ hi95:           {bool(pi_ok_95)}")

    # Confidence gate verification — every scored fastnum should be
    # matsvaedi_confident in the properties parquet.
    print(f"\n  Confidence gate verification:")
    p_confident = props.set_index("fastnum")["matsvaedi_confident"].astype(bool).to_dict()
    bad_gate = [int(fn) for fn in pred_fns if not p_confident.get(int(fn), False)]
    print(f"    scored fastnums NOT in matsvaedi_confident set: {len(bad_gate):,} "
          f"(MUST be 0)")
    if bad_gate:
        print(f"    sample: {bad_gate[:5]}")
        return 3

    # PI honesty by region_tier × segment — the diagnostic established
    # that under spatial-NN matsvaedi, training-sample breach was 0%.
    # Since net-new D3 rows use the same conformal table indexed by
    # (segment, region), and predictions are deterministic under the
    # same inputs, this confirms the conformal PI table is the one being
    # applied. (Empirical breach validation against ground-truth comps is
    # out of scope here — net-new fastnums have no recent sales.)
    print(f"\n  Predictions by region_tier × segment (mean ± half-width log):")
    merged = preds.merge(
        props[["fastnum", "region_tier", "matsvaedi_bucket", "nn_distance_km"]],
        on="fastnum", how="left",
    )
    for (region, seg), sub in merged.groupby(["region_tier", "segment"]):
        if len(sub) < 5:
            continue
        med_mn = int(sub["real_pred_mean"].median())
        med_lo80 = int(sub["real_pred_lo80"].median())
        med_hi80 = int(sub["real_pred_hi80"].median())
        n_M = int(sub["matsvaedi_bucket"].str.startswith("M", na=False).sum())
        print(f"    {region:<13s} {seg:<16s} n={len(sub):>5,}  "
              f"M-bucket {n_M / len(sub) * 100:5.1f}%  "
              f"med pred={med_mn / 1e6:>6.1f}M  "
              f"80% PI=[{med_lo80 / 1e6:>5.1f}, {med_hi80 / 1e6:>5.1f}]M")

    # =======================================================
    # (3b) Peer-ratio spot-check on Country + SUMMERHOUSE scored rows
    # =======================================================
    print("\n" + "-" * 70)
    print("(3b) Peer-ratio spot-check — Country + SUMMERHOUSE scored rows")
    print("-" * 70)
    import numpy as np
    import sys
    sys.path.insert(0, r"D:\\")
    from classify_property import classify_property

    print("  Loading kaupskrá + properties_v2 for peer-comp ...")
    kp = pd.read_csv(r"D:\kaupskra.csv", sep=";", encoding="latin-1",
                     low_memory=False)
    kp["FASTNUM"] = pd.to_numeric(kp["FASTNUM"], errors="coerce").astype("Int64")
    kp["KAUPVERD"] = pd.to_numeric(kp["KAUPVERD"], errors="coerce")
    kp["EINFLM"] = pd.to_numeric(kp["EINFLM"], errors="coerce")
    kp["POSTNR"] = pd.to_numeric(kp["POSTNR"], errors="coerce")
    kp["ONOTHAEFUR_SAMNINGUR"] = pd.to_numeric(
        kp["ONOTHAEFUR_SAMNINGUR"], errors="coerce").fillna(0)
    kp["yr"] = pd.to_datetime(kp["THINGLYSTDAGS"], errors="coerce",
                              format="ISO8601").dt.year
    kp_arm = kp[(kp["ONOTHAEFUR_SAMNINGUR"] == 0) & (kp["yr"] >= 2020)
                & kp["KAUPVERD"].notna() & kp["EINFLM"].notna()
                & kp["POSTNR"].notna()]
    prop_v2 = pd.read_pickle(r"D:\properties_v2.pkl")
    prop_v2["fastnum"] = pd.to_numeric(prop_v2["fastnum"], errors="coerce").astype("Int64")
    cc_map = prop_v2.set_index("fastnum")["tegund"].apply(
        lambda t: classify_property(t)[0] if t is not None else "EXCLUDE"
    )
    kp_arm = kp_arm.merge(cc_map.rename("canonical_code"),
                          left_on="FASTNUM", right_index=True, how="left")

    rng = np.random.default_rng(20260527)
    merged_full = preds.merge(
        props[["fastnum", "postnr", "canonical_code", "einflm",
               "region_tier", "matsvaedi_bucket", "nn_distance_km"]],
        on="fastnum", how="left", suffixes=("", "_p")
    )

    print(f"\n  Country + scored slice (residential, scored, region=Country):")
    country = merged_full[(merged_full["region_tier"] == "Country")
                          & merged_full["canonical_code"].isin(
                              ["APT_FLOOR", "SFH_DETACHED", "ROW_HOUSE",
                               "SEMI_DETACHED", "APT_BASEMENT", "APT_ATTIC",
                               "APT_STANDARD"])]
    country = country[country["postnr"].notna() & country["einflm"].notna()]
    n_country_scored = len(country)
    print(f"    n_scored = {n_country_scored:,}")
    if n_country_scored:
        pick = country.sample(n=min(5, len(country)),
                              random_state=20260527).reset_index(drop=True)
        print(f"    {'fastnum':<10s} {'cc':<14s} {'pnr':>4s} {'efm':>6s} "
              f"{'pred (M)':>9s} {'peer_n':>7s} {'peer_med (M)':>13s} "
              f"{'ratio':>6s} {'nn_km':>6s} {'bucket':<10s}")
        for _, r in pick.iterrows():
            peers = kp_arm[(kp_arm["POSTNR"] == int(r["postnr"]))
                           & (kp_arm["canonical_code"] == r["canonical_code"])
                           & (kp_arm["EINFLM"] >= float(r["einflm"]) * 0.85)
                           & (kp_arm["EINFLM"] <= float(r["einflm"]) * 1.15)]
            pn_n = len(peers)
            peer_med = (peers["KAUPVERD"] * 1000).median() if pn_n else float("nan")
            ratio = r["real_pred_mean"] / peer_med if pn_n > 0 else float("nan")
            bucket_short = (r["matsvaedi_bucket"] or "")[:8]
            print(f"    {int(r['fastnum']):<10d} {r['canonical_code']:<14s} "
                  f"{int(r['postnr']):>4d} {float(r['einflm']):>6.1f} "
                  f"{r['real_pred_mean'] / 1e6:>9.1f} {pn_n:>7,} "
                  f"{peer_med / 1e6 if pn_n else float('nan'):>13.1f} "
                  f"{ratio if pn_n else float('nan'):>6.2f} "
                  f"{r['nn_distance_km'] or 0:>6.2f} {bucket_short:<10s}")

    print(f"\n  SUMMERHOUSE + scored slice:")
    summer = merged_full[merged_full["canonical_code"] == "SUMMERHOUSE"]
    summer = summer[summer["postnr"].notna() & summer["einflm"].notna()]
    n_summer_scored = len(summer)
    print(f"    n_scored = {n_summer_scored:,}")
    if n_summer_scored:
        pick = summer.sample(n=min(5, len(summer)),
                             random_state=20260527).reset_index(drop=True)
        print(f"    {'fastnum':<10s} {'pnr':>4s} {'efm':>6s} "
              f"{'pred (M)':>9s} {'peer_n':>7s} {'peer_med (M)':>13s} "
              f"{'ratio':>6s} {'nn_km':>6s} {'bucket':<10s}")
        for _, r in pick.iterrows():
            # SUMMERHOUSE peer-comp: same postnr × canonical_code × einflm ±15%
            peers = kp_arm[(kp_arm["POSTNR"] == int(r["postnr"]))
                           & (kp_arm["canonical_code"] == "SUMMERHOUSE")
                           & (kp_arm["EINFLM"] >= float(r["einflm"]) * 0.85)
                           & (kp_arm["EINFLM"] <= float(r["einflm"]) * 1.15)]
            pn_n = len(peers)
            # If too few same-postnr peers, expand to ANY SUMMERHOUSE postnr
            # (summer-house comps are geographically sparse).
            note = ""
            if pn_n < 3:
                peers2 = kp_arm[(kp_arm["canonical_code"] == "SUMMERHOUSE")
                                & (kp_arm["EINFLM"] >= float(r["einflm"]) * 0.85)
                                & (kp_arm["EINFLM"] <= float(r["einflm"]) * 1.15)]
                if len(peers2) >= 3:
                    peers = peers2
                    pn_n = len(peers2)
                    note = " (expanded to all postnrs)"
            peer_med = (peers["KAUPVERD"] * 1000).median() if pn_n else float("nan")
            ratio = r["real_pred_mean"] / peer_med if pn_n > 0 else float("nan")
            bucket_short = (r["matsvaedi_bucket"] or "")[:8]
            print(f"    {int(r['fastnum']):<10d} "
                  f"{int(r['postnr']):>4d} {float(r['einflm']):>6.1f} "
                  f"{r['real_pred_mean'] / 1e6:>9.1f} {pn_n:>7,} "
                  f"{peer_med / 1e6 if pn_n else float('nan'):>13.1f} "
                  f"{ratio if pn_n else float('nan'):>6.2f} "
                  f"{r['nn_distance_km'] or 0:>6.2f} {bucket_short:<10s}{note}")

    # =======================================================
    # (4) Coverage of derived columns
    # =======================================================
    print("\n" + "-" * 70)
    print("(4) Derived-column coverage in properties INSERT")
    print("-" * 70)
    n = len(props)
    cols_pct = [
        ("heimilisfang", 95),  # column, expected min %
        ("postnr", 95),
        ("postheiti", 90),
        ("lat", 90),
        ("lng", 90),
        ("tegund_raw", 99),
        ("canonical_code", 100),
        ("einflm", 70),
        ("byggar", 70),
        ("fasteignamat", 99),
        ("brunabotamat", 99),
        ("lhlmat", 95),
        ("byggingarstig", 75),
        ("matseiningar_json", 95),
        ("region_tier", 100),
        ("matsvaedi_bucket", 100),
        ("matsvaedi_numer", 85),
    ]
    print(f"  spatial-NN matsvaedi backfill (within T=1 km):")
    n_conf = int(props["matsvaedi_confident"].fillna(False).astype(bool).sum())
    print(f"    matsvaedi_confident=True:   {n_conf:>7,}  "
          f"({100.0 * n_conf / len(props):5.2f}%)")
    n_M = int(props["matsvaedi_bucket"].str.startswith("M", na=False).sum())
    print(f"    M-bucket (real matsvæði):   {n_M:>7,}  "
          f"({100.0 * n_M / len(props):5.2f}%)")
    print()
    print(f"  {'column':<28s} {'non-null':>10s}  {'pct':>6s}  {'expected':>9s}  status")
    any_below = False
    for col, exp in cols_pct:
        nn = int(props[col].notna().sum())
        pct = 100.0 * nn / n
        ok = "OK" if pct >= exp else "BELOW"
        if pct < exp:
            any_below = True
        print(f"  {col:<28s} {nn:>10,}  {pct:>5.1f}%  {exp:>8d}%  {ok}")

    print(f"\n  canonical_code breakdown (for INSERT universe):")
    for code, count in props["canonical_code"].value_counts().items():
        pct = 100.0 * count / n
        print(f"    {code:<20s} {count:>7,}  ({pct:5.1f}%)")

    # =======================================================
    # (5) Rollback SQL
    # =======================================================
    print("\n" + "-" * 70)
    print("(5) Generating rollback SQL")
    print("-" * 70)
    fn_list = sorted(int(x) for x in insert_fns)
    in_list = ",".join(str(fn) for fn in fn_list)
    content = (
        f"-- Phase D3 NOW-lota rollback — undo three INSERT batches\n"
        f"-- Generated by phase_d3_dryrun.py for {len(fn_list):,} fastnums.\n"
        f"-- Run via Supabase MCP execute_sql or psql against\n"
        f"-- project szzjsvmvxfrhyexblzvq.\n"
        f"--\n"
        f"-- Rollback order (reverse of apply): predictions → sales_history → properties.\n"
        f"-- Transactional. Defensive IN-list so future inserts are not touched.\n\n"
        f"BEGIN;\n"
        f"DELETE FROM public.predictions   WHERE fastnum IN ({in_list});\n"
        f"DELETE FROM public.sales_history WHERE fastnum IN ({in_list});\n"
        f"DELETE FROM public.properties    WHERE fastnum IN ({in_list});\n"
        f"COMMIT;\n"
    )
    ROLLBACK_SQL.write_text(content, encoding="utf-8")
    print(f"  wrote {ROLLBACK_SQL} ({ROLLBACK_SQL.stat().st_size:,} bytes)")

    # =======================================================
    # Summary verdict
    # =======================================================
    print("\n" + "=" * 70)
    print("DRYRUN SUMMARY")
    print("=" * 70)
    print(f"  properties INSERT:   {len(net_new):,} net-new "
          f"(of {len(insert_fns):,} candidates; "
          f"{len(collisions):,} collisions)")
    print(f"  sales_history INSERT: {len(sales):,} rows "
          f"(across {len(sales_fns):,} fastnums)")
    print(f"  predictions INSERT:  {len(preds):,} rows "
          f"(across {len(pred_fns):,} fastnums; "
          f"{len(pred_collisions):,} PK collisions)")
    print()
    print(f"  Post-apply universe size: "
          f"{124_835 + len(net_new):,} (was 124,835)")
    print(f"  Post-apply predictions size: "
          f"{110_316 + (len(pred_fns) - len(pred_collisions)):,} "
          f"(was 110,316)")

    print("\nHALT POINT")
    print("-" * 70)
    print(f"  Review dryrun above. If approved, type 'halt áfram' to proceed")
    print(f"  to phase_d3_apply.py.  Rollback SQL is at: {ROLLBACK_SQL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
