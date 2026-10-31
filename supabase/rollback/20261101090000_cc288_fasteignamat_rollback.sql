-- ROLLBACK 20261101090000_cc288_fasteignamat (skrifað á undan migration, cc288).
-- Fjarlægir ALLT sem migration bjó til. Gögnin eru endurreiknanleg (scripts/cc288_fasteignamat.py).
-- Snertir ekki properties né neinn eldri hlut.
DROP VIEW IF EXISTS semantic.v_fasteignamat_keyrsla;
DROP VIEW IF EXISTS semantic.v_fasteignamat_rodun;
DROP TABLE IF EXISTS semantic.fasteignamat_rodun;
DROP TABLE IF EXISTS semantic.fasteignamat_keyrslur;
DROP TABLE IF EXISTS semantic.atvinnu_flokkun;
DROP TABLE IF EXISTS semantic.fasteignamat_argerd;
