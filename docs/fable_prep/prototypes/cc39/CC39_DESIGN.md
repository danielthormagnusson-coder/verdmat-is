# CC39 — ×1000-override: gildisvarin ÷1000-skilgreining fyrir báðar leiðslur

**Dags.:** 2026-07-23 · **Staða:** FASI 1–2 lokið, HALT fyrir apply · **Deadline:** live fyrir su. 26.07 04:00Z

## 0. Klukka (tvíhliða)

| Uppspretta | Tími | Frávik |
|---|---|---|
| Staðarvél (GMT) | 2026-07-23 05:51:36Z | +0,0215 s vs NTP (time.windows.com) |
| Supabase `now()` | 2026-07-23 05:52:25Z (UTC) | <1 s innbyrðis (mælt í röð) |

## 1. Probe-niðurstöður (read-only, allt sjálfmælt)

### 1.1 Raðirnar — handoff-talan STÓÐST nákvæmlega

CSV (`D:\kaupskra.csv`, 230.008 hráraðir, FK-síað universe 228.756):

| faerslunumer | fastnum | thinglýst | KAUPVERD (þús) | EINFLM | hrátt kr/m² | ÷1000 kr/m² |
|---|---|---|---|---|---|---|
| 744059 | 2513390 | 2026-06-16 | 22.000.000 | 229,9 | 95,7M | 95,7þ |
| 744084 | 2533315 | 2026-06-16 | 25.990.000 | 52,1 | 498,8M | 498,8þ |
| 744085 | 2156644 | 2026-06-16 | 18.000.000 | 302,3 | 59,5M | 59,5þ |

**Lifandi DB ber ÞEGAR rétt gildi**: nominal 22,0M / 25,99M / 18,0M kr, real ≈ nominal
(akkeri 2026-07), allar þrjár `is_suspect_comparable=true` (kv_extreme+...). Spillingin
er því **CSV-megin eingöngu** — daglega leiðslan uppfærir aldrei eldri raðir (DO NOTHING
locked) svo hún flytur skekkjuna ekki inn; vikulegi vörðurinn stöðvar hana.

**Fleiri/færri en 3?** Nei — sannreynt tvíhliða:
- CSV-raðir > 3 ma.kr nominal: 868; þar af 865 ÞEGAR í DB með sömu (háu) gildum =
  fjöleininga-skjöl (heildarverð skjals bókað á hverja einingu, t.d. f=667958:
  10 ma.kr/16.401,6 m² á 33 fastnum; f=545113: 4,44 ma.kr/48.712,8 m²). 868−865 = 3. ✔
- kr/m²-krossmæling: CSV >2M kr/m² = 57, DB = 54, mismunur = 3. ✔
- Neðri halinn: 89 DB-raðir með nominal 1þ–100þ kr = sentinel-/málamyndaverð
  (R1-flokkur, þekkt) — EKKI ÷1000-tilvik, utan umfangs, bókað.

### 1.2 Nefnarar gildisvarnarinnar (dreifing gagnanna sjálfra)

FK-síaðar raðir m/EINFLM>10: 228.696 (60 án nothæfs EINFLM, hámark þeirra 120M kr nominal — hreinar).

| Mæling | Gildi |
|---|---|
| kr/m² p50 / p99 / p99,9 / p99,99 | 317þ / 1,02M / 1,49M / 3,77M |
| **Lögmætt hámark** (f=723979, þegar í DB) | **8.021.633 kr/m²** |
| **Lægsta ×1000-röð** (744085) | **59.543.500 kr/m²** |
| Bil (aðskilnaður) | 7,4× |
| Höfnuð vörn: absolút nominal | p99,9 = 7,5 ma.kr (fjöleininga-skjöl lögmæt yfir öllum þröskuldi) |
| Höfnuð vörn: kv = KAUPVERD/FASTEIGNAMAT | 2.266 lögmætar raðir með kv∈[100,2000] (skjalsheild vs eining) |

### 1.3 Leiðslu-kortið: ein heimild, tveir lesendur — punkturinn ER til

```
D:\kaupskra.csv (HMS)
   └─ derive_sales_rows()  í  scripts/rebuild_sales_history.py:139   ← EINI staðurinn
      (nominal = KAUPVERD*1000; compute_suspect les sama frame)        sem override fer á
        ├─ daily_sales_refresh.py   (S4U nætur; INSERT..DO NOTHING — aldrei UPDATE)
        └─ monthly_cpi_reanchor.py  (S4U su. 04:00; les nominal í sanity, skrifar real)
```
Engin afrit af logíkinni þarf. Utan umfangs, bókað: þjálfunarhliðin
(`D:\build_training_data.py`, `precompute/build_comps_v2.py`) les kaupskra.csv sjálfstætt —
næsti iter5-hringur sér ×1000-raðirnar hráar nema HMS lagi fyrst (kv-band + is_suspect
sía þær líklega; sannreyna í þeirri lotu, ekki hér).

### 1.4 Vörðurinn í vikulegu keyrslunni — vænt hegðun skilgreind FYRIR breytingu

- Staðsetning: `monthly_cpi_reanchor.py` skref [4], `return 3` (línur 224–230).
- Trigger: `nominal_changed>0` (eða onothaefur/thinglystdags) í samanburði
  live ↔ re-derived. Núna: nákvæmlega 3 (loggað 09.07, 12.07, 17.07-dryrun, 19.07).
- Afleiðing í dag: akkerisfærslan 2026-07→2026-08 BLOKKERUÐ (anchor fast síðan 22.06;
  `model_pred_anchor_ym` þegar 2026-08 → akkerin ósamstillt á meðan).
