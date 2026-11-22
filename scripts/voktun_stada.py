"""cc355 (ákvörðun 22.11 liður 5): ein lína um vöktun síðasta sólarhring fyrir vaktarpóstinn (scripts/vakt_kedja.ps1). Aðeins lestur.

Úttak (stdout, UTF-8), ein lína:
    VOKTUN: askriftir=N atburdir=M postar=K
      N = staðfestar áskriftir núna (public.voktun_askrift, stadfest_at is not null; allar tegundir) — staða, ekki hreyfing
      M = atburðir sem vöktunin skráði síðasta sólarhring (public.voktun_atburdur, fundid_at > nú − 24 klst.; allar tegundir)
      K = póstar sendir síðasta sólarhring (einkvæm resend_id í public.voktun_sendur, sent_at > nú − 24 klst.;
          sama talning og sendir_i_dag í voktun_verk.py: einn póstur ber margar raðir)
    eða  VOKTUN: MAELING_MISTOKST <villutegund>    (lestur brást; ekkert netfang, enginn lykill prentaður)
Tölur nást ekki (MAELING_MISTOKST eða ekkert úttak) = „athygli“ í vaktarpósti (svar Danna 22.11); tölur nást = stig óbreytt.
Engin netföng eru lesin. rc alltaf 0.
Próf: --nu <ISO> = viðmiðunartími (annars núið).
"""
import argparse, datetime as dt, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def lesa(nu):
    import psycopg2
    c = psycopg2.connect(Path(r"D:\verdmat-is\.dbconfig").read_text(encoding="utf-8-sig").strip(), connect_timeout=15)
    try:
        c.set_session(readonly=True, autocommit=False)
        cur = c.cursor()
        cur.execute("set statement_timeout = '30s'")
        cur.execute("""select (select count(*) from public.voktun_askrift where stadfest_at is not null),
                              (select count(*) from public.voktun_atburdur where fundid_at > %(f)s and fundid_at <= %(n)s),
                              (select count(distinct resend_id) from public.voktun_sendur where sent_at > %(f)s and sent_at <= %(n)s)""",
                    {"f": nu - dt.timedelta(hours=24), "n": nu})
        return cur.fetchone()
    finally:
        c.rollback()
        c.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nu", default=None)
    a = ap.parse_args()
    nu = dt.datetime.fromisoformat(a.nu) if a.nu else dt.datetime.now(dt.timezone.utc)
    try:
        n, m, k = lesa(nu)
    except Exception as e:
        print(f"VOKTUN: MAELING_MISTOKST {type(e).__name__}")
        return 0
    print(f"VOKTUN: askriftir={n} atburdir={m} postar={k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
