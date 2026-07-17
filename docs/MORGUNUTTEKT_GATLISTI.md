# MORGUNÚTTEKT — GÁTLISTI

Trigger-orð: **„morgunúttekt"**. Lotan er **100% read-only** — engin skrif, enginn push,
engin lagfæring án sér-go. Sniðið er cc10-úttektin 2026-07-17 (fyrsta morgunúttekt á
iter4r_20260716-stofninum). Uppfærðu viðmiðunartölur hér additíft þegar þær breytast.

Supabase-verkefni: `szzjsvmvxfrhyexblzvq` (verdmat-is).

---

## 1. KLUKKA (tvíhliða)

- Local: `Get-Date` + UTC-varpan — vélin stendur á UTC (Ísland, engin DST).
- DB: `select now();` um Supabase MCP.
- Vænt: mismunur innan sekúndna (leiðrétt fyrir kalltöf milli mælinga).

## 2. DELTA-KEÐJAN (01:00)

- Loggur: `D:\verdmat-is\scraper_data\night_logs\night_YYYYMMDD.log`
  → á að enda á `=== CHAIN CLEAN (exit 0) ===`.
- Raðafjöldi nætur: `scraper_data\logs\promote_YYYYMMDD.log`, línan
  `write-set: total=N` + `wrote listings rows=N`.
- **Viðmið: ~600–1500 raðir = heilbrigt; ~25K = watermark brotið → HALT og flagga strax.**
- Watermark: `watermark advanced: sale=A rent=B` á að hækka frá fyrri nótt
  (state: `mbl_promote_append_state.json`).

## 3. NÆTURVERKIN (Task Scheduler)

```powershell
Get-ScheduledTask | ? {$_.TaskName -like 'verdmat-*'} | % {
  $i = $_ | Get-ScheduledTaskInfo
  [PSCustomObject]@{Name=$_.TaskName; State=$_.State; LastRun=$i.LastRunTime;
    LastResult=('0x{0:X}' -f $i.LastTaskResult); NextRun=$i.NextRunTime} } | ft -AutoSize
```

| Verk | Tími | Vænt Last Result |
|---|---|---|
| verdmat-nightly-delta | 01:00 | 0x0 |
| verdmat-nightly-myigloo | 02:00 | 0x0 |
| verdmat-daily-sales-refresh | 02:30 | 0x0 |
| verdmat-nightly-backup | 03:00 | 0x0 |
| verdmat-daily-lifecycle-sweep | 06:00 | 0x0 / 0x41301 (keyrir enn) / 0x41306 (12h-þak, by-design á mid-round nóttum) |
| verdmat-weekly-cpi-reanchor | su. 04:00 | 0x0 / **0x3 (sjá §8 — grænt meðan ×1000-varðan heldur)** |
| verdmat-weekly-model-quality | má. 05:00 | 0x0 |

Óvænt gildi → Scheduler-loggurinn (kveikt síðan 15.07) segir hvað gerðist.

## 4. SWEEP

- **a)** Trigger/resume: 06:00-instansinn á að vera í gangi (0x41301) eða klára hreint.
  State: `D:\verdmat-is\scraper_data\lifecycle_sweep_state.json`
  (`cursor`/`round_total` + `request_log` með jöfnu 120s-bili = lifandi).
- **b)** Escalation-backlog (á að LÆKKA milli daga; upphaf 11.995 þann 15.07):

```sql
with ev as (select source_listing_id, event_type
            from scraper.listing_lifecycle_events where source='mbl')
select count(distinct e1.source_listing_id) as pending_absent_now
from ev e1
where e1.event_type='confirmed_absent_1'
  and not exists (select 1 from ev e2
                  where e2.source_listing_id=e1.source_listing_id
                    and e2.event_type='withdrawn_confirmed');
```

- **c)** `D:\verdmat-is\scraper_data\lifecycle_sweep_error.log` — á **ekki að vera til**
  (traceback-loggerinn skrifar hana aðeins við villu).

## 5. BACKUP (03:00)

- Wrapper: `D:\verdmat-is\backup_log\YYYY-MM-DDT03-00_wrapper.log` (UTF-16)
  → `entries OK: 10 / 10`, `entries failed: 0`. Mengið tekur m.a.
  `app\audit`, `app\heimildasafn`, `docs\fable_prep`, Gagnapakkar-db ×5, image_index.db.
- Detail: `..._log\YYYY-MM-DDT03-00.log` (rclone) — engin ERROR-lína.
- Viðmiðunarstærð 17.07: 422 skrár / ~10,9 GB manifest.

