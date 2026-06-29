#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harvest.py — Harvest open public datasets (HMS + Hagstofa) to disk + manifest.

NO DB writes, NO schema, NO migrations. Download + manifest only.

Idempotent: if a file is already present on disk and its sha256 matches the
MANIFEST entry, it is skipped (no re-download). Run with --force to re-fetch.

Data lands OUTSIDE the git repo at  D:\\verdmat-is\\data\\raw\\opin_gogn\\
(the repo root is D:\\verdmat-is\\app). MANIFEST.json there is authoritative
for what is on disk.

Resolvers fetch each landing page and extract the download link from the HTML
(OCI objectstorage, Azure blob, or Prismic CDN). No hard-coded hashed URLs
except where a landing page is only a dashboard/viewer.

Tiers:
  TIER 1   HMS base CSVs (kaupskra, leiguskra, stadfangaskra)   -> download
  TIER 1b  HMS indices + leiguverdsja CSV                       -> download
           HMS dashboards (maelabord*) with no bulk file        -> manifest only
  TIER 1c  Hagstofa PxWeb greiningarvisitolur (VIS011xx)        -> download
           + secondary building/housing tables (small only)
  TIER 2   mannvirkjaskra / landeignaskra viewers (no bulk file)-> manifest only
  TIER 3   geo files (zip) — RESOLVE + HEAD size, do NOT download (await Danni)

Usage:
  python harvest.py            # idempotent harvest, prints summary
  python harvest.py --force    # re-download everything
  python harvest.py --tier3    # ALSO download Tier-3 geo files (<200MB each)
