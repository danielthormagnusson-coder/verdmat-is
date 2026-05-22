"""Phase 'evalue-audit' — temporal bucket analysis on stage_a_augl_staging.db.

Read-only. Bucket captured_at by 6h windows and per-day; look for windows
where the empty-result rate (n_ads=0 + latest_augl_iso IS NULL) deviates
sharply from baseline — that would indicate a silent outage like HMS had.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta

DB = r"D:\verdmat-is\app\audit\stage_a_augl_staging.db"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = conn.cursor()

    print("=" * 78)
    print("BASELINE — population-wide stats")
    print("=" * 78)
    cur.execute(
        "SELECT count(*), "
        "  sum(CASE WHEN augl_status = 200 THEN 1 ELSE 0 END), "
        "  sum(CASE WHEN augl_status = -1 THEN 1 ELSE 0 END), "
        "  sum(CASE WHEN augl_status NOT IN (200, -1) THEN 1 ELSE 0 END), "
        "  sum(CASE WHEN n_ads IS NULL OR n_ads = 0 THEN 1 ELSE 0 END), "
        "  sum(CASE WHEN latest_augl_iso IS NULL THEN 1 ELSE 0 END), "
        "  sum(CASE WHEN n_image_urls IS NULL OR n_image_urls = 0 THEN 1 ELSE 0 END), "
        "  sum(CASE WHEN augl_json IS NULL THEN 1 ELSE 0 END) "
        "FROM stage_a_augl"
    )
    (total, n200, nm1, nother, n_ads_zero, n_iso_null, n_imgs_zero, n_json_null) = cur.fetchone()
    print(f"  total                       {total:,}")
    print(f"  augl_status=200             {n200:,}  ({100*n200/total:.2f}%)")
    print(f"  augl_status=-1 (placeholder){nm1:,}")
    print(f"  augl_status other           {nother:,}")
    print(f"  n_ads=0 or NULL             {n_ads_zero:,}  ({100*n_ads_zero/total:.2f}%)  baseline empty-rate")
    print(f"  latest_augl_iso IS NULL     {n_iso_null:,}  ({100*n_iso_null/total:.2f}%)")
    print(f"  n_image_urls=0 or NULL      {n_imgs_zero:,}  ({100*n_imgs_zero/total:.2f}%)")
    print(f"  augl_json IS NULL           {n_json_null:,}")

    print()
    print("=" * 78)
    print("PER-DAY breakdown")
    print("=" * 78)
    cur.execute(
        "SELECT substr(captured_at, 1, 10) AS d, "
        "  count(*) AS n, "
        "  sum(CASE WHEN n_ads IS NULL OR n_ads = 0 THEN 1 ELSE 0 END) AS n_empty, "
        "  sum(CASE WHEN latest_augl_iso IS NULL THEN 1 ELSE 0 END) AS n_iso_null, "
        "  sum(CASE WHEN augl_status != 200 THEN 1 ELSE 0 END) AS n_nonok "
        "FROM stage_a_augl "
        "GROUP BY d ORDER BY d"
    )
    print(f"  {'date':12s} {'n':>8s} {'n_empty':>8s} {'empty%':>7s} {'iso_null':>9s} {'null%':>6s} {'n_nonok':>7s}")
    for d, n, n_empty, n_iso, n_nonok in cur.fetchall():
        print(f"  {d:12s} {n:8,d} {n_empty:8,d} {100*n_empty/max(n,1):6.2f}% {n_iso:9,d} {100*n_iso/max(n,1):5.1f}% {n_nonok:7,d}")

    print()
    print("=" * 78)
    print("PER 6-HOUR window — looking for outage clusters")
    print("=" * 78)
    cur.execute(
        "SELECT substr(captured_at, 1, 13) AS h, captured_at "
        "FROM stage_a_augl WHERE captured_at IS NOT NULL "
        "ORDER BY captured_at LIMIT 1"
    )
    first = cur.fetchone()
    cur.execute(
        "SELECT captured_at FROM stage_a_augl ORDER BY captured_at DESC LIMIT 1"
    )
    last = cur.fetchone()
    if not first or not last:
        print("  no data")
        return 0
    first_dt = datetime.fromisoformat(first[1].replace("Z", "+00:00"))
    last_dt = datetime.fromisoformat(last[0].replace("Z", "+00:00"))
    print(f"  span: {first_dt}  ->  {last_dt}  ({last_dt - first_dt})")
    print()
    print(f"  {'window_start':22s} {'n':>8s} {'empty%':>7s} {'iso_null%':>10s} {'avg_n_ads':>10s} {'avg_imgs':>9s}")
    print("  " + "-" * 74)
    # Walk in 6h buckets
    cur_dt = first_dt.replace(minute=0, second=0, microsecond=0)
    # snap to nearest 6h boundary at or before first_dt
    cur_dt = cur_dt - timedelta(hours=cur_dt.hour % 6)
    end_dt = last_dt + timedelta(hours=6)
    flagged = []
    while cur_dt < end_dt:
        nxt = cur_dt + timedelta(hours=6)
        cur.execute(
            "SELECT count(*), "
            "  sum(CASE WHEN n_ads IS NULL OR n_ads = 0 THEN 1 ELSE 0 END), "
            "  sum(CASE WHEN latest_augl_iso IS NULL THEN 1 ELSE 0 END), "
            "  avg(coalesce(n_ads, 0)), "
            "  avg(coalesce(n_image_urls, 0)) "
            "FROM stage_a_augl "
            "WHERE captured_at >= ? AND captured_at < ?",
            (cur_dt.isoformat(), nxt.isoformat()),
        )
        n, n_empty, n_iso, avg_ads, avg_imgs = cur.fetchone()
        if n and n >= 50:  # only print windows with meaningful samples
            empty_pct = 100 * (n_empty or 0) / n
            iso_pct = 100 * (n_iso or 0) / n
            marker = ""
            if empty_pct > 75:
                marker = "  <-- HIGH empty (>75%)"
                flagged.append((cur_dt, n, empty_pct, iso_pct, avg_ads, avg_imgs))
            elif iso_pct > 80:
                marker = "  <-- HIGH iso_null (>80%)"
                flagged.append((cur_dt, n, empty_pct, iso_pct, avg_ads, avg_imgs))
            print(f"  {cur_dt.isoformat():22s} {n:8,d} {empty_pct:6.2f}% {iso_pct:9.2f}% {avg_ads or 0:10.2f} {avg_imgs or 0:9.2f}{marker}")
        cur_dt = nxt

    print()
    print("=" * 78)
    print("FLAGGED 6h-windows")
    print("=" * 78)
    if not flagged:
        print("  none — no window exceeded the 75% empty / 80% iso_null threshold")
    else:
        for f in flagged:
            print(f"  {f}")

    print()
    print("=" * 78)
    print("Sampled augl_json shapes — confirm 'success-but-empty' vs 'success-with-data'")
    print("=" * 78)
    cur.execute(
        "SELECT fastnum, n_ads, n_image_urls, latest_augl_iso, length(augl_json) "
        "FROM stage_a_augl "
        "WHERE n_ads = 0 AND latest_augl_iso IS NULL "
        "LIMIT 5"
    )
    print("  EMPTY rows (n_ads=0, no listings):")
    for r in cur.fetchall():
        print(f"    {r}")
    cur.execute(
        "SELECT fastnum, n_ads, n_image_urls, latest_augl_iso, length(augl_json) "
        "FROM stage_a_augl "
        "WHERE n_ads > 0 "
        "ORDER BY n_ads DESC LIMIT 5"
    )
    print("  RICH rows (highest n_ads):")
    for r in cur.fetchall():
        print(f"    {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
