"""parse_myigloo — Step 1d parser: raw_blobs (detail) -> parsed_myigloo.

Reads pending/failed DETAIL fetches from raw_myigloo.db, gunzips + JSON-parses
the blob, extracts the LOCKED parsed_myigloo column set (SCRAPER_SPEC_v2 §2.2 +
Phase-1.5 wins Q1/Q2/Q3/Q8), and writes one parsed row per
(content_hash, parser_version). api_page rows are NOT parsed here (deferred).

No HTTP, no Supabase, no canonical promotion (Step 1e). stdlib only.

CLI:
    python parse_myigloo.py             # full run (all pending detail blobs)
    python parse_myigloo.py --dry-run   # 10 random pending blobs -> JSON to stdout, NO writes
"""
from __future__ import annotations

import argparse
import gzip
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path  # noqa: E402

PARSER_VERSION = "0.1.0"

# Top-level keys consumed into columns (everything else -> raw_overflow).
MAPPED_TOP_KEYS = {
    "title", "price", "size", "rooms", "bedrooms", "bathrooms",
    "listing_type", "address", "location", "images",
    "available_from", "visible", "published_at", "last_edit", "primary_description",
    "contract_min_months", "contract_max_months", "insurance_price", "insurance_months",
    "real_estate", "mbl_id", "linked_property_id",
}
# Top-level keys dropped entirely from overflow (PII person objects, GDPR-safe).
PII_DROP_TOP = {"owner"}
# Nested dotted paths nulled in overflow (volatile per-request stamps, §2.1.1).
VOLATILE_PATHS = {"organization.verification.as_of"}
# Kept in overflow but flagged: engagement metrics churn over time (not PII).
VOLATILE_SUSPECT_KEYS = {
    "views_count", "application_count", "has_applied", "last_conversation",
    "liked", "pre_approval", "client_steps_done",
}

# Decimal -> str so SQLite NUMERIC affinity stores the value (Decimal isn't bindable).
sqlite3.register_adapter(Decimal, str)


# ──────────────────────────────────────────────────────────── pure helpers
def _safe_get(d, dotted_path):
    cur = d
    for k in dotted_path.split("."):
        cur = cur.get(k) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def _to_decimal(s):
    if s is None or s == "":
        return None
    try:
        return Decimal(str(s))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(s):
    if s is None or s == "":
        return None
    try:
        return int(Decimal(str(s)))   # handles "13", 13, 13.0
    except (InvalidOperation, ValueError, TypeError):
        return None


def _extract_photos(images):
    if not isinstance(images, list):
        return "[]"
    urls = []
    for img in images:
        u = _safe_get(img, "image.file_field") if isinstance(img, dict) else None
        if u:
            urls.append(u)
    return json.dumps(urls, ensure_ascii=False)


def _extract_fastnum(real_estate):
    """HMS fastnum from real_estate.landreg_id, ONLY when landreg_source='landreg'
    (Q1: 'manual' source carries no registry link)."""
    if not isinstance(real_estate, dict):
        return None
    if real_estate.get("landreg_source") != "landreg":
        return None
    return _to_int(real_estate.get("landreg_id"))


def _nullify_path(obj, dotted_path):
    keys = dotted_path.split(".")
    cur = obj
    for k in keys[:-1]:
        if not isinstance(cur, dict) or k not in cur:
            return
        cur = cur[k]
    if isinstance(cur, dict) and keys[-1] in cur:
        cur[keys[-1]] = None


def _build_overflow(payload):
    over = {k: v for k, v in payload.items()
            if k not in MAPPED_TOP_KEYS and k not in PII_DROP_TOP}
    for path in VOLATILE_PATHS:
        _nullify_path(over, path)
    present = sorted(k for k in VOLATILE_SUSPECT_KEYS if k in over)
    if present:
        over["_volatile_suspect"] = present
    return json.dumps(over, ensure_ascii=False, sort_keys=True)


def parse_payload(payload: dict) -> dict:
    """Map a myigloo detail payload to the parsed_myigloo column dict
    (provenance columns added by the caller)."""
    visible = payload.get("visible")
    return {
        "title":              payload.get("title"),
        "lysing":             _safe_get(payload, "primary_description.text"),
        "price_amount":       _to_decimal(_safe_get(payload, "price.price")),
        "price_currency":     _safe_get(payload, "price.currency.code"),
        "size_sqm":           _to_decimal(payload.get("size")),
        "rooms":              _to_decimal(payload.get("rooms")),
        "bedrooms":           _to_decimal(payload.get("bedrooms")),
        "bathrooms":          _to_decimal(payload.get("bathrooms")),
        "tegund_raw":         _safe_get(payload, "listing_type.name"),
        "deposit_isk":        _to_decimal(payload.get("insurance_price")),
        "available_from":     payload.get("available_from"),
        "photos_json":        _extract_photos(payload.get("images")),
        "listing_type_tag":   _safe_get(payload, "listing_type.tag"),
        "category_tag":       _safe_get(payload, "listing_type.category.tag"),
        "addr_street":        _safe_get(payload, "address.street_name"),
        "addr_number":        _safe_get(payload, "address.street_number"),
        "addr_city":          _safe_get(payload, "address.city.name"),
        "addr_postcode":      _safe_get(payload, "address.postal_code.code"),
        "addr_country":       _safe_get(payload, "address.country.name"),
        "lat":                _to_decimal(_safe_get(payload, "location.lat")),
        "lng":                _to_decimal(_safe_get(payload, "location.lng")),
        "contract_min_months": _to_int(payload.get("contract_min_months")),
        "contract_max_months": _to_int(payload.get("contract_max_months")),
        "insurance_months":   _to_int(payload.get("insurance_months")),
        "fastnum_supplied":   _extract_fastnum(payload.get("real_estate")),
        "landreg_source":     _safe_get(payload, "real_estate.landreg_source"),
        "mbl_id":             payload.get("mbl_id"),
        "linked_property_id": payload.get("linked_property_id"),
        "source_visible":     (None if visible is None else int(bool(visible))),
        "source_published_at": payload.get("published_at"),
        "source_last_edit":   payload.get("last_edit"),
        "raw_overflow":       _build_overflow(payload),
        "promoted_to_canonical_at": None,
    }


