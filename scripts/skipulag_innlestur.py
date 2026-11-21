"""skipulag_innlestur.py — cc361: vikulegur innlestur mála úr fundargerðum sveitarfélaga í public.skipulag_mal.

  python scripts/skipulag_innlestur.py --thurrt [--ut MAPPA]   # les heimild + okkar grunn (aðeins lestur), reiknar hlið,
                                                               # skrifar staging í MAPPA (parquet + hlid.json). Ekkert í grunn.
  python scripts/skipulag_innlestur.py --beita                 # sama + staging í pg_temp, hlið, skipti í EINNI færslu, pipeline_runs
  python scripts/skipulag_innlestur.py --beita --leyfa-handvirka   # fyrsta hleðsla: vikuleg_keyrsla má vera handvirk (GO)

HEIMILD: registur_ut.skipulag_verdmat + registur_ut.skipulag_stada, hlutverk verdmat_skipulag (aðeins lestur, 60 s þak,
  mest 3 tengingar -> EIN tenging hér), session pooler 5432. Lesið í einni read-only færslu: bendill + fetch 20000.
  Lykilorð úr umhverfi (SKIPULAG_UT_LYKILORD; keyrarinn hleður D:\\env.local), annars úr D:\\env.local (utf-8-sig).
  Lykilorðið fer aldrei í úttak; villuskilaboð hreinsuð.

HLIÐ (öll verða að standast, annars stendur gamla taflan, rc 2, VAKT-VIDVORUN í status-logg + vaktarpóstur):
  H1 lekapróf: 0 einstaklings-kennitölur (6+4 tölustafir, vartala, mánuður 01-12, dagur 01-31, öld 9/0/8) í textadálkum.
  H2 raðafjöldi (mál með landnr) >= 95/100 af raðafjölda lifandi töflu.
  H3 ferskleiki: elsta sidast_sott í skipulag_stada ekki eldri en 10 dagar.
  H4 skipulag_stada.utflutt (hæsta) nýrri en heimild_utflutt síðustu hleðslu.
  H5 vikuleg_keyrsla byrjar á „í lagi" í öllum röðum skipulag_stada (--leyfa-handvirka sleppir, aðeins með GO).
  H6 dálkar heimildar eins og vænst er (skemabreyting = fall).
SKIPTI: ein færsla á verdmat-grunni: COPY í pg_temp-staging -> talning -> DELETE + INSERT í public.skipulag_mal -> talning
  -> COMMIT. DELETE (ekki TRUNCATE): lesendur sjá gömlu gögnin þar til COMMIT, engin ACCESS EXCLUSIVE-læsing.
  Snertir engar töflur sópunar/næturkeðju; les ekki public.properties.
KÓÐAR: 0 í lagi · 2 hlið féll (ekkert skrifað) · 3 villa · 4 heimild næst ekki.
"""
from __future__ import annotations
import argparse, datetime as dt, io, json, os, re, socket, sys, time
from pathlib import Path

import psycopg2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HOST = "aws-1-eu-central-1.pooler.supabase.com"
USER = "verdmat_skipulag.vpynocsqemidfbttiogs"
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
STATUS_LOG = Path(r"D:\verdmat_status.log")
RUN_TYPE = "skipulag_vikulegt"
SVFN = {"Reykjavíkurborg": 0, "Kópavogsbær": 1000, "Seltjarnarnesbær": 1100, "Garðabær": 1300,
        "Hafnarfjarðarkaupstaður": 1400, "Mosfellsbær": 1604}
VAENTIR_DALKAR = ["id", "sveitarfelag", "nefnd", "dagsetning", "fundarnumer", "malsnumer", "heimilisfang", "landnr",
                  "landnr_uppruni", "fyrirsogn", "malsflokkur", "lysing", "nidurstada", "slod_fundargerd", "keyrt",
                  "regla", "hreinsun_utgafa", "hreinsad"]
TEXTADALKAR = ["sveitarfelag", "nefnd", "fundarnumer", "malsnumer", "heimilisfang", "landnr_uppruni", "fyrirsogn",
               "malsflokkur", "lysing", "nidurstada", "slod_fundargerd", "regla", "hreinsun_utgafa"]
# röð dálka í public.skipulag_mal (án hladid_at, sem fær default)
TOFLU_DALKAR = ["id", "sveitarfelag", "svfn", "nefnd", "dagsetning", "fundarnumer", "malsnumer", "heimilisfang", "landnr",
                "landnr_uppruni", "fyrirsogn", "malsflokkur", "lysing", "nidurstada", "slod_fundargerd", "hreinsad",
                "hreinsun_utgafa", "heimild_keyrt", "heimild_utflutt"]
