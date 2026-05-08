"""
image_archive_analyzer.py — read-only inventory of existing D:\ image archive.

Reads the path list saved by the prior PowerShell scan, groups by fastnum
(parent dir name), counts coverage against Supabase properties, samples
augl_json URLs from D:\\Gagnapakkar\\fasteignir*.db and checks file
existence, and surfaces the cross-property URL bug posture.

Output is printed; the inventory report is composed by hand from this.
"""

from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PATHS_FILE = Path(r"C:\Users\danie\AppData\Local\Temp\image_paths.txt")
LEGACY_DBS = [
    r"D:\Gagnapakkar\fasteignir.db",
    r"D:\Gagnapakkar\fasteignir1.db",
    r"D:\Gagnapakkar\fasteignir2.db",
    r"D:\Gagnapakkar\fasteignir3.db",
    r"D:\Gagnapakkar\fasteignir4.db",
]
PILOT_DB = Path(r"D:\verdmat-is\app\audit\backfill_pilot.db")

CF_RE = re.compile(
    r"https://d1u57vh96em4i1\.cloudfront\.net/(\d+)/([A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp))",
    re.IGNORECASE,
)
FASTNUM_RE = re.compile(r"^\d{7}$")  # canonical 7-digit fastnums (HMS issuance range)


def load_paths():
    paths = PATHS_FILE.read_text(encoding="utf-8").splitlines()
    return [p for p in paths if p.strip()]


def parent_dir_name(p):
    """Last directory component, e.g. '2526172' for 'D:\\Gagnapakki 4\\myndir\\2526172\\foo.jpg'."""
    return os.path.basename(os.path.dirname(p))


