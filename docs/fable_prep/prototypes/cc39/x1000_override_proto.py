"""x1000_override_proto.py — cc39 FASI 2 frumgerð (EKKI tengd í leiðslurnar).

Ein gildisvarin ÷1000-skilgreining fyrir ×1000-raðir úr HMS-kaupskránni.
Eftir GO flyst apply_x1000_override + fastarnir ORÐRÉTT inn í
scripts/rebuild_sales_history.py (derive-kjarnann) og kallast sem ALLRA FYRSTA
skref derive_sales_rows — þar með lesa suspect-reglurnar OG nominal/real-afleiðslan
báðar leiðrétt gildi, og báðir lesendur kjarnans (daily_sales_refresh.py,
monthly_cpi_reanchor.py) erfa skilgreininguna án afrits.

Gildisvörnin (nefnarar bókaðir í CC39_DESIGN.md, mælt í cc39-probe 2026-07-23):
  virkjar AÐEINS ef  hrátt verð/m² = KAUPVERD*1000/EINFLM  >  20.000.000 kr/m²
                     (lögmætt hámark í 228.696 FK-röðum: 8.021.633 kr/m²;
                      ×1000-raðirnar byrja á 59.543.500 kr/m² — 2,5×/3× borð)
  OG                 ÷1000-gildið < 2.000.000 kr/m²
                     (lögmæt p99,9 = 1.485.557; leiðréttu raðirnar lenda á
                      59,5þ–499þ — röð sem stenst EKKI þetta er EKKI leiðrétt
                      og strandar áfram á vikulega verðinum = mannlegt mat)
  Enginn ID-listi — þegar HMS lagar uppsprettuna fellur röðin sjálfkrafa utan
  varnarinnar (hrátt verð/m² verður lögmætt) og override hættir að virka.
  Röð án nothæfs EINFLM (<=10 eða vantar) er ALDREI leiðrétt hér; vikulegi
  sanity-vörðurinn (exit 3) stendur óbreyttur sem bakstopp fyrir allt slíkt.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ×1000-OVERRIDE (cc39): HMS-kaupskráin ber stöku raðir með KAUPVERD í kr í stað þús.kr.
X1000_AUDIT_LOG = Path(r"D:\x1000_override_audit.jsonl")
X1000_RAW_KRM2_MIN = 20_000_000   # hrátt verð/m² yfir þessu er ómögulegt (lögmætt hámark 8,02M — cc39)
X1000_FIXED_KRM2_MAX = 2_000_000  # ÷1000-gildið verður að vera raunhæft (lögmæt p99,9=1,49M) — annars EKKI leiðrétt


def apply_x1000_override(
    kp: pd.DataFrame, audit_log: Path | None = None
) -> tuple[pd.DataFrame, list[dict]]:
    """Gildisvarin ÷1000-leiðrétting á KAUPVERD (þús.kr) á fullu kaupskrá-frame.

    Skilar (kp, audit-færslur). Óbreytt frame (sama object) ef ekkert virkjar —
    núll-kostnaðar no-op leið. Audit-línur appendast í X1000_AUDIT_LOG (JSONL);
    audit-skrif mega aldrei fella leiðsluna, færslurnar skila sér líka í
    return-gildinu svo kallarar geti loggað hátt.
    """
    audit_log = X1000_AUDIT_LOG if audit_log is None else audit_log
    kaupverd = pd.to_numeric(kp["KAUPVERD"], errors="coerce")
    einflm = pd.to_numeric(kp["EINFLM"], errors="coerce")
    raw_krm2 = (kaupverd * 1000) / einflm.where(einflm > 10)
    mask = ((raw_krm2 > X1000_RAW_KRM2_MIN)
            & ((raw_krm2 / 1000) < X1000_FIXED_KRM2_MAX)).fillna(False)
    if not mask.any():
        return kp, []

    kp = kp.copy()
    corrected = (kaupverd[mask] / 1000).round()
    fnum = pd.to_numeric(kp["FAERSLUNUMER"], errors="coerce")
    fast = pd.to_numeric(kp["FASTNUM"], errors="coerce")
    ts = datetime.now(timezone.utc).isoformat()
    caller = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else None
    entries = []
    for idx in kp.index[mask]:
        entries.append({
            "ts_utc": ts,
            "caller": caller,
            "faerslunumer": int(fnum.at[idx]) if pd.notna(fnum.at[idx]) else None,
            "fastnum": int(fast.at[idx]) if pd.notna(fast.at[idx]) else None,
            "thinglystdags": str(kp.at[idx, "THINGLYSTDAGS"]),
            "kaupverd_original_thus": float(kaupverd.at[idx]),
            "kaupverd_corrected_thus": float(corrected.at[idx]),
            "einflm": float(einflm.at[idx]) if pd.notna(einflm.at[idx]) else None,
            "raw_kr_m2": float(raw_krm2.at[idx]),
        })
    # heildarsúlan gerð talnaleg svo ÷1000-úthlutunin sé týpu-hrein (float64 er
    # nákvæm fyrir öll heiltölugildi kaupskrárinnar, < 2^53)
    kp["KAUPVERD"] = kaupverd.astype("float64")
    kp.loc[mask, "KAUPVERD"] = corrected
    try:
        with open(audit_log, "a", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    except Exception:
        pass  # audit-skrif mega aldrei fella leiðsluna
    return kp, entries
