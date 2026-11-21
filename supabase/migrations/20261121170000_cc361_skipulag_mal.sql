-- cc361: skipulags- og byggingarsaga lóðar á /eign — mál úr fundargerðum sveitarfélaga.
--
-- Heimild: útflutningur registur_ut.skipulag_verdmat (persónuupplýsingar hreinsaðar við upptök), lesinn vikulega
-- af scripts/skipulag_innlestur.py. Aðeins mál með landnr eru geymd (birtingarregla: mál eru á lóð, ekki íbúð).
-- Mæling og nefnarar: SKIL_CC361 (A1-A5).
--
-- Aðgangur: RLS á, engar stefnur, engin réttindi fyrir PUBLIC/anon/authenticated. Aðeins service_role les
-- (þjónninn um sb_secret). Ný public-tafla kemur með anon arwdDxtm: REVOKE í SÖMU færslu.
-- BEGIN/COMMIT eru ekki hér: beitingarskriftan stýrir færslunni (lock_timeout 5s).

CREATE TABLE public.skipulag_mal (
  id               integer     PRIMARY KEY,           -- auðkenni heimildar (stöðugt milli útflutninga)
  sveitarfelag     text        NOT NULL,
  svfn             smallint,                          -- sveitarfélagsnúmer, leitt af nafni við innlestur
  nefnd            text        NOT NULL,
  dagsetning       date        NOT NULL,              -- fundardagur
  fundarnumer      text,
  malsnumer        text,
  heimilisfang     text,
  landnr           integer     NOT NULL,
  landnr_uppruni   text,
  fyrirsogn        text,
  malsflokkur      text,
  lysing           text,
  nidurstada       text,
  slod_fundargerd  text,
  hreinsad         boolean     NOT NULL DEFAULT false, -- satt: texti styttur eða nöfn felld út við upptök
  hreinsun_utgafa  text,
  heimild_keyrt    timestamptz,                       -- hvenær heimildin sótti fundargerðina
  heimild_utflutt  timestamptz NOT NULL,              -- utflutt úr skipulag_stada við þann innlestur
  hladid_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX skipulag_mal_landnr_dags ON public.skipulag_mal (landnr, dagsetning DESC, id DESC);

ALTER TABLE public.skipulag_mal ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.skipulag_mal FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.skipulag_mal TO service_role;
COMMENT ON TABLE public.skipulag_mal IS
  'cc361: mál úr fundargerðum skipulags- og byggingarnefnda á lóð (landnr). Vikulegur innlestur (skipulag_innlestur.py). Aðeins service_role.';

-- Saga lóðar fyrir eina eign: mál á lóð eignarinnar (sama saga á öllum eignum lóðarinnar), nýjast fyrst, í síðum.
-- p_hlidrun = fjöldi mála sem sleppt er framan af; p_hamark = síðustærð, þakin við 100 HÉR (ekki aðeins í kallanda).
-- heildarfjoldi (í hverri röð) = fjöldi mála á lóðinni eftir síur, óháð síðu: framendinn sýnir „Sjá öll N mál".
-- /eign les fyrstu 25 (sjálfgefið); /api/skipulagssaga les restina í síðum af 100.
-- Mál sem parað er við lóð í öðru sveitarfélagi en eignin er sleppt (pörunarvilla heimildar, A3).
-- Tvítekin lína (sama nefnd, dagur, málsnúmer, fyrirsögn) birtist einu sinni, lægsta id (A4).
CREATE FUNCTION public.skipulag_saga(p_fastnum bigint, p_hlidrun integer DEFAULT 0, p_hamark integer DEFAULT 25)
RETURNS TABLE (
  id integer, dagsetning date, sveitarfelag text, nefnd text, fundarnumer text, malsnumer text, fyrirsogn text, malsflokkur text,
  nidurstada text, lysing text, hreinsad boolean, slod_fundargerd text, landnr integer, heildarfjoldi integer
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
  WITH e AS (
    SELECT CASE WHEN p.landeign_nr ~ '^[0-9]{1,9}$' THEN p.landeign_nr::integer END AS landnr, p.svfn
      FROM public.properties p
     WHERE p.fastnum = p_fastnum
  ), d AS (
    SELECT DISTINCT ON (m.dagsetning, m.nefnd, coalesce(m.malsnumer, ''), coalesce(m.fyrirsogn, ''))
           m.id, m.dagsetning, m.sveitarfelag, m.nefnd, m.fundarnumer, m.malsnumer, m.fyrirsogn, m.malsflokkur,
           m.nidurstada, m.lysing, m.hreinsad, m.slod_fundargerd, m.landnr
      FROM e JOIN public.skipulag_mal m ON m.landnr = e.landnr
     WHERE e.svfn IS NULL OR m.svfn IS NULL OR m.svfn = e.svfn
     ORDER BY m.dagsetning, m.nefnd, coalesce(m.malsnumer, ''), coalesce(m.fyrirsogn, ''), m.id
  )
  SELECT d.*, (count(*) OVER ())::integer AS heildarfjoldi
    FROM d
   ORDER BY d.dagsetning DESC, d.id DESC
   LIMIT LEAST(GREATEST(coalesce(p_hamark, 25), 1), 100)
  OFFSET GREATEST(coalesce(p_hlidrun, 0), 0)
$$;
REVOKE ALL ON FUNCTION public.skipulag_saga(bigint, integer, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.skipulag_saga(bigint, integer, integer) TO service_role;
COMMENT ON FUNCTION public.skipulag_saga(bigint, integer, integer) IS
  'cc361: mál á lóð eignar (fastnum), nýjast fyrst, í síðum (hliðrun, hámark mest 100); heildarfjoldi í hverri röð. Aðeins service_role (þjónn). Engin mál = engar raðir.';

NOTIFY pgrst, 'reload schema';
