"""anchor_config.py — single source of truth for the pinned CPI anchor month.

Both rebuild_sales_history.py and the daily loader (daily_sales_refresh.py)
import read_anchor() so the anchor lives in exactly one place: the
public.pipeline_config key/value table. No hard-coded fallback — if the row
is missing the caller must fail loudly rather than silently re-anchor.

The anchor (e.g. '2026-07') is the reference VNV month for kaupverd_real:
    cpi_factor(ym) = vnv[anchor] / vnv[ym]
The daily fresh-data path keeps this PINNED; only the monthly path moves it
(and re-anchors all kaupverd_real when it does).
"""
from __future__ import annotations

ANCHOR_KEY = "sales_history_anchor_ym"
MODEL_ANCHOR_KEY = "model_pred_anchor_ym"


def read_model_anchor(conn) -> str | None:
    """Return model_pred_anchor_ym, or None if the key is absent.

    Deliberately NOT fatal, unlike read_anchor: the sales-history path is correct with or
    without it. It exists so callers can DETECT the sales anchor overtaking the model
    anchor — the state in which kaupverd_real and predictions.real_pred_* stop living on
    the same scale, and every real-vs-real comparison acquires a silent offset of
    cpi[sales_anchor]/cpi[model_anchor]. Nominal/nominal comparisons are immune.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM public.pipeline_config WHERE key = %s",
                    (MODEL_ANCHOR_KEY,))
        row = cur.fetchone()
    return str(row[0]) if row and row[0] is not None else None


def read_anchor(conn) -> str:
    """Return the pinned anchor month ('YYYY-MM') from public.pipeline_config.

    `conn` is a live psycopg2 connection (read-only is fine). Raises
    RuntimeError if the key is absent — never falls back to a hard-coded value.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT value FROM public.pipeline_config WHERE key = %s",
            (ANCHOR_KEY,),
        )
        row = cur.fetchone()
    if row is None or row[0] is None:
        raise RuntimeError(
            f"pipeline_config['{ANCHOR_KEY}'] is missing — refusing to guess "
            f"the CPI anchor. Seed it before running the sales-history path."
        )
    return str(row[0])
