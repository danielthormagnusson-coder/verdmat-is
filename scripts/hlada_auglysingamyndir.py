#!/usr/bin/env python3
r"""hlada_auglysingamyndir.py — cc117 FASI B, þrep 4.

Hleður diskmanifestinu (myndamanifest/manifest/*.jsonl) í
`scraper.auglysingamyndir` og merkir 57 raðir í `public.property_images`
sem `vantar_a_r2`.

  --thurrkeyrsla   les allt, skrifar EKKERT, prentar nákvæmlega hvað færi inn
  --skrifa         framkvæmir (krefst þess að taflan sé til, þ.e. migration applýjuð)
  --stadfesta      les töfluna og ber saman við manifestið, engin skrif

ÞRJÁR REGLUR SEM VÉLIN BER
--------------------------
1. MANIFESTIÐ ER HEIMILDIN, TAFLAN ER SPEGILL. Vélin er `idempotent`:
   `on conflict (lykill) do update`. Endurkeyrsla á óbreyttu manifesti skilar
   sama rowcount og hefur engin efnisleg áhrif.
   ATH. VÉLIN GREINIR EKKI `n_ny` FRÁ `n_uppfaerd` — `execute_values` +
   `ON CONFLICT DO UPDATE` skilar ekki þeirri sundurliðun, og hún er ekki
   sótt sérstaklega. Jafnan sem vélin ber er á HEILDINNI (`tafla_jofn`:
   rowcount == einkvæm slot í manifestinu). Þurfi einhver að vita hve margar
   raðir BREYTTUST verður að bæta því við — ekki lesa það úr þessum tölum.

2. TAKEDOWN-DÁLKAR ERU ALDREI SKRIFAÐIR AF ÞESSARI VÉL — nema fyrir
   `vantar_a_r2`. `utilokad_kl` sem rétthafabeiðni setti á að LIFA AF
   endurhleðslu; ella þurrkaði næsta keyrsla út afgreidda beiðni í hljóði.
   Þess vegna telur `on conflict`-liðurinn þá dálka EKKI upp.

3. RÖÐ ER EKKI TALA. `image_nr` úr manifestinu er staða myndarinnar í
   `photos_json`, ekki 1..n röðun. Viewið raðar með `row_number() over
   (order by image_nr)`, svo göt í `image_nr` (mæld: koma fyrir, því
   sumar slóðir eru dauðar) verða samfelld birtingarröð.

FORSENDA: `.dbconfig` (utan git) ber Postgres-URI. Sama skrá og
myndasaekjari.py les. Skrif fara á `rw`-tengingu og
`SET TRANSACTION READ WRITE` er FYRSTA STÆÐAN — sbr.
feedback_set_transaction_read_write_verdur_ad_vera_fyrsta.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# BÁÐIR straumar, ekki bara stdout. Skrifta sem endurstillir stdout eingöngu
# skilar rakningunni eftir sem cp1252-hakki í næturloggi sem fangar `2>&1` —
# og þögul villa í cp1252 er ekki hávær villa. Sbr.
# feedback_haevaer_villa_i_cp1252_er_ekki_haevaer.
for _straumur in (sys.stdout, sys.stderr):
    try:
        _straumur.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROT          = Path(r"D:\verdmat-is")
MANIFEST_DIR = ROT / "scraper_data" / "myndamanifest" / "manifest"
DBCFG        = ROT / ".dbconfig"
IMAGE_INDEX  = Path(r"D:\Gagnapakkar\image_index.db")
AUDIT_DIR    = Path(r"D:\_audit\cc117_myndbirting")

LOTA = 5000  # raðir per executemany-lotu


def _stimpill() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# --------------------------------------------------------------------------- lestur
def lesa_manifest() -> tuple[dict, Counter]:
    """Les allt manifestið og skilar {lykill: rod}. Síðasta lína vinnur.

    Lykillinn er NÁTTÚRULEGI lykillinn (cc109): (lind, source_listing_id,
    image_nr, afbrigdi). URL er ALDREI lykill — 44.206 sóttar slóðir eru
    horfnar úr photos_json og bætin lifa samt.
    """
    radir: dict[tuple, dict] = {}
    talning = Counter()
    skrar = sorted(glob.glob(str(MANIFEST_DIR / "*.jsonl")))
    if not skrar:
        raise SystemExit(f"ENGIN manifest-skrá í {MANIFEST_DIR}")
    for skra in skrar:
        with open(skra, encoding="utf-8") as fh:
            for lina in fh:
                lina = lina.strip()
                if not lina:
                    continue
                d = json.loads(lina)
                talning["linur"] += 1
                if not d.get("sha256"):
                    talning["an_sha"] += 1
                    continue
                lykill = (d["lind"], d["source_listing_id"],
                          int(d["image_nr"]), d["afbrigdi"])
                if lykill in radir:
                    talning["endurtekid_slot"] += 1
                radir[lykill] = d
                talning["m_sha"] += 1
    talning["einkvaem_slot"] = len(radir)
    return radir, talning


def lesa_vantar57() -> list[tuple[int, int]]:
    """57 (fastnum, img_order) pör sem eru EKKI á R2.

    Listinn er LEIDDUR úr image_index.db, aldrei harðkóðaður: hann er
    afleiðing af `downloaded=0` og verður að fylgja vísinum ef hann breytist.
    fastnum=0 er sleppt — sú röð birtist hvergi (58. röðin).
    """
    if not IMAGE_INDEX.exists():
        raise SystemExit(f"vísirinn finnst ekki: {IMAGE_INDEX}")
    c = sqlite3.connect(f"file:{IMAGE_INDEX}?mode=ro", uri=True)
    par = list(c.execute(
        "select fastnum, image_nr from image_index "
        "where downloaded = 0 and fastnum <> 0 order by fastnum, image_nr"))
    c.close()
    return [(int(f), int(n)) for f, n in par]


# --------------------------------------------------------------------------- DB
def tengja(skrifa: bool):
    import psycopg2
    from psycopg2.extras import execute_values  # noqa: F401  (sótt í keyra())
    if not DBCFG.exists():
        raise SystemExit(f"vantar {DBCFG}")
    # utf-8-SIG, ekki utf-8: .dbconfig er UTF-8 MEÐ BOM (mælt: EF BB BF).
    # `utf-8` skilur ﻿ eftir fremst í URI-inu og tengingin fellur á
    # ólæsilegri villu. Sama og myndasaekjari.py:381 gerir. Skjalfest í CLAUDE.md.
    uri = DBCFG.read_text(encoding="utf-8-sig").strip()
    conn = psycopg2.connect(uri)
    conn.autocommit = False
    with conn.cursor() as cur:
        # FYRSTA STÆÐAN. Ekkert SELECT á undan — pooler-gildran (cc86/cc94/cc104).
        cur.execute("SET TRANSACTION READ WRITE" if skrifa
                    else "SET TRANSACTION READ ONLY")
    return conn


# execute_values, EKKI executemany. Mælt vandamál, ekki fagurfræði: executemany
# gerir EINA UMFERÐ Á RÖÐ yfir transaction-poolerinn, sem á 988 þús. röðum er
# klukkustunda-verk. execute_values sendir fjöl-raða VALUES í lotum og gerir
# eina umferð á LOTU. `%s` hér að neðan er raða-sniðmátið sem execute_values
# fyllir — ekki venjuleg stika.
SQL_INNSETNING = """
insert into scraper.auglysingamyndir
  (lind, source_listing_id, image_nr, afbrigdi, listing_id, fastnum,
   agency_name, sha256, r2_lykill, byte_len, breidd, haed, sott_kl)
