"""cc179_apply_corrections.py — EIN leiðréttingarsópun á public.sales_history.

Rót (GAGNAVIDGERD_CC178.md §3.2 + D:\\_audit\\cc179_verd\\q02): daily_sales_refresh.py
var NEW-KEYS-ONLY, svo leiðréttingar HMS á kaupskránni bárust aldrei rööum sem voru
þegar inni. Kóðafixið (UPDATE-armurinn) er komið í daily_sales_refresh.py; þessi skrifta
er EINSKIPTIS-sópunin sem hreinsar uppsafnaða diffið.

EIN LIND: drift-greiningin, akkerishliðið og skrifleiðin eru FLUTT INN úr
daily_sales_refresh (compute_drift / real_anchor_parity_gate / apply_updates).
Ekkert endurútfært hér — annars færu sópunin og næturkeyrslan að reka í sundur
(sbr. feedback_speglud_regla_er_ekki_reglan).

Þrepin, í röð:
  --schema   búa til public.sales_history_corrections (cc179_corrections_schema.sql)
  --freeze   STAGING-AFRIT snertra raða -> public.sales_history_pre_cc179 (+ rollback-SQL)
  --dryrun   mæla drift + akkerishlið, engin skrif   [SJÁLFGEFIÐ]
  --apply    UPDATE í EINNI txn með rowcount == spá hliði + breytingaskrá
  --parity   endurmæla diffið gegn kaupskrá (á að vera 0) + rowcount staging

Rollback: sjá D:\\_audit\\cc179_verd\\cc179_rollback.sql (skrifuð af --freeze).

CLI:
  python scripts/cc179_apply_corrections.py --schema
  python scripts/cc179_apply_corrections.py --freeze
  python scripts/cc179_apply_corrections.py --dryrun
  python scripts/cc179_apply_corrections.py --apply
  python scripts/cc179_apply_corrections.py --parity
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import psycopg2

sys.path.insert(0, str(Path(__file__).parent))
from rebuild_sales_history import (  # noqa: E402
    load_cpi_lookup, derive_sales_rows, fetch_valid_fastnums, fetch_hms_einflm,
    open_ro_conn, CPI_CSV, KAUPSKRA_CSV, DBCONFIG,
)
from anchor_config import read_anchor  # noqa: E402
from suspect_rules import RULESET_VERSION as SUSPECT_RULESET_VERSION  # noqa: E402
from daily_sales_refresh import (  # noqa: E402  EIN LIND — engin endurútfærsla
    UPDATE_COLS, MV_LIST, compute_drift, real_anchor_parity_gate, apply_updates,
    mvs_touching, normalize_for_compare, read_md5, read_last_modified,
)
from migration_helpers import (  # noqa: E402
    start_run, finish_run, open_connection,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(
    sys.stdout, "reconfigure") else None
sys.stderr.reconfigure(encoding="utf-8", errors="replace") if hasattr(
    sys.stderr, "reconfigure") else None

AUDIT = Path(r"D:\_audit\cc179_verd")
STAGING = "public.sales_history_pre_cc179"
SCHEMA_SQL = Path(__file__).parent / "cc179_corrections_schema.sql"
ROLLBACK_SQL = AUDIT / "cc179_rollback.sql"

LIVE_COLS = ["faerslunumer", "fastnum", "thinglystdags", "kaupverd_nominal",
             "kaupverd_real", "einflm_at_sale", "byggar_at_sale", "onothaefur",
             "is_suspect_comparable", "suspect_reason", "suspect_ruleset_version"]


def say(m=""):
    print(m, flush=True)


def open_w():
    """Fersk skrif-tenging. SET TRANSACTION READ WRITE er ALLTAF fyrsta stæðan
    hjá kallandanum (pooler 6543 er read-only sjálfgefið)."""
    c = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    c.autocommit = False
    return c


def fetch_live(conn) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(f"SELECT {', '.join(LIVE_COLS)} FROM public.sales_history")
        df = pd.DataFrame(cur.fetchall(), columns=LIVE_COLS)
    return df[df["faerslunumer"].notna()]


def derive(conn):
    anchor = read_anchor(conn)
    cpi = load_cpi_lookup(CPI_CSV, anchor)
    valid = fetch_valid_fastnums(conn)
    hms = fetch_hms_einflm(conn)
    kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
    d, stats = derive_sales_rows(kp, valid, cpi, hms)
    return d, stats, anchor


def measure(conn):
    """Skilar (drift, update_cols, gate_ok, gate_bad, gate_n, anchor, stats)."""
    live = fetch_live(conn)
    derived, stats, anchor = derive(conn)
    m = normalize_for_compare(live, "L_").merge(
        normalize_for_compare(derived, "D_"), on=["faerslunumer", "fastnum"], how="inner")
    gate_ok, gate_bad, gate_n = real_anchor_parity_gate(m)
    cols = list(UPDATE_COLS) if gate_ok else [c for c in UPDATE_COLS if c != "kaupverd_real"]
    drift, counts, denom = compute_drift(live, derived, cols)
    return drift, counts, denom, cols, gate_ok, gate_bad, gate_n, anchor, stats, live


def report(drift, counts, denom, cols, gate_ok, gate_bad, gate_n, anchor, stats):
    say(f"  anchor(pipeline_config) = {anchor}   ruleset = {SUSPECT_RULESET_VERSION}")
    say(f"  kaupskra md5 = {read_md5()}   last_modified = {read_last_modified()}")
    say(f"  derive: final_rows={stats['final_rows']:,} fk_dropped={stats['fk_dropped_rows']:,} "
        f"x1000_overrides={stats['x1000_overrides']}")
    say("")
    say(f"  AKKERISHLIÐ (kaupverd_real): {'OPIÐ' if gate_ok else 'FALLIÐ'} — "
        f"{gate_bad:,} misræmi af {gate_n:,} rööum með ÓBREYTT nominal")
    if not gate_ok:
        say("    -> kaupverd_real FELLDUR úr skrifmenginu (monthly_cpi_reanchor.py á hann)")
    say(f"  skrifmengi: {cols}")
    say("")
    say(f"  DRIFT = {len(drift):,} raðir af {denom:,} sameiginlegum "
        f"({100.0 * len(drift) / max(denom, 1):.4f} %)")
    say(f"  {'reitur':<26}{'misræmi':>9}{'nefnari':>10}{'%':>10}")
    n_fields = 0
    for c in UPDATE_COLS:
        n = counts.get(c, 0)
        mark = "" if c in cols else "  [FELLDUR]"
        if c in cols:
            n_fields += n
        say(f"    {c:<24}{n:>9,}{denom:>10,}{100.0 * n / max(denom, 1):>9.4f}%{mark}")
    say(f"  -> breytingaskrá myndi fá {n_fields:,} línur (ein á reit)")
    return n_fields


# ----------------------------------------------------------------------
def do_schema():
    say("=== --schema: public.sales_history_corrections ===")
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    c = open_w()
    try:
        with c.cursor() as cur:
            cur.execute("SET TRANSACTION READ WRITE")
            cur.execute(sql)
        c.commit()
        with c.cursor() as cur:
            cur.execute("SET TRANSACTION READ WRITE")
            cur.execute("SELECT count(*) FROM public.sales_history_corrections")
            n = cur.fetchone()[0]
        c.commit()
        say(f"  OK — taflan til, {n:,} línur (0 = ný).")
    except Exception as e:
        c.rollback()
        say(f"  !! VILLA, rúllað til baka: {type(e).__name__}: {e}")
        return 1
    finally:
        c.close()
    return 0


def do_freeze():
    say(f"=== --freeze: staging-afrit snertra raða -> {STAGING} ===")
    ro = open_ro_conn()
    try:
        drift, counts, denom, cols, gate_ok, gate_bad, gate_n, anchor, stats, _ = measure(ro)
    finally:
        ro.close()
    keys = [(int(r["faerslunumer"]), int(r["fastnum"])) for _, r in drift.iterrows()]
    say(f"  snertar raðir: {len(keys):,}")
    if not keys:
        say("  ekkert að frysta — hætti.")
        return 0

    fs = [k[0] for k in keys]
    fn = [k[1] for k in keys]
    c = open_w()
    try:
        with c.cursor() as cur:
            cur.execute("SET TRANSACTION READ WRITE")
            cur.execute(f"DROP TABLE IF EXISTS {STAGING}")
            # Afritið er á RAUNVERULEGU rööunum, sótt með lyklaparinu (ekki
            # faerslunumer einu — 13.692 raðir deila faerslunumeri).
            cur.execute(
                f"CREATE TABLE {STAGING} AS "
                f"SELECT s.* FROM public.sales_history s "
                f"JOIN (SELECT unnest(%s::bigint[]) AS f, unnest(%s::bigint[]) AS fn) k "
                f"  ON s.faerslunumer = k.f AND s.fastnum = k.fn",
                (fs, fn))
            n_frozen = cur.rowcount
            cur.execute(f"COMMENT ON TABLE {STAGING} IS %s",
                        (f"cc179 {datetime.now(timezone.utc).isoformat()}: afrit af "
                         f"{n_frozen} rööum public.sales_history FYRIR leiðréttingarsópun. "
                         f"Rollback-heimild. Má henda eftir staðfesta parity.",))
            cur.execute(f"SELECT count(*) FROM {STAGING}")
            n_check = cur.fetchone()[0]
            if n_check != len(keys):
                raise RuntimeError(f"staging {n_check} != drift {len(keys)}")
        c.commit()
        say(f"  frosið: {n_check:,} raðir í {STAGING}")
    except Exception as e:
        c.rollback()
        say(f"  !! VILLA, rúllað til baka: {type(e).__name__}: {e}")
        return 1
    finally:
        c.close()

    ROLLBACK_SQL.parent.mkdir(parents=True, exist_ok=True)
    ROLLBACK_SQL.write_text(f"""-- cc179_rollback.sql — sjálfvirkt skrifuð af cc179_apply_corrections.py --freeze
