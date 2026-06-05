"""canonicalize_visir — §2.1.1 visir content-hash canonicalization (pure functions).

LOCKED rule (2026-06-04, Phase 1b+1c probe + Step 2b P2 amendments):

  1. Drop every element whose OWN class matches any of:
       Reklama | ad-banner | details-ad-block | partner-link
     (case-insensitive, [a-z0-9]-normalized substring). Class-anchored — covers anchor,
     iframe, and script ad creatives alike (visir rotates the inner creative per request).
  2. Strip remaining /ads/redirect/\\d+ patterns (replace digits with a constant token)
     — belt-and-suspenders for stray refs in onClick handlers etc.
  3. Normalize the "Skoðendur" view counter (ticks on every detail fetch):
       a. labeled:    <digit>[ws]*<span>Skoðendur  ->  __VIEWS__...<span>Skoðendur
       b. standalone: <p class="property__head-text">\\s*<digit>\\s*</p>  ->  __VIEWS__
     Both date-safe: the registration-date <p> contains <span>Skráð, not <span>Skoðendur
     and not pure-digit content.
  4. Apply ONLY to text/html payloads (JSON / other bypass unchanged).
  5. Store the verbatim blob elsewhere; HASH is computed on the canonicalized HTML.

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

_AD_REDIRECT_RE = re.compile(r"/ads/redirect/\d+")
_AD_REDIRECT_TOKEN = "/ads/redirect/__ID__"

# §2.1.1 amendment (Step 2b P2 smoke test, 2026-06-04): the "Skoðendur" view counter
# ticks on each detail fetch — a SECOND volatile field, not covered by the ad-redirect
# rule. Both regexes are date-safe by construction: the registration-date <p> contains
# <span>Skráð (never <span>Skoðendur, never pure-digit content), so it is untouched.
_VIEWS_LABELED_RE = re.compile(r"(\d+)(\s|&nbsp;)*(<span>\s*Skoðendur)")
_VIEWS_STANDALONE_RE = re.compile(r'(<p class="property__head-text">\s*)\d+(\s*</p>)')


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
    """Pass 1: decompose every element whose OWN class matches a target ad-block fragment.

    Class-anchored (not /ads/redirect anchor-walk): visir ad containers rotate their inner
    creative per request — sometimes an <a href=/ads/redirect/>, sometimes a pulsmedia
    <iframe>, sometimes a DFP <script> with no anchor at all (Step 2b P2 smoke finding).
    Matching the container class directly removes the whole block regardless of creative
    type. Targets are domain-specific visir ad classes (Reklama|ad-banner|details-ad-block|
    partner-link) — unlikely to collide with listing content.
    """
    for el in list(soup.find_all(class_=True)):
        if el.parent is None:            # stale ref after an ancestor was decomposed
            continue
        if _matches_adclass(el):
            el.decompose()


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
        out = _AD_REDIRECT_RE.sub(_AD_REDIRECT_TOKEN, out)      # pass 2: normalize ad-redirect leftovers
        out = _VIEWS_LABELED_RE.sub(r"__VIEWS__\2\3", out)      # pass 3a: labeled Skoðendur counter
        out = _VIEWS_STANDALONE_RE.sub(r"\1__VIEWS__\2", out)   # pass 3b: standalone head-text counter
        return out.encode("utf-8")
    except Exception as e:                                      # defensive fallback
        sys.stderr.write("canonicalize_visir: parse failed (%s); regex-only fallback\n"
                         % type(e).__name__)
        return _AD_REDIRECT_RE.sub(_AD_REDIRECT_TOKEN, text).encode("utf-8")


def content_hash_visir(body: bytes, content_type: str = "text/html") -> str:
    """sha256 hex digest (64 chars) of the canonicalized body (§2.1.1)."""
    return hashlib.sha256(canonicalize_visir_html(body, content_type)).hexdigest()
