"""promote_visir — Step 2d: parsed_visir -> scraper.listings_canonical with §4 cross-source dedup.

Reads local parsed_visir rows not yet promoted, decomposes visir's tegund_raw + tenure_signal
into TAXONOMY_v2 (category, tenure, sub_type), resolves price (Tilboð/junk rules), resolves
fastnum (§2.5 tiers vs public.properties), then runs §4 cross-source dedup against the existing
canonical rows (preloaded in-memory): tiered (fastnum / addr+price / geo+price), TENURE-MATCHED,
14-day window. visir wins over myigloo per §2.3-D source_priority (visir=1 > myigloo=3).

Dedup actions: insert_new | visir_wins (fold the existing non-visir row into secondary_source_ids,
visir becomes survivor of that canonical_id) | visir_loses (fold visir into an existing higher/equal
priority canonical row).

CLI:
    python promote_visir.py                       # docstring + exit 0
    python promote_visir.py --confirm             # full run (real Supabase writes)
    python promote_visir.py --confirm --limit N    # first N parsed rows (smoke)
    python promote_visir.py --confirm --dry-run    # decompose + dedup-plan, NO Supabase write

stdlib + psycopg2. normalize_address shared utility (commit b503981). Pooler quirk: a tx
defaults read-only -> SET TRANSACTION READ WRITE folded into each write (single round-trip).
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
from normalize_address import normalize_address   # noqa: E402

PROMOTER_VERSION = "visir_promote_v1"
VISIR_SOURCE_PRIORITY = 1
SOURCE_PRIORITY = {"visir": 1, "mbl": 2, "myigloo": 3, "evalue": 4}   # §2.3-D
JUNK_PRICE_MAX = 100
DEDUP_WINDOW_DAYS = 14
DEDUP_GEO_M = 50
PRICE_TOL = 0.05

# ── Decomposition: visir tegund_raw -> (category, sub_type). sub_type None = keyword-resolve.
TEGUND_TO_TYPE = {
    "fjölbýlishús": ("residential", "apartment"),
    "íbúðir":       ("residential", "apartment"),
    "íbúð":         ("residential", "apartment"),
    "hæð":          ("residential", "apartment"),
    "sérbýli":      ("residential", "house"),
    "einbýli":      ("residential", "house"),
    "einbýlishús":  ("residential", "house"),
    "raðhús":       ("residential", "townhouse"),
    "parhús":       ("residential", "townhouse"),
    "sumarhús":     ("residential", "summerhouse"),
    "sumarbústaður":("residential", "summerhouse"),
    "atvinnuhúsnæði": ("commercial", None),
    "lóð":  ("plot", None),
    "jörð": ("plot", None),
}
COMMERCIAL_KEYWORDS = [
    (["skrifstofa", "skrifstofuhúsnæði"], "office"),
    (["verslun", "verslunarhúsnæði"], "retail"),
    (["iðnaðar", "vörugeymsla", "lager", "verkstæði"], "industrial_warehouse"),
    (["hótel", "gistiheimili", "gistiþjónusta"], "hospitality"),
]
PLOT_KEYWORDS = [
    (["íbúðarhúsalóð", "íbúðarlóð"], "residential_plot"),
    (["sumarhúsalóð", "sumarbústaðaland"], "summer_house_plot"),
    (["atvinnulóð", "verslunarlóð"], "commercial_plot"),
    (["landbúnaðar", "tún", "akur", "jörð"], "agricultural"),
]

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
INSERT_COLUMNS = [c for c in CANONICAL_COLUMNS if c not in ("canonical_id", "geog")]


def _now():
    return datetime.now(timezone.utc).isoformat()


def haversine_m(lat1, lng1, lat2, lng2):
    R = 6371000.0
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lng2) - float(lng1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ─────────────────────────────────────────────────────── decomposition + price
def decompose(tegund_raw, tenure_signal, title, lysing):
    """Return (category, tenure, sub_type) per TAXONOMY_v2. Raises ValueError on unknown tegund."""
    key = (tegund_raw or "").lower().strip()
    if key not in TEGUND_TO_TYPE:
        raise ValueError("unknown tegund_raw: %r" % tegund_raw)
    cat, sub = TEGUND_TO_TYPE[key]
    if sub is None:
        text = ((title or "") + " " + (lysing or "")).lower()
        table = COMMERCIAL_KEYWORDS if cat == "commercial" else PLOT_KEYWORDS
        for kws, name in table:
            if any(kw in text for kw in kws):
                sub = name
                break
        if sub is None:
            sub = "mixed_use_other" if cat == "commercial" else "other_land"
    return (cat, tenure_signal, sub)


def resolve_price(price_amount, is_price_on_request, category):
    """Canonical price_amount, or None to skip. Commercial price-on-request -> 1
    ('verð samkvæmt tilboði', Step 1e convention); residential price-on-request -> skip."""
    if is_price_on_request:
        return 1 if category == "commercial" else None
    if price_amount is None or float(price_amount) == 0:
        return None
    if float(price_amount) <= JUNK_PRICE_MAX and category == "residential":
        return None
    return int(float(price_amount))


def derive_lease(tenure):
    """ck_rent_lease: rent rows need a non-NULL lease_term_class. visir carries no lease
    months -> 'unspecified'. sale -> NULL."""
    return "unspecified" if tenure == "rent" else None


# ─────────────────────────────────────────────────────── fastnum resolution (§2.5)
class PropsIndex:
    def __init__(self):
        self.present = set()
        self.by_addr = {}
        self.by_postnr = {}

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


def resolve_fastnum(p, idx):
    """(fastnum|None, confidence|None, method|None). visir fastnum_supplied is label-anchored
    (authoritative when present), gated on FK-existence in public.properties."""
    if p.get("fastnum_supplied"):
        if idx.exists(p["fastnum_supplied"]):
            return (int(p["fastnum_supplied"]), 1.0, "source_supplied")
        # stale/unknown registry id -> fall through
    pc = p.get("addr_postcode")
    if p.get("addr_street") and p.get("addr_number") and pc:
        addr = normalize_address("%s %s" % (p["addr_street"], p["addr_number"]))
        for tol, conf in ((0.05, 0.95), (0.15, 0.75)):
            m = idx.match(addr, pc, area=p.get("size_sqm"), tol=tol)
            if len(m) == 1:
                return (m[0], conf, "address_match")
        m = idx.match(addr, pc)
        if len(m) == 1:
            return (m[0], 0.55, "address_match")
    if p.get("lat") is not None and p.get("lng") is not None:
        fn = idx.geo_within(p["lat"], p["lng"], pc, 30)
        if fn is not None:
            return (fn, 0.55, "geo_match")
    return (None, None, None)


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


# ─────────────────────────────────────────────────────── §4 cross-source dedup
def _to_dt(v):
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


class CanonicalIndex:
    """In-memory snapshot of existing scraper.listings_canonical for §4 dedup matching.
    All match tiers are TENURE-MATCHED (architect decision: sale & rent of the same property
    are distinct canonical listings, never folded)."""
    def __init__(self):
        self.by_ft = {}        # (fastnum, tenure) -> [cand]
        self.by_addr = {}      # (addr_norm, tenure) -> [cand]
        self.by_tenure = {}    # tenure -> [cand]   (geo scan)

    @staticmethod
    def _price_ok(p_new, p_old):
        if p_new is None or p_old is None:
            return False
        lo, hi = float(p_new) * (1 - PRICE_TOL), float(p_new) * (1 + PRICE_TOL)
        return lo <= float(p_old) <= hi

    @staticmethod
    def _window_ok(fs_new, fs_old):
        if fs_new is None or fs_old is None:
            return False
        return abs((fs_new - fs_old).total_seconds()) / 86400.0 < DEDUP_WINDOW_DAYS

    def tier1(self, fastnum, tenure):
        if fastnum is None:
            return []
        return list(self.by_ft.get((int(fastnum), tenure), []))

    def tier2(self, addr_norm, tenure, price, fs):
        out = []
        for c in self.by_addr.get((addr_norm, tenure), []):
            if self._price_ok(price, c["price_amount"]) and self._window_ok(fs, c["first_seen_at"]):
                out.append(c)
        return out

    def tier3(self, lat, lng, tenure, price, fs):
        if lat is None or lng is None:
            return []
        out = []
        for c in self.by_tenure.get(tenure, []):
            if c["lat"] is None or c["lng"] is None:
                continue
            if (haversine_m(lat, lng, c["lat"], c["lng"]) <= DEDUP_GEO_M
                    and self._price_ok(price, c["price_amount"]) and self._window_ok(fs, c["first_seen_at"])):
                out.append(c)
        return out

    def add(self, cand):
        """Register a freshly-inserted/updated canonical row so later rows in the same run dedup against it."""
        t = cand["tenure"]
        if cand["fastnum"] is not None:
            self.by_ft.setdefault((int(cand["fastnum"]), t), []).append(cand)
        if cand["addr_norm"]:
            self.by_addr.setdefault((cand["addr_norm"], t), []).append(cand)
        self.by_tenure.setdefault(t, []).append(cand)


SIZE_DISAGREE_TOL = 0.10


def _reject_match(visir_row, candidate):
    """Universal §4 false-positive filters (apply across ALL tiers; general for Step 3+ too):
      Rule 1 — both have a fastnum AND they DIFFER -> different registered property.
      Rule 2 — both have size AND they differ by >10% -> different unit (multi-unit building).
    Returns (should_reject, reason)."""
    v_fn, c_fn = visir_row.get("fastnum"), candidate.get("fastnum")
    if v_fn and c_fn and int(v_fn) != int(c_fn):
        return (True, "fastnum_disagreement")
    v_sz, c_sz = visir_row.get("size_sqm"), candidate.get("size_sqm")
    if v_sz and c_sz:
        a, b = float(v_sz), float(c_sz)
        if max(a, b) > 0 and abs(a - b) / max(a, b) > SIZE_DISAGREE_TOL:
            return (True, "size_disagreement")
    return (False, "")


def _filter(cands, fastnum, size):
    vrow = {"fastnum": fastnum, "size_sqm": size}
    return [c for c in cands if not _reject_match(vrow, c)[0]]


PRICE_AGREE_TOL = 0.05
PRICE_SENTINEL = 1   # Tilboð / price-on-request placeholder (Step 1e convention)


def _has_corroborator(visir_row, candidate):
    """Rule 3 (commercial Tier-1): a building fastnum is 1:N over units, so a bare fastnum
    match is not enough for commercial — require at least one INFORMATIVE corroborator:
    size agreement (both >0, within 10%) OR price agreement (both non-sentinel, within 5%)."""
    v_sz, c_sz = visir_row.get("size_sqm"), candidate.get("size_sqm")
    if v_sz and c_sz and float(v_sz) > 0 and float(c_sz) > 0:
        a, b = float(v_sz), float(c_sz)
        if abs(a - b) / max(a, b) <= SIZE_DISAGREE_TOL:
            return True
    v_pr, c_pr = visir_row.get("price_amount"), candidate.get("price_amount")
    if v_pr and c_pr and int(v_pr) > PRICE_SENTINEL and int(c_pr) > PRICE_SENTINEL:
        a, b = float(v_pr), float(c_pr)
        if abs(a - b) / max(a, b) <= PRICE_AGREE_TOL:
            return True
    return False


def find_dedup_candidates(idx: CanonicalIndex, fastnum, tenure, addr_norm, price, lat, lng, fs,
                          size=None, category=None):
    """§4 tiered, tenure-matched, with universal fastnum/size reject filters (+ Rule 3
    commercial Tier-1 corroboration). First tier that survives wins (highest confidence first)."""
    def _commercial_ok(cands):
        # Rule 3: commercial needs an informative corroborator at WHATEVER tier matched
        # (a building fastnum is 1:N, and price=1 sentinel makes addr/geo+price tiers weak too).
        if category != "commercial":
            return cands
        vrow = {"fastnum": fastnum, "size_sqm": size, "price_amount": price}
        return [c for c in cands if _has_corroborator(vrow, c)]

    c = _commercial_ok(_filter(idx.tier1(fastnum, tenure), fastnum, size))
    if c:
        return c, "fastnum"
    if addr_norm and price is not None:
        c = _commercial_ok(_filter(idx.tier2(addr_norm, tenure, price, fs), fastnum, size))
        if c:
            return c, "addr"
    if lat is not None and lng is not None and price is not None:
        c = _commercial_ok(_filter(idx.tier3(lat, lng, tenure, price, fs), fastnum, size))
        if c:
            return c, "geo"
    return [], None


def select_action(candidates):
    """(action, target_canonical_id). visir(1) wins over myigloo(3)/mbl(2). visir_loses only
    against an equal/higher-priority existing row (e.g. another visir)."""
    if not candidates:
        return ("insert_new", None)
    target = sorted(candidates, key=lambda c: (SOURCE_PRIORITY.get(c["source"], 9), str(c["canonical_id"])))[0]
    if VISIR_SOURCE_PRIORITY < SOURCE_PRIORITY.get(target["source"], 9):
        return ("visir_wins", target)
    return ("visir_loses", target)


# ─────────────────────────────────────────────────────── canonical row builder
def _addr_text(p):
    s = " ".join(x for x in (p.get("addr_street"), p.get("addr_number")) if x).strip()
    return s or None


def _listing_title(p):
    return p.get("title") or _addr_text(p)


def build_canonical_row(p, cat, ten, sub, lease, price, fastnum, conf, method, fs, ls, now):
    return {
        "canonical_id": None,
        "source": "visir",
        "source_listing_id": str(p["source_listing_id"]),
        "url": "https://fasteignir.visir.is/property/%s" % p["source_listing_id"],
        "secondary_source_ids": [],
        "first_seen_at": fs, "last_seen_at": ls, "withdrawn_at": None, "is_active": True,
        "price_amount": price, "price_currency": p.get("price_currency") or "ISK",
        "listing_title": _listing_title(p), "lysing": p.get("lysing"),
        "category": cat, "tenure": ten, "sub_type": sub,
        "tegund_raw": p.get("tegund_raw") or "unknown", "lease_term_class": lease,
        "fastnum": fastnum, "lat": p.get("lat"), "lng": p.get("lng"), "geog": None,
        "area_sqm": p.get("size_sqm"), "rooms": p.get("rooms"),
        "bedrooms": p.get("bedrooms"), "bathrooms": p.get("bathrooms"),
        "addr_text": _addr_text(p), "addr_municipality": p.get("addr_city"),
        "addr_postcode": p.get("addr_postcode"), "deposit_isk": None, "available_from": None,
        "photos_json": p.get("photos_json") or "[]",
        "canonical_version": 1, "last_promoted_at": now,
        "surviving_parse_id": p.get("parse_id"), "surviving_source_priority": VISIR_SOURCE_PRIORITY,
        "fastnum_resolution_method": method, "fastnum_resolution_confidence": conf,
        "fastnum_resolution_at": now if method else None,
    }


# ─────────────────────────────────────────────────────── Supabase writes (pooler quirk)
def _row_vals(row):
    vals = []
    for c in INSERT_COLUMNS:
        v = row[c]
        if c == "photos_json":
            v = psycopg2.extras.Json(json.loads(v) if isinstance(v, str) else (v or []))
        elif c == "secondary_source_ids":
            v = list(v or [])
        vals.append(v)
    return vals


def upsert_new(pg, row):
    cols = ", ".join(INSERT_COLUMNS)
    ph = ", ".join(["%s"] * len(INSERT_COLUMNS))
    upd = ", ".join("%s = EXCLUDED.%s" % (c, c) for c in INSERT_COLUMNS
                    if c not in ("source", "source_listing_id", "first_seen_at", "canonical_version"))
    sql = ("INSERT INTO scraper.listings_canonical (%s) VALUES (%s) "
           "ON CONFLICT (source, source_listing_id) DO UPDATE SET %s, "
           "canonical_version = scraper.listings_canonical.canonical_version + 1" % (cols, ph, upd))
    cur = pg.cursor()
    cur.execute(b"SET TRANSACTION READ WRITE; " + cur.mogrify(sql, _row_vals(row)))
    pg.commit()


def update_visir_wins(pg, row, target):
    """visir becomes survivor of target's canonical_id; fold old source into secondary_source_ids."""
    fold = "%s:%s" % (target["source"], target["source_listing_id"])
    set_cols = [c for c in INSERT_COLUMNS
                if c not in ("secondary_source_ids", "first_seen_at", "canonical_version")]
    set_sql = ", ".join("%s = %%s" % c for c in set_cols)
    vals = []
    for c in set_cols:
        v = row[c]
        if c == "photos_json":
            v = psycopg2.extras.Json(json.loads(v) if isinstance(v, str) else (v or []))
        vals.append(v)
    sql = ("UPDATE scraper.listings_canonical SET " + set_sql + ", "
           "secondary_source_ids = array_append(secondary_source_ids, %s), "
           "canonical_version = canonical_version + 1 WHERE canonical_id = %s")
    vals = vals + [fold, target["canonical_id"]]
    cur = pg.cursor()
    cur.execute(b"SET TRANSACTION READ WRITE; " + cur.mogrify(sql, vals))
    pg.commit()


