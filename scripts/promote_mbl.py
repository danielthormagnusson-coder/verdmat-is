"""promote_mbl — Step 3d: parsed_mbl_{sale,rent} -> scraper.listings_canonical.

Promotes the mbl corpus (the third source) into the canonical layer, modelled on
promote_visir.py but with the four mbl-specific decision points from the Step 3d design
(D:\\verdmat-is\\STEP_3D_DESIGN_v1_draft.md, locked in docs/DECISIONS.md 2026-06-15):

  DP1 foreign filter  -> runs BEFORE fastnum resolution (truncation-collision guard).
                         Icelandic-override: a domestic signal (postfang in 101..902 OR
                         lat in 63..67.5) keeps the row even if the parser flagged it
                         foreign or it carries a sentinel postcode (1053/1000). Rescues
                         the 21 Vesturvin rows the parser leaked (DECISIONS 2026-06-15).
  DP2 tenure cascade  -> sale table only (rent table is rent by definition). is_negotiable=0
                         => sale (a price is the strongest tenure signal); is_negotiable=1
                         resolves via a directional regex in lysing/lysing_text.
  DP3 price           -> verd>0 => (verd, is_price_on_request=False); verd=0 => (1, True)
                         (capture-mandate sentinel; Lota 1 is all priced so verd=0 never hits).
  DP4 dedup           -> tiered, tenure-matched, against the STATIC preloaded canonical
                         snapshot (visir + myigloo). Tenure-specific source_priority:
                         sale  visir(1) > mbl(2) > myigloo(3);
                         rent  visir(1) > myigloo(2) > mbl(3).

mbl encoding: fastano = fastnum*10^k + matshluti. 7-digit -> (matshluti=0, k=1);
8-digit -> (matshluti=fastano%10, k=10); 9-digit -> (matshluti=fastano%100, k=100);
6-/10-digit edge -> (matshluti=NULL, k=NULL, addr/geo resolution). The 7-digit truncation
fastnum = fastano//k is the FK into public.properties; matshluti_unit_id + source_raw_fastnum
are preserved per the migration. NOTE: the v1 static dedup keys Tier-1 on the bare fastnum
(existing canonical rows carry matshluti_unit_id=NULL); within-run mbl<->mbl folding on
(fastnum, matshluti) is DEFERRED to post-Lota-1 validation (design Q4). The column is written
now for the index, comparables, and that future folding.

CLI:
    python -m scripts.promote_mbl                                          # docstring + exit 0
    python -m scripts.promote_mbl --confirm --slice priced --table sale     # full run
    python -m scripts.promote_mbl --confirm --dry-run --slice priced --table sale --limit 200
    --slice {priced|negotiable}  priced = is_negotiable=0 (verd>0); negotiable = is_negotiable=1.
    --table {sale|rent}          which parsed_mbl_* table to promote.

stdlib + psycopg2. normalize_address shared utility. Pooler quirk: a tx defaults read-only ->
'SET TRANSACTION READ WRITE' is folded into each write as the FIRST statement (single
round-trip via mogrify). Per-row commit (pg + sqlite) => watermark resume is free.
"""
from __future__ import annotations

import argparse
import json
import math
import re
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
from scraper_paths import get_scraper_data_dir       # noqa: E402
from normalize_address import normalize_address       # noqa: E402

PROMOTER_VERSION = "mbl_promote_v1"

# Tenure-specific source_priority (§2.3-D; spec text updated separately in Stage 9).
# Lower = stronger. mbl is 2 for sale (cleaner SSR than myigloo) but 3 for rent
# (myigloo is rent-specialised with structured lease terms; mbl rent is secondary).
SOURCE_PRIORITY_SALE = {"visir": 1, "mbl": 2, "myigloo": 3, "evalue": 4}
SOURCE_PRIORITY_RENT = {"visir": 1, "myigloo": 2, "mbl": 3, "evalue": 4}

