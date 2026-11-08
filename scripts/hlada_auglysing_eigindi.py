#!/usr/bin/env python
"""cc316 — hleðari í public.auglysing_eigindi (GO Danna 04.11.2026).
Sjálfgefið ÞURRKEYRSLA: les DB + parsed_mbl.db, skrifar samantekt, ekkert í DB. `--ut SLÓÐ` vistar raðirnar.
`--skrifa`: uppfærir í einni færslu. Verk verdmat-nightly-auglysing-eigindi keyrir þetta 06:40.
rc: 0 í lagi / 3 villa / 4 hlið felldi skrif (taflan stendur þá óbreytt).

Reglur:
  Rammi: v_eign_virk_auglysing, mbl, sala, íbúð (sub_type=apartment), fastnum til, ekki fjöleiningar-fastnum,
         og eignin á virka auglýsingu sem sást fyrst >= FRA (fast, ekki rúllandi).
  Gildi: reitur er já ef minnst ein virk auglýsing eignarinnar segir 1 og engin segir 0.
         0, NULL eða ósamræmi milli auglýsinga → engin röð (birtist Óþekkt).
  bilskur_staedi: parking_shelter → staedi_bilakjallara; ella bilskur → bilskur_eda_geymsla; ella parking → staedi.
  Dagsetning: listed_at, ella first_seen_at, á nýjustu auglýsingu (first_seen_at, listing_id).
"""
import argparse, collections, datetime as D, json, sqlite3, sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

FRA = D.datetime(2026, 8, 1, tzinfo=D.timezone.utc)
PARSED = "file:D:/verdmat-is/scraper_data/parsed_mbl.db?mode=ro"
REITIR = ("lyfta", "svalir", "bilskur", "parking", "parking_shelter")
MIN_RADIR = 2000  # hlið: hrun í þekju stöðvar skrif (mælt 04.11: 5.992 raðir)
MIN_HLUTFALL = 0.6  # hlið: ný keyrsla má ekki falla undir 60 % af núverandi töflu
LOGG = Path("D:/verdmat-is/scraper_data/logs")


