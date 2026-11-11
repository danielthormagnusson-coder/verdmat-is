"""cc336b (GO Danna 11.11.2026, G1): vikulegt afrit, verk `verdmat-weekly-db-afrit` (sunnudaga 10:00 UTC).
Vikulegt afrit: (1) pg_dump -Fc af app-skemum, (2) SQLite-skyndimyndir af scraper_data með
online backup API (öruggt þótt sókn skrifi), (3) rclone copy á R2 db_afrit/vikulegt/<dags>/, (4) halda 5 vikur.
Keyrt t.d. sunnudaga 10:00 UTC (utan 01:00–07:30 og fjarri 03:00-afriti). Lykilorð aldrei prentað/skráð.

Les:   D:\\verdmat-is\\.dbconfig (tenging, port þvingað í 5432 = session-hamur pooler)
       D:\\verdmat-is\\.env (R2_BUCKET_NAME)
Skrifar: D:\\verdmat-is\\backup_weekly\\<dags>\\ (staðbundið, eytt eftir vel heppnaða upphleðslu nema síðasta)
         D:\\verdmat-is\\backup_log\\vikulegt_<dags>.json
"""
from __future__ import annotations
import datetime as dt, hashlib, json, os, re, shutil, sqlite3, subprocess, sys, time, urllib.parse
from pathlib import Path

BIN = Path(r"D:\verdmat-is\tools\postgres17\pgsql\bin")
RCLONE = Path(r"D:\verdmat-is\tools\rclone\rclone.exe")
RCONF = Path(r"D:\verdmat-is\tools\rclone\rclone.conf")
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
ENV = Path(r"D:\verdmat-is\.env")
STAGE = Path(r"D:\verdmat-is\backup_weekly")
LOG = Path(r"D:\verdmat-is\backup_log")
SKEMU = ["public", "scraper", "semantic", "registur_utflutningur", "supabase_migrations"]
SQLITE = [  # parsed_mbl.db (3,6 GB) EKKI með — ákvörðun Danna 11.11 (endursmíðanlegt úr raw_mbl.db)
    Path(r"D:\verdmat-is\scraper_data\raw_mbl.db"),
    Path(r"D:\verdmat-is\scraper_data\raw_myigloo.db"),
    Path(r"D:\verdmat-is\scraper_data\raw_visir.db"),
    Path(r"D:\verdmat-is\scraper_data\listing_images.db"),
]
HALDA_VIKUR = 5
BANN_GLUGGI = (1, 7.5)  # UTC klst: keyrir EKKI 01:00–07:30


