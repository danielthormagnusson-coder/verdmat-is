# -*- coding: utf-8 -*-
r"""
cc180_llt_refresh.py — ENDURKEYRSLA lifandi textalindar `last_listing_text`
(R1-b blöndun) í einni keðju: bygging → staging → parity → atómískt rename-swap →
hreinsun eldri árganga. Þetta er skriftan sem Task Scheduler-verkið á að kalla.

    python scripts/cc180_llt_refresh.py            # full keyrsla (flipp ef parity OK)
    python scripts/cc180_llt_refresh.py --no-flip  # bygging + staging + parity, fellir _new, EKKERT flipp
    python scripts/cc180_llt_refresh.py --keep-old 2

Skref:
  1. cc180_build_llt_live.build() → CSV + meta (evalue-raðir úr D:\last_listing_text.pkl
     (R3, frosið) + lifandi mbl-raðir úr scraper.listings). Engin DB-skrif.
  2. ÓHÁÐ spá fyrir hlið [6]: lyklar lifandi töflunnar lesnir (READ-ONLY) og bornir
     við blönduna í pandas → expect_displaced. Hliðið í cc180_llt_flip mælir sömu
     stærð SQL-megin; tvær leiðir, ein tala.
  3. Ef blandan er EINS og lifandi taflan (rowcount, dreifing, 0 ýttar) → sleppt.
  4. cc180_llt_flip.stage(...) með tag ref_<YYYYMMDD_HHMM> → parity 6/6 krafist.
  5. cc180_llt_flip.flip(...) → last_listing_text_old_ref_<tag> stendur sem rollback.
  6. Hreinsun: eldri last_listing_text_old_ref_* felldar, nýjustu --keep-old (1) standa.
     _old_r3 / _old_r1b (lotu-rollback cc180) eru ALDREI snertar hér.

Log: D:\cc180_llt_refresh.log (append) + stdout. Exit: 0 OK/sleppt · 2 parity fall · 3 villa.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import traceback
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

import cc180_build_llt_live as bl  # noqa: E402
import cc180_llt_flip as fl  # noqa: E402

LOG = Path(r"D:\cc180_llt_refresh.log")
PROTECTED = {"last_listing_text_old_r3", "last_listing_text_old_r1b"}


def log(m):
    line = f"[{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {m}"
    print(line, flush=True)
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def live_keys_and_dist():
    ro = fl.open_ro()
    try:
        with ro.cursor() as cur:
            cur.execute(f"SELECT fastnum, thinglyst_dagur, augl_id FROM public.{fl.LIVE}")
            keys = cur.fetchall()
            cur.execute(f"SELECT pair_status, count(*) FROM public.{fl.LIVE} GROUP BY 1")
            dist = {r[0]: r[1] for r in cur.fetchall()}
    finally:
        ro.rollback()
        ro.close()
    return keys, dist


def prune_old(keep):
    w = fl.open_w()
    dropped = []
    try:
        with w.cursor() as cur:
            cur.execute("SET TRANSACTION READ WRITE")
            cur.execute("""
              SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
              WHERE n.nspname='public' AND c.relkind='r' AND c.relname LIKE 'last_listing_text_old_ref_%'
              ORDER BY c.relname DESC""")
            names = [r[0] for r in cur.fetchall()]
            for nm in names[keep:]:
                if nm in PROTECTED:
                    continue
                cur.execute(f"DROP TABLE public.{nm}")
                dropped.append(nm)
        w.commit()
    except Exception:
        w.rollback()
        raise
    finally:
        w.close()
    return dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-flip", action="store_true")
    ap.add_argument("--keep-old", type=int, default=1)
    args = ap.parse_args()
    tag = "ref_" + dt.datetime.now().strftime("%Y%m%d_%H%M")
    log(f"=== cc180_llt_refresh START tag={tag} no_flip={args.no_flip} ===")
    try:
        out, meta = bl.build()
        log(f"bygging: rows={meta['rowcount']} fastnum={meta['fastnum']} live={meta['n_live']} "
            f"status={meta['status']} snapshot={meta['snapshot_ts']}")

        keys, live_dist = live_keys_and_dist()
        new_keys = set(zip(out["fastnum"].astype("int64"), pd.to_datetime(out["thinglyst_dagur"]).dt.date,
                           out["augl_id"].astype(str)))
        displaced = sum(1 for f, d, a in keys if (int(f), d, str(a)) not in new_keys)
        log(f"lifandi: rows={len(keys)} status={live_dist}; ýttar/breyttar raðir (óháð spá hliðs [6]) = {displaced}")

        if displaced == 0 and len(keys) == meta["rowcount"] and live_dist == meta["status"]:
            log("ENGIN BREYTING gegn lifandi töflu — flippi sleppt. exit 0")
            return 0

        st = Namespace(stage=meta["csv"], tag=tag, expect_rows=meta["rowcount"],
                       expect_status=",".join(f"{k}={v}" for k, v in meta["status"].items()),
                       expect_displaced=displaced)
        rc = fl.stage(st)
        if rc != 0:
            log("PARITY FALL — _new stendur til skoðunar, EKKERT flipp. exit 2")
            return 2
        if args.no_flip:
            w = fl.open_w()
            try:
                with w.cursor() as cur:
                    cur.execute("SET TRANSACTION READ WRITE")
                    cur.execute(f"DROP TABLE IF EXISTS public.{fl.NEW}")
                w.commit()
            finally:
                w.close()
            log("--no-flip: parity OK, _new felld, ekkert flippað. exit 0")
            return 0
        fl.flip(Namespace(flip=True, tag=tag, expect_rows=meta["rowcount"]))
        dropped = prune_old(args.keep_old)
        log(f"FLIPPAÐ tag={tag}; felldar eldri: {dropped or 'engar'}. exit 0")
        return 0
    except SystemExit as e:
        log(f"HÆTT (SystemExit {e.code}) — sjá ofar. exit 2")
        return 2
    except Exception:
        log("VILLA:\n" + traceback.format_exc())
        return 3


if __name__ == "__main__":
    sys.exit(main())
