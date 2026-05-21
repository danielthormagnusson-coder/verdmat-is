import psycopg2

uri = open(r"D:\verdmat-is\.dbconfig", encoding="utf-8-sig").read().strip()
with psycopg2.connect(uri) as conn, conn.cursor() as cur:
    cur.execute(
        """
        SELECT column_name, data_type
          FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'ats_lookup'
         ORDER BY ordinal_position
        """
    )
    print("ats_lookup columns:")
    for c, t in cur.fetchall():
        print(f"  {c:35s} {t}")
    cur.execute("SELECT count(*) FROM public.ats_lookup")
    print("ats_lookup rowcount:", cur.fetchone()[0])
