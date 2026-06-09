"""canonicalize_mbl — §2.1.1 mbl content-hash canonicalization (pure function).

LOCKED rule (2026-06-09, Step 3a Phase 1c probe; see DECISIONS + SCRAPER_SPEC_v2 §2.1.1):
mbl's Hasura GraphQL returns DETERMINISTIC JSON bodies — no per-request server stamps
(t=0 vs t=+60s, same id, both raw_hash and sorted-keys hash identical for sale + rent).
So canonicalization is TRIVIAL: sorted-keys re-serialization, ZERO path-nulling. This is
the cleanest §2.1.1 rule of all 3 sources (unlike myigloo's verification.as_of nulling,
unlike visir's Skoðendur counter + ad-block stripping).

The verbatim response stays in raw_blobs.blob_gz; canonicalization influences ONLY the
content_hash (per the §2.1 idempotency contract) — sorted-keys + whitespace-stripped so two
semantically-equal payloads (different key order / spacing) collapse to one hash.

Defensive fallback (per §2.1.1 idempotency contract): on non-JSON content_type, JSON parse
failure, or empty body → sha256 of the raw bytes (no canon), with a stderr parser-concern
warning. The caller decides whether to act on the concern (e.g. flag the raw_fetches row).

stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import sys

MBL_CANONICALIZATION_VERSION = "mbl_canon_v1"


def canonicalize_mbl(body: bytes, content_type: str):
    """Return (canonical_body_bytes, sha256_hex_digest) for an mbl GraphQL response.

    JSON path: json.loads -> json.dumps(sort_keys=True, separators=(',',':')) -> sha256.
    Fallback (non-JSON / empty / malformed): sha256 of the raw bytes.
    """
    if not body:                                            # empty -> fallback
        return body, hashlib.sha256(body).hexdigest()
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype != "application/json":                          # non-JSON -> no canon
        return body, hashlib.sha256(body).hexdigest()
    try:
        parsed = json.loads(body)
        canon = json.dumps(parsed, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")
        return canon, hashlib.sha256(canon).hexdigest()
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        sys.stderr.write("canonicalize_mbl: JSON parse failed (%s); raw-sha256 fallback\n"
                         % type(e).__name__)
        return body, hashlib.sha256(body).hexdigest()
