"""promote_myigloo — Step 1e: parsed_myigloo -> scraper.listings_canonical (Supabase).

Reads local parsed_myigloo rows not yet promoted, applies the TAXONOMY_v2
lookup (listing_type_tag -> category/tenure/sub_type), derives lease_term_class,
resolves fastnum (Tier-1 source_supplied w/ FK-safety -> Tier-2a/2b/2c address+
area -> Tier-3 geo), builds the 39-col scraper.listings_canonical row, and
UPSERTs to Supabase. --dry-run builds + prints rows with NO Supabase write.

stdlib + psycopg2. normalize_address shared utility from commit b503981.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path        # noqa: E402
from normalize_address import normalize_address   # noqa: E402  (shared, b503981)

PROMOTER_VERSION = "0.1.0"
MYIGLOO_SOURCE_PRIORITY = 3   # visir(1) > mbl(2) > myigloo(3) > evalue(4)  (§2.3-D)
JUNK_PRICE_MAX = 100          # rent <= 100 kr = test/junk row -> skip-with-log

# Architect-locked lookup (Step 1e Phase 1): listing_type_tag -> (category, tenure, sub_type)
TAXONOMY_LOOKUP = {
    "apartment":          ("residential", "rent", "apartment"),
    "entire_floor":       ("residential", "rent", "apartment"),
    "single_family_home": ("residential", "rent", "house"),
    "townhouse":          ("residential", "rent", "townhouse"),
    "double_townhouse":   ("residential", "rent", "townhouse"),
    "studio":             ("residential", "rent", "studio"),
    "room":               ("residential", "rent", "room"),
    "storage":            ("commercial",  "rent", "industrial_warehouse"),
    "garage":             ("commercial",  "rent", "mixed_use_other"),
    "cottage":            ("residential", "rent", "summerhouse"),
    "office":             ("commercial",  "rent", "office"),
    "retail":             ("commercial",  "rent", "retail"),
    "warehouse":          ("commercial",  "rent", "industrial_warehouse"),
    "bnb":                ("commercial",  "rent", "hospitality"),
    "apartment_hotel":    ("commercial",  "rent", "hospitality"),
}
# Only residential `room` is unresolvable here — storage/garage were mapped to commercial.
UNRESOLVABLE_SUB_TYPES = {"room"}

CANONICAL_COLUMNS = [
    "canonical_id", "source", "source_listing_id", "url", "secondary_source_ids",
    "first_seen_at", "last_seen_at", "withdrawn_at", "is_active", "price_amount",
    "price_currency", "listing_title", "lysing", "category", "tenure", "sub_type",
    "tegund_raw", "lease_term_class", "fastnum", "lat", "lng", "geog", "area_sqm",
    "rooms", "bedrooms", "bathrooms", "addr_text", "addr_municipality", "addr_postcode",
    "deposit_isk", "available_from", "photos_json", "canonical_version", "last_promoted_at",
    "surviving_parse_id", "surviving_source_priority", "fastnum_resolution_method",
    "fastnum_resolution_confidence", "fastnum_resolution_at",
]
# Inserted columns (canonical_id default uuid, geog generated from lat/lng).
INSERT_COLUMNS = [c for c in CANONICAL_COLUMNS if c not in ("canonical_id", "geog")]


def _now():
    return datetime.now(timezone.utc).isoformat()


def derive_lease(months):
    """§3.2: <6 short_term, >=6 long_term, NULL -> 'unspecified' (ck_rent_lease forbids NULL on rent)."""
    if months is None:
        return "unspecified"
    return "short_term" if int(months) < 6 else "long_term"


def _is_junk(parsed_row, category):
    """Skip a parsed row at promotion if:
      - price_amount is None or 0  (cannot insert per ck_price_pos)
      - price_amount <= JUNK_PRICE_MAX AND category == 'residential'  (genuine junk;
        Icelandic residential rents always exceed 100 ISK)
    Otherwise PROMOTE. Notably: commercial listings with price_amount in 1-1000 ISK
    are 'verð samkvæmt tilboði' (price-on-request) per myigloo agency convention —
    promoted as-is, downstream UI renders accordingly. See DECISIONS.md Step 1e entry.
    """
    price = parsed_row.get("price_amount")
    if price is None or float(price) == 0:
        return True
    if float(price) <= JUNK_PRICE_MAX and category == "residential":
        return True
    return False


def _listing_title(p):
    if p.get("title"):
        return p["title"]
    s = " ".join(x for x in (p.get("addr_street"), p.get("addr_number")) if x).strip()
    return s or None


def _addr_text(p):
    s = " ".join(x for x in (p.get("addr_street"), p.get("addr_number")) if x).strip()
    return s or None


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lng2) - float(lng1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class PropsIndex:
    """In-memory candidate slice of public.properties for fast resolution."""
    def __init__(self):
        self.present = set()      # fastnums that exist (FK-safety for Tier-1)
        self.by_addr = {}         # (heimilisfang_norm, postnr_str) -> [(fastnum, einflm, lat, lng)]
        self.by_postnr = {}       # postnr_str -> [(fastnum, lat, lng)]

    def exists(self, fastnum):
        return int(fastnum) in self.present

    def match(self, addr_norm, postnr, area=None, tol=None):
        cands = self.by_addr.get((addr_norm, str(postnr)), [])
        if area is None or tol is None:
            return [c[0] for c in cands]
        lo, hi = float(area) * (1 - tol), float(area) * (1 + tol)
        return [c[0] for c in cands if c[1] is not None and lo <= float(c[1]) <= hi]

    def geo_within(self, lat, lng, postnr, radius_m=30):
        best, bd = None, float(radius_m)
        for fn, plat, plng in self.by_postnr.get(str(postnr), []):
            if plat is None or plng is None:
                continue
            d = haversine_m(lat, lng, plat, plng)
            if d <= bd:
                bd, best = d, fn
        return best


def resolve_fastnum(p, idx, sub_type):
    """Returns (fastnum|None, confidence|None, method|None). Method is the
    scraper.fastnum_res_enum value (NOT a tier label)."""
    # Tier 1 — source_supplied, gated on FK-existence (51/756 landreg ids miss properties)
    if p.get("landreg_source") == "landreg" and p.get("fastnum_supplied"):
        if idx.exists(p["fastnum_supplied"]):
            return (int(p["fastnum_supplied"]), 1.0, "source_supplied")
        # else: stale/unknown registry id -> fall through to address-match
    if sub_type in UNRESOLVABLE_SUB_TYPES:
        return (None, None, "unresolvable_by_design")
    pc = p.get("addr_postcode")
    if p.get("addr_street") and p.get("addr_number") and pc:
        addr = normalize_address("%s %s" % (p["addr_street"], p["addr_number"]))
        for tol, conf in ((0.05, 0.95), (0.15, 0.75)):          # Tier 2a / 2b
            m = idx.match(addr, pc, area=p.get("size_sqm"), tol=tol)
            if len(m) == 1:
                return (m[0], conf, "address_match")
        m = idx.match(addr, pc)                                  # Tier 2c
        if len(m) == 1:
            return (m[0], 0.55, "address_match")
    if p.get("lat") is not None and p.get("lng") is not None:    # Tier 3
        fn = idx.geo_within(p["lat"], p["lng"], pc, 30)
        if fn is not None:
            return (fn, 0.55, "geo_match")
    return (None, None, None)                                    # unresolved (method NULL -> retry §2.5-C)


def build_canonical_row(p, cat, ten, sub, lease, fastnum, conf, method, first_seen, last_seen, now):
    return {
        "canonical_id": None,
        "source": "myigloo",
        "source_listing_id": str(p["source_listing_id"]),
        "url": "https://myigloo.is/listings/%s" % p["source_listing_id"],
        "secondary_source_ids": [],
        "first_seen_at": first_seen,
        "last_seen_at": last_seen,
        "withdrawn_at": None,
        "is_active": True,
        "price_amount": p.get("price_amount"),
        "price_currency": p.get("price_currency") or "ISK",
        "listing_title": _listing_title(p),
        "lysing": p.get("lysing"),
        "category": cat,
        "tenure": ten,
        "sub_type": sub,
        "tegund_raw": p.get("tegund_raw") or p.get("listing_type_tag") or "unknown",
        "lease_term_class": lease,
        "fastnum": fastnum,
        "lat": p.get("lat"),
        "lng": p.get("lng"),
        "geog": None,
        "area_sqm": p.get("size_sqm"),
        "rooms": p.get("rooms"),
        "bedrooms": p.get("bedrooms"),
        "bathrooms": p.get("bathrooms"),
        "addr_text": _addr_text(p),
        "addr_municipality": p.get("addr_city"),
        "addr_postcode": p.get("addr_postcode"),
        "deposit_isk": p.get("deposit_isk"),
        "available_from": p.get("available_from"),
        "photos_json": p.get("photos_json") or "[]",
        "canonical_version": 1,
        "last_promoted_at": now,
        "surviving_parse_id": p.get("parse_id"),
        "surviving_source_priority": MYIGLOO_SOURCE_PRIORITY,
        "fastnum_resolution_method": method,
        "fastnum_resolution_confidence": conf,
        "fastnum_resolution_at": now,
    }


def preload_props(pg, postcodes, fastnums) -> PropsIndex:
    idx = PropsIndex()
    cur = pg.cursor()
    if fastnums:
        cur.execute("SELECT fastnum FROM public.properties WHERE fastnum = ANY(%s)", (list(fastnums),))
        idx.present = set(r[0] for r in cur.fetchall())
    pcs = sorted({int(x) for x in postcodes if x and str(x).isdigit()})
    if pcs:
        cur.execute("SELECT fastnum, heimilisfang, postnr, einflm, lat, lng "
                    "FROM public.properties WHERE postnr = ANY(%s)", (pcs,))
        for fn, heim, pn, einflm, lat, lng in cur.fetchall():
            key = (normalize_address(heim or ""), str(pn))
            idx.by_addr.setdefault(key, []).append((fn, einflm, lat, lng))
            idx.by_postnr.setdefault(str(pn), []).append((fn, lat, lng))
    return idx


def _upsert(pg, row):
    vals = []
    for c in INSERT_COLUMNS:
        v = row[c]
        if c == "photos_json":
            v = psycopg2.extras.Json(json.loads(v) if isinstance(v, str) else (v or []))
        vals.append(v)
    cols = ", ".join(INSERT_COLUMNS)
    ph = ", ".join(["%s"] * len(INSERT_COLUMNS))
    upd = ", ".join("%s = EXCLUDED.%s" % (c, c) for c in INSERT_COLUMNS
                    if c not in ("source", "source_listing_id", "first_seen_at", "canonical_version"))
    sql = ("INSERT INTO scraper.listings_canonical (%s) VALUES (%s) "
           "ON CONFLICT (source, source_listing_id) DO UPDATE SET %s, "
           "canonical_version = scraper.listings_canonical.canonical_version + 1" % (cols, ph, upd))
    cur = pg.cursor()
    # The transaction pooler may default a tx to read-only; force READ WRITE as the
    # first statement of this tx (folded in via mogrify to keep it a single round-trip).
    cur.execute(b"SET TRANSACTION READ WRITE; " + cur.mogrify(sql, vals))
    pg.commit()


class _Enc(json.JSONEncoder):
    def default(self, o):
        return str(o) if isinstance(o, Decimal) else super().default(o)


def run(dry_run, sq, pg, log=print):
    sq.row_factory = sqlite3.Row
    parsed = [dict(r) for r in sq.execute("SELECT * FROM parsed_myigloo WHERE promoted_to_canonical_at IS NULL")]
    log("=== promote_myigloo: %s (%d parsed rows) ===" % ("DRY-RUN" if dry_run else "FULL", len(parsed)))
    postcodes = {p["addr_postcode"] for p in parsed if p["addr_postcode"]}
    fastnums = [p["fastnum_supplied"] for p in parsed if p["fastnum_supplied"] is not None]
    idx = preload_props(pg, postcodes, fastnums)
    log("preloaded properties: present_fastnums=%d, addr_keys=%d, postnr_buckets=%d"
        % (len(idx.present), len(idx.by_addr), len(idx.by_postnr)))
    if not dry_run:
        pg.rollback()  # close preload's read-tx so the first write-tx can SET TRANSACTION READ WRITE
    seen = {row[0]: (row[1], row[2]) for row in sq.execute(
        "SELECT source_listing_id, MIN(fetched_at), MAX(fetched_at) FROM raw_fetches "
        "WHERE source='myigloo' AND fetch_kind='detail' GROUP BY source_listing_id")}

    stats = Counter()
    comm1_samples = []
    t0 = time.perf_counter()
    for p in parsed:
        tag = p["listing_type_tag"]
        if tag not in TAXONOMY_LOOKUP:
            stats["unknown_tag"] += 1
            log("WARN unknown listing_type_tag=%r parse_id=%s" % (tag, p["parse_id"]))
        cat, ten, sub = TAXONOMY_LOOKUP.get(tag, ("other", "rent", "other"))
        if _is_junk(p, cat):
            stats["skipped_junk"] += 1
            log("skip junk parse_id=%s price=%s cat=%s" % (p["parse_id"], p["price_amount"], cat))
            continue
        lease = derive_lease(p["contract_min_months"])
        fastnum, conf, method = resolve_fastnum(p, idx, sub)
        now = _now()
        fs, ls = seen.get(str(p["source_listing_id"]), (now, now))
        row = build_canonical_row(p, cat, ten, sub, lease, fastnum, conf, method, fs, ls, now)
        if dry_run:
            stats[method or "unresolved"] += 1
            stats["promoted"] += 1
            if cat == "commercial" and float(p.get("price_amount") or 0) == 1 and len(comm1_samples) < 3:
                comm1_samples.append(row)
        else:
            try:
                _upsert(pg, row)
                sq.execute("UPDATE parsed_myigloo SET promoted_to_canonical_at=? WHERE parse_id=?",
                           (now, p["parse_id"]))
                sq.commit()
                stats[method or "unresolved"] += 1
                stats["promoted"] += 1
            except Exception as e:
                pg.rollback()
                stats["failed"] += 1
                log("FAILED parse_id=%s id=%s: %s" % (p["parse_id"], p["source_listing_id"], repr(e)[:160]))

    if dry_run:
        log("\n--- up to 3 commercial price=1 ('verð samkvæmt tilboði') canonical rows ---")
        for r in comm1_samples:
            print(json.dumps(r, ensure_ascii=False, indent=2, cls=_Enc))
    log("\n=== SUMMARY (%.1fs) ===" % (time.perf_counter() - t0))
    for k in ("promoted", "source_supplied", "address_match", "geo_match",
              "unresolvable_by_design", "unresolved", "skipped_junk", "unknown_tag", "failed"):
        log("  %-22s %d" % (k, stats.get(k, 0)))
    return stats


def main():
    ap = argparse.ArgumentParser(description="promote parsed_myigloo -> scraper.listings_canonical")
    ap.add_argument("--dry-run", action="store_true", help="build + print rows, NO Supabase write")
    args = ap.parse_args()
    sq = sqlite3.connect(str(get_raw_db_path("myigloo")))
    dsn = open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read().strip()
    pg = psycopg2.connect(dsn)
    if args.dry_run:
        pg.set_session(readonly=True, autocommit=True)   # belt-and-suspenders: no writes in dry-run
    print("promoter_version=%s  dry_run=%s" % (PROMOTER_VERSION, args.dry_run))
    try:
        run(args.dry_run, sq, pg)
    finally:
        sq.close(); pg.close()


if __name__ == "__main__":
    main()
