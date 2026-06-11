"""parse_mbl — Step 3c mbl parser (raw list-page JSON blobs -> parsed_mbl_sale/_rent).

SCRAPER_SPEC_v2 §2.2 parsed tier for mbl. Decomposes raw_mbl.db list-page blobs
(Hasura GraphQL JSON, 16 listings/page) into per-listing rows in parsed_mbl.db
(SEPARATE DB — see init_parsed_mbl_schema). Source-flavored: fs_fasteign and
rentals_property keep their own field shapes 1:1; NO (category, tenure, sub_type)
decomposition (that is Step 3d promotion).

GENERATION TOLERANCE (DECISIONS 2026-06-11): the corpus is split — publishable seed
pages are v1_scalar (pre-amendment code), negotiable + re-sweep pages are v2_enriched.
fields_version is detected per blob from the LISTINGS THEMSELVES (presence of nested
keys), cross-checked against the fields=v2 marker in the ledger URL; a mismatch sets
the 'fields_marker_mismatch' flag, never a crash. v1 rows keep nested JSON columns NULL.

ONE row per source_listing_id; upsert precedence: v2_enriched > v1_scalar, newer
fetched_at wins within a generation, exact ties are skipped (so re-parse is idempotent
— same input -> same final rows, parsed_at untouched, no duplicates).

PARSE RULES (locked from Step 3c inventory + mini-probe):
  1. Sentinel 0 -> NULL: fastano, fasteignamat, brunabotamat, fermetraverd, bygg_ar
     (sale). The raw 0 survives in the raw layer only.
  2. is_negotiable = (verd == 0) sale / (price == 0) rent; verd/price keep the raw value.
  3. is_foreign = postcode outside the Icelandic 101-902 range OR coords outside the
     Iceland bbox (63.0-67.5 N, -25.0 - -13.0 E). NULL coords alone do NOT flag
     (28.8% of sale rows have no coords; that is missingness, not foreignness).
  4. Hashie::Mash upstream-Ruby leak in rent address/title/normalized_address
     ("Dugguvogur 50#<Hashie::Mash ...>"): strip at '#<', keep trimmed prefix,
     set address_corrupt.
  5. fermetrar/fermetraverd coerced to float (JSON serialization mixes int/float).
  6. Timestamps: sale sent_dags/br_dags are tz-aware -> passthrough; rent created/
     updated (and sale v2 'created') are NAIVE server stamps -> '+00:00' appended.
     ASSUMPTION (documented): Iceland is UTC year-round (no DST since 1968), so mbl's
     naive timestamps ARE UTC wall-clock; appending +00:00 is lossless.
  7. lysing/description: raw HTML kept verbatim + deterministic HTML-strip text column
     (lysing_text/description_text) for the LLM extraction pipe.
  8. Nested lists serialize deterministically: images sorted by imgno (sale) /
     ordering (rent) with array-index fallback for NULL keys; all JSON dumped
     sort_keys=True, compact separators -> re-parse yields identical bytes.

CLI:
    python parse_mbl.py                       # docstring + exit 0
    python parse_mbl.py --confirm             # parse all pending list-page rows
    python parse_mbl.py --confirm --limit N   # first N blobs (debug)
    python parse_mbl.py --confirm --reparse   # re-parse ALL list-page rows

NOTE: the full-corpus run is gated on the enriched re-sweep finishing (the fetcher
holds the write handle on raw_mbl.db until then).

stdlib only.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path  # noqa: E402
from init_parsed_mbl_schema import get_parsed_db_path  # noqa: E402

PARSER_VERSION = "mbl_parse_v1"
V1, V2 = "v1_scalar", "v2_enriched"
_GEN_RANK = {V1: 1, V2: 2}

# Iceland: postcodes 101-902 (Þjóðskrá range); bbox per locked rule 3.
_IS_POST_LO, _IS_POST_HI = 101, 902
_IS_BBOX = (63.0, 67.5, -25.0, -13.0)        # lat_min, lat_max, lng_min, lng_max

_TZ_SUFFIX_RE = re.compile(r"(Z|[+-]\d{2}:?\d{2})$")
_BLOCK_TAGS = {"p", "br", "div", "li", "ul", "ol", "tr", "table", "section",
               "h1", "h2", "h3", "h4", "h5", "h6"}

SALE_SCALARS = (
    "eign_id", "fastano", "gata", "heimilisfang", "normalized_heimilisfang", "postfang",
    "teg_eign", "fermetrar", "fermetraverd", "fjoldi_herb", "fjoldi_svefnhb",
    "fjoldi_badherb", "fjoldi_haeda", "verd", "fasteignamat", "brunabotamat",
    "ahvilandi_lan", "appended_land", "bygg_ar", "nybygging", "latitude", "longitude",
    "hverfi", "lysing", "inngangur", "aukaibud", "bilskur", "gardur", "lyfta", "svalir",
    "parking", "parking_shelter", "electric_car", "pet_allowed", "wheelchair_acc",
    "seniors", "makaskipti", "skiptanleg", "greidslumat", "syna", "dealer_email",
    "embed", "created", "sent_dags", "br_dags", "address_search_id", "price_search_id",
    "size_search_id", "zip_search_id",
)
SALE_BOOLS = ("nybygging", "aukaibud", "bilskur", "gardur", "lyfta", "svalir", "parking",
              "parking_shelter", "electric_car", "pet_allowed", "wheelchair_acc",
              "seniors", "makaskipti", "skiptanleg", "greidslumat", "syna")
SALE_ZERO_NULL = ("fastano", "fasteignamat", "brunabotamat", "fermetraverd", "bygg_ar")
SALE_NESTED = (("images", "images_json"), ("agency", "agency_json"),
               ("attachments", "attachments_json"), ("latest_openhouse", "openhouse_json"),
               ("postal_code", "postal_code_json"), ("promo", "promo_json"))

RENT_SCALARS = (
    "id", "address", "normalized_address", "zipcode", "title", "type_id", "size",
    "price", "rooms", "available_from", "available_until", "longtime", "lift",
    "pet_allowed", "wheelchair_acc", "from_leiguskjol", "show_from_date",
    "show_until_date", "created", "updated", "description",
)
RENT_BOOLS = ("longtime", "lift", "pet_allowed", "wheelchair_acc", "from_leiguskjol")
RENT_NESTED = (("images", "images_json"), ("agency", "agency_json"),
               ("postal_code", "postal_code_json"), ("promo", "promo_json"))

META_COLS = ("source_listing_id", "raw_id", "content_hash", "fetched_at",
             "fields_version", "parser_version", "parsed_at", "flags")
SALE_DERIVED = ("lysing_text", "is_negotiable", "is_foreign")
RENT_DERIVED = ("description_text", "is_negotiable", "is_foreign", "address_corrupt")

SALE_COLUMNS = META_COLS + SALE_SCALARS + SALE_DERIVED + tuple(c for _, c in SALE_NESTED)
RENT_COLUMNS = META_COLS + RENT_SCALARS + RENT_DERIVED + tuple(c for _, c in RENT_NESTED)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ────────────────────────────────────────────────────── pure helpers (testable)
def _bool01(v):
    return None if v is None else int(bool(v))


def _zero_null(v):
    return None if v == 0 else v


def _to_float(v):
    return None if v is None else float(v)


def _tz_normalize(ts):
    """Append +00:00 to a NAIVE ISO timestamp (Iceland is UTC year-round, no DST
    since 1968 — mbl naive server stamps are UTC wall-clock). tz-aware passthrough."""
    if not ts:
        return ts
    return ts if _TZ_SUFFIX_RE.search(ts) else ts + "+00:00"


def _strip_hashie(s):
    """Strip the upstream Hashie::Mash serialization leak. Returns (value, corrupted)."""
    if s and "#<" in s:
        return s.split("#<", 1)[0].rstrip(), True
    return s, False


def _is_foreign(postcode, lat=None, lng=None):
    """Locked rule 3. NULL coords alone never flag; non-IS postcode OR out-of-bbox
    coords do (the Spánarheimili block has postfang 806 INSIDE 101-902 but lat ~38)."""
    post_foreign = postcode is not None and not (_IS_POST_LO <= postcode <= _IS_POST_HI)
    coords_foreign = (lat is not None and lng is not None and not (
        _IS_BBOX[0] <= lat <= _IS_BBOX[1] and _IS_BBOX[2] <= lng <= _IS_BBOX[3]))
    return 1 if (post_foreign or coords_foreign) else 0


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(html):
    """Deterministic HTML -> text: stdlib HTMLParser, block tags become newlines,
    entities unescaped once, whitespace collapsed per line, empty lines dropped."""
    if not html:
        return None
    ex = _TextExtractor()
    ex.feed(html)
    ex.close()
    lines = []
    for raw_line in "".join(ex.parts).split("\n"):
        line = " ".join(raw_line.split())
        if line:
            lines.append(line)
    return "\n".join(lines) or None


def _dump_json(obj):
    """Deterministic JSON: sorted keys, compact, UTF-8 verbatim."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sorted_images(imgs, order_field):
    """Sort image dicts by imgno/ordering; NULL keys keep array order, after keyed ones."""
    return [img for _, img in sorted(
        ((((img or {}).get(order_field) is None, (img or {}).get(order_field) or 0, idx), img)
         for idx, img in enumerate(imgs)), key=lambda t: t[0])]


