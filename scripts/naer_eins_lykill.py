"""naer_eins_lykill.py — HREINSAÐI LYKILLINN (K2 úr cc153). cc156, 13.08.2026.

EITT FALL BER LYKILINN. `lykill(texti)` er eina leiðin að honum — hvorki
mæliforrit né framleiðslulína mega endurgera hann (sbr.
`feedback_merki_verdur_ad_lesast_ur_einu_falli`). cc153-mælitækið
(`D:\\_audit\\cc153_naer_eins\\naer_eins_lib.py`) er FROSIÐ mæliskjal þeirrar
lotu og ber gömlu regluna; það er sagan, ekki lifandi hegðun. Breytist lykillinn
breytist hann HÉR.

HEIMILD: `docs/fable_prep/audits/NAER_EINS_CC153_20260813.md` lið 4.2/4.3 (K2) og
`NAER_EINS_CC156_20260813.md` lið 1 (lagfæringarnar tvær hér að neðan).

──────────────────────────────────────────────────────────────────────────────
LAGFÆRING 1 — `_OPID`-SPÖNNIN (latent galli sem cc153 bókaði)
──────────────────────────────────────────────────────────────────────────────
cc153 lið 4.3 bókaði: *„`_OPID` gleypir allt að 120 stafi á eftir `nánari
upplýsingar` / `upplýsingar veitir` og 80 á eftir `hafðu samband` / `hringdu`.
Mælt á öllum 13.652 textum fjarlægir hún ástandsorð úr 77 þeirra (0,56
prósent) ... Rétta lagfæringin er að binda spönnina við setningarlok, ekki við
stafafjölda."*

**SÚ FORSKRIFT VAR PRÓFUÐ OG HÚN FELLUR.** Mælt á sama 13.652-texta þýði:

    kostur                              textar sem missa ástandsorð
    F0  í dag, [^.]{0,120}                              77
    F1  setningarlok EIN (forskrift cc153)             160   <- VERRA
    F2  haus einn, engin spönn                           0
    F3  setningarlok + EFNISVÖRN                         0

Ástæðan er mæld, ekki ályktuð: CTA-setningin er í þessum textum að jafnaði
LENGRI en 120 stafir (p50 spannar 94, p90 247, max 729), svo 120-stafa glugginn
var í raun að VERJA innihaldið með því að stoppa of snemma. Að binda við
setningarlok étur því MEIRA, ekki minna:

    «nánari upplýsingar um þær hjá fasteignasölu, en rétt er að nefna að búið
     er að endurnýja dren og skolplagnir ásamt neysluvatnslögnum.»   (133 stafir)

Reglan sem stenst er **setningarlok + efnisvörn**: spönnin nær að setningarlokum
(`[.!?]` eða textalok) EN er felld niður ef hún ber ástands- eða verðorð. Þá er
hún ekki CTA heldur innihaldssetning sem byrjar á CTA-orðalagi. Vörnin gerir
hreinsunina fail-closed: í vafa stendur textinn, lykillinn verður STRANGARI og
K2 fellir færri raðir — aldrei öfugt.

──────────────────────────────────────────────────────────────────────────────
LAGFÆRING 2 — STÆRÐARTÖLUVÖRNIN (cc156 fann; cc153 mældi þennan ás ALDREI)
──────────────────────────────────────────────────────────────────────────────
cc153 lið 4.3 sannreyndi K2 á HRÁA mismuninum og fékk „0 raðir bera ORD_ASTAND
og 0 bera ORD_VERD". Sú mæling var rétt á þeim tveimur ásum — en orðalistarnir
þekkja ENGA fermetra, svo hún gat ekki séð þriðja ásinn. Mælt hér:

    textar sem TAPA aukastafatölu í hreinsun:  4.047 af 13.652 (29,64 prósent)
      sökudólgar:  _DAGS 3.718 · _MILLI 364 · _OPID 129 · _URL 5

`_DAGS` (`\\d{1,2}[./]\\d{1,2}`) les „80.1 fm" sem dagsetninguna 80.1 og étur
hana. Afleiðingin var MÆLD á K2 sjálfum: **2 af 172 K2-röðum cc153 fella saman
texta sem bera ÓLÍKAR stærðartölur** (80,0 gegn 80,1 og 90,2 gegn 98,0) — sama
kross-einingar-hrunið og cc153 lið 3.6 lýsir, komið inn um bakdyrnar á
hreinsuninni. Það er raunverulegt tap sem stóð ómælt í kostatöflunni.

Vörnin: aukastafatölur eru **dulbúnar fyrir hreinsun og afhjúpaðar eftir hana**,
svo ENGIN regla geti étið þær. Hún er á lyklinum í heild, ekki plástur á hverja
reglu fyrir sig — fjórar reglur átu tölur og fimmta myndi gera það líka.

    kostur                          ástandstap  verðtap  stærðartap    K2  kross
    gamla reglan (cc153)                    77       45       4.047   172      2
    + efnisvörn á spönn                      0        0       4.149   199      4
    + stærðarvörn (dulbúningur)              0        0         279   194      0
    + spönnin ver dulbúninginn líka          0        0          21   193      0  <- VALIÐ

Síðasta línan er hér af því sú næstsíðasta DUGÐI EKKI og það var mælt: CTA-
spönnin gleypti dulbúna tökenið í heilu lagi, svo `_afhjupa` fann ekkert að
skila. Dulbúningurinn ver töluna fyrir TÖLUREGLUNUM en ekki fyrir spönn sem
étur umhverfi hennar — sbr. `feedback_hlid_a_maelingu_en_ekki_a_skrifleid`.
Afgangurinn 21 (15 fermetratölur) liggur inni í vefslóðum (`nz=17.00`) og í
tölum utan `\\d{1,4}[.,]\\d{1,2}`-forms; vefslóðir EIGA að hverfa.

NIÐURSTAÐA: K2 fer úr 172 í **193 raðir á cc153-þýðinu** — fleiri felldar OG
öll þrjú mældu töpin færð í núll. Viðbótin (+25/−3, `02_vidbot_rynt.txt`) er
undantekningarlaust fasteignasalanöfn, símanúmer og bókunarorðalag; ENGIN
viðbótarröð ber eigindi. Talan sem gildir er hins vegar sú sem mælist á
LIFANDI biðröð við framkvæmd — sjá `k2_sia()` í `extraction_engine.py`.
"""
from __future__ import annotations