## 6. ITER4R-HEILBRIGÐI (lifandi lag)

- **a)** Ein model_version, enginn NULL, raðafjöldi = síðasta þekkta viðmið
  (167.503 frá flippi 16.07):

```sql
select model_version, count(*),
       count(*) filter (where real_pred_median is null) as null_median,
       count(*) filter (where real_pred_lo80 is null or real_pred_hi80 is null) as null_pi80,
       count(*) filter (where confidence_grade is null) as null_grade
from public.v_current_predictions group by 1;
```

- **b)** Anon-REST stikkprufa (lagið sem appið les) — mat + bil + flokkur skila sér;
  lyklar í `app\.env.local`:

```bash
curl -s "$URL/rest/v1/v_current_predictions?select=fastnum,real_pred_median,real_pred_lo80,real_pred_hi80,confidence_grade,model_version&limit=3&offset=1000" \
  -H "apikey: $ANON" -H "Authorization: Bearer $ANON"
```

- **c)** Suspect-flögg nýrra sala nætur (N = `inserted=` úr `D:\daily_sales_refresh.log`):

```sql
with nyjar as (select * from public.sales_history order by id desc limit N)
select count(*) filter (where is_suspect_comparable) as n_suspect,
       count(*) filter (where einflm_at_sale > 0
         and kaupverd_nominal/einflm_at_sale > 10000000
         and not coalesce(is_suspect_comparable,false)) as over10m_EKKI_flaggad
from nyjar;  -- over10m_EKKI_flaggad á að vera 0
```

- **d)** Precompute/extraction: `scraper_data\logs\extraction_YYYYMMDD.log` endar á
  `valued N listings (skipped 0 unscored)`; `failed: 0` í extract-summu.
  Sales-refresh: `D:\daily_sales_refresh.log` → `[7] done.` + `GONE=0` + 12 MV refreshaðar.

## 7. SAMANTEKT + DÓMUR

Tafla: verk / staða / frávik. Dómur JÁ/NEI á heilbrigði nætur. Frávik fá aldrei
lagfæringu í úttektarlotunni sjálfri — rannsókn/lagfæring er sér-lota með sér-go.

---

## 8. 0x3-TÚLKUNIN (verdmat-weekly-cpi-reanchor, su. 04:00)

Bókað 17.07.2026 (cc10-greining):

- `monthly_cpi_reanchor.py` ber SANITY-vörð: endurleidd `nominal/onothaefur/thinglystdags`
  verða að vera óbreytt, annars ABORT með harðkóðuðu **`return 3`** — engin skrif,
  anker óbreytt. Exit-kort skriptunnar: **0** = success/no-op, **1** = skrefsbilun,
  **3** = sanity-vörður hélt.
- Rótin sem heldur vörðnum virkum: HMS-kaupskráin ber ×1000-innsláttarvillu
  (KAUPVERD í kr í stað þús.kr) á faerslunumer **744059 / 744084 / 744085**.
  Meðan hún er óleiðrétt í heimildinni abortar hvert re-anchor á 2026-08 grænt.
- **Vaktarregla: 0x3 á sunnudagsnótt = „vörðurinn heldur" = GRÆNT merki.**
  Rautt væri: 0x1 (skrefsbilun), crash í loggnum `D:\monthly_cpi_reanchor.log`,
  eða 0x3 með ÖÐRUM nominal_changed-röðum en þessum þremur (tékka logg).
- Skriptan les/hreyfir ALDREI `model_pred_anchor_ym` eða `model_version` í
  pipeline_config — exact-key lookup á `sales_history_anchor_ym` eingöngu.
- Framhald: sameinuð gildisvarin inntaks-override á raðirnar þrjár (ein skilgreining,
  notuð af bæði sales_history-leiðslunni og `build_training_data.py` á D:-rót sem ber
  þegar ÷1000-override á sömu raðir; rennur sjálfkrafa út þegar HMS lagar upprunann) —
  sér-lota 20.–21.07, deadline sannreynd fyrir su. 26.07 04:00.

## Líkan-flipinn á /markadur (cc11, 2026-07-17)

- [ ] v_model_vs_sold_by_hood: talning > 0 eftir næsta refresh með mat↔sölu-pörum
  (var 0 raðir 17.07 eftir iter4r-flipp — Líkan-flipinn á www.verdmat.ai/markadur ber
  tóm-stöðu þar til þá; hakað við þegar flipinn sýnir töfluna aftur).
