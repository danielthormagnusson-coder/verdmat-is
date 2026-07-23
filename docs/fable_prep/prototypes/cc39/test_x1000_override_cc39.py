"""test_x1000_override_cc39.py — sjálfstætt próf á gildisvörninni (READ-ONLY, ekkert í DB).

Keyrir gegn RAUNVERULEGU D:\\kaupskra.csv + tilbúnum jaðartilvikum. Audit-slóðin er
beint í tmp svo prófið skrifar ekkert á D:\\. Exit 0 = allt grænt.

  1. raun-CSV: nákvæmlega 3 leiðréttingar = {744059, 744084, 744085}
  2. leiðrétt gildi (þús.kr): 22.000 / 25.990 / 18.000 → nominal == lifandi DB-gildin
  3. lögmætar stór-raðir ósnertar (fjöleininga-skjöl + dýrasta lögmæta kr/m²-röðin)
  4. sjálf-útrennsli: "HMS-lagað" afrit (KAUPVERD þegar ÷1000) → 0 leiðréttingar
  5. jaðar: EINFLM vantar/<=10 → aldrei leiðrétt (fellur á vikulega vörðinn)
  6. jaðar: ÷1000-gildi > 2M kr/m² (ofur-lúx ×1000) → EKKI leiðrétt (mannlegt mat)
  7. audit-JSONL: 3 línur með upphafsgildum
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from x1000_override_proto import apply_x1000_override  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KAUPSKRA_CSV = Path(r"D:\kaupskra.csv")
EXPECTED_F = {744059, 744084, 744085}
# lifandi DB-gildi (sales_history.kaupverd_nominal, mælt 2026-07-23 cc39-probe)
DB_NOMINAL = {744059: 22_000_000, 744084: 25_990_000, 744085: 18_000_000}
# lögmætar stór-raðir sem MEGA EKKI breytast (fjöleininga-skjöl + toppur lögmæta kr/m²-halans)
LEGIT_F = {667958: 10_000_000, 545113: 4_444_932, 723979: 481_298, 744841: 725_000}

fails = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


_fd, _tmp = tempfile.mkstemp(suffix="_cc39_audit.jsonl")
os.close(_fd)  # mkstemp skilur eftir opinn fd — lokum svo unlink virki á Windows
tmp_audit = Path(_tmp)

print("=== 1+2+3: raun-CSV ===")
kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
out, entries = apply_x1000_override(kp, audit_log=tmp_audit)
got_f = {e["faerslunumer"] for e in entries}
check("nákvæmlega 3 leiðréttingar", len(entries) == 3, f"fékk {len(entries)}")
check("faerslunumer == vænt sett", got_f == EXPECTED_F, f"fékk {sorted(got_f)}")
by_f = {e["faerslunumer"]: e for e in entries}
for f, nom_db in DB_NOMINAL.items():
    e = by_f.get(f)
    nom_new = round(e["kaupverd_corrected_thus"] * 1000) if e else None
    check(f"f={f}: derived nominal == DB", nom_new == nom_db,
          f"derived={nom_new:,} DB={nom_db:,}" if e else "vantar")
out_f = pd.to_numeric(out["FAERSLUNUMER"], errors="coerce")
out_kv = pd.to_numeric(out["KAUPVERD"], errors="coerce")
for f, kv_orig in LEGIT_F.items():
    vals = set(out_kv[out_f == f].round().astype("int64").tolist())
    check(f"lögmæt röð f={f} ósnert", vals == {kv_orig}, f"gildi={sorted(vals)}")

print("=== 4: sjálf-útrennsli (HMS-lagað afrit) ===")
fixed = kp[pd.to_numeric(kp["FAERSLUNUMER"], errors="coerce").isin(EXPECTED_F)].copy()
fixed["KAUPVERD"] = (pd.to_numeric(fixed["KAUPVERD"], errors="coerce") / 1000).round()
_, e_fixed = apply_x1000_override(fixed, audit_log=tmp_audit)
check("0 leiðréttingar á löguðum gildum", len(e_fixed) == 0, f"fékk {len(e_fixed)}")

print("=== 5+6: jaðartilvik ===")
edge = pd.DataFrame({
    "FAERSLUNUMER": [1, 2, 3],
    "FASTNUM": [11, 12, 13],
    "THINGLYSTDAGS": ["2026-01-01"] * 3,
    "KAUPVERD": [22_000_000, 22_000_000, 300_000_000],  # þús.kr
    "EINFLM": [float("nan"), 5.0, 100.0],
})
# röð 1: EINFLM vantar; röð 2: EINFLM<=10; röð 3: hrátt 3G kr/m², ÷1000 = 3M > 2M kap
_, e_edge = apply_x1000_override(edge, audit_log=tmp_audit)
check("EINFLM-lausar + ofur-lúx raðir ALDREI leiðréttar", len(e_edge) == 0,
      f"fékk {len(e_edge)}")
# mótpróf: gilt ×1000-tilvik í jaðarforminu virkjar
pos = pd.DataFrame({
    "FAERSLUNUMER": [9], "FASTNUM": [99], "THINGLYSTDAGS": ["2026-01-01"],
    "KAUPVERD": [25_000_000], "EINFLM": [100.0],  # hrátt 250M kr/m², ÷1000=250þ
})
_, e_pos = apply_x1000_override(pos, audit_log=tmp_audit)
check("mótpróf: gilt ×1000-tilvik virkjar", len(e_pos) == 1, f"fékk {len(e_pos)}")

print("=== 7: audit-JSONL ===")
lines = [json.loads(l) for l in tmp_audit.read_text(encoding="utf-8").splitlines()]
check("audit ber 3+1 línur (raun + mótpróf)", len(lines) == 4, f"fékk {len(lines)}")
orig_ok = all(
    l["kaupverd_original_thus"] == l["kaupverd_corrected_thus"] * 1000
    for l in lines)
check("upphafsgildi = 1000× leiðrétt gildi í öllum línum", orig_ok)
tmp_audit.unlink(missing_ok=True)

print(f"\n{'ALLT GRÆNT' if not fails else 'FAIL: ' + ', '.join(fails)} "
      f"({len(fails)} af 13+ tékkum féllu)")
sys.exit(1 if fails else 0)
