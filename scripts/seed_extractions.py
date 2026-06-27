"""seed_extractions.py — one-off lossless seed of scraper.listing_extractions (EXTRACTION ÞREP 3).

Content-addressed seed from two pre-existing extraction sources, hash-matched to the live mbl
lysing so the seed is byte-lossless (no source-mixing):

  * seed_vel1  — model_quality_extraction_cache.jsonl (VÉL 1 OOS cache; mbl canonical lysing,
                 key = fastnum:md5(lysing)[:12]). All entries seeded (content-addressed); a hash
                 with no live Lag-1 listing still belongs in the table.
  * seed_april — Áfangi-3 batch (batch_extraction_unique.jsonl, custom_id->extraction on evalue
                 text). Only the April extractions whose lysing md5[:12] EXACTLY matches a live
                 Lag-1 hash are seeded (evalue text rarely equals mbl text → ~1% overlap; the rest
                 is intentionally NOT seeded to avoid mixing evalue text into the monitoring layer).

ON CONFLICT (lysing_hash) DO NOTHING — VÉL 1 wins any cross-source hash collision; idempotent.
No Haiku, no network. Pooler write opens with SET TRANSACTION READ WRITE.

Usage: python -m scripts.seed_extractions [--confirm]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values, Json

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
VEL1_CACHE = Path(r"D:\model_quality_extraction_cache.jsonl")
APRIL_UNIQUE = Path(r"D:\batch_extraction_unique.jsonl")
LISTINGS_TEXT = Path(r"D:\listings_text_v2.pkl")
SCHEMA_VERSION = "v0.2.2"
MODEL = "claude-haiku-4-5"


def md5_12(t: str | None) -> str:
    return hashlib.md5((t if isinstance(t, str) else "").encode("utf-8")).hexdigest()[:12]


def lag1_hashes(pg) -> set:
    c = pg.cursor()
    c.execute("SELECT DISTINCT substr(md5(lysing), 1, 12) FROM scraper.listings "
              "WHERE lysing IS NOT NULL AND length(lysing) >= 300")
    return set(r[0] for r in c.fetchall())


def load_vel1() -> dict:
    """lysing_hash -> extraction (from VÉL 1 cache)."""
    out = {}
    for line in VEL1_CACHE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        h = o["key"].split(":")[1]
        out[h] = o["raw"]
    return out


def load_april_matching(lag1: set) -> dict:
    """lysing_hash -> extraction, only for April extractions whose evalue-text md5[:12] is a live
    Lag-1 hash. custom_id is assumed == augl_id (verified at runtime)."""
    txt = pd.read_pickle(LISTINGS_TEXT)
    # augl_id(str) -> md5[:12]; keep only those matching a live Lag-1 hash
    target = {}  # augl_id(str) -> hash
    for aid, ly in zip(txt["augl_id"].astype(str), txt["lysing"]):
        h = md5_12(ly)
        if h in lag1:
            target[aid] = h
    print(f"  evalue augl_ids whose text-hash matches a live Lag-1 listing: {len(target)}")
    out = {}
    hit = 0
    for line in APRIL_UNIQUE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        cid = str(o.get("custom_id"))
        if cid in target and o.get("result_type") == "succeeded":
            hit += 1
            out[target[cid]] = o["extraction"]
    print(f"  April extractions whose custom_id matches a target augl_id: {hit}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()

    pg = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    pg.autocommit = True
    pg.set_session(readonly=True)
    lag1 = lag1_hashes(pg)
    print(f"live Lag-1 distinct lysing hashes: {len(lag1)}")

    vel1 = load_vel1()
    print(f"seed_vel1 candidates: {len(vel1)}")
    april = load_april_matching(lag1)
    print(f"seed_april candidates (hash-matched): {len(april)}")

    # build rows; vel1 wins collisions
    rows = []
    for h, ext in vel1.items():
        rows.append((h, Json(ext), SCHEMA_VERSION, MODEL, "seed_vel1"))
    collisions = 0
    for h, ext in april.items():
        if h in vel1:
            collisions += 1
            continue
        rows.append((h, Json(ext), SCHEMA_VERSION, MODEL, "seed_april"))
    print(f"cross-source hash collisions (vel1 wins): {collisions}")
    print(f"total distinct rows to seed: {len(rows)}")
    print(f"  of which match a live Lag-1 listing: {sum(1 for r in rows if r[0] in lag1)}")

    if not args.confirm:
        print("\n[dry] re-run with --confirm to write.")
        pg.close()
        return 0

    pg.set_session(readonly=False)
    cur = pg.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    execute_values(cur,
        "INSERT INTO scraper.listing_extractions "
        "(lysing_hash, extraction, extraction_schema_version, extraction_model, source_trigger) "
        "VALUES %s ON CONFLICT (lysing_hash) DO NOTHING", rows, page_size=500)
    pg.commit()
    cur.execute("SELECT source_trigger, count(*) FROM scraper.listing_extractions GROUP BY 1 ORDER BY 1")
    print("written; listing_extractions by trigger:", cur.fetchall())
    pg.close()
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
