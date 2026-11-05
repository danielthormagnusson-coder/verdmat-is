#!/usr/bin/env python
"""cc316b — næturskref: LLM-lestur eiginda úr lýsingu nýrra íbúðaauglýsinga (GO Danna 05.11.2026).

Sjálfgefið ÞURRKEYRSLA: telur biðröð og kostnað, engin köll, engin skrif.
`--skrifa`: kaupir svör fyrir nýja texta, innan þaks, og uppfærir public.lysing_eigindi.
`--urtak N`: (með þurrkeyrslu) kallar á N texta og prentar varpaðar raðir; ekkert skrifað.
`--baklisti`: tekur líka texta sem sáust fyrst fyrir NYIR_FRA. Án þessa rofa eru þeir aldrei keyptir
(Danni 05.11: baklisti kemur eftir viku ef engin frávik verða). Verkið sendir hann ekki.

Rammi: sami og cc316 áfangi 1 (virk mbl-söluauglýsing á íbúð, fastnúmer, ekki fjöleining, fyrst séð >= FRA).
Idempotens: scraper.lysing_eigindi_svar er lykluð á (lysing_hash, skema_utgafa), svo sami texti er keyptur einu sinni.
Birting: aðeins HVITLISTI og aðeins já (`til:true`, stærð og fermetrar fylgja ekki, þau voru ekki mæld).
rc: 0 í lagi / 2 lykill vantar / 3 villa / 4 hlið felldi skrif.
"""
import argparse, collections, datetime as D, html, json, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

FRA = D.datetime(2026, 8, 1, tzinfo=D.timezone.utc)
# Texti er nýr ef skrapinn uppgötvaði hann fyrst þennan dag eða síðar (discovered_at er skrifað einu sinni).
# first_seen_at dugar ekki: mbl-dagsetning auglýsingar, sólarhring á undan promote.
NYIR_FRA = D.datetime(2026, 11, 5, tzinfo=D.timezone.utc)
MODEL = "claude-haiku-5-5"
VERD = dict(i=0.10, o=0.50, cr=0.01, cw=0.125)  # USD per MTok, 5m skyndiminni
HVITLISTI = ("lyfta", "svalir", "geymsla", "verond_pallur", "gardur")
DAGSTHAK_USD = 1.00
MAX_KOLL = 400
KOSTN_AETLUN = 0.0020  # mælt 0,00184 á 160 köllum (cc316b)
P = json.loads((Path(__file__).parent / "data" / "eigindi_prompt_v3.json").read_text(encoding="utf-8"))
LOGG = Path("D:/verdmat-is/scraper_data/logs")


def skra(texti):
    nu = D.datetime.now(D.timezone.utc)
    with open(LOGG / f"lysing_eigindi_{nu:%Y%m}.log", "a", encoding="utf-8") as f:
        f.write(f"{nu:%Y-%m-%dT%H:%M:%SZ} {texti}" + chr(10))


