"""Probe target tables for the views_layer migration."""

from __future__ import annotations

import psycopg2

uri = open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read().strip()
with psycopg2.connect(uri) as conn, conn.cursor() as cur:
    print("-- tables/views with ats in name --")
    cur.execute(
        """
        SELECT table_schema, table_name, table_type
          FROM information_schema.tables
         WHERE table_name ILIKE '%ats%'
         ORDER BY table_schema, table_name
        """
    )
    for r in cur.fetchall():
        print(r)

    print()
    print("-- tables/views with predict in name --")
    cur.execute(
        """
        SELECT table_schema, table_name, table_type
          FROM information_schema.tables
         WHERE table_name ILIKE '%predict%'
         ORDER BY table_schema, table_name
        """
    )
    for r in cur.fetchall():
        print(r)

    print()
    print("-- predictions row count, distinct fastnum, max(predicted_at), distinct model_group --")
    cur.execute(
        """
        SELECT count(*), count(DISTINCT fastnum), max(predicted_at),
               count(DISTINCT model_group)
          FROM public.predictions
        """
    )
    print(cur.fetchone())

    print()
    print("-- predictions distinct (model_group, segment, model_version, calibration_version) top 20 --")
    cur.execute(
        """
        SELECT model_group, segment, model_version, calibration_version, count(*)
          FROM public.predictions
         GROUP BY 1, 2, 3, 4
         ORDER BY 5 DESC
         LIMIT 20
        """
    )
    for r in cur.fetchall():
        print(r)
