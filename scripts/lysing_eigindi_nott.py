#!/usr/bin/env python
"""cc316c — lestur eiginda úr lýsingu virkra íbúðaauglýsinga (ákvörðun Danna 05.11.2026).

Sjálfgefið ÞURRKEYRSLA: telur biðröð, stöðu bókhalds og áætlun; engin köll, engin skrif.
`--einskiptis --skrifa`: einskiptis lestur á VIRKUM íbúðaauglýsingum, nýjustu fyrst (first_seen_at) og aftur í tímann,
    stöðvast við hart þak ÞAK_VERK_USD. Endurræsing heldur áfram þar sem frá var horfið og telur fyrri kostnað með.
`--skrifa`: nýir textar eingöngu (fyrst fundnir >= NYIR_FRA), hart dagsþak DAGSTHAK_USD. EKKI SKRÁÐ Í VERK: bíður svars Danna.
`--urtak N`: kallar á N texta og prentar raðir; ekkert skrifað í gagnagrunn (telst í bókhaldi).
`--stoppa-kl HH:MM`: hættir hreint á þessum tíma (t.d. fyrir 01:00); gögn standa gild.

Bókhald: skrá BOK er eina heimildin um eyðslu. Fyrir hvert kall er haldi (hámarkskostnaði) bætt við ÁÐUR en kallið fer,
og það gert upp eftir svar. Hrun skilur haldið eftir, svo summan vanmetur aldrei og endurræsing kemst ekki yfir þak.
Birting: aðeins HVITLISTI, aðeins já (`til:true`), og orðstofn verður að standa í texta.
rc: 0 lokið / 2 lykill vantar / 3 villa / 4 hlið felldi birtingu / 6 þak eða tími stöðvaði: biðröð eftir.
"""
import argparse, collections, datetime as D, html, json, re, sys, threading, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

NYIR_FRA = D.datetime(2026, 11, 5, tzinfo=D.timezone.utc)  # discovered_at; first_seen_at er mbl-dagsetning á undan promote
MODEL = "claude-haiku-5-5"
VERD = dict(i=0.10, o=0.50, cr=0.01, cw=0.125)  # USD per MTok, 5m skyndiminni
HVITLISTI = ("lyfta", "svalir", "geymsla", "verond_pallur", "gardur")
STOFN = {"lyfta": "lyft", "svalir": "sval|svöl", "geymsla": "geymsl", "verond_pallur": "verönd|pall", "gardur": "garð|gras"}
ÞAK_VERK_USD = 20.00   # Danni 05.11: hart þak, fyrri kostnaður þessa verks á lyklinum telst með
DAGSTHAK_USD = 2.00    # Danni 05.11: nýir textar framvegis
HALD_USD = 0.0075      # hámark á kall: 8.192 úttaks-tákn + 20 þús. skyndiminnisskrif + 7 þús. inntak (próf a2/prof_thak.py)
KOSTN_AETLUN = 0.0018  # mælt: 0,00184 á 160 og 0,00180 á 62 köllum
FYRRI = [("Sonnet 5, úrtak 160", 5.241), ("Haiku 5.5, úrtak 160", 0.295), ("Haiku 5.5, --urtak 3", 0.009), ("Haiku 5.5, 62 nýir textar", 0.112)]
TOL = 15
P = json.loads((Path(__file__).parent / "data" / "eigindi_prompt_v3.json").read_text(encoding="utf-8"))
LOGG = Path("D:/verdmat-is/scraper_data/logs")
BOK = LOGG / "lysing_eigindi_kostnadur.jsonl"


def skra(texti):
    nu = D.datetime.now(D.timezone.utc)
    with open(LOGG / f"lysing_eigindi_{nu:%Y%m}.log", "a", encoding="utf-8") as f:
        f.write(f"{nu:%Y-%m-%dT%H:%M:%SZ} {texti}" + chr(10))