FALL_HLUTFALL = 0.95
FERSK_DAGAR = 10
KT = re.compile(r"(?<!\d)(\d{6})[-\s.]?(\d{4})(?!\d)")
W = (3, 2, 7, 6, 5, 4, 3, 2)


def log(*a):
    print(dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), *a, flush=True)


def lykilord() -> str:
    v = os.environ.get("SKIPULAG_UT_LYKILORD")
    if v:
        return v
    for lina in open(r"D:\env.local", encoding="utf-8-sig"):
        lina = lina.strip()
        if lina.startswith("SKIPULAG_UT_LYKILORD="):
            v = lina.split("=", 1)[1].strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            return v
    raise RuntimeError("SKIPULAG_UT_LYKILORD vantar")


def einstaklings_kt(s10: str) -> bool:
    d = [int(c) for c in s10]
    r = 11 - sum(a * b for a, b in zip(W, d[:8])) % 11
    r = 0 if r == 11 else r
    if r == 10 or r != d[8] or d[9] not in (9, 0, 8):
        return False
    return 1 <= int(s10[2:4]) <= 12 and 1 <= int(s10[0:2]) <= 31


def lekaprof(radir: list[dict]) -> int:
    n = 0
    for r in radir:
        for c in TEXTADALKAR:
            v = r.get(c)
            if isinstance(v, str):
                for m in KT.finditer(v):
                    if einstaklings_kt(m.group(1) + m.group(2)):
                        n += 1
    return n


def lesa_heimild():
    pw = lykilord()
    t0 = time.time()
    try:
        c = psycopg2.connect(host=HOST, port=5432, user=USER, password=pw, dbname="postgres", sslmode="require",
                             connect_timeout=20, application_name="verdmat_skipulag_innlestur")
    except Exception as e:  # noqa: BLE001
        raise ConnectionError(str(e).replace(pw, "***")[:300]) from None
    finally:
        del pw
    try:
        cur = c.cursor()
        cur.execute("begin read only")
        cur.execute("declare c no scroll cursor for select * from registur_ut.skipulag_verdmat order by id")
        radir, nafn = [], None
        while True:
            cur.execute("fetch 20000 from c")
            if nafn is None:
                nafn = [d[0] for d in cur.description]
            b = cur.fetchall()
            if not b:
                break
            radir.extend(dict(zip(nafn, r)) for r in b)
        cur.execute("close c")
        cur.execute("select * from registur_ut.skipulag_stada")
        sn = [d[0] for d in cur.description]
        stada = [dict(zip(sn, r)) for r in cur.fetchall()]
        cur.execute("commit")
    finally:
        c.close()
    return nafn, radir, stada, time.time() - t0


def lesa_sidustu(dbconfig: Path):
    """(raðafjöldi lifandi töflu, heimild_utflutt síðustu hleðslu) eða (None, None) ef taflan er ekki til."""
    c = psycopg2.connect(dbconfig.read_text(encoding="utf-8-sig").strip(), connect_timeout=15)
    try:
        cur = c.cursor()
        cur.execute("set statement_timeout = '60s'")
        cur.execute("select to_regclass('public.skipulag_mal') is not null")
        if not cur.fetchone()[0]:
            return None, None
        cur.execute("select count(*), max(heimild_utflutt) from public.skipulag_mal")
        n, u = cur.fetchone()
        return n, u
    finally:
        c.rollback(); c.close()


def umbreyta(radir, utflutt):
    ut, othekkt = [], {}
    for r in radir:
        if r.get("landnr") is None:
            continue
        s = r["sveitarfelag"]
        if s not in SVFN:
            othekkt[s] = othekkt.get(s, 0) + 1
        ut.append({"id": r["id"], "sveitarfelag": s, "svfn": SVFN.get(s), "nefnd": r["nefnd"], "dagsetning": r["dagsetning"],
                   "fundarnumer": r["fundarnumer"], "malsnumer": r["malsnumer"], "heimilisfang": r["heimilisfang"],
                   "landnr": int(r["landnr"]), "landnr_uppruni": r["landnr_uppruni"], "fyrirsogn": r["fyrirsogn"],
                   "malsflokkur": r["malsflokkur"], "lysing": r["lysing"], "nidurstada": r["nidurstada"],
                   "slod_fundargerd": r["slod_fundargerd"], "hreinsad": bool(r["hreinsad"]),
                   "hreinsun_utgafa": r["hreinsun_utgafa"], "heimild_keyrt": r["keyrt"], "heimild_utflutt": utflutt})
    return ut, othekkt


