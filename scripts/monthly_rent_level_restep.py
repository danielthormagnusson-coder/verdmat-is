r"""monthly_rent_level_restep.py — mánaðarleg stigfærsla leigumatsins (cc57 liður 2).

Þegar nýr mánuður birtist í leiguvísitölu HMS er stig predictions_rent (allar
sex pred_*-tölurnar, kr á predicted_at-mánuðinum) fært fram um EINA tölu:
f = leiguvísitala[nýr]/leiguvísitala[akkeri], og predicted_at færist á nýja
mánuðinn — allt í EINNI atómískri færslu. Þetta er framkvæmd cc56-dómsins
(LEIGU_YIELD_KONNUN_20260731T0838Z.md §3.3: „stig endurstigfært mánaðarlega á
leiguverðsjá/leiguvísitölu, ein tala/mán") og LEYSIR 1.sept-vörðuna: akkerið
eldist ekki lengur.

HÖNNUNARVAL (bókað fyrir arkitekt): applýjaði stuðullinn er VÍSITÖLU-skrefið
(landsvísitala, slétt, samsetningarfrí) — leiguverðsjáin er DRIFT-MÆLIRINN:
vegið sellustig spá÷MEDAL_LEIGUVERD yfir frosið leigu-birgða-proxý (cc56
s15-aðferðin, 1,037 við maí-2026) mælist og bókast í hverri keyrslu, með
hávaða-braut (WARN yfir ±6 %, ekki abort). Endurtekin WARN = endur-akkerun er
arkitektsákvörðun, ekki sjálfvirkni. Sama hefð og monthly_cpi_reanchor:
gate DB-megin, verðir, logg, pipeline_runs-bókun, exit-kóðar 0/1/3.

Snertir AÐEINS predictions_rent (sex pred_*-dálka + predicted_at). Hreyfir
HVORKI model_version/calibration_version/segment NÉ nokkra aðra töflu. Innbyrðis
hlutföll (bil ÷ punktur) breytast ekki — þetta er hrein endurtjáning á nýjum
mánuði, hliðstæða kaupverd_real-endurakkerunar.

MÓDELVÖRÐUR: rútínan er skrifuð fyrir rent_v1_nan með EINSLEITU predicted_at.
Ef model_version eða predicted_at er ekki einsleitt (endurþjálfun/flip hefur
gerst) → ABORT exit 3, engin skrif — nýtt líkan þarf nýja ákvörðun.

CLI:
  python scripts/monthly_rent_level_restep.py --dryrun               # gate + mæling, engin skrif
  python scripts/monthly_rent_level_restep.py --dryrun --test-month 2026-04  # þvinga mánuð (próf)
  python scripts/monthly_rent_level_restep.py                        # LIVE (ein atómísk txn)
Exit: 0 = success/no-op · 1 = villa · 3 = vörður felldi (til arkitekts)
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import psycopg2

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "pipelines" / "opin_gogn"))
from migration_helpers import (  # noqa: E402  shared Group C audit logging
    start_run, start_step, finish_step, finish_run, open_connection,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
LOGFILE = Path(r"D:\monthly_rent_level_restep.log")
LEIGUVISITALA = Path(r"D:\verdmat-is\data\raw\opin_gogn\hms\visitolur\leiguvisitala.csv")
LEIGUVERDSJA = Path(r"D:\verdmat-is\data\raw\opin_gogn\hms\leiguverdsja\leiguverdsja.csv")
PROXY_CSV = Path(r"D:\verdmat-is\data\ops\rent_stock_proxy_fastnums.csv")

MODEL_VERSION = "rent_v1_nan"
F_MIN, F_MAX = 0.94, 1.06          # stuðuls-vörður (margra mánaða skref rúmast)
DRIFT_WARN = 0.06                  # |sellustig − 1| yfir þessu → hávær WARN (ekki abort)
FETCH_TARGETS = ("leiguvisitala", "leiguverdsja")

# sveitarfélag → leiguverðsjár-flokkur (cc56 s15, orðrétt)
NAGRENNI = "Sveitarfélög í nágrenni höfuðborgarsvæðis"
VORPUN = {"Reykjavíkurborg": "Reykjavíkurborg", "Kópavogsbær": "Kópavogur",
          "Garðabær": "Garðabær og Hafnarfjörður", "Hafnarfjarðarkaupstaður": "Garðabær og Hafnarfjörður",
          "Mosfellsbær": "Mosfellsbær, Seltjarnarnes eða Kjósarhreppur",
          "Seltjarnarnesbær": "Mosfellsbær, Seltjarnarnes eða Kjósarhreppur",
          "Kjósarhreppur": "Mosfellsbær, Seltjarnarnes eða Kjósarhreppur",
          "Akureyrarbær": "Akureyri",
          "Reykjanesbær": NAGRENNI, "Akraneskaupstaður": NAGRENNI,
          "Sveitarfélagið Árborg": NAGRENNI, "Hveragerðisbær": NAGRENNI,
          "Sveitarfélagið Ölfus": NAGRENNI, "Sveitarfélagið Vogar": NAGRENNI,
          "Suðurnesjabær": NAGRENNI, "Grindavíkurbær": NAGRENNI}


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def fetch_hms_files() -> bool:
    """Endurnýta harvest-resolverinn (pipelines/opin_gogn/harvest.py) fyrir
    leiguvísitölu + leiguverðsjá EINGÖNGU. False = sótt mistókst (WARN-braut:
    gengið á diskinn; cc19-hash-vöktunin er varnarrásin ef hlekkir hverfa)."""
    try:
        import harvest  # noqa: PLC0415
        man = harvest.load_manifest()
        ok = True
        for name, landing, hint, subdir, fname, source, cadence in harvest.HMS_DOWNLOADS:
            if name not in FETCH_TARGETS:
                continue
            cands = harvest.resolve_links(landing, ["objectstorage", "public_data",
                                                    "prismic.io/hms", ".csv",
                                                    "blob.core.windows.net"])
            url = harvest.pick(cands, hint)
            if not url:
                log(f"[0] WARN resolver fann engan hlekk fyrir {name} (cc19-mynstrið)")
                ok = False
                continue
            e = harvest.harvest_file(man, name=name, landing_url=landing, file_url=url,
                                     subdir=subdir, fname=fname, source=source,
                                     cadence=cadence, license_=harvest.HMS_LICENSE)
            if not e.get("local_path"):
                ok = False
        harvest.save_manifest(man)
        return ok
    except Exception as e:
        log(f"[0] WARN sótt féll: {type(e).__name__}: {e} — geng á disk-skrárnar")
        return False


def read_visitala() -> pd.Series:
    vt = pd.read_csv(LEIGUVISITALA, encoding="latin-1")
    vt.columns = [c.strip().replace('"', '') for c in vt.columns]
    vt["man"] = vt.AR.astype(int).astype(str) + "-" + vt.MANUDUR.astype(str).str.strip().str.zfill(2)
    return vt.set_index("man").VISITALA.astype(float)


def drift_metric(conn, factor: float):
    """Vegið sellustig (spá×factor ÷ MEDAL_LEIGUVERD) á nýjustu leiguverðsjá yfir
    frosna proxýið — cc56 s15-aðferðin. Skilar (dict|None, skýring)."""
    if not PROXY_CSV.exists():
        return None, f"proxy vantar ({PROXY_CSV}) — mælir sleppt"
    if not LEIGUVERDSJA.exists():
        return None, "leiguverdsja.csv vantar — mælir sleppt"
    proxy = pd.read_csv(PROXY_CSV).fastnum
    lv = pd.read_csv(LEIGUVERDSJA, encoding="latin-1")
    lv.columns = [c.strip().replace('"', '') for c in lv.columns]
    lv = lv[lv.MARKADSLEIGA == "Markaðsleiga"].copy()
    lv_man = lv.DAGSETNING.max()
    lv = lv[lv.DAGSETNING == lv_man]
    props = pd.read_sql("""
        select pr.fastnum, pr.pred_median, p.sveitarfelag, p.fjherb
        from public.predictions_rent pr join public.properties p on p.fastnum = pr.fastnum
        where pr.model_version = %s""", conn, params=(MODEL_VERSION,))
    sp = props[props.fastnum.isin(set(proxy))].copy()
    sp["svfl"] = sp.sveitarfelag.str.strip().map(lambda s: VORPUN.get(s, "Sveitarfélög á landsbyggðinni"))
    sp["herb"] = sp.fjherb.apply(lambda r: "6+" if pd.notna(r) and r >= 6
                                 else (str(int(r)) if pd.notna(r) and r >= 1 else None))
    sellur = []
    for (sv, hb), d in sp.groupby(["svfl", "herb"]):
        ref = lv[(lv.SVEITARFELAGSFLOKKUN == sv) & (lv.FJOLDI_HERBERGJA.astype(str) == hb)]
        if len(d) >= 30 and len(ref) == 1:
            sellur.append({"sella": f"{sv}|{hb}", "n_stock": len(d),
                           "w": float(ref.FJOLDI_SAMNINGA.iloc[0]),
                           "hlutf": float(d.pred_median.mean() * factor / float(ref.MEDAL_LEIGUVERD.iloc[0]))})
    if not sellur:
        return None, "engar gjaldgengar sellur (n>=30 + ein verðsjár-röð)"
    w = sum(s["w"] for s in sellur)
    stig = sum(s["hlutf"] * s["w"] for s in sellur) / w
    return {"verdsja_man": lv_man, "n_sellur": len(sellur),
            "n_samninga": int(w), "stig_vegid": round(stig, 4)}, "ok"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun", action="store_true", help="gate + mæling, engin skrif")
    ap.add_argument("--test-month", default=None,
                    help="þvinga þennan mánuð (YYYY-MM) framhjá gate-inu; prófanir eingöngu")
    ap.add_argument("--skip-fetch", action="store_true", help="sleppa HMS-sókn, ganga á disk")
    args = ap.parse_args()

    log(f"=== monthly_rent_level_restep ({'DRYRUN' if args.dryrun else 'LIVE'}"
        f"{', TEST-MONTH ' + args.test_month if args.test_month else ''}) ===")

    conn_log = open_connection()
    run_id = start_run(conn_log, "monthly_rent_level_restep")
    log(f"  pipeline_runs.id = {run_id}")
    conn_ro = None
    try:
        # ---- Skref 0: sækja nýjustu leiguvísitölu + leiguverðsjá ----
        sid = start_step(conn_log, run_id, "fetch_hms", 1)
        if args.test_month or args.skip_fetch:
            log("[0] sókn sleppt (--test-month/--skip-fetch) — disk-skrár notaðar")
            finish_step(conn_log, sid, 0, notes="skipped")
        else:
            ok = fetch_hms_files()
            log(f"[0] HMS-sókn: {'ok' if ok else 'FÉLL (WARN) — disk-skrár notaðar; '
                'cc19-hash-vöktun er varnarrásin'}")
            finish_step(conn_log, sid, 0, notes=f"fetch {'ok' if ok else 'failed, disk fallback'}")

        # ---- Skref 2: gate — nýr vísitölumánuður vs predicted_at-akkerið ----
        sid = start_step(conn_log, run_id, "gate", 2)
        vidx = read_visitala()
        url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
        conn_ro = psycopg2.connect(url)
        with conn_ro.cursor() as cur:
            cur.execute("""select count(*), count(distinct predicted_at), min(predicted_at),
                                  count(distinct model_version), min(model_version)
                           from public.predictions_rent""")
            n_live, n_dates, anchor_date, n_mv, mv = cur.fetchone()
        anchor_ym = anchor_date.strftime("%Y-%m")
        new_ym = args.test_month or str(vidx.index.max())
        log(f"[2] raðir={n_live:,}  akkeri(predicted_at)={anchor_ym}  nýjast(vísitala)={new_ym}  "
            f"líkan={mv}")

        # MÓDELVÖRÐUR — einsleitni er forsenda einnar-tölu stigfærslu
        if n_dates != 1 or n_mv != 1 or mv != MODEL_VERSION:
            log(f"[2] ABORT módelvörður: predicted_at-einsleitni={n_dates}, líkan={mv} "
                f"(x{n_mv}) — endurþjálfun/flip hefur gerst; rútínan þarf nýja ákvörðun.")
            finish_step(conn_log, sid, 3, notes=f"model guard: dates={n_dates} mv={mv}x{n_mv}")
            finish_run(conn_log, run_id, "failed", {"step": "gate", "reason": "model_guard"})
            return 3
        if anchor_ym not in vidx.index:
            log(f"[2] ABORT: akkerismánuður {anchor_ym} ekki í leiguvísitölu — get ekki hlutfallað.")
            finish_step(conn_log, sid, 3, notes=f"anchor {anchor_ym} missing from index")
            finish_run(conn_log, run_id, "failed", {"step": "gate", "reason": "anchor_missing"})
            return 3
        if new_ym not in vidx.index:
            log(f"[2] ABORT: {new_ym} ekki í leiguvísitölu.")
            finish_step(conn_log, sid, 3, notes=f"{new_ym} missing from index")
            finish_run(conn_log, run_id, "failed", {"step": "gate", "reason": "new_month_missing"})
            return 3
        finish_step(conn_log, sid, 0, notes=f"anchor={anchor_ym} new={new_ym} n={n_live}")

        if not args.test_month and new_ym <= anchor_ym:
            log(f"[2] enginn nýr mánuður ({new_ym} <= {anchor_ym}) — no-op.")
            finish_run(conn_log, run_id, "success",
                       {"noop": True, "anchor": anchor_ym, "dryrun": args.dryrun})
            return 0

        # ---- Skref 3: stuðullinn + vörður ----
        sid = start_step(conn_log, run_id, "factor", 3)
        f = float(vidx[new_ym]) / float(vidx[anchor_ym])
        log(f"[3] f = vísitala[{new_ym}]/vísitala[{anchor_ym}] = {vidx[new_ym]:.1f}/{vidx[anchor_ym]:.1f} "
            f"= {f:.6f}  ({100 * (f - 1):+.2f} %)")
        if not (F_MIN <= f <= F_MAX):
            log(f"[3] ABORT stuðuls-vörður: f={f:.4f} utan [{F_MIN}, {F_MAX}] — til arkitekts.")
            finish_step(conn_log, sid, 3, notes=f"factor {f:.4f} out of rails")
            finish_run(conn_log, run_id, "failed", {"step": "factor", "f": f})
            return 3
        finish_step(conn_log, sid, 0, notes=f"f={f:.6f}")

        # ---- Skref 4: drift-mælirinn (leiguverðsjá, vaktarrásin — WARN-braut) ----
        sid = start_step(conn_log, run_id, "drift_metric", 4)
        met, skyr = drift_metric(conn_ro, f)
        if met is None:
            log(f"[4] WARN drift-mælir: {skyr}")
            finish_step(conn_log, sid, 0, notes=f"skipped: {skyr}")
        else:
            dev = met["stig_vegid"] - 1
            log(f"[4] sellustig EFTIR stigfærslu vs leiguverðsjá {met['verdsja_man']}: "
                f"{met['stig_vegid']:.4f} ({100 * dev:+.1f} %; {met['n_sellur']} sellur, "
                f"{met['n_samninga']:,} samningar að baki) [cc56-viðmið maí-26: 1,037]")
            if abs(dev) > DRIFT_WARN:
                log("[4] " + "!" * 70)
                log(f"[4] !! WARN DRIFT: |{met['stig_vegid']:.4f} − 1| > {DRIFT_WARN} — stigið "
                    f"rekur frá verðsjánni. Endur-akkerun er ARKITEKTSÁKVÖRÐUN, ekki sjálfvirk.")
                log("[4] " + "!" * 70)
            finish_step(conn_log, sid, 0, notes=f"stig={met['stig_vegid']} {met['verdsja_man']}")

        new_date = f"{new_ym}-01"

        # ---- Skref 5a: DRYRUN — UPDATE mælt í txn sem rúllar til baka ----
        if args.dryrun:
            sid = start_step(conn_log, run_id, "atomic_update", 5)
            conn_w = psycopg2.connect(url); conn_w.autocommit = False
            try:
                with conn_w.cursor() as cur:
                    cur.execute("SET TRANSACTION READ WRITE")
                    cur.execute("SET LOCAL statement_timeout='10min'")
                    cur.execute("""select fastnum, pred_median, pred_lo80, pred_hi80
                                   from public.predictions_rent order by fastnum limit 3""")
                    fyrir = cur.fetchall()
                    t0 = time.time()
                    cur.execute("""
                        UPDATE public.predictions_rent
                           SET pred_mean   = round(pred_mean   * %(f)s::numeric)::bigint,
                               pred_median = round(pred_median * %(f)s::numeric)::bigint,
                               pred_lo80   = round(pred_lo80   * %(f)s::numeric)::bigint,
                               pred_hi80   = round(pred_hi80   * %(f)s::numeric)::bigint,
                               pred_lo95   = round(pred_lo95   * %(f)s::numeric)::bigint,
                               pred_hi95   = round(pred_hi95   * %(f)s::numeric)::bigint,
                               predicted_at = %(d)s
                         WHERE model_version = %(mv)s""",
                        {"f": f, "d": new_date, "mv": MODEL_VERSION})
                    updated = cur.rowcount
                    elapsed = time.time() - t0
                    cur.execute("""select fastnum, pred_median, pred_lo80, pred_hi80
                                   from public.predictions_rent order by fastnum limit 3""")
                    eftir = cur.fetchall()
                conn_w.rollback()
                for a, b in zip(fyrir, eftir):
                    log(f"      fn={a[0]}: median {a[1]:,} -> {b[1]:,}  "
                        f"80-bil [{a[2]:,},{a[3]:,}] -> [{b[2]:,},{b[3]:,}]")
                log(f"[5a] DRYRUN: UPDATE myndi snerta {updated:,} raðir á {elapsed:.1f}s "
                    f"(rúllað til baka, ekkert committað)")
                if updated != n_live:
                    log(f"[5a] WARN: rowcount {updated:,} != raðir {n_live:,}")
                finish_step(conn_log, sid, 0, rowcount_after=updated,
                            notes=f"dryrun {elapsed:.1f}s (rolled back)")
                finish_run(conn_log, run_id, "success",
                           {"dryrun": True, "noop": False, "anchor": anchor_ym,
                            "new_month": new_ym, "f": round(f, 6),
                            "rows_would_update": updated,
                            "drift_metric": met, "measured_seconds": round(elapsed, 1)})
                return 0
            except Exception as e:
                conn_w.rollback()
                log(f"[5a] DRYRUN ERROR (rolled back): {type(e).__name__}: {e}")
                finish_step(conn_log, sid, 1, notes=f"dryrun error: {type(e).__name__}")
                finish_run(conn_log, run_id, "failed",
                           {"step": "atomic_update", "dryrun": True, "error": str(e)[:500]})
                return 1
            finally:
                conn_w.close()

        # ---- Skref 5b: LIVE — pre-flight backup í eigin committaðri txn ----
        sid = start_step(conn_log, run_id, "preflight_backup", 5)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        backup_table = f"predictions_rent_level_backup_{ts}"
        conn_b = psycopg2.connect(url); conn_b.autocommit = False
        try:
            with conn_b.cursor() as cur:
                cur.execute("SET TRANSACTION READ WRITE")
                cur.execute(f"""CREATE TABLE public.{backup_table} AS
                                SELECT fastnum, pred_mean, pred_median, pred_lo80, pred_hi80,
                                       pred_lo95, pred_hi95, predicted_at
                                FROM public.predictions_rent""")
                cur.execute(f"ALTER TABLE public.{backup_table} ENABLE ROW LEVEL SECURITY")
                cur.execute(f"REVOKE ALL ON public.{backup_table} FROM anon")
                cur.execute(f"REVOKE ALL ON public.{backup_table} FROM authenticated")
                cur.execute(f"SELECT count(*) FROM public.{backup_table}")
                n_backup = cur.fetchone()[0]
            conn_b.commit()
            log(f"[5b] pre-flight backup committað: public.{backup_table} ({n_backup:,} raðir)")
        except Exception as e:
            conn_b.rollback()
            log(f"[5b] ERROR backup féll: {type(e).__name__}: {e}")
            finish_step(conn_log, sid, 1, notes=f"backup failed: {type(e).__name__}")
            finish_run(conn_log, run_id, "failed", {"step": "preflight_backup",
                                                    "error": str(e)[:500]})
            return 1
        finally:
            conn_b.close()
        finish_step(conn_log, sid, 0, rowcount_after=n_backup, notes=f"created {backup_table}")

        # ---- Skref 6: LIVE — ein atómísk txn m/rowcount-hliði ----
        sid = start_step(conn_log, run_id, "atomic_update", 6)
        conn_w = psycopg2.connect(url); conn_w.autocommit = False
        try:
            with conn_w.cursor() as cur:
                cur.execute("SET TRANSACTION READ WRITE")
                cur.execute("SET LOCAL statement_timeout='10min'")
                t0 = time.time()
                cur.execute("""
                    UPDATE public.predictions_rent
                       SET pred_mean   = round(pred_mean   * %(f)s::numeric)::bigint,
                           pred_median = round(pred_median * %(f)s::numeric)::bigint,
                           pred_lo80   = round(pred_lo80   * %(f)s::numeric)::bigint,
                           pred_hi80   = round(pred_hi80   * %(f)s::numeric)::bigint,
                           pred_lo95   = round(pred_lo95   * %(f)s::numeric)::bigint,
                           pred_hi95   = round(pred_hi95   * %(f)s::numeric)::bigint,
                           predicted_at = %(d)s
                     WHERE model_version = %(mv)s""",
                    {"f": f, "d": new_date, "mv": MODEL_VERSION})
                updated = cur.rowcount
                if updated != n_live:
                    raise RuntimeError(f"rowcount-hlið: uppfærði {updated:,}, vænti {n_live:,}")
            conn_w.commit()
            elapsed = time.time() - t0
            log(f"[6] LIVE committað: {updated:,} raðir × f={f:.6f}, predicted_at → {new_date}, "
                f"{elapsed:.1f}s")
        except Exception as e:
            conn_w.rollback()
            log(f"[6] LIVE ERROR — rúllað til baka (stig óbreytt): {type(e).__name__}: {e}")
            finish_step(conn_log, sid, 1, notes=f"rolled back: {type(e).__name__}")
            finish_run(conn_log, run_id, "failed", {"step": "atomic_update",
                                                    "error": str(e)[:500]})
            return 1
        finally:
            conn_w.close()
        finish_step(conn_log, sid, 0, rowcount_after=updated,
                    notes=f"f={f:.6f} {anchor_ym}->{new_ym} {elapsed:.1f}s")

        log(f"[7] lokið. stig {anchor_ym} → {new_ym} (f={f:.6f}), raðir={updated:,}, "
            f"backup={backup_table}")
        finish_run(conn_log, run_id, "success",
                   {"noop": False, "anchor_old": anchor_ym, "anchor_new": new_ym,
                    "f": round(f, 6), "rows_updated": updated,
                    "backup_table": backup_table, "drift_metric": met})
        return 0
    except Exception as e:
        log(f"*** CRASH: {type(e).__name__}: {e}")
        finish_run(conn_log, run_id, "crashed", {"error": str(e)[:500]})
        raise
    finally:
        if conn_ro is not None:
            try:
                conn_ro.close()
            except Exception:
                pass
        conn_log.close()


if __name__ == "__main__":
    sys.exit(main())