-- {datetime.now(timezone.utc).isoformat()}
-- Bakfærir leiðréttingarsópunina á public.sales_history úr {STAGING}
-- ({n_check} raðir). Keyrist í EINNI txn; READ WRITE er fyrsta stæðan (pooler 6543).
--
-- ATH: bakfærir EKKI public.sales_history_corrections — breytingaskráin á að standa
-- sem heimild um að skrifin áttu sér stað (og að þeim var rúllað til baka).

BEGIN;
SET TRANSACTION READ WRITE;

UPDATE public.sales_history s SET
  thinglystdags           = p.thinglystdags,
  kaupverd_nominal        = p.kaupverd_nominal,
  kaupverd_real           = p.kaupverd_real,
  einflm_at_sale          = p.einflm_at_sale,
  byggar_at_sale          = p.byggar_at_sale,
  onothaefur              = p.onothaefur,
  is_suspect_comparable   = p.is_suspect_comparable,
  suspect_reason          = p.suspect_reason,
  suspect_ruleset_version = p.suspect_ruleset_version
FROM {STAGING} p
WHERE s.faerslunumer = p.faerslunumer AND s.fastnum = p.fastnum;
-- VÆNTUR rowcount: {n_check}

COMMIT;
""", encoding="utf-8")
    say(f"  rollback-SQL: {ROLLBACK_SQL}")
    return 0


def do_apply():
    say("=== --apply: leiðréttingarsópun (EIN txn, rowcount == spá) ===")
    ro = open_ro_conn()
    try:
        drift, counts, denom, cols, gate_ok, gate_bad, gate_n, anchor, stats, _ = measure(ro)
    finally:
        ro.close()
    n_fields = report(drift, counts, denom, cols, gate_ok, gate_bad, gate_n, anchor, stats)
    if drift.empty:
        say("  DRIFT = 0 — ekkert að gera.")
        return 0

    # Rollback-heimildin VERÐUR að vera til áður en skrifað er.
    ro = open_ro_conn()
    try:
        with ro.cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", (STAGING,))
            exists = cur.fetchone()[0]
            n_st = 0
            if exists:
                cur.execute(f"SELECT count(*) FROM {STAGING}")
                n_st = cur.fetchone()[0]
    finally:
        ro.close()
    if not exists or n_st != len(drift):
        say(f"  !! STOPP: {STAGING} {'vantar' if not exists else f'ber {n_st} raðir != drift {len(drift)}'}."
            f" Keyrðu --freeze fyrst.")
        return 2
    say(f"  rollback-heimild OK: {STAGING} ber {n_st:,} raðir")

    conn_log = open_connection()
    run_id = start_run(conn_log, "cc179_sweep")
    say(f"  pipeline_runs.id = {run_id}")
    c = open_w()
    try:
        with c.cursor() as cur:
            cur.execute("SET TRANSACTION READ WRITE")
            n_upd, n_log = apply_updates(
                cur, drift, cols, source="cc179_sweep", run_id=run_id,
                kaupskra_md5=read_md5(), kaupskra_last_modified=read_last_modified(),
                anchor_ym=anchor, ruleset_version=SUSPECT_RULESET_VERSION)
        c.commit()
        say(f"  UPDATE rowcount = {n_upd:,}  (spá {len(drift):,})  -> HLIÐ OPIÐ")
        say(f"  breytingaskrá   = {n_log:,} línur (spá {n_fields:,})")

        # ---- REFRESH MV: sópunin breytti sömu heimild og INSERT-armurinn ----
        # Án þessa situr 725-milljóna röðin áfram í v_street_prices o.fl.
        to_refresh = mvs_touching({"public.sales_history"})
        say(f"  REFRESH {len(to_refresh)} MV (sleppi {len(MV_LIST) - len(to_refresh)}) ...")
        cr = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
        cr.autocommit = True   # REFRESH ... CONCURRENTLY má ekki vera í txn-blokk
        try:
            with cr.cursor() as cur:
                cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE")
                cur.execute("SET work_mem = '64MB'")
                for mv in to_refresh:
                    cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}")
                    say(f"    refreshed {mv}")
        finally:
            cr.close()

        finish_run(conn_log, run_id, "success",
                   {"updated": n_upd, "corrections_logged": n_log,
                    "update_cols": cols, "real_gate_ok": gate_ok,
                    "mv_refreshed": len(to_refresh), "kaupskra_md5": read_md5()})
    except Exception as e:
        c.rollback()
        say(f"  !! VILLA, rúllað til baka: {type(e).__name__}: {e}")
        finish_run(conn_log, run_id, "failed", {"error": str(e)[:500]})
        return 1
    finally:
        c.close()
        conn_log.close()
    return 0


def do_parity():
    say("=== --parity: diff gegn kaupskrá EFTIR sópun (á að vera 0) ===")
    ro = open_ro_conn()
    try:
        drift, counts, denom, cols, gate_ok, gate_bad, gate_n, anchor, stats, _ = measure(ro)
        report(drift, counts, denom, cols, gate_ok, gate_bad, gate_n, anchor, stats)
        with ro.cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", (STAGING,))
            if cur.fetchone()[0]:
                cur.execute(f"SELECT count(*) FROM {STAGING}")
                say(f"  {STAGING}: {cur.fetchone()[0]:,} raðir (rollback-heimild)")
            cur.execute("SELECT count(*) n, count(DISTINCT (faerslunumer, fastnum)) k, "
                        "       min(corrected_at) f, max(corrected_at) t "
                        "FROM public.sales_history_corrections")
            r = cur.fetchone()
            say(f"  breytingaskrá: {r[0]:,} línur á {r[1]:,} rööum  ({r[2]} .. {r[3]})")
            cur.execute("SELECT column_name, count(*) FROM public.sales_history_corrections "
                        "GROUP BY 1 ORDER BY 2 DESC")
            for cn, n in cur.fetchall():
                say(f"      {cn:<26}{n:>7,}")
    finally:
        ro.close()
    say("")
    say(f"  NIÐURSTAÐA: diff = {len(drift):,}  ->  "
        f"{'PARITY' if drift.empty else 'EKKI PARITY — skoðaðu reitina að ofan'}")
    return 0 if drift.empty else 1


def do_dryrun():
    say("=== --dryrun: mæling, engin skrif ===")
    ro = open_ro_conn()
    try:
        drift, counts, denom, cols, gate_ok, gate_bad, gate_n, anchor, stats, _ = measure(ro)
    finally:
        ro.close()
    report(drift, counts, denom, cols, gate_ok, gate_bad, gate_n, anchor, stats)
    if not drift.empty:
        say("")
        say("  20 raða sýnishorn (geymt -> leitt):")
        for _, r in drift.head(20).iterrows():
            breytt = [c for c in cols if r["x_" + c]]
            lys = " | ".join(f"{c}: {r['L_' + c]!r} -> {r['D_' + c]!r}" for c in breytt)
            say(f"    f={int(r['faerslunumer'])} fastnum={int(r['fastnum'])}  {lys}")
        out = AUDIT / "cc179_drift.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        drift.to_csv(out, index=False, encoding="utf-8-sig")
        say(f"\n  [csv] {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--dryrun", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--parity", action="store_true")
    a = ap.parse_args()
    if a.schema:
        return do_schema()
    if a.freeze:
        return do_freeze()
    if a.apply:
        return do_apply()
    if a.parity:
        return do_parity()
    return do_dryrun()


if __name__ == "__main__":
    sys.exit(main())
