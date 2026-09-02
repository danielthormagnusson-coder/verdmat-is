"""fable_worker.py — FRAMLEIÐSLU-WORKER sölugáttarinnar (cc172, fasi 2).

Pollar `public.fable_orders` og keyrir eina greidda pöntun gegnum alla
Fable-keðjuna: pakkasmíð -> (Fable) -> dómgrind -> gröf/kort -> hnitmiðun ->
upphleðsla -> `status='delivered'`.

──────────────────────────────────────────────────────────────────────────
API-HLIÐIÐ (cc172-bannið)
──────────────────────────────────────────────────────────────────────────
ENGIN köll á Anthropic gerast án `--leyfa-fable`. Sjálfgefið stöðvast
workerinn FYRIR þrep 5 og skilar `BIDUR_GO`; pöntunin fer aftur í 'paid'
(ekki 'failed' — ekkert brást, hliðið var einfaldlega lokað).
Þetta nær LÍKA til `count_tokens`: það er ókeypis og engin líkanakeyrsla,
en það er samt kall á api.anthropic.com með model=claude-fable-5, og
bannið er orðað um KÖLL, ekki um kostnað.

──────────────────────────────────────────────────────────────────────────
HVERS VEGNA VINNUMAPPA + PATCH EN EKKI PARAMETERÍSERING
──────────────────────────────────────────────────────────────────────────
Keðjan er 16 skriftur og ENGIN þeirra tekur fastnum sem rök: hver harðkóðar
`FASTNUM = 2230688`, `PAKKI_2230688_cc166.json`, `HLIDARVEGUR64_SKYRSLA.html`
og `D:\\_audit\\cc166_hlidarvegur64` efst hjá sér (74 tilvik í 27 skriftum,
mælt cc172). Hver fyrri lota bjó til nýja eign með því að AFRITA möppuna og
breyta hausunum í höndunum.

Workerinn vélvæðir nákvæmlega það handverk í stað þess að endurskrifa 16
sannreyndar skriftur: hann afritar SNIÐMÁTIÐ í vinnumöppu pöntunarinnar og
beitir þremur skiptingum. Skriftirnar sjálfar eru ÓSNERTAR á disknum, svo
sönnunargildi cc166/cc167/cc168-keyrslnanna helst.

Patchið er MÆLT, ekki treyst: hver skipting telur tilvik fyrir og eftir, og
`_stadfesta_patch` krefst þess að ENGIN leif af sniðmátsgildunum standi eftir
í keyrsluskriftunum. Skipting sem lendir 0 sinnum er FALL, ekki þögn —
str_replace sem hittir ekki er nákvæmlega það sem lítur út eins og velgengni.

FLUTNINGSSLÓÐ (bókuð MVP-ákvörðun): rétta lagfæringin er `argparse` +
`--fastnum` á q05/q06/q10/q11 og heiti leidd af pakkanum. Þangað til er
patch-lagið hliðið sem gerir keðjuna keyranlega per pöntun.

──────────────────────────────────────────────────────────────────────────
KEYRSLURÖÐIN (úr cc166/cc167/cc168)
──────────────────────────────────────────────────────────────────────────
  1  q05 -> q06 -> q08 -> q09      Supabase, read-only
  2  q10                            PAKKI_<fastnum>.json + _kompakt.json
  3  q11 count                      kostnaðarhlið             [API]
  4  q11 run 1                      HTML + hugsun + meta      [API]
     hlið: meta["SVARAD_AF_FABLE"] verður að vera true
  5  q15 (+q12, q12b)               q15_out.json — LESIÐ, kastar ekki
  6  q23_svg + q24_kort -> q26_setja_inn -> q29_stilsnid
  7  q27_domur                      q27_out.json — HEILDARDOMUR
  8  q31_hnitmidun -> q32_domur     q32_out.json — DOMUR, assertar
  9  upphleðsla + status='delivered'

FALLMEÐFERÐ: ein endurkeyrsla (attempt_count). Falli hún aftur ->
`status='qa'` + tölvupóstlína á Danna. ENGIN sjálfvirk afhending á fallinni
skýrslu — það er allur tilgangur dómgrindarinnar.

WRITE SAFETY: pooler 6543 er sjálfgefið READ ONLY; hver skrif-txn byrjar á
`SET TRANSACTION READ WRITE` sem FYRSTU stæðu.

CLI (fullar slóðir, engar cd-samsetningar):
  python D:\\verdmat-is\\app\\scripts\\fable_worker.py
      -> þessi texti, exit 0 (ekkert gerist)
  python D:\\verdmat-is\\app\\scripts\\fable_worker.py --once --dry-run
      -> velur pöntun, undirbýr vinnumöppu, ENGIN DB-skrif, ENGIN API-köll
  python D:\\verdmat-is\\app\\scripts\\fable_worker.py --once
      -> full keyrsla að API-hliðinu, stöðvast þar (BIDUR_GO)
  python D:\\verdmat-is\\app\\scripts\\fable_worker.py --once --leyfa-fable
      -> FULL KEYRSLA MEÐ API-KÖLLUM (krefst GO-línu Danna)
  python D:\\verdmat-is\\app\\scripts\\fable_worker.py --poll --leyfa-fable
      -> Task Scheduler-hamur: lykkja með --bil sekúndna millibili

deps: stdlib + psycopg2 + requests (öll þegar í notkun í þessu repo).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── slóðir ────────────────────────────────────────────────────────────────
DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
SNIDMAT = Path(r"D:\_audit\cc166_hlidarvegur64")
VINNURAETUR = Path(r"D:\_fable_keyrslur")
ENV_AI = Path(r"D:\verdmat-is\verdmat-ai\.env.local")
LOGG = Path(r"D:\_fable_keyrslur\worker.log")

BUCKET = "fable-skyrslur"

# count_tokens-þakið er RUNAWAY-VÖRN, ekki stærðarstýring.
#
# Sópunin í q06 §3 (allar sölur 24 mán, sama tegund, ±15% flatarmál, í ÖLLUM
# póstnúmerum sveitarfélagsins) hefur engin efri mörk, svo pakkastærð ræðst
# af eigninni. Mælt á slembiúrtaki 400 T1/T2-eigna (cc172 q12):
#
#         p50      p75      p90      p99      max     >800 raðir
#   T1    112      558     1270     1494     1497     21% eignanna
#   T2      8      115      497     1479     1493      8%
#
# TÓKASTUÐULLINN ER MÆLDUR, EKKI AFLEIDDUR (cc172 B4, q18). Tveir punktar úr
# raunverulegum count_tokens-köllum:
#     Hlíðarvegur 64:    56 sópunarraðir ->  48.819 tókar (2,04 bæti/tóki)
#     Snæland 2     : 1.560 sópunarraðir -> 302.098 tókar (1,76 bæti/tóki)
#   =>  tokar ≈ 39.388 + 168,4 * sópunarraðir
#
# Fyrri afleiðsla var `30.000 + 97 * raðir`, byggð á 3,5 bæti/tóka — ENSKU
# viðmiði. Íslenskur JSON með fastanúmerum, dagsetningum og götuheitum er
# nærri tvöfalt tókafrekari, svo hún vanmat um ~2x: spáði 175k þar sem
# raunmælingin gaf 302k.
#
# Þakið hefur því verið leiðrétt TVISVAR af sömu ástæðu — það var sett undir
# efri hluta dreifingarinnar:
#   120.000  fyrsta ágiskun (eitt dæmi)      -> hefði fellt 21% T1-eigna
#   250.000  afleitt úr röngum stuðli         -> svarar til 1.251 raða, en
#                                               T1 p90 er 1.270: felldi ~10%
#   350.000  MÆLT: yfir raunhámarki (291k)   <- runaway-vörn, ekki stærðarstýring
#
# Framlegð á mældum kostnaði (1.250 kr - VSK - Paddle = 902 kr nettó):
#   T1 p50  $2,48 -> +561 kr      T1 p90  $4,92 -> +224 kr
#   T1 max  $5,39 -> +158 kr      T2 p50  $2,26 -> +591 kr
# Jákvæð alls staðar, þynnst á efri helft T1 (B2: full sópun stendur).
#
# ÓVALIÐ (á borði Danna, cc172 §4): á að setja ÞAK Á SÓPUNINA sjálfa
# (t.d. 400 raðir, valdar næst í tíma/stærð)? Það lækkar kostnað efri helftar
# T1 um ~$1,3/skýrslu — en sópunartölurnar (p25/p50/p75, histogram) BIRTAST í
# skýrslunni og eru raktar í pakkann af dómgrindinni, svo þakið breytir
# efninu, ekki bara stærðinni. Þess vegna er það ekki tekið hér upp á eigin
# spýtur.
TOKA_THAK = 350000

# Sniðmátsgildin sem patchið skiptir út (mæld í cc166-möppunni).
SNIDMAT_FASTNUM = "2230688"
SNIDMAT_HEITI = "HLIDARVEGUR64"
# Nákvæmlega strengurinn í cc166_hlidarvegur64/q10.py línu 27 (SOTT = "…").
SNIDMAT_SOTT = "2026-08-14 (cc166, fyrsta raunnotkun — kaupandaskýrsla, ein read-only keyrsla)"
SNIDMAT_MAPPA = r"D:\_audit\cc166_hlidarvegur64"

# Skriftirnar sem keyrsluröðin snertir — AÐEINS þær eru afritaðar og
# patchaðar. Hinar 11 í möppunni (kannanir, debug, skjáskot) eiga ekkert
# erindi í framleiðslu og eru skildar eftir viljandi.
KEDJA = [
    "q05.py", "q06.py", "q08.py", "q09.py", "q10.py", "q11.py",
    "q12.py", "q12b.py", "q15.py",
    "q23_svg.py", "q24_kort.py", "q26_setja_inn.py", "q29_stilsnid.py",
    "q27_domur.py", "q31_hnitmidun.py", "q32_domur.py",
]
FYLGISKRAR = ["PROMPT_GRIND_cc166.md"]


# ══════════════════════════════════════════════════════════════════════════
# grunnur
# ══════════════════════════════════════════════════════════════════════════
def nu():
    return datetime.now(timezone.utc)


def log(s):
    lina = "%s  %s" % (nu().strftime("%Y-%m-%dT%H:%M:%SZ"), s)
    print(lina, flush=True)
    try:
        LOGG.parent.mkdir(parents=True, exist_ok=True)
        with LOGG.open("a", encoding="utf-8") as f:
            f.write(lina + "\n")
    except OSError:
        pass  # loggun má aldrei fella keyrslu


def db():
    # .dbconfig er UTF-8 MEÐ BOM — utf-8-sig, aldrei plain utf-8.
    conn = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    conn.autocommit = False
    return conn


def env_ai(lykill):
    """Les einn lykil úr verdmat-ai/.env.local (KEY=value, hunsar $env:-línur)."""
    if not ENV_AI.exists():
        return None
    for lina in ENV_AI.read_text(encoding="utf-8-sig").splitlines():
        lina = lina.strip()
        if lina.startswith("#") or "=" not in lina:
            continue
        k, _, v = lina.partition("=")
        if k.strip().lstrip("$").replace("env:", "") == lykill:
            return v.strip().strip('"').strip("'")
    return None


# ══════════════════════════════════════════════════════════════════════════
# 1. pöntunin
# ══════════════════════════════════════════════════════════════════════════
def taka_pontun(conn, order_id=None, dry=False):
    """Grípur eina greidda pöntun og færir hana í 'generating'.

    Uppfærslan er SKILYRT á status='paid' í WHERE — tveir workerar sem
    lesa sömu röðina geta ekki báðir gripið hana; sá seinni fær rowcount 0.
    """
    with conn.cursor() as cur:
        if not dry:
            cur.execute("SET TRANSACTION READ WRITE")
        if order_id:
            cur.execute("""
                SELECT order_id, fastnum, sjonarhorn, attempt_count, status
                FROM public.fable_orders WHERE order_id = %s
            """, (order_id,))
        else:
            # FOR UPDATE SKIP LOCKED heldur tveimur workerum frá sömu röð — en
            # það er SKRIF-læsing og fellur í read-only txn ("cannot execute
            # SELECT FOR UPDATE in a read-only transaction"), svo --dry-run
            # les án hennar. Dry-keyrsla grípur enga pöntun hvort eð er.
            cur.execute("""
                SELECT order_id, fastnum, sjonarhorn, attempt_count, status
                FROM public.fable_orders
                WHERE status = 'paid'
                ORDER BY paid_at
                LIMIT 1
                %s
            """ % ("" if dry else "FOR UPDATE SKIP LOCKED"))
        rod = cur.fetchone()
        if not rod:
            conn.rollback()
            return None
        oid, fastnum, sjonarhorn, attempts, stada = rod
        # Sjálfvirka biðröðin tekur AÐEINS 'paid'. Handvirkt --order má líka
        # taka 'failed': status-vélin leyfir failed->generating, og það er
        # einmitt endurkeyrslan sem reglan gerir ráð fyrir. Án þessa yrði
        # hver fallin pöntun ósnertanleg nema með handskrifuðu SQL-i.
        leyfilegar = ("paid", "failed") if order_id else ("paid",)
        if stada not in leyfilegar:
            log("pöntun %s er í stöðu '%s', ekki %s — sleppt"
                % (oid, stada, "/".join(leyfilegar)))
            conn.rollback()
            return None
        if dry:
            conn.rollback()
            return {"order_id": str(oid), "fastnum": fastnum,
                    "sjonarhorn": sjonarhorn, "attempt_count": attempts}
        cur.execute("""
            UPDATE public.fable_orders
               SET status = 'generating', attempt_count = attempt_count + 1
             WHERE order_id = %s AND status = ANY(%s)
        """, (oid, list(leyfilegar)))
        if cur.rowcount != 1:
            conn.rollback()
            log("pöntun %s var gripin af öðrum — sleppt" % oid)
            return None
    conn.commit()
    return {"order_id": str(oid), "fastnum": fastnum,
            "sjonarhorn": sjonarhorn, "attempt_count": attempts + 1}


def setja_stodu(conn, order_id, stada, **reitir):
    setningar = ["status = %s"]
    gildi = [stada]
    for k, v in reitir.items():
        setningar.append("%s = %%s" % k)
        gildi.append(v)
    gildi.append(order_id)
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("UPDATE public.fable_orders SET %s WHERE order_id = %%s"
                    % ", ".join(setningar), gildi)
    conn.commit()


# ══════════════════════════════════════════════════════════════════════════
# 2. vinnumappa + MÆLT patch
# ══════════════════════════════════════════════════════════════════════════
def heiti_af_eign(conn, fastnum):
    """Skráarheiti leitt af heimilisfangi (ASCII, hástafir) — kemur í stað
    'HLIDARVEGUR64'. Fastnúmerið er alltaf með svo heitið sé ótvírætt."""
    with conn.cursor() as cur:
        cur.execute("SELECT heimilisfang FROM public.properties WHERE fastnum = %s",
                    (fastnum,))
        rod = cur.fetchone()
    conn.rollback()
    hf = (rod[0] if rod and rod[0] else "EIGN")
    umritun = {"Á": "A", "Ð": "D", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
               "Ý": "Y", "Þ": "TH", "Æ": "AE", "Ö": "O"}
    hreint = "".join(umritun.get(c, c) for c in hf.upper())
    hreint = re.sub(r"[^A-Z0-9]", "", hreint)
    return "%s%s" % (hreint[:24] or "EIGN", fastnum)


def undirbua_vinnumoppu(order_id, fastnum, heiti):
    """Afritar keðjuna í vinnumöppu pöntunarinnar og patchar hana — MÆLT."""
    vinnu = VINNURAETUR / order_id
    if vinnu.exists():
        shutil.rmtree(vinnu)          # endurkeyrsla byrjar á hreinu borði
    vinnu.mkdir(parents=True)

    skiptingar = [
        (SNIDMAT_MAPPA, str(vinnu)),
        (SNIDMAT_FASTNUM, str(fastnum)),
        (SNIDMAT_HEITI, heiti),
        # cc182: `meta.sott` var FROSIÐ á sniðmátsdaginn 2026-08-14 — kassinn
        # sagði „−18. dagur á markaði" á eign auglýstri 1.9. og Fable-textinn
        # „sótt 2026-08-14" ×29. Keyrsludagur pöntunarinnar í staðinn.
        (SNIDMAT_SOTT, "%s (pöntun %s)" % (datetime.now(timezone.utc).date().isoformat(), order_id)),
    ]

    maeling = {}
    for nafn in KEDJA:
        uppruni = SNIDMAT / nafn
        if not uppruni.exists():
            raise FileNotFoundError("sniðmátsskrift vantar: %s" % uppruni)
        texti = uppruni.read_text(encoding="utf-8")
        per_skra = {}
        for fra, til in skiptingar:
            n = texti.count(fra)
            if n:
                texti = texti.replace(fra, til)
            per_skra[fra] = n
        (vinnu / nafn).write_text(texti, encoding="utf-8")
        maeling[nafn] = per_skra

    for nafn in FYLGISKRAR:
        shutil.copyfile(SNIDMAT / nafn, vinnu / nafn)

    _stadfesta_patch(vinnu, maeling)
    return vinnu, maeling


def _stadfesta_patch(vinnu, maeling):
    """Patch sem hittir ekki lítur nákvæmlega út eins og patch sem tókst.

    Tvö hlið:
      (a) ENGIN leif af sniðmátsgildunum má standa eftir í keyrsluskriftunum.
      (b) Hver skipting verður að hafa lent EINHVERS STAÐAR í keðjunni —
          skipting sem lendir 0 sinnum í ÖLLUM skrám þýðir að sniðmátið
          hefur breyst undir workernum og patchið er úrelt.
    """
    leifar = []
    for nafn in KEDJA:
        t = (vinnu / nafn).read_text(encoding="utf-8")
        for merki in (SNIDMAT_FASTNUM, SNIDMAT_HEITI, SNIDMAT_MAPPA, SNIDMAT_SOTT):
            if merki in t:
                leifar.append("%s: leif af '%s'" % (nafn, merki))
    if leifar:
        raise RuntimeError("PATCH-LEIFAR (%d): %s" % (len(leifar), "; ".join(leifar)))

    for merki in (SNIDMAT_FASTNUM, SNIDMAT_HEITI, SNIDMAT_MAPPA, SNIDMAT_SOTT):
        alls = sum(per.get(merki, 0) for per in maeling.values())
        if alls == 0:
            raise RuntimeError(
                "PATCH ÚRELT: '%s' fannst hvergi í keðjunni — sniðmátið hefur "
                "breyst og skiptingin lendir ekki." % merki)


# ══════════════════════════════════════════════════════════════════════════
# 3. keyrsla skriftanna
# ══════════════════════════════════════════════════════════════════════════
class Threp(Exception):
    """Þrep sem féll — ber sitt eigið nafn og úttak."""

    def __init__(self, nafn, kodi, ut):
        super().__init__("%s féll (exit %s)" % (nafn, kodi))
        self.nafn, self.kodi, self.ut = nafn, kodi, ut


def keyra(vinnu, skrift, rok=(), timeout=3600):
    t0 = time.time()
    cmd = [sys.executable, str(vinnu / skrift), *rok]
    r = subprocess.run(cmd, cwd=str(vinnu), capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=timeout)
    sek = time.time() - t0
    log("   %-18s exit=%-3s %6.1fs" % (skrift + " " + " ".join(rok), r.returncode, sek))
    if r.returncode != 0:
        hali = (r.stdout or "")[-1500:] + "\n--- stderr ---\n" + (r.stderr or "")[-1500:]
        raise Threp(skrift, r.returncode, hali)
    return {"skrift": skrift, "rok": list(rok), "sek": round(sek, 1),
            "exit": r.returncode}


def lesa_json(vinnu, nafn):
    p = vinnu / nafn
    if not p.exists():
        raise Threp(nafn, "vantar", "úttaksskrá varð aldrei til: %s" % p)
    return json.loads(p.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════════════════
# 4. upphleðsla
# ══════════════════════════════════════════════════════════════════════════
def hlada_upp(order_id, skyrsla_path):
    """Setur skýrsluna í private bucketinn um Storage-REST með service_role."""
    url = env_ai("NEXT_PUBLIC_SUPABASE_URL")
    lykill = env_ai("SUPABASE_SERVICE_ROLE_KEY") or env_ai("VM_SUPABASE_SERVICE_KEY")
    if not url or not lykill:
        raise RuntimeError("upphleðsla: NEXT_PUBLIC_SUPABASE_URL eða "
                           "SUPABASE_SERVICE_ROLE_KEY vantar í %s" % ENV_AI)
    gogn = skyrsla_path.read_bytes()
    sha = hashlib.sha256(gogn).hexdigest()
    slod = "%s/skyrsla.html" % order_id
    r = requests.post(
        "%s/storage/v1/object/%s/%s" % (url.rstrip("/"), BUCKET, slod),
        headers={"Authorization": "Bearer %s" % lykill,
                 "Content-Type": "text/html",
                 "x-upsert": "true"},
        data=gogn, timeout=120)
    if not r.ok:
        raise RuntimeError("upphleðsla féll: HTTP %s %s" % (r.status_code, r.text[:400]))
    return {"bucket": BUCKET, "path": slod, "sha256": sha, "bytes": len(gogn)}


def tilkynna_danna(efni, texti):
    """qa-línan. Best-effort: bregðist pósturinn stendur staðan samt."""
    key = env_ai("RESEND_API_KEY") or os.environ.get("RESEND_API_KEY")
    til = env_ai("ABENDING_MOTTAKANDI") or os.environ.get("ABENDING_MOTTAKANDI")
    if not key or not til:
        log("   (tölvupóstur ekki stilltur — qa-lína aðeins í logg)")
        return False
    try:
        r = requests.post("https://api.resend.com/emails",
                          headers={"Authorization": "Bearer %s" % key,
                                   "Content-Type": "application/json"},
                          json={"from": env_ai("ABENDING_FRA")
                                or "verdmat.ai <onboarding@resend.dev>",
                                "to": [til], "subject": efni, "text": texti},
                          timeout=30)
        return r.ok
    except requests.RequestException as e:
        log("   tölvupóstur brást: %s" % e)
        return False


# ══════════════════════════════════════════════════════════════════════════
# 5. keðjan sjálf
# ══════════════════════════════════════════════════════════════════════════
def framleida(conn, pontun, leyfa_fable, dry):
    oid = pontun["order_id"]
    fastnum = pontun["fastnum"]
    heiti = heiti_af_eign(conn, fastnum)
    log("PÖNTUN %s — fastnum %s (%s), tilraun %d"
        % (oid, fastnum, heiti, pontun["attempt_count"]))

    vinnu, maeling = undirbua_vinnumoppu(oid, fastnum, heiti)
    alls = {m: sum(p.get(m, 0) for p in maeling.values())
            for m in (SNIDMAT_FASTNUM, SNIDMAT_HEITI, SNIDMAT_MAPPA)}
    log("   vinnumappa %s — patch: fastnum x%d, heiti x%d, mappa x%d"
        % (vinnu, alls[SNIDMAT_FASTNUM], alls[SNIDMAT_HEITI], alls[SNIDMAT_MAPPA]))

    threp = []

    # ---- 1-2. PAKKINN (Supabase, read-only) ----
    for s in ("q05.py", "q06.py", "q08.py", "q09.py", "q10.py"):
        threp.append(keyra(vinnu, s))
    pakki = vinnu / ("PAKKI_%s_cc166.json" % fastnum)
    if not pakki.exists():
        raise Threp("q10.py", "vantar", "pakkinn varð aldrei til: %s" % pakki)
    log("   pakki: %s (%s bæti)" % (pakki.name, format(pakki.stat().st_size, ",")))

    # ---- API-HLIÐIÐ ----
    if not leyfa_fable:
        log("   API-HLIÐIÐ LOKAÐ (--leyfa-fable vantar) — stöðvast fyrir þrep 3.")
        return {"stada": "BIDUR_GO", "vinnumappa": str(vinnu), "threp": threp,
                "pakki": str(pakki)}
    if dry:
        log("   --dry-run: hætt fyrir API-köll.")
        return {"stada": "DRY", "vinnumappa": str(vinnu), "threp": threp}

    # ---- 3. count_tokens-vörnin ----
    threp.append(keyra(vinnu, "q11.py", ("count",), timeout=300))
    tokar = lesa_json(vinnu, "q11_tokar.json")
    log("   count_tokens: %s inntakstókar (~$%.2f cache-skrif)"
        % (format(tokar["input_tokens_alls"], ","),
           tokar["input_tokens_alls"] / 1e6 * 12.5))
    if tokar["input_tokens_alls"] > TOKA_THAK:
        raise Threp("q11 count", "þak",
                    "inntakspakkinn er %s tókar — yfir þakinu %s"
                    % (format(tokar["input_tokens_alls"], ","),
                       format(TOKA_THAK, ",")))

    # ---- 4. FABLE-KEYRSLAN ----
    threp.append(keyra(vinnu, "q11.py", ("run", "1"), timeout=3600))
    meta = lesa_json(vinnu, "KEYRSLA_1_meta.json")
    if not meta.get("SVARAD_AF_FABLE"):
        raise Threp("q11 run", "fallback", "SVARAD_AF_FABLE=false — fallback greip inn í")
    # Tókarnir liggja í meta["tokar"]["output"], EKKI í meta["output_tokens"] —
    # fyrsta smíð las rangan lykil og logaði „0 út-tókar" á keyrslu sem
    # skilaði 33.473. `.get` með sjálfgefnu gildi þegir um rangan lykil.
    tk = meta.get("tokar", {})
    log("   Fable: %s út-tókar (inn %s, cache-skrif %s), $%s, %ss"
        % (format(tk.get("output", 0), ","), format(tk.get("input", 0), ","),
           format(tk.get("cache_write", 0), ","),
           meta.get("kostnadur_usd", "?"), meta.get("sekundur", "?")))

    # Skýrslan sem keðjan vinnur áfram með.
    skyrsla = vinnu / ("%s_SKYRSLA.html" % heiti)
    if not skyrsla.exists():
        # q11 vistar KEYRSLA_1.html; cc166 afritaði hana handvirkt yfir.
        shutil.copyfile(vinnu / "KEYRSLA_1.html", skyrsla)
        log("   KEYRSLA_1.html -> %s" % skyrsla.name)

    # ---- 5. DÓMGRINDIN (les JSON — q15 kastar ekki) ----
    threp.append(keyra(vinnu, "q15.py"))
    d15 = lesa_json(vinnu, "q15_out.json")
    fall15 = _lesa_q15(d15)
    if fall15:
        raise Threp("q15", "domur", "dómgrindin felldi: %s" % "; ".join(fall15))
    log("   q15: STENST")

    # ---- 6. GRÖF + KORT + STÍLL ----
    for s in ("q23_svg.py", "q24_kort.py", "q26_setja_inn.py", "q29_stilsnid.py"):
        threp.append(keyra(vinnu, s))

    # ---- 7. q27 (les HEILDARDOMUR — kastar ekki) ----
    threp.append(keyra(vinnu, "q27_domur.py"))
    d27 = lesa_json(vinnu, "q27_out.json")
    if d27.get("HEILDARDOMUR") != "STENST":
        raise Threp("q27_domur", "domur", "HEILDARDOMUR=%s  domar=%s"
                    % (d27.get("HEILDARDOMUR"), d27.get("domar")))
    log("   q27: STENST")

    # ---- 8. HNITMIÐUN + q32 (assertar sjálf) ----
    # q31 krefst þess að `<HEITI>_SKYRSLA_pre_hnitmidun.html` sé til og
    # BÝTA-EINS og skýrslan (`assert cur == pre`) — cc168 bjó það afrit til
    # í höndunum. Í framleiðslu er enginn til að gera það, svo workerinn
    # tekur afritið hér, rétt áður en q31 breytir skjalinu. Sé það þegar til
    # (endurkeyrsla) stendur það: q31 á að bera saman við UPPRUNANN, ekki
    # við eigið úttak frá fyrri tilraun.
    pre = vinnu / ("%s_SKYRSLA_pre_hnitmidun.html" % heiti)
    if not pre.exists():
        shutil.copyfile(skyrsla, pre)
        log("   afrit tekið: %s" % pre.name)
    threp.append(keyra(vinnu, "q31_hnitmidun.py"))
    threp.append(keyra(vinnu, "q32_domur.py"))
    d32 = lesa_json(vinnu, "q32_out.json")
    if d32.get("DOMUR") != "STENST":
        raise Threp("q32_domur", "domur", "DOMUR=%s" % d32.get("DOMUR"))
    log("   q32: STENST")

    # ---- 9. UPPHLEÐSLA ----
    upp = hlada_upp(oid, skyrsla)
    log("   upphlaðið: %s (%s bæti, sha %s…)"
        % (upp["path"], format(upp["bytes"], ","), upp["sha256"][:12]))

    return {"stada": "DELIVERED", "vinnumappa": str(vinnu), "threp": threp,
            "upp": upp, "meta": meta, "q15": d15, "q27": d27, "q32": d32}


def _lesa_q15(d):
    """q15 skilar teljurum, ekki einu pass/fail — hliðin lesin berum orðum."""
    fall = []
    a1 = d.get("a1", {})
    if a1.get("DOMUR_a_maelanlega_menginu") not in (None, "STENST"):
        fall.append("a1=%s" % a1.get("DOMUR_a_maelanlega_menginu"))
    a2 = d.get("a2", {})
    if a2.get("SKYLDA_n") is not None and a2.get("SKYLDA_stadist") != a2.get("SKYLDA_n"):
        fall.append("a2 skylda %s/%s (brostin: %s)"
                    % (a2.get("SKYLDA_stadist"), a2.get("SKYLDA_n"),
                       a2.get("SKYLDA_brostin")))
    b = d.get("b", {})
    if b.get("bonn_brotin"):
        fall.append("b bönn brotin: %s" % b["bonn_brotin"])
    return fall


# ══════════════════════════════════════════════════════════════════════════
# 6. ein umferð
# ══════════════════════════════════════════════════════════════════════════
def ein_umferd(leyfa_fable, dry, order_id=None):
    conn = db()
    try:
        pontun = taka_pontun(conn, order_id=order_id, dry=dry)
        if not pontun:
            log("engin greidd pöntun í biðröð.")
            return None
        oid = pontun["order_id"]
        try:
            nid = framleida(conn, pontun, leyfa_fable, dry)
        except Exception as e:
            hali = e.ut if isinstance(e, Threp) else traceback.format_exc()[-2000:]
            log("FALL á pöntun %s: %s" % (oid, e))
            log(hali[:1200])
            if dry:
                return {"stada": "FALL(dry)", "villa": str(e)}
            # Ein endurkeyrsla; falli hún aftur -> qa (ALDREI afhending).
            if pontun["attempt_count"] >= 2:
                setja_stodu(conn, oid, "qa", villa_texti=("%s\n\n%s" % (e, hali))[:8000])
                tilkynna_danna(
                    "verdmat.ai — pöntun %s í yfirlestur (qa)" % oid,
                    "Pöntun %s (fastnum %s) féll í tilraun %d.\n\n%s\n\n%s"
                    % (oid, pontun["fastnum"], pontun["attempt_count"], e, hali[:3000]))
                log("   -> status=qa, tölvupóstlína send.")
            else:
                setja_stodu(conn, oid, "failed",
                            villa_texti=("%s\n\n%s" % (e, hali))[:8000])
                log("   -> status=failed (ein endurkeyrsla eftir).")
            return {"stada": "FALL", "villa": str(e)}

        if nid["stada"] == "DELIVERED" and not dry:
            upp = nid["upp"]
            setja_stodu(conn, oid, "delivered",
                        report_bucket=upp["bucket"], report_path=upp["path"],
                        report_sha256=upp["sha256"], report_bytes=upp["bytes"],
                        fable_model=nid["meta"].get("model"),
                        kostnadur_usd=nid["meta"].get("kostnadur_usd"))
            log("PÖNTUN %s AFHENT." % oid)
        elif nid["stada"] == "BIDUR_GO" and not dry:
            # Ekkert brást — hliðið var lokað. Röðin fer aftur í biðröðina.
            setja_stodu(conn, oid, "failed",
                        villa_texti="BIDUR_GO: API-hliðið lokað (--leyfa-fable vantar).")
            log("PÖNTUN %s sett í 'failed' (BIDUR_GO) — bíður GO-línu." % oid)
        return nid
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(add_help=True, description="cc172 Fable-worker")
    ap.add_argument("--once", action="store_true", help="ein pöntun, svo hætt")
    ap.add_argument("--poll", action="store_true", help="lykkja (Task Scheduler)")
    ap.add_argument("--bil", type=int, default=300, help="sekúndur milli polla")
    ap.add_argument("--order", help="tiltekin pöntun (uuid)")
    ap.add_argument("--leyfa-fable", action="store_true",
                    dest="leyfa_fable",
                    help="OPNAR API-HLIÐIÐ — krefst GO-línu Danna")
    ap.add_argument("--dry-run", action="store_true", dest="dry",
                    help="engin DB-skrif, engin API-köll")
    args = ap.parse_args()

    if not (args.once or args.poll or args.order):
        print(__doc__)
        return 0

    if args.leyfa_fable:
        log("!! API-HLIÐIÐ OPIÐ (--leyfa-fable) — Fable-köll verða gerð.")
    else:
        log("API-hliðið lokað (sjálfgefið). Engin Anthropic-köll í þessari keyrslu.")

    if args.poll:
        log("poll-hamur, bil %ds. Ctrl+C til að stöðva." % args.bil)
        while True:
            try:
                ein_umferd(args.leyfa_fable, args.dry)
            except Exception:
                log("umferð féll:\n%s" % traceback.format_exc()[-1500:])
            time.sleep(args.bil)
    else:
        ein_umferd(args.leyfa_fable, args.dry, order_id=args.order)
    return 0


if __name__ == "__main__":
    sys.exit(main())
