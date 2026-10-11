"""cc224d — frambjóðendur og yfirlitsblöð til handvals forsíðumyndar nýbyggingaverkefna. ENGIN Fable-/API-köll.

  python scripts/cc224_myndaval_kandidatar.py --ut DIR [--verkefni ID,ID | --myndlaus] [--saekja] [--blad 20]

Leysir af yfirlitsblöð cc224b (D:\\_audit\\cc224_nybyggingar\\b8_yfirlitsblod.py), sem misstu myndir af tveimur ástæðum (cc224d §4):
  1. aðeins 12 fyrstu myndir á blaði (hringvíst mynd 0, 1, … hverrar auglýsingar) — útlitsmynd aftar í stórri auglýsingu sást aldrei;
  2. myndir lesnar EINGÖNGU úr scraper.auglysingamyndir eftir (listing_id, image_nr). Myndasækirinn sækir hverja SLÓÐ einu sinni
     (myndavisir.db, `thegar_sott`), svo mynd sem önnur auglýsing (eða eldri birting) sótti fyrst fær ALDREI röð á nýju
     auglýsingunni — bætin eru í R2 en raufin er ósýnileg töflunni. Auk þess aðeins tenure='sale'.
Hér: ALLAR myndraufar ALLRA auglýsinga (sala og leiga) á fastnúmerum verkefnisins (scraper.listings.photos_json, kanónískt
afbrigði eins og myndasækirinn: mbl `regular`, myigloo slóðin). Hver rauf leyst í sha256: (a) scraper.auglysingamyndir á
raufinni, (b) myndavisir.db slóð → sha. R2-lykill eftir sha úr scraper.auglysingamyndir (hvaða rauf sem er).
Óleystar raufar (aldrei sóttar): með --saekja sóttar með sama farvegi og myndasækirinn (myndasaekjari.Saekjari, curl_cffi,
EINN þráður, kurteist bil, ekkert framhjá Cloudflare — 403/429/challenge = stöðva) í staðbundna geymslu; ekki á R2.
Tvítök: sama sha einu sinni; nær-eins (dHash, Hamming ≤ 4) einu sinni, stærsta upplausn heldur.
Röðun á blaði: image_nr hækkandi (forsíðumyndir auglýsinga fyrst), svo nýjasta auglýsing fyrst. Ekkert þak — mörg blöð per verkefni.
Úttak (í --ut): kandidatar.csv (verkefni_id, nr, sha256, r2_lykill, listing_id, image_nr, birt, stofa, stadbundid),
yfirlitsblod/<verkefni_id>_<blað>.jpg, samantekt.txt. cc224_myndaval_lesa.py les kandidatar.csv eins og áður.
"""
import argparse
import csv
import re
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import psycopg2
from PIL import Image, ImageDraw, ImageFont, ImageOps

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

ROT = Path(r'D:\verdmat-is')
DBCFG = ROT / '.dbconfig'
VISIR = ROT / 'scraper_data' / 'myndamanifest' / 'myndavisir.db'
FRUM = ROT / 'myndir_nyb' / '_frumrit_kandidat'            # frumrit úr R2 (aðeins lesið úr lokuðu afritafötunni)
OSOTT = ROT / 'myndir_nyb' / '_frumrit_osott'              # myndir sem --saekja sótti (ekki á R2)
RCLONE = ROT / 'tools' / 'rclone' / 'rclone.exe'
CONF = ROT / 'tools' / 'rclone' / 'rclone.conf'
FRUMRIT_REMOTE = 'r2backup:verdmat-backups'
UTGAFA = 'cc224-v6'                                         # sama útgáfa og cc224_nybygging_verkefni.UTGAFA
BIL_S = 2.0                                                  # kurteist bil milli sókna (sek)
TB, TH, COLS, LH = 300, 200, 5, 30
HAMMING = 4


