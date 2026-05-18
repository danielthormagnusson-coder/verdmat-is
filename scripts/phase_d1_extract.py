"""Phase D1 STEP 1 — extract enrichment rows from HMS staging DB.

Reads audit/hms_archive_staging.db, parses each phase=B http=200 row's
fasteign_data JSON, extracts the 10 enrichment columns documented in
SUPABASE migration 20260518_hms_columns.sql, and writes the result to
D:\\phase_d1_enrichment.parquet (or .pkl fallback).

No Supabase writes. Read-only intermediate. Re-runnable.

Primary matseining selection rule (from task spec):
    (a) matseining where merking == 'Aðaleining'  — labels not present in
        the HMS payload; falls through to (b).
    (b) matseining with largest einflm (ignoring unit; literal max).
    (c) first matseining if all else fails.

lhlmat semantics: stored in the HMS payload as an absolute thousand-kr
value representing the land portion of the total fasteignamat. The
Supabase column is documented as 0..1 ratio (per the migration COMMENT).
Compute the ratio at extract time: lhlmat_raw / fasteignamat. NULL when
fasteignamat is 0 or NULL.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

STAGING_DB = Path(r"D:\verdmat-is\app\audit\hms_archive_staging.db")
OUT_PARQUET = Path(r"D:\phase_d1_enrichment.parquet")
OUT_PICKLE_FALLBACK = Path(r"D:\phase_d1_enrichment.pkl")


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
    # Truncate "2003-01-15 00:00:00" → "2003-01-15"
    return s[:10]


def pick_primary_matseining(notkunareiningar):
    """Flatten matseiningar across all notkunareiningar, then apply selection
    rules (a)→(b)→(c). Returns (primary_dict, all_matseiningar_list)."""
    all_ms: list[dict] = []
    for nu in notkunareiningar or []:
        for ms in (nu.get("matseiningar") or []):
            all_ms.append(ms)
    if not all_ms:
        return None, []
    # (a) explicit Aðaleining label (defensive — not seen in probes)
    for ms in all_ms:
        if (ms.get("merking") or "").strip().lower() == "aðaleining":
            return ms, all_ms
    # (b) largest einflm
    def einflm_or_neg(ms):
        v = coerce_numeric(ms.get("einflm"))
        return v if v is not None else -1.0
    sorted_by_size = sorted(all_ms, key=einflm_or_neg, reverse=True)
    if einflm_or_neg(sorted_by_size[0]) > 0:
        return sorted_by_size[0], all_ms
    # (c) first
    return all_ms[0], all_ms


def extract_one(row: dict):
    """Return a dict of the 10 enrichment columns plus fastnum, or raise."""
    fn = row["fastnum"]
    fd = row["fasteignamat"]  # top-level fasteignamat (used to compute lhlmat ratio)

    # Top-level numeric
    brunabotamat = coerce_numeric(row.get("brunabotamat"))
    lhlmat_raw = coerce_numeric(row.get("lhlmat"))
    fasteignamat = coerce_numeric(row.get("fasteignamat"))
    fasteignamat_naesta_ar = coerce_numeric(row.get("fasteignamat_naesta_ar"))

    # lhlmat → ratio 0..1
    if lhlmat_raw is not None and fasteignamat and fasteignamat > 0:
        lhlmat = lhlmat_raw / fasteignamat
    else:
        lhlmat = None

    # Top-level text / id
    landeign_nr = coerce_text(row.get("landeign_nr"))

    # tengd_stadfang_nr — preserve as JSON string for parquet/pickle safety
    tengd = row.get("tengd_stadfang_nr")
    tengd_json = json.dumps(tengd, ensure_ascii=False) if tengd else None

    # Primary matseining → byggingarstig, skodags, gerd, matsstig
    primary, all_ms = pick_primary_matseining(row.get("notkunareiningar") or [])
    byggingarstig = coerce_text(primary.get("byggingarstig")) if primary else None
    skodags = coerce_date(primary.get("skodags")) if primary else None
    # gerd is an integer code in the payload (e.g., 3, 7, 0); store as text
    # per migration schema (text column).
    gerd = primary.get("gerd") if primary else None
    if gerd is not None:
        gerd = str(gerd).strip() or None
    matsstig = coerce_text(primary.get("matsstig")) if primary else None

    # matseiningar — preserve full array as JSON string. Each entry already
    # contains its own merking/byggingarstig/skodags/gerd/etc.
    matseiningar_json = json.dumps(all_ms, ensure_ascii=False) if all_ms else None

    return {
        "fastnum": fn,
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
        # extras for dryrun diagnostics — not written via UPDATE in STEP 3
        "_lhlmat_raw": lhlmat_raw,
        "_fasteignamat": fasteignamat,
        "_n_matseiningar": len(all_ms),
    }


def main() -> int:
    if not STAGING_DB.exists():
        print(f"ERROR: staging DB not found at {STAGING_DB}")
        return 2

    print(f"Reading {STAGING_DB} ...")
    conn = sqlite3.connect(f"file:{STAGING_DB}?mode=ro", uri=True, timeout=30)
    conn.execute("PRAGMA query_only=ON")
    cur = conn.execute(
        "SELECT fastnum, fasteign_data FROM hms_fasteign "
        "WHERE phase='B' AND http_status=200"
    )

    rows_out = []
    json_failures = 0
    missing_primary = 0
    for fastnum, fasteign_data in cur:
        try:
            payload = json.loads(fasteign_data)
        except (json.JSONDecodeError, TypeError):
            json_failures += 1
            continue
        if not isinstance(payload, dict):
            json_failures += 1
            continue
        # The staging DB stores `fasteignData` (the inner object) — already
        # the dict we want. The wrapper-level keys ("type","status","data")
        # only appear if a different scrape variant stored the raw response.
        row = dict(payload)
        row["fastnum"] = fastnum  # ensure fastnum column survives
        try:
            extracted = extract_one(row)
        except Exception as e:
            print(f"  WARN extract failure on fastnum={fastnum}: {type(e).__name__}: {e}")
            json_failures += 1
            continue
        if extracted["_n_matseiningar"] == 0:
            missing_primary += 1
        rows_out.append(extracted)

    conn.close()
    df = pd.DataFrame(rows_out)
    print(f"\nTotal rows processed: {len(df):,}")
    print(f"JSON parse failures: {json_failures}")
    print(f"Missing primary matseining: {missing_primary}")

    print("\nNon-null counts per enrichment column:")
    cols = [
        "brunabotamat",
        "lhlmat",
        "fasteignamat_naesta_ar",
        "byggingarstig",
        "skodags",
        "gerd",
        "matsstig",
        "landeign_nr",
        "matseiningar_json",
        "tengd_stadfang_nr_json",
    ]
    for c in cols:
        nn = int(df[c].notna().sum())
        pct = 100.0 * nn / len(df) if len(df) else 0
        print(f"  {c:<28s} {nn:>7,} / {len(df):,}  ({pct:5.1f}%)")

    print("\nFirst 3 fastnums with full extracted payload:")
    for _, row in df.head(3).iterrows():
        fields = {c: row[c] for c in cols}
        print(f"  fastnum={int(row['fastnum'])}")
        for k, v in fields.items():
            if k in ("matseiningar_json", "tengd_stadfang_nr_json") and v:
                v = (v[:120] + "...") if len(v) > 120 else v
            print(f"    {k}: {v}")

    # Drop diagnostic columns before writing
    df_out = df[["fastnum"] + cols]

    try:
        df_out.to_parquet(OUT_PARQUET, index=False)
        print(f"\nWrote {OUT_PARQUET} ({OUT_PARQUET.stat().st_size:,} bytes)")
    except Exception as e:
        print(f"\nparquet write failed ({type(e).__name__}: {e}); falling back to pickle")
        df_out.to_pickle(OUT_PICKLE_FALLBACK)
        print(f"Wrote {OUT_PICKLE_FALLBACK} ({OUT_PICKLE_FALLBACK.stat().st_size:,} bytes)")

    print("\nSTEP 1 complete. NO Supabase writes performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
