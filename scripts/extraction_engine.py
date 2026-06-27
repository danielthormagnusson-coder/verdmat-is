"""extraction_engine.py — content-addressed extraction + frozen valuation engine (EXTRACTION
ÞREP 3-4). One engine, three triggers (seed / nightly-forward / on-demand-lazy share value_listings;
extract_and_store is the Haiku half used by forward + lazy).

  * value_listings(pg, models, rows)   — score expected_base (structured) + expected_extraction
                                          (+ 108-field features) via the VÉL 1 freeze-anchored
                                          adapter, freeze into scraper.listing_valuations.
                                          NO Haiku — extraction comes from listing_extractions.
  * extract_and_store(pg, client, rows) — Haiku 108-field extract for lysingar with no extraction,
                                          store content-addressed in listing_extractions.

Parity basis: phase_d3_score_extract.score pins sale_year/month to VALUATION_YEAR/MONTH (2026-04),
so expected_base reproduces public.predictions (D2 parity 0.0000%); expected_extraction overlays
the extraction feature columns. Both nominal @ 2026-04, identical basis → gap is clean.

Pooler writes open with SET TRANSACTION READ WRITE. The Haiku key is read ONLY from D:\env.local
(see extract_and_store) — never os.environ.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values, Json

sys.path.insert(0, str(Path(__file__).resolve().parent))   # scripts/
sys.path.insert(0, r"D:\\")                                  # build_training_data_v2

from model_quality_eval import (  # noqa: E402
    load_models_freeze_anchored, _score_iter4, _coerce_numeric, MODEL_VERSION)
from build_training_data_v2 import build_extraction_features  # noqa: E402

VALUATION_YEAR = 2026
SCHEMA_VERSION = "v0.2.2"
EXTRACT_MODEL = "claude-haiku-4-5"

# property feature columns the iter4 adapter consumes (same set as fetch_paired_oos)
PROP_COLS = ("einflm", "lod_flm", "byggar", "matsvaedi_numer", "matsvaedi_bucket",
             "region_tier", "canonical_code", "unit_category", "is_main_unit",
             "is_new_build", "postnr", "lat", "lng", "landeign_nr")


def md5_12(t):
    return hashlib.md5((t if isinstance(t, str) else "").encode("utf-8")).hexdigest()[:12]


def fetch_extracted_listings_to_value(pg, limit=None):
    """mbl listings whose lysing has an extraction but no valuation yet (for this model)."""
    cols = ", ".join(f"pr.{c}" for c in PROP_COLS)
    sql = f"""
      SELECT DISTINCT ON (l.source_listing_id)
             l.source_listing_id, l.fastnum, e.lysing_hash, e.extraction, {cols}
      FROM scraper.listings l
      JOIN scraper.listing_extractions e ON e.lysing_hash = substr(md5(l.lysing), 1, 12)
      JOIN public.properties pr ON pr.fastnum = l.fastnum
      LEFT JOIN scraper.listing_valuations v
             ON v.source_listing_id = l.source_listing_id AND v.model_version = %s
      WHERE l.source = 'mbl' AND l.fastnum IS NOT NULL AND l.lysing IS NOT NULL
        AND v.valuation_id IS NULL
      ORDER BY l.source_listing_id, l.last_seen_at DESC NULLS LAST
      {('LIMIT %d' % int(limit)) if limit else ''}
    """
    cur = pg.cursor()
    cur.execute(sql, (MODEL_VERSION,))
    out = []
    names = [d[0] for d in cur.description]
    for row in cur.fetchall():
        out.append(dict(zip(names, row)))
    return out


def value_listings(pg, models, rows, log=print):
    """Score + freeze valuations for the given extracted listings. Returns n_written."""
    if not rows:
        log("  no listings to value")
        return 0
    # one feature row per fastnum (prediction is per-property)
    by_fastnum = {}
    ext_by_fastnum = {}
    for r in rows:
        fn = int(r["fastnum"])
        if fn not in by_fastnum:
            by_fastnum[fn] = {c: r[c] for c in PROP_COLS}
            by_fastnum[fn]["fastnum"] = fn
            ext_by_fastnum[fn] = build_extraction_features(
                r["extraction"], VALUATION_YEAR, r["canonical_code"])
    df = _coerce_numeric(pd.DataFrame(list(by_fastnum.values())))  # Decimal -> float for LightGBM
    base = _score_iter4(df, models).set_index("fastnum")
    full = _score_iter4(df, models, ext_by_fastnum).set_index("fastnum")

    vals = []
    skipped = 0
    for r in rows:
        fn = int(r["fastnum"])
        if fn not in base.index or fn not in full.index:
            skipped += 1
            continue
        eb = int(round(float(base.loc[fn, "real_pred_median"])))
        ex = int(round(float(full.loc[fn, "real_pred_median"])))
        vals.append((fn, r["source_listing_id"], r["lysing_hash"], eb, ex, True,
                     MODEL_VERSION))
    cur = pg.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    execute_values(cur,
        "INSERT INTO scraper.listing_valuations "
        "(fastnum, source_listing_id, lysing_hash, expected_base, expected_extraction, "
        " extraction_applied, model_version) VALUES %s "
        "ON CONFLICT (source_listing_id, model_version) DO NOTHING", vals, page_size=500)
    pg.commit()
    log(f"  valued {len(vals)} listings (skipped {skipped} unscored); "
        f"{len(by_fastnum)} distinct fastnum scored")
    return len(vals)


# ───────────────────────── forward / lazy Haiku half ─────────────────────────
def fetch_listings_needing_extraction(pg, limit):
    """Distinct mbl lysingar (>=300) with NO extraction yet — one representative listing each."""
    sql = f"""
      WITH need AS (
        SELECT substr(md5(l.lysing), 1, 12) AS h, min(l.source_listing_id) AS slid,
               max(l.lysing) AS lysing
        FROM scraper.listings l
        LEFT JOIN scraper.listing_extractions e ON e.lysing_hash = substr(md5(l.lysing), 1, 12)
        WHERE l.source = 'mbl' AND l.lysing IS NOT NULL AND length(l.lysing) >= 300
          AND e.lysing_hash IS NULL
        GROUP BY 1
      )
      SELECT h, slid, lysing FROM need LIMIT {int(limit)}
    """
    cur = pg.cursor()
    cur.execute(sql)
    return [{"lysing_hash": r[0], "source_listing_id": r[1], "lysing": r[2]} for r in cur.fetchall()]


def extract_and_store(pg, client, rows, source_trigger, log=print):
    """Haiku 108-field extract for each distinct lysing, store content-addressed. Returns counts."""
    from pilot_extract_v022 import build_tool_schema, extract_listing
    schema = build_tool_schema()
    out = []
    n_call = n_fail = 0
    for i, r in enumerate(rows, 1):
        h = r["lysing_hash"]
        # content-addressed idempotency is handled by the fetch filter + ON CONFLICT DO NOTHING
        # (no in-loop SELECT, so the final write keeps SET TRANSACTION READ WRITE as its first stmt)
        try:
            raw, usage, err = extract_listing(client, schema, r["lysing"], lambda *a, **k: None)
            n_call += 1
            if err or raw is None:
                raise RuntimeError(err or "no extraction")
            out.append((h, Json(raw), SCHEMA_VERSION, EXTRACT_MODEL, source_trigger, len(r["lysing"])))
            log(f"    [{i}/{len(rows)}] {h} ok ({usage.get('duration_sec','?')}s)")
        except Exception as e:
            n_fail += 1
            log(f"    [{i}/{len(rows)}] skip {h}: {type(e).__name__}: {e}")
    if out:
        cur = pg.cursor()
        cur.execute("SET TRANSACTION READ WRITE")
        execute_values(cur,
            "INSERT INTO scraper.listing_extractions "
            "(lysing_hash, extraction, extraction_schema_version, extraction_model, "
            " source_trigger, lysing_len) VALUES %s "
            "ON CONFLICT (lysing_hash) DO NOTHING", out, page_size=500)
        pg.commit()
    return {"haiku_calls": n_call, "stored": len(out), "failed": n_fail,
            "cost_est_usd": round(n_call * 0.0071, 4)}