class Bokhald:
    """Append-only: summa allra lína er eyðsla, þar með talin óuppgerð höld."""

    def __init__(self, leid):
        self.lock = threading.Lock()
        self.leid = leid
        if not leid.exists():
            for lysing, usd in FYRRI:
                self._rita(dict(t="fyrri", usd=usd, lysing=lysing))
        self.verk, self.dagur = 0.0, 0.0
        dags = D.datetime.now(D.timezone.utc).date().isoformat()
        for l in leid.read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            if r["t"] in ("fyrri", "einskiptis", "urtak"):
                self.verk += r["usd"]
            elif r["t"] == "nott" and r["d"] == dags:
                self.dagur += r["usd"]

    def _rita(self, r):
        r.setdefault("d", D.datetime.now(D.timezone.utc).date().isoformat())
        with open(self.leid, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + chr(10))
            f.flush()
            os.fsync(f.fileno())

    def halda(self, t):
        with self.lock:
            nu, thak = (self.dagur, DAGSTHAK_USD) if t == "nott" else (self.verk, ÞAK_VERK_USD)
            if nu + HALD_USD > thak:
                return False
            self._rita(dict(t=t, usd=HALD_USD))
            if t == "nott":
                self.dagur += HALD_USD
            else:
                self.verk += HALD_USD
            return True

    def gera_upp(self, t, raun):
        with self.lock:
            m = raun - HALD_USD
            self._rita(dict(t=t, usd=round(m, 7)))
            if t == "nott":
                self.dagur += m
            else:
                self.verk += m


