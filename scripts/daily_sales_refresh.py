"""daily_sales_refresh.py — daily fresh-data path for public.sales_history.

Cadence-separated from the monthly model pipeline (run_monthly.py). This script
appends genuinely-new (faerslunumer, fastnum) sales rows, CARRIES HMS CORRECTIONS
onto rows that already exist, and refreshes the 13 semantic materialized views.
It never touches predictions / feature_attributions / any model output, and it
never deletes rows.

CC179 — UPDATE-ARMURINN (var: NEW-KEYS-ONLY, sjá GAGNAVIDGERD_CC178.md §3.2):
  Fram að cc179 var röð sem þegar var inni ALDREI endurleidd. HMS endurbirtir og
  leiðréttir kaupskrána í stað — verð, ónothæfi og stærðir breytast eftir á — og
  engin þeirra leiðréttinga barst. Mælt 2026-09-01 (D:\\_audit\\cc179_verd\\q02):
  137 raðir af 229.998 (0,060 %) viku frá ferskri kaupskrá; ein þeirra var
  725.000.000 kr sem HMS skráir sem 72.500.000 og sem LIFANDI eignasíða birti.
  Nú ber skriftan bæði arma: INSERT á nýja lykla OG UPDATE á reiti sem víkja.

  kaupverd_real er VARIN AKKERISHLIÐI (real_anchor_parity_gate). Sá dálkur er
  eign monthly_cpi_reanchor.py; ef geymda taflan situr á öðru CPI-akkeri en
  pipeline_config segir myndi blint UPDATE endurakkera hana í hljóði. Hliðið
  MÆLIR það á rööum þar sem nominal er ÓBREYTT og fellir dálkinn úr
  UPDATE-menginu ef mælingin fellur (hávær log-lína, restin gengur samt).

  Hver reitur sem skrifast fer í public.sales_history_corrections
  (cc179_corrections_schema.sql) með gömlu/nýju gildi og útgáfu kaupskrárinnar.

Reuses the derive core from rebuild_sales_history.py by import (no re-implementation)
and the single-source CPI anchor from anchor_config.read_anchor (public.pipeline_config).

Flow:
  0. run D:\\refresh_kaupskra.py; log content_md5 change as diagnostic (no gate).
  1. read pinned anchor + CPI lookup + properties universe (read-only).
  2. re-derive the full rowset from kaupskra.csv (identical transforms).
  3. diff vs live on (faerslunumer, fastnum): NEW + GONE (GONE watched, not deleted)
     + DRIFT (reitir sem víkja á sameiginlegum lyklum) + akkerishlið.
  4. --dryrun: report + examples, no writes.
  5. upsert: INSERT ... ON CONFLICT DO NOTHING á nýja lykla, svo UPDATE ... FROM
     (VALUES) á drift-raðirnar — BÁÐIR í SÖMU txn með rowcount == spá hliði.
  6. REFRESH MV CONCURRENTLY iff inserted + updated > 0 — aðeins MV sem lesa breytta
     töflu (MV_SOURCES vörpunin; sales_history-only umferð sleppir
     v_sveitarfelag_lookup), með SET work_mem='64MB' session-vís (sjá
     DECISIONS 2026-07-14, Disk-IO mótvægi).

CLI:
  python scripts/daily_sales_refresh.py            # live: fetch -> upsert -> refresh
  python scripts/daily_sales_refresh.py --dryrun   # no writes; report what would happen
  python scripts/daily_sales_refresh.py --no-update  # cc179-armurinn af (gamla hegðunin)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from rebuild_sales_history import (  # noqa: E402  reuse derive core, no re-implementation
    load_cpi_lookup,
    derive_sales_rows,
    fetch_valid_fastnums,
    fetch_hms_einflm,
    open_ro_conn,
    CPI_CSV,
    KAUPSKRA_CSV,
    REFRESH_KAUPSKRA,
    DBCONFIG,
)
from anchor_config import read_anchor  # noqa: E402
from suspect_rules import RULESET_VERSION as SUSPECT_RULESET_VERSION  # noqa: E402
from migration_helpers import (  # noqa: E402  shared Group C audit logging
    start_run, start_step, finish_step, finish_run, open_connection,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(
    sys.stdout, "reconfigure") else None

STATE_JSON = Path(r"D:\kaupskra_fetch_state.json")
LOGFILE = Path(r"D:\daily_sales_refresh.log")

# 13 semantic materialized views (probe SKREF 6). _sales_base is a plain VIEW -> NOT here.
MV_LIST = [
    "semantic.v_street_directory",
    "semantic.v_matsvaedi_prices_yearly",
    "semantic.v_street_prices",
    "semantic.v_postnr_prices_yearly",
    "semantic.v_street_activity",
    "semantic.v_sveitarfelag_market",
    "semantic.v_matsvaedi_trend_quarterly",
    "semantic.v_hood_heat",
    "semantic.v_newbuild_share",
    "semantic.v_model_vs_sold_by_hood",
    "semantic.v_summerhouse_market",
    "semantic.v_price_distribution_by_hood",
    "semantic.v_sveitarfelag_lookup",
]

# MV -> grunntöflur sem MV-ið les (staðfest gegn pg_depend 2026-07-14, sjá
# D:\DISK_IO_GREINING_20260714T2131Z.md og DECISIONS 2026-07-14). REFRESH CONCURRENTLY
# á ÓBREYTTU MV les samt heimildir + allt MV-ið (~300 MB+ IO per MV á Micro) — því
# refreshum við aðeins MV sem lesa töflu sem breyttist í umferðinni. Nýtt semantic-MV
# VERÐUR að fá færslu hér; mvs_touching() hendir KeyError annars (hávær, ekki hljóðlát).
MV_SOURCES = {
    "semantic.v_street_directory":           {"public.properties", "public.sales_history"},
    "semantic.v_matsvaedi_prices_yearly":    {"public.sales_history"},
    "semantic.v_street_prices":              {"public.sales_history"},
    "semantic.v_postnr_prices_yearly":       {"public.sales_history"},
    "semantic.v_street_activity":            {"public.sales_history"},
    "semantic.v_sveitarfelag_market":        {"public.sales_history"},
    "semantic.v_matsvaedi_trend_quarterly":  {"public.sales_history"},
    "semantic.v_hood_heat":                  {"public.sales_history"},
    "semantic.v_newbuild_share":             {"public.sales_history"},
    "semantic.v_model_vs_sold_by_hood":      {"public.sales_history", "public.predictions",
                                              "public.cpi_index", "public.pipeline_config"},
    "semantic.v_summerhouse_market":         {"public.sales_history"},
    "semantic.v_price_distribution_by_hood": {"public.sales_history"},
    "semantic.v_sveitarfelag_lookup":        {"public.properties"},
}


def mvs_touching(changed_tables: set[str]) -> list[str]:
    """MV úr MV_LIST (röð varðveitt) sem lesa a.m.k. eina breytta töflu."""
    return [mv for mv in MV_LIST if MV_SOURCES[mv] & changed_tables]

# INSERT column order (id is auto-generated via nextval -> skipped).
INSERT_COLS = [
    "faerslunumer", "fastnum", "thinglystdags", "kaupverd_nominal",
    "kaupverd_real", "einflm_at_sale", "byggar_at_sale", "onothaefur",
    "is_suspect_comparable", "suspect_reason", "suspect_ruleset_version",
]

GONE_WARN_THRESHOLD = 50

# ---------------------------------------------------------------- cc179 UPDATE-armur
# Reitir sem UPDATE-armurinn MÁ skrifa. Lykillinn sjálfur (faerslunumer, fastnum) er
# ekki hér — hann er samsvörunin, ekki farmurinn. `id` er aldrei snert.
# ATH: kaupverd_real er hér EN fer aðeins með ef akkerishliðið hleypir honum í gegn.
UPDATE_COLS = [
    "thinglystdags", "kaupverd_nominal", "kaupverd_real",
    "einflm_at_sale", "byggar_at_sale", "onothaefur",
    "is_suspect_comparable", "suspect_reason", "suspect_ruleset_version",
]

# SQL-týpa hvers dálks — VALUES-listinn kemur inn sem `unknown` og verður að
# steypast beint, bæði í SET og í samsvöruninni (pooler, engin týpuályktun).
UPDATE_COL_TYPES = {
    "faerslunumer": "bigint", "fastnum": "bigint",
    "thinglystdags": "date", "kaupverd_nominal": "bigint",
    "kaupverd_real": "bigint", "einflm_at_sale": "numeric",
    "byggar_at_sale": "numeric", "onothaefur": "smallint",
    "is_suspect_comparable": "boolean", "suspect_reason": "text",
    "suspect_ruleset_version": "text",
}

# Akkerishlið: kaupverd_real = kaupverd_nominal * cpi[anchor]/cpi[ym]. Ef geymda
# taflan situr á ÖÐRU akkeri en pipeline_config segir víkur ÖLL taflan á þeim dálki,
# ekki stakar raðir. Mælt á rööum þar sem nominal er ÓBREYTT: fleiri en þetta hlutfall
# => taflan er ekki á akkerinu og dálkurinn fellur úr UPDATE-menginu (monthly_cpi_
# reanchor.py á hann). Þröskuldurinn er MÆLDUR: cc179 q02 mældi 0 af 229.997.
REAL_ANCHOR_PARITY_MAX_FRAC = 0.001   # 0,1 % af sameiginlegum rööum
REAL_ANCHOR_PARITY_MAX_ABS = 50       # ...og aldrei fleiri en 50 raðir

# Hávær vörn gegn því að ein misheppnuð kaupskrárútgáfa endurskrifi töfluna.
UPDATE_ABORT_THRESHOLD = 5000         # > þetta => engin skrif, run merkt failed

# Síðustærð UPDATE-arms. execute_values sendir eina stæðu á síðu og cur.rowcount
# ber AÐEINS síðustu síðuna — því er hlutað hér og rowcount lagt saman (sjá
# apply_updates). Stærðin er skrifleiðin, ekki hliðið: hún má hreyfast frjálst.
UPDATE_PAGE_SIZE = 500


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # logging must never crash the run


def read_md5() -> str | None:
    if not STATE_JSON.exists():
        return None
    try:
        return json.loads(STATE_JSON.read_text(encoding="utf-8")).get("content_md5")
    except Exception:
        return None


def read_last_modified() -> str | None:
    """Last-Modified haus kaupskrárinnar — ÚTGÁFAN sem leiðréttingin kom úr (cc179)."""
    if not STATE_JSON.exists():
        return None
    try:
        return json.loads(STATE_JSON.read_text(encoding="utf-8")).get("last_modified")
    except Exception:
        return None


def na_to_none(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    if v is pd.NA:
        return None
    return v


def keyset(df: pd.DataFrame) -> set[tuple[int, int]]:
    """Set of (faerslunumer, fastnum) over rows with non-null faerslunumer."""
    sub = df[df["faerslunumer"].notna()]
    return set(zip(sub["faerslunumer"].astype("int64"),
                   sub["fastnum"].astype("int64")))


# ======================================================================
# cc179 — drift-greining (EIN LIND: cc179-sópunin flytur þetta inn, endurútfærir ekki)
# ======================================================================
def normalize_for_compare(df: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    """Varpa (faerslunumer, fastnum) + UPDATE_COLS á samanburðarhæfar týpur.

    Sama vörpun er lögð á BÁÐAR hliðar — geymdu röðina úr DB og leiddu röðina úr
    kaupskrá — svo mismunur geti aldrei stafað af týpumun (Decimal vs float,
    date vs Timestamp, None vs NaN). Sbr. feedback_hlid_sem_les_badar_hlidar_ur_
    somu_heimild_er_daudt: hliðið les tvær ÓHÁÐAR heimildir, aðeins vörpunin er sameiginleg.
    """
    from decimal import Decimal

    o = pd.DataFrame(index=df.index)
    o["faerslunumer"] = pd.to_numeric(df["faerslunumer"], errors="coerce").astype("Int64")
    o["fastnum"] = pd.to_numeric(df["fastnum"], errors="coerce").astype("Int64")
    o[prefix + "thinglystdags"] = pd.to_datetime(
        df["thinglystdags"], errors="coerce").dt.strftime("%Y-%m-%d")
    for c in ("kaupverd_nominal", "kaupverd_real"):
        o[prefix + c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    for c in ("einflm_at_sale", "byggar_at_sale"):
        o[prefix + c] = pd.to_numeric(
            df[c].map(lambda v: float(v) if isinstance(v, Decimal) else v),
            errors="coerce").astype("float64")
    o[prefix + "onothaefur"] = pd.to_numeric(df["onothaefur"], errors="coerce").astype("float64")
    o[prefix + "is_suspect_comparable"] = df["is_suspect_comparable"].map(
        lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else bool(v))
    for c in ("suspect_reason", "suspect_ruleset_version"):
        o[prefix + c] = df[c].where(df[c].notna(), None)
    return o


def _neq(a: pd.Series, b: pd.Series) -> pd.Series:
    """Ójafnt, NULL-öruggt: NULL vs NULL er JAFNT, NULL vs gildi er ÓJAFNT."""
    an, bn = a.isna(), b.isna()
    out = pd.Series(False, index=a.index)
    ok = ~(an | bn)
    out.loc[ok] = (a[ok] != b[ok])
    out.loc[an ^ bn] = True
    return out


def compute_drift(live: pd.DataFrame, derived: pd.DataFrame,
                  update_cols: list[str]) -> tuple[pd.DataFrame, dict[str, int], int]:
    """Raðir sem eru í BÁÐUM en víkja á a.m.k. einum reit úr update_cols.

    Skilar (merged-frame afmarkað við drift-raðir, {dálkur: teljari}, nefnari).
    Frame-ið ber L_* (geymt) og D_* (leitt) fyrir alla UPDATE_COLS — báðar hliðar
    berast áfram svo breytingaskráin geti bókað gamla OG nýja gildið.
    """
    L = normalize_for_compare(live, "L_")
    D = normalize_for_compare(derived, "D_")
    m = L.merge(D, on=["faerslunumer", "fastnum"], how="inner")
    counts: dict[str, int] = {}
    flags = []
    for c in UPDATE_COLS:                      # teljarar á ÖLLUM reitum, líka þeim
        d = _neq(m["L_" + c], m["D_" + c])     # sem hliðið fellir úr skrifmenginu
        m["x_" + c] = d
        counts[c] = int(d.sum())
        if c in update_cols:
            flags.append("x_" + c)
    m["x_any"] = m[flags].any(axis=1) if flags else False
    return m[m["x_any"]].copy(), counts, len(m)


def real_anchor_parity_gate(m: pd.DataFrame) -> tuple[bool, int, int]:
    """Situr geymda taflan á sama CPI-akkeri og pipeline_config segir?

    Mælt á rööum þar sem kaupverd_nominal er ÓBREYTT: þar er kaupverd_real hrein
    fylgnistærð af akkerinu einu. Ef þær víkja í massavís er taflan á öðru akkeri
    og daglega leiðin má EKKI skrifa dálkinn (monthly_cpi_reanchor.py á hann) —
    annars endurakkerar hún töfluna í hljóði, sem hausinn bannar.

    Skilar (hlið_opið, misræmi, nefnari).
    """
    same_nominal = ~_neq(m["L_kaupverd_nominal"], m["D_kaupverd_nominal"])
    sub = m[same_nominal]
    n = len(sub)
    bad = int(_neq(sub["L_kaupverd_real"], sub["D_kaupverd_real"]).sum())
    ok = (bad <= REAL_ANCHOR_PARITY_MAX_ABS
          and (n == 0 or bad / n <= REAL_ANCHOR_PARITY_MAX_FRAC))
    return ok, bad, n


def apply_updates(cur, drift: pd.DataFrame, cols: list[str], *,
                  source: str, run_id: int | None, kaupskra_md5: str | None,
                  kaupskra_last_modified: str | None, anchor_ym: str | None,
                  ruleset_version: str | None) -> tuple[int, int]:
    """UPDATE drift-raðirnar + skrifa breytingaskrá — INNAN kallarans txn.

    Kallandinn á txn-ið (og þar með rollbackið). Hendir RuntimeError ef rowcount
    víkur frá spánni, svo kallandinn rúlli til baka: sbr.
    feedback_bokun_um_vidgerd_er_ekki_vidgerd — rowcount == spá er hliðið, ekki
    færslan um að UPDATE hafi verið keyrt.

    Skilar (uppfærðar raðir, línur í breytingaskrá).
    """
    from psycopg2.extras import execute_values

    if drift.empty or not cols:
        return 0, 0

    key = ["faerslunumer", "fastnum"]
    vcols = key + cols

    def py(v, col):
        """Native python + STEYPT í markdálkstýpuna.

        normalize_for_compare varpar heiltöludálkum í float64 (svo NaN sé til). Að
        senda 72500000.0 inn í ::bigint reiðir sig á óbeina numeric-umbreytingu
        Postgres — hér er hún gerð BEIN, svo hvorki námundun né vísindaritháttur
        komist að heiltöluverði. Sbr. feedback_heiltoludeiling_i_maelifyrirspurn_thegir.
        """
        if v is None or v is pd.NA or (isinstance(v, float) and pd.isna(v)):
            return None
        v = v.item() if hasattr(v, "item") else v
        t = UPDATE_COL_TYPES[col]
        if t in ("bigint", "smallint", "integer"):
            return int(round(float(v)))
        if t == "boolean":
            return bool(v)
        if t == "text":
            return str(v)
        return v          # date / numeric fara óbreytt (str 'YYYY-MM-DD' / float)

    rows = [tuple(py(r["D_" + c] if c in cols else r[c], c) for c in vcols)
            for _, r in drift.iterrows()]

    set_sql = ", ".join(f"{c} = v.{c}::{UPDATE_COL_TYPES[c]}" for c in cols)
    sql = (f"UPDATE public.sales_history s SET {set_sql} "
           f"FROM (VALUES %s) AS v({', '.join(vcols)}) "
           f"WHERE s.faerslunumer = v.faerslunumer::bigint "
           f"  AND s.fastnum      = v.fastnum::bigint")

    # execute_values sendir MARGAR stæður (page_size, sjálfgefið 100) — cur.rowcount
    # ber þá aðeins SÍÐUSTU síðuna. Því er hlutað sjálft og rowcount LAGT SAMAN;
    # annars mælir hliðið síðustu síðuna og hleypir hinum í gegn ómældum.
    # (Fannst í æfingunni q05: rowcount 37 gegn spá 137.)
    n_updated = 0
    for i in range(0, len(rows), UPDATE_PAGE_SIZE):
        chunk = rows[i:i + UPDATE_PAGE_SIZE]
        execute_values(cur, sql, chunk, page_size=len(chunk))
        n_updated += cur.rowcount
    if n_updated != len(rows):
        raise RuntimeError(
            f"UPDATE rowcount {n_updated} != spá {len(rows)} — rúlla til baka")

    # ---- breytingaskrá: EIN LÍNA Á REIT sem raunverulega breyttist ----
    log_rows = []
    for _, r in drift.iterrows():
        for c in cols:
            if not r["x_" + c]:
                continue
            ov, nv = r["L_" + c], r["D_" + c]
            log_rows.append((
                run_id, source, int(r["faerslunumer"]), int(r["fastnum"]), c,
                None if pd.isna(ov) or ov is None else str(ov),
                None if pd.isna(nv) or nv is None else str(nv),
                kaupskra_md5, kaupskra_last_modified, ruleset_version, anchor_ym,
            ))
    if log_rows:
        execute_values(
            cur,
            "INSERT INTO public.sales_history_corrections "
            "(run_id, source, faerslunumer, fastnum, column_name, old_value, "
            " new_value, kaupskra_md5, kaupskra_last_modified, "
            " suspect_ruleset_version, anchor_ym) VALUES %s",
            log_rows,
        )
    return n_updated, len(log_rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun", action="store_true", help="no writes; report only")
    ap.add_argument("--no-update", action="store_true",
                    help="cc179-armurinn af — aðeins NEW-KEYS (gamla hegðunin)")
    args = ap.parse_args()

    log(f"=== daily_sales_refresh ({'DRYRUN' if args.dryrun else 'LIVE'}) ===")

    # Dedicated audit-log connection — independent of conn_ro / conn_w / conn_r so its
    # per-writer commits never touch the data transactions (mirrors run_monthly).
    conn_log = open_connection()
    run_id = start_run(conn_log, "daily_sales_refresh")
    log(f"  pipeline_runs.id = {run_id}")
    conn_ro = None
    try:
        # ---- Step 0: refresh_kaupskra + md5 gate ----
        sid = start_step(conn_log, run_id, "fetch", 1)
        md5_before = read_md5()
        log("[0] running refresh_kaupskra.py ...")
        res = subprocess.run([sys.executable, str(REFRESH_KAUPSKRA)],
                             capture_output=True, text=True, timeout=900)
        if res.returncode != 0:
            log(f"[0] ERROR refresh_kaupskra exit={res.returncode}; "
                f"stderr tail: {(res.stderr or '')[-500:]}")
            finish_step(conn_log, sid, res.returncode, notes="refresh_kaupskra failed")
            finish_run(conn_log, run_id, "failed",
                       {"step": "fetch", "exit_code": res.returncode, "dryrun": args.dryrun})
            return 1
        md5_after = read_md5()
        # md5 is logged as a DIAGNOSTIC only — it does NOT gate. kaupskra can mutate
        # in place (reclassification) without a row-count change, and a same-md5 day
        # is a cheap no-op downstream (derive+diff yields NEW=0). Always proceed.
        changed = "changed" if md5_before != md5_after else "unchanged"
        log(f"[0] kaupskra md5 {changed} today (before={md5_before} after={md5_after})")
        finish_step(conn_log, sid, 0, notes=f"md5 {changed}")

        # ---- Step 1+2: anchor + cpi + universe + re-derive ----
        sid = start_step(conn_log, run_id, "derive_diff", 2)
        conn_ro = open_ro_conn()
        anchor_ym = read_anchor(conn_ro)  # raises if missing — free HALT guard
        cpi = load_cpi_lookup(CPI_CSV, anchor_ym)
        log(f"[1] anchor={anchor_ym} (pipeline_config); cpi months={len(cpi)}")
        valid_fastnums = fetch_valid_fastnums(conn_ro)
        log(f"[1] properties universe={len(valid_fastnums):,}")
        hms_einflm = fetch_hms_einflm(conn_ro)  # R3 input for is_suspect_comparable

        kp = pd.read_csv(KAUPSKRA_CSV, sep=";", encoding="latin-1", low_memory=False)
        log(f"[2] kaupskra raw rows={len(kp):,}")
        derived, stats = derive_sales_rows(kp, valid_fastnums, cpi, hms_einflm)
        log(f"[2] derive stats: fk_dropped={stats['fk_dropped_rows']:,} "
            f"({stats['fk_dropped_distinct_fastnums']:,} distinct), "
            f"rows_in_universe={stats['rows_in_universe']:,}, "
            f"dropped_zero_nominal={stats['dropped_zero_nominal']:,}, "
            f"final_rows={stats['final_rows']:,}")
        if stats["rows_without_cpi"] > 0:
            log(f"[2] WARN: {stats['rows_without_cpi']:,} rows without cpi_factor "
                f"(kaupverd_real NULL for those)")
        if stats.get("x1000_overrides"):
            log(f"[2] ×1000-OVERRIDE (cc39): {stats['x1000_overrides']} raðir leiðréttar ÷1000 "
                f"(f={[e['faerslunumer'] for e in stats['x1000_entries']]}; "
                f"audit: D:\\x1000_override_audit.jsonl)")

        # ---- Step 3: diff vs live ----
        with conn_ro.cursor() as cur:
            cur.execute(
                "SELECT faerslunumer, fastnum, thinglystdags, kaupverd_nominal, "
                "       kaupverd_real, einflm_at_sale, byggar_at_sale, onothaefur, "
                "       is_suspect_comparable, suspect_reason, suspect_ruleset_version "
                "FROM public.sales_history")
            live_df = pd.DataFrame(cur.fetchall(), columns=[
                "faerslunumer", "fastnum", "thinglystdags", "kaupverd_nominal",
                "kaupverd_real", "einflm_at_sale", "byggar_at_sale", "onothaefur",
                "is_suspect_comparable", "suspect_reason", "suspect_ruleset_version"])
        live_df = live_df[live_df["faerslunumer"].notna()]
        live_keys = {(int(f), int(fn)) for f, fn in
                     zip(live_df["faerslunumer"], live_df["fastnum"])}
        derived_keys = keyset(derived)
        new_keys = derived_keys - live_keys
        gone_keys = live_keys - derived_keys
        log(f"[3] NEW={len(new_keys):,}  GONE={len(gone_keys):,}  "
            f"(live={len(live_keys):,}, derived={len(derived_keys):,})")
        if len(gone_keys) > GONE_WARN_THRESHOLD:
            log(f"[3] WARN: GONE={len(gone_keys):,} exceeds {GONE_WARN_THRESHOLD} — "
                f"rows vanished from kaupskra; no delete in v1, review needed.")

        # ---- Step 3b (cc179): DRIFT á sameiginlegum lyklum + akkerishlið ----
        update_cols = [] if args.no_update else list(UPDATE_COLS)
        real_gate_ok, real_bad, real_n = True, 0, 0
        drift = pd.DataFrame()
        drift_counts: dict[str, int] = {}
        if update_cols:
            _all, drift_counts, denom = compute_drift(live_df, derived, UPDATE_COLS)
            real_gate_ok, real_bad, real_n = real_anchor_parity_gate(
                normalize_for_compare(live_df, "L_").merge(
                    normalize_for_compare(derived, "D_"),
                    on=["faerslunumer", "fastnum"], how="inner"))
            if not real_gate_ok:
                update_cols = [c for c in update_cols if c != "kaupverd_real"]
                log(f"[3b] !! AKKERISHLIÐ FALLIÐ: kaupverd_real víkur á {real_bad:,} af "
                    f"{real_n:,} rööum þar sem nominal er ÓBREYTT "
                    f"(þak {REAL_ANCHOR_PARITY_MAX_ABS} / "
                    f"{REAL_ANCHOR_PARITY_MAX_FRAC:.1%}). Taflan situr á ÖÐRU CPI-akkeri "
                    f"en pipeline_config['{anchor_ym}'] — kaupverd_real FELLDUR úr "
                    f"UPDATE-menginu (monthly_cpi_reanchor.py á hann).")
            else:
                log(f"[3b] akkerishlið OPIÐ: kaupverd_real víkur á {real_bad:,} af "
                    f"{real_n:,} óbreyttum-nominal rööum — taflan er á akkeri {anchor_ym}.")
            # drift-mengið endurreiknað með VIRKA dálkamenginu (hliðið gæti hafa fellt einn)
            drift, drift_counts, denom = compute_drift(live_df, derived, update_cols)
            log(f"[3b] DRIFT={len(drift):,} raðir af {denom:,} sameiginlegum "
                f"({100.0 * len(drift) / max(denom, 1):.4f} %)")
            for c in UPDATE_COLS:
                if drift_counts.get(c):
                    mark = "" if c in update_cols else "   [FELLDUR AF HLIÐI]"
                    log(f"[3b]    {c:<24} {drift_counts[c]:>7,}{mark}")
        else:
            log("[3b] --no-update: UPDATE-armurinn af (NEW-KEYS-ONLY, hegðun fyrir cc179)")

        finish_step(conn_log, sid, 0, rowcount_after=stats["final_rows"],
                    notes=f"NEW={len(new_keys)} GONE={len(gone_keys)} "
                          f"DRIFT={len(drift)} real_gate={'ok' if real_gate_ok else 'FALLIÐ'} "
                          f"md5 {changed}")

        # rows to insert (new keys only); informational MAX thinglystdags among them
        dk = derived[derived["faerslunumer"].notna()].copy()
        dk["_k"] = list(zip(dk["faerslunumer"].astype("int64"),
                            dk["fastnum"].astype("int64")))
        to_insert = dk[dk["_k"].isin(new_keys)].drop(columns="_k")
        if len(to_insert):
            max_new = pd.to_datetime(to_insert["thinglystdags"]).max()
            log(f"[3] MAX(thinglystdags) among NEW={max_new.date()} "
                f"(info only — late-registered sales carry old dates)")

        # ---- Hávær vörn: ein misheppnuð kaupskrárútgáfa má ekki endurskrifa töfluna ----
        if len(drift) > UPDATE_ABORT_THRESHOLD:
            log(f"*** ABORT: DRIFT={len(drift):,} fer yfir þakið "
                f"{UPDATE_ABORT_THRESHOLD:,} — engin skrif. Skoðaðu kaupskrárútgáfuna "
                f"(md5={md5_after}) áður en þetta er keyrt aftur.")
            finish_run(conn_log, run_id, "failed",
                       {"step": "drift_guard", "drift": len(drift),
                        "threshold": UPDATE_ABORT_THRESHOLD, "md5": md5_after})
            return 1

        # ---- Step 4: dryrun ----
        if args.dryrun:
            log(f"[4] DRYRUN — engin skrif. Myndi setja inn {len(new_keys):,} raðir "
                f"og uppfæra {len(drift):,} raðir á dálkunum {update_cols}.")
            for _, r in to_insert.head(10).iterrows():
                log(f"      NEW faerslunumer={int(r['faerslunumer'])} fastnum={int(r['fastnum'])} "
                    f"{r['thinglystdags']} nominal={r['kaupverd_nominal']} "
                    f"onothaefur={r['onothaefur']}")
            n_fields = 0
            for _, r in drift.iterrows():
                breytt = [c for c in update_cols if r["x_" + c]]
                n_fields += len(breytt)
            for _, r in drift.head(10).iterrows():
                breytt = [c for c in update_cols if r["x_" + c]]
                lysing = ", ".join(f"{c}: {r['L_' + c]!r} -> {r['D_' + c]!r}" for c in breytt)
                log(f"      UPD faerslunumer={int(r['faerslunumer'])} "
                    f"fastnum={int(r['fastnum'])} | {lysing}")
            log(f"[4] DRYRUN complete — no upsert, no update, no REFRESH. "
                f"({n_fields:,} reitir myndu fara í breytingaskrá)")
            finish_run(conn_log, run_id, "success",
                       {"dryrun": True, "noop": len(new_keys) == 0 and len(drift) == 0,
                        "new": len(new_keys), "gone": len(gone_keys),
                        "drift": len(drift), "drift_fields": n_fields,
                        "update_cols": update_cols, "real_gate_ok": real_gate_ok})
            return 0

        # ---- No-op: nothing new AND nothing drifted (recorded, not dropped) ----
        if len(to_insert) == 0 and len(drift) == 0:
            log("[5] 0 new rows, 0 drifted rows — nothing to write.")
            log("[6] 0 written — sleppi REFRESH.")
            finish_run(conn_log, run_id, "success",
                       {"noop": True, "reason": "no new rows, no drift",
                        "inserted": 0, "updated": 0, "gone": len(gone_keys)})
            return 0

        # ---- Step 5: live write — INSERT (nýir lyklar) + UPDATE (drift), EIN txn ----
        import psycopg2
        from psycopg2.extras import execute_values
        sid = start_step(conn_log, run_id, "upsert", 3)
        inserted = 0
        updated = 0
        logged_fields = 0
        rows = [tuple(na_to_none(r[c]) for c in INSERT_COLS)
                for _, r in to_insert.iterrows()]

        # coerce numpy/pandas scalars to native python for psycopg2
        def py(v):
            if v is None:
                return None
            if hasattr(v, "item"):
                return v.item()
            return v
        rows = [tuple(py(x) for x in row) for row in rows]
        url = DBCONFIG.read_text(encoding="utf-8-sig").strip()
        conn_w = psycopg2.connect(url)
        conn_w.autocommit = False
        try:
            with conn_w.cursor() as cur:
                cur.execute("SET TRANSACTION READ WRITE")  # ALLRA-FYRSTA á ferskri tengingu
                if rows:
                    execute_values(
                        cur,
                        f"INSERT INTO public.sales_history "
                        f"({', '.join(INSERT_COLS)}) VALUES %s "
                        f"ON CONFLICT (faerslunumer, fastnum) DO NOTHING",
                        rows,
                    )
                    inserted = cur.rowcount
                # cc179: leiðréttingararmurinn — SAMA txn, svo INSERT og UPDATE
                # standa eða falla saman og breytingaskráin getur ekki orðið munaðarlaus.
                updated, logged_fields = apply_updates(
                    cur, drift, update_cols,
                    source="daily_sales_refresh", run_id=run_id,
                    kaupskra_md5=md5_after,
                    kaupskra_last_modified=read_last_modified(),
                    anchor_ym=anchor_ym, ruleset_version=SUSPECT_RULESET_VERSION)
            conn_w.commit()
            log(f"[5] inserted={inserted:,} (of {len(new_keys):,} new keys)  "
                f"updated={updated:,} (of {len(drift):,} drifted)  "
                f"breytingaskrá={logged_fields:,} reitir")
            if inserted != len(new_keys):
                log(f"[5] WARN: inserted {inserted:,} != new_keys {len(new_keys):,} "
                    f"(ON CONFLICT skipped some — unexpected for genuinely-new keys)")
        except Exception as e:
            conn_w.rollback()
            log(f"[5] ERROR write rolled back: {type(e).__name__}: {e}")
            conn_w.close()
            finish_step(conn_log, sid, 1, rowcount_before=len(live_keys),
                        notes=f"write rolled back: {type(e).__name__}")
            finish_run(conn_log, run_id, "failed",
                       {"step": "upsert", "error": str(e)[:500]})
            return 1
        conn_w.close()
        finish_step(conn_log, sid, 0, rowcount_before=len(live_keys),
                    rowcount_after=len(live_keys) + inserted,
                    notes=f"inserted={inserted} updated={updated} fields={logged_fields}")

        # ---- Step 6: REFRESH MV (iff inserted + updated > 0) ----
        # cc179: UPDATE breytir sömu heimild og INSERT (kaupverd/onothaefur eru í
        # aggregötum MV-anna), svo hann VERÐUR að hleypa refreshinu af líka.
        sid = start_step(conn_log, run_id, "refresh_mv", 4)
        if inserted + updated > 0:
            # Daglega umferðin skrifar AÐEINS í sales_history -> MV sem lesa hana eingöngu.
            to_refresh = mvs_touching({"public.sales_history"})
            skipped = [mv for mv in MV_LIST if mv not in to_refresh]
            conn_r = psycopg2.connect(url)
            conn_r.autocommit = True  # REFRESH ... CONCURRENTLY must be outside a txn block
            with conn_r.cursor() as cur:
                # READ WRITE er ÁFRAM allra-fyrsta statement (pooler-default er read-only);
                # work_mem kemur á eftir — session-vís, ALDREI globalt (60 conn x 64MB > RAM).
                # Án hennar spillir 13-MV umferð ~1,3 GiB í temp (work_mem 2,2MB á Micro).
                cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE")
                cur.execute("SET work_mem = '64MB'")
                for mv in to_refresh:
                    cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}")
                    log(f"[6] refreshed {mv}")
            conn_r.close()
            if skipped:
                log(f"[6] sleppt (heimildir óbreyttar): {', '.join(skipped)}")
            finish_step(conn_log, sid, 0,
                        notes=f"{len(to_refresh)} MV refreshed, {len(skipped)} skipped (sources unchanged)")
        else:
            log("[6] 0 inserted, 0 updated — sleppi REFRESH.")
            finish_step(conn_log, sid, 0, notes="skipped (0 inserted, 0 updated)")

        # ---- Step 7: final log ----
        with conn_ro.cursor() as cur:
            cur.execute("SELECT max(thinglystdags) FROM public.sales_history")
            live_max = cur.fetchone()[0]
        log(f"[7] done. md5={md5_after} anchor={anchor_ym} "
            f"fk_dropped={stats['fk_dropped_rows']:,} final_rows={stats['final_rows']:,} "
            f"inserted={inserted:,} updated={updated:,} GONE={len(gone_keys):,} "
            f"live_max_thinglystdags={live_max}")
        finish_run(conn_log, run_id, "success",
                   {"noop": False, "inserted": inserted, "updated": updated,
                    "corrections_logged": logged_fields, "update_cols": update_cols,
                    "real_gate_ok": real_gate_ok, "gone": len(gone_keys),
                    "data_through": str(live_max)})
        return 0
    except Exception as e:
        log(f"*** CRASH: {type(e).__name__}: {e}")
        finish_run(conn_log, run_id, "crashed", {"error": str(e)[:500]})
        raise
    finally:
        if conn_ro is not None:
            try:
                conn_ro.close()
            except Exception:
                pass
        conn_log.close()


if __name__ == "__main__":
    sys.exit(main())
