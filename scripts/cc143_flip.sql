-- ============================================================================
-- cc143 FLIPP-STÆÐAN - prior_*-dálkar valuation_tiers á endurmerkta par-lagið.
-- BÍÐUR GO. Keyrist sem EIN atómísk transaction. Snapshot: valuation_tiers_pre_cc143.
-- Rás: psycopg2 (sessionin er read-only að sjálfgefnu -> SET TRANSACTION READ WRITE
--      verður að vera FYRSTA stæðan í transaction).
-- ============================================================================
begin;
set transaction read write;

-- --- 1. nýju flögg-/greiningardálkarnir (viðbætandi, engin gögn snert) --------
alter table public.valuation_tiers
  add column if not exists prior_anchor_lag_q        smallint,
  add column if not exists prior_anchor_stale_flag   boolean,
  add column if not exists prior_series_thin_flag    boolean,
  add column if not exists prior_level_fallback_flag boolean,
  add column if not exists prior_serie_n_pairs       integer,
  add column if not exists prior_serie_sd_dlog       numeric,
  add column if not exists prior_anchor_pairs        integer;

-- --- 2. eignir sem MISSA birt akkeri (skjal ber nú fleiri en eina eign) -------
--     1 röð 12.08: 2145072 (A-002013/2026 ber 46 eignir -> single_deed fellur).
update public.valuation_tiers v
   set prior_date = null, prior_price_kr = null, prior_adj_kr = null,
       prior_idx_factor = null, prior_idx_provisional = null, prior_idx_level = null,
       prior_anchor_q = null, prior_suspect = null, prior_age_years = null,
       prior_old_anchor_flag = null,
       prior_anchor_lag_q = null, prior_anchor_stale_flag = null,
       prior_series_thin_flag = null, prior_level_fallback_flag = null,
       prior_serie_n_pairs = null, prior_serie_sd_dlog = null, prior_anchor_pairs = null
 where v.prior_adj_kr is not null
   and not exists (select 1 from public.valuation_tiers_prior_staging_cc143 s
                    where s.fastnum = v.fastnum);

-- --- 3. prior_*-dálkarnir af staging (77.484 raðir, þ.a. 14 nýjar) -----------
update public.valuation_tiers v
   set prior_date                = s.prior_date,
       prior_price_kr            = s.prior_price_kr,
       prior_adj_kr              = s.prior_adj_kr,
       prior_idx_factor          = s.prior_idx_factor,
       prior_idx_provisional     = s.prior_idx_provisional,
       prior_idx_level           = s.prior_idx_level,
       prior_anchor_q            = s.prior_anchor_q,
       prior_suspect             = s.prior_suspect,
       prior_age_years           = s.prior_age_years,
       prior_old_anchor_flag     = s.prior_old_anchor_flag,
       prior_anchor_lag_q        = s.prior_anchor_lag_q,
       prior_anchor_stale_flag   = s.prior_anchor_stale_flag,
       prior_series_thin_flag    = s.prior_series_thin_flag,
       prior_level_fallback_flag = s.prior_level_fallback_flag,
       prior_serie_n_pairs       = s.prior_serie_n_pairs,
       prior_serie_sd_dlog       = s.prior_serie_sd_dlog,
       prior_anchor_pairs        = s.prior_anchor_pairs
  from public.valuation_tiers_prior_staging_cc143 s
 where v.fastnum = s.fastnum;

-- --- 4. POSTVERIFY i SOMU transaction - fellur allt ef eitthvad bregst -------
do $$
declare
  n_prior  int; n_snap int; chk_other text; chk_other_snap text; n_except int;
begin
  select count(*) into n_prior from public.valuation_tiers where prior_adj_kr is not null;
  if n_prior <> 77484 then
    raise exception 'POSTVERIFY FELLT: eignir m/akkeri = %, vaenting 77484', n_prior;
  end if;

  select count(*) into n_snap from public.valuation_tiers_pre_cc143;
  if n_snap <> (select count(*) from public.valuation_tiers) then
    raise exception 'POSTVERIFY FELLT: rowcount hreyfdist';
  end if;

  -- checksum a ODRUM dalkum skal vera ORDRETT sa sami og fyrir flipp
  select md5(string_agg(fastnum::text||':'||coalesce(tier,'')||':'
             ||coalesce(comp_wmedian_kr::text,'')||':'||coalesce(d_log::text,'')||':'
             ||coalesce(idx_anchor_q,'')||':'||coalesce(n_comps::text,''), ',' order by fastnum))
    into chk_other from public.valuation_tiers;
  select md5(string_agg(fastnum::text||':'||coalesce(tier,'')||':'
             ||coalesce(comp_wmedian_kr::text,'')||':'||coalesce(d_log::text,'')||':'
             ||coalesce(idx_anchor_q,'')||':'||coalesce(n_comps::text,''), ',' order by fastnum))
    into chk_other_snap from public.valuation_tiers_pre_cc143;
  if chk_other <> chk_other_snap then
    raise exception 'POSTVERIFY FELLT: ANNAD en prior_* hreyfdist (checksum % <> %)',
      chk_other, chk_other_snap;
  end if;
  -- vaentanlegt gildi 12.08: bc0d7061a300e8da072dc0914287ba29

  -- ekkert akkeri ma standa eftir ur gamla artifactinu
  select count(*) into n_except from public.valuation_tiers
   where prior_anchor_q = '2025Q4';
  if n_except > 0 then
    raise exception 'POSTVERIFY FELLT: % radir bera enn 2025Q4-akkeri', n_except;
  end if;

  raise notice 'POSTVERIFY PASS: n_prior=%, checksum ANNAD obreytt=%', n_prior, chk_other;
end $$;

commit;

-- ============================================================================
-- ROLLBACK (ef borðið kallar hann): prior_*-dálkarnir aftur af snapshot.
--   begin; set transaction read write;
--   update public.valuation_tiers v set
--     prior_date=p.prior_date, prior_price_kr=p.prior_price_kr,
--     prior_adj_kr=p.prior_adj_kr, prior_idx_factor=p.prior_idx_factor,
--     prior_idx_provisional=p.prior_idx_provisional, prior_idx_level=p.prior_idx_level,
--     prior_anchor_q=p.prior_anchor_q, prior_suspect=p.prior_suspect,
--     prior_age_years=p.prior_age_years, prior_old_anchor_flag=p.prior_old_anchor_flag,
--     prior_anchor_lag_q=null, prior_anchor_stale_flag=null,
--     prior_series_thin_flag=null, prior_level_fallback_flag=null,
--     prior_serie_n_pairs=null, prior_serie_sd_dlog=null, prior_anchor_pairs=null
--   from public.valuation_tiers_pre_cc143 p where v.fastnum=p.fastnum;
--   -- checksum prior fyrir cc143: 2b545c9969460295820221f50f86c3e0
--   commit;
-- ============================================================================
