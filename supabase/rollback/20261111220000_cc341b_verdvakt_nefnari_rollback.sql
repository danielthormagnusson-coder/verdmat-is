-- cc341 (b) ROLLBACK — skilar MV-unum þremur í skilgreininguna fyrir 20261111220000 (lesin lifandi 11.11).
begin;
set local lock_timeout = '5s';
set local statement_timeout = '600s';

create materialized view semantic.v_verdvakt_breytingar_v2_cc341ny as
WITH lst AS (
         SELECT l.listing_id,
            l.source,
            l.source_listing_id,
            l.fastnum,
            l.size_sqm,
            l.rooms,
            l.addr_text,
            l.byggar,
            l.status,
            l.first_seen_at,
            l.last_seen_at,
            l.price_amount,
            COALESCE(( SELECT ph.price_amount
                   FROM scraper.listing_price_history ph
                  WHERE ((ph.source = l.source) AND (ph.source_listing_id = l.source_listing_id) AND (ph.price_amount >= 1000000))
                  ORDER BY ph.id
                 LIMIT 1), l.price_amount) AS fyrsta_verd,
            ((l.addr_text ~* 'hlutdeild'::text) OR (l.lysing ~* 'hlutdeildarl[áa]n|hlutdeildarkaup'::text)) AS hlutd_texti,
            (NOT (EXISTS ( SELECT 1
                   FROM scraper.listing_lifecycle_events e
                  WHERE ((e.source = l.source) AND (e.source_listing_id = l.source_listing_id) AND (e.event_type = 'withdrawn_confirmed'::scraper.lifecycle_event_enum))))) AS an_terminal
           FROM scraper.listings l
          WHERE ((l.tenure = 'sale'::text) AND (l.category = 'residential'::text) AND (l.fastnum IS NOT NULL) AND (l.price_amount IS NOT NULL) AND (l.price_amount >= 1000000) AND (NOT COALESCE(l.is_price_on_request, false)))
        ), seq AS (
         SELECT lst.listing_id,
            lst.source,
            lst.source_listing_id,
            lst.fastnum,
            lst.size_sqm,
            lst.rooms,
            lst.addr_text,
            lst.byggar,
            lst.status,
            lst.first_seen_at,
            lst.last_seen_at,
            lst.price_amount,
            lst.fyrsta_verd,
            lst.hlutd_texti,
            lst.an_terminal,
            lag(lst.price_amount) OVER w AS prev_verd,
            lag(lst.last_seen_at) OVER w AS prev_sast,
            lag(lst.listing_id) OVER w AS prev_lid
           FROM lst
          WINDOW w AS (PARTITION BY lst.fastnum, lst.size_sqm, lst.rooms ORDER BY lst.last_seen_at, lst.listing_id)
        ), milli AS (
         SELECT seq.listing_id,
            'milli'::text AS teg,
            seq.prev_verd AS fyrra_verd,
            seq.prev_sast AS fyrra_sast,
            'sidast'::text AS fyrra_sast_teg,
            seq.fyrsta_verd AS nytt_verd,
            seq.first_seen_at AS nytt_sast,
            seq.prev_lid AS fyrri_listing_id,
            'endurbirting'::text AS dags_lind
           FROM seq
          WHERE ((seq.prev_verd IS NOT NULL) AND (seq.prev_sast < seq.first_seen_at) AND (seq.prev_verd <> seq.fyrsta_verd))
        ), ph AS (
         SELECT l.listing_id,
            ph.id,
            ph.price_amount AS nytt,
            lag(ph.price_amount) OVER (PARTITION BY ph.source, ph.source_listing_id ORDER BY ph.id) AS fyrra
           FROM (scraper.listing_price_history ph
             JOIN lst l USING (source, source_listing_id))
        ), bp AS (
         SELECT ph.listing_id,
            ph.fyrra,
            ph.nytt,
            ph.id,
            row_number() OVER (PARTITION BY ph.listing_id, ph.fyrra, ph.nytt ORDER BY ph.id) AS tilvik
           FROM ph
          WHERE ((ph.fyrra IS NOT NULL) AND (ph.fyrra <> ph.nytt) AND (ph.fyrra >= 1000000) AND (ph.nytt >= 1000000))
        ), ath0 AS (
         SELECT a.listing_id,
            a.price_amount,
            a.fyrst_sed,
            lag(a.price_amount) OVER w AS prev,
            lag(a.sidast_sed) OVER w AS prev_sidast
           FROM scraper.verdvakt_athuganir a
          WINDOW w AS (PARTITION BY a.listing_id ORDER BY a.fyrst_sed)
        ), ath AS (
         SELECT ath0.listing_id,
            ath0.prev AS fyrra,
            ath0.price_amount AS nytt,
            ath0.fyrst_sed,
            ath0.prev_sidast,
            row_number() OVER (PARTITION BY ath0.listing_id, ath0.prev, ath0.price_amount ORDER BY ath0.fyrst_sed) AS tilvik
           FROM ath0
          WHERE ((ath0.prev IS NOT NULL) AND (ath0.prev <> ath0.price_amount))
        ), sop AS (
         SELECT l.listing_id,
            ((e.evidence ->> 'old'::text))::bigint AS fyrra,
            ((e.evidence ->> 'new'::text))::bigint AS nytt,
            e.event_at,
            lag(e.event_at) OVER (PARTITION BY e.source, e.source_listing_id ORDER BY e.event_at) AS fyrri_event,
            row_number() OVER (PARTITION BY l.listing_id, ((e.evidence ->> 'old'::text))::bigint, ((e.evidence ->> 'new'::text))::bigint ORDER BY e.event_at) AS tilvik
           FROM (scraper.listing_lifecycle_events e
             JOIN lst l USING (source, source_listing_id))
          WHERE (e.event_type = 'price_changed'::scraper.lifecycle_event_enum)
        ), innan AS (
         SELECT bp.listing_id,
            'innan'::text AS teg,
            bp.fyrra AS fyrra_verd,
            COALESCE(ath.prev_sidast, h.sast_sidast_fyrra, s.fyrri_event, l.first_seen_at) AS fyrra_sast,
                CASE
                    WHEN (COALESCE(ath.prev_sidast, h.sast_sidast_fyrra, s.fyrri_event) IS NULL) THEN 'fyrst'::text
                    ELSE 'sidast'::text
                END AS fyrra_sast_teg,
            bp.nytt AS nytt_verd,
            COALESCE(ath.fyrst_sed, h.sast_fyrst_nytt, s.event_at) AS nytt_sast,
            NULL::bigint AS fyrri_listing_id,
                CASE
                    WHEN (ath.fyrst_sed IS NOT NULL) THEN 'athuganaskra'::text
                    WHEN (h.sast_fyrst_nytt IS NOT NULL) THEN 'hra_bakfylling'::text
                    ELSE 'sopun'::text
                END AS dags_lind
           FROM ((((bp
             JOIN lst l USING (listing_id))
             LEFT JOIN ath ON (((ath.listing_id = bp.listing_id) AND (ath.fyrra = bp.fyrra) AND (ath.nytt = bp.nytt) AND (ath.tilvik = bp.tilvik))))
             LEFT JOIN scraper.verdvakt_hra_athugun h ON (((h.listing_id = bp.listing_id) AND (h.fyrra_verd = bp.fyrra) AND (h.nytt_verd = bp.nytt) AND (h.tilvik = bp.tilvik))))
             LEFT JOIN sop s ON (((s.listing_id = bp.listing_id) AND (s.fyrra = bp.fyrra) AND (s.nytt = bp.nytt) AND (s.tilvik = bp.tilvik))))
          WHERE (COALESCE(ath.fyrst_sed, h.sast_fyrst_nytt, s.event_at) IS NOT NULL)
        ), ch0 AS (
         SELECT milli.listing_id,
            milli.teg,
            milli.fyrra_verd,
            milli.fyrra_sast,
            milli.fyrra_sast_teg,
            milli.nytt_verd,
            milli.nytt_sast,
            milli.fyrri_listing_id,
            milli.dags_lind
           FROM milli
        UNION ALL
         SELECT innan.listing_id,
            innan.teg,
            innan.fyrra_verd,
            innan.fyrra_sast,
            innan.fyrra_sast_teg,
            innan.nytt_verd,
            innan.nytt_sast,
            innan.fyrri_listing_id,
            innan.dags_lind
           FROM innan
        ), ch1 AS (
         SELECT DISTINCT ON (l.fastnum, c_1.fyrra_verd, c_1.nytt_verd) c_1.listing_id,
            c_1.teg,
            c_1.fyrra_verd,
            c_1.fyrra_sast,
            c_1.fyrra_sast_teg,
            c_1.nytt_verd,
            c_1.nytt_sast,
            c_1.fyrri_listing_id,
            c_1.dags_lind,
            l.source,
            l.source_listing_id,
            l.fastnum,
            l.size_sqm,
            l.rooms,
            l.addr_text,
            l.byggar,
            l.hlutd_texti
           FROM (ch0 c_1
             JOIN lst l USING (listing_id))
          ORDER BY l.fastnum, c_1.fyrra_verd, c_1.nytt_verd, c_1.nytt_sast, c_1.listing_id
        ), virk AS (
         SELECT lst.fastnum,
            lst.size_sqm,
            lst.rooms
           FROM lst
          WHERE ((lst.status = 'active'::text) AND lst.an_terminal)
          GROUP BY lst.fastnum, lst.size_sqm, lst.rooms
        ), ch2 AS (
         SELECT c_1.listing_id,
            c_1.teg,
            c_1.fyrra_verd,
            c_1.fyrra_sast,
            c_1.fyrra_sast_teg,
            c_1.nytt_verd,
            c_1.nytt_sast,
            c_1.fyrri_listing_id,
            c_1.dags_lind,
            c_1.source,
            c_1.source_listing_id,
            c_1.fastnum,
            c_1.size_sqm,
            c_1.rooms,
            c_1.addr_text,
            c_1.byggar,
            c_1.hlutd_texti,
            (c_1.nytt_verd - c_1.fyrra_verd) AS breyting_kr,
            round((((c_1.nytt_verd - c_1.fyrra_verd))::numeric / (c_1.fyrra_verd)::numeric), 4) AS breyting_hlutfall,
            (c_1.hlutd_texti OR ((((c_1.nytt_verd)::numeric / (c_1.fyrra_verd)::numeric) >= 0.748) AND (((c_1.nytt_verd)::numeric / (c_1.fyrra_verd)::numeric) <= 0.752)) OR ((((c_1.nytt_verd)::numeric / (c_1.fyrra_verd)::numeric) >= 1.331) AND (((c_1.nytt_verd)::numeric / (c_1.fyrra_verd)::numeric) <= 1.336))) AS hlutd_grunur,
            (EXISTS ( SELECT 1
                   FROM ch1 r
                  WHERE ((r.fastnum = c_1.fastnum) AND (NOT (r.size_sqm IS DISTINCT FROM c_1.size_sqm)) AND (NOT (r.rooms IS DISTINCT FROM c_1.rooms)) AND (r.fyrra_verd = c_1.nytt_verd) AND (r.nytt_verd = c_1.fyrra_verd) AND (abs(EXTRACT(epoch FROM (r.nytt_sast - c_1.nytt_sast))) <= ((30 * 86400))::numeric)))) AS arekstur,
            (EXISTS ( SELECT 1
                   FROM virk v
                  WHERE ((v.fastnum = c_1.fastnum) AND (NOT (v.size_sqm IS DISTINCT FROM c_1.size_sqm)) AND (NOT (v.rooms IS DISTINCT FROM c_1.rooms))))) AS a_solu,
            ((((c_1.nytt_verd)::numeric / (c_1.fyrra_verd)::numeric) > (3)::numeric) OR (((c_1.nytt_verd)::numeric / (c_1.fyrra_verd)::numeric) < (1.0 / (3)::numeric))) AS grunsamleg
           FROM ch1 c_1
        )
 SELECT row_number() OVER (ORDER BY c.nytt_sast DESC, c.listing_id) AS rod_id,
    c.listing_id,
    c.source,
    c.source_listing_id,
    c.fastnum,
    COALESCE(p.heimilisfang, c.addr_text) AS heimilisfang,
    c.addr_text AS auglyst_heiti,
    p.postnr,
    p.postheiti,
    p.sveitarfelag,
    p.lat,
    p.lng,
    round(c.size_sqm, 1) AS size_sqm,
    c.rooms,
    COALESCE(c.byggar, (p.byggar)::integer) AS byggar,
    c.teg,
    c.fyrra_verd,
    c.fyrra_sast,
    c.fyrra_sast_teg,
    c.nytt_verd,
    c.nytt_sast,
    c.breyting_kr,
    c.breyting_hlutfall,
        CASE
            WHEN (c.size_sqm > (0)::numeric) THEN round(((c.breyting_kr)::numeric / c.size_sqm))
            ELSE NULL::numeric
        END AS breyting_kr_fm,
    c.a_solu,
    ((COALESCE(c.byggar, (p.byggar)::integer) >= ((EXTRACT(year FROM CURRENT_DATE))::integer - 1)) OR ((p.byggingarstig = ANY (ARRAY['B0'::text, 'B1'::text, 'B2'::text, 'B3'::text])) AND (p.matsstig ~ '^[0-6]$'::text))) AS nybygging,
    ((p.einflm IS NOT NULL) AND (abs((c.size_sqm - p.einflm)) < (1)::numeric) AND (EXISTS ( SELECT 1
           FROM jsonb_array_elements(COALESCE(p.matseiningar, '[]'::jsonb)) m(value)
          WHERE ((m.value ->> 'notkun_kodi'::text) = ANY (ARRAY['504'::text, '529'::text]))))) AS staerd_telur_bilskur,
    c.hlutd_grunur,
    c.arekstur,
    (abs(c.breyting_hlutfall) >= 0.30) AS grunur_villa,
    c.fyrri_listing_id,
    c.dags_lind,
    (c.teg = 'milli'::text) AS endurbirting,
        CASE
            WHEN (c.teg = 'milli'::text) THEN 'endurbirt á nýju verði'::text
            WHEN (c.breyting_kr < 0) THEN 'lækkað í auglýsingu'::text
            ELSE 'hækkað í auglýsingu'::text
        END AS flokkur,
        CASE
            WHEN (c.breyting_kr < 0) THEN 'laekkun'::text
            ELSE 'haekkun'::text
        END AS stefna,
    c.grunsamleg,
    'cc219-v2'::text AS regla_version,
    now() AS byggt_at
   FROM (ch2 c
     LEFT JOIN properties p ON ((p.fastnum = c.fastnum)))
