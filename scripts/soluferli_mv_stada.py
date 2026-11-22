"""cc364: staða síðasta skrefs (endurnýjun scraper.soluferli_opin_mv) fyrir status-probe og vaktarpóst. Aðeins lestur.

Les NÝJUSTU röð nokkru sinni í public.pipeline_runs fyrir run_type soluferli_mv_nott og soluferli_mv_sopun og flokkar
í EINU falli (flokka), ákvarðanir 21.11.2026:
    success                                   -> OK        (grænt)
    skipped                                   -> SLEPPT    (hvorki villa né grænt: fyrra skref keðjunnar féll, hávært þar)
    failed, crashed, halted, óþekkt gildi     -> FALL      (athygli)
    engin röð nokkru sinni                    -> VANTAR    (hlutlaust: fyrir fyrstu keyrslu eftir beitingu cc364)
    nýjasta röð eldri en 48 klst.             -> VANTAR48  (athygli: hefur verið skráð, en hvorug keyrslan náði skrefinu)
    lind ólesanleg úr grunni                  -> MAELING_MISTOKST (athygli, ákvörðun 22.11 liður 7)
ATHYGLI = {FALL, VANTAR48, MAELING_MISTOKST}: status-probe setur þá VAKT-viðvörun og vaktarpósturinn stigið „athygli".
Úttak (stdout, UTF-8):
    SOLUFERLI_MV: nott=<FLOKKUR> sopun=<FLOKKUR>
    L <keyrsla> <FLOKKUR> <DD.MM HH:MM> <skýring á mannamáli>     (ein lína á keyrslu sem einhvern tíma hefur verið skráð)
rc alltaf 0; fall í lestri gefur „SOLUFERLI_MV: nott=MAELING_MISTOKST sopun=MAELING_MISTOKST" (athygli, 22.11).
Próf: --radir-ur-skra <json> [{run_type, exit_status, ended_at, summary}] í stað grunns, --nu <ISO> = viðmiðunartími.
"""
import argparse, datetime as dt, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEYRSLUR = ("nott", "sopun")
HEITI = {"nott": "eftir næturkeðju", "sopun": "eftir sópun"}
GLUGGI = dt.timedelta(hours=48)
ATHYGLI = {"FALL", "VANTAR48", "MAELING_MISTOKST"}  # 22.11 liður 7: staða ólesanleg úr grunni = „athygli"


def flokka(exit_status, ended_at=None, nu=None):
    """Eina flokkunin. exit_status None = aldrei skráð. ended_at eldri en 48 klst. fyrir nu = VANTAR48."""
    if exit_status is None:
        return "VANTAR"
    if ended_at is not None and nu is not None and nu - ended_at > GLUGGI:
        return "VANTAR48"
    if exit_status == "success":
        return "OK"
    if exit_status == "skipped":
        return "SLEPPT"
    return "FALL"


def skyring(flokkur, r):
    s = r.get("summary") or {}
    if isinstance(s, str):
        try:
            s = json.loads(s)
        except ValueError:
            s = {}
    if flokkur == "OK":
        return f"endurnýjuð, {s.get('eftir', '?')} eignir á sölu" + (f" á {s['sek']:.0f} s" if isinstance(s.get("sek"), (int, float)) else "")
    if flokkur == "SLEPPT":
        return f"sleppt: {s.get('astaeda') or 'fyrra skref féll'} (leitin heldur fyrri fyllingu)"
    if flokkur == "VANTAR48":
        return f"engin skráning í 48 klst. (síðast {r.get('exit_status')}); leitin heldur fyrri fyllingu"
    return f"féll ({r.get('exit_status')}): {s.get('villa') or s.get('hlid') or 'sjá pipeline_runs'} (leitin heldur fyrri fyllingu)"


def lesa_grunn():
    import psycopg2
    c = psycopg2.connect(Path(r"D:\verdmat-is\.dbconfig").read_text(encoding="utf-8-sig").strip(), connect_timeout=15)
    try:
        c.set_session(readonly=True, autocommit=False)
        cur = c.cursor()
        cur.execute("set statement_timeout = '30s'")
        cur.execute("""select distinct on (run_type) run_type, exit_status, coalesce(ended_at, started_at), summary
                       from public.pipeline_runs
                       where run_type in ('soluferli_mv_nott', 'soluferli_mv_sopun')
                       order by run_type, started_at desc, id desc""")
        return [{"run_type": a, "exit_status": b, "ended_at": e, "summary": s} for a, b, e, s in cur.fetchall()]
    finally:
        c.rollback()
        c.close()


def timi(t):
    if isinstance(t, str):
        t = dt.datetime.fromisoformat(t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radir-ur-skra", default=None)
    ap.add_argument("--nu", default=None, help="próf: viðmiðunartími (ISO), annars núið")
    a = ap.parse_args()
    nu = timi(a.nu) if a.nu else dt.datetime.now(dt.timezone.utc)
    try:
        radir = json.loads(Path(a.radir_ur_skra).read_text(encoding="utf-8")) if a.radir_ur_skra else lesa_grunn()
    except Exception as e:
        print("SOLUFERLI_MV: nott=MAELING_MISTOKST sopun=MAELING_MISTOKST")
        print(f"L lestur MAELING_MISTOKST {type(e).__name__}")
        return 0
    eftir = {}
    for r in radir:  # nýjasta röð á keyrslu (skráin má bera fleiri)
        k = r["run_type"].replace("soluferli_mv_", "")
        if k not in eftir or timi(r.get("ended_at")) > timi(eftir[k].get("ended_at")):
            eftir[k] = r
    fl = {k: flokka((eftir.get(k) or {}).get("exit_status"), timi((eftir.get(k) or {}).get("ended_at")), nu) for k in KEYRSLUR}
    print("SOLUFERLI_MV: " + " ".join(f"{k}={fl[k]}" for k in KEYRSLUR))
    for k in KEYRSLUR:
        r = eftir.get(k)
        if not r:
            continue
        t = timi(r.get("ended_at"))
        kl = t.astimezone(dt.timezone.utc).strftime("%d.%m %H:%M") if t else "?"
        print(f"L {k} {fl[k]} {kl} {HEITI[k]}: {skyring(fl[k], r)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
