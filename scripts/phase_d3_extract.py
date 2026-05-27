"""Phase D3 STEP 1 — extract INSERT-candidate rows for ~108K net-new fastnums.

Reads audit/hms_archive_staging.db, selects all Phase A + Phase C rows where
http_status=200 (covers both orig and reprobed=recovered buckets). Parses
fasteign_data JSON for each, joins Stadfangaskra.csv for lat/lng/postheiti,
applies classify_property + rules.is_new_build, and writes the result to
D:\\phase_d3_insert_rows.parquet.

No Supabase writes. Read-only intermediate. Re-runnable.

Output columns mirror the public.properties schema (43-col allowlist per
DECISIONS 2026-05-21). Listing-snapshot columns (augl_id_latest etc.) are
left NULL — they populate later when the LATER-lota evalue augl-pass runs.

Coverage note: matsvaediNUMER is NOT in the HMS API payload (it's only in
the evalue.is augl payload, which is why properties_v2.pkl has it). For
the ~108K D3 candidates we set matsvaedi_bucket = 'P{postnr}_other' as the
fallback bucket (existing convention in geography.py for rare matsvæði).
matsvaediNUMER/matsvaediNAFN stay NULL; LATER lota's evalue augl-pass
will backfill.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

# Helpers live in D:\ (Python ops scripts location)
sys.path.insert(0, r"D:\\")
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None

from classify_property import classify_property, segment_family  # noqa: E402
from rules import is_new_build  # noqa: E402
from geography import region_tier  # noqa: E402

STAGING_DB = Path(r"D:\verdmat-is\app\audit\hms_archive_staging.db")
STADFANG_CSV = Path(r"D:\Stadfangaskra.csv")
GEO_PKL = Path(r"D:\geography_features.pkl")
T_FILE = Path(r"D:\phase_d3_matsvaedi_T_deg.txt")
OUT_PARQUET = Path(r"D:\phase_d3_insert_rows.parquet")
OUT_PICKLE_FALLBACK = Path(r"D:\phase_d3_insert_rows.pkl")

# Valuation reference (matches rebuild_predictions_iter4.py)
VALUATION_YEAR = 2026
VALUATION_MONTH = 4

# Matsvæði rare-merge threshold (matches geography.MATSVAEDI_MIN_SALES_2015)
MATSVAEDI_MIN_SALES_2015 = 50


def coerce_numeric(value):
    if value is None or value == "":
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n


def coerce_text(value):
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def coerce_date(value):
    if value is None or value == "":
        return None
    s = str(value).strip()
    if not s:
        return None
    return s[:10]


def pick_primary_matseining(notkunareiningar):
    """Same selection logic as phase_d1_extract: flatten matseiningar
    across all notkunareiningar; prefer 'Aðaleining' label; fallback to
    largest einflm; fallback to first. Returns (primary, all_ms)."""
    all_ms: list[dict] = []
    for nu in notkunareiningar or []:
        for ms in (nu.get("matseiningar") or []):
            all_ms.append(ms)
    if not all_ms:
        return None, []
    for ms in all_ms:
        if (ms.get("merking") or "").strip().lower() == "aðaleining":
            return ms, all_ms

    def einflm_or_neg(ms):
        v = coerce_numeric(ms.get("einflm"))
        return v if v is not None else -1.0

    sorted_by_size = sorted(all_ms, key=einflm_or_neg, reverse=True)
    if einflm_or_neg(sorted_by_size[0]) > 0:
        return sorted_by_size[0], all_ms
    return all_ms[0], all_ms


def derive_unit_category(merking):
    """unit_category = first 4 chars of merking (HMS FEPILOG prefix)."""
    if merking is None:
        return None
    s = str(merking).strip()
    if len(s) < 4:
        return None
    return s[:4]


def derive_is_main_unit(merking):
    """is_main_unit = merking ends in '01' (FEPILOG CC=01 convention)."""
    if merking is None:
        return None
    s = str(merking).strip()
    if len(s) < 2:
        return None
    return s[-2:] == "01"


def load_stadfangaskra_lookup() -> dict:
    """Build (LANDNR, HEINUM) → row dict for lat/lng/postheiti lookup.
    LANDNR + HEINUM uniquely identify a stadfang in Stadfangaskra; HMS
    payload exposes landnr + heinum at top level."""
    sf = pd.read_csv(STADFANG_CSV, low_memory=False)
    sf = sf[["LANDNR", "HEINUM", "POSTNR", "HEITI_NF", "HUSNR",
             "N_HNIT_WGS84", "E_HNIT_WGS84"]].dropna(subset=["LANDNR", "HEINUM"])
    sf["LANDNR"] = pd.to_numeric(sf["LANDNR"], errors="coerce").astype("Int64")
    sf["HEINUM"] = pd.to_numeric(sf["HEINUM"], errors="coerce").astype("Int64")
    sf = sf.dropna(subset=["LANDNR", "HEINUM"])
    lookup: dict = {}
    for r in sf.itertuples(index=False):
        key = (int(r.LANDNR), int(r.HEINUM))
        if key in lookup:
            continue  # first-wins for duplicates
        lookup[key] = {
            "postnr_sf": int(r.POSTNR) if pd.notna(r.POSTNR) else None,
            "postheiti": str(r.HEITI_NF).strip() if pd.notna(r.HEITI_NF) else None,
            "husnr": float(r.HUSNR) if pd.notna(r.HUSNR) else None,
            "lat": float(r.N_HNIT_WGS84) if pd.notna(r.N_HNIT_WGS84) else None,
            "lng": float(r.E_HNIT_WGS84) if pd.notna(r.E_HNIT_WGS84) else None,
        }
    print(f"  loaded Stadfangaskra lookup: {len(lookup):,} (LANDNR, HEINUM) pairs")
    return lookup


def matsvaedi_bucket_for(matsvaedi_numer, postnr, sales_2015,
                          min_sales=MATSVAEDI_MIN_SALES_2015) -> str:
    """Mirrors geography.build_matsvaedi_bucket() row-wise.

    - Big matsvæði (sales_2015 ≥ min_sales) → "M{numer}"
    - Small / unknown matsvæði → "P{postnr}_other"
    - Neither → "unknown"
    """
    if matsvaedi_numer is None or pd.isna(matsvaedi_numer):
        rare = True
    else:
        try:
            m = int(matsvaedi_numer)
            rare = sales_2015.get(m, 0) < min_sales
        except (TypeError, ValueError):
            return "unknown"
    if not rare:
        return f"M{m}"
    if postnr is None or pd.isna(postnr):
        return "unknown"
    try:
        return f"P{int(postnr)}_other"
    except (TypeError, ValueError):
        return "unknown"


def load_matsvaedi_donor() -> tuple[cKDTree, np.ndarray, dict, float]:
    """Build the k=1 spatial-NN backfill structure.

    Returns:
        tree: cKDTree on labeled (lat, lon) points
        matsvaedi_array: matsvaediNUMER for each tree row (parallel)
        sales_2015: matsvaediNUMER → sales count (for bucket rare-merge)
        T_deg: confidence threshold (degrees)
    """
    geo = pd.read_pickle(GEO_PKL)
    geo = geo.dropna(subset=["lat", "lon", "matsvaediNUMER"]).copy().reset_index(drop=True)
    tree = cKDTree(geo[["lat", "lon"]].to_numpy())
    matsvaedi_array = geo["matsvaediNUMER"].to_numpy()
    sales_2015 = geo.groupby("matsvaediNUMER")["matsvaedi_sales_2015"].first().to_dict()
    if T_FILE.exists():
        T_deg = float(T_FILE.read_text(encoding="utf-8").strip())
    else:
        # Fallback if calibration hasn't been run — conservative 1 km
        T_deg = 0.009
    print(f"  donor: {len(geo):,} labeled points; "
          f"distinct matsvæði: {len(sales_2015):,}; "
          f"T = {T_deg:.5f}° (~{T_deg * 111:.2f} km)")
    return tree, matsvaedi_array, sales_2015, T_deg


def extract_one(payload: dict, fastnum: int, sf_lookup: dict) -> dict:
    """Map one HMS fasteign_data dict + Stadfangaskra row → properties INSERT row."""
    # Identity
    heimilisfang = coerce_text(payload.get("heimilisfang"))
    postnr = payload.get("postnumer")
    try:
        postnr_int = int(postnr) if postnr is not None and str(postnr).strip() else None
    except (TypeError, ValueError):
        postnr_int = None
    sveitarfelag = coerce_text(payload.get("sveitarfelag_nafn") or payload.get("sveitarfelag"))
    svfn = payload.get("sveitarfelag_nr")
    try:
        svfn_num = float(svfn) if svfn is not None and str(svfn).strip() else None
    except (TypeError, ValueError):
        svfn_num = None

    # Stadfangaskra lookup via (landnr, heinum)
    landnr = payload.get("landnr") or payload.get("landeign_nr")
    heinum = payload.get("heinum")
    try:
        landnr_i = int(landnr) if landnr is not None else None
        heinum_i = int(heinum) if heinum is not None else None
    except (TypeError, ValueError):
        landnr_i = heinum_i = None
    sf_row = sf_lookup.get((landnr_i, heinum_i)) if landnr_i and heinum_i else None

    lat = sf_row["lat"] if sf_row else None
    lng = sf_row["lng"] if sf_row else None
    postheiti = sf_row["postheiti"] if sf_row else None
    husnr = sf_row["husnr"] if sf_row else None
    if postnr_int is None and sf_row and sf_row.get("postnr_sf"):
        postnr_int = sf_row["postnr_sf"]

    # tegund_raw + classification
    tegund_raw = coerce_text(payload.get("notkun_texti"))
    canonical_code, _flags = classify_property(tegund_raw)
    fam = segment_family(canonical_code)
    is_residential = fam in ("main", "secondary")
    is_summerhouse = canonical_code == "SUMMERHOUSE"

    # Primary matseining → byggar, fullbuid, byggingarstig, skodags, gerd, matsstig
    primary, all_ms = pick_primary_matseining(payload.get("notkunareiningar") or [])
    if primary:
        byggar = coerce_numeric(primary.get("byggingarar"))
        fullbuid = coerce_numeric(primary.get("fullbuid"))
        byggingarstig = coerce_text(primary.get("byggingarstig"))
        skodags = coerce_date(primary.get("skodags"))
        gerd_raw = primary.get("gerd")
        gerd = str(gerd_raw).strip() if gerd_raw is not None else None
        if gerd == "":
            gerd = None
        matsstig = coerce_text(primary.get("matsstig"))
        # fjherb may live in matseining
        fjherb = coerce_numeric(primary.get("fjherbergja") or primary.get("fjherb"))
    else:
        byggar = fullbuid = None
        byggingarstig = skodags = gerd = matsstig = fjherb = None

    # merking → unit_category + is_main_unit
    merking = coerce_text(payload.get("merking"))
    unit_category = derive_unit_category(merking)
    is_main_unit = derive_is_main_unit(merking)

    # is_new_build — using valuation-year as proxy "sale year" for INSERT scoring
    # rules.is_new_build(fullbuid, byggar, thinglystdags). For D3 we proxy
    # thinglystdags with valuation_year=2026 since these are not actual sales.
    in_b = is_new_build(fullbuid, byggar, f"{VALUATION_YEAR}-{VALUATION_MONTH:02d}-01")

    # Region tier (matsvaedi backfilled post-pass)
    rt = region_tier(postnr_int)

    # HMS valuation metadata (top-level)
    fasteignamat = coerce_numeric(payload.get("fasteignamat"))
    fasteignamat_gildandi = coerce_numeric(payload.get("fasteignamat_nuverandi"))
    brunabotamat = coerce_numeric(payload.get("brunabotamat"))
    lhlmat_raw = coerce_numeric(payload.get("lhlmat"))
    fasteignamat_naesta_ar = coerce_numeric(payload.get("fasteignamat_naesta_ar"))
    # lhlmat → ratio 0..1 (same convention as phase_d1)
    if lhlmat_raw is not None and fasteignamat and fasteignamat > 0:
        lhlmat = lhlmat_raw / fasteignamat
    else:
        lhlmat = None

    landeign_nr = coerce_text(payload.get("landeign_nr"))

    # JSONB columns — serialize to strings for parquet
    matseiningar_json = json.dumps(all_ms, ensure_ascii=False) if all_ms else None
    tengd = payload.get("tengd_stadfang_nr")
    tengd_json = json.dumps(tengd, ensure_ascii=False) if tengd else None

    # Top-level size
    einflm = coerce_numeric(payload.get("einflm"))
    lod_flm = coerce_numeric(payload.get("land_einflm"))

    return {
        # identity
        "fastnum": fastnum,
        "heimilisfang": heimilisfang,
        "husnr": husnr,
        "postnr": postnr_int,
        "postheiti": postheiti,
        "svfn": svfn_num,
        "sveitarfelag": sveitarfelag,
        # classification
        "tegund_raw": tegund_raw,
        "canonical_code": canonical_code,
        "unit_category": unit_category,
        "unit_family": fam if fam != "exclude" else None,
        "is_residential": is_residential,
        "is_summerhouse": is_summerhouse,
        "is_new_build": bool(in_b) if in_b is not None else None,
        "is_main_unit": is_main_unit,
        # size
        "einflm": einflm,
        "lod_flm": lod_flm,
        "byggar": byggar,
        "fjherb": fjherb,
        "fullbuid": fullbuid,
        # geo (matsvaedi_numer + bucket + nn_distance + confident filled in post-pass)
        "lat": lat,
        "lng": lng,
        "matsvaedi_numer": None,
        "matsvaedi_nafn": None,            # not backfilled — would need a numer→name map
        "matsvaedi_bucket": None,
        "nn_distance_km": None,
        "matsvaedi_confident": False,
        "region_tier": rt,
        # HMS valuation
        "fasteignamat": fasteignamat,
        "fasteignamat_gildandi": fasteignamat_gildandi,
        "brunabotamat": brunabotamat,
        "lhlmat": lhlmat,
        "fasteignamat_naesta_ar": fasteignamat_naesta_ar,
        "byggingarstig": byggingarstig,
        "skodags": skodags,
        "gerd": gerd,
        "matsstig": matsstig,
        "landeign_nr": landeign_nr,
        "matseiningar_json": matseiningar_json,
        "tengd_stadfang_nr_json": tengd_json,
        # listing snapshot — NULL, populated by LATER lota
        # listing columns omitted; INSERT sets them to default NULL
        # default
        "deregistered": False,
    }


def main() -> int:
    if not STAGING_DB.exists():
        print(f"ERROR: staging DB not found at {STAGING_DB}")
        return 2

    print(f"Loading Stadfangaskra.csv lookup ...")
    sf_lookup = load_stadfangaskra_lookup()

    print(f"\nReading staging DB rows ...")
    conn = sqlite3.connect(f"file:{STAGING_DB}?mode=ro", uri=True, timeout=30)
    conn.execute("PRAGMA query_only=ON")
    # Phase A 200 (kaupskrá-only + wide-gap candidates that hit HMS-200) +
    # Phase C 200 (orig + reprobed=recovered) — all net-new HMS-200 not in
    # Supabase at scrape time. Phase B 200 (124,738) is the already-enriched
    # baseline — explicitly EXCLUDED.
    cur = conn.execute(
        "SELECT fastnum, fasteign_data, phase, reprobed_at "
        "FROM hms_fasteign "
        "WHERE http_status=200 AND phase IN ('A','C')"
    )

    rows_out = []
    bucket_counts = {"A_orig": 0, "C_orig": 0, "C_recovered": 0}
    json_failures = 0
    matched_sf = 0
    for fastnum, fasteign_data, phase, reprobed_at in cur:
        if phase == "A":
            bucket_counts["A_orig"] += 1
        elif phase == "C" and reprobed_at is None:
            bucket_counts["C_orig"] += 1
        elif phase == "C" and reprobed_at is not None:
            bucket_counts["C_recovered"] += 1
        try:
            payload = json.loads(fasteign_data)
        except (json.JSONDecodeError, TypeError):
            json_failures += 1
            continue
        if not isinstance(payload, dict):
            json_failures += 1
            continue
        try:
            extracted = extract_one(payload, fastnum, sf_lookup)
        except Exception as e:
            print(f"  WARN extract failure on fastnum={fastnum}: {type(e).__name__}: {e}")
            json_failures += 1
            continue
        if extracted["lat"] is not None:
            matched_sf += 1
        rows_out.append(extracted)
    conn.close()

    df = pd.DataFrame(rows_out)
    print(f"\nBucket counts:")
    for k, v in bucket_counts.items():
        print(f"  {k:<14s} {v:>7,}")
    print(f"  TOTAL          {sum(bucket_counts.values()):>7,}")
    print(f"\nExtracted rows: {len(df):,}")
    print(f"JSON parse failures: {json_failures}")
    print(f"Stadfangaskra lat/lng matched: {matched_sf:,} / {len(df):,} "
          f"({100.0 * matched_sf / max(len(df), 1):.1f}%)")

    # ============================================================
    # Spatial matsvaedi backfill (k=1 NN from geography_features.pkl)
    # ============================================================
    print(f"\nSpatial matsvaedi backfill ...")
    tree, donor_mn, sales_2015, T_deg = load_matsvaedi_donor()

    have_xy = df["lat"].notna() & df["lng"].notna()
    if have_xy.any():
        xy = df.loc[have_xy, ["lat", "lng"]].to_numpy()
        nn_dist, nn_idx = tree.query(xy, k=1)
        inferred_mn = donor_mn[nn_idx]
        df.loc[have_xy, "matsvaedi_numer"] = inferred_mn.astype("float64")
        df.loc[have_xy, "nn_distance_km"] = (nn_dist * 111).astype("float64")
        df.loc[have_xy, "matsvaedi_confident"] = (nn_dist <= T_deg)

    # Recompute matsvaedi_bucket per row using inferred matsvaediNUMER
    # (only if confident; non-confident rows get P{postnr}_other or unknown).
    buckets = []
    for _, r in df.iterrows():
        if r["matsvaedi_confident"]:
            buckets.append(matsvaedi_bucket_for(r["matsvaedi_numer"],
                                                r["postnr"], sales_2015))
        else:
            # Fallback path: no matsvaediNUMER used (treated as unknown)
            buckets.append(matsvaedi_bucket_for(None, r["postnr"], sales_2015))
    df["matsvaedi_bucket"] = buckets

    # Quick breakdown of backfill results
    n = len(df)
    n_with_xy = int(have_xy.sum())
    n_no_xy = n - n_with_xy
    n_confident = int(df["matsvaedi_confident"].sum())
    n_beyond_T = n_with_xy - n_confident
    print(f"  D3 rows total:               {n:,}")
    print(f"  with lat/lng (NN-queried):   {n_with_xy:,}  "
          f"({100.0 * n_with_xy / n:.2f}%)")
    print(f"  no lat/lng (held):           {n_no_xy:,}  "
          f"({100.0 * n_no_xy / n:.2f}%)")
    print(f"  matsvaedi_confident (≤T):    {n_confident:,}  "
          f"({100.0 * n_confident / n:.2f}%)")
    print(f"  beyond T (held):             {n_beyond_T:,}  "
          f"({100.0 * n_beyond_T / n:.2f}%)")
    print(f"  bucket breakdown:")
    for b, c in df["matsvaedi_bucket"].value_counts().head(5).items():
        print(f"    {b:<24s} {c:>7,}")
    print(f"    ... ({df['matsvaedi_bucket'].nunique():,} distinct buckets total)")
    n_M = int(df["matsvaedi_bucket"].str.startswith("M", na=False).sum())
    n_P_other = int(df["matsvaedi_bucket"].str.endswith("_other", na=False).sum())
    n_unknown = int((df["matsvaedi_bucket"] == "unknown").sum())
    print(f"  M<numer>:      {n_M:>7,}  ({100.0 * n_M / n:.1f}%)")
    print(f"  P<postnr>_other: {n_P_other:>5,}  ({100.0 * n_P_other / n:.1f}%)")
    print(f"  unknown:       {n_unknown:>7,}  ({100.0 * n_unknown / n:.1f}%)")

    # Coverage summary
    print("\nNon-null coverage per column:")
    cols = [
        "heimilisfang", "postnr", "postheiti", "lat", "lng",
        "tegund_raw", "canonical_code", "is_residential", "is_summerhouse",
        "einflm", "byggar", "fullbuid",
        "fasteignamat", "brunabotamat", "lhlmat", "fasteignamat_naesta_ar",
        "byggingarstig", "skodags", "gerd", "matsstig",
        "landeign_nr", "matseiningar_json", "unit_category", "is_main_unit",
        "region_tier", "matsvaedi_bucket",
    ]
    n = len(df)
    for c in cols:
        nn = int(df[c].notna().sum())
        pct = 100.0 * nn / n if n else 0
        print(f"  {c:<28s} {nn:>7,} / {n:,}  ({pct:5.1f}%)")

    # canonical_code breakdown
    print("\ncanonical_code breakdown:")
    for code, count in df["canonical_code"].value_counts().items():
        print(f"  {code:<20s} {count:>7,}  ({100.0 * count / n:5.1f}%)")

    # Write parquet (NULL out empty json strings → write proper NULLs)
    try:
        df.to_parquet(OUT_PARQUET, index=False)
        print(f"\nWrote {OUT_PARQUET} ({OUT_PARQUET.stat().st_size:,} bytes)")
    except Exception as e:
        print(f"\nparquet write failed ({type(e).__name__}: {e}); falling back to pickle")
        df.to_pickle(OUT_PICKLE_FALLBACK)
        print(f"Wrote {OUT_PICKLE_FALLBACK} ({OUT_PICKLE_FALLBACK.stat().st_size:,} bytes)")

    print("\nSTEP 1 (properties extract) complete. NO Supabase writes performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
