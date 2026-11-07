"""lifecycle_sweep_lotur_test.py — cc324: kort-lota sveltir ekki, leigu-hringur með bendli.
Ekkert net, engin DB: öll load_*/write_events/Transport skipt út; ríki í bráðabirgðamöppu.
Keyrsla úr rót: python scripts/lifecycle_sweep_lotur_test.py  (rc 0 = allt stenst)."""
import json
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lifecycle_sweep_mbl as m  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UTC = timezone.utc
FOLL = []


def chk(nafn, skil, smat=""):
    print(("OK   " if skil else "FALL ") + nafn + (" | " + str(smat) if smat != "" else ""))
    if not skil:
        FOLL.append(nafn)


class Sim:
    def __init__(s, leiga=7075, kort=21650, sala=0, last_rent="2026-10-16T12:14:08+00:00",
                 last_sale="2026-11-06T13:54:00+00:00", gagn=None, drepa_eftir=None):
        s.d = Path(tempfile.mkdtemp())
        s.nu = datetime(2026, 11, 8, 6, 0, 5, tzinfo=UTC)
        s.drepa_eftir = drepa_eftir
        s.leiga = [(str(5_000_000 + i), 100, None) for i in range(leiga)]
        s.kort = [(str(3_000_000 + i), 100, 1, s.nu - timedelta(days=3)) for i in range(kort)]
        s.sala = [(str(1_000_000 + i), 100, None) for i in range(sala)]
        s.horfin = gagn or set()
        s.prior = set()
        s.events = []
        s.found = []
        s.rot = {"rent": 0, "sale": 0}
        s.request_count = 0
        m.STATE_PATH = s.d / "s.json"
        m.get_scraper_data_dir = lambda: s.d
        m.now_utc = lambda: s.nu
        m.delta_requests_24h = lambda now: 134
        m.load_active_ids = lambda c, t: s.leiga if t == "rent" else s.sala
        m.load_card_ids = lambda c: s.kort
        m.load_prior_absent_set = lambda c, t, b=None: set(s.prior)
        m.write_events = lambda c, e, log=print, found=(): (s.events.extend(e), s.found.extend(found))
        m.Transport = lambda spacing=120, log=print: s
        st = m._default_state()
        st["rent"]["last_completed_at"] = last_rent
        st["sale"].update(enabled=True, last_completed_at=last_sale)
        m.save_sweep_state(st)

    def gql(s, q):
        if s.drepa_eftir is not None and s.request_count >= s.drepa_eftir:
            raise m.KillSwitch("próf")
        s.nu += timedelta(seconds=120)
        s.request_count += 1
        rot = "rent" if "rentals_property" in q else "sale"
        s.rot[rot] += 1
        ids = re.search(r"_in:\[([^\]]*)\]", q).group(1).split(",")
        rows = []
        for i in ids:
            if i in s.horfin:
                continue
            if rot == "rent":
                rows.append({"id": int(i), "price": 100})
            else:
                rows.append({"eign_id": int(i), "verd": 100, "syna": True})
        return {"data": {("rentals_property" if rot == "rent" else "fs_fasteign"): rows}}

    def keyra(s, dagar=0, dry=False, cap=None):
        s.nu = datetime(2026, 11, 8, 6, 0, 5, tzinfo=UTC) + timedelta(days=dagar)
        s.request_count = 0
        s.rot = {"rent": 0, "sale": 0}
        L = []
        m.run_scheduled(None, dry, log=L.append, budget_cap=cap)
        return L

    def st(s):
        return json.loads(m.STATE_PATH.read_text(encoding="utf-8"))


# 1. Núverandi inntak: kort fær beiðnir þótt leiga sé > þak
S = Sim()
L = S.keyra()
k = [x for x in L if x.startswith("[card] budget")][0]
b = int(re.search(r"budget=(\d+)", k).group(1))
chk("kort fær afgang þótt leiga (443) > þak", b >= 200, k)
chk("leiga fer af stað með bendil", 0 < S.st()["rent"]["cursor"] < S.st()["rent"]["round_total"], S.st()["rent"]["cursor"])
chk("heild innan fjárhags 355", S.request_count <= 355, S.request_count)
# 2. Leiga klárast á nokkrum dögum; last_completed uppfærist aðeins þá
d = 0
while S.st()["rent"]["last_completed_at"].startswith("2026-10-16") and d < 20:
    d += 1
    S.keyra(dagar=d)
chk("leigu-hringur klárast innan 7 daga", d < 7, "%d dagar" % (d + 1))
chk("eftir hring: bendill hreinsaður", S.st()["rent"]["round_file"] is None and S.st()["rent"]["cursor"] == 0)
# 3. Dráp í miðjum hring: heldur áfram frá bendli
S = Sim(leiga=1600, kort=0, drepa_eftir=30)
try:
    S.keyra()
    chk("dráp kastar", False)
except m.KillSwitch:
    pass
