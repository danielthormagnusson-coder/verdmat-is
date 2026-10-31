-- ROLLBACK 20261101110000_cc288_v3_samanlagt (skrifað á undan migration, cc288-v3).
-- Fjarlægir „atvinnu samanlagt“-raðir og raðir sem aðeins eru til í víða þýðinu (n < 1), endurheimtir sýnina og
-- skorðurnar ORÐRÉTT eins og þær voru (lesnar úr DB af c7_smida_v3.py) og fellir þrjá heildardálka.
-- Eftir rollback: keyra scripts/cc288_fasteignamat.py --skrifa á cc288-v2-kóða (a69f68f) til að fá hreina v2-keyrslu.
DELETE FROM semantic.fasteignamat_rodun WHERE hopur = 'atvinnu' OR n < 1;
DROP VIEW semantic.v_fasteignamat_rodun;
CREATE VIEW semantic.v_fasteignamat_rodun AS
SELECT r.argerd,
    k.argerd_breyting,
    r.hopur,
    r.tegund,
    r.stig,
    r.lykill,
    r.heiti,
    r.gata,
    r.postnr,
    r.matsvaedi_numer,
    r.svfn,
    r.svf,
    r.n,
    r.n_kr_m2,
        CASE
            WHEN r.n_kr_m2 >= 5 THEN r.midg_kr_m2
            ELSE NULL::numeric
        END AS midg_kr_m2,
        CASE
            WHEN r.n >= 5 THEN r.midg_mat_eign_thkr
            ELSE NULL::numeric
        END AS midg_mat_eign_thkr,
    r.heildarmat_thkr,
    r.midg_flm,
    r.n_breyting,
        CASE
            WHEN r.n_breyting >= 5 THEN r.breyting_pct
            ELSE NULL::numeric
        END AS breyting_pct,
    k.regla_version,
    k.sott_argerd,
    k.sott_breyting,
    k.reiknad_at
   FROM semantic.fasteignamat_rodun r
     JOIN semantic.fasteignamat_keyrslur k ON k.keyrsla_id = r.keyrsla_id AND k.virk
  WHERE r.n >= 5;
REVOKE ALL ON semantic.v_fasteignamat_rodun FROM PUBLIC, anon, authenticated;
GRANT SELECT ON semantic.v_fasteignamat_rodun TO anon, authenticated;
ALTER TABLE semantic.fasteignamat_rodun
  DROP CONSTRAINT fasteignamat_rodun_atvinnu_adeins_samanlagt,
  DROP CONSTRAINT fasteignamat_rodun_heild_n,
  DROP CONSTRAINT fasteignamat_rodun_n_eda_heild,
  DROP CONSTRAINT fasteignamat_rodun_hopur_check,
  DROP CONSTRAINT fasteignamat_rodun_n_check;
ALTER TABLE semantic.fasteignamat_rodun
  DROP COLUMN n_heild,
  DROP COLUMN heildarmat_heild_thkr,
  DROP COLUMN midg_mat_heild_thkr;
ALTER TABLE semantic.fasteignamat_rodun
  ADD CONSTRAINT fasteignamat_rodun_hopur_check CHECK ((hopur = ANY (ARRAY['ibud'::text, 'verslun'::text, 'skrifstofa'::text, 'idnadur_lager'::text, 'gisting'::text]))),
  ADD CONSTRAINT fasteignamat_rodun_n_check CHECK ((n >= 1));
