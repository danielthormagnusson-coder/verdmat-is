# cc319: hlið v1 á keyptum svörum (skema 3, 101). AFRIT af frosnu D:\_audit\cc319_eigindi\hlid.py (a2/frysting.txt). Breyting = ný mæling.
import re


def _s(p, b):
    return bool(re.search(p, b or "", re.I))


GERD_KJ = r"bílakjallar|bílgeymsl|bílageymsl|bílahús|bílastæðahús|bílskýli|bílakjall"
NEI_STAEDI = r"gegn (hóflegu |mánaðar)?gjald|mánaðargjald|möguleik|aðgang|aðgengi|hægt að (kaupa|fá|leigja)|til leigu|hreyfihaml"
JA_STAEDI = r"(sér|eigin|einka|merkt|sérmerkt|fylgir|fylgja|stæði nr|tilheyr)"


def bilskur(s, t):
    v, b = s.get("bilskur_staedi"), s.get("bilskur_brot") or ""
    if v in (None, "ekki_nefnt") or not b or _s(NEI_STAEDI, b):
        return None
    if v == "bilskur" and _s(r"bílskúr", b):
        return dict(gerd="bilskur")
    if v in ("staedi_bilakjallara", "staedi") and _s(GERD_KJ, b) and _s(JA_STAEDI, b):
        return dict(gerd="staedi_bilakjallara")
    if v == "staedi" and _s(r"bílskúr", t):  # a1: „besta gildi" er þá ekki stæði
        return None
    if v == "staedi" and not _s(GERD_KJ, b) and _s(r"stæð", b) and _s(JA_STAEDI, b) and not _s(r"sameig|óskipt|við húsið|á lóð|næg", b):
        return dict(gerd="staedi")
    return None


def thvottahus(s, t):
    v, b = s.get("thvottahus"), s.get("thvottahus_brot") or ""
    if v not in ("innan", "utan") or not _s(r"þvottah|þvottaherb", b) or len(b) < 12:
        return None
    if _s(r"tengi|tengt|tenging|aðstað|gert ráð|soga|borðplöt|þvottavél|bað|sturt", b):
        return None
    if v == "utan" and not _s(r"sameig", b):  # a1: „í kjallara" getur verið innan eignar
        return None
    return dict(stadsetning=v)


def ja(k, stofn, nei=None):
    def f(s, t):
        b = s.get(k + "_brot") or ""
        if s.get(k) != "ja" or not _s(stofn, b) or (nei and _s(nei, b)):
            return None
        return dict(til=True)
    return f


def lodargerd(s, t):
    v, b = s.get("lodargerd"), s.get("lodargerd_brot") or ""
    if v == "serlod" and _s(r"sérlóð|sér lóð|sérafnota|sérnota", b):
        return dict(gerd=v)
    if v == "einkalod" and _s(r"einkalóð|einka lóð", b):
        return dict(gerd=v)
    return None


ATT = {"sudur": r"suð\w*|sunn\w*", "austur_vestur": r"aust\w*|vest\w*", "nordur": r"norð\w*"}


def lodarat(s, t):
    """a1: átt verður að tengjast lóð eða garði beint; blandað og samsettar áttir út."""
    v, b = s.get("lodarat"), s.get("lodarat_brot") or ""
    if v not in ATT or _s(r"sval|verönd|pall|hurð|útgengt|enda|hlíð|norð\w*(vest|aust)|suð\w* og|og \w*(vest|aust|norð)", b):
        return None
    m = ATT[v]
    if not (_s(rf"\b({m})[- ]?(lóð|garð)", b) or _s(rf"\b(lóð|garð)\w*\s+(sem\s+)?(snýr\s+|er\s+|liggur\s+)?(til|í|á móti|móti)\s+({m})", b)):
        return None
    return dict(att=v)


UT = {"sjor": r"sjó|sjáv|haf|sund|flóa|flóann|fjörð|fjörðinn|vog|höfn|strönd|Faxa",
      "fjoll": r"fjall|fjöll|Esj|jökul|Keili|Akrafjall|Skarðsheið|Hengil",
      "borg": r"borg|bæinn|miðbæ"}


def utsyni(s, t):
    b = s.get("utsyni_brot") or ""
    if not _s(r"sýn", b):
        return None
    L = [u for u in (s.get("utsyni") or []) if u in UT and _s(UT[u], b)]
    return dict(tegundir=sorted(L)) if L else None


# a1: vínilparket er ekki parket
GOLF = {"parket": r"(?<!vinil)(?<!vínil)(?<!vinyl)(?<!vínyl)(?<!viníl)(?<!vinil-)(?<!vínil-)parket", "flisar": r"flís", "teppi": r"teppi"}


def golfefni(s, t):
    L = [g for g in (s.get("golfefni") or []) if g in GOLF and _s(GOLF[g], t)]
    return dict(tegundir=sorted(L)) if L else None


HERB = {2: r"2ja|2\s|tveggja|tvegga", 3: r"3ja|3\s|þriggja", 4: r"4ra|4\s|fjögurra", 5: r"5\s|fimm", 6: r"6\s|sex", 7: r"7\s|sjö"}


def herbergi(s, t):
    """a1: Haiku les svefnherbergi ýmist sem herbergi. Aðeins „N herbergja" í tilvitnun, og sama tala."""
    n = s.get("herbergi_i_texta") or 0
    b = s.get("herbergi_brot") or ""
    if n not in HERB or _s(r"svefnh", b) or not _s(rf"({HERB[n]})[- ]*herbergja", b):
        return None
    return dict(fjoldi=n)