import hashlib
import html
import re
import unicodedata

# ── NORM — ÓBREYTT frá cc153 (skref 1-6, í þessari röð) ──────────────────────
_BLOCK = re.compile(r"</?(?:br|p|li|ul|ol|div|h[1-6]|tr|td)\b[^>]*>", re.I)
_TAG = re.compile(r"<[^>]*>")
_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    """1 blokkatög -> bil · 2 önnur tög burt · 3 entity-afkóðun · 4 NBSP/NFC ·
    5 lágstafir · 6 bil samandregin."""
    s = _BLOCK.sub(" ", s or "")
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = unicodedata.normalize("NFC", s).replace("\xa0", " ").replace("\u200b", " ")
    s = s.lower()
    return _WS.sub(" ", s).strip()


# ── HREINSUN ─────────────────────────────────────────────────────────────────
_URL = re.compile(r"https?://\S+|www\.\S+")
_MAIL = re.compile(r"[\w.+-]+@[\w.-]+")
_SIMI = re.compile(r"\b(?:s|sími|gsm|tel)\s*[:.]?\s*\d[\d\s-]{5,}", re.I)
_SIMI2 = re.compile(r"\b\d{3}[\s-]\d{4}\b")
_DAGS = re.compile(r"\b\d{1,2}\s*[./]\s*\d{1,2}(?:\s*[./]\s*\d{2,4})?\b")
_KLST = re.compile(r"\b\d{1,2}[:.]\d{2}\b")
_MILLI = re.compile(r"\b\d{1,2}\s*[-–]\s*\d{1,2}\b")
_VIKUD = re.compile(
    r"\b(mánudag|þriðjudag|miðvikudag|fimmtudag|föstudag|laugardag|sunnudag)\w*", re.I)
_MANUD = re.compile(
    r"\b(janúar|febrúar|mars|apríl|maí|júní|júlí|ágúst|september|október|"
    r"nóvember|desember)\b", re.I)

# CTA-hausar sem draga spönn á eftir sér (LAGFÆRING 1)
_CTA_HAUS = r"(?:nánari upplýsingar|upplýsingar veitir|hafðu samband|hringdu)"
_CTA_SPONN = re.compile(_CTA_HAUS + r"[^.!?]*(?:[.!?]|$)", re.I)
# CTA-orðalag án spannar — óbreytt frá cc153
_CTA_STAKT = re.compile(
    r"(opið hús|opid hus|bókun skoðun\w*|bóka skoðun|panta skoðun|"
    r"verið velkomin\w*|allir velkomnir|\*{2,})", re.I)

