--
-- PostgreSQL database dump
--

\restrict 9NbLoVWi3BdqKTQw5P7Gfha4EbvXz2nyinko7afpW3uVgf1BzjFi4kXjOxGlp1T

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: search_properties_grouped(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.search_properties_grouped(term text) RETURNS TABLE(heimilisfang text, postnr integer, postheiti text, sveitarfelag text, n_units bigint, anchor_fastnum bigint, tegund_summary text)
    LANGUAGE plpgsql STABLE
    SET statement_timeout TO '10s'
    AS $_$
DECLARE
  pattern TEXT := lower(term) || '%';
BEGIN
  RETURN QUERY EXECUTE format(
    $sql$
      SELECT
        p.heimilisfang,
        p.postnr,
        p.postheiti,
        p.sveitarfelag,
        COUNT(*) AS n_units,
        MIN(p.fastnum) AS anchor_fastnum,
        STRING_AGG(DISTINCT p.tegund_raw, ', ' ORDER BY p.tegund_raw) AS tegund_summary
      FROM properties p
      WHERE p.is_residential = TRUE
        AND (
          lower(p.heimilisfang) LIKE %1$L
          OR lower(p.postheiti)  LIKE %1$L
        )
      GROUP BY p.heimilisfang, p.postnr, p.postheiti, p.sveitarfelag
      ORDER BY p.heimilisfang, p.postnr
      LIMIT 15
    $sql$,
    pattern
  );
END;
$_$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ats_dashboard_monthly_heat; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ats_dashboard_monthly_heat (
    canonical_code text NOT NULL,
    region_tier text NOT NULL,
    month text NOT NULL,
    n_month integer,
    median_month numeric,
    above_list_rate numeric,
    rolling_3mo_median numeric,
    rolling_12mo_mean numeric,
    rolling_12mo_sd numeric,
    z_3v12 numeric,
    heat_bucket text
);


--
-- Name: ats_lookup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ats_lookup (
    id integer NOT NULL,
    canonical_code text,
    region_tier text,
    heat_bucket text,
    n_pairs numeric,
    median_log_ratio numeric,
    dispersion_sd numeric,
    dispersion_mad numeric,
    above_list_rate numeric,
    n_quarters_pooled numeric,
    data_quality text,
    p33 numeric,
    p67 numeric,
    median_overall numeric,
    n_qtrs_stable integer
);


--
-- Name: ats_lookup_by_quarter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ats_lookup_by_quarter (
    canonical_code text NOT NULL,
    region_tier text NOT NULL,
    quarter text NOT NULL,
    n_pairs integer,
    median_log_ratio numeric,
    dispersion_sd numeric,
    dispersion_mad numeric,
    above_list_rate numeric,
    heat_bucket text,
    data_quality text,
    p33 numeric,
    p67 numeric,
    n_qtrs_stable integer
);


--
-- Name: ats_lookup_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ats_lookup_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ats_lookup_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ats_lookup_id_seq OWNED BY public.ats_lookup.id;


--
-- Name: comps_index; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comps_index (
    fastnum bigint NOT NULL,
    rank smallint NOT NULL,
    comp_fastnum bigint NOT NULL,
    distance_score numeric,
    last_sale_date date,
    last_sale_price_real bigint
);


--
-- Name: feature_attributions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.feature_attributions (
    fastnum bigint NOT NULL,
    rank smallint NOT NULL,
    feature_name text,
    feature_value text,
    shap_log_contribution numeric,
    real_isk_impact bigint
);


--
-- Name: feature_attributions_iter3v2; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.feature_attributions_iter3v2 (
    fastnum bigint NOT NULL,
    rank smallint NOT NULL,
    feature_name text,
    feature_value text,
    shap_log_contribution numeric,
    real_isk_impact bigint
);


--
-- Name: last_listing_text; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.last_listing_text (
    fastnum bigint NOT NULL,
    sale_rank smallint NOT NULL,
    thinglyst_dagur date,
    augl_id text,
    lysing_plain text,
    scraped_at timestamp with time zone
);


--
-- Name: latest_regime_per_cell; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.latest_regime_per_cell AS
 SELECT DISTINCT ON (canonical_code, region_tier) canonical_code,
    region_tier,
    month,
    heat_bucket,
    above_list_rate,
    n_month,
    z_3v12
   FROM public.ats_dashboard_monthly_heat
  WHERE ((canonical_code = ANY (ARRAY['APT_FLOOR'::text, 'APT_STANDARD'::text, 'SFH_DETACHED'::text, 'ROW_HOUSE'::text])) AND (region_tier = ANY (ARRAY['RVK_core'::text, 'Capital_sub'::text, 'Country'::text])))
  ORDER BY canonical_code, region_tier, month DESC;


--
-- Name: llm_aggregates_quarterly; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_aggregates_quarterly (
    year integer NOT NULL,
    quarter smallint NOT NULL,
    period text NOT NULL,
    canonical_code text NOT NULL,
    region_tier text NOT NULL,
    mean_interior_condition_score numeric,
    n_listings_condition integer,
    pct_recently_renovated numeric,
    n_listings_renovation integer,
    pct_has_unregistered_space numeric,
    n_listings_unregistered integer,
    pct_apt_with_serlod numeric,
    n_listings_serlod integer,
    pct_framing_terse numeric,
    pct_framing_standard numeric,
    pct_framing_elaborate numeric,
    pct_framing_promotional numeric,
    n_listings_total integer,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: model_tracking_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_tracking_history (
    period text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    model_version text NOT NULL,
    calibration_version text,
    segment text,
    n_held integer,
    mape numeric,
    median_ape numeric,
    bias_log numeric,
    cov80 numeric,
    cov95 numeric,
    status_label text
);


--
-- Name: predictions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.predictions (
    fastnum bigint NOT NULL,
    real_pred_mean bigint,
    real_pred_median bigint,
    real_pred_lo80 bigint,
    real_pred_hi80 bigint,
    real_pred_lo95 bigint,
    real_pred_hi95 bigint,
    model_group text,
    segment text,
    model_version text,
    calibration_version text,
    predicted_at date
);


--
-- Name: predictions_iter3v2; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.predictions_iter3v2 (
    fastnum bigint NOT NULL,
    real_pred_mean bigint,
    real_pred_median bigint,
    real_pred_lo80 bigint,
    real_pred_hi80 bigint,
    real_pred_lo95 bigint,
    real_pred_hi95 bigint,
    model_group text,
    segment text,
    model_version text,
    calibration_version text,
    predicted_at date
);


--
-- Name: pro_users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pro_users (
    id uuid NOT NULL,
    email text NOT NULL,
    full_name text,
    role text,
    company text,
    invited_at timestamp with time zone DEFAULT now(),
    activated_at timestamp with time zone,
    logo_url text,
    CONSTRAINT pro_users_role_check CHECK ((role = ANY (ARRAY['banki'::text, 'fasteignasali'::text, 'admin'::text, 'test'::text])))
);


--
-- Name: properties; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.properties (
    fastnum bigint NOT NULL,
    heimilisfang text,
    husnr numeric,
    postnr integer,
    postheiti text,
    svfn numeric,
    sveitarfelag text,
    tegund_raw text,
    canonical_code text,
    unit_category text,
    unit_family text,
    is_residential boolean,
    is_summerhouse boolean,
    einflm numeric,
    lod_flm numeric,
    byggar numeric,
    fjherb numeric,
    fullbuid numeric,
    is_new_build boolean,
    is_main_unit boolean,
    lat double precision,
    lng double precision,
    matsvaedi_numer integer,
    matsvaedi_nafn text,
    matsvaedi_bucket text,
    region_tier text,
    fasteignamat numeric,
    fasteignamat_gildandi numeric,
    augl_id_latest numeric,
    list_price_latest numeric,
    lysing_truncated text,
    scraped_at_latest timestamp with time zone,
    first_photo_url text,
    photo_urls_json jsonb,
    n_photos integer,
    effective_date_latest date,
    brunabotamat numeric,
    lhlmat numeric,
    fasteignamat_naesta_ar numeric,
    byggingarstig text,
    skodags date,
    gerd text,
    matsstig text,
    landeign_nr text,
    matseiningar jsonb,
    tengd_stadfang_nr jsonb,
    deregistered boolean DEFAULT false
);


--
-- Name: COLUMN properties.brunabotamat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.brunabotamat IS 'HMS endurbyggingarmat (rebuild / fire-insurance valuation), independent of market price. Same unit as fasteignamat (thousand kr).';


--
-- Name: COLUMN properties.lhlmat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.lhlmat IS 'Ratio 0..1 of land share of fasteignamat. NULL for non-residential or unset.';


--
-- Name: COLUMN properties.fasteignamat_naesta_ar; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.fasteignamat_naesta_ar IS 'HMS next-year fasteignamat forecast (kept in same unit as fasteignamat). Published in June each year.';


--
-- Name: COLUMN properties.byggingarstig; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.byggingarstig IS 'HMS construction stage code: B0/B1/B2/B3/B4. B4 = Fullbúið. NULL = no building or unset.';


--
-- Name: COLUMN properties.skodags; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.skodags IS 'Date of last on-site HMS inspection. NULL if never inspected.';


--
-- Name: COLUMN properties.gerd; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.gerd IS 'HMS internal sub-classification code (per-matseining, top-level summary).';


--
-- Name: COLUMN properties.matsstig; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.matsstig IS 'HMS assessment quality stage code.';


--
-- Name: COLUMN properties.landeign_nr; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.landeign_nr IS 'HMS land-parcel ID. Groups multiple fastnums sharing a lot (e.g., apartments in same building).';


--
-- Name: COLUMN properties.matseiningar; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.matseiningar IS 'JSONB array of sub-units (matseiningar). Each entry: { merking, einflm, byggingarar, byggingarstig, gerd, matsstig, brunabotamat, fasteignamat, notkun_kodi, notkun_texti, texti, skodags }.';


--
-- Name: COLUMN properties.tengd_stadfang_nr; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.tengd_stadfang_nr IS 'JSONB array of related staðfang IDs cross-referenced from HMS.';


--
-- Name: COLUMN properties.deregistered; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.properties.deregistered IS 'TRUE if HMS no longer recognises this fastnum (ghost handling). Default false. Set TRUE by Phase D for the 97 known ghosts.';


--
-- Name: regime_per_cell_monthly; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.regime_per_cell_monthly AS
 SELECT m.canonical_code,
    m.region_tier,
    m.month,
    m.n_month,
    m.median_month,
    m.above_list_rate,
    m.z_3v12,
    m.heat_bucket AS raw_regime,
        CASE
            WHEN (m.z_3v12 IS NULL) THEN NULL::text
            WHEN (m.z_3v12 > 0.5) THEN 'hot'::text
            WHEN (m.z_3v12 < '-0.5'::numeric) THEN 'cold'::text
            ELSE 'neutral'::text
        END AS smoothed_regime,
    q.heat_bucket AS quarterly_regime,
    q.n_pairs AS quarterly_n_pairs,
    q.quarter AS quarterly_period,
    q.data_quality AS quarterly_data_quality,
        CASE
            WHEN ((m.n_month >= 50) AND (m.z_3v12 IS NOT NULL)) THEN
            CASE
                WHEN (m.z_3v12 > 0.5) THEN 'hot'::text
                WHEN (m.z_3v12 < '-0.5'::numeric) THEN 'cold'::text
                ELSE 'neutral'::text
            END
            ELSE q.heat_bucket
        END AS display_regime,
        CASE
            WHEN ((m.n_month >= 50) AND (m.z_3v12 IS NOT NULL)) THEN 'smoothed_monthly'::text
            ELSE 'quarterly_fallback'::text
        END AS regime_source
   FROM (public.ats_dashboard_monthly_heat m
     LEFT JOIN public.ats_lookup_by_quarter q ON (((q.canonical_code = m.canonical_code) AND (q.region_tier = m.region_tier) AND (q.quarter = ((((EXTRACT(year FROM to_date(m.month, 'YYYY-MM'::text)))::integer)::text || 'Q'::text) || ((EXTRACT(quarter FROM to_date(m.month, 'YYYY-MM'::text)))::integer)::text)))));


--
-- Name: repeat_sale_index; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.repeat_sale_index (
    canonical_code text NOT NULL,
    region_tier text NOT NULL,
    year integer NOT NULL,
    quarter smallint NOT NULL,
    period text,
    index_value_nominal numeric,
    log_index_nominal numeric,
    std_error_nominal numeric,
    index_value_real numeric,
    log_index_real numeric,
    std_error_real numeric,
    n_pairs_in_period integer,
    cell_n_pairs integer,
    insufficient_sample boolean,
    data_quality text
);


--
-- Name: repeat_sale_index_by_segment; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.repeat_sale_index_by_segment AS
 SELECT canonical_code,
    year,
    quarter,
    period,
    (sum((index_value_real * (n_pairs_in_period)::numeric)) / (NULLIF(sum(n_pairs_in_period), 0))::numeric) AS index_real,
    (sum((index_value_nominal * (n_pairs_in_period)::numeric)) / (NULLIF(sum(n_pairs_in_period), 0))::numeric) AS index_nominal,
    sum(n_pairs_in_period) AS n_pairs
   FROM public.repeat_sale_index
  WHERE ((canonical_code = ANY (ARRAY['APT_STANDARD'::text, 'SFH_DETACHED'::text, 'ROW_HOUSE'::text])) AND (region_tier = ANY (ARRAY['RVK_core'::text, 'Capital_sub'::text, 'Country'::text])) AND (insufficient_sample = false))
  GROUP BY canonical_code, year, quarter, period;


--
-- Name: repeat_sale_index_main_pooled; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.repeat_sale_index_main_pooled AS
 SELECT year,
    quarter,
    period,
    (sum((index_value_real * (n_pairs_in_period)::numeric)) / (NULLIF(sum(n_pairs_in_period), 0))::numeric) AS index_real,
    (sum((index_value_nominal * (n_pairs_in_period)::numeric)) / (NULLIF(sum(n_pairs_in_period), 0))::numeric) AS index_nominal,
    sum(n_pairs_in_period) AS n_pairs
   FROM public.repeat_sale_index
  WHERE ((canonical_code = ANY (ARRAY['APT_FLOOR'::text, 'APT_STANDARD'::text, 'SFH_DETACHED'::text, 'ROW_HOUSE'::text])) AND (region_tier = ANY (ARRAY['RVK_core'::text, 'Capital_sub'::text, 'Country'::text])) AND (insufficient_sample = false))
  GROUP BY year, quarter, period;


--
-- Name: sales_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sales_history (
    id integer NOT NULL,
    fastnum bigint NOT NULL,
    thinglystdags date,
    kaupverd_nominal bigint,
    kaupverd_real bigint,
    einflm_at_sale numeric,
    byggar_at_sale numeric,
    onothaefur smallint
);


--
-- Name: sales_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sales_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sales_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sales_history_id_seq OWNED BY public.sales_history.id;


--
-- Name: saved_properties; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.saved_properties (
    user_id uuid NOT NULL,
    fastnum bigint NOT NULL,
    saved_at timestamp with time zone DEFAULT now(),
    notes text
);


--
-- Name: saved_searches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.saved_searches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    name text,
    criteria_json jsonb,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: saved_valuations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.saved_valuations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    fastnum bigint NOT NULL,
    valuation_type text,
    baseline_mean numeric,
    adjusted_mean numeric,
    answers_json jsonb,
    adjustments_json jsonb,
    model_version text DEFAULT 'iter4_conformal_v1'::text,
    created_at timestamp with time zone DEFAULT now(),
    notes text,
    CONSTRAINT saved_valuations_valuation_type_check CHECK ((valuation_type = ANY (ARRAY['baseline'::text, 'adjusted'::text])))
);


--
-- Name: ats_lookup id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ats_lookup ALTER COLUMN id SET DEFAULT nextval('public.ats_lookup_id_seq'::regclass);


--
-- Name: sales_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_history ALTER COLUMN id SET DEFAULT nextval('public.sales_history_id_seq'::regclass);


--
-- Name: ats_dashboard_monthly_heat ats_dashboard_monthly_heat_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ats_dashboard_monthly_heat
    ADD CONSTRAINT ats_dashboard_monthly_heat_pkey PRIMARY KEY (canonical_code, region_tier, month);


--
-- Name: ats_lookup_by_quarter ats_lookup_by_quarter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ats_lookup_by_quarter
    ADD CONSTRAINT ats_lookup_by_quarter_pkey PRIMARY KEY (canonical_code, region_tier, quarter);


--
-- Name: ats_lookup ats_lookup_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ats_lookup
    ADD CONSTRAINT ats_lookup_pkey PRIMARY KEY (id);


--
-- Name: comps_index comps_index_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comps_index
    ADD CONSTRAINT comps_index_pkey PRIMARY KEY (fastnum, rank);


--
-- Name: feature_attributions_iter3v2 feature_attributions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feature_attributions_iter3v2
    ADD CONSTRAINT feature_attributions_pkey PRIMARY KEY (fastnum, rank);


--
-- Name: feature_attributions feature_attributions_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feature_attributions
    ADD CONSTRAINT feature_attributions_pkey1 PRIMARY KEY (fastnum, rank);


--
-- Name: last_listing_text last_listing_text_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.last_listing_text
    ADD CONSTRAINT last_listing_text_pkey PRIMARY KEY (fastnum, sale_rank);


--
-- Name: llm_aggregates_quarterly llm_aggregates_quarterly_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_aggregates_quarterly
    ADD CONSTRAINT llm_aggregates_quarterly_pkey PRIMARY KEY (year, quarter, canonical_code, region_tier);


--
-- Name: predictions_iter3v2 predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions_iter3v2
    ADD CONSTRAINT predictions_pkey PRIMARY KEY (fastnum);


--
-- Name: predictions predictions_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_pkey1 PRIMARY KEY (fastnum);


--
-- Name: pro_users pro_users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pro_users
    ADD CONSTRAINT pro_users_email_key UNIQUE (email);


--
-- Name: pro_users pro_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pro_users
    ADD CONSTRAINT pro_users_pkey PRIMARY KEY (id);


--
-- Name: properties properties_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.properties
    ADD CONSTRAINT properties_pkey PRIMARY KEY (fastnum);


--
-- Name: repeat_sale_index repeat_sale_index_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.repeat_sale_index
    ADD CONSTRAINT repeat_sale_index_pkey PRIMARY KEY (canonical_code, region_tier, year, quarter);


--
-- Name: sales_history sales_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_history
    ADD CONSTRAINT sales_history_pkey PRIMARY KEY (id);


--
-- Name: saved_properties saved_properties_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_properties
    ADD CONSTRAINT saved_properties_pkey PRIMARY KEY (user_id, fastnum);


--
-- Name: saved_searches saved_searches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_searches
    ADD CONSTRAINT saved_searches_pkey PRIMARY KEY (id);


--
-- Name: saved_valuations saved_valuations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_valuations
    ADD CONSTRAINT saved_valuations_pkey PRIMARY KEY (id);


--
-- Name: idx_ats_by_qtr_quarter; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ats_by_qtr_quarter ON public.ats_lookup_by_quarter USING btree (quarter);


--
-- Name: idx_ats_by_qtr_segreg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ats_by_qtr_segreg ON public.ats_lookup_by_quarter USING btree (canonical_code, region_tier);


--
-- Name: idx_ats_lookup_segreg_bucket; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_ats_lookup_segreg_bucket ON public.ats_lookup USING btree (canonical_code, region_tier, heat_bucket) WHERE (heat_bucket IS NOT NULL);


--
-- Name: idx_ats_monthly_month; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ats_monthly_month ON public.ats_dashboard_monthly_heat USING btree (month);


--
-- Name: idx_ats_monthly_segreg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ats_monthly_segreg ON public.ats_dashboard_monthly_heat USING btree (canonical_code, region_tier);


--
-- Name: idx_attr_feature; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_attr_feature ON public.feature_attributions USING btree (feature_name);


--
-- Name: idx_attr_iter3v2_feature; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_attr_iter3v2_feature ON public.feature_attributions_iter3v2 USING btree (feature_name);


--
-- Name: idx_last_listing_fastnum; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_last_listing_fastnum ON public.last_listing_text USING btree (fastnum);


--
-- Name: idx_llm_agg_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_agg_period ON public.llm_aggregates_quarterly USING btree (period);


--
-- Name: idx_llm_agg_segment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_llm_agg_segment ON public.llm_aggregates_quarterly USING btree (canonical_code);


--
-- Name: idx_model_tracking_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_model_tracking_period ON public.model_tracking_history USING btree (period);


--
-- Name: idx_predictions_iter3v2_segment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_predictions_iter3v2_segment ON public.predictions_iter3v2 USING btree (segment);


--
-- Name: idx_predictions_segment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_predictions_segment ON public.predictions USING btree (segment);


--
-- Name: idx_properties_canonical; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_properties_canonical ON public.properties USING btree (canonical_code);


--
-- Name: idx_properties_heimilisfang_lower_prefix; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_properties_heimilisfang_lower_prefix ON public.properties USING btree (lower(heimilisfang) text_pattern_ops);


--
-- Name: idx_properties_heimilisfang_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_properties_heimilisfang_trgm ON public.properties USING gin (heimilisfang public.gin_trgm_ops);


--
-- Name: idx_properties_latlng; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_properties_latlng ON public.properties USING btree (lat, lng) WHERE ((lat IS NOT NULL) AND (lng IS NOT NULL));


--
-- Name: idx_properties_postheiti_lower_prefix; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_properties_postheiti_lower_prefix ON public.properties USING btree (lower(postheiti) text_pattern_ops);


--
-- Name: idx_properties_postnr; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_properties_postnr ON public.properties USING btree (postnr);


--
-- Name: idx_properties_region; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_properties_region ON public.properties USING btree (region_tier);


--
-- Name: idx_properties_residential; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_properties_residential ON public.properties USING btree (is_residential) WHERE (is_residential = true);


--
-- Name: idx_properties_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_properties_search ON public.properties USING gin (to_tsvector('simple'::regconfig, ((((COALESCE(heimilisfang, ''::text) || ' '::text) || COALESCE(postheiti, ''::text)) || ' '::text) || COALESCE((fastnum)::text, ''::text))));


--
-- Name: idx_sales_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sales_date ON public.sales_history USING btree (thinglystdags);


--
-- Name: idx_sales_fastnum; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sales_fastnum ON public.sales_history USING btree (fastnum);


--
-- Name: idx_sv_fastnum; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sv_fastnum ON public.saved_valuations USING btree (fastnum);


--
-- Name: idx_sv_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sv_user ON public.saved_valuations USING btree (user_id);


--
-- Name: model_tracking_history_pkey; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX model_tracking_history_pkey ON public.model_tracking_history USING btree (period, model_version, COALESCE(segment, '__OVERALL__'::text));


--
-- Name: comps_index comps_index_fastnum_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comps_index
    ADD CONSTRAINT comps_index_fastnum_fkey FOREIGN KEY (fastnum) REFERENCES public.properties(fastnum) ON DELETE CASCADE;


--
-- Name: feature_attributions_iter3v2 feature_attributions_fastnum_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feature_attributions_iter3v2
    ADD CONSTRAINT feature_attributions_fastnum_fkey FOREIGN KEY (fastnum) REFERENCES public.properties(fastnum) ON DELETE CASCADE;


--
-- Name: feature_attributions feature_attributions_fastnum_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feature_attributions
    ADD CONSTRAINT feature_attributions_fastnum_fkey1 FOREIGN KEY (fastnum) REFERENCES public.properties(fastnum) ON DELETE CASCADE;


--
-- Name: predictions_iter3v2 predictions_fastnum_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions_iter3v2
    ADD CONSTRAINT predictions_fastnum_fkey FOREIGN KEY (fastnum) REFERENCES public.properties(fastnum) ON DELETE CASCADE;


--
-- Name: predictions predictions_fastnum_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_fastnum_fkey1 FOREIGN KEY (fastnum) REFERENCES public.properties(fastnum) ON DELETE CASCADE;


--
-- Name: pro_users pro_users_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pro_users
    ADD CONSTRAINT pro_users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: sales_history sales_history_fastnum_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales_history
    ADD CONSTRAINT sales_history_fastnum_fkey FOREIGN KEY (fastnum) REFERENCES public.properties(fastnum) ON DELETE CASCADE;


--
-- Name: saved_properties saved_properties_fastnum_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_properties
    ADD CONSTRAINT saved_properties_fastnum_fkey FOREIGN KEY (fastnum) REFERENCES public.properties(fastnum) ON DELETE CASCADE;


--
-- Name: saved_properties saved_properties_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_properties
    ADD CONSTRAINT saved_properties_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: saved_searches saved_searches_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_searches
    ADD CONSTRAINT saved_searches_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: saved_valuations saved_valuations_fastnum_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_valuations
    ADD CONSTRAINT saved_valuations_fastnum_fkey FOREIGN KEY (fastnum) REFERENCES public.properties(fastnum) ON DELETE CASCADE;


--
-- Name: saved_valuations saved_valuations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.saved_valuations
    ADD CONSTRAINT saved_valuations_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: ats_dashboard_monthly_heat; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.ats_dashboard_monthly_heat ENABLE ROW LEVEL SECURITY;

--
-- Name: ats_lookup; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.ats_lookup ENABLE ROW LEVEL SECURITY;

--
-- Name: ats_lookup_by_quarter; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.ats_lookup_by_quarter ENABLE ROW LEVEL SECURITY;

--
-- Name: comps_index; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.comps_index ENABLE ROW LEVEL SECURITY;

--
-- Name: feature_attributions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.feature_attributions ENABLE ROW LEVEL SECURITY;

--
-- Name: feature_attributions_iter3v2; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.feature_attributions_iter3v2 ENABLE ROW LEVEL SECURITY;

--
-- Name: last_listing_text; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.last_listing_text ENABLE ROW LEVEL SECURITY;

--
-- Name: llm_aggregates_quarterly; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.llm_aggregates_quarterly ENABLE ROW LEVEL SECURITY;

--
-- Name: model_tracking_history; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.model_tracking_history ENABLE ROW LEVEL SECURITY;

--
-- Name: saved_properties own saves; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "own saves" ON public.saved_properties USING ((auth.uid() = user_id));


--
-- Name: saved_searches own searches; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "own searches" ON public.saved_searches USING ((auth.uid() = user_id));


--
-- Name: saved_valuations own valuations; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "own valuations" ON public.saved_valuations USING ((auth.uid() = user_id));


--
-- Name: predictions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;

--
-- Name: predictions_iter3v2; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.predictions_iter3v2 ENABLE ROW LEVEL SECURITY;

--
-- Name: pro_users; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.pro_users ENABLE ROW LEVEL SECURITY;

--
-- Name: properties; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.properties ENABLE ROW LEVEL SECURITY;

--
-- Name: ats_dashboard_monthly_heat public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.ats_dashboard_monthly_heat FOR SELECT TO authenticated, anon USING (true);


--
-- Name: ats_lookup public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.ats_lookup FOR SELECT TO authenticated, anon USING (true);


--
-- Name: ats_lookup_by_quarter public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.ats_lookup_by_quarter FOR SELECT TO authenticated, anon USING (true);


--
-- Name: comps_index public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.comps_index FOR SELECT TO authenticated, anon USING (true);


--
-- Name: feature_attributions public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.feature_attributions FOR SELECT TO authenticated, anon USING (true);


--
-- Name: feature_attributions_iter3v2 public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.feature_attributions_iter3v2 FOR SELECT TO authenticated, anon USING (true);


--
-- Name: last_listing_text public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.last_listing_text FOR SELECT TO authenticated, anon USING (true);


--
-- Name: llm_aggregates_quarterly public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.llm_aggregates_quarterly FOR SELECT TO authenticated, anon USING (true);


--
-- Name: model_tracking_history public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.model_tracking_history FOR SELECT TO authenticated, anon USING (true);


--
-- Name: predictions public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.predictions FOR SELECT TO authenticated, anon USING (true);


--
-- Name: predictions_iter3v2 public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.predictions_iter3v2 FOR SELECT TO authenticated, anon USING (true);


--
-- Name: properties public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.properties FOR SELECT TO authenticated, anon USING (true);


--
-- Name: repeat_sale_index public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.repeat_sale_index FOR SELECT TO authenticated, anon USING (true);


--
-- Name: sales_history public_read; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY public_read ON public.sales_history FOR SELECT TO authenticated, anon USING (true);


--
-- Name: pro_users read own; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY "read own" ON public.pro_users FOR SELECT USING ((auth.uid() = id));


--
-- Name: repeat_sale_index; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.repeat_sale_index ENABLE ROW LEVEL SECURITY;

--
-- Name: sales_history; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.sales_history ENABLE ROW LEVEL SECURITY;

--
-- Name: saved_properties; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.saved_properties ENABLE ROW LEVEL SECURITY;

--
-- Name: saved_searches; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.saved_searches ENABLE ROW LEVEL SECURITY;

--
-- Name: saved_valuations; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.saved_valuations ENABLE ROW LEVEL SECURITY;

--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: -
--

GRANT USAGE ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO service_role;


--
-- Name: FUNCTION search_properties_grouped(term text); Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON FUNCTION public.search_properties_grouped(term text) TO anon;
GRANT ALL ON FUNCTION public.search_properties_grouped(term text) TO authenticated;
GRANT ALL ON FUNCTION public.search_properties_grouped(term text) TO service_role;


--
-- Name: TABLE ats_dashboard_monthly_heat; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.ats_dashboard_monthly_heat TO service_role;
GRANT SELECT ON TABLE public.ats_dashboard_monthly_heat TO anon;
GRANT SELECT ON TABLE public.ats_dashboard_monthly_heat TO authenticated;


--
-- Name: TABLE ats_lookup; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.ats_lookup TO service_role;
GRANT SELECT ON TABLE public.ats_lookup TO anon;
GRANT SELECT ON TABLE public.ats_lookup TO authenticated;


--
-- Name: TABLE ats_lookup_by_quarter; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.ats_lookup_by_quarter TO service_role;
GRANT SELECT ON TABLE public.ats_lookup_by_quarter TO anon;
GRANT SELECT ON TABLE public.ats_lookup_by_quarter TO authenticated;


--
-- Name: SEQUENCE ats_lookup_id_seq; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON SEQUENCE public.ats_lookup_id_seq TO anon;
GRANT ALL ON SEQUENCE public.ats_lookup_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.ats_lookup_id_seq TO service_role;


--
-- Name: TABLE comps_index; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.comps_index TO service_role;
GRANT SELECT ON TABLE public.comps_index TO anon;
GRANT SELECT ON TABLE public.comps_index TO authenticated;


--
-- Name: TABLE feature_attributions; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.feature_attributions TO service_role;
GRANT SELECT ON TABLE public.feature_attributions TO anon;
GRANT SELECT ON TABLE public.feature_attributions TO authenticated;


--
-- Name: TABLE feature_attributions_iter3v2; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.feature_attributions_iter3v2 TO service_role;
GRANT SELECT ON TABLE public.feature_attributions_iter3v2 TO anon;
GRANT SELECT ON TABLE public.feature_attributions_iter3v2 TO authenticated;


--
-- Name: TABLE last_listing_text; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.last_listing_text TO service_role;
GRANT SELECT ON TABLE public.last_listing_text TO anon;
GRANT SELECT ON TABLE public.last_listing_text TO authenticated;


--
-- Name: TABLE latest_regime_per_cell; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,REFERENCES,TRIGGER,MAINTAIN ON TABLE public.latest_regime_per_cell TO anon;
GRANT SELECT,REFERENCES,TRIGGER,MAINTAIN ON TABLE public.latest_regime_per_cell TO authenticated;
GRANT ALL ON TABLE public.latest_regime_per_cell TO service_role;


--
-- Name: TABLE llm_aggregates_quarterly; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.llm_aggregates_quarterly TO service_role;
GRANT SELECT ON TABLE public.llm_aggregates_quarterly TO anon;
GRANT SELECT ON TABLE public.llm_aggregates_quarterly TO authenticated;


--
-- Name: TABLE model_tracking_history; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.model_tracking_history TO service_role;
GRANT SELECT ON TABLE public.model_tracking_history TO anon;
GRANT SELECT ON TABLE public.model_tracking_history TO authenticated;


--
-- Name: TABLE predictions; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.predictions TO service_role;
GRANT SELECT ON TABLE public.predictions TO anon;
GRANT SELECT ON TABLE public.predictions TO authenticated;


--
-- Name: TABLE predictions_iter3v2; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.predictions_iter3v2 TO service_role;
GRANT SELECT ON TABLE public.predictions_iter3v2 TO anon;
GRANT SELECT ON TABLE public.predictions_iter3v2 TO authenticated;


--
-- Name: TABLE pro_users; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.pro_users TO authenticated;
GRANT ALL ON TABLE public.pro_users TO service_role;


--
-- Name: TABLE properties; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.properties TO service_role;
GRANT SELECT ON TABLE public.properties TO anon;
GRANT SELECT ON TABLE public.properties TO authenticated;


--
-- Name: TABLE regime_per_cell_monthly; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,REFERENCES,TRIGGER,MAINTAIN ON TABLE public.regime_per_cell_monthly TO anon;
GRANT SELECT,REFERENCES,TRIGGER,MAINTAIN ON TABLE public.regime_per_cell_monthly TO authenticated;
GRANT ALL ON TABLE public.regime_per_cell_monthly TO service_role;


--
-- Name: TABLE repeat_sale_index; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.repeat_sale_index TO service_role;
GRANT SELECT ON TABLE public.repeat_sale_index TO anon;
GRANT SELECT ON TABLE public.repeat_sale_index TO authenticated;


--
-- Name: TABLE repeat_sale_index_by_segment; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,REFERENCES,TRIGGER,MAINTAIN ON TABLE public.repeat_sale_index_by_segment TO anon;
GRANT SELECT,REFERENCES,TRIGGER,MAINTAIN ON TABLE public.repeat_sale_index_by_segment TO authenticated;
GRANT ALL ON TABLE public.repeat_sale_index_by_segment TO service_role;


--
-- Name: TABLE repeat_sale_index_main_pooled; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,REFERENCES,TRIGGER,MAINTAIN ON TABLE public.repeat_sale_index_main_pooled TO anon;
GRANT SELECT,REFERENCES,TRIGGER,MAINTAIN ON TABLE public.repeat_sale_index_main_pooled TO authenticated;
GRANT ALL ON TABLE public.repeat_sale_index_main_pooled TO service_role;


--
-- Name: TABLE sales_history; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.sales_history TO service_role;
GRANT SELECT ON TABLE public.sales_history TO anon;
GRANT SELECT ON TABLE public.sales_history TO authenticated;


--
-- Name: SEQUENCE sales_history_id_seq; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON SEQUENCE public.sales_history_id_seq TO anon;
GRANT ALL ON SEQUENCE public.sales_history_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.sales_history_id_seq TO service_role;


--
-- Name: TABLE saved_properties; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.saved_properties TO authenticated;
GRANT ALL ON TABLE public.saved_properties TO service_role;


--
-- Name: TABLE saved_searches; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.saved_searches TO authenticated;
GRANT ALL ON TABLE public.saved_searches TO service_role;


--
-- Name: TABLE saved_valuations; Type: ACL; Schema: public; Owner: -
--

GRANT ALL ON TABLE public.saved_valuations TO authenticated;
GRANT ALL ON TABLE public.saved_valuations TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON TABLES TO service_role;


--
-- PostgreSQL database dump complete
--

\unrestrict 9NbLoVWi3BdqKTQw5P7Gfha4EbvXz2nyinko7afpW3uVgf1BzjFi4kXjOxGlp1T