"""

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
import time

import requests

try:
    from charset_normalizer import from_bytes as _cn_from_bytes
except Exception:  # pragma: no cover
    _cn_from_bytes = None

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
RAW_DIR = r"D:\verdmat-is\data\raw\opin_gogn"
MANIFEST_PATH = os.path.join(RAW_DIR, "MANIFEST.json")
UA = "Mozilla/5.0 (harvest opin_gogn; verdmat-is; +daniel.thor.magnusson@gmail.com)"
HEADERS = {"User-Agent": UA}
TIMEOUT = 90
TIER3_MAX_BYTES = 200 * 1024 * 1024  # 200 MB gate for Tier-3
SECONDARY_PX_MAX_CELLS = 200_000     # skip secondary PxWeb tables bigger than this

LINKRE = re.compile(r'https?://[^\s"\'<>()]+')
HMS_LICENSE = "HMS opin gogn (public open data, hms.is)"
HAGSTOFA_LICENSE = "Hagstofa Islands / Statistics Iceland (open, attribution)"

session = requests.Session()
session.headers.update(HEADERS)


def utcnow():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def fetch_html(url):
    r = session.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text.replace("\\u0026", "&")


def resolve_links(landing_url, keywords):
    """Fetch a landing page and return candidate download URLs matching keywords."""
    html = fetch_html(landing_url)
    links = set(LINKRE.findall(html))
    out = []
    for l in sorted(links):
        ll = l.lower()
        if any(k in ll for k in keywords):
            out.append(l)
    return out


def pick(cands, hint):
    """Pick the candidate whose URL contains hint (case-insensitive)."""
    for c in cands:
        if hint.lower() in c.lower():
            return c
    return None


def sha256_file(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def detect_encoding(sample_bytes):
    if _cn_from_bytes is None:
        return None
    try:
        best = _cn_from_bytes(sample_bytes).best()
        return best.encoding if best else None
    except Exception:
        return None


def sniff_delimiter(line):
    counts = {d: line.count(d) for d in [";", ",", "\t", "|"]}
    delim = max(counts, key=counts.get)
    return delim if counts[delim] > 0 else ","


def csv_profile(path, encoding):
    """Return (n_rows_excl_header, header_list)."""
    enc = encoding or "utf-8"
    n = 0
    header = None
    # read first line for header/delimiter using detected encoding
    with open(path, "rb") as fb:
        first = fb.readline()
    try:
        first_txt = first.decode(enc, errors="replace")
    except Exception:
        first_txt = first.decode("utf-8", errors="replace")
    first_txt = first_txt.lstrip("﻿")
    delim = sniff_delimiter(first_txt)
    header = next(csv.reader([first_txt], delimiter=delim), None)
    # count rows cheaply
    with open(path, "rb") as fb:
        for _ in fb:
            n += 1
    n_rows = max(n - 1, 0)
    return n_rows, header, delim


def download(url, dest):
    """Stream-download url to dest. Returns bytes written."""
    tmp = dest + ".part"
    total = 0
    with session.get(url, timeout=TIMEOUT, stream=True) as r:
        r.raise_for_status()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
    os.replace(tmp, dest)
    return total


def head_size(url):
    try:
        r = session.head(url, timeout=TIMEOUT, allow_redirects=True)
        cl = r.headers.get("content-length")
        return int(cl) if cl is not None else None, r.headers.get("content-type")
    except Exception as e:
        return None, "HEAD_ERR: %s" % e


def fmt_of(name):
    n = name.lower()
    for ext in (".csv", ".zip", ".json", ".px", ".xlsx", ".gdb"):
        if n.endswith(ext):
            return ext.lstrip(".")
    return "bin"


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #
def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {e["name"]: e for e in data.get("entries", [])}
    return {}


def save_manifest(entries_by_name):
    os.makedirs(RAW_DIR, exist_ok=True)
    entries = sorted(entries_by_name.values(), key=lambda e: (e.get("source", ""), e["name"]))
    doc = {
        "generated_at": utcnow(),
        "root": RAW_DIR,
        "n_entries": len(entries),
        "entries": entries,
    }
    tmp = MANIFEST_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    os.replace(tmp, MANIFEST_PATH)


def upsert(man, entry):
    man[entry["name"]] = entry


# --------------------------------------------------------------------------- #
# Core: process one downloadable file
# --------------------------------------------------------------------------- #
def harvest_file(man, *, name, landing_url, file_url, subdir, fname, source,
                 cadence, license_, notes="", force=False, is_csv=None):
    """Download (idempotently), profile, and upsert a manifest entry."""
    dest = os.path.join(RAW_DIR, subdir, fname)
    fmt = fmt_of(fname)
    if is_csv is None:
        is_csv = fmt == "csv"

    # Idempotency: existing entry + file present + sha matches -> skip
    existing = man.get(name)
    if (not force and existing and existing.get("sha256")
            and os.path.exists(dest)):
        cur = sha256_file(dest)
        if cur == existing["sha256"]:
            log("  SKIP (unchanged): %s" % name)
            return existing

    log("  GET  %s  <- %s" % (name, file_url))
    try:
        nbytes = download(file_url, dest)
    except Exception as e:
        log("  !! download FAILED %s: %s" % (name, e))
        entry = (existing or {}).copy()
        entry.update(dict(
            name=name, source=source, landing_url=landing_url, file_url=file_url,
            local_path=None, fetched_at=utcnow(), bytes=None, sha256=None,
            format=fmt, encoding=None, n_rows=None, columns=None,
            license=license_, cadence=cadence,
            notes=(notes + " | DOWNLOAD FAILED: %s" % e).strip(" |"),
        ))
        upsert(man, entry)
        return entry

    sha = sha256_file(dest)
    encoding = None
    n_rows = None
    columns = None
    delim = None
    if is_csv:
        with open(dest, "rb") as fb:
            sample = fb.read(262144)
        encoding = detect_encoding(sample)
        try:
            n_rows, columns, delim = csv_profile(dest, encoding)
        except Exception as e:
            notes = (notes + " | csv_profile error: %s" % e).strip(" |")

    entry = dict(
        name=name, source=source, landing_url=landing_url, file_url=file_url,
        local_path=dest, fetched_at=utcnow(), bytes=nbytes, sha256=sha,
        format=fmt, encoding=encoding, n_rows=n_rows, columns=columns,
        delimiter=delim, license=license_, cadence=cadence, notes=notes,
    )
    upsert(man, entry)
    log("    ok  bytes=%s enc=%s n_rows=%s" % (nbytes, encoding, n_rows))
    return entry


def manifest_only(man, *, name, landing_url, file_url, source, cadence,
                  license_, notes, fmt=None, bytes_=None):
    entry = dict(
        name=name, source=source, landing_url=landing_url, file_url=file_url,
        local_path=None, fetched_at=utcnow(), bytes=bytes_, sha256=None,
        format=fmt, encoding=None, n_rows=None, columns=None, delimiter=None,
        license=license_, cadence=cadence, notes=notes,
    )
    upsert(man, entry)
    log("  NOTE %s -> %s" % (name, notes[:70]))
    return entry


# --------------------------------------------------------------------------- #
# PxWeb (Hagstofa)
# --------------------------------------------------------------------------- #
PX_API = "https://px.hagstofa.is/pxis/api/v1/is/"


def px_get(path):
    r = session.get(PX_API + path, timeout=TIMEOUT)
    r.encoding = "utf-8"
    r.raise_for_status()
    return r


def px_list(folder):
    """Return list of dicts for a folder (tables have type 't')."""
    r = px_get(folder)
    return r.json()


def px_table_meta(table_path):
    r = px_get(table_path)
    return r.json()


def px_download_csv(table_path, meta):
    q = {
        "query": [
            {"code": v["code"], "selection": {"filter": "all", "values": ["*"]}}
            for v in meta["variables"]
        ],
        "response": {"format": "csv"},
    }
    r = session.post(PX_API + table_path, data=json.dumps(q),
                     headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content


def harvest_pxweb_table(man, *, table_id, folder_path, source, subdir,
                        notes_extra="", force=False, max_cells=None):
    """Download a PxWeb table as CSV (UTF-8-BOM) + save .px metadata JSON."""
    tp = folder_path.rstrip("/") + "/" + table_id  # e.g. .../VIS01106.px
    name = "pxweb_" + table_id.replace(".px", "")
    try:
        meta = px_table_meta(tp)
    except Exception as e:
        return manifest_only(man, name=name,
                             landing_url=PX_API + folder_path, file_url=PX_API + tp,
                             source=source, cadence="monthly",
                             license_=HAGSTOFA_LICENSE,
                             notes="PxWeb meta fetch failed: %s" % e, fmt="csv")
    vars_ = meta.get("variables", [])
    cells = 1
    for v in vars_:
        cells *= max(len(v.get("values", [])), 1)
    var_desc = "; ".join("%s(%d)" % (v["code"], len(v.get("values", []))) for v in vars_)
    title = meta.get("title", "")

    if max_cells is not None and cells > max_cells:
        return manifest_only(man, name=name,
                             landing_url=PX_API + folder_path, file_url=PX_API + tp,
                             source=source, cadence="monthly",
                             license_=HAGSTOFA_LICENSE,
                             notes=("SKIPPED (too large for secondary tier): ~%d cells; "
                                    "vars=%s; title=%s. %s"
                                    % (cells, var_desc, title, notes_extra)).strip(),
                             fmt="csv")

    dest = os.path.join(RAW_DIR, subdir, table_id.replace(".px", "") + ".csv")
    meta_dest = os.path.join(RAW_DIR, subdir, table_id.replace(".px", "") + ".meta.json")
    existing = man.get(name)

    # Save metadata JSON (always cheap)
    os.makedirs(os.path.dirname(meta_dest), exist_ok=True)
    with open(meta_dest, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    if not force and existing and existing.get("sha256") and os.path.exists(dest):
        if sha256_file(dest) == existing["sha256"]:
            log("  SKIP (unchanged): %s" % name)
            return existing

    log("  POST %s  (~%d cells)" % (name, cells))
    try:
        content = px_download_csv(tp, meta)
    except Exception as e:
        return manifest_only(man, name=name,
                             landing_url=PX_API + folder_path, file_url=PX_API + tp,
                             source=source, cadence="monthly",
                             license_=HAGSTOFA_LICENSE,
                             notes="PxWeb data POST failed: %s" % e, fmt="csv")

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(content)
    sha = sha256_file(dest)
    try:
        n_rows, columns, delim = csv_profile(dest, "utf-8-sig")
    except Exception:
        n_rows, columns, delim = None, None, None
    entry = dict(
        name=name, source=source,
        landing_url=PX_API + folder_path, file_url=PX_API + tp,
        local_path=dest, fetched_at=utcnow(), bytes=len(content), sha256=sha,
        format="csv", encoding="utf-8-sig", n_rows=n_rows, columns=columns,
        delimiter=delim, license=HAGSTOFA_LICENSE, cadence="monthly",
        notes=("PxWeb %s | title=%s | vars=%s | meta=%s | %s"
               % (table_id, title, var_desc, os.path.basename(meta_dest), notes_extra)).strip(" |"),
    )
    upsert(man, entry)
    log("    ok  bytes=%s n_rows=%s" % (len(content), n_rows))
    return entry


# --------------------------------------------------------------------------- #
# Job definitions
# --------------------------------------------------------------------------- #
GRUNN = "https://hms.is/gogn-og-maelabord/grunngogntilnidurhals/"

# (name, landing subpage, link keyword hint, subdir, fname, source, cadence)
HMS_DOWNLOADS = [
    ("kaupskra", GRUNN + "kaupskra-fasteigna", "kaupskra.csv",
     "hms/grunngogn", "kaupskra.csv", "hms_grunngogn", "monthly"),
    ("leiguskra", GRUNN + "leiguskra-thinglystra-leigusamninga-ibudarhusnaedis",
     "leiguskra.csv", "hms/grunngogn", "leiguskra.csv", "hms_grunngogn", "monthly"),
    ("stadfangaskra", GRUNN + "stadfangaskra", "stadfangaskra.csv",
     "hms/grunngogn", "Stadfangaskra.csv", "hms_grunngogn", "monthly"),
    ("kaupvisitala", "https://hms.is/gogn-og-maelabord/visitolur", "kaupvisitala.csv",
     "hms/visitolur", "kaupvisitala.csv", "hms_visitolur", "monthly"),
    ("leiguvisitala", "https://hms.is/gogn-og-maelabord/visitolur", "leiguvisitala.csv",
     "hms/visitolur", "leiguvisitala.csv", "hms_visitolur", "monthly"),
    ("leiguverdsja", "https://hms.is/gogn-og-maelabord/maelabordleiguskra/leiguverdsja",
     "leiguverdsja", "hms/leiguverdsja", "leiguverdsja.csv", "hms_leiguverdsja", "monthly"),
]

# Tier-3 geo: resolve + HEAD only, do NOT download unless --tier3
HMS_TIER3 = [
    ("aaetlun_eignamarka", GRUNN + "aaetlun-eignamarka", ".zip",
     "geo_tier3", "HMS_AETLUN.zip", "hms_tier3_geo"),
    ("landeignaskra_zip", GRUNN + "landeignaskrazip", ".zip",
     "geo_tier3", "Landeignaskra.zip", "hms_tier3_geo"),
    ("nytjaland_2006", GRUNN + "nytjaland-2006", ".zip",
     "geo_tier3", "Nytjaland2006.zip", "hms_tier3_geo"),
]

# Dashboards / viewers with no bulk download
HMS_DASHBOARDS = [
    ("maelabord_leiguskra", "https://hms.is/gogn-og-maelabord/maelabordleiguskra",
     "Fjoldi samninga eftir svaedi/leigusalategund. Power BI dashboard embed, "
     "engin bulk-CSV a sidu. Underlying registry = leiguskra.csv (sott)."),
    ("maelabord_fasteignaskra", "https://hms.is/gogn-og-maelabord/maelabordfasteignaskra",
     "Kaupsamningar eftir sveitarfelagi, fyrstu kaupendur. Power BI dashboard embed, "
     "engin bulk-CSV a sidu. Underlying registry = kaupskra.csv (sott)."),
    ("mannvirkjaskra", "https://hms.is/mannvirkjaskra",
     "Staerdir/eiginleikar mannvirkja, byggingarleyfi. Upplysingasida + uppfletti-"
     "thjonusta, engin opin bulk-skra. Tharf resolver/API-adgang ef bulk tharf."),
    ("landeignaskra_vefsja", "https://landeignaskra.hms.is/",
     "Hnitsett landeignir — Vefsja (interactive map viewer), engin bulk-nidurhal a "
     "sidu. Bulk-jafngildi = Tier-3 Landeignaskra.zip (sja landeignaskra_zip)."),
]

PX_FOLDER = "Efnahagur/visitolur/1_vnv/3_greiningarvisitolur"
PX_CORE = ["VIS01101.px", "VIS01103.px", "VIS01106.px"]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def run(force=False, do_tier3=False):
    man = load_manifest()
    os.makedirs(RAW_DIR, exist_ok=True)

    log("\n=== TIER 1 / 1b: HMS downloadable CSVs ===")
    for name, landing, hint, subdir, fname, source, cadence in HMS_DOWNLOADS:
        try:
            cands = resolve_links(landing, ["objectstorage", "public_data", "prismic.io/hms",
                                            ".csv", "blob.core.windows.net"])
            url = pick(cands, hint)
            if not url:
                manifest_only(man, name=name, landing_url=landing, file_url=None,
                              source=source, cadence=cadence, license_=HMS_LICENSE,
                              notes="RESOLVER FOUND NO LINK matching hint '%s'. cands=%s"
                                    % (hint, cands[:5]), fmt="csv")
                continue
            harvest_file(man, name=name, landing_url=landing, file_url=url,
                         subdir=subdir, fname=fname, source=source,
                         cadence=cadence, license_=HMS_LICENSE, force=force)
        except Exception as e:
            manifest_only(man, name=name, landing_url=landing, file_url=None,
                          source=source, cadence=cadence, license_=HMS_LICENSE,
                          notes="ERROR: %s" % e, fmt="csv")
        save_manifest(man)

    log("\n=== TIER 1b / 2: HMS dashboards & viewers (manifest only) ===")
    for name, landing, notes in HMS_DASHBOARDS:
        manifest_only(man, name=name, landing_url=landing, file_url=None,
                      source="hms_dashboard", cadence="dashboard",
                      license_=HMS_LICENSE,
                      notes="adeins embed/vefsja — " + notes)
    save_manifest(man)

    log("\n=== TIER 3: HMS geo (resolve + HEAD, gate %d MB) ===" % (TIER3_MAX_BYTES // 1024 // 1024))
    for name, landing, hint, subdir, fname, source in HMS_TIER3:
        try:
            cands = resolve_links(landing, ["objectstorage", "blob.core.windows.net",
                                            "prismic.io/hms", ".zip"])
            url = pick(cands, ".zip") or (cands[0] if cands else None)
            if not url:
                manifest_only(man, name=name, landing_url=landing, file_url=None,
                              source=source, cadence="static", license_=HMS_LICENSE,
                              notes="TIER3 RESOLVER FOUND NO LINK. cands=%s" % cands[:5],
                              fmt="zip")
                continue
            size, ctype = head_size(url)
            if do_tier3 and size is not None and size <= TIER3_MAX_BYTES:
                harvest_file(man, name=name, landing_url=landing, file_url=url,
                             subdir=subdir, fname=fname, source=source,
                             cadence="static", license_=HMS_LICENSE,
                             notes="Tier-3 geo zip (fetched via --tier3)",
                             force=force, is_csv=False)
            else:
                gate = (">200MB" if (size or 0) > TIER3_MAX_BYTES else "awaiting --tier3 / Danni")
                manifest_only(man, name=name, landing_url=landing, file_url=url,
                              source=source, cadence="static", license_=HMS_LICENSE,
                              notes="TIER3 geo (%s) — NOT downloaded (%s). content-type=%s"
                                    % (fname, gate, ctype),
                              fmt="zip", bytes_=size)
        except Exception as e:
            manifest_only(man, name=name, landing_url=landing, file_url=None,
                          source=source, cadence="static", license_=HMS_LICENSE,
                          notes="TIER3 ERROR: %s" % e, fmt="zip")
        save_manifest(man)

    log("\n=== TIER 1c: Hagstofa PxWeb greiningarvisitolur ===")
    try:
        listing = px_list(PX_FOLDER)
        present = {x["id"] for x in listing if x.get("type") == "t"}
        log("  folder tables: %s" % sorted(present))
        for tid in sorted(present):  # grab ALL tables in this folder (rent/CPI analysis)
            harvest_pxweb_table(man, table_id=tid, folder_path=PX_FOLDER,
                                source="hagstofa_greiningarvisitolur",
                                subdir="hagstofa/greiningarvisitolur",
                                notes_extra="folder=greiningarvisitolur (rent/CPI analysis)",
                                force=force)
            save_manifest(man)
    except Exception as e:
        manifest_only(man, name="pxweb_greiningarvisitolur_FOLDER",
                      landing_url=PX_API + PX_FOLDER, file_url=None,
                      source="hagstofa_greiningarvisitolur", cadence="monthly",
                      license_=HAGSTOFA_LICENSE, notes="PxWeb folder enumerate failed: %s" % e)
        save_manifest(man)

    log("\n=== TIER 1c (secondary): building/housing PxWeb inventory ===")
    harvest_pxweb_secondary(man, force=force)
    save_manifest(man)

    save_manifest(man)
    print_summary(man)
    return man


# Curated relevant subtrees (the task's old Atvinnuvegir__byggingariðnaður /
# Mannfjöldi__heimili paths no longer exist; the tree was reorganized).
#   Atvinnuvegir/idnadur/byggingar = "Bygging íbúðarhúsnæðis" (residential construction)
#   Ibuar/manntal/1_yfirlit        = census overview incl. dwellings/households
SECONDARY_SEED_FOLDERS = [
    "Atvinnuvegir/idnadur/byggingar",
    "Ibuar/manntal/1_yfirlit",
]
SECONDARY_MAX_DEPTH = 3
SECONDARY_MAX_TABLES = 80  # bound the inventory so it can't balloon


def harvest_pxweb_secondary(man, force=False):
    """Bounded walk of curated building/housing subtrees; inventory all tables
    found, fetch the small ones (< SECONDARY_PX_MAX_CELLS), record the rest."""
    seen_tables = []  # (folder_path, table_node)

    def walk(path, depth):
        if depth > SECONDARY_MAX_DEPTH or len(seen_tables) >= SECONDARY_MAX_TABLES:
            return
        try:
            items = px_list(path)
        except Exception as e:
            log("  cannot list %s: %s" % (path, e))
            return
        for it in items:
            if len(seen_tables) >= SECONDARY_MAX_TABLES:
                return
            if it.get("type") == "t":
                seen_tables.append((path, it))
            elif it.get("type") == "l":
                walk(path + "/" + (it.get("id") or it.get("text")), depth + 1)

    for seed in SECONDARY_SEED_FOLDERS:
        walk(seed, 1)

    log("  secondary tables discovered: %d (cap %d)" % (len(seen_tables), SECONDARY_MAX_TABLES))
    inventoried = 0
    fetched = 0
    for folder, it in seen_tables:
        tid = it["id"]
        inventoried += 1
        try:
            e = harvest_pxweb_table(
                man, table_id=tid, folder_path=folder,
                source="hagstofa_secondary", subdir="hagstofa/secondary",
                notes_extra="folder=%s | %s" % (folder, it.get("text", "")),
                force=force, max_cells=SECONDARY_PX_MAX_CELLS)
            if e.get("local_path"):
                fetched += 1
        except Exception as ex:
            manifest_only(man, name="pxweb_" + tid.replace(".px", ""),
                          landing_url=PX_API + folder, file_url=PX_API + folder + "/" + tid,
                          source="hagstofa_secondary", cadence="monthly",
                          license_=HAGSTOFA_LICENSE,
                          notes="secondary fetch error: %s" % ex, fmt="csv")
        save_manifest(man)
    log("  secondary: inventoried=%d fetched=%d" % (inventoried, fetched))


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #
def print_summary(man):
    entries = sorted(man.values(), key=lambda e: (e.get("source", ""), e["name"]))
    log("\n" + "=" * 78)
    log("MANIFEST SUMMARY  (%s)" % MANIFEST_PATH)
    log("=" * 78)
    total_bytes = 0
    fmt = "%-26s %-22s %12s %9s %-10s"
    log(fmt % ("name", "source", "bytes", "n_rows", "cadence"))
    log("-" * 78)
    for e in entries:
        b = e.get("bytes")
        if e.get("local_path") and b:
            total_bytes += b
        log(fmt % (e["name"][:26], (e.get("source") or "")[:22],
                   ("" if b is None else "{:,}".format(b)),
                   ("" if e.get("n_rows") is None else "{:,}".format(e["n_rows"])),
                   (e.get("cadence") or "")[:10]))
    log("-" * 78)
    log("Total on-disk bytes: {:,} ({:.1f} MB)".format(total_bytes, total_bytes / 1024 / 1024))

    waiting = [e for e in entries if e.get("cadence") == "static"
               and not e.get("local_path") and e.get("file_url")]
    if waiting:
        log("\nTIER-3 files RESOLVED but NOT downloaded (awaiting decision):")
        for e in waiting:
            log("  - %-22s %12s  %s" % (
                e["name"],
                ("?" if e.get("bytes") is None else "{:,} B".format(e["bytes"])),
                e.get("file_url")))

    def is_failure(e):
        n = (e.get("notes") or "")
        if e.get("source") in ("hagstofa_secondary",) and "SKIPPED" in n:
            return False  # intentional size-skip, reported separately
        markers = ("RESOLVER FOUND NO LINK", "TIER3 RESOLVER FOUND NO LINK",
                   "DOWNLOAD FAILED", "ERROR:", "TIER3 ERROR", "failed", "FAILED",
                   "csv_profile error")
        return any(m in n for m in markers)

    unresolved = [e for e in entries if is_failure(e)]
    if unresolved:
        log("\nUNRESOLVED / failed:")
        for e in unresolved:
            log("  - %-22s %s" % (e["name"], (e.get("notes") or "")[:90]))
    else:
        log("\nUNRESOLVED / failed: none")

    skipped_big = [e for e in entries if "SKIPPED" in (e.get("notes") or "")]
    if skipped_big:
        log("\nSecondary PxWeb tables INVENTORIED but not fetched (size gate):")
        for e in skipped_big:
            log("  - %-26s %s" % (e["name"], (e.get("notes") or "")[:80]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download everything")
    ap.add_argument("--tier3", action="store_true",
                    help="also download Tier-3 geo files (<200MB each)")
    args = ap.parse_args()
    run(force=args.force, do_tier3=args.tier3)