values %s
on conflict (lind, source_listing_id, image_nr, afbrigdi) do update set
  listing_id  = excluded.listing_id,
  fastnum     = excluded.fastnum,
  agency_name = excluded.agency_name,
  sha256      = excluded.sha256,
  r2_lykill   = excluded.r2_lykill,
  byte_len    = excluded.byte_len,
  breidd      = excluded.breidd,
  haed        = excluded.haed,
  sott_kl     = excluded.sott_kl
-- utilokad_kl / utilokun_astaeda ERU EKKI HÉR. Sjá reglu 2 í hausnum.
"""


def saekja_agency(conn) -> dict[tuple[str, str], str]:
    """(source, source_listing_id) -> agency_name.

    Afritað inn á töfluna af ásettu ráði: fasteignasölu-takedown á að vera
    EITT update á kortlagningartöflunni, ekki join við scraper.listings.

    MÆLT VIÐ HLEÐSLU 2026-08-11 — og niðurstaðan skerpir rökin frekar en
    að staðfesta þau blint. Þekja `agency_name` er 917.412 af 988.651 (92,8%),
    og gatið er ekki jafndreift:

      mbl,     m/listing_id        899.603 raðir → 899.599 m/nafn  (99,9996%)
      mbl,     án listing_id        68.650 raðir →  17.813 m/nafn  ( 25,9%)
      myigloo, hvort sem er         20.398 raðir →       0 m/nafn  (lind án miðlara)

    ⇒ AFRITIÐ LAGAR EKKI 50.837 SÖGULEGU mbl-RAÐIRNAR — þær eiga enga
      auglýsingu í `scraper.listings` lengur og ekkert getur gefið þeim nafn
      án nýrrar heimildar. Það sem afritið gerir er að VERJA hinar 899.599
      fyrir því að verða næsta 50.837-mengi þegar auglýsingar þeirra hverfa
      úr töflunni. Join hefði látið þekjuna rýrna þögult með tímanum.

    ⚠ AFLEIÐING SEM VERÐUR AÐ STANDA Í TEXTA TIL RÉTTHAFA: fasteignasölu-
      takedown („allar myndir frá X") nær til 92,8% raða. Beiðni sem á að ná
      til hinna þarf að vísa á eign eða slóð.
    """
    with conn.cursor() as cur:
        cur.execute("select source, source_listing_id, agency_name "
                    "from scraper.listings where agency_name is not null")
        return {(s, sll): a for s, sll, a in cur.fetchall()}


# --------------------------------------------------------------------------- hamir
def keyra(args) -> int:
    ts = _stimpill()
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== LESTUR MANIFESTS ===")
    radir, t = lesa_manifest()
    print(f"  línur alls        : {t['linur']:>9,}")
    print(f"  án sha (sleppt)   : {t['an_sha']:>9,}")
    print(f"  með sha           : {t['m_sha']:>9,}")
    print(f"  endurtekin slot   : {t['endurtekid_slot']:>9,}  (síðasta lína vinnur)")
    print(f"  EINKVÆM SLOT      : {t['einkvaem_slot']:>9,}  <- fer í töfluna")

    vantar = lesa_vantar57()
    print(f"  vantar_a_r2 pör   : {len(vantar):>9,}")

    per_lind = Counter(k[0] for k in radir)
    m_fastnum = sum(1 for d in radir.values() if d.get("fastnum"))
    einkv_fastnum = len({d["fastnum"] for d in radir.values() if d.get("fastnum")})
    einkv_augl = len({(k[0], k[1]) for k in radir})
    print(f"  per lind          : {dict(per_lind)}")
    print(f"  slot m/fastnum    : {m_fastnum:,}  (án fastnums = leiguauglýsingar: "
          f"{t['einkvaem_slot'] - m_fastnum:,})")
    print(f"  einkvæm fastnúmer : {einkv_fastnum:,}")
    print(f"  einkvæmar augl.   : {einkv_augl:,}")

    if args.thurrkeyrsla:
        # Þurrkeyrslan snertir EKKI DB — hún má keyra áður en migration er applýjuð.
        nidur = {
            "ts": ts, "hamur": "thurrkeyrsla",
            "manifest": dict(t), "per_lind": dict(per_lind),
            "slot_m_fastnum": m_fastnum, "einkvaem_fastnum": einkv_fastnum,
            "einkvaemar_auglysingar": einkv_augl,
            "vantar_a_r2": len(vantar),
        }
        skra = AUDIT_DIR / f"hledsla_thurrkeyrsla_{ts}.json"
        skra.write_text(json.dumps(nidur, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        print(f"\n  ENGIN SKRIF. Niðurstaða: {skra}")
        return 0

    # ---- raunkeyrsla -------------------------------------------------------
    from psycopg2.extras import execute_values

    conn = tengja(skrifa=True)
    try:
        with conn.cursor() as cur:
            cur.execute("select count(*) from scraper.auglysingamyndir")
            fyrir = cur.fetchone()[0]
            cur.execute("select count(*) from public.property_images "
                        "where utilokad_kl is not null")
            uti_fyrir = cur.fetchone()[0]
        print(f"\n=== FYRIR === tafla {fyrir:,} raðir · "
              f"property_images útilokaðar {uti_fyrir:,}")

        agency = saekja_agency(conn)
        print(f"  agency-uppfletting: {len(agency):,} auglýsingar bera nafn")

        buntur, n = [], 0
        with conn.cursor() as cur:
            for (lind, sll, nr, afb), d in radir.items():
                buntur.append((
                    lind, sll, nr, afb,
                    d.get("listing_id"), d.get("fastnum"),
                    agency.get((lind, sll)),
                    d["sha256"], d["r2_lykill"], d.get("byte_len"),
                    d.get("breidd"), d.get("haed"), d.get("sott_kl"),
                ))
                if len(buntur) >= LOTA:
                    execute_values(cur, SQL_INNSETNING, buntur, page_size=LOTA)
                    n += len(buntur); buntur = []
                    print(f"    ... {n:,}/{len(radir):,}", end="\r", flush=True)
            if buntur:
                execute_values(cur, SQL_INNSETNING, buntur, page_size=LOTA)
                n += len(buntur)
            print(f"    ... {n:,}/{len(radir):,}")

            # 57 vantar_a_r2. Skilyrt á `utilokad_kl is null` svo aðgerðin
            # yfirskrifi ALDREI rétthafabeiðni sem er þegar afgreidd.
            cur.executemany(
                "update public.property_images "
                "   set utilokad_kl = now(), utilokun_astaeda = 'vantar_a_r2' "
                " where fastnum = %s and img_order = %s and utilokad_kl is null",
                vantar)

        with conn.cursor() as cur:
            cur.execute("select count(*) from scraper.auglysingamyndir")
            eftir = cur.fetchone()[0]
            cur.execute("select count(*) from public.property_images "
                        "where utilokun_astaeda = 'vantar_a_r2'")
            uti_eftir = cur.fetchone()[0]

        # JÖFNUÐUR — fellur ÁÐUR en commit er gefið.
        #
        # ⚠ HÉR ER **ENGIN** JAFNA Á `v_eign_myndir`, OG ÞAÐ ER VILJANDI.
        # Vélin keyrir á milli 3a og 3b: eftir 3a ber viewið enn GÖMLU
        # skilgreininguna, sem les ekki `utilokad_kl`. Jafna á
        # `safn = 2.583.775 − 57` félli því RANGLEGA hér og stöðvaði rétta
        # hleðslu. Sú jafna á heima í eftirmælingu 3b, þar sem viewið er
        # loksins orðið það sem hún mælir.
        #
        # Reglan á bak við: vél á að jafna á ÞAÐ SEM HÚN SKRIFAÐI, ekki á
        # afleidda fleti sem annað þrep á eftir að breyta.
        jofn = {
            "tafla_jofn":  eftir == len(radir),
            "vantar_jofn": uti_eftir == len(vantar),
        }
        print(f"\n=== EFTIR === tafla {eftir:,} · vantar_a_r2 {uti_eftir:,}")
        for k, v in jofn.items():
            print(f"  {k:14s}: {'OK' if v else 'FELLUR'}")

        if not all(jofn.values()):
            conn.rollback()
            print("\nJÖFNUÐUR FELLUR — ROLLBACK, ekkert skrifað.")
            return 2

        conn.commit()
        print("\nCOMMIT.")
        (AUDIT_DIR / f"hledsla_{ts}.json").write_text(
            json.dumps({"ts": ts, "fyrir": fyrir, "eftir": eftir,
                        "vantar_a_r2": uti_eftir,
                        "jofnudur": jofn}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--thurrkeyrsla", action="store_true",
                   help="les allt, skrifar ekkert, snertir ekki DB")
    g.add_argument("--skrifa", action="store_true",
                   help="framkvæmir (krefst applýjaðrar migration)")
    return keyra(p.parse_args())


if __name__ == "__main__":
    sys.exit(main())