def detect_fields_version(listings):
    """v2_enriched iff any listing carries a nested key (empty v2 lists still carry
    the key — presence, not truthiness, is the signal)."""
    return V2 if any("images" in (L or {}) for L in listings) else V1


# ────────────────────────────────────────────────── per-listing parse (pure)
def parse_sale_listing(L, meta, fields_version, flags):
    row = {c: None for c in SALE_COLUMNS}
    row.update(meta)
    row["fields_version"] = fields_version
    row["source_listing_id"] = L["eign_id"]
    for c in SALE_SCALARS:
        row[c] = L.get(c)
    for c in SALE_BOOLS:
        row[c] = _bool01(row[c])
    row["fermetrar"] = _to_float(row["fermetrar"])
    row["fermetraverd"] = _to_float(row["fermetraverd"])
    for c in SALE_ZERO_NULL:                       # rule 1 — AFTER float coercion
        row[c] = _zero_null(row[c])
    row["created"] = _tz_normalize(row["created"])             # v2-only naive stamp
    row["sent_dags"] = _tz_normalize(row["sent_dags"])         # tz-aware passthrough
    row["br_dags"] = _tz_normalize(row["br_dags"])
    row["is_negotiable"] = 1 if L.get("verd") == 0 else 0      # rule 2 (raw verd kept)
    row["is_foreign"] = _is_foreign(row["postfang"], row["latitude"], row["longitude"])
    row["lysing_text"] = html_to_text(row["lysing"])           # rule 7
    if fields_version == V2:                                    # rule 8
        for src, col in SALE_NESTED:
            if src in L:
                v = L[src]
                if src == "images" and v is not None:
                    v = _sorted_images(v, "imgno")
                row[col] = _dump_json(v) if v is not None else None
    row["flags"] = _dump_json(sorted(flags)) if flags else None
    return row