def update_visir_loses(pg, row, target):
    """Fold visir listing into the existing survivor's secondary_source_ids."""
    fold = "visir:%s" % row["source_listing_id"]
    sql = ("UPDATE scraper.listings_canonical SET "
           "secondary_source_ids = array_append(secondary_source_ids, %s), "
           "last_seen_at = %s, canonical_version = canonical_version + 1 "
           "WHERE canonical_id = %s")
    cur = pg.cursor()
    cur.execute(b"SET TRANSACTION READ WRITE; "
                + cur.mogrify(sql, [fold, row["last_seen_at"], target["canonical_id"]]))
    pg.commit()


def preload_canonical(pg) -> CanonicalIndex:
    idx = CanonicalIndex()
    cur = pg.cursor()
    cur.execute("SELECT canonical_id, source, source_listing_id, first_seen_at, tenure, "
                "fastnum, price_amount, addr_text, lat, lng, area_sqm FROM scraper.listings_canonical")
    for cid, src, slid, fs, tenure, fastnum, price, addr_text, lat, lng, area in cur.fetchall():
        cand = {"canonical_id": cid, "source": src, "source_listing_id": slid,
                "first_seen_at": _to_dt(fs), "tenure": tenure, "fastnum": fastnum,
                "price_amount": price, "addr_norm": normalize_address(addr_text or "") or None,
                "lat": float(lat) if lat is not None else None,
                "lng": float(lng) if lng is not None else None,
                "size_sqm": float(area) if area is not None else None}
        idx.add(cand)
    return idx