# EFNISVÖRNIN — orðin sem fella spönnina. Sami orðaforði og cc153 lið 3.1
# (ORD_ASTAND ∪ ORD_VERD), skrifaður sem ein þýdd regla því hún er keyrð á
# hverri spönn (16.720 spannir á fullri umferð) og `tokset()`-samanburður per
# spönn var mælanlega hægari án þess að breyta niðurstöðu.
_VORN_ORD = (
    r"endurnýj\w*|uppger\w*|standset\w*|lagfær\w*|viðger\w*|viðhald\w*|"
    r"mál(?:að|uð|aður|ning)|nýmál\w*|sprunguviðgerðir|skipt(?:um)?|nýleg\w*|"
    r"yfirfar\w*|endurbæt\w*|múrviðgerðir|þakviðger\w*|gluggaskipti|glerskipti|"
    r"raflagnir|lagnir|dren|einangr\w*|klæt+\w*|klæðning\w*|steinað|múrað|"
    r"flísalag\w*|flísalögð|parketlagt|innrétting\w*|eldhúsinnrétting|"
    r"baðinnrétting|hitakerfi|ofnar|ofnalagnir|þakjárn|þakpappi|ástand\w*|"
    r"verð\w*|ásett\w*|verðlækkun|lækka\w*|lækkun|tilboð\w*|kauptilboð|"
    r"milljón\w*|millj|mkr|kr|krónur|króna|verðtilboð|staðgreiðslu"
)
_VORN = re.compile(r"\b(?:" + _VORN_ORD + r")\b", re.I)

# STÆRÐARTÖLUVÖRNIN (LAGFÆRING 2). Dulbúningurinn ber ENGA tölustafi, svo engin
# af tölureglunum að ofan getur gripið hann.
_AUKASTAFATALA = re.compile(r"\b\d{1,4}[.,]\d{1,2}\b")
_DULBUID = re.compile("\x01([a-j]+)\x02")
_TOLUSTAFIR = "abcdefghij"


def _fela(m, geymd):
    geymd.append(m.group(0))
    kod = "".join(_TOLUSTAFIR[int(c)] for c in str(len(geymd) - 1))
    return " \x01" + kod + "\x02 "


def _afhjupa(m, geymd):
    return geymd[int("".join(str(_TOLUSTAFIR.index(c)) for c in m.group(1)))]


def _cta_sponn(m):
    """Fellir CTA-spönnina NIÐUR ef hún ber INNIHALD — fail-closed.

    Innihald er tvennt og hvort tveggja er mælt (LAGFÆRING 1 + 2):
      * ástands-/verðorð (`_VORN`)
      * dulbúin stærðartala (`\\x01`) — spönnin étur dulbúninginn í heilu lagi
        ef ekkert stöðvar hana, og þá skilar `_afhjupa` engu. Mælt: án þessarar
        greinar tapa 279 textar stærðartölu (241 þeirra FERMETRATÖLU); með henni
        21 (15). Dulbúningurinn einn ver töluna fyrir TÖLUREGLUNUM, ekki fyrir
        spönn sem gleypir hana með umhverfinu.
    """
    t = m.group(0)
    return t if (_VORN.search(t) or "\x01" in t) else " "


def hreinsa(s_norm: str) -> str:
    """HREINSUN ofan á NORM: dagsetningar, klukka, opið hús, CTA og tengiliðir
    burt. Stærðartölur eru varðar allan tímann (LAGFÆRING 2)."""
    geymd = []
    s = _AUKASTAFATALA.sub(lambda m: _fela(m, geymd), s_norm)
    for rx in (_URL, _MAIL, _SIMI, _SIMI2):
        s = rx.sub(" ", s)
    s = _CTA_STAKT.sub(" ", s)
    s = _CTA_SPONN.sub(_cta_sponn, s)
    for rx in (_VIKUD, _MANUD, _DAGS, _KLST, _MILLI):
        s = rx.sub(" ", s)
    s = _DULBUID.sub(lambda m: _afhjupa(m, geymd), s)
    return _WS.sub(" ", s).strip()


def lykill(texti: str) -> str:
    """HREINSAÐI LYKILLINN — 12 stafa md5, sama form og `lysing_hash`.

    Þetta er EINA leiðin að lyklinum. Kalla hann, ekki endurgera hann.
    """
    return hashlib.md5(hreinsa(norm(texti)).encode("utf-8")).hexdigest()[:12]