with data;
CREATE INDEX v_verdvakt_breytingar_v2_nytt_sast_idx_cc341ny ON semantic.v_verdvakt_breytingar_v2_cc341ny USING btree (nytt_sast DESC);
CREATE UNIQUE INDEX v_verdvakt_breytingar_v2_rod_idx_cc341ny ON semantic.v_verdvakt_breytingar_v2_cc341ny USING btree (rod_id);
grant select on semantic.v_verdvakt_breytingar_v2_cc341ny to anon, authenticated;
comment on materialized view semantic.v_verdvakt_breytingar_v2_cc341ny is 'Verðvaktin v2 (cc219): innan-breytingar úr verðsögu dagsettar með athugun (athuganaskrá → hrá-bakfylling 09.06–07.09 → sópun); flokkar endurbirt á nýju verði / lækkað-hækkað í auglýsingu. regla_version cc219-v2.';
create materialized view semantic.v_verdvakt_nefnarar_v2_cc341ny as
WITH lst AS (
         SELECT l.listing_id,
            l.source,
            l.source_listing_id
           FROM scraper.listings l
          WHERE ((l.tenure = 'sale'::text) AND (l.category = 'residential'::text) AND (l.fastnum IS NOT NULL) AND (l.price_amount IS NOT NULL) AND (l.price_amount >= 1000000) AND (NOT COALESCE(l.is_price_on_request, false)))
        ), ph AS (
         SELECT ph.price_amount AS nytt,
            lag(ph.price_amount) OVER (PARTITION BY ph.source, ph.source_listing_id ORDER BY ph.id) AS fyrra
           FROM (scraper.listing_price_history ph
             JOIN lst USING (source, source_listing_id))
        ), tp AS (
         SELECT t.dags,
            t.draug_n,
            t.draug_nefnari,
            t.draug_ovisst
           FROM scraper.thekjuprof t
          ORDER BY t.maelt_kl DESC
         LIMIT 1
        ), b AS (
         SELECT v_verdvakt_breytingar_v2.rod_id,
            v_verdvakt_breytingar_v2.listing_id,
            v_verdvakt_breytingar_v2.source,
            v_verdvakt_breytingar_v2.source_listing_id,
            v_verdvakt_breytingar_v2.fastnum,
            v_verdvakt_breytingar_v2.heimilisfang,
            v_verdvakt_breytingar_v2.auglyst_heiti,
            v_verdvakt_breytingar_v2.postnr,
            v_verdvakt_breytingar_v2.postheiti,
            v_verdvakt_breytingar_v2.sveitarfelag,
            v_verdvakt_breytingar_v2.lat,
            v_verdvakt_breytingar_v2.lng,
            v_verdvakt_breytingar_v2.size_sqm,
            v_verdvakt_breytingar_v2.rooms,
            v_verdvakt_breytingar_v2.byggar,
            v_verdvakt_breytingar_v2.teg,
            v_verdvakt_breytingar_v2.fyrra_verd,
            v_verdvakt_breytingar_v2.fyrra_sast,
            v_verdvakt_breytingar_v2.fyrra_sast_teg,
            v_verdvakt_breytingar_v2.nytt_verd,
            v_verdvakt_breytingar_v2.nytt_sast,
            v_verdvakt_breytingar_v2.breyting_kr,
            v_verdvakt_breytingar_v2.breyting_hlutfall,
            v_verdvakt_breytingar_v2.breyting_kr_fm,
            v_verdvakt_breytingar_v2.a_solu,
            v_verdvakt_breytingar_v2.nybygging,
            v_verdvakt_breytingar_v2.staerd_telur_bilskur,
            v_verdvakt_breytingar_v2.hlutd_grunur,
            v_verdvakt_breytingar_v2.arekstur,
            v_verdvakt_breytingar_v2.grunur_villa,
            v_verdvakt_breytingar_v2.fyrri_listing_id,
            v_verdvakt_breytingar_v2.dags_lind,
            v_verdvakt_breytingar_v2.endurbirting,
            v_verdvakt_breytingar_v2.flokkur,
            v_verdvakt_breytingar_v2.stefna,
            v_verdvakt_breytingar_v2.grunsamleg,
            v_verdvakt_breytingar_v2.regla_version,
            v_verdvakt_breytingar_v2.byggt_at
           FROM semantic.v_verdvakt_breytingar_v2_cc341ny v_verdvakt_breytingar_v2
        )
 SELECT 1 AS id,
    now() AS byggt_at,
    'cc219-v2'::text AS regla_version,
    ( SELECT count(DISTINCT v.fastnum) AS count
           FROM scraper.v_eign_virk_auglysing v
          WHERE ((v.tenure = 'sale'::text) AND (v.category = 'residential'::text) AND (v.fastnum IS NOT NULL))) AS n_eignir_a_solu,
    ( SELECT tp.dags
           FROM tp) AS draug_dags,
    ( SELECT tp.draug_n
           FROM tp) AS draug_n,
    ( SELECT tp.draug_nefnari
           FROM tp) AS draug_nefnari,
    ( SELECT tp.draug_ovisst
           FROM tp) AS draug_ovisst,
    ( SELECT count(*) AS count
           FROM b) AS n_breytingar_alls,
    ( SELECT count(*) AS count
           FROM b
          WHERE (b.teg = 'innan'::text)) AS n_innan,
    ( SELECT count(*) AS count
           FROM b
          WHERE (b.teg = 'milli'::text)) AS n_endurbirtingar,
    ( SELECT count(*) AS count
           FROM b
          WHERE ((b.flokkur = 'endurbirt á nýju verði'::text) AND (NOT b.grunsamleg))) AS n_endurbirt_nytt_verd,
    ( SELECT count(*) AS count
           FROM b
          WHERE ((b.flokkur = 'lækkað í auglýsingu'::text) AND (NOT b.grunsamleg))) AS n_laekkad_i_auglysingu,
    ( SELECT count(*) AS count
           FROM b
          WHERE ((b.flokkur = 'hækkað í auglýsingu'::text) AND (NOT b.grunsamleg))) AS n_haekkad_i_auglysingu,
    ( SELECT count(*) AS count
           FROM b
          WHERE (b.dags_lind = 'athuganaskra'::text)) AS n_lind_athuganaskra,
    ( SELECT count(*) AS count
           FROM b
          WHERE (b.dags_lind = 'hra_bakfylling'::text)) AS n_lind_hra,
    ( SELECT count(*) AS count
           FROM b
          WHERE (b.dags_lind = 'sopun'::text)) AS n_lind_sopun,
    ( SELECT count(*) AS count
           FROM b
          WHERE b.grunsamleg) AS n_grunsamleg,
    ( SELECT count(*) AS count
           FROM b
          WHERE (b.hlutd_grunur AND (NOT b.grunsamleg))) AS n_hlutd_grunur,
    ( SELECT count(*) AS count
           FROM b
          WHERE (b.arekstur AND (NOT b.hlutd_grunur) AND (NOT b.grunsamleg))) AS n_arekstrar,
    ( SELECT count(*) AS count
           FROM b
          WHERE (b.grunur_villa AND (NOT b.hlutd_grunur) AND (NOT b.arekstur) AND (NOT b.grunsamleg))) AS n_grunur_villa,
    (( SELECT count(*) AS count
           FROM ph
          WHERE ((ph.fyrra IS NOT NULL) AND (ph.fyrra <> ph.nytt) AND (ph.fyrra >= 1000000) AND (ph.nytt >= 1000000))) - ( SELECT count(*) AS count
           FROM semantic.v_verdvakt_breytingar_v2_cc341ny x
          WHERE (x.teg = 'innan'::text))) AS n_innan_odagsett_eda_afritud,
    ( SELECT (min(a.fyrst_sed))::date AS min
           FROM scraper.verdvakt_athuganir a) AS athuganaskra_fra,
    ( SELECT (min(h.sast_fyrst_nytt))::date AS min
           FROM scraper.verdvakt_hra_athugun h) AS bakfylling_fra,
    ( SELECT (max(h.sast_fyrst_nytt))::date AS max
           FROM scraper.verdvakt_hra_athugun h) AS bakfylling_til,
    ( SELECT count(*) AS count
           FROM semantic.v_verdvakt_afsala) AS n_farnar_alls,
    ( SELECT max(s.thinglystdags) AS max
           FROM sales_history s
          WHERE (s.onothaefur = 0)) AS kaupskra_til