class _Enc(json.JSONEncoder):
    def default(self, o):
        return str(o) if isinstance(o, Decimal) else super().default(o)


# ─────────────────────────────────────────────────────────────────────── run
def run(dry_run, limit, sq, pg, log=print):
    sq.row_factory = sqlite3.Row
    q = "SELECT * FROM parsed_visir WHERE promoted_to_canonical_at IS NULL ORDER BY parse_id"
    if limit:
        q += " LIMIT %d" % int(limit)
    parsed = [dict(r) for r in sq.execute(q)]
    log("=== promote_visir %s: %d parsed rows ===" % ("DRY-RUN" if dry_run else "FULL", len(parsed)))

    postcodes = {p["addr_postcode"] for p in parsed if p["addr_postcode"]}
    fastnums = [p["fastnum_supplied"] for p in parsed if p["fastnum_supplied"] is not None]
    props = preload_props(pg, postcodes, fastnums)
    canon = preload_canonical(pg)
    log("preloaded: props present=%d addr_keys=%d | canonical rows by_tenure=%s"
        % (len(props.present), len(props.by_addr),
           {k: len(v) for k, v in canon.by_tenure.items()}))
    if not dry_run:
        pg.rollback()   # close preload read-tx so the first write-tx SET READ WRITE is first stmt

    # first_seen per visir listing (min detail fetched_at)
    seen = {row[0]: (_to_dt(row[1]), _to_dt(row[2])) for row in sq.execute(
        "SELECT source_listing_id, MIN(fetched_at), MAX(fetched_at) FROM raw_fetches "
        "WHERE source='visir' AND fetch_kind='detail' GROUP BY source_listing_id")}

    stats = Counter()
    t0 = time.perf_counter()
    for p in parsed:
        try:
            cat, ten, sub = decompose(p.get("tegund_raw"), p.get("tenure_signal"),
                                      p.get("title"), p.get("lysing"))
        except ValueError as e:
            stats["unknown_tegund"] += 1
            log("WARN %s parse_id=%s" % (e, p["parse_id"]))
            continue
        price = resolve_price(p.get("price_amount"), p.get("is_price_on_request"), cat)
        if price is None:
            stats["skipped_junk"] += 1
            continue
        if cat == "plot" and p.get("size_sqm") is None:
            stats["skipped_plot_no_area"] += 1     # ck_plot_area would reject
            continue
        lease = derive_lease(ten)
        fastnum, conf, method = resolve_fastnum(p, props)
        now = _now()
        fs, ls = seen.get(str(p["source_listing_id"]), (_to_dt(now), _to_dt(now)))
        row = build_canonical_row(p, cat, ten, sub, lease, price, fastnum, conf, method, fs, ls, now)

        addr_norm = normalize_address(row["addr_text"] or "") or None
        cands, tier = find_dedup_candidates(canon, fastnum, ten, addr_norm, price,
                                            row["lat"], row["lng"], fs, p.get("size_sqm"), category=cat)
        action, target = select_action(cands)
        stats["action_" + action] += 1
        if tier:
            stats["dedup_tier_" + tier] += 1

        if dry_run:
            stats["promoted"] += 1
            stats[method or "unresolved"] += 1
            continue
        try:
            if action == "insert_new":
                upsert_new(pg, row)
            elif action == "visir_wins":
                update_visir_wins(pg, row, target)
            elif action == "visir_loses":
                update_visir_loses(pg, row, target)
            sq.execute("UPDATE parsed_visir SET promoted_to_canonical_at=? WHERE parse_id=?",
                       (now, p["parse_id"]))
            sq.commit()
            # v1: dedup against the STATIC preloaded snapshot only (myigloo + prior runs).
            # Within-run visir↔visir folding is deferred — avoids placeholder-uuid writes and
            # the tier-2 false-positive risk of folding two distinct units in one building.
            stats["promoted"] += 1
            stats[method or "unresolved"] += 1
        except Exception as e:
            pg.rollback()
            stats["failed"] += 1
            log("FAILED parse_id=%s id=%s: %s" % (p["parse_id"], p["source_listing_id"], repr(e)[:180]))

    log("\n=== SUMMARY (%.1fs) ===" % (time.perf_counter() - t0))
    for k in ("promoted", "action_insert_new", "action_visir_wins", "action_visir_loses",
              "dedup_tier_fastnum", "dedup_tier_addr", "dedup_tier_geo",
              "source_supplied", "address_match", "geo_match", "unresolved",
              "skipped_junk", "skipped_plot_no_area", "unknown_tegund", "failed"):
        if stats.get(k):
            log("  %-22s %d" % (k, stats[k]))
    return stats


def main():
    ap = argparse.ArgumentParser(description="promote parsed_visir -> scraper.listings_canonical (§4 dedup)")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    if not args.confirm:
        print(__doc__)
        print("\nRe-invoke with --confirm (add --dry-run for no writes, --limit N for a smoke run).")
        return 0
    sq = sqlite3.connect(str(get_raw_db_path("visir")))
    dsn = open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read().strip()
    pg = psycopg2.connect(dsn)
    if args.dry_run:
        pg.set_session(readonly=True, autocommit=True)
    print("promoter_version=%s dry_run=%s limit=%s" % (PROMOTER_VERSION, args.dry_run, args.limit))
    try:
        run(args.dry_run, args.limit, sq, pg)
    finally:
        sq.close(); pg.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
