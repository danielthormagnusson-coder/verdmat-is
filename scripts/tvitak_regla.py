"""tvitak_regla.py — cc267: EIN skilgreining á mbl-tvítaki (sbr. feedback_merki_verdur_ad_lesast_ur_einu_falli).

Tilefni: mbl fjöldaskapaði 15.–16.10.2026 sömu auglýsinguna þúsundum sinnum (nýtt eign_id, ~1/s):
Laugavegur 170 íb 605 ×2.899, Áshamar 52 (leiga) ×2.474 o.fl. — SKIL_CC265 §2, SKIL_CC267 §1.

REGLA (regla_version = REGLA_VERSION):
  * efnislykill = (source, tenure, is_price_on_request, fastnum, addr_text, price_amount,
                   size_sqm, agency_source_id, md5(lysing))
    Óstöðug svæði UTAN lykils: source_listing_id, photos_json (undirritaðar CDN-slóðir),
    br_dags, last_seen_at, status, discovered_at, lat/lng, unit_key.
  * innan efnislykils eru raðir raðaðar eftir (listed_at, listing-auðkenni) og KEÐJAÐAR í klasa:
    röð fer í klasa fyrri raðar ef listed_at - listed_at(fyrri) <= GLUGGI.
  * frumrit = fyrsta röð klasans; allar hinar eru tvítök frumritsins.
    frumrit er KLASALYKILL (scraper.listing_tvitok.frumrit_listing_id), ekki endilega röðin sem birtist:
    scraper.v_tvitok_falin endurmetur við hverja lesningu og BIRTIR elsta LIFANDI eintak klasans
    (cc267 ákvörðun 2) — taki mbl frumritið niður en tvítak lifir, helst eignin „Á sölu".
GLUGGI = 10 mín: bil milli raða með sama efni er tvítoppað (mælt 20.10 á 83.176 klösum,
cc267 §1): 13.824 bil < 10 mín, 5 bil 10–60 mín, svo ekkert fyrr en ≥ 1 klst (1.260 < 1 d, 52.818 ≥ 1 d).
Endurbirting sama efnis daginn eftir er því EKKI tvítak — hún er utan þessarar reglu.

Óbreytanlegt: fallið skrifar ekkert, les ekkert — tekur lista af dict og skilar vörpun.
Notað af promote_listings_append (vörn við innsetningu) og D:\\_audit\\cc267_tvitok\\merkja_tvitok.py
(sóttkví þess sem þegar er inni). SQL-spegillinn D:\\_audit\\cc267_tvitok\\regla.sql er AÐEINS
krossprófun (tvær óháðar útfærslur sem verða að skila sama mengi), ekki önnur heimild.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

REGLA_VERSION = "tvitak_v1_10min"
GLUGGI = timedelta(minutes=10)


def _ts(v):
    if v is None or isinstance(v, datetime):
        return v
    s = str(v).strip().replace(" ", "T")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _num(v):
    """Tölur bornar saman óháð gerð (Decimal úr Postgres, float úr parse, str úr CSV)."""
    if v is None or v == "":
        return None
    d = Decimal(str(v))
    return d.normalize() if d == d.to_integral_value() else d.quantize(Decimal("0.01")).normalize()


def _txt(v):
    return None if v is None else str(v)


def efnislykill(r) -> tuple:
    lys = r.get("lysing") or ""
    por = r.get("is_price_on_request")
    if isinstance(por, str):
        por = por.strip().lower() in ("true", "t", "1")
    return (_txt(r.get("source")), _txt(r.get("tenure")), bool(por) if por is not None else None,
            _num(r.get("fastnum")), _txt(r.get("addr_text")), _num(r.get("price_amount")),
            _num(r.get("size_sqm")), _num(r.get("agency_source_id")),
            hashlib.md5(lys.encode("utf-8")).hexdigest())


def flokka(radir, audkenni="listing_id", gluggi=GLUGGI) -> dict:
    """Skilar {auðkenni_tvítaks: auðkenni_frumrits} fyrir allar raðir sem eru tvítök.
    Raðir án listed_at eru aldrei tvítök (fail-closed: í vafa stendur röðin)."""
    hopar = defaultdict(list)
    for r in radir:
        t = _ts(r.get("listed_at"))
        if t is None:
            continue
        hopar[efnislykill(r)].append((t, _rodun(r[audkenni]), r[audkenni]))
    ut = {}
    for rs in hopar.values():
        if len(rs) < 2:
            continue
        rs.sort()
        frumrit, fyrri_t = rs[0][2], rs[0][0]
        for t, _, a in rs[1:]:
            if t - fyrri_t <= gluggi:
                ut[a] = frumrit
            else:
                frumrit = a
            fyrri_t = t
    return ut


def _rodun(a):
    """Jafnteflisbrjótur: tölulegt auðkenni eftir tölugildi, annars sem strengur."""
    s = str(a)
    return (0, int(s), "") if s.isdigit() else (1, 0, s)