def parse_rent_listing(L, meta, fields_version, flags):
    row = {c: None for c in RENT_COLUMNS}
    row.update(meta)
    row["fields_version"] = fields_version
    row["source_listing_id"] = L["id"]
    for c in RENT_SCALARS:
        row[c] = L.get(c)
    for c in RENT_BOOLS:
        row[c] = _bool01(row[c])
    corrupt = False                                            # rule 4
    for c in ("address", "title", "normalized_address"):
        row[c], hit = _strip_hashie(row[c])
        corrupt = corrupt or hit
    row["address_corrupt"] = 1 if corrupt else 0
    row["created"] = _tz_normalize(row["created"])             # rule 6 (naive -> +00:00)
    row["updated"] = _tz_normalize(row["updated"])
    row["is_negotiable"] = 1 if L.get("price") == 0 else 0     # rule 2 (raw price kept)
    row["is_foreign"] = _is_foreign(row["zipcode"])            # rent has no coords
    row["description_text"] = html_to_text(row["description"])  # rule 7
    if fields_version == V2:                                    # rule 8
        for src, col in RENT_NESTED:
            if src in L:
                v = L[src]
                if src == "images" and v is not None:
                    v = _sorted_images(v, "ordering")
                row[col] = _dump_json(v) if v is not None else None
    row["flags"] = _dump_json(sorted(flags)) if flags else None
    return row


# ────────────────────────────────────────────────── per-blob parse (pure)
def parse_blob(body, *, root, url, raw_id, content_hash, fetched_at, parsed_at=None):
    """body bytes -> (rows, fields_version). root in ('sale','rent')."""
    data = json.loads(body)
    root_key = "fs_fasteign" if root == "sale" else "rentals_property"
    listings = data["data"][root_key]
    fields_version = detect_fields_version(listings)
    flags = []
    if ("fields=v2" in (url or "")) != (fields_version == V2):   # ledger cross-check
        flags.append("fields_marker_mismatch")
    meta = {"raw_id": raw_id, "content_hash": content_hash, "fetched_at": fetched_at,
            "parser_version": PARSER_VERSION, "parsed_at": parsed_at or now_iso()}
    fn = parse_sale_listing if root == "sale" else parse_rent_listing
    return [fn(L, meta, fields_version, flags) for L in listings], fields_version


