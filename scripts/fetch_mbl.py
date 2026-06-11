"""fetch_mbl — Step 3b P2 mbl raw fetcher (Hasura GraphQL, offset-paginated).

mbl's data layer is Hasura GraphQL at g.mbl.is/v1/graphql (Step 3a). The anonymous role
HARD-CAPS result rows at 16/query, so enumeration is offset-pagination at 16/page over a
FROZEN id window (frozen_max_id captured at seed start; order_by the immutable PK eign_id/id,
NOT sent_dags which mutates on edit). §0.5 caps <1000 page-loads/24h at minutes-between pacing.

LIFECYCLE (asymmetric):
  * seed-sale  — ~861 pages (13,772 / 16) -> MULTI-NIGHT (~3 runs at --max-pages 400, 120s spacing).
  * seed-rent  — ~85 pages (1,349 / 16)   -> typically a SINGLE run (~2.8h).
After the one-time seed, steady-state is DELTA-ONLY (delta-sale via br_dags>last_seen,
delta-rent via updated>last_seen) — mbl CANNOT do §6's nightly-full-sweep at this pacing.

Resume-safe: state persisted to mbl_fetch_state.json after every page (atomic os.replace).
`--mode resume` continues the single in-flight mode; refuses if >1 in-flight (specify --mode).

content_hash via canonicalize_mbl (§2.1.1 trivial sorted-keys); blob_gz verbatim per §2.1.
NO detail endpoint (list payload is rich). Draft rows filtered out (sale verd>0/fermetrar>0,
rent price>0/size>0). Kill-switch (exit 2): 3+ consec HTTP 400 (visir throttle signal,
preemptive), 403, 429, CAPTCHA body, 3+ consec timeouts, GraphQL `errors` in a 200 body.

CLI:
  python fetch_mbl.py --mode aggregate-check                 # 1 request, no writes
  python fetch_mbl.py --mode seed-sale [--max-pages N] [--dry-run]
  python fetch_mbl.py --mode seed-rent | delta-sale | delta-rent
  python fetch_mbl.py --mode delta-sale-negotiable | delta-rent-negotiable   # Tilboð slices
  python fetch_mbl.py --mode resume                          # continue in-flight seed/delta

deps: stdlib + requests + canonicalize_mbl.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_paths import get_scraper_data_dir, get_raw_db_path  # noqa: E402
from canonicalize_mbl import canonicalize_mbl                    # noqa: E402
import sqlite3                                                   # noqa: E402

ENDPOINT = "https://g.mbl.is/v1/graphql"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
FETCHER_VERSION = "mbl_fetch_v1"
FIELDS_VERSION = "v2_enriched"     # enriched selection (2026-06-10 mini-probe); &fields=v2 on synthetic URLs
PAGE = 16                          # Hasura anonymous-role hard cap
DEFAULT_MAX_PAGES = 400            # per-run budget (keeps a run under §0.5 <1000/24h)
DEFAULT_SPACING = 120.0           # seconds between page-loads
MIN_SPACING_FLOOR = 60.0
TIMEOUT_S = 30
MAX_CONSEC_400 = 3
MAX_CONSEC_TIMEOUT = 3
DEFAULT_STATE_PATH = str(get_scraper_data_dir() / "mbl_fetch_state.json")
_CAPTCHA_MARKERS = (b"captcha", b"challenge", b"cf-challenge", b"just a moment")

# v2_enriched selection (2026-06-10 mini-probe, enriched_sale_16/enriched_rent_16 fixtures):
# ALL scalars except generated_fts (huge derived tsvector) + all nested blocks with full image
# variants (signed CDN URLs, underivable after the fact). Deliberately EXCLUDED: favorite
# (user-scoped), postal_code.fs_count/rt_count (volatile per-postnr listing counters — would
# break §2.1.1 content-hash dedup on delta re-fetches).
SALE_FIELDS = ("eign_id fastano gata heimilisfang normalized_heimilisfang postfang teg_eign "
               "fermetrar fermetraverd fjoldi_herb fjoldi_svefnhb fjoldi_badherb fjoldi_haeda "
               "verd fasteignamat brunabotamat ahvilandi_lan appended_land bygg_ar nybygging "
               "latitude longitude hverfi lysing inngangur "
               "aukaibud bilskur gardur lyfta svalir parking parking_shelter electric_car "
               "pet_allowed wheelchair_acc seniors makaskipti skiptanleg greidslumat syna "
               "dealer_email embed created sent_dags br_dags "
               "address_search_id price_search_id size_search_id zip_search_id "
               "images { id imgno big big_h e_low low regular regular_h small small_h } "
               "agency { sala_id nafn heimilisfang postnumer simi email_tl vefslod logo logo_url } "
               "attachments { id title file } "
               "latest_openhouse { id date open close dt_search_id } "
               "postal_code { postnr baer baer_thgf hverfi landshluti } "
               "promo { seckey }")
RENT_FIELDS = ("id address normalized_address zipcode title type_id size price rooms "
               "available_from available_until longtime lift pet_allowed wheelchair_acc "
               "from_leiguskjol show_from_date show_until_date created updated description "
               "images { id ordering big big_h e_low low regular regular_h small small_h } "
               "agency { sala_id nafn heimilisfang postnumer simi email_tl vefslod logo logo_url } "
               "postal_code { postnr baer baer_thgf hverfi landshluti } "
               "promo { seckey }")

# mode -> config. draft = the publishable/non-draft predicate (excluded from aggregate).
MODECFG = {
    "seed-sale":  {"key": "seed_sale", "root": "fs_fasteign", "pk": "eign_id", "fields": SALE_FIELDS,
                   "draft": "syna:{_eq:true}, verd:{_gt:0}, fermetrar:{_gt:0}", "kind": "list_page_sale",
                   "op": "list_sale"},
    "seed-rent":  {"key": "seed_rent", "root": "rentals_property", "pk": "id", "fields": RENT_FIELDS,
                   "draft": "price:{_gt:0}, size:{_gt:0}", "kind": "list_page_rent", "op": "list_rent"},
    # supplementary "negotiable" slices: inverted price predicate (price/verd _eq:0). Each
    # SELF-ESTABLISHES its own frozen_max_id (no inheritance from the main seed): mbl hard-deletes
    # withdrawn listings, head-of-id newest rows skew negotiable, so reusing the publishable
    # ceiling would permanently miss them. Cross-mode overlap is resolved by §4 promotion dedup.
    "seed-sale-negotiable": {"key": "seed_sale_negotiable", "root": "fs_fasteign", "pk": "eign_id",
                   "fields": SALE_FIELDS, "draft": "syna:{_eq:true}, verd:{_eq:0}, fermetrar:{_gt:0}",
                   "kind": "list_page_sale_negotiable", "op": "seed_sale_negotiable"},
    "seed-rent-negotiable": {"key": "seed_rent_negotiable", "root": "rentals_property", "pk": "id",
                   "fields": RENT_FIELDS, "draft": "price:{_eq:0}, size:{_gt:0}",
                   "kind": "list_page_rent_negotiable", "op": "seed_rent_negotiable"},
    "delta-sale": {"key": "delta_sale", "root": "fs_fasteign", "pk": "eign_id", "fields": SALE_FIELDS,
                   "draft": "syna:{_eq:true}, verd:{_gt:0}, fermetrar:{_gt:0}", "kind": "list_page_sale",
                   "op": "delta_check_sale", "delta_field": "br_dags", "since_key": "last_br_dags_seen"},
    "delta-rent": {"key": "delta_rent", "root": "rentals_property", "pk": "id", "fields": RENT_FIELDS,
                   "draft": "price:{_gt:0}, size:{_gt:0}", "kind": "list_page_rent",
                   "op": "delta_check_rent", "delta_field": "updated", "since_key": "last_updated_seen"},
    # negotiable delta slices (§6-A.1 gap fix): plain delta carries the PUBLISHABLE predicate,
    # so Tilboð-population changes (72.3% of real rent corpus) were delta-blind in steady-state.
    # Each has its OWN high-water (own state dict); fetch_kind keeps the list_page_ prefix so
    # parse_mbl's kind->root mapping picks the blobs up unchanged, with a _delta discriminator
    # so the ledger separates delta pages from seed/re-sweep pages.
    "delta-sale-negotiable": {"key": "delta_sale_negotiable", "root": "fs_fasteign", "pk": "eign_id",
                   "fields": SALE_FIELDS, "draft": "syna:{_eq:true}, verd:{_eq:0}, fermetrar:{_gt:0}",
                   "kind": "list_page_sale_negotiable_delta", "op": "delta_check_sale_negotiable",
                   "delta_field": "br_dags", "since_key": "last_br_dags_seen"},
    "delta-rent-negotiable": {"key": "delta_rent_negotiable", "root": "rentals_property", "pk": "id",
                   "fields": RENT_FIELDS, "draft": "price:{_eq:0}, size:{_gt:0}",
                   "kind": "list_page_rent_negotiable_delta", "op": "delta_check_rent_negotiable",
                   "delta_field": "updated", "since_key": "last_updated_seen"},
}

# --mode choices (kept module-level so tests assert on it without invoking main()/the DB).
MODE_CHOICES = ["seed-sale", "seed-rent", "seed-sale-negotiable", "seed-rent-negotiable",
                "delta-sale", "delta-rent", "delta-sale-negotiable", "delta-rent-negotiable",
                "aggregate-check", "resume"]


class KillSwitch(RuntimeError):
    pass


class SchemaMissing(RuntimeError):
    pass


class AmbiguousResume(RuntimeError):
    def __init__(self, summary):
        self.summary = summary
        super().__init__("multiple modes in-flight")


@dataclass
class RunStats:
    pages: int = 0
    listings: int = 0
    new_blobs: int = 0
    changed1: int = 0
    changed0: int = 0


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _is_captcha(body: bytes) -> bool:
    low = (body or b"")[:4000].lower()
    return any(m in low for m in _CAPTCHA_MARKERS)


def default_state() -> dict:
    return {
        "seed_sale": {"frozen_max_id": None, "last_offset": 0, "total_fetched": 0,
                      "completed": False, "universe_pages": None, "last_run_at": None,
                      "last_page_at": None, "halt_reason": None},
        "seed_rent": {"frozen_max_id": None, "last_offset": 0, "total_fetched": 0,
                      "completed": False, "universe_pages": None, "last_run_at": None,
                      "last_page_at": None, "halt_reason": None},
        "seed_sale_negotiable": {"frozen_max_id": None, "last_offset": 0, "total_fetched": 0,
                      "completed": False, "universe_pages": None, "last_run_at": None,
                      "last_page_at": None, "halt_reason": None},
        "seed_rent_negotiable": {"frozen_max_id": None, "last_offset": 0, "total_fetched": 0,
                      "completed": False, "universe_pages": None, "last_run_at": None,
                      "last_page_at": None, "halt_reason": None},
        "delta_sale": {"last_br_dags_seen": None, "last_run_at": None, "halt_reason": None},
        "delta_rent": {"last_updated_seen": None, "last_run_at": None, "halt_reason": None},
        "delta_sale_negotiable": {"last_br_dags_seen": None, "last_run_at": None, "halt_reason": None},
        "delta_rent_negotiable": {"last_updated_seen": None, "last_run_at": None, "halt_reason": None},
        "session_request_count": 0,
    }


def load_state(path: str) -> dict:
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            st = json.load(fh)
        base = default_state()           # forward-compat: fill missing keys
        for k, v in base.items():
            st.setdefault(k, v)
            if isinstance(v, dict):
                for kk, vv in v.items():
                    st[k].setdefault(kk, vv)
        return st
    return default_state()


def save_state(path: str, state: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)               # atomic — no partial state on crash


def verify_schema(conn) -> bool:
    rows = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return {"raw_blobs", "raw_fetches"}.issubset(rows)


def synthetic_url(op, offset=None, since=None) -> str:
    # &fields=v2 = selection-generation marker (FIELDS_VERSION) so the enriched/scalar-only
    # blob generation boundary is visible in the raw_fetches ledger (P3 querystring-intent pattern).
    if offset is not None:
        base = "%s?op=%s&offset=%d" % (ENDPOINT, op, offset)
    elif since is not None:
        base = "%s?op=%s&since=%s" % (ENDPOINT, op, since)
    else:
        base = "%s?op=%s" % (ENDPOINT, op)
    return base + "&fields=v2"


# ── query builders (kept as functions so tests can assert on the strings) ──
def seed_query(cfg, frozen, offset):
    return ("query { %s(where:{%s:{_lte:%s}, %s}, order_by:{%s:desc}, limit:%d, offset:%d) { %s } }"
            % (cfg["root"], cfg["pk"], frozen, cfg["draft"], cfg["pk"], PAGE, offset, cfg["fields"]))


def delta_query(cfg, since, offset):
    return ('query { %s(where:{%s:{_gt:"%s"}, %s}, order_by:{%s:desc}, limit:%d, offset:%d) { %s } }'
            % (cfg["root"], cfg["delta_field"], since, cfg["draft"], cfg["pk"], PAGE, offset, cfg["fields"]))


def max_id_query(cfg):
    return ("query { %s(where:{%s}, order_by:{%s:desc}, limit:1) { %s } }"
            % (cfg["root"], cfg["draft"], cfg["pk"], cfg["pk"]))


AGG_QUERY = ("query { fs_fasteign_aggregate(where:{syna:{_eq:true}}){aggregate{count}} "
             "rentals_property_aggregate{aggregate{count}} }")


class MblFetcher:
    def __init__(self, session, conn, state, state_path, *, mode=None, max_pages=DEFAULT_MAX_PAGES,
                 min_spacing=DEFAULT_SPACING, dry_run=False, force_restart=False, log=print):
        self.s = session
        self.conn = conn
        self.state = state
        self.state_path = state_path
        self.mode = mode
        self.max_pages = max_pages
        self.min_spacing = max(MIN_SPACING_FLOOR, float(min_spacing))
        self.dry_run = dry_run
        self.force_restart = force_restart
        self.log = log
        self.stats = RunStats()
        self._consec_400 = 0
        self._consec_timeout = 0
        self._active_key = None
        self._sleep = time.sleep          # patchable in tests

    def _save(self):
        if not self.dry_run:              # dry-run mutates nothing
            save_state(self.state_path, self.state)

    # ── transport + kill-switch ──
    def _gql(self, query):
        for _ in range(3):
            try:
                r = self.s.post(ENDPOINT, json={"query": query},
                                headers={"User-Agent": UA, "Accept": "application/json",
                                         "Content-Type": "application/json"}, timeout=TIMEOUT_S)
            except requests.RequestException:
                self._consec_timeout += 1
                if self._consec_timeout >= MAX_CONSEC_TIMEOUT:
                    raise KillSwitch("%d consecutive timeouts" % self._consec_timeout)
                self._sleep(2)
                continue
            self._consec_timeout = 0
            status = r.status_code
            if status == 400:
                self._consec_400 += 1
                if self._consec_400 >= MAX_CONSEC_400:
                    raise KillSwitch("%d consecutive HTTP 400 — likely throttle" % self._consec_400)
                self._sleep(2)
                continue
            self._consec_400 = 0
            if status in (403, 429):
                raise KillSwitch("HTTP %s" % status)
            if status != 200:
                raise KillSwitch("unexpected HTTP %s" % status)
            body = r.content or b""
            ctype = (r.headers.get("content-type") or "application/json").split(";")[0].strip()
            if _is_captcha(body):
                raise KillSwitch("CAPTCHA/challenge body")
            try:
                data = json.loads(body)
            except Exception:
                raise KillSwitch("non-JSON 200 body")
            if isinstance(data, dict) and data.get("errors"):
                raise KillSwitch("GraphQL errors: %s" % json.dumps(data["errors"])[:200])
            self.state["session_request_count"] = self.state.get("session_request_count", 0) + 1
            return status, body, ctype, data
        raise KillSwitch("retries exhausted")

    # ── raw_mbl write (one tx per page) ──
    def _record_page(self, body, ctype, status, kind, url, n_listings):
        canon, chash = canonicalize_mbl(body, ctype)
        new_blob = self.conn.execute(
            "SELECT 1 FROM raw_blobs WHERE content_hash=?", (chash,)).fetchone() is None
        changed = 1 if new_blob else 0
        ts = now_iso()
        self.conn.execute(
            "INSERT OR IGNORE INTO raw_blobs(content_hash, blob_gz, content_type, byte_len, first_stored) "
            "VALUES(?,?,?,?,?)", (chash, gzip.compress(body), ctype, len(body), ts))
        self.conn.execute(
            "INSERT INTO raw_fetches(source, source_listing_id, url, fetch_kind, fetched_at, http_status, "
            "content_hash, changed, retry_count, parse_status) VALUES('mbl',NULL,?,?,?,?,?,?,0,'pending')",
            (url, kind, ts, status, chash, changed))
        self.conn.commit()
        self.stats.pages += 1
        self.stats.listings += n_listings
        self.stats.new_blobs += new_blob
        self.stats.changed1 += changed
        self.stats.changed0 += (1 - changed)
        return changed

    # ── seed (frozen-offset) ──
    def _seed(self, mode):
        cfg = MODECFG[mode]
        key = cfg["key"]
        self._active_key = key
        st = self.state[key]
        if st["completed"] and not self.force_restart:
            self.log("  %s already completed (use --force-restart to re-seed)" % mode)
            return
        if self.force_restart:
            # archive the old window before wiping — frozen_max_id/total_fetched of a finished
            # seed are otherwise unrecoverable (state file is overwritten in place)
            archived = dict(st)
            archived["archived_at"] = now_iso()
            self.state.setdefault(key + "_history", []).append(archived)
            st.update(default_state()[key])
        single = (mode != "seed-sale")                        # only main seed-sale is multi-night
        self.log("=== %s (%s) ===" % (mode, "single-run expected" if single
                                      else "MULTI-NIGHT ~861 pages"))

        if st["frozen_max_id"] is None:                       # establish frozen window once (self)
            if self.dry_run:
                self.log("  [dry-run] would query max %s + aggregate count to freeze the window" % cfg["pk"])
                st["frozen_max_id"] = 999999999
            else:
                _, _, _, d = self._gql(max_id_query(cfg))
                rows = d["data"][cfg["root"]]
                frozen = rows[0][cfg["pk"]] if rows else 0
                st["frozen_max_id"] = frozen
                _, _, _, da = self._gql(AGG_QUERY)
                cnt = da["data"][cfg["root"] + "_aggregate"]["aggregate"]["count"]
                st["universe_pages"] = math.ceil(cnt / PAGE)
                st["last_offset"] = 0
                save_state(self.state_path, self.state)
            self.log("  frozen_max_id=%s universe_pages=%s" % (st["frozen_max_id"], st.get("universe_pages")))
        frozen = st["frozen_max_id"]
        offset = st["last_offset"]
        pages_this_run = 0
        while pages_this_run < self.max_pages:
            q = seed_query(cfg, frozen, offset)
            if self.dry_run:
                self.log("  [dry-run] %s  ::  %s" % (synthetic_url(cfg["op"], offset), q[:90] + "..."))
                offset += PAGE
                pages_this_run += 1
                if pages_this_run >= min(3, self.max_pages):
                    self.log("  [dry-run] (capped at %d planned queries)" % pages_this_run)
                    break
                continue
            if pages_this_run > 0:
                self._sleep(self.min_spacing)
            status, body, ctype, data = self._gql(q)
            rows = data["data"][cfg["root"]]
            if not rows:
                st["completed"] = True
                st["last_offset"] = offset
                st["last_run_at"] = now_iso()
                save_state(self.state_path, self.state)
                self.log("  EXHAUSTED at offset %d — %s seed complete (%d listings)"
                         % (offset, mode, st["total_fetched"]))
                return
            self._record_page(body, ctype, status, cfg["kind"], synthetic_url(cfg["op"], offset), len(rows))
            offset += PAGE
            pages_this_run += 1
            st["last_offset"] = offset
            st["total_fetched"] += len(rows)
            st["last_page_at"] = now_iso()
            save_state(self.state_path, self.state)
            if st["universe_pages"] and (pages_this_run % 25 == 0):
                self.log("  ...page %d (offset %d) of ~%d" % (pages_this_run, offset, st["universe_pages"]))
        st["last_run_at"] = now_iso()
        self._save()
        self.log("  per-run budget reached (%d pages, offset %d/%s) — re-run --mode resume to continue"
                 % (pages_this_run, offset, st.get("universe_pages")))

    # ── delta ──
    def _delta(self, mode):
        cfg = MODECFG[mode]
        key = cfg["key"]
        self._active_key = key
        st = self.state[key]
        since = st.get(cfg["since_key"]) or "1970-01-01T00:00:00+00:00"
        self.log("=== %s (since %s) ===" % (mode, since))
        offset, pages = 0, 0
        high = since
        while pages < self.max_pages:
            q = delta_query(cfg, since, offset)
            if self.dry_run:
                self.log("  [dry-run] %s  ::  %s" % (synthetic_url(cfg["op"], since=since), q[:90] + "..."))
                break
            if pages > 0:
                self._sleep(self.min_spacing)
            status, body, ctype, data = self._gql(q)
            rows = data["data"][cfg["root"]]
            if not rows:
                break
            self._record_page(body, ctype, status, cfg["kind"],
                              synthetic_url(cfg["op"], since=since), len(rows))
            for rrow in rows:
                v = rrow.get(cfg["delta_field"])
                if v and (high is None or str(v) > str(high)):
                    high = v
            offset += PAGE
            pages += 1
        st[cfg["since_key"]] = high
        st["last_run_at"] = now_iso()
        self._save()
        self.log("  delta done — %d pages, new high-water %s = %s" % (pages, cfg["delta_field"], high))

    # ── aggregate-check (1 request, no writes) ──
    def aggregate_check(self):
        self.log("=== aggregate-check (1 request, no writes) ===")
        _, _, _, d = self._gql(AGG_QUERY)
        sc = d["data"]["fs_fasteign_aggregate"]["aggregate"]["count"]
        rc = d["data"]["rentals_property_aggregate"]["aggregate"]["count"]
        self.log("  sale_count=%d  rent_count=%d  (~%d sale pages, ~%d rent pages @ 16/page)"
                 % (sc, rc, math.ceil(sc / PAGE), math.ceil(rc / PAGE)))
        return sc, rc

    # ── resume (R1: refuse if multiple in-flight) ──
    def in_flight(self):
        out = []
        for mode in ("seed-sale", "seed-rent", "seed-sale-negotiable", "seed-rent-negotiable",
                     "delta-sale", "delta-rent", "delta-sale-negotiable", "delta-rent-negotiable"):
            s = self.state[MODECFG[mode]["key"]]
            if mode.startswith("seed"):
                started = (s.get("frozen_max_id") is not None and not s.get("completed")) or s.get("halt_reason")
            else:
                started = bool(s.get("halt_reason"))
            if started:
                out.append(mode)
        return out

    def resume(self):
        inflight = self.in_flight()
        if not inflight:
            self.log("nothing in-flight to resume.")
            return
        if len(inflight) > 1:
            summary = []
            for mode in inflight:
                s = self.state[MODECFG[mode]["key"]]
                summary.append("  %-11s offset %s/%s, halt_reason: %s"
                               % (MODECFG[mode]["key"] + ":", s.get("last_offset", "-"),
                                  s.get("universe_pages", "-"), s.get("halt_reason")))
            raise AmbiguousResume("\n".join(summary))
        return self.dispatch(inflight[0])

    def dispatch(self, mode):
        if mode in ("seed-sale", "seed-rent", "seed-sale-negotiable", "seed-rent-negotiable"):
            return self._seed(mode)
        if mode in ("delta-sale", "delta-rent", "delta-sale-negotiable", "delta-rent-negotiable"):
            return self._delta(mode)
        if mode == "aggregate-check":
            return self.aggregate_check()
        raise ValueError("unknown mode %r" % mode)

    def run(self):
        if self.mode != "aggregate-check" and not self.dry_run and not verify_schema(self.conn):
            raise SchemaMissing("raw_mbl.db missing raw_blobs/raw_fetches — run init_raw_mbl_schema.py")
        try:
            if self.mode == "resume":
                return self.resume()
            return self.dispatch(self.mode)
        except KillSwitch as e:
            if self._active_key:
                self.state[self._active_key]["halt_reason"] = str(e)
                self.state[self._active_key]["last_run_at"] = now_iso()
                save_state(self.state_path, self.state)
            raise


def main():
    ap = argparse.ArgumentParser(description="mbl Hasura GraphQL raw fetcher")
    ap.add_argument("--mode", required=True, choices=MODE_CHOICES)
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    ap.add_argument("--min-spacing-sec", type=float, default=DEFAULT_SPACING)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-restart", action="store_true")
    ap.add_argument("--state-file", default=DEFAULT_STATE_PATH)
    args = ap.parse_args()

    state = load_state(args.state_file)
    conn = sqlite3.connect(str(get_raw_db_path("mbl")))
    conn.execute("PRAGMA foreign_keys=ON")
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    f = MblFetcher(session, conn, state, args.state_file, mode=args.mode, max_pages=args.max_pages,
                   min_spacing=args.min_spacing_sec, dry_run=args.dry_run,
                   force_restart=args.force_restart)
    print("mbl_fetch %s  mode=%s  dry_run=%s  spacing=%.0fs  max_pages=%d"
          % (FETCHER_VERSION, args.mode, args.dry_run, f.min_spacing, args.max_pages))
    try:
        f.run()
    except AmbiguousResume as e:
        print("ERROR: Multiple modes in-flight:\n%s\nSpecify --mode explicitly." % e.summary)
        return 1
    except SchemaMissing as e:
        print("SCHEMA ERROR: %s" % e)
        return 1
    except KillSwitch as e:
        print("\n!! KILL-SWITCH: %s" % e)
        return 2
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
