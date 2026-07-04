-- COMP-FLIP skref 1: comps_v2 toflur (COMPS_V2.md §7 lidur 1). Additive, reversible.
-- Live public.comps_index OSNERT. RLS + public_read fra degi eitt a ollum fjorum -
-- ENGIN tafla faedist exposed ne writable fyrir anon/authenticated (staging-lexian).
-- Rollback: app/scripts/comps_v2_schema_rollback.sql (skrifad FYRIR apply).

-- 1. comps_index_v2: per-comp audit-radir (1.081.901 radir vaentanlegar).
--    Speglar live comps_index conventions: PK (fastnum, rank), FK fastnum -> properties.
CREATE TABLE public.comps_index_v2 (
    fastnum          bigint      NOT NULL,
    rank             smallint    NOT NULL,
    set_role         text        NOT NULL CHECK (set_role IN ('comp', 'naestu_solur')),
    stop_tier        text        NOT NULL CHECK (stop_tier IN ('S0', 'S1p', 'S2p', 'S3')),
    comp_fastnum     bigint      NOT NULL,
    faerslunumer     bigint,
    sale_date        date        NOT NULL,
    price_nominal_kr bigint      NOT NULL,
    idx_factor       numeric     NOT NULL,
    idx_level_used   text        NOT NULL CHECK (idx_level_used IN ('cell', 'family', 'national', 'cpi')),
    idx_anchor_q     text        NOT NULL,
    idx_provisional  boolean     NOT NULL,
    price_adj_kr     bigint      NOT NULL,
    similarity       numeric,            -- NULL a naestu_solur rodum
    km               numeric     NOT NULL,
    kv_ratio         numeric,
    over_boundary    boolean     NOT NULL,
    comp_einflm      numeric,
    comp_byggar      numeric,
    CONSTRAINT comps_index_v2_pkey PRIMARY KEY (fastnum, rank),
    CONSTRAINT comps_index_v2_fastnum_fkey FOREIGN KEY (fastnum)
        REFERENCES public.properties (fastnum) ON DELETE CASCADE
);

-- 2. valuation_tiers: per-eign threp + flogg + prior-akkeri + T5-matsgrunnur (167.503).
CREATE TABLE public.valuation_tiers (
    fastnum               bigint   NOT NULL,
    canonical_code        text     NOT NULL,
    region_tier           text     NOT NULL,
    tier                  text     NOT NULL CHECK (tier IN ('T1', 'T2', 'T3', 'T4', 'T5')),
    tier_ruleset_version  text     NOT NULL,
    stop_tier             text     NOT NULL CHECK (stop_tier IN ('S0', 'S1p', 'S2p', 'S3', 'NONE', 'DATagap')),
    n_comps               integer  NOT NULL,
    n_shown               smallint NOT NULL,
    n_svaedi              integer  NOT NULL,
    s3_only_set           boolean  NOT NULL,
    comp_wmedian_kr       bigint,          -- NULL thegar ekkert midgildi (<K_min)
    d_log                 double precision,
    cell_med_d            double precision,
    cell_sd_d             double precision,
    cell_n_d              integer,
    flag_divergence       boolean  NOT NULL,
    idx_level_used        text     NOT NULL CHECK (idx_level_used IN ('cell', 'family', 'national', 'cpi')),
    idx_anchor_q          text     NOT NULL,
    has_prior_tier        boolean  NOT NULL,
    pred_mean_at_build_kr bigint,          -- snapshot vid build (audit; ekki live-spa)
    confidence_grade      text,
    size_m2               numeric,
    size_src              text,
    byggar                numeric,
    byggar_src            text,
    matsvaedi_numer       bigint,
    fasteignamat_kr       bigint,
    prior_date            date,
    prior_price_kr        bigint,
    prior_adj_kr          bigint,
    prior_idx_factor      numeric,
    prior_idx_provisional boolean,
    prior_idx_level       text,
    prior_anchor_q        text,
    prior_suspect         boolean,
    prior_age_years       numeric,
    prior_old_anchor_flag boolean,
    cell_ppm2_n           integer,
    cell_ppm2_p20         numeric,
    cell_ppm2_p50         numeric,
    cell_ppm2_p80         numeric,
    kv_med_cell48         numeric,
    kv_benchmark_kr       bigint,
    CONSTRAINT valuation_tiers_pkey PRIMARY KEY (fastnum),
    CONSTRAINT valuation_tiers_fastnum_fkey FOREIGN KEY (fastnum)
        REFERENCES public.properties (fastnum) ON DELETE CASCADE
);
CREATE INDEX idx_valuation_tiers_cell ON public.valuation_tiers (canonical_code, region_tier);
CREATE INDEX idx_valuation_tiers_tier ON public.valuation_tiers (tier);

-- 3. comps_drift_diagnostics: per-sella drift (tvilaga lag 1, spec Q5-aggregat).
--    as_of = byggingardagur (date) svo manadarleg vidbot appendist; at_q = verdlags-fjordungur.
CREATE TABLE public.comps_drift_diagnostics (
    canonical_code text     NOT NULL,
    region_tier    text     NOT NULL,
    as_of          date     NOT NULL,
    at_q           text     NOT NULL,
    n_d            integer  NOT NULL,
    med_d          double precision NOT NULL,
    sd_d           double precision,
    flag_rate_pct  numeric  NOT NULL,
    idx_level_used text     NOT NULL,
    idx_anchor_q   text     NOT NULL,
    script_version text     NOT NULL,
    CONSTRAINT comps_drift_diagnostics_pkey PRIMARY KEY (canonical_code, region_tier, as_of)
);

-- 4. comps_t5_basis: naestu-solur med hofnunarastaedum fyrir sub-K_min eignir (38.323).
CREATE TABLE public.comps_t5_basis (
    fastnum      bigint   NOT NULL,
    near_rank    smallint NOT NULL,
    near_fastnum bigint   NOT NULL,
    faerslunumer bigint,
    sale_date    date     NOT NULL,
    price_kr     bigint   NOT NULL,
    km           numeric  NOT NULL,
    reason       text     NOT NULL,
    CONSTRAINT comps_t5_basis_pkey PRIMARY KEY (fastnum, near_rank),
    CONSTRAINT comps_t5_basis_fastnum_fkey FOREIGN KEY (fastnum)
        REFERENCES public.properties (fastnum) ON DELETE CASCADE
);

-- RLS + policy + grants: public_read mynstrid (commit 1d61257) a ollum fjorum.
ALTER TABLE public.comps_index_v2          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.valuation_tiers         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comps_drift_diagnostics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comps_t5_basis          ENABLE ROW LEVEL SECURITY;

CREATE POLICY public_read ON public.comps_index_v2          FOR SELECT TO authenticated, anon USING (true);
CREATE POLICY public_read ON public.valuation_tiers         FOR SELECT TO authenticated, anon USING (true);
CREATE POLICY public_read ON public.comps_drift_diagnostics FOR SELECT TO authenticated, anon USING (true);
CREATE POLICY public_read ON public.comps_t5_basis          FOR SELECT TO authenticated, anon USING (true);

REVOKE ALL ON public.comps_index_v2, public.valuation_tiers,
              public.comps_drift_diagnostics, public.comps_t5_basis
  FROM anon, authenticated;
GRANT SELECT ON public.comps_index_v2, public.valuation_tiers,
                public.comps_drift_diagnostics, public.comps_t5_basis
  TO anon, authenticated;
GRANT ALL ON public.comps_index_v2, public.valuation_tiers,
             public.comps_drift_diagnostics, public.comps_t5_basis
  TO service_role;
