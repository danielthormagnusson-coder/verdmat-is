# cc319: hlið u2. AFRIT af frosnu D:\_audit\cc319_eigindi\hlid2.py (a3/frysting.txt). Breyting = ný mæling.
import re
import lysing_hlid as hlid
_s = hlid._s

GERVI = r"plastparket|vínil|vinil|vínyl|vinyl|viníl|vatnshelt ?parket"
FLIS_GOLF = r"flís\w*\s+á\s+(\w+\s+)?gólf|gólf\w*\s+(er\s+|eru\s+)?(með\s+)?flís|flísalögð gólf|flísalagt gólf"


def golfefni(s, t):
    """a2: flísar og teppi falla á lesun (flísalagt bað, teppi í sameign). Parket aðeins ef ekkert gerviparket í texta; flísar aðeins á gólfi; teppi út."""
    g = s.get("golfefni") or []
    L = []
    if "parket" in g and _s(hlid.GOLF["parket"], t) and not _s(GERVI, t):
        L.append("parket")
    if "flisar" in g and _s(FLIS_GOLF, t):
        L.append("flisar")
    return dict(tegundir=sorted(L)) if L else None


def opid_rymi(s, t):
    b = s.get("opid_rymi_brot") or ""
    if s.get("opid_rymi") != "ja" or _s(r"ljós|lýsing|perum", b):
        return None
    return dict(til=True) if _s(r"\bop(ið|in|nu|na)\s+(\w+\s+)?(rým|skipulag)|\balrým", b) else None


def bilskur(s, t):
    b = s.get("bilskur_brot") or ""
    if _s(r"bílskúrsrétt|grunn|þakjárn|þak á|þaki|yfirbyggt|baklóð|lóð", b):
        return None
    return hlid.bilskur(s, t)


def heitur_pottur(s, t):
    b = s.get("heitur_pottur_brot") or ""
    if _s(r"ónýt|pláss|getur fylgt|skel|köld", b):
        return None
    return hlid.EIG["heitur_pottur"](s, t)


def lagnir(s, t):
    b = (s.get("lagnir") or {}).get("brot") or ""
    if _s(r"stigagang|tafla|töflu|tengl", b):
        return None
    return hlid.astand(s, t, "lagnir")


EIG2 = {"golfefni": golfefni, "opid_rymi": opid_rymi, "bilskur_staedi": bilskur, "heitur_pottur": heitur_pottur}
SELLUR = [("golfefni", "apartment"), ("golfefni", "house"), ("golfefni", "townhouse"), ("opid_rymi", "apartment"), ("bilskur_staedi", "apartment"), ("heitur_pottur", "house"), ("á:lagnir", "apartment")]