JUNK_PRICE_MAX = 100
POR_PRICE_MAX = 1   # rent listings with price <= 1 ISK are commercial-rent-on-request, not
                    # residential junk (Stage 8 finding 2026-06-16; residential rent is never 1 ISK).
DEDUP_WINDOW_DAYS = 14
DEDUP_GEO_M = 50
PRICE_TOL = 0.05
SIZE_DISAGREE_TOL = 0.10
PRICE_AGREE_TOL = 0.05
PRICE_SENTINEL = 1

# Icelandic-domestic override thresholds (DP1).
IS_POSTCODE_LO, IS_POSTCODE_HI = 101, 902
IS_LAT_LO, IS_LAT_HI = 63.0, 67.5

# Directional tenure regexes (DP2). NB: inflected "leigu" (dative), NOT the stem "leiga" —
# the stem under-matched 47 vs 1014 in the first probe (DECISIONS 2026-06-15).
RENT_REGEX = re.compile(r"til leigu|kynnir.{0,40}leigu|leigist", re.IGNORECASE)
SALE_REGEX = re.compile(r"til s[oö]lu|einkas[oö]lu|teki[ðd] [ií] s[oö]lu|tilbo[ðd].{0,20}eign", re.IGNORECASE)

# mbl teg_eign -> (category, sub_type). sub_type None => keyword-resolve (commercial only).
TEG_EIGN_MAP = {
    "fjolb":    ("residential", "apartment"),
    "haedir":   ("residential", "apartment"),
    "einb":     ("residential", "house"),
    "radpar":   ("residential", "townhouse"),
    "sumarhus": ("residential", "summerhouse"),
    "jord":     ("plot", "agricultural"),
    "atv":      ("commercial", None),
    "hesthus":  ("other", "equestrian"),
    "annad":    ("other", "other"),
}
COMMERCIAL_KEYWORDS = [
    (["skrifstofa", "skrifstofuhúsnæði"], "office"),
    (["verslun", "verslunarhúsnæði"], "retail"),
    (["iðnaðar", "vörugeymsla", "lager", "verkstæði"], "industrial_warehouse"),
    (["hótel", "gistiheimili", "gistiþjónusta"], "hospitality"),
]

# mbl public listing URL. mbl/fasteignir is a client-routed SPA (no server-rendered detail
# page, no sitemap); routes verified against the SPA bundle router (2026-06-15):
#   sale detail  -> fasteign/:id/            => /fasteignir/fasteign/<id>/
#   rent detail  -> leiga/leigueign/:id/     => /fasteignir/leiga/leigueign/<id>/
URL_SALE = "https://www.mbl.is/fasteignir/fasteign/%s/"
URL_RENT = "https://www.mbl.is/fasteignir/leiga/leigueign/%s/"

