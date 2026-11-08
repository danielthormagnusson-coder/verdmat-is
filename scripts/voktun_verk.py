"""voktun_verk.py — cc320: næturverk vöktunar. Finnur atburði, frystir „Seldist nýlega", samkeyrir og sendir.

Task Scheduler: verdmat-daily-voktun 08:00 (register_voktun_task.ps1), um cc193_keyra_verk.ps1 -Verk voktun.
Keyrir eftir næturkeðju (05:30), Verðvakt (06:45) og vakt (07:00). Engin vinna 01:00-07:30.

  python scripts/voktun_verk.py                  # full keyrsla (biðhlið á keðju)
  python scripts/voktun_verk.py --thurrt         # les og prentar fjölda, skrifar ekkert, sendir ekkert
  python scripts/voktun_verk.py --synishorn      # eitt sýnishorn af hverri pósttegund á móttakanda eiganda; ekkert skrifað

HVÍTLISTI (hörð regla): sendi() neitar öllum öðrum en ABENDING_MOTTAKANDI nema VOKTUN_OPID=1 sé í umhverfi. Það er sett
aðeins við opnun, með GO Danna. „Fer af sölu" er óvirkt nema AF_SOLU_VIRKT = True: sópun er ekki staðfest (SKIL_CC320 §3).
Tala og hlið koma úr mælingu: BIDTIMI_AF_SOLU = 7 d, ny-lota X = 14 d (SKIL §1, §4).

Reglur sem gilda í pósti (regla 13, cc60/cc69): staðreynd, dagsetning, heimild, tengill; engin hvatning, engin prósenta milli
ásetts verðs og mats, verð aldrei án dagsetningar, pakkasamningur merktur sem heildarverð. UTM ber aðeins tegund pósts.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, hmac, html as H, json, os, re, sys, time, unicodedata, base64
from pathlib import Path
import psycopg2, psycopg2.extras, requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BOTN = Path(r"D:\verdmat-is")
AF_SOLU_VIRKT = False
# cc324 §7: R á uppsöfnunardögum sópunar er dagur athugunar, ekki hvarfs. Aðeins R eftir þennan dag má verða „fer af sölu".
# Sett um leið og AF_SOLU_VIRKT, þegar cc324 hefur staðfest sópun (regla þar: 3 morgnar í röð og ekkert kort-auðkenni óathugað > 7 d).
AF_SOLU_KLUKKA_FRA = None
BIDTIMI_AF_SOLU = 7
LOTU_BIL_DAGAR = 14
DAGSTHAK = 80            # sendingarþak á dag (UTC), talið yfir allar keyrslur dagsins; afgangur fer næsta dag (Resend Free: 100/dag, deilt með vakt og ábendingum)
VIDVORUN_VID = 60        # viðvörun í log og D:\verdmat_status.log (rás status-probe og kedjuvaktar) þegar sendir póstar dagsins ná þessu
STATUS_LOG = Path(r"D:\verdmat_status.log")
BENDILL_HAMARK_KLST = 10
GRUNN = os.environ.get("VOKTUN_GRUNNSLOD", "https://www.verdmat.ai")
FRA = "verdmat.ai <vakt@verdmat.ai>"
MAT_REIKNAD = {"iter4r_20260805_reglaR_strukt": dt.date(2026, 8, 6)}  # sama og lib/matsdagsetning.js
VIKUDAGAR = ["mánudag", "þriðjudag", "miðvikudag", "fimmtudag", "föstudag", "laugardag", "sunnudag"]
EIGIND_HEITI = {"lyfta": "lyfta", "svalir": "svalir", "bilskur": "bílskúr", "eldhus": "endurnýjað eldhús"}
UMR = {"þ": "th", "æ": "ae", "ð": "d", "ö": "o", "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ý": "y"}


def env():
    d = {}
    for p in [BOTN / "verdmat-ai" / ".env.local", Path(r"D:\env.local")]:
        try:
            for ln in p.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r"\s*([A-Z_0-9]+)\s*=\s*\"?([^\"\r\n]*)", ln)
                if m and m.group(1) not in d:
                    d[m.group(1)] = m.group(2).strip()
        except OSError:
            pass
    d.update({k: v for k, v in os.environ.items() if k in ("VOKTUN_OPID", "VOKTUN_LEYND", "RESEND_API_KEY", "ABENDING_MOTTAKANDI", "SUPABASE_SERVICE_ROLE_KEY")})
    return d


E = env()


def gotu_slod(gata: str) -> str:
    s = "".join(UMR.get(c, c) for c in gata.lower())
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", s))


def gotu_heiti(h: str) -> str:
    h = re.sub(r"\s+", " ", h or "").strip()
    m = re.match(r"^(.+?)\s+\d\S*(?:\s.*)?$", h)
    return m.group(1) if m else h


def gata_lykill(heimilisfang, postnr):
    return f"{postnr}/{gotu_slod(gotu_heiti(heimilisfang))}" if heimilisfang and postnr else None


def tengja():
    dsn = (BOTN / ".dbconfig").read_text(encoding="utf-8-sig").strip()
    return psycopg2.connect(dsn, connect_timeout=15, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)


def les(c, sql, args=None, timeout=120):
    with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        c.rollback()
        cur.execute("BEGIN READ ONLY")
        cur.execute("SET LOCAL statement_timeout = %s", (timeout * 1000,))
        cur.execute(sql, args)
        r = cur.fetchall()
    c.rollback()
    return r


def skrifa(c, fall):
    """Skrif: fyrst rollback, svo SET TRANSACTION READ WRITE (WP (h))."""
    c.rollback()
    with c.cursor() as cur:
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("SET LOCAL statement_timeout = 120000")
        cur.execute("SET LOCAL lock_timeout = '10s'")
        r = fall(cur)
    c.commit()
    return r


def kedja_lokid() -> bool:
    p = BOTN / "scraper_data" / "night_logs" / f"night_{dt.date.today():%Y%m%d}.log"
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "CHAIN CLEAN" in t or "CHAIN DEGRADED" in t


# ---------- atburðir ----------
def finna_ny(c):
    """Ný lota á fastnúmeri: engin eldri auglýsing lifandi eða horfin innan 14 d. Auðkenni eitt er ekki atburður (43.204 auðkenni = 3.245 lotur)."""
    return les(c, """
      select distinct on (n.fastnum) n.fastnum, n.first_seen_at, n.discovered_at, n.price_amount, n.is_price_on_request, n.source_listing_id,
             p.heimilisfang, p.postnr, p.postheiti
      from scraper.listings n join public.properties p on p.fastnum=n.fastnum and p.is_residential
      where n.source='mbl' and n.tenure='sale' and n.category='residential' and n.fastnum is not null
        and n.discovered_at > now() - interval '3 days' and n.first_seen_at > now() - interval '30 days'
        and not exists (select 1 from scraper.tvitok_falin t where t.listing_id=n.listing_id)
        and not exists (select 1 from scraper.listings o where o.source='mbl' and o.tenure='sale' and o.fastnum=n.fastnum and o.listing_id<>n.listing_id
            and o.first_seen_at<n.first_seen_at
            and not exists (select 1 from scraper.tvitok_falin t where t.listing_id=o.listing_id)
            and coalesce((select min(e.event_at) from scraper.listing_lifecycle_events e where e.source=o.source and e.source_listing_id=o.source_listing_id and e.event_type='confirmed_absent_1'),
                         o.withdrawn_at, case when o.status='inactive' then o.last_seen_at end, 'infinity'::timestamptz) > n.first_seen_at - interval '14 days')
      order by n.fastnum, n.first_seen_at""", timeout=170)


def finna_verd(c):
    return les(c, """
      select v.listing_id, v.fastnum, v.fyrra_verd, v.nytt_verd, v.nytt_sast, v.stefna, v.teg, p.heimilisfang, p.postnr, p.postheiti
      from semantic.v_verdvakt_breytingar_v2 v join public.properties p on p.fastnum=v.fastnum and p.is_residential
      where v.nytt_sast > now() - interval '3 days' and v.grunsamleg is not true and v.grunur_villa is not true
        and not (v.teg='milli' and v.nytt_sast - v.fyrra_sast > interval '14 days')""")


def finna_solur(c, dagar=45):
    return les(c, """
      select s.fastnum, s.faerslunumer, s.thinglystdags, s.kaupverd_nominal, s.onothaefur, s.is_suspect_comparable,
             count(*) over (partition by s.faerslunumer) as stk, p.heimilisfang, p.postnr, p.postheiti, p.matsvaedi_numer, p.matsvaedi_nafn
      from public.sales_history s join public.properties p on p.fastnum=s.fastnum and p.is_residential
      where s.thinglystdags >= current_date - %s""", (dagar,))


def finna_af_solu(c):
    """Eignarhvarf: fyrsta fjarvera fyrir ≥ BIDTIMI dögum, engin önnur auglýsing lifandi og engin ný síðan. Aðeins kallað ef AF_SOLU_VIRKT."""
    return les(c, """
      with h as (
        select l.listing_id, l.fastnum, min(e.event_at) as r from scraper.listings l
        join scraper.listing_lifecycle_events e on e.source=l.source and e.source_listing_id=l.source_listing_id and e.event_type='confirmed_absent_1'
        where l.source='mbl' and l.tenure='sale' and l.category='residential' and l.fastnum is not null
          and not exists (select 1 from scraper.tvitok_falin t where t.listing_id=l.listing_id)
        group by 1,2)
      select h.fastnum, h.r, p.heimilisfang, p.postnr, p.postheiti from h join public.properties p on p.fastnum=h.fastnum and p.is_residential
      where h.r < now() - make_interval(days => %s) and h.r > now() - make_interval(days => %s + 3) and h.r >= %s
        and not exists (select 1 from scraper.listings o where o.source='mbl' and o.tenure='sale' and o.fastnum=h.fastnum and o.listing_id<>h.listing_id
          and not exists (select 1 from scraper.tvitok_falin t where t.listing_id=o.listing_id)
          and (o.first_seen_at > h.r or (o.status='active' and not exists (select 1 from scraper.listing_lifecycle_events e2 where e2.source=o.source and e2.source_listing_id=o.source_listing_id and e2.event_type='confirmed_absent_1'))))""",
                (BIDTIMI_AF_SOLU, BIDTIMI_AF_SOLU, AF_SOLU_KLUKKA_FRA))


def bendill_klst(c):
    r = les(c, "select (upplysingar->'ferskleiki'->>'bendill_aldur_klst')::numeric a from scraper.thekjuprof order by maelt_kl desc limit 1")
    return float(r[0]["a"]) if r and r[0]["a"] is not None else None


def j(o):
    return json.dumps(o, ensure_ascii=False, default=str)


def skra_atburdi(c, thurrt):
    radir = []
    for r in finna_ny(c):
        radir.append((f"ny:{r['fastnum']}:{r['first_seen_at']:%Y-%m-%d}", "ny", r["fastnum"], gata_lykill(r["heimilisfang"], r["postnr"]), r["postnr"],
                      j(dict(heimilisfang=r["heimilisfang"], postheiti=r["postheiti"], verd=None if r["is_price_on_request"] else r["price_amount"], dags=r["first_seen_at"])), r["first_seen_at"]))
    for r in finna_verd(c):
        radir.append((f"verd:{r['listing_id']}:{r['fyrra_verd']}:{r['nytt_verd']}", "verd", r["fastnum"], gata_lykill(r["heimilisfang"], r["postnr"]), r["postnr"],
                      j(dict(heimilisfang=r["heimilisfang"], postheiti=r["postheiti"], fyrra=r["fyrra_verd"], nytt=r["nytt_verd"], stefna=r["stefna"], dags=r["nytt_sast"])), r["nytt_sast"]))
    for r in finna_solur(c):
        radir.append((f"sala:{r['faerslunumer']}:{r['fastnum']}", "sala", r["fastnum"], gata_lykill(r["heimilisfang"], r["postnr"]), r["postnr"],
                      j(dict(heimilisfang=r["heimilisfang"], postheiti=r["postheiti"], verd=r["kaupverd_nominal"], faerslunumer=r["faerslunumer"], nothaef=r["onothaefur"] == 0, stk=r["stk"], dags=r["thinglystdags"])),
                      dt.datetime.combine(r["thinglystdags"], dt.time(12), dt.timezone.utc)))
    if AF_SOLU_VIRKT:
        if AF_SOLU_KLUKKA_FRA is None:
            raise SystemExit("af_solu: AF_SOLU_KLUKKA_FRA vantar (cc324 §7)")
        b = bendill_klst(c)
        if b is None or b > BENDILL_HAMARK_KLST:
            print(f"af_solu: sleppt, bendill {b} klst")
        else:
            for r in finna_af_solu(c):
                radir.append((f"af_solu:{r['fastnum']}:{r['r']:%Y-%m-%d}", "af_solu", r["fastnum"], gata_lykill(r["heimilisfang"], r["postnr"]), r["postnr"],
                              j(dict(heimilisfang=r["heimilisfang"], postheiti=r["postheiti"], fyrst_horfin=r["r"], dags=r["r"])), r["r"]))
    fj = {}
    for x in radir:
        fj[x[1]] = fj.get(x[1], 0) + 1
    print("atburðir fundnir (þ.m.t. þegar skráðir):", fj)
    if thurrt:
        return 0

    def f(cur):
        return len(psycopg2.extras.execute_values(cur, "insert into public.voktun_atburdur (lykill,tegund,fastnum,gata_lykill,postnr,gogn,atburdar_at) values %s on conflict (lykill) do nothing returning id", radir, page_size=500, fetch=True))
    n = skrifa(c, f)
    print("nýskráðir atburðir:", n)
    return n


def frysta_seldist(c, thurrt, fra=dt.date(2026, 8, 7)):
    """Sala, síðasta ásett verð og mat frosið við fyrstu skráningu. Mat aðeins ef reiknað fyrir þinglýsingu og birtingarhæft (T1-T4). Hlið: nothæfur samningur, eitt fastnúmer, ekki frávik, sala/ásett í 0,7-1,3."""
    r = les(c, """
      with s as (select s.fastnum, s.faerslunumer, s.thinglystdags, s.kaupverd_nominal, s.is_suspect_comparable, s.onothaefur,
                        count(*) over (partition by s.faerslunumer) stk from public.sales_history s where s.thinglystdags >= %s)
      select s.fastnum, s.faerslunumer, s.thinglystdags, s.kaupverd_nominal as sala, p.postnr, p.matsvaedi_numer, p.matsvaedi_nafn, p.heimilisfang,
             a.price_amount as asett, a.first_seen_at as asett_at, pr.real_pred_mean as mat, pr.model_version, t.tier
      from s join public.properties p on p.fastnum=s.fastnum and p.is_residential
      join lateral (select l.price_amount, l.first_seen_at from scraper.listings l
                    where l.source='mbl' and l.tenure='sale' and l.fastnum=s.fastnum and l.price_amount>=1000000 and l.is_price_on_request is not true
                      and l.first_seen_at < s.thinglystdags and l.first_seen_at >= s.thinglystdags - interval '365 days'
                      and not exists (select 1 from scraper.tvitok_falin tf where tf.listing_id=l.listing_id)
                    order by l.first_seen_at desc, l.listing_id desc limit 1) a on true
      left join public.v_current_predictions pr on pr.fastnum=s.fastnum
      left join public.valuation_tiers t on t.fastnum=s.fastnum
      where s.onothaefur=0 and s.stk=1 and s.is_suspect_comparable is not true and p.postnr is not null and p.heimilisfang is not null
        and not exists (select 1 from public.voktun_seldist v where v.fastnum=s.fastnum and v.faerslunumer=s.faerslunumer)""", (fra,), timeout=170)
    radir, utan = [], 0
    for x in r:
        h = float(x["sala"]) / float(x["asett"])
        if not 0.7 <= h <= 1.3:
            utan += 1
            continue
        rk = MAT_REIKNAD.get(x["model_version"])
        mat = int(x["mat"]) if x["mat"] is not None and rk and rk < x["thinglystdags"] and x["tier"] in ("T1", "T2", "T3", "T4") else None
        radir.append((x["fastnum"], x["faerslunumer"], x["thinglystdags"], x["postnr"], x["matsvaedi_numer"], x["matsvaedi_nafn"], x["heimilisfang"], x["asett"], x["asett_at"].date(), x["sala"], mat, x["model_version"] if mat else None))
    print(f"seldist: {len(radir)} nýjar raðir, {utan} utan 0,7-1,3, þar af með mati {sum(1 for x in radir if x[10])}")
    if thurrt or not radir:
        return

    def f(cur):
        psycopg2.extras.execute_values(cur, "insert into public.voktun_seldist (fastnum,faerslunumer,thinglystdags,postnr,matsvaedi_numer,matsvaedi_nafn,heimilisfang,asett,asett_dags,sala,mat,mat_utgafa) values %s on conflict do nothing", radir, page_size=500)
    skrifa(c, f)


# ---------- póstur ----------
def kr(v):
    return f"{int(v):,}".replace(",", ".") + " kr."


def dags(s):
    d = s if isinstance(s, (dt.date, dt.datetime)) else dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return f"{d:%d.%m.%Y}"


def utm(slod, herferd):
    return f"{GRUNN}{slod}?utm_source=verdmat&utm_medium=email&utm_campaign={herferd}"


def still_tak(askrifandi):
    # Sami lykill og www (lib/voktun/thjonn.ts). Án VOKTUN_LEYND passa tákn ekki við www (lykill Vercel er annar, mælt 08.11).
    if E.get("VOKTUN_LEYND"):
        leynd = hashlib.sha256(("voktun-v2:" + E["VOKTUN_LEYND"]).encode()).digest()
    else:
        leynd = hashlib.sha256(("voktun-v1:" + E["SUPABASE_SERVICE_ROLE_KEY"]).encode()).digest()
    sig = base64.urlsafe_b64encode(hmac.new(leynd, f"stillingar:{askrifandi}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{askrifandi}.{sig}"


def rammi(efni_html, tak, efni_titill):
    stilling = f"{GRUNN}/voktun/stillingar?t={tak}"
    afsk = f"{GRUNN}/voktun/afskra?t={tak}"
    return (f'<!doctype html><html lang="is"><head><meta charset="utf-8"><title>{H.escape(efni_titill)}</title></head>'
            '<body style="margin:0;padding:16px;background:#F7F2E9;font-family:Arial,Helvetica,sans-serif;color:#2B2620;font-size:15px;line-height:1.5">'
            '<div style="max-width:560px;margin:0 auto;background:#fff;border:1px solid #E4DCCB;border-radius:12px;padding:20px">'
            '<div style="font-family:Georgia,serif;font-size:17px;margin-bottom:14px">verdmat<span style="color:#B14E2E">.ai</span></div>'
            f'{efni_html}<hr style="border:0;border-top:1px solid #E4DCCB;margin:18px 0 10px"><div style="font-size:12px;color:#5C554A">'
            f'Þú staðfestir þessa vöktun á verdmat.ai. <a href="{stilling}" style="color:#8D3E23">Breyta vali eða tíðni</a> · <a href="{afsk}" style="color:#8D3E23">Afskrá (eyðir netfanginu)</a></div></div></body></html>')


def sendi(til, efni, html, tak, lykill):
    leyft = E.get("ABENDING_MOTTAKANDI", "").strip().lower()
    if E.get("VOKTUN_OPID") != "1" and til.lower() != leyft:
        raise PermissionError("hvítlisti")
    if til.lower() != leyft and not E.get("VOKTUN_LEYND"):
        raise PermissionError("VOKTUN_LEYND vantar: afskráningartenglar virka ekki á www án hans")
    r = requests.post("https://api.resend.com/emails", timeout=30, headers={"Authorization": "Bearer " + E["RESEND_API_KEY"], "Idempotency-Key": lykill},
                      json={"from": FRA, "to": [til], "subject": efni, "html": html, "headers": {
                          "List-Unsubscribe": f"<{GRUNN}/api/voktun/afskra?t={tak}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}})
    if r.status_code >= 300:
        raise RuntimeError(f"Resend {r.status_code}")
    return r.json().get("id")


H2 = 'style="margin:14px 0 6px;font-size:16px;font-family:Georgia,serif"'
HEIM = 'style="font-size:13px;color:#5C554A;margin:8px 0"'


IBUD = {}  # fastnum -> íbúðarnúmer, fyllt fyrir hverja sendingu (ibudarnumer)


def ibudarnumer(c, fastnumer):
    """Sama regla og lib/ibudarnumer.ts: íbúðar-matseining eigin fastanúmers (notkun ber „íbúð", merking 6 stafir), ein ólík;
    forskeyti matshluta ef íbúðir staðfangs eru í > 1 matshluta. Aðeins þegar fleiri en ein íbúð er á staðfanginu."""
    fn = [int(x) for x in set(fastnumer) if x]
    if not fn:
        return {}
    st = les(c, "select distinct heimilisfang, postnr from public.properties where fastnum = any(%s) and heimilisfang is not null and postnr is not null", (fn,))
    if not st:
        return {}
    radir = les(c, """select p.fastnum, p.heimilisfang, p.postnr, p.matseiningar from public.properties p
                       join (select unnest(%s::text[]) h, unnest(%s::int[]) n) s on s.h=p.heimilisfang and s.n=p.postnr
                       where coalesce(p.deregistered,false)=false""", ([x["heimilisfang"] for x in st], [x["postnr"] for x in st]))
    hopar = {}
    for r in radir:
        hopar.setdefault((r["heimilisfang"], r["postnr"]), []).append(r)
    ut = {}
    for hopur in hopar.values():
        mk = {}
        for r in hopur:
            m = {str(e.get("merking") or "").strip() for e in (r["matseiningar"] or []) if isinstance(e, dict)
                 and str(e.get("fastnum")) == str(r["fastnum"]) and "íbúð" in str(e.get("notkun_texti") or "").lower()
                 and re.fullmatch(r"\d{6}", str(e.get("merking") or "").strip())}
            if len(m) == 1:
                mk[r["fastnum"]] = m.pop()
        if len(mk) < 2:
            continue
        med = len({x[:2] for x in mk.values()}) > 1
        for f, x in mk.items():
            ut[f] = f"{x[:2]}-{x[2:]}" if med else x[2:]
    return {f: n for f, n in ut.items() if f in fn}


def eign_nafn(a):
    g = a["gogn"]
    if not g.get("heimilisfang"):
        return f"Fastanúmer {a['fastnum']}"
    n = IBUD.get(a["fastnum"])
    return f"{g['heimilisfang']}, íbúð {n}" if n else g["heimilisfang"]


def lina(a, herferd):
    g, t = a["gogn"], a["tegund"]
    teng = f'<a href="{utm("/eign/" + str(a["fastnum"]), herferd)}" style="color:#8D3E23">{H.escape(eign_nafn(a))}</a>'
    if t == "ny":
        v = kr(g["verd"]) if g.get("verd") and g["verd"] > 1 else "verð samkvæmt beiðni"
        return f"{teng}: ný auglýsing, ásett {v}, {dags(g['dags'])}."
    if t == "verd":
        return f"{teng}: ásett verð {'lækkaði' if g.get('stefna') == 'laekkun' else 'hækkaði'} úr {kr(g['fyrra'])} í {kr(g['nytt'])}, séð {dags(g['dags'])}."
    if t == "sala":
        p = f"samningur um {g['stk']} fastanúmer, heildarverð {kr(g['verd'])}" if g.get("stk", 1) > 1 else kr(g["verd"])
        m = "" if g.get("nothaef") else " HMS telur samninginn ekki nothæfan til samanburðar."
        return f"{teng}: þinglýst sala, {p}, þinglýst {dags(g['dags'])}.{m}"
    if t == "af_solu":
        return f"{teng}: engin auglýsing í {BIDTIMI_AF_SOLU} daga (fannst ekki {dags(g['dags'])}). Það þýðir ekki að eignin sé seld."
    return teng


def heimild(atb):
    h = []
    if {"ny", "verd", "af_solu"} & atb:
        h.append("söluauglýsingar á mbl.is (nætursókn verdmat.ai); ásett verð er ekki söluverð")
    if "sala" in atb:
        h.append("kaupskrá HMS; síðustu þinglýsingardagar geta átt eftir að bætast við")
    return f"<p {HEIM}>Heimild: {'; '.join(h)}.</p>" if h else ""


def herferd(tegund, einu):
    return "soluverd" if einu else {"eign": "vakt_eign", "gata": "vakt_gata", "postnr": "vakt_postnr", "leit": "leit", "frettabref": "frettabref"}.get(tegund, "vakt")


HAMARK_LINA = 20


def hluti_askriftar(s, atb):
    """HTML-hluti einnar áskriftar. atb = atburðir sem eiga við. Hámark línur, afgangur á síðu."""
    her = herferd(s["tegund"], s["einu_sinni"])
    ut = f'<h2 {H2}>{H.escape(s["heiti"])}</h2>'
    if s["tegund"] == "leit":
        ja = [a for a in atb if a.get("_passar")]
        ov = [a for a in atb if not a.get("_passar")]
        if ja:
            ut += f"<p><strong>{len(ja)} nýjar auglýsingar sem passa.</strong></p>"
            ut += "<ul style='padding-left:18px;margin:6px 0'>" + "".join(f"<li>{lina(a, her)}</li>" for a in ja[:HAMARK_LINA]) + "</ul>"
        if ov:
            ut += f"<p>{len(ov)} til viðbótar passa við svæði og verðmat, en eigind er óþekkt. Lýsingar nefna ekki alltaf allt, svo óþekkt þýðir ekki að eigindina vanti.</p>"
    else:
        ut += "<ul style='padding-left:18px;margin:6px 0'>" + "".join(f"<li>{lina(a, her)}</li>" for a in atb[:HAMARK_LINA]) + "</ul>"
        if len(atb) > HAMARK_LINA:
            ut += f"<p>… {len(atb) - HAMARK_LINA} í viðbót.</p>"
    return ut


def velja(s, allt_t, eigindi, mat):
    """Atburðir sem eiga við áskrift, ósendir, fundnir eftir staðfestingu. Einn samningur = einn atburður á götu og póstnúmeri."""
    t, lyk, val = s["tegund"], s["lykill"], set(s["atburdir"])
    ut = []
    if t == "eign":
        v = {"a_solu": {"ny"}, "verd": {"verd"}, "selst": {"sala"}, "af_solu": {"af_solu"} if AF_SOLU_VIRKT else set()}
        teg = set().union(*[v.get(x, set()) for x in val])
        ut = [a for a in allt_t if a["fastnum"] == int(lyk) and a["tegund"] in teg]
    elif t in ("gata", "postnr"):
        samn = set()
        for a in allt_t:
            if (t == "gata" and a["gata_lykill"] != lyk) or (t == "postnr" and str(a["postnr"]) != lyk):
                continue
            if a["tegund"] == "ny" and "ny" in val:
                ut.append(a)
            elif a["tegund"] == "verd" and "laekkun" in val and a["gogn"].get("stefna") == "laekkun":
                ut.append(a)
            elif a["tegund"] == "sala" and "sala" in val and a["gogn"].get("nothaef"):
                f = a["gogn"].get("faerslunumer")
                if f not in samn:
                    samn.add(f)
                    ut.append(a)
    elif t == "leit":
        sk = s["skilyrdi"]
        for a in allt_t:
            if a["tegund"] != "ny" or a["postnr"] != sk["postnr"]:
                continue
            m = mat.get(a["fastnum"])
            if sk.get("mat_fra") and (m is None or m < sk["mat_fra"] * 1e6):
                continue
            if sk.get("mat_til") and (m is None or m > sk["mat_til"] * 1e6):
                continue
            b = dict(a)
            b["_passar"] = all(e in eigindi.get(a["fastnum"], ()) for e in sk.get("eigindi", []))
            ut.append(b)
    return ut


def lesa_eigindi(c, fastnum):
    """Leit: aðeins já. Óþekkt er aldrei nei. Lindir: skráð gildi og sellur sem stóðust blint úrtak (cc319). Regla 11 víkkuð í D20; engin áhrif á mat."""
    if not fastnum:
        return {}, {}
    fn = list(map(int, fastnum))
    r = les(c, """
      select fastnum, k from (
        select fastnum, case when attr_key='lyfta' and value->>'til'='true' then 'lyfta' when attr_key='svalir' and value->>'til'='true' then 'svalir'
                             when attr_key='bilskur_staedi' and value->>'gerd' like 'bilskur%%' then 'bilskur'
                             when attr_key='eldhus_astand' and value->>'stada'='endurnyjad' then 'eldhus' when attr_key='eldhus_astand' and value->>'astand'='uppgert' then 'eldhus' end k
        from (select fastnum,attr_key,value from public.property_attributes where superseded_at is null and fastnum=any(%(f)s)
              union all select fastnum,attr_key,value from public.auglysing_eigindi where fastnum=any(%(f)s)
              union all select fastnum,attr_key,value from public.lysing_eigindi where fastnum=any(%(f)s)
              union all select fastnum,attr_key,value from public.lysing_vidbot where fastnum=any(%(f)s)) u
        union all select fastnum,'eldhus' from public.lysing_astand where attr_key='eldhus' and stada='endurnyjad' and fastnum=any(%(f)s)
      ) x where k is not null""", {"f": fn})
    e = {}
    for x in r:
        e.setdefault(x["fastnum"], set()).add(x["k"])
    m = {x["fastnum"]: float(x["real_pred_mean"]) for x in les(c, "select p.fastnum,p.real_pred_mean from public.v_current_predictions p join public.valuation_tiers t using(fastnum) where t.tier in ('T1','T2','T3','T4') and p.fastnum=any(%(f)s)", {"f": fn})}
    return e, m


def fyrirsogn(hlutar):
    if len(hlutar) == 1:
        s, atb = hlutar[0]
        if s["einu_sinni"]:
            return f"{eign_nafn(atb[0])} seldist á {kr(atb[0]['gogn']['verd'])}" if atb[0]["gogn"].get("stk", 1) == 1 else f"{eign_nafn(atb[0])}: þinglýst sala"
        return f"{s['heiti']}: {len(atb)} {'atburður' if len(atb) == 1 else 'atburðir'}"
    return f"Vöktun: {sum(len(a) for _, a in hlutar)} atburðir á {len(hlutar)} vöktunum"


def sendir_i_dag(c):
    """Póstar sendir í dag (UTC): einkvæm Resend-auðkenni í voktun_sendur. Einn póstur ber margar raðir."""
    return les(c, "select count(distinct resend_id) n from public.voktun_sendur where sent_at >= date_trunc('day', now() at time zone 'utc') at time zone 'utc'")[0]["n"]


def vidvorun_magn(c):
    n = sendir_i_dag(c)
    if n >= VIDVORUN_VID:
        lina = f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ} !! VOKTUN-VIDVORUN: sendir póstar í dag {n} (viðvörun {VIDVORUN_VID}, þak {DAGSTHAK})"
        print(lina)
        try:
            with open(STATUS_LOG, "a", encoding="utf-8") as f:
                f.write(lina + "\n")
        except OSError as e:
            print("status-log skrifaðist ekki:", e)
    return n


def samkeyra_og_senda(c, thurrt):
    nu = dt.datetime.now(dt.timezone.utc)
    vd = dt.date.today().isoweekday()
    ask = les(c, "select id, netfang from public.voktun_askrifandi where stadfest_at is not null order by id")
    leyft = E.get("ABENDING_MOTTAKANDI", "").strip().lower()
    utan = [a for a in ask if E.get("VOKTUN_OPID") != "1" and a["netfang"] != leyft]
    print(f"áskrifendur staðfestir: {len(ask)}; utan hvítlista (fá ekkert): {len(utan)}")
    send = 0 if thurrt else sendir_i_dag(c)  # þakið er á dag, ekki á keyrslu
    for a in ask:
        if a in utan:
            continue
        subs = les(c, "select * from public.voktun_askrift where askrifandi_id=%s and stadfest_at is not null and tegund not in ('frettabref','eignin_min','manadarskyrsla') order by stofnad, id", (a["id"],))
        hlutar = []
        for s in subs:
            if s["tidni"] == "vikuleg" and s["vikudagur"] != vd:
                continue
            if s["tegund"] == "eign":
                sia, arg = "e.fastnum=%s", int(s["lykill"])
            elif s["tegund"] == "gata":
                sia, arg = "e.gata_lykill=%s", s["lykill"]
            elif s["tegund"] == "postnr":
                sia, arg = "e.postnr=%s", int(s["lykill"])
            else:
                sia, arg = "e.postnr=%s", int(s["skilyrdi"]["postnr"])
            atb = les(c, f"""select e.id,e.tegund,e.fastnum,e.gata_lykill,e.postnr,e.gogn,e.atburdar_at,e.fundid_at from public.voktun_atburdur e
                             where {sia} and e.fundid_at > %s and not exists (select 1 from public.voktun_sendur v where v.askrift_id=%s and v.atburdur_id=e.id)
                             order by e.atburdar_at desc, e.id""", (arg, s["stadfest_at"], s["id"]))
            eig, mat = lesa_eigindi(c, {x["fastnum"] for x in atb if x["fastnum"]}) if s["tegund"] == "leit" else ({}, {})
            v = velja(s, atb, eig, mat)
            if v:
                hlutar.append((s, v))
        if not hlutar:
            continue
        if send >= DAGSTHAK:
            print("sendingarþak náð; afgangur næsta dag")
            break
        IBUD.clear()
        IBUD.update(ibudarnumer(c, {x["fastnum"] for _, v in hlutar for x in v if x.get("fastnum")}))
        efni = fyrirsogn(hlutar)
        tegs = {x["tegund"] for _, v in hlutar for x in v}
        body = "".join(hluti_askriftar(s, v) for s, v in hlutar) + heimild(tegs)
        print(f"sending: {len(hlutar)} áskriftir, {sum(len(v) for _, v in hlutar)} atburðir")
        if thurrt:
            send += 1
            continue
        tak = still_tak(a["id"])
        rid = sendi(a["netfang"], efni, rammi(body, tak, efni), tak, f"voktun/{a['id']}/{dt.date.today()}")

        def f(cur):
            for s, v in hlutar:
                psycopg2.extras.execute_values(cur, "insert into public.voktun_sendur (askrift_id,atburdur_id,resend_id) values %s on conflict do nothing", [(s["id"], x["id"], rid) for x in v])
                cur.execute("update public.voktun_askrift set sidast_sent=now() where id=%s", (s["id"],))
                if s["einu_sinni"]:
                    cur.execute("delete from public.voktun_askrift where id=%s", (s["id"],))
        skrifa(c, f)
        send += 1
        time.sleep(0.2)
    print("póstar sendir í dag:", send, "(þurrt)" if thurrt else "")
    return send


def frettabref_tolur(c):
    """Mánudagur: ný lota og lækkun síðustu 7 daga; samningar frá föstudegi til fimmtudags (föstudagur ekki fullskráður á mánudagsmorgni, SKIL §15)."""
    idag = dt.date.today()
    fim = idag - dt.timedelta(days=4)
    fos = fim - dt.timedelta(days=6)
    r = les(c, """select count(*) filter (where tegund='ny' and atburdar_at >= now() - interval '7 days') ny,
                         count(*) filter (where tegund='verd' and gogn->>'stefna'='laekkun' and atburdar_at >= now() - interval '7 days') laekkun
                  from public.voktun_atburdur""")[0]
    s = les(c, "select count(distinct faerslunumer) n from public.sales_history where onothaefur=0 and thinglystdags between %s and %s", (fos, fim))[0]["n"]
    th = les(c, "select max(thinglystdags) d from public.sales_history")[0]["d"]
    return dict(ny=r["ny"], laekkun=r["laekkun"], samningar=s, fra=fos, til=fim, gogn_til=th)


def frettabref_html(t):
    return (f'<h1 style="margin:0 0 8px;font-size:18px;font-family:Georgia,serif">Markaðurinn í vikunni</h1>'
            f"<p><strong>Nýjar auglýsingar:</strong> {t['ny']} eignir sem ekki höfðu verið auglýstar síðustu 14 daga, síðustu 7 daga.</p>"
            f"<p><strong>Verðlækkanir:</strong> {t['laekkun']} í auglýsingum eða við endurbirtingu, síðustu 7 daga.</p>"
            f"<p><strong>Þinglýstar sölur:</strong> {t['samningar']} nothæfir samningar þinglýstir {dags(t['fra'])}–{dags(t['til'])}. Síðari dagar eru ekki fullskráðir á mánudagsmorgni.</p>"
            f'<p {HEIM}>Heimildir: söluauglýsingar á mbl.is (nætursókn verdmat.ai) og kaupskrá HMS, gögn til {dags(t["gogn_til"])}. <a href="{utm("/markadur", "frettabref")}" style="color:#8D3E23">Allar tölur á /markadur</a>.</p>')


def frettabref(c, thurrt):
    if dt.date.today().isoweekday() != 1:
        return
    t = frettabref_tolur(c)
    print("fréttabréf:", {k: t[k] for k in ("ny", "laekkun", "samningar")})
    # Atburðatafla þarf heila viku að baki (fyrsta keyrsla sækir aðeins 3 daga), annars væru tölur vikunnar of lágar.
    if les(c, "select min(fundid_at) < now() - interval '8 days' as heil from public.voktun_atburdur where tegund='ny'")[0]["heil"] is not True:
        print("fréttabréf: atburðatafla yngri en 8 dagar, ekkert sent")
        return
    if thurrt:
        return
    lykill = f"frettabref:{dt.date.today()}"

    def f(cur):
        cur.execute("insert into public.voktun_atburdur (lykill,tegund,gogn,atburdar_at) values (%s,'utgafa',%s,now()) on conflict (lykill) do nothing", (lykill, j(t)))
    skrifa(c, f)
    at = les(c, "select id from public.voktun_atburdur where lykill=%s", (lykill,))[0]["id"]
    subs = les(c, """select s.id, a.id as askrifandi, a.netfang from public.voktun_askrift s join public.voktun_askrifandi a on a.id=s.askrifandi_id
                     join public.voktun_samthykki m on m.askrifandi_id=a.id and m.tilgangur='markadsefni'
                     where s.tegund='frettabref' and s.stadfest_at is not null and not exists (select 1 from public.voktun_sendur v where v.askrift_id=s.id and v.atburdur_id=%s) order by s.id""", (at,))
    leyft = E.get("ABENDING_MOTTAKANDI", "").strip().lower()
    for s in subs:
        if sendir_i_dag(c) >= DAGSTHAK:
            print("fréttabréf: dagsþak náð; afgangur næsta dag")
            break
        if E.get("VOKTUN_OPID") != "1" and s["netfang"] != leyft:
            continue
        tak = still_tak(s["askrifandi"])
        efni = f"Markaðurinn í vikunni, {dags(dt.date.today())}"
        rid = sendi(s["netfang"], efni, rammi(frettabref_html(t), tak, efni), tak, f"voktun-frett/{s['askrifandi']}/{dt.date.today()}")
        skrifa(c, lambda cur: cur.execute("insert into public.voktun_sendur (askrift_id,atburdur_id,resend_id) values (%s,%s,%s) on conflict do nothing", (s["id"], at, rid)))


def tiltekt(c, thurrt):
    """Óstaðfest eytt eftir 48 klst; hraðaraðir eftir 24 klst; endurnýjun: spurt einu sinni eftir 12 mán, eytt 30 d síðar."""
    if thurrt:
        return

    def f(cur):
        cur.execute("delete from public.voktun_tak where rennur_ut < now() - interval '1 day'")
        cur.execute("delete from public.voktun_askrift where stadfest_at is null and stofnad < now() - interval '48 hours'")
        cur.execute("delete from public.notandi_eigindi where stada='bida' and stofnad < now() - interval '48 hours'")
        cur.execute("""delete from public.voktun_askrifandi a where a.stadfest_at is null and a.stofnad < now() - interval '48 hours'""")
        cur.execute("delete from public.voktun_hradi where stofnad < now() - interval '24 hours'")
        cur.execute("delete from public.voktun_askrifandi where endurnyjun_send < now() - interval '30 days' and endurnyjun_at < now()")
    skrifa(c, f)
    # Tóm áskrifendaröð sem hefur enga áskrift og enga eigindaskráningu (t.d. eftir einu_sinni) er ekki geymd.
    skrifa(c, lambda cur: cur.execute("""delete from public.voktun_askrifandi a where a.stadfest_at is not null
          and not exists (select 1 from public.voktun_askrift s where s.askrifandi_id=a.id) and not exists (select 1 from public.notandi_eigindi n where n.askrifandi_id=a.id and n.stada<>'hafnad')"""))
    leyft = E.get("ABENDING_MOTTAKANDI", "").strip().lower()
    for a in les(c, "select id, netfang from public.voktun_askrifandi where stadfest_at is not null and endurnyjun_at < now() and endurnyjun_send is null limit %s", (DAGSTHAK,)):
        if E.get("VOKTUN_OPID") != "1" and a["netfang"] != leyft:
            continue
        tak = still_tak(a["id"])
        efni = "Viltu halda áfram að fá póst frá verdmat.ai?"
        sendi(a["netfang"], efni, rammi(f'<h1 style="margin:0 0 8px;font-size:18px;font-family:Georgia,serif">{efni}</h1><p>Ár er liðið. Ef þú svarar ekki innan 30 daga eyðum við netfanginu. <a href="{GRUNN}/voktun/stillingar?t={tak}" style="color:#8D3E23">Opnaðu stillingarnar til að halda áfram</a>.</p>', tak, efni), tak, f"voktun-endurn/{a['id']}")
        skrifa(c, lambda cur: cur.execute("update public.voktun_askrifandi set endurnyjun_send=now() where id=%s", (a["id"],)))


def synishorn(c):
    """Eitt af hverri pósttegund á móttakanda eiganda, með nýjustu raunatburðum. Ekkert skrifað. Táknið er gervi og tenglarnir virka ekki fyrr en við opnun."""
    leyft = E.get("ABENDING_MOTTAKANDI", "").strip().lower()
    if not leyft:
        raise SystemExit("móttakanda vantar")
    tak = "00000000-0000-0000-0000-000000000000.synishorn"
    d = les(c, """select distinct on (tegund) id,tegund,fastnum,gata_lykill,postnr,gogn,atburdar_at from public.voktun_atburdur where tegund in ('ny','verd','sala') order by tegund, fundid_at desc, id""")
    a = {x["tegund"]: x for x in d}
    pn = a["ny"]["postnr"]
    allt = les(c, "select id,tegund,fastnum,gata_lykill,postnr,gogn,atburdar_at from public.voktun_atburdur where postnr=%s and atburdar_at > now()-interval '14 days' order by atburdar_at desc, id limit 200", (pn,))
    S = lambda **k: dict(dict(einu_sinni=False, skilyrdi=None), **k)
    p = {
        "Eign, verð breytist": [(S(tegund="eign", heiti=f"{a['verd']['gogn'].get('heimilisfang')}"), [a["verd"]])],
        "Eign, kemur á sölu": [(S(tegund="eign", heiti=f"{a['ny']['gogn'].get('heimilisfang')}"), [a["ny"]])],
        "Eign, selst": [(S(tegund="eign", heiti=f"{a['sala']['gogn'].get('heimilisfang')}"), [a["sala"]])],
        "Söluverð, eitt skipti": [(S(tegund="eign", einu_sinni=True, heiti=f"{a['sala']['gogn'].get('heimilisfang')}"), [a["sala"]])],
        "Póstnúmer, vikuleg samantekt": [(S(tegund="postnr", heiti=f"{pn}"), [x for x in allt if x["tegund"] in ("ny", "sala") or x["gogn"].get("stefna") == "laekkun"])],
        "Vistuð leit": [(S(tegund="leit", heiti=f"{pn}, lyfta"), [dict(x, _passar=i < 2) for i, x in enumerate([y for y in allt if y["tegund"] == "ny"][:6])])],
    }
    n = 0
    for nafn, hl in p.items():
        tegs = {x["tegund"] for _, v in hl for x in v}
        efni = f"[SÝNISHORN] {nafn}: {fyrirsogn(hl)}"
        sendi(leyft, efni, rammi("".join(hluti_askriftar(s, v) for s, v in hl) + heimild(tegs), tak, efni), tak, hashlib.sha256((efni + str(dt.date.today())).encode()).hexdigest())
        n += 1
        time.sleep(0.5)
    sidan = les(c, "select min(fundid_at) d from public.voktun_atburdur")[0]["d"]
    efni = "[SÝNISHORN] Staðfesting skráningar"
    sendi(leyft, efni, rammi(f'<h1 style="margin:0 0 8px;font-size:18px;font-family:Georgia,serif">Staðfestu: Dæmigata 1, 105 Reykjavík</h1><p>Þú færð póst um þá atburði sem þú valdir.</p><p><a href="{GRUNN}/voktun/stadfesta?t=synishorn" style="display:inline-block;background:#B14E2E;color:#fff;text-decoration:none;padding:10px 16px;border-radius:8px;font-weight:600">Staðfesta</a></p><p style="font-size:13px;color:#5C554A">Tengillinn gildir í 48 klukkustundir. Ef þú skráðir ekki netfangið: gerðu ekkert, og netfanginu er eytt eftir 48 klukkustundir. <a href="{GRUNN}/voktun/afskra?t={tak}" style="color:#8D3E23">Eyða netfanginu strax</a></p>', tak, efni), tak, hashlib.sha256((efni + str(dt.date.today())).encode()).hexdigest())
    n += 1
    t = frettabref_tolur(c)
    efni = f"[SÝNISHORN] Markaðurinn í vikunni (atburðatafla frá {dags(sidan)}, tölur því lægri en í raun)"
    sendi(leyft, efni, rammi(frettabref_html(t), tak, efni), tak, hashlib.sha256((efni + str(dt.date.today())).encode()).hexdigest())
    n += 1
    print("sýnishorn send:", n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thurrt", action="store_true")
    ap.add_argument("--synishorn", action="store_true")
    ap.add_argument("--hunsa-kedju", action="store_true", help="aðeins handkeyrt próf: sleppir biðhliði á keðjuloggi")
    a = ap.parse_args()
    h = dt.datetime.now().hour + dt.datetime.now().minute / 60
    if 1.0 <= h < 7.5:
        raise SystemExit("voktun: engin keyrsla 01:00-07:30")
    c = tengja()
    t0 = time.time()
    if a.synishorn:
        synishorn(c)
        return 0
    if not a.hunsa_kedju and not kedja_lokid():
        print("keðja dagsins ekki lokið: ekkert gert, næsta keyrsla nær upp (atburðir 3 daga aftur)")
        return 0
    skra_atburdi(c, a.thurrt)
    frysta_seldist(c, a.thurrt)
    samkeyra_og_senda(c, a.thurrt)
    frettabref(c, a.thurrt)
    tiltekt(c, a.thurrt)
    if not a.thurrt:
        vidvorun_magn(c)
    print(f"lokið á {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
