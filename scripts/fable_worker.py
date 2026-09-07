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
  7b q30_umgjord (cc192)            markup-umgjörð (td.tala, kafla-akkeri,
                                    V-hlekkir) — eigin bakfærslu-/textasönnun
  8  q31_hnitmidun -> q32_domur     q32_out.json — DOMUR, assertar
  9  upphleðsla + status='delivered'
 10  póstur á kaupanda (cc186) — hlekkur á /pontun/<order_id>; hliðið er
     email_sent_at á röðinni; póstfall fellir ALDREI delivered

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
  python D:\\verdmat-is\\app\\scripts\\fable_worker.py --once --leyfa-fable --hamark 3 --adeins-live
      -> cc193: Task Scheduler-verkið (5 mín); girðingar (a) live-only (b) hámark 3
      # (c) kill-switch D:\\verdmat-is\\STOPP_FABLE (d) póstur/idempotens óbreytt

deps: stdlib + psycopg2 + requests (öll þegar í notkun í þessu repo).
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import html as htmlmod
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
# cc186: varalind fyrir lykla sem eru HVERGI í verdmat-ai/.env.local
# (RESEND_API_KEY, PADDLE_*_LIVE). Lesin á eftir ENV_AI, aldrei á undan.
ENV_ROT = Path(r"D:\env.local")
LOGG = Path(r"D:\_fable_keyrslur\worker.log")
# cc193 girðing (c): kill-switch standandi Fable-heimildar á scheduler. Sé
# skráin til grípur workerinn ENGA pöntun (engin Fable-köll); pollun og
# póstumferð keyra áfram. Fjarlægðu skrána til að opna aftur.
STOPP_FABLE = Path(r"D:\verdmat-is\STOPP_FABLE")

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
# Nákvæmlega línan í cc166_hlidarvegur64/q06.py:13 og q08.py:11 (cc185).
SNIDMAT_KEYRSLUDAGUR = 'KEYRSLUDAGUR = "2026-08-14"'
# Nákvæmlega strengurinn í q10.py:243 — sópunarglugginn í prompt-textanum,
# sem líkanið afritar orðrétt („14.8.2024–14.8.2026" ×5 í skýrslunni). Sama
# gluggi og q06 §3 reiknar með `dags - interval '24 months'` (cc185).
SNIDMAT_SOPUNARGLUGGI = "(2024-08-14..2026-08-14)"
SNIDMAT_MAPPA = r"D:\_audit\cc166_hlidarvegur64"

