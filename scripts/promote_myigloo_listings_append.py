"""promote_myigloo_listings_append.py — myigloo sales-trajectory Layer 1 populator (ADDITIVE).

The myigloo sibling of promote_listings_append.py (mbl). A2 decision (2026-06-27): a SEPARATE
script, NOT a generalisation of the mbl writer — the mbl nightly path is being armed and must
not be touched, and myigloo's resolution differs (rent-only, no fastano, active-set lifecycle).

Writes:
  * scraper.listings              — ONE row per (source='myigloo', source_listing_id), upsert.
  * scraper.listing_price_history — append-only (observed price per listing).
Does NOT touch scraper.listings_canonical (the old fold path keeps writing it via promote_myigloo).

LIFECYCLE — active-set diff (the genuinely new logic; mbl has none, it reads `syna`):
  * active set = source_listing_ids with a 200 DETAIL fetch in the latest FULL sweep. "Full"
    = a run with >= FULL_SWEEP_MIN detail ids, so dry-run probes (10 ids) cannot be mistaken
    for the active set. Runs are grouped by fetch_run_id (nightly, unambiguous) and, for legacy
    rows that predate that column, by a fetched_at gap (GAP_SECONDS) — the gap is a fallback
    only, never the long-term boundary.
  * status='active' for ids in the active set; status='withdrawn' + withdrawn_at for an id that
    is parsed/known (or already in scraper.listings) but absent from the latest full sweep.

unit_key is ALWAYS NULL: myigloo is rent-only and rent does not participate in the unit rollup
(scraper.v_units filters unit_key IS NOT NULL), so it never enters the sale-trajectory grain.

Idempotent: scraper.listings ON CONFLICT (source, source_listing_id) DO UPDATE refreshes volatile
fields; listing_price_history ON CONFLICT DO NOTHING. Pooler READ-ONLY default → every write-tx
opens with SET TRANSACTION READ WRITE as the first statement.

CLI:
  python -m scripts.promote_myigloo_listings_append                 # docstring + exit 0
  python -m scripts.promote_myigloo_listings_append --confirm        # full run
  python -m scripts.promote_myigloo_listings_append --confirm --dry-run   # build+report, NO writes
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values, Json

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path                      # noqa: E402
from promote_myigloo import (                                  # noqa: E402  reuse identical resolution
    TAXONOMY_LOOKUP, JUNK_PRICE_MAX, _is_junk, _listing_title, _addr_text,
)

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
PROMOTER_VERSION = "myigloo_listings_append_v1"
SOURCE = "myigloo"
GAP_SECONDS = 3600        # >1h between adjacent legacy (NULL-run_id) detail rows = a run boundary
FULL_SWEEP_MIN = 100      # a run needs >= this many 200-detail ids to count as the active set
                          # (excludes dry-run probes, which fetch ~10 details)


def _now_dt():
    return datetime.now(__import__("datetime").timezone.utc)


def _now():
    return _now_dt().isoformat()


def _parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


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


# ───────────────────────────────────── active-set: run grouping over the ledger
def get_runs(sq):
    """Group 200-detail fetches into runs. run_id-stamped rows group by run_id (nightly,
    unambiguous); legacy NULL-run_id rows gap-cluster on fetched_at. Returns runs ordered
    by max_ts ascending, each {label, ids:set, min_ts, max_ts, n}."""
    rows = sq.execute(
        "SELECT fetch_run_id, source_listing_id, fetched_at FROM raw_fetches "
        "WHERE source=? AND fetch_kind='detail' AND http_status=200 "
        "ORDER BY fetched_at", (SOURCE,)).fetchall()
    runs = []
    by_runid, nullrows = {}, []
    for rid, sid, ts in rows:
        if rid:
            by_runid.setdefault(rid, []).append((sid, ts))
        else:
            nullrows.append((sid, ts))
    for rid, items in by_runid.items():
        tss = [t for _, t in items]
        runs.append({"label": "run:" + rid, "ids": {s for s, _ in items},
                     "min_ts": min(tss), "max_ts": max(tss), "n": len({s for s, _ in items})})
    # gap-cluster the legacy rows (already in fetched_at order)
    cluster, prev = [], None

    def flush(cl):
        if not cl:
            return
        tss = [t for _, t in cl]
        runs.append({"label": "legacy:" + min(tss)[:10], "ids": {s for s, _ in cl},
                     "min_ts": min(tss), "max_ts": max(tss), "n": len({s for s, _ in cl})})
    for sid, ts in nullrows:
        if prev is not None and (_parse_ts(ts) - _parse_ts(prev)).total_seconds() > GAP_SECONDS:
            flush(cluster)
            cluster = []
        cluster.append((sid, ts))
        prev = ts
    flush(cluster)
    runs.sort(key=lambda r: r["max_ts"])
    return runs


def pick_active(runs):
    """(active_run, prior_full_run). active = latest run with n >= FULL_SWEEP_MIN; prior = the
    full run before it (for the churn report). Dry-run probes (n<FULL_SWEEP_MIN) are skipped."""
    full = [r for r in runs if r["n"] >= FULL_SWEEP_MIN]
    if not full:
        return None, None
    return full[-1], (full[-2] if len(full) >= 2 else None)


# ───────────────────────────────────── record build
def build_record(p, active_ids, seen, run_max_dt):
    """One parsed_myigloo row (dict) -> a scraper.listings record, or None to skip (junk)."""
    tag = p.get("listing_type_tag")
    cat, ten, sub = TAXONOMY_LOOKUP.get(tag, ("other", "rent", "other"))
    if _is_junk(p, cat):
        return None
    price = p.get("price_amount")
    price = _i(price) if price is not None else None
    # commercial price<=100 ISK = 'verð samkvæmt tilboði' (price-on-request), kept as-is;
    # residential junk already filtered by _is_junk above.
    is_por = bool(cat == "commercial" and price is not None and price <= JUNK_PRICE_MAX)
    sid = str(p["source_listing_id"])
    fs, ls = seen.get(sid, (None, None))
    active = sid in active_ids
    addr = _addr_text(p)
    return {
        "source": SOURCE,
        "source_listing_id": sid,
        "fastnum": None,                 # rent: no rollup, unit_key stays NULL (A2 decision)
        "unit_key": None,
        "ibnr": None,
        "tenure": ten,
        "category": cat,
        "sub_type": sub,
        "tegund_raw": p.get("tegund_raw") or tag or "unknown",
        "price_amount": price,
        "price_currency": p.get("price_currency") or "ISK",
        "is_price_on_request": is_por,
        "size_sqm": _f(p.get("size_sqm")),
        "rooms": _f(p.get("rooms")),
        "bedrooms": _i(p.get("bedrooms")),
        "bathrooms": _i(p.get("bathrooms")),
        "byggar": None,                  # myigloo carries no build year
        "addr_text": addr,
        "addr_postcode": (str(p["addr_postcode"]) if p.get("addr_postcode") is not None else None),
        "addr_municipality": p.get("addr_city"),
        "lat": _f(p.get("lat")),
        "lng": _f(p.get("lng")),
        "lysing": p.get("lysing"),
        "photos_json": p.get("photos_json") or "[]",
        "listed_at": p.get("source_published_at"),
        "first_seen_at": fs,
        "last_seen_at": ls,
        "withdrawn_at": (None if active else run_max_dt.isoformat()),
        "status": ("active" if active else "withdrawn"),
        "surviving_parse_id": p.get("parse_id"),
        "br_dags": p.get("source_last_edit"),
        "promoter_version": PROMOTER_VERSION,
    }


_LISTING_COLS = [
    "source", "source_listing_id", "fastnum", "unit_key", "ibnr", "tenure", "category",
    "sub_type", "tegund_raw", "price_amount", "price_currency", "is_price_on_request",
    "size_sqm", "rooms", "bedrooms", "bathrooms", "byggar", "addr_text", "addr_postcode",
    "addr_municipality", "lat", "lng", "lysing", "photos_json", "listed_at", "first_seen_at",
    "last_seen_at", "withdrawn_at", "status", "surviving_parse_id", "br_dags", "promoter_version",
]
# immutable on re-promote: identity + first_seen_at. Everything else (incl. status/withdrawn_at)
# is refreshed so a re-listing or a withdrawal is reflected.
_UPDATE_COLS = [c for c in _LISTING_COLS if c not in ("source", "source_listing_id", "first_seen_at")]


def write_batch(pg, records):
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
    execute_values(cur,
        f"INSERT INTO scraper.listings ({cols}) VALUES %s "
        f"ON CONFLICT (source, source_listing_id) DO UPDATE SET {upd}", rows, page_size=1000)
    ph = [(r["source"], r["source_listing_id"], r["listed_at"] or r["first_seen_at"],
           r["price_amount"], r["price_currency"])
          for r in records
          if (r["listed_at"] or r["first_seen_at"]) is not None and r["price_amount"] is not None]
    execute_values(cur,
        "INSERT INTO scraper.listing_price_history "
        "(source, source_listing_id, observed_at, price_amount, price_currency) VALUES %s "
        "ON CONFLICT (source, source_listing_id, observed_at, price_amount) DO NOTHING", ph,
        page_size=1000)
    pg.commit()
    return len(rows), len(ph)


def sweep_withdrawn(pg, active_ids, run_max_dt):
    """Belt-and-suspenders: any scraper.listings(myigloo) row still 'active' but absent from the
    latest full sweep -> withdrawn. Catches rows promoted on a prior night that are now gone even
    if they fell out of the parsed universe. Returns rowcount."""
    cur = pg.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    cur.execute(
        "UPDATE scraper.listings SET status='withdrawn', withdrawn_at=%s, updated_at=now() "
        "WHERE source=%s AND status='active' AND NOT (source_listing_id = ANY(%s))",
        (run_max_dt.isoformat(), SOURCE, list(active_ids)))
    n = cur.rowcount
    pg.commit()
    return n


# ───────────────────────────────────────────────────────────────────────── run
def run(dry_run, log=print):
    sq = sqlite3.connect(str(get_raw_db_path(SOURCE)))
    sq.row_factory = sqlite3.Row
    pg = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    if dry_run:
        pg.set_session(readonly=True, autocommit=True)
    t0 = time.perf_counter()
    try:
        runs = get_runs(sq)
        active, prior = pick_active(runs)
        if active is None:
            log("NO full sweep found (no run with >= %d detail ids) — nothing to promote." % FULL_SWEEP_MIN)
            return
        active_ids = active["ids"]
        run_max_dt = _parse_ts(active["max_ts"])
        log("=== promote_myigloo_listings_append %s ===" % ("DRY-RUN" if dry_run else "FULL"))
        log("  active run: %s  n=%d  max_ts=%s" % (active["label"], active["n"], active["max_ts"]))
        if prior:
            gone = prior["ids"] - active_ids
            appeared = active_ids - prior["ids"]
            log("  prior full run: %s n=%d | ledger churn since: gone=%d appeared=%d"
                % (prior["label"], prior["n"], len(gone), len(appeared)))

        seen = {r[0]: (r[1], r[2]) for r in sq.execute(
            "SELECT source_listing_id, MIN(fetched_at), MAX(fetched_at) FROM raw_fetches "
            "WHERE source=? AND fetch_kind='detail' AND http_status=200 GROUP BY source_listing_id",
            (SOURCE,))}

        # universe = latest parsed row per source_listing_id (MAX raw_id wins)
        parsed = [dict(r) for r in sq.execute(
            "SELECT p.* FROM parsed_myigloo p JOIN ("
            "  SELECT source_listing_id, MAX(raw_id) mr FROM parsed_myigloo GROUP BY source_listing_id"
            ") m ON p.source_listing_id=m.source_listing_id AND p.raw_id=m.mr")]
        log("  parsed universe (latest per listing): %d" % len(parsed))

        records, n_junk = [], 0
        for p in parsed:
            rec = build_record(p, active_ids, seen, run_max_dt)
            if rec is None:
                n_junk += 1
            else:
                records.append(rec)
        n_active = sum(1 for r in records if r["status"] == "active")
        n_withdrawn = sum(1 for r in records if r["status"] == "withdrawn")
        log("  records=%d  active=%d  withdrawn(diff)=%d  skipped_junk=%d"
            % (len(records), n_active, n_withdrawn, n_junk))

        if dry_run:
            log("  [dry-run] no writes. sample withdrawn ids: %s"
                % sorted([r["source_listing_id"] for r in records if r["status"] == "withdrawn"])[:10])
            return

        nL = nP = 0
        for i in range(0, len(records), 2000):
            a, b = write_batch(pg, records[i:i + 2000])
            nL += a
            nP += b
        n_swept = sweep_withdrawn(pg, active_ids, run_max_dt)
        log("  wrote scraper.listings rows=%d, price_history rows=%d, extra-withdrawn(sweep)=%d (%.1fs)"
            % (nL, nP, n_swept, time.perf_counter() - t0))
    finally:
        sq.close()
        pg.close()


def main():
    ap = argparse.ArgumentParser(description="myigloo -> scraper.listings + price_history (active-set diff)")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="build + report, NO writes")
    args = ap.parse_args()
    if not args.confirm:
        print(__doc__)
        print("\nRe-invoke with --confirm (add --dry-run for no writes).")
        return 0
    print("%s dry_run=%s" % (PROMOTER_VERSION, args.dry_run))
    run(args.dry_run)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
