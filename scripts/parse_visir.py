"""parse_visir — Step 2c visir parser (raw_blobs HTML -> parsed_visir).

SCRAPER_SPEC_v2 §2.2 parsed tier for visir. Reads detail-fetch HTML blobs from
raw_visir.db, extracts visir's OWN field shape (source-flavored — NO (category, tenure,
sub_type) decomposition; that is Step 2d promotion), and writes parsed_visir rows.

Selectors locked empirically in Step A (5 real Phase-1c samples). fastnum is LABEL-ANCHORED
(Fasteignanúmer fact → value, F-prefix stripped) — never a page-wide regex (Step 2a finding).
tenure_signal is a best-effort detail-HTML hint (rent markers -> 'rent', else 'sale');
Step 2d promotion is the canonical tenure authority.

CLI:
    python parse_visir.py                       # docstring + exit 0
    python parse_visir.py --confirm             # parse all pending detail rows
    python parse_visir.py --confirm --limit N   # first N (debug)
    python parse_visir.py --confirm --reparse   # re-parse ALL detail rows (not just pending)

stdlib + beautifulsoup4 (+ lxml). Timestamps ISO8601 from the Python call-site (§2.1).
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_raw_db_path  # noqa: E402

PARSER_VERSION = "visir_parse_v1"
PHOTO_HOST_RE = re.compile(r"api-beta\.fasteignir\.is/pictures/")
LATLNG_RE = re.compile(r"lat=(6[0-9]\.\d+)&lon=(-?\d[\d.]+)")
RENT_MARKERS = ("leiguverð", "til leigu", "/mán", "á mánuði")   # Decision 1 (lowercased)

PARSED_COLUMNS = (
    "title", "price_amount", "price_currency", "price_text_raw", "is_price_on_request",
    "size_sqm", "rooms", "bedrooms", "bathrooms", "byggar",
    "tegund_raw", "tenure_signal", "lysing",
    "addr_street", "addr_number", "addr_postcode", "addr_city",
    "lat", "lng", "fastnum_supplied", "photos_json", "n_photos",
    "listing_date", "agency_name",
)


# ─────────────────────────────────────────────────────── numeric helpers
def _num(s):
    """Parse an Icelandic-formatted number: '.' thousands, ',' decimal. None on failure."""
    if not s:
        return None
    s = re.sub(r"[^\d.,]", "", str(s))
    if not s:
        return None
    try:
        if "," in s:
            return float(s.replace(".", "").replace(",", "."))
        return int(s.replace(".", ""))
    except ValueError:
        return None


def _txt(el):
    return " ".join(el.get_text().split()) if el else None


class VisirParser:
    def __init__(self, conn):
        self.conn = conn

    # -- pure extraction (testable, no DB) --------------------------------
    def parse_html_bytes(self, html_bytes, raw_id, content_hash, source_listing_id) -> dict:
        text = html_bytes.decode("utf-8", errors="replace")
        low = text.lower()
        try:
            s = BeautifulSoup(text, "lxml")
        except Exception:
            s = BeautifulSoup(text, "html.parser")

        f = {c: None for c in PARSED_COLUMNS}
        f["price_currency"] = "ISK"
        f["is_price_on_request"] = 0

        def guard(name, fn):
            try:
                return fn()
            except Exception:
                return None

        f["title"] = guard("title", lambda: _txt(s.select_one(".property__center-title")))
        f["tegund_raw"] = guard("tegund", lambda: _txt(s.select_one(".property__center-class")))

        # price
        ptxt = guard("price_text", lambda: _txt(s.select_one(".property__center-price")))
        f["price_text_raw"] = ptxt
        if ptxt:
            if "tilboð" in ptxt.lower():
                f["is_price_on_request"] = 1
                f["price_amount"] = None
            else:
                f["price_amount"] = _num(ptxt)

        # summary chips: size / rooms / bedrooms / bathrooms / byggar
        chips = guard("chips", lambda: [_txt(c) for c in s.select(".description__head-text")]) or []
        for chip in chips:
            if not chip:
                continue
            cl = chip.lower()
            if f["size_sqm"] is None:
                m = re.search(r"(\d[\d.,]*)\s*(m²|fm)", chip)
                if m:
                    f["size_sqm"] = _num(m.group(1))
            if "svefnh" in cl and f["bedrooms"] is None:
                m = re.search(r"(\d+)", chip)
                if m:
                    f["bedrooms"] = _num(m.group(1))
            elif "baðherb" in cl and f["bathrooms"] is None:
                m = re.search(r"(\d+)", chip)
                if m:
                    f["bathrooms"] = _num(m.group(1))
            elif "herb" in cl and f["rooms"] is None:       # bare 'herb.' = total rooms
                m = re.search(r"(\d+)", chip)
                if m:
                    f["rooms"] = _num(m.group(1))
            if "byggt" in cl and f["byggar"] is None:
                m = re.search(r"(\d{4})", chip)
                if m:
                    f["byggar"] = int(m.group(1))

        # tenure_signal (Decision 1)
        if any(mk in low for mk in RENT_MARKERS):
            f["tenure_signal"] = "rent"
        elif f["price_text_raw"] is None and f["tegund_raw"] is None:
            f["tenure_signal"] = "unknown"
        else:
            f["tenure_signal"] = "sale"

        # lysing: longest description block
        f["lysing"] = guard("lysing", lambda: max(
            (_txt(d) for d in s.select(".description__bottom-text")), key=lambda t: len(t or ""), default=None))

        # address street+number: primary = .property__center-title (carries the house
        # number; og:title sometimes omits it), unit suffix stripped; fallback = og:title.
        def addr():
            street_number = None
            t = _txt(s.select_one(".property__center-title"))
            if t:
                # drop unit suffix: "íbúð 202", "íb. 5", "íb307"
                street_number = re.sub(r"\s+íb(úð)?\.?\s*\d+.*$", "", t, flags=re.IGNORECASE).strip()
            if not street_number:
                og = s.select_one('meta[property="og:title"]')
                if og and og.get("content"):
                    parts = [p.strip() for p in og["content"].split(":", 1)[-1].split(",")]
                    street_number = parts[0] if parts else None
            if street_number:
                m = re.match(r"^(.*?)\s+(\d+[-–]?\d*[A-Za-zÁ-Þá-þ]?)$", street_number)
                if m:
                    f["addr_street"], f["addr_number"] = m.group(1), m.group(2)
                else:
                    f["addr_street"] = street_number   # named area, no house number
        guard("addr", addr)

        # postcode + city from .property__center-text (first "NNN City")
        def pcity():
            for el in s.select(".property__center-text"):
                t = _txt(el)
                m = re.match(r"^(\d{3})\s+(.+)$", t or "")
                if m:
                    f["addr_postcode"], f["addr_city"] = m.group(1), m.group(2)
                    return
        guard("pcity", pcity)

        # lat / lng (map URL); None when no map (e.g. commercial). Already clean floats —
        # NOT via _num() (which would strip the decimal point and the minus sign).
        m = LATLNG_RE.search(text)
        if m:
            try:
                f["lat"], f["lng"] = float(m.group(1)), float(m.group(2))
            except ValueError:
                pass

        # fastnum — LABEL-ANCHORED via the Fasteignanúmer fact pair
        def fastnum():
            for item in s.select(".property__bottom-item"):
                lab = item.select_one(".property__bottom-text")
                if lab and "asteignan" in lab.get_text():       # Fasteignanúmer
                    val = item.select_one(".property__bottom-title")
                    if val:
                        digits = re.sub(r"\D", "", val.get_text())   # "F2534030" -> 2534030
                        return int(digits) if digits else None
            return None
        f["fastnum_supplied"] = guard("fastnum", fastnum)

        # photos
        def photos():
            seen, urls = set(), []
            for img in s.find_all("img"):
                src = img.get("src") or img.get("data-src") or ""
                if PHOTO_HOST_RE.search(src) and src not in seen:
                    seen.add(src)
                    urls.append(src)
            return urls
        plist = guard("photos", photos) or []
        f["photos_json"] = json.dumps(plist) if plist else None
        f["n_photos"] = len(plist)

        # listing_date: "Skráð <date>"
        def skrad():
            for el in s.select(".property__head-text"):
                t = _txt(el)
                if t and "Skrá" in t:
                    return re.sub(r"^\s*Skrá\w*\s*", "", t).strip()
            return None
        f["listing_date"] = guard("skrad", skrad)

        # agency_name (best-effort, PII — dropped at promotion)
        f["agency_name"] = guard("agency", lambda: _txt(s.select_one(".agency")))

        f.update({"raw_id": raw_id, "content_hash": content_hash,
                  "source_listing_id": source_listing_id, "parser_version": PARSER_VERSION,
                  "parsed_at": datetime.now(timezone.utc).isoformat()})
        return f

    def parse_row(self, raw_id, content_hash, source_listing_id, blob_gz) -> dict:
        return self.parse_html_bytes(gzip.decompress(blob_gz), raw_id, content_hash, source_listing_id)

    # -- DB write ---------------------------------------------------------
    def _insert(self, f) -> int:
        cols = ["raw_id", "content_hash", "source_listing_id", "parser_version", "parsed_at"] \
            + list(PARSED_COLUMNS)
        placeholders = ",".join("?" for _ in cols)
        vals = [f.get(c) for c in cols]
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO parsed_visir(%s) VALUES(%s)" % (",".join(cols), placeholders), vals)
        return cur.rowcount


def run(conn, *, confirm, limit=None, reparse=False, log=print) -> dict:
    parser = VisirParser(conn)
    where = "f.fetch_kind='detail' AND f.content_hash IS NOT NULL"
    if not reparse:
        where += " AND f.parse_status='pending'"
    sql = ("SELECT f.raw_id, f.content_hash, f.source_listing_id, b.blob_gz "
           "FROM raw_fetches f JOIN raw_blobs b ON b.content_hash=f.content_hash "
           "WHERE " + where + " ORDER BY f.raw_id")
    if limit:
        sql += " LIMIT %d" % int(limit)
    rows = conn.execute(sql).fetchall()
    log("=== parse_visir (%s) — %d detail rows to parse ===" % (PARSER_VERSION, len(rows)))
    stats = {"parsed": 0, "inserted": 0, "deduped": 0, "failed": 0}
    for raw_id, content_hash, slid, blob_gz in rows:
        try:
            f = parser.parse_row(raw_id, content_hash, slid, blob_gz)
            inserted = parser._insert(f)
            conn.execute("UPDATE raw_fetches SET parse_status='parsed' WHERE raw_id=?", (raw_id,))
            conn.commit()
            stats["parsed"] += 1
            stats["inserted" if inserted else "deduped"] += 1
        except Exception as e:
            conn.execute("UPDATE raw_fetches SET parse_status='failed', parse_error=? WHERE raw_id=?",
                         (("%s: %s" % (type(e).__name__, e))[:500], raw_id))
            conn.commit()
            stats["failed"] += 1
            log("  raw_id=%s FAILED: %s" % (raw_id, type(e).__name__))
    log("  parsed=%d (inserted=%d, deduped=%d), failed=%d"
        % (stats["parsed"], stats["inserted"], stats["deduped"], stats["failed"]))
    return stats


def main():
    ap = argparse.ArgumentParser(description="visir parser (raw_blobs HTML -> parsed_visir)")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--reparse", action="store_true")
    args = ap.parse_args()
    if not args.confirm:
        print(__doc__)
        print("\nRe-invoke with --confirm to parse pending detail rows.")
        return 0
    db_path = get_raw_db_path("visir")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='parsed_visir'").fetchone():
        print("ERROR: parsed_visir table missing — run init_parsed_visir_schema.py first.")
        return 1
    print("DB: %s" % db_path)
    try:
        run(conn, confirm=True, limit=args.limit, reparse=args.reparse)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