# Skriftirnar sem keyrsluröðin snertir — AÐEINS þær eru afritaðar og
# patchaðar. Hinar 11 í möppunni (kannanir, debug, skjáskot) eiga ekkert
# erindi í framleiðslu og eru skildar eftir viljandi.
KEDJA = [
    "q05.py", "q06.py", "q08.py", "q09.py", "q10.py", "q11.py",
    "q12.py", "q12b.py", "q15.py",
    "q23_svg.py", "q24_kort.py", "q26_setja_inn.py", "q29_stilsnid.py",
    "q27_domur.py", "q30_umgjord.py", "q31_hnitmidun.py", "q32_domur.py",
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
    """Les einn lykil úr verdmat-ai/.env.local, annars D:/env.local (cc186).

    Röðin skiptir máli: framendalindin fyrst (lykillinn sem verdmat-ai keyrir
    á), D:/env.local aðeins fyrir lykla sem hún ber ekki. KEY=value;
    $env:-línur lesnar sem KEY."""
    for skra in (ENV_AI, ENV_ROT):
        if not skra.exists():
            continue
        for lina in skra.read_text(encoding="utf-8-sig").splitlines():
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
def taka_pontun(conn, order_id=None, dry=False, adeins_live=False):
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
                WHERE status = 'paid' %s
                ORDER BY paid_at
                LIMIT 1
                %s
            """ % ("AND paddle_env = 'live'" if adeins_live else "",  # cc193 girðing (a)
                   "" if dry else "FOR UPDATE SKIP LOCKED"))
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


def telja_greiddar(conn, adeins_live=False):
    """Fjöldi greiddra raða í biðröð (cc193) — aðeins til bókunar í logg."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM public.fable_orders WHERE status = 'paid'"
                    + (" AND paddle_env = 'live'" if adeins_live else ""))
        n = cur.fetchone()[0]
    conn.rollback()
    return n


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

    dagur = datetime.now(timezone.utc).date()
    keyrsludagur = dagur.isoformat()
    # Sama og Postgres `dags::date - interval '24 months'` (q06 §2/§3):
    # mánuðurinn færður, dagurinn klemmdur við mánaðarlengd.
    m = dagur.month - 24
    y = dagur.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    gluggi_fra = dagur.replace(year=y, month=m, day=min(dagur.day, calendar.monthrange(y, m)[1])).isoformat()
    skiptingar = [
        (SNIDMAT_MAPPA, str(vinnu)),
        (SNIDMAT_FASTNUM, str(fastnum)),
        (SNIDMAT_HEITI, heiti),
        # cc182: `meta.sott` var FROSIÐ á sniðmátsdaginn 2026-08-14 — kassinn
        # sagði „−18. dagur á markaði" á eign auglýstri 1.9. og Fable-textinn
        # „sótt 2026-08-14" ×29. Keyrsludagur pöntunarinnar í staðinn.
        (SNIDMAT_SOTT, "%s (pöntun %s)" % (keyrsludagur, order_id)),
        # cc185: KEYRSLUDAGUR í q06/q08 var líka frosinn á 2026-08-14 —
        # sópunarglugginn „14.8.2024–14.8.2026" ×5 í texta og sellutölfræðin
        # miðuð við sniðmátsdaginn. Sami dagur og SOTT, reiknaður einu sinni.
        (SNIDMAT_KEYRSLUDAGUR, 'KEYRSLUDAGUR = "%s"' % keyrsludagur),
        # cc185: sami gluggi stóð harðkóðaður í prompt-strengnum í q10 §sopun.
        (SNIDMAT_SOPUNARGLUGGI, "(%s..%s)" % (gluggi_fra, keyrsludagur)),
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
        for merki in (SNIDMAT_FASTNUM, SNIDMAT_HEITI, SNIDMAT_MAPPA, SNIDMAT_SOTT,
                      SNIDMAT_KEYRSLUDAGUR, SNIDMAT_SOPUNARGLUGGI):
            if merki in t:
                leifar.append("%s: leif af '%s'" % (nafn, merki))
    if leifar:
        raise RuntimeError("PATCH-LEIFAR (%d): %s" % (len(leifar), "; ".join(leifar)))

    for merki in (SNIDMAT_FASTNUM, SNIDMAT_HEITI, SNIDMAT_MAPPA, SNIDMAT_SOTT,
                      SNIDMAT_KEYRSLUDAGUR, SNIDMAT_SOPUNARGLUGGI):
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
# 4b. NETFANGSGRIP + PÓSTUR Á KAUPANDA (cc186)
# ══════════════════════════════════════════════════════════════════════════
# HVAR: í WORKERNUM, ekki í webhookinu. Webhookið (verdmat-ai/app/api/paddle/
# webhook/route.js) les `data.customer.email`, en transaction.completed ber
# `customer_id` og ENGAN customer-hlut — reiturinn er því NULL á hverri
# greiddri röð (mælt cc186 q04: Hverafold, kaupandi_email NULL, customer_id
# til). Workerinn á röðina frá 'paid' og áfram, pollar þegar, og breyting hér
# þarf hvorki deploy né push. Gripið: GET /transactions -> customer_id ->
# GET /customers -> email, með lykli eftir paddle_env RAÐARINNAR.
#
# PÓSTURINN fer aðeins á 'delivered'-raðir þar sem email_sent_at IS NULL —
# sá dálkur er HLIÐIÐ (migration 20260903111500_cc186_fable_orders_email).
# Póstfall fellir ALDREI stöðuna: villan bókast í email_villa og næsta poll
# reynir aftur. Idempotency-Key á Resend-kallið (order_id-bundinn) er önnur
# vörn skyldu tveir workerar ná sömu röð milli sendingar og bókunar.
#
# HLEKKURINN er /pontun/<order_id> — ALDREI signed URL (hún rennur út).

PADDLE_ROT = {"sandbox": "https://sandbox-api.paddle.com",
              "live": "https://api.paddle.com"}
POSTUR_FRA = "Verðmat.ai <skyrsla@verdmat.ai>"
POSTUR_SVAR = "hjalp@verdmat.ai"
PONTUN_ROT = "https://www.verdmat.ai/pontun/"
# Raðir afhentar FYRIR póstlögnina (cc186, 03.09.2026) eru sandbox-prófanir
# cc172–cc185 og fá ekki póst í sjálfvirku polli; þær nást aðeins með --order.
POSTUR_UPPHAF = "2026-09-03 00:00:00+00"
POSTUR_REITIR = ("order_id", "fastnum", "paddle_env", "paddle_transaction_id",
                 "kaupandi_email")


def paddle_lykill(env):
    """API-lykill eftir umhverfi RAÐARINNAR — sama regla og lib/paddle-env.js:
    live ósuffixað, sandbox með _SANDBOX. *_LIVE er varanafnið í D:\\env.local."""
    if env == "live":
        return env_ai("PADDLE_API_KEY") or env_ai("PADDLE_API_KEY_LIVE")
    return env_ai("PADDLE_API_KEY_SANDBOX")


def grima_netfang(nf):
    a, _, b = (nf or "").partition("@")
    return (a[:2] + "***@" + b) if b else "***"


def saekja_netfang_paddle(env, txn_id):
    """paddle_transaction_id -> customer_id -> email. None vanti nokkuð."""
    key = paddle_lykill(env)
    if not key or not txn_id:
        log("   netfangsgrip: %s vantar"
            % ("Paddle-lykil (%s)" % env if not key else "paddle_transaction_id"))
        return None
    rot = PADDLE_ROT.get(env)
    h = {"Authorization": "Bearer %s" % key}
    try:
        r = requests.get("%s/transactions/%s" % (rot, txn_id), headers=h, timeout=30)
        if not r.ok:
            log("   netfangsgrip: GET /transactions -> HTTP %s" % r.status_code)
            return None
        ctm = (r.json().get("data") or {}).get("customer_id")
        if not ctm:
            log("   netfangsgrip: færslan ber ekkert customer_id")
            return None
        r2 = requests.get("%s/customers/%s" % (rot, ctm), headers=h, timeout=30)
        if not r2.ok:
            log("   netfangsgrip: GET /customers -> HTTP %s" % r2.status_code)
            return None
        nf = ((r2.json().get("data") or {}).get("email") or "").strip()
        return nf or None
    except (requests.RequestException, ValueError) as e:
        log("   netfangsgrip brást: %s" % e)
        return None


def frysta_netfang(conn, order_id, netfang):
    """Skrifar kaupandi_email AÐEINS sé hann tómur — fyrsta gripið stendur."""
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("""UPDATE public.fable_orders SET kaupandi_email = %s
                        WHERE order_id = %s AND kaupandi_email IS NULL""",
                    (netfang, order_id))
        n = cur.rowcount
    conn.commit()
    return n == 1


def boka_postfall(conn, order_id, villa):
    """Bókar póstfall á röðina. STATUS ER ÓSNERTUR — delivered stendur."""
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("UPDATE public.fable_orders SET email_villa = %s WHERE order_id = %s",
                    (villa[:2000], order_id))
    conn.commit()


def heimilisfang_af_eign(conn, fastnum):
    with conn.cursor() as cur:
        cur.execute("SELECT heimilisfang FROM public.properties WHERE fastnum = %s",
                    (fastnum,))
        rod = cur.fetchone()
    conn.rollback()
    return rod[0] if rod and rod[0] else None


def postur_texti(heimilisfang, order_id):
    """(efni, texti, html). Íslenskur prósi; hlekkur á /pontun/<id>."""
    slod = PONTUN_ROT + order_id
    hf = heimilisfang or "eignina"
    efni = "Skýrslan þín um %s er tilbúin" % hf
    texti = (
        "Góðan dag,\n\n"
        "Verðmatsskýrslan þín um %s er tilbúin.\n\n"
        "Þú opnar hana hér:\n%s\n\n"
        "Slóðin er varanleg — hún er kvittunin þín og þú getur opnað hana hvenær "
        "sem er. Niðurhalshlekkurinn á síðunni endurnýjast við hvern smell, svo "
        "vistaðu skýrsluna sjálfa viljirðu eiga afrit.\n\n"
        "Spurningar eða athugasemdir? Svaraðu þessum pósti eða skrifaðu á %s.\n\n"
        "Kær kveðja,\nVerðmat.ai\n" % (hf, slod, POSTUR_SVAR))
    e = htmlmod.escape
    html = (
        '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
        'font-size:16px;line-height:1.5;color:#1a1a1a;max-width:560px">'
        "<p>Góðan dag,</p>"
        "<p>Verðmatsskýrslan þín um <strong>%s</strong> er tilbúin.</p>"
        '<p><a href="%s" style="display:inline-block;padding:10px 18px;'
        'background:#1a1a1a;color:#fff;text-decoration:none;border-radius:6px">'
        "Opna skýrsluna</a></p>"
        '<p style="font-size:14px;color:#555">Eða afritaðu slóðina: '
        '<a href="%s">%s</a></p>'
        "<p>Slóðin er varanleg — hún er kvittunin þín og þú getur opnað hana "
        "hvenær sem er. Niðurhalshlekkurinn á síðunni endurnýjast við hvern "
        "smell, svo vistaðu skýrsluna sjálfa viljirðu eiga afrit.</p>"
        '<p>Spurningar eða athugasemdir? Svaraðu þessum pósti eða skrifaðu á '
        '<a href="mailto:%s">%s</a>.</p>'
        "<p>Kær kveðja,<br>Verðmat.ai</p></div>"
        % (e(hf), e(slod), e(slod), e(slod), e(POSTUR_SVAR), e(POSTUR_SVAR)))
    return efni, texti, html


def senda_kaupandapost(conn, rod, dry=False, prof_netfang=None):
    """Einn póstur á eina afhenta röð. True aðeins ef sending OG bókun tókust.
    Fellir aldrei status — hvert fall bókast í email_villa og bíður næsta polls."""
    oid = rod["order_id"]
    netfang = rod["kaupandi_email"]
    if not netfang:
        netfang = saekja_netfang_paddle(rod["paddle_env"], rod["paddle_transaction_id"])
        if netfang and not dry:
            frysta_netfang(conn, oid, netfang)
            log("   netfang fryst á röðina: %s" % grima_netfang(netfang))
    if not netfang:
        if not dry:
            boka_postfall(conn, oid, "netfang vantar: hvorki á röð né hjá Paddle")
        log("   póstur %s: netfang vantar — reynt aftur í næsta polli." % oid)
        return False

    vidtakandi = netfang
    if prof_netfang:
        # Prófleið (cc186 lið 5): AÐEINS á sandbox-röð, bókað í logg. Röðin
        # heldur sínu netfangi; aðeins viðtakandi þessa eina pósts víkur.
        if rod["paddle_env"] != "sandbox":
            log("   --prof-netfang HAFNAÐ: röðin er %s, ekki sandbox." % rod["paddle_env"])
            return False
        vidtakandi = prof_netfang
        log("   PRÓF: sent á %s í stað %s (sandbox-röð)"
            % (grima_netfang(prof_netfang), grima_netfang(netfang)))

    key = env_ai("RESEND_API_KEY")
    if not key:
        if not dry:
            boka_postfall(conn, oid, "RESEND_API_KEY vantar")
        log("   póstur: RESEND_API_KEY vantar (ENV_AI/ENV_ROT).")
        return False

    efni, texti, html = postur_texti(heimilisfang_af_eign(conn, rod["fastnum"]), oid)
    if dry:
        log("   --dry-run: hefði sent „%s“ á %s" % (efni, grima_netfang(vidtakandi)))
        return False
    try:
        r = requests.post("https://api.resend.com/emails",
                          headers={"Authorization": "Bearer %s" % key,
                                   "Content-Type": "application/json",
                                   "Idempotency-Key": "delivered/%s" % oid},
                          json={"from": env_ai("POSTUR_FRA") or POSTUR_FRA,
                                "to": [vidtakandi],
                                "reply_to": POSTUR_SVAR,
                                "subject": efni, "text": texti, "html": html},
                          timeout=30)
    except requests.RequestException as e:
        boka_postfall(conn, oid, "Resend: %s" % e)
        log("   póstur %s brást: %s — bókað, reynt aftur." % (oid, e))
        return False
    if not r.ok:
        boka_postfall(conn, oid, "Resend HTTP %s: %s" % (r.status_code, r.text[:300]))
        log("   póstur %s: Resend HTTP %s — bókað, reynt aftur." % (oid, r.status_code))
        return False
    try:
        rid = (r.json() or {}).get("id") or "?"
    except ValueError:
        rid = "?"
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("""UPDATE public.fable_orders
                          SET email_sent_at = now(), email_resend_id = %s, email_villa = NULL
                        WHERE order_id = %s AND email_sent_at IS NULL""", (rid, oid))
        n = cur.rowcount
    conn.commit()
    log("   PÓSTUR SENDUR á %s (resend %s, bókun %s)"
        % (grima_netfang(vidtakandi), rid, "ok" if n == 1 else "ENGIN RÖÐ — þegar bókað?"))
    return n == 1


def posta_afhentar(conn, order_id=None, dry=False, prof_netfang=None):
    """Pollflötur póstsins: delivered AND email_sent_at IS NULL
    (fable_orders_postur_bidrod_idx). Ein tilraun per röð per umferð.
    Án order_id gildir POSTUR_UPPHAF; með order_id er röðin tekin óháð dagsetningu."""
    with conn.cursor() as cur:
        cur.execute("""SELECT order_id::text, fastnum, paddle_env, paddle_transaction_id,
                              kaupandi_email
                         FROM public.fable_orders
                        WHERE status = 'delivered' AND email_sent_at IS NULL
                          AND ((%s::uuid IS NULL AND delivered_at >= %s::timestamptz)
                               OR order_id = %s::uuid)
                        ORDER BY delivered_at
                        LIMIT 20""", (order_id, POSTUR_UPPHAF, order_id))
        radir = [dict(zip(POSTUR_REITIR, r)) for r in cur.fetchall()]
    conn.rollback()
    if not radir:
        log("póstur: engin afhent röð bíður pósts.")
        return 0
    send = 0
    for rod in radir:
        log("PÓSTUR á pöntun %s" % rod["order_id"])
        if senda_kaupandapost(conn, rod, dry=dry, prof_netfang=prof_netfang):
            send += 1
    return send


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

    # ---- 7b. UMGJÖRÐ (cc192) — markup-merki sem CSS ræður ekki við ----
    # Keyrð EFTIR q27 (d5 krefst byte-jafngildis við _pre_graf þegar brot og
    # stíll eru bakfærð) og FYRIR pre_hnitmidun-afritið, svo q31/q32 dæmi
    # gegn skjalinu MEÐ umgjörðinni. Skriftin sannar sjálf að enginn stafur
    # efnistexta hreyfist og að bakfærslan er byte-eins (assert -> exit != 0).
    threp.append(keyra(vinnu, "q30_umgjord.py"))

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
def ein_umferd(leyfa_fable, dry, order_id=None, adeins_postur=False, prof_netfang=None,
               adeins_live=False):
    conn = db()
    try:
        # cc186: póstar á afhentar raðir FYRST — óháð framleiðslu og Fable-hliði.
        # Fall hér má ekki stöðva framleiðsluna: bókað á röðina, umferðin heldur áfram.
        try:
            posta_afhentar(conn, order_id=order_id, dry=dry, prof_netfang=prof_netfang)
        except Exception:
            conn.rollback()
            log("póstumferð féll:\n%s" % traceback.format_exc()[-1200:])
        if adeins_postur:
            return None
        # cc193 girðing (c): kill-switch athugaður ÁÐUR en röð er gripin, svo
        # greidd röð stendur áfram sem 'paid' (hvorki generating né failed/
        # BIDUR_GO) þar til skráin er fjarlægð. Gildir óháð --leyfa-fable.
        if STOPP_FABLE.exists():
            n = telja_greiddar(conn, adeins_live)
            log("STOPP_FABLE til (%s) — Fable-köll SLEPPT í þessu polli; %d greidd röð/raðir "
                "bíða. Pollun og póstumferð keyrðu áfram." % (STOPP_FABLE, n))
            return {"stada": "STOPP", "bida": n}
        pontun = taka_pontun(conn, order_id=order_id, dry=dry, adeins_live=adeins_live)
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
            # cc186: pósturinn strax — bregðist hann bókast það og næsta poll reynir.
            try:
                posta_afhentar(conn, order_id=oid)
            except Exception:
                conn.rollback()
                log("póstur eftir afhendingu féll:\n%s" % traceback.format_exc()[-1200:])
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
    ap.add_argument("--adeins-postur", action="store_true", dest="adeins_postur",
                    help="cc186: aðeins póstumferðin (delivered án email_sent_at), "
                         "engin framleiðsla")
    ap.add_argument("--prof-netfang", dest="prof_netfang",
                    help="cc186: viðtakandi prófpósts í stað netfangs raðarinnar "
                         "— AÐEINS sandbox-raðir")
    ap.add_argument("--hamark", type=int, default=1,
                    help="cc193 girðing (b): hámark pantana (= Fable-kalla) í þessari "
                         "keyrslu; umfram bíður næsta polls (bókað). Scheduler: 3")
    ap.add_argument("--adeins-live", action="store_true", dest="adeins_live",
                    help="cc193 girðing (a): sjálfvirka biðröðin tekur aðeins "
                         "paddle_env='live'")
    args = ap.parse_args()

    if not (args.once or args.poll or args.order or args.adeins_postur):
        print(__doc__)
        return 0

    if args.leyfa_fable:
        log("!! API-HLIÐIÐ OPIÐ (--leyfa-fable) — Fable-köll verða gerð.")
        log("   girðingar cc193: hámark %d pöntun/pantanir í keyrslu; biðröð %s; "
            "kill-switch %s" % (args.hamark,
                                "aðeins live" if args.adeins_live else "live+sandbox",
                                "TIL" if STOPP_FABLE.exists() else "ekki til"))
    else:
        log("API-hliðið lokað (sjálfgefið). Engin Anthropic-köll í þessari keyrslu.")

    if args.poll:
        log("poll-hamur, bil %ds. Ctrl+C til að stöðva." % args.bil)
        while True:
            try:
                ein_umferd(args.leyfa_fable, args.dry,
                           adeins_postur=args.adeins_postur, prof_netfang=args.prof_netfang,
                           adeins_live=args.adeins_live)
            except Exception:
                log("umferð féll:\n%s" % traceback.format_exc()[-1500:])
            time.sleep(args.bil)
    else:
        # cc193 girðing (b): allt að --hamark pantanir í röð, svo hætt. Umfram
        # raðir standa sem 'paid' og bíða næsta polls — bókað í logg.
        n_gert = 0
        while True:
            nid = ein_umferd(args.leyfa_fable, args.dry, order_id=args.order,
                             adeins_postur=args.adeins_postur, prof_netfang=args.prof_netfang,
                             adeins_live=args.adeins_live)
            if (nid is None or nid.get("stada") == "STOPP" or args.order
                    or args.adeins_postur or args.dry):
                break
            n_gert += 1
            if n_gert >= args.hamark:
                conn = db()
                try:
                    bida = telja_greiddar(conn, args.adeins_live)
                finally:
                    conn.close()
                if bida:
                    log("HÁMARK %d náð — %d greidd röð/raðir bíða næsta polls."
                        % (args.hamark, bida))
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
