# -*- coding: utf-8 -*-
r"""
cc180_llt_flip.py — staging + parity + ATÓMÍSKT rename-swap á public.last_listing_text.

Fordæmi: supabase/migrations/20260715_llt_augl_dagur.sql (cc2b) — söluyfirlits-
flöturinn les töfluna lifandi á prod, svo TRUNCATE+COPY (ACCESS EXCLUSIVE alla
hleðsluna) er EKKI notað. Í staðinn:

  --stage  <csv> --tag r3 --expect-rows N --expect-status k=v,k=v
        1. DROP IF EXISTS + CREATE public.last_listing_text_new (8 dálkar, sami
           PK (fastnum, sale_rank) + fastnum-vísir, RLS + public_read SELECT-only,
           grants) — Í SÖMU txn og COPY úr CSV.
        2. PARITY (read-only, eftir commit): rowcount == spá, pair_status-dreifing
           == spá, sale_rank samfelld ≤3 per fastnum, engin NULL lykil-/textareitur,
           sameiginlegar (fastnum, thinglyst_dagur, augl_id)-raðir stafrétt eins
           (md5(lysing_plain), scraped_at, augl_dagur, pair_status) og lifandi.
        3. Skrifar rollback-SQL FYRIR flipp:
           D:\_audit\cc180_textathekja\cc180_rollback_<tag>.sql

  --flip --tag r3 --expect-rows N
        EIN txn (READ WRITE fyrsta stæðan): sannreynir _new-rowcount == spá,
        rename lifandi → last_listing_text_old_<tag> (+ vísanöfn, sbr.
        feedback_endurnefning_skilur_visanofn_eftir), _new → last_listing_text
        (+ vísanöfn í upprunaleg heiti). _old missir anon/authenticated-SELECT +
        public_read-stefnuna (ekki app-lesin). NOTIFY pgrst reload schema eftir
        commit. Svo eftir-parity: lifandi rowcount + dreifing + relacl beggja.

  --status
        Sýnir töflurnar last_listing_text* með rowcount, relacl, RLS.

Pooler 6543: fyrsta stæða hverrar skrif-txn er SET TRANSACTION READ WRITE.
.dbconfig er UTF-8 með BOM → encoding='utf-8-sig'.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras

DBCONFIG = Path(r"D:\verdmat-is\.dbconfig")
AUDIT = Path(r"D:\_audit\cc180_textathekja")
LIVE = "last_listing_text"
NEW = "last_listing_text_new"
COLS = ("fastnum", "sale_rank", "thinglyst_dagur", "augl_id",
        "lysing_plain", "scraped_at", "augl_dagur", "pair_status")

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def dsn() -> str:
    return DBCONFIG.read_text(encoding="utf-8-sig").strip()


def open_ro():
    c = psycopg2.connect(dsn())
    c.set_session(isolation_level="REPEATABLE READ", readonly=True, autocommit=False)
    return c


def open_w():
    c = psycopg2.connect(dsn())
    c.autocommit = False
    return c


def one(cur, sql, params=None):
    cur.execute(sql, params)
    return cur.fetchone()


def parse_status(s: str) -> dict[str, int]:
    out = {}
    for part in s.split(","):
        k, v = part.split("=")
        out[k.strip()] = int(v)
    return out


# --------------------------------------------------------------------------- status
def status(cur, label=""):
    cur.execute("""
      SELECT c.relname, c.relacl::text, c.relrowsecurity,
             (SELECT count(*) FROM pg_policies p WHERE p.schemaname='public' AND p.tablename=c.relname) n_pol,
             s.n_live_tup
      FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      LEFT JOIN pg_stat_user_tables s ON s.relid=c.oid
      WHERE n.nspname='public' AND c.relkind='r' AND c.relname LIKE 'last_listing_text%'
      ORDER BY 1""")
    log(f"--- töflur last_listing_text* {label}---")
    for r in cur.fetchall():
        log(f"  {r[0]:<34} n_live≈{r[4]}  rls={r[2]}  policies={r[3]}  acl={r[1]}")
    cur.execute("""
      SELECT tablename, indexname FROM pg_indexes
      WHERE schemaname='public' AND tablename LIKE 'last_listing_text%' ORDER BY 1,2""")
    for r in cur.fetchall():
        log(f"  vísir  {r[0]:<34} {r[1]}")


# --------------------------------------------------------------------------- stage
def stage(args):
    csv_path = Path(args.stage)
    if not csv_path.exists():
        sys.exit(f"CSV vantar: {csv_path}")
    expect_status = parse_status(args.expect_status)
    sz = csv_path.stat().st_size / 1024 / 1024
    log(f"STAGE tag={args.tag}  csv={csv_path} ({sz:.1f} MB)  spá rows={args.expect_rows} status={expect_status}")

    c = open_w()
    try:
        with c.cursor() as cur:
            cur.execute("SET TRANSACTION READ WRITE")
            cur.execute("SET LOCAL statement_timeout = '20min'")  # COPY 160 MB; pooler-sjálfgefið féll á 2 mín 02.09
            cur.execute(f"DROP TABLE IF EXISTS public.{NEW}")
            cur.execute(f"""
              CREATE TABLE public.{NEW} (
                fastnum         bigint      NOT NULL,
                sale_rank       smallint    NOT NULL,
                thinglyst_dagur date,
                augl_id         text,
                lysing_plain    text,
                scraped_at      timestamp with time zone,
                augl_dagur      date,
                pair_status     text,
                CONSTRAINT {NEW}_pkey PRIMARY KEY (fastnum, sale_rank)
              )""")
            cur.execute(f"CREATE INDEX idx_last_listing_new_fastnum ON public.{NEW} USING btree (fastnum)")
            # RLS + grants Í SÖMU txn og stofnun (CLAUDE.md-reglan; feedback_ny_public_tafla_kemur_med_anon_arwdDxtm)
            cur.execute(f"ALTER TABLE public.{NEW} ENABLE ROW LEVEL SECURITY")
            cur.execute(f"REVOKE ALL ON TABLE public.{NEW} FROM anon, authenticated")
            cur.execute(f"CREATE POLICY public_read ON public.{NEW} FOR SELECT TO anon, authenticated USING (true)")
            cur.execute(f"GRANT SELECT ON TABLE public.{NEW} TO anon, authenticated")
            cur.execute(f"GRANT ALL ON TABLE public.{NEW} TO service_role")
            cur.execute(f"COMMENT ON COLUMN public.{NEW}.augl_dagur IS "
                        "'RAUNVERULEGUR birtingardagur auglýsingarinnar (matched_listing_date úr pairs_v1; "
                        "least(listed_at, first_seen_at) fyrir live_listings) — EKKI söludagurinn.'")
            cur.execute(f"COMMENT ON COLUMN public.{NEW}.pair_status IS "
                        "'Pörunarstaða: paired_fresh/paired_recent/paired_no_price/paired_stale úr pairs_v1 "
                        "(evalue-pakki, frosinn 2026-04-16); live_listings = pörun úr scraper.listings (mbl) "
                        "fyrir sölur þinglýstar eftir 2026-04-16 (cc180 R1-b). stale = eldri auglýsing endurnotuð.'")
            t0 = time.time()
            col_clause = "(" + ",".join(COLS) + ")"
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                cur.copy_expert(f"COPY public.{NEW} {col_clause} FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')", f)
            n = one(cur, f"SELECT count(*) FROM public.{NEW}")[0]
            log(f"  COPY {n:,} raðir á {time.time()-t0:.1f}s")
            if n != args.expect_rows:
                c.rollback()
                sys.exit(f"HLIÐ FALLIÐ: rowcount {n} != spá {args.expect_rows} — ROLLBACK, ekkert stendur eftir")
        c.commit()
        log("  COMMIT staging")
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

    # ---------------- PARITY (read-only) ----------------
    ok = True
    ro = open_ro()
    try:
        with ro.cursor() as cur:
            n = one(cur, f"SELECT count(*) FROM public.{NEW}")[0]
            nf = one(cur, f"SELECT count(DISTINCT fastnum) FROM public.{NEW}")[0]
            log(f"PARITY [1] rowcount {n:,} == spá {args.expect_rows:,}: {'OK' if n == args.expect_rows else 'FALL'}   fastnum {nf:,}")
            ok &= n == args.expect_rows
            cur.execute(f"SELECT pair_status, count(*) FROM public.{NEW} GROUP BY 1 ORDER BY 1")
            dist = {r[0]: r[1] for r in cur.fetchall()}
            same = dist == expect_status
            log(f"PARITY [2] pair_status {dist} == spá: {'OK' if same else 'FALL ' + str(expect_status)}")
            ok &= same
            r = one(cur, f"""
              SELECT count(*) FILTER (WHERE bad_rank>0), count(*) FILTER (WHERE mx>3)
              FROM (SELECT fastnum, max(sale_rank) mx,
                           count(*) FILTER (WHERE sale_rank<1 OR sale_rank>3) bad_rank,
                           (max(sale_rank) <> count(*))::int gap
                    FROM public.{NEW} GROUP BY fastnum) g""")
            g = one(cur, f"""
              SELECT count(*) FROM (SELECT fastnum FROM public.{NEW} GROUP BY fastnum
                                    HAVING max(sale_rank) <> count(*)) x""")[0]
            log(f"PARITY [3] sale_rank: utan 1..3 = {r[0]}, >3 per fastnum = {r[1]}, ósamfelld = {g}: {'OK' if r[0]==0 and r[1]==0 and g==0 else 'FALL'}")
            ok &= r[0] == 0 and r[1] == 0 and g == 0
            r = one(cur, f"""
              SELECT count(*) FILTER (WHERE thinglyst_dagur IS NULL),
                     count(*) FILTER (WHERE augl_id IS NULL),
                     count(*) FILTER (WHERE lysing_plain IS NULL),
                     count(*) FILTER (WHERE length(lysing_plain) < 200),
                     count(*) FILTER (WHERE augl_dagur IS NULL),
                     count(*) FILTER (WHERE scraped_at IS NULL),
                     count(*) FILTER (WHERE lysing_plain ~ '<[a-zA-Z/][^>]*>')
              FROM public.{NEW}""")
            lv = one(cur, f"""
              SELECT count(*) FILTER (WHERE lysing_plain IS NULL),
                     count(*) FILTER (WHERE lysing_plain ~ '<[a-zA-Z/][^>]*>'),
                     count(*) FILTER (WHERE length(lysing_plain) < 200)
              FROM public.{LIVE}""")
            # Hart hlið: lyklar. Mjúkt hlið: NULL-texti / HTML-leifar mega ekki VERSNA
            # umfram lifandi (arfur byggingarinnar: 4 NULL / 6 '<br>'-leifar / 12 <200 í júlí-árgangi).
            log(f"PARITY [4] NULL: thinglyst_dagur={r[0]} augl_id={r[1]} augl_dagur={r[4]} scraped_at={r[5]} | "
                f"lysing_plain NULL={r[2]} (lifandi {lv[0]}), <200 stafir={r[3]} (lifandi {lv[2]}), HTML-leifar={r[6]} (lifandi {lv[1]}): "
                f"{'OK' if r[0]==0 and r[1]==0 and r[6] <= lv[1] else 'FALL'}")
            ok &= r[0] == 0 and r[1] == 0 and r[6] <= lv[1]
            # sameiginlegar raðir vid LIFANDI: stafrétt eins?
            r = one(cur, f"""
              WITH j AS (
                SELECT l.fastnum, l.thinglyst_dagur, l.augl_id,
                       (md5(coalesce(l.lysing_plain,'')) = md5(coalesce(n.lysing_plain,''))) t_ok,
                       (l.scraped_at IS NOT DISTINCT FROM n.scraped_at) s_ok,
                       (l.augl_dagur IS NOT DISTINCT FROM n.augl_dagur) d_ok,
                       (l.pair_status IS NOT DISTINCT FROM n.pair_status) p_ok
                FROM public.{LIVE} l
                JOIN public.{NEW} n ON n.fastnum=l.fastnum AND n.thinglyst_dagur=l.thinglyst_dagur AND n.augl_id=l.augl_id)
              SELECT count(*), count(*) FILTER (WHERE NOT t_ok), count(*) FILTER (WHERE NOT s_ok),
                     count(*) FILTER (WHERE NOT d_ok), count(*) FILTER (WHERE NOT p_ok)
              FROM j""")
            n_live = one(cur, f"SELECT count(*) FROM public.{LIVE}")[0]
            log(f"PARITY [5] sameiginlegar (fastnum,thinglyst_dagur,augl_id) við lifandi: {r[0]:,} af {n_live:,} lifandi; "
                f"misræmi texti={r[1]} scraped_at={r[2]} augl_dagur={r[3]} pair_status={r[4]}: {'OK' if r[1]==0 and r[2]==0 and r[3]==0 and r[4]==0 else 'FALL'}")
            ok &= r[1] == 0 and r[2] == 0 and r[3] == 0 and r[4] == 0
            miss = one(cur, f"""
              SELECT count(*) FROM public.{LIVE} l
              WHERE NOT EXISTS (SELECT 1 FROM public.{NEW} n
                                WHERE n.fastnum=l.fastnum AND n.thinglyst_dagur=l.thinglyst_dagur AND n.augl_id=l.augl_id)""")[0]
            log(f"PARITY [6] lifandi raðir sem EKKI eru í _new (ýtt út af top-3 þaki): {miss:,}"
                + (f"  (spá {args.expect_displaced}: {'OK' if miss == args.expect_displaced else 'FALL'})" if args.expect_displaced is not None else ""))
            if args.expect_displaced is not None:
                ok &= miss == args.expect_displaced
            status(cur, "eftir staging ")
    finally:
        ro.rollback()
        ro.close()

    # ---------------- ROLLBACK-SQL skrifað FYRIR flipp ----------------
    old = f"{LIVE}_old_{args.tag}"
    rb = AUDIT / f"cc180_rollback_{args.tag}.sql"
    rb.write_text(f"""-- cc180_rollback_{args.tag}.sql — skrifað af cc180_llt_flip.py --stage {dt.datetime.now(dt.timezone.utc).isoformat()}
