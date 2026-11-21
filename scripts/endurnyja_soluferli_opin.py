"""cc364: endurnýjar scraper.soluferli_opin_mv (opin söluferli, lind leitar) með REFRESH ... CONCURRENTLY.

Tveir hamir:
  python scripts/endurnyja_soluferli_opin.py [--thurrt]
      Handkeyrsla. rc 0 = COMMIT (eða --thurrt: ROLLBACK), 2 = hlið féll (ROLLBACK), 1 = villa.

  python -m scripts.endurnyja_soluferli_opin --keyrsla {nott,sopun} --fyrri-rc N [--astaeda TEXTI] [--thurrt]
      SÍÐASTA SKREF næturkeðjunnar (nightly_delta_chain.sh) og sópunarinnar (lifecycle_sweep_mbl.py --scheduled),
      ákvörðun 21.11.2026 (ekki fastur klukkutími). Keyrir AÐEINS ef öll fyrri skref enduðu með rc 0
      (--fyrri-rc 0); annars sleppt. Skráir eina röð í public.pipeline_runs (run_type soluferli_mv_<keyrsla>,
      exit_status success / skipped / failed, summary með ástæðu). Skilar ALLTAF rc 0: endurnýjunin fellir
      aldrei keðjuna, og keyrarinn hunsar rc hennar að auki. --thurrt: engin skrif í pipeline_runs (prentar
      röðina), endurnýjun endar á ROLLBACK.

Lásar: REFRESH CONCURRENTLY tekur EXCLUSIVE-lás á MV eina (lesendur stöðvast ekki); grunntöflur fá aðeins
ACCESS SHARE. Mælt í --prof 21.11.2026: 45-61 s, 8.554 raðir. statement_timeout 240 s, undir 600 s svigrúmi
sópunarinnar við tímaþak (RUN_TIME_MARGIN_S).

Hlið fyrir COMMIT: ef raðafjöldi fellur um meira en 25 % frá fyrri fyllingu (eða MV er tóm) er færslunni
rúllað til baka og gamla fyllingin stendur.

Prófhermun (AÐEINS með --thurrt): umhverfisbreytan SOLUFERLI_MV_HERMA = ok | hlid | villa kemur í stað
endurnýjunar í grunni, svo þurra prófið snertir ekki grunninn (cc364 §F).
"""
import argparse, datetime as dt, json, os, sys, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BOTN = Path(r"D:\verdmat-is")
HAMARK_FALL = 0.25
TIMAMORK_S = 240


def tengja():
    import psycopg2
    c = psycopg2.connect((BOTN / ".dbconfig").read_text(encoding="utf-8-sig").strip(), connect_timeout=15)
    c.autocommit = False
    return c