def hlid(nafn, radir, stada, ut, n_lifandi, utflutt_sidast, leyfa_handvirka):
    nu = dt.datetime.now(dt.timezone.utc)
    H = {}
    H["H6_dalkar"] = {"ok": nafn == VAENTIR_DALKAR, "fengnir": nafn}
    n_kt = lekaprof(radir)
    H["H1_lekaprof"] = {"ok": n_kt == 0, "einstaklings_kt": n_kt}
    if n_lifandi is None or n_lifandi == 0:
        H["H2_radafjoldi"] = {"ok": len(ut) > 0, "nytt": len(ut), "lifandi": n_lifandi, "athugasemd": "fyrsta hleðsla"}
    else:
        H["H2_radafjoldi"] = {"ok": len(ut) >= FALL_HLUTFALL * n_lifandi, "nytt": len(ut), "lifandi": n_lifandi,
                              "hlutfall": round(len(ut) / n_lifandi, 4)}
    sott = [s["sidast_sott"] for s in stada if s.get("sidast_sott")]
    elst = min(sott) if sott else None
    H["H3_ferskleiki"] = {"ok": bool(elst) and (nu - elst) <= dt.timedelta(days=FERSK_DAGAR) and len(sott) == len(stada),
                          "elsta_sidast_sott": elst.isoformat() if elst else None,
                          "aldur_dagar": round((nu - elst).total_seconds() / 86400, 2) if elst else None}
    utfl = max((s["utflutt"] for s in stada if s.get("utflutt")), default=None)
    H["H4_utflutt"] = {"ok": utfl is not None and (utflutt_sidast is None or utfl > utflutt_sidast),
                       "utflutt": utfl.isoformat() if utfl else None,
                       "sidasta_hledsla": utflutt_sidast.isoformat() if utflutt_sidast else None}
    vk = sorted({str(s.get("vikuleg_keyrsla")) for s in stada})
    vk_ok = all(str(s.get("vikuleg_keyrsla") or "").strip().casefold().startswith("í lagi") for s in stada) and len(stada) > 0
    H["H5_vikuleg_keyrsla"] = {"ok": vk_ok or leyfa_handvirka, "gildi": vk, "leyft_handvirkt": bool(leyfa_handvirka and not vk_ok)}
    return H, utfl


def vaktarpostur(efni: str, texti: str, senda: bool):
    utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    if not senda:
        log(f"[ÞURRT] vaktarpóstur myndi fara: {efni}")
        return
    try:
        with open(STATUS_LOG, "a", encoding="utf-8") as f:
            f.write(f"{utc} !! VAKT-VIDVORUN: skipulag_innlestur — {efni}\r\n")
    except OSError as e:
        log("status-logg náðist ekki:", type(e).__name__)
    lykill, fra, til = os.environ.get("RESEND_API_KEY"), os.environ.get("ABENDING_FRA"), os.environ.get("ABENDING_MOTTAKANDI")
    if not (lykill and fra and til):
        log("vaktarpóstur: lykil/sendanda/viðtakanda vantar — aðeins status-logg"); return
    try:
        import requests
        r = requests.post("https://api.resend.com/emails", timeout=20, headers={"Authorization": f"Bearer {lykill}"},
                          json={"from": fra, "to": [til], "subject": f"[verdmat vakt] skipulag: {efni}", "text": texti})
        log("vaktarpóstur:", r.status_code)
    except Exception as e:  # noqa: BLE001
        log("vaktarpóstur féll:", type(e).__name__)


