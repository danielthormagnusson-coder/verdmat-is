# -*- coding: utf-8 -*-
r"""
cc180_build_llt_live.py — R1-b LIFANDI BLÖNDUN: last_listing_text = evalue-raðir
(R3-bygging úr frosnum pkl) + lifandi raðir úr scraper.listings (mbl) fyrir sölur
þinglýstar EFTIR 2026-04-16 (frostdag evalue-lindarinnar).

Pörunarregla lifandi lindar (cc178 q21 / cc180 q03, falsprófuð á 49 tvípöruðum
sölum: miðgildi dagamunar 0):
    sama fastnum · tenure='sale' · length(lysing) >= 200 ·
    first_seen_at::date <= thinglystdags · innan 365 daga á undan · nýjasta.
  + evalue vinnur: sala sem á þegar evalue-röð á (fastnum, thinglyst_dagur) fær
    EKKI lifandi röð.
  + dedup á listing_id: ein auglýsing → EIN sala (sú fyrsta eftir auglýsingu).

Uppruni bókaður á HVERJA röð:
    augl_id     = 'mbl:<source_listing_id>'   (aldrei árekstur við evalue-tölur)
    pair_status = 'live_listings'
    scraped_at  = last_seen_at                 (sótt dags)
    augl_dagur  = least(listed_at, first_seen_at)::date

Röðun: per fastnum eftir thinglyst_dagur DESC, jafntefli brotið á R3-sale_rank
(evalue) / 0 (lifandi) → deterministic. Þak 3 per fastnum (óbreytt).

Úttak (ENGIN DB-skrif — hleðsla fer um cc180_llt_flip.py --stage/--flip):
    D:\last_listing_text_blend.pkl
    D:\verdmat-is\precompute\exports\last_listing_text_blend.csv
    + SPÁ-lína fyrir parity-hliðið.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import psycopg2

sys.path.insert(0, r"D:\\")
from build_last_listing_text import strip_html  # noqa: E402  (sama strippari og evalue-raðir)

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
EVALUE_PKL = Path(r"D:\last_listing_text.pkl")           # R3-bygging (66.060)
OUT_PKL = Path(r"D:\last_listing_text_blend.pkl")
OUT_CSV = Path(r"D:\verdmat-is\precompute\exports\last_listing_text_blend.csv")
FROST = "2026-04-16"
MAX_SALES_PER_FASTNUM = 3
COLS = ["fastnum", "sale_rank", "thinglyst_dagur", "augl_id",
        "lysing_plain", "scraped_at", "augl_dagur", "pair_status"]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


LIVE_SQL = f"""
  WITH s AS (
    SELECT faerslunumer, fastnum, thinglystdags
    FROM public.sales_history
    WHERE thinglystdags > date '{FROST}' AND onothaefur=0),
  m AS (
    SELECT s.faerslunumer, s.fastnum, s.thinglystdags, l.*
    FROM s
    JOIN LATERAL (
      SELECT l.listing_id, l.source, l.source_listing_id, l.lysing,
             l.first_seen_at, l.last_seen_at, l.listed_at
      FROM scraper.listings l
      WHERE l.fastnum=s.fastnum AND l.tenure='sale'
        AND length(l.lysing) >= 200
        AND l.first_seen_at::date <= s.thinglystdags
        AND l.first_seen_at::date >= s.thinglystdags - interval '365 days'
      ORDER BY l.first_seen_at DESC LIMIT 1) l ON true),
  d AS (
    SELECT m.*, row_number() OVER (PARTITION BY listing_id ORDER BY thinglystdags, faerslunumer) rn_l
    FROM m)
  SELECT faerslunumer, fastnum, thinglystdags, source, source_listing_id, lysing,
         first_seen_at, last_seen_at, listed_at, rn_l
  FROM d
