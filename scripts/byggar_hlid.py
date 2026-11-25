"""cc381b: byggár við hleðslu nýrra eigna (DECISIONS 2026-11-25, cc381 ákvarðanir 1, 2, 4 og 7).

- byggar_ur_hms(gildi): sama regla og migration 20261125200000_cc381b_byggar: byggingarár aðaleiningar ef það er
  fjögurra stafa ár innan [1700, líðandi ár + 2], annars None. 0 er sentinel (nýskráning án árs), ekki ár -> None
  (grunnregla 10). Aldrei 0.
- byggar_hlid(röð): hlið (4) sem FELLIR hleðsluna (SystemExit) ef eitthvert gildi sem á að skrifa er utan
  NULL / [1700, ár + 2]. Sama hlið og í precompute/byggar_hlid.py (spárkeðja og comps).
"""
import datetime as _dt
import re

import numpy as np
import pandas as pd

BYGGAR_MIN = 1700


def byggar_max(ar=None):
    return (ar or _dt.datetime.now(_dt.timezone.utc).year) + 2


def byggar_ur_hms(gildi, ar=None):
    """Byggingarár úr HMS-matseiningu -> int eða None (aldrei 0)."""
    if gildi is None:
        return None
    if isinstance(gildi, float) and np.isnan(gildi):
        return None
    t = str(gildi).strip()
    if re.fullmatch(r"\d{4}(\.0+)?", t):
        a = int(float(t))
        if BYGGAR_MIN <= a <= byggar_max(ar):
            return a
    return None


def byggar_brot(s, ar=None) -> pd.Series:
    raw = pd.Series(s)
    v = pd.to_numeric(raw, errors="coerce")
    ekki_tala = raw.notna() & v.isna() & ~raw.astype(str).str.strip().isin(["", "nan", "None", "NaT", "<NA>"])
    return (v.notna() & ((v < BYGGAR_MIN) | (v > byggar_max(ar)))) | ekki_tala


def byggar_hlid(s, lysing: str, fastnum=None, ar=None) -> int:
    b = byggar_brot(s, ar)
    if b.any():
        raw = pd.Series(s).reset_index(drop=True)
        idx = np.flatnonzero(b.to_numpy())[:10]
        fn = (pd.Series(fastnum).reset_index(drop=True).iloc[idx].tolist() if fastnum is not None else idx.tolist())
        raise SystemExit(f"[STOPP] cc381 hlið (4) byggár: {int(b.sum())} gildi utan NULL / [{BYGGAR_MIN}, "
                         f"{byggar_max(ar)}] í {lysing}; dæmi (fastnum, byggar): {list(zip(fn, raw.iloc[idx].tolist()))}")
    return int(pd.to_numeric(pd.Series(s), errors="coerce").isna().sum())