CANONICAL_COLUMNS = [
    "canonical_id", "source", "source_listing_id", "url", "secondary_source_ids",
    "first_seen_at", "last_seen_at", "withdrawn_at", "is_active", "price_amount",
    "price_currency", "listing_title", "lysing", "category", "tenure", "sub_type",
    "tegund_raw", "lease_term_class", "fastnum", "lat", "lng", "geog", "area_sqm",
    "rooms", "bedrooms", "bathrooms", "addr_text", "addr_municipality", "addr_postcode",
    "deposit_isk", "available_from", "photos_json", "canonical_version", "last_promoted_at",
    "surviving_parse_id", "surviving_source_priority", "fastnum_resolution_method",
    "fastnum_resolution_confidence", "fastnum_resolution_at",
    # Step 3d additions:
    "matshluti_unit_id", "source_raw_fastnum", "is_price_on_request",
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


def _to_dt(v):
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


def source_priority(source, tenure):
    table = SOURCE_PRIORITY_RENT if tenure == "rent" else SOURCE_PRIORITY_SALE
    return table.get(source, 9)


# ───────────────────────────────────── DP1: foreign filter (+ Icelandic override)
def _has_icelandic_signal(common):
    """A strong domestic signal that overrides a foreign flag / sentinel postcode."""
    pc = common.get("postcode")
    try:
        if pc is not None and IS_POSTCODE_LO <= int(pc) <= IS_POSTCODE_HI:
            return True
    except (TypeError, ValueError):
        pass
    lat = common.get("lat")
    try:
        if lat is not None and IS_LAT_LO <= float(lat) <= IS_LAT_HI:
            return True
    except (TypeError, ValueError):
        pass
    return False


def foreign_filter(common):
    """True => exclude as foreign. The parser's is_foreign is the base; a domestic signal
    rescues mislabelled rows (the Vesturvin leak). Runs BEFORE resolution so a foreign
    8-/9-digit fastano cannot truncate into the properties range and collide."""
    if _has_icelandic_signal(common):
        return False
    return bool(common.get("is_foreign"))


# ───────────────────────────────────── DP2: tenure cascade (sale table only)
def tenure_cascade(common, stats=None):
    """sale | rent for a parsed_mbl_sale row. is_negotiable=0 (price present) => sale.
    is_negotiable=1 (verd=0) => directional regex over lysing/lysing_text; default sale."""
    if not common.get("is_negotiable"):
        if stats is not None:
            stats["tenure_sale_priced"] += 1
        return "sale"
    text = common.get("lysing") or ""
    if RENT_REGEX.search(text):
        if stats is not None:
            stats["tenure_rent_from_leigu"] += 1
        return "rent"
    if SALE_REGEX.search(text):
        if stats is not None:
            stats["tenure_sale_from_solu"] += 1
        return "sale"
    if stats is not None:
        stats["tenure_sale_fallback"] += 1
    return "sale"


# ───────────────────────────────────── fastano decomposition + fastnum resolution
def decompose_fastano(fastano):
    """(matshluti_unit_id, source_raw_fastnum, k). Truncation fastnum = fastano // k.
    7-digit -> (0, raw, 1); 8-digit -> (raw%10, raw, 10); 9-digit -> (raw%100, raw, 100);
    6-/10-digit + short junk edge -> (None, raw, None) (no *10^k fit; addr/geo resolves)."""
    if fastano is None:
        return (None, None, None)
    n = int(fastano)
    L = len(str(abs(n)))
    if L == 7:
        return (0, n, 1)
    if L == 8:
        return (n % 10, n, 10)
    if L == 9:
        return (n % 100, n, 100)
    return (None, n, None)


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


def resolve_fastnum(common, derived_fastnum, idx):
    """(fastnum|None, confidence|None, method|None). §2.5 cascade:
    source_supplied (derived 7-digit truncation, FK-gated) -> address_match -> geo_match."""
    if derived_fastnum is not None and idx.exists(derived_fastnum):
        return (int(derived_fastnum), 1.0, "source_supplied")
    pc = common.get("postcode")
    addr = common.get("addr_text")
    if addr and pc:
        an = normalize_address(addr)
        if an:
            for tol, conf in ((0.05, 0.95), (0.15, 0.75)):
                m = idx.match(an, pc, area=common.get("area"), tol=tol)
                if len(m) == 1:
                    return (m[0], conf, "address_match")
            m = idx.match(an, pc)
            if len(m) == 1:
                return (m[0], 0.55, "address_match")
    if common.get("lat") is not None and common.get("lng") is not None:
        fn = idx.geo_within(common["lat"], common["lng"], pc, 30)
        if fn is not None:
            return (fn, 0.55, "geo_match")
    return (None, None, None)


def preload_props(pg, postcodes, fastnums) -> PropsIndex:
    idx = PropsIndex()
    cur = pg.cursor()
    fns = sorted({int(x) for x in fastnums if x is not None})
    if fns:
        cur.execute("SELECT fastnum FROM public.properties WHERE fastnum = ANY(%s)", (fns,))
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


# ───────────────────────────────────── DP3: price
def resolve_price(verd, table):
    """(price_amount, is_price_on_request).
    verd=0/None     => (1, True)  standard negotiable sentinel ('samkvæmt tilboði').
    rent & verd<=1  => (1, True)  commercial-rent-on-request (Stage 8 finding 2026-06-16;
                                  residential rent is never 1 ISK, so price<=1 is a reliable
                                  commercial-by-tender signal in the priced rent slice).
    otherwise       => (int(verd), False)."""
    if verd is None or float(verd) == 0:
        return (PRICE_SENTINEL, True)
    if table == "rent" and float(verd) <= POR_PRICE_MAX:
        return (PRICE_SENTINEL, True)
    return (int(float(verd)), False)


# ───────────────────────────────────── category / sub_type
def decompose_commercial_sub_type(text, teg_eign=None):
    """Keyword-resolve a commercial sub_type from the listing text; fallback mixed_use_other.
    Shared by atv-sale (decompose_category) and commercial-rent-on-request (Stage 8)."""
    low = (text or "").lower()
    for kws, name in COMMERCIAL_KEYWORDS:
        if any(kw in low for kw in kws):
            return name
    return "mixed_use_other"


def decompose_category(teg_eign, tenure, text=""):
    """(category, sub_type). teg_eign drives category; commercial sub_type is keyword-resolved
    from the listing text (fallback mixed_use_other), matching the visir promoter. tenure does
    not change category (commercial can be sale or rent)."""
    key = (teg_eign or "").lower().strip()
    cat, sub = TEG_EIGN_MAP.get(key, ("other", "other"))
    if sub is None:  # commercial keyword-resolve
        sub = decompose_commercial_sub_type(text, teg_eign)
    return (cat, sub)


def derive_lease(tenure):
    """ck_rent_lease: rent needs non-NULL lease_term_class. mbl carries no lease months ->
    'unspecified' (existing enum value, same as visir). sale -> NULL."""
    return "unspecified" if tenure == "rent" else None


# ───────────────────────────────────── parsed-row normalisation (table-agnostic)
def extract_common(p, table):
    """Map a table-specific parsed_mbl_* row into the common keys the pipeline uses."""
    if table == "sale":
        first = _to_dt(p.get("sent_dags")) or _to_dt(p.get("br_dags")) or _to_dt(p.get("fetched_at"))
        last = _to_dt(p.get("fetched_at")) or first
        addr = p.get("heimilisfang") or p.get("gata")
        return {
            "source_listing_id": str(p["source_listing_id"]),
            "url": URL_SALE % p["source_listing_id"],
            "is_foreign": p.get("is_foreign"), "is_negotiable": p.get("is_negotiable"),
            "teg_eign": p.get("teg_eign"), "fastano": p.get("fastano"),
            "verd": p.get("verd"), "lysing": p.get("lysing") or p.get("lysing_text"),
            "title": addr, "addr_text": addr, "postcode": p.get("postfang"),
            "lat": p.get("latitude"), "lng": p.get("longitude"),
            "area": p.get("fermetrar"), "rooms": p.get("fjoldi_herb"),
            "bedrooms": p.get("fjoldi_svefnhb"), "bathrooms": p.get("fjoldi_badherb"),
            "municipality": None, "available_from": None,
            "tegund_raw": p.get("teg_eign") or "unknown",
            "photos_json": p.get("images_json") or "[]",
            "first_seen": first, "last_seen": last, "parse_id": p.get("parse_id"),
        }
    # rent: residential íbúðaleiga, no fastano, no coords; type_id is an opaque signal.
    first = _to_dt(p.get("created")) or _to_dt(p.get("fetched_at"))
    last = _to_dt(p.get("updated")) or _to_dt(p.get("fetched_at")) or first
    return {
        "source_listing_id": str(p["source_listing_id"]),
        "url": URL_RENT % p["source_listing_id"],
        "is_foreign": p.get("is_foreign"), "is_negotiable": p.get("is_negotiable"),
        "teg_eign": None, "fastano": None,
        "verd": p.get("price"), "lysing": p.get("description") or p.get("description_text"),
        "title": p.get("title") or p.get("address"), "addr_text": p.get("address"),
        "postcode": p.get("zipcode"), "lat": None, "lng": None,
        "area": p.get("size"), "rooms": p.get("rooms"),
        "bedrooms": None, "bathrooms": None, "municipality": None,
        "available_from": p.get("available_from"),
        "tegund_raw": "leiga_type_%s" % (p.get("type_id") if p.get("type_id") is not None else "na"),
        "photos_json": p.get("images_json") or "[]",
        "first_seen": first, "last_seen": last, "parse_id": p.get("parse_id"),
    }


def build_canonical_row(common, tenure, cat, sub, lease, price, is_por, matshluti, raw_fastnum,
                        fastnum, conf, method, now):
    return {
        "canonical_id": None,
        "source": "mbl",
        "source_listing_id": common["source_listing_id"],
        "url": common["url"],
        "secondary_source_ids": [],
        "first_seen_at": common["first_seen"] or _to_dt(now),
        "last_seen_at": common["last_seen"] or _to_dt(now),
        "withdrawn_at": None, "is_active": True,
        "price_amount": price, "price_currency": "ISK",
        "listing_title": common.get("title"), "lysing": common.get("lysing"),
        "category": cat, "tenure": tenure, "sub_type": sub,
        "tegund_raw": common.get("tegund_raw") or "unknown", "lease_term_class": lease,
        "fastnum": fastnum, "lat": common.get("lat"), "lng": common.get("lng"), "geog": None,
        "area_sqm": common.get("area"), "rooms": common.get("rooms"),
        "bedrooms": common.get("bedrooms"), "bathrooms": common.get("bathrooms"),
        "addr_text": common.get("addr_text"), "addr_municipality": common.get("municipality"),
        "addr_postcode": (str(common["postcode"]) if common.get("postcode") is not None else None),
        "deposit_isk": None, "available_from": common.get("available_from"),
        "photos_json": common.get("photos_json") or "[]",
        "canonical_version": 1, "last_promoted_at": now,
        "surviving_parse_id": common.get("parse_id"),
        "surviving_source_priority": source_priority("mbl", tenure),
        "fastnum_resolution_method": method, "fastnum_resolution_confidence": conf,
        "fastnum_resolution_at": now if method else None,
        "matshluti_unit_id": matshluti, "source_raw_fastnum": raw_fastnum,
        "is_price_on_request": is_por,
    }


# ───────────────────────────────────── DP4: dedup (against static canonical snapshot)
class CanonicalIndex:
    """In-memory snapshot of existing scraper.listings_canonical. Tenure-matched tiers.
    Tier-1 keys on the bare fastnum (existing rows carry matshluti_unit_id=NULL — within-run
    (fastnum, matshluti) folding is deferred, design Q4); multi-unit safety comes from the
    size/fastnum reject filters + the commercial corroborator rule."""
    def __init__(self):
        self.by_ft = {}
        self.by_addr = {}
        self.by_tenure = {}

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
        t = cand["tenure"]
        if cand["fastnum"] is not None:
            self.by_ft.setdefault((int(cand["fastnum"]), t), []).append(cand)
        if cand["addr_norm"]:
            self.by_addr.setdefault((cand["addr_norm"], t), []).append(cand)
        self.by_tenure.setdefault(t, []).append(cand)


def _reject_match(mbl_row, candidate):
    """Universal §4 false-positive filters: differing fastnum => different property;
    size differing >10% => different unit (multi-unit building)."""
    m_fn, c_fn = mbl_row.get("fastnum"), candidate.get("fastnum")
    if m_fn and c_fn and int(m_fn) != int(c_fn):
        return True
    m_sz, c_sz = mbl_row.get("size_sqm"), candidate.get("size_sqm")
    if m_sz and c_sz:
        a, b = float(m_sz), float(c_sz)
        if max(a, b) > 0 and abs(a - b) / max(a, b) > SIZE_DISAGREE_TOL:
            return True
    return False


def _filter(cands, fastnum, size):
    vrow = {"fastnum": fastnum, "size_sqm": size}
    return [c for c in cands if not _reject_match(vrow, c)]


def _has_corroborator(mbl_row, candidate):
    """Rule 3 (commercial Tier-1): a building fastnum is 1:N over units, so a bare fastnum
    match needs an informative corroborator: size agreement OR non-sentinel price agreement."""
    m_sz, c_sz = mbl_row.get("size_sqm"), candidate.get("size_sqm")
    if m_sz and c_sz and float(m_sz) > 0 and float(c_sz) > 0:
        a, b = float(m_sz), float(c_sz)
        if abs(a - b) / max(a, b) <= SIZE_DISAGREE_TOL:
            return True
    m_pr, c_pr = mbl_row.get("price_amount"), candidate.get("price_amount")
    if m_pr and c_pr and int(m_pr) > PRICE_SENTINEL and int(c_pr) > PRICE_SENTINEL:
        a, b = float(m_pr), float(c_pr)
        if abs(a - b) / max(a, b) <= PRICE_AGREE_TOL:
            return True
    return False


def find_dedup_candidates(idx, fastnum, tenure, addr_norm, price, lat, lng, fs,
                          size=None, category=None):
    """§4 tiered, tenure-matched, with reject filters (+ Rule 3 commercial corroboration).
    First surviving tier wins (highest confidence first)."""
    def _commercial_ok(cands):
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


def select_action(candidates, tenure):
    """(action, target). mbl_wins if mbl outranks the best candidate's source for this tenure;
    else mbl_loses (fold mbl into the existing survivor). No candidates => insert_new."""
    if not candidates:
        return ("insert_new", None)
    mbl_prio = source_priority("mbl", tenure)
    target = sorted(candidates,
                    key=lambda c: (source_priority(c["source"], tenure), str(c["canonical_id"])))[0]
    if mbl_prio < source_priority(target["source"], tenure):
        return ("mbl_wins", target)
    return ("mbl_loses", target)


# ───────────────────────────────────── Supabase writes (pooler READ WRITE quirk)
def _row_vals(row, cols):
    vals = []
    for c in cols:
        v = row[c]
        if c == "photos_json":
            v = psycopg2.extras.Json(json.loads(v) if isinstance(v, str) else (v or []))
        elif c == "secondary_source_ids":
            v = list(v or [])
        vals.append(v)
    return vals


def apply_upsert(pg, row):
    cols = ", ".join(INSERT_COLUMNS)
    ph = ", ".join(["%s"] * len(INSERT_COLUMNS))
    upd = ", ".join("%s = EXCLUDED.%s" % (c, c) for c in INSERT_COLUMNS
                    if c not in ("source", "source_listing_id", "first_seen_at", "canonical_version"))
    sql = ("INSERT INTO scraper.listings_canonical (%s) VALUES (%s) "
           "ON CONFLICT (source, source_listing_id) DO UPDATE SET %s, "
           "canonical_version = scraper.listings_canonical.canonical_version + 1" % (cols, ph, upd))
    cur = pg.cursor()
    cur.execute(b"SET TRANSACTION READ WRITE; " + cur.mogrify(sql, _row_vals(row, INSERT_COLUMNS)))
    pg.commit()


def update_mbl_wins(pg, row, target):
    """mbl becomes survivor of target's canonical_id; fold the old source into secondary."""
    fold = "%s:%s" % (target["source"], target["source_listing_id"])
    set_cols = [c for c in INSERT_COLUMNS
                if c not in ("secondary_source_ids", "first_seen_at", "canonical_version")]
    set_sql = ", ".join("%s = %%s" % c for c in set_cols)
    vals = _row_vals(row, set_cols) + [fold, target["canonical_id"]]
    sql = ("UPDATE scraper.listings_canonical SET " + set_sql + ", "
           "secondary_source_ids = array_append(secondary_source_ids, %s), "
           "canonical_version = canonical_version + 1 WHERE canonical_id = %s")
    cur = pg.cursor()
    cur.execute(b"SET TRANSACTION READ WRITE; " + cur.mogrify(sql, vals))
    pg.commit()


def update_mbl_loses(pg, row, target):
    """Fold the mbl listing into the existing survivor's secondary_source_ids."""
    fold = "mbl:%s" % row["source_listing_id"]
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


def parsed_db_path():
    return get_scraper_data_dir() / "parsed_mbl.db"


# ───────────────────────────────────────────────────────────────────────── run
def run(table, slice_, dry_run, limit, sq, pg, log=print):
    sq.row_factory = sqlite3.Row
    tbl = "parsed_mbl_%s" % table
    pred = "is_negotiable = 0" if slice_ == "priced" else "is_negotiable = 1"
    q = ("SELECT * FROM %s WHERE promoted_to_canonical_at IS NULL AND %s ORDER BY parse_id"
         % (tbl, pred))
    if limit:
        q += " LIMIT %d" % int(limit)
    parsed = [dict(r) for r in sq.execute(q)]
    commons = [extract_common(p, table) for p in parsed]
    log("=== promote_mbl %s table=%s slice=%s: %d parsed rows ==="
        % ("DRY-RUN" if dry_run else "FULL", table, slice_, len(parsed)))

    # Pre-pass: derived fastnums (for FK presence) + postcodes (for addr/geo).
    derived = []
    for c in commons:
        m, raw, k = decompose_fastano(c["fastano"])
        c["_decomp"] = (m, raw, k)
        if k:
            derived.append(c["fastano"] // k)
    postcodes = {c["postcode"] for c in commons if c["postcode"]}
    props = preload_props(pg, postcodes, derived)
    canon = preload_canonical(pg)
    log("preloaded: props present=%d addr_keys=%d | canonical by_tenure=%s"
        % (len(props.present), len(props.by_addr), {k: len(v) for k, v in canon.by_tenure.items()}))
    if not dry_run:
        pg.rollback()   # close preload read-tx so the first write-tx SET READ WRITE is first stmt

    stats = Counter()
    t0 = time.perf_counter()
    for p, common in zip(parsed, commons):
        try:
            # DP1: foreign filter BEFORE resolution.
            if foreign_filter(common):
                stats["foreign_skip"] += 1
                if not dry_run:
                    sq.execute("UPDATE %s SET promoted_to_canonical_at=? WHERE parse_id=?" % tbl,
                               (_now(), p["parse_id"]))
                    sq.commit()
                continue
            # DP2: tenure.
            tenure = "rent" if table == "rent" else tenure_cascade(common, stats)
            # DP3: price.
            price, is_por = resolve_price(common["verd"], table)
            # category / sub_type.
            if table == "rent":
                if is_por:
                    # commercial-rent-on-request: price<=1 sentinel (Stage 8 finding 2026-06-16).
                    # residential íbúðaleiga is never 1 ISK, so the sentinel marks a commercial
                    # space let by tender. NB Lota-2 caveat: in the negotiable slice (verd=0) is_por
                    # is also True but those may be residential — Lota 2 must revisit this branch.
                    cat = "commercial"
                    sub = decompose_commercial_sub_type(common.get("lysing") or "", common.get("teg_eign"))
                    stats["rent_commercial_on_request"] += 1
                else:
                    # residential íbúðaleiga (type_id opaque — DECISIONS 2026-06-15); LLM refines (T2).
                    cat, sub = "residential", "apartment"
            else:
                cat, sub = decompose_category(common["teg_eign"], tenure, common.get("lysing") or "")
            # junk-guard: only TRUE residential junk (real price <= 100, not the POR sentinel).
            if not is_por and price <= JUNK_PRICE_MAX and cat == "residential":
                stats["skipped_junk"] += 1
                continue
            if cat == "plot" and common.get("area") is None:
                stats["skipped_plot_no_area"] += 1     # ck_plot_area would reject
                continue
            lease = derive_lease(tenure)
            # matshluti + raw fastano (§3, §7) + fastnum resolution (§2.5).
            matshluti, raw_fastnum, k = common["_decomp"]
            derived_fastnum = (common["fastano"] // k) if k else None
            fastnum, conf, method = resolve_fastnum(common, derived_fastnum, props)
            now = _now()
            row = build_canonical_row(common, tenure, cat, sub, lease, price, is_por,
                                      matshluti, raw_fastnum, fastnum, conf, method, now)
            # DP4: dedup against static snapshot.
            addr_norm = normalize_address(row["addr_text"] or "") or None
            cands, tier = find_dedup_candidates(canon, fastnum, tenure, addr_norm, price,
                                                row["lat"], row["lng"], row["first_seen_at"],
                                                common.get("area"), category=cat)
            action, target = select_action(cands, tenure)
            stats["action_" + action] += 1
            if tier:
                stats["dedup_tier_" + tier] += 1

            if dry_run:
                stats["promoted"] += 1
                stats[method or "unresolved"] += 1
                continue
            if action == "insert_new":
                apply_upsert(pg, row)
            elif action == "mbl_wins":
                update_mbl_wins(pg, row, target)
            elif action == "mbl_loses":
                update_mbl_loses(pg, row, target)
            sq.execute("UPDATE %s SET promoted_to_canonical_at=? WHERE parse_id=?" % tbl,
                       (now, p["parse_id"]))
            sq.commit()
            stats["promoted"] += 1
            stats[method or "unresolved"] += 1
        except Exception as e:
            pg.rollback()
            stats["failed"] += 1
            log("FAILED parse_id=%s id=%s: %s" % (p.get("parse_id"), common.get("source_listing_id"), repr(e)[:180]))

    log("\n=== SUMMARY (%.1fs) ===" % (time.perf_counter() - t0))
    for k in ("promoted", "foreign_skip", "tenure_sale_priced", "tenure_rent_from_leigu",
              "tenure_sale_from_solu", "tenure_sale_fallback", "rent_commercial_on_request",
              "action_insert_new", "action_mbl_wins", "action_mbl_loses",
              "dedup_tier_fastnum", "dedup_tier_addr", "dedup_tier_geo",
              "source_supplied", "address_match", "geo_match", "unresolved",
              "skipped_junk", "skipped_plot_no_area", "failed"):
        if stats.get(k):
            log("  %-24s %d" % (k, stats[k]))
    return stats


def main():
    ap = argparse.ArgumentParser(description="promote parsed_mbl_* -> scraper.listings_canonical (Step 3d)")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--slice", choices=["priced", "negotiable"], default="priced")
    ap.add_argument("--table", choices=["sale", "rent"], default="sale")
    args = ap.parse_args()
    if not args.confirm:
        print(__doc__)
        print("\nRe-invoke with --confirm (add --dry-run for no writes, --limit N for a smoke run).")
        return 0
    sq = sqlite3.connect(str(parsed_db_path()))
    dsn = open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read().strip()
    pg = psycopg2.connect(dsn)
    if args.dry_run:
        pg.set_session(readonly=True, autocommit=True)
    print("promoter_version=%s table=%s slice=%s dry_run=%s limit=%s"
          % (PROMOTER_VERSION, args.table, args.slice, args.dry_run, args.limit))
    try:
        run(args.table, args.slice, args.dry_run, args.limit, sq, pg)
    finally:
        sq.close(); pg.close()
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
