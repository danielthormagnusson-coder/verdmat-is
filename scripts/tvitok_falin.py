"""cc276: endurreikningur efnisgerða sóttkvíarmengisins scraper.tvitok_falin.

Lesfletirnir (v_eign_virk_auglysing, v_leit_listings) lesa töfluna; reglan sjálf (elsta LIFANDI eintak
klasans birtist, cc267 ákvörðun 2) býr óbreytt í scraper.v_tvitok_falin og er lesin AÐEINS af
scraper.endurreikna_tvitok_falin(). Skrifararnir á inntök reglunnar kalla þetta í lok keyrslu:
  promote_listings_append (status, listed_at, listing_tvitok) · lifecycle_sweep_mbl (atburðir + status)

Hliðið: gerir ekkert ef taflan er ekki til (migration cc276 = GO-hliðið), sama mynstur og cc267-vörnin.
"""
from __future__ import annotations


def endurreikna(pg, log=print):
    """(baett, eytt, alls) eða None ef migration cc276 er ekki beitt. Eigin færsla, commit hér.
    baett/eytt = hversu langt taflan var á eftir reglunni fyrir þennan endurreikning."""
    pg.rollback()
    cur = pg.cursor()
    cur.execute("SELECT to_regclass('scraper.tvitok_falin') IS NOT NULL")
    if not cur.fetchone()[0]:
        pg.rollback()
        log("  tvitok_falin: ÓVIRK — scraper.tvitok_falin ekki til (migration cc276 óbeitt)")
        return None
    pg.rollback()  # loka les-færslunni; SET TRANSACTION READ WRITE verður fyrsta skipun
    cur.execute("SET TRANSACTION READ WRITE")
    cur.execute("SET LOCAL statement_timeout = '120s'")
    cur.execute("SELECT baett, eytt, alls FROM scraper.endurreikna_tvitok_falin()")
    baett, eytt, alls = cur.fetchone()
    pg.commit()
    log(f"  tvitok_falin endurreiknuð: +{baett} −{eytt} = {alls} faldar")
    return baett, eytt, alls
