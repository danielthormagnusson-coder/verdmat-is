"""cc224b §10 — les handval forsíðumynda inn í skrá sem næturkeyrslan notar.

  python scripts/cc224_myndaval_lesa.py [--myndaval CSV] [--kandidatar CSV]

myndaval.csv (CC/Danni, handvalið af yfirlitsblöðum; Danni má leiðrétta): verkefni_id, heiti, valin_mynd (nr á blaði eða
„engin"), tegund (ljósmynd/3D), bordi (ja = lógó/borði stofu á myndinni, valin aðeins ef engin hrein fannst; tómt = ekki
metið, cc224b), athugasemd. kandidatar.csv (cc224_myndaval_kandidatar.py, cc224d; áður b8_yfirlitsblod.py): verkefni_id,
nr, sha256, r2_lykill, listing_id, image_nr, birt, stofa[, stadbundid] — númer blaðsins → mynd. Mynd sem er ekki í R2
(stadbundid, sótt af kandídataskriftunni) er hafnað: næturkeyrslan les frumrit eingöngu úr afritafötunni.
Úttak: scripts/nybyggingar_myndaval.csv (verkefni_id, sha256, r2_lykill, listing_id, birt, stofa, tegund, bordi, athugasemd);
„engin" fær tóma mynd (hlutlaus flötur, aldrei næstbesta mynd). Verkefni sem vantar í skrána fá enga mynd.
"""
import argparse
import csv
import sys
from pathlib import Path

UT = Path(__file__).resolve().parent / 'nybyggingar_myndaval.csv'
AUDIT = Path(r'D:\_audit\cc224_nybyggingar')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--myndaval', default=str(AUDIT / 'myndaval.csv'))
    ap.add_argument('--kandidatar', default=str(AUDIT / 'kandidatar.csv'))
    a = ap.parse_args()
    K = {}
    for k in csv.DictReader(open(a.kandidatar, encoding='utf-8-sig')):
        K[(k['verkefni_id'], k['nr'])] = k
    radir, villur = [], []
    for r in csv.DictReader(open(a.myndaval, encoding='utf-8-sig')):
        nr = r['valin_mynd'].strip().lower()
        if nr == 'engin':
            radir.append(dict(verkefni_id=r['verkefni_id'], sha256='', r2_lykill='', listing_id='', birt='', stofa='',
                              tegund='', bordi='', athugasemd=r['athugasemd']))
            continue
        k = K.get((r['verkefni_id'], nr))
        if not k:
            villur.append(f"{r['verkefni_id']}: mynd {nr} ekki á blaði"); continue
        if r['tegund'] not in ('ljósmynd', '3D'):
            villur.append(f"{r['verkefni_id']}: tegund {r['tegund']!r}"); continue
        if not k['r2_lykill']:
            villur.append(f"{r['verkefni_id']}: mynd {nr} er ekki í R2 ({k.get('stadbundid')})"); continue
        if r.get('bordi', '') not in ('', 'ja', 'nei'):
            villur.append(f"{r['verkefni_id']}: bordi {r['bordi']!r}"); continue
        radir.append(dict(verkefni_id=r['verkefni_id'], sha256=k['sha256'], r2_lykill=k['r2_lykill'], listing_id=k['listing_id'],
                          birt=k['birt'], stofa=k['stofa'], tegund=r['tegund'], bordi=r.get('bordi', ''), athugasemd=r['athugasemd']))
    if villur:
        print('[STOPP]', *villur, sep='\n  '); return 3
    ids = [x['verkefni_id'] for x in radir]
    assert len(ids) == len(set(ids)), 'tvískráð verkefni'
    with open(UT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(radir[0])); w.writeheader(); w.writerows(sorted(radir, key=lambda x: x['verkefni_id']))
    print(f"[OK] {UT.name}: {len(radir)} verkefni · mynd {sum(1 for x in radir if x['sha256'])} · engin {sum(1 for x in radir if not x['sha256'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
