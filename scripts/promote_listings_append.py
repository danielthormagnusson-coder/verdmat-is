"""promote_listings_append.py — Sales-trajectory Layer 1 populator (ADDITIVE, BLOKK 5).

Reads parsed_mbl_{sale,rent} and writes:
  * scraper.listings              — ONE row per (source, source_listing_id), NO fold-deletion.
  * scraper.listing_price_history — append-only (one row per listing's observed price).

Does NOT touch scraper.listings_canonical or promote_mbl.py — the old fold path keeps writing
canonical unchanged; this is a parallel additive layer. Reuses promote_mbl resolution helpers
(fastnum / category / price / foreign filter) so resolution is identical to the canonical path.

v2 DELTA-WRITE (cc11 rótarfix, 2026-07-10): v1 re-upserted the FULL parsed corpus nightly
(~25K rows, ~364MB TOAST churn) and hit the instance-level 120s statement_timeout as the
corpus grew (nights 07-07→08 and 08→09 aborted). v2 still RESOLVES the full corpus in memory
(unit_key clustering needs every row of a fastnum group — that part is local and cheap) but
ships to Postgres only:
  (a) rows whose parse_id is above the per-table watermark of the last clean run
      (parse_mbl re-parse = DELETE+INSERT -> new parse_id, so this is exactly the
      changed/new set),
  (b) rows whose computed unit_key differs from the stored one (cluster drift caused
      by (a) rows joining/leaving a size cluster), and
  (c) rows missing from scraper.listings entirely (self-healing).
The upsert also carries a no-op guard (DO UPDATE ... WHERE (row) IS DISTINCT FROM (EXCLUDED))
so a content-identical row is never physically rewritten (protects TOAST/WAL independently of
the watermark). Watermarks live in scraper_data/mbl_promote_append_state.json and advance
ONLY after a full clean run (--limit and --dry-run never advance them; a missing/unreadable
state file falls back to the full write-set, which the no-op guard keeps cheap server-side).
The 120s statement_timeout is deliberately NOT raised — it is the safety net that should
bark if the delta path ever regresses to full-corpus writes.

Watermark-INDEPENDENT trajectory rationale (v1 docstring) still holds for CONTENT: every
priced listing is resolved each run; only the shipping of unchanged rows is skipped.

unit_key = (fastnum, size-cluster ±2%) + íb.nr coalesced splitter:
  - split a (fastnum, size-cluster) group into íb.nr sub-units ONLY when >=2 distinct non-null
    íb.nr are present; íb.nr=None is a wildcard (no split). matshluti is discarded (BLOKK 2).

Idempotent: scraper.listings ON CONFLICT (source, source_listing_id) DO UPDATE refreshes volatile
fields (= Vandi-1 field-staleness fix); price_history ON CONFLICT DO NOTHING. A failed run never
advances the watermark, so the re-run re-ships the same delta (upsert-idempotent, abort-not-retry).

Pooler READ-ONLY default: every write-tx opens with SET TRANSACTION READ WRITE as the first stmt.

CLI:
  python -m scripts.promote_listings_append                          # docstring + exit 0
  python -m scripts.promote_listings_append --confirm                # delta run (sale+rent priced)
  python -m scripts.promote_listings_append --confirm --dry-run      # full compute + write-set
                                                                     #   report, ZERO writes
  python -m scripts.promote_listings_append --confirm --limit 200    # smoke (never advances
                                                                     #   watermark)
"""
from __future__ import annotations

import argparse
import json
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
from scraper_paths import get_scraper_data_dir  # noqa: E402

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
PROMOTER_VERSION = "listings_append_v2"
SIZE_TOL = 0.02
STATE_FILE = "mbl_promote_append_state.json"

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


def state_path() -> Path:
    return get_scraper_data_dir() / STATE_FILE


def load_watermarks(log=print):
    """Per-table parse_id watermarks of the last clean run, or None (-> full write-set)."""
    p = state_path()
    if not p.is_file():
        log("  WARNING: no watermark state (%s) — full write-set fallback" % p.name)
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"sale": int(d["sale_max_parse_id"]), "rent": int(d["rent_max_parse_id"])}
    except (KeyError, TypeError, ValueError) as e:
        log("  WARNING: watermark state unreadable (%s) — full write-set fallback" % e)
        return None


