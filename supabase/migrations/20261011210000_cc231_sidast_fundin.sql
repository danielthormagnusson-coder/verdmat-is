-- cc231: scraper.listings.sidast_fundin_at — síðasta skipti sem lífsferilssópun mbl (kort-, sölu- eða
-- leigulota) FANN auglýsinguna lifandi. NULL = aldrei fundin af sópun (eða fyrir 04.07, eða ekki mbl).
--
-- Hvers vegna sér dálkur (cc230 §1, ákvörðun (i)): last_seen_at fyrir mbl er síðasta DELTA-sókn (sala)
-- eða `updated` frá mbl (leiga) og sópunin skrifar hann aldrei. last_seen_at er ÓSNERTUR — hann ber
-- áfram „síðasta delta-sókn" sem verdvakt_skra_athuganir og cc180 byggja á.
--
-- Skrifari: app/scripts/lifecycle_sweep_mbl.py (write_events, sama færsla og atburðir).
-- Afturfylling frá 04.07 úr hringskrám + state-JSON: D:\_audit\cc231_sopun\b1_afturfylling.py.
-- Nullable án sjálfgildis = aðeins lýsigögn (engin endurritun 85K raða), en ACCESS EXCLUSIVE lás í augnablik.
BEGIN;
SET TRANSACTION READ WRITE;

ALTER TABLE scraper.listings ADD COLUMN sidast_fundin_at timestamptz;

COMMENT ON COLUMN scraper.listings.sidast_fundin_at IS
  'cc231: síðast fundin lifandi af lífsferilssópun mbl (kort/sala/leiga). NULL = aldrei fundin af sópun. '
  'Afturfyllt frá 04.07.2026 úr hringskrám (neðri mörk). Ekki last_seen_at (= síðasta delta-sókn).';

COMMIT;
