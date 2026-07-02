"""backfill_suspect_sales_history.py — one-time backfill of is_suspect_comparable on sales_history.

DRYRUN by default (read-only): computes REFINED-B flags for the live rows and prints distribution.
--apply: opens a READ WRITE tx on the pooler (6543), backfills via UPDATE...FROM a TEMP table,
and stamps a pipeline_runs audit row. Columns must already exist (added via migration).

Durable path: suspect_rules.compute_suspect is ALSO wired into derive_sales_rows (rebuild +
daily loader), so future rebuilds regenerate these columns. This script only backfills the
already-present 227,871 rows once.
"""
from __future__ import annotations
import sys, json, socket
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from suspect_rules import compute_suspect, RULESET_VERSION

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
KAUPSKRA = Path(r"D:\kaupskra.csv")
APPLY = "--apply" in sys.argv


def conn(readonly=True):
    import psycopg2
    c = psycopg2.connect(DBCONFIG.read_text(encoding="utf-8-sig").strip())
    c.set_session(readonly=readonly, autocommit=False)
    return c


def main():
    print("=" * 70); print(f"backfill_suspect  mode={'APPLY' if APPLY else 'DRYRUN'}  ruleset={RULESET_VERSION}"); print("=" * 70)
    c = conn(readonly=not APPLY)
    with c.cursor() as cur:
        cur.execute("SELECT fastnum, einflm FROM public.properties WHERE einflm IS NOT NULL")
        hms = {int(f): float(e) for f, e in cur.fetchall()}
        cur.execute("SELECT faerslunumer, fastnum, onothaefur, thinglystdags, einflm_at_sale FROM public.sales_history")
        live = pd.DataFrame(cur.fetchall(), columns=["faerslunumer", "fastnum", "onothaefur", "thinglystdags", "einflm_at_sale"])
    print(f"  properties HMS einflm: {len(hms):,} fastnums | live sales_history rows: {len(live):,}")

    kp = pd.read_csv(KAUPSKRA, sep=";", encoding="latin-1", low_memory=False)
    flags = compute_suspect(kp, hms)
    kp = pd.concat([kp[["FAERSLUNUMER", "FASTNUM"]], flags], axis=1)
    kp["faerslunumer"] = pd.to_numeric(kp["FAERSLUNUMER"], errors="coerce").astype("Int64")
    kp["fastnum"] = pd.to_numeric(kp["FASTNUM"], errors="coerce").astype("Int64")
    # NB: FAERSLUNUMER is NOT unique (repeats across fastnums in multi-unit deeds) — join on BOTH keys.
    live["faerslunumer"] = live["faerslunumer"].astype("Int64")
    live["fastnum"] = live["fastnum"].astype("Int64")
    m = live.merge(kp[["faerslunumer", "fastnum", "is_suspect_comparable", "suspect_reason", "R1", "R2", "R3", "R4"]],
                   on=["faerslunumer", "fastnum"], how="left")
    matched = m["is_suspect_comparable"].notna().sum()
    print(f"  matched live rows by faerslunumer: {matched:,} / {len(m):,}  (unmatched -> {len(m)-matched})")

    # ---- DRYRUN distribution ----
    full = m["is_suspect_comparable"].fillna(False)
    print("\n  DISTRIBUTION on full sales_history:")
    print(f"    suspect = {int(full.sum()):,} ({100*full.mean():.2f}%)  "
          f"[R1={int(m['R1'].sum())} R2={int(m['R2'].sum())} R3={int(m['R3'].sum())} R4={int(m['R4'].sum())}]")
    al = m[m["onothaefur"] == 0]
    print(f"    arms-length subset: {int(al['is_suspect_comparable'].fillna(False).sum()):,} "
          f"({100*al['is_suspect_comparable'].fillna(False).mean():.2f}%)")
    print("    reason breakdown:")
    print(m["suspect_reason"].value_counts(dropna=True).head(8).to_string().replace("\n", "\n      "))
    print("\n  NOTE: comp-eligible CLEAN-pool cost (locked analysis) = 3.36%; SFH-Country >=3 coverage holds 19.7%.")
    print("        Full-table % is higher because it includes comp-INELIGIBLE sales (kv-band / multi-deed failures).")

    if not APPLY:
        c.close(); print("\nDRYRUN done — NO writes. Re-run with --apply after migration adds the columns."); return

    # ---- APPLY: backfill via temp table ----
    up = m[["faerslunumer", "fastnum", "is_suspect_comparable", "suspect_reason"]].dropna(subset=["faerslunumer", "fastnum"]).copy()
    up["is_suspect_comparable"] = up["is_suspect_comparable"].fillna(False).astype(bool)
    up["faerslunumer"] = up["faerslunumer"].astype("int64"); up["fastnum"] = up["fastnum"].astype("int64")
    # NaN reason (non-suspect) -> None so psycopg2 writes SQL NULL, not the string 'NaN'.
    rows = [(f, fn, bool(s), (None if pd.isna(r) else str(r)))
            for f, fn, s, r in up.itertuples(index=False, name=None)]
    from psycopg2.extras import execute_values
    with c.cursor() as cur:
        cur.execute("SET TRANSACTION READ WRITE")
        cur.execute("CREATE TEMP TABLE _sfx (faerslunumer bigint, fastnum bigint, is_suspect boolean, reason text) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO _sfx (faerslunumer, fastnum, is_suspect, reason) VALUES %s", rows, page_size=5000)
        cur.execute(f"""UPDATE public.sales_history s
                        SET is_suspect_comparable = t.is_suspect,
                            suspect_reason = t.reason,
                            suspect_ruleset_version = '{RULESET_VERSION}'
                        FROM _sfx t WHERE s.faerslunumer = t.faerslunumer AND s.fastnum = t.fastnum""")
        n_upd = cur.rowcount
        summary = {"ruleset": RULESET_VERSION, "rows_updated": int(n_upd),
                   "suspect_full_pct": round(100*float(full.mean()), 3),
                   "matched": int(matched), "live_rows": int(len(m))}
        cur.execute("""INSERT INTO public.pipeline_runs (run_type, started_at, ended_at, exit_status, host, summary)
                       VALUES ('sales_history_suspect_backfill', now(), now(), 'ok', %s, %s)""",
                    (socket.gethostname(), json.dumps(summary)))
    c.commit(); c.close()
    print(f"\n  APPLIED: {n_upd:,} rows updated + pipeline_runs stamped. COMMIT ok.")


if __name__ == "__main__":
    main()