_COLUMNS = [
    "raw_id", "content_hash", "source_listing_id", "parser_version", "parsed_at",
    "title", "lysing", "price_amount", "price_currency", "size_sqm", "rooms",
    "bedrooms", "bathrooms", "tegund_raw", "deposit_isk", "available_from", "photos_json",
    "listing_type_tag", "category_tag", "addr_street", "addr_number", "addr_city",
    "addr_postcode", "addr_country", "lat", "lng", "contract_min_months",
    "contract_max_months", "insurance_months", "fastnum_supplied", "landreg_source",
    "mbl_id", "linked_property_id", "source_visible", "source_published_at",
    "source_last_edit", "raw_overflow", "promoted_to_canonical_at",
]


def _insert_parsed(conn, row: dict):
    cols = ", ".join(_COLUMNS)
    ph = ", ".join("?" for _ in _COLUMNS)
    conn.execute(
        "INSERT INTO parsed_myigloo (%s) VALUES (%s) "
        "ON CONFLICT (content_hash, parser_version) DO NOTHING" % (cols, ph),
        tuple(row[c] for c in _COLUMNS))


class _DecimalEnc(json.JSONEncoder):
    def default(self, o):
        return str(o) if isinstance(o, Decimal) else super().default(o)


def run(dry_run: bool, conn, log=print) -> dict:
    cur = conn.cursor()
    order = "ORDER BY RANDOM() LIMIT 10" if dry_run else "ORDER BY rf.raw_id"
    rows = cur.execute(
        "SELECT rf.raw_id, rf.source_listing_id, rf.content_hash, rb.blob_gz "
        "FROM raw_fetches rf JOIN raw_blobs rb ON rf.content_hash = rb.content_hash "
        "WHERE rf.fetch_kind='detail' AND rf.parse_status IN ('pending','failed') " + order
    ).fetchall()
    log("=== parse_myigloo: %s (%d blobs) ===" % ("DRY-RUN" if dry_run else "FULL", len(rows)))
    n_parsed = n_failed = n_fastnum = 0
    t0 = time.perf_counter()
    for raw_id, slid, chash, blob_gz in rows:
        tb = time.perf_counter()
        try:
            payload = json.loads(gzip.decompress(blob_gz))
        except (json.JSONDecodeError, OSError, ValueError) as e:
            n_failed += 1
            if not dry_run:
                conn.execute("UPDATE raw_fetches SET parse_status='failed', parse_error=? WHERE raw_id=?",
                             (repr(e)[:300], raw_id))
                conn.commit()
            log("[%s] FAILED raw_id=%s: %s" % (_now(), raw_id, repr(e)[:80]))
            continue
        cols = parse_payload(payload)
        row = {"raw_id": raw_id, "content_hash": chash, "source_listing_id": str(slid),
               "parser_version": PARSER_VERSION, "parsed_at": _now(), **cols}
        if cols["fastnum_supplied"] is not None:
            n_fastnum += 1
        if dry_run:
            print(json.dumps(row, ensure_ascii=False, indent=2, cls=_DecimalEnc))
        else:
            _insert_parsed(conn, row)
            conn.execute(
                "UPDATE raw_fetches SET parse_status='parsed' "
                "WHERE content_hash=? AND fetch_kind='detail' AND parse_status IN ('pending','failed')",
                (chash,))
            conn.commit()
        n_parsed += 1
        log("[%s] parsed source_listing_id=%s raw_id=%s fastnum_supplied=%s landreg_source=%s elapsed=%.0fms"
            % (_now(), slid, raw_id, cols["fastnum_supplied"], cols["landreg_source"],
               (time.perf_counter() - tb) * 1000))
    elapsed = time.perf_counter() - t0
    log("\n=== SUMMARY ===")
    log("  parsed              : %d" % n_parsed)
    log("  failed              : %d" % n_failed)
    log("  fastnum_supplied set: %d (%.1f%%)" % (n_fastnum, 100 * n_fastnum / n_parsed if n_parsed else 0))
    log("  elapsed_sec         : %.1f" % elapsed)
    return {"parsed": n_parsed, "failed": n_failed, "fastnum": n_fastnum}


def _now():
    return datetime.now(timezone.utc).isoformat()


def main():
    ap = argparse.ArgumentParser(description="myigloo parser (detail blobs -> parsed_myigloo)")
    ap.add_argument("--dry-run", action="store_true", help="10 random pending blobs -> JSON, no writes")
    args = ap.parse_args()
    db = get_raw_db_path("myigloo")
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys=ON")
    print("DB: %s  (parser_version=%s)" % (db, PARSER_VERSION))
    try:
        run(args.dry_run, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