def skrifa(dbconfig: Path, ut: list[dict], prof: bool = False):
    """Ein færsla: staging (pg_temp) -> talning -> DELETE+INSERT -> talning -> COMMIT (eða ROLLBACK ef prof)."""
    import csv
    c = psycopg2.connect(dbconfig.read_text(encoding="utf-8-sig").strip(), connect_timeout=15)
    c.autocommit = False
    t0 = time.time()
    try:
        c.rollback()
        cur = c.cursor()
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("SET LOCAL lock_timeout = '5s'")
        cur.execute("SET LOCAL statement_timeout = '120s'")
        cur.execute("CREATE TEMP TABLE stg (LIKE public.skipulag_mal INCLUDING DEFAULTS) ON COMMIT DROP")
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        for r in ut:
            w.writerow(["\\N" if r[k] is None else (r[k].isoformat() if hasattr(r[k], "isoformat") else
                        ("t" if r[k] is True else "f" if r[k] is False else r[k])) for k in TOFLU_DALKAR])
        buf.seek(0)
        cur.copy_expert(f"COPY stg ({', '.join(TOFLU_DALKAR)}) FROM STDIN WITH (FORMAT csv, NULL '\\N')", buf)
        cur.execute("select count(*) from stg")
        n_stg = cur.fetchone()[0]
        if n_stg != len(ut):
            raise RuntimeError(f"staging {n_stg} != {len(ut)}")
        t_copy = time.time() - t0
        cur.execute("select count(*) from public.skipulag_mal")
        n_fyrir = cur.fetchone()[0]
        cur.execute("DELETE FROM public.skipulag_mal")
        cur.execute(f"INSERT INTO public.skipulag_mal ({', '.join(TOFLU_DALKAR)}) SELECT {', '.join(TOFLU_DALKAR)} FROM stg")
        cur.execute("select count(*) from public.skipulag_mal")
        n_eftir = cur.fetchone()[0]
        if n_eftir != len(ut):
            raise RuntimeError(f"eftir skipti {n_eftir} != {len(ut)}")
        if prof:
            c.rollback()
        else:
            c.commit()
        return {"fyrir": n_fyrir, "eftir": n_eftir, "copy_s": round(t_copy, 1), "alls_s": round(time.time() - t0, 1),
                "prof_rollback": prof}
    except Exception:
        c.rollback(); raise
    finally:
        c.close()


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--thurrt", action="store_true"); g.add_argument("--beita", action="store_true")
    ap.add_argument("--leyfa-handvirka", action="store_true")
    ap.add_argument("--ut", type=Path, default=None, help="þurrkeyrsla: mappa fyrir staging + hlið (parquet/json)")
    ap.add_argument("--dbconfig", type=Path, default=DBCONFIG)
    a = ap.parse_args()
    t0 = time.time()
    run_id = conn_log = None
    if a.beita:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from migration_helpers import open_connection, start_run, finish_run
        conn_log = open_connection(a.dbconfig)
        run_id = start_run(conn_log, RUN_TYPE)
        log("pipeline_runs.id =", run_id)
    samantekt = {}
    rc = 0
    try:
        try:
            nafn, radir, stada, lestur_s = lesa_heimild()
        except ConnectionError as e:
            log("HEIMILD NÆST EKKI:", e)
            vaktarpostur("heimild næst ekki", f"Tenging við heimild féll: {e}", senda=a.beita)
            samantekt = {"villa": "heimild næst ekki"}; rc = 4; return rc
        log(f"heimild: {len(radir)} raðir, stada {len(stada)} raðir, {lestur_s:.1f} s")
        n_lif, utfl_sidast = lesa_sidustu(a.dbconfig)
        utfl = max((s["utflutt"] for s in stada if s.get("utflutt")), default=None)
        ut, othekkt = umbreyta(radir, utfl)
        H, _ = hlid(nafn, radir, stada, ut, n_lif, utfl_sidast, a.leyfa_handvirka)
        allt_ok = all(h["ok"] for h in H.values())
        samantekt = {"heimild_radir": len(radir), "med_landnr": len(ut), "othekkt_sveitarfelag": othekkt,
                     "lestur_s": round(lestur_s, 1), "hlid": H, "utflutt": utfl.isoformat() if utfl else None}
        for k, h in H.items():
            log(f"  {k}: {'OK' if h['ok'] else 'FALL'}  {json.dumps({x: y for x, y in h.items() if x != 'ok'}, ensure_ascii=False, default=str)[:200]}")
        if a.thurrt and a.ut:
            import pandas as pd
            a.ut.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(ut, columns=TOFLU_DALKAR).to_parquet(a.ut / "staging_skipulag_mal.parquet", index=False)
            (a.ut / "thurrkeyrsla_hlid.json").write_text(json.dumps(samantekt, ensure_ascii=False, indent=1, default=str),
                                                        encoding="utf-8")
            log("þurrkeyrsla: staging vistað í", a.ut)
        if not allt_ok:
            fallin = [k for k, h in H.items() if not h["ok"]]
            log("HLIÐ FÉLL:", ", ".join(fallin), "— gamla taflan stendur")
            vaktarpostur("hlið féll: " + ", ".join(fallin),
                         "Vikulegur innlestur skipulagsmála stöðvaðist á hliði; gamla taflan stendur.\n\n" +
                         json.dumps(H, ensure_ascii=False, indent=1, default=str), senda=a.beita)
            rc = 2; return rc
        if a.thurrt:
            log("ÞURRT: öll hlið standast; ekkert skrifað í grunn."); return 0
        res = skrifa(a.dbconfig, ut)
        samantekt["skipti"] = res
        log("SKIPT:", res)
        return 0
    except Exception as e:  # noqa: BLE001
        log("VILLA:", type(e).__name__, str(e)[:300])
        samantekt["villa"] = type(e).__name__
        vaktarpostur("villa", f"{type(e).__name__}", senda=a.beita)
        rc = 3; return rc
    finally:
        samantekt["wall_s"] = round(time.time() - t0, 1)
        if run_id is not None:
            try:
                finish_run(conn_log, run_id, "success" if rc == 0 else "failed", json.loads(json.dumps(samantekt, default=str)))
            finally:
                conn_log.close()


if __name__ == "__main__":
    sys.exit(main())
