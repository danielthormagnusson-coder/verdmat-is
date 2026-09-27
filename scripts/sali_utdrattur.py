"""sali_utdrattur.py — cc213: útdráttur nafns fasteignasala úr auglýsingatexta (mbl `lysing`).

Mælt í cc212b (D:\\_audit\\cc212b_auglysingagat\\SKIL_CC212B.md §4): þekja 84,9–87,2 % eignaðra
sölna 2026-07/08; handrýni 100 raða 86 alveg réttar, 1 röng manneskja. Þessi útgáfa (sali_v3)
ber lagfæringar 1–3 úr þeirri handrýni:
  1. starfsheiti/menntun klippt aftan af nafni („… Lögiltur", „… Lg.", „… Viðskiptafræðingur");
  2. eins-orðs fornafn (oft þágufall: „Herdísi") sameinað fullu nafni í sömu auglýsingu;
  3. samsvörun við nafnaskrá hert: eftirnafn þarf að falla saman eftir STOFNUN (beygingarendingar
     klipptar, -syni→-son, -dóttur→-dóttir), ekki 5 stafa forskeyti (fellir „Guðbjörg Helga" ≠
     „Guðrún … Helgadóttir").

Frambjóðandi telst sali aðeins ef (i) hann fylgir starfsheiti í auglýsingunni og er ≥2 orð,
(ii) er í nafnaskrá stofunnar (nöfn sem standa ≥2× með starfsheiti í safninu), eða (iii) er
fornafn sem persónulegt netfang í sömu auglýsingu staðfestir. Hliðið fellir falsnöfn á borð
við „Vill" (úr „Vill X fasteignasala því benda…") og nöfn framkvæmdaraðila.

Engin gögn úr prod í þessari skrá; prófin (sali_utdrattur_test.py) nota tilbúin nöfn.
"""
from __future__ import annotations

import collections
import html
import re
import unicodedata

UTGAFA = "sali_v3"

UP = "A-ZÁÐÉÍÓÚÝÞÆÖ"
LO = "a-záðéíóúýþæö"
_W = rf"(?:[{UP}][{LO}]+(?:-[{UP}][{LO}]+)?|[{UP}]{{2,}}(?:-[{UP}]{{2,}})?|[{UP}][{LO}]{{0,4}}\.)"
_NAME = rf"({_W}(?:\s+{_W}){{0,3}})"
_TITLE = (r"(?i:löggilt\w*\s+fasteigna\w*|lögg\.?\s*fast\w*|lgf\.?s?\b\.?|lgfs\.?|lfs\b\.?|lg\.\s*fasteigna\w*"
          r"|fasteignasali\b|fasteignasalar\b|nemi\s+(?:til|í)\s+löggilding\w*|aðstoðarm\w+\s+fasteignasala"
          r"|sölufulltrú\w*|sölum[aö]\w*|sölustj\w*\.?|viðskiptastjór\w*|lögmaður\s+og\s+l\w*)")

# Orð sem aldrei eru hluti nafns (haus, starfsheiti, menntun, algeng falsnöfn úr handrýni cc212b)
_STOP = {
    "Nánari", "Upplýsingar", "Allar", "Frekari", "Eignin", "Fasteignasalan", "Fasteignasala", "Kaupandi",
    "Seljandi", "Hafið", "Hafðu", "Samband", "Sjá", "Um", "Og", "OG", "Veitir", "Veita", "Sími", "Gsm", "GSM",
    "S", "Netfang", "Hér", "Íbúðin", "Húsið", "Í", "Á", "Við", "Einkasala", "Einkasölu", "Kynnir", "Kynna",
    "Fasteignir", "Fasteignamiðlun", "Ehf", "EHF", "RE", "MAX", "Nánar", "Bókið", "Bókaðu", "Skoðun", "Opið",
    "Heimasíða", "Tengiliður", "Sölumaður", "Bókun", "Hjá", "Eða", "Email", "Ásamt", "FÆRÐU", "HJÁ",
    "NÁNARI", "UPPLÝSINGAR", "ALLAR", "ALLARU", "VEITIR", "VEITA", "BÓKIÐ", "SKOÐUN", "LIND", "FASTEIGNASALA",
    "KYNNA", "KYNNIR", "Uppl", "Vill", "Verk", "Tok", "Félagi", "Nýtt", "Glæsileg", "Einstaklega", "SELD",
    "EIGNIN", "ER",
}
# Starfsheiti/menntun sem klippast aftan af (lagfæring 1)
_TITLE_WORDS = {
    "löggiltur", "lögiltur", "löggildur", "lögg", "lg", "lgf", "lgfs", "lfs", "fasteignasali", "fasteignasala",
    "viðskiptafræðingur", "viðskfr", "lögfræðingur", "lögmaður", "hrl", "hdl", "ml", "verkfræðingur",
    "sölustjóri", "sölustj", "fasteigna", "skipasali",
}