def endurnyja(thurrt):
    """Skilar dict(rc, ...): rc 0 = í lagi (COMMIT, eða ROLLBACK ef thurrt), 2 = hlið féll, 1 = villa."""
    herma = os.environ.get("SOLUFERLI_MV_HERMA") if thurrt else None
    if herma == "ok":
        return {"rc": 0, "fyrir": 8554, "eftir": 8556, "ovist": 4090, "sek": 0.0, "hermt": True}
    if herma == "hlid":
        return {"rc": 2, "fyrir": 8554, "eftir": 10, "sek": 0.0, "hermt": True, "hlid": "fall > 25 %"}
    if herma == "villa":
        raise RuntimeError("hermd villa (SOLUFERLI_MV_HERMA=villa)")
    c = tengja()
    try:
        c.rollback()
        cur = c.cursor()
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute(f"SET LOCAL statement_timeout = '{TIMAMORK_S}s'")
        cur.execute("SET LOCAL lock_timeout = '10s'")
        cur.execute("select count(*), max(reiknad_at) from scraper.soluferli_opin_mv")
        fyrir, fyrir_at = cur.fetchone()
        t = time.time()
        cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY scraper.soluferli_opin_mv")
        cur.execute("select count(*), count(*) filter (where not upphaf_viss) from scraper.soluferli_opin_mv")
        eftir, ovist = cur.fetchone()
        ut = {"fyrir": fyrir, "eftir": eftir, "ovist": ovist, "sek": round(time.time() - t, 1), "fyrri_fylling": str(fyrir_at)}
        print(f"soluferli_opin_mv: {fyrir} -> {eftir} raðir ({ovist} með óvisst upphaf), {ut['sek']:.0f} s; fyrri fylling {fyrir_at}")
        if eftir == 0 or (fyrir and eftir < fyrir * (1 - HAMARK_FALL)):
            c.rollback()
            print(f"[HLIÐ] raðafjöldi féll úr {fyrir} í {eftir} (> {HAMARK_FALL:.0%}): ROLLBACK, gamla fyllingin stendur")
            return {**ut, "rc": 2, "hlid": f"fall > {HAMARK_FALL:.0%}"}
        if thurrt:
            c.rollback()
            print("--thurrt: ROLLBACK")
        else:
            c.commit()
            print("COMMIT")
        return {**ut, "rc": 0}
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def skra(run_type, stada, samantekt, thurrt):
    """Ein röð í public.pipeline_runs. Fall hér fellir ekkert (prentað, rc 0)."""
    if thurrt:
        print(f"[thurrt] pipeline_runs: run_type={run_type} exit_status={stada} summary={json.dumps(samantekt, ensure_ascii=False, default=str)}")
        return
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from migration_helpers import start_run, finish_run
        c = tengja()
        try:
            c.rollback()
            rid = start_run(c, run_type)
            finish_run(c, rid, stada, samantekt)
            print(f"pipeline_runs.id = {rid} ({stada})")
        finally:
            c.close()
    except Exception as e:
        print(f"[VIÐVÖRUN] pipeline_runs-skráning féll ({type(e).__name__}: {e}); keðjan heldur rc sínum")


def keyrsla_skref(a):
    run_type = f"soluferli_mv_{a.keyrsla}"
    samantekt = {"keyrsla": a.keyrsla, "fyrri_rc": a.fyrri_rc,  # host skráir start_run
                 "kl": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if a.fyrri_rc != 0:
        samantekt["astaeda"] = a.astaeda or f"fyrra skref endaði með rc {a.fyrri_rc}"
        print(f"soluferli_mv: SLEPPT ({samantekt['astaeda']})")
        skra(run_type, "skipped", samantekt, a.thurrt)
        return 0
    try:
        r = endurnyja(a.thurrt)
        samantekt.update({k: v for k, v in r.items() if k != "rc"})
        stada = "success" if r["rc"] == 0 else "failed"
        print(f"soluferli_mv: {stada.upper()} (rc {r['rc']})")
    except Exception as e:
        samantekt["villa"] = f"{type(e).__name__}: {e}"[:500]
        stada = "failed"
        print(f"soluferli_mv: FAILED ({samantekt['villa']}); keðjan heldur rc sínum")
    skra(run_type, stada, samantekt, a.thurrt)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thurrt", action="store_true", help="endurnýjar og rúllar til baka; ekkert skráð í pipeline_runs")
    ap.add_argument("--keyrsla", choices=["nott", "sopun"], help="síðasta skref keðju: skráir í pipeline_runs, skilar alltaf 0")
    ap.add_argument("--fyrri-rc", type=int, default=0, help="með --keyrsla: rc fyrri skrefa (≠ 0 → sleppt)")
    ap.add_argument("--astaeda", default=None, help="með --keyrsla: ástæða þess að fyrra skref féll")
    a = ap.parse_args()
    if a.keyrsla:
        try:
            return keyrsla_skref(a)
        except BaseException as e:  # aldrei fall úr keðjuskrefi
            print(f"[VIÐVÖRUN] soluferli_mv: óvænt {type(e).__name__}: {e}")
            return 0
    try:
        return endurnyja(a.thurrt)["rc"]
    except Exception as e:
        print("[VILLA] ROLLBACK:", type(e).__name__, e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