-- Bakfærir rename-swap flippsins (tag={args.tag}): lifandi taflan (nýja) verður
-- {LIVE}_rolledback_{args.tag}, og {old} (upprunalega) verður aftur {LIVE}.
-- EIN txn; READ WRITE er fyrsta stæðan (pooler 6543). Væntur rowcount á {LIVE} eftir: {n_live}.
BEGIN;
SET TRANSACTION READ WRITE;
ALTER TABLE public.{LIVE} RENAME TO {LIVE}_rolledback_{args.tag};
ALTER INDEX public.{LIVE}_pkey RENAME TO {LIVE}_rolledback_{args.tag}_pkey;
ALTER INDEX public.idx_last_listing_fastnum RENAME TO idx_last_listing_rolledback_{args.tag}_fastnum;
ALTER TABLE public.{old} RENAME TO {LIVE};
ALTER INDEX public.{old}_pkey RENAME TO {LIVE}_pkey;
ALTER INDEX public.idx_last_listing_old_{args.tag}_fastnum RENAME TO idx_last_listing_fastnum;
-- endurheimta app-lestur á upprunalegu töflunni
CREATE POLICY public_read ON public.{LIVE} FOR SELECT TO anon, authenticated USING (true);
GRANT SELECT ON TABLE public.{LIVE} TO anon, authenticated;
-- loka þeirri sem tekin var úr umferð
REVOKE ALL ON TABLE public.{LIVE}_rolledback_{args.tag} FROM anon, authenticated;
DROP POLICY IF EXISTS public_read ON public.{LIVE}_rolledback_{args.tag};
COMMIT;
NOTIFY pgrst, 'reload schema';
-- Varaleið ef {old} er horfin: \\copy public.{LIVE} FROM 'D:\\_audit\\cc180_textathekja\\last_listing_text_pre_cc180_60807.csv' CSV HEADER
""", encoding="utf-8")
    log(f"rollback skrifað: {rb}")
    log(f"STAGE {'PARITY OK — tilbúið í --flip' if ok else 'PARITY FALL — EKKI flippa'}")
    return 0 if ok else 2


# --------------------------------------------------------------------------- flip
def flip(args):
    old = f"{LIVE}_old_{args.tag}"
    rb = AUDIT / f"cc180_rollback_{args.tag}.sql"
    if not rb.exists():
        sys.exit(f"Rollback-SQL vantar ({rb}) — keyrðu --stage fyrst")
    c = open_w()
    try:
        with c.cursor() as cur:
            cur.execute("SET TRANSACTION READ WRITE")
            n_new = one(cur, f"SELECT count(*) FROM public.{NEW}")[0]
            n_live = one(cur, f"SELECT count(*) FROM public.{LIVE}")[0]
            log(f"FLIP tag={args.tag}: _new={n_new:,} (spá {args.expect_rows:,}), lifandi={n_live:,}")
            if n_new != args.expect_rows:
                c.rollback()
                sys.exit("HLIÐ FALLIÐ: _new rowcount != spá — ekkert flippað")
            ex = one(cur, "SELECT to_regclass(%s)", (f"public.{old}",))[0]
            if ex is not None:
                c.rollback()
                sys.exit(f"{old} er þegar til — veldu annað --tag eða felldu hana fyrst")
            cur.execute(f"ALTER TABLE public.{LIVE} RENAME TO {old}")
            cur.execute(f"ALTER INDEX public.{LIVE}_pkey RENAME TO {old}_pkey")
            cur.execute(f"ALTER INDEX public.idx_last_listing_fastnum RENAME TO idx_last_listing_old_{args.tag}_fastnum")
            cur.execute(f"ALTER TABLE public.{NEW} RENAME TO {LIVE}")
            cur.execute(f"ALTER INDEX public.{NEW}_pkey RENAME TO {LIVE}_pkey")
            cur.execute(f"ALTER INDEX public.idx_last_listing_new_fastnum RENAME TO idx_last_listing_fastnum")
            # gamla taflan er ekki app-lesin lengur: loka anon/authenticated
            cur.execute(f"DROP POLICY IF EXISTS public_read ON public.{old}")
            cur.execute(f"REVOKE ALL ON TABLE public.{old} FROM anon, authenticated")
            n_after = one(cur, f"SELECT count(*) FROM public.{LIVE}")[0]
            if n_after != args.expect_rows:
                c.rollback()
                sys.exit("HLIÐ FALLIÐ eftir swap — ROLLBACK")
        c.commit()
        log("  COMMIT swap")
        with c.cursor() as cur:
            cur.execute("SET TRANSACTION READ WRITE")
            cur.execute("NOTIFY pgrst, 'reload schema'")
        c.commit()
        log("  NOTIFY pgrst reload schema")
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

    ro = open_ro()
    try:
        with ro.cursor() as cur:
            n = one(cur, f"SELECT count(*) FROM public.{LIVE}")[0]
            cur.execute(f"SELECT pair_status, count(*) FROM public.{LIVE} GROUP BY 1 ORDER BY 1")
            dist = {r[0]: r[1] for r in cur.fetchall()}
            mx = one(cur, f"SELECT max(thinglyst_dagur), max(scraped_at) FROM public.{LIVE}")
            log(f"EFTIR FLIPP: {LIVE} = {n:,} raðir  dreifing={dist}  max(thinglyst_dagur)={mx[0]} max(scraped_at)={mx[1]}")
            status(cur, "eftir flipp ")
    finally:
        ro.rollback()
        ro.close()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", metavar="CSV")
    ap.add_argument("--flip", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--tag", default="r3")
    ap.add_argument("--expect-rows", type=int)
    ap.add_argument("--expect-status", default="")
    ap.add_argument("--expect-displaced", type=int, default=None)
    args = ap.parse_args()
    if args.status:
        ro = open_ro()
        try:
            with ro.cursor() as cur:
                status(cur)
        finally:
            ro.rollback()
            ro.close()
        return 0
    if args.stage:
        if args.expect_rows is None or not args.expect_status:
            sys.exit("--stage þarf --expect-rows og --expect-status")
        return stage(args)
    if args.flip:
        if args.expect_rows is None:
            sys.exit("--flip þarf --expect-rows")
        return flip(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