_CF = re.compile(r'data-cfemail=\\?"([0-9a-f]+)\\?"')
_EM = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[a-z]{2,}")
_GENERIC_LOCAL = re.compile(
    r"^(info|sala|solu|soluskra|eignir|eign|fasteign\w*|office|skrifstofa|allir|kaupa|torg|senter|mottaka|"
    r"fyrirspurnir|hallo|postur|netfang)$", re.I)


def plain(t) -> str:
    if not isinstance(t, str):
        return ""
    t = re.sub(r"<[^>]+>", " ", html.unescape(t))
    return re.sub(r"\s+", " ", t)


def fold(s: str) -> str:
    s = s.lower().replace("ð", "d").replace("þ", "th").replace("æ", "ae").replace("ö", "o")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


_TITLE_FOLD = frozenset(fold(w) for w in _TITLE_WORDS)


def _cf_decode(h: str) -> str:
    k = int(h[:2], 16)
    return "".join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))


def emails(text) -> list[str]:
    if not isinstance(text, str):
        return []
    e = {x.lower() for x in _EM.findall(html.unescape(text))}
    for h in _CF.findall(text):
        try:
            e.add(_cf_decode(h).lower())
        except ValueError:
            pass
    return sorted(x for x in e if not x.endswith((".png", ".jpg")))


def personal_emails(text, agency_locals: frozenset[str] = frozenset()) -> list[str]:
    """Netföng sem líta út fyrir að vera einstaklings: ekki almennt pósthólf né heiti stofu."""
    out = []
    for e in emails(text):
        loc = e.split("@")[0]
        if _GENERIC_LOCAL.match(loc) or fold(loc) in agency_locals:
            continue
        out.append(e)
    return out


def _stem(tok: str) -> str:
    f = fold(tok.strip("."))
    f = re.sub(r"syni$", "son", f)
    f = re.sub(r"dottur$", "dottir", f)
    return re.sub(r"[aiuy]+$", "", f) if len(f) > 3 else f


def clean(n: str, agency_words: frozenset[str]) -> str | None:
    w = [x for x in n.split() if x.strip(".") not in _STOP and fold(x.strip(".")) not in agency_words]
    while w and fold(w[-1].strip(".")) in _TITLE_FOLD:          # lagfæring 1
        w = w[:-1]
    w = [x for x in w if fold(x.strip(".")) not in _TITLE_FOLD]
    if not w:
        return None
    s = " ".join(w)
    if sum(c.isupper() for c in s) > 0.6 * max(1, sum(c.isalpha() for c in s)):
        s = " ".join(x.capitalize() for x in s.split())
    return s if len(s) >= 3 and not re.search(r"\d", s) else None


