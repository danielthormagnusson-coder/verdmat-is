"""run_extraction.py — driver for the extraction engine (EXTRACTION ÞREP 3-5).

  --value-seeded            value every extracted listing that has no valuation yet (NO Haiku).
  --forward N [--trigger T] extract up to N fresh distinct lysingar via Haiku, then value them.

Hard cost guard on the forward path (a cache regression must never silently burn $$):
  --max-n        per-run ceiling on Haiku calls (default 500).
  --daily-cap-usd  cumulative Haiku spend allowed per calendar day (default 10.0); tracked in
                 scraper_data/extraction_cost_state.json. effective N = min(N, max-n, budget-left).
  The per-run cost (calls × per-call) is printed (lands in the nightly promote log / morning report)
  and added to today's tally.

Two connections: read-only (autocommit) for model load + fetch; read-write (SET TRANSACTION
READ WRITE per tx) for the inserts. The Haiku key is read ONLY from D:\env.local via
model_quality_eval.anthropic_key (dotenv_values — never exported, never os.environ); no client is
created on --value-seeded.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"D:\\")

from model_quality_eval import load_models_freeze_anchored, anthropic_key  # noqa: E402
import extraction_engine as E  # noqa: E402

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
COST_STATE = Path(r"D:\verdmat-is\scraper_data\extraction_cost_state.json")
PER_CALL_USD = 0.0071  # VÉL 1 empirical Haiku cost per extraction


def _today():
    return datetime.now().date().isoformat()


def _load_today_spend():
    if COST_STATE.exists():
        try:
            return float(json.loads(COST_STATE.read_text(encoding="utf-8")).get(_today(), 0.0))
        except Exception:
            return 0.0
    return 0.0


def _record_spend(amount):
    data = {}
    if COST_STATE.exists():
        try:
            data = json.loads(COST_STATE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data[_today()] = round(float(data.get(_today(), 0.0)) + amount, 4)
    # keep only the last ~30 days
    for k in sorted(data)[:-30]:
        data.pop(k, None)
    COST_STATE.write_text(json.dumps(data), encoding="utf-8")


def _connect():
    dsn = DBCONFIG.read_text(encoding="utf-8-sig").strip()
    ro = psycopg2.connect(dsn); ro.autocommit = True; ro.set_session(readonly=True)
    rw = psycopg2.connect(dsn); rw.autocommit = False
    return ro, rw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--value-seeded", action="store_true")
    ap.add_argument("--forward", type=int, default=0)
    ap.add_argument("--max-n", type=int, default=500)
    ap.add_argument("--daily-cap-usd", type=float, default=10.0)
    ap.add_argument("--trigger", default="nightly", choices=["nightly", "ondemand"])
    ap.add_argument("--confirm", action="store_true")
    # cc75 — BRÚIN Í EIGINDALAGIÐ ER OPT-IN, EKKI SJÁLFGEFIN.
    #
    # Hún er OPT-IN af ástæðu og hún er ekki sú venjulega („nýtt sé slökkt
    # fyrst"): brúin skrifar í public.property_attributes, sem PROD LES
    # SAMSTUNDIS. Fari hún af stað áður en verdmat-ai er pushað birtast
    # eigindin á prod með TÓMRI uppruna-pillu — `upprunaHeiti` í lifandi
    # útgáfu er switch án `default` og þekkir ekki lindina 'auglysing'.
    # Eigindi án uppruna er einmitt það sem uppruna-agi lagsins bannar.
    #
    # Réttri röð er því haldið af rofanum sjálfum: push → --bridge → prófun.
    # Að tengja hana inn í nightly_delta_chain.sh er SÉR ÁKVÖRÐUN (sjá §8 í
    # audit-skjalinu: 47,4% lenda á margföldunarþaki leiðréttingarlagsins).
    ap.add_argument("--bridge", action="store_true",
                    help="keyra brúna í eigindalagið að lokinni extraction/valuation")
    ap.add_argument("--bridge-only", action="store_true",
                    help="keyra EINGÖNGU brúna (engin Haiku, engin verðmatsfrysting)")
    args = ap.parse_args()

    ro, rw = _connect()
    # Líkönin þarf aðeins verðmatsfrystingin; brúin er hrein SQL-aðgerð.
    models = None if (args.bridge_only and not (args.forward or args.value_seeded)) \
        else load_models_freeze_anchored(ro)

    # cc75: kostnaðarþak og dry-run STÖÐVA Haiku-hlutann — en máttu ekki
    # lengur stöðva keyrsluna alla, því brúin (ókeypis SQL) á að fá að
    # ganga þótt engir nýir útdrættir séu keyptir. Áður var þetta `return 0`.
    haiku_stodvud = False

    if args.forward:
        spent = _load_today_spend()
        budget_calls = int(max(0.0, args.daily_cap_usd - spent) / PER_CALL_USD)
        effective_n = min(args.forward, args.max_n, budget_calls)
        print(f"forward: requested={args.forward} max_n={args.max_n} "
              f"daily_cap=${args.daily_cap_usd} spent_today=${spent:.4f} "
              f"budget_calls={budget_calls} -> effective_n={effective_n}")
        if effective_n <= 0:
            print("EXTRACTION SKIPPED: daily cost cap reached (or zero budget).")
            haiku_stodvud = True
        else:
            need = E.fetch_listings_needing_extraction(ro, effective_n)
            print(f"forward: {len(need)} fresh distinct lysingar to extract (fresh-first)")
            if not args.confirm:
                print("[dry] re-run with --confirm to call Haiku.")
                haiku_stodvud = True
            else:
                import anthropic
                # Haiku key ONLY from D:\env.local (anthropic_key -> dotenv_values);
                # CC env stays keyless.
                client = anthropic.Anthropic(api_key=anthropic_key(), timeout=60.0,
                                             max_retries=0)
                res = E.extract_and_store(rw, client, need, args.trigger)
                _record_spend(res["cost_est_usd"])
                print(f"extract: {res} | day_total=${_load_today_spend():.4f}")

    if not haiku_stodvud and (args.value_seeded or args.forward):
        rows = E.fetch_extracted_listings_to_value(ro)
        print(f"value: {len(rows)} extracted listings without a valuation")
        if args.confirm or args.value_seeded:
            E.value_listings(rw, models, rows)
        else:
            print("[dry] re-run with --confirm to write valuations.")

    # cc75 — BRÚIN í eigindalagið. OPT-IN (--bridge / --bridge-only, sjá
    # rökin við rofann). Ódýr: eitt SQL-kall, engin Haiku, engin
    # kostnaðarfærsla. Hún gengur yfir ALLT virka framboðið, ekki bara
    # útdrættina úr þessari keyrslu — baklistinn étst um nætur og eldri
    # útdrættir sem aldrei komust í eigindalagið eiga að skila sér líka.
    #
    # HÖRÐ REGLA: brúin fellir ALDREI nóttina. Hún er viðbót ofan á
    # extraction+valuation og villa hér má ekki eyðileggja það sem tókst
    # (sama abort-not-retry-hugsun og keðjan sjálf byggir á).
    if args.bridge or args.bridge_only:
        try:
            E.bridge_attributes(rw, log=print)
        except Exception as e:                                    # noqa: BLE001
            rw.rollback()
            print(f"BRIDGE FAILED (non-fatal): {type(e).__name__}: {e}")
    else:
        print("bridge: SLEPPT (opt-in — bættu við --bridge eða --bridge-only).")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # cc112: stderr LÍKA. Keðjan fangar `> "$xlog" 2>&1`, svo útgáfuhliðið fellur ofan í
    # sama loggið gegnum stderr-rakninguna. Án þessarar línu kom íslenski villutextinn
    # þangað sem cp1252-hakk („SKRIF ST??VU?") — hávær villa sem enginn les er ekki hávær.
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
