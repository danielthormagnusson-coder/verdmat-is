"""suspect_rules.py — is_suspect_comparable (comp-visibility filter) — single source of truth.

A sale is "suspect" if it is technically valid (ONOTHAEFUR_SAMNINGUR=0) but UNTRUSTWORTHY as a
VISIBLE comparable. Distinct from the ONOTHAEFUR exclusion (upstream) and from the comp-VAL kv band.

Locked definition — REFINED-B (Danni/Fable, 2026-07-02; see docs/DECISIONS.md + COMP_PROBES / SUSPECT_COMP_DEF):
  R1 sentinel_price       : KAUPVERD <= 1
  R2 kv_extreme           : kv = KAUPVERD/FASTEIGNAMAT NOT in [0.50, 2.00]  (or undefined)
  R3 size_mismatch        : sale EINFLM EXCEEDS current HMS size by >10%  (REFINED-B: only this
                            direction; sale<HMS is legitimate post-sale expansion, NOT flagged)
                            OR the deed (SKJALANUMER) spans >1 fastnum (multi-unit bundled price)
  R4 new_build_first_sale : FULLBUID==0  OR  (sale_year - BYGGAR) <= 2

REFINED-B rationale: R3 compares per-sale EINFLM to the CURRENT HMS registered size. A symmetric
>10% test over-flagged: 63% of hits were "sale < HMS" on old sales (median sale-year 2014) = properties
LEGITIMATELY expanded AFTER the sale (temporal drift), not bad transactions. REFINED-B flags only
sale>HMS (the genuinely suspicious direction) + multi-unit deeds.

READ-ONLY on inputs; returns two Series. The multi-unit sub-rule needs SKJALANUMER over the FULL
kaupskra — pass the full kaupskra frame so deed spans are counted correctly.
"""
from __future__ import annotations
import pandas as pd

RULESET_VERSION = "refinedB-v1-2026-07-02"

_REASON = [("R1", "sentinel_price"), ("R2", "kv_extreme"),
           ("R3", "size_mismatch"), ("R4", "new_build_first_sale")]


def compute_suspect(kp: pd.DataFrame, hms_einflm_by_fastnum: dict) -> pd.DataFrame:
    """kp: full kaupskra-shaped frame with columns KAUPVERD, FASTEIGNAMAT, EINFLM, BYGGAR,
    FULLBUID, SKJALANUMER, FASTNUM, THINGLYSTDAGS. hms_einflm_by_fastnum: {fastnum: current HMS einflm}.
    Returns a frame indexed like kp with: is_suspect_comparable(bool), suspect_reason(str),
    suspect_ruleset_version(str), and R1..R4 (bool) for audit."""
    d = pd.DataFrame(index=kp.index)
    kaupverd  = pd.to_numeric(kp["KAUPVERD"], errors="coerce")
    fmat      = pd.to_numeric(kp["FASTEIGNAMAT"], errors="coerce")
    einflm    = pd.to_numeric(kp["EINFLM"], errors="coerce")
    byggar    = pd.to_numeric(kp["BYGGAR"], errors="coerce")
    fullbuid  = pd.to_numeric(kp["FULLBUID"], errors="coerce")
    fastnum   = pd.to_numeric(kp["FASTNUM"], errors="coerce").astype("Int64")
    sale_year = pd.to_datetime(kp["THINGLYSTDAGS"], errors="coerce").dt.year

    kv = kaupverd / fmat.where(fmat > 0)
    hms = fastnum.map(hms_einflm_by_fastnum).astype("float")
    denom = pd.concat([einflm, hms], axis=1).max(axis=1)
    relsign = (einflm - hms) / denom                       # >0 => sale larger than HMS
    deed_nfast = kp["SKJALANUMER"].astype(str).map(
        kp.groupby(kp["SKJALANUMER"].astype(str))["FASTNUM"].nunique())

    d["R1"] = kaupverd <= 1
    d["R2"] = ~kv.between(0.50, 2.00) | kv.isna()
    d["R3"] = (hms.notna() & (relsign > 0.10)) | (deed_nfast > 1)
    d["R4"] = (fullbuid == 0) | (sale_year - byggar <= 2)
    d["is_suspect_comparable"] = d[["R1", "R2", "R3", "R4"]].any(axis=1)
    d["suspect_reason"] = [
        "+".join(name for flag, name in _REASON if row[flag]) or None
        for _, row in d[["R1", "R2", "R3", "R4"]].iterrows()
    ]
    d["suspect_ruleset_version"] = RULESET_VERSION
    return d