c = S.st()["rent"]["cursor"]
chk("bendill vistaður við dráp", c == 30 * 16, c)
S.drepa_eftir = None
S.keyra(dagar=1)
chk("hringur kláraðist frá bendli, engin tvítekin beiðni", S.rot["rent"] == 100 - 30, S.rot["rent"])
# 4. Tvö strik: strik í hringnum er ekki annað strik; fyrra strik gefur withdrawn
S = Sim(leiga=32, kort=0, gagn={"5000000", "5000001"})
S.prior = {"5000001"}
S.keyra()
t = {e["id"]: e["event_type"] for e in S.events}
chk("fyrsta fjarvera = confirmed_absent_1", t.get("5000000") == "confirmed_absent_1", t)
chk("fyrra strik = withdrawn_confirmed", t.get("5000001") == "withdrawn_confirmed", t)
chk("sidast_fundin á lifandi", len(S.found) == 30, len(S.found))
chk("sweep_id ber _rent_", all("_rent_" in e["evidence"]["sweep_id"] for e in S.events))
# 5. Sala fær frátekningu sína
S = Sim(leiga=7075, kort=21650, sala=3200, last_sale="2026-10-25T00:00:00+00:00")
S.keyra()
st = S.st()
chk("sala fer af stað samhliða korti og leigu", st["sale"]["cursor"] >= 1600, st["sale"]["cursor"])
chk("leiga fær frátekt sína", st["rent"]["cursor"] >= 1600, st["rent"]["cursor"])
# 6. Ekkert á gjalddaga: allt í kort
S = Sim(leiga=7075, kort=21650, last_rent="2026-11-07T05:00:00+00:00")
L = S.keyra()
chk("leiga ekki á gjalddaga: kort fær allt", S.request_count >= 340 and S.rot["rent"] == 0, S.request_count)
# 7. Eldra ríki (án bendilreita) les
S = Sim()
st = S.st()
st["rent"].pop("round_file", None)
st["rent"].pop("cursor", None)
m.save_sweep_state(st)
S.keyra()
chk("eldra ríki án bendilreita", S.st()["rent"]["cursor"] > 0)
# 8. Þurrkeyrsla: 0 beiðnir, 0 atburðir, ríki óbreytt
S = Sim()
a = m.STATE_PATH.read_text(encoding="utf-8")
L = S.keyra(dry=True)
chk("þurrkeyrsla: 0 beiðnir, ekkert skrifað",
    S.request_count == 0 and not S.events and a == m.STATE_PATH.read_text(encoding="utf-8"), L[-1])
chk("þurrkeyrsla: engin keyrslulína", not (S.d / m.RUN_LOG_NAME).exists())
# 9. Keyrslulína
S = Sim()
S.keyra()
l = json.loads((S.d / m.RUN_LOG_NAME).read_text(encoding="utf-8").splitlines()[-1])
chk("keyrslulína telur", l["requests"] == S.request_count and l["card"] + l["rent"] + l["sale"] == l["requests"], l)
# 10. budget-cap
S = Sim()
S.keyra(cap=8)
chk("--budget-cap virt", S.request_count <= 8, S.request_count)
# 11. Bakkun: gamla vélin les aðeins last_completed_at + epoch; þau standa í miðjum hring
S = Sim()
S.keyra()
chk("bakkun: last_completed_at óbreytt í miðjum hring", S.st()["rent"]["last_completed_at"].startswith("2026-10-16"))
# 12. Falspróf: án þaksins (gamla reglan) fellur próf 1
vist = m.RENT_RUN_RESERVE
vist_g = m.CARD_MIN_RUN
m.RENT_RUN_RESERVE = 10 ** 6
m.CARD_MIN_RUN = 0
S = Sim()
L = S.keyra()
b0 = int(re.search(r"budget=(\d+)", [x for x in L if x.startswith("[card] budget")][0]).group(1))
chk("falspróf: án þaks verður card_budget 0", b0 == 0, b0)
m.RENT_RUN_RESERVE = vist
m.CARD_MIN_RUN = vist_g
# 13. Gólf: lítill fjárhagur fer í kort, leigu ekki frosið (handpróf --budget-cap 8)
S = Sim()
S.keyra(cap=8)
chk("gólf: --budget-cap 8 = 8 kortbeiðnir, 0 leiga", S.rot["sale"] == 8 and S.rot["rent"] == 0 and S.st()["rent"].get("round_file") is None, S.rot)
# 14. Gólf: frátekning stærri en fjárhagur skilur kort ekki eftir með 0
S = Sim(sala=3200, last_sale="2026-10-25T00:00:00+00:00")
L = S.keyra(cap=200)
b1 = int(re.search(r"budget=(\d+)", [x for x in L if x.startswith("[card] budget")][0]).group(1))
chk("gólf: frátekning 220 > fjárhagur 200, kort fær 50", b1 == 50, b1)
print("FÖLL: %d" % len(FOLL))
sys.exit(1 if FOLL else 0)