with data;
CREATE UNIQUE INDEX v_verdvakt_nefnarar_v2_id_idx_cc341ny ON semantic.v_verdvakt_nefnarar_v2_cc341ny USING btree (id);
grant select on semantic.v_verdvakt_nefnarar_v2_cc341ny to anon, authenticated;
create materialized view semantic.v_verdvakt_nefnarar_svaedi_v2_cc341ny as
WITH virk AS (
         SELECT l.fastnum,
            ((COALESCE(l.byggar, (p.byggar)::integer) >= ((EXTRACT(year FROM CURRENT_DATE))::integer - 1)) OR ((p.byggingarstig = ANY (ARRAY['B0'::text, 'B1'::text, 'B2'::text, 'B3'::text])) AND (p.matsstig ~ '^[0-6]$'::text))) AS nyb
           FROM (scraper.listings l
             LEFT JOIN properties p ON ((p.fastnum = l.fastnum)))
          WHERE ((l.tenure = 'sale'::text) AND (l.category = 'residential'::text) AND (l.fastnum IS NOT NULL) AND (l.price_amount IS NOT NULL) AND (l.price_amount >= 1000000) AND (NOT COALESCE(l.is_price_on_request, false)) AND (l.status = 'active'::text) AND (NOT (EXISTS ( SELECT 1
                   FROM scraper.listing_lifecycle_events e_1
                  WHERE ((e_1.source = l.source) AND (e_1.source_listing_id = l.source_listing_id) AND (e_1.event_type = 'withdrawn_confirmed'::scraper.lifecycle_event_enum))))))
        ), eign AS (
         SELECT virk.fastnum,
            bool_or(virk.nyb) AS nyb
           FROM virk
          GROUP BY virk.fastnum
        ), eign_sv AS (
         SELECT eign.fastnum,
            eign.nyb,
                CASE
                    WHEN (p.postnr IS NULL) THEN 'othekkt'::text
                    WHEN (EXISTS ( SELECT 1
                       FROM semantic.verdvakt_hbs_postnr h_1
                      WHERE (h_1.postnr = p.postnr))) THEN 'hbs'::text
                    ELSE 'lands'::text
                END AS svaedi
           FROM (eign
             LEFT JOIN properties p ON ((p.fastnum = eign.fastnum)))
        ), holf AS (
         SELECT sv.svaedi,
            st.nybygg
           FROM (( VALUES ('allt'::text), ('hbs'::text), ('lands'::text)) sv(svaedi)
             CROSS JOIN ( VALUES ('med'::text), ('an'::text), ('adeins'::text)) st(nybygg))
        )
 SELECT h.svaedi,
    h.nybygg,
    count(e.fastnum) AS n_eignir_a_solu,
    50 AS golf,
    (count(e.fastnum) < 50) AS undir_golfi,
    ( SELECT count(*) AS count
           FROM eign_sv
          WHERE (eign_sv.svaedi = 'othekkt'::text)) AS n_postnr_othekkt,
    'cc225-v1'::text AS regla_version,
    now() AS byggt_at
   FROM (holf h
     LEFT JOIN eign_sv e ON ((((h.svaedi = 'allt'::text) OR (e.svaedi = h.svaedi)) AND ((h.nybygg = 'med'::text) OR ((h.nybygg = 'an'::text) AND (e.nyb IS NOT TRUE)) OR ((h.nybygg = 'adeins'::text) AND (e.nyb IS TRUE))))))
  GROUP BY h.svaedi, h.nybygg