# ────────────────────────────────────────────────── upsert (precedence)
def upsert_row(parsed_conn, table, row):
    """ONE row per source_listing_id. Precedence: v2_enriched > v1_scalar; newer
    fetched_at within a generation; exact (generation, fetched_at) ties SKIP so
    re-parse is idempotent (parsed_at untouched). Returns 'inserted'|'replaced'|'skipped'."""
    cur = parsed_conn.execute(
        "SELECT fields_version, fetched_at FROM %s WHERE source_listing_id=?" % table,
        (row["source_listing_id"],)).fetchone()
    if cur is not None:
        old = (_GEN_RANK[cur[0]], cur[1])
        new = (_GEN_RANK[row["fields_version"]], row["fetched_at"])
        if new <= old:
            return "skipped"
        parsed_conn.execute("DELETE FROM %s WHERE source_listing_id=?" % table,
                            (row["source_listing_id"],))
    cols = SALE_COLUMNS if table == "parsed_mbl_sale" else RENT_COLUMNS
    parsed_conn.execute(
        "INSERT INTO %s(%s) VALUES(%s)" % (table, ",".join(cols), ",".join("?" * len(cols))),
        [row.get(c) for c in cols])
    return "replaced" if cur is not None else "inserted"


_KIND_ROOT = (("list_page_sale", "sale"), ("list_page_rent", "rent"))


def _root_for_kind(kind):
    for prefix, root in _KIND_ROOT:
        if kind.startswith(prefix):
            return root
    return None


# ────────────────────────────────────────────────── run loop
def run(raw_conn, parsed_conn, *, limit=None, reparse=False, log=print) -> dict:
    where = "f.content_hash IS NOT NULL AND f.fetch_kind LIKE 'list_page_%'"
    if not reparse:
        where += " AND f.parse_status='pending'"
    sql = ("SELECT f.raw_id, f.fetch_kind, f.url, f.fetched_at, f.content_hash, b.blob_gz "
           "FROM raw_fetches f JOIN raw_blobs b ON b.content_hash=f.content_hash "
           "WHERE " + where + " ORDER BY f.fetched_at, f.raw_id")
    if limit:
        sql += " LIMIT %d" % int(limit)
    blobs = raw_conn.execute(sql).fetchall()
    log("=== parse_mbl (%s) — %d list-page blobs to parse ===" % (PARSER_VERSION, len(blobs)))
    stats = {"blobs": 0, "listings": 0, "inserted": 0, "replaced": 0, "skipped": 0,
             "failed_blobs": 0, "v1_blobs": 0, "v2_blobs": 0}
    for raw_id, kind, url, fetched_at, content_hash, blob_gz in blobs:
        root = _root_for_kind(kind)
        table = "parsed_mbl_sale" if root == "sale" else "parsed_mbl_rent"
        try:
            rows, fv = parse_blob(gzip.decompress(blob_gz), root=root, url=url,
                                  raw_id=raw_id, content_hash=content_hash,
                                  fetched_at=fetched_at)
            for row in rows:
                stats[upsert_row(parsed_conn, table, row)] += 1
            parsed_conn.commit()
            raw_conn.execute("UPDATE raw_fetches SET parse_status='parsed' WHERE raw_id=?",
                             (raw_id,))
            raw_conn.commit()
            stats["blobs"] += 1
            stats["listings"] += len(rows)
            stats["v1_blobs" if fv == V1 else "v2_blobs"] += 1
        except Exception as e:
            raw_conn.execute(
                "UPDATE raw_fetches SET parse_status='failed', parse_error=? WHERE raw_id=?",
                (("%s: %s" % (type(e).__name__, e))[:500], raw_id))
            raw_conn.commit()
            stats["failed_blobs"] += 1
            log("  raw_id=%s FAILED: %s" % (raw_id, type(e).__name__))
    log("  blobs=%d (v1=%d, v2=%d) listings=%d -> inserted=%d replaced=%d skipped=%d failed=%d"
        % (stats["blobs"], stats["v1_blobs"], stats["v2_blobs"], stats["listings"],
           stats["inserted"], stats["replaced"], stats["skipped"], stats["failed_blobs"]))
    return stats


def main():
    ap = argparse.ArgumentParser(description="mbl parser (raw list-page blobs -> parsed_mbl.db)")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--reparse", action="store_true")
    args = ap.parse_args()
    if not args.confirm:
        print(__doc__)
        print("\nRe-invoke with --confirm to parse pending list-page rows.")
        return 0
    raw_conn = sqlite3.connect(str(get_raw_db_path("mbl")))
    parsed_conn = sqlite3.connect(str(get_parsed_db_path()))
    ok = parsed_conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                             "AND name='parsed_mbl_sale'").fetchone()
    if not ok:
        print("ERROR: parsed_mbl tables missing — run init_parsed_mbl_schema.py first.")
        return 1
    print("raw DB    : %s" % get_raw_db_path("mbl"))
    print("parsed DB : %s" % get_parsed_db_path())
    try:
        run(raw_conn, parsed_conn, limit=args.limit, reparse=args.reparse)
    finally:
        raw_conn.close()
        parsed_conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