"""


def main():
    log(f"Loading evalue (R3) frame {EVALUE_PKL} ...")
    ev = pd.read_pickle(EVALUE_PKL)
    ev = ev[COLS].copy()
    ev["fastnum"] = ev["fastnum"].astype("int64")
    ev["augl_id"] = ev["augl_id"].astype("int64").astype(str)
    ev["thinglyst_dagur"] = pd.to_datetime(ev["thinglyst_dagur"])
    ev["augl_dagur"] = pd.to_datetime(ev["augl_dagur"])
    ev["_tie"] = ev["sale_rank"].astype(int)
    log(f"  evalue rows {len(ev):,}  fastnum {ev['fastnum'].nunique():,}  "
        f"max thinglyst {ev['thinglyst_dagur'].max().date()}")

    log("Querying scraper.listings (READ-ONLY) ...")
    dsn = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    c = psycopg2.connect(dsn)
    c.set_session(isolation_level="REPEATABLE READ", readonly=True, autocommit=False)
    try:
        with c.cursor() as cur:
            cur.execute("SET statement_timeout = '10min'")
            cur.execute("SELECT now()")
            snapshot_ts = cur.fetchone()[0]
            cur.execute(LIVE_SQL)
            live = pd.DataFrame(cur.fetchall(), columns=[
                "faerslunumer", "fastnum", "thinglystdags", "source", "source_listing_id",
                "lysing", "first_seen_at", "last_seen_at", "listed_at", "rn_l"])
    finally:
        c.rollback()
        c.close()
    log(f"  snapshot {snapshot_ts}  paraðar fyrir dedup {len(live):,}")
    n_dedup = int((live["rn_l"] > 1).sum())
    live = live[live["rn_l"] == 1].copy()
    log(f"  eftir dedup á listing_id: {len(live):,}  (felldar {n_dedup})")

    # evalue vinnur á (fastnum, thinglyst_dagur)
    live["thinglyst_dagur"] = pd.to_datetime(live["thinglystdags"])
    ev_keys = set(zip(ev["fastnum"], ev["thinglyst_dagur"]))
    mask = [(f, d) in ev_keys for f, d in zip(live["fastnum"].astype("int64"), live["thinglyst_dagur"])]
    n_ev_wins = int(sum(mask))
    live = live[[not x for x in mask]].copy()
    log(f"  evalue vinnur á {n_ev_wins} sölum → lifandi raðir {len(live):,}")

    assert (live["source"] == "mbl").all(), "óvænt lind í scraper.listings-pörun"
    live["fastnum"] = live["fastnum"].astype("int64")
    live["augl_id"] = "mbl:" + live["source_listing_id"].astype(str)
    live["lysing_plain"] = live["lysing"].map(strip_html)
    live["scraped_at"] = pd.to_datetime(live["last_seen_at"], utc=True).dt.tz_convert(None)
    la = pd.to_datetime(live["listed_at"], utc=True)
    fs = pd.to_datetime(live["first_seen_at"], utc=True)
    live["augl_dagur"] = pd.concat([la, fs], axis=1).min(axis=1).dt.tz_convert(None).dt.normalize()
    live["pair_status"] = "live_listings"
    live["_tie"] = 0
    live = live[["fastnum", "thinglyst_dagur", "augl_id", "lysing_plain", "scraped_at",
                 "augl_dagur", "pair_status", "_tie"]]
    n_live_html = int(live["lysing_plain"].fillna("").str.contains(r"<[a-zA-Z/][^>]*>").sum())
    n_live_lt200 = int((live["lysing_plain"].fillna("").str.len() < 200).sum())
    assert live["augl_id"].is_unique, "augl_id ekki einkvæmt í lifandi röðum"
    assert (live["thinglyst_dagur"] > pd.Timestamp(FROST)).all()

    # blanda + endurröðun
    ev_in = ev.drop(columns=["sale_rank"])
    allr = pd.concat([ev_in, live], ignore_index=True)
    allr = allr.sort_values(["fastnum", "thinglyst_dagur", "_tie"],
                            ascending=[True, False, True], kind="mergesort")
    allr["sale_rank"] = allr.groupby("fastnum").cumcount() + 1
    dropped = allr[allr["sale_rank"] > MAX_SALES_PER_FASTNUM]
    out = allr[allr["sale_rank"] <= MAX_SALES_PER_FASTNUM].copy()
    n_disp_ev = int((dropped["pair_status"] != "live_listings").sum())
    n_disp_live = int((dropped["pair_status"] == "live_listings").sum())

    # hve margar evalue-raðir héldu R3-rankinum sínum?
    chk = out[out["pair_status"] != "live_listings"].merge(
        ev[["fastnum", "augl_id", "thinglyst_dagur", "sale_rank"]].rename(columns={"sale_rank": "r3_rank"}),
        on=["fastnum", "augl_id", "thinglyst_dagur"], how="left")
    n_rank_shift = int((chk["sale_rank"] != chk["r3_rank"]).sum())

    out = out[COLS].copy()
    out["sale_rank"] = out["sale_rank"].astype("int64")
    out["thinglyst_dagur"] = out["thinglyst_dagur"].dt.date
    out["augl_dagur"] = pd.to_datetime(out["augl_dagur"], errors="coerce").dt.date
    out.to_pickle(OUT_PKL)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    log(f"wrote {OUT_CSV} ({len(out):,} rows, {OUT_CSV.stat().st_size/1024/1024:.1f} MB)")

    dist = out["pair_status"].value_counts().to_dict()
    log("--- SPÁ (parity-hlið) ---")
    log(f"  ROWCOUNT={len(out)} FASTNUM={out['fastnum'].nunique()}")
    log(f"  STATUS=" + ",".join(f"{k}={v}" for k, v in sorted(dist.items())))
    log(f"  lifandi raðir inn: {len(live):,} (þar af rank1 {int((out[out.pair_status=='live_listings'].sale_rank==1).sum()):,})")
    log(f"  evalue-raðir ýttar út af þaki: {n_disp_ev}  lifandi ýttar út: {n_disp_live}  "
        f"→ EXPECT_DISPLACED (lifandi R3-tafla ekki í blöndu) = {n_disp_ev}")
    log(f"  evalue-raðir sem skipta um sale_rank: {n_rank_shift:,}")
    log(f"  lifandi: HTML-leifar eftir strip {n_live_html}, <200 stafir eftir strip {n_live_lt200}")
    log(f"  per mánuður (lifandi): {out[out.pair_status=='live_listings'].groupby(pd.to_datetime(out.thinglyst_dagur).dt.strftime('%Y-%m')).size().to_dict()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
