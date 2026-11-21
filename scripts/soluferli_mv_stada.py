"""cc364: staða síðasta skrefs (endurnýjun scraper.soluferli_opin_mv) fyrir status-probe og vaktarpóst. Aðeins lestur.

Les nýjustu röð í public.pipeline_runs (síðustu 48 klst.) fyrir run_type soluferli_mv_nott og soluferli_mv_sopun
og flokkar exit_status í EINU falli (flokka):
    success              -> OK      (grænt)
    skipped              -> SLEPPT  (hvorki villa né grænt: fyrra skref keðjunnar féll og það er þegar hávært þar)
    engin röð            -> VANTAR  (hlutlaust: t.d. fyrir beitingu cc364, eða keðja sem ræstist ekki, sem er hávært annars staðar)
    allt annað (failed, crashed, halted, óþekkt) -> FALL (villa)
Úttak (stdout, UTF-8):
    SOLUFERLI_MV: nott=<FLOKKUR> sopun=<FLOKKUR>
    L <keyrsla> <FLOKKUR> <DD.MM HH:MM> <skýring á mannamáli>     (ein lína á keyrslu sem til er)
rc alltaf 0; fall í lestri gefur „SOLUFERLI_MV: nott=MAELING_MISTOKST sopun=MAELING_MISTOKST“.
--radir-ur-skra <json>: les falsaðar raðir [{run_type, exit_status, ended_at, summary}] í stað grunns (próf).
"""
import argparse, datetime as dt, json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEYRSLUR = ("nott", "sopun")
HEITI = {"nott": "eftir næturkeðju", "sopun": "eftir sópun"}


def flokka(exit_status):
    """Eina flokkunin: success = OK, skipped = SLEPPT, engin = VANTAR, annað = FALL."""
    if exit_status is None:
        return "VANTAR"
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
                       where run_type in ('soluferli_mv_nott', 'soluferli_mv_sopun') and started_at > now() - interval '48 hours'
                       order by run_type, started_at desc, id desc""")
        return [{"run_type": a, "exit_status": b, "ended_at": e, "summary": s} for a, b, e, s in cur.fetchall()]
    finally:
        c.rollback()
        c.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radir-ur-skra", default=None)
    a = ap.parse_args()
    try:
        radir = json.loads(Path(a.radir_ur_skra).read_text(encoding="utf-8")) if a.radir_ur_skra else lesa_grunn()
    except Exception as e:
        print("SOLUFERLI_MV: nott=MAELING_MISTOKST sopun=MAELING_MISTOKST")
        print(f"L lestur MAELING_MISTOKST {type(e).__name__}")
        return 0
    eftir = {r["run_type"].replace("soluferli_mv_", ""): r for r in radir}
    fl = {k: flokka((eftir.get(k) or {}).get("exit_status")) for k in KEYRSLUR}
    print("SOLUFERLI_MV: " + " ".join(f"{k}={fl[k]}" for k in KEYRSLUR))
    for k in KEYRSLUR:
        r = eftir.get(k)
        if not r:
            continue
        t = r.get("ended_at")
        if isinstance(t, str):
            t = dt.datetime.fromisoformat(t)
        kl = t.astimezone(dt.timezone.utc).strftime("%d.%m %H:%M") if t else "?"
        print(f"L {k} {fl[k]} {kl} {HEITI[k]}: {skyring(fl[k], r)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