def main():
    paths = load_paths()
    print(f"Loaded {len(paths):,} image paths")
    print()

    # 1. group paths by parent dir name
    print("=" * 60)
    print("1. PARENT DIRECTORY ANALYSIS")
    print("=" * 60)
    by_parent = defaultdict(list)
    for p in paths:
        by_parent[parent_dir_name(p)].append(p)

    n_parents = len(by_parent)
    fastnum_parents = {k: v for k, v in by_parent.items() if FASTNUM_RE.match(k)}
    print(f"  Distinct parent-dir names: {n_parents:,}")
    print(f"  Parents matching 7-digit fastnum pattern: {len(fastnum_parents):,}")
    print(f"  Non-fastnum parents: {n_parents - len(fastnum_parents):,}")
    # Show top non-fastnum parents
    non_fn = [(k, len(v)) for k, v in by_parent.items() if not FASTNUM_RE.match(k)]
    non_fn.sort(key=lambda x: -x[1])
    print(f"  Top 10 non-fastnum parents (by count):")
    for k, n in non_fn[:10]:
        print(f"    [{n:,} files]  parent='{k}'")
    print()

    # 2. fastnum-keyed coverage: how many distinct fastnum-folders exist
    print("=" * 60)
    print("2. FASTNUM-KEYED COVERAGE")
    print("=" * 60)
    distinct_fastnums = set(fastnum_parents.keys())
    print(f"  Distinct 7-digit fastnums with ≥1 image folder: {len(distinct_fastnums):,}")
    # Break down by ROOT (e.g., 'Gagnapakki 1', 'Gagnapakki 4 - fasteignir', etc.)
    by_root = defaultdict(set)
    for p in paths:
        # extract root: e.g. 'D:\\Gagnapakki 1\\' or 'D:\\Gagnapakkar\\images\\'
        # find component-2 of the path
        parts = Path(p).parts
        if len(parts) >= 2:
            root = parts[1]  # e.g. 'Gagnapakki 1'
            fn = parent_dir_name(p)
            if FASTNUM_RE.match(fn):
                by_root[root].add(fn)
    print(f"  By root directory (count of distinct fastnums per root):")
    for root, fns in sorted(by_root.items(), key=lambda x: -len(x[1])):
        print(f"    [{len(fns):>6,} fastnums]  D:\\{root}\\")
    print()

    # 3. Sample 30 random paths
    print("=" * 60)
    print("3. SAMPLE 30 RANDOM PATHS (naming convention check)")
    print("=" * 60)
    rng = random.Random(20260508)
    sample = rng.sample(paths, min(30, len(paths)))
    for p in sample:
        size = os.path.getsize(p)
        print(f"  [{size:>9,} b]  {p}")
    print()

    # 4. cross-ref existing legacy DBs for augl_json URLs
    print("=" * 60)
    print("4. LEGACY DB AUGL_JSON URL CROSS-REF")
    print("=" * 60)
    on_disk_set = set()
    for p in paths:
        # build a "fastnum/basename" key
        fn = parent_dir_name(p)
        bn = os.path.basename(p)
        on_disk_set.add(f"{fn}/{bn}")
    print(f"  Built on-disk set: {len(on_disk_set):,} unique <fastnum>/<basename> pairs")
    print()

    overall_seen_urls = 0
    overall_matches_disk = 0
    total_rows_with_augl = 0
    sample_rows_examined = 0
    SAMPLE_PER_DB = 200
    for db_path in LEGACY_DBS:
        if not os.path.exists(db_path):
            print(f"  {db_path}: not found, skip")
            continue
        try:
            conn = sqlite3.connect(db_path)
            # Probe schema
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            print(f"  {os.path.basename(db_path)}: tables={tables}")
            if "fasteignir" not in tables:
                conn.close()
                continue
            cur = conn.cursor()
            # Count rows with non-empty augl_json
            (n_aug,) = cur.execute(
                "SELECT COUNT(*) FROM fasteignir WHERE augl_json IS NOT NULL AND length(augl_json) > 50"
            ).fetchone()
            total_rows_with_augl += n_aug
            print(f"    rows with augl_json: {n_aug:,}")
            # Sample rows
            rows = cur.execute(
                "SELECT fastnum, augl_json FROM fasteignir "
                "WHERE augl_json IS NOT NULL AND length(augl_json) > 50 "
                "ORDER BY random() LIMIT ?", (SAMPLE_PER_DB,)
            ).fetchall()
            for fn_str, aj in rows:
                sample_rows_examined += 1
                # The legacy schema may store the full envelope or just the inner data; try both.
                blob = aj if isinstance(aj, str) else aj.decode("utf-8", errors="replace")
                urls_found = CF_RE.findall(blob)
                for cf_fn, basename in urls_found:
                    overall_seen_urls += 1
                    key = f"{cf_fn}/{basename}"
                    if key in on_disk_set:
                        overall_matches_disk += 1
            conn.close()
        except Exception as e:
            print(f"  {db_path}: error {e}")
    print()
    print(f"  Sampled rows examined across all DBs: {sample_rows_examined}")
    print(f"  CloudFront URLs seen in samples: {overall_seen_urls:,}")
    print(f"  URLs whose <cf_fastnum>/<basename> exists on disk: {overall_matches_disk:,}")
    if overall_seen_urls > 0:
        print(f"  Match rate: {overall_matches_disk / overall_seen_urls * 100:.1f}%")
    print()

    # 5. Pilot v3 cross-property URL posture in legacy archive
    print("=" * 60)
    print("5. CROSS-PROPERTY URL POSTURE IN LEGACY ARCHIVE")
    print("=" * 60)
    print("  For 5 sampled legacy-DB rows, count: own-property vs cross-property URLs;")
    print("  check whether legacy archive flattened or preserved CloudFront origin.")
    # Sample 5 rows from one DB
    conn = sqlite3.connect(LEGACY_DBS[0])
    rows = conn.execute(
        "SELECT fastnum, augl_json FROM fasteignir "
        "WHERE augl_json IS NOT NULL AND length(augl_json) > 200 "
        "ORDER BY random() LIMIT 5"
    ).fetchall()
    for fn_str, aj in rows:
        own_dir = f"D:\\Gagnapakkar\\{fn_str}\\"  # legacy default
        # find own/cross URL counts
        urls = CF_RE.findall(aj if isinstance(aj, str) else aj.decode("utf-8", errors="replace"))
        own = sum(1 for cf_fn, _ in urls if cf_fn == fn_str)
        cross = sum(1 for cf_fn, _ in urls if cf_fn != fn_str)
        # find on-disk count under any folder named fn_str
        n_disk = sum(1 for p in paths if parent_dir_name(p) == fn_str)
        # check disk for matches by URL
        own_on_disk = sum(1 for cf_fn, bn in urls if cf_fn == fn_str and f"{cf_fn}/{bn}" in on_disk_set)
        cross_on_disk = sum(1 for cf_fn, bn in urls if cf_fn != fn_str and f"{cf_fn}/{bn}" in on_disk_set)
        print(f"  fastnum={fn_str}: urls_total={len(urls)} own={own} cross={cross}  "
              f"on_disk_in_own_dir={n_disk}  url_disk_match[own={own_on_disk} cross={cross_on_disk}]")
    conn.close()
    print()

    # 6. Coverage vs Supabase 124,835
    print("=" * 60)
    print("6. COVERAGE VS SUPABASE properties (124,835 fastnums)")
    print("=" * 60)
    print(f"  Distinct fastnums with disk folder: {len(distinct_fastnums):,}")
    print(f"  As % of 124,835 Supabase rows: {len(distinct_fastnums) / 124_835 * 100:.1f}%")
    # Need actual fastnum overlap — load supabase fastnums (pilot DB doesn't have all)
    print(f"  (full fastnum overlap requires Supabase intersection; deferred to MCP query.)")


if __name__ == "__main__":
    main()
