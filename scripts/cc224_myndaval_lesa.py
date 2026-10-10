"""cc224b §10 — les handval forsíðumynda inn í skrá sem næturkeyrslan notar.

  python scripts/cc224_myndaval_lesa.py [--myndaval CSV] [--kandidatar CSV]

myndaval.csv (CC/Danni, handvalið af yfirlitsblöðum; Danni má leiðrétta): verkefni_id, heiti, valin_mynd (nr á blaði eða
„engin"), tegund (ljósmynd/3D), athugasemd. kandidatar.csv (b8_yfirlitsblod.py): verkefni_id, nr, sha256, r2_lykill,
listing_id, image_nr, birt, stofa — númer blaðsins → mynd.
Úttak: scripts/nybyggingar_myndaval.csv (verkefni_id, sha256, r2_lykill, listing_id, birt, stofa, tegund, athugasemd);
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
                              tegund='', athugasemd=r['athugasemd']))
            continue
        k = K.get((r['verkefni_id'], nr))
        if not k:
            villur.append(f"{r['verkefni_id']}: mynd {nr} ekki á blaði"); continue
        if r['tegund'] not in ('ljósmynd', '3D'):
            villur.append(f"{r['verkefni_id']}: tegund {r['tegund']!r}"); continue
        radir.append(dict(verkefni_id=r['verkefni_id'], sha256=k['sha256'], r2_lykill=k['r2_lykill'], listing_id=k['listing_id'],
                          birt=k['birt'], stofa=k['stofa'], tegund=r['tegund'], athugasemd=r['athugasemd']))
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