def skra(texti):
    nu = D.datetime.now(D.timezone.utc)
    with open(LOGG / f"auglysing_eigindi_{nu:%Y%m}.log", "a", encoding="utf-8") as f:
        f.write(f"{nu:%Y-%m-%dT%H:%M:%SZ} {texti}"+chr(10))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skrifa", action="store_true")
    ap.add_argument("--dbconfig", default=r"D:\verdmat-is\.dbconfig")
    ap.add_argument("--ut", help="vista raðir sem JSON (þurrkeyrsla/próf)")
    a = ap.parse_args()
    c = psycopg2.connect(Path(a.dbconfig).read_text(encoding="utf-8-sig").strip(), connect_timeout=15, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
    # Lesháttur per færslu, aldrei set_session(readonly): hún lekur um 6543-pooler (cc231).
    c.rollback()
    k = c.cursor()
    k.execute("set transaction read " + ("write" if a.skrifa else "only"))
    k.execute("set local statement_timeout='120s'")
    k.execute("""select v.listing_id,l.source_listing_id,v.fastnum,l.first_seen_at,l.listed_at
      from scraper.v_eign_virk_auglysing v join scraper.listings l using(listing_id)
      where v.source='mbl' and v.tenure='sale' and v.category='residential'
        and l.sub_type='apartment' and v.fastnum is not null
        and v.fastnum not in (select fastnum from public.v_fjoleining_fastnum)""")
    augl = collections.defaultdict(list)
    for r in k.fetchall():
        augl[r[2]].append(r)
    ramm = {f: sorted(L, key=lambda r: (r[3], r[0])) for f, L in augl.items() if any(r[3] >= FRA for r in L)}

    s = sqlite3.connect(PARSED, uri=True, timeout=20)
    s.execute("pragma query_only=1")
    P = {str(x[0]): dict(zip(REITIR, x[1:]))
         for x in s.execute(f"select source_listing_id,{','.join(REITIR)} from parsed_mbl_sale")}

    radir, blond = [], collections.Counter()

    def ja(L, reitur):
        v = {P[str(r[1])][reitur] for r in L if str(r[1]) in P} - {None}
        if len(v) > 1:
            blond[reitur] += 1
        return v == {1}

    for f, L in ramm.items():
        sid = L[-1]
        dags = (sid[4] or sid[3]).date().isoformat()

        def rod(key, val):
            radir.append((f, key, json.dumps(val, separators=(",", ":")), str(sid[1]), dags))

        if ja(L, "lyfta"):
            rod("lyfta", {"til": True})
        if ja(L, "svalir"):
            rod("svalir", {"til": True})
        g = ("staedi_bilakjallara" if ja(L, "parking_shelter")
             else "bilskur_eda_geymsla" if ja(L, "bilskur")
             else "staedi" if ja(L, "parking") else None)
        if g:
            rod("bilskur_staedi", {"gerd": g})

    # Samantekt gegn því sem spjaldið sýnir núna
    k.execute("""select fastnum,attr_key,source,value from public.property_attributes
      where superseded_at is null and attr_key in ('lyfta','svalir','bilskur_staedi') and fastnum=any(%s)""", (list(ramm),))
    til = collections.defaultdict(list)
    for f, kk, so, v in k.fetchall():
        til[(f, kk)].append((so, v))
    fyll, vik, nei, gerd = (collections.Counter() for _ in range(4))
    eignir = set()
    for f, kk, v, _, _ in radir:
        if kk == "bilskur_staedi":
            gerd[json.loads(v)["gerd"]] += 1
        if til.get((f, kk)):
            for so, gi in til[(f, kk)]:
                vik[f"{kk}/{so}"] += 1
                if gi.get("til") is False or gi.get("gerd") == "ekkert":
                    nei[f"{kk}/{so}"] += 1
        else:
            fyll[kk] += 1
            eignir.add(f)
    samantekt = (json.dumps(dict(
        eignir_virkar_alls=len(augl), rammi_eignir=len(ramm), radir_alls=len(radir),
        ny_gildi_birt=sum(fyll.values()), per_lykil_ny=fyll, eignir_med_nytt_gildi=len(eignir),
        bilskur_gerd=gerd, vikur_fyrir_skradri=vik, skrad_nei_a_moti_ja=nei,
        eignir_med_osamraemi_per_reit=blond), ensure_ascii=False))
    print(samantekt)
    if a.ut:
        Path(a.ut).write_text(json.dumps(radir, ensure_ascii=False), encoding="utf-8")

    if not a.skrifa:
        c.rollback()
        print("ÞURRKEYRSLA: ekkert skrifað")
        return 0
    k.execute("select count(*) from public.auglysing_eigindi")
    nu = k.fetchone()[0]
    if len(radir) < MIN_RADIR or len(radir) < MIN_HLUTFALL * nu:
        skra(f"HLIÐ: {len(radir)} raðir, {nu} í töflu; ekkert skrifað | {samantekt}")
        c.rollback()
        print("HLIÐ: of fáar raðir", len(radir), "í töflu", nu)
        return 4
    k.execute("set local lock_timeout='5s'")
    k.execute("create temp table n(fastnum bigint,attr_key text,value jsonb,source_listing_id text,source_date date) on commit drop")
    execute_values(k, "insert into n values %s", radir, page_size=1000)
    k.execute("delete from public.auglysing_eigindi t where not exists(select 1 from n where n.fastnum=t.fastnum and n.attr_key=t.attr_key)")
    k.execute("""insert into public.auglysing_eigindi(fastnum,attr_key,value,source_listing_id,source_date)
      select * from n on conflict(fastnum,attr_key) do update
      set value=excluded.value,source_listing_id=excluded.source_listing_id,source_date=excluded.source_date,hladid_at=now()""")
    c.commit()
    skra(f"skrifað {len(radir)} (áður {nu}) | {samantekt}")
    print("skrifað", len(radir))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # taflan stendur óbreytt: færslan er ekki staðfest
        skra(f"VILLA {type(e).__name__}: {e}")
        raise SystemExit(3)
