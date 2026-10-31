-- cc288-v3 — SAMANLAGT FASTEIGNAMAT GÖTU (og svæða) í kassanum „Fasteignamat HMS 2026“ (ósk Danna 31.10).
--
-- Mælikvarði: summa fasteignamats allra eininga götunnar; hvert fastanúmer EINU sinni (fastnum er einkvæmt í properties;
-- heilt fjölbýli á einu fastanúmeri = ein eining með fullu mati). Víða þýðið („heild“): allar einingar hópsins með mat
-- > 0, ekki afskráðar, óháð matsstigi og stærð; geymslubil (cc288-v2) utan. Lágmark n_heild ≥ 5 (regla 13).
-- Hver lína ber samtölu, n_heild og miðgildi á einingu.
-- „atvinnu“ = atvinnu samanlagt (4 raðaflokkar) — AÐEINS fyrir þennan mælikvarða: summa króna er sambærileg milli
-- flokka, kr/m² ekki (Á7). CHECK tryggir að atvinnu-raðir beri hvorki kr/m², mat á eign né breytingu.
-- Grunnregla 8 óhögguð. Grants: CREATE OR REPLACE VIEW heldur GRANT SELECT anon/authenticated (endurstaðfest í --prof).

ALTER TABLE semantic.fasteignamat_rodun
  ADD COLUMN n_heild               int NOT NULL DEFAULT 0 CHECK (n_heild >= 0),
  ADD COLUMN heildarmat_heild_thkr numeric,
  ADD COLUMN midg_mat_heild_thkr   numeric;

ALTER TABLE semantic.fasteignamat_rodun
  DROP CONSTRAINT fasteignamat_rodun_hopur_check,
  DROP CONSTRAINT fasteignamat_rodun_n_check;

ALTER TABLE semantic.fasteignamat_rodun
  ADD CONSTRAINT fasteignamat_rodun_hopur_check
    CHECK (hopur IN ('ibud', 'verslun', 'skrifstofa', 'idnadur_lager', 'gisting', 'atvinnu')),
  ADD CONSTRAINT fasteignamat_rodun_n_check CHECK (n >= 0),
  ADD CONSTRAINT fasteignamat_rodun_n_eda_heild CHECK (n >= 1 OR n_heild >= 1),
  ADD CONSTRAINT fasteignamat_rodun_heild_n
    CHECK ((heildarmat_heild_thkr IS NULL AND midg_mat_heild_thkr IS NULL) OR n_heild >= 5),
  ADD CONSTRAINT fasteignamat_rodun_atvinnu_adeins_samanlagt
    CHECK (hopur <> 'atvinnu' OR (n = 0 AND n_kr_m2 = 0 AND n_breyting = 0 AND midg_kr_m2 IS NULL
                                  AND midg_mat_eign_thkr IS NULL AND breyting_pct IS NULL AND heildarmat_thkr IS NULL));

COMMENT ON COLUMN semantic.fasteignamat_rodun.n_heild IS
  'cc288-v3: einingar í víða þýðinu (allar einingar hópsins með mat > 0, óháð matsstigi/stærð; geymslubil utan). Nefnari samtölunnar.';
COMMENT ON COLUMN semantic.fasteignamat_rodun.heildarmat_heild_thkr IS
  'cc288-v3: summa fasteignamats (þús. kr) allra eininga í víða þýðinu; hvert fastanúmer einu sinni. NULL undir n_heild 5.';

CREATE OR REPLACE VIEW semantic.v_fasteignamat_rodun AS
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
    k.reiknad_at,
    r.n_heild,
        CASE
            WHEN r.n_heild >= 5 THEN r.heildarmat_heild_thkr
            ELSE NULL::numeric
        END AS heildarmat_heild_thkr,
        CASE
            WHEN r.n_heild >= 5 THEN r.midg_mat_heild_thkr
            ELSE NULL::numeric
        END AS midg_mat_heild_thkr
   FROM semantic.fasteignamat_rodun r
     JOIN semantic.fasteignamat_keyrslur k ON k.keyrsla_id = r.keyrsla_id AND k.virk
  WHERE r.n >= 5 OR r.n_heild >= 5;
