-- cc284 FASI A — DRÖG, EKKI BEITT. Rollback skrifað á undan: 20261031_cc284a_anon_revoke_onotad_ROLLBACK.sql
--
-- Afturkallar réttindi anon/authenticated (og PUBLIC á dm-föllum) á hlutum sem
--   (1) enginn kóði í verdmat-ai (origin/main 22f0ef8) les með anon- eða session-klient, og
--   (2) fengu 0 köll á /rest/v1 í edge_logs 24.10–31.10.2026 (7 × 24 klst, jákvætt viðmið staðfest).
-- Allir hlutirnir eru í eigu postgres, svo REVOKE getur ekki þagað sem núllaðgerð (cc105-regla 3:
-- forathugun hér að neðan stöðvar migrationina ef svo er ekki).
--
-- Hlutir sem www LES sem anon (v_current_predictions, v_eign_myndir, vísitölusýnurnar o.fl.)
-- eru EKKI hér. Þeir fara í fasa B, sem krefst kóðabreytingar fyrst (sjá SKIL_CC284.md §3).

begin;
set local lock_timeout = '3s';
set local statement_timeout = '30s';

-- Forathugun: núverandi notandi verður að eiga hvern hlut (annars þegir REVOKE).
do $$
declare r text;
begin
  foreach r in array array[
    'public.ats_lookup_by_quarter','public.comps_drift_diagnostics','public.comps_index',
    'public.daudir_myndahyslar','public.dm_domar','public.dm_fasteignamal',
    'public.feature_attributions','public.feature_attributions_iter3v2',
    'public.valuation_tiers_thinflag_pre_cc152','public.v_ats_lookup_by_heat',
    'semantic.v_verdvakt_breytingar','semantic.v_verdvakt_nefnarar','semantic.v_verdvakt_nefnarar_stadir_v2',
    'public.ats_lookup','public.predictions']
  loop
    if not pg_has_role(current_user, (select relowner from pg_class where oid = r::regclass), 'member') then
      raise exception 'cc284a: % er ekki í eigu %, REVOKE myndi þegja', r, current_user;
    end if;
  end loop;
end $$;

-- 1. Töflur og sýnir sem enginn les um API (öll réttindi, líka skrif-réttindin á dm_* og thinflag)
revoke all on public.ats_lookup_by_quarter               from anon, authenticated;
revoke all on public.comps_drift_diagnostics             from anon, authenticated;
revoke all on public.comps_index                         from anon, authenticated;  -- v1, 243 MB, leyst af comps_index_v2
revoke all on public.daudir_myndahyslar                  from anon, authenticated;  -- lesin af v_eign_myndir (definer), óháð
revoke all on public.dm_domar                            from anon, authenticated;  -- anon bar arwdDxtm
revoke all on public.dm_fasteignamal                     from anon, authenticated;  -- anon bar arwdDxtm
revoke all on public.feature_attributions                from anon, authenticated;
revoke all on public.feature_attributions_iter3v2        from anon, authenticated;  -- úrelt, 127 MB, opin anon
revoke all on public.valuation_tiers_thinflag_pre_cc152  from anon, authenticated;  -- afrit, anon bar arwdDxtm
revoke all on public.v_ats_lookup_by_heat                from anon, authenticated;  -- security_invoker, 0 köll
revoke all on semantic.v_verdvakt_breytingar             from anon, authenticated;  -- v1, leyst af _v2
revoke all on semantic.v_verdvakt_nefnarar               from anon, authenticated;  -- v1, leyst af _v2
revoke all on semantic.v_verdvakt_nefnarar_stadir_v2     from anon, authenticated;  -- aðeins lesin af cc188-refresh (DSN)

-- 2. Dálkaréttindi: predictions er lesin af anon AÐEINS gegnum v_current_predictions (definer, keyrir
--    sem postgres), svo dálkaréttindin eru óþörf. ats_lookup er aðeins lesin um v_ats_lookup_by_heat (lokað í 1).
revoke select on public.predictions from anon, authenticated;
revoke select on public.ats_lookup  from anon, authenticated;

-- 3. dm-föllin (SECURITY INVOKER; skila [] til anon í dag því dm_* eru RLS án policy). PUBLIC líka.
revoke execute on function public.dm_leit(text, text, text, text, text, integer, text, integer, integer) from public, anon, authenticated;
revoke execute on function public.dm_leit_teljarar(text) from public, anon, authenticated;

-- Eftirathugun: ekkert af ofantöldu má lengur vera aðgengilegt anon eða authenticated.
do $$
declare r text; g text;
begin
  foreach g in array array['anon','authenticated'] loop
    foreach r in array array[
      'public.ats_lookup_by_quarter','public.comps_drift_diagnostics','public.comps_index',
      'public.daudir_myndahyslar','public.dm_domar','public.dm_fasteignamal',
      'public.feature_attributions','public.feature_attributions_iter3v2',
      'public.valuation_tiers_thinflag_pre_cc152','public.v_ats_lookup_by_heat',
      'semantic.v_verdvakt_breytingar','semantic.v_verdvakt_nefnarar','semantic.v_verdvakt_nefnarar_stadir_v2']
    loop
      if has_table_privilege(g, r, 'SELECT') or has_table_privilege(g, r, 'INSERT')
         or has_table_privilege(g, r, 'UPDATE') or has_table_privilege(g, r, 'DELETE') then
        raise exception 'cc284a: % ber enn réttindi á %', g, r;
      end if;
    end loop;
    if has_any_column_privilege(g, 'public.predictions', 'SELECT') or has_any_column_privilege(g, 'public.ats_lookup', 'SELECT') then
      raise exception 'cc284a: % ber enn dálkaréttindi á predictions/ats_lookup', g;
    end if;
    if has_function_privilege(g, 'public.dm_leit_teljarar(text)', 'EXECUTE') then
      raise exception 'cc284a: % getur enn keyrt dm_leit_teljarar', g;
    end if;
  end loop;
end $$;

commit;
notify pgrst, 'reload schema';
