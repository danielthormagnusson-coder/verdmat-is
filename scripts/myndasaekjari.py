#!/usr/bin/env python3
r"""myndasaekjari.py — cc111 FASI 1. Eitt kóðaflæði, tveir hamir.

  --framvirkt    watermark-drifið: auglýsingar sem hafa breyst eða bera ófulla þekju
  --bakfylling   listar cc109 á diski (D:\_audit\cc109_myndamal\cc109_gat_slodir.csv)
  --endurbyggja-visi   sáir sóknarvísinum af R2 + image_store + listing_images.db
  --stadfesta    skemavaliderar allt manifestið

Bókhaldið er DISKMANIFEST (JSONL). ENGIN skrif í Postgres — lesið er read-only.
Engin DB-migration. Taflan kemur síðar og hleðst af manifestinu.

ÚRSKURÐIR BORÐSINS SEM KÓÐINN BER (cc111):
  U1  afbrigði = `regular` (mbl) / eina slóðin (myigloo). Eitt afbrigði.
  U2  umfang = A + B (virkar OG horfnar auglýsingar).
  U3  röð = myigloo fyrst; mbl stigað 1->2->4 þræðir, hvert þrep mælt og bókað
      ÁÐUR en næsta hefst; fyrsta frávik -> falla niður um þrep og HALDA þar,
      aldrei hækka aftur í sömu keyrslu.
  U4  R2-speglun INNAN SÖMU HRINU og sókn, m/reikningsjöfnuði per hrinu.
  U5  sækjarinn lokar AUGLÝSINGAgatinu, ekki eignagatinu.

GILDRUR SEM KÓÐINN VER (cc109):
  * URL er ALDREI auðkenni geymdrar myndar. Myndin er auðkennd á `sha256`
    (innihald); manifest-röðin á (lind, source_listing_id, image_nr, afbrigdi).
    `myndavisir.db.slod` er EINGÖNGU "hef ég þegar reynt þessa slóð"-hraðall og
    má aldrei nota til að fletta upp geymdri mynd: 44.206 sóttar slóðir eru
    horfnar úr photos_json og bætin lifa samt (cc109 §1.5).
  * `listing_images.db.listing_status` er FROSIN merking frá 27.06 og er hvergi
    lesin. Staða auglýsingar kemur EINGÖNGU úr `scraper.listings` (cc109 §1.6).
  * Þak og reikningsjöfnun er á BÆTUM jafnt sem fjölda (myigloo = 11% mynda,
    57% bæta).
  * `sync` kemur hvergi fyrir. Áfangaforskeyti verður að byrja á `augl-myndir`.
  * `exit 0` sannar ekkert — staðan er í stada.json með rowcounts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import struct
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

# ----------------------------------------------------------------------------- slóðir
ROT          = Path(r"D:\verdmat-is")
STORE        = ROT / "image_store"
SCRAPER_DATA = ROT / "scraper_data"
MANIFEST_ROT = SCRAPER_DATA / "myndamanifest"
VISIR_DB     = MANIFEST_ROT / "myndavisir.db"
WATERMARK_JL = MANIFEST_ROT / "watermark.jsonl"
HRINUR_JL    = MANIFEST_ROT / "hrinur.jsonl"
STADA_JSON   = MANIFEST_ROT / "stada.json"
KILL_SWITCH  = SCRAPER_DATA / "STOP_MYNDASAEKJARI"

DBCFG        = ROT / ".dbconfig"
LISTING_IMGS = SCRAPER_DATA / "listing_images.db"
CC109_GAT    = Path(r"D:\_audit\cc109_myndamal\cc109_gat_slodir.csv")
# cc109 skrifaði skemadrögin í verdmat-ai-safnið (gitignore-að); app-safnið er varaleið.
SKEMA_LEIDIR = [
    ROT / "verdmat-ai" / "docs" / "fable_prep" / "prototypes" / "cc109_manifest_skema_DROG.json",
    ROT / "app" / "docs" / "fable_prep" / "prototypes" / "cc109_manifest_skema_DROG.json",
]

RCLONE       = ROT / "tools" / "rclone" / "rclone.exe"
RCLONE_CONF  = ROT / "tools" / "rclone" / "rclone.conf"
R2_REMOTE    = "r2backup:verdmat-backups"
R2_FORSKEYTI = "augl-myndir"            # HARÐA REGLAN — sjá _r2_afangi()
AFRIT_FORSK  = ("current", "archive")   # næturafritið, mælt í BÁÐUM endum (cc97)

# cc111 liður 0: manifestið speglast á EIGIÐ forskeyti, í lok hverrar hrinu, í sömu
# keyrslu og sókn. Ekki breyting á næturafritsverkinu; ekki systkini `augl-myndir/`.
MANIFEST_R2 = "myndamanifest"
# Útilokað úr speglun: LIFANDI SQLite (WAL — afrit í miðri keyrslu er rifið og lítur
# samt út eins og afrit), afleiddar skrár og vinnuskrár. Ekkert af þessu ber
# kortlagninguna: `myndavisir.db` er endurbyggjanlegur úr JSONL-bókinni +
# listing_images.db + R2-lyklalistanum (`--endurbyggja-visi`).
MANIFEST_UTILOKANIR = ["myndavisir.db", "myndavisir.db-wal", "myndavisir.db-shm",
                       "r2_lyklar.txt", "tmp/**"]

# ----------------------------------------------------------------------------- fastar
CT_EXT = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
          "image/webp": ".webp", "image/gif": ".gif", "image/avif": ".avif"}
LOGLEG_ENDING = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}

AFBRIGDI = {"mbl": "regular", "myigloo": "direct"}      # U1
STIG     = [1, 2, 4]                                     # U3

ENDURTILRAUN_HAMARK = 2
ENDURTILRAUN_BIL_D  = 7

# frávikaregla U3 — þröskuldar bókaðir, ekki huglægir
FRAVIK_VILLUHLUTFALL = 0.02    # non-200 að frádregnum 404
FRAVIK_5XX           = 3
FRAVIK_HRADAFALL     = 0.80    # afköst/þráð undir 80% af 1-þráða grunni (>20% fall)

NYLINA = chr(10)

RE_DIFF  = re.compile(r"(\d+)\s+differences found")
RE_MATCH = re.compile(r"(\d+)\s+matching files")


def nu() -> datetime:
    return datetime.now(timezone.utc)


def nu_s() -> str:
    return nu().isoformat(timespec="seconds")


# ============================================================================= log
class Log:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(path, "a", encoding="utf-8")
        self.lock = threading.Lock()

    def __call__(self, msg: str) -> None:
        line = f"{nu_s()}  {msg}"
        with self.lock:
            print(line, flush=True)
            self.fh.write(line + "\n")
            self.fh.flush()


# ============================================================================= myndhaus
def maelingar(data: bytes) -> tuple[int | None, int | None]:
    """Breidd/hæð úr hausnum einum. Engin afkóðun, engin ytri hjálparsöfn."""
    try:
        if data[:2] == b"\xff\xd8":                                   # JPEG
            i, n = 2, len(data)
            while i < n - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                mrk = data[i + 1]
                if mrk in (0xD8, 0x01) or 0xD0 <= mrk <= 0xD7:
                    i += 2
                    continue
                seg = struct.unpack(">H", data[i + 2:i + 4])[0]
                if mrk in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                           0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + seg
        elif data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
            w, h = struct.unpack(">II", data[16:24])
            return w, h
        elif data[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", data[6:10])
            return w, h
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            c = data[12:16]
            if c == b"VP8 ":
                w, h = struct.unpack("<HH", data[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if c == b"VP8L":
                v = int.from_bytes(data[21:25], "little")
                return (v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1
            if c == b"VP8X":
                return (int.from_bytes(data[24:27], "little") + 1,
                        int.from_bytes(data[27:30], "little") + 1)
    except Exception:
        pass
    return None, None


# ============================================================================= vísir
SKEMA_SQL = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS slod (
  url TEXT PRIMARY KEY, lind TEXT NOT NULL, sha256 TEXT, byte_len INTEGER,
  sokn_stada TEXT NOT NULL, http_kodi INTEGER, sott_kl TEXT,
  n_tilraunir INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_slod_sha ON slod(sha256);

CREATE TABLE IF NOT EXISTS sha_geymd (
  sha256 TEXT PRIMARY KEY, lind TEXT NOT NULL, ending TEXT NOT NULL,
  byte_len INTEGER, a_disk INTEGER NOT NULL DEFAULT 0, a_r2 INTEGER NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS vatnsmerki (
  lind TEXT NOT NULL, source_listing_id TEXT NOT NULL,
  sidast_skodad_kl TEXT NOT NULL, photos_json_sha TEXT NOT NULL,
  n_slod INTEGER, n_sott INTEGER, n_tynt INTEGER,
  n_tilraunir INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (lind, source_listing_id));
"""


