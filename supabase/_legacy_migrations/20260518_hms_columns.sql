-- HMS columns added to public.properties for Phase C UI / Phase D Supabase sync
-- (logged 2026-05-18). All nullable; Phase D fills existing rows in a separate
-- session. Reversible via DROP COLUMN (rollback block at bottom of file).
--
-- Source: HMS Fasteignaskrá full-scrape 2026-05-18 (commit 57dea2c). See
-- audit/weekend_run_summary.md for the schema design rationale.

ALTER TABLE public.properties
    ADD COLUMN brunabotamat           numeric,
    ADD COLUMN lhlmat                 numeric,
    ADD COLUMN fasteignamat_naesta_ar numeric,
    ADD COLUMN byggingarstig          text,
    ADD COLUMN skodags                date,
    ADD COLUMN gerd                   text,
    ADD COLUMN matsstig               text,
    ADD COLUMN landeign_nr            text,
    ADD COLUMN matseiningar           jsonb,
    ADD COLUMN tengd_stadfang_nr      jsonb,
    ADD COLUMN deregistered           boolean DEFAULT false;

COMMENT ON COLUMN public.properties.brunabotamat IS
    'HMS endurbyggingarmat (rebuild / fire-insurance valuation), independent of market price. Same unit as fasteignamat (thousand kr).';
COMMENT ON COLUMN public.properties.lhlmat IS
    'Ratio 0..1 of land share of fasteignamat. NULL for non-residential or unset.';
COMMENT ON COLUMN public.properties.fasteignamat_naesta_ar IS
    'HMS next-year fasteignamat forecast (kept in same unit as fasteignamat). Published in June each year.';
COMMENT ON COLUMN public.properties.byggingarstig IS
    'HMS construction stage code: B0/B1/B2/B3/B4. B4 = Fullbúið. NULL = no building or unset.';
COMMENT ON COLUMN public.properties.skodags IS
    'Date of last on-site HMS inspection. NULL if never inspected.';
COMMENT ON COLUMN public.properties.gerd IS
    'HMS internal sub-classification code (per-matseining, top-level summary).';
COMMENT ON COLUMN public.properties.matsstig IS
    'HMS assessment quality stage code.';
COMMENT ON COLUMN public.properties.landeign_nr IS
    'HMS land-parcel ID. Groups multiple fastnums sharing a lot (e.g., apartments in same building).';
COMMENT ON COLUMN public.properties.matseiningar IS
    'JSONB array of sub-units (matseiningar). Each entry: { merking, einflm, byggingarar, byggingarstig, gerd, matsstig, brunabotamat, fasteignamat, notkun_kodi, notkun_texti, texti, skodags }.';
COMMENT ON COLUMN public.properties.tengd_stadfang_nr IS
    'JSONB array of related staðfang IDs cross-referenced from HMS.';
COMMENT ON COLUMN public.properties.deregistered IS
    'TRUE if HMS no longer recognises this fastnum (ghost handling). Default false. Set TRUE by Phase D for the 97 known ghosts.';

-- ---------------------------------------------------------------------------
-- Rollback (manual, not auto-executed):
-- ---------------------------------------------------------------------------
--   ALTER TABLE public.properties
--       DROP COLUMN brunabotamat,
--       DROP COLUMN lhlmat,
--       DROP COLUMN fasteignamat_naesta_ar,
--       DROP COLUMN byggingarstig,
--       DROP COLUMN skodags,
--       DROP COLUMN gerd,
--       DROP COLUMN matsstig,
--       DROP COLUMN landeign_nr,
--       DROP COLUMN matseiningar,
--       DROP COLUMN tengd_stadfang_nr,
--       DROP COLUMN deregistered;