def save_watermarks(max_ids, n_written):
    """Advance watermarks (atomic replace). Called ONLY after a full clean run."""
    p = state_path()
    d = {"sale_max_parse_id": max_ids["sale"], "rent_max_parse_id": max_ids["rent"],
         "last_clean_run": datetime.now(timezone.utc).isoformat(),
         "last_written_rows": n_written, "promoter_version": PROMOTER_VERSION}
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2), encoding="utf-8")
    tmp.replace(p)


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
                v = Json(json.loads(v) if isinstance(v, str) else (v or []))
            vals.append(v)
        rows.append(vals)
    cur = pg.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    cols = ", ".join(_LISTING_COLS)
    upd = ", ".join(f"{c}=EXCLUDED.{c}" for c in _UPDATE_COLS) + ", updated_at=now()"
    # no-op guard: content-identical rows are not physically rewritten (no TOAST/WAL churn)
    guard_l = ", ".join(f"l.{c}" for c in _UPDATE_COLS)
    guard_e = ", ".join(f"EXCLUDED.{c}" for c in _UPDATE_COLS)
    execute_values(cur,
        f"INSERT INTO scraper.listings AS l ({cols}) VALUES %s "
        f"ON CONFLICT (source, source_listing_id) DO UPDATE SET {upd} "
        f"WHERE ({guard_l}) IS DISTINCT FROM ({guard_e})", rows, page_size=1000)
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


def run(limit, dry_run=False, log=print):
    sq = sqlite3.connect(str(parsed_db_path()))
    sq.row_factory = sqlite3.Row
    dsn = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    pg = psycopg2.connect(dsn)
    t0 = time.perf_counter()
    try:
        all_recs = []
        derived_all, postcodes_all = [], set()
        staged = []
        max_parse_id = {"sale": 0, "rent": 0}
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
                if p["parse_id"] > max_parse_id[table]:
                    max_parse_id[table] = p["parse_id"]
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
            rec["_parse_id"] = p["parse_id"]
            rec["_table"] = table
            all_recs.append(rec)
        n_split = assign_unit_keys(all_recs)
        n_units = len(set(r["unit_key"] for r in all_recs if r["unit_key"]))
        log(f"  records={len(all_recs)} foreign_skip={n_skip} unit_keys={n_units} split_clusters={n_split}")

        # v2 write-set: parse-delta ∪ unit_key-drift ∪ missing-in-db (full corpus if no watermark)
        wm = load_watermarks(log)
        cur = pg.cursor()
        cur.execute("SELECT source_listing_id, unit_key FROM scraper.listings WHERE source='mbl'")
        db_units = {row[0]: row[1] for row in cur.fetchall()}
        pg.rollback()  # close read-tx; next write-tx SET READ WRITE stays first stmt
        n_delta = n_drift = n_missing = 0
        write_recs = []
        for r in all_recs:
            slid = str(r["source_listing_id"])
            if slid not in db_units:
                n_missing += 1
                write_recs.append(r)
            elif wm is None or r["_parse_id"] > wm[r["_table"]]:
                n_delta += 1
                write_recs.append(r)
            elif db_units[slid] != r["unit_key"]:
                n_drift += 1
                write_recs.append(r)
        wm_txt = ("NO WATERMARK -> full fallback" if wm is None
                  else f"watermark sale>{wm['sale']} rent>{wm['rent']}")
        log(f"  write-set: total={len(write_recs)} (parse-delta={n_delta} unit-drift={n_drift} "
            f"missing-in-db={n_missing}; unchanged-skipped={len(all_recs) - len(write_recs)}; {wm_txt})")

        if dry_run:
            for r in write_recs[:10]:
                log(f"    would-write: slid={r['source_listing_id']} table={r['_table']} "
                    f"parse_id={r['_parse_id']} unit_key={r['unit_key']}")
            log(f"  DRY-RUN: no writes, watermark untouched ({time.perf_counter() - t0:.1f}s)")
            return 0, 0, n_units

        # write in chunks, per-batch progress (a timeout now names its batch)
        nL = nP = 0
        n_batches = (len(write_recs) + 1999) // 2000
        for bi, i in enumerate(range(0, len(write_recs), 2000), start=1):
            tb = time.perf_counter()
            a, b = write_batch(pg, write_recs[i:i + 2000])
            nL += a; nP += b
            log(f"  batch {bi}/{n_batches}: listings={a} price_history={b} "
                f"({time.perf_counter() - tb:.1f}s)")
        if limit is None:
            save_watermarks(max_parse_id, nL)
            log(f"  watermark advanced: sale={max_parse_id['sale']} rent={max_parse_id['rent']} "
                f"-> {state_path().name}")
        else:
            log("  --limit run: watermark NOT advanced")
        log(f"  wrote listings rows={nL}, price_history rows={nP} ({time.perf_counter()-t0:.1f}s)")
        return nL, nP, n_units
    finally:
        sq.close(); pg.close()


def main():
    ap = argparse.ArgumentParser(description="Append parsed_mbl -> scraper.listings + price_history (additive, delta-write)")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="full compute + write-set report, zero writes, watermark untouched")
    args = ap.parse_args()
    if not args.confirm:
        print(__doc__)
        print("\nRe-invoke with --confirm (add --dry-run for a zero-write report, --limit N for a smoke run).")
        return 0
    print(f"promote_listings_append {PROMOTER_VERSION} limit={args.limit} dry_run={args.dry_run}")
    run(args.limit, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