with data;
CREATE UNIQUE INDEX v_verdvakt_nefnarar_svaedi_v2_idx_cc341ny ON semantic.v_verdvakt_nefnarar_svaedi_v2_cc341ny USING btree (svaedi, nybygg);
grant select on semantic.v_verdvakt_nefnarar_svaedi_v2_cc341ny to anon, authenticated;
comment on materialized view semantic.v_verdvakt_nefnarar_svaedi_v2_cc341ny is 'Verðvaktin (cc225): eignir (fastnúmer) á sölu per svæði (allt/hbs/lands, póstnúmeraregla kafla 13) × nýbyggingarstað (med/an/adeins); gólf 50. regla_version cc225-v1.';

-- skipti: lás á lifandi MV aðeins héðan að COMMIT
drop materialized view semantic.v_verdvakt_nefnarar_v2;
drop materialized view semantic.v_verdvakt_breytingar_v2;
drop materialized view semantic.v_verdvakt_nefnarar_svaedi_v2;
alter materialized view semantic.v_verdvakt_breytingar_v2_cc341ny rename to v_verdvakt_breytingar_v2;
alter index semantic.v_verdvakt_breytingar_v2_nytt_sast_idx_cc341ny rename to v_verdvakt_breytingar_v2_nytt_sast_idx;
alter index semantic.v_verdvakt_breytingar_v2_rod_idx_cc341ny rename to v_verdvakt_breytingar_v2_rod_idx;
alter materialized view semantic.v_verdvakt_nefnarar_v2_cc341ny rename to v_verdvakt_nefnarar_v2;
alter index semantic.v_verdvakt_nefnarar_v2_id_idx_cc341ny rename to v_verdvakt_nefnarar_v2_id_idx;
alter materialized view semantic.v_verdvakt_nefnarar_svaedi_v2_cc341ny rename to v_verdvakt_nefnarar_svaedi_v2;
alter index semantic.v_verdvakt_nefnarar_svaedi_v2_idx_cc341ny rename to v_verdvakt_nefnarar_svaedi_v2_idx;

notify pgrst, 'reload schema';
commit;