BAD2 = {2: r"tvö|2", 3: r"þrjú|3", 4: r"fjögur|4"}
FLEIRI = r"tvö bað|2 bað|þrjú bað|3 bað|annað bað|auka ?bað|bæði bað|baðherbergin|baðherbergjum|baðherbergi 2|baðherbergi ii|aukaíbúð|stúdíó|efri hæð|neðri hæð|tvö salerni|gestasalerni"


def badherb(s, t):
    """a1: talning. 2+ aðeins með tölu fyrir framan orðið; 1 aðeins ef ekkert í texta bendir á fleiri eða aukarými."""
    n = s.get("badherbergi_i_texta") or 0
    b = s.get("badherbergi_fjoldi_brot") or ""
    if n in BAD2:
        if _s(r"aukaíbúð|stúdíó|gesta|salerni|snyrting", b) or not _s(rf"({BAD2[n]})\s+(\w+\s+)?baðherb", b):
            return None
        return dict(fjoldi=n)
    if n != 1 or not _s(r"baðherb", b) or _s(FLEIRI, t):
        return None
    return dict(fjoldi=1)


EIG = {"serinngangur": ja("serinngangur", r"sér ?inng|sérinng", r"kjallar|aukaíbúð|stúdíó|geymsl|þvottah|bílskúr|útleigu|leigu|hlið|neðri hæð"),
       "lofthaed": ja("lofthaed", r"(mikil|mikla|miklum|aukin|aukna|hárri|óvenju|tvöf|gríðar|há )\w*\s*(\w+\s+)?lofth|hátt til lofts|lofth\w* (er |eru )?(\w+ )?\d[,.]\d", r"góð|bílskúr|skúr|kjallar|geymsl"),
       "heitur_pottur": ja("heitur_pottur", r"pott", r"teng|lagn|lögn|leggja|gert ráð|undirbú|möguleik|sameig"),
       "arinn": ja("arinn", r"\barin|\barni\b|kamín|eldstæð|viðarofn"),
       "opid_rymi": ja("opid_rymi", r"\bop(ið|in|nu|na)\s+(\w+\s+)?(rým|skipulag)|\balrým|\bopi[ðn] (á )?(milli|við|inn|í|yfir)"),
       "adgengi_hjolastols": ja("adgengi_hjolastols", r"hjólast|hreyfihaml|fatlað", r"stæð|stétt|\bfyrir hreyfihamlaða$"),
       "ev_hledsla": ja("ev_hledsla", r"hleðsl", r"teng|lagnaleið|undirbú|möguleik|dreifibox|gert ráð|hægt að|fyrirhug|lagnir|lögn|ídrátt|leggja|lagt"),
       "endaeining": ja("endaeining", r"enda ?(raðh|íbúð|eining|hús|parh)|í enda|endaíb", r"götu|botnlang"),
       "bilskur_staedi": bilskur, "thvottahus": thvottahus, "lodargerd": lodargerd, "lodarat": lodarat,
       "utsyni": utsyni, "golfefni": golfefni, "herbergi": herbergi, "badherbergi": badherb}


def eigindi(s, t):
    u = {}
    for k, f in EIG.items():
        v = f(s, t)
        if v is not None:
            u[k] = v
    return u


# ---- ástand: skema 101 ----
STOFN = {"eldhus": r"eldh|innrétt", "badherbergi": r"bað|salerni|sturt", "golfefni": r"gólf|parket|flís|teppi", "gluggar": r"glugg|gler",
         "lagnir": r"lagn|lögn|dren|skólp|ofn|rafmagnst|raflög|raflagn|tafl|klóak", "thak": r"þak",
         "almennt": r"endurnýj|uppger|standsett|uppgert|tekin í gegn|taka í gegn|tekið í gegn"}
VIDHALD = r"mála|málun|málað|filma|filmu|yfirfar|lagfær|viðgerð|gert við|þrif|nýmál|nýleg|nýrri|vel við|gott viðhald|viðhald"
ALMENNT_HLUTI = r"eldh|bað|gólf|parket|glugg|þak|lagn|lögn|innrétt"


def astand(s, t, k):
    h = s.get(k) or {}
    b = h.get("brot") or ""
    if h.get("stada") != "endurnyjad" or not _s(STOFN[k], b) or _s(VIDHALD, b):
        return None
    if k == "lagnir" and _s(r"snjóbræðsl|tröpp|stétt|plan|bílaplan", b):  # a1: utanhúss hitalagnir
        return None
    if k == "almennt" and (_s(ALMENNT_HLUTI, b) or not _s(r"íbúð|eign|hús|allt|öll|heild", b)):
        return None
    return dict(stada="endurnyjad")


def ar(s, t, k):
    h = s.get(k) or {}
    a = h.get("ar")
    return a if a and 1950 <= a <= 2027 and str(a) in (h.get("brot") or "") else None


def oskrad(s, t):
    b = s.get("oskrad_brot") or ""
    if s.get("oskrad") != "ja" or _s(r"stæð|bílast|bílskúr|bílgeymsl|bílageymsl|geymsl|skúr|útihús|sameiginleg", b):
        return None
    if not _s(r"óskráð|ekki skráð|ekki inni|ekki innifal|utan|ekki í|ekki talin|ekki með|ótalin", b):
        return None
    m = s.get("oskrad_m2")
    return dict(m2=m if m and str(int(m)) in b else None)