def dhash(p: Path) -> int | None:
    try:
        with Image.open(p) as im:
            g = ImageOps.exif_transpose(im).convert('L').resize((9, 8), Image.LANCZOS)
            px = list(g.tobytes())
        return sum(1 << i for i in range(64) if px[(i // 8) * 9 + i % 8] > px[(i // 8) * 9 + i % 8 + 1])
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ut', required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--verkefni', help='kommuskilin verkefni_id')
    g.add_argument('--myndlaus', action='store_true', help=f'öll verkefni {UTGAFA} án forsíðumyndar (mynd_lykill null)')
    ap.add_argument('--saekja', action='store_true', help='sækja óleystar raufar (myndasækjafarvegur, einn þráður, bil)')
    ap.add_argument('--blad', type=int, default=20, help='myndir per yfirlitsblað')
    a = ap.parse_args()
    UT = Path(a.ut); BLOD = UT / 'yfirlitsblod'; BLOD.mkdir(parents=True, exist_ok=True)
    FRUM.mkdir(parents=True, exist_ok=True); OSOTT.mkdir(parents=True, exist_ok=True)

    c = psycopg2.connect(open(DBCFG, encoding='utf-8-sig').read().strip()); c.set_session(readonly=True)
    cur = c.cursor(); cur.execute("set statement_timeout='300s'")
    if a.myndlaus:
        cur.execute('select verkefni_id, heiti from semantic.nybygging_verkefni where utgafa=%s and mynd_lykill is null', (UTGAFA,))
    else:
        cur.execute('select verkefni_id, heiti from semantic.nybygging_verkefni where utgafa=%s and verkefni_id = any(%s)',
                    (UTGAFA, a.verkefni.split(',')))
    V = dict(cur.fetchall())
    cur.execute('select fastnum, verkefni_id from semantic.nybygging_einingar where utgafa=%s and verkefni_id = any(%s)',
                (UTGAFA, list(V)))
    FV = dict(cur.fetchall())
    # allar auglýsingar (sala OG leiga) á fastnúmerum verkefnisins; kanónískt afbrigði eins og myndasaekjari.KANON_SQL
    cur.execute("""select l.listing_id, l.fastnum, l.source, coalesce(l.listed_at, l.first_seen_at), l.agency_name, l.tenure,
                          (t.ord - 1)::int,
                          case when l.source = 'mbl' then t.el ->> 'regular'
                               when jsonb_typeof(t.el) = 'string' then t.el #>> '{}' end
                     from scraper.listings l, jsonb_array_elements(coalesce(l.photos_json, '[]'::jsonb)) with ordinality t(el, ord)
                    where l.fastnum = any(%s)""", (list(FV),))
    RAUF = cur.fetchall()
    lids = list({r[0] for r in RAUF})
    cur.execute("""select listing_id, image_nr, sha256 from scraper.auglysingamyndir
                    where listing_id = any(%s) and utilokad_kl is null""", (lids,))
    A_RAUF = {(l, n): s.strip() for l, n, s in cur.fetchall()}
    cur.execute('select listing_id from scraper.auglysingamyndir where listing_id = any(%s) and utilokad_kl is not null', (lids,))
    UTILOKAD_L = {r[0] for r in cur.fetchall()}
    vdb = sqlite3.connect(f'file:{VISIR}?mode=ro', uri=True)

    tal = defaultdict(lambda: defaultdict(int))
    raufar = []   # (vid, sha|None, url, lid, nr, birt, stofa, tenure)
    for lid, f, src, birt, stofa, ten, nr, url in RAUF:
        vid = FV[f]; tal[vid]['raufar'] += 1
        if not url:
            tal[vid]['engin_slod'] += 1; continue
        sha = A_RAUF.get((lid, nr))
        if sha:
            tal[vid]['leyst_tafla'] += 1
        else:
            r = vdb.execute('select sha256, sokn_stada, http_kodi from slod where url=?', (url,)).fetchone()
            if r and r[0]:
                sha = r[0].strip(); tal[vid]['leyst_visir'] += 1
            elif r and r[2] == 404:
                tal[vid]['404'] += 1; continue
            else:
                tal[vid]['osott'] += 1
        raufar.append((vid, sha, url, lid, nr, birt, stofa or '', ten))

    allir_sha = list({r[1] for r in raufar if r[1]})
    cur.execute("""select distinct on (sha256) sha256, r2_lykill from scraper.auglysingamyndir
                    where sha256 = any(%s) and r2_lykill is not null and utilokad_kl is null
                    order by sha256, (afbrigdi = 'regular') desc, sott_kl desc""", (allir_sha,))
    R2 = {s.strip(): k for s, k in cur.fetchall()}
    # útilokað sha (rétthafabeiðni) fer aldrei á blað
    cur.execute('select distinct sha256 from scraper.auglysingamyndir where sha256 = any(%s) and utilokad_kl is not null', (allir_sha,))
    UTILOKAD = {s.strip() for (s,) in cur.fetchall()}

    # óleystar raufar: sækja með myndasækjafarveginum (valkvætt)
    stadb = {}
    osott = [r for r in raufar if not r[1]]
    if osott and a.saekja:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from myndasaekjari import Saekjari, Verk, CT_EXT  # noqa: E402
        import hashlib
        s = Saekjari(); sed_url = {}
        for i, (vid, _, url, lid, nr, *_r) in enumerate(osott):
            if url in sed_url:
                continue
            if i:
                time.sleep(BIL_S)
            m = s.saekja(Verk('mbl' if 'mbl.is' in url else 'myigloo', '', nr, '', url, lid))
            if m['ok']:
                sha = hashlib.sha256(m['data']).hexdigest()
                p = OSOTT / f"{sha}{CT_EXT.get(m['ct'], '.jpg')}"; p.write_bytes(m['data'])
                sed_url[url] = sha; stadb[sha] = p
            else:
                sed_url[url] = None
                print(f'  sókn {m.get("kodi")} {url}')
                if m.get('kodi') in (403, 429, 503):
                    print('  STÖÐVA: 403/429/503 — ekki farið framhjá Cloudflare'); break
        raufar = [(r[0], r[1] or sed_url.get(r[2]), *r[2:]) for r in raufar]
        for r in osott:
            tal[r[0]]['sott_nu' if sed_url.get(r[2]) else 'sokn_mistokst'] += 1

    # frumrit úr lokuðu afritafötunni (aðeins lesið)
    vantar = sorted({R2[s] for s in {r[1] for r in raufar if r[1]} if s in R2 and not (FRUM / R2[s]).exists()})
    if vantar:
        ff = UT / 'files_from.txt'; ff.write_text('\n'.join(vantar) + '\n', encoding='utf-8')
        p = subprocess.run([str(RCLONE), '--config', str(CONF), 'copy', FRUMRIT_REMOTE, str(FRUM), '--files-from', str(ff),
                            '--transfers', '16', '--no-traverse'], capture_output=True, text=True, timeout=7200)
        print('rclone rc', p.returncode, p.stderr[-300:])

    def slod(sha):
        if sha in R2:
            return FRUM / R2[sha]
        return stadb.get(sha)

    kand = []
    eftir_v = defaultdict(list)
    for r in raufar:
        eftir_v[r[0]].append(r)
    for vid, rr in eftir_v.items():
        rr.sort(key=lambda r: (r[4], -(r[5].timestamp() if r[5] else 0), r[3]))
        sed, hopar = set(), []   # hopar: [dhash, besta (r, flatarmál)]
        for r in rr:
            sha = r[1]
            if not sha or sha in sed:
                continue
            sed.add(sha)
            if sha in UTILOKAD:
                tal[vid]['utilokad'] += 1; continue
            p = slod(sha)
            if not p or not p.exists():
                tal[vid]['frumrit_vantar'] += 1; continue
            h = dhash(p)
            try:
                with Image.open(p) as im:
                    fl = im.size[0] * im.size[1]
            except Exception:
                tal[vid]['olaesileg'] += 1; continue
            for hp in hopar:
                if h is not None and hp[0] is not None and bin(h ^ hp[0]).count('1') <= HAMMING:
                    if fl > hp[2]:
                        hp[1], hp[2] = r, fl
                    tal[vid]['naer_eins'] += 1
                    break
            else:
                hopar.append([h, r, fl])
        for i, (_, r, _) in enumerate(hopar):
            sha = r[1]
            kand.append(dict(verkefni_id=vid, nr=i + 1, sha256=sha, r2_lykill=R2.get(sha, ''), listing_id=r[3], image_nr=r[4],
                             birt=r[5].date() if r[5] else '', stofa=r[6], stadbundid=str(stadb.get(sha, '')) if sha not in R2 else ''))
        tal[vid]['a_blodum'] = len(hopar)

    with open(UT / 'kandidatar.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=['verkefni_id', 'nr', 'sha256', 'r2_lykill', 'listing_id', 'image_nr', 'birt', 'stofa',
                                           'stadbundid'])
        w.writeheader(); w.writerows(kand)

    try:
        F_NR = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 24)
        F_H = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 22)
    except OSError:
        F_NR = F_H = ImageFont.load_default()
    ek = defaultdict(list)
    for k in kand:
        ek[k['verkefni_id']].append(k)
    n_blod = 0
    for vid, kk in ek.items():
        bl = [kk[i:i + a.blad] for i in range(0, len(kk), a.blad)]
        for b, hluti in enumerate(bl, 1):
            rows = (len(hluti) + COLS - 1) // COLS
            blad = Image.new('RGB', (COLS * (TB + 8) + 8, rows * (TH + LH + 8) + 44), (40, 40, 40))
            d = ImageDraw.Draw(blad)
            d.text((10, 10), f'{vid} · {V.get(vid, "?")} · blað {b}/{len(bl)}', fill=(255, 255, 255), font=F_H)
            for i, k in enumerate(hluti):
                # númerið á eigin rönd OFAN við myndina: merki ofan á myndinni huldi lógó stofa í horninu (cc224d)
                x, y = 8 + (i % COLS) * (TB + 8), 44 + (i // COLS) * (TH + LH + 8)
                d.rectangle([x, y, x + TB, y + LH - 2], fill=(255, 220, 0))
                d.text((x + 5, y), str(k['nr']), fill=(0, 0, 0), font=F_NR)
                p = FRUM / k['r2_lykill'] if k['r2_lykill'] else Path(k['stadbundid'])
                try:
                    with Image.open(p) as im:
                        im = ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((TB, TH))
                        blad.paste(im, (x + (TB - im.size[0]) // 2, y + LH + (TH - im.size[1]) // 2))
                except Exception as e:  # noqa: BLE001
                    d.text((x + 10, y + LH + 80), f'villa {type(e).__name__}', fill=(255, 80, 80), font=F_H)
            blad.save(BLOD / f'{vid}_{b:02d}.jpg', 'JPEG', quality=82); n_blod += 1

    lin = ['verkefni_id\theiti\t' + '\t'.join(['raufar', 'leyst_tafla', 'leyst_visir', '404', 'osott', 'sott_nu', 'sokn_mistokst',
                                               'utilokad', 'frumrit_vantar', 'olaesileg', 'naer_eins', 'a_blodum'])]
    for vid in sorted(V, key=lambda v: V[v]):
        t = tal.get(vid, {})
        lin.append(f'{vid}\t{V[vid]}\t' + '\t'.join(str(t.get(k, 0)) for k in ['raufar', 'leyst_tafla', 'leyst_visir', '404',
                   'osott', 'sott_nu', 'sokn_mistokst', 'utilokad', 'frumrit_vantar', 'olaesileg', 'naer_eins',
                   'a_blodum']))
    (UT / 'samantekt.txt').write_text('\n'.join(lin) + '\n', encoding='utf-8')
    print('\n'.join(lin))
    print(f'verkefni {len(V)} · með frambjóðendur {len(ek)} · frambjóðendur {len(kand)} · blöð {n_blod}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