def hreinn(t):
    t = html.unescape(html.unescape(t or ""))
    t = re.sub(r"<\s*(br|/p|/div|/li)[^>]*>", chr(10), t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", chr(10), t).strip()


def rammi(k):
    """Virk: v_eign_virk_auglysing (status active, enginn withdrawn_confirmed/confirmed_absent, ekki tvítak), auk withdrawn_at tómt.
    last_seen_at er ekki notað: það er ekki líf. Fulltrúi eignar: nýjasta auglýsing eftir first_seen_at, ekki listed_at."""
    k.execute("""select v.fastnum,l.source_listing_id,l.first_seen_at,l.listed_at,l.lysing,substr(md5(l.lysing),1,12),v.listing_id
      from scraper.v_eign_virk_auglysing v join scraper.listings l using(listing_id)
      where v.source='mbl' and v.tenure='sale' and v.category='residential' and l.sub_type='apartment'
        and l.withdrawn_at is null and v.fastnum is not null and l.lysing is not null and length(l.lysing)>=300
        and v.fastnum not in (select fastnum from public.v_fjoleining_fastnum)""")
    by = collections.defaultdict(list)
    for r in k.fetchall():
        by[r[0]].append(r)
    return {f: sorted(L, key=lambda r: (r[2], r[6]))[-1] for f, L in by.items()}


def fyrst_fundid(k, hashar):
    """Hvenær TEXTINN fannst fyrst: endurbirting gerir texta ekki nýjan. NULL discovered_at telst aldrei nýtt (fail-closed)."""
    k.execute("""select substr(md5(lysing),1,12), case when bool_and(discovered_at is not null) then min(discovered_at) end
      from scraper.listings where source='mbl' and lysing is not null and substr(md5(lysing),1,12)=any(%s) group by 1""", (list(hashar),))
    return dict(k.fetchall())


def kall(klient, bok, t, h, texti):
    """Skilar (h, svar, kostnaður), eða None ef þak stöðvaði. Hald er sett áður en kallið fer."""
    import anthropic
    if not bok.halda(t):
        return None
    try:
        s = klient.messages.create(
            model=MODEL, max_tokens=8192,
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": P["skema"]}},
            system=[{"type": "text", "text": P["prompt"], "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": texti}],
        )
    except anthropic.APIStatusError:
        bok.gera_upp(t, 0.0)  # hafnað af API: ekkert rukkað
        raise
    u = s.usage
    ko = (u.input_tokens * VERD["i"] + u.output_tokens * VERD["o"]
          + (u.cache_read_input_tokens or 0) * VERD["cr"] + (u.cache_creation_input_tokens or 0) * VERD["cw"]) / 1e6
    bok.gera_upp(t, ko)
    if s.stop_reason != "end_turn":
        raise RuntimeError(f"stop_reason={s.stop_reason}")
    return h, json.loads(next(b.text for b in s.content if b.type == "text")), ko


def radir_ur_svari(svar, texti):
    return [a for a in HVITLISTI if svar.get(a) == "ja" and re.search(STOFN[a], texti, re.I)]


def rw(c):
    c.rollback()
    k = c.cursor()
    k.execute("set transaction read write")
    k.execute("set local lock_timeout='5s'")
    k.execute("set local statement_timeout='120s'")
    return k


def uppfaera_birtingu(c, R, til):
    radir = []
    for f, r in R.items():
        svar = til.get(r[5])
        if svar:
            dags = (r[3] or r[2]).date().isoformat()
            radir += [(f, key, '{"til":true}', r[5], P["skema_utgafa"], dags) for key in radir_ur_svari(svar, hreinn(r[4]))]
    k = rw(c)
    k.execute("select count(*) from public.lysing_eigindi")
    nu = k.fetchone()[0]
    if nu >= 200 and len(radir) < 0.6 * nu:  # lítil tafla sveiflast eðlilega; hlið aðeins þegar hún er orðin stór
        c.rollback()
        skra(f"HLIÐ: {len(radir)} raðir, {nu} í töflu; birting óbreytt")
        return None
    k.execute("create temp table n(fastnum bigint,attr_key text,value jsonb,lysing_hash text,skema_utgafa int,source_date date) on commit drop")
    if radir:
        execute_values(k, "insert into n values %s", radir, page_size=1000)
    k.execute("delete from public.lysing_eigindi t where not exists(select 1 from n where n.fastnum=t.fastnum and n.attr_key=t.attr_key)")
    k.execute("""insert into public.lysing_eigindi(fastnum,attr_key,value,lysing_hash,skema_utgafa,source_date) select * from n
      on conflict(fastnum,attr_key) do update set value=excluded.value,lysing_hash=excluded.lysing_hash,
      skema_utgafa=excluded.skema_utgafa,source_date=excluded.source_date,hladid_at=now()""")
    c.commit()
    return len(radir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skrifa", action="store_true")
    ap.add_argument("--einskiptis", action="store_true")
    ap.add_argument("--urtak", type=int, default=0)
    ap.add_argument("--stoppa-kl", default=None)
    ap.add_argument("--dbconfig", default=r"D:\verdmat-is\.dbconfig")
    a = ap.parse_args()
    stopp = None
    if a.stoppa_kl:
        h, m = map(int, a.stoppa_kl.split(":"))
        stopp = D.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        if stopp <= D.datetime.now():  # klukkan er þegar liðin í dag: átt er við næsta sólarhring
            stopp += D.timedelta(days=1)
    c = psycopg2.connect(Path(a.dbconfig).read_text(encoding="utf-8-sig").strip())
    c.rollback()
    k = c.cursor()
    k.execute("set transaction read only")
    k.execute("set local statement_timeout='120s'")
    R = rammi(k)
    k.execute("select lysing_hash,svar from scraper.lysing_eigindi_svar where skema_utgafa=%s", (P["skema_utgafa"],))
    til = dict(k.fetchall())
    # Nýjast fyrst eftir first_seen_at; jafntefli brotið með auglýsingarnúmeri svo röðin sé fall.
    allt = {r[5]: r[4] for r in sorted(R.values(), key=lambda r: (r[2], r[6]), reverse=True) if r[5] not in til}
    fs = fyrst_fundid(k, allt) if allt else {}
    c.rollback()
    nyir = {h: t for h, t in allt.items() if fs.get(h) and fs[h] >= NYIR_FRA}
    bid = allt if a.einskiptis else nyir
    bok = Bokhald(BOK)
    tegund = "urtak" if a.urtak else "einskiptis" if a.einskiptis else "nott"
    print(json.dumps(dict(rammi_eignir=len(R), textar_til=len(til), nyir_textar=len(nyir), eldri_textar=len(allt) - len(nyir),
                          hamur=tegund, kaupa=len(bid), aaetlun_usd=round(len(bid) * KOSTN_AETLUN, 2),
                          verk_eytt_usd=round(bok.verk, 3), verk_thak_usd=ÞAK_VERK_USD, dagur_eytt_usd=round(bok.dagur, 3),
                          dagsthak_usd=DAGSTHAK_USD), ensure_ascii=False))
    if not a.skrifa and not a.urtak:
        print("ÞURRKEYRSLA: engin köll, ekkert skrifað")
        return 0

    lykill = next((l.split("=", 1)[1].strip().strip('"') for l in Path("D:/env.local").read_text(encoding="utf-8").splitlines()
                   if l.startswith("ANTHROPIC_API_KEY=")), None)
    if not lykill:
        print("lykill vantar")
        return 2
    import anthropic
    klient = anthropic.Anthropic(api_key=lykill, max_retries=4)
    verk = [(h, hreinn(t)) for h, t in list(bid.items())[:a.urtak or None]]
    keypt, kostn, villur, thak, timi, fra_uppf = 0, 0.0, 0, False, False, 0
    with ThreadPoolExecutor(TOL) as ex:
        for i in range(0, len(verk), TOL):
            if stopp and D.datetime.now() >= stopp:
                timi = True
                break
            hrina = verk[i:i + TOL]
            ny = []
            for f in [ex.submit(kall, klient, bok, tegund, h, t) for h, t in hrina]:
                try:
                    x = f.result()
                    if x is None:
                        thak = True
                    else:
                        ny.append(x)
                except Exception as e:
                    villur += 1
                    print("villa", type(e).__name__, str(e)[:120], flush=True)
            kostn += sum(x[2] for x in ny)
            keypt += len(ny)
            if a.urtak:
                for h, svar, _ in ny:
                    print(h, radir_ur_svari(svar, dict(hrina)[h]))
            elif ny:
                # Vistað strax: ekkert má geta glatast milli greidds kalls og vistunar.
                k = rw(c)
                execute_values(k, """insert into scraper.lysing_eigindi_svar(lysing_hash,skema_utgafa,model,svar,kostnadur_usd)
                  values %s on conflict do nothing""", [(h, P["skema_utgafa"], MODEL, Json(s), ko) for h, s, ko in ny], page_size=200)
                c.commit()
                til.update({h: s for h, s, _ in ny})
                fra_uppf += len(ny)
            if not ny and len(hrina) and villur >= TOL:
                print("hætt: heil hrina af villum", flush=True)
                break
            if thak:
                break
            if (keypt % 150) < TOL:
                print(f"köll {keypt}/{len(verk)}, ${kostn:.3f} í lotu, verk ${bok.verk:.3f}", flush=True)
            if not a.urtak and fra_uppf >= 500:
                uppfaera_birtingu(c, R, til)
                fra_uppf = 0
    print(f"köll {keypt}, villur {villur}, kostnaður ${kostn:.3f}, verk alls ${bok.verk:.3f}, dagur ${bok.dagur:.3f}, þak stöðvaði: {thak}, tími stöðvaði: {timi}", flush=True)
    if a.urtak:
        print("ÚRTAK: ekkert skrifað í gagnagrunn")
        return 0
    n = uppfaera_birtingu(c, R, til)
    eftir = len(verk) - keypt
    skra(f"{tegund}: köll {keypt}, villur {villur}, ${kostn:.3f}, verk ${bok.verk:.3f}, dagur ${bok.dagur:.3f}, biðröð eftir {eftir}, þak {thak}, tími {timi}, raðir {n}")
    if n is None:
        return 4
    print("skrifað", n, "biðröð eftir", eftir, flush=True)
    return 6 if (thak or timi) and eftir else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # birtingartaflan stendur óbreytt: færslan er ekki staðfest
        skra(f"VILLA {type(e).__name__}: {e}")
        raise
