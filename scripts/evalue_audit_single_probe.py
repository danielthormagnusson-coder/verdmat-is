"""Phase 'evalue-audit' — SINGLE manual probe (read-only).

One POST to evalue.is/fastnum/{fn}?/get_fasteign_augl with a known-good
positive control. Confirms endpoint is alive, returns 200, decodes JSON.
Does NOT batch. Does NOT write to the production staging DB.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

PROBE_FASTNUM = 2526172  # positive control from backfill_evalue_range.POSITIVE_CONTROLS
URL = f"https://www.evalue.is/fastnum/{PROBE_FASTNUM}?/get_fasteign_augl"
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "User-Agent": "verdmat.is/0.1 evalue-audit-probe (+https://verdmat-is.vercel.app)",
    "Origin": "https://www.evalue.is",
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    data = f"fastnum={PROBE_FASTNUM}".encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers=HEADERS, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read()
            elapsed = time.monotonic() - started
            ct = resp.headers.get("Content-Type", "")
            cf_mit = resp.headers.get("cf-mitigated")
            print(f"http_status        = {resp.status}")
            print(f"elapsed_seconds    = {elapsed:.2f}")
            print(f"content_type       = {ct}")
            print(f"cf-mitigated       = {cf_mit!r}")
            print(f"body_bytes         = {len(body)}")
            body_text = body.decode("utf-8", errors="replace")
            if "html" in ct.lower() or body_text.lstrip().lower().startswith(("<!doctype", "<html")):
                print("CONCERN: HTML response — Cloudflare challenge or block")
                print(f"  body[:300]: {body_text[:300]!r}")
                return 2
            try:
                payload = json.loads(body_text)
            except json.JSONDecodeError as e:
                print(f"json_decode_error = {e}")
                print(f"  body[:300]: {body_text[:300]!r}")
                return 3
            inner_status = payload.get("status")
            data_field = payload.get("data") or ""
            print(f"inner_status       = {inner_status}")
            print(f"data_field_length  = {len(data_field)}")
            try:
                inner_parsed = json.loads(data_field) if isinstance(data_field, str) else data_field
            except Exception:
                inner_parsed = None
            if isinstance(inner_parsed, list) and inner_parsed and isinstance(inner_parsed[0], list):
                print(f"n_ads              = {len(inner_parsed[0])}")
            else:
                print(f"inner_parsed_type  = {type(inner_parsed).__name__}")
            return 0
    except urllib.error.HTTPError as e:
        print(f"http_error         = {e.code} {e.reason}")
        return 4
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"net_error          = {e}")
        return 5
    except Exception as e:
        print(f"unexpected         = {type(e).__name__}: {e}")
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