def pg_env() -> dict:
    u = urllib.parse.urlparse(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    return dict(os.environ, PGHOST=u.hostname, PGPORT="5432", PGUSER=urllib.parse.unquote(u.username),
                PGPASSWORD=urllib.parse.unquote(u.password), PGDATABASE=(u.path.lstrip("/") or "postgres"),
                PGSSLMODE="require", PGAPPNAME="verdmat_vikuafrit")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def bucket() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*R2_BUCKET_NAME\s*=\s*(\S+)", line)
        if m:
            return m.group(1).strip("'\"")
    raise SystemExit("R2_BUCKET_NAME vantar")


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    h = now.hour + now.minute / 60
    if BANN_GLUGGI[0] <= h < BANN_GLUGGI[1] and "--leyfa-glugga" not in sys.argv:
        print("HALT: innan 01:00–07:30 UTC"); return 2
    dags = now.strftime("%Y-%m-%d")
    d = STAGE / dags
    d.mkdir(parents=True, exist_ok=True)
    rep = {"dags": dags, "hafid": now.isoformat(), "hlutir": []}

    # 1) pg_dump
    out = d / f"verdmat_{dags}.dump"
    args = [str(BIN / "pg_dump.exe"), "-Fc", "-Z", "6", "--no-owner", "--no-privileges", "-f", str(out)]
    for s in SKEMU:
        args += ["-n", s]
    t = time.time()
    r = subprocess.run(args, env=pg_env(), capture_output=True, text=True, timeout=3600)
    rep["pg_dump"] = {"rc": r.returncode, "sek": round(time.time() - t, 1), "villa": r.stderr[-800:]}
    if r.returncode != 0:
        print("pg_dump FÉLL", r.stderr[-800:]); _skra(rep); return 1
    # sannreyna að dump sé læsilegt (TOC)
    toc = subprocess.run([str(BIN / "pg_restore.exe"), "-l", str(out)], capture_output=True, text=True)
    rep["pg_dump"]["toc_faerslur"] = sum(1 for l in toc.stdout.splitlines() if l and not l.startswith(";"))
    rep["pg_dump"]["toflugogn"] = toc.stdout.count(" TABLE DATA ")

    # 2) SQLite online backup
    for src in SQLITE:
        if not src.exists():
            continue
        dst = d / src.name
        t = time.time()
        s = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=60)
        dd = sqlite3.connect(dst)
        s.backup(dd, pages=4096, sleep=0.05)
        ok = dd.execute("pragma quick_check").fetchone()[0]
        dd.close(); s.close()
        rep["hlutir"].append({"skra": src.name, "sek": round(time.time() - t, 1), "quick_check": ok})

    for p in sorted(d.iterdir()):
        rep["hlutir"].append({"skra": p.name, "baeti": p.stat().st_size, "sha256": sha256(p)})
    (d / "manifest.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")

    # 3) upphleðsla
    b = bucket()
    t = time.time()
    r = subprocess.run([str(RCLONE), "--config", str(RCONF), "copy", str(d), f"r2backup:{b}/db_afrit/vikulegt/{dags}/",
                        "--transfers", "4", "--checksum", "--log-file", str(LOG / f"vikulegt_{dags}_rclone.log"),
                        "--log-level", "INFO"], capture_output=True, text=True)
    rep["rclone"] = {"rc": r.returncode, "sek": round(time.time() - t, 1)}
    if r.returncode != 0:
        _skra(rep); return 1
    r = subprocess.run([str(RCLONE), "--config", str(RCONF), "check", str(d), f"r2backup:{b}/db_afrit/vikulegt/{dags}/",
                        "--one-way"], capture_output=True, text=True)
    rep["rclone_check_rc"] = r.returncode

    # 4) varðveisla: halda HALDA_VIKUR nýjustu á R2; staðbundið aðeins nýjasta
    ls = subprocess.run([str(RCLONE), "--config", str(RCONF), "lsf", "--dirs-only", f"r2backup:{b}/db_afrit/vikulegt/"],
                        capture_output=True, text=True).stdout.split()
    dirs = sorted(x.rstrip("/") for x in ls)
    bad = [x for x in dirs if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x)]
    if bad or len(dirs) > 20:
        rep["vardveisla"] = f"HALT: óvænt forskeyti {bad[:3]} / {len(dirs)}"
    else:
        eyda = dirs[:-HALDA_VIKUR]
        for x in eyda:
            subprocess.run([str(RCLONE), "--config", str(RCONF), "purge", f"r2backup:{b}/db_afrit/vikulegt/{x}/"], timeout=600)
        rep["vardveisla"] = {"a_r2": len(dirs) - len(eyda), "eytt": eyda}
    for old in sorted(STAGE.iterdir())[:-1]:
        shutil.rmtree(old, ignore_errors=True)
    _skra(rep)
    print(json.dumps({k: v for k, v in rep.items() if k != "hlutir"}, ensure_ascii=False))
    return 0 if rep.get("rclone_check_rc") == 0 else 1


def _skra(rep: dict) -> None:
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / f"vikulegt_{rep['dags']}.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    # Verkið keyrir python beint (engin run_*.ps1-umbúð): stdout/stderr í dagsetta skrá svo
    # ekkert hverfi (sbr. cc43), og óvænt villa skráð með rakningu + útgöngukóða.
    LOG.mkdir(parents=True, exist_ok=True)
    _f = open(LOG / f"vikulegt_{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}_keyrsla.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = _f
    try:
        rc = main()
    except BaseException:
        import traceback
        traceback.print_exc()
        rc = 3
    print(f"útgöngukóði {rc}")
    sys.exit(rc)
