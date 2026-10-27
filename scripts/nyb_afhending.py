"""cc283 (lið 5) — frysting afhendinga nýbyggingagagna til þriðja aðila (fjölmiðla, samstarfsaðila).

  python scripts/nyb_afhending.py --vidtakandi VB --ur-db [--utgafa cc224-v9] [--svaedi hbs|allt] [--virk]
  python scripts/nyb_afhending.py --vidtakandi VB --farmur DIR      # DIR/farmur.pkl úr cc224 --dryrun (prófun)

Hver afhending vistast ÓBREYTANLEG í D:\\_audit\\afhent\\<YYYY-MM-DD>_<viðtakandi>\\ (sé mappan til: _2, _3, …; ekkert er
nokkurn tíma yfirskrifað). Í henni:
  nybyggingar_<dags>.xlsx   taflan sem fer út (Verkefni + Skýringar + Lýsigögn) — þrískipting, aldrei „óseld"
  verkefni.csv, einingar.csv, farmur.pkl   nákvæmur farmur keyrslunnar (endurgeranleiki; fer EKKI út)
  MANIFEST.json             viðtakandi, keyrsla_id, útgáfa, data_through, listings_snapshot, kóða-hash byggingar
                            (úr nybygging_keyrslur) + hash þessarar skriftu, sha256 hverrar skrár, niðurstaða H-NYB
Allt er fyrst skrifað í falda bráðabirgðamöppu; H-NYB (cc224.hlid_nyb) keyrir á farminum OG á texta xlsx-skjalsins;
aðeins ef hvort tveggja stenst er mappan endurnefnd í lokanafn og skrárnar gerðar read-only. Falli hliðið er
bráðabirgðamöppunni eytt og rc = 4 — engin afhending verður til.
Engin sending: skriftan býr aðeins til skjalið. Sending er handvirk og skráist ekki hér.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cc224_nybygging_verkefni as M  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ROT = Path(r"D:\_audit\afhent")
FORSALA_SKYRING = (
    "Forsala sést ekki í kaupskrá: kaupsamningi um íbúð er ekki þinglýst fyrr en hún er orðin sjálfstæð eign — eftir "
    "eignaskiptayfirlýsingu og þegar húsið er komið á þinglýsanlegt stig. Íbúð sem er seld í forsölu birtist því ekki "
    "í kaupskrá HMS fyrr en við þinglýsingu, oft við afhendingu. Í húsum þar sem svo háttar (óskipt fastanúmer, "
    "byggingarstig B0–B2 eða óskráð, fastanúmer án heimilisfangs, eða ekkert þinglýst í húsinu frá 2021) eru aðeins "
    "þinglýstar sölur og virkar auglýsingar taldar; íbúðir sem hvorki eru þinglýstar né auglýstar eru ekki taldar.")
ASTAEDUR = dict(oskipt="óskipt fastanúmer", b0_b2="byggingarstig B0–B2/óskráð", an_heimilisfangs="fastanúmer án heimilisfangs",
                hus_0_samninga="ekkert þinglýst í húsinu frá 2021")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kodi_afhendingar() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]


def lesa_db(utgafa):
    c = M.tengja()
    try:
        cur = c.cursor()
        cur.execute("SET TRANSACTION READ ONLY")
        V = pd.read_sql(f"select {', '.join(M.VCOLS)}, keyrsla_id from semantic.nybygging_verkefni where utgafa = %(u)s", c, params=dict(u=utgafa))
        E = pd.read_sql(f"select {', '.join(M.ECOLS)} from semantic.nybygging_einingar where utgafa = %(u)s", c, params=dict(u=utgafa))
        kid = sorted(V.keyrsla_id.unique())
        if len(kid) != 1:
            raise SystemExit(f"[STOPP] útgáfa {utgafa} ber {len(kid)} keyrslur ({kid}) — afhending krefst einnar")
        K = pd.read_sql("select keyrsla_id, data_through, listings_snapshot, kodi_hash, md5_verkefni, md5_einingar "
                        "from semantic.nybygging_keyrslur where keyrsla_id = %(k)s", c, params=dict(k=int(kid[0])))
        HBS = set(pd.read_sql("select postnr from semantic.verdvakt_hbs_postnr", c).postnr.astype(int))
        c.rollback()
    finally:
        c.close()
    k = K.iloc[0]
    return dict(V=V.drop(columns="keyrsla_id"), E=E, S=None, utgafa=utgafa, keyrsla_id=int(k.keyrsla_id),
                data_through=k.data_through, snap=k.listings_snapshot, kodi_hash=k.kodi_hash,
                md5=dict(verkefni=k.md5_verkefni, einingar=k.md5_einingar)), HBS


def lesa_farmur(d: Path):
    F = pd.read_pickle(d / "farmur.pkl")
    F["keyrsla_id"] = None   # dryrun: aldrei skrifuð í nybygging_keyrslur
    c = M.tengja()
    try:
        c.cursor().execute("SET TRANSACTION READ ONLY")
        HBS = set(pd.read_sql("select postnr from semantic.verdvakt_hbs_postnr", c).postnr.astype(int))
        c.rollback()
    finally:
        c.close()
    return F, HBS


def tafla(V, HBS, svaedi, virk):
    """Verkefnatafla afhendingarinnar — sömu teljarar og /nybyggingar (sýnilegur hluti = hús þar sem kaupskrá sker úr)."""
    V = V.copy()
    V["hbs"] = V.postnr.fillna(0).astype(int).isin(HBS)
    if svaedi == "hbs":
        V = V[V.hbs]
    if virk:
        V = V[V.n_virkar > 0]
    y_s = V.n_einingar - V.n_forsala_ibudir
    T = pd.DataFrame({
        "Verkefni": V.heiti, "Póstnúmer": V.postnr, "Sveitarfélag": V.sveitarfelag,
        "Íbúðir alls": V.n_einingar,
        "Þinglýst seldar": V.n_seld,
        "Auglýstar til sölu": V.n_auglyst,
        "Íbúðir í húsum þar sem sala sést í kaupskrá": y_s,
        "þar af þinglýst seldar": V.n_seld - V.n_forsala_thinglyst,
        "þar af auglýstar": V.n_auglyst - V.n_forsala_auglyst,
        "þar af óþekkt staða (hvorki þinglýst né auglýst)": V.n_othekkt,
        "Íbúðir þar sem forsala sést ekki í kaupskrá": V.n_forsala_ibudir,
        "þar af þinglýst seldar ": V.n_forsala_thinglyst,
        "þar af auglýstar ": V.n_forsala_auglyst,
        "Forsöluhús": V.forsala_hus.map(lambda x: ", ".join(x) if len(x) else ""),
        "Ástæða": V.forsala_astaedur.map(lambda x: ", ".join(ASTAEDUR[a] for a in x)),
        "Virkar auglýsingar án fastanúmers (tengdar)": V.n_augl_an_fastnr,
    }).sort_values(["Íbúðir alls", "Verkefni"], ascending=[False, True])
    return T


def skrifa_xlsx(p: Path, T, F, vidtakandi, svaedi, virk):
    s = T.sum(numeric_only=True)
    ys = int(s["Íbúðir í húsum þar sem sala sést í kaupskrá"])
    skyr = pd.DataFrame({"Skýring": [
        f"Gögn: verðmat.ai, útgáfa {F['utgafa']}, kaupskrá HMS til {F['data_through']}, auglýsingar {str(F['snap'])[:16]}.",
        f"Úrval: {'höfuðborgarsvæðið' if svaedi == 'hbs' else 'allt landið'}{', verkefni með minnst eina íbúð í virkri söluauglýsingu' if virk else ''}; {len(T)} verkefni.",
        "Þinglýst seld: þinglýstur kaupsamningur frá 2021 (nothæfur, eða ónothæfur sem ekki var fylgt eftir með nýrri söluauglýsingu).",
        "Auglýst: íbúð sem ekki er þinglýst seld og er í virkri söluauglýsingu.",
        "Óþekkt staða: hvorki þinglýst sala né virk auglýsing. Íbúðin getur verið seld (samningur ekki kominn í kaupskrá) eða óseld; gögnin skera ekki úr.",
        FORSALA_SKYRING,
        f"Samtals: {int(s['Íbúðir alls'])} íbúðir · {int(s['Þinglýst seldar'])} þinglýst seldar · {int(s['Auglýstar til sölu'])} auglýstar · "
        f"óþekkt staða {int(s['þar af óþekkt staða (hvorki þinglýst né auglýst)'])} af {ys} íbúðum í húsum þar sem sala sést í kaupskrá · "
        f"{int(s['Íbúðir þar sem forsala sést ekki í kaupskrá'])} íbúðir þar sem forsala sést ekki í kaupskrá (ekki taldar sem óþekkt).",
    ]})
    meta = pd.DataFrame({"Reitur": ["Viðtakandi", "Búið til", "Útgáfa", "Keyrsla", "Kaupskrá til", "Auglýsingar", "Kóði byggingar", "Kóði afhendingar"],
                         "Gildi": [vidtakandi, dt.datetime.now().strftime("%Y-%m-%d %H:%M"), F["utgafa"], F.get("keyrsla_id") or "prófun (dryrun)",
                                   str(F["data_through"]), str(F["snap"])[:19], F.get("kodi_hash") or "", kodi_afhendingar()]})
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        T.to_excel(w, sheet_name="Verkefni", index=False)
        skyr.to_excel(w, sheet_name="Skýringar", index=False)
        meta.to_excel(w, sheet_name="Lýsigögn", index=False)


def texti_xlsx(p: Path) -> str:
    with zipfile.ZipFile(p) as z:
        return " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.endswith(".xml"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vidtakandi", required=True, help="t.d. VB (stafir, tölur, -, _)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ur-db", action="store_true", help="les útgáfuna úr semantic (ein keyrsla)")
    g.add_argument("--farmur", metavar="DIR", help="farmur.pkl úr cc224 --dryrun (prófun; keyrsla_id = None)")
    ap.add_argument("--utgafa", default=M.UTGAFA)
    ap.add_argument("--svaedi", choices=["hbs", "allt"], default="hbs")
    ap.add_argument("--virk", action="store_true", help="aðeins verkefni með ≥ 1 auglýsta íbúð (VB-sían)")
    ap.add_argument("--rot", default=str(ROT))
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,40}", a.vidtakandi):
        raise SystemExit("[STOPP] --vidtakandi: aðeins stafir, tölur, - og _")
    F, HBS = lesa_db(a.utgafa) if a.ur_db else lesa_farmur(Path(a.farmur))
    V, E = F["V"], F["E"]

    rot = Path(a.rot); rot.mkdir(parents=True, exist_ok=True)
    dags = dt.date.today().isoformat()
    tmp = rot / f".{dags}_{a.vidtakandi}.{os.getpid()}.tmp"
    tmp.mkdir()
    try:
        brot = M.hlid_nyb(V, E, F.get("S"))
        T = tafla(V, HBS, a.svaedi, a.virk)
        xl = tmp / f"nybyggingar_{dags}.xlsx"
        skrifa_xlsx(xl, T, F, a.vidtakandi, a.svaedi, a.virk)
        if M.OSELD.search(texti_xlsx(xl)):
            brot.append("H2: „óseld\" stendur í texta xlsx-skjalsins")
        if brot:
            for b in brot:
                print(f"[H-NYB FELLUR] {b}")
            raise SystemExit(4)
        V.to_csv(tmp / "verkefni.csv", index=False, encoding="utf-8-sig")
        E.to_csv(tmp / "einingar.csv", index=False, encoding="utf-8-sig")
        pd.to_pickle(F, tmp / "farmur.pkl")
        skrar = sorted(p.name for p in tmp.iterdir())
        man = dict(vidtakandi=a.vidtakandi, buid_til=dt.datetime.now().isoformat(timespec="seconds"), utgafa=F["utgafa"],
                   keyrsla_id=F.get("keyrsla_id"), data_through=str(F["data_through"]), listings_snapshot=str(F["snap"]),
                   kodi_hash_byggingar=F.get("kodi_hash"), kodi_hash_afhendingar=kodi_afhendingar(), md5_db=F.get("md5"),
                   svaedi=a.svaedi, virk=a.virk, n_verkefni=len(T), h_nyb="stenst", sent=False,
                   sha256={n: sha(tmp / n) for n in skrar})
        (tmp / "MANIFEST.json").write_text(json.dumps(man, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        # lokanafn — ALDREI yfirskrifað: fyrsta lausa <dags>_<viðtakandi>[_N]
        n = 1
        while True:
            lok = rot / (f"{dags}_{a.vidtakandi}" + (f"_{n}" if n > 1 else ""))
            try:
                os.rename(tmp, lok)   # atómískt; fellur ef lok er til
                break
            except FileExistsError:
                n += 1
        for p in lok.iterdir():
            os.chmod(p, stat.S_IREAD)
        print(f"[OK] afhending fryst: {lok} ({len(T)} verkefni; keyrsla {F.get('keyrsla_id')}; kóði {F.get('kodi_hash')})")
        print("     skrár:", ", ".join(sorted(p.name for p in lok.iterdir())), "— ekkert sent")
        return 0
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


if __name__ == "__main__":
    sys.exit(main())
