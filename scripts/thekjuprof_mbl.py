"""thekjuprof_mbl.py — cc210 C1: daglegt þekjupróf mbl ↔ scraper.listings („mallar hún rétt?").

Task Scheduler: verdmat-daily-thekjuprof 07:15 (register_thekjuprof_task.ps1). Ein röð í
scraper.thekjuprof per keyrsla + ein lína í night_logs/night_YYYYMMDD.log.

Þrjár mælingar, hver með teljara OG nefnara (SKIL_CC199 §5 C1):

 (a) GAP — nákvæm talning, ekki úrtak. Gluggi = lifandi innlendar mbl-söluauglýsingar
     (priced + tilboð) STOFNAÐAR síðustu GAP_DAYS daga sem delta-bendillinn er kominn fram
     hjá (br_dags < cursor_ts úr mbl_fetch_state.json — það sem keðjan ÁTTI að hafa séð).
     Ein aggregate-beiðni ber nefnarann og teljarann: teljari = sama sía + `eign_id _nin`
     [öll mbl-auðkenni okkar ≥ lægsta eign_id gluggans]. Þetta er rótin frá cc199 (auglýsing
     stofnuð, aldrei sótt) mæld beint. Fyrri beiðnin (1) ber universe-talningu + lægsta
     eign_id gluggans.
 (b) ÚRTAK — 4 síður × 16 á slembi-offset yfir ALLT lifandi innlent verðlagt mengi (br_dags <
     bendill). Klasa-úrtak (16 samliggjandi auðkenni, sjá feedback_sidu_urtak_er_klasa_urtak):
     vísbending um eldra gat utan gluggans, ekki óbjagað mat á fjölda.
 (c) DRAUGAR — DRAUG_N slembi fastnum úr scraper.v_eign_virk_auglysing (mbl, sala, fastnum ekki
     NULL = ber „Á sölu"-kort). Probað á mbl: lifandi (syna) auglýsing á fastano-bili fastnum
     (f*10..f*10+9) EÐA undir einhverju korta-auðkenni? Ef ekki → draugur. 8 fastnum per
     beiðni; skili beiðni 16 röðum (Hasura-þakið) eru ófundnir í henni ÓVÍSIR og utan nefnara.

Viðvörun (vidvorun-dálkur + „VIÐVÖRUN" í night-log): gap_n > GAP_ALERT eða draugar >
DRAUG_ALERT_PCT % af nefnara. Viðvörun fellir ekki keyrsluna (exit 0).

Kurteisi: 2 + 4 + 4 = 10 beiðnir, 120 s bil (fetch_mbl gólf 60 s), kill-switch lifecycle-
sópunarinnar (Transport: 3×400/403/429/CAPTCHA/GraphQL-villur/3× timeout). Beiðnirnar
teljast ekki í raw_fetches (eins og sópunin) — ~10/dag ofan á delta+sópun, langt undir 1000.

DB: les á pooler read-only; eina skrifin eru INSERT í scraper.thekjuprof (SET TRANSACTION
READ WRITE fyrst). --no-db: mælir og prentar, skrifar ekkert í DB (night-log ekki heldur).

Exit: 0 mæling skráð (líka með viðvörun) · 2 kill-switch · 3 villa.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_mbl import SALE_DOMESTIC  # noqa: E402  sama innlenda sía og delta-forsögnin
from lifecycle_sweep_mbl import Transport, DEFAULT_SPACING  # noqa: E402  sami kill-switch
from fetch_mbl import KillSwitch  # noqa: E402
from scraper_paths import get_scraper_data_dir  # noqa: E402

ADFERD = "thekjuprof_mbl_v1"
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
GAP_DAYS = 14
GAP_ALERT = 50            # raðir
DRAUG_ALERT_PCT = 20.0    # % af nefnara
N_SAMPLE_PAGES = 4
PAGE = 16
DRAUG_N = 32
DRAUG_PER_REQ = 8
PRICED = "syna:{_eq:true}, verd:{_gt:0}, fermetrar:{_gt:0}, " + SALE_DOMESTIC
NEGOT = "syna:{_eq:true}, verd:{_eq:0}, fermetrar:{_gt:0}, " + SALE_DOMESTIC
# sölu-rót okkar megin (sama greinir og lifecycle_sweep_mbl.load_active_ids): leigu-borðið
# ber alltaf tegund_raw leiga_type_% og id úr rentals_property — annað id-rúm, má ekki í _nin.
SALE_ROOT = "(l.tenure = 'sale' OR l.tegund_raw NOT LIKE 'leiga_type_%%')"


def now_utc():
    return datetime.now(timezone.utc)


class Log:
    def __init__(self, path):
        self.path = path

    def __call__(self, msg):
        line = "%s %s" % (now_utc().isoformat(timespec="seconds"), msg)
        print(line, flush=True)
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def load_cursors():
    st = json.loads((get_scraper_data_dir() / "mbl_fetch_state.json").read_text(encoding="utf-8"))
    sale = st["delta_sale"].get("cursor_ts") or st["delta_sale"]["last_br_dags_seen"]
    neg = (st["delta_sale_negotiable"].get("cursor_ts")
           or st["delta_sale_negotiable"]["last_br_dags_seen"])
    if not sale or not neg:
        raise RuntimeError("delta-bendill ósettur í mbl_fetch_state.json")
    return sale, neg


def agg(where):
    return "fs_fasteign_aggregate(where:{%s}) { aggregate { count } }" % where


def measure(pg, tr, log, seed):
    rnd = random.Random(seed)
    cur_sale, cur_neg = load_cursors()
    since = (now_utc() - timedelta(days=GAP_DAYS)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    info = {"gluggi_created_gte": since, "cursor_sale": cur_sale, "cursor_neg": cur_neg,
            "gap_days": GAP_DAYS, "seed": seed}

    # DB-lestur kortanna FREMST: villa hér kostar enga mbl-beiðni
    with pg.cursor() as c:
        c.execute("SELECT v.fastnum, array_agg(l.source_listing_id) FROM scraper.v_eign_virk_auglysing v "
                  "JOIN scraper.listings l ON l.listing_id = v.listing_id "
                  "WHERE v.source='mbl' AND v.fastnum IS NOT NULL AND " + SALE_ROOT.replace('%%', '%') + " "
                  "GROUP BY v.fastnum ORDER BY v.fastnum")
        cards = c.fetchall()

    # ── (1) universe + lægsta eign_id gluggans ──
    seen_priced = 'br_dags:{_lt:"%s"}, %s' % (cur_sale, PRICED)
    q1 = ("query { u: %s w: fs_fasteign_aggregate(where:{created:{_gte:\"%s\"}, syna:{_eq:true}, "
          "fermetrar:{_gt:0}, %s}) { aggregate { count min { eign_id } } } }"
          % (agg(seen_priced), since, SALE_DOMESTIC))
    d = tr.gql(q1)["data"]
    universe = d["u"]["aggregate"]["count"]
    e0 = d["w"]["aggregate"]["min"]["eign_id"]
    info["universe_def"] = "lifandi innlendar verðlagðar söluaugl. m/ br_dags < cursor_sale"
    info["e0"] = e0
    log("(1) universe=%d gluggi: created>=%s min eign_id=%s" % (universe, since, e0))

    # ── (2) gap: nákvæm talning með _nin á okkar auðkenni ──
    with pg.cursor() as c:
        c.execute("SELECT DISTINCT l.source_listing_id::bigint FROM scraper.listings l "
                  "WHERE l.source='mbl' AND " + SALE_ROOT + " AND l.source_listing_id ~ '^[0-9]+$' "
                  "AND l.source_listing_id::bigint >= %s", (e0 or 0,))
        ours = sorted(r[0] for r in c.fetchall())
    info["okkar_ids_i_glugga"] = len(ours)
    nin = ",".join(str(i) for i in ours)
    win_p = 'created:{_gte:"%s"}, eign_id:{_gte:%d}, br_dags:{_lt:"%s"}, %s' % (since, e0 or 0, cur_sale, PRICED)
    win_n = 'created:{_gte:"%s"}, eign_id:{_gte:%d}, br_dags:{_lt:"%s"}, %s' % (since, e0 or 0, cur_neg, NEGOT)
    # eign_id ber þegar _gte í gluggasíunni → _nin fer í _and svo lykillinn tvítekst ekki í hlutnum
    not_ours = "_and:[{eign_id:{_nin:[%s]}}]" % nin
    q2 = ("query { dp: %s dn: %s gp: %s gn: %s "
          "xp: fs_fasteign(where:{%s, %s}, order_by:{eign_id:asc}, limit:16) "
          "{ eign_id created br_dags heimilisfang postfang } }"
          % (agg(win_p), agg(win_n), agg(win_p + ", " + not_ours), agg(win_n + ", " + not_ours),
             win_p, not_ours))
    info["q2_bytes"] = len(q2)
    d = tr.gql(q2)["data"]
    dp, dn = d["dp"]["aggregate"]["count"], d["dn"]["aggregate"]["count"]
    gp, gn = d["gp"]["aggregate"]["count"], d["gn"]["aggregate"]["count"]
    gap_n, gap_nef = gp + gn, dp + dn
    info.update({"gap_priced": [gp, dp], "gap_negot": [gn, dn],
                 "gap_daemi": [{k: r[k] for k in ("eign_id", "created", "br_dags", "heimilisfang", "postfang")}
                               for r in d["xp"]]})
    log("(2) GAP: %d / %d (verðlagt %d/%d, tilboð %d/%d) — _nin %d auðkenni, %d bæti"
        % (gap_n, gap_nef, gp, dp, gn, dn, len(ours), len(q2)))

    # ── (3) úrtak: 4 slembi-síður yfir allt lifandi mengið ──
    sample = []
    for _ in range(N_SAMPLE_PAGES):
        off = rnd.randint(0, max(0, universe - PAGE))
        q = ("query { fs_fasteign(where:{%s}, order_by:{eign_id:asc}, limit:%d, offset:%d) "
             "{ eign_id created br_dags } }" % (seen_priced, PAGE, off))
        rows = tr.gql(q)["data"]["fs_fasteign"]
        sample.extend(rows)
    ids = sorted({str(r["eign_id"]) for r in sample})
    with pg.cursor() as c:
        c.execute("SELECT source_listing_id, status FROM scraper.listings "
                  "WHERE source='mbl' AND source_listing_id = ANY(%s)", (ids,))
        have = {}
        for sid, stt in c.fetchall():
            have.setdefault(sid, set()).add(stt)
    missing = [i for i in ids if i not in have]
    not_active = [i for i in ids if i in have and "active" not in have[i]]
    info.update({"urtak_vantar_ids": missing[:20], "urtak_ekki_active": len(not_active),
                 "urtak_ekki_active_ids": not_active[:20]})
    log("(3) ÚRTAK: vantar %d / %d einkvæm auðkenni (til en ekki active: %d)"
        % (len(missing), len(ids), len(not_active)))

    # ── (4) draugar á „Á sölu"-kortum ──
    info["kort_fastnum_n"] = len(cards)
    picked = rnd.sample(cards, min(DRAUG_N, len(cards)))
    ghosts, unsure, alive = [], [], 0
    for i in range(0, len(picked), DRAUG_PER_REQ):
        chunk = picked[i:i + DRAUG_PER_REQ]
        ors = [("{fastano:{_gte:%d,_lte:%d}}" % (f * 10, f * 10 + 9)) for f, _ in chunk]
        lids = sorted({int(x) for _, ls in chunk for x in ls if x.isdigit()})
        ors.append("{eign_id:{_in:[%s]}}" % ",".join(map(str, lids)))
        q = ("query { fs_fasteign(where:{syna:{_eq:true}, _or:[%s]}, limit:16) { eign_id fastano } }"
             % ",".join(ors))
        rows = tr.gql(q)["data"]["fs_fasteign"]
        live_ids = {int(r["eign_id"]) for r in rows}
        live_fa = [int(r["fastano"]) for r in rows if r.get("fastano") is not None]
        trunc = len(rows) >= 16
        for f, ls in chunk:
            hit = any(f * 10 <= fa <= f * 10 + 9 for fa in live_fa) or any(
                int(x) in live_ids for x in ls if x.isdigit())
            if hit:
                alive += 1
            elif trunc:
                unsure.append(f)
            else:
                ghosts.append({"fastnum": f, "kort_ids": ls})
    draug_nef = alive + len(ghosts)
    info.update({"draugar": ghosts, "draug_ovissir": unsure})
    log("(4) DRAUGAR: %d / %d „Á sölu\"-fastnum án lifandi mbl-auglýsingar (óvíst %d, úr %d kort-fastnum)"
        % (len(ghosts), draug_nef, len(unsure), len(cards)))

    return {"gap_n": gap_n, "gap_nefnari": gap_nef, "urtak_vantar": len(missing),
            "urtak_nefnari": len(ids), "universe_n": universe, "draug_n": len(ghosts),
            "draug_nefnari": draug_nef, "draug_ovisst": len(unsure), "upplysingar": info}


def alerts(m):
    out = []
    if m["gap_n"] > GAP_ALERT:
        out.append("gap %d > %d" % (m["gap_n"], GAP_ALERT))
    if m["draug_nefnari"] and 100.0 * m["draug_n"] / m["draug_nefnari"] > DRAUG_ALERT_PCT:
        out.append("draugar %.1f %% > %.0f %%" % (100.0 * m["draug_n"] / m["draug_nefnari"], DRAUG_ALERT_PCT))
    return "; ".join(out) or None


def write_row(dsn, m, beidnir, vidvorun, dags):
    w = psycopg2.connect(dsn)
    try:
        with w.cursor() as c:
            c.execute("SET TRANSACTION READ WRITE")
            c.execute("INSERT INTO scraper.thekjuprof (dags, adferd, gap_n, gap_nefnari, urtak_vantar, "
                      "urtak_nefnari, universe_n, draug_n, draug_nefnari, draug_ovisst, beidnir, vidvorun, "
                      "upplysingar) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                      (dags, ADFERD, m["gap_n"], m["gap_nefnari"], m["urtak_vantar"], m["urtak_nefnari"],
                       m["universe_n"], m["draug_n"], m["draug_nefnari"], m["draug_ovisst"], beidnir,
                       vidvorun, Json(m["upplysingar"])))
            rid = c.fetchone()[0]
        w.commit()
        return rid
    finally:
        w.close()


def night_line(text):
    p = get_scraper_data_dir() / "night_logs" / ("night_%s.log" % now_utc().strftime("%Y%m%d"))
    with open(p, "a", encoding="utf-8") as f:
        f.write("%s %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-db", action="store_true", help="mæla og prenta; engin DB-skrif, engin night-log-lína")
    ap.add_argument("--spacing", type=float, default=DEFAULT_SPACING)
    ap.add_argument("--seed", type=int, default=None, help="sjálfgefið: dagsetning (YYYYMMDD)")
    args = ap.parse_args()
    dags = now_utc().date()
    seed = args.seed if args.seed is not None else int(dags.strftime("%Y%m%d"))
    logdir = get_scraper_data_dir() / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    log = Log(logdir / ("thekjuprof_%s.log" % dags.strftime("%Y%m%d")))
    log("=== thekjuprof %s seed=%d no_db=%s ===" % (ADFERD, seed, args.no_db))

    dsn = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    pg = psycopg2.connect(dsn)
    pg.set_session(readonly=True, autocommit=True)
    tr = Transport(spacing=args.spacing, log=log)
    try:
        m = measure(pg, tr, log, seed)
    except KillSwitch as e:
        log("KILL-SWITCH: %s (beiðnir=%d)" % (e, tr.request_count))
        if not args.no_db:
            night_line("thekjuprof: KILL-SWITCH %s — engin mæling" % e)
        return 2
    finally:
        pg.close()

    vid = alerts(m)
    pct = 100.0 * m["draug_n"] / m["draug_nefnari"] if m["draug_nefnari"] else 0.0
    summary = ("thekjuprof: gap=%d/%d (stofnaðar %dd, br_dags<bendill) urtak_vantar=%d/%d "
               "draugar=%d/%d (%.1f %%, óvíst %d) universe=%d beidnir=%d%s"
               % (m["gap_n"], m["gap_nefnari"], GAP_DAYS, m["urtak_vantar"], m["urtak_nefnari"],
                  m["draug_n"], m["draug_nefnari"], pct, m["draug_ovisst"], m["universe_n"],
                  tr.request_count, (" VIÐVÖRUN: " + vid) if vid else ""))
    log(summary)
    if args.no_db:
        log("--no-db: ekkert skrifað")
        return 0
    rid = write_row(dsn, m, tr.request_count, vid, dags)
    night_line(summary + " -> scraper.thekjuprof id=%d" % rid)
    log("skrifað scraper.thekjuprof id=%d" % rid)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:
        err = get_scraper_data_dir() / "logs" / "thekjuprof_error.log"
        with open(err, "a", encoding="utf-8") as fh:
            fh.write("=== %s ===\n" % now_utc().isoformat())
            traceback.print_exc(file=fh)
        traceback.print_exc()
        sys.exit(3)
