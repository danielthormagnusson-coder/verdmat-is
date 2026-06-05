"""canonicalize_visir — §2.1.1 visir content-hash canonicalization (pure functions).

LOCKED rule (2026-06-04, Phase 1b+1c probe; see DECISIONS.md + SCRAPER_SPEC_v2 §2.1.1):

  1. Strip /ads/redirect/\\d+ patterns (replace digits with a constant token).
  2. Drop the ad-block element whose class matches any of:
       Reklama | ad-banner | details-ad-block | partner-link
     (banner `img src` and other ad attributes rotate per request, not just `href`,
      so the whole block is removed — found via its /ads/redirect/ anchor).
  3. Apply ONLY to text/html payloads (JSON / other bypass unchanged).
  4. Store the verbatim blob elsewhere; HASH is computed on the canonicalized HTML.

The point: two fetches of the same listing differing only in rotating ad blocks must
hash identically, while any real listing-content change flips the hash.

deps: stdlib + beautifulsoup4 (+ lxml parser, falls back to html.parser).
"""
from __future__ import annotations

import hashlib
import re
import sys

from bs4 import BeautifulSoup

# Ad-block class fragments (normalized: hyphens/underscores stripped, lowercased).
# Matching is substring-on-normalized so `Reklama__img`, `ad-banner-mobile`,
# `details-ad-block`, `b-partnerlink`/`partner-link` all hit.
_TARGET_FRAGMENTS = ("reklama", "adbanner", "detailsadblock", "partnerlink")

_AD_HREF_PREFIX = "/ads/redirect/"
_AD_REDIRECT_RE = re.compile(r"/ads/redirect/\d+")
_AD_REDIRECT_TOKEN = "/ads/redirect/__ID__"
_ANCESTOR_DEPTH = 3                      # how far up to look for the ad-block class


def _norm_class(value) -> str:
    """Join a BS4 class attr (list or str) and strip to [a-z0-9] for robust matching."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = " ".join(value)
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _matches_adclass(el) -> bool:
    norm = _norm_class(el.get("class")) if el is not None and hasattr(el, "get") else ""
    if not norm:
        return False
    return any(frag in norm for frag in _TARGET_FRAGMENTS)


def _drop_ad_blocks(soup) -> None:
    """Pass 1: decompose the nearest ad-classed ancestor of each /ads/redirect/ anchor."""
    anchors = [a for a in soup.find_all("a", href=True)
               if a["href"].startswith(_AD_HREF_PREFIX)]
    for a in anchors:
        if a.parent is None:             # already removed via an earlier decompose
            continue
        target = None
        node = a.parent
        for _ in range(_ANCESTOR_DEPTH):
            if node is None or node.name is None:
                break
            if _matches_adclass(node):
                target = node            # keep walking; prefer the highest matching ancestor
            node = node.parent
        if target is not None and target.parent is not None:
            target.decompose()


def canonicalize_visir_html(body: bytes, content_type: str = "text/html") -> bytes:
    """Apply the §2.1.1 visir canonicalization; return canonicalized bytes.

    Defensive:
      * empty body -> returned unchanged.
      * non-text/html content_type -> returned unchanged (no parse attempted).
      * parse failure -> regex-only strip (no element drop) + a stderr warning.

    Idempotent: canonicalize(canonicalize(x)) == canonicalize(x).
    """
    if not body:
        return body
    if "html" not in (content_type or "").lower():
        return body

    text = body.decode("utf-8", errors="replace")
    try:
        try:
            soup = BeautifulSoup(text, "lxml")
        except Exception:
            soup = BeautifulSoup(text, "html.parser")
        _drop_ad_blocks(soup)                                   # pass 1: drop ad blocks
        out = str(soup)
        out = _AD_REDIRECT_RE.sub(_AD_REDIRECT_TOKEN, out)      # pass 2: normalize leftovers
        return out.encode("utf-8")
    except Exception as e:                                      # defensive fallback
        sys.stderr.write("canonicalize_visir: parse failed (%s); regex-only fallback\n"
                         % type(e).__name__)
        return _AD_REDIRECT_RE.sub(_AD_REDIRECT_TOKEN, text).encode("utf-8")


def content_hash_visir(body: bytes, content_type: str = "text/html") -> str:
    """sha256 hex digest (64 chars) of the canonicalized body (§2.1.1)."""
    return hashlib.sha256(canonicalize_visir_html(body, content_type)).hexdigest()
