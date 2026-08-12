"""extraction_engine.py — content-addressed extraction + frozen valuation engine (EXTRACTION
ÞREP 3-4). One engine, three triggers (seed / nightly-forward / on-demand-lazy share value_listings;
extract_and_store is the Haiku half used by forward + lazy).

  * value_listings(pg, models, rows)   — score expected_base (structured) + expected_extraction
                                          (+ 108-field features) via the VÉL 1 freeze-anchored
                                          adapter, freeze into scraper.listing_valuations.
                                          NO Haiku — extraction comes from listing_extractions.
  * extract_and_store(pg, client, rows) — Haiku 108-field extract for lysingar with no extraction,
                                          store content-addressed in listing_extractions.

Parity basis: phase_d3_score_extract.score pins sale_year/month to VALUATION_YEAR/MONTH (2026-04),
so expected_base reproduces public.predictions; expected_extraction overlays the extraction
feature columns. Both nominal @ 2026-04, identical basis → gap is clean.

cc140 (12.08.2026): the frozen column is `real_pred_mean` from that same scoring — NOT
`real_pred_median` as it was 27.06–12.08. Aldamörk `valued_at >= 2026-08-12 00:00:00+00`;
older rows stand unrewritten and carry the median age. See value_listings + DECISIONS §5D-4.

Pooler writes open with SET TRANSACTION READ WRITE. The Haiku key is read ONLY from D:\env.local
(see extract_and_store) — never os.environ.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from psycopg2.extras import execute_values, Json

sys.path.insert(0, str(Path(__file__).resolve().parent))   # scripts/
sys.path.insert(0, r"D:\\")                                  # build_training_data_v2

# cc47 replaced the hardcoded MODEL_VERSION with pipeline_config.model_version + the adapter's
# own stamp; these valuations are computed BY the freeze-anchored adapter, so its stamp is the
# honest model_version here (same value the historical listing_valuations rows carry).
#
# cc112: that stamp being "honest" is what makes the mismatch DANGEROUS, not safe. The adapter
# still loads D:\iter4a_*.lgb (154 features, untouched since 21.04) while pipeline_config has
# moved on to iter4r_20260805_reglaR_strukt (156). read_model_version is imported here so the
# write path asks the SAME question, off the SAME key, as the measurement does.
#
# cc113 ENDURTENGING: MODEL_VERSION er ekki lengur FASTI heldur BINDING. Sjálfgefið
# gildi er sögulegi stimpillinn (fail-safe: sé artifactið aldrei hlaðið fellur hliðið),
# en load_serving_models() endurbindur hann við stimpil þess artifacts sem raunverulega
# var hlaðið af diski. Hliðið sjálft (assert_write_world_matches_live) er ÓSNERT —
# breytingin er á því HVAÐ nafnið vísar á, ekki á því hvað hliðið gerir.
from model_quality_eval import (  # noqa: E402
    load_models_live_artifact, _score_iter4, _coerce_numeric,
    read_model_version, MODEL_VERSION_KEY,
    ADAPTER_MODEL_VERSION as MODEL_VERSION)
from build_training_data_v2 import build_extraction_features  # noqa: E402


def load_serving_models(pg, log=print):
    """cc113 — hlaða artifactið sem pipeline_config vísar á og binda MODEL_VERSION við
    stimpil þess AF DISKI (manifest), ekki við hardkóðaðan fasta.

    Kallað af run_extraction ÁÐUR en biðröðin er sótt: `fetch_extracted_listings_to_value`
    síar á MODEL_VERSION, svo binding eftir á myndi sækja biðröð fyrir rangt líkan.
    """
    global MODEL_VERSION
    models = load_models_live_artifact(pg, log=log)
    MODEL_VERSION = models["model_version"]
    return models

VALUATION_YEAR = 2026
SCHEMA_VERSION = "v0.2.2"
EXTRACT_MODEL = "claude-haiku-4-5"

# ── cc127 KOSTNAÐARBÓKHALD — RAUNNOTKUN Í STAÐ FASTA ─────────────────────────
# Fram að cc127 var kostnaður bókaður sem `n_call × 0.0071` — FASTI margfaldaður
# með kallafjölda. `extract_listing` skilar raunnotkun (input/output/cache_read/
# cache_creation) og kallandinn henti henni. Fastinn sjálfur var afkomandi
# calc_cost-vanmatsins (DECISIONS.md 2026-04-19, lagað á diski í cc127) og mældist
# 2,8× of lágur: raunkostnaður $0,0197–0,0200/kall á TVEIMUR óháðum $10-hringjum
# (A: 06.–08.08, B: 09.–11.08, cc125 §A2).
#
# Þessi fasti er nú EINGÖNGU VARAÁÆTLUN, í tveimur hlutverkum:
#   (a) FORSPÁ  — run_extraction verður að umreikna „dollarar eftir af dagsþaki"
#                 í „hversu mörg köll má kaupa" ÁÐUR en nokkurt kall er gert.
#                 Þess vegna verður hann að vera >= raunkostnaður, annars hleypur
#                 hrinan fram úr þakinu (nákvæmlega bilunin sem cc127 lagar).
#   (b) FALLBACK — kall sem skilar engri notkun (fallið kall) er bókað á þessu
#                 verði og TALIÐ SÉR, svo áætlun og mæling ruglist aldrei saman.
# Forspá sem VANMETUR er þak sem lekur, svo talan verður að DROTTNA yfir mælda
# versta tilviki — ekki hitta meðaltalið. Fyrsta tilraun cc127 setti hana á efri
# mörk bilsins ($0,0200) og ÞURRKEYRSLAN FELLDI HANA: rauðsönnunin í §4 mældi
# $0,020717/kall (köld skyndiminnis-ræsing innifalin), svo 500 leyfð köll hefðu
# endað í $10,36 — þakið lak enn, bara 3,6% í stað 179%.
#
# $0,0225 er versta mælda tilvikið + ~9% svigrúm. Mælda dreifingin sjálf sýnir af
# hverju fastinn getur aðeins verið ÞAK en aldrei VERÐ: sama hrinan kostaði
# $0,019430/kall með heitt skyndiminni en $0,020717/kall með kalt. Þess vegna er
# BÓKUNIN raunnotkun; þessi tala er eingöngu forspá og fallback.
# Rekstrarleg áhrif engin: nóttin kaupir 200 köll (~$4,1), langt undir þakinu.
PER_CALL_USD_EST = 0.0225

# ── cc94 ÞREP A — validering á skrif-leiðinni ────────────────────────────────
# MÆLT 2026-08-04 (read-only, nefnari 5.122 útdrættir): 152 (2,97%) bera
# `components` sem STRENG — 0 af 152 parsast, því líkanið typar strenginn sjálft
# og misritar unicode-escape-in (`múrvið\u00gerðir`). 2 ár utan bils (10, 20) —
# frumtextarnir segja „fyrir um 10/20 árum", þ.e. AFSTÆÐUR ALDUR skrifaður í
# ártalsreit, EKKI stytt ártal (tilgátan 10→2010 var mæld og felld). 11 lyklar
# og 5 status-gildi utan lokaðra mengja. Blæddi enn: 4 nýjar raðir í nótt.
#
# RÓTIN: `input_schema` í tólaskilgreiningunni er LEIÐBEINING til líkansins, ekki
# server-side validator. Skemað í pilot_extract_v022.build_tool_schema er rétt
# skrifað (`components` = object, `year` = [1900,2030], `additionalProperties`
# false) — það er einfaldlega ekki þvingað, og ekkert lag hafnaði.
# pilot_extract_v022.flatten_row BAR skynjara („components_malformed") en býr í
# CSV-flötunarfalli pilotsins sem nætur-keðjan kallar ALDREI. Sú lexía er ástæðan
# fyrir að þetta fall er kallað hér, í `extract_and_store` — eina staðnum sem
# skrifar í scraper.listing_extractions (sannreynt með grepi 04.08: kallstaðurinn
# er nightly_delta_chain.sh:228 -> run_extraction.py:131 -> extract_and_store;
# model_quality_eval.py kallar sama extract_listing en skrifar í JSONL-cache,
# ekki töfluna).
COMPONENT_KEYS = frozenset((
    'kitchen', 'primary_bathroom', 'secondary_bathroom', 'flooring',
    'interior_finishes', 'paint', 'electrical_panel', 'electrical_wiring',
    'plumbing', 'heating', 'windows_unit', 'roof', 'cladding',
    'windows_building', 'insulation', 'elevator_mechanism',
    'sameign_cosmetic', 'foundation_drainage'))
STATUS_ENUM = frozenset((
    'replaced_new', 'overhauled', 'well_maintained', 'original_functional',
    'in_progress', 'needs_work', 'not_mentioned'))
# Neðri mörkin eru 1900 skv. GO-inu (sama bil og cc94-mælingin notaði). BÓKAÐ
# FRÁVIK: disksafnið ber 1882 (1×) og 1898 (3×) sem eru trúverðug byggingarár —
# við þessi mörk væri slíkur útdráttur hafnaður. Höfnun er afturkræf (röðin er
# vistuð ÓBREYTT), svo víkkun í 1850 + endurvalidering endurheimtir hann; það er
# breyting á þessari einu línu. Mælt tíðni: 4 af 27.464 fylltum árum = 0,015%.
YEAR_MIN = 1900
# Efri mörkin eru yfirstandandi ár, ekki fast 2026 og ekki 2030 úr skemanu:
# framkvæmdaár í framtíð er ekki framkvæmd sem er lokið.
YEAR_MAX = VALUATION_YEAR


def validate_extraction(raw):
    """cc94 — dæmir hrátt tool_use.input gegn v0.2.2-skemanu. Skilar (status, reasons).

    HREINT FALL: það BREYTIR ENGU. Röðin er vistuð ÓBREYTT hvort sem hún stenst
    eða fellur — hrásvarið er sönnunargagnið sem gerði cc94-greininguna mögulega,
    og ætti aldrei að hverfa við skrif. Öll leiðrétting (endurlestur strengja,
    ár → NULL, brottfelling lykla) er ÞREP B og gerist afturvirkt, ekki hér.

    status: 'ok' eða 'rejected:<ástæða>[+<ástæða>…]'
    reasons: listi ástæðukóða (tómur ef 'ok') — fleiri en ein ástæða er skeytt
             saman svo seinna brotið feli sig ekki á bak við það fyrra.
    """
    reasons = []
    if not isinstance(raw, dict):
        return "rejected:not_an_object", ["not_an_object"]

    comps = raw.get("components")
    if isinstance(comps, str):
        reasons.append("components_string")
    elif not isinstance(comps, dict):
        reasons.append("components_missing")
    else:
        if set(comps) - COMPONENT_KEYS:
            reasons.append("key_outside_enum")
        bad_year = bad_status = False
        for v in comps.values():
            if not isinstance(v, dict):
                bad_status = True
                continue
            s = v.get("status")
            if s is not None and s not in STATUS_ENUM:
                bad_status = True
            y = v.get("year")
            if y is not None:
                # bool er undirklassi int í Python — True myndi annars sleppa í gegn
                if isinstance(y, bool) or not isinstance(y, int) \
                        or y < YEAR_MIN or y > YEAR_MAX:
                    bad_year = True
        if bad_year:
            reasons.append("year_out_of_range")
        if bad_status:
            reasons.append("status_outside_enum")

    if not reasons:
        return "ok", []
    return "rejected:" + "+".join(reasons), reasons

# property feature columns the iter4 adapter consumes (same set as fetch_paired_oos)
PROP_COLS = ("einflm", "lod_flm", "byggar", "matsvaedi_numer", "matsvaedi_bucket",
             "region_tier", "canonical_code", "unit_category", "is_main_unit",
             "is_new_build", "postnr", "lat", "lng", "landeign_nr")


def md5_12(t):
    return hashlib.md5((t if isinstance(t, str) else "").encode("utf-8")).hexdigest()[:12]


def fetch_extracted_listings_to_value(pg, limit=None):
    """mbl listings whose lysing has an extraction but no valuation yet (for this model)."""
    cols = ", ".join(f"pr.{c}" for c in PROP_COLS)
    sql = f"""
      SELECT DISTINCT ON (l.source_listing_id)
             l.source_listing_id, l.fastnum, e.lysing_hash, e.extraction, {cols}
      FROM scraper.listings l
      JOIN scraper.listing_extractions e ON e.lysing_hash = substr(md5(l.lysing), 1, 12)
      JOIN public.properties pr ON pr.fastnum = l.fastnum
      LEFT JOIN scraper.listing_valuations v
             ON v.source_listing_id = l.source_listing_id AND v.model_version = %s
      WHERE l.source = 'mbl' AND l.fastnum IS NOT NULL AND l.lysing IS NOT NULL
        AND v.valuation_id IS NULL
        -- cc94 ÞREP A: hafnaður útdráttur má ALDREI verða að eiginleikavigri.
        -- Án þessarar línu er höfnunin aðeins merking: build_extraction_features
        -- tekur `year` beint (years_since = sale_year - year), svo year=20 gefur
        -- years_since_heating = 2006 og fer óbreytt inn í frysta verðmatið.
        -- NULL er MEÐTALIÐ af ásettu ráði: það eru 5.122 raðirnar sem voru
        -- skrifaðar fyrir cc94 og aldrei valideraðar. Að útiloka þær hér væri að
        -- stöðva verðmat á öllu safninu sem fyrir er. Tvö spillt ár lifa þar og
        -- eru viðfangsefni ÞREPS B2, ekki þessarar síu.
        AND (e.validation_status IS NULL OR e.validation_status NOT LIKE 'rejected:%%')
        -- ── cc134 SKORUNARHLIÐIÐ — SAMA ÚTILOKUN OG BIRTINGARLEIÐIN ──────────
        -- Hliðið var TIL, en í röngu falli. `phase_d3_score_extract.main()`
        -- (línur 451-464) ber þriggja hliða trekt:
        --     is_scorable = is_residential | is_summerhouse   <- þetta hlið
        --     has_byggar  = byggar.notna()
        --     is_confident= matsvaedi_confident
        -- `value_listings` kallar `score()` BEINT gegnum `_score_iter4` og
        -- sleppir því öllum þremur. Sama gerð og cc112 (hlið á mælingu en ekki
        -- á skrifleið) og cc94 (`flatten_row`-skynjarinn í falli sem keðjan
        -- kallaði aldrei): sían var skrifuð í keyrslu-drifið, ekki í vélina.
        --
        -- ATH. ENGIN PRÓSENTUMERKI Í ÞESSUM ATHUGASEMDUM — skrifaðu orðið.
        -- Strengurinn fer í `cur.execute(sql, params)`, svo psycopg2 les hvert
        -- prósentumerki sem placeholder — líka inni í SQL-athugasemd, því
        -- interpólunin gerist á undan parsernum. Bert prósentumerki hér fellir
        -- næturkeyrsluna með `IndexError: tuple index out of range` ÁÐUR en
        -- nokkur röð er sótt. Eina leyfða notkunin í þessu falli er tvöfölduð
        -- (`rejected:` -liðurinn að ofan), sem psycopg2 skilar sem einu merki.
        -- Fannst í sannprófun cc134 12.08 — á þessari sömu athugasemd.
        --
        -- MÆLT cc134 (12.08, read-only): `training_data_v2.pkl` — sha256[:16]
        -- 32f9a1242b212d11, endurmæld = manifest lifandi líkans — ber 0
        -- EXCLUDE-raðir af 146.841 og enga NaN-röð. `canonical_code` er pandas
        -- Categorical með 12 flokkum; EXCLUDE er ekki í þeim, svo
        -- `pd.Categorical('EXCLUDE', categories=<12>)` -> -1 -> NaN
        -- (phase_d3_score_extract.py:263). Eiginleiki með 2,87 prósenta gain
        -- hverfur og röðin fer niður grein sem ENGIN þjálfunarröð þjálfaði.
        -- Skorað í minni á 410 EXCLUDE-eignum: að þvinga flokkinn í APT_FLOOR
        -- færir töluna um 3,10 prósent að meðaltali — talan er „íbúð af þessari
        -- stærð hér", ekki mat á atvinnuhúsnæði. 82 eignanna hafa ekkert
        -- byggingarflatarmál og bera samt 22,12 M kr að meðaltali
        -- (sumarbústaðaland 19,94 M). Gegn ásettu verði: MdAPE 60,2 gegn 7,7 á
        -- APT_FLOOR.
        --
        -- BORÐIÐ VALDI S1 (12.08). Mælt að S1 og S2 eru SAMA MENGIÐ:
        -- `canonical_code = 'EXCLUDE'` og `NOT (is_residential OR is_summerhouse)`
        -- greinir á um 0 eignir af 232.887. S2 er orðalag birtingarleiðarinnar,
        -- S1 er orðalagið sem borðið bókaði; þau eru jafngild og línan má lesast
        -- sem hvort tveggja.
        --
        -- NULL FELLUR MEÐ, AF ÁSETTU RÁÐI. `<>` sleppir NULL, og það er RÉTT
        -- hegðun hér en ekki í cc94-línunni að ofan: NULL `canonical_code` fer
        -- sömu leið í NaN og EXCLUDE, svo fail-closed er eina stefnan sem
        -- samræmist reglunni. Mælt í dag: 0 af 232.887 eignum bera NULL, svo
        -- línan fjarlægir ekkert umfram EXCLUDE eins og er.
        --
        -- ÁHRIF Á BIÐRÖÐINA, mælt 12.08: 20.270 -> 18.177 raðir (2.093 burt,
        -- 10,33 prósent; 415 eignir). Kostnaður $0,00 — verðmats-þrepið gerir engin
        -- Haiku-köll. Þessi lína snertir ENGA röð sem þegar er í töflunni: hún er
        -- á VERKEFNASKRÁNNI. Gömlu 2.372 raðirnar standa (ákvörðun borðsins,
        -- kostur (b) FELLDUR — söguleg heimild um hvað vélin sagði, sömu rök og
        -- cc116 fyrir 20.642 sögulegu raðirnar). Hreinsun MÆLINGARINNAR er
        -- kostur (c) og býr í scraper.v_expected_vs_real + ops_scraper_signals().
        AND pr.canonical_code <> 'EXCLUDE'
      ORDER BY l.source_listing_id, l.last_seen_at DESC NULLS LAST
      -- cc128 FALSY-GILDRAN LOKUÐ. Skilyrðið var `if limit` — og 0 er falsy, svo
      -- LIMIT-liðurinn FÉLL ÚT og limit=0 skilaði ALLRI biðröðinni. Mælt á lifandi
      -- DB fyrir lagfæringu (11.08): None -> 20.270, 0 -> 20.270, 5 -> 5.
      -- Eftir: None -> 20.270, 0 -> 0, 5 -> 5. `is not None` er eina greiningin sem
      -- heldur „ótakmarkað" (None) aðskildu frá „ekkert" (0). Neikvæð gildi komast
      -- ekki hingað: run_extraction hafnar þeim í argparse (--value-limit >= 0).
      {('LIMIT %d' % int(limit)) if limit is not None else ''}
    """
    cur = pg.cursor()
    cur.execute(sql, (MODEL_VERSION,))
    out = []
    names = [d[0] for d in cur.description]
    for row in cur.fetchall():
        out.append(dict(zip(names, row)))
    return out


class ModelWorldMismatch(RuntimeError):
    """Skrif-hliðið féll: vélin skorar úr öðrum heimi en framleiðslan lifir í."""


def assert_write_world_matches_live(pg, log=print):
    """cc112 F1-VÖRN — ÚTGÁFUHLIÐ Á SKRIFLEIÐINNI.

    model_quality_eval.py:130-134 hefur borið þetta hlið síðan cc47, en aðeins á
    MÆLINGUNNI: reiknist E2-gap milli tveggja LÍKANA er það ekki extraction-gap, svo
    mælingin neitar að birta töluna. Skrifleiðin bar ekkert samsvarandi hlið og hélt
    því áfram að frysta raðir í scraper.listing_valuations úr gamla heiminum.

    MÆLT (cc110 morgunvakt 07.08, S1): adapterinn hleður D:\\iter4a_*.lgb (154
    eiginleikar, óhreyfðir frá 21.04) og stimplar 'iter4_final_v1' meðan
    pipeline_config.model_version ber 'iter4r_20260805_reglaR_strukt' (156). 953 raðir
    skrifaðar eftir 2026-08-06T12:24:26Z, 103 af 478 eignum (21,5%) á eignum sem regla R
    endurflokkaði. Frystu tölurnar eru því ekki það sem framleiðslan myndi segja í dag.

    Sama regla og mælingin ber: VÉL SEM SKORAR MÁ EKKI SKRIFA ÞEGAR HÚN SKORAR ÚR ÖÐRUM
    HEIMI EN FRAMLEIÐSLAN. Hliðið fellur með villu (ekki þöglu `return 0`) svo
    run_extraction fari út með exit != 0 og nightly_delta_chain.sh riti CHAIN FAIL —
    þögul sleppa væri nákvæmlega sama bilunin og hún á að stöðva, bara hljóðlát.

    Hliðið er ekki tengingin sjálf: það stöðvar bara blæðinguna. Endurtenging við
    iter4r-artefaktana + endurreikningur röðanna 953 eru sér verk (PLANNING_BACKLOG).
    """
    live = read_model_version(pg)
    # pipeline_config-lesturinn opnaði lestrar-txn á rw-tengingunni (autocommit=False).
    # Hún VERÐUR að lokast hér, annars er `SET TRANSACTION READ WRITE` neðar ekki lengur
    # fyrsta stæðan í sinni txn og skrifin falla á pooler-num.
    pg.rollback()
    if live != MODEL_VERSION:
        raise ModelWorldMismatch(
            "\n" + "!" * 78 + "\n"
            "SKRIF STÖÐVUÐ — ÚTGÁFUHLIÐ FÉLL (cc112 F1-VÖRN)\n"
            f"  adapter (phase_d3_score_extract / D:\\iter4a_*.lgb) skorar og stimplar: "
            f"'{MODEL_VERSION}'\n"
            f"  lifandi pipeline_config.{MODEL_VERSION_KEY}:                          "
            f"'{live}'\n"
            "Vélin skorar úr ÖÐRUM HEIMI en framleiðslan. Frystar raðir í\n"
            "scraper.listing_valuations væru ekki það sem lifandi líkanið segir, svo\n"
            "EKKERT er skrifað. Þetta er sama hlið og mælingin ber\n"
            "(model_quality_eval.py:130-134), nú líka á skrifleiðinni.\n"
            "Útdrátturinn sjálfur er ÓSKERTUR — hann var vistaður og committaður áður\n"
            "en hér var komið.\n"
            "VIÐGERÐ: endurtengja nætur-vélina við iter4r-artefaktana + serving-lagið\n"
            "(sér verk með eigin sannprófunarkröfu, sjá PLANNING_BACKLOG cc112).\n"
            "Þetta hlið má EKKI fjarlægja til að þagga keðjuna.\n"
            + "!" * 78)
    log(f"  útgáfuhlið: adapter '{MODEL_VERSION}' == lifandi '{live}' — skrif heimiluð")
    return live


def value_listings(pg, models, rows, log=print):
    """Score + freeze valuations for the given extracted listings. Returns n_written."""
    # cc112: hliðið er FYRSTA stæðan, á undan tómleikaprófinu. Nótt þar sem `rows` er tómt
    # skrifar ekkert hvort sem er — en að þegja þá væri að láta viðvörunina ráðast af
    # biðröðinni frekar en af heiminum. Mismunurinn á að heyrast í hvert sinn.
    assert_write_world_matches_live(pg, log=log)
    if not rows:
        log("  no listings to value")
        return 0
    # one feature row per fastnum (prediction is per-property)
    by_fastnum = {}
    ext_by_fastnum = {}
    for r in rows:
        fn = int(r["fastnum"])
        if fn not in by_fastnum:
            by_fastnum[fn] = {c: r[c] for c in PROP_COLS}
            by_fastnum[fn]["fastnum"] = fn
            ext_by_fastnum[fn] = build_extraction_features(
                r["extraction"], VALUATION_YEAR, r["canonical_code"])
    df = _coerce_numeric(pd.DataFrame(list(by_fastnum.values())))  # Decimal -> float for LightGBM
    base = _score_iter4(df, models).set_index("fastnum")
    full = _score_iter4(df, models, ext_by_fastnum).set_index("fastnum")

    vals = []
    skipped = 0
    for r in rows:
        fn = int(r["fastnum"])
        if fn not in base.index or fn not in full.index:
            skipped += 1
            continue
        # ── cc140 MIÐSÆKNIN FLUTT Á `real_pred_mean` ────────────────────────
        # ALDAMÖRK: 2026-08-12. Raðir með `valued_at < 2026-08-12 00:00:00+00`
        # bera MEDIAN-öldina; raðir frá og með þeim stimpli bera MEAN-öldina.
        # Mörkin eru ótvíræð af mælingu, ekki af ályktun: síðasta median-röðin
        # er 2026-08-08 03:33:24.343465+00 og 0 raðir liggja á milli hennar og
        # aldamarkanna (bakfyllingin er í pásu, --skip-valuation ósnert).
        # `scraper.v_expected_vs_real_all.midsaekni_old` reiknar öldina af
        # ÞESSUM sama stimpli — sé mörkunum breytt hér verður migrationin að
        # fylgja, annars merkir mæliflöturinn raðir á ranga öld.
        #
        # HEIMILD: DECISIONS §5D-4 (cc140) sem framkvæmir §5D-1 (cc123,
        # afstaða borðsins: kostur (a), allt á `real_pred_mean`). Rökin eru
        # INNBYRÐIS SAMRÆMI, ekki nákvæmni: cc123 mældi engan marktækan
        # nákvæmnismun á OOS-holdouti (n=949 — MAPE p=0,42, ±10 prósent
        # p=0,26, MdAPE jafntefli, 0 af 18 hólfum marktæk) meðan 17 af 21
        # neytanda lásu þegar `mean`. Bilin (lo80/hi80), flokkur A-D og SHAP
        # eru öll akkeruð á `mean`, svo þessi lína lokar K3 úr cc120: frysta
        # talan lá utan BIRTA 80 prósenta bilsins á 6.926 eignum af 167.503.
        #
        # BJAGINN FYLGIR MEÐ, ÓFALINN: `mean`-höfuðið er +1,93 prósent UNDIR
        # söluverði OOS (t = -10,74, p = 1,75e-25, cc123 §1). Sú tala á að
        # fylgja hverri umfjöllun um nákvæmni þessarar töflu.
        #
        # GAMLu RAÐIRNAR STANDA. 23.605 raðir haldast óendurritaðar (kostur
        # (b) felldur, sömu rök og cc116/cc134-b: punktmæling er söguleg
        # heimild um hvað vélin sagði). Þar með er `base_pct_error` ÓSAMFELLD
        # TÍMARÖÐ yfir aldamörkin og má ekki lesast sem ein sería.
        #
        # D2-PARITY-HLIÐIÐ ER ÓSNERT OG ÞARF EKKI AÐ FYLGJA. cc123 §7 spáði
        # að hliðið félli „ef aðeins vélin er færð"; kóðalestur fellir þá
        # spá. `model_quality_eval.run_parity` (l. 873-885) ber saman
        # ADAPTERINN við `public.predictions.real_pred_median` og les
        # `listing_valuations` hvergi — það er fidelity-próf á skoraranum,
        # óháð því hvaða dálk þessi lína frystir.
        eb = int(round(float(base.loc[fn, "real_pred_mean"])))
        ex = int(round(float(full.loc[fn, "real_pred_mean"])))
        vals.append((fn, r["source_listing_id"], r["lysing_hash"], eb, ex, True,
                     MODEL_VERSION))
    cur = pg.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    execute_values(cur,
        "INSERT INTO scraper.listing_valuations "
        "(fastnum, source_listing_id, lysing_hash, expected_base, expected_extraction, "
        " extraction_applied, model_version) VALUES %s "
        "ON CONFLICT (source_listing_id, model_version) DO NOTHING", vals, page_size=500)
    pg.commit()
    log(f"  valued {len(vals)} listings (skipped {skipped} unscored); "
        f"{len(by_fastnum)} distinct fastnum scored")
    return len(vals)


# ───────────────────────── forward / lazy Haiku half ─────────────────────────
def fetch_listings_needing_extraction(pg, limit):
    """Distinct mbl lysingar (>=300) with NO extraction yet — one representative listing each."""
    # FRESH FIRST: order distinct lysingar by most-recent listing date so newly-posted listings
    # (highest withdrawal risk) extract before the older backlog (ÞREP 2).
    sql = f"""
      WITH need AS (
        SELECT substr(md5(l.lysing), 1, 12) AS h, min(l.source_listing_id) AS slid,
               max(l.lysing) AS lysing, max(l.listed_at) AS fresh
        FROM scraper.listings l
        LEFT JOIN scraper.listing_extractions e ON e.lysing_hash = substr(md5(l.lysing), 1, 12)
        -- cc150: joinið er MARGFELDIS-ÖRUGGT og það var mælt, ekki gefið sér.
        -- `public.properties` er einkvæm á fastnum (12.08: 232.887 raðir,
        -- 232.887 einkvæm fastnúmer), svo þessi lína breytir engri af
        -- samantektartölunum í HAVING-liðnum að neðan.
        LEFT JOIN public.properties pr ON pr.fastnum = l.fastnum
        WHERE l.source = 'mbl' AND l.lysing IS NOT NULL AND length(l.lysing) >= 300
          AND e.lysing_hash IS NULL
        GROUP BY 1
        -- ══ cc150 · TVÆR SÍUR Á VERKEFNASKRÁNA — heimild cc130 (12.08) ══════
        --
        -- ATH. ENGIN PRÓSENTUMERKI Í ÞESSUM ATHUGASEMDUM — skrifaðu orðið.
        -- Þessi strengur fer í dag í `cur.execute(sql)` ÁN params, svo bert
        -- merki fellir ekki kallið EINS OG ER. Það er nákvæmlega ástæðan fyrir
        -- að reglan er skrifuð hingað: cc134 fann villuna í systurfallinu og
        -- lærdómurinn var að athugasemdir fá enga skoðun og params bætast við
        -- síðar. Sama regla og í `fetch_extracted_listings_to_value`.
        --
        -- Hin cc134-gildran, cc128-falsy: hún er skoðuð og hún er ekki hér.
        -- Hliðin að neðan bera BER `> 0` samanburð, ekki sannleiksgildi, og
        -- þetta fall hefur enga `if limit`-grein (`limit` er alltaf heiltala
        -- frá `run_extraction`, sem stöðvar á `effective_n <= 0` á undan).
        --
        -- BÁÐAR SÍURNAR ERU Á VERKEFNASKRÁNNI — hvaða lýsingar eru KEYPTAR í
        -- kvöld — ekki á neinni röð sem þegar liggur í `listing_extractions`.
        -- Sama mynstur og cc134. Ekkert er eytt og hvorug sían er endanleg:
        -- röð sem hættir að uppfylla skilyrðið birtist aftur í biðröðinni af
        -- sjálfu sér næstu nótt. Þetta er FRESTUN, ekki brottfelling.
        --
        -- ── SÍA #2 — DAUÐ KÖLL (cc130 liður 5d + tillaga 2) ─────────────────
        -- cc130 ORÐRÉTT, liður 5d („Flokkarnir sem enginn getur lesið"):
        --   „fastnum ÓLEYST (NULL) | 108 | $2,24 |
        --    `fetch_extracted_listings_to_value` krefst `fastnum IS NOT NULL`;
        --    brúin lyklar á fastnum. Hvorug leiðin nær þeim."
        --   „engin mbl-auglýsing ber textann | 163 | $3,38 |
        --    textinn er horfinn úr `listings` — hvorki verðmat né brú finnur
        --    hann"
        --   „samtals | 271 | $5,62 | 6,3 prósent næturinnar"
        -- og dómur borðsins: „RÉTTLÆTT ÁN SKILYRÐA. Eini sannanlega dauði
        -- flokkurinn." (cc130 tillaga 2.)
        --
        -- SEINNI HELMINGURINN FÆR ENGA LÍNU — hann er 0 AF BYGGINGU hérna.
        -- Biðröðin er sótt ÚR `scraper.listings`, svo lýsing sem engin
        -- auglýsing ber kemst aldrei í hana. Mælt í dag: 0 af 9.037. Sá liður
        -- var mæling á ÞEGAR KEYPTUM útdráttum, ekki á biðröðinni; hann bítur
        -- á texta sem HVARF eftir kaupin og engin forsía nær því.
        --
        -- `count(l.fastnum) > 0` er FAIL-CLOSED útgáfan: röðin fellur aðeins
        -- ef ENGIN auglýsing sem ber textann hefur fastnúmer. Fulltrúa-
        -- útgáfan (fastnum NULL á `MIN(source_listing_id)`, sú sem cc130 taldi
        -- í lið 4) fellir 560 — fjórar þeirra eiga systkina-auglýsingu MEÐ
        -- fastnúmeri sem brúin næði. Sbr. `feedback_single_deed_sian_er_timahad`:
        -- samantekt á ÖLLUM systkinum er eina greiningin sem er ekki tímaháð.
        --
        -- STAÐFEST GEGN LIFANDI KÓÐA 12.08, ekki tekið á orðinu:
        -- `public.bru_extraction_i_eigindi` ber `where v.fastnum is not null`,
        -- og `fetch_extracted_listings_to_value` ber `l.fastnum IS NOT NULL`.
        -- Greppað yfir bæði repó: `listing_extractions` er hvergi lesin af
        -- `verdmat-ai` (aðeins ferskleika-stimpillinn á `/ops`), svo þriðja
        -- leiðin sem gæti bjargað þessum röðum er ekki til. MÆLT: 556 af
        -- 9.037 (6,15 prósent, $11,52).
        --
        -- ── SÍA #4 — commercial / plot / other (cc130 tillaga 4) ────────────
        -- cc130 ORÐRÉTT: „Sleppa `category IN (commercial, plot, other)` |
        -- $7,19 | 8,0 prósent | 347 köll (þar af 319 á EXCLUDE-eignum) missa
        -- eigindi | RÉTTLÆTT EF eigandi ákveður að `/eign` á atvinnuhúsnæði sé
        -- ekki afurð. 319 af 347 bera enga spá (allar EXCLUDE); 28 falla á
        -- íbúðarflokka og eru mistalning, ekki atvinnuhúsnæði."
        -- Borðið svaraði 12.08: JÁ, SÍA — `/eign` á atvinnuhúsnæði og lóðum er
        -- ekki afurð.
        --
        -- ÁSINN ER `scraper.listings.category`, EKKI `canonical_code`.
        -- `canonical_code` ber ekki gildin commercial/plot/other yfirhöfuð —
        -- mótsvar hans er EXCLUDE, og hann er notaður hér sem VÖRN en ekki sem
        -- sía. cc130 felldi jafnframt þriðja ásinn: `er_atvinnuhusnaedi` er
        -- RENT-ONLY (NULL á öllum 37.236 sölu-auglýsingum) og því ónothæfur.
        --
        -- VARÐHLIÐIÐ SEM MÆLINGIN KREFÐIST. Hrá sían (öll systkin c/p/o)
        -- fellir 1.158 raðir — og 67 þeirra bera EIGN MEÐ GILDU ÍBÚÐAR-
        -- CANONICAL: SFH_DETACHED 38, SUMMERHOUSE 20, APT_FLOOR 6, ROW_HOUSE 1,
        -- SEMI_DETACHED 1. Það eru lóðar-auglýsingar á eign sem BER hús — sama
        -- mistalning og cc130 sá (28 af 347 í 30-daga glugganum). Þess vegna er
        -- seinni liður hliðsins til: beri EINHVER auglýsing textans eign sem
        -- cc134-hliðið hleypir í gegn, er röðin ÍBÚÐARHÆF og stendur. Með
        -- vörninni fellur 1.091, og mótprófið er 0 raðir með gilt
        -- íbúðar-canonical í fellda menginu.
        --
        -- SKÖRUNIN VIÐ cc134 ER FULLKOMIN, OG ÞAÐ ER NIÐURSTAÐAN SEM SKIPTIR
        -- MÁLI: varðaða mengið 1.091 ER nákvæmlega það mengi c/p/o-raða sem
        -- cc134-hliðið (`pr.canonical_code <> 'EXCLUDE'` í
        -- `fetch_extracted_listings_to_value`) stöðvar hvort sem er. ENGIN
        -- VERÐMÖT tapast við þessa síu. Það sem tapast er eigindalagið: 892
        -- eignir sem hefðu fengið `source='auglysing'`-raðir gegnum brúna.
        -- Það er nákvæmlega fórnin sem borðið samþykkti, hvorki meira né minna.
        --
        -- OG cc134 DREGUR SAMT EKKERT FRÁ SPARNAÐINUM: hún situr á
        -- VERÐMATSLEIÐINNI, sem gerir engin Haiku-köll ($0,00 í cc134).
        -- Haiku-kallið er keypt HÉR, á útdráttarleiðinni. cc134 sparaði enga
        -- kalla; hún stöðvaði skorun. Sparnaðurinn að neðan er því nýr og
        -- ekki tvítalinn.
        --
        -- ── MÆLT 12.08 MEÐ RAUNFALLINU — NEFNARINN ER BIÐRÖÐIN ─────────────
        --   biðröð fyrir      9.037   ($187,22 · 45,2 nætur á 200/nótt)
        --   sía 2 (dautt)       556   (6,15 prósent, $11,52)
        --   sía 4 (varðað)    1.091   (12,07 prósent, $22,60)
        --   skörun 2 og 4        69   (0,76 prósent, $1,43)
        --   SAMEINING         1.578   (17,46 prósent, $32,69)
        --   biðröð eftir      7.459   ($154,53 · 37,3 nætur)
        -- Verðeining $0,020717/kall (cc127). NEFNARINN ER ANNAR en cc130-
        -- tölurnar ($5,62 og $7,19), sem eru á 30-daga KEYPTA glugganum:
        -- biðröðin ber þyngri c/p/o-hlut (12,8 gegn 8,0 prósentum) af því að
        -- atvinnu-auglýsingar liggja lengur ólesnar en íbúðir. cc130-tölurnar
        -- mega því EKKI flytjast hingað óbreyttar.
        --
        -- ÞETTA LÆKKAR EKKI `day_total` STRAX, OG ÞAÐ ER EKKI GALLI. Nóttin
        -- kaupir `min(--forward, biðröð)`; biðröðin er 7.459 eftir síun, svo
        -- 200 köll seljast áfram á $4,143/nótt. Sparnaðurinn kemur fram sem
        -- STYTTRI BIÐRÖÐ: 1.578 köll verða aldrei keypt. Koma nýrra hasha
        -- mælist 15,5/dag (418 á 27 dögum), svo nettó-tæming er 184,5/nótt:
        -- 49,0 nætur að tæmingu fyrir, 40,4 eftir. Fyrst þegar biðröðin fer
        -- undir 200 fellur `day_total` af sjálfu sér.
        HAVING count(l.fastnum) > 0
           AND (count(*) FILTER (WHERE l.category IS DISTINCT FROM 'commercial'
                                   AND l.category IS DISTINCT FROM 'plot'
                                   AND l.category IS DISTINCT FROM 'other') > 0
             OR count(*) FILTER (WHERE pr.canonical_code IS NOT NULL
                                   AND pr.canonical_code <> 'EXCLUDE') > 0)
      )
      SELECT h, slid, lysing FROM need ORDER BY fresh DESC NULLS LAST LIMIT {int(limit)}
    """
    cur = pg.cursor()
    cur.execute(sql)
    return [{"lysing_hash": r[0], "source_listing_id": r[1], "lysing": r[2]} for r in cur.fetchall()]


def extract_and_store(pg, client, rows, source_trigger, log=print):
    """Haiku 108-field extract for each distinct lysing, store content-addressed. Returns counts."""
    from pilot_extract_v022 import build_tool_schema, extract_listing, calc_cost
    schema = build_tool_schema()
    out = []
    n_call = n_fail = n_rejected = n_retry_saved = 0
    reason_tally = {}

    # cc127 — raunkostnaður safnast PER KALL, ekki sem fasti × kallafjöldi.
    # Tvö aðskilin bókhöld: MÆLT (notkun fylgdi svarinu) og ÁÆTLAÐ (hún gerði það
    # ekki). Þau eru lögð saman í eina dagstölu en aldrei brædd saman í logginu.
    cost_measured = 0.0
    n_measured = n_unmeasured = 0
    tok = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}

    def _bok_notkun(usage):
        """Bóka raunnotkun eins Haiku-kalls. Skilar True ef notkun fylgdi svarinu.

        Fallið kall skilar `{}` (pilot_extract_v022:701-704) — þá er ENGIN tala til
        og kallið fer í áætlunar-dálkinn frekar en að vera bókað á núll.
        """
        nonlocal cost_measured, n_measured, n_unmeasured
        if not usage or usage.get("input_tokens") is None:
            n_unmeasured += 1
            return False
        cost_measured += calc_cost(usage)
        n_measured += 1
        tok["input"] += usage["input_tokens"]
        tok["output"] += usage["output_tokens"]
        tok["cache_read"] += usage["cache_read_tokens"]
        tok["cache_creation"] += usage["cache_creation_tokens"]
        return True
    for i, r in enumerate(rows, 1):
        h = r["lysing_hash"]
        # content-addressed idempotency is handled by the fetch filter + ON CONFLICT DO NOTHING
        # (no in-loop SELECT, so the final write keeps SET TRANSACTION READ WRITE as its first stmt)
        try:
            raw, usage, err = extract_listing(client, schema, r["lysing"], lambda *a, **k: None)
            n_call += 1
            _bok_notkun(usage)          # cc127: bóka ÁÐUR en villa kastar okkur út
            if err or raw is None:
                raise RuntimeError(err or "no extraction")

            # cc94 ÞREP A — dæma svarið ÁÐUR en það fer í töfluna.
            status, reasons = validate_extraction(raw)

            # Form-rekið er slembið (2,97% að meðaltali, ekki eiginleiki tiltekinnar
            # lýsingar), svo EITT endurkall bjargar meirihluta strengja-tilvika á
            # ~$0,0071. Aðeins reynt á components-brotunum: ár og enum-brot eru
            # lestrarvillur á textanum sjálfum og endurkall myndi líklega endurtaka þau.
            if any(x in reasons for x in ("components_string", "components_missing")):
                log(f"    [{i}/{len(rows)}] {h} {status} — endurkalla einu sinni")
                raw2, usage2, err2 = extract_listing(client, schema, r["lysing"],
                                                     lambda *a, **k: None)
                n_call += 1          # kostnaðarbókhaldið verður að telja endurkallið
                _bok_notkun(usage2)  # cc127: og verðleggja það á SINNI eigin notkun
                if not err2 and raw2 is not None:
                    status2, reasons2 = validate_extraction(raw2)
                    if status2 == "ok":
                        n_retry_saved += 1
                        raw, status, reasons = raw2, status2, reasons2
                    elif not any(x in reasons2 for x in
                                 ("components_string", "components_missing")):
                        # seinna svarið er heilt að byggingu þótt það brjóti annað —
                        # það er strangt betra en strengur og verður fyrir valinu
                        raw, status, reasons = raw2, status2, reasons2

            # A1: RÖÐIN ER VISTUÐ HVORT SEM ER, ÓBREYTT. Höfnun sem sleppir
            # skrifum myndi láta fetch_listings_needing_extraction (LEFT JOIN á
            # lysing_hash IS NULL) velja SÖMU lýsingu aftur næstu nótt, að eilífu.
            out.append((h, Json(raw), SCHEMA_VERSION, EXTRACT_MODEL, source_trigger,
                        len(r["lysing"]), status))
            if status == "ok":
                log(f"    [{i}/{len(rows)}] {h} ok ({usage.get('duration_sec','?')}s)")
            else:
                n_rejected += 1
                for x in reasons:
                    reason_tally[x] = reason_tally.get(x, 0) + 1
                log(f"    [{i}/{len(rows)}] {h} HAFNAD {status}")
        except Exception as e:
            n_fail += 1
            log(f"    [{i}/{len(rows)}] skip {h}: {type(e).__name__}: {e}")
    if out:
        cur = pg.cursor()
        cur.execute("SET TRANSACTION READ WRITE")
        execute_values(cur,
            "INSERT INTO scraper.listing_extractions "
            "(lysing_hash, extraction, extraction_schema_version, extraction_model, "
            " source_trigger, lysing_len, validation_status) VALUES %s "
            "ON CONFLICT (lysing_hash) DO NOTHING", out, page_size=500)
        pg.commit()
    # cc127 — kostnaðurinn er nú SUMMA raunkalla, ekki fasti × fjöldi.
    # `cost_usd` er talan sem bókast á daginn; hinar tvær sýna úr hverju hún er gerð.
    # Gamli lykillinn `cost_est_usd` er FALLINN VILJANDI (ekki endurnefndur hljóðlega):
    # hann bar áætlun og hver sem les hann á að fá KeyError, ekki ranga tölu.
    cost_fallback = n_unmeasured * PER_CALL_USD_EST
    return {"haiku_calls": n_call, "stored": len(out), "failed": n_fail,
            "rejected": n_rejected, "retry_saved": n_retry_saved,
            "reasons": reason_tally,
            "cost_usd": round(cost_measured + cost_fallback, 6),
            "cost_measured_usd": round(cost_measured, 6),
            "cost_estimated_usd": round(cost_fallback, 6),
            "calls_measured": n_measured,
            "calls_estimated": n_unmeasured,
            "tokens": dict(tok)}


# ───────────────────────────── brúin í eigindalagið ─────────────────────────────
def bridge_attributes(pg, fastnum=None, log=print):
    """cc75 — flytur útdrættina í public.property_attributes (source='auglysing').

    Öll vörpunin og öll idempotens-logíkin er í DB-fallinu
    public.bru_extraction_i_eigindi (migration 20260803_cc75_bru_extraction_eigindi):
    deterministísk kortlagning v0.2.2 → 28-lykla vokabúlar, ENGIN Haiku-kall,
    enginn kostnaður. Þessi hjúpur er aðeins kallið + logglínan.

    Fyrir cc75 lá ENGIN leið héðan í eigindalagið: 3.133 eignir með virka
    auglýsingu báru útdrátt sem app-pípan sá aldrei (hún les eingöngu
    public.last_listing_text = pöruð SÖLU-söluyfirlit), svo hvert einasta
    eigindi stóð „Óþekkt" á eign í virkri sölu.

    Idempotent: mengjasamanburður í DB-fallinu, óbreytt mengi = 0 skrif.
    Óhætt að keyra hvenær sem er og hversu oft sem er.
    """
    cur = pg.cursor()
    cur.execute("SET TRANSACTION READ WRITE")
    cur.execute("SELECT * FROM public.bru_extraction_i_eigindi(%s)", (fastnum,))
    eignir, nyjar, vikjandi = cur.fetchone()
    pg.commit()
    log(f"  bridge: {eignir} eignir kortlagðar -> {nyjar} nyjar radir, "
        f"{vikjandi} vikjandi (source='auglysing')")
    return {"eignir": eignir, "nyjar": nyjar, "vikjandi": vikjandi}
