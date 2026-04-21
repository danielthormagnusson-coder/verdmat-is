"""
Parser for SvelteKit's devalue serialization format.

Structure: flat JSON array where element 0 is the root. Integers in structures
are references to other indices. Primitives at those indices are values.

Special sentinel values (negative integers):
  -1: undefined (treat as None)
  -2: null
  -3: NaN
  -4: +Infinity
  -5: -Infinity
  -6: -0
"""
import json
from typing import Any

SENTINELS = {-1: None, -2: None, -3: float('nan'), -4: float('inf'),
             -5: float('-inf'), -6: -0.0}


def parse(raw: str | list) -> Any:
    arr = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(arr, list) or not arr:
        return arr

    resolved: dict[int, Any] = {}
    in_progress: set[int] = set()

    def resolve(idx: int) -> Any:
        if isinstance(idx, int) and idx < 0:
            return SENTINELS.get(idx, None)
        if not isinstance(idx, int) or idx >= len(arr):
            return idx
        if idx in resolved:
            return resolved[idx]
        if idx in in_progress:
            # cycle — return a placeholder, will be patched or left as-is
            return None
        in_progress.add(idx)
        v = arr[idx]
        if isinstance(v, list):
            out = [resolve(x) if isinstance(x, int) else x for x in v]
        elif isinstance(v, dict):
            out = {k: resolve(x) if isinstance(x, int) else x for k, x in v.items()}
        else:
            out = v  # primitive (str, number, bool, None)
        resolved[idx] = out
        in_progress.discard(idx)
        return out

    return resolve(0)


def parse_outer(raw: str) -> Any:
    """Parse the outer wrapper { type, status, data } and return the parsed data."""
    outer = json.loads(raw)
    if isinstance(outer, dict) and 'data' in outer:
        return parse(outer['data'])
    return parse(outer)
