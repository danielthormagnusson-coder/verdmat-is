"""promote_listings_append.py — Sales-trajectory Layer 1 populator (ADDITIVE, BLOKK 5).

Reads parsed_mbl_{sale,rent} and writes:
  * scraper.listings              — ONE row per (source, source_listing_id), NO fold-deletion.
  * scraper.listing_price_history — append-only (one row per listing's observed price).

Does NOT touch scraper.listings_canonical or promote_mbl.py — the old fold path keeps writing
canonical unchanged; this is a parallel additive layer. Reuses promote_mbl resolution helpers
(fastnum / category / price / foreign filter) so resolution is identical to the canonical path.

Watermark-INDEPENDENT: processes ALL priced listings (not just promoted_to_canonical_at IS NULL)
so a unit's FULL re-listing trajectory is captured (canonical promote already consumed many rows).

unit_key = (fastnum, size-cluster ±2%) + íb.nr coalesced splitter:
  - split a (fastnum, size-cluster) group into íb.nr sub-units ONLY when >=2 distinct non-null
    íb.nr are present; íb.nr=None is a wildcard (no split). matshluti is discarded (BLOKK 2).

Idempotent: scraper.listings ON CONFLICT (source, source_listing_id) DO UPDATE refreshes volatile
fields (= Vandi-1 field-staleness fix); price_history ON CONFLICT DO NOTHING.

Pooler READ-ONLY default: every write-tx opens with SET TRANSACTION READ WRITE as the first stmt.

CLI:
  python -m scripts.promote_listings_append                 # docstring + exit 0
  python -m scripts.promote_listings_append --confirm        # full run (sale priced + rent priced)
  python -m scripts.promote_listings_append --confirm --limit 200   # smoke
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values, Json

sys.path.insert(0, str(Path(__file__).resolve().parent))
from promote_mbl import (  # noqa: E402  reuse identical resolution logic
    foreign_filter, tenure_cascade, resolve_price, decompose_category,
    decompose_fastano, resolve_fastnum, preload_props, extract_common, parsed_db_path,
)

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
PROMOTER_VERSION = "listings_append_v1"
SIZE_TOL = 0.02

# íb.nr extractor (BLOKK 4, widened for "- NNN" without grabbing street ranges like "2-4")
_IBRX = re.compile(r"(?:íb\.?\s*|íbúð\s*|\()\s*(\d{1,4})|\s-\s+(\d{3,4})\b", re.IGNORECASE)


def extract_ibnr(addr: str | None) -> str | None:
    if not addr:
        return None
    last = None
    for m in _IBRX.finditer(addr):
        last = m.group(1) or m.group(2)
    return str(int(last)) if last else None


def size_cluster_map(sizes, tol=SIZE_TOL) -> dict:
    """Map each distinct size -> cluster representative (min size, int). Single-linkage on
    sorted sizes within relative tol. Deterministic for a fixed size-set."""
    uniq = sorted(set(s for s in sizes if s is not None))
    out = {}
    if not uniq:
        return out
    cur = [uniq[0]]
    for x in uniq[1:]:
        if abs(x - cur[-1]) / max(cur[-1], 1.0) <= tol:
            cur.append(x)
        else:
            rep = int(round(min(cur)))
            for y in cur:
                out[y] = rep
            cur = [x]
    rep = int(round(min(cur)))
    for y in cur:
        out[y] = rep
    return out


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _i(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def build_record(p, common, table, props):
    """Resolve one parsed row into a listings record (or None to skip)."""
    if foreign_filter(common):
        return None
    tenure = "rent" if table == "rent" else tenure_cascade(common)
    price, is_por = resolve_price(common["verd"], table)
    if table == "rent":
        cat, sub = ("residential", "apartment") if not is_por else ("commercial", None)
    else:
        cat, sub = decompose_category(common["teg_eign"], tenure, common.get("lysing") or "")
    m, raw, k = decompose_fastano(common.get("fastano"))
    derived = (common["fastano"] // k) if k else None
    fastnum, conf, method = resolve_fastnum(common, derived, props)
    size = _f(common.get("area"))
    ibnr = extract_ibnr(common.get("addr_text"))
    return {
        "source": "mbl",
        "source_listing_id": common["source_listing_id"],
        "fastnum": fastnum,
        "ibnr": ibnr,
        "tenure": tenure, "category": cat, "sub_type": sub,
        "tegund_raw": common.get("tegund_raw"),
        "price_amount": price, "is_price_on_request": is_por,
        "size_sqm": size, "rooms": _f(common.get("rooms")),
        "bedrooms": _i(common.get("bedrooms")), "bathrooms": _i(common.get("bathrooms")),
        "byggar": _i(p.get("bygg_ar")),
        "addr_text": common.get("addr_text"),
        "addr_postcode": (str(common["postcode"]) if common.get("postcode") is not None else None),
        "addr_municipality": common.get("municipality"),
        "lat": _f(common.get("lat")), "lng": _f(common.get("lng")),
        "lysing": common.get("lysing"),
        "photos_json": common.get("photos_json") or "[]",
        "listed_at": common.get("first_seen"), "first_seen_at": common.get("first_seen"),
        "last_seen_at": common.get("last_seen"),
        "status": "active" if (p.get("syna") in (1, None)) else "inactive",
        "surviving_parse_id": common.get("parse_id"),
        "br_dags": p.get("br_dags") if table == "sale" else p.get("updated"),
        "promoter_version": PROMOTER_VERSION,
    }


def assign_unit_keys(records):
    """Coalesced unit_key per record (in place). fastnum NULL -> unit_key NULL."""
    by_fastnum = defaultdict(list)
    for r in records:
        if r["fastnum"] is not None and r["size_sqm"] is not None:
            by_fastnum[int(r["fastnum"])].append(r)
        else:
            r["unit_key"] = None
    n_split = 0
    for fn, rs in by_fastnum.items():
        cmap = size_cluster_map([r["size_sqm"] for r in rs])
        by_cluster = defaultdict(list)
        for r in rs:
            by_cluster[cmap[r["size_sqm"]]].append(r)
        for rep, crs in by_cluster.items():
            nonnull = set(r["ibnr"] for r in crs if r["ibnr"])
            split = len(nonnull) >= 2
            if split:
                n_split += 1
            for r in crs:
                if split and r["ibnr"]:
                    r["unit_key"] = f"{fn}:{rep}:{r['ibnr']}"
                else:
                    r["unit_key"] = f"{fn}:{rep}"
    return n_split


_LISTING_COLS = [
    "source", "source_listing_id", "fastnum", "unit_key", "ibnr", "tenure", "category",
    "sub_type", "tegund_raw", "price_amount", "is_price_on_request", "size_sqm", "rooms",
    "bedrooms", "bathrooms", "byggar", "addr_text", "addr_postcode", "addr_municipality",
    "lat", "lng", "lysing", "photos_json", "listed_at", "first_seen_at", "last_seen_at",
    "discovered_at",
    "status", "surviving_parse_id", "br_dags", "promoter_version",
]
# volatile columns refreshed on re-promote (Vandi-1 fix); immutable ones preserved.
# first_seen_at + discovered_at are write-once: excluded from the update set so a
# re-promote never overwrites them (and pre-existing NULL discovered_at rows stay NULL).
_UPDATE_COLS = [c for c in _LISTING_COLS
                if c not in ("source", "source_listing_id", "first_seen_at", "discovered_at")]


def write_batch(pg, records, log=print):
    # discovered_at: write-once system-discovery stamp = now() at first INSERT.
    # One run timestamp for the whole batch (honest "when WE first recorded it",
    # NOT derived from listed_at/first_seen_at). Excluded from the ON CONFLICT update
    # set above, so re-promotes preserve the original and pre-existing NULL rows stay NULL.
    run_ts = datetime.now(timezone.utc)
    for r in records:
        r.setdefault("discovered_at", run_ts)
    rows = []
    for r in records:
        vals = []
        for c in _LISTING_COLS:
            v = r[c]
            if c == "photos_json":
                import json
                v = Json(json.loads(v) if isinstance(v, str) else (v or []))
            vals.append(v)
        rows.append(vals)
    cur = pg.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    cols = ", ".join(_LISTING_COLS)
    upd = ", ".join(f"{c}=EXCLUDED.{c}" for c in _UPDATE_COLS) + ", updated_at=now()"
    execute_values(cur,
        f"INSERT INTO scraper.listings ({cols}) VALUES %s "
        f"ON CONFLICT (source, source_listing_id) DO UPDATE SET {upd}", rows, page_size=1000)
    # price history: one observed price per listing (observed_at = listed_at), append-idempotent
    ph = [(r["source"], r["source_listing_id"], r["listed_at"], r["price_amount"], "ISK")
          for r in records if r["listed_at"] is not None and r["price_amount"] is not None]
    execute_values(cur,
        "INSERT INTO scraper.listing_price_history "
        "(source, source_listing_id, observed_at, price_amount, price_currency) VALUES %s "
        "ON CONFLICT (source, source_listing_id, observed_at, price_amount) DO NOTHING", ph,
        page_size=1000)
    pg.commit()
    return len(rows), len(ph)  # rows attempted (cur.rowcount only reflects the last page)


def run(limit, log=print):
    sq = sqlite3.connect(str(parsed_db_path()))
    sq.row_factory = sqlite3.Row
    dsn = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    pg = psycopg2.connect(dsn)
    t0 = time.perf_counter()
    try:
        all_recs = []
        derived_all, postcodes_all = [], set()
        staged = []
        for table in ("sale", "rent"):
            q = (f"SELECT * FROM parsed_mbl_{table} WHERE is_negotiable=0 ORDER BY parse_id"
                 + (f" LIMIT {int(limit)}" if limit else ""))
            parsed = [dict(r) for r in sq.execute(q)]
            for p in parsed:
                c = extract_common(p, table)
                m, raw, k = decompose_fastano(c.get("fastano"))
                if k:
                    derived_all.append(c["fastano"] // k)
                if c.get("postcode"):
                    postcodes_all.add(c["postcode"])
                staged.append((p, c, table))
            log(f"  loaded parsed_mbl_{table} (priced): {len(parsed)}")
        props = preload_props(pg, postcodes_all, derived_all)
        pg.rollback()  # close preload read-tx so first write-tx SET READ WRITE is first stmt
        log(f"  preloaded props: present={len(props.present)} addr_keys={len(props.by_addr)}")
        n_skip = 0
        for p, c, table in staged:
            rec = build_record(p, c, table, props)
            if rec is None:
                n_skip += 1
                continue
            all_recs.append(rec)
        n_split = assign_unit_keys(all_recs)
        n_units = len(set(r["unit_key"] for r in all_recs if r["unit_key"]))
        log(f"  records={len(all_recs)} foreign_skip={n_skip} unit_keys={n_units} split_clusters={n_split}")
        # write in chunks
        nL = nP = 0
        for i in range(0, len(all_recs), 2000):
            a, b = write_batch(pg, all_recs[i:i+2000])
            nL += a; nP += b
        log(f"  wrote listings rows={nL}, price_history rows={nP} ({time.perf_counter()-t0:.1f}s)")
        return nL, nP, n_units
    finally:
        sq.close(); pg.close()


def main():
    ap = argparse.ArgumentParser(description="Append parsed_mbl -> scraper.listings + price_history (additive)")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if not args.confirm:
        print(__doc__)
        print("\nRe-invoke with --confirm (add --limit N for a smoke run).")
        return 0
    print(f"promote_listings_append {PROMOTER_VERSION} limit={args.limit}")
    run(args.limit)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