def opna_visi() -> sqlite3.Connection:
    MANIFEST_ROT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(VISIR_DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=30000")
    db.executescript(SKEMA_SQL)
    db.commit()
    return db


def _kodi_ur_notes(notes: str | None) -> int | None:
    if not notes or not notes.startswith("http:"):
        return None
    try:
        return int(notes.split()[0].split(":")[1])
    except Exception:
        return None


def _saa_slodir(db: sqlite3.Connection, rows: list) -> None:
    """Sáning má aldrei lækka þekkta stöðu: sott > tynt > oreynt."""
    db.executemany("""
        INSERT INTO slod(url,lind,sha256,byte_len,sokn_stada,http_kodi,sott_kl,n_tilraunir)
        VALUES(?,?,?,?,?,?,?,?)
        ON CONFLICT(url) DO UPDATE SET
          sha256      = COALESCE(excluded.sha256, slod.sha256),
          byte_len    = COALESCE(excluded.byte_len, slod.byte_len),
          sokn_stada  = CASE WHEN slod.sokn_stada='sott' OR excluded.sokn_stada='sott' THEN 'sott'
                             WHEN slod.sokn_stada='tynt' OR excluded.sokn_stada='tynt' THEN 'tynt'
                             ELSE 'oreynt' END,
          http_kodi   = COALESCE(excluded.http_kodi, slod.http_kodi),
          sott_kl     = COALESCE(excluded.sott_kl, slod.sott_kl),
          n_tilraunir = MAX(slod.n_tilraunir, excluded.n_tilraunir)
    """, rows)


def endurbyggja_visi(log: Log, r2_lyklaskra: Path | None) -> dict:
    """Sáir vísinum af því sem ÞEGAR er til. Idempotent."""
    db = opna_visi()
    tal: dict = {}

    # ---- 1. R2: hvað liggur raunverulega undir augl-myndir/ ----
    if r2_lyklaskra is None:
        r2_lyklaskra = MANIFEST_ROT / "r2_lyklar.txt"
        log(f"lsf R2 {R2_FORSKEYTI}/ -> {r2_lyklaskra}")
        with open(r2_lyklaskra, "w", encoding="utf-8") as fh:
            rc = subprocess.run(
                [str(RCLONE), "lsf", "-R", f"{R2_REMOTE}/{R2_FORSKEYTI}/",
                 "--config", str(RCLONE_CONF), "--fast-list", "--files-only",
                 "--format", "ps", "--separator", "|"],
                stdout=fh, stderr=subprocess.PIPE, text=True)
        if rc.returncode != 0:
            raise SystemExit(f"rclone lsf féll: {rc.stderr[:400]}")

    UPS_R2 = """INSERT INTO sha_geymd(sha256,lind,ending,byte_len,a_r2) VALUES(?,?,?,?,1)
                ON CONFLICT(sha256) DO UPDATE SET a_r2=1,
                  byte_len=COALESCE(sha_geymd.byte_len, excluded.byte_len)"""
    n_r2, rows = 0, []
    with open(r2_lyklaskra, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            path, size = line.rsplit("|", 1)
            h = path.split("/")
            if h and h[0] == R2_FORSKEYTI:
                h = h[1:]
            if len(h) < 2:
                continue
            sha, _, ext = h[-1].partition(".")
            if not sha or not ext:          # möppulína úr lsf -R, ekki hlutur
                continue
            rows.append((sha, h[0], "." + ext, int(size)))
            n_r2 += 1
            if len(rows) >= 20000:
                db.executemany(UPS_R2, rows); rows.clear()
    if rows:
        db.executemany(UPS_R2, rows)
    db.commit()
    tal["r2_hlutir"] = n_r2
    log(f"  R2-lyklar lesnir: {n_r2:,}")

    # ---- 2. image_store á D: ----
    UPS_DISK = """INSERT INTO sha_geymd(sha256,lind,ending,byte_len,a_disk) VALUES(?,?,?,?,1)
                  ON CONFLICT(sha256) DO UPDATE SET a_disk=1,
                    byte_len=COALESCE(sha_geymd.byte_len, excluded.byte_len)"""
    n_disk, rows = 0, []
    if STORE.exists():
        for lind_dir in sorted(p for p in STORE.iterdir() if p.is_dir()):
            for shard in sorted(p for p in lind_dir.iterdir() if p.is_dir()):
                for f in shard.iterdir():
                    if not f.is_file() or f.name.endswith(".part"):
                        continue
                    sha, _, ext = f.name.partition(".")
                    rows.append((sha, lind_dir.name, "." + ext, f.stat().st_size))
                    n_disk += 1
                    if len(rows) >= 20000:
                        db.executemany(UPS_DISK, rows); rows.clear()
    if rows:
        db.executemany(UPS_DISK, rows)
    db.commit()
    tal["disk_skrar"] = n_disk
    log(f"  image_store skrár: {n_disk:,}")

    # ---- 3. listing_images.db: hvaða SLÓÐIR hafa þegar verið reyndar ----
    #     `status` hér er SÓKNARSTAÐREYND. `listing_status` er ALDREI lesin.
    n_li, rows = 0, []
    if LISTING_IMGS.exists():
        li = sqlite3.connect(f"file:{LISTING_IMGS}?mode=ro", uri=True)
        for url, src, st, sha, blen, fat, notes in li.execute(
                """SELECT url, source, status, content_sha256, byte_len, fetched_at, notes
                   FROM listing_images"""):
            if st == "fetched":
                stada, kodi, tilr = "sott", 200, 1
            elif st == "lost":
                stada, kodi, tilr = "tynt", _kodi_ur_notes(notes), 1
            else:
                stada, kodi, tilr = "oreynt", None, 0
            rows.append((url, src, sha, blen, stada, kodi, fat, tilr))
            n_li += 1
            if len(rows) >= 20000:
                _saa_slodir(db, rows); rows.clear()
        if rows:
            _saa_slodir(db, rows)
        li.close()
        db.commit()
    tal["listing_images_radir"] = n_li
    log(f"  listing_images.db slóðaraðir: {n_li:,}")

    # ---- 4. samræming: slóð telst SÓTT aðeins ef bætin liggja raunverulega á R2 ----
    cur = db.execute("""UPDATE slod SET sokn_stada='oreynt', sha256=NULL
                        WHERE sokn_stada='sott'
                          AND (sha256 IS NULL
                               OR sha256 NOT IN (SELECT sha256 FROM sha_geymd WHERE a_r2=1))""")
    tal["nidurfaerdar_sott_an_baeta"] = cur.rowcount
    db.commit()

    for k, q in (("slod_alls", "SELECT COUNT(*) FROM slod"),
                 ("slod_sott", "SELECT COUNT(*) FROM slod WHERE sokn_stada='sott'"),
                 ("slod_tynt", "SELECT COUNT(*) FROM slod WHERE sokn_stada='tynt'"),
                 ("slod_oreynt", "SELECT COUNT(*) FROM slod WHERE sokn_stada='oreynt'"),
                 ("sha_alls", "SELECT COUNT(*) FROM sha_geymd"),
                 ("sha_a_r2", "SELECT COUNT(*) FROM sha_geymd WHERE a_r2=1"),
                 ("sha_a_disk", "SELECT COUNT(*) FROM sha_geymd WHERE a_disk=1"),
                 ("sha_disk_ekki_r2", "SELECT COUNT(*) FROM sha_geymd WHERE a_disk=1 AND a_r2=0"),
                 ("sha_r2_ekki_disk", "SELECT COUNT(*) FROM sha_geymd WHERE a_r2=1 AND a_disk=0")):
        tal[k] = db.execute(q).fetchone()[0]
    db.close()
    return tal


# ============================================================================= verkefni
class Verk:
    __slots__ = ("lind", "sll", "image_nr", "afbrigdi", "url",
                 "listing_id", "fastnum", "forgangur")

    def __init__(self, lind, sll, image_nr, afbrigdi, url,
                 listing_id=None, fastnum=None, forgangur=9):
        self.lind, self.sll, self.image_nr = lind, sll, image_nr
        self.afbrigdi, self.url = afbrigdi, url
        self.listing_id, self.fastnum, self.forgangur = listing_id, fastnum, forgangur


KANON_SQL = """
  SELECT l.listing_id, l.source, l.source_listing_id, l.fastnum, l.status,
         COALESCE(jsonb_agg(jsonb_build_array(x.nr, x.url) ORDER BY x.nr)
                    FILTER (WHERE x.url IS NOT NULL), '[]'::jsonb) AS slodir
  FROM scraper.listings l
  LEFT JOIN LATERAL (
    SELECT (t.ord - 1)::int AS nr,
           CASE WHEN l.source = 'mbl' THEN t.el ->> 'regular'
                WHEN jsonb_typeof(t.el) = 'string' THEN t.el #>> '{}'
                ELSE NULL END AS url
    FROM jsonb_array_elements(l.photos_json) WITH ORDINALITY AS t(el, ord)
  ) x ON TRUE
  WHERE l.source = ANY(%s)
  GROUP BY l.listing_id
"""


def lesa_auglysingar(lindir: list[str], log: Log):
    """READ-ONLY úr Postgres. Kanóníska afbrigðið dregið út SERVER-SIDE (U1)."""
    import psycopg2
    import psycopg2.extras
    dsn = open(DBCFG, encoding="utf-8-sig").read().strip()
    conn = psycopg2.connect(dsn)
    conn.set_session(readonly=True, autocommit=False)
    cur = conn.cursor(name="cc111_kanon", cursor_factory=psycopg2.extras.DictCursor)
    cur.itersize = 500
    t0 = time.monotonic()
    cur.execute(KANON_SQL, (lindir,))
    n = 0
    try:
        for row in cur:
            n += 1
            yield (row["listing_id"], row["source"], row["source_listing_id"],
                   row["fastnum"], row["status"],
                   [(int(a), b) for a, b in row["slodir"]])
    finally:
        cur.close()
        conn.close()
        log(f"  lesnar {n:,} auglýsingar úr scraper.listings (read-only, "
            f"{time.monotonic()-t0:.0f}s)")


def pj_sha(slodir: list[tuple[int, str]]) -> str:
    return hashlib.sha256(
        "\n".join(f"{nr}\t{url}" for nr, url in sorted(slodir)).encode("utf-8")).hexdigest()


def ma_reyna(r: sqlite3.Row | None, nuna: datetime) -> tuple[bool, str]:
    if r is None:
        return True, ""
    if r["sokn_stada"] == "sott" and r["sha256"]:
        return False, "thegar_sott"
    if r["http_kodi"] == 404:
        return False, "404_endanlegt"
    if (r["n_tilraunir"] or 0) >= ENDURTILRAUN_HAMARK:
        return False, "tilraunathak"
    if r["sott_kl"]:
        try:
            s = datetime.fromisoformat(str(r["sott_kl"]).replace("Z", "+00:00"))
            if s.tzinfo is None:
                s = s.replace(tzinfo=timezone.utc)
            if (nuna - s).days < ENDURTILRAUN_BIL_D:
                return False, "bidtimi_7d"
        except Exception:
            pass
    return True, ""


def velja_framvirkt(db, lindir, nyjustu, log):
    """Forgangsröð skv. manifest-drögum §2:
       1 active m/ófulla þekju · 2 active m/breytt photos_json_sha · 3 withdrawn."""
    nuna = nu()
    verk: list[Verk] = []
    augl: dict[tuple[str, str], dict] = {}
    tal = {"n_augl": 0, "n_augl_m_slodir": 0, "n_augl_breytt": 0,
           "f1_active_ofull": 0, "f2_active_breytt": 0, "f3_withdrawn": 0,
           "sleppt_endurtilraunaregla": 0, "augl_thegar_heil": 0}

    raw = []
    for lid, lind, sll, fastnum, status, slodir in lesa_auglysingar(lindir, log):
        tal["n_augl"] += 1
        if slodir:
            tal["n_augl_m_slodir"] += 1
            raw.append((lid, lind, sll, fastnum, status, slodir))

    if nyjustu:
        raw.sort(key=lambda t: t[0], reverse=True)
        raw = raw[:nyjustu]
        log(f"  --nyjustu {nyjustu}: takmarkað við {len(raw):,} auglýsingar "
            f"(listing_id {raw[-1][0]}..{raw[0][0]})")

    wm = {(r["lind"], r["source_listing_id"]): r
          for r in db.execute("SELECT * FROM vatnsmerki")}

    for lid, lind, sll, fastnum, status, slodir in raw:
        sha_nu = pj_sha(slodir)
        w = wm.get((lind, sll))
        breytt = (w is None) or (w["photos_json_sha"] != sha_nu)
        if breytt:
            tal["n_augl_breytt"] += 1
        vantar = []
        for nr, url in slodir:
            r = db.execute("SELECT * FROM slod WHERE url=?", (url,)).fetchone()
            ok, _ = ma_reyna(r, nuna)
            if ok:
                vantar.append((nr, url))
            elif r is not None and r["sokn_stada"] != "sott":
                tal["sleppt_endurtilraunaregla"] += 1
        if not vantar:
            tal["augl_thegar_heil"] += 1
            continue
        if status == "active":
            f, lykill = (2, "f2_active_breytt") if breytt else (1, "f1_active_ofull")
        else:
            f, lykill = 3, "f3_withdrawn"
        tal[lykill] += len(vantar)
        augl[(lind, sll)] = {"sha": sha_nu, "n_slod_alls": len(slodir),
                             "n_valin": len(vantar)}
        for nr, url in vantar:
            verk.append(Verk(lind, sll, nr, AFBRIGDI[lind], url, lid, fastnum, f))

    verk.sort(key=lambda v: (v.forgangur, v.lind, v.sll, v.image_nr))
    return verk, tal, augl


def velja_bakfylling(db, lindir, log):
    """Bakfylling af cc109-listanum, auðguð með lifandi (sll, image_nr) úr
    scraper.listings. Slóð sem engin lifandi auglýsing ber lengur fær
    sll='__horfin__' — hún tapast ekki, en hún færir ekkert vatnsmerki."""
    if not CC109_GAT.exists():
        raise SystemExit(f"cc109-listinn finnst ekki: {CC109_GAT}")
    nuna = nu()
    gat: dict[str, str] = {}
    with open(CC109_GAT, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["source"] in lindir:
                gat[row["url"]] = row["source"]
    log(f"  cc109-gat: {len(gat):,} slóðir")

    url2verk: dict[str, Verk] = {}
    augl: dict[tuple[str, str], dict] = {}
    n_augl = 0
    for lid, lind, sll, fastnum, status, slodir in lesa_auglysingar(lindir, log):
        n_augl += 1
        if not slodir:
            continue
        sha_nu = pj_sha(slodir)
        n_hitt = 0
        for nr, url in slodir:
            if url in gat and url not in url2verk:
                url2verk[url] = Verk(lind, sll, nr, AFBRIGDI[lind], url, lid, fastnum,
                                     1 if status == "active" else 3)
                n_hitt += 1
        if n_hitt:
            augl[(lind, sll)] = {"sha": sha_nu, "n_slod_alls": len(slodir),
                                 "n_valin": 0}

    tal = {"n_gat": len(gat), "n_augl": n_augl, "n_porud_vid_lifandi_augl": len(url2verk),
           "n_munadarlausar_slodir": 0, "sleppt_endurtilraunaregla": 0}
    verk: list[Verk] = []
    for url, lind in gat.items():
        r = db.execute("SELECT * FROM slod WHERE url=?", (url,)).fetchone()
        ok, _ = ma_reyna(r, nuna)
        if not ok:
            tal["sleppt_endurtilraunaregla"] += 1
            continue
        v = url2verk.get(url)
        if v is None:
            tal["n_munadarlausar_slodir"] += 1
            v = Verk(lind, "__horfin__", 0, AFBRIGDI[lind], url, None, None, 4)
        else:
            augl[(v.lind, v.sll)]["n_valin"] += 1
        verk.append(v)

    augl = {k: d for k, d in augl.items() if d["n_valin"] > 0}
    verk.sort(key=lambda v: (v.forgangur, v.lind, v.sll, v.image_nr))
    return verk, tal, augl


# ============================================================================= sókn
class Saekjari:
    def __init__(self):
        from curl_cffi import requests as rq
        self.rq = rq
        # cc109 §3.1 mældi ENGAR client-kröfur; hausarnir eru kurteisi, ekki nauðsyn.
        self.hausar = {"Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}

    def saekja(self, v: Verk) -> dict:
        t0 = time.monotonic()
        try:
            r = self.rq.get(v.url, impersonate="chrome", timeout=30,
                            allow_redirects=True, headers=self.hausar)
            ms = (time.monotonic() - t0) * 1000
            ct = (r.headers.get("content-type", "") or "").split(";")[0].strip().lower()
            if r.status_code == 200 and r.content and ct.startswith("image/"):
                return {"v": v, "ok": True, "kodi": 200, "ct": ct, "data": r.content, "ms": ms}
            return {"v": v, "ok": False, "kodi": r.status_code, "ct": ct, "data": None,
                    "ms": ms, "ath": f"http:{r.status_code} ct:{ct}"}
        except Exception as e:
            return {"v": v, "ok": False, "kodi": None, "ct": None, "data": None,
                    "ms": (time.monotonic() - t0) * 1000,
                    "ath": f"err:{type(e).__name__}:{str(e)[:120]}"}


# ============================================================================= R2
def _r2_afangi(undir: str = "") -> str:
    """HARÐA REGLAN (cc97): áfangi verður alltaf að byrja á `augl-myndir`."""
    slod = f"{R2_FORSKEYTI}/{undir}".rstrip("/")
    if not slod.startswith(R2_FORSKEYTI):
        raise SystemExit(f"NEITA: áfangaforskeyti byrjar ekki á {R2_FORSKEYTI!r}: {slod!r}")
    return f"{R2_REMOTE}/{slod}"


def _r2_manifest_afangi() -> str:
    """HARÐA REGLAN, önnur útgáfa: manifest-spegillinn má aldrei lenda undir
    myndaforskeytunum. `sync` er hvergi notað — aðeins `copy`."""
    if not MANIFEST_R2.startswith("myndamanifest"):
        raise SystemExit(f"NEITA: manifest-forskeyti rangt: {MANIFEST_R2!r}")
    if MANIFEST_R2.startswith(("myndir", "augl-myndir", "current", "archive")):
        raise SystemExit(f"NEITA: manifest-forskeyti skarast við myndarými: {MANIFEST_R2!r}")
    return f"{R2_REMOTE}/{MANIFEST_R2}"


def _sia() -> list[str]:
    ut = []
    for u in MANIFEST_UTILOKANIR:
        ut += ["--exclude", u]
    return ut


def spegla_manifest(log: Log, merki: str = "") -> dict:
    """cc111 liður 0 — speglar kortlagninguna á R2 og SANNPRÓFAR með `rclone size`
    BÁÐUM MEGIN. Kortlagningin má aldrei standa á einum stað þegar hrina lýkur."""
    afangi = _r2_manifest_afangi()
    t0 = time.monotonic()
    p = subprocess.run(
        [str(RCLONE), "copy", str(MANIFEST_ROT), afangi, "--config", str(RCLONE_CONF),
         *_sia(), "--transfers", "8", "--checkers", "8", "--stats-one-line"],
        capture_output=True, text=True, timeout=3600)
    t_copy = time.monotonic() - t0

    def staerd(mid: list[str]) -> tuple[int, int]:
        q = subprocess.run([str(RCLONE), "size", *mid, "--config", str(RCLONE_CONF),
                            "--json"], capture_output=True, text=True, timeout=1800)
        if q.returncode != 0:
            raise RuntimeError(f"rclone size féll: {q.stderr[:300]}")
        d = json.loads(q.stdout)
        return int(d["count"]), int(d["bytes"])

    lc, lb = staerd([str(MANIFEST_ROT), *_sia()])     # D: með SÖMU síu
    rc, rb = staerd([afangi + "/", "--fast-list"])    # R2
    jafn = (lc == rc and lb == rb)
    d = {"copy_exit": p.returncode, "copy_sek": round(t_copy, 1),
         "disk_skrar": lc, "disk_baeti": lb, "r2_skrar": rc, "r2_baeti": rb,
         "jafna_manifest": jafn}
    if p.returncode != 0:
        log(f"  !! manifest-copy exit={p.returncode}: {p.stderr[-300:]}")
    log(f"  manifest-spegill{merki}: D: {lc} skrár / {lb:,} b  ==  "
        f"R2 {rc} skrár / {rb:,} b  ->  {'JAFNT' if jafn else 'ÓJAFNT <<<'}  "
        f"({t_copy:.1f}s)")
    with open(MANIFEST_ROT / "manifest_spegill.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": nu_s(), "merki": merki, **d}, ensure_ascii=False) + "\n")
    return d


def r2_staerd(forskeyti: str) -> tuple[int, int]:
    p = subprocess.run(
        [str(RCLONE), "size", f"{R2_REMOTE}/{forskeyti}/", "--config", str(RCLONE_CONF),
         "--fast-list", "--json"], capture_output=True, text=True, timeout=3600)
    if p.returncode != 0:
        raise RuntimeError(f"rclone size féll á {forskeyti}: {p.stderr[:300]}")
    d = json.loads(p.stdout)
    return int(d["count"]), int(d["bytes"])


def r2_maeling() -> dict:
    m = {}
    m["augl_hlutir"], m["augl_baeti"] = r2_staerd(R2_FORSKEYTI)
    for f in AFRIT_FORSK:                      # næturafritið mælt í BÁÐUM endum (cc97)
        m[f"afrit_{f}_hlutir"], m[f"afrit_{f}_baeti"] = r2_staerd(f)
    return m


def spegla_hrinu(skrar: list[str], log: Log, tmpdir: Path) -> dict:
    """U4: copy + tæmandi `--checksum` check á NÁKVÆMLEGA skrám þessarar hrinu.
    Ekkert úrtak: `--files-from` telur 100% hlutanna sem hrinan bjó til (9%-reglan)."""
    tom = {"copy_exit": 0, "check_exit": 0, "check_matching": 0, "check_differences": 0,
           "copy_sek": 0.0, "check_sek": 0.0, "n_skrar": 0}
    if not skrar:
        return tom
    ff = tmpdir / "files_from.txt"
    ff.write_text("\n".join(skrar) + "\n", encoding="utf-8")
    afangi = _r2_afangi()

    t0 = time.monotonic()
    p1 = subprocess.run(
        [str(RCLONE), "copy", str(STORE), afangi, "--config", str(RCLONE_CONF),
         "--files-from", str(ff), "--transfers", "16", "--checkers", "16",
         "--no-traverse", "--stats-one-line"],
        capture_output=True, text=True, timeout=14400)
    t_copy = time.monotonic() - t0

    t0 = time.monotonic()
    p2 = subprocess.run(
        [str(RCLONE), "check", str(STORE), afangi, "--config", str(RCLONE_CONF),
         "--files-from", str(ff), "--checksum", "--checkers", "32"],
        capture_output=True, text=True, timeout=14400)
    t_check = time.monotonic() - t0

    txt = (p2.stderr or "") + "\n" + (p2.stdout or "")
    md, mm = RE_DIFF.search(txt), RE_MATCH.search(txt)
    differences = int(md.group(1)) if md else (0 if p2.returncode == 0 else -1)
    matching = int(mm.group(1)) if mm else (len(skrar) if p2.returncode == 0 else -1)

    if p1.returncode != 0:
        log(f"  !! rclone copy exit={p1.returncode}: {p1.stderr[-400:]}")
    if p2.returncode != 0:
        log(f"  !! rclone check exit={p2.returncode}: {p2.stderr[-400:]}")
    return {"copy_exit": p1.returncode, "check_exit": p2.returncode,
            "check_matching": matching, "check_differences": differences,
            "copy_sek": round(t_copy, 1), "check_sek": round(t_check, 1),
            "n_skrar": len(skrar)}


# ============================================================================= keyrsla
class Keyrsla:
    def __init__(self, a, log: Log, db: sqlite3.Connection):
        self.a, self.log, self.db = a, log, db
        self.run_id = nu().strftime("%Y%m%dT%H%M%SZ")
        self.byrjad = nu_s()
        self.manifest_dir = MANIFEST_ROT / "manifest"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.tmp = MANIFEST_ROT / "tmp"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.saekjari = Saekjari()
        self.n = {"sott": 0, "tvitak": 0, "tynt": 0, "sleppt": 0,
                  "manifest": 0, "baeti_ny": 0, "put": 0}
        self.hrinur: list[dict] = []
        self.threp_bok: list[dict] = []
        self.n_afgreidd = 0        # verk uppgerð í þessari keyrslu (þökin mælast á þessu)
        self.baeti_afgreidd = 0    # ný bæti uppgerð í þessari keyrslu
        self.url_kesja: dict[str, dict] = {}     # slóð -> niðurstaða, EIN sókn per keyrslu
        self.grunn_afkost: float | None = None   # afköst/þráð við 1 þráð (U3-grunnur)
        self.hamark_stig: int | None = None      # pinnað eftir fyrsta frávik
        self.hofnun_texti: str | None = None     # öryggisnetið (keyrsla 3)
        self.t0 = time.monotonic()

    # ---------------------------------------------------------------- stöðvun
    # Þökin eru mæld á AFGREIDDU verki (þrepgranularitet), ekki á bókuðu verki
    # (hrinugranularitet). Annars hleypur hrinustærðin fram úr þakinu: 2 GiB af
    # myigloo er ~1.400 myndir og `--thak-myndir 400` yrði marklaust.
    def stodvun(self) -> str | None:
        if KILL_SWITCH.exists():
            return "kill_switch"
        if self.a.thak_myndir and self.n_afgreidd >= self.a.thak_myndir:
            return "thak_myndir"
        if self.a.thak_gib and self.baeti_afgreidd >= self.a.thak_gib * 1024 ** 3:
            return "thak_gib"
        if self.a.thak_min and (time.monotonic() - self.t0) / 60 >= self.a.thak_min:
            return "thak_min"
        return None

    def eftirstodvar_thaks(self) -> int | None:
        """Hve mörg verk má enn afgreiða áður en myndaþakinu er náð."""
        if not self.a.thak_myndir:
            return None
        return max(0, self.a.thak_myndir - self.n_afgreidd)

    # ---------------------------------------------------------------- þrep
    def keyra_threp(self, verk: list[Verk], thraedir: int) -> tuple[dict, list[dict]]:
        """Ein slóð er sótt Í MESTA LAGI EINU SINNI í keyrslunni, en hún gefur
        manifest-röð fyrir HVERT (auglýsing, image_nr) sem ber hana. mbl
        endurnýtir fs-pool: 214.718 slot standa á 101.390 einstökum slóðum."""
        t0 = time.monotonic()
        m = {"thraedir": thraedir, "n": len(verk), "kodar": {}, "n_200": 0, "n_404": 0,
             "n_5xx": 0, "n_villa": 0, "n_tvitak_an_beidni": 0,
             "n_endurtekin_slod": 0, "baeti": 0}
        ms: list[float] = []
        nidur: list[dict] = []

        def ur_kesju(v: Verk, c: dict) -> dict:
            return {"v": v, "stada": ("tvitak" if c["sha"] else "tynt"),
                    "sha": c["sha"], "blen": c["blen"], "ct": c.get("ct"),
                    "kodi": c.get("kodi"), "ny": False, "w": c.get("w"), "h": c.get("h"),
                    "ending": c.get("ending"), "ath": c.get("ath")}

        # 1) slóðir sem eru ÞEGAR uppgerðar: í þessari keyrslu eða í vísinum
        saekja_url: dict[str, Verk] = {}       # einstakar slóðir sem þarf raunverulega
        bid: list[Verk] = []                   # verk sem bíða niðurstöðu þeirra
        for v in verk:
            c = self.url_kesja.get(v.url)
            if c is not None:
                nidur.append(ur_kesju(v, c))
                m["n_endurtekin_slod"] += 1
                continue
            r = self.db.execute("SELECT * FROM slod WHERE url=?", (v.url,)).fetchone()
            if r is not None and r["sokn_stada"] == "sott" and r["sha256"]:
                g = self.db.execute("SELECT * FROM sha_geymd WHERE sha256=?",
                                    (r["sha256"],)).fetchone()
                if g is not None and g["a_r2"] == 1:
                    c = {"sha": r["sha256"], "blen": r["byte_len"], "ct": None,
                         "kodi": None, "w": None, "h": None, "ending": g["ending"],
                         "ath": None}
                    self.url_kesja[v.url] = c
                    nidur.append(ur_kesju(v, c))
                    m["n_tvitak_an_beidni"] += 1
                    continue
            if v.url in saekja_url:
                bid.append(v)                  # sama slóð tvisvar innan þrepsins
            else:
                saekja_url[v.url] = v

        # 2) raunveruleg sókn með bundnu flugi (minnisþak ~ thraedir*3 myndir)
        if saekja_url:
            with ThreadPoolExecutor(max_workers=thraedir) as ex:
                it, flug, buid = iter(saekja_url.values()), [], False
                gluggi = max(thraedir * 3, 2)
                while True:
                    while not buid and len(flug) < gluggi:
                        try:
                            flug.append(ex.submit(self.saekjari.saekja, next(it)))
                        except StopIteration:
                            buid = True
                    if not flug:
                        break
                    self._taka_vid(flug.pop(0).result(), m, ms, nidur)

        # 3) systkinaslot sömu slóðar fá sína manifest-röð án nýrrar beiðni
        for v in bid:
            c = self.url_kesja.get(v.url)
            if c is None:
                continue
            nidur.append(ur_kesju(v, c))
            m["n_endurtekin_slod"] += 1

        sek = time.monotonic() - t0
        m["sek"] = round(sek, 2)
        m["mynd_s"] = round(m["n"] / sek, 2) if sek > 0 else 0.0
        # afköst/þráð mæld á RAUNBEIÐNUM einum — tvítök án beiðni menga ekki mælinguna
        n_beidnir = len(saekja_url)
        m["n_beidnir"] = n_beidnir
        m["beidnir_s"] = round(n_beidnir / sek, 2) if sek > 0 else 0.0
        m["beidnir_s_thrad"] = round(m["beidnir_s"] / thraedir, 3) if thraedir else 0.0
        m["mid_ms"] = round(sorted(ms)[len(ms) // 2]) if ms else None
        m["p95_ms"] = round(sorted(ms)[int(len(ms) * 0.95)]) if ms else None
        m["villuhlutfall"] = round((m["n_villa"] + m["n_5xx"]) / n_beidnir, 4) if n_beidnir else 0.0
        return m, nidur

    def _taka_vid(self, r: dict, m: dict, ms: list, nidur: list) -> None:
        v = r["v"]
        ms.append(r["ms"])
        kodi = r["kodi"]
        m["kodar"][str(kodi)] = m["kodar"].get(str(kodi), 0) + 1
        if r["ok"]:
            m["n_200"] += 1
            data = r["data"]
            sha = hashlib.sha256(data).hexdigest()
            ext = CT_EXT.get(r["ct"]) or os.path.splitext(v.url.split("?")[0])[1].lower()
            if ext not in LOGLEG_ENDING:
                ext = ".jpg"
            g = self.db.execute("SELECT * FROM sha_geymd WHERE sha256=?", (sha,)).fetchone()
            ny = not (g is not None and g["a_r2"] == 1)
            if g is not None and g["ending"]:
                ext = g["ending"]                 # halda lykli sem þegar er til
            path = STORE / v.lind / sha[:2] / f"{sha}{ext}"
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_name(path.name + ".part")
                with open(tmp, "wb") as fh:
                    fh.write(data)
                os.replace(tmp, path)
            w, h = maelingar(data)
            m["baeti"] += len(data)
            self.url_kesja[v.url] = {"sha": sha, "blen": len(data), "ct": r["ct"],
                                     "kodi": 200, "w": w, "h": h, "ending": ext,
                                     "ath": None}
            nidur.append({"v": v, "stada": "sott" if ny else "tvitak", "sha": sha,
                          "blen": len(data), "ct": r["ct"], "kodi": 200, "ny": ny,
                          "w": w, "h": h, "ending": ext, "ath": None})
        else:
            if kodi == 404:
                m["n_404"] += 1
            elif kodi is not None and 500 <= kodi < 600:
                m["n_5xx"] += 1
            else:
                m["n_villa"] += 1
            self.url_kesja[v.url] = {"sha": None, "blen": None, "ct": r.get("ct"),
                                     "kodi": kodi, "w": None, "h": None,
                                     "ending": None, "ath": r.get("ath")}
            nidur.append({"v": v, "stada": "tynt", "sha": None, "blen": None,
                          "ct": r.get("ct"), "kodi": kodi, "ny": False, "w": None,
                          "h": None, "ending": None, "ath": r.get("ath")})

    # ---------------------------------------------------------------- U3 stigun
    def fravik(self, m: dict) -> str | None:
        k = m["kodar"]
        if k.get("429") or k.get("403"):
            return f"höfnun 429/403 ({k.get('429', 0)}/{k.get('403', 0)})"
        if m["n_5xx"] >= FRAVIK_5XX:
            return f"5xx-hrina ({m['n_5xx']})"
        if m["villuhlutfall"] > FRAVIK_VILLUHLUTFALL:
            return f"villuhlutfall {m['villuhlutfall']:.2%} > {FRAVIK_VILLUHLUTFALL:.0%}"
        if self.grunn_afkost and m["n_beidnir"] >= 20 and \
                m["beidnir_s_thrad"] < self.grunn_afkost * FRAVIK_HRADAFALL:
            return (f"hraðafall {m['beidnir_s_thrad']:.3f}/þráð < {FRAVIK_HRADAFALL:.0%} "
                    f"af grunni {self.grunn_afkost:.3f}")
        return None

    def hord_hofnun(self, m: dict) -> str | None:
        """ÖRYGGISNET sem virkar ÓHÁÐ `--stigun` (cc111 keyrsla 3).
        Ber EKKI hraðafallsregluna — borðið dæmdi 20%-mörkin of næm fyrir mbl.
        Hér er aðeins spurt hvort lindin sé raunverulega að HAFNA okkur."""
        k = m["kodar"]
        if k.get("429") or k.get("403"):
            return f"höfnun 429/403 ({k.get('429', 0)}/{k.get('403', 0)})"
        if m["n_5xx"] >= FRAVIK_5XX:
            return f"5xx-hrina ({m['n_5xx']} í einu þrepi)"
        if m["villuhlutfall"] > FRAVIK_VILLUHLUTFALL:
            return f"villuhlutfall {m['villuhlutfall']:.2%} > {FRAVIK_VILLUHLUTFALL:.0%}"
        return None

    def naesta_stig(self, stig_nu: int, m: dict) -> int:
        fr = self.fravik(m)
        if fr:
            nytt = STIG[max(0, STIG.index(stig_nu) - 1)]
            self.hamark_stig = nytt
            self.log(f"  *** FRÁVIK á {stig_nu} þráðum: {fr}  ->  falla í {nytt} "
                     f"og HALDA þar út keyrsluna (aldrei hækkað aftur)")
            return nytt
        if self.hamark_stig is not None:
            return min(stig_nu, self.hamark_stig)
        return STIG[min(len(STIG) - 1, STIG.index(stig_nu) + 1)]

    # ---------------------------------------------------------------- hrina
    def loka_hrinu(self, hrina_id: str, nidur: list, fyrir: dict) -> dict:
        skrar, ny_sha, ny_baeti = [], set(), 0
        n_st = {"sott": 0, "tvitak": 0, "tynt": 0, "sleppt": 0}
        linur = []
        for d in nidur:
            v = d["v"]
            n_st[d["stada"]] += 1
            if d["stada"] == "sott" and d["sha"] not in ny_sha:
                ny_sha.add(d["sha"])
                ny_baeti += d["blen"]
                skrar.append(f"{v.lind}/{d['sha'][:2]}/{d['sha']}{d['ending']}")
            r2l = (f"{R2_FORSKEYTI}/{v.lind}/{d['sha'][:2]}/{d['sha']}{d['ending']}"
                   if d["sha"] else None)
            linur.append({
                "lind": v.lind, "source_listing_id": v.sll, "image_nr": v.image_nr,
                "afbrigdi": v.afbrigdi, "listing_id": v.listing_id, "fastnum": v.fastnum,
                "url_sott": v.url, "sha256": d["sha"], "byte_len": d["blen"],
                "content_type": d.get("ct"), "ending": d.get("ending"), "r2_lykill": r2l,
                "breidd": d.get("w"), "haed": d.get("h"), "sokn_stada": d["stada"],
                "http_kodi": d.get("kodi"), "sott_kl": nu_s(), "hrina_id": hrina_id,
                "athugasemd": d.get("ath")})

        sp = spegla_hrinu(skrar, self.log, self.tmp)     # U4: speglun INNAN hrinunnar
        eftir = r2_maeling()

        d_hlutir = eftir["augl_hlutir"] - fyrir["augl_hlutir"]
        d_baeti = eftir["augl_baeti"] - fyrir["augl_baeti"]
        j1 = len(linur) == sum(n_st.values())
        j2 = d_hlutir == len(ny_sha)
        j3 = d_baeti == ny_baeti
        j4 = (sp["copy_exit"] == 0 and sp["check_exit"] == 0
              and sp["check_differences"] == 0 and sp["check_matching"] == len(skrar))

        mf = self.manifest_dir / f"{hrina_id}.jsonl"
        with open(mf, "w", encoding="utf-8") as fh:
            for ln in linur:
                fh.write(json.dumps(ln, ensure_ascii=False) + "\n")

        # FIMMTA JAFNAN (cc111 liður 0): kortlagningin speglast áður en hrinan
        # telst HEIL. Manifest-skráin er þegar rituð, svo hún fer með.
        msp = spegla_manifest(self.log, f" [{hrina_id}]")
        j5 = bool(msp["jafna_manifest"]) and msp["copy_exit"] == 0

        heil = j1 and j2 and j3 and j4 and j5
        if heil:
            self._bokfaera_i_visi(nidur)

        bok = {"hrina_id": hrina_id, "run_id": self.run_id, "ts": nu_s(),
               "n_manifest": len(linur), "n_sott": n_st["sott"], "n_tvitak": n_st["tvitak"],
               "n_tynt": n_st["tynt"], "n_sleppt": n_st["sleppt"],
               "n_einstok_ny_sha": len(ny_sha), "baeti_ny_sha": ny_baeti,
               "r2_hlutir_fyrir": fyrir["augl_hlutir"], "r2_hlutir_eftir": eftir["augl_hlutir"],
               "r2_baeti_fyrir": fyrir["augl_baeti"], "r2_baeti_eftir": eftir["augl_baeti"],
               "afrit_hlutir_fyrir": fyrir["afrit_current_hlutir"] + fyrir["afrit_archive_hlutir"],
               "afrit_hlutir_eftir": eftir["afrit_current_hlutir"] + eftir["afrit_archive_hlutir"],
               "afrit_baeti_fyrir": fyrir["afrit_current_baeti"] + fyrir["afrit_archive_baeti"],
               "afrit_baeti_eftir": eftir["afrit_current_baeti"] + eftir["afrit_archive_baeti"],
               **sp, "jafna_fjoldi": j1, "jafna_hlutir": j2, "jafna_baeti": j3,
               "jafna_spegill": j4, "jafna_manifest_spegill": j5,
               "manifest_spegill": msp,
               "stada": "HEIL" if heil else "OLOKIN", "manifest_skra": str(mf)}
        with open(HRINUR_JL, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(bok, ensure_ascii=False) + "\n")

        self.log(f"  hrina {hrina_id}: {'HEIL' if heil else 'OLOKIN  <<< JÖFNUÐUR BRAST'}"
                 f"  manifest={len(linur)} sott={n_st['sott']} tvitak={n_st['tvitak']} "
                 f"tynt={n_st['tynt']} | ný_sha={len(ny_sha)} vs +{d_hlutir} hlutir | "
                 f"{ny_baeti/1048576:.1f} MiB vs +{d_baeti/1048576:.1f} MiB | "
                 f"copy={sp['copy_sek']}s check={sp['check_sek']}s diff={sp['check_differences']}")
        if not heil:
            self.log(f"     jöfnur: fjöldi={j1} hlutir={j2} bæti={j3} spegill={j4} "
                     f"manifest_spegill={j5}")
        self.hrinur.append(bok)
        for k in n_st:
            self.n[k] += n_st[k]
        self.n["manifest"] += len(linur)
        self.n["baeti_ny"] += ny_baeti
        self.n["put"] += len(ny_sha)
        return bok

    def _bokfaera_i_visi(self, nidur: list) -> None:
        for d in nidur:
            v = d["v"]
            if d["stada"] in ("sott", "tvitak"):
                self.db.execute(
                    """INSERT INTO sha_geymd(sha256,lind,ending,byte_len,a_disk,a_r2)
                       VALUES(?,?,?,?,1,1)
                       ON CONFLICT(sha256) DO UPDATE SET a_disk=1, a_r2=1""",
                    (d["sha"], v.lind, d["ending"], d["blen"]))
                self.db.execute(
                    """INSERT INTO slod(url,lind,sha256,byte_len,sokn_stada,http_kodi,
                                        sott_kl,n_tilraunir)
                       VALUES(?,?,?,?,'sott',?,?,1)
                       ON CONFLICT(url) DO UPDATE SET sha256=excluded.sha256,
                         byte_len=excluded.byte_len, sokn_stada='sott',
                         http_kodi=excluded.http_kodi, sott_kl=excluded.sott_kl,
                         n_tilraunir=slod.n_tilraunir+1""",
                    (v.url, v.lind, d["sha"], d["blen"], d.get("kodi"), nu_s()))
            elif d["stada"] == "tynt":
                self.db.execute(
                    """INSERT INTO slod(url,lind,sha256,byte_len,sokn_stada,http_kodi,
                                        sott_kl,n_tilraunir)
                       VALUES(?,?,NULL,NULL,'tynt',?,?,1)
                       ON CONFLICT(url) DO UPDATE SET sokn_stada='tynt',
                         http_kodi=excluded.http_kodi, sott_kl=excluded.sott_kl,
                         n_tilraunir=slod.n_tilraunir+1""",
                    (v.url, v.lind, d.get("kodi"), nu_s()))
        self.db.commit()

    def bokfaera_vatnsmerki(self, snert: dict, augl: dict) -> int:
        """Vatnsmerki færist AÐEINS fyrir auglýsingu sem var KLÁRUÐ í HEILRI hrinu.
        Ófullgerð auglýsing heldur gamla merkinu og verður endurvalin næst."""
        n = 0
        with open(WATERMARK_JL, "a", encoding="utf-8") as fh:
            for lykill, s in snert.items():
                meta = augl.get(lykill)
                if meta is None or s["n_lokid"] < meta["n_valin"]:
                    continue
                ln = {"lind": lykill[0], "source_listing_id": lykill[1],
                      "sidast_skodad_kl": nu_s(), "photos_json_sha": meta["sha"],
                      "n_slod": meta["n_slod_alls"], "n_sott": s["n_sott"],
                      "n_tynt": s["n_tynt"]}
                self.db.execute(
                    """INSERT INTO vatnsmerki(lind,source_listing_id,sidast_skodad_kl,
                              photos_json_sha,n_slod,n_sott,n_tynt,n_tilraunir)
                       VALUES(?,?,?,?,?,?,?,1)
                       ON CONFLICT(lind,source_listing_id) DO UPDATE SET
                         sidast_skodad_kl=excluded.sidast_skodad_kl,
                         photos_json_sha=excluded.photos_json_sha,
                         n_slod=excluded.n_slod, n_sott=excluded.n_sott,
                         n_tynt=excluded.n_tynt, n_tilraunir=vatnsmerki.n_tilraunir+1""",
                    (ln["lind"], ln["source_listing_id"], ln["sidast_skodad_kl"],
                     ln["photos_json_sha"], ln["n_slod"], ln["n_sott"], ln["n_tynt"]))
                fh.write(json.dumps(ln, ensure_ascii=False) + "\n")
                n += 1
        self.db.commit()
        return n


# ============================================================================= aðalflæði
def keyra(a, log: Log, db: sqlite3.Connection) -> int:
    K = Keyrsla(a, log, db)
    lindir = ["mbl", "myigloo"] if a.lind == "allar" else [a.lind]

    if KILL_SWITCH.exists():
        log(f"KILL-SWITCH virkur ({KILL_SWITCH}) — ekkert gert.")
        skrifa_stodu(K, a, "kill_switch_vid_raesingu", {}, 0)
        return 3

    log(f"=== myndasaekjari run_id={K.run_id} ham={a.ham} lindir={lindir} "
        f"afbrigdi={ {l: AFBRIGDI[l] for l in lindir} } ===")

    if a.ham == "framvirkt":
        verk, val_tal, augl = velja_framvirkt(db, lindir, a.nyjustu, log)
    else:
        verk, val_tal, augl = velja_bakfylling(db, lindir, log)
    log(f"  verkefnaval: {json.dumps(val_tal, ensure_ascii=False)}")
    log(f"  VALIN VERKEFNI: {len(verk):,}  (auglýsingar snertar: {len(augl):,})")

    if a.throka:
        log("  --throka: engin sókn framkvæmd.")
        skrifa_stodu(K, a, "throka", val_tal, len(verk))
        return 0
    if not verk:
        log("  ekkert að sækja.")
        skrifa_stodu(K, a, "ekkert_ad_saekja", val_tal, 0)
        return 0

    rod = sorted(lindir, key=lambda l: 0 if l == "myigloo" else 1)   # U3: myigloo fyrst
    log(f"  röð linda (U3): {rod}")

    haetta: str | None = None
    for lind in rod:
        vl = [v for v in verk if v.lind == lind]
        if not vl:
            continue
        stigun = a.stigun and lind == "mbl"
        stig = STIG[0] if stigun else (a.thraedir_mbl if lind == "mbl" else a.thraedir_myigloo)
        log(f"--- lind={lind}: {len(vl):,} verkefni · "
            f"{'STIGUN 1->2->4 (U3)' if stigun else f'{stig} þræðir fastir'} ---")

        i, hrina_nr = 0, 0
        hrina_nidur: list[dict] = []
        hrina_baeti = 0
        snert: dict = {}
        hrina_fyrir = r2_maeling()

        while i < len(vl):
            haetta = K.stodvun()
            if haetta:
                log(f"  STÖÐVUN: {haetta}")
            else:
                n_threp = a.threp_myndir
                eftir_thak = K.eftirstodvar_thaks()
                if eftir_thak is not None:
                    n_threp = min(n_threp, eftir_thak)
                threp = vl[i:i + n_threp]
                i += len(threp)
                m, nid = K.keyra_threp(threp, stig)
                K.n_afgreidd += len(nid)
                K.baeti_afgreidd += sum((d["blen"] or 0) for d in nid
                                        if d["stada"] == "sott" and d["ny"])
                m["lind"], m["threp_nr"] = lind, len(K.threp_bok) + 1
                K.threp_bok.append(m)
                log(f"  þrep {m['threp_nr']:>3} lind={lind} þræðir={stig} n={m['n']:>4} "
                    f"beiðnir={m['n_beidnir']:>4} {m['beidnir_s']:>6.2f} beiðnir/s "
                    f"({m['beidnir_s_thrad']:.3f}/þráð) mið={m['mid_ms']}ms "
                    f"p95={m['p95_ms']}ms kóðar={m['kodar']} "
                    f"villuhlutfall={m['villuhlutfall']:.2%} "
                    f"tvítök_án_beiðni={m['n_tvitak_an_beidni']} "
                    f"endurtekin_slóð={m['n_endurtekin_slod']}")

                hrina_nidur.extend(nid)
                hrina_baeti += sum((d["blen"] or 0) for d in nid if d["stada"] == "sott")
                for d in nid:
                    v = d["v"]
                    if v.sll == "__horfin__":
                        continue
                    s = snert.setdefault((v.lind, v.sll),
                                         {"n_lokid": 0, "n_sott": 0, "n_tynt": 0})
                    s["n_lokid"] += 1
                    if d["stada"] in ("sott", "tvitak"):
                        s["n_sott"] += 1
                    else:
                        s["n_tynt"] += 1

                # ÖRYGGISNET — gildir í BÁÐUM hömum, líka án --stigun.
                # "0 höfnanir hingað til" er forsenda; brotni hún er hún ekki forsenda.
                hh = K.hord_hofnun(m)
                if hh:
                    log(f"  *** HÖFNUN Á {stig} ÞRÁÐUM: {hh}")
                    log(f"      -> STÖÐVA STRAX. Ráðlögð stilling næstu keyrslu: 2 þræðir.")
                    K.hamark_stig = 2
                    K.hofnun_texti = hh
                    haetta = "hofnun_stodvun"
                elif stigun:
                    if stig == 1 and K.grunn_afkost is None and m["n_beidnir"] >= 20:
                        K.grunn_afkost = m["beidnir_s_thrad"]
                        log(f"  grunnafköst (1 þráður): {K.grunn_afkost:.3f} beiðnir/s/þráð")
                    stig = K.naesta_stig(stig, m)

            # hrinu-lok: bætaþak EÐA fjöldaþak EÐA búið EÐA stöðvun
            if hrina_nidur and (hrina_baeti >= a.hrina_gib * 1024 ** 3
                                or len(hrina_nidur) >= a.hrina_myndir
                                or i >= len(vl) or haetta):
                hrina_nr += 1
                bok = K.loka_hrinu(f"{K.run_id}_{lind}_{hrina_nr:03d}",
                                   hrina_nidur, hrina_fyrir)
                if bok["stada"] != "HEIL":
                    log("  HALT: jöfnuður brast — hætti.")
                    haetta = "jofnudur_brast"
                    break
                nw = K.bokfaera_vatnsmerki(snert, augl)
                log(f"  vatnsmerki færð: {nw}")
                # vatnsmerkin voru rituð EFTIR hrinuspeglunina — lokahnykkur svo
                # ekkert af kortlagningunni standi á einum stað þegar hrinan lýkur.
                msp2 = spegla_manifest(log, " [lokahnykkur]")
                if not msp2["jafna_manifest"] or msp2["copy_exit"] != 0:
                    log("  HALT: manifest-spegill ójafn eftir vatnsmerki.")
                    haetta = "manifest_spegill_ojafn"
                    break
                hrina_nidur, hrina_baeti, snert = [], 0, {}
                if i < len(vl) and not haetta:
                    hrina_fyrir = r2_maeling()
            if haetta:
                break
        if haetta:
            break

    astaeda = haetta or "kladhr"
    skrifa_stodu(K, a, astaeda, val_tal, len(verk))
    olokin = sum(1 for h in K.hrinur if h["stada"] != "HEIL")
    log(f"=== LOKIÐ ham={a.ham} ástæða={astaeda} · manifest={K.n['manifest']:,} "
        f"sott={K.n['sott']:,} tvitak={K.n['tvitak']:,} tynt={K.n['tynt']:,} · "
        f"PUT={K.n['put']:,} · ný_bæti={K.n['baeti_ny']/1048576:.1f} MiB · "
        f"hrinur={len(K.hrinur)} ({olokin} ÓLOKNAR) ===")
    if olokin or astaeda in ("jofnudur_brast", "manifest_spegill_ojafn",
                             "hofnun_stodvun"):
        return 2
    if astaeda == "kill_switch":
        return 3
    return 0


def skrifa_stodu(K: Keyrsla, a, astaeda: str, val_tal: dict, n_valin: int) -> None:
    lindir = ["mbl", "myigloo"] if a.lind == "allar" else [a.lind]
    d = {"run_id": K.run_id, "ham": a.ham, "lind": a.lind,
         "afbrigdi": {l: AFBRIGDI[l] for l in lindir},
         "byrjad": K.byrjad, "endad": nu_s(), "sek": round(time.monotonic() - K.t0, 1),
         "haetta_astaeda": astaeda, "verkefnaval": val_tal, "n_verkefni_valin": n_valin,
         "n_manifest_radir": K.n["manifest"], "n_sott": K.n["sott"],
         "n_tvitak": K.n["tvitak"], "n_tynt": K.n["tynt"], "n_sleppt": K.n["sleppt"],
         "n_put": K.n["put"], "baeti_ny": K.n["baeti_ny"],
         "n_hrinur": len(K.hrinur),
         "n_hrinur_heil": sum(1 for h in K.hrinur if h["stada"] == "HEIL"),
         "n_hrinur_olokin": sum(1 for h in K.hrinur if h["stada"] != "HEIL"),
         "jofnudur_allur_ok": all(h["stada"] == "HEIL" for h in K.hrinur),
         "hamark_stig_pinnad": K.hamark_stig, "grunn_afkost": K.grunn_afkost,
         "hofnun": K.hofnun_texti,
         "thok": {"myndir": a.thak_myndir, "gib": a.thak_gib, "min": a.thak_min},
         "threp": K.threp_bok, "hrinur": K.hrinur}
    txt = json.dumps(d, ensure_ascii=False, indent=1)
    STADA_JSON.write_text(txt, encoding="utf-8")
    (MANIFEST_ROT / "keyrslur").mkdir(exist_ok=True)
    (MANIFEST_ROT / "keyrslur" / f"stada_{K.run_id}.json").write_text(txt, encoding="utf-8")


# ============================================================================= validator
def stadfesta(log: Log) -> int:
    import jsonschema
    skema_p = next((p for p in SKEMA_LEIDIR if p.exists()), None)
    if skema_p is None:
        log("NEITA: cc109-skemadrögin finnast hvergi: "
            + " | ".join(str(p) for p in SKEMA_LEIDIR))
        return 1
    log(f"skema: {skema_p}")
    skema = json.loads(skema_p.read_text(encoding="utf-8"))
    lina_skema = {k: v for k, v in skema.items()
                  if not k.startswith("$maelt") and k != "$defs"}
    V = jsonschema.Draft202012Validator(lina_skema)

    n = n_villa = arekstrar = 0
    lyklar: dict[tuple, str] = {}
    stodur: dict[str, int] = {}
    villur: list[str] = []
    skrar = sorted((MANIFEST_ROT / "manifest").glob("*.jsonl"))
    for p in skrar:
        with open(p, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                n += 1
                d = json.loads(line)
                for e in V.iter_errors(d):
                    n_villa += 1
                    if len(villur) < 25:
                        villur.append(f"{p.name}:{i}  "
                                      f"{'/'.join(map(str, e.path)) or '<rót>'}: {e.message}")
                stodur[d["sokn_stada"]] = stodur.get(d["sokn_stada"], 0) + 1
                nl = (d["lind"], d["source_listing_id"], d["image_nr"], d["afbrigdi"])
                if nl in lyklar and lyklar[nl] != d["hrina_id"]:
                    arekstrar += 1
                lyklar[nl] = d["hrina_id"]
    log(f"SKEMA-VALIDERING: {len(skrar)} manifest-skrár · {n:,} línur · "
        f"{n_villa} skemabrot · {len(lyklar):,} einstakir náttúrulegir lyklar · "
        f"{arekstrar} endurskrif á lykli (nýjasta hrina gildir) · stöður={stodur}")
    for v in villur:
        log("  " + v)
    return 0 if n_villa == 0 else 1



# ============================================================================= slot-útvíkkun
def slot_utvikkun(log: Log, thurr: bool = False) -> int:
    r"""cc111 keyrsla 4 — gerir manifestið að TÆMANDI kortlagningu.

    Engin ytri sókn, engin ný bæti, ekkert PUT. Skrifar manifest-röð fyrir hvert
    (lind, source_listing_id, image_nr, afbrigdi) sem á bæti á R2.

    TVÆR LINDIR, BÁÐAR SKYLDA:
      A. `scraper.listings.photos_json`  — lifandi slot (read-only úr Postgres)
      B. `listing_images.db`             — SÖGULEG slot. 44.206 sóttar slóðir eru
         horfnar úr photos_json og kortlagning þeirra er AÐEINS til hér (cc109 §1.5).
         Taflan er lyklað á (source, source_listing_id, image_nr) — réttum lykli —
         með 386.587 einkvæmar `fetched`-raðir.

    `listing_status` í B er ALDREI lesin (frosin merking frá 27.06, cc109 §1.6).
    Slot sem þegar á manifest-röð er ekki endurskrifað — sóknarstaðreyndin þar er
    upprunalegri en útvíkkunin.
    """
    db = opna_visi()
    hrina_id = nu().strftime("%Y%m%dT%H%M%SZ") + "_slotutvikkun"

    # ---- 0. hvað á bæti? (slóð -> sha/ending/bæti) ----
    slod: dict[str, tuple] = {}
    for r in db.execute("""SELECT s.url, s.sha256, s.byte_len, g.ending
                           FROM slod s JOIN sha_geymd g ON g.sha256 = s.sha256
                           WHERE s.sokn_stada='sott' AND g.a_r2=1"""):
        slod[r["url"]] = (r["sha256"], r["byte_len"], r["ending"])
    log(f"  slóðir m/bæti á R2: {len(slod):,}")

    # ---- 1. slot sem ÞEGAR eiga manifest-röð ----
    fyrir: set[tuple] = set()
    for p in sorted((MANIFEST_ROT / "manifest").glob("*.jsonl")):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                d = json.loads(line)
                fyrir.add((d["lind"], d["source_listing_id"], d["image_nr"], d["afbrigdi"]))
    log(f"  manifest-slot fyrir: {len(fyrir):,}")

    ny: dict[tuple, dict] = {}
    tal = {"A_photos_json_slot": 0, "A_m_baeti": 0, "A_ny_rod": 0,
           "B_listing_images_radir": 0, "B_m_baeti": 0, "B_ny_rod": 0,
           "B_utan_photos_json": 0}

    def baeta(lind, sll, nr, url, fastnum, listing_id, uppruni):
        v = slod.get(url)
        if v is None:
            return False
        lykill = (lind, sll, nr, AFBRIGDI[lind])
        if lykill in fyrir or lykill in ny:
            return False
        sha, blen, ending = v
        ny[lykill] = {
            "lind": lind, "source_listing_id": sll, "image_nr": nr,
            "afbrigdi": AFBRIGDI[lind], "listing_id": listing_id, "fastnum": fastnum,
            "url_sott": url, "sha256": sha, "byte_len": blen,
            "content_type": None, "ending": ending,
            "r2_lykill": f"{R2_FORSKEYTI}/{lind}/{sha[:2]}/{sha}{ending}",
            "breidd": None, "haed": None,
            "sokn_stada": "tvitak", "http_kodi": None, "sott_kl": nu_s(),
            "hrina_id": hrina_id,
            "athugasemd": f"slot-utvikkun/{uppruni}"}
        return True

    # ---- A. photos_json (lifandi slot) ----
    for lid, lind, sll, fastnum, status, slodir in lesa_auglysingar(["mbl", "myigloo"], log):
        for nr, url in slodir:
            tal["A_photos_json_slot"] += 1
            if url in slod:
                tal["A_m_baeti"] += 1
                if baeta(lind, sll, nr, url, fastnum, lid, "photos_json"):
                    tal["A_ny_rod"] += 1

    # ---- B. listing_images.db (söguleg slot) ----
    lifandi_slod = set()
    if LISTING_IMGS.exists():
        li = sqlite3.connect(f"file:{LISTING_IMGS}?mode=ro", uri=True)
        for src, sll, nr, url, fastnum in li.execute(
                """SELECT source, source_listing_id, image_nr, url, fastnum
                   FROM listing_images"""):
            tal["B_listing_images_radir"] += 1
            if url in slod:
                tal["B_m_baeti"] += 1
                if baeta(src, str(sll), nr, url, fastnum, None, "listing_images"):
                    tal["B_ny_rod"] += 1
        li.close()
    db.close()

    log("  " + json.dumps(tal, ensure_ascii=False))
    log(f"  NÝJAR MANIFEST-RAÐIR: {len(ny):,}  ->  alls {len(fyrir)+len(ny):,}")
    if thurr:
        log("  --throka: ekkert skrifað.")
        return 0

    mf = MANIFEST_ROT / "manifest" / f"{hrina_id}.jsonl"
    with open(mf, "w", encoding="utf-8") as fh:
        for d in ny.values():
            fh.write(json.dumps(d, ensure_ascii=False))
            fh.write(NYLINA)
    log(f"  skrifað {mf} ({mf.stat().st_size/1048576:.1f} MB)")

    bok = {"hrina_id": hrina_id, "run_id": hrina_id, "ts": nu_s(),
           "n_manifest": len(ny), "n_sott": 0, "n_tvitak": len(ny), "n_tynt": 0,
           "n_sleppt": 0, "n_einstok_ny_sha": 0, "baeti_ny_sha": 0,
           "jafna_fjoldi": True, "jafna_hlutir": True, "jafna_baeti": True,
           "jafna_spegill": True, "tegund": "slot_utvikkun_engin_sokn",
           **{f"tal_{k}": v for k, v in tal.items()},
           "manifest_skra": str(mf)}
    msp = spegla_manifest(log, " [slot-utvikkun]")
    bok["jafna_manifest_spegill"] = bool(msp["jafna_manifest"]) and msp["copy_exit"] == 0
    bok["manifest_spegill"] = msp
    bok["stada"] = "HEIL" if bok["jafna_manifest_spegill"] else "OLOKIN"
    with open(HRINUR_JL, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(bok, ensure_ascii=False)); fh.write(NYLINA)
    return 0 if bok["stada"] == "HEIL" else 2


# ============================================================================= CLI
def main() -> int:
    ap = argparse.ArgumentParser(description="cc111 myndasækjari")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--framvirkt", action="store_true")
    g.add_argument("--bakfylling", action="store_true")
    g.add_argument("--endurbyggja-visi", action="store_true")
    g.add_argument("--stadfesta", action="store_true")
    g.add_argument("--spegla-manifest", action="store_true")
    g.add_argument("--slot-utvikkun", action="store_true")

    ap.add_argument("--lind", default="allar", choices=["mbl", "myigloo", "allar"])
    ap.add_argument("--thraedir-mbl", type=int, default=1)
    ap.add_argument("--thraedir-myigloo", type=int, default=4)
    ap.add_argument("--stigun", action="store_true",
                    help="U3: stiga mbl 1->2->4, falla á fyrsta fráviki og halda")
    ap.add_argument("--threp-myndir", type=int, default=400)
    ap.add_argument("--hrina-myndir", type=int, default=4000)
    ap.add_argument("--hrina-gib", type=float, default=2.0)
    ap.add_argument("--thak-myndir", type=int, default=0)
    ap.add_argument("--thak-gib", type=float, default=0.0)
    ap.add_argument("--thak-min", type=int, default=0)
    ap.add_argument("--nyjustu", type=int, default=0,
                    help="framvirkt: takmarka við N nýjustu auglýsingar")
    ap.add_argument("--throka", action="store_true", help="velja og telja, engin sókn")
    ap.add_argument("--r2-lyklaskra", default=None)
    a = ap.parse_args()
    a.ham = ("framvirkt" if a.framvirkt else "bakfylling" if a.bakfylling
             else "endurbyggja_visi" if a.endurbyggja_visi
             else "spegla_manifest" if a.spegla_manifest
             else "slot_utvikkun" if a.slot_utvikkun else "stadfesta")

    MANIFEST_ROT.mkdir(parents=True, exist_ok=True)
    (MANIFEST_ROT / "keyrslur").mkdir(exist_ok=True)
    log = Log(MANIFEST_ROT / "keyrslur" / f"{nu().strftime('%Y%m%d')}_{a.ham}.log")

    if a.ham == "stadfesta":
        return stadfesta(log)
    if a.ham == "slot_utvikkun":
        return slot_utvikkun(log, a.throka)
    if a.ham == "spegla_manifest":
        d = spegla_manifest(log, " [sjalfstaett]")
        return 0 if (d["jafna_manifest"] and d["copy_exit"] == 0) else 2
    if a.ham == "endurbyggja_visi":
        t = endurbyggja_visi(log, Path(a.r2_lyklaskra) if a.r2_lyklaskra else None)
        log("VÍSIR ENDURBYGGÐUR: " + json.dumps(t, ensure_ascii=False))
        (MANIFEST_ROT / "visir_stada.json").write_text(
            json.dumps({"ts": nu_s(), **t}, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    db = opna_visi()
    if db.execute("SELECT COUNT(*) FROM sha_geymd").fetchone()[0] == 0:
        log("NEITA: vísirinn er tómur. Keyrðu --endurbyggja-visi fyrst, annars "
            "telur sækjarinn allt safnið ósótt og sækir 213.843 myndir að óþörfu.")
        return 4
    try:
        return keyra(a, log, db)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