PATS = [
    ("P1", re.compile(_NAME + r"\s*[,(/\-–]?\s*(?:\(\s*)?" + _TITLE)),
    ("P2", re.compile(r"(?:\b(?:og|OG|ásamt|ÁSAMT)|\s[/\-–])\s+" + _NAME + r"(?:\s*[,(]?\s*" + _TITLE + r")?\s*,?\s*(?i:kynn)")),
    ("P2b", re.compile(_NAME + r"\s+(?:og|OG)\s+[^.]{2,45}?\s+(?i:kynn)")),
    ("P3", re.compile(r"(?i:upplýsingar|uppl\.|bókun\s+skoðunar|skoðun|samband\s+við)[^.]{0,50}?"
                      r"(?i:veitir|veita|gefur|gefa|færðu\s+hjá|hjá|við|:)\s*:?\s*" + _NAME)),
    ("P4", re.compile(r"(?i:sölumaður|tengiliður|umsjón(?:armaður)?|söluaðili|ábyrgðarmaður)\s*:\s*" + _NAME)),
    ("P5", re.compile(_NAME + r"\s*[,\-–|/]\s*(?:(?i:s\.|sími|gsm|s)\s*:?\s*)?(?:\d{3}[\s\-]?\d{4}|[a-z0-9._\-]+@)")),
]


def candidates(text, agency_words: frozenset[str] = frozenset()) -> list[tuple[str, str]]:
    p = plain(text)
    out = []
    for lbl, rx in PATS:
        for m in rx.finditer(p):
            n = clean(m.group(1), agency_words)
            if n:
                out.append((lbl, n))
    return out


def same_person(a: str, b: str) -> bool:
    """Sama manneskja? Forskeyti hvort af öðru, EÐA fornafnsstofn eins + eftirnafnsstofn eins (lagfæring 3)."""
    fa, fb = fold(a), fold(b)
    if fa.startswith(fb) or fb.startswith(fa):
        return True
    ta, tb = a.split(), b.split()
    if len(ta) == 1 or len(tb) == 1:
        return False
    if _stem(ta[0])[:3] != _stem(tb[0])[:3]:
        return False
    return _stem(ta[-1]) == _stem(tb[-1])


class Nafnaskra:
    """Nafnaskrá per stofu: grunnmynd = lengsta, svo algengasta mynd."""

    def __init__(self):
        self.teljari: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        self.grunn: dict[str, list[str]] = {}

    def baeta_vid(self, stofa: str, nafn: str) -> None:
        self.teljari[stofa][nafn] += 1

    def smida(self, min_n: int = 2) -> None:
        for stofa, c in self.teljari.items():
            reps: list[str] = []
            for n in sorted(c, key=lambda n: (-len(n.split()), -c[n], n)):
                if c[n] < min_n:
                    continue
                if not any(same_person(n, r) for r in reps):
                    reps.append(n)
            self.grunn[stofa] = reps

    def fletta(self, stofa: str, nafn: str) -> str | None:
        for r in self.grunn.get(stofa, []):
            if same_person(nafn, r):
                return r
        return None


def extract(text, stofa: str, skra: Nafnaskra | None, agency_words: frozenset[str] = frozenset(),
            agency_locals: frozenset[str] = frozenset()) -> list[str]:
    """Samþykkt nöfn (grunnmynd), í röð fyrstu komu, án tvítekninga."""
    locs = [fold(e.split("@")[0]) for e in personal_emails(text, agency_locals)]
    out: list[str] = []
    for lbl, n in candidates(text, agency_words):
        c = skra.fletta(stofa, n) if skra is not None else None
        if c is None and lbl == "P1" and len(n.split()) >= 2:
            c = n
        if c is None and locs:
            f0 = fold(n.split()[0])
            if len(f0) >= 3 and any(l.startswith(f0[:4]) or f0.startswith(l[:4]) for l in locs if len(l) >= 3):
                c = n
        if not c or any(same_person(c, o) for o in out):
            continue
        out.append(c)
    # lagfæring 2: eins-orðs nafn sem er fornafn (þ.m.t. beygt) annars nafns í sömu auglýsingu fellur
    multi = [o for o in out if len(o.split()) > 1]
    return [o for o in out if len(o.split()) > 1
            or not any(_stem(o)[:4] == _stem(m.split()[0])[:4] for m in multi)]