def hreinn(t):
    t = html.unescape(html.unescape(t or ""))
    t = re.sub(r"<\s*(br|/p|/div|/li)[^>]*>", chr(10), t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", chr(10), t).strip()


def rammi(k):
    k.execute("""select v.fastnum,l.source_listing_id,l.first_seen_at,l.listed_at,l.lysing,substr(md5(l.lysing),1,12)
      from scraper.v_eign_virk_auglysing v join scraper.listings l using(listing_id)
      where v.source='mbl' and v.tenure='sale' and v.category='residential' and l.sub_type='apartment'
        and v.fastnum is not null and l.lysing is not null and length(l.lysing)>=300
        and v.fastnum not in (select fastnum from public.v_fjoleining_fastnum)""")
    by = collections.defaultdict(list)
    for r in k.fetchall():
        by[r[0]].append(r)
    ut = {}
    for f, L in by.items():
        if any(r[2] >= FRA for r in L):
            L.sort(key=lambda r: (r[2], str(r[1])))
            ut[f] = L[-1]
    return ut


def fyrst_sed(k, hashar):
    """Hvenær TEXTINN fannst fyrst, í hvaða auglýsingu sem er: endurbirting gerir texta ekki nýjan.
    Röð með NULL discovered_at er eldri en dálkurinn, svo slíkur texti telst aldrei nýr (fail-closed)."""
    k.execute("""select substr(md5(lysing),1,12),
        case when bool_and(discovered_at is not null) then min(discovered_at) end
      from scraper.listings
      where source='mbl' and lysing is not null and substr(md5(lysing),1,12)=any(%s) group by 1""", (list(hashar),))
    return dict(k.fetchall())


def kall(klient, h_texti):
    h, texti = h_texti
    s = klient.messages.create(
        model=MODEL, max_tokens=8192,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": P["skema"]}},
        system=[{"type": "text", "text": P["prompt"], "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": texti}],
    )
    if s.stop_reason != "end_turn":
        raise RuntimeError(f"stop_reason={s.stop_reason}")
    u = s.usage
    k = (u.input_tokens * VERD["i"] + u.output_tokens * VERD["o"]
         + (u.cache_read_input_tokens or 0) * VERD["cr"] + (u.cache_creation_input_tokens or 0) * VERD["cw"]) / 1e6
    return h, json.loads(next(b.text for b in s.content if b.type == "text")), k


# Vörn: já birtist aðeins ef orðstofn eigindisins stendur í texta. Enginn líkanskostnaður.
STOFN = {"lyfta": "lyft", "svalir": "sval|svöl", "geymsla": "geymsl", "verond_pallur": "verönd|pall", "gardur": "garð|gras"}


def radir_ur_svari(svar, texti):
    return [a for a in HVITLISTI if svar.get(a) == "ja" and re.search(STOFN[a], texti, re.I)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skrifa", action="store_true")
    ap.add_argument("--urtak", type=int, default=0)
    ap.add_argument("--baklisti", action="store_true")
    ap.add_argument("--dbconfig", default=r"D:\verdmat-is\.dbconfig")
    a = ap.parse_args()
    c = psycopg2.connect(Path(a.dbconfig).read_text(encoding="utf-8-sig").strip())
    c.rollback()
    k = c.cursor()
    k.execute("set transaction read only")
    k.execute("set local statement_timeout='120s'")
    R = rammi(k)
    k.execute("select to_regclass('scraper.lysing_eigindi_svar')")
    if k.fetchone()[0]:
        k.execute("select lysing_hash,svar from scraper.lysing_eigindi_svar where skema_utgafa=%s", (P["skema_utgafa"],))
        til = dict(k.fetchall())
    else:
        til = {}
    allt = {r[5]: r[4] for r in sorted(R.values(), key=lambda r: r[2], reverse=True) if r[5] not in til}
    fs = fyrst_sed(k, allt) if allt else {}
    c.rollback()
    nyir = {h: t for h, t in allt.items() if fs.get(h) and fs[h] >= NYIR_FRA}
    bid = allt if a.baklisti else nyir
    print(json.dumps(dict(rammi_eignir=len(R), textar_til=len(til), nyir_textar=len(nyir), eldri_textar=len(allt) - len(nyir),
                          baklisti_rofi=a.baklisti, kaupa=len(bid), aaetlun_usd=round(len(bid) * KOSTN_AETLUN, 2)), ensure_ascii=False))
    if not a.skrifa and not a.urtak:
        print("ÞURRKEYRSLA: engin köll, ekkert skrifað")
        return 0

    lykill = next((l.split("=", 1)[1].strip().strip('"') for l in Path("D:/env.local").read_text(encoding="utf-8").splitlines()
                   if l.startswith("ANTHROPIC_API_KEY=")), None)
    if not lykill:
        print("lykill vantar")
        return 2
    import anthropic
    klient = anthropic.Anthropic(api_key=lykill)
    n = a.urtak if a.urtak else min(MAX_KOLL, int(DAGSTHAK_USD / KOSTN_AETLUN))
    verk = [(h, hreinn(t)) for h, t in list(bid.items())[:n]]
    ny, kostn, villur = [], 0.0, 0
    with ThreadPoolExecutor(5) as ex:
        for i in range(0, len(verk), 5):
            if kostn >= DAGSTHAK_USD:
                break
            for f in [ex.submit(kall, klient, v) for v in verk[i:i + 5]]:
                try:
                    h, svar, ko = f.result()
                    ny.append((h, P["skema_utgafa"], MODEL, Json(svar), ko))
                    kostn += ko
                except Exception as e:
                    villur += 1
                    print("villa", type(e).__name__, str(e)[:120])
    print(f"köll {len(ny)}, villur {villur}, kostnaður ${kostn:.3f}")
    if a.urtak:
        for x in ny:
            print(x[0], radir_ur_svari(x[3].adapted, hreinn(bid[x[0]])))
        print("ÚRTAK: ekkert skrifað")
        return 0

    til.update({x[0]: x[3].adapted for x in ny})
    radir = []
    for f, r in R.items():
        svar = til.get(r[5])
        if svar:
            dags = (r[3] or r[2]).date().isoformat()
            radir += [(f, key, json.dumps({"til": True}, separators=(",", ":")), r[5], P["skema_utgafa"], dags)
                      for key in radir_ur_svari(svar, hreinn(r[4]))]
    c.rollback()
    k = c.cursor()
    k.execute("set transaction read write")
    k.execute("set local lock_timeout='5s'")
    k.execute("set local statement_timeout='120s'")
    # Keypt svör varðveitast þótt hlið felli birtingu: þau eru þegar greidd.
    if ny:
        execute_values(k, """insert into scraper.lysing_eigindi_svar(lysing_hash,skema_utgafa,model,svar,kostnadur_usd)
          values %s on conflict do nothing""", ny, page_size=200)
    c.commit()
    k.execute("set transaction read write")
    k.execute("set local lock_timeout='5s'")
    k.execute("select count(*) from public.lysing_eigindi")
    nu = k.fetchone()[0]
    if nu >= 200 and len(radir) < 0.6 * nu:  # lítil tafla sveiflast eðlilega; hlið aðeins þegar hún er orðin stór
        c.rollback()
        skra(f"HLIÐ: {len(radir)} raðir, {nu} í töflu; birting óbreytt")
        return 4
    k.execute("create temp table n(fastnum bigint,attr_key text,value jsonb,lysing_hash text,skema_utgafa int,source_date date) on commit drop")
    execute_values(k, "insert into n values %s", radir or [(0, "x", "{}", "x", 0, "2000-01-01")], page_size=1000)
    k.execute("delete from n where fastnum=0")
    k.execute("delete from public.lysing_eigindi t where not exists(select 1 from n where n.fastnum=t.fastnum and n.attr_key=t.attr_key)")
    k.execute("""insert into public.lysing_eigindi(fastnum,attr_key,value,lysing_hash,skema_utgafa,source_date) select * from n
      on conflict(fastnum,attr_key) do update set value=excluded.value,lysing_hash=excluded.lysing_hash,
      skema_utgafa=excluded.skema_utgafa,source_date=excluded.source_date,hladid_at=now()""")
    c.commit()
    skra(f"köll {len(ny)}, villur {villur}, ${kostn:.3f}, biðröð eftir {max(len(bid) - len(ny), 0)}, raðir {len(radir)} (áður {nu})")
    print("skrifað", len(radir))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # birtingartaflan stendur óbreytt: færslan er ekki staðfest
        skra(f"VILLA {type(e).__name__}: {e}")
        raise SystemExit(3)
