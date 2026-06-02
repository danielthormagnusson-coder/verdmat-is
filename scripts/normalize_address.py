"""normalize_address — shared Icelandic street-address normalizer.

Single source of truth for address matching across the scraper substream:
  * SCRAPER_SPEC_v2 §2.3 dedup tier-2          (cross-source listing dedup)
  * SCRAPER_SPEC_v2 §2.5 fastnum resolution 2   (listing -> properties.fastnum)

Do NOT roll a second implementation in either path — import this one.

Designed to match `public.properties.heimilisfang` AFTER normalization.
`heimilisfang` is a CLEAN street+number string (empirically confirmed
2026-06-01 introspection: e.g. 'Kaupvangur 23A', 'Langitangi 9-13',
'Hverfisgata 12' — no unit/floor/town/postcode embedded; 232,887 rows /
111,932 distinct).

This utility handles ONLY the bottom-level invariant: clean street+number ->
normalized. Per-source pre-extraction of street+number from messier listing
addresses ('Hverfisgata 12, 101 Reykjavík', 'Hverfisgata 12, íbúð 0301',
myigloo nested address{street, number, city}) lives in the source-specific
parser-mappers, NOT here.

stdlib only.
"""
from __future__ import annotations

import re

# Icelandic diacritics -> ASCII. Explicit map: NFD decomposition mishandles
# þ/ð (they are letters, not accented bases), so we map directly. Both case
# forms map to the lowercase ASCII result; plain-ASCII case is handled by
# .lower() afterwards. str.translate accepts 1-char -> multi-char values.
_ICELANDIC = {
    "þ": "th", "Þ": "th",
    "ð": "d",  "Ð": "d",
    "æ": "ae", "Æ": "ae",
    "ö": "o",  "Ö": "o",
    "á": "a",  "Á": "a",
    "é": "e",  "É": "e",
    "í": "i",  "Í": "i",
    "ó": "o",  "Ó": "o",
    "ú": "u",  "Ú": "u",
    "ý": "y",  "Ý": "y",
}
_TRANS = str.maketrans(_ICELANDIC)
_WS = re.compile(r"\s+")


def normalize_address(addr: str | None) -> str | None:
    """Normalize an Icelandic street address for matching.

    Designed to match public.properties.heimilisfang format AFTER
    normalization. Input is expected to be a 'clean' street+number string
    (e.g. 'Kaupvangur 23A', 'Langitangi 9-13'). Per-source pre-extraction of
    street+number from messier listing addresses is handled upstream by
    parser-mappers, NOT here.

    Rules:
      - Strip Icelandic diacritics: þ->th, ð->d, æ->ae, ö->o,
        á/é/í/ó/ú/ý -> a/e/i/o/u/y (lowercase + uppercase forms both)
      - Lowercase
      - Collapse multiple whitespace -> single space
      - Strip leading/trailing whitespace
      - PRESERVE letter suffixes on house numbers ('23a')
      - PRESERVE house number ranges ('9-13')
      - Return None if input is None or empty/whitespace-only

    Examples:
      'Kaupvangur 23A'     -> 'kaupvangur 23a'
      'Langitangi 9-13'    -> 'langitangi 9-13'
      'Þórsgata 5'         -> 'thorsgata 5'
      '  Hverfisgata  12 ' -> 'hverfisgata 12'
      ''                   -> None
      None                 -> None
    """
    if addr is None:
        return None
    # diacritics -> ASCII (handles both case forms), then lowercase plain ASCII,
    # then collapse all whitespace runs to a single space, then trim.
    out = addr.translate(_TRANS).lower()
    out = _WS.sub(" ", out).strip()
    return out or None