- **EFTIR override: keyrslan á að VINNA (exit 0)** — override leiðréttir lesturinn svo
  nominal_changed=0; UPDATE á kaupverd_real ~öllum sameiginlegum röðum (akkerisskipti
  breyta hverri röð), akkeri→2026-08, cpi_index-upsert, MV-refresh.
  **Vörðurinn stendur ÓBREYTTUR** (return 3 ósnert) sem bakstopp fyrir hverja framtíðar-
  stökkbreytingu sem gildisvörnin nær ekki (t.d. röð án EINFLM, ný tegund skekkju).

## 2. Skilgreiningin (FASI 2)

Ein fall, `apply_x1000_override(kp)` (sjá `x1000_override_proto.py` — flyst orðrétt):

- **Virkjar aðeins á gildi, aldrei ID**: `KAUPVERD*1000/EINFLM > 20.000.000 kr/m²`
  (2,5× yfir lögmæta hámarkinu 8,02M; 3× undir lægstu ×1000-röðinni 59,5M)
  **OG** `÷1000-gildið < 2.000.000 kr/m²` (lögmæt p99,9=1,49M — röð sem stenst þetta
  ekki er EKKI leiðrétt og strandar áfram á verðinum = mannlegt mat).
- **Sjálf-útrennsli**: HMS-löguð röð fellur á fyrra skilyrðið → engin virkjun, ekkert
  handtak. Prófað á tilbúnum "löguðum" gildum (próf 4).
- **Staðsetning**: allra fyrsta skref `derive_sales_rows` — bæði suspect-reglurnar og
  nominal/real-afleiðslan lesa leiðrétt gildi; báðir lesendur erfa.
- **Audit-spor**: JSONL-append í `D:\x1000_override_audit.jsonl` (ts_utc, caller,
  faerslunumer, fastnum, thinglystdags, upphafsgildi, leiðrétt gildi, einflm, hrátt
  kr/m²) + færslur skilað í stats svo báðir kallarar logga hátt í sínar keyrslu-loggur.
- **EINFLM-laus röð**: aldrei leiðrétt hér (60 slíkar í dag, allar hreinar);
  vikulegi vörðurinn ver þær áfram.

**Próf: 14/14 GRÆN** (`test_x1000_override_cc39.py`, keyrt 2026-07-23 gegn raun-CSV):
nákvæmlega 3 leiðréttingar; derived nominal == DB-gildin þrjú; 4 lögmætar stór-raðir
ósnertar; HMS-lagað afrit → 0; EINFLM-laus + ofur-lúx (÷1000>2M) → 0; mótpróf virkjar;
audit-línur réttar.

## 3. Apply-plan eftir GO (engin DB-skrif — hrein kóðabreyting)

1. `rebuild_sales_history.py`: fastar + `apply_x1000_override` (orðrétt úr proto);
   fyrsta lína `derive_sales_rows`: `kp, x1000_entries = apply_x1000_override(kp)`;
   `stats["x1000_overrides"]=len(...)`, `stats["x1000_entries"]=...`.
2. `daily_sales_refresh.py` + `monthly_cpi_reanchor.py`: ein hávær log-lína hvor ef
   `stats["x1000_overrides"]>0` (Stage-B-lexían: engin þögul leiðrétting).
3. Sannreyning á lesflötum BEGGJA (raunkeyrsla, ekki ályktun):
   `daily_sales_refresh.py --dryrun` (vænt: override=3, engin ný innsetning vegna þeirra)
   og `monthly_cpi_reanchor.py --dryrun --test-anchor 2026-08` (vænt: **nominal_changed=0**,
   DRYRUN-UPDATE ~228,7þ raðir mældar og rúllað til baka). Dry-run ER studd → fyrsta
   raunpróf þarf ekki að bíða sunnudags-blint.
4. Git: explicit paths eingöngu (3 skrár + prototypes/cc39/), aldrei `add -A`.

**Vænt rowcount-tafla:**

| Mæling | Vænt |
|---|---|
| Override-virkjanir per keyrsla (þar til HMS lagar) | 3 (744059/744084/744085) |
| Vikuleg sanity: nominal/onothaefur/thinglystdags changed | 0 / 0 / 0 |
| Vikuleg UPDATE kaupverd_real (su. 26.07) | ≈ fjöldi sameiginlegra raða (228.756 í dag, vex ~daglega; 228,7þ–229,1þ) |
| Vænt exit-kóði su. 26.07 04:00 | 0 (LastTaskResult 0x0), akkeri 2026-07→2026-08 |
| Handvirk DB-skrif í cc39 | ENGIN (FASI 4-pooler-prótókollið á ekki við) |

## 4. Rollback

`rollback_cc39.sql` (Test-Path-sannreynt í HALT-skilum): A) kóða-revert = git;
B) ef sunnudagskeyrslan committar og þarf afturköllun: restore úr
`sales_history_real_backup_<ts>` (innbyggt rollback-net keyrslunnar, committað FYRIR
skrifin) + akkeri aftur á 2026-07 + MV-refresh-listi. Öruggt bilunarform eftir revert:
vörðurinn fer sjálfkrafa aftur í exit 3.

## 5. Skrár í þessari möppu

| Skrá | Hlutverk |
|---|---|
| `x1000_override_proto.py` | Skilgreiningin sjálf (flyst orðrétt í derive-kjarnann) |
| `test_x1000_override_cc39.py` | Sjálfstætt próf, 14/14 grænt 2026-07-23 |
| `rollback_cc39.sql` | Rollback-slóðir A+B |
| `probe_cc39.py`, `probe_cc39_b.py` | FASI 1 read-only mælingarnar |
| `CC39_DESIGN.md` | Þetta skjal |
