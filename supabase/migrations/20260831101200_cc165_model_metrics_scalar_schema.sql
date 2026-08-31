-- =====================================================================
-- cc165 — model_metrics-FLUTNINGURINN, SKEMADRÖG. ÓBEITT.
-- Skrifað 2026-08-14. ENGIN keyrsla, ekkert apply, engin MCP-migration.
-- Þessi skrá er UNDIRBÚNINGUR fyrir framkvæmdarlotu; hún má ekki keyrast
-- fyrr en borðið hefur valið (a) töfluheiti og (b) lesheimildarstöðu.
-- =====================================================================
--
-- HVERS VEGNA NÝ TAFLA EN EKKI ALTER Á public.model_metrics
-- ---------------------------------------------------------
-- `public.model_metrics` (skrifuð af scripts/model_quality_eval.py) er
-- NÁKVÆMNIMÆLING með fastri kornastærð: eina röðin er
--   (metric_run_id, model_version, oos_cutoff, score_type, segment_dim,
--    segment_value, sample_scope) -> n_pairs, mape, med_ape, bias, cov80, cov95
-- Sú tafla getur ekki borið „brúttó-áhrif uppgerðs eldhúss umfram
-- grunnstand, se, n" né „miðgildi kaupverðs/ásetts á fjórðungi" — það eru
-- ekki mape/cov80-dálkar. Að bæta teljara/nefnara-dálkum við hana með
-- NOT NULL myndi gera ALLAR fyrirliggjandi raðir ólöglegar; að bæta þeim
-- við NULL-hæfum eyðileggur nefnaraskylduna sem er allur tilgangur
-- þessarar töflu. Því: SÉRTAFLA, viðbótandi, sem snertir ekki
-- `model_metrics` og skiptir henni ekki út.
--
-- ÓVALIÐ (borðið): heitið `model_metrics_scalar` er drög. Valkostir:
--   `measured_metrics` (heiðarlegra — hluti raðanna er markaðsmæling,
--   ekki líkansmæling) eða `model_metrics_flat`. Nafnið er ódýrt að
--   breyta MEÐAN skráin er óbeitt; eftir apply er það migration.
--
-- NEFNARASKYLDAN ER DÁLKASKYLDA, EKKI VENJA
-- -----------------------------------------
-- `denominator` er NOT NULL og `denominator_def` er NOT NULL með lengdar-
-- skilyrði. Röð sem getur ekki sagt HVAÐ hún er hlutfall AF kemst ekki
-- inn. Þetta felldi tvær raðir í cc165-flutningnum (cc35 beinn kontrast
-- „uppgert vs gott" og „slæmt vs gott" — §3-taflan ritar „—" í n_treated).
-- Þær eru bókaðar á GAT-LEIFINA, ekki giskaðar.
--
-- ATH CHECK-GILDRAN (bókuð lexía): `CHECK (denominator > 0)` er SATT-
-- ÓÞEKKT og hleypir röð í gegn þegar denominator ER NULL. NOT NULL er
-- því hlífin, ekki CHECK-ið. Bæði eru sett; hvorugt eitt dugir.
-- =====================================================================

BEGIN;
SET TRANSACTION READ WRITE;  -- cc172 r01: pooler-reglan

CREATE TABLE public.model_metrics_scalar (
  id                bigserial PRIMARY KEY,

  -- HVAÐ er mælt
  metric_name       text        NOT NULL,   -- snake_case, stöðugt milli keyrslna
  metric_value      numeric     NOT NULL,   -- gildið sjálft, í `unit`
  unit              text        NOT NULL,   -- 'pct' | 'pct_pt' | 'ratio' | 'count' | 'kr' | 'days'

  -- NEFNARASKYLDAN
  numerator         numeric,               -- MÁ vanta (meðaltöl/miðgildi eiga engan teljara)
  denominator       numeric     NOT NULL,  -- MÁ ALDREI vanta
  denominator_def   text        NOT NULL,  -- hvað nefnarinn ER, í heilli setningu

  -- óvissa, þar sem hún er mæld
  se                numeric,               -- staðalvilla í sömu einingu og metric_value
  ci_lo             numeric,
  ci_hi             numeric,

  -- HVENÆR og Á HVAÐ
  computed_on       date        NOT NULL,  -- keyrsludagur mælingarinnar (EKKI innsetningardagur)
  model_version     text        NOT NULL,  -- 'iter4r_20260805_reglaR_strukt' | 'ekki_likansmaeling'

  -- HVAÐAN (heimildaskrá á D:)
  source_path       text        NOT NULL,  -- full D:-slóð á frosnu heimildina
  source_section    text,                  -- kafli/lykill/lína innan heimildar
  source_dated      date,                  -- dagsetning heimildarinnar sjálfrar

  -- STAÐA og BLÖNDUNARBANN
  status            text        NOT NULL
                    DEFAULT 'BIRTANLEG',   -- orðaforðinn úr leidretting_studlar_v1.json
  never_sum_with    text[],                -- t.d. '{fresh_edge}' — má ekki leggja saman
  supersedes_value  numeric,               -- úrelta talan sem þessi röð leysir af
  supersedes_source text,                  -- hvar úrelta talan stendur enn
  notes             text,

  created_at        timestamptz NOT NULL DEFAULT now(),

  -- ---- hliðin ----
  CONSTRAINT mms_denominator_positive
    CHECK (denominator > 0),
  CONSTRAINT mms_denominator_def_er_setning
    CHECK (length(btrim(denominator_def)) >= 20),
  CONSTRAINT mms_teljari_ekki_yfir_nefnara
    CHECK (numerator IS NULL OR numerator <= denominator),
  CONSTRAINT mms_unit_ordaforda
    CHECK (unit IN ('pct', 'pct_pt', 'ratio', 'count', 'kr', 'days')),
  CONSTRAINT mms_status_ordaforda
    CHECK (status IN ('BIRTANLEG', 'I-BID', 'OMAELANLEG', 'NULL-MAELT')),
  -- ATH: `LIKE 'D:\%'` VÆRI VILLA — bakstrikið er sjálfgefinn ESCAPE-stafur í
  -- LIKE, svo mynstrið læsi „D:" + bókstaflegt prósentumerki og felldi ALLAR
  -- raðir. left() er ótvírætt og þarf enga escape-reglu.
  CONSTRAINT mms_heimild_a_D
    CHECK (left(source_path, 3) = 'D:\'),
  CONSTRAINT mms_se_ekki_neikvaett
    CHECK (se IS NULL OR se >= 0),
  CONSTRAINT mms_bil_rett_rodud
    CHECK (ci_lo IS NULL OR ci_hi IS NULL OR ci_lo <= ci_hi)
);

-- Ein mæling per (heiti, líkansútgáfa, keyrsludagur). Endurkeyrsla sama dags
-- er UPPFÆRSLA, ekki ný röð — ON CONFLICT DO UPDATE í innsetningarskránni.
CREATE UNIQUE INDEX model_metrics_scalar_lykill
  ON public.model_metrics_scalar (metric_name, model_version, computed_on);

CREATE INDEX model_metrics_scalar_nafn_idx
  ON public.model_metrics_scalar (metric_name, computed_on DESC);

COMMENT ON TABLE public.model_metrics_scalar IS
  'cc165 — mældir skalarar fluttir af frosnum D:-skjölum inn í Supabase svo '
  'pakkasmiðurinn geti lesið þá úr fyrirspurn (harða reglan: tala sem aðeins '
  'er til á D: fer á GAT-LISTANN, ekki í pakkann). LEYSIR EKKI public.model_metrics '
  'af hólmi — sú tafla er áfram úttak vikulegu model_quality_eval-keyrslunnar.';
COMMENT ON COLUMN public.model_metrics_scalar.denominator IS
  'NOT NULL AF ÁSETTU RÁÐI. Tala án nefnara er ekki mæling. Röð sem getur ekki '
  'sagt hvað hún er hlutfall af á heima á GAT-listanum, ekki í töflunni.';
COMMENT ON COLUMN public.model_metrics_scalar.denominator_def IS
  'Heil setning: hvaða þýði nefnarinn telur, hvaða síur voru virkar, hvaða '
  'pörun. Tvær mælingar með sama heiti en ólíkum nefnara eru SYSTKIN, ekki '
  'framhald hvor af annarri — þessi reitur er það sem sker úr.';
COMMENT ON COLUMN public.model_metrics_scalar.computed_on IS
  'Dagur MÆLINGARINNAR, ekki dagur innsetningar. created_at ber innsetninguna.';
COMMENT ON COLUMN public.model_metrics_scalar.never_sum_with IS
  'Speglar extra.never_sum_with úr public.model_metrics. Þunn jaðarmæling '
  '(fresh_edge, n=87) má aldrei leggjast við aðaltöluna né birtast sem hún.';

-- ---------------------------------------------------------------------
-- RLS + heimildir — í SÖMU migration og taflan (CLAUDE.md-reglan).
-- SJÁLFGEFIÐ: DEFAULT-DENY. Þessi tafla er ÞJÓNUSTULIND pakkasmiðsins,
-- ekki síðugagn. Ef borðið ákveður að /markadur/modelstada eigi að lesa
-- hana beint þarf public_read-stefnuna hér að neðan — hún er VILJANDI
-- í athugasemd og má ekki afkommenta án ákvörðunar.
-- ---------------------------------------------------------------------
ALTER TABLE public.model_metrics_scalar ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.model_metrics_scalar FROM anon, authenticated;
-- Engin stefna skilgreind => default-deny fyrir anon + authenticated.
-- service_role fer framhjá RLS og skrifar/les eins og áður.

-- OPINN LESTUR — AÐEINS EF BORÐIÐ VELUR ÞAÐ:
-- GRANT SELECT ON public.model_metrics_scalar TO anon, authenticated;
-- CREATE POLICY public_read ON public.model_metrics_scalar
--   FOR SELECT TO anon, authenticated USING (true);

COMMIT;

-- PostgREST sér hvorki nýja töflu né nýtt RPC fyrr en skemað er endurlesið.
-- Án þessa svarar REST-leiðin eins og taflan sé ekki til, þótt SQL virki.
NOTIFY pgrst, 'reload schema';
