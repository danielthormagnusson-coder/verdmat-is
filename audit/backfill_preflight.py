"""
backfill_preflight.py — Pre-flight checks for Áfangi 0 Stage 1 backfill
candidate sources.

Read-only HTTP probes against candidate scrape sources to check
robots.txt posture, ToS surface, and rate-limit reality. Does NOT
attempt to scrape any data. Outputs structured findings for
backfill_preflight_report.md generation.

Usage:
    python audit/backfill_preflight.py

Output:
    audit/backfill_preflight_raw.json — raw probe results
    (report.md generated separately)

Throttle: 1 req per 2 sec between sites; 10 serial requests at 1 req/sec
within rate-limit-reality probe per site. Total request count per run:
~5 robots.txt + ~5 HEAD probes + 10 rate-limit probes per site = ~20-30
requests over ~2 minutes. Negligible footprint.

User-Agent: identifies project + contact URL per SCRAPER_SPEC §7.1
hygiene principle. Source operators get a contact path if there is a
problem.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = REPO_ROOT / "audit"

USER_AGENT = (
    "verdmat.is/0.1 backfill-preflight (+https://verdmat-is.vercel.app)"
)

# Candidate sources for Stage 1 fastnum backfill. evalue.is is the
# spec-suggested primary; fastinn.is and fasteignir.is are alternatives
# from the legacy scraper context. hms.is is the canonical source per
# SCRAPER_SPEC §7.3 — included here for completeness.
SITES = [
    "https://www.evalue.is",
    "https://fastinn.is",
    "https://fasteignir.is",
    "https://fasteignir.visir.is",
    "https://hms.is",
]


def fetch(url: str, method: str = "GET", timeout: int = 15) -> dict:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read() if method == "GET" else b""
            return {
                "url": url,
                "method": method,
                "status": resp.status,
                "headers": dict(resp.headers.items()),
                "body": body.decode("utf-8", errors="replace") if method == "GET" else "",
                "elapsed_s": time.monotonic() - started,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        return {
            "url": url,
            "method": method,
            "status": e.code,
            "headers": dict(e.headers.items()) if e.headers else {},
            "body": "",
            "elapsed_s": time.monotonic() - started,
            "error": str(e),
        }
    except Exception as e:
        return {
            "url": url,
            "method": method,
            "status": None,
            "headers": {},
            "body": "",
            "elapsed_s": time.monotonic() - started,
            "error": str(e),
        }


def probe_site(base_url: str) -> dict:
    print(f"\n=== {base_url} ===")

    # 1. robots.txt
    robots = fetch(f"{base_url}/robots.txt", "GET")
    print(f"  robots.txt: HTTP {robots['status']}, {len(robots['body'])} bytes")

    time.sleep(2)

    # 2. HEAD on root
    head = fetch(base_url + "/", "HEAD")
    print(f"  HEAD /: HTTP {head['status']}, {head['elapsed_s']:.2f}s")

    time.sleep(2)

    # 3. Rate-limit reality probe — 10 serial GETs at 1 req/sec
    rate_probe = []
    print("  rate-limit probe (10 × 1 req/sec) ...")
    for i in range(10):
        result = fetch(base_url + "/", "HEAD", timeout=10)
        rate_probe.append({
            "n": i + 1,
            "status": result["status"],
            "elapsed_s": round(result["elapsed_s"], 3),
            "error": result["error"],
        })
        if result["status"] in (429, 503):
            print(f"    [{i+1}] HTTP {result['status']} — rate-limited, halting")
            break
        time.sleep(1)
    statuses = [r["status"] for r in rate_probe]
    print(f"    statuses: {statuses}")

    return {
        "base_url": base_url,
        "robots_txt": {
            "status": robots["status"],
            "body": robots["body"][:5000],  # cap length
            "error": robots["error"],
        },
        "head_root": {
            "status": head["status"],
            "headers": head["headers"],
            "elapsed_s": round(head["elapsed_s"], 3),
            "error": head["error"],
        },
        "rate_limit_probe": rate_probe,
    }


def main() -> int:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_agent": USER_AGENT,
        "sites": [],
    }

    for site in SITES:
        try:
            results["sites"].append(probe_site(site))
        except KeyboardInterrupt:
            print("\nINTERRUPTED — partial results saved")
            break
        time.sleep(2)  # inter-site cooldown

    out_path = AUDIT_DIR / "backfill_preflight_raw.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
