-- cc82 — SÖLUAÐILI ÚR AUGLÝSINGU Í GEGN (parse → promote → birting).
--
-- Rökin (FASTINN_SAMANBURDUR_CC82 §2.12, §3.3): mbl-svarið ber söluaðilann og
-- `parse_mbl.py` hefur alltaf geymt hann í `parsed_mbl_{sale,rent}.agency_json`
-- (37.517 / 38.706 sale-raðir = 96,9%; 3.150 / 3.165 rent-raðir = 99,5%).
-- Promote-lagið tók hann aldrei með, svo Postgres — og þar með allar
-- notendasíður — vissu ekki af honum. Þetta er FLUTNINGUR á gögnum sem við
-- eigum þegar, ekki ný gagnasókn.
--
-- SKALARDÁLKAR, EKKI jsonb: hvert gildi sem BIRTIST notanda er sér dálkur í
-- þessari töflu (sbr. bedrooms/bathrooms/byggar); `photos_json` er jsonb því
-- það er SAFN. Skalarnir gera þekjumælingu ótvíræða (NULL = vantar) og halda
-- birtingarlaginu lausu við ótýpaða JSON-gröft.
--
-- LINDARMERKING: söluaðili er FULLYRÐING AUGLÝSANDA, nákvæmlega eins og verð
-- og lýsing. Birtingin ber lindina (cc69-regla ASoluKort: „Heimild: [lind]").
--
-- ADDITIVE: engir dálkar felldir, engin gögn snert, engin vísitala bætt við
-- (enginn þekktur síunar-lesandi enn — vísitala bíður raunverulegs lesanda).

alter table scraper.listings
  add column if not exists agency_name      text,
  add column if not exists agency_phone     text,
  add column if not exists agency_email     text,
  add column if not exists agency_addr      text,
  add column if not exists agency_postcode  text,
  add column if not exists agency_url       text,
  add column if not exists agency_source_id integer;

comment on column scraper.listings.agency_name is
  'Fasteignasala úr auglýsingu (mbl agency.nafn). Fullyrðing auglýsanda, ekki okkar mæling. cc82.';
comment on column scraper.listings.agency_phone is
  'Símanúmer söluaðila úr auglýsingu (mbl agency.simi). cc82.';
comment on column scraper.listings.agency_email is
  'Netfang söluaðila úr auglýsingu (mbl agency.email_tl). cc82.';
comment on column scraper.listings.agency_addr is
  'Starfsstöð söluaðila úr auglýsingu (mbl agency.heimilisfang). cc82.';
comment on column scraper.listings.agency_postcode is
  'Póstnúmer/staður starfsstöðvar úr auglýsingu (mbl agency.postnumer, frítexti: "103 Reykjavík"). cc82.';
comment on column scraper.listings.agency_url is
  'Vefslóð söluaðila úr auglýsingu (mbl agency.vefslod). cc82.';
comment on column scraper.listings.agency_source_id is
  'Auðkenni söluaðila hjá lindinni (mbl agency.sala_id) — EKKI okkar auðkenni. cc82.';

-- Virka-auglýsingar-viewið er eina leiðin sem eignasíðan les auglýsinguna um
-- (cc69/cc71/cc75). Nýju dálkarnir bætast AFTAST — röð og týpur eldri dálka
-- óbreyttar, sem er skilyrði `create or replace view`.
create or replace view scraper.v_eign_virk_auglysing as
 SELECT l.listing_id,
    l.source,
    l.fastnum,
    l.tenure,
    l.category,
    l.price_amount,
    l.is_price_on_request,
    ph.asett_verd_dags,
    l.listed_at,
    l.first_seen_at,
    l.last_seen_at,
    l.er_atvinnuhusnaedi,
    l.lysing,
    l.agency_name,
    l.agency_phone,
    l.agency_email,
    l.agency_addr,
    l.agency_postcode,
    l.agency_url
   FROM scraper.listings l
     LEFT JOIN LATERAL ( SELECT max(ph2.observed_at) AS asett_verd_dags
           FROM scraper.listing_price_history ph2
          WHERE ph2.source = l.source AND ph2.source_listing_id = l.source_listing_id) ph ON true
  WHERE l.status = 'active'::text AND NOT (EXISTS ( SELECT 1
           FROM scraper.listing_lifecycle_events e
          WHERE e.source = l.source AND e.source_listing_id = l.source_listing_id AND e.event_type = 'withdrawn_confirmed'::scraper.lifecycle_event_enum)) AND NOT (EXISTS ( SELECT 1
           FROM scraper.listing_lifecycle_events ea
          WHERE ea.source = l.source AND ea.source_listing_id = l.source_listing_id AND ea.event_type = 'confirmed_absent_1'::scraper.lifecycle_event_enum)) AND (l.addr_text IS NULL OR l.addr_text !~* '(\yseld\y|\yseldar\y|\yseldur\y|\ysold\y|\yfrátekin\y|\yfrátekið\y)'::text);
